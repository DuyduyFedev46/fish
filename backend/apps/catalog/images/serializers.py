"""Dựng JSON ảnh mặt hàng cho 3 nơi gọi: response upload, console (list/detail), Shop.

Không dùng `ModelSerializer` vì output là object lồng (`urls`) khác hình dạng model, và
Shop/console cần bớt field khác nhau (không rò `id` nội bộ, người tải, ngày tải ra Shop).
"""
from django.conf import settings
from django.utils import timezone

from .storage import get_storage


def _display_name(user):
    if user is None:
        return None
    profile = getattr(user, "staff_profile", None)
    if profile is not None and profile.display_name:
        return profile.display_name
    return user.get_username()


def image_urls(item_id, image_id) -> dict:
    storage = get_storage()
    return {
        size_name: storage.url(f"items/{item_id}/{image_id}/{size_name}.webp")
        for size_name in settings.ITEM_IMAGE_SIZES
    }


def serialize_item_image(image, *, include_uploaded_by=True):
    """Console (API nội bộ, A2 §Contract mục 1 & 2). `include_uploaded_by=False` cho danh
    sách/chi tiết mặt hàng (contract A2 mục 2: "bỏ uploaded_by")."""
    if image is None:
        return None
    data = {
        "id": image.image_id,
        "alt": image.alt_text,
        "is_illustration": image.is_illustration,
        "urls": image_urls(image.item_id, image.image_id),
        # B2: `updated_at` (không phải `created_at`) — phải là lần TẢI/THAY gần nhất, vì
        # thay ảnh (Q2, mỗi mặt hàng 1 ảnh) cập nhật cùng bản ghi, không tạo bản ghi mới.
        # B3: quy đổi sang giờ VN (Asia/Ho_Chi_Minh, +07:00) trước khi xuất ISO 8601 — DB
        # lưu UTC nên `.isoformat()` trực tiếp trả "+00:00", sai contract (`uploaded_at`
        # mẫu "...+07:00" ở 02-stories.md).
        "uploaded_at": timezone.localtime(image.updated_at).isoformat(),
    }
    if include_uploaded_by:
        data["uploaded_by"] = _display_name(image.uploaded_by)
    return data


def serialize_item_image_public(image):
    """Shop (A4): KHÔNG `id`, KHÔNG người tải/ngày tải, KHÔNG đường dẫn tệp gốc hay bucket
    nội bộ ngoài URL công khai (bất biến 1, BR-DM-15)."""
    if image is None:
        return None
    return {
        "alt": image.alt_text,
        "is_illustration": image.is_illustration,
        "urls": image_urls(image.item_id, image.image_id),
    }
