"""
Slug đường dẫn (SHOP-2-01, 02b §2.1): bỏ dấu tiếng Việt, chữ thường, nối bằng dấu gạch ngang.

`slugify_vi` thuần hàm; `unique_slug` hỏi DB để tránh trùng (thêm -2, -3…).
Data migration `catalog/0006` CHÉP logic này vào file migration (không import code app) để
migration không đổi nghĩa khi code đổi.
"""
import re
import unicodedata

SLUG_MAX_LENGTH = 80
FALLBACK_SLUG = "group"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify_vi(text, max_length=SLUG_MAX_LENGTH):
    """"Đặc sản Cá Thu" -> "dac-san-ca-thu". Rỗng hoặc toàn ký hiệu -> "group"."""
    folded = unicodedata.normalize("NFD", str(text or ""))
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn")
    folded = folded.replace("đ", "d").replace("Đ", "D").lower()
    slug = _NON_ALNUM.sub("-", folded).strip("-")[:max_length].strip("-")
    return slug or FALLBACK_SLUG


def unique_slug(model, base, exclude_pk=None, field="slug", max_length=SLUG_MAX_LENGTH):
    """Trả `base` nếu chưa ai dùng, ngược lại `base-2`, `base-3`… (cắt `base` để vừa độ dài)."""
    queryset = model.objects.all()
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    taken = set(queryset.filter(**{f"{field}__startswith": base[: max_length - 8]}).values_list(field, flat=True))
    candidate = base[:max_length].strip("-") or FALLBACK_SLUG
    counter = 2
    while candidate in taken:
        suffix = f"-{counter}"
        candidate = f"{base[: max_length - len(suffix)].strip('-')}{suffix}"
        counter += 1
    return candidate
