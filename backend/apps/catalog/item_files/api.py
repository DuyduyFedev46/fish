"""
API tải và nhập file Excel mặt hàng (FISH-66 S3, S4, S5, S6).
`APIView` riêng, KHÔNG phải `@action` của `ItemViewSet`, và chỉ dùng `MultiPartParser`, để bộ dò lệnh AI
(`apps/ai/registry/discovery.py`) không tự đăng ký thành lệnh AI (02b D6).
View mỏng: kiểm quyền, gọi service, trả kết quả.
"""
from django.http import HttpResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import require_perm

from . import services
from .columns import IMPORT_PERMS, VIEW_ITEMS_PERM

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _file_response(content, filename, row_count):
    response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Row-Count"] = str(row_count)
    response["Cache-Control"] = "no-store"
    return response


def _require_import_perms(user):
    for perm in IMPORT_PERMS:
        require_perm(user, perm)


class ItemExportView(APIView):
    """GET /api/catalog/items/export/ — Chủ, Quản lý (17 cột), NV kho (14 cột, không cột giá)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    http_method_names = ["get", "options"]

    def get(self, request):
        require_perm(request.user, VIEW_ITEMS_PERM)
        content, row_count = services.export_items(user=request.user, params=request.query_params)
        return _file_response(content, services.export_filename(), row_count)


class ItemExportTemplateView(APIView):
    """GET /api/catalog/items/export-template/ — cùng quyền với tải danh sách (C-2)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    http_method_names = ["get", "options"]

    def get(self, request):
        require_perm(request.user, VIEW_ITEMS_PERM)
        content, row_count = services.export_template(user=request.user)
        return _file_response(content, services.TEMPLATE_FILENAME, row_count)


class ItemImportLimitsView(APIView):
    """GET /api/catalog/items/import/limits/ — trả các ngưỡng nhập Excel từ settings (02b §3.4)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    http_method_names = ["get", "options"]

    def get(self, request):
        _require_import_perms(request.user)
        return Response(services.get_import_limits())


class ItemImportPreviewView(APIView):
    """POST /api/catalog/items/import/preview/ — đọc file .xlsx và trả bảng xem trước + preview_token (02b §3.5)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    http_method_names = ["post", "options"]

    def post(self, request):
        _require_import_perms(request.user)
        data = services.preview_import(user=request.user, uploaded_file=request.FILES.get("file"))
        return Response(data)


class ItemImportCommitView(APIView):
    """POST /api/catalog/items/import/commit/ — xác nhận và ghi thay đổi theo file + preview_token (02b §3.6)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    http_method_names = ["post", "options"]

    def post(self, request):
        _require_import_perms(request.user)
        preview_token = request.data.get("preview_token") if hasattr(request.data, "get") else ""
        uploaded_file = request.FILES.get("file")
        data = services.commit_import(
            user=request.user,
            uploaded_file=uploaded_file,
            preview_token=preview_token or "",
        )
        return Response(data)
