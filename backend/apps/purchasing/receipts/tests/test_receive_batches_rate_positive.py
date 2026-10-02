"""
#22 (Lô bổ sung A, Duy 02/10): `receive-batches` từ chối dòng có `rate` = 0 (giá mua phải > 0), 400 theo field
`lines[i].rate`, không ghi gì. Giá mua nhỏ nhất hợp lệ là 0.01 đ/kg. Mọi dữ liệu là giả.
"""
from django.test import TestCase

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import PurchaseReceipt, Supplier

URL = "/api/purchasing/receipts/receive-batches/"


class ReceiveBatchesRatePositiveTests(TestCase):
    def setUp(self):
        group = ItemGroup.objects.create(name="Cá")
        Item.objects.create(code="TOM01", name="Tôm sú", item_group=group, shelf_life_in_days=90, stock_uom="KG")
        self.supplier = Supplier.objects.create(name="Đầu mối Phan Thiết")
        Warehouse.objects.create(name="Kho chính")
        self.warehouse_client = client_for(make_user("kho_rate", roles.WAREHOUSE_STAFF))

    def post(self, lines, key):
        return self.warehouse_client.post(
            URL, {"supplier": self.supplier.pk, "received_date": "2026-09-28", "idempotency_key": key, "lines": lines},
            format="json")

    def test_ac22_rate_zero_is_400_by_line_rate_and_writes_nothing(self):
        for i, rate in enumerate(("0", "0.00", 0, "0.001")):
            res = self.post([{"item_code": "TOM01", "qty": "1.000", "rate": rate}], f"z{i}")
            self.assertEqual(res.status_code, 400, (rate, res.content))
            self.assertIn("rate", res.json()["lines"][0], (rate, res.content))
        self.assertEqual(PurchaseReceipt.objects.count(), 0)
        self.assertEqual(Batch.objects.count(), 0)

    def test_ac22_rate_zero_on_second_line_points_at_second_line(self):
        res = self.post([{"item_code": "TOM01", "qty": "1.000", "rate": "80000"},
                         {"item_code": "TOM01", "qty": "1.000", "rate": "0"}], "z-second")
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn("rate", res.json()["lines"][1])
        self.assertEqual(PurchaseReceipt.objects.count(), 0)

    def test_ac22_smallest_valid_rate_is_201(self):
        res = self.post([{"item_code": "TOM01", "qty": "1.000", "rate": "0.01"}], "z-min")
        self.assertEqual(res.status_code, 201, res.content)

    def test_ac22_negative_rate_still_400(self):
        res = self.post([{"item_code": "TOM01", "qty": "1.000", "rate": "-1"}], "z-neg")
        self.assertEqual(res.status_code, 400, res.content)
