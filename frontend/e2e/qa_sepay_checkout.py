"""
QA E2E — hồ sơ 2026-09-26-sepay-cong-thanh-toan, story P4 (Shop, luồng thanh toán SePay).

Chạy với build THẬT (NEXT_PUBLIC_USE_MOCK=0) trỏ Django tạm + adapter thật, KHÔNG mock.
Chặn điều hướng thật tới SePay bằng route interception (page.route) để kiểm payload form
POST đúng thứ tự/nội dung mà không gọi ra ngoài.

Yêu cầu trước khi chạy (do QA tự dựng, xem 04-qa-report.md):
- Django chạy tại DJANGO_BASE (mặc định http://127.0.0.1:8123), có item QA-ROUND (giá lẻ
  xu) + batch còn hàng, seed_demo đã chạy.
- Adapter chạy tại ADAPTER_BASE (mặc định http://127.0.0.1:8199), SEPAY_SECRET_KEY khớp.
- Frontend build thật (`NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=<DJANGO_BASE> npm run
  build`) được serve tại SHOP_BASE (mặc định http://localhost:3410) bằng server tôn trọng
  trailingSlash/cleanUrls của firebase.json (vd `firebase serve --only hosting --port
  3410`), vì success_url/cancel_url/error_url do BE sinh không có "/" cuối trước query.

Không sửa code sản phẩm. Test data (item/batch) do QA tự tạo, không đụng
backend/apps hay frontend/app|components|lib.
"""
import json
import os
import re
import sys
import time
import urllib.parse

import requests
from playwright.sync_api import sync_playwright, expect

SHOP_BASE = os.environ.get("QA_SHOP_BASE", "http://localhost:3410")
DJANGO_BASE = os.environ.get("QA_DJANGO_BASE", "http://127.0.0.1:8123")
ADAPTER_BASE = os.environ.get("QA_ADAPTER_BASE", "http://127.0.0.1:8199")
SEPAY_SECRET = os.environ.get("QA_SEPAY_SECRET_KEY", "test-secret")

SHOTS_DIR = os.environ.get("QA_SHOTS_DIR", "/tmp")

failures = []


def check(label, cond, extra=""):
    status = "OK" if cond else "FAIL"
    print(f"[{status}] {label} {extra}")
    if not cond:
        failures.append(label)


def send_ipn(order_code, amount, ref):
    body = {
        "notification_type": "ORDER_PAID",
        "order": {
            "order_invoice_number": order_code,
            "amount": amount,
            "currency": "VND",
            "status": "CAPTURED",
        },
        "transaction": {"id": abs(hash(ref)) % 10_000_000, "reference_code": ref,
                         "paid_at": "2026-09-26T19:00:00+07:00"},
        "customer": {"name": "QA E2E", "phone": "0955555555"},
    }
    r = requests.post(f"{ADAPTER_BASE}/ipn/sepay", json=body,
                       headers={"X-Secret-Key": SEPAY_SECRET}, timeout=10)
    return r


def run(viewport, tag):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport)
        console_errors = []
        page.on("console", lambda m: m.type == "error" and console_errors.append(m.text))

        captured_forms = []

        def on_route(route, request):
            if request.method == "POST":
                captured_forms.append({
                    "url": request.url,
                    "post_data": request.post_data,
                })
            route.fulfill(status=200, content_type="text/html",
                           body="<html><body>QA stub SePay page</body></html>")

        page.route("https://pay-sandbox.sepay.vn/**", on_route)

        # 1) Đặt hàng bằng mặt hàng lẻ xu QA-ROUND (đã seed sẵn ngoài script này)
        page.goto(f"{SHOP_BASE}/shop/")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=f"{SHOTS_DIR}/qa-p4-{tag}-01-catalog.png", full_page=True)

        card = page.locator(".item-card", has_text="QA hàng lẻ xu")
        if card.count() == 0:
            check("Tìm thấy mặt hàng QA-ROUND trên bảng giá", False)
            browser.close()
            return
        card.get_by_role("button", name="Thêm vào giỏ").click()

        page.goto(f"{SHOP_BASE}/shop/checkout/")
        page.wait_for_load_state("networkidle")
        page.get_by_label("Tên người nhận").fill("QA E2E Tester")
        page.get_by_label("Số điện thoại").fill("0955555555")
        page.get_by_label("Địa chỉ giao hàng").fill("123 QA E2E street")
        page.get_by_role("button", name=re.compile("Đặt hàng|Xác nhận")).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".order-code", timeout=10000)
        page.screenshot(path=f"{SHOTS_DIR}/qa-p4-{tag}-02-payment-panel.png", full_page=True)

        order_code_el = page.locator(".order-code")
        order_code = order_code_el.inner_text().strip()
        check("P4-AC1: hiện mã đơn", bool(order_code), order_code)
        check("P4-AC1: có nút Thanh toán bằng VietQR",
              page.get_by_role("button", name="Thanh toán bằng VietQR").count() == 1)
        check("P4-AC1: không còn QR giả (chuỗi VIETQR|ORDER)",
              "VIETQR|ORDER" not in page.content())
        check("Không lộ giá vốn/PII lạ trong HTML checkout",
              not re.search(r"purchase_rate|landed_unit_cost|SEPAY_SECRET", page.content()))

        # 2) Bấm thanh toán -> chặn điều hướng thật, kiểm payload form
        page.get_by_role("button", name="Thanh toán bằng VietQR").click()
        page.wait_for_timeout(1500)
        check("P4-AC2: form POST đã được submit sang trang cổng (bị chặn bởi route)",
              len(captured_forms) == 1, f"count={len(captured_forms)}")
        if captured_forms:
            form = captured_forms[0]
            check("P4-AC2: checkout_url đúng miền sandbox",
                  form["url"].startswith("https://pay-sandbox.sepay.vn/"))
            pairs = urllib.parse.parse_qsl(form["post_data"] or "", keep_blank_values=True)
            names = [k for k, _ in pairs]
            expected_order = ["merchant", "operation", "payment_method", "order_amount",
                               "currency", "order_invoice_number", "order_description",
                               "success_url", "error_url", "cancel_url", "signature"]
            check("P1/P4: thứ tự field khớp SDK SePay (merchant..signature)",
                  names == expected_order, str(names))
            values = dict(pairs)
            check("P4: order_invoice_number khớp mã đơn vừa tạo",
                  values.get("order_invoice_number") == order_code, values.get("order_invoice_number"))
            check("P4: order_amount là số nguyên (không dấu chấm/phẩy)",
                  bool(re.fullmatch(r"\d+", values.get("order_amount", ""))),
                  values.get("order_amount"))
            check("BR-TT-13: không có secret/khoá trong payload form",
                  SEPAY_SECRET not in (form["post_data"] or ""))
            check("P4: success/cancel/error_url trỏ về đúng Shop domain",
                  all(values.get(k, "").startswith(SHOP_BASE) for k in
                      ("success_url", "error_url", "cancel_url")))

        total_amount_str = values.get("order_amount") if captured_forms else None

        # 3) Quay về success_url trước khi IPN tới -> "đang chờ xác nhận"
        page.goto(f"{SHOP_BASE}/shop/orders/?code={order_code}&result=success")
        page.wait_for_load_state("networkidle")
        page.get_by_label("4 số cuối SĐT").fill("5555")
        # Nếu Shop tự nhớ SĐT (sessionStorage) nút Tra cứu có thể đã tự chạy; bấm lại cho chắc
        page.get_by_role("button", name=re.compile("Tra cứu")).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        check("P4-AC3: hiện 'Đang chờ xác nhận thanh toán…' trước khi IPN tới",
              "Đang chờ xác nhận thanh toán" in page.content())
        check("P4-AC3: KHÔNG hiện 'Đã thanh toán' chỉ vì quay về success_url",
              "Đã thanh toán, đang soạn hàng" not in page.content())
        page.screenshot(path=f"{SHOTS_DIR}/qa-p4-{tag}-03-waiting.png", full_page=True)

        # 4) Bắn IPN thật qua adapter cho đúng số tiền đã ký, đợi trang tự cập nhật (poll 5s)
        r = send_ipn(order_code, int(total_amount_str), f"FT-E2E-{tag}-{int(time.time())}")
        check("Adapter trả 200 cho IPN hợp lệ", r.status_code == 200, r.text)

        page.wait_for_timeout(6500)  # > chu kỳ poll 5s
        check("P4-AC4: trang tự chuyển 'Đã thanh toán, đang soạn hàng' qua poll (không F5 tay)",
              "Đã thanh toán, đang soạn hàng" in page.content())
        page.screenshot(path=f"{SHOTS_DIR}/qa-p4-{tag}-04-paid.png", full_page=True)

        check("Không có lỗi console đỏ trong toàn bộ luồng", len(console_errors) == 0,
              str(console_errors))

        browser.close()


if __name__ == "__main__":
    run({"width": 390, "height": 844}, "mobile-390")
    run({"width": 1280, "height": 900}, "desktop-1280")

    print("\n=== TỔNG KẾT ===")
    if failures:
        print(f"{len(failures)} lỗi:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("Tất cả kiểm tra PASS.")
