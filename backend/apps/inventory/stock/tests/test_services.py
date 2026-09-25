from decimal import Decimal

from apps.common.exceptions import BusinessError
from apps.inventory.batches.tests.base import InventoryServiceBase
from apps.inventory.stock import services as stock_services


class StockLedgerServiceTests(InventoryServiceBase):
    def test_record_movement_cannot_go_negative(self):
        b = self._batch(qty="10")
        with self.assertRaises(BusinessError):
            stock_services.record_movement(
                batch=b, qty_change=Decimal("-11"),
                movement_type=b.ledger_entries.model.MovementType.SALE,
            )
