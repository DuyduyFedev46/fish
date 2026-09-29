"""Serializers cho Entry (§8.3 02b-tech-design)."""
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from apps.content.models.entries import Entry
from apps.content.images.serializers import ContentImageSerializer


class EntryListSerializer(serializers.ModelSerializer):
    has_unpublished_changes = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Entry
        fields = [
            "id",
            "kind",
            "status",
            "title",
            "slug",
            "category",
            "has_unpublished_changes",
            "updated_at",
            "source",
            "page_role",
        ]

    def get_has_unpublished_changes(self, obj: Entry) -> bool:
        if obj.published_version_id is None:
            return False
        return obj.draft_hash != obj.published_version.content_hash

    def get_updated_at(self, obj: Entry) -> str:
        return timezone.localtime(obj.updated_at).isoformat()


class EntryDetailSerializer(serializers.ModelSerializer):
    slug_locked = serializers.SerializerMethodField()
    has_unpublished_changes = serializers.SerializerMethodField()
    required_for_golive = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()
    images = ContentImageSerializer(many=True, read_only=True)
    first_published_at = serializers.SerializerMethodField()
    last_published_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Entry
        fields = [
            "id",
            "kind",
            "status",
            "title",
            "slug",
            "slug_locked",
            "category",
            "excerpt",
            "seo_title",
            "seo_description",
            "cover_image",
            "body",
            "images",
            "has_unpublished_changes",
            "published_version",
            "first_published_at",
            "last_published_at",
            "restored_from",
            "return_reason",
            "page_role",
            "required_for_golive",
            "show_in_footer",
            "footer_order",
            "public_url",
            "source",
            "row_version",
            "updated_at",
        ]

    def get_slug_locked(self, obj: Entry) -> bool:
        return obj.first_published_at is not None

    def get_has_unpublished_changes(self, obj: Entry) -> bool:
        if obj.published_version_id is None:
            return False
        return obj.draft_hash != obj.published_version.content_hash

    def get_required_for_golive(self, obj: Entry) -> bool:
        return obj.page_role is not None

    def get_public_url(self, obj: Entry) -> str | None:
        if obj.first_published_at is None:
            return None
        base_url = getattr(settings, "SHOP_BASE_URL", "").rstrip("/")
        path = f"/bai-viet/?slug={obj.slug}" if obj.kind == "post" else f"/trang/?slug={obj.slug}"
        return f"{base_url}{path}"

    def get_first_published_at(self, obj: Entry) -> str | None:
        if not obj.first_published_at:
            return None
        return timezone.localtime(obj.first_published_at).isoformat()

    def get_last_published_at(self, obj: Entry) -> str | None:
        if not obj.last_published_at:
            return None
        return timezone.localtime(obj.last_published_at).isoformat()

    def get_updated_at(self, obj: Entry) -> str:
        return timezone.localtime(obj.updated_at).isoformat()


class EntryVersionListSerializer(serializers.Serializer):
    """
    Serializer cho danh sách phiên bản của một bài viết (§8.5, CMS-11-AC1).
    Tuyệt đối không trả body ở danh sách phiên bản (CMS-11-AC1).
    published_by_name chỉ có ở ERP (CMS-11-AC5).
    """

    version = serializers.IntegerField()
    published_at = serializers.SerializerMethodField()
    published_by_name = serializers.SerializerMethodField()
    title = serializers.CharField()
    restored_from = serializers.IntegerField(allow_null=True)

    def get_published_at(self, obj) -> str:
        return timezone.localtime(obj.published_at).isoformat()

    def get_published_by_name(self, obj) -> str:
        if not obj.published_by:
            return ""
        staff_profile = getattr(obj.published_by, "staff_profile", None)
        if staff_profile and getattr(staff_profile, "display_name", None):
            return staff_profile.display_name
        return obj.published_by.username


class EntryVersionDetailSerializer(serializers.Serializer):
    """
    Serializer chi tiết một phiên bản của bài viết (§8.5, CMS-11).
    """

    version = serializers.IntegerField()
    published_at = serializers.SerializerMethodField()
    published_by_name = serializers.SerializerMethodField()
    kind = serializers.CharField()
    title = serializers.CharField()
    slug = serializers.CharField()
    excerpt = serializers.CharField()
    seo_title = serializers.CharField()
    seo_description = serializers.CharField()
    description = serializers.CharField()
    category = serializers.IntegerField(source="category_id", allow_null=True)
    cover_image = serializers.IntegerField(source="cover_image_id", allow_null=True)
    body = serializers.DictField()
    restored_from = serializers.IntegerField(allow_null=True)

    def get_published_at(self, obj) -> str:
        return timezone.localtime(obj.published_at).isoformat()

    def get_published_by_name(self, obj) -> str:
        if not obj.published_by:
            return ""
        staff_profile = getattr(obj.published_by, "staff_profile", None)
        if staff_profile and getattr(staff_profile, "display_name", None):
            return staff_profile.display_name
        return obj.published_by.username

