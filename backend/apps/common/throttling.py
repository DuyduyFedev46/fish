"""
Lớp throttle cho các endpoint công khai (S03 / L-5, doc/features/2026-09-28-sua-loi-bao-mat).

Nguyên tắc:
- Mức đọc động từ settings.CAVEVE_THROTTLE_RATES mỗi request (hỗ trợ override_settings trong test).
- Scope tắt khi mức là None / rỗng.
- Khoá cache không chứa PII: login_user dùng băm sha256(username.lower()).
- Shop lookup order dùng mã đơn viết hoa để chặn dò mã từ nhiều IP khác nhau.
"""
import hashlib
from functools import wraps

from django.conf import settings
from django.http import HttpResponse
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


class ShopVoucherCheckThrottle(SettingsRateThrottle):
    """Kiểm mã giảm giá công khai: 20/phút/IP, chặn dò mã (BR-DM-24, 02b §3.11)."""

    scope = "shop_voucher_check"


class ShopOrderCreateThrottle(SettingsRateThrottle):
    scope = "shop_order_create"


class ShopCheckoutThrottle(SettingsRateThrottle):
    scope = "shop_checkout"


class LoginIpThrottle(SettingsRateThrottle):
    scope = "login_ip"


def _login_username(request) -> str:
    """Username đã chuẩn hoá từ DRF Request (`.data`) hoặc Django HttpRequest (`.POST`, form Admin).
    Không phải chuỗi (số, object, list, null) -> "" (B4): view trả 400, throttle không được nổ."""
    try:
        data = request.data if hasattr(request, "data") else request.POST
    except Exception:  # ParseError: để view báo lỗi
        return ""
    raw = data.get("username") if hasattr(data, "get") else None
    return raw.strip().lower() if isinstance(raw, str) else ""


class LoginUserThrottle(SettingsRateThrottle):
    """B6/L-3: giới hạn theo CẶP (username, IP). Người ngoài gõ sai từ IP khác không khoá được người thật;
    chống dò từ nhiều IP đã có `LoginIpThrottle` (theo IP)."""

    scope = "login_user"

    def get_cache_key(self, request, view):
        username = _login_username(request)
        if not username:
            return None
        ident = hashlib.sha256(f"{username}|{self.get_ident(request)}".encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class ChangePasswordThrottle(SettingsRateThrottle):
    """B8: chặn dò `old_password` ở đổi mật khẩu, đếm theo người dùng đang đăng nhập."""

    scope = "change_password"

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


def throttle_admin_login(login_view):
    """H-1: bọc view đăng nhập Django Admin bằng cùng hai throttle với `/api/auth/token/`.
    Chỉ đếm POST (lần gõ mật khẩu); vượt mức -> 429, kể cả khi mật khẩu đúng."""

    @wraps(login_view)
    def wrapper(request, *args, **kwargs):
        if request.method == "POST":
            for throttle_class in (LoginIpThrottle, LoginUserThrottle):
                if not throttle_class().allow_request(request, None):
                    return HttpResponse(
                        "Thử đăng nhập quá nhiều lần. Vui lòng đợi rồi thử lại.",
                        status=429, content_type="text/plain; charset=utf-8",
                    )
        return login_view(request, *args, **kwargs)

    return wrapper


class CustomerSearchThrottle(SettingsRateThrottle):
    scope = "customer_search"

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


class PublicContentThrottle(SettingsRateThrottle):
    scope = "public_content"


