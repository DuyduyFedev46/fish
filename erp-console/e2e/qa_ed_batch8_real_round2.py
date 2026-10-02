"""Vòng 2: hai người cùng sửa (ghi chú, ngày, dòng), Tải lại, chữ BR-KK-09. QA độc lập Lô 8 FE (Kiểm kê, ED-28) trên BE THẬT (Django 8140 + ERP build MOCK=0 phục vụ tĩnh ở 3202).
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

    def shot(pg, name, full=False):
        pg.screenshot(path=f"{SHOTS}/{name}.png", full_page=full)

    def make_recon(lines, note="r2"):
        c, rb = api(ACC_STORE1, "POST", "/api/inventory/reconciliations/", {"count_date": "2026-10-02", "note": note, "lines": lines})
        return rb["id"]

    def get(rid):
        return api("loc", "GET", f"/api/inventory/reconciliations/{rid}/")[1]

    def open_two(rid, u1=ACC_STORE1, u2=ACC_STORE2):
        A, B = new(u1), new(u2)
        for pg in (A, B):
            pg.goto(BASE + f"/stocktake/edit/?id={rid}")
            wait_idle(pg)
            pg.wait_for_selector("li[data-line-row]")
        return A, B

    def save(pg):
        pg.get_by_role("button", name="Lưu nháp").click()

    # K1 (lại): A lưu số, B (bản cũ) đổi Ghi chú + sửa dòng
    rid = make_recon([{"batch": 3, "counted_qty": "27", "reason": ""}, {"batch": 4, "counted_qty": "24", "reason": ""}], "ban đầu")
    A, B = open_two(rid)
    fill(A, 3, "26")
    save(A)
    A.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    B.get_by_label("Ghi chú").fill("B đổi ghi chú")
    fill(B, 4, "23")
    save(B)
    B.wait_for_selector("text=vừa được", timeout=10_000)
    cur = get(rid)
    l3 = [l["counted_qty"] for l in cur["lines"] if l["batch"] == 3]
    ok("K1 B (bản cũ) đổi ghi chú + dòng: ra banner 409", B.get_by_text(re.compile("Phiếu vừa được")).count() >= 1)
    ok("K1 BE giữ số của A (lô 3 = 26) và ghi chú gốc, ghi chú của B KHÔNG được ghi", l3 == ["26.000"] and cur["note"] == "ban đầu", f"{l3} / {cur['note']}")
    ok("K1 B giữ nguyên thứ B đang gõ trong form sau 409", B.get_by_label("Ghi chú").input_value() == "B đổi ghi chú" and row(B, 4).locator("input[data-counted]").input_value() in ("23",))
    ok("K1 Có câu cảnh báo trước khi Tải lại (bỏ phần chưa lưu)", B.locator("[data-conflict-hint]").count() == 1 and "bị bỏ" in B.locator("[data-conflict-hint]").inner_text(), B.locator("[data-conflict-hint]").inner_text() if B.locator("[data-conflict-hint]").count() else "")
    shot(B, "R2_K1_banner_hint_1280")

    # K2: chỉ đổi ghi chú (không đổi dòng), màn cũ -> 409 và ghi chú không ghi
    rid2 = make_recon([{"batch": 3, "counted_qty": "27", "reason": ""}], "gốc2")
    A, B = open_two(rid2)
    fill(A, 3, "25")
    save(A)
    A.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    B.get_by_label("Ghi chú").fill("chỉ đổi ghi chú ở B")
    save(B)
    B.wait_for_timeout(2500)
    cur = get(rid2)
    ok("K2 B chỉ đổi Ghi chú trên màn cũ: có banner 409", B.get_by_text(re.compile("Phiếu vừa được")).count() >= 1)
    ok("K2 BE: ghi chú vẫn là 'gốc2', lô 3 vẫn 25 của A", cur["note"] == "gốc2" and [l["counted_qty"] for l in cur["lines"]] == ["25.000"], f"{cur['note']} {[l['counted_qty'] for l in cur['lines']]}")
    # K3: Tải lại nạp toàn bộ bản máy chủ rồi lưu lần hai không mất gì
    B.get_by_role("button", name=re.compile("Tải lại")).click()
    wait_idle(B, 800)
    ok("K3 Tải lại: banner mất, ghi chú về 'gốc2', số về 25 của A", B.get_by_text(re.compile("Phiếu vừa được")).count() == 0 and B.get_by_label("Ghi chú").input_value() == "gốc2" and row(B, 3).locator("input[data-counted]").input_value() in ("25",), B.get_by_label("Ghi chú").input_value())
    B.get_by_label("Ghi chú").fill("B ghi chú sau tải lại")
    save(B)
    B.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    cur = get(rid2)
    ok("K3 Sau Tải lại, B đổi ghi chú và lưu được; số của A còn nguyên", cur["note"] == "B ghi chú sau tải lại" and [l["counted_qty"] for l in cur["lines"]] == ["25.000"], f"{cur['note']}")

    # K4: A thêm dòng, B nhận 409, Tải lại thấy dòng của A, lưu lần hai giữ cả hai dòng
    rid3 = make_recon([{"batch": 3, "counted_qty": "27", "reason": ""}], "F3")
    A, B = open_two(rid3)
    A.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    A.wait_for_selector("li[data-line-row][data-batch='5']")
    fill(A, 5, "60")
    save(A)
    A.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    fill(B, 3, "26,5")
    save(B)
    B.wait_for_selector("text=vừa được", timeout=10_000)
    B.get_by_role("button", name=re.compile("Tải lại")).click()
    wait_idle(B, 800)
    rows_b = B.eval_on_selector_all("li[data-line-row]", "els => els.map(e => e.dataset.batch)")
    ok("K4 Sau Tải lại B thấy lô 5 do A thêm (và lô 3)", "5" in rows_b and "3" in rows_b, str(rows_b))
    fill(B, 3, "26,5")
    save(B)
    B.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    cur = get(rid3)
    got = {l["batch"]: l["counted_qty"] for l in cur["lines"]}
    ok("K4 Lưu lần hai: BE giữ cả lô 5 của A và lô 3 = 26,5 của B", got.get(5) == "60.000" and got.get(3) == "26.500", str(got))

    # K5: A chỉ đổi ghi chú (không lưu dòng), B (bản cũ) sửa dòng: không được âm thầm ghi đè ghi chú của A
    rid4 = make_recon([{"batch": 3, "counted_qty": "27", "reason": ""}], "gốc4")
    A, B = open_two(rid4)
    A.get_by_label("Ghi chú").fill("A đổi ghi chú")
    save(A)
    A.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    B.get_by_label("Ngày kiểm kê").fill("2026-10-01") if B.get_by_label("Ngày kiểm kê").count() else None
    fill(B, 3, "26")
    save(B)
    B.wait_for_timeout(2500)
    cur = get(rid4)
    banner = B.get_by_text(re.compile("Phiếu vừa được")).count() >= 1
    ok("K5 (biên) A đổi ghi chú, B màn cũ sửa dòng rồi lưu: hoặc có 409, hoặc ghi chú của A còn", banner or cur["note"] == "A đổi ghi chú", f"banner={banner} note={cur['note']} lines={[l['counted_qty'] for l in cur['lines']]}")

    # K6: tự lưu hai lần liên tiếp trên cùng trang không tự gây 409
    rid5 = make_recon([{"batch": 3, "counted_qty": "27", "reason": ""}], "lưu hai lần")
    A = new(ACC_STORE1)
    A.goto(BASE + f"/stocktake/edit/?id={rid5}")
    wait_idle(A)
    A.wait_for_selector("li[data-line-row]")
    fill(A, 3, "26")
    save(A)
    A.wait_for_selector("text=Đã lưu nháp", timeout=10_000)
    A.get_by_label("Ghi chú").fill("lần hai")
    fill(A, 3, "25")
    save(A)
    A.wait_for_timeout(2000)
    cur = get(rid5)
    ok("K6 Lưu lần hai cùng trang (không ai khác sửa): không 409, BE nhận 25 và ghi chú", A.get_by_text(re.compile("Phiếu vừa được")).count() == 0 and cur["note"] == "lần hai" and [l["counted_qty"] for l in cur["lines"]] == ["25.000"], f"{cur['note']} {[l['counted_qty'] for l in cur['lines']]}")
    # bấm đúp Lưu nháp ở trang sửa
    fill(A, 3, "24")
    A.get_by_role("button", name="Lưu nháp").dblclick()
    A.wait_for_timeout(2000)
    cur = get(rid5)
    ok("K6 Bấm đúp Lưu nháp: không banner 409 giả, BE nhận 24", A.get_by_text(re.compile("Phiếu vừa được")).count() == 0 and [l["counted_qty"] for l in cur["lines"]] == ["24.000"], str([l["counted_qty"] for l in cur["lines"]]))

    # K7: form mới, bấm đúp Lưu nháp chỉ tạo 1 phiếu, URL chỉ có id
    n0 = db("from apps.inventory.models import StockReconciliation as R\nprint('OUT:'+str(R.objects.filter(note='R2 double').count()))")[0]
    N = new(ACC_STORE1)
    N.goto(BASE + "/stocktake/new/")
    wait_idle(N)
    N.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    N.wait_for_selector("li[data-line-row]")
    fill(N, 3, "26")
    N.get_by_label("Ghi chú").fill("R2 double")
    N.get_by_role("button", name="Lưu nháp").dblclick()
    N.wait_for_timeout(3000)
    n1 = db("from apps.inventory.models import StockReconciliation as R\nprint('OUT:'+str(R.objects.filter(note='R2 double').count()))")[0]
    ok("K7 Form mới, bấm đúp Lưu nháp: đúng 1 phiếu", n1 - n0 == 1, f"{n1 - n0}")
    ok("K7 URL chuyển sang edit chỉ mang ?id=", re.fullmatch(r".*/stocktake/edit/\?id=\d+", N.url) is not None, N.url)
    # bấm Lưu nháp lần nữa sau khi URL đã đổi: không tạo phiếu thứ hai, không 409
    fill(N, 3, "25")
    N.get_by_role("button", name="Lưu nháp").click()
    N.wait_for_timeout(2000)
    n2 = db("from apps.inventory.models import StockReconciliation as R\nprint('OUT:'+str(R.objects.filter(note='R2 double').count()))")[0]
    ok("K7 Lưu tiếp sau khi URL đổi: vẫn 1 phiếu, không 409", n2 - n0 == 1 and N.get_by_text(re.compile("Phiếu vừa được")).count() == 0, f"{n2 - n0}")

    # K8: chữ BR-KK-09 + bán xen giữa trên BE thật
    rid6 = make_recon([{"batch": 5, "counted_qty": "59", "reason": ""}], "R2 chữ")
    before = qty(5)
    sell(5, 2)
    Q = new(ACC_MGR1)
    Q.goto(BASE + f"/stocktake/detail/?id={rid6}")
    wait_idle(Q)
    page_txt = Q.locator("body").inner_text()
    ok("K8 'Tiếp theo' nói theo chênh lệch đã ghi lúc đếm, không hứa số đếm", "chênh lệch đã ghi" in page_txt and "theo số thực đếm" not in page_txt and "theo số đếm" not in page_txt, page_txt[:400].replace("\n", " | "))
    Q.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    Q.wait_for_selector("[role=dialog]")
    dlg = Q.locator("[role=dialog]").inner_text()
    ok("K8 Hộp xác nhận: cộng/trừ đúng phần chênh đã ghi, không đặt lại bằng số đếm", "cộng hoặc trừ" in dlg and "không đặt lại" in dlg and "theo số thực đếm" not in dlg, dlg.replace("\n", " | ")[:300])
    shot(Q, "R2_K8_confirm_1280")
    Q.get_by_role("button", name="Duyệt phiếu").click()
    Q.wait_for_timeout(1800)
    after = qty(5)
    bt = Q.locator("body").inner_text()
    delta = round(float(after) - (float(before) - 2), 3)
    c, cur = api("loc", "GET", f"/api/inventory/reconciliations/{rid6}/")
    cap = round(float(cur["lines"][0]["counted_qty"]) - float(cur["lines"][0]["system_qty"]), 3)
    ok("K8 Tồn sau duyệt = tồn sau bán + chênh đã chụp (BR-KK-09)", abs(delta - cap) < 0.0005, f"trước {before}, sau bán {float(before)-2}, sau duyệt {after}, chênh chụp {cap}")
    ok("K8 Toast sau duyệt nói cộng/trừ theo chênh lệch đã ghi, không hứa 'theo số đếm'", "chênh lệch đã ghi" in bt and "theo số đếm" not in bt and "theo số thực đếm" not in bt, bt[-250:].replace("\n", " | "))
    shot(Q, "R2_K8_done_1280")

    # K9: màn chi tiết 1280 không cắt bảng (Low đã sửa) + 360 không cuộn ngang
    L = new(ACC_MGR1)
    L.goto(BASE + f"/stocktake/detail/?id={rid3}")
    wait_idle(L)
    dims = L.evaluate("() => { const t = document.querySelector('table.lt') || document.querySelector('table'); const w = t.closest('div'); return [t.scrollWidth, w.clientWidth, document.documentElement.scrollWidth, window.innerWidth]; }")
    ok("K9 Chi tiết 1280: bảng không bị cắt (scrollWidth <= khung) và trang không cuộn ngang", dims[0] <= dims[1] + 1 and dims[2] <= dims[3] + 1, str(dims))
    shot(L, "R2_K9_detail_1280")
    for u, path, tag in ((ACC_MGR1, f"/stocktake/detail/?id={rid3}", "detail"), (ACC_STORE1, f"/stocktake/edit/?id={rid3}", "edit"), (ACC_STORE1, "/stocktake/new/", "new")):
        S = new(u, 360, 780)
        S.goto(BASE + path)
        wait_idle(S)
        ok(f"K9 360px {tag}: không cuộn ngang", no_hscroll(S))
        shot(S, f"R2_K9_360_{tag}")

    # K10: quyền sau sửa (giao1, cs2, ẩn danh) và rò dữ liệu
    for u in ("giao1", "cs2"):
        c, _ = api(u, "POST", f"/api/inventory/reconciliations/{rid3}/approve/", {})
        ok(f"K10 {u} không duyệt được qua API", c == 403, str(c))
    blob = json.dumps(get(rid3), ensure_ascii=False).lower()
    ok("K10 JSON phiếu không có field giá vốn / tiền / khách", not any(k in blob for k in ("cost", "rate", "landed", "price", "phone", "address", "customer")), blob[:200])
    ok("K10 console không có lỗi đỏ (ngoài prefetch RSC, ai-status, và 409 cố ý)", not [c for c in CONSOLE if c[1] == "error" and "RSC payload" not in c[2] and "/api/ai/status" not in c[2] and "404" not in c[2] and "409" not in c[2]], str([c for c in CONSOLE if c[1] == "error"][:3]))

    br.close()

passed = sum(1 for r in results if r[1])
print(f"\n{passed}/{len(results)} đạt")
for n, c, e in results:
    if not c:
        print("FAIL:", n, e)
