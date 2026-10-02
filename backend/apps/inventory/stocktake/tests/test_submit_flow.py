"""
Lô bổ sung A (Duy chốt 02/10) — #6 tự duyệt theo quyền, #20 trạng thái "Chờ duyệt" (SUBMITTED).

Luồng: DRAFT (nháp) → `POST …/submit/` → SUBMITTED (chờ duyệt) → `POST …/approve/` → APPROVED.
Không còn chặn "người nhập/sửa số không được duyệt" (BR-KK-02, BR-KK-08 bỏ); AuditLog vẫn ghi ai nhập, ai gửi, ai duyệt.
"""
from decimal import Decimal

from apps.accounts.models import AuditLog
from apps.inventory.models import StockLedgerEntry, StockReconciliation

from .base import URL, StocktakeApiBase, line


class SubmitFlowTests(StocktakeApiBase):
    def submit(self, user, rec):
        return self.api(user).post(f"{URL}{rec['id']}/submit/")

    def approve(self, user, rec):
        return self.api(user).post(f"{URL}{rec['id']}/approve/")

    def return_to_draft(self, user, rec):
        return self.api(user).post(f"{URL}{rec['id']}/return-to-draft/")

    # --- #20 luồng trạng thái ---
    def test_kk20_new_receipt_is_draft_and_label_is_draft_vi(self):
        rec = self.make_draft(self.warehouse_staff)
        self.assertEqual(rec["status"], "DRAFT")
        self.assertEqual(rec["status_label"], "Nháp")

    def test_kk20_submit_moves_to_submitted_with_label_cho_duyet(self):
        rec = self.make_draft(self.warehouse_staff)
        resp = self.submit(self.warehouse_staff, rec)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "SUBMITTED")
        self.assertEqual(resp.json()["status_label"], "Chờ duyệt")
        self.assertGreater(resp.json()["updated_at"], rec["updated_at"])
        self.assertNoCostLeak(resp)

    def test_kk20_approve_draft_is_400_must_submit_first_and_stock_unchanged(self):
        rec = self.make_draft(self.warehouse_staff)
        resp = self.approve(self.owner, rec)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_NOT_SUBMITTED")
        self.assertEqual(self.recon(rec["id"]).status, StockReconciliation.Status.DRAFT)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("50.000"))

    def test_kk20_submit_then_approve_applies_stock(self):
        rec = self.make_draft(self.warehouse_staff)
        self.submit(self.warehouse_staff, rec)
        resp = self.approve(self.owner, rec)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "APPROVED")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("48.500"))

    def test_kk20_submit_empty_reconciliation_is_400_recon_empty(self):
        rec = self.create_via_api(self.warehouse_staff)
        resp = self.submit(self.warehouse_staff, rec)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_EMPTY")
        self.assertEqual(self.recon(rec["id"]).status, StockReconciliation.Status.DRAFT)

    def test_kk20_submit_twice_and_submit_approved_is_400(self):
        rec = self.make_draft(self.warehouse_staff)
        self.assertEqual(self.submit(self.warehouse_staff, rec).status_code, 200)
        again = self.submit(self.warehouse_staff, rec)
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.json()["code"], "RECON_NOT_DRAFT")
        self.approve(self.owner, rec)
        self.assertEqual(self.submit(self.warehouse_staff, rec).status_code, 400)

    def test_kk20_submitted_cannot_edit_lines_or_note(self):
        rec = self.make_draft(self.warehouse_staff)
        submitted = self.submit(self.warehouse_staff, rec).json()
        resp = self.replace_via_api(self.warehouse_staff, submitted, [line(self.batch, "49")])
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_NOT_DRAFT")
        patch = self.api(self.warehouse_staff).patch(f"{URL}{rec['id']}/", {"note": "đổi"}, format="json")
        self.assertEqual(patch.status_code, 400, patch.content)
        self.assertEqual(self.recon(rec["id"]).lines.get().counted_qty, Decimal("48.500"))

    def test_kk20_submit_permission_matrix(self):
        rec = self.make_draft(self.warehouse_staff)
        for user in (self.delivery_staff, self.customer_service):
            self.assertEqual(self.submit(user, rec).status_code, 403, user.username)
        self.assertEqual(self.submit(None, rec).status_code, 401)
        self.assertEqual(self.recon(rec["id"]).status, StockReconciliation.Status.DRAFT)

    def test_kk20_available_actions_follow_status(self):
        rec = self.make_draft(self.warehouse_staff)
        url = f"{URL}{rec['id']}/"
        self.assertEqual(self.api(self.warehouse_staff).get(url).json()["available_actions"], ["edit_lines", "submit"])
        self.assertEqual(
            self.api(self.owner).get(url).json()["available_actions"], ["edit_lines", "submit"]
        )  # DRAFT: chưa duyệt được
        self.submit(self.warehouse_staff, rec)
        self.assertEqual(self.api(self.warehouse_staff).get(url).json()["available_actions"], ["return_to_draft"])
        self.assertEqual(
            self.api(self.owner).get(url).json()["available_actions"], ["return_to_draft", "approve"]
        )
        self.approve(self.owner, rec)
        self.assertEqual(self.api(self.owner).get(url).json()["available_actions"], [])

    def test_kk20_filter_status_submitted(self):
        a = self.make_draft(self.warehouse_staff)
        b = self.make_draft(self.warehouse_staff, [line(self.batch2, "29")])
        self.submit(self.warehouse_staff, b)
        resp = self.api(self.owner).get(f"{URL}?status=SUBMITTED").json()
        self.assertEqual({r["id"] for r in resp["results"]}, {b["id"]})
        self.assertNotIn(a["id"], {r["id"] for r in resp["results"]})

    def test_kk20_submitted_receipt_blocks_closing_batch_like_draft(self):
        from apps.inventory.batches import services as batch_services

        first = self.make_draft(self.warehouse_staff)
        self.submit(self.warehouse_staff, first)
        self.approve(self.owner, first)
        self.batch.refresh_from_db()
        codes = lambda: {m.code for m in batch_services.check_close_batch(self.batch)}  # noqa: E731
        self.assertNotIn("BR-KK-05", codes())
        second = self.make_draft(self.warehouse_staff, [line(self.batch, "48")])
        self.submit(self.warehouse_staff, second)
        self.assertIn("BR-KK-05", codes())

    # --- return-to-draft ---
    def test_kk20_return_to_draft_reopens_editing(self):
        rec = self.make_draft(self.warehouse_staff)
        submitted = self.submit(self.warehouse_staff, rec).json()
        resp = self.return_to_draft(self.manager, submitted)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "DRAFT")
        ok = self.replace_via_api(self.warehouse_staff, resp.json(), [line(self.batch, "49")])
        self.assertEqual(ok.status_code, 200, ok.content)

    def test_kk20_return_to_draft_only_from_submitted(self):
        rec = self.make_draft(self.warehouse_staff)
        resp = self.return_to_draft(self.warehouse_staff, rec)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "RECON_NOT_SUBMITTED")
        self.submit(self.warehouse_staff, rec)
        self.approve(self.owner, rec)
        self.assertEqual(self.return_to_draft(self.owner, rec).status_code, 400)

    def test_kk20_return_to_draft_requires_change_permission(self):
        rec = self.make_draft(self.warehouse_staff)
        self.submit(self.warehouse_staff, rec)
        for user in (self.delivery_staff, self.customer_service):
            self.assertEqual(self.return_to_draft(user, rec).status_code, 403, user.username)
        self.assertEqual(self.return_to_draft(None, rec).status_code, 401)

    # --- #6 tự duyệt theo quyền ---
    def test_kk06_creator_with_permission_can_approve_own_receipt(self):
        rec = self.make_draft(self.manager)
        self.submit(self.manager, rec)
        resp = self.approve(self.manager, rec)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["approved_by"]["id"], self.manager.pk)
        self.assertEqual(resp.json()["created_by"]["id"], self.manager.pk)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("48.500"))
        self.assertEqual(StockLedgerEntry.objects.filter(movement_type="RECONCILE").count(), 1)

    def test_kk06_editor_with_permission_can_approve(self):
        rec = self.make_draft(self.warehouse_staff)
        self.assertEqual(self.replace_via_api(self.manager, rec, [line(self.batch, "49")]).status_code, 200)
        self.submit(self.manager, rec)
        self.assertEqual(self.approve(self.manager, rec).status_code, 200)

    def test_kk06_user_without_approve_permission_still_403(self):
        rec = self.make_draft(self.warehouse_staff)
        self.submit(self.warehouse_staff, rec)
        self.assertEqual(self.approve(self.warehouse_staff, rec).status_code, 403)
        self.assertEqual(self.recon(rec["id"]).status, StockReconciliation.Status.SUBMITTED)

    def test_kk06_no_blocked_reason_for_creator(self):
        rec = self.make_draft(self.manager)
        self.submit(self.manager, rec)
        body = self.api(self.manager).get(f"{URL}{rec['id']}/").json()
        self.assertIn("approve", body["available_actions"])
        self.assertIsNone(body["approve_blocked_reason"])

    def test_kk06_audit_log_shows_who_entered_submitted_and_approved(self):
        rec = self.make_draft(self.warehouse_staff)
        self.replace_via_api(self.manager, rec, [line(self.batch, "49")])
        self.submit(self.warehouse_staff, rec)
        self.approve(self.owner, rec)
        rows = AuditLog.objects.filter(
            model_name=StockReconciliation._meta.label, object_id=str(rec["id"])
        ).order_by("id")
        actors = [(row.action, row.actor_id) for row in rows]
        self.assertEqual(actors, [
            ("create_stockreconciliation", self.warehouse_staff.pk),
            ("update_reconciliation_lines", self.manager.pk),
            ("submit_stockreconciliation", self.warehouse_staff.pk),
            ("approve_stockreconciliation", self.owner.pk),
        ])
        for row in rows:
            self.assertEqual(set(row.changes or {}) - {"line_count"}, set())
