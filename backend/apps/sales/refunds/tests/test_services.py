from decimal import Decimal

from django.utils import timezone

from apps.common.exceptions import BusinessError
from apps.sales.models import Refund, SalesInvoice
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.base import SalesServiceBase
from apps.sales.payments import services as payment_services
from apps.sales.refunds import services as refund_services


class RefundTests(SalesServiceBase):
    def test_refund_not_exceed_collected_and_requires_txn_ref(self):
        from django.contrib.auth.models import User

        chu = User.objects.create(username="chu_refund")  # hoàn tiền luôn do người, không phải Hệ thống
        ca = self._item("RF1", price="100000")
        self._stocked_batch(ca, "10")
        order = order_services.create_order(
            customer_phone="0900000060", customer_name="A", delivery_address="x",
            phone="0900000060", lines=[{"item_code": "RF1", "qty": Decimal("2")}],
        )
        payment_services.confirm_payment(order=order, bank_txn_id="RFTX", amount=order.total_amount,
                                 received_at=timezone.now())
        inv = SalesInvoice.objects.get(sales_order=order)
        with self.assertRaises(BusinessError):  # vượt số đã thu
            refund_services.create_refund(invoice=inv, amount=inv.amount + Decimal("1"),
                                   is_partial=False, reason="", actor=chu)
        refund = refund_services.create_refund(invoice=inv, amount=inv.amount, is_partial=False,
                                        reason="khách đổi ý", actor=chu)
        self.assertEqual(refund.status, Refund.Status.PENDING)
        with self.assertRaises(BusinessError):  # xác nhận suông không có mã GD
            refund_services.confirm_refund(refund=refund, bank_txn_ref="", actor=chu)
        confirmed = refund_services.confirm_refund(refund=refund, bank_txn_ref="CK123", actor=chu)
        self.assertEqual(confirmed.status, Refund.Status.REFUNDED)
