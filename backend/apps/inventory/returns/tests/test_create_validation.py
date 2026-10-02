"""R9 (02b §3.8): tạo hàng hoàn từ phiếu giao. BR-HV-01/02, BR-PQ-12/14/16, ED-26-AC2. Dữ liệu giả."""
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.delivery.models import DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import ReturnToStock, StockLedgerEntry

from .base import NOTE_WITH_PHONE, PHONE_SENTINEL, URL, ReturnsApiBase


class CreateReturnTests(ReturnsApiBase):
    def test_r9_ed26_ac2_courier_creates_for_own_note(self):
        resp = self.post(self.courier, self.payload(qty="4.5", note="Khách vắng nhà"))
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        rt = ReturnToStock.objects.get()
        self.assertEqual((rt.status, rt.decision), ("DRAFT", "PENDING"))
        self.assertEqual(rt.created_by, self.courier)
        self.assertEqual(rt.delivery_note, self.note)
        self.assertEqual(rt.qty, Decimal("4.5"))
        self.assertEqual(body["code"], f"RT-{rt.pk}")
        self.assertEqual(body["delivery_note_code"], self.note.code)
        self.assertEqual(body["order_code"], "SO-R9-A")
        self.assertEqual(body["batch_code"], self.batch.batch_id)
        self.assertEqual(body["item_name"], "Cá thu")
        self.assertEqual(body["status_label"], "Chờ duyệt")
        self.assertEqual(body["decision_label"], "Chờ quyết định")
        self.assertEqual(body["created_by"], self.courier.pk)
        self.assertEqual(body["created_by_name"], "Phúc Thử")
        self.assertEqual(body["note"], "Khách vắng nhà")

    def test_r9_note_with_phone_is_rejected(self):
        """QA Lô 9 B1: ghi chú có dãy số dài (SĐT) bị chặn ở API — cùng luật các ghi chú khác (bất biến 9)."""
        for note in (NOTE_WITH_PHONE, "gọi 0900 000 777", "stk 0900.000.777"):
            resp = self.post(self.courier, self.payload(note=note))
            self.assertEqual(resp.status_code, 400, (note, resp.content))
            self.assertNotIn(PHONE_SENTINEL, resp.content.decode())
        self.assertFalse(ReturnToStock.objects.exists())
        rt = self.make_return(free_note="")
        resp = client_for(self.owner).patch(f"{URL}{rt.pk}/", {"note": NOTE_WITH_PHONE}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_r9_closed_batch_rejects_new_return(self):
        """QA Lô 9 B4: lô đã chốt không nhận hàng hoàn mới (duyệt cũng bị chặn BR-HV-04)."""
        self.batch.status = self.batch.Status.CLOSED
        self.batch.save(update_fields=["status"])
        resp = self.post(self.courier, self.payload())
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RETURN_BATCH_CLOSED")
        self.assertFalse(ReturnToStock.objects.exists())

    def test_r9_br_hv_02_create_does_not_change_stock(self):
        before = self.batch.qty_available
        ledger_before = StockLedgerEntry.objects.count()
        self.assertEqual(self.post(self.courier, self.payload()).status_code, 201)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, before)
        self.assertEqual(StockLedgerEntry.objects.count(), ledger_before)

    def test_r9_audit_return_to_warehouse_written_without_free_text(self):
        resp = self.post(self.courier, self.payload(note="Khách Nguyễn Thử hẹn lại"))
        self.assertEqual(resp.status_code, 201, resp.content)
        rows = AuditLog.objects.filter(model_name="inventory.ReturnToStock", object_id=str(resp.json()["id"]))
        self.assertEqual([r.action for r in rows], ["return_to_warehouse"])
        self.assertEqual(rows[0].actor, self.courier)
        for row in AuditLog.objects.all():
            blob = f"{row.changes} {row.note} {row.object_repr}"
            self.assertNotIn(PHONE_SENTINEL, blob)
            self.assertNotIn("Nguyễn Thử", blob)

    def test_r9_left_warehouse_at_taken_from_start_of_delivery(self):
        body = self.post(self.courier, self.payload()).json()
        self.assertIsNotNone(body["left_warehouse_at"])
        self.assertIsNotNone(body["returned_at"])
        self.assertIsInstance(body["outside_minutes"], int)
        self.assertGreaterEqual(body["outside_minutes"], 0)

    def test_r9_failed_note_also_accepted(self):
        DeliveryNote.objects.filter(pk=self.note.pk).update(status=DeliveryNote.Status.FAILED)
        self.assertEqual(self.post(self.courier, self.payload()).status_code, 201)

    def test_r9_warehouse_staff_and_owner_create_for_any_note(self):
        for user in (self.warehouse_staff, self.owner):
            resp = self.post(user, self.payload(delivery_note=self.other_note, qty="1"))
            self.assertEqual(resp.status_code, 201, (user.username, resp.content))
        self.assertEqual(ReturnToStock.objects.count(), 2)

    # --- phạm vi dòng: delivery_staff -------------------------------------------------------------------------
    def test_r2_return_other_courier_404(self):
        resp = self.post(self.courier, self.payload(delivery_note=self.other_note))
        self.assertEqual(resp.status_code, 404, resp.content)
        self.assertFalse(ReturnToStock.objects.exists())
        self.assertEqual(AuditLog.objects.filter(action="return_to_warehouse").count(), 0)

    def test_r2_nonexistent_note_is_indistinguishable_from_other_courier_404(self):
        missing = self.post(self.courier, {**self.payload(), "delivery_note": 999999})
        other = self.post(self.courier, self.payload(delivery_note=self.other_note))
        self.assertEqual((missing.status_code, other.status_code), (404, 404))
        self.assertEqual(missing.json(), other.json())

    # --- không tạo vượt số kg đã giao ----------------------------------------------------------------------------
    def test_r9_qty_over_delivered_400(self):
        resp = self.post(self.courier, self.payload(qty="10.001"))
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RETURN_QTY_EXCEEDS")
        self.assertFalse(ReturnToStock.objects.exists())

    def test_r9_qty_equal_to_delivered_ok(self):
        self.assertEqual(self.post(self.courier, self.payload(qty="10")).status_code, 201)

    def test_r9_qty_cumulative_over_delivered_400(self):
        self.assertEqual(self.post(self.courier, self.payload(qty="6")).status_code, 201)
        resp = self.post(self.courier, self.payload(qty="4.001"))
        self.assertEqual((resp.status_code, resp.json()["code"]), (400, "RETURN_QTY_EXCEEDS"))
        self.assertEqual(self.post(self.courier, self.payload(qty="4")).status_code, 201)
        self.assertEqual(self.post(self.courier, self.payload(qty="0.001")).status_code, 400)
        self.assertEqual(ReturnToStock.objects.count(), 2)

    def test_r9_qty_sums_all_allocation_lines_of_same_batch(self):
        self.add_allocation(self.note, self.batch, "5")  # tổng 15 kg của cùng lô
        self.assertEqual(self.post(self.courier, self.payload(qty="15")).status_code, 201)

    def test_r9_batch_not_in_note_400(self):
        other_batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            qty=Decimal("5"), purchase_rate=Decimal("90000"),
        )
        resp = self.post(self.courier, {**self.payload(), "batch": other_batch.pk})
        self.assertEqual((resp.status_code, resp.json()["code"]), (400, "RETURN_BATCH_NOT_IN_NOTE"))
        self.assertFalse(ReturnToStock.objects.exists())

    def test_r9_note_status_must_be_failed_or_delivering(self):
        for status in ("PREPARING", "READY", "COMPLETED", "CANCELLED"):
            DeliveryNote.objects.filter(pk=self.note.pk).update(status=status)
            resp = self.post(self.warehouse_staff, self.payload())
            self.assertEqual((resp.status_code, resp.json()["code"]), (400, "RETURN_NOTE_STATUS"), status)
        self.assertFalse(ReturnToStock.objects.exists())

    # --- tham số sai --------------------------------------------------------------------------------------------
    def test_r9_bad_input_400(self):
        bad_payloads = [
            {"batch": self.batch.pk, "qty": "1"},                               # thiếu phiếu giao
            {"delivery_note": self.note.pk, "qty": "1"},                        # thiếu lô
            {"delivery_note": self.note.pk, "batch": self.batch.pk},            # thiếu số kg
            self.payload(qty="0"), self.payload(qty="-1"), self.payload(qty="abc"), self.payload(qty="1.0001"),
            self.payload(qty=None), self.payload(note="x" * 501),
            {**self.payload(), "delivery_note": "abc"}, {**self.payload(), "delivery_note": True},
            {**self.payload(), "delivery_note": 10**30}, {**self.payload(), "delivery_note": None},
            {**self.payload(), "batch": "abc"}, {**self.payload(), "batch": 10**30}, {**self.payload(), "batch": 999999},
        ]
        for payload in bad_payloads:
            resp = self.post(self.courier, payload)
            self.assertEqual(resp.status_code, 400, (payload, resp.status_code, resp.content))
        self.assertFalse(ReturnToStock.objects.exists())

    def test_r9_locked_and_actor_fields_rejected(self):
        cases = {
            "status": ("APPROVED", "BR-PQ-14"), "decision": ("RESTOCK", "BR-PQ-14"),
            "approved_by": (self.owner.pk, "BR-PQ-14"), "created_by": (self.owner.pk, "BR-PQ-16"),
            "left_warehouse_at": ("2026-10-01T00:00:00Z", "BR-PQ-14"),
            "returned_at": ("2026-10-01T00:00:00Z", "BR-PQ-14"),
        }
        for field, (value, code) in cases.items():
            resp = self.post(self.courier, {**self.payload(), field: value})
            self.assertEqual((resp.status_code, resp.json()["code"]), (400, code), field)
        self.assertFalse(ReturnToStock.objects.exists())

    # --- quyền --------------------------------------------------------------------------------------------------
    def test_r9_forbidden_groups_403(self):
        for user in (self.manager, self.customer_service, self.no_group):
            resp = self.post(user, self.payload())
            self.assertEqual(resp.status_code, 403, (user.username, resp.content))
        self.assertFalse(ReturnToStock.objects.exists())

    def test_r9_unauthenticated_401(self):
        self.assertEqual(client_for(None).post(URL, self.payload(), format="json").status_code, 401)

    def test_r9_note_text_is_covered_by_ai_scrub_keys(self):
        from apps.ai.policy.rules import SCRUB_FREE_TEXT_KEYS

        self.assertIn("note", SCRUB_FREE_TEXT_KEYS)
