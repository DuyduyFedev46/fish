"""PV-02-AC1 — migration `accounts/0014` (bảng) và `0015` (gieo hiện trạng). 02b §3.

Gọi thẳng hàm của migration trên model thật của DB test (5 Group đã seed bởi các migration trước, đúng tập quyền đang có).
Migrate từ DB trống và lùi/tiến bằng lệnh thật kiểm riêng khi nghiệm thu (xem 03-dev-notes.md). Dữ liệu toàn bộ là giả.
"""
import importlib

from django.apps import apps as global_apps
from django.contrib.auth.models import Group, Permission
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase

from apps.accounts import roles
from apps.accounts.data_scopes import catalog
from apps.accounts.models import GroupAccessConfig, GroupDataScope

seed = importlib.import_module("apps.accounts.migrations.0015_seed_group_data_scopes")

SEEDED_GROUPS = (roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE)


def stored(group_name):
    return dict(
        GroupDataScope.objects.filter(group__name=group_name).values_list("object_key", "value")
    )


def group_permissions():
    return {
        g.name: sorted(g.permissions.values_list("content_type__app_label", "codename"))
        for g in Group.objects.filter(name__in=roles.ALL_ROLES)
    }


class SeedAfterMigrateTests(TestCase):
    """Trạng thái DB test = kết quả chạy 0001..0015 từ DB trống."""

    def test_pv02_ac1_every_role_group_has_access_config_version_one(self):
        configs = {c.group.name: c.row_version for c in GroupAccessConfig.objects.select_related("group")}
        self.assertEqual(configs, {name: 1 for name in roles.ALL_ROLES})

    def test_pv02_ac1_owner_has_no_scope_rows(self):
        self.assertFalse(GroupDataScope.objects.filter(group__name=roles.OWNER).exists())

    def test_pv02_ac1_seeded_values_equal_catalog_defaults(self):
        keys = [obj.key for obj in catalog.stored_objects()]
        for group in SEEDED_GROUPS:
            self.assertEqual(
                stored(group), {key: catalog.BY_KEY[key].defaults[group] for key in keys}, group,
            )

    def test_pv02_ac1_values_match_contract_table(self):
        self.assertEqual(stored(roles.MANAGER), {
            "orders": "all", "deliveries": "all", "confirmation": "all_pending", "returns": "all", "receipts": "all",
            "customers": "all",
        })
        self.assertEqual(stored(roles.DELIVERY_STAFF), {
            "orders": "assigned_deliveries", "deliveries": "assigned", "confirmation": "pending_or_called_recently",
            "returns": "assigned_deliveries", "receipts": "all", "customers": "assigned_deliveries",
        })
        self.assertEqual(stored(roles.CUSTOMER_SERVICE)["orders"], "assigned_or_confirmation")
        self.assertEqual(stored(roles.WAREHOUSE_STAFF)["customers"], "none")

    def test_pv02_ac1_each_group_has_at_most_one_row_per_object(self):
        total = GroupDataScope.objects.count()
        self.assertEqual(total, len(SEEDED_GROUPS) * len(catalog.stored_objects()))

    def test_pv02_ac1_customers_scope_follows_view_customers_permission_at_migrate_time(self):
        """D7 = all với nhóm ĐANG có `sales.view_customer_list` lúc migrate; còn lại G -> assigned_deliveries, khác none."""
        perm = Permission.objects.get(content_type__app_label="sales", codename="view_customer_list")
        Group.objects.get(name=roles.CUSTOMER_SERVICE).permissions.add(perm)  # Chủ đã bật "Xem khách hàng" qua B4
        Group.objects.get(name=roles.MANAGER).permissions.remove(perm)  # và tắt cho Quản lý
        Group.objects.get(name=roles.DELIVERY_STAFF).permissions.add(perm)
        GroupDataScope.objects.filter(object_key="customers").delete()
        seed.seed_group_data_scopes(global_apps, None)
        self.assertEqual(stored(roles.CUSTOMER_SERVICE)["customers"], "all")
        self.assertEqual(stored(roles.DELIVERY_STAFF)["customers"], "all")
        self.assertEqual(stored(roles.MANAGER)["customers"], "none")
        self.assertEqual(stored(roles.WAREHOUSE_STAFF)["customers"], "none")

    def test_pv02_ac1_seed_is_idempotent_and_never_overwrites(self):
        GroupDataScope.objects.filter(group__name=roles.MANAGER, object_key="receipts").update(value="created_by_me")
        GroupAccessConfig.objects.filter(group__name=roles.MANAGER).update(row_version=7)
        before = list(GroupDataScope.objects.order_by("pk").values_list("pk", "group_id", "object_key", "value"))
        seed.seed_group_data_scopes(global_apps, None)
        seed.seed_group_data_scopes(global_apps, None)
        after = list(GroupDataScope.objects.order_by("pk").values_list("pk", "group_id", "object_key", "value"))
        self.assertEqual(before, after)
        self.assertEqual(GroupAccessConfig.objects.get(group__name=roles.MANAGER).row_version, 7)

    def test_pv02_ac1_seed_fills_only_missing_rows(self):
        GroupDataScope.objects.filter(group__name=roles.WAREHOUSE_STAFF, object_key="returns").delete()
        seed.seed_group_data_scopes(global_apps, None)
        self.assertEqual(stored(roles.WAREHOUSE_STAFF)["returns"], "all")

    def test_pv02_ac1_seed_does_not_touch_group_permissions(self):
        """Giữ nguyên quyền hiện tại của 5 nhóm (D-1, ranh giới Lô 2): migration gieo cấu hình, không đụng quyền Tầng 1/2."""
        before = group_permissions()
        seed.seed_group_data_scopes(global_apps, None)
        seed.unseed_group_data_scopes(global_apps, None)
        seed.seed_group_data_scopes(global_apps, None)
        self.assertEqual(group_permissions(), before)

    def test_pv02_ac1_reverse_removes_seeded_rows_only(self):
        seed.unseed_group_data_scopes(global_apps, None)
        self.assertEqual(GroupDataScope.objects.count(), 0)
        self.assertEqual(GroupAccessConfig.objects.count(), 0)
        seed.seed_group_data_scopes(global_apps, None)
        self.assertEqual(GroupAccessConfig.objects.count(), 5)

    def test_pv02_ac1_missing_group_is_skipped_without_error(self):
        Group.objects.filter(name=roles.CUSTOMER_SERVICE).delete()
        seed.seed_group_data_scopes(global_apps, None)
        self.assertEqual(GroupAccessConfig.objects.count(), 4)


class SeedModelConstraintTests(TestCase):
    def test_pv02_unique_group_object_key(self):
        from django.db import IntegrityError, transaction

        group = Group.objects.get(name=roles.MANAGER)
        with self.assertRaises(IntegrityError), transaction.atomic():
            GroupDataScope.objects.create(group=group, object_key="orders", value="all")

    def test_pv02_models_have_no_default_permissions(self):
        self.assertEqual(GroupDataScope._meta.default_permissions, ())
        self.assertEqual(GroupAccessConfig._meta.default_permissions, ())
        self.assertFalse(Permission.objects.filter(codename__in=[
            "add_groupdatascope", "change_groupdatascope", "view_groupaccessconfig", "change_groupaccessconfig",
        ]).exists())


class MigrationGraphTests(SimpleTestCase):
    def test_pv02_0015_depends_on_group_rename_and_customer_list_grant(self):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        key = ("accounts", "0015_seed_group_data_scopes")
        self.assertIn(key, loader.graph.nodes)
        parents = set(loader.graph.node_map[key].parents)
        flat = {p.key for p in parents}
        self.assertIn(("accounts", "0014_group_data_scopes"), flat)
        ancestors = {n for n in loader.graph.forwards_plan(key)}
        self.assertIn(("accounts", "0013_rename_groups_to_english"), ancestors)
        self.assertIn(("sales", "0013_grant_view_customer_list"), ancestors)
