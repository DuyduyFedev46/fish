"""
Tiền VNĐ và ngày giờ Việt Nam hiển thị đúng trên Shop bất kể múi giờ trình duyệt (SHOP-7-01; decisions "VNĐ + giờ GMT+7").
BE thật. Trình duyệt chạy ở 4 múi giờ: America/New_York, UTC, Pacific/Kiritimati (UTC+14), Asia/Ho_Chi_Minh (đối chứng).
Dữ liệu mốc: một đơn đặt/trả lúc 2026-09-30T17:30:00Z (= 00:30 ngày 01/10 giờ VN) và một bài Góc bếp đăng đúng mốc đó.
Thay `qa-lo8-shop-format.py` và `qa-lo8-shop-django.py` (bám UI cũ, mã/ID cũ, API giả).
Chạy: python3 frontend/e2e/run_shop_e2e.py --suite formats_timezones
"""
import json
import re
import uuid

from playwright.sync_api import sync_playwright

from shop_e2e_lib import *

R = Report("formats_timezones")
TZS = ["America/New_York", "UTC", "Pacific/Kiritimati", "Asia/Ho_Chi_Minh"]
BOUNDARY = "2026-09-30T17:30:00+00:00"

# đơn mốc: đã trả (paid_at/created_at ở ranh giới ngày) + bài Góc bếp đăng ở ranh giới
st, o = create_order_api([("CA-THU", "2"), ("COMBO-BEP-NHA", "1")])
code, ltoken = o["order_code"], o["lookup_token"]
pay_order(code, o["total_amount"])
manage_shell(
    "from django.utils.dateparse import parse_datetime\nfrom apps.sales.models import SalesOrder, SalesInvoice, PaymentTransaction\n"
    "from apps.content.models import Entry\nfrom django.db import connection\n"
    f"t=parse_datetime({BOUNDARY!r})\n"
    f"SalesOrder.objects.filter(code={code!r}).update(created_at=t)\n"
    f"PaymentTransaction.objects.filter(sales_order__code={code!r}).update(received_at=t)\n"
    f"SalesInvoice.objects.filter(sales_order__code={code!r}).update(issued_at=t) if hasattr(SalesInvoice,'issued_at') else None\n"
)
manage_shell(   # phiên bản đã đăng bất biến (BR-ND-05): đổi mốc bằng SQL thẳng, chỉ trong DB e2e tạm
    "from django.db import connection\nfrom apps.content.models import Entry, EntryVersion\n"
    "e=Entry.objects.get(slug='ca-thu-hap-gung-hanh')\n"
    "c=connection.cursor()\n"
    "c.execute('UPDATE %s SET published_at=%%s WHERE entry_id=%%s' % EntryVersion._meta.db_table, ['2026-09-30 17:30:00', e.pk])\n"
    "c.execute('UPDATE %s SET first_published_at=%%s, last_published_at=%%s WHERE id=%%s' % Entry._meta.db_table, ['2026-09-30 17:30:00', '2026-09-30 17:30:00', e.pk])\n"
)
st_l, look = lookup_api(code, FAKE_PHONE)
R.ok("[API] mốc đơn 2026-09-30T17:30:00Z được lưu (placed_at)", st_l == 200 and look["placed_at"].startswith("2026-09-30T17:30"), look.get("placed_at"))

with sync_playwright() as p:
    browser = p.chromium.launch()
    for tz in TZS:
        tag = tz.split("/")[-1]
        for width in (360, 1280):
            ctx = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800}, timezone_id=tz, locale="vi-VN")
            page = ctx.new_page()
            watch = PageWatch(page)
            off = page.evaluate("new Date('2026-09-30T17:30:00Z').getTimezoneOffset()")
            if width == 360:
                R.ok(f"[{tag}] múi giờ trình duyệt đã đổi (offset {off} phút)", (off == -420) == (tz == "Asia/Ho_Chi_Minh"), off)
            # tiền: catalog, chi tiết, giỏ, checkout
            for path in ("/shop/", "/shop/item/?code=CA-THU", "/shop/item/?code=COMBO-BEP-NHA"):
                goto(page, path, 600)
                bad = money_ok(page.inner_text("body"))
                R.ok(f"[{tag}][{width}] {path}: mọi số tiền dạng 1.234.567đ (không thập phân, không NaN)", not bad, bad)
            page.goto(SHOP + "/shop/orders/")
            page.wait_for_load_state("networkidle")
            page.evaluate("(l)=>localStorage.setItem('cangcaloc_cart_v1', JSON.stringify(l))", [
                {"item_code": "CA-THU", "name": "Cá thu", "unit": "kg", "price": "165000", "qty": 1.5},
                {"item_code": "COMBO-BEP-NHA", "name": "Combo bếp nhà", "unit": "combo", "price": "450000", "qty": 2}])
            goto(page, "/shop/cart/", 600)
            page.wait_for_selector("text=Tóm tắt đơn")
            t = page.inner_text("main")
            R.ok(f"[{tag}][{width}] giỏ: 1,5 kg × 165.000 + 2 combo × 450.000 = 1.147.500đ (giá là số, không nối chuỗi)", "1.147.500đ" in t and not money_ok(t), t[:300])
            # đơn mốc: giờ theo VN
            page.goto(SHOP + "/shop/orders/")
            page.wait_for_load_state("networkidle")
            page.evaluate("(a)=>sessionStorage.setItem('cangcaloc_order_tokens_v1', JSON.stringify({[a[0]]:a[1]}))", [code, ltoken])
            goto(page, f"/shop/orders/?code={code}", 1000)
            t = page.inner_text("main")
            R.ok(f"[{tag}][{width}] đơn mốc: 'Đặt lúc 00:30 · 01/10' (giờ VN, không 30/09 hay giờ máy)", "00:30" in t and "01/10" in t and "30/09" not in t, t[:300])
            R.ok(f"[{tag}][{width}] đơn mốc: tiền đúng dạng, không NaN", not money_ok(t), money_ok(t))
            # bài đăng ranh giới
            goto(page, "/blog/?slug=ca-thu-hap-gung-hanh", 900)
            t = page.inner_text("article")
            R.ok(f"[{tag}][{width}] bài Góc bếp: ngày '01/10/2026' (không 30/09/2026, không ISO)", "01/10/2026" in t and "30/09/2026" not in t and "2026-10-01" not in t, t[:120])
            # hạn mã giảm giá: ends_at 2026-12-31T16:30:00Z = 23:30 31/12 giờ VN
            if width == 360 and tz == "UTC":
                pass
            R.ok(f"[{tag}][{width}] không lỗi JS", not watch.errors and not watch.console_errors(), (watch.errors[:2], watch.console_errors()[:2]))
            if width == 360 and tz in ("Pacific/Kiritimati", "America/New_York"):
                snap(page, f"order-boundary-{tag}", width, "formats")
            ctx.close()

    # hạn mã giảm giá theo giờ VN: ends 2026-12-31T16:30:00Z = 23:30 31/12 (VN)
    import datetime as dt
    tok = login_token()
    vcode = "TZ" + uuid.uuid4().hex[:6].upper()
    now = dt.datetime.now(dt.timezone.utc)
    api("POST", "/api/catalog/vouchers/", {"code": vcode, "name": "mã múi giờ", "kind": "PERCENT", "value": "10", "max_discount": "50000", "min_order_amount": "0",
        "starts_at": (now - dt.timedelta(days=1)).isoformat(), "ends_at": "2026-12-31T16:30:00+00:00", "total_uses": 10, "customer_terms": ""}, token=tok)
    for tz in TZS:
        ctx = browser.new_context(viewport={"width": 360, "height": 844}, timezone_id=tz, locale="vi-VN")
        page = ctx.new_page()
        page.goto(SHOP + "/shop/orders/")
        page.wait_for_load_state("networkidle")
        page.evaluate("(l)=>localStorage.setItem('cangcaloc_cart_v1', JSON.stringify(l))", [{"item_code": "CA-THU", "name": "Cá thu", "unit": "kg", "price": "165000", "qty": 1}])
        goto(page, "/shop/cart/", 600)
        page.wait_for_selector("text=Tóm tắt đơn")
        page.get_by_role("button", name="Nhập mã").click()
        page.wait_for_timeout(400)
        page.locator("input[type=text]:visible").last.fill(vcode)
        page.get_by_role("button", name="Áp dụng").locator("visible=true").last.click()
        page.wait_for_timeout(1200)
        t = page.inner_text("main")
        R.ok(f"[{tz.split('/')[-1]}] hạn mã giảm giá hiện theo giờ VN '23:30 31/12'", "23:30 31/12" in t, t[:400])
        ctx.close()
    browser.close()
R.finish()
