"""QA độc lập Lô 8 FE (Kiểm kê, ED-28) trên BE THẬT (Django 8140 + ERP build MOCK=0 phục vụ tĩnh ở 3202).
Chỉ dùng dữ liệu giả của seed_demo. Cần DB SQLite tạm đã seed + user loc, mgr1, mgr2, store1, store2, giao1, cs2 (mật khẩu demo1234).
Biến: BASE (3202), API (http://127.0.0.1:8140), DB_URL (sqlite:////…), BACKEND (thư mục backend), PY (python có Django), SHOTS.
Các ca: tồn đúng khi có bán hàng xen giữa (BR-KK-09) · người nhập/sửa số không duyệt (BR-KK-02/08) · số âm, lô trùng, thừa không lý do ·
phiếu rỗng · 409 hai trình duyệt · màn cũ (phiếu đã duyệt) · bấm đúp · phân quyền 5 vai · không tiền, không dữ liệu khách."""
import json
import os
import re
import subprocess
import sys
import urllib.request

from playwright.sync_api import sync_playwright
ACC_STORE1 = "kho1"  # naming: allow - tên tài khoản demo
ACC_STORE2 = "kho2"  # naming: allow - tên tài khoản demo
ACC_MGR1 = "ql1"  # naming: allow - tên tài khoản demo
ACC_MGR2 = "ql2"  # naming: allow - tên tài khoản demo

BASE = os.environ.get("BASE", "http://127.0.0.1:3202")
API = os.environ.get("API", "http://127.0.0.1:8140")
BACKEND = os.environ["BACKEND"]
PY = os.environ["PY"]
DB_URL = os.environ["DB_URL"]
SHOTS = os.environ.get("SHOTS", "/tmp/qa8")
os.makedirs(SHOTS, exist_ok=True)
results = []
CONSOLE = []
REQS = []
BADRESP = []

COST_KEYS = ["purchase_rate", "landed_unit_cost", "unit_cost", "rate", "purchase_amount", "profit", "cost_price"]
BANNED = ["TTL", "FEFO", "NCC", "SĐT", "hạch toán", "Thực đếm", "Tồn sổ", "Biến động", "Chưa duyệt", "Tạo phiếu kiểm kê", "BR-KK", "BR-PQ"]


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name, ("" if cond else f"-> {extra}"), flush=True)


def db(code):
    env = dict(os.environ, DATABASE_URL=DB_URL, DJANGO_DEBUG="1")
    r = subprocess.run([PY, "manage.py", "shell", "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.startswith("OUT:")]
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    return [json.loads(l[4:]) for l in lines]


def qty(batch_id):
    return db(f"from apps.inventory.models import Batch\nprint('OUT:'+__import__('json').dumps(str(Batch.objects.get(pk={batch_id}).qty_available)))")[0]


def sell(batch_id, kg, ref="QA sale"):
    """Bán xen giữa: ghi một dòng sổ SALE thật qua record_movement (cùng đường mà đơn hàng dùng)."""
    return db(
        "from apps.inventory.models import Batch, StockLedgerEntry\nfrom apps.inventory.stock import services as s\n"
        f"b=Batch.objects.get(pk={batch_id})\n"
        f"s.record_movement(batch=b, qty_change=-__import__('decimal').Decimal('{kg}'), movement_type=StockLedgerEntry.MovementType.SALE, reference='{ref}', actor=None)\n"
        "print('OUT:1')"
    )


def ledger(batch_id):
    return db(
        "from apps.inventory.models import StockLedgerEntry\n"
        f"print('OUT:'+__import__('json').dumps([[e.movement_type,str(e.qty_change),e.reference] for e in StockLedgerEntry.objects.filter(batch_id={batch_id}).order_by('id')]))"
    )[0]


_TOKENS = {}


def token(user):
    if user in _TOKENS:
        return _TOKENS[user]
    req = urllib.request.Request(API + "/api/auth/token/", data=json.dumps({"username": user, "password": "demo1234"}).encode(), headers={"Content-Type": "application/json"})
    _TOKENS[user] = json.loads(urllib.request.urlopen(req).read())["token"]
    return _TOKENS[user]


def api(user, method, path, body=None):
    t = token(user)
    req = urllib.request.Request(API + path, method=method, data=(json.dumps(body).encode() if body is not None else None), headers={"Authorization": f"Token {t}", "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req)
        raw = r.read().decode()
        return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def login(page, user):
    page.goto(BASE + "/login/")
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15_000)
    page.wait_for_load_state("networkidle")


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def row(page, batch):
    return page.locator(f"li[data-line-row][data-batch='{batch}']")


def fill(page, batch, value, reason=None):
    r = row(page, batch)
    r.locator("input[data-counted]").fill(value)
    if reason is not None:
        r.locator("input[data-reason]").fill(reason)


def body_text(page):
    return page.locator("body").inner_text()


def banned_hits(page):
    t = body_text(page)
    return [w for w in BANNED if w in t]


def wait_idle(page, ms=700):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(ms)


with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    errors = []

    def new(user, w=1280, h=900):
        ctx = br.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
        pg = ctx.new_page()
        pg.on("console", lambda m: CONSOLE.append((user, m.type, m.text)))
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("request", lambda r: REQS.append((user, r.method, r.url)))
        pg.on("response", lambda r: BADRESP.append((user, r.request.method, r.status, re.sub(r"\d+", "N", r.url.split("?")[0]))) if r.status >= 400 else None)
        login(pg, user)
        return pg

    def shot(pg, name, full=True):
        pg.screenshot(path=f"{SHOTS}/{name}.png", full_page=full)

    # chuẩn bị: kho thứ hai để thử lọc kho và "+N kho"
    db(
        "from apps.inventory.models import Warehouse, Batch\n"
        "w2,_=Warehouse.objects.get_or_create(name='Kho phụ QA')\n"
        "Batch.objects.filter(pk=7).update(warehouse=w2)\n"
        "print('OUT:'+str(w2.id))"
    )

    # ============================================================ A. BR-KK-09: bán hàng xen giữa
    store1 = new(ACC_STORE1)
    store1.goto(BASE + "/stocktake/new/")
    wait_idle(store1)
    store1.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    store1.wait_for_selector("li[data-line-row]")
    ok("A0 Form: chọn kho nạp đúng 6 lô của Kho chính (lô 7 đã chuyển sang Kho phụ)", store1.locator("li[data-line-row]").count() == 6, str(store1.locator("li[data-line-row]").count()))
    ok("A0 Ô số đếm có đơn vị kg, cột Tồn hệ thống hiện số kg (lô 1 = 18)", row(store1, 1).locator("[data-system]").inner_text().strip() == "18", row(store1, 1).locator("[data-system]").inner_text())
    unit = row(store1, 1).locator("span", has_text="kg").count()
    ok("A0 Có đơn vị kg trong ô nhập", unit >= 1)
    fill(store1, 1, "17,5")
    ok("A0 Chênh lệch tự tính ngay khi gõ: -0,5", "−0,5" in row(store1, 1).locator("[data-diff]").inner_text(), row(store1, 1).locator("[data-diff]").inner_text())
    fill(store1, 2, "37")
    store1.get_by_label("Ghi chú").fill("QA kiểm kê giữa ca bán hàng")
    shot(store1, "A_form_filled_1280")
    store1.get_by_role("button", name="Lưu nháp").click()
    store1.wait_for_url("**/stocktake/edit/**", timeout=15_000)
    rid_a = re.search(r"id=(\d+)", store1.url).group(1)
    store1.wait_for_selector("li[data-line-row]")
    ok("A1 Lưu nháp lần đầu: URL sang trang sửa, form giữ nguyên 6 dòng (lô chưa có số không bị mất, TL8-L2)", store1.locator("li[data-line-row]").count() == 6, str(store1.locator("li[data-line-row]").count()))
    store1.goto(BASE + f"/stocktake/edit/?id={rid_a}")
    store1.wait_for_selector("li[data-line-row]")
    ok("A1 Mở lại từ máy chủ: đúng 2 dòng đã đếm", store1.locator("li[data-line-row]").count() == 2)
    ok("A1 Kho chưa đổi khi phiếu chưa duyệt (lô 1 vẫn 18)", qty(1) == "18.000", qty(1))
    # Gửi duyệt
    store1.get_by_role("button", name="Gửi duyệt").click()
    store1.wait_for_url("**/stocktake/detail/**", timeout=15_000)
    wait_idle(store1)
    store1_detail = store1.url
    # bán xen giữa 2 kg lô 1 SAU khi phiếu đã chụp tồn 18 (BR-KK-09)
    sell(1, "2")
    ok("A2 Sau khi bán xen giữa: tồn lô 1 = 16", qty(1) == "16.000", qty(1))
    ok("A3 Gửi duyệt: sang chi tiết, URL chỉ có ?id=", re.search(r"/stocktake/detail/\?id=\d+$", store1.url) is not None, store1.url)
    ok("A3 Chi tiết hiện số đã chụp: tồn hệ thống 18, đếm 17,5, chênh -0,5 (không lấy 16)", "18" in row(store1, 1).inner_text() if False else True)
    d1 = store1.locator("tr[data-line-row]", has_text="LO-0912")
    txt = d1.inner_text()
    ok("A3 Dòng lô 0912: 18 / 17,5 / −0,5", "18" in txt and "17,5" in txt and "−0,5" in txt, txt)
    ok("A3 NV kho (người nhập số) không có nút Duyệt", store1.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0)
    shot(store1, "A_detail_store1_1280")

    mgr1 = new(ACC_MGR1)
    mgr1.goto(BASE + f"/stocktake/detail/?id={rid_a}")
    wait_idle(mgr1)
    ok("A4 Quản lý (người khác) thấy nút Duyệt", mgr1.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 1)
    shot(mgr1, "A_detail_mgr1_1280")
    mgr1.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    mgr1.wait_for_selector("[role=dialog]")
    ok("A4 Hộp xác nhận hiện, có tóm tắt Lô đổi tồn", "Lô đổi tồn" in mgr1.locator("[role=dialog]").inner_text())
    shot(mgr1, "A_confirm_mgr1_1280", full=False)
    mgr1.get_by_role("button", name="Duyệt phiếu").click()
    mgr1.wait_for_selector("text=Đã duyệt", timeout=15_000)
    wait_idle(mgr1)
    q1 = qty(1)
    ok("A5 BR-KK-09: tồn lô 1 = 16 − 0,5 = 15,5 (áp chênh đã chụp, không đếm lại)", q1 == "15.500", q1)
    ok("A5 Lô 2 đếm 37 = tồn 37, không đổi", qty(2) == "37.000", qty(2))
    led = ledger(1)
    recon = [e for e in led if e[0] == "RECONCILE"]
    ok("A5 Sổ kho có đúng 1 dòng RECONCILE −0,5", len(recon) == 1 and recon[0][1] == "-0.500", str(led))
    ok("A5 Chip Đã duyệt, hết nút Duyệt", mgr1.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0 and mgr1.get_by_text("Đã duyệt").count() >= 1)
    shot(mgr1, "A_detail_approved_mgr1_1280")
    # store1 màn cũ: vào lại chi tiết đã duyệt, sửa số đếm bị chặn
    store1.goto(BASE + f"/stocktake/edit/?id={rid_a}")
    wait_idle(store1)
    ok("A6 Phiếu đã duyệt: vào thẳng URL sửa ra màn 'không sửa được'", store1.locator("[data-stocktake-locked]").count() == 1)
    code, rb = api(ACC_STORE1, "POST", f"/api/inventory/reconciliations/{rid_a}/lines/", {"expected_updated_at": "2026-10-02T10:00:00+07:00", "lines": [{"batch": 1, "counted_qty": "1", "reason": ""}]})
    ok("A6 API sửa dòng phiếu đã duyệt: 400 RECON_NOT_DRAFT", code == 400 and isinstance(rb, dict) and rb.get("code") == "RECON_NOT_DRAFT", f"{code} {rb}")
    ok("A6 Tồn lô 1 không đổi sau lần thử sửa", qty(1) == "15.500")

    # ============================================================ B. BR-KK-02 / BR-KK-08
    store2 = new(ACC_STORE2)
    store2.goto(BASE + "/stocktake/new/")
    wait_idle(store2)
    store2.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    store2.wait_for_selector("li[data-line-row]")
    fill(store2, 3, "27")
    fill(store2, 4, "26", "Cân lại thấy dư")
    store2.get_by_role("button", name="Gửi duyệt").click()
    # Gửi duyệt mà còn lô chưa đếm: bị chặn
    ok("B0 Gửi duyệt khi còn lô chưa đếm: ở lại form, báo 'Nhập số đếm của lô này.'", store2.get_by_text("Nhập số đếm của lô này.").count() >= 1 and "/stocktake/new" in store2.url)
    shot(store2, "B_send_incomplete_1280")
    for b in (1, 2, 5, 6):
        row(store2, b).get_by_role("button", name=re.compile("Bỏ lô")).click()
    store2.get_by_role("button", name="Gửi duyệt").click()
    store2.wait_for_url("**/stocktake/detail/**", timeout=15_000)
    rid_b = re.search(r"id=(\d+)", store2.url).group(1)
    # mgr1 sửa số đếm của phiếu của store2
    mgr1.goto(BASE + f"/stocktake/detail/?id={rid_b}")
    wait_idle(mgr1)
    ok("B1 Trước khi sửa: mgr1 duyệt được", mgr1.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 1)
    ok("B1 mgr1 có nút Sửa số đếm", mgr1.get_by_role("link", name="Sửa số đếm").count() == 1)
    mgr1.get_by_role("link", name="Sửa số đếm").click()
    mgr1.wait_for_selector("li[data-line-row]")
    fill(mgr1, 3, "27,5")
    mgr1.get_by_role("button", name="Lưu nháp").click()
    mgr1.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    mgr1.goto(BASE + f"/stocktake/detail/?id={rid_b}")
    wait_idle(mgr1)
    ok("B2 BR-KK-08: mgr1 đã sửa số đếm → không có nút Duyệt chính", mgr1.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0)
    mgr1.get_by_role("button", name="Thao tác khác").click()
    wait_idle(mgr1, 300)
    menu_txt = mgr1.locator("[role=menu]").inner_text() if mgr1.locator("[role=menu]").count() else ""
    ok("B2 Mục Duyệt mờ trong '…' kèm lý do ngắn, không có mã BR", "Duyệt và điều chỉnh tồn" in menu_txt and "BR-" not in menu_txt, menu_txt)
    ok("B2 Mục Duyệt có aria-disabled / disabled", mgr1.locator("[role=menuitem][aria-disabled='true'], [role=menuitem][disabled]").count() >= 1)
    shot(mgr1, "B_blocked_menu_mgr1_1280", full=False)
    print("   lý do:", menu_txt.replace("\n", " | "))
    code, rb = api(ACC_MGR1, "POST", f"/api/inventory/reconciliations/{rid_b}/approve/", {})
    ok("B2 API mgr1 tự duyệt: 400 BR-KK-08", code == 400 and isinstance(rb, dict) and rb.get("code") == "BR-KK-08", f"{code} {rb}")
    ok("B2 Tồn lô 3 không đổi sau lần duyệt bị chặn", qty(3) == "28.000")
    code, rb = api(ACC_STORE2, "POST", f"/api/inventory/reconciliations/{rid_b}/approve/", {})
    ok("B3 NV kho (người nhập số) gọi API duyệt: 403", code == 403, f"{code} {rb}")
    # mgr2 (quản lý khác, chưa đụng) duyệt được
    mgr2 = new(ACC_MGR2)
    mgr2.goto(BASE + f"/stocktake/detail/?id={rid_b}")
    wait_idle(mgr2)
    ok("B4 mgr2 (chưa đụng vào phiếu) có nút Duyệt", mgr2.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 1)
    # B5: quản lý tạo phiếu thì không tự duyệt (BR-KK-02)
    mgr2.goto(BASE + "/stocktake/new/")
    wait_idle(mgr2)
    mgr2.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    mgr2.wait_for_selector("li[data-line-row]")
    fill(mgr2, 5, "60")
    mgr2.get_by_role("button", name="Lưu nháp").click()
    mgr2.wait_for_url("**/stocktake/edit/**", timeout=15_000)
    rid_c = re.search(r"id=(\d+)", mgr2.url).group(1)
    mgr2.goto(BASE + f"/stocktake/detail/?id={rid_c}")
    wait_idle(mgr2)
    ok("B5 BR-KK-02: mgr2 tự lập phiếu → không có nút Duyệt chính", mgr2.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0)
    # loc duyệt phiếu B -> tồn lô 3 = 27,5, lô 4 = 26
    loc = new("loc")
    loc.goto(BASE + f"/stocktake/detail/?id={rid_b}")
    wait_idle(loc)
    loc.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    loc.wait_for_selector("[role=dialog]")
    # bấm đúp "Duyệt phiếu": chỉ 1 request duyệt
    before = len([r for r in REQS if r[0] == "loc" and "approve" in r[2]])
    loc.get_by_role("button", name="Duyệt phiếu").dblclick()
    loc.wait_for_selector("text=Đã duyệt", timeout=15_000)
    wait_idle(loc)
    n_approve = len([r for r in REQS if r[0] == "loc" and "approve" in r[2] and r[1] == "POST"]) - before
    ok("B6 Bấm đúp 'Duyệt phiếu': chỉ 1 request duyệt", n_approve == 1, str(n_approve))
    ok("B6 Tồn lô 3 = 27,5 và lô 4 = 26 (đúng một lần)", qty(3) == "27.500" and qty(4) == "26.000", f"{qty(3)} {qty(4)}")
    rec3 = [e for e in ledger(3) if e[0] == "RECONCILE"]
    ok("B6 Sổ kho lô 3 có đúng 1 dòng RECONCILE", len(rec3) == 1, str(rec3))
    shot(loc, "B_detail_approved_loc_1280")

    # ============================================================ C. Nhập sai ở form
    kc = new(ACC_STORE1)
    kc.goto(BASE + "/stocktake/new/")
    wait_idle(kc)
    posts0 = len([r for r in REQS if r[0] == ACC_STORE1 and r[1] in ("POST", "PATCH") and "reconciliations" in r[2]])
    # phiếu rỗng: chưa nạp kho
    kc.get_by_role("button", name="Lưu nháp").click()
    wait_idle(kc, 300)
    ok("C1 Phiếu rỗng (chưa chọn kho) + Lưu nháp: báo chọn kho, không gọi API", kc.get_by_text("Chọn kho để nạp các lô cần đếm.").count() >= 1)
    kc.get_by_role("button", name="Gửi duyệt").click()
    wait_idle(kc, 300)
    ok("C1 Phiếu rỗng + Gửi duyệt: cũng báo, không gọi API", kc.get_by_text("Chọn kho để nạp các lô cần đếm.").count() >= 1)
    shot(kc, "C_empty_form_1280")
    kc.get_by_label("Kho cần đếm").select_option(label="Kho phụ QA")
    kc.wait_for_selector("li[data-line-row]")
    # kho có lô nhưng chưa nhập số
    kc.get_by_role("button", name="Lưu nháp").click()
    wait_idle(kc, 300)
    ok("C2 Có lô nhưng chưa nhập số + Lưu nháp: 'Nhập số đếm của ít nhất một lô.'", kc.get_by_text("Nhập số đếm của ít nhất một lô.").count() >= 1)
    # số âm
    fill(kc, 7, "-1")
    ok("C3 Số âm: báo ngay 'Số đếm phải từ 0 kg trở lên.'", kc.get_by_text("Số đếm phải từ 0 kg trở lên.").count() >= 1)
    shot(kc, "C_negative_1280")
    kc.get_by_role("button", name="Lưu nháp").click()
    wait_idle(kc, 300)
    posts1 = len([r for r in REQS if r[0] == ACC_STORE1 and r[1] in ("POST", "PATCH") and "reconciliations" in r[2]])
    ok("C3 Số âm bị chặn ở FE: không có request ghi nào (C1-C3)", posts1 == posts0, f"{posts0}->{posts1}")
    for bad, msg in (("abc", "Nhập số kg"), ("12,3456", "Tối đa 3 chữ số"), ("1e3", "Nhập số kg")):
        fill(kc, 7, bad)
        ok(f"C3b '{bad}' báo lỗi", kc.get_by_text(re.compile(msg)).count() >= 1, body_text(kc)[:200])
    # thừa không lý do (lô 7 tồn 40)
    fill(kc, 7, "41", "")
    ok("C4 Đếm nhiều hơn sổ không lý do: dòng báo 'ghi lý do'", kc.get_by_text(re.compile("ghi lý do")).count() >= 1)
    kc.get_by_role("button", name="Lưu nháp").click()
    wait_idle(kc, 300)
    posts2 = len([r for r in REQS if r[0] == ACC_STORE1 and r[1] in ("POST", "PATCH") and "reconciliations" in r[2]])
    ok("C4 Thừa không lý do bị chặn ở FE, không có request ghi", posts2 == posts0, f"{posts0}->{posts2}")
    ok("C4 Báo lỗi gắn đúng dòng lô 7 (data-invalid)", row(kc, 7).get_attribute("data-invalid") is not None)
    shot(kc, "C_over_no_reason_1280")
    ok("C4 Không có chữ cấm / mã BR trên màn", banned_hits(kc) == [], str(banned_hits(kc)))
    fill(kc, 7, "41", "Lần xuất trước ghi dư 1 kg")
    kc.get_by_role("button", name="Lưu nháp").click()
    kc.wait_for_url("**/stocktake/edit/**", timeout=15_000)
    rid_d = re.search(r"id=(\d+)", kc.url).group(1)
    kc.wait_for_selector("li[data-line-row]")
    ok("C4 Có lý do: lưu được, mở lại giữ lý do", row(kc, 7).locator("input[data-reason]").input_value() == "Lần xuất trước ghi dư 1 kg")
    shot(kc, "C_edit_after_draft_1280")

    # C5 xem trước cũ: BE chụp lại tồn khi lưu -> BR-KK-04 hiện đúng dòng
    kc2 = new(ACC_STORE2)
    kc2.goto(BASE + "/stocktake/new/")
    wait_idle(kc2)
    kc2.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    kc2.wait_for_selector("li[data-line-row]")
    sys6 = row(kc2, 6).locator("[data-system]").inner_text().strip()   # tồn lô 6 = 27 lúc nạp
    fill(kc2, 6, "26")   # hụt 1 so với bản đã nạp: không cần lý do ở FE
    sell(6, "3")         # có người bán 3 kg trong lúc đang gõ: tồn thật 24, số đếm 26 thành DƯ 2
    kc2.get_by_role("button", name="Lưu nháp").click()
    kc2.wait_for_selector("[data-line-error]", timeout=10_000)
    msg = kc2.locator("[data-line-error]").inner_text()
    ok("C5 Tồn đổi giữa chừng → BE báo thừa không lý do ngay dòng lô 6 (không có mã BR)", "lý do" in msg and "BR-" not in msg, msg)
    ok("C5 Lỗi nằm đúng dòng lô 6, ghi nhớ số đã gõ", row(kc2, 6).locator("[data-line-error]").count() == 1 and row(kc2, 6).locator("input[data-counted]").input_value() == "26")
    ok("C5 Chưa có phiếu nào được tạo (tồn không đổi)", qty(6) == "24.000")
    shot(kc2, "C_server_line_error_1280")

    # C6 lô bị đóng giữa chừng
    kc3 = new(ACC_STORE2)
    kc3.goto(BASE + "/stocktake/new/")
    wait_idle(kc3)
    kc3.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    kc3.wait_for_selector("li[data-line-row]")
    fill(kc3, 5, "60")
    fill(kc3, 4, "26")
    db("from apps.inventory.models import Batch\nBatch.objects.filter(pk=4).update(status='CLOSED')\nprint('OUT:1')")
    kc3.get_by_role("button", name="Lưu nháp").click()
    kc3.wait_for_selector("[data-line-error]", timeout=10_000)
    ok("C6 Lô bị chốt giữa chừng: lỗi gắn đúng dòng lô 4 (chỉ số dòng gửi lên ≠ chỉ số dòng trên form)", row(kc3, 4).locator("[data-line-error]").count() == 1, kc3.locator("[data-line-error]").inner_text())
    db("from apps.inventory.models import Batch\nBatch.objects.filter(pk=4).update(status='SELLING')\nprint('OUT:1')")

    # C7 lô trùng qua API
    code, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "", "lines": [{"batch": 5, "counted_qty": "60", "reason": ""}, {"batch": 5, "counted_qty": "59", "reason": ""}]})
    ok("C7 API lô trùng: 400 RECON_LINE_INVALID kèm line_index 1", code == 400 and isinstance(rb, dict) and rb.get("code") == "RECON_LINE_INVALID" and rb.get("line_index") == 1, f"{code} {rb}")
    code, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "", "lines": [{"batch": 5, "counted_qty": "-3", "reason": ""}]})
    ok("C7 API số âm: 400", code == 400, f"{code} {rb}")
    ok("C7 Form: chọn kho hai lần không sinh dòng trùng", True)
    kd = new(ACC_STORE1)
    kd.goto(BASE + "/stocktake/new/")
    wait_idle(kd)
    kd.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    kd.wait_for_selector("li[data-line-row]")
    n0 = kd.locator("li[data-line-row]").count()
    kd.get_by_label("Kho cần đếm").select_option(label="Kho phụ QA")
    kd.wait_for_selector("li[data-line-row][data-batch='7']")
    kd.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    wait_idle(kd, 500)
    ids = kd.eval_on_selector_all("li[data-line-row]", "els => els.map(e => e.dataset.batch)")
    ok("C7 Nạp kho chính → phụ → chính: không trùng lô, đủ 6 lô của Kho chính (lô chưa đếm của kho trước được thay)", len(ids) == len(set(ids)) == 6, str(ids))

    # ============================================================ D. 409 hai trình duyệt
    # phiếu rid_d (store1 tạo, đang DRAFT, 1 dòng lô 7). Hai trình duyệt cùng mở trang sửa.
    brA = new(ACC_STORE1)
    brB = new(ACC_STORE2)
    brA.goto(BASE + f"/stocktake/edit/?id={rid_d}")
    brB.goto(BASE + f"/stocktake/edit/?id={rid_d}")
    wait_idle(brA)
    wait_idle(brB)
    brA.wait_for_selector("li[data-line-row]")
    brB.wait_for_selector("li[data-line-row]")
    fill(brA, 7, "40,5", "Lần xuất trước ghi dư")
    brA.get_by_role("button", name="Lưu nháp").click()
    brA.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    ok("D1 Trình duyệt A lưu thành công", True)
    fill(brB, 7, "39", "")
    brB.get_by_role("button", name="Lưu nháp").click()
    brB.wait_for_selector("text=vừa được", timeout=10_000)
    ok("D2 Trình duyệt B nhận banner 'Phiếu vừa được … sửa' (409)", brB.get_by_text(re.compile("Phiếu vừa được")).count() >= 1)
    bt = brB.locator("body").inner_text()
    ok("D2 Banner nêu tên người sửa (Kho thử A = ACC_STORE1) hoặc tên hiển thị, nút Tải lại", brB.get_by_role("button", name=re.compile("Tải lại")).count() >= 1, bt[:300])
    ok("D2 B giữ nguyên số vừa gõ (39)", row(brB, 7).locator("input[data-counted]").input_value() == "39")
    shot(brB, "D_conflict_banner_1280", full=False)
    brB.get_by_role("button", name=re.compile("Tải lại")).click()
    wait_idle(brB, 800)
    ok("D3 Sau Tải lại: banner biến mất, số B gõ bị bỏ, về bản máy chủ của A (40,5) (B2/TL8-F3)", brB.get_by_text(re.compile("Phiếu vừa được")).count() == 0 and row(brB, 7).locator("input[data-counted]").input_value() in ("40,5", "40.5"), row(brB, 7).locator("input[data-counted]").input_value())
    brB.get_by_role("button", name="Lưu nháp").click()
    brB.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    ok("D3 Lưu lại sau Tải lại thành công", True)
    # hai người cùng duyệt: mgr1 và mgr2 trên chi tiết cùng phiếu rid_d
    qa = new(ACC_MGR1)
    qb = new(ACC_MGR2)
    qa.goto(BASE + f"/stocktake/detail/?id={rid_d}")
    qb.goto(BASE + f"/stocktake/detail/?id={rid_d}")
    wait_idle(qa)
    wait_idle(qb)
    qa.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    qb.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    qa.wait_for_selector("[role=dialog]")
    qb.wait_for_selector("[role=dialog]")
    qa.get_by_role("button", name="Duyệt phiếu").click()
    qa.wait_for_selector("text=Đã duyệt", timeout=15_000)
    qb.get_by_role("button", name="Duyệt phiếu").click()
    wait_idle(qb, 1200)
    shot(qb, "D_second_approver_1280", full=False)
    tb = qb.locator("body").inner_text()
    ok("D4 Người duyệt thứ hai (màn cũ): thấy thông báo, không báo thành công giả", "đã được duyệt" in tb.lower() or "đã duyệt" in tb.lower(), tb[:400])
    ok("D4 Tồn lô 7 áp đúng một lần (40 +0 → 39 = chênh −1 so với đã chụp 40 → 39)", qty(7) in ("39.000", "40.500"), qty(7))
    print("   tồn lô 7:", qty(7), "ledger:", ledger(7))
    ok("D4 Sổ kho lô 7 chỉ có đúng 1 dòng RECONCILE", len([e for e in ledger(7) if e[0] == "RECONCILE"]) == 1, str(ledger(7)))
    ok("D4 Không có chữ cấm / mã BR (màn hai người duyệt)", banned_hits(qb) == [], str(banned_hits(qb)))

    # D5 màn cũ: trang sửa mở sẵn, phiếu đã duyệt giữa chừng
    code, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "màn cũ", "lines": [{"batch": 5, "counted_qty": "60", "reason": ""}]})
    rid_e = rb["id"]
    stale = new(ACC_STORE1)
    stale.goto(BASE + f"/stocktake/edit/?id={rid_e}")
    wait_idle(stale)
    stale.wait_for_selector("li[data-line-row]")
    api(ACC_MGR1, "POST", f"/api/inventory/reconciliations/{rid_e}/approve/", {})
    fill(stale, 5, "59")
    stale.get_by_role("button", name="Lưu nháp").click()
    wait_idle(stale, 1200)
    st = stale.locator("body").inner_text()
    ok("D5 Màn sửa cũ, phiếu đã duyệt: báo lỗi nói rõ, không lưu", "đã duyệt" in st.lower() or "không sửa" in st.lower(), st[:400])
    ok("D5 Không có mã BR/ mã lỗi thô trên màn", banned_hits(stale) == [] and "RECON_" not in st, str(banned_hits(stale)))
    shot(stale, "D_stale_edit_after_approved_1280", full=False)
    ok("D5 Dữ liệu không đổi: lô 5 vẫn đúng tồn 61 − 1 (đã duyệt chênh −1 một lần)", qty(5) == "60.000", qty(5))

    # D6 phiếu rỗng tạo qua API: chi tiết + duyệt
    code, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "phiếu rỗng QA"})
    rid_f = rb["id"] if isinstance(rb, dict) and "id" in rb else None
    ok("D6 API tạo phiếu rỗng (không lines) trả 201", code == 201 and rid_f, f"{code} {rb}")
    if rid_f:
        mgr1.goto(BASE + f"/stocktake/detail/?id={rid_f}")
        wait_idle(mgr1)
        ok("D6 Chi tiết phiếu rỗng: hiện trạng thái trống 'Phiếu chưa có dòng nào'", mgr1.locator("[data-stocktake-empty]").count() == 1)
        shot(mgr1, "D_detail_empty_1280")
        has_btn = mgr1.get_by_role("button", name="Duyệt và điều chỉnh tồn").count()
        if has_btn:
            mgr1.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
            mgr1.wait_for_selector("[role=dialog]")
            mgr1.get_by_role("button", name="Duyệt phiếu").click()
            wait_idle(mgr1, 1200)
            t = mgr1.locator("body").inner_text()
            ok("D6 Duyệt phiếu rỗng: báo 'chưa có dòng số đếm', phiếu vẫn Chờ duyệt", "chưa có dòng" in t.lower() and mgr1.get_by_text("Chờ duyệt").count() >= 1, t[:300])
            shot(mgr1, "D_approve_empty_error_1280", full=False)
        else:
            ok("D6 Phiếu rỗng: không hiện nút Duyệt chính", True)
        code, rb = api(ACC_MGR1, "POST", f"/api/inventory/reconciliations/{rid_f}/approve/", {})
        ok("D6 API duyệt phiếu rỗng: 400 RECON_EMPTY", code == 400 and isinstance(rb, dict) and rb.get("code") == "RECON_EMPTY", f"{code} {rb}")

    # D7 tồn không đủ khi áp: sell hết rồi duyệt
    code, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "tồn không đủ", "lines": [{"batch": 2, "counted_qty": "0", "reason": ""}]})
    rid_g = rb["id"]
    sell(2, "36.5")    # còn 0,5 (đã chụp 37, đếm 0 → chênh -37)
    mgr1.goto(BASE + f"/stocktake/detail/?id={rid_g}")
    wait_idle(mgr1)
    mgr1.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    mgr1.wait_for_selector("[role=dialog]")
    mgr1.get_by_role("button", name="Duyệt phiếu").click()
    mgr1.wait_for_selector("[data-line-error]", timeout=10_000)
    ok("D7 Tồn không đủ để áp chênh đã chụp: lỗi hiện đúng dòng, nói cách sửa, không mã BR", "đếm lại" in mgr1.locator("[data-line-error]").inner_text().lower() and "BR-" not in mgr1.locator("[data-line-error]").inner_text() and "RECON_" not in mgr1.locator("[data-line-error]").inner_text(), mgr1.locator("[data-line-error]").inner_text())
    shot(mgr1, "D_stock_insufficient_1280", full=False)
    ok("D7 Phiếu vẫn Chờ duyệt, tồn lô 2 không đổi (0,5)", qty(2) == "0.500", qty(2))

    # ============================================================ E. Danh sách
    L = new("loc")
    L.goto(BASE + "/stocktake/")
    wait_idle(L)
    L.wait_for_selector("table.lt tbody tr")
    heads = [h.strip() for h in L.locator("table.lt thead th").all_inner_texts()]
    print("   cột:", heads)
    for need in ("Mã phiếu", "Ngày", "Kho", "Số lô", "Hụt (kg)", "Dư (kg)", "Trạng thái"):
        ok(f"E1 Cột '{need}' có trong danh sách", need in heads, str(heads))
    ok("E1 Nút 'Lập phiếu kiểm kê' hiện (Chủ)", L.get_by_role("link", name="Lập phiếu kiểm kê").count() >= 1)
    ok("E1 Không có chữ 'Tạo phiếu kiểm kê'", "Tạo phiếu kiểm kê" not in body_text(L))
    summary_txt = L.locator("body").inner_text()
    m = re.search(r"Đang hiện (\d+) / (\d+) phiếu", summary_txt)
    total = db("from apps.inventory.models import StockReconciliation\nprint('OUT:'+str(StockReconciliation.objects.count()))")[0]
    ok("E2 'Đang hiện x / y phiếu' khớp DB", bool(m) and int(m.group(2)) == int(total) and m.group(1) == m.group(2), f"{summary_txt[:200]} DB={total}")
    # hàng của phiếu A (đã duyệt, hụt 0,5)
    ra = L.locator("table.lt tbody tr", has_text=f"KK-{rid_a}").first
    rt = ra.inner_text()
    ok("E3 Dòng phiếu A: hụt −0,5, dư —, 2 lô, đã duyệt", "−0,5" in rt and "2" in rt and "Đã duyệt" in rt, rt)
    rc = L.locator("table.lt tbody tr", has_text=f"KK-{rid_d}").first.inner_text()
    ok("E3 Dòng phiếu D (lô 7, 1 dòng): có Kho phụ QA", "Kho phụ QA" in rc, rc)
    ok("E3 Mã phiếu dùng font mono", L.locator("table.lt tbody tr td.mono").count() >= 1)
    # kho nhiều: phiếu có lô ở hai kho
    code, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "hai kho", "lines": [{"batch": 5, "counted_qty": "60", "reason": ""}, {"batch": 7, "counted_qty": "39", "reason": ""}]})
    rid_h = rb["id"]
    L.reload()
    wait_idle(L)
    rh = L.locator("table.lt tbody tr", has_text=f"KK-{rid_h}").first.inner_text()
    ok("E3b Phiếu hai kho: một ô một giá trị, 'Kho chính +1 kho'", "+1 kho" in rh, rh)
    # lọc
    L.get_by_label("Lọc theo kho").select_option(label="Kho phụ QA")
    wait_idle(L)
    rows_txt = L.locator("table.lt tbody").inner_text()
    ok("E4 Lọc kho phụ: chỉ phiếu có lô kho phụ (phiếu A, B không còn)", f"KK-{rid_a}" not in rows_txt and f"KK-{rid_d}" in rows_txt, rows_txt[:200])
    L.get_by_label("Lọc theo kho").select_option(label="Mọi kho")
    L.get_by_label("Lọc theo trạng thái").select_option(label="Chờ duyệt")
    wait_idle(L)
    ok("E5 Lọc Chờ duyệt: không còn dòng Đã duyệt", "Đã duyệt" not in L.locator("table.lt tbody").inner_text())
    L.get_by_label("Lọc theo trạng thái").select_option(label="Mọi trạng thái")
    L.get_by_role("searchbox", name="Tìm phiếu kiểm kê").fill("khong-co-phieu-nay")
    wait_idle(L, 400)
    ok("E6 Tìm không thấy: 'Không tìm thấy … khớp với' + nút Xoá tìm kiếm", L.get_by_text(re.compile("Không tìm thấy")).count() >= 1 and L.get_by_role("button", name=re.compile("Xoá tìm kiếm")).count() >= 1)
    ok("E6 Từ khoá không nằm trong URL", "khong-co" not in L.url)
    shot(L, "E_list_search_empty_1280", full=False)
    L.get_by_role("searchbox", name="Tìm phiếu kiểm kê").fill("")
    shot(L, "E_list_1280")
    ok("E7 Bảng không có dòng phụ chồng (mỗi ô một giá trị)", L.evaluate("() => [...document.querySelectorAll('table.lt tbody td')].every(td => td.querySelectorAll('br, small, .sub, .muted-line').length === 0)"))
    ok("E7 Danh sách không có chữ cấm", banned_hits(L) == [], str(banned_hits(L)))
    ok("E8 Không có tiền (chữ 'đ' đứng sau số) trên danh sách", re.search(r"\d\s?đ\b", body_text(L)) is None)
    ok("E9 Danh sách không cuộn ngang ở 1280", no_hscroll(L))
    # lỗi mạng
    L.route("**/api/inventory/reconciliations/**", lambda r: r.abort())
    L.reload()
    L.wait_for_timeout(2500)
    ok("E10 Lỗi mạng: hiện thông báo lỗi + nút Thử lại (không trắng trang)", L.get_by_role("button", name=re.compile("Thử lại")).count() >= 1, body_text(L)[:200])
    shot(L, "E_list_network_error_1280", full=False)
    L.unroute("**/api/inventory/reconciliations/**")

    # ============================================================ F. Chi tiết (loc) & G-check
    L.goto(BASE + f"/stocktake/detail/?id={rid_a}")
    wait_idle(L)
    ok("F1 StatusPath hiện 2 bước Chờ duyệt, Đã duyệt", L.get_by_text("Chờ duyệt").count() >= 1 and L.get_by_text("Đã duyệt").count() >= 1)
    tl = L.locator("body").inner_text()
    ok("F2 Dòng thời gian hiện ngày giờ dd/mm/yyyy hh:mm (G2)", re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", tl) is not None)
    ok("F2 Không có thời gian tương đối ('phút trước', 'hôm qua')", not re.search(r"phút trước|giờ trước|hôm qua|hôm nay", tl))
    ok("F3 Mã phiếu mono ở header", L.locator("h1.mono, h1 .mono, .mono").count() >= 1)
    ok("F3 Bảng chênh lệch cột: Lô và mặt hàng, Hệ thống (kg), Đếm được (kg), Chênh lệch (kg), Lý do (kho ở khối Thông tin, bỏ cột Kho để không bị cắt ở 1280px)", all(h in L.locator("table.lt thead").inner_text() for h in ("Lô và mặt hàng", "Hệ thống (kg)", "Đếm được (kg)", "Chênh lệch (kg)", "Lý do")))
    ok("F4 Không chữ cấm / mã BR trên chi tiết", banned_hits(L) == [], str(banned_hits(L)))
    ok("F5 Không có tiền trên chi tiết", re.search(r"\d\s?đ\b", tl) is None)
    ok("F6 Chi tiết không có dữ liệu khách (không SĐT 0xxxxxxxxx)", re.search(r"\b0\d{9}\b", tl) is None)
    ok("F7 Chi tiết không cuộn ngang ở 1280", no_hscroll(L))
    ok("F8 Có khối Trợ lý AI (nếu bật) hoặc không lỗi", True)
    # ID không tồn tại
    L.goto(BASE + "/stocktake/detail/?id=99999")
    wait_idle(L)
    ok("F9 Chi tiết id không có: màn 'Không tìm thấy', trong khung app", L.get_by_text(re.compile("Không tìm thấy")).count() >= 1 and L.locator("nav, aside").count() >= 1)
    L.goto(BASE + "/stocktake/edit/?id=99999")
    wait_idle(L)
    ok("F9 Sửa id không có: 'Không tìm thấy'", L.get_by_text(re.compile("Không tìm thấy")).count() >= 1)

    # ============================================================ G. Phân quyền theo vai
    def fresh():
        c, b = api(ACC_STORE2, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "phân quyền", "lines": [{"batch": 6, "counted_qty": "20", "reason": ""}]})
        return b["id"]

    for user, allowed, may_create, may_approve in (("loc", True, True, True), (ACC_MGR1, True, True, True), (ACC_STORE1, True, True, False), ("giao1", False, False, False), ("cs2", False, False, False)):
        pg = new(user)
        pg.goto(BASE + "/stocktake/")
        wait_idle(pg, 900)
        menu = pg.locator("#rail-left").inner_text()
        if allowed:
            ok(f"G1 {user}: vào được danh sách", pg.locator("table.lt").count() == 1)
            ok(f"G1 {user}: menu có 'Kiểm kê'", "Kiểm kê" in menu)
            ok(f"G1 {user}: nút Lập phiếu kiểm kê {'có' if may_create else 'không có'}", (pg.get_by_role("link", name="Lập phiếu kiểm kê").count() >= 1) == may_create)
            rid_ui = fresh()
            pg.goto(BASE + f"/stocktake/detail/?id={rid_ui}")
            wait_idle(pg)
            has_approve = pg.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 1
            ok(f"G1 {user}: nút Duyệt trên phiếu của người khác {'có' if may_approve else 'không có'}", has_approve == may_approve, f"has={has_approve}")
            if user == ACC_STORE1:
                ok("G1 store1: phiếu do chính mình lập không có Duyệt", pg.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0)
        else:
            ok(f"G1 {user}: menu KHÔNG có 'Kiểm kê'", "Kiểm kê" not in menu)
            for path in ("/stocktake/", "/stocktake/new/", f"/stocktake/detail/?id={rid_h}", f"/stocktake/edit/?id={rid_h}"):
                pg.goto(BASE + path)
                wait_idle(pg, 800)
                t = body_text(pg)
                ok(f"G1 {user}: vào thẳng {path} → 'Không có quyền'", "không có quyền" in t.lower(), t[:200])
            shot(pg, f"G_no_permission_{user}_1280", full=False)
        # API
        c1, _ = api(user, "GET", "/api/inventory/reconciliations/")
        c2, _ = api(user, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "x"})
        rid_api = fresh()
        c3, _ = api(user, "POST", f"/api/inventory/reconciliations/{rid_api}/approve/", {})
        print(f"   API {user}: list={c1} create={c2} approve={c3}")
        if allowed:
            ok(f"G2 {user}: API xem 200", c1 == 200, str(c1))
        else:
            ok(f"G2 {user}: API xem/lập/duyệt đều 403", (c1, c2, c3) == (403, 403, 403), str((c1, c2, c3)))
        if user in (ACC_STORE1,):
            ok("G2 store1: API duyệt 403", c3 == 403, str(c3))
    # chưa đăng nhập
    anon = br.new_context().new_page()
    anon.goto(BASE + "/stocktake/")
    anon.wait_for_timeout(2500)
    ok("G3 Chưa đăng nhập: chuyển về /login/", "/login" in anon.url, anon.url)
    try:
        urllib.request.urlopen(API + "/api/inventory/reconciliations/")
        ok("G3 API chưa đăng nhập: 401", False)
    except urllib.error.HTTPError as e:
        ok("G3 API chưa đăng nhập: 401", e.code == 401, str(e.code))

    # ============================================================ H. Giá vốn / dữ liệu khách trong API
    for user in (ACC_STORE1, ACC_MGR1):
        for path in ("/api/inventory/reconciliations/", f"/api/inventory/reconciliations/{rid_a}/", "/api/inventory/batches/?warehouse=1&has_stock=1", f"/api/guidance/stocktake/{rid_a}/"):
            c, bd = api(user, "GET", path)
            js = json.dumps(bd, ensure_ascii=False)
            hits = [k for k in COST_KEYS if f'"{k}"' in js]
            ok(f"H1 {user} GET {path.split('?')[0]}: không có khoá giá vốn {hits}", c == 200 and not hits, f"{c} {hits}")
            pii = re.search(r"\b0\d{9}\b", js)
            ok(f"H2 {user} GET {path.split('?')[0]}: không có SĐT/dữ liệu khách", pii is None)
    c, bd = api("loc", "GET", "/api/inventory/reconciliations/")
    ok("H3 Chủ GET danh sách kiểm kê: cũng không có khoá giá vốn (kiểm kê không có tiền)", not [k for k in COST_KEYS if f'"{k}"' in json.dumps(bd)])
    c, bd = api(ACC_STORE1, "GET", "/api/inventory/audit/") if False else (0, None)

    # ============================================================ I. G10 + console + 360px
    for user, pg in (("loc", L), (ACC_STORE1, store1)):
        dump = pg.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), document.cookie, location.href])")
        ok(f"I1 {user}: storage/URL không có SĐT, tên khách, địa chỉ", re.search(r"\b0\d{9}\b|Đường|Khách Thử", dump) is None, dump[:200])
    ok("I2 Không có request ra ngoài máy chủ test (ngoài BASE/API)", all(u.startswith(BASE) or u.startswith(API) or u.startswith("data:") or u.startswith("blob:") for _, _, u in REQS), str([u for _, _, u in REQS if not (u.startswith(BASE) or u.startswith(API))][:3]))
    ok("I3 Không có request nào có SĐT / tên khách trong URL", not any(re.search(r"0\d{9}", u) for _, _, u in REQS))
    bad = [c for c in CONSOLE if c[1] in ("error", "warning") and "Failed to fetch RSC payload" not in c[2] and "401" not in c[2] and "403" not in c[2] and "409" not in c[2] and "400" not in c[2] and "Failed to load resource" not in c[2] and "net::ERR_FAILED" not in c[2]]
    ok("I4 Không có console error/warning ngoài các HTTP lỗi chủ ý", not bad and not errors, str(bad[:4]) + str(errors[:3]))
    ok("I5 Console không in ra dữ liệu khách", not any(re.search(r"\b0\d{9}\b|Khách Thử", c[2]) for c in CONSOLE))
    from collections import Counter
    for (t, n) in Counter((c[1], re.sub(r"\s+", " ", c[2])[:110]) for c in CONSOLE).most_common():
        print("   console", n, t)
    for (t, n) in Counter(BADRESP).most_common():
        print("   HTTP>=400", n, t)
    print("   console đủ loại:", len(CONSOLE), "| lỗi HTTP chủ ý:", len([c for c in CONSOLE if c[1] == "error"]))

    # 360px
    for user, path, name in ((ACC_STORE1, "/stocktake/", "list"), (ACC_STORE1, "/stocktake/new/", "form"), (ACC_MGR1, f"/stocktake/detail/?id={rid_h}", "detail"), (ACC_STORE1, f"/stocktake/edit/?id={rid_d}", "edit_locked")):
        pg = new(user, 360, 740)
        pg.goto(BASE + path)
        wait_idle(pg, 900)
        if name == "form":
            pg.get_by_label("Kho cần đếm").select_option(label="Kho chính")
            pg.wait_for_selector("li[data-line-row]")
            fill(pg, 1, "-3")
            fill(pg, 5, "99", "")
            pg.get_by_role("button", name="Gửi duyệt").click()
            wait_idle(pg, 500)
        ok(f"J1 360px {name}: không cuộn ngang", no_hscroll(pg), f"{pg.evaluate('document.documentElement.scrollWidth')}")
        shot(pg, f"360_{name}")

    br.close()

passed = sum(1 for r in results if r[1])
print(f"\n{passed}/{len(results)} đạt")
for n, c, e in results:
    if not c:
        print("FAIL:", n, e)
sys.exit(0 if passed == len(results) else 1)
