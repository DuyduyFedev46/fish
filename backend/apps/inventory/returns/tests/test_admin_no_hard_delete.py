"""
Duy quyết 03/10 #8: Django admin không được xoá cứng phiếu hoàn (BR-PQ-10, bất biến 3).
Chỉ có xoá mềm qua API `/delete/`. Dữ liệu giả.
"""
from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from apps.inventory.models import ReturnToStock


class ReturnAdminNoHardDeleteTests(TestCase):
    def test_superuser_has_no_delete_permission_on_return_admin(self):
        superuser = User.objects.create_superuser("root_x", password="x")
        request = RequestFactory().get("/admin/")
        request.user = superuser
        model_admin = admin.site._registry[ReturnToStock]
        self.assertFalse(model_admin.has_delete_permission(request))
        self.assertNotIn("delete_selected", model_admin.get_actions(request))
