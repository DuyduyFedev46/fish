"""
Lô dọn chữ AI, W1 và W2 (02b 2.4) — Shop tra đơn không bao giờ trả mã thô hay chữ kỹ thuật ("TTL").
Chỉ đổi chuỗi nhãn, không thêm key. Bảng nhãn theo doc/thuat-ngu-va-trang-thai.md mục 4 (T2, T24–T30). Dữ liệu giả.
"""
import re

from django.test import override_settings
from rest_framework.test import APIClient

from apps.delivery.models import DeliveryNote
from apps.sales.models import SalesOrder
from apps.sales.orders.shop_labels import SHOP_DELIVERY_STATUS_LABELS, UNKNOWN_STATUS_LABEL
from apps.sales.orders.tests.test_s10_api import OrderApiBase

PHONE = "0900000456"
RAW_CODE = re.compile(r"^[A-Z_]+$")
EXPECTED = {
    "CONFIRMING": "Chờ vựa gọi xác nhận",
    "PREPARING": "Đang soạn hàng",
    "READY": "Đã soạn xong, chờ giao",
    "DELIVERING": "Đang giao",
    "COMPLETED": "Đã giao",
    "FAILED": "Giao chưa thành công, vựa sẽ liên hệ lại",
    "CANCELLED": "Đã huỷ",
}
TOP_KEYS = {"order_code", "status", "status_label", "total_amount", "lines", "delivery", "booked_expires_at",
            "cancel_notice"}


class ShopLookupLabelTests(OrderApiBase):
    def _lookup(self, order):
        return APIClient().get(f"/api/shop/orders/{order.code}/", {"phone_last4": PHONE[-4:]})

    def test_auto_cancelled_label_is_plain_vietnamese(self):
        order = self._order(phone=PHONE)
        SalesOrder.objects.filter(pk=order.pk).update(status=SalesOrder.Status.AUTO_CANCELLED)
        body = self._lookup(order).json()
        self.assertEqual(body["status_label"], "Đã huỷ vì quá giờ thanh toán")
        self.assertNotIn("TTL", str(body))
        self.assertEqual(set(body), TOP_KEYS)

    def test_delivery_status_labels_match_table(self):
        order = self._paid_order(phone=PHONE)
        note = order.invoice.delivery_notes.first()
        for code, label in EXPECTED.items():
            DeliveryNote.objects.filter(pk=note.pk).update(status=code)
            body = self._lookup(order).json()
            self.assertEqual(body["delivery"]["status_label"], label, code)
            self.assertEqual(set(body["delivery"]), {"status", "status_label"})
            self.assertNotEqual(body["delivery"]["status_label"], code)
            self.assertIsNone(RAW_CODE.match(body["delivery"]["status_label"]))
            self.assertEqual(set(body), TOP_KEYS)

    def test_table_covers_every_delivery_status(self):
        self.assertEqual(set(SHOP_DELIVERY_STATUS_LABELS), set(DeliveryNote.Status.values))

    def test_unknown_delivery_status_never_returns_raw_code(self):
        order = self._paid_order(phone=PHONE)
        note = order.invoice.delivery_notes.first()
        DeliveryNote.objects.filter(pk=note.pk).update(status="FUTURE_STATUS")
        body = self._lookup(order).json()
        self.assertEqual(body["delivery"]["status_label"], UNKNOWN_STATUS_LABEL)
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
