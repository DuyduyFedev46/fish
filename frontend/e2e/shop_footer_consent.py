"""
E2E chân trang pháp lý, ô đồng ý chính sách, chính sách đổi giữa chừng (409), shop đóng (503), quay về từ cổng thanh toán
(SHOP-1-05, 3-03, 4-02; go-live GL-01…GL-04; BR-BH-17, 25, 27; bất biến 9). BE thật; chỉ chặn/giả phản hồi ở ca ghi rõ.
Thay `golive_footer_checks.py` và `qa-lo6-sr21-shop.py` (bám footer cũ, dữ liệu dựng bằng route).
Chạy: python3 frontend/e2e/run_shop_e2e.py --suite footer_consent
"""
import json
import re
import uuid

from playwright.sync_api import sync_playwright

from shop_e2e_lib import *

R = Report("footer_consent")
ROUTES = ["/", "/shop/", "/shop/item/?code=CA-THU", "/shop/cart/", "/shop/checkout/", "/shop/orders/", "/about/", "/blog/", "/pages/?slug=doi-tra"]
real_site = api("GET", "/api/public/site-info/")[1]
footer_links = api("GET", "/api/public/content/footer-links/")[1]


def new(browser, width):
    ctx = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800})
    page = ctx.new_page()
    # SHOP-FIX-01: đặt xong tự sang cổng thanh toán; chặn cổng ngoài, ghi lại form POST
    page.gateway_posts = []
    page.route(re.compile(r"https://(?!localhost).*sepay.*"), lambda r: (page.gateway_posts.append(r.request.post_data),
               r.fulfill(status=200, content_type="text/html", body="<html><body>gateway giả lập</body></html>")))
    return ctx, page, PageWatch(page)


def cart_with(page, lines):
    page.goto(SHOP + "/shop/orders/")
    page.wait_for_load_state("networkidle")
    page.evaluate("(l)=>localStorage.setItem('cangcaloc_cart_v1', JSON.stringify(l))", lines)


LINES = [{"item_code": "CA-THU", "name": "Cá thu", "unit": "kg", "price": "165000", "qty": 1}]


def to_checkout(page):
    cart_with(page, LINES)
    goto(page, "/shop/checkout/", 900)


def fill(page, phone=FAKE_PHONE, consent=True):
    page.fill("#f-name", FAKE_NAME)
    page.fill("#f-phone", phone)
    page.fill("#f-addr", FAKE_ADDRESS)
    if consent and page.locator("#f-consent").count():
        page.locator("#f-consent").check()


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ============================================================ chân trang
    for width in (360, 1280):
        tag = f"[{width}]"
        ctx, page, watch = new(browser, width)
        bad = []
        for r in ROUTES:
            goto(page, r, 600)
            try:
                page.wait_for_function("() => /MST/.test(document.querySelector('footer')?.innerText || '')", timeout=6000)
            except Exception:  # noqa: BLE001
                pass
            foot = page.locator("footer").first.inner_text()
            compact = r in ("/shop/cart/", "/shop/checkout/")   # giỏ và đặt hàng dùng chân trang gọn (DesktopCart/Checkout)
            need = ["Cá Về (dữ liệu giả)", "MST 0000000000"] + ([] if compact else ["00A-000000", "gia@example.test"])
            if not all(n in foot for n in need) or re.search(r"null|undefined|\[\s*\]", foot):
                bad.append((r, foot[:120]))
            if "Chính sách" not in page.locator("footer").first.inner_text() and not page.locator("footer a[href*='/pages/']").count():
                bad.append((r, "thiếu liên kết chính sách"))
        R.ok(f"{tag} chân trang trên {len(ROUTES)} đường dẫn: tên người bán, MST, GCN ĐKKD, email từ site-info, không null/undefined", not bad, bad[:2])
        goto(page, "/shop/", 700)
        hrefs = page.eval_on_selector_all("footer a[href*='/pages/']", "els => els.map(e => e.getAttribute('href'))")
        slugs_api = [l.get("slug") for l in (footer_links.get("results", footer_links) if isinstance(footer_links, dict) else footer_links)]
        R.ok(f"{tag} liên kết chính sách ở chân trang lấy từ CMS (đủ slug footer-links)", all(any(f"slug={s}" in h for h in hrefs) for s in slugs_api if s), (slugs_api, hrefs[:6]))
        snap(page, "footer", width, "footer")
        # người bán chưa đủ thông tin → ẩn dòng pháp lý, không vỡ
        page.route("**/api/public/site-info/", lambda r: r.fulfill(status=200, content_type="application/json", headers={"access-control-allow-origin": "*"},
                                                                  body=json.dumps({**real_site, "seller": {k: None for k in real_site["seller"]}, "seller_complete": False})))
        goto(page, "/shop/", 700)
        foot = page.locator("footer").first.inner_text()
        R.ok(f"{tag} site-info người bán rỗng: chân trang không vỡ, không 'null', không MST rỗng", "null" not in foot and "undefined" not in foot and "MST" not in foot and page.locator("footer").count() >= 1, foot[:150])
        page.unroute("**/api/public/site-info/")
        page.route("**/api/public/site-info/", lambda r: r.abort("internetdisconnected"))
        goto(page, "/shop/", 700)
        R.ok(f"{tag} site-info lỗi mạng: trang vẫn dùng được (có danh mục và chân trang)", page.locator("footer").count() >= 1 and "Cá thu" in page.inner_text("main"))
        page.unroute("**/api/public/site-info/")
        R.ok(f"{tag} chân trang: console sạch lỗi JS", not watch.errors, watch.errors[:2])
        ctx.close()

    # ============================================================ ô đồng ý
    for width in (360, 1280):
        tag = f"[{width}]"
        ctx, page, watch = new(browser, width)
        posts = []
        page.on("request", lambda r: posts.append(r.post_data) if r.method == "POST" and "/api/shop/orders/" in r.url and "lookup" not in r.url and "checkout" not in r.url else None)
        to_checkout(page)
        box = page.locator("#f-consent")
        R.ok(f"{tag} ô đồng ý không tick sẵn, có link chính sách mở tab mới, có câu 'máy chủ đặt ở nước ngoài'", box.count() == 1 and not box.is_checked()
             and page.locator("a[href*='quyen-rieng-tu'][target=_blank]").count() >= 1 and "nước ngoài" in page.inner_text("main"))
        fill(page, consent=False)
        page.get_by_role("button", name="Đặt hàng").click()
        page.wait_for_timeout(700)
        R.ok(f"{tag} chưa tick mà bấm Đặt hàng → báo lỗi ô đồng ý, KHÔNG gửi POST", not posts and "đánh dấu đồng ý" in page.inner_text("main").lower(), (posts, page.inner_text("main")[:200]))
        snap(page, "consent-error", width, "footer")
        page.locator("#f-consent").check()
        cnt = order_count()
        page.get_by_role("button", name="Đặt hàng").click()
        page.wait_for_url(re.compile(r"sepay"), timeout=15000)   # SHOP-FIX-01: vào thẳng cổng
        body = json.loads(posts[0])
        R.ok(f"{tag} tick rồi đặt → payload có privacy_consent {{accepted: true, policy_version_id: số nguyên}}, đơn tạo đúng 1", body["privacy_consent"]["accepted"] is True
             and isinstance(body["privacy_consent"]["policy_version_id"], int) and order_count() == cnt + 1, body.get("privacy_consent"))
        R.ok(f"{tag} sau khi đặt: URL, storage, console không chứa dữ liệu cá nhân", not contains_pii(page.url + storage_dump(page) + " ".join(t for _, t in watch.console)))
        page.reload(); page.wait_for_load_state("networkidle")
        to_checkout(page)
        R.ok(f"{tag} F5 / vào lại form: không nhớ tên, SĐT, địa chỉ", page.input_value("#f-name") == "" and page.input_value("#f-phone") == "" and page.input_value("#f-addr") == "")
        ctx.close()

    # ---- 409 chính sách đổi giữa chừng: chính BE trả 409 (ta chỉ đưa FE một version_id cũ giả)
    ctx, page, watch = new(browser, 360)
    stale = {"n": 0}
    def policy_route(route):
        real = route.fetch()
        data = real.json()
        if stale["n"] == 0:
            data["version_id"] = 999999   # FE tưởng đây là phiên bản hiện hành; BE sẽ báo 409
        route.fulfill(response=real, body=json.dumps(data))
    page.route("**/api/public/content/pages/by-role/privacy/", policy_route)
    posts = []
    page.on("request", lambda r: posts.append(json.loads(r.post_data)) if r.method == "POST" and r.url.rstrip("/").endswith("/api/shop/orders") else None)
    to_checkout(page)
    fill(page)
    cnt = order_count()
    page.get_by_role("button", name="Đặt hàng").click()
    page.wait_for_timeout(1500)
    dlg = page.locator("[role=dialog]")
    dt = dlg.inner_text() if dlg.count() else ""
    R.ok("[360] BE trả 409 POLICY_CHANGED thật → popup 'Chính sách vừa cập nhật' có link xem chính sách, chưa tạo đơn", dlg.count() == 1 and "Chính sách" in dt and order_count() == cnt, dt[:300])
    snap(page, "policy-changed", 360, "footer")
    stale["n"] = 1   # từ giờ trả version thật
    btn = dlg.get_by_role("button", name=re.compile("đồng ý|Đồng ý|tiếp tục|Tiếp tục|Xác nhận", re.I))
    if btn.count():
        btn.first.click()
        page.wait_for_timeout(1500)
    if "sepay" not in page.url:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        if page.locator("#f-consent").count() and not page.locator("#f-consent").is_checked():
            page.locator("#f-consent").check()
        page.get_by_role("button", name="Đặt hàng").click()
        page.wait_for_timeout(2000)
    R.ok("[360] sau khi đồng ý lại: gửi lại với version mới, đơn tạo đúng 1, không trùng", "sepay" in page.url and order_count() == cnt + 1, (page.url, order_count() - cnt))
    ctx.close()

    # ---- 503 Shop đóng (thiếu chính sách đã đăng): thử thật bằng cách gỡ đăng trang chính sách riêng tư
    ctx, page, watch = new(browser, 360)
    to_checkout(page)
    fill(page)
    out = manage_shell(
        "from apps.content.models import Entry\nfrom apps.content.entries import services as s\nfrom django.contrib.auth import get_user_model\n"
        "e=Entry.objects.get(slug='quyen-rieng-tu')\nu=get_user_model().objects.get(username='qa_owner')\n"
        "try:\n    s.unpublish_entry(entry=e, actor=u, row_version=e.row_version, reason='e2e shop đóng')\n    print('UNPUB')\nexcept Exception as ex:\n    print('ERR', ex)\n")
    if "UNPUB" in out:
        cnt = order_count()
        page.get_by_role("button", name="Đặt hàng").click()
        page.wait_for_timeout(1500)
        t = page.inner_text("body")
        R.ok("[360] chính sách bị gỡ → BE 503 SHOP_CLOSED thật: màn 'tạm ngưng nhận đơn', giỏ vẫn giữ, không tạo đơn",
             "tạm ngưng" in t.lower() and order_count() == cnt and "cangcaloc_cart_v1" in storage_dump(page), t[:300])
        snap(page, "shop-closed", 360, "footer")
    else:
        R.skip("[360] 503 SHOP_CLOSED thật", f"không gỡ đăng được bằng service: {out[-120:]}")
    ctx.close()
    # khôi phục: nạp lại nội dung (đăng lại trang chính sách)
    info = env_info()
    subprocess = __import__("subprocess")
    env = {**os.environ, **info["be_env"]}
    rr = subprocess.run([str(BACKEND / ".venv/bin/python"), "manage.py", "load_shop_content", "--author", "qa_owner", "--publish", "--overwrite"],
                        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=300)
    R.ok("khôi phục: nạp lại nội dung → chính sách riêng tư đăng lại, Shop nhận đơn lại", api("GET", "/api/public/content/pages/by-role/privacy/")[0] == 200, rr.stdout[-150:])

    # ============================================================ quay về từ cổng thanh toán
    st, o = create_order_api([("CA-THU", "1")])
    code, ltoken = o["order_code"], o["lookup_token"]
    for width in (360, 1280):
        tag = f"[{width}]"
        ctx, page, watch = new(browser, width)
        page.goto(SHOP + "/shop/orders/")
        page.wait_for_load_state("networkidle")
        page.evaluate("(a)=>sessionStorage.setItem('cangcaloc_order_tokens_v1', JSON.stringify({[a[0]]:a[1]}))", [code, ltoken])
        for result, needle in (("cancel", "chưa"), ("error", "chưa"), ("success", "chờ")):
            goto(page, f"/shop/orders/?code={code}&result={result}", 900)
            t = page.inner_text("main")
            R.ok(f"{tag} quay về result={result} khi chưa có tiền: báo đúng ('{needle}…'), có cách thanh toán lại/đợi, URL không chứa dữ liệu cá nhân",
                 needle in t.lower() and not contains_pii(page.url), t[:250])
        # mã đơn của người khác, không có token → không hiện đơn, chỉ form tra cứu
        ctx2, page2, w2 = new(browser, width)
        goto(page2, f"/shop/orders/?code={code}&result=success", 900)
        page2.wait_for_selector("#lookup-code", timeout=15000)
        t2 = page2.inner_text("main")
        R.ok(f"{tag} mở link đơn từ phiên không có token → không lộ đơn, hiện form tra cứu (mã + SĐT)", "Tra cứu" in t2 and "647" not in t2 and "Cá thu" not in t2, t2[:250])
        ctx2.close()
        ctx.close()
    browser.close()
R.finish()
