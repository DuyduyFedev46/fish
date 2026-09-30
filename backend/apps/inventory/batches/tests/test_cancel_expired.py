"""
Test cho Story DW-06 — Chủ huỷ lô quá hạn (EXPIRED -> CANCELLED, hạch toán lỗ).

Acceptance Criteria:
- DW-06-AC1: Lô EXPIRED còn 5 kg -> Chủ bấm "Huỷ lô", xác nhận -> lô CANCELLED;
  StockLedgerEntry ghi xuất huỷ 5 kg; lãi lỗ lô có dòng lỗ hết hạn = 5 × landed_unit_cost;
  profit không đổi so với trước huỷ; AuditLog 1 dòng (BR-LO-03, BR-PQ-05, TL-4).
- DW-06-AC2 (lỗi): Lô SELLING hoặc NEAR_EXPIRY gọi API -> 400 BR-LO-03 ("Chỉ huỷ được lô Quá hạn."),
  không đổi dữ liệu.
- DW-06-AC3 (song song / khoá): Hai request huỷ cùng lô -> đúng 1 request thành công,
  sổ kho có đúng 1 dòng huỷ (atomic + select_for_update).
- DW-06-AC4 (quyền): quan_ly, nv_kho, nv_giao gọi API -> 403; khách chưa đăng nhập -> 401;
  dữ liệu không đổi.
- DW-06-AC5 (giá vốn): Sau khi huỷ, quan_ly xem dòng thời gian lô -> thấy "Chủ đã huỷ lô",
  không có số lỗ (Bất biến 1).
- DW-06-AC6 (guidance): Lô EXPIRED -> Chủ xem khối Tiếp theo có bước "Huỷ lô" allowed=true;
  sau khi huỷ, bước kế là "Chốt lô".
- DW-06-AC7 (AI tắt): AI_ENABLED=false -> huỷ lô chạy bình thường (BR-AI-10).
- Migration test: Group chu có quyền cancel_expired_batch; 3 Group còn lại không có.
"""
from decimal import Decimal
import json

from django.contrib.auth.models import Group
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockLedgerEntry
from apps.reports import services as report_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.accounts import roles


class CancelExpiredBatchTest(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.chu = make_user("chu_cancel_exp", roles.OWNER)
        self.ql = make_user("ql_cancel_exp", roles.MANAGER)
        self.kho = make_user("kho_cancel_exp", roles.WAREHOUSE_STAFF)
        self.giao = make_user("giao_cancel_exp", roles.DELIVERY_STAFF)

        self.c_chu = client_for(self.chu)
        self.c_ql = client_for(self.ql)
        self.c_kho = client_for(self.kho)
        self.c_giao = client_for(self.giao)

        # Chuẩn bị một lô EXPIRED còn đúng 5 kg
        self.batch.status = Batch.Status.EXPIRED
        self.batch.qty_available = Decimal("5.000")
        self.batch.qty_reserved = Decimal("0")
        self.batch.purchase_rate = Decimal("50000")
        self.batch.landed_unit_cost = Decimal("50000")
        self.batch.save(update_fields=[
            "status", "qty_available", "qty_reserved", "purchase_rate", "landed_unit_cost"
        ])

    # --- DW-06-AC1 -----------------------------------------------------------
    def test_dw06_ac1_cancel_expired_success(self):
        """Lô EXPIRED còn 5 kg: huỷ thành công -> CANCELLED, 1 dòng WRITE_OFF, PnL expired_cost, profit không đổi."""
        # PnL trước khi huỷ
        pnl_before = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(pnl_before["expired_qty"], Decimal("0"))
        self.assertEqual(pnl_before["expired_cost"], Decimal("0"))
        profit_before = pnl_before["profit"]

        # Gọi API huỷ lô bằng token Chủ
        resp = self.c_chu.post(f"/api/inventory/batches/{self.batch.pk}/cancel-expired/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["status"], Batch.Status.CANCELLED)

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, Batch.Status.CANCELLED)
        self.assertEqual(self.batch.qty_available, Decimal("0"))

        # Sổ kho ghi nhận đúng 1 dòng WRITE_OFF âm 5 kg
        write_offs = StockLedgerEntry.objects.filter(
            batch=self.batch,
            movement_type=StockLedgerEntry.MovementType.WRITE_OFF,
        )
        self.assertEqual(write_offs.count(), 1)
        entry = write_offs.first()
        self.assertEqual(entry.qty_change, Decimal("-5.000"))
        self.assertEqual(entry.created_by, self.chu)

        # AuditLog có đúng 1 dòng cancel_expired_batch
        audits = AuditLog.objects.filter(
            model_name=Batch._meta.label,
            object_id=str(self.batch.pk),
            action="cancel_expired_batch",
        )
        self.assertEqual(audits.count(), 1)
        audit_entry = audits.first()
        self.assertEqual(audit_entry.actor, self.chu)
        self.assertEqual(audit_entry.changes.get("status", {}).get("to"), Batch.Status.CANCELLED)

        # PnL sau khi huỷ: expired_qty = 5, expired_cost = 5 * landed_unit_cost, profit KHÔNG ĐỔI (TL-4)
        pnl_after = report_services.batch_pnl(batch=self.batch)
        self.assertEqual(pnl_after["expired_qty"], Decimal("5.000"))
        self.assertEqual(pnl_after["expired_cost"], Decimal("250000.0000"))
        self.assertEqual(pnl_after["profit"], profit_before)
        self.assertEqual(pnl_after["total_cost"], pnl_before["total_cost"])

    # --- DW-06-AC2 (lỗi khi sai trạng thái) -----------------------------------
    def test_dw06_ac2_cancel_non_expired_rejected_br_lo_03(self):
        """Lô SELLING hoặc NEAR_EXPIRY gọi huỷ -> 400 BR-LO-03 'Chỉ huỷ được lô Quá hạn.', không đổi dữ liệu."""
        for invalid_status in (Batch.Status.SELLING, Batch.Status.NEAR_EXPIRY, Batch.Status.DRAFT):
            self.batch.status = invalid_status
            self.batch.save(update_fields=["status"])

            resp = self.c_chu.post(f"/api/inventory/batches/{self.batch.pk}/cancel-expired/")
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
            data = resp.json()
            self.assertEqual(data.get("code"), "BR-LO-03")
            self.assertEqual(data.get("detail"), "Chỉ huỷ được lô Quá hạn.")

            self.batch.refresh_from_db()
            self.assertEqual(self.batch.status, invalid_status)
            self.assertEqual(self.batch.qty_available, Decimal("5.000"))

    # --- DW-06-AC3 (song song / gọi lặp lại) ---------------------------------
    def test_dw06_ac3_repeat_cancel_rejected(self):
        """Huỷ lần 2 trên cùng một lô -> lần 2 nhận 400 BR-LO-03, sổ kho chỉ có đúng 1 dòng huỷ."""
        # Lần 1: thành công
        resp1 = self.c_chu.post(f"/api/inventory/batches/{self.batch.pk}/cancel-expired/")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)

        # Lần 2: thất bại vì lô đã thành CANCELLED
        resp2 = self.c_chu.post(f"/api/inventory/batches/{self.batch.pk}/cancel-expired/")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp2.json().get("code"), "BR-LO-03")

        write_offs = StockLedgerEntry.objects.filter(
            batch=self.batch,
            movement_type=StockLedgerEntry.MovementType.WRITE_OFF,
        )
        self.assertEqual(write_offs.count(), 1)

    # --- DW-06-AC4 (phân quyền 4 Group + khách) ------------------------------
    def test_dw06_ac4_permissions_matrix(self):
        """quan_ly, nv_kho, nv_giao gọi API nhận 403; khách chưa đăng nhập nhận 401."""
        for c in (self.c_ql, self.c_kho, self.c_giao):
            resp = c.post(f"/api/inventory/batches/{self.batch.pk}/cancel-expired/")
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
            self.batch.refresh_from_db()
            self.assertEqual(self.batch.status, Batch.Status.EXPIRED)

        # Khách ẩn danh
        anon_resp = self.client.post(f"/api/inventory/batches/{self.batch.pk}/cancel-expired/")
        self.assertEqual(anon_resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- DW-06-AC5 (giá vốn trong dòng thời gian) -----------------------------
    def test_dw06_ac5_cost_hidden_in_timeline_for_quan_ly(self):
        """Sau khi huỷ, quan_ly xem dòng thời gian lô: thấy 'Chủ đã huỷ lô', không có số tiền lỗ."""
        # Chủ huỷ lô
        self.c_chu.post(f"/api/inventory/batches/{self.batch.pk}/cancel-expired/")

        # Quản lý xem guidance
        resp_ql = self.c_ql.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp_ql.status_code, status.HTTP_200_OK)
        data_ql = resp_ql.json()

        # Kiểm tra timeline của Quản lý: có "Chủ đã huỷ lô", chuỗi không có số tiền giá vốn (250000 hoặc 50000)
        timeline_labels = [e["label"] for e in data_ql["timeline"]]
        self.assertIn("Chủ đã huỷ lô", timeline_labels)
        raw_json_ql = json.dumps(data_ql)
        self.assertNotIn("250.000", raw_json_ql)
        self.assertNotIn("250000", raw_json_ql)
        self.assertNotIn("50.000", raw_json_ql)

        # Chủ xem guidance: thấy có số tiền lỗ
        resp_chu = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp_chu.status_code, status.HTTP_200_OK)
        labels_chu = [e["label"] for e in resp_chu.json()["timeline"]]
        self.assertTrue(any("Huỷ lô quá hạn" in lbl for lbl in labels_chu))

    # --- DW-06-AC6 (guidance trước và sau khi huỷ) ---------------------------
    def test_dw06_ac6_guidance_next_steps_expired_then_cancelled(self):
        """Lô EXPIRED có bước 'Huỷ lô' allowed=true; sau khi huỷ, bước kế là 'Chốt lô'."""
        # 1. Trước khi huỷ: lô EXPIRED
        resp = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        steps_before = {s["key"]: s for s in resp.json()["next_steps"]}
        self.assertIn("cancel_expired", steps_before)
        cancel_step = steps_before["cancel_expired"]
        self.assertTrue(cancel_step["allowed"])
        # P8 Lô 5 (SR-15): đổi nhãn thành "Xác nhận Đã huỷ phần tồn" (song song có "Xác nhận Đã trả NCC").
        self.assertEqual(cancel_step["label"], "Xác nhận Đã huỷ phần tồn")
        self.assertEqual(cancel_step["why"]["br"], "BR-LO-03")
        # P8 Lô 5 (SR-15, BR-LO-04): EXPIRED còn tồn vẫn hiện bước close nhưng chưa allowed (phải xử lý hết tồn).
        self.assertIn("close", steps_before)
        self.assertFalse(steps_before["close"]["allowed"])
        self.assertIn("BR-LO-04", [m["code"] for m in steps_before["close"]["missing"]])

        # Với NV kho: bước cancel_expired allowed=false
        resp_kho = self.c_kho.get(f"/api/guidance/batch/{self.batch.pk}/")
        steps_kho = {s["key"]: s for s in resp_kho.json()["next_steps"]}
        self.assertIn("cancel_expired", steps_kho)
        self.assertFalse(steps_kho["cancel_expired"]["allowed"])

        # 2. Thực hiện huỷ lô
        self.c_chu.post(f"/api/inventory/batches/{self.batch.pk}/cancel-expired/")

        # 3. Sau khi huỷ: lô CANCELLED -> bước kế là "close" (Chốt lô)
        resp_after = self.c_chu.get(f"/api/guidance/batch/{self.batch.pk}/")
        steps_after = {s["key"]: s for s in resp_after.json()["next_steps"]}
        self.assertNotIn("cancel_expired", steps_after)
        self.assertIn("close", steps_after)
        self.assertEqual(steps_after["close"]["label"], "Chốt lô")

    # --- DW-06-AC7 (AI tắt) --------------------------------------------------
    def test_dw06_ac7_cancel_expired_when_ai_disabled(self):
        """AI_ENABLED=false -> huỷ lô chạy bình thường (BR-AI-10)."""
        with override_settings(AI_ENABLED=False):
            resp = self.c_chu.post(f"/api/inventory/batches/{self.batch.pk}/cancel-expired/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.batch.refresh_from_db()
            self.assertEqual(self.batch.status, Batch.Status.CANCELLED)

    # --- Test migration gán quyền --------------------------------------------
    def test_migration_permissions_group_chu_only(self):
        """Data migration gán cancel_expired_batch cho đúng Group chu; quan_ly, nv_kho, nv_giao không có."""
        g_chu = Group.objects.get(name=roles.OWNER)
        g_ql = Group.objects.get(name=roles.MANAGER)
        g_kho = Group.objects.get(name=roles.WAREHOUSE_STAFF)
        g_giao = Group.objects.get(name=roles.DELIVERY_STAFF)

        perm_codename = "cancel_expired_batch"
        self.assertTrue(g_chu.permissions.filter(codename=perm_codename).exists())
        self.assertFalse(g_ql.permissions.filter(codename=perm_codename).exists())
        self.assertFalse(g_kho.permissions.filter(codename=perm_codename).exists())
        self.assertFalse(g_giao.permissions.filter(codename=perm_codename).exists())
