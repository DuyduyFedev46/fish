from decimal import Decimal

from django.utils import timezone

from apps.inventory.models import Batch
from apps.sales.models import SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.base import SalesServiceBase
from apps.sales.payments import services as payment_services


class PaymentAndInvoiceTests(SalesServiceBase):
    def _order(self, phone="0900000040", qty="3", price="100000", stock="100"):
        ca = self._item(f"IT{phone[-3:]}", price=price)
        self._stocked_batch(ca, stock)
        return order_services.create_order(
            customer_phone=phone, customer_name="A", delivery_address="x",
            phone=phone, lines=[{"item_code": ca.code, "qty": Decimal(qty)}],
        ), ca

    def test_confirm_payment_matched_issues_invoice_and_deducts_stock(self):
        order, ca = self._order()
        payment_services.confirm_payment(
            order=order, bank_txn_id="TX1", amount=order.total_amount,
            received_at=timezone.now(),
        )
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)
        inv = SalesInvoice.objects.get(sales_order=order)
        self.assertEqual(inv.amount, order.total_amount)
        # tồn thật đã trừ, giữ chỗ đã nhả; SalesInvoiceLineBatch (nguồn giá vốn) tồn tại
        b = Batch.objects.get(item=ca)
        self.assertEqual(b.qty_available, Decimal("97"))
        self.assertEqual(b.qty_reserved, Decimal("0"))
        silb = inv.lines.first().batch_allocations.first()
        self.assertEqual(silb.qty, Decimal("3"))
        self.assertGreater(silb.unit_cost, Decimal("0"))

    def test_confirm_payment_idempotent(self):
        order, ca = self._order(phone="0900000041")
        payment_services.confirm_payment(order=order, bank_txn_id="TXDUP", amount=order.total_amount,
                                 received_at=timezone.now())
        payment_services.confirm_payment(order=order, bank_txn_id="TXDUP", amount=order.total_amount,
                                 received_at=timezone.now())  # gọi lại
        self.assertEqual(SalesInvoice.objects.filter(sales_order=order).count(), 1)  # không xuất 2 lần
        self.assertEqual(Batch.objects.get(item=ca).qty_available, Decimal("97"))    # không trừ 2 lần

    def test_underpaid_does_not_confirm(self):
        order, ca = self._order(phone="0900000042")
        pay = payment_services.confirm_payment(
            order=order, bank_txn_id="TXLOW",
            amount=order.total_amount - Decimal("1"), received_at=timezone.now(),
        )
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.BOOKED)  # vẫn chờ
        self.assertEqual(SalesInvoice.objects.filter(sales_order=order).count(), 0)
        self.assertEqual(pay.match_status, pay.MatchStatus.UNDERPAID)

    def test_payment_after_cancel_is_orphan(self):
        order, ca = self._order(phone="0900000043")
        order.status = SalesOrder.Status.AUTO_CANCELLED
        order.save(update_fields=["status"])
        pay = payment_services.confirm_payment(order=order, bank_txn_id="TXORP",
                                       amount=order.total_amount, received_at=timezone.now())
        self.assertEqual(pay.match_status, pay.MatchStatus.ORPHAN)
