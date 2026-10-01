"""
P8b Lô 4a (R6): việc AI hẹn giờ tạo bằng id lệnh và nhóm nhận việc CŨ, sau khi chạy migration `ai/0003` thì
`run_due_ai_actions` vẫn tìm đúng lệnh mới, tính đúng mức từ cấu hình ghim khoá cũ và thực thi (không bị hạ về C
vì "lệnh không còn tồn tại").
"""
import datetime
import importlib
import io
import unittest.mock

from django.apps import apps as global_apps
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts import roles
from apps.ai.execution.dispatch import DispatchResult
from apps.ai.models import AiAction, AiConfigVersion
from apps.ai.registry.discovery import get_registry
from apps.common.tests.fixtures import make_user

migration = importlib.import_module("apps.ai.migrations.0003_rename_ai_keys_to_english")

OLD_ID = "purchasing.purchasereceipt.nhap_lo"  # naming: allow - id lệnh cũ, dữ liệu trước migration
NEW_ID = "purchasing.purchasereceipt.receive_batches"


@override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="B")
class ScheduledActionCreatedWithOldIdTests(TestCase):
    def setUp(self):
        self.warehouse = make_user("rename_job_kho", roles.WAREHOUSE_STAFF)
        get_registry().build(force=True)
        # Cấu hình ghim khoá CŨ (đúng như dữ liệu trước Lô 4).
        AiConfigVersion.objects.create(
            user=self.warehouse, version=1, created_by=self.warehouse,
            group_levels={"thu_mua": {"read": "A", "write": "B"}},  # naming: allow - khoá cũ
            overrides={OLD_ID: "B"},
        )
        self.action = AiAction.objects.create(
            command=OLD_ID, kind=AiAction.Kind.WRITE, status=AiAction.Status.SCHEDULED, level=AiAction.Level.B,
            owner=self.warehouse, assignee_group="nv_kho",  # naming: allow - tên Group cũ
            execute_after=timezone.now() - datetime.timedelta(minutes=1),
            undo_until=timezone.now() - datetime.timedelta(minutes=1),
            args={"note": "created_before_p8b"},
        )

    def _run_job(self):
        with unittest.mock.patch("apps.ai.management.commands.run_due_ai_actions.dispatch_command") as dispatch:
            dispatch.return_value = DispatchResult({"id": 1}, status_code=200, is_error=False)
            call_command("run_due_ai_actions", stdout=io.StringIO())
        return dispatch

    def test_job_after_migration_executes_the_renamed_command(self):
        migration.rename_ai_keys_forward(global_apps, None)
        self.action.refresh_from_db()
        self.assertEqual(self.action.command, NEW_ID)
        dispatch = self._run_job()
        dispatch.assert_called_once()
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, AiAction.Status.DONE)

    def test_job_after_migration_still_reads_the_old_pinned_config(self):
        """Phiên bản cũ (khoá `thu_mua`/id cũ) không bị mất tác dụng: nếu tắt (OFF) thì vẫn bị hạ, không nới mức."""
        AiConfigVersion.objects.filter(user=self.warehouse).update(overrides={OLD_ID: "OFF"})  # dựng dữ liệu cũ
        migration.rename_ai_keys_forward(global_apps, None)
        dispatch = self._run_job()
        dispatch.assert_not_called()
        self.action.refresh_from_db()
        self.assertNotEqual(self.action.status, AiAction.Status.DONE)
