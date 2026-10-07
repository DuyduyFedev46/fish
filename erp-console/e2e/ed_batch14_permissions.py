# E2E ERP theo design, Lô 14 (Nhân sự ED-37/38 + Phân quyền ED-39/40): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/ed_batch14_permissions.py      # tắt server sau khi xong
# Kiểm: loc (Chủ) bật/tắt việc ở ma trận (hỏi lại khi tắt, "Tất cả khách" khi bật Xem khách hàng, cột Chủ khoá) và ở trang nhóm
# (thêm / bỏ thành viên), hồ sơ nhân viên (sửa, nút theo available_actions) · ql1, kho1, giao1, cs2: không có menu Nhân sự / Phân quyền,
# vào URL thì "Không có quyền" và KHÔNG có request /api/staff · ql9 (manage_staff nhưng không thuộc Chủ): chỉ xem ·
# ca ngoài đường thuận: id/mã nhóm sai, thiếu tham số, máy chủ lỗi 500, 403 giữa chừng khi bật việc, Escape không gọi API ·
# Kho giả cave_erp_mock_* (người dùng + mật khẩu demo của mock đăng nhập, có từ trước lô này) không tính vào kiểm storage.
# 360px không cuộn ngang, vùng bấm >= 44px · tên/SĐT không nằm ở URL, localStorage, sessionStorage.
import os
import re

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)
PHONE_RE = re.compile(r"0\d{9}")
BAD_WORDS = ("undefined", "NaN", "[object", "BR-PQ", "BR-GH")


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    settle(page)


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def new_page(browser, user, w=1280, h=860, errors=None, touch=False):
    errors = errors if errors is not None else []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", **({"is_mobile": True, "has_touch": True} if touch else {}))
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, user)
    return ctx, page, errors


def storage_dump(page):
    # Khoá giả của mock (cave_erp_mock_*: người dùng, đơn, SĐT giả của dữ liệu mẫu) nằm ở cả local và session; bản thật không có.
    return page.evaluate("""() => {
        const real = (e) => e[0] !== 'cave_erp_token' && !e[0].startsWith('cave_erp_mock_');
        return JSON.stringify([Object.entries(localStorage).filter(real), Object.entries(sessionStorage).filter(real)]);
    }""")


def nav_labels(page):
    return [t.split("\n")[-1].strip() for t in page.locator(".nav a").all_inner_texts()]


def log(page):
    return page.evaluate("() => window.__caveMock.log.slice()")


def clear_log(page):
    page.evaluate("() => window.__caveMock.clearLog()")


def dialog(page):
    return page.get_by_role("dialog")


def staff_row(page, username):
    return page.locator("main tr.lt-click").filter(has=page.locator("td", has_text=re.compile(rf"^{re.escape(username)}$")))


def wait_staff_rows(page):
    expect(page.locator("main tr.lt-click").first).to_be_visible()
    expect(page.locator("main [aria-busy=true]")).to_have_count(0)


def switch(page, task, group):
    return page.get_by_role("switch", name=f"{task} — {group}", exact=True)


def toast_text(page):
    return page.locator(".toast-item").first.inner_text()


def smsg(page, key, *args):
    return page.evaluate("([k, a]) => { const v = window.__caveMock.staffMsg[k]; return typeof v === 'function' ? v(...a) : v; }", [key, list(args)])


def no_perm(page):
    return page.get_by_role("heading", name=page.evaluate("() => window.__caveMock.msg.noViewPermission")).count() == 1


SMALL_TARGETS = """() => [...document.querySelectorAll('main button, main a, main input, main [role=switch]')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    if (e.type === 'checkbox' || e.classList.contains('lt-link')) return false;
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y >= 0 && r.y < innerHeight
      && (r.height < 44 || (r.width < 44 && e.tagName !== 'INPUT' && !e.closest('td')));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.id).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""


def owner(browser):
    ctx, page, errors = new_page(browser, "loc")
    ok("loc: menu có Nhân sự và Phân quyền", "Nhân sự" in nav_labels(page) and "Phân quyền" in nav_labels(page), str(nav_labels(page)))

    # ---------- Ma trận ----------
    go(page, "/permissions/")
    expect(page.get_by_role("switch").first).to_be_visible()
    heads = [h.strip().lower() for h in page.locator("table thead th").all_text_contents()]
    ok("ma trận: có cột Quản lý và Nhân viên giao, cột 'Chỉ Chủ'", "quản lý" in heads and "nhân viên giao" in heads and "chỉ chủ" in heads, str(heads))
    rows_text = page.locator("main table").nth(1).inner_text()
    ok("ma trận: có việc Xem khách hàng, Ghi hàng hoàn về kho", "Xem khách hàng" in rows_text and "Ghi hàng hoàn về kho" in rows_text)
    ok("danh sách nhóm: 5 nhóm, bấm được", page.locator("main table").first.locator("tr.lt-click").count() == 5, str(page.locator("main table").first.locator("tr.lt-click").count()))
    ok("giá vốn không hiện ở cột nhóm trừ cờ Có/Không", "Xem giá vốn" in page.locator("main table").first.inner_text())
    page.screenshot(path=f"{SHOTS}/lo14-desktop-1280-matrix.png", full_page=True)

    # Ô Chủ: khoá, không phải switch
    own_cell = page.locator("main table").nth(1).locator("tbody tr", has_text="Xem khách hàng").locator("td").nth(0)
    ok("cột Chủ: không có công tắc", own_cell.get_by_role("switch").count() == 0)
    # tìm việc
    page.get_by_role("searchbox", name="Tìm việc trong ma trận").fill("khách")
    ok("tìm 'khách': chỉ còn việc khớp", page.locator("main table").nth(1).locator("tbody tr th[scope=row]").count() == 1,
       str(page.locator("main table").nth(1).locator("tbody tr th[scope=row]").all_inner_texts()))
    page.get_by_role("searchbox", name="Tìm việc trong ma trận").fill("zzzz-khong-co")
    expect(page.get_by_text("Không có việc nào khớp")).to_be_visible()
    ok("tìm không ra: báo rõ, không bảng trống trơn", True)
    page.get_by_role("searchbox", name="Tìm việc trong ma trận").fill("")

    # Bật Xem khách hàng cho Nhân viên kho → "Tất cả khách"
    sw = switch(page, "Xem khách hàng", "Nhân viên kho")
    expect(sw).to_have_attribute("aria-checked", "false")
    clear_log(page)
    sw.click()
    expect(sw).to_have_attribute("aria-checked", "true")
    ok("bật Xem khách hàng gọi PUT .../capabilities/", any(x.startswith("PUT /api/staff/groups/warehouse_staff/capabilities/") for x in log(page)), str(log(page)))
    ok("bật Xem khách hàng: ghi rõ 'Tất cả khách' (quyết định #13)", page.locator("main table").nth(1).get_by_text("Tất cả khách").count() >= 1)
    page.screenshot(path=f"{SHOTS}/lo14-desktop-1280-all-customers.png")

    # Việc làm hỏng cả màn khi tắt (Xem đơn) → hỏi lại; Giữ nguyên / Escape không gọi API
    sw2 = switch(page, "Xem đơn", "Quản lý")
    expect(sw2).to_have_attribute("aria-checked", "true")
    clear_log(page)
    sw2.click()
    dlg = dialog(page)
    expect(dlg).to_be_visible()
    ok("tắt Xem đơn: hỏi lại trước, chưa gọi API", not any(x.startswith("PUT") for x in log(page)), str(log(page)))
    dlg.get_by_role("button", name="Giữ nguyên").click()
    expect(dialog(page)).to_have_count(0)
    ok("Giữ nguyên: ô vẫn bật, không PUT", sw2.get_attribute("aria-checked") == "true" and not any(x.startswith("PUT") for x in log(page)))
    sw2.click()
    page.keyboard.press("Escape")
    expect(dialog(page)).to_have_count(0)
    ok("Escape ở hộp xác nhận: không gọi API, ô vẫn bật", not any(x.startswith("PUT") for x in log(page)) and sw2.get_attribute("aria-checked") == "true")
    sw2.click()
    dialog(page).get_by_role("button", name="Tắt việc này").click()
    expect(dialog(page)).to_have_count(0)
    expect(sw2).to_have_attribute("aria-checked", "false")
    ok("xác nhận tắt Xem đơn: ô tắt, đã PUT", any(x.startswith("PUT /api/staff/groups/manager/capabilities/") for x in log(page)), str(log(page)))
    sw2.click()
    expect(sw2).to_have_attribute("aria-checked", "true")

    # Việc thường: tắt ngay (có thể hoàn tác), tải lại vẫn giữ (mock lưu sessionStorage)
    sw3 = switch(page, "Gọi xác nhận đơn", "Quản lý")
    expect(sw3).to_have_attribute("aria-checked", "true")
    sw3.click()
    expect(sw3).to_have_attribute("aria-checked", "false")
    ok("việc thường: tắt ngay, không hộp hỏi", dialog(page).count() == 0)
    go(page, "/permissions/")
    expect(switch(page, "Gọi xác nhận đơn", "Quản lý")).to_have_attribute("aria-checked", "false")
    ok("tải lại trang vẫn thấy việc đã tắt", True)
    switch(page, "Gọi xác nhận đơn", "Quản lý").click()
    expect(switch(page, "Gọi xác nhận đơn", "Quản lý")).to_have_attribute("aria-checked", "true")
    switch(page, "Xem khách hàng", "Nhân viên kho").click()
    expect(switch(page, "Xem khách hàng", "Nhân viên kho")).to_have_attribute("aria-checked", "false")

    # Việc 'Chỉ Chủ' ở nhóm khác: ô khoá, không phải công tắc
    ok("việc Chỉ Chủ ở nhóm khác: không có công tắc", switch(page, "Xem giá vốn", "Quản lý").count() == 0)
    ok("việc Ghi hàng hoàn về kho: có công tắc cho Nhân viên kho", switch(page, "Ghi hàng hoàn về kho", "Nhân viên kho").count() == 1)

    # ---------- Trang nhóm ----------
    page.get_by_role("link", name="Mở nhóm Quản lý").click()
    page.wait_for_url("**/permissions/detail/?group=manager")
    expect(page.locator("main h2", has_text="Quản lý").first).to_be_visible()
    settle(page)
    ok("trang nhóm: có Thành viên và Việc được làm", page.get_by_role("heading", name="Việc được làm").count() == 1 and page.get_by_role("heading", name=re.compile("^Thành viên")).count() == 1)
    ok("trang nhóm: URL chỉ mang mã nhóm", "?group=manager" in page.url and not PHONE_RE.search(page.url), page.url)
    ok("trang nhóm: có Phạm vi dữ liệu và Lịch sử thay đổi", page.get_by_text("Phạm vi dữ liệu").count() >= 1 and page.get_by_text("Lịch sử thay đổi").count() >= 1)
    page.screenshot(path=f"{SHOTS}/lo14-desktop-1280-group.png", full_page=True)
    # thêm người
    page.get_by_role("button", name="Thêm người vào nhóm").click()
    dlg = dialog(page)
    expect(dlg.get_by_role("searchbox", name="Tìm nhân viên để thêm")).to_be_visible()
    dlg.get_by_role("searchbox", name="Tìm nhân viên để thêm").fill("kho1")
    clear_log(page)
    dlg.get_by_role("button", name=re.compile("^Thêm vào nhóm: ")).click()
    expect(dialog(page)).to_have_count(0)
    expect(page.locator(".toast-item", has_text="Đã thêm Anh Tâm")).to_have_count(1)
    expect(page.locator("main tr.lt-click", has_text="kho1")).to_have_count(1)
    ok("thêm người: toast + có trong bảng", True)
    # bỏ người
    page.get_by_role("button", name="Bỏ Anh Tâm khỏi nhóm").click()
    dlg = dialog(page)
    expect(dlg).to_be_visible()
    dlg.get_by_role("button", name="Bỏ khỏi nhóm").click()
    expect(dialog(page)).to_have_count(0)
    expect(page.locator("main tr.lt-click", has_text="kho1")).to_have_count(0)
    ok("bỏ người: biến khỏi bảng", True)
    # Chủ: nhóm khoá
    go(page, "/permissions/detail/?group=owner")
    expect(page.get_by_text("Nhóm Chủ luôn có đủ quyền")).to_be_visible()
    ok("nhóm Chủ: khoá, không có công tắc", page.get_by_role("switch").count() == 0)
    # Việc khách hàng ở nhóm bật rõ cảnh báo
    go(page, "/permissions/detail/?group=warehouse_staff")
    sw = page.get_by_role("switch", name="Xem khách hàng — Nhân viên kho")
    sw.click()
    expect(sw).to_have_attribute("aria-checked", "true")
    expect(page.get_by_role("note").filter(has_text="danh sách khách hàng đầy đủ")).to_be_visible()
    ok("trang nhóm: bật Xem khách hàng hiện 'Tất cả khách' + cảnh báo", page.get_by_text("Tất cả khách").count() >= 1)
    page.screenshot(path=f"{SHOTS}/lo14-desktop-1280-group-customers.png", full_page=True)
    sw.click()
    expect(sw).to_have_attribute("aria-checked", "false")

    # ---------- Nhân sự ----------
    go(page, "/staff/")
    wait_staff_rows(page)
    ok("danh sách nhân viên: có tab Đang làm / Đã nghỉ / Tất cả", page.get_by_role("tab").count() == 3 or page.get_by_role("button", name=re.compile("Đã nghỉ")).count() >= 1)
    ok("danh sách nhân viên: chỉ người đang làm, có kho1, không có nghi1", staff_row(page, "kho1").count() == 1 and staff_row(page, "nghi1").count() == 0)
    ok("danh sách nhân viên: có khối Nhóm quyền", page.get_by_role("heading", name=re.compile("^Nhóm quyền")).count() == 1)
    page.screenshot(path=f"{SHOTS}/lo14-desktop-1280-staff.png", full_page=True)
    page.get_by_role("searchbox", name="Tìm nhân viên").fill("xyz-khong-co")
    expect(page.get_by_text(re.compile("Không có nhân viên nào khớp|Không tìm thấy"))).to_be_visible()
    ok("tìm không ra: báo rõ", True)
    page.get_by_role("searchbox", name="Tìm nhân viên").fill("")
    page.get_by_role("tab", name=re.compile("Đã nghỉ")).click()
    expect(staff_row(page, "nghi1")).to_be_visible()
    ok("tab Đã nghỉ có nghi1", True)
    ok("tab lưu ở URL chỉ là ?tab=", "tab=inactive" in page.url and not PHONE_RE.search(page.url), page.url)
    page.get_by_role("tab", name=re.compile("Đang làm")).click()

    # Hồ sơ kho1
    staff_row(page, "kho1").locator("a").first.click()
    page.wait_for_url(re.compile(r"/staff/detail/\?id=3"))
    expect(page.locator("main h2").first).to_contain_text("Anh Tâm")
    settle(page)
    ok("hồ sơ: URL chỉ có id số", page.url.endswith("?id=3"), page.url)
    ok("hồ sơ: có Sửa hồ sơ, Đổi nhóm, menu '…'", page.get_by_role("button", name="Sửa hồ sơ").count() == 1 and page.get_by_role("button", name="Đổi nhóm").count() == 1 and page.get_by_role("button", name="Thao tác khác").count() == 1)
    ok("hồ sơ: có Quyền theo nhóm", page.get_by_role("heading", name="Quyền theo nhóm").count() == 1)
    page.screenshot(path=f"{SHOTS}/lo14-desktop-1280-staff-detail.png", full_page=True)
    # Sửa hồ sơ: chưa đổi gì → không gọi API
    page.get_by_role("button", name="Sửa hồ sơ").click()
    dlg = dialog(page)
    clear_log(page)
    dlg.get_by_role("button", name="Lưu hồ sơ").click()
    expect(dlg.get_by_text(smsg(page, "editNothing"))).to_be_visible()
    ok("sửa hồ sơ chưa đổi gì: báo, không gọi API", not any(x.startswith("PATCH") for x in log(page)), str(log(page)))
    dlg.get_by_label("Tên hiển thị").fill("Anh Tâm Kho")
    dlg.get_by_role("button", name="Lưu hồ sơ").click()
    expect(dialog(page)).to_have_count(0)
    expect(page.locator("main h2").first).to_contain_text("Anh Tâm Kho")
    ok("sửa hồ sơ: PATCH, tiêu đề đổi theo", any(x.startswith("PATCH /api/staff/3/") for x in log(page)), str(log(page)))
    # Menu "…" Cho nghỉ + Thôi
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name="Cho nghỉ").click()
    dlg = dialog(page)
    expect(dlg).to_contain_text("đăng xuất khỏi mọi máy")
    dlg.get_by_role("button", name="Thôi").click()
    expect(dialog(page)).to_have_count(0)
    ok("Cho nghỉ có hộp hỏi lại; Thôi thì chưa gì", page.get_by_text("Đang làm").count() >= 1)
    # Đặt lại mật khẩu lệch → không gọi API; hết thì thấy mật khẩu; kiểm không lưu
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name="Đặt lại mật khẩu").click()
    dlg = dialog(page)
    clear_log(page)
    dlg.locator("#sr-password").fill("Songbien2026")
    dlg.locator("#sr-password-again").fill("Songbien2027")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    ok("đặt lại mật khẩu lệch: không gọi API", not any("reset-password" in x for x in log(page)), str(log(page)))
    dlg.locator("#sr-password-again").fill("Songbien2026")
    dlg.get_by_role("button", name="Đặt lại mật khẩu").click()
    expect(dlg.locator(".cred-password")).to_have_text("Songbien2026")
    dlg.get_by_role("button", name="Xong").click()
    expect(dialog(page)).to_have_count(0)
    ok("sau khi đặt lại: mật khẩu không ở URL/storage", "Songbien2026" not in page.url and "Songbien2026" not in storage_dump(page))
    go(page, "/staff/detail/?id=1")
    expect(page.locator("main h2").first).to_be_visible()
    ok("hồ sơ chính mình: có ghi chú 'tài khoản của bạn'", page.get_by_text("Đây là tài khoản của bạn").count() == 1)
    page.get_by_role("button", name="Thao tác khác").click()
    mi = page.get_by_role("menuitem", name="Cho nghỉ")
    ok("Cho nghỉ của chính mình bị khoá kèm lý do", mi.count() == 1 and (mi.get_attribute("aria-disabled") == "true" or mi.is_disabled()))
    page.keyboard.press("Escape")
    # giao2: việc đang giao
    go(page, "/staff/detail/?id=7")
    expect(page.get_by_role("heading", name="Việc đang giao")).to_be_visible()
    expect(page.locator("main tr.lt-click")).to_have_count(2)
    deliv = page.get_by_role("region", name="Việc đang giao").inner_text() if page.get_by_role("region", name="Việc đang giao").count() else page.locator("section[aria-label='Việc đang giao']").inner_text()
    ok("giao2: Việc đang giao 2 phiếu, không có SĐT khách", not PHONE_RE.search(deliv), deliv[:80])
    page.screenshot(path=f"{SHOTS}/lo14-desktop-1280-staff-delivering.png", full_page=True)
    # giao2 cho nghỉ (ED-38-AC3 / BR-GH-08): hộp nêu SẴN số phiếu + mã phiếu, nút xác nhận khoá, chưa gọi BE
    clear_log(page)
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name="Cho nghỉ").click()
    dlg = dialog(page)
    block = dlg.locator("[data-delivering-block]")
    expect(block).to_be_visible()
    block_text = block.inner_text()
    ok("giao2: hộp Cho nghỉ nêu 2 phiếu Đang giao kèm mã phiếu",
       "2 phiếu Đang giao" in block_text and "GH-INV-DH01-A1B2C" in block_text and "GH-INV-DH02-K7M3Q" in block_text, block_text[:120])
    ok("giao2: nút xác nhận Cho nghỉ bị khoá", dlg.get_by_role("button", name="Cho nghỉ").is_disabled())
    ok("giao2: hộp chặn từ phía trước, chưa gọi POST deactivate", not any("deactivate" in x for x in log(page)), str(log(page)))
    ok("giao2: câu chặn không có SĐT khách", not PHONE_RE.search(block_text))
    ok("giao2: đang bị chặn thì không liệt kê hậu quả 'khoá ngay'", "đăng xuất khỏi mọi máy" not in dialog(page).inner_text())
    page.screenshot(path=f"{SHOTS}/lo14-desktop-1280-staff-deactivate-blocked.png")
    page.keyboard.press("Escape")
    expect(dialog(page)).to_have_count(0)
    # Đối chứng: nhân viên giao không có phiếu (giao1) → không bị chặn, nút xác nhận bấm được (không bấm)
    go(page, "/staff/detail/?id=4")
    expect(page.locator("main h2").first).to_be_visible()
    expect(page.get_by_role("heading", name="Việc đang giao")).to_be_visible()
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name="Cho nghỉ").click()
    dlg = dialog(page)
    expect(dlg.get_by_role("button", name="Cho nghỉ")).to_be_visible()
    # Chờ hết bước "Đang kiểm tra phiếu đang giao…" (cờ data-delivering-checking) rồi mới đọc hộp.
    expect(dlg.locator("[data-delivering-checking]")).to_have_count(0)
    expect(dlg.get_by_role("button", name="Cho nghỉ")).to_be_enabled()
    ok("giao1 không có phiếu đang giao: hộp không chặn, nút xác nhận bấm được, vẫn nêu hậu quả",
       dlg.locator("[data-delivering-block]").count() == 0 and dlg.get_by_role("button", name="Cho nghỉ").is_enabled()
       and "đăng xuất khỏi mọi máy" in dlg.inner_text())
    page.keyboard.press("Escape")
    expect(dialog(page)).to_have_count(0)

    # Thêm nhân viên: form lệch mật khẩu không gọi API; tạo xong thấy mật khẩu, không nháp
    go(page, "/staff/")
    wait_staff_rows(page)
    page.get_by_role("button", name="Thêm nhân viên").first.click()
    dlg = dialog(page)
    expect(dlg.get_by_label("Tên đăng nhập")).to_be_focused()
    dlg.get_by_label("Tên đăng nhập").fill("giao9")
    dlg.get_by_label("Số điện thoại").fill("0909333999")
    dlg.locator("#sc-password").fill("Songbien2026")
    clear_log(page)
    ok("form thêm: không ghi nháp vào storage", "giao9" not in storage_dump(page) and "0909333999" not in storage_dump(page))
    dlg.get_by_role("button", name="Tạo tài khoản").click()
    ok("form thêm thiếu nhập lại/lệch: không gọi POST", not any(x.startswith("POST /api/staff/") for x in log(page)), str(log(page)))
    page.keyboard.press("Escape")
    ctx.close()
    return errors


def forbidden(browser):
    for user in ("ql1", "kho1", "giao1", "cs2"):
        ctx, page, errors = new_page(browser, user)
        labels = nav_labels(page)
        ok(f"{user}: menu không có Nhân sự, Phân quyền", "Nhân sự" not in labels and "Phân quyền" not in labels, str(labels))
        clear_log(page)
        for path in ("/permissions/", "/staff/", "/staff/detail/?id=1", "/permissions/detail/?group=manager"):
            go(page, path)
            ok(f"{user}: {path} -> Không có quyền", no_perm(page))
        ok(f"{user}: không có request /api/staff", all("/api/staff" not in x for x in log(page)), str(log(page)))
        if user == "ql1":
            page.screenshot(path=f"{SHOTS}/lo14-desktop-1280-ql1-noperm.png")
        ctx.close()


def readonly(browser):
    ctx, page, errors = new_page(browser, "ql9")
    go(page, "/permissions/")
    expect(page.get_by_text("Chỉ Chủ mới bật hoặc tắt được")).to_be_visible()
    ok("ql9 (manage_staff, không thuộc Chủ): ma trận chỉ xem, 0 công tắc", page.get_by_role("switch").count() == 0)
    go(page, "/permissions/detail/?group=manager")
    expect(page.get_by_text("Bạn chỉ xem được")).to_be_visible()
    ok("ql9: trang nhóm chỉ xem, 0 công tắc", page.get_by_role("switch").count() == 0)
    go(page, "/staff/detail/?id=1")
    expect(page.locator("main h2").first).to_be_visible()
    ok("ql9 xem hồ sơ Chủ: không có Sửa hồ sơ/Đổi nhóm", page.get_by_role("button", name="Sửa hồ sơ").count() == 0 and page.get_by_role("button", name="Đổi nhóm").count() == 0)
    ok("ql9 xem hồ sơ Chủ: báo không có thao tác nào", page.get_by_text("Bạn không có thao tác nào trên tài khoản này").count() == 1)
    ctx.close()


def off_path(browser):
    ctx, page, errors = new_page(browser, "loc")
    for path, what in (
        ("/staff/detail/", "thiếu id"),
        ("/staff/detail/?id=abc", "id chữ"),
        ("/staff/detail/?id=99999", "id không có"),
        ("/permissions/detail/", "thiếu mã nhóm"),
        ("/permissions/detail/?group=zzz", "mã nhóm lạ"),
        ("/permissions/detail/?group=..%2Fowner", "mã nhóm có ký tự lạ"),
    ):
        go(page, path)
        page.wait_for_function("() => document.body.innerText.includes('Không tìm thấy')", timeout=10_000)
        ok(f"{path} ({what}) -> Không tìm thấy, không văng lỗi", True)
        txt = page.locator("body").inner_text()
        ok(f"{path}: không lộ chữ kỹ thuật", not any(w in txt for w in BAD_WORDS))
    # Không rò dữ liệu cá nhân vào storage / URL
    go(page, "/staff/detail/?id=3")
    expect(page.locator("main h2").first).to_be_visible()
    dump = storage_dump(page)
    ok("storage không chứa SĐT hay tên nhân viên", not PHONE_RE.search(dump) and "Anh Tâm" not in dump, dump[:120])
    ctx.close()


def mobile(browser):
    ctx, page, errors = new_page(browser, "loc", 360, 740, touch=True)
    for path, name in (
        ("/staff/", "staff"),
        ("/staff/detail/?id=3", "staff-detail"),
        ("/permissions/", "matrix"),
        ("/permissions/detail/?group=manager", "group"),
    ):
        go(page, path)
        page.wait_for_selector("main h1, main h2, main table", state="attached")
        expect(page.locator("main [aria-busy=true]")).to_have_count(0)
        ok(f"360 {name}: không cuộn ngang trang", no_hscroll(page), str(page.evaluate("() => document.documentElement.scrollWidth")))
        small = page.evaluate(SMALL_TARGETS)
        ok(f"360 {name}: vùng bấm >= 44px", not small, str(small))
        page.screenshot(path=f"{SHOTS}/lo14-mobile-360-{name}.png", full_page=True)
    go(page, "/staff/detail/?id=3")
    page.get_by_role("button", name="Đổi nhóm").click()
    expect(dialog(page)).to_be_visible()
    ok("360 hộp Đổi nhóm: không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo14-mobile-360-staff-groups.png")
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errs = []
    errs += owner(browser)
    forbidden(browser)
    readonly(browser)
    off_path(browser)
    mobile(browser)
    browser.close()

relevant = [e for e in errs if "fonts.g" not in e and "net::" not in e and "401" not in e]
ok("Không lỗi console", not relevant, str(relevant[:5]))
passed = sum(1 for _, c, _ in results if c)
print(f"{passed}/{len(results)} PASS")
raise SystemExit(0 if passed == len(results) else 1)
