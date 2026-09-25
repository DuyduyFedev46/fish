"""Phiếu nhập tại cảng + dòng nhập (P-02, BR-MH-01/02)."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .suppliers import Supplier


class PurchaseReceipt(models.Model):
    """Phiếu nhập kho tại cảng — kiểm đếm vật lý. Mỗi dòng sinh 1 Batch."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        SUBMITTED = "SUBMITTED", "Đã ghi nhận"

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="receipts", verbose_name="Nhà cung cấp"
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse", on_delete=models.PROTECT, related_name="receipts",
        verbose_name="Kho nhập",
    )
    received_date = models.DateField("Ngày nhập")
    status = models.CharField(
        "Trạng thái", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchase_receipts",
        verbose_name="Người nhập",
    )
    note = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Phiếu nhập kho"
        verbose_name_plural = "Phiếu nhập kho"
        ordering = ["-received_date", "-id"]

    def __str__(self):
        return f"PR-{self.pk} · {self.supplier} · {self.received_date}"


class PurchaseReceiptLine(models.Model):
    """
    Một dòng = một mặt hàng nhập = một lô (BR-MH-01).
    `rate` (đơn giá mua) là field NHẠY CẢM (1.6, BR-MH-06).
    """

    receipt = models.ForeignKey(
        PurchaseReceipt, on_delete=models.CASCADE, related_name="lines", verbose_name="Phiếu nhập"
    )
    item = models.ForeignKey(
        "catalog.Item", on_delete=models.PROTECT, related_name="+", verbose_name="Mặt hàng"
    )
    qty = models.DecimalField(
        "Số lượng (kg)", max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    rate = models.DecimalField(  # NHẠY CẢM — chỉ view_costprice mới xem
        "Đơn giá mua (đ/kg)", max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    shelf_life_days = models.PositiveIntegerField(
        "Hạn dùng (ngày)", null=True, blank=True,
        help_text="Bỏ trống = lấy theo Item. Cho sửa thấp hơn, không cao hơn (BR-MH-02).",
    )
    batch = models.OneToOneField(
        "inventory.Batch", on_delete=models.PROTECT, null=True, blank=True,
        related_name="source_line", verbose_name="Lô sinh ra",
    )

    class Meta:
        verbose_name = "Dòng nhập kho"
        verbose_name_plural = "Dòng nhập kho"

    def __str__(self):
        # Không đưa `rate` vào chuỗi: __str__ hiện ở Admin inline/AuditLog cho người thiếu
        # view_costprice (rò giá vốn, §1.6).
        return f"{self.item.code} × {self.qty}kg"
