"""
API tải lên / thay / gỡ ảnh mặt hàng — `POST` & `DELETE /api/catalog/items/{id}/image/`.

Quyền Tầng 2 `catalog.change_item_image` (Q3: chu + quan_ly). Kiểm quyền TẠI ĐÂY (không
chỉ ẩn nút ở console) — BR-PQ-12. Không dùng `BusinessModelPermissions`/`change_item`:
quyền ảnh không mở rộng sang sửa tên/hạn dùng/ẩn-hiện (spec §1.4, A2-AC15).
"""
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Item

from . import services
from .serializers import serialize_item_image

CHANGE_ITEM_IMAGE_PERM = "catalog.change_item_image"
TRUE_STRINGS = {"1", "true", "yes", "on"}


class ItemImagePermissionDenied(PermissionDenied):
    """403 `{"detail", "code": "BR-PQ-12"}` (render ở `apps.common.api.exception_handler`)."""

    default_detail = "Bạn không có quyền sửa ảnh mặt hàng (BR-PQ-12)."
    default_code = "BR-PQ-12"
    render_code = True


def _parse_bool(value, default=False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in TRUE_STRINGS


class ItemImageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _require_perm(self, request):
        if not request.user.has_perm(CHANGE_ITEM_IMAGE_PERM):
            raise ItemImagePermissionDenied()

    def post(self, request, pk):
        self._require_perm(request)
        item = get_object_or_404(Item, pk=pk)
        expected_image_id = request.data.get("expected_image_id") if (
            "expected_image_id" in request.data
        ) else None
        outcome = services.upload_item_image(
            item=item,
            file=request.data.get("file"),
            alt_text=request.data.get("alt_text", "") or "",
            is_illustration=_parse_bool(request.data.get("is_illustration")),
            expected_image_id=expected_image_id,
            actor=request.user,
        )
        data = {
            "item_id": item.pk,
            "item_code": item.code,
            "image": serialize_item_image(outcome.image),
            "warnings": outcome.warnings,
        }
        return Response(data, status=201 if outcome.created else 200)

    def delete(self, request, pk):
        self._require_perm(request)
        item = get_object_or_404(Item, pk=pk)
        expected_image_id = request.query_params.get("expected_image_id")
        services.remove_item_image(
            item=item, expected_image_id=expected_image_id, actor=request.user
        )
        return Response(status=204)
