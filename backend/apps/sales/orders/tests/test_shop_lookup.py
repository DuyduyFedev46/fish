"""
SHOP-3-02 — tra đơn Shop bằng POST (mã + SĐT đầy đủ hoặc mã tra đơn), gỡ GET 4 số cuối. BR-BH-25, 26; bất biến 9; V-02.
`state` đúng mọi hàng bảng E6 (02b §3.4.2). Dữ liệu giả (tên "Chị Hoa", SĐT 09xxxxxxxx, địa chỉ "12 Lê Lợi").
"""
import base64
import datetime
import json
import logging
import time
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.delivery.models import DeliveryNote
from apps.sales.models import PaymentTransaction, SalesOrder
from apps.sales.orders import lookup_token, services
from apps.sales.orders.tests.test_s10_api import OrderApiBase

PHONE = "0901234567"
NAME = "Chị Hoa"
ADDRESS = "12 Lê Lợi, Vũng Tàu"
URL = "/api/shop/orders/lookup/"
KEYS = {
    "order_code", "status", "state", "status_label", "placed_at", "paid_at", "delivered_at", "booked_expires_at",
    "server_now", "hold_minutes", "payment_pending_minutes", "delivery", "lines", "subtotal", "discount",
    "total_amount", "cancel_notice", "late_payment", "lookup_token",
}
S = DeliveryNote.Status
O = SalesOrder.Status


def lookup(body, **extra):
    return APIClient().post(URL, body, format="json", **extra)


class LookupBase(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = self.chu  # naming: allow - thuộc tính của OrderApiBase dùng chung

    def tearDown(self):
        cache.clear()

    def by_phone(self, order, phone=PHONE, **extra):
        return lookup({"order_code": order.code, "phone": phone}, **extra)

    def set_state(self, order, order_status, note_status=None):
        SalesOrder.objects.filter(pk=order.pk).update(status=order_status)
        if note_status is not None:
            DeliveryNote.objects.filter(sales_invoice=order.invoice).update(status=note_status)
        order.refresh_from_db()


class LookupAccessTests(LookupBase):
    def test_s3_02_ac1_phone_and_token_both_return_full_payload_with_fresh_token(self):
        order = self._order(phone=PHONE)
        by_phone = self.by_phone(order)
        self.assertEqual(by_phone.status_code, 200, by_phone.content)
        data = by_phone.json()
        self.assertEqual(set(data), KEYS)
        self.assertEqual(data["order_code"], order.code)
        self.assertEqual(data["state"], "awaiting_payment")
        self.assertEqual(data["status_label"], "Chờ thanh toán")
        self.assertEqual(data["hold_minutes"], 30)
        self.assertEqual(data["payment_pending_minutes"], 5)
        by_token = lookup({"order_code": order.code, "token": data["lookup_token"]})
        self.assertEqual(by_token.status_code, 200)
        self.assertEqual(by_token.json()["order_code"], order.code)
        self.assertTrue(by_token.json()["lookup_token"])
        self.assertEqual(by_phone["Cache-Control"], "no-store")

    def test_s3_02_ac1_phone_forms_and_code_case_are_accepted(self):
        order = self._order(phone=PHONE)
        for typed in ("0901234567", "+84901234567", "84901234567", "0901 234 567", " 090.123.4567 "):
            with self.subTest(typed=typed):
                self.assertEqual(lookup({"order_code": order.code.lower(), "phone": typed}).status_code, 200)

    def test_s3_02_ac1_token_wins_when_both_given(self):
        order = self._order(phone=PHONE)
        token = self.by_phone(order).json()["lookup_token"]
        resp = lookup({"order_code": order.code, "phone": "0999999999", "token": token})
        self.assertEqual(resp.status_code, 200)

    def test_s3_02_ac2_every_wrong_input_gives_the_same_404(self):
        order = self._order(phone=PHONE)
        other = self._order(phone="0907654321")
        other_token = lookup({"order_code": other.code, "phone": "0907654321"}).json()["lookup_token"]
        attempts = [
            {"order_code": order.code, "phone": "0900000000"},                 # sai SĐT
            {"order_code": "SO000000-AAAAAA", "phone": PHONE},                  # sai mã
            {"order_code": "SO000000-AAAAAA", "phone": "0900000000"},           # sai cả hai
            {"order_code": order.code, "token": other_token},                   # token của đơn khác
            {"order_code": order.code, "token": "rac.khong.hop.le"},            # token hỏng
            {"order_code": order.code, "phone": "abc"},                         # SĐT không phải số
            {"order_code": order.code, "phone": "4567"},                        # 4 số cuối không đủ
        ]
        bodies = set()
        for body in attempts:
            with self.subTest(body=body):
                resp = lookup(body)
                self.assertEqual(resp.status_code, 404, resp.content)
                self.assertEqual(
                    resp.json(),
                    {"code": "ORDER_NOT_FOUND", "detail": "Không tìm thấy đơn khớp mã và số điện thoại."},
                )
                bodies.add(resp.content)
        self.assertEqual(len(bodies), 1)

    def test_s3_02_ac2_four_last_digits_alone_no_longer_work(self):
        order = self._order(phone=PHONE)
        self.assertEqual(lookup({"order_code": order.code, "phone": PHONE[-4:]}).status_code, 404)
        self.assertEqual(lookup({"order_code": order.code, "phone_last4": PHONE[-4:]}).status_code, 400)

    def test_s3_02_ac3_expired_token_is_401(self):
        order = self._order(phone=PHONE)
        token = lookup_token.make_token(order.code)
        later = time.time() + 31 * 86400
        with mock.patch("django.core.signing.time.time", return_value=later):
            resp = lookup({"order_code": order.code, "token": token})
        self.assertEqual(resp.status_code, 401, resp.content)
        self.assertEqual(
            resp.json(), {"code": "TOKEN_EXPIRED", "detail": "Phiên xem đơn đã hết hạn. Nhập số điện thoại để xem lại."}
        )
        # còn trong hạn 30 ngày thì dùng được; hạn đọc từ settings
        with mock.patch("django.core.signing.time.time", return_value=time.time() + 29 * 86400):
            self.assertEqual(lookup({"order_code": order.code, "token": token}).status_code, 200)
        with override_settings(SHOP_LOOKUP_TOKEN_DAYS=1), mock.patch(
            "django.core.signing.time.time", return_value=time.time() + 2 * 86400
        ):
            self.assertEqual(lookup({"order_code": order.code, "token": token}).status_code, 401)

    def test_s3_02_token_payload_has_only_order_code(self):
        order = self._order(phone=PHONE, name=NAME)
        token = self.by_phone(order).json()["lookup_token"]
        part = token.split(":")[0]
        decoded = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)).decode()
        self.assertEqual(json.loads(decoded), {"o": order.code})
        for secret in (PHONE, NAME, "Lê Lợi"):
            self.assertNotIn(secret, decoded)

    def test_s3_02_validation_when_phone_and_token_both_missing(self):
        order = self._order(phone=PHONE)
        for body in ({}, {"order_code": order.code}, {"phone": PHONE}, {"order_code": "", "phone": ""}, {"order_code": 5, "phone": 7}):
            with self.subTest(body=body):
                resp = lookup(body)
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "VALIDATION")
                self.assertIn("fields", resp.json())

    def test_s3_02_ac7_get_route_is_removed(self):
        order = self._order(phone=PHONE)
        client = APIClient()
        for url in (f"/api/shop/orders/{order.code}/", f"/api/shop/orders/{order.code}/?phone_last4={PHONE[-4:]}"):
            self.assertEqual(client.get(url).status_code, 404, url)
        self.assertEqual(client.post(f"/api/shop/orders/{order.code}/", {}, format="json").status_code, 404)
        self.assertEqual(client.get(URL).status_code, 405)

    def test_s3_02_lookup_never_changes_order_state(self):
        order = self._order(phone=PHONE)
        before = (SalesOrder.objects.get(pk=order.pk).status, SalesOrder.objects.count())
        self.by_phone(order)
        self.assertEqual((SalesOrder.objects.get(pk=order.pk).status, SalesOrder.objects.count()), before)


class LookupPrivacyTests(LookupBase):
    def test_s3_02_ac5_lookup_never_returns_pii(self):
        order = self._paid_order(phone=PHONE)
        order.customer.name = NAME
        order.customer.save(update_fields=["name"])
        SalesOrder.objects.filter(pk=order.pk).update(cancel_note="gọi 0900000001")
        for resp in (self.by_phone(order), lookup({"order_code": order.code, "token": lookup_token.make_token(order.code)})):
            raw = resp.content.decode()
            for secret in (PHONE, PHONE[1:], "+84" + PHONE[1:], "84" + PHONE[1:], PHONE[-4:], NAME, "Chị", "Hoa",
                           ADDRESS, "Lê Lợi", "Vũng Tàu", "0900000001", "cancel_note"):
                self.assertNotIn(secret, raw, secret)
            for forbidden in ("customer", "phone", "address", "recipient", "refund", "confirmation", "batch",
                              "unit_cost", "purchase_rate", "landed", "qty_available", "assigned_to", "courier"):
                self.assertNotIn(f'"{forbidden}', raw, forbidden)

    def test_s3_02_ac5_walk_all_keys_for_internal_names(self):
        order = self._paid_order(phone=PHONE)
        names = set()

        def walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    names.add(key)
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(self.by_phone(order).json())
        for bad in ("customer", "phone", "delivery_address", "cancel_note", "note", "batch_id", "refund", "deadline",
                    "refunded_at", "confirmation"):
            self.assertNotIn(bad, names)

    def test_s3_02_ac7_wrong_credentials_do_not_leak_cancel_notice(self):
        order = self._paid_order(phone=PHONE)
        services.cancel_paid_order(order=order, actor=self.owner, reason_code="DAMAGED_WHEN_PACKING")
        resp = self.by_phone(order, phone="0900000000")
        self.assertEqual(resp.status_code, 404)
        for leak in ("cancel_notice", "Hàng không đạt", "CANCELLED", "Đã huỷ"):
            self.assertNotIn(leak, resp.content.decode())

    def test_s3_02_ac8_logs_have_only_order_code_and_masked_phone(self):
        class Capture(logging.Handler):
            def __init__(self):
                super().__init__(level=logging.DEBUG)
                self.lines = []

            def emit(self, record):
                self.lines.append(record.getMessage())
                self.lines.append(json.dumps(record.__dict__, default=str, ensure_ascii=False))

        order = self._order(phone=PHONE, name=NAME)
        capture = Capture()
        root = logging.getLogger()
        previous = root.level
        root.addHandler(capture)
        root.setLevel(logging.DEBUG)
        try:
            self.by_phone(order)
            self.by_phone(order, phone="0900000000")
            lookup({"order_code": order.code, "token": "hong"})
        finally:
            root.removeHandler(capture)
            root.setLevel(previous)
        joined = "\n".join(capture.lines)
        for secret in (PHONE, PHONE[1:], "0900000000", NAME, "Lê Lợi"):
            self.assertNotIn(secret, joined)
        self.assertIn(order.code, joined)
        self.assertIn("09xx xxx 000", joined)  # SĐT đã che

    def test_s3_02_response_stays_free_of_consent_keys(self):
        order = self._order(phone=PHONE)
        data = self.by_phone(order).json()
        for key in ("privacy_consent", "privacy_consent_at", "privacy_policy_version"):
            self.assertNotIn(key, data)


class LookupThrottleTests(LookupBase):
    @override_settings(CAVEVE_THROTTLE_RATES={"shop_lookup_ip": "3/min"})
    def test_s3_02_ac4_ip_throttle_on_phone_lookup(self):
        order = self._order(phone=PHONE)
        for _ in range(3):
            self.assertEqual(self.by_phone(order, phone="0900000000", REMOTE_ADDR="10.9.0.1").status_code, 404)
        self.assertEqual(self.by_phone(order, REMOTE_ADDR="10.9.0.1").status_code, 429)

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_lookup_order": "2/hour"})
    def test_s3_02_ac4_phone_lookup_throttled_by_order_code_from_body_across_ips(self):
        order = self._order(phone=PHONE)
        for i in (1, 2):
            self.assertEqual(self.by_phone(order, phone="0900000000", REMOTE_ADDR=f"10.9.1.{i}").status_code, 404)
        self.assertEqual(self.by_phone(order, REMOTE_ADDR="10.9.1.3").status_code, 429)
        # mã đơn khác không bị ảnh hưởng
        other = self._order(phone="0907654321")
        self.assertEqual(self.by_phone(other, phone="0907654321", REMOTE_ADDR="10.9.1.4").status_code, 200)

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_lookup_order": "2/hour", "shop_lookup_ip": "2/min", "shop_lookup_token": "5/min"})
    def test_s3_02_token_lookup_has_its_own_ip_limit_not_counted_in_code_or_ip_limits(self):
        order = self._order(phone=PHONE)
        token = lookup_token.make_token(order.code)
        for _ in range(5):
            self.assertEqual(lookup({"order_code": order.code, "token": token}, REMOTE_ADDR="10.9.2.1").status_code, 200)
        self.assertEqual(lookup({"order_code": order.code, "token": token}, REMOTE_ADDR="10.9.2.1").status_code, 429)
        # đường SĐT của cùng IP và cùng mã vẫn còn đủ hạn riêng
        self.assertEqual(self.by_phone(order, REMOTE_ADDR="10.9.2.1").status_code, 200)
        # IP khác dùng token vẫn được
        self.assertEqual(lookup({"order_code": order.code, "token": token}, REMOTE_ADDR="10.9.2.2").status_code, 200)

    def test_s3_02_default_rates_are_defined(self):
        from django.conf import settings as real_settings

        # CAVEVE_THROTTLE_RATES tắt khi TESTING; kiểm hằng mặc định bằng cách đọc lại module
        import importlib
        import os

        import config.settings as cfg

        self.assertTrue(hasattr(cfg, "_DEFAULT_THROTTLE_RATES"))
        self.assertEqual(cfg._DEFAULT_THROTTLE_RATES["shop_lookup_token"], "60/min")
        self.assertEqual(cfg._DEFAULT_THROTTLE_RATES["shop_lookup_order"], "10/hour")
        self.assertEqual(cfg._DEFAULT_THROTTLE_RATES["shop_lookup_ip"], "20/min")
        del real_settings, importlib, os

    @override_settings(CAVEVE_THROTTLE_RATES={"shop_lookup_ip": "1/min"})
    def test_s3_02_malformed_json_body_does_not_crash_throttle(self):
        resp = APIClient().post(URL, "{khong phai json", content_type="application/json")
        self.assertIn(resp.status_code, (400, 429))


class LookupTimesTests(LookupBase):
    def test_s3_02_ac6_paid_and_delivered_times_are_utc_iso_and_match_source(self):
        order = self._paid_order(phone=PHONE)
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        done = timezone.now().replace(microsecond=0)
        DeliveryNote.objects.filter(pk=note.pk).update(status=S.COMPLETED, completed_at=done)
        SalesOrder.objects.filter(pk=order.pk).update(status=O.COMPLETED)
        data = self.by_phone(order).json()

        def utc(dt):
            return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        order.refresh_from_db()
        self.assertEqual(data["placed_at"], utc(order.created_at))
        self.assertEqual(data["paid_at"], utc(order.invoice.issued_at))
        self.assertEqual(data["delivered_at"], utc(done))
        self.assertEqual(data["state"], "completed")
        self.assertIsNone(data["booked_expires_at"])
        for key in ("placed_at", "paid_at", "delivered_at", "server_now"):
            self.assertRegex(data[key], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_s3_02_unpaid_order_has_no_paid_or_delivered_time_and_expiry_in_utc(self):
        order = self._order(phone=PHONE)
        data = self.by_phone(order).json()
        self.assertIsNone(data["paid_at"])
        self.assertIsNone(data["delivered_at"])
        self.assertEqual(
            data["booked_expires_at"], order.booked_expires_at.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        self.assertIsNone(data["delivery"])

    def test_s3_02_lines_subtotal_and_total_match_order(self):
        order = self._order(phone=PHONE, qty="2")
        data = self.by_phone(order).json()
        self.assertEqual(
            data["lines"], [{"item_code": "TOM-SU-1", "name": "Tôm sú loại 1", "unit": "kg", "qty": "2", "amount": "540000"}]
        )
        self.assertEqual(data["subtotal"], "540000")
        self.assertEqual(data["total_amount"], "540000")
        self.assertEqual(data["discount"], {"source": None, "code": None, "amount": "0"})


class StateTableTests(LookupBase):
    """Mọi hàng bảng E6 (02b §3.4.2) và `delivery.step`."""

    def state_of(self, order):
        data = self.by_phone(order).json()
        return data["state"], data["status_label"], data["delivery"], data

    def test_awaiting_payment_then_hold_expired_by_clock_only(self):
        order = self._order(phone=PHONE)
        state, label, delivery, data = self.state_of(order)
        self.assertEqual((state, label, delivery), ("awaiting_payment", "Chờ thanh toán", None))
        SalesOrder.objects.filter(pk=order.pk).update(booked_expires_at=timezone.now() - datetime.timedelta(seconds=1))
        state, label, _, data = self.state_of(order)
        self.assertEqual((state, label), ("hold_expired", "Chờ thanh toán"))
        self.assertEqual(data["status"], "BOOKED")  # job chưa chạy, server thắng bằng đồng hồ

    def test_expired_when_auto_cancelled_without_money(self):
        order = self._order(phone=PHONE)
        services.cancel_unpaid_expired(now=timezone.now() + datetime.timedelta(hours=2))
        order.refresh_from_db()
        self.assertEqual(order.status, O.AUTO_CANCELLED)
        state, label, delivery, data = self.state_of(order)
        self.assertEqual((state, label, delivery), ("expired", "Đã huỷ vì quá giờ thanh toán", None))
        self.assertFalse(data["late_payment"])
        self.assertIsNone(data["cancel_notice"])
        self.assertIsNone(data["booked_expires_at"])

    def test_cancelled_by_owner(self):
        order = self._paid_order(phone=PHONE)
        services.cancel_paid_order(order=order, actor=self.owner, reason_code="CUSTOMER_CHANGED_MIND")
        state, label, delivery, data = self.state_of(order)
        self.assertEqual((state, label), ("cancelled", "Đã huỷ"))
        self.assertIsNone(delivery)  # phiếu giao CANCELLED -> không có khối
        self.assertFalse(data["late_payment"])
        self.assertEqual(data["cancel_notice"]["scope"], "full")

    def test_cancelled_when_money_arrives_after_auto_cancel(self):
        order = self._order(phone=PHONE)
        services.cancel_unpaid_expired(now=timezone.now() + datetime.timedelta(hours=2))
        order.refresh_from_db()
        from apps.sales.payments import services as payment_services

        payment_services.confirm_payment(
            order=order, bank_txn_id="FT2626799001", amount=order.total_amount, received_at=timezone.now(),
        )
        order.refresh_from_db()
        self.assertEqual(order.status, O.AUTO_CANCELLED)
        self.assertTrue(PaymentTransaction.objects.filter(sales_order=order).exists())
        state, label, _, data = self.state_of(order)
        self.assertEqual((state, label), ("cancelled", "Đã huỷ"))
        self.assertTrue(data["late_payment"])

    def test_preparing_rows_and_labels(self):
        order = self._paid_order(phone=PHONE)
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        rows = [
            (O.PAID, None, "Đã thanh toán – chờ vựa gọi xác nhận"),
            (O.PROCESSING, S.CONFIRMING, "Đã thanh toán – chờ vựa gọi xác nhận"),
            (O.PROCESSING, S.PREPARING, "Đang chuẩn bị hàng"),
            (O.PROCESSING, S.READY, "Đang chuẩn bị hàng"),
        ]
        for order_status, note_status, expected in rows:
            with self.subTest(order_status=order_status, note_status=note_status):
                self.set_state(order, order_status, note_status or note.status)
                state, label, delivery, _ = self.state_of(order)
                self.assertEqual((state, label), ("preparing", expected))
                self.assertEqual(delivery["step"], "preparing")

    def test_paid_order_without_delivery_note_is_preparing(self):
        from apps.sales.orders import shop_state

        order = self._paid_order(phone=PHONE)
        for status in (O.PAID, O.PROCESSING):
            order.status = status
            self.assertEqual(shop_state.order_state(order, now=timezone.now(), note=None), "preparing")
        self.assertIsNone(shop_state.delivery_block(None))
        self.assertEqual(shop_state.state_label("preparing", None), "Đang chuẩn bị hàng")

    def test_delivering_failed_and_completed_rows(self):
        order = self._paid_order(phone=PHONE)
        self.set_state(order, O.PROCESSING, S.DELIVERING)
        state, label, delivery, _ = self.state_of(order)
        self.assertEqual((state, label), ("delivering", "Đang giao"))
        self.assertEqual(delivery, {"step": "delivering", "step_label": "Đang giao"})

        self.set_state(order, O.PROCESSING, S.FAILED)
        state, label, delivery, _ = self.state_of(order)
        self.assertEqual((state, label), ("delivery_failed", "Giao không thành công"))
        self.assertEqual(delivery["step"], "failed")

        self.set_state(order, O.COMPLETED, S.COMPLETED)
        state, label, delivery, _ = self.state_of(order)
        self.assertEqual((state, label), ("completed", "Đã giao"))
        self.assertEqual(delivery, {"step": "delivered", "step_label": "Đã giao"})

    def test_delivery_step_mapping_covers_every_note_status(self):
        order = self._paid_order(phone=PHONE)
        expected = {
            S.CONFIRMING: "preparing", S.PREPARING: "preparing", S.READY: "preparing", S.DELIVERING: "delivering",
            S.COMPLETED: "delivered", S.FAILED: "failed", S.CANCELLED: None,
        }
        for note_status, step in expected.items():
            with self.subTest(note_status=note_status):
                self.set_state(order, O.PROCESSING, note_status)
                delivery = self.by_phone(order).json()["delivery"]
                self.assertEqual(delivery["step"] if delivery else None, step)
                if delivery:
                    self.assertEqual(set(delivery), {"step", "step_label"})

    def test_every_state_value_is_one_of_the_eight(self):
        allowed = {"awaiting_payment", "hold_expired", "expired", "cancelled", "preparing", "delivering",
                   "delivery_failed", "completed"}
        order = self._paid_order(phone=PHONE)
        for order_status in SalesOrder.Status.values:
            for note_status in (None, *DeliveryNote.Status.values):
                self.set_state(order, order_status, note_status)
                self.assertIn(self.by_phone(order).json()["state"], allowed, (order_status, note_status))


class CancelNoticeTests(LookupBase):
    def notice(self, order):
        return self.by_phone(order).json()["cancel_notice"]

    def test_s4_05_ac1_full_cancel_matches_contract_without_refund_keys(self):
        order = self._paid_order(phone=PHONE)
        services.cancel_paid_order(order=order, actor=self.owner, reason_code="DAMAGED_WHEN_PACKING")
        data = self.by_phone(order).json()
        notice = data["cancel_notice"]
        self.assertEqual(
            notice,
            {
                "scope": "full",
                "reason_code": "DAMAGED_WHEN_PACKING",
                "reason_label": "Hàng không đạt khi soạn",
                "cancelled_amount": "540000",
                "message": "Cá Về sẽ gọi vào số điện thoại đặt hàng trong 1 ngày làm việc để trả lại 540.000đ.",
                "hotline": "1900 xxxx",
                "policy_url": "/pages/?slug=doi-tra#xu-ly-tien",
            },
        )

    def test_s4_05_ac1_cancel_notice_has_no_refund_keys_or_word(self):
        order = self._paid_order(phone=PHONE)
        services.cancel_paid_order(order=order, actor=self.owner, reason_code="CUSTOMER_CHANGED_MIND")
        from apps.sales.refunds import services as refund_services

        refund_services.create_refund(invoice=order.invoice, amount=order.total_amount, is_partial=False,
                                      reason="khách đổi ý", actor=self.owner)
        raw = json.dumps(self.notice(order), ensure_ascii=False)
        self.assertEqual(
            set(self.notice(order)),
            {"scope", "reason_code", "reason_label", "cancelled_amount", "message", "hotline", "policy_url"},
        )
        for key in ("refund", "deadline", "refunded_at", "status_label"):
            self.assertNotIn(key, raw)
        self.assertNotIn("hoàn", raw.lower())
        self.assertNotIn("refund", self.by_phone(order).content.decode().lower())

    @override_settings(SHOP_CANCEL_CALLBACK_WITHIN="2 giờ", SHOP_CANCEL_POLICY_URL="/pages/?slug=abc", SHOP_HOTLINE="1900 0000")
    def test_s4_05_callback_deadline_hotline_and_url_come_from_settings(self):
        order = self._paid_order(phone=PHONE)
        services.cancel_paid_order(order=order, actor=self.owner, reason_code="CUSTOMER_CHANGED_MIND")
        notice = self.notice(order)
        self.assertIn("trong 2 giờ để trả lại", notice["message"])
        self.assertEqual(notice["hotline"], "1900 0000")
        self.assertEqual(notice["policy_url"], "/pages/?slug=abc")

    def test_s4_05_ac2_other_reason_note_is_never_leaked(self):
        order = self._paid_order(phone=PHONE)
        services.cancel_paid_order(order=order, actor=self.owner, reason_code="OTHER", cancel_note="khách nhờ gọi lại ở Lê Lợi")
        SalesOrder.objects.filter(pk=order.pk).update(cancel_note="gọi 0900000001")
        data = self.by_phone(order).json()
        raw = json.dumps(data, ensure_ascii=False)
        self.assertNotIn("0900000001", raw)
        self.assertNotIn("gọi", raw.replace("Cá Về sẽ gọi vào số điện thoại đặt hàng", ""))
        self.assertNotIn("Lê Lợi", raw)
        self.assertEqual(data["cancel_notice"]["reason_code"], "OTHER")
        self.assertEqual(data["cancel_notice"]["reason_label"], "Cá Về đã huỷ đơn này")

    def test_s4_05_unknown_or_blank_reason_codes_fall_back_to_generic_label(self):
        from apps.sales.models import SalesCreditNote

        order = self._paid_order(phone=PHONE)
        services.cancel_paid_order(order=order, actor=self.owner, reason_code="CUSTOMER_CHANGED_MIND")
        for code in ("", "WHATEVER", "gọi 0900000001"):
            with self.subTest(code=code):
                SalesCreditNote.objects.filter(sales_invoice=order.invoice).update(reason_code=code)
                notice = self.notice(order)
                self.assertEqual(notice["reason_label"], "Cá Về đã huỷ đơn này")
                self.assertEqual(notice["reason_code"], "OTHER")
                self.assertNotIn("0900000001", json.dumps(notice, ensure_ascii=False))

    def test_s4_05_public_label_table_is_fixed(self):
        from apps.sales.orders.customer_notices import PUBLIC_CANCEL_REASON_LABELS as labels

        self.assertEqual(
            labels,
            {
                "CUSTOMER_CHANGED_MIND": "Huỷ theo yêu cầu của bạn",
                "DAMAGED_WHEN_PACKING": "Hàng không đạt khi soạn",
                "GIVE_UP_AFTER_FAILED": "Giao không thành công",
                "UNREACHABLE": "Không liên lạc được để xác nhận đơn",
                "UNREACHABLE_AUTO": "Không liên lạc được để xác nhận đơn",
                "PAID_AFTER_EXPIRY": "Hết giờ giữ hàng, tiền về sau",
                "PARTIAL": "Một phần đơn không giao được",
            },
        )

    def test_s4_05_ac3_partial_refund_gives_partial_notice_with_partial_amount(self):
        from apps.sales.refunds import services as refund_services

        order = self._paid_order(phone=PHONE)
        self.set_state(order, O.PROCESSING, S.PREPARING)
        refund_services.create_refund(invoice=order.invoice, amount="135000", is_partial=True, reason="thiếu hàng", actor=self.owner)
        data = self.by_phone(order).json()
        self.assertEqual(data["state"], "preparing")
        notice = data["cancel_notice"]
        self.assertEqual(notice["scope"], "partial")
        self.assertEqual(notice["reason_code"], "PARTIAL")
        self.assertEqual(notice["reason_label"], "Một phần đơn không giao được")
        self.assertEqual(notice["cancelled_amount"], "135000")
        self.assertIn("135.000đ", notice["message"])
        self.assertEqual(data["total_amount"], "540000")  # tổng đơn không đổi
        self.assertNotIn("reason\":", json.dumps(notice))

    def test_s4_05_ac3_failed_partial_refund_is_ignored_and_two_are_summed(self):
        from apps.sales.models import Refund
        from apps.sales.refunds import services as refund_services

        order = self._paid_order(phone=PHONE)
        self.set_state(order, O.PROCESSING, S.PREPARING)
        failed = refund_services.create_refund(invoice=order.invoice, amount="50000", is_partial=True, reason="", actor=self.owner)
        Refund.objects.filter(pk=failed.pk).update(status=Refund.Status.FAILED)
        self.assertIsNone(self.notice(order))
        refund_services.create_refund(invoice=order.invoice, amount="100000", is_partial=True, reason="", actor=self.owner)
        refund_services.create_refund(invoice=order.invoice, amount="35000", is_partial=True, reason="", actor=self.owner)
        self.assertEqual(self.notice(order)["cancelled_amount"], "135000")

    def test_s4_05_full_refund_on_processing_order_is_not_a_partial_notice(self):
        from apps.sales.refunds import services as refund_services

        order = self._paid_order(phone=PHONE)
        self.set_state(order, O.PROCESSING, S.PREPARING)
        refund_services.create_refund(invoice=order.invoice, amount="540000", is_partial=False, reason="", actor=self.owner)
        self.assertIsNone(self.notice(order))

    def test_s4_05_completed_order_with_refund_has_no_notice(self):
        from apps.sales.refunds import services as refund_services

        order = self._paid_order(phone=PHONE)
        refund_services.create_refund(invoice=order.invoice, amount="10000", is_partial=True, reason="", actor=self.owner)
        self.set_state(order, O.COMPLETED, S.COMPLETED)
        self.assertIsNone(self.notice(order))

    def test_s4_05_ac4_late_payment_notice(self):
        from apps.sales.payments import services as payment_services

        order = self._order(phone=PHONE)
        services.cancel_unpaid_expired(now=timezone.now() + datetime.timedelta(hours=2))
        order.refresh_from_db()
        payment_services.confirm_payment(
            order=order, bank_txn_id="FT2626799002", amount=order.total_amount, received_at=timezone.now(),
        )
        data = self.by_phone(order).json()
        self.assertTrue(data["late_payment"])
        notice = data["cancel_notice"]
        self.assertEqual(notice["scope"], "full")
        self.assertEqual(notice["reason_code"], "PAID_AFTER_EXPIRY")
        self.assertEqual(notice["reason_label"], "Hết giờ giữ hàng, tiền về sau")
        self.assertEqual(notice["cancelled_amount"], "540000")
        self.assertIn("540.000đ", notice["message"])

    def test_s4_05_late_payment_amount_skips_suspected_duplicate_rows(self):
        from apps.sales.payments import services as payment_services

        order = self._order(phone=PHONE)
        services.cancel_unpaid_expired(now=timezone.now() + datetime.timedelta(hours=2))
        order.refresh_from_db()
        payment_services.confirm_payment(order=order, bank_txn_id="FT2626799003", amount=order.total_amount, received_at=timezone.now())
        payment_services.confirm_payment(order=order, bank_txn_id="FT2626799004", amount=order.total_amount, received_at=timezone.now())
        PaymentTransaction.objects.filter(bank_txn_id="FT2626799004").update(duplicate_warning="nghi trùng")
        self.assertEqual(self.notice(order)["cancelled_amount"], "540000")

    def test_s4_05_ac5_unreachable_auto_label(self):
        order = self._paid_order(phone=PHONE)
        services.cancel_paid_order(order=order, actor=None, reason_code="UNREACHABLE_AUTO")
        notice = self.notice(order)
        self.assertEqual(notice["reason_code"], "UNREACHABLE_AUTO")
        self.assertEqual(notice["reason_label"], "Không liên lạc được để xác nhận đơn")

    def test_s4_05_expired_order_has_no_notice(self):
        order = self._order(phone=PHONE)
        services.cancel_unpaid_expired(now=timezone.now() + datetime.timedelta(hours=2))
        self.assertIsNone(self.notice(order))
