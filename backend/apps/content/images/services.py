"""Dịch vụ tải và xử lý ảnh bài viết giữ tỉ lệ (§7 02b-tech-design)."""
from django.conf import settings
from apps.common.exceptions import BusinessError
from apps.catalog.images.processing import process_image_keep_ratio, InvalidImageError
from apps.catalog.images.storage import get_storage
from apps.catalog.models.images import generate_image_id
from apps.content.models.images import ContentImage
from apps.content.models.entries import Entry


def upload_content_image(*, entry: Entry, file, alt: str = "", actor) -> ContentImage:
    """
    Tải ảnh cho bài viết:
    - Kiểm dung lượng theo ITEM_IMAGE_MAX_BYTES (10 MB, lỗi BR-DM-10)
    - Kiểm tra giới hạn số ảnh (BR-ND-07)
    - Xử lý giữ tỉ lệ, gỡ EXIF/GPS, xuất 3 cỡ WebP
    - Lưu vào bucket kho dưới tiền tố content/<entry_id>/<image_id>/
    - Tạo bản ghi ContentImage
    """
    max_bytes = getattr(settings, "ITEM_IMAGE_MAX_BYTES", 10 * 1024 * 1024)
    file_size = getattr(file, "size", 0)
    if file_size > max_bytes:
        raise BusinessError("Dung lượng ảnh vượt quá 10MB (BR-DM-10).", code="BR-DM-10")

    # Giới hạn tổng số lần tải ảnh/bài (100)
    max_uploads = getattr(settings, "CONTENT_MAX_IMAGE_UPLOADS_PER_ENTRY", 100)
    if ContentImage.objects.filter(entry=entry).count() >= max_uploads:
        raise BusinessError("Số lượt tải ảnh của bài đã đạt giới hạn (BR-ND-07).", code="BR-ND-07")

    # Giới hạn số ảnh đang dùng trong bài + bìa (20)
    max_images_per_entry = getattr(settings, "CONTENT_MAX_IMAGES_PER_ENTRY", 20)
    used_image_ids = set()
    if entry.cover_image_id:
        used_image_ids.add(entry.cover_image_id)
    if isinstance(entry.body, dict) and isinstance(entry.body.get("blocks"), list):
        for b in entry.body.get("blocks", []):
            if isinstance(b, dict) and b.get("type") == "image" and isinstance(b.get("image_id"), int):
                used_image_ids.add(b["image_id"])

    if len(used_image_ids) >= max_images_per_entry:
        raise BusinessError("Bài viết đã đạt giới hạn 20 ảnh (BR-ND-07).", code="BR-ND-07")

    # Đọc raw bytes
    try:
        raw = file.read()
    except Exception as exc:
        raise BusinessError("Không thể đọc tệp ảnh (BR-DM-10).", code="BR-DM-10") from exc

    if len(raw) > max_bytes:
        raise BusinessError("Dung lượng ảnh vượt quá 10MB (BR-DM-10).", code="BR-DM-10")

    # Xử lý ảnh giữ tỉ lệ
    widths = getattr(settings, "CONTENT_IMAGE_WIDTHS", {"sm": 480, "md": 960, "lg": 1600})
    try:
        processed = process_image_keep_ratio(raw, widths=widths)
    except InvalidImageError as exc:
        raise BusinessError(f"Tệp ảnh không hợp lệ: {exc} (BR-DM-10).", code="BR-DM-10") from exc

    # Lưu vào storage
    image_id = generate_image_id()
    storage = get_storage()
    for size_name, data in processed.sizes.items():
        object_name = f"content/{entry.pk}/{image_id}/{size_name}.webp"
        try:
            storage.save(object_name, data, "image/webp")
        except Exception as exc:
            raise BusinessError("Lỗi hệ thống lưu trữ ảnh (BR-DM-16).", code="BR-DM-16", status_code=503) from exc


    # Alt text mặc định
    clean_alt = (alt or "").strip()
    if not clean_alt:
        clean_alt = (entry.title or "").strip()[:200]
    if not clean_alt:
        clean_alt = "Ảnh minh hoạ bài viết"

    image = ContentImage.objects.create(
        entry=entry,
        image_id=image_id,
        alt=clean_alt[:200],
        width=processed.width,
        height=processed.height,
        uploaded_by=actor,
    )
    return image


def update_image_alt(*, image: ContentImage, alt: str, actor) -> ContentImage:
    """Cập nhật alt text của ảnh bài viết (tối đa 200 ký tự)."""
    image.alt = (alt or "").strip()[:200]
    image.save(update_fields=["alt"])
    return image
