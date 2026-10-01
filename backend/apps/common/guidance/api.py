"""
API endpoint cho khối Tiếp theo · Đã làm: GET /api/guidance/<loại>/<id>/ (02b §6.7).

Quy tắc:
- Không nằm dưới /api/ai/, KHÔNG BAO GIỜ trả 410 khi AI tắt.
- Quyền: T1 view_<model> + T3 scope giống hệt API chi tiết tương ứng.
- Không mở /api/audit-logs/ cho NV kho / NV giao.
"""
from importlib import import_module
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


# Loại chứng từ → module đăng ký provider (nạp lười để tránh import vòng).
_LAZY_MODULES: dict[str, str] = {
    "order": "apps.sales.orders.next_steps",
    "refund": "apps.sales.refunds.next_steps",
    "payment": "apps.sales.payments.next_steps",
    "batch": "apps.inventory.batches.next_steps",
    # Lô 2 (R2): provider chỉ có dòng thời gian (audit_timeline.py).
    "receipt": "apps.purchasing.receipts.next_steps",
    "supplier": "apps.purchasing.receipts.next_steps",
    "stocktake": "apps.inventory.stocktake.next_steps",
    "return": "apps.inventory.returns.next_steps",
    "delivery": "apps.delivery.next_steps",
    "item": "apps.catalog.items.next_steps",
    "customer": "apps.sales.customers.next_steps",
    "staff": "apps.accounts.staff.next_steps",
    # Lô 14 (B4): dòng thời gian nhóm quyền.
    "group": "apps.accounts.capabilities.next_steps",
}


def get_guidance_provider(doc_type: str) -> Callable[..., dict[str, Any]] | None:
    if doc_type not in _PROVIDERS and doc_type in _LAZY_MODULES:
        import_module(_LAZY_MODULES[doc_type])
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
                {"detail": "Không hỗ trợ loại chứng từ này.", "code": "GUIDANCE_TYPE_UNKNOWN"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = provider(doc_id=doc_id, user=request.user, request=request)
        response = Response(data, status=status.HTTP_200_OK)
        if getattr(provider, "no_store", False):
            # Đối tượng gắn dữ liệu khách (phiếu giao, khách): không cho cache (bất biến 9).
            response["Cache-Control"] = "no-store"
        return response
