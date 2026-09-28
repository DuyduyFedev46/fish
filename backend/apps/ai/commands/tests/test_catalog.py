"""
S01 — GET /api/commands/catalog (authenticated): trả theo quyền, không rò lệnh.

Nguồn: 02b-tech-design mục 3 (contract S01) + C.4 #11 (catalog = 0 query nghiệp vụ —
registry là code, quyết định 2); 02-stories S01-AC1…AC6; lệch D6 (field `description`).
"""
import jsonschema
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.common.tests.fixtures import client_for, make_user

CATALOG_URL = "/api/commands/catalog/"

ACTIVE = {
    "nhap_lo", "tra_ton", "tra_lo", "tra_hang", "tra_don",
    "bao_cao_ton_kho", "bao_cao_lo", "bao_cao_ky",
    "chot_lo", "tao_phieu_hoan", "xac_nhan_hoan", "xac_nhan_thanh_toan_tay",
}

ITEM_KEYS = {
    "name", "channel", "sensitivity", "min_permissions", "input_schema",
    "output_schema", "status", "description", "needs_confirmation", "forbidden_channel",
}

# Bảng nghiệp vụ mà catalog KHÔNG được query (C.4 #11).
BUSINESS_TABLE_SNIPPETS = (
    "catalog_", "inventory_", "sales_", "purchasing_", "delivery_", "reports_", "accounts_",
)


class CatalogApiTests(TestCase):
    def setUp(self):
        self.chu = make_user("chu1", "chu")
        self.ql = make_user("ql1", "quan_ly")
        self.kho = make_user("kho1", "nv_kho")
        self.giao = make_user("giao1", "nv_giao")

    def _catalog(self, user):
        resp = client_for(user).get(CATALOG_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()["commands"]

    def test_s01_ac1_chu_thay_du_12_lenh_active_du_truong(self):
        commands = self._catalog(self.chu)
        self.assertEqual({c["name"] for c in commands}, ACTIVE)
        for c in commands:
            self.assertTrue(ITEM_KEYS <= set(c), f"{c['name']} thiếu field")
            self.assertEqual(c["status"], "active")
            self.assertIn(c["channel"], ("local", "cloud"))
            self.assertIn(c["sensitivity"], ("cao", "trung_binh", "thap"))
            self.assertTrue(c["min_permissions"], c["name"])
            self.assertIsInstance(c["needs_confirmation"], bool)
            self.assertIn(c["forbidden_channel"], ("ai", None))
            jsonschema.Draft7Validator.check_schema(c["input_schema"])
            jsonschema.Draft7Validator.check_schema(c["output_schema"])
            self.assertTrue(c["description"].strip(), c["name"])  # D6

    def test_s01_ac2_nv_giao_chi_thay_lenh_co_quyen(self):
        names = {c["name"] for c in self._catalog(self.giao)}
        # cap_nhat_giao còn draft → không trả; tra_don thì có quyền view_salesorder.
        self.assertEqual(names, {"tra_don"})
        self.assertNotIn("nhap_lo", names)
        self.assertNotIn("bao_cao_lo", names)

    def test_s01_ac3_quan_ly_khong_thay_bao_cao_lo_ky_chu_thi_thay(self):
        names = {c["name"] for c in self._catalog(self.ql)}
        self.assertNotIn("bao_cao_lo", names)  # bất biến 1: không rò lệnh giá vốn/lãi lỗ
        self.assertNotIn("bao_cao_ky", names)
        chu_names = {c["name"] for c in self._catalog(self.chu)}
        self.assertIn("bao_cao_lo", chu_names)
        self.assertIn("bao_cao_ky", chu_names)

    def test_s01_ac4_catalog_co_forbidden_channel_dung_3_lenh(self):
        by_name = {c["name"]: c for c in self._catalog(self.chu)}
        for name in ("chot_lo", "xac_nhan_hoan", "xac_nhan_thanh_toan_tay"):
            self.assertEqual(by_name[name]["forbidden_channel"], "ai", name)
        for name, c in by_name.items():
            if name not in ("chot_lo", "xac_nhan_hoan", "xac_nhan_thanh_toan_tay"):
                self.assertIsNone(c["forbidden_channel"], name)

    def test_s01_ac5_chua_dang_nhap_401_khong_lo_ten_lenh(self):
        resp = client_for(None).get(CATALOG_URL)
        self.assertEqual(resp.status_code, 401)
        body = resp.content.decode()
        for name in ACTIVE:
            self.assertNotIn(name, body)

    def test_s01_nv_kho_chi_thay_lenh_co_quyen(self):
        names = {c["name"] for c in self._catalog(self.kho)}
        self.assertEqual(
            names,
            {"nhap_lo", "tra_ton", "tra_lo", "tra_hang", "tra_don", "bao_cao_ton_kho"},
        )

    def test_s01_catalog_0_query_nghiep_vu_registry_la_code(self):
        # C.4 #11: catalog không query bảng nghiệp vụ nào — danh mục nằm trong code.
        with CaptureQueriesContext(connection) as ctx:
            resp = client_for(self.chu).get(CATALOG_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        for q in ctx.captured_queries:
            sql = q["sql"]
            for snippet in BUSINESS_TABLE_SNIPPETS:
                self.assertNotIn(snippet, sql, f"catalog query bảng nghiệp vụ: {sql}")
