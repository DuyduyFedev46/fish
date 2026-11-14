"""
Phát hành và kiểm tra `preview_token` có chữ ký số cho quy trình nhập mặt hàng từ Excel (FISH-66, 02b §5.1, §5.3).

- Dùng `django.core.signing.dumps` / `loads` (`salt="catalog.item_files.import"`, `compress=True`), không cần bảng DB hay Redis.
- Hạn kiểm bằng `t` ở bước 5 (sau khi kiểm `import_ref` ở bước 4 trong `commit_import`).
"""
import datetime
import time
import uuid

from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.common.exceptions import BusinessError

TOKEN_SALT = "catalog.item_files.import"
TOKEN_VERSION = 1

PREVIEW_INVALID_MSG = "File khác với file đã xem trước. Bấm Xem trước lại."
PREVIEW_EXPIRED_MSG = "Phiên xem trước đã hết hạn. Chưa ghi gì. Bấm Xem trước lại."


def issue_preview_token(
    *,
    user_id: int,
    file_sha256: str,
    data_fingerprint: str,
    now: int | None = None,
) -> tuple[str, str, str]:
    """
    Trả `(preview_token, expires_at_iso, import_ref)`.
    `expires_at_iso` định dạng ISO-8601 theo múi giờ cấu hình (`Asia/Ho_Chi_Minh`).
    """
    issued_at = int(now if now is not None else time.time())
    ttl_seconds = int(settings.ITEM_IMPORT_PREVIEW_TTL_MINUTES) * 60
    expires_ts = issued_at + ttl_seconds
    import_ref = uuid.uuid4().hex

    payload = {
        "v": TOKEN_VERSION,
        "u": int(user_id),
        "h": str(file_sha256),
        "d": str(data_fingerprint),
        "n": import_ref,
        "t": issued_at,
    }
    token = signing.dumps(payload, salt=TOKEN_SALT, compress=True)
    expires_dt = timezone.localtime(
        datetime.datetime.fromtimestamp(expires_ts, tz=datetime.timezone.utc)
    )
    return token, expires_dt.isoformat(), import_ref


def verify_preview_token_signature(
    token: str,
    *,
    user_id: int,
    file_sha256: str | None = None,
) -> dict:
    """
    Bước 2 (§5.3): Giải mã và kiểm chữ ký `preview_token`, `u == user_id`, và `h == file_sha256`.
    Chưa kiểm hạn `t` ở đây để bước 4 kiểm `IMPORT_ALREADY_APPLIED` chạy trước bước 5 kiểm hết hạn.
    """
    if not token or not isinstance(token, str):
        raise BusinessError(PREVIEW_INVALID_MSG, code="IMPORT_PREVIEW_INVALID")
    try:
        payload = signing.loads(token, salt=TOKEN_SALT)
    except signing.BadSignature as exc:
        raise BusinessError(PREVIEW_INVALID_MSG, code="IMPORT_PREVIEW_INVALID") from exc

    if not isinstance(payload, dict) or payload.get("v") != TOKEN_VERSION:
        raise BusinessError(PREVIEW_INVALID_MSG, code="IMPORT_PREVIEW_INVALID")
    if payload.get("u") != int(user_id):
        raise BusinessError(PREVIEW_INVALID_MSG, code="IMPORT_PREVIEW_INVALID")
    if not payload.get("n") or not payload.get("d") or not payload.get("h"):
        raise BusinessError(PREVIEW_INVALID_MSG, code="IMPORT_PREVIEW_INVALID")
    if file_sha256 is not None and payload.get("h") != str(file_sha256):
        raise BusinessError(PREVIEW_INVALID_MSG, code="IMPORT_PREVIEW_INVALID")
    return payload


def check_preview_token_expiry(payload: dict, *, now: int | None = None) -> None:
    """Bước 5 (§5.3): Kiểm hạn `t` của phiếu xem trước. Quá hạn → 410 `IMPORT_PREVIEW_EXPIRED`."""
    current_ts = int(now if now is not None else time.time())
    issued_at = int(payload.get("t") or 0)
    ttl_seconds = int(settings.ITEM_IMPORT_PREVIEW_TTL_MINUTES) * 60
    if current_ts - issued_at > ttl_seconds:
        raise BusinessError(
            PREVIEW_EXPIRED_MSG,
            code="IMPORT_PREVIEW_EXPIRED",
            status_code=410,
        )
