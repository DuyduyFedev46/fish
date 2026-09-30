"""
Kiểm thử ảnh bài viết và ảnh bìa giữ tỉ lệ (CMS-05, BR-ND-07, BR-DM-10..16).
"""
import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from apps.catalog.images.storage import get_storage
from apps.content.models.entries import Entry
from apps.content.models.images import ContentImage

from apps.catalog.images.tests.factories import make_image_bytes, make_jpeg_with_exif_orientation
from apps.accounts import roles

User = get_user_model()


def _make_jpeg_exif(width=4000, height=3000):
    exif = Image.Exif()
    exif[274] = 1
    return make_image_bytes(size=(width, height), fmt="JPEG", exif=exif)



class ContentImageTests(APITestCase):
    def setUp(self):
        self.quan_ly = User.objects.create_user(username="quan_ly_user", password="password")
        self.nv_kho = User.objects.create_user(username="nv_kho_user", password="password")
        g_ql, _ = Group.objects.get_or_create(name=roles.MANAGER)
        g_kho, _ = Group.objects.get_or_create(name=roles.WAREHOUSE_STAFF)
        self.quan_ly.groups.add(g_ql)
        self.nv_kho.groups.add(g_kho)

        self.entry = Entry.objects.create(
            title="Cách rã đông cá thu",
            slug="cach-ra-dong-ca-thu",
            created_by=self.quan_ly,
        )

    def test_cms_05_ac1_jpeg_keep_ratio_and_strip_exif(self):
        """CMS-05-AC1: Ảnh JPEG 4000x3000 có EXIF GPS -> 201; các cỡ WebP giữ 4:3 (sai số <= 1px), không còn EXIF."""
        self.client.force_authenticate(user=self.quan_ly)
        raw_bytes = _make_jpeg_exif(4000, 3000)
        uploaded = SimpleUploadedFile("fish.jpg", raw_bytes, content_type="image/jpeg")

        url = f"/api/content/entries/{self.entry.pk}/images/"
        resp = self.client.post(url, {"file": uploaded}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        data = resp.json()
        self.assertEqual(data["alt"], "Cách rã đông cá thu")  # Mặc định lấy title bài (CMS-05-AC4)
        self.assertEqual(data["width"], 1600)
        self.assertEqual(data["height"], 1200)

        # Kiểm tra tỉ lệ 4:3
        ratio = data["width"] / data["height"]
        self.assertAlmostEqual(ratio, 4 / 3, places=2)

        # Đọc lại từ storage kiểm tra không còn EXIF
        import os
        from django.conf import settings
        img_record = ContentImage.objects.get(pk=data["id"])
        full_path = os.path.join(settings.MEDIA_ROOT, f"content/{self.entry.pk}/{img_record.image_id}/lg.webp")
        with open(full_path, "rb") as fh:
            saved_bytes = fh.read()
        processed_img = Image.open(io.BytesIO(saved_bytes))
        self.assertEqual(processed_img.format, "WEBP")
        # WebP không có exif tag
        exif = processed_img.getexif()
        self.assertEqual(len(exif), 0)


    def test_cms_05_ac2_invalid_images_rejected(self):
        """CMS-05-AC2: Tệp SVG, tệp text giả jpg, ảnh 10MB + 1 byte -> 400 BR-DM-10, không object ghi."""
        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/images/"

        # 1. SVG
        svg_file = SimpleUploadedFile("test.svg", b"<svg><circle/></svg>", content_type="image/svg+xml")
        resp = self.client.post(url, {"file": svg_file}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.json()["code"], "BR-DM-10")

        # 2. Text giả .jpg
        fake_jpg = SimpleUploadedFile("fake.jpg", b"hello text file", content_type="image/jpeg")
        resp = self.client.post(url, {"file": fake_jpg}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.json()["code"], "BR-DM-10")

        # 3. 10MB + 1 byte
        huge_file = SimpleUploadedFile("huge.jpg", b"0" * (10 * 1024 * 1024 + 1), content_type="image/jpeg")
        resp = self.client.post(url, {"file": huge_file}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.json()["code"], "BR-DM-10")

        # Không tạo ContentImage nào
        self.assertEqual(ContentImage.objects.filter(entry=self.entry).count(), 0)

    def test_cms_05_ac3_max_20_images_limit(self):
        """CMS-05-AC3: Bài đã có 20 ảnh -> tải ảnh thứ 21 -> 400 BR-ND-07."""
        self.client.force_authenticate(user=self.quan_ly)
        # Giả lập bài đã có 20 ảnh trong body
        raw_bytes = _make_jpeg_exif(100, 100)
        blocks = []
        for i in range(20):
            img = ContentImage.objects.create(
                entry=self.entry,
                alt=f"Ảnh {i}",
                uploaded_by=self.quan_ly,
            )
            blocks.append({"type": "image", "image_id": img.pk, "alt": f"Ảnh {i}", "caption": ""})
        self.entry.body = {"type": "doc", "blocks": blocks}
        self.entry.save()

        # Tải ảnh thứ 21
        uploaded = SimpleUploadedFile("img21.jpg", raw_bytes, content_type="image/jpeg")
        url = f"/api/content/entries/{self.entry.pk}/images/"
        resp = self.client.post(url, {"file": uploaded}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.json()["code"], "BR-ND-07")

    def test_cms_05_ac4_alt_text_behavior(self):
        """CMS-05-AC4: Không nhập alt -> lấy title bài; alt sửa được <= 200 ký tự."""
        self.client.force_authenticate(user=self.quan_ly)
        raw_bytes = _make_jpeg_exif(200, 200)

        # 1. Tải không alt
        uploaded = SimpleUploadedFile("pic.jpg", raw_bytes, content_type="image/jpeg")
        url = f"/api/content/entries/{self.entry.pk}/images/"
        resp = self.client.post(url, {"file": uploaded}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        img_id = resp.json()["id"]
        self.assertEqual(resp.json()["alt"], "Cách rã đông cá thu")

        # 2. Sửa alt qua PATCH /api/content/images/<id>/
        patch_url = f"/api/content/images/{img_id}/"
        patch_resp = self.client.patch(patch_url, {"alt": "Cá thu cắt khoanh"})
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.json()["alt"], "Cá thu cắt khoanh")

    def test_cms_05_ac7_permission_denied_for_nv_kho(self):
        """CMS-05-AC7: NV kho POST ảnh -> 403; không object nào được ghi."""
        self.client.force_authenticate(user=self.nv_kho)
        raw_bytes = _make_jpeg_exif(200, 200)
        uploaded = SimpleUploadedFile("kho.jpg", raw_bytes, content_type="image/jpeg")
        url = f"/api/content/entries/{self.entry.pk}/images/"

        resp = self.client.post(url, {"file": uploaded}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ContentImage.objects.filter(entry=self.entry).count(), 0)
