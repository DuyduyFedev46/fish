"""Bảng giá, giá niêm yết theo hiệu lực, ưu đãi 1 tầng (P-01, BR-DM-02/03/08)."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .items import Item


class PriceList(models.Model):
    """Bảng giá. V1 chỉ cần 1 bảng 'Bán lẻ'."""

    name = models.CharField("Tên bảng giá", max_length=120, unique=True)
    currency = models.CharField("Tiền tệ", max_length=8, default="VND")
    is_default = models.BooleanField("Mặc định", default=False)

    class Meta:
        verbose_name = "Bảng giá"
        verbose_name_plural = "Bảng giá"

    def __str__(self):
        return self.name


class ItemPrice(models.Model):
    """
    Giá niêm yết có hiệu lực theo mùa (lưu lịch sử).
    BR-DM-02: giá bán luôn lấy từ ItemPrice hiệu lực tại thời điểm đặt.
    BR-DM-03: cùng item + cùng bảng giá không được chồng lấn khoảng hiệu lực.
    """

    price_list = models.ForeignKey(
        PriceList, on_delete=models.PROTECT, related_name="prices", verbose_name="Bảng giá"
    )
    item = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name="prices", verbose_name="Mặt hàng"
    )
    rate = models.DecimalField(
        "Đơn giá (đ/kg)", max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    valid_from = models.DateField("Hiệu lực từ")
    valid_upto = models.DateField("Hiệu lực đến", null=True, blank=True)

    class Meta:
        verbose_name = "Giá niêm yết"
        verbose_name_plural = "Giá niêm yết"
        ordering = ["item", "-valid_from"]

    def __str__(self):
        return f"{self.item.code}: {self.rate}đ ({self.valid_from} → {self.valid_upto or '∞'})"

    def clean(self):
        # BR-DM-03: chặn chồng lấn khoảng hiệu lực trên cùng item + bảng giá.
        if not (self.item_id and self.price_list_id and self.valid_from):
            return
        end = self.valid_upto or models.Value  # dùng None = vô hạn
        qs = ItemPrice.objects.filter(
            price_list_id=self.price_list_id, item_id=self.item_id
        ).exclude(pk=self.pk)
        for other in qs:
            o_start, o_end = other.valid_from, other.valid_upto
            # Hai khoảng [a_start, a_end] và [o_start, o_end] (None = +∞) chồng nhau?
            a_end = self.valid_upto
            overlap = (o_end is None or self.valid_from <= o_end) and (
                a_end is None or o_start <= a_end
            )
            if overlap:
                raise ValidationError(
                    "Khoảng hiệu lực chồng lấn với một giá đã có của mặt hàng này (BR-DM-03)."
                )


class PricingRule(models.Model):
    """
    Ưu đãi 1 tầng (BR-DM-08). Nhiều rule cùng khớp -> chọn DUY NHẤT rule có lợi
    nhất cho khách, KHÔNG cộng dồn. Không mã giảm giá, không ngân sách, không lồng.
    """

    class ApplyOn(models.TextChoices):
        ITEM = "ITEM", "Theo mặt hàng (mua ≥ N kg)"
        ORDER = "ORDER", "Theo đơn (tổng ≥ M đồng)"

    class DiscountType(models.TextChoices):
        AMOUNT = "AMOUNT", "Giảm số tiền"
        PERCENT = "PERCENT", "Giảm phần trăm"

    name = models.CharField("Tên ưu đãi", max_length=150)
    is_active = models.BooleanField("Đang áp dụng", default=True)
    apply_on = models.CharField("Áp dụng trên", max_length=8, choices=ApplyOn.choices)
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pricing_rules",
        verbose_name="Mặt hàng điều kiện",
        help_text="Bắt buộc khi 'Áp dụng trên' = Theo mặt hàng.",
    )
    min_qty = models.DecimalField(
        "Số kg tối thiểu", max_digits=12, decimal_places=3, null=True, blank=True
    )
    min_amount = models.DecimalField(
        "Giá trị đơn tối thiểu (đ)", max_digits=14, decimal_places=2, null=True, blank=True
    )
    discount_type = models.CharField(
        "Kiểu giảm", max_length=8, choices=DiscountType.choices
    )
    discount_value = models.DecimalField(
        "Mức giảm", max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    valid_from = models.DateField("Hiệu lực từ", null=True, blank=True)
    valid_upto = models.DateField("Hiệu lực đến", null=True, blank=True)

    class Meta:
        verbose_name = "Ưu đãi"
        verbose_name_plural = "Ưu đãi"

    def __str__(self):
        return self.name

    def clean(self):
        if self.apply_on == self.ApplyOn.ITEM:
            if not self.item_id:
                raise ValidationError({"item": "Ưu đãi theo mặt hàng phải chọn mặt hàng."})
            if self.min_qty is None:
                raise ValidationError({"min_qty": "Cần số kg tối thiểu cho ưu đãi theo mặt hàng."})
        if self.apply_on == self.ApplyOn.ORDER and self.min_amount is None:
            raise ValidationError({"min_amount": "Cần giá trị đơn tối thiểu cho ưu đãi theo đơn."})
        if self.discount_type == self.DiscountType.PERCENT and self.discount_value > 100:
            raise ValidationError({"discount_value": "Phần trăm giảm không vượt 100."})
