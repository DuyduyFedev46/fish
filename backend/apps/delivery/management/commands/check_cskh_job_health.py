"""
Lệnh cũ `check_cskh_job_health` (tên tiếng Việt), giữ tới P8b Lô 5 để job giám sát đang chạy không gãy.
Chỉ bọc gọi lệnh mới `check_confirmation_job_health` (exit code 1 được truyền nguyên).
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "[Tên cũ] Gọi check_confirmation_job_health. Dùng tên mới; tên cũ gỡ ở P8b Lô 5."

    def add_arguments(self, parser):
        parser.add_argument("--grace-minutes", type=int, default=10, help="Số phút trễ cho phép (mặc định 10).")

    def handle(self, *args, **options):
        call_command(
            "check_confirmation_job_health",
            grace_minutes=options.get("grace_minutes", 10),
            stdout=self.stdout,
            stderr=self.stderr,
        )
