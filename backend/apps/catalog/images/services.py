"""
Nghiệp vụ ảnh mặt hàng — thêm/thay (A2, UC-A1), gỡ (A3, UC-A2). BR-DM-09..16.

Mỗi mặt hàng đúng 1 ảnh (Q2, `ItemImage` 1-1 với `Item`). Ảnh không phải chứng từ
(BR-PQ-10 không áp dụng): thay/gỡ chỉ đổi bản ghi `ItemImage`, KHÔNG xoá object cũ ở
storage (BR-DM-14) — tầng storage không có thao tác xoá. Mọi thêm/thay/gỡ ghi AuditLog
(BR-DM-12, mở rộng BR-PQ-04 sang catalog — thay đổi hiển thị công khai đầu tiên).
"""
from dataclasses import dataclass, field

from django.conf import settings
from django.db import transaction

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError

from . import processing
from .storage import get_storage

MAX_ALT_LEN = 125
LOW_RESOLUTION_WARNING = {
    "code": "LOW_RESOLUTION",
    "message": "Ảnh nhỏ hơn 600 px, trên Shop có thể bị mờ.",
}


class ItemImageConflict(BusinessError):
    """409 — `expected_image_id` không khớp ảnh hiện tại (BR-DM-12, UC-A1 E6)."""

    http_status = 409

    def __init__(self, message="Ảnh vừa được người khác đổi, tải lại để xem."):
        super().__init__(message, code="BR-DM-12")


class ItemImageNotFound(BusinessError):
    """404 — gỡ ảnh khi mặt hàng chưa có ảnh nào (BR-DM-09, A3-AC4)."""

    http_status = 404

    def __init__(self, message="Mặt hàng chưa có ảnh."):
        super().__init__(message, code="BR-DM-09")


@dataclass
class UploadOutcome:
    image: object
    created: bool
    warnings: list = field(default_factory=list)


def _current_image(item):
    from apps.catalog.models.images import ItemImage

    try:
        return item.image
    except ItemImage.DoesNotExist:
        return None


def _check_expected_image(item, expected_image_id):
    """`expected_image_id is None` = FE không gửi field -> bỏ qua kiểm tra khoá lạc quan."""
    if expected_image_id is None:
        return
    current = _current_image(item)
    current_id = current.image_id if current else ""
    if str(expected_image_id) != current_id:
        raise ItemImageConflict()


def _validate_alt_text(alt_text):
    if alt_text and len(alt_text) > MAX_ALT_LEN:
        raise BusinessError(
            f"Alt text vượt quá {MAX_ALT_LEN} ký tự (BR-DM-11).", code="BR-DM-11"
        )


def _validate_file(file):
    if file is None:
        raise BusinessError("Thiếu tệp ảnh (BR-DM-10).", code="BR-DM-10")
    max_bytes = getattr(settings, "ITEM_IMAGE_MAX_BYTES", 10 * 1024 * 1024)
    size = getattr(file, "size", None)
    if size is None:
        pos = file.tell()
        file.seek(0, 2)
        size = file.tell()
        file.seek(pos)
    if size > max_bytes:
        limit_mb = max_bytes / (1024 * 1024)
        raise BusinessError(
            f"Ảnh vượt {limit_mb:.0f} MB (BR-DM-10).", code="BR-DM-10"
        )


@transaction.atomic
def upload_item_image(
    *,
    item,
    file,
    alt_text="",
    is_illustration=False,
    expected_image_id=None,
    actor=None,
    storage=None,
):
    """Thêm ảnh lần đầu (`item_image_add`) hoặc thay ảnh (`item_image_replace`).

    Thứ tự kiểm: định dạng/dung lượng tệp (BR-DM-10) -> alt text (BR-DM-11) -> khoá lạc
    quan (BR-DM-12) -> xử lý ảnh -> ghi storage. Lỗi ở bất kỳ bước nào không đổi gì trên
    `item` và không ghi AuditLog (transaction.atomic).
    """
    from apps.catalog.models.images import ItemImage, generate_image_id

    _validate_file(file)
    _validate_alt_text(alt_text)
    _check_expected_image(item, expected_image_id)

    raw = file.read()
    try:
        processed = processing.process_item_image(raw, sizes=settings.ITEM_IMAGE_SIZES)
    except processing.InvalidImageError as exc:
        raise BusinessError(
            f"{exc} Chỉ nhận ảnh JPEG, PNG hoặc WebP (BR-DM-10).", code="BR-DM-10"
        ) from exc

    active_storage = storage or get_storage()
    new_image_id = generate_image_id()
    for size_name, data in processed.sizes.items():
        # Lỗi ở đây (ItemImageStorageError, 503) lăn ra ngoài transaction.atomic -> rollback,
        # không có object nào được coi là "đã lưu" ở tầng DB (UC-A1 E5, A2-AC11).
        active_storage.save(f"items/{item.pk}/{new_image_id}/{size_name}.webp", data, "image/webp")

    current = _current_image(item)
    old_image_id = current.image_id if current else None
    old_illustration = current.is_illustration if current else None
    resolved_alt = (alt_text or "").strip() or item.name
    resolved_alt = resolved_alt[:MAX_ALT_LEN]

    if current is None:
        image = ItemImage.objects.create(
            item=item,
            image_id=new_image_id,
            alt_text=resolved_alt,
            is_illustration=is_illustration,
            uploaded_by=actor,
        )
        created = True
        action = "item_image_add"
    else:
        current.image_id = new_image_id
        current.alt_text = resolved_alt
        current.is_illustration = is_illustration
        current.uploaded_by = actor
        current.save(
            update_fields=["image_id", "alt_text", "is_illustration", "uploaded_by", "updated_at"]
        )
        image = current
        created = False
        action = "item_image_replace"

    record_audit(
        action,
        actor=actor,
        obj=item,
        changes={
            "image_id": [old_image_id, new_image_id],
            "is_illustration": [old_illustration, is_illustration],
        },
    )

    warnings = []
    min_side_warn = getattr(settings, "ITEM_IMAGE_MIN_SIDE_WARN", 600)
    if processed.source_side < min_side_warn:
        warnings.append(dict(LOW_RESOLUTION_WARNING))
    return UploadOutcome(image=image, created=created, warnings=warnings)


@transaction.atomic
def remove_item_image(*, item, expected_image_id=None, actor=None):
    """Gỡ ảnh (A3, UC-A2). Không xoá object ở storage (BR-DM-14)."""
    current = _current_image(item)
    if current is None:
        raise ItemImageNotFound()
    _check_expected_image(item, expected_image_id)
    old_image_id = current.image_id
    current.delete()
    record_audit(
        "item_image_remove",
        actor=actor,
        obj=item,
        changes={"image_id": [old_image_id, None]},
    )
