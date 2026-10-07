# E2E sửa lỗi khung ERP (vòng 2 sau review Techlead + QA): mỗi mục sửa có một ca chạy trên trình duyệt thật.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   node_modules/.bin/vite build --config e2e/qa_harness_ed_batch1/vite.config.mjs
#   (cd e2e/qa_harness_ed_batch1/dist && python3 -m http.server 3102 &)
#   SHOTS=<thư mục ảnh> python3 e2e/ed_shell_fixes.py      # tắt hai server sau khi xong
# Kiểm: ED-01-AC4 Back quay về tab trước · ED-03-AC4 dải mất mạng có "Dữ liệu lúc", nút Thử lại, dữ liệu mờ ·
# đếm ngược giữ chỗ nhảy từng giây · "Về ..." theo vai ở 404 · Esc ở ⌘K trả tiêu điểm · cột khoá không làm cuộn ngang 360.
# Không dùng wait_for_timeout: chỉ chờ điều kiện.

import os
import pathlib
import re

from playwright.sync_api import expect, sync_playwright

from e2e_support import finish, page_404_body

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
HARNESS = os.environ.get("HARNESS", "http://127.0.0.1:3102")
SHOTS = os.environ.get("SHOTS", "/tmp")

# Dòng đơn trong bảng /orders/ (DataTable: dòng bấm được có class lt-click). Class cũ .order-open đã bỏ từ Lô 3.
ORDER_ROW = "#main tbody tr.lt-click"
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ---------- ED-01-AC4: Back quay về tab trước (harness, vì mock ERP chưa có màn nào dùng tab theo URL) ----------
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(HARNESS + "/?m=tabparam")
    expect(page.locator("#tab-now")).to_have_text("all")
    page.get_by_role("tab", name="Hàng chờ thanh toán").click()
    expect(page.locator("#tab-now")).to_have_text("pay")
    page.get_by_role("tab", name="Phiếu hoàn").click()
    expect(page.locator("#tab-now")).to_have_text("ref")
    ok("ED-01-AC4 đổi tab ghi vào URL", "tab=ref" in page.url, page.url)
    page.go_back()
    expect(page.locator("#tab-now")).to_have_text("pay")
    ok("ED-01-AC4 Back từ 'ref' về 'pay'", True)
    page.go_back()
    expect(page.locator("#tab-now")).to_have_text("all")
    ok("ED-01-AC4 Back tiếp về 'all'", True)
    page.go_forward()
    expect(page.locator("#tab-now")).to_have_text("pay")
    ok("ED-01-AC4 Forward trở lại 'pay'", True)
    # Bấm lại đúng tab đang chọn không chồng thêm bước lịch sử
    n0 = page.evaluate("() => history.length")
    page.get_by_role("tab", name="Hàng chờ thanh toán").click()
    ok("ED-01-AC4 bấm lại tab đang chọn: không thêm bước lịch sử", page.evaluate("() => history.length") == n0)
    # Giá trị tab rác trên URL -> về tab đầu, không vỡ
    page.goto(HARNESS + "/?m=tabparam&tab=%3Cscript%3E")
    expect(page.locator("#tab-now")).to_have_text("all")
    ok("ED-01-AC4 tab rác trên URL -> tab mặc định", True)
    ctx.close()

    # ---------- 360: cột khoá giá vốn không gây cuộn ngang trang ----------
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(HARNESS + "/?m=rows&locked=1")
    page.wait_for_selector("table.lt")
    ok("DataTable 360: có quyền xem giá vốn, trang không cuộn ngang",
       page.evaluate("() => document.documentElement.scrollWidth") <= 360,
       str(page.evaluate("() => document.documentElement.scrollWidth")))
    ok("DataTable 360: vùng bảng tự cuộn ngang bên trong",
       page.evaluate("() => { const s = document.querySelector('.lt-scroll'); return s.scrollWidth > s.clientWidth; }"))
    page.screenshot(path=f"{SHOTS}/ed-fix-360-locked.png")
    page.goto(HARNESS + "/?m=rows&locked=0")
    page.wait_for_selector("table.lt")
    ok("DataTable: không có quyền thì không có cột 'Giá vốn'", page.get_by_text("Giá vốn").count() == 0)
    ctx.close()

    # ---------- App thật (mock): mất mạng, đếm ngược, 404 theo vai, Esc ở ⌘K ----------
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "loc")
    page.goto(BASE + "/orders/")
    page.wait_for_selector(ORDER_ROW, state="attached")
    # Đếm ngược chạy từng giây (M2): đọc chữ "còn mm:ss" hai lần, phải khác nhau trong ~vài giây.
    # Mock lưu ngày tại giờ VN: đơn BOOKED còn hạn thì mới có đếm; nếu mock không có đơn còn hạn thì bỏ qua ca này có ghi chú.
    cd = page.locator("span", has_text=re.compile(r"^.*còn \d\d:\d\d$")).first
    if cd.count():
        t1 = cd.inner_text()
        page.wait_for_function(
            "(t) => { const el = [...document.querySelectorAll('span')].find(e => /còn \\d\\d:\\d\\d$/.test(e.textContent) && e.children.length <= 1); return el && el.textContent !== t; }",
            arg=t1, timeout=5000)
        ok("M2 đếm ngược giữ chỗ đổi trong 5 giây (nhảy từng giây)", True, t1)
    else:
        ok("M2 đếm ngược: mock không có đơn còn hạn giữ chỗ (bỏ qua ca)", True)

    # Mất mạng trên /orders/ (M1)
    ctx.set_offline(True)
    page.evaluate("() => window.dispatchEvent(new Event('offline'))")
    banner = page.locator(".offline-banner")
    expect(banner).to_be_visible()
    ok("ED-03-AC4 dải mất mạng ghi 'Dữ liệu lúc dd/mm/yyyy hh:mm'",
       re.search(r"Dữ liệu lúc \d{2}/\d{2}/\d{4} \d{2}:\d{2}", banner.inner_text()) is not None, banner.inner_text())
    ok("ED-03-AC4 có nút Thử lại", banner.get_by_role("button", name="Thử lại").count() == 1)
    ok("ED-03-AC4 dữ liệu cũ bị làm mờ", page.locator("#main .is-stale").count() >= 1)
    page.screenshot(path=f"{SHOTS}/ed-fix-offline-orders.png")
    ctx.set_offline(False)
    page.evaluate("() => window.dispatchEvent(new Event('online'))")
    expect(banner).to_have_count(0)
    ok("ED-03 có mạng lại: dải tắt, hết mờ", page.locator("#main .is-stale").count() == 0)
    # Thử lại không vỡ trang
    ctx.set_offline(True)
    page.evaluate("() => window.dispatchEvent(new Event('offline'))")
    expect(banner).to_be_visible()
    banner.get_by_role("button", name="Thử lại").click()
    expect(page.locator(ORDER_ROW).first).to_be_visible()
    ok("ED-03-AC4 bấm Thử lại: danh sách vẫn còn, trang không vỡ", True)
    ctx.set_offline(False)
    page.evaluate("() => window.dispatchEvent(new Event('online'))")

    # Esc ở ⌘K trả tiêu điểm cho nút mở (B6)
    opener = page.locator("button.search-trigger")
    opener.focus()
    opener.click()
    expect(page.get_by_role("dialog", name="Tìm màn hình")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog", name="Tìm màn hình")).to_have_count(0)
    page.wait_for_function("() => document.activeElement && document.activeElement.classList.contains('search-trigger')")
    ok("B6 Esc đóng ⌘K: tiêu điểm về nút mở", True)
    page.keyboard.press("Control+k")
    expect(page.get_by_role("dialog", name="Tìm màn hình")).to_be_visible()
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.activeElement && document.activeElement !== document.body")
    ok("B6 mở bằng phím tắt rồi Esc: tiêu điểm không rơi về body", True)
    ctx.close()

    # 404 theo vai (B2): giao1 -> "Về Việc giao của tôi", loc -> "Về Tổng quan"
    for user, label, target in [("giao1", "Về Việc giao của tôi", "/my-deliveries/"), ("loc", "Về Tổng quan", "/overview/")]:
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page = ctx.new_page()
        login(page, user)
        body = page_404_body(BASE)
        page.route("**/khong-co-man-nay/**", lambda route: route.fulfill(status=404, content_type="text/html; charset=utf-8", body=body))
        page.goto(BASE + "/khong-co-man-nay/")
        link = page.get_by_role("link", name=label)
        expect(link).to_be_visible()
        ok(f"B2 404 cho {user}: có nút '{label}'", True)
        link.click()
        page.wait_for_url(f"**{target}")
        ok(f"B2 404 cho {user}: bấm về {target}", target in page.url, page.url)
        ctx.close()

    browser.close()

for n, c, e in results:
    print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + e))
print(f"{sum(1 for _, c, _ in results if c)}/{len(results)} PASS")
finish(results)
