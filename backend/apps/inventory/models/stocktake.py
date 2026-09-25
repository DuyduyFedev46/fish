"""Kiểm kê định kỳ theo lô (P-09, BR-KK)."""
from decimal import Decimal

from django.conf import settings
from django.db import models

from .batches import Batch


class StockReconciliation(models.Model):
    """
    Kiểm kê định kỳ (P-09). Người nhập số ≠ người duyệt (BR-KK-02).
    Chưa duyệt thì tồn sổ chưa đổi.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Chờ duyệt"
        APPROVED = "APPROVED", "Đã duyệt"

    count_date = models.DateField("Ngày kiểm kê")
    status = models.CharField(
        "Trạng thái", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reconciliations_created",
        verbose_name="Người nhập số",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="reconciliations_approved", verbose_name="Người duyệt",
    )
    approved_at = models.DateTimeField("Thời điểm duyệt", null=True, blank=True)
    note = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Phiếu kiểm kê"
        verbose_name_plural = "Phiếu kiểm kê"
        ordering = ["-count_date", "-id"]
        permissions = [("approve_stockreconciliation", "Duyệt kiểm kê")]

    def __str__(self):
        return f"KK-{self.pk} · {self.count_date}"


class StockReconciliationLine(models.Model):
    """Chi tiết kiểm kê theo từng lô (BR-KK-01)."""

    reconciliation = models.ForeignKey(
        StockReconciliation, on_delete=models.CASCADE, related_name="lines",
        verbose_name="Phiếu kiểm kê",
    )
    batch = models.ForeignKey(
        Batch, on_delete=models.PROTECT, related_name="reconciliation_lines", verbose_name="Lô"
    )
    system_qty = models.DecimalField(
        "Tồn sổ (ảnh chụp)", max_digits=12, decimal_places=3,
        help_text="Tồn sổ tại thời điểm nhập số.",
    )
    counted_qty = models.DecimalField("Tồn thực đếm (kg)", max_digits=12, decimal_places=3)
    difference_qty = models.DecimalField(
        "Chênh lệch (kg)", max_digits=12, decimal_places=3, default=Decimal("0")
    )
    reason = models.TextField(
        "Lý do", blank=True, help_text="Bắt buộc khi chênh lệch dương (BR-KK-04)."
    )

    class Meta:
        verbose_name = "Dòng kiểm kê"
        verbose_name_plural = "Dòng kiểm kê"

    def __str__(self):
        return f"{self.batch.batch_id}: sổ {self.system_qty} / đếm {self.counted_qty}"
