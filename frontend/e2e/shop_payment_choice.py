"""
E2E SHOP-FIX-01: chọn phương thức thanh toán ngay ở form đặt hàng; đặt xong vào thẳng cổng thanh toán.
Chạy: python3 frontend/e2e/run_shop_e2e.py --suite payment_choice   (cổng thật được chặn: dừng ở bước trình duyệt chuyển sang URL cổng).
Dữ liệu cá nhân 100% giả. Mã: BR-BH-27 (chống đặt trùng), BR-TT-01/13 (form POST cổng), bất biến 9.
"""
import json
import re
import urllib.parse

from playwright.sync_api import sync_playwright

from shop_e2e_lib import *

R = Report("payment_choice")
SUB = "qa"
GATEWAY = re.compile(r"https://(?!localhost).*sepay.*")
FAIL_MSG = "Chưa mở được trang thanh toán. Thử lại."


def new_page(browser, width):
    ctx = browser.new_context(viewport={"width": width, "height": 800 if width < 600 else 900})
    page = ctx.new_page()
    page.gateway_posts = []

    def handler(route):
        page.gateway_posts.append((route.request.url, route.request.post_data))
        route.fulfill(status=200, content_type="text/html", body="<html><body>gateway giả lập</body></html>")
    page.route(GATEWAY, handler)
    page.creates = []
    page.on("request", lambda r: page.creates.append(r.post_data) if r.method == "POST" and re.search(r"/api/shop/orders/$", r.url) else None)
    return ctx, page, PageWatch(page)


def to_checkout(page, item="CA-THU"):
    add_to_cart(page, item)
    goto(page, "/shop/checkout/", 900)


def code_of(post):
    m = re.search(r"code%3D(SO[\w-]+)", post or "") or re.search(r"code=(SO[\w-]+)", urllib.parse.unquote_plus(post or ""))
    return m.group(1) if m else None


def ac1(browser, width):
    tag = str(width)
    ctx, page, watch = new_page(browser, width)
    to_checkout(page)
    fs = page.locator("fieldset", has=page.locator("legend", has_text="Phương thức thanh toán"))
    R.ok(f"[{tag}] AC1 có fieldset + legend 'Phương thức thanh toán'", fs.count() == 1)
    radio = page.locator("input[type=radio][name=payment_method]")
    R.ok(f"[{tag}] AC1 đúng 1 radio, đã chọn sẵn", radio.count() == 1 and radio.is_checked())
    R.ok(f"[{tag}] AC1 radio có tên truy cập 'Chuyển khoản ngân hàng (quét mã QR)'",
         "Chuyển khoản ngân hàng (quét mã QR)" in fs.inner_text() and page.get_by_role("radio", name=re.compile("Chuyển khoản ngân hàng")).count() == 1)
    ay = page.locator("#f-addr").bounding_box()["y"]
    fy = fs.bounding_box()["y"]
    cy = page.locator("#f-consent").bounding_box()["y"] if page.locator("#f-consent").count() else 10**6
    R.ok(f"[{tag}] AC1 khối nằm dưới ô địa chỉ và trước ô đồng ý", ay < fy < cy, (ay, fy, cy))
    card_h = page.locator("label[for=f-pay-qr]").bounding_box()["height"]
    R.ok(f"[{tag}] AC1 vùng chạm >= 44px", card_h >= 44, card_h)
    R.ok(f"[{tag}] AC1 không ghi tên nhà cung cấp cổng (HTML)", not re.search(r"sepay|vietqr|payos|momo|vnpay", page.content(), re.I))
    R.ok(f"[{tag}] AC5 ô đồng ý KHÔNG tick sẵn", page.locator("#f-consent").count() == 0 or not page.locator("#f-consent").is_checked())
    R.ok(f"[{tag}] AC5 không cuộn ngang", no_hscroll(page, width))
    # bàn phím: Tab từ ô địa chỉ tới radio
    page.focus("#f-addr")
    focused = []
    for _ in range(6):
        page.keyboard.press("Tab")
        focused.append(page.evaluate("document.activeElement.id || document.activeElement.tagName + ':' + (document.activeElement.getAttribute('name')||'')"))
        if focused[-1] == "f-pay-qr":
            break
    R.ok(f"[{tag}] AC1 bàn phím: Tab từ ô địa chỉ tới được radio thanh toán", "f-pay-qr" in focused, focused)
    snap(page, "ac1-checkout-form", width, SUB, full=True)
    # cuộn xuống cuối: khối thanh toán và ô đồng ý không bị thanh "Đặt hàng" dính đáy che
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)"); page.wait_for_timeout(400)
    def uncovered(sel):
        return page.evaluate("""(sel)=>{const e=document.querySelector(sel);e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();
          const t=document.elementFromPoint(r.left+Math.min(20,r.width/2), r.top+r.height/2);return e===t||e.contains(t)||(t&&t.closest('label')===e.closest('label')&&!!t.closest('label'))}""", sel)
    R.ok(f"[{tag}] AC1 cuộn tới khối thanh toán: không bị thanh dính đáy che", uncovered("label[for=f-pay-qr]"))
    R.ok(f"[{tag}] AC1 ô đồng ý cũng không bị che", uncovered("#f-consent") if page.locator("#f-consent").count() else True)
    page.evaluate("document.querySelector('label[for=f-pay-qr]').scrollIntoView({block:'center'})"); page.wait_for_timeout(300)
    snap(page, "ac1-payment-block", width, SUB)
    page.keyboard.press("ArrowDown"); page.keyboard.press("ArrowUp")
    R.ok(f"[{tag}] AC1 phím mũi tên không bỏ chọn radio", radio.is_checked())
    R.ok(f"[{tag}] 0 lỗi console ở form", not watch.errors and not watch.console_errors(), (watch.errors, watch.console_errors()))
    ctx.close()


def ac2_ac4(browser, width, phone):
    tag = str(width)
    ctx, page, watch = new_page(browser, width)
    to_checkout(page)
    fill_checkout(page, phone=phone)
    before = order_count(phone)
    # làm chậm tạo đơn để quan sát nút "đang xử lý"
    def slow(route):
        page.wait_for_timeout(1500)
        route.continue_()
    page.route(re.compile(r"/api/shop/orders/$"), slow)
    btn = page.get_by_role("button", name=re.compile("Đặt hàng|Đang đặt"))
    btn.dblclick()
    page.wait_for_timeout(300)
    txt = btn.first.inner_text()
    R.ok(f"[{tag}] AC2 sau bấm: nút ở trạng thái đang xử lý (disabled hoặc chữ 'Đang')",
         btn.first.is_disabled() or "Đang" in txt or page.locator("button[aria-busy=true]").count() > 0, txt)
    snap(page, "ac2-submitting", width, SUB)
    page.wait_for_url(GATEWAY, timeout=20000)
    page.wait_for_timeout(500)
    R.ok(f"[{tag}] AC2 bấm đúp: đúng 1 đơn, đúng 1 request tạo đơn, đúng 1 lần mở cổng",
         order_count(phone) == before + 1 and len(page.creates) == 1 and len(page.gateway_posts) == 1,
         (before, order_count(phone), len(page.creates), len(page.gateway_posts)))
    R.ok(f"[{tag}] AC2 vào thẳng URL cổng (không dừng ở trang đơn): {page.url[:45]}", "/shop/orders" not in page.url and "sepay" in page.url)
    post = page.gateway_posts[0][1] or ""
    dec = urllib.parse.unquote_plus(post)
    code = code_of(post)
    R.ok(f"[{tag}] AC2 form gửi cổng có mã đơn, success/cancel/error URL, không SĐT/tên/địa chỉ",
         bool(code) and all(k in dec for k in ("success_url", "cancel_url")) and not contains_pii(dec), dec[:200])
    R.ok(f"[{tag}] AC2 giỏ đã xoá sau khi đặt (localStorage không chứa dữ liệu cá nhân)",
         not contains_pii(storage_dump(page)))
    # AC4: khách đóng cổng/quay lại → trang đơn còn nút Thanh toán
    goto(page, f"/shop/orders/?code={code}", 1200)
    R.ok(f"[{tag}] AC4 quay lại trang đơn: còn nút 'Thanh toán'", page.get_by_role("button", name="Thanh toán").count() >= 1, page.inner_text("main")[:200])
    snap(page, "ac4-back-to-order", width, SUB)
    page.gateway_posts.clear()
    page.get_by_role("button", name="Thanh toán").first.click()
    page.wait_for_timeout(2500)
    R.ok(f"[{tag}] AC4 bấm 'Thanh toán' ở trang đơn → mở cổng lại, không tạo đơn mới",
         len(page.gateway_posts) == 1 and order_count(phone) == before + 1, (len(page.gateway_posts), order_count(phone)))
    goto(page, f"/shop/orders/?code={code}&result=cancel", 1200)
    R.ok(f"[{tag}] AC4 quay về từ cổng với result=cancel: còn nút Thanh toán / Thanh toán lại",
         page.get_by_role("button", name=re.compile("Thanh toán")).count() >= 1, page.inner_text("main")[:200])
    snap(page, "ac4-cancel", width, SUB)
    R.ok(f"[{tag}] không dữ liệu cá nhân ở URL/storage/console", not contains_pii(page.url) and not contains_pii(storage_dump(page))
         and not contains_pii(" ".join(t for _, t in watch.console)))
    # E6: server là chủ — IPN xong thì không còn nút
    st, res = pay_order(code, int(float(lookup_api(code, phone)[1]["total_amount"])), "QA-FIX01-" + code)
    page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(1500)
    R.ok(f"[{tag}] AC4/E6 đơn đã trả (server): trang đơn không còn nút Thanh toán", st == 200 and page.get_by_role("button", name=re.compile("^Thanh toán")).count() == 0,
         page.inner_text("main")[:200])
    R.ok(f"[{tag}] 0 lỗi console", not watch.errors and not watch.console_errors(), (watch.errors, watch.console_errors()))
    ctx.close()


def ac3(browser, width, phone, mode):
    tag = f"{width}/{mode}"
    ctx, page, watch = new_page(browser, width)
    to_checkout(page)
    fill_checkout(page, phone=phone)
    before = order_count(phone)
    cpat = re.compile(r"/api/shop/orders/[^/]+/checkout/")
    if mode == "503":
        page.route(cpat, lambda r: r.fulfill(status=503, content_type="application/json",
                                             body='{"code":"CHECKOUT_UNAVAILABLE","detail":"Cổng thanh toán tạm không khả dụng."}'))
    elif mode == "network":
        page.route(cpat, lambda r: r.abort("internetdisconnected"))
    else:
        page.route(cpat, lambda r: r.fulfill(status=500, content_type="text/plain", body="boom"))
    page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_url(re.compile(r"/shop/orders/\?code="), timeout=15000)
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
    main = page.inner_text("main")
    R.ok(f"[{tag}] AC3 vào trang đơn D1 có câu lỗi '{FAIL_MSG}'", FAIL_MSG in main, main[:250])
    R.ok(f"[{tag}] AC3 có nút 'Thanh toán'", page.get_by_role("button", name="Thanh toán").count() >= 1)
    R.ok(f"[{tag}] AC3 không tạo đơn thứ hai (DB = +1, 1 request tạo đơn, chưa mở cổng)",
         order_count(phone) == before + 1 and len(page.creates) == 1 and not page.gateway_posts, (before, order_count(phone), len(page.creates)))
    R.ok(f"[{tag}] AC3 URL không chứa dữ liệu cá nhân", not contains_pii(page.url) and "pay=failed" in page.url, page.url)
    R.ok(f"[{tag}] AC5 không cuộn ngang ở D1 lỗi", no_hscroll(page, width))
    snap(page, f"ac3-d1-error-{mode}", width, SUB)
    if mode == "503":
        page.unroute(cpat)
        page.get_by_role("button", name="Thanh toán").first.click()
        page.wait_for_timeout(2500)
        R.ok(f"[{tag}] AC3 bấm 'Thanh toán' thử lại (cổng đã ổn) → mở cổng, vẫn 1 đơn",
             len(page.gateway_posts) == 1 and order_count(phone) == before + 1, (len(page.gateway_posts), order_count(phone)))
    R.ok(f"[{tag}] không dữ liệu cá nhân ở storage", not contains_pii(storage_dump(page)))
    ctx.close()


def ac5_extra(browser):
    # Hết hàng sau khi vào form (C3): popup, không đơn, không cổng
    ctx, page, watch = new_page(browser, 360)
    add_to_cart(page, "CA-HOI-NU"); goto(page, "/shop/checkout/", 900)
    fill_checkout(page, phone="0900000071")
    stock_set("CA-HOI-NU", 0)
    cnt = order_count("0900000071")
    page.get_by_role("button", name="Đặt hàng").click(); page.wait_for_timeout(1500)
    R.ok("[360] AC5 C3 hết hàng: popup role=dialog, không tạo đơn, không mở cổng, nút đặt hàng dùng lại được",
         page.locator("[role=dialog]").count() == 1 and order_count("0900000071") == cnt and not page.gateway_posts
         and "/shop/checkout/" in page.url)
    snap(page, "ac5-c3-soldout", 360, SUB)
    stock_set("CA-HOI-NU", 20)
    ctx.close()
    # Mất mạng khi tạo đơn (C4): thử lại cùng client_request_id -> 1 đơn rồi vào cổng
    ctx, page, watch = new_page(browser, 360)
    to_checkout(page, "BACH-TUOC"); fill_checkout(page, phone="0900000072")
    cnt = order_count("0900000072")
    page.route("**/api/shop/orders/", lambda r: r.abort("internetdisconnected"))
    page.get_by_role("button", name="Đặt hàng").click(); page.wait_for_timeout(1500)
    R.ok("[360] AC5 C4 mất mạng khi tạo đơn: popup, không đơn, ở lại form", page.locator("[role=dialog]").count() == 1
         and order_count("0900000072") == cnt and "/shop/checkout/" in page.url)
    snap(page, "ac5-c4-network", 360, SUB)
    page.unroute("**/api/shop/orders/")
    retry = page.locator("[role=dialog]").get_by_role("button", name=re.compile("Thử lại|Đặt lại", re.I))
    if retry.count():
        retry.first.click()
    else:
        page.keyboard.press("Escape"); page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_url(GATEWAY, timeout=15000)
    ids = {json.loads(p)["client_request_id"] for p in page.creates if p}
    R.ok("[360] AC5 C4 thử lại: đúng 1 đơn, cùng client_request_id, rồi vào cổng", order_count("0900000072") == cnt + 1 and len(ids) == 1, (order_count("0900000072"), ids))
    ctx.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w in (360, 1280):
            ac1(browser, w)
        ac2_ac4(browser, 360, "0900000061")
        ac2_ac4(browser, 1280, "0900000062")
        ac3(browser, 360, "0900000063", "503")
        ac3(browser, 1280, "0900000064", "503")
        ac3(browser, 360, "0900000065", "network")
        ac3(browser, 360, "0900000066", "500")
        ac5_extra(browser)
        browser.close()
    R.finish()


if __name__ == "__main__":
    import json
    main()
