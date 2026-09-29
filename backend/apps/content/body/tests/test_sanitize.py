"""
Kiểm thử chuẩn hoá thân bài và phòng chống XSS (CMS-03-AC5, BR-ND-06).
"""
from django.test import TestCase
from apps.common.exceptions import BusinessError
from apps.content.body.sanitize import normalize_body
from apps.content.body.tests.xss_payloads import XSS_PAYLOADS
from apps.content.models.entries import Entry
from apps.content.models.images import ContentImage
from django.contrib.auth import get_user_model

User = get_user_model()



class SanitizeBodyTests(TestCase):
    def setUp(self):
        from apps.catalog.models import Item, ItemGroup
        self.user = User.objects.create_user(username="test_author", password="password")
        self.entry = Entry.objects.create(
            title="Bài kiểm tra",
            slug="bai-kiem-tra",
            created_by=self.user,
        )
        grp, _ = ItemGroup.objects.get_or_create(name="Hải sản")
        self.item = Item.objects.create(code="CA-THU-1KG", name="Cá thu 1kg", item_group=grp)

    def test_cms_03_ac5_invalid_doc_root(self):
        """Root không phải dict {'type':'doc', 'blocks':[...]} -> 400 BR-ND-06."""
        with self.assertRaises(BusinessError) as ctx:
            normalize_body("not a dict")
        self.assertEqual(ctx.exception.code, "BR-ND-06")

        with self.assertRaises(BusinessError) as ctx:
            normalize_body({"type": "invalid", "blocks": []})
        self.assertEqual(ctx.exception.code, "BR-ND-06")

    def test_cms_03_ac5_xss_payloads(self):
        """
        Kiểm tra 15 payload XSS theo §6.3:
        - Các khối lạ (html, script, iframe, embed) bị loại bỏ.
        - href nguy hiểm (javascript, vbscript, data, //evil) bị bỏ href, giữ text.
        - text có ký tự < giữ nguyên dạng chữ.
        - mark lạ bị bỏ.
        - thuộc tính thừa bị bỏ, level heading sai được ép về 2.
        - image_id của bài khác raise BR-ND-07.
        - item_code không hợp lệ bị bỏ.
        """
        # Test payload 1..13 và 15 khi ghép thành doc
        blocks = [p for p in XSS_PAYLOADS if p.get("type") != "image"]
        raw_doc = {"type": "doc", "blocks": blocks}

        clean = normalize_body(raw_doc, entry=self.entry)

        # 1. Các khối html, script, iframe, embed không còn trong clean['blocks']
        block_types = [b["type"] for b in clean["blocks"]]
        self.assertNotIn("html", block_types)
        self.assertNotIn("script", block_types)
        self.assertNotIn("iframe", block_types)
        self.assertNotIn("embed", block_types)

        # 2. Kiểm tra text và href
        for b in clean["blocks"]:
            if b["type"] in ("paragraph", "quote"):
                for inline in b["children"]:
                    # Không còn href bắt đầu bằng javascript, vbscript, data, //, /\
                    if "href" in inline:
                        href = inline["href"].lower()
                        self.assertFalse(href.startswith("javascript"))
                        self.assertFalse(href.startswith("vbscript"))
                        self.assertFalse(href.startswith("data:"))
                        self.assertFalse(href.startswith("//"))
                        self.assertFalse(href.startswith(r"/\ "))

            if b["type"] == "heading":
                # level=1 bị sửa thành 2
                self.assertEqual(b["level"], 2)
                # style và onclick bị bỏ
                self.assertNotIn("style", b)
                self.assertNotIn("onclick", b)
                # Ký tự < trong text giữ nguyên
                self.assertEqual(b["text"], "<svg onload=alert(1)>")

        # 3. Payload 11: chữ <img src=x onerror=alert(1)> giữ nguyên
        text_nodes = [
            inline["text"]
            for b in clean["blocks"]
            if b["type"] == "paragraph"
            for inline in b["children"]
        ]
        self.assertIn("<img src=x onerror=alert(1)>", text_nodes)

        # 4. Payload 12: mark 'script', 'onclick' bị loại bỏ, chỉ còn 'bold'
        p12 = next(
            b for b in clean["blocks"]
            if b["type"] == "paragraph" and any(i.get("text") == "a" for i in b["children"])
        )
        self.assertEqual(p12["children"][0].get("marks"), ["bold"])

        # 5. Payload 14: image của bài khác -> raise BR-ND-07
        payload_14 = {"type": "doc", "blocks": [XSS_PAYLOADS[13]]}
        with self.assertRaises(BusinessError) as ctx:
            normalize_body(payload_14, entry=self.entry, strict=True)
        self.assertEqual(ctx.exception.code, "BR-ND-07")

        # Payload 14 nếu đúng bài của mình -> 200
        img = ContentImage.objects.create(
            entry=self.entry,
            alt="Ảnh đúng",
            uploaded_by=self.user,
        )
        valid_img_doc = {
            "type": "doc",
            "blocks": [{"type": "image", "image_id": img.pk, "alt": "Ảnh", "caption": "Mô tả"}],
        }
        res = normalize_body(valid_img_doc, entry=self.entry, strict=True)
        self.assertEqual(len(res["blocks"]), 1)
        self.assertEqual(res["blocks"][0]["image_id"], img.pk)

    def test_cms_03_ac5_idempotent(self):
        """Idempotent: normalize(normalize(x)) == normalize(x)."""
        raw_doc = {
            "type": "doc",
            "blocks": [
                {"type": "heading", "level": 3, "text": "Tiêu đề <h3 & special>"},
                {
                    "type": "paragraph",
                    "children": [
                        {"text": "Đoạn văn có link ", "marks": ["bold"]},
                        {"text": "Cá Về", "marks": ["bold", "italic"], "href": "https://caveve.vn/shop"},
                        {"text": " và link nội bộ ", "marks": ["italic"]},
                        {"text": "trang chủ", "href": "/shop"},
                    ],
                },
                {"type": "quote", "children": [{"text": "Trích dẫn cá tươi <ngon>"}]},
                {
                    "type": "list",
                    "ordered": True,
                    "items": [
                        [{"text": "Mục 1", "marks": ["bold"]}],
                        [{"text": "Mục 2", "href": "/bai-viet"}],
                    ],
                },
                {"type": "item_card", "item_code": "CA-THU-1KG"},
            ],
        }
        first_pass = normalize_body(raw_doc, entry=self.entry)
        second_pass = normalize_body(first_pass, entry=self.entry)
        self.assertEqual(first_pass, second_pass)

    def test_max_blocks_limit(self):
        """Vượt quá CONTENT_MAX_BLOCKS -> raise BR-ND-06."""
        blocks = [{"type": "paragraph", "children": [{"text": "x"}]} for _ in range(301)]
        with self.assertRaises(BusinessError) as ctx:
            normalize_body({"type": "doc", "blocks": blocks}, entry=self.entry)
        self.assertEqual(ctx.exception.code, "BR-ND-06")

    def test_max_images_limit(self):
        """Số ảnh trong body + cover_image vượt quá 20 -> raise BR-ND-07."""
        # Tạo 21 ảnh cho bài
        imgs = [
            ContentImage.objects.create(entry=self.entry, alt=f"Ảnh {i}", uploaded_by=self.user)
            for i in range(21)
        ]
        blocks = [{"type": "image", "image_id": img.pk} for img in imgs]
        with self.assertRaises(BusinessError) as ctx:
            normalize_body({"type": "doc", "blocks": blocks}, entry=self.entry, strict=True)
        self.assertEqual(ctx.exception.code, "BR-ND-07")

    def test_cms_06_ac2_invalid_item_code_raises_br_nd_10(self):
        """Lưu body có item_card với mã không tồn tại -> 400 BR-ND-10 (CMS-06-AC2)."""
        doc = {
            "type": "doc",
            "blocks": [{"type": "item_card", "item_code": "NON-EXISTENT-ITEM"}],
        }
        with self.assertRaises(BusinessError) as ctx:
            normalize_body(doc, entry=self.entry, strict=True)
        self.assertEqual(ctx.exception.code, "BR-ND-10")

        # Với strict=False (lúc public_body), không raise mà giữ nguyên
        clean = normalize_body(doc, entry=self.entry, strict=False)
        self.assertEqual(clean["blocks"][0]["item_code"], "NON-EXISTENT-ITEM")
