"""
Phạm vi dòng (Tầng 3, BR-PQ-12) của hàng hoàn về kho — MỘT nơi duy nhất cho API và dòng thời gian `return`.

Chủ, Quản lý, Nhân viên kho (và superuser) thấy mọi phiếu. Người chỉ thuộc `delivery_staff` chỉ thấy phiếu hàng hoàn
của phiếu giao được gán cho mình; phiếu của người khác (và phiếu không gắn phiếu giao) là 404, không phải 403, để
không lộ việc phiếu có tồn tại. Cùng quy tắc với `DeliveryNoteViewSet.get_queryset`.
"""
from apps.common.api import has_full_delivery_scope


def scope_returns_for(user, queryset):
    """`(user, queryset) -> queryset` — dạng `scope_fn` của `make_audit_timeline_provider`."""
    if has_full_delivery_scope(user):
        return queryset
    return queryset.filter(delivery_note__assigned_to=user)


def scope_delivery_notes_for(user, queryset):
    """Phiếu giao mà `user` được tạo hàng hoàn cho: cùng điều kiện với `scope_returns_for`, áp lên phiếu giao."""
    if has_full_delivery_scope(user):
        return queryset
    return queryset.filter(assigned_to=user)
