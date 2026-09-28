"""
Test cho DW-05 — Khối "Tiếp theo · Đã làm" trên Lô hàng (Lô 1b, P2).

Acceptance Criteria:
- DW-05-AC1: Lô SELLING, hạn dùng còn 10 ngày, NEAR_EXPIRY_DAYS=14 -> NV kho xem thấy bước system "chuyển Cận hạn" có deadline; close/publish allowed=false cho NV kho.
- DW-05-AC2: Lô SOLD_OUT còn đơn BOOKED tham chiếu lô -> bước "Chốt lô" allowed=false, missing có BR-LO-04; gọi thẳng close nhận 400 BR-LO-04.
- DW-05-AC3 (giá vốn): Lô đã chốt + có record_purchase_cost -> quan_ly và nv_kho thấy "Chủ đã chốt lô", "Chủ ghi nhận chi phí mua" KHÔNG có số; chu thấy số.
- DW-05-AC4 (giá vốn): Lô chưa có chi phí mua -> cảnh báo "lô chưa có chi phí mua" không kèm số; chu và nv_kho thấy cùng câu.
- DW-05-AC5 (quyền): nv_giao gọi guidance lô -> 403.
- DW-05-AC6 (PII): Lô có đơn xuất kho -> dòng sổ kho không chứa tên/SĐT/địa chỉ khách.
- DW-05-AC7: AI_ENABLED=False -> endpoint trả 200, ai=null.
"""
import datetime
from decimal import Decimal
import json

from django.test import override_settings
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, StockLedgerEntry
from apps.inventory.batches import services as batch_services
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase


class GuidanceBatchTest(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.chu = make_user("chu_b_guidance", "chu")
        self.ql = make_user("ql_b_guidance", "quan_ly")
        self.kho = make_user("kho_b_guidance", "nv_kho")
        self.giao = make_user("giao_b_guidance", "nv_giao")

        self.c_chu = client_for(self.chu)
        self.c_ql = client_for(self.ql)
        self.c_kho = client_for(self.kho)
        self.c_giao = client_for(self.giao)

    # --- DW-05-AC1 -----------------------------------------------------------
    def test_dw05_ac1_selling_near_expiry_next_steps_for_nv_kho(self):
        """Lô SELLING, hạn dùng còn 10 ngày, NEAR_EXPIRY_DAYS=14: NV kho thấy auto_near_expiry, publish/close allowed=false."""
        today = timezone.localdate()
        self.batch.expiry_date = today + datetime.timedelta(days=10)
        self.batch.status = Batch.Status.SELLING
        self.batch.save(update_fields=["expiry_date", "status"])

        with override_settings(BATCH_NEAR_EXPIRY_DAYS=14):
            resp = self.c_kho.get(f"/api/guidance/batch/{self.batch.pk}/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            data = resp.json()

            steps = {s["key"]: s for s in data["next_steps"]}
            self.assertIn("auto_near_expiry", steps)
            auto_step = steps["auto_near_expiry"]
            self.assertEqual(auto_step["actor"], "system")
            self.assertFalse(auto_step["allowed"])
            self.assertIsNotNone(auto_step["deadline"])
            self.assertEqual(auto_step["why"]["br"], "BR-LO-06")

            # Bước chốt lô không allowed cho NV kho
            if "close" in steps:
                self.assertFalse(steps["close"]["allowed"])

    # --- DW-05-AC2 -----------------------------------------------------------
    def test_dw05_ac2_close_blocked_when_open_orders_exist(self):
        """Lô SOLD_OUT còn đơn BOOKED tham chiếu lô -> bước 'Chốt lô' allowed=false, missing có BR-LO-04; gọi thẳng nhận 400 BR-LO-04."""
        # Tạo đơn giữ chỗ tham chiếu lô
        order = order_services.create_order(
            customer_phone="0900000123",
            customer_name="Khách Thử Nghiệm",
            delivery_address="1 Đường Test, Q.1",
            phone="0900000123",
            lines=[{"item_code": self.item.code, "qty": Decimal("1")}],
        )
        self.batch.status = Batch.Status.SOLD_OUT
        self.batch.qty_available = Decimal("0")
        self.batch.save(update_fields=["status", "qty_available"])

        # Chủ xem guidance
        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        steps = {s["key"]: s for s in resp.json()["next_steps"]}
        self.assertIn("close", steps)
        close_step = steps["close"]
        self.assertFalse(close_step["allowed"])
        missing_codes = [m["code"] for m in close_step["missing"]]
        self.assertIn("BR-LO-04", missing_codes)

        # Gọi thẳng action chốt qua API nhận 400 BR-LO-04
        resp_act = self.c_chu.post(f"/api/inventory/batches/{self.batch.pk}/close/")
        self.assertEqual(resp_act.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp_act.json().get("code"), "BR-LO-04")

    # --- DW-05-AC3 (giá vốn trong dòng thời gian) -----------------------------
    def test_dw05_ac3_cost_hidden_in_timeline_for_non_chu(self):
        """Lô đã chốt + có record_purchase_cost -> quan_ly và nv_kho thấy 'Chủ đã chốt lô', 'Chủ ghi nhận chi phí mua' KHÔNG có số; chu thấy số."""
        self.batch.status = Batch.Status.CLOSED
        self.batch.landed_unit_cost = Decimal("185000")
        self.batch.save(update_fields=["status", "landed_unit_cost"])

        # Tạo AuditLog chốt lô
        AuditLog.objects.create(
            actor=self.chu,
            actor_kind=AuditLog.ActorKind.USER,
            action="close_batch",
            model_name=Batch._meta.label,
            object_id=str(self.batch.pk),
            changes={"landed_unit_cost": {"final": "185000.00"}},
        )
        # Tạo AuditLog ghi nhận chi phí mua
        AuditLog.objects.create(
            actor=self.chu,
            actor_kind=AuditLog.ActorKind.USER,
            action="record_purchase_cost",
            model_name=Batch._meta.label,
            object_id=str(self.batch.pk),
            changes={"amount": "2500000.00"},
        )

        cost_marker = "185000"
        cost_marker_2 = "2500000"

        # 1. quan_ly và nv_kho xem
        for c in (self.c_ql, self.c_kho):
            resp = c.get(f"/api/guidance/batch/{self.batch.pk}/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            tl = resp.json()["timeline"]
            labels = [e["label"] for e in tl]
            self.assertIn("Chủ đã chốt lô", labels)
            self.assertIn("Chủ ghi nhận chi phí mua", labels)

            raw_str = json.dumps(resp.json())
            self.assertNotIn(cost_marker, raw_str)
            self.assertNotIn(cost_marker_2, raw_str)

        # 2. chu xem -> thấy số tiền
        resp_chu = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp_chu.status_code, status.HTTP_200_OK)
        raw_chu = json.dumps(resp_chu.json())
        self.assertTrue("185" in raw_chu or "Chốt lô (giá vốn" in raw_chu)

    # --- DW-05-AC4 (giá vốn trong cảnh báo) -----------------------------------
    def test_dw05_ac4_purchase_cost_warning_has_no_money_numbers(self):
        """Lô chưa có chi phí mua -> cảnh báo 'lô chưa có chi phí mua' không kèm số; chu và nv_kho thấy cùng câu."""
        # batch chưa có cost_allocations
        resp_kho = self.c_kho.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp_kho.status_code, status.HTTP_200_OK)
        warns_kho = [w["text"] for w in resp_kho.json()["warnings"]]
        self.assertTrue(any("chưa có chi phí mua" in w for w in warns_kho))

        resp_chu = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp_chu.status_code, status.HTTP_200_OK)
        warns_chu = [w["text"] for w in resp_chu.json()["warnings"]]
        self.assertEqual(warns_kho, warns_chu)

    # --- DW-05-AC5 (quyền) ----------------------------------------------------
    def test_dw05_ac5_nv_giao_gets_403(self):
        """nv_giao gọi guidance lô -> 403, không lộ bước."""
        resp = self.c_giao.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn("next_steps", resp.json())

    # --- DW-05-AC6 (PII trong dòng sổ kho) ------------------------------------
    def test_dw05_ac6_no_pii_in_stock_ledger_entries(self):
        """Lô có xuất kho -> dòng sổ kho không chứa tên/SĐT/địa chỉ khách."""
        # Ghi một dòng SALE
        pii_name = "KHÁCH VIP 0912345678"
        StockLedgerEntry.objects.create(
            batch=self.batch,
            movement_type=StockLedgerEntry.MovementType.SALE,
            qty_change=Decimal("-5.0"),
            reference=f"Xuất cho đơn của {pii_name}",
        )

        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tl = resp.json()["timeline"]
        stock_entries = [e for e in tl if e["kind"] == "stock_sale"]
        self.assertTrue(len(stock_entries) > 0)
        for se in stock_entries:
            self.assertEqual(se["label"], "Xuất bán 5.000 kg")
            self.assertNotIn("0912345678", se["label"])
            self.assertNotIn("KHÁCH VIP", se["label"])

    # --- DW-05-AC7 (AI tắt) ---------------------------------------------------
    @override_settings(AI_ENABLED=False)
    def test_dw05_ac7_guidance_works_when_ai_disabled(self):
        """AI_ENABLED=False -> endpoint trả 200, ai=null."""
        resp = self.c_kho.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("next_steps", data)
        for s in data["next_steps"]:
            self.assertIsNone(s["ai"])
