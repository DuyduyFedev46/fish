"""Trả nhà cung cấp phần tồn lô quá hạn (P8 Lô 5, BR-MH-08)."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .batches import Batch


class BatchSupplierReturn(models.Model):
    """
    Trả lại NCC phần tồn lô quá hạn (BR-MH-08). Append-only, chỉ ghi qua service
    `return_batch_to_supplier`. PA: NCC hoàn tiền ngoài hệ thống, hệ thống chỉ ghi sổ.

    `supplier_refund_amount` NHẠY CẢM (thuộc COST_KEYS): không đưa vào response/serializer nào,
    chỉ `batch_pnl` (view_profitreport) dùng để giảm tổng chi phí lô (BR-BC-04).
    """

    batch = models.ForeignKey(
        Batch, on_delete=models.PROTECT, related_name="supplier_returns", verbose_name="Lô"
    )
    qty = models.DecimalField(
        "Số kg trả NCC", max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    supplier_refund_amount = models.DecimalField(
        "Tiền NCC hoàn", max_digits=14, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    note = models.CharField("Ghi chú", max_length=500, blank=True)
    request_id = models.UUIDField("Mã yêu cầu (chống gửi lặp)", null=True, blank=True, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name="Người xác nhận"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Trả nhà cung cấp"
        verbose_name_plural = "Trả nhà cung cấp"
        default_permissions = ("view",)

    def __str__(self):
        return f"SR-{self.pk} · {self.batch_id} · {self.qty}kg"
