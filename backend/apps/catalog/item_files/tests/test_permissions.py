"""FISH-66 S5, S6: phân quyền nhập file Excel mặt hàng (02b §3.1, §7, §9). Dữ liệu giả."""
from django.contrib.auth.models import Permission

from apps.accounts.models import AuditLog
from apps.catalog.item_files.columns import IMPORT_PERMS

from .base import COMMIT_URL, LIMITS_URL, PREVIEW_URL, ItemFilesBase


class ImportPermissionTests(ItemFilesBase):
    def _valid_file(self):
        return self.make_xlsx_file([
            {"code": "MUC01", "name": "Mực thử", "item_group": "Cá", "is_active": True, "new_price": 150000}
        ])

    def test_s5_ac13_owner_can_access_limits_preview_and_commit(self):
        limits = self.get(self.owner, LIMITS_URL)
        self.assertEqual(limits.status_code, 200)
        self.assertEqual(
            set(limits.json().keys()),
            {"max_rows", "max_bytes", "preview_ttl_minutes"},
        )
        f = self._valid_file()
        prev = self.post_preview(self.owner, f)
        self.assertEqual(prev.status_code, 200)
        commit = self.post_commit(self.owner, f, prev.json()["preview_token"])
        self.assertEqual(commit.status_code, 200)

    def test_s5_ac13_and_s6_ac9_non_owner_roles_get_403_and_anonymous_gets_401(self):
        f = self._valid_file()
        prev = self.post_preview(self.owner, f)
        owner_token = prev.json()["preview_token"]

        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service, self.no_group):
            with self.subTest(user=user.username):
                self.assertEqual(self.get(user, LIMITS_URL).status_code, 403)
                self.assertEqual(self.post_preview(user, self._valid_file()).status_code, 403)
                self.assertEqual(self.post_commit(user, f, owner_token).status_code, 403)

        self.assertEqual(self.get(None, LIMITS_URL).status_code, 401)
        self.assertEqual(self.client_as(None).post(PREVIEW_URL, {}).status_code, 401)
        self.assertEqual(self.client_as(None).post(COMMIT_URL, {}).status_code, 401)
        self.assertFalse(AuditLog.objects.filter(action="import_items").exists())

    def test_d4_missing_any_single_import_perm_gets_403_even_if_manager_has_price_perms(self):
        perms = {}
        for perm_str in IMPORT_PERMS:
            _, codename = perm_str.split(".")
            perms[perm_str] = Permission.objects.get(content_type__app_label="catalog", codename=codename)

        # Quản lý được uỷ "Sửa giá bán" (add_itemprice + change_itemprice) vẫn 403 (S5-AC13, S6-AC9)
        self.manager.user_permissions.set([perms["catalog.add_itemprice"], perms["catalog.change_itemprice"]])
        self.manager = type(self.manager).objects.get(pk=self.manager.pk)
        self.assertEqual(self.post_preview(self.manager, self._valid_file()).status_code, 403)
        self.assertEqual(self.post_commit(self.manager, self._valid_file(), "any-token").status_code, 403)

        for missing in IMPORT_PERMS:
            with self.subTest(missing=missing):
                self.manager.user_permissions.set([p for k, p in perms.items() if k != missing])
                self.manager = type(self.manager).objects.get(pk=self.manager.pk)
                self.assertEqual(self.get(self.manager, LIMITS_URL).status_code, 403)
                self.assertEqual(self.post_preview(self.manager, self._valid_file()).status_code, 403)
                self.assertEqual(self.post_commit(self.manager, self._valid_file(), "any-token").status_code, 403)

        # Cấp đủ cả 4 quyền → gọi được cả 3 API
        self.manager.user_permissions.set(list(perms.values()))
        self.manager = type(self.manager).objects.get(pk=self.manager.pk)
        self.assertEqual(self.get(self.manager, LIMITS_URL).status_code, 200)
        f = self._valid_file()
        prev = self.post_preview(self.manager, f)
        self.assertEqual(prev.status_code, 200)
        self.assertEqual(self.post_commit(self.manager, f, prev.json()["preview_token"]).status_code, 200)

    def test_s6_ac10_owner_losing_perm_between_preview_and_commit_gets_403(self):
        f = self._valid_file()
        prev = self.post_preview(self.owner, f)
        self.assertEqual(prev.status_code, 200)
        token = prev.json()["preview_token"]

        self.owner.groups.clear()
        self.owner = type(self.owner).objects.get(pk=self.owner.pk)
        resp = self.post_commit(self.owner, f, token)
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(AuditLog.objects.filter(action="import_items").exists())


class ImportNoStoreHeaderTests(ItemFilesBase):
    def test_l1_limits_preview_commit_responses_have_cache_control_no_store(self):
        limits = self.get(self.owner, LIMITS_URL)
        self.assertEqual(limits["Cache-Control"], "no-store")
        f = self.make_xlsx_file([
            {"code": "MUC01", "name": "Mực thử", "item_group": "Cá", "is_active": True, "new_price": 150000}
        ])
        prev = self.post_preview(self.owner, f)
        self.assertEqual(prev.status_code, 200)
        self.assertEqual(prev["Cache-Control"], "no-store")
        commit = self.post_commit(self.owner, f, prev.json()["preview_token"])
        self.assertEqual(commit.status_code, 200)
        self.assertEqual(commit["Cache-Control"], "no-store")
        # cả đường lỗi (403, 400) cũng no-store
        self.assertEqual(self.get(self.manager, LIMITS_URL)["Cache-Control"], "no-store")
        self.assertEqual(self.post_preview(self.owner, None)["Cache-Control"], "no-store")
