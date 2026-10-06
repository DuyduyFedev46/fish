"""
API kịch bản gọi (CS-18, 02b §4.6): `/api/confirmation/scripts/`.
Chủ soạn (add/change_callscript); Quản lý và CSKH chỉ đọc (view_callscript); Kho, Giao không thấy (BR-PQ-12).
Không xoá (DELETE trả 405): tắt bằng `is_active`. Người chỉ đọc chỉ thấy kịch bản đang dùng.
Không dữ liệu cá nhân, không giá, không AI.
"""
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import NoStoreMixin
from apps.delivery.confirmation import call_scripts
from apps.delivery.models import CallScript


def serialize_script(script: CallScript, *, with_state: bool = True) -> dict:
    data = {
        "situation": script.situation,
        "situation_label": script.get_situation_display(),
        "content": script.content,
    }
    if with_state:
        data["is_active"] = script.is_active
    return data


class CallScriptViewSet(NoStoreMixin, viewsets.GenericViewSet):
    lookup_field = "situation"
    permission_classes = [IsAuthenticated]
    queryset = CallScript.objects.all()
    required_perms: tuple = ()

    def _require(self, request, codename, message):
        if not request.user.has_perm(f"delivery.{codename}"):
            raise PermissionDenied(message)

    def list(self, request, *args, **kwargs):
        self._require(request, "view_callscript", "Bạn không có quyền xem kịch bản gọi.")
        qs = CallScript.objects.all()
        if not request.user.has_perm("delivery.change_callscript"):
            qs = qs.filter(is_active=True)
        return Response({"results": [serialize_script(s) for s in qs.order_by("situation")]})

    def create(self, request, *args, **kwargs):
        self._require(request, "add_callscript", "Chỉ Chủ được soạn kịch bản gọi.")
        data = request.data or {}
        script = call_scripts.create_script(
            actor=request.user,
            situation=data.get("situation"),
            content=data.get("content"),
            is_active=data.get("is_active", True),
        )
        return Response(serialize_script(script), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        self._require(request, "change_callscript", "Chỉ Chủ được sửa kịch bản gọi.")
        script = CallScript.objects.filter(situation=kwargs.get("situation")).first()
        if not script:
            raise NotFound("Không tìm thấy kịch bản.")
        data = request.data or {}
        script = call_scripts.update_script(
            actor=request.user, script=script, content=data.get("content"), is_active=data.get("is_active"),
        )
        return Response(serialize_script(script))
