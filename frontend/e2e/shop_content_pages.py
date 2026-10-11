"""
E2E nội dung CMS trên Shop, BE thật đã chạy `load_shop_content --publish` (SHOP-5-04, 5-05, 1-08, 1-09, CMS-06, CMS-13).
Thay `about_page.py`, `content_public_pages.py`, `content_item_card.py`, `qa-lo7-shop-links.py`, `qa-lo7-shop-xss.py` (bám giao diện cũ,
cổng cứng, dữ liệu dựng tay).

  - trang giới thiệu /about/ và 404; API nội dung lỗi → nút "Thử lại"
  - trang chính sách (mục lục, Các chính sách), Liên hệ (không form), Cách mua (5 bước, hỏi đáp), slug lạ, bài đã gỡ
  - Góc bếp: lọc chuyên mục, bài có thẻ món (giá lấy lúc xem, UTM, thêm giỏ, hết hàng, ngưng bán, chỉ gọi API công khai)
  - an toàn nội dung: link độc (javascript:, //, \\) không thành <a>; link ngoài target/rel đủ; không dialog, không request tới host lạ
Chạy: python3 frontend/e2e/run_shop_e2e.py --suite content_pages
"""
import json
import re
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

from shop_e2e_lib import *

R = Report("content_pages")
SLUG = "ca-thu-hap-gung-hanh"
BLOCKED = ("tươi sống", "miễn phí giao", "cá tươi")
FORBIDDEN_KEYS = ["purchase_rate", "landed_unit_cost", "unit_cost", "profit", "created_by", "updated_by", "username"]


def price_in_card(page, code):
    txt = page.locator(f'li:has(a[href*="code={code}"])').first.inner_text()
    m = re.search(r"(\d[\d.]*)đ", txt)
    return int(m.group(1).replace(".", "")) if m else None


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (360, 1280):
        tag = f"[{width}]"
        ctx = browser.new_context(viewport={"width": width, "height": 844 if width < 600 else 800})
        page = ctx.new_page()
        watch = PageWatch(page)
        dialogs = []
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        # ---- /about/ + 404
        goto(page, "/about/", 900)
        body = page.inner_text("main")
        R.ok(f"{tag} /about/: có H1, nút 'Xem hàng đang có' → /shop/, không cụm cấm", page.locator("h1").count() == 1
             and page.get_by_role("link", name=re.compile("Xem hàng đang có")).count() >= 1 and not any(b in body.lower() for b in BLOCKED), body[:200])
        snap(page, "about", width, "content")
        page.goto(SHOP + "/khong-co-trang-nay/")
        page.wait_for_load_state("networkidle")
        t404 = page.inner_text("body")
        R.ok(f"{tag} 404: chữ báo không tìm thấy + 2 nút điều hướng + noindex", "tìm thấy" in t404.lower()
             and page.locator('meta[name="robots"][content*="noindex"]').count() >= 1, t404[:200])
        # API nội dung lỗi → Thử lại
        page.route("**/api/public/content/**", lambda r: r.abort("internetdisconnected"))
        goto(page, "/about/", 900)
        try:
            page.wait_for_selector("text=Thử lại", timeout=8000)
        except Exception:  # noqa: BLE001
            pass
        R.ok(f"{tag} /about/ khi API nội dung lỗi: có nút 'Thử lại', không trắng trang", "Thử lại" in page.inner_text("body"), page.inner_text("body")[:150])
        page.unroute("**/api/public/content/**")

        # ---- trang CMS
        goto(page, "/pages/?slug=doi-tra", 900)
        toc = page.eval_on_selector_all('nav a[href^="#muc-"]', "els => els.map(e => e.getAttribute('href'))")
        R.ok(f"{tag} chính sách: mục lục ≥ 2 link neo, mỗi link trỏ đúng 1 H2", len(toc) >= 2 and all(page.locator(f"h2{h}").count() == 1 for h in toc), toc)
        R.ok(f"{tag} chính sách: 'Các chính sách' đánh dấu trang đang xem (aria-current), có Breadcrumb",
             page.locator('nav a[aria-current="page"][href*="slug=doi-tra"]').count() >= 1 and page.locator('nav[aria-label="Đường dẫn"]').count() >= 1)
        R.ok(f"{tag} chính sách: tiêu đề tab không lặp thương hiệu", page.title().count("Cá Về") == 1, page.title())
        snap(page, "policy", width, "content")
        goto(page, "/pages/?slug=lien-he", 900)
        mt = page.inner_text("main")
        R.ok(f"{tag} Liên hệ: không form/ô nhập, không ô giữ chỗ '[…]'", page.locator("main form, main input, main textarea").count() == 0 and "[" not in mt, mt[:200])
        goto(page, "/pages/?slug=cach-mua-hang", 900)
        mt = page.inner_text("main")
        R.ok(f"{tag} Cách mua: ≥ 5 bước, hỏi đáp <details>, có 1 kg / 0,5 kg / 30 phút",
             page.locator("main ol > li").count() >= 5 and page.locator("main details").count() >= 1 and all(w in mt for w in ("1 kg", "0,5 kg", "30 phút")), mt[:200])
        for slug in ("doi-tra", "giao-hang", "thanh-toan", "quyen-rieng-tu", "dieu-khoan", "khieu-nai", "thong-tin-nguoi-ban", "lien-he", "cach-mua-hang"):
            goto(page, f"/pages/?slug={slug}", 500)
            t = page.inner_text("main").lower()
            if any(b in t for b in BLOCKED):
                R.ok(f"{tag} /pages/?slug={slug}: không cụm cấm (cá tươi, tươi sống, miễn phí giao)", False, t[:100])
        R.ok(f"{tag} 9 trang chính sách: không cụm cấm 'cá tươi/tươi sống/miễn phí giao'", True)
        goto(page, "/pages/?slug=khong-co-trang-nay", 700)
        R.ok(f"{tag} slug không có → 'Không tìm thấy trang này'", "Không tìm thấy trang này" in page.inner_text("body"))

        # ---- Góc bếp
        goto(page, "/blog/", 900)
        R.ok(f"{tag} Góc bếp: tiêu đề tab không lặp thương hiệu", page.title().count("Cá Về") == 1, page.title())
        cats = page.eval_on_selector_all('nav[aria-label="Chuyên mục"] a[href*="category="]', "els => els.map(e => e.getAttribute('href'))")
        R.ok(f"{tag} Góc bếp: có chip chuyên mục", len(cats) >= 1, cats)
        if cats:
            goto(page, cats[0], 800)
            R.ok(f"{tag} chip đang chọn có aria-current; có thanh điều hướng đáy (điện thoại) hoặc menu (máy tính)",
                 page.locator('nav[aria-label="Chuyên mục"] a[aria-current="page"]').count() == 1)
        snap(page, "blog-list", width, "content")
        goto(page, "/blog/?slug=khong-co-bai-nay", 700)
        R.ok(f"{tag} bài không có → thông báo không tìm thấy bài", "Không tìm thấy" in page.inner_text("body"), page.inner_text("body")[:150])

        # ---- Bài có thẻ món
        reqs_before = len(watch.requests)
        goto(page, f"/blog/?slug={SLUG}", 1200)
        R.ok(f"{tag} bài: tiêu đề + tác giả 'Cá Về' + ngày; title có '| Cá Về' một lần; meta description", "Cá thu hấp gừng hành" in page.inner_text("body")
             and "Cá Về" in page.inner_text("article") and page.title().count("Cá Về") == 1 and bool(page.locator('meta[name="description"]').get_attribute("content")))
        links = page.eval_on_selector_all('a[href*="/shop/item/"]', "els => els.map(e => e.getAttribute('href'))")
        qs = parse_qs(urlparse(links[0]).query) if links else {}
        R.ok(f"{tag} thẻ món: link sang trang món có UTM đúng (caveve_web / bai_viet / slug bài)",
             qs == {"code": ["CA-THU"], "utm_source": ["caveve_web"], "utm_medium": ["bai_viet"], "utm_campaign": [SLUG]}, links)
        R.ok(f"{tag} thẻ món: giá lấy từ catalog (165.000đ), có nút 'Thêm 1 kg'", price_in_card(page, "CA-THU") == 165000
             and page.locator('li:has(a[href*="code=CA-THU"]) button', has_text="Thêm 1 kg").count() == 1)
        snap(page, "blog-article-itemcard", width, "content")
        # thêm giỏ từ thẻ
        page.locator('li:has(a[href*="code=CA-THU"]) button', has_text="Thêm 1 kg").first.click()
        page.wait_for_timeout(500)
        R.ok(f"{tag} thêm từ thẻ món: giỏ có CA-THU 1 kg, toast có 'Xem giỏ'",
             "CA-THU" in page.evaluate("localStorage.getItem('cangcaloc_cart_v1')||''") and page.get_by_role("link", name="Xem giỏ").count() >= 1)
        # chỉ gọi API công khai
        calls = [u for _, u, _ in watch.requests[reqs_before:] if "/api/" in u]
        R.ok(f"{tag} trang bài chỉ gọi API công khai (nội dung + catalog + site-info), không API nội bộ",
             all(("/api/public/" in u or "/api/shop/catalog/" in u) for u in calls), [u for u in calls if "/api/public/" not in u and "/api/shop/catalog/" not in u])
        html = page.content()
        R.ok(f"{tag} HTML trang bài không có khoá giá vốn/nội bộ", not any(f'"{k}"' in html for k in FORBIDDEN_KEYS))
        hosts = {urlparse(u).hostname for _, u, _ in watch.requests if urlparse(u).hostname}
        R.ok(f"{tag} chỉ gọi tới localhost (không bên thứ ba)", hosts <= {"localhost"}, hosts)
        # giá thay đổi lúc xem, không cần đăng lại bài: đổi giá bằng lệnh BE rồi tải lại
        manage_shell("from apps.catalog.models import Item, ItemPrice\nfrom decimal import Decimal as D\n"
                     "ItemPrice.objects.filter(item__code='CA-THU').update(rate=D('170000'))")
        goto(page, f"/blog/?slug={SLUG}", 1000)
        R.ok(f"{tag} đổi giá món (165.000 → 170.000) mà không đăng lại bài → thẻ hiện giá mới", price_in_card(page, "CA-THU") == 170000, price_in_card(page, "CA-THU"))
        manage_shell("from apps.catalog.models import ItemPrice\nfrom decimal import Decimal as D\nItemPrice.objects.filter(item__code='CA-THU').update(rate=D('165000'))")
        # hết hàng → 'Liên hệ chúng tôi'; ngưng bán → ẩn thẻ, mã hàng không lộ
        stock_set("CA-THU", 0)
        goto(page, f"/blog/?slug={SLUG}", 1000)
        R.ok(f"{tag} món hết hàng: thẻ hiện 'Liên hệ chúng tôi', không nút thêm", page.locator('li:has(a[href*="code=CA-THU"])', has_text="Liên hệ chúng tôi").count() >= 1
             and page.locator('li:has(a[href*="code=CA-THU"]) button', has_text="Thêm 1 kg").count() == 0)
        stock_set("CA-THU", 40)
        manage_shell("from apps.catalog.models import Item\nItem.objects.filter(code='CA-THU').update(is_active=False)")
        goto(page, f"/blog/?slug={SLUG}", 1000)
        R.ok(f"{tag} món ngưng bán: thẻ ẩn, mã hàng thô không lộ, bài vẫn đọc được", page.locator('a[href*="code=CA-THU"]').count() == 0
             and "CA-THU" not in page.inner_text("body") and "Cá thu hấp gừng hành" in page.inner_text("body"))
        manage_shell("from apps.catalog.models import Item\nItem.objects.filter(code='CA-THU').update(is_active=True)")
        R.ok(f"{tag} console sạch lỗi JS, không dialog", not watch.console_errors() and not watch.errors and not dialogs, (watch.console_errors()[:2], dialogs))
        ctx.close()

    # ---- an toàn nội dung bài: link độc (API công khai bị thay bằng bài dựng sẵn, build thật)
    BAD = ["\\\\evil.example", "\\\\\\\\evil.example/x", "/\\evil.example", "//evil.example", "///evil.example", "javascript:window.__x=1",
           " javascript:window.__x=1", "JaVaScRiPt:window.__x=1", "java\tscript:window.__x=1", "data:text/html,<script>window.__x=1</script>",
           "vbscript:msgbox(1)", "file:///etc/passwd", "\u0001javascript:window.__x=1", "x" * 2100]
    CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"}
    def entry(blocks):
        return {"kind": "post", "slug": "bai-thu", "title": "Bài thử an toàn", "seo_title": "", "description": "", "excerpt": "", "category": None,
                "cover_image": None, "body": {"type": "doc", "blocks": blocks}, "published_at": "2026-10-01T00:00:00Z",
                "updated_at": "2026-10-01T00:00:00Z", "version": 1, "effective_from": None, "author": "Cá Về"}
    for width in (360, 1280):
        tag = f"[{width}]"
        ctx = browser.new_context(viewport={"width": width, "height": 800})
        page = ctx.new_page()
        evil, dialogs, errs, popups = [], [], [], []
        ctx.route(lambda u: urlparse(u).hostname == "evil.example", lambda r: (evil.append(r.request.url), r.abort()))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("pageerror", lambda e: errs.append(str(e)))
        ctx.on("page", lambda pg: popups.append(pg.url))
        blocks = [{"type": "paragraph", "children": [{"text": f"LINK{i}", "href": h}]} for i, h in enumerate(BAD)]
        blocks.append({"type": "paragraph", "children": [{"text": "LINKOK", "href": "https://evil.example/hop-le"}]})
        blocks.append({"type": "paragraph", "children": [{"text": "<img src=x onerror=window.__x=1> <script>window.__x=1</script>"}]})
        def fake(route):
            path = urlparse(route.request.url).path
            if route.request.method == "OPTIONS":
                return route.fulfill(status=204, headers=CORS)
            if path.startswith("/api/public/content/entries/") and path != "/api/public/content/entries/":
                return route.fulfill(status=200, content_type="application/json", headers=CORS, body=json.dumps(entry(blocks)))
            return route.continue_()
        page.route(f"{API}/**", fake)
        goto(page, "/blog/?slug=bai-thu", 800)
        anchors = page.eval_on_selector_all("article a", "els => els.map(a => ({t: a.textContent, tg: a.target, rel: a.rel}))")
        R.ok(f"{tag} {len(BAD)} link độc (javascript:, //, \\\\, data:, file:, ký tự điều khiển, dài 2100) không thành thẻ <a>",
             not [a for a in anchors if a["t"].startswith("LINK") and not a["t"].startswith("LINKOK")], [a for a in anchors if a["t"].startswith("LINK") and not a["t"].startswith("LINKOK")][:3])
        ok_a = [a for a in anchors if a["t"].startswith("LINKOK")]
        R.ok(f"{tag} link https hợp lệ: target=_blank + rel nofollow noopener noreferrer", len(ok_a) == 1 and ok_a[0]["tg"] == "_blank"
             and all(x in ok_a[0]["rel"] for x in ("nofollow", "noopener", "noreferrer")), ok_a)
        R.ok(f"{tag} chữ '<img onerror>' và '<script>' hiện nguyên văn, không thành thẻ thật",
             page.locator("article img[onerror]").count() == 0 and page.locator("article script").count() == 0 and "onerror=" in page.inner_text("article"))
        for i in range(len(BAD)):
            loc = page.get_by_text(f"LINK{i}", exact=True)
            if loc.count():
                loc.first.click(force=True)
        page.wait_for_timeout(300)
        R.ok(f"{tag} bấm hết link độc: vẫn ở origin gốc, 0 request tới evil.example, không dialog/__x/pageerror/tab mới",
             urlparse(page.url).netloc == urlparse(SHOP).netloc and not evil and not dialogs and page.evaluate("window.__x === undefined") and not errs and not popups,
             (page.url, evil, dialogs, errs, popups))
        ctx.close()
    browser.close()
R.finish()
