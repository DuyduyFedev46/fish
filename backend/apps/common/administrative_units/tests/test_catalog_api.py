"""
STA-01 (T-A1…T-A8): danh mục đơn vị hành chính và API công khai. Dữ liệu danh mục là công cộng, không phải dữ liệu khách.
"""
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.common.administrative_units import catalog
from apps.common.administrative_units.addresses import STREET_MAX, parse_address_parts

URL = "/api/shop/administrative-units/"


class CatalogIntegrityTests(SimpleTestCase):
    def test_a1_counts_and_parent_integrity(self):
        self.assertEqual(len(catalog.provinces("current")), 34)
        self.assertEqual(len(catalog._index("current")["wards"]), 3321)
        self.assertEqual(len(catalog.provinces("legacy")), 63)
        self.assertEqual(len(catalog._index("legacy")["districts"]), 696)
        self.assertEqual(len(catalog._index("legacy")["wards"]), 10051)
        cur, leg = catalog._index("current"), catalog._index("legacy")
        self.assertTrue(all(w.parent_code in cur["provinces"] for w in cur["wards"].values()))
        self.assertTrue(all(d.parent_code in leg["provinces"] for d in leg["districts"].values()))
        self.assertTrue(all(w.parent_code in leg["districts"] for w in leg["wards"].values()))

    def test_a1_no_duplicate_codes_per_level(self):
        import json
        for scheme in catalog.SCHEMES:
            with open(catalog._DATA_DIR / f"{scheme}.json", encoding="utf-8") as handle:
                raw = json.load(handle)
            for level in ("provinces", "districts", "wards"):
                codes = [u["code"] for u in raw.get(level, [])]
                self.assertEqual(len(codes), len(set(codes)), f"{scheme}.{level}")

    def test_a2_same_ward_code_has_different_names_per_scheme(self):
        self.assertEqual(catalog.get_ward("current", "22918").name, "Phường Mũi Né")
        self.assertEqual(catalog.get_ward("legacy", "22918").name, "Phường Hàm Tiến")

    def test_lookup_rejects_non_string_and_unknown(self):
        self.assertIsNone(catalog.get_ward("current", 22918))
        self.assertIsNone(catalog.get_province("legacy", "99"))
        with self.assertRaises(ValueError):
            catalog.provinces("new")


class AdministrativeUnitApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()  # khách chưa đăng nhập

    def get(self, **params):
        return self.client.get(URL, params)

    def test_a3_public_lists(self):
        self.assertEqual(len(self.get(scheme="current", level="province").json()["items"]), 34)
        self.assertEqual(len(self.get(scheme="legacy", level="province").json()["items"]), 63)
        codes = lambda r: {i["code"] for i in r.json()["items"]}  # noqa: E731
        self.assertIn("593", codes(self.get(scheme="legacy", level="district", parent="60")))
        self.assertIn("22945", codes(self.get(scheme="current", level="ward", parent="68")))
        resp = self.get(scheme="legacy", level="ward", parent="593")
        self.assertIn("22915", codes(resp))
        self.assertEqual(resp.json()["parent_code"], "593")
        self.assertIn("public, max-age=", resp["Cache-Control"])
        self.assertIsNone(self.get(scheme="current", level="province").json()["parent_code"])

    def test_a4_errors(self):
        cases = [
            (dict(scheme="new", level="province"), "scheme"),
            (dict(level="province"), "scheme"),
            (dict(scheme="current", level="city"), "level"),
            (dict(scheme="current"), "level"),
            (dict(scheme="current", level="district", parent="68"), "level"),
            (dict(scheme="legacy", level="district"), "parent"),
            (dict(scheme="current", level="ward"), "parent"),
            (dict(scheme="current", level="ward", parent="99"), "parent"),
            (dict(scheme="legacy", level="ward", parent="60"), "parent"),
            (dict(scheme="current", level="ward", parent="593"), "parent"),
        ]
        for params, field in cases:
            resp = self.get(**params)
            self.assertEqual(resp.status_code, 400, params)
            body = resp.json()
            self.assertEqual(body["code"], "VALIDATION", params)
            self.assertEqual(list(body["fields"]), [field], params)
            self.assertNotIn("max-age", resp.get("Cache-Control", ""), params)

    @override_settings(PRIVACY_CONSENT_REQUIRED=True)
    def test_a5_works_when_shop_closed(self):
        self.assertEqual(self.get(scheme="current", level="province").status_code, 200)

    def test_a7_write_methods_405(self):
        for method in ("post", "put", "delete"):
            resp = getattr(self.client, method)(URL + "?scheme=current&level=province", {}, format="json")
            self.assertEqual(resp.status_code, 405, method)

    def test_a8_items_only_code_and_name(self):
        for params in (dict(scheme="current", level="province"), dict(scheme="legacy", level="ward", parent="593")):
            for item in self.get(**params).json()["items"]:
                self.assertEqual(set(item), {"code", "name"})


class ParseAddressPartsTests(SimpleTestCase):
    def parts(self, **over):
        base = {"scheme": "legacy", "province_code": "60", "district_code": "593", "ward_code": "22915", "street": "12 Đường Giả"}
        base.update(over)
        return parse_address_parts(base)

    def test_legacy_ok_composes_full_text(self):
        addr, errors = self.parts()
        self.assertEqual(errors, {})
        self.assertTrue(addr.full_text.startswith("12 Đường Giả, "))
        self.assertEqual(addr.full_text.count(", "), 3)

    def test_current_ok(self):
        addr, errors = parse_address_parts(
            {"scheme": "current", "province_code": "68", "district_code": None, "ward_code": "22945", "street": "12 Đường Giả"}
        )
        self.assertEqual(errors, {})
        self.assertEqual(addr.full_text, "12 Đường Giả, Phường Phan Thiết, Tỉnh Lâm Đồng")
        self.assertEqual(addr.district_code, "")

    def test_errors_cascade_and_scheme_only(self):
        self.assertEqual(self.parts(scheme="new")[1], {"scheme": "Chọn kiểu địa chỉ."})
        self.assertEqual(set(self.parts(province_code="99")[1]), {"province_code", "district_code", "ward_code"})
        self.assertEqual(parse_address_parts("x")[1], {"delivery_address": "Chọn địa chỉ giao hàng."})
        self.assertEqual(set(self.parts(province_code=60)[1]), {"province_code", "district_code", "ward_code"})

    def test_street_rules(self):
        self.assertIn("street", self.parts(street="  \n ")[1])
        self.assertIn("street", self.parts(street="a" * (STREET_MAX + 1))[1])
        self.assertIn("street", self.parts(street=5)[1])
        self.assertEqual(self.parts(street="a" * STREET_MAX)[1], {})
        self.assertEqual(self.parts(street="12\nĐường  Giả")[0].street, "12 Đường Giả")
