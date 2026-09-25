"""
Sửa lỗi QA lần 2 (2026-09-24) — phần tài khoản · BR-PQ-19.

- B4: tự đổi mật khẩu sang đúng mật khẩu hiện tại (vd mật khẩu tạm Chủ vừa đặt) → 400
  `AUTH_WEAK_PASSWORD` "Mật khẩu mới phải khác mật khẩu hiện tại.", cờ giữ nguyên.
- B3: người còn cờ `must_change_password` (is_staff) không dùng được Django Admin — trang báo
  đặt mật khẩu qua ERP; đăng xuất Admin vẫn được. Superuser không bị ép.
"""
from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts.models import StaffProfile
from apps.accounts.staff.tests.helpers import staff_user

from .test_s48_must_change_password import CHANGE, TEMP, S48Base

SAME_MSG = "Mật khẩu mới phải khác mật khẩu hiện tại."


class B4SamePasswordTests(S48Base):
    def test_b4_doi_sang_mat_khau_trung_mat_khau_tam_400_co_giu_nguyen(self):
        giao4 = self.create_giao4()
        client = self.login_client("giao4", TEMP)
        resp = client.post(CHANGE, {"old_password": TEMP, "new_password": TEMP}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "AUTH_WEAK_PASSWORD")
        self.assertEqual(resp.json()["detail"], SAME_MSG)
        self.assertTrue(StaffProfile.objects.get(user=giao4).must_change_password)
        giao4.refresh_from_db()
        self.assertTrue(giao4.check_password(TEMP))
        # Token cũ vẫn dùng được (không đổi gì).
        self.assertEqual(client.get("/api/auth/me/").status_code, 200)


class B3AdminTests(TestCase):
    def setUp(self):
        self.kho1 = staff_user("kho1", "nv_kho")
        self.kho1.is_staff = True
        self.kho1.save()

    def flag(self, user):
        StaffProfile.objects.update_or_create(user=user, defaults={"must_change_password": True})

    def test_b3_nhan_vien_con_co_khong_vao_duoc_admin(self):
        self.flag(self.kho1)
        self.client.force_login(self.kho1)
        for url in ("/admin/", "/admin/inventory/batch/", "/admin/sales/salesorder/"):
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 403)
                self.assertContains(resp, "đặt mật khẩu mới", status_code=403)
                self.assertContains(resp, "BR-PQ-19", status_code=403)

    def test_b3_nhan_vien_con_co_van_dang_xuat_admin_duoc(self):
        self.flag(self.kho1)
        self.client.force_login(self.kho1)
        resp = self.client.post("/admin/logout/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_b3_nhan_vien_khong_co_co_vao_admin_binh_thuong(self):
        self.client.force_login(self.kho1)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_b3_superuser_khong_bi_ep(self):
        root = User.objects.create_superuser("admin", password=TEMP)
        self.flag(root)
        self.client.force_login(root)
        self.assertEqual(self.client.get("/admin/").status_code, 200)


class R7AdminMiddlewarePrefixTests(TestCase):
    """R7 (code review): middleware B3 không reverse() mỗi request — prefix admin tính một lần."""

    setUp = B3AdminTests.setUp
    flag = B3AdminTests.flag

    def test_r7_khong_reverse_moi_request(self):
        from unittest import mock

        from apps.accounts.auth import middleware
        self.flag(self.kho1)
        self.client.force_login(self.kho1)
        self.client.get("/api/auth/me/")  # làm ấm cache (nếu có)
        with mock.patch.object(middleware, "reverse", wraps=middleware.reverse) as spy:
            self.assertEqual(self.client.get("/admin/").status_code, 403)
            self.assertEqual(self.client.get("/admin/sales/salesorder/").status_code, 403)
            self.assertEqual(self.client.post("/admin/logout/").status_code, 200)
            self.client.get("/api/auth/me/")
        self.assertEqual(spy.call_count, 0)
