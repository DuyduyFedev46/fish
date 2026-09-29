"""
Cloud Run Job / Cron: Quét các mốc thời gian CSKH (02b §5.1, CS-07, CS-08).
- Bước 1: PENDING quá W phút -> ESCALATED
- Bước 2: ESCALATED quá D phút -> Tự huỷ (nếu CSKH_AUTO_CANCEL_ENABLED=1)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.delivery.cskh import services as cskh_services


class Command(BaseCommand):
    help = "Quét các mốc thời gian CSKH: chuyển Quản lý khi hết cửa sổ và tự huỷ khi Quản lý không xử lý."

    def handle(self, *args, **options):
        now = timezone.now()
        escalated_n = cskh_services.escalate_expired_windows(now=now)
        auto_res = cskh_services.auto_cancel_overdue(now=now)
        m = auto_res.get("cancelled", 0)
        k = auto_res.get("blocked", 0)
        self.stdout.write(f"Đã chuyển Quản lý {escalated_n} phiếu; tự huỷ {m} đơn; chặn {k} đơn.")
