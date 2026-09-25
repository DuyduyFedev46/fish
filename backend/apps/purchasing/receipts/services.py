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
            f"{line.item.code}: chỉ cho sửa xuống thấp hơn (BR-MH-02)."
        )
