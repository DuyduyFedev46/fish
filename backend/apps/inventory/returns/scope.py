"""
Phạm vi dòng (Tầng 3, BR-PQ-12/35) của hàng hoàn về kho — MỘT nơi duy nhất cho API và dòng thời gian `return`, đọc từ
cấu hình D5 (PV-04, 02b §1.4).

- `all` (mặc định Chủ, Quản lý, NV kho; superuser): thấy mọi phiếu.
- `assigned_deliveries` (mặc định NV giao; hẹp nhất): chỉ phiếu hàng hoàn của phiếu giao được gán cho mình. Phiếu của
  người khác (và phiếu không gắn phiếu giao) là 404, không phải 403, để không lộ việc phiếu có tồn tại.
Quyền xem `inventory.view_returntostock` (Tầng 1) vẫn đứng trước. D5 độc lập với D3: Chủ có thể cho NV giao thấy mọi
phiếu hàng hoàn mà vẫn chỉ thấy phiếu giao của mình.
"""
from apps.accounts.data_scopes.resolver import resolve_data_scope

ALL = "all"
ASSIGNED_DELIVERIES = "assigned_deliveries"


def returns_scope_value(user) -> str:
    """Giá trị D5 "Hàng hoàn về kho" của `user`."""
    return resolve_data_scope(user, "returns")


def scope_returns_for(user, queryset, *, value=None):
    """`(user, queryset) -> queryset` — dạng `scope_fn` của `make_audit_timeline_provider`. `value` để xem trước (PV-09)."""
    if (value or returns_scope_value(user)) == ALL:
        return queryset
    return queryset.filter(delivery_note__assigned_to=user)


def scope_delivery_notes_for(user, queryset):
    """Phiếu giao mà `user` được tạo hàng hoàn cho: cùng giá trị D5 với `scope_returns_for`, áp lên phiếu giao."""
    if returns_scope_value(user) == ALL:
        return queryset
    return queryset.filter(assigned_to=user)
