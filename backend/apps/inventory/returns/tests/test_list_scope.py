"""R9 (02b §3.8): danh sách và chi tiết hàng hoàn. Phạm vi dòng của delivery_staff (BR-PQ-12), không rò giá vốn
(bất biến 1), không rò dữ liệu cá nhân (bất biến 9), không N+1. Dữ liệu giả."""
import datetime

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.common.tests.fixtures import client_for
from apps.inventory.models import ReturnToStock

from .base import (
    NOTE_WITH_PHONE, PHONE_SENTINEL, RATE_SENTINEL, URL, ReturnsApiBase, find_cost_keys,
)

EXPECTED_KEYS = {
    "id", "code", "delivery_note", "delivery_note_code", "order_code", "batch", "batch_code", "item_name", "qty",
    "left_warehouse_at", "returned_at", "outside_minutes", "decision", "decision_label", "status", "status_label",
    "created_by", "created_by_name", "approved_by", "approved_by_name", "created_at", "note", "available_actions",
}


class ReturnListScopeTests(ReturnsApiBase):
    def setUp(self):
        super().setUp()
        self.mine = self.make_return(self.note, "2", self.courier, NOTE_WITH_PHONE)
        self.theirs = self.make_return(self.other_note, "3", self.other_courier, "Khách từ chối")

    def ids(self, user, query=""):
        resp = client_for(user).get(f"{URL}{query}")
        self.assertEqual(resp.status_code, 200, resp.content)
        return {row["id"] for row in resp.json()["results"]}

    def test_r9_full_scope_groups_see_all(self):
        for user in (self.owner, self.manager, self.warehouse_staff):
            self.assertEqual(self.ids(user), {self.mine.pk, self.theirs.pk}, user.username)

    def test_r9_delivery_staff_sees_only_own_note_returns(self):
        self.assertEqual(self.ids(self.courier), {self.mine.pk})
        self.assertEqual(self.ids(self.other_courier), {self.theirs.pk})

    def test_r9_delivery_staff_does_not_see_returns_without_note(self):
        orphan = ReturnToStock.objects.create(batch=self.batch, qty=1, created_by=self.warehouse_staff)
        self.assertNotIn(orphan.pk, self.ids(self.courier))
        self.assertIn(orphan.pk, self.ids(self.warehouse_staff))
        self.assertEqual(client_for(self.courier).get(f"{URL}{orphan.pk}/").status_code, 404)

    def test_r2_return_other_courier_detail_404(self):
        self.assertEqual(client_for(self.courier).get(f"{URL}{self.mine.pk}/").status_code, 200)
        resp = client_for(self.courier).get(f"{URL}{self.theirs.pk}/")
        self.assertEqual(resp.status_code, 404, resp.content)
        self.assertNotIn("Khách từ chối", resp.content.decode())

    def test_r2_other_courier_cannot_approve_or_patch_even_with_perm_check(self):
        for method, path, body in (
            ("post", f"{URL}{self.theirs.pk}/approve/", {"decision": "RESTOCK"}),
            ("patch", f"{URL}{self.theirs.pk}/", {"note": "x"}),
        ):
            resp = getattr(client_for(self.courier), method)(path, body, format="json")
            self.assertIn(resp.status_code, (403, 404), (method, resp.status_code))
        self.theirs.refresh_from_db()
        self.assertEqual((self.theirs.status, self.theirs.note), ("DRAFT", "Khách từ chối"))

    def test_r9_customer_service_403_and_unauthenticated_401(self):
        self.assertEqual(client_for(self.customer_service).get(URL).status_code, 403)
        self.assertEqual(client_for(self.customer_service).get(f"{URL}{self.mine.pk}/").status_code, 403)
        self.assertEqual(client_for(self.no_group).get(URL).status_code, 403)
        self.assertEqual(client_for(None).get(URL).status_code, 401)
        self.assertEqual(client_for(None).get(f"{URL}{self.mine.pk}/").status_code, 401)

    def test_r9_row_fields_are_explicit_and_have_no_cost(self):
        resp = client_for(self.warehouse_staff).get(f"{URL}{self.mine.pk}/")
        self.assertEqual(set(resp.json()), EXPECTED_KEYS)
        for user in (self.warehouse_staff, self.manager, self.courier, self.owner):
            for path in (URL, f"{URL}{self.mine.pk}/"):
                text = client_for(user).get(path).content.decode()
                self.assertNotIn(RATE_SENTINEL, text, (user.username, path))
        for user in (self.warehouse_staff, self.manager):
            body = client_for(user).get(URL).json()
            self.assertEqual(find_cost_keys(body), set(), user.username)

    def test_r9_display_fields_in_list(self):
        row = next(r for r in client_for(self.owner).get(URL).json()["results"] if r["id"] == self.mine.pk)
        self.assertEqual(row["code"], f"RT-{self.mine.pk}")
        self.assertEqual(row["order_code"], "SO-R9-A")
        self.assertEqual(row["delivery_note_code"], self.note.code)
        self.assertEqual(row["decision_label"], "Chờ quyết định")
        self.assertEqual(row["status_label"], "Chờ duyệt")
        self.assertEqual(row["qty"], "2.000")

    def test_r9_outside_minutes_is_difference_of_times(self):
        left = timezone.now() - datetime.timedelta(minutes=95)
        ReturnToStock.objects.filter(pk=self.mine.pk).update(left_warehouse_at=left, returned_at=left + datetime.timedelta(minutes=95))
        body = client_for(self.owner).get(f"{URL}{self.mine.pk}/").json()
        self.assertEqual(body["outside_minutes"], 95)
        self.assertIsNone(client_for(self.owner).get(f"{URL}{self.theirs.pk}/").json()["outside_minutes"])

    def test_r9_decision_label_for_write_off(self):
        ReturnToStock.objects.filter(pk=self.mine.pk).update(decision="WRITE_OFF")
        ReturnToStock.objects.filter(pk=self.theirs.pk).update(decision="RESTOCK")
        rows = {r["id"]: r for r in client_for(self.owner).get(URL).json()["results"]}
        self.assertEqual(rows[self.mine.pk]["decision_label"], "Huỷ bỏ, ghi lỗ")
        self.assertEqual(rows[self.theirs.pk]["decision_label"], "Tái nhập")

    # --- lọc ---------------------------------------------------------------------------------------------------
    def test_r9_filter_status(self):
        ReturnToStock.objects.filter(pk=self.mine.pk).update(status="APPROVED")
        self.assertEqual(self.ids(self.owner, "?status=APPROVED"), {self.mine.pk})
        self.assertEqual(self.ids(self.owner, "?status=DRAFT"), {self.theirs.pk})
        self.assertEqual(self.ids(self.owner, "?status=DRAFT,APPROVED"), {self.mine.pk, self.theirs.pk})
        self.assertEqual(self.ids(self.owner, "?status="), {self.mine.pk, self.theirs.pk})

    def test_r9_filter_month_uses_vietnam_time(self):
        # 2026-09-30 17:30 UTC = 01/10/2026 00:30 giờ VN: thuộc tháng 10, không thuộc tháng 9.
        edge = datetime.datetime(2026, 9, 30, 17, 30, tzinfo=datetime.timezone.utc)
        ReturnToStock.objects.filter(pk=self.mine.pk).update(created_at=edge)
        ReturnToStock.objects.filter(pk=self.theirs.pk).update(created_at=edge - datetime.timedelta(days=40))
        self.assertEqual(self.ids(self.owner, "?month=2026-10"), {self.mine.pk})
        self.assertEqual(self.ids(self.owner, "?month=2026-09"), set())
        self.assertEqual(self.ids(self.owner, "?month=2026-08"), {self.theirs.pk})

    def test_r9_filters_are_applied_inside_courier_scope(self):
        self.assertEqual(self.ids(self.courier, "?status=DRAFT"), {self.mine.pk})

    def test_r9_bad_filters_400(self):
        for query in (
            "?status=FOO", "?status=DRAFT,FOO", "?month=2026-13", "?month=2026-1", "?month=abcd-ef",
            "?month=1999-01", "?month=2026-10-01", "?month=%0A2026-10", "?month=２０２６-１０",
        ):
            resp = client_for(self.owner).get(f"{URL}{query}")
            self.assertEqual(resp.status_code, 400, (query, resp.status_code))
            self.assertEqual(resp.json()["code"], "INVALID_FILTER", query)

    def test_r9_bad_filter_message_does_not_echo_input(self):
        resp = client_for(self.owner).get(f"{URL}?status=<script>0900000555")
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("0900000555", resp.content.decode())

    def test_r9_pagination_shape(self):
        body = client_for(self.owner).get(URL).json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(len(body["results"]), 2)

    # --- dữ liệu cá nhân ---------------------------------------------------------------------------------------
    def test_r9_response_is_no_store(self):
        self.assertEqual(client_for(self.owner).get(URL)["Cache-Control"], "no-store")

    def test_r9_no_customer_identity_fields_in_response(self):
        text = client_for(self.owner).get(URL).content.decode()
        for forbidden in ("customer_name", "customer_phone", "phone", "address", "recipient", "0900000201", "Khách SO-R9-A"):
            self.assertNotIn(forbidden, text)

    def test_r9_free_note_not_in_other_courier_view_or_timelines(self):
        # SĐT giả chỉ nằm trong `note`: người giao khác không thấy ở danh sách.
        text = client_for(self.other_courier).get(URL).content.decode()
        self.assertNotIn(PHONE_SENTINEL, text)

    # --- hiệu năng ---------------------------------------------------------------------------------------------
    def test_r9_list_has_no_n_plus_one(self):
        """Số câu SQL của danh sách không đổi khi có thêm phiếu (đo cho cả owner và người giao)."""

        def measure(user):
            with CaptureQueriesContext(connection) as ctx:
                resp = client_for(user).get(URL)
            self.assertEqual(resp.status_code, 200)
            return len(ctx), resp.json()["count"]

        measure(self.owner)    # làm nóng cache quyền
        measure(self.courier)
        owner_before, owner_rows_before = measure(self.owner)
        courier_before, courier_rows_before = measure(self.courier)
        for i in range(8):
            courier = self.courier if i % 2 else self.other_courier
            _o, _c, note = self.make_delivering_note(f"SO-R9-X{i}", f"090000030{i}", courier)
            self.make_return(note, "1", courier, f"ghi chú {i}")
        owner_after, owner_rows_after = measure(self.owner)
        courier_after, courier_rows_after = measure(self.courier)
        self.assertEqual(owner_rows_after, owner_rows_before + 8)
        self.assertEqual(courier_rows_after, courier_rows_before + 4)  # chỉ 4 phiếu gán cho người giao này
        self.assertEqual(owner_after, owner_before, (owner_before, owner_after))
        self.assertEqual(courier_after, courier_before, (courier_before, courier_after))
