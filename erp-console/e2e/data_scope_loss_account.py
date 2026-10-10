# E2E ERP, phạm vi dữ liệu cấu hình (PV-13 mất quyền giữa chừng, PV-14 khối "Dữ liệu bạn xem được", §2.7 chữ ô khách theo lý do che).
# Chạy trên bản build MOCK phục vụ tĩnh:
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/data_scope_loss_account.py      # tắt server sau khi xong
# Kiểm: màn Tài khoản có khối 8 dòng cho NV giao / NV kho kiêm giao / Chủ / superuser, không nút, không ô nhập, 360px không cuộn ngang ·
# đơn đã mở, Chủ bị thu hẹp quyền rồi "Tải lại" (qua banner 409) thì màn mất quyền, XOÁ tên/SĐT/địa chỉ khỏi DOM, không log ra console ·
# mở lần đầu mục ngoài phạm vi vẫn là "Không tìm thấy trang này" · tải lại bị 500 thì giữ màn, không có chữ "không còn quyền" ·
# thiếu V2: ô khách ghi "Đã ẩn (không có quyền xem thông tin khách)" và danh sách hoá đơn bán không có cột Khách; có V2 thì có.
# Mock chỉ thu hẹp được ở màn Đơn (phạm vi theo nhóm); các màn còn lại (phiếu nhập, phiếu giao, khách, gọi xác nhận, hàng hoàn, phiếu hoàn tiền)
# QA kiểm trên BE thật, còn vitest kiểm hook (useDetail, useCustomerDetail, useReturnDetail) và hàm AC2.
import os
import re

from playwright.sync_api import expect, sync_playwright

from e2e_support import finish

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)
LOST_TITLE = "Bạn không còn quyền xem mục này."
NOT_PERMITTED = "Đã ẩn (không có quyền xem thông tin khách)"
# Khách giả của đơn mẫu 101 (mock): đúng cặp tên/SĐT trong dữ liệu mẫu, không phải dữ liệu thật.
CUSTOMER_NAME = "Chị Hoa"
CUSTOMER_PHONE = "0901234567"


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, "" if cond else extra, flush=True)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)


def idle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    idle(page)


def new_page(browser, user, w=1280, h=900, dark=False, console=None):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", color_scheme="dark" if dark else "light")
    page = ctx.new_page()
    if console is not None:
        page.on("console", lambda m: console.append(m.text))
        page.on("pageerror", lambda e: console.append(str(e)))
    login(page, user)
    return ctx, page


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def patch_user(page, username, patch):
    page.evaluate("([u, p]) => window.__caveMock.patchUser(u, p)", [username, patch])


def block(page):
    return page.locator("[data-testid=data-scopes]")


def row(page, key):
    return block(page).locator(f"[data-scope={key}]")


def open_account(page):
    go(page, "/account/")
    expect(block(page)).to_be_visible()


def lose_scope_on_order(page, oid):
    """Mở đơn, bấm "Xác nhận đã nhận tiền" nhưng người khác vừa xử lý (409), rồi bấm "Tải lại" trong banner. Trước khi bấm, `before` đã chạy."""
    go(page, f"/orders/detail/?id={oid}")
    expect(page.locator("main header h2")).to_be_visible()
    idle(page)
    page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg = page.get_by_role("dialog", name="Xác nhận đã nhận tiền")
    expect(dlg).to_be_visible()
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799777")
    page.evaluate("() => window.__caveMock.conflictNext()")
    dlg.locator("button[type=submit]").click()
    expect(page.locator("[data-conflict-banner]")).to_be_visible()
    idle(page)


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ---------- PV-14: khối "Dữ liệu bạn xem được" ----------
    ctx, page = new_page(browser, "giao1", w=360, h=800)
    open_account(page)
    b = block(page)
    ok("PV-14-AC4: khối có tiêu đề 'Dữ liệu bạn xem được' và câu dẫn", "Dữ liệu bạn xem được" in b.inner_text() and "Chỉ để xem, không đổi ở đây." in b.inner_text())
    ok("PV-14-AC3: đủ 8 dòng", b.locator("[data-scope]").count() == 8, str(b.locator("[data-scope]").count()))
    ok("PV-14-AC4: NV giao, Đơn hàng 'Đơn có phiếu giao gán cho tôi' theo nhóm Nhân viên giao", "Đơn có phiếu giao gán cho tôi" in row(page, "orders").inner_text() and "theo nhóm Nhân viên giao" in row(page, "orders").inner_text(), row(page, "orders").inner_text())
    ok("PV-14-AC3: NV giao, Hoá đơn bán 'Không xem', không chữ phụ", "Không xem" in row(page, "invoices").inner_text() and "theo nhóm" not in row(page, "invoices").inner_text() and "theo quyền" not in row(page, "invoices").inner_text(), row(page, "invoices").inner_text())
    ok("PV-14-AC3: NV giao không xem Phiếu nhập, Gọi xác nhận, Nhật ký", all("Không xem" in row(page, k).inner_text() for k in ("receipts", "confirmation", "audit_log")))
    ok("PV-14: chỉ để xem, không có nút, ô nhập hay liên kết trong khối", b.locator("button, input, select, textarea, a").count() == 0)
    ok("PV-14: không có dòng 'Toàn bộ' cho người thường", b.locator("[data-testid=data-scope-superuser]").count() == 0)
    ok("PV-14-AC4: 360px không cuộn ngang", no_hscroll(page))
    b.screenshot(path=f"{SHOTS}/pv14-giao1-360-light.png")
    ctx.close()

    ctx, page = new_page(browser, "giao1", w=360, h=800, dark=True)
    open_account(page)
    ok("PV-14: tối, 360px không cuộn ngang", no_hscroll(page))
    block(page).screenshot(path=f"{SHOTS}/pv14-giao1-360-dark.png")
    ctx.close()

    ctx, page = new_page(browser, "kho1", w=1280, h=900)
    open_account(page)
    ok("PV-14-AC1: NV kho kiêm giao, Đơn hàng lấy rộng nhất 'Tất cả đơn' theo nhóm Nhân viên kho", "Tất cả đơn" in row(page, "orders").inner_text() and "theo nhóm Nhân viên kho" in row(page, "orders").inner_text(), row(page, "orders").inner_text())
    ok("PV-14-AC1: Hoá đơn bán 'Hoá đơn của tất cả đơn' theo nhóm Nhân viên kho", "Hoá đơn của tất cả đơn" in row(page, "invoices").inner_text() and "theo nhóm Nhân viên kho" in row(page, "invoices").inner_text())
    ok("PV-14-AC1: Khách hàng theo nhóm Nhân viên giao (nhóm cho giá trị đó)", "theo nhóm Nhân viên giao" in row(page, "customers").inner_text(), row(page, "customers").inner_text())
    ok("PV-14: 1280px không cuộn ngang", no_hscroll(page))
    block(page).screenshot(path=f"{SHOTS}/pv14-kho1-1280-light.png")
    # BR-PQ-36: quyền đổi thì đọc lại me mới thấy. Thu nhóm xuống chỉ còn NV giao rồi bấm 'Tải lại quyền'.
    patch_user(page, "kho1", {"groups": ["delivery_staff"]})
    page.get_by_role("button", name="Tải lại quyền").click()
    expect(row(page, "orders")).to_contain_text("Đơn có phiếu giao gán cho tôi")
    ok("PV-14: sau 'Tải lại quyền' dòng Đơn hàng đổi theo nhóm mới", "theo nhóm Nhân viên giao" in row(page, "orders").inner_text(), row(page, "orders").inner_text())
    ctx.close()

    ctx, page = new_page(browser, "loc", w=1280, h=900)
    open_account(page)
    ok("PV-14: Chủ, Gọi xác nhận 'Mọi phiếu chờ gọi' theo nhóm Chủ", "Mọi phiếu chờ gọi" in row(page, "confirmation").inner_text() and "theo nhóm Chủ" in row(page, "confirmation").inner_text(), row(page, "confirmation").inner_text())
    ok("PV-14: Chủ xem Nhật ký 'Tất cả'", "Tất cả" in row(page, "audit_log").inner_text())
    ctx.close()

    ctx, page = new_page(browser, "admin", w=360, h=800)
    open_account(page)
    ok("PV-14 (02c G.3): superuser có dòng 'Toàn bộ (quản trị hệ thống)'", "Toàn bộ (quản trị hệ thống)" in block(page).locator("[data-testid=data-scope-superuser]").inner_text())
    ok("PV-14: superuser, mọi dòng rộng nhất và không chữ phụ", "Tất cả đơn" in row(page, "orders").inner_text() and "Mọi phiếu chờ gọi" in row(page, "confirmation").inner_text() and "theo nhóm" not in block(page).inner_text() and "theo quyền" not in block(page).inner_text())
    ok("PV-14: superuser 360px không cuộn ngang", no_hscroll(page))
    block(page).screenshot(path=f"{SHOTS}/pv14-admin-360-light.png")
    ctx.close()

    # ---------- PV-13: mất quyền giữa chừng ----------
    console = []
    ctx, page = new_page(browser, "loc", w=1280, h=900, console=console)
    lose_scope_on_order(page, 101)
    ok("PV-13 tiền đề: đơn đang mở có tên khách", CUSTOMER_NAME in page.locator("main").inner_text())
    order_code = page.locator("main header h2").inner_text().strip()
    patch_user(page, "loc", {"groups": ["delivery_staff"]})  # Chủ bị thu về phạm vi 'đơn gán cho tôi'
    page.locator("[data-conflict-banner]").get_by_role("button").first.click()
    expect(page.get_by_text(LOST_TITLE)).to_be_visible()
    idle(page)
    body = page.locator("body").inner_text()
    ok("PV-13-AC1: tải lại bị 404 → 'Bạn không còn quyền xem mục này.' (h2, role=alert)", page.locator("h2[role=alert]").inner_text().strip() == LOST_TITLE)
    ok("PV-13-AC1: có câu gợi ý nhờ Quản lý hoặc Chủ vựa", "nhờ Quản lý hoặc Chủ vựa" in body)
    ok("PV-13-AC1: nút 'Về danh sách' trỏ về /orders/", (page.get_by_role("link", name="Về danh sách").get_attribute("href") or "").rstrip("/") .endswith("/orders"), str(page.get_by_role("link", name="Về danh sách").get_attribute("href")))
    ok("PV-13-AC2: không có câu 'Phiếu tạo từ hôm trước' ở màn đơn", "Phiếu tạo từ hôm trước" not in body)
    ok("PV-13-AC5: DOM không còn tên, SĐT của khách", CUSTOMER_NAME not in body and CUSTOMER_PHONE not in body and "0901 234 567" not in body, body[:200])
    ok("PV-13-AC5: không còn mã đơn, bảng hàng, dòng thời gian, khối AI", page.locator("main header h2").count() == 0 and page.locator("[data-testid=order-refund-summary]").count() == 0 and bool(order_code) and order_code not in body, order_code)
    ok("PV-13-AC5: console không có tên/SĐT khách", not any(CUSTOMER_NAME in m or CUSTOMER_PHONE in m for m in console), str(console)[:200])
    ok("PV-13-AC5: URL chỉ có id, storage thật không chứa tên/SĐT", CUSTOMER_PHONE not in page.url and CUSTOMER_NAME not in page.url and CUSTOMER_PHONE not in page.evaluate("() => JSON.stringify(Object.entries(localStorage).filter((e) => e[0] === 'cave_erp_token'))"))
    page.screenshot(path=f"{SHOTS}/pv13-scope-lost-1280-light.png")
    page.get_by_role("link", name="Về danh sách").click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    ok("PV-13-AC1: bấm 'Về danh sách' sang /orders/", True)
    ctx.close()

    ctx, page = new_page(browser, "loc", w=360, h=800, dark=True)
    lose_scope_on_order(page, 101)
    patch_user(page, "loc", {"groups": ["delivery_staff"]})
    page.locator("[data-conflict-banner]").get_by_role("button").first.click()
    expect(page.get_by_text(LOST_TITLE)).to_be_visible()
    ok("PV-13: 360px tối, không cuộn ngang, nút 'Về danh sách' >= 44px", no_hscroll(page) and page.get_by_role("link", name="Về danh sách").bounding_box()["height"] >= 44)
    page.screenshot(path=f"{SHOTS}/pv13-scope-lost-360-dark.png")
    ctx.close()

    # Lần đầu bị 404 (ED-19-AC6): giữ 'Không tìm thấy trang này', không dùng câu mất quyền.
    ctx, page = new_page(browser, "cs2")  # CSKH kiêm giao: phạm vi hạn chế như NV giao nhưng có menu Đơn
    go(page, "/orders/detail/?id=101")
    expect(page.get_by_text("Không tìm thấy trang này")).to_be_visible()
    ok("PV-13 (ED-19-AC6): CSKH kiêm giao mở thẳng đơn ngoài phạm vi (lần đầu) → 'Không tìm thấy trang này'", LOST_TITLE not in page.locator("body").inner_text())
    ctx.close()

    # AC4: tải lại bị 500 → giữ màn, không dùng câu mất quyền.
    ctx, page = new_page(browser, "loc")
    lose_scope_on_order(page, 101)
    page.evaluate("() => window.__caveMock.orders('detailfail')")
    page.locator("[data-conflict-banner]").get_by_role("button").first.click()
    expect(page.get_by_role("button", name="Thử lại")).to_be_visible()
    idle(page)
    body = page.locator("body").inner_text()
    ok("PV-13-AC4: tải lại bị 500 → giữ màn đơn kèm lỗi và nút Thử lại", CUSTOMER_NAME in body and LOST_TITLE not in body)
    page.evaluate("() => window.__caveMock.orders('ok')")
    ctx.close()

    # ---------- §2.7: chữ ô khách theo lý do che ----------
    ctx, page = new_page(browser, "kho1")
    go(page, "/orders/")
    expect(page.locator("table tbody tr").first).to_be_visible()
    ok("§2.7: có V2 → danh sách đơn hiện tên khách", CUSTOMER_NAME in page.locator("main").inner_text() and NOT_PERMITTED not in page.locator("main").inner_text())
    go(page, "/accounting/sales-invoices/")
    expect(page.locator("table tbody tr").first).to_be_visible()
    ok("§2.7: có V2 → danh sách hoá đơn bán có cột Khách hàng (mở theo V2, không theo 'xem danh sách khách')", page.locator("table thead th", has_text="Khách hàng").count() == 1)
    patch_user(page, "kho1", {"denied_perms": ["sales.view_order_customer_info"]})
    go(page, "/orders/")
    expect(page.locator("table tbody tr").first).to_be_visible()
    main = page.locator("main").inner_text()
    ok("§2.7: thiếu V2 → danh sách đơn ghi 'Đã ẩn (không có quyền xem thông tin khách)', không lộ tên", NOT_PERMITTED in main and CUSTOMER_NAME not in main, main[:200])
    go(page, "/orders/detail/?id=101")
    expect(page.locator("main header h2")).to_be_visible()
    main = page.locator("main").inner_text()
    ok("§2.7: thiếu V2 → chi tiết đơn: tên, SĐT, địa chỉ đều ghi lý do, không lộ giá trị", main.count(NOT_PERMITTED) >= 3 and CUSTOMER_NAME not in main and CUSTOMER_PHONE not in main, main[:300])
    page.screenshot(path=f"{SHOTS}/pv13-not-permitted-1280-light.png")
    go(page, "/accounting/sales-invoices/")
    expect(page.locator("table tbody tr").first).to_be_visible()
    ok("§2.7: thiếu V2 → danh sách hoá đơn bán KHÔNG có cột Khách hàng", page.locator("table thead th", has_text="Khách hàng").count() == 0)
    ctx.close()

    # Người có phạm vi giao hạn chế (cs2): chữ che, nếu có, là 'quá 7 ngày', không phải 'không có quyền' (V2 còn bật).
    ctx, page = new_page(browser, "cs2")
    go(page, "/orders/")
    page.wait_for_timeout(300)
    main = page.locator("main").inner_text()
    ok("§2.7: người giao hạn chế vẫn có V2; chữ che (nếu có) là 'quá 7 ngày', không phải 'không có quyền'", NOT_PERMITTED not in main, main[:200])
    ctx.close()

    browser.close()

finish(results)
