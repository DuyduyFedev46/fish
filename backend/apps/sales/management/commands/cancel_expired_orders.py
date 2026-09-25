"""
Chạy huỷ đơn quá TTL một lần (dùng cho cron nếu không chạy Celery Beat).
`python manage.py cancel_expired_orders`
"""
from django.core.management.base import BaseCommand

from apps.sales.orders import services


class Command(BaseCommand):
    help = "Huỷ đơn giữ chỗ quá TTL, nhả giữ chỗ (idempotent)."

    def handle(self, *args, **options):
        n = services.cancel_unpaid_expired()
        self.stdout.write(self.style.SUCCESS(f"Đã huỷ {n} đơn quá TTL."))
