# E2E ERP theo design Lô 7 (Kho & lô, chi tiết lô, Sổ nhập xuất, Kho): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3301 &)
#   BASE=http://127.0.0.1:3301 SHOTS=<thư mục ảnh> python3 e2e/ed_batch7_inventory.py      # tắt server sau khi xong
# Trạng thái mock nằm trong bộ nhớ trang: page.goto làm về seed, nên các luồng ghi đi bằng bấm menu / bấm dòng, không gõ URL.
# Kiểm: ba vai loc / ql1 / kho1 (chỉ Chủ thấy giá vốn, chỉ Chủ có "Thêm kho") · không có nút "Điều chỉnh tồn" / "Ngừng bán lô" ·
# F1e mở bán (Quản lý) · F1g trả nhà cung cấp, F1h huỷ phần tồn, F1i chốt lô có lãi/lỗ (Chủ) · Sổ nhập xuất có "Tồn sau" ·
# đường sai (?id= rác, lô không có) · 360px (không cuộn ngang, vùng bấm >= 44px) · không console.error.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3301")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)

SMALL_TAPS_JS = """() => [...document.querySelectorAll('button, a, input, select')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y < innerHeight
      && !e.classList.contains('sr-only') && (r.height < 44 || (!['INPUT', 'SELECT'].includes(e.tagName) && r.width < 44));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""


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
        page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(f"[{user}] {m.text}"))
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
    page.wait_for_timeout(120)


def nav(page, label):
    """Bấm menu (điều hướng mềm, giữ trạng thái mock) trên desktop, hoặc thanh dưới / ngăn kéo trên điện thoại."""
    link = page.locator(".nav a", has_text=label).first
    if link.is_visible():
        link.click()
    else:
        page.goto(BASE + {"Kho & lô": "/inventory/", "Sổ nhập xuất": "/ledger/"}[label])


def lots_table(page):
    t = page.locator("table.lt").first
    expect(t.locator("tbody tr").first).to_be_visible()
    expect(t.locator("tr.lt-skel")).to_have_count(0)
    return t


def go_inventory(page):
    nav(page, "Kho & lô")
    page.wait_for_url("**/inventory/**")
    return lots_table(page)


def open_lot(page, code):
    t = page.locator("table.lt").first
    t.locator("tbody tr", has_text=code).first.locator("a").first.click()
    page.wait_for_selector("[data-testid=qty-available]")
    settle(page)


def menu_items(page):
    page.get_by_role("button", name="Thao tác khác").click()
    items = [re.sub(r"\s+", " ", x).strip() for x in page.get_by_role("menuitem").all_inner_texts()]
    return items


def close_menu(page):
    page.keyboard.press("Escape")


def pick_menu(page, label):
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^" + re.escape(label))).click()


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def qty_text(page):
    return re.sub(r"\s+", " ", page.locator("[data-testid=qty-available]").inner_text()).strip()


def body(page):
    return page.locator("body").inner_text()


FORBIDDEN_WORDS = ["Ngừng bán lô", "Tạo phiếu điều chỉnh", "Thêm điều chỉnh", "HSD", "NCC", "FEFO", "BR-"]
PHONE = re.compile(r"\b0\d{9}\b")


# ---------------------------------------------------------------- Chủ (loc)
def run_owner(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    t = go_inventory(page)

    # --- Danh sách lô
    tabs = page.get_by_role("tab").all_inner_texts()
    ok("Chủ: 3 tab Tồn theo lô · Điều chỉnh tồn · Kho", [x.strip() for x in tabs] == ["Tồn theo lô", "Điều chỉnh tồn", "Kho"], str(tabs))
    heads = [re.sub(r"\s+", " ", h).split(" lock")[0].split("lock")[0].strip() for h in t.locator("thead th").all_inner_texts()]
    ok("Chủ: cột Giá mua/kg và Giá vốn/kg có (khoá)", "Giá mua/kg" in heads and "Giá vốn/kg" in heads, str(heads))
    ok("Chủ: có biểu tượng khoá ở cột giá vốn", t.locator("thead th .mi, thead th svg, thead th [data-icon]").count() >= 1 or "lock" in " ".join(t.locator("thead th").all_inner_texts()))
    cost = t.locator("tbody tr td:nth-child(8)").all_inner_texts()
    ok("Chủ: ô Giá vốn/kg là tiền VNĐ", cost and all(re.search(r"\d\.?\d* đ$", c.strip()) for c in cost), str(cost[:3]))
    ok("Chủ: 'Đang hiện 16 / 16 lô'", page.get_by_text("Đang hiện 16 / 16 lô").is_visible())
    ok("Chủ: không có nút 'Điều chỉnh tồn' / 'Ngừng bán lô' / từ viết tắt", page.get_by_role("button", name=re.compile("Điều chỉnh tồn")).count() == 0 and not [w for w in FORBIDDEN_WORDS if w in body(page)], str([w for w in FORBIDDEN_WORDS if w in body(page)]))
    ok("Chủ: tab Điều chỉnh tồn là tab, không phải nút hành động", page.get_by_role("tab", name="Điều chỉnh tồn").count() == 1)
    page.screenshot(path=f"{SHOTS}/ed7-loc-1-ton-theo-lo.png")

    # Lọc trạng thái + tìm không dấu
    page.get_by_label("Trạng thái lô").select_option(label="Quá hạn")
    expect(t.locator("tbody tr")).to_have_count(3)
    expect(page.get_by_text("Đang hiện 3 / 3 lô")).to_be_visible()
    ok("Lọc Quá hạn → 3 lô, mọi dòng 'Quá hạn'", all("Quá hạn" in r for r in t.locator("tbody tr").all_inner_texts()))
    page.get_by_test_id("clear-status-filter").click()
    expect(t.locator("tbody tr")).to_have_count(16)
    page.get_by_role("searchbox").or_(page.get_by_placeholder("Tìm mã lô, mặt hàng, nhà cung cấp")).first.fill("muc ong")
    expect(t.locator("tbody tr")).to_have_count(1)
    ok("Tìm 'muc ong' (không dấu) → Mực ống", "Mực ống" in t.locator("tbody tr").first.inner_text())
    page.get_by_role("button", name="Xoá tìm kiếm").first.click()
    expect(t.locator("tbody tr")).to_have_count(16)

    # Nhập xuất gần đây
    panel = page.get_by_label("Nhập xuất gần đây")
    ok("Có khối 'Nhập xuất gần đây' (8 dòng) + link 'Xem sổ nhập xuất'", panel.locator("tbody tr").count() == 8 and panel.get_by_role("link", name="Xem sổ nhập xuất").count() == 1, str(panel.locator("tbody tr").count()))

    # --- Tab Điều chỉnh tồn (chỉ đọc)
    page.get_by_role("tab", name="Điều chỉnh tồn").click()
    expect(page.locator("table.lt").first.locator("tbody tr").first).to_be_visible()
    st = page.locator("table.lt").first
    sheads = [h.strip() for h in st.locator("thead th").all_inner_texts()]
    ok("Điều chỉnh tồn: cột Mã phiếu · Thời gian · Mục đích · Lô · Mặt hàng · Thay đổi (kg) · Lý do · Người làm", sheads == ["Mã phiếu", "Thời gian", "Mục đích", "Lô", "Mặt hàng", "Thay đổi (kg)", "Lý do", "Người làm"], str(sheads))
    mains = page.locator("main button:not([role=tab])").all_inner_texts()
    ok("Điều chỉnh tồn chỉ đọc: không có nút tạo / sửa", not [m for m in mains if re.search(r"Tạo|Thêm|Sửa|Điều chỉnh|Xoá", m)], str(mains))
    page.screenshot(path=f"{SHOTS}/ed7-loc-2-dieu-chinh-ton.png")

    # --- Tab Kho + Thêm kho (chỉ Chủ)
    page.get_by_role("tab", name="Kho", exact=True).click()
    wt = lots_table(page)
    add = page.get_by_role("button", name="Thêm kho")
    ok("Chủ thấy nút 'Thêm kho'", add.count() == 1)
    n0 = wt.locator("tbody tr").count()
    add.click()
    dlg = page.get_by_role("dialog", name="Thêm kho")
    dlg.get_by_role("button", name="Thêm kho").click()
    ok("Thêm kho: tên trống → báo lỗi dưới ô, không đóng hộp", dlg.is_visible() and dlg.get_by_text("Nhập tên kho.").count() == 1, dlg.inner_text()[:80])
    dlg.get_by_label("Tên kho").fill("Kho thử nghiệm")
    dlg.get_by_role("button", name="Thêm kho").click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã thêm kho Kho thử nghiệm.")).to_be_visible()
    expect(wt.locator("tbody tr")).to_have_count(n0 + 1)
    ok("Thêm kho: hàng mới hiện trong danh sách", "Kho thử nghiệm" in wt.inner_text())
    page.screenshot(path=f"{SHOTS}/ed7-loc-3-kho.png")

    # --- Sổ nhập xuất
    nav(page, "Sổ nhập xuất")
    page.wait_for_url("**/ledger/**")
    lt = lots_table(page)
    lheads = [h.strip() for h in lt.locator("thead th").all_inner_texts()]
    ok("Sổ nhập xuất: cột đúng ED-29", lheads == ["Thời gian", "Loại", "Lô", "Mặt hàng", "Thay đổi (kg)", "Tồn sau (kg)", "Chứng từ", "Người làm"], str(lheads))
    summ = page.locator(".fb-summary").inner_text()
    m = re.fullmatch(r"Đang hiện (\d+) / (\d+) dòng", summ.strip())
    ok("Sổ nhập xuất: 'Đang hiện x / y dòng'", bool(m) and int(m.group(1)) == 20 and int(m.group(2)) > 20, summ)
    first = [c.strip() for c in lt.locator("tbody tr").first.locator("td").all_inner_texts()]
    ok("Sổ nhập xuất: dòng đầu có thời gian dd/mm/yyyy hh:mm, 'Tồn sau' dạng kg", re.fullmatch(r"\d\d/\d\d/\d{4} \d\d:\d\d", first[0]) and re.search(r"kg$", first[5]), str(first))
    qty_changes = lt.locator("tbody tr td:nth-child(5)").all_inner_texts()
    ok("Sổ nhập xuất: 'Thay đổi' có dấu +/-", all(re.match(r"^[+-]", q.strip()) for q in qty_changes), str(qty_changes[:4]))
    ok("Sổ nhập xuất: chỉ đọc, không nút sửa/xoá/tạo", not [x for x in page.locator("main button").all_inner_texts() if re.search(r"Sửa|Xoá|Tạo|Thêm|Điều chỉnh", x)])
    ok("Sổ nhập xuất: không lộ giá vốn", "Giá vốn" not in body(page) and "Giá mua" not in body(page))
    page.get_by_role("button", name="Tải thêm").click()
    expect(page.locator(".fb-summary")).to_contain_text("Đang hiện 40 /")
    ok("Sổ nhập xuất: 'Tải thêm' nạp trang kế", True)
    page.get_by_label("Loại", exact=True).select_option(label="Bán ra")
    expect(page.locator(".fb-summary")).not_to_contain_text("Đang hiện 40 /")
    page.wait_for_function("() => document.querySelectorAll('table.lt tbody tr:not(.lt-skel)').length > 0")
    settle(page)
    types = [r.locator("td").nth(1).inner_text().strip() for r in lt.locator("tbody tr").all()]
    ok("Lọc Loại = Bán ra: mọi dòng 'Bán ra'", types and set(types) == {"Bán ra"}, str(set(types)))
    page.evaluate("() => window.__caveMock.clearLog()")
    page.get_by_label("Từ ngày").fill("2026-10-05")
    page.get_by_label("Đến ngày").fill("2026-10-01")
    settle(page)
    ok("Khoảng ngày ngược thứ tự: báo 'Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.'", page.get_by_text("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.").count() == 1)
    ok("Khoảng ngày ngược thứ tự: không gọi API với khoảng sai", not [l for l in page.evaluate("() => window.__caveMock.log") if "date_from=2026-10-05" in l and "date_to=2026-10-01" in l], str(page.evaluate("() => window.__caveMock.log")))
    page.screenshot(path=f"{SHOTS}/ed7-loc-4-so-nhap-xuat.png")

    ctx.close()


def run_owner_detail(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    go_inventory(page)
    open_lot(page, "L0908-CT00")
    txt = body(page)
    ok("Chi tiết lô: có Thông tin lô, Số lượng & giá vốn, Nhập xuất của lô, Đơn lấy hàng từ lô, Dòng thời gian",
       all(s.lower() in txt.lower() for s in ["Thông tin lô", "Số lượng & giá vốn", "Nhập xuất của lô", "Đơn lấy hàng từ lô", "Dòng thời gian"]))
    ok("Chi tiết lô Chủ: có Giá mua/kg, Chi phí phụ/kg, Giá vốn/kg (khoá)", all(s in txt for s in ["Giá mua/kg", "Chi phí phụ/kg", "Giá vốn/kg"]))
    ok("Chi tiết lô: tồn khả dụng 6,5 kg", qty_text(page).startswith("6,5"), qty_text(page))
    led = page.get_by_label("Nhập xuất của lô").first
    lheads = [h.strip() for h in page.locator("table.lt").first.locator("thead th").all_inner_texts()]
    ok("Nhập xuất của lô: có cột Tồn sau (kg), không cột Lô", "Tồn sau (kg)" in lheads and "Lô" not in lheads, str(lheads))
    last_balance = [c.strip() for c in page.locator("table.lt").first.locator("tbody tr").first.locator("td").all_inner_texts()]
    ok("Nhập xuất của lô: dòng mới nhất 'Tồn sau' = 6,5 kg (khớp tồn khả dụng)", "6,5 kg" in last_balance, str(last_balance))
    ok("Đơn lấy hàng từ lô: không có SĐT / tên khách", not PHONE.search(txt) and "Khách" not in [h.strip() for h in page.locator("table.lt").nth(1).locator("thead th").all_inner_texts()])
    ok("Chi tiết lô: không từ cấm, không mã BR", not [w for w in FORBIDDEN_WORDS if w in txt], str([w for w in FORBIDDEN_WORDS if w in txt]))
    ok("Chi tiết lô: URL chỉ có ?id= số", re.search(r"/inventory/detail/\?id=\d+$", page.url) is not None, page.url)
    items = menu_items(page)
    ok("Chủ, lô quá hạn: menu có Trả nhà cung cấp, Huỷ phần tồn ghi lỗ, Chốt lô (khoá, kèm lý do)", any(i.startswith("Trả nhà cung cấp") for i in items) and any(i.startswith("Huỷ phần tồn, ghi lỗ") for i in items) and any(i.startswith("Chốt lô") and "Lô còn 6,5 kg" in i for i in items), str(items))
    ok("Menu: không có 'Ngừng bán lô' / 'Điều chỉnh tồn'", not [i for i in items if re.search(r"Ngừng bán|Điều chỉnh", i)], str(items))
    close_menu(page)
    page.screenshot(path=f"{SHOTS}/ed7-loc-5-chi-tiet-lo.png")

    # --- F1g Trả nhà cung cấp: tồn phía máy chủ đã đổi -> báo, "Tải lại tồn"; rồi bấm đúp chỉ 1 request
    page.evaluate("() => window.__caveMock.expiredSetQty('L0908-CT00', 2)")
    pick_menu(page, "Trả nhà cung cấp")
    dlg = page.get_by_role("dialog", name="Trả nhà cung cấp")
    dlg.wait_for()
    qty = dlg.get_by_label("Số kg đã trả")
    ok("F1g: ô số kg inputMode=decimal, focus vào ô", qty.get_attribute("inputmode") == "decimal" and page.evaluate("() => document.activeElement && document.activeElement.tagName") == "INPUT")
    ok("F1g: tóm tắt Lô / Mặt hàng / Tồn còn (6,5 kg theo màn)", all(s in dlg.inner_text() for s in ["L0908-CT00", "Cá thu phi lê", "6,5 kg"]))
    page.evaluate("() => window.__caveMock.clearLog()")
    qty.fill("9")
    dlg.get_by_role("button", name="Ghi nhận đã trả").click()
    ok("F1g: 9 kg > 6,5 kg bị chặn ngay ở form, không gọi API", dlg.get_by_text(re.compile("không vượt tồn 6,5 kg")).count() == 1 and not [l for l in page.evaluate("() => window.__caveMock.log") if "return-to-supplier" in l])
    qty.fill("5")
    dlg.get_by_role("button", name="Ghi nhận đã trả").click()
    err = page.get_by_test_id("rts-error")
    err.wait_for()
    ok("F1g: máy chủ báo tồn đã đổi (400) hiện tiếng Việt, hộp vẫn mở", "2,000 kg" in err.inner_text() and dlg.is_visible(), err.inner_text())
    err.get_by_role("button", name="Tải lại tồn").click()
    dlg.wait_for(state="detached")
    settle(page)
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('2')")
    ok("F1g: 'Tải lại tồn' → tồn hiển thị 2 kg", qty_text(page).startswith("2"), qty_text(page))
    pick_menu(page, "Trả nhà cung cấp")
    dlg = page.get_by_role("dialog", name="Trả nhà cung cấp")
    dlg.wait_for()
    dlg.get_by_role("button", name="Trả hết").click()
    ok("F1g: 'Trả hết' điền 2", dlg.get_by_label("Số kg đã trả").input_value() == "2")
    dlg.get_by_label("Tiền nhà cung cấp hoàn").fill("150000")
    dlg.get_by_label("Ghi chú").fill("Trả về ghe buổi sáng")
    page.evaluate("() => window.__caveMock.clearLog()")
    dlg.get_by_role("button", name="Ghi nhận đã trả").dblclick()
    dlg.wait_for(state="detached")
    settle(page)
    calls = [l for l in page.evaluate("() => window.__caveMock.log") if "return-to-supplier" in l]
    ok(f"F1g: bấm đúp → đúng 1 request ({len(calls)})", len(calls) == 1)
    expect(page.get_by_text("Đã ghi nhận trả 2 kg cho nhà cung cấp.")).to_be_visible()
    ok("F1g: tồn về 0 kg, dòng sổ mới 'Trả nhà cung cấp'", qty_text(page).startswith("0") and "Trả nhà cung cấp" in page.locator("table.lt").first.inner_text())
    ok("F1g: không hiện lại tiền nhà cung cấp hoàn", "150.000" not in body(page))
    page.screenshot(path=f"{SHOTS}/ed7-loc-6-tra-nha-cung-cap.png")
    items = menu_items(page)
    ok("Hết tồn: Trả / Huỷ bị khoá 'Lô không còn tồn.', 'Chốt lô' mở được (không còn lý do)", any(i == "Trả nhà cung cấp · Lô không còn tồn." for i in items) and any(i == "Huỷ phần tồn, ghi lỗ · Lô không còn tồn." for i in items) and any(i == "Chốt lô" for i in items), str(items))
    close_menu(page)

    # --- F1i Chốt lô (Chủ có xem lãi/lỗ)
    pick_menu(page, "Chốt lô")
    cd = page.get_by_role("dialog", name="Chốt lô")
    cd.wait_for()
    cd.get_by_text("Lãi/lỗ lô").wait_for()
    ok("F1i Chủ: hộp chốt lô có dòng 'Lãi/lỗ lô' (khoá)", "Lãi/lỗ lô" in cd.inner_text() and "đ" in cd.inner_text(), cd.inner_text()[:200])
    ok("F1i: cảnh báo lô đã chốt không sửa được", "không nhập, xuất hay sửa" in cd.inner_text())
    page.screenshot(path=f"{SHOTS}/ed7-loc-7-chot-lo-lai-lo.png")
    cd.get_by_role("button", name="Chốt lô").click()
    cd.wait_for(state="detached")
    settle(page)
    expect(page.get_by_text(re.compile("Đã chốt lô L0908-CT00"))).to_be_visible()
    after = [i for i in menu_items(page) if re.match(r"Trả|Huỷ|Chốt", i)]
    ok("F1i: sau chốt mọi mục ghi đều bị khoá kèm lý do 'Lô đã chốt.'", after and all(i.endswith("· Lô đã chốt.") for i in after), str(after))
    close_menu(page)

    # --- F1h Huỷ phần tồn: confirm_qty lệch -> 400 -> tải lại -> huỷ được; có "Tiền ghi lỗ" cho Chủ
    go_inventory(page)
    open_lot(page, "L0910-TS00")
    page.evaluate("() => window.__caveMock.expiredSetQty('L0910-TS00', 5)")
    pick_menu(page, "Huỷ phần tồn, ghi lỗ")
    cdlg = page.get_by_role("dialog", name="Huỷ phần tồn, ghi lỗ")
    cdlg.wait_for()
    ok("F1h: hộp nêu 3 kg đang hiện, có 'Tiền ghi lỗ' (Chủ), cảnh báo không hoàn tác", cdlg.get_by_test_id("cancel-qty").inner_text().startswith("3") and "Tiền ghi lỗ" in cdlg.inner_text() and "Không hoàn tác được" in cdlg.inner_text(), cdlg.inner_text()[:200])
    page.screenshot(path=f"{SHOTS}/ed7-loc-8-huy-phan-ton.png")
    cdlg.get_by_role("button", name=re.compile("^Huỷ 3")).click()
    derr = page.get_by_test_id("dialog-error")
    derr.wait_for()
    ok("F1h: confirm_qty lệch → báo 'Tồn đã đổi (5,000 kg)'", "5,000 kg" in derr.inner_text(), derr.inner_text())
    derr.get_by_role("button", name=re.compile("Tải lại")).click()
    cdlg.wait_for(state="detached")
    settle(page)
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('5')")
    pick_menu(page, "Huỷ phần tồn, ghi lỗ")
    cdlg = page.get_by_role("dialog", name="Huỷ phần tồn, ghi lỗ")
    cdlg.wait_for()
    ok("F1h: sau tải lại hộp nêu 5 kg", cdlg.get_by_test_id("cancel-qty").inner_text().startswith("5"))
    cdlg.get_by_role("button", name=re.compile("^Huỷ 5")).click()
    cdlg.wait_for(state="detached")
    settle(page)
    expect(page.get_by_text(re.compile("Đã huỷ 5 kg của lô L0910-TS00"))).to_be_visible()
    ok("F1h: lô thành 'Đã huỷ'", "Đã huỷ" in page.locator("main").inner_text())

    # --- Lô đang giữ chỗ: Huỷ / Trả / Chốt bị khoá kèm lý do
    go_inventory(page)
    open_lot(page, "L0909-MU00")
    items = menu_items(page)
    ok("Lô giữ chỗ: mục bị khoá nêu lý do giữ chỗ 1,5 kg", any("giữ chỗ" in i and "1,5" in i for i in items), str(items))
    close_menu(page)
    ctx.close()


def run_owner_close_soldout(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    go_inventory(page)
    open_lot(page, "L0921-MU03")  # Hết hàng, tồn 0, chưa chốt
    items = menu_items(page)
    ok("Lô hết hàng nhưng chưa đủ điều kiện chốt: 'Chốt lô' bị khoá kèm lý do tiếng Việt, không lộ mã BR", any(i.startswith("Chốt lô · ") for i in items) and not any("BR-" in i for i in items), str(items))
    close_menu(page)
    ctx.close()


# ---------------------------------------------------------------- Hai tab: trạng thái lô đã đổi (QA B1)
def run_two_tabs(browser, errors):
    """Hai tab cùng mở một lô: tab kia đã đổi trạng thái (mock: expiredSetStatus). Tab này bấm thao tác -> BE trả lỗi sai
    trạng thái; hộp phải có 'Tải lại tồn', KHÔNG có 'Thử lại', nút chính bị khoá (gửi lại cũng lỗi y hệt), chỉ 1 request."""
    cases = [
        # (mã lô, trạng thái tab kia đặt, mục menu, tên hộp, nút chính, chữ lỗi, trạng thái hiện sau khi tải lại)
        ("L0908-CT00", "CANCELLED", "Huỷ phần tồn, ghi lỗ", "Huỷ phần tồn, ghi lỗ", re.compile(r"^Huỷ \d"), "Chỉ huỷ được lô Quá hạn.", "Đã huỷ", "BR-LO-03 Huỷ"),
        ("L0910-TS00", "CLOSED", "Trả nhà cung cấp", "Trả nhà cung cấp", re.compile("^Ghi nhận đã trả"), "Lô đã chốt.", "Đã chốt", "BR-LO-05 Trả NCC"),
        ("L0922-TS02", "SELLING", "Mở bán lô", "Mở bán lô", re.compile("^Mở bán lô"), "Chỉ mở bán lô đang ở trạng thái Nháp.", "Đang bán", "BR-MH-05 Mở bán"),
    ]
    for code, other_tab_status, menu_label, dlg_name, primary, msg, after_status, tag in cases:
        ctx, page = new_page(browser, "loc", errors=errors)
        go_inventory(page)
        open_lot(page, code)
        page.evaluate("([c, st]) => window.__caveMock.expiredSetStatus(c, st)", [code, other_tab_status])  # tab kia đã làm xong
        page.evaluate("() => window.__caveMock.clearLog()")
        if menu_label == "Mở bán lô":  # lô Nháp: Mở bán là nút chính, không nằm trong menu "Thao tác khác"
            page.get_by_role("button", name="Mở bán lô").click()
        else:
            pick_menu(page, menu_label)
        dlg = page.get_by_role("dialog", name=dlg_name)
        dlg.wait_for()
        if menu_label == "Trả nhà cung cấp":
            dlg.get_by_label("Số kg đã trả").fill("1")
        dlg.get_by_role("button", name=primary).click()
        e = dlg.locator("[data-testid=dialog-error], [data-testid=rts-error]").first
        e.wait_for()
        ok(f"Hai tab {tag}: hộp báo đúng lý do tiếng Việt, không mã BR", msg in e.inner_text() and "BR-" not in e.inner_text(), e.inner_text())
        ok(f"Hai tab {tag}: có 'Tải lại tồn'", e.get_by_role("button", name="Tải lại tồn").count() == 1)
        ok(f"Hai tab {tag}: không có 'Thử lại', nút chính khoá (gửi lại cũng lỗi y hệt)",
           dlg.get_by_role("button", name="Thử lại").count() == 0 and dlg.get_by_role("button", name=primary).is_disabled())
        posts = [l for l in page.evaluate("() => window.__caveMock.log") if l.startswith("POST")]
        ok(f"Hai tab {tag}: chỉ 1 request ghi", len(posts) == 1, str(posts))
        page.screenshot(path=f"{SHOTS}/ed7-hai-tab-{code}.png")
        e.get_by_role("button", name="Tải lại tồn").click()
        dlg.wait_for(state="detached")
        settle(page)
        page.wait_for_function("(t) => document.body.innerText.includes(t)", arg=after_status)
        ok(f"Hai tab {tag}: sau 'Tải lại tồn' màn hiện trạng thái thật '{after_status}'", after_status in body(page))
        ctx.close()


# ---------------------------------------------------------------- Quản lý (ql1)
def run_manager(browser, errors):
    ctx, page = new_page(browser, "ql1", errors=errors)
    t = go_inventory(page)
    heads = [h.strip() for h in t.locator("thead th").all_inner_texts()]
    ok("Quản lý: danh sách lô KHÔNG có cột giá mua / giá vốn", not [h for h in heads if "Giá" in h], str(heads))
    ok("Quản lý: DOM không có số tiền VNĐ trong bảng lô", not re.search(r"\d\s?đ", t.inner_text()))
    ok("Quản lý: có tab Điều chỉnh tồn và Kho", page.get_by_role("tab", name="Điều chỉnh tồn").count() == 1 and page.get_by_role("tab", name="Kho", exact=True).count() == 1)
    page.get_by_role("tab", name="Kho", exact=True).click()
    expect(page.locator("table.lt").first.locator("tbody tr").first).to_be_visible()
    ok("Quản lý: KHÔNG có nút 'Thêm kho' (chỉ Chủ)", page.get_by_role("button", name="Thêm kho").count() == 0)
    page.get_by_role("tab", name="Tồn theo lô").click()
    lots_table(page)

    # Chi tiết lô quá hạn: không giá vốn, không Trả/Huỷ/Chốt
    open_lot(page, "L0908-CT00")
    txt = body(page)
    ok("Quản lý: chi tiết lô không có giá mua / chi phí phụ / giá vốn", not any(s in txt for s in ["Giá mua", "Chi phí phụ", "Giá vốn", "Lãi/lỗ"]), "")
    items = menu_items(page)
    ok("Quản lý: menu chỉ có Sao chép mã lô, Xem nhật ký (không Trả/Huỷ/Chốt)", not [i for i in items if re.match(r"Trả|Huỷ|Chốt", i)] and any(i.startswith("Sao chép") for i in items), str(items))
    close_menu(page)
    ok("Quản lý: không có nút Mở bán lô trên lô đã bán", page.get_by_role("button", name="Mở bán lô").count() == 0)

    # F1e Mở bán lô Nháp (Quản lý có inventory.publish_batch)
    go_inventory(page)
    open_lot(page, "L0922-TS02")
    pub = page.get_by_role("button", name="Mở bán lô")
    ok("Quản lý: lô Nháp có nút chính 'Mở bán lô'", pub.count() == 1)
    pub.click()
    dlg = page.get_by_role("dialog", name="Mở bán lô")
    dlg.wait_for()
    ok("F1e: hộp Mở bán lô nêu Lô / Mặt hàng / Số kg / Hạn dùng, không 'Giá bán'", all(s in dlg.inner_text() for s in ["L0922-TS02", "Tôm sú size 30", "Số kg", "Hạn dùng"]) and "Giá bán" not in dlg.inner_text() and "Giá vốn" not in dlg.inner_text(), dlg.inner_text()[:200])
    page.screenshot(path=f"{SHOTS}/ed7-ql1-1-mo-ban-lo.png")
    page.evaluate("() => window.__caveMock.clearLog()")
    dlg.get_by_role("button", name="Mở bán lô").dblclick()
    dlg.wait_for(state="detached")
    settle(page)
    calls = [l for l in page.evaluate("() => window.__caveMock.log") if "publish" in l]
    ok(f"F1e: bấm đúp → đúng 1 request ({len(calls)})", len(calls) == 1, str(calls))
    expect(page.get_by_text(re.compile("Đã mở bán lô L0922-TS02"))).to_be_visible()
    ok("F1e: nút 'Mở bán lô' biến mất sau khi mở bán", page.get_by_role("button", name="Mở bán lô").count() == 0)

    # Sổ nhập xuất: Quản lý xem được, không giá vốn
    nav(page, "Sổ nhập xuất")
    page.wait_for_url("**/ledger/**")
    lots_table(page)
    ok("Quản lý: Sổ nhập xuất xem được, không giá vốn", "Giá vốn" not in body(page) and page.locator(".fb-summary").count() == 1)
    ctx.close()


# ---------------------------------------------------------------- Nhân viên kho (kho1)
def run_warehouse(browser, errors):
    ctx, page = new_page(browser, "kho1", errors=errors)
    t = go_inventory(page)
    heads = [h.strip() for h in t.locator("thead th").all_inner_texts()]
    ok("NV kho: không cột giá mua / giá vốn", not [h for h in heads if "Giá" in h], str(heads))
    page.get_by_role("tab", name="Kho", exact=True).click()
    expect(page.locator("table.lt").first.locator("tbody tr").first).to_be_visible()
    ok("NV kho: không có nút 'Thêm kho'", page.get_by_role("button", name="Thêm kho").count() == 0)
    page.get_by_role("tab", name="Tồn theo lô").click()
    lots_table(page)
    open_lot(page, "L0908-CT00")
    txt = body(page)
    ok("NV kho: chi tiết lô không giá vốn, không Lãi/lỗ", not any(s in txt for s in ["Giá mua", "Chi phí phụ", "Giá vốn", "Lãi/lỗ"]))
    items = menu_items(page)
    ok("NV kho: menu không có Trả / Huỷ / Chốt", not [i for i in items if re.match(r"Trả|Huỷ|Chốt", i)], str(items))
    close_menu(page)
    ok("NV kho: không nút Mở bán lô", page.get_by_role("button", name="Mở bán lô").count() == 0)
    ctx.close()


# ---------------------------------------------------------------- Khối Trợ lý AI
def run_ai(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    for mode in ("off", "on"):
        page.evaluate("(m) => { window.__caveMock.ai(m); window.__caveMock.aiConsent(true); window.__caveMock.clearLog(); }", mode)
        go_inventory(page)
        open_lot(page, "L0908-CT00")
        page.wait_for_timeout(600)
        summarize = page.get_by_role("button", name="Tóm tắt lịch sử chứng từ này")
        calls = [l for l in page.evaluate("() => window.__caveMock.log") if "/api/ai/" in l]
        if mode == "off":
            ok("AI tắt: chi tiết lô không có khối Trợ lý, không gọi /api/ai/actions", summarize.count() == 0 and not [c for c in calls if "/api/ai/actions" in c], str(calls))
        else:
            ok("AI bật: khối Trợ lý hiện, hỏi đúng target inventory.batch theo mã lô VÀ pk (TL7-M1)", summarize.count() == 1 and any("target_model=inventory.batch&target_id=" in c and "L0908-CT00" in c and "901" in c for c in calls), str(calls))
            ok("AI bật: yêu cầu AI không mang tên/SĐT/địa chỉ", not [c for c in calls if PHONE.search(c)])
            page.screenshot(path=f"{SHOTS}/ed7-loc-9-chi-tiet-lo-ai-bat.png")
    ctx.close()


# ---------------------------------------------------------------- Đường sai
def run_off_path(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    for q in ["?id=abc", "?id=", "", "?id=-1", "?id=1.5", "?id=99999", "?id=1%3Bdrop"]:
        page.evaluate("() => window.__caveMock.clearLog()")
        page.goto(BASE + "/inventory/detail/" + q)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        found = "Không tìm thấy" in body(page)
        ok(f"Đường sai /inventory/detail/{q}: hiện 'Không tìm thấy', có lối về Kho & lô", found and page.get_by_role("link", name="Về Kho & lô").count() == 1, body(page)[:80])
        if q in ("?id=abc", "?id=", "", "?id=-1", "?id=1.5", "?id=1%3Bdrop"):
            lg = page.evaluate("() => window.__caveMock.log")
            ok(f"Đường sai {q or '(trống)'}: không gọi API lô", not [l for l in lg if "/api/inventory/batches/" in l], str(lg))
    page.goto(BASE + "/ledger/?batch=abc")
    page.wait_for_load_state("networkidle")
    lots_table(page)
    ok("/ledger/?batch=abc: bỏ giá trị rác, vẫn tải bình thường", page.get_by_label("Lô", exact=True).input_value() == "")
    page.goto(BASE + "/inventory/?status=HACK")
    page.wait_for_load_state("networkidle")
    lots_table(page)
    ok("/inventory/?status=HACK: bỏ giá trị rác, hiện đủ lô", page.locator("table.lt").first.locator("tbody tr").count() == 16)
    ctx.close()


# ---------------------------------------------------------------- 360px
def run_mobile(browser, errors):
    ctx, page = new_page(browser, "loc", w=360, h=740, mobile=True, errors=errors)
    page.goto(BASE + "/inventory/")
    page.wait_for_load_state("networkidle")
    lots_table(page)
    page.evaluate("() => document.fonts.ready")
    ok("360 /inventory/ không cuộn ngang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360 /inventory/ vùng bấm >= 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/ed7-360-1-ton-theo-lo.png")

    page.locator("table.lt").first.locator("tbody tr", has_text="L0908-CT00").first.locator("a").first.click()
    page.wait_for_selector("[data-testid=qty-available]")
    settle(page)
    ok("360 chi tiết lô không cuộn ngang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360 chi tiết lô vùng bấm >= 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/ed7-360-2-chi-tiet-lo.png")
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^Trả nhà cung cấp")).click()
    dlg = page.get_by_role("dialog", name="Trả nhà cung cấp")
    dlg.wait_for()
    ok("360 hộp Trả nhà cung cấp không cuộn ngang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360 hộp Trả nhà cung cấp vùng bấm >= 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/ed7-360-3-hop-tra-nha-cung-cap.png")
    page.keyboard.press("Escape")

    page.goto(BASE + "/ledger/")
    page.wait_for_load_state("networkidle")
    lots_table(page)
    ok("360 /ledger/ không cuộn ngang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360 /ledger/ vùng bấm >= 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/ed7-360-4-so-nhap-xuat.png")
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []
    for fn in (run_owner, run_owner_detail, run_owner_close_soldout, run_two_tabs, run_manager, run_warehouse, run_ai, run_off_path, run_mobile):
        try:
            fn(browser, errors)
        except Exception as e:  # một kịch bản hỏng không che các kịch bản sau
            ok(f"{fn.__name__} chạy hết không lỗi", False, repr(e)[:400])
    browser.close()

relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "Failed to load resource" not in e]
ok("Không lỗi console / pageerror", not relevant, str(relevant[:5]))
ok("Console không chứa SĐT", not [e for e in errors if PHONE.search(e)])
failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
