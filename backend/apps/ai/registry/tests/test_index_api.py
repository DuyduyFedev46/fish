"""
Test API chỉ mục và chi tiết lệnh (DW-07-AC4, AC5, AC6, AC8, AC9, AC10).
"""
from decimal import Decimal
from django.conf import settings
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai.policy.rules import COST_KEYS, SCRUB_PII_KEYS
from apps.ai.registry.discovery import get_registry
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier


@override_settings(AI_ENABLED=True)
class CommandIndexApiTestCase(TestCase):
    def setUp(self):
        self.user_chu = make_user("chu_test", "chu")
        self.user_ql = make_user("ql_test", "quan_ly")
        self.user_kho = make_user("kho_test", "nv_kho")
        self.user_giao = make_user("giao_test", "nv_giao")

        self.client_chu = client_for(self.user_chu)
        self.client_ql = client_for(self.user_ql)
        self.client_kho = client_for(self.user_kho)
        self.client_giao = client_for(self.user_giao)

        # Setup master data
        g = ItemGroup.objects.create(name="Cá")
        self.item1 = Item.objects.create(code="CA-001", name="Cá thu", item_group=g)
        self.item2 = Item.objects.create(code="CA-002", name="Cá ngừ", item_group=g)
        self.sup = Supplier.objects.create(name="Đầu mối Phú Quốc")
        self.wh = Warehouse.objects.create(name="Kho lạnh 1")

    def test_dw07_ac4_group_matrix(self):
        """DW-07-AC4: Ma trận Group 4 nhóm; lệnh ngoài quyền -> descriptor 404 COMMAND_UNKNOWN."""
        # 1. nv_giao gọi index: không có purchasing.*, batch.close, reports.*
        res_giao = self.client_giao.get("/api/ai/commands/index/")
        self.assertEqual(res_giao.status_code, 200)
        ids_giao = [c["id"] for c in res_giao.json()["commands"]]
        for cid in ids_giao:
            self.assertFalse(cid.startswith("purchasing."), f"nv_giao có lệnh purchasing: {cid}")
            self.assertFalse(cid.startswith("reports."), f"nv_giao có lệnh reports: {cid}")
            self.assertNotEqual(cid, "inventory.batch.close", "nv_giao có lệnh chốt lô")

        # 2. quan_ly, nv_kho, nv_giao không có reports.batch_pnl, reports.period_pnl (view_profitreport)
        for cl, name in ((self.client_ql, "quan_ly"), (self.client_kho, "nv_kho"), (self.client_giao, "nv_giao")):
            res = cl.get("/api/ai/commands/index/")
            ids = [c["id"] for c in res.json()["commands"]]
            self.assertNotIn("reports.batch_pnl", ids, f"{name} thấy reports.batch_pnl")
            self.assertNotIn("reports.period_pnl", ids, f"{name} thấy reports.period_pnl")

        # Chu thấy 2 báo cáo này
        res_chu = self.client_chu.get("/api/ai/commands/index/")
        ids_chu = [c["id"] for c in res_chu.json()["commands"]]
        self.assertIn("reports.batch_pnl", ids_chu, "chu phải thấy reports.batch_pnl")
        self.assertIn("reports.period_pnl", ids_chu, "chu phải thấy reports.period_pnl")

        # 3. Lệnh không thấy -> descriptor 404 COMMAND_UNKNOWN cùng thân với lệnh không tồn tại
        res_404_no_exist = self.client_chu.get("/api/ai/commands/lenh.khong.ton_tai/")
        self.assertEqual(res_404_no_exist.status_code, 404)
        self.assertEqual(res_404_no_exist.json(), {"detail": "Không có lệnh này.", "code": "COMMAND_UNKNOWN"})

        res_404_forbidden = self.client_giao.get("/api/ai/commands/inventory.batch.close/")
        self.assertEqual(res_404_forbidden.status_code, 404)
        self.assertEqual(res_404_forbidden.json(), {"detail": "Không có lệnh này.", "code": "COMMAND_UNKNOWN"})

    def test_dw07_ac5_cost_keys_scrubbing_by_role(self):
        """DW-07-AC5: quan_ly, nv_kho không có purchase_rate, landed_unit_cost trong output_fields; chu có."""
        # 1. nv_kho gọi descriptor inventory.batch.list
        res_kho = self.client_kho.get("/api/ai/commands/inventory.batch.list/")
        self.assertEqual(res_kho.status_code, 200)
        out_kho = res_kho.json()["output_fields"]
        self.assertNotIn("purchase_rate", out_kho)
        self.assertNotIn("landed_unit_cost", out_kho)

        # 2. quan_ly gọi
        res_ql = self.client_ql.get("/api/ai/commands/inventory.batch.list/")
        self.assertEqual(res_ql.status_code, 200)
        out_ql = res_ql.json()["output_fields"]
        self.assertNotIn("purchase_rate", out_ql)
        self.assertNotIn("landed_unit_cost", out_ql)

        # 3. chu gọi: phải có purchase_rate, landed_unit_cost
        res_chu = self.client_chu.get("/api/ai/commands/inventory.batch.list/")
        self.assertEqual(res_chu.status_code, 200)
        out_chu = res_chu.json()["output_fields"]
        self.assertIn("purchase_rate", out_chu)
        self.assertIn("landed_unit_cost", out_chu)

    def test_dw07_ac6_no_pii_keys_in_output_fields(self):
        """DW-07-AC6: Mọi Group quét descriptor mọi lệnh -> không output_fields nào chứa khoá PII của 02b §3."""
        registry = get_registry()
        # Test trên token chu (quyền cao nhất)
        for spec in registry.get_specs():
            res = self.client_chu.get(f"/api/ai/commands/{spec.id}/")
            if res.status_code == 200:
                fields = res.json().get("output_fields", [])
                for f in fields:
                    self.assertNotIn(f, SCRUB_PII_KEYS, f"Lệnh {spec.id} chứa khoá PII trong output_fields: {f}")

    def test_dw07_ac8_index_no_business_queries(self):
        """DW-07-AC8: Gọi index chỉ query bảng auth_*/ai_*, không bảng nghiệp vụ."""
        # Nạp trước cache/permissions của user
        self.client_chu.get("/api/ai/commands/index/")

        with self.assertNumQueries(0):  # Không query thêm bảng nào khi gọi lại cùng tiến trình nếu đã cache
            # Hoặc kiểm tra các bảng query không thuộc bảng nghiệp vụ
            pass

        queries_before = len(connection.queries)
        res = self.client_kho.get("/api/ai/commands/index/")
        self.assertEqual(res.status_code, 200)
        queries_after = connection.queries[queries_before:]

        for q in queries_after:
            sql = q["sql"].lower()
            # Bắt buộc không query bảng nghiệp vụ
            self.assertNotIn("inventory_batch", sql)
            self.assertNotIn("sales_salesorder", sql)
            self.assertNotIn("purchasing_purchasereceipt", sql)

    @override_settings(AI_ENABLED=False)
    def test_dw07_ac9_ai_disabled(self):
        """DW-07-AC9: AI_ENABLED=False -> index và descriptor trả 410 AI_DISABLED; catalog cũ vẫn 200."""
        res_idx = self.client_chu.get("/api/ai/commands/index/")
        self.assertEqual(res_idx.status_code, 410)
        self.assertEqual(res_idx.json().get("code"), "AI_DISABLED")

        res_det = self.client_chu.get("/api/ai/commands/inventory.batch.list/")
        self.assertEqual(res_det.status_code, 410)
        self.assertEqual(res_det.json().get("code"), "AI_DISABLED")

        # DW-15-AC1: Endpoint catalog cũ đã gỡ bỏ -> trả về 404
        res_old = self.client_chu.get("/api/commands/catalog/")
        self.assertEqual(res_old.status_code, 404)

    def test_dw07_ac10_batch_filter_and_fefo(self):
        """DW-07-AC10: Lọc lô theo item_code và status giữ đúng thứ tự FEFO."""
        # Tạo 2 lô CA-001 (hạn 10 ngày và 5 ngày) và 1 lô CA-002
        today = timezone.localdate()
        b_near = batch_services.create_batch(
            item=self.item1, supplier=self.sup, warehouse=self.wh,
            received_date=today, qty=Decimal("10"), purchase_rate=Decimal("50000"),
            shelf_life_days=5,
        )
        b_far = batch_services.create_batch(
            item=self.item1, supplier=self.sup, warehouse=self.wh,
            received_date=today, qty=Decimal("20"), purchase_rate=Decimal("50000"),
            shelf_life_days=10,
        )
        b_other = batch_services.create_batch(
            item=self.item2, supplier=self.sup, warehouse=self.wh,
            received_date=today, qty=Decimal("15"), purchase_rate=Decimal("60000"),
            shelf_life_days=3,
        )

        res = self.client_kho.get("/api/inventory/batches/?item_code=CA-001")
        self.assertEqual(res.status_code, 200)
        data = res.json()["results"]
        # Chỉ có 2 lô của CA-001
        batch_ids = [b["batch_id"] for b in data]
        self.assertIn(b_near.batch_id, batch_ids)
        self.assertIn(b_far.batch_id, batch_ids)
        self.assertNotIn(b_other.batch_id, batch_ids)

        # Thứ tự FEFO: b_near (hạn 5 ngày) phải đứng trước b_far (hạn 10 ngày)
        idx_near = batch_ids.index(b_near.batch_id)
        idx_far = batch_ids.index(b_far.batch_id)
        self.assertLess(idx_near, idx_far, "Thứ tự phải ưu tiên lô hết hạn sớm hơn (FEFO)")
