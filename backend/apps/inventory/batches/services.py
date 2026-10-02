"""
Lô hàng: sinh lô, chọn lô FEFO + giữ chỗ, vòng đời, giá vốn lô, job trạng thái theo hạn (P-04).

Giữ chỗ tách khỏi tồn thật: `qty_reserved` (BR-BH-01/02). Chọn lô FEFO — hạn dùng sớm nhất
xuất trước, cùng hạn thì lô nhập trước, rồi lô tạo trước (BR-BH-05, decisions 2026-09-26). Tất cả hàm chạy trong transaction, dùng `select_for_update` để an
toàn khi hai khách tranh lô cuối (BR-BH-02, E-06). Biến động tồn đi qua
`apps.inventory.stock.services.record_movement`.
"""
import datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.common.pii import has_long_digit_run
from apps.inventory.models import (
    Batch,
    BatchSupplierReturn,
    ReturnToStock,
    StockLedgerEntry,
    StockReconciliation,
    StockReconciliationLine,
)
from apps.inventory.stock import services as stock


ZERO = Decimal("0")
SELLABLE_STATUSES = (Batch.Status.SELLING, Batch.Status.NEAR_EXPIRY)
# Thứ tự xuất FEFO (BR-BH-05): hạn dùng tăng dần → ngày nhập → lô tạo trước (id). Mọi chỗ chọn
# lô để bán hoặc hiển thị "thứ tự xuất" phải dùng khoá này (hoặc `sellable_batches`).
FEFO_ORDER = ("expiry_date", "received_date", "id")


def sellable_batches(*, item=None, on_date=None):
    """
    Nguồn DUY NHẤT cho "lô bán được" (BR-LO-02, S1): trạng thái SELLING/NEAR_EXPIRY
    **và** `expiry_date >= hôm nay` theo giờ Asia/Ho_Chi_Minh. `expiry_date` là ngày
    cuối còn bán (C1). Không phụ thuộc job `update_batch_status` — job chết thì lô
    quá hạn vẫn không bán được. Trả về theo thứ tự xuất FEFO (`FEFO_ORDER`, BR-BH-05).
    """
    on_date = on_date or timezone.localdate()
    qs = Batch.objects.filter(status__in=SELLABLE_STATUSES, expiry_date__gte=on_date)
    if item is not None:
        qs = qs.filter(item=item)
    return qs.order_by(*FEFO_ORDER)


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

def allocate_fefo(*, item, qty):
    """
    Tính phân bổ FEFO cho `qty` kg của `item` từ các lô đang bán được (còn hạn, BR-LO-02):
    lấy dần tồn khả dụng theo thứ tự `sellable_batches` (BR-BH-05/06). Trả list[(Batch, kg)].
    KHÔNG thay đổi state (chỉ tính). Raise nếu không đủ (BR-BH-02).
    Chỉ gọi lúc TẠO ĐƠN — thanh toán trừ đúng lô đã giữ, không chọn lại (BR-BH-11).
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


# Tên cũ (trước FEFO 2026-09-26) — giữ để không vỡ chỗ gọi ngoài; hành vi là FEFO.
allocate_fifo = allocate_fefo


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

@transaction.atomic
def publish_batch(*, batch, actor):
    """
    DRAFT -> SELLING (BR-MH-05). Kiểm perm publish_batch ở tầng API.
    Khoá dòng lô rồi ĐỌC LẠI trạng thái trước khi kiểm DRAFT (SR-10): object `batch` do
    caller đưa có thể đã cũ (phiếu nhập vừa huỷ ở request khác, `cancel_receipt` cũng khoá
    dòng lô) — không được mở bán lại lô đã huỷ.
    """
    b = Batch.objects.select_for_update().get(pk=batch.pk)
    if b.status != Batch.Status.DRAFT:
        raise BusinessError("Chỉ publish được lô đang ở trạng thái Nháp.", code="BR-MH-05")
    b.status = Batch.Status.SELLING
    b.save(update_fields=["status"])
    record_audit("publish_batch", actor=actor, obj=b)
    return b


# Trạng thái đơn bán hàng đang mở (chưa hoàn tất hoặc huỷ) tham chiếu lô (S04 / L-1, BR-LO-04)
OPEN_ORDER_STATUSES = ("BOOKED", "PAID", "PROCESSING")
# Đơn còn giữ chỗ (qty_reserved) trên lô: chỉ BOOKED — thanh toán xong là đã trừ kho (SR-08, BR-LO-07)
RESERVING_ORDER_STATUSES = ("BOOKED",)


def _open_orders_count(batch, statuses):
    """Số đơn (distinct) ở trạng thái `statuses` có dòng phân bổ tham chiếu `batch`."""
    from apps.sales.models import SalesOrderLineBatch
    return (
        SalesOrderLineBatch.objects.filter(
            batch=batch,
            order_line__order__status__in=statuses,
        )
        .values("order_line__order")
        .distinct()
        .count()
    )


def _fmt_kg(qty):
    """Định dạng số kg kiểu Việt: 2,000 (3 chữ số thập phân, dấu phẩy)."""
    return f"{Decimal(qty):.3f}".replace(".", ",")


def check_close_batch(batch):
    """
    Kiểm tra toàn bộ điều kiện nghiệp vụ để chốt lô (BR-LO-04/05, BR-KK-05).
    Trả list[Missing]. Rỗng nếu đủ điều kiện chốt.
    """
    from apps.common.guidance.steps import Missing

    missing: list[Missing] = []
    if batch.is_closed:
        missing.append(Missing("BR-LO-05", "Lô đã chốt."))
        return missing

    # SR-15 (P8 Lô 5, Duy duyệt 30/09): bỏ ngoại lệ tạm thời "chốt thẳng lô Quá hạn". Lô Quá hạn còn tồn
    # phải xử lý hết (Đã huỷ / Đã trả NCC, BR-LO-07) rồi mới chốt.
    if batch.qty_available > ZERO:
        missing.append(Missing("BR-LO-04", "Chốt lô yêu cầu tồn = 0 hoặc đã huỷ phần còn lại (BR-LO-04)."))

    if batch.qty_reserved > ZERO:
        missing.append(Missing("BR-LO-04", "Lô còn lượng giữ chỗ chưa giải phóng (BR-LO-04)."))

    open_orders_count = _open_orders_count(batch, OPEN_ORDER_STATUSES)  # L3: dùng chung với BR-LO-07
    if open_orders_count > 0:
        missing.append(Missing(
            "BR-LO-04",
            f"Còn {open_orders_count} đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04)."
        ))

    if ReturnToStock.objects.filter(batch=batch, status=ReturnToStock.Status.DRAFT).exists():
        missing.append(Missing("BR-LO-04", "Còn phiếu hàng hoàn đang chờ duyệt tham chiếu lô (BR-LO-04)."))

    line = getattr(batch, "source_line", None)
    if line is not None and not line.receipt.invoices.exists():
        missing.append(Missing("BR-LO-04", "Cần có Purchase Invoice trước khi chốt lô (BR-MH-04/BR-LO-04)."))

    has_approved_recon = StockReconciliationLine.objects.filter(
        batch=batch,
        reconciliation__status=StockReconciliation.Status.APPROVED,
    ).exists()
    has_draft_recon = StockReconciliationLine.objects.filter(
        batch=batch,
        reconciliation__status__in=(StockReconciliation.Status.DRAFT, StockReconciliation.Status.SUBMITTED),
    ).exists()
    if not has_approved_recon or has_draft_recon:
        missing.append(Missing("BR-KK-05", "Lô phải được kiểm kê và duyệt trước khi chốt (BR-KK-05)."))

    return missing


@transaction.atomic
def close_batch(*, batch, actor):
    """
    Chốt lô (BR-LO-04/05, BR-KK-05). Yêu cầu:
    - Chưa chốt (BR-LO-05)
    - Tồn = 0, kể cả lô Quá hạn (BR-LO-04, SR-15: bỏ ngoại lệ S04)
    - Không còn lượng giữ chỗ qty_reserved > 0 (BR-LO-04)
    - Không còn đơn mở BOOKED, PAID, PROCESSING (BR-LO-04)
    - Không có phiếu hàng hoàn DRAFT (BR-LO-04, BR-LO-05)
    - Đã có Purchase Invoice nếu nhập từ PO (BR-MH-04/BR-LO-04)
    - Đã kiểm kê và duyệt (APPROVED), không có phiếu kiểm kê DRAFT (BR-KK-05)
    Đông cứng lãi/lỗ. Chỉ Chủ (perm close_batch kiểm ở API).
    """
    batch = Batch.objects.select_for_update().get(pk=batch.pk)
    missing = check_close_batch(batch)
    if missing:
        raise BusinessError(missing[0].text, code=missing[0].code)

    batch.status = Batch.Status.CLOSED
    batch.closed_at = timezone.now()
    batch.closed_by = actor
    batch.save(update_fields=["status", "closed_at", "closed_by"])
    record_audit(
        "close_batch", actor=actor, obj=batch,
        changes={"landed_unit_cost": {"final": batch.landed_unit_cost}},
    )
    return batch


def _check_expired_reserved(batch):
    """Lô EXPIRED còn giữ chỗ của đơn BOOKED -> [Missing BR-LO-07] (SR-08), else []."""
    from apps.common.guidance.steps import Missing

    # SR-08 / BR-LO-07: còn giữ chỗ của đơn BOOKED thì chưa xử lý phần tồn — huỷ/trả sẽ xoá tồn mà đơn
    # khách vẫn đang giữ, thanh toán sau đó văng "Xuất vượt tồn" và mất giao dịch tiền.
    # Không tự nhả giữ chỗ / huỷ đơn khách; giữ chỗ tự hết theo TTL.
    if batch.qty_reserved > ZERO:
        n = _open_orders_count(batch, RESERVING_ORDER_STATUSES)
        return [Missing(
            "BR-LO-07",
            f"Còn {_fmt_kg(batch.qty_reserved)} kg đang giữ chỗ của {n} đơn — "
            "chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ.",
        )]
    return []


def check_cancel_expired_batch(batch):
    """
    Kiểm tra điều kiện huỷ lô quá hạn (BR-LO-03, BR-LO-07, DW-06).
    Chỉ huỷ được lô khi đang ở trạng thái EXPIRED (Quá hạn) và không còn giữ chỗ.
    Cho phép tồn 0 (huỷ lô đã trả hết NCC vẫn hợp lệ để kết thúc lô).
    """
    from apps.common.guidance.steps import Missing

    if batch.status != Batch.Status.EXPIRED:
        return [Missing("BR-LO-03", "Chỉ huỷ được lô Quá hạn.")]
    return _check_expired_reserved(batch)


def check_process_expired_stock(batch):
    """
    Điều kiện xác nhận "Đã trả NCC" phần tồn lô Quá hạn (BR-LO-07, BR-MH-08, SR-16).
    Như huỷ lô quá hạn nhưng còn phải CÒN TỒN (qty_available > 0) và lô chưa chốt (BR-LO-05).
    """
    from apps.common.guidance.steps import Missing

    if batch.is_closed:
        return [Missing("BR-LO-05", "Lô đã chốt.")]
    if batch.status != Batch.Status.EXPIRED or batch.qty_available <= ZERO:
        return [Missing("BR-LO-07", "Chỉ xác nhận trả NCC cho lô Quá hạn còn tồn.")]
    return _check_expired_reserved(batch)


def cancel_expired_batch(*, batch, actor, confirm_qty=None):
    """
    Huỷ lô quá hạn (EXPIRED -> CANCELLED, BR-LO-03, BR-LO-07, DW-06).
    - transaction.atomic + select_for_update TRƯỚC mọi phép kiểm.
    - `confirm_qty` (tuỳ chọn, SR-15): số kg người dùng đang thấy trên màn hình; lệch tồn hiện tại
      (vd vừa trả NCC một phần ở tab khác) -> 400 BR-LO-07, không huỷ.
    - Ghi StockLedgerEntry WRITE_OFF âm đúng lượng tồn còn lại (append-only).
    - Status chuyển CANCELLED.
    - Ghi AuditLog 1 dòng với loss_amount nếu có tồn.
    """
    with transaction.atomic():
        b = Batch.objects.select_for_update().get(pk=batch.pk)
        missing = check_cancel_expired_batch(b)
        if missing:
            raise BusinessError(missing[0].text, code=missing[0].code)

        if confirm_qty not in (None, ""):
            try:
                confirmed = Decimal(str(confirm_qty))
                if not confirmed.is_finite():
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                raise BusinessError("Số kg xác nhận không hợp lệ.", code="BR-LO-07")
            if confirmed != b.qty_available:
                raise BusinessError(
                    f"Tồn đã đổi ({_fmt_kg(b.qty_available)} kg) — tải lại.", code="BR-LO-07"
                )

        remaining_qty = b.qty_available
        if remaining_qty > ZERO:
            stock.record_movement(
                batch=b,
                qty_change=-remaining_qty,
                movement_type=StockLedgerEntry.MovementType.WRITE_OFF,
                reference=f"cancel_expired_batch {b.batch_id}",  # F11: batch_pnl đếm expired_qty theo tiền tố này
                actor=actor,
            )
        b.refresh_from_db()
        old_status = b.status
        b.status = Batch.Status.CANCELLED
        b.save(update_fields=["status"])
        loss_amount = remaining_qty * b.landed_unit_cost
        record_audit(
            "cancel_expired_batch",
            actor=actor,
            obj=b,
            changes={
                "status": {"from": old_status, "to": Batch.Status.CANCELLED},
                "loss_amount": loss_amount,
                "qty": remaining_qty,
            },
            note=f"cancel_expired_batch {remaining_qty}kg",
        )
    return b


SUPPLIER_RETURN_NOTE_MAX = 500
_MONEY_MAX = Decimal("1000000000000")  # 14 chữ số nguyên khớp max_digits=14, decimal_places=2


def _parse_decimal(value):
    """Decimal hữu hạn hoặc None (chuỗi rác, NaN, Infinity, bool, None)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


@transaction.atomic
def return_batch_to_supplier(*, batch, qty, supplier_refund_amount, note, request_id, actor):
    """
    Xác nhận "Đã trả NCC" một phần/toàn bộ tồn lô Quá hạn (BR-LO-07, BR-MH-08, SR-16).
    - `request_id` trùng bản ghi cũ -> trả bản ghi cũ, KHÔNG trừ kho lần 2 (chống bấm đúp/gửi lại).
    - Khoá dòng lô rồi kiểm điều kiện (`check_process_expired_stock`), 0 < qty <= tồn, tiền >= 0.
    - Ghi BatchSupplierReturn + StockLedgerEntry SUPPLIER_RETURN âm; lô vẫn EXPIRED (có thể còn tồn
      để huỷ tiếp hoặc về 0 để chốt).
    - Tiền NCC hoàn nhạy cảm: chỉ vào `changes` của AuditLog (khoá thuộc COST_KEYS -> quan_ly không thấy);
      `note` audit không chứa ghi chú tự do/tiền để không lọt qua Nhật ký.
    - KHÔNG tính lại landed_unit_cost (tránh lệch giá vốn ảnh chụp của hoá đơn đã bán); tiền hoàn chỉ
      giảm total_cost lô ở `batch_pnl`.
    """
    b = Batch.objects.select_for_update().get(pk=batch.pk)
    if request_id is not None:
        # Sau khi khoá lô: hai request cùng request_id tuần tự hoá ở đây, request sau thấy bản ghi của request trước.
        existing = BatchSupplierReturn.objects.filter(request_id=request_id).first()
        if existing is not None:
            if existing.batch_id != b.pk:
                raise BusinessError("Mã yêu cầu đã được dùng cho lô khác.", code="BR-MH-08")
            return existing
    missing = check_process_expired_stock(b)
    if missing:
        raise BusinessError(missing[0].text, code=missing[0].code)

    qty_d = _parse_decimal(qty)
    if qty_d is None or qty_d <= ZERO or qty_d > b.qty_available or qty_d != qty_d.quantize(Decimal("0.001")):
        raise BusinessError(
            f"Số kg trả phải lớn hơn 0 và không vượt tồn {_fmt_kg(b.qty_available)} kg.", code="BR-MH-08"
        )
    refund = _parse_decimal(supplier_refund_amount if supplier_refund_amount not in (None, "") else "0")
    if refund is None or refund < ZERO or refund >= _MONEY_MAX or refund != refund.quantize(Decimal("0.01")):
        raise BusinessError("Tiền NCC hoàn phải là số không âm, tối đa 2 chữ số thập phân.", code="BR-MH-08")
    note = (note or "").strip()
    if len(note) > SUPPLIER_RETURN_NOTE_MAX:
        raise BusinessError(f"Ghi chú tối đa {SUPPLIER_RETURN_NOTE_MAX} ký tự.", code="BR-MH-08")
    if has_long_digit_run(note):
        raise BusinessError("Ghi chú không được chứa dãy số dài (số điện thoại, số tài khoản).", code="BR-MH-08")

    rec = BatchSupplierReturn.objects.create(
        batch=b, qty=qty_d, supplier_refund_amount=refund, note=note,
        request_id=request_id, created_by=actor,
    )
    stock.record_movement(
        batch=b,
        qty_change=-qty_d,
        movement_type=StockLedgerEntry.MovementType.SUPPLIER_RETURN,
        reference=f"supplier_return SR-{rec.pk}",
        actor=actor,
    )
    record_audit(
        "return_batch_to_supplier",
        actor=actor,
        obj=b,
        changes={"qty": qty_d, "supplier_refund_amount": refund},
        note=f"return_batch_to_supplier {qty_d}kg",
    )
    return rec


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
