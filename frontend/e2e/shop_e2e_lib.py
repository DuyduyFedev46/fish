"""
Thư viện dùng chung cho bộ e2e Shop (SHOP-7-01). Không chạy trực tiếp; xem `run_shop_e2e.py`.

Quy ước:
- Môi trường (BE thật SQLite tạm + Shop + ERP build `USE_MOCK=0`) do `run_shop_e2e.py` dựng và ghi `env.json`
  vào thư mục làm việc. Mọi kịch bản đọc `SHOP_E2E_WORKDIR` để biết cổng, DB, thư mục ảnh.
- Dữ liệu cá nhân 100% giả (Nguyễn Văn A, 0900000001, 1 Đường Thử, Phường Mẫu), bất biến 9.
- Mỗi kịch bản dùng `Report`: `ok(tên, điều kiện, ghi chú)`; cuối kịch bản gọi `finish()` (thoát khác 0 khi còn FAIL).
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
ERP = ROOT / "erp-console"
BACKEND = ROOT / "backend"
DEFAULT_SHOTS = ROOT / "doc/features/2026-10-06-shop-giao-dien-moi/shots/lo7"
DESIGN_DIR = ROOT / "doc/design/shop/screens"

BE_PORT, SHOP_PORT, ERP_PORT = 8000, 3000, 3100
API = f"http://localhost:{BE_PORT}"
SHOP = f"http://localhost:{SHOP_PORT}"
ERP_URL = f"http://localhost:{ERP_PORT}"

# Dữ liệu cá nhân GIẢ dùng khắp bộ kịch bản.
FAKE_NAME = "Lê Thị Mẫu"  # không dùng "Nguyễn Văn A": đó là chữ mẫu (placeholder) có sẵn trong ô Họ và tên
FAKE_PHONE = "0900000001"
FAKE_ADDRESS = "1 Đường Thử, Phường Mẫu"
PII_STRINGS = [FAKE_NAME, FAKE_PHONE, FAKE_ADDRESS, "+84900000001", "900000001", "Phường Mẫu"]
OWNER_USER, QA_PASSWORD = "qa_owner", "QaPass-12345"


def workdir():
    wd = os.environ.get("SHOP_E2E_WORKDIR")
    if not wd:
        sys.exit("Thiếu SHOP_E2E_WORKDIR. Chạy qua: python3 frontend/e2e/run_shop_e2e.py (hoặc --suite <tên>).")
    return Path(wd)


def env_info():
    return json.loads((workdir() / "env.json").read_text())


def shots_dir(sub=""):
    d = Path(os.environ.get("SHOP_E2E_SHOTS") or DEFAULT_SHOTS) / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


class Report:
    def __init__(self, name):
        self.name = name
        self.rows = []

    def ok(self, label, cond, extra=""):
        self.rows.append({"name": label, "pass": bool(cond), "note": "" if cond else str(extra)[:400]})
        print(("PASS " if cond else "FAIL ") + label + ("" if cond else f"  <{str(extra)[:300]}>"), flush=True)
        return bool(cond)

    def skip(self, label, why):
        self.rows.append({"name": label, "pass": None, "note": why})
        print(f"SKIP {label}  ({why})", flush=True)

    def finish(self):
        passed = sum(1 for r in self.rows if r["pass"] is True)
        failed = sum(1 for r in self.rows if r["pass"] is False)
        skipped = sum(1 for r in self.rows if r["pass"] is None)
        print(f"== {self.name}: {passed} PASS, {failed} FAIL, {skipped} SKIP", flush=True)
        try:
            (workdir() / f"result-{self.name}.json").write_text(json.dumps(self.rows, ensure_ascii=False, indent=1))
        except SystemExit:
            pass
        sys.exit(1 if failed or not self.rows else 0)


# ----------------------------------------------------------------------------- API (HTTP thật)
def api(method, path, body=None, token=None, headers=None, base=None):
    """Trả (status, json|None). Không ném lỗi theo mã HTTP."""
    data = None if body is None else json.dumps(body).encode()
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = f"Token {token}"
    req = urllib.request.Request((base or API) + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode("utf-8", "replace")


def login_token(username=OWNER_USER, password=QA_PASSWORD):
    status, body = api("POST", "/api/auth/token/", {"username": username, "password": password})
    assert status == 200, (status, body)
    return body["token"]


def internal_ipn(order_code, amount, txn_id, received_at=None):
    """Giả lập IPN cổng thanh toán qua cửa nội bộ (đúng đường adapter gọi). Gửi lại cùng txn_id = idempotent."""
    from datetime import datetime, timezone
    body = {"bank_txn_id": txn_id, "order_code": order_code, "amount": str(amount),
            "received_at": received_at or datetime.now(timezone.utc).isoformat(), "raw": {}}
    return api("POST", "/api/internal/payments/sepay-ipn/", body,
               headers={"X-Internal-Token": env_info()["internal_token"]})


def manage_shell(code):
    """Chạy một đoạn Python trong `manage.py shell` của DB tạm. Trả stdout."""
    info = env_info()
    env = {**os.environ, **info["be_env"]}
    out = subprocess.run([str(BACKEND / ".venv/bin/python"), "manage.py", "shell", "-c", code], cwd=BACKEND, env=env,
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(out.stderr[-1500:])
    return out.stdout


def stock_set(item_code, kg):
    """Đặt tồn bán được của một món (chỉ lô đang bán đầu tiên) về `kg`; các lô khác của món về 0. Dữ liệu giả."""
    return manage_shell(
        "from decimal import Decimal as D\nfrom apps.inventory.models import Batch\n"
        f"bs=list(Batch.objects.filter(item__code={item_code!r}).order_by('expiry_date','id'))\n"
        "for i,b in enumerate(bs):\n"
        f"    b.qty_available=b.qty_reserved+(D({str(kg)!r}) if i==0 else D(0))\n"
        "    b.status='SELLING' if b.qty_available>b.qty_reserved else 'SOLD_OUT'\n    b.save()\n"
    )


# ----------------------------------------------------------------------------- Trình duyệt
class PageWatch:
    """Gắn vào một page: thu console, lỗi trang, request, để quét dữ liệu cá nhân và ngân sách request."""

    def __init__(self, page):
        self.page = page
        self.console = []
        self.errors = []
        self.requests = []
        self.responses = []
        page.on("console", lambda m: self.console.append((m.type, m.text)))
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        page.on("request", lambda r: self.requests.append((r.method, r.url, r.post_data)))

    def console_errors(self):
        # lỗi tải tài nguyên có chủ ý của kịch bản (mô phỏng 4xx/5xx/mất mạng) không tính là lỗi JS
        # bỏ: lỗi tải tài nguyên do chính kịch bản mô phỏng (4xx/5xx/mất mạng) và RSC prefetch bị huỷ khi kịch bản tự điều hướng
        return [t for k, t in self.console if k == "error" and "Failed to load resource" not in t and "net::ERR" not in t
                and "Failed to fetch RSC payload" not in t]

    def api_calls(self, needle=""):
        return [r for r in self.requests if "/api/" in r[1] and needle in r[1]]


def storage_dump(page):
    return page.evaluate(
        "() => JSON.stringify({l: Object.entries(localStorage), s: Object.entries(sessionStorage), c: document.cookie})")


def contains_pii(text):
    return [p for p in PII_STRINGS if p in text]


def goto(page, url, wait=400):
    page.goto(url if url.startswith("http") else SHOP + url)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(wait)


def snap(page, name, width, sub="", full=False):
    d = shots_dir(sub)
    path = d / f"{name}-{width}.png"
    page.screenshot(path=str(path), full_page=full)
    return path


def no_hscroll(page, width):
    return page.evaluate("document.documentElement.scrollWidth") <= width + 0


def money_ok(text):
    """Mọi số tiền trên trang đúng dạng `1.234.567đ`; không NaN/undefined/thập phân."""
    bad = []
    for m in re.finditer(r"(\d[\d.,]*)\s?[đ₫]", text):
        if not re.fullmatch(r"\d{1,3}(\.\d{3})*", m.group(1)):
            bad.append(m.group(0))
    for w in ("NaN", "undefined", "[object"):
        if w in text:
            bad.append(w)
    return bad


def add_to_cart(page, item_code, qty_clicks=0, unit="kg"):
    """Vào trang chi tiết rồi bấm "Thêm vào giỏ" (qty_clicks lần "Thêm 0,5 kg" trước đó)."""
    goto(page, f"/shop/item/?code={item_code}")
    for _ in range(qty_clicks):
        page.get_by_role("button", name=re.compile(r"^Thêm (0,5|1)\s(kg|combo)")).click()
    page.get_by_role("button", name="Thêm vào giỏ").click()
    page.wait_for_timeout(500)


def fill_checkout(page, name=FAKE_NAME, phone=FAKE_PHONE, address=FAKE_ADDRESS, consent=True):
    page.fill("#f-name", name)
    page.fill("#f-phone", phone)
    page.fill("#f-addr", address)
    box = page.locator("#f-consent")
    if consent and box.count():
        box.check()


# ----------------------------------------------------------------------------- Dựng đơn nhanh bằng API (cho ca cần trạng thái đơn)
def privacy_consent():
    status, body = api("GET", "/api/public/content/pages/by-role/privacy/")
    return {"accepted": True, "policy_version_id": body["version_id"]} if status == 200 else None


def create_order_api(items, *, name=FAKE_NAME, phone=FAKE_PHONE, address=FAKE_ADDRESS, voucher=None, base=None,
                     request_id=None):
    """POST /api/shop/orders/ như FE. items = [(item_code, "1.5"), ...]. Trả (status, body)."""
    import uuid
    payload = {"client_request_id": request_id or str(uuid.uuid4()), "customer": {"name": name, "phone": phone},
               "delivery_address": address, "items": [{"item_code": c, "qty": q} for c, q in items]}
    consent = privacy_consent()
    if consent:
        payload["privacy_consent"] = consent
    if voucher:
        payload["voucher_code"] = voucher
    return api("POST", "/api/shop/orders/", payload, base=base)


def pay_order(order_code, amount, txn_id=None):
    import uuid
    return internal_ipn(order_code, amount, txn_id or f"E2E-{uuid.uuid4().hex[:12]}")


def lookup_api(order_code, phone=None, token=None, base=None):
    body = {"order_code": order_code}
    if token:
        body["token"] = token
    if phone:
        body["phone"] = phone
    return api("POST", "/api/shop/orders/lookup/", body, base=base)


def order_count(phone=FAKE_PHONE):
    return int(manage_shell(
        f"from apps.sales.models import SalesOrder\nprint(SalesOrder.objects.filter(phone={phone!r}).count())").strip())


def set_delivery_status(order_code, status):
    """Đặt trạng thái phiếu giao của đơn đã trả (CONFIRMING/PREPARING/READY/DELIVERING/COMPLETED/FAILED). Dữ liệu giả."""
    return manage_shell(
        "from apps.sales.models import SalesOrder\nfrom apps.delivery.models import DeliveryNote\n"
        f"o=SalesOrder.objects.get(code={order_code!r})\n"
        f"n=DeliveryNote.objects.filter(sales_invoice__sales_order=o).order_by('-id').first()\n"
        f"n.status={status!r}; n.save()\nprint(n.status)\n")


def set_order_status(order_code, status):
    return manage_shell(
        "from apps.sales.models import SalesOrder\n"
        f"SalesOrder.objects.filter(code={order_code!r}).update(status={status!r})\n")


def expire_hold(order_code):
    """Đưa hạn giữ chỗ về quá khứ (chưa chạy job) → trạng thái hold_expired."""
    return manage_shell(
        "from datetime import timedelta\nfrom django.utils import timezone\nfrom apps.sales.models import SalesOrder\n"
        f"SalesOrder.objects.filter(code={order_code!r}).update(booked_expires_at=timezone.now()-timedelta(minutes=2))\n")


def run_expiry_job():
    info = env_info()
    env = {**os.environ, **info["be_env"]}
    return subprocess.run([str(BACKEND / ".venv/bin/python"), "manage.py", "cancel_expired_orders"], cwd=BACKEND,
                          env=env, capture_output=True, text=True, timeout=120).stdout


def cancel_paid(order_code, note="Hết hàng lúc soạn (giả)"):
    return manage_shell(
        "from apps.sales.models import SalesOrder\nfrom apps.sales.orders import services\n"
        "from django.contrib.auth import get_user_model\n"
        f"o=SalesOrder.objects.get(code={order_code!r})\n"
        "u=get_user_model().objects.get(username='qa_owner')\n"
        f"services.cancel_paid_order(order=o, actor=u, cancel_note={note!r})\n")


def spawn_be(port, extra_env):
    """BE thứ hai (cùng DB tạm) với giới hạn tần suất riêng, để thấy 429 thật. Gọi `.terminate()` khi xong."""
    info = env_info()
    env = {**os.environ, **info["be_env"], **extra_env}
    p = subprocess.Popen([str(BACKEND / ".venv/bin/python"), "manage.py", "runserver", str(port), "--noreload"],
                         cwd=BACKEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import time
    for _ in range(40):
        try:
            urllib.request.urlopen(f"http://localhost:{port}/api/shop/catalog/", timeout=2)
            return p
        except Exception:
            time.sleep(0.5)
    p.terminate()
    raise RuntimeError("BE phụ không lên")


def redemption_state(order_code):
    out = manage_shell(
        "from apps.sales.models import VoucherRedemption\n"
        f"r=VoucherRedemption.objects.filter(order__code={order_code!r}).first()\nprint(r.state if r else 'NONE')").strip()
    return out


def order_status(order_code):
    return manage_shell(
        "from apps.sales.models import SalesOrder\n"
        f"print(SalesOrder.objects.get(code={order_code!r}).status)").strip()


def expire_hold_in(order_code, seconds):
    """Đặt hạn giữ chỗ còn `seconds` giây nữa (để thấy đồng hồ về 0 khi khách đang xem trang)."""
    return manage_shell(
        "from datetime import timedelta\nfrom django.utils import timezone\nfrom apps.sales.models import SalesOrder\n"
        f"SalesOrder.objects.filter(code={order_code!r}).update(booked_expires_at=timezone.now()+timedelta(seconds={int(seconds)}))\n")
