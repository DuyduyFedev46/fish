"""
TL12-num (Lô 17a, A4): `/api/reports/*` trả tiền và kg dạng CHUỖI Decimal (không còn float).

Tiền: 2 chữ số thập phân ("1000000.00"). Kg (khoá `qty_*`, `*_qty`): 3 chữ số ("50.000"). Số đếm (int) và `bool` giữ nguyên.
Chỉ đổi ở tầng API; `services.batch_pnl`/`period_pnl` vẫn trả Decimal. Không thêm hay bớt khoá. Dữ liệu giả.
"""
from decimal import Decimal

from django.test import TestCase

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_batch, make_master, make_user
from apps.reports import services
from apps.reports.decimal_strings import stringify_decimals

QTY_KEYS = {"qty_received", "qty_sold", "reversed_qty", "shrinkage_qty", "damage_qty", "expired_qty", "supplier_return_qty"}


class StringifyDecimalsUnitTests(TestCase):
    def test_m1_unit_cost_suffix_uses_four_places(self):
        out = stringify_decimals({"landed_unit_cost": Decimal("85333.33335"), "unit_cost": Decimal("1")})
        self.assertEqual(out, {"landed_unit_cost": "85333.3334", "unit_cost": "1.0000"})

    def test_money_two_places_qty_three_places_ints_and_bools_kept(self):
        out = stringify_decimals({
            "revenue": Decimal("1000000"), "qty_sold": Decimal("12.5"), "supplier_return_qty": Decimal("1"),
            "invoice_count": 3, "provisional": True, "name": "x", "nested": [{"profit": Decimal("-5.005")}],
        })
        self.assertEqual(out["revenue"], "1000000.00")
        self.assertEqual(out["qty_sold"], "12.500")
        self.assertEqual(out["supplier_return_qty"], "1.000")
        self.assertEqual(out["invoice_count"], 3)
        self.assertIs(out["provisional"], True)
        self.assertEqual(out["name"], "x")
        self.assertEqual(out["nested"][0]["profit"], "-5.01")  # ROUND_HALF_UP, không dùng làm tròn chẵn


class ReportsDecimalStringApiTests(TestCase):
    def setUp(self):
        item, sup, wh = make_master()
        self.batch = make_batch(item, sup, wh, qty="20")
        self.owner = make_user("chu1", roles.OWNER)
        self.client = client_for(self.owner)

    def assert_matches_service(self, body, expected):
        for key, value in expected.items():
            if isinstance(value, Decimal):
                self.assertIsInstance(body[key], str, key)
                self.assertEqual(Decimal(body[key]), value, key)
                places = 4 if key.endswith("unit_cost") else 3 if key in QTY_KEYS else 2
                self.assertEqual(len(body[key].split(".")[1]), places, key)
            else:
                self.assertEqual(body[key], value, key)

    def test_batch_report_money_and_kg_are_strings_equal_to_service(self):
        body = self.client.get(f"/api/reports/batch/{self.batch.batch_id}/").json()
        expected = services.batch_pnl(batch=self.batch)
        self.assertEqual(set(body), set(expected))  # không thêm/bớt khoá
        self.assert_matches_service(body, expected)
        self.assertIs(body["provisional"], True)

    def test_m1_unit_cost_keeps_four_decimal_places(self):
        from apps.inventory.models import Batch
        Batch.objects.filter(pk=self.batch.pk).update(landed_unit_cost=Decimal("85333.3333"))
        self.batch.refresh_from_db()
        for body in (
            self.client.get(f"/api/reports/batch/{self.batch.batch_id}/").json(),
            self.client.get("/api/reports/batches/").json()["results"][0],
        ):
            self.assertEqual(body["landed_unit_cost"], "85333.3333")
            self.assertEqual(Decimal(body["landed_unit_cost"]), self.batch.landed_unit_cost)

    def test_batches_list_rows_are_strings(self):
        body = self.client.get("/api/reports/batches/").json()
        self.assertGreaterEqual(body["count"], 1)
        row = body["results"][0]
        self.assertIsInstance(row["profit"], str)
        self.assertIsInstance(row["qty_received"], str)
        self.assertEqual(row["item_name"], "Cá thu")

    def test_period_report_money_strings_and_counts_stay_int(self):
        from django.utils import timezone
        today = timezone.localdate()
        body = self.client.get("/api/reports/period/", {"year": today.year, "month": today.month}).json()
        expected = services.period_pnl(year=today.year, month=today.month)
        self.assert_matches_service(body, expected)
        self.assertIsInstance(body["invoice_count"], int)
        self.assertIsInstance(body["refund_count"], int)
        self.assertIsInstance(body["year"], int)

    def test_without_view_profitreport_still_403_for_all_three(self):
        manager = make_user("ql1", roles.MANAGER)
        warehouse_staff = make_user("kho1", roles.WAREHOUSE_STAFF)
        urls = (f"/api/reports/batch/{self.batch.batch_id}/", "/api/reports/batches/", "/api/reports/period/?year=2026&month=10")
        for user in (manager, warehouse_staff):
            for url in urls:
                self.assertEqual(client_for(user).get(url).status_code, 403, url)
        for url in urls:
            self.assertEqual(client_for(None).get(url).status_code, 401, url)
