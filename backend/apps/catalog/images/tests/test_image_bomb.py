"""B7/L-5 (rà soát bảo mật 15/11): ảnh quá nhiều điểm ảnh bị chặn TRƯỚC khi giải mã."""
import io
from unittest import mock

from django.test import SimpleTestCase, override_settings
from PIL import Image

from apps.catalog.images import processing

SIZES = {"thumb": 160, "card": 480, "detail": 1200}


def _big_png(side):
    buf = io.BytesIO()
    Image.new("1", (side, side)).save(buf, format="PNG")  # ảnh 1 bit nén rất nhỏ
    return buf.getvalue()


class ImageBombTests(SimpleTestCase):
    def test_13000_square_png_is_rejected_before_decode(self):
        raw = _big_png(13000)  # 169 triệu điểm ảnh, file vài trăm KB
        self.assertLess(len(raw), 10 * 1024 * 1024)
        with mock.patch.object(Image.Image, "load", side_effect=AssertionError("đã giải mã ảnh")):
            with self.assertRaises(processing.InvalidImageError) as ctx:
                processing.process_item_image(raw, sizes=SIZES)
        self.assertIn("quá lớn", str(ctx.exception))

    def test_keep_ratio_path_also_rejects(self):
        with self.assertRaises(processing.InvalidImageError):
            processing.process_image_keep_ratio(_big_png(13000), widths={"sm": 480})

    def test_9500_square_png_is_rejected(self):
        with self.assertRaises(processing.InvalidImageError):
            processing.process_item_image(_big_png(9500), sizes=SIZES)  # 90 triệu điểm ảnh

    def test_normal_photo_size_still_ok(self):
        buf = io.BytesIO()
        Image.new("RGB", (4000, 3000)).save(buf, format="JPEG")  # 12 triệu điểm ảnh
        result = processing.process_item_image(buf.getvalue(), sizes=SIZES)
        self.assertEqual(set(result.sizes), {"thumb", "card", "detail"})

    @override_settings(ITEM_IMAGE_MAX_PIXELS=1_000_000)
    def test_limit_is_configurable(self):
        with self.assertRaises(processing.InvalidImageError):
            processing.process_item_image(_big_png(1100), sizes=SIZES)
