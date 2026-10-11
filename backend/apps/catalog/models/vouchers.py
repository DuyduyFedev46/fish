"""
Mã giảm giá công khai (SHOP-3b-01, BR-DM-17…24, quyết định Duy 10/10).

Một mã/đơn, không cộng dồn với PricingRule, có trần tiền, tổng lượt và hạn. Lượt dùng nằm ở
`sales.VoucherRedemption` (không lưu SĐT/tên, bất biến 9). Mã luôn IN HOA, không xoá (bất biến 3):
dừng bằng `is_active=False`.
"""
from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Voucher(models.Model):
    class Kind(models.TextChoices):
        AMOUNT = "AMOUNT", "Giảm số tiền"
        PERCENT = "PERCENT", "Giảm phần trăm"

    class DisabledReason(models.TextChoices):
        BUDGET = "BUDGET", "Hết ngân sách"
        INCIDENT = "INCIDENT", "Sự cố"
        OTHER = "OTHER", "Khác"

    code = models.CharField("Mã", max_length=20, unique=True)  # luôn IN HOA
    name = models.CharField("Tên chương trình", max_length=120)
    kind = models.CharField("Kiểu giảm", max_length=8, choices=Kind.choices)
    value = models.DecimalField("Mức giảm", max_digits=14, decimal_places=2)
    max_discount = models.DecimalField("Trần giảm (đ)", max_digits=14, decimal_places=2, null=True, blank=True)
    min_order_amount = models.DecimalField("Đơn tối thiểu (đ)", max_digits=14, decimal_places=2, default=0)
    starts_at = models.DateTimeField("Bắt đầu")
    ends_at = models.DateTimeField("Kết thúc")
    total_uses = models.PositiveIntegerField("Tổng lượt")
    customer_terms = models.CharField("Điều kiện hiển thị cho khách", max_length=300, blank=True, default="")
    is_active = models.BooleanField("Đang bật", default=True)
    disabled_reason = models.CharField(
        "Lý do tắt", max_length=10, choices=DisabledReason.choices, blank=True, default=""
    )
    disabled_note = models.CharField("Ghi chú khi tắt", max_length=200, blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mã giảm giá"
        verbose_name_plural = "Mã giảm giá"
        default_permissions = ()
        permissions = [("manage_voucher", "Quản lý mã giảm giá")]
        constraints = [
            models.CheckConstraint(condition=Q(starts_at__lt=F("ends_at")), name="voucher_starts_before_ends"),
        ]
        indexes = [models.Index(fields=["is_active", "ends_at"])]

    def __str__(self):
        return self.code
