"""
Kiểm thử nghiệp vụ chuyên mục (CMS-02-AC1..AC6, §4.7, §8.2 02b-tech-design).
"""
from django.test import TestCase
from rest_framework import status

from apps.common.tests.fixtures import client_for, make_user
from apps.content.models import Category, Entry
from apps.content.permissions import (
    PERM_ADD_ENTRY,
    PERM_CHANGE_ENTRY,
    PERM_DELETE_ENTRY,
    PERM_VIEW_CATEGORY,
    PERM_VIEW_ENTRY,
)


class CategoryApiTests(TestCase):
    def setUp(self):
        self.user_ql = make_user("test_ql_cat", "quan_ly")
        self.user_nd01_only = make_user(
            "test_nd01_only",
            perms=[
                PERM_VIEW_CATEGORY,
                PERM_VIEW_ENTRY,
                PERM_ADD_ENTRY,
                PERM_CHANGE_ENTRY,
                PERM_DELETE_ENTRY,
            ],
        )
        self.client_ql = client_for(self.user_ql)

    def test_cms_02_ac1_create_category(self):
        """CMS-02-AC1: Tạo chuyên mục 'Công thức nấu' -> 201, slug 'cong-thuc-nau', order tăng dần."""
        resp = self.client_ql.post(
            "/api/content/categories/",
            {"name": "Công thức nấu", "description": "Hướng dẫn chế biến", "order": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "Công thức nấu")
        self.assertEqual(resp.data["slug"], "cong-thuc-nau")
        self.assertEqual(resp.data["order"], 1)
        self.assertTrue(resp.data["is_active"])
        self.assertEqual(resp.data["published_count"], 0)

        # Kiểm tra danh sách trả về theo order
        Category.objects.create(name="Tin tức", name_key="tin tuc", slug="tin-tuc", order=0)
        list_resp = self.client_ql.get("/api/content/categories/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in list_resp.data]
        self.assertEqual(names, ["Tin tức", "Công thức nấu"])

    def test_cms_02_ac2_duplicate_name_case_and_accents(self):
        """CMS-02-AC2: Đã có 'Công thức nấu' -> Tạo 'cong thuc NẤU' -> 400 BR-ND-04."""
        self.client_ql.post(
            "/api/content/categories/",
            {"name": "Công thức nấu", "order": 1},
            format="json",
        )
        count_before = Category.objects.count()

        resp = self.client_ql.post(
            "/api/content/categories/",
            {"name": "cong thuc NẤU", "order": 2},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data.get("code"), "BR-ND-04")
        self.assertEqual(Category.objects.count(), count_before)

    def test_cms_02_ac3_rename_keeps_slug(self):
        """CMS-02-AC3: Chuyên mục có 2 bài Đã đăng -> Đổi tên thành 'Món ngon' -> 200, slug không đổi."""
        resp = self.client_ql.post(
            "/api/content/categories/",
            {"name": "Công thức", "order": 1},
            format="json",
        )
        cat_id = resp.data["id"]
        cat = Category.objects.get(id=cat_id)
        self.assertEqual(cat.slug, "cong-thuc")

        # Tạo 2 bài published thuộc chuyên mục
        for i in range(2):
            Entry.objects.create(
                title=f"Bài {i}",
                slug=f"bai-{i}",
                category=cat,
                status="published",
                created_by=self.user_ql,
            )

        patch_resp = self.client_ql.patch(
            f"/api/content/categories/{cat_id}/",
            {"name": "Món ngon", "order": 2},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Món ngon")
        self.assertEqual(cat.slug, "cong-thuc", "Slug phải giữ nguyên khi đổi tên")
        self.assertEqual(cat.order, 2)
        self.assertEqual(patch_resp.data["published_count"], 2)

    def test_cms_02_ac4_deactivate_blocked_when_published_entries_exist(self):
        """
        CMS-02-AC4: Chuyên mục còn 7 bài Đã đăng -> Đặt is_active=false -> 400 BR-ND-02,
        trả tối đa 5 bài kèm total: 7; chuyên mục vẫn hoạt động.
        """
        cat = Category.objects.create(
            name="Hải sản tươi",
            name_key="hai san tuoi",
            slug="hai-san-tuoi",
            order=1,
            is_active=True,
        )

        for i in range(7):
            Entry.objects.create(
                title=f"Mẹo chọn cá {i}",
                slug=f"meo-chon-ca-{i}",
                category=cat,
                status="published",
                created_by=self.user_ql,
            )

        resp = self.client_ql.patch(
            f"/api/content/categories/{cat.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data.get("code"), "BR-ND-02")
        self.assertEqual(resp.data.get("total"), 7)
        entries_returned = resp.data.get("entries", [])
        self.assertEqual(len(entries_returned), 5, "Chỉ trả tối đa 5 bài trong extra")
        for item in entries_returned:
            self.assertIn("id", item)
            self.assertIn("title", item)

        cat.refresh_from_db()
        self.assertTrue(cat.is_active, "Chuyên mục phải vẫn hoạt động sau khi bị chặn")

    def test_cms_02_ac5_deactivate_allowed_when_only_draft_or_unpublished(self):
        """CMS-02-AC5: Chỉ còn bài draft hoặc unpublished -> Ngừng dùng 200; DELETE trả 405."""
        cat = Category.objects.create(
            name="Chuyên mục cũ",
            name_key="chuyen muc cu",
            slug="chuyen-muc-cu",
            order=1,
            is_active=True,
        )
        Entry.objects.create(
            title="Bài nháp",
            slug="bai-nhap",
            category=cat,
            status="draft",
            created_by=self.user_ql,
        )
        Entry.objects.create(
            title="Bài đã gỡ",
            slug="bai-da-go",
            category=cat,
            status="unpublished",
            created_by=self.user_ql,
        )

        resp = self.client_ql.patch(
            f"/api/content/categories/{cat.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cat.refresh_from_db()
        self.assertFalse(cat.is_active)

        # DELETE -> 405 MethodNotAllowed
        del_resp = self.client_ql.delete(f"/api/content/categories/{cat.id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cms_02_ac6_user_with_only_nd01_permissions(self):
        """CMS-02-AC6: User chỉ có ND-01 -> GET 200 (để chọn khi soạn); POST 403, không tạo dòng."""
        cat = Category.objects.create(
            name="Đặc sản",
            name_key="dac san",
            slug="dac-san",
            order=1,
            is_active=True,
        )
        client_nd01 = client_for(self.user_nd01_only)

        # GET 200
        get_resp = client_nd01.get("/api/content/categories/")
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(get_resp.data), 1)

        # POST 403
        count_before = Category.objects.count()
        post_resp = client_nd01.post(
            "/api/content/categories/",
            {"name": "Đặc sản 2", "order": 2},
            format="json",
        )
        self.assertEqual(post_resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Category.objects.count(), count_before)
