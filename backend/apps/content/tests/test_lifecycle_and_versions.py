"""
Kiểm thử Lô 7 CMS:
- Story CMS-09: Gửi duyệt bài và trả về nháp (AC1..AC6)
- Story CMS-11: Lịch sử phiên bản và khôi phục (AC1..AC5)
"""

from io import BytesIO
from PIL import Image as PILImage
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog, StaffProfile
from apps.content.models.categories import Category
from apps.content.models.entries import Entry, EntryVersion
from apps.content.models.images import ContentImage

User = get_user_model()

FORBIDDEN_KEYS = {
    "unit_cost",
    "cost",
    "purchase_rate",
    "landed_cost",
    "profit",
    "gross_margin",
    "created_by",
    "updated_by",
    "uploaded_by",
    "password",
    "token",
    "phone",
    "delivery_address",
    "customer_name",
}


def _has_forbidden_key(data: any) -> set[str]:
    found = set()
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() in FORBIDDEN_KEYS:
                found.add(k)
            found |= _has_forbidden_key(v)
    elif isinstance(data, list):
        for item in data:
            found |= _has_forbidden_key(item)
    return found


def _make_sample_image(name="test.jpg", color="blue"):
    f = BytesIO()
    img = PILImage.new("RGB", (400, 300), color=color)
    img.save(f, format="JPEG")
    f.seek(0)
    return SimpleUploadedFile(name, f.read(), content_type="image/jpeg")


class LifecycleAndVersionsTests(APITestCase):
    def setUp(self):
        # 1. Setup groups and users
        self.grp_quan_ly = Group.objects.get(name="quan_ly")
        self.grp_nv_kho = Group.objects.get(name="nv_kho")

        self.manager = User.objects.create_user(username="manager_u7", password="password")
        self.manager.groups.add(self.grp_quan_ly)
        StaffProfile.objects.create(user=self.manager, display_name="Quản lý A")

        # User ND-01: chỉ có quyền soạn, không có publish_entry
        self.author_nd01 = User.objects.create_user(username="author_nd01", password="password")
        nd01_perms = Permission.objects.filter(
            codename__in=[
                "view_entry",
                "add_entry",
                "change_entry",
                "delete_entry",
                "view_category",
            ],
            content_type__app_label="content",
        )
        self.author_nd01.user_permissions.set(nd01_perms)
        StaffProfile.objects.create(user=self.author_nd01, display_name="Biên tập viên ND01")

        self.warehouse = User.objects.create_user(username="warehouse_u7", password="password")
        self.warehouse.groups.add(self.grp_nv_kho)

        # 2. Setup category & sample entry
        self.category = Category.objects.create(
            name="Kiến thức cá",
            slug="kien-thuc-ca",
            name_key="kien thuc ca",
            order=1,
            is_active=True,
        )

        self.entry = Entry.objects.create(
            kind="post",
            title="Bí quyết chọn cá hồi tươi ngon",
            slug="bi-quyet-chon-ca-hoi-tuoi-ngon",
            category=self.category,
            excerpt="Cách chọn cá hồi tự nhiên tươi ngon chuẩn vựa...",
            seo_title="Bí quyết chọn cá hồi",
            seo_description="Bí quyết chọn cá hồi tự nhiên tươi ngon chuẩn vựa từ chuyên gia Cá Về.",
            body={"type": "doc", "blocks": [{"type": "paragraph", "text": "Thịt cá hồi phải có màu cam tươi tự nhiên."}]},
            draft_hash="hash_draft_1",
            status="draft",
            row_version=1,
            created_by=self.author_nd01,
            updated_by=self.author_nd01,
        )

        # Create cover image
        self.cover_img = ContentImage.objects.create(
            entry=self.entry,
            alt="Cá hồi phi lê tươi",
            width=400,
            height=300,
            uploaded_by=self.author_nd01,
        )
        self.entry.cover_image = self.cover_img
        self.entry.save(update_fields=["cover_image"])

    def test_cms_09_ac1_author_submit_valid_draft_success_and_auditlog(self):
        """CMS-09-AC1: User ND-01 gửi duyệt nháp đủ điều kiện BR-ND-03 -> 200 pending_review, AuditLog content_submit."""
        self.client.force_authenticate(user=self.author_nd01)
        res = self.client.post(
            f"/api/content/entries/{self.entry.id}/submit/",
            {"row_version": 1},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["status"], "pending_review")
        self.assertEqual(res.data["row_version"], 2)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "pending_review")
        self.assertEqual(self.entry.row_version, 2)

        # Kiểm tra AuditLog content_submit
        audit = AuditLog.objects.filter(action="content_submit", object_id=str(self.entry.id)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.author_nd01)
        self.assertEqual(audit.changes, {"entry_id": self.entry.id})
        self.assertEqual(audit.object_repr, f"Nội dung #{self.entry.id}")

    def test_cms_09_ac2_submit_incomplete_draft_rejected_br_nd_03(self):
        """CMS-09-AC2: Gửi duyệt nháp thiếu điều kiện -> 400 BR-ND-03 với danh sách missing."""
        incomplete_entry = Entry.objects.create(
            kind="post",
            title="Bài chưa xong",
            slug="bai-chua-xong",
            category=None,
            cover_image=None,
            body={"type": "doc", "blocks": []},
            status="draft",
            row_version=1,
            created_by=self.author_nd01,
            updated_by=self.author_nd01,
        )
        self.client.force_authenticate(user=self.author_nd01)
        res = self.client.post(
            f"/api/content/entries/{incomplete_entry.id}/submit/",
            {"row_version": 1},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "BR-ND-03")
        missing = res.data.get("missing", [])
        self.assertIn("category", missing)
        self.assertIn("cover_image", missing)
        self.assertIn("body", missing)

    def test_cms_09_ac3_counts_and_manager_publish_from_pending_review(self):
        """CMS-09-AC3: Đếm counts pending_review hiện số bài chờ duyệt, Quản lý publish được từ pending_review."""
        self.entry.status = "pending_review"
        self.entry.save(update_fields=["status"])

        # Tạo bài thứ 2 pending_review
        Entry.objects.create(
            kind="post",
            title="Bài thứ 2",
            slug="bai-thu-2",
            status="pending_review",
            row_version=1,
            created_by=self.author_nd01,
            updated_by=self.author_nd01,
        )

        self.client.force_authenticate(user=self.manager)
        res_counts = self.client.get("/api/content/entries/counts/")
        self.assertEqual(res_counts.status_code, status.HTTP_200_OK)
        self.assertEqual(res_counts.data["pending_review"], 2)

        # Quản lý xuất bản bài chờ duyệt
        res_pub = self.client.post(
            f"/api/content/entries/{self.entry.id}/publish/",
            {"row_version": 1, "checklist_confirmed": True},
            format="json",
        )
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)
        self.assertEqual(res_pub.data["status"], "published")

    def test_cms_09_ac4_manager_return_to_draft_with_reason_and_auditlog(self):
        """CMS-09-AC4: Quản lý bấm Trả về nháp, chọn lý do -> 200 draft, return_reason, AuditLog content_return."""
        self.entry.status = "pending_review"
        self.entry.save(update_fields=["status"])

        self.client.force_authenticate(user=self.manager)
        # Lý do không hợp lệ -> 400 BR-ND-15
        res_bad = self.client.post(
            f"/api/content/entries/{self.entry.id}/return/",
            {"row_version": 1, "reason": "invalid_reason_xxx"},
            format="json",
        )
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_bad.data.get("code"), "BR-ND-15")

        # Lý do hợp lệ: missing_info
        res = self.client.post(
            f"/api/content/entries/{self.entry.id}/return/",
            {"row_version": 1, "reason": "missing_info"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "draft")
        self.assertEqual(res.data["row_version"], 2)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "draft")
        self.assertEqual(self.entry.return_reason, "missing_info")

        # AuditLog content_return
        audit = AuditLog.objects.filter(action="content_return", object_id=str(self.entry.id)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes, {"entry_id": self.entry.id, "reason": "missing_info"})

    def test_cms_09_ac5_author_cannot_return_or_publish_forbidden_403(self):
        """CMS-09-AC5: User ND-01 gọi return hoặc publish -> 403 BR-PQ-12."""
        self.entry.status = "pending_review"
        self.entry.save(update_fields=["status"])

        self.client.force_authenticate(user=self.author_nd01)
        res_ret = self.client.post(
            f"/api/content/entries/{self.entry.id}/return/",
            {"row_version": 1, "reason": "missing_info"},
            format="json",
        )
        self.assertEqual(res_ret.status_code, status.HTTP_403_FORBIDDEN)

        res_pub = self.client.post(
            f"/api/content/entries/{self.entry.id}/publish/",
            {"row_version": 1, "checklist_confirmed": True},
            format="json",
        )
        self.assertEqual(res_pub.status_code, status.HTTP_403_FORBIDDEN)

    def test_cms_09_ac6_submit_published_or_unpublished_rejected_br_nd_02(self):
        """CMS-09-AC6: Bài Đã đăng hoặc Đã gỡ gọi submit -> 400 BR-ND-02."""
        self.entry.status = "published"
        self.entry.save(update_fields=["status"])

        self.client.force_authenticate(user=self.author_nd01)
        res_pub = self.client.post(
            f"/api/content/entries/{self.entry.id}/submit/",
            {"row_version": 1},
            format="json",
        )
        self.assertEqual(res_pub.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_pub.data.get("code"), "BR-ND-02")

        self.entry.status = "unpublished"
        self.entry.save(update_fields=["status"])

        res_unpub = self.client.post(
            f"/api/content/entries/{self.entry.id}/submit/",
            {"row_version": 1},
            format="json",
        )
        self.assertEqual(res_unpub.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_unpub.data.get("code"), "BR-ND-02")

    def test_cms_11_ac1_list_versions_descending_without_body(self):
        """CMS-11-AC1: Bài có phiên bản 1, 2, 3 -> GET versions trả 3 dòng mới nhất trước, có thời điểm và người đăng, không có body."""
        # Tạo 3 phiên bản
        v1 = EntryVersion.objects.create(
            entry=self.entry,
            version=1,
            kind="post",
            title="Phiên bản 1",
            slug=self.entry.slug,
            description="Mô tả 1",
            content_hash="h1",
            published_at=timezone.now(),
            published_by=self.manager,
        )
        v2 = EntryVersion.objects.create(
            entry=self.entry,
            version=2,
            kind="post",
            title="Phiên bản 2",
            slug=self.entry.slug,
            description="Mô tả 2",
            content_hash="h2",
            published_at=timezone.now(),
            published_by=self.manager,
        )
        v3 = EntryVersion.objects.create(
            entry=self.entry,
            version=3,
            kind="post",
            title="Phiên bản 3",
            slug=self.entry.slug,
            description="Mô tả 3",
            content_hash="h3",
            published_at=timezone.now(),
            published_by=self.manager,
        )

        self.client.force_authenticate(user=self.manager)
        res = self.client.get(f"/api/content/entries/{self.entry.id}/versions/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        versions_list = res.data
        self.assertEqual(len(versions_list), 3)
        self.assertEqual(versions_list[0]["version"], 3)
        self.assertEqual(versions_list[1]["version"], 2)
        self.assertEqual(versions_list[2]["version"], 1)

        for item in versions_list:
            self.assertIn("version", item)
            self.assertIn("published_at", item)
            self.assertEqual(item["published_by_name"], "Quản lý A")
            self.assertIn("title", item)
            # CMS-11-AC1: Danh sách không trả thân bài
            self.assertNotIn("body", item)

    def test_cms_11_ac2_restore_version_1_and_republish_version_4(self):
        """CMS-11-AC2: Đang ở phiên bản 3 -> Khôi phục phiên bản 1 rồi Cập nhật bài -> Phiên bản 4 có nội dung v1, AuditLog content_restore_version."""
        v1 = EntryVersion.objects.create(
            entry=self.entry,
            version=1,
            kind="post",
            title="Cá hồi nướng bơ tỏi (v1)",
            slug=self.entry.slug,
            category=self.category,
            cover_image=self.cover_img,
            excerpt="Công thức v1 thơm ngon",
            seo_description="Bí quyết cá hồi nướng bơ tỏi v1",
            body={"type": "doc", "blocks": [{"type": "paragraph", "text": "Công thức v1"}]},
            description="Mô tả 1",
            content_hash="h1",
            published_at=timezone.now(),
            published_by=self.manager,
        )
        v2 = EntryVersion.objects.create(
            entry=self.entry,
            version=2,
            kind="post",
            title="Cá hồi sốt chanh leo (v2)",
            slug=self.entry.slug,
            category=self.category,
            cover_image=self.cover_img,
            body={"type": "doc", "blocks": [{"type": "paragraph", "text": "Công thức v2"}]},
            description="Mô tả 2",
            content_hash="h2",
            published_at=timezone.now(),
            published_by=self.manager,
        )
        v3 = EntryVersion.objects.create(
            entry=self.entry,
            version=3,
            kind="post",
            title="Cá hồi áp chảo (v3)",
            slug=self.entry.slug,
            category=self.category,
            cover_image=self.cover_img,
            body={"type": "doc", "blocks": [{"type": "paragraph", "text": "Công thức v3"}]},
            description="Mô tả 3",
            content_hash="h3",
            published_at=timezone.now(),
            published_by=self.manager,
        )
        self.entry.status = "published"
        self.entry.published_version = v3
        self.entry.title = "Cá hồi áp chảo (v3)"
        self.entry.body = {"type": "doc", "blocks": [{"type": "paragraph", "text": "Công thức v3"}]}
        self.entry.row_version = 5
        self.entry.first_published_at = timezone.now()
        self.entry.save()

        self.client.force_authenticate(user=self.manager)

        # 1. Khôi phục phiên bản 1
        res_restore = self.client.post(
            f"/api/content/entries/{self.entry.id}/versions/1/restore/",
            {"row_version": 5},
            format="json",
        )
        self.assertEqual(res_restore.status_code, status.HTTP_200_OK)
        self.assertEqual(res_restore.data["title"], "Cá hồi nướng bơ tỏi (v1)")
        self.assertEqual(res_restore.data["restored_from"], 1)
        self.assertEqual(res_restore.data["row_version"], 6)

        # 2. Cập nhật bài (publish lại)
        res_pub = self.client.post(
            f"/api/content/entries/{self.entry.id}/publish/",
            {"row_version": 6, "checklist_confirmed": True},
            format="json",
        )
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK, res_pub.data)
        self.assertEqual(res_pub.data["version"], 4)

        # Kiểm tra phiên bản 4 trong DB
        v4 = EntryVersion.objects.get(entry=self.entry, version=4)
        self.assertEqual(v4.title, "Cá hồi nướng bơ tỏi (v1)")
        self.assertEqual(v4.restored_from, 1)

        # AuditLog content_restore_version
        audit = AuditLog.objects.filter(action="content_restore_version", object_id=str(self.entry.id)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes["restored_from"], 1)
        self.assertEqual(audit.changes["version"], 4)

    def test_cms_11_ac4_warehouse_get_versions_forbidden_403(self):
        """CMS-11-AC4: NV kho gọi GET versions -> 403 BR-PQ-12."""
        self.client.force_authenticate(user=self.warehouse)
        res = self.client.get(f"/api/content/entries/{self.entry.id}/versions/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_cms_11_ac5_published_by_name_in_erp_only_and_no_forbidden_keys(self):
        """CMS-11-AC5: published_by_name chỉ có ở API ERP; API công khai không có khoá nào trong bộ khoá cấm."""
        v1 = EntryVersion.objects.create(
            entry=self.entry,
            version=1,
            kind="post",
            title="Bài test khoá",
            slug=self.entry.slug,
            category=self.category,
            cover_image=self.cover_img,
            excerpt="Đoạn trích kiểm tra khoá cấm",
            seo_description="Mô tả SEO kiểm tra khoá cấm",
            body={"type": "doc", "blocks": [{"type": "paragraph", "text": "Thân bài kiểm tra khoá cấm"}]},
            description="Mô tả test",
            content_hash="h1",
            published_at=timezone.now(),
            published_by=self.manager,
        )
        self.entry.status = "published"
        self.entry.published_version = v1
        self.entry.first_published_at = timezone.now()
        self.entry.save()

        # ERP versions
        self.client.force_authenticate(user=self.manager)
        res_erp = self.client.get(f"/api/content/entries/{self.entry.id}/versions/")
        self.assertEqual(res_erp.status_code, status.HTTP_200_OK)
        self.assertEqual(res_erp.data[0]["published_by_name"], "Quản lý A")

        # Public detail
        self.client.logout()
        res_pub = self.client.get(f"/api/public/content/entries/{self.entry.slug}/")
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK, res_pub.data)
        self.assertNotIn("published_by_name", res_pub.data)
        self.assertEqual(res_pub.data.get("author"), "Cá Về")

        # Quét bộ khoá cấm
        forbidden = _has_forbidden_key(res_pub.data)
        self.assertEqual(forbidden, set(), f"Rò rỉ khoá cấm trong public API: {forbidden}")
