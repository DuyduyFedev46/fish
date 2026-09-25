"""
S46 — Đăng xuất thu hồi phiên, tự đổi mật khẩu · BR-PQ-12, BR-PQ-04, BR-PQ-17, C8.

C8: DRF cấp **một token mỗi người** → đăng xuất / đổi mật khẩu ở một máy là văng mọi máy.
Test dùng token thật (header `Authorization: Token …`), không `force_authenticate`, để kiểm
đúng việc thu token.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import make_user

LOGOUT = "/api/auth/logout/"
CHANGE = "/api/auth/change-password/"
ME = "/api/auth/me/"
LOGIN = "/api/auth/token/"
UNAUTHORIZED = {"detail": "Thông tin xác thực không hợp lệ."}

OLD = "Ca-ve-cu-2026"
NEW = "Ca-ve-moi-2026"


def token_client(key):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
    return client


def login(username, password):
    return APIClient().post(LOGIN, {"username": username, "password": password}, format="json")


class S46LogoutTests(TestCase):
    def setUp(self):
        self.giao1 = make_user("giao1", "nv_giao")
        self.token = Token.objects.create(user=self.giao1)

    def test_s46_ac1_dang_xuat_204_xoa_token(self):
        client = token_client(self.token.key)
        resp = client.post(LOGOUT, {}, format="json")
        self.assertEqual(resp.status_code, 204, resp.content)
        self.assertFalse(Token.objects.filter(user=self.giao1).exists())

    def test_s46_ac1_goi_lai_bang_token_cu_401(self):
        client = token_client(self.token.key)
        client.post(LOGOUT, {}, format="json")
        resp = client.get(ME)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), UNAUTHORIZED)

    def test_s46_ac1_c8_may_khac_cung_van_401(self):
        # C8: một token mỗi người — máy B dùng cùng token nên văng theo.
        may_b = token_client(self.token.key)
        token_client(self.token.key).post(LOGOUT, {}, format="json")
        self.assertEqual(may_b.get(ME).status_code, 401)

    def test_s46_ac1_dang_nhap_lai_duoc_token_moi(self):
        user = User.objects.get(pk=self.giao1.pk)
        user.set_password(OLD)
        user.save()
        token_client(self.token.key).post(LOGOUT, {}, format="json")
        resp = login("giao1", OLD)
        self.assertEqual(resp.status_code, 200)
        self.assertNotEqual(resp.json()["token"], self.token.key)
        self.assertEqual(token_client(resp.json()["token"]).get(ME).status_code, 200)

    def test_s46_ac1_khong_dung_token_cua_nguoi_khac(self):
        kho1 = make_user("kho1", "nv_kho")
        other = Token.objects.create(user=kho1)
        token_client(self.token.key).post(LOGOUT, {}, format="json")
        self.assertTrue(Token.objects.filter(pk=other.pk).exists())
        self.assertEqual(token_client(other.key).get(ME).status_code, 200)

    def test_s46_ac1_nguoi_khong_thuoc_group_nao_cung_dang_xuat_duoc(self):
        moi = make_user("moi1")
        key = Token.objects.create(user=moi).key
        self.assertEqual(token_client(key).post(LOGOUT, {}, format="json").status_code, 204)
        self.assertFalse(Token.objects.filter(user=moi).exists())

    def test_s46_dang_xuat_chua_dang_nhap_401(self):
        resp = APIClient().post(LOGOUT, {}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), UNAUTHORIZED)
        self.assertTrue(Token.objects.filter(pk=self.token.pk).exists())

    def test_s46_dang_xuat_token_da_thu_401(self):
        client = token_client(self.token.key)
        client.post(LOGOUT, {}, format="json")
        self.assertEqual(client.post(LOGOUT, {}, format="json").status_code, 401)

    def test_s46_dang_xuat_chi_post(self):
        resp = token_client(self.token.key).get(LOGOUT)
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Token.objects.filter(pk=self.token.pk).exists())

    def test_s46_dang_xuat_ghi_audit(self):
        token_client(self.token.key).post(LOGOUT, {}, format="json")
        log = AuditLog.objects.get(action="logout")
        self.assertEqual(log.actor_id, self.giao1.pk)
        self.assertNotIn(self.token.key, str(log.changes) + log.note + log.object_repr)


class S46ChangePasswordTests(TestCase):
    def setUp(self):
        self.kho1 = make_user("kho1", "nv_kho")
        self.kho1.set_password(OLD)
        self.kho1.save()
        self.loc = make_user("loc", "chu")
        self.loc.set_password("Loc-mat-khau-2026")
        self.loc.save()
        self.token = Token.objects.create(user=self.kho1)
        self.may_a = token_client(self.token.key)
        self.may_b = token_client(self.token.key)

    def change(self, client=None, **body):
        return (client or self.may_a).post(CHANGE, body, format="json")

    # --- AC2 -----------------------------------------------------------------
    def test_s46_ac2_doi_mat_khau_tra_token_moi_may_a_lam_tiep(self):
        resp = self.change(old_password=OLD, new_password=NEW)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(set(body), {"token"})
        self.assertNotEqual(body["token"], self.token.key)
        self.assertEqual(Token.objects.get(user=self.kho1).key, body["token"])
        self.assertEqual(token_client(body["token"]).get(ME).status_code, 200)

    def test_s46_ac2_may_b_401_o_lan_goi_ke_tiep(self):
        self.change(old_password=OLD, new_password=NEW)
        resp = self.may_b.get(ME)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), UNAUTHORIZED)

    def test_s46_ac2_mat_khau_moi_dang_nhap_duoc_cu_thi_khong(self):
        self.change(old_password=OLD, new_password=NEW)
        self.assertEqual(login("kho1", NEW).status_code, 200)
        self.assertEqual(login("kho1", OLD).status_code, 400)

    def test_s46_ac2_audit_password_change_self_khong_chua_mat_khau(self):
        resp = self.change(old_password=OLD, new_password=NEW)
        log = AuditLog.objects.get(action="password_change_self")
        self.assertEqual(log.actor_id, self.kho1.pk)
        self.assertEqual(log.object_id, str(self.kho1.pk))
        dump = f"{log.changes} {log.note} {log.object_repr}"
        user = User.objects.get(pk=self.kho1.pk)
        for secret in (OLD, NEW, user.password, self.token.key, resp.json()["token"]):
            self.assertNotIn(secret, dump)

    def test_s46_ac2_nguoi_chua_co_token_doi_qua_session_van_nhan_token(self):
        # Đăng nhập kiểu session (vd Django Admin) — không có token trước đó.
        client = APIClient()
        client.force_authenticate(self.loc)
        resp = client.post(
            CHANGE, {"old_password": "Loc-mat-khau-2026", "new_password": NEW}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(Token.objects.get(user=self.loc).key, resp.json()["token"])

    # --- AC3 -----------------------------------------------------------------
    def test_s46_ac3_sai_mat_khau_hien_tai_400_token_cu_con_dung(self):
        resp = self.change(old_password="sai-roi-nhe", new_password=NEW)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(),
            {"code": "AUTH_OLD_PASSWORD", "detail": "Mật khẩu hiện tại không đúng."},
        )
        self.assertEqual(self.may_b.get(ME).status_code, 200)
        self.assertTrue(User.objects.get(pk=self.kho1.pk).check_password(OLD))
        self.assertFalse(AuditLog.objects.filter(action="password_change_self").exists())

    def test_s46_ac3_thieu_mat_khau_hien_tai_400(self):
        resp = self.change(new_password=NEW)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "AUTH_OLD_PASSWORD")

    def test_s46_ac3_mat_khau_moi_6_ky_tu_400_tieng_viet(self):
        resp = self.change(old_password=OLD, new_password="Ab1-x9")
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "AUTH_WEAK_PASSWORD")
        self.assertIn("ít nhất 8 ký tự", body["detail"])
        self.assertNotIn("Ab1-x9", body["detail"])
        self.assertEqual(self.may_b.get(ME).status_code, 200)
        self.assertTrue(User.objects.get(pk=self.kho1.pk).check_password(OLD))

    def test_s46_ac3_mat_khau_moi_giong_ten_dang_nhap_400(self):
        tam = make_user("nguyenvantam", "nv_kho")
        tam.set_password(OLD)
        tam.save()
        client = token_client(Token.objects.create(user=tam).key)
        resp = self.change(client, old_password=OLD, new_password="nguyenvantam1")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "AUTH_WEAK_PASSWORD")

    def test_s46_ac3_mat_khau_moi_pho_bien_400(self):
        resp = self.change(old_password=OLD, new_password="password123")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "AUTH_WEAK_PASSWORD")

    def test_s46_ac3_mat_khau_moi_rong_400(self):
        resp = self.change(old_password=OLD, new_password="")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "AUTH_WEAK_PASSWORD")
        self.assertEqual(self.may_b.get(ME).status_code, 200)

    def test_s46_ac3_mat_khau_moi_khong_phai_chuoi_400(self):
        resp = self.change(old_password=OLD, new_password=12345678901)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "AUTH_WEAK_PASSWORD")

    def test_s46_ac3_sai_ca_hai_thi_bao_mat_khau_hien_tai_truoc(self):
        resp = self.change(old_password="sai-roi-nhe", new_password="123")
        self.assertEqual(resp.json()["code"], "AUTH_OLD_PASSWORD")

    # --- AC4 -----------------------------------------------------------------
    def test_s46_ac4_chua_dang_nhap_401(self):
        resp = APIClient().post(CHANGE, {"old_password": OLD, "new_password": NEW}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), UNAUTHORIZED)
        self.assertTrue(User.objects.get(pk=self.kho1.pk).check_password(OLD))

    def test_s46_ac4_token_sai_401(self):
        resp = self.change(token_client("khong-phai-token"), old_password=OLD, new_password=NEW)
        self.assertEqual(resp.status_code, 401)

    def test_s46_ac4_chi_post(self):
        self.assertEqual(self.may_a.get(CHANGE).status_code, 405)

    # --- AC5 -----------------------------------------------------------------
    def test_s46_ac5_gui_username_loc_bi_tu_choi_400_khong_doi_ai(self):
        resp = self.change(old_password=OLD, new_password=NEW, username="loc")
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["code"], "BR-PQ-17")
        self.assertIn("username", body["detail"])
        self.assertTrue(User.objects.get(pk=self.loc.pk).check_password("Loc-mat-khau-2026"))
        self.assertTrue(User.objects.get(pk=self.kho1.pk).check_password(OLD))
        self.assertEqual(self.may_b.get(ME).status_code, 200)

    def test_s46_ac5_gui_user_id_bi_tu_choi(self):
        resp = self.change(old_password=OLD, new_password=NEW, user=self.loc.pk)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-PQ-17")

    def test_s46_ac5_chi_doi_mat_khau_nguoi_dang_nhap(self):
        self.change(old_password=OLD, new_password=NEW)
        self.assertTrue(User.objects.get(pk=self.kho1.pk).check_password(NEW))
        self.assertTrue(User.objects.get(pk=self.loc.pk).check_password("Loc-mat-khau-2026"))

    def test_s46_nguoi_da_nghi_khong_doi_duoc_401(self):
        User.objects.filter(pk=self.kho1.pk).update(is_active=False)
        self.assertEqual(self.change(old_password=OLD, new_password=NEW).status_code, 401)


class S46SessionTests(TestCase):
    """Người đăng nhập bằng session (Django Admin) — đổi mật khẩu vẫn giữ phiên hiện tại."""

    def test_s46_ac2_session_giu_phien_sau_khi_tu_doi(self):
        kho1 = make_user("kho1", "nv_kho")
        kho1.set_password(OLD)
        kho1.save()
        client = APIClient()
        self.assertTrue(client.login(username="kho1", password=OLD))
        resp = client.post(CHANGE, {"old_password": OLD, "new_password": NEW}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(client.get(ME).status_code, 200)

    def test_s46_ac1_dang_xuat_session_thi_phien_chet(self):
        make_user("kho1", "nv_kho")
        client = APIClient()
        self.assertTrue(client.login(username="kho1", password="x"))
        self.assertEqual(client.post(LOGOUT, {}, format="json").status_code, 204)
        self.assertEqual(client.get(ME).status_code, 401)
