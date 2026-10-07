"""
Phạm vi dòng (Tầng 3) của phiếu giao — MỘT nguồn duy nhất, đọc từ cấu hình D3 (PV-04, BR-PQ-33/34/35).

Dùng cho `DeliveryNoteViewSet` (danh sách, chi tiết, "Việc giao của tôi", đổi trạng thái, giao người, tem) và dòng thời gian
`delivery` (`next_steps.py`), nên các đường không lệch nhau.

- `all` (mặc định Chủ, Quản lý, NV kho; superuser): thấy mọi phiếu, không có cửa sổ dữ liệu khách.
- `assigned` (mặc định NV giao): chỉ phiếu gán cho mình; dữ liệu khách của phiếu đã kết thúc quá cửa sổ SR-PII-02 bị ẩn
  (`pii_scope.py`, không đổi số ngày). Phiếu CANCELLED gán cho mình vẫn thấy để nhận 400 BR-GH-24 thay vì 404 (W37 S2-AC2).
- Người không nhóm (gán quyền trực tiếp) hoặc nhóm thiếu cấu hình: giá trị hẹp nhất `assigned` (UC-6).

Quyền xem phiếu giao (Tầng 1, `delivery.view_deliverynote`) vẫn đứng trước: phạm vi `all` không cấp quyền xem (BR-PQ-34).
"""
from apps.accounts.data_scopes.resolver import resolve_data_scope

ALL = "all"
ASSIGNED = "assigned"


def deliveries_scope_value(user) -> str:
    """Giá trị D3 "Phiếu giao" của `user` (phân giải từ cấu hình nhóm)."""
    return resolve_data_scope(user, "deliveries")


def deliveries_window_applies(user) -> bool:
    """True khi dữ liệu khách của phiếu đã kết thúc bị ẩn sau cửa sổ SR-PII-02 (phạm vi khác `all`)."""
    return deliveries_scope_value(user) != ALL


def scope_deliveries_for(user, qs, *, value=None):
    """Lọc queryset `DeliveryNote` theo phạm vi D3 của `user`. `value` truyền sẵn khi view đã phân giải."""
    value = value or deliveries_scope_value(user)
    if value == ALL:
        return qs
    return qs.filter(assigned_to=user)
