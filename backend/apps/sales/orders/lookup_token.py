"""
Mã tra đơn tạm của Shop (SHOP-3-01 AC5, SHOP-3-02, BR-BH-25, 02b §3.4.1).

Ký bằng khoá máy chủ (`django.core.signing`, salt riêng), KHÔNG lưu DB. Giải base64 chỉ thấy mã đơn và mốc thời gian,
không có tên, SĐT hay địa chỉ (bất biến 9). Hạn sống đọc từ `SHOP_LOOKUP_TOKEN_DAYS`.
"""
from django.conf import settings
from django.core import signing

SALT = "shop.order.lookup"


class TokenExpired(Exception):
    """Mã hợp lệ nhưng quá hạn -> 401 TOKEN_EXPIRED."""


class TokenInvalid(Exception):
    """Mã hỏng, bị sửa, hoặc của đơn khác -> cùng 404 với mọi ca sai (không lộ ô nào sai)."""


def make_token(order_code: str) -> str:
    return signing.dumps({"o": order_code}, salt=SALT, compress=False)


def read_token(token: str, order_code: str) -> None:
    """Không trả gì khi hợp lệ; raise `TokenExpired` hoặc `TokenInvalid`."""
    max_age = int(settings.SHOP_LOOKUP_TOKEN_DAYS) * 86400
    try:
        payload = signing.loads(token, salt=SALT, max_age=max_age)
    except signing.SignatureExpired:
        raise TokenExpired() from None
    except signing.BadSignature:
        raise TokenInvalid() from None
    if not isinstance(payload, dict) or payload.get("o") != order_code:
        raise TokenInvalid()
