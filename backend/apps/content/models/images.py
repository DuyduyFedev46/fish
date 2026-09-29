from django.conf import settings
from django.db import models

from apps.catalog.models.images import generate_image_id


class ContentImage(models.Model):
    """Ảnh trong bài viết / ảnh bìa (§2.4 02b-tech-design)."""

    entry = models.ForeignKey("content.Entry", on_delete=models.CASCADE, related_name="images")
    image_id = models.CharField(max_length=32, unique=True, default=generate_image_id, editable=False)
    alt = models.CharField(max_length=200, blank=True, default="")
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_content_images"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        default_permissions = ()

    def __str__(self):
        return f"Ảnh #{self.pk} ({self.image_id})"
