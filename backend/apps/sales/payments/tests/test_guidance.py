"""
Test cho DW-04 — Khối "Tiếp theo · Đã làm" trên Giao dịch lệch / Thanh toán (Lô 1b, P2).

Acceptance Criteria:
- DW-04-AC3: available_actions cũ = mới; bước allowed=true chạy thật không 400.
- DW-04-AC4 (PII): Giao dịch lệch có raw_payload, nội dung CK, tên người chuyển giả: gọi bằng token Chủ -> response không chứa các chuỗi đó.
- DW-04-AC5: nv_kho, nv_giao gọi guidance giao dịch lệch -> 403, không lộ bước.
- DW-04-AC7: AI_ENABLED=False -> endpoint trả 200, ai=null.
"""
from decimal import Decimal
import json

from django.test import override_settings
from django.utils import timezone
from rest_framework import status

from apps.common.tests.fixtures import client_for, make_user
from apps.sales.models import PaymentTransaction, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.payments import services as payment_services
from apps.accounts import roles


class GuidancePaymentTest(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.chu = make_user("chu_pm_guidance", roles.OWNER)
        self.ql = make_user("ql_pm_guidance", roles.MANAGER)
        self.kho = make_user("kho_pm_guidance", roles.WAREHOUSE_STAFF)
        self.giao = make_user("giao_pm_guidance", roles.DELIVERY_STAFF)

        self.c_chu = client_for(self.chu)
        self.c_ql = client_for(self.ql)
        self.c_kho = client_for(self.kho)
        self.c_giao = client_for(self.giao)

        self.pii_raw_payload = "RAW_SEPAY_SECRET_PAYLOAD_ABCXYZ"
        self.pii_content = "CHUYEN KHOAN MUA CA - NGUYEN VAN A 0987654321"
        self.pii_sender_name = "NGUYEN VAN A"

    def _create_unmatched_payment(self, amount=Decimal("200000")):
        return PaymentTransaction.objects.create(
            bank_txn_id=f"TXN-UNMATCHED-{timezone.now().timestamp()}",
            amount=amount,
            source=PaymentTransaction.Source.GATEWAY,
            match_status=PaymentTransaction.MatchStatus.UNMATCHED,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            raw_payload={
                "secret": self.pii_raw_payload,
                "description": self.pii_content,
                "counter_account_name": self.pii_sender_name,
            },
            received_at=timezone.now(),
        )

    def _create_underpaid_order_and_payment(self):
        order = order_services.create_order(
            customer_phone="0900000123",
            customer_name="Khách Thử Nghiệm",
            delivery_address="1 Đường Test, Q.1",
            phone="0900000123",
            lines=[{"item_code": self.item.code, "qty": Decimal("2")}],  # total = 540k
        )
        # Thanh toán thiếu 200k < 540k
        p = payment_services.confirm_payment(
            order=order,
            bank_txn_id=f"TXN-UNDER-{order.pk}",
            amount=Decimal("200000"),
            received_at=timezone.now(),
        )
        return order, p

    # --- DW-04-AC3 -----------------------------------------------------------
    def test_dw04_ac3_available_actions_and_live_execution(self):
        """available_actions cũ = mới; bước allowed=true chạy thật không 400."""
        # 1. UNMATCHED payment
        p_unmatched = self._create_unmatched_payment()
        actions_chu = payment_services.payment_available_actions(payment=p_unmatched, user=self.chu)
        self.assertEqual(actions_chu, ["attach_to_order", "refund"])

        actions_ql = payment_services.payment_available_actions(payment=p_unmatched, user=self.ql)
        self.assertEqual(actions_ql, [])

        # 2. UNDERPAID payment
        order, p_under = self._create_underpaid_order_and_payment()
        actions_under = payment_services.payment_available_actions(payment=p_under, user=self.chu)
        # Chưa bù đủ -> chỉ có refund
        self.assertEqual(actions_under, ["refund"])

        # Bù thêm 340k đủ 540k
        p_bu = PaymentTransaction.objects.create(
            bank_txn_id=f"TXN-BU-{order.pk}",
            amount=Decimal("340000"),
            source=PaymentTransaction.Source.GATEWAY,
            match_status=PaymentTransaction.MatchStatus.UNDERPAID,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            sales_order=order,
            received_at=timezone.now(),
        )
        actions_bu = payment_services.payment_available_actions(payment=p_bu, user=self.chu)
        self.assertEqual(actions_bu, ["confirm_order", "refund"])

        # Chạy thật bước confirm_order bằng Chủ -> không 400
        res = payment_services.resolve_payment(
            payment=p_bu,
            action="CONFIRM_ORDER",
            actor=self.chu,
        )
        self.assertEqual(res["resolution_status"], PaymentTransaction.ResolutionStatus.RESOLVED)

    # --- DW-04-AC4 (PII) -----------------------------------------------------
    def test_dw04_ac4_no_pii_leak_in_payment_guidance_for_chu(self):
        """Giao dịch lệch có raw_payload, nội dung CK, tên người chuyển giả: gọi bằng token Chủ -> response không chứa các chuỗi đó."""
        p = self._create_unmatched_payment()
        resp = self.c_chu.get(f"/api/guidance/payment/{p.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp_text = json.dumps(resp.json(), ensure_ascii=False)
        self.assertNotIn(self.pii_raw_payload, resp_text)
        self.assertNotIn(self.pii_content, resp_text)
        self.assertNotIn(self.pii_sender_name, resp_text)

    # --- DW-04-AC5 -----------------------------------------------------------
    def test_dw04_ac5_permissions(self):
        """nv_kho, nv_giao gọi guidance giao dịch lệch -> 403, không lộ bước."""
        p = self._create_unmatched_payment()
        for c in (self.c_kho, self.c_giao):
            resp = c.get(f"/api/guidance/payment/{p.pk}/")
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
            self.assertNotIn("next_steps", resp.json())

    # --- DW-04-AC7 -----------------------------------------------------------
    @override_settings(AI_ENABLED=False)
    def test_dw04_ac7_guidance_works_when_ai_disabled(self):
        """AI_ENABLED=False -> endpoint trả 200, ai=null."""
        p = self._create_unmatched_payment()
        resp = self.c_chu.get(f"/api/guidance/payment/{p.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("next_steps", data)
        for s in data["next_steps"]:
            self.assertIsNone(s["ai"])
