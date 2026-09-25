"""
S47 — "Quyền của tôi": `/api/auth/me/` thêm `group_labels`, `capabilities` · BR-PQ-09, BR-PQ-12, BR-PQ-15.

`capabilities` = quyền Tầng 2 (spec §1.5 + mọi `Meta.permissions` tuỳ biến) người đó đang có,
kèm nhãn tiếng Việt; tính lại mỗi lần gọi `me` nên đổi nhóm có hiệu lực ngay, không cần
đăng nhập lại. Key cũ của S6 giữ nguyên.
"""
from django.apps import apps
from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.auth import services
from apps.accounts.models import StaffProfile
from apps.common.tests.fixtures import client_for, make_user

URL = "/api/auth/me/"
S6_KEYS = {"id", "username", "display_name", "phone", "groups", "permissions",
           "can_view_cost", "can_view_profit", "home"}


def codes(body):
    return [c["code"] for c in body["capabilities"]]


class S47MeLabelsTests(TestCase):
    def test_s47_ac1_quan_ly_nhan_nhom_va_viec_theo_spec_1_5(self):
        ql1 = make_user("ql1", "quan_ly")
        StaffProfile.objects.create(user=ql1, phone="0909000111", display_name="Chị Hạnh")
        resp = client_for(ql1).get(URL)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["display_name"], "Chị Hạnh")
        self.assertEqual(body["phone"], "0909000111")
        self.assertEqual(body["group_labels"], [{"code": "quan_ly", "label": "Quản lý"}])
        self.assertEqual(
            body["capabilities"][:5],
            [
                {"code": "inventory.publish_batch", "label": "Mở bán lô"},
                {"code": "sales.cancel_paid_order", "label": "Huỷ đơn đã thanh toán"},
                {"code": "sales.create_refund", "label": "Tạo phiếu hoàn"},
                {"code": "inventory.approve_returntostock", "label": "Duyệt hàng hoàn"},
                {"code": "inventory.approve_stockreconciliation", "label": "Duyệt kiểm kê"},
            ],
        )
        # Ngoài 5 việc §1.5, Quản lý chỉ còn quyền xem Tổng quan (S6); không có việc của Chủ.
        self.assertEqual(codes(body)[5:], ["reports.view_dashboard"])
        self.assertIs(body["can_view_cost"], False)

    def test_s47_ac1_chu_co_du_viec_tang_2(self):
        body = client_for(make_user("loc", "chu")).get(URL).json()
        self.assertEqual(body["group_labels"], [{"code": "chu", "label": "Chủ"}])
        self.assertEqual(codes(body), list(services.CAPABILITY_LABELS))
        for code in ("inventory.close_batch", "sales.confirm_refund",
                     "sales.confirm_payment_manual", "purchasing.add_purchasecost",
                     "inventory.view_costprice", "reports.view_profitreport",
                     "accounts.manage_staff"):
            self.assertIn(code, codes(body))

    def test_s47_ac1_kiem_nhiem_nhan_theo_thu_tu_vai(self):
        body = client_for(make_user("kho1", "nv_giao", "nv_kho")).get(URL).json()
        self.assertEqual(
            body["group_labels"],
            [{"code": "nv_kho", "label": "Nhân viên kho"},
             {"code": "nv_giao", "label": "Nhân viên giao"}],
        )

    def test_s47_ac1_nv_giao_khong_co_viec_tang_2(self):
        body = client_for(make_user("giao1", "nv_giao")).get(URL).json()
        self.assertEqual(body["capabilities"], [])

    def test_s47_capabilities_la_tap_con_cua_permissions(self):
        for user in (make_user("loc", "chu"), make_user("ql1", "quan_ly"),
                     make_user("kho1", "nv_kho"), make_user("giao1", "nv_giao")):
            body = client_for(user).get(URL).json()
            self.assertTrue(set(codes(body)) <= set(body["permissions"]), user.username)

    def test_s47_moi_quyen_meta_permissions_deu_co_nhan(self):
        # Thêm quyền Tầng 2 mới mà quên nhãn → test này đỏ.
        custom = {
            f"{m._meta.app_label}.{codename}"
            for m in apps.get_models() for codename, _ in m._meta.permissions
        }
        self.assertTrue(custom)
        self.assertEqual(custom - set(services.CAPABILITY_LABELS), set())

    def test_s47_quyen_gan_rieng_cho_user_cung_hien(self):
        body = client_for(make_user("kho1", "nv_kho", perms=["inventory.publish_batch"])).get(URL).json()
        self.assertIn("inventory.publish_batch", codes(body))

    def test_s47_nhom_la_hien_ten_goc(self):
        Group.objects.create(name="thu_viec")
        body = client_for(make_user("tv1", "thu_viec")).get(URL).json()
        self.assertEqual(body["group_labels"], [{"code": "thu_viec", "label": "thu_viec"}])

    # --- AC2 / AC3: đổi nhóm có hiệu lực ngay, không đăng nhập lại ----------------
    def test_s47_ac2_them_nv_giao_thi_me_doi_ngay_cung_token(self):
        kho1 = make_user("kho1", "nv_kho")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=kho1).key}")
        self.assertEqual([g["code"] for g in client.get(URL).json()["group_labels"]], ["nv_kho"])
        kho1.groups.add(Group.objects.get(name="nv_giao"))
        body = client.get(URL).json()
        self.assertEqual([g["code"] for g in body["group_labels"]], ["nv_kho", "nv_giao"])

    def test_s47_ac3_bo_quan_ly_thi_huy_don_mat_khoi_capabilities(self):
        ql1 = make_user("ql1", "quan_ly")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=ql1).key}")
        self.assertIn("sales.cancel_paid_order", codes(client.get(URL).json()))
        ql1.groups.remove(Group.objects.get(name="quan_ly"))
        body = client.get(URL).json()
        self.assertEqual(body["capabilities"], [])
        self.assertEqual(body["group_labels"], [])
        self.assertEqual(body["home"], "no-role")

    # --- AC4: không rò giá vốn ------------------------------------------------------
    def test_s47_ac4_khong_co_view_costprice_thi_khong_hien(self):
        for user in (make_user("ql1", "quan_ly"), make_user("kho1", "nv_kho"),
                     make_user("giao1", "nv_giao")):
            body = client_for(user).get(URL).json()
            self.assertNotIn("inventory.view_costprice", codes(body), user.username)
            self.assertNotIn("reports.view_profitreport", codes(body), user.username)
            self.assertIs(body["can_view_cost"], False)

    def test_s47_ac4_chu_co_view_costprice(self):
        body = client_for(make_user("loc", "chu")).get(URL).json()
        self.assertIn({"code": "inventory.view_costprice", "label": "Xem giá vốn"},
                      body["capabilities"])
        self.assertIs(body["can_view_cost"], True)

    # --- AC5 ------------------------------------------------------------------------
    def test_s47_ac5_superuser_khong_group_van_no_role(self):
        admin = User.objects.create_superuser("admin", password="x")
        body = client_for(admin).get(URL).json()
        self.assertEqual(body["group_labels"], [])
        self.assertEqual(body["home"], "no-role")

    # --- contract: chỉ THÊM key -------------------------------------------------------
    def test_s47_giu_key_s6_them_group_labels_capabilities(self):
        body = client_for(make_user("loc", "chu")).get(URL).json()
        self.assertEqual(set(body), S6_KEYS | {"group_labels", "capabilities", "must_change_password"})  # + S48

    def test_s47_chua_dang_nhap_401(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)
