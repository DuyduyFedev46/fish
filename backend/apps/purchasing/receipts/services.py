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
        received_date = timezone.now().date()

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
