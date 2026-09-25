"""
QA Q1 — đồng thời ở /api/staff/ (BR-PQ-08, BR-PQ-18).

- Hai request tạo cùng username: request thua gặp IntegrityError ở DB → phải thành 400 BR-PQ-08,
  không 500, không tạo hồ sơ/AuditLog thừa. Giả lập "đua" bằng cách vô hiệu bước kiểm trước.
- Cho nghỉ / đổi nhóm: khoá dòng User theo thứ tự cố định (pk tăng dần, một câu lệnh) gồm
  người bị thao tác + mọi Chủ đang làm → hai Chủ cho nghỉ nhau cùng lúc không deadlock.
  SQLite không có FOR UPDATE nên chỉ kiểm được thứ tự khoá qua helper; TransactionTestCase
  trên Postgres còn nợ.
"""
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts.models import AuditLog, StaffProfile
from apps.accounts.staff import services

from .helpers import LIST_URL, STRONG_PASSWORD, client_for, detail_url, staff_user


class Q1CreateRaceTests(TestCase):
    def setUp(self):
        self.loc = staff_user("loc", "chu")
        self.chu = client_for(self.loc)
        staff_user("giao4", "nv_giao")  # request "thắng" đã insert xong

    def test_q1_trung_username_dong_thoi_400_br_pq_08(self):
        with mock.patch.object(services, "_username_taken", return_value=False):
            resp = self.chu.post(
                LIST_URL,
                {"username": "giao4", "phone": "0909333444", "groups": ["nv_giao"],
                 "password": STRONG_PASSWORD},
                format="json",
            )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(
            resp.json(), {"code": "BR-PQ-08", "detail": "Tên đăng nhập đã tồn tại."}
        )
        self.assertEqual(User.objects.filter(username="giao4").count(), 1)
        self.assertEqual(StaffProfile.objects.filter(user__username="giao4").count(), 1)
        self.assertFalse(AuditLog.objects.filter(action="staff_create").exists())


class Q1LockOrderTests(TestCase):
    def setUp(self):
        self.loc = staff_user("loc", "chu")
        self.chu2 = staff_user("chu2", "chu")
        self.kho1 = staff_user("kho1", "nv_kho")

    def test_q1_khoa_nguoi_bi_thao_tac_va_cac_chu_theo_pk_tang_dan(self):
        locked_ids, target = services._lock_target_and_chus(self.kho1)
        self.assertEqual(locked_ids, sorted({self.loc.pk, self.chu2.pk, self.kho1.pk}))
        self.assertEqual(target.pk, self.kho1.pk)

    def test_q1_deactivate_khoa_mot_lan_duy_nhat(self):
        real = services._lock_target_and_chus
        with mock.patch.object(services, "_lock_target_and_chus", side_effect=real) as spy:
            resp = client_for(self.loc).post(detail_url(self.chu2, "deactivate/"), {},
                                             format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        spy.assert_called_once()

    def test_q1_set_groups_khoa_mot_lan_duy_nhat(self):
        real = services._lock_target_and_chus
        with mock.patch.object(services, "_lock_target_and_chus", side_effect=real) as spy:
            resp = client_for(self.loc).put(detail_url(self.chu2, "groups/"),
                                            {"groups": ["quan_ly"]}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        spy.assert_called_once()

    def test_q1_br_pq_18_van_giu_khi_hai_chu(self):
        # Sau khi loc cho chu2 nghỉ, chu2 (nếu request đến sau) không thể cho loc nghỉ.
        client_for(self.loc).post(detail_url(self.chu2, "deactivate/"), {}, format="json")
        root = User.objects.create_superuser("root", password="x")
        resp = client_for(root).post(detail_url(self.loc, "deactivate/"), {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-PQ-18")
