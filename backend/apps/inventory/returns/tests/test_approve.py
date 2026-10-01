"""R9: duyệt hàng hoàn (BR-HV-01/02/04, ED-26-AC3/AC4/AC5). `apply_return` giữ nguyên, API bọc khoá + 409."""
from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.inventory.models import Batch, ReturnToStock, StockLedgerEntry

from .base import RATE_SENTINEL, URL, ReturnsApiBase, find_cost_keys


class ApproveReturnTests(ReturnsApiBase):
    def setUp(self):
        super().setUp()
        self.rt = self.make_return(self.note, "4", self.courier, "ghi chú")
        self.url = f"{URL}{self.rt.pk}/approve/"

    def approve(self, user, decision=None):
        body = {} if decision is None else {"decision": decision}
        return client_for(user).post(self.url, body, format="json")

    def test_r9_ed26_ac3_manager_restock_adds_back_to_original_batch(self):
        self.batch.refresh_from_db()
        before = self.batch.qty_available
        resp = self.approve(self.manager, "RESTOCK")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body["status"], body["status_label"]), ("APPROVED", "Đã duyệt"))
        self.assertEqual((body["decision"], body["decision_label"]), ("RESTOCK", "Tái nhập"))
        self.assertEqual(body["approved_by"], self.manager.pk)
        self.assertEqual(body["code"], f"RT-{self.rt.pk}")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available - before, self.rt.qty)
        entry = StockLedgerEntry.objects.filter(movement_type="RETURN_RESTOCK").get()
        self.assertEqual(entry.batch, self.batch)
        self.assertTrue(AuditLog.objects.filter(action="approve_returntostock", object_id=str(self.rt.pk)).exists())

    def test_r9_write_off_does_not_restock(self):
        self.batch.refresh_from_db()
        before = self.batch.qty_available
        resp = self.approve(self.owner, "WRITE_OFF")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["decision_label"], "Huỷ bỏ, ghi lỗ")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, before)
        self.assertTrue(StockLedgerEntry.objects.filter(movement_type="WRITE_OFF", batch=self.batch).exists())

    def test_r9_ed26_ac5_only_holders_of_approve_perm(self):
        for user in (self.warehouse_staff, self.courier, self.other_courier, self.customer_service, self.no_group):
            resp = self.approve(user, "RESTOCK")
            self.assertEqual(resp.status_code, 403, (user.username, resp.content))
        self.assertEqual(client_for(None).post(self.url, {"decision": "RESTOCK"}, format="json").status_code, 401)
        self.rt.refresh_from_db()
        self.assertEqual((self.rt.status, self.rt.decision, self.rt.approved_by), ("DRAFT", "PENDING", None))
        self.assertFalse(StockLedgerEntry.objects.filter(movement_type="RETURN_RESTOCK").exists())

    def test_r9_ed26_ac4_already_approved_gets_409_stale_state(self):
        self.assertEqual(self.approve(self.manager, "RESTOCK").status_code, 200)
        resp = self.approve(self.owner, "WRITE_OFF")
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["code"], "STALE_STATE")
        self.rt.refresh_from_db()
        self.assertEqual((self.rt.decision, self.rt.approved_by), ("RESTOCK", self.manager))  # không bị ghi đè
        self.assertEqual(StockLedgerEntry.objects.filter(movement_type="RETURN_RESTOCK").count(), 1)

    def test_r9_br_hv_02_decision_required(self):
        for body in (None, "PENDING", "", "FOO", 5):
            resp = self.approve(self.manager, body)
            self.assertEqual(resp.status_code, 400, (body, resp.content))
        self.rt.refresh_from_db()
        self.assertEqual((self.rt.status, self.rt.decision), ("DRAFT", "PENDING"))

    def test_r9_br_hv_04_closed_batch_rejected_and_decision_not_persisted(self):
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.CLOSED)
        resp = self.approve(self.manager, "RESTOCK")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-HV-04")
        self.rt.refresh_from_db()
        self.assertEqual((self.rt.status, self.rt.decision), ("DRAFT", "PENDING"))

    def test_r9_approve_response_has_no_cost(self):
        for user in (self.manager, self.owner):
            rt = self.make_return(self.note, "1", self.courier)
            resp = client_for(user).post(f"{URL}{rt.pk}/approve/", {"decision": "RESTOCK"}, format="json")
            self.assertEqual(resp.status_code, 200, resp.content)
            self.assertEqual(find_cost_keys(resp.json()), set())
            self.assertNotIn(RATE_SENTINEL, resp.content.decode())

    def test_r9_approve_unknown_id_404(self):
        self.assertEqual(client_for(self.manager).post(f"{URL}999999/approve/", {"decision": "RESTOCK"}, format="json").status_code, 404)

    def test_r9_no_delete(self):
        self.assertEqual(client_for(self.owner).delete(f"{URL}{self.rt.pk}/").status_code, 405)
        self.assertTrue(ReturnToStock.objects.filter(pk=self.rt.pk).exists())


class UpdateReturnTests(ReturnsApiBase):
    """PATCH chỉ đổi ghi chú khi phiếu còn Chờ duyệt (BR-PQ-10/14): số kg, lô, phiếu giao không sửa sau khi tạo."""

    def setUp(self):
        super().setUp()
        self.rt = self.make_return(self.note, "4", self.courier, "cũ")
        self.url = f"{URL}{self.rt.pk}/"

    def test_r9_owner_can_edit_note_only(self):
        resp = client_for(self.owner).patch(self.url, {"note": "mới"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.rt.refresh_from_db()
        self.assertEqual(self.rt.note, "mới")

    def test_r9_cannot_change_qty_batch_note_link(self):
        for field, value in {"qty": "9", "batch": self.batch.pk, "delivery_note": self.other_note.pk}.items():
            resp = client_for(self.owner).patch(self.url, {field: value}, format="json")
            self.assertEqual((resp.status_code, resp.json()["code"]), (400, "BR-PQ-14"), field)
        self.rt.refresh_from_db()
        self.assertEqual((str(self.rt.qty), self.rt.delivery_note), ("4.000", self.note))

    def test_r9_cannot_edit_after_approval(self):
        ReturnToStock.objects.filter(pk=self.rt.pk).update(status="APPROVED")
        resp = client_for(self.owner).patch(self.url, {"note": "sửa"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.rt.refresh_from_db()
        self.assertEqual(self.rt.note, "cũ")

    def test_r9_non_owner_cannot_patch(self):
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service):
            resp = client_for(user).patch(self.url, {"note": "x"}, format="json")
            self.assertIn(resp.status_code, (403, 404), (user.username, resp.status_code))
        self.rt.refresh_from_db()
        self.assertEqual(self.rt.note, "cũ")
