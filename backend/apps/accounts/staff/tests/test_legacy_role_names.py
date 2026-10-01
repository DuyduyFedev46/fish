"""
P8b Lô 4a (R5): đường GHI nhận tên Group cũ (`LEGACY_ROLE_NAMES`) cho client FE cũ còn mở trong lúc Lô 4 đang triển khai.

Tên cũ được chuẩn hoá sang tên mới TRƯỚC khi lưu; kết quả lưu và mức quyền giống hệt khi gửi tên mới.
"""
from apps.accounts import roles
from apps.accounts.staff.tests.helpers import detail_url, group_names, staff_user
from apps.common.tests.fixtures import client_for, make_user
from django.test import TestCase

LIST_URL = "/api/staff/"
OLD = {
    "owner": "chu",  # naming: allow - tên Group cũ
    "manager": "quan_ly",  # naming: allow - tên Group cũ
    "warehouse_staff": "nv_kho",  # naming: allow - tên Group cũ
    "delivery_staff": "nv_giao",  # naming: allow - tên Group cũ
    "customer_service": "cskh",  # naming: allow - tên Group cũ
}


class LegacyRoleNameWriteTests(TestCase):
    def setUp(self):
        self.owner = staff_user("legacy_chief", roles.OWNER)
        self.client = client_for(self.owner)

    def test_p8b_l4_put_groups_with_old_names_stores_new_names(self):
        target = staff_user("legacy_target", roles.DELIVERY_STAFF, phone="0900000001")
        resp = self.client.put(
            detail_url(target, "groups/"),
            {"groups": [OLD["warehouse_staff"], OLD["customer_service"]]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(sorted(group_names(target)), sorted([roles.WAREHOUSE_STAFF, roles.CUSTOMER_SERVICE]))
        self.assertEqual(sorted(resp.json()["groups"]), sorted([roles.WAREHOUSE_STAFF, roles.CUSTOMER_SERVICE]))
        self.assertEqual(sorted(resp.json()["added"]), sorted([roles.WAREHOUSE_STAFF, roles.CUSTOMER_SERVICE]))
        self.assertEqual(resp.json()["removed"], [roles.DELIVERY_STAFF])

    def test_p8b_l4_old_and_new_names_give_identical_stored_result(self):
        a = staff_user("legacy_same_a", phone="0900000002")
        b = staff_user("legacy_same_b", phone="0900000003")
        self.client.put(detail_url(a, "groups/"), {"groups": [OLD["manager"], OLD["delivery_staff"]]}, format="json")
        self.client.put(detail_url(b, "groups/"), {"groups": [roles.MANAGER, roles.DELIVERY_STAFF]}, format="json")
        self.assertEqual(group_names(a), group_names(b))
        self.assertEqual(
            sorted(a.get_all_permissions()), sorted(type(a).objects.get(pk=b.pk).get_all_permissions())
        )

    def test_p8b_l4_old_and_new_name_of_same_role_do_not_duplicate(self):
        target = staff_user("legacy_dup", phone="0900000004")
        resp = self.client.put(
            detail_url(target, "groups/"), {"groups": [OLD["manager"], roles.MANAGER]}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(group_names(target), [roles.MANAGER])

    def test_p8b_l4_create_staff_with_old_group_name(self):
        resp = self.client.post(
            LIST_URL,
            {
                "username": "legacy_new_hire",
                "display_name": "Nhân viên thử",
                "phone": "0900000005",
                "groups": [OLD["warehouse_staff"]],
                "password": "CaVe-Kho-2026!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["groups"], [roles.WAREHOUSE_STAFF])

    def test_p8b_l4_old_owner_name_still_requires_owner_actor(self):
        """BR-PQ-17: gán nhóm Chủ bằng tên cũ `chu` vẫn chỉ Chủ mới được (không lách bằng tên cũ)."""
        manager = staff_user("legacy_mgr", roles.MANAGER, phone="0900000006")
        target = staff_user("legacy_tgt2", phone="0900000007")
        resp = client_for(manager).put(
            detail_url(target, "groups/"), {"groups": [OLD["owner"]]}, format="json"
        )
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(group_names(target), [])

    def test_p8b_l4_unknown_group_name_is_still_rejected(self):
        target = staff_user("legacy_unknown", phone="0900000008")
        resp = self.client.put(detail_url(target, "groups/"), {"groups": ["khong_co"]}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-PQ-08")
