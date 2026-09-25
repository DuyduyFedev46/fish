"""Test job TTL (Celery task chạy đồng bộ) + command giám sát sức khoẻ job."""
import datetime
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tasks import cancel_expired_orders


class TtlJobTests(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            price_list=pl, item=self.item, rate=Decimal("100000"),
            valid_from=timezone.localdate() - datetime.timedelta(days=1),
        )
        b = batch_services.create_batch(
            item=self.item, supplier=Supplier.objects.create(name="A"),
            warehouse=Warehouse.objects.create(name="Kho"),
            received_date=timezone.localdate(), qty=Decimal("50"), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=b, actor=None)

    def _expired_order(self):
        order = order_services.create_order(
            customer_phone="0912345678", customer_name="A", delivery_address="x",
            phone="0912345678", lines=[{"item_code": "CA01", "qty": Decimal("3")}],
        )
        order.booked_expires_at = timezone.now() - datetime.timedelta(minutes=10)
        order.save(update_fields=["booked_expires_at"])
        return order

    def test_task_cancels_expired_and_releases(self):
        order = self._expired_order()
        n = cancel_expired_orders()  # shared_task chạy đồng bộ khi gọi trực tiếp
        self.assertEqual(n, 1)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.AUTO_CANCELLED)
        self.assertEqual(Batch.objects.get(item=self.item).qty_reserved, Decimal("0"))

    def test_health_check_flags_dead_job_then_ok(self):
        self._expired_order()  # đơn quá hạn còn treo -> job coi như chết
        with self.assertRaises(SystemExit):
            call_command("check_ttl_job_health", "--grace-minutes", "5")
        cancel_expired_orders()  # job chạy, dọn xong
        call_command("check_ttl_job_health", "--grace-minutes", "5")  # giờ khoẻ, không raise
