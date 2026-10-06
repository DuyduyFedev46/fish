"""
Phạm vi dòng (Tầng 3) của phiếu nhập — MỘT nguồn duy nhất, đọc từ cấu hình D6 (PV-06, BR-PQ-33/34/35, spec §1.6, Q-3).

Dùng cho `PurchaseReceiptViewSet` (danh sách, chi tiết, sửa, gửi ghi nhận, huỷ) và dòng thời gian `receipt`.

- `all` (mặc định mọi nhóm có quyền phiếu nhập; Chủ, superuser): mọi phiếu, đúng hiện trạng.
- `created_by_me`: phiếu do mình tạo.
- `created_by_me_today` (hẹp nhất): phiếu do mình tạo trong ngày lịch giờ VN (Asia/Ho_Chi_Minh) của HÔM NAY; DB lưu UTC.
  Phiếu mở lúc 23:59 mà gửi lúc 00:01 hôm sau thì ngoài phạm vi: 404, phiếu không đổi và không mất (PV-06-AC4).

Huỷ phiếu giữ luật cũ (người tạo, hoặc Quản lý/Chủ), KHÔNG bị D6 chặn thêm và không được D6 mở thêm: xem
`cancel_scope_q` và `can_cancel_receipt` (`services.py`).
"""
import datetime

from django.db.models import Q
from django.utils import timezone

from apps.accounts.data_scopes.resolver import resolve_data_scope

ALL = "all"
CREATED_BY_ME = "created_by_me"
CREATED_BY_ME_TODAY = "created_by_me_today"


def receipts_scope_value(user) -> str:
    """Giá trị D6 "Phiếu nhập" của `user`."""
    return resolve_data_scope(user, "receipts")


def vietnam_day_bounds(*, now=None):
    """(00:00 hôm nay, 00:00 ngày mai) theo giờ VN, là hai mốc aware; so với `created_at` lưu UTC."""
    local_now = timezone.localtime(now or timezone.now())
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.datetime.combine(local_now.date(), datetime.time.min), tz)
    return start, start + datetime.timedelta(days=1)


def scope_q(user, *, value=None, now=None) -> Q:
    """Q trên `PurchaseReceipt` cho phạm vi D6 của `user` (rỗng khi `all`)."""
    value = value or receipts_scope_value(user)
    if value == ALL:
        return Q()
    mine = Q(created_by=user)
    if value == CREATED_BY_ME:
        return mine
    start, end = vietnam_day_bounds(now=now)
    return mine & Q(created_at__gte=start, created_at__lt=end)


def scope_receipts_for(user, qs, *, value=None, now=None):
    """Lọc queryset `PurchaseReceipt` theo phạm vi D6. Dạng `scope_fn(user, qs)` của `make_audit_timeline_provider`."""
    condition = scope_q(user, value=value, now=now)
    return qs.filter(condition) if condition else qs


def cancel_scope_q(user) -> Q:
    """Q trên `PurchaseReceipt` cho action huỷ: phiếu trong D6 HOẶC phiếu qua luật huỷ cũ (người tạo, hoặc Quản lý/Chủ).

    Phiếu ngoài cả hai là 404 (không lộ tồn tại); phiếu trong D6 nhưng không qua luật huỷ cũ thì để `cancel_receipt` báo 403
    như hôm nay (PV-06-AC5, AC6)."""
    from .services import can_cancel_any_receipt

    condition = scope_q(user)
    if can_cancel_any_receipt(user) or not condition:  # Q() rỗng = không giới hạn; không được OR với Q khác (bị bỏ mất)
        return Q()
    return condition | Q(created_by=user)
