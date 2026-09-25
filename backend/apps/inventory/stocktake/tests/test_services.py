from decimal import Decimal

from django.contrib.auth.models import User

from apps.common.exceptions import BusinessError
from apps.inventory.batches.tests.base import InventoryServiceBase
from apps.inventory.models import StockReconciliation
from apps.inventory.stocktake import services as stocktake_services


class StocktakeServiceTests(InventoryServiceBase):
    def test_reconciliation_requires_different_approver(self):
        u1 = User.objects.create(username="kho1")
        b = self._batch(qty="100")
        rec = StockReconciliation.objects.create(count_date=self.today, created_by=u1)
        rec.lines.create(batch=b, system_qty=Decimal("100"), counted_qty=Decimal("97"))
        with self.assertRaises(BusinessError):
            stocktake_services.apply_reconciliation(reconciliation=rec, approver=u1)

    def test_reconciliation_applies_shrinkage(self):
        u1 = User.objects.create(username="kho2")
        u2 = User.objects.create(username="chu2")
        b = self._batch(qty="100")
        rec = StockReconciliation.objects.create(count_date=self.today, created_by=u1)
        rec.lines.create(batch=b, system_qty=Decimal("100"), counted_qty=Decimal("97"))
        stocktake_services.apply_reconciliation(reconciliation=rec, approver=u2)
        b.refresh_from_db()
        self.assertEqual(b.qty_available, Decimal("97"))  # hao hụt 3kg
        self.assertEqual(rec.status, StockReconciliation.Status.APPROVED)
