"""
P8b Lô 4a (R2/R5): migration `ai/0003_rename_ai_keys_to_english`.

- `AiAction.assignee_group` và `AiAction.command` đổi sang khoá mới (đây là dữ liệu vận hành, được UPDATE).
- `AiConfigVersion` / `AiPolicyVersion` là append-only: KHÔNG sửa dòng cũ, chỉ THÊM phiên bản mới mang khoá tiếng Anh,
  giá trị giữ nguyên, ghi chú "P8b: đổi khoá sang tiếng Anh, giá trị giữ nguyên".
- Chạy lại không làm gì thêm; reverse thêm phiên bản mang khoá cũ (vẫn không sửa/xoá dòng nào).

Test gọi thẳng hàm của migration trên model thật (đủ để kiểm hành vi dữ liệu); thứ tự phụ thuộc kiểm ở
`test_group_rename_migration`.
"""
import importlib
import io
from contextlib import redirect_stdout

from django.apps import apps as global_apps
from django.test import TestCase

from apps.accounts import roles
from apps.ai.models import AiAction
from apps.ai.models.config import AiConfigVersion
from apps.ai.models.policy import AiPolicyVersion
from apps.common.tests.fixtures import make_user

migration = importlib.import_module("apps.ai.migrations.0003_rename_ai_keys_to_english")

OLD_ID = "purchasing.purchasereceipt.nhap_lo"  # naming: allow - id lệnh cũ, dữ liệu trước Lô 4
NEW_ID = "purchasing.purchasereceipt.receive_batches"
NOTE = "P8b: đổi khoá sang tiếng Anh, giá trị giữ nguyên"


def _run(func):
    out = io.StringIO()
    with redirect_stdout(out):
        func(global_apps, None)
    return out.getvalue()


class AiKeyRenameMigrationTests(TestCase):
    def setUp(self):
        self.owner = make_user("ai_mig_owner", roles.OWNER)
        self.staff = make_user("ai_mig_staff", roles.WAREHOUSE_STAFF)

    def _old_config(self, user, version=1, **extra):
        data = dict(
            group_levels={"thu_mua": {"read": "A", "write": "OFF"}, "cskh": {"write": "C"}},  # naming: allow - khoá cũ
            overrides={OLD_ID: "OFF", "inventory.batch.list": "A"},
            limits={OLD_ID: {"kg": "100", "vnd": "5000000"}},
        )
        data.update(extra)
        return AiConfigVersion.objects.create(user=user, version=version, created_by=user, **data)

    def _action(self, **kwargs):
        defaults = dict(command=OLD_ID, kind="write", level="C", owner=self.owner, assignee_group="chu")  # naming: allow - tên Group cũ
        defaults.update(kwargs)
        return AiAction.objects.create(**defaults)

    def test_ai_actions_command_and_assignee_group_renamed(self):
        escalated = self._action(assignee_group="chu", status="ESCALATED")  # naming: allow - tên Group cũ
        by_manager = self._action(assignee_group="quan_ly")  # naming: allow - tên Group cũ
        no_group = self._action(assignee_group="", command="inventory.batch.list", kind="read", level="A")

        _run(migration.rename_ai_keys_forward)

        for row in (escalated, by_manager, no_group):
            row.refresh_from_db()
        self.assertEqual((escalated.command, escalated.assignee_group), (NEW_ID, roles.OWNER))
        self.assertEqual(by_manager.assignee_group, roles.MANAGER)
        self.assertEqual((no_group.command, no_group.assignee_group), ("inventory.batch.list", ""))

    def test_printed_action_count_is_rows_not_field_changes(self):
        """Một việc đổi cả lệnh lẫn nhóm nhận việc chỉ tính MỘT dòng (không đếm trùng)."""
        self._action(assignee_group="chu")  # naming: allow - tên Group cũ
        self._action(assignee_group="")
        output = _run(migration.rename_ai_keys_forward)
        self.assertIn("2 việc AI", output)

    def test_config_versions_are_appended_not_updated(self):
        original = self._old_config(self.staff)
        before = AiConfigVersion.objects.filter(pk=original.pk).values().get()

        _run(migration.rename_ai_keys_forward)

        self.assertEqual(AiConfigVersion.objects.filter(pk=original.pk).values().get(), before, "dòng cũ không đổi")
        latest = AiConfigVersion.objects.filter(user=self.staff).order_by("-version").first()
        self.assertEqual(latest.version, 2)
        self.assertEqual(latest.note, NOTE)
        self.assertEqual(latest.created_by_id, self.staff.pk)
        self.assertEqual(
            latest.group_levels, {"purchasing": {"read": "A", "write": "OFF"}, "customer_service": {"write": "C"}}
        )
        self.assertEqual(latest.overrides, {NEW_ID: "OFF", "inventory.batch.list": "A"})
        self.assertEqual(latest.limits, {NEW_ID: {"kg": "100", "vnd": "5000000"}})
        self.assertEqual(latest.killed, original.killed)

    def test_killed_flag_is_carried_over(self):
        self._old_config(self.staff, killed=True)
        _run(migration.rename_ai_keys_forward)
        self.assertTrue(AiConfigVersion.objects.filter(user=self.staff).order_by("-version").first().killed)

    def test_only_latest_version_per_user_is_considered(self):
        self._old_config(self.staff, version=1)
        self._old_config(self.staff, version=2)
        _run(migration.rename_ai_keys_forward)
        self.assertEqual(AiConfigVersion.objects.filter(user=self.staff).count(), 3)
        self.assertEqual(AiConfigVersion.objects.filter(user=self.staff, note=NOTE).get().version, 3)

    def test_user_without_old_keys_gets_no_new_version(self):
        AiConfigVersion.objects.create(
            user=self.staff, version=1, created_by=self.staff,
            group_levels={"purchasing": {"read": "A"}}, overrides={NEW_ID: "OFF"}, limits={},
        )
        AiConfigVersion.objects.create(user=self.owner, version=1, created_by=self.owner)
        _run(migration.rename_ai_keys_forward)
        self.assertEqual(AiConfigVersion.objects.count(), 2)

    def test_policy_caps_renamed_by_appending_a_version(self):
        old = AiPolicyVersion.objects.create(
            version=1, created_by=self.owner, global_mode="c_only", red_zone_open={"inventory.close_batch": False},
            caps={OLD_ID: {"kg": 200, "vnd": 1000, "daily": 3}, "inventory.batch.close": {"max_level": "C"}},
        )
        _run(migration.rename_ai_keys_forward)
        self.assertEqual(AiPolicyVersion.objects.get(pk=old.pk).caps[OLD_ID]["kg"], 200, "dòng cũ nguyên vẹn")
        latest = AiPolicyVersion.objects.order_by("-version").first()
        self.assertEqual(latest.version, 2)
        self.assertEqual(latest.note, NOTE)
        self.assertEqual(latest.global_mode, "c_only")
        self.assertEqual(latest.red_zone_open, {"inventory.close_batch": False})
        self.assertEqual(
            latest.caps, {NEW_ID: {"kg": 200, "vnd": 1000, "daily": 3}, "inventory.batch.close": {"max_level": "C"}}
        )

    def test_second_run_adds_nothing(self):
        self._old_config(self.staff)
        AiPolicyVersion.objects.create(version=1, created_by=self.owner, caps={OLD_ID: {"kg": 1}})
        self._action()
        _run(migration.rename_ai_keys_forward)
        counts = (AiConfigVersion.objects.count(), AiPolicyVersion.objects.count())
        _run(migration.rename_ai_keys_forward)
        self.assertEqual((AiConfigVersion.objects.count(), AiPolicyVersion.objects.count()), counts)

    def test_empty_database_is_a_no_op(self):
        AiAction.objects.all().delete()
        AiConfigVersion.objects.all().delete()
        AiPolicyVersion.objects.all().delete()
        self.assertEqual(_run(migration.rename_ai_keys_forward), "")

    def test_output_contains_counts_only_and_no_user_data(self):
        self._old_config(self.staff)
        self._action()
        output = _run(migration.rename_ai_keys_forward)
        self.assertNotIn("ai_mig_staff", output)
        self.assertNotIn("ai_mig_owner", output)
        self.assertRegex(output, r"\d")

    def test_reverse_restores_old_keys_by_appending_and_old_action_values(self):
        self._old_config(self.staff)
        AiPolicyVersion.objects.create(version=1, created_by=self.owner, caps={OLD_ID: {"kg": 9}})
        action = self._action()
        _run(migration.rename_ai_keys_forward)

        _run(migration.rename_ai_keys_backward)

        action.refresh_from_db()
        self.assertEqual((action.command, action.assignee_group), (OLD_ID, "chu"))  # naming: allow - giá trị cũ
        latest_cfg = AiConfigVersion.objects.filter(user=self.staff).order_by("-version").first()
        self.assertEqual(latest_cfg.version, 3, "reverse thêm phiên bản, không xoá/sửa")
        self.assertIn(OLD_ID, latest_cfg.overrides)
        self.assertIn("thu_mua", latest_cfg.group_levels)  # naming: allow - khoá cũ
        latest_policy = AiPolicyVersion.objects.order_by("-version").first()
        self.assertEqual(latest_policy.version, 3)
        self.assertEqual(latest_policy.caps, {OLD_ID: {"kg": 9}})
