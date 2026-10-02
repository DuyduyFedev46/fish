"""
Lô bổ sung A #15 (Duy chốt 02/10): đơn Tự huỷ (AUTO_CANCELLED) là đơn đã chết.
- `available_actions` (và các bước guidance) của đơn đó rỗng: không còn `confirm_payment` hay thao tác ghi nào.
- `POST /api/sales/orders/{id}/confirm-payment` -> 400 `ORDER_AUTO_CANCELLED`, không ghi giao dịch, không audit.
- Tiền về muộn (webhook / IPN) vẫn vào hàng chờ thanh toán lệch (ORPHAN) để Chủ hoàn tiền (BR-TT-05).
Dữ liệu giả.
"""
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch
from apps.sales.models import PaymentTransaction, SalesInvoice, SalesOrder
from apps.sales.orders.tests.test_s10_api import SENSITIVE_KEYS, OrderApiBase, find_keys
from apps.sales.payments import services as payment_services

CODE = "ORDER_AUTO_CANCELLED"
WEBHOOK_URL = "/api/internal/payments/sepay-webhook/"


class AutoCancelledOrderTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("owner_a15", roles.OWNER)
        self.manager = make_user("manager_a15", roles.MANAGER)
        self.warehouse_staff = make_user("warehouse_a15", roles.WAREHOUSE_STAFF)
        self.courier = make_user("courier_a15", roles.DELIVERY_STAFF)
        self.order = self._order()
        SalesOrder.objects.filter(pk=self.order.pk).update(status=SalesOrder.Status.AUTO_CANCELLED)
        self.order.refresh_from_db()

    def _confirm(self, user, **data):
        payload = {"bank_txn_id": "FTLATE1", "amount": "540000", **data}
        return client_for(user).post(f"/api/sales/orders/{self.order.pk}/confirm-payment", payload, format="json")

    def test_a15_available_actions_is_empty_for_every_role(self):
        for user in (self.owner, self.manager, self.warehouse_staff):
            body = client_for(user).get(f"/api/sales/orders/{self.order.pk}/").json()
            self.assertEqual(body["available_actions"], [], user.username)

    def test_a15_guidance_has_no_write_step(self):
        resp = client_for(self.owner).get(f"/api/guidance/order/{self.order.pk}/")
        if resp.status_code == 200:
            self.assertEqual([s for s in resp.json().get("next_steps", []) if s.get("allowed")], [])

    def test_a15_confirm_payment_is_400_order_auto_cancelled(self):
        resp = self._confirm(self.owner)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], CODE)
        self.assertIn("tự huỷ", resp.json()["detail"])

    def test_a15_confirm_payment_writes_nothing(self):
        self._confirm(self.owner)
        self.assertFalse(PaymentTransaction.objects.exists())
        self.assertFalse(SalesInvoice.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action="confirm_payment_manual").exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.AUTO_CANCELLED)

    def test_a15_confirm_payment_does_not_change_stock(self):
        before = Batch.objects.get(pk=self.batch.pk)
        self._confirm(self.owner)
        after = Batch.objects.get(pk=self.batch.pk)
        self.assertEqual((after.qty_available, after.qty_reserved), (before.qty_available, before.qty_reserved))

    def test_a15_confirm_payment_still_403_without_permission(self):
        for user in (self.manager, self.warehouse_staff, self.courier, self.nobody):
            self.assertEqual(self._confirm(user).status_code, 403, user.username)

    def test_a15_repeat_call_stays_400_even_with_an_old_orphan_payment(self):
        # Dữ liệu cũ: giao dịch ORPHAN ghi tay từ trước quyết định này. Gọi lại cùng mã GD vẫn 400, không "duplicate".
        payment_services.confirm_payment(
            order=self.order, bank_txn_id="FTLATE1", amount=Decimal("540000"), received_at=timezone.now(),
        )
        resp = self._confirm(self.owner)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], CODE)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_a15_service_level_manual_confirm_raises(self):
        from apps.common.exceptions import BusinessError

        with self.assertRaises(BusinessError) as ctx:
            payment_services.confirm_payment_manual(
                order=self.order, bank_txn_id="FTLATE2", amount="540000", actor=self.owner,
            )
        self.assertEqual(ctx.exception.code, CODE)

    def test_a15_late_money_via_service_still_reaches_payment_queue(self):
        pay = payment_services.confirm_payment(
            order=self.order, bank_txn_id="FTLATE3", amount=Decimal("540000"), received_at=timezone.now(),
        )
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.ORPHAN)
        self.assertEqual(pay.resolution_status, PaymentTransaction.ResolutionStatus.OPEN)
        body = client_for(self.owner).get("/api/sales/payments/", {"resolution_status": "OPEN"}).json()
        row = next(r for r in body["results"] if r["id"] == pay.pk)
        self.assertEqual(row["match_status"], "ORPHAN")
        self.assertIn("refund", " ".join(row["available_actions"]).lower())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.AUTO_CANCELLED)
        self.assertFalse(SalesInvoice.objects.exists())

    @override_settings(INTERNAL_SERVICE_TOKEN="tok")
    def test_a15_late_money_via_webhook_still_reaches_payment_queue(self):
        resp = client_for(None).post(
            WEBHOOK_URL,
            {"bank_txn_id": "FTLATE4", "order_code": self.order.code, "amount": "540000",
             "received_at": "2026-10-02T10:00:00+07:00"},
            format="json", HTTP_X_INTERNAL_TOKEN="tok",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        pay = PaymentTransaction.objects.get(bank_txn_id="FTLATE4")
        self.assertEqual(pay.match_status, PaymentTransaction.MatchStatus.ORPHAN)
        self.assertEqual(pay.resolution_status, PaymentTransaction.ResolutionStatus.OPEN)

    def test_a15_booked_order_is_unaffected(self):
        booked = self._order(phone="0902222222")
        self.assertEqual(
            client_for(self.owner).get(f"/api/sales/orders/{booked.pk}/").json()["available_actions"],
            ["confirm_payment"],
        )
        resp = client_for(self.owner).post(
            f"/api/sales/orders/{booked.pk}/confirm-payment",
            {"bank_txn_id": "FTOK1", "amount": "540000"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["result"], "PAID")

    def test_a15_response_has_no_cost_or_personal_data(self):
        raw = self._confirm(self.owner).content.decode()
        detail = client_for(self.owner).get(f"/api/sales/orders/{self.order.pk}/").json()["available_actions"]
        self.assertEqual(find_keys(detail, SENSITIVE_KEYS), set())
        for secret in ("0901234567", "Chị Hoa", "Lê Lợi", "FTLATE1"):
            self.assertNotIn(secret, raw)
