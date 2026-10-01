"""
R10 — `GET /api/purchasing/receipts/` (02b §3.8, ED-20-AC1/AC5/AC6): danh sách phiếu nhập.
BR-MH-06: tiền mua và đơn giá chỉ lộ cho người có `view_costprice`. BR-PQ: ai được xem danh sách.
"""
import datetime
import json
from decimal import Decimal

from apps.common.tests.fixtures import client_for

from .api_base import (
    INVOICE_SENTINEL, RATE, RATE_SENTINEL, URL, ReceiptsApiBase, find_cost_keys,
)

MAIN_AMOUNT = "1234570.00"  # 10 kg x 123457 + 5 kg x 80000 = 1234570 + 400000
MAIN_TOTAL = "1634570.00"


class ReceiptListTests(ReceiptsApiBase):
    # --- phân quyền -------------------------------------------------------------------------------------------
    def test_r10_permission_matrix_list(self):
        for user, expected in (
            (self.owner, 200), (self.manager, 200), (self.warehouse_staff, 200),
            (self.courier, 403), (self.customer_service, 403), (self.no_group, 403), (None, 401),
        ):
            self.assertEqual(client_for(user).get(URL).status_code, expected, getattr(user, "username", "anon"))

    def test_r10_permission_matrix_detail(self):
        for user, expected in (
            (self.owner, 200), (self.manager, 200), (self.warehouse_staff, 200),
            (self.courier, 403), (self.customer_service, 403), (None, 401),
        ):
            self.assertEqual(client_for(user).get(f"{URL}{self.receipt.pk}/").status_code, expected)

    # --- nội dung (owner) -------------------------------------------------------------------------------------
    def test_r10_owner_row_shape(self):
        self.add_invoice(self.receipt)
        resp = self.get(self.owner)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 1)
        row = body["results"][0]
        self.assertEqual(row["id"], self.receipt.pk)
        self.assertEqual(row["code"], f"PR-{self.receipt.pk}")
        self.assertEqual(row["supplier"], self.supplier.pk)
        self.assertEqual(row["supplier_name"], "Đầu mối A")
        self.assertEqual(row["warehouse_name"], "Kho chính")
        self.assertEqual(row["created_by_name"], "Tâm Thử")
        self.assertEqual(row["items_summary"], "Cá thu, Tôm sú")
        self.assertEqual(row["total_qty"], "15.000")
        self.assertEqual(row["batch_codes"], [b.batch_id for b in self.batches])
        self.assertEqual(row["status"], "SUBMITTED")
        self.assertEqual(row["status_label"], "Đã ghi nhận")
        self.assertEqual(row["received_date"], "2026-09-28")
        self.assertEqual(row["purchase_amount"], MAIN_TOTAL)
        self.assertEqual(row["invoice"], {"id": self.receipt.invoices.first().pk})

    def test_r10_draft_receipt_has_no_batch_and_no_invoice(self):
        draft = self.make_draft()
        row = next(r for r in self.get(self.owner).json()["results"] if r["id"] == draft.pk)
        self.assertEqual(row["batch_codes"], [])
        self.assertIsNone(row["invoice"])
        self.assertEqual(row["status_label"], "Nháp")
        self.assertEqual(row["purchase_amount"], "370371.00")

    def test_r10_status_label_cancelled(self):
        draft = self.make_draft()
        type(draft).objects.filter(pk=draft.pk).update(status="CANCELLED")
        row = next(r for r in self.get(self.owner).json()["results"] if r["id"] == draft.pk)
        self.assertEqual(row["status_label"], "Đã huỷ")

    def test_r10_pagination_shape_and_page_size(self):
        for day in range(1, 23):
            self.make_draft(received_date=datetime.date(2026, 10, 1) + datetime.timedelta(days=day))
        body = self.get(self.owner).json()
        self.assertEqual(body["count"], 23)
        self.assertEqual(len(body["results"]), 20)
        self.assertIsNotNone(body["next"])
        self.assertEqual(len(self.get(self.owner, "?page=2").json()["results"]), 3)

    # --- không rò tiền mua / giá vốn ---------------------------------------------------------------------------
    def test_r10_manager_and_warehouse_staff_see_no_purchase_money(self):
        self.add_invoice(self.receipt)
        self.add_cost(self.batches)
        for user in (self.manager, self.warehouse_staff):
            resp = self.get(user)
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(find_cost_keys(body), set(), user.username)
            self.assertNotIn("purchase_amount", json.dumps(body), user.username)
            text = resp.content.decode()
            for sentinel in (RATE_SENTINEL, INVOICE_SENTINEL, MAIN_TOTAL, "1234570", "400000"):
                self.assertNotIn(sentinel, text, (user.username, sentinel))

    def test_r10_owner_sees_purchase_amount(self):
        row = self.get(self.owner).json()["results"][0]
        self.assertIn("purchase_amount", row)

    def test_r10_purchase_amount_is_registered_cost_key(self):
        from apps.common.cost_keys import COST_KEYS, redact_cost

        self.assertIn("purchase_amount", COST_KEYS)
        self.assertEqual(redact_cost({"purchase_amount": "1", "qty": "2"}), {"qty": "2"})
        self.assertIn("purchase_amount", self.get(self.owner).json()["results"][0])

    def test_r10_anonymous_and_forbidden_responses_have_no_data(self):
        self.assertNotIn(RATE_SENTINEL, client_for(self.courier).get(URL).content.decode())
        self.assertNotIn(RATE_SENTINEL, client_for(None).get(URL).content.decode())

    # --- lọc --------------------------------------------------------------------------------------------------
    def test_r10_filter_status(self):
        draft = self.make_draft()
        self.assertEqual(self.ids(self.owner, "?status=DRAFT"), {draft.pk})
        self.assertEqual(self.ids(self.owner, "?status=SUBMITTED"), {self.receipt.pk})
        self.assertEqual(self.ids(self.owner, "?status=DRAFT,SUBMITTED"), {draft.pk, self.receipt.pk})
        self.assertEqual(self.ids(self.owner, "?status=CANCELLED"), set())
        self.assertEqual(self.ids(self.owner, "?status="), {draft.pk, self.receipt.pk})

    def test_r10_filter_supplier(self):
        other = self.make_draft(supplier=self.other_supplier)
        self.assertEqual(self.ids(self.owner, f"?supplier={self.other_supplier.pk}"), {other.pk})
        self.assertEqual(self.ids(self.owner, f"?supplier={self.supplier.pk}"), {self.receipt.pk})

    def test_r10_filter_month_by_received_date(self):
        october = self.make_draft(received_date=datetime.date(2026, 10, 1))
        self.assertEqual(self.ids(self.owner, "?month=2026-10"), {october.pk})
        self.assertEqual(self.ids(self.owner, "?month=2026-09"), {self.receipt.pk})
        self.assertEqual(self.ids(self.owner, "?month=2026-08"), set())

    def test_r10_filter_month_december_rolls_over_year(self):
        december = self.make_draft(received_date=datetime.date(2026, 12, 31))
        self.assertEqual(self.ids(self.owner, "?month=2026-12"), {december.pk})
        self.assertEqual(self.ids(self.owner, "?month=2027-01"), set())

    def test_r10_filter_date_range(self):
        october = self.make_draft(received_date=datetime.date(2026, 10, 1))
        self.assertEqual(self.ids(self.owner, "?date_from=2026-10-01"), {october.pk})
        self.assertEqual(self.ids(self.owner, "?date_to=2026-09-28"), {self.receipt.pk})
        self.assertEqual(self.ids(self.owner, "?date_from=2026-09-28&date_to=2026-10-01"), {october.pk, self.receipt.pk})

    def test_r10_filter_has_invoice(self):
        draft = self.make_draft()
        self.add_invoice(self.receipt)
        self.assertEqual(self.ids(self.owner, "?has_invoice=1"), {self.receipt.pk})
        self.assertEqual(self.ids(self.owner, "?has_invoice=0"), {draft.pk})
        self.assertEqual(self.ids(self.owner, "?has_invoice=true"), {self.receipt.pk})
        self.assertEqual(self.ids(self.owner, "?has_invoice=false"), {draft.pk})

    def test_r10_two_invoices_do_not_duplicate_row(self):
        self.add_invoice(self.receipt)
        self.add_invoice(self.receipt, amount=Decimal("1"))
        resp = self.get(self.owner, "?has_invoice=1")
        self.assertEqual(resp.json()["count"], 1)

    def test_r10_filters_work_for_manager_without_money(self):
        draft = self.make_draft()
        self.assertEqual(self.ids(self.manager, "?status=DRAFT"), {draft.pk})

    def test_r10_bad_filters_400(self):
        for query in (
            "?status=FOO", "?status=DRAFT,FOO", "?supplier=abc", "?supplier=0", "?supplier=-1", "?supplier=1.5",
            "?supplier=99999999999999999999", "?month=2026-13", "?month=2026-1", "?month=1999-01",
            "?month=2026-10-01", "?month=%0A2026-10", "?month=２０２６-１０", "?has_invoice=maybe",
            "?date_from=2026-02-30", "?date_to=abc",
        ):
            resp = self.get(self.owner, query)
            self.assertEqual(resp.status_code, 400, (query, resp.status_code))
            self.assertEqual(resp.json()["code"], "INVALID_FILTER", query)

    def test_r10_bad_filter_message_does_not_echo_input(self):
        resp = self.get(self.owner, "?status=<script>0900000555")
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("0900000555", resp.content.decode())

    # --- hiệu năng ---------------------------------------------------------------------------------------------
    def _count_queries(self, user):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        client = client_for(user)
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(client.get(URL).status_code, 200)
        return len(ctx)

    def test_r10_list_has_no_n_plus_one(self):
        for user in (self.owner, self.manager):
            self._count_queries(user)  # làm nóng cache quyền/ContentType
            before = self._count_queries(user)
            for _ in range(8):
                receipt, batches = self.submit(
                    self.other_supplier, [(self.item_a, "4", RATE), (self.item_b, "2", RATE)], datetime.date(2026, 9, 29)
                )
                self.add_invoice(receipt)
            self.assertEqual(self._count_queries(user), before, user.username)
