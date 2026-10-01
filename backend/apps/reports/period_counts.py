"""
Số chứng từ của một kỳ cho màn Báo cáo (R15): `invoice_count`, `refund_count`.

Đếm đúng tập chứng từ mà `services.period_pnl` đã cộng tiền, để số đếm và số tiền cùng một căn cứ:
- `invoice_count`: hoá đơn `ISSUED` có `issued_at` thuộc tháng (doanh thu ghi nhận, BR-BC-01).
- `refund_count`: phiếu hoàn `REFUNDED` có hoá đơn, xác nhận trong tháng, trừ phiếu xác nhận SAU/CÙNG lúc lập chứng từ
  đảo của hoá đơn đó (đã đảo bằng chứng từ, không trừ hai lần — D1-B).
`period_pnl` không đổi: nếu quy tắc hoàn tiền ở đó đổi thì sửa theo ở đây (test `test_r15_ac6_*` giữ hai bên khớp).
"""
from django.db.models import Exists, OuterRef

from apps.sales.models import Refund, SalesCreditNote, SalesInvoice


def period_counts(*, year, month):
    invoice_count = SalesInvoice.objects.filter(
        status=SalesInvoice.Status.ISSUED, issued_at__year=year, issued_at__month=month,
    ).count()
    covered_by_credit_note = SalesCreditNote.objects.filter(
        sales_invoice=OuterRef("sales_invoice"), issued_at__lte=OuterRef("confirmed_at"),
    )
    refund_count = (
        Refund.objects.filter(
            status=Refund.Status.REFUNDED, confirmed_at__year=year, confirmed_at__month=month,
            sales_invoice__isnull=False,
        )
        .exclude(Exists(covered_by_credit_note))
        .count()
    )
    return {"invoice_count": invoice_count, "refund_count": refund_count}
