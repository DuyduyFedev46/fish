"""
P8b Lô 5: đường GHI không còn nhận tên Group cũ (chuẩn hoá `LEGACY_ROLE_NAMES` đã gỡ; Lô 4a từng nhận cho client FE cũ).

Tên cũ giờ giống tên lạ: 400 `BR-PQ-08`, không lưu gì, không đổi nhóm của ai. Tên mới vẫn dùng bình thường.
Gán nhóm Chủ chỉ Chủ được làm (BR-PQ-17) vẫn đúng với tên mới.
"""
from apps.accounts import roles
from apps.accounts.staff.tests.helpers import detail_url, group_names, staff_user
from apps.common.tests.fixtures import client_for
from django.contrib.auth.models import User
from django.test import TestCase

LIST_URL = "/api/staff/"
OLD = {
    "owner": "chu",
    "manager": "quan_ly",
    "warehouse_staff": "nv_kho",
    "delivery_staff": "nv_giao",
    "customer_service": "cskh",
}


class OldRoleNameWriteTests(TestCase):
    def setUp(self):
        self.owner = staff_user("old_name_chief", roles.OWNER)
        self.client = client_for(self.owner)

    def test_put_groups_with_each_old_name_is_rejected_and_changes_nothing(self):
        target = staff_user("old_name_target", roles.DELIVERY_STAFF, phone="0900000001")
        for new_name, old_name in OLD.items():
            with self.subTest(old=old_name):
                resp = self.client.put(detail_url(target, "groups/"), {"groups": [old_name]}, format="json")
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertEqual(resp.json()["code"], "BR-PQ-08")
                self.assertIn(old_name, resp.json()["detail"])
                self.assertEqual(group_names(target), [roles.DELIVERY_STAFF])

    def test_put_groups_mixing_new_and_old_name_is_rejected_as_a_whole(self):
        target = staff_user("old_name_mixed", roles.DELIVERY_STAFF, phone="0900000002")
        resp = self.client.put(
            detail_url(target, "groups/"), {"groups": [roles.MANAGER, OLD["warehouse_staff"]]}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(group_names(target), [roles.DELIVERY_STAFF])

    def test_put_groups_with_new_names_still_works(self):
        target = staff_user("old_name_ok", roles.DELIVERY_STAFF, phone="0900000003")
        resp = self.client.put(
            detail_url(target, "groups/"), {"groups": [roles.WAREHOUSE_STAFF, roles.CUSTOMER_SERVICE]}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            sorted(group_names(target)), sorted([roles.WAREHOUSE_STAFF, roles.CUSTOMER_SERVICE])
        )

    def test_create_staff_with_old_group_name_is_rejected_and_creates_no_user(self):
        before = User.objects.count()
        resp = self.client.post(
            LIST_URL,
            {
                "username": "old_name_new_hire",
                "display_name": "Nhân viên thử",
                "phone": "0900000005",
                "groups": [OLD["warehouse_staff"]],
                "password": "CaVe-Kho-2026!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(User.objects.count(), before)
        self.assertFalse(User.objects.filter(username="old_name_new_hire").exists())

    def test_manager_cannot_grant_owner_by_old_name_either(self):
        """BR-PQ-17: tên cũ `chu` không phải đường vòng để Quản lý gán nhóm Chủ; không có nhóm nào được gán."""
        manager = staff_user("old_name_mgr", roles.MANAGER, phone="0900000006")
        target = staff_user("old_name_tgt2", phone="0900000007")
        resp = client_for(manager).put(detail_url(target, "groups/"), {"groups": [OLD["owner"]]}, format="json")
        self.assertIn(resp.status_code, (400, 403), resp.content)
        self.assertEqual(group_names(target), [])

    def test_manager_cannot_grant_owner_by_new_name(self):
        manager = staff_user("old_name_mgr2", roles.MANAGER, phone="0900000008")
        target = staff_user("old_name_tgt3", phone="0900000009")
        resp = client_for(manager).put(detail_url(target, "groups/"), {"groups": [roles.OWNER]}, format="json")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(group_names(target), [])

    def test_unknown_group_name_is_rejected(self):
        target = staff_user("old_name_unknown", phone="0900000010")
        resp = self.client.put(detail_url(target, "groups/"), {"groups": ["khong_co"]}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-PQ-08")

    def test_roles_module_has_no_old_name_normalizer(self):
        self.assertFalse(hasattr(roles, "LEGACY_ROLE_NAMES"))
        self.assertFalse(hasattr(roles, "normalize_role_name"))
