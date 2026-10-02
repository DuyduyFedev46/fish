"""GET /api/ai/status/ — mọi người dùng đã đăng nhập; luôn 200 kể cả AI tắt (S05-AC1/AC4/AC5)."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import build_status


class AiStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_status(request.user))
