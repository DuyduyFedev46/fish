"""Giao dịch tiền vào (webhook SePay / xác nhận tay) — chống trùng theo bank_txn_id (BR-TT-03)."""
from django.db import models

from .orders import SalesOrder


class PaymentTransaction(models.Model):
    """
    Giao dịch tiền vào (từ webhook SePay qua adapter FastAPI, hoặc nhập tay).
    Chống trùng webhook bằng `bank_txn_id` unique (BR-TT-03, idempotent).
    Các case lệch (thiếu tiền / tới sau khi đã huỷ) đẩy vào hàng chờ Chủ (BR-TT-04/05).
    """

    class MatchStatus(models.TextChoices):
        MATCHED = "MATCHED", "Khớp — đã xác nhận"
        UNDERPAID = "UNDERPAID", "Thiếu tiền — chờ Chủ"       # BR-TT-04
        ORPHAN = "ORPHAN", "Đến sau khi đơn đã huỷ — chờ Chủ"  # BR-TT-05
        UNMATCHED = "UNMATCHED", "Không khớp đơn — chờ Chủ"

    class Source(models.TextChoices):
        WEBHOOK = "WEBHOOK", "Webhook SePay"
        MANUAL = "MANUAL", "Xác nhận tay"

    bank_txn_id = models.CharField("Mã giao dịch ngân hàng", max_length=100, unique=True)
    sales_order = models.ForeignKey(
        SalesOrder, on_delete=models.PROTECT, null=True, blank=True,
        related_name="payments", verbose_name="Đơn khớp",
    )
    amount = models.DecimalField("Số tiền về", max_digits=14, decimal_places=2)
    match_status = models.CharField(
        "Kết quả khớp", max_length=12, choices=MatchStatus.choices
    )
    source = models.CharField("Nguồn", max_length=8, choices=Source.choices, default=Source.WEBHOOK)
    raw_payload = models.JSONField("Payload gốc", default=dict, blank=True)
    received_at = models.DateTimeField("Thời điểm nhận")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Giao dịch thanh toán"
        verbose_name_plural = "Giao dịch thanh toán"
        ordering = ["-received_at", "-id"]

    def __str__(self):
        return f"{self.bank_txn_id} · {self.amount}đ ({self.get_match_status_display()})"
