# P8 Lô 5 (FE) — SR-15 AC3/AC4/AC7, SR-16 AC8, SR-17 AC3: lô Quá hạn còn tồn + bỏ cột Khách ở Tổng quan.
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


def open_lot(page, code):
    page.locator("tbody tr", has_text=code).first.locator("button").first.click()
    page.get_by_role("dialog", name=re.compile(f"Chi tiết lô {code}")).wait_for(timeout=10_000)
    page.locator("[data-testid=qty-available]").wait_for()
    settle(page)


def sheet_qty(page):
    return re.sub(r"\s+", " ", page.locator("[data-testid=qty-available]").inner_text()).strip()


def run_chu(browser, tag, viewport, errors):
    ctx = browser.new_context(viewport=viewport, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(f"[{tag}] {m.text}"))
    login(page, "loc")
    page.goto(BASE + "/overview/")
    page.wait_for_load_state("networkidle")
    settle(page)

    # ---- SR-17-AC3: bảng đơn không còn cột Khách, DOM không có tên khách mock ----
    orders = page.locator("section[aria-labelledby=ov-orders]")
    orders.locator("tbody tr").first.wait_for()
    heads = [h.strip() for h in orders.locator("thead th").all_inner_texts()]
    ok(f"[{tag}] SR-17-AC3 bảng đơn: không có cột 'Khách' (cột: {heads})", "Khách" not in heads and len(heads) == 3)
    body_text = page.locator("body").inner_text()
    html = page.content()
    leaked = [n for n in OLD_CUSTOMERS if n in body_text or n in html]
    ok(f"[{tag}] SR-17-AC3 DOM không có tên khách mock", not leaked, str(leaked))
    ok(f"[{tag}] SR-17-AC3 placeholder tìm kiếm không nhắc 'khách'", "khách" not in (page.locator("input[type=search]").first.get_attribute("placeholder") or "").lower())

    # ---- SR-15-AC4: thẻ Cần chú ý ----
    card = page.locator("[data-attention=expired_batches_open]")
    card.wait_for(timeout=10_000)
    ok(f"[{tag}] SR-15-AC4 Chủ thấy thẻ 'Lô quá hạn còn tồn: 3'", "Lô quá hạn còn tồn: 3" in card.inner_text(), card.inner_text().replace("\n", " | "))
    ok(f"[{tag}] SR-17 không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-1-tong-quan-chu-the-can-chu-y.png")

    card.get_by_role("link").click()
    page.wait_for_url("**/inventory/?status=EXPIRED")
    page.wait_for_load_state("networkidle")
    page.locator("tbody tr").first.wait_for()
    settle(page)
    rows = page.locator("tbody tr")
    codes = [r.locator("td").first.inner_text().strip() for r in rows.all()]
    ok(f"[{tag}] SR-15-AC4 bấm thẻ → /inventory/?status=EXPIRED, danh sách chỉ 3 lô quá hạn ({codes})", len(codes) == 3 and set(codes) == {"L0908-CT00", "L0909-MU00", "L0910-TS00"})
    chips = page.locator("tbody tr .chip, tbody tr [class*=chip]").all_inner_texts()
    ok(f"[{tag}] mọi dòng đều 'Quá hạn'", all("Quá hạn" in r.inner_text() for r in rows.all()))
    ok(f"[{tag}] có nút 'Bỏ lọc, xem tất cả lô'", page.get_by_test_id("clear-status-filter").count() == 1)
    ok(f"[{tag}] không cuộn ngang (danh sách)", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-2-danh-sach-loc-qua-han.png")

    # ---- SR-15-AC3: lô còn tồn có 2 nút + Chốt bị khoá kèm lý do ----
    open_lot(page, "L0908-CT00")
    acts = page.get_by_test_id("batch-actions")
    acts.wait_for()
    b_cancel = acts.locator("[data-action=cancel_expired]")
    b_return = acts.locator("[data-action=return_to_supplier]")
    b_close = acts.locator("[data-action=close]")
    ok(f"[{tag}] SR-15-AC3 nút 'Xác nhận Đã huỷ phần tồn' bật", b_cancel.count() == 1 and b_cancel.is_enabled() and "Xác nhận Đã huỷ phần tồn" in b_cancel.inner_text())
    ok(f"[{tag}] SR-15-AC3 nút 'Xác nhận Đã trả NCC' bật", b_return.count() == 1 and b_return.is_enabled() and "Xác nhận Đã trả NCC" in b_return.inner_text())
    lock = page.locator("[data-lock=close]")
    ok(f"[{tag}] SR-15-AC3 'Chốt lô' bị khoá kèm lý do tồn = 0", b_close.count() == 1 and b_close.is_disabled() and "tồn = 0" in lock.inner_text(), lock.inner_text())
    heights = [round(b.bounding_box()["height"]) for b in (b_cancel, b_return, b_close)]
    ok(f"[{tag}] nút cao >= 44px trên điện thoại ({heights})", viewport["width"] > 500 or all(h >= 44 for h in heights))
    ok(f"[{tag}] tồn hiển thị 6,5 kg", sheet_qty(page).startswith("6,5"), sheet_qty(page))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-3-chi-tiet-lo-hai-nut-chot-khoa.png")

    # ---- SR-16-AC8: form Đã trả NCC. 400 khi tồn phía máy chủ đã đổi (còn 2 kg, màn vẫn hiện 6,5) ----
    page.evaluate("() => window.__caveMock.expiredSetQty('L0908-CT00', 2)")
    b_return.click()
    dlg = page.get_by_role("dialog", name="Xác nhận Đã trả NCC")
    dlg.wait_for()
    qty = dlg.get_by_label("Số kg đã trả")
    ok(f"[{tag}] SR-16-AC8 ô kg có inputMode=decimal", qty.get_attribute("inputmode") == "decimal")
    ok(f"[{tag}] focus rơi vào ô số kg", page.evaluate("() => document.activeElement && document.activeElement.id") == "rts-qty")
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-4-form-da-tra-ncc.png")

    # kiểm tra phía form: vượt tồn ĐANG HIỂN THỊ bị chặn ngay, không gọi API
    page.evaluate("() => window.__caveMock.clearLog()")
    qty.fill("9")
    dlg.get_by_role("button", name="Ghi nhận đã trả").click()
    ok(f"[{tag}] nhập 9 kg (> 6,5 đang hiển thị) bị chặn ngay ở form, không gọi API", dlg.locator("#rts-qty-err").count() == 1 and not [l for l in page.evaluate("() => window.__caveMock.log") if "return-to-supplier" in l])
    # 5 kg hợp lệ theo màn nhưng máy chủ chỉ còn 2 kg → 400
    qty.fill("5")
    dlg.get_by_role("button", name="Ghi nhận đã trả").click()
    err = page.get_by_test_id("rts-error")
    err.wait_for(timeout=10_000)
    ok(f"[{tag}] SR-16-AC8 400 hiện đúng `detail` tiếng Việt", "không vượt tồn 2,000 kg" in err.inner_text(), err.inner_text().replace("\n", " | "))
    ok(f"[{tag}] form vẫn mở, nút gửi bật lại", dlg.get_by_role("button", name="Ghi nhận đã trả").is_enabled())
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-5-form-loi-400.png")
    err.get_by_role("button", name="Tải lại tồn").click()
    page.get_by_role("dialog", name="Xác nhận Đã trả NCC").wait_for(state="detached")
    settle(page)
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('2')", timeout=10_000)
    ok(f"[{tag}] 'Tải lại tồn' → tồn hiển thị cập nhật 2 kg", sheet_qty(page).startswith("2"), sheet_qty(page))

    # bấm đúp "Ghi nhận" khi Trả hết: chỉ 1 request, gửi kèm tiền NCC hoàn (không hiện lại sau khi lưu)
    b_return.click()
    dlg = page.get_by_role("dialog", name="Xác nhận Đã trả NCC")
    dlg.wait_for()
    dlg.get_by_role("button", name="Trả hết").click()
    ok(f"[{tag}] 'Trả hết' điền 2", dlg.get_by_label("Số kg đã trả").input_value() == "2")
    dlg.get_by_label("Tiền NCC hoàn").fill("150000")
    dlg.get_by_label("Ghi chú").fill("Trả về ghe buổi sáng")
    page.evaluate("() => window.__caveMock.clearLog()")
    dlg.get_by_role("button", name="Ghi nhận đã trả").dblclick()
    page.get_by_test_id("batch-notice").wait_for(timeout=10_000)
    calls = [l for l in page.evaluate("() => window.__caveMock.log") if "return-to-supplier" in l]
    ok(f"[{tag}] SR-16-AC8 bấm đúp → đúng 1 request return-to-supplier ({len(calls)})", len(calls) == 1)
    settle(page)
    notice = page.get_by_test_id("batch-notice").inner_text()
    ok(f"[{tag}] thông báo 'Đã ghi nhận trả NCC 2 kg', tồn còn 0 kg", "Đã ghi nhận trả NCC 2 kg" in notice and "0 kg" in notice, notice)
    all_text = page.locator("body").inner_text()
    ok(f"[{tag}] SR-16 không hiện lại tiền NCC hoàn sau khi lưu", "150.000" not in all_text and "150000" not in all_text)
    b_close = page.locator("[data-action=close]")
    ok(f"[{tag}] SR-15-AC7 tồn = 0 → nút 'Chốt lô' mở", b_close.is_enabled() and page.locator("[data-lock=close]").count() == 0)
    ok(f"[{tag}] nút Huỷ / Trả NCC biến mất khi hết tồn", page.locator("[data-action=cancel_expired]").count() == 0 and page.locator("[data-action=return_to_supplier]").count() == 0)
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-6-tra-het-chot-lo-mo.png")

    b_close.click()
    cd = page.get_by_role("dialog", name="Chốt lô")
    cd.wait_for()
    cd.get_by_role("button", name="Chốt lô").click()
    page.wait_for_function("() => document.querySelector('[data-testid=batch-notice]')?.innerText.includes('Đã chốt lô')", timeout=10_000)
    settle(page)
    ok(f"[{tag}] chốt lô xong: trạng thái 'Đã chốt'", "Đã chốt" in page.get_by_role("dialog", name=re.compile("Chi tiết lô")).inner_text())
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    page.wait_for_load_state("networkidle")

    # ---- Đã huỷ phần tồn: hộp xác nhận nêu kg, confirm_qty lệch → 400, tải lại, huỷ thành công ----
    open_lot(page, "L0910-TS00")
    page.evaluate("() => window.__caveMock.expiredSetQty('L0910-TS00', 5)")
    page.locator("[data-action=cancel_expired]").click()
    cdlg = page.get_by_role("dialog", name="Xác nhận Đã huỷ phần tồn")
    cdlg.wait_for()
    ok(f"[{tag}] SR-15-AC3 hộp huỷ nêu đúng số kg đang hiển thị (3 kg) và không nêu tiền", cdlg.get_by_test_id("cancel-qty").inner_text().startswith("3") and "₫" not in cdlg.inner_text(), cdlg.inner_text().replace("\n", " | "))
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-7-hop-huy-phan-ton.png")
    page.evaluate("() => window.__caveMock.clearLog()")
    cdlg.get_by_role("button", name=re.compile("Xác nhận huỷ")).click()
    derr = page.get_by_test_id("dialog-error")
    derr.wait_for(timeout=10_000)
    ok(f"[{tag}] SR-15 confirm_qty lệch → 400 'Tồn đã đổi (5,000 kg) — tải lại.'", "Tồn đã đổi (5,000 kg) — tải lại." in derr.inner_text(), derr.inner_text())
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-8-huy-ton-da-doi-400.png")
    derr.get_by_role("button", name="Tải lại").click()
    page.get_by_role("dialog", name="Xác nhận Đã huỷ phần tồn").wait_for(state="detached")
    settle(page)
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('5')", timeout=10_000)
    page.locator("[data-action=cancel_expired]").click()
    cdlg = page.get_by_role("dialog", name="Xác nhận Đã huỷ phần tồn")
    cdlg.wait_for()
    ok(f"[{tag}] sau tải lại hộp huỷ nêu 5 kg", cdlg.get_by_test_id("cancel-qty").inner_text().startswith("5"))
    cdlg.get_by_role("button", name=re.compile("Xác nhận huỷ")).click()
    page.wait_for_function("() => document.querySelector('[data-testid=batch-notice]')?.innerText.includes('Đã huỷ phần tồn')", timeout=10_000)
    ok(f"[{tag}] huỷ thành công: lô 'Đã huỷ'", "Đã huỷ" in page.get_by_role("dialog", name=re.compile("Chi tiết lô")).inner_text())
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    settle(page)

    # ---- Lô đang giữ chỗ: cả hai nút bị khoá kèm lý do (SR-08) ----
    open_lot(page, "L0909-MU00")
    ok(f"[{tag}] lô giữ chỗ: Huỷ/Trả NCC/Chốt đều bị khoá", all(page.locator(f"[data-action={k}]").is_disabled() for k in ("cancel_expired", "return_to_supplier", "close")))
    reason = page.locator("[data-lock=cancel_expired]").inner_text()
    ok(f"[{tag}] lý do nêu giữ chỗ 1,5 kg", "giữ chỗ" in reason and "1,5" in reason, reason)
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-9-lo-giu-cho-khoa.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- danh sách sau các thao tác: chỉ còn lô giữ chỗ ----
    settle(page)
    left = [r.locator("td").first.inner_text().strip() for r in page.locator("tbody tr").all()]
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
    ok(f"[{tag}] SR-15-AC4 nv_kho (kho1) không thấy thẻ Lô quá hạn", page.locator("[data-attention=expired_batches_open]").count() == 0)
    ok(f"[{tag}] SR-17 nv_kho: không có cột Khách", "Khách" not in [h.strip() for h in page.locator("section[aria-labelledby=ov-orders] thead th").all_inner_texts()])
    page.screenshot(path=f"{SHOTS}/lo5-{tag}-10-tong-quan-nv-kho-khong-co-the.png")
    page.goto(BASE + "/inventory/?status=EXPIRED")
    page.wait_for_load_state("networkidle")
    page.locator("tbody tr").first.wait_for()
    settle(page)
    open_lot(page, "L0908-CT00")
    page.wait_for_timeout(300)
    ok(f"[{tag}] SR-15-AC3 nv_kho mở lô quá hạn: không có nút Huỷ / Trả NCC / Chốt", page.get_by_test_id("batch-actions").count() == 0 and page.locator("[data-action]").count() == 0)
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
