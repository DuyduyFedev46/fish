"""
Bộ chuẩn hoá và chống XSS thân bài theo danh sách trắng (§6.1 02b-tech-design).
Python thuần, idempotent, không dùng HTML parser vì hệ thống lưu JSON khối.
"""
import re
from urllib.parse import urlsplit
from django.conf import settings
from apps.common.exceptions import BusinessError


ITEM_CODE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")
ALLOWED_MARKS = {"bold", "italic"}
ALLOWED_BLOCK_TYPES = {"heading", "paragraph", "list", "quote", "image", "item_card"}
ALLOWED_SCHEMES = {"https", "http", "mailto", "tel"}


def _strip_control_chars(text: str) -> str:
    """Loại bỏ ký tự điều khiển C0 trừ '\\n'."""
    if not text:
        return ""
    return "".join(ch for ch in str(text) if ch == "\n" or ord(ch) >= 32)


def _is_valid_href(href: str) -> bool:
    """
    Kiểm tra href hợp lệ theo §6.1:
    - <= 2000 ký tự
    - Không chứa ký tự điều khiển hoặc khoảng trắng
    - (a) urlsplit().scheme in {https, http, mailto, tel}
    - (b) hoặc bắt đầu bằng '/' nhưng không '//' hay '/\\'
    """
    if not href or len(href) > 2000:
        return False
    # Chặn khoảng trắng hoặc ký tự điều khiển bất kỳ
    if any(ch.isspace() or ord(ch) < 32 for ch in href):
        return False
    # Kiểm tra đường dẫn tương đối nội bộ
    if href.startswith("/"):
        if href.startswith("//") or href.startswith(r"/\ "):
            return False
        if len(href) > 1 and href[1] in ("/", "\\"):
            return False
        return True
    # Kiểm tra URL có scheme
    try:
        parts = urlsplit(href)
        scheme = parts.scheme.lower()
        return scheme in ALLOWED_SCHEMES
    except Exception:
        return False


def _clean_inlines(raw_inlines: list) -> tuple[list[dict], int]:
    """Làm sạch danh sách inline node, trả về (danh_sách_sạch, tổng_ký_tự)."""
    cleaned = []
    char_count = 0
    if not isinstance(raw_inlines, list):
        return cleaned, char_count

    for item in raw_inlines:
        if not isinstance(item, dict):
            continue
        raw_text = item.get("text")
        if raw_text is None:
            continue
        text = _strip_control_chars(str(raw_text))
        if not text:
            continue

        char_count += len(text)
        node: dict = {"text": text}

        # Marks
        raw_marks = item.get("marks")
        if isinstance(raw_marks, list):
            valid_marks = []
            for m in raw_marks:
                if isinstance(m, str) and m in ALLOWED_MARKS and m not in valid_marks:
                    valid_marks.append(m)
            if valid_marks:
                node["marks"] = valid_marks

        # Href
        raw_href = item.get("href")
        if raw_href and isinstance(raw_href, str):
            href_clean = raw_href.strip()
            if _is_valid_href(href_clean):
                node["href"] = href_clean

        cleaned.append(node)

    return cleaned, char_count


def normalize_body(
    body: any,
    entry: any = None,
    *,
    strict: bool = True,
    cover_image_id: int | None = None,
) -> dict:
    """
    Chuẩn hoá thân bài dạng JSON khối (§6.1).
    - Gốc: dict {"type": "doc", "blocks": [...]}
    - Khối không cho phép -> bỏ qua
    - Khoá thừa trên khối/inline -> bỏ qua
    - Idempotent: normalize_body(normalize_body(x)) == normalize_body(x)
    """
    if not isinstance(body, dict) or body.get("type") != "doc" or not isinstance(body.get("blocks"), list):
        raise BusinessError("Thân bài không hợp lệ (BR-ND-06).", code="BR-ND-06")

    raw_blocks = body.get("blocks", [])
    max_blocks = getattr(settings, "CONTENT_MAX_BLOCKS", 300)
    if len(raw_blocks) > max_blocks:
        raise BusinessError("Số khối vượt quá giới hạn cho phép (BR-ND-06).", code="BR-ND-06")

    max_body_chars = getattr(settings, "CONTENT_BODY_MAX_CHARS", 60000)
    max_images_per_entry = getattr(settings, "CONTENT_MAX_IMAGES_PER_ENTRY", 20)

    cleaned_blocks = []
    total_chars = 0
    image_ids = set()

    # Thu thập cover image nếu có
    if cover_image_id:
        image_ids.add(cover_image_id)
    elif entry and getattr(entry, "cover_image_id", None):
        image_ids.add(entry.cover_image_id)

    for block in raw_blocks:
        if not isinstance(block, dict):
            continue
        b_type = block.get("type")
        if b_type not in ALLOWED_BLOCK_TYPES:
            # Loại khác (html, script, iframe, embed, ...) -> bỏ khối
            continue

        if b_type == "heading":
            raw_level = block.get("level")
            level = raw_level if raw_level in (2, 3) else 2
            text = _strip_control_chars(str(block.get("text", "")))
            total_chars += len(text)
            cleaned_blocks.append({"type": "heading", "level": level, "text": text})

        elif b_type in ("paragraph", "quote"):
            inlines, count = _clean_inlines(block.get("children", []))
            total_chars += count
            cleaned_blocks.append({"type": b_type, "children": inlines})

        elif b_type == "list":
            ordered = bool(block.get("ordered", False))
            raw_items = block.get("items", [])
            if not isinstance(raw_items, list):
                raw_items = []
            cleaned_items = []
            for raw_inlines in raw_items[:100]:
                inlines, count = _clean_inlines(raw_inlines)
                total_chars += count
                cleaned_items.append(inlines)
            cleaned_blocks.append({"type": "list", "ordered": ordered, "items": cleaned_items})

        elif b_type == "image":
            image_id = block.get("image_id")
            if not isinstance(image_id, int):
                # Không có image_id hợp lệ -> bỏ khối
                continue
            alt = _strip_control_chars(str(block.get("alt", "")))[:200]
            caption = _strip_control_chars(str(block.get("caption", "")))[:300]

            if strict and entry is not None and getattr(entry, "pk", None):
                from apps.content.models.images import ContentImage

                if not ContentImage.objects.filter(pk=image_id, entry=entry).exists():
                    raise BusinessError("Ảnh không thuộc bài viết này (BR-ND-07).", code="BR-ND-07")

            image_ids.add(image_id)
            cleaned_blocks.append({"type": "image", "image_id": image_id, "alt": alt, "caption": caption})

        elif b_type == "item_card":
            item_code = str(block.get("item_code", "")).strip()
            if not ITEM_CODE_RE.match(item_code):
                # Mã không hợp lệ hoặc chứa payload XSS -> bỏ khối
                continue
            cleaned_blocks.append({"type": "item_card", "item_code": item_code})

    if total_chars > max_body_chars:
        raise BusinessError("Thân bài vượt quá giới hạn ký tự (BR-ND-06).", code="BR-ND-06")

    if len(image_ids) > max_images_per_entry:
        raise BusinessError("Vượt quá số lượng ảnh tối đa cho phép (BR-ND-07).", code="BR-ND-07")

    return {"type": "doc", "blocks": cleaned_blocks}
