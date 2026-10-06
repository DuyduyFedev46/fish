"""E2 (lô dọn chữ AI, W1/W2): Shop tra đơn không lộ mã trạng thái thô và không có chữ "TTL". Bản build MOCK, dữ liệu giả.
Chạy: cd frontend && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3220 --bind 127.0.0.1 &)
      BASE=http://127.0.0.1:3220 SHOTS=/tmp python3 e2e/order_lookup_no_raw_codes.py"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3220")
SHOTS = os.environ.get("SHOTS", "/tmp")
RAW = re.compile(r"\b(BOOKED|PAID|PROCESSING|COMPLETED|CANCELLED|AUTO_CANCELLED|CONFIRMING|PREPARING|READY|DELIVERING|FAILED)\b|TTL")
# (mã đơn, 4 số cuối SĐT, nhãn giao hàng mong đợi hoặc None, nhãn đơn mong đợi hoặc None)
CASES = [
    ("DH-DEMO001", "6789", "Đang soạn hàng", None),
    ("DH-DEMO002", "1234", None, "Đang giữ chỗ, chờ thanh toán"),
    ("DH-DEMO003", "4321", "Đã huỷ", "Đã huỷ vì quá giờ thanh toán"),
    ("DH-DEMO004", "5678", "Đã huỷ", None),
    ("DH-DEMO005", "5001", "Chờ vựa gọi xác nhận", None),
    ("DH-DEMO006", "5002", "Đã soạn xong, chờ giao", None),
    ("DH-DEMO007", "5003", "Đang giao", None),
    ("DH-DEMO008", "5004", "Đã giao", None),
    ("DH-DEMO009", "5005", "Giao chưa thành công, vựa sẽ liên hệ lại", None),
]
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:300]), flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_context(viewport={"width": 390, "height": 800}, reduced_motion="reduce").new_page()
    for code, last4, delivery, status in CASES:
        page.goto(BASE + "/shop/orders/")
        page.wait_for_load_state("networkidle")
        page.fill("#orderCode", code)
        page.fill("#phoneLast4", last4)
        page.locator("form button[type=submit]").click()
        page.locator(".status-badge").wait_for(timeout=8000)
        body = page.inner_text("main")
        ok(f"{code}: không có mã thô hay 'TTL'", not RAW.search(body), RAW.search(body) and RAW.search(body).group(0))
        if delivery:
            ok(f"{code}: giao hàng = '{delivery}'", f"Trạng thái giao hàng: {delivery}" in body.replace("\n", " "), body[-200:])
        if status:
            ok(f"{code}: trạng thái đơn = '{status}'", status in page.locator(".status-badge").inner_text())
        if code == "DH-DEMO009":
            page.screenshot(path=f"{SHOTS}/e2-order-lookup-mobile.png", full_page=True)
    browser.close()
passed = sum(1 for _, c, _ in results if c)
print(f"== {passed}/{len(results)} PASS")
sys.exit(0 if passed == len(results) else 1)
