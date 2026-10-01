"""
ERP theo design, Lô 3 — bất biến 9: dòng thời gian của đơn không ghép chữ tự do (lý do phiếu hoàn).

`Refund.reason` do người dùng gõ, có thể chứa SĐT. Nhãn "Tạo phiếu hoàn …" chỉ có số tiền; lý do vẫn
xem ở phiếu hoàn (`GET /api/sales/refunds/<id>/`). Dữ liệu giả.
"""
from decimal import Decimal

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.refunds import services as refund_services

FAKE_PHONE_IN_REASON = "0900000999"


class TimelineFreeTextTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("t_owner", roles.OWNER)
        self.manager = make_user("t_manager", roles.MANAGER)
        self.order = self._paid_order(phone="0900000123")
        self.refund, _ = refund_services.create_invoice_refund(
            invoice=self.order.invoice, amount=Decimal("100000"), is_partial=True,
            reason=f"Khách Thử A nhờ hoàn, gọi {FAKE_PHONE_IN_REASON}", actor=self.manager,
        )

    def test_ed12_order_guidance_has_no_refund_reason(self):
        resp = client_for(self.owner).get(f"/api/guidance/order/{self.order.pk}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        raw = resp.content.decode()
        self.assertNotIn(FAKE_PHONE_IN_REASON, raw)
        self.assertNotIn("Khách Thử A nhờ hoàn", raw)

    def test_ed12_order_detail_has_no_refund_reason(self):
        resp = client_for(self.owner).get(f"/api/sales/orders/{self.order.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(FAKE_PHONE_IN_REASON, resp.content.decode())

    def test_ed12_label_keeps_amount_and_reason_stays_on_refund(self):
        timeline = client_for(self.owner).get(f"/api/sales/orders/{self.order.pk}/").json()["timeline"]
        labels = [e["label"] for e in timeline if e["kind"] == "refund_created"]
        self.assertEqual(len(labels), 1)
        self.assertTrue(labels[0].startswith("Tạo phiếu hoàn"))
        self.assertIn("100.000", labels[0])
        self.assertNotIn("—", labels[0])
        refund = client_for(self.owner).get(f"/api/sales/refunds/{self.refund.pk}/").json()
        self.assertIn(FAKE_PHONE_IN_REASON, refund["reason"])

