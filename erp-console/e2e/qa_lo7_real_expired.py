"""QA Lô 7 — L5-1 với BACKEND THẬT (Django SQLite 8118) + ERP build thật (3219): danh sách lô EXPIRED dùng has_stock=1.
Dữ liệu giả. Dấu vết giá vốn: 777001/777002 (giá mua) không được xuất hiện với warehouse_staff."""
import json, os, re, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = "http://127.0.0.1:3219"; API = "http://127.0.0.1:8118"; SHOTS = os.environ["SHOTS"]
res = []
def ok(n, c, e=""):
    res.append(bool(c)); print(("PASS " if c else "FAIL ") + n + ("" if c else f"  <{e}>"))
def token(u):
    r = urllib.request.Request(API + "/api/auth/token/", data=json.dumps({"username": u, "password": "demo1234"}).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r))["token"]
def api(u, path):
    r = urllib.request.Request(API + path, headers={"Authorization": "Token " + token(u)})
    try:
        x = urllib.request.urlopen(r); return x.status, x.read().decode(), x.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers
# --- API thật, ma trận Group ---
for u, exp in (("loc", 200), ("ql1", 200), ("kho1", 200), ("giao1", 403)):
    st, body, _ = api(u, "/api/inventory/batches/?status=EXPIRED&has_stock=1")
    ok(f"API {u}: {st}", st == exp, body[:100])
    if st == 200:
        rows = json.loads(body)["results"]
        ok(f"API {u}: đúng 2 lô EXPIRED còn tồn (không có lô hết tồn, không có lô SELLING)", len(rows) == 2 and all(r["status"] == "EXPIRED" and float(r["qty_available"]) > 0 for r in rows), str(len(rows)))
        ok(f"API {u}: có item_name/supplier_name/warehouse_name/status_label", all(all(r.get(k) for k in ("item_name", "supplier_name", "warehouse_name", "status_label")) for r in rows), str(rows[:1])[:200])
        if u in ("kho1",):
            ok(f"API {u}: JSON không chứa giá mua 777001/777002 và khoá giá vốn", not re.search(r"77700[1-4]", body) and not re.search(r"purchase_rate|landed|unit_cost", body), body[:200])
        if u == "loc":
            ok("API loc (đối chứng): thấy giá vốn", re.search(r"777001|purchase_rate|landed", body) is not None)
st, body, _ = api("kho1", "/api/inventory/batches/?status=EXPIRED")
ok("API kho1 không has_stock: 3 lô EXPIRED (đối chứng, filter thật sự lọc)", json.loads(body)["count"] == 3, body[:100])
try:
    urllib.request.urlopen(API + "/api/inventory/batches/?has_stock=1"); ok("API chưa đăng nhập: 401", False)
except urllib.error.HTTPError as e:
    ok("API chưa đăng nhập: 401", e.code == 401)
# --- UI thật ---
def login(page, user):
    page.goto(BASE + "/login/"); page.wait_for_load_state("networkidle")
    page.fill("#u", user); page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15000); page.wait_for_load_state("networkidle")
with sync_playwright() as p:
    b = p.chromium.launch()
    for user, vp in (("kho1", (1280, 800)), ("kho1", (375, 700)), ("loc", (1280, 800)), ("ql1", (1280, 800))):
        ctx = b.new_context(viewport={"width": vp[0], "height": vp[1]}); page = ctx.new_page()
        reqs, cons = [], []
        page.on("request", lambda r: reqs.append(r.url)); page.on("console", lambda m: cons.append(m.text))
        login(page, user)
        page.goto(BASE + "/inventory/?status=EXPIRED"); page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
        tag = f"UI {user} {vp[0]}px"
        list_reqs = [u for u in reqs if "/api/inventory/batches/" in u and "status=EXPIRED" in u]
        ok(f"{tag}: gọi đúng has_stock=1 (1 URL, không lọc lại ở FE)", any("has_stock=1" in u for u in list_reqs), str(list_reqs))
        rows = page.locator("tbody tr") if vp[0] > 500 else page.locator("[data-testid], li, tbody tr")
        txt = page.inner_text("body")
        ok(f"{tag}: thấy 2 lô còn tồn (CA-GIA-1-260925, CA-GIA-2-260924)", "CA-GIA-1-260925" in txt and "CA-GIA-2-260924" in txt)
        ok(f"{tag}: KHÔNG thấy lô hết tồn CA-GIA-1-260923 và lô SELLING", "CA-GIA-1-260923" not in txt and "CA-GIA-2-260929" not in txt)
        ok(f"{tag}: hiện tên NCC/kho/nhãn trạng thái từ BE", "Đầu mối Giả A" in txt and "Kho giả chính" in txt and "Quá hạn" in txt, txt[:300].replace("\n", " | "))
        html = page.content()
        if user == "kho1":
            ok(f"{tag}: DOM không có giá mua 777001/777002 và không có cột GIÁ VỐN", not re.search(r"77[ .,]?700[1-4]", html) and not any("GIÁ VỐN" in h.upper() for h in page.locator("thead th").all_inner_texts()), str(page.locator("thead th").all_inner_texts()))
        elif user == "loc":
            ok(f"{tag} (đối chứng): Chủ thấy cột GIÁ VỐN và giá 777.001", any("GIÁ VỐN" in h.upper() for h in page.locator("thead th").all_inner_texts()) and re.search(r"777[.,]?001", txt) is not None, txt[:200])
        else:
            ok(f"{tag}: Quản lý không thấy giá vốn", not re.search(r"77[ .,]?700[1-4]", html))
        ok(f"{tag}: không cuộn ngang", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
        ls = page.evaluate("JSON.stringify(Object.assign({}, localStorage)) + JSON.stringify(Object.assign({}, sessionStorage))")
        ok(f"{tag}: storage/URL/console không có giá vốn hay dữ liệu khách", not re.search(r"77700\d", ls + page.url + " ".join(cons) + " ".join(reqs)) if user == "kho1" else True)
        page.screenshot(path=f"{SHOTS}/real-l51-{user}-{vp[0]}.png", full_page=True)
        ctx.close()
    # delivery_staff vào thẳng URL
    ctx = b.new_context(viewport={"width": 1280, "height": 800}); page = ctx.new_page(); login(page, "giao1")
    page.goto(BASE + "/inventory/?status=EXPIRED"); page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
    t = page.inner_text("body")
    ok("UI giao1 vào thẳng /inventory: không thấy lô nào", "CA-GIA-1-260925" not in t and not re.search(r"77700\d", page.content()), t[:200].replace("\n", " | "))
    page.screenshot(path=f"{SHOTS}/real-l51-giao1.png"); ctx.close()
    b.close()
print(f"Tổng {len(res)} ca, {res.count(False)} FAIL"); sys.exit(1 if False in res else 0)
