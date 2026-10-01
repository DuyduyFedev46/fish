# P8 Lô 3 — SR-09-AC4: màn gọi CSKH nhận 409 STALE_STATE -> hiện thông điệp + nút "Tải lại" -> bấm -> màn cập nhật.
# Mock (NEXT_PUBLIC_USE_MOCK=1) mô phỏng job tự huỷ chạy trước lúc bấm (phiếu DH-260928-0036, dữ liệu giả).
# Chạy: cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out <thư-mục-out-riêng>
#       (cd <thư-mục-out-riêng> && python3 -m http.server 3213 &)
#       SHOTS=<thư mục ảnh> python3 e2e/sr09_ac4_stale_state.py     # tắt server sau khi xong
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3213")
SHOTS = os.environ.get("SHOTS", "/tmp")
CODE = "DH-260928-0036"
DETAIL = "Đơn đã bị huỷ — tải lại màn hình."
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


def run_case(browser, tag, viewport):
    ctx = browser.new_context(viewport=viewport)
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(m.text))
    login(page, "cs1")
    page.goto(BASE + "/confirmation/")
    page.wait_for_load_state("networkidle")
    card = page.locator("[class*='queueCard']", has_text=CODE)
    card.first.wait_for(timeout=10_000)
    ok(f"[{tag}] hàng chờ có phiếu {CODE} (còn CONFIRMING)", card.count() == 1)

    card.first.click()
    modal = page.get_by_role("dialog")
    modal.get_by_text("Đã xác nhận", exact=False).first.wait_for(timeout=10_000)
    page.wait_for_timeout(400)
    ok(f"[{tag}] chưa có cảnh báo stale trước khi bấm", page.get_by_test_id("confirmation-stale-alert").count() == 0)

    modal.get_by_role("button", name="Đã xác nhận").first.click()
    alert = page.get_by_test_id("confirmation-stale-alert")
    alert.wait_for(timeout=10_000)
    ok(f"[{tag}] hiện đúng thông điệp `detail` của BE", DETAIL in alert.inner_text(), alert.inner_text().replace("\n", " | "))
    page.wait_for_timeout(300)
    box = alert.bounding_box()
    ok(f"[{tag}] cảnh báo nằm trong khung nhìn (không bị cuộn khuất)", box and box["y"] >= 0 and box["y"] + box["height"] <= viewport["height"], str(box))
    reload_btn = alert.get_by_role("button", name="Tải lại")
    ok(f"[{tag}] có nút Tải lại cao >= 44px", reload_btn.count() == 1 and reload_btn.bounding_box()["height"] >= 43.5)
    ok(f"[{tag}] các nút kết quả bị khoá, không gửi lại được", modal.get_by_role("button", name="Đã xác nhận").first.is_disabled())
    ok(f"[{tag}] không cuộn ngang", no_horizontal_scroll(page))
    page.screenshot(path=f"{SHOTS}/sr09-ac4-{tag}-1-thong-diep-409.png")

    reload_btn.click()
    page.wait_for_timeout(700)
    page.wait_for_load_state("networkidle")
    ok(f"[{tag}] bấm Tải lại: modal đóng", page.get_by_role("dialog").count() == 0)
    ok(f"[{tag}] bấm Tải lại: phiếu rời hàng chờ mặc định (dữ liệu đã nạp lại)", page.locator("[class*='queueCard']", has_text=CODE).count() == 0)
    page.screenshot(path=f"{SHOTS}/sr09-ac4-{tag}-2-sau-tai-lai.png")

    # Phiếu đã chuyển sang việc "báo hoàn tiền"
    page.get_by_role("button", name="Báo hoàn tiền", exact=False).first.click()
    page.wait_for_timeout(700)
    page.wait_for_load_state("networkidle")
    ok(f"[{tag}] phiếu nằm ở tab báo hoàn tiền (REFUND_CALL)", page.locator("[class*='queueCard']", has_text=CODE).count() == 1)
    page.screenshot(path=f"{SHOTS}/sr09-ac4-{tag}-3-tab-bao-hoan-tien.png")
    ok(f"[{tag}] console không chứa SĐT/tên khách", not any(("0900000777" in l or "Khách Thử G" in l) for l in logs))
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    run_case(browser, "desktop-1280", {"width": 1280, "height": 800})
    run_case(browser, "mobile-375x667", {"width": 375, "height": 667})
    browser.close()

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} PASS")
sys.exit(1 if fails else 0)
