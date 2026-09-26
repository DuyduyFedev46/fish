"""
Kho lưu trữ ảnh mặt hàng — trừu tượng hoá qua `ITEM_IMAGE_STORAGE` (A1).

- `local` (mặc định dev/test): ghi vào `MEDIA_ROOT`. KHÔNG gọi mạng ra GCS — bắt buộc
  cho CI/máy dev không có credential GCS (A1-AC6).
- `gcs` (staging/production): Cloud Storage, bucket `ITEM_IMAGE_BUCKET`. Object đọc công
  khai qua IAM `roles/storage.legacyObjectReader` cho `allUsers` (cấu hình hạ tầng, xem
  `doc/ops/moi-truong.md`) — code chỉ ghi (SA Cloud Run chỉ có `roles/storage.objectCreator`,
  không có quyền xoá, BR-DM-14).

Ảnh cũ KHÔNG bao giờ bị xoá ở tầng này (thay/gỡ chỉ đổi bản ghi `ItemImage`, object cũ ở
storage vẫn còn — BR-DM-14, dọn sau 30 ngày để sau).
"""
import os

from django.conf import settings

from apps.common.exceptions import BusinessError

CACHE_CONTROL = "public, max-age=31536000, immutable"  # URL không bao giờ bị ghi đè (A2-AC4)


class ItemImageStorageError(BusinessError):
    """503 — kho ảnh không ghi được (A2-AC11, UC-A1 E5, BR-DM-16)."""

    http_status = 503

    def __init__(self, message="Chưa lưu được ảnh, thử lại."):
        super().__init__(message, code="BR-DM-16")


class LocalItemImageStorage:
    """Dev/test: ghi file vào `MEDIA_ROOT/<path>`, phục vụ qua `ITEM_IMAGE_PUBLIC_BASE_URL`."""

    def save(self, path: str, data: bytes, content_type: str) -> str:
        media_root = str(getattr(settings, "MEDIA_ROOT", "") or "")
        if not media_root:
            raise ItemImageStorageError("Thiếu cấu hình MEDIA_ROOT (ITEM_IMAGE_STORAGE=local).")
        full_path = os.path.join(media_root, path)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as fh:
                fh.write(data)
        except OSError as exc:
            raise ItemImageStorageError() from exc
        return self.url(path)

    def url(self, path: str) -> str:
        base = str(settings.ITEM_IMAGE_PUBLIC_BASE_URL).rstrip("/")
        return f"{base}/{path}"


class GCSItemImageStorage:
    """Staging/production. Import `google-cloud-storage` bên trong hàm để dev/test không
    cần cài thư viện này (chỉ cần khi `ITEM_IMAGE_STORAGE=gcs`, xem 03-dev-notes.md)."""

    def save(self, path: str, data: bytes, content_type: str) -> str:
        bucket_name = getattr(settings, "ITEM_IMAGE_BUCKET", "")
        if not bucket_name:
            raise ItemImageStorageError("Thiếu cấu hình ITEM_IMAGE_BUCKET.")
        try:
            from google.cloud import storage as gcs_storage  # phụ thuộc chỉ cần ở gcs

            client = gcs_storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(path)
            blob.cache_control = CACHE_CONTROL
            blob.upload_from_string(data, content_type=content_type)
        except ItemImageStorageError:
            raise
        except Exception as exc:  # network / auth / quota... -> 503 đồng nhất (UC-A1 E5)
            raise ItemImageStorageError() from exc
        return self.url(path)

    def url(self, path: str) -> str:
        base = str(settings.ITEM_IMAGE_PUBLIC_BASE_URL).rstrip("/")
        return f"{base}/{path}"


def get_storage():
    backend = str(getattr(settings, "ITEM_IMAGE_STORAGE", "local")).strip().lower()
    if backend == "gcs":
        return GCSItemImageStorage()
    return LocalItemImageStorage()
