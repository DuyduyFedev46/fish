import datetime
from decimal import Decimal

from django.utils import timezone

from apps.catalog.models import BundleLine, Item, PricingRule
from apps.common.exceptions import BusinessError
from apps.inventory.models import Batch
from apps.sales.models import SalesOrder, SalesOrderLineBatch
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.base import SalesServiceBase
from apps.sales.payments import services as payment_services


class CreateOrderTests(SalesServiceBase):
    def test_simple_order_prices_reserves_and_groups_customer(self):
        ca = self._item("CA01", price="100000")
        self._stocked_batch(ca, "100")
        order = order_services.create_order(
            customer_phone="0900000001", customer_name="Anh A",
            delivery_address="1 Cảng", phone="0900000001",
            lines=[{"item_code": "CA01", "qty": Decimal("3")}],
        )
        self.assertEqual(order.status, SalesOrder.Status.BOOKED)
        self.assertEqual(order.total_amount, Decimal("300000.00"))
        self.assertIsNotNone(order.booked_expires_at)
        # tồn khả dụng giảm đúng phần giữ chỗ
        b = Batch.objects.get(item=ca)
        self.assertEqual(b.qty_reserved, Decimal("3"))
        self.assertEqual(b.qty_available, Decimal("100"))  # chưa trừ tồn thật
        # đặt lần 2 cùng SĐT -> gộp cùng customer
        order_services.create_order(
            customer_phone="0900000001", customer_name="Anh A",
            delivery_address="1 Cảng", phone="0900000001",
            lines=[{"item_code": "CA01", "qty": Decimal("1")}],
        )
        self.assertEqual(order.customer.orders.count(), 2)

    def test_order_spans_multiple_batches_fifo(self):
        ca = self._item("CA02", price="100000")
        self._stocked_batch(ca, "5", received=self.yday)  # lô cũ ra trước
        self._stocked_batch(ca, "5", received=self.today)
        order = order_services.create_order(
            customer_phone="0900000002", customer_name="B",
            delivery_address="x", phone="0900000002",
            lines=[{"item_code": "CA02", "qty": Decimal("7")}],
        )
        allocs = SalesOrderLineBatch.objects.filter(order_line__order=order).order_by("id")
        self.assertEqual(allocs.count(), 2)
        self.assertEqual(allocs[0].qty, Decimal("5"))  # vét lô cũ trước
        self.assertEqual(allocs[1].qty, Decimal("2"))

    def test_insufficient_stock_rolls_back_whole_order(self):
        ca = self._item("CA03", price="100000")
        self._stocked_batch(ca, "2")
        with self.assertRaises(BusinessError):
            order_services.create_order(
                customer_phone="0900000003", customer_name="C",
                delivery_address="x", phone="0900000003",
                lines=[{"item_code": "CA03", "qty": Decimal("5")}],
            )
        self.assertEqual(SalesOrder.objects.count(), 0)  # rollback sạch
        Batch.objects.get(item=ca).refresh_from_db()
        self.assertEqual(Batch.objects.get(item=ca).qty_reserved, Decimal("0"))

    def test_two_customers_race_last_batch(self):
        ca = self._item("CA04", price="100000")
        self._stocked_batch(ca, "4")
        order_services.create_order(
            customer_phone="0900000010", customer_name="X", delivery_address="x",
            phone="0900000010", lines=[{"item_code": "CA04", "qty": Decimal("4")}],
        )
        with self.assertRaises(BusinessError):  # người sau thấy hết hàng (BR-BH-02)
            order_services.create_order(
                customer_phone="0900000011", customer_name="Y", delivery_address="x",
                phone="0900000011", lines=[{"item_code": "CA04", "qty": Decimal("1")}],
            )

    def test_bundle_explodes_and_reserves_all_components(self):
        tom = self._item("TOM", price=None)
        muc = self._item("MUC", price=None)
        self._stocked_batch(tom, "10")
        self._stocked_batch(muc, "10")
        combo = self._item("SET01", price="500000", item_type=Item.ItemType.BUNDLE)
        BundleLine.objects.create(bundle=combo, component=tom, qty_per_bundle=Decimal("1"))
        BundleLine.objects.create(bundle=combo, component=muc, qty_per_bundle=Decimal("0.5"))
        order = order_services.create_order(
            customer_phone="0900000020", customer_name="Z", delivery_address="x",
            phone="0900000020", lines=[{"item_code": "SET01", "qty": Decimal("2")}],
        )
        self.assertEqual(order.total_amount, Decimal("1000000.00"))  # 2 × giá combo độc lập
        Batch.objects.get(item=tom).refresh_from_db()
        self.assertEqual(Batch.objects.get(item=tom).qty_reserved, Decimal("2"))    # 1kg×2
        self.assertEqual(Batch.objects.get(item=muc).qty_reserved, Decimal("1.0"))  # 0.5×2

    def test_bundle_missing_one_component_fails_whole_order(self):
        tom = self._item("TOM2", price=None)
        muc = self._item("MUC2", price=None)
        self._stocked_batch(tom, "10")
        self._stocked_batch(muc, "0.4")  # thiếu mực
        combo = self._item("SET02", price="500000", item_type=Item.ItemType.BUNDLE)
        BundleLine.objects.create(bundle=combo, component=tom, qty_per_bundle=Decimal("1"))
        BundleLine.objects.create(bundle=combo, component=muc, qty_per_bundle=Decimal("0.5"))
        with self.assertRaises(BusinessError):
            order_services.create_order(
                customer_phone="0900000021", customer_name="Z", delivery_address="x",
                phone="0900000021", lines=[{"item_code": "SET02", "qty": Decimal("1")}],
            )
        self.assertEqual(SalesOrder.objects.count(), 0)
        self.assertEqual(Batch.objects.get(item=tom).qty_reserved, Decimal("0"))  # nhả sạch


class PricingRuleTests(SalesServiceBase):
    def test_best_item_rule_applied_not_stacked(self):
        ca = self._item("CA05", price="100000")
        self._stocked_batch(ca, "100")
        # hai rule cùng khớp mua >=3kg: giảm 5% vs giảm 10% -> chọn 10% (lợi nhất)
        PricingRule.objects.create(
            name="giảm 5%", is_active=True, apply_on=PricingRule.ApplyOn.ITEM,
            item=ca, min_qty=Decimal("3"), discount_type=PricingRule.DiscountType.PERCENT,
            discount_value=Decimal("5"),
        )
        PricingRule.objects.create(
            name="giảm 10%", is_active=True, apply_on=PricingRule.ApplyOn.ITEM,
            item=ca, min_qty=Decimal("3"), discount_type=PricingRule.DiscountType.PERCENT,
            discount_value=Decimal("10"),
        )
        order = order_services.create_order(
            customer_phone="0900000030", customer_name="A", delivery_address="x",
            phone="0900000030", lines=[{"item_code": "CA05", "qty": Decimal("3")}],
        )
        # gross 300k, giảm 10% = 30k -> 270k (không cộng dồn 15%)
        self.assertEqual(order.total_amount, Decimal("270000.00"))


class TTLAndCancelTests(SalesServiceBase):
    def test_cancel_unpaid_expired_releases_and_idempotent(self):
        ca = self._item("EXP1", price="100000")
        self._stocked_batch(ca, "10")
        order = order_services.create_order(
            customer_phone="0900000050", customer_name="A", delivery_address="x",
            phone="0900000050", lines=[{"item_code": "EXP1", "qty": Decimal("4")}],
        )
        order.booked_expires_at = timezone.now() - datetime.timedelta(minutes=1)
        order.save(update_fields=["booked_expires_at"])
        n = order_services.cancel_unpaid_expired()
        self.assertEqual(n, 1)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.AUTO_CANCELLED)
        self.assertEqual(Batch.objects.get(item=ca).qty_reserved, Decimal("0"))  # nhả giữ chỗ
        self.assertEqual(order_services.cancel_unpaid_expired(), 0)  # idempotent

    def test_cancel_paid_order_restores_stock(self):
        ca = self._item("CP1", price="100000")
        self._stocked_batch(ca, "10")
        order = order_services.create_order(
            customer_phone="0900000070", customer_name="A", delivery_address="x",
            phone="0900000070", lines=[{"item_code": "CP1", "qty": Decimal("3")}],
        )
        payment_services.confirm_payment(order=order, bank_txn_id="CPTX", amount=order.total_amount,
                                 received_at=timezone.now())
        self.assertEqual(Batch.objects.get(item=ca).qty_available, Decimal("7"))
        order_services.cancel_paid_order(order=order, actor=None, reason="test")
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(Batch.objects.get(item=ca).qty_available, Decimal("10"))  # hoàn kho lô gốc
