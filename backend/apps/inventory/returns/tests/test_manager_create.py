"""Lô bổ sung A (Duy chốt 02/10, #21): Quản lý được quyền tạo phiếu hàng hoàn (`inventory.add_returntostock`)."""
from apps.inventory.models import ReturnToStock

from .base import ReturnsApiBase


class ManagerCanCreateReturnTests(ReturnsApiBase):
    def test_return_add_manager_has_permission_and_creates(self):
        self.assertTrue(self.manager.has_perm("inventory.add_returntostock"))
        resp = self.post(self.manager, self.payload(qty="3"))
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(ReturnToStock.objects.get(pk=resp.json()["id"]).created_by, self.manager)

    def test_return_add_customer_service_and_no_group_still_forbidden(self):
        for user in (self.customer_service, self.no_group):
            self.assertFalse(user.has_perm("inventory.add_returntostock"), user.username)
            self.assertEqual(self.post(user, self.payload()).status_code, 403, user.username)
        self.assertFalse(ReturnToStock.objects.exists())

    def test_return_add_manager_still_has_approve_and_no_delete(self):
        self.assertTrue(self.manager.has_perm("inventory.approve_returntostock"))
        self.assertFalse(self.manager.has_perm("inventory.delete_returntostock"))
