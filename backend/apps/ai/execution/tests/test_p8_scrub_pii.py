"""
P8 Lô 2 — SR-04-AC2: `scrub_data` bỏ CẢ NHÁNH của khoá PII khách (bất biến 9, H2).
Dữ liệu chỉ là sentinel giả.
"""

from apps.ai.execution.scrub import scrub_data
from apps.ai.policy.rules import SCRUB_PII_KEYS
from apps.common.tests.fixtures import make_user
from django.test import TestCase


class ScrubCustomerBranchTests(TestCase):
    def setUp(self):
        self.chu = make_user("chu_scrub_p8", "chu")

    def test_sr04_ac2_customer_dang_chuoi_bi_bo(self):
        res = scrub_data({"code": "SO-1", "customer": "Khách Giả Bí Mật"}, user=self.chu)
        self.assertEqual(res, {"code": "SO-1"})

    def test_sr04_ac2_customer_dang_dict_bi_bo_ca_nhanh(self):
        raw = {
            "code": "SO-1",
            "customer": {"name": "Khách Giả Bí Mật", "phone": "0900000123", "address": "Số 1 Đường Giả"},
        }
        res = scrub_data(raw, user=self.chu)
        self.assertEqual(res, {"code": "SO-1"})
        self.assertNotIn("Khách Giả Bí Mật", str(res))

    def test_sr04_ac2_customer_dang_list_long_nhau_bi_bo(self):
        raw = {"rows": [{"code": "SO-1", "customer": {"name": "Khách Giả Bí Mật"}}]}
        res = scrub_data(raw, user=self.chu)
        self.assertEqual(res, {"rows": [{"code": "SO-1"}]})

    def test_sr04_ac2_khoa_sdt_che_bi_bo(self):
        raw = {
            "code": "SO-1",
            "recipient_phone": "0900000123",
            "recipient_phone_masked": "09xx xxx 123",
            "phone_last4": "0123",
            "phone_masked": "09xx xxx 123",
            "customer_address": "Số 1 Đường Giả",
        }
        self.assertEqual(scrub_data(raw, user=self.chu), {"code": "SO-1"})

    def test_sr04_ac2_khoa_khong_phan_biet_hoa_thuong(self):
        res = scrub_data({"Customer": {"name": "Khách Giả Bí Mật"}, "code": "SO-1"}, user=self.chu)
        self.assertEqual(res, {"code": "SO-1"})

    def test_sr04_ac2_tap_khoa_pii_du_khoa_moi(self):
        for key in ("customer", "recipient_phone", "recipient_phone_masked", "phone_last4",
                    "phone_masked", "customer_address"):
            self.assertIn(key, SCRUB_PII_KEYS)
