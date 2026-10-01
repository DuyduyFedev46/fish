"""
P8b Lô 3: `POST /api/purchasing/receipts/receive-batches/` (tên mới) và `/nhap-lo/` (tên cũ, alias tới Lô 5)
cùng trỏ hàm `receive_batches` (Lô 4 đổi tên hàm và id lệnh AI): cùng ma trận vai, cùng kết quả,
không rò giá vốn ra vai không được xem. `nhap-lo/` chỉ là route alias, gỡ ở Lô 5.
"""
from decimal import Decimal

from django.test import TestCase

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import PurchaseReceipt, Supplier

NEW = "/api/purchasing/receipts/receive-batches/"
OLD = "/api/purchasing/receipts/nhap-lo/"


class ReceiveBatchesAliasTests(TestCase):
    def setUp(self):
        group = ItemGroup.objects.create(name="Cá")
        Item.objects.create(code="TOM01", name="Tôm sú", item_group=group, shelf_life_in_days=90, stock_uom="KG")
        self.supplier = Supplier.objects.create(name="Đầu mối Phan Thiết")
        self.warehouse = Warehouse.objects.create(name="Kho chính")
        self.users = {
            roles.OWNER: make_user("chu_alias", roles.OWNER),
            roles.MANAGER: make_user("ql_alias", roles.MANAGER),
            roles.WAREHOUSE_STAFF: make_user("kho_alias", roles.WAREHOUSE_STAFF),
            roles.DELIVERY_STAFF: make_user("giao_alias", roles.DELIVERY_STAFF),
            roles.CUSTOMER_SERVICE: make_user("cs_alias", roles.CUSTOMER_SERVICE),
        }

    def _payload(self):
        return {
            "supplier": self.supplier.pk,
            "received_date": "2026-09-28",
            "warehouse": self.warehouse.pk,
            "lines": [{"item_code": "TOM01", "qty": "50.000", "rate": "80000.00", "shelf_life_days": 60}],
        }

    def test_receive_batches_role_matrix_same_on_both_paths(self):
        for role, user in self.users.items():
            statuses = {
                path: client_for(user).post(path, self._payload(), format="json").status_code
                for path in (NEW, OLD)
            }
            self.assertEqual(statuses[NEW], statuses[OLD], role)
            expected = 201 if role in (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF) else 403
            self.assertEqual(statuses[NEW], expected, role)

    def test_receive_batches_anonymous_is_401_on_both_paths(self):
        for path in (NEW, OLD):
            self.assertEqual(client_for(None).post(path, self._payload(), format="json").status_code, 401)
        self.assertEqual(PurchaseReceipt.objects.count(), 0)

    def test_receive_batches_creates_receipt_and_batches_on_new_path(self):
        res = client_for(self.users[roles.WAREHOUSE_STAFF]).post(NEW, self._payload(), format="json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(set(data), {"receipt", "batches"})
        self.assertEqual(len(data["batches"]), 1)
        self.assertEqual(PurchaseReceipt.objects.count(), 1)
        self.assertEqual(Batch.objects.count(), 1)

    def test_receive_batches_same_response_shape_on_both_paths(self):
        client = client_for(self.users[roles.WAREHOUSE_STAFF])
        new = client.post(NEW, self._payload(), format="json").json()
        old = client.post(OLD, self._payload(), format="json").json()
        self.assertEqual(set(new), set(old))
        self.assertEqual(set(new["receipt"]), set(old["receipt"]))
        self.assertEqual(set(new["batches"][0]), set(old["batches"][0]))

    def test_receive_batches_rejects_get_on_both_paths(self):
        client = client_for(self.users[roles.OWNER])
        for path in (NEW, OLD):
            self.assertEqual(client.get(path).status_code, 405, path)

    def test_receive_batches_invalid_payload_400_on_both_paths(self):
        client = client_for(self.users[roles.OWNER])
        for path in (NEW, OLD):
            self.assertEqual(client.post(path, {"lines": []}, format="json").status_code, 400, path)

    def test_receive_batches_cost_fields_follow_view_costprice_on_both_paths(self):
        """Bất biến 1: NV kho và Quản lý không thấy `purchase_rate`, `landed_unit_cost`, `rate` của dòng phiếu; Chủ thấy.

        Kiểm khoá thật của response (mẫu `test_nhap_lo.py`, DW-17-AC5), chạy trên cả `nhap-lo/` và `receive-batches/`.
        """
        for path in (NEW, OLD):
            for role in (roles.WAREHOUSE_STAFF, roles.MANAGER):
                with self.subTest(path=path, role=role):
                    res = client_for(self.users[role]).post(path, self._payload(), format="json")
                    self.assertEqual(res.status_code, 201)
                    data = res.json()
                    self.assertTrue(data["batches"])
                    self.assertNotIn("purchase_rate", data["batches"][0])
                    self.assertNotIn("landed_unit_cost", data["batches"][0])
                    self.assertTrue(data["receipt"]["lines"])
                    for line in data["receipt"]["lines"]:
                        self.assertNotIn("rate", line)
            with self.subTest(path=path, role=roles.OWNER):
                res = client_for(self.users[roles.OWNER]).post(path, self._payload(), format="json")
                self.assertEqual(res.status_code, 201)
                data = res.json()
                self.assertIn("purchase_rate", data["batches"][0])
                self.assertIn("landed_unit_cost", data["batches"][0])
                self.assertTrue(data["receipt"]["lines"])
                for line in data["receipt"]["lines"]:
                    self.assertIn("rate", line)
                self.assertEqual(Decimal(str(data["receipt"]["lines"][0]["rate"])), Decimal("80000.00"))

    def test_receive_batches_is_the_only_ai_command_and_its_path_is_the_new_route(self):
        """P8b Lô 4: id lệnh AI là `receive_batches`, path `/receive-batches/`; `nhap-lo/` chỉ là route alias, không thêm lệnh."""
        from apps.ai.registry.discovery import get_registry

        specs = {spec.id: spec for spec in get_registry().get_specs()}
        receive_id = "purchasing.purchasereceipt.receive_batches"
        self.assertIn(receive_id, specs)
        self.assertFalse([i for i in specs if i.endswith(".nhap_lo")])  # naming: allow - id cũ phải biến mất
        self.assertEqual(specs[receive_id].path, "/api/purchasing/receipts/receive-batches/")
        self.assertEqual([i for i in specs if "purchasereceipt" in i and "receive" in i], [receive_id])

    def test_receive_batches_old_and_new_paths_resolve_to_the_same_view_method(self):
        from django.urls import resolve

        new_match = resolve(NEW)
        old_match = resolve(OLD)
        self.assertEqual(new_match.func.actions, {"post": "receive_batches"})
        self.assertEqual(old_match.func.actions, {"post": "receive_batches"})
