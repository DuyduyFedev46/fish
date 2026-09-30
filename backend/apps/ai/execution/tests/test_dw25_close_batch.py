"""
Test suite cho Story DW-25: AI của Chủ chốt lô (trì hoãn 30 phút) khi đủ điều kiện sàn (DW-25-AC1..AC7).
"""
import datetime
from decimal import Decimal
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction, AiPolicyVersion
from apps.ai.registry import get_registry
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import (
    Batch,
    StockLedgerEntry,
    StockReconciliation,
    Warehouse,
)
from apps.purchasing.models import (
    PurchaseCost,
    PurchaseCostAllocation,
    PurchaseInvoice,
    PurchaseReceipt,
    PurchaseReceiptLine,
    Supplier,
)
from apps.sales.models import Customer, SalesOrder, SalesOrderLine, SalesOrderLineBatch
from apps.accounts import roles

User = get_user_model()


class CloseBatchAiTests(TestCase):
    def setUp(self):
        get_registry().build(force=True)

        self.g = ItemGroup.objects.create(name="Cá biển")
        self.item = Item.objects.create(code="CA01", name="Cá nục", item_group=self.g, shelf_life_in_days=60, is_active=True)
        self.sup = Supplier.objects.create(name="Cảng Phan Thiết", is_active=True)
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.today = timezone.localdate()

        self.u_chu = make_user("chu_dw25", roles.OWNER)
        self.u_quanly = make_user("ql_dw25", roles.MANAGER)
        self.u_kho = make_user("kho_dw25", roles.WAREHOUSE_STAFF)

        self.client_chu = client_for(self.u_chu)
        self.client_quanly = client_for(self.u_quanly)
        self.client_kho = client_for(self.u_kho)

    def _create_fully_eligible_batch(self):
        """Tạo lô cá đã bán hết và đủ 100% điều kiện sàn để AI chốt lô (DW-25, Q-M6)."""
        now = timezone.now()
        # 1. Tạo lô ban đầu
        batch = batch_services.create_batch(
            item=self.item,
            supplier=self.sup,
            warehouse=self.wh,
            received_date=self.today - datetime.timedelta(days=15),
            qty=Decimal("100"),
            purchase_rate=Decimal("50000"),
        )
        batch_services.publish_batch(batch=batch, actor=None)
        batch.refresh_from_db()

        # Giả lập đã xuất bán hết: qty_available = 0, status = SOLD_OUT
        batch.qty_available = Decimal("0")
        batch.qty_reserved = Decimal("0")
        batch.status = Batch.Status.SOLD_OUT
        batch.save(update_fields=["qty_available", "qty_reserved", "status"])

        # 2. Hoá đơn mua thông qua PurchaseReceipt và PurchaseReceiptLine
        receipt = PurchaseReceipt.objects.create(
            supplier=self.sup,
            warehouse=self.wh,
            received_date=self.today - datetime.timedelta(days=15),
            status=PurchaseReceipt.Status.SUBMITTED,
            created_by=self.u_chu,
        )
        PurchaseReceiptLine.objects.create(
            receipt=receipt,
            item=self.item,
            qty=Decimal("100"),
            rate=Decimal("50000"),
            batch=batch,
        )
        PurchaseInvoice.objects.create(
            receipt=receipt,
            supplier=self.sup,
            invoice_date=self.today - datetime.timedelta(days=14),
            amount=Decimal("5000000"),
            created_by=self.u_chu,
        )

        # 3. Lần xuất kho cuối cùng cách đây 8 ngày
        last_out_entry = StockLedgerEntry.objects.create(
            batch=batch,
            qty_change=Decimal("-100"),
            movement_type=StockLedgerEntry.MovementType.SALE,
            created_by=self.u_chu,
            reference="sale_out_1",
        )
        StockLedgerEntry.objects.filter(pk=last_out_entry.pk).update(
            created_at=now - datetime.timedelta(days=8)
        )

        # 4. Biên bản kiểm kê kho đã duyệt sau lần xuất cuối (cách đây 7 ngày)
        rec = StockReconciliation.objects.create(
            count_date=self.today - datetime.timedelta(days=7),
            created_by=self.u_chu,
            approved_by=self.u_chu,
            status=StockReconciliation.Status.APPROVED,
            approved_at=now - datetime.timedelta(days=7),
        )
        rec.lines.create(batch=batch, system_qty=Decimal("0"), counted_qty=Decimal("0"))

        # 5. Chi phí mua cách đây 9 ngày (>= 7 ngày)
        cost = PurchaseCost.objects.create(
            cost_type=PurchaseCost.CostType.TRANSPORT,
            amount=Decimal("200000"),
            incurred_date=self.today - datetime.timedelta(days=9),
            created_by=self.u_chu,
        )
        PurchaseCost.objects.filter(pk=cost.pk).update(
            created_at=now - datetime.timedelta(days=9)
        )
        PurchaseCostAllocation.objects.create(
            purchase_cost=cost,
            batch=batch,
            allocated_amount=Decimal("200000"),
        )

        return batch

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_dw25_ac1_eligible_batch_scheduled_30m_then_executed_to_closed(self):
        """DW-25-AC1: Lô đủ điều kiện sàn, công tắc mở, Chủ đặt B -> call scheduled 30m; tới hạn job chốt CLOSED."""
        batch = self._create_fully_eligible_batch()

        # 1. Mở công tắc vùng đỏ và Chủ đặt B cho inventory.batch.close
        self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "red_zone": {"inventory.close_batch": True},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.client_chu.put(
            "/api/ai/my-config/",
            {
                "base_version": 0,
                "overrides": {"inventory.batch.close": "B"},
                "acknowledge_responsibility": True,
            },
            format="json",
        )

        # 2. Gọi call chốt lô
        res_call = self.client_chu.post(
            "/api/ai/commands/inventory.batch.close/call/",
            {
                "args": {},
                "target_id": str(batch.id),
            },
            format="json",
        )
        self.assertEqual(res_call.status_code, status.HTTP_200_OK)
        data = res_call.json()
        self.assertEqual(data["outcome"], "scheduled")
        self.assertEqual(data["level"], "B")
        action_id = data["action_id"]

        # Lô chưa chốt, vẫn SOLD_OUT
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.SOLD_OUT)
        self.assertFalse(batch.is_closed)

        action = AiAction.objects.get(pk=action_id)
        self.assertEqual(action.status, AiAction.Status.SCHEDULED)
        # Độ trễ 30 phút
        self.assertTrue(action.execute_after > timezone.now() + datetime.timedelta(minutes=25))

        # 3. Tua thời gian tới hạn và chạy management command run_due_ai_actions
        AiAction.objects.filter(pk=action.pk).update(
            execute_after=timezone.now() - datetime.timedelta(seconds=1)
        )
        call_command("run_due_ai_actions")

        # 4. Kiểm tra lô đã chốt CLOSED thành công
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.CLOSED)
        self.assertTrue(batch.is_closed)
        self.assertEqual(batch.closed_by, self.u_chu)

        action.refresh_from_db()
        self.assertEqual(action.status, AiAction.Status.DONE)
        self.assertIsNotNone(action.executed_at)

        # AuditLog ghi nhận execute_inventory.batch.close với ai_level=B
        self.assertTrue(
            AuditLog.objects.filter(
                action="execute_inventory.batch.close",
                ai_level="B",
                proposal_ref=str(action.id),
            ).exists()
        )

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_dw25_ac2_missing_condition_downgrades_to_c_proposal(self):
        """DW-25-AC2: Thiếu 1 điều kiện sàn (chi phí mua mới 3 ngày trước) -> tự động hạ C proposal, không xếp lịch."""
        batch = self._create_fully_eligible_batch()

        # Tạo chi phí mua mới cách đây 3 ngày (< 7 ngày)
        recent_cost = PurchaseCost.objects.create(
            cost_type=PurchaseCost.CostType.ICE,
            amount=Decimal("50000"),
            incurred_date=self.today - datetime.timedelta(days=3),
            created_by=self.u_chu,
        )
        PurchaseCost.objects.filter(pk=recent_cost.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=3)
        )
        PurchaseCostAllocation.objects.create(
            purchase_cost=recent_cost,
            batch=batch,
            allocated_amount=Decimal("50000"),
        )

        # Mở công tắc và đặt B
        self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "red_zone": {"inventory.close_batch": True},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.client_chu.put(
            "/api/ai/my-config/",
            {
                "base_version": 0,
                "overrides": {"inventory.batch.close": "B"},
                "acknowledge_responsibility": True,
            },
            format="json",
        )

        # Gọi call chốt lô
        res = self.client_chu.post(
            "/api/ai/commands/inventory.batch.close/call/",
            {
                "args": {},
                "target_id": str(batch.id),
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["outcome"], "proposal")
        self.assertEqual(data["level"], "C")
        self.assertIsNotNone(data.get("downgrade_reason"))
        self.assertEqual(data["downgrade_reason"]["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")

        # Action là PENDING, không phải SCHEDULED
        action = AiAction.objects.get(pk=data["action_id"])
        self.assertEqual(action.status, AiAction.Status.PENDING)
        self.assertEqual(action.level, AiAction.Level.C)

        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.SOLD_OUT)

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_dw25_ac3_undo_within_30m_cancels_action_batch_not_closed(self):
        """DW-25-AC3: Chủ huỷ lịch trong 30 phút -> action CANCELLED, lô không chốt."""
        batch = self._create_fully_eligible_batch()

        self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "red_zone": {"inventory.close_batch": True},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.client_chu.put(
            "/api/ai/my-config/",
            {
                "base_version": 0,
                "overrides": {"inventory.batch.close": "B"},
                "acknowledge_responsibility": True,
            },
            format="json",
        )

        res_call = self.client_chu.post(
            "/api/ai/commands/inventory.batch.close/call/",
            {"args": {}, "target_id": str(batch.id)},
            format="json",
        )
        action_id = res_call.json()["action_id"]

        # Huỷ lịch
        res_undo = self.client_chu.post(f"/api/ai/actions/{action_id}/undo/")
        self.assertEqual(res_undo.status_code, status.HTTP_200_OK)
        self.assertEqual(res_undo.json()["outcome"], "cancelled")

        action = AiAction.objects.get(pk=action_id)
        self.assertEqual(action.status, AiAction.Status.CANCELLED)

        # Chạy job tới hạn không thực thi
        AiAction.objects.filter(pk=action.pk).update(
            execute_after=timezone.now() - datetime.timedelta(seconds=1)
        )
        call_command("run_due_ai_actions")

        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.SOLD_OUT)

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_dw25_ac4_reserved_qty_added_in_window_escalates_to_chu(self):
        """DW-25-AC4: Có đơn mới giữ lô trong 30 phút -> job tới hạn không chốt, chuyển ESCALATED cho Chủ."""
        batch = self._create_fully_eligible_batch()

        self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "red_zone": {"inventory.close_batch": True},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.client_chu.put(
            "/api/ai/my-config/",
            {
                "base_version": 0,
                "overrides": {"inventory.batch.close": "B"},
                "acknowledge_responsibility": True,
            },
            format="json",
        )

        res_call = self.client_chu.post(
            "/api/ai/commands/inventory.batch.close/call/",
            {"args": {}, "target_id": str(batch.id)},
            format="json",
        )
        action_id = res_call.json()["action_id"]

        # Trong 30 phút, phát sinh lượng giữ chỗ (đơn mới giữ lô)
        batch.qty_reserved = Decimal("5")
        batch.save(update_fields=["qty_reserved"])

        # Tua thời gian tới hạn và chạy job
        AiAction.objects.filter(pk=action_id).update(
            execute_after=timezone.now() - datetime.timedelta(seconds=1)
        )
        call_command("run_due_ai_actions")

        # Kiểm tra không chốt lô, action chuyển ESCALATED cho Chủ
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.SOLD_OUT)

        action = AiAction.objects.get(pk=action_id)
        self.assertEqual(action.status, AiAction.Status.ESCALATED)
        self.assertEqual(action.assignee_group, roles.OWNER)
        self.assertIsNotNone(action.downgrade_reason)
        self.assertEqual(action.downgrade_reason["code"], "AI_CLOSE_BATCH_CONDITIONS_NOT_MET")

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_dw25_ac5_view_action_no_cost_keys_for_unauthorized(self):
        """DW-25-AC5: Việc chuyển về lô -> người thiếu view_costprice (quan_ly, nv_kho) xem không có số giá vốn."""
        batch = self._create_fully_eligible_batch()
        action = AiAction.objects.create(
            command="inventory.batch.close",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.B,
            status=AiAction.Status.ESCALATED,
            assignee_group=roles.MANAGER,
            owner=self.u_chu,
            target_model="batch",
            target_id=str(batch.id),
            args={"pk": batch.id, "unit_cost": "50000", "purchase_cost": "5000000"},
        )

        # quan_ly xem chi tiết việc AI
        res = self.client_quanly.get(f"/api/ai/actions/{action.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        args_str = str(data.get("args_preview", {}))
        self.assertNotIn("50000", args_str)
        self.assertNotIn("unit_cost", args_str)
        self.assertNotIn("purchase_cost", args_str)

    @override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, AI_WRITE_LEVELS_ALLOWED="B")
    def test_dw25_ac6_quan_ly_cannot_call_close_batch_404(self):
        """DW-25-AC6: quan_ly gọi call chốt lô -> 404 COMMAND_UNKNOWN."""
        batch = self._create_fully_eligible_batch()
        res = self.client_quanly.post(
            "/api/ai/commands/inventory.batch.close/call/",
            {"args": {}, "target_id": str(batch.id)},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.json()["code"], "COMMAND_UNKNOWN")

    @override_settings(AI_ENABLED=False)
    def test_dw25_ac7_ai_disabled_manual_close_still_works(self):
        """DW-25-AC7: AI_ENABLED=false -> Chủ chốt tay trên ERP qua UI chạy bình thường."""
        batch = self._create_fully_eligible_batch()
        res = self.client_chu.post(f"/api/inventory/batches/{batch.id}/close/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.CLOSED)
