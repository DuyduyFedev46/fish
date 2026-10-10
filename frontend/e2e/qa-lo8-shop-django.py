"""
QA P8 Lô 8 — SR-25 (Shop) với BACKEND THẬT (Django SQLite tạm) + build Shop thật (NEXT_PUBLIC_USE_MOCK=0).
Múi giờ trình duyệt: America/New_York, UTC, Pacific/Kiritimati (UTC+14), Asia/Ho_Chi_Minh (đối chứng).
Dữ liệu 100% giả. Các đơn mốc `SO261001-*` do QA dựng bằng cách đóng băng đồng hồ Django ở 2026-09-30T17:30:00Z
(= 00:30 ngày 01/10 giờ VN).

Biến môi trường:
  QA_SHOP     http://127.0.0.1:3113   (build thật trỏ API_BASE=http://127.0.0.1:8119)
  QA_API      http://127.0.0.1:8119
  QA_ORDER_PAID / QA_ORDER_REFUNDED / QA_ORDER_PENDING  "MÃ:4SỐ" (đơn đã trả / đã huỷ + hoàn / huỷ + chờ hoàn)
  QA_SHOT_DIR thư mục ảnh
"""
import json
import os
import re
import sys
import urllib.request

from playwright.sync_api import sync_playwright

SHOP = os.environ.get("QA_SHOP", "http://127.0.0.1:3113")
API = os.environ.get("QA_API", "http://127.0.0.1:8119")
SHOT = os.environ.get("QA_SHOT_DIR", "/tmp")
PAID = os.environ["QA_ORDER_PAID"].split(":")
REFUNDED = os.environ["QA_ORDER_REFUNDED"].split(":")
PENDING = os.environ["QA_ORDER_PENDING"].split(":")
TZS = ["America/New_York", "UTC", "Pacific/Kiritimati", "Asia/Ho_Chi_Minh"]
MONEY = re.compile(r"(\d[\d.,]*)\s?([đ₫])(?!\w)")
res = []


def ok(name, cond, extra=""):
    res.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  <{str(extra)[:300]}>"))


def money_bad(text):
    toks = MONEY.findall(text)
    bad = [a + b for a, b in toks if b != "₫" or not re.fullmatch(r"\d{1,3}(\.\d{3})*", a)]
    bad += [m.group(0) for m in re.finditer(r"\d+\.\d{2}\s?[đ₫](?!\w)", text)]
    bad += ["NaN"] if "NaN" in text else []
    bad += ["undefined"] if "undefined" in text else []
    return len(toks), bad


def get_json(path):
    with urllib.request.urlopen(API + path) as r:
        return json.load(r)


def goto(page, path):
    page.goto(SHOP + path)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)


def vnd(n):
    return f"{n:,}".replace(",", ".") + " ₫"


catalog = {c["item_code"]: c for c in get_json("/api/shop/catalog/")["items"]}
ok("API thật trả price dạng CHUỖI Decimal (RA-01 có thật)", isinstance(catalog["BACH-TUOC"]["price"], str) and catalog["BACH-TUOC"]["price"].endswith(".00"), catalog["BACH-TUOC"])

with sync_playwright() as p:
    b = p.chromium.launch()
    for tz in TZS:
        tag = tz.split("/")[-1]
        ctx = b.new_context(viewport={"width": 390, "height": 800}, timezone_id=tz, locale="vi-VN")
        page = ctx.new_page()
        errs, cons, posts = [], [], []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: cons.append(m.text) if m.type in ("error", "warning") else None)
        page.on("response", lambda r: posts.append(r) if r.request.method == "POST" and "/api/shop/orders" in r.url else None)
        off = page.evaluate("new Date('2026-09-30T17:30:00Z').getTimezoneOffset()")
        ok(f"[{tag}] múi giờ trình duyệt đã đổi (offset {off} phút)", (off == -420) == (tz == "Asia/Ho_Chi_Minh"), off)

        # --- catalog
        goto(page, "/shop/")
        body = page.inner_text("body")
        cnt, bad = money_bad(body)
        exp = {c["item_code"]: vnd(int(float(c["price"]))) for c in catalog.values()}
        ok(f"[{tag}] /shop/ mọi giá là x.xxx ₫ và khớp API ({len(exp)} món)", cnt >= len(exp) and not bad and all(v in body for v in exp.values()), (bad, [v for v in exp.values() if v not in body]))
        cur = {c["item_code"]: c for c in get_json("/api/shop/catalog/")["items"]}
        level = cur["BACH-TUOC"]["stock_level"]
        label = {"low": "Sắp hết", "out": "Hết hàng"}.get(level)
        ok(f"[{tag}] /shop/ tồn mức '{level}' -> nhãn '{label}', không hiện số kg tồn", (label is None or label in body) and ".000 kg" not in body, body[:400])
        page.screenshot(path=f"{SHOT}/dj-{tag}-shop.png", full_page=True)

        # --- giỏ + checkout: tổng khớp BE
        page.evaluate("localStorage.clear()")
        goto(page, "/shop/")
        cards = page.locator("button", has_text="Thêm vào giỏ")
        cards.first.click()
        cards.nth(2).click()
        cart_raw = page.evaluate("localStorage.getItem('cangcaloc_cart_v1')")
        cart = json.loads(cart_raw)
        ok(f"[{tag}] giỏ lưu giá dạng số, chỉ mã hàng/tên/giá/số lượng (không dữ liệu cá nhân)", all(isinstance(l["price"], (int, float)) for l in cart) and set().union(*[set(l) for l in cart]) <= {"item_code", "name", "price", "unit", "qty"}, cart_raw)
        want = sum(int(l["price"] * l["qty"]) for l in cart)
        goto(page, "/shop/checkout/")
        body = page.inner_text("body")
        cnt, bad = money_bad(body)
        ok(f"[{tag}] checkout: tổng {vnd(want)} và không token tiền sai", vnd(want) in body and not bad, (bad, body[-300:]))
        page.fill("#name", "Khách Giả QA8")
        page.fill("#phone", "0900000123")
        page.fill("#address", "1 Đường Giả, Phường Giả")
        if page.locator('input[type="checkbox"]').count():
            page.locator('input[type="checkbox"]').check()
        page.get_by_role("button", name=re.compile("Đặt hàng")).click()
        page.wait_for_timeout(1500)
        body = page.inner_text("body")
        created = [r for r in posts if r.status == 201]
        ok(f"[{tag}] POST tạo đơn 201", len(created) == 1, [r.status for r in posts])
        if created:
            j = created[-1].json()
            be_total = int(float(j["total_amount"]))
            ok(f"[{tag}] tổng FE ({vnd(want)}) = tổng BE ({j['total_amount']}) — không lệch đồng nào", be_total == want, (be_total, want))
            ok(f"[{tag}] màn thanh toán hiện đúng {vnd(be_total)} theo BE", vnd(be_total) in body and not money_bad(body)[1], body[:300])
            exp_iso = j["booked_expires_at"]
            ok(f"[{tag}] ISO API giữ offset (booked_expires_at={exp_iso})", re.search(r"(Z|[+-]\d{2}:\d{2})$", exp_iso) is not None, exp_iso)
            ok(f"[{tag}] mã đơn mới theo NGÀY VN (SO + yymmdd giờ VN hiện tại)", j["order_code"].startswith("SO" + __import__("datetime").datetime.now(__import__("datetime").timezone(__import__("datetime").timedelta(hours=7))).strftime("%y%m%d")), j["order_code"])
        page.screenshot(path=f"{SHOT}/dj-{tag}-thanh-toan.png", full_page=True)
        ls = page.evaluate("JSON.stringify(localStorage)+JSON.stringify(sessionStorage)")
        ok(f"[{tag}] storage/URL sau đặt hàng không có tên/SĐT/địa chỉ", not re.search(r"0900000123|Khách Giả|Đường Giả", ls + page.url), ls[:200])

        # --- giỏ cũ: giá chuỗi / rác
        for label, price, exp_txt in (("chuỗi Decimal", '"280000.00"', "560.000 ₫"), ("số", "280000", "560.000 ₫")):
            page.evaluate(f"localStorage.setItem('cangcaloc_cart_v1', JSON.stringify([{{item_code:'BACH-TUOC',name:'Bạch tuộc',price:{price},unit:'Kg',qty:2}}]))")
            goto(page, "/shop/checkout/")
            body = page.inner_text("body")
            ok(f"[{tag}] giỏ cũ giá {label} x2 -> {exp_txt}", exp_txt in body and not money_bad(body)[1], body[-300:])
        page.evaluate("localStorage.setItem('cangcaloc_cart_v1', JSON.stringify([{item_code:'BACH-TUOC',name:'Bạch tuộc',price:'abc',unit:'Kg',qty:2},{item_code:'CA-THU',name:'Cá thu',price:null,unit:'Kg',qty:1},{item_code:'GHE-XANH',name:'Ghẹ',price:'310000.00',unit:'Kg',qty:1}]))")
        goto(page, "/shop/checkout/")
        body = page.inner_text("body")
        ok(f"[{tag}] giỏ hỏng (giá 'abc'/null) không NaN/undefined, không vỡ trang", "NaN" not in body and "undefined" not in body and not errs, (errs, body[-300:]))
        page.screenshot(path=f"{SHOT}/dj-{tag}-gio-hong.png", full_page=True)
        page.evaluate("localStorage.clear()")

        # --- tra đơn (ngày VN từ BE thật)
        def lookup(code, last4):
            goto(page, "/shop/orders/")
            page.fill("#orderCode", code)
            page.fill("#phoneLast4", last4)
            page.get_by_role("button", name=re.compile("Tra|Kiểm")).first.click()
            page.wait_for_timeout(1200)
            return page.inner_text("body")

        body = lookup(*REFUNDED)
        ok(f"[{tag}] tra đơn đã hoàn: '330.000 ₫' + 'đã hoàn 01/10/2026' (giờ VN, không 30/09)", "330.000 ₫" in body and "đã hoàn 01/10/2026" in body and "30/09" not in body and not money_bad(body)[1], body[300:900])
        page.screenshot(path=f"{SHOT}/dj-{tag}-tra-don-hoan.png", full_page=True)
        body = lookup(*PENDING)
        ok(f"[{tag}] tra đơn chờ hoàn: 'hạn hoàn: 31/10/2026' (30 ngày từ 01/10 VN), không '2026-10-31'", "hạn hoàn: 31/10/2026" in body and "2026-10-31" not in body, body[300:900])
        body = lookup(*PAID)
        ok(f"[{tag}] tra đơn đã trả: thành tiền '165.000 ₫'", "165.000 ₫" in body and not money_bad(body)[1], body[300:900])
        ok(f"[{tag}] tra đơn không lộ tên/SĐT/địa chỉ", not re.search(r"Khách Giả|0900000777|Đường Giả", body), body[:300])
        ok(f"[{tag}] không pageerror/console error", not errs and not [c for c in cons if "Failed to load resource" not in c and "Failed to fetch RSC payload" not in c], (errs, cons[:3]))
        ctx.close()
    b.close()
print(f"Tổng {len(res)} ca, {res.count(False)} FAIL")
sys.exit(1 if False in res else 0)
