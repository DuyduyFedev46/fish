"""
Lớp throttle cho các endpoint công khai (S03 / L-5, doc/features/2026-09-28-sua-loi-bao-mat).

Nguyên tắc:
- Mức đọc động từ settings.CAVEVE_THROTTLE_RATES mỗi request (hỗ trợ override_settings trong test).
- Scope tắt khi mức là None / rỗng.
- Khoá cache không chứa PII: login_user dùng băm sha256(username.lower()).
- Shop lookup order dùng mã đơn viết hoa để chặn dò mã từ nhiều IP khác nhau.
"""
import hashlib
from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class SettingsRateThrottle(SimpleRateThrottle):
    """
    Đọc mức từ settings.CAVEVE_THROTTLE_RATES MỖI request (override_settings có hiệu lực).
    Không dùng DEFAULT_THROTTLE_RATES: SimpleRateThrottle.THROTTLE_RATES bị gán lúc import.
    """

    def parse_rate(self, rate):
        if not rate or not isinstance(rate, str) or "/" not in rate:
            return (None, None)
        return super().parse_rate(rate)

    def get_rate(self):
        rates = getattr(settings, "CAVEVE_THROTTLE_RATES", {}) or {}
        val = rates.get(self.scope)
        if not val or not isinstance(val, str) or val.strip().lower() in {"off", "none", "0"}:
            return None
        return val.strip()

    def allow_request(self, request, view):
        self.rate = self.get_rate()
        if self.rate is None:
            return True
        self.num_requests, self.duration = self.parse_rate(self.rate)
        if self.num_requests is None:
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class ShopLookupIpThrottle(SettingsRateThrottle):
    scope = "shop_lookup_ip"


def body_dict(request) -> dict:
    """Thân JSON của request dưới dạng dict; lỗi parse hoặc kiểu lạ -> {} (view sẽ trả 400 sau)."""
    try:
        data = request.data
    except Exception:  # ParseError: để view báo lỗi, throttle không được nổ
        return {}
    return data if hasattr(data, "get") else {}


class ShopLookupOrderThrottle(SettingsRateThrottle):
    """Tra đơn bằng SĐT: giới hạn theo mã đơn IN HOA đọc từ BODY (02b §3.11), chặn dò SĐT từ nhiều IP."""

    scope = "shop_lookup_order"

    def get_cache_key(self, request, view):
        order_code = body_dict(request).get("order_code") or view.kwargs.get("order_code") or ""
        ident = str(order_code).strip().upper()
        if not ident:
            return None
        # Chuỗi tuỳ ý từ body -> băm để khoá cache an toàn và có độ dài cố định.
        ident = hashlib.sha256(ident.encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class ShopLookupTokenThrottle(SettingsRateThrottle):
    """Tra đơn bằng mã tra đơn: 60/phút/IP, tách khỏi hạn 10/giờ theo mã đơn (02b §3.11)."""

    scope = "shop_lookup_token"


class ShopOrderCreateThrottle(SettingsRateThrottle):
    scope = "shop_order_create"


class ShopCheckoutThrottle(SettingsRateThrottle):
    scope = "shop_checkout"


class LoginIpThrottle(SettingsRateThrottle):
    scope = "login_ip"


class LoginUserThrottle(SettingsRateThrottle):
    scope = "login_user"

    def get_cache_key(self, request, view):
        try:
            data = request.data if hasattr(request, "data") and hasattr(request.data, "get") else {}
        except Exception:
            data = {}
        username = (data.get("username") or "").strip().lower()
        if not username:
            return None
        ident = hashlib.sha256(username.encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class CustomerSearchThrottle(SettingsRateThrottle):
    scope = "customer_search"

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


class PublicContentThrottle(SettingsRateThrottle):
    scope = "public_content"


