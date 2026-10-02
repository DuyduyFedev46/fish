# E2E ERP theo design, Lô 8 (Kiểm kê ED-28): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3201 &)
#   BASE=http://127.0.0.1:3201 SHOTS=<thư mục ảnh> python3 e2e/ed_batch8_stocktake.py      # tắt server sau khi xong
# Kiểm: loc / ql1 / kho1 vào được, giao1 / cs2 không · danh sách (cột kho, hụt, dư, lọc, tìm, rỗng) · lập phiếu: chọn kho nạp lô,
# lưu nháp rồi gửi duyệt, lỗi (số âm, thiếu số, đếm dư không lý do, kho rỗng, ngày trống) · chi tiết: bảng chênh lệch, dòng thời gian ·
# người nhập số không duyệt được (nút mờ trong "…" kèm lý do), người khác duyệt được, tồn kho đổi đúng số đã chụp (BR-KK-09) ·
# người đã sửa số đếm cũng bị chặn (BR-KK-08) · 409 STALE_STATE -> ConflictBanner · RECON_EMPTY · RECON_STOCK_INSUFFICIENT đúng dòng ·
# phiếu đã duyệt không sửa · 404 · 360px không cuộn ngang · không có tiền, không có dữ liệu khách ở localStorage / URL / console.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3201")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)

WAREHOUSE_STAFF = "Kho lạnh Bến Đá"


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    settle(page)


def switch_user(page, user):
    """Đổi người đăng nhập nhưng GIỮ kho giả (localStorage của phiếu), như hai người dùng chung một BE."""
    page.goto(BASE + "/login/")
    page.evaluate("() => localStorage.removeItem('cave_erp_token')")
    login(page, user)


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def new_page(browser, user, w=1280, h=860, errors=None):
    errors = errors if errors is not None else []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and "HTTP" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, user)
    return ctx, page, errors


def stock(page, batch):
    return page.evaluate("(b) => window.__caveMock.stocktakeStock(b)", batch)


def rows(page):
    return page.locator("li[data-line-row]")


def row_of(page, code):
    return page.locator("table.lt tbody tr", has_text=code)


def line(page, batch):
    return page.locator(f"li[data-line-row][data-batch='{batch}']")


def pick_warehouse(page, name):
    page.get_by_label("Kho cần đếm").select_option(label=name)
    page.wait_for_load_state("networkidle")
    settle(page)


def count(page, batch, value, reason=None):
    r = line(page, batch)
    r.locator("input[data-counted]").fill(value)
    if reason is not None:
        r.locator("input[data-reason]").fill(reason)


def toast(page, text):
    return page.get_by_text(text, exact=False).first


def more_menu(page):
    page.get_by_role("button", name="Thao tác khác").click()
    return page.get_by_role("menu")


# ---------------------------------------------------------------- vai được vào / không được vào
def role_access(browser):
    for user in ("loc", "ql1", "kho1"):
        ctx, page, _ = new_page(browser, user)
        go(page, "/stocktake/")
        ok(f"{user}: vào được /stocktake/", page.locator("table.lt").count() == 1 and page.get_by_text("không có quyền", exact=False).count() == 0, page.url)
        ok(f"{user}: có nút Lập phiếu kiểm kê", page.get_by_role("link", name="Lập phiếu kiểm kê").count() >= 1)
        ctx.close()
    for user in ("giao1", "cs2"):
        ctx, page, _ = new_page(browser, user)
        for path in ("/stocktake/", "/stocktake/new/", "/stocktake/edit/?id=14", "/stocktake/detail/?id=14"):
            go(page, path)
            ok(f"{user}: {path} hiện không có quyền", page.get_by_text("không có quyền", exact=False).first.is_visible())
        ok(f"{user}: không có mục Kiểm kê trong menu", page.locator(".nav a", has_text="Kiểm kê").count() == 0)
        ctx.close()


# ---------------------------------------------------------------- danh sách
def list_screen(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/stocktake/")
    heads = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts()]
    ok("cột đủ: mã, ngày, kho, số lô, hụt, dư, người nhập, người duyệt, trạng thái, ghi chú",
       heads == ["Mã phiếu", "Ngày", "Kho", "Số lô", "Hụt (kg)", "Dư (kg)", "Người nhập số", "Người duyệt", "Trạng thái", "Ghi chú"], str(heads))
    r14 = row_of(page, "KK-14")
    c14 = r14.inner_text().split("\t")
    t14 = "|".join(c14)
    ok("KK-14: kho, số lô 3, hụt −0,8, dư +0,3, Chờ duyệt", c14[2] == WAREHOUSE_STAFF and c14[3] == "3" and c14[4] == "−0,8" and c14[5] == "+0,3" and c14[8] == "Chờ duyệt", t14)
    ok("KK-14: giờ ngày dạng dd/mm/yyyy", "01/10/2026" in t14, t14)
    c17 = row_of(page, "KK-17").inner_text().split("\t")
    ok("KK-17 (phiếu trống): kho và hụt/dư là gạch, số lô 0", c17[2] == "—" and c17[3] == "0" and c17[4] == "—" and c17[5] == "—", str(c17))
    ok("KK-13: Đã duyệt, người duyệt Lộc", "Đã duyệt" in row_of(page, "KK-13").inner_text() and "Lộc" in row_of(page, "KK-13").inner_text())
    summary = page.locator(".fb").inner_text()
    ok("có dòng tóm tắt 'Đang hiện n / m phiếu' kèm số chờ duyệt", re.search(r"Đang hiện 6 / 6 phiếu · 4 chờ duyệt", summary) is not None, summary.replace("\n", "|"))
    # lọc
    page.get_by_label("Lọc theo trạng thái").select_option("APPROVED")
    page.wait_for_load_state("networkidle")
    settle(page)
    ok("lọc Đã duyệt: còn 2 phiếu", page.locator("table.lt tbody tr").count() == 2, str(page.locator("table.lt tbody tr").count()))
    page.get_by_label("Lọc theo trạng thái").select_option("")
    page.get_by_label("Lọc theo kho").select_option(label="Kho mát chợ Vũng Tàu")
    page.wait_for_load_state("networkidle")
    settle(page)
    ok("lọc kho Vũng Tàu: KK-16 và KK-15", sorted(t.split("\t")[0] for t in page.locator("table.lt tbody tr").all_inner_texts()) == ["KK-15", "KK-16"], str(page.locator("table.lt tbody tr").all_inner_texts()))
    page.get_by_label("Lọc theo kho").select_option("")
    page.wait_for_load_state("networkidle")
    settle(page)
    page.locator("input[name=q]").fill("KK-14")
    ok("tìm KK-14: một dòng", page.locator("table.lt tbody tr").count() == 1)
    page.locator("input[name=q]").fill("zzzz")
    ok("tìm không ra: báo không khớp, không lỗi", page.get_by_text("Không tìm thấy phiếu kiểm kê khớp với", exact=False).first.is_visible())
    page.locator("input[name=q]").fill("")
    r14.click()
    page.wait_for_url("**/stocktake/detail/?id=14")
    ok("bấm dòng mở chi tiết, URL chỉ mang ?id=", page.url.endswith("/stocktake/detail/?id=14"), page.url)
    ok("không có lỗi console", not errors, str(errors[:2]))
    ctx.close()


# ---------------------------------------------------------------- lập phiếu: đường thuận + lỗi
def create_flow(browser):
    errors = []
    ctx, page, errors = new_page(browser, "kho1", errors=errors)
    go(page, "/stocktake/new/")
    ok("form mới: có ngày hôm nay, chưa có lô, hướng dẫn chọn kho", page.get_by_label("Ngày kiểm kê").input_value() != "" and rows(page).count() == 0 and page.locator("[data-stocktake-empty]").is_visible())
    # lưu mà chưa chọn kho / chưa nhập số
    page.get_by_role("button", name="Lưu nháp").click()
    ok("chưa có lô: báo chọn kho", page.get_by_text("Chọn kho để nạp các lô cần đếm.", exact=False).first.is_visible())
    pick_warehouse(page, WAREHOUSE_STAFF)
    ok("chọn kho nạp 5 lô còn tồn", rows(page).count() == 5, str(rows(page).count()))
    pick_warehouse(page, WAREHOUSE_STAFF)
    ok("chọn lại cùng kho không nhân đôi dòng (không trùng lô)", rows(page).count() == 5)
    ok("hiện tồn hệ thống kg, dấu phẩy", line(page, 101).locator("[data-system]").inner_text() == "18,5", line(page, 101).locator("[data-system]").inner_text())
    ok("form không có số tiền / giá vốn", re.search(r"\d\s?đ\b|giá vốn", page.inner_text("main"), re.I) is None)
    # Lưu nháp chưa nhập số
    page.get_by_role("button", name="Lưu nháp").click()
    ok("chưa nhập số nào: báo nhập ít nhất một lô, chưa tạo phiếu", page.get_by_text("Nhập số đếm của ít nhất một lô.", exact=False).first.is_visible() and "/stocktake/new/" in page.url)
    # số âm
    count(page, 101, "-5")
    ok("số âm: viền đỏ + câu dưới ô ngay khi gõ", line(page, 101).get_by_text("Số đếm phải từ 0 kg trở lên.").is_visible() and line(page, 101).locator("input[data-counted]").get_attribute("aria-invalid") == "true")
    page.get_by_role("button", name="Lưu nháp").click()
    ok("số âm: không gửi, còn ở form mới", "/stocktake/new/" in page.url and page.get_by_text("Có dòng chưa hợp lệ", exact=False).first.is_visible())
    count(page, 101, "abc")
    ok("chữ: báo nhập số kg", line(page, 101).get_by_text("Nhập số kg", exact=False).is_visible())
    count(page, 101, "1,23456")
    ok("quá 3 chữ số lẻ: báo", line(page, 101).get_by_text("Tối đa 3 chữ số sau dấu phẩy.").is_visible())
    # đếm dư không lý do
    count(page, 101, "20,25")
    ok("đếm dư: chênh lệch +1,75 màu cảnh báo", line(page, 101).locator("[data-diff]").inner_text() == "+1,75")
    page.get_by_role("button", name="Lưu nháp").click()
    ok("đếm dư không lý do: lỗi dưới ô lý do, không gửi", line(page, 101).get_by_text("ghi lý do", exact=False).is_visible() and "/stocktake/new/" in page.url, page.url)
    count(page, 101, "20,25", "Nhập thiếu phiếu hôm qua")
    ok("có lý do: hết lỗi dòng", line(page, 101).locator("[aria-invalid='true']").count() == 0)
    # đếm hụt, bằng 0 hợp lệ
    count(page, 102, "11,6")
    count(page, 103, "0")
    ok("đếm 0 kg hợp lệ, chênh lệch −25,25", line(page, 103).locator("[data-diff]").inner_text() == "−25,25")
    ok("tóm tắt: 3 lô đã nhập số", "3 / 5" in page.locator("[data-row-count]").inner_text(), page.locator("[data-row-count]").inner_text())
    # bỏ một lô
    line(page, 105).get_by_role("button", name=re.compile("^Bỏ lô")).click()
    ok("bỏ lô khỏi phiếu: còn 4 dòng", rows(page).count() == 4)
    # Gửi duyệt khi còn dòng trống
    page.get_by_role("button", name="Gửi duyệt").click()
    ok("Gửi duyệt khi còn lô chưa đếm: báo đỏ ở lô trống", line(page, 104).get_by_text("Nhập số đếm của lô này.").is_visible() and "/stocktake/new/" in page.url)
    # Lưu nháp lần đầu: ở lại trang, không mất lý do đã gõ, URL chuyển sang trang sửa, nói rõ lô chưa có số chưa được lưu (TL8-L1, L2)
    line(page, 104).locator("input[data-reason]").fill("Chưa đếm xong, để sau")
    page.get_by_role("button", name="Lưu nháp").click()
    page.wait_for_url("**/stocktake/edit/?id=18")
    settle(page)
    ok("Lưu nháp tạo phiếu 18, URL sang trang sửa và chỉ mang ?id=", page.url.endswith("/stocktake/edit/?id=18"), page.url)
    ok("tiêu đề đổi thành Sửa số đếm KK-18", page.get_by_text("Sửa số đếm KK-18", exact=False).first.is_visible())
    ok("vẫn ở nguyên form: 4 dòng, số và lý do còn nguyên", rows(page).count() == 4 and line(page, 101).locator("input[data-counted]").input_value() == "20,25" and line(page, 103).locator("input[data-counted]").input_value() == "0" and line(page, 101).locator("input[data-reason]").input_value() == "Nhập thiếu phiếu hôm qua")
    ok("lô chưa có số vẫn giữ lý do đã gõ trong form (TL8-L2)", line(page, 104).locator("input[data-reason]").input_value() == "Chưa đếm xong, để sau")
    ok("toast nói 1 lô chưa có số nên chưa được lưu", toast(page, "1 lô chưa có số nên chưa được lưu").is_visible())
    # bấm Lưu nháp hai lần liên tiếp không tạo thêm phiếu (TL8-L1)
    page.get_by_role("button", name="Lưu nháp").dblclick()
    settle(page)
    ok("bấm đúp Lưu nháp sau khi đã tạo: vẫn là phiếu 18", page.url.endswith("/stocktake/edit/?id=18"), page.url)
    # nạp thêm lô còn thiếu rồi gửi duyệt
    pick_warehouse(page, WAREHOUSE_STAFF)
    ok("nạp lại kho: giữ 4 dòng đang có, thêm lô 105 chưa có (không trùng)", rows(page).count() == 5, str(rows(page).count()))
    count(page, 104, "30")
    count(page, 105, "41,75")
    # nhấn đúp Gửi duyệt chỉ tạo một lần
    btn = page.get_by_role("button", name="Gửi duyệt")
    btn.dblclick()
    page.wait_for_url("**/stocktake/detail/?id=18")
    settle(page)
    ok("Gửi duyệt: sang chi tiết KK-18", page.get_by_role("heading", name="KK-18").is_visible(), page.url)
    ok("chi tiết: chip Chờ duyệt, 5 dòng, đúng chênh lệch", "Chờ duyệt" in page.locator("main").inner_text() and page.locator("table.lt tbody tr[data-line-row]").count() == 5)
    diffs = [r.locator("[data-diff]").inner_text() for r in page.locator("table.lt tbody tr[data-line-row]").all()]
    ok("chênh lệch từng lô đúng (+1,75 −0,4 −25,25 0 0)", sorted(diffs) == sorted(["+1,75", "−0,4", "−25,25", "0", "0"]), str(diffs))
    ok("nhân viên kho (người nhập số) không có nút Duyệt, không có menu chặn", page.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0 and page.get_by_role("button", name="Thao tác khác").count() == 0)
    ok("người nhập số có nút Sửa số đếm", page.get_by_role("link", name="Sửa số đếm").count() == 1)
    ok("không có lỗi console", not errors, str(errors[:2]))
    # KHÔNG tạo hai phiếu
    go(page, "/stocktake/")
    codes = [t.split("\t")[0] for t in page.locator("table.lt tbody tr").all_inner_texts()]
    ok("danh sách có đúng một phiếu mới KK-18 (không nhân đôi khi bấm đúp)", codes.count("KK-18") == 1 and "KK-19" not in codes, str(codes))
    # đổi người: ql1 duyệt
    before = {b: stock(page, b) for b in (101, 102, 103, 104, 105)}
    switch_user(page, "ql1")
    go(page, "/stocktake/detail/?id=18")
    ok("người khác (ql1) có nút Duyệt và điều chỉnh tồn", page.get_by_role("button", name="Duyệt và điều chỉnh tồn").is_visible())
    page.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    dlg = page.get_by_role("dialog")
    ok("hộp xác nhận nói đúng chênh lệch đã ghi lúc đếm, không nói \"theo số đếm\", không sửa lại được", dlg.get_by_text("đúng phần chênh lệch đã ghi lúc đếm", exact=False).is_visible() and dlg.get_by_text("Phiếu đã duyệt không sửa lại được", exact=False).is_visible() and re.search(r"theo số (thực )?đếm", dlg.inner_text()) is None, dlg.inner_text())
    dlg.get_by_role("button", name="Duyệt phiếu").click()
    page.get_by_text("Đã duyệt. Tồn kho đã cộng hoặc trừ theo chênh lệch đã ghi", exact=False).first.wait_for()
    ok("duyệt xong: chip Đã duyệt, hết nút Duyệt và Sửa số đếm", "Đã duyệt" in page.locator("main").inner_text() and page.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0 and page.get_by_role("link", name="Sửa số đếm").count() == 0)
    after = {b: stock(page, b) for b in (101, 102, 103, 104, 105)}
    ok("BR-KK-09: tồn sau duyệt = tồn cũ cộng chênh lệch đã chụp (kho không đổi giữa chừng nên bằng số đếm)", [after[b] for b in (101, 102, 103, 104, 105)] == ["20.250", "11.600", "0.000", "30.000", "41.750"], f"trước {before} sau {after}")
    ok("duyệt xong: có người duyệt ở thông tin", page.get_by_text("Người duyệt", exact=True).count() >= 1 and "Chị Hạnh" in page.inner_text("main"))
    page.get_by_text("Duyệt kiểm kê và cân đối sổ kho", exact=False).first.wait_for()
    ok("dòng thời gian có 'Duyệt kiểm kê và cân đối sổ kho' ngay sau khi duyệt (tải lại lịch sử)", page.get_by_text("Duyệt kiểm kê và cân đối sổ kho", exact=False).count() >= 1)
    ctx.close()


# ---------------------------------------------------------------- chi tiết, quyền duyệt, chặn
def detail_and_approval(browser):
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/stocktake/detail/?id=15")  # do Chị Hạnh (ql1) nhập số
    ok("KK-15: ql1 là người nhập số, không có nút chính Duyệt", page.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0)
    menu = more_menu(page)
    item = menu.get_by_role("menuitem", name=re.compile("Duyệt và điều chỉnh tồn"))
    ok("KK-15: Duyệt nằm mờ trong '…' kèm lý do BE trả", item.count() == 1 and item.get_attribute("aria-disabled") == "true" and "không tự duyệt được" in item.inner_text(), item.inner_text().replace("\n", "|") if item.count() else "")
    item.click(force=True)
    ok("KK-15: bấm mục mờ không mở hộp", page.get_by_role("dialog").count() == 0)
    page.keyboard.press("Escape")
    ok("KK-15: câu Tiếp theo nói cần người khác", page.get_by_text("Cần người khác duyệt phiếu này.", exact=False).first.is_visible())
    # người nhập số sửa số đếm của phiếu khác -> bị chặn duyệt (BR-KK-08)
    go(page, "/stocktake/edit/?id=16")
    ok("KK-16: ql1 mở được trang sửa", rows(page).count() == 2)
    count(page, 202, "19,5")
    page.get_by_role("button", name="Lưu nháp").click()
    page.get_by_text("Đã lưu nháp", exact=False).first.wait_for()
    go(page, "/stocktake/detail/?id=16")
    ok("KK-16: ql1 đã sửa số đếm nên không có nút Duyệt", page.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0)
    item = more_menu(page).get_by_role("menuitem", name=re.compile("Duyệt và điều chỉnh tồn"))
    ok("KK-16: lý do nói đã sửa số đếm (BR-KK-08)", item.count() == 1 and "đã sửa số đếm" in item.inner_text(), item.inner_text() if item.count() else "")
    page.keyboard.press("Escape")
    ok("KK-16: cột Cập nhật lần cuối ghi tên người sửa", "Chị Hạnh" in page.inner_text("main"))
    # Chủ duyệt được cả hai
    switch_user(page, "loc")
    go(page, "/stocktake/detail/?id=16")
    ok("loc thấy nút Duyệt ở KK-16", page.get_by_role("button", name="Duyệt và điều chỉnh tồn").is_visible())
    page.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    page.get_by_role("dialog").get_by_role("button", name="Duyệt phiếu").click()
    page.get_by_text("Đã duyệt. Tồn kho đã cộng hoặc trừ theo chênh lệch đã ghi", exact=False).first.wait_for()
    ok("BR-KK-09: tồn lô 202 = 19,5 (20 trừ chênh lệch đã chụp 0,5)", stock(page, 202) == "19.500", str(stock(page, 202)))
    ok("không có lỗi console", not errors, str(errors[:2]))

    # chi tiết KK-14: bảng đúng
    go(page, "/stocktake/detail/?id=14")
    trs = page.locator("table.lt tbody tr[data-line-row]")
    ok("KK-14: 3 dòng", trs.count() == 3)
    cut = page.evaluate("""() => { const s = document.querySelector('.lt-scroll'); const th = [...document.querySelectorAll('table.lt thead th')]; const last = th[th.length - 1].getBoundingClientRect().right; const diff = th.find((e) => e.textContent.startsWith('Chênh lệch')).getBoundingClientRect().right; return { scroll: s.scrollWidth - s.clientWidth, lastOver: last - s.getBoundingClientRect().right, diffOver: diff - s.getBoundingClientRect().right }; }""")
    ok("1280px: bảng chi tiết không cuộn ngang, cột Chênh lệch và Lý do không bị cắt", cut["scroll"] <= 1 and cut["lastOver"] <= 1 and cut["diffOver"] <= 1, str(cut))
    ok("KK-14: phiếu một kho nên bảng không có cột Kho (kho ở khối Thông tin)", page.locator("table.lt thead th").all_inner_texts() == ["Lô và mặt hàng", "Hệ thống (kg)", "Đếm được (kg)", "Chênh lệch (kg)", "Lý do"], str(page.locator("table.lt thead th").all_inner_texts()))
    ok("KK-14: dòng 101 tồn 18,5 đếm 18,1 chênh −0,4", [" ".join(c.split()) for c in trs.nth(0).locator("td").all_inner_texts()][:4] == ["L0914-CT01 Cá thu phi lê", "18,5", "18,1", "−0,4"], str(trs.nth(0).locator("td").all_inner_texts()))
    ok("KK-14: dòng dư có lý do hiện đủ", "Lần xuất 27/09/2026 ghi dư 0,3 kg" in trs.nth(2).inner_text())
    totals = page.locator("[data-totals]").inner_text().replace("\n", " ")
    ok("KK-14: tổng hụt 0,8 · dư 0,3 · ròng −0,5", "Lô hụt 2 · 0,8 kg" in totals and "Lô dư 1 · 0,3 kg" in totals and "−0,5 kg" in totals, totals)
    body = page.inner_text("main")
    ok("không có số tiền / giá vốn trong chi tiết", re.search(r"\d\s?đ\b|giá vốn", body, re.I) is None)
    ok("không hiện mã BR-/SR- trên màn", re.search(r"\b(?:BR|SR)-[A-Z]+-\d+", page.inner_text("body")) is None)
    # phiếu đã duyệt
    go(page, "/stocktake/detail/?id=13")
    ok("KK-13 đã duyệt: chip Đã duyệt, không nút Duyệt / Sửa", "Đã duyệt" in page.inner_text("main") and page.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0 and page.get_by_role("link", name="Sửa số đếm").count() == 0)
    ok("KK-13: dòng thời gian có người nhập số và người duyệt", "Nhập số kiểm kê" in page.inner_text("body") and "Duyệt kiểm kê và cân đối sổ kho" in page.inner_text("body"))
    go(page, "/stocktake/edit/?id=13")
    ok("sửa phiếu đã duyệt: báo không sửa được, có đường xem phiếu", page.get_by_text("không sửa được", exact=False).first.is_visible() and page.get_by_role("link", name="Xem phiếu").count() == 1)
    ctx.close()


# ---------------------------------------------------------------- RECON_EMPTY, RECON_STOCK_INSUFFICIENT
def approve_errors(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/stocktake/detail/?id=17")
    ok("KK-17 trống: hiện trạng thái rỗng của bảng", page.locator("[data-stocktake-empty]").is_visible())
    page.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    page.get_by_role("dialog").get_by_role("button", name="Duyệt phiếu").click()
    page.get_by_text("chưa có dòng số đếm nào", exact=False).first.wait_for()
    ok("RECON_EMPTY: câu của BE hiện đầu trang, hộp đóng lại, phiếu còn Chờ duyệt", page.get_by_role("dialog").count() == 0 and "Chờ duyệt" in page.inner_text("main"))
    # RECON_STOCK_INSUFFICIENT với line_index
    page.evaluate("() => window.__caveMock.stocktakeSetStock(202, 0.1)")
    go(page, "/stocktake/detail/?id=16")
    page.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    page.get_by_role("dialog").get_by_role("button", name="Duyệt phiếu").click()
    page.locator("[data-line-error]").first.wait_for()
    bad = page.locator("table.lt tbody tr[data-invalid='true']")
    ok("RECON_STOCK_INSUFFICIENT: báo đúng dòng (dòng 2, lô 202), dòng 1 không đỏ", bad.count() == 1 and "L0922-TS02" in bad.inner_text() and "không đủ" in bad.inner_text(), bad.inner_text().replace("\n", "|") if bad.count() else "")
    ok("phiếu vẫn Chờ duyệt, tồn không đổi", "Chờ duyệt" in page.inner_text("main") and stock(page, 202) == "0.100")
    ok("câu lỗi không còn mã (BR-…)", re.search(r"\((?:BR|SR)-", page.inner_text("main")) is None)
    ok("không có lỗi console ngoài lỗi chủ ý", not [e for e in errors if "400" not in e], str(errors[:2]))
    ctx.close()


# ---------------------------------------------------------------- 409
def conflicts(browser):
    # B2 (TL8-F3): Tải lại nhận bản mới của máy chủ, bỏ phần đang gõ, nói trước là sẽ bỏ
    ctx, page, errors = new_page(browser, "kho1")
    go(page, "/stocktake/edit/?id=16")
    count(page, 202, "19,9")
    page.evaluate("() => window.__caveMock.stocktakeEditByOther(16, {batch: 101, counted: 4})")
    page.get_by_role("button", name="Lưu nháp").click()
    banner = page.locator("[data-conflict-banner]")
    banner.wait_for()
    txt = banner.inner_text().replace("\n", " ")
    ok("409: ConflictBanner 'Phiếu vừa được Chị Lan sửa lúc dd/mm/yyyy hh:mm'", re.search(r"Phiếu vừa được Chị Lan sửa lúc \d{2}/\d{2}/\d{4} \d{2}:\d{2}", txt) is not None, txt)
    ok("409: không hiện alert đỏ, số đã gõ còn nguyên cho tới khi tải lại", page.locator("[data-form-alert='error']").count() == 0 and line(page, 202).locator("input[data-counted]").input_value() == "19,9")
    ok("409: có câu 'Thay đổi chưa lưu của bạn sẽ bị bỏ' trước khi tải lại", page.locator("[data-conflict-hint]").is_visible() and "sẽ bị bỏ" in page.locator("[data-conflict-hint]").inner_text())
    banner.get_by_role("button", name="Tải lại").click()
    page.wait_for_function("() => !document.querySelector('[data-conflict-banner]')", timeout=10_000)
    ok("Tải lại: banner mất, dòng người kia thêm (lô 101) hiện ra", line(page, 101).count() == 1 and line(page, 101).locator("input[data-counted]").input_value() == "4")
    ok("Tải lại: số đang gõ bị bỏ, về số của máy chủ (19,7)", line(page, 202).locator("input[data-counted]").input_value() == "19,7", line(page, 202).locator("input[data-counted]").input_value())
    ok("Tải lại: câu cảnh báo hết", page.locator("[data-conflict-hint]").count() == 0)
    page.get_by_role("button", name="Lưu nháp").click()
    page.get_by_text("Đã lưu nháp", exact=False).first.wait_for()
    ok("lưu lại sau khi tải lại: thành công, không 409", page.locator("[data-conflict-banner]").count() == 0)
    ok("lưu lại: cả hai dòng (202 và 101) còn trong phiếu", line(page, 202).count() == 1 and line(page, 101).count() == 1)
    ctx.close()

    # B1 (TL8-F1): đổi ghi chú + dòng trên trang cũ -> 409, KHÔNG ghi đè ghi chú của người kia
    ctx, page, errors = new_page(browser, "kho1")
    go(page, "/stocktake/edit/?id=16")
    page.evaluate("() => window.__caveMock.stocktakeEditByOther(16, {note: 'Ghi chú của chị Lan'})")
    page.get_by_label("Ghi chú").fill("Ghi chú của tôi, đè lên")
    count(page, 202, "19,9")
    page.get_by_role("button", name="Lưu nháp").click()
    page.locator("[data-conflict-banner]").wait_for()
    ok("ghi chú + 409: hiện banner", page.locator("[data-conflict-banner]").is_visible())
    note_on_server = page.evaluate("() => { const s = JSON.parse(localStorage.getItem('cave_erp_mock_stocktake') || '{}'); const r = (s.recs || []).find(x => x.id === 16); return r ? r.note : null; }")
    ok("ghi chú + 409: ghi chú trên máy chủ vẫn của chị Lan (không PATCH)", note_on_server == "Ghi chú của chị Lan", str(note_on_server))
    page.get_by_role("button", name="Tải lại").click()
    page.wait_for_function("() => !document.querySelector('[data-conflict-banner]')", timeout=10_000)
    ok("Tải lại: ô ghi chú là của chị Lan", page.get_by_label("Ghi chú").input_value() == "Ghi chú của chị Lan", page.get_by_label("Ghi chú").input_value())
    ctx.close()


# ---------------------------------------------------------------- lỗi phụ của form
def form_edges(browser):
    ctx, page, errors = new_page(browser, "kho1")
    go(page, "/stocktake/new/")
    pick_warehouse(page, "Kho dự phòng")
    ok("kho không còn lô: trạng thái rỗng, nói chọn kho khác", rows(page).count() == 0 and page.get_by_text("Kho này chưa có lô nào còn tồn").is_visible())
    pick_warehouse(page, "Kho mát chợ Vũng Tàu")
    ok("đổi kho: nạp 2 lô của kho Vũng Tàu", rows(page).count() == 2)
    count(page, 201, "14,2")
    pick_warehouse(page, WAREHOUSE_STAFF)
    ok("đổi kho: giữ dòng đã nhập của kho cũ, bỏ dòng chưa chạm", rows(page).count() == 6 and line(page, 201).locator("input[data-counted]").input_value() == "14,2" and line(page, 202).count() == 0, str(rows(page).count()))
    page.get_by_label("Ngày kiểm kê").fill("")
    page.get_by_role("button", name="Gửi duyệt").click()
    ok("ngày trống: báo chọn ngày", page.get_by_text("Chọn ngày kiểm kê.").first.is_visible() and "/stocktake/new/" in page.url)
    page.get_by_label("Ngày kiểm kê").fill("2026-10-02")
    ok("lý do giới hạn 500 ký tự", page.locator("input[data-reason]").first.get_attribute("maxlength") == "500")
    ok("ô số đếm dùng bàn phím số thập phân", page.locator("input[data-counted]").first.get_attribute("inputmode") == "decimal")
    # id sai
    go(page, "/stocktake/edit/?id=abc")
    ok("edit?id=abc: không tìm thấy trang", page.get_by_text("Không tìm thấy", exact=False).first.is_visible())
    go(page, "/stocktake/edit/?id=999")
    ok("edit?id=999: không tìm thấy", page.get_by_text("Không tìm thấy", exact=False).first.is_visible())
    go(page, "/stocktake/detail/?id=999")
    ok("detail?id=999: không tìm thấy", page.get_by_text("Không tìm thấy", exact=False).first.is_visible())
    go(page, "/stocktake/detail/")
    ok("detail không có id: không tìm thấy", page.get_by_text("Không tìm thấy", exact=False).first.is_visible())
    # dữ liệu cá nhân
    dump = storage_dump(page)
    ok("localStorage/sessionStorage không có SĐT / địa chỉ khách", re.search(r"0900000\d{3}|Hải Phòng|Khách Thử", dump) is None)
    ctx.close()


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])")


# ---------------------------------------------------------------- 360px
def mobile(browser):
    ctx, page, errors = new_page(browser, "kho1", 360, 740)
    go(page, "/stocktake/")
    ok("360px danh sách: không cuộn ngang", no_hscroll(page))
    ok("360px danh sách: nút Lập phiếu kiểm kê cao >= 44px", page.get_by_role("link", name="Lập phiếu kiểm kê").first.bounding_box()["height"] >= 43.5)
    page.screenshot(path=os.path.join(SHOTS, "ed28_list_360.png"), full_page=True)
    go(page, "/stocktake/new/")
    pick_warehouse(page, WAREHOUSE_STAFF)
    count(page, 101, "20,25")
    page.get_by_role("button", name="Lưu nháp").click()
    ok("360px form: không cuộn ngang (kể cả khi có lỗi dòng)", no_hscroll(page))
    inputs = page.locator("input[data-counted]").first.bounding_box()
    ok("360px form: ô số đếm cao >= 44px", inputs["height"] >= 43.5, str(inputs))
    page.screenshot(path=os.path.join(SHOTS, "ed28_form_360.png"), full_page=True)
    go(page, "/stocktake/detail/?id=14")
    ok("360px chi tiết: không cuộn ngang", no_hscroll(page))
    page.screenshot(path=os.path.join(SHOTS, "ed28_detail_360.png"), full_page=True)
    go(page, "/stocktake/edit/?id=14")
    ok("360px sửa: không cuộn ngang", no_hscroll(page))
    ctx.close()
    ctx, page, _ = new_page(browser, "ql1", 360, 740)
    go(page, "/stocktake/detail/?id=15")
    ok("360px chi tiết (Duyệt bị chặn): không cuộn ngang", no_hscroll(page))
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for fn in (role_access, list_screen, create_flow, detail_and_approval, approve_errors, conflicts, form_edges, mobile):
        try:
            fn(browser)
        except Exception as exc:  # một nhóm lỗi không làm mất kết quả các nhóm khác
            ok(f"{fn.__name__}: chạy không ném lỗi", False, repr(exc)[:400])
    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} đạt")
sys.exit(1 if failed else 0)
