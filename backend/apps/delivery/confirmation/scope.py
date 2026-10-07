"""
Phạm vi gọi xác nhận (D4, BR-GH-18, PV-05, 02b §3.2) — MỘT nguồn duy nhất cho API hàng chờ, tìm kiếm, dòng thời gian
phiếu giao và nhánh "đơn trong phạm vi gọi" của phạm vi đơn.

Giá trị D4 đọc từ cấu hình nhóm (`data_scopes.resolver`), không còn gắn với tên nhóm:
- `all_pending` (mặc định Chủ, Quản lý, NV kho; superuser): thấy mọi phiếu có mục chờ gọi, đúng nghĩa "thấy hết" hôm nay.
- `pending_or_called_recently` (mặc định CSKH; hẹp nhất của nhóm): phiếu đang chờ gọi, hoặc phiếu chính mình đã gọi trong
  `CONFIRMATION_PII_RECENT_DAYS` ngày.
Quyền Tầng 1 `delivery.confirm_with_customer` vẫn đứng trước ở từng view (BR-PQ-34): phạm vi `all_pending` không cấp quyền gọi.
"""
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.accounts.data_scopes.resolver import resolve_data_scopes

OPEN_CALL_STATES = ("PENDING", "CALLBACK", "ESCALATED")
ALL_PENDING = "all_pending"
PENDING_OR_CALLED_RECENTLY = "pending_or_called_recently"
NO_SCOPE = "none"  # không phải lựa chọn của Chủ: người không thuộc nhóm nào đủ điều kiện gọi xác nhận


def confirmation_scope_value(user) -> str:
    """Giá trị D4 "Gọi xác nhận" của `user` (phân giải một lần mỗi request nhờ bộ nhớ trên đối tượng user).

    Người không có nhóm nào đủ điều kiện (chỉ được gán quyền `confirm_with_customer` trực tiếp, R9/D-3) trả `none`: không có
    mục nào trong phạm vi, đúng như trước PV-05. Không để họ rơi về giá trị hẹp nhất `pending_or_called_recently`, vì đó là
    MỞ THÊM dữ liệu khách (phiếu đang chờ gọi) cho người chưa từng được cấp phạm vi (bất biến 9)."""
    resolved = resolve_data_scopes(user)["confirmation"]
    if resolved.via_group is None and not getattr(user, "is_superuser", False):
        return NO_SCOPE
    return resolved.value


def customer_service_note_q(user, *, now=None, prefix=""):
    """
    Q trên DeliveryNote: phiếu trong phạm vi hẹp nhất của việc gọi xác nhận (BR-GH-18). Dùng cho nhánh
    `assigned_or_confirmation` của phạm vi đơn (D1), nên giữ nguyên nghĩa "điều kiện rank 0 của D4".
    Bao gồm:
    1. Phiếu CONFIRMING và ConfirmationTask thuộc {PENDING, CALLBACK, ESCALATED}.
    2. Hoặc phiếu mà user đã từng gọi trong vòng CONFIRMATION_PII_RECENT_DAYS ngày.
    """
    now = now or timezone.now()
    days = getattr(settings, "CONFIRMATION_PII_RECENT_DAYS", 7)
    since = now - timedelta(days=days)
    p = prefix

    from apps.delivery.models import CustomerCall

    called_note_ids = CustomerCall.objects.filter(
        created_by=user, created_at__gte=since
    ).values("note_id")

    return (
        Q(**{f"{p}status": "CONFIRMING", f"{p}confirmation__state__in": OPEN_CALL_STATES})
        | Q(**{f"{p}pk__in": called_note_ids})
    )


def note_in_confirmation_scope(user, note, *, now=None, value=None) -> bool:
    """Một DeliveryNote cụ thể có nằm trong phạm vi gọi xác nhận D4 của user hay không.

    `value` là D4 đã phân giải của người gọi; view tính một lần rồi truyền vào để danh sách không phân giải mỗi dòng."""
    if not user or not user.is_authenticated:
        return False
    value = value or confirmation_scope_value(user)
    if value == NO_SCOPE:
        return False
    if value == ALL_PENDING:
        return True

    if note.status == "CONFIRMING":
        confirmation = getattr(note, "confirmation", None)
        if confirmation and confirmation.state in OPEN_CALL_STATES:
            return True

    now = now or timezone.now()
    days = getattr(settings, "CONFIRMATION_PII_RECENT_DAYS", 7)
    since = now - timedelta(days=days)
    from apps.delivery.models import CustomerCall

    return CustomerCall.objects.filter(note=note, created_by=user, created_at__gte=since).exists()
