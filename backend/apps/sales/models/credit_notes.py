"""
Chứng từ đảo doanh thu (BR-HT-06, BR-HT-10) — F04 của P8.

Duy cấm đổi/xoá hoá đơn gốc (nguyên văn 30/09: "sợ ko ghi được lịch sử"), nên khi huỷ đơn đã thanh
toán Hệ thống lập MỘT chứng từ đảo gắn hoá đơn gốc, có dòng theo lô + kg + đơn giá bán lấy từ phân
bổ lô của hoá đơn (BR-BH-06). Append-only: `default_permissions = ("view",)` → không có quyền
add/change/delete cho ai (BR-PQ-10/11); chỉ `credit_notes.services` ghi.

`SalesCreditNoteLine.unit_cost` là giá vốn ảnh chụp — field NHẠY CẢM (view_costprice): không serializer/API
nào trả; Admin ẩn với người thiếu quyền. Không có field dữ liệu cá nhân của khách (bất biến 9).
"""
from django.conf import settings
from django.db import models

from .invoices import SalesInvoice, SalesInvoiceLineBatch


class SalesCreditNote(models.Model):
    """Chứng từ đảo doanh thu (BR-HT-10). Append-only, Hệ thống lập. Không sửa/xoá hoá đơn gốc."""

    class Kind(models.TextChoices):
        CANCEL_ORDER = "CANCEL_ORDER", "Huỷ đơn đã thanh toán"

    code = models.CharField("Mã chứng từ", max_length=40, unique=True)  # "DC-<mã hoá đơn>"
    source_key = models.CharField(
        "Khoá nguồn (chống trùng)", max_length=64, unique=True,
    )  # "cancel:<order.pk>" — mỗi đơn tối đa một chứng từ huỷ
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.CANCEL_ORDER)
    sales_invoice = models.ForeignKey(
        SalesInvoice, on_delete=models.PROTECT, related_name="credit_notes", verbose_name="Hoá đơn gốc",
    )
    issued_at = models.DateTimeField("Thời điểm ghi nhận (kỳ đảo)")
    amount = models.DecimalField("Số tiền đảo", max_digits=14, decimal_places=2)  # = invoice.amount khi huỷ cả đơn
    stock_restored = models.BooleanField("Đã hoàn kho lúc huỷ")
    reason_code = models.CharField("Mã lý do huỷ", max_length=32, blank=True)
    backfilled = models.BooleanField("Lập bù (SR-14)", default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
        verbose_name="Người huỷ (trống = Hệ thống)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chứng từ đảo doanh thu"
        verbose_name_plural = "Chứng từ đảo doanh thu"
        default_permissions = ("view",)  # BR-PQ-11: không add/change/delete
        ordering = ["-issued_at", "-id"]
        indexes = [models.Index(fields=["issued_at"])]

    def __str__(self):
        return self.code


class SalesCreditNoteLine(models.Model):
    """Một dòng đảo = một dòng phân bổ lô của hoá đơn gốc (lô + kg + đơn giá bán)."""

    credit_note = models.ForeignKey(
        SalesCreditNote, on_delete=models.CASCADE, related_name="lines", verbose_name="Chứng từ",
    )
    invoice_line_batch = models.ForeignKey(
        SalesInvoiceLineBatch, on_delete=models.PROTECT, related_name="+", verbose_name="Phân bổ lô gốc",
    )
    batch = models.ForeignKey(
        "inventory.Batch", on_delete=models.PROTECT, related_name="credit_note_lines", verbose_name="Lô",
    )
    qty = models.DecimalField("Số kg đảo", max_digits=12, decimal_places=3)
    rate = models.DecimalField("Đơn giá bán (đ/kg)", max_digits=14, decimal_places=2)  # SalesInvoiceLine.rate
    amount = models.DecimalField("Thành tiền đảo", max_digits=14, decimal_places=2)  # qty × rate
    unit_cost = models.DecimalField(  # NHẠY CẢM (view_costprice) = SalesInvoiceLineBatch.unit_cost
        "Giá vốn ảnh chụp (đ/kg)", max_digits=14, decimal_places=4,
    )

    class Meta:
        verbose_name = "Dòng chứng từ đảo"
        verbose_name_plural = "Dòng chứng từ đảo"
        default_permissions = ("view",)

    def __str__(self):
        return f"{self.credit_note.code} ⇐ {self.batch.batch_id} × {self.qty}kg"
