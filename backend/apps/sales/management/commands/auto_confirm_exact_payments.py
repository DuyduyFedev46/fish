"""
Management command chạy job tự động khớp thanh toán tuyệt đối (DW-26, V-DW1).
"""
from django.core.management.base import BaseCommand
from apps.sales.payments.auto_confirm import process_exact_payment_matches


class Command(BaseCommand):
    help = "Quét các giao dịch mở và tự động khớp các ca khớp tuyệt đối theo DW-26."

    def handle(self, *args, **options):
        res = process_exact_payment_matches()
        reason = f" ({res['reason']})" if res.get("reason") else ""
        self.stdout.write(
            f"Finished: confirmed {res['confirmed']}, escalated {res['escalated']}, skipped {res['skipped']}{reason}."
        )
