"""Hoá đơn mua — tách khỏi phiếu nhập, phải có trước khi chốt lô (BR-MH-04)."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .receipts import PurchaseReceipt
from .suppliers import Supplier


class PurchaseInvoice(models.Model):
    """Hoá đơn mua — ghi chi phí, tách khỏi nhập kho (BR-MH-04)."""

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="invoices", verbose_name="Nhà cung cấp"
    )
    receipt = models.ForeignKey(
        PurchaseReceipt, on_delete=models.PROTECT, null=True, blank=True,
        related_name="invoices", verbose_name="Phiếu nhập liên quan",
    )
    amount = models.DecimalField(
        "Số tiền", max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    is_paid = models.BooleanField("Đã trả tiền", default=True)  # BR-MH-03
    invoice_date = models.DateField("Ngày hoá đơn")
    paid_at = models.DateTimeField("Thời điểm trả", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchase_invoices",
        verbose_name="Người ghi",
    )

    class Meta:
        verbose_name = "Hoá đơn mua"
        verbose_name_plural = "Hoá đơn mua"
        ordering = ["-invoice_date", "-id"]

    def __str__(self):
        return f"PI-{self.pk} · {self.supplier} · {self.amount}đ"
