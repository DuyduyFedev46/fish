"""
S41-AC8 — Django Admin User/Group · BR-PQ-04, BR-PQ-17.

Superuser đổi nhóm trong Admin vẫn ghi AuditLog `staff_groups_change` (trước → sau). Người không
phải superuser (kể cả Chủ có `auth.change_user`) không mở được trang User/Group trong Admin — nếu
không, Chủ tự bật `is_superuser` cho mình hoặc sửa quyền của Group là cửa sau chống BR-PQ-17.
Ô chọn người (autocomplete) trong form khác vẫn chạy.
"""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .helpers import audits, group_names, make_user, staff_user
from apps.accounts import roles


def admin_staff(username, *groups):
    user = make_user(username, *groups)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return User.objects.get(pk=user.pk)


class S41AdminTests(TestCase):
    def setUp(self):
        self.kho1 = staff_user("kho1", roles.WAREHOUSE_STAFF)
        self.root = User.objects.create_superuser("root", password="x")

    def user_form(self, user, groups, **extra):
        data = {
            "username": user.username,
            "first_name": "", "last_name": "", "email": "",
            "is_active": "on",
            "groups": [str(Group.objects.get(name=g).pk) for g in groups],
            "date_joined_0": user.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": user.date_joined.strftime("%H:%M:%S"),
        }
        data.update(extra)
        return data

    def test_s41_ac8_superuser_doi_nhom_trong_admin_ghi_audit(self):
        self.client.force_login(self.root)
        url = reverse("admin:auth_user_change", args=[self.kho1.pk])
        resp = self.client.post(url, self.user_form(self.kho1, [roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF]))
        self.assertEqual(resp.status_code, 302, resp.content[:2000])
        self.assertEqual(group_names(self.kho1), [roles.DELIVERY_STAFF, roles.WAREHOUSE_STAFF])
        log = audits("staff_groups_change").get()
        self.assertEqual(log.actor, self.root)
        self.assertEqual(log.object_id, str(self.kho1.pk))
        self.assertEqual(log.changes, {"groups": {"from": [roles.WAREHOUSE_STAFF], "to": [roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF]}})

    def test_s41_ac8_superuser_luu_khong_doi_nhom_khong_ghi_audit(self):
        self.client.force_login(self.root)
        url = reverse("admin:auth_user_change", args=[self.kho1.pk])
        resp = self.client.post(url, self.user_form(self.kho1, [roles.WAREHOUSE_STAFF], first_name="Tâm"))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(audits("staff_groups_change").exists())

    def test_s41_ac8_chu_khong_superuser_khong_mo_duoc_user_group_trong_admin(self):
        chu = admin_staff("loc", roles.OWNER)
        self.client.force_login(chu)
        chu_group = Group.objects.get(name=roles.OWNER)
        for url in (
            reverse("admin:auth_user_changelist"),
            reverse("admin:auth_user_change", args=[self.kho1.pk]),
            reverse("admin:auth_user_change", args=[chu.pk]),
            reverse("admin:auth_user_add"),
            reverse("admin:auth_group_changelist"),
            reverse("admin:auth_group_change", args=[chu_group.pk]),
        ):
            self.assertIn(self.client.get(url).status_code, (403, 302), url)
        resp = self.client.post(
            reverse("admin:auth_user_change", args=[chu.pk]),
            self.user_form(chu, [roles.OWNER], is_superuser="on", is_staff="on"),
        )
        self.assertEqual(resp.status_code, 403)
        chu.refresh_from_db()
        self.assertFalse(chu.is_superuser)
        self.assertNotIn(b"auth/user/", self.client.get(reverse("admin:index")).content)

    def test_s41_ac8_chu_van_dung_o_chon_nguoi_autocomplete(self):
        chu = admin_staff("loc", roles.OWNER)
        self.client.force_login(chu)
        resp = self.client.get(
            reverse("admin:autocomplete"),
            {"app_label": "accounts", "model_name": "staffprofile", "field_name": "user",
             "term": "kho"},
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("kho1", resp.content.decode())
