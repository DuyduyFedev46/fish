from django.conf import settings
from django.db import models


class AiPolicyVersion(models.Model):
    """
    02b §7.2: Chính sách AI của Chủ, append-only.
    """

    class GlobalMode(models.TextChoices):
        ON = "on", "Bật"
        C_ONLY = "c_only", "Chỉ mức C"
        OFF = "off", "Tắt"

    version = models.PositiveIntegerField("Phiên bản", unique=True)
    global_mode = models.CharField(
        "Chế độ toàn cục",
        max_length=10,
        choices=GlobalMode.choices,
        default=GlobalMode.ON,
    )
    red_zone_open = models.JSONField("Trạng thái mở vùng đỏ", default=dict, blank=True)
    caps = models.JSONField("Trần của Chủ", default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="Người tạo phiên bản",
    )
    created_at = models.DateTimeField("Thời điểm tạo", auto_now_add=True)
    note = models.TextField("Ghi chú", blank=True)

    class Meta:
        verbose_name = "Phiên bản chính sách AI"
        verbose_name_plural = "Phiên bản chính sách AI"
        ordering = ["-version"]
        default_permissions = ()
        permissions = [
            ("manage_ai_policy", "Quản lý chính sách AI"),
        ]

    def __str__(self):
        return f"AI Policy v{self.version} ({self.global_mode})"
