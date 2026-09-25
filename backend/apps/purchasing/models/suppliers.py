"""Nhà cung cấp (đầu mối tại cảng)."""
from django.db import models


class Supplier(models.Model):
    """Nhà cung cấp — tối giản (cá nhân đầu mối tại cảng)."""

    class SupplierType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Cá nhân"
        COMPANY = "COMPANY", "Doanh nghiệp"

    name = models.CharField("Tên nhà cung cấp", max_length=200)
    supplier_type = models.CharField(
        "Loại", max_length=12, choices=SupplierType.choices, default=SupplierType.INDIVIDUAL
    )
    phone = models.CharField("Điện thoại", max_length=20, blank=True)
    note = models.TextField("Ghi chú", blank=True)
    is_active = models.BooleanField("Đang hợp tác", default=True)

    class Meta:
        verbose_name = "Nhà cung cấp"
        verbose_name_plural = "Nhà cung cấp"
        ordering = ["name"]

    def __str__(self):
        return self.name
