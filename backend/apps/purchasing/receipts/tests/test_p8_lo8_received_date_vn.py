"""
P8 Lô 8 — L8-2 (BR-MH-01): ngày nhập mặc định của phiếu nhập lô là ngày VN (GMT+7), không phải ngày UTC.
Cố định giờ 2026-09-30T17:30Z (= 00:30 ngày 01/10 giờ VN); ca 10:00Z (17:00 VN cùng ngày) không đổi.
"""
import datetime
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase

from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import PurchaseReceipt, Supplier
from apps.purchasing.receipts import services

AFTER_MIDNIGHT_VN = datetime.datetime(2026, 9, 30, 17, 30, tzinfo=dt_timezone.utc)  # 01/10 00:30 VN
SAME_DAY_VN = datetime.datetime(2026, 9, 30, 10, 0, tzinfo=dt_timezone.utc)  # 30/09 17:00 VN


class ReceivedDateVnTests(TestCase):
    def setUp(self):
        grp = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="TOM01", name="Tôm sú", item_group=grp, shelf_life_in_days=90, stock_uom="KG")
        self.sup = Supplier.objects.create(name="Đầu mối giả")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.kho = make_user("kho_lo8", "nv_kho")

    def _payload(self):
        return {
            "supplier": self.sup.pk,
            "warehouse": self.wh.pk,
            "lines": [{"item_code": "TOM01", "qty": "10.000", "rate": "80000.00", "shelf_life_days": 30}],
        }

    def test_l8_2_api_khong_truyen_ngay_sau_nua_dem_vn_lay_ngay_vn(self):
        with patch("django.utils.timezone.now", return_value=AFTER_MIDNIGHT_VN):
            res = client_for(self.kho).post("/api/purchasing/receipts/nhap-lo/", self._payload(), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        receipt = PurchaseReceipt.objects.get(pk=res.json()["receipt"]["id"])
        self.assertEqual(receipt.received_date, datetime.date(2026, 10, 1))
        batch = Batch.objects.get(batch_id=res.json()["batches"][0]["batch_id"])
        self.assertIn("-261001-", batch.batch_id)
        self.assertEqual(batch.received_date, datetime.date(2026, 10, 1))
        self.assertEqual(batch.expiry_date, datetime.date(2026, 10, 31))  # 01/10 + 30 ngày

    def test_l8_2_service_khong_truyen_ngay_sau_nua_dem_vn(self):
        with patch("django.utils.timezone.now", return_value=AFTER_MIDNIGHT_VN):
            receipt, batches = services.create_and_submit_receipt(
                supplier=self.sup, warehouse=self.wh, actor=self.kho,
                lines=[{"item_code": self.item, "qty": "10.000", "rate": "80000.00"}],
            )
        self.assertEqual(receipt.received_date, datetime.date(2026, 10, 1))
        self.assertIn("-261001-", batches[0].batch_id)
        self.assertEqual(batches[0].expiry_date, datetime.date(2026, 10, 1) + datetime.timedelta(days=90))

    def test_l8_2_ca_10h_utc_van_la_ngay_30_khong_doi(self):
        with patch("django.utils.timezone.now", return_value=SAME_DAY_VN):
            res = client_for(self.kho).post("/api/purchasing/receipts/nhap-lo/", self._payload(), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        receipt = PurchaseReceipt.objects.get(pk=res.json()["receipt"]["id"])
        self.assertEqual(receipt.received_date, datetime.date(2026, 9, 30))
        self.assertIn("-260930-", res.json()["batches"][0]["batch_id"])

    def test_l8_2_truyen_received_date_tuong_minh_van_duoc_giu(self):
        payload = dict(self._payload(), received_date="2026-09-28")
        with patch("django.utils.timezone.now", return_value=AFTER_MIDNIGHT_VN):
            res = client_for(self.kho).post("/api/purchasing/receipts/nhap-lo/", payload, format="json")
        self.assertEqual(PurchaseReceipt.objects.get(pk=res.json()["receipt"]["id"]).received_date, datetime.date(2026, 9, 28))
