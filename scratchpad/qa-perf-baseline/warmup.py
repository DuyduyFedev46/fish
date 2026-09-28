"""Warm-up: tải trước các trang sẽ đo (không tính vào kết quả) + chụp ảnh bằng chứng."""
from playwright.sync_api import sync_playwright

PAGES = {
    "erp-login": "https://cangca-erp-staging.web.app/login/",
    "shop": "https://cangca-loc-staging.web.app/shop/",
    "landing": "https://cangca-loc-staging.web.app/",
}

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9223")
    ctx = browser.contexts[0]
    for name, url in PAGES.items():
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.goto(url, wait_until="load")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"/Users/dangthiduyen/Downloads/loc/scratchpad/qa-perf-baseline/warm-{name}.png")
        print(name, "->", page.title(), "| errors:", len(errors))
        page.close()
    browser.close()
