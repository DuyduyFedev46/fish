"""
QA rà soát A2 (2026-09-30-ra-soat-agy) — bằng chứng chạy thật cho hồ sơ
`2026-09-28-khung-go-live` (GL-01..GL-05), đáp ứng bảng "AC thiếu bằng chứng" và SR-21
(doc/features/2026-09-30-sua-loi-review/02-stories.md).

Chạy build THẬT của Shop (`NEXT_PUBLIC_USE_MOCK=0`) trên cổng 3101, chặn mọi request
`/api/**` bằng `page.route` để kiểm từng nhánh AC (thành công, lỗi 404/409/503, dữ liệu
rỗng) mà không cần backend thật — dữ liệu 100% giả định.

Cách chạy:
    cd frontend && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8199 \
        npx next dev -p 3101 &
    python3 e2e/ra-soat-a2-golive.py

Có thể phục vụ bản `out/` tĩnh (P8 Lô 6 làm vậy): QA_BASE=http://127.0.0.1:3106 QA_SHOT_DIR=<thư mục ảnh>.
"""
import json
import os
import sys
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("QA_BASE", "http://localhost:3101")
SHOT_DIR = os.environ.get("QA_SHOT_DIR", "/tmp")

SITE_INFO_OK = {
    "seller": {
        "name": "Vựa Thử Nghiệm QA",
        "business_type": "Hộ kinh doanh",
        "registration_no": "0000000001",
        "tax_code": "0000000002",
        "address": "1 Đường Giả, Phường Giả, Tỉnh Giả",
        "phone": "0900000000",
        "email": "lienhe@example.com",
        "registration_issued_by": "Sở Giả Định",
        "registration_issued_on": "2026-01-01",
    },
    "seller_complete": True,
    "privacy_consent_required": True,
    "confirm_call_notice": False,
    "confirm_call_hours": "7:00–20:00",
}
# 6 trang chính sách theo thứ tự lệnh nạp nội dung (06-marketing B4); tiêu đề lấy từ CMS.
FOOTER_LINKS_OK = [
    {"title": "Chính sách đổi trả và hoàn tiền", "slug": "doi-tra"},
    {"title": "Chính sách giao hàng", "slug": "giao-hang"},
    {"title": "Chính sách thanh toán", "slug": "thanh-toan"},
    {"title": "Chính sách quyền riêng tư", "slug": "quyen-rieng-tu"},
    {"title": "Điều kiện giao dịch chung", "slug": "dieu-khoan"},
    {"title": "Cơ chế giải quyết khiếu nại", "slug": "khieu-nai"},
]
POLICY_TITLES = [x["title"] for x in FOOTER_LINKS_OK]
POLICY_NAV = "footer nav:has(h2:text-is('Chính sách')) a"
CATALOG_OK = {
    "groups": [{"slug": "ca", "name": "Cá", "item_count": 1}],
    "items": [
        {
            "item_code": "CA-QA-01",
            "name": "Cá QA giả định",
            "item_type": "SIMPLE",
            "unit": "kg",
            "price": "100000",
            "stock_level": "in",
            "min_qty": "1",
            "qty_step": "0.5",
            "group": {"slug": "ca", "name": "Cá"},
            "short_note": "",
            "image": None,
        }
    ],
}
PRIVACY_POLICY_OK = {
    "slug": "chinh-sach-bao-mat",
    "title": "Chính sách bảo mật thông tin",
    "version": 1,
    "version_id": 918,
    "effective_from": "2026-09-28T00:00:00Z",
}
PAGE_CONTENT_OK = {
    "slug": "chinh-sach-bao-mat",
    "title": "Chính sách bảo mật thông tin",
    "html": "<p>Nội dung chính sách giả định cho QA.</p>",
}

failures = []


def check(label, cond):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}")
    if not cond:
        failures.append(label)


def route_json(route, data, status=200):
    route.fulfill(status=status, content_type="application/json", body=json.dumps(data))


def route_abort(route):
    route.abort("failed")


def install_common_routes(page, site_info=None, footer_links=None, catalog=None):
    page.route(
        "**/api/public/site-info/",
        lambda r: route_json(r, site_info if site_info is not None else SITE_INFO_OK),
    )
    page.route(
        "**/api/public/content/footer-links/",
        lambda r: route_json(r, footer_links if footer_links is not None else FOOTER_LINKS_OK),
    )
    page.route(
        "**/api/shop/catalog/",
        lambda r: route_json(r, catalog if catalog is not None else CATALOG_OK),
    )
    page.route("**/api/public/content/pages/by-slug/**", lambda r: route_json(r, PAGE_CONTENT_OK))
    page.route(
        "**/api/public/content/pages/**",
        lambda r: route_json(r, [{"title": "Bài viết QA giả định", "slug": "bai-qa"}]),
    )


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ---------- GL-01-AC2: footer F1 có dải pháp lý đủ thông tin người bán trên nhiều trang công khai ----------
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        install_common_routes(page)
        for route_path, label in [
            ("/", "Trang chủ"),
            ("/shop/", "Shop"),
            ("/trang/?slug=doi-tra", "Trang nội dung"),
        ]:
            page.goto(f"{BASE}{route_path}")
            page.wait_for_load_state("networkidle")
            foot = page.locator("footer").last.inner_text()
            check(
                f"GL-01-AC2 [{label}] dải pháp lý có tên, MST, địa chỉ, GCN ĐKKD (nơi cấp, ngày cấp)",
                all(
                    x in foot
                    for x in [
                        "Vựa Thử Nghiệm QA",
                        "MST 0000000002",
                        "1 Đường Giả",
                        "GCN ĐKKD số 0000000001 do Sở Giả Định cấp ngày 01/01/2026",
                    ]
                ),
            )
            check(f"GL-01-AC2 [{label}] SĐT là link tel:", page.locator('footer a[href="tel:0900000000"]').count() >= 1)
            check(f"GL-01-AC2 [{label}] Email là link mailto:", page.locator('footer a[href="mailto:lienhe@example.com"]').count() >= 1)
            check(f"GL-01-AC2 [{label}] chưa có link thông báo website thì không có khối logo", "thông báo website" not in foot)
            check(f"GL-01-AC2 [{label}] không có chữ chờ kiểu [..] hay 'Đang chờ'", "[" not in foot and "Đang chờ" not in foot)
        page.screenshot(path=f"{SHOT_DIR}/gl01-ac2-shop-footer.png", full_page=True)
        ctx.close()

        # ---------- GL-01-AC5: API site-info lỗi -> ẩn khối người bán, không trắng trang ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        console_errors = []
        page.on("console", lambda m: m.type == "error" and console_errors.append(m.text))
        page.route("**/api/public/site-info/", route_abort)
        page.route(
            "**/api/public/content/footer-links/", lambda r: route_json(r, FOOTER_LINKS_OK)
        )
        page.route("**/api/shop/catalog/", lambda r: route_json(r, CATALOG_OK))
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        body = page.inner_text("body")
        check("GL-01-AC5 khối người bán ẩn khi site-info lỗi", "MST" not in body)
        check("GL-01-AC5 trang không trắng (vẫn còn nội dung Shop)", "Cá QA giả định" in body)
        check(
            "GL-01-AC5 không lộ dữ liệu cá nhân/PII nào trong console lỗi",
            not any("0900000000" in e or "lienhe@example.com" in e for e in console_errors),
        )
        page.screenshot(path=f"{SHOT_DIR}/gl01-ac5-site-info-error.png", full_page=True)
        ctx.close()

        # ---------- GL-02-AC1: nhóm "Chính sách" của F1 đúng 6 link theo thứ tự CMS ----------
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        install_common_routes(page)
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        page.locator(POLICY_NAV).first.wait_for()
        links = page.locator(POLICY_NAV)
        titles = [links.nth(i).inner_text().strip() for i in range(links.count())]
        check("GL-02-AC1 footer có đúng 6 link chính sách theo thứ tự CMS", titles == POLICY_TITLES)
        check("GL-02-AC1 có 'Điều kiện giao dịch chung' và không có 'Điều khoản sử dụng'",
              "Điều kiện giao dịch chung" in titles and "Điều khoản sử dụng" not in page.locator("footer").last.inner_text())
        check("GL-02-AC1 có 'Cơ chế giải quyết khiếu nại'", "Cơ chế giải quyết khiếu nại" in titles)
        hrefs = [links.nth(i).get_attribute("href") for i in range(links.count())]
        check("GL-02-AC1 link trỏ /trang/?slug=...", all("/trang/" in h and "slug=" in h for h in hrefs))
        ctx.close()

        # ---------- GL-02-AC2/AC3: gỡ 1 trang khỏi footer, tải lại không cần build lại FE ----------
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        state = {"links": FOOTER_LINKS_OK}
        page.route("**/api/public/site-info/", lambda r: route_json(r, SITE_INFO_OK))
        page.route("**/api/shop/catalog/", lambda r: route_json(r, CATALOG_OK))
        page.route("**/api/public/content/footer-links/", lambda r: route_json(r, state["links"]))
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        check("GL-02-AC2/AC3 trước khi gỡ: 6 link hiện đủ", page.locator(POLICY_NAV).count() == 6)
        # Gỡ 1 trang (show_in_footer=False) mô phỏng bằng response mới, KHÔNG build lại FE
        state["links"] = [x for x in FOOTER_LINKS_OK if x["slug"] != "giao-hang"]
        page.reload()
        page.wait_for_load_state("networkidle")
        links = page.locator(POLICY_NAV)
        titles = [links.nth(i).inner_text().strip() for i in range(links.count())]
        check("GL-02-AC2/AC3 sau khi gỡ: link biến mất, 5 link còn lại giữ nguyên thứ tự",
              titles == [t for t in POLICY_TITLES if t != "Chính sách giao hàng"])
        ctx.close()

        # ---------- GL-02-AC4: footer-links lỗi -> ẩn nhóm Chính sách, dải pháp lý vẫn còn ----------
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.route("**/api/public/site-info/", lambda r: route_json(r, SITE_INFO_OK))
        page.route("**/api/shop/catalog/", lambda r: route_json(r, CATALOG_OK))
        page.route("**/api/public/content/footer-links/", route_abort)
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        body = page.inner_text("body")
        check("GL-02-AC4 nhóm Chính sách ẩn khi footer-links lỗi", page.locator(POLICY_NAV).count() == 0
              and "Chính sách đổi trả" not in body)
        check("GL-02-AC4 dải pháp lý người bán KHÔNG bị ảnh hưởng", "Vựa Thử Nghiệm QA" in body)
        check("GL-02-AC4 các nhóm khác của footer vẫn hiện", "Mua hàng" in body and "Về Cá Về" in body)
        ctx.close()

        # ---------- F2: footer rút gọn ở trang đặt hàng, 3 link chính sách mở tab mới ----------
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        install_common_routes(page)
        page.goto(f"{BASE}/shop/checkout/")
        page.wait_for_load_state("networkidle")
        f2 = page.locator("footer a[target='_blank']")
        t2 = [f2.nth(i).inner_text().replace("(mở tab mới)", "").strip() for i in range(f2.count())]
        check("F2 có đúng 3 link: đổi trả, quyền riêng tư, thanh toán",
              t2 == ["Chính sách đổi trả và hoàn tiền", "Chính sách quyền riêng tư", "Chính sách thanh toán"])
        check("F2 link có rel=noopener", all("noopener" in (f2.nth(i).get_attribute("rel") or "") for i in range(f2.count())))
        ctx.close()

        # ---------- GL-02-AC5: viewport 375x667, không cuộn ngang, vùng chạm >= 44px ----------
        ctx = browser.new_context(viewport={"width": 375, "height": 667})
        page = ctx.new_page()
        install_common_routes(page)
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        client_w = page.evaluate("document.documentElement.clientWidth")
        check(f"GL-02-AC5 không cuộn ngang ở 375px (scrollWidth={scroll_w} clientWidth={client_w})", scroll_w <= client_w + 1)
        # Điện thoại: nhóm "Chính sách" thu gọn mặc định, mở ra rồi mới đo (SHOP-1-05 AC3).
        page.locator("footer summary:has(h2:text-is('Chính sách'))").click()
        link = page.locator(POLICY_NAV).first
        box = link.bounding_box()
        check(f"GL-02-AC5 vùng chạm link >= 44px chiều cao (đo {box['height'] if box else None})", box is not None and box["height"] >= 44)
        page.screenshot(path=f"{SHOT_DIR}/gl02-ac5-mobile-375.png", full_page=True)
        ctx.close()

        # ---------- GL-03-AC2: checkbox chưa tick, nhãn nêu mục đích, link mở tab mới, nút khoá ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        install_common_routes(page)
        page.route(
            "**/api/public/content/pages/by-role/privacy/", lambda r: route_json(r, PRIVACY_POLICY_OK)
        )
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Thêm vào giỏ").first.click()
        page.goto(f"{BASE}/shop/checkout/")
        page.wait_for_load_state("networkidle")
        checkbox = page.locator('input[type="checkbox"]')
        check("GL-03-AC2 checkbox đồng ý CHƯA tick sẵn", checkbox.is_checked() is False)
        label_text = page.inner_text("form")
        check(
            "GL-03-AC2 nhãn nêu mục đích giao hàng/xác nhận đơn",
            "giao hàng" in label_text and "xác nhận đơn" in label_text,
        )
        policy_link = page.locator('form a[href*="/trang/"]', has_text="Chính sách bảo mật")
        check("GL-03-AC2 link chính sách mở tab mới (target=_blank)", policy_link.get_attribute("target") == "_blank")
        submit_btn = page.get_by_role("button", name="Đặt hàng", exact=False)
        check("GL-03-AC2 nút Đặt hàng bị khoá khi chưa tick", submit_btn.is_disabled())
        checkbox.check()
        check("GL-03-AC2 nút Đặt hàng mở khoá sau khi tick", submit_btn.is_disabled() is False)
        page.screenshot(path=f"{SHOT_DIR}/gl03-ac2-checkout-consent.png", full_page=True)
        ctx.close()

        # ---------- GL-03-AC4: chính sách đổi phiên bản -> 409 POLICY_CHANGED ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        install_common_routes(page)
        page.route(
            "**/api/public/content/pages/by-role/privacy/", lambda r: route_json(r, PRIVACY_POLICY_OK)
        )
        page.route(
            "**/api/shop/orders/",
            lambda r: route_json(
                r,
                {
                    "detail": "Chính sách vừa cập nhật, vui lòng xem và đồng ý lại.",
                    "code": "POLICY_CHANGED",
                    "current": {"version": 2, "version_id": 930, "slug": "chinh-sach-bao-mat"},
                },
                status=409,
            )
            if r.request.method == "POST"
            else r.continue_(),
        )
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Thêm vào giỏ").first.click()
        page.goto(f"{BASE}/shop/checkout/")
        page.wait_for_load_state("networkidle")
        page.fill("#name", "Khách QA")
        page.fill("#phone", "0912345678")
        page.fill("#address", "123 Đường QA giả định")
        page.locator('input[type="checkbox"]').check()
        page.get_by_role("button", name="Đặt hàng", exact=False).click()
        page.wait_for_timeout(500)
        body = page.inner_text("body")
        check(
            "GL-03-AC4 báo lỗi 'chính sách vừa cập nhật'",
            "Chính sách vừa cập nhật" in body,
        )
        checkbox = page.locator('input[type="checkbox"]')
        check("GL-03-AC4 sau 409: checkbox bị bỏ tick", checkbox.is_checked() is False)
        check("GL-03-AC4 dữ liệu form còn nguyên (tên)", page.input_value("#name") == "Khách QA")
        check("GL-03-AC4 dữ liệu form còn nguyên (SĐT)", page.input_value("#phone") == "0912345678")
        check("GL-03-AC4 dữ liệu form còn nguyên (địa chỉ)", page.input_value("#address") == "123 Đường QA giả định")
        page.screenshot(path=f"{SHOT_DIR}/gl03-ac4-policy-changed.png", full_page=True)
        ctx.close()

        # ---------- GL-03-AC5: chưa có chính sách đã đăng -> "Shop tạm chưa nhận đơn" ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        install_common_routes(page)
        page.route("**/api/public/content/pages/by-role/privacy/", lambda r: route_json(r, {"detail": "Không tìm thấy"}, status=404))
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Thêm vào giỏ").first.click()
        page.goto(f"{BASE}/shop/checkout/")
        page.wait_for_load_state("networkidle")
        body = page.inner_text("body")
        check("GL-03-AC5 hiện màn 'Shop tạm chưa nhận đơn'", "Shop tạm chưa nhận đơn" in body)
        check("GL-03-AC5 form đặt hàng không còn (không có ô Tên người nhận)", page.locator("#name").count() == 0)
        page.screenshot(path=f"{SHOT_DIR}/gl03-ac5-shop-closed.png", full_page=True)
        ctx.close()

        # ---------- GL-03-AC8: log console + localStorage/sessionStorage/URL không có PII ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        console_logs = []
        page.on("console", lambda m: console_logs.append(m.text))
        install_common_routes(page)
        page.route(
            "**/api/public/content/pages/by-role/privacy/", lambda r: route_json(r, PRIVACY_POLICY_OK)
        )
        page.route(
            "**/api/shop/orders/",
            lambda r: route_json(
                r, {"order_code": "DH-QA-0001", "total_amount": "100000", "booked_expires_at": "2099-01-01T00:00:00Z"}, status=201
            )
            if r.request.method == "POST"
            else r.continue_(),
        )
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Thêm vào giỏ").first.click()
        page.goto(f"{BASE}/shop/checkout/")
        page.wait_for_load_state("networkidle")
        page.fill("#name", "Khách QA Ẩn Danh")
        page.fill("#phone", "0912345678")
        page.fill("#address", "999 Đường Bí Mật QA")
        page.locator('input[type="checkbox"]').check()
        page.get_by_role("button", name="Đặt hàng", exact=False).click()
        page.wait_for_timeout(500)
        local_storage = page.evaluate("JSON.stringify(window.localStorage)")
        session_storage = page.evaluate("JSON.stringify(window.sessionStorage)")
        url = page.url
        pii_terms = ["0912345678", "Khách QA Ẩn Danh", "999 Đường Bí Mật QA"]
        check(
            "GL-03-AC8 localStorage không chứa SĐT/tên/địa chỉ đầy đủ",
            not any(t in local_storage for t in pii_terms),
        )
        check(
            "GL-03-AC8 sessionStorage không chứa SĐT/tên/địa chỉ đầy đủ",
            not any(t in session_storage for t in pii_terms),
        )
        check("GL-03-AC8 sessionStorage CÓ giữ order_code + 4 số cuối (hành vi hiện có)", "DH-QA-0001" in session_storage and "5678" in session_storage)
        check("GL-03-AC8 URL không chứa PII", not any(t in url for t in pii_terms))
        check(
            "GL-03-AC8 console log không chứa SĐT/tên/địa chỉ đầy đủ",
            not any(any(t in line for t in pii_terms) for line in console_logs),
        )
        ctx.close()

        # ---------- GL-04-AC1/AC3/AC4/AC5: thông báo gọi xác nhận ở màn thanh toán ----------
        for notice_on, label in [(True, "bật"), (False, "tắt")]:
            ctx = browser.new_context()
            page = ctx.new_page()
            site_info = dict(SITE_INFO_OK)
            site_info["confirm_call_notice"] = notice_on
            install_common_routes(page, site_info=site_info)
            page.route(
                "**/api/public/content/pages/by-role/privacy/", lambda r: route_json(r, PRIVACY_POLICY_OK)
            )
            page.route(
                "**/api/shop/orders/",
                lambda r: route_json(
                    r, {"order_code": "DH-QA-0002", "total_amount": "100000", "booked_expires_at": "2099-01-01T00:00:00Z"}, status=201
                )
                if r.request.method == "POST"
                else r.continue_(),
            )
            page.goto(f"{BASE}/shop/")
            page.wait_for_load_state("networkidle")
            page.get_by_role("button", name="Thêm vào giỏ").first.click()
            page.goto(f"{BASE}/shop/checkout/")
            page.wait_for_load_state("networkidle")
            page.fill("#name", "Khách QA")
            page.fill("#phone", "0912345678")
            page.fill("#address", "123 Đường QA")
            page.locator('input[type="checkbox"]').check()
            page.get_by_role("button", name="Đặt hàng", exact=False).click()
            page.wait_for_timeout(500)
            notice = page.locator('[data-testid="confirm-call-notice"]')
            if notice_on:
                check("GL-04-AC1 thông báo hiện đúng 4 số cuối + khung giờ", notice.count() == 1 and "5678" in notice.inner_text() and "7:00" in notice.inner_text())
                check("GL-04-AC3 DOM không chứa SĐT đầy đủ", "0912345678" not in page.inner_text("body"))
                check("GL-04-AC3 URL không có tham số SĐT", "0912345678" not in page.url)
                page.screenshot(path=f"{SHOT_DIR}/gl04-ac1-notice-on.png", full_page=True)
            else:
                check("GL-04-AC4 confirm_call_notice=false -> không có thông báo", notice.count() == 0)
            ctx.close()

        # ---------- GL-04-AC2: quay về /shop/orders?code=..&result=success -> vẫn có thông báo ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        site_info = dict(SITE_INFO_OK)
        site_info["confirm_call_notice"] = True
        install_common_routes(page, site_info=site_info)
        page.route(
            "**/api/shop/orders/DH-QA-0003/**",
            lambda r: route_json(
                r,
                {
                    "order_code": "DH-QA-0003",
                    "status": "PAID",
                    "status_label": "Đã thanh toán",
                    "total_amount": "100000",
                    "lines": [],
                    "delivery": None,
                    "booked_expires_at": None,
                    "is_paid": True,
                    "is_expired": False,
                },
            ),
        )
        # Mô phỏng "vừa đặt hàng" đã lưu order_code + 4 số cuối vào sessionStorage trước khi
        # quay lại từ cổng thanh toán (đúng hành vi rememberOrderContact khi tạo đơn).
        page.goto(f"{BASE}/shop/")
        page.evaluate(
            "window.sessionStorage.setItem('cangcaloc_last_order_contact_v1', JSON.stringify({order_code:'DH-QA-0003', phone_last4:'5678'}))"
        )
        page.goto(f"{BASE}/shop/orders/?code=DH-QA-0003&result=success")
        page.wait_for_load_state("networkidle")
        notice = page.locator('[data-testid="confirm-call-notice"]')
        check("GL-04-AC2 sau khi quay về từ cổng thanh toán vẫn có thông báo (dùng sessionStorage)", notice.count() == 1 and "5678" in notice.inner_text())
        check("GL-04-AC2/AC3 URL không có SĐT đầy đủ", "0912345678" not in page.url)
        page.screenshot(path=f"{SHOT_DIR}/gl04-ac2-return-success.png", full_page=True)
        ctx.close()

        # ---------- GL-04-AC5: site-info lỗi -> không thông báo, luồng thanh toán không bị chặn ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        page.route("**/api/public/site-info/", route_abort)
        page.route("**/api/public/content/footer-links/", lambda r: route_json(r, FOOTER_LINKS_OK))
        page.route("**/api/shop/catalog/", lambda r: route_json(r, CATALOG_OK))
        page.route(
            "**/api/public/content/pages/by-role/privacy/", lambda r: route_json(r, PRIVACY_POLICY_OK)
        )
        page.route(
            "**/api/shop/orders/",
            lambda r: route_json(
                r, {"order_code": "DH-QA-0004", "total_amount": "100000", "booked_expires_at": "2099-01-01T00:00:00Z"}, status=201
            )
            if r.request.method == "POST"
            else r.continue_(),
        )
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Thêm vào giỏ").first.click()
        page.goto(f"{BASE}/shop/checkout/")
        page.wait_for_load_state("networkidle")
        # site-info lỗi -> privacy_consent_required không xác định được từ site-info, nhưng
        # policy vẫn tải được nên consentRequired mặc định true (an toàn) và form vẫn dùng được.
        page.fill("#name", "Khách QA")
        page.fill("#phone", "0912345678")
        page.fill("#address", "123 Đường QA")
        checkbox = page.locator('input[type="checkbox"]')
        if checkbox.count():
            checkbox.check()
        submit = page.get_by_role("button", name="Đặt hàng", exact=False)
        check("GL-04-AC5 luồng thanh toán KHÔNG bị chặn dù site-info lỗi (nút còn bấm được)", submit.is_disabled() is False)
        submit.click()
        page.wait_for_timeout(500)
        notice = page.locator('[data-testid="confirm-call-notice"]')
        check("GL-04-AC5 không có thông báo gọi xác nhận khi site-info lỗi", notice.count() == 0)
        check("GL-04-AC5 đơn vẫn đặt thành công (không bị site-info lỗi chặn)", "Đặt hàng thành công" in page.inner_text("body"))
        ctx.close()

        browser.close()

    print(f"\nTổng: {len(failures)} lỗi / các ca đã chạy ở trên.")
    if failures:
        print("CÁC CA FAIL:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("TẤT CẢ CA PASS.")


if __name__ == "__main__":
    main()
