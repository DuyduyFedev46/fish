"""
API endpoint cho chỉ mục và mô tả lệnh AI (02b §6.1, §6.2, DW-07).
"""
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.policy.effective import effective_level
from apps.ai.policy.rules import COST_KEYS, SCRUB_PII_KEYS
from .discovery import get_registry


class AiCommandsIndexView(APIView):
    """
    GET /api/ai/commands/index/
    Chỉ mục lệnh rút gọn cho FE tìm kiếm (chỉ lệnh effective_level != OFF của người gọi).
    410 khi AI_ENABLED=False.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not getattr(settings, "AI_ENABLED", False):
            return Response(
                {"detail": "Tính năng AI đang tắt.", "code": "AI_DISABLED"},
                status=status.HTTP_410_GONE,
            )

        registry = get_registry()
        user = request.user
        commands = []

        for spec in registry.get_specs():
            lvl = effective_level(user, spec)
            if lvl == "OFF":
                continue

            cmd_data = {
                "id": spec.id,
                "title": spec.title,
                "group": spec.group,
                "kind": spec.kind,
                "level": lvl,
                "screens": list(spec.screens),
                "keywords": spec.keywords,
            }
            if spec.target:
                cmd_data["target"] = spec.target
            if spec.red_zone:
                cmd_data["red_zone"] = True
            if spec.form_only:
                cmd_data["form_only"] = True

            commands.append(cmd_data)

        return Response({
            "index_version": registry.index_version,
            "config_version": 1,
            "commands": commands,
        })


class AiCommandDetailView(APIView):
    """
    GET /api/ai/commands/<id>/
    Chi tiết mô tả lệnh (schema, output_fields theo quyền).
    404 COMMAND_UNKNOWN nếu không tồn tại hoặc không có quyền (không lộ thông tin).
    410 khi AI_ENABLED=False.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, command_id):
        if not getattr(settings, "AI_ENABLED", False):
            return Response(
                {"detail": "Tính năng AI đang tắt.", "code": "AI_DISABLED"},
                status=status.HTTP_410_GONE,
            )

        registry = get_registry()
        spec = registry.get_spec(command_id)

        if spec is None:
            return Response(
                {"detail": "Không có lệnh này.", "code": "COMMAND_UNKNOWN"},
                status=status.HTTP_404_NOT_FOUND,
            )

        lvl = effective_level(request.user, spec)
        if lvl == "OFF":
            return Response(
                {"detail": "Không có lệnh này.", "code": "COMMAND_UNKNOWN"},
                status=status.HTTP_404_NOT_FOUND,
            )

        can_view_cost = request.user.has_perm("inventory.view_costprice")
        clean_output_fields = []
        for f in spec.all_output_fields:
            if f in SCRUB_PII_KEYS:
                continue
            if not can_view_cost and f in COST_KEYS:
                continue
            clean_output_fields.append(f)

        return Response({
            "id": spec.id,
            "title": spec.title,
            "description": spec.description,
            "kind": spec.kind,
            "level": lvl,
            "max_level": spec.max_level,
            "sensitivity": spec.sensitivity,
            "channel": spec.channel,
            "red_zone": spec.red_zone,
            "target": spec.target,
            "form_only": spec.form_only,
            "schema_tokens_est": spec.schema_tokens_est,
            "input_schema": spec.input_schema,
            "output_fields": clean_output_fields,
        })
