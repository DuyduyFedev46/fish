# E2E S41, S42 (Nhân viên) + S46, S47 (Tài khoản của tôi): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s41_s47_staff.py      # tắt server sau khi xong
#
# "Máy khác" của cùng một người: mock lưu người dùng trong localStorage của trình duyệt, nên kịch bản giả lập
# máy thứ hai bằng cách giữ lại token cũ rồi gắn lại vào máy (token cũ phải bị 401 sau khi Chủ cho nghỉ /
# đặt lại mật khẩu / người đó tự đổi mật khẩu hoặc đăng xuất).
#
# Ổn định (QA Q2, lô L6b): KHÔNG ngủ (wait_for_timeout) — luôn chờ đúng điều kiện: URL, phần tử, nháp đã ghi vào
# localStorage, danh sách hết `aria-busy` trước khi bấm một dòng. Context bật reduced_motion → không có hiệu ứng chuyển.
# S48 (mật khẩu tạm phải đổi lần đầu) kiểm riêng ở s48_password.py; ở đây chỉ đi qua màn đó khi luồng cần.

import os
import re

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []
expect.set_options(timeout=10_000)  # máy dev chậm: mock trễ 250ms/request + tải lại danh sách


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()


def token(page):
    return page.evaluate("() => localStorage.getItem('cave_erp_token')")


def drop_token(page):
    """Rời máy mà KHÔNG đăng xuất (token vẫn sống ở server)."""
    page.evaluate("() => localStorage.removeItem('cave_erp_token')")


def use_token(page, t, path="/overview/"):
    """Gắn lại token cũ ("máy khác") rồi mở trang. Mọi chỗ dùng đều mong token đã chết → chờ về /login/."""
    page.evaluate(f"() => localStorage.setItem('cave_erp_token', '{t}')")
    page.goto(BASE + path)
    try:
        page.wait_for_url("**/login/**", timeout=10_000)
    except Exception:
        pass  # không về đăng nhập → kiểm ở ok() sẽ báo FAIL


def list_idle(page):
    """Danh sách nhân viên không còn đang tải lại (tránh bấm vào dòng sắp bị vẽ lại — flake 'detached')."""
    expect(page.locator("ul.staff-list > li").first).to_be_visible()
    expect(page.locator("section[aria-busy=true]")).to_have_count(0)


def fill_pw(scope, label, value, again=None):
    """Ô mật khẩu + ô 'Nhập lại …' (S48). `again` khác None để thử lệch."""
    scope.get_by_label(label, exact=True).fill(value)
    scope.get_by_label("Nhập lại " + label[0].lower() + label[1:], exact=True).fill(value if again is None else again)


def log(page):
    return page.evaluate("() => window.__caveMock.log.slice()")


def clear_log(page):
    page.evaluate("() => window.__caveMock.clearLog()")


def nav_labels(page):
    return [t.split("\n")[-1].strip() for t in page.locator(".nav a").all_inner_texts()]


def staff_row(page, username):
    return page.locator("ul.staff-list > li").filter(
        has=page.locator("small", has_text=re.compile(rf"^{re.escape(username)}$"))
    )


def open_staff(page, username):
    list_idle(page)
    staff_row(page, username).locator(".staff-open").click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    return dlg


def goto_staff(page):
    page.goto(BASE + "/staff/")
    list_idle(page)


def alert_text(scope):
    return scope.locator(".alert-box.err span").inner_text().strip()


# ---- Câu mong đợi lấy từ bảng của app (mock mở qua window.__caveMock), KHÔNG gõ lại chuỗi ở đây ----
def be(page, key, **params):
    """`detail` BE (shared/lib/beErrors.mock.ts — chép từ contract BE)."""
    return page.evaluate("([k, p]) => window.__caveMock.beDetail(k, p)", [key, params])


def pw_problem(page, key):
    return page.evaluate("k => window.__caveMock.pwProblems[k]", key)


def msg(page, key):
    """Thông điệp FE (shared/lib/messages.ts)."""
    return page.evaluate("k => window.__caveMock.msg[k]", key)


def smsg(page, key, *args):
    """Thông báo màn Nhân viên (features/staff/messages.ts)."""
    return page.evaluate("([k, a]) => { const v = window.__caveMock.staffMsg[k]; return typeof v === 'function' ? v(...a) : v; }", [key, list(args)])


SMALL_TARGETS = """() => [...document.querySelectorAll('button, a, input, label.check-row')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    if (e.classList.contains('sheet-scrim') || e.type === 'checkbox') return false;
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y < innerHeight
      && (r.height < 44 || (r.width < 44 && e.tagName !== 'INPUT'));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.id).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []

    # ======================= Desktop 1280×800 =======================
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    # Giữ token của giao1 và kho1 như thể họ đang đăng nhập ở máy khác.
    login(page, "giao1")
    page.wait_for_url("**/my-deliveries/")
    t_giao1 = token(page)
    drop_token(page)
    login(page, "kho1")
    page.wait_for_url("**/overview/")
    t_kho1 = token(page)
    drop_token(page)

    # ---- Chủ vào màn Nhân viên ----
    login(page, "loc")
    page.wait_for_url("**/overview/")
    page.wait_for_load_state("networkidle")
    ok("Menu Chủ có 'Nhân sự · Nhật ký'", "Nhân sự · Nhật ký" in nav_labels(page), str(nav_labels(page)))
    page.get_by_role("link", name="Nhân sự · Nhật ký").click()
    page.wait_for_url("**/staff/")
    expect(page.locator("ul.staff-list > li").first).to_be_visible()
    users = page.locator("ul.staff-list > li small").all_inner_texts()
    ok("Lọc 'Đang làm' mặc định: có giao1, kho1; không có nghi1", "giao1" in users and "kho1" in users and "nghi1" not in users, str(users))
    ok("Lọc 'Đang làm' gọi ?is_active=true", "GET /api/staff/?is_active=true" in log(page), str(log(page)[-3:]))
    ok("SĐT là link tel:", staff_row(page, "giao1").locator("a[href='tel:0909000333']").count() == 1)
    page.get_by_role("button", name="Đã nghỉ").click()
    expect(page.locator("ul.staff-list > li small").first).to_have_text("nghi1")
    ok("Lọc 'Đã nghỉ' chỉ có nghi1", page.locator("ul.staff-list > li small").all_inner_texts() == ["nghi1"])
    dlg = open_staff(page, "nghi1")
    btns = [b.strip() for b in dlg.locator(".staff-actions button").all_inner_texts()]
    ok("Người đã nghỉ: nút theo available_actions = Sửa hồ sơ, Cho làm lại", [b.split("\n")[-1] for b in btns] == ["Sửa hồ sơ", "Cho làm lại"], str(btns))
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Tất cả").click()
    expect(staff_row(page, "nghi1")).to_be_visible()
    ok("Lọc 'Tất cả' có cả người đang làm và đã nghỉ", staff_row(page, "loc").count() == 1)
    page.get_by_role("button", name="Đang làm").click()
    expect(staff_row(page, "loc")).to_be_visible()

    # Chính mình: chỉ "Sửa hồ sơ" + chỉ tới Tài khoản của tôi
    dlg = open_staff(page, "loc")
    btns = [b.split("\n")[-1].strip() for b in dlg.locator(".staff-actions button").all_inner_texts()]
    ok("Chính mình: chỉ có 'Sửa hồ sơ' (BR-PQ-17)", btns == ["Sửa hồ sơ"], str(btns))
    ok("Chính mình: chỉ đường đổi mật khẩu ở Tài khoản của tôi", dlg.get_by_role("link", name="Tài khoản của tôi").count() == 1)
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)

    # ---- S41-AC4: lỗi khi tạo — hiện nguyên văn BE ----
    page.get_by_role("button", name="Thêm nhân viên").click()
    dlg = page.get_by_role("dialog")
    expect(dlg.get_by_label("Tên đăng nhập")).to_be_focused()
    dlg.get_by_label("Tên đăng nhập").fill("GIAO1")
    dlg.get_by_label("Số điện thoại").fill("0909333444")
    fill_pw(dlg, "Mật khẩu tạm", "Songbien2026")
    dlg.get_by_role("button", name="Tạo tài khoản").click()
    expect(dlg.locator(".alert-box.err")).to_be_visible()
    ok("S41-AC4 username trùng → 'Tên đăng nhập đã tồn tại.'", alert_text(dlg) == be(page, "USERNAME_EXISTS"), alert_text(dlg))
    dlg.get_by_label("Tên đăng nhập").fill("giao4")
    dlg.get_by_label("Số điện thoại").fill("")
    dlg.get_by_role("button", name="Tạo tài khoản").click()
    expect(dlg.locator(".alert-box.err span")).to_have_text(be(page, "PHONE_REQUIRED"))
    ok("S41-AC4 thiếu SĐT → 'Số điện thoại là bắt buộc.'", True)
    dlg.get_by_label("Số điện thoại").fill("0909333444")
    fill_pw(dlg, "Mật khẩu tạm", "abc")
    dlg.get_by_role("button", name="Tạo tài khoản").click()
    expect(dlg.locator(".alert-box.err span")).to_contain_text(pw_problem(page, "PW_TOO_SHORT"))
    ok("S41-AC4 mật khẩu < 8 ký tự → thông điệp Django nguyên văn", alert_text(dlg).startswith(pw_problem(page, "PW_TOO_SHORT")), alert_text(dlg))
    ok("S41-AC4 lỗi → không tạo gì", "giao4" not in page.locator("ul.staff-list > li small").all_inner_texts())

    # ---- S7-AC6 trên form thật: hết phiên giữa chừng → đăng nhập lại cùng người → form mở lại đủ nội dung ----
    dlg.get_by_label("Tên hiển thị").fill("Anh Năm")
    dlg.get_by_text("Nhân viên giao", exact=True).click()
    fill_pw(dlg, "Mật khẩu tạm", "Songbien2026")
    # chờ nháp đã ghi (useDraft ghi sau 400ms) — điều kiện, không ngủ
    page.wait_for_function("""() => { const d = JSON.parse(localStorage.getItem('cave_erp_draft:staff:create') || 'null');
        return !!d && d.data.display_name === 'Anh Năm' && d.data.groups.includes('nv_giao'); }""")
    ok("S48-AC5 nháp KHÔNG chứa mật khẩu", "Songbien2026" not in page.evaluate(
        "() => Object.keys(localStorage).filter(k => k.startsWith('cave_erp_draft:')).map(k => localStorage.getItem(k)).join('')"))
    page.evaluate("() => window.__caveMock.expire()")
    dlg.get_by_role("button", name="Tạo tài khoản").click()
    page.wait_for_url("**/login/**")
    ok("S7-AC6 401 khi gửi form → về đăng nhập, next=/staff/", "next=%2Fstaff" in page.url, page.url)
    page.get_by_label("Tài khoản").fill("loc")
    page.get_by_label("Mật khẩu").fill("demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/staff/")
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    vals = {
        "u": dlg.get_by_label("Tên đăng nhập").input_value(),
        "n": dlg.get_by_label("Tên hiển thị").input_value(),
        "p": dlg.get_by_label("Số điện thoại").input_value(),
        "g": dlg.locator("input[name=groups]:checked").evaluate_all("els => els.map(e => e.value)"),
        "pw": dlg.get_by_label("Mật khẩu tạm", exact=True).input_value(),
    }
    ok("S7-AC6 form tạo tài khoản mở lại đủ nội dung (trừ mật khẩu)",
       vals == {"u": "giao4", "n": "Anh Năm", "p": "0909333444", "g": ["nv_giao"], "pw": ""}, str(vals))
    ok("S7-AC6 báo đã mở lại nháp, nhắc nhập lại mật khẩu", dlg.get_by_text(smsg(page, "draftRestored")).count() == 1)
    page.screenshot(path=f"{SHOTS}/s41-desktop-1280-create-restored.png")

    # ---- S41-AC1: tạo giao4 (Q2: nháp đã áp xong trước khi gõ → bấm là có POST) ----
    fill_pw(dlg, "Mật khẩu tạm", "Songbien2026")
    clear_log(page)
    dlg.get_by_role("button", name="Tạo tài khoản").click()
    expect(dlg.locator(".cred-username")).to_have_text("giao4")
    expect(dlg.locator(".cred-password")).to_have_text("Songbien2026")
    ok("S41-AC1 POST /api/staff/ → màn 'Đã tạo' hiện tên đăng nhập + mật khẩu tạm", "POST /api/staff/" in log(page), str(log(page)))
    dlg.get_by_role("button", name="Xong").click()
    expect(staff_row(page, "giao4")).to_be_visible()
    ok("S41-AC1 giao4 có trong danh sách, nhóm Nhân viên giao", "Nhân viên giao" in staff_row(page, "giao4").inner_text())
    ok("Tạo xong thì nháp bị xoá", page.evaluate("() => localStorage.getItem('cave_erp_draft:staff:create')") in (None,) or
       '"username":""' in (page.evaluate("() => localStorage.getItem('cave_erp_draft:staff:create')") or ""))

    # ---- S41-AC3: bỏ nv_giao của kho1 ----
    dlg = open_staff(page, "kho1")
    dlg.get_by_role("button", name="Đổi nhóm").click()
    dlg.get_by_text("Nhân viên giao", exact=True).click()
    clear_log(page)
    dlg.get_by_role("button", name="Lưu nhóm").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    ok("S41-AC3 PUT /api/staff/3/groups/", "PUT /api/staff/3/groups/" in log(page), str(log(page)))
    expect(page.locator(".alert-box.ok")).to_contain_text(smsg(page, "groupsChanged", "Anh Tâm (kho1)", "", "Nhân viên giao"))
    expect(staff_row(page, "kho1").locator(".group-tag")).to_have_text(["Nhân viên kho"])
    ok("S41-AC3 kho1 chỉ còn Nhân viên kho", staff_row(page, "kho1").locator(".group-tag").all_inner_texts() == ["Nhân viên kho"],
       str(staff_row(page, "kho1").locator(".group-tag").all_inner_texts()))

    # ---- Thêm nhóm Chủ → hỏi xác nhận; Quay lại thì không gọi API ----
    dlg = open_staff(page, "ql1")
    dlg.get_by_role("button", name="Đổi nhóm").click()
    dlg.get_by_text("Chủ", exact=True).click()
    clear_log(page)
    dlg.get_by_role("button", name="Lưu nhóm").click()
    expect(dlg.locator(".confirm-danger")).to_contain_text("thêm nhóm Chủ")
    ok("Thêm nhóm Chủ → hỏi xác nhận trước, chưa gọi API", not any(x.startswith("PUT") for x in log(page)), str(log(page)))
    page.screenshot(path=f"{SHOTS}/s41-desktop-1280-confirm-chu.png")
    dlg.get_by_role("button", name="Quay lại").click()
    dlg.get_by_role("button", name="Quay lại").click()
    page.keyboard.press("Escape")

    # ---- S42-AC4: BR-GH-08 nguyên văn ----
    dlg = open_staff(page, "giao2")
    dlg.get_by_role("button", name="Cho nghỉ").click()
    expect(dlg.locator(".confirm-danger")).to_contain_text("đăng xuất khỏi mọi máy")
    dlg.get_by_role("button", name="Cho nghỉ").click()
    expect(dlg.locator(".alert-box.err")).to_be_visible()
    ok("S42-AC4 BR-GH-08 hiện nguyên văn",
       alert_text(dlg) == be(page, "DELIVERING_LEFT", count=2, notes="GH-INV-DH01-A1B2C, GH-INV-DH02-K7M3Q"), alert_text(dlg))
    dlg.get_by_role("button", name="Thôi").click()
    page.keyboard.press("Escape")
    ok("S42-AC4 giao2 vẫn đang làm", staff_row(page, "giao2").count() == 1)

    # ---- S42-AC1: cho giao1 nghỉ (có xác nhận) ----
    dlg = open_staff(page, "giao1")
    dlg.get_by_role("button", name="Cho nghỉ").click()
    ok("S42 cho nghỉ có bước xác nhận", dlg.get_by_role("button", name="Thôi").is_visible())
    page.screenshot(path=f"{SHOTS}/s42-desktop-1280-confirm-deactivate.png")
    dlg.get_by_role("button", name="Cho nghỉ").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(page.locator(".alert-box.ok")).to_contain_text(smsg(page, "deactivated", "Anh Phúc (giao1)"))
    expect(staff_row(page, "giao1")).to_have_count(0)
    ok("S42-AC1 giao1 biến khỏi 'Đang làm'", staff_row(page, "giao1").count() == 0)
    page.get_by_role("button", name="Đã nghỉ").click()
    expect(staff_row(page, "giao1")).to_be_visible()
    ok("S42-AC1 giao1 ở 'Đã nghỉ'", staff_row(page, "giao1").count() == 1)
    page.get_by_role("button", name="Đang làm").click()
    expect(staff_row(page, "loc")).to_be_visible()

    # ---- S42-AC3: đặt lại mật khẩu kho1 ----
    dlg = open_staff(page, "kho1")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    fill_pw(dlg, "Mật khẩu mới", "abc")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    expect(dlg.locator(".alert-box.err span")).to_contain_text(pw_problem(page, "PW_TOO_SHORT"))
    ok("S42 mật khẩu yếu → lỗi nguyên văn", True)
    dlg.get_by_role("button", name="Tạo ngẫu nhiên").click()
    gen = dlg.get_by_label("Mật khẩu mới", exact=True).input_value()
    ok("Nút 'Tạo ngẫu nhiên' sinh 10 ký tự, điền cả ô Nhập lại, hiện chữ",
       len(gen) == 10 and dlg.get_by_label("Nhập lại mật khẩu mới", exact=True).input_value() == gen
       and dlg.get_by_label("Mật khẩu mới", exact=True).get_attribute("type") == "text", gen)
    fill_pw(dlg, "Mật khẩu mới", "Songbien2026")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    expect(dlg.locator(".cred-password")).to_have_text("Songbien2026")
    ok("S42-AC3 xong: hiện mật khẩu mới để đọc cho nhân viên", True)
    dlg.get_by_role("button", name="Xong").click()
    # S48: Chủ đặt lại → kho1 phải đổi mật khẩu ở lần đăng nhập kế (kiểm ở s48_password.py). Ở đây bỏ cờ để đi tiếp S46.
    ok("S48-AC6 đặt lại mật khẩu → bật cờ phải đổi",
       page.evaluate("() => JSON.parse(localStorage.getItem('cave_erp_mock_users')).find(u => u.username === 'kho1').must_change_password") is True)
    page.evaluate("() => window.__caveMock.patchUser('kho1', {must_change_password: false})")

    # ---- S46-AC1: Chủ đăng xuất ở màn Tài khoản của tôi ----
    t_loc = token(page)
    page.locator(".who-link").click()
    page.wait_for_url("**/account/")
    ok("Bấm tên ở chân menu → Tài khoản của tôi", page.locator(".topbar h1").inner_text() == "Tài khoản của tôi")
    page.screenshot(path=f"{SHOTS}/s47-desktop-1280-account-chu.png")
    page.evaluate("() => localStorage.setItem('cave_erp_draft:x', JSON.stringify({owner:1,savedAt:'x',data:{a:1}}))")
    clear_log(page)
    page.locator(".account").get_by_role("button", name="Đăng xuất").click()
    page.wait_for_url("**/login/")
    ok("S46-AC1 gọi POST /api/auth/logout/", "POST /api/auth/logout/" in log(page), str(log(page)))
    ok("S46-AC1 xoá nháp trên máy", page.evaluate("() => localStorage.getItem('cave_erp_draft:x')") is None)
    use_token(page, t_loc)
    ok("S46-AC1 token cũ của Chủ → 401, về đăng nhập", "/login" in page.url, page.url)

    # ---- S42-AC1 / AC3: máy khác của giao1, kho1 → 401 ----
    use_token(page, t_giao1, "/my-deliveries/")
    ok("S42-AC1 máy của giao1 → 401 ở lần gọi kế tiếp", "/login" in page.url and page.get_by_text(msg(page, "sessionExpired")).count() == 1, page.url)
    login(page, "giao1")
    expect(page.locator(".alert-box.err span")).to_have_text(msg(page, "loginFailed"))
    ok("S42-AC1 giao1 đã nghỉ không đăng nhập được", "/login" in page.url)
    use_token(page, t_kho1)
    ok("S42-AC3 máy kho (token cũ của kho1) → 401", "/login" in page.url, page.url)
    login(page, "kho1")
    expect(page.locator(".alert-box.err")).to_be_visible()
    ok("S42-AC3 kho1 mật khẩu cũ không vào được", "/login" in page.url)
    login(page, "kho1", "Songbien2026")
    page.wait_for_url("**/overview/")
    page.wait_for_load_state("networkidle")
    ok("S42-AC3 kho1 mật khẩu mới vào được; S41-AC3 không còn 'Việc giao của tôi'",
       "Việc giao của tôi" not in nav_labels(page), str(nav_labels(page)))

    # ---- S46-AC2/AC3: kho1 tự đổi mật khẩu ----
    t_kho1_b = token(page)  # "máy B"
    drop_token(page)
    login(page, "kho1", "Songbien2026")  # "máy A"
    page.wait_for_url("**/overview/")
    page.locator(".who-link").click()
    page.wait_for_url("**/account/")
    page.get_by_role("button", name="Đổi mật khẩu").click()
    dlg = page.get_by_role("dialog")
    dlg.get_by_label("Mật khẩu hiện tại").fill("sai-mat-khau")
    dlg.get_by_label("Mật khẩu mới", exact=True).fill("Cangca2026x")
    dlg.get_by_label("Nhập lại mật khẩu mới").fill("Cangca2026x")
    dlg.get_by_role("button", name="Đổi mật khẩu").click()
    expect(dlg.locator(".alert-box.err span")).to_have_text(be(page, "AUTH_OLD_PASSWORD"))
    ok("S46-AC3 sai mật khẩu hiện tại → 'Mật khẩu hiện tại không đúng.'", True)
    dlg.get_by_label("Mật khẩu hiện tại").fill("Songbien2026")
    dlg.get_by_label("Mật khẩu mới", exact=True).fill("123456")
    dlg.get_by_label("Nhập lại mật khẩu mới").fill("123456")
    dlg.get_by_role("button", name="Đổi mật khẩu").click()
    expect(dlg.locator(".alert-box.err span")).to_contain_text(pw_problem(page, "PW_TOO_SHORT"))
    ok("S46-AC3 mật khẩu mới 6 ký tự → AUTH_WEAK_PASSWORD, detail nguyên văn", alert_text(dlg).startswith(pw_problem(page, "PW_TOO_SHORT")), alert_text(dlg))
    dlg.get_by_label("Mật khẩu mới", exact=True).fill("Cangca2026x")
    dlg.get_by_label("Nhập lại mật khẩu mới").fill("Cangca2026y")
    clear_log(page)
    dlg.get_by_role("button", name="Đổi mật khẩu").click()
    expect(dlg.locator(".field-err span")).to_have_text(msg(page, "passwordMismatch"))
    ok("S48-AC3 Nhập lại không khớp → 'Hai mật khẩu không khớp', không gọi API", log(page) == [], str(log(page)))
    dlg.get_by_label("Nhập lại mật khẩu mới").fill("Cangca2026x")
    t_before = token(page)
    dlg.get_by_role("button", name="Đổi mật khẩu").click()
    expect(page.locator(".alert-box.ok span")).to_have_text(msg(page, "passwordChanged"))
    ok("S46 tự đổi (không bị ép) → không hiện thông báo 'Đã đặt mật khẩu mới' của S48", page.locator(".pw-done-notice").count() == 0)
    ok("S46-AC2 máy A nhận token mới", token(page) not in (None, t_before))
    page.goto(BASE + "/inventory/")
    page.wait_for_load_state("networkidle")
    ok("S46-AC2 máy A làm tiếp (không bị đá ra)", "/inventory" in page.url, page.url)
    t_kho1_a = token(page)
    use_token(page, t_kho1_b)
    ok("S46-AC2 máy B → 401", "/login" in page.url, page.url)
    login(page, "kho1", "Cangca2026x")
    page.wait_for_url("**/overview/")
    ok("S46-AC2 mật khẩu mới đăng nhập được", True)

    # ---- S47-AC2: Chủ thêm lại nv_giao cho kho1 → kho1 bấm 'Tải lại quyền' (hoặc mở lại app) → menu có Việc giao ----
    page.evaluate("() => window.__caveMock.patchUser('kho1', {groups: ['nv_kho', 'nv_giao']})")
    page.locator(".who-link").click()
    page.wait_for_url("**/account/")
    page.get_by_role("button", name="Tải lại quyền").click()
    expect(page.locator(".nav").get_by_role("link", name="Việc giao của tôi")).to_be_visible()
    ok("S47-AC2 menu 'Việc giao của tôi' xuất hiện, không cần đăng nhập lại", True)
    page.locator(".who .iconbtn").click()
    page.wait_for_url("**/login/")

    # ---- S47-AC1 / AC4 + S41-AC9: Quản lý ----
    login(page, "ql1")
    page.wait_for_url("**/overview/")
    page.wait_for_load_state("networkidle")
    ok("S41-AC9 Quản lý không có menu Nhân sự", "Nhân sự · Nhật ký" not in nav_labels(page), str(nav_labels(page)))
    clear_log(page)
    page.goto(BASE + "/staff/")
    expect(page.get_by_text(msg(page, "noViewPermission"))).to_be_visible()
    ok("S41-AC9 gõ /staff/ → chặn, không gọi /api/staff/", all("/api/staff" not in x for x in log(page)), str(log(page)))
    page.locator(".who-link").click()
    page.wait_for_url("**/account/")
    caps = [c.split("\n")[-1].strip() for c in page.locator(".cap-list li").all_inner_texts()]
    ok("S47-AC1 Quản lý: 5 việc §1.5 + Xem Tổng quan (BE L6)",
       caps == ["Mở bán lô", "Huỷ đơn đã thanh toán", "Tạo phiếu hoàn", "Duyệt hàng hoàn", "Duyệt kiểm kê", "Xem Tổng quan"], str(caps))
    ok("S47-AC1 nhóm 'Quản lý', tên, SĐT", page.locator(".who-card .group-tag").all_inner_texts() == ["Quản lý"]
       and page.locator(".who-card a[href='tel:0909000111']").count() == 1)
    yn = page.locator(".perm-yn").inner_text()
    ok("S47-AC1/AC4 'Xem giá vốn: Không', capabilities không có Xem giá vốn", "Xem giá vốn\nKhông" in yn and "Xem giá vốn" not in caps, yn)
    ok("S47-AC1 có nút Đổi mật khẩu, Đăng xuất", page.get_by_role("button", name="Đổi mật khẩu").is_visible() and page.locator(".account").get_by_role("button", name="Đăng xuất").is_visible())
    page.screenshot(path=f"{SHOTS}/s47-desktop-1280-account-quanly.png")
    page.locator(".account").get_by_role("button", name="Đăng xuất").click()
    page.wait_for_url("**/login/")

    # ---- S41-AC6 / S42-AC7 + S47-AC3: ql9 có manage_staff nhưng không thuộc Chủ ----
    login(page, "ql9")
    page.wait_for_url("**/overview/")
    goto_staff(page)
    dlg = open_staff(page, "loc")
    ok("S42-AC7 ql9 xem tài khoản Chủ: không có nút nào (available_actions = [])",
       dlg.locator(".staff-actions button").count() == 0 and dlg.get_by_text(smsg(page, "noActions")).count() == 1)
    page.keyboard.press("Escape")
    dlg = open_staff(page, "kho1")
    dlg.get_by_role("button", name="Đổi nhóm").click()
    dlg.get_by_text("Chủ", exact=True).click()
    dlg.get_by_role("button", name="Lưu nhóm").click()
    dlg.get_by_role("button", name="Thêm nhóm Chủ").click()
    expect(dlg.locator(".alert-box.err")).to_be_visible()
    ok("S41-AC6 ql9 gán Chủ → 403 BR-PQ-17 nguyên văn", alert_text(dlg) == be(page, "CHU_GROUP_ONLY"), alert_text(dlg))
    ok("S41-AC6 403 do luật (quyền không đổi) → không báo 'Quyền vừa thay đổi'", page.locator(".perm-notice").count() == 0)
    page.keyboard.press("Escape")
    # 403 ở trên làm console tải lại /me (mock trả lời sau 250ms, đọc dữ liệu lúc trả lời) → chờ xong rồi mới đổi quyền,
    # nếu không /me đang bay sẽ thấy quyền mới và ẩn màn Nhân viên trước khi kịp mở giao2 (đua thời gian, không phải lỗi).
    page.wait_for_function("() => window.__caveMock.pending() === 0")
    # Chủ gỡ manage_staff của ql9 "từ máy khác", ql9 vẫn đang mở màn → bấm thao tác → 403 → tải lại me
    page.evaluate("() => window.__caveMock.patchUser('ql9', {extra_perms: []})")
    dlg = open_staff(page, "giao2")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    fill_pw(dlg, "Mật khẩu mới", "Songbien2026")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    expect(page.locator(".perm-notice")).to_be_visible()
    ok("S47-AC3 403 → tải lại me, báo 'Quyền của bạn vừa thay đổi'", msg(page, "permChanged") in page.locator(".perm-notice").inner_text())
    expect(page.get_by_text(msg(page, "noViewPermission"))).to_be_visible()
    ok("S47-AC3 màn Nhân viên ẩn, menu không còn Nhân sự", "Nhân sự · Nhật ký" not in nav_labels(page), str(nav_labels(page)))
    page.screenshot(path=f"{SHOTS}/s47-desktop-1280-perm-changed.png")
    page.locator(".who .iconbtn").click()
    page.wait_for_url("**/login/")

    # ---- S41-AC7: BR-PQ-18 (sa1 = superuser, bỏ Chủ của loc — Chủ cuối cùng) ----
    login(page, "sa1")
    page.wait_for_url("**/overview/")
    goto_staff(page)
    dlg = open_staff(page, "loc")
    btns = [b.split("\n")[-1].strip() for b in dlg.locator(".staff-actions button").all_inner_texts()]
    ok("Chủ cuối cùng: không có nút 'Cho nghỉ' (BE bỏ deactivate)", "Cho nghỉ" not in btns and "Đổi nhóm" in btns, str(btns))
    dlg.get_by_role("button", name="Đổi nhóm").click()
    dlg.get_by_text("Chủ", exact=True).click()
    dlg.get_by_role("button", name="Lưu nhóm").click()
    expect(dlg.locator(".confirm-danger")).to_contain_text("bỏ nhóm Chủ")
    dlg.get_by_role("button", name="Bỏ nhóm Chủ").click()
    expect(dlg.locator(".alert-box.err")).to_be_visible()
    ok("S41-AC7 BR-PQ-18 nguyên văn", alert_text(dlg) == be(page, "LAST_CHU_GROUP"), alert_text(dlg))
    page.keyboard.press("Escape")
    page.locator(".who .iconbtn").click()
    page.wait_for_url("**/login/")

    # ---- S41-AC1: giao4 đăng nhập → (S48: đặt mật khẩu mới trước) → Việc giao của tôi;
    #      S42-AC2: cho giao1 làm lại → đăng nhập bằng mật khẩu cũ ----
    login(page, "giao4", "Songbien2026")
    page.wait_for_url("**/set-password/")
    page.get_by_label("Mật khẩu hiện tại").fill("Songbien2026")
    fill_pw(page, "Mật khẩu mới", "Mayxanh2026")
    page.get_by_role("button", name="Lưu mật khẩu mới").click()
    page.wait_for_url("**/my-deliveries/")
    ok("S41-AC1 giao4 đăng nhập (qua màn đặt mật khẩu mới S48) → Việc giao của tôi", True)
    page.locator(".who .iconbtn").click()
    page.wait_for_url("**/login/")
    login(page, "loc")
    page.wait_for_url("**/overview/")
    goto_staff(page)
    page.get_by_role("button", name="Đã nghỉ").click()
    expect(staff_row(page, "giao1")).to_be_visible()
    dlg = open_staff(page, "giao1")
    dlg.get_by_role("button", name="Cho làm lại").click()
    dlg.get_by_role("button", name="Cho làm lại").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(page.locator(".alert-box.ok")).to_contain_text(smsg(page, "reactivated", "Anh Phúc (giao1)"))
    page.locator(".who .iconbtn").click()
    page.wait_for_url("**/login/")
    login(page, "giao1")
    page.wait_for_url("**/my-deliveries/")
    ok("S42-AC2 giao1 đăng nhập lại bằng mật khẩu cũ", True)
    ctx.close()

    # ======================= Mobile 360×640 =======================
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, device_scale_factor=2, is_mobile=True, has_touch=True,
                              reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.wait_for_url("**/overview/")
    goto_staff(page)
    sw = page.evaluate("() => document.documentElement.scrollWidth")
    ok("360 Nhân viên: không cuộn ngang", sw <= 360, str(sw))
    small = page.evaluate(SMALL_TARGETS)
    ok("360 Nhân viên: vùng bấm ≥44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/s41-mobile-360-staff.png")
    dlg = open_staff(page, "kho1")
    expect(dlg.locator(".staff-actions button").first).to_be_visible()
    sw = page.evaluate("() => document.documentElement.scrollWidth")
    small = page.evaluate(SMALL_TARGETS)
    ok("360 chi tiết: không cuộn ngang, nút ≥44px", sw <= 360 and not small, f"{sw} {small}")
    page.screenshot(path=f"{SHOTS}/s42-mobile-360-detail.png")
    dlg.get_by_role("button", name="Đổi nhóm").click()
    expect(dlg.get_by_role("button", name="Lưu nhóm")).to_be_visible()
    small = page.evaluate(SMALL_TARGETS)
    ok("360 đổi nhóm: ô chọn nhóm ≥44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/s41-mobile-360-groups.png")
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Thêm nhân viên").click()
    expect(page.get_by_role("dialog").get_by_label("Tên đăng nhập")).to_be_focused()
    sw = page.evaluate("() => document.documentElement.scrollWidth")
    small = page.evaluate(SMALL_TARGETS)
    ok("360 form tạo tài khoản: không cuộn ngang, nút ≥44px", sw <= 360 and not small, f"{sw} {small}")
    page.screenshot(path=f"{SHOTS}/s41-mobile-360-create.png")
    page.keyboard.press("Escape")
    page.goto(BASE + "/account/")
    expect(page.locator(".cap-list li").first).to_be_visible()
    sw = page.evaluate("() => document.documentElement.scrollWidth")
    small = page.evaluate(SMALL_TARGETS)
    ok("360 Tài khoản của tôi: không cuộn ngang, nút ≥44px", sw <= 360 and not small, f"{sw} {small}")
    page.screenshot(path=f"{SHOTS}/s47-mobile-360-account.png", full_page=True)
    page.get_by_role("button", name="Đổi mật khẩu").click()
    expect(page.get_by_role("dialog").get_by_label("Mật khẩu hiện tại")).to_be_focused()
    page.screenshot(path=f"{SHOTS}/s46-mobile-360-change-password.png")
    ctx.close()
    browser.close()

relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "401" not in e
            and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]
ok("Không lỗi console", not relevant, str(relevant[:5]))
passed = sum(1 for _, c, _ in results if c)
for n, c, e in results:
    print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + e))
print(f"{passed}/{len(results)} PASS")
