"""TEM-01 (AC1-AC4): SĐT trên tem chỉ hiện 4 số cuối; `mask_phone` cũ giữ nguyên. Dữ liệu giả."""
from django.test import SimpleTestCase

from apps.common.pii import mask_phone, mask_phone_tail


class MaskPhoneLast4Tests(SimpleTestCase):
    def test_tem01_ac1_plain_number(self):
        self.assertEqual(mask_phone_tail("0901234567"), "xxxxxx4567")

    def test_tem01_ac2_normalized_formats(self):
        for raw in ("+84 901 234 567", "84901234567", "090.123.4567", "0901 234 567", " 090-123-4567 "):
            with self.subTest(raw=raw):
                self.assertEqual(mask_phone_tail(raw), "xxxxxx4567")

    def test_tem01_ac3_empty_or_short(self):
        for raw in ("", None, "123", "ab", "+84"):
            with self.subTest(raw=raw):
                self.assertEqual(mask_phone_tail(raw), "***")

    def test_tem01_ac3_exactly_four_digits(self):
        self.assertEqual(mask_phone_tail("4567"), "xxxxxx4567")

    def test_tem01_ac4_old_mask_phone_unchanged(self):
        self.assertEqual(mask_phone("0901234567"), "09xx xxx 567")
        self.assertEqual(mask_phone("123"), "***")
