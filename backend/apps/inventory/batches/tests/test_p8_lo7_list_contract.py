"""
P8 Lô 7 — nợ Lô 5 L5-1 (phần BE): GET /api/inventory/batches/ có bộ lọc `has_stock=1`
(qty_available > 0) và các khoá hiển thị `item_name`, `supplier_name`, `warehouse_name`, `status_label`.
Không thêm trường tiền/giá vốn. Dữ liệu giả.

- L5-1-AC1: has_stock=1 chỉ trả lô còn tồn; không truyền thì trả cả lô tồn 0.
- L5-1-AC2: mỗi dòng có item_name/supplier_name/warehouse_name/status_label đúng giá trị.
- L5-1-AC3: nv_kho (không có view_costprice) không thấy khoá giá vốn, kể cả số giá mua 180000.
- L5-1-AC4: ma trận Group: chu, quan_ly, nv_kho 200; nv_giao, cskh 403; khách 401.
"""
from decimal import Decimal

from django.test import TestCase

from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch
from apps.sales.orders.tests.test_s10_api import OrderApiBase, find_keys
from apps.accounts import roles

URL = "/api/inventory/batches/"
NEW_KEYS = {"item_name", "supplier_name", "warehouse_name", "status_label"}


class ListContractTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.cs = make_user("cs_l51", roles.CUSTOMER_SERVICE)

    def _empty_batch(self):
        """Thêm lô thứ hai đã hết tồn (qty_available = 0)."""
        from apps.inventory.batches import services as batch_services
        import datetime
        from django.utils import timezone
        other = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=timezone.localdate() - datetime.timedelta(days=1),
            qty=Decimal("10"), purchase_rate=Decimal("180000"),
        )
        Batch.objects.filter(pk=other.pk).update(qty_available=Decimal("0"))
        return other

    def _ids(self, resp):
        return {r["id"] for r in resp.json()["results"]}

    def test_l51_ac1_has_stock_chi_tra_lo_con_ton(self):
        empty = self._empty_batch()
        c = client_for(self.kho)
        all_ids = self._ids(c.get(URL))
        self.assertEqual(all_ids, {self.batch.pk, empty.pk})
        res = c.get(URL, {"has_stock": "1"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self._ids(res), {self.batch.pk})

    def test_l51_ac1_has_stock_ket_hop_status(self):
        empty = self._empty_batch()
        Batch.objects.filter(pk=empty.pk).update(status=Batch.Status.SOLD_OUT)
        res = client_for(self.kho).get(URL, {"has_stock": "1", "status": Batch.Status.SELLING})
        self.assertEqual(self._ids(res), {self.batch.pk})

    def test_l51_ac1_has_stock_0_hoac_khac_1_khong_loc(self):
        empty = self._empty_batch()
        res = client_for(self.kho).get(URL, {"has_stock": "0"})
        self.assertEqual(self._ids(res), {self.batch.pk, empty.pk})

    def test_l51_ac2_khoa_hien_thi_dung_gia_tri(self):
        row = client_for(self.kho).get(URL).json()["results"][0]
        self.assertEqual(row["item_name"], "Tôm sú loại 1")
        self.assertEqual(row["supplier_name"], "Đầu mối A")
        self.assertEqual(row["warehouse_name"], "Kho chính")
        self.assertEqual(row["status_label"], self.batch.get_status_display())
        self.assertTrue(NEW_KEYS <= set(row))
        # khoá cũ giữ nguyên (FE cũ không vỡ)
        for k in ("id", "batch_id", "item", "item_code", "qty_available", "qty_sellable", "status"):
            self.assertIn(k, row)

    def test_l51_ac2_chi_tiet_lo_cung_co_khoa_hien_thi(self):
        res = client_for(self.kho).get(f"{URL}{self.batch.pk}/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(NEW_KEYS <= set(res.json()))

    def test_l51_ac3_nv_kho_khong_thay_gia_von_o_danh_sach(self):
        res = client_for(self.kho).get(URL, {"has_stock": "1"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(find_keys(res.json(), COST_KEYS), set(), res.content)
        self.assertNotIn(b"180000", res.content)

    def test_l51_ac3_khoa_moi_khong_phai_khoa_tien(self):
        self.assertFalse(NEW_KEYS & set(COST_KEYS))

    def test_l51_ac3_chu_van_thay_gia_von_doi_chung(self):
        row = client_for(self.chu).get(URL).json()["results"][0]
        self.assertIn("purchase_rate", row)

    def test_l51_ac4_ma_tran_group(self):
        for user, expected in ((self.chu, 200), (self.ql, 200), (self.kho, 200), (self.giao, 403), (self.cs, 403)):
            with self.subTest(user=user.username):
                res = client_for(user).get(URL, {"has_stock": "1"})
                self.assertEqual(res.status_code, expected, res.content)

    def test_l51_ac4_khach_401(self):
        self.assertEqual(client_for(None).get(URL, {"has_stock": "1"}).status_code, 401)
