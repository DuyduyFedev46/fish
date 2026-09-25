# E2E S41, S42, S46, S47 trên BACKEND THẬT (Django), KHÔNG mock.
#   1) Django:  cd backend && DATABASE_URL=sqlite:////<tmp>/realbe.sqlite3 .venv/bin/python manage.py migrate
#               rồi bootstrap_masterdata, rồi seed tài khoản (mật khẩu chung PW) bằng `manage.py shell`: tạo User + StaffProfile
#               (phone, display_name) và gán Group cho loc (chu), ql1 (quan_ly), kho1 (nv_kho+nv_giao), giao1 (nv_giao),
#               nghi1 (nv_kho, is_active=False); rồi
#               CORS_ALLOWED_ORIGINS=http://127.0.0.1:3102 .venv/bin/python manage.py runserver 127.0.0.1:8000
#   2) Console: cd erp-console && npm run build && (cd out && python3 -m http.server 3102 &)
#   3) SHOTS=<thư mục ảnh> python3 e2e/s41_s47_real.py        # tắt cả hai server sau khi xong
#
# Không gõ lại câu lỗi nào: kịch bản bắt RESPONSE THẬT của API rồi so với chữ UI hiện ra (hiện nguyên văn `detail`),
# và kiểm `code` trong JSON. Seed: loc (chu), ql1 (quan_ly), kho1 (nv_kho+nv_giao), giao1 (nv_giao), nghi1 (đã nghỉ).
# Kịch bản sửa dữ liệu (tạo giao4, cho giao1 nghỉ, đổi mật khẩu kho1) → chạy lại thì seed lại DB tạm.
# Lô L6b: thêm S48 trên BE thật (contract "Lô L6b (BE)"): Chủ đặt lại mật khẩu → kho1 bị ép đặt mật khẩu mới,
# API nghiệp vụ 403 AUTH_MUST_CHANGE_PASSWORD; ô "Nhập lại" lệch → không có request. Không ngủ: chờ điều kiện.

import os
import re

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3102")
API = os.environ.get("API", "http://localhost:8000")
SHOTS = os.environ.get("SHOTS", "/tmp")
PW = os.environ.get("PW", "Songbien2026")
NEW_PW = os.environ.get("NEW_PW", "Cangca2026xyz")
results = []
expect.set_options(timeout=10_000)


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))


def login(page, user, pw=PW):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()


def fill_pw(scope, label, value, again=None):
    """Ô mật khẩu + ô 'Nhập lại …' (S48)."""
    scope.get_by_label(label, exact=True).fill(value)
    scope.get_by_label("Nhập lại " + label[0].lower() + label[1:], exact=True).fill(value if again is None else again)


def api_get(ctx, tok, path):
    r = ctx.request.get(API + path, headers={"Authorization": f"Token {tok}"})
    try:
        return r.status, r.json()
    except Exception:
        return r.status, None


def token(page):
    return page.evaluate("() => localStorage.getItem('cave_erp_token')")


def api_status(ctx, tok, path="/api/auth/me/"):
    return ctx.request.get(API + path, headers={"Authorization": f"Token {tok}"}).status


def staff_row(page, username):
    return page.locator("ul.staff-list > li").filter(
        has=page.locator("small", has_text=re.compile(rf"^{re.escape(username)}$"))
    )


def open_staff(page, username):
    staff_row(page, username).locator(".staff-open").click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    return dlg


def err_text(scope):
    loc = scope.locator(".alert-box.err span")
    expect(loc).to_be_visible()
    return loc.inner_text().strip()


def submit_and_capture(page, click, url_part, method):
    """Bấm nút, trả JSON response thật của request khớp url_part + method."""
    with page.expect_response(lambda r: url_part in r.url and r.request.method == method) as info:
        click()
    r = info.value
    try:
        body = r.json()
    except Exception:
        body = None
    return r.status, body


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    # Token "máy khác" của giao1, kho1
    login(page, "giao1")
    page.wait_for_url("**/my-deliveries/")
    t_giao1 = token(page)
    page.evaluate("() => localStorage.removeItem('cave_erp_token')")
    login(page, "kho1")
    page.wait_for_url("**/overview/")
    t_kho1 = token(page)
    page.evaluate("() => localStorage.removeItem('cave_erp_token')")

    # ---- Chủ: danh sách ----
    login(page, "loc")
    page.wait_for_url("**/overview/")
    with page.expect_response(lambda r: "/api/staff/?is_active=true" in r.url) as info:
        page.get_by_role("link", name="Nhân sự · Nhật ký").click()
    rows = info.value.json()
    expect(page.locator("ul.staff-list > li").first).to_be_visible()
    ui_users = page.locator("ul.staff-list > li small").all_inner_texts()
    ok("Danh sách = đúng JSON BE (?is_active=true)", sorted(ui_users) == sorted(r["username"] for r in rows), f"{ui_users} vs {[r['username'] for r in rows]}")
    ok("S41-AC10 JSON thật không có key password/token", all("password" not in r and "token" not in r for r in rows))
    ok("Không có nghi1 trong 'Đang làm'", "nghi1" not in ui_users)
    me_row = next(r for r in rows if r["username"] == "loc")
    dlg = open_staff(page, "loc")
    btns = [b.split("\n")[-1].strip() for b in dlg.locator(".staff-actions button").all_inner_texts()]
    ok("Nút theo available_actions BE (chính mình)", me_row["available_actions"] == ["edit"] and btns == ["Sửa hồ sơ"], f"{me_row['available_actions']} {btns}")
    page.keyboard.press("Escape")

    # ---- S41-AC4: lỗi thật hiện nguyên văn ----
    page.get_by_role("button", name="Thêm nhân viên").click()
    dlg = page.get_by_role("dialog")
    dlg.get_by_label("Tên đăng nhập").fill("KHO1")
    dlg.get_by_label("Số điện thoại").fill("0909333444")
    fill_pw(dlg, "Mật khẩu tạm", PW)
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Tạo tài khoản").click(), "/api/staff/", "POST")
    ok("S41-AC4 trùng username: 400 BR-PQ-08, UI = detail BE", st == 400 and body.get("code") == "BR-PQ-08" and err_text(dlg) == body.get("detail"), f"{st} {body}")
    dlg.get_by_label("Tên đăng nhập").fill("giao4")
    dlg.get_by_label("Số điện thoại").fill("")
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Tạo tài khoản").click(), "/api/staff/", "POST")
    ok("S41-AC4 thiếu SĐT: UI = detail BE", st == 400 and err_text(dlg) == body.get("detail"), f"{st} {body}")
    dlg.get_by_label("Số điện thoại").fill("0909333444")
    fill_pw(dlg, "Mật khẩu tạm", "abc")
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Tạo tài khoản").click(), "/api/staff/", "POST")
    ok("S41-AC4 mật khẩu yếu: UI = detail Django thật", st == 400 and err_text(dlg) == body.get("detail"), f"{st} {body}")

    # ---- S7-AC6 trên form thật + backend thật: token hỏng giữa chừng → đăng nhập lại → form mở lại ----
    dlg.get_by_label("Tên hiển thị").fill("Anh Năm")
    dlg.get_by_text("Nhân viên giao", exact=True).click()
    fill_pw(dlg, "Mật khẩu tạm", PW)
    page.wait_for_function("""() => { const d = JSON.parse(localStorage.getItem('cave_erp_draft:staff:create') || 'null');
        return !!d && d.data.display_name === 'Anh Năm' && d.data.groups.includes('nv_giao'); }""")
    ok("S48-AC5 nháp không chứa mật khẩu", PW not in (page.evaluate("() => localStorage.getItem('cave_erp_draft:staff:create')") or ""))
    page.evaluate("() => localStorage.setItem('cave_erp_token', 'token-da-bi-thu-hoi')")
    st, _ = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Tạo tài khoản").click(), "/api/staff/", "POST")
    page.wait_for_url("**/login/**")
    ok("S7-AC6 BE trả 401 → về đăng nhập", st == 401 and "next=%2Fstaff" in page.url, f"{st} {page.url}")
    page.get_by_label("Tài khoản").fill("loc")
    page.get_by_label("Mật khẩu").fill(PW)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/staff/")
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    ok("S7-AC6 form mở lại đủ nội dung (trừ mật khẩu)",
       dlg.get_by_label("Tên đăng nhập").input_value() == "giao4" and dlg.get_by_label("Tên hiển thị").input_value() == "Anh Năm"
       and dlg.locator("input[name=groups]:checked").evaluate_all("els => els.map(e => e.value)") == ["nv_giao"])

    # ---- S48-AC3: Nhập lại lệch → không có request POST ----
    posts = []
    page.on("request", lambda r: "/api/staff/" in r.url and r.method == "POST" and posts.append(r.url))
    fill_pw(dlg, "Mật khẩu tạm", PW, again=PW + "x")
    dlg.get_by_role("button", name="Tạo tài khoản").click()
    expect(dlg.locator(".field-err span")).to_be_visible()
    ok("S48-AC3 tạo tài khoản: Nhập lại lệch → không gửi POST", posts == [], str(posts))

    # ---- S41-AC1: tạo giao4 thật (Q2: bấm là có POST) ----
    fill_pw(dlg, "Mật khẩu tạm", PW)
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Tạo tài khoản").click(), "/api/staff/", "POST")
    ok("S41-AC1 POST 201, nhóm nv_giao", st == 201 and body.get("groups") == ["nv_giao"], f"{st} {body}")
    dlg.get_by_role("button", name="Xong").click()
    expect(staff_row(page, "giao4")).to_be_visible()
    page.screenshot(path=f"{SHOTS}/real-s41-desktop-1280-staff.png")

    # ---- S41-AC3: bỏ nv_giao của kho1 ----
    dlg = open_staff(page, "kho1")
    dlg.get_by_role("button", name="Đổi nhóm").click()
    dlg.get_by_text("Nhân viên giao", exact=True).click()
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Lưu nhóm").click(), "/groups/", "PUT")
    ok("S41-AC3 PUT groups 200, removed nv_giao", st == 200 and body.get("removed") == ["nv_giao"], f"{st} {body}")
    expect(staff_row(page, "kho1").locator(".group-tag")).to_have_text(["Nhân viên kho"])

    # ---- S42-AC1: cho giao1 nghỉ → token máy giao1 chết ----
    dlg = open_staff(page, "giao1")
    dlg.get_by_role("button", name="Cho nghỉ").click()
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Cho nghỉ").click(), "/deactivate/", "POST")
    ok("S42-AC1 deactivate 200", st == 200 and body == {"is_active": False}, f"{st} {body}")
    expect(staff_row(page, "giao1")).to_have_count(0)
    ok("S42-AC1 token cũ của giao1 → 401 ở BE", api_status(ctx, t_giao1) == 401)

    # ---- S42-AC3: đặt lại mật khẩu kho1 ----
    dlg = open_staff(page, "kho1")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    fill_pw(dlg, "Mật khẩu mới", PW + "b")
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Đặt lại mật khẩu").click(), "/reset-password/", "POST")
    ok("S42-AC3 reset-password 200", st == 200, f"{st} {body}")
    ok("S42-AC3 token cũ máy kho → 401 ở BE", api_status(ctx, t_kho1) == 401)
    dlg.get_by_role("button", name="Xong").click()

    # ---- S46-AC1: Chủ đăng xuất ----
    t_loc = token(page)
    page.locator(".who-link").click()
    page.wait_for_url("**/account/")
    page.screenshot(path=f"{SHOTS}/real-s47-desktop-1280-account-chu.png")
    st, _ = submit_and_capture(page, lambda: page.locator(".account").get_by_role("button", name="Đăng xuất").click(), "/api/auth/logout/", "POST")
    page.wait_for_url("**/login/")
    ok("S46-AC1 logout 204, token cũ → 401 ở BE", st == 204 and api_status(ctx, t_loc) == 401, str(st))

    # ---- S48 trên BE thật: giao4 (Chủ vừa tạo) có cờ, API nghiệp vụ 403 AUTH_MUST_CHANGE_PASSWORD ----
    r = ctx.request.post(API + "/api/auth/token/", data={"username": "giao4", "password": PW})
    t_g4 = r.json().get("token")
    st, me_g4 = api_get(ctx, t_g4, "/api/auth/me/")
    ok("S48-AC1 BE: giao4 vừa tạo → me.must_change_password = true", st == 200 and me_g4.get("must_change_password") is True, f"{st} {me_g4}")
    st, body = api_get(ctx, t_g4, "/api/staff/")
    st2, body2 = api_get(ctx, t_g4, "/api/dashboard/summary/")
    ok("S48-AC1 BE: API khác → 403 code AUTH_MUST_CHANGE_PASSWORD",
       st == 403 and st2 == 403 and (body or {}).get("code") == "AUTH_MUST_CHANGE_PASSWORD"
       and (body2 or {}).get("code") == "AUTH_MUST_CHANGE_PASSWORD", f"{st} {body} {st2} {body2}")

    # ---- S48-AC1/AC2/AC6: kho1 bị Chủ đặt lại → đăng nhập → chỉ màn "Đặt mật khẩu mới" → đổi → home ----
    login(page, "kho1", PW + "b")
    page.wait_for_url("**/set-password/")
    t_forced = token(page)
    st, body = api_get(ctx, t_forced, "/api/inventory/batches/")
    ok("S48-AC6 BE: Chủ đặt lại → cờ bật; UI chỉ mở /set-password/; API nghiệp vụ 403 AUTH_MUST_CHANGE_PASSWORD",
       st == 403 and (body or {}).get("code") == "AUTH_MUST_CHANGE_PASSWORD" and page.locator(".nav").count() == 0, f"{st} {body}")
    page.goto(BASE + "/overview/")
    page.wait_for_url("**/set-password/")
    ok("S48-AC1 gõ /overview/ → vẫn ở màn đặt mật khẩu", True)
    page.screenshot(path=f"{SHOTS}/real-s48-desktop-1280-set-password.png")
    cps = []
    page.on("request", lambda r: "/change-password/" in r.url and cps.append(r.url))
    page.get_by_label("Mật khẩu hiện tại").fill(PW + "b")
    fill_pw(page, "Mật khẩu mới", PW + "c", again=PW + "d")
    page.get_by_role("button", name="Lưu mật khẩu mới").click()
    expect(page.locator(".field-err span")).to_be_visible()
    ok("S48-AC3 đặt mật khẩu mới: lệch → không gọi change-password", cps == [], str(cps))
    fill_pw(page, "Mật khẩu mới", PW + "c")
    st, body = submit_and_capture(page, lambda: page.get_by_role("button", name="Lưu mật khẩu mới").click(), "/change-password/", "POST")
    page.wait_for_url("**/overview/")
    st_me, me_k = api_get(ctx, token(page), "/api/auth/me/")
    ok("S48-AC2 BE: change-password 200 → cờ false, vào Tổng quan",
       st == 200 and me_k.get("must_change_password") is False and page.locator(".nav").count() == 1, f"{st} {me_k}")
    page.locator(".who .iconbtn").click()
    page.wait_for_url("**/login/")

    # ---- S46-AC2/AC3: kho1 tự đổi mật khẩu ----
    login(page, "kho1", PW + "c")
    page.wait_for_url("**/overview/")
    ok("S48-AC6 tự đổi xong không bật lại cờ: đăng nhập lại → thẳng Tổng quan", True)
    ok("S41-AC3 kho1 không còn menu 'Việc giao của tôi'", page.locator(".nav").get_by_role("link", name="Việc giao của tôi").count() == 0)
    t_a = token(page)
    page.locator(".who-link").click()
    page.wait_for_url("**/account/")
    page.get_by_role("button", name="Đổi mật khẩu").click()
    dlg = page.get_by_role("dialog")
    dlg.get_by_label("Mật khẩu hiện tại").fill("sai-mat-khau")
    dlg.get_by_label("Mật khẩu mới", exact=True).fill(NEW_PW)
    dlg.get_by_label("Nhập lại mật khẩu mới").fill(NEW_PW)
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Đổi mật khẩu").click(), "/change-password/", "POST")
    ok("S46-AC3 sai MK cũ: AUTH_OLD_PASSWORD, UI = detail BE", st == 400 and body.get("code") == "AUTH_OLD_PASSWORD" and err_text(dlg) == body.get("detail"), f"{st} {body}")
    ok("S46-AC3 lỗi → token cũ vẫn dùng được", api_status(ctx, t_a) == 200)
    dlg.get_by_label("Mật khẩu hiện tại").fill(PW + "c")
    dlg.get_by_label("Mật khẩu mới", exact=True).fill("123456")
    dlg.get_by_label("Nhập lại mật khẩu mới").fill("123456")
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Đổi mật khẩu").click(), "/change-password/", "POST")
    ok("S46-AC3 MK mới yếu: AUTH_WEAK_PASSWORD, UI = detail Django", st == 400 and body.get("code") == "AUTH_WEAK_PASSWORD" and err_text(dlg) == body.get("detail"), f"{st} {body}")
    dlg.get_by_label("Mật khẩu mới", exact=True).fill(NEW_PW)
    dlg.get_by_label("Nhập lại mật khẩu mới").fill(NEW_PW)
    st, body = submit_and_capture(page, lambda: dlg.get_by_role("button", name="Đổi mật khẩu").click(), "/change-password/", "POST")
    expect(page.get_by_role("dialog")).to_have_count(0)
    ok("S46-AC2 200 + token mới trên máy, token cũ → 401", st == 200 and token(page) == body.get("token") and api_status(ctx, t_a) == 401, f"{st}")
    page.goto(BASE + "/inventory/")
    expect(page.locator(".screen")).to_be_visible()
    ok("S46-AC2 máy A làm tiếp bằng token mới", "/inventory" in page.url, page.url)
    page.locator(".who .iconbtn").click()
    page.wait_for_url("**/login/")

    # ---- S47-AC1/AC4 + S41-AC9: Quản lý ----
    login(page, "ql1")
    page.wait_for_url("**/overview/")
    page.goto(BASE + "/account/")
    expect(page.locator(".cap-list li").first).to_be_visible()
    # QA Q2: không đọc body của response đã bị thay khi trang reload — hỏi thẳng API bằng token của máy
    _, me = api_get(ctx, token(page), "/api/auth/me/")
    caps = [c.split("\n")[-1].strip() for c in page.locator(".cap-list li").all_inner_texts()]
    ok("S47-AC1 việc được làm = capabilities BE", caps == [c["label"] for c in me["capabilities"]], f"{caps} vs {me['capabilities']}")
    ok("S47-AC1 nhóm = group_labels BE", page.locator(".who-card .group-tag").all_inner_texts() == [g["label"] for g in me["group_labels"]])
    ok("S47-AC4 không có view_costprice, can_view_cost=false",
       all(c["code"] != "inventory.view_costprice" for c in me["capabilities"]) and me["can_view_cost"] is False
       and "Không" in page.locator(".perm-yn dd").first.inner_text())
    page.screenshot(path=f"{SHOTS}/real-s47-desktop-1280-account-quanly.png")
    page.goto(BASE + "/staff/")
    expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
    ok("S41-AC9 Quản lý: màn Nhân viên bị chặn", page.locator("ul.staff-list").count() == 0)
    ok("S41-AC9 Quản lý gọi thẳng /api/staff/ → 403 ở BE", api_status(ctx, token(page), "/api/staff/") == 403)
    ctx.close()

    # ---- Mobile 360 trên backend thật ----
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, device_scale_factor=2, is_mobile=True, has_touch=True,
                              reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.wait_for_url("**/overview/")
    page.goto(BASE + "/staff/")
    expect(page.locator("ul.staff-list > li").first).to_be_visible()
    ok("360 Nhân viên (BE thật): không cuộn ngang", page.evaluate("() => document.documentElement.scrollWidth") <= 360)
    page.screenshot(path=f"{SHOTS}/real-s41-mobile-360-staff.png")
    open_staff(page, "kho1")
    page.screenshot(path=f"{SHOTS}/real-s42-mobile-360-detail.png")
    page.keyboard.press("Escape")
    page.goto(BASE + "/account/")
    expect(page.locator(".cap-list li").first).to_be_visible()
    ok("360 Tài khoản (BE thật): không cuộn ngang", page.evaluate("() => document.documentElement.scrollWidth") <= 360)
    page.screenshot(path=f"{SHOTS}/real-s47-mobile-360-account.png", full_page=True)
    ctx.close()
    browser.close()

relevant = [e for e in errors if "fonts.g" not in e and "401" not in e and "400" not in e and "403" not in e
            and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]
ok("Không lỗi console (trừ 4xx cố ý)", not relevant, str(relevant[:5]))
passed = sum(1 for _, c, _ in results if c)
for n, c, e in results:
    print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + e))
print(f"{passed}/{len(results)} PASS")
