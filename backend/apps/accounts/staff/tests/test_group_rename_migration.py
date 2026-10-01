"""
P8b Lô 4a (R2 Critical): migration `accounts/0013_rename_groups_to_english` đổi tên 5 Group GIỮ ID.

Gọi thẳng hàm của migration trên model thật của DB test (5 Group đã seed bởi các migration trước, đúng tập quyền đang có),
để chứng minh quyền đi theo id: id, tập quyền của từng Group và thành viên của từng user giống hệt trước/sau.
`nv_kho` không có `sales.view_customer` (0012, SR-PII-01) thì sau đổi tên cũng không có.
Thứ tự chạy trên DB mới kiểm bằng đồ thị migration; chạy migrate/rollback thật trên DB sạch là bước kiểm riêng khi nghiệm thu.

Bất biến 9: chỉ dùng username giả, không in và không ghi dữ liệu người dùng.
"""
import importlib

from django.apps import apps as global_apps
from django.contrib.auth.models import Group, User
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase

from apps.accounts import roles

migration = importlib.import_module("apps.accounts.migrations.0013_rename_groups_to_english")

ACCOUNTS_BEFORE = ("accounts", "0012_revoke_customer_view_warehouse_staff")
ACCOUNTS_AFTER = ("accounts", "0013_rename_groups_to_english")

# Tên cũ nằm trong test này có chủ đích: đây là dữ liệu trước migration.
RENAMES = (
    ("chu", roles.OWNER),  # naming: allow - tên Group cũ, dữ liệu trước migration
    ("quan_ly", roles.MANAGER),  # naming: allow - tên Group cũ, dữ liệu trước migration
    ("nv_kho", roles.WAREHOUSE_STAFF),  # naming: allow - tên Group cũ, dữ liệu trước migration
    ("nv_giao", roles.DELIVERY_STAFF),  # naming: allow - tên Group cũ, dữ liệu trước migration
    ("cskh", roles.CUSTOMER_SERVICE),  # naming: allow - tên Group cũ, dữ liệu trước migration
)
OLD_NAMES = [old for old, _ in RENAMES]
NEW_NAMES = [new for _, new in RENAMES]


def _snapshot():
    """Trạng thái theo id Group: {id: (name, perms)} và thành viên theo username."""
    groups = {
        group.pk: (group.name, sorted(group.permissions.values_list("content_type__app_label", "codename")))
        for group in Group.objects.all()
    }
    members = {user.username: sorted(user.groups.values_list("pk", flat=True)) for user in User.objects.all()}
    return groups, members


class GroupRenameMigrationTests(TestCase):
    def setUp(self):
        # Trạng thái "trước migration": 5 Group tên cũ, giữ nguyên id và tập quyền đã seed.
        for old, new in RENAMES:
            Group.objects.filter(name=new).update(name=old)
        self.assertEqual(sorted(Group.objects.values_list("name", flat=True)), sorted(OLD_NAMES))
        for index, (old, _new) in enumerate(RENAMES):
            User.objects.create(username=f"migration_user_{index}").groups.add(Group.objects.get(name=old))
        multi = User.objects.create(username="migration_user_multi")
        multi.groups.set(Group.objects.filter(name__in=["quan_ly", "nv_kho"]))  # naming: allow - tên Group cũ

    def _forward(self):
        migration.rename_groups_forward(global_apps, None)

    def _backward(self):
        migration.rename_groups_backward(global_apps, None)

    def _perm_names(self, group_name):
        group = Group.objects.get(name=group_name)
        return {f"{app}.{codename}" for app, codename in group.permissions.values_list("content_type__app_label", "codename")}

    def test_rename_keeps_group_ids_permissions_and_memberships(self):
        before_groups, before_members = _snapshot()

        self._forward()

        after_groups, after_members = _snapshot()
        self.assertEqual(set(after_groups), set(before_groups), "id Group không đổi, không xoá/tạo lại")
        mapping = dict(RENAMES)
        for group_id, (old_name, perms) in before_groups.items():
            new_name, new_perms = after_groups[group_id]
            self.assertEqual(new_name, mapping[old_name])
            self.assertEqual(new_perms, perms, f"tập quyền của {new_name} phải giống hệt trước đổi tên")
        self.assertEqual(after_members, before_members, "thành viên từng user giống hệt")
        self.assertEqual(sorted(Group.objects.values_list("name", flat=True)), sorted(NEW_NAMES))

    def test_groups_carry_real_permissions_so_the_comparison_is_not_vacuous(self):
        self.assertTrue(self._perm_names("chu"))  # naming: allow - tên Group cũ
        self.assertTrue(self._perm_names("nv_kho"))  # naming: allow - tên Group cũ

    def test_warehouse_staff_still_lacks_customer_book_permission_and_others_keep_it(self):
        self.assertNotIn("sales.view_customer", self._perm_names("nv_kho"))  # naming: allow - tên Group cũ
        self._forward()
        self.assertNotIn("sales.view_customer", self._perm_names(roles.WAREHOUSE_STAFF))
        for name in (roles.DELIVERY_STAFF, roles.OWNER, roles.MANAGER):
            self.assertIn("sales.view_customer", self._perm_names(name), name)
        self.assertNotIn("sales.view_customer", self._perm_names(roles.CUSTOMER_SERVICE))

    def test_reverse_restores_old_names_with_same_ids_and_permissions(self):
        before_groups, before_members = _snapshot()
        self._forward()
        self._backward()

        after_groups, after_members = _snapshot()
        self.assertEqual(after_groups, before_groups)
        self.assertEqual(after_members, before_members)
        self.assertNotIn("sales.view_customer", self._perm_names("nv_kho"))  # naming: allow - tên Group cũ

        self._forward()  # tiến lại sau khi lùi vẫn đúng
        self.assertNotIn("sales.view_customer", self._perm_names(roles.WAREHOUSE_STAFF))
        self.assertEqual(sorted(Group.objects.values_list("name", flat=True)), sorted(NEW_NAMES))

    def test_running_the_data_step_twice_changes_nothing(self):
        self._forward()
        first = _snapshot()
        self._forward()
        self._forward()
        self.assertEqual(_snapshot(), first)

    def test_stops_when_old_and_new_name_both_exist_and_changes_nothing(self):
        Group.objects.create(name=roles.OWNER)  # có cả `chu` lẫn `owner`
        before = _snapshot()
        with self.assertRaises(RuntimeError):
            self._forward()
        self.assertEqual(_snapshot(), before, "kiểm xung đột trước khi đổi bất kỳ Group nào")

    def test_skips_when_no_old_group_exists(self):
        Group.objects.all().delete()
        self._forward()
        self.assertEqual(Group.objects.count(), 0)

    def test_output_contains_only_counts(self):
        import io
        from contextlib import redirect_stdout

        out = io.StringIO()
        with redirect_stdout(out):
            self._forward()
        self.assertRegex(out.getvalue(), r"5")
        self.assertNotIn("migration_user", out.getvalue())


def _migrations_mentioning_old_group_names():
    """(app_label, tên migration) của mọi migration trong `apps/*/migrations` có chuỗi tên Group cũ, trừ hai migration đổi tên."""
    import re
    from pathlib import Path

    pattern = re.compile(r"""["'](%s)["']""" % "|".join(old for old, _ in RENAMES))
    skip = {ACCOUNTS_AFTER, ("ai", "0003_rename_ai_keys_to_english")}
    found = set()
    for path in Path(__file__).resolve().parents[3].glob("*/migrations/0*.py"):
        node = (path.parents[1].name, path.stem)
        if node in skip:
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            found.add(node)
    return sorted(found)


class GroupRenameMigrationOrderTests(SimpleTestCase):
    def test_every_group_seed_by_old_name_runs_before_the_rename_on_a_fresh_database(self):
        graph = MigrationLoader(None, ignore_no_migrations=True).graph  # không đụng DB
        plan = graph.forwards_plan(ACCOUNTS_AFTER)
        self.assertIn(ACCOUNTS_BEFORE, plan)
        # Quét MỌI migration có nhắc tên Group cũ (không dùng danh sách cứng): migration nào gán/thu quyền theo tên cũ
        # đều phải chạy trước khi đổi tên (D1). Chỉ loại chính hai migration đổi tên.
        for node in _migrations_mentioning_old_group_names():
            self.assertIn(node, plan, f"{node} nhắc tên Group cũ nên phải là tiền đề của {ACCOUNTS_AFTER}")
        self.assertGreaterEqual(len(_migrations_mentioning_old_group_names()), 6, "bộ quét phải thấy các migration seed/cấp quyền")
        full_plan = graph.forwards_plan(("ai", "0003_rename_ai_keys_to_english"))
        self.assertLess(full_plan.index(("ai", "0002_grant_manage_ai_policy")), full_plan.index(ACCOUNTS_AFTER))
        self.assertLess(full_plan.index(ACCOUNTS_AFTER), full_plan.index(("ai", "0003_rename_ai_keys_to_english")))
