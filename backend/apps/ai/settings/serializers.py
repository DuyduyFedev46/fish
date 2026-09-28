"""
Serializers cho màn AI của tôi (DW-12).
"""
from rest_framework import serializers
from apps.ai.models.config import AiConfigVersion


class MyConfigUpdateSerializer(serializers.Serializer):
    base_version = serializers.IntegerField(required=True, min_value=0)
    groups = serializers.DictField(required=False, default=dict)
    overrides = serializers.DictField(required=False, default=dict)
    limits = serializers.DictField(required=False, default=dict)
    acknowledge_responsibility = serializers.BooleanField(required=True)


class MyConfigKillSerializer(serializers.Serializer):
    killed = serializers.BooleanField(required=True)


class AiConfigVersionListSerializer(serializers.ModelSerializer):
    created_by_display = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()

    class Meta:
        model = AiConfigVersion
        fields = [
            "version",
            "created_at",
            "created_by_display",
            "changes",
            "note",
        ]

    def get_created_by_display(self, obj) -> str:
        # DW-12-AC11: chỉ tên hiển thị nhân viên
        if not obj.created_by:
            return "Hệ thống"
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_changes(self, obj) -> list:
        # Lấy bản ghi trước đó để so sánh thay đổi
        prev = AiConfigVersion.objects.filter(
            user=obj.user, version__lt=obj.version
        ).order_by("-version").first()

        changes = []
        old_overrides = prev.overrides if prev else {}
        for k, v in (obj.overrides or {}).items():
            old_v = old_overrides.get(k, "default")
            if old_v != v:
                changes.append({"scope": "override", "key": k, "from": old_v, "to": v})

        if prev and prev.killed != obj.killed:
            changes.append({"scope": "kill", "key": "killed", "from": prev.killed, "to": obj.killed})

        return changes
