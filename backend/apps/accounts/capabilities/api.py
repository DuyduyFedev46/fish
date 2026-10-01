"""
Endpoint ma trận phân quyền (B4) — `/api/staff/groups/…`. Đọc: `accounts.manage_staff`; ghi: chỉ nhóm Chủ.

View chỉ: kiểm quyền → kiểm field được phép → gọi services → trả JSON. Không có POST/PATCH/DELETE (405).
Route khai trong `config/api_urls.py` TRƯỚC `include(router.urls)` để `StaffViewSet` không bắt `pk="groups"`.
Nằm dưới `/api/staff/` nên đã thuộc danh sách cấm của AI.
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.staff.api import CanManageStaff
from apps.common.exceptions import BusinessError

from . import next_steps  # noqa: F401 - đăng ký guidance provider `group` (R2) khi nạp URL
from . import services


class GroupListView(APIView):
    permission_classes = [CanManageStaff]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        return Response(services.list_groups())


class GroupDetailView(APIView):
    permission_classes = [CanManageStaff]
    http_method_names = ["get", "head", "options"]

    def get(self, request, code):
        return Response(services.describe_group(code))


class GroupCapabilitiesView(APIView):
    permission_classes = [CanManageStaff]
    http_method_names = ["put", "options"]

    def put(self, request, code):
        data = request.data if hasattr(request.data, "keys") else {}
        unknown = sorted(set(data.keys()) - {"capabilities"})
        if unknown:
            raise BusinessError("Có trường không được phép.", code=services.INPUT_CODE)
        body = services.set_group_capabilities(
            group_code=code, changes=data.get("capabilities"), actor=request.user
        )
        return Response(body)
