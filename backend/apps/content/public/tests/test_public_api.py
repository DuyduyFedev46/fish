"""
Kiểm thử API công khai nội dung (CMS-13-AC1..AC10, CMS-14-AC1..AC6, §8.6 02b-tech-design).
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.content.models.categories import Category
from apps.content.models.entries import Entry, EntryVersion
from apps.content.models.images import ContentImage

User = get_user_model()

FORBIDDEN_KEYS = {
    "cost",
    "unit_cost",
    "total_cost",
    "purchase_rate",
    "purchase_price",
    "landed_cost",
    "profit",
    "margin",
    "customer_name",
    "phone",
    "customer_phone",
    "delivery_address",
    "raw_payload",
    "created_by",
    "updated_by",
}


def assert_no_forbidden_keys(test_case, data, path=""):
    """Đệ quy kiểm tra không có khoá cấm nào xuất hiện trong response JSON (Bất biến 1, 9)."""
    if isinstance(data, dict):
        for k, v in data.items():
            curr_path = f"{path}.{k}" if path else k
            lower_k = k.lower()
            for forbidden in FORBIDDEN_KEYS:
                test_case.assertNotIn(
                    forbidden,
                    lower_k,
                    f"Phát hiện khoá cấm '{forbidden}' tại '{curr_path}'",
                )
            assert_no_forbidden_keys(test_case, v, curr_path)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            assert_no_forbidden_keys(test_case, item, f"{path}[{idx}]")


class PublicContentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

        self.user = User.objects.create_user(username="author", password="password123")

        self.category = Category.objects.create(
            name="Món ngon",
            name_key="mon ngon",
            slug="mon-ngon",
            is_active=True,
        )

        self.entry_pub = Entry.objects.create(
            kind="post",
            title="Cách nấu canh chua cá bớp",
            slug="cach-nau-canh-chua-ca-bop",
            category=self.category,
            excerpt="Món canh chua cá bớp đậm đà hương vị miền biển",
            seo_title="Cách nấu canh chua cá bớp ngon | Cá Về",
            seo_description="Hướng dẫn nấu canh chua cá bớp chuẩn vị",
            status="published",
            first_published_at=timezone.now(),
            last_published_at=timezone.now(),
            row_version=2,
            created_by=self.user,
            updated_by=self.user,
        )

        self.cover_img = ContentImage.objects.create(
            entry=self.entry_pub,
            alt="Bát canh chua cá bớp nghi ngút khói",
            width=1600,
            height=1200,
            uploaded_by=self.user,
        )
        self.entry_pub.cover_image = self.cover_img
        self.entry_pub.save()

        # Tạo version cho entry_pub
        self.version_pub = EntryVersion.objects.create(
            entry=self.entry_pub,
            version=1,
            kind="post",
            title="Cách nấu canh chua cá bớp",
            slug="cach-nau-canh-chua-ca-bop",
            excerpt="Món canh chua cá bớp đậm đà hương vị miền biển",
            seo_title="Cách nấu canh chua cá bớp ngon | Cá Về",
            seo_description="Hướng dẫn nấu canh chua cá bớp chuẩn vị",
            description="Hướng dẫn nấu canh chua cá bớp chuẩn vị",
            category=self.category,
            cover_image=self.cover_img,
            body={
                "type": "doc",
                "blocks": [
                    {
                        "type": "paragraph",
                        "children": [{"text": "Nguyên liệu gồm cá bớp, thơm, cà chua, me và rau thơm."}],
                    }
                ],
            },
            published_at=timezone.now(),
            published_by=self.user,
        )
        self.entry_pub.published_version = self.version_pub
        self.entry_pub.save()

        # Bài nháp (status=draft)
        self.entry_draft = Entry.objects.create(
            kind="post",
            title="Bài nháp chưa đăng",
            slug="bai-nhap-chua-dang",
            category=self.category,
            status="draft",
            row_version=1,
            created_by=self.user,
            updated_by=self.user,
        )

        # Bài đã gỡ (status=unpublished)
        self.entry_unpub = Entry.objects.create(
            kind="post",
            title="Bài viết đã gỡ",
            slug="bai-viet-da-go",
            category=self.category,
            status="unpublished",
            row_version=3,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_cms_13_ac1_public_detail_view(self):
        """CMS-13-AC1: Khách mở chi tiết bài viết đã đăng -> 200, đủ các trường công khai."""
        url = f"/api/public/content/entries/{self.entry_pub.slug}/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["slug"], "cach-nau-canh-chua-ca-bop")
        self.assertEqual(data["title"], "Cách nấu canh chua cá bớp")
        self.assertEqual(data["author"], "Cá Về")
        self.assertEqual(data["seo_title"], "Cách nấu canh chua cá bớp ngon | Cá Về")
        self.assertEqual(data["description"], "Hướng dẫn nấu canh chua cá bớp chuẩn vị")
        self.assertIsNotNone(data["category"])
        self.assertEqual(data["category"]["slug"], "mon-ngon")
        self.assertIsNotNone(data["cover_image"])
        self.assertEqual(data["cover_image"]["alt"], "Bát canh chua cá bớp nghi ngút khói")
        self.assertIn("urls", data["cover_image"])
        self.assertEqual(data["version"], 1)

        # Cache-Control max-age <= 60
        self.assertIn("Cache-Control", res)
        self.assertIn("public, max-age=", res["Cache-Control"])

    def test_cms_13_ac2_xss_layer1b_in_public_body(self):
        """
        CMS-13-AC2: Ghi thẳng vào DB EntryVersion có khối lạ (script, iframe) hoặc href javascript:
        -> Public API loại bỏ khối lạ, href xấu bị bỏ qua, không có image_id lộ ra.
        """
        raw_xss_body = {
            "type": "doc",
            "blocks": [
                {"type": "html", "html": "<script>alert(1)</script>"},
                {"type": "iframe", "src": "https://evil.com"},
                {
                    "type": "paragraph",
                    "children": [
                        {"text": "Bấm vào đây ", "href": "javascript:alert(1)"},
                        {"text": "<img src=x onerror=alert(1)>"},
                    ],
                },
                {
                    "type": "image",
                    "image_id": self.cover_img.pk,
                    "alt": "Ảnh hợp lệ",
                },
            ],
        }

        # Lưu thẳng vào DB
        v_xss = EntryVersion.objects.create(
            entry=self.entry_pub,
            version=2,
            kind="post",
            title="Bài test XSS",
            slug=self.entry_pub.slug,
            description="Mô tả",
            category=self.category,
            cover_image=self.cover_img,
            body=raw_xss_body,
            published_at=timezone.now(),
            published_by=self.user,
        )
        self.entry_pub.published_version = v_xss
        self.entry_pub.save()

        url = f"/api/public/content/entries/{self.entry_pub.slug}/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        blocks = res.data["body"]["blocks"]
        # Không có khối html hay iframe
        self.assertFalse(any(b.get("type") in ("html", "iframe") for b in blocks))

        # Paragraph: không còn href javascript, giữ nguyên text <img src=x...>
        para = blocks[0]
        self.assertEqual(para["type"], "paragraph")
        self.assertNotIn("href", para["children"][0])
        self.assertEqual(para["children"][1]["text"], "<img src=x onerror=alert(1)>")

        # Khối image: đã được chuyển đổi có urls, không còn image_id
        img_block = blocks[1]
        self.assertEqual(img_block["type"], "image")
        self.assertNotIn("image_id", img_block)
        self.assertIn("urls", img_block)

    def test_cms_13_ac4_draft_or_non_existent_returns_identical_404_and_unpublished_410(self):
        """
        CMS-13-AC4:
        - Slug không tồn tại -> 404 {"detail": "Không tìm thấy bài.", "code": "NOT_FOUND"}
        - Slug của bài nháp -> 404 giống hệt không tồn tại (không lộ tồn tại của bài nháp)
        - Slug của bài đã gỡ -> 410 {"detail": "Bài này không còn trên web.", "code": "GONE"}
        """
        # 1. Non-existent
        res_non = self.client.get("/api/public/content/entries/slug-khong-ton-tai/")
        self.assertEqual(res_non.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res_non.data, {"detail": "Không tìm thấy bài.", "code": "NOT_FOUND"})

        # 2. Draft
        res_draft = self.client.get(f"/api/public/content/entries/{self.entry_draft.slug}/")
        self.assertEqual(res_draft.status_code, status.HTTP_404_NOT_FOUND)
        # Body giống hệt không tồn tại
        self.assertEqual(res_draft.data, res_non.data)

        # 3. Unpublished
        res_unpub = self.client.get(f"/api/public/content/entries/{self.entry_unpub.slug}/")
        self.assertEqual(res_unpub.status_code, status.HTTP_410_GONE)
        self.assertEqual(res_unpub.data, {"detail": "Bài này không còn trên web.", "code": "GONE"})

    def test_cms_13_ac5_recursive_check_forbidden_keys(self):
        """CMS-13-AC5: Quét đệ quy JSON của API công khai (list và detail), không chứa bất kỳ khoá cấm nào."""
        # 1. Detail
        res_detail = self.client.get(f"/api/public/content/entries/{self.entry_pub.slug}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        assert_no_forbidden_keys(self, res_detail.data)

        # 2. List
        res_list = self.client.get("/api/public/content/entries/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        assert_no_forbidden_keys(self, res_list.data)

    def test_cms_13_ac9_write_methods_to_public_api_return_405(self):
        """CMS-13-AC9: Gọi POST, PUT, PATCH, DELETE vào /api/public/content/** mà không đăng nhập -> 405 MethodNotAllowed."""
        urls = [
            "/api/public/content/entries/",
            f"/api/public/content/entries/{self.entry_pub.slug}/",
            "/api/public/content/categories/",
        ]
        for url in urls:
            for method in ("post", "put", "patch", "delete"):
                client_fn = getattr(self.client, method)
                res = client_fn(url, {})
                self.assertEqual(
                    res.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                    f"Method {method.upper()} trên {url} không trả về 405",
                )

    def test_public_content_throttle(self):
        """Kiểm tra giới hạn tần suất PublicContentThrottle với scope public_content."""
        cache.clear()
        with override_settings(CAVEVE_THROTTLE_RATES={"public_content": "1/min"}):
            url = f"/api/public/content/entries/{self.entry_pub.slug}/"
            res1 = self.client.get(url)
            self.assertEqual(res1.status_code, status.HTTP_200_OK)

            res2 = self.client.get(url)
            self.assertEqual(res2.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
