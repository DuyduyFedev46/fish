"""Mặt hàng & nhóm hàng & công thức combo (P-01, BR-DM-01/04/05/06)."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


KG = "Kg"  # BR-DM-01: mọi mặt hàng bán theo Kg, không quy đổi đa đơn vị.


class ItemGroup(models.Model):
    """Phân loại: cá / tôm / mực / cua... (cây phân cấp đơn giản qua parent)."""

    name = models.CharField("Tên nhóm", max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Nhóm cha",
    )

    class Meta:
        verbose_name = "Nhóm hàng"
        verbose_name_plural = "Nhóm hàng"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(models.Model):
    """Mặt hàng. SIMPLE = mặt hàng thường / đóng gói sẵn; BUNDLE = combo có công thức."""

    class ItemType(models.TextChoices):
        SIMPLE = "SIMPLE", "Mặt hàng thường"
        BUNDLE = "BUNDLE", "Combo dạng gói (có công thức)"

    code = models.CharField("Mã hàng", max_length=40, unique=True)
    name = models.CharField("Tên hàng", max_length=200)
    item_group = models.ForeignKey(
        ItemGroup, on_delete=models.PROTECT, related_name="items", verbose_name="Nhóm hàng"
    )
    item_type = models.CharField(
        "Loại", max_length=10, choices=ItemType.choices, default=ItemType.SIMPLE
    )
    stock_uom = models.CharField("Đơn vị", max_length=10, default=KG)  # luôn Kg (BR-DM-01)
    shelf_life_in_days = models.PositiveIntegerField("Hạn dùng mặc định (ngày)", default=90)
    has_batch_no = models.BooleanField("Quản lý theo lô", default=True)
    has_expiry_date = models.BooleanField("Có hạn dùng", default=True)
    is_active = models.BooleanField("Đang kinh doanh", default=True)
    description = models.TextField("Mô tả", blank=True)

    class Meta:
        verbose_name = "Mặt hàng"
        verbose_name_plural = "Mặt hàng"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def is_bundle(self) -> bool:
        return self.item_type == self.ItemType.BUNDLE


class BundleLine(models.Model):
    """Thành phần của combo dạng gói + định mức kg. BR-DM-05: BUNDLE không chứa BUNDLE."""

    bundle = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="bundle_lines",
        limit_choices_to={"item_type": Item.ItemType.BUNDLE},
        verbose_name="Combo",
    )
    component = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name="used_in_bundles",
        limit_choices_to={"item_type": Item.ItemType.SIMPLE},
        verbose_name="Thành phần",
    )
    qty_per_bundle = models.DecimalField(
        "Định mức (kg / 1 combo)",
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    class Meta:
        verbose_name = "Thành phần combo"
        verbose_name_plural = "Thành phần combo"
        constraints = [
            models.UniqueConstraint(
                fields=["bundle", "component"], name="uniq_bundle_component"
            )
        ]

    def __str__(self):
        return f"{self.bundle.code} ⊃ {self.component.code} × {self.qty_per_bundle}kg"

    def clean(self):
        # BR-DM-05: không lồng combo trong combo.
        if self.component_id and self.component.item_type == Item.ItemType.BUNDLE:
            raise ValidationError({"component": "Thành phần không được là combo (BR-DM-05)."})
        if self.bundle_id and self.bundle.item_type != Item.ItemType.BUNDLE:
            raise ValidationError({"bundle": "Chỉ mặt hàng loại BUNDLE mới có công thức."})
        if self.bundle_id and self.component_id and self.bundle_id == self.component_id:
            raise ValidationError("Combo không thể chứa chính nó.")
