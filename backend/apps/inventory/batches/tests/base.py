"""Dữ liệu nền dùng chung cho test service kho (batches/stock/stocktake/returns)."""
import datetime

from django.test import TestCase

from apps.catalog.models import Item, ItemGroup
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier


class InventoryServiceBase(TestCase):
    def setUp(self):
        self.g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=self.g)
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.today = datetime.date(2026, 9, 1)

    def _batch(self, qty="100", rate="80000", days=90):
        return batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=self.today, qty=qty, purchase_rate=rate, shelf_life_days=days,
        )
