"""P8b Lô 4: `preview_group_rename` chỉ đọc và chỉ in số lượng (bất biến 9: không tên đăng nhập, họ tên, SĐT)."""
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.models import StaffProfile
from apps.ai.models import AiAction
from apps.ai.models.config import AiConfigVersion
from apps.common.tests.fixtures import make_user


def _run():
    out = StringIO()
    call_command("preview_group_rename", stdout=out)
    return out.getvalue()


class PreviewGroupRenameTests(TestCase):
    def test_reports_counts_per_role_without_personal_data(self):
        user = make_user("preview_user_xyz", roles.WAREHOUSE_STAFF)
        StaffProfile.objects.create(user=user, phone="0900000099", display_name="Người Thử Nghiệm")
        output = _run()
        self.assertIn(f"{roles.WAREHOUSE_STAFF}: id=", output)
        self.assertIn("1 thành viên", output)
        for secret in ("preview_user_xyz", "0900000099", "Người Thử Nghiệm"):
            self.assertNotIn(secret, output)

    def test_reports_legacy_ai_rows_and_conflicts(self):
        owner = make_user("preview_owner", roles.OWNER)
        AiAction.objects.create(
            command="purchasing.purchasereceipt.nhap_lo", kind="write", level="C", owner=owner, assignee_group="chu"  # naming: allow - dữ liệu cũ
        )
        AiConfigVersion.objects.create(
            user=owner, version=1, created_by=owner, group_levels={"thu_mua": {"read": "A"}}  # naming: allow - khoá cũ
        )
        Group.objects.create(name="chu")  # naming: allow - dựng xung đột có chủ đích
        output = _run()
        self.assertIn("việc AI còn mã lệnh cũ: 1", output)
        self.assertIn("nhóm nhận việc tên cũ: 1", output)
        self.assertIn("còn khoá cũ (sẽ thêm phiên bản mới): 1", output)
        self.assertIn("XUNG ĐỘT", output)
        self.assertIn("Xung đột: 1", output)

    def test_reports_unknown_groups_as_a_stop_point(self):
        """02c: có Group lạ (ngoài 5 tên cũ và 5 tên mới) thì báo số lượng để người chạy dừng lại xem."""
        Group.objects.create(name="extra_role_for_test")
        Group.objects.create(name="another_role_for_test")
        output = _run()
        self.assertIn("Group lạ (ngoài 10 tên cũ và mới): 2", output)
        self.assertNotIn("extra_role_for_test", output)

    def test_unknown_group_count_is_zero_on_a_standard_database(self):
        self.assertIn("Group lạ (ngoài 10 tên cũ và mới): 0", _run())

    def test_is_read_only(self):
        make_user("preview_ro", roles.MANAGER)
        before = (
            list(Group.objects.order_by("pk").values_list("pk", "name")),
            User.objects.count(),
            AiConfigVersion.objects.count(),
        )
        _run()
        after = (
            list(Group.objects.order_by("pk").values_list("pk", "name")),
            User.objects.count(),
            AiConfigVersion.objects.count(),
        )
        self.assertEqual(before, after)
