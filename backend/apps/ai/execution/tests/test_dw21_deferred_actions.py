"""
Kiểm thử toàn diện cho Story DW-21: Trì hoãn ghi (undo="defer") + Job chạy việc tới hạn.
Bao phủ các tiêu chí DW-21-AC1 đến DW-21-AC8.
"""
import datetime
import io
import unittest.mock
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction, AiConfigVersion
from apps.ai.registry.discovery import get_registry
from apps.ai.registry.spec import CommandSpec
from apps.common.tests.fixtures import client_for, make_user
from apps.ai import command_groups
from apps.accounts import roles


@override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="B")
class DW21DeferredActionsTestCase(TestCase):
    def setUp(self):
        self.user_chu = make_user("chu_dw21", roles.OWNER)
        self.user_kho = make_user("kho_dw21", roles.WAREHOUSE_STAFF)
        self.client_kho = client_for(self.user_kho)

        # Cấu hình AI mức B cho user_kho
        self.config_kho = AiConfigVersion.objects.create(
            user=self.user_kho,
            version=1,
            group_levels={command_groups.PURCHASING: {"read": "A", "write": "B"}},
            overrides={"test.deferred.command": "B"},
            created_by=self.user_kho,
        )

        # Đăng ký lệnh thử nghiệm có undo="defer" vào registry
        self.test_spec = CommandSpec(
            id="test.deferred.command",
            title="Lệnh thử nghiệm trì hoãn ghi",
            kind="write",
            group=command_groups.PURCHASING,
            method="POST",
            path="/api/purchasing/receipts/receive-batches/",
            action="receive_batches",
            max_level="B",
            undo="defer",
            required_perms=("purchasing.add_purchasereceipt", "purchasing.change_purchasereceipt"),
        )
        registry = get_registry()
        registry._specs[self.test_spec.id] = self.test_spec

    def test_dw21_ac1_deferred_command_call_creates_scheduled_action(self):
        """DW-21-AC1: Lệnh undo=defer ở mức B -> outcome=scheduled, execute_after=+10m, chứng từ chưa đổi."""
        url = f"/api/ai/commands/{self.test_spec.id}/call/"
        payload = {"args": {"note": "test_schedule"}}

        res = self.client_kho.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["outcome"], "scheduled")
        self.assertEqual(res.data["level"], "B")
        self.assertIn("action_id", res.data)
        self.assertIn("execute_after", res.data)
        self.assertIn("undo_until", res.data)

        # Kiểm tra AiAction trong DB có status SCHEDULED
        action = AiAction.objects.get(id=res.data["action_id"])
        self.assertEqual(action.status, AiAction.Status.SCHEDULED)
        self.assertIsNotNone(action.execute_after)

        # AuditLog ghi nhận schedule
        audit = AuditLog.objects.filter(action=f"schedule_{self.test_spec.id}").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor_kind, "ai")
        self.assertEqual(audit.ai_level, "B")

    def test_dw21_ac2_job_executes_due_scheduled_actions(self):
        """DW-21-AC2: Tới hạn, job chạy kiểm tra bước 2-7 -> gọi view, AiAction DONE, AuditLog ghi nhận."""
        action = AiAction.objects.create(
            command=self.test_spec.id,
            kind=AiAction.Kind.WRITE,
            status=AiAction.Status.SCHEDULED,
            level=AiAction.Level.B,
            owner=self.user_kho,
            execute_after=timezone.now() - datetime.timedelta(minutes=1),
            undo_until=timezone.now() - datetime.timedelta(minutes=1),
            args={"note": "ready_to_run"},
        )

        with unittest.mock.patch("apps.ai.management.commands.run_due_ai_actions.dispatch_command") as mock_dispatch:
            from apps.ai.execution.dispatch import DispatchResult
            mock_dispatch.return_value = DispatchResult({"id": 999, "status": "OK"}, status_code=200, is_error=False)

            out = io.StringIO()
            call_command("run_due_ai_actions", stdout=out)

            mock_dispatch.assert_called_once()
            action.refresh_from_db()
            self.assertEqual(action.status, AiAction.Status.DONE)
            self.assertIsNotNone(action.executed_at)

            audit = AuditLog.objects.filter(action=f"execute_{self.test_spec.id}").first()
            self.assertIsNotNone(audit)
            self.assertEqual(audit.actor_kind, "ai")
            self.assertEqual(audit.ai_actor, self.user_kho)

    def test_dw21_ac3_job_revokes_scheduled_action_if_conditions_changed(self):
        """DW-21-AC3: Cấu hình về C, hoặc tắt khẩn, hoặc mất quyền -> job hạ về C (PENDING)."""
        action = AiAction.objects.create(
            command=self.test_spec.id,
            kind=AiAction.Kind.WRITE,
            status=AiAction.Status.SCHEDULED,
            level=AiAction.Level.B,
            owner=self.user_kho,
            execute_after=timezone.now() - datetime.timedelta(minutes=1),
            args={},
        )

        # Người dùng bị tắt khẩn AI
        AiConfigVersion.objects.create(
            user=self.user_kho,
            version=2,
            killed=True,
            created_by=self.user_kho,
        )

        with unittest.mock.patch("apps.ai.management.commands.run_due_ai_actions.dispatch_command") as mock_dispatch:
            call_command("run_due_ai_actions")
            mock_dispatch.assert_not_called()

        action.refresh_from_db()
        self.assertEqual(action.status, AiAction.Status.PENDING)
        self.assertEqual(action.level, AiAction.Level.C)
        self.assertEqual(action.downgrade_reason["code"], "AI_LEVEL_REVOKED")

    def test_dw21_ac4_user_cancels_scheduled_action_within_window(self):
        """DW-21-AC4: Bấm huỷ lịch trong cửa sổ -> AiAction CANCELLED, chứng từ không đổi."""
        action = AiAction.objects.create(
            command=self.test_spec.id,
            kind=AiAction.Kind.WRITE,
            status=AiAction.Status.SCHEDULED,
            level=AiAction.Level.B,
            owner=self.user_kho,
            undo_until=timezone.now() + datetime.timedelta(minutes=5),
            args={},
        )

        url_undo = f"/api/ai/actions/{action.id}/undo/"
        res = self.client_kho.post(url_undo, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["outcome"], "cancelled")

        action.refresh_from_db()
        self.assertEqual(action.status, AiAction.Status.CANCELLED)
        self.assertEqual(action.decided_by, self.user_kho)

        audit = AuditLog.objects.filter(action=f"cancel_schedule_{self.test_spec.id}").first()
        self.assertIsNotNone(audit)

    def test_dw21_ac5_job_is_idempotent_with_select_for_update_skip_locked(self):
        """DW-21-AC5: Chạy job 2 lần -> view chỉ được gọi đúng 1 lần duy nhất."""
        action = AiAction.objects.create(
            command=self.test_spec.id,
            kind=AiAction.Kind.WRITE,
            status=AiAction.Status.SCHEDULED,
            level=AiAction.Level.B,
            owner=self.user_kho,
            execute_after=timezone.now() - datetime.timedelta(minutes=1),
            args={},
        )

        with unittest.mock.patch("apps.ai.management.commands.run_due_ai_actions.dispatch_command") as mock_dispatch:
            from apps.ai.execution.dispatch import DispatchResult
            mock_dispatch.return_value = DispatchResult({"id": 1}, status_code=200, is_error=False)

            # Lần 1
            call_command("run_due_ai_actions")
            self.assertEqual(mock_dispatch.call_count, 1)

            # Lần 2 (ngay sau khi xong)
            call_command("run_due_ai_actions")
            self.assertEqual(mock_dispatch.call_count, 1)

    def test_dw21_ac6_no_http_path_to_force_auth_user(self):
        """DW-21-AC6: Không có đường HTTP nào để inject _force_auth_user."""
        url = f"/api/ai/commands/{self.test_spec.id}/call/"
        payload = {
            "args": {},
            "_force_auth_user": self.user_chu.id,
            "force_user": self.user_chu.username,
        }
        res = self.client_kho.post(url, payload, format="json", HTTP_X_FORCE_USER="chu_dw21")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        action = AiAction.objects.get(id=res.data["action_id"])
        # Action vẫn chỉ thuộc về user_kho từ token
        self.assertEqual(action.owner, self.user_kho)

    def test_dw21_ac7_job_logs_only_command_and_action_id_no_pii_no_cost(self):
        """DW-21-AC7: Log của command CHỈ in id lệnh + mã action, không in PII hay giá vốn."""
        pii_name = "Khach Thu Nghiem PII"
        pii_phone = "0900000123"
        cost_val = "987654.32"

        action = AiAction.objects.create(
            command=self.test_spec.id,
            kind=AiAction.Kind.WRITE,
            status=AiAction.Status.SCHEDULED,
            level=AiAction.Level.B,
            owner=self.user_kho,
            execute_after=timezone.now() - datetime.timedelta(minutes=1),
            args={"name": pii_name, "phone": pii_phone, "rate": cost_val},
        )

        with unittest.mock.patch("apps.ai.management.commands.run_due_ai_actions.dispatch_command") as mock_dispatch:
            from apps.ai.execution.dispatch import DispatchResult
            mock_dispatch.return_value = DispatchResult({"id": 1}, status_code=200, is_error=False)

            with self.assertLogs("apps.ai.management.commands.run_due_ai_actions", level="INFO") as cm:
                call_command("run_due_ai_actions")

                log_text = " ".join(cm.output)
                self.assertIn(str(action.id), log_text)
                self.assertIn(self.test_spec.id, log_text)

                # Tuyệt đối không có PII và giá vốn trong logs
                self.assertNotIn(pii_name, log_text)
                self.assertNotIn(pii_phone, log_text)
                self.assertNotIn(cost_val, log_text)

    @override_settings(AI_ENABLED=False)
    def test_dw21_ac8_job_when_ai_disabled_downgrades_to_pending_c(self):
        """DW-21-AC8: AI_ENABLED=false lúc tới hạn -> job chuyển action SCHEDULED sang PENDING (C)."""
        action = AiAction.objects.create(
            command=self.test_spec.id,
            kind=AiAction.Kind.WRITE,
            status=AiAction.Status.SCHEDULED,
            level=AiAction.Level.B,
            owner=self.user_kho,
            execute_after=timezone.now() - datetime.timedelta(minutes=1),
            args={},
        )

        call_command("run_due_ai_actions")

        action.refresh_from_db()
        self.assertEqual(action.status, AiAction.Status.PENDING)
        self.assertEqual(action.level, AiAction.Level.C)
        self.assertEqual(action.downgrade_reason["code"], "AI_DISABLED")
