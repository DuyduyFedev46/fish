"""Dữ liệu nền dùng chung cho test service bán hàng (orders/payments/refunds)."""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier


class SalesServiceBase(TestCase):
    def setUp(self):
        self.g = ItemGroup.objects.create(name="Hải sản")
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        self.today = timezone.localdate()
        self.yday = self.today - datetime.timedelta(days=1)

    def _item(self, code, price=None, item_type=Item.ItemType.SIMPLE):
        it = Item.objects.create(code=code, name=code, item_group=self.g, item_type=item_type)
        if price is not None:
            ItemPrice.objects.create(
                price_list=self.pl, item=it, rate=Decimal(price),
                valid_from=self.yday, valid_upto=None,
            )
        return it

    def _stocked_batch(self, item, qty, rate="80000", received=None):
        b = batch_services.create_batch(
            item=item, supplier=self.sup, warehouse=self.wh,
            received_date=received or self.today, qty=Decimal(qty), purchase_rate=Decimal(rate),
        )
        batch_services.publish_batch(batch=b, actor=None)
        b.refresh_from_db()
        return b
