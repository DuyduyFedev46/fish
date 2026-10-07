# P8 Lô 5 (FE) — SR-15 AC3/AC4/AC7, SR-16 AC8, SR-17 AC3: lô Quá hạn còn tồn + bỏ cột Khách ở Tổng quan.
# Cập nhật ERP theo design Lô 7: chi tiết lô là TRANG (/inventory/detail/?id=), hành động nằm ở menu 'Thao tác khác', nhãn 'nhà cung cấp' thay 'NCC'.
# Chạy trên bản build MOCK phục vụ tĩnh (dữ liệu bịa; 3 lô quá hạn L0908-CT00 sạch, L0909-MU00 đang giữ chỗ, L0910-TS00 sạch).
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out <thư-mục-out-riêng>
#   (cd <thư-mục-out-riêng> && python3 -m http.server 3215 --bind 127.0.0.1 &)
#   BASE=http://127.0.0.1:3215 SHOTS=<thư mục ảnh> python3 e2e/p8_lo5_fe_lo_qua_han.py     # tắt server sau khi xong
# Trạng thái mock nằm trong bộ nhớ trang: mỗi context mới bắt đầu từ seed.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3215")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []

OLD_CUSTOMERS = ["Chị Mai", "Nhà hàng Biển Xanh", "Anh Khoa", "Cô Thuý", "Quán Ốc Tám", "Chị Ngân", "Anh Bình", "Nhà hàng Hải Âu", "Khách lẻ"]


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


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)
    page.wait_for_timeout(150)


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def lots_table(page):
    t = page.locator("table.lt").first
    t.locator("tbody tr").first.wait_for()
    page.wait_for_function("() => document.querySelectorAll('table.lt tr.lt-skel').length === 0")
    return t


def open_lot(page, code):
    lots_table(page).locator("tbody tr", has_text=code).first.locator("a").first.click()
    page.locator("[data-testid=qty-available]").wait_for()
    settle(page)


def sheet_qty(page):
    return re.sub(r"\s+", " ", page.locator("[data-testid=qty-available]").inner_text()).strip()


def menu_items(page):
    page.get_by_role("button", name="Thao tác khác").click()
    return [re.sub(r"\s+", " ", x).strip() for x in page.get_by_role("menuitem").all_inner_texts()]


def pick_menu(page, label):
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^" + re.escape(label))).click()


def back_to_list(page):
    page.go_back()
    lots_table(page)
    settle(page)


def run_chu(browser, tag, viewport, errors):
    ctx = browser.new_context(viewport=viewport, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(f"[{tag}] {m.text}"))
    login(page, "loc")
    page.goto(BASE + "/overview/")
    page.wait_for_load_state("networkidle")
    settle(page)

    # ---- SR-17-AC3: bảng đơn không còn cột Khách, DOM không có tên khách mock ----
    orders = page.locator(".lt-card:has(h2:text-is('Đơn hàng gần đây'))")
    orders.locator("tbody tr").first.wait_for()
    heads = [h.strip() for h in orders.locator("thead th").all_inner_texts()]
    ok(f"[{tag}] SR-17-AC3 bảng đơn (nay 5 cột, ED-08): không có cột 'Khách' (cột: {heads})", "Khách" not in heads and heads == ["Mã đơn", "Giá trị", "Trạng thái", "Lý do", "Còn giữ chỗ"])
    body_text = page.locator("body").inner_text()
    html = page.content()
    leaked = [n for n in OLD_CUSTOMERS if n in body_text or n in html]
    ok(f"[{tag}] SR-17-AC3 DOM không có tên khách mock", not leaked, str(leaked))
    ok(f"[{tag}] SR-17-AC3 placeholder tìm kiếm không nhắc 'khách'", "khách" not in " ".join((e.get_attribute("placeholder") or "") + " " + (e.get_attribute("aria-label") or "") for e in page.locator("input, .search-trigger").all()).lower())

    # ---- SR-15-AC4: thẻ Cần chú ý ----
    card = page.locator("[data-attention=expired_batches_open]")
    card.wait_for(timeout=10_000)
    ok(f"[{tag}] SR-15-AC4 Chủ thấy thẻ '3 lô quá hạn còn tồn' (nhãn thẻ ED-08)", "3 lô quá hạn còn tồn" in card.inner_text(), card.inner_text().replace("\n", " | "))
    ok(f"[{tag}] SR-17 không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-1-tong-quan-chu-the-can-chu-y.png")

    card.get_by_role("link").click()
    page.wait_for_url("**/inventory/?status=EXPIRED")
    page.wait_for_load_state("networkidle")
    t = lots_table(page)
    settle(page)
    rows = t.locator("tbody tr")
    codes = [r.locator("td").first.inner_text().strip() for r in rows.all()]
    ok(f"[{tag}] SR-15-AC4 bấm thẻ → /inventory/?status=EXPIRED, danh sách chỉ 3 lô quá hạn ({codes})", len(codes) == 3 and set(codes) == {"L0908-CT00", "L0909-MU00", "L0910-TS00"})
    ok(f"[{tag}] mọi dòng đều 'Quá hạn'", all("Quá hạn" in r.inner_text() for r in rows.all()))
    ok(f"[{tag}] có nút 'Bỏ lọc'", page.get_by_test_id("clear-status-filter").count() == 1)
    ok(f"[{tag}] không cuộn ngang (danh sách)", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-2-danh-sach-loc-qua-han.png")

    # ---- SR-15-AC3: lô còn tồn có Trả nhà cung cấp + Huỷ phần tồn; Chốt bị khoá kèm lý do còn tồn ----
    open_lot(page, "L0908-CT00")
    items = menu_items(page)
    ok(f"[{tag}] SR-15-AC3 menu có 'Huỷ phần tồn, ghi lỗ' bật", "Huỷ phần tồn, ghi lỗ" in items, str(items))
    ok(f"[{tag}] SR-15-AC3 menu có 'Trả nhà cung cấp' bật", "Trả nhà cung cấp" in items, str(items))
    ok(f"[{tag}] SR-15-AC3 'Chốt lô' bị khoá kèm lý do còn tồn", any(i.startswith("Chốt lô · ") and "Lô còn 6,5 kg" in i for i in items), str(items))
    page.keyboard.press("Escape")
    ok(f"[{tag}] tồn hiển thị 6,5 kg", sheet_qty(page).startswith("6,5"), sheet_qty(page))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-3-chi-tiet-lo.png")

    # ---- SR-16-AC8: form Trả nhà cung cấp. 400 khi tồn phía máy chủ đã đổi (còn 2 kg, màn vẫn hiện 6,5) ----
    page.evaluate("() => window.__caveMock.expiredSetQty('L0908-CT00', 2)")
    pick_menu(page, "Trả nhà cung cấp")
    dlg = page.get_by_role("dialog", name="Trả nhà cung cấp")
    dlg.wait_for()
    qty = dlg.get_by_label("Số kg đã trả")
    ok(f"[{tag}] SR-16-AC8 ô kg có inputMode=decimal", qty.get_attribute("inputmode") == "decimal")
    ok(f"[{tag}] focus rơi vào ô số kg", page.evaluate("() => document.activeElement === document.querySelector('[role=dialog] input')"))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-4-form-tra-nha-cung-cap.png")

    # kiểm tra phía form: vượt tồn ĐANG HIỂN THỊ bị chặn ngay, không gọi API
    page.evaluate("() => window.__caveMock.clearLog()")
    qty.fill("9")
    dlg.get_by_role("button", name="Ghi nhận đã trả").click()
    ok(f"[{tag}] nhập 9 kg (> 6,5 đang hiển thị) bị chặn ngay ở form, không gọi API", dlg.get_by_text(re.compile("không vượt tồn 6,5 kg")).count() == 1 and not [l for l in page.evaluate("() => window.__caveMock.log") if "return-to-supplier" in l])
    # 5 kg hợp lệ theo màn nhưng máy chủ chỉ còn 2 kg → 400
    qty.fill("5")
    dlg.get_by_role("button", name="Ghi nhận đã trả").click()
    err = page.get_by_test_id("rts-error")
    err.wait_for(timeout=10_000)
    ok(f"[{tag}] SR-16-AC8 400 hiện đúng `detail` tiếng Việt", "không vượt tồn 2,000 kg" in err.inner_text(), err.inner_text().replace("\n", " | "))
    ok(f"[{tag}] form vẫn mở, nút gửi bật lại", dlg.get_by_role("button", name=re.compile("Ghi nhận đã trả|Thử lại")).is_enabled())
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-5-form-loi-400.png")
    err.get_by_role("button", name="Tải lại tồn").click()
    page.get_by_role("dialog", name="Trả nhà cung cấp").wait_for(state="detached")
    settle(page)
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('2')", timeout=10_000)
    ok(f"[{tag}] 'Tải lại tồn' → tồn hiển thị cập nhật 2 kg", sheet_qty(page).startswith("2"), sheet_qty(page))

    # bấm đúp "Ghi nhận" khi Trả hết: chỉ 1 request, gửi kèm tiền nhà cung cấp hoàn (không hiện lại sau khi lưu)
    pick_menu(page, "Trả nhà cung cấp")
    dlg = page.get_by_role("dialog", name="Trả nhà cung cấp")
    dlg.wait_for()
    dlg.get_by_role("button", name="Trả hết").click()
    ok(f"[{tag}] 'Trả hết' điền 2", dlg.get_by_label("Số kg đã trả").input_value() == "2")
    dlg.get_by_label("Tiền nhà cung cấp hoàn").fill("150000")
    dlg.get_by_label("Ghi chú").fill("Trả về ghe buổi sáng")
    page.evaluate("() => window.__caveMock.clearLog()")
    dlg.get_by_role("button", name="Ghi nhận đã trả").dblclick()
    page.get_by_text("Đã ghi nhận trả 2 kg cho nhà cung cấp.").wait_for(timeout=10_000)
    calls = [l for l in page.evaluate("() => window.__caveMock.log") if "return-to-supplier" in l]
    ok(f"[{tag}] SR-16-AC8 bấm đúp → đúng 1 request return-to-supplier ({len(calls)})", len(calls) == 1)
    settle(page)
    ok(f"[{tag}] tồn còn 0 kg", sheet_qty(page).startswith("0"), sheet_qty(page))
    all_text = page.locator("body").inner_text()
    ok(f"[{tag}] SR-16 không hiện lại tiền nhà cung cấp hoàn sau khi lưu", "150.000" not in all_text and "150000" not in all_text)
    items = menu_items(page)
    ok(f"[{tag}] SR-15-AC7 tồn = 0 → 'Chốt lô' mở, không còn lý do", "Chốt lô" in items, str(items))
    ok(f"[{tag}] Huỷ / Trả nhà cung cấp bị khoá 'Lô không còn tồn.'", "Huỷ phần tồn, ghi lỗ · Lô không còn tồn." in items and "Trả nhà cung cấp · Lô không còn tồn." in items, str(items))
    page.keyboard.press("Escape")
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-6-tra-het-chot-lo-mo.png")

    pick_menu(page, "Chốt lô")
    cd = page.get_by_role("dialog", name="Chốt lô")
    cd.wait_for()
    cd.get_by_role("button", name="Chốt lô").click()
    page.get_by_text(re.compile("Đã chốt lô L0908-CT00")).wait_for(timeout=10_000)
    settle(page)
    ok(f"[{tag}] chốt lô xong: trạng thái 'Đã chốt'", "Đã chốt" in page.locator("main").inner_text())
    back_to_list(page)

    # ---- Huỷ phần tồn: hộp xác nhận nêu kg, confirm_qty lệch → 400, tải lại, huỷ thành công ----
    open_lot(page, "L0910-TS00")
    page.evaluate("() => window.__caveMock.expiredSetQty('L0910-TS00', 5)")
    pick_menu(page, "Huỷ phần tồn, ghi lỗ")
    cdlg = page.get_by_role("dialog", name="Huỷ phần tồn, ghi lỗ")
    cdlg.wait_for()
    ok(f"[{tag}] SR-15-AC3 hộp huỷ nêu đúng số kg đang hiển thị (3 kg)", cdlg.get_by_test_id("cancel-qty").inner_text().startswith("3") and "Không hoàn tác được" in cdlg.inner_text(), cdlg.inner_text().replace("\n", " | "))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-7-hop-huy-phan-ton.png")
    page.evaluate("() => window.__caveMock.clearLog()")
    cdlg.get_by_role("button", name=re.compile("^Huỷ 3")).click()
    derr = page.get_by_test_id("dialog-error")
    derr.wait_for(timeout=10_000)
    ok(f"[{tag}] SR-15 confirm_qty lệch → 400 'Tồn đã đổi (5,000 kg) — tải lại.'", "Tồn đã đổi (5,000 kg) — tải lại." in derr.inner_text(), derr.inner_text())
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-8-huy-ton-da-doi-400.png")
    derr.get_by_role("button", name=re.compile("Tải lại")).click()
    page.get_by_role("dialog", name="Huỷ phần tồn, ghi lỗ").wait_for(state="detached")
    settle(page)
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('5')", timeout=10_000)
    pick_menu(page, "Huỷ phần tồn, ghi lỗ")
    cdlg = page.get_by_role("dialog", name="Huỷ phần tồn, ghi lỗ")
    cdlg.wait_for()
    ok(f"[{tag}] sau tải lại hộp huỷ nêu 5 kg", cdlg.get_by_test_id("cancel-qty").inner_text().startswith("5"))
    cdlg.get_by_role("button", name=re.compile("^Huỷ 5")).click()
    page.get_by_text(re.compile("Đã huỷ 5 kg của lô L0910-TS00")).wait_for(timeout=10_000)
    ok(f"[{tag}] huỷ thành công: lô 'Đã huỷ'", "Đã huỷ" in page.locator("main").inner_text())
    settle(page)
    back_to_list(page)

    # ---- Lô đang giữ chỗ: cả ba mục bị khoá kèm lý do (SR-08) ----
    open_lot(page, "L0909-MU00")
    items = menu_items(page)
    locked = [i for i in items if re.match(r"Trả|Huỷ|Chốt", i)]
    ok(f"[{tag}] lô giữ chỗ: Huỷ/Trả/Chốt đều bị khoá kèm lý do", len(locked) == 3 and all(" · " in i for i in locked), str(items))
    ok(f"[{tag}] lý do nêu giữ chỗ 1,5 kg", any("giữ chỗ" in i and "1,5" in i for i in locked), str(locked))
    page.keyboard.press("Escape")
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-9-lo-giu-cho-khoa.png")
    back_to_list(page)

    # ---- danh sách sau các thao tác: chỉ còn lô giữ chỗ ----
    left = [r.locator("td").first.inner_text().strip() for r in page.locator("table.lt").first.locator("tbody tr").all()]
    ok(f"[{tag}] danh sách sau thao tác chỉ còn L0909-MU00 ({left})", left == ["L0909-MU00"])
    page.goto(BASE + "/overview/")
    page.wait_for_load_state("networkidle")
    settle(page)
    ok(f"[{tag}] Tổng quan chưa tải lại trang thì thẻ vẫn khớp (trang mới = seed nên 3)", page.locator("[data-attention=expired_batches_open]").count() == 1)
    ctx.close()


def run_kho(browser, tag, viewport, errors):
    ctx = browser.new_context(viewport=viewport, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(f"[{tag}] {m.text}"))
    login(page, "kho1")
    page.goto(BASE + "/overview/")
    page.wait_for_load_state("networkidle")
    settle(page)
    ok(f"[{tag}] SR-15-AC4 warehouse_staff (kho1) không thấy thẻ Lô quá hạn", page.locator("[data-attention=expired_batches_open]").count() == 0)
    ok(f"[{tag}] SR-17 warehouse_staff: không có cột Khách", "Khách" not in [h.strip() for h in page.locator(".lt-card:has(h2:text-is('Đơn hàng gần đây')) thead th").all_inner_texts()])
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-10-tong-quan-nv-kho-khong-co-the.png")
    page.goto(BASE + "/inventory/?status=EXPIRED")
    page.wait_for_load_state("networkidle")
    lots_table(page)
    settle(page)
    open_lot(page, "L0908-CT00")
    items = menu_items(page)
    page.keyboard.press("Escape")
    ok(f"[{tag}] SR-15-AC3 warehouse_staff mở lô quá hạn: không có Huỷ / Trả nhà cung cấp / Chốt", not [i for i in items if re.match(r"Trả|Huỷ|Chốt", i)], str(items))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-11-nv-kho-chi-tiet-khong-nut.png")
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []
    for tag, vp in (("1366", {"width": 1366, "height": 800}), ("375", {"width": 375, "height": 812})):
        run_chu(browser, tag, vp, errors)
        run_kho(browser, tag, vp, errors)
    browser.close()

# lỗi console không được chứa dữ liệu cá nhân; 401/403 khi mock kiểm quyền là bình thường
pii = [e for e in errors if re.search(r"\b0\d{9}\b", e)]
ok("console không có SĐT", not pii, str(pii))
print("Console errors:", len(errors), errors[:5])
failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
