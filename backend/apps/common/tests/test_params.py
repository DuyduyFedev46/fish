"""Hàm parse id nguyên dương dùng chung cho tham số lọc (`apps/common/params.py`)."""
from django.test import SimpleTestCase

from apps.common.exceptions import BusinessError
from apps.common.params import MAX_ID, month_bounds, parse_positive_id


class ParsePositiveIdTests(SimpleTestCase):
    def test_accepts_plain_ascii_digits_up_to_int64(self):
        self.assertEqual(parse_positive_id("1"), 1)
        self.assertEqual(parse_positive_id("0042"), 42)
        self.assertEqual(parse_positive_id(str(MAX_ID)), MAX_ID)

    def test_rejects_non_positive_non_ascii_and_oversized(self):
        bad = [
            "", "0", "-3", "+5", " 5", "5 ", "abc", "1.5", "1e3",
            str(MAX_ID + 1), "99999999999999999999999",
            "1" * 5000,                     # quá giới hạn chuyển chuỗi sang số của Python
            "１２３",                       # chữ số toàn độ rộng
            "٣",                            # chữ số Ả Rập
            None, 5, True,
        ]
        for raw in bad:
            with self.assertRaises(ValueError, msg=repr(raw)):
                parse_positive_id(raw)


class MonthBoundsTests(SimpleTestCase):
    """`month_bounds` (R3/R9): tháng theo giờ VN, sai dạng → 400 INVALID_FILTER, không lặp lại giá trị gửi lên."""

    def test_returns_start_and_next_month_start_in_vietnam_time(self):
        start, end = month_bounds("2026-10")
        self.assertEqual(start.isoformat(), "2026-10-01T00:00:00+07:00")
        self.assertEqual(end.isoformat(), "2026-11-01T00:00:00+07:00")

    def test_december_rolls_over_to_next_year(self):
        start, end = month_bounds("2026-12")
        self.assertEqual((start.isoformat(), end.isoformat()), ("2026-12-01T00:00:00+07:00", "2027-01-01T00:00:00+07:00"))

    def test_year_bounds_are_inclusive(self):
        month_bounds("2000-01")
        month_bounds("2100-12")

    def test_rejects_bad_values_with_invalid_filter(self):
        bad = [
            "", "2026-1", "2026-13", "2026-00", "abcd-ef", "1999-12", "2101-01", "2026-10-01", "2026/10",
            "\n2026-10", "2026-10\n", " 2026-10", "２０２６-１０", None, 202610,
        ]
        for raw in bad:
            with self.assertRaises(BusinessError, msg=repr(raw)) as ctx:
                month_bounds(raw)
            self.assertEqual(ctx.exception.code, "INVALID_FILTER", repr(raw))
            self.assertEqual(str(ctx.exception), "Tham số month phải có dạng YYYY-MM.")
