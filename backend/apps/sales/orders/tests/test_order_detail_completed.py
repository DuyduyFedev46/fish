"""
W37 L2: chi tiết đơn có `refund_summary` (S5, S7-AC8, S7-AC10). BR-BH-20, BR-HT-04, bất biến 1 và 9.
Dữ liệu giả (SĐT 0900000xxx).
"""
import json
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.common.tests.fixtures import client_for
from apps.delivery.models import DeliveryNote
from apps.delivery.tests.test_order_completion import CompletionBase
from apps.sales.models import Refund, SalesInvoice, SalesOrder

S = DeliveryNote.Status
COST_KEYS = ("unit_cost", "landed_unit_cost", "purchase_rate", "profit", "pnl", "cost")


def detail_url(order):
    return f"/api/sales/orders/{order.pk}/"


def keys_deep(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from keys_deep(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from keys_deep(inner)


class RefundSummaryTests(CompletionBase):
    def _completed(self):
        order, note = self._processing()
        self._complete(self.courier, note)
        order.refresh_from_db()
        return order

    def _refund(self, order, amount, status):
        return Refund.objects.create(
            sales_invoice=order.invoice, amount=Decimal(amount), status=status, created_by=self.owner,
        )

    def _detail(self, user, order):
        resp = client_for(user).get(detail_url(order))
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_refund_summary_zero_without_refunds(self):
        order = self._completed()
        self.assertEqual(self._detail(self.manager, order)["refund_summary"],
                         {"refunded_amount": "0", "pending_amount": "0"})

    def test_refund_summary_sums_refunded_and_pending_and_ignores_failed(self):
        order = self._completed()
        self._refund(order, "200000", Refund.Status.REFUNDED)
        self._refund(order, "30000", Refund.Status.REFUNDED)
        self._refund(order, "100000", Refund.Status.PENDING)
        self._refund(order, "50000", Refund.Status.FAILED)
        self.assertEqual(self._detail(self.manager, order)["refund_summary"],
                         {"refunded_amount": "230000", "pending_amount": "100000"})

    def test_refund_summary_zero_when_order_has_no_invoice(self):
        order = self._order()  # BOOKED, chưa có hoá đơn
        self.assertFalse(SalesInvoice.objects.filter(sales_order=order).exists())
        self.assertEqual(self._detail(self.manager, order)["refund_summary"],
                         {"refunded_amount": "0", "pending_amount": "0"})

    def test_refund_summary_has_only_two_money_strings_no_personal_data(self):
        order = self._completed()
        self._refund(order, "200000", Refund.Status.REFUNDED)
        summary = self._detail(self.owner, order)["refund_summary"]
        self.assertEqual(set(summary), {"refunded_amount", "pending_amount"})
        self.assertTrue(all(isinstance(v, str) for v in summary.values()))
        blob = json.dumps(summary, ensure_ascii=False)
        for secret in ("0900000123", "Khách", "Lê Lợi"):
            self.assertNotIn(secret, blob)

    def test_refund_summary_present_for_scope_limited_courier_without_customer_data(self):
        order = self._completed()
        self._refund(order, "200000", Refund.Status.PENDING)
        body = self._detail(self.courier, order)
        self.assertEqual(body["refund_summary"], {"refunded_amount": "0", "pending_amount": "200000"})

    def test_no_extra_queries_for_refund_summary(self):
        """`refund_summary` tính từ `invoice.refunds` đã prefetch: thêm phiếu hoàn không thêm query (không N+1)."""
        order = self._completed()
        client = client_for(self.manager)
        self._refund(order, "200000", Refund.Status.REFUNDED)
        client.get(detail_url(order))  # làm nóng cache quyền/content type
        with CaptureQueriesContext(connection) as one:
            client.get(detail_url(order))
        self._refund(order, "100000", Refund.Status.PENDING)
        self._refund(order, "50000", Refund.Status.FAILED)
        with CaptureQueriesContext(connection) as three:
            client.get(detail_url(order))
        self.assertEqual(len(three), len(one))

    def test_s5_ac8_s7_ac8_completed_order_offers_create_refund_not_cancel(self):
        order = self._completed()
        for user in (self.manager, self.owner):
            with self.subTest(user=user.username):
                actions = self._detail(user, order)["available_actions"]
                self.assertIn("create_refund", actions)
                self.assertNotIn("cancel", actions)

    def test_s5_ac8_no_create_refund_when_nothing_left_to_refund(self):
        order = self._completed()
        self._refund(order, str(order.invoice.amount), Refund.Status.REFUNDED)
        actions = self._detail(self.manager, order)["available_actions"]
        self.assertNotIn("create_refund", actions)
        self.assertNotIn("cancel", actions)
        self.assertEqual(SalesOrder.objects.get(pk=order.pk).status, "COMPLETED")

    def test_s7_ac10_no_cost_keys_anywhere_for_manager_and_warehouse(self):
        order = self._completed()
        self._refund(order, "200000", Refund.Status.REFUNDED)
        for user in (self.manager, self.kho):  # naming: allow - thuộc tính fixture cũ của OrderApiBase
            with self.subTest(user=user.username):
                resp = client_for(user).get(detail_url(order))
                if resp.status_code != 200:  # kho có thể không có quyền xem đơn: vẫn không rò gì
                    self.assertEqual(resp.status_code, 403)
                    continue
                found = set(keys_deep(resp.json()))
                for key in COST_KEYS:
                    self.assertNotIn(key, found)

    def test_unauthenticated_and_no_perm_cannot_read_summary(self):
        order = self._completed()
        self.assertEqual(client_for(None).get(detail_url(order)).status_code, 401)
        self.assertEqual(client_for(self.nobody).get(detail_url(order)).status_code, 403)
