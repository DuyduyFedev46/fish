"""
Đợt sửa bảo mật gấp 15/11: cấu hình production (không DEBUG).

Mã: H-1 (api-auth, Admin, session, renderer), M-1/B5 (cache dùng chung), M-4/B11 (token nội bộ),
L-2 (HSTS, chuyển hướng HTTPS). Chạy settings trong tiến trình con với môi trường kiểm soát được.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from django.core.cache import caches
from django.core.cache.backends.db import DatabaseCache
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings

from apps.common.startup_checks import validate_internal_service_token

BACKEND = Path(__file__).resolve().parents[3]
STRONG_KEY = "k" * 50
STRONG_TOKEN = "t" * 40

PROBE = """
import dotenv; dotenv.load_dotenv = lambda *a, **k: None
import json, os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
import django; django.setup()
from django.conf import settings
from django.urls import Resolver404, resolve
def ok(path):
    try:
        resolve(path); return True
    except Resolver404:
        return False
print("PROBE=" + json.dumps({
    "api_auth": ok("/api-auth/login/"),
    "admin": ok("/admin/login/"),
    "auth_classes": settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"],
    "renderers": settings.REST_FRAMEWORK.get("DEFAULT_RENDERER_CLASSES"),
    "cache": settings.CACHES["default"]["BACKEND"],
    "hsts": settings.SECURE_HSTS_SECONDS,
    "hsts_sub": settings.SECURE_HSTS_INCLUDE_SUBDOMAINS,
    "ssl_redirect": settings.SECURE_SSL_REDIRECT,
    "proxy_header": settings.SECURE_PROXY_SSL_HEADER,
    "token_ttl": settings.AUTH_TOKEN_TTL_HOURS,
}))
"""


def run_probe(env):
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "SECURE_", "AUTH_", "INTERNAL_"))}
    clean.update({"DJANGO_SECRET_KEY": STRONG_KEY, "INTERNAL_SERVICE_TOKEN": STRONG_TOKEN, **env})
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=BACKEND, env=clean,
                         capture_output=True, text=True, timeout=90)
    line = next((x for x in out.stdout.splitlines() if x.startswith("PROBE=")), None)
    assert line, out.stdout + out.stderr
    return json.loads(line[len("PROBE="):])


class ProductionUrlsAndAuthTests(SimpleTestCase):
    """H-1: production không có /api-auth/, không session/Browsable API cho DRF; Admin tắt được bằng env."""

    def test_production_has_no_api_auth_login_form(self):
        self.assertFalse(run_probe({"DJANGO_DEBUG": "0"})["api_auth"])

    def test_debug_keeps_api_auth_login_form(self):
        self.assertTrue(run_probe({"DJANGO_DEBUG": "1"})["api_auth"])

    def test_production_drf_uses_token_only_and_json_only(self):
        probe = run_probe({"DJANGO_DEBUG": "0"})
        self.assertEqual(probe["auth_classes"], ["apps.accounts.auth.authentication.TokenAuthentication"])
        self.assertEqual(probe["renderers"], ["rest_framework.renderers.JSONRenderer"])

    def test_debug_keeps_session_auth_and_browsable_api(self):
        probe = run_probe({"DJANGO_DEBUG": "1"})
        self.assertIn("apps.accounts.auth.authentication.SessionAuthentication", probe["auth_classes"])
        self.assertIn("rest_framework.renderers.BrowsableAPIRenderer", probe["renderers"])

    def test_admin_on_by_default_because_ops_uses_it(self):
        self.assertTrue(run_probe({"DJANGO_DEBUG": "0"})["admin"])

    def test_admin_can_be_switched_off_by_env(self):
        self.assertFalse(run_probe({"DJANGO_DEBUG": "0", "DJANGO_ADMIN_ENABLED": "0"})["admin"])


class ProductionTransportTests(SimpleTestCase):
    """L-2: HSTS + chuyển hướng HTTPS khi không DEBUG; TTL token mặc định 12 giờ."""

    def test_production_transport_security(self):
        probe = run_probe({"DJANGO_DEBUG": "0"})
        self.assertEqual(probe["hsts"], 31536000)
        self.assertFalse(probe["hsts_sub"])
        self.assertTrue(probe["ssl_redirect"])
        self.assertEqual(probe["proxy_header"], ["HTTP_X_FORWARDED_PROTO", "https"])

    def test_debug_has_no_https_redirect(self):
        probe = run_probe({"DJANGO_DEBUG": "1"})
        self.assertFalse(probe["ssl_redirect"])
        self.assertEqual(probe["hsts"], 0)

    def test_token_ttl_default_and_env(self):
        self.assertEqual(run_probe({"DJANGO_DEBUG": "0"})["token_ttl"], 12)
        self.assertEqual(run_probe({"DJANGO_DEBUG": "0", "AUTH_TOKEN_TTL_HOURS": "5"})["token_ttl"], 5)


class SharedCacheConfigTests(SimpleTestCase):
    """M-1/B5: production dùng cache dùng chung giữa worker và instance, không phải LocMem."""

    def test_production_cache_is_database_cache(self):
        probe = run_probe({"DJANGO_DEBUG": "0"})
        self.assertEqual(probe["cache"], "django.core.cache.backends.db.DatabaseCache")


class SharedCacheBehaviourTests(TestCase):
    """Bảng cache do migration tạo; hai handle cache khác nhau đếm chung (như hai instance)."""

    CACHES = {"default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "OPTIONS": {"MAX_ENTRIES": 100000},
    }}

    def test_cache_table_exists_after_migrate_and_is_shared(self):
        with override_settings(CACHES=self.CACHES):
            first = caches["default"]
            self.assertIsInstance(first, DatabaseCache)
            first.set("probe-key", 7, 60)
            second = DatabaseCache("django_cache", {"OPTIONS": {"MAX_ENTRIES": 100000}})
            self.assertEqual(second.get("probe-key"), 7)

    @override_settings(CACHES=CACHES, CAVEVE_THROTTLE_RATES={"login_ip": "2/min", "login_user": "100/hour"})
    def test_throttle_counts_in_shared_cache(self):
        from rest_framework.test import APIClient
        caches["default"].clear()
        codes = [APIClient().post("/api/auth/token/", {"username": "a", "password": "b"}, format="json",
                                  REMOTE_ADDR="10.7.7.7").status_code for _ in range(3)]
        self.assertEqual(codes[2], 429)
        other = DatabaseCache("django_cache", {"OPTIONS": {"MAX_ENTRIES": 100000}})
        self.assertTrue(any(other.get(k) for k in ("throttle_login_ip_10.7.7.7",)))


class InternalServiceTokenTests(SimpleTestCase):
    """M-4/B11: production không khởi động với token nội bộ rỗng, ngắn hoặc là chuỗi mẫu."""

    def test_rejects_empty_short_and_placeholder(self):
        for bad in ("", "   ", "short-token", "đổi-thành-token-nội-bộ", "doi-gia-tri-nay-thanh-secret-that"):
            with self.subTest(token=bad), self.assertRaises(ImproperlyConfigured):
                validate_internal_service_token(bad)

    def test_accepts_strong_token(self):
        validate_internal_service_token(STRONG_TOKEN)

    def test_wsgi_refuses_to_start_in_production_with_weak_token(self):
        for token in ("", "yeu"):
            with self.subTest(token=token):
                env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "INTERNAL_"))}
                env.update({"DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": STRONG_KEY, "INTERNAL_SERVICE_TOKEN": token})
                code = ("import dotenv; dotenv.load_dotenv = lambda *a, **k: None\n"
                        "from django.core.exceptions import ImproperlyConfigured\n"
                        "try:\n    import config.wsgi\n    print('STARTED')\n"
                        "except ImproperlyConfigured as e:\n    print('IMPROPERLY:' + str(e))\n")
                out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env,
                                     capture_output=True, text=True, timeout=90)
                self.assertIn("IMPROPERLY:", out.stdout + out.stderr)
                self.assertIn("INTERNAL_SERVICE_TOKEN", out.stdout + out.stderr)

    def test_wsgi_starts_in_production_with_strong_token(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "INTERNAL_"))}
        env.update({"DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": STRONG_KEY, "INTERNAL_SERVICE_TOKEN": STRONG_TOKEN})
        code = "import dotenv; dotenv.load_dotenv = lambda *a, **k: None\nimport config.wsgi\nprint('STARTED')\n"
        out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env,
                             capture_output=True, text=True, timeout=90)
        self.assertIn("STARTED", out.stdout, out.stderr)
