"""Tiện ích dùng chung trong app sales: làm tròn tiền, sinh mã chứng từ, giờ hiện tại."""
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from django.utils import timezone

ZERO = Decimal("0")
CENT = Decimal("0.01")


def now():
    return timezone.now()


def money(amount):
    """Làm tròn về 2 chữ số thập phân (tiền)."""
    return Decimal(amount).quantize(CENT, rounding=ROUND_HALF_UP)


def gen_code(prefix, model):
    """Sinh mã chứng từ duy nhất."""
    while True:
        code = f"{prefix}{now():%y%m%d}-{uuid4().hex[:6].upper()}"
        if not model.objects.filter(code=code).exists():
            return code


KG = Decimal("0.001")


def money_str(amount):
    """Tiền ra JSON dạng chuỗi thập phân (bất biến #7): 540000.00 → "540000", 12.50 → "12.5"."""
    if amount is None:
        return None
    d = Decimal(amount)
    if d == d.to_integral_value():
        return str(d.quantize(Decimal("1")))
    return format(d.normalize(), "f")


def kg_str(qty):
    """Số kg ra JSON dạng chuỗi 3 chữ số thập phân: 2 → "2.000"."""
    if qty is None:
        return None
    return str(Decimal(qty).quantize(KG, rounding=ROUND_HALF_UP))


def fold_text(value):
    """Chuẩn hoá để tìm không dấu, không phân biệt hoa thường: "Anh Đạt" → "anh dat"."""
    import unicodedata

    s = unicodedata.normalize("NFD", str(value or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").casefold()


def vnd_display(amount):
    """Tiền hiển thị trong câu chữ: 540000 → "540.000 ₫" (không float, bất biến #7)."""
    d = Decimal(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(d):,}".replace(",", ".") + " ₫"


def vnd_short(amount):
    """Tiền trong thông điệp lỗi theo contract: 300000 → "300.000đ" (S12/S13)."""
    return vnd_display(amount).replace(" ₫", "đ")
