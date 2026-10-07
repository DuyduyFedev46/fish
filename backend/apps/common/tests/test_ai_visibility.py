"""Lô dọn chữ AI (BR-AI-17, BR-PQ-04/05): một cờ AI ở BE, lọc dòng AI trước khi cắt `limit`. Dữ liệu giả."""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.accounts.models import AuditLog
from apps.common.ai_visibility import ai_features_enabled, exclude_ai_audit_rows
from apps.common.audit import record_audit


class AiVisibilityTests(TestCase):
    def setUp(self):
        record_audit("some_action", note="người")
        record_audit("some_action", actor_kind="ai", note="ai")
        record_audit("some_action", actor_kind="system", proposal_ref="P-1", note="hệ thống có đề xuất")
        record_audit("some_action", actor_kind="system", note="hệ thống thường")

    @override_settings(AI_ENABLED=False)
    def test_flag_off_hides_ai_rows_only(self):
        self.assertFalse(ai_features_enabled())
        notes = set(exclude_ai_audit_rows(AuditLog.objects.all()).values_list("note", flat=True))
        self.assertEqual(notes, {"người", "hệ thống thường"})

    @override_settings(AI_ENABLED=False)
    def test_flag_off_hides_ai_admin_rows_but_keeps_proposal_business_rows(self):
        # Duy 08/10 câu 2: ai_config_*, ai_policy_*, downgrade_* ẩn; dòng nghiệp vụ người duyệt giữ.
        for action in ("ai_config_update", "ai_config_kill", "ai_policy_update", "downgrade_cancel_order"):
            record_audit(action, note="admin-ai")
        record_audit("cancel_order", actor=User.objects.create_user("actor_fake"), note="giữ", proposal_ref="P-9")
        notes = set(exclude_ai_audit_rows(AuditLog.objects.all()).values_list("note", flat=True))
        self.assertNotIn("admin-ai", notes)
        self.assertIn("giữ", notes)

    @override_settings(AI_ENABLED=True)
    def test_flag_on_still_shows_ai_admin_rows(self):
        record_audit("ai_policy_update", note="admin-ai")
        self.assertTrue(exclude_ai_audit_rows(AuditLog.objects.filter(action="ai_policy_update")).exists())

    @override_settings(AI_ENABLED=True)
    def test_flag_on_keeps_everything(self):
        self.assertTrue(ai_features_enabled())
        self.assertEqual(exclude_ai_audit_rows(AuditLog.objects.all()).count(), 4)

    @override_settings(AI_ENABLED=False)
    def test_append_only_rows_still_in_db(self):
        exclude_ai_audit_rows(AuditLog.objects.all()).count()
        self.assertEqual(AuditLog.objects.count(), 4)
