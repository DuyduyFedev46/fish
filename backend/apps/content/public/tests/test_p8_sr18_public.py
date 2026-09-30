"""
P8 Lô 6 — SR-18-AC3 (lớp 1b): API công khai bỏ khối ảnh / ảnh bìa không thuộc bài (dữ liệu cũ).
Dữ liệu giả.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.content.models.categories import Category
from apps.content.models.entries import Entry, EntryVersion
from apps.content.models.images import ContentImage

User = get_user_model()


class Sr18PublicLayer1bTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(username="sr18_pub_author", password="x")
        self.cat = Category.objects.create(name="Sr18 pub", name_key="sr18 pub", slug="sr18-pub", is_active=True)
        # Bài A còn là NHÁP, có ảnh riêng — không được lộ qua bài khác
        self.entry_a = Entry.objects.create(kind="post", title="A nháp", slug="a-nhap", status="draft",
                                            created_by=self.user)
        self.img_a = ContentImage.objects.create(entry=self.entry_a, alt="Ảnh nháp bài A", width=10, height=10,
                                                 uploaded_by=self.user)
        # Bài B đã đăng
        self.entry_b = Entry.objects.create(kind="post", title="B đăng", slug="b-dang", status="published",
                                            category=self.cat, first_published_at=timezone.now(),
                                            created_by=self.user)
        self.img_b = ContentImage.objects.create(entry=self.entry_b, alt="Ảnh của B", width=20, height=20,
                                                 uploaded_by=self.user)

    def publish(self, *, cover, image_ids):
        blocks = [{"type": "paragraph", "children": [{"text": "Nội dung"}]}]
        blocks += [{"type": "image", "image_id": i, "alt": "a", "caption": "c"} for i in image_ids]
        ver = EntryVersion.objects.create(
            entry=self.entry_b, version=1, kind="post", title="B đăng", slug="b-dang", description="d",
            category=self.cat, cover_image=cover, body={"type": "doc", "blocks": blocks},
            published_at=timezone.now(), published_by=self.user,
        )
        self.entry_b.published_version = ver
        self.entry_b.save()
        return ver

    def _assert_no_a(self, text):
        self.assertNotIn(f"content/{self.entry_a.pk}/", text)
        self.assertNotIn(self.img_a.image_id, text)
        self.assertNotIn("Ảnh nháp bài A", text)

    def test_sr18_ac3_chi_tiet_bo_khoi_anh_va_bia_cua_bai_khac(self):
        self.publish(cover=self.img_a, image_ids=[self.img_a.pk, self.img_b.pk])
        res = self.client.get("/api/public/content/entries/b-dang/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsNone(data["cover_image"])
        images = [b for b in data["body"]["blocks"] if b["type"] == "image"]
        self.assertEqual(len(images), 1)
        self.assertIn(self.img_b.image_id, images[0]["urls"]["md"])
        self._assert_no_a(res.content.decode())

    def test_sr18_ac3_danh_sach_bia_cua_bai_khac_null(self):
        self.publish(cover=self.img_a, image_ids=[])
        res = self.client.get("/api/public/content/entries/")
        self.assertEqual(res.status_code, 200)
        rows = res.json()["results"] if isinstance(res.json(), dict) else res.json()
        row = next(r for r in rows if r["slug"] == "b-dang")
        self.assertIsNone(row["cover_image"])
        self._assert_no_a(res.content.decode())

    def test_sr18_ac3_doi_chung_anh_cua_chinh_bai_van_hien(self):
        self.publish(cover=self.img_b, image_ids=[self.img_b.pk])
        data = self.client.get("/api/public/content/entries/b-dang/").json()
        self.assertIsNotNone(data["cover_image"])
        self.assertIn(self.img_b.image_id, data["cover_image"]["urls"]["sm"])
        self.assertEqual(len([b for b in data["body"]["blocks"] if b["type"] == "image"]), 1)
        rows = self.client.get("/api/public/content/entries/").json()
        rows = rows["results"] if isinstance(rows, dict) else rows
        self.assertIsNotNone(next(r for r in rows if r["slug"] == "b-dang")["cover_image"])

    def test_sr18_ac3_trang_theo_vai_tro_khong_lo_anh_bai_khac(self):
        """Không có endpoint công khai nào khác trả ảnh: quét chi tiết + danh sách + footer không chứa ảnh nháp A."""
        self.publish(cover=self.img_a, image_ids=[self.img_a.pk])
        for url in ("/api/public/content/entries/b-dang/", "/api/public/content/entries/",
                    "/api/public/content/footer-links/"):
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, url)
            self._assert_no_a(res.content.decode())
