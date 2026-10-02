"""
Chốt chặn trạng thái phiếu nhập (sửa QA Lô 10 B1-B3, BR-MH-07, BR-MH-04, BR-GV-02, BR-PQ-10).

Phiếu đã huỷ không được ghi nhận lại, gắn hoá đơn, hay nhận chi phí. Chỉ phiếu Nháp mới ghi nhận và sửa được.
Mọi dữ liệu là giả.
"""
import datetime
from decimal import Decimal

from apps.inventory.models import Batch, StockLedgerEntry
from apps.purchasing.models import PurchaseInvoice, PurchaseReceipt
from apps.purchasing.receipts import services

from .api_base import URL, ReceiptsApiBase

INVOICES_URL = "/api/purchasing/invoices/"
COSTS_URL = "/api/purchasing/costs/"


class ReceiptStateGuardTests(ReceiptsApiBase):
    def cancel(self, receipt):
        services.cancel_receipt(receipt=receipt, actor=self.owner)
        receipt.refresh_from_db()
        return receipt

    def stock_snapshot(self):
        return (
            Batch.objects.count(),
            StockLedgerEntry.objects.count(),
            sorted(Batch.objects.values_list("pk", "qty_available", "status")),
        )

    # ---- B1: submit ----

    def test_b1_submit_cancelled_receipt_returns_400_and_makes_no_batch(self):
        receipt = self.cancel(self.receipt)
        before = self.stock_snapshot()
        resp = self.owner_client().post(f"{URL}{receipt.pk}/submit/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "RECEIPT_NOT_DRAFT")
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, PurchaseReceipt.Status.CANCELLED)
        self.assertEqual(self.stock_snapshot(), before)

    def test_b1_submit_cancelled_draft_receipt_makes_no_batch(self):
        """Phiếu nháp rồi huỷ (chưa có lô) cũng không ghi nhận lại được."""
        draft = self.make_draft()
        self.cancel(draft)
        before = self.stock_snapshot()
        resp = self.owner_client().post(f"{URL}{draft.pk}/submit/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "RECEIPT_NOT_DRAFT")
        self.assertEqual(self.stock_snapshot(), before)

    def test_b1_submit_twice_second_call_returns_400(self):
        draft = self.make_draft()
        client = self.owner_client()
        first = client.post(f"{URL}{draft.pk}/submit/", {}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(first.json()["batches_created"]), 1)
        before = self.stock_snapshot()
        second = client.post(f"{URL}{draft.pk}/submit/", {}, format="json")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.json()["code"], "RECEIPT_NOT_DRAFT")
        self.assertEqual(self.stock_snapshot(), before)

    def test_b1_submit_draft_happy_path(self):
        draft = self.make_draft()
        resp = self.owner_client().post(f"{URL}{draft.pk}/submit/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        draft.refresh_from_db()
        self.assertEqual(draft.status, PurchaseReceipt.Status.SUBMITTED)
        self.assertEqual(Batch.objects.filter(source_line__receipt=draft).count(), 1)

    def test_b1_submit_forbidden_for_role_without_change_permission(self):
        draft = self.make_draft()
        resp = self.owner_client(self.courier).post(f"{URL}{draft.pk}/submit/", {}, format="json")
        self.assertEqual(resp.status_code, 403)
        draft.refresh_from_db()
        self.assertEqual(draft.status, PurchaseReceipt.Status.DRAFT)

    def test_b1_error_does_not_echo_sender_value(self):
        receipt = self.cancel(self.receipt)
        resp = self.owner_client().post(f"{URL}{receipt.pk}/submit/", {"note": "GIATRI-NGUOI-GUI"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("GIATRI-NGUOI-GUI", resp.content.decode())

    # ---- B1: cancel ----

    def test_b1_cancel_twice_second_call_returns_400(self):
        client = self.owner_client()
        first = client.post(f"{URL}{self.receipt.pk}/cancel/", {}, format="json")
        self.assertEqual(first.status_code, 200)
        before = self.stock_snapshot()
        second = client.post(f"{URL}{self.receipt.pk}/cancel/", {}, format="json")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(self.stock_snapshot(), before)

    # ---- B1: sửa phiếu (PATCH) ----

    def test_b1_patch_non_draft_receipt_returns_400(self):
        cancelled = self.make_draft()
        self.cancel(cancelled)
        for receipt in (self.receipt, cancelled):  # đã ghi nhận, đã huỷ
            resp = self.owner_client().patch(
                f"{URL}{receipt.pk}/", {"supplier": self.other_supplier.pk}, format="json"
            )
            self.assertEqual(resp.status_code, 400, receipt.status)
            self.assertEqual(resp.json()["code"], "RECEIPT_NOT_DRAFT")
            receipt.refresh_from_db()
            self.assertEqual(receipt.supplier_id, self.supplier.pk)

    def test_b1_patch_draft_receipt_still_works(self):
        draft = self.make_draft()
        resp = self.owner_client().patch(f"{URL}{draft.pk}/", {"note": "ghi chú mới"}, format="json")
        self.assertEqual(resp.status_code, 200)
        draft.refresh_from_db()
        self.assertEqual(draft.note, "ghi chú mới")

    # ---- B2: hoá đơn ----

    def invoice_payload(self, receipt):
        return {
            "supplier": receipt.supplier_id, "receipt": receipt.pk, "amount": "1000.00",
            "invoice_date": "2026-09-28",
        }

    def test_b2_invoice_on_cancelled_receipt_returns_400(self):
        receipt = self.cancel(self.receipt)
        count = PurchaseInvoice.objects.count()
        resp = self.owner_client().post(INVOICES_URL, self.invoice_payload(receipt), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "RECEIPT_CANCELLED")
        self.assertEqual(PurchaseInvoice.objects.count(), count)

    def test_b2_invoice_on_submitted_receipt_still_works(self):
        resp = self.owner_client().post(INVOICES_URL, self.invoice_payload(self.receipt), format="json")
        self.assertEqual(resp.status_code, 201)

    def test_b2_invoice_without_receipt_still_works(self):
        payload = self.invoice_payload(self.receipt)
        payload.pop("receipt")
        resp = self.owner_client().post(INVOICES_URL, payload, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_b2_patch_invoice_to_cancelled_receipt_returns_400(self):
        invoice = self.add_invoice(self.receipt)
        cancelled = self.make_draft()
        self.cancel(cancelled)
        resp = self.owner_client().patch(f"{INVOICES_URL}{invoice.pk}/", {"receipt": cancelled.pk}, format="json")
        self.assertEqual(resp.status_code, 400)
        invoice.refresh_from_db()
        self.assertEqual(invoice.receipt_id, self.receipt.pk)

    def test_b2_invoice_forbidden_for_warehouse_staff(self):
        resp = self.owner_client(self.warehouse_staff).post(
            INVOICES_URL, self.invoice_payload(self.receipt), format="json"
        )
        self.assertEqual(resp.status_code, 403)

    # ---- B3: chi phí ----

    def cost_payload(self, batches):
        return {
            "cost_type": "ICE", "amount": "100000", "allocation_method": "BY_QTY",
            "incurred_date": "2026-09-28",
            "allocations": [{"batch_id": b.batch_id} for b in batches],
        }

    def test_b3_cost_on_batch_of_cancelled_receipt_returns_400(self):
        batches = list(self.batches)
        self.cancel(self.receipt)
        before = {b.pk: b.landed_unit_cost for b in Batch.objects.filter(pk__in=[b.pk for b in batches])}
        resp = self.owner_client().post(COSTS_URL, self.cost_payload(batches), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BATCH_CANCELLED")
        after = {b.pk: b.landed_unit_cost for b in Batch.objects.filter(pk__in=before)}
        self.assertEqual(after, before)
        from apps.purchasing.models import PurchaseCost, PurchaseCostAllocation
        self.assertEqual(PurchaseCost.objects.count(), 0)
        self.assertEqual(PurchaseCostAllocation.objects.count(), 0)

    def test_b3_cost_mixed_live_and_cancelled_batches_rejected_entirely(self):
        other_receipt, other_batches = self.submit(
            self.supplier, [(self.item_a, "4", Decimal("90000"))], datetime.date(2026, 9, 29)
        )
        self.cancel(self.receipt)
        live = other_batches[0]
        live_before = Batch.objects.get(pk=live.pk).landed_unit_cost
        resp = self.owner_client().post(COSTS_URL, self.cost_payload([live, self.batches[0]]), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Batch.objects.get(pk=live.pk).landed_unit_cost, live_before)

    def test_b3_batch_of_cancelled_receipt_even_if_batch_status_not_cancelled(self):
        """Lô thuộc phiếu đã huỷ bị chặn dù trạng thái lô chưa kịp đổi (phòng dữ liệu lệch)."""
        PurchaseReceipt.objects.filter(pk=self.receipt.pk).update(status=PurchaseReceipt.Status.CANCELLED)
        resp = self.owner_client().post(COSTS_URL, self.cost_payload(self.batches), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BATCH_CANCELLED")

    def test_b3_cost_on_expired_cancelled_batch_still_accepted_before_close(self):
        """TL10B-M1, E-14, BR-GV-02: lô bán một phần, quá hạn, bị huỷ (BR-LO-03) nhưng chưa chốt vẫn nhận chi phí đến muộn."""
        from apps.inventory.batches import services as batch_services
        from apps.inventory.stock import services as stock_services

        batch = self.batches[0]
        stock_services.record_movement(
            batch=batch, qty_change=Decimal("-2"), movement_type=StockLedgerEntry.MovementType.SALE,
            reference="SO-TEST", actor=self.owner,
        )
        Batch.objects.filter(pk=batch.pk).update(status=Batch.Status.EXPIRED)
        batch_services.cancel_expired_batch(batch=Batch.objects.get(pk=batch.pk), actor=self.owner)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.CANCELLED)
        self.assertNotEqual(batch.source_line.receipt.status, PurchaseReceipt.Status.CANCELLED)
        before = batch.landed_unit_cost

        resp = self.owner_client().post(COSTS_URL, self.cost_payload([batch]), format="json")
        self.assertEqual(resp.status_code, 201)
        batch.refresh_from_db()
        self.assertGreater(batch.landed_unit_cost, before)

    def test_b3_cost_on_closed_batch_still_rejected(self):
        """BR-GV-02: lô đã chốt vẫn bị chặn (không đổi)."""
        Batch.objects.filter(pk=self.batches[0].pk).update(status=Batch.Status.CLOSED)
        resp = self.owner_client().post(COSTS_URL, self.cost_payload(self.batches[:1]), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertNotEqual(resp.json()["code"], "BATCH_CANCELLED")

    def test_b3_cost_on_live_batches_still_works(self):
        before = Batch.objects.get(pk=self.batches[0].pk).landed_unit_cost
        resp = self.owner_client().post(COSTS_URL, self.cost_payload(self.batches), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertGreater(Batch.objects.get(pk=self.batches[0].pk).landed_unit_cost, before)

    def test_b3_cost_forbidden_for_manager_and_warehouse_staff(self):
        for user in (self.manager, self.warehouse_staff):
            resp = self.owner_client(user).post(COSTS_URL, self.cost_payload(self.batches), format="json")
            self.assertEqual(resp.status_code, 403)

    def owner_client(self, user=None):
        from apps.common.tests.fixtures import client_for
        return client_for(user or self.owner)
