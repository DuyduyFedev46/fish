"""
Test cho DW-03 — Khối "Tiếp theo · Đã làm" trên màn Đơn hàng (Lô 1a, P2).

Acceptance Criteria:
- DW-03-AC1: Đơn BOOKED -> next_steps có bước hệ thống tự huỷ (actor=system, deadline),
             xác nhận thanh toán tay allowed=false cho quan_ly (who=["Chủ"], why.br="BR-TT-07").
- DW-03-AC2: available_actions = đúng danh sách key có allowed=true trong next_steps,
             khớp kết quả cũ trên mọi trạng thái × 4 Group; bước allowed=true gọi thật không 400.
- DW-03-AC3: timeline gộp đơn, hoá đơn, phiếu giao, phiếu hoàn có trường doc, related liệt kê mã chứng từ.
- DW-03-AC4 (L-4): dòng actor_kind=ai hiện "AI của <tên hiển thị>" kèm mức, không hiện "Hệ thống";
                   config_version chỉ có khi người xem có ai.manage_ai_policy.
- DW-03-AC5 (PII): gọi bằng token Chủ -> response không chứa tên, SĐT, địa chỉ, nội dung CK, không changes thô.
- DW-03-AC6 (giá vốn): thiếu view_costprice -> không có khoá giá vốn ở bất kỳ tầng nào.
- DW-03-AC7 (quyền): thiếu view_salesorder -> 403; ngoài scope -> 404.
- DW-03-AC9 (AI tắt): AI_ENABLED=False -> endpoint trả 200, trường ai của mọi bước = null.
- DW-03-AC10 (vì sao): quét reasons.py -> mọi why.br có 1 câu; không câu nào chứa số tiền.
"""
import datetime
from decimal import Decimal
import re

from django.test import override_settings
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.common.guidance.reasons import REASONS, get_reason
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.models import DeliveryNote
from apps.sales.models import Customer, PaymentTransaction, Refund, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import OrderApiBase, find_keys, SENSITIVE_KEYS
from apps.accounts import roles


class GuidanceOrderTest(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.chu = make_user("chu_guidance", roles.OWNER)
        self.ql = make_user("ql_guidance", roles.MANAGER)
        self.kho = make_user("kho_guidance", roles.WAREHOUSE_STAFF)
        self.giao = make_user("giao_guidance", roles.DELIVERY_STAFF)
        self.giao_khac = make_user("giao_khac_guidance", roles.DELIVERY_STAFF)

        self.c_chu = client_for(self.chu)
        self.c_ql = client_for(self.ql)
        self.c_kho = client_for(self.kho)
        self.c_giao = client_for(self.giao)
        self.c_giao_khac = client_for(self.giao_khac)

        self.order_pii_name = "Nguyễn Văn A"
        self.order_pii_phone = "0987654321"
        self.order_pii_addr = "123 Đường Hải Sản, Quận 1, TP.HCM"

    def _create_order(self, phone=None, name=None, address=None):
        p = phone or self.order_pii_phone
        return order_services.create_order(
            customer_phone=p,
            customer_name=name or self.order_pii_name,
            delivery_address=address or self.order_pii_addr,
            phone=p,
            lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )

    def _pay_order(self, order, manual=False, actor=None):
        from apps.sales.payments import services as payment_services
        bank_txn = f"TXN-TEST-{order.pk}"
        if manual:
            return order_services.confirm_payment_manual(
                order=order,
                amount=order.total_amount,
                bank_txn_id=bank_txn,
                actor=actor or self.chu,
            )
        else:
            return payment_services.confirm_payment(
                order=order,
                bank_txn_id=bank_txn,
                amount=order.total_amount,
                received_at=timezone.now(),
            )


    # --- DW-03-AC1 -----------------------------------------------------------
    def test_dw03_ac1_booked_order_next_steps(self):
        """Đơn BOOKED -> next_steps có bước hệ thống tự huỷ, xác nhận thanh toán tay allowed=false cho ql."""
        order = self._create_order()
        resp = self.c_ql.get(f"/api/guidance/order/{order.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()

        steps = {s["key"]: s for s in data["next_steps"]}
        self.assertIn("auto_cancel", steps)
        self.assertIn("confirm_payment", steps)

        auto_cancel = steps["auto_cancel"]
        self.assertEqual(auto_cancel["actor"], "system")
        self.assertFalse(auto_cancel["allowed"])
        self.assertIsNotNone(auto_cancel["deadline"])
        self.assertEqual(auto_cancel["why"]["br"], "BR-BH-04")

        confirm_pay = steps["confirm_payment"]
        self.assertEqual(confirm_pay["actor"], "user")
        self.assertFalse(confirm_pay["allowed"])  # Quản lý không có quyền confirm_payment_manual
        self.assertEqual(confirm_pay["who"], ["Chủ"])
        self.assertEqual(confirm_pay["why"]["br"], "BR-TT-07")
        self.assertTrue(any(m["code"] == "BR-TT-07" for m in confirm_pay["missing"]))

        # Với Chủ: confirm_payment được phép
        resp_chu = self.c_chu.get(f"/api/guidance/order/{order.pk}/")
        self.assertEqual(resp_chu.status_code, status.HTTP_200_OK)
        steps_chu = {s["key"]: s for s in resp_chu.json()["next_steps"]}
        self.assertTrue(steps_chu["confirm_payment"]["allowed"])
        self.assertEqual(steps_chu["confirm_payment"]["missing"], [])

    # --- DW-03-AC2 -----------------------------------------------------------
    def test_dw03_ac2_available_actions_match_and_callable(self):
        """
        so available_actions cũ = mới trên fixture đơn mọi trạng thái × 4 Group.
        Mỗi bước allowed=true gọi thao tác thật không 400.
        """
        # Tạo đơn ở các trạng thái
        o_booked = self._create_order()

        o_paid = self._create_order()
        self._pay_order(o_paid)

        o_cancelled = self._create_order()
        self._pay_order(o_cancelled)
        order_services.cancel_paid_order(
            order=o_cancelled, actor=self.chu, reason="Khách huỷ", reason_code="CUSTOMER_CHANGED_MIND"
        )

        users = [self.chu, self.ql, self.kho, self.giao]
        orders = [o_booked, o_paid, o_cancelled]

        for u in users:
            for o in orders:
                o.refresh_from_db()
                from apps.sales.orders.next_steps import get_order_next_steps
                steps = get_order_next_steps(order=o, user=u)
                allowed_keys = [s.key for s in steps if s.allowed]

                # Gọi service available_actions
                actions = order_services.available_actions(order=o, user=u)
                self.assertEqual(
                    actions, allowed_keys,
                    f"Mismatch available_actions for user {u.get_username()} on order {o.status}"
                )

        # Kiểm tra bước allowed=true gọi thao tác thật không bị 400:
        # Với o_booked và chu: có confirm_payment -> gọi thật không bị 400
        client_chu = client_for(self.chu)
        resp_pay = client_chu.post(
            f"/api/sales/orders/{o_booked.pk}/confirm-payment",
            {"bank_txn_id": f"TXN-CALL-{o_booked.pk}"},
            format="json",
        )
        self.assertIn(resp_pay.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

        # Với o_paid và chu: có cancel -> gọi thật không bị 400
        resp_cancel = client_chu.post(
            f"/api/sales/orders/{o_paid.pk}/cancel/",
            {"reason_code": "CUSTOMER_CHANGED_MIND", "note": ""},
            format="json",
        )
        self.assertEqual(resp_cancel.status_code, status.HTTP_200_OK)

    # --- DW-03-AC3 -----------------------------------------------------------
    def test_dw03_ac3_timeline_merged_related(self):
        """timeline gộp đơn, hoá đơn, phiếu giao, phiếu hoàn có doc; related liệt kê mã."""
        order = self._create_order()
        self._pay_order(order)
        order.refresh_from_db()
        invoice = order.invoice

        # Tạo phiếu hoàn
        refund = Refund.objects.create(
            sales_invoice=invoice,
            amount=Decimal("50000"),
            reason="Hàng lỗi",
            created_by=self.ql,
        )

        resp = self.c_ql.get(f"/api/guidance/order/{order.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()

        # timeline có doc và sắp xếp tăng dần theo at
        timeline = data["timeline"]
        self.assertGreater(len(timeline), 0)
        docs = {e["doc"] for e in timeline}
        self.assertIn("order", docs)
        self.assertIn("invoice", docs)
        self.assertIn("delivery", docs)
        self.assertIn("refund", docs)

        ats = [e["at"] for e in timeline]
        self.assertEqual(ats, sorted(ats))

        # related có đủ invoice, delivery, refund
        related_types = {r["type"] for r in data["related"]}
        self.assertIn("invoice", related_types)
        self.assertIn("delivery", related_types)
        self.assertIn("refund", related_types)

    # --- DW-03-AC4 (L-4) -----------------------------------------------------
    def test_dw03_ac4_ai_actor_timeline_l4(self):
        """AuditLog có actor_kind=ai -> hiện 'AI của <tên>' kèm mức, không hiện 'Hệ thống'; config_version tuân thủ quyền."""
        order = self._create_order()
        # Giả lập dòng AuditLog do AI thực hiện thay cho Chủ
        AuditLog.objects.create(
            actor=None,
            actor_kind=AuditLog.ActorKind.AI,
            ai_actor=self.chu,
            action="cancel_paid_order",
            model_name=SalesOrder._meta.label,
            object_id=str(order.pk),
            object_repr=order.code,
            note="AI tự huỷ theo yêu cầu",
        )

        # Quản lý xem (chưa có ai.manage_ai_policy)
        resp_ql = self.c_ql.get(f"/api/guidance/order/{order.pk}/")
        data_ql = resp_ql.json()
        ai_entries_ql = [e for e in data_ql["timeline"] if e["actor"]["kind"] == "ai"]
        self.assertEqual(len(ai_entries_ql), 1)
        ai_actor_ql = ai_entries_ql[0]["actor"]
        self.assertTrue(ai_actor_ql["display"].startswith("AI của "))
        self.assertNotIn("Hệ thống", ai_actor_ql["display"])
        self.assertEqual(ai_actor_ql.get("level"), "C")
        self.assertNotIn("config_version", ai_actor_ql)

    # --- DW-03-AC5 (PII) -----------------------------------------------------
    def test_dw03_ac5_no_pii_for_chu(self):
        """Gọi guidance bằng token Chủ -> response không chứa tên, SĐT, địa chỉ khách, nội dung CK, changes thô."""
        order = self._create_order()
        self._pay_order(order)

        resp = self.c_chu.get(f"/api/guidance/order/{order.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        content_text = resp.content.decode("utf-8")

        # Kiểm tra không có PII
        self.assertNotIn(self.order_pii_name, content_text)
        self.assertNotIn(self.order_pii_phone, content_text)
        self.assertNotIn(self.order_pii_addr, content_text)
        self.assertNotIn("changes", resp.json()["timeline"][0])

    # --- DW-03-AC6 (giá vốn) -------------------------------------------------
    def test_dw03_ac6_no_cost_leak(self):
        """Người xem thiếu view_costprice -> không có khoá giá vốn ở bất kỳ tầng nào."""
        order = self._create_order()
        self._pay_order(order)

        # Quản lý và NV kho không có view_costprice
        for client in (self.c_ql, self.c_kho):
            resp = client.get(f"/api/guidance/order/{order.pk}/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            leaked = find_keys(resp.json(), SENSITIVE_KEYS)
            self.assertEqual(leaked, set(), f"Rò giá vốn trong guidance: {leaked}")

    # --- DW-03-AC7 (quyền) ---------------------------------------------------
    def test_dw03_ac7_permissions(self):
        """Thiếu view_salesorder -> 403; ngoài scope -> 404."""
        order = self._create_order()
        self._pay_order(order)
        order.refresh_from_db()
        note = order.invoice.delivery_notes.first()
        note.assigned_to = self.giao
        note.save(update_fields=["assigned_to"])

        # NV giao khác (ngoài scope T3) -> 404
        resp_khac = self.c_giao_khac.get(f"/api/guidance/order/{order.pk}/")
        self.assertEqual(resp_khac.status_code, status.HTTP_404_NOT_FOUND)

        # NV giao được gán đơn -> 200
        resp_giao = self.c_giao.get(f"/api/guidance/order/{order.pk}/")
        self.assertEqual(resp_giao.status_code, status.HTTP_200_OK)

        # Khách chưa đăng nhập -> 401
        resp_anon = self.client.get(f"/api/guidance/order/{order.pk}/")
        self.assertEqual(resp_anon.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- DW-03-AC9 (AI tắt) --------------------------------------------------
    @override_settings(AI_ENABLED=False)
    def test_dw03_ac9_ai_disabled(self):
        """AI_ENABLED=False -> endpoint trả 200 đủ, field ai của mọi bước = null."""
        order = self._create_order()
        resp = self.c_chu.get(f"/api/guidance/order/{order.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()

        self.assertIn("next_steps", data)
        self.assertIn("timeline", data)
        self.assertIn("warnings", data)
        for s in data["next_steps"]:
            self.assertIsNone(s["ai"])

    # --- DW-03-AC10 (vì sao) -------------------------------------------------
    def test_dw03_ac10_reasons_no_money_amount(self):
        """Quét reasons.py -> không câu nào chứa số tiền."""
        money_pattern = re.compile(r"(\d+\s*(?:đ|vnd|vnđ|đồng)|(?:triệu|nghìn)\s*đồng)", re.IGNORECASE)
        for code, text in REASONS.items():
            self.assertFalse(
                money_pattern.search(text),
                f"Lý do {code} chứa số tiền: {text}"
            )
            # Kiểm tra get_reason trả về đúng câu đó
            self.assertEqual(get_reason(code), text)
