# P8 Lô 3 — SR-09-AC4: màn gọi CSKH nhận 409 STALE_STATE -> hiện thông điệp + nút "Tải lại" -> bấm -> màn cập nhật.
# Mock (NEXT_PUBLIC_USE_MOCK=1) mô phỏng job tự huỷ chạy trước lúc bấm (phiếu SO260928-E83D36, dữ liệu giả).
# Chạy: cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out <thư-mục-out-riêng>
#       (cd <thư-mục-out-riêng> && python3 -m http.server 3201 &)
#       SHOTS=<thư mục ảnh> python3 e2e/sr09_ac4_stale_state.py     # tắt server sau khi xong
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3201")
SHOTS = os.environ.get("SHOTS", "/tmp")
CODE = "SO260928-E83D36"
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
    # ERP theo design (ED-15): hàng chờ là bảng; bấm dòng mở trang chi tiết, "Ghi kết quả gọi" mở hộp F2h.
    row = page.locator("table.lt tbody tr", has_text=CODE)
    row.first.wait_for(timeout=10_000)
    ok(f"[{tag}] hàng chờ có phiếu {CODE} (còn CONFIRMING)", row.count() == 1)

    row.first.locator("a").first.click()
    page.get_by_role("heading", name=CODE).wait_for(timeout=10_000)
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    modal = page.get_by_role("dialog")
    modal.get_by_text("Đã xác nhận", exact=False).first.wait_for(timeout=10_000)
    page.wait_for_timeout(400)
    ok(f"[{tag}] chưa có cảnh báo stale trước khi bấm", modal.get_by_role("alert").count() == 0)

    modal.locator("label", has_text="Đã xác nhận").first.click()
    modal.get_by_role("button", name="Lưu kết quả").click()
    alert = modal.get_by_role("alert").first
    alert.wait_for(timeout=10_000)
    ok(f"[{tag}] hiện đúng thông điệp `detail` của BE", DETAIL in alert.inner_text(), alert.inner_text().replace("\n", " | "))
    page.wait_for_timeout(300)
    box = alert.bounding_box()
    ok(f"[{tag}] cảnh báo nằm trong khung nhìn (không bị cuộn khuất)", box and box["y"] >= 0 and box["y"] + box["height"] <= viewport["height"], str(box))
    reload_btn = modal.get_by_role("button", name="Tải lại")
    # Bộ nút dùng chung của ERP mới: >= 44px trên điện thoại (vùng bấm ngoài trời), cỡ gọn trên màn máy tính.
    min_h = 43.5 if viewport["width"] < 768 else 30
    ok(f"[{tag}] có nút Tải lại cao >= {int(min_h + 0.5)}px", reload_btn.count() == 1 and reload_btn.bounding_box()["height"] >= min_h, str(reload_btn.bounding_box()))
    ok(f"[{tag}] các lựa chọn kết quả bị khoá, không gửi lại được", modal.locator("input[type=radio]").first.is_disabled())
    ok(f"[{tag}] không cuộn ngang", no_horizontal_scroll(page))
    page.screenshot(path=f"{SHOTS}/sr09-ac4-{tag}-1-thong-diep-409.png")

    reload_btn.click()
    page.wait_for_timeout(700)
    page.wait_for_load_state("networkidle")
    ok(f"[{tag}] bấm Tải lại: hộp đóng", page.get_by_role("dialog").count() == 0)
    ok(f"[{tag}] bấm Tải lại: trang chi tiết nạp lại, phiếu đã chuyển sang Báo hoàn tiền", page.get_by_role("heading", name=CODE).is_visible() and page.get_by_text("Báo hoàn tiền", exact=False).count() >= 1)
    page.screenshot(path=f"{SHOTS}/sr09-ac4-{tag}-2-sau-tai-lai.png")

    # Về hàng chờ (chuyển trang trong ứng dụng để giữ dữ liệu mock): phiếu rời tab mặc định
    page.get_by_role("link", name="Gọi xác nhận").first.click() if page.get_by_role("link", name="Gọi xác nhận").count() else None
    page.wait_for_url("**/confirmation/**")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    ok(f"[{tag}] phiếu rời hàng chờ mặc định (dữ liệu đã nạp lại)", page.locator("table.lt tbody tr", has_text=CODE).count() == 0)

    # Phiếu đã chuyển sang việc "báo hoàn tiền"
    page.get_by_role("tab", name="Gọi báo hoàn tiền").click()
    page.wait_for_timeout(700)
    page.wait_for_load_state("networkidle")
    ok(f"[{tag}] phiếu nằm ở tab Gọi báo hoàn tiền (REFUND_CALL)", page.locator("table.lt tbody tr", has_text=CODE).count() == 1)
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
