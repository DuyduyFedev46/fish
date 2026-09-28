"""
Serializers cho chính sách AI của Chủ (DW-13).
"""
from rest_framework import serializers
from apps.ai.models.policy import AiPolicyVersion


class PolicyUpdateSerializer(serializers.Serializer):
    base_version = serializers.IntegerField(required=True, min_value=0)
    global_mode = serializers.ChoiceField(
        choices=AiPolicyVersion.GlobalMode.choices,
        required=False,
    )
    red_zone = serializers.DictField(required=False)
    caps = serializers.DictField(required=False)
    acknowledge_responsibility = serializers.BooleanField(required=True)


class AdminUserKillSerializer(serializers.Serializer):
    killed = serializers.BooleanField(required=True)


class AiPolicyVersionListSerializer(serializers.ModelSerializer):
    created_by_display = serializers.SerializerMethodField()

    class Meta:
        model = AiPolicyVersion
        fields = [
            "version",
            "global_mode",
            "created_at",
            "created_by_display",
            "note",
        ]

    def get_created_by_display(self, obj) -> str:
        if not obj.created_by:
            return "Hệ thống"
        return obj.created_by.get_full_name() or obj.created_by.username
