"""B4 · Điểm dừng 02b §5.2: nhóm Nhân viên giao còn đủ quyền cho việc giao hàng (Lô 4: B5, B6, R4)."""
from django.test import TestCase

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user

from .base import group_perms

REQUIRED = {
    "delivery.view_deliverynote",    # xem phiếu được gán (R4)
    "delivery.change_deliverynote",  # báo kết quả giao, báo giao thất bại kèm lý do (B5)
    "sales.view_salesorder",         # đơn trong phạm vi được gán
}


class DeliveryStaffKeepsPermissionsTests(TestCase):
    def test_delivery_staff_still_has_every_permission_the_delivery_screens_need(self):
        self.assertTrue(REQUIRED <= group_perms(roles.DELIVERY_STAFF),
                        REQUIRED - group_perms(roles.DELIVERY_STAFF))

    def test_delivery_staff_cannot_assign_deliveries_b6_is_owner_and_manager_only(self):
        self.assertNotIn("delivery.assign_deliverynote", group_perms(roles.DELIVERY_STAFF))
        self.assertIn("delivery.assign_deliverynote", group_perms(roles.OWNER))
        self.assertIn("delivery.assign_deliverynote", group_perms(roles.MANAGER))

    def test_delivery_staff_can_still_open_delivery_notes_and_my_orders(self):
        client = client_for(make_user("giao1", roles.DELIVERY_STAFF))
        self.assertEqual(client.get("/api/delivery/notes/").status_code, 200)
        self.assertEqual(client.get("/api/sales/orders/").status_code, 200)
