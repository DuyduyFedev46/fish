"""
Kiểm thử toàn diện cho Việc AI (DW-11-AC1 đến DW-11-AC10).
"""
from decimal import Decimal
import datetime
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Warehouse
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier
from apps.sales.models import Customer, SalesOrder
from apps.accounts import roles


@override_settings(AI_ENABLED=True)
class AiActionApiTestCase(TestCase):
    def setUp(self):
        self.user_chu = make_user("chu_test", roles.OWNER)
        self.user_ql = make_user("ql_test", roles.MANAGER)
        self.user_kho = make_user("kho_test", roles.WAREHOUSE_STAFF)
        self.user_giao = make_user("giao_test", roles.DELIVERY_STAFF)

        self.client_chu = client_for(self.user_chu)
        self.client_ql = client_for(self.user_ql)
        self.client_kho = client_for(self.user_kho)
        self.client_giao = client_for(self.user_giao)

        # Master data
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA-001", name="Cá thu", item_group=g)
        self.sup = Supplier.objects.create(name="Đầu mối 1")
        self.wh = Warehouse.objects.create(name="Kho 1")

        # Phiếu nhập DRAFT
        self.receipt = PurchaseReceipt.objects.create(
            supplier=self.sup,
            warehouse=self.wh,
            received_date=timezone.now().date(),
            created_by=self.user_kho,
            status=PurchaseReceipt.Status.DRAFT,
        )
        self.receipt_line = PurchaseReceiptLine.objects.create(
            receipt=self.receipt,
            item=self.item,
            qty=Decimal("10.000"),
            rate=Decimal("80000.00"),
        )

    def test_dw11_ac1_call_write_creates_proposal_and_auditlog(self):
        """DW-11-AC1: nv_kho gọi lệnh ghi -> 200 outcome=proposal, level=C, expires_at=+15m, phiếu vẫn DRAFT, AuditLog propose_... actor_kind=ai."""
        res = self.client_kho.post(
            "/api/ai/commands/purchasing.purchasereceipt.submit/call/",
            {"target_id": self.receipt.pk, "args": {}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["outcome"], "proposal")
        self.assertEqual(data["level"], "C")
        self.assertIn("action_id", data)
        self.assertIn("expires_at", data)
        self.assertIn("preview", data)

        # Phiếu vẫn là DRAFT
        self.receipt.refresh_from_db()
        self.assertEqual(self.receipt.status, PurchaseReceipt.Status.DRAFT)

        # AiAction có status=PENDING
        action = AiAction.objects.get(id=data["action_id"])
        self.assertEqual(action.status, AiAction.Status.PENDING)
        self.assertEqual(action.level, AiAction.Level.C)
        self.assertEqual(action.owner, self.user_kho)

        # AuditLog có dòng propose_...
        log = AuditLog.objects.filter(proposal_ref=str(action.id)).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor_kind, "ai")
        self.assertEqual(log.ai_actor, self.user_kho)
        self.assertEqual(log.ai_level, "C")

    def test_dw11_ac2_confirm_success_after_3_seconds(self):
        """DW-11-AC2: Mở chi tiết >= 3 giây, confirm -> phiếu SUBMITTED, AuditLog thực thi mang actor_kind=user, actor=người duyệt."""
        # 1. Tạo proposal
        res_call = self.client_kho.post(
            "/api/ai/commands/purchasing.purchasereceipt.submit/call/",
            {"target_id": self.receipt.pk, "args": {}},
            format="json",
        )
        action_id = res_call.json()["action_id"]

        # 2. Người có quyền (Chủ hoặc nv_kho) mở xem chi tiết
        res_get = self.client_kho.get(f"/api/ai/actions/{action_id}/")
        self.assertEqual(res_get.status_code, 200)
        nonce = res_get.json()["confirm_nonce"]

        # Giả lập đã xem qua 3 giây (V5)
        action = AiAction.objects.get(id=action_id)
        action.viewed_at = timezone.now() - datetime.timedelta(seconds=5)
        action.save(update_fields=["viewed_at"])

        # 3. Confirm
        res_confirm = self.client_kho.post(
            f"/api/ai/actions/{action_id}/confirm/",
            {"confirm_nonce": nonce},
            format="json",
        )
        self.assertEqual(res_confirm.status_code, 200)
        self.assertEqual(res_confirm.json()["outcome"], "done")

        # Phiếu chuyển thành SUBMITTED
        self.receipt.refresh_from_db()
        self.assertEqual(self.receipt.status, PurchaseReceipt.Status.SUBMITTED)

        # AiAction thành CONFIRMED
        action.refresh_from_db()
        self.assertEqual(action.status, AiAction.Status.CONFIRMED)
        self.assertEqual(action.decided_by, self.user_kho)

        # AuditLog thực thi ghi actor_kind=user, actor=người duyệt, proposal_ref=id
        log = AuditLog.objects.filter(
            action="confirm_purchasing.purchasereceipt.submit",
            proposal_ref=str(action.id),
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor_kind, "user")
        self.assertEqual(log.actor, self.user_kho)

    def test_dw11_ac3_confirm_errors(self):
        """DW-11-AC3: Chưa mở hoặc < 3 giây -> 400; duyệt lần 2 -> 409; hết hạn 15m -> 410."""
        # Tạo proposal
        res_call = self.client_kho.post(
            "/api/ai/commands/purchasing.purchasereceipt.submit/call/",
            {"target_id": self.receipt.pk, "args": {}},
            format="json",
        )
        action_id = res_call.json()["action_id"]

        # (a) Chưa mở chi tiết mà confirm -> 400 BR-AI-14
        r_err1 = self.client_kho.post(f"/api/ai/actions/{action_id}/confirm/", {}, format="json")
        self.assertEqual(r_err1.status_code, 400)
        self.assertEqual(r_err1.json()["code"], "BR-AI-14")

        # Mở chi tiết
        self.client_kho.get(f"/api/ai/actions/{action_id}/")

        # (b) Chưa đủ 3 giây -> 400 BR-AI-14
        r_err2 = self.client_kho.post(f"/api/ai/actions/{action_id}/confirm/", {}, format="json")
        self.assertEqual(r_err2.status_code, 400)
        self.assertEqual(r_err2.json()["code"], "BR-AI-14")

        # (c) Đã hết hạn (quá 15 phút) -> 410 AI_ACTION_EXPIRED
        action = AiAction.objects.get(id=action_id)
        action.viewed_at = timezone.now() - datetime.timedelta(seconds=5)
        action.expires_at = timezone.now() - datetime.timedelta(minutes=1)
        action.save(update_fields=["viewed_at", "expires_at"])

        r_err3 = self.client_kho.post(f"/api/ai/actions/{action_id}/confirm/", {}, format="json")
        self.assertEqual(r_err3.status_code, 410)
        self.assertEqual(r_err3.json()["code"], "AI_ACTION_EXPIRED")

        # (d) Đã quyết định trước đó -> 409 AI_ACTION_ALREADY_DECIDED
        action.status = AiAction.Status.CONFIRMED
        action.expires_at = timezone.now() + datetime.timedelta(minutes=10)
        action.save(update_fields=["status", "expires_at"])

        r_err4 = self.client_kho.post(f"/api/ai/actions/{action_id}/confirm/", {}, format="json")
        self.assertEqual(r_err4.status_code, 409)
        self.assertEqual(r_err4.json()["code"], "AI_ACTION_ALREADY_DECIDED")

    def test_dw11_ac4_reject_action(self):
        """DW-11-AC4: Nháp bất kỳ -> reject -> AiAction REJECTED, chứng từ không đổi, AuditLog 1 dòng."""
        res_call = self.client_kho.post(
            "/api/ai/commands/purchasing.purchasereceipt.submit/call/",
            {"target_id": self.receipt.pk, "args": {}},
            format="json",
        )
        action_id = res_call.json()["action_id"]

        res_rej = self.client_kho.post(
            f"/api/ai/actions/{action_id}/reject/",
            {"reason_code": "NOT_NEEDED"},
            format="json",
        )
        self.assertEqual(res_rej.status_code, 200)

        action = AiAction.objects.get(id=action_id)
        self.assertEqual(action.status, AiAction.Status.REJECTED)
        self.receipt.refresh_from_db()
        self.assertEqual(self.receipt.status, PurchaseReceipt.Status.DRAFT)

        # AuditLog có dòng reject
        log = AuditLog.objects.filter(
            action="reject_purchasing.purchasereceipt.submit",
            proposal_ref=str(action.id),
        ).first()
        self.assertIsNotNone(log)

    def test_dw11_ac5_permission_denied_on_confirm(self):
        """DW-11-AC5: Người duyệt thiếu quyền -> 403 BR-AI-04. scope=all chỉ người có manage_ai_policy xem được."""
        # 1. nv_giao cố confirm lệnh không đủ quyền -> 403 BR-AI-04.
        # P8 Lô 7 (BM-05): việc của người khác (ngoài phạm vi) nay là 404 (xem test_p8_lo7_bm05); để vẫn
        # kiểm BR-AI-04 thì việc phải nằm trong phạm vi của nv_giao (chính nv_giao là chủ việc).
        action = AiAction.objects.create(
            command="purchasing.purchasereceipt.submit",
            kind="write",
            level="C",
            status="PENDING",
            owner=self.user_giao,
            target_model="purchasereceipt",
            target_id=str(self.receipt.pk),
            viewed_at=timezone.now() - datetime.timedelta(seconds=5),
            expires_at=timezone.now() + datetime.timedelta(minutes=15),
        )
        res_giao = self.client_giao.post(f"/api/ai/actions/{action.id}/confirm/", {}, format="json")
        self.assertEqual(res_giao.status_code, 403)
        self.assertEqual(res_giao.json()["code"], "BR-AI-04")

        # 2. nv_kho gọi scope=all -> 403 PERMISSION_DENIED
        res_scope_kho = self.client_kho.get("/api/ai/actions/?scope=all")
        self.assertEqual(res_scope_kho.status_code, 403)

        # 3. Chu có manage_ai_policy gọi scope=all -> 200
        res_scope_chu = self.client_chu.get("/api/ai/actions/?scope=all")
        self.assertEqual(res_scope_chu.status_code, 200)

    def _make_stocktake_users(self):
        self.stocktake_owner = make_user("ai_st_owner", roles.OWNER)
        self.stocktake_warehouse = make_user("ai_st_warehouse", roles.WAREHOUSE_STAFF)

    def _submitted_reconciliation(self, creator):
        """Phiếu kiểm kê SUBMITTED có 1 dòng (lô giả), do `creator` nhập."""
        from apps.inventory.batches import services as batch_services
        from apps.inventory.models import StockReconciliation
        from apps.inventory.stocktake import services as stocktake_services
        from apps.inventory.models import StockReconciliationLine

        batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=timezone.now().date(), qty=Decimal("50"), purchase_rate=Decimal("90000"),
        )
        rec = stocktake_services.create_reconciliation(
            count_date=timezone.now().date(), note="", lines=None, actor=creator,
        )
        StockReconciliationLine.objects.create(
            reconciliation=rec, batch=batch, system_qty=Decimal("50"),
            counted_qty=Decimal("49"), difference_qty=Decimal("-1"), reason="hao hụt",
        )
        rec = stocktake_services.submit_reconciliation(reconciliation=rec, actor=creator)
        self.assertEqual(rec.status, StockReconciliation.Status.SUBMITTED)
        return rec

    def _approve_action(self, owner, rec):
        return AiAction.objects.create(
            command="inventory.stockreconciliation.approve",
            kind="write",
            level="C",
            status="PENDING",
            owner=owner,
            target_model="stockreconciliation",
            target_id=str(rec.pk),
            viewed_at=timezone.now() - datetime.timedelta(seconds=5),
            expires_at=timezone.now() + datetime.timedelta(minutes=15),
        )

    def test_dw11_ac6_owner_of_ai_with_approve_perm_can_self_confirm_stocktake(self):
        """DW-11-AC6 (đổi theo TLA-M1, quyết định #6): người có quyền duyệt kiểm kê và là chủ việc AI thì
        tự xác nhận được, không còn chặn BR-KK-02. Phiếu chuyển APPROVED, AuditLog ghi người duyệt."""
        from apps.inventory.models import StockReconciliation

        self._make_stocktake_users()
        rec = self._submitted_reconciliation(self.stocktake_owner)
        action = self._approve_action(self.stocktake_owner, rec)
        res = client_for(self.stocktake_owner).post(f"/api/ai/actions/{action.id}/confirm/", {}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertNotEqual(res.json().get("code"), "BR-KK-02")
        rec.refresh_from_db()
        self.assertEqual(rec.status, StockReconciliation.Status.APPROVED)
        action.refresh_from_db()
        self.assertEqual(action.status, AiAction.Status.CONFIRMED)
        self.assertEqual(action.decided_by, self.stocktake_owner)

    def test_dw11_ac6_confirmer_without_approve_perm_gets_403_on_stocktake(self):
        """DW-11-AC6 (TLA-M1): người xác nhận thiếu approve_stockreconciliation -> 403 BR-AI-04, phiếu không đổi."""
        from apps.inventory.models import StockReconciliation

        self._make_stocktake_users()
        rec = self._submitted_reconciliation(self.stocktake_warehouse)
        action = self._approve_action(self.stocktake_warehouse, rec)
        res = client_for(self.stocktake_warehouse).post(f"/api/ai/actions/{action.id}/confirm/", {}, format="json")
        self.assertEqual(res.status_code, 403, res.content)
        self.assertEqual(res.json()["code"], "BR-AI-04")
        rec.refresh_from_db()
        self.assertEqual(rec.status, StockReconciliation.Status.SUBMITTED)
        action.refresh_from_db()
        self.assertEqual(action.status, AiAction.Status.PENDING)

    def test_dw11_ac7_args_preview_scrub_cost_keys(self):
        """DW-11-AC7: args_preview không có rate với người thiếu view_costprice; chu thấy rate."""
        action = AiAction.objects.create(
            command="purchasing.purchasereceipt.submit",
            kind="write",
            level="C",
            status="PENDING",
            owner=self.user_kho,
            args={"item_code": "CA-001", "rate": "80000.00", "qty": "10.000"},
            viewed_at=timezone.now() - datetime.timedelta(seconds=5),
            expires_at=timezone.now() + datetime.timedelta(minutes=15),
        )
        # nv_kho xem chi tiết -> args_preview KHÔNG có rate
        res_kho = self.client_kho.get(f"/api/ai/actions/{action.id}/")
        self.assertEqual(res_kho.status_code, 200)
        self.assertNotIn("rate", res_kho.json()["args_preview"])

        # chu xem chi tiết -> args_preview CÓ rate
        res_chu = self.client_chu.get(f"/api/ai/actions/{action.id}/")
        self.assertEqual(res_chu.status_code, 200)
        self.assertIn("rate", res_chu.json()["args_preview"])

    def test_dw11_ac8_target_only_type_and_code_no_pii(self):
        """DW-11-AC8: target chỉ loại + mã; không tên/SĐT/địa chỉ; không object_repr."""
        cust = Customer.objects.create(name="Khách PII", phone="0988888888", default_address="HCM")
        order = SalesOrder.objects.create(code="SO260928-PII", customer=cust)
        action = AiAction.objects.create(
            command="sales.salesorder.confirm_payment",
            kind="write",
            level="C",
            status="PENDING",
            owner=self.user_chu,
            target_model="salesorder",
            target_id=order.code,
            viewed_at=timezone.now() - datetime.timedelta(seconds=5),
            expires_at=timezone.now() + datetime.timedelta(minutes=15),
        )
        res = self.client_chu.get(f"/api/ai/actions/{action.id}/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        target = data["target"]
        self.assertEqual(target["type"], "salesorder")
        self.assertEqual(target["code"], order.code)
        self.assertNotIn("Khách PII", str(data))
        self.assertNotIn("0988888888", str(data))

    @override_settings(AI_ENABLED=False)
    def test_dw11_ac9_ai_disabled_behavior(self):
        """DW-11-AC9: AI_ENABLED=false -> confirm 410; reject và GET vẫn chạy."""
        action = AiAction.objects.create(
            command="purchasing.purchasereceipt.submit",
            kind="write",
            level="C",
            status="PENDING",
            owner=self.user_kho,
            viewed_at=timezone.now() - datetime.timedelta(seconds=5),
            expires_at=timezone.now() + datetime.timedelta(minutes=15),
        )
        # GET vẫn chạy (200)
        res_get = self.client_kho.get(f"/api/ai/actions/{action.id}/")
        self.assertEqual(res_get.status_code, 200)

        # Confirm trả 410 AI_DISABLED
        res_conf = self.client_kho.post(f"/api/ai/actions/{action.id}/confirm/", {}, format="json")
        self.assertEqual(res_conf.status_code, 410)
        self.assertEqual(res_conf.json()["code"], "AI_DISABLED")

        # Reject vẫn chạy (200)
        res_rej = self.client_kho.post(f"/api/ai/actions/{action.id}/reject/", {}, format="json")
        self.assertEqual(res_rej.status_code, 200)

    def test_dw11_ac10_viewset_list_display_and_filtering(self):
        """DW-11-AC10: ViewSet list trả owner_display ('AI của <tên>'), lọc theo status."""
        action = AiAction.objects.create(
            command="purchasing.purchasereceipt.submit",
            kind="write",
            level="C",
            status="PENDING",
            owner=self.user_kho,
            expires_at=timezone.now() + datetime.timedelta(minutes=15),
        )
        res = self.client_kho.get("/api/ai/actions/?status=PENDING")
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]["owner_display"], f"AI của {self.user_kho.username}")
