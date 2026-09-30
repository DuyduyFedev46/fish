"""
Kiểm thử tạo, lưu và xoá nháp bài viết / trang (CMS-03, BR-ND-01, 02, 04, 06, 15).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import AuditLog
from apps.content.models.entries import Entry, EntryVersion
from apps.content.models.categories import Category
from apps.accounts import roles

User = get_user_model()


class DraftEntryTests(APITestCase):
    def setUp(self):
        self.quan_ly = User.objects.create_user(username="quan_ly_user", password="password")
        self.nv_giao = User.objects.create_user(username="nv_giao_user", password="password")
        self.viewer_only = User.objects.create_user(username="viewer_user", password="password")

        g_ql, _ = Group.objects.get_or_create(name=roles.MANAGER)
        g_giao, _ = Group.objects.get_or_create(name=roles.DELIVERY_STAFF)
        self.quan_ly.groups.add(g_ql)
        self.nv_giao.groups.add(g_giao)

        # viewer_only chỉ có quyền view_entry
        p_view = Permission.objects.get(codename="view_entry", content_type__app_label="content")
        self.viewer_only.user_permissions.add(p_view)

        self.category = Category.objects.create(name="Công thức nấu", slug="cong-thuc-nau")

    def test_cms_03_ac1_create_draft_empty_slug(self):
        """CMS-03-AC1: Tạo bài để trống slug -> 201, status=draft, slug tự sinh, row_version=1."""
        self.client.force_authenticate(user=self.quan_ly)
        payload = {
            "kind": "post",
            "title": "Cách rã đông cá thu",
            "slug": "",
            "category": self.category.pk,
            "excerpt": "",
            "seo_title": "",
            "seo_description": "",
            "body": {"type": "doc", "blocks": []},
        }
        resp = self.client.post("/api/content/entries/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        self.assertEqual(data["title"], "Cách rã đông cá thu")
        self.assertEqual(data["slug"], "cach-ra-dong-ca-thu")
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["row_version"], 1)
        self.assertFalse(data["slug_locked"])

    def test_cms_03_ac2_custom_slug_normalized(self):
        """CMS-03-AC2: Nhập slug 'Cá Thu  Đông!!' -> lưu thành 'ca-thu-dong'."""
        self.client.force_authenticate(user=self.quan_ly)
        payload = {
            "kind": "post",
            "title": "Tiêu đề bài",
            "slug": "Cá Thu  Đông!!",
            "category": self.category.pk,
            "body": {"type": "doc", "blocks": []},
        }
        resp = self.client.post("/api/content/entries/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json()["slug"], "ca-thu-dong")

    def test_cms_03_ac3_duplicate_slug_suggestion(self):
        """CMS-03-AC3: Đã có bài slug 'cach-ra-dong-ca-thu' ở trạng thái Đã gỡ -> 400 BR-ND-04 + suggestion."""
        Entry.objects.create(
            title="Bài cũ đã gỡ",
            slug="cach-ra-dong-ca-thu",
            status="unpublished",
            created_by=self.quan_ly,
        )
        self.client.force_authenticate(user=self.quan_ly)
        payload = {
            "kind": "post",
            "title": "Cách rã đông cá thu",
            "slug": "cach-ra-dong-ca-thu",
            "category": self.category.pk,
            "body": {"type": "doc", "blocks": []},
        }
        resp = self.client.post("/api/content/entries/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        data = resp.json()
        self.assertEqual(data["code"], "BR-ND-04")
        self.assertEqual(data["suggestion"], "cach-ra-dong-ca-thu-2")

    def test_cms_03_ac4_empty_title_allowed_for_draft(self):
        """CMS-03-AC4: Lưu nháp với tiêu đề trống -> 201, bài vẫn là draft."""
        self.client.force_authenticate(user=self.quan_ly)
        payload = {
            "kind": "post",
            "title": "",
            "slug": "",
            "body": {"type": "doc", "blocks": []},
        }
        resp = self.client.post("/api/content/entries/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json()["status"], "draft")
        self.assertTrue(resp.json()["slug"].startswith("bai-"))

    def test_cms_03_ac5_patch_sanitizes_xss(self):
        """CMS-03-AC5: PATCH payload XSS -> 200, body chỉ còn khối và mark cho phép."""
        entry = Entry.objects.create(
            title="Bài test XSS",
            slug="bai-test-xss",
            created_by=self.quan_ly,
        )
        self.client.force_authenticate(user=self.quan_ly)
        patch_payload = {
            "row_version": 1,
            "body": {
                "type": "doc",
                "blocks": [
                    {"type": "html", "html": "<script>alert(1)</script>"},
                    {"type": "paragraph", "children": [{"text": "Chào khách", "href": "javascript:alert(1)"}]},
                    {"type": "heading", "level": 1, "text": "<img src=x onerror=alert(1)>", "style": "color:red"},
                ],
            },
        }
        resp = self.client.patch(f"/api/content/entries/{entry.pk}/", patch_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        blocks = data["body"]["blocks"]
        # html bị bỏ
        self.assertEqual(len(blocks), 2)
        # paragraph mất href javascript
        self.assertEqual(blocks[0]["type"], "paragraph")
        self.assertNotIn("href", blocks[0]["children"][0])
        # heading level 1 -> 2, style bị bỏ, text giữ nguyên
        self.assertEqual(blocks[1]["type"], "heading")
        self.assertEqual(blocks[1]["level"], 2)
        self.assertNotIn("style", blocks[1])
        self.assertEqual(blocks[1]["text"], "<img src=x onerror=alert(1)>")

    def test_cms_03_ac7_stale_version_409(self):
        """CMS-03-AC7: Sửa trùng row_version -> 409 STALE_VERSION."""
        entry = Entry.objects.create(
            title="Bài đang sửa",
            slug="bai-dang-sua",
            row_version=3,
            created_by=self.quan_ly,
        )
        self.client.force_authenticate(user=self.quan_ly)

        # Người 1 lưu trước -> row_version tăng lên 4
        resp1 = self.client.patch(
            f"/api/content/entries/{entry.pk}/",
            {"row_version": 3, "title": "Bản của Chủ"},
            format="json",
        )
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertEqual(resp1.json()["row_version"], 4)

        # Người 2 lưu với row_version=3 cũ -> 409 STALE_VERSION
        resp2 = self.client.patch(
            f"/api/content/entries/{entry.pk}/",
            {"row_version": 3, "title": "Bản của Quản lý"},
            format="json",
        )

        self.assertEqual(resp2.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp2.json()["code"], "STALE_VERSION")

        # Nội dung của người 1 vẫn còn nguyên
        entry.refresh_from_db()
        self.assertEqual(entry.title, "Bản của Chủ")

    def test_cms_03_ac8_delete_draft_never_published(self):
        """CMS-03-AC8: Xoá nháp chưa từng đăng -> 204, không có AuditLog mới."""
        entry = Entry.objects.create(
            title="Nháp cần xoá",
            slug="nhap-can-xoa",
            created_by=self.quan_ly,
        )
        log_count_before = AuditLog.objects.count()

        self.client.force_authenticate(user=self.quan_ly)
        resp = self.client.delete(f"/api/content/entries/{entry.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Entry.objects.filter(pk=entry.pk).exists())
        self.assertEqual(AuditLog.objects.count(), log_count_before)

    def test_cms_03_ac9_cannot_delete_published_entry(self):
        """CMS-03-AC9: Bài đã từng đăng (published hoặc unpublished) -> DELETE trả 400 BR-ND-02."""
        from django.utils import timezone
        entry = Entry.objects.create(
            title="Bài đã đăng",
            slug="bai-da-dang",
            status="published",
            first_published_at=timezone.now(),
            created_by=self.quan_ly,
        )
        self.client.force_authenticate(user=self.quan_ly)
        resp = self.client.delete(f"/api/content/entries/{entry.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.json()["code"], "BR-ND-02")
        self.assertTrue(Entry.objects.filter(pk=entry.pk).exists())

    def test_cms_03_ac10_save_draft_no_audit_log(self):
        """CMS-03-AC10: Nháp lưu 5 lần liên tiếp -> AuditLog không tăng."""
        entry = Entry.objects.create(
            title="Bài nháp lưu nhiều lần",
            slug="nhap-nhieu-lan",
            created_by=self.quan_ly,
        )
        log_count_before = AuditLog.objects.count()
        self.client.force_authenticate(user=self.quan_ly)

        for i in range(5):
            entry.refresh_from_db()
            resp = self.client.patch(
                f"/api/content/entries/{entry.pk}/",
                {"row_version": entry.row_version, "title": f"Tiêu đề lần {i}"},
                format="json",
            )
            self.assertEqual(resp.status_code, status.HTTP_200_OK)


        self.assertEqual(AuditLog.objects.count(), log_count_before)

    def test_cms_03_ac11_title_max_length(self):
        """CMS-03-AC11: Tiêu đề dài 201 ký tự -> 400."""
        self.client.force_authenticate(user=self.quan_ly)
        payload = {
            "title": "A" * 201,
            "slug": "",
        }
        resp = self.client.post("/api/content/entries/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.json()["code"], "BR-ND-01")

    def test_cms_03_ac12_permission_denied(self):
        """CMS-03-AC12: NV giao và user chỉ view_entry gọi POST/PATCH/DELETE -> 403."""
        entry = Entry.objects.create(
            title="Bài mẫu",
            slug="bai-mau",
            created_by=self.quan_ly,
        )

        for user in (self.nv_giao, self.viewer_only):
            self.client.force_authenticate(user=user)

            # POST
            resp = self.client.post("/api/content/entries/", {"title": "X"}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

            # PATCH
            resp = self.client.patch(f"/api/content/entries/{entry.pk}/", {"title": "Y"}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

            # DELETE
            resp = self.client.delete(f"/api/content/entries/{entry.pk}/")
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # Dữ liệu không đổi
        entry.refresh_from_db()
        self.assertEqual(entry.title, "Bài mẫu")
