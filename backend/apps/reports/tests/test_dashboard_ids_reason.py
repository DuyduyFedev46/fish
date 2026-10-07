"""
TL15-dash (Lô 17a, A2, ED-08-AC3): dashboard `recent_orders[]`, `batches[]`, `alerts[]` có `id`; `recent_orders[]` có `reason`
cùng shape với cột Lý do của `/orders/` ({code, label} hoặc null). Dữ liệu giả.
"""
import datetime
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_batch, make_master, make_order_with_note, make_user
from apps.inventory.models import Batch
from apps.sales.models import SalesCreditNote, SalesOrder

URL = "/api/dashboard/summary/"
NOTE_PHONE = "0900000777"  # giả, ghi trong cancel_note: không được lộ qua `reason`


class DashboardIdsReasonTests(TestCase):
    def setUp(self):
        self.owner = make_user("u_owner", roles.OWNER)
        self.warehouse_staff = make_user("u_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("u_courier", roles.DELIVERY_STAFF)
        item, supplier, warehouse = make_master()
        self.batch = make_batch(item, supplier, warehouse, qty="50")
        soon = timezone.localdate() + datetime.timedelta(days=3)
        Batch.objects.filter(pk=self.batch.pk).update(expiry_date=soon, status=Batch.Status.SELLING)

    def _get(self, user):
        response = client_for(user).get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def _cancelled_order(self, code, reason_code, cancel_note=""):
        self._seq = getattr(self, "_seq", 0) + 1
        order, _customer, _note = make_order_with_note(code, f"09000006{self._seq:02d}")
        order.status = SalesOrder.Status.CANCELLED
        order.cancel_note = cancel_note
        order.save(update_fields=["status", "cancel_note"])
        invoice = order.invoice
        SalesCreditNote.objects.create(
            code=f"DC-{code}", source_key=f"cancel:{order.pk}", sales_invoice=invoice,
            issued_at=timezone.now(), amount=Decimal("100000"), stock_restored=True, reason_code=reason_code,
        )
        return order

    def test_tl15_dash_ids_present_and_match_pk_in_three_arrays(self):
        order, _c, _n = make_order_with_note("SO-D1", "0900000502")
        data = self._get(self.owner)
        self.assertEqual(data["recent_orders"][0]["id"], order.pk)
        self.assertEqual([b["id"] for b in data["batches"]], [self.batch.pk])
        self.assertEqual([a["id"] for a in data["alerts"]], [self.batch.pk])

    def test_tl15_dash_reason_auto_cancelled(self):
        order, _c, _n = make_order_with_note("SO-D2", "0900000503")
        SalesOrder.objects.filter(pk=order.pk).update(status=SalesOrder.Status.AUTO_CANCELLED)
        row = self._get(self.owner)["recent_orders"][0]
        self.assertEqual(row["reason"], {"code": "AUTO_CANCELLED", "label": "Hết giờ giữ chỗ"})

    def test_tl15_dash_reason_cancelled_with_code(self):
        self._cancelled_order("SO-D3", "CUSTOMER_CHANGED_MIND")
        row = self._get(self.owner)["recent_orders"][0]
        self.assertEqual(row["reason"], {"code": "CUSTOMER_CHANGED_MIND", "label": "Khách đổi ý"})

    def test_tl15_dash_ordinary_order_reason_is_null(self):
        make_order_with_note("SO-D4", "0900000504")
        row = self._get(self.owner)["recent_orders"][0]
        self.assertIn("reason", row)
        self.assertIsNone(row["reason"])

    def test_tl15_dash_reason_does_not_leak_cancel_note(self):
        self._cancelled_order("SO-D5", "OTHER", cancel_note=f"Khách gọi lại số {NOTE_PHONE}")
        response = client_for(self.owner).get(URL)
        self.assertNotIn(NOTE_PHONE, response.content.decode())
        self.assertEqual(response.json()["recent_orders"][0]["reason"]["label"], "Lý do khác")

    def test_tl15_dash_warehouse_staff_sees_no_cost_fields(self):
        data = self._get(self.warehouse_staff)
        self.assertNotIn("inventory_value", data["kpis"])
        self.assertTrue(all("unit_cost" not in b for b in data["batches"]))
        self.assertIn("id", data["batches"][0])

    def test_tl15_dash_courier_gets_403(self):
        self.assertEqual(client_for(self.courier).get(URL).status_code, 403)
        self.assertEqual(client_for(None).get(URL).status_code, 401)

    def test_tl15_dash_query_count_does_not_grow_with_number_of_orders(self):
        self._cancelled_order("SO-Q1", "CUSTOMER_CHANGED_MIND")
        client = client_for(self.owner)
        client.get(URL)  # làm nóng cache quyền/nội dung
        with CaptureQueriesContext(connection) as few:
            client.get(URL)
        for i in range(2, 8):
            self._cancelled_order(f"SO-Q{i}", "OTHER")
        with CaptureQueriesContext(connection) as many:
            response = client.get(URL)
        self.assertEqual(len(response.json()["recent_orders"]), 7)
        self.assertLessEqual(len(many), len(few))
