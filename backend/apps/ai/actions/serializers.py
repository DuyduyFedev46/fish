"""
Serializers cho Việc AI (02b §6.4, DW-11).
"""
from rest_framework import serializers
from apps.ai.execution.scrub import scrub_data
from apps.ai.models import AiAction
from apps.ai.registry.discovery import get_registry


class AiActionSerializer(serializers.ModelSerializer):
    """
    Serializer danh sách / chi tiết việc AI.
    - args_preview: lọc theo quyền NGƯỜI XEM (giá vốn) và lọc bỏ PII.
    - target: chỉ chứa type + code, tuyệt đối không chứa PII hay object_repr.
    """

    title = serializers.SerializerMethodField()
    owner_display = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    args_preview = serializers.SerializerMethodField()
    confirm_nonce = serializers.SerializerMethodField()

    class Meta:
        model = AiAction
        fields = [
            "id",
            "command",
            "title",
            "kind",
            "level",
            "status",
            "owner_display",
            "created_at",
            "expires_at",
            "execute_after",
            "undo_until",
            "viewed_at",
            "target",
            "args_preview",
            "downgrade_reason",
            "result_ref",
            "confirm_nonce",
            "assignee_group",
        ]

    def get_title(self, obj) -> str:
        spec = get_registry().get(obj.command)
        return spec.title if spec else obj.command

    def get_owner_display(self, obj) -> str:
        name = obj.owner.first_name or obj.owner.get_full_name() or obj.owner.username
        return f"AI của {name}"

    def get_target(self, obj) -> dict:
        # DW-11-AC8: target chỉ loại + mã; không tên/SĐT/địa chỉ; không object_repr
        return {
            "type": obj.target_model or "document",
            "code": obj.target_id or "",
        }

    def get_args_preview(self, obj) -> dict:
        # DW-11-AC7: Lọc theo quyền của NGƯỜI XEM (request.user)
        request = self.context.get("request")
        user = request.user if request else None
        return scrub_data(obj.args or {}, user=user, is_ai_read=False)

    def get_confirm_nonce(self, obj) -> str:
        # Trả về confirm_nonce phục vụ xác nhận sau khi xem chi tiết
        import hashlib
        raw = f"{obj.id}:{obj.created_at.isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
