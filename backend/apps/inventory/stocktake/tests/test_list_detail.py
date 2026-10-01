"""R8 — danh sách và chi tiết phiếu kiểm kê (02b §3 B1 "Body chi tiết/danh sách")."""
import datetime
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.inventory.models import StockReconciliation

from .base import URL, StocktakeApiBase, line

LIST_KEYS = {
    "id", "code", "count_date", "status", "status_label", "note", "created_by", "approved_by", "approved_at",
    "updated_at", "updated_by_name", "warehouse_names", "line_count", "short_count", "over_count", "match_count",
    "short_qty", "over_qty", "net_difference", "available_actions", "approve_blocked_reason",
}
LINE_KEYS = {
    "id", "batch", "batch_code", "item_name", "warehouse_name", "system_qty", "counted_qty", "difference_qty",
    "reason",
}


class ListDetailTests(StocktakeApiBase):
    def setUp(self):
        super().setUp()
        self.batch3 = self.make_batch("10", item=self.item, warehouse=self.wh)

    def two_warehouse_rec(self):
        return self.make_draft(
            self.warehouse_staff,
            [
                line(self.batch, "48.500"),            # -1.500, Kho chính
                line(self.batch2, "30.400", "Ghi dư"),  # +0.400, Kho lạnh
                line(self.batch3, "10"),               # 0, Kho chính
            ],
        )

    def test_r8_list_warehouse_names_come_from_lines_batches(self):
        self.two_warehouse_rec()
        self.make_draft(self.warehouse_staff, [line(self.batch2, "29")])
        results = self.api(self.warehouse_staff).get(URL).json()["results"]
        names = {tuple(row["warehouse_names"]) for row in results}
        self.assertEqual(names, {("Kho chính", "Kho lạnh"), ("Kho lạnh",)})

    def test_r8_empty_draft_has_no_warehouse_names(self):
        self.create_via_api(self.warehouse_staff)
        row = self.api(self.warehouse_staff).get(URL).json()["results"][0]
        self.assertEqual(row["warehouse_names"], [])
        self.assertEqual(row["line_count"], 0)

    def test_r8_list_row_contract_and_stats(self):
        rec = self.two_warehouse_rec()
        resp = self.api(self.warehouse_staff).get(URL)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(set(body), {"count", "next", "previous", "results"})
        row = body["results"][0]
        self.assertEqual(set(row), LIST_KEYS)
        self.assertNotIn("lines", row)
        self.assertEqual(row["code"], f"KK-{rec['id']}")
        self.assertEqual(row["status_label"], "Chờ duyệt")
        self.assertEqual(
            (row["line_count"], row["short_count"], row["over_count"], row["match_count"]), (3, 1, 1, 1)
        )
        self.assertEqual((row["short_qty"], row["over_qty"], row["net_difference"]), ("1.500", "0.400", "-1.100"))
        self.assertEqual(row["created_by"], {"id": self.warehouse_staff.pk, "display_name": "Kho Thử"})
        self.assertIsNone(row["approved_by"])
        self.assertEqual(row["updated_by_name"], "Kho Thử")

    def test_r8_detail_contract_lines_with_difference(self):
        rec = self.two_warehouse_rec()
        body = self.api(self.warehouse_staff).get(f"{URL}{rec['id']}/").json()
        self.assertEqual(set(body), LIST_KEYS | {"lines"})
        self.assertEqual(len(body["lines"]), 3)
        for row in body["lines"]:
            self.assertEqual(set(row), LINE_KEYS)
        first = next(row for row in body["lines"] if row["batch"] == self.batch.pk)
        self.assertEqual(first["batch_code"], self.batch.batch_id)
        self.assertEqual(first["item_name"], "Cá thu")
        self.assertEqual(first["warehouse_name"], "Kho chính")
        self.assertEqual(first["system_qty"], "50.000")
        self.assertEqual(first["counted_qty"], "48.500")
        self.assertEqual(first["difference_qty"], "-1.500")

    def test_r8_user_without_display_name_falls_back_to_username(self):
        rec = self.make_draft(self.owner)
        body = self.api(self.owner).get(f"{URL}{rec['id']}/").json()
        self.assertEqual(body["created_by"]["display_name"], self.owner.username)

    def test_r8_approved_reconciliation_shows_approver_and_no_actions(self):
        rec = self.make_draft(self.warehouse_staff)
        self.api(self.owner).post(f"{URL}{rec['id']}/approve/")
        body = self.api(self.owner).get(f"{URL}{rec['id']}/").json()
        self.assertEqual(body["status"], "APPROVED")
        self.assertEqual(body["status_label"], "Đã duyệt")
        self.assertEqual(body["approved_by"]["id"], self.owner.pk)
        self.assertIsNotNone(body["approved_at"])
        self.assertEqual(body["available_actions"], [])
        self.assertIsNone(body["approve_blocked_reason"])
        # Sau khi duyệt, số liệu chênh lệch lấy theo tồn lúc duyệt.
        self.assertEqual(body["net_difference"], "-1.500")

    def test_r8_available_actions_by_user(self):
        rec = self.make_draft(self.warehouse_staff)
        url = f"{URL}{rec['id']}/"
        as_staff = self.api(self.warehouse_staff).get(url).json()
        self.assertEqual(as_staff["available_actions"], ["edit_lines"])  # không có quyền duyệt
        self.assertIsNone(as_staff["approve_blocked_reason"])
        as_owner = self.api(self.owner).get(url).json()
        self.assertEqual(as_owner["available_actions"], ["edit_lines", "approve"])
        self.assertIsNone(as_owner["approve_blocked_reason"])

    def test_r8_creator_with_approve_permission_sees_blocked_reason(self):
        rec = self.make_draft(self.manager)
        body = self.api(self.manager).get(f"{URL}{rec['id']}/").json()
        self.assertEqual(body["available_actions"], ["edit_lines"])
        self.assertEqual(body["approve_blocked_reason"]["code"], "BR-KK-02")
        self.assertTrue(body["approve_blocked_reason"]["label"])

    def test_r8_editor_sees_blocked_reason_br_kk_08_other_user_does_not(self):
        rec = self.make_draft(self.warehouse_staff)
        self.replace_via_api(self.manager, rec, [line(self.batch, "49")])
        url = f"{URL}{rec['id']}/"
        as_editor = self.api(self.manager).get(url).json()
        self.assertNotIn("approve", as_editor["available_actions"])
        self.assertEqual(as_editor["approve_blocked_reason"]["code"], "BR-KK-08")
        as_other = self.api(self.owner).get(url).json()
        self.assertIn("approve", as_other["available_actions"])
        self.assertIsNone(as_other["approve_blocked_reason"])
        # Cũng đúng trong danh sách.
        row = next(r for r in self.api(self.manager).get(URL).json()["results"] if r["id"] == rec["id"])
        self.assertEqual(row["approve_blocked_reason"]["code"], "BR-KK-08")

    def test_r8_delivery_and_customer_service_get_403_and_anonymous_401(self):
        rec = self.make_draft()
        for user in (self.delivery_staff, self.customer_service):
            self.assertEqual(self.api(user).get(URL).status_code, 403)
            self.assertEqual(self.api(user).get(f"{URL}{rec['id']}/").status_code, 403)
        self.assertEqual(self.api(None).get(URL).status_code, 401)

    def test_r8_no_cost_leak_in_list_and_detail_for_all_readers(self):
        rec = self.two_warehouse_rec()
        for user in (self.warehouse_staff, self.manager, self.owner):
            self.assertNoCostLeak(self.api(user).get(URL))
            self.assertNoCostLeak(self.api(user).get(f"{URL}{rec['id']}/"))

    def test_r8_filters_status_warehouse_dates(self):
        old = self.make_draft(self.warehouse_staff, [line(self.batch, "49")])
        StockReconciliation.objects.filter(pk=old["id"]).update(count_date=datetime.date(2026, 8, 1))
        cold = self.make_draft(self.warehouse_staff, [line(self.batch2, "29")])
        approved = self.make_draft(self.warehouse_staff, [line(self.batch3, "9")])
        self.api(self.owner).post(f"{URL}{approved['id']}/approve/")
        client = self.api(self.warehouse_staff)

        def ids(query):
            resp = client.get(URL + query)
            self.assertEqual(resp.status_code, 200, (query, resp.content))
            return {row["id"] for row in resp.json()["results"]}

        self.assertEqual(ids("?status=APPROVED"), {approved["id"]})
        self.assertEqual(ids("?status=DRAFT"), {old["id"], cold["id"]})
        self.assertEqual(ids("?status=DRAFT,APPROVED"), {old["id"], cold["id"], approved["id"]})
        self.assertEqual(ids(f"?warehouse={self.wh2.pk}"), {cold["id"]})
        self.assertEqual(ids(f"?warehouse={self.wh.pk}"), {old["id"], approved["id"]})
        self.assertEqual(ids("?date_to=2026-08-31"), {old["id"]})
        self.assertEqual(ids("?date_from=2026-09-01"), {cold["id"], approved["id"]})
        self.assertEqual(ids("?status="), {old["id"], cold["id"], approved["id"]})
        self.assertEqual(ids("?warehouse=999999"), set())

    def test_r8_warehouse_filter_does_not_duplicate_rows(self):
        self.two_warehouse_rec()  # 2 dòng cùng Kho chính
        body = self.api(self.warehouse_staff).get(f"{URL}?warehouse={self.wh.pk}").json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(len(body["results"]), 1)

    def test_r8_bad_filters_are_400_invalid_filter_without_echo(self):
        client = self.api(self.warehouse_staff)
        for query in (
            "?status=NOPE", "?warehouse=abc", "?warehouse=-1", "?warehouse=" + "9" * 5000,
            "?date_from=hôm-nay", "?date_to=2026-13-40",
        ):
            resp = client.get(URL + query)
            self.assertEqual(resp.status_code, 400, (query[:30], resp.content[:200]))
            self.assertEqual(resp.json()["code"], "INVALID_FILTER")
            self.assertNotIn("NOPE", resp.json()["detail"])

    def test_bad_filter_without_permission_is_403_not_400(self):
        self.assertEqual(self.api(self.delivery_staff).get(URL + "?status=NOPE").status_code, 403)

    def test_r8_pagination_is_standard_20_per_page(self):
        for _ in range(21):
            self.create_via_api(self.warehouse_staff)
        body = self.api(self.warehouse_staff).get(URL).json()
        self.assertEqual(body["count"], 21)
        self.assertEqual(len(body["results"]), 20)
        self.assertEqual(len(self.api(self.warehouse_staff).get(URL + "?page=2").json()["results"]), 1)

    def test_r8_list_has_no_n_plus_one(self):
        client = self.api(self.manager)

        def count_queries():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(client.get(URL).status_code, 200)
            return len(ctx)

        self.two_warehouse_rec()
        count_queries()  # lần đầu nạp quyền của user vào bộ nhớ đệm
        one = count_queries()
        for _ in range(6):
            self.two_warehouse_rec()
        self.assertEqual(count_queries(), one)

    def test_r8_detail_query_count_does_not_grow_with_lines(self):
        batches = [self.make_batch("5") for _ in range(8)]
        small = self.make_draft(self.warehouse_staff, [line(self.batch, "40")])
        big = self.make_draft(self.warehouse_staff, [line(b, "4") for b in batches])
        client = self.api(self.manager)
        client.get(f"{URL}{small['id']}/")  # lần đầu nạp quyền của user vào bộ nhớ đệm
        counts = []
        for rec in (small, big):
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(client.get(f"{URL}{rec['id']}/").status_code, 200)
            counts.append(len(ctx))
        self.assertEqual(counts[0], counts[1])

    def test_legacy_reconciliation_made_without_service_still_renders(self):
        """Phiếu tạo thẳng bằng ORM (không có AuditLog): updated_by_name rơi về người tạo."""
        rec = StockReconciliation.objects.create(
            count_date=self.today, created_by=self.warehouse_staff,
        )
        rec.lines.create(
            batch=self.batch, system_qty=Decimal("50"), counted_qty=Decimal("49"), difference_qty=Decimal("-1"),
        )
        body = self.api(self.manager).get(f"{URL}{rec.pk}/").json()
        self.assertEqual(body["updated_by_name"], "Kho Thử")
        self.assertEqual(body["line_count"], 1)
