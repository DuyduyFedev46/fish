"""Phiếu hoàn tiền (P-07, BR-HT-01/03/07)."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .invoices import SalesInvoice
from .payments import PaymentTransaction


class Refund(models.Model):
    """
    Phiếu hoàn tiền (P-07) — entity riêng (BR-HT-01), không phải field trên đơn.
    Tách quyền: create_refund (Chủ + Quản lý) ≠ confirm_refund (chỉ Chủ) — BR-HT-07.
    Thực thi V1 là chuyển khoản tay; hệ thống chỉ ghi sổ.

    Gắn ĐÚNG MỘT trong hai (S13 / Q9): hoá đơn (tiền đã ghi doanh thu) hoặc giao dịch thanh
    toán không có hoá đơn (tiền về sau khi huỷ / thiếu mà khách không bù / chuyển thừa).
    """

    class Method(models.TextChoices):
        MANUAL_TRANSFER = "MANUAL_TRANSFER", "Chuyển khoản tay"  # V1
        GATEWAY = "GATEWAY", "Qua cổng (chưa hiện thực)"        # chỗ chừa sẵn

    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ hoàn"
        REFUNDED = "REFUNDED", "Đã hoàn"
        FAILED = "FAILED", "Thất bại"

    sales_invoice = models.ForeignKey(
        SalesInvoice, on_delete=models.PROTECT, related_name="refunds", verbose_name="Hoá đơn",
        null=True, blank=True,
    )
    payment_transaction = models.ForeignKey(
        PaymentTransaction, on_delete=models.PROTECT, related_name="refunds",
        verbose_name="Giao dịch thanh toán (không hoá đơn)", null=True, blank=True,
    )
    # Q12 (S13/S15): khoá chống tạo trùng do FE sinh khi mở form, gửi lại y nguyên khi thử lại.
    request_id = models.UUIDField("Mã yêu cầu (chống trùng)", null=True, blank=True, unique=True)
    amount = models.DecimalField(
        "Số tiền hoàn", max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    is_partial = models.BooleanField("Hoàn một phần", default=False)  # BR-HT-02
    method = models.CharField(
        "Phương thức", max_length=16, choices=Method.choices, default=Method.MANUAL_TRANSFER
    )
    status = models.CharField(
        "Trạng thái", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    bank_txn_ref = models.CharField(
        "Mã giao dịch chuyển khoản", max_length=100, blank=True,
        help_text="Bắt buộc khi chuyển sang Đã hoàn (BR-HT-03).",
    )
    reason = models.TextField("Lý do", blank=True)
    # S16 (BR-HT-09): lý do Chủ báo chuyển khoản thất bại — chỉ đổi qua `mark-failed`/`retry`.
    failure_reason = models.TextField("Lý do thất bại", blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="refunds_created",
        verbose_name="Người tạo phiếu",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="refunds_confirmed", verbose_name="Người xác nhận hoàn",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField("Thời điểm hoàn", null=True, blank=True)

    class Meta:
        verbose_name = "Phiếu hoàn tiền"
        verbose_name_plural = "Phiếu hoàn tiền"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                name="refund_exactly_one_source",
                condition=(
                    models.Q(sales_invoice__isnull=False, payment_transaction__isnull=True)
                    | models.Q(sales_invoice__isnull=True, payment_transaction__isnull=False)
                ),
            ),
        ]
        permissions = [
            ("create_refund", "Tạo phiếu hoàn tiền"),
            ("confirm_refund", "Xác nhận đã hoàn tiền (tiền rời tài khoản)"),
        ]

    def __str__(self):
        return f"HT-{self.pk} · {self.amount}đ ({self.get_status_display()})"
