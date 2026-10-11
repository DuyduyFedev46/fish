"""
SHOP-3b-04 AC9 (BR-BC-01, 02, 04, bất biến 1) — mã giảm giá không làm sai lãi lỗ THEO KỲ: doanh thu ghi theo tiền thực thu
(hoá đơn = tổng sau giảm), giá vốn ảnh chụp không đổi, kỳ đã qua không đổi số. Lãi lỗ THEO LÔ (Duy chốt 11/10) trừ phần
giảm của MÃ giảm giá đã dùng, chia theo kg phân bổ; ưu đãi tự động (PricingRule) và đơn không mã giữ `qty × rate`.
Dữ liệu giả.
"""
import datetime
from decimal import Decimal

from django.utils import timezone

from apps.accounts import roles
from apps.catalog.models import PricingRule
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

    def test_batch_pnl_deducts_voucher_discount(self):
        self.paid("0900000017", voucher_code="GIAM50K")
        self.batch.refresh_from_db()
        result = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(result["revenue"], D("550000"))   # 600.000 - 50.000 đã phân bổ vào dòng
        self.assertEqual(result["profit"], D("550000") - result["total_cost"])

    def test_batch_pnl_without_voucher_unchanged(self):
        self.paid("0900000018")
        self.assertEqual(report_services.batch_pnl(batch=self.batch)["revenue"], D("600000"))

    def test_line_spanning_two_batches_splits_net_revenue_and_sums_exactly(self):
        # Lô thứ hai hạn sau; đơn 7 kg ăn 3 kg lô 1 + ... nên dùng đơn lớn hơn tồn lô 1.
        small = self._item("MUC-B", price="150000")
        b1 = self._stocked_batch(small, "3", rate="100000")
        b2 = self._stocked_batch(small, "10", rate="100000")
        order = order_services.create_order(
            customer_phone="0900000019", customer_name="Khách giả", delivery_address="1 Đường Thử",
            phone="0900000019", lines=[{"item_code": "MUC-B", "qty": D("7")}], voucher_code="GIAM50K")
        payment_services.confirm_payment(order=order, bank_txn_id="TX19", amount=order.total_amount,
                                         received_at=timezone.now())
        self.assertEqual(sum(1 for b in (b1, b2) if report_services.batch_pnl(batch=b)["revenue"] > 0), 2)
        total = sum(report_services.batch_pnl(batch=b)["revenue"] for b in (b1, b2))
        self.assertEqual(total, D("1000000"))   # 7 × 150.000 - 50.000
        for b in (b1, b2):
            r = report_services.batch_pnl(batch=b)["revenue"]
            self.assertEqual(r, r.to_integral_value())

    def test_period_profit_matches_sum_of_batch_profits(self):
        now = timezone.now()
        self.paid("0900000020", voucher_code="GIAM50K")
        self.paid("0900000021")
        self.batch.refresh_from_db()
        self.assertEqual(self.pnl(now)["revenue"], report_services.batch_pnl(batch=self.batch)["revenue"])

    def test_cancelled_paid_voucher_order_reverses_net_revenue(self):
        from apps.sales.credit_notes import services as cn_services
        invoice = self.paid("0900000022", voucher_code="GIAM50K")
        cn_services.issue_cancel_credit_note(invoice=invoice, actor=None, reason_code="", stock_restored=False)
        result = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(result["reversed_revenue"], D("550000"))   # đảo đúng phần thực thu
        self.assertEqual(result["revenue"], D("0"))

    def test_batch_pnl_cost_fields_unchanged_by_voucher(self):
        self.paid("0900000023", voucher_code="GIAM50K")
        r = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(r["purchase_cost"], D("10000000"))

    def _pricing_rule(self):
        PricingRule.objects.create(
            name="giảm 20k", is_active=True, apply_on=PricingRule.ApplyOn.ITEM, item=self.item, min_qty=D("1"),
            discount_type=PricingRule.DiscountType.AMOUNT, discount_value=D("5000"),
        )

    def test_pricing_rule_order_without_voucher_keeps_gross_batch_revenue(self):
        self._pricing_rule()
        invoice = self.paid("0900000024")
        self.assertLess(invoice.amount, D("600000"))   # ưu đãi tự động có giảm vào hoá đơn
        self.assertEqual(report_services.batch_pnl(batch=self.batch)["revenue"], D("600000"))

    def test_closed_batch_with_pricing_rule_order_does_not_change(self):
        self._pricing_rule()
        self.paid("0900000025")
        before = report_services.batch_pnl(batch=self.batch)["revenue"]
        self.batch.status = "CLOSED"
        self.batch.closed_at = timezone.now()
        self.batch.save(update_fields=["status", "closed_at"])
        self.assertEqual(report_services.batch_pnl(batch=self.batch)["revenue"], before)
        self.assertEqual(before, D("600000"))

    def test_voucher_plus_pricing_rule_uses_amount_actually_paid(self):
        self._pricing_rule()
        invoice = self.paid("0900000026", voucher_code="GIAM50K")
        self.assertEqual(report_services.batch_pnl(batch=self.batch)["revenue"], invoice.amount)

    def test_batch_pnl_query_count_does_not_grow_with_orders(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.paid("0900000027", voucher_code="GIAM50K")
        with CaptureQueriesContext(connection) as few:
            report_services.batch_pnl(batch=self.batch)
        for i in range(28, 33):
            self.paid(f"09000000{i}", voucher_code="GIAM50K")
        with CaptureQueriesContext(connection) as many:
            report_services.batch_pnl(batch=self.batch)
        # mỗi dòng thêm tối đa 1 truy vấn phân bổ (nhớ theo dòng), không nhân theo số phân bổ
        self.assertLessEqual(len(many) - len(few), 5)
