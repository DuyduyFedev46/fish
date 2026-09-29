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
