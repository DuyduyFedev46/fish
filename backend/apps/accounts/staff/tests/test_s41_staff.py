"""
S41 — Chủ tạo tài khoản nhân viên và gán nhóm · BR-PQ-08/03/09, BR-PQ-17, BR-PQ-18.

Contract: `GET/POST /api/staff/`, `PATCH /api/staff/{id}/`, `PUT /api/staff/{id}/groups/`.
Mọi endpoint đòi `accounts.manage_staff` (chỉ Chủ có). Chống tự nâng quyền: không ai tự đổi
nhóm của mình; chỉ Chủ/superuser đụng nhóm `chu` và tài khoản Chủ.
"""
import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.accounts.models import AuditLog, StaffProfile
from apps.common.tests.fixtures import make_master
from apps.purchasing.models import PurchaseReceipt

from .helpers import (
    LIST_URL,
    ME_URL,
    STRONG_PASSWORD,
    audits,
    client_for,
    detail_url,
    group_names,
    login,
    make_user,
    staff_user,
    token_client,
)

ITEM_KEYS = {
    "id", "username", "display_name", "phone", "groups", "is_active", "last_login",
    "available_actions",
}


def new_staff(**overrides):
    body = {
        "username": "giao4", "display_name": "Anh Năm", "phone": "0909333444",
        "groups": ["nv_giao"], "password": STRONG_PASSWORD,
    }
    body.update(overrides)
    return body


class S41Base:
    def setUp(self):
        self.loc = staff_user("loc", "chu", phone="0909123456", display_name="Lộc")
        self.kho1 = staff_user("kho1", "nv_kho", phone="0909000222", display_name="Anh Tâm")
        self.chu = client_for(self.loc)


class S41CreateTests(S41Base, TestCase):
    def test_s41_ac1_chu_tao_giao4_dang_nhap_duoc_home_my_deliveries(self):
        resp = self.chu.post(LIST_URL, new_staff(), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        giao4 = User.objects.get(username="giao4")
        self.assertEqual(body["id"], giao4.pk)
        self.assertEqual(body["username"], "giao4")
        self.assertEqual(body["groups"], ["nv_giao"])
        self.assertIs(body["is_active"], True)
        profile = StaffProfile.objects.get(user=giao4)
        self.assertEqual(profile.phone, "0909333444")
        self.assertEqual(profile.display_name, "Anh Năm")
        self.assertFalse(giao4.is_staff)
        self.assertFalse(giao4.is_superuser)

        status, token = login("giao4", STRONG_PASSWORD)
        self.assertEqual(status, 200)
        me = client_for(None)
        me.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(me.get(ME_URL).json()["home"], "my-deliveries")

    def test_s41_ac1_audit_staff_create_khong_chua_mat_khau(self):
        self.chu.post(LIST_URL, new_staff(), format="json")
        logs = audits("staff_create")
        self.assertEqual(logs.count(), 1)
        log = logs.get()
        self.assertEqual(log.actor, self.loc)
        self.assertEqual(log.object_id, str(User.objects.get(username="giao4").pk))
        self.assertEqual(log.changes["groups"], {"from": [], "to": ["nv_giao"]})
        dumped = json.dumps(log.changes, ensure_ascii=False) + log.note + log.object_repr
        self.assertNotIn(STRONG_PASSWORD, dumped)
        self.assertNotIn("password", dumped)

    def test_s41_ac1_tao_nhieu_nhom_va_khong_nhom(self):
        resp = self.chu.post(
            LIST_URL, new_staff(username="kg1", groups=["nv_giao", "nv_kho"]), format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["groups"], ["nv_kho", "nv_giao"])
        resp = self.chu.post(LIST_URL, new_staff(username="moi1", groups=[]), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["groups"], [])

    def _assert_rejected(self, body, code="BR-PQ-08", detail=None):
        users_before = User.objects.count()
        resp = self.chu.post(LIST_URL, body, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], code)
        if detail:
            self.assertEqual(resp.json()["detail"], detail)
        self.assertEqual(User.objects.count(), users_before)
        self.assertFalse(audits("staff_create").exists())
        return resp.json()

    def test_s41_ac4_thieu_sdt(self):
        self._assert_rejected(new_staff(phone=""), detail="Số điện thoại là bắt buộc.")
        body = new_staff()
        del body["phone"]
        self._assert_rejected(body, detail="Số điện thoại là bắt buộc.")

    def test_s41_ac4_username_trung(self):
        self._assert_rejected(new_staff(username="kho1"), detail="Tên đăng nhập đã tồn tại.")
        self._assert_rejected(new_staff(username="KHO1"), detail="Tên đăng nhập đã tồn tại.")

    def test_s41_ac4_mat_khau_ngan_thong_diep_tieng_viet(self):
        body = self._assert_rejected(new_staff(password="Ab1!x"))
        self.assertIn("ít nhất 8 ký tự", body["detail"])

    def test_s41_ac4_mat_khau_pho_bien_hoac_toan_so(self):
        self._assert_rejected(new_staff(password="password123"))
        self._assert_rejected(new_staff(password="1234567890123"))

    def test_s41_ac4_nhom_khong_ton_tai(self):
        body = self._assert_rejected(new_staff(groups=["nv_giao", "admin"]))
        self.assertIn("admin", body["detail"])

    def test_s41_ac4_thieu_username_hoac_mat_khau_hoac_field_la(self):
        self._assert_rejected(new_staff(username=""))
        self._assert_rejected(new_staff(password=""))
        self._assert_rejected(new_staff(username="co dau cach"))
        self._assert_rejected(new_staff(is_superuser=True))
        self._assert_rejected(new_staff(groups="nv_giao"))

    def test_s41_ac6_ql9_manage_staff_khong_tao_duoc_tai_khoan_chu(self):
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        resp = client_for(ql9).post(LIST_URL, new_staff(groups=["chu"]), format="json")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(
            resp.json(), {"code": "BR-PQ-17", "detail": "Chỉ Chủ mới gán hoặc bỏ nhóm Chủ."}
        )
        self.assertFalse(User.objects.filter(username="giao4").exists())


class S41GroupsTests(S41Base, TestCase):
    def put_groups(self, client, user, groups):
        return client.put(detail_url(user, "groups/"), {"groups": groups}, format="json")

    def test_s41_ac2_chu_them_nv_giao_cho_kho1_me_co_ca_hai_nhom(self):
        _item, sup, wh = make_master()
        receipt = PurchaseReceipt.objects.create(
            supplier=sup, warehouse=wh, received_date=timezone.localdate(), created_by=self.kho1,
        )
        resp = self.put_groups(self.chu, self.kho1, ["nv_kho", "nv_giao"])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            resp.json(), {"groups": ["nv_kho", "nv_giao"], "added": ["nv_giao"], "removed": []}
        )
        me = token_client(self.kho1).get(ME_URL).json()
        self.assertEqual(me["groups"], ["nv_kho", "nv_giao"])
        log = audits("staff_groups_change").get()
        self.assertEqual(log.actor, self.loc)
        self.assertEqual(log.object_id, str(self.kho1.pk))
        self.assertEqual(log.changes, {"groups": {"from": ["nv_kho"], "to": ["nv_kho", "nv_giao"]}})
        receipt.refresh_from_db()
        self.assertEqual(receipt.created_by, self.kho1)  # BR-PQ-03: không hồi tố

    def test_s41_ac3_chu_bo_nv_giao_me_chi_con_nv_kho(self):
        self.put_groups(self.chu, self.kho1, ["nv_kho", "nv_giao"])
        resp = self.put_groups(self.chu, self.kho1, ["nv_kho"])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json(), {"groups": ["nv_kho"], "added": [], "removed": ["nv_giao"]})
        me = token_client(self.kho1).get(ME_URL).json()
        self.assertEqual(me["groups"], ["nv_kho"])
        self.assertEqual(me["home"], "dashboard")

    def test_s41_dat_nhom_giong_cu_khong_ghi_audit(self):
        resp = self.put_groups(self.chu, self.kho1, ["nv_kho"])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"groups": ["nv_kho"], "added": [], "removed": []})
        self.assertFalse(audits("staff_groups_change").exists())

    def test_s41_ac4_nhom_la_hoac_sai_kieu_400_khong_doi(self):
        for bad in (["nv_kho", "sieu_quyen"], "nv_kho", None):
            resp = self.put_groups(self.chu, self.kho1, bad)
            self.assertEqual(resp.status_code, 400, (bad, resp.content))
        self.assertEqual(group_names(self.kho1), ["nv_kho"])

    def test_s41_ac5_chu_tu_doi_nhom_cua_minh_400(self):
        for groups in (["chu", "quan_ly"], ["chu"], []):
            resp = self.put_groups(self.chu, self.loc, groups)
            self.assertEqual(resp.status_code, 400, resp.content)
            self.assertEqual(
                resp.json(),
                {"code": "BR-PQ-17", "detail": "Không thể tự đổi nhóm của chính mình."},
            )
        self.assertEqual(group_names(self.loc), ["chu"])
        self.assertFalse(audits("staff_groups_change").exists())

    def test_s41_ac5_superuser_cung_khong_tu_doi_nhom(self):
        root = User.objects.create_superuser("root", password="x")
        resp = self.put_groups(client_for(root), root, ["chu"])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-PQ-17")
        self.assertEqual(group_names(root), [])

    def test_s41_ac6_ql9_gan_chu_cho_kho1_403(self):
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        resp = self.put_groups(client_for(ql9), self.kho1, ["nv_kho", "chu"])
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(
            resp.json(), {"code": "BR-PQ-17", "detail": "Chỉ Chủ mới gán hoặc bỏ nhóm Chủ."}
        )
        self.assertEqual(group_names(self.kho1), ["nv_kho"])

    def test_s41_ac6_ql9_bo_chu_cua_loc_403(self):
        staff_user("chu_b", "chu")  # còn Chủ khác → lỗi phải là 403, không phải BR-PQ-18
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        resp = self.put_groups(client_for(ql9), self.loc, ["quan_ly"])
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-17")
        self.assertEqual(group_names(self.loc), ["chu"])

    def test_s41_ac6_ql9_doi_nhom_khac_cua_tai_khoan_chu_403(self):
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        resp = self.put_groups(client_for(ql9), self.loc, ["chu", "nv_kho"])
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(
            resp.json(),
            {"code": "BR-PQ-17", "detail": "Chỉ Chủ mới thao tác trên tài khoản Chủ."},
        )
        self.assertEqual(group_names(self.loc), ["chu"])

    def test_s41_ac6_ql9_van_doi_nhom_thuong_duoc(self):
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        resp = self.put_groups(client_for(ql9), self.kho1, ["nv_kho", "nv_giao"])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(group_names(self.kho1), ["nv_giao", "nv_kho"])

    def test_s41_chu_khong_phai_superuser_khong_thao_tac_tai_khoan_superuser(self):
        root = User.objects.create_superuser("root", password="x")
        resp = self.put_groups(self.chu, root, ["nv_kho"])
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-17")
        self.assertEqual(group_names(root), [])

    def test_s41_chu_gan_chu_cho_kho1_duoc(self):
        resp = self.put_groups(self.chu, self.kho1, ["chu", "nv_kho"])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["groups"], ["chu", "nv_kho"])

    def test_s41_ac7_superuser_bo_chu_cua_chu_duy_nhat_400(self):
        chu2 = User.objects.create_superuser("chu2", password="x")
        resp = self.put_groups(client_for(chu2), self.loc, ["quan_ly"])
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(
            resp.json(), {"code": "BR-PQ-18", "detail": "Phải còn ít nhất một Chủ đang làm."}
        )
        self.assertEqual(group_names(self.loc), ["chu"])

    def test_s41_ac7_con_chu_khac_dang_lam_thi_bo_duoc(self):
        chu_b = staff_user("chu_b", "chu")
        resp = self.put_groups(self.chu, chu_b, ["quan_ly"])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(group_names(chu_b), ["quan_ly"])

    def test_s41_ac7_chu_khac_da_nghi_khong_tinh(self):
        chu_b = staff_user("chu_b", "chu")
        chu_b.is_active = False
        chu_b.save()
        chu2 = User.objects.create_superuser("chu2", password="x")
        resp = self.put_groups(client_for(chu2), self.loc, [])
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-18")


class S41ListEditTests(S41Base, TestCase):
    def test_s41_list_dung_contract(self):
        resp = self.chu.get(LIST_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        rows = {r["username"]: r for r in resp.json()}
        self.assertEqual(set(rows), {"loc", "kho1"})
        kho1 = rows["kho1"]
        self.assertEqual(set(kho1), ITEM_KEYS)
        self.assertEqual(kho1["id"], self.kho1.pk)
        self.assertEqual(kho1["display_name"], "Anh Tâm")
        self.assertEqual(kho1["phone"], "0909000222")
        self.assertEqual(kho1["groups"], ["nv_kho"])
        self.assertIs(kho1["is_active"], True)
        self.assertIsNone(kho1["last_login"])
        self.assertEqual(
            kho1["available_actions"], ["edit", "set_groups", "reset_password", "deactivate"]
        )

    def test_s41_list_hanh_dong_cua_chinh_minh_khong_co_doi_nhom_cho_nghi(self):
        rows = {r["username"]: r for r in self.chu.get(LIST_URL).json()}
        self.assertEqual(rows["loc"]["available_actions"], ["edit"])

    def test_s41_list_loc_is_active(self):
        self.kho1.is_active = False
        self.kho1.save()
        active = [r["username"] for r in self.chu.get(LIST_URL + "?is_active=true").json()]
        inactive = self.chu.get(LIST_URL + "?is_active=false").json()
        self.assertEqual(active, ["loc"])
        self.assertEqual([r["username"] for r in inactive], ["kho1"])
        self.assertEqual(inactive[0]["available_actions"], ["edit", "reactivate"])

    def test_s41_list_ql9_thay_tai_khoan_chu_khong_co_hanh_dong(self):
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        rows = {r["username"]: r for r in client_for(ql9).get(LIST_URL).json()}
        self.assertEqual(rows["loc"]["available_actions"], [])
        self.assertIn("set_groups", rows["kho1"]["available_actions"])

    def test_s41_ac10_list_khong_co_mat_khau_hash_token(self):
        token_client(self.kho1)  # kho1 đã đăng nhập → có token
        resp = self.chu.get(LIST_URL)
        text = resp.content.decode()
        for row in resp.json():
            self.assertEqual(set(row), ITEM_KEYS)
        self.assertNotIn('"password"', text)  # action "reset_password" là tên nút, được phép
        self.assertNotIn(User.objects.get(pk=self.kho1.pk).password, text)
        self.assertNotIn(Token.objects.get(user=self.kho1).key, text)
        self.assertNotIn('"token"', text.lower())

    def test_s41_patch_sua_ten_sdt_ghi_audit(self):
        resp = self.chu.patch(
            detail_url(self.kho1), {"display_name": "Anh Tâm Kho", "phone": "0909000999"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["display_name"], "Anh Tâm Kho")
        self.assertEqual(resp.json()["phone"], "0909000999")
        profile = StaffProfile.objects.get(user=self.kho1)
        self.assertEqual((profile.display_name, profile.phone), ("Anh Tâm Kho", "0909000999"))
        log = audits("staff_update").get()
        self.assertEqual(log.changes["phone"], {"from": "0909000222", "to": "0909000999"})

    def test_s41_patch_tao_ho_so_neu_chua_co(self):
        moi = make_user("moi1")
        resp = self.chu.patch(detail_url(moi), {"phone": "0911222333"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(StaffProfile.objects.get(user=moi).phone, "0911222333")

    def test_s41_patch_field_la_hoac_sdt_rong_400(self):
        for body in ({"groups": ["chu"]}, {"is_active": False}, {"password": "x" * 12},
                     {"username": "khac"}, {"phone": ""}, {"is_superuser": True}):
            resp = self.chu.patch(detail_url(self.kho1), body, format="json")
            self.assertEqual(resp.status_code, 400, (body, resp.content))
        self.kho1.refresh_from_db()
        self.assertEqual(self.kho1.username, "kho1")
        self.assertEqual(group_names(self.kho1), ["nv_kho"])
        self.assertFalse(audits("staff_update").exists())

    def test_s41_put_chi_tiet_405(self):
        resp = self.chu.put(detail_url(self.kho1), {"display_name": "x"}, format="json")
        self.assertEqual(resp.status_code, 405)

    def test_s41_ql9_khong_sua_ho_so_chu(self):
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        resp = client_for(ql9).patch(detail_url(self.loc), {"phone": "0900"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["code"], "BR-PQ-17")


class S41PermissionTests(S41Base, TestCase):
    def test_s41_ac9_quan_ly_nv_kho_nv_giao_403(self):
        for username, group in (("ql1", "quan_ly"), ("kho2", "nv_kho"), ("giao1", "nv_giao")):
            client = client_for(make_user(username, group))
            self.assertEqual(client.get(LIST_URL).status_code, 403, username)
            self.assertEqual(client.get(detail_url(self.kho1)).status_code, 403, username)
            self.assertEqual(
                client.post(LIST_URL, new_staff(), format="json").status_code, 403, username
            )
            self.assertEqual(
                client.put(detail_url(self.kho1, "groups/"), {"groups": ["chu"]},
                           format="json").status_code, 403, username,
            )
            self.assertEqual(
                client.patch(detail_url(self.kho1), {"phone": "0"}, format="json").status_code,
                403, username,
            )
        self.assertFalse(User.objects.filter(username="giao4").exists())
        self.assertEqual(group_names(self.kho1), ["nv_kho"])
        self.assertFalse(AuditLog.objects.exists())

    def test_s41_ac9_chua_dang_nhap_401(self):
        anon = client_for(None)
        self.assertEqual(anon.get(LIST_URL).status_code, 401)
        self.assertEqual(anon.post(LIST_URL, new_staff(), format="json").status_code, 401)
        self.assertEqual(
            anon.put(detail_url(self.kho1, "groups/"), {"groups": []}, format="json").status_code,
            401,
        )
