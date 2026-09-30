"""
P8 Lô 7 — SR-22 / BM-07: scrub giá vốn dùng đúng một nguồn quyền `apps.common.cost_keys.can_view_cost`
(`inventory.view_costprice`). Quyền `reports.view_profitreport` (xem báo cáo lãi lỗ) KHÔNG đủ để AI thấy giá vốn.
Dữ liệu giả.
"""
from django.test import TestCase

from apps.ai.execution.scrub import scrub_data
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import make_user
from apps.accounts import roles


class Bm07ScrubCostTests(TestCase):
    RAW = {
        "batch_code": "CA01-260930-1",
        "unit_cost": "12000",
        "landed_unit_cost": "11000",
        "qty": "5",
        "lines": [{"item_code": "CA01", "purchase_rate": "13000", "qty": "2"}],
    }

    def test_bm07_chi_co_view_profitreport_van_bi_bo_khoa_gia_von(self):
        user = make_user("bm07_pnl", perms=("reports.view_profitreport",))
        res = scrub_data(self.RAW, user=user, is_ai_read=False)
        self.assertNotIn("unit_cost", res)
        self.assertNotIn("landed_unit_cost", res)
        self.assertNotIn("purchase_rate", res["lines"][0])
        self.assertEqual(res["qty"], "5")
        self.assertEqual(res["lines"][0]["qty"], "2")

    def test_bm07_co_view_costprice_thay_gia_von(self):
        user = make_user("bm07_cost", perms=("inventory.view_costprice",))
        res = scrub_data(self.RAW, user=user, is_ai_read=False)
        self.assertEqual(res["unit_cost"], "12000")
        self.assertEqual(res["lines"][0]["purchase_rate"], "13000")

    def test_bm07_nhom_khong_co_view_costprice_khong_thay(self):
        for group in (roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE, roles.MANAGER):
            with self.subTest(group=group):
                user = make_user(f"bm07_{group}", group)
                res = scrub_data(self.RAW, user=user, is_ai_read=False)
                for key in COST_KEYS & set(self.RAW):
                    self.assertNotIn(key, res)

    def test_bm07_chua_dang_nhap_khong_thay(self):
        from django.contrib.auth.models import AnonymousUser
        res = scrub_data(self.RAW, user=AnonymousUser(), is_ai_read=False)
        self.assertNotIn("unit_cost", res)
