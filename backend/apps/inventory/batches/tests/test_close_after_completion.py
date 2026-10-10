"""
W37 L2 (S4): chốt lô khi mọi đơn tham chiếu đã Hoàn tất. BR-LO-04, BR-LO-05, BR-BH-18, bất biến 1.
Không sửa `OPEN_ORDER_STATUSES` (BOOKED, PAID, PROCESSING): COMPLETED không nằm trong đó nên không chặn.
Dữ liệu giả (SĐT 0900000xxx). Dựng lô và đơn dùng lại helper của `test_l1_close_batch`.
"""
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.delivery.models import DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.batches.tests import test_l1_close_batch as l1
from apps.inventory.models import Batch
from apps.sales.models import SalesInvoice, SalesOrder

BLOCKED_ONE = "Còn 1 đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04)."


class CloseAfterCompletionTests(TestCase):
    def setUp(self):
        l1.CloseBatchS04Tests.setUp(self)
        self.owner, self.manager = self.chu, self.quan_ly  # naming: allow - thuộc tính fixture cũ của test_l1_close_batch
        self.warehouse_user, self.courier = self.nv_kho, self.nv_giao  # naming: allow - thuộc tính fixture cũ của test_l1_close_batch

    _create_ready_batch = l1.CloseBatchS04Tests._create_ready_batch
    _attach_order = l1.CloseBatchS04Tests._attach_order

    def _close(self, user, batch):
        return client_for(user).post(f"/api/inventory/batches/{batch.pk}/close/")

    def _invoice_with_note(self, order, note_status):
        invoice = SalesInvoice.objects.create(
            code=f"INV-{order.code}", sales_order=order, customer=order.customer, issued_at=timezone.now(),
            amount=Decimal("100000"), status=SalesInvoice.Status.ISSUED,
        )
        note = invoice.delivery_notes.get()
        DeliveryNote.objects.filter(pk=note.pk).update(
            status=note_status, completed_at=timezone.now() if note_status == DeliveryNote.Status.COMPLETED else None,
        )
        return note

    def test_s4_ac1_all_orders_completed_or_cancelled_allows_close(self):
        batch = self._create_ready_batch()
        self._attach_order(batch, status=SalesOrder.Status.COMPLETED)
        self._attach_order(batch, status=SalesOrder.Status.CANCELLED, phone="0900000002")
        self._attach_order(batch, status=SalesOrder.Status.AUTO_CANCELLED, phone="0900000003")
        resp = self._close(self.owner, batch)
        self.assertEqual(resp.status_code, 200, resp.content)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.CLOSED)

    def test_s4_ac1_open_order_statuses_unchanged(self):
        self.assertEqual(batch_services.OPEN_ORDER_STATUSES, ("BOOKED", "PAID", "PROCESSING"))

    def test_s4_ac2_processing_order_with_failed_note_still_blocks(self):
        batch = self._create_ready_batch()
        self._attach_order(batch, status=SalesOrder.Status.COMPLETED)
        order = self._attach_order(batch, status=SalesOrder.Status.PROCESSING, phone="0900000002")
        self._invoice_with_note(order, DeliveryNote.Status.FAILED)
        resp = self._close(self.owner, batch)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json(), {"code": "BR-LO-04", "detail": BLOCKED_ONE})
        batch.refresh_from_db()
        self.assertNotEqual(batch.status, Batch.Status.CLOSED)

    def test_s4_ac3_old_batch_blocked_by_legacy_order_closes_after_backfill(self):
        batch = self._create_ready_batch()
        order = self._attach_order(batch, status=SalesOrder.Status.PROCESSING)
        self._invoice_with_note(order, DeliveryNote.Status.COMPLETED)  # dữ liệu cũ: phiếu xong, đơn chưa chuyển
        blocked = self._close(self.owner, batch)
        self.assertEqual(blocked.status_code, 400, blocked.content)
        self.assertEqual(blocked.json()["detail"], BLOCKED_ONE)

        call_command("backfill_completed_orders", stdout=StringIO())
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.COMPLETED)

        resp = self._close(self.owner, batch)
        self.assertEqual(resp.status_code, 200, resp.content)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.CLOSED)

    def test_s4_ac4_manager_without_close_batch_gets_403_and_batch_unchanged(self):
        batch = self._create_ready_batch()
        self._attach_order(batch, status=SalesOrder.Status.COMPLETED)
        for user in (self.manager, self.warehouse_user, self.courier):
            self.assertEqual(self._close(user, batch).status_code, 403)
        self.assertEqual(client_for(None).post(f"/api/inventory/batches/{batch.pk}/close/").status_code, 401)
        batch.refresh_from_db()
        self.assertNotEqual(batch.status, Batch.Status.CLOSED)
        self.assertFalse(AuditLog.objects.filter(action="close_batch", object_id=str(batch.pk)).exists())

    def test_s4_ac5_manager_sees_no_cost_after_close(self):
        batch = self._create_ready_batch(purchase_rate="99999")
        self._attach_order(batch, status=SalesOrder.Status.COMPLETED)
        self.assertEqual(self._close(self.owner, batch).status_code, 200)
        for user in (self.manager, self.warehouse_user):
            resp = client_for(user).get("/api/inventory/batches/")
            self.assertEqual(resp.status_code, 200, resp.content)
            text = resp.content.decode("utf-8")
            self.assertNotIn("purchase_rate", text)
            self.assertNotIn("landed_unit_cost", text)
            self.assertNotIn("99999", text)
        owner_row = client_for(self.owner).get("/api/inventory/batches/").json()["results"][0]
        self.assertIn("landed_unit_cost", owner_row)
