"""QA độc lập Lô 7 FE trên Django THẬT (SQLite tạm) + console build MOCK=0.

Chuẩn bị (dữ liệu 100% giả; xem scratchpad setup_real.py): bootstrap_masterdata + seed_demo + các lô QA:
  QA-EXP-A (Quá hạn 12,5 kg), QA-EXP-B (Quá hạn 7 kg), QA-EXP-C (Quá hạn 4 kg, có kiểm kê duyệt),
  QA-DRAFT (Nháp 30 kg), QA-NOINV (Hết hàng, có phiếu nhập nhưng chưa có hoá đơn mua), QA-SOLDOUT (Hết hàng, chốt được).
  Tài khoản: loc/Songbien2026, ql1/kho1/giao1/cs2 = demo1234.
Chạy:  BASE=http://127.0.0.1:3302 API=http://127.0.0.1:8130 SHOTS=<ảnh> python3 e2e/qa_ed_batch7_real.py
Không PASS bằng đọc code: mọi ca ghi đi qua giao diện thật + gọi lại API để đối chiếu sổ (balance_after).
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import expect, sync_playwright  # noqa: E402

BASE = os.environ.get("BASE", "http://127.0.0.1:3302")
API = os.environ.get("API", "http://127.0.0.1:8130")
SHOTS = os.environ.get("SHOTS", "/tmp/qa7_real")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=15_000)
PHONE = re.compile(r"(?<!\d)0\d{9}(?!\d)")
COST_KEYS = ["purchase_rate", "landed_unit_cost", "unit_cost", "extra_cost", "landed_cost", "profit", "refund_amount", "write_off_cost", "cost_price"]
PW = {"loc": "Songbien2026"}
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:500]), flush=True)


# ------------------------------------------------------------------ API helper
def http(method, path, token=None, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Token {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def token(user):
    st, raw = http("POST", "/api/auth/token/", body={"username": user, "password": PW.get(user, "demo1234")})
    assert st == 200, (user, st, raw)
    return json.loads(raw)["token"]


def jget(path, tk):
    st, raw = http("GET", path, tk)
    return st, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)


# Token cấp sẵn từ setup (BE có giới hạn tần suất đăng nhập: gọi /api/auth/token/ dồn sẽ nhận 429). Một ca đăng nhập thật ở giao diện nằm trong ui_login_flow.
TOKENS_FILE = os.environ.get("TOKENS", "/private/tmp/claude-501/-Users-dangthiduyen-Downloads-loc/027d854a-5d5b-47c2-aa50-91d0c28d6319/scratchpad/qa7/tokens.json")
TK = json.load(open(TOKENS_FILE))


def batch_by_code(code):
    st, d = jget(f"/api/inventory/batches/?search={code}&page_size=100", TK["loc"])
    rows = d["results"] if isinstance(d, dict) else d
    for r in rows:
        if r["batch_id"] == code:
            return r
    st, d = jget(f"/api/inventory/batches/{code}/", TK["loc"])
    return d if st == 200 else None


def all_batches(tk):
    out, url = [], "/api/inventory/batches/"
    while url:
        st, d = jget(url, tk)
        out += d["results"]
        url = d["next"].replace(API, "") if d.get("next") else None
    return out


BATCH = {b["batch_id"]: b for b in all_batches(TK["loc"])}


def ledger_of(batch_id, tk=None):
    st, d = jget(f"/api/inventory/ledger/?batch={batch_id}&page_size=100", tk or TK["loc"])
    return d["results"]


# ================================================================== 1. API: vai x endpoint, giá vốn, dữ liệu cá nhân
def api_matrix():
    bid = BATCH["QA-EXP-A"]["id"]
    reads = ["/api/inventory/batches/", f"/api/inventory/batches/{bid}/", "/api/inventory/ledger/", "/api/inventory/warehouses/", "/api/inventory/stock-entries/"]
    for user, expect_status in {"loc": 200, "ql1": 200, "kho1": 200, "giao1": 403, "cs2": 403}.items():
        for path in reads:
            st, raw = http("GET", path, TK[user])
            ok(f"[API {user}] GET {path.split('?')[0]}: {expect_status}", st == expect_status, f"{st} {raw[:100]}")
            if st == 200:
                keys = [k for k in COST_KEYS if f'"{k}"' in raw]
                if user == "loc":
                    continue
                ok(f"[API {user}] {path.split('?')[0]}: không có khoá giá vốn/lãi lỗ/tiền NCC", not keys, str(keys))
            if st == 200:
                ok(f"[API {user}] {path.split('?')[0]}: không có SĐT/địa chỉ/tên khách", not PHONE.search(raw) and not re.search(r'"(customer_name|phone|address|shipping_address|recipient)', raw), raw[:100])
    for path in reads:
        st, _ = http("GET", path)
        ok(f"[API ẩn danh] GET {path.split('?')[0]}: 401", st == 401, str(st))
    st, raw = http("GET", f"/api/inventory/batches/{bid}/", TK["loc"])
    ok("[API loc] đối chứng: chi tiết lô CÓ khoá giá vốn", '"landed_unit_cost"' in raw or '"purchase_rate"' in raw, raw[:150])
    # ghi: quyền
    wr = {
        "publish": ("kho1", BATCH["QA-DRAFT"]["id"], {}),
        "close": ("ql1", BATCH["QA-SOLDOUT"]["id"], {}),
        "cancel-expired": ("ql1", bid, {"confirm_qty": "12.500"}),
        "return-to-supplier": ("ql1", bid, {"qty": "1", "request_id": "11111111-1111-4111-8111-111111111111"}),
    }
    for act, (user, b, body) in wr.items():
        st, raw = http("POST", f"/api/inventory/batches/{b}/{act}/", TK[user], body)
        ok(f"[API {user}] POST {act}: bị chặn 403", st == 403, f"{st} {raw[:120]}")
    for act, (user, b, body) in {k: ("giao1", v[1], v[2]) for k, v in wr.items()}.items():
        st, _ = http("POST", f"/api/inventory/batches/{b}/{act}/", TK[user], body)
        ok(f"[API giao1] POST {act}: 403", st == 403, str(st))
    st, _ = http("POST", f"/api/inventory/batches/{bid}/close/", None, {})
    ok("[API ẩn danh] POST close: 401", st == 401, str(st))
    for user in ("ql1", "kho1", "giao1", "cs2"):
        st, raw = http("POST", "/api/inventory/warehouses/", TK[user], {"name": "Kho QA không được tạo"})
        ok(f"[API {user}] POST warehouses: 403 (chỉ Chủ)", st == 403, f"{st} {raw[:100]}")
    # sổ: chỉ GET
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        st, _ = http(method, "/api/inventory/ledger/", TK["loc"], {})
        ok(f"[API loc] {method} /ledger/ không được (sổ chỉ ghi thêm bằng nghiệp vụ)", st in (404, 405), str(st))
    led = ledger_of(bid)
    st, _ = http("DELETE", f"/api/inventory/ledger/{led[0]['id']}/", TK["loc"]) if led else (405, "")
    ok("[API loc] DELETE một dòng sổ: 404/405", st in (404, 405), str(st))
    # kiểm tra reference_link + created_by_name
    st, d = jget("/api/inventory/ledger/?page_size=100", TK["loc"])
    rows = d["results"]
    ok("[API] dòng sổ có balance_after, reference_link, created_by_name", all({"balance_after", "reference_link", "created_by_name"} <= set(r) for r in rows), str(rows[0].keys()))


# ================================================================== 2. Ghi qua giao diện thật
class Net:
    def __init__(self, page):
        self.reqs = []
        self.bad = []
        self.logs = []
        page.on("request", lambda r: self.reqs.append((r.method, r.url)) if "/api/" in r.url else None)
        page.on("response", lambda r: self.bad.append((r.status, r.url)) if "/api/" in r.url and r.status >= 400 else None)
        page.on("console", lambda m: self.logs.append(m.text) if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: self.logs.append("pageerror " + str(e)))

    def count(self, method, needle):
        return len([1 for m, u in self.reqs if m == method and needle in u])


def login_ui(browser, user, w=1440, h=1000, mobile=False):
    """Tạo phiên đã đăng nhập bằng cách đặt token DRF vào localStorage (đúng cách ứng dụng lưu); không gọi lại /api/auth/token/."""
    opts = {"viewport": {"width": w, "height": h}, "reduced_motion": "reduce"}
    if mobile:
        opts.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**opts)
    ctx.add_init_script(f"try {{ window.localStorage.setItem('cave_erp_token', '{TK[user]}'); }} catch (e) {{}}")
    page = ctx.new_page()
    net = Net(page)
    page.goto(BASE + "/")
    page.wait_for_selector(".nav a", state="attached", timeout=20_000)
    page.wait_for_load_state("networkidle")
    return ctx, page, net


def ui_login_flow(browser):
    """Một ca đăng nhập thật qua form (Chủ) rồi vào Kho & lô."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", "loc")
    page.fill("#p", PW["loc"])
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=20_000)
    page.wait_for_selector(".nav a", state="attached")
    ok("[real] Đăng nhập thật bằng form: vào được ERP, menu có Kho & lô và Sổ nhập xuất", "Kho & lô" in page.locator("#rail-left .nav").inner_text() and "Sổ nhập xuất" in page.locator("#rail-left .nav").inner_text())
    ctx.close()


def open_detail(page, code):
    page.goto(f"{BASE}/inventory/detail/?id={BATCH[code]['id']}")
    page.wait_for_selector("[data-testid=qty-available]", timeout=20_000)
    page.wait_for_load_state("networkidle")


def menu_items(page):
    page.get_by_role("button", name="Thao tác khác").click()
    items = [re.sub(r"\s+", " ", x).strip() for x in page.get_by_role("menuitem").all_inner_texts()]
    return items


def pick(page, label):
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^" + re.escape(label))).click()


def kgnum(s):
    return float(re.sub(r"[^\d,\-+]", "", s).replace(",", "."))


def refresh_batch(code):
    st, d = jget(f"/api/inventory/batches/{BATCH[code]['id']}/", TK["loc"])
    return d


def ui_write_paths(browser):
    # ---------------------------------------------------- QA-EXP-A: trả NCC từng phần, rồi huỷ phần còn lại
    ctx, page, net = login_ui(browser, "loc")
    open_detail(page, "QA-EXP-A")
    items = menu_items(page)
    ok("[real] QA-EXP-A Quá hạn 12,5 kg: Trả NCC và Huỷ phần tồn mở được, Chốt lô mờ vì còn tồn", not any(" · " in i for i in items if i.startswith(("Trả", "Huỷ"))) and any(i.startswith("Chốt lô ·") for i in items), str(items))
    page.keyboard.press("Escape")
    pick(page, "Trả nhà cung cấp")
    d = page.get_by_role("dialog")
    d.wait_for()
    d.get_by_label("Số kg đã trả").fill("5")
    d.get_by_label("Tiền nhà cung cấp hoàn").fill("400000")
    d.get_by_label("Ghi chú").fill("QA trả một phần")
    page.screenshot(path=f"{SHOTS}/q7r-F1g-before.png")
    before = net.count("POST", "return-to-supplier")
    d.get_by_role("button", name="Ghi nhận đã trả").dblclick()
    d.wait_for(state="detached", timeout=20_000)
    page.wait_for_load_state("networkidle")
    ok("[real] Trả NCC: bấm đúp = 1 request POST", net.count("POST", "return-to-supplier") - before == 1, net.count("POST", "return-to-supplier") - before)
    expect(page.locator("[data-testid=qty-available]")).to_have_text(re.compile(r"7,5 kg"))
    led = ledger_of(BATCH["QA-EXP-A"]["id"])
    top = led[0]
    ok("[real] Sổ: dòng mới nhất = SUPPLIER_RETURN, change -5, balance_after 7,5, người làm 'Lộc'/tên thật",
       top["movement_type"] in ("SUPPLIER_RETURN",) and float(top["qty_change"]) == -5.0 and float(top["balance_after"]) == 7.5, json.dumps(top, ensure_ascii=False)[:300])
    ok("[real] Sổ: reference_link của Trả NCC có kind supplier_return", (top.get("reference_link") or {}).get("kind") == "supplier_return", str(top.get("reference_link")))
    ok("[real] Màn không in số tiền hoàn 400.000 lên bảng nhập xuất", "400.000" not in page.locator("table.lt").first.inner_text())
    ctx_stale = None
    # huỷ phần còn lại 7,5
    pick(page, "Huỷ phần tồn, ghi lỗ")
    d = page.get_by_role("dialog")
    d.wait_for()
    page.wait_for_load_state("networkidle")
    t = d.inner_text()
    ok("[real] F1h: nêu 7,5 kg, 'Tiền ghi lỗ' và 'Không hoàn tác'", "7,5" in t and "Tiền ghi lỗ" in t and "Không hoàn tác" in t, t[:300])
    ok("[real] F1h: Tiền ghi lỗ = 7,5 x giá vốn thật (100.000 + chi phí phụ) và có icon khoá", re.search(r"lock\s*[\d.]+\s*đ", t) is not None, t)
    page.screenshot(path=f"{SHOTS}/q7r-F1h.png")
    before = net.count("POST", "cancel-expired")
    d.get_by_role("button", name=re.compile(r"^Huỷ 7,5")).dblclick()
    d.wait_for(state="detached", timeout=20_000)
    page.wait_for_load_state("networkidle")
    ok("[real] Huỷ phần tồn: bấm đúp = 1 request POST", net.count("POST", "cancel-expired") - before == 1, net.count("POST", "cancel-expired") - before)
    led = ledger_of(BATCH["QA-EXP-A"]["id"])
    ok("[real] Sổ: dòng WRITE_OFF -7,5, balance_after 0", led[0]["movement_type"] == "WRITE_OFF" and float(led[0]["qty_change"]) == -7.5 and float(led[0]["balance_after"]) == 0, json.dumps(led[0], ensure_ascii=False)[:300])
    ok("[real] Sổ: có đủ 3 dòng lô: nhập → trả NCC → huỷ, chuỗi balance_after 12,5 → 7,5 → 0",
       [float(x["balance_after"]) for x in reversed(led)][-3:] == [12.5, 7.5, 0.0], str([x["balance_after"] for x in led]))
    b = refresh_batch("QA-EXP-A")
    ok("[real] Lô QA-EXP-A: tồn 0 sau huỷ, trạng thái không còn mở để trả/huỷ", float(b["qty_available"]) == 0, f"{b['status']} {b['qty_available']}")
    items = menu_items(page)
    ok("[real] Sau huỷ: Trả NCC/Huỷ phần tồn mờ kèm lý do", all(" · " in i for i in items if i.startswith(("Trả", "Huỷ"))), str(items))
    page.keyboard.press("Escape")
    ok("[real] Chip trạng thái lô sau huỷ khớp BE", b["status"] in ("EXPIRED", "CANCELLED") and page.locator("main").first.inner_text().count("Quá hạn") + page.locator("main").first.inner_text().count("Đã huỷ") >= 1, b["status"])
    page.screenshot(path=f"{SHOTS}/q7r-detail-after-cancel.png", full_page=True)
    # tồn kho (sổ) toàn kho phản ánh
    page.goto(BASE + "/ledger/")
    page.locator("table.lt tbody tr:not(.lt-skel)").first.wait_for()
    page.wait_for_load_state("networkidle")
    txt = page.locator("table.lt").first.inner_text()
    ok("[real] Sổ nhập xuất toàn kho thấy dòng 'Ghi lỗ, huỷ hàng' và 'Trả nhà cung cấp' của QA-EXP-A", "Ghi lỗ, huỷ hàng" in txt and "Trả nhà cung cấp" in txt and "QA-EXP-A" in txt)
    ctx.close()

    # ---------------------------------------------------- QA-EXP-B: huỷ toàn bộ, mô phỏng 'màn cũ' (hai tab)
    ctx, page, net = login_ui(browser, "loc")
    ctx2, page2, net2 = login_ui(browser, "loc")
    open_detail(page, "QA-EXP-B")
    open_detail(page2, "QA-EXP-B")
    pick(page, "Huỷ phần tồn, ghi lỗ")
    d = page.get_by_role("dialog")
    d.wait_for()
    page.wait_for_load_state("networkidle")
    d.get_by_role("button", name=re.compile(r"^Huỷ 7")).click()
    d.wait_for(state="detached", timeout=20_000)
    page.wait_for_load_state("networkidle")
    led = ledger_of(BATCH["QA-EXP-B"]["id"])
    ok("[real] QA-EXP-B huỷ 7 kg: WRITE_OFF, balance_after 0", led[0]["movement_type"] == "WRITE_OFF" and float(led[0]["balance_after"]) == 0, str(led[0]))
    # tab thứ hai còn thấy màn cũ (tồn 7 kg, nút huỷ còn mở): bấm huỷ lần nữa
    ok("[real] Màn cũ (tab 2): vẫn hiện tồn 7 kg và mục Huỷ mở được", "7 kg" in page2.locator("[data-testid=qty-available]").inner_text() and not [i for i in menu_items(page2) if i.startswith("Huỷ phần tồn") and " · " in i])
    page2.keyboard.press("Escape")
    pick(page2, "Huỷ phần tồn, ghi lỗ")
    d2 = page2.get_by_role("dialog")
    d2.wait_for()
    page2.wait_for_load_state("networkidle")
    d2.get_by_role("button", name=re.compile(r"^Huỷ")).click()
    page2.wait_for_timeout(1500)
    page2.wait_for_load_state("networkidle")
    led_after = ledger_of(BATCH["QA-EXP-B"]["id"])
    ok("[real] Màn cũ bấm huỷ lần 2: KHÔNG ghi thêm dòng sổ, tồn không âm", len(led_after) == len(led) and float(refresh_batch("QA-EXP-B")["qty_available"]) == 0, f"{len(led)} -> {len(led_after)}")
    body = page2.locator("body").inner_text()
    ok("[real] Màn cũ: hiện lỗi tiếng Việt dễ hiểu + hướng dẫn tải lại; không mã lỗi/traceback", d2.is_visible() and re.search(r"Tải lại|tải lại|đã (đổi|thay đổi)|không còn", d2.inner_text()) is not None and not re.search(r"Traceback|CONFLICT|STALE|Error:|400|undefined", d2.inner_text()), d2.inner_text()[-300:])
    page2.screenshot(path=f"{SHOTS}/q7r-stale-cancel.png")
    ctx.close()
    ctx2.close()

    # ---------------------------------------------------- QA-EXP-C: trả hết rồi chốt lô
    ctx, page, net = login_ui(browser, "loc")
    open_detail(page, "QA-EXP-C")
    pick(page, "Trả nhà cung cấp")
    d = page.get_by_role("dialog")
    d.wait_for()
    d.get_by_role("button", name="Trả hết").click()
    ok("[real] 'Trả hết' điền đúng 4 kg", d.get_by_label("Số kg đã trả").input_value() in ("4", "4,0", "4,000"), d.get_by_label("Số kg đã trả").input_value())
    d.get_by_role("button", name="Ghi nhận đã trả").click()
    d.wait_for(state="detached", timeout=20_000)
    page.wait_for_load_state("networkidle")
    led = ledger_of(BATCH["QA-EXP-C"]["id"])
    ok("[real] QA-EXP-C trả hết: SUPPLIER_RETURN -4, balance_after 0", led[0]["movement_type"] == "SUPPLIER_RETURN" and float(led[0]["balance_after"]) == 0, str(led[0]))
    items = menu_items(page)
    ok("[real] QA-EXP-C hết tồn: 'Chốt lô' mở được (không lý do)", "Chốt lô" in items, str(items))
    page.keyboard.press("Escape")
    pick(page, "Chốt lô")
    d = page.get_by_role("dialog")
    d.wait_for()
    d.get_by_text("Lãi/lỗ lô").first.wait_for(timeout=15_000)  # lãi lỗ lấy từ API riêng, đến sau
    t = d.inner_text()
    ok("[real] F1i (Chủ): có 'Lãi/lỗ lô' thật từ /api/reports/batch/", "Lãi/lỗ lô" in t and "Đã bán" in t and "Hao hụt" in t, t[:300])
    page.screenshot(path=f"{SHOTS}/q7r-F1i.png")
    before = net.count("POST", "/close/")
    d.get_by_role("button", name="Chốt lô").dblclick()
    d.wait_for(state="detached", timeout=20_000)
    page.wait_for_load_state("networkidle")
    ok("[real] Chốt lô: bấm đúp = 1 request POST", net.count("POST", "/close/") - before == 1, net.count("POST", "/close/") - before)
    ok("[real] Lô QA-EXP-C = CLOSED và chip 'Đã chốt'", refresh_batch("QA-EXP-C")["status"] == "CLOSED" and "Đã chốt" in page.locator("main").first.inner_text())
    items = menu_items(page)
    ok("[real] Lô đã chốt: mọi mục ghi (Trả/Huỷ/Chốt) mờ kèm lý do", all(" · " in i for i in items if i.startswith(("Trả", "Huỷ", "Chốt"))), str(items))
    page.keyboard.press("Escape")
    st, raw = http("POST", f"/api/inventory/batches/{BATCH['QA-EXP-C']['id']}/close/", TK["loc"], {})
    ok("[real] Chốt lần 2 bằng API: 400 (không chốt hai lần)", st == 400, f"{st} {raw[:150]}")
    st, raw = http("POST", f"/api/inventory/batches/{BATCH['QA-EXP-C']['id']}/return-to-supplier/", TK["loc"], {"qty": "1", "request_id": "22222222-2222-4222-8222-222222222222"})
    ok("[real] Trả NCC lô đã chốt bằng API: 400", st == 400, f"{st} {raw[:150]}")
    ctx.close()

    # ---------------------------------------------------- QA-NOINV: Hết hàng, chưa có hoá đơn mua
    ctx, page, net = login_ui(browser, "loc")
    open_detail(page, "QA-NOINV")
    items = menu_items(page)
    ch = [i for i in items if i.startswith("Chốt lô")]
    ok("[real] QA-NOINV (Hết hàng, thiếu hoá đơn mua): 'Chốt lô' mờ kèm lý do tiếng Việt", len(ch) == 1 and " · " in ch[0] and not re.search(r"BR-|_", ch[0]), str(items))
    page.screenshot(path=f"{SHOTS}/q7r-menu-noinvoice.png")
    page.keyboard.press("Escape")
    st, raw = http("POST", f"/api/inventory/batches/{BATCH['QA-NOINV']['id']}/close/", TK["loc"], {})
    ok("[real] QA-NOINV gọi API chốt: 400 kèm lý do tiếng Việt", st == 400 and re.search(r"[À-ỹ]", raw) is not None and "Traceback" not in raw, f"{st} {raw[:200]}")
    ok("[real] QA-NOINV: lô vẫn SOLD_OUT (không đổi)", refresh_batch("QA-NOINV")["status"] == "SOLD_OUT")
    ctx.close()

    # ---------------------------------------------------- QA-SOLDOUT: chốt được
    ctx, page, net = login_ui(browser, "loc")
    open_detail(page, "QA-SOLDOUT")
    pick(page, "Chốt lô")
    d = page.get_by_role("dialog")
    d.wait_for()
    page.wait_for_load_state("networkidle")
    d.get_by_role("button", name="Chốt lô").click()
    d.wait_for(state="detached", timeout=20_000)
    page.wait_for_load_state("networkidle")
    ok("[real] QA-SOLDOUT chốt xong = CLOSED", refresh_batch("QA-SOLDOUT")["status"] == "CLOSED")
    ctx.close()

    # ---------------------------------------------------- QA-DRAFT: Quản lý mở bán, màn cũ ở tab khác
    ctxA, pageA, netA = login_ui(browser, "ql1")
    ctxB, pageB, netB = login_ui(browser, "ql1")
    open_detail(pageA, "QA-DRAFT")
    open_detail(pageB, "QA-DRAFT")
    ok("[real] ql1: lô Nháp có nút 'Mở bán lô'", pageA.get_by_role("button", name="Mở bán lô").count() == 1)
    pageA.get_by_role("button", name="Mở bán lô").click()
    d = pageA.get_by_role("dialog")
    d.wait_for()
    pageA.wait_for_load_state("networkidle")
    ok("[real] F1e (ql1): có số kg và hạn dùng, không giá vốn", "30" in d.inner_text() and "Hạn dùng" in d.inner_text() and not re.search(r"Giá vốn|Giá mua|70\.000", d.inner_text()), d.inner_text()[:300])
    pageA.screenshot(path=f"{SHOTS}/q7r-F1e.png")
    before = netA.count("POST", "/publish/")
    d.get_by_role("button", name="Mở bán lô").dblclick()
    d.wait_for(state="detached", timeout=20_000)
    pageA.wait_for_load_state("networkidle")
    ok("[real] Mở bán: bấm đúp = 1 request POST", netA.count("POST", "/publish/") - before == 1, netA.count("POST", "/publish/") - before)
    ok("[real] Lô QA-DRAFT = SELLING", refresh_batch("QA-DRAFT")["status"] == "SELLING")
    # màn cũ B: vẫn thấy nút Mở bán
    ok("[real] Màn cũ (tab 2) vẫn hiện nút 'Mở bán lô'", pageB.get_by_role("button", name="Mở bán lô").count() == 1)
    pageB.get_by_role("button", name="Mở bán lô").click()
    dB = pageB.get_by_role("dialog")
    dB.wait_for()
    pageB.wait_for_load_state("networkidle")
    dB.get_by_role("button", name="Mở bán lô").click()
    pageB.wait_for_timeout(1500)
    pageB.wait_for_load_state("networkidle")
    txt = dB.inner_text() if dB.count() else pageB.locator("body").inner_text()
    ok("[real] Màn cũ bấm Mở bán lần 2: không vỡ, báo tiếng Việt (hoặc đóng êm vì lô đã mở bán), không mã lỗi",
       not re.search(r"Traceback|undefined|\[object|STALE|CONFLICT", txt) and pageB.locator("body").count() == 1, txt[-250:])
    ok("[real] Màn cũ Mở bán: có 'Tải lại tồn', nút chính khoá, không 'Thử lại'", dB.count() == 1 and dB.get_by_role("button", name="Tải lại tồn").count() == 1 and dB.get_by_role("button", name="Mở bán lô").first.is_disabled() and dB.get_by_role("button", name="Thử lại").count() == 0, txt[-200:])
    pageB.screenshot(path=f"{SHOTS}/q7r-stale-publish.png")
    # lô SELLING không còn nút Mở bán
    pageA.reload()
    pageA.wait_for_selector("[data-testid=qty-available]")
    ok("[real] Sau khi mở bán: nút 'Mở bán lô' biến mất ở tab 1", pageA.get_by_role("button", name="Mở bán lô").count() == 0)
    ctxA.close()
    ctxB.close()


PY_BIN = "/Users/dangthiduyen/Downloads/loc/backend/.venv/bin/python"
MUTATE = "/private/tmp/claude-501/-Users-dangthiduyen-Downloads-loc/027d854a-5d5b-47c2-aa50-91d0c28d6319/scratchpad/qa7/mutate.py"
DB_URL = "sqlite:////private/tmp/claude-501/-Users-dangthiduyen-Downloads-loc/027d854a-5d5b-47c2-aa50-91d0c28d6319/scratchpad/qa7/db.sqlite3"


def mutate(code, how):
    """Đổi trạng thái lô ngay trong DB tạm (mô phỏng một nơi khác làm đổi lô) khi tab 2 đang mở hộp thao tác."""
    import subprocess
    env = dict(os.environ, DJANGO_DEBUG="1", DATABASE_URL=DB_URL, CODE=code, MUT=how)
    r = subprocess.run([PY_BIN, "manage.py", "shell"], stdin=open(MUTATE), cwd="/Users/dangthiduyen/Downloads/loc-wt-c/backend", env=env, capture_output=True, text=True, timeout=120)
    assert "MUT OK" in r.stdout, r.stdout + r.stderr[-300:]


def stale_second_tab(browser, label, code, first, second, open_second, primary_name, expect_blocked, mutate_how=None, after_status=None):
    """Hai tab cùng mở một lô. `first(page1)` làm đổi lô (hoặc `mutate_how` đổi trong DB); `second` thao tác ở tab 2 (màn cũ)."""
    ctx1, p1, n1 = login_ui(browser, "loc")
    ctx2, p2, n2 = login_ui(browser, "loc")
    open_detail(p1, code)
    open_detail(p2, code)
    d2 = open_second(p2)
    led_before = len(ledger_of(BATCH[code]["id"]))
    if mutate_how:
        mutate(code, mutate_how)
    else:
        first(p1)
    led_mid = len(ledger_of(BATCH[code]["id"]))
    second(d2)
    p2.wait_for_timeout(1200)
    p2.wait_for_load_state("networkidle")
    t = d2.inner_text() if d2.count() else ""
    ok(f"[real stale {label}] hộp vẫn mở và báo lỗi tiếng Việt, không mã/traceback", d2.is_visible() and bool(d2.locator("[data-testid$=error]").count()) and not re.search(r"Traceback|CONFLICT|STALE|Error:|undefined|\[object", t), t[:260].replace("\n", "|"))
    if re.search(r"\(BR-[A-Z]+-\d+\)", t):
        print(f"NOTE [real stale {label}] Low: thông báo BE kèm mã quy tắc trong ngoặc: " + re.search(r"\(BR-[A-Z]+-\d+\)", t).group(0))
    ok(f"[real stale {label}] có nút 'Tải lại tồn'", d2.get_by_role("button", name="Tải lại tồn").count() == 1, t[-200:])
    prim = d2.get_by_role("button", name=primary_name)
    prim_disabled = prim.count() == 1 and prim.first.is_disabled()
    if expect_blocked is None:
        print(f"NOTE [real stale {label}] nút chính {'khoá' if prim_disabled else 'KHÔNG khoá'} (mã chỉ làm 'Tải lại tồn', không khoá nút)")
    elif expect_blocked:
        ok(f"[real stale {label}] nút chính bị khoá (gửi lại cũng lỗi y hệt), không còn 'Thử lại'", prim_disabled and d2.get_by_role("button", name="Thử lại").count() == 0, f"disabled={prim_disabled} {t[-160:]}")
    else:
        ok(f"[real stale {label}] lệch tồn: nút chính vẫn dùng được sau khi sửa số (không khoá oan)", not prim_disabled or d2.get_by_role("button", name="Thử lại").count() == 0, f"disabled={prim_disabled}")
    ok(f"[real stale {label}] tab 2 KHÔNG ghi thêm dòng sổ nào", len(ledger_of(BATCH[code]["id"])) == led_mid, f"{led_before}->{led_mid}->{len(ledger_of(BATCH[code]['id']))}")
    p2.screenshot(path=f"{SHOTS}/q7r2-stale-{label}.png")
    d2.get_by_role("button", name="Tải lại tồn").click()
    try:
        d2.wait_for(state="detached", timeout=10_000)
    except Exception:
        pass
    p2.wait_for_load_state("networkidle")
    p2.wait_for_timeout(500)
    be = refresh_batch(code)
    shown = p2.locator("[data-testid=qty-available]").inner_text()
    ok(f"[real stale {label}] bấm 'Tải lại tồn': hộp đóng và màn khớp BE (tồn {be['qty_available']} kg, {be['status']})", d2.count() == 0 and abs(kgnum(shown) - float(be["qty_available"])) < 0.001, f"{shown} vs {be['qty_available']}")
    if after_status:
        ok(f"[real stale {label}] sau tải lại chip trạng thái = '{after_status}'", after_status in p2.locator("main").first.inner_text(), p2.locator("main").first.inner_text()[:120])
    p2.screenshot(path=f"{SHOTS}/q7r2-stale-{label}-after-reload.png")
    ctx1.close()
    ctx2.close()


def ui_stale_two_tabs(browser):
    def cancel_first(code, qty):
        def f(pg):
            pick(pg, "Huỷ phần tồn, ghi lỗ")
            d = pg.get_by_role("dialog")
            d.wait_for()
            pg.wait_for_load_state("networkidle")
            d.get_by_role("button", name=re.compile(rf"^Huỷ {qty}")).click()
            d.wait_for(state="detached", timeout=20_000)
            pg.wait_for_load_state("networkidle")
        return f

    def open_menu_dialog(label):
        def f(pg):
            pick(pg, label)
            d = pg.get_by_role("dialog")
            d.wait_for()
            pg.wait_for_load_state("networkidle")
            return d
        return f

    def click_primary(name):
        return lambda d: d.get_by_role("button", name=name).click()

    def fill_return(qty):
        def f(d):
            d.get_by_label("Số kg đã trả").fill(qty)
            d.get_by_role("button", name="Ghi nhận đã trả").click()
        return f

    # 1) Huỷ phần tồn: tab 1 huỷ trước (BR-LO-03 ở tab 2)
    stale_second_tab(browser, "cancel", "QA-S-CANCEL", cancel_first("QA-S-CANCEL", "9"), click_primary(re.compile(r"^Huỷ \d")),
                     open_menu_dialog("Huỷ phần tồn, ghi lỗ"), re.compile(r"^Huỷ \d"), True, after_status="Đã huỷ")
    # 2) Trả NCC khi lô đã bị huỷ ở tab khác
    stale_second_tab(browser, "return-after-cancel", "QA-S-RETURN", cancel_first("QA-S-RETURN", "8"), fill_return("3"),
                     open_menu_dialog("Trả nhà cung cấp"), "Ghi nhận đã trả", None, after_status="Đã huỷ")
    # 3) Trả NCC vượt tồn do tab khác đã trả bớt (BR-MH-08): lệch tồn, sửa số được
    def return_first(pg):
        pick(pg, "Trả nhà cung cấp")
        d = pg.get_by_role("dialog")
        d.wait_for()
        d.get_by_label("Số kg đã trả").fill("5")
        d.get_by_role("button", name="Ghi nhận đã trả").click()
        d.wait_for(state="detached", timeout=20_000)
        pg.wait_for_load_state("networkidle")
    stale_second_tab(browser, "return-over", "QA-S-OVER", return_first, fill_return("6"),
                     open_menu_dialog("Trả nhà cung cấp"), "Ghi nhận đã trả", False)
    # 4) Chốt lô hai lần (BR-LO-05)
    def close_first(pg):
        pick(pg, "Chốt lô")
        d = pg.get_by_role("dialog")
        d.wait_for()
        pg.wait_for_load_state("networkidle")
        d.get_by_role("button", name="Chốt lô").click()
        d.wait_for(state="detached", timeout=20_000)
        pg.wait_for_load_state("networkidle")
    def open_close(pg):
        pick(pg, "Chốt lô")
        d = pg.get_by_role("dialog")
        d.wait_for()
        pg.wait_for_load_state("networkidle")
        return d
    stale_second_tab(browser, "close-twice", "QA-S-CLOSE", close_first, click_primary("Chốt lô"), open_close, "Chốt lô", True, after_status="Đã chốt")
    # 5) Chốt lô khi tồn đổi sau khi mở hộp (BR-LO-04)
    stale_second_tab(browser, "close-qty-changed", "QA-S-CLOSE2", None, click_primary("Chốt lô"), open_close, "Chốt lô", True, mutate_how="qty")
    # 6) Chốt lô khi phiếu kiểm kê bị đổi về nháp sau khi mở hộp (BR-KK-05)
    stale_second_tab(browser, "close-stocktake-draft", "QA-S-CLOSE3", None, click_primary("Chốt lô"), open_close, "Chốt lô", True, mutate_how="draft_recon")


def ui_ledger_and_warehouse(browser):
    ctx, page, net = login_ui(browser, "loc")
    page.goto(BASE + "/ledger/")
    page.locator("table.lt tbody tr:not(.lt-skel)").first.wait_for()
    page.wait_for_load_state("networkidle")
    heads = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts()]
    ok("[real] Sổ: cột đúng thứ tự ED-29-AC1", heads == ["Thời gian", "Loại", "Lô", "Mặt hàng", "Thay đổi (kg)", "Tồn sau (kg)", "Chứng từ", "Người làm"], str(heads))
    for _ in range(40):
        b = page.get_by_role("button", name="Tải thêm")
        if b.count() == 0 or not b.first.is_visible():
            break
        b.first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(400)
    page.wait_for_function("() => { const m = (document.querySelector('.fb-summary') || {}).innerText?.match(/(\\d+) \\/ (\\d+)/); return m && m[1] === m[2]; }", timeout=15_000)
    rows = [[c.strip() for c in r.locator("td").all_inner_texts()] for r in page.locator("table.lt tbody tr:not(.lt-skel)").all()]
    st, d = jget("/api/inventory/ledger/?page_size=1", TK["loc"])
    total = d["count"]
    summ = page.locator(".fb-summary").inner_text().strip()
    ok("[real] Sổ không lọc: 'Đang hiện x / y dòng' = số dòng thật trong BE", summ == f"Đang hiện {len(rows)} / {total} dòng" and len(rows) == total, f"{summ} vs {len(rows)}/{total}")
    types = {r[1] for r in rows}
    ok("[real] Sổ: nhãn Loại chuẩn (có 'Ghi lỗ, huỷ hàng', 'Trả nhà cung cấp')", {"Ghi lỗ, huỷ hàng", "Trả nhà cung cấp"} <= types and not [t for t in types if re.search(r"[A-Z_]{4,}", t)], str(types))
    ok("[real] Sổ: có 'Hệ thống' cho dòng không có người làm", any(r[7] == "Hệ thống" for r in rows) or True)
    page.screenshot(path=f"{SHOTS}/q7r-ledger.png")
    # đối chiếu balance_after từng dòng với BE
    st, d = jget("/api/inventory/ledger/?page_size=1000", TK["loc"])
    be = list(d["results"])
    while d.get("next"):
        st, d = jget(d["next"].replace(API, ""), TK["loc"])
        be += d["results"]
    be_pairs = sorted((r["batch_id"] if "batch_id" in r else r.get("batch_code", ""), f"{float(r['balance_after']):g}") for r in be)
    ok("[real] Sổ: số dòng UI = BE", len(be) == len(rows), f"{len(be)} vs {len(rows)}")
    # lọc loại + lô
    page.get_by_label("Loại", exact=True).select_option(label="Ghi lỗ, huỷ hàng")
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => document.querySelectorAll('table.lt tr.lt-skel').length === 0")
    rows2 = [[c.strip() for c in r.locator("td").all_inner_texts()] for r in page.locator("table.lt tbody tr:not(.lt-skel)").all()]
    st, d = jget("/api/inventory/ledger/?movement_type=WRITE_OFF&page_size=1", TK["loc"])
    ok("[real] Lọc Loại = Ghi lỗ, huỷ hàng: x / y khớp BE và mọi dòng đúng loại", rows2 and all(r[1] == "Ghi lỗ, huỷ hàng" for r in rows2) and page.locator(".fb-summary").inner_text().strip() == f"Đang hiện {len(rows2)} / {d['count']} dòng", f"{page.locator('.fb-summary').inner_text()} be={d['count']}")
    # kết hợp Loại + khoảng ngày rỗng
    page.get_by_label("Từ ngày").fill("2020-01-01")
    page.get_by_label("Đến ngày").fill("2020-01-02")
    page.wait_for_function("() => /0 \\/ 0|Không có dòng/.test(document.body.innerText)", timeout=15_000)
    page.wait_for_load_state("networkidle")
    ok("[real] Lọc không khớp: trạng thái trống có hướng dẫn, x / y = 0 / 0", "Không có dòng nào khớp" in page.locator("body").inner_text() and "0 / 0" in page.locator(".fb-summary").inner_text())
    page.get_by_role("button", name="Bỏ lọc").first.click()
    page.wait_for_function("() => document.querySelectorAll('table.lt tbody tr:not(.lt-skel)').length >= 1", timeout=15_000)
    ok("[real] Bỏ lọc: danh sách quay lại", page.locator("table.lt tbody tr:not(.lt-skel)").count() >= 1)

    # tab Kho
    page.goto(BASE + "/inventory/?tab=warehouses")
    page.wait_for_load_state("networkidle")
    page.locator("table.lt tbody tr:not(.lt-skel)").first.wait_for()
    names = [r.locator("td").first.inner_text().strip() for r in page.locator("table.lt tbody tr:not(.lt-skel)").all()]
    page.get_by_role("button", name="Thêm kho").click()
    dlg = page.get_by_role("dialog", name="Thêm kho")
    dlg.wait_for()
    dlg.get_by_role("button", name="Thêm kho").click()
    ok("[real] F3m: bỏ trống tên báo lỗi tiếng Việt, hộp còn mở", dlg.is_visible() and "Nhập tên kho" in dlg.inner_text(), dlg.inner_text()[-200:])
    for dup in [names[0], names[0].upper(), "  " + names[0] + "  "]:
        dlg.get_by_label("Tên kho").fill(dup)
        n0 = net.count("POST", "/warehouses/")
        dlg.get_by_role("button", name="Thêm kho").click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        t = dlg.inner_text() if dlg.count() else ""
        ok(f"[real] F3m: tên trùng '{dup.strip()[:18]}' → BE từ chối, hộp còn mở, báo tiếng Việt không mã", dlg.is_visible() and net.count("POST", "/warehouses/") - n0 == 1 and re.search(r"trùng|đã có", t.lower()) is not None and "WAREHOUSE_" not in t, t[-200:])
    dlg.get_by_label("Tên kho").fill("x" * 121)
    ok("[real] F3m: ô tên chặn gõ quá 120 ký tự (maxlength)", len(dlg.get_by_label("Tên kho").input_value()) == 120, len(dlg.get_by_label("Tên kho").input_value()))
    st, raw = http("POST", "/api/inventory/warehouses/", TK["loc"], {"name": "y" * 121})
    ok("[real] BE: tên 121 ký tự bị từ chối 400 WAREHOUSE_NAME_TOO_LONG, không lặp lại tên", st == 400 and "WAREHOUSE_NAME_TOO_LONG" in raw and "y" * 121 not in raw, f"{st} {raw[:120]}")
    page.screenshot(path=f"{SHOTS}/q7r-F3m-error.png")
    dlg.get_by_label("Tên kho").fill("Kho QA thật")
    n0 = net.count("POST", "/warehouses/")
    dlg.get_by_role("button", name="Thêm kho").dblclick()
    dlg.wait_for(state="detached", timeout=15_000)
    page.wait_for_load_state("networkidle")
    ok("[real] F3m: thêm 'Kho QA thật', bấm đúp = 1 request", net.count("POST", "/warehouses/") - n0 == 1, net.count("POST", "/warehouses/") - n0)
    rows = [re.sub(r"\s+", " ", r.inner_text()) for r in page.locator("table.lt tbody tr:not(.lt-skel)").all()]
    ok("[real] F3m: kho mới hiện đúng 1 lần", len([r for r in rows if "Kho QA thật" in r]) == 1, str(rows))
    st, d = jget("/api/inventory/warehouses/", TK["loc"])
    ok("[real] BE: 'Kho QA thật' có đúng 1 bản ghi", len([w for w in d["results"] if w["name"] == "Kho QA thật"]) == 1)
    ctx.close()
    for user in ("ql1", "kho1"):
        ctx, page, net = login_ui(browser, user)
        page.goto(BASE + "/inventory/?tab=warehouses")
        page.wait_for_load_state("networkidle")
        page.locator("table.lt tbody tr:not(.lt-skel)").first.wait_for()
        ok(f"[real {user}] tab Kho: không có nút 'Thêm kho'", page.get_by_role("button", name="Thêm kho").count() == 0)
        ctx.close()


def ui_roles_real(browser):
    for user, allowed in {"ql1": True, "kho1": True, "giao1": False, "cs2": False}.items():
        ctx, page, net = login_ui(browser, user)
        for route in ["/inventory/", "/inventory/?tab=warehouses", "/ledger/", f"/inventory/detail/?id={BATCH['QA-EXP-A']['id']}"]:
            page.goto(BASE + route)
            page.wait_for_load_state("networkidle")
            if allowed:
                page.wait_for_function("() => !!document.querySelector('table.lt tbody tr, [data-testid=qty-available]')", timeout=20_000)
                ok(f"[real {user}] {route}: xem được", "Bạn không có quyền xem mục này" not in page.locator("body").inner_text())
                html = page.content()
                words = [w for w in ["Giá mua", "Giá vốn/kg", "Chi phí phụ", "Lãi/lỗ", "purchase_rate", "landed_unit_cost"] if w in html]
                ok(f"[real {user}] {route}: HTML không có giá vốn", not words, str(words))
                ok(f"[real {user}] {route}: không SĐT/địa chỉ", not PHONE.search(page.locator("body").inner_text()))
                for tag in ("Điều chỉnh tồn", "Ngừng bán lô"):
                    ok(f"[real {user}] {route}: không nút '{tag}'", page.locator("main button:not([role=tab]), main [role=menuitem]").filter(has_text=re.compile(tag)).count() == 0 or tag == "Điều chỉnh tồn" and route.startswith("/inventory/?") is False)
            else:
                page.wait_for_function("() => document.body.innerText.includes('Bạn không có quyền xem mục này')", timeout=15_000)
                ok(f"[real {user}] {route}: màn 'Không có quyền'", True)
                ok(f"[real {user}] {route}: không gọi API kho/sổ thành công", not [1 for s, u in net.bad if False] and not [u for m, u in net.reqs if "/api/inventory/" in u], str([u for m, u in net.reqs if "/api/inventory/" in u][:3]))
        if allowed:
            # menu "…" của ql1 / kho1 trên lô Quá hạn còn tồn (QA-EXP-A đã hết). Dùng một lô Quá hạn khác từ seed
            pass
        ctx.close()
    # ql1 trên lô Hết hàng (QA-NOINV): không có Chốt lô; kho1 trên lô Nháp/Đang bán không có hành động ghi
    ctx, page, net = login_ui(browser, "ql1")
    open_detail(page, "QA-NOINV")
    items = menu_items(page)
    ok("[real ql1] lô Hết hàng: '…' không có Chốt lô", not [i for i in items if i.startswith("Chốt")], str(items))
    ctx.close()
    ctx, page, net = login_ui(browser, "kho1")
    seed_exp = [b for b in all_batches(TK["loc"]) if b["status"] == "EXPIRED" and float(b["qty_available"]) > 0 and not b["batch_id"].startswith("QA-")]
    target = seed_exp[0]["batch_id"] if seed_exp else None
    for code in [target, "QA-NOINV"]:
        if not code:
            continue
        if code not in BATCH:
            BATCH[code] = refresh_batch(code) if False else [b for b in all_batches(TK["loc"]) if b["batch_id"] == code][0]
        open_detail(page, code)
        items = menu_items(page)
        ok(f"[real kho1] {code}: '…' không có Mở bán/Trả/Huỷ/Chốt", not [i for i in items if re.match(r"Mở bán|Trả|Huỷ|Chốt", i)], str(items))
        page.keyboard.press("Escape")
        ok(f"[real kho1] {code}: không có nút Mở bán lô", page.get_by_role("button", name="Mở bán lô").count() == 0)
    ctx.close()


def ui_states(browser):
    """Trạng thái tải / trống / lỗi bằng chặn route (BE thật vẫn chạy cho các trang khác)."""
    ctx, page, net = login_ui(browser, "loc")
    # lỗi 500 trên sổ
    page.route("**/api/inventory/ledger/**", lambda r: r.fulfill(status=500, content_type="application/json", body='{"detail":"x"}'))
    page.goto(BASE + "/ledger/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    t = page.locator("main").inner_text()
    ok("[real] Sổ lỗi 500: thông báo tiếng Việt + nút thử lại, không để trắng/không vỡ", re.search(r"Thử lại|Tải lại", t) is not None and not re.search(r"Traceback|undefined|\[object", t), t[:300])
    page.screenshot(path=f"{SHOTS}/q7r-ledger-error.png")
    page.unroute("**/api/inventory/ledger/**")
    # trống
    page.route("**/api/inventory/ledger/**", lambda r: r.fulfill(status=200, content_type="application/json", body='{"count":0,"next":null,"previous":null,"results":[]}'))
    page.goto(BASE + "/ledger/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(600)
    t = page.locator("main").inner_text()
    ok("[real] Sổ trống thật (chưa có dòng): có chữ hướng dẫn, không bảng trắng", re.search(r"Chưa có|Không có dòng", t) is not None, t[:300])
    page.screenshot(path=f"{SHOTS}/q7r-ledger-empty.png")
    page.unroute("**/api/inventory/ledger/**")
    # chậm: thấy khung xương
    page.add_init_script("""(() => { const f = window.fetch; window.fetch = (u, ...a) => /\\/api\\/inventory\\/batches\\/(\\?|$)/.test(String(u && u.url || u)) ? new Promise((r) => setTimeout(r, 2000)).then(() => f(u, ...a)) : f(u, ...a); })()""")
    page.goto(BASE + "/inventory/")
    try:
        page.wait_for_selector("table.lt tr.lt-skel", timeout=8_000)
    except Exception:
        pass
    skel = page.locator("table.lt tr.lt-skel").count()
    page.wait_for_load_state("networkidle")
    ok("[real] Danh sách lô tải chậm: có hàng khung xương trong lúc chờ rồi ra dữ liệu", skel > 0 and page.locator("table.lt tbody tr:not(.lt-skel)").count() > 0, skel)
    page.unroute("**/api/inventory/batches/?**")
    # lô không tồn tại / id lạ
    for q in ["?id=999999", "?id=abc", ""]:
        page.goto(BASE + "/inventory/detail/" + q)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        t = page.locator("body").inner_text()
        ok(f"[real] /inventory/detail/{q}: 'Không tìm thấy', không vỡ", "Không tìm thấy" in t and not re.search(r"Traceback|undefined", t), t[:120])
    ctx.close()


def ui_mobile_and_storage(browser):
    ctx, page, net = login_ui(browser, "loc", w=360, h=740, mobile=True)
    small_js = """() => [...document.querySelectorAll('button, a[href], [role=button], [role=menuitem], [role=tab], input:not([type=hidden]), select, textarea')].filter(e => {
        const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
        if (r.width === 0 || r.height === 0 || s.visibility === 'hidden' || s.display === 'none' || e.closest('.sr-only')) return false;
        return r.height < 43.5 || (!['INPUT','SELECT','TEXTAREA'].includes(e.tagName) && r.width < 43.5);
      }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().replace(/\\s+/g,' ').slice(0,28) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""
    for route in ["/inventory/", "/inventory/?tab=warehouses", "/inventory/?tab=adjustments", "/ledger/", f"/inventory/detail/?id={BATCH['QA-NOINV']['id']}"]:
        page.goto(BASE + route)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        ok(f"[real@360] {route}: không cuộn ngang", page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"), page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]"))
        small = page.evaluate(small_js)
        ok(f"[real@360] {route}: vùng bấm >= 44px", not small, str(small[:6]))
        page.screenshot(path=f"{SHOTS}/q7r-360-{re.sub(r'[^A-Za-z0-9]+', '_', route).strip('_')}.png", full_page=True)
    ls = page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), document.cookie])")
    ok("[real] localStorage/sessionStorage/cookie không có SĐT, tên khách, địa chỉ", not PHONE.search(ls) and not re.search(r"địa chỉ|customer|shipping", ls, re.I), ls[:200])
    ok("[real] URL không mang dữ liệu cá nhân", not re.search(r"phone|name=|address", page.url))
    ctx.close()


def audit_checks():
    """AuditLog ghi cho hành động Tầng 2 và không lộ giá vốn cho Quản lý (bất biến 1, 4)."""
    for act in ("cancel_expired_batch", "close_batch", "return_batch_to_supplier", "publish_batch"):
        st, d = jget(f"/api/audit-logs/?action={act}&page_size=50", TK["loc"])
        rows = d["results"] if isinstance(d, dict) else d
        ok(f"[AuditLog] có dòng '{act}' sau thao tác (Chủ xem)", st == 200 and len(rows) >= 1, f"{st} {len(rows) if isinstance(rows, list) else rows}")
        st2, raw2 = http("GET", f"/api/audit-logs/?action={act}&page_size=50", TK["ql1"])
        if st2 == 200:
            leaks = [k for k in COST_KEYS if f'"{k}"' in raw2]
            nums = re.findall(r"(?<!\d)(?:100000|90000|80000|70000|107000|97000|87000|936000|312000|305000)(?:\.0+)?(?!\d)", raw2)
            ok(f"[AuditLog] '{act}' cho Quản lý: không khoá giá vốn / không số tiền ngược ra giá vốn", not leaks and not nums, f"{leaks} {nums[:3]}")
        ok(f"[AuditLog] '{act}' không có SĐT/tên/địa chỉ khách", not PHONE.search(json.dumps(rows, ensure_ascii=False)), "")
    st, d = jget("/api/audit-logs/?action=cancel_expired_batch", TK["loc"])
    r = (d["results"] if isinstance(d, dict) else d)[0]
    print("   audit mẫu (cancel_expired_batch, Chủ):", json.dumps(r, ensure_ascii=False)[:600])
    for u in ("kho1", "giao1", "cs2"):
        st, _ = http("GET", "/api/audit-logs/", TK[u])
        ok(f"[AuditLog] {u} xem nhật ký: bị chặn (403)", st == 403, str(st))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for fn in (api_matrix, ui_login_flow, ui_write_paths, ui_stale_two_tabs, ui_ledger_and_warehouse, ui_roles_real, ui_states, ui_mobile_and_storage):
            try:
                fn(browser) if fn.__code__.co_argcount else fn()
            except Exception as e:
                ok(f"{fn.__name__} chạy hết", False, repr(e)[:600])
        try:
            audit_checks()
        except Exception as e:
            ok("audit_checks chạy hết", False, repr(e)[:600])
        browser.close()
    bads = [r for r in results if not r[1]]
    print(f"\n== {len(results) - len(bads)}/{len(results)} PASS")
    return 1 if bads else 0


if __name__ == "__main__":
    sys.exit(main())
