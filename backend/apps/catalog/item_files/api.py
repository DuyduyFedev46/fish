"""
API tải file Excel mặt hàng (FISH-66 S3, S4). `APIView` riêng, KHÔNG phải `@action` của `ItemViewSet`, và không có
JSON parser, để bộ dò lệnh AI (`apps/ai/registry/discovery.py`) không tự đăng ký thành lệnh AI (02b D6).
View mỏng: kiểm quyền, gọi service, trả file.
"""
from django.http import HttpResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api import require_perm

from . import services
from .columns import VIEW_ITEMS_PERM

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _file_response(content, filename, row_count):
    response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Row-Count"] = str(row_count)
    response["Cache-Control"] = "no-store"
    return response


class ItemExportView(APIView):
    """GET /api/catalog/items/export/ — Chủ, Quản lý (17 cột), NV kho (14 cột, không cột giá)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        require_perm(request.user, VIEW_ITEMS_PERM)
        content, row_count = services.export_items(user=request.user, params=request.query_params)
        return _file_response(content, services.export_filename(), row_count)


class ItemExportTemplateView(APIView):
    """GET /api/catalog/items/export-template/ — cùng quyền với tải danh sách (C-2)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        require_perm(request.user, VIEW_ITEMS_PERM)
        content, row_count = services.export_template(user=request.user)
        return _file_response(content, services.TEMPLATE_FILENAME, row_count)
