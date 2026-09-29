"""
Kiểm thử sinh và gợi ý slug tiếng Việt (CMS-03-AC1..AC3, BR-ND-04).
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.content.body.slug import slugify_vi, suggest_unique_slug
from apps.content.models.entries import Entry

User = get_user_model()



class SlugTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="slug_user", password="password")

    def test_cms_03_ac1_slugify_clean(self):
        """Sinh slug sạch từ tiêu đề tiếng Việt."""
        self.assertEqual(slugify_vi("Cách rã đông cá thu"), "cach-ra-dong-ca-thu")

    def test_cms_03_ac2_slug_punctuation(self):
        """Slug chữ thường, không dấu, gạch nối, không gạch nối đôi hay ở đầu/cuối."""
        self.assertEqual(slugify_vi("Cá Thu  Đông!!"), "ca-thu-dong")

    def test_cms_03_ac3_suggest_unique_slug(self):
        """Khi slug đã tồn tại (kể cả bài đã gỡ) -> gợi ý <base>-<n nhỏ nhất >= 2 còn trống>."""
        Entry.objects.create(
            title="Cách rã đông cá thu",
            slug="cach-ra-dong-ca-thu",
            status="unpublished",
            created_by=self.user,
        )
        suggestion = suggest_unique_slug("cach-ra-dong-ca-thu")
        self.assertEqual(suggestion, "cach-ra-dong-ca-thu-2")

        # Nếu đã có cả -2 -> gợi ý -3
        Entry.objects.create(
            title="Cách rã đông cá thu 2",
            slug="cach-ra-dong-ca-thu-2",
            created_by=self.user,
        )
        suggestion_3 = suggest_unique_slug("cach-ra-dong-ca-thu")
        self.assertEqual(suggestion_3, "cach-ra-dong-ca-thu-3")
