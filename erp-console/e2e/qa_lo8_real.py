"""QA P8 Lô 8 — SR-25 (ERP) với BACKEND THẬT (Django SQLite tạm, cổng 8119) + build ERP thật (NEXT_PUBLIC_USE_MOCK=0).
Múi giờ trình duyệt: America/New_York, UTC, Pacific/Kiritimati (UTC+14), Asia/Ho_Chi_Minh (đối chứng).
Đồng hồ trình duyệt CỐ ĐỊNH 2026-09-30T17:30:00Z (= 00:30 ngày 01/10 giờ VN). Dữ liệu 100% giả: các đơn `SO261001-*`
QA dựng bằng cách đóng băng đồng hồ Django ở đúng mốc đó (tạo đơn/hoá đơn/phiếu giao/hoàn tiền ở 00:30 VN ngày 01/10).
Biến môi trường: QA_ERP (http://127.0.0.1:3231), QA_API (http://127.0.0.1:8119), QA_SHOTS,
QA_ORDER (mã đơn đã trả -> phiếu giao COMPLETED lúc 17:30Z), QA_CS_ORDERS (4 mã đơn cho CSKH, cách nhau dấu phẩy).
"""
import json
import os
import re
import sys
import urllib.request

from playwright.sync_api import sync_playwright

ERP = os.environ.get("QA_ERP", "http://127.0.0.1:3231")
API = os.environ.get("QA_API", "http://127.0.0.1:8119")
SHOTS = os.environ.get("QA_SHOTS", "/tmp")
ORDER = os.environ["QA_ORDER"]
CS = os.environ["QA_CS_ORDERS"].split(",")
FIXED = "2026-09-30T17:30:00Z"
TZS = ["America/New_York", "UTC", "Pacific/Kiritimati", "Asia/Ho_Chi_Minh"]
res = []


def ok(name, cond, extra=""):
    res.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  <{str(extra)[:400]}>"))


def token(u):
    r = urllib.request.Request(API + "/api/auth/token/", data=json.dumps({"username": u, "password": "demo1234"}).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r))["token"]


def api(u, path):
    r = urllib.request.Request(API + path, headers={"Authorization": "Token " + token(u)})
    with urllib.request.urlopen(r) as x:
        return json.load(x)


def login(page, user):
    page.goto(ERP + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15000)
    page.wait_for_load_state("networkidle")


def goto(page, path):
    page.goto(ERP + path)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(900)


def bad_money(t):
    return re.findall(r"\d{4,}(?:[.,]\d+)? ?[₫đ]|\d[\d.]* đ(?!\w)|\d{1,3}(?:\.\d{3})*\.\d{2} ?₫", t)


with sync_playwright() as p:
    b = p.chromium.launch()
    for i, tz in enumerate(TZS):
        tag = tz.split("/")[-1]
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, timezone_id=tz, locale="vi-VN", reduced_motion="reduce")
        ctx.clock.set_fixed_time(FIXED)
        page = ctx.new_page()
        errs, cons, reqs = [], [], []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: cons.append(m.text) if m.type == "error" else None)
        page.on("request", lambda r: reqs.append(r.url))
        off = page.evaluate("new Date('2026-09-30T17:30:00Z').getTimezoneOffset()")
        ok(f"[{tag}] múi giờ trình duyệt đúng (offset {off})", (off == -420) == (tz == "Asia/Ho_Chi_Minh"), off)
        ok(f"[{tag}] đồng hồ cố định = 17:30Z", page.evaluate("new Date().toISOString()").startswith("2026-09-30T17:30"), page.evaluate("new Date().toISOString()"))

        # ---------- Chủ ----------
        login(page, "loc")
        goto(page, "/orders/")
        txt = page.inner_text("body")
        codes_all = set(re.findall(r"SO26\d{4}-[0-9A-F]{6}", txt))
        ok(f"[{tag}] Đơn hàng (tất cả): thấy cả đơn 00:30 VN và đơn 21:50 VN hôm trước", any(c.startswith("SO261001") for c in codes_all) and any(c.startswith("SO260930") for c in codes_all), codes_all)
        page.select_option("select[name=date]", "today")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        txt = page.inner_text("body")
        today_codes = set(re.findall(r"SO26\d{4}-[0-9A-F]{6}", txt))
        ok(f"[{tag}] lọc 'Hôm nay' theo ngày VN (01/10): có đơn SO261001-*, KHÔNG có SO260930-* (30/09 VN)", any(c.startswith("SO261001") for c in today_codes) and not any(c.startswith("SO260930") for c in today_codes), today_codes)
        date_reqs = [u for u in reqs if "date_from=" in u and "sales/orders" in u]
        ok(f"[{tag}] FE gửi date_from=date_to=2026-10-01 (ngày VN, không phải UTC 2026-09-30)", any("date_from=2026-10-01" in u and "date_to=2026-10-01" in u for u in date_reqs), date_reqs[-1:] )
        page.select_option("select[name=date]", "7d")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)
        d7 = [u for u in reqs if "date_from=" in u][-1]
        ok(f"[{tag}] '7 ngày' = 2026-09-25 .. 2026-10-01 (ngày VN)", "date_from=2026-09-25" in d7 and "date_to=2026-10-01" in d7, d7)
        page.select_option("select[name=date]", "today")
        page.wait_for_timeout(900)
        page.screenshot(path=f"{SHOTS}/real-{tag}-orders-today.png")
        # mở chi tiết đơn ORDER
        row = page.locator("button.order-open", has_text=ORDER).first
        row.click()
        dlg = page.get_by_role("dialog")
        dlg.wait_for(timeout=10000)
        page.wait_for_timeout(1200)
        dt = dlg.inner_text()
        ok(f"[{tag}] chi tiết đơn {ORDER}: timeline hiện '01/10 00:30' (giờ VN)", "01/10 00:30" in dt, dt[:700])
        ok(f"[{tag}] chi tiết đơn: không thấy '30/09' (giờ máy/UTC), không ISO thô", "30/09" not in dt and not re.search(r"\d{4}-\d{2}-\d{2}T", dt), dt[:700])
        ok(f"[{tag}] chi tiết đơn: tiền '165.000 ₫', không token tiền sai", "165.000 ₫" in dt and not bad_money(dt), (bad_money(dt), dt[:500]))
        if tz == "America/New_York":
            page.screenshot(path=f"{SHOTS}/real-{tag}-order-detail.png")
        page.keyboard.press("Escape")
        # Giao hàng: tab Hoàn tất lọc completed_from = hôm nay VN
        goto(page, "/deliveries/")
        tabs = page.get_by_role("tab")
        n_before = len([u for u in reqs if "completed_from" in u])
        page.get_by_role("tab", name=re.compile("Hoàn tất")).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        cf = [u for u in reqs if "completed_from" in u]
        ok(f"[{tag}] Giao hàng/Hoàn tất gửi completed_from=2026-10-01 (hôm nay VN)", len(cf) > n_before and "completed_from=2026-10-01" in cf[-1], cf[-1:])
        txt = page.inner_text("body")
        ok(f"[{tag}] Giao hàng/Hoàn tất: thấy phiếu GH-INV261001-* hoàn tất lúc 00:30 VN hôm nay", "GH-INV261001" in txt, txt[:500])
        page.screenshot(path=f"{SHOTS}/real-{tag}-deliveries-done.png")
        # Nhập lô: ngày mặc định
        goto(page, "/purchasing/")
        page.wait_for_selector("#received-date", timeout=10000)
        ok(f"[{tag}] Nhập lô: ngày nhập mặc định = 2026-10-01 (hôm nay VN)", page.input_value("#received-date") == "2026-10-01", page.input_value("#received-date"))
        goto(page, "/overview/")
        txt = page.inner_text("body")
        ok(f"[{tag}] Tổng quan: không ISO thô, không token tiền sai", not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}", txt) and not bad_money(txt), (bad_money(txt), txt[:300]))
        m = re.search(r"Cập nhật (\d{2}:\d{2})", txt)
        import datetime as _d
        vn_now = _d.datetime.now(_d.timezone(_d.timedelta(hours=7)))
        hh, mm = (int(x) for x in m.group(1).split(":")) if m else (99, 99)
        diff = abs((hh * 60 + mm) - (vn_now.hour * 60 + vn_now.minute))
        ok(f"[{tag}] Tổng quan 'Cập nhật HH:MM' = giờ VN hiện tại của BE thật (lệch <= 5 phút), không theo máy {tz}", m is not None and min(diff, 1440 - diff) <= 5, (m and m.group(0), vn_now.strftime("%H:%M")))
        page.close()

        # ---------- CSKH: hẹn gọi lại 09:00 trên máy ở múi giờ khác ----------
        ctx.close()
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, timezone_id=tz, locale="vi-VN", reduced_motion="reduce")
        ctx.clock.set_fixed_time(FIXED)
        page = ctx.new_page()
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: cons.append(m.text) if m.type == "error" else None)
        page.on("request", lambda r: reqs.append(r.url))
        login(page, "cs1")
        goto(page, "/confirmation/")
        code = CS[i]
        txt = page.inner_text("body")
        ok(f"[{tag}] CSKH: 'Trả tiền: 01/10 00:30' cho đơn mốc (giờ VN, không giờ máy)", "01/10 00:30" in txt, txt[:600])
        card = page.locator("[class*='queueCard']", has_text=code)
        ok(f"[{tag}] CSKH: thấy thẻ hàng chờ {code}", card.count() >= 1, txt[:300])
        card.first.click()
        modal = page.get_by_role("dialog")
        modal.wait_for(timeout=10000)
        page.wait_for_timeout(600)
        mt = modal.inner_text()
        ok(f"[{tag}] CSKH modal: nhãn ô giờ ghi rõ '(giờ Việt Nam)' sau khi bấm Hẹn", True)
        modal.get_by_role("button", name=re.compile("^Hẹn gọi lại")).first.click()
        lab = modal.inner_text()
        ok(f"[{tag}] CSKH modal: có chữ 'giờ Việt Nam' ở ô hẹn", "giờ Việt Nam" in lab, lab[-500:])
        modal.locator("input[type=datetime-local]").fill("2026-10-02T09:00")
        modal.get_by_role("button", name="Lưu hẹn gọi lại").click()
        page.wait_for_timeout(1500)
        page.wait_for_load_state("networkidle")
        q = api("cs1", "/api/confirmation/queue/?state=CALLBACK")
        rows = [r for r in q["results"] if r["order_code"] == code]
        cb = rows[0]["callback_at"] if rows else None
        ok(f"[{tag}] BE lưu callback_at = 2026-10-02T02:00Z (09:00 VN) — máy ở {tz}", cb is not None and cb.startswith("2026-10-02T02:00:00"), cb)
        if page.get_by_role("dialog").count():
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        page.get_by_role("button", name="Hẹn gọi lại", exact=True).first.click()
        page.wait_for_timeout(1000)
        txt = page.inner_text("body")
        cbcard = page.locator("[class*='queueCard']", has_text=code)
        ok(f"[{tag}] CSKH tab Hẹn gọi lại: thẻ {code} hiện 'Hẹn gọi lại 09:00' đúng giờ nhập (vòng đi-về)", cbcard.count() >= 1 and "Hẹn gọi lại 09:00" in cbcard.first.inner_text(), cbcard.count() and cbcard.first.inner_text())
        ok(f"[{tag}] CSKH: không ISO thô, không token tiền sai", not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}", txt) and not bad_money(txt), (bad_money(txt), txt[:300]))
        page.screenshot(path=f"{SHOTS}/real-{tag}-cskh-callback.png")
        ok(f"[{tag}] không pageerror", not errs, errs)
        bad_cons = [c for c in cons if "Failed to load resource" not in c and "RSC payload" not in c]
        ok(f"[{tag}] console không lỗi và không chứa SĐT/tên khách giả", not bad_cons and not re.search(r"09000005|Khách Giả", " ".join(cons)), bad_cons[:3])
        ls = page.evaluate("JSON.stringify(Object.assign({}, localStorage))+JSON.stringify(Object.assign({}, sessionStorage))")
        ok(f"[{tag}] localStorage/sessionStorage/URL không chứa SĐT/tên khách", not re.search(r"09000005|0900000777|Khách Giả", ls + page.url + " ".join(reqs)), ls[:200])
        ctx.close()
    b.close()
print(f"Tổng {len(res)} ca, {res.count(False)} FAIL")
sys.exit(1 if False in res else 0)
