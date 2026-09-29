from django.db import models


class Category(models.Model):
    """Chuyên mục bài viết (§2.1 02b-tech-design)."""

    name = models.CharField(max_length=80)
    name_key = models.CharField(max_length=80, unique=True, db_index=True)
    slug = models.CharField(max_length=80, unique=True, db_index=True)
    description = models.CharField(max_length=300, blank=True, default="")
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        default_permissions = ("view", "add", "change")

    def __str__(self):
        return self.name
