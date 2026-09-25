"""
Sửa nhỏ — `POST /api/auth/token/` phải cập nhật `User.last_login` (cột "Đăng nhập gần nhất"
ở /api/staff/). Giữ nguyên path, JSON `{"token": ...}` và mã lỗi của obtain_auth_token.
"""
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.common.tests.fixtures import make_user

LOGIN = "/api/auth/token/"
PW = "Ca-ve-2026"


def login(username, password):
    return APIClient().post(LOGIN, {"username": username, "password": password}, format="json")


class LoginLastLoginTests(TestCase):
    def setUp(self):
        self.kho = make_user("kho1", "nv_kho")
        self.kho.set_password(PW)
        self.kho.save()

    def test_login_dung_set_last_login(self):
        self.assertIsNone(self.kho.last_login)
        resp = login("kho1", PW)
        self.assertEqual(resp.status_code, 200)
        self.kho.refresh_from_db()
        self.assertIsNotNone(self.kho.last_login)

    def test_login_json_khong_doi(self):
        resp = login("kho1", PW)
        self.assertEqual(resp.json(), {"token": Token.objects.get(user=self.kho).key})

    def test_sai_mat_khau_khong_set_last_login(self):
        resp = login("kho1", "sai")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("non_field_errors", resp.json())
        self.kho.refresh_from_db()
        self.assertIsNone(self.kho.last_login)

    def test_nguoi_da_nghi_van_bi_tu_choi(self):
        self.kho.is_active = False
        self.kho.save()
        resp = login("kho1", PW)
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Token.objects.filter(user=self.kho).exists())
        self.kho.refresh_from_db()
        self.assertIsNone(self.kho.last_login)

    def test_login_lan_hai_dung_lai_token(self):
        k1 = login("kho1", PW).json()["token"]
        k2 = login("kho1", PW).json()["token"]
        self.assertEqual(k1, k2)
