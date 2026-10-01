"""
QA P8 Lô 6 — SR-21 (phần Shop): bằng chứng chạy thật BỔ SUNG cho `ra-soat-a2-golive.py`.

Phủ các khe A2 chưa phủ / phủ yếu (đối chiếu trong 04-qa-report.md, mục "Lô 6 — SR-21"):
  GL-01-AC2/AC5/AC6  footer trên 8 route (A2 chỉ 3), API 500/abort/seller null, không chữ cứng trong bundle footer
  GL-02-AC1..AC5     thứ tự/gỡ/đổi thứ tự/mảng rỗng/lỗi trên 8 route, 375 và 320 px, link dài, bàn phím, bấm link chạy thật
  GL-03-AC2/4/5/8    payload consent thật, cờ tắt, Enter khi chưa tick, bấm đúp, 409 rồi gửi lại, 503 khi POST, 400/429,
                     link chính sách mở tab mới giữ form, sweep PII (localStorage/sessionStorage/cookie/URL/console/request)
                     ở CẢ đường lỗi, form không nhớ sau F5, chỉ gọi origin + API (không bên thứ ba), form cổng thanh toán
  GL-04-AC1..AC5     quay về với cờ tắt / không storage / storage sai mã / cancel|error / storage bị sửa thành SĐT đầy đủ /
                     site-info lỗi / site-info chậm; quét outerHTML (không chỉ inner_text)
  M5-1 (phát hiện thêm) quét bản build thật xem còn mã mock/SĐT giả không.

Dữ liệu 100% giả. Chặn toàn bộ /api/** bằng page.route trên build THẬT (NEXT_PUBLIC_USE_MOCK=0).

Cách chạy (P8 Lô 6 — phục vụ bản `out/` tĩnh đã copy sang thư mục riêng):
    cd frontend && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8199 npm run build
    cp -R out/. <scratch>/qa-lo6-sr21/ ; (cd <scratch>/qa-lo6-sr21 && python3 -m http.server 3106 --bind 127.0.0.1 &)
    QA_BASE=http://127.0.0.1:3106 QA_OUT_DIR=<scratch>/qa-lo6-sr21 \
    QA_SHOT_DIR=doc/features/2026-09-30-sua-loi-review/qa-lo6 python3 e2e/qa-lo6-sr21-shop.py
"""
import glob
import json
import os
import re
import sys
import time
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright

BASE = os.environ.get("QA_BASE", "http://127.0.0.1:3106")
OUT_DIR = os.environ.get("QA_OUT_DIR", "")
SHOT_DIR = os.environ.get("QA_SHOT_DIR", "/tmp")
API = "http://localhost:8199"
PAY_HOST = "https://pay-sandbox.qa.example"
ALLOWED_HOSTS = {urlparse(BASE).netloc, "localhost:8199", "pay-sandbox.qa.example"}

PII_NAME = "Khách QA Ẩn Danh"
PII_PHONE = "0912345678"
PII_ADDR = "999 Đường Bí Mật QA"
PII_ALL = [PII_NAME, PII_PHONE, PII_ADDR, quote(PII_NAME), quote(PII_ADDR)]

SELLER = {
    "name": "Vựa Thử Nghiệm QA", "business_type": "Hộ kinh doanh", "registration_no": "0000000001",
    "tax_code": "0000000002", "address": "1 Đường Giả, Phường Giả, Tỉnh Giả", "phone": "0900000000",
    "email": "lienhe@example.com",
}
SITE_OK = {
    "seller": SELLER, "seller_complete": True, "privacy_consent_required": True,
    "confirm_call_notice": False, "confirm_call_hours": "7:00–20:00", "confirmation_policy": None, "cskh_notice": None,
}
LINKS_OK = [
    {"title": "Chính sách bảo mật", "slug": "chinh-sach-bao-mat"},
    {"title": "Chính sách đổi trả", "slug": "chinh-sach-doi-tra"},
    {"title": "Chính sách thanh toán", "slug": "chinh-sach-thanh-toan"},
]
CATALOG = [{
    "item_code": "CA-QA-01", "name": "Cá QA giả định", "group": "ca", "item_type": "SIMPLE", "unit": "Kg",
    "price": 100000, "sellable_qty": 50, "image": None,
}]
ITEM_DETAIL = dict(CATALOG[0], bundle_components=[])
POLICY_V1 = {"slug": "chinh-sach-bao-mat", "title": "Chính sách bảo mật thông tin", "version": 1,
             "version_id": 918, "effective_from": "2026-09-28T00:00:00Z"}
ENTRY = {
    "kind": "page", "slug": "chinh-sach-bao-mat", "title": "Chính sách bảo mật thông tin", "seo_title": "",
    "description": "", "excerpt": "", "category": None, "cover_image": None,
    "body": {"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Nội dung giả cho QA."}]}]},
    "published_at": "2026-09-28T00:00:00Z", "updated_at": "2026-09-28T00:00:00Z", "version": 1,
    "effective_from": "2026-09-28T00:00:00Z", "author": "Cá Về",
}
CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"}
ORDER_201 = {"order_code": "DH-QA-0001", "total_amount": "100000", "booked_expires_at": "2099-01-01T00:00:00Z"}

ROUTES = [
    ("Landing", "/"), ("Shop", "/shop/"), ("Sản phẩm", "/shop/item/?code=CA-QA-01"),
    ("Checkout", "/shop/checkout/"), ("Tra đơn", "/shop/orders/"),
    ("Trang", "/trang/?slug=chinh-sach-bao-mat"), ("Bài viết", "/bai-viet/"), ("Chi tiết bài", "/bai-viet/?slug=chinh-sach-bao-mat"),
]

LF = 'footer[aria-label^="Thông tin pháp lý"]'
failures = []
total = 0


def check(label, cond, detail=""):
    global total
    total += 1
    ok = bool(cond)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f"  <{detail}>" if (detail and not ok) else ""))
    if not ok:
        failures.append(label)


lows = []


def low(label, cond):
    """Ghi nhận lỗi mức Low: in [LOW], không làm exit code đỏ."""
    global total
    total += 1
    print(f"[{'PASS' if cond else 'LOW '}] {label}")
    if not cond:
        lows.append(label)


def info(label):
    print(f"[INFO] {label}")


class Rec:
    def __init__(self):
        self.api = []          # (method, url, post_data)
        self.all_urls = []     # mọi request của trang
        self.console = []      # (type, text)
        self.pageerrors = []
        self.pay_posts = []    # post_data gửi tới cổng thanh toán giả


def resp(route, body, status=200, extra=None):
    h = dict(CORS)
    if extra:
        h.update(extra)
    route.fulfill(status=status, content_type="application/json", headers=h, body=json.dumps(body))


def answer(route, spec):
    """spec: dict|list -> 200; ("s", status, body); "abort"; callable(route)."""
    if spec == "abort":
        return route.abort("failed")
    if isinstance(spec, tuple) and spec[0] == "s":
        return resp(route, spec[2], spec[1])
    if callable(spec):
        return spec(route)
    return resp(route, spec)


def setup(page, cfg=None):
    """Cài chặn API; trả về Rec. cfg ghi đè theo khoá: site, links, catalog, item, privacy, entry, entries, orders_post,
    order_get, checkout."""
    cfg = cfg or {}
    rec = Rec()
    page.on("console", lambda m: rec.console.append((m.type, m.text)))
    page.on("pageerror", lambda e: rec.pageerrors.append(str(e)))
    page.on("request", lambda r: rec.all_urls.append(r.url))

    def api(route):
        req = route.request
        path = urlparse(req.url).path
        m = req.method
        if m == "OPTIONS":
            return route.fulfill(status=204, headers=CORS)
        rec.api.append((m, req.url, req.post_data))
        if path == "/api/public/site-info/":
            return answer(route, cfg.get("site", SITE_OK))
        if path == "/api/public/content/footer-links/":
            return answer(route, cfg.get("links", LINKS_OK))
        if path == "/api/public/content/pages/by-role/privacy/":
            return answer(route, cfg.get("privacy", POLICY_V1))
        if path.startswith("/api/public/content/entries/") and path != "/api/public/content/entries/":
            return answer(route, cfg.get("entry", ENTRY))
        if path == "/api/public/content/entries/":
            return answer(route, cfg.get("entries", {"results": [], "count": 0}))
        if path == "/api/public/content/categories/":
            return resp(route, [])
        if path == "/api/shop/catalog/":
            return answer(route, cfg.get("catalog", CATALOG))
        if path.startswith("/api/shop/catalog/"):
            return answer(route, cfg.get("item", ITEM_DETAIL))
        if path == "/api/shop/orders/" and m == "POST":
            return answer(route, cfg.get("orders_post", ("s", 201, ORDER_201)))
        if re.match(r"^/api/shop/orders/[^/]+/checkout/$", path) and m == "POST":
            return answer(route, cfg.get("checkout", {
                "checkout_url": f"{PAY_HOST}/v1/checkout/init",
                "fields": [{"name": "merchant", "value": "MQA"}, {"name": "order_invoice_number", "value": "DH-QA-0001"},
                           {"name": "signature", "value": "abc"}],
            }))
        if re.match(r"^/api/shop/orders/[^/]+/$", path) and m == "GET":
            return answer(route, cfg.get("order_get", ("s", 404, {"detail": "Không tìm thấy"})))
        return resp(route, {"detail": "Không tìm thấy"}, 404)

    page.route(f"{API}/**", api)

    def pay(route):
        rec.pay_posts.append(route.request.post_data)
        route.fulfill(status=200, content_type="text/html", body="<html><body>cổng giả</body></html>")

    page.route(f"{PAY_HOST}/**", pay)
    return rec


def new_page(browser, cfg=None, viewport=None):
    ctx = browser.new_context(viewport=viewport or {"width": 1280, "height": 800})
    page = ctx.new_page()
    return ctx, page, setup(page, cfg)


def footer_text(page):
    loc = page.locator(LF)
    return loc.inner_text() if loc.count() else ""


def goto(page, path):
    page.goto(f"{BASE}{path}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(250)


def add_to_cart_and_open_checkout(page):
    goto(page, "/shop/")
    page.get_by_role("button", name="Thêm vào giỏ").first.click()
    goto(page, "/shop/checkout/")


def fill_form(page, tick=True):
    page.fill("#name", PII_NAME)
    page.fill("#phone", PII_PHONE)
    page.fill("#address", PII_ADDR)
    if tick and page.locator('input[type="checkbox"]').count():
        page.locator('input[type="checkbox"]').check()


def submit_btn(page):
    return page.get_by_role("button", name=re.compile("Đặt hàng"))


def storage_dump(page):
    return page.evaluate(
        "JSON.stringify({ls: Object.assign({}, window.localStorage), ss: Object.assign({}, window.sessionStorage),"
        " cookie: document.cookie, hist: JSON.stringify(window.history.state)})"
    )


def has_pii(text):
    return any(t in text for t in PII_ALL)


def post_bodies(rec, path_part):
    return [json.loads(b) for (m, u, b) in rec.api if m == "POST" and path_part in u and b]


def sweep_pii(page, rec, label):
    """Bất biến 9: storage, cookie, URL, history, console, pageerror, URL mọi request KHÔNG chứa PII."""
    dump = storage_dump(page)
    check(f"{label}: localStorage/sessionStorage/cookie/history không có tên-SĐT-địa chỉ", not has_pii(dump), dump[:200])
    check(f"{label}: URL trang không có PII", not has_pii(page.url), page.url)
    console_txt = " | ".join(t for _, t in rec.console) + " | ".join(rec.pageerrors)
    check(f"{label}: console (mọi mức) + pageerror không có PII", not has_pii(console_txt))
    check(f"{label}: URL của mọi request không có PII", not any(has_pii(u) for u in rec.all_urls))
    hosts = {urlparse(u).netloc for u in rec.all_urls if u.startswith("http")}
    check(f"{label}: chỉ gọi origin + API (+ cổng thanh toán), không bên thứ ba", hosts <= ALLOWED_HOSTS, str(hosts - ALLOWED_HOSTS))


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # =====================================================================
        # GL-01-AC2 / GL-02-AC1 trên 8 route (A2 chỉ 3 route)
        # =====================================================================
        for label, path in ROUTES:
            ctx, page, rec = new_page(browser)
            goto(page, path)
            ft = footer_text(page)
            check(f"GL-01-AC2 [{label}] footer đủ 7 thông tin người bán",
                  all(s in ft for s in ["Vựa Thử Nghiệm QA", "Hộ kinh doanh", "0000000001", "0000000002", "1 Đường Giả", "0900000000", "lienhe@example.com"]))
            check(f"GL-01-AC2 [{label}] có link tel: và mailto:", page.locator(LF + ' a[href="tel:0900000000"]').count() == 1 and page.locator(LF + ' a[href="mailto:lienhe@example.com"]').count() == 1)
            titles = [page.locator(LF + " a[href*='/trang/']").nth(i).inner_text() for i in range(page.locator(LF + " a[href*='/trang/']").count())]
            check(f"GL-02-AC1 [{label}] 3 link chính sách đúng thứ tự cấu hình", titles == [l["title"] for l in LINKS_OK], str(titles))
            check(f"GL-02-AC1 [{label}] chỉ có 1 footer pháp lý (không nhân đôi)", page.locator(LF).count() == 1)
            check(f"GL-01-AC2 [{label}] không pageerror", not rec.pageerrors, str(rec.pageerrors))
            if label == "Shop":
                page.screenshot(path=f"{SHOT_DIR}/sr21-gl01-footer-shop-1280.png", full_page=True)
            ctx.close()

        # Bấm link footer -> mở đúng trang chính sách (link chạy thật, không chỉ có href)
        ctx, page, rec = new_page(browser)
        goto(page, "/shop/")
        page.locator(LF + " a", has_text="Chính sách bảo mật").click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        check("GL-02-AC1 bấm link footer -> /trang/?slug=chinh-sach-bao-mat và hiện nội dung trang",
              "/trang/" in page.url and "slug=chinh-sach-bao-mat" in page.url and "Nội dung giả cho QA." in page.inner_text("body"), page.url)
        ctx.close()

        # =====================================================================
        # GL-01-AC5: API site-info lỗi (abort / 500 / thiếu seller) trên 8 route
        # =====================================================================
        for mode, site_spec in [("abort", "abort"), ("500", ("s", 500, {"detail": "Lỗi máy chủ"})), ("seller=null", {"privacy_consent_required": True, "seller": None})]:
            for label, path in ROUTES:
                ctx, page, rec = new_page(browser, {"site": site_spec})
                goto(page, path)
                body = page.inner_text("body")
                ft = footer_text(page)
                check(f"GL-01-AC5 [{mode}] [{label}] khối người bán ẩn, trang không trắng, không pageerror",
                      "Thông tin đơn vị bán hàng" not in body and len(body.strip()) > 80 and not rec.pageerrors, f"len={len(body.strip())} err={rec.pageerrors}")
                check(f"GL-01-AC6 [{mode}] [{label}] khi API chết không còn MST/SĐT chữ cứng nào trong DOM",
                      not re.search(r"\b\d{9,13}\b", ft), ft[:120])
                check(f"GL-02-AC4 [{mode}] [{label}] link chính sách KHÔNG bị ảnh hưởng khi site-info lỗi",
                      page.locator(LF + " a[href*='/trang/']").count() == 3)
                ctx.close()

        # seller có field null -> "Đang cập nhật", không vỡ
        ctx, page, rec = new_page(browser, {"site": dict(SITE_OK, seller=dict(SELLER, tax_code=None, registration_no=None, email=None, phone=None), seller_complete=False)})
        goto(page, "/shop/")
        ft = footer_text(page)
        check("GL-01-AC5 seller thiếu field (tax_code/ĐKKD/email/phone = null) -> 'Đang cập nhật', không a[href=tel:] rỗng",
              ft.count("Đang cập nhật") == 4 and page.locator(LF + ' a[href^="tel:"]').count() == 0 and page.locator(LF + ' a[href^="mailto:"]').count() == 0 and not rec.pageerrors, ft)
        ctx.close()

        # =====================================================================
        # GL-01-AC6: không chữ cứng dữ liệu người bán trong bundle footer (bản build thật)
        # =====================================================================
        if OUT_DIR:
            chunks = [f for f in glob.glob(f"{OUT_DIR}/_next/static/chunks/**/*.js", recursive=True) if "Thông tin đơn vị bán hàng" in open(f, encoding="utf-8", errors="ignore").read()
                      or "Th\\xf4ng tin đơn vị b\\xe1n h\\xe0ng" in open(f, encoding="utf-8", errors="ignore").read()]
            check("GL-01-AC6 tìm thấy chunk footer trong bản build thật", len(chunks) >= 1, str(chunks))
            for f in chunks:
                s = open(f, encoding="utf-8", errors="ignore").read()
                check(f"GL-01-AC6 chunk {os.path.basename(f)} không có dãy số >= 9 chữ số (MST/SĐT) và không có '@' email chữ cứng",
                      not re.search(r"\d{9,}", s) and not re.search(r"[\w.]+@[\w.]+\.\w+", s))

        # =====================================================================
        # GL-02-AC2/AC3: gỡ trang, đổi thứ tự, mảng rỗng, không cần build lại
        # =====================================================================
        state = {"links": LINKS_OK}
        ctx, page, rec = new_page(browser, {"links": lambda r: resp(r, state["links"])})
        goto(page, "/shop/")
        t = lambda: [page.locator(LF + " a[href*='/trang/']").nth(i).inner_text() for i in range(page.locator(LF + " a[href*='/trang/']").count())]
        check("GL-02-AC2 trước: 3 link", len(t()) == 3)
        state["links"] = list(reversed(LINKS_OK))
        page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(250)
        check("GL-02-AC1/AC3 đổi footer_order ở server -> tải lại thấy thứ tự mới (không build lại FE)", t() == [l["title"] for l in reversed(LINKS_OK)], str(t()))
        state["links"] = [LINKS_OK[1]]
        page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(250)
        check("GL-02-AC2 gỡ 2 trang -> còn đúng 1 link", t() == [LINKS_OK[1]["title"]], str(t()))
        state["links"] = []
        page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(250)
        check("GL-02-AC3 gỡ hết -> khối link ẩn, khối người bán còn, không nút/ul rỗng",
              page.locator(LF + " ul").count() == 0 and "Thông tin đơn vị bán hàng" in footer_text(page))
        state["links"] = {"detail": "sai định dạng"}
        page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(250)
        check("GL-02-AC4 footer-links trả không phải mảng -> ẩn khối link, không pageerror", page.locator(LF + " ul").count() == 0 and not rec.pageerrors, str(rec.pageerrors))
        ctx.close()

        for mode, spec in [("abort", "abort"), ("500", ("s", 500, {"detail": "x"}))]:
            ctx, page, rec = new_page(browser, {"links": spec})
            goto(page, "/shop/checkout/")
            check(f"GL-02-AC4 [{mode}] footer-links lỗi -> ẩn khối link, khối người bán còn", page.locator(LF + " ul").count() == 0 and "Vựa Thử Nghiệm QA" in footer_text(page))
            ctx.close()
        # cả hai API lỗi -> không có footer nào, không chiếm chỗ
        ctx, page, rec = new_page(browser, {"site": "abort", "links": "abort"})
        goto(page, "/shop/")
        check("GL-01-AC5/GL-02-AC4 cả site-info và footer-links lỗi -> không render <footer> rỗng", page.locator(LF).count() == 0 and "Cá QA giả định" in page.inner_text("body"))
        ctx.close()

        # =====================================================================
        # GL-02-AC5: 375x667 và 320x568, chữ dài, mọi route
        # =====================================================================
        long_seller = dict(SELLER, name="Công ty TNHH Một Thành Viên Vựa Hải Sản Thử Nghiệm Rất Dài QA", address="Số 1234/56/78 Đường Giả Rất Dài, Khu phố Giả Mạo, Phường Không Có Thật, Quận Giả, Thành phố Không Tồn Tại, Tỉnh Giả Định",
                           email="lien.he.rat.dai.de.thu.tran.ngang@ten-mien-gia-rat-dai-example.com")
        long_links = [{"title": "Chính sách bảo mật thông tin cá nhân và quyền của chủ thể dữ liệu rất dài " + str(i), "slug": f"cs-{i}"} for i in range(3)]
        for vw, vh in [(375, 667), (320, 568)]:
            for label, path in ROUTES:
                ctx, page, rec = new_page(browser, {"site": dict(SITE_OK, seller=long_seller), "links": long_links}, viewport={"width": vw, "height": vh})
                goto(page, path)
                sw = page.evaluate("document.documentElement.scrollWidth")
                cw = page.evaluate("document.documentElement.clientWidth")
                check(f"GL-02-AC5 [{vw}x{vh}] [{label}] không cuộn ngang với chữ dài (sw={sw}, cw={cw})", sw <= cw + 1)
                if page.locator(LF + " a[href*='/trang/']").count():
                    hs = [page.locator(LF + " a[href*='/trang/']").nth(i).bounding_box()["height"] for i in range(3)]
                    check(f"GL-02-AC5 [{vw}x{vh}] [{label}] mọi link chính sách cao >= 44px ({min(hs):.0f})", min(hs) >= 44)
                    tel = page.locator(LF + ' a[href^="tel:"]').bounding_box()
                    check(f"GL-02-AC5 [{vw}x{vh}] [{label}] link tel: nằm trong khung nhìn ngang (x+w<={cw})", tel["x"] >= 0 and tel["x"] + tel["width"] <= cw + 1)
                if label == "Shop" and vw == 375:
                    page.locator(LF).scroll_into_view_if_needed()
                    page.screenshot(path=f"{SHOT_DIR}/sr21-gl02-footer-375-chu-dai.png", full_page=False)
                ctx.close()

        # bàn phím: Tab tới được link footer, có focus nhìn thấy
        ctx, page, rec = new_page(browser)
        goto(page, "/shop/checkout/")
        reached = False
        for _ in range(80):
            page.keyboard.press("Tab")
            if page.evaluate("document.activeElement && document.activeElement.closest('footer[aria-label^=\"Thông tin pháp lý\"]') && document.activeElement.tagName") == "A":
                reached = True
                break
        check("GL-02-AC5 (bổ sung) Tab bàn phím tới được link trong footer", reached)
        ctx.close()

        # =====================================================================
        # GL-03-AC2: form + payload thật + cờ tắt + Enter + bấm đúp + link tab mới giữ form
        # =====================================================================
        ctx, page, rec = new_page(browser, viewport={"width": 375, "height": 667})
        add_to_cart_and_open_checkout(page)
        cb = page.locator('input[type="checkbox"]')
        form_txt = page.inner_text("form")
        check("GL-03-AC2 [375px] checkbox chưa tick, nút khoá, nhãn nêu họ tên/SĐT/địa chỉ/giao hàng/xác nhận đơn",
              cb.is_checked() is False and submit_btn(page).is_disabled() and all(s in form_txt for s in ["họ tên", "số điện thoại", "địa chỉ", "giao hàng", "xác nhận đơn"]))
        check("GL-03-AC2 [375px] không cuộn ngang ở checkout", page.evaluate("document.documentElement.scrollWidth") <= page.evaluate("document.documentElement.clientWidth") + 1)
        pl = page.locator('form a[href*="/trang/"]', has_text="Chính sách bảo mật")
        check("GL-03-AC2 link chính sách target=_blank + rel noopener", pl.get_attribute("target") == "_blank" and "noopener" in (pl.get_attribute("rel") or ""))
        page.screenshot(path=f"{SHOT_DIR}/sr21-gl03-ac2-checkout-375.png", full_page=True)
        # bấm link -> tab mới, form ở tab cũ còn nguyên
        page.fill("#name", PII_NAME)
        with ctx.expect_page() as popup_info:
            pl.click()
        popup = popup_info.value
        popup.wait_for_load_state("networkidle")
        check("GL-03-AC2 bấm link mở TAB MỚI tới /trang/?slug=chinh-sach-bao-mat, tab đặt hàng giữ nguyên tên đã nhập",
              "/trang/" in popup.url and "slug=chinh-sach-bao-mat" in popup.url and page.input_value("#name") == PII_NAME, popup.url)
        popup.close()
        # Enter khi chưa tick -> không gửi
        page.fill("#phone", PII_PHONE); page.fill("#address", PII_ADDR)
        page.press("#name", "Enter")
        page.wait_for_timeout(400)
        check("GL-03-AC2 (biên) nhấn Enter trong ô tên khi CHƯA tick -> không có POST /api/shop/orders/", len(post_bodies(rec, "/api/shop/orders/")) == 0)
        ctx.close()

        # payload thật khi cờ bật + bấm đúp chỉ 1 POST
        def slow_201(route):
            time.sleep(0.3)
            resp(route, ORDER_201, 201)
        ctx, page, rec = new_page(browser, {"orders_post": slow_201})
        add_to_cart_and_open_checkout(page)
        fill_form(page)
        submit_btn(page).dblclick()
        page.wait_for_timeout(900)
        posts = post_bodies(rec, "/api/shop/orders/")
        check("GL-03-AC2 (bấm đúp) chỉ 1 POST /api/shop/orders/", len(posts) == 1, str(len(posts)))
        if posts:
            b = posts[0]
            check("GL-03-AC3/AC2 payload có privacy_consent {accepted:true, policy_version_id:918} đúng kiểu số", b.get("privacy_consent") == {"accepted": True, "policy_version_id": 918}, str(b.get("privacy_consent")))
            check("GL-03-AC7 payload chỉ gồm khoá tối thiểu (customer, delivery_address, phone, items, privacy_consent)", set(b) == {"customer", "delivery_address", "phone", "items", "privacy_consent"}, str(set(b)))
        page.screenshot(path=f"{SHOT_DIR}/sr21-gl03-ac8-sau-dat-don-1280.png", full_page=True)
        html = page.content()
        check("GL-03-AC8/GL-04-AC3 màn 'Đặt hàng thành công': outerHTML không có tên/SĐT/địa chỉ đầy đủ", not has_pii(html))
        sweep_pii(page, rec, "GL-03-AC8 [đặt đơn thành công]")
        # cổng thanh toán: FE chỉ chuyển tiếp field do máy chủ lập, không chèn PII
        page.get_by_role("button", name=re.compile("Thanh toán bằng VietQR")).click()
        page.wait_for_timeout(700)
        check("GL-03-AC8 form gửi cổng thanh toán (bên thứ ba đã duyệt) chỉ có field do máy chủ lập, đúng thứ tự, không PII",
              len(rec.pay_posts) == 1 and rec.pay_posts[0] == "merchant=MQA&order_invoice_number=DH-QA-0001&signature=abc" and not has_pii(rec.pay_posts[0] or ""), str(rec.pay_posts))
        ctx.close()

        # cờ tắt -> không checkbox, POST không có privacy_consent
        ctx, page, rec = new_page(browser, {"site": dict(SITE_OK, privacy_consent_required=False)})
        add_to_cart_and_open_checkout(page)
        check("GL-03-AC6/AC2 [cờ tắt] không có checkbox, nút không bị khoá", page.locator('input[type="checkbox"]').count() == 0 and not submit_btn(page).is_disabled())
        fill_form(page)
        submit_btn(page).click(); page.wait_for_timeout(500)
        posts = post_bodies(rec, "/api/shop/orders/")
        check("GL-03-AC6 [cờ tắt] POST không có khoá privacy_consent, đơn tạo được", len(posts) == 1 and "privacy_consent" not in posts[0] and "Đặt hàng thành công" in page.inner_text("body"))
        ctx.close()

        # cờ tắt + không có chính sách -> vẫn bán (không đóng shop)
        ctx, page, rec = new_page(browser, {"site": dict(SITE_OK, privacy_consent_required=False), "privacy": ("s", 404, {"detail": "Không tìm thấy"})})
        add_to_cart_and_open_checkout(page)
        check("GL-03-AC5/AC6 (cờ tắt + chưa có chính sách) KHÔNG đóng shop, form còn", "Shop tạm chưa nhận đơn" not in page.inner_text("body") and page.locator("#name").count() == 1)
        ctx.close()

        # =====================================================================
        # GL-03-AC4: 409 rồi gửi lại với phiên bản mới; giỏ giữ nguyên; màn cũ
        # =====================================================================
        seq = {"n": 0}
        def orders_409_then_201(route):
            seq["n"] += 1
            if seq["n"] == 1:
                return resp(route, {"detail": "Chính sách vừa cập nhật.", "code": "POLICY_CHANGED",
                                    "current": {"version": 2, "version_id": 930, "slug": "chinh-sach-bao-mat-moi"}}, 409)
            return resp(route, ORDER_201, 201)
        ctx, page, rec = new_page(browser, {"orders_post": orders_409_then_201}, viewport={"width": 375, "height": 667})
        add_to_cart_and_open_checkout(page)
        fill_form(page)
        submit_btn(page).click(); page.wait_for_timeout(600)
        page.screenshot(path=f"{SHOT_DIR}/sr21-gl03-ac4-409-375.png", full_page=True)
        cb = page.locator('input[type="checkbox"]')
        check("GL-03-AC4 sau 409: báo lỗi, bỏ tick, nút khoá lại, giữ nguyên 3 field",
              "Chính sách vừa cập nhật" in page.inner_text("body") and cb.is_checked() is False and submit_btn(page).is_disabled()
              and page.input_value("#name") == PII_NAME and page.input_value("#phone") == PII_PHONE and page.input_value("#address") == PII_ADDR)
        check("GL-03-AC4 link chính sách được cập nhật sang slug mới trong `current`", "slug=chinh-sach-bao-mat-moi" in (page.locator('form a[href*="/trang/"]').get_attribute("href") or ""))
        check("GL-03-AC4 giỏ hàng KHÔNG bị xoá sau 409 (localStorage giỏ còn 1 dòng, bảng giỏ còn hiện)",
              len(json.loads(page.evaluate("window.localStorage.getItem('cangcaloc_cart_v1')"))) == 1 and page.locator("table.cart-table tbody tr").count() == 1)
        sweep_pii(page, rec, "GL-03-AC8 [sau 409]")
        cb.check(); submit_btn(page).click(); page.wait_for_timeout(600)
        posts = post_bodies(rec, "/api/shop/orders/")
        check("GL-03-AC4 (màn cũ) gửi lại sau 409 dùng policy_version_id MỚI 930 và đơn tạo được",
              len(posts) == 2 and posts[1].get("privacy_consent") == {"accepted": True, "policy_version_id": 930} and "Đặt hàng thành công" in page.inner_text("body"), str(posts[-1].get("privacy_consent")) if posts else "")
        ctx.close()

        # 409 thiếu `current` -> không vỡ
        ctx, page, rec = new_page(browser, {"orders_post": ("s", 409, {"detail": "x", "code": "POLICY_CHANGED"})})
        add_to_cart_and_open_checkout(page)
        fill_form(page); submit_btn(page).click(); page.wait_for_timeout(500)
        check("GL-03-AC4 (biên) 409 không kèm `current` -> báo lỗi, bỏ tick, không pageerror", "Chính sách vừa cập nhật" in page.inner_text("body") and page.locator('input[type="checkbox"]').is_checked() is False and not rec.pageerrors)
        ctx.close()

        # =====================================================================
        # GL-03-AC5: 503 khi POST, chính sách 404/500 khi tải, site-info lỗi
        # =====================================================================
        ctx, page, rec = new_page(browser, {"orders_post": ("s", 503, {"detail": "Shop tạm chưa nhận đơn", "code": "PRIVACY_POLICY_MISSING"})}, viewport={"width": 375, "height": 667})
        add_to_cart_and_open_checkout(page)
        fill_form(page); submit_btn(page).click(); page.wait_for_timeout(600)
        body = page.inner_text("body")
        check("GL-03-AC5 POST trả 503 -> màn 'Shop tạm chưa nhận đơn' thay form, có nút quay lại cửa hàng", "Shop tạm chưa nhận đơn" in body and page.locator("#name").count() == 0 and page.get_by_role("link", name="Quay lại cửa hàng").count() == 1)
        check("GL-03-AC5 giỏ hàng vẫn còn trong localStorage sau 503", len(json.loads(page.evaluate("window.localStorage.getItem('cangcaloc_cart_v1')"))) == 1)
        page.screenshot(path=f"{SHOT_DIR}/sr21-gl03-ac5-503-375.png", full_page=True)
        sweep_pii(page, rec, "GL-03-AC8 [sau 503]")
        page.get_by_role("link", name="Quay lại cửa hàng").click(); page.wait_for_url("**/shop/", timeout=5000)
        check("GL-03-AC5 bấm 'Quay lại cửa hàng' về /shop/", page.url.rstrip("/").endswith("/shop"), page.url)
        ctx.close()

        for mode, spec in [("404", ("s", 404, {"detail": "Không tìm thấy"})), ("500", ("s", 500, {"detail": "lỗi"})), ("abort", "abort")]:
            ctx, page, rec = new_page(browser, {"privacy": spec})
            add_to_cart_and_open_checkout(page)
            check(f"GL-03-AC5 [chính sách {mode}, cờ bật] fail-safe: đóng shop, không hiện form thu PII", "Shop tạm chưa nhận đơn" in page.inner_text("body") and page.locator("#phone").count() == 0)
            ctx.close()
        ctx, page, rec = new_page(browser, {"site": "abort", "privacy": ("s", 404, {"detail": "x"})})
        add_to_cart_and_open_checkout(page)
        check("GL-03-AC5 [site-info lỗi + chưa có chính sách] mặc định coi là BẮT BUỘC đồng ý -> đóng shop (không thu PII khi không chắc)", "Shop tạm chưa nhận đơn" in page.inner_text("body"))
        ctx.close()
        ctx, page, rec = new_page(browser, {"site": "abort"})
        add_to_cart_and_open_checkout(page)
        check("GL-03-AC2/AC5 [site-info lỗi + có chính sách] mặc định bắt buộc: checkbox hiện, chưa tick, nút khoá", page.locator('input[type="checkbox"]').count() == 1 and page.locator('input[type="checkbox"]').is_checked() is False and submit_btn(page).is_disabled())
        ctx.close()

        # =====================================================================
        # GL-03-AC8: các đường lỗi khác (400, 429) + form không nhớ sau F5 + giỏ chỉ giữ mã/số lượng
        # =====================================================================
        for code, body_json, expect in [(400, {"detail": "Mặt hàng CA-QA-01 không đủ tồn.", "code": "BR-BH-03"}, "không đủ tồn"),
                                        (429, {"detail": "Bạn thao tác quá nhanh, thử lại sau."}, "quá nhanh")]:
            ctx, page, rec = new_page(browser, {"orders_post": ("s", code, body_json)})
            add_to_cart_and_open_checkout(page)
            fill_form(page); submit_btn(page).click(); page.wait_for_timeout(500)
            check(f"GL-03-AC8 [{code}] hiện thông điệp máy chủ, giữ form + đã tick, không pageerror",
                  expect in page.inner_text("body") and page.input_value("#phone") == PII_PHONE and page.locator('input[type="checkbox"]').is_checked() and not rec.pageerrors)
            sweep_pii(page, rec, f"GL-03-AC8 [{code}]")
            if code == 400:
                page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(300)
                check("GL-03-AC8 F5 sau lỗi: form KHÔNG nhớ tên/SĐT/địa chỉ (không lưu ở đâu)", page.input_value("#name") == "" and page.input_value("#phone") == "" and page.input_value("#address") == "")
                cart = json.loads(page.evaluate("window.localStorage.getItem('cangcaloc_cart_v1')"))
                check("GL-03-AC8 giỏ hàng trong localStorage chỉ gồm item_code/name/price/unit/qty", all(set(l) <= {"item_code", "name", "price", "unit", "qty"} for l in cart), str(cart))
            ctx.close()

        # Sau đặt đơn thành công + reload: sessionStorage chỉ có mã đơn + 4 số cuối, giỏ đã xoá
        ctx, page, rec = new_page(browser)
        add_to_cart_and_open_checkout(page)
        fill_form(page); submit_btn(page).click(); page.wait_for_timeout(600)
        page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(300)
        ss = json.loads(page.evaluate("JSON.stringify(window.sessionStorage)"))
        # đường thanh toán chưa bấm -> sessionStorage có thể rỗng; nếu có thì chỉ order_code + 4 số cuối
        stored = json.dumps(ss)
        check("GL-03-AC8 sau đặt + F5: sessionStorage rỗng hoặc chỉ {order_code, phone_last4}", not has_pii(stored) and (not ss or all(set(json.loads(v)) == {"order_code", "phone_last4"} for v in ss.values())), stored)
        check("GL-03-AC8 sau đặt thành công giỏ hàng đã xoá", json.loads(page.evaluate("window.localStorage.getItem('cangcaloc_cart_v1') || '[]'")) == [])
        ctx.close()

        # Tra đơn (form): URL không chứa 4 số cuối/PII, request có 4 số cuối, console sạch, 429 hiển thị
        for label, spec, expect in [("200", {"order_code": "DH-QA-0001", "status": "BOOKED", "status_label": "Chờ thanh toán", "total_amount": "100000", "lines": [], "delivery": None, "booked_expires_at": "2099-01-01T00:00:00Z", "cancel_notice": None}, "DH-QA-0001"),
                                    ("404", ("s", 404, {"detail": "Không tìm thấy"}), "Không tìm thấy đơn hàng phù hợp"),
                                    ("429", ("s", 429, {"detail": "Tra cứu quá nhiều lần, thử lại sau."}), "quá nhiều lần")]:
            ctx, page, rec = new_page(browser, {"order_get": spec})
            goto(page, "/shop/orders/")
            page.fill("#orderCode", "DH-QA-0001"); page.fill("#phoneLast4", "5678")
            page.get_by_role("button", name="Tra cứu").click(); page.wait_for_timeout(500)
            reqs = [u for (m, u, b) in rec.api if m == "GET" and "/api/shop/orders/DH-QA-0001/" in u]
            check(f"GL-03-AC8 [tra đơn {label}] hiện đúng kết quả/thông điệp, URL trang không đổi (không lộ 4 số cuối/PII), request chỉ có 4 số cuối",
                  expect in page.inner_text("body") and "5678" not in page.url and (len(reqs) >= 1 and all("phone_last4=5678" in u for u in reqs)), page.url)
            sweep_pii(page, rec, f"GL-03-AC8 [tra đơn {label}]")
            check(f"GL-03-AC8 [tra đơn {label}] không lưu 4 số cuối vào localStorage", "5678" not in page.evaluate("JSON.stringify(window.localStorage)"))
            ctx.close()

        # =====================================================================
        # GL-04-AC1..AC5
        # =====================================================================
        def order_get_paid(code="DH-QA-0003"):
            return {"order_code": code, "status": "PAID", "status_label": "Đã thanh toán", "total_amount": "100000", "lines": [], "delivery": None, "booked_expires_at": None, "cancel_notice": None}

        site_on = dict(SITE_OK, confirm_call_notice=True)
        notice = lambda pg: pg.locator('[data-testid="confirm-call-notice"]')

        # AC1: đúng câu, đúng giờ theo API (đổi giờ không build lại), SĐT dạng +84 / 11 số, nút thanh toán vẫn dùng được, 375px
        for ph, expect_last4 in [(PII_PHONE, "5678"), ("+84912345678", "5678"), ("09123456789", "6789")]:
            ctx, page, rec = new_page(browser, {"site": dict(site_on, confirm_call_hours="8:00–18:30")}, viewport={"width": 375, "height": 667})
            add_to_cart_and_open_checkout(page)
            page.fill("#name", PII_NAME); page.fill("#phone", ph); page.fill("#address", PII_ADDR)
            page.locator('input[type="checkbox"]').check(); submit_btn(page).click(); page.wait_for_timeout(600)
            nt = notice(page).inner_text() if notice(page).count() == 1 else ""
            check(f"GL-04-AC1 [SĐT {ph[:3]}…{ph[-4:]}] câu đúng: 'gọi số đuôi {expect_last4} trong khung 8:00–18:30' (giờ lấy từ API)",
                  f"đuôi {expect_last4}" in nt and "8:00–18:30" in nt, nt)
            check(f"GL-04-AC1/AC3 [SĐT {ph[:3]}…{ph[-4:]}] outerHTML không có SĐT đầy đủ, URL sạch", ph not in page.content() and ph not in page.url and PII_NAME not in page.content())
            check(f"GL-04-AC1 [SĐT {ph[:3]}…{ph[-4:]}] nút 'Thanh toán bằng VietQR' vẫn bấm được, không cuộn ngang 375px",
                  page.get_by_role("button", name=re.compile("Thanh toán bằng VietQR")).is_enabled() and page.evaluate("document.documentElement.scrollWidth") <= page.evaluate("document.documentElement.clientWidth") + 1)
            if ph == PII_PHONE:
                page.screenshot(path=f"{SHOT_DIR}/sr21-gl04-ac1-notice-375.png", full_page=True)
            ctx.close()

        # AC2: quay về từ cổng — các đường ngoài thuận
        def ret(cfg, storage=None, query="?code=DH-QA-0003&result=success", viewport=None):
            ctx, page, rec = new_page(browser, cfg, viewport=viewport)
            goto(page, "/shop/")
            if storage is not None:
                page.evaluate("v => window.sessionStorage.setItem('cangcaloc_last_order_contact_v1', v)", storage)
            goto(page, f"/shop/orders/{query}")
            return ctx, page, rec

        cfg_ret = {"site": site_on, "order_get": order_get_paid()}
        ctx, page, rec = ret(cfg_ret, json.dumps({"order_code": "DH-QA-0003", "phone_last4": "5678"}), viewport={"width": 375, "height": 667})
        check("GL-04-AC2 quay về success + có storage -> đúng 1 thông báo, đuôi 5678, 7:00–20:00", notice(page).count() == 1 and "5678" in notice(page).inner_text() and "7:00–20:00" in notice(page).inner_text())
        check("GL-04-AC2 tự tra đơn bằng 4 số cuối đã nhớ (hiện 'Đã thanh toán') và khách không phải gõ lại", "Đã thanh toán" in page.inner_text("body") and page.input_value("#phoneLast4") == "5678")
        page.screenshot(path=f"{SHOT_DIR}/sr21-gl04-ac2-return-375.png", full_page=True)
        ctx.close()

        ctx, page, rec = ret(cfg_ret, None)
        check("GL-04-AC2 (biên) quay về success KHÔNG có storage (mở tab mới) -> không thông báo, không pageerror, ô nhập 4 số cuối còn", notice(page).count() == 0 and page.locator("#phoneLast4").count() == 1 and not rec.pageerrors)
        ctx.close()
        ctx, page, rec = ret(cfg_ret, json.dumps({"order_code": "DH-KHAC-9999", "phone_last4": "1111"}))
        check("GL-04-AC2 (biên) storage của ĐƠN KHÁC -> không dùng 4 số cuối của đơn khác", notice(page).count() == 0 and "1111" not in page.content())
        ctx.close()
        for res in ["cancel", "error"]:
            ctx, page, rec = ret(cfg_ret, json.dumps({"order_code": "DH-QA-0003", "phone_last4": "5678"}), query=f"?code=DH-QA-0003&result={res}")
            check(f"GL-04-AC2 (biên) result={res} -> KHÔNG hiện 'sẽ gọi xác nhận' (chưa thanh toán xong)", notice(page).count() == 0)
            ctx.close()
        ctx, page, rec = ret(cfg_ret, json.dumps({"order_code": "DH-QA-0003", "phone_last4": PII_PHONE}))
        html = page.content()
        check("GL-04-AC3 (đối kháng) storage bị sửa thành SĐT ĐẦY ĐỦ -> khối thông báo vẫn chỉ hiện 4 số cuối, URL sạch",
              PII_PHONE not in page.url and (notice(page).count() == 0 or (PII_PHONE not in notice(page).inner_text() and "5678" in notice(page).inner_text())))
        low("GL-04-AC3 (Low, hardening) storage bị sửa tay thành SĐT đầy đủ thì `recallOrderContact` không kiểm /^\\d{4}$/ -> SĐT đầy đủ vào ô `#phoneLast4` và query `?phone_last4=` của GET tra đơn (chỉ xảy ra khi tự sửa storage, luồng thường luôn ghi 4 số)",
            PII_PHONE not in html and not any(PII_PHONE in u for (_, u, _) in rec.api))
        ctx.close()
        ctx, page, rec = ret(cfg_ret, json.dumps({"order_code": "DH-QA-0003", "phone_last4": "12"}))
        check("GL-04-AC3 (đối kháng) storage 'phone_last4' không đủ 4 số -> không thông báo, không vỡ", notice(page).count() == 0 and not rec.pageerrors)
        ctx.close()
        ctx, page, rec = ret(cfg_ret, "{không phải json")
        check("GL-04-AC2 (đối kháng) storage hỏng (không phải JSON) -> không vỡ trang", notice(page).count() == 0 and not rec.pageerrors and page.locator("#orderCode").count() == 1)
        ctx.close()
        # AC4 trên màn quay về: cờ tắt
        ctx, page, rec = ret({"site": SITE_OK, "order_get": order_get_paid()}, json.dumps({"order_code": "DH-QA-0003", "phone_last4": "5678"}))
        check("GL-04-AC4 cờ tắt: màn quay về KHÔNG có thông báo, đơn vẫn hiện", notice(page).count() == 0 and "Đã thanh toán" in page.inner_text("body"))
        ctx.close()
        # AC5 trên màn quay về: site-info lỗi
        ctx, page, rec = ret({"site": "abort", "order_get": order_get_paid()}, json.dumps({"order_code": "DH-QA-0003", "phone_last4": "5678"}))
        check("GL-04-AC5 site-info lỗi ở màn quay về -> ẩn thông báo, vẫn tra được đơn, không pageerror", notice(page).count() == 0 and "Đã thanh toán" in page.inner_text("body") and not rec.pageerrors)
        ctx.close()
        # AC5 site-info chậm 3s: nút thanh toán dùng được ngay, không chờ site-info
        def slow_site(route):
            time.sleep(1.5)
            resp(route, site_on)
        ctx, page, rec = new_page(browser, {"site": slow_site})
        add_to_cart_and_open_checkout(page)
        page.wait_for_timeout(1800)
        fill_form(page); submit_btn(page).click(); page.wait_for_timeout(500)
        check("GL-04-AC5 site-info chậm 1,5s: đặt hàng vẫn thành công, nút thanh toán bấm được", "Đặt hàng thành công" in page.inner_text("body") and page.get_by_role("button", name=re.compile("Thanh toán bằng VietQR")).is_enabled())
        sweep_pii(page, rec, "GL-04-AC3 [màn thanh toán, cờ bật]")
        ctx.close()

        # Ghi nhận (không chấm lỗi): cả confirm_call_notice và cskh_notice bật -> hai câu, hai khung giờ (review F10, Lô 7)
        ctx, page, rec = new_page(browser, {"site": dict(site_on, confirmation_policy={"enabled": True, "working_hours": "07:00-21:00", "max_attempts": 3, "window_minutes": 180, "decision_minutes": 30, "auto_cancel_enabled": False, "refund_deadline_days": 3, "hotline": "0900000000"})})
        add_to_cart_and_open_checkout(page); fill_form(page); submit_btn(page).click(); page.wait_for_timeout(600)
        body = page.inner_text("body")
        info(f"F10 (Lô 7, SR-23) khi bật cả hai cờ: thông báo GL-04 = {notice(page).count()}, khối CSKH = {page.locator('[data-testid=confirmation-policy-notice]').count()}; khung giờ '7:00–20:00' {('7:00–20:00' in body)} và '07:00-21:00' {('07:00-21:00' in body)} cùng hiện")
        ctx.close()

        # =====================================================================
        # M5-1 (phát hiện thêm): bản build thật còn mã mock / SĐT giả?
        # =====================================================================
        if OUT_DIR:
            hits = {}
            for f in glob.glob(f"{OUT_DIR}/**/*", recursive=True):
                if os.path.isfile(f) and f.endswith((".js", ".html", ".txt")):
                    s = open(f, encoding="utf-8", errors="ignore").read()
                    for pat in [r"DH-DEMO00\d", r"cangcaloc_mock_orders", r"CA-BASA-PHILE", r"\b09\d{8}\b"]:
                        if re.search(pat, s):
                            hits.setdefault(pat, set()).add(os.path.relpath(f, OUT_DIR))
            check("M5-1 bản build thật (NEXT_PUBLIC_USE_MOCK=0) không còn mã/dữ liệu mock (DH-DEMO00x, kho đơn mock, SĐT giả 09xxxxxxxx)", not hits, json.dumps({k: sorted(v) for k, v in hits.items()}, ensure_ascii=False))

        browser.close()

    print(f"\nTổng: {total} ca, {len(failures)} FAIL, {len(lows)} LOW.")
    if failures:
        print("CÁC CA FAIL:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("TẤT CẢ CA PASS.")


if __name__ == "__main__":
    main()
