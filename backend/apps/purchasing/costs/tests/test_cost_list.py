"""
R12 (ERP theo design Lô 12, 02b §3.8): `GET /api/purchasing/costs/` đọc chi phí phụ.

Chi phí phụ là giá vốn (landed cost, BR-GV, bất biến 1): toàn bộ chứng từ chỉ cho người có `view_purchasecost`
(chỉ owner) VÀ `view_costprice`. Vai khác 403, chưa đăng nhập 401, không lộ số tiền trong thân lỗi.
Lọc `cost_type` (nhiều, cách phẩy), `month=YYYY-MM` (theo `incurred_date`); sai → 400 `INVALID_FILTER`.
POST giữ như cũ (chỉ owner). Mọi dữ liệu là giả.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.costs import services
from apps.purchasing.models import PurchaseCost, Supplier

URL = "/api/purchasing/costs/"
EXPECTED_KEYS = {
    "id", "cost_type", "cost_type_label", "amount", "allocation_method", "allocation_method_label",
    "incurred_date", "note", "created_by", "created_at", "allocations", "batch_count",
}
ALLOCATION_KEYS = {"id", "purchase_cost", "batch", "allocated_amount"}
AMOUNT_SENTINEL = "987654"


class CostListBase(TestCase):
    def setUp(self):
        self.owner = make_user("u_owner", roles.OWNER)
        self.manager = make_user("u_manager", roles.MANAGER)
        self.warehouse_staff = make_user("u_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("u_courier", roles.DELIVERY_STAFF)
        self.customer_service = make_user("u_cs", roles.CUSTOMER_SERVICE)
        self.no_group = User.objects.create_user("u_no_group", password="x")
        group = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=group)
        self.supplier = Supplier.objects.create(name="Đầu mối A")
        self.warehouse = Warehouse.objects.create(name="Kho chính")

    def make_batch(self, qty="10"):
        return batch_services.create_batch(
            item=self.item, supplier=self.supplier, warehouse=self.warehouse,
            received_date=datetime.date(2026, 9, 28), qty=Decimal(qty), purchase_rate=Decimal("80000"),
        )

    def make_cost(self, *, cost_type="ICE", amount="100000", method="BY_QTY", day=datetime.date(2026, 9, 28),
                  batches=None):
        batches = batches or [self.make_batch()]
        return services.record_purchase_cost(
            cost_type=cost_type, amount=Decimal(amount), allocation_method=method, incurred_date=day,
            allocations=list(batches), actor=self.owner,
        )

    def get(self, user, query=""):
        return client_for(user).get(f"{URL}{query}")

    def ids(self, user, query=""):
        resp = self.get(user, query)
        self.assertEqual(resp.status_code, 200, (query, resp.content))
        return [row["id"] for row in resp.json()["results"]]


class CostListPermissionTests(CostListBase):
    def test_r12_owner_gets_200(self):
        self.make_cost()
        self.assertEqual(self.get(self.owner).status_code, 200)

    def test_r12_every_other_role_403_without_leaking_amount(self):
        self.make_cost(amount=AMOUNT_SENTINEL)
        cost = PurchaseCost.objects.get()
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service, self.no_group):
            for url in (URL, f"{URL}{cost.pk}/"):
                resp = client_for(user).get(url)
                self.assertEqual(resp.status_code, 403, (user.username, url))
                self.assertNotIn(AMOUNT_SENTINEL, resp.content.decode(), (user.username, url))
        self.assertEqual(self.get(None).status_code, 401)
        self.assertEqual(client_for(None).get(f"{URL}{cost.pk}/").status_code, 401)

    def test_r12_view_purchasecost_without_view_costprice_is_403(self):
        """Tiền chi phí phụ là giá vốn: có quyền xem model mà thiếu `view_costprice` vẫn bị chặn."""
        self.make_cost(amount=AMOUNT_SENTINEL)
        partial = make_user("u_partial", perms=("purchasing.view_purchasecost",))
        resp = self.get(partial)
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn(AMOUNT_SENTINEL, resp.content.decode())

    def test_r12_costprice_without_view_purchasecost_is_403(self):
        self.make_cost()
        partial = make_user("u_partial2", perms=("inventory.view_costprice",))
        self.assertEqual(self.get(partial).status_code, 403)


class CostListContractTests(CostListBase):
    def test_r12_row_contract_labels_and_batch_count(self):
        batches = [self.make_batch("10"), self.make_batch("30")]
        cost = self.make_cost(cost_type="TRANSPORT", amount="400000", method="BY_VALUE", batches=batches)
        self.make_cost(cost_type="ICE", amount="50000")
        resp = self.get(self.owner)
        body = resp.json()
        self.assertEqual(body["count"], 2)
        row = next(r for r in body["results"] if r["id"] == cost.pk)
        self.assertEqual(set(row), EXPECTED_KEYS)
        self.assertEqual(row["cost_type"], "TRANSPORT")
        self.assertEqual(row["cost_type_label"], "Vận chuyển")
        self.assertEqual(row["allocation_method"], "BY_VALUE")
        self.assertEqual(row["allocation_method_label"], "Theo giá trị")
        self.assertEqual(row["amount"], "400000.00")
        self.assertEqual(row["incurred_date"], "2026-09-28")
        self.assertEqual(row["batch_count"], 2)
        self.assertEqual(len(row["allocations"]), 2)
        self.assertEqual(set(row["allocations"][0]), ALLOCATION_KEYS)
        total = sum(Decimal(a["allocated_amount"]) for a in row["allocations"])
        self.assertEqual(total, Decimal("400000.00"))
        other = next(r for r in body["results"] if r["id"] != cost.pk)
        self.assertEqual(other["cost_type_label"], "Đá")
        self.assertEqual(other["allocation_method_label"], "Theo số kg")
        self.assertEqual(other["batch_count"], 1)

    def test_r12_all_labels_cover_every_choice(self):
        for cost_type, label in (("ICE", "Đá"), ("TRANSPORT", "Vận chuyển"), ("LOADING", "Bốc vác"), ("OTHER", "Khác")):
            cost = self.make_cost(cost_type=cost_type)
            row = client_for(self.owner).get(f"{URL}{cost.pk}/").json()
            self.assertEqual(row["cost_type_label"], label)

    def test_r12_detail_has_same_keys(self):
        cost = self.make_cost(amount=AMOUNT_SENTINEL)
        body = client_for(self.owner).get(f"{URL}{cost.pk}/").json()
        self.assertEqual(set(body), EXPECTED_KEYS)
        self.assertEqual(body["batch_count"], 1)

    def test_r12_whole_document_is_cost_data_only_owner_receives_it(self):
        """Mọi khoá tiền của chứng từ nằm trong thân owner; không vai nào khác nhận được dù chỉ một khoá."""
        self.make_cost(amount=AMOUNT_SENTINEL)
        self.assertIn(AMOUNT_SENTINEL, self.get(self.owner).content.decode())
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service):
            body = self.get(user).json()
            self.assertEqual(set(body) & (COST_KEYS | {"amount", "allocations", "results"}), set(), user.username)

    def test_r12_sorted_newest_first_and_paginated_20(self):
        older = self.make_cost(day=datetime.date(2026, 9, 1))
        newer = self.make_cost(day=datetime.date(2026, 9, 20))
        self.assertEqual(self.ids(self.owner), [newer.pk, older.pk])
        for _ in range(22):
            self.make_cost()
        body = self.get(self.owner).json()
        self.assertEqual(body["count"], 24)
        self.assertEqual(len(body["results"]), 20)
        self.assertIsNotNone(body["next"])


class CostListFilterTests(CostListBase):
    def setUp(self):
        super().setUp()
        self.ice_sep = self.make_cost(cost_type="ICE", day=datetime.date(2026, 9, 30))
        self.transport_sep = self.make_cost(cost_type="TRANSPORT", day=datetime.date(2026, 9, 5))
        self.loading_oct = self.make_cost(cost_type="LOADING", day=datetime.date(2026, 10, 1))

    def test_r12_filter_cost_type_single_and_multiple(self):
        self.assertEqual(self.ids(self.owner, "?cost_type=ICE"), [self.ice_sep.pk])
        self.assertEqual(set(self.ids(self.owner, "?cost_type=ICE,LOADING")), {self.ice_sep.pk, self.loading_oct.pk})
        self.assertEqual(len(self.ids(self.owner, "?cost_type=")), 3)

    def test_r12_filter_month_uses_incurred_date_with_boundaries(self):
        self.assertEqual(set(self.ids(self.owner, "?month=2026-09")), {self.ice_sep.pk, self.transport_sep.pk})
        self.assertEqual(self.ids(self.owner, "?month=2026-10"), [self.loading_oct.pk])
        self.assertEqual(self.ids(self.owner, "?month=2026-08"), [])

    def test_r12_filters_combine(self):
        self.assertEqual(self.ids(self.owner, "?cost_type=TRANSPORT&month=2026-09"), [self.transport_sep.pk])
        self.assertEqual(self.ids(self.owner, "?cost_type=TRANSPORT&month=2026-10"), [])

    def test_r12_invalid_filters_get_400_without_echoing_value(self):
        for query in ("cost_type=GOLD", "cost_type=ICE,GOLD", "cost_type=ice", "month=2026-13", "month=2026-1",
                      "month=1999-12", "month=2101-01", "month=%0A2026-10", "month=thang-muoi"):
            resp = self.get(self.owner, f"?{query}")
            self.assertEqual(resp.status_code, 400, query)
            body = resp.json()
            self.assertEqual(body["code"], "INVALID_FILTER", query)
            value = query.split("=", 1)[1]
            if len(value) > 3 and "%" not in value:
                self.assertNotIn(value, body["detail"], query)

    def test_r12_filter_error_never_reaches_non_owner(self):
        self.assertEqual(self.get(self.manager, "?cost_type=GOLD").status_code, 403)


class CostListQueryCountTests(CostListBase):
    def test_r12_no_n_plus_one(self):
        def run():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.get(self.owner).status_code, 200)
            return len(ctx)

        self.make_cost()
        run()
        base = run()
        for _ in range(6):
            self.make_cost(batches=[self.make_batch(), self.make_batch()])
        self.assertEqual(run(), base)


class CostWriteUnchangedTests(CostListBase):
    def payload(self):
        batch = self.make_batch()
        return {
            "cost_type": "ICE", "amount": "250000", "allocation_method": "BY_QTY", "incurred_date": "2026-10-01",
            "allocations": [{"batch": batch.pk}],
        }

    def test_r12_owner_post_201_with_labels(self):
        resp = client_for(self.owner).post(URL, self.payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(set(body), EXPECTED_KEYS)
        self.assertEqual(body["batch_count"], 1)
        self.assertEqual(body["cost_type_label"], "Đá")

    def test_r12_manager_post_403_and_nothing_written(self):
        resp = client_for(self.manager).post(URL, self.payload(), format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(PurchaseCost.objects.count(), 0)

    def test_r12_delete_405(self):
        cost = self.make_cost()
        self.assertEqual(client_for(self.owner).delete(f"{URL}{cost.pk}/").status_code, 405)
        self.assertTrue(PurchaseCost.objects.filter(pk=cost.pk).exists())
