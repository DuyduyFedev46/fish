"""
Kiểm thử đăng bài viết và trang nội dung (CMS-01-AC5, CMS-07-AC1..AC9, §4.3, §4.5 02b-tech-design).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.content.models.categories import Category
from apps.content.models.entries import Entry, EntryVersion
from apps.content.models.images import ContentImage

User = get_user_model()


class PublishEntryTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Tạo user quản lý (có đủ quyền content)
        self.quan_ly = User.objects.create_user(username="quan_ly", password="password123")
        group_ql, _ = Group.objects.get_or_create(name="quan_ly")
        for perm_code in ("view_entry", "add_entry", "change_entry", "delete_entry", "publish_entry"):
            perm = Permission.objects.get(codename=perm_code, content_type__app_label="content")
            group_ql.permissions.add(perm)
        self.quan_ly.groups.add(group_ql)

        # Tạo user chỉ có quyền soạn (ND-01: view_entry, add_entry, change_entry)
        self.user_soan = User.objects.create_user(username="user_soan", password="password123")
        for perm_code in ("view_entry", "add_entry", "change_entry"):
            perm = Permission.objects.get(codename=perm_code, content_type__app_label="content")
            self.user_soan.user_permissions.add(perm)

        # Tạo user NV kho (không có quyền content nào)
        self.nv_kho = User.objects.create_user(username="nv_kho", password="password123")
        group_kho, _ = Group.objects.get_or_create(name="nv_kho")
        self.nv_kho.groups.add(group_kho)

        # Chuyên mục hợp lệ
        self.category = Category.objects.create(
            name="Công thức nấu",
            name_key="cong thuc nau",
            slug="cong-thuc-nau",
            order=1,
            is_active=True,
        )

        # Bài nháp cơ bản đủ điều kiện
        self.entry = Entry.objects.create(
            kind="post",
            title="Cách rã đông cá thu tươi ngon",
            slug="cach-ra-dong-ca-thu-tuoi-ngon",
            category=self.category,
            excerpt="Hướng dẫn chi tiết mẹo rã đông cá thu",
            seo_title="Mẹo rã đông cá thu | Cá Về",
            seo_description="Cách rã đông cá thu giữ nguyên vị ngọt tươi",
            body={
                "type": "doc",
                "blocks": [
                    {
                        "type": "paragraph",
                        "children": [{"text": "Để cá trong ngăn mát từ 4-6 tiếng trước khi nấu."}],
                    }
                ],
            },
            source="human",
            row_version=1,
            created_by=self.quan_ly,
            updated_by=self.quan_ly,
        )

        # Ảnh bìa có alt
        self.cover_image = ContentImage.objects.create(
            entry=self.entry,
            alt="Cá thu cắt khoanh tươi ngon",
            width=1600,
            height=1200,
            uploaded_by=self.quan_ly,
        )
        self.entry.cover_image = self.cover_image
        self.entry.save()

    def test_cms_01_ac5_user_with_only_nd01_calls_publish_403(self):
        """CMS-01-AC5: User chỉ có ND-01 gọi API publish -> 403, không đổi trạng thái."""
        self.client.force_authenticate(user=self.user_soan)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(url, {"row_version": 1, "checklist_confirmed": True})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "draft")
        self.assertEqual(EntryVersion.objects.count(), 0)

    def test_cms_07_ac1_publish_post_success(self):
        """CMS-07-AC1: Đăng bài lần đầu thành công -> 200, status=published, version=1, slug_locked=True."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
                "acknowledge_warnings": False,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "published")
        self.assertEqual(res.data["version"], 1)
        self.assertIn("public_path", res.data)
        self.assertIn("cach-ra-dong-ca-thu-tuoi-ngon", res.data["public_path"])

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "published")
        self.assertTrue(self.entry.slug_locked)
        self.assertIsNotNone(self.entry.first_published_at)
        self.assertIsNotNone(self.entry.published_version)
        self.assertEqual(self.entry.published_version.version, 1)

    def test_cms_07_ac2_audit_log_format(self):
        """
        CMS-07-AC2: Đúng 1 dòng AuditLog content_publish, changes chỉ entry_id/version/kind,
        không chứa tiêu đề hay chữ nào của bài viết.
        """
        initial_count = AuditLog.objects.count()
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(AuditLog.objects.count(), initial_count + 1)

        log = AuditLog.objects.latest("id")
        self.assertEqual(log.action, "content_publish")
        self.assertEqual(log.actor, self.quan_ly)
        self.assertEqual(log.object_repr, f"Nội dung #{self.entry.pk}")
        self.assertEqual(log.note, "")

        # Kiểm tra changes chỉ gồm entry_id, version, kind
        self.assertEqual(
            log.changes,
            {
                "entry_id": self.entry.pk,
                "version": 1,
                "kind": "post",
            },
        )
        # Không chứa tiêu đề hay đoạn trích trong AuditLog
        self.assertNotIn(self.entry.title, str(log.changes))
        self.assertNotIn("rã đông", log.object_repr)

    def test_cms_07_ac3_missing_fields_validation(self):
        """CMS-07-AC3: Nháp thiếu chuyên mục và alt ảnh bìa -> 400 BR-ND-03, missing liệt kê đúng 2 mục."""
        self.entry.category = None
        self.cover_image.alt = ""
        self.cover_image.save()
        self.entry.save()

        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "BR-ND-03")
        missing = res.data.get("missing", [])
        self.assertIn("category", missing)
        self.assertIn("cover_image_alt", missing)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "draft")

    def test_cms_07_ac4_checklist_not_confirmed(self):
        """CMS-07-AC4: checklist_confirmed=False -> 400 BR-ND-13."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": False,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "BR-ND-13")

    def test_cms_07_ac5_description_computed_from_excerpt(self):
        """CMS-07-AC5: Nháp có excerpt 300 ký tự, seo_description trống -> description cắt <= 160 ký tự tại khoảng trắng cuối."""
        long_excerpt = (
            "Cá thu là loại cá biển giàu dinh dưỡng chứa nhiều omega 3 và protein "
            "tốt cho sức khoẻ của mọi lứa tuổi gia đình việt nam. Bài viết này hướng "
            "dẫn cách rã đông giữ trọn vị tươi nguyên bản như vừa đánh bắt tại cảng biển."
        )
        self.assertTrue(len(long_excerpt) > 200)
        self.entry.seo_description = ""
        self.entry.excerpt = long_excerpt
        self.entry.save()

        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        version = EntryVersion.objects.get(entry=self.entry, version=1)
        self.assertTrue(len(version.description) <= 160)
        # Không bị cắt giữa chữ (chữ cuối cùng kết thúc trọn vẹn)
        self.assertFalse(version.description.endswith("..."))
        self.assertFalse(version.description.endswith(" "))

    def test_cms_07_ac6_concurrent_publish_stale_version_409(self):
        """CMS-07-AC6: Hai request publish cùng lúc -> 1 request 200, request kia 409 STALE_VERSION."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"

        # Request 1 thành công
        res1 = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
            },
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Request 2 gửi lại với row_version cũ -> 409 STALE_VERSION
        res2 = self.client.post(
            url,
            {
                "row_version": 1,
                "checklist_confirmed": True,
            },
        )
        self.assertEqual(res2.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res2.data.get("code"), "STALE_VERSION")

    def test_cms_07_ac7_published_entry_cannot_change_slug(self):
        """CMS-07-AC7: Bài đã đăng -> PATCH đổi slug trả về 400 BR-ND-04."""
        # Xuất bản bài
        self.client.force_authenticate(user=self.quan_ly)
        url_pub = f"/api/content/entries/{self.entry.pk}/publish/"
        res_pub = self.client.post(
            url_pub,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
            },
        )
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)

        self.entry.refresh_from_db()
        patch_url = f"/api/content/entries/{self.entry.pk}/"
        res_patch = self.client.patch(
            patch_url,
            {
                "row_version": self.entry.row_version,
                "slug": "doi-sang-slug-khac",
            },
        )
        self.assertEqual(res_patch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_patch.data.get("code"), "BR-ND-04")
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.slug, "cach-ra-dong-ca-thu-tuoi-ngon")

    def test_cms_07_ac8_nv_kho_cannot_publish_403(self):
        """CMS-07-AC8: NV kho gọi publish -> 403."""
        self.client.force_authenticate(user=self.nv_kho)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(url, {"row_version": 1, "checklist_confirmed": True})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
