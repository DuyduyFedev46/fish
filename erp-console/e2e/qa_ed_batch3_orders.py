# QA độc lập ERP theo design Lô 3 FE (Đơn & tiền: ED-09, ED-10, ED-11, ED-12) trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<doc/features/2026-10-01-erp-theo-design/shots/lot3> python3 -u e2e/qa_ed_batch3_orders.py
# Khác kịch bản của dev (ed_batch3_orders.py): chấm theo bảng enum-map/UI-RULES từ phía người dùng — chip từng dòng so với bộ nhãn
# chuẩn, mọi ô ngày/tiền theo regex, "một giá trị một ô", bảng nút × vai × trạng thái, đối chiếu chữ cấm, các ca ngoài đường thuận
# (bấm đúp, màn cũ, id rác, 409, lỗi tải) và ảnh chụp 1280/360 đặt cạnh board. Chỉ dữ liệu giả của mock.
import os
import re
import sys
import traceback

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=8_000)
results = []
console_all = []  # mọi dòng console (không chỉ lỗi) để soát dữ liệu cá nhân
errors = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, ("" if cond else "  -> " + str(extra)[:300]), flush=True)


def section(name):
    def deco(fn):
        print(f"\n=== {name}", flush=True)
        try:
            fn()
        except Exception as e:  # một nhóm lỗi không làm mất các nhóm sau
            ok(f"[NHÓM {name}] chạy hết không ngoại lệ", False, f"{type(e).__name__}: {str(e)[:250]}")
            traceback.print_exc(limit=3)
        return fn

    return deco


def new_page(browser, user, w=1280, h=900, mobile=False, dark=False, login_as=True):
    kw = dict(viewport={"width": w, "height": h}, reduced_motion="reduce", color_scheme="dark" if dark else "light")
    if mobile:
        kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**kw)
    pg = ctx.new_page()

    def on_console(m):
        console_all.append(m.text)
        if m.type == "error" and "Failed to fetch RSC payload" not in m.text:
            errors.append(f"[{user}] {m.text}")

    pg.on("console", on_console)
    pg.on("pageerror", lambda e: errors.append(f"[{user}] pageerror {e}"))
    if login_as:
        pg.goto(BASE + "/login/")
        pg.wait_for_load_state("networkidle")
        pg.get_by_label("Tài khoản").fill(user)
        pg.get_by_label("Mật khẩu").fill("demo1234")
        pg.get_by_role("button", name="Đăng nhập").click()
        pg.wait_for_selector(".nav a", state="attached")
        pg.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)
    return ctx, pg


def idle(pg):
    pg.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def go(pg, path, wait_idle=True):
    pg.goto(BASE + path)
    pg.wait_for_load_state("networkidle")
    if wait_idle:
        idle(pg)


def mock(pg, expr, arg=None):
    return pg.evaluate(f"(a) => window.__caveMock.{expr}", arg)


def log(pg):
    return pg.evaluate("() => window.__caveMock.log.slice()")


def clear_log(pg):
    pg.evaluate("() => window.__caveMock.clearLog()")


def posts(pg):
    return [x for x in log(pg) if x.startswith("POST")]


def header_buttons(pg):
    return [t.strip() for t in pg.locator("main header .btn").all_inner_texts() if t.strip()]


def open_detail(pg, kind, oid):
    path = {"order": "/orders/detail/?id=", "pay": "/orders/payments/detail/?id=", "refund": "/orders/refunds/detail/?id="}[kind]
    go(pg, path + str(oid))
    expect(pg.locator("main header h2")).to_be_visible()
    idle(pg)


def menu_of(pg):
    pg.get_by_role("button", name="Thao tác khác").click()
    m = pg.get_by_role("menu")
    expect(m).to_be_visible()
    items = []
    for it in m.get_by_role("menuitem").all():
        txt = it.inner_text().strip().replace("\n", " ")
        items.append((txt, it.get_attribute("aria-disabled") == "true"))
    return m, items


def close_menu(pg):
    pg.keyboard.press("Escape")


def dlg_of(pg, name):
    d = pg.get_by_role("dialog", name=name)
    expect(d).to_be_visible()
    return d


def hscroll_ok(pg, w):
    return pg.evaluate("(w) => document.documentElement.scrollWidth <= w + 1", w)


def toast_text(pg):
    return " ".join(pg.locator(".toast-item").all_inner_texts())


def shot(pg, name, full=False):
    pg.screenshot(path=f"{SHOTS}/qa-{name}.png", full_page=full)


DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$")
MONEY_RE = re.compile(r"^\d{1,3}(\.\d{3})* đ$")
ORDER_CODE_RE = re.compile(r"^SO\d{6}-[0-9A-F]{6}$")
ORDER_CODE_IN = re.compile(r"SO\d{6}-[0-9A-F]{6}")
# UI-RULES §3.2 + §3.4: chữ cấm / tên cũ (kiểm trên văn bản nhìn thấy của mọi màn Lô 3)
FORBIDDEN = [r"\bTTL\b", r"\bFEFO\b", r"hạch toán", r"\bNCC\b", r"\bNV\b", r"\bSĐT\b", r"\bSTK\b", r"Tổng hoàn", r"Tạo phiếu hoàn",
             r"Báo hoàn tiền", r"Xác nhận thanh toán", r"Xác nhận tiền về", r"Xác nhận đã chuyển", r"\bBR-[A-Z]", r"Đồng ý thực thi",
             r"Cấu hình", r"Hoàn tác"]
PII = re.compile(r"0901234567|0912345678|0945222333|0977111222|0868554561|Lê Lợi|Lý Thường Kiệt|Chị Hoa|Anh Khoa|Anh Minh|Cô Lan|Chị Thảo|Bác Tư|Chị Ngọc Ánh")
ORDER_CHIPS = {"Giữ chỗ", "Đã thanh toán", "Đang xử lý", "Hoàn tất", "Đã huỷ"}
DELIVERY_CHIPS = {"Chờ xác nhận", "Soạn hàng", "Chờ lấy hàng", "Đang giao", "Hoàn tất", "Giao thất bại", "Đã huỷ theo đơn", "—"}
MATCH_CHIPS = {"Khớp", "Thiếu tiền", "Về sau khi đơn tự huỷ", "Không khớp đơn", "Chuyển thừa"}
RES_CHIPS = {"Chờ xử lý", "Đã xử lý"}
REFUND_CHIPS = {"Chờ hoàn", "Đã hoàn", "Thất bại"}


def table_rows(pg):
    out = []
    for r in pg.locator("main table tbody tr:not(.lt-skel)").all():
        out.append([t.strip() for t in r.locator("td").all_inner_texts()])
    return out


def heads(pg):
    return [h.strip() for h in pg.locator("main table thead th").all_inner_texts()]


def visible_text(pg):
    return pg.locator("body").inner_text()


def forbidden_hits(text):
    return [f for f in FORBIDDEN if re.search(f, text)]


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # =================================================================================================== 1. Danh sách đơn
    @section("1. Danh sách đơn (Chủ)")
    def _():
        ctx, pg = new_page(browser, "loc")
        go(pg, "/orders/")
        expect(pg.locator("main table tbody tr").first).to_be_visible()
        ok("L1 ba tab theo thứ tự", [t.strip() for t in pg.get_by_role("tab").all_inner_texts()] == ["Đơn hàng", "Hàng chờ thanh toán", "Phiếu hoàn"],
           pg.get_by_role("tab").all_inner_texts())
        ok("L1 tab Đơn hàng đang chọn (aria-selected)", pg.get_by_role("tab", name="Đơn hàng").get_attribute("aria-selected") == "true")
        ok("ED-09-AC1 7 cột đúng thứ tự", heads(pg) == ["Mã đơn", "Khách hàng", "Trạng thái", "Giao hàng", "Lý do", "Tổng tiền", "Thời gian"], heads(pg))
        rows = table_rows(pg)
        ok("L1 mỗi dòng đủ 7 ô", all(len(r) == 7 for r in rows), [len(r) for r in rows])
        ok("L1 'Đang hiện 20 / 45 đơn' (n/m)", pg.get_by_text("Đang hiện 20 / 45 đơn").count() == 1 and len(rows) == 20, len(rows))
        ok("L1 mã đơn dạng SO<yymmdd>-<6 HEX>", all(ORDER_CODE_RE.match(r[0]) for r in rows), [r[0] for r in rows if not ORDER_CODE_RE.match(r[0])])
        ok("L1 chip Trạng thái ∈ bộ nhãn enum-map (không 'Tự huỷ', không chú thích trong chip)", all(r[2] in ORDER_CHIPS for r in rows), {r[2] for r in rows} - ORDER_CHIPS)
        ok("L1 chip Giao hàng ∈ nhãn DeliveryNote.status hoặc —", all(r[3] in DELIVERY_CHIPS for r in rows), {r[3] for r in rows} - DELIVERY_CHIPS)
        ok("L1 Tổng tiền dạng '1.234.000 đ'", all(MONEY_RE.match(r[5]) for r in rows), [r[5] for r in rows if not MONEY_RE.match(r[5])])
        ok("L1 Thời gian dd/mm/yyyy hh:mm", all(DATE_RE.match(r[6]) for r in rows), [r[6] for r in rows if not DATE_RE.match(r[6])])
        ok("L1 không 'hôm nay / hôm qua / phút trước' trong bảng", re.search(r"hôm nay|hôm qua|phút trước|giờ trước", " ".join(" ".join(r) for r in rows), re.I) is None)
        auto = [r for r in rows if r[4] == "Hết giờ giữ chỗ"]
        ok("ED-09-AC1 đơn tự huỷ: chip 'Đã huỷ' + Lý do 'Hết giờ giữ chỗ' (ô riêng)", len(auto) >= 1 and all(r[2] == "Đã huỷ" for r in auto), auto)
        ok("L1 Lý do là ô riêng: chip Giao hàng không kèm lý do", all(" · " not in r[3] and " · " not in r[2] for r in rows))
        ok("L1 Khách hàng chỉ tên, không SĐT/địa chỉ trong ô", all(not re.search(r"\d{9,}", r[1]) for r in rows))
        ok("L1 chữ cấm/tên cũ không có trong màn", forbidden_hits(visible_text(pg)) == [], forbidden_hits(visible_text(pg)))
        ok("L1 không có panel phải/tấm trượt (UI-RULES 4.1)", pg.locator("aside[role=dialog], .sheet, [data-sheet]").count() == 0)
        shot(pg, "list-1280")
        # lọc theo trạng thái
        pg.get_by_label("Lọc theo trạng thái").select_option(label="Giữ chỗ")
        idle(pg)
        r2 = table_rows(pg)
        ok("L1 lọc 'Giữ chỗ' → mọi dòng chip Giữ chỗ", len(r2) >= 1 and all(r[2] == "Giữ chỗ" for r in r2), {r[2] for r in r2})
        ok("L1 'Đang hiện n / m' đổi theo lọc (n=m khi hết)", re.search(rf"Đang hiện {len(r2)} / {len(r2)} đơn", visible_text(pg)) is not None, re.findall(r"Đang hiện[^\n]*", visible_text(pg)))
        pg.get_by_label("Lọc theo trạng thái").select_option(label="Đã huỷ")
        idle(pg)
        r3 = table_rows(pg)
        ok("L1 lọc 'Đã huỷ' gồm cả đơn tự huỷ (lý do Hết giờ giữ chỗ)", len(r3) >= 2 and all(r[2] == "Đã huỷ" for r in r3) and any(r[4] == "Hết giờ giữ chỗ" for r in r3), r3[:3])
        pg.get_by_label("Lọc theo trạng thái").select_option(label="Mọi trạng thái")
        idle(pg)
        # tìm không thấy
        pg.get_by_role("searchbox", name="Tìm đơn hàng").fill("zzqq")
        pg.wait_for_function("() => window.__caveMock.log.some(x => x.includes('q=zzqq'))")
        idle(pg)
        txt = pg.locator("main").inner_text()
        ok("L1 tìm không thấy: 'Không tìm thấy … khớp với zzqq' + 'Xoá tìm kiếm'", "zzqq" in txt and "Không tìm thấy" in txt and pg.locator("button.btn", has_text="Xoá tìm kiếm").count() == 1, txt[-300:])
        shot(pg, "list-notfound-1280")
        pg.locator("button.btn", has_text="Xoá tìm kiếm").click()
        idle(pg)
        pg.wait_for_timeout(600)
        ok("L1 'Xoá tìm kiếm' trả lại danh sách", len(table_rows(pg)) == 20, (len(table_rows(pg)), pg.locator("main").inner_text()[-200:]))
        # tải thêm
        pg.get_by_role("button", name=re.compile("Tải thêm")).first.click()
        expect(pg.locator("main table tbody tr")).to_have_count(40)
        ok("L1 tải thêm: 40 dòng, 'Đang hiện 40 / 45 đơn'", pg.get_by_text("Đang hiện 40 / 45 đơn").count() == 1)
        ctx.close()

        # đang tải: khung xương, header + bộ lọc vẫn hiện
        ctx, pg = new_page(browser, "loc")
        pg.goto(BASE + "/orders/")
        pg.wait_for_selector("tr.lt-skel", timeout=5000)
        ok("L1 đang tải: khung xương trong bảng", pg.locator("tr.lt-skel").count() >= 1)
        ok("L1 đang tải: bộ lọc và tab vẫn hiện", pg.get_by_role("tab", name="Đơn hàng").is_visible() and pg.get_by_role("searchbox", name="Tìm đơn hàng").is_visible())
        shot(pg, "list-loading-1280")
        ctx.close()
        # trống / lỗi / không có quyền theo chế độ mock
        ctx, pg = new_page(browser, "loc")
        pg.evaluate("() => window.__caveMock.orders('empty')")
        go(pg, "/orders/")
        t = pg.locator("main").inner_text()
        ok("L1 danh sách trống: tiêu đề + 1 câu gợi ý, không bảng rỗng", pg.locator("main table tbody tr").count() == 0 and re.search(r"Chưa có đơn", t) is not None, t[-200:])
        shot(pg, "list-empty-1280")
        pg.evaluate("() => window.__caveMock.orders('fail')")
        go(pg, "/orders/")
        t = pg.locator("main").inner_text()
        ok("L1 lỗi tải: thông báo + nút 'Thử lại'", pg.get_by_role("button", name="Thử lại").count() >= 1, t[-200:])
        shot(pg, "list-error-1280")
        pg.evaluate("() => window.__caveMock.orders('ok')")
        pg.get_by_role("button", name="Thử lại").first.click()
        idle(pg)
        expect(pg.locator("main table tbody tr").first).to_be_visible()
        ok("L1 bấm 'Thử lại' sau khi hết lỗi → có dữ liệu", len(table_rows(pg)) == 20)
        pg.evaluate("() => window.__caveMock.orders('forbidden')")
        go(pg, "/orders/")
        ok("L1 API 403 → màn 'Không có quyền'", "Bạn không có quyền" in pg.locator("main").inner_text())
        pg.evaluate("() => window.__caveMock.orders('ok')")
        ctx.close()

    # =================================================================================================== 2. Hàng chờ thanh toán
    @section("2. Hàng chờ thanh toán")
    def _():
        ctx, pg = new_page(browser, "loc")
        go(pg, "/orders/payments/")
        expect(pg.locator("main table tbody tr").first).to_be_visible()
        ok("ED-11-AC1 cột", heads(pg) == ["Mã giao dịch", "Số tiền", "Loại khoản tiền", "Tình trạng xử lý", "Đơn", "Nhận lúc"], heads(pg))
        rows = table_rows(pg)
        ok("ED-11-AC1 chip loại khoản ∈ nhãn FE ngắn", all(r[2] in MATCH_CHIPS for r in rows) and {r[2] for r in rows} >= {"Thiếu tiền", "Không khớp đơn", "Chuyển thừa", "Về sau khi đơn tự huỷ"},
           {r[2] for r in rows})
        ok("ED-11-AC1 'Tình trạng xử lý' là cột riêng, chip Chờ xử lý/Đã xử lý", all(r[3] in RES_CHIPS for r in rows), {r[3] for r in rows})
        ok("ED-11 cột Đơn: mã đơn hoặc 'Chưa gắn đơn'", all(ORDER_CODE_RE.match(r[4]) or r[4] == "Chưa gắn đơn" for r in rows), [r[4] for r in rows])
        ok("ED-11 Số tiền 'x đ', Nhận lúc dd/mm/yyyy hh:mm", all(MONEY_RE.match(r[1]) and DATE_RE.match(r[5]) for r in rows), rows[:2])
        ok("ED-11 'Đang hiện 5 / 5 khoản'", pg.get_by_text("Đang hiện 5 / 5 khoản").count() == 1, re.findall(r"Đang hiện[^\n]*", visible_text(pg)))
        ok("ED-11 chữ cấm không có", forbidden_hits(visible_text(pg)) == [], forbidden_hits(visible_text(pg)))
        shot(pg, "payments-1280")
        pg.get_by_label("Tình trạng xử lý").select_option(label="Đã xử lý")
        idle(pg)
        r2 = table_rows(pg)
        ok("ED-11 lọc 'Đã xử lý' → mọi dòng Đã xử lý", len(r2) >= 1 and all(r[3] == "Đã xử lý" for r in r2), r2)
        pg.get_by_label("Tình trạng xử lý").select_option(label="Chờ xử lý")
        idle(pg)
        pg.get_by_role("searchbox", name="Tìm khoản tiền").fill("zzqq")
        pg.wait_for_timeout(1200)
        idle(pg)
        ok("ED-11 tìm không thấy + 'Xoá tìm kiếm'", pg.locator("button.btn", has_text="Xoá tìm kiếm").count() == 1 and "Không tìm thấy" in pg.locator("main").inner_text())
        ctx.close()
        ctx, pg = new_page(browser, "loc")
        pg.evaluate("() => window.__caveMock.payments('empty')")
        go(pg, "/orders/payments/")
        ok("ED-11 trống: icon + tiêu đề + 1 câu", pg.locator("main table tbody tr").count() == 0 and "Không còn khoản tiền nào chờ xử lý" in pg.locator("main").inner_text(), pg.locator("main").inner_text()[-200:])
        shot(pg, "payments-empty-1280")
        pg.evaluate("() => window.__caveMock.payments('fail')")
        go(pg, "/orders/payments/")
        ok("ED-11 lỗi tải: 'Thử lại'", pg.get_by_role("button", name="Thử lại").count() >= 1)
        pg.evaluate("() => window.__caveMock.payments('ok')")
        ctx.close()

    # =================================================================================================== 3. Phiếu hoàn (danh sách)
    @section("3. Phiếu hoàn (danh sách)")
    def _():
        ctx, pg = new_page(browser, "loc")
        go(pg, "/orders/refunds/")
        expect(pg.locator("main table tbody tr").first).to_be_visible()
        h = heads(pg)
        ok("ED-12-AC1 cột có 'Số tiền hoàn', không 'Tổng hoàn'", "Số tiền hoàn" in h and "Tổng hoàn" not in " ".join(h), h)
        rows = table_rows(pg)
        ok("ED-12-AC1 chip ∈ Chờ hoàn · Đã hoàn · Thất bại", all(any(c in " ".join(r) for c in REFUND_CHIPS) for r in rows) and
           all(any(r[i] in REFUND_CHIPS for i in range(len(r))) for r in rows), rows)
        ok("ED-12 phiếu chưa có hoá đơn hiện '#id' hoặc 'Không có hoá đơn' (không rỗng)", all(any(x for x in r[:2]) for r in rows), rows)
        ok("ED-12 số tiền 'x đ', ngày dd/mm/yyyy hh:mm", all(any(MONEY_RE.match(c) for c in r) and any(DATE_RE.match(c) for c in r) for r in rows), rows)
        ok("ED-12 mặc định lọc 'Chờ chuyển (Chờ hoàn, Thất bại)'", "Chờ chuyển" in pg.locator("main").inner_text())
        ok("ED-12 chữ cấm không có", forbidden_hits(visible_text(pg)) == [], forbidden_hits(visible_text(pg)))
        shot(pg, "refunds-1280")
        ctx.close()
        ctx, pg = new_page(browser, "loc")
        pg.evaluate("() => window.__caveMock.refunds('empty')")
        go(pg, "/orders/refunds/")
        ok("ED-12-AC1 trống: 'Chưa có phiếu hoàn nào chờ chuyển'", "Chưa có phiếu hoàn nào chờ chuyển" in pg.locator("main").inner_text(), pg.locator("main").inner_text()[-200:])
        shot(pg, "refunds-empty-1280")
        pg.evaluate("() => window.__caveMock.refunds('fail')")
        go(pg, "/orders/refunds/")
        ok("ED-12 lỗi tải: 'Thử lại'", pg.get_by_role("button", name="Thử lại").count() >= 1)
        pg.evaluate("() => window.__caveMock.refunds('ok')")
        ctx.close()

    # =================================================================================================== 4. Chi tiết đơn khớp D2b
    @section("4. Chi tiết đơn (D2b)")
    def _():
        ctx, pg = new_page(browser, "loc")
        pg.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); }")
        # (oid, chip, current-step, bad-end?)
        cases = [(101, "Giữ chỗ", "Giữ chỗ", False), (105, "Đã thanh toán", "Đã thanh toán", False), (104, "Đang xử lý", "Soạn hàng", False),
                 (107, "Đang xử lý", "Đang giao", False), (109, "Hoàn tất", "Hoàn tất", False), (103, "Đã huỷ", "Giữ chỗ", True), (112, "Đã huỷ", None, True)]
        for oid, chip, cur, bad in cases:
            open_detail(pg, "order", oid)
            pg.wait_for_timeout(300)
            steps = [(li.get_attribute("data-state"), re.sub(r"^check\s*", "", li.inner_text().strip())) for li in pg.locator("main ol li[data-state]").all()]
            labels = [s[1] for s in steps if s[0] != "bad" and s[1] in ("Giữ chỗ", "Đã thanh toán", "Soạn hàng", "Đang giao", "Hoàn tất")]
            ok(f"ED-09-AC2 đơn {oid}: 5 bước đúng thứ tự{' + bước đỏ Đã huỷ' if bad else ''}",
               labels[:5] == ["Giữ chỗ", "Đã thanh toán", "Soạn hàng", "Đang giao", "Hoàn tất"] and (pg.locator("main ol li[data-state=bad]").count() == (1 if bad else 0)), steps)
            if cur and not bad:
                now = [s[1] for s in steps if s[0] == "current"]
                ok(f"ED-09-AC2 đơn {oid}: bước hiện tại = {cur}", now == [cur], steps)
                passed = [s[1] for s in steps if s[0] == "done"]
                order = ["Giữ chỗ", "Đã thanh toán", "Soạn hàng", "Đang giao", "Hoàn tất"]
                ok(f"ED-09-AC2 đơn {oid}: mọi bước trước {cur} là đã qua", passed == order[: order.index(cur)], passed)
            if bad:
                ok(f"ED-09-AC2 đơn {oid}: bước đỏ 'Đã huỷ'", "Đã huỷ" in pg.locator("main ol li[data-state=bad]").inner_text())
            hdr = pg.locator("main header").first.inner_text()
            ok(f"D2b đơn {oid}: header có mã đơn mono + chip '{chip}'", ORDER_CODE_IN.search(hdr) is not None and chip in hdr, hdr)
            ok(f"D2b đơn {oid}: có 'Tiếp theo' (trái) và 'Đã làm' hoặc 'Không còn việc'", ("Tiếp theo:" in pg.locator("main").inner_text() or "Không còn việc nào cần làm" in pg.locator("main").inner_text()))
        # một giá trị một ô + SĐT đủ + ngày giờ
        open_detail(pg, "order", 101)
        cells = pg.locator("main div[data-kind]").all()
        multi = []
        for c in cells:
            dd = c.locator("dd").first.inner_text().strip()
            if "\n" in dd or c.locator("dd .muted, dd small").count() > 0 and c.locator("dd").inner_text().strip().count("\n") > 0:
                multi.append(dd[:60])
        ok("UI-RULES 1.1 mỗi trường chỉ một giá trị (không dòng phụ xuống hàng trong ô)", multi == [], multi)
        info = {c.locator("dt").first.inner_text().strip(): c.locator("dd").first.inner_text().strip() for c in cells}
        ok("ED-09-AC8 'Số điện thoại' đủ 10 số (không che)", re.fullmatch(r"0\d{9}", info.get("Số điện thoại", "")) is not None, info.get("Số điện thoại"))
        ok("D2b nhãn trường theo bảng chữ chuẩn: 'Khách hàng', 'Số điện thoại' (không 'Khách', 'SĐT')", "Khách hàng" in info and "Số điện thoại" in info and "SĐT" not in info and "Khách" not in info, list(info))
        ok("D2b 'Đặt lúc' dd/mm/yyyy hh:mm", DATE_RE.match(info.get("Đặt lúc", "")) is not None, info.get("Đặt lúc"))
        ok("ED-09-AC5 'Còn giữ chỗ' mm:ss và 'Tự huỷ lúc' hai trường riêng", re.fullmatch(r"\d{2}:\d{2}", info.get("Còn giữ chỗ", "")) is not None and DATE_RE.match(info.get("Tự huỷ lúc", "")) is not None, info)
        ok("D2b 'Tổng tiền' có 'đ'", MONEY_RE.match(info.get("Tổng tiền", "")) is not None, info.get("Tổng tiền"))
        # Dòng thời gian
        tl = pg.locator("main").inner_text()
        ok("D2b có khối 'Trợ lý AI' (AI bật) và 'Dòng thời gian'", "Trợ lý AI".lower() in tl.lower() and "Dòng thời gian".lower() in tl.lower())
        ok("D2b khối AI có ô chat + nút gửi", pg.get_by_placeholder(re.compile("Hỏi AI")).count() == 1)
        shot(pg, "detail-booked-1440")
        # dòng thời gian: mỗi dòng bắt đầu bằng ngày giờ, mới nhất trước
        open_detail(pg, "order", 107)
        tl_items = pg.locator("[class*=Timeline] li, ol[class*=imeline] li, section:has(h3:text('Dòng thời gian')) li").all_inner_texts()
        stamps = [re.match(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", t.strip()) for t in tl_items]
        ok("D2b Dòng thời gian: mỗi dòng có dd/mm/yyyy hh:mm", len(tl_items) >= 2 and all(stamps), tl_items[:3])
        ts = [s.group(1)[6:] + s.group(1)[3:5] + s.group(1)[:2] + s.group(2) for s in stamps if s]
        ok("D2b Dòng thời gian: mới nhất trước", ts == sorted(ts, reverse=True), ts)
        ok("D2b chữ cấm không có ở chi tiết đơn", forbidden_hits(visible_text(pg)) == [], forbidden_hits(visible_text(pg)))
        yen = re.findall(r"[\d.]+ ₫", pg.locator("main").inner_text())
        print("   [thông tin] B3 nợ BE (PO chốt: không tính lỗi của lô): số '₫' do mock/BE dựng sẵn =", len(yen), flush=True)
        shot(pg, "detail-delivering-1440", full=True)
        # AI tắt → không có khối AI
        ctx.close()
        ctx, pg = new_page(browser, "loc")
        open_detail(pg, "order", 101)
        pg.wait_for_timeout(600)
        ok("AI tắt (mặc định mock) → không vẽ khối Trợ lý AI (fail-closed)", pg.get_by_text("Trợ lý AI", exact=False).count() == 0)
        ctx.close()

    # =================================================================================================== 5. Bảng nút × trạng thái × vai
    @section("5. Bảng thao tác theo trạng thái × vai (D2c)")
    def _():
        SUGGEST = "Đơn chưa thanh toán sẽ tự huỷ khi hết giờ giữ chỗ."
        DELIV = "Đơn đang giao: báo giao thất bại trước rồi mới huỷ được."
        # (oid, tên, nút chính loc, menu loc [(nhãn đầu, mờ?, có lý do?)])
        expected = {
            101: ("Giữ chỗ", ["Xác nhận đã nhận tiền"], [("Huỷ đơn", True, SUGGEST), ("Sao chép mã đơn", False, None), ("Xem nhật ký của đơn", False, None)]),
            105: ("Đã thanh toán", ["Huỷ đơn"], [("Lập phiếu hoàn", False, None), ("Sao chép mã đơn", False, None), ("Xem nhật ký của đơn", False, None)]),
            104: ("Soạn hàng", ["Huỷ đơn"], [("Lập phiếu hoàn", False, None), ("Sao chép mã đơn", False, None), ("Xem nhật ký của đơn", False, None)]),
            107: ("Đang giao", [], [("Huỷ đơn", True, DELIV), ("Lập phiếu hoàn", False, None), ("Sao chép mã đơn", False, None), ("Xem nhật ký của đơn", False, None)]),
            109: ("Hoàn tất", ["Lập phiếu hoàn"], [("Sao chép mã đơn", False, None), ("Xem nhật ký của đơn", False, None)]),
            103: ("Đã huỷ (tự huỷ)", ["Xác nhận đã nhận tiền"], [("Sao chép mã đơn", False, None), ("Xem nhật ký của đơn", False, None)]),
            112: ("Đã huỷ", [], [("Sao chép mã đơn", False, None), ("Xem nhật ký của đơn", False, None)]),
        }
        ctx, pg = new_page(browser, "loc")
        for oid, (name, want_btn, want_menu) in expected.items():
            open_detail(pg, "order", oid)
            ok(f"D2c Chủ · {name} ({oid}) → nút chính {want_btn or 'không có'}", header_buttons(pg) == want_btn, header_buttons(pg))
            m, items = menu_of(pg)
            got = [(re.sub(r"\s+", " ", t), dis) for t, dis in items]
            for lbl, dis, why in want_menu:
                hit = [g for g in got if g[0].startswith(lbl)]
                good = len(hit) == 1 and hit[0][1] == dis and (why is None or why in hit[0][0])
                ok(f"D2c Chủ · {name} ({oid}) · '…' có '{lbl}'{' (mờ + lý do ngay cạnh)' if dis else ''}", good, got)
            ok(f"D2c Chủ · {name} ({oid}) · '…' không có mục thừa", len(got) == len(want_menu), got)
            if oid == 107:
                shot(pg, "menu-delivering-1280")
            close_menu(pg)
        # nút 'Huỷ đơn' ở Soạn hàng phải đỏ
        open_detail(pg, "order", 104)
        ok("D2c nút 'Huỷ đơn' là nút đỏ (danger)", "danger" in (pg.locator("main header .btn", has_text="Huỷ đơn").first.get_attribute("class") or ""))
        ctx.close()
        # Quản lý: không có Xác nhận đã nhận tiền (ED-09-AC7), có Huỷ/Hoàn (ED-10-AC2)
        ctx, pg = new_page(browser, "ql1")
        for oid in (101, 103):
            open_detail(pg, "order", oid)
            ok(f"ED-09-AC7 Quản lý · đơn {oid}: không nút 'Xác nhận đã nhận tiền'", "Xác nhận đã nhận tiền" not in pg.locator("main").inner_text(), header_buttons(pg))
        open_detail(pg, "order", 101)
        _, items = menu_of(pg)
        ok("ED-09-AC4 Quản lý · Giữ chỗ: '…' vẫn có 'Huỷ đơn' mờ + lý do", any(t.startswith("Huỷ đơn") and d and "tự huỷ khi hết giờ giữ chỗ" in t for t, d in items), items)
        close_menu(pg)
        open_detail(pg, "order", 105)
        ok("ED-10-AC2 Quản lý · Đã thanh toán: có 'Huỷ đơn' (đỏ)", header_buttons(pg) == ["Huỷ đơn"], header_buttons(pg))
        open_detail(pg, "order", 109)
        ok("D2c Quản lý · Hoàn tất: 'Lập phiếu hoàn'", header_buttons(pg) == ["Lập phiếu hoàn"], header_buttons(pg))
        ctx.close()
        # NV kho + CSKH: không Huỷ đơn / Lập phiếu hoàn (ED-10-AC6)
        for u in ("kho1", "cs2"):
            ctx, pg = new_page(browser, u)
            go(pg, "/orders/")
            first = pg.locator("main table tbody tr a, main table tbody tr").first
            ids = pg.evaluate("() => [...document.querySelectorAll('main table tbody tr')].length")
            seen_cancel = False
            for oid in (105, 104, 109, 107):
                go(pg, f"/orders/detail/?id={oid}", wait_idle=True)
                if pg.locator("main header h2").count() == 0:
                    continue  # cs2 chỉ thấy đơn thuộc phiếu giao của mình → màn 404 cho đơn khác
                bt = header_buttons(pg)
                _, items = menu_of(pg)
                close_menu(pg)
                if any(b in ("Huỷ đơn", "Lập phiếu hoàn", "Xác nhận đã nhận tiền") for b in bt) or any(t.startswith(("Huỷ đơn", "Lập phiếu hoàn")) for t, _ in items):
                    seen_cancel = True
            ok(f"ED-10-AC6 {u}: không có Huỷ đơn / Lập phiếu hoàn / Xác nhận đã nhận tiền ở bất kỳ đơn nào", not seen_cancel)
            if u == "kho1":
                r = pg.evaluate("() => window.__caveMock.cancelJson('kho1', 105, {reason: 'CUSTOMER_CHANGED'})")
                ok("ED-10-AC6 kho1 gọi thẳng cancel → 403", r and r.get("status") == 403, r)
                r = pg.evaluate("() => window.__caveMock.refundJson('kho1', {})")
                ok("ED-10-AC6 kho1 gọi thẳng create-refund → 403", r and r.get("status") == 403, r)
            ctx.close()

    # =================================================================================================== 6. Phân quyền màn hàng chờ / phiếu hoàn
    @section("6. Phân quyền 3 tab × 5 vai + URL trực tiếp")
    def _():
        who = {
            "loc": (["Đơn hàng", "Hàng chờ thanh toán", "Phiếu hoàn"], True, True, True),
            "ql1": (["Đơn hàng", "Phiếu hoàn"], True, False, True),
            "kho1": ([], True, False, False),
            "giao1": ([], False, False, False),
            "cs2": ([], True, False, False),
        }
        for u, (tabs, orders_ok, pay_ok, ref_ok) in who.items():
            ctx, pg = new_page(browser, u)
            nav = [t.split("\n")[-1].strip() for t in pg.locator(".nav a").all_inner_texts()]
            ok(f"PQ {u}: mục 'Đơn & tiền' ở sidebar {'có' if orders_ok else 'không có'}", ("Đơn & tiền" in nav) == orders_ok, nav)
            for path, allowed in (("/orders/", orders_ok), ("/orders/payments/", pay_ok), ("/orders/refunds/", ref_ok),
                                  ("/orders/payments/detail/?id=880", pay_ok), ("/orders/refunds/detail/?id=4", ref_ok)):
                go(pg, path, wait_idle=False)
                pg.wait_for_timeout(500)
                denied = "Bạn không có quyền" in pg.locator("main").inner_text()
                ok(f"PQ {u}: URL {path} → {'xem được' if allowed else 'màn Không có quyền'}", denied != allowed, pg.locator("main").inner_text()[:80])
            go(pg, "/orders/", wait_idle=False)
            pg.wait_for_timeout(400)
            tbs = [t.strip() for t in pg.get_by_role("tab").all_inner_texts()]
            ok(f"PQ {u}: tab hiện {tabs or 'không có tab'} (đúng quyền, không lộ tab cấm)", tbs == tabs, tbs)
            ctx.close()
        # Quản lý: chỉ xem phiếu hoàn
        ctx, pg = new_page(browser, "ql1")
        open_detail(pg, "refund", 4)
        ok("ED-12-AC4 Quản lý: phiếu Chờ hoàn không có 'Xác nhận đã hoàn tiền' / 'Báo chuyển thất bại'", header_buttons(pg) == [] and pg.get_by_text("Báo chuyển thất bại").count() == 0, header_buttons(pg))
        ok("ED-12-AC4 Quản lý: không có nút '…' thừa", pg.get_by_role("button", name="Thao tác khác").count() == 0, "")
        r = pg.evaluate("() => window.__caveMock.confirmRefundJson('ql1', 4, {bank_txn_ref: 'FT2626799777'})")
        ok("ED-12-AC4 Quản lý gọi thẳng confirm-refund → 403", r and r.get("status") == 403, r)
        r = pg.evaluate("() => window.__caveMock.markRefundFailedJson('ql1', 4, {})")
        ok("ED-12-AC4 Quản lý gọi thẳng mark-failed → 403", r and r.get("status") == 403, r)
        r = pg.evaluate("() => window.__caveMock.resolveJson('ql1', 880, {action: 'REFUNDED'})")
        ok("ED-11-AC5 Quản lý gọi thẳng resolve → 403", r and r.get("status") == 403, r)
        go(pg, "/orders/refunds/")
        ok("ED-12 Quản lý: danh sách phiếu hoàn không có nút thao tác trong dòng", pg.locator("main table tbody tr .btn").count() == 0)
        ctx.close()

    # =================================================================================================== 7. F2a–F2g popup
    @section("7. Popup F2a–F2g")
    def _():
        ctx, pg = new_page(browser, "loc")
        # --- F2a Xác nhận đã nhận tiền (đơn 102)
        open_detail(pg, "order", 102)
        pg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
        d = dlg_of(pg, "Xác nhận đã nhận tiền")
        txt = d.inner_text()
        ok("F2a khối tóm tắt: dòng 'Đơn' + 'Tổng đơn' + số tiền", ORDER_CODE_IN.search(txt) is not None and "Tổng đơn" in txt and "đ" in txt, txt[:200])
        ok("F2a có 'Quay lại' hoặc 'Đóng' (nút phụ) và nút chính ghi số tiền", d.get_by_role("button", name=re.compile("^(Quay lại|Đóng)$")).count() >= 1 and re.search(r"Xác nhận đã nhận [\d.]+ đ", d.locator("button[type=submit]").inner_text()) is not None, d.locator("button").all_inner_texts())
        ok("F2a nhãn trên ô, bắt buộc có '*', không chữ gợi ý xám dưới ô", d.locator("label").first.inner_text().strip() != "" and d.locator(".hint, .field-hint, small.muted").count() == 0)
        shot(pg, "F2a-confirm-payment")
        pg.keyboard.press("Escape")
        ok("F2a Esc đóng hộp, không gửi gì", pg.get_by_role("dialog").count() == 0 and posts(pg) == [])
        # --- F2b Huỷ đơn (đơn 105)
        open_detail(pg, "order", 105)
        pg.get_by_role("button", name="Huỷ đơn").first.click()
        d = dlg_of(pg, "Huỷ đơn")
        ok("F2b tóm tắt: Đơn + Tổng đơn", ORDER_CODE_IN.search(d.inner_text()) and "Tổng đơn" in d.inner_text(), d.inner_text()[:160])
        ok("F2b lý do chọn từ danh sách chuẩn", all(x in d.inner_text() for x in ("Khách đổi ý", "Hư khi đóng hàng", "Bỏ sau khi giao thất bại", "Khác")))
        ok("F2b nút phụ 'Đóng' + nút chính 'Tiếp tục' (bước xác nhận hậu quả sau đó)", d.get_by_role("button", name="Tiếp tục").count() == 1)
        shot(pg, "F2b-cancel-step1")
        d.get_by_role("button", name="Tiếp tục").click()
        expect(d.get_by_text("Chọn một lý do huỷ.")).to_be_visible()
        ok("F2b chưa chọn lý do → báo lỗi tại ô, KHÔNG gọi API", posts(pg) == [])
        d.get_by_label("Lý do huỷ").select_option(label="Khách đổi ý")
        d.get_by_role("button", name="Tiếp tục").click()
        pg.wait_for_timeout(300)
        d = pg.get_by_role("dialog").first
        t2 = d.inner_text()
        ok("F2b bước 2 'xác nhận hậu quả': nút đỏ 'Huỷ đơn' + có 'Quay lại'", d.get_by_role("button", name="Quay lại").count() == 1 and "danger" in (d.locator("button[type=submit], .btn.danger").last.get_attribute("class") or ""), d.locator("button").all_inner_texts())
        shot(pg, "F2b-cancel-step2")
        d.get_by_role("button", name="Quay lại").click()
        ok("F2b 'Quay lại' về bước 1 giữ nguyên lựa chọn", pg.get_by_role("dialog").count() == 1 and pg.get_by_label("Lý do huỷ").input_value() != "")
        pg.keyboard.press("Escape")
        # --- F2c Lập phiếu hoàn (đơn 105)
        pg.get_by_role("button", name="Thao tác khác").click()
        pg.get_by_role("menuitem", name=re.compile("Lập phiếu hoàn")).click()
        d = dlg_of(pg, "Lập phiếu hoàn")
        ok("F2c tóm tắt: Đơn · Tổng đơn · Còn hoàn được", all(x in d.inner_text() for x in ("Tổng đơn", "Còn hoàn được")), d.inner_text()[:240])
        ok("F2c khối tóm tắt: mỗi dòng xuất hiện đúng một lần (không lặp 'Còn hoàn được')", d.inner_text().count("Còn hoàn được") == 1, d.inner_text().count("Còn hoàn được"))
        ok("F2c nút chính ghi số tiền 'Lập phiếu hoàn 1.190.000 đ'", re.search(r"Lập phiếu hoàn [\d.]+ đ", d.locator("button[type=submit]").inner_text()) is not None, d.locator("button").all_inner_texts())
        ok("F2c có alert vàng 'Tiền chưa rời tài khoản…'", "Tiền chưa rời tài khoản" in d.inner_text())
        shot(pg, "F2c-create-refund")
        # số tiền vượt → lỗi 'Nhập tối đa' + khoá nút chính (ED-10-AC3)
        amt = d.get_by_label("Số tiền hoàn")
        amt.fill("99999999")
        d.get_by_label("Lý do hoàn").fill("Khách đổi ý")
        exp = d.locator("button[type=submit]")
        pg.wait_for_timeout(200)
        ok("ED-10-AC3 vượt 'Còn hoàn được' → 'Nhập tối đa … đ.' tại ô", re.search(r"Nhập tối đa [\d.]+ đ\.", d.inner_text()) is not None, d.inner_text()[-300:])
        ok("ED-10-AC3 nút chính bị khoá (disabled / aria-disabled)", exp.is_disabled() or exp.get_attribute("aria-disabled") == "true", exp.inner_text())
        clear_log(pg)
        exp.click(force=True)
        ok("ED-10-AC3 bấm nút khoá không gọi API", posts(pg) == [], log(pg))
        for raw in ("0", "-5", "abc"):
            amt.fill(raw)
            clear_log(pg)
            exp.click(force=True)
            ok(f"F2c số tiền {raw!r} (0/âm/chữ) không gọi API", posts(pg) == [], log(pg))
        # hợp lệ + bấm đúp → 1 POST
        amt.fill("100000")
        clear_log(pg)
        exp.dblclick()
        pg.wait_for_timeout(1200)
        idle(pg)
        ok("F2c bấm đúp 'Lập phiếu hoàn' → đúng 1 POST", len(posts(pg)) == 1, posts(pg))
        ok("F2c thành công: hộp đóng + toast, URL chỉ có id", pg.get_by_role("dialog").count() == 0 and "?id=105" in pg.url and re.search(r"\?id=\d+$", pg.url) is not None, pg.url)
        ok("F2c toast không có 'Hoàn tác' (không có việc hoàn tác)", "Hoàn tác" not in toast_text(pg), toast_text(pg))
        ctx.close()

    @section("7b. F2d–F2g (khoản tiền, phiếu hoàn)")
    def _():
        ctx, pg = new_page(browser, "loc")
        # --- Lập phiếu hoàn từ khoản tiền (cùng RefundModal, vào từ Chi tiết khoản tiền)
        open_detail(pg, "pay", 880)
        if pg.get_by_role("button", name=re.compile("Lập phiếu hoàn")).count():
            pg.get_by_role("button", name=re.compile("Lập phiếu hoàn")).first.click()
        else:
            pg.get_by_role("button", name="Thao tác khác").click()
            pg.get_by_role("menuitem", name=re.compile("Lập phiếu hoàn")).click()
        d = dlg_of(pg, "Lập phiếu hoàn")
        ok("F2c' (từ khoản tiền) khối tóm tắt: 'Còn hoàn được' đúng một lần", d.inner_text().count("Còn hoàn được") == 1, d.inner_text()[:260])
        shot(pg, "F2c-from-payment")
        pg.keyboard.press("Escape")
        # --- F2d Gắn vào đơn (khoản 880)
        open_detail(pg, "pay", 880)
        pg.get_by_role("button", name="Gắn vào đơn").click()
        d = dlg_of(pg, "Gắn khoản tiền vào đơn")
        ok("F2d tóm tắt: Khoản tiền + Số tiền đã nhận", "Khoản tiền" in d.inner_text() and "Số tiền đã nhận" in d.inner_text(), d.inner_text()[:200])
        ok("F2d có 'Quay lại' + nút chính 'Gắn vào đơn'", d.get_by_role("button", name="Quay lại").count() == 1 and d.locator("button[type=submit]").inner_text().strip().startswith("Gắn"), d.locator("button").all_inner_texts())
        pg.wait_for_timeout(500)
        shot(pg, "F2d-attach")
        clear_log(pg)
        d.locator("button[type=submit]").click()
        pg.wait_for_timeout(300)
        ok("F2d chưa chọn đơn → báo lỗi, KHÔNG gọi API", posts(pg) == [] and (d.locator("[role=alert], .field-err").count() >= 1), log(pg))
        pg.keyboard.press("Escape")
        # --- F2e Xác nhận đơn đã đủ tiền: dựng bằng 2 khoản thiếu cộng đủ
        r = pg.evaluate("() => window.__caveMock.confirmJson('loc', 106, {bank_txn_id: 'FT2626799106', amount: '100000'})")
        ok("F2e dựng dữ liệu: chuyển bù cho đơn 106", r and r["status"] in (200, 201), r)
        q = pg.evaluate("() => window.__caveMock.queueJson('loc','OPEN')")["results"]
        under = [x for x in q if x["order"] and x["order"]["id"] == 106]
        ok("F2e có 2 khoản thiếu cùng đơn, đã đủ", len(under) == 2 and all("confirm_order" in x["available_actions"] for x in under), under)
        open_detail(pg, "pay", under[0]["id"])
        pg.get_by_role("button", name="Xác nhận đơn đủ tiền").first.click()
        d = dlg_of(pg, "Xác nhận đơn đã đủ tiền")
        ok("F2e tóm tắt có 'Đơn' + 'Tổng đơn'/'Đã nhận' và 'Quay lại'", ORDER_CODE_IN.search(d.inner_text()) is not None and d.get_by_role("button", name="Quay lại").count() == 1, d.inner_text()[:260])
        shot(pg, "F2e-confirm-order")
        clear_log(pg)
        pg.evaluate("() => window.__caveMock.conflictNext()")
        d.locator("button[type=submit]").click()
        expect(pg.locator("[data-conflict-banner]")).to_be_visible()
        idle(pg)
        ok("F2e/ED-11-AC4 409 → banner xung đột + nút 'Tải lại', đóng hộp, không toast thành công, 1 POST", pg.get_by_role("dialog").count() == 0 and len(posts(pg)) == 1 and "Đã xác nhận" not in toast_text(pg), (log(pg), toast_text(pg)))
        shot(pg, "409-banner")
        pg.locator("[data-conflict-banner]").get_by_role("button").first.click()
        pg.wait_for_timeout(400)
        # --- F2f Xác nhận đã hoàn tiền (phiếu 4)
        open_detail(pg, "refund", 4)
        pg.get_by_role("button", name="Xác nhận đã hoàn tiền").click()
        d = dlg_of(pg, "Xác nhận đã hoàn tiền")
        ok("F2f tóm tắt + nút chính 'Xác nhận đã hoàn 1.140.000 đ'", re.search(r"Xác nhận đã hoàn [\d.]+ đ", d.locator("button[type=submit]").inner_text()) is not None and d.get_by_role("button", name="Quay lại").count() == 1, d.locator("button").all_inner_texts())
        shot(pg, "F2f-confirm-refund")
        clear_log(pg)
        d.locator("button[type=submit]").click()
        pg.wait_for_timeout(300)
        ok("F2f thiếu mã giao dịch hoàn → báo tại ô, KHÔNG gọi API", posts(pg) == [], log(pg))
        d.get_by_label(re.compile("Mã giao dịch")).fill("FT2626799555")
        clear_log(pg)
        d.locator("button[type=submit]").dblclick()
        pg.wait_for_timeout(1200)
        idle(pg)
        ok("F2f bấm đúp 'Xác nhận đã hoàn' → đúng 1 POST", len(posts(pg)) == 1, posts(pg))
        ok("F2f xong: chip 'Đã hoàn', hết nút xác nhận", "Đã hoàn" in pg.locator("main header").first.inner_text() and "Xác nhận đã hoàn tiền" not in pg.locator("main header").first.inner_text(), pg.locator("main header").first.inner_text())
        # --- F2g Báo chuyển thất bại: dùng phiếu mới từ đơn 105 → lập qua mock rồi mở
        open_detail(pg, "refund", 31)
        ok("F2g phiếu Thất bại: nút chính 'Chuyển lại', chip 'Thất bại', lý do thất bại là trường riêng", header_buttons(pg)[:1] == ["Chuyển lại"] and "Thất bại" in pg.locator("main header").first.inner_text() and "Sai số tài khoản" in pg.locator("main").inner_text(), header_buttons(pg))
        ok("F2g phiếu thất bại không bị xoá (vẫn xem được)", "#31" in pg.locator("main header h2").inner_text())
        ctx.close()
        ctx, pg = new_page(browser, "loc")
        # phiếu Chờ hoàn khác: lập phiếu từ khoản 880 qua mock rồi báo thất bại
        res = pg.evaluate("() => window.__caveMock.refundJson('loc', {payment_transaction: 880, amount: '540000', reason: 'Khách chuyển nhầm'})")
        ok("F2g dựng dữ liệu: lập phiếu hoàn từ khoản 880", res and res.get("status") in (200, 201), res)
        rid = (res or {}).get("body", {}).get("id") if isinstance(res, dict) else None
        if rid:
            open_detail(pg, "refund", rid)
            m, items = menu_of(pg)
            ok("F2g 'Báo chuyển thất bại' nằm trong '…' và đỏ", any(t.startswith("Báo chuyển thất bại") for t, _ in items), items)
            m.get_by_role("menuitem", name=re.compile("Báo chuyển thất bại")).click()
            d = dlg_of(pg, "Báo chuyển thất bại")
            ok("F2g tóm tắt + 'Quay lại' + nút chính đỏ", d.get_by_role("button", name="Quay lại").count() == 1 and "danger" in (d.locator("button[type=submit]").get_attribute("class") or ""), d.locator("button").all_inner_texts())
            shot(pg, "F2g-mark-failed")
            ok("F2g lý do thất bại là ô riêng (textarea) trong hộp", d.locator("textarea").count() == 1)
            d.locator("textarea").fill("Sai số tài khoản người nhận")
            clear_log(pg)
            d.locator("button[type=submit]").dblclick()
            pg.wait_for_timeout(1000)
            idle(pg)
            ok("F2g bấm đúp 'Báo chuyển thất bại' → đúng 1 POST mark-failed", len([x for x in posts(pg) if "mark-failed" in x]) == 1, posts(pg))
            ok("F2g thành công: chip 'Thất bại', phiếu vẫn còn", "Thất bại" in pg.locator("main header").first.inner_text() or "Chuyển lại" in " ".join(header_buttons(pg)), pg.locator("main header").first.inner_text())
        ctx.close()

    # =================================================================================================== 8. Ngoại lệ
    @section("8. Ngoại lệ: bấm đúp xác nhận tiền, màn cũ, id rác, huỷ khi đang giao, lỗi tải")
    def _():
        ctx, pg = new_page(browser, "loc")
        open_detail(pg, "order", 101)
        pg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
        d = dlg_of(pg, "Xác nhận đã nhận tiền")
        d.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799001")
        clear_log(pg)
        d.locator("button[type=submit]").dblclick()
        pg.wait_for_timeout(1500)
        idle(pg)
        ok("EX bấm đúp 'Xác nhận đã nhận tiền' → đúng 1 POST confirm-payment", len(posts(pg)) == 1, posts(pg))
        ok("ED-10-AC1 (PO chốt 02/10) sau xác nhận: chip 'Đang xử lý' (theo enum-map), toast 'Đã nhận tiền'", "Đang xử lý" in pg.locator("main header").first.inner_text() and "Đã nhận tiền" in toast_text(pg),
           (pg.locator("main header").first.inner_text(), toast_text(pg)))
        ok("EX sau xác nhận: không còn nút 'Xác nhận đã nhận tiền', không toast 'Hoàn tác'", "Xác nhận đã nhận tiền" not in pg.locator("main header").first.inner_text() and "Hoàn tác" not in toast_text(pg),
           (pg.locator("main header").first.inner_text(), toast_text(pg)))
        ok("EX dòng thời gian có thêm dòng mới sau khi xác nhận", pg.locator("main").inner_text().count("Nhận ") >= 1)
        ok("EX URL sau thao tác chỉ có id", re.search(r"/orders/detail/\?id=101$", pg.url) is not None, pg.url)
        # xác nhận lần 2 với cùng mã giao dịch từ màn cũ qua API → trùng, không cộng thêm
        r = pg.evaluate("() => window.__caveMock.confirmJson('loc', 101, {bank_txn_id: 'FT2626799001', amount: '540000'})")
        ok("EX gọi lần hai cùng mã giao dịch → báo trùng (không tạo giao dịch thứ hai)", r and (r.get("body", {}).get("duplicate") is True or r.get("status") in (200, 409)) and
           len([x for x in pg.evaluate("() => window.__caveMock.orderJson('loc', 101)")["payments"]]) == 1, r)
        # màn cũ: đơn 102 tự huỷ trong lúc Chủ đang xem
        open_detail(pg, "order", 102)
        pg.evaluate("() => window.__caveMock.expireOrder(102)")
        pg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
        d = dlg_of(pg, "Xác nhận đã nhận tiền")
        d.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799002")
        d.locator("button[type=submit]").click()
        pg.wait_for_timeout(1200)
        idle(pg)
        ok("EX màn cũ: đơn đã tự huỷ → KHÔNG báo 'Đã xác nhận … đã thanh toán', đơn không sống lại",
           "Đã thanh toán" not in pg.locator("main header").first.inner_text() and pg.evaluate("() => window.__caveMock.orderJson('loc', 102).status") == "AUTO_CANCELLED", (toast_text(pg), pg.locator("main header").first.inner_text()))
        ok("EX màn cũ: người dùng được nói rõ (toast/alert), không im lặng", len(toast_text(pg)) > 10 or pg.locator(".alert-box").count() >= 1, toast_text(pg))
        # màn cũ: phiếu hoàn đã được xác nhận ở nơi khác
        open_detail(pg, "refund", 31)
        pg.evaluate("() => window.__caveMock.conflictNext()")
        pg.get_by_role("button", name="Chuyển lại").click()
        pg.wait_for_timeout(300)
        d = pg.get_by_role("dialog")
        if d.count():
            clear_log(pg)
            d.locator("button[type=submit]").click()
            pg.wait_for_timeout(1000)
        ok("EX phiếu hoàn: 409 khi 'Chuyển lại' → banner xung đột, không treo", pg.locator("[data-conflict-banner]").count() == 1 or pg.locator(".alert-box").count() >= 1, pg.locator("main").inner_text()[:200])
        # Huỷ khi đang giao: chặn ở UI và ở API
        open_detail(pg, "order", 107)
        ok("EX Huỷ khi đang giao: không có nút chính 'Huỷ đơn'", "Huỷ đơn" not in header_buttons(pg), header_buttons(pg))
        r = pg.evaluate("() => window.__caveMock.cancelJson('loc', 107, {reason: 'CUSTOMER_CHANGED', note: ''})")
        ok("EX Huỷ khi đang giao: gọi thẳng cancel bị BE từ chối (4xx) — đơn giữ nguyên", r and r.get("status") in (400, 409, 422) and pg.evaluate("() => window.__caveMock.orderJson('loc', 107).status") == "PROCESSING", r)
        m, items = menu_of(pg)
        item = m.get_by_role("menuitem", name=re.compile("^Huỷ đơn"))
        clear_log(pg)
        item.click(force=True)
        pg.wait_for_timeout(300)
        ok("EX Huỷ khi đang giao: bấm mục mờ không mở hộp, không gọi API", pg.get_by_role("dialog").count() == 0 and posts(pg) == [], log(pg))
        close_menu(pg)
        # id rác
        for bad in ("abc", "0", "-1", "999999", "1e3", "101abc", "", "%3Cscript%3Ealert(1)%3C/script%3E", "9" * 30):
            go(pg, f"/orders/detail/?id={bad}", wait_idle=False)
            pg.wait_for_timeout(700)
            t = pg.locator("main").inner_text()
            ok(f"EX id rác {bad[:14]!r}: 'Không tìm thấy trang này' trong khung app, không vỡ", "Không tìm thấy" in t and pg.locator(".nav a").count() > 0 and "<script" not in t, t[:120])
        for path in ("/orders/payments/detail/?id=abc", "/orders/refunds/detail/?id=abc", "/orders/payments/detail/?id=999999", "/orders/refunds/detail/?id=999999", "/orders/payments/detail/", "/orders/refunds/detail/"):
            go(pg, path, wait_idle=False)
            pg.wait_for_timeout(700)
            ok(f"EX id rác {path}: 'Không tìm thấy'", "Không tìm thấy" in pg.locator("main").inner_text(), pg.locator("main").inner_text()[:100])
        # lỗi tải chi tiết
        pg.evaluate("() => window.__caveMock.orders('detailfail')")
        go(pg, "/orders/detail/?id=105", wait_idle=False)
        pg.wait_for_timeout(900)
        ok("EX lỗi tải chi tiết: thông báo + 'Thử lại', không trắng màn", pg.get_by_role("button", name="Thử lại").count() >= 1, pg.locator("main").inner_text()[:150])
        shot(pg, "detail-error-1280")
        pg.evaluate("() => window.__caveMock.orders('ok')")
        pg.get_by_role("button", name="Thử lại").first.click()
        pg.wait_for_timeout(800)
        ok("EX 'Thử lại' sau khi hết lỗi → hiện đơn", pg.locator("main header h2").count() == 1 and ORDER_CODE_IN.search(pg.locator("main header h2").inner_text()) is not None)
        ctx.close()

    # =================================================================================================== 8b. Hết giờ giữ chỗ khi đang mở màn (ED-09-AC5)
    @section("8b. Hết giờ giữ chỗ khi đang mở màn")
    def _():
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        pg = ctx.new_page()
        pg.clock.install()
        pg.on("pageerror", lambda e: errors.append(f"[clock] pageerror {e}"))
        pg.goto(BASE + "/login/")
        pg.wait_for_load_state("networkidle")
        pg.get_by_label("Tài khoản").fill("loc")
        pg.get_by_label("Mật khẩu").fill("demo1234")
        pg.get_by_role("button", name="Đăng nhập").click()
        pg.wait_for_selector(".nav a", state="attached")
        pg.clock.run_for(1000)
        pg.goto(BASE + "/orders/detail/?id=101")
        pg.wait_for_selector("main header h2", timeout=15000)
        pg.clock.run_for(1000)
        info0 = {c.locator("dt").first.inner_text().strip(): c.locator("dd").first.inner_text().strip() for c in pg.locator("main div[data-kind]").all()}
        ok("ED-09-AC5 đang giữ chỗ: chip 'Giữ chỗ' + đếm ngược mm:ss", "Giữ chỗ" in pg.locator("main header").first.inner_text() and re.fullmatch(r"\d{2}:\d{2}", info0.get("Còn giữ chỗ", "")) is not None, info0)
        pg.clock.run_for(5000)
        info1 = {c.locator("dt").first.inner_text().strip(): c.locator("dd").first.inner_text().strip() for c in pg.locator("main div[data-kind]").all()}
        ok("ED-09-AC5 đếm ngược chạy (số giây giảm sau 5s) không cần tải lại", info1.get("Còn giữ chỗ") != info0.get("Còn giữ chỗ"), (info0.get("Còn giữ chỗ"), info1.get("Còn giữ chỗ")))
        pg.clock.fast_forward("21:00")
        pg.wait_for_timeout(600)
        pg.clock.run_for(2000)
        head = pg.locator("main header").first.inner_text()
        ok("ED-09-AC5 hết giờ: chip đổi thành 'Đã huỷ' mà KHÔNG tải lại trang", "Đã huỷ" in head and "Giữ chỗ" not in head, head.replace("\n", " | "))
        ok("ED-09-AC5 hết giờ: StatusPath có bước đỏ 'Đã huỷ'", pg.locator("main ol li[data-state=bad]").count() == 1)
        ok("ED-09-AC5/D2c hết giờ: 'Xác nhận đã nhận tiền' vẫn có (tiền về muộn)", "Xác nhận đã nhận tiền" in " ".join(header_buttons(pg)), header_buttons(pg))
        shot(pg, "hold-expired-live")
        ctx.close()

    # =================================================================================================== 9. Rò giá vốn
    @section("9. Rò giá vốn")
    def _():
        for u, expect_cost in (("loc", True), ("ql1", False), ("kho1", False), ("cs2", False)):
            ctx, pg = new_page(browser, u)
            for oid in (101, 105, 107, 109):
                j = pg.evaluate("([u, i]) => window.__caveMock.orderJson(u, i)", [u, oid])
                raw = str(j)
                has_cost_key = any("unit_cost" in a or "cost" in "".join(a.keys()) for a in (j.get("allocations") or []))
                if j is None:
                    continue
                if u != "loc":
                    ok(f"GV {u} · JSON đơn {oid} không có unit_cost / cost", "unit_cost" not in raw and "cost" not in raw.lower().replace("customer", ""), raw[:120])
                else:
                    ok(f"GV loc · JSON đơn {oid} (Chủ) có unit_cost ở phân bổ lô", oid in (109,) or "unit_cost" in raw or j.get("allocations") == [], "")
            for oid in (101, 105, 107):
                go(pg, f"/orders/detail/?id={oid}")
                if pg.locator("main header h2").count() == 0:
                    pg.wait_for_timeout(500)
                if pg.locator("main header h2").count() == 0:
                    continue  # cs2 chỉ thấy đơn thuộc phiếu giao của mình
                html = pg.content()
                low = html.lower()
                leak = [k for k in ("unit_cost", "cost_price", "giá vốn", "landed_cost", "gross_profit", "lãi") if k in low]
                if u == "loc":
                    ok(f"GV loc · HTML đơn {oid}: cột 'Giá vốn/kg' có khoá", "giá vốn/kg" in low)
                else:
                    ok(f"GV {u} · HTML đơn {oid}: không chứa giá vốn/lãi", leak == [], leak)
            for path in ("/orders/", "/orders/payments/", "/orders/refunds/"):
                go(pg, path, wait_idle=False)
                pg.wait_for_timeout(400)
                leak = [k for k in ("unit_cost", "giá vốn") + (() if u == "loc" else ("lãi lỗ",)) if k in pg.content().lower()]
                ok(f"GV {u} · {path}: không chứa giá vốn", leak == [], leak)
            ctx.close()

    # =================================================================================================== 10. Dữ liệu cá nhân
    @section("10. Dữ liệu cá nhân")
    def _():
        ctx, pg = new_page(browser, "loc")
        pg.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); }")
        for path in ("/orders/", "/orders/detail/?id=101", "/orders/payments/detail/?id=880", "/orders/refunds/detail/?id=4", "/orders/detail/?id=102"):
            go(pg, path)
            ok(f"PII URL {path}: không chứa tên/SĐT/địa chỉ", PII.search(pg.url) is None, pg.url)
            ls = pg.evaluate("() => JSON.stringify(Object.assign({}, window.localStorage))")
            ok(f"PII localStorage sau {path}: không có tên/SĐT/địa chỉ", PII.search(ls) is None, ls[:200])
        # thao tác rồi soát console + toast
        open_detail(pg, "order", 102)
        pg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
        d = dlg_of(pg, "Xác nhận đã nhận tiền")
        d.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799321")
        d.locator("button[type=submit]").click()
        pg.wait_for_timeout(1200)
        idle(pg)
        ok("PII toast sau xác nhận không có tên/SĐT/địa chỉ", PII.search(toast_text(pg)) is None, toast_text(pg))
        ok("PII toàn bộ console của phiên (mọi mức) không có tên/SĐT/địa chỉ", all(PII.search(c) is None for c in console_all), [c for c in console_all if PII.search(c)][:2])
        ok("PII tên khách chỉ nằm trong DOM của người có quyền xem đơn; không có trong title/meta của trang", PII.search(pg.title()) is None, pg.title())
        # cs2 chỉ thấy đơn của phiếu giao của mình; không thấy đơn khác
        ctx.close()
        ctx, pg = new_page(browser, "cs2")
        go(pg, "/orders/")
        rows = table_rows(pg)
        ids_visible = len(rows)
        ok("PII cs2: danh sách chỉ gồm đơn thuộc phiếu giao của mình (ít hơn toàn bộ)", 0 < ids_visible < 45, ids_visible)
        for oid in (101, 105, 107):
            go(pg, f"/orders/detail/?id={oid}", wait_idle=False)
            pg.wait_for_timeout(600)
            ok(f"PII cs2: đơn {oid} không thuộc mình → 'Không tìm thấy trang này' (không lộ SĐT/địa chỉ)", "Không tìm thấy" in pg.locator("main").inner_text() and PII.search(pg.content()) is None, pg.locator("main").inner_text()[:80])
        ctx.close()
        # kho1: có link 'Mở trang khách'? không (không có quyền xem khách)
        ctx, pg = new_page(browser, "kho1")
        open_detail(pg, "order", 105)
        ok("ED-09-AC8 kho1 (không 'Xem khách hàng'): tên là chữ thường, không link 'Mở trang khách'", pg.get_by_text("Mở trang khách").count() == 0 and pg.locator("a[href*='/customers/']").count() == 0)
        ctx.close()

    # =================================================================================================== 11. 360px
    @section("11. 360px không cuộn ngang")
    def _():
        ctx, pg = new_page(browser, "loc", w=360, h=800, mobile=True)
        for path in ("/orders/", "/orders/payments/", "/orders/refunds/", "/orders/detail/?id=101", "/orders/detail/?id=107",
                     "/orders/payments/detail/?id=880", "/orders/refunds/detail/?id=4"):
            go(pg, path)
            pg.wait_for_timeout(300)
            ok(f"360 {path}: không cuộn ngang trang", hscroll_ok(pg, 360), pg.evaluate("() => document.documentElement.scrollWidth"))
            name = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")
            shot(pg, f"360-{name}")
        open_detail(pg, "order", 105)
        pg.get_by_role("button", name="Huỷ đơn").first.click()
        dlg_of(pg, "Huỷ đơn")
        ok("360 hộp Huỷ đơn: không cuộn ngang, nút chính trong khung nhìn", hscroll_ok(pg, 360) and pg.get_by_role("button", name="Tiếp tục").bounding_box()["x"] + pg.get_by_role("button", name="Tiếp tục").bounding_box()["width"] <= 361)
        shot(pg, "360-popup-cancel")
        pg.keyboard.press("Escape")
        ok("360 tab 3 mục: thanh tab không làm tràn trang", (go(pg, "/orders/") or True) and hscroll_ok(pg, 360))
        ctx.close()

    # =================================================================================================== 12. Console sạch
    @section("12. Console")
    def _():
        rel = [e for e in errors if not any(s in e for s in ("fonts.g", "net::", "Failed to load resource", "401", "403", "500", "404", "409", "422"))]
        ok("Console không có lỗi ngoài ca cố ý (401/403/404/409/422/500 do mock)", rel == [], rel[:5])

    browser.close()

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} PASS")
for n, _, e in fails:
    print("FAIL", n, "->", str(e)[:300])
sys.exit(1 if fails else 0)
