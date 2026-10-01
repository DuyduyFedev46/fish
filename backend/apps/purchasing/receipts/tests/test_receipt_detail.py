"""
R10 — `GET /api/purchasing/receipts/{id}/` (màn W2b, ED-20-AC5/AC6): chi tiết phiếu nhập.
Dòng nhập kèm lô, hoá đơn mua, chi phí phụ phân bổ vào lô của phiếu. Giá mua, thành tiền, chi phí, giá vốn chỉ cho
người có `view_costprice` (BR-MH-06, bất biến 1).
"""
import datetime
import json
from decimal import Decimal

from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine

from .api_base import (
    COST_SENTINEL, INVOICE_SENTINEL, RATE, RATE_SENTINEL, ReceiptsApiBase, find_cost_keys,
)


class ReceiptDetailTests(ReceiptsApiBase):
    def detail(self, user, receipt=None):
        resp = self.get(user, f"{(receipt or self.receipt).pk}/")
        self.assertEqual(resp.status_code, 200)
        return resp.json()

    def test_r10_detail_owner_header_and_lines(self):
        body = self.detail(self.owner)
        self.assertEqual(body["code"], f"PR-{self.receipt.pk}")
        self.assertEqual(body["supplier_name"], "Đầu mối A")
        self.assertEqual(body["warehouse_name"], "Kho chính")
        self.assertEqual(body["created_by_name"], "Tâm Thử")
        self.assertEqual(body["status_label"], "Đã ghi nhận")
        self.assertEqual(body["line_count"], 2)
        self.assertEqual(body["total_qty"], "15.000")
        self.assertEqual(body["purchase_amount"], "1634570.00")
        self.assertIn("created_at", body)
        self.assertIn("note", body)
        first, second = body["lines"]
        self.assertEqual(first["item_code"], "CA01")
        self.assertEqual(first["item_name"], "Cá thu")
        self.assertEqual(first["batch"], self.batches[0].pk)
        self.assertEqual(first["batch_code"], self.batches[0].batch_id)
        self.assertEqual(first["batch_status"], "DRAFT")
        self.assertEqual(first["expiry_date"], self.batches[0].expiry_date.isoformat())
        self.assertEqual(first["shelf_life_days"], None)
        self.assertEqual(first["qty"], "10.000")
        self.assertEqual(first["rate"], "123457.00")
        self.assertEqual(first["purchase_amount"], "1234570.00")
        self.assertEqual(first["landed_unit_cost"], "123457.00")
        self.assertEqual(second["item_name"], "Tôm sú")
        self.assertEqual(second["purchase_amount"], "400000.00")

    def test_r10_detail_draft_line_has_no_batch(self):
        draft = self.make_draft()
        line = self.detail(self.owner, draft)["lines"][0]
        self.assertIsNone(line["batch"])
        self.assertIsNone(line["batch_code"])
        self.assertIsNone(line["batch_status"])
        self.assertIsNone(line["expiry_date"])
        self.assertIsNone(line["landed_unit_cost"])

    def test_r10_detail_invoices_and_costs_for_owner(self):
        invoice = self.add_invoice(self.receipt)
        cost = self.add_cost(self.batches)
        body = self.detail(self.owner)
        self.assertEqual(body["invoice"], {"id": invoice.pk})
        self.assertEqual(len(body["invoices"]), 1)
        got = body["invoices"][0]
        self.assertEqual(got["id"], invoice.pk)
        self.assertEqual(got["code"], f"#{invoice.pk}")
        self.assertEqual(got["is_paid"], True)
        self.assertEqual(got["amount"], "555551.00")
        self.assertEqual(got["invoice_date"], "2026-09-28")
        self.assertEqual(len(body["costs"]), 1)
        got_cost = body["costs"][0]
        self.assertEqual(got_cost["id"], cost.pk)
        self.assertEqual(got_cost["cost_type"], "ICE")
        self.assertEqual(got_cost["cost_type_label"], "Đá")
        self.assertEqual(got_cost["allocation_method_label"], "Theo số kg")
        self.assertEqual(got_cost["amount"], "987654.00")
        self.assertEqual(got_cost["allocated_amount"], "987654.00")
        self.assertEqual(got_cost["batch_count"], 2)
        self.assertEqual(body["allocated_amount"], "987654.00")
        # Giá vốn của lô đã gồm chi phí phụ: 987654 / 15 kg cộng vào đơn giá.
        self.assertNotEqual(body["lines"][0]["landed_unit_cost"], "123457.00")

    def test_r10_detail_cost_shared_with_other_receipt_counts_only_this_receipt(self):
        other, other_batches = self.submit(self.other_supplier, [(self.item_a, "10", RATE)], datetime.date(2026, 9, 29))
        self.add_cost([self.batches[0], other_batches[0]], amount=Decimal("1000"))
        mine = self.detail(self.owner)["costs"][0]
        theirs = self.detail(self.owner, other)["costs"][0]
        self.assertEqual(mine["amount"], "1000.00")
        self.assertEqual(mine["allocated_amount"], "500.00")
        self.assertEqual(theirs["allocated_amount"], "500.00")

    def test_r10_detail_empty_invoices_and_costs(self):
        body = self.detail(self.owner)
        self.assertIsNone(body["invoice"])
        self.assertEqual(body["invoices"], [])
        self.assertEqual(body["costs"], [])
        self.assertEqual(body["allocated_amount"], "0.00")

    # --- không rò -----------------------------------------------------------------------------------------------
    def test_r10_manager_and_warehouse_staff_detail_has_no_purchase_money(self):
        self.add_invoice(self.receipt)
        self.add_cost(self.batches)
        for user in (self.manager, self.warehouse_staff):
            resp = self.get(user, f"{self.receipt.pk}/")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            # `amount` của hoá đơn KHÔNG nằm trong COST_KEYS (D-3), nên quét khoá giá vốn vẫn phải rỗng cho cả hai.
            self.assertEqual(find_cost_keys(body), set(), user.username)
            text = resp.content.decode()
            for sentinel in (RATE_SENTINEL, COST_SENTINEL, "1234570", "1634570", "400000"):
                self.assertNotIn(sentinel, text, (user.username, sentinel))
            for key in ("purchase_amount", "costs", "allocated_amount", "landed_unit_cost", "rate"):
                self.assertNotIn(f'"{key}"', json.dumps(body), (user.username, key))
            # Phần không phải tiền vẫn có đủ cho màn W2b.
            self.assertEqual(body["lines"][0]["batch_code"], self.batches[0].batch_id)
            self.assertEqual(body["invoice"], {"id": self.receipt.invoices.first().pk})
            if user == self.manager:
                self.assertEqual(body["invoices"][0]["code"], f"#{body['invoices'][0]['id']}")
                self.assertEqual(body["invoices"][0]["is_paid"], True)
            else:
                self.assertNotIn("invoices", body)  # L1: kho chỉ còn `invoice: {"id"}`

    def test_r10_d3_manager_sees_invoice_amount_warehouse_staff_does_not(self):
        """D-3 (02b §6 Q3): Quản lý thấy tiền hoá đơn mua (quyền view_purchaseinvoice); nhân viên kho không."""
        from apps.common.cost_keys import COST_KEYS

        self.assertNotIn("amount", COST_KEYS)  # ngoại lệ D-3: `amount` hoá đơn không phải khoá giá vốn
        self.add_invoice(self.receipt)
        for user in (self.owner, self.manager):
            invoice = self.detail(user)["invoices"][0]
            self.assertEqual(invoice["amount"], "555551.00", user.username)
        warehouse_body = self.detail(self.warehouse_staff)
        self.assertNotIn("invoices", warehouse_body)
        self.assertEqual(warehouse_body["invoice"], {"id": self.receipt.invoices.first().pk})
        self.assertNotIn(INVOICE_SENTINEL, json.dumps(warehouse_body))

    def test_r10_l1_invoices_list_needs_view_purchaseinvoice(self):
        """L1: người thiếu `view_purchaseinvoice` (kho) không nhận `invoices[]`, kể cả khi phiếu không có hoá đơn."""
        self.assertNotIn("invoices", self.detail(self.warehouse_staff))
        self.assertEqual(self.detail(self.manager)["invoices"], [])
        self.assertEqual(self.detail(self.owner)["invoices"], [])

    def test_r10_l2_lines_are_ordered_by_id(self):
        receipt = self.make_draft()
        receipt.lines.all().delete()
        for item, qty in ((self.item_b, "1"), (self.item_a, "2"), (self.item_b, "3")):
            PurchaseReceiptLine.objects.create(receipt=receipt, item=item, qty=Decimal(qty), rate=RATE)
        body = self.detail(self.owner, receipt)
        ids = [line["id"] for line in body["lines"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual([line["item_code"] for line in body["lines"]], ["TOM01", "CA01", "TOM01"])
        self.assertEqual(body["items_summary"], "Tôm sú, Cá thu")

    def test_r10_l3_costs_computed_once_per_receipt(self):
        from django.test import RequestFactory

        from apps.purchasing.receipts.serializers import PurchaseReceiptDetailSerializer

        self.add_cost(self.batches)
        request = RequestFactory().get("/")
        request.user = self.owner
        receipt = PurchaseReceipt.objects.prefetch_related("lines__batch__cost_allocations__purchase_cost").get(
            pk=self.receipt.pk
        )
        serializer = PurchaseReceiptDetailSerializer(receipt, context={"request": request})
        data = serializer.data  # dựng `costs` và `allocated_amount`
        self.assertEqual(data["allocated_amount"], "987654.00")
        self.assertIs(serializer._costs(receipt), serializer._costs(receipt))
        with self.assertNumQueries(0):
            serializer._costs(receipt)

    def test_r10_d3_manager_still_cannot_see_cost_fields_beside_invoice_amount(self):
        self.add_invoice(self.receipt)
        self.add_cost(self.batches)
        body = self.detail(self.manager)
        for key in ("purchase_amount", "costs", "allocated_amount"):
            self.assertNotIn(key, body)
        for line in body["lines"]:
            for key in ("rate", "purchase_amount", "landed_unit_cost"):
                self.assertNotIn(key, line)

    def test_r10_receive_batches_response_has_no_rate_for_warehouse_staff(self):
        # Phản hồi `receive-batches` của người kho cũng không có giá mua (ED-20-AC5).
        resp = self.client_for_post(self.warehouse_staff)
        self.assertEqual(resp.status_code, 201)
        self.assertNotIn(RATE_SENTINEL, resp.content.decode())

    def client_for_post(self, user):
        from apps.common.tests.fixtures import client_for
        return client_for(user).post(
            "/api/purchasing/receipts/receive-batches/",
            {"supplier": self.supplier.pk, "warehouse": self.warehouse.pk, "received_date": "2026-09-30",
             "lines": [{"item_code": "CA01", "qty": "2", "rate": RATE_SENTINEL}]}, format="json",
        )

    def test_r10_detail_has_no_n_plus_one_on_lines(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from apps.common.tests.fixtures import client_for

        def count(receipt):
            client = client_for(self.owner)
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(client.get(f"/api/purchasing/receipts/{receipt.pk}/").status_code, 200)
            return len(ctx)

        count(self.receipt)  # làm nóng
        small, small_batches = self.submit(self.supplier, [(self.item_a, "1", RATE)], datetime.date(2026, 9, 30))
        self.add_cost(small_batches, amount=Decimal("10"))
        self.add_invoice(small)
        big, big_batches = self.submit(
            self.supplier, [(self.item_a, "1", RATE), (self.item_b, "2", RATE)] * 4, datetime.date(2026, 9, 30)
        )
        self.add_cost(big_batches, amount=Decimal("10"))
        self.add_cost(big_batches[:3], amount=Decimal("20"))
        self.add_invoice(big)
        self.assertEqual(count(big), count(small))

    def test_r10_unknown_receipt_is_404(self):
        self.assertEqual(self.get(self.owner, "999999/").status_code, 404)
