"""
Máy quét cảnh báo nội dung trước khi xuất bản (CMS-08, §9 02b-tech-design).
- Quét số giống SĐT (phone_like) và che số trong snippet.
- Quét từ khoá giá vốn (cost_keyword) không phân biệt hoa thường/dấu.
- Quét mặt hàng không khả dụng (item_unavailable) cho thẻ mặt hàng.
- Quét cụm khẳng định cấm (claim): "tươi sống", "miễn phí giao"… (02b §3.7.5, SHOP-5-03 AC3). Chỉ cảnh báo, không chặn.
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


# Số liên hệ của người bán tự được phép trong thân bài CMS (SHOP-5-01 AC5, 06-marketing F4).
SELLER_PHONE_SETTINGS = ("SHOP_HOTLINE", "SELLER_PHONE")
MIN_SELLER_PHONE_DIGITS = 8  # "1900 xxxx" (giữ chỗ) chỉ còn 4 chữ số -> bỏ qua


def get_phone_allowlist() -> set[str]:
    """Số được phép: `CONTENT_PHONE_ALLOWLIST` cộng hotline và SĐT người bán đang cấu hình."""
    raw = getattr(settings, "CONTENT_PHONE_ALLOWLIST", ()) or ()
    items = raw.split(",") if isinstance(raw, str) else raw
    allowlist = set()
    for item in items:
        cleaned = normalize_phone_digits(str(item).strip())
        if cleaned:
            allowlist.add(cleaned)
    for name in SELLER_PHONE_SETTINGS:
        digits = normalize_phone_digits(str(getattr(settings, name, "") or ""))
        if len(digits) >= MIN_SELLER_PHONE_DIGITS:
            allowlist.add(digits)
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


# Cụm khẳng định chưa có nguồn hoặc trái nghiệp vụ (06-marketing A; decisions 10–11/10; BR-BH-30; S-18).
# Hàng là cấp đông, nguồn theo mùa, chưa có phí ship và chưa hứa giờ giao. Đổi danh sách bằng setting
# `CONTENT_BLOCKED_CLAIMS` (tuple hoặc chuỗi phân tách bằng dấu phẩy). Lệnh nạp `load_shop_content` dùng chung danh sách này.
DEFAULT_BLOCKED_CLAIMS = (
    "tươi sống",
    "đánh bắt sáng nay",
    "về cảng mỗi ngày",
    "luôn có hàng",
    "miễn phí giao",
    "phí giao",
    "giao trong ngày",
    "Cân đúng",
    "hút chân không",
    "cấp đông ngay tại cảng",
)
MAX_CLAIM_WARNINGS_PER_FIELD = 5


def _nfc_lower(text: str) -> str:
    """Chữ thường dạng NFC, GIỮ dấu: "cần dùng" khác "Cân đúng"."""
    return unicodedata.normalize("NFC", str(text or "")).lower()


def get_blocked_claims() -> list[str]:
    """Danh sách cụm cấm (chữ thường, NFC). Setting `CONTENT_BLOCKED_CLAIMS` thay cho danh sách mặc định."""
    raw = getattr(settings, "CONTENT_BLOCKED_CLAIMS", DEFAULT_BLOCKED_CLAIMS)
    items = raw.split(",") if isinstance(raw, str) else raw
    claims: list[str] = []
    for item in items or ():
        cleaned = _nfc_lower(str(item).strip())
        if cleaned and cleaned not in claims:
            claims.append(cleaned)
    return claims


def find_blocked_claims(text: str, claims: list[str]) -> list[tuple[str, int, int]]:
    """Các chỗ khớp (cụm, vị trí đầu, vị trí cuối) trên chữ NFC. Cụm dài xét trước; chỗ đã khớp không khớp lần nữa."""
    lowered = _nfc_lower(text)
    taken: list[tuple[int, int]] = []
    found: list[tuple[str, int, int]] = []
    for claim in sorted(claims, key=len, reverse=True):
        start = lowered.find(claim)
        while start != -1:
            end = start + len(claim)
            if not any(start < t_end and t_start < end for t_start, t_end in taken):
                taken.append((start, end))
                found.append((claim, start, end))
            start = lowered.find(claim, end)
    return sorted(found, key=lambda m: m[1])


def _extract_snippet(text: str, start: int, end: int, window: int = 30) -> str:
    """Trích xuất cửa sổ văn bản xung quanh vị trí xuất hiện (<= 90 ký tự)."""
    snippet_start = max(0, start - window)
    snippet_end = min(len(text), end + window)
    prefix = "…" if snippet_start > 0 else ""
    suffix = "…" if snippet_end < len(text) else ""
    snippet = prefix + text[snippet_start:snippet_end].strip() + suffix
    return snippet[:90]


def _scan_text_for_warnings(
    text: str, field_name: str, allowlist: set[str], cost_keywords: list[str], claims: list[str] | None = None
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

    # 3. Cụm khẳng định cấm (cảnh báo, không chặn). Snippet lấy trên chữ NFC và che SĐT.
    if claims:
        nfc_text = unicodedata.normalize("NFC", text)
        for claim, start, end in find_blocked_claims(nfc_text, claims)[:MAX_CLAIM_WARNINGS_PER_FIELD]:
            raw_snippet = _extract_snippet(nfc_text, start, end)
            warnings.append({
                "type": "claim",
                "field": field_name,
                "claim": claim,
                "snippet": _mask_phone_in_text(raw_snippet, allowlist),
            })

    return warnings


def scan_entry_warnings(entry: Any) -> list[dict[str, Any]]:
    """
    Quét toàn bộ nội dung của entry tìm các nguy cơ bảo mật trước khi publish.
    Trả về danh sách các cảnh báo (CMS-08).
    """
    allowlist = get_phone_allowlist()
    cost_keywords = _get_cost_keywords()
    claims = get_blocked_claims()
    warnings: list[dict[str, Any]] = []

    # 1. Quét các trường văn bản cấp entry
    for field_name in ("title", "excerpt", "seo_title", "seo_description"):
        val = getattr(entry, field_name, "") or ""
        warnings.extend(_scan_text_for_warnings(val, field_name, allowlist, cost_keywords, claims))

    # 2. Quét alt của ảnh bìa
    if entry.cover_image and entry.cover_image.alt:
        warnings.extend(_scan_text_for_warnings(entry.cover_image.alt, "image_alt", allowlist, cost_keywords, claims))

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
            warnings.extend(_scan_text_for_warnings(text, "body", allowlist, cost_keywords, claims))

        elif btype in ("paragraph", "quote"):
            children = block.get("children", [])
            for child in children:
                if isinstance(child, dict) and child.get("text"):
                    warnings.extend(_scan_text_for_warnings(str(child["text"]), "body", allowlist, cost_keywords, claims))

        elif btype == "list":
            items = block.get("items", [])
            for item in items:
                if isinstance(item, list):
                    for child in item:
                        if isinstance(child, dict) and child.get("text"):
                            warnings.extend(_scan_text_for_warnings(str(child["text"]), "body", allowlist, cost_keywords, claims))

        elif btype == "image":
            if block.get("alt"):
                warnings.extend(_scan_text_for_warnings(str(block["alt"]), "image_alt", allowlist, cost_keywords, claims))
            if block.get("caption"):
                warnings.extend(_scan_text_for_warnings(str(block["caption"]), "image_caption", allowlist, cost_keywords, claims))

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
