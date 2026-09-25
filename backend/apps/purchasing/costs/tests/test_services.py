import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.catalog.models import Item, ItemGroup
from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.inventory.stock import services as stock_services
from apps.purchasing.costs import services as cost_services
from apps.purchasing.models import PurchaseCost, PurchaseCostAllocation, Supplier


class RecordPurchaseCostTests(TestCase):
    def setUp(self):
        self.g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=self.g)
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.user = User.objects.create(username="chu")
        self.today = datetime.date(2026, 9, 1)

    def _batch(self, qty, rate):
        return batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=self.today, qty=Decimal(qty), purchase_rate=Decimal(rate),
        )

    def test_by_qty_updates_landed_unit_cost(self):
        # 1 lô: 100kg @ 80000. Chi phí 1,000,000 phân bổ theo kg.
        b = self._batch("100", "80000")
        cost = cost_services.record_purchase_cost(
            cost_type=PurchaseCost.CostType.ICE,
            amount=Decimal("1000000"),
            allocation_method=PurchaseCost.AllocationMethod.BY_QTY,
            incurred_date=self.today,
            allocations=[b],
            actor=self.user,
        )
        b.refresh_from_db()
        # (80000*100 + 1000000) / 100 = 90000
        self.assertEqual(b.landed_unit_cost, Decimal("90000"))
        self.assertEqual(cost.allocations.count(), 1)
        self.assertEqual(cost.allocations.first().allocated_amount, Decimal("1000000"))

    def test_by_qty_splits_across_batches(self):
        b1 = self._batch("100", "80000")
        b2 = self._batch("100", "60000")
        cost_services.record_purchase_cost(
            cost_type=PurchaseCost.CostType.TRANSPORT,
            amount=Decimal("1000000"),
            allocation_method=PurchaseCost.AllocationMethod.BY_QTY,
            incurred_date=self.today,
            allocations=[{"batch_id": b1.batch_id}, {"batch_id": b2.batch_id}],
            actor=self.user,
        )
        b1.refresh_from_db()
        b2.refresh_from_db()
        # kg bằng nhau -> mỗi lô 500000
        self.assertEqual(b1.landed_unit_cost, Decimal("85000"))  # (8,000,000+500,000)/100
        self.assertEqual(b2.landed_unit_cost, Decimal("65000"))  # (6,000,000+500,000)/100

    def test_by_value_allocation(self):
        b1 = self._batch("100", "80000")   # giá trị 8,000,000
        b2 = self._batch("100", "60000")   # giá trị 6,000,000 ; tổng 14,000,000
        cost_services.record_purchase_cost(
            cost_type=PurchaseCost.CostType.OTHER,
            amount=Decimal("1400000"),
            allocation_method=PurchaseCost.AllocationMethod.BY_VALUE,
            incurred_date=self.today,
            allocations=[b1, b2],
            actor=self.user,
        )
        b1.refresh_from_db()
        b2.refresh_from_db()
        # b1: 1,400,000 * 8/14 = 800,000 ; b2: 600,000
        self.assertEqual(b1.landed_unit_cost, Decimal("88000"))  # (8,000,000+800,000)/100
        self.assertEqual(b2.landed_unit_cost, Decimal("66000"))  # (6,000,000+600,000)/100

    def test_explicit_amounts_per_batch(self):
        b1 = self._batch("100", "80000")
        b2 = self._batch("100", "60000")
        cost_services.record_purchase_cost(
            cost_type=PurchaseCost.CostType.LOADING,
            amount=Decimal("300000"),
            allocation_method=PurchaseCost.AllocationMethod.BY_QTY,
            incurred_date=self.today,
            allocations=[
                {"batch": b1, "amount": Decimal("200000")},
                {"batch": b2, "amount": Decimal("100000")},
            ],
            actor=self.user,
        )
        b1.refresh_from_db()
        b2.refresh_from_db()
        self.assertEqual(b1.landed_unit_cost, Decimal("82000"))  # (8,000,000+200,000)/100
        self.assertEqual(b2.landed_unit_cost, Decimal("61000"))  # (6,000,000+100,000)/100

    def test_explicit_amounts_must_sum_to_total(self):
        b1 = self._batch("100", "80000")
        b2 = self._batch("100", "60000")
        with self.assertRaises(BusinessError):
            cost_services.record_purchase_cost(
                cost_type=PurchaseCost.CostType.LOADING,
                amount=Decimal("300000"),
                allocation_method=PurchaseCost.AllocationMethod.BY_QTY,
                incurred_date=self.today,
                allocations=[
                    {"batch": b1, "amount": Decimal("200000")},
                    {"batch": b2, "amount": Decimal("50000")},  # tổng 250k != 300k
                ],
                actor=self.user,
            )

    def test_total_allocation_matches_amount_with_rounding(self):
        # 3 lô kg bằng nhau, amount không chia hết -> phần dư dồn vào lô cuối
        b1 = self._batch("100", "50000")
        b2 = self._batch("100", "50000")
        b3 = self._batch("100", "50000")
        cost = cost_services.record_purchase_cost(
            cost_type=PurchaseCost.CostType.ICE,
            amount=Decimal("100.00"),
            allocation_method=PurchaseCost.AllocationMethod.BY_QTY,
            incurred_date=self.today,
            allocations=[b1, b2, b3],
            actor=self.user,
        )
        total = sum(
            a.allocated_amount for a in cost.allocations.all()
        )
        self.assertEqual(total, Decimal("100.00"))
        amounts = sorted(a.allocated_amount for a in cost.allocations.all())
        # 33.33 + 33.33 + 33.34
        self.assertEqual(amounts, [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")])

    def test_closed_batch_rejected(self):
        b = self._batch("100", "80000")
        b.status = Batch.Status.CLOSED
        b.save(update_fields=["status"])
        with self.assertRaises(BusinessError):
            cost_services.record_purchase_cost(
                cost_type=PurchaseCost.CostType.ICE,
                amount=Decimal("100000"),
                allocation_method=PurchaseCost.AllocationMethod.BY_QTY,
                incurred_date=self.today,
                allocations=[b],
                actor=self.user,
            )
        # BR-GV-02: không ghi gì cả (rollback)
        self.assertEqual(PurchaseCost.objects.count(), 0)
        self.assertEqual(PurchaseCostAllocation.objects.count(), 0)

    def test_retroactive_cost_after_partial_sale(self):
        # giá vốn hồi tố: lô đã bán vài kg, chi phí về sau vẫn cập nhật landed_unit_cost
        b = self._batch("100", "80000")
        b.status = Batch.Status.SELLING
        b.save(update_fields=["status"])
        stock_services.record_movement(
            batch=b, qty_change=Decimal("-30"),
            movement_type=b.ledger_entries.model.MovementType.SALE,
        )
        cost_services.record_purchase_cost(
            cost_type=PurchaseCost.CostType.ICE,
            amount=Decimal("1000000"),
            allocation_method=PurchaseCost.AllocationMethod.BY_QTY,
            incurred_date=self.today,
            allocations=[b],
            actor=self.user,
        )
        b.refresh_from_db()
        # mẫu số vẫn là qty_received=100 (BR-GV-01), không phải tồn còn lại
        self.assertEqual(b.landed_unit_cost, Decimal("90000"))
