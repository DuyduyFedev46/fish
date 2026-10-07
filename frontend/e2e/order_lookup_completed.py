"""W37 L3 FE (S8-AC1, AC6): Shop tra đơn thấy "Hoàn tất" và "Đã giao" khi đơn đã nhận hàng. Bản build MOCK, dữ liệu giả.
Chạy: cd frontend && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3220 --bind 127.0.0.1 &)
      BASE=http://127.0.0.1:3220 SHOTS=/tmp python3 e2e/order_lookup_completed.py"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3220")
SHOTS = os.environ.get("SHOTS", "/tmp")
RAW = re.compile(r"\b(COMPLETED|PROCESSING|DELIVERING|FAILED)\b")
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:300]), flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_context(viewport={"width": 390, "height": 800}, reduced_motion="reduce").new_page()
    page.goto(BASE + "/shop/orders/")
    page.wait_for_load_state("networkidle")
    page.fill("#orderCode", "DH-DEMO008")
    page.fill("#phoneLast4", "5004")
    page.locator("form button[type=submit]").click()
    page.locator(".status-badge").wait_for(timeout=8000)
    body = page.inner_text("main").replace("\n", " ")
    ok("S8-AC6: badge 'Hoàn tất'", page.locator(".status-badge").inner_text().strip() == "Hoàn tất", page.locator(".status-badge").inner_text())
    ok("S8-AC1: dòng phiếu 'Đã giao'", "Trạng thái giao hàng: Đã giao" in body, body[-200:])
    ok("không lộ mã thô", not RAW.search(body))
    ok("không cuộn ngang (390px)", page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
    page.screenshot(path=f"{SHOTS}/shop_order_completed_390.png", full_page=True)
    browser.close()
passed = sum(1 for _, c, _ in results if c)
print(f"== {passed}/{len(results)} PASS")
sys.exit(0 if passed == len(results) else 1)
