from rest_framework import serializers

from apps.content.models.categories import Category


class CategorySerializer(serializers.ModelSerializer):
    published_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "order", "is_active", "published_count"]
        read_only_fields = ["id", "slug", "published_count"]
