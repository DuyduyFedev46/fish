"""TD-03: một hàm định dạng số kg kiểu Việt Nam dùng chung (dấu phẩy)."""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.sales.utils import kg_vn_str


class KgVnStrTests(SimpleTestCase):
    def test_td03_comma_decimal_and_trims_trailing_zero(self):
        cases = [
            (Decimal("0.5"), "0,5"),
            (Decimal("1"), "1"),
            (Decimal("1.0"), "1"),
            (Decimal("1.500"), "1,5"),
            (Decimal("12.25"), "12,25"),
            ("0.5", "0,5"),
            (2, "2"),
            (Decimal("10"), "10"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(kg_vn_str(value), expected)
