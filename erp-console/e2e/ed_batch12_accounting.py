# E2E ERP theo design Lô 12 (Kế toán, ED-32 Báo cáo lãi lỗ · ED-33 Hoá đơn bán · ED-34 Hoá đơn mua & chi phí phụ): bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3501 --bind 127.0.0.1 &)
#   BASE=http://127.0.0.1:3501 SHOTS=<thư mục ảnh> python3 e2e/ed_batch12_accounting.py      # tắt server sau khi xong
# Trạng thái mock nằm trong bộ nhớ trang: page.goto làm về seed, nên luồng ghi đi bằng bấm menu / bấm nút, không gõ URL.
# Kiểm: loc thấy cả ba màn (có Giá vốn, Lãi gộp) · ql1 chỉ Hoá đơn bán (không giá vốn) + Hoá đơn mua thấy số tiền nhưng không có tab Chi phí phụ / nút thêm ·
# kho1 chỉ Hoá đơn bán, không cột giá vốn, không tên khách · giao1 / cs2 không có menu, vào thẳng thì "không có quyền" ·
# kỳ trống · chế độ lỗi · bộ lọc · hộp Thêm hoá đơn (lỗi ô trống, "Đã trả tiền" mở "Trả lúc") · 360px · không rò dữ liệu cá nhân ra storage/URL.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3501")
SHOTS = os.environ.get("SHOTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shots"))
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)

SMALL_TAPS_JS = """() => [...document.querySelectorAll('button, a, input, select')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y < innerHeight
      && !e.classList.contains('sr-only') && !e.classList.contains('lt-link') && !e.matches('input[type=checkbox]') && (r.height < 44 || (!['INPUT', 'SELECT'].includes(e.tagName) && r.width < 44));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""

NO_PERM = "không có quyền"


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra if not cond else "")


def new_page(browser, user, w=1366, h=900, mobile=False, errors=None):
    opts = {"viewport": {"width": w, "height": h}, "reduced_motion": "reduce"}
    if mobile:
        opts.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**opts)
    page = ctx.new_page()
    if errors is not None:
        page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and "Failed to load resource" not in m.text and errors.append(f"[{user}] {m.text}"))
        page.on("pageerror", lambda e: errors.append(f"[{user}] {e}"))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")
    return ctx, page


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)
    page.wait_for_timeout(150)


def body(page):
    return page.locator("body").inner_text()


def main_text(page):
    return page.locator("main").inner_text() if page.locator("main").count() else body(page)


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def menu_labels(page):
    # Mỗi mục có chữ tên biểu tượng đứng trước nhãn: bỏ dòng đầu.
    return [x.strip().split("\n")[-1].strip() for x in page.locator(".nav a").all_inner_texts()]


def go_menu(page, label, url):
    """Bấm menu nếu thấy (giữ trạng thái mock), nếu không (điện thoại) gõ URL."""
    link = page.locator(".nav a", has_text=label).first
    if link.count() and link.is_visible():
        link.click()
    else:
        page.goto(BASE + url)
    page.wait_for_url("**" + url + "**")
    settle(page)


def heads(page):
    t = page.locator("table.lt").first
    return [re.sub(r"\s+", " ", h).split(" lock")[0].split("lock")[0].strip() for h in t.locator("thead th").all_inner_texts()]


def wait_table(page):
    t = page.locator("table.lt").first
    expect(t.locator("tbody tr").first).to_be_visible()
    expect(t.locator("tr.lt-skel")).to_have_count(0)
    settle(page)
    return t


def storage_dump(page):
    # Bỏ các khoá `cave_erp_mock_*`: đó là kho dữ liệu bịa của mock Lô 5/Lô 2 (chỉ có ở bản build mock, bị check-no-mock gỡ khỏi bản thật), không phải mã của Lô 12.
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage).filter(([k]) => !k.startsWith('cave_erp_mock_')), Object.entries(sessionStorage).filter(([k]) => !k.startsWith('cave_erp_mock_')), location.href])")


def rows_count(page):
    return page.locator("table.lt tbody tr").count()


# ---------------------------------------------------------------- Chủ (loc)
def run_owner(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    labels = menu_labels(page)
    ok("Chủ: menu có Báo cáo lãi lỗ, Hoá đơn bán, Hoá đơn mua & chi phí", all(x in labels for x in ("Báo cáo lãi lỗ", "Hoá đơn bán", "Hoá đơn mua & chi phí")), str(labels))
    ok("Chủ: không còn nhãn 'sắp có' ở menu Kế toán", "Sắp có" not in body(page))

    # ---- Báo cáo lãi lỗ
    go_menu(page, "Báo cáo lãi lỗ", "/reports/")
    wait_table(page)
    txt = main_text(page)
    ok("Báo cáo: có Doanh thu ghi nhận, Giá vốn ghi nhận, Lãi/lỗ tháng", all(x in txt for x in ("Doanh thu ghi nhận", "Giá vốn ghi nhận", "Lãi/lỗ tháng")), txt[:300])
    ok("Báo cáo: số liệu tháng này khớp công thức (lãi 5.600.000 đ)", page.get_by_test_id("stat-profit").inner_text().replace("\u00a0", " ").strip().startswith("5.600.000"), page.get_by_test_id("stat-profit").inner_text())
    ok("Báo cáo: so với tháng trước có chữ 'giảm' (lãi T9 8.400.000 đ)", "giảm 2.800.000 đ so với T9" in txt, txt[:600])
    br = page.get_by_test_id("breakdown")
    ok("Báo cáo: Cấu thành lãi có 6 dòng (5 thành phần + tổng)", br.locator("li").count() == 6, str(br.locator("li").count()))
    ok("Báo cáo: có ghi chú tiêu chí 'lô phát sinh trong tháng'", "lô phát sinh trong tháng" in page.get_by_test_id("report-criterion").inner_text())
    h = heads(page)
    ok("Báo cáo: cột bảng lô đủ 9 cột (có Doanh thu, Tổng chi phí, Lãi/lỗ)", h == ["Lô", "Mặt hàng", "Trạng thái", "Nhập", "Đã bán", "Doanh thu", "Tổng chi phí", "Lãi/lỗ", "Ghi chú"], str(h))
    ok("Báo cáo: tháng này 12 lô, tab Tất cả đếm 12", rows_count(page) == 12 and "12" in page.get_by_role("tab", name=re.compile("^Tất cả")).inner_text())
    ok("Báo cáo: lô lỗ có dấu trừ (−)", re.search(r"[−-]2\.880\.000 đ", main_text(page)) is not None)
    ok("Báo cáo: không có chữ NCC / SĐT / mã BR", "NCC" not in txt and "SĐT" not in txt and not re.search(r"\bBR-", txt))
    page.screenshot(path=f"{SHOTS}/ed12-1-loc-bao-cao.png", full_page=True)

    # Tab Đã chốt / Tạm tính trong tháng này
    page.get_by_role("tab", name=re.compile("^Đã chốt")).click()
    settle(page)
    ok("Báo cáo: tháng này chưa lô nào chốt thì hiện trạng thái rỗng có 'Xem tất cả'", page.get_by_role("button", name="Xem tất cả").count() == 1, body(page)[:200])
    page.get_by_role("button", name="Xem tất cả").click()
    settle(page)
    ok("Báo cáo: 'Xem tất cả' trả lại 12 lô", rows_count(page) == 12)
    page.get_by_role("tab", name=re.compile("^Tạm tính")).click()
    settle(page)
    ok("Báo cáo: tab Tạm tính còn đủ 12 lô, mọi dòng ghi 'Tạm tính'", rows_count(page) == 12 and page.locator("table.lt tbody td", has_text="Tạm tính").count() == 12)
    page.get_by_role("tab", name=re.compile("^Tất cả")).click()
    settle(page)

    # Chi tiết lô
    page.get_by_role("button", name="Xem chi tiết lô LO-0924-D").click()
    detail = page.get_by_test_id("batch-detail")
    detail.wait_for()
    dt = detail.inner_text()
    ok("Báo cáo: chi tiết lô có thành phần doanh thu, chi phí, lãi/lỗ và phần 'chỉ để tham khảo'", "Tôm sú size 30" in dt and "tham khảo" in dt and detail.locator("[data-line=profit]").count() == 1, dt[:300])
    page.screenshot(path=f"{SHOTS}/ed12-2-loc-chi-tiet-lo.png")
    page.keyboard.press("Escape")
    ok("Báo cáo: Esc đóng hộp chi tiết", page.get_by_test_id("batch-detail").count() == 0)
    # TL12-FE-M2: chi tiết lô là hộp thoại (Modal), có nút Đóng, không phải tấm trượt bên.
    page.get_by_role("button", name="Xem chi tiết lô LO-0924-D").click()
    page.get_by_test_id("batch-detail").wait_for()
    dlg = page.get_by_role("dialog")
    ok("Báo cáo: chi tiết lô mở trong hộp thoại có nút Đóng", dlg.count() == 1 and dlg.get_by_role("button", name="Đóng", exact=True).count() >= 1, str(dlg.count()))
    dlg.get_by_role("button", name="Đóng", exact=True).last.click()
    ok("Báo cáo: bấm Đóng thì hộp chi tiết biến mất", page.get_by_test_id("batch-detail").count() == 0)

    # Đổi tháng: tháng trước có lô đã chốt, tháng xa thì kỳ trống
    sel = page.get_by_test_id("report-month")
    sel.select_option(index=1)
    settle(page)
    ok("Báo cáo: tháng trước có 12 lô", rows_count(page) == 12)
    ok("Báo cáo: tháng trước hiện số liệu, không trạng thái trống", page.get_by_test_id("period-empty").count() == 0)
    sel.select_option(index=8)
    settle(page)
    ok("Báo cáo: kỳ không giao dịch hiện trạng thái trống (không số 0 giả)", page.get_by_test_id("period-empty").count() == 1 and "chưa có giao dịch" in page.get_by_test_id("period-empty").inner_text())
    ok("Báo cáo: kỳ trống thì danh sách lô báo 'Không có lô nào phát sinh'", "Không có lô nào phát sinh" in main_text(page))
    page.screenshot(path=f"{SHOTS}/ed12-3-loc-ky-trong.png")
    ok("Báo cáo: tháng chọn không lên URL", "month" not in page.url and "2026" not in page.url.split("/reports/")[-1])
    sel.select_option(index=0)
    settle(page)

    # Chế độ lỗi
    page.evaluate("() => window.__caveMock.reports('fail')")
    sel.select_option(index=1)
    page.wait_for_timeout(400)
    settle(page)
    ok("Báo cáo: lỗi máy chủ hiện thông báo + nút Thử lại, không số liệu cũ", page.get_by_role("button", name="Thử lại").count() >= 1 and page.get_by_test_id("breakdown").count() == 0, main_text(page)[:200])
    page.screenshot(path=f"{SHOTS}/ed12-4-loc-loi.png")
    page.evaluate("() => window.__caveMock.reports('ok')")
    page.get_by_role("button", name="Thử lại").first.click()
    settle(page)
    ok("Báo cáo: sửa chế độ rồi Thử lại thì có số liệu", page.get_by_test_id("breakdown").count() == 1)

    # ---- Hoá đơn bán
    go_menu(page, "Hoá đơn bán", "/accounting/sales-invoices/")
    t = wait_table(page)
    h = heads(page)
    ok("Hoá đơn bán (Chủ): cột có Giá vốn và Lãi gộp", "Giá vốn" in h and "Lãi gộp" in h and "Khách hàng" in h, str(h))
    ok("Hoá đơn bán: 'Đang hiện 20 / 27 hoá đơn'", "Đang hiện 20 / 27 hoá đơn" in body(page))
    note = page.get_by_test_id("invoice-note")
    ok("Hoá đơn bán: chỉ một câu ngắn ở chân bảng 'Không tính hoá đơn Đã huỷ.', không còn khối ghi chú phía trên", note.count() == 1 and note.inner_text().strip() == "Không tính hoá đơn Đã huỷ.", note.inner_text() if note.count() else "")
    tot = page.get_by_test_id("invoice-totals")
    ok("Hoá đơn bán: chân bảng có Tổng số tiền và Lãi gộp", page.get_by_test_id("total-amount").count() == 1 and page.get_by_test_id("total-profit").count() == 1 and "đ" in tot.inner_text(), tot.inner_text())
    ok("Hoá đơn bán: có nút Tải thêm; không có nút tạo hoá đơn", page.get_by_role("button", name="Tải thêm").count() == 1 and page.get_by_role("button", name=re.compile("^(Thêm|Tạo)")).count() == 0)
    amount_all = page.get_by_test_id("total-amount").inner_text()
    page.get_by_role("button", name="Tải thêm").click()
    settle(page)
    ok("Hoá đơn bán: Tải thêm đủ 27 dòng, hết nút Tải thêm", rows_count(page) == 27 and page.get_by_role("button", name="Tải thêm").count() == 0)
    ok("Hoá đơn bán: tổng số tiền là của cả kết quả (không đổi khi tải thêm)", page.get_by_test_id("total-amount").inner_text() == amount_all)
    page.screenshot(path=f"{SHOTS}/ed12-5-loc-hoa-don-ban.png", full_page=True)

    sel = page.get_by_label("Trạng thái hoá đơn")
    sel.select_option(label="Đã huỷ")
    settle(page)
    ok("Hoá đơn bán: lọc Đã huỷ còn 3 dòng", rows_count(page) == 3, str(rows_count(page)))
    ok("Hoá đơn bán: tổng số tiền khi chỉ lọc Đã huỷ là 0 đ (huỷ không tính)", page.get_by_test_id("total-amount").inner_text().strip().startswith("0"), page.get_by_test_id("total-amount").inner_text())
    page.get_by_role("button", name="Bỏ lọc").first.click()
    settle(page)
    ok("Hoá đơn bán: Bỏ lọc trả lại danh sách", rows_count(page) >= 20)
    box = page.get_by_role("searchbox", name="Tìm hoá đơn bán").or_(page.get_by_placeholder("Tìm mã hoá đơn hoặc mã đơn")).first
    box.fill("INV00005")
    page.wait_for_timeout(500)
    settle(page)
    ok("Hoá đơn bán: tìm INV00005 ra đúng 1 dòng", rows_count(page) == 1 and "INV00005" in main_text(page))
    box.fill("khongtontai")
    page.wait_for_timeout(500)
    settle(page)
    ok("Hoá đơn bán: tìm không ra thì có nút Bỏ lọc", rows_count(page) == 0 and page.get_by_role("button", name="Bỏ lọc").count() >= 1)
    page.get_by_role("button", name="Bỏ lọc").first.click()
    settle(page)
    # Khoảng ngày sai
    df = page.locator("input[type=date]")
    df.nth(0).fill("2026-10-05")
    df.nth(1).fill("2026-10-01")
    page.wait_for_timeout(300)
    ok("Hoá đơn bán: khoảng ngày ngược thì báo dưới ô, không gọi lỗi", page.get_by_role("alert").filter(has_text="Ngày bắt đầu đang sau ngày kết thúc").count() == 1)
    page.get_by_role("button", name="Bỏ lọc").first.click()
    settle(page)

    # Lỗi
    page.evaluate("() => window.__caveMock.salesInvoices('fail')")
    sel.select_option(label="Đã xuất")
    page.wait_for_timeout(400)
    settle(page)
    ok("Hoá đơn bán: lỗi máy chủ hiện thông báo + Thử lại", page.get_by_role("button", name="Thử lại").count() >= 1, main_text(page)[:200])
    page.evaluate("() => window.__caveMock.salesInvoices('ok')")
    page.get_by_role("button", name="Thử lại").first.click()
    settle(page)
    ok("Hoá đơn bán: Thử lại thành công", rows_count(page) >= 1)

    # Bấm dòng mở đơn
    page.get_by_role("link", name="DH327").first.click()
    page.wait_for_url("**/orders/detail/**")
    ok("Hoá đơn bán: bấm mã đơn mở chi tiết đơn", "/orders/detail/" in page.url)

    # ---- Hoá đơn mua & chi phí phụ
    go_menu(page, "Hoá đơn mua & chi phí", "/accounting/purchase-invoices/")
    wait_table(page)
    tabs = [re.sub(r"\s+", " ", x).strip() for x in page.get_by_role("tab").all_inner_texts()]
    ok("Hoá đơn mua (Chủ): hai tab Hoá đơn mua · Chi phí phụ", tabs == ["Hoá đơn mua", "Chi phí phụ"], str(tabs))
    h = heads(page)
    ok("Hoá đơn mua: có cột Số tiền và Trả lúc", "Số tiền" in h and "Trả lúc" in h, str(h))
    ok("Hoá đơn mua: dòng tóm tắt 'Đang hiện n / m hoá đơn · k chưa trả'", re.search(r"Đang hiện \d+ / \d+ hoá đơn · \d+ chưa trả", body(page)) is not None, body(page)[:300])
    ok("Hoá đơn mua: Chủ có nút Thêm hoá đơn mua", page.get_by_test_id("add-invoice").count() == 1)
    ok("Hoá đơn mua: hoá đơn đã trả có giờ 'dd/mm/yyyy hh:mm'", re.search(r"\d\d/\d\d/\d{4} \d\d:\d\d", main_text(page)) is not None)
    page.screenshot(path=f"{SHOTS}/ed12-6-loc-hoa-don-mua.png", full_page=True)

    # Hộp Thêm hoá đơn
    page.get_by_test_id("add-invoice").click()
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    settle(page)
    dlg.get_by_role("button", name="Lưu hoá đơn").click()
    page.wait_for_timeout(200)
    dt = dlg.inner_text()
    ok("Thêm hoá đơn: bỏ trống thì báo lỗi nhà cung cấp / số tiền ngay dưới ô, hộp vẫn mở", dlg.is_visible() and "Nhập số tiền lớn hơn 0." in dt, dt[:300])
    ok("Thêm hoá đơn: chưa tick 'Đã trả tiền' thì không có ô 'Trả lúc'", page.get_by_test_id("paid-at").count() == 0)
    dlg.get_by_label("Đã trả tiền").check()
    ok("Thêm hoá đơn: tick 'Đã trả tiền' hiện ô 'Trả lúc' có giờ mặc định", page.get_by_test_id("paid-at").count() == 1 and re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d", dlg.locator("input[name=paid_at]").input_value()) is not None, dlg.locator("input[name=paid_at]").input_value() if dlg.locator("input[name=paid_at]").count() else "")
    dlg.locator("input[name=paid_at]").fill("")
    dlg.get_by_role("button", name="Lưu hoá đơn").click()
    page.wait_for_timeout(200)
    ok("Thêm hoá đơn: bỏ trống 'Trả lúc' thì báo 'Chọn giờ trả tiền.'", "Chọn giờ trả tiền." in dlg.inner_text(), dlg.inner_text()[:300])
    # Chọn nhà cung cấp -> bộ chọn phiếu nhập lọc theo nhà cung cấp
    sup = dlg.locator("select[name=supplier]")
    ok("Thêm hoá đơn: có ô chọn nhà cung cấp và bộ chọn phiếu nhập", sup.count() == 1 and page.get_by_test_id("receipt-select").count() == 1)
    sup_opts = sup.locator("option").all_inner_texts()
    picked = False
    for i in range(1, len(sup_opts)):
        sup.select_option(index=i)
        settle(page)
        page.wait_for_timeout(300)
        if page.get_by_test_id("receipt-count").count() == 1:
            picked = True
            break
    ok("Thêm hoá đơn: có nhà cung cấp mà bộ chọn phiếu nhập hiện 'Đang hiện n / m phiếu nhập'", picked, str(sup_opts[:4]))
    page.screenshot(path=f"{SHOTS}/ed12-7-loc-them-hoa-don.png")
    # Chọn phiếu có tiền mua thì gợi ý số tiền (làm tròn đồng)
    rsel = dlg.locator("select[name=receipt]")
    if rsel.locator("option").count() > 1:
        rsel.select_option(index=1)
        page.wait_for_timeout(200)
        amt = dlg.locator("input[name=amount]").input_value()
        ok("Thêm hoá đơn: chọn phiếu thì gợi ý số tiền nguyên đồng, nhóm nghìn", re.fullmatch(r"\d{1,3}(\.\d{3})*", amt) is not None, amt)
        # TL12-FE-M1: chọn phiếu rồi đổi sang nhà cung cấp khác thì bỏ phiếu và số gợi ý, không gửi cặp lệch.
        receipt_supplier = sup.input_value()
        other = next((v for v in sup.locator("option").evaluate_all("els => els.map(e => e.value)") if v and v != receipt_supplier), None)
        ok("Thêm hoá đơn: có nhà cung cấp thứ hai để thử đổi", other is not None, receipt_supplier)
        if other:
            sup.select_option(value=other)
            settle(page)
            page.wait_for_timeout(300)
            ok("Thêm hoá đơn: đổi nhà cung cấp thì bỏ phiếu đang chọn (M1)", dlg.locator("select[name=receipt]").input_value() == "", dlg.locator("select[name=receipt]").input_value())
            ok("Thêm hoá đơn: đổi nhà cung cấp thì bỏ số tiền gợi ý của phiếu cũ", dlg.locator("input[name=amount]").input_value() == "", dlg.locator("input[name=amount]").input_value())
            # Số do người gõ thì giữ khi đổi nhà cung cấp, nhưng phiếu vẫn bị bỏ.
            sup.select_option(value=receipt_supplier)
            settle(page)
            page.wait_for_timeout(300)
            rsel = dlg.locator("select[name=receipt]")
            if rsel.locator("option").count() > 1:
                rsel.select_option(index=1)
                page.wait_for_timeout(200)
                dlg.locator("input[name=amount]").fill("123456")
                sup.select_option(value=other)
                settle(page)
                page.wait_for_timeout(300)
                ok("Thêm hoá đơn: số tiền người gõ được giữ, phiếu vẫn bị bỏ khi đổi nhà cung cấp", dlg.locator("input[name=amount]").input_value() == "123.456" and dlg.locator("select[name=receipt]").input_value() == "", dlg.locator("input[name=amount]").input_value())
    else:
        ok("Thêm hoá đơn: có ít nhất một phiếu nhập để chọn", False, dlg.inner_text()[:200])
    dlg.get_by_role("button", name="Quay lại").click()
    ok("Thêm hoá đơn: Huỷ đóng hộp", page.get_by_role("dialog").count() == 0)

    # Tab Chi phí phụ
    page.get_by_role("tab", name="Chi phí phụ").click()
    settle(page)
    wait_table(page)
    ok("Chi phí phụ: có nút Thêm chi phí phụ", page.get_by_test_id("add-cost").count() == 1)
    ok("Chi phí phụ: cột Loại chi phí, Số tiền, Cách chia, Ngày phát sinh", all(x in heads(page) for x in ("Loại chi phí", "Số tiền", "Cách chia", "Ngày phát sinh")), str(heads(page)))
    ok("Chi phí phụ: tab chọn không lên URL dạng dữ liệu cá nhân, mở lại ?tab=costs được", "tab=costs" in page.url, page.url)
    page.screenshot(path=f"{SHOTS}/ed12-8-loc-chi-phi-phu.png", full_page=True)
    page.get_by_test_id("add-cost").click()
    page.wait_for_url("**/purchasing/costs/new/**")
    page.wait_for_selector("select[name=supplier_filter]", timeout=10_000)
    settle(page)
    ok("Form chi phí: có bộ lọc nhà cung cấp và bộ chọn phiếu nhập", page.locator("select[name=supplier_filter]").count() == 1 and page.get_by_test_id("receipt-select").count() == 1)
    page.screenshot(path=f"{SHOTS}/ed12-9-loc-form-chi-phi.png", full_page=True)

    ok("Chủ: không cuộn ngang ở màn kế toán", no_hscroll(page))
    dump = storage_dump(page)
    ok("Chủ: không rò dữ liệu cá nhân vào storage/URL", not any(x in dump for x in ("(mẫu)", "0901234567", "0912345678")), str([x for x in ("(mẫu)", "0901234567", "0912345678") if x in dump]))
    ctx.close()


# ---------------------------------------------------------------- Quản lý (ql1)
def run_manager(browser, errors):
    ctx, page = new_page(browser, "ql1", errors=errors)
    labels = menu_labels(page)
    ok("Quản lý: menu có Hoá đơn bán và Hoá đơn mua & chi phí, không có Báo cáo lãi lỗ", "Hoá đơn bán" in labels and "Hoá đơn mua & chi phí" in labels and "Báo cáo lãi lỗ" not in labels, str(labels))

    go_menu(page, "Hoá đơn bán", "/accounting/sales-invoices/")
    wait_table(page)
    h = heads(page)
    ok("Quản lý: Hoá đơn bán có Khách hàng, KHÔNG có Giá vốn / Lãi gộp", "Khách hàng" in h and "Giá vốn" not in h and "Lãi gộp" not in h, str(h))
    ok("Quản lý: chân bảng có tổng số tiền, KHÔNG có Lãi gộp", page.get_by_test_id("total-amount").count() == 1 and page.get_by_test_id("total-profit").count() == 0)
    html = page.content()
    ok("Quản lý: DOM không chứa giá vốn / lãi gộp", "Lãi gộp" not in html and "Giá vốn" not in html)
    page.screenshot(path=f"{SHOTS}/ed12-10-ql1-hoa-don-ban.png")

    go_menu(page, "Hoá đơn mua & chi phí", "/accounting/purchase-invoices/")
    wait_table(page)
    ok("Quản lý: không có tab Chi phí phụ", page.get_by_role("tab", name="Chi phí phụ").count() == 0)
    ok("Quản lý: thấy số tiền hoá đơn mua (quyết định D-3)", "3.577.200 đ" in main_text(page), main_text(page)[:300])
    ok("Quản lý: không có nút Thêm hoá đơn mua / Thêm chi phí phụ", page.get_by_test_id("add-invoice").count() == 0 and page.get_by_test_id("add-cost").count() == 0)
    page.goto(BASE + "/accounting/purchase-invoices/?tab=costs")
    page.wait_for_load_state("networkidle")
    ok("Quản lý: ?tab=costs không mở được danh sách chi phí phụ", "Danh sách chi phí phụ" not in body(page) and page.get_by_role("tab", name="Chi phí phụ").count() == 0)
    page.screenshot(path=f"{SHOTS}/ed12-11-ql1-hoa-don-mua.png")

    page.goto(BASE + "/reports/")
    page.wait_for_load_state("networkidle")
    ok("Quản lý: vào thẳng /reports/ thì 'không có quyền', không có số liệu", NO_PERM in body(page).lower() and "Doanh thu ghi nhận" not in body(page))
    ctx.close()


# ---------------------------------------------------------------- NV kho (kho1)
def run_warehouse(browser, errors):
    ctx, page = new_page(browser, "kho1", errors=errors)
    labels = menu_labels(page)
    ok("NV kho: menu có Hoá đơn bán, không có Hoá đơn mua & chi phí / Báo cáo lãi lỗ", "Hoá đơn bán" in labels and "Hoá đơn mua & chi phí" not in labels and "Báo cáo lãi lỗ" not in labels, str(labels))
    go_menu(page, "Hoá đơn bán", "/accounting/sales-invoices/")
    wait_table(page)
    h = heads(page)
    ok("NV kho: bảng chỉ có Mã hoá đơn, Đơn, Ngày xuất, Số tiền, Trạng thái", h == ["Mã hoá đơn", "Đơn", "Ngày xuất", "Số tiền", "Trạng thái"], str(h))
    html = page.content()
    ok("NV kho: DOM không có tên khách, giá vốn, lãi gộp", "(mẫu)" not in html and "Lãi gộp" not in html and "Giá vốn" not in html and "Khách hàng" not in html)
    ok("NV kho: chân bảng không có Lãi gộp", page.get_by_test_id("total-profit").count() == 0)
    page.screenshot(path=f"{SHOTS}/ed12-12-kho1-hoa-don-ban.png", full_page=True)
    for url in ("/accounting/purchase-invoices/", "/reports/"):
        page.goto(BASE + url)
        page.wait_for_load_state("networkidle")
        ok(f"NV kho: vào thẳng {url} thì 'không có quyền'", NO_PERM in body(page).lower(), body(page)[:150])
    ctx.close()


# ---------------------------------------------------------------- giao1, cs2
def run_denied(browser, errors, user):
    ctx, page = new_page(browser, user, errors=errors)
    labels = menu_labels(page)
    ok(f"{user}: menu không có Báo cáo lãi lỗ / Hoá đơn bán / Hoá đơn mua & chi phí", not any(x in labels for x in ("Báo cáo lãi lỗ", "Hoá đơn bán", "Hoá đơn mua & chi phí")), str(labels))
    for url in ("/reports/", "/accounting/sales-invoices/", "/accounting/purchase-invoices/"):
        page.goto(BASE + url)
        page.wait_for_load_state("networkidle")
        ok(f"{user}: vào thẳng {url} thì 'không có quyền'", NO_PERM in body(page).lower() and page.locator("table.lt").count() == 0, body(page)[:150])
    ctx.close()


# ---------------------------------------------------------------- 360px
def run_mobile(browser, errors):
    ctx, page = new_page(browser, "loc", w=360, h=800, mobile=True, errors=errors)
    for name, url, shot in (
        ("Báo cáo", "/reports/", "ed12-13-m-bao-cao.png"),
        ("Hoá đơn bán", "/accounting/sales-invoices/", "ed12-14-m-hoa-don-ban.png"),
        ("Hoá đơn mua & chi phí", "/accounting/purchase-invoices/", "ed12-15-m-hoa-don-mua.png"),
    ):
        page.goto(BASE + url)
        page.wait_for_load_state("networkidle")
        settle(page)
        page.wait_for_timeout(300)
        ok(f"360px {name}: không cuộn ngang trang", no_hscroll(page))
        small = page.evaluate(SMALL_TAPS_JS)
        ok(f"360px {name}: nút / liên kết / ô nhập đủ 44px", not small, str(small[:6]))
        page.screenshot(path=f"{SHOTS}/{shot}", full_page=True)
    # Hộp Thêm hoá đơn trên điện thoại
    page.get_by_test_id("add-invoice").click()
    page.get_by_role("dialog").wait_for()
    settle(page)
    page.get_by_label("Đã trả tiền").check()
    ok("360px: hộp Thêm hoá đơn không cuộn ngang, nút Lưu hoá đơn thấy được", no_hscroll(page) and page.get_by_role("button", name="Lưu hoá đơn").is_visible())
    page.screenshot(path=f"{SHOTS}/ed12-16-m-them-hoa-don.png")
    ctx.close()


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        run_owner(browser, errors)
        run_manager(browser, errors)
        run_warehouse(browser, errors)
        run_denied(browser, errors, "giao1")
        run_denied(browser, errors, "cs2")
        run_mobile(browser, errors)
        browser.close()
    ok("Không có lỗi console / pageerror", not errors, "; ".join(errors[:5]))
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
    for r in failed:
        print("FAIL:", r[0], r[2])
    sys.exit(1 if failed else 0)


main()
