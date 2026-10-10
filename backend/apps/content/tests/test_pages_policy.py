"""
Kiểm thử Lô 5 CMS: Trang nội dung và phiên bản có hiệu lực (Story CMS-15-AC1..AC9, TD-3).
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.content.entries.services import (
    current_policy_version,
    effective_version,
    golive_missing_roles,
    publish_entry,
)
from apps.content.models.entries import Entry, EntryVersion
from apps.content.public.tests.test_public_api import assert_no_forbidden_keys
from apps.accounts import roles

User = get_user_model()


class PagesPolicyTests(APITestCase):
    def setUp(self):
        self.quan_ly = User.objects.create_user(username=roles.MANAGER, password="password")
        self.nv_kho = User.objects.create_user(username=roles.WAREHOUSE_STAFF, password="password")
        self.user_nd01 = User.objects.create_user(username="user_nd01", password="password")

        g_ql, _ = Group.objects.get_or_create(name=roles.MANAGER)
        g_kho, _ = Group.objects.get_or_create(name=roles.WAREHOUSE_STAFF)
        self.quan_ly.groups.add(g_ql)
        self.nv_kho.groups.add(g_kho)

        p_view = Permission.objects.get(codename="view_entry", content_type__app_label="content")
        p_change = Permission.objects.get(codename="change_entry", content_type__app_label="content")
        p_add = Permission.objects.get(codename="add_entry", content_type__app_label="content")
        self.user_nd01.user_permissions.add(p_view, p_change, p_add)
        for p in (p_view, p_change, p_add):
            g_ql.permissions.add(p)
        p_pub = Permission.objects.get(codename="publish_entry", content_type__app_label="content")
        g_ql.permissions.add(p_pub)

    def test_cms_15_ac1_create_and_publish_page_without_category_and_cover(self):
        """CMS-15-AC1: Tạo kind=page không chuyên mục, không ảnh bìa, Đăng -> 200, hiện ở /pages/?slug=..., không xuất hiện trong danh sách bài."""
        self.client.force_authenticate(user=self.quan_ly)
        res_create = self.client.post("/api/content/entries/", {
            "kind": "page",
            "title": "Chính sách bảo mật",
            "slug": "chinh-sach-bao-mat",
            "excerpt": "Cam kết bảo mật thông tin khách hàng",
            "body": {"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Nội dung bảo mật."}]}]},
            "page_role": "privacy",
            "show_in_footer": True,
            "footer_order": 1,
        }, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        entry_id = res_create.data["id"]

        res_pub = self.client.post(f"/api/content/entries/{entry_id}/publish/", {
            "row_version": res_create.data["row_version"],
            "checklist_confirmed": True,
        }, format="json")
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)
        self.assertEqual(res_pub.data["public_path"], "/pages/?slug=chinh-sach-bao-mat")

        self.client.logout()
        res_list = self.client.get("/api/public/content/entries/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertFalse(any(item["slug"] == "chinh-sach-bao-mat" for item in res_list.data["results"]))

        # Kiểm tra API công khai chi tiết bài
        res_detail = self.client.get("/api/public/content/entries/chinh-sach-bao-mat/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["title"], "Chính sách bảo mật")
        self.assertEqual(res_detail.data["kind"], "page")

    def test_cms_15_ac2_duplicate_page_role_rejected_br_nd_16(self):
        """CMS-15-AC2: Mỗi vai trò chỉ một trang (page_role trùng -> 400 BR-ND-16)."""
        Entry.objects.create(
            kind="page",
            title="Trang 1",
            slug="trang-1",
            page_role="privacy",
            created_by=self.quan_ly,
            row_version=1,
        )
        self.client.force_authenticate(user=self.quan_ly)
        res = self.client.post("/api/content/entries/", {
            "kind": "page",
            "title": "Trang 2",
            "slug": "trang-2",
            "page_role": "privacy",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "BR-ND-16")

    def test_cms_15_ac3_unpublish_policy_page_rejected_br_nd_16(self):
        """CMS-15-AC3: Trang privacy Đã đăng gọi gỡ -> 400 BR-ND-16."""
        page = Entry.objects.create(
            kind="page",
            title="Bảo mật",
            slug="bao-mat",
            page_role="privacy",
            status="published",
            first_published_at=timezone.now(),
            created_by=self.quan_ly,
            row_version=1,
        )
        self.client.force_authenticate(user=self.quan_ly)
        res = self.client.post(f"/api/content/entries/{page.pk}/unpublish/", {
            "row_version": page.row_version,
            "reason": "other",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "BR-ND-16")
        self.assertEqual(res.data.get("detail"), "Trang bắt buộc go-live chỉ sửa và đăng lại (BR-ND-16).")

    def test_cms_15_ac4_effective_version_3_timestamps_and_current_policy_version(self):
        """CMS-15-AC4: Gọi effective_version('privacy', at) theo 3 mốc thời gian."""
        page = Entry.objects.create(
            kind="page",
            title="Bảo mật",
            slug="bao-mat-policy",
            page_role="privacy",
            created_by=self.quan_ly,
            row_version=1,
        )
        t_base = timezone.now()
        t_v1 = t_base + timedelta(days=1)
        t_mid = t_base + timedelta(days=5)
        t_v2 = t_base + timedelta(days=10)
        t_after = t_base + timedelta(days=15)
        t_before = t_base - timedelta(days=1)

        v1 = EntryVersion.objects.create(
            entry=page,
            version=1,
            kind="page",
            title="Bảo mật v1",
            slug="bao-mat-policy",
            published_at=t_v1,
            published_by=self.quan_ly,
        )
        v2 = EntryVersion.objects.create(
            entry=page,
            version=2,
            kind="page",
            title="Bảo mật v2",
            slug="bao-mat-policy",
            published_at=t_v2,
            published_by=self.quan_ly,
        )

        self.assertIsNone(effective_version("privacy", at=t_before))
        self.assertEqual(effective_version("privacy", at=t_mid).version, 1)
        self.assertEqual(effective_version("privacy", at=t_after).version, 2)

        self.assertIsNone(current_policy_version("privacy"))
        page.status = "published"
        page.published_version = v2
        page.save(update_fields=["status", "published_version"])
        self.assertEqual(current_policy_version("privacy").version, 2)

    def test_cms_15_ac5_public_page_by_role_contract_and_forbidden_keys(self):
        """CMS-15-AC5: GET pages/by-role/privacy/ trả đúng các khoá trong contract, không rò khoá cấm."""
        page = Entry.objects.create(
            kind="page",
            title="Chính sách bảo mật",
            slug="chinh-sach-bao-mat-ac5",
            page_role="privacy",
            status="published",
            created_by=self.quan_ly,
            row_version=1,
        )
        ver = EntryVersion.objects.create(
            entry=page,
            version=3,
            kind="page",
            title="Chính sách bảo mật",
            slug="chinh-sach-bao-mat-ac5",
            published_at=timezone.now(),
            published_by=self.quan_ly,
        )
        page.published_version = ver
        page.save(update_fields=["published_version"])

        res = self.client.get("/api/public/content/pages/by-role/privacy/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        expected_keys = {"slug", "title", "version", "version_id", "effective_from"}
        self.assertEqual(set(res.data.keys()), expected_keys)
        self.assertEqual(res.data["version"], 3)
        self.assertEqual(res.data["version_id"], ver.pk)
        self.assertIn("Cache-Control", res)
        assert_no_forbidden_keys(self, res.data)

    def test_cms_15_ac6_public_footer_links_order_and_published_only(self):
        """CMS-15-AC6: GET footer-links trả đúng trang Đã đăng có show_in_footer theo thứ tự."""
        p1 = Entry.objects.create(
            kind="page",
            title="Trang 1",
            slug="t1",
            show_in_footer=True,
            footer_order=2,
            status="published",
            created_by=self.quan_ly,
            row_version=1,
        )
        v1 = EntryVersion.objects.create(
            entry=p1,
            version=1,
            kind="page",
            title="Trang 1 Title",
            slug="t1",
            published_at=timezone.now(),
            published_by=self.quan_ly,
        )
        p1.published_version = v1
        p1.save(update_fields=["published_version"])

        p2 = Entry.objects.create(
            kind="page",
            title="Trang 2",
            slug="t2",
            show_in_footer=True,
            footer_order=1,
            status="published",
            created_by=self.quan_ly,
            row_version=1,
        )
        v2 = EntryVersion.objects.create(
            entry=p2,
            version=1,
            kind="page",
            title="Trang 2 Title",
            slug="t2",
            published_at=timezone.now(),
            published_by=self.quan_ly,
        )
        p2.published_version = v2
        p2.save(update_fields=["published_version"])

        Entry.objects.create(
            kind="page",
            title="Trang nháp",
            slug="t-nhap",
            show_in_footer=True,
            footer_order=0,
            status="draft",
            created_by=self.quan_ly,
            row_version=1,
        )

        res = self.client.get("/api/public/content/footer-links/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        links = res.data
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["slug"], "t2")
        self.assertEqual(links[1]["slug"], "t1")
        for item in links:
            self.assertEqual(set(item.keys()), {"title", "slug"})

    def test_cms_15_ac7_golive_missing_roles_service_and_api(self):
        """CMS-15-AC7: golive_missing_roles() và GET /api/content/golive-status/ trả danh sách vai trò chưa có trang Đã đăng."""
        missing = golive_missing_roles()
        for r in ("privacy", "terms", "refund", "seller_info"):
            self.assertIn(r, missing)

        self.client.force_authenticate(user=self.quan_ly)
        res = self.client.get("/api/content/golive-status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # SHOP-5-02 (BR-ND-20): thêm shipping, payment, complaints.
        self.assertEqual(
            set(res.data["missing_roles"]),
            {"privacy", "terms", "refund", "seller_info", "shipping", "payment", "complaints"},
        )

    def test_cms_15_ac8_user_with_only_nd01_patch_policy_fields_forbidden_403(self):
        """CMS-15-AC8: User chỉ ND-01 PATCH page_role hoặc show_in_footer -> 403 BR-PQ-12 và không field nào bị đổi."""
        page = Entry.objects.create(
            kind="page",
            title="Trang mẫu",
            slug="trang-mau",
            created_by=self.quan_ly,
            row_version=1,
        )
        self.client.force_authenticate(user=self.user_nd01)
        res = self.client.patch(f"/api/content/entries/{page.pk}/", {
            "row_version": page.row_version,
            "title": "Tiêu đề mới",
            "page_role": "privacy",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("code"), "BR-PQ-12")
        page.refresh_from_db()
        self.assertEqual(page.title, "Trang mẫu")
        self.assertIsNone(page.page_role)

    def test_cms_15_ac9_nv_kho_golive_status_403_and_guest_401(self):
        """CMS-15-AC9: NV kho gọi GET golive-status -> 403 BR-PQ-12. Khách -> 401."""
        self.client.force_authenticate(user=self.nv_kho)
        res_kho = self.client.get("/api/content/golive-status/")
        self.assertEqual(res_kho.status_code, status.HTTP_403_FORBIDDEN)

        self.client.logout()
        res_guest = self.client.get("/api/content/golive-status/")
        self.assertEqual(res_guest.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_td_3_cannot_change_or_remove_page_role_of_published_entry(self):
        """TD-3: Trang bắt buộc go-live đang Đã đăng không được bỏ hoặc đổi vai trò (400 BR-ND-16)."""
        page = Entry.objects.create(
            kind="page",
            title="Bảo mật",
            slug="bao-mat-td3",
            page_role="privacy",
            status="published",
            created_by=self.quan_ly,
            row_version=1,
        )
        self.client.force_authenticate(user=self.quan_ly)
        res_remove = self.client.patch(f"/api/content/entries/{page.pk}/", {
            "row_version": page.row_version,
            "page_role": None,
        }, format="json")
        self.assertEqual(res_remove.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_remove.data.get("code"), "BR-ND-16")
