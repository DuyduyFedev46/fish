"""Khách hàng (7.1): guest checkout — gộp/khởi tạo Customer theo số điện thoại; sửa hồ sơ ở danh bạ (B2)."""
import re

from django.db import IntegrityError, transaction

from apps.common.audit import record_audit
from apps.common.pii import normalize_phone
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


# B2 (BR-PQ-31): Chủ/Quản lý sửa hồ sơ khách ở danh bạ. Lô bổ sung A #5 (Duy chốt 02/10): thêm `phone`.
EDITABLE_PROFILE_FIELDS = ("name", "default_address", "note", "phone")

# Khớp luật ô SĐT ở Shop (`^(0|\+84)\d{9,10}$`) sau khi `normalize_phone` đổi +84/84 về 0.
_VALID_PHONE = re.compile(r"0\d{9,10}")
_ALT_PREFIX_PHONE = "+84"  # Shop lưu SĐT đúng như khách gõ nên có thể là "+84…"


class _CustomerAuditRef:
    """Đối tượng thay thế cho `record_audit(obj=...)`: `str(Customer)` chứa tên + SĐT nên không được chép vào
    `AuditLog.object_repr` (bất biến 9). Ở đây chỉ có nhãn model, mã khách và chuỗi `KH-<mã>`."""

    _meta = Customer._meta

    def __init__(self, customer):
        self.pk = customer.pk

    def __str__(self):
        return f"KH-{self.pk}"


def _clean_phone(raw):
    """Chuẩn hoá SĐT nhập ở ERP về dạng "0…" (cùng hàm `normalize_phone` của PII). Sai dạng -> 400 INVALID_PHONE."""
    phone = normalize_phone(raw)
    if not _VALID_PHONE.fullmatch(phone):
        raise BusinessError("Số điện thoại không hợp lệ.", code="INVALID_PHONE")
    return phone


def _phone_taken_error():
    # Không lặp lại số trong thông điệp (bất biến 9).
    return BusinessError("Số điện thoại này đã thuộc về một khách hàng khác.", code="CUSTOMER_PHONE_TAKEN")


@transaction.atomic
def update_customer_profile(*, customer, changes, actor):
    """
    Sửa `name`, `phone`, `default_address`, `note` của khách (chỉ các khoá trong `EDITABLE_PROFILE_FIELDS`).
    `phone` được chuẩn hoá (`normalize_phone`), phải đúng dạng 0… 10–11 số và không trùng khách khác. Đơn/hoá đơn/phiếu
    giao nối với khách bằng FK nên giữ nguyên liên kết; `SalesOrder.phone` là số lúc đặt đơn, không đổi.
    Ghi AuditLog `update_customer` với `changes={"fields": [tên trường đã đổi]}`, tuyệt đối không chép giá trị
    (bất biến 9, BR-PQ-04). Không có gì đổi thì không ghi audit. Trả khách sau khi lưu.
    """
    unknown = set(changes) - set(EDITABLE_PROFILE_FIELDS)
    if unknown:
        raise BusinessError(
            "Chỉ sửa được tên, số điện thoại, địa chỉ giao mặc định và ghi chú.",
            code="INPUT_NOT_ALLOWED",
        )
    changes = dict(changes)
    if "phone" in changes:
        changes["phone"] = _clean_phone(changes["phone"])
    customer = Customer.objects.select_for_update().get(pk=customer.pk)
    changed = sorted(field for field, value in changes.items() if getattr(customer, field) != value)
    if not changed:
        return customer
    if "phone" in changed:
        taken = Customer.objects.filter(phone__in=(changes["phone"], _ALT_PREFIX_PHONE + changes["phone"][1:]))
        if taken.exclude(pk=customer.pk).exists():
            raise _phone_taken_error()
    for field in changed:
        setattr(customer, field, changes[field])
    try:
        with transaction.atomic():  # savepoint: hai người đổi cùng lúc thì ràng buộc unique chặn
            customer.save(update_fields=changed)
    except IntegrityError:
        raise _phone_taken_error() from None
    record_audit(
        "update_customer", actor=actor, obj=_CustomerAuditRef(customer), changes={"fields": changed},
    )
    return customer
