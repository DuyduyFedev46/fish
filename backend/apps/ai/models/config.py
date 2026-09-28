from django.conf import settings
from django.db import models


class AiConfigVersion(models.Model):
    """
    02b §7.1: Cấu hình 'AI của tôi', append-only.
    Lưu cả ảnh chụp mỗi phiên bản để truy vết cấu hình hiệu lực lúc AI hành động.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ai_config_versions",
        verbose_name="Chủ AI",
    )
    version = models.PositiveIntegerField("Phiên bản")
    group_levels = models.JSONField("Mặc định nhóm", default=dict, blank=True)
    overrides = models.JSONField("Chỉnh riêng theo lệnh", default=dict, blank=True)
    limits = models.JSONField("Ngưỡng theo lệnh", default=dict, blank=True)
    killed = models.BooleanField("Tắt khẩn theo user", default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="Người tạo phiên bản",
    )
    created_at = models.DateTimeField("Thời điểm tạo", auto_now_add=True)
    note = models.TextField("Ghi chú", blank=True)

    class Meta:
        verbose_name = "Phiên bản cấu hình AI"
        verbose_name_plural = "Phiên bản cấu hình AI"
        ordering = ["-version"]
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["user", "version"], name="uniq_user_ai_config_version"
            )
        ]
        indexes = [
            models.Index(fields=["user", "-version"], name="ai_config_user_ver_idx"),
        ]

    def __str__(self):
        return f"AI Config {self.user.username} v{self.version}"
