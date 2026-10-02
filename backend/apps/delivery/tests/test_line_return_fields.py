"""Lô 9 FE: dòng phiếu giao (chi tiết) có `batch_pk` (pk lô, để tạo phiếu hoàn mà không cần quyền xem lô) và
`returned_qty` (số kg đã hoàn: phiếu hoàn Chờ duyệt + Đã duyệt của lô đó trên phiếu giao này, BR-HV-01).
Không phải giá vốn, không phải dữ liệu cá nhân. Dữ liệu giả."""
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for
from apps.inventory.models import ReturnToStock
from apps.inventory.returns.tests.base import RATE_SENTINEL, ReturnsApiBase, find_cost_keys

DELIVERY_URL = "/api/delivery/notes/"
LINE_KEYS = {"item_name", "qty_kg", "batch_id", "expiry_date", "batch_pk", "returned_qty"}


class DeliveryLineReturnFieldsTests(ReturnsApiBase):
    def detail(self, user, note=None):
        resp = client_for(user).get(f"{DELIVERY_URL}{(note or self.note).pk}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_courier_sees_batch_pk_and_zero_returned_qty(self):
        data = self.detail(self.courier)
        self.assertEqual(len(data["lines"]), 1)
        line = data["lines"][0]
        self.assertEqual(set(line), LINE_KEYS)
        self.assertEqual(line["batch_pk"], self.batch.pk)
        self.assertEqual(line["batch_id"], self.batch.batch_id)  # khoá cũ giữ nguyên
        self.assertEqual(Decimal(line["returned_qty"]), Decimal("0"))

    def test_returned_qty_after_return_of_3kg(self):
        resp = self.post(self.courier, self.payload(qty="3"))
        self.assertEqual(resp.status_code, 201, resp.content)
        line = self.detail(self.courier)["lines"][0]
        self.assertEqual(Decimal(line["returned_qty"]), Decimal("3"))

    def test_returned_qty_counts_draft_and_approved(self):
        self.make_return(self.note, "2", self.courier)
        approved = self.make_return(self.note, "1.5", self.courier)
        ReturnToStock.objects.filter(pk=approved.pk).update(status=ReturnToStock.Status.APPROVED)
        line = self.detail(self.courier)["lines"][0]
        self.assertEqual(Decimal(line["returned_qty"]), Decimal("3.5"))

    def test_returned_qty_ignores_other_note_of_same_batch(self):
        self.make_return(self.other_note, "4", self.other_courier)
        line = self.detail(self.courier)["lines"][0]
        self.assertEqual(Decimal(line["returned_qty"]), Decimal("0"))

    def test_scope_unchanged_courier_cannot_open_other_note(self):
        resp = client_for(self.courier).get(f"{DELIVERY_URL}{self.other_note.pk}/")
        self.assertEqual(resp.status_code, 404)

    def test_full_scope_groups_see_fields(self):
        self.make_return(self.note, "2", self.courier)
        for user in (self.owner, self.manager, self.warehouse_staff):
            line = self.detail(user)["lines"][0]
            self.assertEqual(line["batch_pk"], self.batch.pk, user.username)
            self.assertEqual(Decimal(line["returned_qty"]), Decimal("2"), user.username)

    def test_no_cost_keys_or_rate_in_detail(self):
        self.make_return(self.note, "2", self.courier)
        resp = client_for(self.courier).get(f"{DELIVERY_URL}{self.note.pk}/")
        self.assertEqual(find_cost_keys(resp.json()), set())
        self.assertNotIn(RATE_SENTINEL, resp.content.decode())
        self.assertFalse({"batch_pk", "returned_qty"} & COST_KEYS)

    def test_list_does_not_carry_lines(self):
        self.make_return(self.note, "2", self.courier)
        resp = client_for(self.courier).get(DELIVERY_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        for row in resp.json()["results"]:
            self.assertNotIn("lines", row)
            self.assertNotIn("batch_pk", row)
            self.assertNotIn("returned_qty", row)

    def test_no_n_plus_one_with_many_lines(self):
        def count_queries():
            with CaptureQueriesContext(connection) as ctx:
                self.detail(self.courier)
            return len(ctx)

        baseline = count_queries()
        # Thêm nhiều dòng phân bổ và nhiều phiếu hoàn trên cùng phiếu giao.
        for _ in range(5):
            self.add_allocation(self.note, self.batch, "1")
        for _ in range(4):
            self.make_return(self.note, "0.5", self.courier)
        with CaptureQueriesContext(connection) as ctx:
            data = self.detail(self.courier)
        self.assertEqual(len(data["lines"]), 6)
        self.assertTrue(all(Decimal(line["returned_qty"]) == Decimal("2") for line in data["lines"]))
        self.assertLessEqual(len(ctx), baseline + 1)
