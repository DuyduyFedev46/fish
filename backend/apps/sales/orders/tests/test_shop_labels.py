"""
Lô dọn chữ AI, W1 và W2 (02b 2.4) — Shop tra đơn không bao giờ trả mã thô hay chữ kỹ thuật ("TTL").
Chỉ đổi chuỗi nhãn, không thêm key. Bảng nhãn theo doc/thuat-ngu-va-trang-thai.md mục 4 (T2, T24–T30). Dữ liệu giả.
"""
import re

from django.test import override_settings
from rest_framework.test import APIClient

from apps.delivery.models import DeliveryNote
from apps.sales.models import SalesOrder
from apps.sales.orders.shop_labels import (
    SHOP_DELIVERY_STATUS_LABELS,
    UNKNOWN_STATUS_LABEL,
    shop_delivery_status_label,
)
from apps.sales.orders.tests.test_s10_api import OrderApiBase

PHONE = "0900000456"
RAW_CODE = re.compile(r"^[A-Z_]+$")
URL = "/api/shop/orders/lookup/"
EXPECTED = {
    "CONFIRMING": "Chờ vựa gọi xác nhận",
    "PREPARING": "Đang soạn hàng",
    "READY": "Đã soạn xong, chờ giao",
    "DELIVERING": "Đang giao",
    "COMPLETED": "Đã giao",
    "FAILED": "Giao chưa thành công, vựa sẽ liên hệ lại",
    "CANCELLED": "Đã huỷ",
}
TOP_KEYS = {
    "order_code", "status", "state", "status_label", "placed_at", "paid_at", "delivered_at", "booked_expires_at",
    "server_now", "hold_minutes", "payment_pending_minutes", "delivery", "lines", "subtotal", "discount",
    "total_amount", "cancel_notice", "late_payment", "lookup_token",
}


class ShopLookupLabelTests(OrderApiBase):
    def _lookup(self, order):
        return APIClient().post(URL, {"order_code": order.code, "phone": PHONE}, format="json")

    def test_auto_cancelled_label_is_plain_vietnamese(self):
        order = self._order(phone=PHONE)
        SalesOrder.objects.filter(pk=order.pk).update(status=SalesOrder.Status.AUTO_CANCELLED)
        body = self._lookup(order).json()
        self.assertEqual(body["status_label"], "Đã huỷ vì quá giờ thanh toán")
        self.assertEqual(body["state"], "expired")
        self.assertNotIn("TTL", str(body))
        self.assertEqual(set(body), TOP_KEYS)

    def test_delivery_status_labels_match_table(self):
        order = self._paid_order(phone=PHONE)
        note = order.invoice.delivery_notes.first()
        for code, label in EXPECTED.items():
            DeliveryNote.objects.filter(pk=note.pk).update(status=code)
            body = self._lookup(order).json()
            delivery = body["delivery"]
            if code == "CANCELLED":
                self.assertIsNone(delivery)  # phiếu đã huỷ theo đơn: không có khối giao (02b §3.4.2)
                continue
            self.assertEqual(delivery["step_label"], label, code)
            self.assertEqual(set(delivery), {"step", "step_label"})
            self.assertNotEqual(delivery["step_label"], code)
            self.assertIsNone(RAW_CODE.match(delivery["step_label"]))
            self.assertEqual(set(body), TOP_KEYS)

    def test_table_covers_every_delivery_status(self):
        self.assertEqual(set(SHOP_DELIVERY_STATUS_LABELS), set(DeliveryNote.Status.values))

    def test_unknown_delivery_status_never_returns_raw_code(self):
        order = self._paid_order(phone=PHONE)
        note = order.invoice.delivery_notes.first()
        DeliveryNote.objects.filter(pk=note.pk).update(status="FUTURE")
        body = self._lookup(order).json()
        self.assertIsNone(body["delivery"])  # mã lạ không có bước công khai -> không khối giao
        self.assertEqual(body["state"], "preparing")
        self.assertEqual(shop_delivery_status_label("FUTURE"), UNKNOWN_STATUS_LABEL)
        self.assertEqual(UNKNOWN_STATUS_LABEL, "Đang cập nhật")

    def test_paid_order_waiting_confirmation_label_kept(self):
        order = self._paid_order(phone=PHONE)
        body = self._lookup(order).json()
        self.assertEqual(body["status_label"], "Đã thanh toán – chờ vựa gọi xác nhận")

    def test_no_personal_data_in_response(self):
        order = self._paid_order(phone=PHONE)
        raw = self._lookup(order).content.decode()
        self.assertNotIn(PHONE, raw)
        self.assertNotIn("Chị Hoa", raw)
        self.assertNotIn("Lê Lợi", raw)
