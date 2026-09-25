"""
Cấu hình Django — Cá Về (Level 4, Phase 1).

Nguyên tắc (theo decisions.md / URD.md):
- Django làm 100% lõi. FastAPI chỉ là adapter mỏng cho bên thứ 3 (Phase 4).
- PostgreSQL là DB sản phẩm; cho phép fallback SQLite khi dev chưa cài Postgres.
- Ngưỡng nghiệp vụ (TTL, cận hạn, chuỗi lạnh...) là tham số cấu hình, không hard-code.
"""
import sys
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


# `manage.py test` (dùng thêm ở dưới cho PASSWORD_HASHERS).
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# R2 (code review trước deploy 1): an toàn mặc định. DEBUG TẮT khi không khai báo — dev local
# bật bằng `.env` (DJANGO_DEBUG=1, xem .env.example). DEBUG tắt mà SECRET_KEY thiếu hoặc còn là
# key dev / placeholder → dừng ngay khi khởi động thay vì chạy production với key đoán được.
DEV_SECRET_KEY = "dev-insecure-key-đổi-khi-lên-prod"
_INSECURE_SECRET_KEYS = {DEV_SECRET_KEY, "đổi-thành-chuỗi-ngẫu-nhiên-dài"}
DEBUG = _bool("DJANGO_DEBUG", "0")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "").strip()
if not SECRET_KEY or SECRET_KEY in _INSECURE_SECRET_KEYS:
    if not DEBUG and not TESTING:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY thiếu hoặc đang là key dev/placeholder trong khi DJANGO_DEBUG tắt. "
            "Đặt DJANGO_SECRET_KEY bí mật (production) hoặc DJANGO_DEBUG=1 trong .env (dev)."
        )
    SECRET_KEY = DEV_SECRET_KEY
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    # Apps nghiệp vụ (tách theo domain — mỗi app model/admin/API/migration riêng)
    "apps.accounts",
    "apps.catalog",
    "apps.purchasing",
    "apps.inventory",
    "apps.sales",
    "apps.delivery",
    "apps.reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Phục vụ file tĩnh (Django Admin) ngay trong container Cloud Run.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # CORS phải đứng trước CommonMiddleware để gắn header cho mọi response.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # BR-PQ-19 (B3): người còn phải đổi mật khẩu không dùng được Django Admin.
    "apps.accounts.auth.middleware.AdminMustChangePasswordMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Cơ sở dữ liệu ---------------------------------------------------------
# Có DATABASE_URL -> PostgreSQL (sản phẩm). Không có -> SQLite (dev cục bộ).
_db_url = os.getenv("DATABASE_URL", "").strip()
if _db_url:
    DATABASES = {"default": dj_database_url.parse(_db_url, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# CHỈ khi chạy `manage.py test`: băm mật khẩu bằng MD5 cho nhanh. Mặc định PBKDF2 mất
# ~0,26 s/lần băm và fixture test tạo user liên tục (suite 142 test mất ~40 s, gần hết
# là băm mật khẩu). Production (gunicorn) không đi qua nhánh này → vẫn PBKDF2.
if TESTING:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# Cloud Run: collectstatic gom vào đây, WhiteNoise phục vụ (nén + hash).
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Bảo mật/triển khai production (kích hoạt khi DEBUG=0) ------------------
# Cloud Run kết thúc TLS ở proxy và chuyển tiếp X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Origin của Shop (Firebase) được phép gọi API cross-origin. Khai báo qua env.
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
# Domain được tin cho form POST/Admin qua HTTPS (Cloud Run *.run.app).
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Token cho dashboard SPA (cross-origin), Session cho browsable API/Admin.
        # Bản bọc của DRF: thêm chặn BR-PQ-19 (phải đổi mật khẩu trước) — S48.
        "apps.accounts.auth.authentication.TokenAuthentication",
        "apps.accounts.auth.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    # Đổi BusinessError (service layer) -> HTTP 400 (apps/common/api.py).
    "EXCEPTION_HANDLER": "apps.common.api.exception_handler",
}

# --- Tham số nghiệp vụ cấu hình được (không hard-code trong logic) ---------
# Nguồn: business-process-spec.md (BR-MH-02, BR-LO-06, BR-BH-03, BR-GH-04, BR-HV-03).
BATCH_DEFAULT_SHELF_LIFE_DAYS = int(os.getenv("BATCH_DEFAULT_SHELF_LIFE_DAYS", "90"))
BATCH_NEAR_EXPIRY_DAYS = int(os.getenv("BATCH_NEAR_EXPIRY_DAYS", "14"))
SALES_ORDER_TTL_MINUTES = int(os.getenv("SALES_ORDER_TTL_MINUTES", "30"))
DELIVERY_MAX_FAILED_ATTEMPTS = int(os.getenv("DELIVERY_MAX_FAILED_ATTEMPTS", "2"))
COLD_CHAIN_MAX_HOURS = int(os.getenv("COLD_CHAIN_MAX_HOURS", "6"))

INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")

# --- Celery (job nền) ------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = _bool("CELERY_TASK_ALWAYS_EAGER", "0")  # =1 để test không cần broker
CELERY_BEAT_SCHEDULE = {
    # Huỷ đơn quá TTL — chạy mỗi phút (BR-BH-03/04). Idempotent.
    "cancel-expired-orders": {
        "task": "apps.sales.tasks.cancel_expired_orders",
        "schedule": 60.0,
    },
}
# Ngưỡng cảnh báo job TTL "chết": còn đơn BOOKED quá hạn lâu hơn số phút này = báo động.
TTL_JOB_HEALTH_GRACE_MINUTES = int(os.getenv("TTL_JOB_HEALTH_GRACE_MINUTES", "5"))
