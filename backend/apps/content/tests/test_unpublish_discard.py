"""
Kiểm thử CMS-12 (Gỡ bài viết/trang) và CMS-10 (Sửa nháp bài đang đăng & huỷ thay đổi, append-only EntryVersion).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.exceptions import BusinessError
from apps.accounts.models import AuditLog
from apps.content.entries.services import publish_entry
from apps.content.models.categories import Category
from apps.content.models.entries import Entry, EntryVersion
from apps.content.models.images import ContentImage

User = get_user_model()


class UnpublishAndDiscardTests(APITestCase):
    def setUp(self):
        self.quan_ly = User.objects.create_user(username="quan_ly_user", password="password")
        self.nv_kho = User.objects.create_user(username="nv_kho_user", password="password")
        self.nv_giao = User.objects.create_user(username="nv_giao_user", password="password")
        self.user_nd01 = User.objects.create_user(username="user_nd01", password="password")

        g_ql, _ = Group.objects.get_or_create(name="quan_ly")
        g_kho, _ = Group.objects.get_or_create(name="nv_kho")
        g_giao, _ = Group.objects.get_or_create(name="nv_giao")
        self.quan_ly.groups.add(g_ql)
        self.nv_kho.groups.add(g_kho)
        self.nv_giao.groups.add(g_giao)

        from django.contrib.auth.models import Permission
        p_view = Permission.objects.get(codename="view_entry", content_type__app_label="content")
        p_change = Permission.objects.get(codename="change_entry", content_type__app_label="content")
        self.user_nd01.user_permissions.add(p_view, p_change)


        self.category = Category.objects.create(
            name="Mẹo nhà bếp",
            name_key="meo nha bep",
            slug="meo-nha-bep",
            order=1,
            is_active=True,
        )

        self.entry = Entry.objects.create(
            kind="post",
            status="draft",
            title="Cách làm sạch mang cá",
            slug="cach-lam-sach-mang-ca",
            category=self.category,
            excerpt="Hướng dẫn rửa sạch mang cá không còn mùi tanh.",
            seo_title="Mẹo làm sạch mang cá | Cá Về",
            seo_description="Bí quyết rửa sạch nhớt và máu tanh ở mang cá biển.",
            body={
                "type": "doc",
                "blocks": [
                    {
                        "type": "paragraph",
                        "children": [{"text": "Dùng muối hạt xát nhẹ vào mang cá rồi rửa lại bằng nước sạch."}],
                    }
                ],
            },
            source="human",
            row_version=1,
            created_by=self.quan_ly,
            updated_by=self.quan_ly,
        )

        self.cover_image = ContentImage.objects.create(
            entry=self.entry,
            alt="Đĩa cá tươi đã làm sạch",
            width=1600,
            height=1200,
            uploaded_by=self.quan_ly,
        )
        self.entry.cover_image = self.cover_image
        self.entry.save()

        # Xuất bản lần đầu
        publish_entry(
            entry=self.entry,
            actor=self.quan_ly,
            row_version=self.entry.row_version,
            checklist_confirmed=True,
            acknowledge_warnings=False,
        )
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "published")
        self.assertEqual(self.entry.published_version.version, 1)

    # =========================================================================
    # CMS-12: Gỡ bài viết
    # =========================================================================

    def test_cms_12_ac1_unpublish_published_entry_success(self):
        """CMS-12-AC1: Gỡ bài đang published với lý do hợp lệ -> 200, status=unpublished."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/unpublish/"

        res = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "reason": "wrong_price",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data.get("status"), "unpublished")

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "unpublished")
        self.assertEqual(self.entry.return_reason, "wrong_price")

    def test_cms_12_ac1_err_missing_or_invalid_reason(self):
        """CMS-12-AC1: Thiếu hoặc sai lý do gỡ -> 400 BR-ND-15."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/unpublish/"

        # Thiếu lý do
        res1 = self.client.post(url, {"row_version": self.entry.row_version}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res1.data.get("code"), "BR-ND-15")

        # Lý do không thuộc danh mục
        res2 = self.client.post(
            url,
            {"row_version": self.entry.row_version, "reason": "khong_thich_nua"},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res2.data.get("code"), "BR-ND-15")

    def test_cms_12_ac2_audit_log_format(self):
        """CMS-12-AC2: Ghi AuditLog 1 dòng content_unpublish chứa entry_id, version, reason; không ghi text bài."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/unpublish/"

        before_count = AuditLog.objects.count()
        res = self.client.post(
            url,
            {"row_version": self.entry.row_version, "reason": "complaint"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(AuditLog.objects.count(), before_count + 1)
        log = AuditLog.objects.latest("id")
        self.assertEqual(log.action, "content_unpublish")
        self.assertEqual(log.object_repr, f"Nội dung #{self.entry.pk}")
        self.assertEqual(log.changes.get("entry_id"), self.entry.pk)
        self.assertEqual(log.changes.get("version"), 1)
        self.assertEqual(log.changes.get("reason"), "complaint")
        # Không chứa text bài hay slug
        self.assertNotIn("title", log.changes)
        self.assertNotIn("body", log.changes)
        self.assertNotIn("slug", log.changes)

    def test_cms_12_ac3_public_api_immediately_returns_410(self):
        """CMS-12-AC3: Sau khi gỡ, API công khai ngay lập tức trả 410 GONE kèm Cache-Control."""
        self.client.force_authenticate(user=self.quan_ly)
        url_unpub = f"/api/content/entries/{self.entry.pk}/unpublish/"
        self.client.post(url_unpub, {"row_version": self.entry.row_version, "reason": "other"}, format="json")

        self.client.logout()
        url_pub = f"/api/public/content/entries/{self.entry.slug}/"
        res_pub = self.client.get(url_pub)
        self.assertEqual(res_pub.status_code, status.HTTP_410_GONE)
        self.assertEqual(res_pub.data.get("code"), "GONE")
        self.assertEqual(res_pub.data.get("detail"), "Bài này không còn trên web.")
        self.assertIn("Cache-Control", res_pub)
        self.assertIn("max-age=60", res_pub["Cache-Control"])

    def test_cms_12_ac4_republish_same_slug_creates_version_n_plus_1(self):
        """CMS-12-AC4: Đăng lại bài đã gỡ -> tạo phiên bản 2, AuditLog ghi content_republish."""
        self.client.force_authenticate(user=self.quan_ly)
        url_unpub = f"/api/content/entries/{self.entry.pk}/unpublish/"
        self.client.post(url_unpub, {"row_version": self.entry.row_version, "reason": "wrong_price"}, format="json")

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "unpublished")

        # Đăng lại
        url_pub = f"/api/content/entries/{self.entry.pk}/publish/"
        res_repub = self.client.post(
            url_pub,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
            },
            format="json",
        )
        self.assertEqual(res_repub.status_code, status.HTTP_200_OK)
        self.assertEqual(res_repub.data.get("version"), 2)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "published")
        self.assertEqual(self.entry.published_version.version, 2)

        log = AuditLog.objects.latest("id")
        self.assertEqual(log.action, "content_republish")
        self.assertEqual(log.changes.get("version"), 2)

    def test_cms_12_ac5_delete_unpublished_entry_rejected_br_nd_02(self):
        """CMS-12-AC5: DELETE bài đã gỡ -> 400 BR-ND-02 (không thể xoá bài đã từng đăng)."""
        self.client.force_authenticate(user=self.quan_ly)
        url_unpub = f"/api/content/entries/{self.entry.pk}/unpublish/"
        self.client.post(url_unpub, {"row_version": self.entry.row_version, "reason": "other"}, format="json")

        url_del = f"/api/content/entries/{self.entry.pk}/"
        res_del = self.client.delete(url_del)
        self.assertEqual(res_del.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_del.data.get("code"), "BR-ND-02")

    def test_cms_12_ac6_permissions_unpublish_forbidden_403(self):
        """CMS-12-AC7: User chỉ có ND-01, NV kho, NV giao gọi unpublish -> 403 Forbidden; bài vẫn giữ trạng thái."""
        url = f"/api/content/entries/{self.entry.pk}/unpublish/"
        payload = {"row_version": self.entry.row_version, "reason": "other"}

        for u in (self.nv_kho, self.nv_giao, self.user_nd01):
            self.client.force_authenticate(user=u)
            res = self.client.post(url, payload, format="json")
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "published")


    def test_cms_12_ac7_unpublish_on_draft_rejected_br_nd_01(self):
        """CMS-12-AC7: Gọi unpublish trên bài đang là draft -> 400 BR-ND-01."""
        draft_entry = Entry.objects.create(
            kind="post",
            status="draft",
            title="Bài nháp mới",
            slug="bai-nhap-moi",
            category=self.category,
            created_by=self.quan_ly,
        )
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{draft_entry.pk}/unpublish/"
        res = self.client.post(url, {"row_version": draft_entry.row_version, "reason": "other"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "BR-ND-01")

    # =========================================================================
    # CMS-10: Sửa nháp bài đang đăng & Huỷ thay đổi & Append-only
    # =========================================================================

    def test_cms_10_ac1_edit_draft_of_published_entry(self):
        """CMS-10-AC1: Bài đang published, sửa nháp -> has_unpublished_changes=True."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/"

        res = self.client.patch(
            url,
            {
                "row_version": self.entry.row_version,
                "title": "Cách làm sạch mang cá và khử tanh triệt để",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("has_unpublished_changes"))

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.title, "Cách làm sạch mang cá và khử tanh triệt để")
        self.assertEqual(self.entry.published_version.title, "Cách làm sạch mang cá")

    def test_cms_10_ac2_public_api_still_serves_published_version(self):
        """CMS-10-AC2: Khi nháp đang sửa, API công khai vẫn trả nội dung của published_version."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/"
        self.client.patch(
            url,
            {
                "row_version": self.entry.row_version,
                "title": "Tiêu đề nháp chưa xuất bản",
            },
            format="json",
        )

        self.client.logout()
        url_pub = f"/api/public/content/entries/{self.entry.slug}/"
        res_pub = self.client.get(url_pub)
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)
        # Vẫn là tiêu đề cũ của bản xuất bản
        self.assertEqual(res_pub.data.get("title"), "Cách làm sạch mang cá")

    def test_cms_10_ac3_discard_changes_restores_from_published_version(self):
        """CMS-10-AC3: discard_changes nạp lại nội dung published_version, has_unpublished_changes=False, không AuditLog."""
        self.client.force_authenticate(user=self.quan_ly)
        url_patch = f"/api/content/entries/{self.entry.pk}/"
        patch_res = self.client.patch(
            url_patch,
            {
                "row_version": self.entry.row_version,
                "title": "Tiêu đề sửa nhầm",
                "excerpt": "Tóm tắt sửa nhầm",
            },
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)

        self.entry.refresh_from_db()
        before_audit = AuditLog.objects.count()

        # Gọi discard_changes
        url_discard = f"/api/content/entries/{self.entry.pk}/discard-changes/"
        res_discard = self.client.post(
            url_discard,
            {"row_version": self.entry.row_version},
            format="json",
        )
        self.assertEqual(res_discard.status_code, status.HTTP_200_OK)
        # CMS-10-AC3: Trả về chi tiết bản ghi
        self.assertEqual(res_discard.data.get("title"), "Cách làm sạch mang cá")
        self.assertEqual(res_discard.data.get("excerpt"), "Hướng dẫn rửa sạch mang cá không còn mùi tanh.")
        self.assertFalse(res_discard.data.get("has_unpublished_changes"))

        self.entry.refresh_from_db()
        # Đã khôi phục lại tiêu đề gốc
        self.assertEqual(self.entry.title, "Cách làm sạch mang cá")
        self.assertEqual(self.entry.excerpt, "Hướng dẫn rửa sạch mang cá không còn mùi tanh.")
        # Không sinh thêm AuditLog
        self.assertEqual(AuditLog.objects.count(), before_audit)

        # GET detail trả has_unpublished_changes = False
        res_detail = self.client.get(url_patch)
        self.assertFalse(res_detail.data.get("has_unpublished_changes"))


    def test_cms_10_ac4_republish_without_changes_rejected_br_nd_05(self):
        """CMS-10-AC4: Đăng lại khi không có thay đổi -> 400 BR-ND-05."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "BR-ND-05")

    def test_cms_10_ac5_entry_version_append_only(self):
        """CMS-10-AC5: EntryVersion append-only; save, delete, QuerySet.update, QuerySet.delete đều raise BR-ND-05."""
        ver = self.entry.published_version

        # 1. ver.save() khi đã tồn tại -> BusinessError BR-ND-05
        ver.title = "Tiêu đề bị sửa lén"
        with self.assertRaises(BusinessError) as ctx1:
            ver.save()
        self.assertEqual(ctx1.exception.code, "BR-ND-05")

        # 2. ver.delete() -> BusinessError BR-ND-05
        with self.assertRaises(BusinessError) as ctx2:
            ver.delete()
        self.assertEqual(ctx2.exception.code, "BR-ND-05")

        # 3. QuerySet.update() -> BusinessError BR-ND-05
        with self.assertRaises(BusinessError) as ctx3:
            EntryVersion.objects.filter(pk=ver.pk).update(title="Lén đổi")
        self.assertEqual(ctx3.exception.code, "BR-ND-05")

        # 4. QuerySet.delete() -> BusinessError BR-ND-05
        with self.assertRaises(BusinessError) as ctx4:
            EntryVersion.objects.filter(pk=ver.pk).delete()
        self.assertEqual(ctx4.exception.code, "BR-ND-05")

    def test_cms_10_ac6_user_nd01_can_edit_draft_but_cannot_publish_403(self):
        """CMS-10-AC6: User chỉ có ND-01 sửa được nháp bài đã đăng (PATCH 200), nhưng gọi publish bị 403, public API vẫn hiện bản cũ."""
        self.client.force_authenticate(user=self.user_nd01)
        url_patch = f"/api/content/entries/{self.entry.pk}/"

        # 1. Sửa nháp thành công
        res_patch = self.client.patch(
            url_patch,
            {
                "row_version": self.entry.row_version,
                "title": "Tiêu đề do biên tập viên sửa",
            },
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertTrue(res_patch.data.get("has_unpublished_changes"))

        # 2. Gọi publish -> 403 Forbidden
        url_pub = f"/api/content/entries/{self.entry.pk}/publish/"
        res_pub = self.client.post(
            url_pub,
            {
                "row_version": res_patch.data.get("row_version"),
                "checklist_confirmed": True,
            },
            format="json",
        )
        self.assertEqual(res_pub.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Web công khai vẫn phục vụ bản cũ đã xuất bản
        self.client.logout()
        res_public = self.client.get(f"/api/public/content/entries/{self.entry.slug}/")
        self.assertEqual(res_public.status_code, status.HTTP_200_OK)
        self.assertEqual(res_public.data.get("title"), "Cách làm sạch mang cá")

