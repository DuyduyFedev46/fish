"""
B3 — `GET /api/purchasing/suppliers/` (02b §3 B3, ED-21): số liệu tổng hợp của nhà cung cấp.

Quy tắc đã chốt (Duy 01/10, Q4 ở 02-stories): chỉ phiếu `SUBMITTED` (Đã ghi nhận) được tính cho cả ba số
`receipt_count`, `last_received_at`, `purchase_total`. Phiếu Nháp và Đã huỷ không tính.
`purchase_total` là tiền mua (giá vốn): chỉ người có `view_costprice` thấy (BR-MH-06, bất biến 1).
Mọi dữ liệu là giả.
"""
import datetime
import json
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for
from apps.purchasing.models import PurchaseReceipt, Supplier

from .api_base import RATE_SENTINEL, ReceiptsApiBase, find_cost_keys

SUPPLIERS_URL = "/api/purchasing/suppliers/"
MAIN_TOTAL = "1634570.00"  # phiếu của setUp: 10 kg x 123457 + 5 kg x 80000


def row_of(resp, supplier):
    return next(row for row in resp.json()["results"] if row["id"] == supplier.pk)


class SupplierAggregateTests(ReceiptsApiBase):
    def get(self, user, path=""):
        return client_for(user).get(f"{SUPPLIERS_URL}{path}")

    def at(self, receipt, moment):
        """`created_at` là auto_now_add: ghi đè để test kiểm "lần gần nhất" chắc chắn."""
        PurchaseReceipt.objects.filter(pk=receipt.pk).update(created_at=moment)

    def aware(self, *args):
        return timezone.make_aware(datetime.datetime(*args))

    # --- ED-21-AC1: số liệu đúng --------------------------------------------------------------------------
    def test_supplier_aggregates_count_only_submitted_receipts(self):
        second, _ = self.submit(
            self.supplier, [(self.item_a, "2", Decimal("100000"))], datetime.date(2026, 9, 29)
        )
        self.at(self.receipt, self.aware(2026, 9, 28, 8, 0))
        self.at(second, self.aware(2026, 9, 29, 5, 40))
        draft = self.make_draft()  # mới nhất nhưng là Nháp
        self.at(draft, self.aware(2026, 10, 1, 9, 0))
        cancelled, _ = self.submit(
            self.supplier, [(self.item_b, "9", Decimal("999000"))], datetime.date(2026, 9, 30)
        )
        PurchaseReceipt.objects.filter(pk=cancelled.pk).update(
            status=PurchaseReceipt.Status.CANCELLED, created_at=self.aware(2026, 9, 30, 9, 0)
        )

        row = row_of(self.get(self.owner), self.supplier)

        self.assertEqual(row["receipt_count"], 2)
        self.assertEqual(row["purchase_total"], "1834570.00")  # 1634570 + 2 kg x 100000
        self.assertEqual(row["last_received_at"], "2026-09-29T05:40:00+07:00")

    def test_supplier_purchase_total_matches_receipt_list_rounding(self):
        # 0,333 kg x 100,01 = 33,30333 -> mỗi dòng làm tròn 2 chữ số rồi cộng, như `purchase_amount` của phiếu.
        receipt, _ = self.submit(
            self.other_supplier,
            [(self.item_a, "0.333", Decimal("100.01")), (self.item_b, "0.333", Decimal("100.01"))],
            datetime.date(2026, 9, 29),
        )
        row = row_of(self.get(self.owner), self.other_supplier)
        listed = client_for(self.owner).get(f"/api/purchasing/receipts/{receipt.pk}/").json()
        self.assertEqual(row["purchase_total"], listed["purchase_amount"])
        self.assertEqual(row["purchase_total"], "66.60")

    def test_supplier_aggregates_are_per_supplier_and_many_lines(self):
        self.submit(
            self.other_supplier,
            [(self.item_a, "1", Decimal("10")), (self.item_b, "2", Decimal("20")), (self.item_a, "3", Decimal("30"))],
            datetime.date(2026, 9, 29),
        )
        resp = self.get(self.owner)
        self.assertEqual(row_of(resp, self.supplier)["purchase_total"], MAIN_TOTAL)
        self.assertEqual(row_of(resp, self.supplier)["receipt_count"], 1)
        other = row_of(resp, self.other_supplier)
        self.assertEqual(other["purchase_total"], "140.00")
        self.assertEqual(other["receipt_count"], 1)

    def test_supplier_aggregates_money_is_string_decimal(self):
        value = row_of(self.get(self.owner), self.supplier)["purchase_total"]
        self.assertIsInstance(value, str)
        self.assertEqual(Decimal(value), Decimal(MAIN_TOTAL))

    # --- ED-21-AC3: chưa có phiếu -------------------------------------------------------------------------
    def test_supplier_without_receipts_has_zero_and_null(self):
        row = row_of(self.get(self.owner), self.other_supplier)
        self.assertEqual(row["receipt_count"], 0)
        self.assertIsNone(row["last_received_at"])
        self.assertEqual(row["purchase_total"], "0.00")

    def test_supplier_with_only_draft_and_cancelled_counts_zero(self):
        self.make_draft(supplier=self.other_supplier)
        row = row_of(self.get(self.owner), self.other_supplier)
        self.assertEqual((row["receipt_count"], row["last_received_at"], row["purchase_total"]), (0, None, "0.00"))

    def test_supplier_detail_has_same_aggregates_and_labels(self):
        resp = client_for(self.owner).get(f"{SUPPLIERS_URL}{self.supplier.pk}/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["receipt_count"], 1)
        self.assertEqual(body["purchase_total"], MAIN_TOTAL)
        self.assertEqual(body["supplier_type"], "INDIVIDUAL")
        self.assertEqual(body["supplier_type_label"], "Cá nhân")
        self.assertEqual(
            set(body),
            {"id", "name", "supplier_type", "supplier_type_label", "phone", "note", "is_active",
             "receipt_count", "last_received_at", "purchase_total"},
        )

    def test_supplier_company_type_label(self):
        company = Supplier.objects.create(name="Công ty Thử", supplier_type="COMPANY")
        body = client_for(self.owner).get(f"{SUPPLIERS_URL}{company.pk}/").json()
        self.assertEqual(body["supplier_type_label"], "Doanh nghiệp")

    # --- ED-21-AC2: không rò tiền mua ---------------------------------------------------------------------
    def test_supplier_purchase_total_only_for_view_costprice(self):
        owner_list = self.get(self.owner)
        self.assertEqual(find_cost_keys(owner_list.json()), {"purchase_total"})
        for user in (self.manager, self.warehouse_staff):
            for path in ("", f"{self.supplier.pk}/"):
                resp = client_for(user).get(f"{SUPPLIERS_URL}{path}")
                self.assertEqual(resp.status_code, 200, user.username)
                text = json.dumps(resp.json())
                self.assertNotIn("purchase_total", text, user.username)
                self.assertEqual(find_cost_keys(resp.json()), set(), user.username)
                # Số mồi: không tổng nào, không đơn giá nào lọt ra.
                for sentinel in (RATE_SENTINEL, "1634570", "1234570", "400000"):
                    self.assertNotIn(sentinel, text, f"{user.username} {sentinel}")

    def test_supplier_purchase_total_is_in_cost_keys(self):
        self.assertIn("purchase_total", COST_KEYS)

    def test_supplier_write_responses_do_not_leak_purchase_total(self):
        resp = client_for(self.manager).patch(
            f"{SUPPLIERS_URL}{self.supplier.pk}/", {"note": "ghi chú thử"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("purchase_total", resp.json())
        self.assertEqual(resp.json()["receipt_count"], 1)
        resp = client_for(self.manager).post(SUPPLIERS_URL, {"name": "Vựa mới thử"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertNotIn("purchase_total", resp.json())

    def test_supplier_write_responses_for_owner_carry_real_aggregates(self):
        resp = client_for(self.owner).patch(
            f"{SUPPLIERS_URL}{self.supplier.pk}/", {"note": "ghi chú thử"}, format="json"
        )
        self.assertEqual(resp.json()["purchase_total"], MAIN_TOTAL)
        resp = client_for(self.owner).post(SUPPLIERS_URL, {"name": "Vựa mới thử"}, format="json")
        self.assertEqual(
            (resp.json()["receipt_count"], resp.json()["purchase_total"], resp.json()["last_received_at"]),
            (0, "0.00", None),
        )

    # --- ED-21-AC5: không N+1 ------------------------------------------------------------------------------
    def count_list_queries(self):
        client = client_for(self.owner)
        client.get(SUPPLIERS_URL)  # làm nóng bộ nhớ đệm quyền của user, để các lần đo sau so sánh được
        with CaptureQueriesContext(connection) as ctx:
            resp = client.get(SUPPLIERS_URL)
        self.assertEqual(resp.status_code, 200)
        return len(ctx), resp.json()["count"]

    def test_supplier_list_query_count_does_not_grow_with_suppliers(self):
        before, count_before = self.count_list_queries()
        for index in range(20):
            supplier = Supplier.objects.create(name=f"Đầu mối thử {index:02d}")
            self.submit(supplier, [(self.item_a, "1", Decimal("1000")), (self.item_b, "2", Decimal("2000"))],
                        datetime.date(2026, 9, 29))
        after, count_after = self.count_list_queries()
        self.assertEqual(count_after, count_before + 20)
        self.assertEqual(after, before)

    def test_supplier_list_with_50_suppliers_is_one_page_with_constant_queries(self):
        for index in range(48):
            Supplier.objects.create(name=f"Đầu mối {index:02d}")
        _, count = self.count_list_queries()
        self.assertEqual(count, 50)
        self.assertLessEqual(self.count_list_queries()[0], 6)  # xác thực, quyền, đếm, danh sách, tổng tiền
