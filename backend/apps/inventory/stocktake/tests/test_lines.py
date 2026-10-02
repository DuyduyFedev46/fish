"""
B1 — gửi dòng số đếm kiểm kê (ED-27, BR-KK-01/04/08, BR-PQ-10) — 02b §3 B1.

Tạo phiếu kèm dòng: POST /api/inventory/reconciliations/
Thay toàn bộ dòng:   POST /api/inventory/reconciliations/{id}/lines/ (cần `expected_updated_at`)
"""
from decimal import Decimal

from apps.accounts.models import AuditLog
from apps.inventory.models import Batch, StockLedgerEntry, StockReconciliation

from .base import URL, StocktakeApiBase, line


class CreateReconciliationTests(StocktakeApiBase):
    def test_ed27_ac1_create_with_lines_snapshots_system_qty(self):
        body = self.create_via_api(
            self.warehouse_staff, [line(self.batch, "48.500"), line(self.batch2, "30.300", "Lần xuất 27/09 ghi dư")]
        )
        self.assertEqual(body["status"], "DRAFT")
        self.assertEqual(body["created_by"]["id"], self.warehouse_staff.pk)
        by_batch = {row["batch"]: row for row in body["lines"]}
        first = by_batch[self.batch.pk]
        self.assertEqual(first["system_qty"], "50.000")
        self.assertEqual(first["counted_qty"], "48.500")
        self.assertEqual(first["difference_qty"], "-1.500")
        second = by_batch[self.batch2.pk]
        self.assertEqual(second["difference_qty"], "0.300")
        # Chưa duyệt thì kho không đổi (BR-KK-01).
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("50.000"))
        self.assertFalse(StockLedgerEntry.objects.filter(movement_type="RECONCILE").exists())

    def test_ed27_ac1_client_system_qty_and_difference_are_ignored(self):
        payload = [{**line(self.batch, "48.500"), "system_qty": "999", "difference_qty": "999"}]
        body = self.create_via_api(self.warehouse_staff, payload)
        self.assertEqual(body["lines"][0]["system_qty"], "50.000")
        self.assertEqual(body["lines"][0]["difference_qty"], "-1.500")

    def test_ed27_ac5_group_matrix_on_create(self):
        for user in (self.owner, self.manager, self.warehouse_staff):
            resp = self.api(user).post(
                URL, {"count_date": str(self.today), "lines": [line(self.batch, "40")]}, format="json"
            )
            self.assertEqual(resp.status_code, 201, (user.username, resp.content))
        before = StockReconciliation.objects.count()
        payload = {"count_date": str(self.today), "lines": [line(self.batch, "40")]}
        for user in (self.delivery_staff, self.customer_service):
            self.assertEqual(self.api(user).post(URL, payload, format="json").status_code, 403, user.username)
        self.assertEqual(self.api(None).post(URL, payload, format="json").status_code, 401)
        self.assertEqual(StockReconciliation.objects.count(), before)

    def test_ed27_ac4_negative_count_is_400_and_creates_nothing(self):
        resp = self.api(self.warehouse_staff).post(
            URL, {"count_date": str(self.today), "lines": [line(self.batch, "-0.100")]}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_LINE_INVALID")
        self.assertEqual(resp.json()["line_index"], 0)
        self.assertIn("Dòng 1", resp.json()["detail"])
        self.assertFalse(StockReconciliation.objects.exists())

    def test_ed27_ac4_non_numeric_nan_and_too_many_decimals_are_400(self):
        for bad in ("abc", "NaN", "Infinity", "1.2345", "", None, True, [1]):
            resp = self.api(self.warehouse_staff).post(
                URL,
                {"count_date": str(self.today), "lines": [{"batch": self.batch.pk, "counted_qty": bad}]},
                format="json",
            )
            self.assertEqual(resp.status_code, 400, (bad, resp.content))
            self.assertEqual(resp.json()["code"], "RECON_LINE_INVALID", bad)
        self.assertFalse(StockReconciliation.objects.exists())

    def test_ed27_ac4_duplicate_batch_is_400_and_points_to_second_line(self):
        resp = self.api(self.warehouse_staff).post(
            URL,
            {"count_date": str(self.today), "lines": [line(self.batch, "40"), line(self.batch, "41")]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_LINE_INVALID")
        self.assertEqual(resp.json()["line_index"], 1)
        self.assertFalse(StockReconciliation.objects.exists())

    def test_ed27_ac4_unknown_batch_and_bad_batch_ids_are_400(self):
        for bad in (999999, "abc", 0, -3, None, "12.5", 10**30, True):
            resp = self.api(self.warehouse_staff).post(
                URL,
                {"count_date": str(self.today), "lines": [{"batch": bad, "counted_qty": "1"}]},
                format="json",
            )
            self.assertEqual(resp.status_code, 400, (bad, resp.content))
            self.assertEqual(resp.json()["code"], "RECON_LINE_INVALID", bad)

    def test_ed27_ac4_cancelled_or_closed_batch_is_400(self):
        for status in (Batch.Status.CANCELLED, Batch.Status.CLOSED):
            Batch.objects.filter(pk=self.batch.pk).update(status=status)
            resp = self.api(self.warehouse_staff).post(
                URL, {"count_date": str(self.today), "lines": [line(self.batch, "1")]}, format="json"
            )
            self.assertEqual(resp.status_code, 400, (status, resp.content))
            self.assertEqual(resp.json()["code"], "RECON_LINE_INVALID", status)

    def test_ed27_ac2_positive_difference_requires_reason(self):
        resp = self.api(self.warehouse_staff).post(
            URL, {"count_date": str(self.today), "lines": [line(self.batch, "52")]}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-KK-04")
        self.assertEqual(resp.json()["line_index"], 0)
        # Chỉ khoảng trắng cũng không tính là lý do.
        resp = self.api(self.warehouse_staff).post(
            URL, {"count_date": str(self.today), "lines": [line(self.batch, "52", "   ")]}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        # Có lý do thì được; chênh âm không cần lý do.
        self.create_via_api(self.warehouse_staff, [line(self.batch, "52", "Lần xuất trước ghi dư")])
        self.create_via_api(self.warehouse_staff, [line(self.batch, "49")])

    def test_reason_longer_than_500_chars_is_400(self):
        resp = self.api(self.warehouse_staff).post(
            URL, {"count_date": str(self.today), "lines": [line(self.batch, "40", "x" * 501)]}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_LINE_INVALID")

    def test_lines_must_be_non_empty_list_when_sent(self):
        for bad in ([], "abc", {"batch": 1}, [1, 2], None):
            resp = self.api(self.warehouse_staff).post(
                URL, {"count_date": str(self.today), "lines": bad}, format="json"
            )
            self.assertEqual(resp.status_code, 400, (bad, resp.content))
            self.assertEqual(resp.json()["code"], "RECON_LINE_INVALID", bad)

    def test_too_many_lines_is_400(self):
        resp = self.api(self.warehouse_staff).post(
            URL,
            {"count_date": str(self.today), "lines": [{"batch": self.batch.pk, "counted_qty": "1"}] * 501},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_LINE_INVALID")

    def test_create_without_lines_key_still_makes_empty_draft(self):
        """Tương thích cũ (S4): không gửi `lines` thì tạo phiếu rỗng, điền dòng sau qua …/lines/."""
        body = self.create_via_api(self.warehouse_staff)
        self.assertEqual(body["lines"], [])
        self.assertEqual(body["line_count"], 0)

    def test_create_audit_has_only_line_count(self):
        body = self.make_draft()
        row = AuditLog.objects.get(action="create_stockreconciliation", object_id=str(body["id"]))
        self.assertEqual(row.changes, {"line_count": 1})
        self.assertEqual(row.actor_id, self.warehouse_staff.pk)
        self.assertNotIn("Đếm đầu ca", str(row.changes) + row.note + row.object_repr)

    def test_no_cost_leak_on_create_for_warehouse_staff_and_manager(self):
        for user in (self.warehouse_staff, self.manager):
            resp = self.api(user).post(
                URL, {"count_date": str(self.today), "lines": [line(self.batch, "40")]}, format="json"
            )
            self.assertEqual(resp.status_code, 201)
            self.assertNoCostLeak(resp)


class ReplaceLinesTests(StocktakeApiBase):
    def test_ed27_replace_lines_happy_path_replaces_whole_set(self):
        rec = self.make_draft(lines=[line(self.batch, "48.500")])
        resp = self.replace_via_api(
            self.warehouse_staff, rec, [line(self.batch2, "29.000"), line(self.batch, "50.000")]
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(sorted(row["batch"] for row in body["lines"]), sorted([self.batch.pk, self.batch2.pk]))
        self.assertEqual(body["line_count"], 2)
        self.assertEqual(self.recon(rec["id"]).lines.count(), 2)
        self.assertGreater(body["updated_at"], rec["updated_at"])

    def test_replace_lines_audit_only_line_count(self):
        rec = self.make_draft()
        self.replace_via_api(self.manager, rec, [line(self.batch, "49")])
        row = AuditLog.objects.get(action="update_reconciliation_lines", object_id=str(rec["id"]))
        self.assertEqual(row.changes, {"line_count": 1})
        self.assertEqual(row.actor_id, self.manager.pk)

    def test_ed27_ac5_group_matrix_on_replace(self):
        rec = self.make_draft()
        for user in (self.owner, self.manager, self.warehouse_staff):
            current = self.api(user).get(f"{URL}{rec['id']}/").json()
            resp = self.replace_via_api(user, current, [line(self.batch, "49")])
            self.assertEqual(resp.status_code, 200, (user.username, resp.content))
        current = self.api(self.owner).get(f"{URL}{rec['id']}/").json()
        for user in (self.delivery_staff, self.customer_service):
            resp = self.replace_via_api(user, current, [line(self.batch, "10")])
            self.assertEqual(resp.status_code, 403, user.username)
        self.assertEqual(self.replace_via_api(None, current, [line(self.batch, "10")]).status_code, 401)
        self.assertEqual(self.recon(rec["id"]).lines.get().counted_qty, Decimal("49.000"))

    def test_ed27_ac3_replace_on_approved_is_400_recon_not_draft(self):
        rec = self.make_draft(self.warehouse_staff)
        self.assertEqual(self.approve_via_api(self.owner, rec).status_code, 200)
        approved = self.api(self.owner).get(f"{URL}{rec['id']}/").json()
        resp = self.replace_via_api(self.warehouse_staff, approved, [line(self.batch, "10")])
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_NOT_DRAFT")
        self.assertEqual(self.recon(rec["id"]).lines.get().counted_qty, Decimal("48.500"))

    def test_replace_invalid_lines_keep_old_lines(self):
        rec = self.make_draft(lines=[line(self.batch, "48.500")])
        for bad in ([], [line(self.batch, "-1")], [line(self.batch, "1"), line(self.batch, "2")]):
            resp = self.replace_via_api(self.warehouse_staff, rec, bad)
            self.assertEqual(resp.status_code, 400, (bad, resp.content))
            self.assertEqual(resp.json()["code"], "RECON_LINE_INVALID")
        lines = list(self.recon(rec["id"]).lines.all())
        self.assertEqual([x.counted_qty for x in lines], [Decimal("48.500")])

    def test_replace_requires_expected_updated_at(self):
        rec = self.make_draft()
        resp = self.api(self.warehouse_staff).post(
            f"{URL}{rec['id']}/lines/", {"lines": [line(self.batch, "49")]}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "EXPECTED_UPDATED_AT_REQUIRED")
        for bad in ("hôm qua", "2026-10-01T07:30:12", 123, ""):  # chuỗi lạ, thiếu múi giờ, không phải chuỗi
            resp = self.api(self.warehouse_staff).post(
                f"{URL}{rec['id']}/lines/",
                {"expected_updated_at": bad, "lines": [line(self.batch, "49")]}, format="json",
            )
            self.assertEqual(resp.status_code, 400, (bad, resp.content))
            self.assertIn(resp.json()["code"], ("EXPECTED_UPDATED_AT_REQUIRED", "EXPECTED_UPDATED_AT_INVALID"))

    def test_two_people_edit_at_once_second_gets_409_with_who_and_when(self):
        rec = self.make_draft(self.manager)  # cả hai cùng mở bản này
        first = self.replace_via_api(self.warehouse_staff, rec, [line(self.batch, "49")])
        self.assertEqual(first.status_code, 200, first.content)
        second = self.replace_via_api(self.manager, rec, [line(self.batch, "45")])
        self.assertEqual(second.status_code, 409, second.content)
        body = second.json()
        self.assertEqual(body["code"], "STALE_STATE")
        self.assertEqual(body["updated_by_name"], "Kho Thử")
        self.assertEqual(body["updated_at"], first.json()["updated_at"])
        # Dữ liệu của người sửa trước không bị ghi đè.
        self.assertEqual(self.recon(rec["id"]).lines.get().counted_qty, Decimal("49.000"))
        # Tải lại rồi gửi lại thì được.
        again = self.replace_via_api(self.manager, first.json(), [line(self.batch, "45")])
        self.assertEqual(again.status_code, 200, again.content)

    def test_stale_state_409_does_not_leak_personal_data_or_cost(self):
        rec = self.make_draft(self.manager)
        self.replace_via_api(self.warehouse_staff, rec, [line(self.batch, "49")])
        resp = self.replace_via_api(self.manager, rec, [line(self.batch, "45")])
        self.assertEqual(resp.status_code, 409)
        self.assertNotIn("0900000", resp.content.decode())  # SĐT nhân viên giả không lộ
        self.assertNoCostLeak(resp)

    def test_patch_note_bumps_updated_at_so_other_editor_gets_409(self):
        rec = self.make_draft(self.manager)
        resp = self.api(self.manager).patch(f"{URL}{rec['id']}/", {"note": "Đã đổi ghi chú"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        stale = self.replace_via_api(self.warehouse_staff, rec, [line(self.batch, "49")])
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["updated_by_name"], "Quản Lý Thử")

    def test_ed27_ac3_patch_on_approved_is_400_and_data_unchanged(self):
        rec = self.make_draft(self.warehouse_staff)
        self.approve_via_api(self.owner, rec)
        resp = self.api(self.owner).patch(f"{URL}{rec['id']}/", {"note": "Sửa sau khi duyệt"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_NOT_DRAFT")
        self.assertEqual(self.recon(rec["id"]).note, "Đếm đầu ca")

    def test_patch_with_lines_is_rejected_use_lines_endpoint(self):
        rec = self.make_draft()
        resp = self.api(self.warehouse_staff).patch(
            f"{URL}{rec['id']}/", {"lines": [line(self.batch, "1")]}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "RECON_USE_LINES_ENDPOINT")

    def test_patch_note_and_count_date_still_work_on_draft(self):
        rec = self.make_draft()
        resp = self.api(self.warehouse_staff).patch(
            f"{URL}{rec['id']}/", {"note": "Ghi chú mới", "count_date": "2026-10-02"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["note"], "Ghi chú mới")
        self.assertEqual(resp.json()["count_date"], "2026-10-02")

    def test_delete_is_405(self):
        rec = self.make_draft()
        for user in (self.owner, self.warehouse_staff):
            self.assertEqual(self.api(user).delete(f"{URL}{rec['id']}/").status_code, 405)

    def test_replace_no_cost_leak_for_warehouse_staff_and_manager(self):
        for user in (self.warehouse_staff, self.manager):
            rec = self.make_draft(user)
            resp = self.replace_via_api(user, rec, [line(self.batch, "49")])
            self.assertEqual(resp.status_code, 200)
            self.assertNoCostLeak(resp)


class ApproverRuleTests(StocktakeApiBase):
    """Duyệt kiểm kê. BR-KK-02/BR-KK-08 đã bỏ (Duy chốt 02/10, #6): xem thêm `test_submit_flow.py`."""

    def approve(self, user, rec):
        return self.approve_via_api(user, rec)

    def test_other_person_can_approve_and_stock_changes(self):
        rec = self.make_draft(self.warehouse_staff)
        self.replace_via_api(self.manager, rec, [line(self.batch, "49")])
        resp = self.approve(self.owner, rec)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "APPROVED")
        self.assertEqual(resp.json()["approved_by"]["id"], self.owner.pk)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("49.000"))
        entry = StockLedgerEntry.objects.get(movement_type="RECONCILE")
        self.assertEqual(entry.qty_change, Decimal("-1.000"))

    def test_approve_requires_approve_permission(self):
        rec = self.make_draft(self.manager)
        for user in (self.warehouse_staff2, self.delivery_staff, self.customer_service):
            self.assertEqual(self.approve(user, rec).status_code, 403, user.username)
        self.assertEqual(self.approve(None, rec).status_code, 401)

    def test_approve_twice_second_is_400_and_stock_applied_once(self):
        rec = self.make_draft(self.warehouse_staff)
        self.assertEqual(self.approve(self.owner, rec).status_code, 200)
        resp = self.approve(self.manager, rec)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("48.500"))
        self.assertEqual(StockLedgerEntry.objects.filter(movement_type="RECONCILE").count(), 1)

    def test_approve_bumps_updated_at(self):
        rec = self.make_draft(self.warehouse_staff)
        body = self.approve(self.owner, rec).json()
        self.assertGreater(body["updated_at"], rec["updated_at"])

    def test_approve_response_has_no_cost(self):
        rec = self.make_draft(self.warehouse_staff)
        self.assertNoCostLeak(self.approve(self.manager, rec))
