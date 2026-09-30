"""
Kiểm thử toàn diện cho Story DW-19: Mức B: AI tự ghi, báo ngay, hoàn tác trong 10 phút.
Bao phủ các tiêu chí DW-19-AC1 đến DW-19-AC10.
"""
import datetime
from decimal import Decimal
import unittest.mock
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction, AiConfigVersion, AiPolicyVersion
from apps.ai.registry.discovery import get_registry
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import PurchaseReceipt, Supplier
from apps.ai import command_groups
from apps.accounts import roles

User = get_user_model()


@override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="B")
class DW19LevelBTestCase(TestCase):
    def setUp(self):
        self.user_chu = make_user("chu1", roles.OWNER)
        self.user_ql = make_user("ql1", roles.MANAGER)
        self.user_kho = make_user("kho1", roles.WAREHOUSE_STAFF)
        self.user_kho2 = make_user("kho2", roles.WAREHOUSE_STAFF)
        self.user_giao = make_user("giao1", roles.DELIVERY_STAFF)

        self.client_chu = client_for(self.user_chu)
        self.client_ql = client_for(self.user_ql)
        self.client_kho = client_for(self.user_kho)
        self.client_kho2 = client_for(self.user_kho2)
        self.client_giao = client_for(self.user_giao)

        self.group = ItemGroup.objects.create(name="Cá biển")
        self.item1 = Item.objects.create(
            code="CA-DW19-1",
            name="Cá ngừ",
            item_group=self.group,
            shelf_life_in_days=60,
            is_active=True,
        )
        self.sup = Supplier.objects.create(name="Cảng Vũng Tàu", is_active=True)
        self.wh = Warehouse.objects.create(name="Kho lạnh B")

        # Cấu hình mức B cho user kho1
        self.config_kho1 = AiConfigVersion.objects.create(
            user=self.user_kho,
            version=1,
            group_levels={command_groups.PURCHASING: {"read": "A", "write": "B"}},
            overrides={"purchasing.purchasereceipt.nhap_lo": "B"},
            limits={"purchasing.purchasereceipt.nhap_lo": {"kg": "150", "vnd": "30000000"}},
            created_by=self.user_kho,
        )
        self.config_ql = AiConfigVersion.objects.create(
            user=self.user_ql,
            version=1,
            group_levels={command_groups.PURCHASING: {"read": "A", "write": "C"}, command_groups.SALES: {"read": "A", "write": "C"}},
            created_by=self.user_ql,
        )

        get_registry().build(force=True)

    def test_dw19_ac1_call_level_b_nhap_lo_success(self):
        """DW-19-AC1: Staging, NV kho đặt B, phiếu 50 kg -> outcome=done, level=B, undo_until=+10m."""
        url = "/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/"
        payload = {
            "args": {
                "supplier": self.sup.id,
                "received_date": timezone.now().date().isoformat(),
                "warehouse": self.wh.id,
                "lines": [
                    {"item_code": self.item1.code, "qty": "50.000", "rate": "80000.00", "shelf_life_days": 30}
                ],
            }
        }
        res = self.client_kho.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["outcome"], "done")
        self.assertEqual(res.data["level"], "B")
        self.assertIn("action_id", res.data)
        self.assertIn("undo_until", res.data)

        # Kiểm tra chứng từ thật đã tạo trong DB
        receipt = PurchaseReceipt.objects.filter(created_by=self.user_kho).first()
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.status, PurchaseReceipt.Status.SUBMITTED)

        batches = Batch.objects.filter(supplier=self.sup)
        self.assertEqual(batches.count(), 1)
        self.assertEqual(batches.first().status, Batch.Status.DRAFT)

        # Kiểm tra AiAction
        action = AiAction.objects.get(id=res.data["action_id"])
        self.assertEqual(action.status, AiAction.Status.DONE)
        self.assertEqual(action.level, AiAction.Level.B)
        self.assertIsNotNone(action.undo_until)

        # Kiểm tra AuditLog
        audit = AuditLog.objects.filter(action="execute_purchasing.purchasereceipt.nhap_lo").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor_kind, "ai")
        self.assertEqual(audit.ai_actor, self.user_kho)
        self.assertEqual(audit.ai_level, "B")
        self.assertEqual(audit.ai_config_version, self.config_kho1.version)

    @override_settings(AI_WRITE_LEVELS_ALLOWED="C")
    def test_dw19_ac2_production_blocks_level_b(self):
        """DW-19-AC2: Production (AI_WRITE_LEVELS_ALLOWED=C), PUT B -> 400 BR-AI-27."""
        # GET my-config -> choices không có B
        res_get = self.client_kho.get("/api/ai/my-config/")
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertNotIn("B", res_get.data["write_levels_allowed"])

        # PUT override B -> 400 BR-AI-27
        put_payload = {
            "base_version": self.config_kho1.version,
            "groups": {command_groups.PURCHASING: {"read": "A", "write": "C"}},
            "overrides": {"purchasing.purchasereceipt.nhap_lo": "B"},
            "acknowledge_responsibility": True,
        }
        res_put = self.client_kho.put("/api/ai/my-config/", put_payload, format="json")
        self.assertEqual(res_put.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_put.data.get("code"), "BR-AI-27")

    def test_dw19_ac3_undo_within_window_cancels_receipt(self):
        """DW-19-AC3: Trong 10 phút, POST undo -> phiếu và lô CANCELLED, AiAction UNDONE."""
        # 1. Tạo phiếu bằng call mức B
        url_call = "/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/"
        payload = {
            "args": {
                "supplier": self.sup.id,
                "received_date": timezone.now().date().isoformat(),
                "warehouse": self.wh.id,
                "lines": [
                    {"item_code": self.item1.code, "qty": "40.000", "rate": "75000.00", "shelf_life_days": 30}
                ],
            }
        }
        res_call = self.client_kho.post(url_call, payload, format="json")
        action_id = res_call.data["action_id"]

        receipt = PurchaseReceipt.objects.get(created_by=self.user_kho)
        self.assertEqual(receipt.status, PurchaseReceipt.Status.SUBMITTED)

        # 2. Gọi undo
        url_undo = f"/api/ai/actions/{action_id}/undo/"
        res_undo = self.client_kho.post(url_undo, format="json")
        self.assertEqual(res_undo.status_code, status.HTTP_200_OK)
        self.assertEqual(res_undo.data["outcome"], "undone")

        # Kiểm tra phiếu và lô đã chuyển CANCELLED
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, PurchaseReceipt.Status.CANCELLED)
        batch = Batch.objects.get(supplier=self.sup)
        self.assertEqual(batch.status, Batch.Status.CANCELLED)

        # Kiểm tra AiAction UNDONE
        action = AiAction.objects.get(id=action_id)
        self.assertEqual(action.status, AiAction.Status.UNDONE)
        self.assertEqual(action.decided_by, self.user_kho)

        # Kiểm tra AuditLog hoàn tác
        audit = AuditLog.objects.filter(action=f"undo_{action.command}").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.user_kho)

    def test_dw19_ac4_undo_expired_window_or_published_batch(self):
        """DW-19-AC4: Quá 10 phút -> 410; hoặc lô đã publish -> 400 BR-MH-07."""
        url_call = "/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/"
        payload = {
            "args": {
                "supplier": self.sup.id,
                "received_date": timezone.now().date().isoformat(),
                "warehouse": self.wh.id,
                "lines": [
                    {"item_code": self.item1.code, "qty": "30.000", "rate": "80000.00", "shelf_life_days": 30}
                ],
            }
        }
        res_call = self.client_kho.post(url_call, payload, format="json")
        action_id = res_call.data["action_id"]

        # Kịch bản 1: Quá 10 phút
        action = AiAction.objects.get(id=action_id)
        action.undo_until = timezone.now() - datetime.timedelta(seconds=1)
        action.save(update_fields=["undo_until"])

        url_undo = f"/api/ai/actions/{action_id}/undo/"
        res_undo1 = self.client_kho.post(url_undo, format="json")
        self.assertEqual(res_undo1.status_code, status.HTTP_410_GONE)
        self.assertEqual(res_undo1.data["code"], "AI_UNDO_WINDOW_CLOSED")

        # Kịch bản 2: Lô đã mở bán (SELLING)
        action.undo_until = timezone.now() + datetime.timedelta(minutes=5)
        action.save(update_fields=["undo_until"])

        batch = Batch.objects.get(supplier=self.sup)
        batch.status = Batch.Status.SELLING
        batch.save(update_fields=["status"])

        res_undo2 = self.client_kho.post(url_undo, format="json")
        self.assertEqual(res_undo2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_undo2.data["code"], "BR-MH-07")

    def test_dw19_ac5_downgrade_to_c_on_limits(self):
        """DW-19-AC5: Vượt ngưỡng kg (180kg > 150kg) hoặc lần thứ 21 -> hạ mức C (proposal)."""
        url_call = "/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/"

        # 1. Vượt ngưỡng kg (180 kg > 150 kg của user_kho)
        payload_over_kg = {
            "args": {
                "supplier": self.sup.id,
                "received_date": timezone.now().date().isoformat(),
                "warehouse": self.wh.id,
                "lines": [
                    {"item_code": self.item1.code, "qty": "180.000", "rate": "80000.00", "shelf_life_days": 30}
                ],
            }
        }
        res_kg = self.client_kho.post(url_call, payload_over_kg, format="json")
        self.assertEqual(res_kg.status_code, status.HTTP_200_OK)
        self.assertEqual(res_kg.data["outcome"], "proposal")
        self.assertEqual(res_kg.data["level"], "C")
        self.assertEqual(res_kg.data["downgrade_reason"]["code"], "AI_LIMIT_KG")
        # Chứng từ chưa được tạo
        self.assertEqual(PurchaseReceipt.objects.count(), 0)

        # 2. Vượt hạn mức 20 lần trong ngày
        for i in range(20):
            AiAction.objects.create(
                command="purchasing.purchasereceipt.nhap_lo",
                kind=AiAction.Kind.WRITE,
                status=AiAction.Status.DONE,
                level=AiAction.Level.B,
                owner=self.user_kho,
            )

        payload_within_limit = {
            "args": {
                "supplier": self.sup.id,
                "received_date": timezone.now().date().isoformat(),
                "warehouse": self.wh.id,
                "lines": [
                    {"item_code": self.item1.code, "qty": "20.000", "rate": "80000.00", "shelf_life_days": 30}
                ],
            }
        }
        res_daily = self.client_kho.post(url_call, payload_within_limit, format="json")
        self.assertEqual(res_daily.status_code, status.HTTP_200_OK)
        self.assertEqual(res_daily.data["outcome"], "proposal")
        self.assertEqual(res_daily.data["level"], "C")
        self.assertEqual(res_daily.data["downgrade_reason"]["code"], "AI_DAILY_LIMIT")

    def test_dw19_ac6_h5_atomic_rollback_on_audit_error(self):
        """DW-19-AC6 (H5): Ép ghi AuditLog lỗi -> rollback toàn bộ, không tạo phiếu/lô."""
        url_call = "/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/"
        payload = {
            "args": {
                "supplier": self.sup.id,
                "received_date": timezone.now().date().isoformat(),
                "warehouse": self.wh.id,
                "lines": [
                    {"item_code": self.item1.code, "qty": "50.000", "rate": "80000.00", "shelf_life_days": 30}
                ],
            }
        }

        with unittest.mock.patch("apps.ai.execution.pipeline.record_audit", side_effect=RuntimeError("Simulated Audit Failure")):
            try:
                self.client_kho.post(url_call, payload, format="json")
            except RuntimeError:
                pass

        # Bất biến H5: Không chứng từ nào được tạo trong DB
        self.assertEqual(PurchaseReceipt.objects.count(), 0)
        self.assertEqual(Batch.objects.count(), 0)
        self.assertEqual(AiAction.objects.filter(level=AiAction.Level.B).count(), 0)

    def test_dw19_ac7_force_c_commands_cannot_be_set_to_b(self):
        """DW-19-AC7: Lệnh trần C ép (như sales.refund.create_refund) PUT B -> 400 BR-AI-19."""
        put_payload = {
            "base_version": self.config_ql.version,
            "groups": {command_groups.PURCHASING: {"read": "A", "write": "C"}, command_groups.SALES: {"read": "A", "write": "C"}},
            "overrides": {"sales.refund.create_refund": "B"},
            "acknowledge_responsibility": True,
        }
        res = self.client_ql.put("/api/ai/my-config/", put_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "BR-AI-19")
        self.assertIn("giới hạn trần tối đa là C", res.data.get("detail", ""))

    def test_dw19_ac8_cost_price_scrubbed_in_b_result(self):
        """DW-19-AC8: Người thiếu view_costprice (nv_kho) gọi mức B -> result không chứa giá vốn."""
        url_call = "/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/"
        payload = {
            "args": {
                "supplier": self.sup.id,
                "received_date": timezone.now().date().isoformat(),
                "warehouse": self.wh.id,
                "lines": [
                    {"item_code": self.item1.code, "qty": "50.000", "rate": "80000.00", "shelf_life_days": 30}
                ],
            }
        }
        res = self.client_kho.post(url_call, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res_str = str(res.data)
        self.assertNotIn("purchase_rate", res_str)
        self.assertNotIn("landed_unit_cost", res_str)
        self.assertNotIn("rate", res_str)

    @override_settings(AI_ENABLED=False)
    def test_dw19_ac10_undo_ai_disabled_still_allowed(self):
        """DW-19-AC10 (đổi theo P8 SR-22 / F10): AI tắt vẫn được hoàn tác, không còn 410 AI_DISABLED.
        Việc không tồn tại -> 404 NOT_FOUND. Ca hoàn tác thật khi AI tắt: test_p8_lo7_undo."""
        res = self.client_kho.post("/api/ai/actions/00000000-0000-0000-0000-000000000000/undo/", format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["code"], "NOT_FOUND")
