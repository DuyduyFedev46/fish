"""
Nợ review lô 3+4 làm ở lô 3b (02b §12): M1 cờ `delivery.awaiting_confirmation`, M3 tự huỷ mà mọi giao dịch nghi trùng,
D3 mốc server `payment_pending_since`, L1 log mã đơn lấy từ body, L2 bỏ `_now`/`_body` thừa. Dữ liệu giả.
"""
import datetime
import logging

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.delivery.models import DeliveryNote
from apps.sales.models import PaymentTransaction, SalesOrder
from apps.sales.orders import services
from apps.sales.orders.shop_api import _loggable_code
from apps.sales.orders.tests.test_shop_lookup import PHONE, LookupBase, lookup
from apps.sales.payments import services as payment_services

S = DeliveryNote.Status
O = SalesOrder.Status


class AwaitingConfirmationTests(LookupBase):
    def delivery_of(self, order):
        return self.by_phone(order).json()["delivery"]

    def test_m1_flag_is_true_only_while_the_latest_note_is_confirming(self):
        order = self._paid_order(phone=PHONE)
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        expected = {
            S.CONFIRMING: True, S.PREPARING: False, S.READY: False,
            S.DELIVERING: False, S.COMPLETED: False, S.FAILED: False,
        }
        for status, flag in expected.items():
            with self.subTest(status=status):
                DeliveryNote.objects.filter(pk=note.pk).update(status=status)
                delivery = self.delivery_of(order)
                self.assertIs(delivery["awaiting_confirmation"], flag)
                self.assertEqual(set(delivery), {"step", "step_label", "awaiting_confirmation"})

    def test_m1_confirming_example_matches_contract(self):
        order = self._paid_order(phone=PHONE)
        DeliveryNote.objects.filter(sales_invoice=order.invoice).update(status=S.CONFIRMING)
        self.assertEqual(
            self.delivery_of(order),
            {"step": "preparing", "step_label": "Chờ vựa gọi xác nhận", "awaiting_confirmation": True},
        )

    def test_m1_no_delivery_block_when_no_note_or_cancelled(self):
        order = self._order(phone=PHONE)
        self.assertIsNone(self.delivery_of(order))


class DuplicateOnlyLateMoneyTests(LookupBase):
    """M3: tự huỷ mà mọi giao dịch về đều nghi trùng -> coi như không có tiền về (hết giờ), không câu "trả lại 0đ"."""

    def auto_cancelled_with_late_txn(self, txn="FT2626700001"):
        order = self._order(phone=PHONE)
        services.cancel_unpaid_expired(now=timezone.now() + datetime.timedelta(hours=2))
        order.refresh_from_db()
        payment_services.confirm_payment(order=order, bank_txn_id=txn, amount=order.total_amount, received_at=timezone.now())
        return order

    def test_m3_only_suspected_duplicate_rows_means_expired_without_notice(self):
        order = self.auto_cancelled_with_late_txn()
        PaymentTransaction.objects.filter(sales_order=order).update(duplicate_warning="nghi trùng")
        data = self.by_phone(order).json()
        self.assertEqual((data["state"], data["late_payment"], data["cancel_notice"]), ("expired", False, None))
        self.assertEqual(data["status_label"], "Đã huỷ vì quá giờ thanh toán")

    def test_m3_real_money_still_gives_late_payment_and_notice(self):
        order = self.auto_cancelled_with_late_txn()
        data = self.by_phone(order).json()
        self.assertEqual((data["state"], data["late_payment"]), ("cancelled", True))
        self.assertEqual(data["cancel_notice"]["cancelled_amount"], "540000")

    def test_m3_mixed_real_and_duplicate_counts_only_real(self):
        order = self.auto_cancelled_with_late_txn("FT2626700002")
        payment_services.confirm_payment(order=order, bank_txn_id="FT2626700003", amount=order.total_amount, received_at=timezone.now())
        PaymentTransaction.objects.filter(bank_txn_id="FT2626700003").update(duplicate_warning="nghi trùng")
        data = self.by_phone(order).json()
        self.assertTrue(data["late_payment"])
        self.assertEqual(data["cancel_notice"]["cancelled_amount"], "540000")

    def test_m3_notice_never_says_zero_dong(self):
        order = self.auto_cancelled_with_late_txn("FT2626700004")
        PaymentTransaction.objects.filter(sales_order=order).update(duplicate_warning="nghi trùng")
        self.assertNotIn("0đ", str(self.by_phone(order).json()))


class PaymentPendingSinceTests(LookupBase):
    """D3: mốc server khách được đưa sang cổng thanh toán (thay sessionStorage `shop_pending_since_v1`)."""

    def checkout(self, order):
        return APIClient().post(f"/api/shop/orders/{order.code}/checkout/", {}, format="json")

    def test_null_until_the_customer_opens_the_gateway(self):
        order = self._order(phone=PHONE)
        self.assertIsNone(self.by_phone(order).json()["payment_pending_since"])

    def test_checkout_records_the_time_and_lookup_returns_utc_z(self):
        order = self._order(phone=PHONE)
        before = timezone.now()
        response = self.checkout(order)
        self.assertEqual(response.status_code, 200, response.content)
        order.refresh_from_db()
        self.assertIsNotNone(order.payment_started_at)
        self.assertGreaterEqual(order.payment_started_at, before)
        value = self.by_phone(order).json()["payment_pending_since"]
        self.assertTrue(value.endswith("Z"))
        self.assertEqual(value, order.payment_started_at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    def test_second_checkout_moves_the_marker_forward(self):
        order = self._order(phone=PHONE)
        self.checkout(order)
        SalesOrder.objects.filter(pk=order.pk).update(payment_started_at=timezone.now() - datetime.timedelta(minutes=10))
        self.checkout(order)
        order.refresh_from_db()
        self.assertGreater(order.payment_started_at, timezone.now() - datetime.timedelta(minutes=1))

    def test_marker_is_hidden_once_the_order_is_no_longer_booked(self):
        order = self._order(phone=PHONE)
        self.checkout(order)
        payment_services.confirm_payment(order=order, bank_txn_id="FT2626700010", amount=order.total_amount, received_at=timezone.now())
        self.assertIsNone(self.by_phone(order).json()["payment_pending_since"])

    def test_failed_checkout_does_not_set_the_marker(self):
        order = self._order(phone=PHONE)
        SalesOrder.objects.filter(pk=order.pk).update(status=O.AUTO_CANCELLED)
        self.checkout(order)
        order.refresh_from_db()
        self.assertIsNone(order.payment_started_at)


class LogHygieneTests(LookupBase):
    def tearDown(self):
        cache.clear()

    def test_l1_loggable_code_strips_control_chars_and_caps_length(self):
        self.assertEqual(_loggable_code("SO261011-AB12CD\nFAKE LOG LINE"), "SO261011-AB12CDFAKELOGLINE"[:32])
        self.assertEqual(len(_loggable_code("A" * 500)), 32)
        self.assertNotIn("\n", _loggable_code("A\r\nB"))
        self.assertEqual(_loggable_code("SO261011-AB12CD"), "SO261011-AB12CD")

    def test_l1_lookup_logs_do_not_carry_raw_body_text(self):
        class Capture(logging.Handler):
            def __init__(self):
                super().__init__(level=logging.DEBUG)
                self.lines = []

            def emit(self, record):
                self.lines.append(record.getMessage())

        capture = Capture()
        logger = logging.getLogger("apps.sales.orders.shop_api")
        previous = logger.level
        logger.addHandler(capture)
        logger.setLevel(logging.DEBUG)
        try:
            lookup({"order_code": "SO1\nINJECTED LINE " + "X" * 200, "phone": PHONE})
        finally:
            logger.removeHandler(capture)
            logger.setLevel(previous)
        self.assertTrue(any("shop lookup miss" in line for line in capture.lines))
        for line in capture.lines:
            self.assertNotIn("\n", line)
            self.assertNotIn("INJECTED LINE", line)
            self.assertNotIn(PHONE, line)
            self.assertLessEqual(len(line), 120)

    def test_l2_view_no_longer_reaches_into_services_private_clock(self):
        import inspect

        from apps.sales.orders import shop_api

        source = inspect.getsource(shop_api)
        self.assertNotIn("services._now", source)
        self.assertNotIn("_body", source.replace("_parse_create_body", ""))
