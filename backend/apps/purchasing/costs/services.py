"""
Chi phí mua hàng & giá vốn lô — landed cost (P-03, BR-GV).

`record_purchase_cost`: ghi Purchase Cost + phân bổ vào lô nhận, rồi tính lại
landed_unit_cost qua `apps.inventory.batches.services.recompute_landed_cost`.
Chặn lô đã chốt (BR-GV-02). Lỗi nghiệp vụ -> BusinessError.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batches
from apps.inventory.models import Batch
from apps.purchasing.models import PurchaseCost, PurchaseCostAllocation

ZERO = Decimal("0")
CENT = Decimal("0.01")


def record_purchase_cost(*, cost_type, amount, allocation_method, incurred_date,
                         allocations, actor, note=""):
    """
    Ghi một Purchase Cost và phân bổ vào các lô nhận, rồi tính lại landed_unit_cost.

    `allocations` là list mô tả các lô nhận phân bổ, mỗi phần tử có thể là:
      - Batch instance (auto-allocate),
      - dict {"batch": Batch | pk} hoặc {"batch_id": "<mã lô>"} (auto-allocate),
      - dict như trên kèm "amount"/"allocated_amount" -> truyền sẵn số tiền mỗi lô.

    Hai kiểu phân bổ:
      (a) Truyền sẵn: mọi phần tử có "amount". Tổng phải khớp `amount`.
      (b) Tự phân bổ: không phần tử nào có "amount". Chia tổng `amount` theo
          `allocation_method` — BY_QTY theo số kg (mặc định, BR-GV-04) hoặc
          BY_VALUE theo giá trị mua (purchase_rate * qty_received). Phần dư làm
          tròn dồn vào lô cuối để tổng phân bổ = amount.

    BR-GV-02: không cho thêm chi phí vào lô đã chốt (CLOSED) -> BusinessError.
    BR-GV-03: recompute_landed_cost tự ghi AuditLog mỗi khi giá vốn đổi (kể cả hồi tố).
    """
    amount = Decimal(amount)
    if amount < ZERO:
        raise BusinessError("Số tiền chi phí không được âm.")
    if not allocations:
        raise BusinessError("Phải chỉ định ít nhất một lô nhận phân bổ.")

    with transaction.atomic():
        resolved = [_resolve_allocation(a) for a in allocations]

        # BR-GV-02: chặn lô đã chốt trước khi ghi bất cứ thứ gì
        for batch, _ in resolved:
            if batch.is_closed:
                raise BusinessError(
                    f"Lô {batch.batch_id} đã chốt, không thêm chi phí được (BR-GV-02)."
                )

        amounts = _split_amounts(amount, resolved, allocation_method)

        cost = PurchaseCost.objects.create(
            cost_type=cost_type,
            amount=amount,
            allocation_method=allocation_method,
            incurred_date=incurred_date,
            note=note,
            created_by=actor,
        )
        for (batch, _), alloc_amount in zip(resolved, amounts):
            PurchaseCostAllocation.objects.create(
                purchase_cost=cost, batch=batch, allocated_amount=alloc_amount
            )

        # tính lại giá vốn hiện hành cho từng lô nhận (giá vốn hồi tố hợp lệ)
        for batch, _ in resolved:
            batches.recompute_landed_cost(batch=batch, actor=actor)

    return cost


def _resolve_allocation(entry):
    """Trả (Batch, explicit_amount | None) từ một phần tử allocations."""
    if isinstance(entry, Batch):
        return entry, None
    if not isinstance(entry, dict):
        raise BusinessError("Phần tử phân bổ không hợp lệ.")

    batch = _resolve_batch(entry)
    raw = entry.get("amount", entry.get("allocated_amount"))
    explicit = Decimal(raw) if raw is not None else None
    if explicit is not None and explicit < ZERO:
        raise BusinessError(f"Số tiền phân bổ cho lô {batch.batch_id} không được âm.")
    return batch, explicit


def _resolve_batch(entry):
    b = entry.get("batch")
    if isinstance(b, Batch):
        return b
    if "batch_id" in entry and entry["batch_id"] is not None:
        try:
            return Batch.objects.get(batch_id=entry["batch_id"])
        except Batch.DoesNotExist:
            raise BusinessError(f"Không tìm thấy lô có mã {entry['batch_id']}.")
    pk = b if b is not None else entry.get("batch_pk", entry.get("pk"))
    if pk is not None:
        try:
            return Batch.objects.get(pk=pk)
        except Batch.DoesNotExist:
            raise BusinessError(f"Không tìm thấy lô id={pk}.")
    raise BusinessError("Mỗi phần tử phân bổ phải chỉ ra một lô (batch / batch_id).")


def _split_amounts(amount, resolved, allocation_method):
    """
    Chia `amount` thành list số tiền theo từng lô, tổng luôn = amount.
    Ưu tiên số truyền sẵn; nếu không có thì tự phân bổ theo kg / giá trị.
    """
    has_explicit = [amt is not None for _, amt in resolved]
    if any(has_explicit) and not all(has_explicit):
        raise BusinessError(
            "Phân bổ phải nhất quán: hoặc truyền số tiền cho MỌI lô, hoặc không lô nào."
        )

    if all(has_explicit):
        amounts = [amt.quantize(CENT, rounding=ROUND_HALF_UP) for _, amt in resolved]
        if sum(amounts, ZERO) != amount.quantize(CENT, rounding=ROUND_HALF_UP):
            raise BusinessError(
                "Tổng số tiền phân bổ truyền vào không khớp số tiền chi phí."
            )
        return amounts

    # tự phân bổ theo trọng số
    weights = [_weight(batch, allocation_method) for batch, _ in resolved]
    total_weight = sum(weights, ZERO)
    if total_weight <= ZERO:
        raise BusinessError(
            "Không thể phân bổ: tổng trọng số (kg / giá trị) của các lô bằng 0."
        )

    amounts = []
    running = ZERO
    last = len(resolved) - 1
    for i, w in enumerate(weights):
        if i == last:
            # dồn phần dư vào lô cuối để tổng = amount tuyệt đối
            amounts.append((amount - running).quantize(CENT, rounding=ROUND_HALF_UP))
        else:
            share = (amount * w / total_weight).quantize(CENT, rounding=ROUND_HALF_UP)
            amounts.append(share)
            running += share
    return amounts


def _weight(batch, allocation_method):
    if allocation_method == PurchaseCost.AllocationMethod.BY_VALUE:
        return batch.purchase_rate * batch.qty_received
    # BY_QTY (mặc định, BR-GV-04)
    return batch.qty_received
