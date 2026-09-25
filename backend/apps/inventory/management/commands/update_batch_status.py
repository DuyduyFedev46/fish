"""
Job hằng ngày cập nhật trạng thái lô theo hạn & tồn (S2, BR-LO-01/02/06).
`python manage.py update_batch_status` — lịch đề xuất 00:05 giờ VN.
Idempotent: chạy lại cùng ngày không đổi gì, không sinh AuditLog.
"""
from django.core.management.base import BaseCommand

from apps.inventory.batches import services


class Command(BaseCommand):
    help = "Chuyển lô sang Cận hạn / Quá hạn / Hết hàng (idempotent, actor = Hệ thống)."

    def handle(self, *args, **options):
        changed = services.update_batch_statuses()
        total = sum(changed.values())
        detail = ", ".join(f"{k}={v}" for k, v in sorted(changed.items())) or "không đổi"
        self.stdout.write(self.style.SUCCESS(f"Đã cập nhật {total} lô ({detail})."))
