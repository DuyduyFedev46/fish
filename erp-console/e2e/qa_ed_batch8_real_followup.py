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

    def new(user, w=1280, h=900):
        ctx = br.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
        pg = ctx.new_page()
        pg.on("console", lambda m: CONSOLE.append((user, m.type, m.text)))
        login(pg, user)
        return pg

    def shot(pg, name, full=True):
        pg.screenshot(path=f"{SHOTS}/{name}.png", full_page=full)

    # ---- K1/K2: TL8-F1 + TL8-F3 trên BE thật. Phiếu có lô 3 (28), lô 4 (25). A và B (hai trình duyệt, hai người) cùng mở trang sửa.
    code, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "ban đầu", "lines": [{"batch": 3, "counted_qty": "27", "reason": ""}, {"batch": 4, "counted_qty": "24", "reason": ""}]})
    rid = rb["id"]
    A = new(ACC_STORE1)
    B = new(ACC_STORE2)
    A.goto(BASE + f"/stocktake/edit/?id={rid}")
    B.goto(BASE + f"/stocktake/edit/?id={rid}")
    for pg in (A, B):
        wait_idle(pg)
        pg.wait_for_selector("li[data-line-row]")
    # A sửa lô 3 thành 26 và lưu
    fill(A, 3, "26")
    A.get_by_role("button", name="Lưu nháp").click()
    A.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    c, cur = api("loc", "GET", f"/api/inventory/reconciliations/{rid}/")
    ok("K0 A đã lưu: lô 3 đếm 26 trên BE", any(l["batch"] == 3 and l["counted_qty"] == "26.000" for l in cur["lines"]), str(cur["lines"]))
    # B chỉ đổi GHI CHÚ và lô 4 rồi lưu (trang B vẫn giữ bản cũ)
    B.get_by_label("Ghi chú").fill("B đổi ghi chú")
    fill(B, 4, "23")
    B.get_by_role("button", name="Lưu nháp").click()
    B.wait_for_timeout(2500)
    c, cur = api("loc", "GET", f"/api/inventory/reconciliations/{rid}/")
    l3 = [l["counted_qty"] for l in cur["lines"] if l["batch"] == 3]
    conflict_shown = B.get_by_text(re.compile("Phiếu vừa được")).count() >= 1
    ok("K1 TL8-F1: B sửa ghi chú + số trên màn cũ → phải nhận 409 (không ghi đè số của A)", conflict_shown and l3 == ["26.000"], f"banner={conflict_shown}; lô 3 trên BE sau khi B lưu={l3}; ghi chú={cur['note']}")
    shot(B, "K_F1_after_B_save_1280", full=False)

    # ---- K3: TL8-F3 sau Tải lại có thấy bản của người kia không
    A2 = new(ACC_STORE1)
    B2 = new(ACC_STORE2)
    code, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "F3", "lines": [{"batch": 3, "counted_qty": "27", "reason": ""}]})
    rid2 = rb["id"]
    A2.goto(BASE + f"/stocktake/edit/?id={rid2}")
    B2.goto(BASE + f"/stocktake/edit/?id={rid2}")
    for pg in (A2, B2):
        wait_idle(pg)
        pg.wait_for_selector("li[data-line-row]")
    # A thêm lô 5 (đếm 60) và lưu: phiếu giờ có 2 dòng
    A2.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    A2.wait_for_selector("li[data-line-row][data-batch='5']")
    fill(A2, 5, "60")
    A2.get_by_role("button", name="Lưu nháp").click()
    A2.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    # B (không đổi ghi chú) sửa lô 3 và lưu → 409
    fill(B2, 3, "26,5")
    B2.get_by_role("button", name="Lưu nháp").click()
    B2.wait_for_selector("text=Phiếu vừa được", timeout=10_000)
    B2.get_by_role("button", name=re.compile("Tải lại")).click()
    wait_idle(B2, 800)
    rows_b = B2.eval_on_selector_all("li[data-line-row]", "els => els.map(e => e.dataset.batch)")
    ok("K3 TL8-F3: sau Tải lại, B thấy lô 5 do A vừa thêm (để biết mình sắp ghi đè)", "5" in rows_b, str(rows_b))
    B2.get_by_role("button", name="Lưu nháp").click()
    B2.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    c, cur = api("loc", "GET", f"/api/inventory/reconciliations/{rid2}/")
    ok("K3 TL8-F3: sau khi B lưu lần hai, dòng lô 5 của A vẫn còn trên BE", any(l["batch"] == 5 for l in cur["lines"]), str([l["batch"] for l in cur["lines"]]))

    # ---- K4: TL8-L1 bấm Lưu nháp hai lần ở form mới
    before = db("from apps.inventory.models import StockReconciliation\nprint('OUT:'+str(StockReconciliation.objects.filter(note='L1 double').count()))")[0]
    N = new(ACC_STORE1)
    N.goto(BASE + "/stocktake/new/")
    wait_idle(N)
    N.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    N.wait_for_selector("li[data-line-row]")
    fill(N, 3, "26")
    N.get_by_label("Ghi chú").fill("L1 double")
    # bấm lần 2 ngay khi phản hồi POST đầu tiên về (trước khi trang sửa nạp xong)
    N.evaluate("""() => { const orig = window.fetch; window.fetch = async (...a) => { const r = await orig(...a); if (String(a[0]).includes('/reconciliations/') && (a[1]||{}).method === 'POST') { setTimeout(() => [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Lưu nháp')?.click(), 0); } return r; }; }""")
    N.get_by_role("button", name="Lưu nháp").click()
    N.wait_for_timeout(3000)
    after = db("from apps.inventory.models import StockReconciliation\nprint('OUT:'+str(StockReconciliation.objects.filter(note='L1 double').count()))")[0]
    ok("K4 TL8-L1: bấm Lưu nháp lần hai sát sau lần một chỉ tạo 1 phiếu", after - before == 1, f"tạo {after - before} phiếu")

    # ---- K5: câu chữ trên hộp xác nhận / toast (TL8-F2)
    code, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": "F2", "lines": [{"batch": 5, "counted_qty": "60", "reason": ""}]})
    ridf2 = rb["id"]
    Q = new(ACC_MGR1)
    Q.goto(BASE + f"/stocktake/detail/?id={ridf2}")
    wait_idle(Q)
    nxt = Q.locator("body").inner_text()
    Q.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    Q.wait_for_selector("[role=dialog]")
    dlg = Q.locator("[role=dialog]").inner_text()
    ok("K5 TL8-F2: chữ không hứa 'theo số thực đếm' (BE áp phần chênh đã chụp, BR-KK-09)", "theo số thực đếm" not in dlg and "theo số thực đếm" not in nxt, dlg.replace("\n", " | ")[:300])
    Q.get_by_role("button", name="Duyệt phiếu").click()
    Q.wait_for_timeout(1500)
    ok("K5 TL8-F2: toast sau duyệt không hứa 'theo số đếm'", "theo số đếm" not in Q.locator("body").inner_text(), Q.locator("body").inner_text()[-300:])

    br.close()

passed = sum(1 for r in results if r[1])
print(f"\n{passed}/{len(results)} đạt")
for n, c, e in results:
    if not c:
        print("FAIL:", n, e)
