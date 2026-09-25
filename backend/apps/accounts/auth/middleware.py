"""
BR-PQ-19 cho Django Admin (B3, QA lần 2).

Lớp xác thực DRF (authentication.py) chỉ phủ API. Admin đăng nhập bằng session, không qua DRF
→ middleware này chặn mọi trang `/admin/` khi người đăng nhập còn cờ `must_change_password`
(superuser không bị ép), trả 403 kèm hướng dẫn đặt mật khẩu mới trên ERP console. Trang đăng
nhập/đăng xuất Admin vẫn mở để người đó thoát ra được.
"""
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils.html import escape

from .authentication import must_change_password

ADMIN_MUST_CHANGE_PASSWORD_MESSAGE = (
    "Bạn cần đặt mật khẩu mới trên ERP console (cửa sổ đăng nhập nhân viên) trước khi dùng "
    "trang quản trị (BR-PQ-19)."
)


# R7 (code review): URL Admin chỉ tính MỘT lần (lazy — urlconf chưa sẵn lúc nạp middleware),
# không reverse() ở mỗi request. Đổi ROOT_URLCONF (chỉ xảy ra trong test) thì tính lại.
_admin_urls_cache = {}


def _admin_urls():
    """(prefix admin, {login, logout}, logout_url) — tính lần đầu rồi dùng lại."""
    if not _admin_urls_cache:
        logout = reverse("admin:logout")
        _admin_urls_cache["value"] = (
            reverse("admin:index"), frozenset((reverse("admin:login"), logout)), logout,
        )
    return _admin_urls_cache["value"]


@receiver(setting_changed)
def _reset_admin_urls(*, setting, **kwargs):
    if setting == "ROOT_URLCONF":
        _admin_urls_cache.clear()


class AdminMustChangePasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        admin_root, exempt, logout_url = _admin_urls()
        if request.path.startswith(admin_root):
            if request.path not in exempt and must_change_password(getattr(request, "user", None)):
                return HttpResponseForbidden(
                    "<!doctype html><meta charset='utf-8'><title>Cần đặt mật khẩu mới</title>"
                    f"<p>{escape(ADMIN_MUST_CHANGE_PASSWORD_MESSAGE)}</p>"
                    f"<form method='post' action='{logout_url}'>"
                    f"<input type='hidden' name='csrfmiddlewaretoken' value='{self._csrf(request)}'>"
                    "<button type='submit'>Đăng xuất</button></form>",
                    content_type="text/html; charset=utf-8",
                )
        return self.get_response(request)

    @staticmethod
    def _csrf(request):
        from django.middleware.csrf import get_token
        return escape(get_token(request))
