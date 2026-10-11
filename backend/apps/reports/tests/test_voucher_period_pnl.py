"""
SHOP-3b-04 AC9 (BR-BC-01, 02, bất biến 1) — mã giảm giá không làm sai lãi lỗ THEO KỲ: doanh thu ghi theo tiền thực thu
(hoá đơn = tổng sau giảm), giá vốn ảnh chụp không đổi, kỳ đã qua không đổi số. Lãi lỗ THEO LÔ giữ công thức cũ
(02b §8.1, chờ Duy quyết riêng) — test cuối ghi lại đúng hiện trạng đó để ai đổi công thức phải sửa test có chủ đích.
`apps/reports/services.py` KHÔNG sửa ở lô 3b. Dữ liệu giả.
"""
import datetime
from decimal import Decimal

from django.utils import timezone

from apps.accounts import roles
from apps.catalog.vouchers.tests.base import make_voucher
from apps.common.tests.fixtures import make_user
from apps.reports import services as report_services
from apps.sales.models import SalesInvoice, SalesInvoiceLineBatch
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.base import SalesServiceBase
from apps.sales.payments import services as payment_services

D = Decimal


class VoucherPeriodPnlTests(SalesServiceBase):
    def setUp(self):
        super().setUp()
        self.item = self._item("MUC-A", price="150000")
        self.batch = self._stocked_batch(self.item, "100", rate="100000")  # giá vốn 100.000/kg
        self.owner = make_user("chu_pnl", roles.OWNER)
        make_voucher(owner=self.owner, code="GIAM50K", kind="AMOUNT", value=D("50000"), max_discount=None,
                     min_order_amount=D("0"))

    def paid(self, phone, qty="4", voucher_code=None):
        order = order_services.create_order(
            customer_phone=phone, customer_name="Khách giả", delivery_address="1 Đường Thử", phone=phone,
            lines=[{"item_code": "MUC-A", "qty": D(qty)}], voucher_code=voucher_code,
        )
        payment_services.confirm_payment(order=order, bank_txn_id=f"TX{phone}", amount=order.total_amount,
                                         received_at=timezone.now())
        return SalesInvoice.objects.get(sales_order=order)

    def pnl(self, when):
        return report_services.period_pnl(year=when.year, month=when.month)

    def test_revenue_is_the_amount_actually_paid_and_cogs_is_unchanged(self):
        now = timezone.now()
        invoice = self.paid("0900000011", voucher_code="GIAM50K")  # 4 kg = 600.000, giảm 50.000
        self.assertEqual(invoice.amount, D("550000"))
        pnl = self.pnl(now)
        self.assertEqual(pnl["revenue"], D("550000"))
        self.assertEqual(pnl["cogs"], D("400000"))   # 4 kg × 100.000: không phụ thuộc giảm giá
        self.assertEqual(pnl["profit"], D("150000"))

    def test_cogs_snapshot_equals_the_same_order_without_voucher(self):
        with_code = self.paid("0900000012", voucher_code="GIAM50K")
        without = self.paid("0900000013")
        def cost(invoice):
            return sorted(SalesInvoiceLineBatch.objects.filter(invoice_line__invoice=invoice)
                          .values_list("qty", "unit_cost"))
        self.assertEqual(cost(with_code), cost(without))
        self.assertEqual(without.amount - with_code.amount, D("50000"))

    def test_invoice_lines_sum_to_the_invoice_amount(self):
        invoice = self.paid("0900000014", voucher_code="GIAM50K")
        self.assertEqual(sum(line.amount for line in invoice.lines.all()), invoice.amount)

    def test_past_period_does_not_change_when_vouchers_are_used_later(self):
        past = timezone.now() - datetime.timedelta(days=62)
        old = self.paid("0900000015")
        SalesInvoice.objects.filter(pk=old.pk).update(issued_at=past)
        before = self.pnl(past)
        self.paid("0900000016", voucher_code="GIAM50K")
        self.assertEqual(self.pnl(past), before)
        self.assertEqual(before["revenue"], D("600000"))

    def test_batch_pnl_keeps_the_old_gross_formula_pending_owner_decision(self):
        self.paid("0900000017", voucher_code="GIAM50K")
        self.batch.refresh_from_db()
        result = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(result["revenue"], D("600000"))  # 4 kg × 150.000 gộp, chưa trừ giảm (02b §8.1)
