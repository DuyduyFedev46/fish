"""Hàm chuẩn hoá văn bản và slug tiếng Việt (§4.1 02b-tech-design)."""
import re
import unicodedata


def fold_text(value: str) -> str:
    """Chuẩn hoá không dấu, chữ thường: 'Cá Thu  Đông!!' -> 'ca thu  dong!!'."""
    s = unicodedata.normalize("NFD", str(value or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "d").lower()


def normalize_name_key(text: str) -> str:
    """Bỏ dấu, gộp khoảng trắng: 'cong thuc NẤU' -> 'cong thuc nau' (BR-ND-01 / BR-ND-04)."""
    folded = fold_text(text)
    return " ".join(folded.split())


def slugify_vi(text: str, max_len: int = 100) -> str:
    """
    Sinh slug tiếng Việt sạch (§4.1):
    'Cá Thu  Đông!!' -> 'ca-thu-dong'.
    """
    folded = fold_text(text)
    slug = re.sub(r"[^a-z0-9]+", "-", folded)
    slug = slug.strip("-")
    if len(slug) > max_len:
        trimmed = slug[:max_len]
        last_dash = trimmed.rfind("-")
        if last_dash > 0:
            slug = trimmed[:last_dash]
        else:
            slug = trimmed
        slug = slug.strip("-")
    return slug
