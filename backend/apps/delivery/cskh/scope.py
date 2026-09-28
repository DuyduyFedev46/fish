"""
Phạm vi dữ liệu cá nhân cho nhóm CSKH (BR-GH-18, 02b §3.2).
"""
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.common.api import has_full_delivery_scope

OPEN_CALL_STATES = ("PENDING", "CALLBACK", "ESCALATED")


def is_cskh(user) -> bool:
    """Kiểm tra user có thuộc Group cskh hay không."""
    return bool(user and user.is_authenticated and user.groups.filter(name="cskh").exists())


def cskh_note_q(user, *, now=None, prefix=""):
    """
    Q trên DeliveryNote: phiếu CSKH được thấy đủ tên/SĐT/địa chỉ (BR-GH-18).
    Bao gồm:
    1. Phiếu CONFIRMING và ConfirmationTask thuộc {PENDING, CALLBACK, ESCALATED}.
    2. Hoặc phiếu mà user đã từng gọi trong vòng CSKH_PII_RECENT_DAYS ngày.
    """
    now = now or timezone.now()
    days = getattr(settings, "CSKH_PII_RECENT_DAYS", 7)
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


def note_in_cskh_scope(user, note, *, now=None) -> bool:
    """Kiểm tra một DeliveryNote cụ thể có nằm trong phạm vi CSKH của user hay không."""
    if not user or not user.is_authenticated:
        return False
    if has_full_delivery_scope(user):
        return True
    if not is_cskh(user):
        return False

    if note.status == "CONFIRMING":
        confirmation = getattr(note, "confirmation", None)
        if confirmation and confirmation.state in OPEN_CALL_STATES:
            return True

    now = now or timezone.now()
    days = getattr(settings, "CSKH_PII_RECENT_DAYS", 7)
    since = now - timedelta(days=days)
    from apps.delivery.models import CustomerCall

    return CustomerCall.objects.filter(note=note, created_by=user, created_at__gte=since).exists()
