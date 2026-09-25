"""
Endpoint quản lý nhân viên (S41, S42) — `/api/staff/…`. Mọi action đòi `accounts.manage_staff`.

View chỉ: kiểm quyền → kiểm field được phép (field lạ → 400) → gọi services → trả JSON.
Không có PUT chi tiết, không có DELETE (BR-PQ-02) → 405.
"""
from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.common.exceptions import BusinessError

from . import services
from .serializers import staff_item

MANAGE_STAFF_PERM = "accounts.manage_staff"

CREATE_FIELDS = {"username", "display_name", "phone", "groups", "password"}
UPDATE_FIELDS = {"display_name", "phone"}


class CanManageStaff(BasePermission):
    """Tầng 2 `accounts.manage_staff` (chỉ Chủ). Đã đăng nhập mà method không có → 405."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.has_perm(MANAGE_STAFF_PERM)


def _payload(request, allowed, *, required=()):
    data = request.data if hasattr(request.data, "keys") else {}
    unknown = sorted(set(data.keys()) - set(allowed))
    if unknown:
        raise BusinessError(
            f"Trường không được phép: {', '.join(unknown)}.", code=services.INPUT_CODE
        )
    return {k: data.get(k) for k in allowed if k in data or k in required}


class StaffViewSet(viewsets.GenericViewSet):
    permission_classes = [CanManageStaff]
    queryset = User.objects.select_related("staff_profile").prefetch_related("groups")
    http_method_names = ["get", "post", "patch", "put", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset().order_by("username")
        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "1"):
            qs = qs.filter(is_active=True)
        elif is_active in ("false", "0"):
            qs = qs.filter(is_active=False)
        return qs

    def _item(self, user):
        user = User.objects.select_related("staff_profile").prefetch_related("groups").get(
            pk=user.pk
        )  # đọc lại sau khi service đổi nhóm/hồ sơ
        return staff_item(user, actor=self.request.user, active_chus=services.active_chu_ids())

    def list(self, request):
        active_chus = services.active_chu_ids()
        return Response(
            [staff_item(u, actor=request.user, active_chus=active_chus)
             for u in self.get_queryset()]
        )

    def retrieve(self, request, pk=None):
        return Response(self._item(self.get_object()))

    def create(self, request):
        data = _payload(request, CREATE_FIELDS, required=("phone", "username", "password"))
        user = services.create_staff(
            actor=request.user,
            username=data.get("username"),
            password=data.get("password"),
            phone=data.get("phone"),
            display_name=data.get("display_name", ""),
            groups=data.get("groups", []),
        )
        return Response(self._item(user), status=201)

    def update(self, request, pk=None):  # PUT chi tiết không hỗ trợ — chỉ PATCH
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, pk=None):
        data = _payload(request, UPDATE_FIELDS)
        user = services.update_profile(actor=request.user, user=self.get_object(), **data)
        return Response(self._item(user))

    @action(detail=True, methods=["put"], url_path="groups")
    def groups(self, request, pk=None):
        data = _payload(request, {"groups"}, required=("groups",))
        groups, added, removed = services.set_groups(
            actor=request.user, user=self.get_object(), groups=data["groups"]
        )
        return Response({"groups": groups, "added": added, "removed": removed})

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        _payload(request, set())
        user = services.deactivate(actor=request.user, user=self.get_object())
        return Response({"is_active": user.is_active})

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        _payload(request, set())
        user = services.reactivate(actor=request.user, user=self.get_object())
        return Response({"is_active": user.is_active})

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        data = _payload(request, {"new_password"}, required=("new_password",))
        services.reset_password(
            actor=request.user, user=self.get_object(), new_password=data["new_password"]
        )
        return Response({})
