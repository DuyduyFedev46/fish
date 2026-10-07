"""
B2 (QA 08/10, BR-MH-07, BR-GV-02): thêm chi phí ∥ huỷ phiếu nhập cùng lô -> không bao giờ cả hai cùng thành công,
không có PurchaseCostAllocation trỏ vào lô của phiếu CANCELLED, không deadlock.
Gốc lỗi: `select_for_update(of=("self",)).select_related("source_line__receipt")`; người chờ khoá lô thức dậy với
phía nối ngoài (source_line -> receipt) còn là bản cũ nên `_is_cancelled_batch` không chặn.
Chỉ chạy trên PostgreSQL. Dữ liệu giả.
"""
import threading
import time
from decimal import Decimal
from unittest import skipUnless

from django.db import connection, transaction
from django.test import TransactionTestCase

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import make_user
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.costs import services as cost_services
from apps.purchasing.models import PurchaseCostAllocation, PurchaseReceipt, Supplier
from apps.purchasing.receipts import services as receipt_services

JOIN_TIMEOUT_SECONDS = 10
ROUNDS = 15


@skipUnless(connection.vendor == "postgresql", "Cần PostgreSQL: select_for_update không có tác dụng trên SQLite.")
class CostVersusCancelReceiptRaceTests(TransactionTestCase):
    serialized_rollback = True

    def _fixture_setup(self):
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.all().delete()
        super()._fixture_setup()
        ContentType.objects.clear_cache()

    def setUp(self):
        self.owner = make_user("race_owner", roles.OWNER)
        group = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=group)
        self.supplier = Supplier.objects.create(name="Đầu mối A")
        self.warehouse = Warehouse.objects.create(name="Kho chính")

    def _receipt(self):
        receipt, batches = receipt_services.create_and_submit_receipt(
            supplier=self.supplier, actor=self.owner, warehouse=self.warehouse,
            lines=[{"item_code": self.item, "qty": Decimal("5"), "rate": Decimal("70000")}],
        )
        return receipt, batches[0]

    def _add_cost(self, batch):
        return cost_services.record_purchase_cost(
            cost_type="ICE", amount=Decimal("50000"), allocation_method="BY_QTY",
            incurred_date="2026-10-08", allocations=[{"batch_id": batch.batch_id}], actor=self.owner,
        )

    def _assert_no_cost_on_cancelled(self, receipt, batch):
        receipt = PurchaseReceipt.objects.get(pk=receipt.pk)
        if receipt.status == PurchaseReceipt.Status.CANCELLED:
            self.assertFalse(PurchaseCostAllocation.objects.filter(batch_id=batch.pk).exists(),
                             "chi phí lọt vào lô của phiếu đã huỷ (BR-MH-07)")
            self.assertEqual(Batch.objects.get(pk=batch.pk).status, Batch.Status.CANCELLED)

    def test_b2_cost_waiting_on_lock_sees_cancelled_receipt(self):
        """Huỷ phiếu giữ khoá, chi phí chờ; huỷ commit xong thì chi phí phải bị 400 BATCH_CANCELLED."""
        for i in range(ROUNDS):
            with self.subTest(i=i):
                receipt, batch = self._receipt()
                result = {}

                def cost():
                    try:
                        self._add_cost(batch)
                        result["outcome"] = "ok"
                    except BusinessError as exc:
                        result["outcome"] = exc.code
                    except Exception as exc:  # noqa: BLE001
                        result["outcome"] = f"ERROR {type(exc).__name__}"
                    finally:
                        connection.close()

                thread = threading.Thread(target=cost)
                with transaction.atomic():
                    receipt_services.cancel_receipt(receipt=receipt, actor=self.owner)
                    thread.start()
                    time.sleep(0.4)  # chi phí chắc chắn đang chờ khoá lô
                thread.join(JOIN_TIMEOUT_SECONDS)
                self.assertFalse(thread.is_alive(), "treo quá thời hạn (nghi deadlock)")
                self.assertEqual(result["outcome"], "BATCH_CANCELLED")
                self._assert_no_cost_on_cancelled(receipt, batch)

    def test_b2_cancel_and_cost_at_once_never_both_succeed(self):
        for i in range(ROUNDS * 2):
            with self.subTest(i=i):
                receipt, batch = self._receipt()
                barrier = threading.Barrier(2)
                result = {}

                def cancel():
                    try:
                        barrier.wait(JOIN_TIMEOUT_SECONDS)
                        receipt_services.cancel_receipt(receipt=receipt, actor=self.owner)
                        result["cancel"] = "ok"
                    except BusinessError as exc:
                        result["cancel"] = exc.code
                    except Exception as exc:  # noqa: BLE001
                        result["cancel"] = f"ERROR {type(exc).__name__}"
                    finally:
                        connection.close()

                def cost():
                    try:
                        barrier.wait(JOIN_TIMEOUT_SECONDS)
                        time.sleep((i % 6) * 0.01)  # lệch giờ 0-50 ms để phủ cả hai thứ tự
                        self._add_cost(batch)
                        result["cost"] = "ok"
                    except BusinessError as exc:
                        result["cost"] = exc.code
                    except Exception as exc:  # noqa: BLE001
                        result["cost"] = f"ERROR {type(exc).__name__}"
                    finally:
                        connection.close()

                threads = [threading.Thread(target=cancel), threading.Thread(target=cost)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(JOIN_TIMEOUT_SECONDS)
                    self.assertFalse(t.is_alive(), "treo quá thời hạn (nghi deadlock)")
                pair = (result["cancel"], result["cost"])
                self.assertIn(pair, {("ok", "BATCH_CANCELLED"), ("BR-MH-07", "ok")}, pair)
                self._assert_no_cost_on_cancelled(receipt, batch)
