"""Khách hàng (7.1): guest checkout — gộp/khởi tạo Customer theo số điện thoại; sửa hồ sơ ở danh bạ (B2)."""
from django.db import transaction

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.sales.models import Customer


def get_or_create_by_phone(*, phone, name="", default_address=""):
    """
    Số điện thoại là khoá tự nhiên của khách. Khách cũ chưa có tên thì điền tên mới;
    không ghi đè tên/địa chỉ đã có. Gọi bên trong transaction của create_order.
    """
    customer, created = Customer.objects.get_or_create(
        phone=phone,
        defaults={"name": name or "", "default_address": default_address or ""},
    )
    if not created and name and not customer.name:
        customer.name = name
        customer.save(update_fields=["name"])
    return customer


# B2 (BR-PQ-31): Chủ/Quản lý sửa hồ sơ khách ở danh bạ. SĐT là khoá tự nhiên nên KHÔNG nằm trong danh sách này.
EDITABLE_PROFILE_FIELDS = ("name", "default_address", "note")


class _CustomerAuditRef:
    """Đối tượng thay thế cho `record_audit(obj=...)`: `str(Customer)` chứa tên + SĐT nên không được chép vào
    `AuditLog.object_repr` (bất biến 9). Ở đây chỉ có nhãn model, mã khách và chuỗi `KH-<mã>`."""

    _meta = Customer._meta

    def __init__(self, customer):
        self.pk = customer.pk

    def __str__(self):
        return f"KH-{self.pk}"


@transaction.atomic
def update_customer_profile(*, customer, changes, actor):
    """
    Sửa `name`, `default_address`, `note` của khách (chỉ các khoá trong `EDITABLE_PROFILE_FIELDS`).
    Ghi AuditLog `update_customer` với `changes={"fields": [tên trường đã đổi]}`, tuyệt đối không chép giá trị
    (bất biến 9, BR-PQ-04). Không có gì đổi thì không ghi audit. Trả khách sau khi lưu.
    """
    unknown = set(changes) - set(EDITABLE_PROFILE_FIELDS)
    if unknown:
        raise BusinessError(
            "Chỉ sửa được tên, địa chỉ giao mặc định và ghi chú. Số điện thoại là khoá của khách, không đổi được.",
            code="INPUT_NOT_ALLOWED",
        )
    customer = Customer.objects.select_for_update().get(pk=customer.pk)
    changed = sorted(field for field, value in changes.items() if getattr(customer, field) != value)
    if not changed:
        return customer
    for field in changed:
        setattr(customer, field, changes[field])
    customer.save(update_fields=changed)
    record_audit(
        "update_customer", actor=actor, obj=_CustomerAuditRef(customer), changes={"fields": changed},
    )
    return customer
