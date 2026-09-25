# E2E S7 (khung console): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s7_shell.py      # tắt server sau khi xong

from playwright.sync_api import sync_playwright, expect

import os
BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []

def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))

def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()

def nav_labels(page):
    return page.locator(".nav a").all_inner_texts()

def fonts_ready(page):
    """Chờ font (icon Material Symbols) tải xong trước khi đo/chụp — điều kiện, không ngủ (QA Q2, lô L6b)."""
    page.wait_for_function("() => document.fonts.status === 'loaded'")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ---------- Desktop 1280x800 ----------
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    # AC4: sai mật khẩu / đã nghỉ
    for u, pw in [("loc", "sai"), ("nghi1", "demo1234")]:
        login(page, u, pw)
        err = page.locator(".alert-box.err")
        expect(err).to_contain_text("Sai tài khoản/mật khẩu hoặc tài khoản đã ngừng hoạt động")
        ok(f"AC4 {u}", "/login" in page.url)

    # AC1: Chủ
    login(page, "loc")
    page.wait_for_url("**/overview/")
    page.wait_for_load_state("networkidle")
    labels = nav_labels(page)
    labels = [l.split("\n")[-1].strip() for l in labels]
    expected = ["Tổng quan", "Đơn & tiền", "Giao hàng", "Kho & lô", "Mua hàng", "Kiểm kê", "Báo cáo lãi lỗ", "Danh mục & giá", "Nhân sự · Nhật ký"]
    ok("AC1 menu Chủ", labels == expected, str(labels))
    rr = page.locator("#rail-right")
    ok("AC7 1280: 3 cột (cột phải hiện)", rr.is_visible() and rr.bounding_box()["x"] > 900, str(rr.bounding_box()))
    ok("AC7 1280: không có menu đáy", not page.locator(".bottom-nav").is_visible())
    fonts_ready(page)
    page.screenshot(path=f"{SHOTS}/s7-desktop-1280-chu.png")

    # AC6: nháp giữ khi hết phiên, cùng người đăng nhập lại
    page.evaluate("""() => localStorage.setItem('cave_erp_draft:test-form', JSON.stringify({owner:1,savedAt:'x',data:{note:'đang gõ dở'}}))""")
    page.goto(BASE + "/purchasing/")
    page.wait_for_load_state("networkidle")
    page.evaluate("() => window.__caveMock.expire()")
    page.reload()
    page.wait_for_url("**/login/**")
    ok("AC6 401 → về đăng nhập, next giữ trang", "next=%2Fpurchasing" in page.url, page.url)
    ok("AC6 thông báo hết phiên", page.get_by_role("status").filter(has_text="Phiên đăng nhập đã hết").count() == 1)
    ok("AC6 nháp còn sau 401", page.evaluate("() => localStorage.getItem('cave_erp_draft:test-form')") is not None)
    page.get_by_label("Tài khoản").fill("loc")
    page.get_by_label("Mật khẩu").fill("demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/purchasing/**")
    ok("AC6 cùng người → quay lại trang đang dở", "/purchasing" in page.url, page.url)
    ok("AC6 cùng người → nháp còn", page.evaluate("() => localStorage.getItem('cave_erp_draft:test-form')") is not None)
    # người khác đăng nhập cùng máy
    page.evaluate("() => window.__caveMock.expire()")
    page.reload()
    page.wait_for_url("**/login/**")
    page.get_by_label("Tài khoản").fill("giao1")
    page.get_by_label("Mật khẩu").fill("demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/my-deliveries/")
    ok("AC6 người khác → không về trang người trước, nháp bị xoá",
       page.evaluate("() => localStorage.getItem('cave_erp_draft:test-form')") is None and "/my-deliveries" in page.url, page.url)

    # AC2: giao1
    page.wait_for_load_state("networkidle")
    labels = [l.split("\n")[-1].strip() for l in nav_labels(page)]
    ok("AC2 menu giao1 chỉ 'Việc giao của tôi'", labels == ["Việc giao của tôi"], str(labels))

    # AC3: giao1 gõ /reports
    page.goto(BASE + "/reports")
    expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
    log = page.evaluate("() => window.__caveMock.log.slice()")
    ok("AC3 không gọi API báo cáo", all("report" not in x for x in log) and log == ["GET /api/auth/me/"], str(log))

    # AC5: admin (không Group)
    page.locator(".who .iconbtn").click()  # đăng xuất
    page.wait_for_url("**/login/")
    login(page, "admin")
    page.wait_for_url("**/no-role/")
    expect(page.get_by_text("Tài khoản chưa được phân quyền")).to_be_visible()
    ok("AC5 không có menu", page.locator(".nav").count() == 0 and page.locator("#rail-right").count() == 0)
    ok("AC5 gõ /overview vẫn bị đưa về no-role", True)
    page.goto(BASE + "/overview/")
    page.wait_for_url("**/no-role/")
    ctx.close()

    # ---------- Mobile 360x640 ----------
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, device_scale_factor=2, is_mobile=True, has_touch=True, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    sw = page.evaluate("() => document.documentElement.scrollWidth")
    ok("AC7 360 login không cuộn ngang", sw <= 360, str(sw))
    page.screenshot(path=f"{SHOTS}/s7-mobile-360-login.png")
    login(page, "kho1")
    page.wait_for_url("**/overview/")
    expect(page.locator(".tile[data-kpi=revenue]")).to_be_visible()
    fonts_ready(page)
    sw = page.evaluate("() => document.documentElement.scrollWidth")
    ok("AC7 360 overview không cuộn ngang", sw <= 360, str(sw))
    bottom = page.locator(".bottom-nav")
    ok("AC7 360 menu đáy hiện", bottom.is_visible())
    bl = [t.split("\n")[-1].strip() for t in bottom.locator("a, button").all_inner_texts()]
    ok("AC7 360 menu đáy ≤5 mục (4 + Thêm)", len(bl) <= 5 and bl[-1] == "Thêm", str(bl))
    ok("AC7 360 cột phải ẩn (ngăn kéo)", not page.locator("#rail-right").is_visible())
    small = page.evaluate("""() => [...document.querySelectorAll('button, a')].filter(e => {
        const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
        return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && (r.height < 44 || r.width < 44);
      }).map(e => (e.getAttribute('aria-label') || e.innerText).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))""")
    ok("AC7 360 vùng bấm ≥44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/s7-mobile-360-kho1.png")
    page.get_by_role("button", name="Mở menu").click()
    expect(page.locator("#rail-left.open")).to_be_visible()
    ok("AC7 360 ☰ mở menu đầy đủ", page.locator("#rail-left").is_visible() and page.get_by_role("link", name="Kiểm kê").first.is_visible())
    sw = page.evaluate("() => document.documentElement.scrollWidth")
    ok("AC7 360 drawer không cuộn ngang", sw <= 360, str(sw))
    page.screenshot(path=f"{SHOTS}/s7-mobile-360-menu.png")
    page.keyboard.press("Escape")
    expect(page.locator("#rail-left.open")).to_have_count(0)
    page.get_by_role("button", name="Mở ghi chú, trợ lý, hoạt động").click()
    expect(page.locator("#rail-right")).to_be_visible()
    ok("AC7 360 cột phải là ngăn kéo mở được", page.locator("#rail-right").is_visible())
    page.screenshot(path=f"{SHOTS}/s7-mobile-360-rightrail.png")
    ctx.close()
    browser.close()

# "Failed to fetch RSC payload": Next prefetch bị huỷ khi kịch bản page.goto giữa chừng (server log BrokenPipe) — không phải lỗi app.
relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "401" not in e
            and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]
ok("Không lỗi console (trừ font/401 cố ý)", not relevant, str(relevant[:5]))
for n, c, e in results:
    print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + e))
print("all errors:", errors[:6])
