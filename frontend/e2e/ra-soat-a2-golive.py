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
    },
    "seller_complete": True,
    "privacy_consent_required": True,
    "confirm_call_notice": False,
    "confirm_call_hours": "7:00–20:00",
}
FOOTER_LINKS_OK = [
    {"title": "Chính sách bảo mật", "slug": "chinh-sach-bao-mat"},
    {"title": "Chính sách đổi trả", "slug": "chinh-sach-doi-tra"},
    {"title": "Chính sách thanh toán", "slug": "chinh-sach-thanh-toan"},
]
CATALOG_OK = [
    {
        "item_code": "CA-QA-01",
        "name": "Cá QA giả định",
        "group": "ca",
        "item_type": "SIMPLE",
        "unit": "Kg",
        "price": 100000,
        "sellable_qty": 50,
        "image": None,
    }
]
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

        # ---------- GL-01-AC2: footer đủ 7 thông tin trên nhiều trang công khai ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        install_common_routes(page)
        for route_path, label in [
            ("/", "Landing"),
            ("/shop/", "Shop"),
            ("/trang/?slug=chinh-sach-bao-mat", "Trang nội dung"),
        ]:
            page.goto(f"{BASE}{route_path}")
            page.wait_for_load_state("networkidle")
            body = page.inner_text("body")
            check(
                f"GL-01-AC2 [{label}] footer có đủ 7 thông tin người bán",
                all(
                    s in body
                    for s in [
                        "Vựa Thử Nghiệm QA",
                        "Hộ kinh doanh",
                        "0000000001",
                        "0000000002",
                        "1 Đường Giả",
                        "0900000000",
                        "lienhe@example.com",
                    ]
                ),
            )
            tel = page.locator('a[href="tel:0900000000"]')
            mailto = page.locator('a[href="mailto:lienhe@example.com"]')
            check(f"GL-01-AC2 [{label}] SĐT là link tel:", tel.count() >= 1)
            check(f"GL-01-AC2 [{label}] Email là link mailto:", mailto.count() >= 1)
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
        check("GL-01-AC5 khối người bán ẩn khi site-info lỗi", "Thông tin đơn vị bán hàng" not in body)
        check("GL-01-AC5 trang không trắng (vẫn còn nội dung Shop)", "Cá QA giả định" in body)
        check(
            "GL-01-AC5 không lộ dữ liệu cá nhân/PII nào trong console lỗi",
            not any("0900000000" in e or "lienhe@example.com" in e for e in console_errors),
        )
        page.screenshot(path=f"{SHOT_DIR}/gl01-ac5-site-info-error.png", full_page=True)
        ctx.close()

        # ---------- GL-02-AC1: 3 link footer theo đúng thứ tự ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        install_common_routes(page)
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        links = page.locator("footer a[href*='/trang/']")
        titles = [links.nth(i).inner_text() for i in range(links.count())]
        check(
            "GL-02-AC1 footer có đúng 3 link theo thứ tự cấu hình",
            titles == ["Chính sách bảo mật", "Chính sách đổi trả", "Chính sách thanh toán"],
        )
        hrefs = [links.nth(i).get_attribute("href") for i in range(links.count())]
        check(
            "GL-02-AC1 link trỏ /trang/?slug=...",
            all("/trang/" in h and "slug=" in h for h in hrefs),
        )
        ctx.close()

        # ---------- GL-02-AC2/AC3: gỡ 1 trang khỏi footer, tải lại không cần build lại FE ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        state = {"links": FOOTER_LINKS_OK}
        page.route("**/api/public/site-info/", lambda r: route_json(r, SITE_INFO_OK))
        page.route("**/api/shop/catalog/", lambda r: route_json(r, CATALOG_OK))
        page.route("**/api/public/content/footer-links/", lambda r: route_json(r, state["links"]))
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        links = page.locator("footer a[href*='/trang/']")
        check("GL-02-AC2/AC3 trước khi gỡ: 3 link hiện đủ", links.count() == 3)
        # Gỡ 1 trang (show_in_footer=False) mô phỏng bằng response mới, KHÔNG build lại FE
        state["links"] = [FOOTER_LINKS_OK[0], FOOTER_LINKS_OK[2]]
        page.reload()
        page.wait_for_load_state("networkidle")
        links = page.locator("footer a[href*='/trang/']")
        titles = [links.nth(i).inner_text() for i in range(links.count())]
        check(
            "GL-02-AC2/AC3 sau khi gỡ: link biến mất, 2 link còn lại giữ nguyên",
            titles == ["Chính sách bảo mật", "Chính sách thanh toán"],
        )
        ctx.close()

        # ---------- GL-02-AC4: footer-links lỗi -> ẩn khối link, khối người bán vẫn còn ----------
        ctx = browser.new_context()
        page = ctx.new_page()
        page.route("**/api/public/site-info/", lambda r: route_json(r, SITE_INFO_OK))
        page.route("**/api/shop/catalog/", lambda r: route_json(r, CATALOG_OK))
        page.route("**/api/public/content/footer-links/", route_abort)
        page.goto(f"{BASE}/shop/")
        page.wait_for_load_state("networkidle")
        body = page.inner_text("body")
        check("GL-02-AC4 khối link ẩn khi footer-links lỗi", "Chính sách bảo mật" not in body)
        check(
            "GL-02-AC4 khối người bán KHÔNG bị ảnh hưởng",
            "Vựa Thử Nghiệm QA" in body,
        )
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
        link = page.locator("footer a[href*='/trang/']").first
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
