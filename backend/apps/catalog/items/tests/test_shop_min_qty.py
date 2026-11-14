"""
FISH-66 S1: API danh mục Shop với mức tối thiểu mặc định 0,5 kg (BR-BH-22, BR-BH-23, bất biến 1 và 9).
Kiểm giá trị MẶC ĐỊNH nên không override settings. Dữ liệu giả.
"""
import json
from decimal import Decimal

from apps.catalog.items import services

from .test_shop_catalog import FORBIDDEN_KEYS, ShopCatalogBase, all_keys


class HalfKgCatalogTests(ShopCatalogBase):
    def test_s1_ac6_below_half_kg_is_out(self):
        self.item("DUOI04", kg="0.4")
        self.assertEqual(self.level("DUOI04"), "out")

    def test_s1_ac7_exactly_half_kg_is_low(self):
        self.item("DUOI05", kg="0.5")
        self.assertEqual(self.level("DUOI05"), "low")

    def test_s1_ac8_min_qty_and_step_in_list_and_detail(self):
        fish = self.item("CA", kg="10")
        self.combo("COMBO", [(fish, "0.5")])
        rows = {row["item_code"]: row for row in self.catalog()["items"]}
        self.assertEqual((rows["CA"]["min_qty"], rows["CA"]["qty_step"]), ("0.5", "0.5"))
        self.assertEqual((rows["COMBO"]["min_qty"], rows["COMBO"]["qty_step"]), ("1", "1"))
        for code, expected in (("CA", ("0.5", "0.5")), ("COMBO", ("1", "1"))):
            body = self.client.get(f"/api/shop/catalog/{code}/").json()
            self.assertEqual((body["min_qty"], body["qty_step"]), expected)

    def test_s1_ac8_service_rule_default(self):
        fish = self.item("CA2")
        self.assertEqual(services.qty_rule(fish), (Decimal("0.5"), Decimal("0.5")))

    def test_s1_ac12_guest_catalog_has_no_cost_batch_or_stock_numbers(self):
        self.item("CA3", kg="0.5")
        body = self.catalog()
        self.assertFalse(set(all_keys(body)) & FORBIDDEN_KEYS)
        raw = json.dumps(body)
        self.assertNotIn("80000", raw)
