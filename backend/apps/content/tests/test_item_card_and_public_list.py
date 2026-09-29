"""
Kiểm thử Lô 6 CMS:
- Story CMS-06: Thẻ mặt hàng dẫn sang Shop (AC1, AC2, AC6, AC7)
- Story CMS-14: Danh sách bài và chuyên mục trên web (AC1, AC2, AC5, AC6)
"""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.content.body.scan import scan_entry_warnings
from apps.content.models.categories import Category
from apps.content.models.entries import Entry, EntryVersion

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


class ItemCardAndPublicListTests(APITestCase):
    def setUp(self):
        # 1. Tạo nhóm và user
        self.grp_quan_ly = Group.objects.get(name="quan_ly")
        self.manager = User.objects.create_user(username="manager_u6", password="password")
        self.manager.groups.add(self.grp_quan_ly)

        # 2. Tạo Item và Price
        self.item_group, _ = ItemGroup.objects.get_or_create(name="Hải sản tươi")
        self.item_thu = Item.objects.create(
            code="CA-THU-1KG",
            name="Cá thu Phan Thiết 1kg",
            item_group=self.item_group,
            is_active=True,
        )
        self.price_list, _ = PriceList.objects.get_or_create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(
            item=self.item_thu,
            price_list=self.price_list,
            rate=250000,
            valid_from=timezone.localdate() - timedelta(days=5),
        )

        self.item_inactive = Item.objects.create(
            code="CA-NGU-1KG",
            name="Cá ngừ đại dương",
            item_group=self.item_group,
            is_active=False,
        )

        # 3. Tạo Category
        from apps.content.body.slug import fold_text
        self.cat_cong_thuc = Category.objects.create(
            name="Công thức nấu",
            name_key=fold_text("Công thức nấu"),
            slug="cong-thuc",
            order=1,
            is_active=True,
        )
        self.cat_meo_bep = Category.objects.create(
            name="Mẹo nhà bếp",
            name_key=fold_text("Mẹo nhà bếp"),
            slug="meo-bep",
            order=2,
            is_active=True,
        )
        self.cat_empty = Category.objects.create(
            name="Chuyên mục trống",
            name_key=fold_text("Chuyên mục trống"),
            slug="trong",
            order=3,
            is_active=True,
        )

    def test_cms_06_ac1_save_draft_with_valid_item_card(self):
        """CMS-06-AC1: Lưu nháp với khối item_card có mã hợp lệ -> 200/201."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "kind": "post",
            "title": "Món ngon với cá thu",
            "category": self.cat_cong_thuc.id,
            "body": {
                "type": "doc",
                "blocks": [
                    {"type": "paragraph", "children": [{"text": "Giới thiệu cá thu"}]},
                    {"type": "item_card", "item_code": "CA-THU-1KG"},
                ],
            },
        }
        res = self.client.post("/api/content/entries/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(res.data["body"]["blocks"]), 2)
        self.assertEqual(res.data["body"]["blocks"][1]["item_code"], "CA-THU-1KG")

    def test_cms_06_ac2_save_draft_with_non_existent_item_card_raises_br_nd_10(self):
        """CMS-06-AC2: Lưu body có item_card với mã không tồn tại -> 400 BR-ND-10; body không đổi."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "kind": "post",
            "title": "Bài viết thử nghiệm mã sai",
            "category": self.cat_cong_thuc.id,
            "body": {
                "type": "doc",
                "blocks": [
                    {"type": "paragraph", "children": [{"text": "Thử mã không có"}]},
                    {"type": "item_card", "item_code": "MA-KHONG-TON-TAI-999"},
                ],
            },
        }
        res = self.client.post("/api/content/entries/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["code"], "BR-ND-10")
        self.assertFalse(Entry.objects.filter(title="Bài viết thử nghiệm mã sai").exists())

    def test_cms_06_ac6_warning_item_unavailable_when_inactive_or_no_price(self):
        """
        CMS-06-AC6: Bài có thẻ mặt hàng đang ẩn hoặc không có giá hiệu lực:
        Quét cảnh báo trả về item_unavailable.
        """
        entry = Entry.objects.create(
            kind="post",
            title="Bài có cá ngừ",
            slug="bai-co-ca-ngu",
            category=self.cat_cong_thuc,
            created_by=self.manager,
            body={
                "type": "doc",
                "blocks": [
                    {"type": "paragraph", "children": [{"text": "Thử mặt hàng ẩn"}]},
                    {"type": "item_card", "item_code": "CA-NGU-1KG"},
                ],
            },
        )
        warnings = scan_entry_warnings(entry)
        item_warnings = [w for w in warnings if w["type"] == "item_unavailable"]
        self.assertEqual(len(item_warnings), 1)
        self.assertEqual(item_warnings[0]["item_code"], "CA-NGU-1KG")

    def test_cms_14_ac1_public_entries_list_pagination_and_exclusion(self):
        """
        CMS-14-AC1: 25 bài Đã đăng, 3 bài Nháp, 2 Trang:
        - Mở danh sách công khai: Trang 1 có 12 bài, mới nhất trước, có nút sang trang 2;
        - Không có Nháp và Trang.
        """
        now = timezone.now()
        # 1. Tạo 25 bài Đã đăng (post)
        for i in range(1, 26):
            entry = Entry.objects.create(
                kind="post",
                title=f"Bài viết đã đăng {i:02d}",
                slug=f"bai-viet-{i:02d}",
                category=self.cat_cong_thuc,
                status="published",
                first_published_at=now - timedelta(hours=30 - i),
                created_by=self.manager,
            )
            v = EntryVersion.objects.create(
                entry=entry,
                version=1,
                title=entry.title,
                slug=entry.slug,
                category=self.cat_cong_thuc,
                body={"type": "doc", "blocks": []},
                description="Mô tả bài viết",
                published_at=entry.first_published_at,
                published_by=self.manager,
            )
            entry.published_version = v
            entry.save()

        # 2. Tạo 3 bài Nháp
        for i in range(1, 4):
            Entry.objects.create(
                kind="post",
                title=f"Bài nháp {i}",
                slug=f"bai-nhap-{i}",
                category=self.cat_cong_thuc,
                status="draft",
                created_by=self.manager,
            )

        # 3. Tạo 2 Trang (kind="page") Đã đăng
        for i in range(1, 3):
            page_entry = Entry.objects.create(
                kind="page",
                title=f"Trang tĩnh {i}",
                slug=f"trang-tinh-{i}",
                status="published",
                first_published_at=now - timedelta(days=1),
                created_by=self.manager,
            )
            pv = EntryVersion.objects.create(
                entry=page_entry,
                version=1,
                title=page_entry.title,
                slug=page_entry.slug,
                body={"type": "doc", "blocks": []},
                description="Mô tả trang tĩnh",
                published_at=page_entry.first_published_at,
                published_by=self.manager,
            )
            page_entry.published_version = pv
            page_entry.save()

        # Gọi GET trang 1
        res1 = self.client.get("/api/public/content/entries/?page=1")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data["count"], 25)
        self.assertEqual(len(res1.data["results"]), 12)
        self.assertIsNotNone(res1.data["next"])
        self.assertIsNone(res1.data["previous"])

        # Bài mới nhất (25) đứng trước bài 24
        self.assertEqual(res1.data["results"][0]["slug"], "bai-viet-25")
        self.assertEqual(res1.data["results"][1]["slug"], "bai-viet-24")

        # Đảm bảo không có bài nháp và trang tĩnh trong kết quả
        all_slugs_p1 = [r["slug"] for r in res1.data["results"]]
        self.assertFalse(any(s.startswith("bai-nhap-") for s in all_slugs_p1))
        self.assertFalse(any(s.startswith("trang-tinh-") for s in all_slugs_p1))

        # Gọi GET trang 2
        res2 = self.client.get("/api/public/content/entries/?page=2")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res2.data["results"]), 12)
        self.assertIsNotNone(res2.data["next"])
        self.assertIsNotNone(res2.data["previous"])

        # Gọi GET trang 3
        res3 = self.client.get("/api/public/content/entries/?page=3")
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res3.data["results"]), 1)
        self.assertIsNone(res3.data["next"])
        self.assertIsNotNone(res3.data["previous"])

    def test_cms_14_ac2_filter_by_category_slug(self):
        """CMS-14-AC2: Lọc theo chuyên mục ?category=cong-thuc; chuyên mục rỗng trả danh sách rỗng."""
        now = timezone.now()
        # Tạo 2 bài thuộc cat_cong_thuc, 1 bài thuộc cat_meo_bep
        for slug, cat in [
            ("bai-ct-1", self.cat_cong_thuc),
            ("bai-ct-2", self.cat_cong_thuc),
            ("bai-mb-1", self.cat_meo_bep),
        ]:
            e = Entry.objects.create(
                kind="post",
                title=slug,
                slug=slug,
                category=cat,
                status="published",
                first_published_at=now,
                created_by=self.manager,
            )
            v = EntryVersion.objects.create(
                entry=e,
                version=1,
                title=e.title,
                slug=e.slug,
                category=cat,
                body={"type": "doc", "blocks": []},
                description="",
                published_at=now,
                published_by=self.manager,
            )
            e.published_version = v
            e.save()

        # Lọc cat_cong_thuc -> 2 bài
        res = self.client.get("/api/public/content/entries/?category=cong-thuc")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)
        self.assertEqual({r["slug"] for r in res.data["results"]}, {"bai-ct-1", "bai-ct-2"})

        # Lọc chuyên mục trống -> 0 bài
        res_empty = self.client.get("/api/public/content/entries/?category=trong")
        self.assertEqual(res_empty.status_code, status.HTTP_200_OK)
        self.assertEqual(res_empty.data["count"], 0)
        self.assertEqual(res_empty.data["results"], [])

    def test_cms_14_ac5_public_list_and_categories_no_forbidden_keys(self):
        """CMS-14-AC5: Quét đệ quy JSON danh sách và categories: không có body, không có khoá cấm."""
        now = timezone.now()
        e = Entry.objects.create(
            kind="post",
            title="Bài kiểm tra bảo mật",
            slug="bai-kt-bm",
            category=self.cat_cong_thuc,
            status="published",
            first_published_at=now,
            created_by=self.manager,
        )
        v = EntryVersion.objects.create(
            entry=e,
            version=1,
            title=e.title,
            slug=e.slug,
            category=self.cat_cong_thuc,
            body={"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "nội dung"}]}]},
            description="mô tả",
            published_at=now,
            published_by=self.manager,
        )
        e.published_version = v
        e.save()

        # Quét danh sách bài
        res_list = self.client.get("/api/public/content/entries/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(_has_forbidden_key(res_list.data), set())
        for r in res_list.data["results"]:
            self.assertNotIn("body", r)

        # Quét categories
        res_cat = self.client.get("/api/public/content/categories/")
        self.assertEqual(res_cat.status_code, status.HTTP_200_OK)
        self.assertEqual(_has_forbidden_key(res_cat.data), set())
        # Chỉ có cat_cong_thuc có bài đã đăng, cat_meo_bep và cat_empty không có bài đã đăng nên không xuất hiện
        cat_slugs = [c["slug"] for c in res_cat.data]
        self.assertIn("cong-thuc", cat_slugs)
        self.assertNotIn("trong", cat_slugs)

    def test_cms_14_ac6_page_beyond_bounds_returns_404(self):
        """CMS-14-AC6: page=999 trả về 404 (không 500)."""
        res = self.client.get("/api/public/content/entries/?page=999")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
