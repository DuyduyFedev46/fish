"""
R5 (02b §3.8, ED-23): GET /api/inventory/batches/ lọc theo `supplier`, `warehouse` (cộng `item_code`, `status`,
`has_stock` đã có) và trả thêm `receipt: {"id","code"} | null`.

- ED-23-AC1: lọc theo nhà cung cấp và theo kho; id lạ → danh sách rỗng (không lỗi).
- ED-23-AC2: `receipt` có `{"id","code":"PR-n"}` với lô sinh từ phiếu nhập, `null` với lô tạo tay.
- ED-23-AC3: id sai dạng → 400 `INVALID_FILTER`, không lặp lại giá trị đã gửi.
- ED-23-AC4: nhóm không có `view_batch` → 403, chưa đăng nhập → 401.
- Không rò giá mua / giá vốn nhập về cho quản lý, nhân viên kho (Chủ vẫn thấy).
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts import roles
from apps.inventory.stock.tests.base import (
    NON_READERS, PURCHASE_RATE, READERS, StockApiBase, find_cost_keys,
)

URL = "/api/inventory/batches/"


class BatchFilterReceiptTests(StockApiBase):
    def ids(self, query="", user=None):
        response = self.api(user or self.owner).get(URL + query)
        self.assertEqual(response.status_code, 200, response.content)
        return {row["id"] for row in response.json()["results"]}

    def test_ed23_ac1_filter_by_supplier(self):
        a = self.make_batch(supplier=self.sup)
        b = self.make_batch(supplier=self.sup2)
        self.assertEqual(self.ids(f"?supplier={self.sup.pk}"), {a.pk})
        self.assertEqual(self.ids(f"?supplier={self.sup2.pk}"), {b.pk})
        self.assertEqual(self.ids(), {a.pk, b.pk})
        self.assertEqual(self.ids("?supplier="), {a.pk, b.pk})

    def test_ed23_ac1_filter_by_warehouse(self):
        a = self.make_batch(warehouse=self.wh)
        b = self.make_batch(warehouse=self.wh2)
        self.assertEqual(self.ids(f"?warehouse={self.wh.pk}"), {a.pk})
        self.assertEqual(self.ids(f"?warehouse={self.wh2.pk}"), {b.pk})

    def test_ed23_ac1_filters_combine_with_existing_ones(self):
        a = self.make_batch(supplier=self.sup, warehouse=self.wh, item=self.item)
        self.make_batch(supplier=self.sup, warehouse=self.wh, item=self.item2)
        self.make_batch(supplier=self.sup2, warehouse=self.wh, item=self.item)
        self.make_batch(supplier=self.sup, warehouse=self.wh2, item=self.item)
        query = f"?supplier={self.sup.pk}&warehouse={self.wh.pk}&item_code=CA01&has_stock=1"
        self.assertEqual(self.ids(query), {a.pk})

    def test_ed23_ac1_unknown_ids_give_empty_list(self):
        self.make_batch()
        self.assertEqual(self.ids("?supplier=999999"), set())
        self.assertEqual(self.ids("?warehouse=999999"), set())

    def test_ed23_ac3_bad_id_gets_400_without_echo(self):
        for name in ("supplier", "warehouse"):
            for bad in ("abc-SECRET", "0", "-3", "1.5", "99999999999999999999", "1;DROP"):
                response = self.api(self.owner).get(URL, {name: bad})
                self.assertEqual(response.status_code, 400, (name, bad))
                self.assertEqual(response.json()["code"], "INVALID_FILTER", (name, bad))
                self.assertNotIn(bad, response.content.decode(), (name, bad))

    def test_ed23_filters_do_not_break_detail_and_actions(self):
        batch = self.make_batch()
        response = self.api(self.owner).get(f"{URL}{batch.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("receipt", response.json())

    def test_ed23_ac2_receipt_for_batch_from_receipt(self):
        receipt, batch = self.make_receipt_batch()
        rows = {r["id"]: r for r in self.api(self.owner).get(URL).json()["results"]}
        self.assertEqual(rows[batch.pk]["receipt"], {"id": receipt.pk, "code": f"PR-{receipt.pk}"})

    def test_ed23_ac2_receipt_is_null_for_manual_batch(self):
        batch = self.make_batch()
        rows = {r["id"]: r for r in self.api(self.owner).get(URL).json()["results"]}
        self.assertIsNone(rows[batch.pk]["receipt"])

    def test_ed23_ac2_receipt_in_detail(self):
        receipt, batch = self.make_receipt_batch()
        body = self.api(self.manager).get(f"{URL}{batch.pk}/").json()
        self.assertEqual(body["receipt"], {"id": receipt.pk, "code": f"PR-{receipt.pk}"})

    def test_ed23_ac4_permission_matrix(self):
        self.make_batch()
        for name in READERS:
            self.assertEqual(self.api(self.users[name]).get(URL).status_code, 200, name)
        for name in NON_READERS:
            self.assertEqual(self.api(self.users[name]).get(f"{URL}?supplier={self.sup.pk}").status_code, 403, name)
        self.assertEqual(self.api(self.no_group).get(URL).status_code, 403)
        self.assertEqual(self.api(None).get(URL).status_code, 401)
        self.assertEqual(self.api(None).get(f"{URL}?supplier=abc").status_code, 401)

    def test_ed23_cost_hidden_from_manager_and_warehouse_staff_but_owner_sees(self):
        self.make_receipt_batch()
        self.make_batch()
        for name in (roles.MANAGER, roles.WAREHOUSE_STAFF):
            response = self.api(self.users[name]).get(f"{URL}?supplier={self.sup.pk}&warehouse={self.wh.pk}")
            self.assert_no_cost(response, who=name)
        owner_rows = self.api(self.owner).get(URL).json()["results"]
        self.assertTrue(all("purchase_rate" in r for r in owner_rows))
        self.assertEqual(find_cost_keys(owner_rows), {"purchase_rate", "landed_unit_cost"})
        self.assertEqual(Decimal(owner_rows[0]["purchase_rate"]), PURCHASE_RATE)

    def test_ed23_receipt_object_has_no_cost_or_personal_data(self):
        _, batch = self.make_receipt_batch()
        for name in (roles.MANAGER, roles.WAREHOUSE_STAFF):
            row = next(r for r in self.api(self.users[name]).get(URL).json()["results"] if r["id"] == batch.pk)
            self.assertEqual(set(row["receipt"]), {"id", "code"}, name)

    def test_ed23_no_n_plus_one_for_receipt(self):
        def count():
            user = User.objects.get(pk=self.manager.pk)
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.api(user).get(URL).status_code, 200)
            return len(ctx)

        self.make_receipt_batch()
        small = count()
        for _ in range(5):
            self.make_receipt_batch(item=self.item2)
            self.make_batch()
        self.assertEqual(count(), small)

