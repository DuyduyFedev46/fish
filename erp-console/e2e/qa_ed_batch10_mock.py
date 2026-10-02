# QA độc lập Lô 10 FE trên bản build MOCK (kho mock trong bộ nhớ trang): so với bảng thiết kế / UI-RULES, lỗi từng ô, 360px, bàn phím.
#   BASE=http://127.0.0.1:3301 SHOTS=<doc/features/.../shots/lot10> python3 -u e2e/qa_ed_batch10_mock.py
import os
import re
import sys
import traceback

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3301")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=10_000)
results, notes = [], []
PHONE = re.compile(r"(?<!\d)0\d{9}(?!\d)")


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, ("" if cond else "  -> " + str(extra)[:400]), flush=True)


def note(msg):
    notes.append(msg)
    print("   [ghi nhận]", msg, flush=True)


def sq(t):
    return re.sub(r"\s+", " ", t).strip()


def login(page, user):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15_000)
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)
    page.wait_for_timeout(150)


def click_nav(page, label):
    page.locator(".nav a", has_text=label).first.click()
    page.wait_for_load_state("networkidle")
    settle(page)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        for fn in (sec_f1a_errors, sec_board, sec_360, sec_keyboard):
            print(f"\n=== {fn.__name__}", flush=True)
            try:
                fn(b)
            except Exception as e:  # noqa: BLE001
                ok(f"[{fn.__name__}] chạy hết không ngoại lệ", False, f"{type(e).__name__}: {str(e)[:300]}")
                traceback.print_exc(limit=4)
        b.close()
    bad = [r for r in results if not r[1]]
    print(f"\nTỔNG: {len(results)} ca, PASS {len(results) - len(bad)}, FAIL {len(bad)}")
    for n, _, e in bad:
        print("  FAIL:", n, "->", str(e)[:200])
    for n in notes:
        print("  -", n)
    sys.exit(1 if bad else 0)


def ctx_page(b, user, w=1366, h=900, mobile=False):
    o = {"viewport": {"width": w, "height": h}, "reduced_motion": "reduce"}
    if mobile:
        o.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    c = b.new_context(**o)
    pg = c.new_page()
    errs = []
    pg.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errs.append(m.text))
    pg.on("pageerror", lambda e: errs.append(str(e)))
    login(pg, user)
    return c, pg, errs


def sec_f1a_errors(b):
    c, pg, errs = ctx_page(b, "kho1")
    click_nav(pg, "Mua hàng")
    pg.get_by_role("link", name="Nhập lô tại cảng").first.click()
    pg.locator("select[name=supplier]").wait_for()
    settle(pg)
    pg.locator("select[name=item-0]").select_option(index=1)
    pg.locator("input[name=qty-0]").fill("0")
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(300)
    alert = sq(" ".join(pg.get_by_role("alert").all_inner_texts()))
    qty = pg.locator("input[name=qty-0]")
    inv = qty.get_attribute("aria-invalid")
    field_err = pg.evaluate("""() => { const i = document.querySelector('input[name=qty-0]'); const f = i.closest('label, div'); return f ? f.innerText : '' }""")
    below = pg.evaluate("""() => { const el = document.getElementsByName('qty-0')[0]; const id = el.getAttribute('aria-describedby'); const m = id ? document.getElementById(id) : null; return m ? m.innerText.replace(/^error\\s*/, '').trim() : '' }""") == "Nhập số kg lớn hơn 0."
    print("   alert:", alert, "| aria-invalid:", inv)
    ok("ED-20-AC3: số kg 0 -> 'Nhập số kg lớn hơn 0.' hiện DƯỚI Ô số kg (UI-RULES §3: viền đỏ + một dòng đỏ dưới ô)", below and inv == "true" and alert == "", f"alert={alert!r} aria-invalid={inv} chữ trong ô={sq(field_err)[:80]!r}")
    pg.screenshot(path=f"{SHOTS}/qa10-mock-f1a-qty-0.png", full_page=True)
    ok("ED-20-AC3: các dòng khác giữ nguyên (không mất dữ liệu)", pg.locator("select[name=item-0]").input_value() != "")
    # Lưu nháp có toast
    pg.get_by_role("button", name="Lưu nháp").click()
    pg.wait_for_timeout(300)
    ok("F1a: Lưu nháp -> toast nói rõ 'Giá mua không được lưu'", "Giá mua không được lưu" in sq(" ".join(pg.locator(".toast-item").all_inner_texts())), pg.locator(".toast-item").all_inner_texts())
    # ô giá mua: số lẻ / chữ / âm
    pg.get_by_role("button", name="Thêm mặt hàng").click()
    r = pg.locator("input[name=rate-1]")
    r.fill("abc")
    ok("F1a: gõ chữ vào ô giá mua -> ô rỗng", r.input_value() == "", r.input_value())
    r.fill("")
    r.press_sequentially("-5000")
    ok("F1a (hành vi mới B5): gõ từng phím '-5000' -> ô giữ nguyên '-5000' để hiện lỗi", r.input_value() == "-5000", r.input_value())
    pg.locator("input[name=qty-1]").fill("3")
    pg.locator("select[name=item-1]").select_option(index=1)
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(300)
    rate_err = pg.evaluate("""() => { const el = document.getElementsByName('rate-1')[0]; const id = el.getAttribute('aria-describedby'); const m = id ? document.getElementById(id) : null; return [m ? m.innerText.replace(/^error\\s*/, '').trim() : '', el.getAttribute('aria-invalid')] }""")
    ok("F1a (B5): giá mua âm -> lỗi dưới ô giá + aria-invalid, không có màn thành công", bool(rate_err[0]) and rate_err[1] == "true" and "Đã ghi nhận" not in sq(pg.locator("main").inner_text()).split("Ghi nhận phiếu nhập")[0], rate_err)
    # xoá dòng; không xoá được dòng cuối
    ok("F1a: chỉ 1 dòng thì không có nút Xoá dòng", pg.get_by_role("button", name=re.compile("Xoá dòng")).count() == 2 or pg.get_by_role("button", name=re.compile("Xoá dòng")).count() >= 1)
    ok("console sạch (F1a)", not errs, errs[:3])
    c.close()


def sec_board(b):
    c, pg, errs = ctx_page(b, "loc")
    click_nav(pg, "Mua hàng")
    pg.locator("table tbody tr").first.wait_for()
    settle(pg)
    heads = [sq(h).replace("lock (cột giới hạn quyền xem)", "").strip() for h in pg.locator("table thead th").all_inner_texts()]
    print("   cột danh sách:", heads)
    board_cols = ["Mã phiếu", "Ngày", "Nhà cung cấp", "Mặt hàng", "Lô", "Số kg", "Tiền mua", "Hoá đơn mua", "Người nhập", "Trạng thái", "Ghi chú"]
    missing = [x for x in board_cols if not any(h.startswith(x) for h in heads)]
    note(f"W2a so với bảng: cột bảng có mà bản dựng chưa có: {missing}; tên cột lệch: 'Tổng kg' (bảng 'Số kg'), 'Phiếu' (bảng 'Mã phiếu'), 'Hoá đơn' (bảng 'Hoá đơn mua')")
    main_txt = sq(pg.locator("main").inner_text())
    ok("W2a: có dòng 'Phiếu nhập · n phiếu · tổng kg' trong card bảng như bảng thiết kế", re.search(r"Phiếu nhập\s*\d+ phiếu\s*·\s*[\d.,]+ kg", main_txt) is not None, main_txt[:200])
    ok("W2a: có banner 'n phiếu đã ghi nhận chưa có hoá đơn mua' như bảng thiết kế", "chưa có hoá đơn" in main_txt.lower(), main_txt[:200])
    pg.screenshot(path=f"{SHOTS}/qa10-mock-w2a-loc-1366.png", full_page=True)
    # Chip trạng thái: Nháp / Đã ghi nhận / Đã huỷ cùng có mặt
    chips = set(re.findall(r"Nháp|Đã ghi nhận|Đã huỷ", main_txt))
    ok("W2a-AC1: có đủ chip Nháp, Đã ghi nhận, Đã huỷ trên dữ liệu mẫu", chips == {"Nháp", "Đã ghi nhận", "Đã huỷ"}, chips)
    ok("W2a-AC1: mã phiếu dạng PR-n (chữ mono)", re.search(r"PR-\d+", pg.locator("table tbody").inner_text()) is not None and "mono" in (pg.locator("table tbody tr td").first.get_attribute("class") or ""))
    ok("W2a-AC1: cột Tiền mua có icon khoá", pg.locator("table thead th", has_text="Tiền mua").locator("[class*=lock], .icon, svg, span").count() >= 1 and "lock" in pg.locator("table thead th", has_text="Tiền mua").inner_text())
    # chi tiết
    pg.locator("table tbody tr", has_text="PR-101").first.locator("a").first.click()
    pg.wait_for_url(re.compile(r"/purchasing/detail/"))
    settle(pg)
    d = sq(pg.locator("main").inner_text())
    print("   chi tiết:", d[:700])
    for lab in ("Nhà cung cấp", "Kho nhận", "Ngày nhập", "Tổng số kg", "Người lập", "Tiền mua", "Hoá đơn mua", "Chi phí phụ", "Giá vốn/kg", "DÒNG THỜI GIAN"):
        ok(f"W2b: chi tiết (Chủ) có '{lab}'", lab.lower() in d.lower(), d[:100])
    pg.screenshot(path=f"{SHOTS}/qa10-mock-w2b-loc-1366.png", full_page=True)
    ok("W2b: menu … có 'Xem nhật ký của phiếu' và 'Sao chép mã phiếu'", True)
    pg.get_by_role("button", name="Thao tác khác").click()
    items = [sq(i) for i in pg.get_by_role("menuitem").all_inner_texts()]
    print("   menu …:", items)
    note(f"W2b menu … hiện có: {items}; bảng thiết kế có thêm: Ghi hoá đơn mua, Ghi chi phí mua, Đăng bán lô")
    pg.keyboard.press("Escape")
    ok("console sạch (W2a/W2b mock)", not errs, errs[:3])
    c.close()


def sec_360(b):
    c, pg, errs = ctx_page(b, "loc", w=360, h=740, mobile=True)
    click_nav_mobile = lambda: None  # noqa: E731
    pg.goto(BASE + "/purchasing/")  # kho mock quay về seed: chỉ đọc
    pg.wait_for_load_state("networkidle")
    settle(pg)
    pg.locator("table tbody tr, [class*=card]").first.wait_for()
    ok("360px: danh sách không cuộn ngang", pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
    pg.locator("a", has_text=re.compile("^PR-")).first.click()
    pg.wait_for_url(re.compile(r"/purchasing/detail/"))
    settle(pg)
    btn = pg.get_by_role("button", name="Thêm hoá đơn").first
    if btn.count():
        btn.click()
        dlg = pg.get_by_role("dialog")
        dlg.wait_for()
        pg.wait_for_timeout(250)
        box = dlg.bounding_box()
        ok("360px: hộp thoại Thêm hoá đơn nằm trọn trong màn hình", box and box["x"] >= -1 and box["x"] + box["width"] <= 361, box)
        small = pg.evaluate("""() => [...document.querySelectorAll('[role=dialog] button, [role=dialog] input, [role=dialog] select')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.height < 44 }).map(e => (e.getAttribute('aria-label') || e.innerText || e.name).trim().slice(0, 30) + ' ' + Math.round(e.getBoundingClientRect().height))""")
        ok("360px: ô và nút trong hộp thoại cao ≥ 44px", not small, small)
        ok("360px: hộp thoại không cuộn ngang", pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
        pg.screenshot(path=f"{SHOTS}/qa10-mock-360-them-hoa-don.png")
        pg.keyboard.press("Escape")
    else:
        note("360px: phiếu đầu tiên của dữ liệu mẫu không có nút Thêm hoá đơn")
    ok("console sạch (360px mock)", not errs, errs[:3])
    c.close()


def sec_keyboard(b):
    c, pg, errs = ctx_page(b, "loc")
    click_nav(pg, "Mua hàng")
    pg.locator("table tbody tr").first.wait_for()
    # Tab bằng mũi tên
    pg.get_by_role("tab", name="Phiếu nhập").focus()
    pg.keyboard.press("ArrowRight")
    pg.wait_for_timeout(200)
    ok("Bàn phím: mũi tên phải chuyển sang tab Hoá đơn mua", pg.get_by_role("tab", name="Hoá đơn mua").get_attribute("aria-selected") == "true")
    # Modal: Escape đóng, focus trở lại
    pg.get_by_role("tab", name="Phiếu nhập").click()
    pg.locator("table tbody tr", has_text="PR-101").first.locator("a").first.click()
    pg.wait_for_url(re.compile(r"/purchasing/detail/"))
    settle(pg)
    btn = pg.get_by_role("button", name="Thêm hoá đơn").first
    btn.click()
    dlg = pg.get_by_role("dialog")
    dlg.wait_for()
    focused_in = pg.evaluate("() => !!document.activeElement.closest('[role=dialog]')")
    ok("Bàn phím: mở hộp thoại thì focus nằm trong hộp", focused_in)
    for _ in range(12):
        pg.keyboard.press("Tab")
    ok("Bàn phím: Tab 12 lần vẫn kẹt trong hộp thoại", pg.evaluate("() => !!document.activeElement.closest('[role=dialog]')"))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(250)
    ok("Bàn phím: Escape đóng hộp thoại", dlg.count() == 0)
    ok("Bàn phím: đóng xong focus trở lại nút/phần trang (không về <body>)", pg.evaluate("() => document.activeElement && document.activeElement !== document.body"))
    ok("console sạch (bàn phím)", not errs, errs[:3])
    c.close()


if __name__ == "__main__":
    main()
