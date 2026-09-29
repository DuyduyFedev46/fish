"""Serializers cho ảnh nội dung (§8.4 02b-tech-design)."""
from rest_framework import serializers
from apps.catalog.images.storage import get_storage
from apps.content.models.images import ContentImage


class ContentImageSerializer(serializers.ModelSerializer):
    urls = serializers.SerializerMethodField()

    class Meta:
        model = ContentImage
        fields = ["id", "alt", "width", "height", "urls"]

    def get_urls(self, obj: ContentImage) -> dict[str, str]:
        storage = get_storage()
        entry_id = obj.entry_id
        image_id = obj.image_id
        return {
            size: storage.url(f"content/{entry_id}/{image_id}/{size}.webp")
            for size in ("sm", "md", "lg")
        }


class ContentImageUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    alt = serializers.CharField(required=False, allow_blank=True, max_length=200, default="")


class ContentImageUpdateSerializer(serializers.Serializer):
    alt = serializers.CharField(required=True, allow_blank=True, max_length=200)
