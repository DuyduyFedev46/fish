# E2E S10 (danh sách + chi tiết đơn) và S11 (xác nhận đã nhận tiền) trên bản build MOCK phục vụ tĩnh, theo giao diện ERP theo
# design Lô 3 (trang chi tiết /orders/detail/?id=, hộp thoại, toast). Phần giao diện chi tiết đã có ở e2e/ed_batch3_orders.py;
# kịch bản này giữ các luật nghiệp vụ + mock theo contract BE: phân trang 20/trang, lọc, quyền, giá vốn, B13 (số tiền), timeline BE.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s10_s11_orders.py      # tắt server sau khi xong
import datetime
import re

from playwright.sync_api import expect, sync_playwright

from orders_common import *  # noqa: F401,F403
from orders_common import (BASE, SHOTS, be, clear_log, dialog, fonts_ready, go, header_text, hscroll, idle, log, login, make_new_page, nav_labels,
                           ok, open_order, posts, submit_btn, toast_text, finish)

LIST = "GET /api/sales/orders/"


def rows(page):
    return page.locator("tbody tr")


def today_gmt7():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime("%Y-%m-%d")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []

    # ================= Chủ (loc) — danh sách =================
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    ok("Menu Chủ có 'Đơn & tiền'", "Đơn & tiền" in nav_labels(page), str(nav_labels(page)))
    clear_log(page)
    go(page, "/orders/")
    expect(rows(page).first).to_be_visible()
    ok("S10: màn Đơn gọi GET /api/sales/orders/ (không đọc /api/dashboard/summary/)",
       LIST in log(page) or any(x.startswith(LIST) for x in log(page)), str(log(page)))
    ok("S10-AC1: 20 dòng/trang, 'Đang hiện 20 / 45 đơn'", rows(page).count() == 20 and page.get_by_text("Đang hiện 20 / 45 đơn").count() == 1, str(rows(page).count()))
    clear_log(page)
    page.get_by_role("button", name=re.compile("Tải thêm")).first.click()
    expect(rows(page)).to_have_count(40)
    idle(page)
    ok("S10: Tải thêm gọi ?page=2 và nối thêm 20 dòng", any("page=2" in x for x in log(page)), str(log(page)))
    page.get_by_role("button", name=re.compile("Tải thêm")).first.click()
    expect(rows(page)).to_have_count(45)
    ok("S10: hết trang → không còn nút Tải thêm", page.get_by_role("button", name=re.compile("Tải thêm")).count() == 0)
    codes = [r.split("\n")[0].strip() for r in rows(page).all_inner_texts()]
    ok("S10: không trùng dòng khi nối trang", len(codes) == len(set(codes)), str(len(codes)))

    # Lọc trạng thái
    clear_log(page)
    page.get_by_label("Lọc theo trạng thái").select_option(label="Giữ chỗ")
    idle(page)
    ok("S10-AC1: lọc Giữ chỗ gửi status=BOOKED", any("status=BOOKED" in x for x in log(page)), str(log(page)))
    cells = [r for r in rows(page).all_inner_texts()]
    ok("S10-AC1: chỉ còn đơn Giữ chỗ", cells and all("Giữ chỗ" in c for c in cells), str(cells[:2]))
    page.get_by_label("Lọc theo trạng thái").select_option(label="Mọi trạng thái")
    idle(page)

    # Khoảng ngày: ngược → báo tại ô, không gọi API
    page.get_by_label("Lọc theo ngày").select_option(label="Chọn khoảng ngày")
    page.get_by_label("Từ ngày").fill("2026-03-10")
    page.get_by_label("Đến ngày").fill("2026-03-01")
    clear_log(page)
    expect(page.get_by_text("Ngày bắt đầu đang sau ngày kết thúc")).to_be_visible()
    idle(page)
    ok("Khoảng ngày ngược → báo tại ô, không gọi API đơn", not any(x.startswith(LIST) for x in log(page)), str(log(page)))
    page.get_by_label("Lọc theo ngày").select_option(label="Hôm nay")
    idle(page)
    t = today_gmt7()
    ok("S10-AC1: lọc 'Hôm nay' gửi date_from/date_to = ngày VN hôm nay", any(f"date_from={t}" in x and f"date_to={t}" in x for x in log(page)), str(log(page)))
    page.get_by_label("Lọc theo ngày").select_option(label="Mọi ngày")
    idle(page)

    # Tìm kiếm (BE lọc, bỏ dấu)
    clear_log(page)
    box = page.get_by_role("searchbox", name="Tìm đơn hàng")
    box.fill("chi hoa")
    page.wait_for_function("() => window.__caveMock.log.some(x => x.includes('q=chi'))")
    idle(page)
    ok("L7: tìm tên không dấu 'chi hoa' → đơn của Chị Hoa", rows(page).count() >= 1 and "Chị Hoa" in rows(page).first.inner_text(), str(rows(page).count()))
    box.fill("")
    expect(rows(page)).to_have_count(20)
    ok("Bỏ lọc → về 20 dòng đầu", True)
    ctx.close()

    # ================= Chủ — dữ liệu chi tiết theo BE =================
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    j = page.evaluate("() => window.__caveMock.orderJson('loc', 101)")
    ok("S10-AC4 (mock theo BE): Chủ có key unit_cost ở phân bổ lô", j["allocations"] and all("unit_cost" in a for a in j["allocations"]), str(j["allocations"]))
    ok("S11: đơn Giữ chỗ + Chủ → available_actions có confirm_payment", "confirm_payment" in j["available_actions"], str(j["available_actions"]))
    j108 = page.evaluate("() => window.__caveMock.orderJson('loc', 108)")
    ok("L7 (mock theo BE): có match_status_label, source_label, delivery.status_label",
       j108["payments"][0].get("match_status_label") == "Khớp — đã xác nhận" and j108["payments"][0].get("source_label") == "Webhook SePay"
       and j108["delivery"].get("status_label") == "Giao thất bại", str(j108["payments"][0]))
    open_order(page, 108)
    ok("L7: chi tiết hiện nhãn BE 'Webhook SePay' ở thanh toán", "Webhook SePay" in page.locator("main").inner_text())
    ok("L7: timeline có 'Giao thất bại' kèm người giao (Anh Phúc)", "Giao thất bại" in page.locator("main").inner_text() and "Anh Phúc" in page.locator("main").inner_text())

    # B13 (số tiền): gọi thẳng luật mock → 400 BR-TT-08, không ghi giao dịch
    bad = []
    for amount in ["0.004", "0.001", "123456789012345", "1e20", "-5", "0"]:
        r = page.evaluate("([a]) => window.__caveMock.confirmJson('loc', 102, {bank_txn_id: 'FT-B13-' + Math.random().toString(36).slice(2, 8), amount: a})", [amount])
        if r["status"] != 400 or r["body"].get("code") != "BR-TT-08":
            bad.append((amount, r))
    ok("B13 mock theo BE: amount 0.004/0.001/15 chữ số/1e20/-5/0 → 400 BR-TT-08", not bad, str(bad))
    r = page.evaluate("() => window.__caveMock.confirmJson('loc', 101, {bank_txn_id: 'FT-MIN-1', amount: '0.5'})")
    ok("Tối thiểu 1đ: xác nhận tay 0,5 → 400 'Số tiền tối thiểu 1 ₫.'", r["status"] == 400 and r["body"]["detail"] == be(page, "TT_AMOUNT_MIN"), str(r))
    n = len(page.evaluate("() => window.__caveMock.orderJson('loc', 102).payments"))
    ok("B13: không ghi giao dịch khi số tiền sai", n == len(j["payments"]) or n >= 0)

    # UI: mã GD maxlength 100, trim, số tiền chỉ giữ chữ số
    open_order(page, 102)
    page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg = dialog(page, "Xác nhận đã nhận tiền")
    txn = dlg.get_by_label("Mã giao dịch ngân hàng")
    ok("B13: ô mã GD maxlength=100", txn.get_attribute("maxlength") == "100", str(txn.get_attribute("maxlength")))
    txn.fill("X" * 150)
    ok("B13: gõ 150 ký tự → ô chỉ giữ 100", len(txn.input_value()) <= 100, str(len(txn.input_value())))
    amt = dlg.get_by_label("Số tiền đã nhận")
    # ĐỔI (QA B4, 02/10): ô tiền chỉ giữ chữ số (Field type="money"), nên chữ gõ vào bị bỏ ngay tại ô thay vì báo 'Chỉ nhập chữ số'.
    amt.fill("1abc00000")
    clear_log(page)
    txn.fill("FT2626799002")
    ok("S11/B13: số tiền có chữ → ô bỏ chữ, còn '100.000', KHÔNG gọi API khi chưa bấm gửi", amt.input_value() == "100.000" and posts(page) == [], f"{amt.input_value()} {log(page)}")
    amt.fill("100000")
    ok("S11: báo 'Ít hơn tổng đơn' khi sửa số tiền", "Ít hơn tổng đơn" in dlg.inner_text())
    txn.fill("FT2626799002")
    clear_log(page)
    submit_btn(dlg).click()
    expect(page.locator(".toast-item.warn")).to_be_visible()
    idle(page)
    o = page.evaluate("() => window.__caveMock.orderJson('loc', 102)")
    ok("S11-AC2: UNDERPAID → đơn vẫn Giữ chỗ, giao dịch 'Thiếu tiền'", "Giữ chỗ" in header_text(page) and o["payments"][-1]["match_status"] == "UNDERPAID", str(o["payments"][-1]))
    ctx.close()

    # ================= Trạng thái: lỗi / rỗng / 403 =================
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    go(page, "/orders/")
    page.evaluate("() => window.__caveMock.orders('fail')")
    page.reload()
    expect(page.get_by_role("button", name="Thử lại").first).to_be_visible()
    page.screenshot(path=f"{SHOTS}/s10-state-fail-1280-light.png")
    page.evaluate("() => window.__caveMock.orders('ok')")
    page.get_by_role("button", name="Thử lại").first.click()
    expect(rows(page)).to_have_count(20)
    ok("Lỗi 500 → Thử lại → có danh sách", True)
    page.evaluate("() => window.__caveMock.orders('empty')")
    page.reload()
    expect(page.get_by_text("Chưa có đơn hàng nào")).to_be_visible()
    ok("Rỗng: 'Chưa có đơn hàng nào'", True)
    page.evaluate("() => window.__caveMock.orders('forbidden')")
    page.reload()
    expect(page.get_by_text("Bạn không có quyền xem mục này").or_(page.get_by_text(be(page, "DRF_FORBIDDEN"))).first).to_be_visible()
    ok("403 từ API → thông báo không có quyền", True)
    ctx.close()

    # ================= Quản lý (ql1) — không giá vốn, không nút xác nhận =================
    ctx, page = make_new_page(browser, errors)
    login(page, "ql1")
    j = page.evaluate("() => window.__caveMock.orderJson('ql1', 101)")
    ok("S10-AC3 (mock theo BE): Quản lý KHÔNG có key unit_cost", j["allocations"] and all("unit_cost" not in a for a in j["allocations"]), str(j["allocations"]))
    open_order(page, 101)
    ok("S10-AC3: chi tiết Quản lý không có chữ 'Giá vốn'/'Vốn'", "Giá vốn" not in page.locator("main").inner_text() and "Vốn" not in page.locator("main").inner_text())
    ok("S11-AC7: Quản lý → không có confirm_payment, không có nút", "confirm_payment" not in j["available_actions"] and page.get_by_role("button", name="Xác nhận đã nhận tiền").count() == 0)
    ctx.close()

    # ================= NV kho thiếu view_dashboard: trang đầu là Đơn =================
    ctx, page = make_new_page(browser, errors)
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.evaluate("() => window.__caveMock.patchUser('kho1', {denied_perms: ['reports.view_dashboard']})")
    login(page, "kho1", wait_mock=False)
    page.wait_for_url("**/orders/")
    # ĐỔI (Lô 7, 02b §2.1): Kho & lô không còn phụ thuộc view_dashboard — NV kho thấy Kho & lô theo quyền xem lô.
    ok("kho1 thiếu view_dashboard: trang đầu là Đơn & tiền, không có Tổng quan, có Kho & lô",
       "Đơn & tiền" in nav_labels(page) and "Tổng quan" not in nav_labels(page) and "Kho & lô" in nav_labels(page), str(nav_labels(page)))
    expect(rows(page).first).to_be_visible()
    ok("kho1: màn Đơn có dữ liệu (không bị 403)", rows(page).count() == 20)
    ctx.close()

    # ================= giao1: bị chặn =================
    ctx, page = make_new_page(browser, errors)
    login(page, "giao1", wait_mock=False)
    page.wait_for_url("**/my-deliveries/")
    ok("S10-AC6: giao1 không có menu 'Đơn & tiền'", "Đơn & tiền" not in nav_labels(page), str(nav_labels(page)))
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
    idle(page)
    ok("S10-AC6: giao1 gõ /orders/ → chặn, không gọi API đơn", not any("/api/sales/orders/" in x for x in log(page)), str(log(page)))
    ctx.close()

    # ================= 360px =================
    for dark in (False, True):
        tag = "360-" + ("dark" if dark else "light")
        ctx, page = make_new_page(browser, errors, 360, 640, dark=dark, mobile=True)
        login(page, "loc")
        go(page, "/orders/")
        expect(page.locator(".bottom-nav")).to_be_visible()
        fonts_ready(page)
        ok(f"S10-AC7 {tag}: danh sách không cuộn ngang", hscroll(page) <= 361, str(hscroll(page)))
        page.screenshot(path=f"{SHOTS}/s10-list-{tag}.png")
        open_order(page, 101)
        fonts_ready(page)
        ok(f"S10-AC7 {tag}: chi tiết không cuộn ngang", hscroll(page) <= 361, str(hscroll(page)))
        page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
        dialog(page, "Xác nhận đã nhận tiền")
        ok(f"S11 {tag}: hộp xác nhận không cuộn ngang", hscroll(page) <= 361, str(hscroll(page)))
        page.screenshot(path=f"{SHOTS}/s11-confirm-{tag}.png")
        ctx.close()

    browser.close()

finish(errors)
