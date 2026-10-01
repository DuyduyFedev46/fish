"""
`POST /api/purchasing/receipts/receive-batches/` (P8b Lô 3-4): ma trận vai, kết quả, không rò giá vốn ra vai không được xem.
Route tên cũ (alias tạm của Lô 3-4) đã gỡ ở Lô 5: không còn chạy hàm nhập lô và không tạo phiếu.
"""
from decimal import Decimal

from django.test import TestCase

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import PurchaseReceipt, Supplier

NEW = "/api/purchasing/receipts/receive-batches/"
REMOVED = "/api/purchasing/receipts/nhap-lo/"


class ReceiveBatchesRouteTests(TestCase):
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

    def test_receive_batches_role_matrix(self):
        for role, user in self.users.items():
            status = client_for(user).post(NEW, self._payload(), format="json").status_code
            expected = 201 if role in (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF) else 403
            self.assertEqual(status, expected, role)

    def test_receive_batches_anonymous_is_401(self):
        self.assertEqual(client_for(None).post(NEW, self._payload(), format="json").status_code, 401)
        self.assertEqual(PurchaseReceipt.objects.count(), 0)

    def test_removed_old_route_no_longer_receives_batches_for_any_role(self):
        """P8b Lô 5: tên cũ không còn là route nhập lô. Mọi vai (kể cả Chủ có đủ quyền) không tạo được phiếu, kho không đổi."""
        attempts = 0
        for role, user in self.users.items():
            res = client_for(user).post(REMOVED, self._payload(), format="json")
            self.assertNotIn(res.status_code, (200, 201), role)
            attempts += 1
        res = client_for(None).post(REMOVED, self._payload(), format="json")
        self.assertNotIn(res.status_code, (200, 201))
        self.assertEqual(attempts, 5)
        self.assertEqual(PurchaseReceipt.objects.count(), 0)
        self.assertEqual(Batch.objects.count(), 0)

    def test_removed_old_route_does_not_resolve_to_the_receive_batches_view(self):
        from django.urls import resolve

        match = resolve(REMOVED)
        self.assertNotEqual(getattr(match.func, "actions", {}).get("post"), "receive_batches")
        self.assertEqual(resolve(NEW).func.actions, {"post": "receive_batches"})

    def test_receive_batches_creates_receipt_and_batches_on_new_path(self):
        res = client_for(self.users[roles.WAREHOUSE_STAFF]).post(NEW, self._payload(), format="json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(set(data), {"receipt", "batches"})
        self.assertEqual(len(data["batches"]), 1)
        self.assertEqual(PurchaseReceipt.objects.count(), 1)
        self.assertEqual(Batch.objects.count(), 1)

    def test_receive_batches_rejects_get(self):
        self.assertEqual(client_for(self.users[roles.OWNER]).get(NEW).status_code, 405)

    def test_receive_batches_invalid_payload_400(self):
        self.assertEqual(client_for(self.users[roles.OWNER]).post(NEW, {"lines": []}, format="json").status_code, 400)

    def test_receive_batches_cost_fields_follow_view_costprice(self):
        """Bất biến 1: NV kho và Quản lý không thấy `purchase_rate`, `landed_unit_cost`, `rate` của dòng phiếu; Chủ thấy.

        Kiểm khoá thật của response (mẫu `test_nhap_lo.py`, DW-17-AC5).
        """
        for role in (roles.WAREHOUSE_STAFF, roles.MANAGER):
            with self.subTest(role=role):
                res = client_for(self.users[role]).post(NEW, self._payload(), format="json")
                self.assertEqual(res.status_code, 201)
                data = res.json()
                self.assertTrue(data["batches"])
                self.assertNotIn("purchase_rate", data["batches"][0])
                self.assertNotIn("landed_unit_cost", data["batches"][0])
                self.assertTrue(data["receipt"]["lines"])
                for line in data["receipt"]["lines"]:
                    self.assertNotIn("rate", line)
        res = client_for(self.users[roles.OWNER]).post(NEW, self._payload(), format="json")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("purchase_rate", data["batches"][0])
        self.assertIn("landed_unit_cost", data["batches"][0])
        self.assertTrue(data["receipt"]["lines"])
        for line in data["receipt"]["lines"]:
            self.assertIn("rate", line)
        self.assertEqual(Decimal(str(data["receipt"]["lines"][0]["rate"])), Decimal("80000.00"))

    def test_receive_batches_is_the_only_ai_command_and_its_path_is_the_new_route(self):
        """P8b Lô 4: id lệnh AI là `receive_batches`, path `/receive-batches/`; chỉ có một lệnh nhập lô."""
        from apps.ai.registry.discovery import get_registry

        specs = {spec.id: spec for spec in get_registry().get_specs()}
        receive_id = "purchasing.purchasereceipt.receive_batches"
        self.assertIn(receive_id, specs)
        self.assertFalse([i for i in specs if i.endswith(".nhap_lo")])
        self.assertEqual(specs[receive_id].path, "/api/purchasing/receipts/receive-batches/")
        self.assertEqual([i for i in specs if "purchasereceipt" in i and "receive" in i], [receive_id])
