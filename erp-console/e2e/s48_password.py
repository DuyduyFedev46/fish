# E2E S48 — Tài khoản & mật khẩu "làm đàng hoàng": chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s48_password.py      # tắt server sau khi xong
#
# Mock theo contract S48 (story 02-stories.md): /api/auth/me/ có `must_change_password`; còn mật khẩu tạm thì mọi API
# nghiệp vụ → 403 `AUTH_MUST_CHANGE_PASSWORD` (trừ me, change-password, logout). Không ngủ: chờ đúng điều kiện.
# Câu mong đợi đọc từ bảng của app qua window.__caveMock (không gõ lại chuỗi ở đây).

import os

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []
expect.set_options(timeout=10_000)


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()


def logout(page):
    page.locator(".who .iconbtn").click()
    page.wait_for_url("**/login/")


def log(page):
    return page.evaluate("() => window.__caveMock.log.slice()")


def clear_log(page):
    page.evaluate("() => window.__caveMock.clearLog()")


def msg(page, key):
    return page.evaluate("k => window.__caveMock.msg[k]", key)


def be(page, key):
    return page.evaluate("k => window.__caveMock.beDetail(k)", key)


def mock_user(page, username):
    return page.evaluate(
        "u => (JSON.parse(localStorage.getItem('cave_erp_mock_users') || '[]').find(x => x.username === u) || null)", username)


def fill_pw(scope, label, value, again=None):
    scope.get_by_label(label, exact=True).fill(value)
    scope.get_by_label("Nhập lại " + label[0].lower() + label[1:], exact=True).fill(value if again is None else again)


def list_idle(page):
    expect(page.locator("ul.staff-list > li").first).to_be_visible()
    expect(page.locator("section[aria-busy=true]")).to_have_count(0)


SMALL_TARGETS = """() => [...document.querySelectorAll('button, a, input')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    if (e.type === 'checkbox') return false;
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360
      && (r.height < 44 || (r.width < 44 && e.tagName !== 'INPUT'));
  }).map(e => (e.innerText || e.id || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    # Về seed người dùng mock (lần chạy trước có thể đã đổi mật khẩu)
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.evaluate("() => { window.__caveMock.resetUsers(); localStorage.removeItem('cave_erp_mock_revoked'); }")

    # ---- S48-AC4: ô mật khẩu ở màn đăng nhập có nút mắt ≥ 44px ----
    pw = page.get_by_label("Mật khẩu")
    pw.fill("demo1234")
    eye = page.get_by_role("button", name=msg(page, "pwShow"))
    box = eye.bounding_box()
    ok("S48-AC4 đăng nhập: ô mật khẩu mặc định ẩn", pw.get_attribute("type") == "password")
    eye.click()
    ok("S48-AC4 đăng nhập: bấm mắt → hiện chữ", pw.get_attribute("type") == "text"
       and page.get_by_role("button", name=msg(page, "pwHide")).get_attribute("aria-pressed") == "true")
    ok("S48-AC4 nút mắt ≥ 44×44", box["width"] >= 44 and box["height"] >= 44, str(box))
    page.get_by_role("button", name=msg(page, "pwHide")).click()
    ok("S48-AC4 bấm lần nữa → ẩn lại", pw.get_attribute("type") == "password")
    ok("S48-AC4 đăng nhập KHÔNG có ô Nhập lại, không có gợi ý quy tắc",
       page.get_by_label("Nhập lại", exact=False).count() == 0 and page.locator(".pw-rules").count() == 0)

    # ---- S48-AC1: kho5 còn mật khẩu tạm → chỉ màn "Đặt mật khẩu mới" ----
    login(page, "kho5")
    page.wait_for_url("**/set-password/")
    ok("S48-AC1 me.must_change_password → vào /set-password/", True)
    expect(page.get_by_role("heading", name=msg(page, "mustChangeTitle"))).to_be_visible()
    ok("S48-AC1 không có menu nghiệp vụ", page.locator(".nav").count() == 0)
    clear_log(page)
    page.goto(BASE + "/overview/")
    page.wait_for_url("**/set-password/")
    ok("S48-AC1 gõ /overview/ → bị đưa về màn đặt mật khẩu, không gọi API nghiệp vụ",
       all(x.startswith("GET /api/auth/me/") for x in log(page)), str(log(page)))
    page.goto(BASE + "/inventory/")
    page.wait_for_url("**/set-password/")
    ok("S48-AC1 gõ /inventory/ → bị đưa về", True)

    # ---- S48-AC4: gợi ý quy tắc hiện TRƯỚC khi gửi, cập nhật khi gõ ----
    rules = page.locator(".pw-rules li")
    ok("S48-AC4 có gợi ý quy tắc ngay khi mở (4 dòng)", rules.count() == 4, str(rules.all_inner_texts()))
    page.get_by_label("Mật khẩu mới", exact=True).fill("1234")
    ok("S48-AC4 '1234': chưa đạt 'ít nhất 8 ký tự' và 'không toàn số'",
       rules.nth(0).get_attribute("class") != "ok" and rules.nth(1).get_attribute("class") != "ok",
       str(page.locator(".pw-rules li.ok").all_inner_texts()))
    page.get_by_label("Mật khẩu mới", exact=True).fill("Kho5abcd2026")
    ok("S48-AC4 'Kho5abcd2026' (chứa tên đăng nhập): gợi ý 'không giống tên đăng nhập' CHƯA đạt trước khi gửi",
       rules.nth(2).get_attribute("class") != "ok")
    page.get_by_label("Mật khẩu mới", exact=True).fill("Bienxanh2026")
    ok("S48-AC4 'Bienxanh2026': đạt độ dài + không toàn số + không giống tên",
       rules.nth(2).get_attribute("class") == "ok" and rules.nth(0).get_attribute("class") == "ok" and rules.nth(1).get_attribute("class") == "ok",
       str(page.locator(".pw-rules li.ok").all_inner_texts()))
    page.screenshot(path=f"{SHOTS}/s48-desktop-1280-set-password.png")

    # ---- S48-AC3: Nhập lại khác → báo, không gọi API ----
    page.get_by_label("Mật khẩu hiện tại").fill("demo1234")
    fill_pw(page, "Mật khẩu mới", "Bienxanh2026", again="Bienxanh2027")
    clear_log(page)
    page.get_by_role("button", name="Lưu mật khẩu mới").click()
    expect(page.locator(".field-err span")).to_have_text(msg(page, "passwordMismatch"))
    ok("S48-AC3 'Hai mật khẩu không khớp', không gọi API", log(page) == [], str(log(page)))

    # hai ô mới + nhập lại hiện/ẩn cùng nhau
    page.get_by_role("button", name=msg(page, "pwShow")).nth(1).click()
    ok("S48-AC4 bấm mắt ô mới → ô mới và ô nhập lại cùng hiện",
       page.get_by_label("Mật khẩu mới", exact=True).get_attribute("type") == "text"
       and page.get_by_label("Nhập lại mật khẩu mới", exact=True).get_attribute("type") == "text"
       and page.get_by_label("Mật khẩu hiện tại").get_attribute("type") == "password")

    # sai mật khẩu hiện tại → lỗi BE nguyên văn
    page.get_by_label("Mật khẩu hiện tại").fill("sai-mat-khau")
    fill_pw(page, "Mật khẩu mới", "Bienxanh2026")
    page.get_by_role("button", name="Lưu mật khẩu mới").click()
    expect(page.locator(".alert-box.err span")).to_have_text(be(page, "AUTH_OLD_PASSWORD"))
    ok("Sai mật khẩu hiện tại → AUTH_OLD_PASSWORD nguyên văn, vẫn ở màn đặt mật khẩu", "/set-password" in page.url)

    # ---- S48-AC2: đổi xong → vào home ----
    page.get_by_label("Mật khẩu hiện tại").fill("demo1234")
    clear_log(page)
    page.get_by_role("button", name="Lưu mật khẩu mới").click()
    page.wait_for_url("**/overview/")
    ok("S48-AC2 đổi xong → vào home (Tổng quan) bình thường",
       "POST /api/auth/change-password/" in log(page) and page.locator(".nav").count() == 1, str(log(page)))
    ok("S48-AC2 cờ must_change_password đã tắt", mock_user(page, "kho5")["must_change_password"] is False)
    # Code review trước deploy 1: xác nhận thành công phải THẤY được (trước đây màn chuyển đi trước khi kịp hiện).
    expect(page.locator(".pw-done-notice span")).to_have_text(msg(page, "mustChangeDone"))
    ok("Review #2: sau khi đặt mật khẩu mới, màn home hiện xác nhận 'Đã đặt mật khẩu mới'", True)
    page.locator(".pw-done-notice").get_by_role("button", name="Đóng thông báo").click()
    expect(page.locator(".pw-done-notice")).to_have_count(0)
    ok("Review #2: đóng được thông báo", True)
    logout(page)

    login(page, "kho5", "Bienxanh2026")
    page.wait_for_url("**/overview/")
    expect(page.locator(".tile[data-kpi=revenue]")).to_be_visible()
    ok("Review #2: đăng nhập lại → không còn thông báo đặt mật khẩu", page.locator(".pw-done-notice").count() == 0)
    logout(page)

    # ---- S48-AC6: tự đổi không bật lại cờ ----
    login(page, "kho5", "Bienxanh2026")
    page.wait_for_url("**/overview/")
    ok("S48-AC6 đăng nhập lại bằng mật khẩu riêng → thẳng Tổng quan", True)

    # ---- S48-AC1 (403 AUTH_MUST_CHANGE_PASSWORD giữa phiên): cờ bật lúc đang mở console → bị đưa về màn đặt MK ----
    expect(page.locator(".tile[data-kpi=revenue]")).to_be_visible()
    page.evaluate("() => window.__caveMock.patchUser('kho5', {must_change_password: true})")
    page.get_by_role("button", name="Làm mới").click()
    page.wait_for_url("**/set-password/")
    ok("S48-AC1 API trả 403 AUTH_MUST_CHANGE_PASSWORD → console chuyển sang màn đặt mật khẩu", True)
    ok("403 AUTH_MUST_CHANGE_PASSWORD không báo 'Quyền của bạn vừa thay đổi'", page.locator(".perm-notice").count() == 0)
    page.get_by_role("button", name="Đăng xuất").click()
    page.wait_for_url("**/login/")
    ok("Màn đặt mật khẩu có nút Đăng xuất", True)
    page.evaluate("() => window.__caveMock.patchUser('kho5', {must_change_password: false})")

    # ---- Chủ: tạo tài khoản + đặt lại mật khẩu (ô Nhập lại, mắt, không gọi API khi lệch) ----
    login(page, "loc")
    page.wait_for_url("**/overview/")
    page.goto(BASE + "/staff/")
    list_idle(page)
    page.get_by_role("button", name="Thêm nhân viên").click()
    dlg = page.get_by_role("dialog")
    expect(dlg.get_by_label("Tên đăng nhập")).to_be_focused()
    ok("S48-AC4 form tạo: có gợi ý quy tắc trước khi gửi", dlg.locator(".pw-rules li").count() == 4)
    dlg.get_by_label("Tên đăng nhập").fill("giao6")
    dlg.get_by_label("Tên hiển thị").fill("Anh Bảy")
    dlg.get_by_label("Số điện thoại").fill("0909555666")
    dlg.get_by_text("Nhân viên giao", exact=True).click()
    fill_pw(dlg, "Mật khẩu tạm", "Songbien2026", again="Songbien2025")
    clear_log(page)
    dlg.get_by_role("button", name="Tạo tài khoản").click()
    expect(dlg.locator(".field-err span")).to_have_text(msg(page, "passwordMismatch"))
    ok("S48-AC3 tạo tài khoản: Nhập lại khác → báo, không POST", log(page) == [], str(log(page)))
    ok("S48-AC4 form tạo: 2 nút mắt", dlg.get_by_role("button", name=msg(page, "pwShow")).count() == 2)
    page.wait_for_function("""() => { const d = JSON.parse(localStorage.getItem('cave_erp_draft:staff:create') || 'null');
        return !!d && d.data.username === 'giao6'; }""")
    draft_raw = page.evaluate("() => localStorage.getItem('cave_erp_draft:staff:create')")
    ok("S48-AC5 nháp có tên đăng nhập, KHÔNG có mật khẩu", "giao6" in draft_raw and "Songbien" not in draft_raw and "password" not in draft_raw, draft_raw)
    fill_pw(dlg, "Mật khẩu tạm", "Songbien2026")
    clear_log(page)
    dlg.get_by_role("button", name="Tạo tài khoản").click()
    expect(dlg.locator(".cred-username")).to_have_text("giao6")
    expect(dlg.locator(".cred-password")).to_have_text("Songbien2026")
    ok("Khớp → POST /api/staff/", "POST /api/staff/" in log(page), str(log(page)))
    ok("S48-AC1 tài khoản mới: must_change_password = true", mock_user(page, "giao6")["must_change_password"] is True)
    dlg.get_by_role("button", name="Xong").click()

    # đặt lại mật khẩu kho5 → cờ bật lại
    list_idle(page)
    page.locator("ul.staff-list > li").filter(has=page.locator("small", has_text="kho5")).locator(".staff-open").click()
    dlg = page.get_by_role("dialog")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    ok("S48-AC4 đặt lại: có ô Nhập lại + gợi ý quy tắc",
       dlg.get_by_label("Nhập lại mật khẩu mới", exact=True).count() == 1 and dlg.locator(".pw-rules").count() == 1)
    fill_pw(dlg, "Mật khẩu mới", "Songbien2026", again="khac")
    clear_log(page)
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    expect(dlg.locator(".field-err span")).to_have_text(msg(page, "passwordMismatch"))
    ok("S48-AC3 đặt lại: lệch → không gọi API", log(page) == [], str(log(page)))
    fill_pw(dlg, "Mật khẩu mới", "Songbien2026")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    expect(dlg.locator(".cred-password")).to_have_text("Songbien2026")
    ok("S48-AC6 Chủ đặt lại → cờ bật lại", mock_user(page, "kho5")["must_change_password"] is True)
    dlg.get_by_role("button", name="Xong").click()
    logout(page)

    # giao6 đăng nhập bằng mật khẩu tạm → màn đặt mật khẩu → đổi → Việc giao của tôi
    login(page, "giao6", "Songbien2026")
    page.wait_for_url("**/set-password/")
    page.get_by_label("Mật khẩu hiện tại").fill("Songbien2026")
    fill_pw(page, "Mật khẩu mới", "Mayxanh2026")
    page.get_by_role("button", name="Lưu mật khẩu mới").click()
    page.wait_for_url("**/my-deliveries/")
    ok("S48-AC1/AC2 tài khoản Chủ vừa tạo: đặt mật khẩu mới rồi vào home của vai (Việc giao)", True)
    expect(page.locator(".pw-done-notice span")).to_have_text(msg(page, "mustChangeDone"))
    ok("Review #2: giao6 vào Việc giao cũng thấy xác nhận 'Đã đặt mật khẩu mới'", True)
    logout(page)

    # kho5 sau khi bị đặt lại → lại bị ép
    login(page, "kho5", "Songbien2026")
    page.wait_for_url("**/set-password/")
    ok("S48-AC6 kho5 sau khi Chủ đặt lại → lại vào màn đặt mật khẩu", True)
    page.get_by_role("button", name="Đăng xuất").click()
    page.wait_for_url("**/login/")

    # superuser không bị ép
    page.evaluate("() => window.__caveMock.patchUser('admin', {must_change_password: true})")
    login(page, "admin")
    page.wait_for_url("**/no-role/")
    ok("S48-AC6 superuser admin không bị ép (me.must_change_password=false)", True)
    page.get_by_role("button", name="Đăng xuất").click()
    page.wait_for_url("**/login/")
    ctx.close()

    # ======================= Mobile 360×640 =======================
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, device_scale_factor=2, is_mobile=True, has_touch=True,
                              reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Mật khẩu").fill("demo1234")
    ok("360 đăng nhập: không cuộn ngang, nút ≥44px",
       page.evaluate("() => document.documentElement.scrollWidth") <= 360 and not page.evaluate(SMALL_TARGETS), str(page.evaluate(SMALL_TARGETS)))
    page.screenshot(path=f"{SHOTS}/s48-mobile-360-login.png")
    page.get_by_label("Tài khoản").fill("kho5")  # context mới = kho mock mới (seed): mật khẩu tạm demo1234
    page.get_by_label("Mật khẩu").fill("demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/set-password/")
    expect(page.get_by_label("Mật khẩu hiện tại")).to_be_visible()
    page.get_by_label("Mật khẩu mới", exact=True).fill("Kho5")
    page.get_by_label("Nhập lại mật khẩu mới", exact=True).fill("Kho")
    page.get_by_label("Mật khẩu hiện tại").fill("demo1234")
    page.get_by_role("button", name="Lưu mật khẩu mới").click()
    expect(page.locator(".field-err")).to_be_visible()
    sw = page.evaluate("() => document.documentElement.scrollWidth")
    small = page.evaluate(SMALL_TARGETS)
    ok("360 màn đặt mật khẩu mới: không cuộn ngang, mọi nút/ô ≥44px", sw <= 360 and not small, f"{sw} {small}")
    page.screenshot(path=f"{SHOTS}/s48-mobile-360-set-password.png", full_page=True)
    ctx.close()
    browser.close()

relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "401" not in e and "403" not in e
            and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]
ok("Không lỗi console", not relevant, str(relevant[:5]))
passed = sum(1 for _, c, _ in results if c)
for n, c, e in results:
    print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + e))
print(f"{passed}/{len(results)} PASS")
