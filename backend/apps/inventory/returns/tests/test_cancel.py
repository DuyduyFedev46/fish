"""
Lô bổ sung A (Duy chốt 02/10, #8): huỷ phiếu hàng hoàn còn Chờ duyệt — `POST /api/inventory/returns/{id}/cancel/`.

Phiếu bị huỷ không tính vào số kg đã hoàn của (phiếu giao, lô) nên tạo phiếu mới được. Không có DELETE (BR-PQ-10).
Quyền: người có `approve_returntostock` (Chủ, Quản lý) hoặc `change_returntostock`; riêng người tạo (có quyền tạo) huỷ được
phiếu của chính mình.
"""
from decimal import Decimal

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.inventory.batches import services as batch_services
from apps.inventory.models import ReturnToStock, StockLedgerEntry
from apps.inventory.returns.creation import returned_qty_by_batch

from .base import NOTE_WITH_PHONE, PHONE_SENTINEL, RATE_SENTINEL, URL, ReturnsApiBase, find_cost_keys


class CancelReturnTests(ReturnsApiBase):
    def setUp(self):
        super().setUp()
        self.rt = self.make_return(self.note, "4", self.courier, NOTE_WITH_PHONE.replace(PHONE_SENTINEL, "ghi chú"))
        self.url = f"{URL}{self.rt.pk}/cancel/"

    def cancel(self, user, url=None):
        return client_for(user).post(url or self.url, {}, format="json")

    # --- hành vi ---
    def test_return_cancel_manager_cancels_pending_and_stock_untouched(self):
        self.batch.refresh_from_db()
        before = self.batch.qty_available
        resp = self.cancel(self.manager)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body["status"], body["status_label"]), ("CANCELLED", "Đã huỷ"))
        self.rt.refresh_from_db()
        self.assertEqual(self.rt.status, ReturnToStock.Status.CANCELLED)
        self.assertEqual(self.rt.decision, ReturnToStock.Decision.PENDING)
        self.assertIsNone(self.rt.approved_by)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, before)
        self.assertFalse(StockLedgerEntry.objects.filter(movement_type__in=["RETURN_RESTOCK", "WRITE_OFF"]).exists())

    def test_return_cancel_creator_courier_cancels_own(self):
        self.assertEqual(self.cancel(self.courier).status_code, 200)

    def test_return_cancel_creator_warehouse_staff_cancels_own_not_others(self):
        mine = self.make_return(self.note, "1", self.warehouse_staff)
        self.assertEqual(self.cancel(self.warehouse_staff, f"{URL}{mine.pk}/cancel/").status_code, 200)
        resp = self.cancel(self.warehouse_staff)  # phiếu của người giao
        self.assertEqual(resp.status_code, 403, resp.content)
        self.rt.refresh_from_db()
        self.assertEqual(self.rt.status, ReturnToStock.Status.DRAFT)

    def test_return_cancel_other_courier_gets_404_and_not_creator_courier_403(self):
        self.assertEqual(self.cancel(self.other_courier).status_code, 404)
        by_staff = self.make_return(self.note, "1", self.warehouse_staff)
        resp = self.cancel(self.courier, f"{URL}{by_staff.pk}/cancel/")  # thấy phiếu (phiếu giao của mình) nhưng không phải người tạo
        self.assertEqual(resp.status_code, 403, resp.content)
        by_staff.refresh_from_db()
        self.assertEqual(by_staff.status, ReturnToStock.Status.DRAFT)

    def test_return_cancel_users_without_permission_and_anonymous(self):
        for user in (self.customer_service, self.no_group):
            self.assertIn(self.cancel(user).status_code, (403, 404), user.username)
        self.assertEqual(self.cancel(None).status_code, 401)
        self.rt.refresh_from_db()
        self.assertEqual(self.rt.status, ReturnToStock.Status.DRAFT)

    def test_return_cancel_approved_is_409_stale_state(self):
        self.assertEqual(
            client_for(self.manager).post(f"{URL}{self.rt.pk}/approve/", {"decision": "RESTOCK"}, format="json").status_code,
            200,
        )
        resp = self.cancel(self.manager)
        self.assertEqual((resp.status_code, resp.json()["code"]), (409, "STALE_STATE"))
        self.rt.refresh_from_db()
        self.assertEqual(self.rt.status, ReturnToStock.Status.APPROVED)

    def test_return_cancel_twice_is_409_and_approve_after_cancel_is_409(self):
        self.assertEqual(self.cancel(self.manager).status_code, 200)
        self.assertEqual(self.cancel(self.manager).status_code, 409)
        resp = client_for(self.manager).post(f"{URL}{self.rt.pk}/approve/", {"decision": "RESTOCK"}, format="json")
        self.assertEqual((resp.status_code, resp.json()["code"]), (409, "STALE_STATE"))
        self.assertFalse(StockLedgerEntry.objects.filter(movement_type="RETURN_RESTOCK").exists())

    def test_return_cancel_cancelled_cannot_be_edited(self):
        self.cancel(self.manager)
        resp = client_for(self.owner).patch(f"{URL}{self.rt.pk}/", {"note": "sửa"}, format="json")
        self.assertEqual((resp.status_code, resp.json()["code"]), (400, "RETURN_NOT_EDITABLE"))

    def test_return_cancel_frees_quantity_for_a_new_return(self):
        self.assertEqual(self.post(self.courier, self.payload(qty="6")).status_code, 201)  # 4 + 6 = 10 đã đủ
        over = self.post(self.courier, self.payload(qty="1"))
        self.assertEqual((over.status_code, over.json()["code"]), (400, "RETURN_QTY_EXCEEDS"))
        self.cancel(self.manager)
        self.assertEqual(returned_qty_by_batch(self.note), {self.batch.pk: Decimal("6")})
        self.assertEqual(self.post(self.courier, self.payload(qty="4")).status_code, 201)
        self.assertEqual(self.post(self.courier, self.payload(qty="0.001")).status_code, 400)

    def test_return_cancel_note_line_returned_qty_excludes_cancelled(self):
        self.cancel(self.manager)
        resp = client_for(self.courier).get(f"/api/delivery/notes/{self.note.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([line["returned_qty"] for line in resp.json()["lines"]], ["0.000"])

    def test_return_cancel_does_not_block_closing_batch(self):
        pending = "hàng hoàn đang chờ duyệt"
        self.assertTrue(any(pending in m.text for m in batch_services.check_close_batch(self.batch)))
        self.cancel(self.manager)
        self.assertFalse(any(pending in m.text for m in batch_services.check_close_batch(self.batch)))

    def test_return_cancel_filter_status_cancelled(self):
        self.cancel(self.manager)
        other = self.make_return(self.note, "1", self.courier)
        resp = client_for(self.manager).get(f"{URL}?status=CANCELLED").json()
        self.assertEqual([row["id"] for row in resp["results"]], [self.rt.pk])
        self.assertNotIn(other.pk, [row["id"] for row in resp["results"]])

    def test_return_cancel_delete_still_405(self):
        self.assertEqual(client_for(self.owner).delete(f"{URL}{self.rt.pk}/").status_code, 405)

    # --- AuditLog + dữ liệu cá nhân + giá vốn ---
    def test_return_cancel_writes_audit_without_free_text(self):
        rt = self.make_return(self.note, "1", self.courier, NOTE_WITH_PHONE)
        self.cancel(self.manager, f"{URL}{rt.pk}/cancel/")
        row = AuditLog.objects.get(action="cancel_returntostock", object_id=str(rt.pk))
        self.assertEqual(row.actor_id, self.manager.pk)
        self.assertNotIn(PHONE_SENTINEL, str(row.changes) + (row.note or ""))
        self.assertEqual(row.changes, {"status": {"from": "DRAFT", "to": "CANCELLED"}})

    def test_return_cancel_response_no_cost_and_no_store(self):
        resp = self.cancel(self.manager)
        self.assertEqual(find_cost_keys(resp.json()), set())
        self.assertNotIn(RATE_SENTINEL, resp.content.decode())
        self.assertIn("no-store", resp["Cache-Control"])
