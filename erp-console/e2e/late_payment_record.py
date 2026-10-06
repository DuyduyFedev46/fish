# E2E #15 FE "Ghi tiền về muộn" (BR-TT-18) trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/late_payment_record.py      # tắt server sau khi xong; xoá out/
import re

from playwright.sync_api import expect, sync_playwright

from orders_common import (SHOTS, clear_log, dialog, fonts_ready, go, hscroll, idle, login, make_new_page, ok, posts, qjson, submit_btn, toast_text,
                           finish)

OPEN_BTN = "Ghi tiền về muộn"


def open_refund_dialog(page):
    """Khoản không gắn đơn: nút chính là 'Gắn vào đơn', 'Lập phiếu hoàn' nằm trong 'Thao tác khác'."""
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("Lập phiếu hoàn")).click()


def open_form(page):
    page.get_by_role("button", name=OPEN_BTN).click()
    return dialog(page, OPEN_BTN)


def fill_form(d, txn, amount, order=None, at=None):
    d.get_by_label("Mã giao dịch ngân hàng").fill(txn)
    d.get_by_label("Số tiền").fill(amount)
    if at:
        d.get_by_label("Giờ nhận theo sao kê").fill(at)
    if order is not None:
        d.get_by_label("Mã đơn (nếu biết)").fill(order)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []

    # ============ Vai không có quyền: không thấy nút ============
    for user in ("ql1", "kho1"):
        ctx, page = make_new_page(browser, errors)
        login(page, user)
        go(page, "/orders/payments/")
        ok(f"{user}: không có nút '{OPEN_BTN}'", page.get_by_role("button", name=OPEN_BTN).count() == 0)
        ctx.close()

    # ============ Chủ (loc), 1280 ============
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    go(page, "/orders/payments/")
    fonts_ready(page)
    expect(page.get_by_role("button", name=OPEN_BTN)).to_be_visible()
    ok("Chủ: thấy nút Ghi tiền về muộn ở hàng chờ", True)
    page.screenshot(path=f"{SHOTS}/queue-1280.png")

    j = qjson(page)
    auto = next(r for r in j["results"] if r["order"] and r["order"]["status"] == "AUTO_CANCELLED")
    booked = next(r["order"] for r in j["results"] if r["order"] and r["order"]["status"] == "BOOKED")
    order_code = auto["order"]["code"]

    # --- Lỗi chặn tại ô: không gửi ---
    clear_log(page)
    d = open_form(page)
    ok("Form không có ô ghi chú", d.get_by_label(re.compile("ghi chú", re.I)).count() == 0 and d.locator("textarea").count() == 0)
    ok("Giờ nhận điền sẵn theo giờ hiện tại", re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", d.get_by_label("Giờ nhận theo sao kê").input_value()) is not None)
    fill_form(d, "Nguyễn Văn A 0900000321", "abc")
    submit_btn(d).click()
    expect(d.get_by_text("chỉ gồm chữ không dấu, số")).to_be_visible()
    ok("Lỗi mã GD + số tiền hiện dưới ô, không gửi POST", len(posts(page)) == 0 and d.locator("[aria-invalid=true]").count() >= 2, str(posts(page)))
    # giờ tương lai
    fill_form(d, "FTE2E001", "350000", at="2999-01-01T10:00")
    submit_btn(d).click()
    expect(d.get_by_text("không được ở tương lai")).to_be_visible()
    ok("Giờ nhận tương lai báo tại ô, không gửi", len(posts(page)) == 0)
    fill_form(d, "FTE2E001", "350000", at="2026-10-03T10:29")

    # --- Lỗi theo khoá từ BE: mã đơn không có / Giữ chỗ ---
    d.get_by_label("Mã đơn (nếu biết)").fill("SO-KHONG-CO")
    submit_btn(d).click()
    expect(d.get_by_text("Không tìm thấy đơn mang mã này")).to_be_visible()
    ok("400 LATE_PAYMENT_ORDER_NOT_FOUND hiện dưới ô Mã đơn", d.get_by_label("Mã đơn (nếu biết)").get_attribute("aria-invalid") == "true")
    d.get_by_label("Mã đơn (nếu biết)").fill(booked["code"])
    submit_btn(d).click()
    expect(d.get_by_text("Đơn còn đang giữ chỗ")).to_be_visible()
    link = d.get_by_role("link", name="Mở đơn")
    ok("400 ORDER_BOOKED: lỗi tại ô + link Mở đơn", link.count() == 1 and f"/orders/detail/?id={booked['id']}" in link.get_attribute("href"), str(link.get_attribute("href")))
    page.screenshot(path=f"{SHOTS}/form-error-1280.png")

    # --- Thành công: đơn Tự huỷ → ORPHAN ---
    d.get_by_label("Mã đơn (nếu biết)").fill(order_code.lower())
    clear_log(page)
    submit_btn(d).click()
    expect(page.get_by_role("heading", name="FTE2E001")).to_be_visible()
    idle(page)
    body = [x for x in posts(page) if "record-late" in x]
    ok("Thành công: gọi POST /api/sales/payments/record-late/", len(body) == 1, str(posts(page)))
    ok("Chuyển sang chi tiết giao dịch (?id=), toast ghi xong", "/orders/payments/detail/?id=" in page.url and "Đã ghi khoản FTE2E001" in toast_text(page), page.url + " | " + toast_text(page))
    ok("URL không chứa dữ liệu form (mã GD/số tiền/đơn)", "FTE2E001" not in page.url and "350000" not in page.url and order_code not in page.url, page.url)
    ls = page.evaluate("() => JSON.stringify(Object.entries(localStorage))")
    ok("localStorage không chứa mã GD vừa nhập", "FTE2E001" not in ls)
    main = page.locator("main").inner_text()
    ok("Chi tiết: loại 'Về sau khi đơn tự huỷ', nguồn 'Xác nhận tay', còn mở", "Về sau khi đơn tự huỷ" in main and "Xác nhận tay" in main and order_code in main, main[:400])
    ok("Dòng thời gian có 'Ghi tay tiền về muộn 350.000 đ (mã GD FTE2E001)'", "Ghi tay tiền về muộn 350.000 đ (mã GD FTE2E001)" in page.locator("main").inner_text())
    ok("Chi tiết khoản ORPHAN: nút chính là Lập phiếu hoàn", page.locator("main header .btn.primary").first.inner_text().strip() == "Lập phiếu hoàn", page.locator("main header .btn.primary").first.inner_text())
    page.screenshot(path=f"{SHOTS}/detail-late-1280.png")

    # --- 409 nghi trùng: không đơn, cùng số tiền ---
    go(page, "/orders/payments/")
    d = open_form(page)
    fill_form(d, "FTE2E002", "123000")
    submit_btn(d).click()
    expect(page.get_by_role("heading", name="FTE2E002")).to_be_visible()
    idle(page)
    go(page, "/orders/payments/")
    d = open_form(page)
    fill_form(d, "FTE2E003", "123000")
    submit_btn(d).click()
    box = d.get_by_text("Có khoản giống đã ghi")
    expect(box).to_be_visible()
    ok("409: hộp vàng nêu mã GD khoản giống", "FTE2E002" in d.inner_text(), d.inner_text()[:300])
    ok("409: không hiện alert đỏ", d.locator("[data-form-alert=error]").count() == 0)
    tick = d.get_by_label("Tôi đã kiểm, đây không phải trùng")
    ok("409: ô tick chưa chọn, nút ghi bị khoá", (not tick.is_checked()) and submit_btn(d).is_disabled())
    page.screenshot(path=f"{SHOTS}/similar-409-1280.png")
    clear_log(page)
    tick.check()
    ok("Tick xong mở khoá nút", submit_btn(d).is_enabled())
    submit_btn(d).click()
    expect(page.get_by_role("heading", name="FTE2E003")).to_be_visible()
    idle(page)
    ok("Gửi lại kèm cờ → vào chi tiết", "/orders/payments/detail/?id=" in page.url)
    ok("Chi tiết có khung vàng Nghi trùng khoản tiền", page.locator("[data-form-alert=warn]").filter(has_text="Nghi trùng khoản ghi tay").count() == 1)
    dup_url = page.url

    # --- Lập phiếu hoàn từ khoản có nhãn: phải tick ---
    open_refund_dialog(page)
    rd = dialog(page, "Lập phiếu hoàn")
    ok("Hộp hoàn: có hộp Nghi trùng + ô tick, nút khoá", rd.locator("[data-duplicate-box]").count() == 1 and submit_btn(rd).is_disabled())
    page.screenshot(path=f"{SHOTS}/refund-tick-1280.png")
    rd.get_by_label("Tôi đã đối chiếu sao kê").check()
    clear_log(page)
    submit_btn(rd).click()
    idle(page)
    ok("Hoàn có nhãn: tick xong lập được phiếu (toast)", "phiếu hoàn" in toast_text(page).lower(), toast_text(page))

    # --- 409 PAYMENT_DUPLICATE_WARNING mở lại hộp đúng chỗ ---
    go(page, "/orders/payments/")
    d = open_form(page)
    fill_form(d, "FTE2E004", "777000")
    submit_btn(d).click()
    expect(page.get_by_role("heading", name="FTE2E004")).to_be_visible()
    idle(page)
    open_refund_dialog(page)
    rd = dialog(page, "Lập phiếu hoàn")
    ok("Khoản chưa có nhãn: hộp hoàn không có hộp Nghi trùng", rd.locator("[data-duplicate-box]").count() == 0)
    pid = int(re.search(r"id=(\d+)", page.url).group(1))
    page.evaluate("(id) => window.__caveMock.flagDuplicate(id)", pid)  # webhook về sau khi màn đã mở
    submit_btn(rd).click()
    expect(rd.locator("[data-duplicate-box]")).to_be_visible()
    ok("BE 409: mở lại đúng hộp với ô tick, không alert đỏ, nút khoá", rd.locator("[data-form-alert=error]").count() == 0 and submit_btn(rd).is_disabled())
    rd.get_by_label("Tôi đã đối chiếu sao kê").check()
    submit_btn(rd).click()
    idle(page)
    ok("Tick rồi gửi lại: lập phiếu thành công", "phiếu hoàn" in toast_text(page).lower(), toast_text(page))

    # --- Hàng chờ: biểu tượng nghi trùng ---
    go(page, "/orders/payments/")
    flagged = page.locator("tr", has_text="FTE2E003")
    ok("Hàng chờ: dòng nghi trùng có nhãn cho trình đọc màn hình", flagged.locator("[data-duplicate-warning]").count() == 1 and "Nghi trùng" in flagged.inner_text())
    ok("Hàng chờ: dòng thường không có dấu", page.locator("tr", has_text="FTE2E002").locator("[data-duplicate-warning]").count() == 0)
    ctx.close()

    # ============ 360 px ============
    ctx, page = make_new_page(browser, errors, width=360, height=800, mobile=True)
    login(page, "loc")
    go(page, "/orders/payments/")
    fonts_ready(page)
    ok("360: hàng chờ không cuộn ngang", hscroll(page) <= 360, str(hscroll(page)))
    page.screenshot(path=f"{SHOTS}/queue-360.png")
    d = open_form(page)
    fill_form(d, "FTE2E009", "123000")
    submit_btn(d).click()
    expect(page.get_by_role("heading", name="FTE2E009")).to_be_visible()
    idle(page)
    go(page, "/orders/payments/")
    d = open_form(page)
    fill_form(d, "FTE2E010", "123000")
    submit_btn(d).click()
    d.get_by_text("Có khoản giống đã ghi").wait_for()
    ok("360: hộp 409 không cuộn ngang, nút ≥ 44px", hscroll(page) <= 360 and submit_btn(d).bounding_box()["height"] >= 44, str(submit_btn(d).bounding_box()))
    page.screenshot(path=f"{SHOTS}/similar-409-360.png")
    d.get_by_label("Tôi đã kiểm, đây không phải trùng").check()
    page.screenshot(path=f"{SHOTS}/similar-ticked-360.png")
    ctx.close()

    browser.close()
    finish(errors)
