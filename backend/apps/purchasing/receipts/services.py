"""
Ghi nhận phiếu nhập tại cảng -> sinh lô (P-02).

`submit_receipt`: mỗi dòng sinh MỘT lô riêng (BR-MH-01), hạn dùng chỉ được sửa XUỐNG
(BR-MH-02). Idempotent. Sinh lô qua `apps.inventory.batches.services.create_batch`.
"""
from django.db import transaction

from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batch_services


def submit_receipt(*, receipt, actor):
    """
    Ghi nhận phiếu nhập: mỗi PurchaseReceiptLine chưa có lô -> sinh MỘT lô riêng
    (BR-MH-01, không gộp lô). Trả list[Batch] của mọi dòng.

    - Hạn dùng lô = ngày nhập + shelf_life. Cho phép sửa tay XUỐNG thấp hơn mặc
      định của mặt hàng, KHÔNG cho cao hơn (BR-MH-02) -> vi phạm raise BusinessError.
    - Đặt receipt.status = SUBMITTED.
    - Idempotent: gọi lại không tạo lô trùng cho dòng đã có batch.
    """
    batches = []
    with transaction.atomic():
        # khoá phiếu để hai lần submit song song không tạo lô trùng
        lines = list(receipt.lines.select_for_update().select_related("item"))
        for line in lines:
            if line.batch_id is not None:
                # đã có lô -> giữ nguyên (idempotent), chỉ gom vào kết quả
                batches.append(line.batch)
                continue

            _validate_shelf_life(line)
            batch = batch_services.create_batch(
                item=line.item,
                supplier=receipt.supplier,
                warehouse=receipt.warehouse,
                received_date=receipt.received_date,
                qty=line.qty,
                purchase_rate=line.rate,
                shelf_life_days=line.shelf_life_days,
                actor=actor,
            )
            line.batch = batch
            line.save(update_fields=["batch"])
            batches.append(batch)

        if receipt.status != receipt.Status.SUBMITTED:
            receipt.status = receipt.Status.SUBMITTED
            receipt.save(update_fields=["status"])
    return batches


def _validate_shelf_life(line):
    """BR-MH-02: hạn dùng tay chỉ được <= mặc định của mặt hàng (không cho cao hơn)."""
    override = line.shelf_life_days
    if override is None:
        return
    default_days = line.item.shelf_life_in_days
    if default_days is not None and override > default_days:
        raise BusinessError(
            f"Hạn dùng {override} ngày vượt mặc định {default_days} ngày của "
            f"{line.item.code}: chỉ cho sửa xuống thấp hơn (BR-MH-02).",
            code="BR-MH-02",
        )


def create_and_submit_receipt(
    *,
    supplier,
    lines,
    actor,
    received_date=None,
    warehouse=None,
    idempotency_key=None,
):
    """
    Tạo và ghi nhận phiếu nhập tại cảng (DW-17, BR-MH-01, BR-MH-02, BR-MH-05).
    - Mỗi dòng sinh MỘT lô riêng (status DRAFT).
    - Idempotent: nếu cùng actor + idempotency_key đã tồn tại -> trả lại phiếu cũ và danh sách lô của nó.
    - Hạn dùng chỉ được sửa thấp hơn hoặc bằng mặc định của Item (BR-MH-02).
    - Ghi nhận AuditLog với actor_kind=user/ai.
    """
    if idempotency_key:
        from apps.purchasing.models import PurchaseReceipt
        existing = PurchaseReceipt.objects.filter(
            created_by=actor,
            idempotency_key=idempotency_key,
        ).first()
        if existing is not None:
            batches = [line.batch for line in existing.lines.select_related("batch") if line.batch_id]
            return existing, batches

    from django.utils import timezone
    from apps.common.audit import record_audit
    from apps.inventory.models import Warehouse
    from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine

    if warehouse is None:
        warehouse = Warehouse.objects.first()
        if warehouse is None:
            raise BusinessError("Chưa có kho nhận hàng nào trong hệ thống.", code="BR-MH-05")

    if received_date is None:
        received_date = timezone.localdate()  # L8-2: ngày nhập theo giờ VN, không phải ngày UTC

    # Kiểm tra trước BR-MH-02 cho tất cả các dòng
    for line_data in lines:
        item = line_data["item_code"]
        override = line_data.get("shelf_life_days")
        default_days = item.shelf_life_in_days
        if override is not None and default_days is not None and override > default_days:
            raise BusinessError(
                f"Hạn dùng {override} ngày vượt mặc định {default_days} ngày của "
                f"{item.code}: chỉ cho sửa xuống thấp hơn (BR-MH-02).",
                code="BR-MH-02",
            )

    with transaction.atomic():
        receipt = PurchaseReceipt.objects.create(
            supplier=supplier,
            warehouse=warehouse,
            received_date=received_date,
            status=PurchaseReceipt.Status.DRAFT,
            created_by=actor,
            idempotency_key=idempotency_key or None,
        )
        for line_data in lines:
            PurchaseReceiptLine.objects.create(
                receipt=receipt,
                item=line_data["item_code"],
                qty=line_data["qty"],
                rate=line_data["rate"],
                shelf_life_days=line_data.get("shelf_life_days"),
            )

        batches = submit_receipt(receipt=receipt, actor=actor)
        record_audit(
            "create_and_submit_receipt",
            actor=actor,
            obj=receipt,
            note=f"Nhà cung cấp {supplier.name}, {len(batches)} lô",
        )

    return receipt, batches


def cancel_receipt(*, receipt, actor):
    """
    Huỷ phiếu nhập kho khi mọi lô còn Nháp (DW-18, BR-MH-07, V-DW2).
    - Phân quyền V-DW2: Người tạo phiếu (phiếu của mình) HOẶC Quản lý/Chủ (mọi phiếu).
    - Trong transaction.atomic + select_for_update:
      - Kiểm tra phiếu chưa bị huỷ.
      - Kiểm tra chưa có PurchaseInvoice gắn với phiếu.
      - Khoá các dòng và các lô liên quan.
      - Kiểm tra từng lô: chưa phân bổ chi phí, trạng thái DRAFT, chưa xuất kho.
      - Đặt receipt.status = CANCELLED.
      - Với mỗi lô: ghi bút toán đảo WRITE_OFF cho phần tồn kho còn lại, đặt batch.status = CANCELLED.
      - Ghi AuditLog cancel_purchase_receipt.
    """
    from django.core.exceptions import PermissionDenied
    from apps.common.audit import record_audit
    from apps.inventory.models import Batch, StockLedgerEntry
    from apps.inventory.stock import services as stock
    from apps.purchasing.models import PurchaseReceipt

    is_creator = (receipt.created_by_id == actor.id)
    is_manager_or_owner = (
        actor.has_perm("purchasing.delete_purchasereceipt")
        or actor.groups.filter(name__in=["chu", "quan_ly"]).exists()
        or getattr(actor, "is_superuser", False)
    )
    if not (is_creator or is_manager_or_owner):
        raise PermissionDenied("Bạn không có quyền huỷ phiếu nhập này.")

    with transaction.atomic():
        receipt = PurchaseReceipt.objects.select_for_update().get(pk=receipt.pk)
        if receipt.status == PurchaseReceipt.Status.CANCELLED:
            raise BusinessError("Phiếu nhập đã bị huỷ.", code="BR-MH-07")

        if receipt.invoices.exists():
            raise BusinessError("Không thể huỷ phiếu nhập đã gắn hoá đơn mua.", code="BR-MH-07")

        lines = list(receipt.lines.select_for_update().select_related("batch"))
        batch_ids = [line.batch_id for line in lines if line.batch_id]
        batches = list(Batch.objects.select_for_update().filter(id__in=batch_ids))

        for batch in batches:
            if batch.cost_allocations.exists():
                raise BusinessError("Không thể huỷ phiếu nhập đã phân bổ chi phí mua hàng.", code="BR-MH-07")

            if batch.status != Batch.Status.DRAFT:
                raise BusinessError(
                    f"Lô {batch.batch_id} đã chuyển trạng thái {batch.get_status_display()}, không thể huỷ phiếu.",
                    code="BR-MH-07",
                )

            has_other_entries = batch.ledger_entries.exclude(
                movement_type=StockLedgerEntry.MovementType.RECEIPT
            ).exists()
            if batch.qty_available != batch.qty_received or has_other_entries:
                raise BusinessError(
                    f"Lô {batch.batch_id} đã phát sinh xuất kho, không thể huỷ phiếu.",
                    code="BR-MH-07",
                )

        receipt.status = PurchaseReceipt.Status.CANCELLED
        receipt.save(update_fields=["status"])

        for batch in batches:
            if batch.qty_available > 0:
                stock.record_movement(
                    batch=batch,
                    qty_change=-batch.qty_available,
                    movement_type=StockLedgerEntry.MovementType.WRITE_OFF,
                    reference=f"cancel_purchase_receipt PR-{receipt.pk}",
                    actor=actor,
                )
            batch.status = Batch.Status.CANCELLED
            batch.save(update_fields=["status"])

        record_audit(
            "cancel_purchase_receipt",
            actor=actor,
            obj=receipt,
            note=f"Huỷ phiếu nhập PR-{receipt.pk}, {len(batches)} lô đã huỷ",
        )

    return receipt

