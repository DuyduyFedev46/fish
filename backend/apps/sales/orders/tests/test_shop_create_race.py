"""
SHOP-2-02 AC4 (BR-BH-01, BR-BH-02): hai đơn tranh nhau phần tồn cuối -> đúng một đơn, đơn kia OUT_OF_STOCK;
tổng giữ chỗ không vượt tồn. Chỉ chạy trên PostgreSQL (SQLite không có khoá dòng). Dữ liệu giả.
"""
import datetime
import threading
import time
from decimal import Decimal
from unittest import skipUnless

from django.db import connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.tests.postgres_race import PostgresRaceFixtureMixin
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder
from apps.sales.orders import services
from apps.sales.orders.shop_errors import OutOfStockError

JOIN_TIMEOUT_SECONDS = 15
ROUNDS = 10


@skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL: select_for_update không có tác dụng trên SQLite.")
class ShopCreateRaceTests(PostgresRaceFixtureMixin, TransactionTestCase):
    def setUp(self):
        today = timezone.localdate()
        group = ItemGroup.objects.create(name="Race")
        self.item = Item.objects.create(code="RACE", name="Cá thử", item_group=group)
        price_list = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            price_list=price_list, item=self.item, rate=Decimal("100000"),
            valid_from=today - datetime.timedelta(days=1),
        )
        self.supplier = Supplier.objects.create(name="Đầu mối giả")
        self.warehouse = Warehouse.objects.create(name="Kho")

    def _batch(self, kg):
        batch = batch_services.create_batch(
            item=self.item, supplier=self.supplier, warehouse=self.warehouse,
            received_date=timezone.localdate(), qty=Decimal(kg), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=batch, actor=None)
        return batch

    def _order(self, kg, n):
        return services.create_order(
            customer_phone=f"09000{n:05d}", customer_name="Khách giả", delivery_address="1 Đường Thử",
            phone=f"09000{n:05d}", lines=[{"item_code": "RACE", "qty": Decimal(kg)}],
        )

    def test_s2_02_ac4_two_parallel_orders_for_last_stock_exactly_one_wins(self):
        for i in range(ROUNDS):
            with self.subTest(i=i):
                batch = self._batch("2")
                barrier = threading.Barrier(2)
                outcomes = []

                def place(n):
                    try:
                        barrier.wait(JOIN_TIMEOUT_SECONDS)
                        self._order("2", n)
                        outcomes.append("ok")
                    except OutOfStockError as exc:
                        outcomes.append(exc.code)
                    except Exception as exc:  # noqa: BLE001
                        outcomes.append(f"ERROR {type(exc).__name__}")
                    finally:
                        connection.close()

                threads = [threading.Thread(target=place, args=(i * 10 + k,)) for k in (1, 2)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(JOIN_TIMEOUT_SECONDS)
                    self.assertFalse(t.is_alive(), "treo quá thời hạn (nghi deadlock)")
                self.assertEqual(sorted(outcomes), ["OUT_OF_STOCK", "ok"])
                batch.refresh_from_db()
                self.assertEqual(batch.qty_reserved, Decimal("2"))
                # dọn để vòng sau có lô mới sạch
                Batch.objects.filter(pk=batch.pk).update(status=Batch.Status.CLOSED)

    def test_s2_02_waiter_after_lock_wait_gets_out_of_stock_not_500(self):
        """Người thứ hai qua kiểm tồn rồi CHỜ khoá lô; người trước commit giữ hết -> OUT_OF_STOCK, không 500."""
        for i in range(ROUNDS):
            with self.subTest(i=i):
                batch = self._batch("2")
                result = {}

                def waiter():
                    try:
                        self._order("2", 500 + i)
                        result["outcome"] = "ok"
                    except OutOfStockError as exc:
                        result["outcome"] = exc.code
                    except Exception as exc:  # noqa: BLE001
                        result["outcome"] = f"ERROR {type(exc).__name__}"
                    finally:
                        connection.close()

                thread = threading.Thread(target=waiter)
                with transaction.atomic():
                    locked = Batch.objects.select_for_update().get(pk=batch.pk)
                    thread.start()
                    time.sleep(0.5)  # luồng kia đã qua kiểm tồn và đang chờ khoá lô
                    locked.qty_reserved = Decimal("2")
                    locked.save(update_fields=["qty_reserved"])
                thread.join(JOIN_TIMEOUT_SECONDS)
                self.assertFalse(thread.is_alive(), "treo quá thời hạn (nghi deadlock)")
                self.assertEqual(result["outcome"], "OUT_OF_STOCK")
                self.assertFalse(SalesOrder.objects.filter(phone=f"09000{500 + i:05d}").exists())
                Batch.objects.filter(pk=batch.pk).update(status=Batch.Status.CLOSED)
