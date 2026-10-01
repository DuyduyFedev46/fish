"""
R7 (02b §3.8, ED-25): GET/POST /api/inventory/warehouses/ — danh sách kho kèm số lô còn tồn; thêm kho.

- ED-25-AC3: thêm kho (Kho hoặc Nhóm kho), kho mới hiện trong danh sách.
- ED-25-AC4: nhóm không có `view_warehouse` → 403, chưa đăng nhập → 401.
- Thêm kho chỉ Chủ (`add_warehouse`); trùng tên → 400 `WAREHOUSE_NAME_TAKEN`; có AuditLog.
"""
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import AuditLog
from apps.inventory.models import Batch, Warehouse
from apps.inventory.stock import services as stock_services

from .base import NON_READERS, READERS, StockApiBase, roles

URL = "/api/inventory/warehouses/"
EXPECTED_KEYS = {"id", "name", "is_group", "is_group_label", "active_batch_count", "total_qty"}


class WarehouseListTests(StockApiBase):
    def test_ed25_ac4_readers_get_200_others_403_401(self):
        for name in READERS:
            self.assertEqual(self.api(self.users[name]).get(URL).status_code, 200, name)
        for name in NON_READERS:
            self.assertEqual(self.api(self.users[name]).get(URL).status_code, 403, name)
        self.assertEqual(self.api(self.no_group).get(URL).status_code, 403)
        self.assertEqual(self.api(None).get(URL).status_code, 401)

    def test_r7_exact_keys_and_no_cost_for_every_reader(self):
        self.make_batch(qty="30")
        for name in READERS:
            response = self.api(self.users[name]).get(URL)
            self.assert_no_cost(response, who=name)
            for row in response.json()["results"]:
                self.assertEqual(set(row), EXPECTED_KEYS, name)

    def test_r7_counts_only_batches_with_stock(self):
        self.make_batch(qty="30")                     # còn 30
        self.make_batch(item=self.item2, qty="12.5")  # còn 12,5
        empty = self.make_batch(qty="8")
        stock_services.record_movement(
            batch=empty, qty_change="-8", movement_type="SALE", reference="INV-X",
        )
        rows = {r["name"]: r for r in self.api(self.owner).get(URL).json()["results"]}
        self.assertEqual(rows["Kho chính"]["active_batch_count"], 2)
        self.assertEqual(rows["Kho chính"]["total_qty"], "42.500")
        self.assertEqual(rows["Kho lạnh"]["active_batch_count"], 0)
        self.assertEqual(rows["Kho lạnh"]["total_qty"], "0.000")

    def test_r7_sums_do_not_multiply_with_several_batches(self):
        for _ in range(3):
            self.make_batch(qty="10")
        row = next(r for r in self.api(self.owner).get(URL).json()["results"] if r["name"] == "Kho chính")
        self.assertEqual((row["active_batch_count"], row["total_qty"]), (3, "30.000"))

    def test_r7_is_group_label(self):
        Warehouse.objects.create(name="Nhóm kho miền Nam", is_group=True)
        rows = {r["name"]: r for r in self.api(self.owner).get(URL).json()["results"]}
        self.assertEqual(rows["Nhóm kho miền Nam"]["is_group_label"], "Nhóm kho")
        self.assertTrue(rows["Nhóm kho miền Nam"]["is_group"])
        self.assertEqual(rows["Kho chính"]["is_group_label"], "Kho")

    def test_r7_ordered_by_name(self):
        names = [r["name"] for r in self.api(self.owner).get(URL).json()["results"]]
        self.assertEqual(names, sorted(names))

    def test_r7_retrieve(self):
        self.make_batch(qty="30")
        response = self.api(self.manager).get(f"{URL}{self.wh.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["active_batch_count"], 1)

    def test_r7_no_n_plus_one(self):
        def count():
            user = User.objects.get(pk=self.manager.pk)
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.api(user).get(URL).status_code, 200)
            return len(ctx)

        self.make_batch(qty="5")
        small = count()
        for i in range(6):
            wh = Warehouse.objects.create(name=f"Kho phụ {i}")
            self.make_batch(warehouse=wh, qty="5")
        self.assertEqual(count(), small)


class WarehouseCreateTests(StockApiBase):
    def post(self, user, body):
        return self.api(user).post(URL, body, format="json")

    def test_ed25_ac3_owner_creates_warehouse_and_it_appears_in_list(self):
        response = self.post(self.owner, {"name": "Kho đông lạnh", "is_group": False})
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(set(body), EXPECTED_KEYS)
        self.assertEqual((body["name"], body["is_group"], body["active_batch_count"], body["total_qty"]),
                         ("Kho đông lạnh", False, 0, "0.000"))
        names = [r["name"] for r in self.api(self.owner).get(URL).json()["results"]]
        self.assertIn("Kho đông lạnh", names)

    def test_ed25_ac3_can_create_group_warehouse(self):
        response = self.post(self.owner, {"name": "Nhóm kho Bắc", "is_group": True})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["is_group_label"], "Nhóm kho")

    def test_ed25_is_group_defaults_to_false(self):
        response = self.post(self.owner, {"name": "Kho mặc định"})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertFalse(response.json()["is_group"])

    def test_ed25_name_is_trimmed(self):
        response = self.post(self.owner, {"name": "   Kho  sau   cảng "})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["name"], "Kho sau cảng")

    def test_ed25_ac4_only_owner_can_create(self):
        for name in (roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE):
            response = self.post(self.users[name], {"name": f"Kho của {name}"})
            self.assertEqual(response.status_code, 403, name)
        self.assertEqual(self.post(self.no_group, {"name": "Kho X"}).status_code, 403)
        self.assertEqual(self.post(None, {"name": "Kho X"}).status_code, 401)
        self.assertEqual(Warehouse.objects.count(), 2)  # chỉ 2 kho của setUp
        self.assertFalse(AuditLog.objects.filter(action="create_warehouse").exists())

    def test_ed25_duplicate_name_gets_400_without_echo(self):
        for body_name in ("Kho chính", "  kho CHÍNH ", "Kho  chính"):
            response = self.post(self.owner, {"name": body_name})
            self.assertEqual(response.status_code, 400, body_name)
            self.assertEqual(response.json()["code"], "WAREHOUSE_NAME_TAKEN")
            self.assertNotIn("chính", response.json()["detail"].lower())
        self.assertEqual(Warehouse.objects.count(), 2)
        self.assertFalse(AuditLog.objects.filter(action="create_warehouse").exists())

    def test_ed25_blank_or_missing_name_gets_400(self):
        for body in ({"name": ""}, {"name": "   "}, {"name": None}):
            response = self.post(self.owner, body)
            self.assertEqual(response.status_code, 400, body)
        response = self.post(self.owner, {"name": "   "})
        self.assertEqual(response.json()["code"], "WAREHOUSE_NAME_REQUIRED")
        self.assertEqual(self.post(self.owner, {}).status_code, 400)
        self.assertEqual(Warehouse.objects.count(), 2)

    def test_ed25_too_long_name_gets_400_without_echo(self):
        long_name = "K" * 121
        response = self.post(self.owner, {"name": long_name})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "WAREHOUSE_NAME_TOO_LONG")
        self.assertNotIn(long_name, response.content.decode())
        self.assertEqual(self.post(self.owner, {"name": "K" * 120}).status_code, 201)

    def test_ed25_wrong_types_get_400(self):
        self.assertEqual(self.post(self.owner, {"name": ["a"]}).status_code, 400)
        self.assertEqual(self.post(self.owner, {"name": "Kho T", "is_group": "khong-phai-bool"}).status_code, 400)
        self.assertEqual(self.api(self.owner).post(URL, "chuoi", format="json").status_code, 400)
        self.assertEqual(Warehouse.objects.count(), 2)

    def test_ed25_audit_log_records_creation_without_free_text(self):
        response = self.post(self.owner, {"name": "Kho kiểm toán", "is_group": True})
        self.assertEqual(response.status_code, 201)
        log = AuditLog.objects.get(action="create_warehouse")
        self.assertEqual(log.actor, self.owner)
        self.assertEqual(log.actor_kind, "user")
        self.assertEqual(log.model_name, "inventory.Warehouse")
        self.assertEqual(log.object_id, str(response.json()["id"]))
        self.assertEqual(log.changes, {"is_group": True})

    def test_ed25_owner_can_still_rename_existing_warehouse(self):
        response = self.api(self.owner).patch(f"{URL}{self.wh.pk}/", {"name": "Kho đổi tên"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["name"], "Kho đổi tên")
        self.assertEqual(set(response.json()), EXPECTED_KEYS)

    def test_ed25_rename_to_duplicate_name_gets_400(self):
        response = self.api(self.owner).patch(f"{URL}{self.wh.pk}/", {"name": "Kho lạnh"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_ed25_non_owner_cannot_rename(self):
        for name in (roles.MANAGER, roles.WAREHOUSE_STAFF):
            response = self.api(self.users[name]).patch(f"{URL}{self.wh.pk}/", {"name": "Đổi"}, format="json")
            self.assertEqual(response.status_code, 403, name)
        self.wh.refresh_from_db()
        self.assertEqual(self.wh.name, "Kho chính")

    def test_ed25_warehouse_with_batch_cannot_be_deleted_through_api(self):
        self.make_batch()
        response = self.api(self.owner).delete(f"{URL}{self.wh.pk}/")
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Batch.objects.filter(warehouse=self.wh).exists())
