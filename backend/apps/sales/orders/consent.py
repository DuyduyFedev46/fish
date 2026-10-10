"""
Đồng ý chính sách quyền riêng tư khi đặt hàng (GL-03, BR-BH-17). Thứ tự lỗi theo 02b §3.3:
`SHOP_CLOSED` (503) đứng đầu, ô đồng ý chưa tick là `VALIDATION.fields.consent`, `POLICY_CHANGED` (409) sau `INVALID_QTY`.
"""
from django.conf import settings

from apps.common.exceptions import BusinessError

from .shop_errors import validation_error

CONSENT_MISSING_MESSAGE = "Đánh dấu đồng ý ở trên để đặt hàng."


class PolicyChanged(BusinessError):
    http_status = 409


class ShopClosed(BusinessError):
    http_status = 503


def _required() -> bool:
    return getattr(settings, "PRIVACY_CONSENT_REQUIRED", True)


def _current_policy():
    from apps.content.entries.services import current_policy_version

    return current_policy_version("privacy")


def ensure_shop_open():
    """Bước 1 của tạo đơn: chưa có chính sách đã đăng mà bắt buộc đồng ý -> 503 `SHOP_CLOSED`."""
    if _current_policy() is None and _required():
        raise ShopClosed("Shop tạm chưa nhận đơn.", code="SHOP_CLOSED")


def consent_field_error(payload) -> str | None:
    """Bước 2 (VALIDATION): câu lỗi cho ô đồng ý, hoặc `None` nếu hợp lệ / không bắt buộc."""
    if _current_policy() is None:
        return None
    if payload is None and not _required():
        return None  # GL-03-AC6
    if not isinstance(payload, dict) or payload.get("accepted") is not True:
        return CONSENT_MISSING_MESSAGE
    return None


def resolve_privacy_consent(payload):
    """
    Trả EntryVersion (để lưu vào đơn) hoặc None. Raise trước khi có bất kỳ ghi DB nào (BR-BH-17).
    """
    ensure_shop_open()
    current = _current_policy()
    if current is None:
        return None  # dev/test: không có chính sách -> bỏ qua

    message = consent_field_error(payload)
    if message:
        raise validation_error(consent=message)
    if payload is None:
        return None

    policy_version_id = payload.get("policy_version_id")
    # So sánh int tuyệt đối; kiểu chuỗi "918" cũng coi là lệch version
    if not isinstance(policy_version_id, int) or policy_version_id != current.pk:
        raise PolicyChanged(
            "Chính sách vừa cập nhật, vui lòng xem và đồng ý lại.",
            code="POLICY_CHANGED",
            extra={
                "current": {
                    "version": current.version,
                    "version_id": current.pk,
                    "slug": current.entry.slug,
                }
            },
        )

    return current
