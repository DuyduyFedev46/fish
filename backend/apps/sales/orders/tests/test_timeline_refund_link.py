"""
Lô bổ sung A #2 (Duy chốt 02/10): dòng "Tạo phiếu hoàn …" trên timeline đơn có link sang phiếu hoàn.
`doc: {type: "refund", id}` chỉ nằm ở `timeline` của chi tiết đơn (khoá mới); nhãn không thêm chữ tự do (bất biến 9).
Dữ liệu giả.
"""
from decimal import Decimal

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.refunds import services as refund_services


class TimelineRefundLinkTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("rl_owner", roles.OWNER)
        self.manager = make_user("rl_manager", roles.MANAGER)
        self.order = self._paid_order(phone="0900000123")
        self.refund, _ = refund_services.create_invoice_refund(
            invoice=self.order.invoice, amount=Decimal("100000"), is_partial=True,
            reason="Hàng nhỏ hơn đặt", actor=self.manager,
        )

    def _timeline(self):
        return client_for(self.owner).get(f"/api/sales/orders/{self.order.pk}/").json()["timeline"]

    def test_refund_created_line_links_to_refund(self):
        rows = [e for e in self._timeline() if e["kind"] == "refund_created"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["doc"], {"type": "refund", "id": self.refund.pk})
        self.assertTrue(rows[0]["label"].startswith("Lập phiếu hoàn tiền"))
        self.assertNotIn("Hàng nhỏ hơn đặt", rows[0]["label"])  # không chữ tự do

    def test_link_target_opens_for_the_same_viewer(self):
        row = next(e for e in self._timeline() if e["kind"] == "refund_created")
        res = client_for(self.owner).get(f"/api/sales/refunds/{row['doc']['id']}/")
        self.assertEqual(res.status_code, 200)

    def test_other_lines_keep_old_shape(self):
        for e in self._timeline():
            if e["kind"] != "refund_created":
                self.assertNotIn("doc", e, e["kind"])
                self.assertEqual(set(e), {"at", "kind", "label", "actor_display"})

    def test_guidance_timeline_doc_stays_a_string(self):
        body = client_for(self.owner).get(f"/api/guidance/order/{self.order.pk}/").json()
        for e in body["timeline"]:
            self.assertIsInstance(e["doc"], str)
