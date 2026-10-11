"""
API ERP mã giảm giá (SHOP-3b-01, 02b §3.9). MỌI endpoint cần `catalog.manage_voucher` (Tầng 2, mặc định chỉ Chủ, uỷ được
ở màn Phân quyền): chưa đăng nhập 401, thiếu quyền 403. Không có DELETE (bất biến 3): dừng mã bằng `disable`.
"""
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.models import Voucher
from apps.common.api import StandardPagination

from . import services
from .serializers import redemption_payload, voucher_payload

MANAGE_VOUCHER_PERM = "catalog.manage_voucher"


class CanManageVoucher(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if not request.user.has_perm(MANAGE_VOUCHER_PERM):
            raise PermissionDenied(f"Thiếu quyền: {MANAGE_VOUCHER_PERM}")
        return True


def _data(request) -> dict:
    return request.data if hasattr(request.data, "get") else {}


class VoucherViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanManageVoucher]
    pagination_class = StandardPagination
    http_method_names = ["get", "post", "patch", "head", "options"]
    queryset = Voucher.objects.all()

    def get_queryset(self):
        qs = services.with_counts(Voucher.objects.all()).order_by("-id")
        if self.action == "list":
            status = self.request.query_params.get("status")
            if status in services.STATUS_VALUES:
                qs = services.filter_by_status(qs, status, now=timezone.now())
        return qs

    def _one(self, voucher):
        fresh = services.with_counts(Voucher.objects.filter(pk=voucher.pk)).get()
        return voucher_payload(fresh, now=timezone.now())

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        now = timezone.now()
        return self.get_paginated_response([voucher_payload(v, now=now) for v in page])

    def retrieve(self, request, *args, **kwargs):
        return Response(voucher_payload(self.get_object(), now=timezone.now()))

    def create(self, request, *args, **kwargs):
        voucher = services.create_voucher(actor=request.user, data=_data(request))
        return Response(self._one(voucher), status=201)

    def partial_update(self, request, *args, **kwargs):
        voucher = services.update_voucher(voucher=self.get_object(), actor=request.user, data=_data(request))
        return Response(self._one(voucher))

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        data = _data(request)
        voucher = services.disable_voucher(
            voucher=self.get_object(), actor=request.user, reason_code=data.get("reason"), note=data.get("note", ""),
        )
        return Response(self._one(voucher))

    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):
        voucher = services.enable_voucher(voucher=self.get_object(), actor=request.user)
        return Response(self._one(voucher))

    @action(detail=True, methods=["get"])
    def redemptions(self, request, pk=None):
        voucher = self.get_object()
        rows = voucher.redemptions.select_related("order").order_by("-held_at", "-id")
        page = self.paginate_queryset(rows)
        return self.get_paginated_response([redemption_payload(r) for r in page])
