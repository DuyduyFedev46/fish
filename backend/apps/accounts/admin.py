from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User

from apps.accounts.auth.services import sorted_groups
from apps.common.audit import record_audit

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
    """Chỉ đọc — append-only (BR-PQ-06)."""

    list_display = ("created_at", "actor", "action", "model_name", "object_repr")
    list_filter = ("action", "model_name")
    search_fields = ("action", "object_repr", "object_id")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
