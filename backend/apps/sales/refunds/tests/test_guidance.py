"""
Test cho DW-04 — Khối "Tiếp theo · Đã làm" trên Phiếu hoàn tiền (Lô 1b, P2).

Acceptance Criteria:
- DW-04-AC1: Phiếu hoàn PENDING, Quản lý xem -> bước "Xác nhận đã hoàn" allowed=false, who=["Chủ"], missing có BR-HT-03.
- DW-04-AC2: Phiếu hoàn PENDING tạo cách đây >= 25 ngày -> warnings có cảnh báo gần hạn 30 ngày; phiếu 10 ngày không có.
- DW-04-AC3: available_actions cũ = mới; bước allowed=true chạy thật không 400.
- DW-04-AC5: nv_kho, nv_giao gọi guidance phiếu hoàn -> 403, không lộ bước.
- DW-04-AC6: Phiếu hoàn đã xác nhận -> thao tác cũ trả 400 kèm mã BR.
- DW-04-AC7: AI_ENABLED=False -> endpoint trả 200, ai=null.
"""
import datetime
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.tests.fixtures import client_for, make_user
from apps.catalog.models import Item
from apps.inventory.models import Batch
from apps.sales.models import Customer, PaymentTransaction, Refund, SalesInvoice, SalesOrder
from apps.sales.refunds import services as refund_services
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services


from apps.sales.orders.tests.test_s10_api import OrderApiBase


class GuidanceRefundTest(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.chu = make_user("chu_rf_guidance", "chu")
        self.ql = make_user("ql_rf_guidance", "quan_ly")
        self.kho = make_user("kho_rf_guidance", "nv_kho")
        self.giao = make_user("giao_rf_guidance", "nv_giao")

        self.c_chu = client_for(self.chu)
        self.c_ql = client_for(self.ql)
        self.c_kho = client_for(self.kho)
        self.c_giao = client_for(self.giao)

        # Tạo đơn và hoá đơn
        self.order = order_services.create_order(
            customer_phone="0900000123",
            customer_name="Khách Thử Nghiệm",
            delivery_address="1 Đường Test, Q.1",
            phone="0900000123",
            lines=[{"item_code": self.item.code, "qty": Decimal("1")}],
        )
        self.pay = payment_services.confirm_payment(
            order=self.order,
            bank_txn_id=f"TXN-RF-{self.order.pk}",
            amount=self.order.total_amount,
            received_at=timezone.now(),
        )
        self.invoice = self.order.invoice

    def _create_refund(self, amount=Decimal("50000")):
        return refund_services.create_refund(
            invoice=self.invoice,
            amount=amount,
            reason="Hàng lỗi",
            actor=self.ql,
            is_partial=True,
        )

    # --- DW-04-AC1 -----------------------------------------------------------
    def test_dw04_ac1_pending_refund_next_steps_for_manager(self):
        """Phiếu hoàn PENDING, Quản lý xem -> bước 'Xác nhận đã hoàn' allowed=false, who=['Chủ'], missing có BR-HT-03."""
        refund = self._create_refund()
        resp = self.c_ql.get(f"/api/guidance/refund/{refund.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()

        steps = {s["key"]: s for s in data["next_steps"]}
        self.assertIn("confirm", steps)
        self.assertIn("mark_failed", steps)

        confirm_step = steps["confirm"]
        self.assertEqual(confirm_step["actor"], "user")
        self.assertFalse(confirm_step["allowed"])
        self.assertIn("Chủ", confirm_step["who"])
        missing_codes = [m["code"] for m in confirm_step["missing"]]
        self.assertIn("BR-HT-03", missing_codes)

        # Chủ xem -> allowed=True
        resp_chu = self.c_chu.get(f"/api/guidance/refund/{refund.pk}/")
        self.assertEqual(resp_chu.status_code, status.HTTP_200_OK)
        steps_chu = {s["key"]: s for s in resp_chu.json()["next_steps"]}
        self.assertTrue(steps_chu["confirm"]["allowed"])
        self.assertTrue(steps_chu["mark_failed"]["allowed"])

    # --- DW-04-AC2 -----------------------------------------------------------
    def test_dw04_ac2_refund_near_deadline_warning(self):
        """Phiếu hoàn PENDING tạo cách đây 25 ngày -> warnings có cảnh báo gần hạn 30 ngày; phiếu 10 ngày không có."""
        refund_old = self._create_refund()
        # Set created_at về 26 ngày trước
        past_26d = timezone.now() - datetime.timedelta(days=26)
        Refund.objects.filter(pk=refund_old.pk).update(created_at=past_26d)

        refund_recent = self._create_refund(amount=Decimal("10000"))
        past_10d = timezone.now() - datetime.timedelta(days=10)
        Refund.objects.filter(pk=refund_recent.pk).update(created_at=past_10d)

        with override_settings(GUIDANCE_REFUND_WARNING_DAYS=25):
            resp_old = self.c_ql.get(f"/api/guidance/refund/{refund_old.pk}/")
            self.assertEqual(resp_old.status_code, status.HTTP_200_OK)
            warnings_old = resp_old.json()["warnings"]
            self.assertTrue(any("gần hạn 30 ngày" in w["text"] for w in warnings_old))

            resp_recent = self.c_ql.get(f"/api/guidance/refund/{refund_recent.pk}/")
            self.assertEqual(resp_recent.status_code, status.HTTP_200_OK)
            warnings_recent = resp_recent.json()["warnings"]
            self.assertFalse(any("gần hạn 30 ngày" in w["text"] for w in warnings_recent))

    # --- DW-04-AC3 -----------------------------------------------------------
    def test_dw04_ac3_available_actions_and_live_execution(self):
        """Fixture phiếu hoàn mọi trạng thái: available_actions cũ = mới; bước allowed=true chạy thật không 400."""
        # 1. PENDING
        refund = self._create_refund()
        actions_chu = refund_services.refund_available_actions(refund=refund, user=self.chu)
        self.assertEqual(actions_chu, ["confirm", "mark_failed"])

        actions_ql = refund_services.refund_available_actions(refund=refund, user=self.ql)
        self.assertEqual(actions_ql, [])

        # Chạy thật bước confirm bằng Chủ -> không 400
        refund_confirmed = refund_services.confirm_refund(
            refund=refund,
            bank_txn_ref="REF-TXN-123456",
            actor=self.chu,
        )
        self.assertEqual(refund_confirmed.status, Refund.Status.REFUNDED)
        self.assertEqual(
            refund_services.refund_available_actions(refund=refund_confirmed, user=self.chu),
            [],
        )

        # 2. FAILED
        refund2 = self._create_refund(amount=Decimal("10000"))
        refund2 = refund_services.mark_refund_failed(refund=refund2, reason="Sai số tài khoản", actor=self.chu)
        self.assertEqual(refund2.status, Refund.Status.FAILED)

        actions_failed = refund_services.refund_available_actions(refund=refund2, user=self.chu)
        self.assertEqual(actions_failed, ["retry"])

        # Chạy thật bước retry bằng Chủ -> không 400
        refund_retried = refund_services.retry_refund(refund=refund2, actor=self.chu)
        self.assertEqual(refund_retried.status, Refund.Status.PENDING)

    # --- DW-04-AC5 -----------------------------------------------------------
    def test_dw04_ac5_permissions(self):
        """nv_kho, nv_giao gọi guidance phiếu hoàn -> 403, không lộ bước."""
        refund = self._create_refund()
        for c in (self.c_kho, self.c_giao):
            resp = c.get(f"/api/guidance/refund/{refund.pk}/")
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
            self.assertNotIn("next_steps", resp.json())

    # --- DW-04-AC6 -----------------------------------------------------------
    def test_dw04_ac6_stale_action_returns_400_with_br_code(self):
        """Phiếu hoàn vừa được Chủ xác nhận ở tab khác -> Quản lý / thao tác cũ nhận 400 kèm mã BR."""
        refund = self._create_refund()
        # Chủ xác nhận
        refund_services.confirm_refund(refund=refund, bank_txn_ref="REF-OK-999", actor=self.chu)

        # Thao tác confirm lại hoặc mark_failed nhận 400 BR-HT-09
        resp = self.c_chu.post(f"/api/sales/refunds/{refund.pk}/mark-failed/", {"reason": "thử lại"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.json().get("code"), "BR-HT-09")

    # --- DW-04-AC7 -----------------------------------------------------------
    @override_settings(AI_ENABLED=False)
    def test_dw04_ac7_guidance_works_when_ai_disabled(self):
        """AI_ENABLED=False -> endpoint trả 200, ai=null."""
        refund = self._create_refund()
        resp = self.c_ql.get(f"/api/guidance/refund/{refund.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("next_steps", data)
        for s in data["next_steps"]:
            self.assertIsNone(s["ai"])
