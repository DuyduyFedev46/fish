"""
QA P8 Lô 7 — L5-1: has_stock cho danh sách lô hết hạn (dùng thật ở FE), giá trị lạ, phân trang, khoá tên không lộ giá vốn
cho nv_kho (đếm số dòng > 0 để không đạt vì rỗng). Dữ liệu giả.
"""
import datetime
from decimal import Decimal

from django.utils import timezone

from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch
from apps.sales.orders.tests.test_s10_api import OrderApiBase, find_keys

URL = "/api/inventory/batches/"


class QaL51(OrderApiBase):
    def _mk(self, status, qty_available, days=1, rate="181818"):
        b = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=timezone.localdate() - datetime.timedelta(days=days),
            qty=Decimal("10"), purchase_rate=Decimal(rate),
        )
        Batch.objects.filter(pk=b.pk).update(status=status, qty_available=Decimal(qty_available))
        return b

    def test_qa_expired_con_ton_vs_expired_het_ton(self):
        e1 = self._mk(Batch.Status.EXPIRED, "3")
        e0 = self._mk(Batch.Status.EXPIRED, "0", days=2)
        res = client_for(self.kho).get(URL, {"status": "EXPIRED", "has_stock": "1"})
        ids = {r["id"] for r in res.json()["results"]}
        self.assertEqual(ids, {e1.pk})
        self.assertNotIn(e0.pk, ids)

    def test_qa_ton_le_rat_nho_van_tinh_la_con_ton_va_am_khong(self):
        small = self._mk(Batch.Status.EXPIRED, "0.001")
        neg = self._mk(Batch.Status.EXPIRED, "0", days=3)
        ids = {r["id"] for r in client_for(self.kho).get(URL, {"has_stock": "1", "status": "EXPIRED"}).json()["results"]}
        self.assertIn(small.pk, ids)
        self.assertNotIn(neg.pk, ids)

    def test_qa_gia_tri_la_cua_has_stock_khong_gay_500(self):
        self._mk(Batch.Status.EXPIRED, "0")
        for v in ("", "abc", "-1", "1; DROP TABLE", "TRUE", "true", "True", "2"):
            with self.subTest(v=v):
                res = client_for(self.kho).get(URL, {"has_stock": v})
                self.assertEqual(res.status_code, 200)

    def test_qa_phan_trang_va_dem_nhieu_dong_khong_lo_gia_von_voi_nv_kho(self):
        for i in range(30):
            self._mk(Batch.Status.EXPIRED if i % 2 else Batch.Status.SELLING, "5", days=i + 2, rate=str(190000 + i))
        c = client_for(self.kho)
        n = 0
        url = URL
        params = {"has_stock": "1", "page_size": 10}
        while url:
            res = c.get(url, params if url == URL else None)
            self.assertEqual(res.status_code, 200)
            body = res.json()
            n += len(body["results"])
            self.assertEqual(find_keys(body, COST_KEYS), set())
            for r in body["results"]:
                for bad in ("190", "purchase_rate", "landed", "unit_cost"):
                    self.assertNotIn(bad + "0", str(r)) if bad == "190" else self.assertNotIn(bad, r)
            nxt = body.get("next")
            url = nxt.split("testserver", 1)[-1] if nxt else None
        self.assertGreaterEqual(n, 30)

    def test_qa_khoa_ten_khong_chua_gia_tri_gia_von_o_ban_ghi_chi_tiet_cho_nv_kho(self):
        e = self._mk(Batch.Status.EXPIRED, "3", rate="181818")
        res = client_for(self.kho).get(f"{URL}{e.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(find_keys(res.json(), COST_KEYS), set())
        self.assertNotIn("181818", res.content.decode())
