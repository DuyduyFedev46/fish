from django.conf import settings
from apps.common.exceptions import BusinessError


class PolicyChanged(BusinessError):
    http_status = 409


class ShopClosed(BusinessError):
    http_status = 503


def resolve_privacy_consent(payload):
    """
    Trả EntryVersion (để lưu vào đơn) hoặc None.
    Raise trước khi có bất kỳ ghi DB nào (BR-BH-17).
    """
    from apps.content.entries.services import current_policy_version

    current = current_policy_version("privacy")
    required = getattr(settings, "PRIVACY_CONSENT_REQUIRED", True)

    if current is None:
        if required:
            raise ShopClosed("Shop tạm chưa nhận đơn.", code="BR-BH-17")
        return None  # dev/test: không có chính sách -> bỏ qua

    if payload is None and not required:
        return None  # GL-03-AC6

    if not isinstance(payload, dict) or payload.get("accepted") is not True:
        raise BusinessError("Vui lòng đồng ý chính sách xử lý dữ liệu cá nhân.", code="BR-BH-17")

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
