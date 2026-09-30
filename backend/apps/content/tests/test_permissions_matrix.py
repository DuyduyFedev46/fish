"""
Kiểm tra ma trận phân quyền app content (CMS-01-AC1, AC2, AC3, §3 02b-tech-design).
"""
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.tests.fixtures import client_for, make_user
from apps.content.models import Category, ContentImage, Entry, EntryVersion
from apps.content.permissions import CONTENT_ALL_PERMS
from apps.accounts import roles


class ContentPermissionsMatrixTests(TestCase):
    def setUp(self):
        self.user_chu = make_user("test_chu", roles.OWNER)
        self.user_quan_ly = make_user("test_ql", roles.MANAGER)
        self.user_nv_kho = make_user("test_kho", roles.WAREHOUSE_STAFF)
        self.user_nv_giao = make_user("test_giao", roles.DELIVERY_STAFF)

        # Tạo sẵn 1 category để test endpoint detail
        self.cat = Category.objects.create(
            name="Món ngon",
            name_key="mon ngon",
            slug="mon-ngon",
            order=1,
            is_active=True,
        )

    def test_cms_01_ac1_group_permissions(self):
        """CMS-01-AC1: chu và quan_ly có đủ 8 quyền; nv_kho và nv_giao không có quyền nào."""
        group_chu = Group.objects.get(name=roles.OWNER)
        group_ql = Group.objects.get(name=roles.MANAGER)
        group_kho = Group.objects.get(name=roles.WAREHOUSE_STAFF)
        group_giao = Group.objects.get(name=roles.DELIVERY_STAFF)

        for perm_code in CONTENT_ALL_PERMS:
            app_label, codename = perm_code.split(".")
            self.assertTrue(
                group_chu.permissions.filter(content_type__app_label=app_label, codename=codename).exists(),
                f"Group chu thiếu quyền {perm_code}",
            )
            self.assertTrue(
                group_ql.permissions.filter(content_type__app_label=app_label, codename=codename).exists(),
                f"Group quan_ly thiếu quyền {perm_code}",
            )

        # nv_kho và nv_giao không có bất kỳ quyền nào của content
        self.assertFalse(group_kho.permissions.filter(content_type__app_label="content").exists())
        self.assertFalse(group_giao.permissions.filter(content_type__app_label="content").exists())

    def test_cms_01_ac2_nv_kho_nv_giao_endpoints(self):
        """
        CMS-01-AC2: Token NV kho, rồi token NV giao gọi từng endpoint /api/content/**:
        - Method hỗ trợ -> 403
        - Method không hỗ trợ -> 405
        - Số dòng mọi bảng content không đổi.
        """
        initial_counts = (
            Category.objects.count(),
            Entry.objects.count(),
            EntryVersion.objects.count(),
            ContentImage.objects.count(),
        )

        endpoints_supported = [
            ("get", "/api/content/categories/"),
            ("post", "/api/content/categories/", {"name": "Test"}),
            ("patch", f"/api/content/categories/{self.cat.id}/", {"name": "Test 2"}),
            ("get", "/api/content/entries/"),
            ("get", "/api/content/entries/counts/"),
        ]

        endpoints_unsupported = [
            ("delete", f"/api/content/categories/{self.cat.id}/"),
            ("put", f"/api/content/categories/{self.cat.id}/", {"name": "Test"}),
        ]

        for user in [self.user_nv_kho, self.user_nv_giao]:
            client = client_for(user)
            # Method hỗ trợ -> 403
            for method, path, *args in endpoints_supported:
                data = args[0] if args else {}
                call_func = getattr(client, method)
                resp = call_func(path, data, format="json") if method in ("post", "patch") else call_func(path)
                self.assertEqual(
                    resp.status_code,
                    status.HTTP_403_FORBIDDEN,
                    f"User {user.username} {method.upper()} {path} phải nhận 403, nhận {resp.status_code}",
                )

            # Method không hỗ trợ -> 405
            for method, path, *args in endpoints_unsupported:
                data = args[0] if args else {}
                call_func = getattr(client, method)
                resp = call_func(path, data, format="json") if method in ("put",) else call_func(path)
                self.assertEqual(
                    resp.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                    f"User {user.username} {method.upper()} {path} phải nhận 405, nhận {resp.status_code}",
                )

        current_counts = (
            Category.objects.count(),
            Entry.objects.count(),
            EntryVersion.objects.count(),
            ContentImage.objects.count(),
        )
        self.assertEqual(initial_counts, current_counts, "Số dòng bảng content không được đổi")

    def test_cms_01_ac3_unauthenticated_401(self):
        """CMS-01-AC3: Khách không đăng nhập -> 401; không dữ liệu nào trả về."""
        client = APIClient()
        endpoints = [
            ("get", "/api/content/categories/"),
            ("post", "/api/content/categories/"),
            ("patch", f"/api/content/categories/{self.cat.id}/"),
            ("get", "/api/content/entries/"),
            ("get", "/api/content/entries/counts/"),
        ]
        for method, path in endpoints:
            call_func = getattr(client, method)
            resp = call_func(path, {}, format="json") if method in ("post", "patch") else call_func(path)
            self.assertEqual(
                resp.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Guest {method.upper()} {path} phải nhận 401, nhận {resp.status_code}",
            )
