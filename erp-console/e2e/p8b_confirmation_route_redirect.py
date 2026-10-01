# P8b Lô 3 — đường dẫn /cskh/ (cũ) chuyển sang /confirmation/ (mới), giữ query; FE chỉ gọi API mới.
# Mock (NEXT_PUBLIC_USE_MOCK=1), tài khoản demo cs1 (dữ liệu giả).
# Chạy: cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out <thư-mục-out-riêng>
#       (cd <thư-mục-out-riêng> && python3 -m http.server 3242 &)
#       SHOTS=<thư mục ảnh> python3 e2e/p8b_confirmation_route_redirect.py     # tắt server sau khi xong
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3242")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")


def no_horizontal_scroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 360, "height": 740})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    login(page, "cs1")
    # (Mock không mô phỏng me.home = hàng đợi xác nhận; phần đó do vitest shared/lib/legacyNames.test.ts kiểm.)

    # Đường dẫn cũ: chuyển tới đường dẫn mới, giữ nguyên query
    page.goto(BASE + "/cskh/?state=CALLBACK")
    page.wait_for_url("**/confirmation/?state=CALLBACK", timeout=10_000)
    page.wait_for_load_state("networkidle")
    ok("/cskh/?state=CALLBACK chuyển sang /confirmation/?state=CALLBACK (giữ query)", page.url.endswith("/confirmation/?state=CALLBACK"), page.url)
    ok("màn Gọi xác nhận hiện sau khi chuyển", page.get_by_text("Gọi xác nhận", exact=False).count() > 0)

    page.go_back()
    page.wait_for_timeout(500)
    ok("nút Back không kẹt ở trang chuyển hướng", "/cskh/" not in page.url, page.url)

    page.goto(BASE + "/confirmation/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(600)
    log = page.evaluate("() => window.__caveMock.log")
    ok("FE gọi /api/confirmation/queue/", any("/api/confirmation/queue/" in x for x in log), str(log[-4:]))
    ok("FE không gọi /api/cskh/ nào", not any("/api/cskh/" in x for x in log), str([x for x in log if "cskh" in x]))
    ok("360px: không cuộn ngang", no_horizontal_scroll(page))
    page.screenshot(path=os.path.join(SHOTS, "p8b-l3-confirmation-360.png"), full_page=True)

    # Menu: mục Gọi xác nhận trỏ /confirmation/
    hrefs = page.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href'))")
    ok("không còn liên kết nào trỏ /cskh/ trong màn", not any(h and h.startswith("/cskh") for h in hrefs), str([h for h in hrefs if h and "cskh" in h]))
    ok("không có pageerror", not errors, str(errors))
    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} đạt")
sys.exit(1 if failed else 0)
