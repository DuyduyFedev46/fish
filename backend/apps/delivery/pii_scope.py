"""
Phạm vi dữ liệu cá nhân của khách đối với NV giao (SR-PII-02, bất biến 9, BR-PQ-12).

NV giao chỉ thấy tên, SĐT, địa chỉ, ghi chú của khách khi phiếu giao gán cho mình còn "trong cửa sổ":
- Phiếu chưa kết thúc (kể cả FAILED, vì FAILED có thể quay lại DELIVERING): luôn thấy.
- Phiếu kết thúc (COMPLETED, CANCELLED): thấy tới hết ngày lịch thứ `DELIVERY_PII_RECENT_DAYS` kể từ ngày
  kết thúc (giờ VN), từ 00:00 ngày kế tiếp thì ẩn. Mã đơn, mã phiếu, trạng thái, số kg vẫn trả để xem lịch sử.

Mốc kết thúc: `completed_at`. Phiếu CANCELLED không có mốc riêng (hệ thống không ghi), dùng `created_at`
làm mốc thay, nghĩa là có thể ẩn sớm hơn thực tế, hướng an toàn cho dữ liệu cá nhân.

Một nguồn duy nhất cho cả ba endpoint (orders, customers, delivery notes).
PV-03: điều kiện "thấy hết, không cửa sổ" của đơn nay là phạm vi D1/D2 = `all` (cấu hình), không còn là tên nhóm.
"""
import datetime

from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from .models import DeliveryNote

TERMINAL_STATUSES = (DeliveryNote.Status.COMPLETED, DeliveryNote.Status.CANCELLED)


def pii_recent_days() -> int:
    return int(getattr(settings, "DELIVERY_PII_RECENT_DAYS", 7))


def pii_cutoff(*, now=None):
    """Đầu ngày (00:00 giờ VN) của ngày `hôm nay - N`. Phiếu kết thúc trước mốc này thì ẩn dữ liệu khách."""
    local_now = timezone.localtime(now or timezone.now())
    cutoff_date = local_now.date() - datetime.timedelta(days=pii_recent_days())
    return timezone.make_aware(
        datetime.datetime.combine(cutoff_date, datetime.time.min), timezone.get_current_timezone()
    )


def _within_window_q(cutoff):
    """Q trên DeliveryNote: chưa kết thúc, hoặc kết thúc từ `cutoff` trở đi."""
    return (
        ~Q(status__in=TERMINAL_STATUSES)
        | Q(completed_at__gte=cutoff)
        | Q(completed_at__isnull=True, created_at__gte=cutoff)
    )


def courier_visible_note_q(user, *, now=None):
    """Q trên DeliveryNote: phiếu gán cho `user` và còn trong cửa sổ xem dữ liệu khách."""
    return Q(assigned_to=user) & _within_window_q(pii_cutoff(now=now))


def is_note_pii_expired(note, *, now=None) -> bool:
    """Bản Python của điều kiện trên, cho serializer. True = phải ẩn dữ liệu khách của phiếu."""
    if note.status not in TERMINAL_STATUSES:
        return False
    ended = note.completed_at or note.created_at
    return ended < pii_cutoff(now=now)


def annotate_order_pii_visible(user, qs, *, value, now=None):
    """
    Gắn `pii_visible` (bool) cho queryset `SalesOrder` mà phạm vi `value` của `user` KHÔNG phải `all`: True khi đơn có
    phiếu gán cho user còn trong cửa sổ, hoặc (chỉ khi `value` = `assigned_or_confirmation`) nằm trong phạm vi gọi
    xác nhận (BR-GH-18). `value` là giá trị D1 (đơn) hay D2 (hoá đơn) đã phân giải của người gọi, truyền tường minh để
    một request chỉ phân giải một lần. Phạm vi `all` thì không gọi hàm này (không có cửa sổ, như Chủ/Quản lý/NV kho hôm nay).
    """
    visible_note = DeliveryNote.objects.filter(
        sales_invoice__sales_order=OuterRef("pk")
    ).filter(courier_visible_note_q(user, now=now))
    visible = Exists(visible_note)

    if value == "assigned_or_confirmation":
        from apps.delivery.confirmation.scope import customer_service_note_q

        visible = visible | Exists(
            DeliveryNote.objects.filter(sales_invoice__sales_order=OuterRef("pk")).filter(
                customer_service_note_q(user)
            )
        )
    return qs.annotate(pii_visible=visible)
