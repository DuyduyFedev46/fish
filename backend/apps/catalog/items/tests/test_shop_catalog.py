"""
SHOP-2-01 — catalog công khai trả `{groups, items}` với mức tồn (BR-BH-23), đơn vị, tối thiểu, bước.
G1 (không số kg tồn) và G3 (không giá vốn, mã lô) kiểm trên toàn bộ JSON, không chỉ vài khoá.
Dữ liệu giả.
"""
import datetime
import json
import re
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.items import services
from apps.catalog.models import BundleLine, Item, ItemGroup, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier

# Khoá không bao giờ được xuất hiện ở bất kỳ độ sâu nào của JSON Shop (G1, G3).
FORBIDDEN_KEYS = {
    "sellable_qty", "available_qty", "stock_qty", "qty_available", "qty_reserved", "on_hand",
    "purchase_rate", "landed_unit_cost", "unit_cost", "rate", "batch_id", "batch_code", "batch",
    "supplier", "margin", "profit",
}


def all_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from all_keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from all_keys(value)


class ShopCatalogBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.localdate()
        self.price_list = PriceList.objects.create(name="Bán lẻ", is_default=True)
        self.supplier = Supplier.objects.create(name="Đầu mối giả")
        self.warehouse = Warehouse.objects.create(name="Kho")
        self.group = ItemGroup.objects.create(name="Mực")

    def item(self, code, *, kg=None, price="278000", group=None, item_type=Item.ItemType.SIMPLE,
             name=None, active=True):
        it = Item.objects.create(
            code=code, name=name or code, item_group=group or self.group, item_type=item_type,
            is_active=active,
        )
        if price is not None:
            ItemPrice.objects.create(
                price_list=self.price_list, item=it, rate=Decimal(price),
                valid_from=self.today - datetime.timedelta(days=1),
            )
        if kg is not None:
            self.stock(it, kg)
        return it

    def stock(self, item, kg):
        batch = batch_services.create_batch(
            item=item, supplier=self.supplier, warehouse=self.warehouse,
            received_date=self.today, qty=Decimal(str(kg)), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=batch, actor=None)
        return batch

    def combo(self, code, parts, price="450000"):
        """parts: [(component_item, qty_per_bundle)]"""
        combo = self.item(code, price=price, item_type=Item.ItemType.BUNDLE, group=self.group)
        for component, qty in parts:
            BundleLine.objects.create(bundle=combo, component=component, qty_per_bundle=Decimal(str(qty)))
        return combo

    def catalog(self):
        resp = self.client.get("/api/shop/catalog/")
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def level(self, code):
        return next(i for i in self.catalog()["items"] if i["item_code"] == code)["stock_level"]


class StockLevelTests(ShopCatalogBase):
    def test_s2_01_ac1_simple_levels_in_low_out_out(self):
        self.item("IN5", kg="5")
        self.item("LOW25", kg="2.5")
        self.item("OUT09", kg="0.9")
        self.item("OUT0")  # chưa có lô nào
        self.assertEqual(
            [self.level(c) for c in ("IN5", "LOW25", "OUT09", "OUT0")], ["in", "low", "out", "out"]
        )

    def test_s2_01_ac1_boundaries_follow_v01(self):
        """V-01: dưới 3 kg là low (đúng 3 kg là in); dưới 1 kg là out (đúng 1 kg là low)."""
        self.item("B3", kg="3")
        self.item("B299", kg="2.999")
        self.item("B1", kg="1")
        self.item("B0999", kg="0.999")
        self.assertEqual(
            [self.level(c) for c in ("B3", "B299", "B1", "B0999")], ["in", "low", "low", "out"]
        )

    def test_s2_01_ac2_combo_levels_and_unit(self):
        rich = self.item("RICH", kg="100")
        poor = self.item("POOR", kg="1")          # 1 kg / 0,5 mỗi combo = 2 bộ
        empty = self.item("EMPTY")
        self.combo("C-IN", [(rich, "0.5")])                  # 200 bộ
        self.combo("C-5", [(rich, "20")])                    # đúng 5 bộ -> in
        self.combo("C-LOW", [(poor, "0.5")])                 # 2 bộ -> low
        self.combo("C-OUT", [(poor, "2")])                   # 0 bộ -> out
        self.combo("C-ONE-PART-OUT", [(rich, "1"), (empty, "1")])  # một thành phần hết -> out
        self.assertEqual(
            [self.level(c) for c in ("C-IN", "C-5", "C-LOW", "C-OUT", "C-ONE-PART-OUT")],
            ["in", "in", "low", "out", "out"],
        )
        row = next(i for i in self.catalog()["items"] if i["item_code"] == "C-LOW")
        self.assertEqual(
            (row["item_type"], row["unit"], row["min_qty"], row["qty_step"]),
            ("BUNDLE", "combo", "1", "1"),
        )

    def test_s2_01_ac2_combo_low_threshold_boundary(self):
        part = self.item("PART", kg="100")
        self.combo("C3", [(part, "33.4")])   # 2 bộ (100 // 33.4) -> low
        self.combo("C3B", [(part, "33")])    # 3 bộ -> in (đúng ngưỡng không phải low)
        self.assertEqual((self.level("C3"), self.level("C3B")), ("low", "in"))

    def test_s2_01_ac3_below_minimum_is_out_even_without_reservation(self):
        self.item("TAIL", kg="0.9")
        self.assertEqual(self.level("TAIL"), "out")

    def test_s2_01_ac3_reservation_lowers_level(self):
        item = self.item("RES", kg="5")
        batch = batch_services.sellable_batches(item=item).get()
        batch_services.reserve(batch=batch, qty=Decimal("4.5"))   # còn 0,5 kg bán được
        self.assertEqual(self.level("RES"), "out")

    def test_s2_01_ac4_thresholds_come_from_settings(self):
        self.item("S4", kg="4")
        self.assertEqual(self.level("S4"), "in")
        with override_settings(SHOP_LOW_STOCK_KG=Decimal("5")):
            self.assertEqual(self.level("S4"), "low")
        with override_settings(SHOP_MIN_QTY_KG=Decimal("5")):
            self.assertEqual(self.level("S4"), "out")

    def test_s2_01_ac4_combo_threshold_from_settings(self):
        part = self.item("P", kg="100")
        self.combo("C5", [(part, "20")])   # 5 bộ
        self.assertEqual(self.level("C5"), "in")
        with override_settings(SHOP_LOW_STOCK_COMBO=6):
            self.assertEqual(self.level("C5"), "low")

    def test_service_functions_direct(self):
        simple = self.item("SV", kg="2")
        combo = self.combo("SVC", [(simple, "1")])
        self.assertEqual(services.stock_level(simple), "low")
        self.assertEqual(services.sale_unit(simple), "kg")
        self.assertEqual(services.sale_unit(combo), "combo")
        self.assertEqual(services.qty_rule(simple), (Decimal("1"), Decimal("0.5")))
        self.assertEqual(services.qty_rule(combo), (Decimal("1"), Decimal("1")))

    def test_validate_line_qty_rules_ac2_of_story_2_02(self):
        simple = self.item("VQ")
        combo = self.item("VQC", item_type=Item.ItemType.BUNDLE)
        for ok in ("1", "1.5", "2", "10.5", "1.50"):
            self.assertTrue(services.validate_line_qty(simple, Decimal(ok)), ok)
        for bad in ("0.5", "0.3", "1.25", "0", "-1", "1.2", "NaN", "Infinity", "1e30", "-0", "1e999999999",
                    "1." + "0" * 60 + "1"):
            self.assertFalse(services.validate_line_qty(simple, Decimal(bad)), bad)
        for ok in ("1", "2", "7"):
            self.assertTrue(services.validate_line_qty(combo, Decimal(ok)), ok)
        for bad in ("1.5", "0", "-1", "0.5", "2.0001"):
            self.assertFalse(services.validate_line_qty(combo, Decimal(bad)), bad)

    def test_validate_line_qty_step_from_settings(self):
        simple = self.item("VQS")
        with override_settings(SHOP_QTY_STEP_KG=Decimal("1")):
            self.assertFalse(services.validate_line_qty(simple, Decimal("1.5")))
            self.assertTrue(services.validate_line_qty(simple, Decimal("2")))


class CatalogShapeTests(ShopCatalogBase):
    def test_contract_shape_groups_and_items(self):
        shrimp = ItemGroup.objects.create(name="Tôm")
        self.item("MUC-ONG", kg="2.7", name="Mực ống làm sạch")
        self.item("MUC-LA", kg="9", name="Mực lá")
        self.item("TOM-SU", kg="9", group=shrimp, name="Tôm sú")
        body = self.catalog()
        self.assertEqual(set(body), {"groups", "items"})
        self.assertEqual(
            body["groups"],
            [
                {"slug": "muc", "name": "Mực", "item_count": 2},
                {"slug": "tom", "name": "Tôm", "item_count": 1},
            ],
        )
        row = next(i for i in body["items"] if i["item_code"] == "MUC-ONG")
        self.assertEqual(
            set(row),
            {"item_code", "name", "item_type", "unit", "price", "stock_level", "min_qty", "qty_step",
             "group", "short_note", "image"},
        )
        self.assertEqual(row["price"], "278000")
        self.assertEqual(row["unit"], "kg")
        self.assertEqual((row["min_qty"], row["qty_step"]), ("1", "0.5"))
        self.assertEqual(row["group"], {"slug": "muc", "name": "Mực"})
        self.assertEqual(row["short_note"], "")
        self.assertIsNone(row["image"])
        self.assertEqual(row["stock_level"], "low")

    def test_items_sorted_by_group_name_then_code(self):
        other = ItemGroup.objects.create(name="Cá")
        self.item("B2")
        self.item("A1")
        self.item("Z9", group=other)
        self.assertEqual([i["item_code"] for i in self.catalog()["items"]], ["Z9", "A1", "B2"])

    def test_inactive_and_unpriced_items_hidden_and_not_counted(self):
        self.item("SHOWN", kg="5")
        self.item("HIDDEN-OFF", kg="5", active=False)
        self.item("HIDDEN-NOPRICE", kg="5", price=None)
        empty_group = ItemGroup.objects.create(name="Rỗng")
        self.item("ONLY-OFF", group=empty_group, active=False)
        body = self.catalog()
        self.assertEqual([i["item_code"] for i in body["items"]], ["SHOWN"])
        self.assertEqual(body["groups"], [{"slug": "muc", "name": "Mực", "item_count": 1}])

    def test_empty_catalog(self):
        self.assertEqual(self.catalog(), {"groups": [], "items": []})

    def test_detail_adds_text_fields_and_bundle_components(self):
        squid = self.item("MUC-ONG", kg="9", name="Mực ống làm sạch")
        self.combo("COMBO-LAU", [(squid, "0.5")])
        simple = self.client.get("/api/shop/catalog/MUC-ONG/")
        self.assertEqual(simple.status_code, 200)
        data = simple.json()
        for key in ("description", "spec", "storage", "origin"):
            self.assertEqual(data[key], "", key)
        self.assertNotIn("bundle_components", data)
        combo = self.client.get("/api/shop/catalog/COMBO-LAU/").json()
        self.assertEqual(
            combo["bundle_components"],
            [{"item_code": "MUC-ONG", "name": "Mực ống làm sạch", "qty_per_bundle": "0.5", "unit": "kg"}],
        )
        self.assertEqual((combo["unit"], combo["min_qty"], combo["qty_step"]), ("combo", "1", "1"))

    def test_detail_keeps_legacy_description_private_until_story_2b(self):
        """`Item.description` có sẵn trong DB nhưng lô 1 vẫn trả "" (lô 2b mới mở, có kiểm chữ BR-DM-25)."""
        it = self.item("DESC", kg="5")
        it.description = "Ghi chú nội bộ"
        it.save()
        self.assertEqual(self.client.get("/api/shop/catalog/DESC/").json()["description"], "")


class NotFoundTests(ShopCatalogBase):
    def test_s2_01_ac6_missing_inactive_unpriced_same_404_body(self):
        self.item("OFF", kg="5", active=False)
        self.item("NOPRICE", kg="5", price=None)
        bodies = []
        for code in ("NOPE", "OFF", "NOPRICE"):
            resp = self.client.get(f"/api/shop/catalog/{code}/")
            self.assertEqual(resp.status_code, 404, code)
            bodies.append(resp.json())
        self.assertEqual(bodies[0], {"code": "ITEM_NOT_FOUND", "detail": "Không tìm thấy món này."})
        self.assertEqual(bodies[0], bodies[1])
        self.assertEqual(bodies[1], bodies[2])

    def test_s2_01_ac8_write_methods_rejected_and_data_unchanged(self):
        item = self.item("RO", kg="5")
        before = Item.objects.count(), ItemGroup.objects.count()
        for url in ("/api/shop/catalog/", "/api/shop/catalog/RO/"):
            for method in ("post", "put", "patch", "delete"):
                resp = getattr(self.client, method)(url, {"name": "Hack"}, format="json")
                self.assertIn(resp.status_code, (403, 405), f"{method} {url}")
        item.refresh_from_db()
        self.assertEqual(item.name, "RO")
        self.assertEqual((Item.objects.count(), ItemGroup.objects.count()), before)


class NoLeakTests(ShopCatalogBase):
    """G1 (không số kg tồn) và G3 (không giá vốn, mã lô) — quét đệ quy mọi khoá và cả chuỗi JSON."""

    def setUp(self):
        super().setUp()
        self.low = self.item("MUC-ONG", kg="2.7", name="Mực ống")       # G1: 2,7 kg
        self.tail = self.item("MUC-DUOI", kg="0.6", name="Mực đuôi")     # G1: 0,6 kg
        part = self.item("MUC-LA", kg="11.25", name="Mực lá")
        self.combo("COMBO-LAU", [(part, "5.5")])                          # ráp được 2 bộ
        self.batch_codes = list(Batch.objects.values_list("batch_id", flat=True))

    def responses(self):
        return [
            self.client.get("/api/shop/catalog/"),
            self.client.get("/api/shop/catalog/MUC-ONG/"),
            self.client.get("/api/shop/catalog/COMBO-LAU/"),
        ]

    def test_g1_g3_no_forbidden_keys_at_any_depth(self):
        for resp in self.responses():
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(FORBIDDEN_KEYS & set(all_keys(resp.json())), set(), resp.request["PATH_INFO"])

    def test_g1_no_stock_quantity_number_in_raw_json(self):
        for resp in self.responses():
            raw = resp.content.decode()
            for stock_number in ("2.7", "0.6", "11.25", "11.250", "2.700", "0.600"):
                self.assertIsNone(re.search(rf"(?<![\d.]){re.escape(stock_number)}(?![\d])", raw), stock_number)

    def test_g3_no_batch_code_cost_or_supplier_in_raw_json(self):
        for resp in self.responses():
            raw = resp.content.decode()
            for code in self.batch_codes:
                self.assertNotIn(code, raw)
            self.assertNotIn("80000", raw)            # giá mua của fixture
            self.assertNotIn("Đầu mối giả", raw)
            self.assertNotIn(json.dumps("Đầu mối giả", ensure_ascii=True)[1:-1], raw)

    def test_stock_level_is_one_of_three_values(self):
        levels = {i["stock_level"] for i in self.catalog()["items"]}
        self.assertTrue(levels <= {"in", "low", "out"})
        self.assertEqual(levels, {"in", "low", "out"})   # 11,25 kg in; 2,7 kg và combo 2 bộ low; 0,6 kg out

    def test_public_item_row_never_calls_for_cost_permission(self):
        """Khách ẩn danh gọi được, không cần đăng nhập (AllowAny)."""
        self.assertEqual(self.client.get("/api/shop/catalog/").status_code, 200)
