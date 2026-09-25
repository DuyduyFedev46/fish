"""Giao dịch tiền vào (webhook SePay / xác nhận tay) — chống trùng theo bank_txn_id (BR-TT-03)."""
from django.conf import settings
from django.db import models

from .orders import SalesOrder


class PaymentTransaction(models.Model):
    """
    Giao dịch tiền vào (từ webhook SePay qua adapter FastAPI, hoặc nhập tay).
    Chống trùng webhook bằng `bank_txn_id` unique (BR-TT-03, idempotent).
    Các case lệch (thiếu tiền / tới sau khi đã huỷ / không khớp / chuyển thừa) đẩy vào hàng
    chờ Chủ (BR-TT-04/05/10) và phải được Chủ ĐÓNG bằng một cách xử lý có ghi lại (BR-TT-09, S12).
    """

    class MatchStatus(models.TextChoices):
        MATCHED = "MATCHED", "Khớp — đã xác nhận"
        UNDERPAID = "UNDERPAID", "Thiếu tiền — chờ Chủ"       # BR-TT-04
        ORPHAN = "ORPHAN", "Đến sau khi đơn đã huỷ — chờ Chủ"  # BR-TT-05
        UNMATCHED = "UNMATCHED", "Không khớp đơn — chờ Chủ"
        OVERPAID = "OVERPAID", "Chuyển thừa — đơn đã thanh toán, chờ Chủ"  # BR-TT-10 (P5)

    class ResolutionStatus(models.TextChoices):
        """BR-TT-09. `null` = giao dịch khớp, không thuộc hàng chờ."""
        OPEN = "OPEN", "Chờ xử lý"
        RESOLVED = "RESOLVED", "Đã xử lý"

    class Resolution(models.TextChoices):
        ATTACHED = "ATTACHED", "Gắn vào đơn"
        CONFIRMED = "CONFIRMED", "Xác nhận đơn (khách đã bù)"
        REFUNDED = "REFUNDED", "Đã hoàn tiền"

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

    # --- S12 / BR-TT-09: hàng chờ lệch — ai đóng, lúc nào, bằng cách nào ---------
    resolution_status = models.CharField(
        "Xử lý lệch", max_length=8, choices=ResolutionStatus.choices, null=True, blank=True,
        db_index=True, help_text="Để trống = giao dịch khớp, không cần xử lý.",
    )
    resolution = models.CharField(
        "Cách xử lý", max_length=10, choices=Resolution.choices, blank=True, default="",
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="payments_resolved", verbose_name="Người xử lý",
    )
    resolved_at = models.DateTimeField("Thời điểm xử lý", null=True, blank=True)
    resolution_note = models.TextField("Ghi chú xử lý", blank=True, default="")

    class Meta:
        verbose_name = "Giao dịch thanh toán"
        verbose_name_plural = "Giao dịch thanh toán"
        ordering = ["-received_at", "-id"]

    def __str__(self):
        return f"{self.bank_txn_id} · {self.amount}đ ({self.get_match_status_display()})"
