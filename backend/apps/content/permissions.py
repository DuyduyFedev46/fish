"""Phân quyền app content — T1 cho CRUD và T2 cho @action (§3.2 02b-tech-design)."""
from rest_framework.exceptions import PermissionDenied

from apps.common.api import BusinessModelPermissions

# Danh mục 8 quyền của app content (CMS-01)
PERM_VIEW_CATEGORY = "content.view_category"
PERM_ADD_CATEGORY = "content.add_category"
PERM_CHANGE_CATEGORY = "content.change_category"
PERM_VIEW_ENTRY = "content.view_entry"
PERM_ADD_ENTRY = "content.add_entry"
PERM_CHANGE_ENTRY = "content.change_entry"
PERM_DELETE_ENTRY = "content.delete_entry"
PERM_PUBLISH_ENTRY = "content.publish_entry"

CONTENT_ALL_PERMS = (
    PERM_VIEW_CATEGORY,
    PERM_ADD_CATEGORY,
    PERM_CHANGE_CATEGORY,
    PERM_VIEW_ENTRY,
    PERM_ADD_ENTRY,
    PERM_CHANGE_ENTRY,
    PERM_DELETE_ENTRY,
    PERM_PUBLISH_ENTRY,
)


class ContentPermissions(BusinessModelPermissions):
    """
    T1 theo model cho CRUD; T2 cho @action qua `required_perms` khai ngay trên @action.
    Custom action KHÔNG có required_perms → từ chối (fail-closed), không rơi về 'đã đăng nhập là được'.
    """

    def has_permission(self, request, view):
        action_name = getattr(view, "action", None)
        if not action_name and getattr(view, "required_perms", ()):
            if not request.user or not request.user.is_authenticated:
                return False
            for perm in view.required_perms:
                if not request.user.has_perm(perm):
                    raise PermissionDenied(f"Thiếu quyền: {perm}")
            return True

        if not super().has_permission(request, view):
            return False

        custom_perm_actions = getattr(view, "custom_perm_actions", ())
        if action_name and action_name in custom_perm_actions:
            action_func = getattr(view, action_name, None)
            func_kwargs = getattr(action_func, "kwargs", {}) if action_func else {}
            perms = tuple(
                getattr(action_func, "required_perms", None)
                or func_kwargs.get("required_perms")
                or getattr(view, "required_perms", ())
                or ()
            )
            if not perms:
                return False
            if not request.user or not request.user.is_authenticated:
                return False
            for perm in perms:
                if not request.user.has_perm(perm):
                    raise PermissionDenied(f"Thiếu quyền: {perm}")
            return True

        return True

