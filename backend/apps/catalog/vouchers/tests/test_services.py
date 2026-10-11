"""SHOP-3b-01/03/04 — tính giảm, so ưu đãi tự động, chia vào dòng (BR-DM-17…21, 24). Hàm thuần, không gọi API."""
import datetime
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.catalog.models import Voucher
from apps.catalog.vouchers import services

from .base import make_voucher

D = Decimal


class ComputeDiscountTests(TestCase):
    def test_s3b_03_ac1_percent_hits_cap_amount(self):
        v = make_voucher()  # 10% trần 50.000
        self.assertEqual(services.compute_discount(v, D("556000")), D("50000"))  # 55.600 chạm trần

    def test_percent_below_cap_is_floored_to_whole_vnd(self):
        v = make_voucher(value=D("10"), max_discount=D("500000"))
        self.assertEqual(services.compute_discount(v, D("333335")), D("33333"))  # 33333.5 làm tròn XUỐNG

    def test_s3b_03_ac6_amount_voucher_capped_at_fifty_percent_of_cart(self):
        v = make_voucher(code="TIEN400", kind=Voucher.Kind.AMOUNT, value=D("400000"), max_discount=None)
        self.assertEqual(services.compute_discount(v, D("600000")), D("300000"))

    @override_settings(VOUCHER_MAX_PERCENT=D("30"))
    def test_cap_percent_comes_from_settings(self):
        v = make_voucher(code="TIEN400", kind=Voucher.Kind.AMOUNT, value=D("400000"), max_discount=None)
        self.assertEqual(services.compute_discount(v, D("600000")), D("180000"))

    @override_settings(VOUCHER_MAX_PERCENT=D("100"))
    def test_total_after_discount_is_always_positive_even_with_cap_100(self):
        v = make_voucher(code="TIEN400", kind=Voucher.Kind.AMOUNT, value=D("400000"), max_discount=None)
        discount = services.compute_discount(v, D("300000"))
        self.assertLess(discount, D("300000"))
        self.assertEqual(D("300000") - discount, D("1"))


class EvaluateTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.v = make_voucher()

    def evaluate(self, **kw):
        args = dict(voucher=self.v, subtotal=D("556000"), auto_discount=D("0"), now=self.now, committed=0)
        args.update(kw)
        return services.evaluate_voucher(**args)

    def test_valid(self):
        r = self.evaluate()
        self.assertTrue(r.valid)
        self.assertEqual(r.discount, D("50000"))
        self.assertIsNone(r.reason_code)

    def test_s3b_03_ac3_missing_code_not_started_and_disabled_are_invalid(self):
        self.assertEqual(self.evaluate(voucher=None).reason_code, "INVALID")
        future = make_voucher(code="SAUNAY", starts_at=self.now + datetime.timedelta(hours=1))
        self.assertEqual(self.evaluate(voucher=future).reason_code, "INVALID")
        self.v.is_active = False
        self.assertEqual(self.evaluate().reason_code, "INVALID")

    def test_s3b_03_ac3_after_end_is_expired(self):
        r = self.evaluate(now=self.v.ends_at + datetime.timedelta(seconds=1))
        self.assertEqual(r.reason_code, "EXPIRED")
        self.assertFalse(r.terms_visible)

    def test_s3b_03_ac4_used_up_when_held_plus_used_reach_total(self):
        r = self.evaluate(committed=100)
        self.assertEqual(r.reason_code, "USED_UP")
        self.assertEqual(self.evaluate(committed=99).reason_code, None)

    def test_s3b_03_ac2_min_order_has_missing_amount_and_terms(self):
        r = self.evaluate(subtotal=D("256000"))
        self.assertEqual((r.reason_code, r.missing_amount, r.terms_visible), ("MIN_ORDER", D("44000"), True))

    def test_min_order_compares_pre_discount_subtotal_exactly(self):
        self.assertTrue(self.evaluate(subtotal=D("300000")).valid)

    def test_s3b_03_ac5_better_or_equal_promo_wins(self):
        self.assertEqual(self.evaluate(auto_discount=D("60000")).reason_code, "BETTER_PROMO")
        self.assertEqual(self.evaluate(auto_discount=D("50000")).reason_code, "BETTER_PROMO")  # hoà
        self.assertTrue(self.evaluate(auto_discount=D("49999")).valid)

    def test_reason_order_invalid_expired_used_up_min_order_better_promo(self):
        expired_and_used = self.evaluate(now=self.v.ends_at, committed=100, subtotal=D("1"), auto_discount=D("9"))
        self.assertEqual(expired_and_used.reason_code, "EXPIRED")
        used_and_min = self.evaluate(committed=100, subtotal=D("1"))
        self.assertEqual(used_and_min.reason_code, "USED_UP")
        min_and_promo = self.evaluate(subtotal=D("100000"), auto_discount=D("90000"))
        self.assertEqual(min_and_promo.reason_code, "MIN_ORDER")


class AllocateTests(TestCase):
    def test_s3b_04_ac1_example_26978_plus_23022(self):
        self.assertEqual(services.allocate_whole_vnd(D("50000"), [D("300000"), D("256000")]), [D("26978"), D("23022")])

    def test_sum_always_equals_discount_and_every_share_is_whole_vnd(self):
        cases = [
            (D("50000"), [D("100000"), D("100000"), D("100000")]),
            (D("1"), [D("3"), D("3"), D("3")]),
            (D("99999"), [D("123457"), D("77777"), D("1")]),
            (D("10"), [D("5"), D("5")]),
        ]
        for discount, gross in cases:
            with self.subTest(discount=discount):
                shares = services.allocate_whole_vnd(discount, gross)
                self.assertEqual(sum(shares), discount)
                self.assertTrue(all(s == s.to_integral_value() and s >= 0 for s in shares))
                self.assertTrue(all(s <= g for s, g in zip(shares, gross)))

    def test_remainder_never_pushes_last_line_above_its_gross(self):
        shares = services.allocate_whole_vnd(D("5"), [D("100"), D("1")])  # 4 + dư 1 = 5 > gộp dòng cuối 1? đúng 4 và 1
        self.assertEqual(sum(shares), D("5"))
        self.assertLessEqual(shares[1], D("1"))

    def test_empty_or_zero(self):
        self.assertEqual(services.allocate_whole_vnd(D("0"), [D("10")]), [D("0")])
        self.assertEqual(services.allocate_whole_vnd(D("10"), []), [])


class NormalizeTests(TestCase):
    def test_spaces_and_case(self):
        self.assertEqual(services.normalize_code(" cave 10 "), "CAVE10")
        self.assertEqual(services.normalize_code(None), "")
