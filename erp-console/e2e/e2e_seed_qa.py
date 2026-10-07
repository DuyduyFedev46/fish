"""Dữ liệu giả cố định cho e2e chạy trên backend THẬT: đọc bảng mã -> id do `manage.py seed_qa` ghi ra.

Cách chạy (xem backend/README.md, mục "Dữ liệu giả cho e2e"):
    export DJANGO_DEBUG=1 DATABASE_URL=sqlite:////tmp/e2e.sqlite3
    manage.py migrate && manage.py bootstrap_masterdata && QA_PASSWORD=... manage.py seed_qa
    SEED_QA_IDS=/tmp/seed_qa_ids.json QA_PASSWORD=... BASE=<ERP build thật> API=<backend>/ python3 e2e/<kịch bản>.py

Kịch bản KHÔNG cứng id hay mã của phiên QA cũ: lấy qua `ids()`. Mật khẩu các tài khoản `qa_*` lấy từ env QA_PASSWORD (không mặc định).
Hạn giữ chỗ của đơn BOOKED (QA-SO-01/02/13) tính từ lúc seed, nên seed ngay trước khi chạy.
"""

import json
import os

SEED_QA_IDS = os.environ.get("SEED_QA_IDS", "/tmp/seed_qa_ids.json")
BASE = os.environ.get("BASE", "http://127.0.0.1:3521")
API = os.environ.get("API", "http://127.0.0.1:8621").rstrip("/")


def password():
    pw = os.environ.get("QA_PASSWORD")
    if not pw:
        raise SystemExit("Thiếu env QA_PASSWORD (mật khẩu các tài khoản qa_* do seed_qa tạo).")
    return pw


def ids():
    """Bảng mã -> id (khoá: users, customers, items, batches, orders, invoices, delivery_notes, payments, refunds, returns, receipts, stocktakes, call_scripts)."""
    with open(SEED_QA_IDS, encoding="utf-8") as f:
        return json.load(f)


def order_id(code):
    return ids()["orders"][code]["id"]


def orders_with_status(status):
    return [c for c, v in ids()["orders"].items() if v["status"] == status]


def refund_codes_with_status(status):
    return [c for c, v in ids()["refunds"].items() if v["status"] == status]
