"""SHOP-3b-03 — POST /api/shop/vouchers/check/: lý do, so ưu đãi tự động, trần, throttle, không rò (BR-DM-18, 21, 24)."""
import datetime
import json
from decimal import Decimal

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import PricingRule
from apps.sales.models import SalesOrder, VoucherRedemption
from apps.sales.orders.tests.base import SalesServiceBase

from .base import make_voucher
from .test_api import make_order

URL = "/api/shop/vouchers/check/"
D = Decimal


class CheckBase(SalesServiceBase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.a = self._item("MUC-A", price="150000")   # 2 kg = 300.000
        self.b = self._item("MUC-B", price="128000")   # 2 kg = 256.000
        for item in (self.a, self.b):
            self._stocked_batch(item, "40")
        self.voucher = make_voucher()
        self.cart = [{"item_code": "MUC-A", "qty": "2"}, {"item_code": "MUC-B", "qty": "2"}]  # 556.000

    def check(self, code="CAVE10", items=None, **extra):
        body = {"items": items if items is not None else self.cart, **extra}
        if code is not None:
            body["code"] = code
        return self.client.post(URL, body, format="json")


class CheckReasonTests(CheckBase):
    def test_s3b_03_ac1_valid_code_any_case_and_spaces(self):
        for typed in ("cave10", "cave 10", " Cave10 "):
            with self.subTest(typed):
                response = self.check(typed)
                self.assertEqual(response.status_code, 200, response.content)
                data = response.json()
                self.assertEqual((data["code"], data["valid"], data["reason_code"]), ("CAVE10", True, None))
                self.assertEqual((data["subtotal"], data["discount_amount"], data["total_after"], data["auto_discount_amount"]),
                                 ("556000", "50000", "506000", "0"))
                self.assertEqual(data["applied"], {"source": "voucher", "amount": "50000"})
                self.assertIsNone(data["missing_amount"])

    def test_terms_have_everything_the_cart_needs(self):
        terms = self.check().json()["terms"]
        self.assertEqual(set(terms), {"kind", "value", "max_discount", "min_order_amount", "starts_at", "ends_at",
                                      "customer_terms"})
        self.assertEqual((terms["kind"], terms["value"], terms["max_discount"], terms["min_order_amount"]),
                         ("PERCENT", "10", "50000", "300000"))
        self.assertTrue(terms["ends_at"].endswith("Z"))
        self.assertEqual(terms["customer_terms"], "Áp dụng cho đơn từ 300.000đ.")

    def test_amount_voucher_terms_have_no_max_discount(self):
        make_voucher(code="GIAM30K", kind="AMOUNT", value=D("30000"), max_discount=None, min_order_amount=D("0"))
        data = self.check("GIAM30K").json()
        self.assertEqual((data["valid"], data["discount_amount"]), (True, "30000"))
        self.assertIsNone(data["terms"]["max_discount"])
        self.assertEqual(data["terms"]["min_order_amount"], "0")

    def test_s3b_03_ac2_min_order_reports_missing_amount(self):
        data = self.check(items=[{"item_code": "MUC-B", "qty": "2"}]).json()
        self.assertEqual((data["valid"], data["reason_code"], data["missing_amount"]), (False, "MIN_ORDER", "44000"))
        self.assertEqual((data["subtotal"], data["discount_amount"], data["total_after"]), ("256000", "0", "256000"))
        self.assertEqual(data["applied"], {"source": None, "amount": "0"})
        self.assertEqual(data["terms"]["min_order_amount"], "300000")

    def test_s3b_03_ac3_unknown_not_started_and_disabled_are_invalid_without_terms(self):
        make_voucher(code="SAUNAY01", starts_at=timezone.now() + datetime.timedelta(hours=1))
        make_voucher(code="DATAT001", is_active=False)
        for code in ("KHONGCO1", "SAUNAY01", "DATAT001"):
            with self.subTest(code):
                data = self.check(code).json()
                self.assertEqual((data["valid"], data["reason_code"], data["terms"]), (False, "INVALID", None))

    def test_s3b_03_ac3_expired(self):
        make_voucher(code="HETHAN01", starts_at=timezone.now() - datetime.timedelta(days=9),
                     ends_at=timezone.now() - datetime.timedelta(minutes=1))
        data = self.check("HETHAN01").json()
        self.assertEqual((data["valid"], data["reason_code"], data["terms"]), (False, "EXPIRED", None))

    def test_s3b_03_ac4_used_up_counts_held_plus_used_and_hides_the_numbers(self):
        v = make_voucher(code="HETLUOT1", total_uses=2)
        for i, state in enumerate(("HELD", "USED")):
            VoucherRedemption.objects.create(order=make_order(f"090000020{i}"), voucher=v, code=v.code,
                                             discount_amount=D("1000"), state=state)
        response = self.check("HETLUOT1")
        data = response.json()
        self.assertEqual((data["valid"], data["reason_code"], data["terms"]), (False, "USED_UP", None))
        text = response.content.decode().lower()
        for hidden in ("remaining", "left", "held", "used_count", "total_uses", "lượt", "redemption"):
            self.assertNotIn(hidden, text)

    def test_released_redemption_does_not_count(self):
        v = make_voucher(code="MOTLUOT1", total_uses=1)
        VoucherRedemption.objects.create(order=make_order("0900000300"), voucher=v, code=v.code, discount_amount=D("1000"),
                                         state="RELEASED")
        self.assertTrue(self.check("MOTLUOT1").json()["valid"])

    def test_s3b_03_ac5_better_or_equal_auto_promo_wins(self):
        PricingRule.objects.create(name="Giảm 60k", apply_on="ORDER", min_amount=D("100000"), discount_type="AMOUNT",
                                   discount_value=D("60000"))
        data = self.check().json()
        self.assertEqual((data["valid"], data["reason_code"], data["auto_discount_amount"]), (False, "BETTER_PROMO", "60000"))
        self.assertEqual((data["discount_amount"], data["applied"], data["total_after"]),
                         ("0", {"source": "promo", "amount": "60000"}, "496000"))
        self.assertIsNotNone(data["terms"])

    def test_tie_goes_to_auto_promo(self):
        PricingRule.objects.create(name="Giảm 50k", apply_on="ORDER", min_amount=D("100000"), discount_type="AMOUNT",
                                   discount_value=D("50000"))
        self.assertEqual(self.check().json()["reason_code"], "BETTER_PROMO")

    def test_smaller_auto_promo_loses_to_voucher_and_is_not_added(self):
        PricingRule.objects.create(name="Giảm 20k", apply_on="ORDER", min_amount=D("100000"), discount_type="AMOUNT",
                                   discount_value=D("20000"))
        data = self.check().json()
        self.assertTrue(data["valid"])
        self.assertEqual((data["discount_amount"], data["auto_discount_amount"], data["total_after"]),
                         ("50000", "20000", "506000"))  # không cộng dồn: 556000 − 50000

    def test_s3b_03_ac6_amount_voucher_is_capped_at_half_the_cart(self):
        make_voucher(code="TIEN400K", kind="AMOUNT", value=D("400000"), max_discount=None, min_order_amount=D("0"))
        data = self.check("TIEN400K", items=[{"item_code": "MUC-A", "qty": "4"}]).json()  # 600.000
        self.assertEqual((data["discount_amount"], data["total_after"]), ("300000", "300000"))

    def test_no_code_quotes_the_cart_and_auto_promo_only(self):
        data = self.check(None).json()
        self.assertEqual((data["code"], data["valid"], data["reason_code"], data["terms"]), (None, None, None, None))
        self.assertEqual((data["subtotal"], data["applied"], data["total_after"]),
                         ("556000", {"source": None, "amount": "0"}, "556000"))
        PricingRule.objects.create(name="Giảm 60k", apply_on="ORDER", min_amount=D("100000"), discount_type="AMOUNT",
                                   discount_value=D("60000"))
        data = self.check(None).json()
        self.assertEqual((data["applied"], data["auto_discount_amount"], data["total_after"]),
                         ({"source": "promo", "amount": "60000"}, "60000", "496000"))
        self.assertEqual(self.check("   ").json()["code"], None)

    def test_total_after_is_whole_vnd_and_positive(self):
        data = self.check().json()
        self.assertRegex(data["total_after"], r"^[1-9]\d*$")


class CheckInputTests(CheckBase):
    def test_validation_errors(self):
        for items in ([], None, [{"item_code": "MUC-A", "qty": "abc"}], [{"item_code": "MUC-A", "qty": "2"}] * 2):
            with self.subTest(items=items):
                response = self.client.post(URL, {"code": "CAVE10", "items": items}, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "VALIDATION")
                self.assertIn("items", response.json()["fields"])

    @override_settings(SHOP_MAX_ORDER_LINES=1)
    def test_too_many_lines(self):
        self.assertEqual(self.check().status_code, 400)

    def test_unsellable_item_is_validation(self):
        response = self.check(items=[{"item_code": "KHONGCO", "qty": "2"}])
        self.assertEqual((response.status_code, response.json()["code"]), (400, "VALIDATION"))
        self.a.is_active = False
        self.a.save()
        self.assertEqual(self.check(items=[{"item_code": "MUC-A", "qty": "2"}]).json()["code"], "VALIDATION")

    def test_invalid_qty_lists_lines(self):
        response = self.check(items=[{"item_code": "MUC-A", "qty": "0.3"}])
        self.assertEqual((response.status_code, response.json()["code"]), (400, "INVALID_QTY"))
        self.assertEqual(response.json()["lines"][0]["item_code"], "MUC-A")

    def test_get_is_405_and_no_store_header(self):
        self.assertEqual(self.client.get(URL).status_code, 405)
        self.assertEqual(self.check().headers["Cache-Control"], "no-store")

    def test_non_string_code_is_treated_as_no_code(self):
        self.assertIsNone(self.check(123456).json()["valid"])


class CheckSafetyTests(CheckBase):
    def test_s3b_03_ac7_throttled_per_ip(self):
        with override_settings(CAVEVE_THROTTLE_RATES={"shop_voucher_check": "3/min"}):
            codes = [self.check().status_code for _ in range(4)]
        self.assertEqual(codes, [200, 200, 200, 429])

    def test_default_rate_is_20_per_minute(self):
        from config import settings as config_settings

        self.assertEqual(config_settings._DEFAULT_THROTTLE_RATES["shop_voucher_check"], "20/min")

    def test_s3b_03_ac8_no_other_codes_orders_cost_or_stock_numbers(self):
        make_voucher(code="KHAC9999", name="Mã bí mật khác")
        order = make_order("0900000400")
        VoucherRedemption.objects.create(order=order, voucher=self.voucher, code="CAVE10", discount_amount=D("50000"))
        response = self.check()
        text = response.content.decode()
        for hidden in ("KHAC9999", "Mã bí mật khác", order.code, "0900000400", "Khách Giả", "Đường Thử", "unit_cost",
                       "purchase_rate", "landed", "profit", "margin", "batch", "sellable", "qty_available", "created_by"):
            self.assertNotIn(hidden, text)
        self.assertNotIn("40", [str(v) for v in json.loads(text).values()])  # tồn 40 kg không lộ

    def test_invalid_code_response_is_identical_for_unknown_and_disabled(self):
        make_voucher(code="DATAT001", is_active=False)
        a, b = self.check("KHONGCO1").json(), self.check("DATAT001").json()
        a.pop("code"), b.pop("code")
        self.assertEqual(a, b)  # không phân biệt "không có mã" với "đã tắt"

    def test_check_never_creates_orders_or_holds(self):
        self.check()
        self.assertEqual(SalesOrder.objects.count(), 0)
        self.assertEqual(VoucherRedemption.objects.count(), 0)
