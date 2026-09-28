"""Đăng nhập console staging (tài khoản thử, dữ liệu giả) để chụp baseline TTI/TBT/LCP."""
from playwright.sync_api import sync_playwright

ERP = "https://cangca-erp-staging.web.app"
USER = "loc"
PASS = "Test@12345"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9223")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.goto(ERP + "/login/", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.fill("#u", USER)
    page.fill("#p", PASS)
    page.get_by_role("button", name="Đăng nhập").click()
    try:
        page.wait_for_url("**/overview/**", timeout=20000)
        status = "LOGIN_OK"
    except Exception:
        status = "LOGIN_FAIL"
    page.wait_for_load_state("networkidle")
    print("status:", status)
    print("url:", page.url)
    print("title:", page.title())
    body = page.content()
    print("has Tong quan:", "Tổng quan" in body or "Tong quan" in body)
    token = page.evaluate("localStorage.getItem('caveve_token')") if False else None
    keys = page.evaluate("Object.keys(localStorage)")
    print("localStorage keys:", keys)
    page.screenshot(path="/Users/dangthiduyen/Downloads/loc/scratchpad/qa-perf-baseline/shot-overview.png")
    page.close()
    browser.close()
