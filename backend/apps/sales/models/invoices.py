"""Hoá đơn bán + phân bổ lô đã bán — NGUỒN giá vốn (BR-BH-06, BR-TT-06). unit_cost nhạy cảm."""
from django.db import models

from .customers import Customer
from .orders import SalesOrder


class SalesInvoice(models.Model):
    """
    Hoá đơn bán — do Hệ thống tạo khi xác nhận thanh toán (BR-PQ-11).
    Ghi doanh thu tại thời điểm này (BR-TT-06 / BR-BC-01).
    """

    class Status(models.TextChoices):
        ISSUED = "ISSUED", "Đã xuất"
        CANCELLED = "CANCELLED", "Đã huỷ"

    code = models.CharField("Mã hoá đơn", max_length=32, unique=True)
    sales_order = models.OneToOneField(
        SalesOrder, on_delete=models.PROTECT, related_name="invoice", verbose_name="Đơn hàng"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="invoices", verbose_name="Khách hàng"
    )
    issued_at = models.DateTimeField("Thời điểm xuất (xác nhận TT)")
    amount = models.DecimalField("Số tiền", max_digits=14, decimal_places=2)
    payment_txn_ref = models.CharField("Mã giao dịch ngân hàng", max_length=100, blank=True)
    payment_method = models.CharField("Kênh thanh toán", max_length=32, default="VIETQR")
    status = models.CharField(
        "Trạng thái", max_length=10, choices=Status.choices, default=Status.ISSUED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Hoá đơn bán"
        verbose_name_plural = "Hoá đơn bán"
        ordering = ["-issued_at", "-id"]
        default_permissions = ("view", "change")  # BR-PQ-11: không add/delete
        permissions = [
            ("confirm_payment_manual", "Xác nhận thanh toán thủ công"),
        ]

    def __str__(self):
        return self.code


class SalesInvoiceLine(models.Model):
    invoice = models.ForeignKey(
        SalesInvoice, on_delete=models.CASCADE, related_name="lines", verbose_name="Hoá đơn"
    )
    item = models.ForeignKey(
        "catalog.Item", on_delete=models.PROTECT, related_name="+", verbose_name="Mặt hàng"
    )
    qty = models.DecimalField("Số lượng (kg)", max_digits=12, decimal_places=3)
    rate = models.DecimalField("Đơn giá (đ/kg)", max_digits=14, decimal_places=2)
    amount = models.DecimalField("Thành tiền", max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = "Dòng hoá đơn"
        verbose_name_plural = "Dòng hoá đơn"
        default_permissions = ("view",)  # con của SalesInvoice (system-written)

    def __str__(self):
        return f"{self.invoice.code} · {self.item.code}"


class SalesInvoiceLineBatch(models.Model):
    """
    dòng ↔ lô ↔ kg ↔ đơn giá vốn — NGUỒN SỰ THẬT của báo cáo giá vốn (BR-BH-06).
    `unit_cost` NHẠY CẢM (view_costprice). System-written, không CRUD tay.
    """

    invoice_line = models.ForeignKey(
        SalesInvoiceLine, on_delete=models.CASCADE, related_name="batch_allocations",
        verbose_name="Dòng hoá đơn",
    )
    batch = models.ForeignKey(
        "inventory.Batch", on_delete=models.PROTECT, related_name="sold_allocations",
        verbose_name="Lô",
    )
    component_item = models.ForeignKey(
        "catalog.Item", on_delete=models.PROTECT, related_name="+",
        verbose_name="Mặt hàng thực trừ",
    )
    qty = models.DecimalField("Số kg", max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(  # NHẠY CẢM
        "Giá vốn ảnh chụp (đ/kg)", max_digits=14, decimal_places=4
    )

    class Meta:
        verbose_name = "Phân bổ lô đã bán"
        verbose_name_plural = "Phân bổ lô đã bán"
        default_permissions = ("view",)

    def __str__(self):
        return f"{self.invoice_line} ⇐ {self.batch.batch_id} × {self.qty}kg"
