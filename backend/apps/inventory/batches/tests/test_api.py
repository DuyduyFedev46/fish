"""
Test chống rò rỉ giá vốn qua API (BR-PQ-13 / spec 1.6) — rủi ro triển khai số 1.
Gọi API bằng đúng token của Group để xác nhận field nhạy cảm không lộ.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier


class CostLeakAPITests(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Cá")
        item = Item.objects.create(code="CA01", name="Cá thu", item_group=g)
        sup = Supplier.objects.create(name="A")
        wh = Warehouse.objects.create(name="Kho")
        batch_services.create_batch(
            item=item, supplier=sup, warehouse=wh,
            received_date=datetime.date(2026, 9, 1), qty=Decimal("50"), purchase_rate=Decimal("80000"),
        )
        self.chu = User.objects.create_user("chu", password="x")
        self.chu.groups.add(Group.objects.get(name="chu"))
        self.kho = User.objects.create_user("kho", password="x")
        self.kho.groups.add(Group.objects.get(name="nv_kho"))

    def _first_batch(self, user):
        client = APIClient()
        client.force_authenticate(user)
        resp = client.get("/api/inventory/batches/")
        self.assertEqual(resp.status_code, 200, resp.content)
        results = resp.json()["results"]
        self.assertTrue(results)
        return results[0]

    def test_chu_sees_cost_fields(self):
        row = self._first_batch(self.chu)
        self.assertIn("landed_unit_cost", row)
        self.assertIn("purchase_rate", row)

    def test_nv_kho_cannot_see_cost_fields(self):
        row = self._first_batch(self.kho)
        self.assertNotIn("landed_unit_cost", row)  # RÒ RỈ nếu có
        self.assertNotIn("purchase_rate", row)
        self.assertIn("qty_available", row)  # vẫn thấy tồn (không nhạy cảm)

    def test_nv_kho_cannot_publish_batch(self):
        batch = Batch.objects.first()
        client = APIClient()
        client.force_authenticate(self.kho)  # nv_kho không có publish_batch
        resp = client.post(f"/api/inventory/batches/{batch.pk}/publish/")
        self.assertEqual(resp.status_code, 403)

    def test_chu_can_publish_batch(self):
        batch = Batch.objects.first()
        client = APIClient()
        client.force_authenticate(self.chu)
        resp = client.post(f"/api/inventory/batches/{batch.pk}/publish/")
        self.assertEqual(resp.status_code, 200, resp.content)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.SELLING)
