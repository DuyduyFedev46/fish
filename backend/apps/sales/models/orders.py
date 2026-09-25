"""Đơn hàng + dòng đơn + giữ chỗ theo lô (P-05, BR-PQ-11, BR-BH-02/06/07/08)."""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .customers import Customer


class SalesOrder(models.Model):
    """Đơn hàng. Do Hệ thống tạo khi khách đặt trên Shop (BR-PQ-11)."""

    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Giữ chỗ"            # giữ kg trong lô, chưa trừ tồn thật
        PAID = "PAID", "Đã thanh toán"          # webhook xác nhận
        PROCESSING = "PROCESSING", "Đang xử lý"  # đã trừ kho + ghi doanh thu
        COMPLETED = "COMPLETED", "Hoàn tất"
        CANCELLED = "CANCELLED", "Đã huỷ"        # cancel_paid_order (P-07)
        AUTO_CANCELLED = "AUTO_CANCELLED", "Tự huỷ (quá TTL)"

    code = models.CharField("Mã đơn", max_length=32, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders", verbose_name="Khách hàng"
    )
    status = models.CharField(
        "Trạng thái", max_length=16, choices=Status.choices, default=Status.BOOKED
    )
    delivery_address = models.TextField("Địa chỉ giao")  # bắt buộc (BR-BH-09)
    phone = models.CharField("SĐT nhận hàng", max_length=20)
    total_amount = models.DecimalField(
        "Tổng tiền", max_digits=14, decimal_places=2, default=Decimal("0")
    )
    booked_expires_at = models.DateTimeField(
        "Hết hạn giữ chỗ", null=True, blank=True,
        help_text="created_at + TTL (mặc định 30') — job nền quét & nhả (BR-BH-03/04).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # KHÔNG có trường phí giao hàng (BR-BH-10 — outscope hoàn toàn).

    class Meta:
        verbose_name = "Đơn hàng"
        verbose_name_plural = "Đơn hàng"
        ordering = ["-created_at", "-id"]
        # BR-PQ-11: không ai được tạo/xoá tay — chỉ còn view/change.
        default_permissions = ("view", "change")
        permissions = [("cancel_paid_order", "Huỷ đơn đã thanh toán")]

    def __str__(self):
        return self.code


class SalesOrderLine(models.Model):
    """Dòng đơn — giá & công thức BUNDLE đóng băng tại thời điểm đặt (BR-BH-08)."""

    order = models.ForeignKey(
        SalesOrder, on_delete=models.CASCADE, related_name="lines", verbose_name="Đơn"
    )
    item = models.ForeignKey(
        "catalog.Item", on_delete=models.PROTECT, related_name="+", verbose_name="Mặt hàng"
    )
    qty = models.DecimalField(
        "Số lượng (kg)", max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    rate = models.DecimalField(  # ảnh chụp ItemPrice tại thời điểm đặt (BR-DM-02)
        "Đơn giá (đ/kg)", max_digits=14, decimal_places=2
    )
    bundle_snapshot = models.JSONField(
        "Ảnh chụp công thức combo", default=dict, blank=True,
        help_text="Công thức BundleLine đóng băng lúc đặt (BR-DM-07).",
    )
    pricing_rule = models.ForeignKey(
        "catalog.PricingRule", on_delete=models.PROTECT, null=True, blank=True,
        related_name="+", verbose_name="Ưu đãi áp dụng",
    )
    discount_amount = models.DecimalField(
        "Giảm giá (đ)", max_digits=14, decimal_places=2, default=Decimal("0")
    )
    amount = models.DecimalField(
        "Thành tiền", max_digits=14, decimal_places=2, default=Decimal("0")
    )

    class Meta:
        verbose_name = "Dòng đơn"
        verbose_name_plural = "Dòng đơn"
        default_permissions = ("view",)  # con của SalesOrder (system-written)

    def __str__(self):
        return f"{self.order.code} · {self.item.code} × {self.qty}kg"


class SalesOrderLineBatch(models.Model):
    """
    Giữ chỗ ở MỨC LÔ (BR-BH-02). Một dòng đơn được phép ăn nhiều lô (BR-BH-06).
    Với BUNDLE, các bản ghi này là của từng thành phần (BR-BH-07).
    """

    order_line = models.ForeignKey(
        SalesOrderLine, on_delete=models.CASCADE, related_name="batch_allocations",
        verbose_name="Dòng đơn",
    )
    batch = models.ForeignKey(
        "inventory.Batch", on_delete=models.PROTECT, related_name="reservations",
        verbose_name="Lô",
    )
    component_item = models.ForeignKey(
        "catalog.Item", on_delete=models.PROTECT, related_name="+",
        verbose_name="Mặt hàng thực trừ",
        help_text="Với BUNDLE là thành phần; với SIMPLE trùng item của dòng.",
    )
    qty = models.DecimalField("Số kg giữ", max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(  # NHẠY CẢM — ảnh chụp landed_unit_cost
        "Giá vốn ảnh chụp", max_digits=14, decimal_places=4, default=Decimal("0")
    )

    class Meta:
        verbose_name = "Giữ chỗ theo lô"
        verbose_name_plural = "Giữ chỗ theo lô"
        default_permissions = ("view",)  # system-written

    def __str__(self):
        return f"{self.order_line} ⇐ {self.batch.batch_id} × {self.qty}kg"
