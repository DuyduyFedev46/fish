"""
TL-D3-L4 — Nhật ký: (1) dòng cũ có chữ tự do chỉ hiện "Có ghi chú" (không sửa DB); (2) AI tắt thì ẩn dòng AI
(count + phân trang). Dữ liệu giả.
"""
from django.test import TestCase, override_settings

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.common.audit import NOTE_PRESENT_LABEL, NOTE_PRESENT_NEUTRAL_LABEL, record_audit
from apps.common.tests.fixtures import client_for, make_user

URL = "/api/audit-logs/"
NAME, PHONE = "Nguyễn Văn Giả", "0900000321"


class OldNoteRedactionTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner_fake", roles.OWNER)

    def _notes(self):
        rows = client_for(self.owner).get(URL, {"page_size": 100}).json()
        rows = rows["results"] if isinstance(rows, dict) else rows
        return {r["action"]: r["note"] for r in rows}

    def test_old_free_text_rows_are_masked_but_db_untouched(self):
        old = f"{NAME} {PHONE}"
        for action in ("attach_payment", "resolve_payment", "mark_refund_failed", "cancel_paid_order",
                       "delivery_unconfirmed", "delivery_confirm_skipped", "delivery_extended",
                       "reject_sales.x"):
            record_audit(action, note=old)
        notes = self._notes()
        for action in ("attach_payment", "resolve_payment", "mark_refund_failed", "cancel_paid_order",
                       "delivery_unconfirmed", "delivery_confirm_skipped", "delivery_extended",
                       "reject_sales.x"):
            self.assertEqual(notes[action], NOTE_PRESENT_NEUTRAL_LABEL, action)
        blob = str(client_for(self.owner).get(URL, {"page_size": 100}).content, "utf-8")
        self.assertNotIn(NAME, blob)
        self.assertNotIn(PHONE, blob)
        self.assertTrue(AuditLog.objects.filter(note=old).count() == 8)  # DB không sửa

    def test_old_cancel_note_with_label_and_free_text_masked(self):
        record_audit("cancel_paid_order", note=f"Lý do: Khác — {NAME}")
        self.assertEqual(self._notes()["cancel_paid_order"], NOTE_PRESENT_NEUTRAL_LABEL)

    def test_new_fixed_notes_pass_through(self):
        record_audit("cancel_paid_order", note=f"Lý do: Khác · {NOTE_PRESENT_LABEL}")
        record_audit("resolve_payment", note="Hoàn tiền theo phiếu hoàn #12")
        record_audit("reject_sales.x", note="Từ chối đề xuất AI 12")
        record_audit("attach_payment", note=NOTE_PRESENT_LABEL)
        record_audit("delivery_extended", note=NOTE_PRESENT_NEUTRAL_LABEL)
        notes = self._notes()
        self.assertEqual(notes["cancel_paid_order"], f"Lý do: Khác · {NOTE_PRESENT_LABEL}")
        self.assertEqual(notes["resolve_payment"], "Hoàn tiền theo phiếu hoàn #12")
        self.assertEqual(notes["reject_sales.x"], "Từ chối đề xuất AI 12")
        self.assertEqual(notes["attach_payment"], NOTE_PRESENT_LABEL)

    def test_trailing_newline_does_not_slip_through(self):
        """RR-L2: fullmatch, `$` không cho phép đuôi `\\n` lọt."""
        record_audit("resolve_payment", note="Hoàn tiền theo phiếu hoàn #12\n" + NAME)
        record_audit("reject_sales.y", note="Từ chối đề xuất AI 12\n" + NAME)
        notes = self._notes()
        self.assertEqual(notes["resolve_payment"], NOTE_PRESENT_NEUTRAL_LABEL)
        self.assertEqual(notes["reject_sales.y"], NOTE_PRESENT_NEUTRAL_LABEL)

    def test_other_actions_untouched(self):
        record_audit("close_batch", note="câu cố định của hệ thống")
        self.assertEqual(self._notes()["close_batch"], "câu cố định của hệ thống")


class AiRowsHiddenWhenAiOffTests(TestCase):
    """Chỉ ẩn dòng DO AI làm. Dòng do người làm (kể cả có proposal_ref) phải còn (RR-M2)."""

    def setUp(self):
        self.owner = make_user("owner_fake", roles.OWNER)
        self.warehouse_user = make_user("warehouse_fake", roles.WAREHOUSE_STAFF)
        for i in range(22):
            record_audit("close_batch", actor=self.owner, note=f"u{i}")
        # Dòng DO AI làm: ẩn khi AI tắt.
        record_audit("propose_x", actor_kind="ai", ai_actor=self.warehouse_user, proposal_ref="P-1")
        record_audit("execute_x", actor_kind="ai", ai_actor=self.warehouse_user, proposal_ref="P-1")
        record_audit("escalate_overdue_x", actor_kind="system", proposal_ref="P-2")
        # Dòng do NGƯỜI làm: luôn giữ.
        record_audit("confirm_x", actor=self.owner, proposal_ref="P-1")  # người duyệt đề xuất
        record_audit("reject_x", actor=self.owner, proposal_ref="P-3")  # người từ chối
        record_audit("close_batch", actor=self.owner, proposal_ref="P-1", note="người duyệt thực thi")  # nghiệp vụ
        record_audit("ai_config_update", actor=self.owner)  # Chủ đổi cấu hình
        record_audit("ai_config_kill", actor=self.owner)
        record_audit("ai_policy_update", actor=self.owner)

    def _get(self, **params):
        return client_for(self.owner).get(URL, params).json()

    def _actions(self, body):
        return [r["action"] for r in body["results"]]

    @override_settings(AI_ENABLED=False)
    def test_ai_off_hides_only_rows_made_by_ai(self):
        body = self._get()
        self.assertEqual(body["count"], 22 + 6)
        self.assertEqual(len(body["results"]), 20)
        second = self._get(page=2)
        self.assertEqual(len(second["results"]), 8)
        shown = self._actions(body) + self._actions(second)
        for hidden in ("propose_x", "execute_x", "escalate_overdue_x"):
            self.assertNotIn(hidden, shown)
        for kept in ("confirm_x", "reject_x", "ai_config_update", "ai_config_kill", "ai_policy_update"):
            self.assertIn(kept, shown)
        self.assertIn("người duyệt thực thi", [r["note"] for r in body["results"] + second["results"]])
        self.assertEqual(self._get(actor_kind="ai")["count"], 0)

    @override_settings(AI_ENABLED=True)
    def test_ai_on_shows_all_rows(self):
        self.assertEqual(self._get()["count"], 22 + 9)
        self.assertEqual(self._get(actor_kind="ai")["count"], 2)
