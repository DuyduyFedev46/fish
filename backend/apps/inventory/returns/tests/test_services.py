from decimal import Decimal

from django.contrib.auth.models import User

from apps.inventory.batches import services as batch_services
from apps.inventory.batches.tests.base import InventoryServiceBase
from apps.inventory.models import ReturnToStock
from apps.inventory.returns import services as return_services
from apps.inventory.stock import services as stock_services


class ReturnServiceTests(InventoryServiceBase):
    def test_return_restock_adds_back_to_original_batch(self):
        b = self._batch(qty="10")
        batch_services.publish_batch(batch=b, actor=None)
        stock_services.record_movement(
            batch=b, qty_change=Decimal("-4"),
            movement_type=b.ledger_entries.model.MovementType.SALE,
        )
        b.refresh_from_db()
        rt = ReturnToStock.objects.create(
            batch=b, qty=Decimal("4"), decision=ReturnToStock.Decision.RESTOCK,
            created_by=User.objects.create(username="giao1"),
        )
        return_services.apply_return(return_to_stock=rt, approver=None)
        b.refresh_from_db()
        self.assertEqual(b.qty_available, Decimal("10"))  # cộng lại đúng lô gốc

    def test_return_writeoff_does_not_restock(self):
        b = self._batch(qty="10")
        batch_services.publish_batch(batch=b, actor=None)
        stock_services.record_movement(
            batch=b, qty_change=Decimal("-4"),
            movement_type=b.ledger_entries.model.MovementType.SALE,
        )
        rt = ReturnToStock.objects.create(
            batch=b, qty=Decimal("4"), decision=ReturnToStock.Decision.WRITE_OFF,
            created_by=User.objects.create(username="giao2"),
        )
        return_services.apply_return(return_to_stock=rt, approver=None)
        b.refresh_from_db()
        self.assertEqual(b.qty_available, Decimal("6"))  # không cộng lại
