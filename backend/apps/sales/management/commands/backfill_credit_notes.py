"""
Lập bù chứng từ đảo doanh thu cho đơn đã huỷ TRƯỚC P8 (SR-14, F04, BR-HT-10).

`python manage.py backfill_credit_notes`            -> chỉ IN (dry-run), không ghi gì.
`python manage.py backfill_credit_notes --apply`    -> lập chứng từ, mỗi đơn một transaction.

Idempotent: đơn đã có chứng từ không được chọn lại. Chứng từ lập bù: `backfilled=True`,
`created_by=None`, `issued_at` = THỜI ĐIỂM CHẠY LỆNH (E1, Duy quyết 30/09: "báo cáo đã qua thì không
được sửa số" — kỳ cũ giữ nguyên, kỳ hiện tại nhận điều chỉnh), `stock_restored` lấy từ AuditLog
`cancel_paid_order` mới nhất của đơn (mặc định True). Lô đã CLOSED không đổi lãi lỗ (E2): `batch_pnl`
chỉ trừ chứng từ lập trước lúc chốt.

Output CHỈ gồm mã đơn, mã hoá đơn, số tiền bán, mã lô — không tên/SĐT/địa chỉ khách, không giá vốn.
Dry-run liệt kê riêng các đơn thuộc lô CLOSED (lãi lỗ lô giữ nguyên, điều chỉnh vào kỳ hiện tại).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import AuditLog
from apps.inventory.models import Batch
from apps.sales.credit_notes import services
from apps.sales.models import SalesInvoice, SalesInvoiceLineBatch, SalesOrder


def _pending_orders():
    return (
        SalesOrder.objects.filter(
            status=SalesOrder.Status.CANCELLED,
            invoice__status=SalesInvoice.Status.ISSUED,
            invoice__credit_notes__isnull=True,
        )
        .select_related("invoice")
        .order_by("pk")
    )


def _cancel_audit(order):
    return (
        AuditLog.objects.filter(
            model_name=SalesOrder._meta.label, object_id=str(order.pk), action="cancel_paid_order",
        )
        .order_by("-created_at", "-id")
        .first()
    )


class Command(BaseCommand):
    help = "Lập bù chứng từ đảo doanh thu cho đơn đã huỷ trước P8 (mặc định chỉ in; --apply để lập)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Lập chứng từ thật (mặc định chỉ in).")

    def handle(self, *args, **options):
        apply = options["apply"]
        orders = list(_pending_orders())
        self.stdout.write(
            f"{'APPLY' if apply else 'DRY-RUN'}: {len(orders)} đơn đã huỷ có hoá đơn còn hiệu lực "
            "chưa có chứng từ đảo."
        )

        closed = set()
        closed_orders = []
        for o in orders:
            inv = o.invoice
            batch_ids = set(
                SalesInvoiceLineBatch.objects.filter(invoice_line__invoice=inv)
                .values_list("batch__batch_id", flat=True)
            )
            order_closed = set(
                Batch.objects.filter(batch_id__in=batch_ids, status=Batch.Status.CLOSED)
                .values_list("batch_id", flat=True)
            )
            closed |= order_closed
            if order_closed:
                closed_orders.append((o.code, sorted(order_closed)))
            self.stdout.write(f"- đơn {o.code} · hoá đơn {inv.code} · số tiền bán {inv.amount:.0f} · lô {', '.join(sorted(batch_ids))}")

        if closed:
            self.stdout.write(
                "Lô đã CLOSED liên quan (lãi lỗ lô giữ nguyên, điều chỉnh vào kỳ hiện tại): "
                + ", ".join(sorted(closed))
            )
            for code, batch_ids in closed_orders:
                self.stdout.write(
                    f"  * đơn {code} · lô {', '.join(batch_ids)} — lãi lỗ lô giữ nguyên, điều chỉnh vào kỳ hiện tại"
                )
        else:
            self.stdout.write("Không có lô CLOSED bị ảnh hưởng.")

        if not apply:
            self.stdout.write("Chưa ghi gì. Thêm --apply để lập chứng từ.")
            return

        created = 0
        for o in orders:
            with transaction.atomic():
                audit = _cancel_audit(o)
                stock_restored = (audit.changes or {}).get("stock_restored", True) if audit else True
                cn = services.issue_cancel_credit_note(
                    invoice=o.invoice, actor=None,
                    reason_code=(audit.changes or {}).get("reason_code", "") if audit else "",
                    stock_restored=bool(stock_restored),
                    at=None,  # E1: lúc chạy lệnh (timezone.now() trong service)
                    backfilled=True,
                )
                created += 1
                self.stdout.write(f"  đã lập {cn.code}")
        self.stdout.write(self.style.SUCCESS(f"Đã lập {created} chứng từ đảo."))
