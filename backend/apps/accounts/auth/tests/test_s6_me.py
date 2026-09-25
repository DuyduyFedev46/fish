"""
S6 — API "tôi là ai, có quyền gì" (`GET /api/auth/me/`) · BR-PQ-09, BR-PQ-01, UC-01.

Kèm quyết định S6 cho FE: quyền `reports.view_dashboard` (Tổng quan) được tạo mới, gán
chu/quan_ly/nv_kho; `/api/dashboard/summary/` đòi quyền này (BR-PQ-12: backend là lớp chặn).
"""
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import StaffProfile
from apps.common.tests.fixtures import client_for, make_user

URL = "/api/auth/me/"
DASHBOARD = "/api/dashboard/summary/"
UNAUTHORIZED = {"detail": "Thông tin xác thực không hợp lệ."}


def group_perms(*names):
    perms = Permission.objects.filter(group__name__in=names).select_related("content_type")
    return sorted({f"{p.content_type.app_label}.{p.codename}" for p in perms})


class S6MeTests(TestCase):
    def test_s6_ac1_chu_xem_gia_von_lai_lo_home_dashboard(self):
        loc = make_user("loc", "chu")
        StaffProfile.objects.create(user=loc, phone="0909123456", display_name="Lộc")
        resp = client_for(loc).get(URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["id"], loc.pk)
        self.assertEqual(body["username"], "loc")
        self.assertEqual(body["display_name"], "Lộc")
        self.assertEqual(body["phone"], "0909123456")
        self.assertEqual(body["groups"], ["chu"])
        self.assertIs(body["can_view_cost"], True)
        self.assertIs(body["can_view_profit"], True)
        self.assertEqual(body["home"], "dashboard")
        self.assertEqual(body["permissions"], group_perms("chu"))
        for perm in ("inventory.publish_batch", "inventory.close_batch",
                     "sales.confirm_payment_manual", "reports.view_dashboard"):
            self.assertIn(perm, body["permissions"])

    def test_s6_ac1_dung_dung_cac_key_contract(self):
        body = client_for(make_user("loc", "chu")).get(URL).json()
        self.assertEqual(
            set(body),
            {"id", "username", "display_name", "phone", "groups", "permissions",
             "can_view_cost", "can_view_profit", "home",
             "group_labels", "capabilities",  # S47 chỉ thêm 2 key
             "must_change_password"},  # S48 thêm 1 key
        )

    def test_s6_ac1_khong_co_ho_so_thi_display_name_la_username_phone_rong(self):
        body = client_for(make_user("loc", "chu")).get(URL).json()
        self.assertEqual(body["display_name"], "loc")
        self.assertEqual(body["phone"], "")

    def test_s6_ac2_kiem_nhiem_kho_giao_permissions_la_hop(self):
        kho1 = make_user("kho1", "nv_giao", "nv_kho")
        body = client_for(kho1).get(URL).json()
        self.assertEqual(body["groups"], ["nv_kho", "nv_giao"])  # thứ tự cố định theo vai
        self.assertEqual(body["permissions"], group_perms("nv_kho", "nv_giao"))
        self.assertEqual(body["home"], "dashboard")
        self.assertIs(body["can_view_cost"], False)
        self.assertIs(body["can_view_profit"], False)

    def test_s6_ac3_chi_nv_giao_home_my_deliveries_khong_xem_gia_von(self):
        body = client_for(make_user("giao1", "nv_giao")).get(URL).json()
        self.assertEqual(body["groups"], ["nv_giao"])
        self.assertEqual(body["home"], "my-deliveries")
        self.assertIs(body["can_view_cost"], False)
        self.assertNotIn("inventory.view_costprice", body["permissions"])
        self.assertNotIn("reports.view_dashboard", body["permissions"])

    def test_s6_ac3_quan_ly_khong_xem_gia_von(self):
        body = client_for(make_user("ql1", "quan_ly")).get(URL).json()
        self.assertEqual(body["home"], "dashboard")
        self.assertIs(body["can_view_cost"], False)
        self.assertIs(body["can_view_profit"], False)
        self.assertNotIn("inventory.view_costprice", body["permissions"])
        self.assertNotIn("reports.view_profitreport", body["permissions"])

    def test_s6_ac4_khong_group_nao_home_no_role(self):
        body = client_for(make_user("moi1")).get(URL).json()
        self.assertEqual(body["groups"], [])
        self.assertEqual(body["permissions"], [])
        self.assertEqual(body["home"], "no-role")

    def test_s6_ac4_superuser_khong_group_van_no_role(self):
        # S47-AC5: admin (superuser, không Group) vào console → màn "chưa được phân quyền".
        admin = User.objects.create_superuser("admin", password="x")
        body = client_for(admin).get(URL).json()
        self.assertEqual(body["groups"], [])
        self.assertEqual(body["home"], "no-role")

    def test_s6_ac5_token_cua_nguoi_da_nghi_bi_401_moi_api(self):
        giao1 = make_user("giao1", "nv_giao")
        token = Token.objects.create(user=giao1)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(client.get(URL).status_code, 200)
        giao1.is_active = False
        giao1.save(update_fields=["is_active"])
        resp = client.get(URL)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), UNAUTHORIZED)
        self.assertEqual(client.get("/api/delivery/notes/").status_code, 401)
        self.assertEqual(client.get(DASHBOARD).status_code, 401)

    def test_s6_ac5_token_da_thu_hoi_401(self):
        giao1 = make_user("giao1", "nv_giao")
        token = Token.objects.create(user=giao1)
        key = token.key
        token.delete()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        resp = client.get(URL)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), UNAUTHORIZED)

    def test_s6_ac6_khong_token_401(self):
        resp = APIClient().get(URL)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), UNAUTHORIZED)

    def test_s6_chi_cho_get(self):
        resp = client_for(make_user("loc", "chu")).post(URL, {}, format="json")
        self.assertEqual(resp.status_code, 405)


class S6DashboardPermissionTests(TestCase):
    """Quyết định S6: `reports.view_dashboard` là quyền của mục Tổng quan."""

    def test_s6_view_dashboard_gan_cho_chu_quan_ly_nv_kho_khong_cho_nv_giao(self):
        holders = set(
            Group.objects.filter(
                permissions__content_type__app_label="reports",
                permissions__codename="view_dashboard",
            ).values_list("name", flat=True)
        )
        self.assertEqual(holders, {"chu", "quan_ly", "nv_kho"})

    def test_s6_dashboard_200_voi_nguoi_co_quyen(self):
        for name, group in (("loc", "chu"), ("ql1", "quan_ly"), ("kho1", "nv_kho")):
            with self.subTest(group=group):
                resp = client_for(make_user(name, group)).get(DASHBOARD)
                self.assertEqual(resp.status_code, 200, resp.content)

    def test_s6_dashboard_403_voi_nv_giao_va_nguoi_khong_group(self):
        for name, groups in (("giao1", ("nv_giao",)), ("moi1", ())):
            with self.subTest(user=name):
                resp = client_for(make_user(name, *groups)).get(DASHBOARD)
                self.assertEqual(resp.status_code, 403, resp.content)

    def test_s6_dashboard_401_khi_chua_dang_nhap(self):
        self.assertEqual(APIClient().get(DASHBOARD).status_code, 401)
