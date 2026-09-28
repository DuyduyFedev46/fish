import uuid
from django.conf import settings
from django.db import models


class AiAction(models.Model):
    """
    02b §7.3: Bản ghi hành động AI (đọc mức A hoặc ghi mức C/B/D).
    id chính là proposal_ref trong AuditLog.
    """

    class Kind(models.TextChoices):
        READ = "read", "Đọc"
        WRITE = "write", "Ghi"

    class Level(models.TextChoices):
        A = "A", "Mức A"
        B = "B", "Mức B"
        C = "C", "Mức C"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ duyệt"
        CONFIRMED = "CONFIRMED", "Đã duyệt"
        REJECTED = "REJECTED", "Đã từ chối"
        EXPIRED = "EXPIRED", "Hết hạn"
        SCHEDULED = "SCHEDULED", "Đã lên lịch"
        DONE = "DONE", "Đã thực hiện"
        UNDONE = "UNDONE", "Đã hoàn tác"
        CANCELLED = "CANCELLED", "Đã huỷ"
        ESCALATED = "ESCALATED", "Đã chuyển việc"
        FAILED = "FAILED", "Thất bại"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    command = models.CharField("Mã lệnh", max_length=128)
    kind = models.CharField("Loại lệnh", max_length=10, choices=Kind.choices)
    level = models.CharField("Mức tự chủ", max_length=1, choices=Level.choices)
    status = models.CharField(
        "Trạng thái",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ai_actions",
        verbose_name="Chủ AI",
    )
    config_version = models.PositiveIntegerField(
        "Phiên bản cấu hình lúc tạo", null=True, blank=True
    )
    policy_version = models.PositiveIntegerField(
        "Phiên bản chính sách lúc tạo", null=True, blank=True
    )
    target_model = models.CharField("Model đích", max_length=100, blank=True)
    target_id = models.CharField("ID đích", max_length=64, blank=True)
    args = models.JSONField("Tham số đầu vào", default=dict, blank=True)
    idempotency_key = models.CharField("Khóa chống trùng", max_length=64, blank=True)
    channel = models.CharField("Kênh", max_length=32, default="ai_local")
    client = models.CharField("Ứng dụng client", max_length=64, default="erp-console")
    downgrade_reason = models.JSONField("Lý do hạ mức", null=True, blank=True)
    expires_at = models.DateTimeField("Hạn duyệt", null=True, blank=True)
    execute_after = models.DateTimeField("Lên lịch chạy sau", null=True, blank=True)
    undo_until = models.DateTimeField("Hạn hoàn tác", null=True, blank=True)
    viewed_at = models.DateTimeField("Thời điểm mở xem", null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Người quyết định",
    )
    decided_at = models.DateTimeField("Thời điểm quyết định", null=True, blank=True)
    executed_at = models.DateTimeField("Thời điểm thực thi", null=True, blank=True)
    created_at = models.DateTimeField("Thời điểm tạo", auto_now_add=True)
    assignee_group = models.CharField("Nhóm nhận việc", max_length=50, blank=True)
    result_ref = models.JSONField("Tham chiếu kết quả", null=True, blank=True)

    class Meta:
        verbose_name = "Hành động AI"
        verbose_name_plural = "Hành động AI"
        ordering = ["-created_at"]
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "idempotency_key"],
                condition=models.Q(idempotency_key__gt=""),
                name="uniq_owner_ai_action_idempotency",
            )
        ]
        indexes = [
            models.Index(
                fields=["owner", "status", "-created_at"],
                name="ai_action_owner_status_idx",
            ),
            models.Index(
                fields=["status", "execute_after"],
                name="ai_action_status_exec_idx",
            ),
            models.Index(fields=["created_at"], name="ai_action_created_at_idx"),
        ]

    def __str__(self):
        return f"[{self.status}] {self.command} ({self.id})"
