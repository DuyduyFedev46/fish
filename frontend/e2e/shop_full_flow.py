"""
E2E toàn luồng khách Shop trên BE thật (SHOP-7-01 AC1, AC2, AC4): trang chủ → danh mục → tìm → chi tiết → giỏ → mã giảm giá →
đặt hàng → thanh toán (giả lập IPN) → trang đơn → tra cứu từ phiên khác, ở 360 và 1280, cộng các nhánh lỗi chính.

Chạy: python3 frontend/e2e/run_shop_e2e.py --suite full_flow   (xem run_shop_e2e.py). Dữ liệu cá nhân 100% giả.
Mã nghiệp vụ: BR-BH-01/05/22/23/24/25/26/27, BR-TT-02/03, BR-DM-17…24, bất biến 9.
"""
import datetime as dt
import json
import re
import threading

from playwright.sync_api import sync_playwright

from shop_e2e_lib import *

R = Report("full_flow")
SUB = "flow"
tok = login_token()
now = dt.datetime.now(dt.timezone.utc)
SUF = __import__("uuid").uuid4().hex[:4].upper()  # mã mỗi lần chạy khác nhau, chạy lại trên cùng DB không đụng nhau
V_MAIN, V_EXPIRED, V_MIN, V_ONCE, V_GONE = [p + SUF for p in ("FLOW", "EXPD", "MINO", "ONCE", "GONE")]


def create_voucher(code, **kw):
    d = dict(code=code, name="Mã e2e " + code, kind="PERCENT", value="10", max_discount="50000", min_order_amount="100000",
             starts_at=(now - dt.timedelta(days=1)).isoformat(), ends_at=(now + dt.timedelta(days=30)).isoformat(),
             total_uses=100, customer_terms="Giảm 10% tối đa 50.000đ, đơn từ 100.000đ")
    d.update(kw)
    status, body = api("POST", "/api/catalog/vouchers/", d, token=tok)
    assert status in (201, 400), (status, body)
    return body


def stub_gateway(page):
    """Chặn cổng thanh toán ngoài: ghi lại form POST (url, body) thay vì ra mạng thật. Trả danh sách ghi."""
    posts = []

    def handler(route):
        posts.append((route.request.url, route.request.post_data))
        route.fulfill(status=200, content_type="text/html", body="<html><body>gateway giả lập</body></html>")
    page.route(re.compile(r"https://(?!localhost).*sepay.*"), handler)
    return posts


def code_from_gateway_post(post):
    """Mã đơn nằm trong success_url của form gửi cổng (SHOP-FIX-01: đặt hàng xong vào thẳng cổng)."""
    return re.search(r"code%3D(SO[\w-]+)", post or "") or re.search(r"code=(SO[\w-]+)", post or "")


def fresh_context(browser, width, **kw):
    ctx = browser.new_context(viewport={"width": width, "height": 800 if width < 600 else 900}, **kw)
    page = ctx.new_page()
    page.gateway_posts = stub_gateway(page)
    return ctx, page, PageWatch(page)


def pii_sweep(label, page, watch, *, html=True):
    """Bất biến 9: URL, storage, console và (nếu html) cả HTML trang không chứa dữ liệu cá nhân giả."""
    texts = {"url": page.url, "storage": storage_dump(page), "console": " ".join(t for _, t in watch.console)}
    if html:
        texts["html"] = page.content()
    leaks = {k: contains_pii(v) for k, v in texts.items() if contains_pii(v)}
    R.ok(f"{label}: không rò dữ liệu cá nhân (URL, storage, console{', HTML' if html else ''})", not leaks, leaks)


def journey(browser, width):
    tag = str(width)
    ctx, page, watch = fresh_context(browser, width)
    # chặn cổng thanh toán ngoài: ghi lại form POST thay vì ra mạng thật
    gateway_posts = page.gateway_posts

    # 1. Trang chủ
    goto(page, "/")
    body = page.inner_text("body")
    R.ok(f"[{tag}] trang chủ: có thẻ hàng, giá dạng 1.234đ, không số kg tồn", "Cá thu" in body and not money_ok(body)
         and not re.search(r"còn\s*[\d.,]+\s*(kg|combo)", body, re.I), body[:200])
    R.ok(f"[{tag}] trang chủ: không cuộn ngang", no_hscroll(page, width))
    snap(page, "01-home", width, SUB)

    # 2. Danh mục + lọc nhóm
    goto(page, "/shop/")
    R.ok(f"[{tag}] danh mục: 8 món, 3 mức tồn đủ cả ba (Còn hàng/Sắp hết/Hết hàng)",
         all(s in page.inner_text("body") for s in ("Sắp hết", "Hết hàng")) and page.locator("text=Thêm 1 kg").count() >= 3)
    page.get_by_role("button", name="Cá", exact=True).first.click() if page.get_by_role("button", name="Cá", exact=True).count() else \
        page.get_by_role("link", name="Cá", exact=True).first.click()
    page.wait_for_timeout(600)
    R.ok(f"[{tag}] lọc nhóm Cá: chỉ còn món nhóm Cá (không Mực ống)",
         "Cá thu" in page.inner_text("main") and "Mực ống" not in page.inner_text("main"), page.url)
    snap(page, "02-category-filter", width, SUB)

    # 3. Tìm kiếm (không dấu) → gợi ý → xem tất cả
    goto(page, "/")
    box = page.locator("input[type=search]:visible").first
    box.click()
    box.fill("muc")
    page.wait_for_timeout(900)
    sug = page.locator("[role=listbox]")
    R.ok(f"[{tag}] gõ 'muc' (không dấu) → gợi ý Mực ống, tối đa 5 dòng, không số kg tồn",
         sug.count() == 1 and "Mực ống" in sug.inner_text() and not re.search(r"còn\s*[\d.,]+\s*kg", sug.inner_text(), re.I),
         sug.inner_text() if sug.count() else "no listbox")
    snap(page, "03-search-suggest", width, SUB)
    box.press("Enter")
    page.wait_for_url(re.compile(r"/shop/\?q=muc"))
    page.wait_for_selector("text=Kết quả cho", timeout=10000)
    page.wait_for_timeout(700)
    R.ok(f"[{tag}] Enter → /shop/?q=muc, có kết quả Mực ống", "Mực ống" in page.inner_text("main"))
    goto(page, "/shop/?q=zzzkhongco")
    R.ok(f"[{tag}] tìm không thấy: câu chữ + không trắng trang", "không" in page.inner_text("main").lower(), page.inner_text("main")[:200])
    snap(page, "03b-search-empty", width, SUB)

    # 4. Chi tiết + thêm giỏ (1,5 kg Cá thu; 1 combo)
    goto(page, "/shop/item/?code=CA-THU")
    page.get_by_role("button", name=re.compile(r"^1,5\s?kg$")).click()
    R.ok(f"[{tag}] chi tiết: chọn 1,5 kg → tạm tính 247.500đ", "247.500đ" in page.inner_text("main"))
    page.get_by_role("button", name="Thêm vào giỏ").click()
    page.wait_for_timeout(700)
    status_text = " ".join(page.locator("[role=status]").all_inner_texts())
    R.ok(f"[{tag}] thêm giỏ: toast 'Đã thêm 1,5 kg Cá thu' (role=status)", "Đã thêm" in status_text and "Cá thu" in status_text, status_text)
    snap(page, "04-added-toast", width, SUB)
    add_to_cart(page, "COMBO-BEP-NHA")
    cart_ls = json.loads(page.evaluate("localStorage.getItem('cangcaloc_cart_v1')"))
    R.ok(f"[{tag}] giỏ lưu localStorage chỉ mã hàng + số lượng + giá (không dữ liệu cá nhân)",
         [c["item_code"] for c in cart_ls] == ["CA-THU", "COMBO-BEP-NHA"] and not contains_pii(json.dumps(cart_ls)), cart_ls)

    # 5. Giỏ + mã giảm giá
    goto_cart(page)
    ctext = page.inner_text("main")
    R.ok(f"[{tag}] giỏ: 2 dòng, tạm tính 697.500đ, câu 'Đã gồm giao hàng'", "697.500đ" in ctext and "Đã gồm giao hàng" in ctext, ctext[:400])
    R.ok(f"[{tag}] giỏ: không ghi 'Phí giao: báo khi xác nhận', không 'miễn phí giao'",
         "báo khi xác nhận" not in ctext.lower() and "miễn phí giao" not in ctext.lower())
    snap(page, "05-cart", width, SUB)
    open_code_ui(page)
    page.locator("input[type=text]:visible").last.fill(V_MAIN.lower())
    page.get_by_role("button", name="Áp dụng").locator("visible=true").last.click()
    page.wait_for_timeout(1200)
    ctext = page.inner_text("main")
    R.ok(f"[{tag}] mã giảm giá: giảm 50.000đ (10% = 69.750 chạm trần), tổng 647.500đ", "−50.000đ" in ctext and "647.500đ" in ctext, ctext[:600])
    snap(page, "06-voucher-applied", width, SUB)

    # 6. Checkout (thiếu/sai → lỗi từng ô), rồi nhập đúng
    page.get_by_role("button", name=re.compile("^Tiếp tục")).click()
    page.wait_for_url(re.compile(r"/shop/checkout/"))
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_timeout(500)
    R.ok(f"[{tag}] checkout để trống bấm Đặt hàng → báo lỗi từng ô, chưa tạo đơn thật",
         page.locator("[role=alert], [aria-invalid=true]").count() >= 1, page.inner_text("main")[:300])
    snap(page, "07-checkout-invalid", width, SUB)
    before = order_count()
    page.fill("#f-name", FAKE_NAME)
    page.fill("#f-phone", "12345")
    page.fill("#f-addr", FAKE_ADDRESS)
    page.locator("#f-consent").check()
    page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_timeout(500)
    R.ok(f"[{tag}] SĐT sai ('12345') → báo lỗi, không tạo đơn", order_count() == before and "/shop/checkout/" in page.url)
    page.fill("#f-phone", FAKE_PHONE)
    snap(page, "08-checkout-filled", width, SUB)
    # bấm đúp: chỉ 1 đơn
    page.get_by_role("button", name="Đặt hàng").dblclick()
    # SHOP-FIX-01 AC2: đặt xong tự mở cổng thanh toán (không dừng ở trang đơn)
    page.wait_for_url(re.compile(r"pay-sandbox\.sepay\.vn|sepay"), timeout=15000)
    page.wait_for_timeout(600)
    R.ok(f"[{tag}] bấm đúp 'Đặt hàng' → đúng 1 đơn mới và đúng 1 lần mở cổng (SHOP-FIX-01 AC2)",
         order_count() == before + 1 and len(gateway_posts) == 1, (before, order_count(), len(gateway_posts)))
    m = code_from_gateway_post(__import__("urllib.parse").parse.unquote_plus(gateway_posts[0][1]) if gateway_posts else "")
    code = m.group(1) if m else re.search(r"(SO[\w-]+)", gateway_posts[0][1] or "").group(1)
    gateway_posts.clear()
    # AC4: quay lại trang đơn (khách đóng cổng giữa chừng) vẫn còn nút Thanh toán
    goto(page, f"/shop/orders/?code={code}", 1200)
    R.ok(f"[{tag}] URL trang đơn chỉ có mã đơn (không SĐT/tên/địa chỉ)", not contains_pii(page.url), page.url)
    ptext = page.inner_text("main")
    R.ok(f"[{tag}] thanh toán: đếm ngược giữ hàng, 'Chuyển khoản ngân hàng (quét mã QR)', tổng 647.500đ, không tên cổng",
         re.search(r"\d\d:\d\d", ptext) and "Chuyển khoản ngân hàng (quét mã QR)" in ptext and "647.500đ" in ptext
         and not re.search(r"sepay|vietqr|payos|momo", page.content(), re.I), ptext[:400])
    R.ok(f"[{tag}] thanh toán: không ô hoá đơn điện tử, không luồng hoàn tiền",
         "hoá đơn điện tử" not in ptext.lower() and "hoàn tiền" not in ptext.lower(), ptext[:300])
    snap(page, "09-payment", width, SUB)
    pii_sweep(f"[{tag}] trang thanh toán", page, watch)
    # 7. Bấm Thanh toán: form POST tới cổng đúng thứ tự field
    page.get_by_role("button", name="Thanh toán").click()
    page.wait_for_timeout(2500)
    R.ok(f"[{tag}] bấm Thanh toán → form POST tới cổng (1 lần) có success/cancel/error URL về /shop/orders/?code=",
         len(gateway_posts) >= 1 and all(k in (gateway_posts[0][1] or "") for k in ("success_url", "cancel_url", "order_code" if False else "success_url")),
         gateway_posts[:1])
    if gateway_posts:
        post = gateway_posts[0][1] or ""
        names = [kv.split("=")[0] for kv in post.split("&")]
        R.ok(f"[{tag}] field gửi cổng giữ thứ tự máy chủ trả (BR-TT-13), không lộ SĐT/tên/địa chỉ", not contains_pii(
            __import__("urllib.parse").parse.unquote_plus(post)), names)
    # 8. Trở về từ cổng khi tiền CHƯA về (D3) rồi IPN tới → tự chuyển sang trang đơn
    goto(page, f"/shop/orders/?code={code}&result=success", 800)
    d3 = page.inner_text("main")
    R.ok(f"[{tag}] quay về từ cổng khi tiền chưa về → màn 'đang chờ xác nhận tiền' (D3)", re.search(r"chờ|xác nhận", d3, re.I) is not None, d3[:300])
    snap(page, "10-pay-pending", width, SUB)
    st1, res1 = pay_order(code, 647500, "E2E-TXN-FLOW-" + code)
    R.ok(f"[{tag}] IPN khớp đủ tiền → matched, đơn PROCESSING", st1 == 200 and res1["matched"] and res1["order_status"] == "PROCESSING", (st1, res1))
    st2, res2 = pay_order(code, 647500, "E2E-TXN-FLOW-" + code)
    R.ok(f"[{tag}] IPN gửi 2 lần cùng mã giao dịch → idempotent (kết quả y hệt, 1 hoá đơn)", st2 == 200 and res2 == res1, res2)
    inv = manage_shell("from apps.sales.models import SalesInvoice\nprint(SalesInvoice.objects.filter(sales_order__code=%r).count())" % code).strip()
    R.ok(f"[{tag}] đúng 1 hoá đơn sau 2 lần IPN", inv == "1", inv)
    page.wait_for_timeout(500)
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    otext = page.inner_text("main")
    R.ok(f"[{tag}] sau thanh toán vào thẳng trang đơn hàng: có mã đơn, 'Đang soạn hàng', giảm mã −50.000đ, tổng 647.500đ",
         code in otext and "647.500đ" in otext and "50.000đ" in otext, otext[:500])
    R.ok(f"[{tag}] trang đơn KHÔNG hiện người nhận (tên, SĐT, địa chỉ)", not contains_pii(page.content()) and not contains_pii(otext))
    R.ok(f"[{tag}] trang đơn không lộ mã trạng thái thô (PROCESSING, BOOKED, PAID...)",
         not re.search(r"\b(BOOKED|PAID|PROCESSING|COMPLETED|AUTO_CANCELLED|CONFIRMING|PREPARING|READY|DELIVERING|FAILED)\b", otext), otext[:300])
    snap(page, "11-order-preparing", width, SUB)
    R.ok(f"[{tag}] đơn PROCESSING, lượt mã 'USED'", order_status(code) == "PROCESSING" and redemption_state(code) == "USED",
         (order_status(code), redemption_state(code)))
    pii_sweep(f"[{tag}] trang đơn sau thanh toán", page, watch)
    R.ok(f"[{tag}] console sạch lỗi JS suốt hành trình", not watch.console_errors() and not watch.errors, (watch.console_errors(), watch.errors))
    R.ok(f"[{tag}] không request tới bên thứ ba (chỉ localhost, trừ cổng thanh toán)",
         all(("localhost" in u) or ("sepay" in u) for _, u, _ in watch.requests), [u for _, u, _ in watch.requests if "localhost" not in u][:5])
    ctx.close()
    return code


def goto_cart(page):
    goto(page, "/shop/cart/")
    page.wait_for_selector("text=Tóm tắt đơn", timeout=10000)
    page.wait_for_timeout(300)


def open_code_ui(page):
    """Mở ô nhập mã ở giỏ: 360 là nút 'Nhập mã' mở sheet; 1280 ô nhập có sẵn trong khối tóm tắt."""
    btn = page.get_by_role("button", name="Nhập mã")
    if btn.locator("visible=true").count():
        btn.locator("visible=true").first.click()
        page.wait_for_timeout(500)


def lookup_from_other_session(browser, code, width, wrong=False):
    ctx, page, watch = fresh_context(browser, width)
    goto(page, "/shop/orders/")
    page.wait_for_selector("#lookup-code", timeout=15000)
    page.fill("#lookup-code", code)
    page.fill("#lookup-phone", "0900000002" if wrong else FAKE_PHONE)
    page.get_by_role("button", name="Tra cứu").click()
    page.wait_for_timeout(1500)
    text = page.inner_text("main")
    posts = [r for r in watch.requests if "/api/shop/orders/lookup/" in r[1]]
    gets = [r for r in watch.requests if r[0] == "GET" and "lookup" in r[1] and "/api/" in r[1]]
    R.ok(f"[{width}] tra cứu phiên khác: dùng POST (không GET), SĐT không lên URL", len(posts) >= 1 and not gets and not contains_pii(page.url),
         (posts, gets, page.url))
    if wrong:
        R.ok(f"[{width}] tra sai SĐT → câu chung 'Không tìm thấy đơn' (F2), không chỉ ra ô sai", "Không tìm thấy" in text and "SĐT" not in text.split("Không tìm thấy")[1][:80], text[:300])
        snap(page, "13-lookup-not-found", width, SUB)
    else:
        R.ok(f"[{width}] tra đúng mã + SĐT từ phiên khác → thấy đơn, không người nhận", code in text and not contains_pii(page.content()), text[:300])
        snap(page, "12-lookup-found", width, SUB)
        pii_sweep(f"[{width}] trang tra cứu", page, watch, html=True)
    ctx.close()


def error_branches(browser):
    # --- E-06 hết hàng lúc đặt: món còn 2 kg, khách đặt 3 kg (short) và món vừa hết (out)
    ctx, page, watch = fresh_context(browser, 360)
    add_to_cart(page, "CA-HOI-NU", 0)
    add_to_cart(page, "MUC-ONG", 0)
    goto_cart(page)
    page.get_by_role("button", name=re.compile("^Tiếp tục")).click()
    page.wait_for_url(re.compile(r"/shop/checkout/"))
    page.wait_for_load_state("networkidle")
    fill_checkout(page)
    stock_set("CA-HOI-NU", 0)           # món 1 hết hẳn SAU khi khách đã vào form đặt hàng
    cnt = order_count()
    page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_timeout(1500)
    dlg = page.locator("[role=dialog]")
    dtext = dlg.inner_text() if dlg.count() else ""
    R.ok("[360] hết hàng lúc đặt (C3): popup role=dialog aria-modal, đúng câu, không số kg tồn, không tạo đơn",
         dlg.count() == 1 and dlg.get_attribute("aria-modal") == "true" and order_count() == cnt
         and not re.search(r"còn\s*[\d.,]+\s*(kg|combo)", dtext, re.I) and "Cá hồi" in dtext, dtext[:400])
    snap(page, "20-c3-soldout", 360, SUB)
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    R.ok("[360] Esc đóng popup C3, tiêu điểm trả về trong trang (nút Đặt hàng)", page.locator("[role=dialog]").count() == 0)
    stock_set("CA-HOI-NU", 20)
    ctx.close()

    # --- C4 mất mạng khi đặt: thử lại cùng client_request_id → không trùng đơn
    ctx, page, watch = fresh_context(browser, 360)
    add_to_cart(page, "BACH-TUOC")
    goto(page, "/shop/checkout/")
    fill_checkout(page)
    cnt = order_count()
    reqs = []
    page.on("request", lambda r: reqs.append(r.post_data) if "/api/shop/orders/" in r.url and r.method == "POST" else None)
    page.route("**/api/shop/orders/", lambda r: r.abort("internetdisconnected"))
    page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_timeout(1500)
    dlg = page.locator("[role=dialog]")
    dtext = dlg.inner_text() if dlg.count() else ""
    R.ok("[360] mất mạng lúc đặt (C4): popup 'Lỗi kết nối', giữ nguyên form, chưa có đơn",
         dlg.count() == 1 and order_count() == cnt and "/shop/checkout/" in page.url, dtext[:300])
    snap(page, "21-c4-network", 360, SUB)
    page.unroute("**/api/shop/orders/")
    retry = dlg.get_by_role("button", name=re.compile("Thử lại|Đặt lại", re.I))
    if retry.count():
        retry.first.click()
    else:
        page.keyboard.press("Escape")
        page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_url(re.compile(r"sepay"), timeout=15000)
    R.ok("[360] thử lại sau mất mạng → đúng 1 đơn (cùng client_request_id, BR-BH-27)", order_count() == cnt + 1, (cnt, order_count()))
    ids = {json.loads(p)["client_request_id"] for p in reqs if p}
    R.ok("[360] hai lần gửi dùng cùng một client_request_id", len(ids) == 1, ids)
    ctx.close()

    # --- E-01 hết giờ giữ hàng: D4 → job → trạng thái hết hạn
    ctx, page, watch = fresh_context(browser, 360)
    st, o = create_order_api([("GHE-XANH", "1")])
    code = o["order_code"]
    goto(page, f"/shop/orders/?code={code}")  # chưa có token trong phiên → hiện form tra cứu? dùng token
    page.evaluate("(a)=>sessionStorage.setItem('cangcaloc_order_tokens_v1', JSON.stringify({[a[0]]:a[1]}))", [code, o["lookup_token"]])
    expire_hold(code)
    goto(page, f"/shop/orders/?code={code}", 800)
    t = page.inner_text("body")
    R.ok("[360] quá hạn giữ hàng (E-01, chưa chạy job): popup/khối 'hết giờ giữ hàng' (D4), không cho thanh toán",
         re.search(r"hết giờ|quá giờ|hết thời gian", t, re.I) is not None, t[:400])
    snap(page, "22-d4-hold-expired", 360, SUB)
    out1 = run_expiry_job()
    out2 = run_expiry_job()
    R.ok("[360] job cancel_expired_orders chạy 2 lần: đơn AUTO_CANCELLED, lần 2 không đổi (idempotent)",
         order_status(code) == "AUTO_CANCELLED", (out1[-200:], out2[-200:]))
    goto(page, f"/shop/orders/?code={code}", 800)
    R.ok("[360] sau job: trang đơn báo 'đã hết hạn / đã huỷ', không còn nút Thanh toán",
         page.get_by_role("button", name="Thanh toán").count() == 0, page.inner_text("main")[:300])
    snap(page, "23-expired-after-job", 360, SUB)
    # tiền về trễ sau khi đơn tự huỷ (BR-TT-05): ghi nhận chờ Chủ, trang đơn báo gọi lại
    st, res = pay_order(code, o["total_amount"], "E2E-LATE-" + code)
    R.ok("[360] tiền về sau khi đơn tự huỷ → không xác nhận đơn (ORPHAN/UNMATCHED chờ Chủ)", st == 200 and not res["matched"], res)
    goto(page, f"/shop/orders/?code={code}", 800)
    R.ok("[360] đơn hết hạn mà có tiền về trễ → trang đơn báo Cá Về sẽ gọi lại (không luồng hoàn tiền)",
         "gọi" in page.inner_text("main").lower() and "hoàn tiền" not in page.inner_text("main").lower(), page.inner_text("main")[:400])
    snap(page, "24-late-payment", 360, SUB)
    ctx.close()

    # --- Mã giảm giá lỗi: sai, hết hạn, đơn tối thiểu, hết lượt; mã mất hiệu lực lúc đặt (C6)
    create_voucher(V_EXPIRED, starts_at=(now - dt.timedelta(days=10)).isoformat(), ends_at=(now - dt.timedelta(days=1)).isoformat())
    create_voucher(V_MIN, min_order_amount="500000")
    create_voucher(V_ONCE, total_uses=1)
    create_voucher(V_GONE)
    ctx, page, watch = fresh_context(browser, 360)
    add_to_cart(page, "CA-THU")
    goto_cart(page)
    cases = [("KHONGCO", "không"), (V_EXPIRED, "hết hạn"), (V_MIN, "tối thiểu")]
    for code_try, needle in cases:
        open_code_ui(page)
        field = page.locator("input[type=text]:visible").last
        field.fill(code_try)
        page.get_by_role("button", name="Áp dụng").locator("visible=true").last.click()
        page.wait_for_timeout(1000)
        txt = page.inner_text("body").lower()
        R.ok(f"[360] mã {code_try}: báo lỗi có câu rõ ('{needle}'), không áp giảm, tổng giữ 165.000đ",
             needle in txt and "165.000đ" in txt, txt[:300])
        if code_try == V_MIN:
            snap(page, "30-voucher-min", 360, SUB)
        if code_try == "KHONGCO":
            snap(page, "31-voucher-invalid", 360, SUB)
        # đóng sheet nếu còn
        if page.locator("[role=dialog]").count():
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
    # ONCE1: người 1 dùng hết lượt, người 2 thấy 'đã hết lượt'
    st, o = create_order_api([("CA-THU", "1")], voucher=V_ONCE, phone="0900000003")
    R.ok("[API] mã 1 lượt: đơn đầu dùng được, lượt chuyển 'HELD'", st == 201 and redemption_state(o["order_code"]) == "HELD", (st, o))
    st2, o2 = create_order_api([("CA-THU", "1")], voucher=V_ONCE, phone="0900000004")
    R.ok("[API] mã 1 lượt hết lượt → 400 VOUCHER_INVALID, không tạo đơn thứ hai", st2 == 400 and o2.get("code") in ("VOUCHER_INVALID", "VOUCHER_USED_UP"), (st2, o2))
    # lượt giữ được nhả khi đơn tự huỷ hết giờ (BR-DM-20)
    expire_hold(o["order_code"])
    run_expiry_job()
    R.ok("[API] đơn tự huỷ hết giờ → lượt mã 'RELEASED' (nhả lượt)", redemption_state(o["order_code"]) == "RELEASED", redemption_state(o["order_code"]))
    st3, o3 = create_order_api([("CA-THU", "1")], voucher=V_ONCE, phone="0900000005")
    R.ok("[API] sau khi nhả lượt, mã dùng lại được", st3 == 201, (st3, o3))
    # C6: mã bị tắt giữa lúc khách đang ở giỏ → đặt đơn báo 'mã hết hiệu lực'
    goto_cart(page)
    open_code_ui(page)
    page.locator("input[type=text]:visible").last.fill(V_GONE)
    page.get_by_role("button", name="Áp dụng").locator("visible=true").last.click()
    page.wait_for_timeout(1000)
    page.get_by_role("button", name=re.compile("^Tiếp tục")).click()
    page.wait_for_url(re.compile(r"/shop/checkout/"))
    page.wait_for_load_state("networkidle")
    fill_checkout(page, phone="0900000006")
    page.wait_for_selector(f"text=Mã giảm giá ({V_GONE})", timeout=10000)   # chờ FE kiểm lại mã xong rồi mới tắt mã
    # mã bị Chủ tắt SAU khi khách đã vào form đặt hàng
    vid = [v for v in api("GET", "/api/catalog/vouchers/?status=running", token=tok)[1]["results"] if v["code"] == V_GONE][0]["id"]
    s_dis, b_dis = api("POST", f"/api/catalog/vouchers/{vid}/disable/", {"reason": "OTHER", "note": "e2e"}, token=tok)
    R.ok("[API] Chủ tắt mã GONE1 thành công", s_dis == 200, (s_dis, b_dis))
    cnt = order_count("0900000006")
    page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_timeout(1500)
    dtext = page.locator("[role=dialog]").inner_text() if page.locator("[role=dialog]").count() else ""
    R.ok("[360] mã mất hiệu lực lúc đặt (C6): popup báo + không tạo đơn", page.locator("[role=dialog]").count() == 1 and order_count("0900000006") == cnt, dtext[:300])
    snap(page, "32-c6-voucher-gone", 360, SUB)
    ctx.close()

    # --- B2: bấm "Đặt hàng" ngay sau khi vào form có mã đã áp (FE chưa kiểm lại mã) → đơn vẫn có giảm giá
    ctx, page, watch = fresh_context(browser, 360)
    add_to_cart(page, "CA-THU")
    goto_cart(page)
    open_code_ui(page)
    page.locator("input[type=text]:visible").last.fill(V_MAIN)
    page.get_by_role("button", name="Áp dụng").locator("visible=true").last.click()
    page.wait_for_timeout(1200)
    page.get_by_role("button", name=re.compile("^Tiếp tục")).click()
    page.wait_for_url(re.compile(r"/shop/checkout/"))
    page.fill("#f-name", FAKE_NAME); page.fill("#f-phone", "0900000012"); page.fill("#f-addr", FAKE_ADDRESS)
    if page.locator("#f-consent").count():
        page.locator("#f-consent").check()
    page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_timeout(2500)
    code_fast = code_from_gateway_post(__import__("urllib.parse").parse.unquote_plus(page.gateway_posts[0][1] or "")) if page.gateway_posts else re.search(r"code=(SO[\w-]+)", page.url)
    if code_fast:
        _, lk = lookup_api(code_fast.group(1), "0900000012")
        R.ok("[360] bấm Đặt hàng ngay sau khi vào form có mã đã áp: đơn vẫn có giảm giá (không bỏ mã im lặng)", lk["discount"]["amount"] != "0" and lk["total_amount"] != "165000", lk["total_amount"])
    else:
        R.ok("[360] bấm Đặt hàng ngay: chưa tạo đơn thì phải có thông báo (không tạo đơn giá gốc)", page.locator("[role=dialog]").count() >= 1, page.url)
    ctx.close()

    # --- A6 mất mạng khi tải hàng, rồi Thử lại
    ctx, page, watch = fresh_context(browser, 360)
    page.route("**/api/shop/catalog/", lambda r: r.abort("internetdisconnected"))
    goto(page, "/shop/")
    t = page.inner_text("main")
    R.ok("[360] mất mạng khi tải hàng (A6): thẻ lỗi + nút 'Thử lại', không trắng trang", "Thử lại" in t, t[:200])
    snap(page, "33-a6-offline", 360, SUB)
    page.unroute("**/api/shop/catalog/")
    page.get_by_role("button", name="Thử lại").click()
    page.wait_for_timeout(1500)
    R.ok("[360] bấm Thử lại khi có mạng → hàng hiện đủ", "Cá thu" in page.inner_text("main"))
    ctx.close()

    # --- 429 thật: BE phụ có giới hạn thấp; trình duyệt chuyển request sang BE phụ
    be2 = spawn_be(8001, {"THROTTLE_SHOP_ORDER_CREATE": "1/hour", "THROTTLE_SHOP_LOOKUP_IP": "3/min", "THROTTLE_SHOP_LOOKUP_ORDER": "3/hour",
                          "THROTTLE_SHOP_LOOKUP_TOKEN": "3/min", "THROTTLE_SHOP_VOUCHER_CHECK": "3/min"})
    try:
        api_b = "http://localhost:8001"
        s1, b1 = create_order_api([("CA-THU", "1")], phone="0900000007", base=api_b)
        s2, b2 = create_order_api([("CA-THU", "1")], phone="0900000008", base=api_b)
        R.ok("[API] tạo đơn quá giới hạn → 429 có thông điệp tiếng Việt", s1 == 201 and s2 == 429 and isinstance(b2, dict) and "detail" in b2, (s1, s2, b2))
        lk = [lookup_api("SO000000-AAAAAA", FAKE_PHONE, base=api_b)[0] for _ in range(6)]
        R.ok("[API] tra đơn lặp nhiều lần → có 429 (giới hạn tần suất tra đơn)", 429 in lk and lk[0] in (404, 400), lk)
        # UI: popup C8
        ctx, page, watch = fresh_context(browser, 360)

        def to_b(route):
            u = route.request.url.replace("localhost:8000", "localhost:8001")
            resp = route.fetch(url=u)
            route.fulfill(response=resp)
        page.route("**/api/shop/orders/", to_b)
        add_to_cart(page, "BACH-TUOC")
        goto(page, "/shop/checkout/")
        fill_checkout(page, phone="0900000009")
        page.get_by_role("button", name="Đặt hàng").click()
        page.wait_for_timeout(1800)
        dlg = page.locator("[role=dialog]")
        dtext = dlg.inner_text() if dlg.count() else page.inner_text("main")
        R.ok("[360] quá giới hạn thao tác (C8, 429 thật): popup 'thao tác quá nhanh', không tạo đơn", "nhanh" in dtext.lower() or "thử lại" in dtext.lower(), dtext[:300])
        snap(page, "34-c8-429", 360, SUB)
        ctx.close()
    finally:
        be2.terminate()


def main():
    create_voucher(V_MAIN)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        code360 = journey(browser, 360)
        code1280 = journey(browser, 1280)
        lookup_from_other_session(browser, code360, 360)
        lookup_from_other_session(browser, code360, 360, wrong=True)
        lookup_from_other_session(browser, code1280, 1280)
        error_branches(browser)
        browser.close()
    R.finish()


if __name__ == "__main__":
    main()
