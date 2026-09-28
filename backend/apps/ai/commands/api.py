"""
Catalog lệnh — GET /api/commands/catalog (S01).

Trả lệnh `status=active` lọc theo `min_permissions` của user đăng nhập (S01-AC2/AC3 —
BR-AI-04). Registry là code: không query DB nghiệp vụ (C.4 #11). Chưa đăng nhập → 401,
không lộ tên lệnh (S01-AC5).
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .registry import active_commands_for
from .serializers import command_item


class CommandCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"commands": [command_item(s) for s in active_commands_for(request.user)]})
