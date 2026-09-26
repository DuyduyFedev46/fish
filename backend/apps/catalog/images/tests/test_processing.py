"""Xử lý ảnh (BR-DM-10, Q5-Q10) — không đụng DB, không đụng storage."""
import io

from django.test import SimpleTestCase
from PIL import Image

from apps.catalog.images import processing

from .factories import make_image_bytes, make_jpeg_with_exif_orientation

SIZES = {"thumb": 160, "card": 480, "detail": 1200}


class ProcessItemImageTests(SimpleTestCase):
    def test_a2_ac1_cat_vuong_va_xuat_3_co_webp(self):
        raw = make_image_bytes(size=(3000, 2000), fmt="JPEG")
        result = processing.process_item_image(raw, sizes=SIZES)
        self.assertEqual(set(result.sizes), {"thumb", "card", "detail"})
        for name, target in SIZES.items():
            img = Image.open(io.BytesIO(result.sizes[name]))
            self.assertEqual(img.format, "WEBP")
            self.assertEqual(img.size, (target, target))  # vuông 1:1 (Q6)

    def test_a2_ac2_go_exif_va_gps(self):
        raw = make_jpeg_with_exif_orientation(size=(3000, 2000))
        before = Image.open(io.BytesIO(raw))
        self.assertIn(274, dict(before.getexif()))  # có EXIF trước khi xử lý
        result = processing.process_item_image(raw, sizes=SIZES)
        for data in result.sizes.values():
            after = Image.open(io.BytesIO(data))
            self.assertEqual(dict(after.getexif()), {})  # sạch EXIF/GPS

    def test_a2_ac6_khong_phong_to_anh_nho_va_bao_canh_ngan(self):
        raw = make_image_bytes(size=(400, 400), fmt="PNG")
        result = processing.process_item_image(raw, sizes=SIZES)
        self.assertEqual(result.source_side, 400)
        for name, data in result.sizes.items():
            img = Image.open(io.BytesIO(data))
            self.assertLessEqual(img.size[0], 400)
            self.assertLessEqual(img.size[1], 400)

    def test_a2_ac7_gioi_han_dung_luong_thumb_va_card(self):
        raw = make_image_bytes(size=(4000, 3000), fmt="WEBP")
        result = processing.process_item_image(raw, sizes=SIZES)
        self.assertLessEqual(len(result.sizes["card"]), 60 * 1024)
        self.assertLessEqual(len(result.sizes["thumb"]), 15 * 1024)

    def test_a2_ac9_gif_bi_tu_choi_du_pillow_mo_duoc(self):
        buf = io.BytesIO()
        Image.new("RGB", (100, 100)).save(buf, format="GIF")
        with self.assertRaises(processing.InvalidImageError):
            processing.process_item_image(buf.getvalue(), sizes=SIZES)

    def test_a2_ac9_tep_txt_doi_duoi_jpg_bi_tu_choi(self):
        fake = b"day khong phai anh, chi la text ngau nhien" * 20
        with self.assertRaises(processing.InvalidImageError):
            processing.process_item_image(fake, sizes=SIZES)

    def test_a2_ac9_svg_bi_tu_choi(self):
        svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
        with self.assertRaises(processing.InvalidImageError):
            processing.process_item_image(svg, sizes=SIZES)

    def test_a2_ac9_pdf_bi_tu_choi(self):
        pdf = b"%PDF-1.4\n%..." + b"0" * 200
        with self.assertRaises(processing.InvalidImageError):
            processing.process_item_image(pdf, sizes=SIZES)
