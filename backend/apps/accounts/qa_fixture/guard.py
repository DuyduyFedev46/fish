"""
Cổng chặn của `manage.py seed_qa`: bộ dữ liệu giả này KHÔNG BAO GIỜ chạy trên production.

Quy tắc (hồ sơ 2026-10-01-erp-theo-design, mục seed_qa):
1. Chữ ký production luôn bị chặn, không cờ nào mở được: `SEPAY_ENV=PRODUCTION` (SePay live), hoặc DB PostgreSQL tên `postgres` (đúng tên DB
   production trên Supabase, doc/ops/moi-truong.md), hoặc tên DB/host có chữ `prod` mà không có `staging`.
2. Mặc định chỉ chạy khi `DEBUG` bật VÀ (DB là SQLite HOẶC tên DB/host có chữ `staging`).
3. Cờ tường minh `--allow-non-local` chỉ nới điều 2 (DEBUG tắt, hoặc PostgreSQL không tên staging như
   DB dev của máy). Không nới được điều 1.
"""
from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection

PRODUCTION_DB_NAMES = {"postgres"}


def database_facts():
    cfg = connection.settings_dict
    engine = str(cfg.get("ENGINE", ""))
    return {
        "is_sqlite": "sqlite" in engine,
        "name": str(cfg.get("NAME", "")).lower(),
        "host": str(cfg.get("HOST", "")).lower(),
    }


def looks_like_production(facts) -> bool:
    if facts["is_sqlite"]:
        return False
    text = f"{facts['name']} {facts['host']}"
    if facts["name"] in PRODUCTION_DB_NAMES:
        return True
    return "prod" in text and "staging" not in text


def check_allowed(*, allow_non_local=False):
    """Raise CommandError nếu không được phép chạy trên DB hiện tại."""
    if str(getattr(settings, "SEPAY_ENV", "")).upper() == "PRODUCTION":
        raise CommandError(
            "seed_qa từ chối chạy: SEPAY_ENV=PRODUCTION (cổng thanh toán chạy thật). Không cờ nào mở được."
        )
    facts = database_facts()
    if looks_like_production(facts):
        raise CommandError(
            "seed_qa từ chối chạy: DB này giống production (không có cờ nào mở được). "
            "Dữ liệu giả chỉ dành cho SQLite dev hoặc DB staging."
        )
    problems = []
    if not settings.DEBUG:
        problems.append("DEBUG đang tắt")
    if not facts["is_sqlite"] and "staging" not in f"{facts['name']} {facts['host']}":
        problems.append("DB không phải SQLite và tên không chứa 'staging'")
    if problems and not allow_non_local:
        raise CommandError(
            "seed_qa từ chối chạy: " + "; ".join(problems) + ". "
            "Chạy trên máy dev với DJANGO_DEBUG=1 và SQLite; nếu thật sự cần DB khác "
            "(không phải production) thì thêm --allow-non-local."
        )
