from rest_framework import serializers

from apps.content.models.entries import Entry


class EntryListSerializer(serializers.ModelSerializer):
    """Serializer danh sách bài viết / trang cho console ERP (§8.3 02b-tech-design)."""

    has_unpublished_changes = serializers.SerializerMethodField()

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
        if not obj.published_version_id:
            return False
        return bool(obj.published_version and obj.draft_hash != obj.published_version.content_hash)
