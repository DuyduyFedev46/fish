"""
Máy quét cảnh báo nội dung trước khi xuất bản (CMS-08, §9 02b-tech-design).
- Quét số giống SĐT (phone_like) và che số trong snippet.
- Quét từ khoá giá vốn (cost_keyword) không phân biệt hoa thường/dấu.
- Quét mặt hàng không khả dụng (item_unavailable) cho thẻ mặt hàng.
- Tuyệt đối không log số điện thoại hay dữ liệu cá nhân (Bất biến 9, CMS-08-AC7).
"""

import re
import unicodedata
from typing import Any, List, Dict
from django.conf import settings
from apps.content.body.slug import fold_text


# Regex nhận diện số điện thoại VN (10-11 chữ số bắt đầu bằng 0, +84 hoặc 84)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){9,10}(?!\d)")


def normalize_phone_digits(candidate: str) -> str:
    """Rút gọn chỉ còn chữ số, chuẩn hoá đầu 84 thành 0."""
    digits = re.sub(r"\D", "", candidate)
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    return digits


def _mask_phone_in_text(text: str, allowlist: set[str]) -> str:
    """Thay thế các số điện thoại trong chuỗi bằng chuỗi đã che (vd: 09xx xxx 678)."""
    def repl(m: re.Match) -> str:
        raw = m.group(0)
        digits = normalize_phone_digits(raw)
        if digits in allowlist:
            return raw
        if len(digits) >= 5:
            return f"{digits[:2]}xx xxx {digits[-3:]}"
        return f"{digits[:2]}xx"

    return PHONE_RE.sub(repl, text)


def get_phone_allowlist() -> set[str]:
    raw = getattr(settings, "CONTENT_PHONE_ALLOWLIST", ()) or ()
    items = raw.split(",") if isinstance(raw, str) else raw
    allowlist = set()
    for item in items:
        cleaned = normalize_phone_digits(str(item).strip())
        if cleaned:
            allowlist.add(cleaned)
    return allowlist


def _get_cost_keywords() -> list[str]:
    raw = getattr(
        settings,
        "CONTENT_COST_KEYWORDS",
        ("giá mua", "giá vốn", "giá nhập", "giá cảng", "nhà cung cấp", "tiền lãi"),
    )
    items = raw.split(",") if isinstance(raw, str) else raw
    keywords = []
    for kw in items:
        clean_kw = fold_text(str(kw).strip())
        if clean_kw:
            keywords.append(clean_kw)
    return keywords


def _extract_snippet(text: str, start: int, end: int, window: int = 30) -> str:
    """Trích xuất cửa sổ văn bản xung quanh vị trí xuất hiện (<= 90 ký tự)."""
    snippet_start = max(0, start - window)
    snippet_end = min(len(text), end + window)
    prefix = "…" if snippet_start > 0 else ""
    suffix = "…" if snippet_end < len(text) else ""
    snippet = prefix + text[snippet_start:snippet_end].strip() + suffix
    return snippet[:90]


def _scan_text_for_warnings(
    text: str, field_name: str, allowlist: set[str], cost_keywords: list[str]
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if not text or not isinstance(text, str):
        return warnings

    # 1. Quét số điện thoại
    phone_counts = 0
    for match in PHONE_RE.finditer(text):
        if phone_counts >= 5:
            break
        raw_match = match.group(0)
        digits = normalize_phone_digits(raw_match)
        if digits in allowlist:
            continue
        # Trích snippet và che số trong snippet
        raw_snippet = _extract_snippet(text, match.start(), match.end())
        masked_snippet = _mask_phone_in_text(raw_snippet, allowlist)

        warnings.append({
            "type": "phone_like",
            "field": field_name,
            "snippet": masked_snippet,
        })
        phone_counts += 1

    # 2. Quét từ khoá giá vốn
    folded_text = fold_text(text)
    cost_counts = 0
    for kw in cost_keywords:
        if cost_counts >= 5:
            break
        # Biên từ với regex
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])")
        for match in pattern.finditer(folded_text):
            if cost_counts >= 5:
                break
            raw_snippet = _extract_snippet(text, match.start(), match.end())
            # Che mọi SĐT nếu tình cờ có trong snippet
            masked_snippet = _mask_phone_in_text(raw_snippet, allowlist)
            warnings.append({
                "type": "cost_keyword",
                "field": field_name,
                "snippet": masked_snippet,
            })
            cost_counts += 1

    return warnings


def scan_entry_warnings(entry: Any) -> list[dict[str, Any]]:
    """
    Quét toàn bộ nội dung của entry tìm các nguy cơ bảo mật trước khi publish.
    Trả về danh sách các cảnh báo (CMS-08).
    """
    allowlist = get_phone_allowlist()
    cost_keywords = _get_cost_keywords()
    warnings: list[dict[str, Any]] = []

    # 1. Quét các trường văn bản cấp entry
    for field_name in ("title", "excerpt", "seo_title", "seo_description"):
        val = getattr(entry, field_name, "") or ""
        warnings.extend(_scan_text_for_warnings(val, field_name, allowlist, cost_keywords))

    # 2. Quét alt của ảnh bìa
    if entry.cover_image and entry.cover_image.alt:
        warnings.extend(_scan_text_for_warnings(entry.cover_image.alt, "image_alt", allowlist, cost_keywords))

    # 3. Quét thân bài (body blocks)
    body = entry.body if isinstance(entry.body, dict) else {}
    blocks = body.get("blocks", []) if isinstance(body.get("blocks"), list) else []

    item_codes_to_check: list[str] = []

    for block in blocks:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")

        if btype == "heading":
            text = str(block.get("text") or "")
            warnings.extend(_scan_text_for_warnings(text, "body", allowlist, cost_keywords))

        elif btype in ("paragraph", "quote"):
            children = block.get("children", [])
            for child in children:
                if isinstance(child, dict) and child.get("text"):
                    warnings.extend(_scan_text_for_warnings(str(child["text"]), "body", allowlist, cost_keywords))

        elif btype == "list":
            items = block.get("items", [])
            for item in items:
                if isinstance(item, list):
                    for child in item:
                        if isinstance(child, dict) and child.get("text"):
                            warnings.extend(_scan_text_for_warnings(str(child["text"]), "body", allowlist, cost_keywords))

        elif btype == "image":
            if block.get("alt"):
                warnings.extend(_scan_text_for_warnings(str(block["alt"]), "image_alt", allowlist, cost_keywords))
            if block.get("caption"):
                warnings.extend(_scan_text_for_warnings(str(block["caption"]), "image_caption", allowlist, cost_keywords))

        elif btype == "item_card":
            item_code = block.get("item_code")
            if item_code and isinstance(item_code, str):
                item_codes_to_check.append(item_code.strip())

    # 4. Quét item_card không khả dụng (CMS-06, CMS-08, §9 02b-tech-design)
    if item_codes_to_check:
        try:
            from apps.catalog.models import Item
            from apps.catalog.pricing.services import effective_price

            items_by_code = {
                it.code: it for it in Item.objects.filter(code__in=item_codes_to_check)
            }
            for code in item_codes_to_check:
                item_obj = items_by_code.get(code)
                if not item_obj or not item_obj.is_active or effective_price(item_obj) is None:
                    warnings.append({
                        "type": "item_unavailable",
                        "item_code": code,
                    })
        except Exception:
            pass

    return warnings
