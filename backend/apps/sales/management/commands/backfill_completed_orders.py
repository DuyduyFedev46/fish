"""
Chuyển bù đơn cũ đã giao xong sang Hoàn tất (W37 S3, BR-BH-18, BR-BH-21, BR-BC-06).

`python manage.py backfill_completed_orders`            -> chạy THẬT (khác `backfill_credit_notes`: lệnh đó mặc định chỉ in).
`python manage.py backfill_completed_orders --dry-run`  -> chỉ in, không ghi DB, không AuditLog.

Mỗi đơn một `transaction.atomic()`: khoá đơn, đọc lại, dùng chung luật `complete_order_if_delivered` với đường giao xong.
Chỉ đổi `status` của đơn (không động vào hoá đơn, kho, chứng từ đảo, phiếu hoàn). Lỗi ở một đơn: dừng, in mã đơn lỗi, exit
khác 0; đơn trước đó đã commit, chạy lại thì làm nốt. Idempotent. Không có route HTTP.

Output CHỈ gồm mã đơn (bất biến 9): không tên, SĐT, địa chỉ, số tiền.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.delivery.models import DeliveryNote
from apps.sales.models import SalesOrder
from apps.sales.orders.completion import backfill_candidates, complete_order_if_delivered, is_delivery_finished


def _latest_completed_note(order):
    return (
        DeliveryNote.objects.filter(sales_invoice__sales_order_id=order.pk, status=DeliveryNote.Status.COMPLETED)
        .order_by("-completed_at", "-pk")
        .first()
    )


class Command(BaseCommand):
    help = "Chuyển bù đơn PROCESSING đã giao xong sang COMPLETED (mặc định chạy thật; --dry-run để thử)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Chỉ in mã đơn sẽ chuyển, không ghi gì.")

    def handle(self, *args, **options):
        ids = list(backfill_candidates().values_list("pk", flat=True))
        if options["dry_run"]:
            return self._dry_run(ids)

        moved = []
        for pk in ids:
            code = None
            try:
                with transaction.atomic():
                    order = SalesOrder.objects.select_for_update().get(pk=pk)
                    code = order.code
                    trigger = _latest_completed_note(order)
                    if trigger is None:
                        continue
                    if complete_order_if_delivered(order=order, trigger_note=trigger, backfill=True):
                        moved.append(code)
            except Exception as exc:  # mỗi đơn một giao dịch: đơn lỗi đã rollback, đơn trước giữ nguyên
                self.stdout.write(f"Đã chuyển {len(moved)} đơn trước khi lỗi.")
                raise CommandError(f"Lỗi ở đơn {code or pk} ({type(exc).__name__}); đã dừng, chạy lại để làm nốt.") from exc

        self.stdout.write(self.style.SUCCESS(f"Đã chuyển {len(moved)} đơn."))
        for code in moved:
            self.stdout.write(f"- {code}")

    def _dry_run(self, ids):
        eligible = []
        for order in SalesOrder.objects.filter(pk__in=ids).order_by("pk"):
            statuses = DeliveryNote.objects.filter(sales_invoice__sales_order_id=order.pk).values_list("status", flat=True)
            if is_delivery_finished(list(statuses)):
                eligible.append(order.code)
        self.stdout.write(f"Sẽ chuyển {len(eligible)} đơn:")
        for code in eligible:
            self.stdout.write(f"- {code}")
        self.stdout.write("Chưa ghi gì (--dry-run).")
