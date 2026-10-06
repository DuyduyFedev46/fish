# E2E ERP theo design, Lô 1 (khung): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/ed_batch1_shell.py      # tắt server sau khi xong
# Kiểm: menu 4 vai mock đúng UI-RULES §2.1 · thu gọn menu nhớ sau khi tải lại · menu avatar đúng 3 mục, không "Làm mới" ·
# 404 nằm trong khung (http.server tĩnh không có 404 fallback nên giả bằng page.route) · giá trị rác trong localStorage.
# Không dùng wait_for_timeout: chỉ chờ điều kiện.

import os
import pathlib

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
OUT_404 = pathlib.Path(__file__).resolve().parent.parent / "out" / "404.html"
results = []

# UI-RULES §2.1: thứ tự đầy đủ của menu trái (mục có thể ẩn theo quyền nhưng không đổi thứ tự).
FULL_ORDER = [
    "Tổng quan",
    "Đơn & tiền", "Khách hàng", "Gọi xác nhận", "Giao hàng", "Việc giao của tôi",
    "Mua hàng", "Nhà cung cấp", "Kho & lô", "Hàng hoàn", "Kiểm kê", "Sổ nhập xuất", "Danh mục & giá",
    "Báo cáo lãi lỗ", "Hoá đơn bán", "Hoá đơn mua & chi phí",
    "Nội dung",
    "Nhân sự", "Phân quyền", "Nhật ký hoạt động", "Chính sách AI", "Báo cáo AI",
]
SECTIONS = ["Bán hàng", "Hàng hoá & kho", "Kế toán", "Website", "Quản trị"]
# Mock chưa có quyền mới (xem 03-dev-notes.md, Lô 1 — FE) nên mỗi vai chỉ thấy phần đã làm.
ROLE_MENU = {
    # Hợp Lô 7 (mock Chủ đủ quyền như BE: Gọi xác nhận, Chính sách AI, Báo cáo AI; Sổ nhập xuất) + Lô 9 (Hàng hoàn).
    "loc": (["Tổng quan", "Đơn & tiền", "Khách hàng", "Gọi xác nhận", "Giao hàng", "Mua hàng", "Nhà cung cấp", "Kho & lô", "Hàng hoàn", "Kiểm kê", "Sổ nhập xuất", "Danh mục & giá", "Báo cáo lãi lỗ", "Hoá đơn bán", "Hoá đơn mua & chi phí", "Nội dung", "Nhân sự", "Phân quyền", "Nhật ký hoạt động", "Chính sách AI", "Báo cáo AI"],
            ["Bán hàng", "Hàng hoá & kho", "Kế toán", "Website", "Quản trị"]),
    "ql1": (["Tổng quan", "Đơn & tiền", "Khách hàng", "Gọi xác nhận", "Giao hàng", "Mua hàng", "Nhà cung cấp", "Kho & lô", "Hàng hoàn", "Kiểm kê", "Sổ nhập xuất", "Danh mục & giá", "Hoá đơn bán", "Hoá đơn mua & chi phí", "Nội dung", "Nhật ký hoạt động"],
            ["Bán hàng", "Hàng hoá & kho", "Kế toán", "Website", "Quản trị"]),
    "kho1": (["Tổng quan", "Đơn & tiền", "Giao hàng", "Việc giao của tôi", "Mua hàng", "Nhà cung cấp", "Kho & lô", "Hàng hoàn", "Kiểm kê", "Sổ nhập xuất", "Danh mục & giá", "Hoá đơn bán"],
             ["Bán hàng", "Hàng hoá & kho", "Kế toán"]),
    "giao1": (["Việc giao của tôi", "Hàng hoàn"], ["Bán hàng", "Hàng hoá & kho"]),
}


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")


def nav_labels(page):
    return [t.split("\n")[-1].strip() for t in page.locator(".nav a").all_inner_texts()]


def is_subsequence(sub, full):
    it = iter(full)
    return all(x in it for x in sub)


def fonts_ready(page):
    page.wait_for_function("() => document.fonts.status === 'loaded'")


def fulfil_404(page, path_glob):
    body = OUT_404.read_text(encoding="utf-8")
    page.route(path_glob, lambda route: route.fulfill(status=404, content_type="text/html; charset=utf-8", body=body))


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []

    # ---------- Menu 4 vai (desktop 1280) ----------
    for user, (labels_expected, sections_expected) in ROLE_MENU.items():
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page = ctx.new_page()
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        login(page, user)
        labels = nav_labels(page)
        heads = [t.strip() for t in page.locator(".nav-h").all_inner_texts()]
        ok(f"ED-01 menu {user} đúng danh sách", labels == labels_expected, str(labels))
        ok(f"ED-01 menu {user} theo thứ tự UI-RULES §2.1", is_subsequence(labels, FULL_ORDER), str(labels))
        ok(f"ED-01 menu {user} chỉ hiện nhóm có mục", heads == sections_expected and is_subsequence(heads, SECTIONS), str(heads))
        ok(f"ED-01 {user} không còn cột phải", page.locator("#rail-right").count() == 0)
        ok(f"ED-01 {user} không có nút đổi sáng/tối", page.locator(".theme-toggle, [aria-label*='giao diện' i]").count() == 0)
        # mục đang mở được đánh dấu
        ok(f"ED-01 {user} đúng 1 mục aria-current", page.locator(".nav a[aria-current=page]").count() == 1)
        if user == "loc":
            fonts_ready(page)
            page.screenshot(path=f"{SHOTS}/ed-lo1-desktop-1280-chu.png")
        ctx.close()

    # ---------- Thu gọn menu, nhớ sau khi tải lại; menu avatar; 404; ⌘K ----------
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.wait_for_url("**/overview/")
    rail = page.locator("#rail-left")
    w_open = rail.bounding_box()["width"]
    ok("ED-01 menu mở rộng 240px", abs(w_open - 240) <= 1, str(w_open))
    page.get_by_test_id("sidebar-toggle").click()
    expect(page.locator("#rail-left.collapsed")).to_have_count(1)
    expect(rail).to_have_css("width", "60px")
    ok("ED-01 thu gọn còn 60px", abs(rail.bounding_box()["width"] - 60) <= 1)
    ok("ED-01 lưu 'collapsed' vào localStorage", page.evaluate("() => localStorage.getItem('cave_ui_sidebar')") == "collapsed")
    first_link = page.locator(".nav a").first
    ok("ED-01 thu gọn: icon còn tooltip/nhãn", bool(first_link.get_attribute("title")) and bool(first_link.get_attribute("aria-label")))
    page.screenshot(path=f"{SHOTS}/ed-lo1-desktop-1280-collapsed.png")
    page.reload()
    page.wait_for_selector(".nav a", state="attached")
    expect(page.locator("#rail-left.collapsed")).to_have_count(1)
    ok("ED-01 thu gọn còn nguyên sau khi tải lại", abs(page.locator("#rail-left").bounding_box()["width"] - 60) <= 1)
    page.get_by_test_id("sidebar-toggle").click()
    expect(page.locator("#rail-left.collapsed")).to_have_count(0)
    ok("ED-01 mở rộng lại ghi 'open'", page.evaluate("() => localStorage.getItem('cave_ui_sidebar')") == "open")

    # Menu avatar: đúng 3 mục, không "Làm mới", không đăng xuất rời
    ok("ED-01 chưa mở avatar: không có chữ 'Làm mới'", page.get_by_text("Làm mới").count() == 0)
    ok("ED-01 đăng xuất không nằm rời ngoài menu avatar", page.get_by_role("button", name="Đăng xuất").count() == 0)
    page.locator(".avatar-btn").click()
    items = [t.split("\n")[-1].strip() for t in page.locator("[role=menuitem]").all_inner_texts()]
    ok("ED-01 menu avatar đúng 3 mục", items == ["Tài khoản của tôi", "AI của tôi", "Đăng xuất"], str(items))
    ok("ED-01 menu avatar không có 'Làm mới'", page.get_by_text("Làm mới").count() == 0)
    page.screenshot(path=f"{SHOTS}/ed-lo1-desktop-1280-avatar.png")
    page.keyboard.press("Escape")
    expect(page.locator("[role=menu]")).to_have_count(0)
    ok("ED-01 Esc đóng menu avatar và trả focus", page.evaluate("() => document.activeElement && document.activeElement.classList.contains('avatar-btn')"))

    # ⌘K chỉ nhảy tới màn trong menu
    page.keyboard.press("Control+k")
    dialog = page.get_by_role("dialog", name="Tìm màn hình")
    expect(dialog).to_be_visible()
    page.get_by_role("combobox", name="Tìm màn hình").fill("kiem ke")
    options = [t.strip() for t in page.locator(".cmd").get_by_role("option").all_inner_texts()]
    ok("ED-01 ⌘K bỏ dấu vẫn tìm ra 'Kiểm kê'", any("Kiểm kê" in o for o in options), str(options))
    page.keyboard.press("Enter")
    page.wait_for_url("**/stocktake/")
    ok("ED-01 ⌘K Enter nhảy tới màn", "/stocktake" in page.url, page.url)
    ok("ED-01 ⌘K đóng sau khi nhảy", page.get_by_role("dialog", name="Tìm màn hình").count() == 0)
    page.keyboard.press("Control+k")
    page.get_by_role("combobox", name="Tìm màn hình").fill("zzzzzz")
    ok("ED-01 ⌘K không khớp: có thông báo, không có mục", page.locator(".cmd").get_by_role("option").count() == 0 and page.locator(".cmd").inner_text().strip() != "")
    page.keyboard.press("Escape")

    # 404 trong khung
    fulfil_404(page, "**/khong-co-man-nay/**")
    page.goto(BASE + "/khong-co-man-nay/")
    page.wait_for_selector(".page-state")
    expect(page.get_by_text("Không tìm thấy trang này")).to_be_visible()
    ok("ED-03 404 nằm trong khung: có menu trái", page.locator("#rail-left .nav a").count() > 0)
    ok("ED-03 404 có nút về Tổng quan", page.get_by_role("link", name="Về Tổng quan").count() == 1)
    page.screenshot(path=f"{SHOTS}/ed-lo1-desktop-1280-404.png")
    page.get_by_role("link", name="Về Tổng quan").click()
    page.wait_for_url("**/overview/")

    # Đăng xuất qua menu avatar
    page.locator(".avatar-btn").click()
    page.get_by_role("menuitem", name="Đăng xuất").click()
    page.wait_for_url("**/login/**")
    ok("ED-01 đăng xuất từ menu avatar về trang đăng nhập", "/login" in page.url, page.url)
    ctx.close()

    # ---------- Ngoài đường thuận: giá trị rác trong localStorage ----------
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    for junk in ["<script>alert(1)</script>", "", "COLLAPSED", "{\"a\":1}", "x" * 5000]:
        page.evaluate("(v) => localStorage.setItem('cave_ui_sidebar', v)", junk)
        page.reload()
        page.wait_for_selector(".nav a", state="attached")
        ok(f"ED-01 localStorage rác ({junk[:12]!r}) -> menu mở, không vỡ",
           page.locator("#rail-left.collapsed").count() == 0 and abs(page.locator("#rail-left").bounding_box()["width"] - 240) <= 1)
    # Mất mạng: dải báo hiện, trở lại thì tắt
    ctx.set_offline(True)
    page.evaluate("() => window.dispatchEvent(new Event('offline'))")
    expect(page.locator(".offline-banner")).to_be_visible()
    ok("ED-03 mất mạng: có dải báo", "Mất kết nối" in page.locator(".offline-banner").inner_text())
    ctx.set_offline(False)
    page.evaluate("() => window.dispatchEvent(new Event('online'))")
    expect(page.locator(".offline-banner")).to_have_count(0)
    ok("ED-03 có mạng lại: dải báo tắt", True)
    # Bất biến 9: localStorage chỉ có khoá kỹ thuật (token, trạng thái menu, nháp), không có tên/SĐT/địa chỉ
    page.evaluate("() => localStorage.removeItem('cave_ui_sidebar')")
    keys = page.evaluate("() => Object.keys(localStorage)")
    # cave_erp_last_user = mã số người dùng (không phải tên); cave_erp_mock_users chỉ có ở bản MOCK (dữ liệu giả).
    # cave_erp_signed_in_at = mốc giờ đăng nhập (Lô 15, ED-06): chỉ một chuỗi thời gian, không có dữ liệu cá nhân.
    allowed = ("cave_erp_token", "cave_ui_sidebar", "cave_erp_last_user", "cave_erp_mock_users", "cave_erp_signed_in_at")
    ok("Bất biến 9: localStorage chỉ có khoá kỹ thuật", all(k in allowed or k.startswith("cave_erp_draft:") for k in keys), str(keys))
    ctx.close()

    # ---------- Mobile 360 ----------
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, device_scale_factor=2, is_mobile=True, has_touch=True, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "kho1")
    page.wait_for_url("**/overview/")
    fonts_ready(page)
    ok("T4 360: menu đáy còn", page.locator(".bottom-nav").is_visible())
    ok("T4 360: không cuộn ngang", page.evaluate("() => document.documentElement.scrollWidth") <= 360)
    ok("T4 360: nút thu gọn không hiện (chỉ có ngăn kéo)", not page.get_by_test_id("sidebar-toggle").is_visible())
    page.get_by_role("button", name="Mở menu").click()
    expect(page.locator("#rail-left.open")).to_be_visible()
    ok("T4 360: ngăn kéo luôn đủ chữ (không thu gọn)", page.locator("#rail-left .nav-label").first.is_visible())
    page.screenshot(path=f"{SHOTS}/ed-lo1-mobile-360-drawer.png")
    page.keyboard.press("Escape")
    expect(page.locator("#rail-left.open")).to_have_count(0)
    page.locator(".avatar-btn").click()
    menu = page.locator(".avatar-menu")
    expect(menu).to_be_visible()
    box = menu.bounding_box()
    ok("ED-01 360: menu avatar nằm trọn trong màn hình", box["x"] >= 0 and box["x"] + box["width"] <= 360, str(box))
    page.screenshot(path=f"{SHOTS}/ed-lo1-mobile-360-avatar.png")
    ctx.close()
    browser.close()

relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "401" not in e
            and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]
ok("Không lỗi console (trừ font/401/offline cố ý)", not relevant, str(relevant[:5]))
for n, c, e in results:
    print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + e))
print(f"{sum(1 for _, c, _ in results if c)}/{len(results)} PASS")
raise SystemExit(0 if all(c for _, c, _ in results) else 1)
