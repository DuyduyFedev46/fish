"""
S42 — Chủ cho nhân viên nghỉ, cho làm lại, đặt lại mật khẩu · BR-PQ-01/02/04, BR-PQ-17/18, BR-GH-08.

Cho nghỉ = `is_active=False` + xoá token → mọi API của người đó 401 ngay (C8: một token mỗi
người, nên mọi máy cùng văng). Đặt lại mật khẩu cũng thu token. Không xoá tài khoản.
"""
import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token

from apps.accounts.models import AuditLog, StaffProfile
from apps.common.tests.fixtures import make_order_with_note
from apps.delivery.models import DeliveryNote

from .helpers import (
    ME_URL,
    STRONG_PASSWORD,
    UNAUTHORIZED,
    audits,
    client_for,
    detail_url,
    login,
    make_user,
    staff_user,
    token_client,
)

NEW_PASSWORD = "Moi-Kho-2026?"


class S42Base(TestCase):
    def setUp(self):
        self.loc = staff_user("loc", "chu", display_name="Lộc")
        self.giao1 = staff_user("giao1", "nv_giao", display_name="Anh Tư")
        self.giao1.set_password(STRONG_PASSWORD)
        self.giao1.save()
        self.kho1 = staff_user("kho1", "nv_kho")
        self.kho1.set_password(STRONG_PASSWORD)
        self.kho1.save()
        self.chu = client_for(self.loc)

    def post(self, client, user, action, body=None):
        return client.post(detail_url(user, f"{action}/"), body or {}, format="json")


class S42DeactivateTests(S42Base):
    def test_s42_ac1_cho_nghi_token_bi_xoa_api_ke_tiep_401(self):
        phone = token_client(self.giao1)
        self.assertEqual(phone.get(ME_URL).status_code, 200)
        _order, _cust, note = make_order_with_note("DH01", "0901000001", assigned_to=self.giao1)
        note.status = DeliveryNote.Status.COMPLETED
        note.save(update_fields=["status"])

        resp = self.post(self.chu, self.giao1, "deactivate")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json(), {"is_active": False})

        again = phone.get(ME_URL)
        self.assertEqual(again.status_code, 401)
        self.assertEqual(again.json(), UNAUTHORIZED)
        self.assertFalse(Token.objects.filter(user=self.giao1).exists())
        self.giao1.refresh_from_db()
        self.assertFalse(self.giao1.is_active)
        self.assertEqual(
            StaffProfile.objects.get(user=self.giao1).status, StaffProfile.Status.INACTIVE
        )
        note.refresh_from_db()
        self.assertEqual(note.assigned_to, self.giao1)  # chứng từ cũ vẫn giữ người giao
        log = audits("staff_deactivate").get()
        self.assertEqual(log.actor, self.loc)
        self.assertEqual(log.object_id, str(self.giao1.pk))
        self.assertEqual(log.changes["is_active"], {"from": True, "to": False})
        self.assertEqual(login("giao1", STRONG_PASSWORD)[0], 400)  # không đăng nhập lại được

    def test_s42_ac1_khong_xoa_tai_khoan(self):
        self.post(self.chu, self.giao1, "deactivate")
        self.assertTrue(User.objects.filter(pk=self.giao1.pk).exists())

    def test_s42_ac2_cho_lam_lai_dang_nhap_bang_mat_khau_cu(self):
        self.post(self.chu, self.giao1, "deactivate")
        resp = self.post(self.chu, self.giao1, "reactivate")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json(), {"is_active": True})
        status, token = login("giao1", STRONG_PASSWORD)
        self.assertEqual(status, 200)
        self.assertTrue(token)
        self.assertEqual(
            StaffProfile.objects.get(user=self.giao1).status, StaffProfile.Status.ACTIVE
        )
        log = audits("staff_reactivate").get()
        self.assertEqual(log.changes["is_active"], {"from": False, "to": True})

    def test_s42_cho_nghi_nguoi_da_nghi_hoac_lam_lai_nguoi_dang_lam_400(self):
        self.assertEqual(self.post(self.chu, self.giao1, "reactivate").status_code, 400)
        self.post(self.chu, self.giao1, "deactivate")
        self.assertEqual(self.post(self.chu, self.giao1, "deactivate").status_code, 400)
        self.assertEqual(audits("staff_deactivate").count(), 1)
        self.assertFalse(audits("staff_reactivate").exists())

    def test_s42_ac4_con_phieu_dang_giao_khong_cho_nghi(self):
        token_client(self.giao1)
        codes = []
        for code, phone in (("DH01", "0901000001"), ("DH02", "0901000002")):
            _o, _c, note = make_order_with_note(code, phone, assigned_to=self.giao1)
            note.status = DeliveryNote.Status.DELIVERING
            note.save(update_fields=["status"])
            codes.append(note.code)
        resp = self.post(self.chu, self.giao1, "deactivate")
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "BR-GH-08")
        self.assertIn("Còn 2 phiếu Đang giao", body["detail"])
        for code in codes:
            self.assertIn(code, body["detail"])
        self.giao1.refresh_from_db()
        self.assertTrue(self.giao1.is_active)
        self.assertTrue(Token.objects.filter(user=self.giao1).exists())
        self.assertFalse(audits("staff_deactivate").exists())

    def test_s42_ac5_superuser_cho_nghi_chu_cuoi_cung_400(self):
        root = User.objects.create_superuser("root", password="x")
        resp = self.post(client_for(root), self.loc, "deactivate")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(
            resp.json(), {"code": "BR-PQ-18", "detail": "Không thể cho nghỉ Chủ cuối cùng."}
        )
        self.loc.refresh_from_db()
        self.assertTrue(self.loc.is_active)

    def test_s42_ac5_con_chu_khac_thi_cho_nghi_duoc(self):
        chu_b = staff_user("chu_b", "chu")
        resp = self.post(self.chu, chu_b, "deactivate")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_s42_ac6_chu_tu_cho_nghi_minh_400(self):
        staff_user("chu_b", "chu")  # còn Chủ khác → lỗi phải là BR-PQ-17
        resp = self.post(self.chu, self.loc, "deactivate")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(
            resp.json(), {"code": "BR-PQ-17", "detail": "Không thể tự cho nghỉ chính mình."}
        )
        self.loc.refresh_from_db()
        self.assertTrue(self.loc.is_active)

    def test_s42_ac7_ql9_cho_nghi_hoac_lam_lai_tai_khoan_chu_403(self):
        chu_b = staff_user("chu_b", "chu")
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        resp = self.post(client_for(ql9), self.loc, "deactivate")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(
            resp.json(),
            {"code": "BR-PQ-17", "detail": "Chỉ Chủ mới thao tác trên tài khoản Chủ."},
        )
        self.loc.refresh_from_db()
        self.assertTrue(self.loc.is_active)
        chu_b.is_active = False
        chu_b.save()
        self.assertEqual(self.post(client_for(ql9), chu_b, "reactivate").status_code, 403)

    def test_s42_ql9_cho_nghi_nhan_vien_thuong_duoc(self):
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        self.assertEqual(self.post(client_for(ql9), self.giao1, "deactivate").status_code, 200)


class S42ResetPasswordTests(S42Base):
    def test_s42_ac3_dat_lai_mat_khau_thu_token_mat_khau_moi_dang_nhap_duoc(self):
        machine = token_client(self.kho1)
        self.assertEqual(machine.get(ME_URL).status_code, 200)
        resp = self.post(self.chu, self.kho1, "reset-password", {"new_password": NEW_PASSWORD})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json(), {})
        self.assertEqual(machine.get(ME_URL).status_code, 401)
        self.assertEqual(login("kho1", STRONG_PASSWORD)[0], 400)
        self.assertEqual(login("kho1", NEW_PASSWORD)[0], 200)

    def test_s42_ac3_audit_khong_chua_mat_khau(self):
        self.post(self.chu, self.kho1, "reset-password", {"new_password": NEW_PASSWORD})
        log = audits("staff_password_reset").get()
        self.assertEqual(log.actor, self.loc)
        self.assertEqual(log.object_id, str(self.kho1.pk))
        dumped = json.dumps(log.changes, ensure_ascii=False) + log.note + log.object_repr
        self.assertNotIn(NEW_PASSWORD, dumped)
        self.assertNotIn(User.objects.get(pk=self.kho1.pk).password, dumped)
        for other in AuditLog.objects.all():
            self.assertNotIn(NEW_PASSWORD, json.dumps(other.changes, ensure_ascii=False))

    def test_s42_mat_khau_yeu_400_khong_doi_token_con(self):
        token_client(self.kho1)
        for bad in ("abc", "password123", "12345678901", "", None):
            resp = self.post(self.chu, self.kho1, "reset-password", {"new_password": bad})
            self.assertEqual(resp.status_code, 400, (bad, resp.content))
        resp = self.post(self.chu, self.kho1, "reset-password", {"new_password": "Ab1!x"})
        self.assertIn("ít nhất 8 ký tự", resp.json()["detail"])
        self.assertEqual(login("kho1", STRONG_PASSWORD)[0], 200)
        self.assertFalse(audits("staff_password_reset").exists())

    def test_s42_field_la_trong_reset_password_400(self):
        resp = self.post(
            self.chu, self.kho1, "reset-password",
            {"new_password": NEW_PASSWORD, "username": "loc"},
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(login("kho1", STRONG_PASSWORD)[0], 200)

    def test_s42_khong_tu_dat_lai_mat_khau_cua_minh_qua_endpoint_nay(self):
        resp = self.post(self.chu, self.loc, "reset-password", {"new_password": NEW_PASSWORD})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-17")

    def test_s42_ac7_ql9_dat_lai_mat_khau_chu_403(self):
        ql9 = make_user("ql9", "quan_ly", perms=("accounts.manage_staff",))
        resp = self.post(client_for(ql9), self.loc, "reset-password", {"new_password": NEW_PASSWORD})
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(
            resp.json(),
            {"code": "BR-PQ-17", "detail": "Chỉ Chủ mới thao tác trên tài khoản Chủ."},
        )
        self.assertFalse(User.objects.get(pk=self.loc.pk).check_password(NEW_PASSWORD))

    def test_s42_chu_khong_superuser_khong_dat_lai_mat_khau_superuser(self):
        root = User.objects.create_superuser("root", password="x")
        resp = self.post(self.chu, root, "reset-password", {"new_password": NEW_PASSWORD})
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.json()["code"], "BR-PQ-17")
        self.assertTrue(User.objects.get(pk=root.pk).check_password("x"))
        self.assertEqual(self.post(self.chu, root, "deactivate").status_code, 403)


class S42PermissionTests(S42Base):
    def test_s42_ac8_delete_405_khong_xoa(self):
        resp = self.chu.delete(detail_url(self.giao1))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(User.objects.filter(pk=self.giao1.pk).exists())

    def test_s42_ac9_quan_ly_nv_kho_nv_giao_403(self):
        token_client(self.giao1)
        for username, group in (("ql1", "quan_ly"), ("kho2", "nv_kho"), ("giao2", "nv_giao")):
            client = client_for(make_user(username, group))
            for action, body in (("deactivate", {}), ("reactivate", {}),
                                 ("reset-password", {"new_password": NEW_PASSWORD})):
                resp = self.post(client, self.giao1, action, body)
                self.assertEqual(resp.status_code, 403, (username, action))
            self.assertEqual(client.delete(detail_url(self.giao1)).status_code, 403)
        self.giao1.refresh_from_db()
        self.assertTrue(self.giao1.is_active)
        self.assertTrue(self.giao1.check_password(STRONG_PASSWORD))
        self.assertTrue(Token.objects.filter(user=self.giao1).exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_s42_ac9_chua_dang_nhap_401(self):
        anon = client_for(None)
        for action in ("deactivate", "reactivate", "reset-password"):
            self.assertEqual(self.post(anon, self.giao1, action).status_code, 401)
