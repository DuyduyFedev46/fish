"""
Xử lý tệp ảnh mặt hàng (BR-DM-10, Q5-Q10).

- Kiểm nội dung THẬT bằng Pillow (không tin đuôi file): chỉ nhận JPEG/PNG/WebP thật sự
  giải mã được. HEIC/SVG/PDF/.txt đổi đuôi -> Pillow không mở được -> từ chối. GIF (kể
  cả GIF tĩnh) bị từ chối tường minh vì `format` không nằm trong `ALLOWED_FORMATS`.
- Gỡ EXIF/GPS: xoay ảnh đúng chiều theo EXIF Orientation trước (`exif_transpose`), rồi
  chỉ giữ lại pixel (không truyền `exif=` khi lưu) — ảnh xuất ra không còn metadata gốc.
- Cắt vuông 1:1 giữa (Q6), xuất 3 cỡ WebP, KHÔNG phóng to ảnh nhỏ hơn cỡ đích.
"""
import io
from dataclasses import dataclass

from PIL import Image, ImageOps

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

# Ngân sách dung lượng theo cỡ (Q7: "mỗi ảnh lưới khoảng dưới 60 KB"). Không phải tham
# số nghiệp vụ cấu hình qua env (khác `ITEM_IMAGE_*` trong 02-stories.md) — chỉ là mức
# nén kỹ thuật để đạt yêu cầu băng thông.
SIZE_BUDGET_BYTES = {"thumb": 15 * 1024, "card": 60 * 1024}
DEFAULT_WEBP_QUALITY = 82
MIN_WEBP_QUALITY = 20


class InvalidImageError(Exception):
    """Tệp không phải ảnh raster cho phép (BR-DM-10)."""


@dataclass
class ProcessedImage:
    sizes: dict  # {"thumb": bytes, "card": bytes, "detail": bytes} (WebP)
    source_side: int  # cạnh ảnh vuông sau khi cắt, dùng để tính cảnh báo LOW_RESOLUTION


def _open_verified(raw: bytes) -> Image.Image:
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
        fmt = (probe.format or "").upper()
    except Exception as exc:  # UnidentifiedImageError, OSError, SyntaxError...
        raise InvalidImageError(
            "Tệp không phải ảnh hợp lệ hoặc đã hỏng."
        ) from exc
    if fmt not in ALLOWED_FORMATS:
        raise InvalidImageError(
            f"Định dạng {fmt or 'không xác định'} không được nhận."
        )
    # `verify()` làm hỏng object cho các thao tác tiếp theo -> mở lại từ đầu.
    image = Image.open(io.BytesIO(raw))
    image.load()
    return image


def _strip_exif_and_orient(image: Image.Image) -> Image.Image:
    oriented = ImageOps.exif_transpose(image) or image
    if oriented.mode in ("RGBA", "LA"):
        rgba = oriented.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if oriented.mode == "P":
        return oriented.convert("RGB")
    return oriented.convert("RGB")


def _crop_square_center(image: Image.Image) -> Image.Image:
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def _encode_webp(image: Image.Image, *, max_bytes=None, quality=DEFAULT_WEBP_QUALITY) -> bytes:
    q = quality
    while True:
        buf = io.BytesIO()
        image.save(buf, format="WEBP", quality=q, method=6)
        data = buf.getvalue()
        if max_bytes is None or len(data) <= max_bytes or q <= MIN_WEBP_QUALITY:
            return data
        q -= 15


def process_item_image(raw: bytes, *, sizes: dict) -> ProcessedImage:
    """`sizes`: vd {"thumb": 160, "card": 480, "detail": 1200} (từ `settings.ITEM_IMAGE_SIZES`)."""
    image = _open_verified(raw)
    clean = _strip_exif_and_orient(image)
    square = _crop_square_center(clean)
    side = square.size[0]

    outputs = {}
    for name, target in sizes.items():
        out_side = min(int(target), side)  # không phóng to (BR-DM-10, AC6)
        resized = square if out_side == side else square.resize(
            (out_side, out_side), Image.LANCZOS
        )
        outputs[name] = _encode_webp(resized, max_bytes=SIZE_BUDGET_BYTES.get(name))
    return ProcessedImage(sizes=outputs, source_side=side)
