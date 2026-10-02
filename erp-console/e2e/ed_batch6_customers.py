# E2E ERP theo design, Lô 6 (Khách hàng ED-14): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/ed_batch6_customers.py      # tắt server sau khi xong
# Kiểm: kho1 / giao1 / cs2 không thấy menu Khách hàng và vào URL thì "Không có quyền" · loc và ql1 xem và sửa được ·
# trang chi tiết KHÔNG có khối AI · số điện thoại không có ô sửa (khoá) · PATCH chỉ gửi trường đổi, không bao giờ có phone ·
# tìm kiếm (không thấy -> Xoá tìm kiếm), sắp xếp, tải thêm · lỗi tải, danh sách rỗng, chi tiết lỗi, lưu lỗi giữ chữ đã gõ ·
# id sai / không có -> Không tìm thấy · tên khách, SĐT, địa chỉ không nằm trong URL / localStorage / sessionStorage / console ·
# 360px không cuộn ngang.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)
PHONE_RE = re.compile(r"0900000\d{3}")


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
    # Lỗi HTTP 4xx/5xx chủ ý (ca lạ) tự sinh dòng "Failed to load resource": không tính.
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, user)
    return ctx, page, errors


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])")


def nav_labels(page):
    return [t.strip() for t in page.locator(".nav a").all_inner_texts()]


def set_mode(page, mode):
    page.evaluate("(m) => window.__caveMock.customers(m)", mode)


def roles(browser):
    for user in ("kho1", "giao1", "cs2"):
        ctx, page, errors = new_page(browser, user)
        ok(f"{user}: menu không có Khách hàng", not any("Khách hàng" in t for t in nav_labels(page)), str(nav_labels(page)))
        go(page, "/customers/")
        ok(f"{user}: /customers/ hiện 'Không có quyền'", page.get_by_role("heading", name="Không có quyền").count() >= 1)
        ok(f"{user}: /customers/ không vẽ bảng khách", page.locator("main table").count() == 0 and not PHONE_RE.search(page.inner_text("main")))
        go(page, "/customers/detail/?id=3")
        ok(f"{user}: /customers/detail/ hiện 'Không có quyền', không lộ tên/số", page.get_by_role("heading", name="Không có quyền").count() >= 1 and not PHONE_RE.search(page.inner_text("main")) and "Khách Thử" not in page.inner_text("main"))
        ok(f"{user}: không console.error", errors == [], str(errors))
        ctx.close()

    for user in ("loc", "ql1"):
        ctx, page, errors = new_page(browser, user)
        ok(f"{user}: menu có Khách hàng, bấm được", any("Khách hàng" in t for t in nav_labels(page)))
        page.locator(".nav a", has_text="Khách hàng").first.click()
        page.wait_for_url(re.compile(r"/customers/?$"))
        settle(page)
        body = page.inner_text("main")
        ok(f"{user}: danh sách có cột Khách hàng · Số điện thoại · Số đơn · Đơn huỷ · Tổng đã mua · Đơn gần nhất", all(h in body for h in ("Khách hàng", "Số điện thoại", "Số đơn", "Đơn huỷ", "Tổng đã mua", "Đơn gần nhất")))
        ok(f"{user}: tiền dạng 'n.nnn đ'", re.search(r"\d\.\d{3} đ", body) is not None)
        ok(f"{user}: thời gian dạng dd/mm/yyyy hh:mm", re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", body) is not None)
        ok(f"{user}: không có từ viết tắt SĐT", "SĐT" not in body)
        ok(f"{user}: không console.error", errors == [], str(errors))
        ctx.close()


def list_behaviour(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/customers/")
    ok("Danh sách: mở đầu 20 / 27 khách và có nút Tải thêm", "20 / 27" in page.inner_text("main") and page.get_by_role("button", name="Tải thêm khách").count() == 1)
    page.get_by_role("button", name="Tải thêm khách").click()
    page.wait_for_function("() => document.body.innerText.includes('27 / 27')")
    ok("Tải thêm: đủ 27 khách, hết nút Tải thêm", "27 / 27" in page.inner_text("main") and page.get_by_role("button", name="Tải thêm khách").count() == 0)

    # Tìm kiếm: tên bỏ dấu, ô trống -> khôi phục, không thấy -> Xoá tìm kiếm
    box = page.get_by_role("searchbox", name="Tìm khách hàng")
    box.fill("khach thu d")
    page.wait_for_function("() => document.body.innerText.includes('Khách Thử D') && !document.body.innerText.includes('Khách Thử E')")
    ok("Tìm kiếm: 'khach thu d' (bỏ dấu) ra Khách Thử D", "Khách Thử D" in page.inner_text("main"))
    ok("Tìm kiếm: từ khoá KHÔNG nằm trong URL", "khach" not in page.url and page.url.rstrip("/").endswith("/customers"), page.url)
    box.fill("zzzz-khong-co")
    page.wait_for_function("() => document.body.innerText.includes('Xoá tìm kiếm')")
    ok("Tìm kiếm không khớp: có 'Xoá tìm kiếm', không bảng cũ", page.locator("main table tbody tr").count() == 0)
    page.locator("main").get_by_role("button", name="Xoá tìm kiếm").first.click()
    page.wait_for_function("() => document.body.innerText.includes('Khách Thử A')")
    ok("Xoá tìm kiếm: danh sách đầy đủ trở lại", "Khách Thử A" in page.inner_text("main"))
    box.fill("090")
    page.wait_for_function("() => document.body.innerText.includes('Xoá tìm kiếm')")
    ok("Tìm '090' (dưới 4 chữ số) không dò theo số điện thoại", page.locator("main table tbody tr").count() == 0)
    box.fill("")
    page.wait_for_function("() => document.body.innerText.includes('Khách Thử A')")

    # Sắp xếp
    page.get_by_label("Sắp xếp").select_option(label="Tên từ A đến Z")
    page.wait_for_function("() => window.__caveMock.pending() === 0")
    first = page.locator("main table tbody tr").first.inner_text()
    ok("Sắp xếp theo tên A đến Z: hàng đầu là Khách Thử A", "Khách Thử A" in first, first[:40])
    page.get_by_label("Sắp xếp").select_option(label="Tổng đã mua nhiều nhất")
    page.wait_for_function("() => window.__caveMock.pending() === 0")
    ok("Sắp xếp theo tổng đã mua: hàng đầu là Khách Thử D (3.055.000 đ)", "3.055.000" in page.locator("main table tbody tr").first.inner_text())
    ok("Sắp xếp: URL không đổi theo (chỉ trạng thái nội bộ)", page.url.rstrip("/").endswith("/customers"), page.url)

    # Mở chi tiết bằng bấm dòng
    page.locator("main table tbody tr").first.click()
    page.wait_for_url(re.compile(r"/customers/detail/\?id=\d+$"))
    ok("Bấm dòng: URL chỉ mang id số", re.search(r"\?id=\d+$", page.url) is not None, page.url)
    ok("Danh sách: storage không có tên/số khách", not PHONE_RE.search(storage_dump(page)) and "Khách Thử" not in storage_dump(page))
    ok("Danh sách: không console.error", errors == [], str(errors))
    page.screenshot(path=f"{SHOTS}/lo6_desktop_detail.png", full_page=True)
    ctx.close()


def detail_behaviour(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/customers/detail/?id=3")
    body = page.inner_text("main")
    ok("Chi tiết: có tên khách ở tiêu đề", page.locator("main h2").first.inner_text().startswith("Khách Thử"), page.locator("main h2").first.inner_text())
    ok("Chi tiết: KHÔNG có khối AI", page.locator("[data-ai-block], [aria-label*='AI'], [data-testid*='ai']").count() == 0 and "Trợ lý" not in body and "Gợi ý của AI" not in body)
    ok("Chi tiết: số điện thoại hiện đủ và có biểu tượng khoá", PHONE_RE.search(body) is not None and page.locator("[data-kind='locked']", has_text="Số điện thoại").count() == 1)
    ok("Chi tiết: số điện thoại KHÔNG có nút sửa", page.get_by_label("Sửa số điện thoại").count() == 0)
    ok("Chi tiết: tên · địa chỉ · ghi chú có nút sửa", all(page.get_by_label(f"Sửa {l}").count() == 1 for l in ("tên", "địa chỉ giao mặc định", "ghi chú")))
    ok("Chi tiết: có Đơn hàng, Phiếu hoàn, Dòng thời gian", all(t in body.upper() for t in ("ĐƠN HÀNG", "PHIẾU HOÀN", "DÒNG THỜI GIAN")))
    ok("Chi tiết: URL chỉ id", page.url.endswith("?id=3"), page.url)

    # Sửa nội tuyến ghi chú
    page.get_by_label("Sửa ghi chú").click()
    page.locator("main form input, main form textarea").first.fill("Ghi chú thử nghiệm Lô 6")
    page.locator("main form").get_by_role("button", name="Lưu").click()
    page.wait_for_function("() => document.body.innerText.includes('Đã lưu thông tin khách.')")
    settle(page)
    ok("Sửa ghi chú: hiện toast và giá trị mới", "Ghi chú thử nghiệm Lô 6" in page.inner_text("main"))
    ok("Sửa ghi chú: dòng thời gian có 'Cập nhật hồ sơ khách'", "Cập nhật hồ sơ khách" in page.inner_text("main"))
    ok("Sửa ghi chú: ghi chú không nằm trong storage", "Ghi chú thử nghiệm" not in storage_dump(page))
    req = [x for x in page.evaluate("() => window.__caveMock.log.slice()") if x.startswith("PATCH")]
    ok("Sửa ghi chú: PATCH chỉ gửi trường đổi (không có phone)", len(req) >= 1 and all("phone" not in x for x in req), str(req))

    # Sửa tên: để trống bị chặn, Esc bỏ
    page.get_by_label("Sửa tên").click()
    page.locator("main form [name], main form input, main form textarea").first.fill("   ")
    page.locator("main form").get_by_role("button", name="Lưu").click()
    ok("Sửa tên: để trống thì chặn tại chỗ (ô sửa dùng câu chung 'Nhập giá trị cho ô này.')", page.get_by_text("Nhập giá trị cho ô này.").count() >= 1)
    page.locator("main form [name], main form input, main form textarea").first.press("Escape")
    ok("Sửa tên: Esc bỏ sửa, tên cũ còn nguyên", page.locator("main h2").first.inner_text().startswith("Khách Thử") and page.locator("main form").count() == 0)

    # Hộp Sửa thông tin
    page.get_by_role("button", name="Sửa thông tin").first.click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    ok("Hộp Sửa thông tin: có Tên · Địa chỉ · Ghi chú, KHÔNG có ô số điện thoại", dlg.get_by_label("Tên").count() == 1 and dlg.get_by_label("Số điện thoại").count() == 0 and dlg.get_by_label("Địa chỉ giao mặc định").count() == 1)
    dlg.get_by_role("button", name="Lưu thay đổi").click()
    ok("Hộp Sửa thông tin: không đổi gì thì báo 'Chưa có gì thay đổi'", dlg.get_by_text("Chưa có gì thay đổi để lưu.").count() >= 1)
    dlg.get_by_label("Địa chỉ giao mặc định").fill("Số 1 Đường Thử, Vũng Tàu")
    dlg.get_by_role("button", name="Lưu thay đổi").click()
    page.wait_for_function("() => document.body.innerText.includes('Đã lưu thông tin khách.')")
    settle(page)
    ok("Hộp Sửa thông tin: lưu địa chỉ, hộp đóng, giá trị hiện", page.get_by_role("dialog").count() == 0 and "Số 1 Đường Thử" in page.inner_text("main"))
    ok("Hộp Sửa thông tin: địa chỉ không nằm trong storage/URL", "Số 1 Đường Thử" not in storage_dump(page) and "Th%E1%BB%AD" not in page.url)

    # Liên kết sang đơn
    link = page.locator("main table tbody a, main table tbody tr").first
    ok("Chi tiết: bảng đơn có dòng bấm được", page.locator("main table").first.locator("tbody tr").count() >= 1)
    ok("Chi tiết: không console.error", errors == [], str(errors))
    ctx.close()

    # ql1 cũng sửa được
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/customers/detail/?id=4")
    ok("ql1: có nút Sửa thông tin và sửa được ghi chú", page.get_by_role("button", name="Sửa thông tin").count() >= 1 and page.get_by_label("Sửa ghi chú").count() == 1)
    ok("ql1: số điện thoại vẫn khoá", page.get_by_label("Sửa số điện thoại").count() == 0)
    ctx.close()


def off_happy_path(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/customers/detail/?id=abc")
    ok("Ca lạ: ?id=abc hiện Không tìm thấy, không văng", page.get_by_role("heading", name=re.compile("Không tìm thấy")).count() >= 1)
    go(page, "/customers/detail/")
    ok("Ca lạ: thiếu ?id hiện Không tìm thấy", page.get_by_role("heading", name=re.compile("Không tìm thấy")).count() >= 1)
    go(page, "/customers/detail/?id=999999")
    ok("Ca lạ: id không có hiện Không tìm thấy", page.get_by_role("heading", name=re.compile("Không tìm thấy")).count() >= 1)
    go(page, "/customers/detail/?id=0")
    ok("Ca lạ: ?id=0 hiện Không tìm thấy", page.get_by_role("heading", name=re.compile("Không tìm thấy")).count() >= 1)

    set_mode(page, "fail")
    go(page, "/customers/")
    ok("Lỗi tải danh sách: có thông báo lỗi và nút Thử lại", page.get_by_role("button", name=re.compile("Thử lại")).count() >= 1 and not PHONE_RE.search(page.inner_text("main")))
    set_mode(page, "ok")
    page.get_by_role("button", name=re.compile("Thử lại")).first.click()
    page.wait_for_function("() => document.body.innerText.includes('Khách Thử A')")
    ok("Thử lại: danh sách hiện lại", "Khách Thử A" in page.inner_text("main"))

    set_mode(page, "empty")
    go(page, "/customers/")
    ok("Danh sách rỗng: 'Chưa có khách hàng nào'", "Chưa có khách hàng nào" in page.inner_text("main"))

    set_mode(page, "forbidden")
    go(page, "/customers/")
    ok("BE trả 403: hiện 'Không có quyền'", page.get_by_role("heading", name="Không có quyền").count() >= 1)

    set_mode(page, "detailfail")
    go(page, "/customers/detail/?id=3")
    ok("Lỗi tải chi tiết: có Thử lại, không lộ dữ liệu", page.get_by_role("button", name=re.compile("Thử lại")).count() >= 1 and not PHONE_RE.search(page.inner_text("main")))

    set_mode(page, "patchfail")
    go(page, "/customers/detail/?id=3")
    page.get_by_label("Sửa ghi chú").click()
    page.locator("main form input, main form textarea").first.fill("Chữ đã gõ không được mất")
    page.locator("main form").get_by_role("button", name="Lưu").click()
    page.wait_for_function("() => window.__caveMock.pending() === 0")
    ok("Lưu lỗi: ô vẫn mở và giữ chữ đã gõ", page.locator("main form input, main form textarea").first.input_value() == "Chữ đã gõ không được mất")
    ok("Lưu lỗi: nút đổi thành 'Thử lại'", page.locator("main form").get_by_role("button", name="Thử lại").count() == 1)
    ok("Lưu lỗi: chữ đã gõ không nằm trong storage", "Chữ đã gõ" not in storage_dump(page))
    set_mode(page, "ok")
    page.locator("main form").get_by_role("button", name="Thử lại").click()
    page.wait_for_function("() => document.body.innerText.includes('Đã lưu thông tin khách.')")
    ok("Thử lại sau lỗi: lưu được", True)
    ok("Ca lạ: không console.error (không tính HTTP 4xx/5xx chủ ý)", errors == [], str(errors))
    page.evaluate("() => window.localStorage.removeItem('cave_erp_mock_customers_mode')")
    ctx.close()


def mobile(browser):
    ctx, page, errors = new_page(browser, "loc", 360, 740, touch=True)
    go(page, "/customers/")
    ok("360px /customers/: không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo6_mobile_list.png")
    go(page, "/customers/detail/?id=4")
    ok("360px /customers/detail/: không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo6_mobile_detail.png", full_page=True)
    page.get_by_role("button", name="Sửa thông tin").first.click()
    expect(page.get_by_role("dialog")).to_be_visible()
    ok("360px hộp Sửa thông tin: không cuộn ngang, trong màn hình", no_hscroll(page) and page.get_by_role("dialog").bounding_box()["width"] <= 361)
    page.screenshot(path=f"{SHOTS}/lo6_mobile_edit.png")
    ok("360px: không console.error", errors == [], str(errors))
    ctx.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            roles(browser)
            list_behaviour(browser)
            detail_behaviour(browser)
            off_happy_path(browser)
            mobile(browser)
        finally:
            browser.close()
    fails = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(fails)}/{len(results)} PASS")
    sys.exit(1 if fails else 0)


main()
