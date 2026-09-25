"""Sổ chuyển động kho (append-only) + phiếu điều chỉnh kho thủ công."""
from django.conf import settings
from django.db import models

from .batches import Batch


class StockLedgerEntry(models.Model):
    """
    Sổ chuyển động kho — append-only, do Hệ thống ghi (không CRUD trực tiếp).
    Nền tảng để dựng lại tồn và báo cáo. `qty_change` dương = nhập, âm = xuất.
    """

    class MovementType(models.TextChoices):
        RECEIPT = "RECEIPT", "Nhập lô"
        SALE = "SALE", "Bán ra"
        RETURN_RESTOCK = "RETURN_RESTOCK", "Hàng hoàn tái nhập"
        RECONCILE = "RECONCILE", "Điều chỉnh kiểm kê"
        WRITE_OFF = "WRITE_OFF", "Hạch toán lỗ / huỷ"
        CANCEL_RESTORE = "CANCEL_RESTORE", "Hoàn kho do huỷ đơn"

    batch = models.ForeignKey(
        Batch, on_delete=models.PROTECT, related_name="ledger_entries", verbose_name="Lô"
    )
    movement_type = models.CharField("Loại", max_length=16, choices=MovementType.choices)
    qty_change = models.DecimalField("Biến động (kg)", max_digits=12, decimal_places=3)
    reference = models.CharField("Chứng từ nguồn", max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="stock_movements", verbose_name="Người/Hệ thống",
    )

    class Meta:
        verbose_name = "Chuyển động kho"
        verbose_name_plural = "Sổ chuyển động kho"
        ordering = ["-created_at", "-id"]
        default_permissions = ("view",)  # system-written, không CRUD tay

    def __str__(self):
        return f"{self.batch.batch_id} {self.qty_change:+} ({self.get_movement_type_display()})"


class StockEntry(models.Model):
    """Điều chỉnh kho thủ công (material receipt / hiệu chỉnh) — có kiểm soát."""

    class Purpose(models.TextChoices):
        MATERIAL_RECEIPT = "MATERIAL_RECEIPT", "Nhập vật tư"
        ADJUSTMENT = "ADJUSTMENT", "Điều chỉnh"

    purpose = models.CharField("Mục đích", max_length=20, choices=Purpose.choices)
    batch = models.ForeignKey(
        Batch, on_delete=models.PROTECT, related_name="stock_entries", verbose_name="Lô"
    )
    qty_change = models.DecimalField("Biến động (kg)", max_digits=12, decimal_places=3)
    reason = models.TextField("Lý do", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stock_entries",
        verbose_name="Người thực hiện",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Phiếu điều chỉnh kho"
        verbose_name_plural = "Phiếu điều chỉnh kho"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"SE-{self.pk} · {self.batch.batch_id} {self.qty_change:+}"
