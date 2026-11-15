"""
Rà soát bảo mật 15/11 (H-2, M-2): trần đặt hàng online chống đơn ảo giữ hết tồn/lượt mã. BR-BH-31 (và BR-BH-22/23/24).
Trần chạy TRƯỚC kiểm tồn nên lỗi thiếu hàng không còn dùng để dò số tồn. Dữ liệu giả.
"""
import datetime
import json
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone

from apps.catalog.models import Voucher
from apps.sales.models import SalesOrder

from .test_shop_create import ShopCreateBase

CAP_CODES = {"ORDER_LINE_TOO_LARGE", "ORDER_TOO_LARGE", "TOO_MANY_OPEN_ORDERS"}


class CapBase(ShopCreateBase):
    def setUp(self):
        super().setUp()
        self.fish = self._item("CA-THU", price="100000")
        self.batch = self._stocked_batch(self.fish, "50")

    def place(self, items, phone="0900000001", ip="10.0.0.1", **extra):
        body = {
            "customer": {"phone": phone, "name": "Khach Gia"},
            "delivery_address": "Dia chi gia",
            "items": [{"item_code": c, "qty": str(q)} for c, q in items],
            **extra,
        }
        return self.client.post("/api/shop/orders/", body, format="json", REMOTE_ADDR=ip)

    def reserved(self):
        self.batch.refresh_from_db()
        return self.batch.qty_reserved


class LineCapTests(CapBase):
    def test_bh31_normal_two_kg_order_still_works(self):
        self.assertEqual(self.place([("CA-THU", "2")]).status_code, 201)

    def test_bh31_exactly_at_line_cap_allowed_just_over_blocked(self):
        self.assertEqual(self.place([("CA-THU", "20")]).status_code, 201)
        r = self.place([("CA-THU", "20.5")], phone="0900000002", ip="10.0.0.2")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()["code"], "ORDER_LINE_TOO_LARGE")

    def test_bh31_line_cap_blocks_whole_order_without_holding(self):
        before = self.reserved()
        r = self.place([("CA-THU", "50")])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.reserved(), before)
        self.assertEqual(SalesOrder.objects.filter(phone="0900000001").count(), 0)

    def test_bh31_cap_is_env_parameter(self):
        with override_settings(SHOP_MAX_LINE_KG=Decimal("5")):
            self.assertEqual(self.place([("CA-THU", "5")]).status_code, 201)
            r = self.place([("CA-THU", "5.5")], phone="0900000002", ip="10.0.0.2")
            self.assertEqual(r.json()["code"], "ORDER_LINE_TOO_LARGE")

    def test_bh31_combo_line_cap(self):
        part = self._item("MUC-ONG", price="1000")
        self._stocked_batch(part, "500")
        self.combo("COMBO-LAU", [(part, "0.5")], price="1000")
        self.assertEqual(self.place([("COMBO-LAU", "10")]).status_code, 201)
        r = self.place([("COMBO-LAU", "11")], phone="0900000002", ip="10.0.0.2")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "ORDER_LINE_TOO_LARGE")

    def test_bh31_message_has_hotline_and_no_stock_number(self):
        with override_settings(SHOP_HOTLINE="0123 456 789"):
            r = self.place([("CA-THU", "50")])
        self.assertIn("0123 456 789", r.json()["detail"])
        text = json.dumps(r.json())
        self.assertNotIn("stock_level", text)
        self.assertNotIn("short", text)


class OrderCapTests(CapBase):
    def test_bh31_total_cap_exact_and_over(self):
        item = self._item("TOM", price="500000")
        self._stocked_batch(item, "100")
        # 20 kg * 500.000 = 10.000.000 đúng trần -> được
        self.assertEqual(self.place([("TOM", "20")]).status_code, 201)
        r = self.place([("TOM", "20"), ("CA-THU", "1")], phone="0900000002", ip="10.0.0.2")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()["code"], "ORDER_TOO_LARGE")

    def test_bh31_total_cap_checked_before_discount(self):
        item = self._item("TOM", price="600000")
        self._stocked_batch(item, "100")
        r = self.place([("TOM", "20")])
        self.assertEqual(r.json()["code"], "ORDER_TOO_LARGE")


class OpenOrderCapTests(CapBase):
    def test_bh31_third_open_order_same_phone_blocked_without_holding(self):
        for i in range(2):
            self.assertEqual(self.place([("CA-THU", "1")], ip=f"10.0.1.{i}").status_code, 201)
        before = self.reserved()
        r = self.place([("CA-THU", "1")], ip="10.0.1.9")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()["code"], "TOO_MANY_OPEN_ORDERS")
        self.assertEqual(self.reserved(), before)
        self.assertEqual(SalesOrder.objects.count(), 2)

    def test_bh31_phone_format_is_normalized(self):
        for i in range(2):
            self.assertEqual(self.place([("CA-THU", "1")], ip=f"10.0.1.{i}").status_code, 201)
        r = self.place([("CA-THU", "1")], phone="0900 000 001", ip="10.0.1.9")
        self.assertEqual(r.json()["code"], "TOO_MANY_OPEN_ORDERS")

    def test_bh31_sixth_open_order_same_ip_blocked(self):
        for i in range(5):
            r = self.place([("CA-THU", "1")], phone=f"09000001{i:02d}")
            self.assertEqual(r.status_code, 201, r.content)
        r = self.place([("CA-THU", "1")], phone="0900000199")
        self.assertEqual(r.json()["code"], "TOO_MANY_OPEN_ORDERS")
        # IP khác thì vẫn đặt được
        self.assertEqual(self.place([("CA-THU", "1")], phone="0900000199", ip="10.0.0.77").status_code, 201)

    def test_bh31_expired_or_paid_orders_do_not_count(self):
        for i in range(2):
            self.assertEqual(self.place([("CA-THU", "1")], ip=f"10.0.1.{i}").status_code, 201)
        first, second = SalesOrder.objects.order_by("pk")
        SalesOrder.objects.filter(pk=first.pk).update(booked_expires_at=timezone.now() - datetime.timedelta(minutes=1))
        SalesOrder.objects.filter(pk=second.pk).update(status=SalesOrder.Status.PROCESSING)
        self.assertEqual(self.place([("CA-THU", "1")], ip="10.0.1.9").status_code, 201)

    def test_bh31_caps_are_env_parameters(self):
        with override_settings(SHOP_MAX_OPEN_ORDERS_PER_PHONE=1):
            self.assertEqual(self.place([("CA-THU", "1")]).status_code, 201)
            r = self.place([("CA-THU", "1")], ip="10.0.9.9")
            self.assertEqual(r.json()["code"], "TOO_MANY_OPEN_ORDERS")

    def test_bh31_ip_is_not_stored_raw(self):
        self.place([("CA-THU", "1")], ip="203.0.113.9")
        order = SalesOrder.objects.get()
        self.assertNotIn("203.0.113.9", order.client_ip_hash)
        self.assertEqual(len(order.client_ip_hash), 64)


class NoOracleTests(CapBase):
    def test_bh31_probe_over_cap_gives_same_error_whatever_stock(self):
        """Đặt vượt trần cho cùng một lỗi dù tồn nhiều hay ít: không còn dò được số tồn."""
        r1 = self.place([("CA-THU", "50")])
        self.batch.qty_available = Decimal("1")
        self.batch.save(update_fields=["qty_available"])
        r2 = self.place([("CA-THU", "50")])
        self.assertEqual(r1.json(), r2.json())
        self.assertEqual(r1.json()["code"], "ORDER_LINE_TOO_LARGE")

    def test_bh31_single_order_cannot_lock_all_stock(self):
        self.assertEqual(self.place([("CA-THU", "50")]).status_code, 400)
        self.assertEqual(self.reserved(), Decimal("0"))
        self.assertEqual(self.client.get("/api/shop/catalog/CA-THU/").json()["stock_level"], "in")

    def test_bh31_in_cap_over_stock_error_keeps_existing_shape(self):
        small = self._item("OC", price="1000")
        self._stocked_batch(small, "3")
        r = self.place([("OC", "4")])
        self.assertEqual(r.json()["code"], "OUT_OF_STOCK")
        self.assertEqual(set(r.json()["lines"][0]), {"item_code", "stock_level"})


class VoucherNotHeldTests(CapBase):
    def test_bh31_rejected_order_does_not_hold_voucher(self):
        from django.contrib.auth.models import User
        owner = User.objects.create_user("owner_v", password="x")
        now = timezone.now()
        v = Voucher.objects.create(code="CAVE10", name="x", kind="AMOUNT", value=Decimal("10000"),
                                   starts_at=now - datetime.timedelta(hours=1), ends_at=now + datetime.timedelta(days=1),
                                   total_uses=2, created_by=owner)
        r = self.place([("CA-THU", "50")], voucher_code="CAVE10")
        self.assertEqual(r.json()["code"], "ORDER_LINE_TOO_LARGE")
        for i in range(2):
            ok = self.place([("CA-THU", "1")], phone=f"09000002{i:02d}", ip=f"10.0.2.{i}", voucher_code="CAVE10")
            self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(v.redemptions.count(), 2)  # chỉ 2 đơn hợp lệ giữ lượt

    def test_bh31_open_order_cap_rejection_does_not_hold_voucher(self):
        from django.contrib.auth.models import User
        owner = User.objects.create_user("owner_v2", password="x")
        now = timezone.now()
        Voucher.objects.create(code="CAVE10", name="x", kind="AMOUNT", value=Decimal("10000"),
                               starts_at=now - datetime.timedelta(hours=1), ends_at=now + datetime.timedelta(days=1),
                               total_uses=3, created_by=owner)
        for i in range(2):
            self.assertEqual(self.place([("CA-THU", "1")], ip=f"10.0.3.{i}").status_code, 201)
        r = self.place([("CA-THU", "1")], ip="10.0.3.9", voucher_code="CAVE10")
        self.assertEqual(r.json()["code"], "TOO_MANY_OPEN_ORDERS")
        chk = self.client.post("/api/shop/vouchers/check/",
                               {"code": "CAVE10", "items": [{"item_code": "CA-THU", "qty": "1"}]}, format="json")
        self.assertTrue(chk.json().get("valid", True), chk.json())
