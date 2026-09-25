"""
Giám sát job huỷ TTL (BR-BH-04 / E-12).

Nếu job nhả giữ chỗ chết, sẽ tồn tại đơn BOOKED quá hạn LÂU mà chưa bị huỷ — hàng
bị khoá vô hình. Command này đo trực tiếp bất biến đó: đếm đơn BOOKED có
booked_expires_at cũ hơn (now − grace). Có → exit code 1 + log lỗi để hệ thống
giám sát ngoài (cron + alert) bắt được. Không cần lưu heartbeat riêng.

`python manage.py check_ttl_job_health`  (exit 0 = khoẻ, 1 = nghi job chết)
"""
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.sales.models import SalesOrder

logger = logging.getLogger("cangca.sales.ttl")


class Command(BaseCommand):
    help = "Cảnh báo nếu job huỷ TTL có vẻ đã chết (còn đơn BOOKED quá hạn lâu)."

    def add_arguments(self, parser):
        parser.add_argument("--grace-minutes", type=int, default=settings.TTL_JOB_HEALTH_GRACE_MINUTES)

    def handle(self, *args, **options):
        grace = options["grace_minutes"]
        threshold = timezone.now() - timezone.timedelta(minutes=grace)
        stale = SalesOrder.objects.filter(
            status=SalesOrder.Status.BOOKED, booked_expires_at__lt=threshold
        ).count()
        if stale:
            msg = (
                f"CẢNH BÁO: {stale} đơn BOOKED quá hạn > {grace} phút chưa bị huỷ — "
                f"job huỷ TTL có thể đã chết (BR-BH-04). Hàng đang bị khoá vô hình."
            )
            logger.error(msg)
            self.stderr.write(self.style.ERROR(msg))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("Job huỷ TTL khoẻ (không có đơn BOOKED quá hạn treo)."))
