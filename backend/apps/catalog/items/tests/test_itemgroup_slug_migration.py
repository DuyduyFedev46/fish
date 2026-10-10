"""SHOP-2-01 AC5 (BR-DM-01, bất biến 8): data migration slug nhóm hàng — điền, duy nhất, chạy lại được, chạy ngược được."""
import importlib

from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [("catalog", "0004_alter_item_options_alter_item_item_type_and_more")]
ADDED = [("catalog", "0005_itemgroup_slug")]
UNIQUE = [("catalog", "0007_alter_itemgroup_slug_unique")]


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    return MigrationExecutor(connection).loader.project_state(targets).apps


class ItemGroupSlugMigrationTests(TransactionTestCase):
    def tearDown(self):
        # Trả DB test về bản mới nhất cho các test sau.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_s2_01_ac5_slug_filled_unique_and_reversible(self):
        old_apps = _migrate(BEFORE)
        Group = old_apps.get_model("catalog", "ItemGroup")
        for name in ("Cá thu", "Cá Thu", "Đặc sản", "Mực", "***"):
            Group.objects.create(name=name)

        new_apps = _migrate(UNIQUE)
        slugs = dict(new_apps.get_model("catalog", "ItemGroup").objects.values_list("name", "slug"))
        self.assertEqual(
            slugs,
            {"Cá thu": "ca-thu", "Cá Thu": "ca-thu-2", "Đặc sản": "dac-san", "Mực": "muc", "***": "group"},
        )
        self.assertEqual(len(set(slugs.values())), len(slugs))

        # Cột đã khoá unique: tạo trùng phải lỗi.
        Group = new_apps.get_model("catalog", "ItemGroup")
        with self.assertRaises(IntegrityError):
            Group.objects.create(name="Khác", slug="muc")

        # Chạy ngược: về bước 0005 thì slug về null, không mất nhóm.
        back_apps = _migrate(ADDED)
        BackGroup = back_apps.get_model("catalog", "ItemGroup")
        self.assertEqual(BackGroup.objects.count(), 5)
        self.assertFalse(BackGroup.objects.exclude(slug__isnull=True).exists())

    def test_s2_01_ac5_populate_is_idempotent_and_avoids_existing_slugs(self):
        old_apps = _migrate(ADDED)
        Group = old_apps.get_model("catalog", "ItemGroup")
        Group.objects.create(name="Mực", slug="muc")          # đã có slug: giữ nguyên
        Group.objects.create(name="Muc", slug=None)           # sẽ trùng "muc" -> muc-2
        module = importlib.import_module("apps.catalog.migrations.0006_populate_itemgroup_slug")

        module.populate_slugs(old_apps, None)
        first = dict(Group.objects.values_list("name", "slug"))
        module.populate_slugs(old_apps, None)
        second = dict(Group.objects.values_list("name", "slug"))

        self.assertEqual(first, {"Mực": "muc", "Muc": "muc-2"})
        self.assertEqual(second, first)
