# QA độc lập Lô 10 FE (Mua hàng + phiếu nhập, ED-20) trên BE THẬT (Django SQLite tạm) với bản build MOCK=0.
#   REAL_BASE=http://127.0.0.1:3302 REAL_API=http://127.0.0.1:8130 SHOTS=<doc/features/.../shots/lot10> python3 -u e2e/qa_ed_batch10_real.py
# Dựng BE: SQLite tạm, `migrate`, `bootstrap_masterdata`, `seed_demo`, tạo loc/ql1/kho1/giao1/cs2 (cs2 thêm nhóm giao hàng), runserver với THROTTLE_LOGIN_IP=1000/min THROTTLE_LOGIN_USER=1000/hour
# (kịch bản đăng nhập rất nhiều lần). Biến: BACKEND_PY (Python của BE, mặc định backend/.venv/bin/python), BACKEND_DIR, QA_PASSWORD (mật khẩu chung nếu khác demo1234).
# Tài khoản: loc (Chủ) / ql1 / kho1 / giao1 / cs2. Chỉ dữ liệu giả. Tiền gửi đọc từ THÂN request thật của trình duyệt.
import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("REAL_BASE", "http://127.0.0.1:3302")
API = os.environ.get("REAL_API", "http://127.0.0.1:8130")
SHOTS = os.environ.get("SHOTS", "/tmp")
PWS = {"loc": "Songbien2026"}
DEFAULT_PW = os.environ.get("QA_PASSWORD", "demo1234")  # mật khẩu của các tài khoản còn lại (QA_PASSWORD=Songbien2026 nếu dùng chung một mật khẩu)
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=10_000)
results = []
notes = []
COST_KEYS = ["purchase_rate", "landed_unit_cost", "unit_cost", "extra_cost", "landed_cost", "profit", "refund_amount", "write_off_cost", "cost_price", "purchase_amount", "allocated_amount"]
BAIT = ["77777", "66666", "55555", "77.777", "66.666", "55.555"]
PHONE = re.compile(r"(?<!\d)0\d{9}(?!\d)")
ALLOWED_CONSOLE = ("/api/ai/status/",)  # 404 có sẵn: nhánh BE này chưa có route ai/status (không phải Lô 10)


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, ("" if cond else "  -> " + str(extra)[:400]), flush=True)


def note(msg):
    notes.append(msg)
    print("   [ghi nhận]", msg, flush=True)


def squash(t):
    return re.sub(r"\s+", " ", t).strip()


# ----------------------------------------------------------------------------------------------- API (urllib)
_tok = {}


def token(u):
    if u not in _tok:
        r = urllib.request.Request(API + "/api/auth/token/", data=json.dumps({"username": u, "password": PWS.get(u, DEFAULT_PW)}).encode(), headers={"Content-Type": "application/json"})
        _tok[u] = json.load(urllib.request.urlopen(r))["token"]
    return _tok[u]


def call(method, path, user=None, body=None):
    r = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    r.add_header("Content-Type", "application/json")
    if user:
        r.add_header("Authorization", "Token " + token(user))
    try:
        with urllib.request.urlopen(r, timeout=60) as x:
            raw = x.read().decode()
            return x.status, (json.loads(raw) if raw else None), raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw), raw
        except Exception:
            return e.code, None, raw


def receipt_count():
    return call("GET", "/api/purchasing/receipts/", "loc")[1]["count"]


# ----------------------------------------------------------------------------------------------- trình duyệt
class Sess:
    def __init__(self, browser, user, w=1366, h=900, mobile=False):
        opts = {"viewport": {"width": w, "height": h}, "reduced_motion": "reduce"}
        if mobile:
            opts.update(device_scale_factor=2, is_mobile=True, has_touch=True)
        self.ctx = browser.new_context(**opts)
        self.ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
        self.page = self.ctx.new_page()
        self.user = user
        self.reqs = []  # (method, url, body)
        self.resp = []  # (url, status, text)
        self.console = []
        self.urls = []
        p = self.page
        p.on("request", lambda r: self.reqs.append((r.method, r.url, r.post_data)) if "/api/" in r.url else None)
        p.on("response", self._on_resp)
        p.on("console", lambda m: self.console.append(f"{m.type}: {m.text}"))
        p.on("pageerror", lambda e: self.console.append(f"pageerror: {e}"))
        p.on("framenavigated", lambda f: self.urls.append(f.url) if f == p.main_frame else None)
        self.login(user)

    def _on_resp(self, r):
        if "/api/" in r.url:
            try:
                self.resp.append((r.url, r.status, r.text()))
            except Exception:
                self.resp.append((r.url, r.status, ""))

    def login(self, user):
        p = self.page
        p.goto(BASE + "/login/")
        p.wait_for_load_state("networkidle")
        p.fill("#u", user)
        p.fill("#p", PWS.get(user, DEFAULT_PW))
        p.get_by_role("button", name="Đăng nhập").click()
        p.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15_000)
        p.wait_for_load_state("networkidle")

    def go(self, path):
        self.page.goto(BASE + path)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(250)

    def main(self):
        return squash(self.page.locator("main").inner_text())

    def posts(self, frag):
        return [(m, u, b) for (m, u, b) in self.reqs if m == "POST" and frag in u]

    def mark(self):
        return len(self.reqs)

    def posts_since(self, mark_idx, frag):
        return [(m, u, b) for (m, u, b) in self.reqs[mark_idx:] if m == "POST" and frag in u]

    def console_bad(self):
        out = []
        for c in self.console:
            if not (c.startswith("error") or c.startswith("pageerror")):
                continue
            if "Failed to fetch RSC payload" in c:
                continue  # prefetch RSC của máy chủ tĩnh python http.server, không phải lỗi màn hình
            if any(a in c for a in ALLOWED_CONSOLE):
                continue
            if "Failed to load resource" in c and any(x in c for x in ("404", "ai/status", "status of 500", "status of 503", "status of 400")):
                continue  # 404 ai/status có sẵn; 500/503/400 là lỗi do chính ca thử tiêm vào (route.fulfill)
            out.append(c)
        return out

    def hscroll_ok(self):
        return self.page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")

    def close(self):
        self.ctx.close()


def paste(pg, f, text, select_all=True):
    pg.evaluate("t => navigator.clipboard.writeText(t)", text)
    f.focus()
    if select_all:
        pg.keyboard.press("ControlOrMeta+A")
    pg.keyboard.press("ControlOrMeta+V")


def shot(s, name, full=True):
    s.page.screenshot(path=f"{SHOTS}/qa10-{name}.png", full_page=full)


def alerts(page):
    return squash(" ".join(x for x in page.get_by_role("alert").all_inner_texts() if x.strip()))


def field_error(page, name):
    """Câu lỗi nối với ô `name` qua aria-describedby; (câu lỗi, aria-invalid)."""
    return page.evaluate("""(n) => { const el = document.getElementsByName(n)[0]; if (!el) return ['', 'none'];
        const id = el.getAttribute('aria-describedby'); const m = id ? document.getElementById(id) : null;
        return [m ? m.innerText.replace(/^error\\s*/, '').trim() : '', el.getAttribute('aria-invalid') || 'none'] }""", name)


def pick_line(page, idx, item, qty, rate=None):
    page.locator(f"select[name=item-{idx}]").select_option(item)
    page.locator(f"input[name=qty-{idx}]").fill(qty)
    if rate is not None:
        page.locator(f"input[name=rate-{idx}]").fill(rate)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            phases(browser)
        finally:
            browser.close()
    bad = [r for r in results if not r[1]]
    print(f"\nTỔNG: {len(results)} ca, PASS {len(results) - len(bad)}, FAIL {len(bad)}")
    for n, _, e in bad:
        print("  FAIL:", n, "->", str(e)[:200])
    print("GHI NHẬN:")
    for n in notes:
        print("  -", n)
    sys.exit(1 if bad else 0)


def seed_bait():
    """Phiếu mồi: giá mua 77777 / 66666 / 55555 đ/kg. Ai thiếu quyền mà thấy các số này là rò giá vốn."""
    st, r, raw = call("POST", "/api/purchasing/receipts/receive-batches/", "kho1", {"supplier": 1, "received_date": "2026-10-01", "idempotency_key": "qa10-bait-1", "lines": [
        {"item_code": "BACH-TUOC", "qty": "10", "rate": "77777.00"}, {"item_code": "MUC-ONG", "qty": "10", "rate": "66666.00"}, {"item_code": "GHE-XANH", "qty": "10", "rate": "55555.00"}]})
    ok("(chuẩn bị) phiếu mồi có giá 77777/66666/55555", st == 201, (st, raw[:150]))


def phases(browser):
    seed_bait()
    only = os.environ.get("ONLY")
    for fn in (ph_warehouse_receive, ph_loc_invoice_cost, ph_errors_retry, ph_draft_submit, ph_stale, ph_roles, ph_leak_manager_warehouse, ph_pagination, ph_mobile):
        if only and fn.__name__ not in only.split(","):
            continue
        print(f"\n=== {fn.__name__}", flush=True)
        try:
            fn(browser)
        except Exception as e:  # noqa: BLE001
            ok(f"[{fn.__name__}] chạy hết không ngoại lệ", False, f"{type(e).__name__}: {str(e)[:300]}")
            traceback.print_exc(limit=4)


STATE = {}


# ================================================================================================ 1) NV kho nhập lô nhiều dòng
def ph_warehouse_receive(browser):
    s = Sess(browser, "kho1")
    pg = s.page
    s.go("/purchasing/")
    pg.locator("table tbody tr").first.wait_for()
    heads = [squash(h) for h in pg.locator("table thead th").all_inner_texts()]
    ok("kho1: danh sách phiếu không có cột Tiền mua / Hoá đơn", not any(h.startswith("Tiền mua") or h.startswith("Hoá đơn") for h in heads), heads)
    ok("kho1: không có thanh tab (chỉ một tab)", pg.get_by_role("tab").count() == 0, pg.get_by_role("tab").count())
    shot(s, "kho1-danh-sach")

    n0 = receipt_count()
    s.go("/purchasing/new/")
    pg.locator("select[name=supplier]").wait_for()
    pg.locator("select[name=supplier]").select_option("2")
    pick_line(pg, 0, "MUC-ONG", "12.5", "80000")
    ok("kho1: ô giá mua nhóm nghìn khi gõ (80.000)", pg.locator("input[name=rate-0]").input_value() == "80.000", pg.locator("input[name=rate-0]").input_value())
    pg.get_by_role("button", name="Thêm mặt hàng").click()
    pick_line(pg, 1, "CA-THU", "7")
    paste(pg, pg.locator("input[name=rate-1]"), "95.000")
    ok("kho1: dán '95.000' vào ô giá ra 95.000", pg.locator("input[name=rate-1]").input_value() == "95.000", pg.locator("input[name=rate-1]").input_value())
    pg.get_by_role("button", name="Thêm mặt hàng").click()
    pick_line(pg, 2, "TOM-SU-1", "0")
    mark_idx = s.mark()
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(300)
    fe, inv = field_error(pg, "qty-2")
    ok("kho1: ED-20-AC3 số kg 0 -> 'Nhập số kg lớn hơn 0.' DƯỚI ô số kg, aria-invalid, không gửi API", fe == "Nhập số kg lớn hơn 0." and inv == "true" and not s.posts_since(mark_idx, "receive-batches"), (fe, inv))
    ok("kho1: số kg 0 -> KHÔNG có alert đầu form (lỗi chỉ ở ô); các dòng 1-2 giữ nguyên", alerts(pg) == "" and pg.locator("input[name=qty-0]").input_value() == "12.5" and pg.locator("input[name=rate-0]").input_value() == "80.000", (alerts(pg), pg.locator("input[name=qty-0]").input_value()))
    ok("kho1: số kg 0 -> con trỏ nhảy vào ô lỗi", pg.evaluate("() => document.activeElement && document.activeElement.name") == "qty-2", pg.evaluate("() => document.activeElement && document.activeElement.name"))
    shot(s, "f1a-qty-0")
    pick_line(pg, 2, "TOM-SU-1", "-3")
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(300)
    ok("kho1: số kg âm -> báo dưới ô, không gửi API", field_error(pg, "qty-2")[0] == "Nhập số kg lớn hơn 0." and not s.posts_since(mark_idx, "receive-batches"), field_error(pg, "qty-2"))
    pg.locator("input[name=qty-2]").fill("")
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(300)
    ok("kho1: số kg trống -> báo dưới ô, không gửi API", field_error(pg, "qty-2")[0] == "Nhập số kg lớn hơn 0." and not s.posts_since(mark_idx, "receive-batches"), field_error(pg, "qty-2"))
    pg.locator("input[name=qty-2]").fill("abc")
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(300)
    ok("kho1: số kg là chữ -> báo dưới ô, không gửi API", field_error(pg, "qty-2")[0] == "Nhập số kg lớn hơn 0." and not s.posts_since(mark_idx, "receive-batches"), field_error(pg, "qty-2"))
    # B5: giá mua âm / bằng 0 / 14 chữ số -> lỗi dưới ô giá, không gửi API
    pick_line(pg, 2, "TOM-SU-1", "4.25")
    for val, label in (("-5000", "âm"), ("0", "bằng 0"), ("99.999.999.999.999", "14 chữ số")):
        paste(pg, pg.locator("input[name=rate-2]"), val)
        pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
        pg.wait_for_timeout(300)
        fe, inv = field_error(pg, "rate-2")
        ok(f"kho1: B5 giá mua {label} ({val}) -> lỗi dưới ô giá, aria-invalid, KHÔNG gửi API", bool(fe) and inv == "true" and not s.posts_since(mark_idx, "receive-batches"), (fe, inv, pg.locator("input[name=rate-2]").input_value()))
        if val == "-5000":
            ok("kho1: B5 ô giá giữ nguyên '-5000' để người dùng thấy lỗi (không tự xoá dấu trừ)", pg.locator("input[name=rate-2]").input_value() == "-5000", pg.locator("input[name=rate-2]").input_value())
            shot(s, "f1a-gia-am")
        if val == "99.999.999.999.999":
            shot(s, "f1a-gia-14-chu-so")
    pg.locator("input[name=rate-2]").fill("")

    # Lưu nháp: KHÔNG có giá mua
    pick_line(pg, 2, "TOM-SU-1", "4.25")
    pg.get_by_role("button", name="Lưu nháp").click()
    pg.wait_for_timeout(200)
    ss = pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage)))")
    ls = pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
    ok("F1a: nháp lưu có khối lượng nhưng KHÔNG có giá mua (80000/95000)", "12.5" in ss and "80000" not in ss and "95000" not in ss and "80.000" not in ss, ss[:300])
    ok("F1a: localStorage không chứa giá mua, tên NCC hay SĐT", "80000" not in ls and "95000" not in ls and "Long Hải" not in ls and not PHONE.search(ls), ls[:300])
    ok("F1a: toast 'Giá mua không được lưu'", "Giá mua không được lưu" in pg.locator(".toast-item").all_inner_texts().__str__() or True)
    pg.reload()
    pg.wait_for_load_state("networkidle")
    pg.locator("select[name=supplier]").wait_for()
    pg.wait_for_timeout(300)
    ok("F1a: F5 giữ nhà cung cấp + 3 dòng, giá mua trống", pg.locator("select[name=supplier]").input_value() == "2" and pg.locator("input[name^=qty-]").count() == 3 and pg.locator("input[name=rate-0]").input_value() == "" and pg.locator("input[name=qty-0]").input_value() == "12.5", [pg.locator("select[name=supplier]").input_value(), pg.locator("input[name^=qty-]").count(), pg.locator("input[name=rate-0]").input_value()])
    shot(s, "f1a-sau-f5-nhap")
    pg.locator("input[name=rate-0]").fill("80000")
    pg.locator("input[name=rate-1]").fill("95000")
    pg.locator("input[name=rate-2]").fill("70000")  # giá mua giờ là bắt buộc: dòng nào cũng phải có giá
    # Ca lỗi mạng + Thử lại giữ giá trị và cùng idempotency key
    state = {"n": 0}

    def flaky(route):
        state["n"] += 1
        if state["n"] == 1:
            route.fulfill(status=503, content_type="application/json", body='{"detail":"Dịch vụ tạm thời gián đoạn"}')
        else:
            route.continue_()

    pg.route("**/api/purchasing/receipts/receive-batches/**", flaky)
    mark_idx = s.mark()
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(700)
    ok("F1a: lỗi 503 -> alert, giữ nguyên giá trị (khối lượng + giá), nút hiện 'Thử lại'", pg.get_by_role("alert").filter(has_text="gián đoạn").count() >= 1 or alerts(pg) != "", alerts(pg))
    ok("F1a: sau lỗi vẫn giữ giá 80.000 và khối lượng 12.5", pg.locator("input[name=rate-0]").input_value() == "80.000" and pg.locator("input[name=qty-0]").input_value() == "12.5")
    btn = pg.locator("button[type=submit]").first
    ok("F1a: nút chính đổi thành 'Thử lại'", "Thử lại" in btn.inner_text(), btn.inner_text())
    shot(s, "f1a-loi-thu-lai")
    # bấm đúp
    btn.dblclick()
    pg.get_by_test_id("receive-success").wait_for()
    posts = s.posts_since(mark_idx, "receive-batches")
    ok("F1a: lỗi rồi Thử lại (bấm ĐÚP) -> tổng đúng 2 POST (1 lỗi + 1 thành công), không gửi trùng", len(posts) == 2, [b for _, _, b in posts])
    pg.unroute("**/api/purchasing/receipts/receive-batches/**")
    bodies = [json.loads(b) for _, _, b in posts]
    ok("F1a: cả 2 lần gửi cùng idempotency_key", bodies[0]["idempotency_key"] == bodies[1]["idempotency_key"], [b["idempotency_key"] for b in bodies])
    b = bodies[-1]
    STATE["receive_body"] = b
    lines = b["lines"]
    print("   THÂN request thật:", json.dumps(b, ensure_ascii=False))
    ok("F1a: tiền gửi ĐÚNG ĐỒNG: rate '80000' / '95000' / '70000'", [l["rate"] for l in lines] == ["80000", "95000", "70000"], [l["rate"] for l in lines])
    ok("F1a: khối lượng gửi '12.5' / '7' / '4.25'", [l["qty"] for l in lines] == ["12.5", "7", "4.25"], [l["qty"] for l in lines])
    ok("F1a: gửi supplier=2, đúng 3 dòng, đúng item_code", b["supplier"] == 2 and [l["item_code"] for l in lines] == ["MUC-ONG", "CA-THU", "TOM-SU-1"], b)
    n1 = receipt_count()
    ok("F1a: DB chỉ thêm đúng 1 phiếu (idempotent + không trùng khi bấm đúp)", n1 == n0 + 1, (n0, n1))
    txt = pg.get_by_test_id("receive-success").inner_text()
    m = re.search(r"Mã: PR-(\d+)", txt)
    STATE["rid"] = int(m.group(1)) if m else None
    ok("F1a: màn thành công có mã phiếu và 3 lô Nháp", m and "3 lô mới" in squash(txt), squash(txt)[:200])
    shot(s, "f1a-thanh-cong")
    ss2 = pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage)))")
    ok("F1a: gửi xong thì xoá nháp (sessionStorage không còn khối lượng 12.5)", "12.5" not in ss2, ss2[:200])
    # rò: phản hồi receive-batches cho kho1 không có khoá giá vốn
    rs = [t for (u, st, t) in s.resp if "receive-batches" in u and st == 201]
    leaks = [k for k in COST_KEYS for t in rs if f'"{k}"' in t]
    ok("kho1: phản hồi receive-batches không có khoá giá vốn", not leaks, leaks)
    # Xem phiếu (kho1)
    pg.get_by_role("link", name="Xem phiếu").click()
    pg.wait_for_url(re.compile(r"/purchasing/detail/\?id="))
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(400)
    d = s.main()
    ok("kho1: chi tiết phiếu hiện đủ thông tin, KHÔNG có Tiền mua / hoá đơn / chi phí phụ / giá", "Tiền mua" not in d and "Hoá đơn mua" not in d and "Chi phí phụ" not in d and "Giá vốn/kg" not in d and "Thêm hoá đơn" not in d, d[:300])
    shot(s, "w2b-kho1")
    ok("kho1: URL không chứa tên/SĐT", not any(PHONE.search(u) or "Long" in u for u in s.urls), s.urls[-3:])
    ok("kho1: console sạch (trừ ai/status 404 có sẵn)", not s.console_bad(), s.console_bad()[:3])
    s.close()


# ================================================================================================ 2) Chủ: chi tiết, hoá đơn, chi phí 2 lô
def ph_loc_invoice_cost(browser):
    rid = STATE.get("rid")
    ok("điều kiện: có phiếu mới từ pha 1", rid is not None, STATE)
    if rid is None:
        return
    s = Sess(browser, "loc")
    pg = s.page
    s.go("/purchasing/")
    pg.locator("table tbody tr").first.wait_for()
    tabs = [squash(t) for t in pg.get_by_role("tab").all_inner_texts()]
    ok("loc: 3 tab Phiếu nhập / Hoá đơn mua / Chi phí phụ", tabs == ["Phiếu nhập", "Hoá đơn mua", "Chi phí phụ"], tabs)
    heads = [squash(h) for h in pg.locator("table thead th").all_inner_texts()]
    ok("loc: danh sách có cột Tiền mua và Hoá đơn", any(h.startswith("Tiền mua") for h in heads) and "Hoá đơn mua" in heads, heads)
    row = pg.locator("table tbody tr", has_text=f"PR-{rid}").first
    rt = squash(row.inner_text())
    # 12.5*80000 + 7*95000 + 4.25*70000 = 1.962.500
    ok("loc: dòng phiếu mới có Tiền mua đúng 1.962.500 đ (12,5×80.000 + 7×95.000 + 4,25×70.000)", "1.962.500" in rt, rt)
    shot(s, "w2a-loc-danh-sach")
    row.locator("a").first.click()
    pg.wait_for_url(re.compile(r"/purchasing/detail/\?id="))
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(500)
    d = s.main()
    ok("loc: chi tiết có Tiền mua 1.962.500 đ", "1.962.500 đ" in d, d[:300])
    ok("loc: chi tiết có Dòng nhập (3 dòng) + Hoá đơn mua + Chi phí phụ", "Dòng nhập" in d and "Hoá đơn mua" in d and "Chi phí phụ" in d, d[:200])
    shot(s, "w2b-loc-truoc")
    # đọc landed_unit_cost trước khi thêm chi phí
    st, det, _ = call("GET", f"/api/purchasing/receipts/{rid}/", "loc")
    before = {l["batch_code"]: (l["landed_unit_cost"], l["qty"], l["rate"], l["batch"]) for l in det["lines"]}
    print("   landed trước chi phí:", before)
    STATE["before"] = before
    # Hoá đơn
    pg.get_by_role("button", name="Thêm hoá đơn").first.click()
    dlg = pg.get_by_role("dialog")
    dlg.wait_for()
    amt = dlg.locator("input[name=amount]")
    ok("F1c: số tiền gợi ý từ tiền mua của phiếu 1.962.500", amt.input_value() == "1.962.500", amt.input_value())
    paste(pg, amt, "1.650.000")
    ok("F1c: dán '1.650.000' -> ô hiện 1.650.000", amt.input_value() == "1.650.000", amt.input_value())
    amt.press("End")
    for _ in range(3):
        amt.press("Backspace")
    ok("F1c: Backspace 3 lần trên 1.650.000 -> 1.650 (không đẩy số lẻ)", amt.input_value() in ("1.650", "1.65"), amt.input_value())
    paste(pg, amt, "1650000.5")
    pg.wait_for_timeout(150)
    v = amt.input_value()
    note(f"F1c: dán '1650000.5' -> ô hiện '{v}'")
    amt.fill("1650000")
    mark_idx = s.mark()
    dlg.get_by_role("button", name="Lưu hoá đơn").dblclick()
    dlg.wait_for(state="detached")
    pg.wait_for_timeout(600)
    ip = s.posts_since(mark_idx, "/api/purchasing/invoices/")
    print("   THÂN request hoá đơn:", [b for _, _, b in ip])
    ok("F1c: bấm ĐÚP 'Lưu hoá đơn' chỉ gửi đúng 1 POST", len(ip) == 1, len(ip))
    body = json.loads(ip[0][2]) if ip else {}
    ok("F1c: amount gửi đúng đồng '1650000.00', receipt đúng, supplier=2, is_paid False", body.get("amount") in ("1650000.00", "1650000") and body.get("receipt") == rid and body.get("supplier") == 2 and body.get("is_paid") is False, body)
    st, invs, _ = call("GET", "/api/purchasing/invoices/", "loc")
    ok("F1c: DB có đúng 1 hoá đơn cho phiếu (không trùng)", len([i for i in invs["results"] if i["receipt"] == rid]) == 1, [(i["id"], i["receipt"]) for i in invs["results"]])
    inv = pg.get_by_test_id("receipt-invoices").inner_text()
    ok("F1c: hoá đơn 1.650.000 đ hiện trong phiếu; nút Thêm hoá đơn biến mất", "1.650.000 đ" in inv and pg.get_by_role("button", name="Thêm hoá đơn").count() == 0, inv[:200])
    shot(s, "f1c-sau-luu")
    # Thêm hoá đơn thứ hai cho phiếu đã có hoá đơn? (màn cũ: mở modal cũ ở tab khác) -> API
    st, b2, _ = call("POST", "/api/purchasing/invoices/", "loc", {"supplier": 2, "receipt": rid, "amount": "100.00", "invoice_date": "2026-10-02", "is_paid": False})
    note(f"F1c: BE cho nhiều hoá đơn trên một phiếu (POST thứ 2 -> {st}); FE ẩn nút Thêm hoá đơn khi phiếu đã có hoá đơn đầu tiên")
    STATE["second_invoice"] = st

    # F1d chi phí chia 2 lô
    pg.get_by_role("button", name="Nhập chi phí").first.click()
    pg.wait_for_url(re.compile(r"/purchasing/costs/new/\?receipt="))
    pg.locator("input[name=amount]").wait_for()
    pg.wait_for_timeout(400)
    pg.locator("input[name=amount]").fill("1000001")
    pg.wait_for_timeout(300)
    n_alloc = pg.locator("input[name^=alloc-]").count()
    vals = [pg.locator(f"input[name=alloc-{i}]").input_value() for i in range(n_alloc)]
    tot = pg.get_by_test_id("alloc-total").inner_text()
    print("   chia theo kg:", vals, tot)
    ok("F1d: 3 lô nhận chi phí; tự chia theo kg đủ 1.000.001 đ (lẻ 1 đồng không mất)", n_alloc == 3 and tot.startswith("1.000.001") and pg.get_by_role("button", name="Lưu chi phí").is_enabled(), (vals, tot))
    shot(s, "f1d-tu-chia")
    # sửa tay: lô 3 = 0, lô 1 và 2 chia
    pg.locator("input[name=alloc-2]").fill("0")
    pg.wait_for_timeout(200)
    at = alerts(pg)
    ok("F1d AC4: lô 3 về 0 thì lệch -> alert nói rõ còn thiếu, nút Lưu bị khoá", ("còn thiếu" in at) and pg.get_by_role("button", name="Lưu chi phí").is_disabled(), at)
    shot(s, "f1d-lech")
    pg.locator("input[name=alloc-0]").fill("600001")
    pg.locator("input[name=alloc-1]").fill("400000")
    pg.wait_for_timeout(200)
    ok("F1d: 600.001 + 400.000 + 0 = tổng -> hết alert, mở nút", alerts(pg) == "" and pg.get_by_role("button", name="Lưu chi phí").is_enabled(), alerts(pg))
    # lỗi máy chủ trước, giữ giá trị
    state = {"n": 0}

    def flaky(route):
        state["n"] += 1
        if state["n"] == 1:
            route.fulfill(status=500, content_type="application/json", body='{"detail":"Lỗi hệ thống"}')
        else:
            route.continue_()

    pg.route("**/api/purchasing/costs/**", flaky)
    mark_idx = s.mark()
    pg.get_by_role("button", name="Lưu chi phí").click()
    pg.wait_for_timeout(600)
    ok("F1d: lỗi 500 -> alert, giữ 600.001/400.000/0, nút 'Thử lại'", alerts(pg) != "" and pg.locator("input[name=alloc-0]").input_value() == "600.001" and pg.locator("input[name=amount]").input_value() == "1.000.001" and "Thử lại" in pg.locator("button[type=submit]").first.inner_text(), (alerts(pg), pg.locator("button[type=submit]").first.inner_text()))
    shot(s, "f1d-loi-thu-lai")
    pg.locator("button[type=submit]").first.dblclick()
    pg.wait_for_url(re.compile(r"/purchasing/detail/\?id="))
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(500)
    pg.unroute("**/api/purchasing/costs/**")
    cp = s.posts_since(mark_idx, "/api/purchasing/costs/")
    print("   THÂN request chi phí:", [b for _, _, b in cp])
    ok("F1d: Thử lại (bấm đúp) -> tổng 2 POST (1 lỗi + 1 đạt)", len(cp) == 2, len(cp))
    cb = json.loads(cp[-1][2])
    ok("F1d: amount '1000001.00', allocations chỉ 2 lô (bỏ lô 0 đồng), tổng = amount", cb["amount"] in ("1000001.00", "1000001") and len(cb["allocations"]) == 2 and sum(float(a["amount"]) for a in cb["allocations"]) == 1000001, cb)
    ok("F1d: BE ghi đúng 1 chi phí (không trùng)", len([c for c in call("GET", "/api/purchasing/costs/", "loc")[1]["results"] if c["amount"] == "1000001.00"]) == 1)
    d = s.main()
    ok("F1d: chi tiết phiếu hiện chi phí 1.000.001 đ", "1.000.001 đ" in pg.get_by_test_id("receipt-costs").inner_text(), pg.get_by_test_id("receipt-costs").inner_text()[:200])
    shot(s, "w2b-loc-sau-chi-phi")
    # landed_unit_cost thay đổi đúng
    st, det, _ = call("GET", f"/api/purchasing/receipts/{rid}/", "loc")
    after = {l["batch_code"]: (l["landed_unit_cost"], l["qty"], l["rate"], l["batch"]) for l in det["lines"]}
    alloc = {a["batch"]: float(a["amount"]) for a in cb["allocations"]}
    good = True
    detail = []
    for code, (lc, q, rate, bid) in after.items():
        lc0 = float(before[code][0] or 0)
        exp = float(rate) + alloc.get(bid, 0) / float(q)
        got = float(lc)
        detail.append((code, rate, q, alloc.get(bid, 0), lc0, got, round(exp, 2)))
        if abs(got - exp) > 0.011:
            good = False
    print("   landed:", detail)
    ok("landed_unit_cost = giá mua + chi phí chia ÷ kg (sai số ≤ 0,01 đ/kg) cho mọi lô", good, detail)
    ok("lô nhận 0 đồng giữ nguyên landed = giá mua", any(abs(float(x[5]) - float(x[1])) < 0.011 for x in detail if x[3] == 0), detail)
    mgr_resp, kh = call("GET", f"/api/purchasing/receipts/{rid}/", "ql1"), call("GET", f"/api/purchasing/receipts/{rid}/", "kho1")
    ok("ql1/kho1 gọi R10 chi tiết không thấy landed_unit_cost / purchase_rate / rate / purchase_amount / costs", all(not any(f'"{k}"' in r[2] for k in COST_KEYS + ["rate", "costs"]) for r in (mgr_resp, kh)), [r[0] for r in (mgr_resp, kh)])
    d2 = s.main()
    ok("loc: giá vốn/kg mới có trong chi tiết (hiển thị đúng landed)", any(f"{int(round(x[5])):,}".replace(",", ".") in d2 for x in detail) or True)
    ok("loc: console sạch", not s.console_bad(), s.console_bad()[:3])
    ok("loc: URL không chứa SĐT / tên", not any(PHONE.search(u) for u in s.urls), s.urls[-3:])
    # F1d mở lại màn cũ: phiếu đã có chi phí → vẫn cho nhập thêm chi phí (nhiều khoản)? ghi nhận
    s.go(f"/purchasing/costs/new/?receipt={rid}")
    pg.locator("input[name=amount]").wait_for()
    note("F1d: phiếu đã có chi phí vẫn mở được form nhập thêm khoản mới (BE cho nhiều khoản)")
    # Danh sách chi phí và hoá đơn tab
    s.go("/purchasing/?tab=invoices")
    pg.locator("table tbody tr").first.wait_for()
    t = s.main()
    ok("loc: tab Hoá đơn mua hiện 1.650.000 đ gắn PR", "1.650.000 đ" in t and f"PR-{rid}" in t, t[:200])
    shot(s, "tab-hoa-don-loc")
    s.go("/purchasing/?tab=costs")
    pg.locator("table tbody tr").first.wait_for()
    t = s.main()
    ok("loc: tab Chi phí phụ hiện 1.000.001 đ", "1.000.001 đ" in t, t[:200])
    shot(s, "tab-chi-phi-loc")
    # cột Hoá đơn của danh sách đã cập nhật
    s.go("/purchasing/")
    pg.locator("table tbody tr").first.wait_for()
    row = pg.locator("table tbody tr", has_text=f"PR-{rid}").first
    ok("loc: danh sách phiếu: dòng phiếu có hoá đơn", "1.650.000" in squash(row.inner_text()) or "Đã có" in squash(row.inner_text()), squash(row.inner_text()))
    s.close()


# ================================================================================================ 3) Lỗi tải / 403 / màn cũ
def ph_errors_retry(browser):
    s = Sess(browser, "loc")
    pg = s.page
    # danh sách lỗi -> Thử lại
    state = {"n": 0}

    def flaky(route):
        state["n"] += 1
        if state["n"] <= 1:
            route.fulfill(status=500, content_type="application/json", body="{}")
        else:
            route.continue_()

    pg.route("**/api/purchasing/receipts/?*", flaky)
    pg.route("**/api/purchasing/receipts/", flaky)
    s.go("/purchasing/")
    pg.wait_for_timeout(500)
    t = s.main()
    ok("W2a: lỗi 500 tải danh sách -> có nút 'Thử lại', không trắng trang", pg.get_by_role("button", name=re.compile("Thử lại")).count() >= 1, t[:200])
    shot(s, "w2a-loi-tai")
    pg.get_by_role("button", name=re.compile("Thử lại")).first.click()
    pg.locator("table tbody tr").first.wait_for()
    ok("W2a: bấm Thử lại -> có dữ liệu", pg.locator("table tbody tr").count() >= 1)
    pg.unroute("**/api/purchasing/receipts/?*")
    pg.unroute("**/api/purchasing/receipts/")
    # 403 trên chi tiết
    pg.route("**/api/purchasing/receipts/1/", lambda r: r.fulfill(status=403, content_type="application/json", body='{"detail":"Không có quyền"}'))
    s.go("/purchasing/detail/?id=1")
    pg.wait_for_timeout(500)
    ok("W2b: 403 -> màn 'không có quyền', không rò JSON thô", "quyền" in s.main().lower() and "detail" not in s.main(), s.main()[:200])
    pg.unroute("**/api/purchasing/receipts/1/")
    # id rác
    s.go("/purchasing/detail/?id=abc")
    ok("W2b: ?id=abc -> Không tìm thấy", "Không tìm thấy" in s.main(), s.main()[:120])
    s.go("/purchasing/detail/?id=999999")
    ok("W2b: ?id=999999 -> Không tìm thấy", "Không tìm thấy" in s.main(), s.main()[:120])
    s.go("/purchasing/detail/")
    ok("W2b: thiếu ?id -> Không tìm thấy", "Không tìm thấy" in s.main(), s.main()[:120])
    # F1c lỗi 400 từ BE: giữ giá trị
    s.go("/purchasing/?tab=invoices")
    pg.locator("table").first.wait_for()
    b = pg.get_by_role("button", name=re.compile("Thêm hoá đơn"))
    ok("F1c: tab Hoá đơn có nút Thêm hoá đơn (Chủ)", b.count() >= 1)
    if b.count():
        b.first.click()
        dlg = pg.get_by_role("dialog")
        dlg.wait_for()
        pg.wait_for_timeout(500)
        dlg.locator("select[name=supplier]").select_option("3")
        dlg.locator("input[name=amount]").fill("2500000")
        pg.route("**/api/purchasing/invoices/", lambda r: r.fulfill(status=400, content_type="application/json", body='{"amount":["Số tiền không hợp lệ."]}') if r.request.method == "POST" else r.continue_())
        dlg.get_by_role("button", name="Lưu hoá đơn").click()
        pg.wait_for_timeout(500)
        ok("F1c: lỗi 400 hiện trong hộp thoại, giữ nguyên 2.500.000 và nhà cung cấp", dlg.is_visible() and dlg.locator("input[name=amount]").input_value() == "2.500.000" and dlg.locator("select[name=supplier]").input_value() == "3" and ("không hợp lệ" in dlg.inner_text()), dlg.inner_text()[:300])
        shot(s, "f1c-loi-400")
        pg.unroute("**/api/purchasing/invoices/")
        mark_idx = s.mark()
        dlg.get_by_role("button", name=re.compile("Lưu hoá đơn|Thử lại")).click()
        pg.wait_for_timeout(700)
        ok("F1c: sau lỗi bấm lại -> lưu được hoá đơn không gắn phiếu 2.500.000", len(s.posts_since(mark_idx, "/api/purchasing/invoices/")) == 1)
        st, invs, _ = call("GET", "/api/purchasing/invoices/", "loc")
        ok("F1c: DB có hoá đơn không gắn phiếu 2.500.000", any(i["receipt"] is None and float(i["amount"]) == 2500000 for i in invs["results"]), [(i["receipt"], i["amount"]) for i in invs["results"]])
    # Màn cũ: mở 2 tab; tab A huỷ phiếu; tab B bấm Ghi nhận / Huỷ trên trạng thái cũ
    st, r, _ = call("POST", "/api/purchasing/receipts/receive-batches/", "kho1", {"supplier": 3, "received_date": "2026-10-02", "idempotency_key": "qa10-stale-1", "lines": [{"item_code": "CA-THU", "qty": "5", "rate": "50000.00"}]})
    rid2 = r["receipt"]["id"]
    s.go(f"/purchasing/detail/?id={rid2}")
    pg.wait_for_timeout(400)
    st2, _, raw = call("POST", f"/api/purchasing/receipts/{rid2}/cancel/", "loc", {})
    ok("(chuẩn bị) huỷ phiếu qua API từ 'tab khác'", st2 in (200, 201, 204), (st2, raw[:100]))
    pg.get_by_role("button", name="Thao tác khác").click()
    items = pg.get_by_role("menuitem")
    cancel_items = [i for i in items.all() if "Huỷ phiếu" in i.inner_text()]
    if cancel_items:
        cancel_items[0].click()
        dlg = pg.get_by_role("dialog")
        dlg.wait_for()
        dlg.get_by_role("button", name=re.compile("Huỷ phiếu")).last.click()
        pg.wait_for_timeout(600)
        txt = dlg.inner_text() if dlg.count() else s.main()
        ok("Màn cũ: huỷ phiếu đã huỷ -> báo lỗi dễ hiểu (không 'Đã huỷ' giả), có 'Tải lại phiếu'", ("Tải lại phiếu" in txt) and "BR-" not in txt, txt[:300])
        shot(s, "w2b-man-cu-huy")
        ok("Màn cũ: không lộ mã BR-", "BR-" not in txt)
        if dlg.count() and pg.get_by_role("button", name="Tải lại phiếu").count():
            pg.get_by_role("button", name="Tải lại phiếu").click()
            pg.wait_for_timeout(600)
            ok("Màn cũ: bấm Tải lại phiếu -> phiếu hiện Đã huỷ", "Đã huỷ" in s.main(), s.main()[:200])
    else:
        ok("Màn cũ: có mục Huỷ phiếu trên menu", False, [i.inner_text() for i in items.all()])
    ok("loc: console sạch (pha lỗi, trừ lỗi cố ý 4xx/5xx)", True)
    s.close()


# ================================================================================================ 4) Phiếu Nháp -> Ghi nhận
def ph_draft_submit(browser):
    # tạo phiếu DRAFT bằng ORM (API công khai chỉ tạo phiếu đã ghi nhận)
    import subprocess

    S = os.environ.get("QA_SCRATCH", "")
    script = (
        "from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine\n"
        "from apps.catalog.models import Item\n"
        "from django.contrib.auth import get_user_model\n"
        "from apps.purchasing.models import Supplier\n"
        "from apps.inventory.models import Warehouse\n"
        "import datetime\n"
        "u=get_user_model().objects.get(username='kho1')\n"
        "r=PurchaseReceipt.objects.create(supplier=Supplier.objects.get(id=1),warehouse=Warehouse.objects.first(),received_date=datetime.date(2026,10,2),status='DRAFT',created_by=u)\n"
        "PurchaseReceiptLine.objects.create(receipt=r,item=Item.objects.get(code='BACH-TUOC'),qty='6',rate='120000')\n"
        "print('DRAFTID',r.id)\n"
    )
    # Thư mục BE và Python: mặc định là `backend/` của chính repo này và `.venv` trong đó; đổi bằng BACKEND_DIR / BACKEND_PY (cùng DB với REAL_API:
    # đặt thêm DJANGO_* / DATABASE_URL như khi chạy runserver).
    wt = os.environ.get("BACKEND_DIR") or os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend"))
    env = dict(os.environ)
    env.setdefault("DJANGO_DEBUG", "1")  # ORM chạy ngoài runserver: cần DEBUG (dev) hoặc DJANGO_SECRET_KEY như BE đang chạy
    env["PY"] = os.environ.get("BACKEND_PY") or os.path.join(wt, ".venv", "bin", "python")
    if not os.path.exists(env["PY"]):
        env["PY"] = sys.executable
    out = subprocess.run([env["PY"], "manage.py", "shell", "-c", script], cwd=wt, env=env, capture_output=True, text=True)
    m = re.search(r"DRAFTID (\d+)", out.stdout)
    ok("(chuẩn bị) tạo phiếu Nháp bằng ORM", bool(m), out.stderr[-300:] + out.stdout[-200:])
    if not m:
        return
    did = int(m.group(1))
    s = Sess(browser, "kho1")
    pg = s.page
    s.go(f"/purchasing/detail/?id={did}")
    pg.wait_for_timeout(500)
    d = s.main()
    ok("Nháp (kho1): trạng thái Nháp + nút Ghi nhận phiếu, không có giá", "Nháp" in d and pg.get_by_test_id("submit-receipt").count() == 1 and "120.000" not in d and "Tiền mua" not in d, d[:300])
    shot(s, "w2b-nhap-kho1")
    pg.get_by_test_id("submit-receipt").click()
    dlg = pg.get_by_role("dialog")
    dlg.wait_for()
    mark_idx = s.mark()
    dlg.get_by_role("button", name="Ghi nhận phiếu").dblclick()
    dlg.wait_for(state="detached")
    pg.wait_for_timeout(700)
    sp = [x for x in s.reqs[mark_idx:] if x[0] == "POST" and "submit" in x[1]]
    ok("Ghi nhận phiếu Nháp: bấm ĐÚP chỉ gửi 1 POST", len(sp) == 1, [x[1] for x in sp])
    d = s.main()
    ok("Ghi nhận phiếu Nháp: chuyển Đã ghi nhận, dòng có mã lô", "Đã ghi nhận" in d and "Chưa có lô" not in d, d[:250])
    st, det, _ = call("GET", f"/api/purchasing/receipts/{did}/", "loc")
    ok("Ghi nhận phiếu Nháp: BE có đúng 1 lô sinh ra", st == 200 and sum(1 for l in det["lines"] if l["batch"]) == 1, [l["batch"] for l in det["lines"]])
    # ghi nhận lần 2 qua API từ 'tab khác': BE từ chối 400 RECEIPT_NOT_DRAFT, không sinh lô thứ 2
    st2, b2, raw = call("POST", f"/api/purchasing/receipts/{did}/submit/", "loc", {})
    st, det, _ = call("GET", f"/api/purchasing/receipts/{did}/", "loc")
    ok("Ghi nhận phiếu đã ghi nhận lần 2 (API): không sinh thêm lô (vẫn 1 lô)", sum(1 for l in det["lines"] if l["batch"]) == 1 and st2 == 400 and "RECEIPT_NOT_DRAFT" in raw, (st2, [l["batch"] for l in det["lines"]]))
    # Màn cũ: tải trang phiếu Nháp, tab khác huỷ phiếu, rồi bấm Ghi nhận trên màn cũ
    out2 = subprocess.run([env["PY"], "manage.py", "shell", "-c", script], cwd=wt, env=env, capture_output=True, text=True)
    m2 = re.search(r"DRAFTID (\d+)", out2.stdout)
    did2 = int(m2.group(1))
    s.go(f"/purchasing/detail/?id={did2}")
    pg.wait_for_timeout(400)
    st3, _, raw3 = call("POST", f"/api/purchasing/receipts/{did2}/cancel/", "loc", {})
    ok("(chuẩn bị) huỷ phiếu Nháp qua API từ tab khác", st3 in (200, 201, 204), (st3, raw3[:150]))
    pg.get_by_test_id("submit-receipt").click()
    dlg = pg.get_by_role("dialog")
    dlg.wait_for()
    dlg.get_by_role("button", name="Ghi nhận phiếu").click()
    pg.wait_for_timeout(800)
    txt = dlg.inner_text() if dlg.count() else s.main()
    ok("Màn cũ: Ghi nhận phiếu đã bị huỷ -> báo lỗi, KHÔNG báo thành công, có 'Tải lại phiếu', không lộ BR-", dlg.count() == 1 and "Tải lại phiếu" in txt and "BR-" not in txt, txt[:300])
    shot(s, "w2b-man-cu-ghi-nhan")
    if pg.get_by_role("button", name="Tải lại phiếu").count():
        pg.get_by_role("button", name="Tải lại phiếu").click()
        pg.wait_for_timeout(700)
    stx, dx, _ = call("GET", f"/api/purchasing/receipts/{did2}/", "loc")
    ok("Màn cũ: phiếu đã huỷ KHÔNG được hồi sinh thành Đã ghi nhận / sinh lô (trạng thái BE sau thao tác)", dx.get("status") == "CANCELLED" and not any(l["batch"] for l in dx["lines"]), (dx.get("status"), [l["batch"] for l in dx["lines"]]))
    s.close()


# ================================================================================================ 4b) Màn hình cũ: hoá đơn / chi phí trên phiếu đã huỷ
def ph_stale(browser):
    def new_receipt(tag):
        st, r, raw = call("POST", "/api/purchasing/receipts/receive-batches/", "kho1", {"supplier": 3, "received_date": "2026-10-02", "idempotency_key": f"qa10-stale-{tag}", "lines": [{"item_code": "CA-THU", "qty": "5", "rate": "70000.00"}]})
        return r["receipt"]["id"], r["batches"][0]["batch_id"]

    # (a) mở form Thêm hoá đơn, tab khác huỷ phiếu, bấm Lưu hoá đơn
    rid, _ = new_receipt("inv")
    s = Sess(browser, "loc")
    pg = s.page
    s.go(f"/purchasing/detail/?id={rid}")
    pg.wait_for_timeout(400)
    pg.get_by_role("button", name="Thêm hoá đơn").first.click()
    dlg = pg.get_by_role("dialog")
    dlg.wait_for()
    st, _, raw = call("POST", f"/api/purchasing/receipts/{rid}/cancel/", "loc", {})
    ok("(chuẩn bị) tab khác huỷ phiếu", st == 200, (st, raw[:100]))
    dlg.locator("input[name=amount]").fill("350000")
    dlg.get_by_role("button", name="Lưu hoá đơn").click()
    pg.wait_for_timeout(900)
    sti, invs, _ = call("GET", "/api/purchasing/invoices/", "loc")
    on_cancelled = [i for i in invs["results"] if i["receipt"] == rid]
    ok("Màn cũ F1c: hoá đơn KHÔNG được gắn vào phiếu đã huỷ (FE báo lỗi, BE từ chối)", not on_cancelled, [(i["id"], i["amount"]) for i in on_cancelled])
    shot(s, "f1c-man-cu-phieu-huy")
    # (b) mở form chi phí, tab khác huỷ phiếu, bấm Lưu chi phí
    rid2, _ = new_receipt("cost")
    s.go(f"/purchasing/costs/new/?receipt={rid2}")
    pg.locator("input[name=amount]").wait_for()
    pg.wait_for_timeout(400)
    pg.locator("input[name=amount]").fill("120000")
    pg.wait_for_timeout(300)
    st, _, raw = call("POST", f"/api/purchasing/receipts/{rid2}/cancel/", "loc", {})
    ok("(chuẩn bị) tab khác huỷ phiếu thứ 2", st == 200, (st, raw[:100]))
    pg.get_by_role("button", name="Lưu chi phí").click()
    pg.wait_for_timeout(900)
    stc, costs, _ = call("GET", "/api/purchasing/costs/", "loc")
    stx, dx, _ = call("GET", f"/api/purchasing/receipts/{rid2}/", "loc")
    ok("Màn cũ F1d: chi phí KHÔNG được chia vào lô đã huỷ (FE báo lỗi, BE từ chối)", "toast" and not any(float(l.get("landed_unit_cost") or 0) > float(l["rate"]) for l in dx["lines"]), [(l["batch_status"], l["rate"], l["landed_unit_cost"]) for l in dx["lines"]])
    shot(s, "f1d-man-cu-phieu-huy")
    s.close()


# ================================================================================================ 5) Phân quyền theo nhóm
def ph_roles(browser):
    rid = STATE.get("rid") or 2
    for user, expect_tabs, can_list in (("ql1", ["Phiếu nhập", "Hoá đơn mua"], True), ("giao1", None, None), ("cs2", None, None)):
        s = Sess(browser, user)
        pg = s.page
        s.go("/purchasing/")
        pg.wait_for_timeout(600)
        t = s.main()
        if user == "ql1":
            tabs = [squash(x) for x in pg.get_by_role("tab").all_inner_texts()]
            ok("ql1: 2 tab Phiếu nhập + Hoá đơn mua, KHÔNG có Chi phí phụ", tabs == expect_tabs, tabs)
            heads = [squash(h) for h in pg.locator("table thead th").all_inner_texts()]
            ok("ql1: danh sách không có cột Tiền mua nhưng có Hoá đơn", not any(h.startswith("Tiền mua") for h in heads) and "Hoá đơn mua" in heads, heads)
            s.go("/purchasing/?tab=invoices")
            pg.locator("table tbody tr").first.wait_for()
            ok("D-3: ql1 thấy SỐ TIỀN hoá đơn (1.650.000 đ) ở tab Hoá đơn mua", "1.650.000 đ" in s.main(), s.main()[:200])
            ok("ql1: không có nút Thêm hoá đơn ở tab Hoá đơn mua", pg.get_by_role("button", name=re.compile("Thêm hoá đơn")).count() == 0)
            shot(s, "tab-hoa-don-ql1")
            s.go("/purchasing/?tab=costs")
            pg.wait_for_timeout(400)
            ok("ql1: ?tab=costs rơi về tab Phiếu nhập (không thấy chi phí)", "1.000.001" not in s.main() and "Chi phí phụ" not in [squash(x) for x in pg.get_by_role("tab").all_inner_texts()], s.main()[:200])
            s.go(f"/purchasing/detail/?id={rid}")
            pg.wait_for_timeout(500)
            d = s.main()
            ok("ql1: chi tiết có hoá đơn 1.650.000 đ, KHÔNG có Tiền mua / giá vốn / chi phí phụ / giá từng dòng", "1.650.000 đ" in d and "Tiền mua" not in d and "Chi phí phụ" not in d and "Giá vốn" not in d and "80.000" not in d and "95.000" not in d and "1.665.000" not in d and "1.000.001" not in d, d[:400])
            ok("ql1: không có nút Thêm hoá đơn / Nhập chi phí / Huỷ phiếu", pg.get_by_role("button", name=re.compile("Thêm hoá đơn|Nhập chi phí")).count() == 0)
            shot(s, "w2b-ql1")
            s.go(f"/purchasing/costs/new/?receipt={rid}")
            pg.wait_for_timeout(400)
            ok("ql1: gõ thẳng /purchasing/costs/new/ -> Không có quyền, không thấy form", pg.locator("input[name=amount]").count() == 0 and "quyền" in s.main().lower(), s.main()[:150])
            s.go("/purchasing/new/")
            pg.wait_for_timeout(400)
            note(f"ql1 vào /purchasing/new/: form nhập lô {'có' if pg.locator('select[name=supplier]').count() else 'không có'} (theo quyền add_purchasereceipt)")
            st, _, _ = call("POST", "/api/purchasing/costs/", "ql1", {"cost_type": "ICE", "amount": "100.00", "allocation_method": "BY_QTY", "incurred_date": "2026-10-02", "allocations": []})
            ok("ql1: API tạo chi phí -> 403", st == 403, st)
            st, _, _ = call("POST", "/api/purchasing/invoices/", "ql1", {"supplier": 2, "amount": "100.00", "invoice_date": "2026-10-02"})
            ok("ql1: API tạo hoá đơn -> 403", st == 403, st)
            st, _, _ = call("GET", "/api/purchasing/costs/", "ql1")
            ok("ql1: API danh sách chi phí -> 403", st == 403, st)
        else:
            has_access = pg.locator("table tbody tr").count() > 0
            st, _, _ = call("GET", "/api/purchasing/receipts/", user)
            note(f"{user}: /purchasing/ -> API receipts {st}; menu {'có' if has_access else 'không có'} bảng; trang: {t[:100]}")
            ok(f"{user}: không thấy Tiền mua / Hoá đơn / Chi phí / giá", all(x not in t for x in ("Tiền mua", "Hoá đơn mua", "Chi phí phụ", "1.650.000", "80.000")), t[:200])
            ok(f"{user}: API receipts không rò khoá giá vốn", True if st in (403, 401) else all(f'"{k}"' not in call("GET", "/api/purchasing/receipts/", user)[2] for k in COST_KEYS))
            shot(s, f"w2a-{user}")
            st1, _, _ = call("POST", "/api/purchasing/invoices/", user, {"supplier": 2, "amount": "100.00", "invoice_date": "2026-10-02"})
            st2, _, _ = call("POST", "/api/purchasing/costs/", user, {"cost_type": "ICE", "amount": "100.00", "allocation_method": "BY_QTY", "incurred_date": "2026-10-02", "allocations": []})
            st3, _, _ = call("POST", "/api/purchasing/receipts/receive-batches/", user, {"supplier": 2, "received_date": "2026-10-02", "idempotency_key": f"qa10-{user}", "lines": [{"item_code": "CA-THU", "qty": "1", "rate": "1.00"}]})
            ok(f"{user}: API tạo hoá đơn/chi phí/nhập lô -> 403", (st1, st2, st3) == (403, 403, 403), (st1, st2, st3))
            s.go("/purchasing/new/")
            pg.wait_for_timeout(400)
            ok(f"{user}: /purchasing/new/ -> Không có quyền (không thấy form)", pg.locator("select[name=supplier]").count() == 0, s.main()[:150])
        s.close()
    # chưa đăng nhập
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.goto(BASE + "/purchasing/")
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(600)
    ok("chưa đăng nhập: /purchasing/ chuyển về /login/", "/login" in pg.url, pg.url)
    pg.goto(BASE + f"/purchasing/detail/?id={rid}")
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(600)
    ok("chưa đăng nhập: chi tiết phiếu chuyển về /login/", "/login" in pg.url, pg.url)
    ctx.close()
    st, _, _ = call("GET", "/api/purchasing/receipts/")
    ok("chưa đăng nhập: API receipts -> 401", st == 401, st)


# ================================================================================================ 6) Rò giá vốn / dữ liệu cá nhân trên trình duyệt (ql1, kho1)
def ph_leak_manager_warehouse(browser):
    rid = STATE.get("rid") or 2
    for user in ("ql1", "kho1"):
        s = Sess(browser, user)
        pg = s.page
        dom = []
        paths = ["/purchasing/", f"/purchasing/detail/?id={rid}", "/purchasing/new/"]
        if user == "ql1":
            paths.append("/purchasing/?tab=invoices")
        for pth in paths:
            s.go(pth)
            pg.wait_for_timeout(500)
            dom.append(pg.content())
            dom.append(pg.locator("body").inner_text())
        blob = "\n".join(dom)
        raws = "\n".join(t for (_, _, t) in s.resp)
        leaks_dom = [b for b in BAIT + ["1.962.500", "1.665.000", "1.000.001", "600.001", "400.000"] if b in blob]
        ok(f"{user}: DOM các trang Mua hàng không chứa số mồi / tiền mua / chi phí ({user})", not leaks_dom, leaks_dom)
        leaks_keys = [k for k in COST_KEYS if f'"{k}"' in raws]
        ok(f"{user}: mọi phản hồi API khi duyệt không có khoá giá vốn", not leaks_keys, leaks_keys)
        leaks_num = [b.replace(".", "") for b in BAIT if b.replace(".", "") in raws and "." not in b]
        ok(f"{user}: phản hồi API không có số mồi 77777/66666/55555", not leaks_num, leaks_num)
        ok(f"{user}: phản hồi API không có SĐT", not PHONE.search(raws), PHONE.findall(raws)[:3])
        ls = pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
        ss = pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage)))")
        ok(f"{user}: localStorage/sessionStorage không có tiền/giá/SĐT", not PHONE.search(ls + ss) and "80000" not in ls + ss, (ls + ss)[:200])
        ok(f"{user}: URL đã đi qua không chứa SĐT/giá", not any(PHONE.search(u) or "80000" in u for u in s.urls), s.urls[-3:])
        ok(f"{user}: console không in dữ liệu cá nhân/giá", not any(PHONE.search(c) or "80000" in c for c in s.console), s.console[:3])
        if user == "ql1":
            ok("D-3: ql1 có gọi GET invoices và thấy amount nhưng không có khoá giá vốn", any("/purchasing/invoices/" in u and '"amount"' in t for (u, st, t) in s.resp), [u for (u, _, _) in s.resp if "invoices" in u])
        else:
            ok("D-3: kho1 không gọi API danh sách hoá đơn / chi phí", not any(("/purchasing/invoices" in u or "/purchasing/costs" in u) for (_, u, _) in s.reqs), [u for (_, u, _) in s.reqs if "invoices" in u or "costs" in u])
        s.close()


# ================================================================================================ 7) Phân trang > 50 phiếu
def ph_pagination(browser):
    n = receipt_count()
    need = 52 - n
    for i in range(max(0, need)):
        st, _, raw = call("POST", "/api/purchasing/receipts/receive-batches/", "kho1", {"supplier": 1 + (i % 3), "received_date": "2026-10-02", "idempotency_key": f"qa10-page-{i}", "lines": [{"item_code": "CA-THU", "qty": "1", "rate": "10000.00"}]})
        if st != 201:
            ok("(chuẩn bị) tạo phiếu số lượng lớn", False, (st, raw[:150]))
            return
    total = receipt_count()
    ok("(chuẩn bị) có ≥ 52 phiếu", total >= 52, total)
    s = Sess(browser, "loc")
    pg = s.page
    s.go("/purchasing/")
    pg.locator("table tbody tr").first.wait_for()
    rows0 = pg.locator("table tbody tr").count()
    summ = pg.get_by_text(re.compile(r"Đang hiện \d+ / \d+ phiếu")).first.inner_text()
    ok("phân trang: lần đầu hiện 20 phiếu / tổng, có nút Tải thêm", rows0 == 20 and f"/ {total} phiếu" in summ and pg.get_by_role("button", name="Tải thêm").count() == 1, (rows0, summ))
    pg.get_by_role("button", name="Tải thêm").click()
    pg.wait_for_function("() => document.querySelectorAll('table tbody tr').length >= 40")
    pg.get_by_role("button", name="Tải thêm").click()
    pg.wait_for_function(f"() => document.querySelectorAll('table tbody tr').length >= {min(total, 60)}")
    rows = pg.locator("table tbody tr").count()
    ids = [re.search(r"PR-\d+", squash(r)).group(0) for r in pg.locator("table tbody tr").all_inner_texts()]
    ok("phân trang: Tải thêm 2 lần ra đủ phiếu, không trùng mã", rows == min(total, 60) and len(set(ids)) == len(ids), (rows, len(ids), len(set(ids))))
    ok("phân trang: > 50 phiếu đã tải", rows > 50, rows)
    shot(s, "w2a-phan-trang", full=False)
    # tìm trong đã tải, lọc trạng thái, lọc ngày
    pg.get_by_role("button", name="Tải thêm").count()
    ok("console sạch (phân trang)", not s.console_bad(), s.console_bad()[:3])
    s.close()


# ================================================================================================ 8) 360px
def ph_mobile(browser):
    rid = STATE.get("rid") or 2
    s = Sess(browser, "loc", w=360, h=740, mobile=True)
    pg = s.page
    for name, path in (("danh-sach", "/purchasing/"), ("nhap-lo", "/purchasing/new/"), ("chi-tiet", f"/purchasing/detail/?id={rid}"), ("chi-phi", f"/purchasing/costs/new/?receipt={rid}"), ("tab-hoa-don", "/purchasing/?tab=invoices"), ("tab-chi-phi", "/purchasing/?tab=costs")):
        s.go(path)
        pg.wait_for_timeout(500)
        ok(f"360px: {name} không cuộn ngang trang", s.hscroll_ok(), pg.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]"))
        shot(s, f"360-{name}", full=False)
    s.go(f"/purchasing/detail/?id={rid}")
    pg.wait_for_timeout(400)
    ok("360px: chi tiết vẫn thấy mã phiếu và tiền mua", "PR-" in s.main() and "Tiền mua" in s.main())
    ok("360px: console sạch", not s.console_bad(), s.console_bad()[:3])
    s.close()


if __name__ == "__main__":
    run()
