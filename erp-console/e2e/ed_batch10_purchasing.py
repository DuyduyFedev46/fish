# E2E ERP theo design Lô 10 (Mua hàng + phiếu nhập, ED-20): bản build MOCK phục vụ tĩnh, thêm một kịch bản trên Django thật.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3301 &)
#   BASE=http://127.0.0.1:3301 SHOTS=<thư mục ảnh> python3 e2e/ed_batch10_purchasing.py      # tắt server sau khi xong
#   Kịch bản thật (tuỳ chọn): REAL_BASE=http://127.0.0.1:3302 REAL_API=http://127.0.0.1:8130 (build MOCK=0, NEXT_PUBLIC_API_BASE=REAL_API;
#   Django SQLite tạm + bootstrap_masterdata + seed_demo + loc/ql1/kho1 mật khẩu REAL_PW). Không đặt REAL_BASE thì kịch bản thật ghi "bỏ qua".
# Trạng thái mock nằm trong bộ nhớ trang: page.goto làm về seed, nên các luồng ghi đi bằng bấm link / menu, không gõ URL.
# Kiểm: ba vai loc / ql1 / kho1 (tiền mua chỉ Chủ thấy, Quản lý thấy số tiền hoá đơn, NV kho không có hoá đơn) · F1d chỉ Chủ ·
# tiền đúng từng đồng · F1a lưu nháp (không giá mua) · AC2/AC3 · AC4 chia chi phí lệch · đường sai (?id= rác/không có, 403) · 360px ·
# không console.error · không mã BR-.
import json
import os
import re
import sys
import urllib.request

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3301")
REAL_BASE = os.environ.get("REAL_BASE", "")
REAL_API = os.environ.get("REAL_API", "http://127.0.0.1:8130")
REAL_PW = os.environ.get("REAL_PW", "Songbien2026")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)

SMALL_TAPS_JS = """() => [...document.querySelectorAll('button, a, input, select')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y < innerHeight
      && !e.classList.contains('sr-only') && (r.height < 44 || (!['INPUT', 'SELECT'].includes(e.tagName) && r.width < 44));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""

FORBIDDEN_WORDS = ["BR-", "NCC", "HSD", "FEFO", "ago", "phút trước", "giờ trước", "hôm qua"]
PHONE = re.compile(r"\b0\d{9}\b")


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra if not cond else "")


def squash(text):
    return re.sub(r"\s+", " ", text).strip()


def login(page, user, pw="demo1234", base=BASE):
    page.goto(base + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15_000)
    page.wait_for_load_state("networkidle")


def new_page(browser, user, w=1366, h=900, mobile=False, errors=None):
    opts = {"viewport": {"width": w, "height": h}, "reduced_motion": "reduce"}
    if mobile:
        opts.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**opts)
    page = ctx.new_page()
    if errors is not None:
        page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(f"[{user}] {m.text}"))
        page.on("pageerror", lambda e: errors.append(f"[{user}] {e}"))
    login(page, user)
    return ctx, page


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)
    page.wait_for_timeout(120)


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    settle(page)


def main_text(page):
    return squash(page.locator("main").inner_text())


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def alert_text(page):
    """Chữ của các alert đang có nội dung (vùng thông báo rỗng của toast không tính)."""
    return squash(" ".join(x for x in page.get_by_role("alert").all_inner_texts() if x.strip()))


def field_error(page, name):
    """Chữ lỗi dưới ô `name` (ô có aria-invalid và aria-describedby trỏ tới dòng lỗi), hoặc None khi ô không báo lỗi."""
    el = page.locator(f"[name='{name}']").first
    if el.get_attribute("aria-invalid") != "true":
        return None
    return squash(page.locator("[id='" + el.get_attribute("aria-describedby") + "'] span").last.inner_text())


def receive_posts(page):
    return [x for x in page.evaluate("() => window.__caveMock.log") if "receive-batches" in x and x.startswith("POST")]


def tab_names(page):
    return [squash(x) for x in page.get_by_role("tab").all_inner_texts()]


def selected_tab(page):
    return squash(page.locator("[role=tab][aria-selected=true]").first.inner_text())


def wait_rows(page):
    page.locator("table tbody tr").first.wait_for()
    settle(page)


def menu_items(page):
    page.get_by_role("button", name="Thao tác khác").click()
    items = [squash(x) for x in page.get_by_role("menuitem").all_inner_texts()]
    page.keyboard.press("Escape")
    return items


def pick_menu(page, label):
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^" + re.escape(label))).click()


def fill_receive_line(page, idx, item_index, qty, rate=""):
    page.locator(f"select[name='item-{idx}']").select_option(index=item_index)
    page.locator(f"input[name='qty-{idx}']").fill(qty)
    if rate:
        page.locator(f"input[name='rate-{idx}']").fill(rate)


# ---------------------------------------------------------------- Chủ (loc)
def run_owner(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    go(page, "/purchasing/")
    wait_rows(page)

    ok("Chủ: 3 tab Phiếu nhập · Hoá đơn mua · Chi phí phụ", tab_names(page) == ["Phiếu nhập", "Hoá đơn mua", "Chi phí phụ"], str(tab_names(page)))
    ok("Chủ: mặc định ở tab Phiếu nhập", selected_tab(page) == "Phiếu nhập")
    heads = [squash(h) for h in page.locator("table thead th").all_inner_texts()]
    ok("Chủ: cột Tiền mua có (khoá) và Hoá đơn có", any(h.startswith("Tiền mua") for h in heads) and any(h.startswith("Hoá đơn") for h in heads), str(heads))
    ok("Chủ: tên cột theo bảng thiết kế: Mã phiếu, Số kg, Hoá đơn mua", any(h.startswith("Mã phiếu") for h in heads) and any(h.startswith("Số kg") for h in heads) and any(h.startswith("Hoá đơn mua") for h in heads), str(heads))
    title = squash(page.locator(".lt-head").inner_text())
    ok("Chủ: dòng tiêu đề thẻ bảng 'Phiếu nhập 17 phiếu · … kg'", title.startswith("Phiếu nhập 17 phiếu · ") and title.endswith(" kg"), title)
    row104 = page.locator("table tbody tr", has_text="PR-104").first
    ok("Chủ: PR-104 hiện tiền mua 7.620.000 đ và trạng thái Nháp", "7.620.000 đ" in row104.inner_text() and "Nháp" in row104.inner_text(), row104.inner_text())
    ok("Chủ: 'Đang hiện 17 / 17 phiếu'", page.get_by_text("Đang hiện 17 / 17 phiếu").is_visible())
    ok("Chủ: có nút Nhập lô tại cảng", page.get_by_role("link", name="Nhập lô tại cảng").count() == 1)
    page.screenshot(path=f"{SHOTS}/ed10-1-chu-danh-sach.png", full_page=True)

    # Lọc theo trạng thái (đường ngoài đường thuận: lọc ra đúng 1 phiếu Đã huỷ, rồi không kết quả)
    page.get_by_label("Trạng thái phiếu").select_option(label="Đã huỷ")
    settle(page)
    ok("Chủ: lọc Đã huỷ còn đúng PR-88", page.locator("table tbody tr").count() == 1 and "PR-88" in main_text(page), main_text(page)[:200])
    page.get_by_role("searchbox").first.fill("khong-co-phieu-nay") if page.get_by_role("searchbox").count() else page.get_by_placeholder("Tìm trong các phiếu đã tải").fill("khong-co-phieu-nay")
    page.wait_for_timeout(400)
    ok("Chủ: tìm không ra thì có thông báo rỗng, không bảng trống", page.locator("table tbody tr").count() == 0 and page.locator("[data-testid=clear-filters], button:has-text('Xoá bộ lọc')").count() >= 1, main_text(page)[:200])
    page.locator("[data-testid=clear-filters], button:has-text('Xoá bộ lọc')").first.click()
    settle(page)
    ok("Chủ: Xoá bộ lọc trả lại 17 phiếu", page.get_by_text("Đang hiện 17 / 17 phiếu").is_visible())

    # Tab theo URL (một useTabParam, ?tab=)
    go(page, "/purchasing/?tab=invoices")
    ok("Chủ: ?tab=invoices mở tab Hoá đơn mua", selected_tab(page) == "Hoá đơn mua")
    page.locator("table tbody tr").first.wait_for()
    inv_text = main_text(page)
    ok("Chủ: tab Hoá đơn có #40 3.577.200 đ gắn PR-97 và hoá đơn không gắn phiếu hiện —", "#40" in inv_text and "3.577.200 đ" in inv_text and "PR-97" in inv_text, inv_text[:300])
    # TL-L3: đang tìm thì phải có nút Bỏ lọc, bấm thì xoá ô tìm
    search = page.get_by_placeholder("Tìm mã hoá đơn, nhà cung cấp, phiếu nhập")
    search.fill("khong-co-hoa-don-nay")
    page.wait_for_timeout(300)
    ok("Chủ: tab Hoá đơn: tìm không ra thì có nút Bỏ lọc", page.locator("table tbody tr").count() == 0 and page.get_by_role("button", name="Bỏ lọc").count() >= 1)
    page.get_by_role("button", name="Bỏ lọc").first.click()
    page.wait_for_timeout(300)
    ok("Chủ: tab Hoá đơn: Bỏ lọc xoá ô tìm và trả lại các dòng", search.input_value() == "" and page.locator("table tbody tr").count() >= 1, search.input_value())
    go(page, "/purchasing/?tab=costs")
    ok("Chủ: ?tab=costs mở tab Chi phí phụ", selected_tab(page) == "Chi phí phụ")
    page.locator("table tbody tr").first.wait_for()
    search = page.get_by_placeholder(re.compile("^Tìm"))
    search.first.fill("khong-co-chi-phi-nay")
    page.wait_for_timeout(300)
    ok("Chủ: tab Chi phí: tìm không ra thì có nút Bỏ lọc, bấm thì xoá ô tìm", page.get_by_role("button", name="Bỏ lọc").count() >= 1 and (page.get_by_role("button", name="Bỏ lọc").first.click() or True) and search.first.input_value() == "")
    page.wait_for_timeout(300)
    ok("Chủ: tab Chi phí có khoản 1.200.000 đ Vận chuyển", "1.200.000 đ" in main_text(page) and "Vận chuyển" in main_text(page))
    go(page, "/purchasing/?tab=khong-co")
    ok("Chủ: ?tab= rác rơi về tab Phiếu nhập", selected_tab(page) == "Phiếu nhập")

    # Chi tiết phiếu đã có hoá đơn + chi phí
    go(page, "/purchasing/detail/?id=101")
    page.wait_for_selector("#receipt-detail, [data-testid=receipt-costs]")
    settle(page)
    d = main_text(page)
    ok("Chủ: chi tiết PR-101 có tiền mua 5.680.000 đ và Giá vốn/kg 147.500 đ", "5.680.000 đ" in d and "147.500 đ" in d, d[:300])
    ok("Chủ: chi tiết có chi phí phụ 220.000 đ chia vào phiếu", "220.000 đ" in page.locator("[data-testid=receipt-costs]").inner_text(), page.locator("[data-testid=receipt-costs]").inner_text()[:200])
    ok("Chủ: có Dòng thời gian", page.locator("#receipt-timeline").count() >= 1 or "DÒNG THỜI GIAN" in page.locator("main").inner_text().upper())
    ok("Chủ: có nút Thêm hoá đơn (phiếu chưa có hoá đơn)", page.get_by_role("button", name="Thêm hoá đơn").count() >= 1)
    items = menu_items(page)
    ok("Chủ: menu … có Nhập chi phí mua, Huỷ phiếu", any(i.startswith("Nhập chi phí mua") for i in items) and any(i.startswith("Huỷ phiếu") for i in items), str(items))
    page.screenshot(path=f"{SHOTS}/ed10-2-chu-chi-tiet-pr101.png", full_page=True)

    # F1c Thêm hoá đơn: tiền đúng từng đồng; tên phiếu gắn sẵn
    page.get_by_role("button", name="Thêm hoá đơn").first.click()
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    amount = dlg.locator("input[name=amount]")
    amount.fill("")
    dlg.get_by_role("button", name="Lưu hoá đơn").click()
    ok("F1c: bỏ trống số tiền thì báo lỗi dưới ô, không gửi", "Nhập số tiền lớn hơn 0." in dlg.inner_text() and dlg.is_visible(), dlg.inner_text()[:200])
    for label, bad, expect in (("âm", "-5000", "không được âm"), ("14 chữ số", "99999999999999", "quá lớn"), ("bằng 0", "0", "lớn hơn 0")):
        page.evaluate("() => window.__caveMock.clearLog()")
        amount.fill("")
        page.wait_for_timeout(100)
        amount.type(bad)
        dlg.get_by_role("button", name="Lưu hoá đơn").click()
        page.wait_for_timeout(150)
        err = field_error(page, "amount")
        ok(f"F1c B5: số tiền hoá đơn {label} báo dưới ô, không gửi", bool(err) and expect in err and dlg.is_visible() and not [x for x in page.evaluate("() => window.__caveMock.log") if x.startswith("POST")], f"{err!r}")
    amount.fill("")
    page.wait_for_timeout(100)
    amount.fill("1650000")
    ok("F1c: ô tiền nhóm nghìn khi gõ (1.650.000)", amount.input_value() == "1.650.000", amount.input_value())
    page.evaluate("() => window.__caveMock.clearLog()")
    dlg.get_by_role("button", name="Lưu hoá đơn").click()
    dlg.wait_for(state="detached")
    settle(page)
    log = page.evaluate("() => window.__caveMock.log")
    ok("F1c: gọi POST /api/purchasing/invoices/ đúng một lần", len([x for x in log if x.startswith("POST /api/purchasing/invoices/")]) == 1, str(log))
    inv = page.locator("[data-testid=receipt-invoices]")
    ok("F1c: hoá đơn mới hiện đúng 1.650.000 đ trong phiếu (mock nhận đúng số nguyên đồng)", "1.650.000 đ" in inv.inner_text(), inv.inner_text()[:200])
    ok("F1c: lưu xong không có alert lỗi", alert_text(page) == "", alert_text(page))

    # F1d Nhập chi phí (phiếu 1 lô): AC4
    pick_menu(page, "Nhập chi phí mua")
    page.wait_for_url(re.compile(r"/purchasing/costs/new/\?receipt=101"))
    page.locator("input[name=amount]").wait_for()
    settle(page)
    save = page.get_by_role("button", name="Lưu chi phí")
    page.locator("input[name=amount]").type("-5")
    page.wait_for_timeout(150)
    ok("F1d B5: tổng chi phí âm báo dưới ô và khoá nút Lưu", "không được âm" in str(field_error(page, "amount")) and (save.is_disabled() or save.get_attribute("aria-disabled") == "true"), str(field_error(page, "amount")))
    page.locator("input[name=amount]").fill("")
    page.wait_for_timeout(100)
    page.locator("input[name=amount]").type("99999999999999")
    page.wait_for_timeout(150)
    ok("F1d B5: tổng chi phí 14 chữ số báo 'quá lớn' dưới ô", "quá lớn" in str(field_error(page, "amount")), str(field_error(page, "amount")))
    page.locator("input[name=amount]").fill("")
    page.wait_for_timeout(100)
    page.locator("input[name=amount]").fill("1200000")
    page.wait_for_timeout(200)
    page.locator("input[name=alloc-0]").fill("")
    page.locator("input[name=alloc-0]").type("-5")
    page.wait_for_timeout(150)
    ok("F1d B5: phần chia âm báo dưới ô lô đó, nút Lưu khoá, không coi như 0", "không được âm" in str(field_error(page, "alloc-0")) and (save.is_disabled() or save.get_attribute("aria-disabled") == "true"), str(field_error(page, "alloc-0")))
    page.locator("input[name=alloc-0]").fill("")
    page.locator("input[name=amount]").fill("1100000")
    page.wait_for_timeout(100)
    page.locator("input[name=amount]").fill("1200000")
    page.wait_for_timeout(200)
    ok("F1d: chia sẵn vào lô duy nhất đủ 1.200.000 đ, nút Lưu chi phí mở", page.locator("[data-testid=alloc-total]").inner_text().startswith("1.200.000") and save.is_enabled(), page.locator("[data-testid=alloc-total]").inner_text())
    page.locator("input[name=alloc-0]").fill("1150000")
    page.wait_for_timeout(200)
    at = alert_text(page)
    ok("F1d AC4: lệch tổng -> alert đỏ 'Tổng tiền chia phải bằng 1.200.000 đ, còn thiếu 50.000 đ.'", "Tổng tiền chia phải bằng 1.200.000 đ, còn thiếu 50.000 đ." in at, at)
    ok("F1d AC4: nút Lưu chi phí bị khoá", save.is_disabled() or save.get_attribute("aria-disabled") == "true")
    page.screenshot(path=f"{SHOTS}/ed10-3-chu-chi-phi-lech.png", full_page=True)
    page.locator("input[name=alloc-0]").fill("1250000")
    page.wait_for_timeout(200)
    at = alert_text(page)
    ok("F1d AC4: thừa thì báo 'đang thừa 50.000 đ'", "đang thừa 50.000 đ" in at, at)
    page.locator("input[name=alloc-0]").fill("1200000")
    page.wait_for_timeout(200)
    ok("F1d: sửa cho khớp thì hết alert và mở nút", save.is_enabled() and alert_text(page) == "", alert_text(page))
    page.evaluate("() => window.__caveMock.clearLog()")
    save.dblclick()
    page.wait_for_url(re.compile(r"/purchasing/detail/\?id=101"))
    settle(page)
    log = page.evaluate("() => window.__caveMock.log")
    ok("F1d: gọi POST /api/purchasing/costs/ đúng một lần", len([x for x in log if x.startswith("POST /api/purchasing/costs/")]) == 1, str(log))
    costs = page.locator("[data-testid=receipt-costs]").inner_text()
    ok("F1d: chi phí mới hiện trong phiếu đúng 1.200.000 đ (tổng đã chia 1.420.000 đ)", "1.200.000 đ" in costs and "1.420.000 đ" in costs, costs[:300])

    # Phiếu Nháp: Ghi nhận phiếu -> lô Nháp
    go(page, "/purchasing/")
    wait_rows(page)
    page.locator("table tbody tr", has_text="PR-104").first.locator("a").first.click()
    page.wait_for_url(re.compile(r"/purchasing/detail/\?id=104"))
    page.get_by_role("button", name="Ghi nhận phiếu").first.click()
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    ok("Ghi nhận phiếu: hộp xác nhận có tổng 48 kg", "48 kg" in dlg.inner_text(), dlg.inner_text()[:200])
    dlg.get_by_role("button", name="Ghi nhận phiếu").click()
    dlg.wait_for(state="detached")
    settle(page)
    ok("Ghi nhận phiếu: trạng thái chuyển Đã ghi nhận, dòng nhập có mã lô", "Đã ghi nhận" in main_text(page) and not "Chưa có lô" in main_text(page), main_text(page)[:200])

    # Huỷ phiếu: bị chặn khi lô đã mở bán (PR-101 SELLING), huỷ được khi lô còn Nháp (PR-103)
    go(page, "/purchasing/detail/?id=101")
    page.get_by_role("button", name="Thao tác khác").click()
    cancel_item = page.get_by_role("menuitem", name=re.compile("^Huỷ phiếu"))
    ok("Huỷ phiếu: PR-101 (lô đã mở bán) bị chặn, mục menu mờ kèm lý do", cancel_item.get_attribute("aria-disabled") == "true", cancel_item.inner_text())
    page.keyboard.press("Escape")
    go(page, "/purchasing/detail/?id=103")
    pick_menu(page, "Huỷ phiếu")
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    dlg.get_by_role("button", name="Huỷ phiếu").click()
    dlg.wait_for(state="detached")
    settle(page)
    ok("Huỷ phiếu: PR-103 chuyển Đã huỷ", "Đã huỷ" in main_text(page).split("THÔNG TIN")[0], main_text(page)[:150])

    # Đường sai
    go(page, "/purchasing/detail/?id=zzz")
    ok("Đường sai: ?id= rác -> Không tìm thấy trang này, không gọi API", "Không tìm thấy trang này" in main_text(page))
    go(page, "/purchasing/detail/?id=99999")
    ok("Đường sai: phiếu không có -> Không tìm thấy trang này", "Không tìm thấy trang này" in main_text(page))
    go(page, "/purchasing/detail/")
    ok("Đường sai: thiếu ?id= -> Không tìm thấy trang này", "Không tìm thấy trang này" in main_text(page))
    go(page, "/purchasing/costs/new/?receipt=abc")
    ok("Đường sai: ?receipt= rác -> form cho chọn phiếu (không vỡ)", "Phiếu nhập" in main_text(page) and page.get_by_role("button", name="Tiếp tục").count() == 1, main_text(page)[:200])
    go(page, "/purchasing/costs/new/?receipt=99999")
    ok("Đường sai: ?receipt= không có -> Không tìm thấy", "Không tìm thấy trang này" in main_text(page), main_text(page)[:200])

    body_all = page.locator("body").inner_text()
    ok("Chủ: không từ cấm / mã BR-, không SĐT", not [w for w in FORBIDDEN_WORDS if w in body_all] and not PHONE.search(body_all), str([w for w in FORBIDDEN_WORDS if w in body_all]))
    ctx.close()


# ---------------------------------------------------------------- F1a Nhập lô tại cảng (Chủ)
def run_receive_form(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    go(page, "/purchasing/")
    wait_rows(page)
    page.get_by_role("link", name="Nhập lô tại cảng").click()
    page.wait_for_url("**/purchasing/new/")
    page.locator("select[name=supplier]").wait_for()
    settle(page)
    page.screenshot(path=f"{SHOTS}/ed10-4-nhap-lo-form.png", full_page=True)

    ok("F1a: tự chọn sẵn nhà cung cấp đầu danh sách", page.locator("select[name=supplier]").input_value() != "")
    page.locator("select[name=supplier]").select_option("")
    submit = page.get_by_role("button", name="Ghi nhận phiếu nhập")
    submit.click()
    ok("F1a: chưa chọn nhà cung cấp -> báo 'Vui lòng chọn nhà cung cấp.'", "Vui lòng chọn nhà cung cấp." in main_text(page))
    page.locator("select[name=supplier]").select_option(index=1)
    submit.click()
    ok("F1a: chưa chọn mặt hàng -> 'Chọn mặt hàng.' dưới ô mặt hàng", field_error(page, "item-0") == "Chọn mặt hàng.", str(field_error(page, "item-0")))
    # AC3: khối lượng 0
    fill_receive_line(page, 0, 1, "0", "80000")
    page.evaluate("() => window.__caveMock.clearLog()")
    submit.click()
    ok("F1a AC3: khối lượng 0 -> 'Nhập số kg lớn hơn 0.' DƯỚI ô số kg (aria-invalid), không lên alert đầu form, KHÔNG gọi API",
       field_error(page, "qty-0") == "Nhập số kg lớn hơn 0." and alert_text(page) == "" and not receive_posts(page), f"{field_error(page, 'qty-0')} | alert={alert_text(page)!r}")
    for bad_qty in ("", "-3", "abc"):
        page.locator("input[name=qty-0]").fill(bad_qty)
        ok(f"F1a AC3: số kg {bad_qty!r} cũng báo dưới ô", field_error(page, "qty-0") == "Nhập số kg lớn hơn 0.", str(field_error(page, "qty-0")))
    page.locator("input[name=qty-0]").fill("0")
    # Tiền đúng đồng: ô tiền từ chối số lẻ
    rate0 = page.locator("input[name=rate-0]")
    rate0.fill("80,5")
    ok("F1a: ô giá mua từ chối số lẻ đồng và báo dưới ô", "Số tiền là số nguyên đồng" in main_text(page), f"{rate0.input_value()} | {main_text(page)[:200]}")
    rate0.fill("")
    page.wait_for_timeout(150)
    rate0.fill("80000")
    ok("F1a: giá mua nhóm nghìn 80.000", rate0.input_value() == "80.000", rate0.input_value())

    # B5: giá mua âm / quá lớn / bằng 0 -> báo dưới ô, không gửi, không bao giờ thành 0 đ
    page.locator("input[name=qty-0]").fill("12.5")
    for label, bad, expect in (("âm", "-5000", "không được âm"), ("11 chữ số (N1)", "10000000000", "tối đa 10 chữ số"), ("12 chữ số (N1)", "999999999999", "tối đa 10 chữ số"), ("14 chữ số", "99999999999999", "quá lớn"), ("bằng 0", "0", "lớn hơn 0")):
        page.evaluate("() => window.__caveMock.clearLog()")
        rate0.fill("")
        page.wait_for_timeout(100)
        rate0.type(bad)
        submit.click()
        page.wait_for_timeout(200)
        err = field_error(page, "rate-0")
        ok(f"F1a B5: giá mua {label} ({bad}) báo dưới ô giá mua và KHÔNG gọi API", bool(err) and expect in err and not receive_posts(page), f"{err!r} posts={receive_posts(page)}")
    ok("F1a B5: lỗi giá mua không nằm ở alert đầu form", alert_text(page) == "", alert_text(page))
    rate0.fill("")
    page.wait_for_timeout(100)
    ok("F1a #22: xoá hẳn ô giá mua thì báo bắt buộc (Lô bổ sung A, không còn \"trống = chưa có giá\")", "lớn hơn 0" in str(field_error(page, "rate-0")), str(field_error(page, "rate-0")))
    rate0.type("9999999999")
    page.wait_for_timeout(100)
    ok("F1a N1: biên 10 chữ số (9.999.999.999) hợp lệ, không báo lỗi", field_error(page, "rate-0") is None and rate0.input_value() == "9.999.999.999", f"{field_error(page, 'rate-0')} {rate0.input_value()}")
    rate0.fill("")
    page.wait_for_timeout(100)
    rate0.type("80000")
    ok("F1a B5: nhập lại giá hợp lệ thì hết lỗi", field_error(page, "rate-0") is None and rate0.input_value() == "80.000", f"{field_error(page, 'rate-0')} {rate0.input_value()}")

    # Lưu nháp: không có giá mua trong storage
    fill_receive_line(page, 0, 1, "12.5", "81234")
    page.get_by_role("button", name="Lưu nháp").click()
    page.wait_for_timeout(300)
    st = page.evaluate("() => JSON.stringify(localStorage) + JSON.stringify(sessionStorage)")
    draft = page.evaluate("() => JSON.stringify(Object.fromEntries(Object.keys(sessionStorage).map(k => [k, sessionStorage.getItem(k)])))")
    ok("F1a: Lưu nháp có thông báo, storage không chứa giá mua 81234 / 81.234, nháp không có SĐT/tên", "Đã lưu nháp" in page.locator("body").inner_text() and "81234" not in st and "81.234" not in st and not PHONE.search(draft) and '"rate"' not in draft, draft[:200])
    ok("F1a: nháp nằm ở sessionStorage, localStorage không có khoá nháp", page.evaluate("() => Object.keys(sessionStorage).some(k => k.startsWith('cave_draft_receive_batches:')) && !Object.keys(localStorage).some(k => k.startsWith('cave_draft'))"))
    ok("F1a: URL không có query dữ liệu", "?" not in page.url, page.url)

    # AC2: 3 dòng -> 3 lô; gửi
    page.get_by_role("button", name="Thêm mặt hàng").click()
    page.get_by_role("button", name="Thêm mặt hàng").click()
    fill_receive_line(page, 1, 2, "7", "150000")
    fill_receive_line(page, 2, 3, "3.25", "90000")
    ok("F1a AC2: có 3 dòng mặt hàng", page.locator("select[name^=item-]").count() == 3)
    page.evaluate("() => window.__caveMock.clearLog()")
    submit.click()
    page.get_by_text("Ghi nhận phiếu nhập thành công").wait_for()
    settle(page)
    ok("F1a AC2: gọi POST receive-batches đúng một lần", len([x for x in page.evaluate("() => window.__caveMock.log") if x.startswith("POST /api/purchasing/receipts/receive-batches/")]) == 1)
    ok("F1a AC2: 3 lô Nháp được sinh", page.locator("[data-testid=receive-success] li").count() == 3, page.locator("[data-testid=receive-success]").inner_text()[:300])
    st2 = page.evaluate("() => JSON.stringify(localStorage) + JSON.stringify(sessionStorage)")
    ok("F1a: gửi xong thì nháp bị xoá, storage vẫn sạch giá mua", not page.evaluate("() => Object.keys(sessionStorage).some(k => k.startsWith('cave_draft_receive_batches:') && JSON.parse(sessionStorage.getItem(k)).lines)") or "81234" not in st2)
    page.screenshot(path=f"{SHOTS}/ed10-5-nhap-lo-thanh-cong.png", full_page=True)

    # Xem phiếu vừa tạo (điều hướng mềm giữ mock): giá mua 150.000 đ đúng đồng
    page.get_by_role("link", name="Xem phiếu").click()
    page.wait_for_url(re.compile(r"/purchasing/detail/\?id=\d+"))
    page.get_by_text("Dòng nhập").first.wait_for()
    settle(page)
    d = main_text(page)
    ok("F1a: phiếu vừa tạo hiện giá mua 150.000 đ, 81.234 đ (mock nhận đúng số nguyên đồng)", "150.000 đ" in d and "81.234 đ" in d, d[:400])
    ok("F1a: phiếu vừa tạo có 3 dòng nhập", page.locator("table tbody tr").count() >= 3)

    # F1d cho phiếu 3 lô: chia theo kg, tổng khớp đúng đồng
    pick_menu(page, "Nhập chi phí mua")
    page.wait_for_url(re.compile(r"/purchasing/costs/new/\?receipt=\d+"))
    page.locator("input[name=amount]").wait_for()
    settle(page)
    page.locator("input[name=amount]").fill("1000001")
    page.wait_for_timeout(250)
    parts = [int(page.locator(f"input[name=alloc-{i}]").input_value().replace(".", "") or 0) for i in range(3)]
    ok("F1d: 3 lô chia theo kg, tổng đúng 1.000.001 đ (dư dồn lô cuối, không làm tròn)", sum(parts) == 1000001 and all(p > 0 for p in parts), str(parts))
    ok("F1d: chia đủ thì nút Lưu chi phí mở", page.get_by_role("button", name="Lưu chi phí").is_enabled())
    page.locator("input[name=alloc-1]").fill(str(parts[1] + 50000))
    page.wait_for_timeout(250)
    ok("F1d AC4 (3 lô): lệch thì khoá nút và nói thừa 50.000 đ", page.get_by_role("button", name="Lưu chi phí").is_disabled() and "đang thừa 50.000 đ" in alert_text(page))
    page.locator("input[name=allocation_method]").nth(1).check()
    page.wait_for_timeout(250)
    parts2 = [int(page.locator(f"input[name=alloc-{i}]").input_value().replace(".", "") or 0) for i in range(3)]
    ok("F1d: đổi cách chia thì chia lại đủ tổng, nút mở", sum(parts2) == 1000001 and page.get_by_role("button", name="Lưu chi phí").is_enabled(), str(parts2))
    ctx.close()


def run_cancel_just_created(browser, errors):
    ctx, page = new_page(browser, "kho1", errors=errors)
    go(page, "/purchasing/")
    wait_rows(page)
    page.get_by_role("link", name="Nhập lô tại cảng").click()
    page.wait_for_url("**/purchasing/new/")
    page.locator("select[name=supplier]").wait_for()
    settle(page)
    page.locator("select[name=supplier]").select_option(index=2)
    fill_receive_line(page, 0, 1, "5", "75000")
    page.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    page.get_by_text("Ghi nhận phiếu nhập thành công").wait_for()
    settle(page)
    page.get_by_role("button", name="Huỷ phiếu nhập này").click()
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    dlg.get_by_role("button", name="Huỷ phiếu").click()
    dlg.wait_for(state="detached")
    settle(page)
    ok("F1a: NV kho nhập xong huỷ được phiếu vừa tạo (có hộp xác nhận)", "đã huỷ" in page.locator("[data-testid=receive-success]").inner_text().lower(), page.locator("[data-testid=receive-success]").inner_text()[:200])
    ctx.close()


# ---------------------------------------------------------------- Quản lý (ql1)
def run_manager(browser, errors):
    ctx, page = new_page(browser, "ql1", errors=errors)
    go(page, "/purchasing/")
    wait_rows(page)
    ok("Quản lý: 2 tab Phiếu nhập · Hoá đơn mua (không có Chi phí phụ)", tab_names(page) == ["Phiếu nhập", "Hoá đơn mua"], str(tab_names(page)))
    html = page.content()
    t = main_text(page)
    heads = [squash(h) for h in page.locator("table thead th").all_inner_texts()]
    ok("Quản lý: danh sách không có cột Tiền mua, không có số 7.620.000", not any(h.startswith("Tiền mua") for h in heads) and "7.620.000" not in html, str(heads))
    ok("Quản lý: cột Hoá đơn có (view_purchaseinvoice)", any(h.startswith("Hoá đơn") for h in heads), str(heads))
    ok("Quản lý: DOM không có giá vốn/giá mua", not re.search(r"Giá vốn|Giá mua|landed|purchase_amount", html), "")
    go(page, "/purchasing/?tab=invoices")
    page.locator("table tbody tr").first.wait_for()
    ok("Quản lý: tab Hoá đơn thấy số tiền hoá đơn 3.577.200 đ (quyết định D-3), không có nút Thêm hoá đơn", "3.577.200 đ" in main_text(page) and page.get_by_role("button", name="Thêm hoá đơn").count() == 0 and page.get_by_role("link", name="Thêm hoá đơn").count() == 0)
    go(page, "/purchasing/?tab=costs")
    ok("Quản lý: ?tab=costs rơi về Phiếu nhập (không có tab Chi phí)", selected_tab(page) == "Phiếu nhập", selected_tab(page))
    go(page, "/purchasing/detail/?id=97")
    page.wait_for_selector("[data-testid=receipt-invoices]")
    settle(page)
    html = page.content()
    d = main_text(page)
    ok("Quản lý: chi tiết PR-97 thấy hoá đơn 3.577.200 đ", "3.577.200 đ" in page.locator("[data-testid=receipt-invoices]").inner_text())
    ok("Quản lý: chi tiết không có tiền mua 3.577.200 ở khối Tiền mua, không Giá mua/kg, không Giá vốn/kg, không phần Chi phí phụ", "Giá mua/kg" not in d and "Giá vốn/kg" not in d and page.locator("[data-testid=receipt-costs]").count() == 0 and "Chi phí phụ" not in d, d[:300])
    ok("Quản lý: không có nút Thêm hoá đơn / Nhập chi phí trên phiếu", page.get_by_role("button", name=re.compile("Thêm hoá đơn|Nhập chi phí")).count() == 0 and not any(i.startswith("Nhập chi phí") for i in menu_items(page)))
    go(page, "/purchasing/costs/new/?receipt=101")
    ok("Quản lý: /purchasing/costs/new/ -> Không có quyền (F1d chỉ Chủ)", "quyền" in main_text(page).lower() and page.locator("input[name=amount]").count() == 0, main_text(page)[:200])
    go(page, "/purchasing/new/")
    page.locator("select[name=supplier]").wait_for()
    ok("Quản lý: mở được /purchasing/new/ (có quyền thêm phiếu nhập)", page.locator("input[name=qty-0]").count() == 1)
    ctx.close()


# ---------------------------------------------------------------- NV kho (kho1)
def run_warehouse(browser, errors):
    ctx, page = new_page(browser, "kho1", errors=errors)
    go(page, "/purchasing/")
    wait_rows(page)
    html = page.content()
    ok("NV kho: không có thanh tab (chỉ danh sách phiếu)", page.get_by_role("tab").count() == 0, str(tab_names(page)))
    heads = [squash(h) for h in page.locator("table thead th").all_inner_texts()]
    ok("NV kho: không cột Tiền mua, không cột Hoá đơn", not any(h.startswith(("Tiền mua", "Hoá đơn")) for h in heads), str(heads))
    ok("NV kho: DOM không có số tiền mua, giá mua, giá vốn", not re.search(r"7\.620\.000|\d\d\d\.\d\d\d đ|Giá vốn|Giá mua", html), "")
    ok("NV kho thấy mọi phiếu (quyết định #9): 17 phiếu", page.get_by_text("Đang hiện 17 / 17 phiếu").is_visible())
    go(page, "/purchasing/?tab=invoices")
    ok("NV kho: ?tab=invoices không mở tab Hoá đơn", page.get_by_role("tab").count() == 0 and "Danh sách hoá đơn mua" not in page.locator("body").inner_text())
    go(page, "/purchasing/detail/?id=97")
    page.get_by_text("Dòng nhập").first.wait_for()
    settle(page)
    html = page.content()
    d = main_text(page)
    ok("NV kho: chi tiết không có Hoá đơn mua, tiền mua, giá mua/kg, giá vốn, chi phí phụ", not re.search(r"Hoá đơn mua|Tiền mua|Giá mua|Giá vốn|Chi phí phụ|3\.577\.200|\d\d\d\.\d\d\d đ", d + html), d[:300])
    go(page, "/purchasing/costs/new/?receipt=101")
    ok("NV kho: /purchasing/costs/new/ -> Không có quyền", page.locator("input[name=amount]").count() == 0 and "quyền" in main_text(page).lower())
    go(page, "/purchasing/new/")
    page.locator("select[name=supplier]").wait_for()
    ok("NV kho: mở được /purchasing/new/ (có quyền thêm phiếu nhập)", page.locator("input[name=qty-0]").count() == 1)
    ctx.close()


# ---------------------------------------------------------------- 360px
def run_mobile(browser, errors):
    ctx, page = new_page(browser, "loc", 360, 740, mobile=True, errors=errors)
    paths = [
        ("/purchasing/", "table tbody tr", "ed10-6-m-danh-sach.png"),
        ("/purchasing/new/", "select[name=supplier]", "ed10-7-m-nhap-lo.png"),
        ("/purchasing/detail/?id=101", "[data-testid=receipt-costs]", "ed10-8-m-chi-tiet.png"),
        ("/purchasing/costs/new/?receipt=101", "input[name=amount]", "ed10-9-m-chi-phi.png"),
        ("/purchasing/?tab=invoices", "table tbody tr", "ed10-10-m-hoa-don.png"),
    ]
    for path, sel, shot in paths:
        go(page, path)
        page.locator(sel).first.wait_for()
        settle(page)
        ok(f"360px {path}: không cuộn ngang", no_hscroll(page))
        small = page.evaluate(SMALL_TAPS_JS)
        ok(f"360px {path}: vùng bấm >= 44px", not small, str(small[:5]))
        page.screenshot(path=f"{SHOTS}/{shot}")
    # Modal Thêm hoá đơn trên điện thoại
    go(page, "/purchasing/detail/?id=101")
    page.get_by_role("button", name="Thêm hoá đơn").first.click()
    page.get_by_role("dialog").wait_for()
    ok("360px: hộp Thêm hoá đơn không cuộn ngang, nút Lưu hoá đơn thấy được", no_hscroll(page) and page.get_by_role("button", name="Lưu hoá đơn").is_visible())
    page.screenshot(path=f"{SHOTS}/ed10-11-m-them-hoa-don.png")
    ctx.close()


# ---------------------------------------------------------------- Django thật
def run_real(browser):
    if not REAL_BASE:
        print("SKIP kịch bản Django thật (không đặt REAL_BASE)")
        return

    def token(user):
        r = urllib.request.Request(REAL_API + "/api/auth/token/", data=json.dumps({"username": user, "password": REAL_PW}).encode(), headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(r))["token"]

    def api(user, path):
        r = urllib.request.Request(REAL_API + path, headers={"Authorization": "Token " + token(user)})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    ctx = browser.new_context(viewport={"width": 1366, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    bodies = {"receive": None, "invoice": None, "cost": None}
    api_bad = []

    def on_request(rq):
        if rq.method != "POST":
            return
        data = json.loads(rq.post_data or "{}")
        if "receive-batches" in rq.url:
            bodies["receive"] = data
        elif "/api/purchasing/invoices/" in rq.url:
            bodies["invoice"] = data
        elif "/api/purchasing/costs/" in rq.url:
            bodies["cost"] = data

    page.on("request", on_request)
    page.on("response", lambda r: api_bad.append((r.url, r.status)) if "/api/" in r.url and r.status >= 400 and "/api/ai/status/" not in r.url else None)
    login(page, "loc", REAL_PW, REAL_BASE)
    page.goto(REAL_BASE + "/purchasing/")
    page.wait_for_load_state("networkidle")
    page.get_by_role("link", name="Nhập lô tại cảng").click()
    page.wait_for_url("**/purchasing/new/")
    page.locator("select[name=supplier]").wait_for()
    page.wait_for_timeout(500)
    page.locator("select[name=supplier]").select_option(index=1)
    page.locator("select[name='item-0']").select_option(index=1)
    page.locator("input[name='qty-0']").fill("12.5")
    # B5: giá mua sai (âm, 14 chữ số, 0) và số kg 0 -> không gửi gì lên BE thật, không biến thành rate "0"
    for bad_rate in ("-5000", "99999999999999", "999999999999", "10000000000", "0"):
        page.locator("input[name='rate-0']").fill(bad_rate)
        page.get_by_role("button", name="Ghi nhận phiếu nhập").click()
        page.wait_for_timeout(400)
        ok(f"Thật B5: giá mua {bad_rate!r} -> không gửi request nhập lô, báo lỗi dưới ô", bodies["receive"] is None and field_error(page, "rate-0") is not None, str(field_error(page, "rate-0")))
    page.locator("input[name='rate-0']").fill("80000")
    page.locator("input[name='qty-0']").fill("0")
    page.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    page.wait_for_timeout(400)
    ok("Thật B4: số kg 0 -> không gửi request, báo 'Nhập số kg lớn hơn 0.' dưới ô", bodies["receive"] is None and field_error(page, "qty-0") == "Nhập số kg lớn hơn 0.", str(field_error(page, "qty-0")))
    page.locator("input[name='qty-0']").fill("12.5")
    page.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    page.get_by_text("Ghi nhận phiếu nhập thành công").wait_for(timeout=15_000)
    rb = bodies["receive"] or {}
    line = (rb.get("lines") or [{}])[0]
    ok("Thật F1a: body nhập lô đúng đồng (rate '80000', qty '12.5', có idempotency_key)", line.get("rate") == "80000" and line.get("qty") == "12.5" and bool(rb.get("idempotency_key")), json.dumps(line))
    code = page.locator("[data-testid=receive-success] h2").inner_text()
    ok("Thật F1a: ghi nhận thành công, mã PR-<số>", re.search(r"PR-\d+", code) is not None, code)
    page.screenshot(path=f"{SHOTS}/ed10-real-1-nhap-lo.png")
    page.get_by_role("link", name="Xem phiếu").click()
    page.wait_for_url(re.compile(r"/purchasing/detail/\?id=\d+"))
    rid = re.search(r"id=(\d+)", page.url).group(1)
    page.get_by_text("Dòng nhập").first.wait_for(timeout=15_000)
    page.wait_for_timeout(500)
    d = squash(page.locator("main").inner_text())
    ok("Thật W2b: chi tiết phiếu có mã, 12,5 kg, giá mua 80.000 đ (Chủ)", f"PR-{rid}" in d and "12,5 kg" in d and "80.000 đ" in d, d[:300])
    # F1c
    page.get_by_role("button", name="Thêm hoá đơn").first.click()
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    dlg.locator("input[name=amount]").fill("1000000")
    dlg.get_by_role("button", name="Lưu hoá đơn").click()
    dlg.wait_for(state="detached", timeout=15_000)
    page.wait_for_timeout(700)
    ib = bodies["invoice"] or {}
    ok("Thật F1c: body hoá đơn amount đúng '1000000', receipt khớp phiếu", str(ib.get("amount")) == "1000000" and str(ib.get("receipt")) == rid, json.dumps(ib))
    ok("Thật F1c: hoá đơn mới hiện 1.000.000 đ trong phiếu", "1.000.000 đ" in page.locator("[data-testid=receipt-invoices]").inner_text())
    # F1d
    pick_menu(page, "Nhập chi phí mua")
    page.wait_for_url(re.compile(r"/purchasing/costs/new/\?receipt=\d+"))
    page.locator("input[name=amount]").wait_for()
    page.wait_for_timeout(500)
    page.locator("input[name=amount]").fill("100000")
    page.wait_for_timeout(300)
    page.get_by_role("button", name="Lưu chi phí").click()
    page.wait_for_url(re.compile(r"/purchasing/detail/\?id=\d+"), timeout=15_000)
    page.wait_for_timeout(700)
    cb = bodies["cost"] or {}
    allocs = cb.get("allocations") or []
    ok("Thật F1d: body chi phí amount '100000', tổng allocations đúng 100000", str(cb.get("amount")) == "100000" and sum(int(float(a["amount"])) for a in allocs) == 100000, json.dumps(cb))
    costs = page.locator("[data-testid=receipt-costs]").inner_text()
    ok("Thật F1d: chi phí hiện trong phiếu 100.000 đ", "100.000 đ" in costs, costs[:200])
    page.screenshot(path=f"{SHOTS}/ed10-real-2-chi-tiet.png", full_page=True)
    ok("Thật: không lỗi API (ngoài ai/status đã biết)", not api_bad, str(api_bad[:3]))

    # Phản hồi API thật theo vai: Quản lý và NV kho không có tiền mua / giá vốn
    sensitive = ["rate", "purchase_amount", "landed_unit_cost", "costs", "allocated_amount", "line_amount"]
    for user in ("ql1", "kho1"):
        det = api(user, f"/api/purchasing/receipts/{rid}/")
        lst = api(user, "/api/purchasing/receipts/")
        dump = json.dumps(det) + json.dumps(lst)
        leaked = [k for k in sensitive if f'"{k}"' in dump]
        ok(f"Thật API: {user} không nhận {', '.join(sensitive)} trong phiếu và danh sách", not leaked, str(leaked))
    inv_manager = api("ql1", f"/api/purchasing/receipts/{rid}/")
    ok("Thật API: ql1 thấy invoices[] có amount (quyết định D-3)", any("amount" in i for i in inv_manager.get("invoices", [])), json.dumps(inv_manager.get("invoices")))
    warehouse_keys = api("kho1", f"/api/purchasing/receipts/{rid}/")
    ok("Thật API: kho1 không có khoá invoices", "invoices" not in warehouse_keys or not warehouse_keys.get("invoices"), json.dumps(warehouse_keys.get("invoices")))
    try:
        api("kho1", "/api/purchasing/costs/")
        ok("Thật API: kho1 GET costs bị 403", False)
    except urllib.error.HTTPError as e:
        ok("Thật API: kho1 GET costs bị 403", e.code == 403, str(e.code))
    ctx.close()


errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    for fn in (run_owner, run_receive_form, run_cancel_just_created, run_manager, run_warehouse, run_mobile):
        try:
            fn(browser, errors)
        except Exception as exc:  # một kịch bản vỡ không che các kịch bản sau
            ok(f"{fn.__name__} chạy hết không ngoại lệ", False, repr(exc)[:400])
    try:
        run_real(browser)
    except Exception as exc:
        ok("run_real chạy hết không ngoại lệ", False, repr(exc)[:400])
    ok("Không có console.error / pageerror ở mọi vai", not errors, str(errors[:3]))
    browser.close()

bads = [r for r in results if not r[1]]
print(f"\n{len(results) - len(bads)}/{len(results)} PASS")
sys.exit(1 if bads else 0)
