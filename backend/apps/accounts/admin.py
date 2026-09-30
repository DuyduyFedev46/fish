import json

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.utils.html import format_html

from apps.accounts.auth.services import sorted_groups
from apps.common.audit import record_audit
from apps.common.cost_keys import can_view_cost, redact_cost

from .models import AuditLog, StaffProfile


class SuperuserOnlyAdminMixin:
    """
    S41-AC8 · BR-PQ-17: trang User/Group trong Admin chỉ dành cho superuser. Chủ vẫn có
    `auth.change_user`/`change_group` (dùng cho API qua service có chặn), nhưng nếu mở Admin thì
    tự bật `is_superuser` hay sửa quyền Group được → cửa sau tự nâng quyền. Quản lý nhân viên
    hằng ngày đi qua console (`/api/staff/`).

    Ngoại lệ: ô chọn người (autocomplete) ở form khác (vd Hồ sơ nhân viên) vẫn chạy cho người có
    `view` — view autocomplete chỉ trả id + tên, không mở trang User.
    """

    def _is_autocomplete(self, request):
        match = getattr(request, "resolver_match", None)
        return bool(match and match.url_name == "autocomplete")

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._is_autocomplete(request) and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(SuperuserOnlyAdminMixin, BaseUserAdmin):
    """Superuser đổi nhóm ở đây vẫn ghi AuditLog `staff_groups_change` (S41-AC8, BR-PQ-04)."""

    def save_related(self, request, form, formsets, change):
        before = sorted_groups(form.instance.groups.values_list("name", flat=True)) if change else []
        super().save_related(request, form, formsets, change)
        after = sorted_groups(form.instance.groups.values_list("name", flat=True))
        if before != after:
            record_audit(
                "staff_groups_change", actor=request.user, obj=form.instance,
                changes={"groups": {"from": before, "to": after}},
                note="Đổi nhóm trong Django Admin.",
            )


@admin.register(Group)
class GroupAdmin(SuperuserOnlyAdminMixin, BaseGroupAdmin):
    pass


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "phone", "status", "joined_date")
    list_filter = ("status",)
    search_fields = ("user__username", "display_name", "phone")
    autocomplete_fields = ("user",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Chỉ đọc — append-only (BR-PQ-06). Dòng AI hiển thị `ai:<tên user>` (S03).

    Bất biến 1 (P8 Lô 5, B1): `changes` chứa khoá giá vốn/tiền NCC hoàn (COST_KEYS). Cột này không
    hiện thẳng mà đi qua `changes_visible`, dùng ĐÚNG `can_view_cost` + `redact_cost` như endpoint
    `/api/audit-logs/` (một nguồn duy nhất). `note` theo quy ước không chứa số tiền (audit.py) và
    API cũng trả nguyên văn, nên giữ nguyên.
    """

    exclude = ("changes",)

    def get_readonly_fields(self, request, obj=None):
        # Callable gắn theo request (không lưu trạng thái trên instance admin dùng chung giữa các luồng).
        show_cost = can_view_cost(request.user)

        def changes_visible(row):
            data = row.changes if show_cost else redact_cost(row.changes)
            return format_html("<pre>{}</pre>", json.dumps(data, ensure_ascii=False, indent=2, default=str))

        changes_visible.short_description = "Thay đổi"
        return [*super().get_readonly_fields(request, obj), changes_visible]

    list_display = ("created_at", "actor_kind", "actor", "ai_actor", "action",
                    "model_name", "object_repr")
    list_filter = ("actor_kind", "action", "model_name")
    search_fields = ("action", "object_repr", "object_id")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
