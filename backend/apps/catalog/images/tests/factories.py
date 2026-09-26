"""Sinh ảnh thử BẰNG CODE lúc chạy test (quy ước 2026-09-25, BR-DM-16) — không commit tệp ảnh."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageDraw

CONTENT_TYPE_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def make_image_bytes(size=(3000, 2000), fmt="JPEG", exif=None) -> bytes:
    """Ảnh "chụp thật" giả lập: dải màu (nén thực tế, không phải noise ngẫu nhiên)."""
    width, height = size
    img = Image.new("RGB", (width, height), (30, 60, 90))
    draw = ImageDraw.Draw(img)
    step = max(1, width // 40)
    for i, x in enumerate(range(0, width, step)):
        color = ((i * 5) % 256, (i * 11) % 256, (i * 17) % 256)
        draw.rectangle([x, 0, x + step, height], fill=color)
    buf = io.BytesIO()
    save_kwargs = {"exif": exif} if exif is not None else {}
    img.save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()


def make_jpeg_with_exif_orientation(size=(3000, 2000)) -> bytes:
    exif = Image.Exif()
    exif[274] = 6  # Orientation: xoay 90° (BR-DM-10 — kiểm gỡ EXIF sau xử lý)
    return make_image_bytes(size=size, fmt="JPEG", exif=exif)


def make_uploaded_image(
    name="anh.jpg", size=(3000, 2000), fmt="JPEG", raw: bytes = None
) -> SimpleUploadedFile:
    data = raw if raw is not None else make_image_bytes(size=size, fmt=fmt)
    content_type = CONTENT_TYPE_BY_FORMAT.get(fmt, "application/octet-stream")
    return SimpleUploadedFile(name, data, content_type=content_type)


def make_uploaded_bytes(name: str, data: bytes, content_type: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, data, content_type=content_type)
