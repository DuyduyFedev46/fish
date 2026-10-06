"""
Giao hàng (P-06) và CSKH gọi xác nhận (2026-09-28-cskh-xac-nhan-in-tem).
100% giao tận nhà bởi nhân viên nội bộ.

- BR-GH-01: người giao là nhân viên nội bộ, FK trỏ `User` (StaffProfile cấp SĐT).
- BR-GH-03: số kg cân khi soạn = số kg khách đặt (giả định V1).
- BR-GH-11: đơn đã thanh toán vào CONFIRMING trước khi soạn hàng.
- BR-GH-18: phạm vi xem dữ liệu cá nhân khách cho nhóm customer_service.
- BR-GH-22: báo giao thất bại phải có lý do (`failure_reason`); "Khác" đòi ghi chú (ERP theo design, Lô 4, B5).
- BR-GH-23: giao / đổi người giao bằng quyền riêng `assign_deliverynote` (ERP theo design, Lô 4, B6).
"""
from django.conf import settings
from django.db import models


class DeliveryNote(models.Model):
    class Status(models.TextChoices):
        CONFIRMING = "CONFIRMING", "Chờ xác nhận"
        PREPARING = "PREPARING", "Soạn hàng"
        READY = "READY", "Chờ lấy hàng"
        DELIVERING = "DELIVERING", "Đang giao"
        COMPLETED = "COMPLETED", "Hoàn tất"      # điểm không quay lui (BR-GH-05)
        FAILED = "FAILED", "Giao thất bại"       # trạng thái tạm (BR-GH-04)
        CANCELLED = "CANCELLED", "Đã huỷ theo đơn"  # S14: đơn bị huỷ (BR-GH-07), không quay lui

    code = models.CharField("Mã phiếu giao", max_length=32, unique=True)
    sales_invoice = models.ForeignKey(
        "sales.SalesInvoice", on_delete=models.PROTECT, related_name="delivery_notes",
        verbose_name="Hoá đơn",
    )
    status = models.CharField(
        "Trạng thái", max_length=12, choices=Status.choices, default=Status.PREPARING
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="deliveries", verbose_name="Nhân viên giao",  # BR-GH-01
    )
    failed_attempts = models.PositiveSmallIntegerField("Số lần giao thất bại", default=0)

    class FailureReason(models.TextChoices):
        """BR-GH-22. Mã là hợp đồng với FE và với `apps/sales/orders/reasons.py` (nhãn lý do của đơn)."""
        NOT_MET = "NOT_MET", "Không gặp khách"
        REFUSED = "REFUSED", "Khách từ chối nhận"
        WRONG_ADDRESS = "WRONG_ADDRESS", "Sai địa chỉ"
        DAMAGED = "DAMAGED", "Hàng hư khi giao"
        OTHER = "OTHER", "Khác"

    # Lý do của lần thất bại gần nhất. Giao lại (FAILED -> DELIVERING) giữ nguyên tới khi có lần mới;
    # lịch sử từng lần nằm ở AuditLog (chỉ mã lý do, không chép ghi chú).
    failure_reason = models.CharField(
        "Lý do giao thất bại", max_length=16, choices=FailureReason.choices, blank=True, default=""
    )
    # Chữ tự do của người giao, có thể chứa dữ liệu cá nhân: không vào AuditLog, log, AI (bất biến 9).
    failure_note = models.CharField("Ghi chú giao thất bại", max_length=200, blank=True, default="")
    note = models.TextField("Ghi chú", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField("Thời điểm hoàn tất", null=True, blank=True)
    # Duy chốt 02/10 (#18): mốc cho "đã giao bao lâu" và "thất bại lúc nào". Ghi đè mỗi lần (giao lại, thất bại lại);
    # lịch sử từng lần nằm ở AuditLog. Phiếu cũ để null.
    delivery_started_at = models.DateTimeField("Bắt đầu giao lúc", null=True, blank=True)
    failed_at = models.DateTimeField("Giao thất bại lúc", null=True, blank=True)

    # CSKH xác nhận & người nhận hộ (2026-09-28-cskh-xac-nhan-in-tem)
    confirmed_at = models.DateTimeField("Thời điểm xác nhận", null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="+", verbose_name="Người xác nhận",
    )
    confirm_skipped = models.BooleanField("Bỏ qua xác nhận", default=False)
    recipient_name = models.CharField("Tên người nhận", max_length=200, blank=True, default="")
    recipient_phone = models.CharField("SĐT người nhận", max_length=20, blank=True, default="")

    class Meta:
        verbose_name = "Phiếu giao hàng"
        verbose_name_plural = "Phiếu giao hàng"
        ordering = ["-created_at", "-id"]
        permissions = [
            ("confirm_with_customer", "Gọi xác nhận đơn"),
            ("change_recipient", "Đổi thông tin nhận hàng"),
            ("decide_unconfirmed", "Quyết định đơn không liên lạc được"),
            ("pack_deliverynote", "Đóng gói phiếu giao"),
            ("print_label", "In / huỷ tem giao"),
            ("assign_deliverynote", "Giao phiếu cho người giao"),
        ]

    def __str__(self):
        return self.code


class ConfirmationTask(models.Model):
    """Mục chờ gọi CSKH, 1-1 với phiếu giao (02b §2.2)."""

    class State(models.TextChoices):
        PENDING = "PENDING", "Chờ gọi"
        CALLBACK = "CALLBACK", "Hẹn gọi lại"
        ESCALATED = "ESCALATED", "Cần quyết định"
        REFUND_CALL = "REFUND_CALL", "Gọi báo hoàn tiền"
        DONE = "DONE", "Hoàn tất"

    class EscalationReason(models.TextChoices):
        UNREACHABLE = "UNREACHABLE", "Không nghe máy"
        WRONG_NUMBER = "WRONG_NUMBER", "Sai số"
        WANT_CANCEL = "WANT_CANCEL", "Khách muốn huỷ"
        WANT_CHANGE = "WANT_CHANGE", "Khách muốn đổi"

    note = models.OneToOneField(
        DeliveryNote, on_delete=models.PROTECT, related_name="confirmation",
        verbose_name="Phiếu giao",
    )
    state = models.CharField(
        "Tình trạng gọi", max_length=12, choices=State.choices, default=State.PENDING, db_index=True
    )
    escalation_reason = models.CharField(
        "Lý do cần quyết định", max_length=16, choices=EscalationReason.choices, blank=True, default=""
    )
    attempts = models.PositiveSmallIntegerField("Số lần gọi không được", default=0)
    first_unreachable_at = models.DateTimeField("Lần đầu không liên lạc được", null=True, blank=True)
    last_unreachable_at = models.DateTimeField("Lần gần nhất không liên lạc được", null=True, blank=True)
    callback_at = models.DateTimeField("Hẹn gọi lại lúc", null=True, blank=True)
    escalated_at = models.DateTimeField("Chuyển Quản lý lúc", null=True, blank=True, db_index=True)
    auto_cancel_blocked_code = models.CharField("Mã chặn tự huỷ", max_length=16, blank=True, default="")
    auto_cancelled_at = models.DateTimeField("Thời điểm Hệ thống tự huỷ", null=True, blank=True)
    refund = models.ForeignKey(
        "sales.Refund", on_delete=models.PROTECT, null=True, blank=True, related_name="+",
        verbose_name="Phiếu hoàn tiền liên quan",
    )
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
        verbose_name="Người đang xử lý",
    )
    claimed_until = models.DateTimeField("Hạn giữ xử lý", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mục chờ gọi CSKH"
        verbose_name_plural = "Mục chờ gọi CSKH"
        default_permissions = ()
        indexes = [
            models.Index(fields=["state", "escalated_at"]),
        ]

    def __str__(self):
        return f"Chờ gọi {self.note_id}"


class CustomerCall(models.Model):
    """Bản ghi cuộc gọi — append-only (02b §2.3)."""

    class Result(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Đã xác nhận"
        CONFIRMED_CHANGED = "CONFIRMED_CHANGED", "Xác nhận có đổi thông tin"
        UNREACHABLE = "UNREACHABLE", "Không nghe máy"
        WRONG_NUMBER = "WRONG_NUMBER", "Sai số"
        CALLBACK = "CALLBACK", "Hẹn gọi lại"
        WANT_CHANGE = "WANT_CHANGE", "Khách muốn đổi món/số lượng"
        WANT_CANCEL = "WANT_CANCEL", "Khách muốn huỷ"
        NOTIFIED = "NOTIFIED", "Đã báo hoàn tiền"

    note = models.ForeignKey(
        DeliveryNote, on_delete=models.PROTECT, related_name="calls", verbose_name="Phiếu giao"
    )
    result = models.CharField("Kết quả gọi", max_length=20, choices=Result.choices)
    note_text = models.CharField("Ghi chú cuộc gọi", max_length=200, blank=True, default="")
    callback_at = models.DateTimeField("Hẹn gọi lại lúc", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Người gọi"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    request_id = models.UUIDField("Mã chống trùng", unique=True, null=True, blank=True)

    class Meta:
        verbose_name = "Bản ghi cuộc gọi"
        verbose_name_plural = "Bản ghi cuộc gọi"
        default_permissions = ()
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["created_by", "created_at"]),
        ]

    def __str__(self):
        return f"Cuộc gọi #{self.pk} · {self.result}"


class LabelPrint(models.Model):
    """Lượt in tem giao hàng (02b §2.4)."""

    class Reason(models.TextChoices):
        FIRST = "FIRST", "In lần đầu"
        REPRINT = "REPRINT", "In lại"
        ADDRESS_CHANGED = "ADDRESS_CHANGED", "Đổi thông tin nhận"

    note = models.ForeignKey(
        DeliveryNote, on_delete=models.PROTECT, related_name="label_prints", verbose_name="Phiếu giao"
    )
    print_no = models.PositiveSmallIntegerField("Số thứ tự in")
    reason = models.CharField("Lý do in", max_length=16, choices=Reason.choices, default=Reason.FIRST)
    printed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Người in"
    )
    printed_at = models.DateTimeField(auto_now_add=True)
    request_id = models.UUIDField("Mã chống trùng", unique=True, null=True, blank=True)
    superseded_at = models.DateTimeField("Thời điểm bị thay thế", null=True, blank=True)
    voided_at = models.DateTimeField("Thời điểm huỷ tem", null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
        verbose_name="Người huỷ tem",
    )

    class Meta:
        verbose_name = "Lượt in tem giao"
        verbose_name_plural = "Lượt in tem giao"
        default_permissions = ()
        ordering = ["print_no"]
        constraints = [
            models.UniqueConstraint(fields=["note", "print_no"], name="uniq_delivery_label_print"),
        ]

    def __str__(self):
        return f"Lượt in #{self.print_no} cho {self.note.code}"


class CallScript(models.Model):
    """
    Kịch bản gọi soạn sẵn theo tình huống (CS-18, 02b §2.6). Không AI, không chứa dữ liệu cá nhân của khách
    (service chặn chuỗi số dài, BR-GH-19). Không xoá: tắt bằng `is_active`.
    """

    class Situation(models.TextChoices):
        FIRST_ORDER = "FIRST_ORDER", "Khách mua lần đầu"
        RETURNING = "RETURNING", "Khách quen"
        COMBO = "COMBO", "Đơn có combo"
        GENERAL = "GENERAL", "Lời dặn chung"

    situation = models.CharField("Tình huống", max_length=16, choices=Situation.choices, unique=True)
    content = models.TextField("Nội dung", max_length=2000)
    is_active = models.BooleanField("Đang dùng", default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name="Người sửa cuối"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kịch bản gọi"
        verbose_name_plural = "Kịch bản gọi"
        default_permissions = ("view", "add", "change")
        ordering = ["situation"]

    def __str__(self):
        return f"Kịch bản {self.situation}"
