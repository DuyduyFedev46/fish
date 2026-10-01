"""Khách cá nhân — guest checkout, gộp theo số điện thoại (7.1)."""
from django.db import models


class Customer(models.Model):
    """Khách cá nhân (B2C). Guest checkout — gộp theo số điện thoại (khoá tự nhiên, 7.1)."""

    phone = models.CharField("Số điện thoại", max_length=20, unique=True)
    name = models.CharField("Tên khách", max_length=200, blank=True)
    default_address = models.TextField("Địa chỉ giao mặc định", blank=True)
    note = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Khách hàng"
        verbose_name_plural = "Khách hàng"
        ordering = ["phone"]
        # B2 (BR-PQ-31): quyền Tầng 2 "Xem khách hàng" = xem danh bạ khách `/api/sales/customer-directory/`.
        # Khác `view_customer` (Tầng 1, phạm vi dòng của NV giao). Cấp cho owner + manager ở migration 0013.
        permissions = [("view_customer_list", "Xem khách hàng")]

    def __str__(self):
        return f"{self.name or 'Khách'} ({self.phone})"
