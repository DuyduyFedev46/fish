"""
W37 L3 (S8-AC1..AC5, AC7): Shop tra đơn với đơn Hoàn tất. BR-BH-18 (Q5), BR-PQ-11, bất biến 9.
Bảng nhãn theo 02b §2.6 (7 dòng) và doc/thuat-ngu-va-trang-thai.md mục 4. Dữ liệu giả (SĐT 0900000xxx).
"""
import json

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.delivery.models import DeliveryNote
from apps.delivery.tests.test_order_completion import ADDRESS, NAME, PHONE, CompletionBase
from apps.sales.models import SalesOrder

S = DeliveryNote.Status
O = SalesOrder.Status
TOP_KEYS = {"order_code", "status", "status_label", "total_amount", "lines", "delivery", "booked_expires_at",
            "cancel_notice"}

# (order.status, delivery.status, status_label, delivery.status_label): đủ 7 dòng bảng §2.6
TABLE = [
    (O.PROCESSING, S.CONFIRMING, "Đã thanh toán – chờ vựa gọi xác nhận", "Chờ vựa gọi xác nhận"),
    (O.PROCESSING, S.PREPARING, "Đang xử lý", "Đang soạn hàng"),
    (O.PROCESSING, S.READY, "Đang xử lý", "Đã soạn xong, chờ giao"),
    (O.PROCESSING, S.DELIVERING, "Đang xử lý", "Đang giao"),
    (O.PROCESSING, S.FAILED, "Đang xử lý", "Giao chưa thành công, vựa sẽ liên hệ lại"),
    (O.COMPLETED, S.COMPLETED, "Hoàn tất", "Đã giao"),
    (O.CANCELLED, S.CANCELLED, "Đã huỷ", "Đã huỷ"),
]


class ShopLookupCompletedTests(CompletionBase):
    def tearDown(self):
        cache.clear()

    def _lookup(self, order, last4=PHONE[-4:], **extra):
        return APIClient().get(f"/api/shop/orders/{order.code}/", {"phone_last4": last4}, **extra)

    def _completed(self):
        order, note = self._processing()
        self._complete(self.courier, note)
        order.refresh_from_db()
        self.assertEqual(order.status, O.COMPLETED)
        return order

    def test_s8_ac1_completed_order_label_and_delivery(self):
        resp = self._lookup(self._completed())
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], "COMPLETED")
        self.assertEqual(body["status_label"], "Hoàn tất")
        self.assertEqual(body["delivery"], {"status": "COMPLETED", "status_label": "Đã giao"})

    def test_s8_ac2_label_table_all_seven_rows(self):
        order = self._paid_order(phone=PHONE)
        note = order.invoice.delivery_notes.first()
        for order_status, note_status, label, note_label in TABLE:
            SalesOrder.objects.filter(pk=order.pk).update(status=order_status)
            DeliveryNote.objects.filter(pk=note.pk).update(status=note_status)
            body = self._lookup(order).json()
            ctx = f"{order_status}/{note_status}"
            self.assertEqual(body["status_label"], label, ctx)
            self.assertEqual(body["delivery"]["status_label"], note_label, ctx)
            self.assertNotEqual(body["status_label"], body["status"], ctx)

    def test_s8_ac3_key_set_unchanged_and_no_personal_data(self):
        order = self._completed()
        resp = self._lookup(order)
        body = resp.json()
        self.assertEqual(set(body), TOP_KEYS)
        self.assertEqual(set(body["delivery"]), {"status", "status_label"})
        raw = json.dumps(body, ensure_ascii=False)
        for secret in (PHONE, NAME, ADDRESS, "Lê Lợi", "completed_at", "assigned_to", "courier", "giao1"):
            self.assertNotIn(secret, raw)
        self.assertNotIn(self.courier.get_username(), raw)

    def test_s8_ac3_key_set_same_as_processing_order(self):
        processing, _ = self._processing()
        self.assertEqual(set(self._lookup(processing).json()), TOP_KEYS)

    def test_s8_ac4_wrong_last4_is_404_without_status_leak(self):
        order = self._completed()
        resp = self._lookup(order, last4="0000")
        self.assertEqual(resp.status_code, 404)
        raw = resp.content.decode()
        for leak in ("Hoàn tất", "COMPLETED", "Đã giao"):
            self.assertNotIn(leak, raw)

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_lookup_ip": "3/min"})
    def test_s8_ac5_ip_throttle_applies_to_completed_order(self):
        order = self._completed()
        for i in range(3):
            self.assertEqual(self._lookup(order, REMOTE_ADDR="192.168.7.7").status_code, 200, i)
        self.assertEqual(self._lookup(order, REMOTE_ADDR="192.168.7.7").status_code, 429)

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_lookup_order": "2/hour"})
    def test_s8_ac5_order_code_throttle_across_ips(self):
        order = self._completed()
        for i in (1, 2):
            self.assertEqual(self._lookup(order, REMOTE_ADDR=f"10.7.0.{i}").status_code, 200)
        self.assertEqual(self._lookup(order, REMOTE_ADDR="10.7.0.3").status_code, 429)

    def test_s8_ac7_anonymous_cannot_change_order_status(self):
        order, note = self._processing()
        anon = APIClient()
        resp = anon.post(f"/api/delivery/notes/{note.pk}/status/",
                         {"to_status": S.COMPLETED, "from_status": S.DELIVERING}, format="json")
        self.assertIn(resp.status_code, (401, 403))
        cancel = anon.post(f"/api/sales/orders/{order.pk}/cancel/", {}, format="json")
        self.assertIn(cancel.status_code, (401, 403, 404, 405))
        order.refresh_from_db()
        note.refresh_from_db()
        self.assertEqual(order.status, O.PROCESSING)
        self.assertEqual(note.status, S.DELIVERING)
