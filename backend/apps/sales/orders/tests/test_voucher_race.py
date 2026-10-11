"""
SHOP-3b-04 AC2 (BR-DM-20) — lượt mã không bao giờ vượt tổng khi nhiều khách đặt cùng lúc; thứ tự khoá đơn -> mã -> lô
(02b §2.2) không deadlock. Chỉ chạy trên PostgreSQL (SQLite không có khoá dòng); chạy trên DB test cloud riêng
(decisions 10/10). Dữ liệu giả.
"""
import datetime
import threading
import time
from decimal import Decimal
from unittest import skipUnless

from django.contrib.auth.models import User
from django.db import connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList, Voucher
from apps.common.tests.postgres_race import PostgresRaceFixtureMixin
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesOrder, VoucherRedemption
from apps.sales.orders import services
from apps.sales.orders.shop_errors import VoucherInvalidError

JOIN_TIMEOUT_SECONDS = 20
THREADS = 5


@skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL: select_for_update không có tác dụng trên SQLite.")
class VoucherRaceTests(PostgresRaceFixtureMixin, TransactionTestCase):
    def setUp(self):
        today = timezone.localdate()
        group = ItemGroup.objects.create(name="Race")
        self.item = Item.objects.create(code="RACE", name="Cá thử", item_group=group)
        price_list = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            price_list=price_list, item=self.item, rate=Decimal("100000"),
            valid_from=today - datetime.timedelta(days=1),
        )
        batch = batch_services.create_batch(
            item=self.item, supplier=Supplier.objects.create(name="Đầu mối giả"),
            warehouse=Warehouse.objects.create(name="Kho"), received_date=today, qty=Decimal("500"),
            purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=batch, actor=None)
        self.batch = batch
        self.maker = User.objects.create_user("voucher_maker", password="x")

    def voucher(self, code, total_uses):
        now = timezone.now()
        return Voucher.objects.create(
            code=code, name="Đua lượt", kind=Voucher.Kind.AMOUNT, value=Decimal("10000"), min_order_amount=Decimal("0"),
            starts_at=now - datetime.timedelta(days=1), ends_at=now + datetime.timedelta(days=1),
            total_uses=total_uses, created_by=self.maker,
        )

    def place(self, code, n, outcomes):
        try:
            order = services.create_order(
                customer_phone=f"09001{n:05d}", customer_name="Khách giả", delivery_address="1 Đường Thử",
                phone=f"09001{n:05d}", lines=[{"item_code": "RACE", "qty": Decimal("1")}], voucher_code=code,
            )
            outcomes.append(("ok", order.code))
        except VoucherInvalidError as exc:
            outcomes.append((exc.extra["reason_code"], None))
        except Exception as exc:  # noqa: BLE001
            outcomes.append((f"ERROR {type(exc).__name__}", None))
        finally:
            connection.close()

    def run_parallel(self, code, base):
        barrier = threading.Barrier(THREADS)
        outcomes = []

        def worker(n):
            try:
                barrier.wait(JOIN_TIMEOUT_SECONDS)
            except threading.BrokenBarrierError:
                pass
            self.place(code, n, outcomes)

        threads = [threading.Thread(target=worker, args=(base + k,)) for k in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(JOIN_TIMEOUT_SECONDS)
            self.assertFalse(t.is_alive(), "treo quá thời hạn (nghi deadlock)")
        return outcomes

    def test_s3b_04_ac2_five_parallel_orders_for_the_last_use_exactly_one_wins(self):
        for i in range(5):
            with self.subTest(round=i):
                code = f"RACE{i}"
                self.voucher(code, total_uses=1)
                outcomes = self.run_parallel(code, base=i * 10)
                self.assertEqual(sorted(o[0] for o in outcomes), ["USED_UP"] * 4 + ["ok"], outcomes)
                self.assertEqual(VoucherRedemption.objects.filter(code=code).count(), 1)
                self.assertEqual(SalesOrder.objects.filter(voucher_redemption__code=code).count(), 1)
        # 4 request thua KHÔNG tạo đơn, không giữ chỗ: mỗi vòng đúng 1 kg
        self.assertEqual(SalesOrder.objects.count(), 5)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_reserved, Decimal("5"))

    def test_uses_never_exceed_total_when_more_orders_than_uses(self):
        for i in range(3):
            with self.subTest(round=i):
                code = f"RACEN{i}"
                self.voucher(code, total_uses=3)
                outcomes = self.run_parallel(code, base=100 + i * 10)
                self.assertEqual(sorted(o[0] for o in outcomes), ["USED_UP"] * 2 + ["ok"] * 3, outcomes)
                self.assertEqual(VoucherRedemption.objects.filter(code=code).count(), 3)

    def test_waiter_on_the_voucher_lock_sees_the_use_committed_by_the_holder(self):
        """Người thứ hai qua kiểm nhanh (chưa thấy lượt), rồi CHỜ khoá mã; người giữ khoá commit lượt cuối -> USED_UP."""
        for i in range(5):
            with self.subTest(round=i):
                code = f"WAIT{i}"
                voucher = self.voucher(code, total_uses=1)
                customer = Customer.objects.create(phone=f"09002{i:05d}", name="Khách giả")
                result = {}

                def waiter():
                    outcomes = []
                    self.place(code, 200 + i, outcomes)
                    result["outcome"] = outcomes[0][0]

                thread = threading.Thread(target=waiter)
                with transaction.atomic():
                    Voucher.objects.select_for_update().get(pk=voucher.pk)
                    thread.start()
                    time.sleep(0.5)  # luồng kia đã qua kiểm nhanh và đang chờ khoá mã
                    holder = SalesOrder.objects.create(
                        code=f"SOWAIT{i}", customer=customer, delivery_address="1 Đường Thử", phone=customer.phone,
                        total_amount=Decimal("100000"),
                    )
                    VoucherRedemption.objects.create(
                        order=holder, voucher=voucher, code=code, discount_amount=Decimal("10000"),
                    )
                thread.join(JOIN_TIMEOUT_SECONDS)
                self.assertFalse(thread.is_alive(), "treo quá thời hạn (nghi deadlock)")
                self.assertEqual(result["outcome"], "USED_UP")
                self.assertFalse(SalesOrder.objects.filter(phone=f"09001{200 + i:05d}").exists())

    def test_expiry_job_and_new_orders_do_not_deadlock(self):
        """Job hết giờ (khoá đơn -> lô -> lượt) chạy song song với đặt đơn có mã (đơn -> mã -> lô): không treo."""
        self.voucher("MIXED001", total_uses=50)
        for n in range(6):
            order = services.create_order(
                customer_phone=f"09003{n:05d}", customer_name="Khách giả", delivery_address="1 Đường Thử",
                phone=f"09003{n:05d}", lines=[{"item_code": "RACE", "qty": Decimal("1")}], voucher_code="MIXED001",
            )
            SalesOrder.objects.filter(pk=order.pk).update(booked_expires_at=timezone.now() - datetime.timedelta(minutes=1))
        outcomes = []

        def job():
            try:
                outcomes.append(("job", services.cancel_unpaid_expired()))
            finally:
                connection.close()

        threads = [threading.Thread(target=job)] + [
            threading.Thread(target=self.place, args=("MIXED001", 300 + k, outcomes)) for k in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(JOIN_TIMEOUT_SECONDS)
            self.assertFalse(t.is_alive(), "treo quá thời hạn (nghi deadlock)")
        self.assertEqual([o for o in outcomes if str(o[0]).startswith("ERROR")], [])
        released = VoucherRedemption.objects.filter(state=VoucherRedemption.State.RELEASED).count()
        self.assertEqual(released, 6)
        self.assertEqual(VoucherRedemption.objects.filter(state=VoucherRedemption.State.HELD).count(), 4)
