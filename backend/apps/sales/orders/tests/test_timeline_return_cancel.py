"""
TLA-L1 (review Lô bổ sung A, #8): dòng thời gian đơn hiểu việc huỷ phiếu hàng hoàn (`cancel_returntostock`).
Phiếu đã huỷ không còn hiện "chờ duyệt"; thêm dòng `return_cancelled` (doc nội bộ "return", chi tiết đơn chỉ phơi `doc` cho phiếu hoàn tiền). Nhãn không có chữ tự do,
không số tiền (bất biến 9, bất biến 1). Dữ liệu giả.
"""
from decimal import Decimal

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, confirm_note_for_test, make_user
from apps.delivery import services as delivery_services
from apps.delivery.models import DeliveryNote
from apps.inventory.models import ReturnToStock

from .test_s10_api import OrderApiBase

FREE_NOTE = "Khách Nguyễn Thử gọi 0900000777"


class TimelineReturnCancelTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("tl_owner", roles.OWNER)
        self.manager = make_user("tl_manager", roles.MANAGER)
        self.courier = make_user("tl_courier", roles.DELIVERY_STAFF)
        self.order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=self.order.invoice)
        confirm_note_for_test(note)
        for status in (DeliveryNote.Status.READY, DeliveryNote.Status.DELIVERING):
            delivery_services.advance_status(note=note, to_status=status, actor=self.courier)
        delivery_services.mark_failed(note=note, actor=self.courier)
        self.rt = delivery_services.return_to_warehouse(note=note, batch=self.batch, qty=Decimal("2"), actor=self.courier)
        ReturnToStock.objects.filter(pk=self.rt.pk).update(note=FREE_NOTE)

    def cancel(self, user):
        return client_for(user).post(f"/api/inventory/returns/{self.rt.pk}/cancel/", {}, format="json")

    def rows(self):
        return client_for(self.owner).get(f"/api/sales/orders/{self.order.pk}/").json()["timeline"]

    def test_tla_l1_cancelled_return_gets_its_own_line_and_no_pending_label(self):
        self.assertEqual(self.cancel(self.manager).status_code, 200)
        rows = self.rows()
        kinds = [r["kind"] for r in rows]
        self.assertEqual(kinds[-2:], ["return_to_warehouse", "return_cancelled"])
        created, cancelled = rows[-2], rows[-1]
        self.assertNotIn("chờ duyệt", created["label"])
        self.assertIn("2.000 kg", created["label"])
        self.assertEqual(cancelled["label"], "Huỷ phiếu hàng về kho 2.000 kg")
        self.assertEqual(cancelled["actor_display"], "tl_manager")

    def test_tla_l1_pending_return_still_says_pending(self):
        rows = self.rows()
        self.assertEqual(rows[-1]["kind"], "return_to_warehouse")
        self.assertIn("chờ duyệt", rows[-1]["label"])
        self.assertNotIn("return_cancelled", [r["kind"] for r in rows])

    def test_tla_l1_cancel_line_has_no_free_text_or_money(self):
        self.cancel(self.manager)
        raw = client_for(self.owner).get(f"/api/sales/orders/{self.order.pk}/").content.decode()
        for secret in ("0900000777", "Nguyễn Thử", FREE_NOTE):
            self.assertNotIn(secret, raw)
        cancelled = [r for r in self.rows() if r["kind"] == "return_cancelled"][0]
        self.assertNotIn("₫", cancelled["label"])
        self.assertNotIn("VNĐ", cancelled["label"])
