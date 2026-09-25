"""
S48 — Đổi mật khẩu bắt buộc lần đầu · BR-PQ-19.

BR-PQ-19: tài khoản do Chủ tạo (S41) hoặc được Chủ đặt lại mật khẩu (S42) mang cờ
`StaffProfile.must_change_password=True`. Khi cờ bật, mọi API nghiệp vụ trả
403 `{"detail", "code": "AUTH_MUST_CHANGE_PASSWORD"}`, trừ `/api/auth/me/`,
`/api/auth/change-password/`, `/api/auth/logout/` (và đăng nhập). Tự đổi mật khẩu xong → cờ tắt.
Superuser không bị ép.

Test dùng token thật (như console), không `force_authenticate` (DRF bỏ qua lớp xác thực).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import StaffProfile
from apps.accounts.staff.tests.helpers import STRONG_PASSWORD, client_for, staff_user

ME = "/api/auth/me/"
CHANGE = "/api/auth/change-password/"
LOGOUT = "/api/auth/logout/"
LOGIN = "/api/auth/token/"
STAFF = "/api/staff/"
CODE = "AUTH_MUST_CHANGE_PASSWORD"
TEMP = "Tam-thoi-2026!"
MINE = "Cua-rieng-toi-2026"

# Một mẫu API nghiệp vụ đại diện cho từng miền.
BUSINESS_GETS = (
    "/api/delivery/notes/",
    "/api/sales/orders/",
    "/api/inventory/batches/",
    "/api/dashboard/summary/",
    "/api/catalog/items/",
)


def login(username, password):
    return APIClient().post(LOGIN, {"username": username, "password": password}, format="json")


def token_client(key):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
    return client


class S48Base(TestCase):
    def setUp(self):
        self.loc = staff_user("loc", "chu", display_name="Lộc")
        self.chu = client_for(self.loc)

    def create_giao4(self):
        resp = self.chu.post(
            STAFF,
            {"username": "giao4", "display_name": "Anh Năm", "phone": "0909333444",
             "groups": ["nv_giao", "nv_kho"], "password": TEMP},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        return User.objects.get(username="giao4")

    def login_client(self, username, password):
        resp = login(username, password)
        self.assertEqual(resp.status_code, 200, resp.content)
        return token_client(resp.json()["token"])


class S48FlagTests(S48Base):
    def test_s48_ac1_tao_tai_khoan_bat_co(self):
        giao4 = self.create_giao4()
        self.assertTrue(StaffProfile.objects.get(user=giao4).must_change_password)

    def test_s48_ac1_me_co_must_change_password_true(self):
        self.create_giao4()
        resp = self.login_client("giao4", TEMP).get(ME)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIs(resp.json()["must_change_password"], True)

    def test_s48_me_nguoi_binh_thuong_false(self):
        resp = client_for(self.loc).get(ME)
        self.assertIs(resp.json()["must_change_password"], False)

    def test_s48_me_nguoi_khong_co_ho_so_false(self):
        user = User.objects.create_user("khongHoSo", password="x")
        resp = client_for(user).get(ME)
        self.assertIs(resp.json()["must_change_password"], False)

    def test_s48_ac1_moi_api_nghiep_vu_403_code(self):
        self.create_giao4()
        client = self.login_client("giao4", TEMP)
        for url in BUSINESS_GETS:
            with self.subTest(url=url):
                resp = client.get(url)
                self.assertEqual(resp.status_code, 403, resp.content)
                body = resp.json()
                self.assertEqual(body["code"], CODE)
                self.assertTrue(body["detail"])

    def test_s48_ac1_ghi_cung_bi_chan(self):
        self.create_giao4()
        client = self.login_client("giao4", TEMP)
        resp = client.post("/api/purchasing/suppliers/", {"name": "NCC lạ"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["code"], CODE)

    def test_s48_ac1_logout_van_dung_duoc(self):
        giao4 = self.create_giao4()
        client = self.login_client("giao4", TEMP)
        self.assertEqual(client.post(LOGOUT, {}, format="json").status_code, 204)
        self.assertFalse(Token.objects.filter(user=giao4).exists())

    def test_s48_ac1_chu_bi_dat_lai_mat_khau_cung_bi_chan_staff_api(self):
        # Chủ thứ hai bị superuser đặt lại mật khẩu → cũng phải tự đổi trước khi quản lý người.
        chu2 = staff_user("chu2", "chu")
        root = User.objects.create_superuser("root", password="x")
        resp = client_for(root).post(
            f"{STAFF}{chu2.pk}/reset-password/", {"new_password": TEMP}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        client = self.login_client("chu2", TEMP)
        resp = client.get(STAFF)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["code"], CODE)


class S48ChangeTests(S48Base):
    def test_s48_ac2_doi_mat_khau_tat_co_va_vao_duoc_nghiep_vu(self):
        giao4 = self.create_giao4()
        client = self.login_client("giao4", TEMP)
        resp = client.post(CHANGE, {"old_password": TEMP, "new_password": MINE}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(StaffProfile.objects.get(user=giao4).must_change_password)
        fresh = token_client(resp.json()["token"])
        self.assertIs(fresh.get(ME).json()["must_change_password"], False)
        self.assertEqual(fresh.get("/api/delivery/notes/").status_code, 200)

    def test_s48_ac2_doi_that_bai_co_van_bat(self):
        giao4 = self.create_giao4()
        client = self.login_client("giao4", TEMP)
        resp = client.post(CHANGE, {"old_password": "sai", "new_password": MINE}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(StaffProfile.objects.get(user=giao4).must_change_password)

    def test_s48_ac6_tu_doi_khi_co_tat_khong_bat_lai(self):
        kho1 = staff_user("kho1", "nv_kho")
        kho1.set_password(STRONG_PASSWORD)
        kho1.save()
        client = self.login_client("kho1", STRONG_PASSWORD)
        resp = client.post(
            CHANGE, {"old_password": STRONG_PASSWORD, "new_password": MINE}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(StaffProfile.objects.get(user=kho1).must_change_password)

    def test_s48_ac6_chu_dat_lai_mat_khau_bat_lai_co(self):
        kho1 = staff_user("kho1", "nv_kho")
        self.assertFalse(StaffProfile.objects.get(user=kho1).must_change_password)
        resp = self.chu.post(
            f"{STAFF}{kho1.pk}/reset-password/", {"new_password": TEMP}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(StaffProfile.objects.get(user=kho1).must_change_password)
        client = self.login_client("kho1", TEMP)
        self.assertEqual(client.get("/api/inventory/batches/").json()["code"], CODE)

    def test_s48_ac6_superuser_khong_bi_ep(self):
        root = User.objects.create_superuser("admin", password=TEMP)
        StaffProfile.objects.create(user=root, phone="0900", must_change_password=True)
        client = self.login_client("admin", TEMP)
        self.assertIs(client.get(ME).json()["must_change_password"], False)
        self.assertEqual(client.get("/api/sales/orders/").status_code, 200)

    def test_s48_ac7_ho_so_moi_mac_dinh_false(self):
        kho1 = staff_user("kho1", "nv_kho")
        self.assertFalse(StaffProfile.objects.get(user=kho1).must_change_password)
