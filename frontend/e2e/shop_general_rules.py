"""
AC chung G1–G8 trên toàn Shop (02-stories.md, SHOP-7-01 AC3, AC4, AC5), chạy trên BE thật.

  G1 không số kg tồn     quét JSON mọi endpoint /api/shop/* và /api/public/*, và chữ/aria-label mọi trang
  G2 không rò cá nhân    API công khai, HTML, storage, URL, console, log BE; tra đơn chỉ POST
  G3 không rò giá vốn    JSON, HTML, bản build; ERP: Quản lý không dùng được API mã giảm giá (thiếu quyền)
  G4 tối thiểu 1 kg      BE: 0,5/0,3/1,25 kg, 1,5 combo, 0, âm → 400 INVALID_QTY, không tạo đơn; FE: "−" ở 1 kg mở hộp bỏ món
  G5 popup               role=dialog, aria-modal, giữ tiêu điểm khi Tab/Shift+Tab 20 lần, Esc đóng, trả tiêu điểm; máy tính 440–480 px
  G7 không mã hex rời    grep hex và transition cho mọi thuộc tính
  G8 code cũ đã xoá      grep tên component/field cũ
  + axe-core mức serious/critical ở 360 (nếu có axe-core sẵn trên máy; không cài thêm)
Chạy: python3 frontend/e2e/run_shop_e2e.py --suite general_rules
"""
import glob
import json
import re
import subprocess
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

from shop_e2e_lib import *

R = Report("general_rules")
tok = login_token()

STOCK_KEYS = {"sellable" + "_qty", "available_qty", "stock_qty", "qty_available", "on_hand", "qty_on_hand", "stock", "available", "remaining", "qty_reserved"}
COST_KEYS = {"purchase_rate", "landed_unit_cost", "unit_cost", "rate", "batch_id", "batch_code", "batch", "margin", "profit", "cost", "cogs",
             "purchase_cost"}
# TD-05: dòng đơn công khai có `rate` = đơn giá BÁN niêm yết đã đóng băng (không phải giá vốn). Chỉ cho phép đúng đường dẫn này;
# `rate` ở chỗ khác vẫn bị coi là rò giá nhập.
ALLOWED_COST_PATHS = {"/lines/rate"}
PII_KEYS = {"phone", "address", "delivery_address", "customer", "recipient", "full_name", "email"}
STOCK_TEXT = re.compile(r"còn\s*[\d.,]+\s*(kg|combo)", re.I)


def keys_of(obj, path=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append((path + "/" + k, k))
            out += keys_of(v, path + "/" + k)
    elif isinstance(obj, list):
        for v in obj:
            out += keys_of(v, path)
    return out


def scan(label, body, *, stock=True, cost=True, pii=True, text=None):
    flat = keys_of(body)
    bad = []
    if stock:
        bad += [p for p, k in flat if k in STOCK_KEYS]
    if cost:
        bad += [p for p, k in flat if k in COST_KEYS and p not in ALLOWED_COST_PATHS]
    if pii:
        bad += [p for p, k in flat if k in PII_KEYS and "/seller" not in p and "/fields" not in p]
    dump = json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body
    leaks = contains_pii(dump)
    return bad, leaks, dump


# ============================================================ G1 + G2 + G3 trên API công khai
catalog = api("GET", "/api/shop/catalog/")[1]
codes = [i["item_code"] for i in catalog["items"]]
endpoints = {
    "GET /api/shop/catalog/": api("GET", "/api/shop/catalog/"),
    "GET /api/public/site-info/": api("GET", "/api/public/site-info/"),
    "GET /api/public/content/entries/": api("GET", "/api/public/content/entries/"),
    "GET /api/public/content/categories/": api("GET", "/api/public/content/categories/"),
    "GET /api/public/content/footer-links/": api("GET", "/api/public/content/footer-links/"),
}
for c in codes:
    endpoints[f"GET /api/shop/catalog/{c}/"] = api("GET", f"/api/shop/catalog/{c}/")
for role in ("privacy", "terms", "contact", "returns", "shipping", "payment", "complaints", "how_to_buy", "about"):
    endpoints[f"GET /api/public/content/pages/by-role/{role}/"] = api("GET", f"/api/public/content/pages/by-role/{role}/")
st, ents = api("GET", "/api/public/content/entries/")
rows = ents.get("results", ents) if isinstance(ents, dict) else ents
for e in (rows or [])[:6]:
    endpoints[f"GET /api/public/content/entries/{e['slug']}/"] = api("GET", f"/api/public/content/entries/{e['slug']}/")
endpoints["POST /api/shop/vouchers/check/ (không mã)"] = api("POST", "/api/shop/vouchers/check/", {"items": [{"item_code": "CA-THU", "qty": "1"}]})
endpoints["POST /api/shop/vouchers/check/ (mã sai)"] = api("POST", "/api/shop/vouchers/check/", {"code": "KHONGCO", "items": [{"item_code": "CA-THU", "qty": "1"}]})
st, order = create_order_api([("CA-THU", "1.5"), ("COMBO-BEP-NHA", "1")])
endpoints["POST /api/shop/orders/ (thành công)"] = (st, order)
code, ltoken = order["order_code"], order["lookup_token"]
endpoints["POST /api/shop/orders/<mã>/checkout/"] = api("POST", f"/api/shop/orders/{code}/checkout/")
endpoints["POST /api/shop/orders/lookup/ (mã + SĐT)"] = lookup_api(code, FAKE_PHONE)
endpoints["POST /api/shop/orders/lookup/ (mã + token)"] = lookup_api(code, token=ltoken)
endpoints["POST /api/shop/orders/lookup/ (sai SĐT)"] = lookup_api(code, "0900000002")
pay_order(code, order["total_amount"])
endpoints["POST /api/shop/orders/lookup/ (đã trả)"] = lookup_api(code, FAKE_PHONE)
# lỗi nghiệp vụ: hết hàng, sai số lượng
stock_set("CA-HOI-NU", 1)
endpoints["POST /api/shop/orders/ (OUT_OF_STOCK short)"] = create_order_api([("CA-HOI-NU", "2")])
stock_set("CA-HOI-NU", 0)
endpoints["POST /api/shop/orders/ (OUT_OF_STOCK out)"] = create_order_api([("CA-HOI-NU", "1"), ("MUC-ONG", "1")])
stock_set("CA-HOI-NU", 20)
endpoints["POST /api/shop/orders/ (INVALID_QTY)"] = create_order_api([("CA-THU", "0.5")])
endpoints["POST /api/shop/orders/ (VALIDATION)"] = api("POST", "/api/shop/orders/", {"items": []})

for label, (status, body) in endpoints.items():
    if status == 404 and "catalog/" in label and "KHONG" in label:
        continue
    pii_scan = "orders" in label or "vouchers" in label  # chỉ yêu cầu khoá cá nhân trống ở API đơn
    bad, leaks, dump = scan(label, body, pii=("orders" in label))
    # `name` hợp lệ ở catalog (tên món), site-info (người bán), nội dung (tác giả/chuyên mục): chỉ xét khoá cá nhân ở API đơn
    R.ok(f"G1/G3 {label} [{status}]: không khoá số kg tồn / giá vốn / mã lô / dữ liệu người nhận", not bad, bad)
    R.ok(f"G2 {label}: không chứa tên/SĐT/địa chỉ giả của khách", not leaks, leaks)
    if "OUT_OF_STOCK" in label:
        txt = json.dumps(body, ensure_ascii=False)
        R.ok(f"G1/G3 {label}: lỗi hết hàng không có số kg, chữ 'kg', mã lô",
             not re.search(r"\d+(\.\d+)?\s*kg|\bLO-|batch|còn \d", txt, re.I) and "1.5" not in txt and "0.5" not in txt, txt[:300])
lv = {i["item_code"]: i["stock_level"] for i in catalog["items"]}
R.ok("G1 catalog: stock_level chỉ in/low/out; có đủ 3 mức trong dữ liệu mẫu", set(lv.values()) == {"in", "low", "out"}, lv)

# GET tra đơn cũ (4 số cuối) đã gỡ
s_get, _ = api("GET", f"/api/shop/orders/lookup/?order_code={code}&" + "phone_" + "last4=0001")
R.ok("G2 tra đơn không còn GET (4 số cuối): 405/404", s_get in (404, 405), s_get)
s_get2, _ = api("GET", f"/api/shop/orders/{code}/?" + "phone_" + "last4=0001")
R.ok("G2 GET /api/shop/orders/<mã>/ không có (không lộ đơn qua GET)", s_get2 in (404, 405), s_get2)

# log BE không có dữ liệu cá nhân
logs = [p for p in (workdir() / "be.log", workdir() / "be8000.log") if p.exists()]
if logs:
    text = "".join(p.read_text(errors="replace") for p in logs)
    R.ok("G2 log BE của lần chạy không chứa tên/SĐT/địa chỉ giả", not contains_pii(text) and "Nguyễn Văn A" not in text, contains_pii(text))
else:
    R.skip("G2 log BE", "không có be.log trong thư mục làm việc")

# ============================================================ ERP: Quản lý không dùng được API mã giảm giá (G3, bất biến 2)
for user in ("qa_manager", "qa_warehouse", "qa_courier1", "qa_cs1", "qa_nogroup"):
    t = login_token(user)
    s1, _ = api("GET", "/api/catalog/vouchers/", token=t)
    s2, _ = api("POST", "/api/catalog/vouchers/", {"code": "ABC"}, token=t)
    R.ok(f"G3 ERP: {user} không dùng được API mã giảm giá (403)", s1 == 403 and s2 == 403, (s1, s2))
s_anon, _ = api("GET", "/api/catalog/vouchers/")
R.ok("G3 ERP: chưa đăng nhập → 401 ở API mã giảm giá", s_anon == 401, s_anon)
s_own, _ = api("GET", "/api/catalog/vouchers/", token=tok)
R.ok("G3 ERP: Chủ dùng được (200)", s_own == 200, s_own)

# ============================================================ G4 BE: số lượng sai
before = order_count()
bad_qty = [("CA-THU", "0.3"), ("CA-THU", "1.25"), ("COMBO-BEP-NHA", "1.5"), ("COMBO-BEP-NHA", "0"), ("CA-THU", "0"),
           ("CA-THU", "-1"), ("CA-THU", "abc"), ("CA-THU", "1e30"), ("CA-THU", "NaN")]
res = []
for item, qty in bad_qty:
    s, b = create_order_api([(item, qty)])
    res.append((item, qty, s, b.get("code") if isinstance(b, dict) else b))
R.ok("G4 BE: mọi số lượng sai (0,3/1,25 kg, 1,5 combo, 0, âm, chữ, 1e30, NaN) → 400 và không tạo đơn",
     all(r[2] == 400 for r in res) and order_count() == before, res)
R.ok("G4 BE: mã lỗi là INVALID_QTY hoặc VALIDATION (không 500)", all(r[3] in ("INVALID_QTY", "VALIDATION") for r in res), res)
reserved_before = manage_shell("from apps.inventory.models import Batch\nfrom django.db.models import Sum\nprint(Batch.objects.aggregate(s=Sum('qty_reserved'))['s'])")
s_ok_05, _ = create_order_api([("CA-THU", "0.5")])
s_ok_1, _ = create_order_api([("CA-THU", "1")])
R.ok("G4 BE: đúng bước hợp lệ (0,5 kg và 1 kg) đặt được", s_ok_05 == 201 and s_ok_1 == 201, (s_ok_05, s_ok_1))

# ============================================================ UI: quét chữ/aria-label G1, G2; hex; popup; axe
ROUTES = ["/", "/shop/", "/shop/?q=muc", "/shop/item/?code=CA-THU", "/shop/item/?code=MUC-ONG", "/shop/item/?code=TOM-SU-1",
          "/shop/item/?code=COMBO-BEP-NHA", "/shop/cart/", "/shop/checkout/", "/shop/orders/", "/about/", "/blog/",
          "/pages/?slug=doi-tra", "/pages/?slug=lien-he", "/pages/?slug=cach-mua-hang", "/khong-co/"]


def find_axe():
    cands = [os.environ.get("AXE_JS", "")] + glob.glob(str(ROOT / "**/node_modules/axe-core/axe.min.js"), recursive=True)[:5] + \
        glob.glob(str(ROOT / "scratchpad/**/node_modules/axe-core/axe.min.js"), recursive=True)[:3]
    for c in cands:
        if c and Path(c).exists():
            return c
    return None


AXE = find_axe()


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (360, 1280):
        ctx = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800})
        page = ctx.new_page()
        watch = PageWatch(page)
        page.goto(SHOP + "/shop/orders/")
        page.wait_for_load_state("networkidle")
        page.evaluate("(l)=>localStorage.setItem('cangcaloc_cart_v1', JSON.stringify(l))",
                      [{"item_code": "CA-THU", "name": "Cá thu", "unit": "kg", "price": "165000", "qty": 1}])
        bad_text, bad_html, hs = [], [], []
        for r in ROUTES:
            goto(page, r, 600)
            body = page.inner_text("body")
            aria = " ".join(page.eval_on_selector_all("[aria-label],[title],[alt]", "e=>e.map(x=>(x.getAttribute('aria-label')||'')+' '+(x.getAttribute('title')||'')+' '+(x.getAttribute('alt')||''))"))
            html = page.content()
            if STOCK_TEXT.search(body) or STOCK_TEXT.search(aria):
                bad_text.append((r, (STOCK_TEXT.search(body) or STOCK_TEXT.search(aria)).group(0)))
            leaks = contains_pii(html + page.url + storage_dump(page))
            if leaks:
                bad_html.append((r, leaks))
            if re.search(r"purchase_rate|landed_unit_cost|unit_cost|giá vốn|lãi lỗ", html, re.I):
                bad_html.append((r, "giá vốn"))
            if page.evaluate("document.documentElement.scrollWidth") > width:
                hs.append(r)
        R.ok(f"G1 [{width}] {len(ROUTES)} trang: không có chữ 'còn N kg/combo' (kể cả aria-label, title, alt)", not bad_text, bad_text)
        R.ok(f"G2/G3 [{width}] {len(ROUTES)} trang: HTML/URL/storage không chứa dữ liệu cá nhân giả, không từ giá vốn", not bad_html, bad_html)
        R.ok(f"G6 [{width}] {len(ROUTES)} trang: không cuộn ngang", not hs, hs)
        R.ok(f"G2 [{width}] console sạch lỗi JS, không PII", not watch.console_errors() and not contains_pii(" ".join(t for _, t in watch.console)),
             watch.console_errors()[:2])

        # ---------------- G4 FE: "−" ở mức tối thiểu (0,5 kg cho món kg, 1 bộ cho combo)
        set_cart_js = "(l)=>localStorage.setItem('cangcaloc_cart_v1', JSON.stringify(l))"
        page.goto(SHOP + "/shop/orders/")
        page.wait_for_load_state("networkidle")
        page.evaluate(set_cart_js, [{"item_code": "CA-THU", "name": "Cá thu", "unit": "kg", "price": "165000", "qty": 0.5},
                                     {"item_code": "COMBO-BEP-NHA", "name": "Combo bếp nhà", "unit": "combo", "price": "450000", "qty": 1}])
        goto(page, "/shop/cart/", 900)
        page.wait_for_selector("text=Tóm tắt đơn")
        btn = page.get_by_role("button", name=re.compile(r"^Bỏ Cá thu khỏi giỏ")).first
        btn.click()
        page.wait_for_timeout(500)
        dlg = page.locator("[role=dialog]")
        R.ok(f"G4/G5 [{width}] giỏ: bấm '−' ở mức tối thiểu (0,5 kg) → mở hộp 'Bỏ món này?'", dlg.count() == 1 and "Bỏ" in dlg.inner_text(), dlg.inner_text() if dlg.count() else "")
        if dlg.count():
            R.ok(f"G5 [{width}] hộp bỏ món: role=dialog, aria-modal=true, có tên (aria-label/labelledby)",
                 dlg.get_attribute("aria-modal") == "true" and (dlg.get_attribute("aria-labelledby") or dlg.get_attribute("aria-label")))
            focus_ok = True
            for i in range(20):
                page.keyboard.press("Tab" if i % 2 == 0 else "Shift+Tab")
                inside = page.evaluate("(() => { const d = document.querySelector('[role=dialog]'); return !!d && d.contains(document.activeElement); })()")
                focus_ok = focus_ok and inside
            for i in range(20):
                page.keyboard.press("Tab")
                focus_ok = focus_ok and page.evaluate("(() => { const d = document.querySelector('[role=dialog]'); return !!d && d.contains(document.activeElement); })()")
            R.ok(f"G5 [{width}] Tab/Shift+Tab 20 lần: tiêu điểm không ra khỏi hộp", focus_ok)
            if width >= 600:
                w = dlg.bounding_box()["width"]
                R.ok(f"G5 [{width}] hộp thoại máy tính rộng 440–480 px", 440 <= w <= 480, w)
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
            R.ok(f"G5 [{width}] Esc đóng hộp", page.locator("[role=dialog]").count() == 0)
            back_on_trigger = page.evaluate("(() => { const a = document.activeElement; return a ? (a.getAttribute('aria-label') || a.innerText || '') : ''; })()")
            R.ok(f"G5 [{width}] sau Esc tiêu điểm trả về nút đã mở ('Bỏ Cá thu khỏi giỏ')", "Bỏ Cá thu" in back_on_trigger, back_on_trigger)
        # combo ở 1: cũng mở hộp
        page.get_by_role("button", name=re.compile(r"^Bỏ Combo bếp nhà")).first.click()
        page.wait_for_timeout(400)
        R.ok(f"G4 [{width}] combo ở 1 bộ: bấm '−' mở hộp bỏ món", page.locator("[role=dialog]").count() == 1)
        page.get_by_role("button", name="Bỏ khỏi giỏ").click()
        page.wait_for_timeout(400)
        left = json.loads(page.evaluate("localStorage.getItem('cangcaloc_cart_v1')"))
        R.ok(f"G4 [{width}] 'Bỏ' xoá đúng dòng combo; không dòng nào có số lượng < tối thiểu", [x["item_code"] for x in left] == ["CA-THU"] and all(x["qty"] >= 0.5 for x in left), left)
        # chi tiết: bộ chọn số lượng không xuống dưới mức tối thiểu (0,5 kg)
        goto(page, "/shop/item/?code=CA-THU", 700)
        page.get_by_role("heading", name="Cá thu").wait_for(timeout=10000)
        minus = page.get_by_role("button", name=re.compile(r"^Bớt 0,5\s?kg"))
        dis = minus.first.is_disabled() if minus.count() else None
        R.ok(f"G4 [{width}] chi tiết: ở mức tối thiểu (0,5 kg) nút 'Bớt 0,5 kg' bị vô hiệu", dis is True, dis)

        # ---------------- G5: các popup khác mở thật
        # Leave payment (D6)
        st_o, o = create_order_api([("GHE-XANH", "1")])
        assert st_o == 201, (st_o, o)
        page.goto(SHOP + "/shop/orders/")
        page.wait_for_load_state("networkidle")
        page.evaluate("(a)=>sessionStorage.setItem('cangcaloc_order_tokens_v1', JSON.stringify({[a[0]]:a[1]}))", [o["order_code"], o["lookup_token"]])
        goto(page, f"/shop/orders/?code={o['order_code']}", 900)
        # 360: nút mũi tên "Quay lại"; 1280: bấm logo ở đầu trang (header đặt hàng gọn không có nút quay lại)
        trigger = (page.get_by_role("button", name=re.compile("^Quay lại")) if width < 600 else page.get_by_role("link", name=re.compile("trang chủ", re.I))).first
        trigger.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        dlg = page.locator("[role=dialog]")
        ok_dlg = dlg.count() == 1 and dlg.get_attribute("aria-modal") == "true"
        trapped = True
        for i in range(20):
            page.keyboard.press("Tab" if i % 2 == 0 else "Shift+Tab")
            trapped = trapped and page.evaluate("(() => { const d = document.querySelector('[role=dialog]'); return !!d && d.contains(document.activeElement); })()")
        page.keyboard.press("Escape"); page.wait_for_timeout(400)
        R.ok(f"G5 [{width}] 'Rời trang thanh toán?': mở bằng bàn phím, role/aria-modal, giữ tiêu điểm, Esc đóng",
             ok_dlg and trapped and page.locator("[role=dialog]").count() == 0, (ok_dlg, trapped))
        R.ok(f"G5 [{width}] 'Rời trang thanh toán?': sau Esc tiêu điểm về nút/liên kết đã mở",
             re.search("Quay lại|trang chủ|Cá Về", page.evaluate("(() => { const a = document.activeElement; return a ? (a.getAttribute('aria-label')||a.innerText||'') : ''; })()")) is not None)

        # Toast không cướp tiêu điểm, role=status
        goto(page, "/shop/item/?code=CA-THU", 600)
        page.get_by_role("button", name="Thêm vào giỏ").focus()
        page.keyboard.press("Enter"); page.wait_for_timeout(500)
        active = page.evaluate("(() => { const a = document.activeElement; return a ? (a.innerText||'') : ''; })()")
        R.ok(f"G5 [{width}] toast 'Đã thêm' là role=status và không cướp tiêu điểm khỏi nút", page.locator("[role=status]").count() >= 1 and "Thêm vào giỏ" in active, active)

        # ---------------- axe-core (serious/critical) ở 360
        if width == 360:
            if not AXE:
                R.skip("axe-core ở 360", "không có axe-core sẵn trên máy (không cài thêm theo yêu cầu)")
            else:
                axe_src = Path(AXE).read_text()
                viol_all = {}
                for r in ["/", "/shop/", "/shop/item/?code=CA-THU", "/shop/cart/", "/shop/checkout/", "/shop/orders/",
                          f"/shop/orders/?code={o['order_code']}", "/about/", "/blog/", "/pages/?slug=doi-tra", "/pages/?slug=lien-he", "/khong-co/"]:
                    goto(page, r, 800)
                    page.evaluate(axe_src)
                    res_axe = page.evaluate("axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}).then(r => r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length, sample: v.nodes[0].target.join(' ')})))")
                    serious = [v for v in res_axe if v["impact"] in ("serious", "critical")]
                    if serious:
                        viol_all[r] = serious
                R.ok("axe-core 360: 0 lỗi serious/critical trên 12 trang chính", not viol_all, json.dumps(viol_all, ensure_ascii=False)[:600])

        # ---------------- GUI-04: giỏ hỏng trong localStorage (giá "abc" và null)
        corrupt_cart = [
            {"item_code": "CA-THU", "name": "Cá thu", "unit": "kg", "price": "abc", "qty": 1},
            {"item_code": "MUC-ONG", "name": "Mực ống", "unit": "kg", "price": None, "qty": 1},
        ]
        goto(page, "/shop/orders/", 500)
        page.wait_for_selector("#lookup-code", timeout=15000)
        page.evaluate(set_cart_js, corrupt_cart)
        goto(page, "/shop/cart/", 900)
        page.get_by_text("Cá thu").first.wait_for(timeout=15000)
        snap(page, "corrupt-cart", width, "gui-04")
        cart_body = page.inner_text("body")
        cart_html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", page.content(), flags=re.S | re.I)
        cart_bad_tokens = [
            token_word for token_word in ("NaN", "undefined", "Infinity")
            if token_word in cart_body or token_word in cart_html
        ]
        cart_stored = json.loads(page.evaluate("localStorage.getItem('cangcaloc_cart_v1') || '[]'"))
        cart_prices_valid = (
            len(cart_stored) == 2
            and all(isinstance(entry.get("price"), str) and entry["price"].isdigit() for entry in cart_stored)
            and not money_ok(cart_body)
            and "Giá cũ —" not in cart_body
        )
        R.ok(
            f"GUI-04 [{width}] /shop/cart/ với giỏ hỏng (price='abc', null): không NaN/undefined/Infinity, giá hợp lệ, không lỗi console",
            "Cá thu" in cart_body and "Mực ống" in cart_body and not cart_bad_tokens and cart_prices_valid
            and not watch.console_errors() and not watch.errors,
            (cart_bad_tokens, cart_stored, watch.console_errors()[:2], watch.errors[:2]),
        )

        page.evaluate(set_cart_js, corrupt_cart)
        goto(page, "/shop/checkout/", 900)
        page.locator("#f-name").wait_for(timeout=10000)
        snap(page, "corrupt-checkout", width, "gui-04")
        checkout_body = page.inner_text("body")
        checkout_html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", page.content(), flags=re.S | re.I)
        checkout_bad_tokens = [
            token_word for token_word in ("NaN", "undefined", "Infinity")
            if token_word in checkout_body or token_word in checkout_html
        ]
        checkout_stored = json.loads(page.evaluate("localStorage.getItem('cangcaloc_cart_v1') || '[]'"))
        checkout_prices_valid = (
            len(checkout_stored) == 2
            and all(isinstance(entry.get("price"), str) and entry["price"].isdigit() for entry in checkout_stored)
            and not money_ok(checkout_body)
            and "× —" not in checkout_body
            and not re.search(r"Tổng tiền hàng\s+—", checkout_body)
        )
        R.ok(
            f"GUI-04 [{width}] /shop/checkout/ với giỏ hỏng (price='abc', null): không NaN/undefined/Infinity, giá hợp lệ, không lỗi console",
            "/shop/checkout" in page.url and not checkout_bad_tokens and checkout_prices_valid
            and not watch.console_errors() and not watch.errors,
            (page.url, checkout_bad_tokens, checkout_stored, watch.console_errors()[:2], watch.errors[:2]),
        )

        # ---------------- GUI-06: nút chat Zalo nổi (ca không có Zalo trên site-info mặc định)
        goto(page, "/", 600)
        snap(page, "zalo-absent-home", width, "gui-06")
        R.ok(
            f"GUI-06 [{width}] site-info không có seller.zalo → ẩn nút chat Zalo nổi",
            page.locator("[data-testid='floating-zalo']").count() == 0,
            page.locator("[data-testid='floating-zalo']").count(),
        )
        ctx.close()

        # ---------------- GUI-06: nút chat Zalo nổi (ca có seller.zalo)
        base_site_info = endpoints["GET /api/public/site-info/"][1]
        zalo_site_info = {
            **base_site_info,
            "seller": {**(base_site_info.get("seller") or {}), "zalo": "0900000999"},
        }
        zalo_ctx = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800})
        def fulfill_site_info(route):
            route.fulfill(
                status=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json; charset=utf-8",
                },
                body=json.dumps(zalo_site_info, ensure_ascii=False),
            )

        zalo_ctx.route(re.compile(r".*/api/public/site-info/?$"), fulfill_site_info)
        zalo_ctx.route(
            re.compile(r"^https://([a-z0-9-]+\.)?zalo\.me/.*"),
            lambda route: route.fulfill(status=200, content_type="text/html", body="<html><body>zalo stub</body></html>"),
        )
        zalo_page = zalo_ctx.new_page()
        zalo_watch = PageWatch(zalo_page)

        def rects_overlap(box_a, box_b):
            if not box_a or not box_b:
                return False
            return not (
                box_a["x"] + box_a["width"] <= box_b["x"]
                or box_b["x"] + box_b["width"] <= box_a["x"]
                or box_a["y"] + box_a["height"] <= box_b["y"]
                or box_b["y"] + box_b["height"] <= box_a["y"]
            )

        # 1) Trang chủ: thuộc tính, kích thước vùng chạm, bàn phím mở tab mới, không đè BottomNav
        goto(zalo_page, "/", 800)
        fab = zalo_page.locator("[data-testid='floating-zalo']")
        fab.wait_for(state="visible", timeout=5000)
        fab_href = fab.get_attribute("href") or ""
        fab_label = fab.get_attribute("aria-label") or ""
        fab_rel = fab.get_attribute("rel") or ""
        fab_target = fab.get_attribute("target") or ""
        fab_box = fab.bounding_box()
        R.ok(
            f"GUI-06 [{width}] trang chủ: nút Zalo nổi có aria-label, href https://zalo.me/…, target=_blank, rel có noopener, ≥44px",
            bool(fab_label.strip())
            and fab_href == "https://zalo.me/0900000999"
            and fab_target == "_blank"
            and "noopener" in fab_rel
            and fab_box is not None
            and fab_box["width"] >= 44
            and fab_box["height"] >= 44,
            (fab_label, fab_href, fab_target, fab_rel, fab_box),
        )
        if width < 768:
            bottom_nav_box = zalo_page.locator("nav[aria-label='Điều hướng chính']").last.bounding_box()
            R.ok(
                f"GUI-06 [{width}] trang chủ: nút Zalo nằm phía trên thanh điều hướng dưới",
                fab_box is not None and bottom_nav_box is not None and fab_box["y"] + fab_box["height"] <= bottom_nav_box["y"],
                (fab_box, bottom_nav_box),
            )
        snap(zalo_page, "zalo-home", width, "gui-06")
        fab.focus()
        focused_test_id = zalo_page.evaluate("document.activeElement?.getAttribute('data-testid') || ''")
        with zalo_page.expect_popup() as popup_info:
            zalo_page.keyboard.press("Enter")
        popup_page = popup_info.value
        popup_page.wait_for_load_state("domcontentloaded")
        popup_url = popup_page.url
        popup_page.close()
        R.ok(
            f"GUI-06 [{width}] nút Zalo bấm được bằng bàn phím (focus + Enter mở tab https://zalo.me/…)",
            focused_test_id == "floating-zalo" and popup_url.startswith("https://zalo.me/0900000999"),
            (focused_test_id, popup_url),
        )

        # 2) Trang chi tiết món: không che nút "Thêm vào giỏ" / "Chọn mua"
        goto(zalo_page, "/shop/item/?code=CA-THU", 800)
        fab_detail = zalo_page.locator("[data-testid='floating-zalo']")
        fab_detail.wait_for(state="visible", timeout=5000)
        fab_detail_box = fab_detail.bounding_box()
        add_btn_box = zalo_page.get_by_role("button", name="Thêm vào giỏ").bounding_box()
        buy_btn_box = zalo_page.get_by_role("button", name="Chọn mua").bounding_box()
        R.ok(
            f"GUI-06 [{width}] chi tiết món: nút Zalo không che 'Thêm vào giỏ' hay 'Chọn mua'",
            fab_detail_box is not None
            and not rects_overlap(fab_detail_box, add_btn_box)
            and not rects_overlap(fab_detail_box, buy_btn_box)
            and (width >= 768 or (add_btn_box is not None and fab_detail_box["y"] + fab_detail_box["height"] <= add_btn_box["y"])),
            (fab_detail_box, add_btn_box, buy_btn_box),
        )
        snap(zalo_page, "zalo-item", width, "gui-06")

        # 3) Trang giỏ hàng: không che thanh tóm tắt hay nút tiếp tục đặt hàng
        zalo_page.goto(SHOP + "/shop/orders/")
        zalo_page.wait_for_load_state("networkidle")
        zalo_page.evaluate(
            set_cart_js,
            [
                {"item_code": "CA-THU", "name": "Cá thu", "unit": "kg", "price": "165000", "qty": 1.5},
                {"item_code": "COMBO-BEP-NHA", "name": "Combo bếp nhà", "unit": "combo", "price": "450000", "qty": 1},
            ],
        )
        goto(zalo_page, "/shop/cart/", 900)
        zalo_page.wait_for_selector("[data-cart-summary]")
        zalo_page.wait_for_timeout(200)
        fab_cart = zalo_page.locator("[data-testid='floating-zalo']")
        fab_cart.wait_for(state="visible", timeout=5000)
        fab_cart_box = fab_cart.bounding_box()
        summary_box = zalo_page.locator("[data-cart-summary]").bounding_box()
        proceed_btn_box = zalo_page.locator("[data-cart-summary] button, [data-cart-summary] a").last.bounding_box()
        R.ok(
            f"GUI-06 [{width}] giỏ hàng: nút Zalo không che nút đặt hàng / thanh tóm tắt đáy",
            fab_cart_box is not None
            and not rects_overlap(fab_cart_box, proceed_btn_box)
            and (width >= 768 or (summary_box is not None and fab_cart_box["y"] + fab_cart_box["height"] <= summary_box["y"])),
            (fab_cart_box, summary_box, proceed_btn_box),
        )
        snap(zalo_page, "zalo-cart", width, "gui-06")

        # 4) Trang đặt hàng & thanh toán: ẩn để không che nút hành động chính
        goto(zalo_page, "/shop/checkout/", 800)
        zalo_page.locator("#f-name").wait_for(timeout=10000)
        hidden_on_checkout = zalo_page.locator("[data-testid='floating-zalo']").count() == 0
        zalo_page.evaluate("(a)=>sessionStorage.setItem('cangcaloc_order_tokens_v1', JSON.stringify({[a[0]]:a[1]}))", [o["order_code"], o["lookup_token"]])
        goto(zalo_page, f"/shop/orders/?code={o['order_code']}", 800)
        hidden_on_payment = zalo_page.locator("[data-testid='floating-zalo']").count() == 0
        R.ok(
            f"GUI-06 [{width}] trang đặt hàng & thanh toán: ẩn nút Zalo nổi để không che nút chính",
            hidden_on_checkout and hidden_on_payment and not zalo_watch.console_errors() and not zalo_watch.errors,
            (hidden_on_checkout, hidden_on_payment, zalo_watch.console_errors()[:2]),
        )
        if width == 360 and AXE:
            axe_src = Path(AXE).read_text()
            goto(zalo_page, "/", 700)
            zalo_page.evaluate(axe_src)
            zalo_axe = zalo_page.evaluate(
                "axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}).then(r => r.violations.filter(v => v.impact === 'serious' || v.impact === 'critical'))"
            )
            R.ok("GUI-06 [360] axe-core khi hiện nút Zalo nổi: 0 lỗi serious/critical", not zalo_axe, zalo_axe)
        zalo_ctx.close()

        # ---------------- GUI-07, GUI-08, GUI-10: kiểm giao diện & chụp ảnh 360 + 1280
        cors_json = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json; charset=utf-8"}
        svg_thumb = (
            "data:image/svg+xml;utf8,"
            + urllib.parse.quote(
                '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240">'
                '<rect width="240" height="240" fill="rgb(10,110,140)"/>'
                '<circle cx="120" cy="120" r="68" fill="rgb(20,148,184)"/>'
                "</svg>"
            )
        )
        svg_banner = (
            "data:image/svg+xml;utf8,"
            + urllib.parse.quote(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="480">'
                '<rect width="1280" height="480" fill="rgb(12,68,118)"/>'
                '<path d="M0 320 Q320 260 640 320 T1280 320 L1280 480 L0 480 Z" fill="rgb(18,98,156)"/>'
                "</svg>"
            )
        )

        # --- GUI-07: mục danh mục có ảnh đại diện, không có ảnh, và ảnh lỗi (onError)
        base_cat = endpoints["GET /api/shop/catalog/"][1]
        cat_gui07 = json.loads(json.dumps(base_cat))
        for it in cat_gui07["items"]:
            if it["item_code"] in ("CA-THU", "COMBO-BEP-NHA", "GHE-XANH"):
                it["image"] = {
                    "alt": it["name"],
                    "is_illustration": False,
                    "urls": {"thumb": svg_thumb, "card": svg_thumb, "detail": svg_thumb},
                }
            elif it["item_code"] == "MUC-ONG":
                # URL ảnh hỏng để kích hoạt onError -> khung dự phòng nội bộ
                it["image"] = {
                    "alt": it["name"],
                    "is_illustration": False,
                    "urls": {
                        "thumb": "http://localhost:8000/media/broken-cat-thumb.jpg",
                        "card": "http://localhost:8000/media/broken-cat-thumb.jpg",
                        "detail": "http://localhost:8000/media/broken-cat-thumb.jpg",
                    },
                }
            else:
                it["image"] = None
        ctx07 = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800})
        ctx07.route(
            re.compile(r".*/api/shop/catalog/?$"),
            lambda route: route.fulfill(status=200, headers=cors_json, body=json.dumps(cat_gui07, ensure_ascii=False)),
        )
        ctx07.route(
            re.compile(r".*/media/broken-cat-thumb\.jpg$"),
            lambda route: route.fulfill(status=404, headers={"Access-Control-Allow-Origin": "*"}, body="not found"),
        )
        page07 = ctx07.new_page()
        watch07 = PageWatch(page07)
        goto(page07, "/", 800)
        snap(page07, "home-categories", width, "gui-07")
        home_cat_nav = page07.locator("nav[aria-label='Danh mục']").first
        home_cat_imgs = home_cat_nav.locator("img[loading='lazy']")
        home_cat_svgs = home_cat_nav.locator("svg")
        R.ok(
            f"GUI-07 [{width}] trang chủ: mục danh mục có ảnh đại diện hiện <img loading=lazy alt=...>, mục không ảnh/ảnh lỗi hiện khung SVG nội bộ",
            home_cat_imgs.count() >= 3
            and home_cat_svgs.count() >= 2
            and all(bool(home_cat_imgs.nth(i).get_attribute("alt")) for i in range(home_cat_imgs.count())),
            (home_cat_imgs.count(), home_cat_svgs.count()),
        )
        goto(page07, "/shop/", 800)
        snap(page07, "catalog-categories", width, "gui-07")
        shop_cat_nav = page07.locator("nav[aria-label='Danh mục']").first
        shop_cat_imgs = shop_cat_nav.locator("img[loading='lazy']")
        shop_cat_svgs = shop_cat_nav.locator("svg")
        R.ok(
            f"GUI-07 [{width}] đầu trang danh mục (/shop/): hiện ảnh đại diện nhóm + khung dự phòng khi thiếu/lỗi ảnh, không cuộn ngang",
            shop_cat_imgs.count() >= 3 and shop_cat_svgs.count() >= 2 and no_hscroll(page07, width) and not watch07.console_errors(),
            (shop_cat_imgs.count(), shop_cat_svgs.count(), watch07.console_errors()[:2]),
        )
        ctx07.close()

        # --- GUI-08: mức mua tối thiểu 0,5 kg (mock catalog & site-info min_qty=0.5)
        cat_gui08 = json.loads(json.dumps(base_cat))
        for it in cat_gui08["items"]:
            if it["unit"] == "kg":
                it["min_qty"] = "0.5"
                it["qty_step"] = "0.5"
        site_gui08 = {
            **base_site_info,
            "policies": {**(base_site_info.get("policies") or {}), "min_qty_kg": "0.5", "qty_step_kg": "0.5"},
        }
        ctx08 = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800})
        ctx08.route(
            re.compile(r".*/api/shop/catalog/?$"),
            lambda route: route.fulfill(status=200, headers=cors_json, body=json.dumps(cat_gui08, ensure_ascii=False)),
        )
        ctx08.route(
            re.compile(r".*/api/shop/catalog/CA-THU/?$"),
            lambda route: route.fulfill(
                status=200,
                headers=cors_json,
                body=json.dumps(
                    {
                        **endpoints["GET /api/shop/catalog/CA-THU/"][1],
                        "min_qty": "0.5",
                        "qty_step": "0.5",
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        ctx08.route(
            re.compile(r".*/api/public/site-info/?$"),
            lambda route: route.fulfill(status=200, headers=cors_json, body=json.dumps(site_gui08, ensure_ascii=False)),
        )
        page08 = ctx08.new_page()
        goto(page08, "/shop/", 800)
        snap(page08, "catalog-min-05kg", width, "gui-08")
        add05_btns = page08.get_by_role("button", name=re.compile(r"^Thêm 0,5\s*kg"))
        R.ok(
            f"GUI-08 [{width}] danh mục với min_qty=0.5: thẻ món hiện nút 'Thêm 0,5 kg'",
            add05_btns.count() >= 3,
            add05_btns.count(),
        )
        add05_btns.first.click()
        page08.wait_for_timeout(500)
        stored08 = json.loads(page08.evaluate("localStorage.getItem('cangcaloc_cart_v1') || '[]'"))
        R.ok(
            f"GUI-08 [{width}] bấm 'Thêm 0,5 kg' thêm đúng 0,5 kg vào giỏ",
            len(stored08) == 1 and stored08[0]["qty"] == 0.5,
            stored08,
        )
        goto(page08, "/shop/cart/", 900)
        page08.wait_for_selector("text=Tóm tắt đơn")
        cart08_body = page08.inner_text("body")
        R.ok(
            f"GUI-08 [{width}] giỏ hàng với min_qty=0.5: ghi chú 'Mua tối thiểu 0,5 kg mỗi món'",
            "Mua tối thiểu 0,5 kg mỗi món" in cart08_body and "Mua tối thiểu 1 kg" not in cart08_body,
            cart08_body[:240],
        )
        page08.get_by_role("button", name=re.compile(r"^Bỏ .* khỏi giỏ")).first.click()
        page08.wait_for_timeout(400)
        dlg08 = page08.locator("[role=dialog]")
        dlg08_txt = dlg08.inner_text() if dlg08.count() else ""
        snap(page08, "cart-remove-dialog-05kg", width, "gui-08")
        R.ok(
            f"GUI-08 [{width}] ở 0,5 kg bấm '−' mở hộp thoại bỏ món ('tối thiểu 0,5 kg')",
            dlg08.count() == 1 and "0,5 kg" in dlg08_txt,
            dlg08_txt,
        )
        ctx08.close()

        # --- GUI-10: 3 trạng thái banner trang chủ (CMS 404, slide không ảnh, slide có ảnh)
        # Ca 1: slide không có ảnh (mặc định từ load_shop_content)
        ctx10_noimg = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800})
        page10_noimg = ctx10_noimg.new_page()
        goto(page10_noimg, "/", 800)
        snap(page10_noimg, "banner-slide-no-image", width, "gui-10")
        hero_noimg = page10_noimg.locator("section[aria-label='Khuyến mãi']")
        h1_noimg = page10_noimg.locator("h1")
        home_body_noimg = page10_noimg.inner_text("body")
        snap(page10_noimg, "home-no-pay-tile", width, "gui-11")
        R.ok(
            f"GUI-10 [{width}] ca slide không có ảnh: hiện nền minh hoạ SVG nội bộ, đúng 1 thẻ h1",
            hero_noimg.locator("svg").count() >= 1 and h1_noimg.count() == 1 and bool(h1_noimg.inner_text().strip()),
            (hero_noimg.locator("svg").count(), h1_noimg.count(), h1_noimg.inner_text()),
        )
        R.ok(
            f"GUI-11 [{width}] trang chủ đã gỡ ô 'Chuyển khoản quét mã QR · Tiền về đủ là đơn tự xác nhận', không cuộn ngang",
            "Tiền về đủ là đơn tự xác nhận" not in home_body_noimg
            and "Chuyển khoản quét mã QR" not in home_body_noimg
            and no_hscroll(page10_noimg, width),
            (no_hscroll(page10_noimg, width),),
        )
        ctx10_noimg.close()

        # Ca 2: CMS chưa tạo bài home-banner (404)
        ctx10_404 = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800})
        ctx10_404.route(
            re.compile(r".*/api/public/content/entries/home-banner/?$"),
            lambda route: route.fulfill(status=404, headers=cors_json, body=json.dumps({"detail": "Not found"})),
        )
        page10_404 = ctx10_404.new_page()
        goto(page10_404, "/", 800)
        snap(page10_404, "banner-cms-404", width, "gui-10")
        hero_404 = page10_404.locator("section[aria-label='Khuyến mãi']")
        h1_404 = page10_404.locator("h1")
        cta_404 = hero_404.locator("a[href='/shop/']").first
        R.ok(
            f"GUI-10 [{width}] ca CMS 404: vẫn hiện khung banner mặc định có nền SVG, đúng 1 h1 và nút dẫn tới /shop/",
            hero_404.locator("svg").count() >= 1
            and h1_404.count() == 1
            and "Cá Về: hải sản cấp đông theo lô" in h1_404.inner_text()
            and cta_404.is_visible(),
            (h1_404.count(), h1_404.inner_text()),
        )
        ctx10_404.close()

        # Ca 3: slide có ảnh nền thật (giả lập URL ảnh nền hợp lệ)
        banner_with_img = {
            "kind": "page",
            "slug": "home-banner",
            "title": "Banner trang chủ",
            "seo_title": "",
            "description": "Hải sản cấp đông theo lô · mua từ 0,5 kg · giao tận nhà",
            "excerpt": "Hải sản cấp đông theo lô · mua từ 0,5 kg · giao tận nhà",
            "category": None,
            "cover_image": None,
            "published_at": "2026-10-01T00:00:00Z",
            "updated_at": "2026-10-01T00:00:00Z",
            "version": 1,
            "effective_from": None,
            "author": "Cá Về",
            "body": {
                "type": "doc",
                "blocks": [
                    {"type": "heading", "level": 2, "text": "Mua theo lô tại cảng"},
                    {"type": "paragraph", "children": [{"text": "Hải sản cấp đông, giá theo kg, mua từ 0,5 kg."}]},
                    {"type": "paragraph", "children": [{"text": "Xem hàng đang có", "href": "/shop/"}]},
                    {
                        "type": "image",
                        "alt": "Thuyền đánh cá tại cảng biển",
                        "urls": {
                            "sm": "http://localhost:8000/media/mock-banner.svg",
                            "md": "http://localhost:8000/media/mock-banner.svg",
                            "lg": "http://localhost:8000/media/mock-banner.svg",
                        },
                    },
                ],
            },
        }
        ctx10_img = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800})
        ctx10_img.route(
            re.compile(r".*/api/public/content/entries/home-banner/?$"),
            lambda route: route.fulfill(status=200, headers=cors_json, body=json.dumps(banner_with_img, ensure_ascii=False)),
        )
        ctx10_img.route(
            re.compile(r".*/media/mock-banner\.svg$"),
            lambda route: route.fulfill(
                status=200,
                headers={"Access-Control-Allow-Origin": "*", "Content-Type": "image/svg+xml"},
                body=urllib.parse.unquote(svg_banner.split(",", 1)[1]),
            ),
        )
        page10_img = ctx10_img.new_page()
        goto(page10_img, "/", 800)
        snap(page10_img, "banner-slide-with-image", width, "gui-10")
        hero_img = page10_img.locator("section[aria-label='Khuyến mãi']")
        banner_img_el = hero_img.locator("img").first
        R.ok(
            f"GUI-10 [{width}] ca slide có ảnh: hiện <img> nền không méo (object-fit: cover), đúng 1 h1",
            banner_img_el.count() == 1
            and banner_img_el.is_visible()
            and page10_img.locator("h1").count() == 1,
            (banner_img_el.count(), page10_img.locator("h1").count()),
        )
        ctx10_img.close()
    browser.close()

# ============================================================ G7, G8 (grep)
def grep(pattern, paths, exclude=()):
    cmd = ["grep", "-rnIE", pattern] + paths
    cmd += [f"--exclude-dir={e}" for e in ("node_modules", ".next", "out", *exclude)]
    r = subprocess.run(cmd, cwd=FRONTEND, capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l]


hex_hits = [l for l in grep(r"#[0-9A-Fa-f]{6}\b", ["components", "app", "features", "lib"]) if "globals.css" not in l]
R.ok("G7 không mã hex rời ở components/app/features/lib (trừ globals.css)", not hex_hits, hex_hits[:5])
# mã hex mà là mã màu thật (#RRGGBB) trong chuỗi TSX tính là hit; mã băm/anchor sẽ lộ ra ở đây để QA xem
trans = grep(r"transition:\s*all", ["."])
R.ok("G7 không dùng transition cho mọi thuộc tính trong frontend", not trans, trans[:5])

# Tên viết tách để chính tệp này không bị grep khớp (G8 quét cả thư mục e2e).
old_names = ["sellable" + "_qty", "Catalog" + "Grid", "AddToCart" + "Control", "Countdown" + "Timer", "phone_" + "last4", "SiteLegal" + "Footer"]
hits = {n: grep(n, ["."]) for n in old_names}
# frontend/README.md có một dòng lịch sử "đã xoá ở lô 5c: <tên cũ>" (tài liệu, không phải code): tách riêng, không tính là code còn sót.
code_hits = {k: [l for l in v if not l.startswith("./README.md")] for k, v in hits.items()}
doc_hits = [l for v in hits.values() for l in v if l.startswith("./README.md")]
R.ok("G8 không còn tên code cũ (lưới danh mục, nút thêm giỏ, đồng hồ đếm, 4 số cuối SĐT, footer pháp lý cũ, field tồn kg) trong code frontend, kể cả e2e",
     not any(code_hits.values()), {k: v[:3] for k, v in code_hits.items() if v})
R.ok(f"G8 (ghi nhận) chỉ còn {len(doc_hits)} dòng lịch sử trong frontend/README.md nhắc tên đã xoá (tài liệu)", len(doc_hits) <= 1, doc_hits[:2])
old_lookup = "OrderLook" + "up"
broad = grep(old_lookup, ["."])
strict = [l for l in broad if re.search(r"\b" + old_lookup + r"\b", l)]
R.ok("G8 component tra đơn cũ (đúng tên, có ranh giới từ) không còn trong code (frontend/README.md ghi lịch sử xoá, không tính)",
     not [l for l in strict if not l.startswith("./README.md")], strict[:3])
R.ok("G8 (ghi nhận) grep rộng chỉ còn khớp tên kiểu contract hiện hành (…Result/…Input) và dòng lịch sử trong README",
     all(re.search(old_lookup + r"(Result|Input)", l) or l.startswith("./README.md") for l in broad), broad[:3])
R.finish()
