"""
Lô hàng: sinh lô, FIFO + giữ chỗ, vòng đời, giá vốn lô, job trạng thái theo hạn (P-04).

Giữ chỗ tách khỏi tồn thật: `qty_reserved` (BR-BH-01/02). Chọn lô FIFO theo ngày
nhập (BR-BH-05). Tất cả hàm chạy trong transaction, dùng `select_for_update` để an
toàn khi hai khách tranh lô cuối (BR-BH-02, E-06). Biến động tồn đi qua
`apps.inventory.stock.services.record_movement`.
"""
import datetime
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.inventory.models import Batch, StockLedgerEntry
from apps.inventory.stock import services as stock


ZERO = Decimal("0")
SELLABLE_STATUSES = (Batch.Status.SELLING, Batch.Status.NEAR_EXPIRY)


def sellable_batches(*, item=None, on_date=None):
    """
    Nguồn DUY NHẤT cho "lô bán được" (BR-LO-02, S1): trạng thái SELLING/NEAR_EXPIRY
    **và** `expiry_date >= hôm nay` theo giờ Asia/Ho_Chi_Minh. `expiry_date` là ngày
    cuối còn bán (C1). Không phụ thuộc job `update_batch_status` — job chết thì lô
    quá hạn vẫn không bán được. Thứ tự FIFO theo ngày nhập (BR-BH-05).
    """
    on_date = on_date or timezone.localdate()
    qs = Batch.objects.filter(status__in=SELLABLE_STATUSES, expiry_date__gte=on_date)
    if item is not None:
        qs = qs.filter(item=item)
    return qs.order_by("received_date", "id")


# --- Sinh lô ----------------------------------------------------------------

def create_batch(*, item, supplier, warehouse, received_date, qty, purchase_rate,
                 shelf_life_days=None, actor=None, batch_id=None):
    """
    Sinh một lô mới (BR-MH-01: mỗi lần nhập một mặt hàng = một lô).
    Hạn dùng = ngày nhập + shelf_life (mặc định theo Item / settings). landed_unit_cost
    khởi tạo = giá mua (chưa có chi phí phụ). Ghi ledger RECEIPT.
    """
    qty = Decimal(qty)
    purchase_rate = Decimal(purchase_rate)
    days = shelf_life_days or item.shelf_life_in_days or settings.BATCH_DEFAULT_SHELF_LIFE_DAYS
    expiry = received_date + datetime.timedelta(days=days)
    bid = batch_id or f"{item.code}-{received_date:%y%m%d}-{uuid4().hex[:5].upper()}"

    with transaction.atomic():
        batch = Batch.objects.create(
            batch_id=bid,
            item=item,
            supplier=supplier,
            warehouse=warehouse,
            received_date=received_date,
            expiry_date=expiry,
            qty_received=qty,
            qty_available=ZERO,  # sẽ +qty qua record_movement để sổ khớp
            qty_reserved=ZERO,
            purchase_rate=purchase_rate,
            landed_unit_cost=purchase_rate,
            status=Batch.Status.DRAFT,
        )
        stock.record_movement(
            batch=batch, qty_change=qty, movement_type=StockLedgerEntry.MovementType.RECEIPT,
            reference=f"create_batch {bid}", actor=actor,
        )
    batch.refresh_from_db()
    return batch


# --- Giữ chỗ (reservation) --------------------------------------------------

def allocate_fifo(*, item, qty):
    """
    Tính phân bổ FIFO cho `qty` kg của `item` từ các lô đang bán được (còn hạn, BR-LO-02).
    Trả list[(Batch, kg)]. KHÔNG thay đổi state (chỉ tính). Raise nếu không đủ.
    """
    qty = Decimal(qty)
    remaining = qty
    result = []
    for b in sellable_batches(item=item):
        sellable = b.qty_available - b.qty_reserved
        if sellable <= ZERO:
            continue
        take = min(sellable, remaining)
        result.append((b, take))
        remaining -= take
        if remaining <= ZERO:
            break
    if remaining > ZERO:
        raise BusinessError(
            f"Không đủ tồn khả dụng cho {item.code}: thiếu {remaining}kg (BR-BH-02)."
        )
    return result


def reserve(*, batch, qty):
    """Giữ chỗ ở mức lô — khoá lô cuối theo thứ tự tạo đơn (BR-BH-02)."""
    qty = Decimal(qty)
    with transaction.atomic():
        b = Batch.objects.select_for_update().get(pk=batch.pk)
        if (b.qty_available - b.qty_reserved) < qty:
            raise BusinessError(f"Lô {b.batch_id} không còn đủ để giữ chỗ (BR-BH-02).")
        b.qty_reserved += qty
        b.save(update_fields=["qty_reserved"])
    return b


def release(*, batch, qty):
    """Nhả giữ chỗ (huỷ đơn / hết TTL / chuyển thành bán thật)."""
    qty = Decimal(qty)
    with transaction.atomic():
        b = Batch.objects.select_for_update().get(pk=batch.pk)
        b.qty_reserved = max(ZERO, b.qty_reserved - qty)
        b.save(update_fields=["qty_reserved"])
    return b


# --- Vòng đời lô ------------------------------------------------------------

def publish_batch(*, batch, actor):
    """DRAFT -> SELLING (BR-MH-05). Kiểm perm publish_batch ở tầng API."""
    if batch.status != Batch.Status.DRAFT:
        raise BusinessError("Chỉ publish được lô đang ở trạng thái Nháp.", code="BR-MH-05")
    batch.status = Batch.Status.SELLING
    batch.save(update_fields=["status"])
    record_audit("publish_batch", actor=actor, obj=batch)
    return batch


def close_batch(*, batch, actor):
    """
    Chốt lô (BR-LO-04/05). Yêu cầu: tồn=0 (hoặc đã huỷ phần còn lại) và đã có
    Purchase Invoice. Đông cứng lãi/lỗ. Chỉ Chủ (perm close_batch kiểm ở API).
    """
    if batch.is_closed:
        raise BusinessError("Lô đã chốt.")
    if batch.qty_available > ZERO and batch.status not in (
        Batch.Status.EXPIRED, Batch.Status.CANCELLED
    ):
        raise BusinessError("Chốt lô yêu cầu tồn = 0 hoặc đã huỷ phần còn lại (BR-LO-04).")
    line = getattr(batch, "source_line", None)
    if line is not None and not line.receipt.invoices.exists():
        raise BusinessError("Cần có Purchase Invoice trước khi chốt lô (BR-MH-04/BR-LO-04).")
    batch.status = Batch.Status.CLOSED
    batch.closed_at = timezone.now()
    batch.closed_by = actor
    batch.save(update_fields=["status", "closed_at", "closed_by"])
    record_audit(
        "close_batch", actor=actor, obj=batch,
        changes={"landed_unit_cost": {"final": batch.landed_unit_cost}},
    )
    return batch


def recompute_landed_cost(*, batch, actor=None):
    """
    landed_unit_cost = (giá mua lô + Σ chi phí phân bổ) / qty_received (BR-GV-01).
    Mẫu số KHÔNG đổi theo hao hụt. Mỗi lần đổi ghi AuditLog (BR-GV-03).
    """
    if batch.qty_received <= ZERO:
        return batch
    alloc_total = sum(
        (a.allocated_amount for a in batch.cost_allocations.all()), ZERO
    )
    purchase_total = batch.purchase_rate * batch.qty_received
    new_cost = (purchase_total + alloc_total) / batch.qty_received
    old_cost = batch.landed_unit_cost
    if new_cost != old_cost:
        batch.landed_unit_cost = new_cost
        batch.save(update_fields=["landed_unit_cost"])
        record_audit(
            "recompute_landed_cost", actor=actor, obj=batch,
            changes={"landed_unit_cost": {"from": old_cost, "to": new_cost}},
        )
    return batch


# --- Job trạng thái lô theo hạn & tồn (S2) -----------------------------------

# Lô ở các trạng thái này do Hệ thống tự điều chỉnh. EXPIRED/CANCELLED/CLOSED là
# điểm cuối (BR-LO-03/05) — job không đụng tới.
AUTO_STATUSES = (
    Batch.Status.DRAFT, Batch.Status.SELLING, Batch.Status.NEAR_EXPIRY, Batch.Status.SOLD_OUT,
)
_STATUS_AUDIT_ACTION = {
    Batch.Status.NEAR_EXPIRY: "batch_near_expiry",
    Batch.Status.EXPIRED: "batch_expired",
    Batch.Status.SOLD_OUT: "batch_sold_out",
    Batch.Status.SELLING: "batch_selling",
}


def _status_audit_action(old, target):
    if old == Batch.Status.SOLD_OUT and target in SELLABLE_STATUSES:
        return "batch_back_in_stock"  # hàng hoàn tái nhập (BR-HV-02)
    return _STATUS_AUDIT_ACTION[target]


def _target_status(batch, *, today, near_cutoff):
    """Trạng thái lô NÊN có hôm nay; trả None nếu giữ nguyên."""
    s = batch.status
    has_stock = batch.qty_available > ZERO or batch.qty_reserved > ZERO
    if batch.expiry_date < today:  # hạn = ngày cuối còn bán (C1)
        if s == Batch.Status.SOLD_OUT and not has_stock:
            return None  # hết hàng rồi mới quá hạn: không còn gì để loại
        return Batch.Status.EXPIRED  # BR-LO-02
    if s == Batch.Status.DRAFT:
        return None  # chưa publish (BR-MH-05) — chỉ bị đổi khi quá hạn
    if not has_stock:
        return Batch.Status.SOLD_OUT
    if batch.expiry_date <= near_cutoff:
        return Batch.Status.NEAR_EXPIRY  # BR-LO-01: chỉ cảnh báo, không đổi giá
    return Batch.Status.SELLING


def update_batch_statuses(*, today=None):
    """
    Job hằng ngày (S2, BR-LO-01/02/06): chuyển lô sang Cận hạn / Quá hạn / Hết hàng,
    hoặc trả Hết hàng về Đang bán khi có hàng hoàn tái nhập (BR-HV-02).

    IDEMPOTENT: chỉ ghi khi trạng thái đích khác hiện tại, nên chạy lại cùng ngày
    không đổi gì và không sinh AuditLog. Actor = None (Hệ thống, BR-PQ-07).
    Không nhả giữ chỗ: đơn đã giữ chỗ trước nửa đêm vẫn xác nhận được (C1).
    Trả dict {trạng_thái_đích: số lô đã đổi}.
    """
    today = today or timezone.localdate()
    near_cutoff = today + datetime.timedelta(days=settings.BATCH_NEAR_EXPIRY_DAYS)
    changed = {}
    candidate_ids = list(
        Batch.objects.filter(status__in=AUTO_STATUSES).values_list("pk", flat=True)
    )
    for pk in candidate_ids:
        with transaction.atomic():
            b = Batch.objects.select_for_update().get(pk=pk)
            if b.status not in AUTO_STATUSES:
                continue  # đã bị người khác chốt/huỷ giữa chừng
            target = _target_status(b, today=today, near_cutoff=near_cutoff)
            if target is None or target == b.status:
                continue
            old = b.status
            b.status = target
            b.save(update_fields=["status"])
            record_audit(
                _status_audit_action(old, target), actor=None, obj=b,
                changes={"status": {"from": old, "to": target}},
                note=f"update_batch_status {today.isoformat()}",
            )
        changed[target] = changed.get(target, 0) + 1
    return changed
