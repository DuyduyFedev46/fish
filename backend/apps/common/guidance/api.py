"""
API endpoint cho khối Tiếp theo · Đã làm: GET /api/guidance/<loại>/<id>/ (02b §6.7).

Quy tắc:
- Không nằm dưới /api/ai/, KHÔNG BAO GIỜ trả 410 khi AI tắt.
- Quyền: T1 view_<model> + T3 scope giống hệt API chi tiết tương ứng.
- Không mở /api/audit-logs/ cho NV kho / NV giao.
"""
from typing import Any, Callable

from django.http import Http404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

_PROVIDERS: dict[str, Callable[..., dict[str, Any]]] = {}


def register_guidance(doc_type: str, provider: Callable[..., dict[str, Any]]) -> None:
    """Đăng ký hàm cung cấp guidance cho loại chứng từ (order, refund, payment, batch...)."""
    _PROVIDERS[doc_type] = provider


def get_guidance_provider(doc_type: str) -> Callable[..., dict[str, Any]] | None:
    return _PROVIDERS.get(doc_type)


class GuidanceView(APIView):
    """
    GET /api/guidance/<loại>/<id>/
    Trả thông tin khối Tiếp theo · Đã làm cho chứng từ.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, doc_type: str, doc_id: str):
        provider = get_guidance_provider(doc_type)
        if provider is None:
            return Response(
                {"detail": f"Không hỗ trợ loại chứng từ: {doc_type}.", "code": "GUIDANCE_TYPE_UNKNOWN"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = provider(doc_id=doc_id, user=request.user, request=request)
        return Response(data, status=status.HTTP_200_OK)
