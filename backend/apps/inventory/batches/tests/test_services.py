import datetime
from decimal import Decimal

from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batch_services
from apps.inventory.batches.tests.base import InventoryServiceBase
from apps.inventory.models import Batch
from apps.inventory.stock import services as stock_services


class BatchServiceTests(InventoryServiceBase):
    def test_create_batch_sets_qty_expiry_and_ledger(self):
        b = self._batch()
        self.assertEqual(b.qty_available, Decimal("100"))
        self.assertEqual(b.qty_received, Decimal("100"))
        self.assertEqual(b.status, Batch.Status.DRAFT)
        self.assertEqual(b.expiry_date, self.today + datetime.timedelta(days=90))
        self.assertEqual(b.ledger_entries.count(), 1)

    def test_allocate_fefo_cung_han_thi_lo_nhap_truoc_ra_truoc(self):
        # F1: hai lô cùng hạn (cùng ngày tạo + 90) -> tiêu chí phụ ngày nhập (BR-BH-05).
        b1 = self._batch(qty="5")
        b1.received_date = datetime.date(2026, 8, 1)
        b1.status = Batch.Status.SELLING
        b1.save()
        b2 = self._batch(qty="5")
        b2.status = Batch.Status.SELLING
        b2.save()
        alloc = batch_services.allocate_fefo(item=self.item, qty=Decimal("7"))
        self.assertEqual(alloc[0][0].pk, b1.pk)      # cùng hạn: lô nhập trước ra trước
        self.assertEqual(alloc[0][1], Decimal("5"))
        self.assertEqual(alloc[1][1], Decimal("2"))

    def test_allocate_fefo_insufficient_raises(self):
        b = self._batch(qty="3")
        b.status = Batch.Status.SELLING
        b.save()
        with self.assertRaises(BusinessError):
            batch_services.allocate_fefo(item=self.item, qty=Decimal("5"))

    def test_reserve_reduces_sellable_and_blocks_oversell(self):
        b = self._batch(qty="4")
        b.status = Batch.Status.SELLING
        b.save()
        batch_services.reserve(batch=b, qty=Decimal("4"))
        b.refresh_from_db()
        self.assertEqual(b.qty_sellable, Decimal("0"))
        with self.assertRaises(BusinessError):
            batch_services.reserve(batch=b, qty=Decimal("1"))

    def test_draft_batch_not_sellable(self):
        self._batch(qty="10")  # DRAFT
        with self.assertRaises(BusinessError):
            batch_services.allocate_fefo(item=self.item, qty=Decimal("1"))

    def test_publish_and_close_batch(self):
        b = self._batch(qty="2")
        batch_services.publish_batch(batch=b, actor=None)
        b.refresh_from_db()
        self.assertEqual(b.status, Batch.Status.SELLING)
        # bán hết
        stock_services.record_movement(
            batch=b, qty_change=Decimal("-2"),
            movement_type=b.ledger_entries.model.MovementType.SALE,
        )
        b.refresh_from_db()
        batch_services.close_batch(batch=b, actor=None)
        b.refresh_from_db()
        self.assertEqual(b.status, Batch.Status.CLOSED)
        self.assertIsNotNone(b.closed_at)

    def test_close_batch_requires_zero_stock(self):
        b = self._batch(qty="5")
        batch_services.publish_batch(batch=b, actor=None)
        b.refresh_from_db()
        with self.assertRaises(BusinessError):
            batch_services.close_batch(batch=b, actor=None)
