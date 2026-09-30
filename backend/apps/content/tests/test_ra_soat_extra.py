"""
A5 (2026-09-30-ra-soat-agy) — ca ngoài đường thuận bổ sung cho hồ sơ 2026-09-28-cms-viet-bai.
Chỉ thêm test cho hành vi hệ thống ĐÃ đúng (GREEN); lỗi thật tìm thấy trong lượt rà soát này
(F1 IDOR ảnh khi tạo bài — trùng SR-18) được để riêng ở
doc/features/2026-09-30-ra-soat-agy/repro/A5-f1-idor-cover-image-on-create.py, KHÔNG ở đây.
"""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import AuditLog
from apps.catalog.images.tests.factories import make_image_bytes
from apps.content.entries.services import publish_entry
from apps.content.models.categories import Category
from apps.content.models.entries import Entry
from apps.content.models.images import ContentImage

User = get_user_model()


def _client_for(user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user)
    return client


class DoubleClickUnpublishTests(APITestCase):
    """CMS-12 — bấm đúp nút 'Gỡ bài' chỉ được xử lý 1 lần (khoá lạc quan qua row_version)."""

    def setUp(self):
        self.quan_ly = User.objects.create_user(username="ra_ql_dbl", password="x")
        g_ql, _ = Group.objects.get_or_create(name="quan_ly")
        self.quan_ly.groups.add(g_ql)
        self.quan_ly = User.objects.get(pk=self.quan_ly.pk)

        self.category = Category.objects.create(
            name="Ra soat dbl", name_key="ra soat dbl", slug="ra-soat-dbl", is_active=True
        )
        self.entry = Entry.objects.create(
            kind="post",
            title="Bai kiem tra bam dup go bai",
            slug="bai-kiem-tra-bam-dup-go-bai",
            category=self.category,
            excerpt="du lieu gia",
            seo_description="mo ta du lieu gia",
            body={"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "noi dung"}]}]},
            row_version=1,
            created_by=self.quan_ly,
            updated_by=self.quan_ly,
        )
        img = self.entry.images.create(
            alt="anh bia", width=100, height=100, uploaded_by=self.quan_ly
        )
        self.entry.cover_image = img
        self.entry.save(update_fields=["cover_image"])
        publish_entry(
            entry=Entry.objects.get(pk=self.entry.pk),
            actor=self.quan_ly,
            row_version=self.entry.row_version,
            checklist_confirmed=True,
            acknowledge_warnings=False,
        )
        self.entry.refresh_from_db()

    def test_double_click_unpublish_only_processed_once(self):
        client = _client_for(self.quan_ly)
        row_version = self.entry.row_version

        # Mô phỏng bấm đúp: 2 request "gỡ bài" gửi liên tiếp với CÙNG row_version đọc lúc mở màn,
        # giống việc người dùng bấm 2 lần trước khi UI kịp khoá nút / phản hồi request đầu.
        resp1 = client.post(
            f"/api/content/entries/{self.entry.id}/unpublish/",
            {"row_version": row_version, "reason": "wrong_price"},
            format="json",
        )
        resp2 = client.post(
            f"/api/content/entries/{self.entry.id}/unpublish/",
            {"row_version": row_version, "reason": "wrong_price"},
            format="json",
        )

        statuses = sorted([resp1.status_code, resp2.status_code])
        self.assertEqual(
            statuses,
            [200, 409],
            f"Bấm đúp phải có đúng 1 request 200 và 1 request 409 STALE_VERSION, có: {statuses}",
        )

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, "unpublished")

        # Không phình AuditLog: đúng 1 dòng content_unpublish cho bài này.
        count = AuditLog.objects.filter(action="content_unpublish", object_id=str(self.entry.id)).count()
        self.assertEqual(count, 1, "Bấm đúp không được ghi 2 dòng AuditLog content_unpublish")


class DraftNotExposedByPublicApiTests(APITestCase):
    """CMS-13-AC4 mở rộng: kể cả khi biết CHÍNH XÁC slug + id nội bộ của một bài Nháp, API công
    khai vẫn trả 404 giống hệt bài không tồn tại (không có cách nào phân biệt để dò bài nháp)."""

    def setUp(self):
        self.quan_ly = User.objects.create_user(username="ra_ql_draft", password="x")
        g_ql, _ = Group.objects.get_or_create(name="quan_ly")
        self.quan_ly.groups.add(g_ql)
        self.category = Category.objects.create(
            name="Ra soat draft", name_key="ra soat draft", slug="ra-soat-draft", is_active=True
        )
        self.draft = Entry.objects.create(
            kind="post",
            title="Bai nhap chua duoc duyet - du lieu gia",
            slug="bai-nhap-chua-duoc-duyet-ra-soat",
            category=self.category,
            status="draft",
            row_version=1,
            created_by=self.quan_ly,
            updated_by=self.quan_ly,
        )

    def test_draft_slug_and_nonexistent_slug_return_identical_body(self):
        from django.test import Client

        client = Client()
        resp_draft = client.get(f"/api/public/content/entries/{self.draft.slug}/")
        resp_missing = client.get("/api/public/content/entries/slug-chac-chan-khong-ton-tai-ra-soat/")

        self.assertEqual(resp_draft.status_code, 404)
        self.assertEqual(resp_missing.status_code, 404)
        self.assertEqual(
            resp_draft.json(),
            resp_missing.json(),
            "Bài Nháp và slug không tồn tại phải trả về body 404 GIỐNG HỆT nhau (không lộ bài nháp có tồn tại)",
        )


class CoverImageNeverDeletedTests(APITestCase):
    """CMS-05-AC5: ảnh gỡ khỏi bài rồi đăng phiên bản mới -> object KHÔNG bị xoá ở storage
    (BR-DM-14) và bản ghi ContentImage vẫn còn — trước lượt A5 chưa có test thật cho AC này
    (review-cms-golive-fe-qa.md: 'Không có test gỡ ảnh khỏi bài thì URL cũ vẫn còn')."""

    def setUp(self):
        self.quan_ly = User.objects.create_user(username="ra_ql_img5", password="x")
        g_ql, _ = Group.objects.get_or_create(name="quan_ly")
        self.quan_ly.groups.add(g_ql)
        self.quan_ly = User.objects.get(pk=self.quan_ly.pk)
        self.client.force_authenticate(self.quan_ly)

        self.category = Category.objects.create(
            name="Ra soat img5", name_key="ra soat img5", slug="ra-soat-img5", is_active=True
        )
        self.entry = Entry.objects.create(
            kind="post",
            title="Bai kiem tra go anh khong xoa object",
            slug="bai-kiem-tra-go-anh-khong-xoa-object",
            category=self.category,
            excerpt="du lieu gia",
            seo_description="mo ta du lieu gia",
            row_version=1,
            created_by=self.quan_ly,
            updated_by=self.quan_ly,
        )

    def _upload(self, filename="anh.jpg"):
        raw = make_image_bytes(size=(800, 600), fmt="JPEG")
        uploaded = SimpleUploadedFile(filename, raw, content_type="image/jpeg")
        resp = self.client.post(
            f"/api/content/entries/{self.entry.pk}/images/", {"file": uploaded}, format="multipart"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        return resp.json()

    def test_removed_image_object_and_row_still_exist_after_republish(self):
        cover = self._upload("bia.jpg")
        extra = self._upload("phu.jpg")  # ảnh X sẽ bị gỡ khỏi bài ở phiên bản 2

        # Phiên bản 1: có cả 2 ảnh (ảnh bìa + 1 ảnh trong thân bài)
        resp = self.client.patch(
            f"/api/content/entries/{self.entry.pk}/",
            {
                "row_version": self.entry.row_version,
                "cover_image": cover["id"],
                "body": {
                    "type": "doc",
                    "blocks": [{"type": "image", "image_id": extra["id"], "alt": "Ảnh X"}],
                },
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        row_version = resp.json()["row_version"]

        resp = self.client.post(
            f"/api/content/entries/{self.entry.pk}/publish/",
            {"row_version": row_version, "checklist_confirmed": True, "acknowledge_warnings": False},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        extra_image_id = extra["id"]
        extra_record = ContentImage.objects.get(pk=extra_image_id)
        saved_path = os.path.join(settings.MEDIA_ROOT, f"content/{self.entry.pk}/{extra_record.image_id}/sm.webp")
        self.assertTrue(os.path.exists(saved_path), "Ảnh X phải thật sự được ghi ra storage ở phiên bản 1")

        # Phiên bản 2: gỡ ảnh X khỏi thân bài (chỉ còn ảnh bìa)
        self.entry.refresh_from_db()
        resp = self.client.patch(
            f"/api/content/entries/{self.entry.pk}/",
            {
                "row_version": self.entry.row_version,
                "body": {
                    "type": "doc",
                    "blocks": [{"type": "paragraph", "children": [{"text": "Da go anh X khoi bai"}]}],
                },
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        row_version_2 = resp.json()["row_version"]

        resp = self.client.post(
            f"/api/content/entries/{self.entry.pk}/publish/",
            {"row_version": row_version_2, "checklist_confirmed": True, "acknowledge_warnings": False},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        # BE không xoá bản ghi ContentImage của X (BR-DM-14) — vẫn còn trong DB
        self.assertTrue(
            ContentImage.objects.filter(pk=extra_image_id).exists(),
            "Ảnh X bị gỡ khỏi thân bài KHÔNG được xoá bản ghi ContentImage (BR-DM-14)",
        )
        # File vật lý ở storage vẫn còn nguyên (không có API/hàm nào xoá object cũ)
        self.assertTrue(
            os.path.exists(saved_path),
            "Ảnh X bị gỡ khỏi thân bài nhưng object ở storage vẫn phải còn (URL cũ còn dùng được, BR-DM-14)",
        )
        # Không có phương thức xoá nào tồn tại ở tầng storage (kiểm cấu trúc, đúng chủ đích BR-DM-14)
        from apps.catalog.images.storage import LocalItemImageStorage

        self.assertFalse(
            hasattr(LocalItemImageStorage, "delete"),
            "Storage không được có hàm xoá object (BR-DM-14)",
        )
