"""Chi phí mua hàng + phân bổ vào lô — landed cost (P-03, BR-GV)."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class PurchaseCost(models.Model):
    """
    Chi phí phụ mua hàng (đá, vận chuyển, bốc vác) phân bổ vào giá vốn lô (P-03).
    Chỉ Chủ có `add_purchasecost` — đụng thẳng vào giá vốn.
    """

    class CostType(models.TextChoices):
        ICE = "ICE", "Đá"
        TRANSPORT = "TRANSPORT", "Vận chuyển"
        LOADING = "LOADING", "Bốc vác"
        OTHER = "OTHER", "Khác"

    class AllocationMethod(models.TextChoices):
        BY_QTY = "BY_QTY", "Theo số kg"  # mặc định (BR-GV-04)
        BY_VALUE = "BY_VALUE", "Theo giá trị"

    cost_type = models.CharField("Loại chi phí", max_length=12, choices=CostType.choices)
    amount = models.DecimalField(
        "Số tiền", max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    allocation_method = models.CharField(
        "Phân bổ theo", max_length=10, choices=AllocationMethod.choices,
        default=AllocationMethod.BY_QTY,
    )
    incurred_date = models.DateField("Ngày phát sinh")
    note = models.TextField("Ghi chú", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchase_costs",
        verbose_name="Người ghi",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chi phí mua hàng"
        verbose_name_plural = "Chi phí mua hàng"
        ordering = ["-incurred_date", "-id"]
        # 'add_purchasecost' = quyền builtin `add` của Django cho model này. Không
        # khai custom (sẽ clash auth.E005). Gate "chỉ Chủ" thực hiện bằng cách chỉ
        # gán builtin add_purchasecost cho Group `chu` trong fixture phân quyền.

    def __str__(self):
        return f"{self.get_cost_type_display()} · {self.amount}đ"


class PurchaseCostAllocation(models.Model):
    """Chi tiết phân bổ một PurchaseCost vào từng lô nhận."""

    purchase_cost = models.ForeignKey(
        PurchaseCost, on_delete=models.CASCADE, related_name="allocations",
        verbose_name="Chi phí",
    )
    batch = models.ForeignKey(
        "inventory.Batch", on_delete=models.PROTECT, related_name="cost_allocations",
        verbose_name="Lô nhận",
    )
    allocated_amount = models.DecimalField(
        "Tiền phân bổ", max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        verbose_name = "Phân bổ chi phí"
        verbose_name_plural = "Phân bổ chi phí"
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_cost", "batch"], name="uniq_cost_batch"
            )
        ]

    def __str__(self):
        return f"{self.purchase_cost} → {self.batch} = {self.allocated_amount}đ"
