"""Lô hàng — trái tim vận hành (P-04, BR-LO, BR-BH-01/05). Field nhạy cảm: purchase_rate, landed_unit_cost."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .warehouses import Warehouse


class Batch(models.Model):
    """Lô hàng nhập tại cảng — kg, hạn dùng, giá vốn sau phân bổ."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"            # BR-MH-05: chưa hiện Shop
        SELLING = "SELLING", "Đang bán"    # publish_batch
        NEAR_EXPIRY = "NEAR_EXPIRY", "Cận hạn"  # hệ thống cảnh báo (BR-LO-01)
        SOLD_OUT = "SOLD_OUT", "Hết hàng"
        EXPIRED = "EXPIRED", "Quá hạn"     # loại khỏi bán ngay (BR-LO-02)
        CANCELLED = "CANCELLED", "Đã huỷ"  # huỷ lô quá hạn, hạch toán lỗ (BR-LO-03)
        CLOSED = "CLOSED", "Đã chốt"       # close_batch — đông cứng (BR-LO-05)

    batch_id = models.CharField("Mã lô", max_length=40, unique=True)
    item = models.ForeignKey(
        "catalog.Item", on_delete=models.PROTECT, related_name="batches", verbose_name="Mặt hàng"
    )
    supplier = models.ForeignKey(
        "purchasing.Supplier", on_delete=models.PROTECT, related_name="batches",
        verbose_name="Nhà cung cấp",
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="batches", verbose_name="Kho"
    )
    received_date = models.DateField("Ngày nhập")
    expiry_date = models.DateField("Hạn dùng")  # = received_date + shelf_life (BR-MH-02)

    qty_received = models.DecimalField(
        "Số kg nhập ban đầu", max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Mẫu số tính landed_unit_cost — KHÔNG đổi khi có hao hụt (BR-GV-01).",
    )
    qty_available = models.DecimalField(
        "Tồn sổ (kg)", max_digits=12, decimal_places=3, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    qty_reserved = models.DecimalField(
        "Đang giữ chỗ (kg)", max_digits=12, decimal_places=3, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Tổng kg đang bị đơn 'giữ chỗ' khoá (BR-BH-02).",
    )

    # --- Field NHẠY CẢM: chỉ view_costprice mới được đọc (1.6, phạm vi cột) ---
    purchase_rate = models.DecimalField(
        "Đơn giá mua (đ/kg)", max_digits=14, decimal_places=2, default=Decimal("0")
    )
    landed_unit_cost = models.DecimalField(
        "Giá vốn lô (đ/kg)", max_digits=14, decimal_places=4, default=Decimal("0"),
        help_text="(giá mua lô + chi phí phân bổ) / qty_received. Đổi phải ghi AuditLog (BR-GV-03).",
    )

    status = models.CharField(
        "Trạng thái", max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    closed_at = models.DateTimeField("Thời điểm chốt", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="closed_batches", verbose_name="Người chốt",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lô hàng"
        verbose_name_plural = "Lô hàng"
        ordering = ["received_date", "id"]  # FIFO theo ngày nhập (BR-BH-05)
        permissions = [
            ("publish_batch", "Publish lô ra Shop"),
            ("close_batch", "Chốt lô (đông cứng lãi/lỗ)"),
            ("view_costprice", "Xem giá vốn / đơn giá mua"),
        ]

    def __str__(self):
        return f"{self.batch_id} · {self.item.code}"

    @property
    def qty_sellable(self) -> Decimal:
        """Tồn khả dụng hiển thị Shop (BR-BH-01)."""
        return self.qty_available - self.qty_reserved

    @property
    def is_closed(self) -> bool:
        return self.status == self.Status.CLOSED
