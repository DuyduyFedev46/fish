"""Hàng giao thất bại quay về kho (P-08, BR-HV)."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .batches import Batch


class ReturnToStock(models.Model):
    """
    Hàng giao thất bại quay về kho (P-08). Nhân viên tạo phiếu, KHÔNG tự nhập lại
    kho — bắt buộc qua `approve_returntostock` (BR-HV-02). Về đúng lô gốc (BR-HV-01).
    """

    class Decision(models.TextChoices):
        PENDING = "PENDING", "Chờ quyết định"
        RESTOCK = "RESTOCK", "Tái nhập"
        WRITE_OFF = "WRITE_OFF", "Huỷ bỏ (hạch toán lỗ)"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Chờ duyệt"
        APPROVED = "APPROVED", "Đã duyệt"

    delivery_note = models.ForeignKey(
        "delivery.DeliveryNote", on_delete=models.PROTECT, null=True, blank=True,
        related_name="returns", verbose_name="Phiếu giao liên quan",
    )
    batch = models.ForeignKey(
        Batch, on_delete=models.PROTECT, related_name="returns", verbose_name="Lô gốc"
    )
    qty = models.DecimalField(
        "Số kg mang về", max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    left_warehouse_at = models.DateTimeField("Giờ rời kho", null=True, blank=True)
    returned_at = models.DateTimeField("Giờ về kho", null=True, blank=True)
    decision = models.CharField(
        "Quyết định", max_length=10, choices=Decision.choices, default=Decision.PENDING
    )
    status = models.CharField(
        "Trạng thái", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="returns_created",
        verbose_name="Người ghi nhận",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="returns_approved", verbose_name="Người duyệt",
    )
    note = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Hàng hoàn về kho"
        verbose_name_plural = "Hàng hoàn về kho"
        ordering = ["-created_at", "-id"]
        permissions = [("approve_returntostock", "Duyệt hàng hoàn về kho")]

    def __str__(self):
        return f"RT-{self.pk} · {self.batch.batch_id} · {self.qty}kg"
