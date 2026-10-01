"""
Lệnh cũ `process_cskh_deadlines` (tên tiếng Việt), giữ tới P8b Lô 5 để Cloud Run Job/Cron đang chạy
không gãy. Chỉ bọc gọi lệnh mới `process_confirmation_deadlines`.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "[Tên cũ] Gọi process_confirmation_deadlines. Dùng tên mới; tên cũ gỡ ở P8b Lô 5."

    def handle(self, *args, **options):
        call_command("process_confirmation_deadlines", stdout=self.stdout, stderr=self.stderr)
