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
