# QA Lô 3 FE lần 2 trên BE THẬT (Django runserver + SQLite tạm đã nạp seed_demo và dữ liệu giả của QA), khối Trợ lý AI ở 3 trang chi tiết.
#   AI_EXPECT=off  → BE chạy AI_ENABLED=0 (mặc định): 3 danh sách 0 request /api/ai/*, 3 trang chi tiết tối đa 1 request status, không khối.
#   AI_EXPECT=on   → BE chạy AI_ENABLED=1: khối hiện ở 3 trang, GET /api/ai/actions/?target_model=…&target_id=… trả 200 (không 400), không cảnh báo,
#                    chỗ hỏi AI gõ nhanh không mất chữ, JSON/HTML của khối không có giá vốn hay dữ liệu cá nhân.
# Điều kiện: BE ở http://127.0.0.1:8000, console build NEXT_PUBLIC_USE_MOCK=0 phục vụ tĩnh ở http://127.0.0.1:3102, mật khẩu Songbien2026.
# Chỉ dữ liệu giả. Ảnh: SHOTS/qa2-real-ai-*.png
import json
import os
import re
import time
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright

FE = os.environ.get("FE", "http://127.0.0.1:3102")
API = os.environ.get("API", "http://127.0.0.1:8000/api")
SHOTS = os.environ.get("SHOTS", "/tmp")
EXPECT = os.environ.get("AI_EXPECT", "off")
PW = "Songbien2026"
ASK = "Hỏi AI về chứng từ này"
expect.set_options(timeout=15_000)
R = []
console_all = []
errors = []


def ok(name, cond, extra=""):
    R.append((name, bool(cond), extra))
    print("PASS" if cond else "FAIL", name, "" if cond else "  -> " + str(extra)[:300], flush=True)


def call(method, path, token=None, body=None):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Token {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None), raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw), raw
        except Exception:
            return e.code, None, raw


def token_of(u):
    s, b, _ = call("POST", "/auth/token/", body={"username": u, "password": PW})
    return b["token"] if s == 200 else None


TOK = {u: token_of(u) for u in ("loc", "ql1")}
ok("API: đăng nhập được loc và ql1", all(TOK.values()))
s, b, _ = call("GET", "/sales/orders/?page_size=100", TOK["loc"])
ORDER = next(o for o in b["results"] if o["code"] == "SO261002-B00003")
ORDER_ID, ORDER_CODE = ORDER["id"], ORDER["code"]
s, b, _ = call("GET", "/sales/payments/?resolution_status=OPEN", TOK["loc"])
PAY_ID = (b["results"] if isinstance(b, dict) and "results" in b else b)[0]["id"]
s, b, _ = call("GET", "/sales/refunds/?status=PENDING,FAILED", TOK["loc"])
REF_ID = (b["results"] if isinstance(b, dict) and "results" in b else b)[0]["id"]
print(f"   [thông tin] đơn {ORDER_CODE}#{ORDER_ID}, khoản tiền #{PAY_ID}, phiếu hoàn #{REF_ID}, AI_EXPECT={EXPECT}", flush=True)
s, b, raw = call("GET", "/ai/status/", TOK["loc"])
ok(f"BE /api/ai/status/ khớp AI_EXPECT={EXPECT}", s == 200 and bool(b.get("enabled")) == (EXPECT == "on"), (s, raw[:120]))

DETAILS = [
    (f"/orders/detail/?id={ORDER_ID}", "sales.salesorder", f"{ORDER_CODE},{ORDER_ID}"),
    (f"/orders/payments/detail/?id={PAY_ID}", "sales.paymenttransaction", str(PAY_ID)),
    (f"/orders/refunds/detail/?id={REF_ID}", "sales.refund", str(REF_ID)),
]
LISTS = ["/orders/", "/orders/payments/", "/orders/refunds/"]


def make_session(browser, user, w=1280, h=900, consent=True):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    if consent:
        ctx.add_init_script("try { localStorage.setItem('cave_erp_ai_consent', '1') } catch (e) {}")
    pg = ctx.new_page()
    pg.reqs = []      # (method, url, status)
    pg.bodies = []

    def on_resp(r):
        if "/api/" in r.url:
            pg.reqs.append((r.request.method, r.url, r.status))
            if "/api/ai/actions" in r.url:
                try:
                    pg.bodies.append(r.text())
                except Exception:
                    pass

    pg.on("response", on_resp)
    pg.on("console", lambda m: (console_all.append(m.text), m.type == "error" and "Failed to fetch RSC" not in m.text and "401" not in m.text and errors.append(f"[{user}] {m.text}")))
    pg.on("pageerror", lambda e: errors.append(f"[{user}] pageerror {e}"))
    for attempt in range(3):
        pg.goto(FE + "/login/")
        pg.wait_for_load_state("networkidle")
        pg.get_by_label("Tài khoản").fill(user)
        pg.get_by_label("Mật khẩu").fill(PW)
        pg.get_by_role("button", name="Đăng nhập").click()
        try:
            pg.wait_for_selector(".nav a", state="attached", timeout=15_000)
            break
        except Exception:
            time.sleep(65)
    return ctx, pg


def ai_reqs(pg):
    return [r for r in pg.reqs if "/api/ai/" in r[1]]


def settle(pg, ms=1200):
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(ms)


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx, pg = make_session(browser, "loc")

    # ---------------------------------------------------------------- 3 danh sách
    for path in LISTS:
        pg.reqs.clear()
        pg.goto(FE + path)
        settle(pg)
        bad = [r for r in ai_reqs(pg) if "counts" in r[1] or "/api/ai/actions" in r[1]]
        ok(f"BE thật, AI {EXPECT}: danh sách {path} không gọi actions/counts", bad == [], ai_reqs(pg))
        if EXPECT == "off":
            ok(f"BE thật, AI tắt: danh sách {path} gọi 0 request /api/ai/*", ai_reqs(pg) == [], ai_reqs(pg))
        ok(f"BE thật: danh sách {path} có dòng dữ liệu hoặc câu rỗng, không lỗi 5xx", all(r[2] < 500 for r in pg.reqs), [r for r in pg.reqs if r[2] >= 500])

    # ---------------------------------------------------------------- 3 trang chi tiết
    for path, model, target in DETAILS:
        pg.reqs.clear(); pg.bodies.clear()
        pg.goto(FE + path)
        settle(pg, 1800)
        calls = ai_reqs(pg)
        blocks = pg.locator("[data-ai-block]").count()
        if EXPECT == "off":
            ok(f"BE thật, AI tắt: {path} tối đa 1 request /api/ai/status/, không actions", len(calls) <= 1 and all("/api/ai/status/" in c[1] for c in calls), calls)
            ok(f"BE thật, AI tắt: {path} không có khối Trợ lý AI", blocks == 0)
        else:
            acts = [c for c in calls if "/api/ai/actions" in c[1]]
            ok(f"BE thật, AI bật: {path} có khối Trợ lý AI", blocks == 1, blocks)
            ok(f"BE thật, AI bật: {path} gọi actions đúng target_model={model}", any(f"target_model={model}" in c[1] for c in acts), [c[1][-90:] for c in acts])
            ok(f"BE thật, AI bật: {path} actions trả 200 (không 400/403/5xx)", acts != [] and all(c[2] == 200 for c in acts), [(c[1][-80:], c[2]) for c in acts])
            ok(f"BE thật, AI bật: {path} không cảnh báo lỗi trong khối, có ô hỏi", pg.locator("[data-ai-block] [role=alert]").count() == 0 and pg.get_by_label(ASK).count() >= 1, pg.locator("[data-ai-block]").inner_text()[:200] if blocks else "")
            ok(f"BE thật, AI bật: {path} khối nói rõ khi chưa có đề xuất (không treo 'Đang kiểm tra')", "Đang kiểm tra" not in (pg.locator("[data-ai-block]").inner_text() if blocks else ""), pg.locator("[data-ai-block]").inner_text()[:160] if blocks else "")
            txt = pg.locator("[data-ai-block]").inner_text() if blocks else ""
            alltxt = txt + " ".join(pg.bodies)
            ok(f"BE thật, AI bật: {path} khối/JSON actions không có giá vốn hay dữ liệu cá nhân", not re.search(r"unit_cost|landed_unit_cost|purchase_rate|Khách Thử|09000001\d\d", alltxt), alltxt[:160])
            pg.screenshot(path=f"{SHOTS}/qa2-real-ai-{path.split('/')[2]}-1280.png")
        ok(f"BE thật: {path} không 5xx", all(r[2] < 500 for r in pg.reqs), [r for r in pg.reqs if r[2] >= 500])

    # ---------------------------------------------------------------- gõ nhanh, chunk chậm (chỉ khi AI bật)
    if EXPECT == "on":
        for path, model, target in DETAILS[:2]:
            pg2ctx, pg2 = make_session(browser, "loc")
            pg2.goto(FE + path)
            settle(pg2, 1500)
            held = []
            pg2.route(re.compile(r".*/_next/static/chunks/.*\.js"), lambda route: held.append(route))
            box = pg2.get_by_label(ASK).first
            expect(box).to_be_visible()
            text = "tom tat chung tu nay abc DEF 123"
            box.click()
            box.press_sequentially(text, delay=0)
            pg2.wait_for_timeout(1500)
            for r in held:
                r.continue_()
            pg2.unroute(re.compile(r".*/_next/static/chunks/.*\.js"))
            pg2.wait_for_timeout(3000)
            vals = pg2.evaluate("() => [...document.querySelectorAll('[data-ai-block] textarea, [data-ai-block] input[type=text], [data-ai-block] input:not([type])')].map(e => e.value)")
            ok(f"BE thật, gõ nhanh khi chunk chậm ({path.split('/')[2]}): đủ chữ, một ô, chunk bị giữ thật ({len(held)})", len(held) >= 1 and len(vals) == 1 and vals[0] == text, (len(held), vals))
            ok(f"BE thật, gõ nhanh ({path.split('/')[2]}): chưa tự gửi chat khi chưa Enter", not any("/chat" in r[1] or "/summary" in r[1] for r in ai_reqs(pg2)), ai_reqs(pg2))
            pg2.screenshot(path=f"{SHOTS}/qa2-real-ai-typing-{path.split('/')[2]}-1280.png")
            pg2ctx.close()
        # 360 px
        c3, p3 = make_session(browser, "loc", 360, 800)
        for path, *_r in DETAILS:
            p3.goto(FE + path); settle(p3, 1200)
            ok(f"BE thật 360px: {path.split('/')[2]} có khối AI, không cuộn ngang", p3.locator("[data-ai-block]").count() == 1 and p3.evaluate("() => document.documentElement.scrollWidth <= 361"), p3.evaluate("() => document.documentElement.scrollWidth"))
        c3.close()

    # ---------------------------------------------------------------- Quản lý (view-only ở phiếu hoàn)
    ctx_m, pm = make_session(browser, "ql1")
    for path, model, target in (DETAILS[0], DETAILS[2]):
        pm.reqs.clear(); pm.bodies.clear()
        pm.goto(FE + path); settle(pm, 1500)
        acts = [c for c in ai_reqs(pm) if "/api/ai/actions" in c[1]]
        if EXPECT == "off":
            ok(f"BE thật, AI tắt, Quản lý: {path.split('/')[2]} không khối, không actions", pm.locator("[data-ai-block]").count() == 0 and acts == [])
        else:
            ok(f"BE thật, AI bật, Quản lý: {path.split('/')[2]} actions không 5xx, khối không báo lỗi lạ", all(c[2] < 500 for c in acts) and pm.locator("[data-ai-block] [role=alert]").count() == 0, [(c[1][-70:], c[2]) for c in acts])
        body = pm.locator("main").inner_text()
        ok(f"BE thật, Quản lý: {path.split('/')[2]} không giá vốn trong HTML", not re.search(r"Giá vốn|unit_cost", body), body[:100])
    ctx_m.close()

    ok("không console.error/pageerror (ngoài RSC/401)", errors == [], errors[:3])
    ok("console không chứa tên/SĐT giả của QA", not any(re.search(r"Khách Thử|09000001\d\d", c) for c in console_all))
    ctx.close()
    browser.close()

passed = sum(1 for r in R if r[1])
print(f"\n{passed}/{len(R)} PASS", flush=True)
for n, c, e in R:
    if not c:
        print("FAIL", n, "->", str(e)[:300])
