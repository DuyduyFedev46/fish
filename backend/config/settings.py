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
    # AI Native ERP (doc/features/2026-09-27-ai-native-erp): lớp lệnh dùng chung —
    # Lô 1 chỉ registry + catalog (chưa có model); AiProposal/AiUsageLedger ở lô sau.
    "apps.ai",
    # CMS viết bài (doc/features/2026-09-28-cms-viet-bai)
    "apps.content",
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

# Chỉ dùng khi ITEM_IMAGE_STORAGE=local (dev/test) — Cloud Run KHÔNG lưu ảnh trên đĩa
# tạm này (BR-DM-16), production/staging luôn ITEM_IMAGE_STORAGE=gcs.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Ảnh mặt hàng (A1/A2/A3/A4, doc/features/2026-09-26-anh-mat-hang) -------
# `local` (mặc định, dev/test — không gọi mạng ra GCS) | `gcs` (staging/production).
ITEM_IMAGE_STORAGE = os.getenv("ITEM_IMAGE_STORAGE", "local").strip().lower()
ITEM_IMAGE_BUCKET = os.getenv("ITEM_IMAGE_BUCKET", "").strip()
# Mặc định suy ra từ bucket khi dùng GCS; local thì phục vụ qua MEDIA_URL của chính API.
ITEM_IMAGE_PUBLIC_BASE_URL = os.getenv("ITEM_IMAGE_PUBLIC_BASE_URL", "").strip() or (
    f"https://storage.googleapis.com/{ITEM_IMAGE_BUCKET}"
    if ITEM_IMAGE_STORAGE == "gcs" and ITEM_IMAGE_BUCKET
    else "http://localhost:8000/media/item-images"
)
ITEM_IMAGE_MAX_BYTES = int(os.getenv("ITEM_IMAGE_MAX_BYTES", str(10 * 1024 * 1024)))
ITEM_IMAGE_MIN_SIDE_WARN = int(os.getenv("ITEM_IMAGE_MIN_SIDE_WARN", "600"))
# 3 cỡ WebP xuất ra (Q7): thu nhỏ / lưới / chi tiết. Không phóng to ảnh gốc nhỏ hơn cỡ này.
ITEM_IMAGE_SIZES = {
    "thumb": int(os.getenv("ITEM_IMAGE_SIZE_THUMB", "160")),
    "card": int(os.getenv("ITEM_IMAGE_SIZE_CARD", "480")),
    "detail": int(os.getenv("ITEM_IMAGE_SIZE_DETAIL", "1200")),
}

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
    "NUM_PROXIES": int(os.getenv("DRF_NUM_PROXIES", "1")),
}

# --- Giới hạn tần suất throttle (S03 / L-5, doc/features/2026-09-28-sua-loi-bao-mat) ----
def _rate(name: str, default: str) -> str | None:
    val = os.getenv(name, default).strip()
    if not val or val.lower() in {"off", "none", "0"}:
        return None
    return val

_DEFAULT_THROTTLE_RATES = {
    "shop_lookup_ip": _rate("THROTTLE_SHOP_LOOKUP_IP", "20/min"),
    "shop_lookup_order": _rate("THROTTLE_SHOP_LOOKUP_ORDER", "10/hour"),
    "shop_order_create": _rate("THROTTLE_SHOP_ORDER_CREATE", "20/hour"),
    "shop_checkout": _rate("THROTTLE_SHOP_CHECKOUT", "30/hour"),
    "login_ip": _rate("THROTTLE_LOGIN_IP", "10/min"),
    "login_user": _rate("THROTTLE_LOGIN_USER", "30/hour"),
    "customer_search": _rate("THROTTLE_CUSTOMER_SEARCH", "30/min"),
    "public_content": _rate("THROTTLE_PUBLIC_CONTENT", "120/min"),
}

CAVEVE_THROTTLE_RATES = {k: None for k in _DEFAULT_THROTTLE_RATES} if TESTING else _DEFAULT_THROTTLE_RATES

# --- Tham số nghiệp vụ cấu hình được (không hard-code trong logic) ---------
# Nguồn: business-process-spec.md (BR-MH-02, BR-LO-06, BR-BH-03, BR-GH-04, BR-HV-03).
BATCH_DEFAULT_SHELF_LIFE_DAYS = int(os.getenv("BATCH_DEFAULT_SHELF_LIFE_DAYS", "365"))
BATCH_NEAR_EXPIRY_DAYS = int(os.getenv("BATCH_NEAR_EXPIRY_DAYS", "14"))
SALES_ORDER_TTL_MINUTES = int(os.getenv("SALES_ORDER_TTL_MINUTES", "30"))
DELIVERY_MAX_FAILED_ATTEMPTS = int(os.getenv("DELIVERY_MAX_FAILED_ATTEMPTS", "2"))
COLD_CHAIN_MAX_HOURS = int(os.getenv("COLD_CHAIN_MAX_HOURS", "6"))
# Số dòng nhật ký tối đa trong một timeline "Đã làm" (R2); thừa thì trả timeline_truncated=true.
GUIDANCE_TIMELINE_MAX_ROWS = int(os.getenv("GUIDANCE_TIMELINE_MAX_ROWS", "200"))

INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")

# --- Cổng thanh toán SePay (P1/P3, doc/features/2026-09-26-sepay-cong-thanh-toan) ----------
# BR-TT-14: môi trường + URL cổng + khoá là cấu hình theo môi trường, KHÔNG hard-code.
# Secret thật nằm ở GCP Secret Manager (cangca-sepay-sandbox-*) — KHÔNG có giá trị mặc định
# ở đây, rỗng thì P1 từ chối ký (an toàn hơn ký nhầm bằng chuỗi rỗng).
SEPAY_ENV = os.getenv("SEPAY_ENV", "SANDBOX").strip().upper()  # SANDBOX | PRODUCTION
# BR-TT-18 (#15): cửa sổ (giờ) để coi hai khoản không gắn đơn cùng số tiền là nghi trùng khi ghi tiền về muộn.
LATE_PAYMENT_DUPLICATE_WINDOW_HOURS = int(os.getenv("LATE_PAYMENT_DUPLICATE_WINDOW_HOURS", "72"))
SEPAY_MERCHANT_ID = os.getenv("SEPAY_MERCHANT_ID", "")
SEPAY_SECRET_KEY = os.getenv("SEPAY_SECRET_KEY", "")
SEPAY_CHECKOUT_URL_SANDBOX = os.getenv(
    "SEPAY_CHECKOUT_URL_SANDBOX", "https://pay-sandbox.sepay.vn/v1/checkout/init"
)
SEPAY_CHECKOUT_URL_PRODUCTION = os.getenv(
    "SEPAY_CHECKOUT_URL_PRODUCTION", "https://pay.sepay.vn/v1/checkout/init"
)
# Trang tra đơn Shop — success/cancel/error_url của P1 đều trỏ về đây (BR-TT-12).
SHOP_BASE_URL = os.getenv("SHOP_BASE_URL", "http://localhost:3000").rstrip("/")

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

# --- AI Digital Worker ----------------------------------------------------
AI_ENABLED = _bool("AI_ENABLED", "0")
GUIDANCE_REFUND_WARNING_DAYS = int(os.getenv("GUIDANCE_REFUND_WARNING_DAYS", "25"))
AI_WRITE_LEVELS_ALLOWED = os.getenv("AI_WRITE_LEVELS_ALLOWED", "C").strip().upper()
AI_PRODUCTION_READY = _bool("AI_PRODUCTION_READY", "0")
AI_ACTION_TTL_MINUTES = int(os.getenv("AI_ACTION_TTL_MINUTES", "15"))
AI_UNDO_WINDOW_MINUTES = int(os.getenv("AI_UNDO_WINDOW_MINUTES", "10"))
AI_RED_ZONE_DELAY_MINUTES = int(os.getenv("AI_RED_ZONE_DELAY_MINUTES", "30"))
AI_DEFERRED_DELAY_MINUTES = int(os.getenv("AI_DEFERRED_DELAY_MINUTES", "10"))
AI_DAILY_LIMIT_DEFAULT = int(os.getenv("AI_DAILY_LIMIT_DEFAULT", "20"))
AI_DAILY_LIMIT_RED_ZONE = int(os.getenv("AI_DAILY_LIMIT_RED_ZONE", "10"))
AI_RESULT_MAX_ROWS = int(os.getenv("AI_RESULT_MAX_ROWS", "20"))
AI_RESULT_MAX_CHARS = int(os.getenv("AI_RESULT_MAX_CHARS", "3000"))
AI_SCHEMA_MAX_TOKENS = int(os.getenv("AI_SCHEMA_MAX_TOKENS", "450"))
AI_CALL_RATE = os.getenv("AI_CALL_RATE", "30/min")
AI_CONFIRM_MIN_SECONDS = int(os.getenv("AI_CONFIRM_MIN_SECONDS", "3"))
# GET /api/ai/status/ (S05): model on-device (trống = chưa chốt, S17), công tắc cloud (mặc định tắt, Q5), trần chi phí cloud (BR-AI-11).
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "").strip()
AI_MODEL_VERSION = os.getenv("AI_MODEL_VERSION", "").strip()
AI_MODEL_GGUF_URL = os.getenv("AI_MODEL_GGUF_URL", "").strip()
AI_CLOUD_ENABLED = _bool("AI_CLOUD_ENABLED", "0")
AI_CLOUD_MONTHLY_BUDGET_VND = int(os.getenv("AI_CLOUD_MONTHLY_BUDGET_VND", "200000"))
AI_CLOUD_ALERT_PCT = int(os.getenv("AI_CLOUD_ALERT_PCT", "80"))

# --- Xác nhận đơn (confirmation) & In tem (2026-09-28-cskh-xac-nhan-in-tem) ---------
# Chỉ đọc biến môi trường `CONFIRMATION_*`; tên cũ `CSKH_*` đã bỏ ở P8b Lô 5 (đặt trên Cloud Run thì bị bỏ qua, xem doc/ops/moi-truong.md).
CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS = int(os.getenv("CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS", "3"))
CONFIRMATION_UNREACHABLE_WINDOW_MINUTES = int(os.getenv("CONFIRMATION_UNREACHABLE_WINDOW_MINUTES", "30"))
CONFIRMATION_MIN_RETRY_MINUTES = int(os.getenv("CONFIRMATION_MIN_RETRY_MINUTES", "10"))
CONFIRMATION_MANAGER_DECISION_MINUTES = int(os.getenv("CONFIRMATION_MANAGER_DECISION_MINUTES", "30"))
CONFIRMATION_PII_RECENT_DAYS = int(os.getenv("CONFIRMATION_PII_RECENT_DAYS", "7"))
# NV giao xem dữ liệu khách (tên, SĐT, địa chỉ, ghi chú) của phiếu đã kết thúc trong N ngày lịch (giờ VN), sau đó ẩn (SR-PII-02).
DELIVERY_PII_RECENT_DAYS = int(os.getenv("DELIVERY_PII_RECENT_DAYS", "7"))
CONFIRMATION_CLAIM_MINUTES = int(os.getenv("CONFIRMATION_CLAIM_MINUTES", "5"))
CONFIRMATION_EXTEND_MAX_HOURS = int(os.getenv("CONFIRMATION_EXTEND_MAX_HOURS", "24"))
CONFIRMATION_WORKING_HOURS = os.getenv("CONFIRMATION_WORKING_HOURS", "07:00-21:00")
CONFIRMATION_QUEUE_ALERT_MINUTES = int(os.getenv("CONFIRMATION_QUEUE_ALERT_MINUTES", "60"))
LABEL_UNPRINTED_ALERT_MINUTES = int(os.getenv("LABEL_UNPRINTED_ALERT_MINUTES", "15"))
REFUND_DEADLINE_DAYS = int(os.getenv("REFUND_DEADLINE_DAYS", "30"))
SHOP_HOTLINE = os.getenv("SHOP_HOTLINE", "1900 xxxx")
CONFIRMATION_AUTO_CANCEL_ENABLED = _bool("CONFIRMATION_AUTO_CANCEL_ENABLED", "0")
CONFIRMATION_NOTICE_ENABLED = _bool("CONFIRMATION_NOTICE_ENABLED", "1")

# --- Content / CMS (2026-09-28-cms-viet-bai) -------------------------------
CONTENT_TITLE_MAX = int(os.getenv("CONTENT_TITLE_MAX", "200"))
CONTENT_DESCRIPTION_MAX = int(os.getenv("CONTENT_DESCRIPTION_MAX", "160"))
CONTENT_MAX_IMAGES_PER_ENTRY = int(os.getenv("CONTENT_MAX_IMAGES_PER_ENTRY", "20"))
CONTENT_LIST_PAGE_SIZE = int(os.getenv("CONTENT_LIST_PAGE_SIZE", "12"))
CONTENT_PUBLIC_CACHE_SECONDS = int(os.getenv("CONTENT_PUBLIC_CACHE_SECONDS", "60"))
CONTENT_COST_KEYWORDS = (
    "giá mua",
    "giá vốn",
    "giá nhập",
    "giá cảng",
    "nhà cung cấp",
    "tiền lãi",
)
CONTENT_PHONE_ALLOWLIST = tuple(
    x.strip() for x in os.getenv("CONTENT_PHONE_ALLOWLIST", "").split(",") if x.strip()
)
CONTENT_IMAGE_WIDTHS = {"sm": 480, "md": 960, "lg": 1600}
CONTENT_MAX_BLOCKS = int(os.getenv("CONTENT_MAX_BLOCKS", "300"))
CONTENT_BODY_MAX_CHARS = int(os.getenv("CONTENT_BODY_MAX_CHARS", "60000"))
CONTENT_MAX_IMAGE_UPLOADS_PER_ENTRY = int(os.getenv("CONTENT_MAX_IMAGE_UPLOADS_PER_ENTRY", "100"))

# --- Khung go-live pháp lý (2026-09-28-khung-go-live) -----------------------
SELLER_NAME = os.getenv("SELLER_NAME", "")
SELLER_BUSINESS_TYPE = os.getenv("SELLER_BUSINESS_TYPE", "")
SELLER_REG_NO = os.getenv("SELLER_REG_NO", "")
SELLER_TAX_CODE = os.getenv("SELLER_TAX_CODE", "")
SELLER_ADDRESS = os.getenv("SELLER_ADDRESS", "")
SELLER_PHONE = os.getenv("SELLER_PHONE", "")
SELLER_EMAIL = os.getenv("SELLER_EMAIL", "")


def privacy_consent_required(testing: bool, debug: bool, env) -> bool:
    """Đọc cờ bắt buộc đồng ý chính sách bảo mật: mặc định TẮT khi test/debug, BẬT ngoài dev/test (G1)."""
    raw = env.get("PRIVACY_CONSENT_REQUIRED", "0" if (testing or debug) else "1")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Cờ bắt buộc đồng ý chính sách bảo mật (mặc định BẬT ngoài dev/test - G1)
PRIVACY_CONSENT_REQUIRED = privacy_consent_required(TESTING, DEBUG, os.environ)

# Cờ thông báo xác nhận cuộc gọi (mặc định TẮT tới khi CSKH vận hành - G2)
SHOP_CONFIRM_CALL_NOTICE = _bool("SHOP_CONFIRM_CALL_NOTICE", "0")
SHOP_CONFIRM_CALL_HOURS = os.getenv("SHOP_CONFIRM_CALL_HOURS", "7:00–20:00")




