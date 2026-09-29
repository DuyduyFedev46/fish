from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.exceptions import BusinessError


class Entry(models.Model):
    """Bài viết hoặc Trang nội dung (§2.2 02b-tech-design)."""

    KIND_CHOICES = [("post", "Bài viết"), ("page", "Trang")]
    STATUS_CHOICES = [
        ("draft", "Nháp"),
        ("pending_review", "Chờ duyệt"),
        ("published", "Đã đăng"),
        ("unpublished", "Đã gỡ"),
    ]
    PAGE_ROLE_CHOICES = [
        ("privacy", "Bảo mật"),
        ("terms", "Điều kiện giao dịch"),
        ("refund", "Đổi trả hoàn tiền"),
        ("seller_info", "Thông tin người bán"),
    ]
    SOURCE_CHOICES = [("human", "Người dùng"), ("ai", "AI")]

    kind = models.CharField(max_length=8, choices=KIND_CHOICES, default="post")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft", db_index=True)
    title = models.CharField(max_length=255, blank=True, default="")
    slug = models.CharField(max_length=120, unique=True, db_index=True)
    category = models.ForeignKey(
        "content.Category", on_delete=models.PROTECT, null=True, blank=True, related_name="entries"
    )
    excerpt = models.TextField(blank=True, default="")
    seo_title = models.CharField(max_length=200, blank=True, default="")
    seo_description = models.CharField(max_length=300, blank=True, default="")
    cover_image = models.ForeignKey(
        "content.ContentImage", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    body = models.JSONField(default=dict)
    draft_hash = models.CharField(max_length=64, blank=True, default="")
    published_version = models.ForeignKey(
        "content.EntryVersion", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    first_published_at = models.DateTimeField(null=True, blank=True)
    last_published_at = models.DateTimeField(null=True, blank=True)
    restored_from = models.PositiveIntegerField(null=True, blank=True)
    return_reason = models.CharField(max_length=20, blank=True, default="")
    page_role = models.CharField(max_length=16, null=True, blank=True, choices=PAGE_ROLE_CHOICES)
    show_in_footer = models.BooleanField(default=False)
    footer_order = models.PositiveSmallIntegerField(default=0)
    source = models.CharField(max_length=8, choices=SOURCE_CHOICES, default="human")
    row_version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_content_entries"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="updated_content_entries"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [("publish_entry", "Đăng, gỡ, trả về nháp bài; đặt trang go-live và footer")]
        constraints = [
            models.UniqueConstraint(
                fields=["page_role"], condition=Q(page_role__isnull=False), name="unique_entry_page_role"
            )
        ]
        indexes = [
            models.Index(fields=["kind", "status", "first_published_at"], name="idx_content_entry_pub")
        ]

    def __str__(self):
        # __str__ trả f"Nội dung #{self.pk}", KHÔNG trả tiêu đề — record_audit chép str(obj) vào AuditLog.object_repr; CMS-07-AC2 cấm tiêu đề trong AuditLog.
        return f"Nội dung #{self.pk}"


class EntryVersionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise BusinessError("Không được sửa phiên bản đã đăng (BR-ND-05).", code="BR-ND-05")

    def delete(self):
        raise BusinessError("Không được xoá phiên bản đã đăng (BR-ND-05).", code="BR-ND-05")


class EntryVersion(models.Model):
    """Bản chụp append-only của bài khi đăng (§2.3 02b-tech-design)."""

    entry = models.ForeignKey("content.Entry", on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    kind = models.CharField(max_length=8)
    title = models.CharField(max_length=255, blank=True, default="")
    slug = models.CharField(max_length=120)
    excerpt = models.TextField(blank=True, default="")
    seo_title = models.CharField(max_length=200, blank=True, default="")
    seo_description = models.CharField(max_length=300, blank=True, default="")
    body = models.JSONField(default=dict)
    description = models.CharField(max_length=300, blank=True, default="")
    category = models.ForeignKey(
        "content.Category", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    cover_image = models.ForeignKey(
        "content.ContentImage", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    content_hash = models.CharField(max_length=64, blank=True, default="")
    restored_from = models.PositiveIntegerField(null=True, blank=True)
    published_at = models.DateTimeField()
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="published_entry_versions"
    )

    objects = EntryVersionQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["entry", "version"], name="unique_entry_version")
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise BusinessError("Không được sửa phiên bản đã đăng (BR-ND-05).", code="BR-ND-05")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise BusinessError("Không được xoá phiên bản đã đăng (BR-ND-05).", code="BR-ND-05")

    def __str__(self):
        return f"Phiên bản {self.version} của nội dung #{self.entry_id}"
