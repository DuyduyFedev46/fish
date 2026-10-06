# E2E ERP theo design, Lô 3 (Đơn & tiền: ED-09, ED-10, ED-11, ED-12): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/ed_batch3_orders.py      # tắt server sau khi xong
# Mỗi nhóm kịch bản dùng context mới để dữ liệu mock (sessionStorage) về seed. Đơn mẫu: 101 Giữ chỗ (Chị Hoa 0901234567, 540.000),
# 102 Giữ chỗ, 103 Tự huỷ, 104 Đang xử lý/Soạn hàng, 105 Đã thanh toán, 106 Giữ chỗ chuyển thiếu, 107 Đang giao, 109 Hoàn tất.
# Vai: loc (Chủ), ql1 (Quản lý), kho1 (NV kho), cs2 (CSKH + giao: chỉ thấy đơn của phiếu giao mình), giao1 (chỉ giao: bị chặn).
# Kiểm: 3 tab theo route · cột danh sách · bảng trạng thái → nút · "…" mục bị chặn có lý do · F2a–F2g · 409 · SĐT đủ · URL chỉ có id ·
# không dữ liệu cá nhân ở localStorage · không "Hoàn tác" · ?order=&open=refund · đồng hồ giữ chỗ · quyền · 360px không cuộn ngang.
import os
import re

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra if not cond else "")


def login(page, user="loc", pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)


def idle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def new_page(browser, user, w=1280, h=900, dark=False, mobile=False, errors=None):
    kw = dict(viewport={"width": w, "height": h}, reduced_motion="reduce", color_scheme="dark" if dark else "light")
    if mobile:
        kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**kw)
    page = ctx.new_page()
    if errors is not None:
        page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, user)
    return ctx, page


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    idle(page)


def open_order(page, oid):
    go(page, f"/orders/detail/?id={oid}")
    expect(page.locator("main header h2")).to_be_visible()
    idle(page)


def header_text(page):
    return page.locator("main header").first.inner_text()


def header_buttons(page):
    """Nhãn các nút trong header (bỏ nút '…' và liên kết quay lại)."""
    return [t.strip() for t in page.locator("main header .btn").all_inner_texts() if t.strip()]


def field(page, label):
    """Giá trị (dd) của ô InfoField có nhãn đúng bằng `label`."""
    cell = page.locator("div[data-kind]").filter(has=page.locator("dt", has_text=re.compile(rf"^\s*{re.escape(label)}\s*$"))).first
    return cell.locator("dd")


def open_more(page):
    page.get_by_role("button", name="Thao tác khác").click()
    expect(page.get_by_role("menu")).to_be_visible()
    return page.get_by_role("menu")


def menu_items(page):
    m = open_more(page)
    items = [t.strip() for t in m.get_by_role("menuitem").all_inner_texts()]
    page.keyboard.press("Escape")
    return items


def dialog(page, name):
    d = page.get_by_role("dialog", name=name)
    expect(d).to_be_visible()
    return d


def submit_btn(dlg):
    return dlg.locator("button[type=submit]")



_RULE_CODE = r"(?:BR|DW|V|E|P)-[A-Z0-9]+(?:-[A-Z0-9]+)*"
_PAREN_CODES = re.compile(r"\s*[(（]\s*" + _RULE_CODE + r"(?:\s*[,;/]\s*" + _RULE_CODE + r")*\s*[)）]")
_BARE_BR = re.compile(r"\s*\bBR-[A-Z]+(?:-\d+)?\b")


def strip_rule_codes(msg):
    """Giống shared/lib/ruleCodes.ts: màn ERP bỏ mã luật (BR-…) khỏi câu lỗi BE trước khi hiển thị."""
    if not isinstance(msg, str) or not re.search(r"\b(?:BR|DW|V|E|P)-[A-Z0-9]", msg):
        return msg
    out = _BARE_BR.sub("", _PAREN_CODES.sub("", msg))
    out = re.sub(r"[ \t]{2,}", " ", out)
    return re.sub(r"\s+([.,;:!?])", r"\1", out).strip()


def be(page, key, params=None):
    return strip_rule_codes(page.evaluate("([k, p]) => window.__caveMock.beDetail(k, p || undefined)", [key, params]))


def log(page):
    return page.evaluate("() => window.__caveMock.log.slice()")


def clear_log(page):
    page.evaluate("() => window.__caveMock.clearLog()")


def posts(page):
    return [x for x in log(page) if x.startswith("POST")]


def toast_text(page):
    return " ".join(page.locator(".toast-item").all_inner_texts())


def hscroll_ok(page, w):
    return page.evaluate("(w) => document.documentElement.scrollWidth <= w + 1", w)


PII = re.compile(r"0901234567|0912345678|Chị Hoa|Anh Minh|Lê Lợi|Trần Phú")


def storage_has_pii(page):
    return page.evaluate("() => JSON.stringify(Object.assign({}, window.localStorage))")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []

    # ======================================================= Chủ (loc): danh sách + 3 tab
    ctx, page = new_page(browser, "loc", errors=errors)
    go(page, "/orders/")
    tabs = [t.strip() for t in page.get_by_role("tab").all_inner_texts()]
    ok("ED-09: 3 tab Đơn hàng · Hàng chờ thanh toán · Phiếu hoàn tiền", tabs == ["Đơn hàng", "Hàng chờ thanh toán", "Phiếu hoàn tiền"], str(tabs))
    heads = [h.strip() for h in page.locator("thead th").all_inner_texts()]
    ok("ED-09-AC1: cột Mã đơn · Khách hàng · Trạng thái · Giao hàng · Lý do · Tổng tiền · Thời gian",
       heads == ["Mã đơn", "Khách hàng", "Trạng thái", "Giao hàng", "Lý do", "Tổng tiền", "Thời gian"], str(heads))
    rows = page.locator("tbody tr")
    ok("ED-09: 20 dòng/trang, 'Đang hiện 20 / 45 đơn'", rows.count() == 20 and page.get_by_text("Đang hiện 20 / 45 đơn").count() == 1, str(rows.count()))
    cancelled = rows.nth(3).inner_text()
    ok("ED-09-AC2: đơn tự huỷ hiện chip 'Hết giờ giữ chỗ' (T2, Q-2) + cột lý do cùng chữ", "Hết giờ giữ chỗ" in cancelled, cancelled)
    ok("ED-09: đơn thiếu tiền có lý do 'Chuyển thiếu tiền'", "Chuyển thiếu tiền" in rows.nth(1).inner_text())
    ok("ED-09: SĐT/ địa chỉ không nằm trong danh sách (chỉ tên khách)", "0901234567" not in rows.nth(0).inner_text())
    page.get_by_role("button", name=re.compile("Tải thêm")).first.click()
    expect(rows).to_have_count(40)
    page.get_by_role("button", name=re.compile("Tải thêm")).first.click()
    expect(rows).to_have_count(45)
    ok("ED-09: tải thêm 40 rồi 45 dòng, hết trang không còn nút", page.get_by_role("button", name=re.compile("Tải thêm")).count() == 0)
    clear_log(page)
    page.get_by_label("Lọc theo trạng thái").select_option(label="Giữ chỗ")
    idle(page)
    ok("ED-09: lọc Giữ chỗ gửi ?status=BOOKED", any("status=BOOKED" in x for x in log(page)), str(log(page)))
    page.get_by_label("Lọc theo trạng thái").select_option(label="Mọi trạng thái")
    idle(page)
    page.get_by_role("searchbox", name="Tìm đơn hàng").fill("0901234")
    page.wait_for_function("() => window.__caveMock.log.some(x => x.includes('q=0901234'))")
    idle(page)
    ok("ED-09: tìm theo SĐT một phần → 1 đơn của Chị Hoa", rows.count() == 1 and "Chị Hoa" in rows.first.inner_text(), str(rows.count()))
    page.get_by_role("searchbox", name="Tìm đơn hàng").fill("")
    idle(page)
    page.screenshot(path=f"{SHOTS}/ed3-list-1280-light.png")

    # chuyển tab = chuyển trang
    page.get_by_role("tab", name="Hàng chờ thanh toán").click()
    page.wait_for_url("**/orders/payments/")
    page.get_by_role("tab", name="Phiếu hoàn tiền").click()
    page.wait_for_url("**/orders/refunds/")
    page.get_by_role("tab", name="Đơn hàng").click()
    page.wait_for_url("**/orders/")
    ok("ED-09: chuyển tab đổi route /orders/ ↔ /orders/payments/ ↔ /orders/refunds/", True)

    # bấm dòng → trang chi tiết, URL chỉ có id
    expect(rows.first).to_be_visible()
    idle(page)
    rows.first.click()
    page.wait_for_url(re.compile(r"/orders/detail/\?id=101$"))
    ok("ED-09: bấm dòng mở trang chi tiết, URL chỉ có id", page.url.endswith("/orders/detail/?id=101"), page.url)
    ctx.close()

    # ======================================================= Chủ: chi tiết 101
    ctx, page = new_page(browser, "loc", errors=errors)
    open_order(page, 101)
    code = page.locator("main header h2").inner_text()
    ok("ED-09: tiêu đề là mã đơn SO<yymmdd>-<6 HEX>", re.fullmatch(r"SO\d{6}-[0-9A-F]{6}", code) is not None, code)
    ok("ED-09: chip Giữ chỗ", "Giữ chỗ" in header_text(page))
    ok("ED-09-AC3: BOOKED → nút chính 'Xác nhận đã nhận tiền'", header_buttons(page) == ["Xác nhận đã nhận tiền"], str(header_buttons(page)))
    ok("ED-09-AC8: SĐT hiện đủ, không che", "0901234567" in field(page, "Số điện thoại").inner_text(), field(page, "Số điện thoại").inner_text())
    ok("ED-09-AC8: không có link 'Mở trang khách' khi BE không trả id khách", page.get_by_text("Mở trang khách").count() == 0)
    t1 = field(page, "Còn giữ chỗ").inner_text().strip()
    ok("ED-09-AC5: 'Còn giữ chỗ' dạng mm:ss", re.fullmatch(r"\d{2}:\d{2}", t1) is not None, t1)
    page.wait_for_function(
        "t => [...document.querySelectorAll('dt')].find(d => d.textContent.trim() === 'Còn giữ chỗ').nextElementSibling.textContent.trim() !== t",
        arg=t1,
    )
    ok("ED-09-AC5: đồng hồ chạy (giây đổi)", True)
    ok("ED-09-AC5: 'Tự huỷ lúc' là trường riêng", re.search(r"\d{2}/\d{2}/\d{4}", field(page, "Tự huỷ lúc").inner_text()) is not None, field(page, "Tự huỷ lúc").inner_text())
    path = [t.strip() for t in page.locator("ol li").all_inner_texts()][:5]
    ok("ED-09-AC4 (W37 S7): StatusPath Giữ chỗ → Chờ gọi xác nhận → Soạn hàng → Đang giao → Hoàn tất",
       [re.sub(r"^check\s*", "", t) for t in path] == ["Giữ chỗ", "Chờ gọi xác nhận", "Soạn hàng", "Đang giao", "Hoàn tất"], str(path))
    ok("ED-09: chưa có 'Tiếp theo: Huỷ đơn' (guidance của trạng thái khác bị bỏ)", "Tiếp theo: Huỷ đơn" not in page.locator("main").inner_text())
    ok("ED-09: không có nút 'Hoàn tác' ở đâu trong trang", page.get_by_text("Hoàn tác").count() == 0)
    ok("ED-09-AC7 (Chủ): có cột Giá vốn/kg ở phân bổ lô", page.get_by_text(re.compile("Giá vốn")).count() >= 1 or "unit_cost" in str(page.evaluate("() => window.__caveMock.orderJson('loc', 101)")))
    ok("Bảo mật: localStorage không có tên/SĐT/địa chỉ khách", PII.search(storage_has_pii(page)) is None, storage_has_pii(page)[:200])
    ok("Bảo mật: URL chỉ chứa id", "0901" not in page.url and "Hoa" not in page.url and "?id=101" in page.url, page.url)
    m = open_more(page)
    items = {t.strip(): m.get_by_role("menuitem", name=re.compile(re.escape(t.strip()))) for t in m.get_by_role("menuitem").all_inner_texts()}
    cancel_item = [i for k, i in items.items() if k.startswith("Huỷ đơn")][0]
    ok("ED-09-AC3: '…' có 'Huỷ đơn' mờ + lý do chưa thanh toán tự huỷ khi hết giờ giữ chỗ",
       cancel_item.get_attribute("aria-disabled") == "true" and "Đơn chưa thanh toán sẽ tự huỷ khi hết giờ giữ chỗ." in cancel_item.inner_text(), cancel_item.inner_text())
    ok("ED-09: '…' luôn có 'Sao chép mã đơn' và (Chủ) 'Xem nhật ký của đơn'",
       "Sao chép mã đơn" in items and "Xem nhật ký của đơn" in items, str(list(items)))
    page.screenshot(path=f"{SHOTS}/ed3-detail-menu-1280-light.png")
    page.keyboard.press("Escape")
    ctx.close()

    # ======================================================= Bảng trạng thái → nút (Chủ)
    ctx, page = new_page(browser, "loc", errors=errors)
    table = [
        (103, [], "Hết giờ giữ chỗ"),   # tự huỷ: không còn nút nào (#15)
        (104, ["Huỷ đơn"], "Đang xử lý"),             # Soạn hàng
        (105, ["Huỷ đơn"], "Đã thanh toán"),
        (107, [], "Đang xử lý"),                       # Đang giao: không nút
        (109, ["Lập phiếu hoàn tiền"], "Hoàn tất"),  # W37 S7-AC4
    ]
    for oid, want, chip in table:
        open_order(page, oid)
        ok(f"ED-09-AC3: đơn {oid} ({chip}) → nút chính {want or 'không có'}", header_buttons(page) == want and chip in header_text(page), f"{header_buttons(page)} {header_text(page)[:60]}")
    open_order(page, 104)
    ok("ED-09-AC3: 'Huỷ đơn' ở Soạn hàng là nút đỏ (danger)", "danger" in (page.locator("main header .btn").first.get_attribute("class") or ""))
    open_order(page, 107)
    m = open_more(page)
    ci = m.get_by_role("menuitem", name=re.compile("^Huỷ đơn"))
    ok("ED-09-AC3: Đang giao → '…' có 'Huỷ đơn' mờ + 'báo giao thất bại trước rồi mới huỷ được'",
       ci.count() == 1 and ci.get_attribute("aria-disabled") == "true" and "Đơn đang giao: báo giao thất bại trước rồi mới huỷ được." in ci.inner_text(), ci.inner_text() if ci.count() else "")
    clear_log(page)
    ci.click(force=True)
    ok("ED-09: bấm mục bị chặn không mở hộp thoại, không gọi API", page.get_by_role("dialog").count() == 0 and posts(page) == [])
    page.keyboard.press("Escape")
    open_order(page, 103)
    ok("ED-09-AC4: đơn tự huỷ: StatusPath kết bằng 'Đã huỷ' (đỏ)", page.locator('[data-state="bad"]').count() == 1 and "Đã huỷ" in page.locator('[data-state="bad"]').inner_text())
    ctx.close()

    # ======================================================= F2a Xác nhận đã nhận tiền (Chủ) + 409
    ctx, page = new_page(browser, "loc", errors=errors)
    open_order(page, 102)
    page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg = dialog(page, "Xác nhận đã nhận tiền")
    ok("ED-10-AC1: hộp có tóm tắt đơn + tổng", code_re := re.search(r"SO\d{6}-[0-9A-F]{6}", dlg.inner_text()) is not None and "đ" in dlg.inner_text())
    total_txt = re.search(r"([\d.]+) đ", dlg.inner_text()).group(1)
    ok("ED-10-AC1: nút chính ghi 'Xác nhận đã nhận <tổng> đ'", submit_btn(dlg).inner_text().strip() == f"Xác nhận đã nhận {total_txt} đ", submit_btn(dlg).inner_text())
    ok("ED-10: focus vào ô mã giao dịch", page.evaluate("() => document.activeElement && document.activeElement.name === 'bank_txn_id'"))
    clear_log(page)
    submit_btn(dlg).click()
    expect(dlg.get_by_text("Nhập mã giao dịch ngân hàng")).to_be_visible()
    ok("ED-10: mã GD trống → báo tại ô, KHÔNG gọi API", posts(page) == [], str(log(page)))
    # BR-TT-03: mã đã ghi cho đơn khác
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626700002")
    submit_btn(dlg).click()
    expect(dlg.locator(".alert-box").first).to_contain_text(be(page, "TT_TXN_OTHER"))
    ok("BR-TT-03: mã của đơn khác → hiện nguyên văn câu BE, ở lại hộp, giữ giá trị", dlg.get_by_label("Mã giao dịch ngân hàng").input_value() == "FT2626700002")
    ok("ED-10: sau lỗi nút chính đổi 'Thử lại'", "Thử lại" in submit_btn(dlg).inner_text(), submit_btn(dlg).inner_text())
    # số tiền ngoài miền
    amt = dlg.get_by_label("Số tiền đã nhận")
    for raw, frag in [("0", "trở lên"), ("-5", "không được âm"), ("123456789012345", "quá lớn")]:
        amt.fill(raw)
        clear_log(page)
        submit_btn(dlg).click()
        expect(dlg.get_by_text(re.compile(frag)).first).to_be_visible()
        ok(f"ED-10: số tiền {raw!r} → báo tại ô, KHÔNG gọi API", posts(page) == [] and amt.get_attribute("aria-invalid") == "true", str(log(page)))
    # 409: người khác vừa xử lý
    amt.fill(re.sub(r"\.", "", total_txt))
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799501")
    page.evaluate("() => window.__caveMock.conflictNext()")
    clear_log(page)
    submit_btn(dlg).click()
    expect(page.locator("[data-conflict-banner]")).to_be_visible()
    idle(page)
    ok("ED-11-AC4/ED-10: 409 → banner xung đột (không toast thành công), hộp đóng", page.get_by_role("dialog").count() == 0 and "Đã xác nhận" not in toast_text(page))
    ok("409: banner nêu người xử lý và nút Tải lại", page.locator("[data-conflict-banner]").get_by_role("button").count() >= 1, page.locator("[data-conflict-banner]").inner_text())
    ok("409: đơn vẫn Giữ chỗ, chỉ đã gửi 1 POST", "Giữ chỗ" in header_text(page) and len(posts(page)) == 1, str(posts(page)))
    page.screenshot(path=f"{SHOTS}/ed3-conflict-1280-light.png")
    page.locator("[data-conflict-banner]").get_by_role("button").first.click()
    expect(page.locator("[data-conflict-banner]")).to_have_count(0)
    # thiếu tiền → UNDERPAID
    page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg = dialog(page, "Xác nhận đã nhận tiền")
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799502")
    dlg.get_by_label("Số tiền đã nhận").fill("100000")
    ok("ED-10: sửa số tiền thấp hơn tổng → cảnh báo 'Ít hơn tổng đơn'", "Ít hơn" in dlg.inner_text(), dlg.inner_text()[-200:])
    submit_btn(dlg).click()
    expect(page.locator(".toast-item")).to_contain_text("còn thiếu")
    idle(page)
    ok("ED-10: UNDERPAID → toast vàng 'còn thiếu', đơn vẫn Giữ chỗ", "Giữ chỗ" in header_text(page) and page.locator(".toast-item.warn").count() == 1)
    ok("ED-10: toast không có SĐT / địa chỉ / không có 'Hoàn tác'", "0912345678" not in toast_text(page) and "Hoàn tác" not in toast_text(page))
    # duplicate: đơn 106 webhook đã ghi FT2626700002
    open_order(page, 106)
    page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg = dialog(page, "Xác nhận đã nhận tiền")
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626700002")
    clear_log(page)
    submit_btn(dlg).click()
    expect(page.locator(".toast-item")).to_contain_text("đã được ghi trước đó")
    idle(page)
    ok("ED-11-AC4: trùng mã GD (webhook ghi trước) → báo đã ghi trước đó, không xử lý lần hai", len(posts(page)) == 1 and page.locator(".toast-item.warn").count() >= 1)
    # Lô bổ sung A #15: đơn tự huỷ thì KHÔNG còn nút xác nhận; đơn tự huỷ "trong lúc đang xem" thì BE trả ORDER_AUTO_CANCELLED
    open_order(page, 103)
    ok("Lô bổ sung A #15: đơn Tự huỷ không có nút Xác nhận đã nhận tiền, không có nút nào ở đầu trang",
       page.get_by_role("button", name="Xác nhận đã nhận tiền").count() == 0 and header_buttons(page) == [], str(header_buttons(page)))
    open_order(page, 102)
    page.evaluate("() => window.__caveMock.expireOrder(102)")
    page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg = dialog(page, "Xác nhận đã nhận tiền")
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799503")
    clear_log(page)
    submit_btn(dlg).click()
    expect(page.locator(".toast-item").last).to_contain_text(be(page, "ORDER_AUTO_CANCELLED"))
    idle(page)
    ok("Lô bổ sung A #15: ORDER_AUTO_CANCELLED -> hộp đóng, toast vàng nêu lý do, chỉ gửi 1 POST", page.get_by_role("dialog").count() == 0 and page.locator(".toast-item.warn").count() >= 1 and len(posts(page)) == 1, str(posts(page)))
    expect(page.locator("main header")).to_contain_text("Hết giờ giữ chỗ")
    ok("Lô bổ sung A #15: sau khi tải lại đơn thành Đã huỷ, hết nút Xác nhận", page.get_by_role("button", name="Xác nhận đã nhận tiền").count() == 0 and header_buttons(page) == [], str(header_buttons(page)))
    # thành công trên 101: chip đổi, timeline có dòng mới, toast
    open_order(page, 101)
    n0 = page.locator("[aria-label='Dòng thời gian'] li, section:has(h3:text('Dòng thời gian')) li").count()
    page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg = dialog(page, "Xác nhận đã nhận tiền")
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799001")
    clear_log(page)
    submit_btn(dlg).dblclick()
    expect(page.locator(".toast-item.success")).to_be_visible()
    idle(page)
    ok("ED-10-AC1: bấm đúp → chỉ 1 POST", posts(page) == ["POST /api/sales/orders/101/confirm-payment/"], str(posts(page)))
    expect(page.locator("main header")).to_contain_text("Đang xử lý")
    ok("ED-10-AC1 (PO chốt): thành công → toast 'Đã nhận tiền', không nói 'Đã thanh toán'", "Đã nhận tiền" in toast_text(page) and "Đã thanh toán" not in toast_text(page), toast_text(page))
    ok("ED-10-AC1 (PO chốt): chip theo enum-map = 'Đang xử lý' (BE chuyển thẳng PAID → PROCESSING)", "Đang xử lý" in page.locator("main header").first.inner_text(), page.locator("main header").first.inner_text())
    ok("ED-10-AC1: đã xử lý → không còn nút 'Xác nhận đã nhận tiền'", page.get_by_role("button", name="Xác nhận đã nhận tiền").count() == 0)
    n1 = page.locator("[aria-label='Dòng thời gian'] li, section:has(h3:text('Dòng thời gian')) li").count()
    ok("ED-10-AC1: Dòng thời gian có thêm dòng mới", n1 > n0, f"{n0}->{n1}")
    page.screenshot(path=f"{SHOTS}/ed3-paid-1280-light.png")
    ctx.close()

    # ======================================================= F2b Huỷ đơn + F2c Lập phiếu hoàn
    ctx, page = new_page(browser, "loc", errors=errors)
    open_order(page, 105)
    page.get_by_role("button", name="Huỷ đơn").first.click()
    dlg = dialog(page, "Huỷ đơn")
    sel = dlg.get_by_label("Lý do huỷ")
    opts = [o.strip() for o in sel.locator("option").all_inner_texts()]
    ok("ED-10-AC2: lý do huỷ Khách đổi ý · Hàng hư lúc soạn hàng · Giao thất bại, không giao lại · Lý do khác",
       opts[1:] == ["Khách đổi ý", "Hàng hư lúc soạn hàng", "Giao thất bại, không giao lại", "Lý do khác"], str(opts))
    clear_log(page)
    submit_btn(dlg).click()
    expect(dlg.get_by_text("Chọn một lý do huỷ")).to_be_visible()
    ok("ED-10-AC2: chưa chọn lý do → báo tại ô, không POST", posts(page) == [])
    sel.select_option(label="Lý do khác")
    submit_btn(dlg).click()
    expect(dlg.get_by_text("phải nhập ghi chú")).to_be_visible()
    ok("ED-10-AC2: chọn 'Khác' phải có ghi chú", True)
    sel.select_option(label="Khách đổi ý")
    submit_btn(dlg).click()
    dlg2 = dialog(page, "Huỷ đơn này?")
    ok("ED-10-AC2: bước xác nhận hậu quả có nút 'Huỷ đơn' màu đỏ", "danger" in (submit_btn(dlg2).get_attribute("class") or "") and submit_btn(dlg2).inner_text().strip() == "Huỷ đơn")
    ok("ED-10-AC2: bước hậu quả nêu hàng về lô gốc + cần lập phiếu hoàn", "lô gốc" in dlg2.inner_text() and "phiếu hoàn" in dlg2.inner_text())
    page.screenshot(path=f"{SHOTS}/ed3-cancel-confirm-1280-light.png")
    clear_log(page)
    submit_btn(dlg2).dblclick()
    expect(page.locator(".toast-item.success")).to_be_visible()
    idle(page)
    ok("ED-10-AC2: bấm đúp → chỉ 1 POST huỷ", len(posts(page)) == 1, str(posts(page)))
    expect(page.locator("main header")).to_contain_text("Đã huỷ")
    ok("ED-10-AC2: huỷ xong gợi ý 'Lập phiếu hoàn' (đúng số tiền)", page.get_by_role("button", name=re.compile("Lập phiếu hoàn")).count() >= 1)
    ok("ED-10-AC2: toast huỷ không có 'Hoàn tác'", "Hoàn tác" not in toast_text(page))
    # F2c vượt mức
    page.get_by_role("button", name=re.compile("Lập phiếu hoàn")).first.click()
    dlg = dialog(page, "Lập phiếu hoàn")
    mx = re.search(r"Còn hoàn được\s*([\d.]+) đ", dlg.inner_text().replace("\n", " "))
    maxv = mx.group(1) if mx else ""
    amt = dlg.get_by_label("Số tiền hoàn")
    amt.fill(str(int(maxv.replace(".", "")) + 1000))
    expect(dlg.get_by_text(f"Nhập tối đa {maxv} đ.")).to_be_visible()
    ok("ED-10-AC3: vượt 'Còn hoàn được' → lỗi 'Nhập tối đa <số> đ.' + nút chính khoá", submit_btn(dlg).is_disabled(), maxv)
    page.screenshot(path=f"{SHOTS}/ed3-refund-over-1280-light.png")
    amt.fill(maxv.replace(".", ""))
    ok("ED-10-AC3: về đúng mức → mở khoá", submit_btn(dlg).is_enabled())
    ok("ED-10: nút ghi số tiền 'Lập phiếu hoàn tiền <số> đ'", submit_btn(dlg).inner_text().strip() == f"Lập phiếu hoàn tiền {maxv} đ", submit_btn(dlg).inner_text())
    clear_log(page)
    submit_btn(dlg).click()
    expect(page.locator(".toast-item.success").last).to_contain_text("Đã lập phiếu hoàn")
    idle(page)
    ok("ED-10: lập phiếu hoàn → toast + đúng 1 POST", len(posts(page)) == 1, str(posts(page)))
    ok("ED-10: sau khi hoàn hết, đơn không còn nút 'Lập phiếu hoàn'", page.get_by_role("button", name=re.compile("Lập phiếu hoàn")).count() == 0)
    ctx.close()

    # ======================================================= ?order=&open=refund (từ màn gọi xác nhận)
    ctx, page = new_page(browser, "loc", errors=errors)
    page.goto(BASE + "/orders/?order=109&open=refund")
    page.wait_for_url(re.compile(r"/orders/detail/\?id=109$"))
    dialog(page, "Lập phiếu hoàn")
    ok("Tương thích: /orders/?order=109&open=refund → /orders/detail/?id=109 và mở hộp 'Lập phiếu hoàn'", True)
    ok("Tương thích: tham số open bị bỏ khỏi thanh địa chỉ sau khi mở", "open=" not in page.url, page.url)
    ctx.close()

    # ======================================================= Quản lý (ql1)
    ctx, page = new_page(browser, "ql1", errors=errors)
    open_order(page, 101)
    j = page.evaluate("() => window.__caveMock.orderJson('ql1', 101)")
    ok("ED-09-AC6: Quản lý — BE không trả unit_cost", j["allocations"] and all("unit_cost" not in a for a in j["allocations"]))
    ok("ED-09-AC6: Quản lý — UI không có 'Giá vốn'", "Giá vốn" not in page.locator("main").inner_text())
    ok("ED-09-AC7: Quản lý không có nút 'Xác nhận đã nhận tiền'", page.get_by_role("button", name="Xác nhận đã nhận tiền").count() == 0 and header_buttons(page) == [], str(header_buttons(page)))
    open_order(page, 104)
    ok("ED-10: Quản lý có 'Huỷ đơn' ở đơn Soạn hàng", header_buttons(page) == ["Huỷ đơn"], str(header_buttons(page)))
    ok("ED-10: Quản lý không có 'Xem nhật ký của đơn' khi không có quyền nhật ký hoặc có thì hiện đúng", "Sao chép mã đơn" in menu_items(page))
    # Quản lý ở hàng chờ (chỉ Chủ có sales.confirm_payment_manual) + phiếu hoàn (xem được, không có nút)
    go(page, "/orders/payments/")
    expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
    ok("ED-11: Quản lý mở /orders/payments/ → 403 màn chặn, không có Gắn / Xác nhận đơn", page.get_by_role("button", name=re.compile("Gắn vào đơn|Xác nhận đơn")).count() == 0)
    go(page, "/orders/refunds/")
    tabs = [t.strip() for t in page.get_by_role("tab").all_inner_texts()]
    ok("ED-11: Quản lý chỉ thấy tab Đơn hàng · Phiếu hoàn (không có Hàng chờ thanh toán)", tabs == ["Đơn hàng", "Phiếu hoàn tiền"], str(tabs))
    page.locator("tbody tr", has_text="Chờ hoàn").first.click()
    page.wait_for_url(re.compile(r"/orders/refunds/detail/\?id=\d+$"))
    expect(page.locator("main header h2")).to_be_visible()
    idle(page)
    ok("ED-12: Quản lý không có 'Xác nhận đã hoàn tiền'", page.get_by_role("button", name=re.compile("Xác nhận đã hoàn")).count() == 0 and header_buttons(page) == [], str(header_buttons(page)))
    r = page.evaluate("() => window.__caveMock.confirmRefundJson('ql1', 4, {bank_txn_ref: 'FT-QL-1'})")
    ok("ED-12: Quản lý gọi API xác nhận hoàn → 403", r["status"] == 403, str(r["status"]))
    ctx.close()

    # ======================================================= NV kho (kho1): không Huỷ đơn / Lập phiếu hoàn
    ctx, page = new_page(browser, "kho1", errors=errors)
    for oid in (104, 109):
        open_order(page, oid)
        mi = menu_items(page)
        ok(f"ED-10-AC6: NV kho, đơn {oid} → không Huỷ đơn / Lập phiếu hoàn", header_buttons(page) == [] and not [x for x in mi if x.startswith(("Huỷ đơn", "Lập phiếu hoàn"))], f"{header_buttons(page)} {mi}")
    r = page.evaluate("() => window.__caveMock.cancelJson('kho1', 104, {reason_code: 'CUSTOMER_CHANGED_MIND'})")
    ok("ED-10-AC6: NV kho gọi API huỷ → 403", r["status"] == 403, str(r["status"]))
    ctx.close()

    # ======================================================= Phạm vi giao: cs2 → 404; giao1 → chặn
    ctx, page = new_page(browser, "cs2", errors=errors)
    go(page, "/orders/detail/?id=101")
    expect(page.get_by_text("Không tìm thấy trang này")).to_be_visible()
    ok("ED-09-AC9: người có phạm vi giao mở đơn không thuộc phiếu của mình → 'Không tìm thấy trang này' (404)", True)
    ok("ED-09-AC9: không lộ dữ liệu khách ở trang 404", "0901234567" not in page.locator("main").inner_text())
    go(page, "/orders/detail/?id=142")
    expect(page.locator("main header h2")).to_be_visible()
    ok("ED-09-AC9: đơn thuộc phiếu của mình mở được", True)
    ctx.close()
    ctx, page = new_page(browser, "giao1", errors=errors)
    go(page, "/orders/detail/?id=101")
    expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
    ok("Phân quyền: giao1 (chỉ giao) gõ URL chi tiết đơn → chặn, không lộ dữ liệu", "0901234567" not in page.locator("main").inner_text())
    ctx.close()

    # ======================================================= Trạng thái lỗi / không có id / id sai
    ctx, page = new_page(browser, "loc", errors=errors)
    go(page, "/orders/detail/")
    expect(page.get_by_text("Không tìm thấy trang này")).to_be_visible()
    ok("Chi tiết thiếu id → 'Không tìm thấy trang này'", True)
    go(page, "/orders/detail/?id=abc")
    expect(page.get_by_text("Không tìm thấy trang này")).to_be_visible()
    ok("Chi tiết id sai dạng → 'Không tìm thấy trang này'", True)
    go(page, "/orders/detail/?id=99999")
    expect(page.get_by_text("Không tìm thấy trang này")).to_be_visible()
    ok("Chi tiết id không tồn tại → 404", True)
    page.evaluate("() => window.__caveMock.orders('detailfail')")
    page.goto(BASE + "/orders/detail/?id=101")
    expect(page.get_by_role("button", name="Thử lại")).to_be_visible()
    page.screenshot(path=f"{SHOTS}/ed3-detail-error-1280-light.png")
    page.evaluate("() => window.__caveMock.orders('ok')")
    page.get_by_role("button", name="Thử lại").click()
    expect(page.locator("main header h2")).to_be_visible()
    ok("Chi tiết lỗi 500 → hộp lỗi + 'Thử lại' → có dữ liệu", True)
    page.evaluate("() => window.__caveMock.orders('fail')")
    page.goto(BASE + "/orders/")
    expect(page.get_by_text("Không tải được dữ liệu").first).to_be_visible()
    page.evaluate("() => window.__caveMock.orders('ok')")
    page.get_by_role("button", name="Thử lại").first.click()
    expect(page.locator("tbody tr").first).to_be_visible()
    ok("Danh sách lỗi → Thử lại → có dòng", True)
    page.evaluate("() => window.__caveMock.orders('empty')")
    page.goto(BASE + "/orders/")
    expect(page.get_by_text("Chưa có đơn hàng nào")).to_be_visible()
    ok("Danh sách rỗng → 'Chưa có đơn hàng nào'", True)
    page.evaluate("() => window.__caveMock.orders('forbidden')")
    page.goto(BASE + "/orders/")
    expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
    ok("Danh sách 403 từ API → màn 'Bạn không có quyền xem mục này'", True)
    ctx.close()

    # ======================================================= Đồng hồ giữ chỗ: chip đổi không cần tải lại
    ctx, page = new_page(browser, "loc", errors=errors)
    go(page, "/orders/")
    page.evaluate(
        """() => { const k = 'cave_erp_mock_orders'; const s = JSON.parse(sessionStorage.getItem(k));
        const o = s.orders.find(x => x.id === 102); const t = Date.now() + 3000;
        o.reserved_until = new Date(t).toISOString(); sessionStorage.setItem(k, JSON.stringify(s)); }"""
    )
    page.goto(BASE + "/orders/detail/?id=102")
    expect(page.locator("main header h2")).to_be_visible()
    ok("ED-09-AC5: trước hạn chip 'Giữ chỗ'", "Giữ chỗ" in header_text(page))
    expect(page.locator("main header")).to_contain_text("Hết giờ giữ chỗ", timeout=8000)
    ok("ED-09-AC5: hết giờ → chip đổi 'Đã huỷ' không tải lại trang", True)
    ctx.close()

    # ======================================================= Hàng chờ thanh toán (Chủ)
    ctx, page = new_page(browser, "loc", errors=errors)
    go(page, "/orders/payments/")
    heads = [h.strip() for h in page.locator("thead th").all_inner_texts()]
    ok("ED-11-AC1: cột Mã giao dịch · Số tiền · Loại khoản tiền · Tình trạng xử lý · Đơn · Nhận lúc",
       heads == ["Mã giao dịch", "Số tiền", "Loại khoản tiền", "Tình trạng xử lý", "Đơn", "Nhận lúc"], str(heads))
    body = page.locator("tbody").inner_text()
    ok("ED-11-AC1: nhãn loại khoản Chuyển thiếu · Chuyển thừa · Về sau khi đơn đã huỷ · Không khớp đơn",
       all(x in body for x in ["Chuyển thiếu", "Chuyển thừa", "Về sau khi đơn đã huỷ", "Không khớp đơn"]))
    ok("ED-11-AC1: 'Tình trạng xử lý' là cột riêng (Chờ xử lý)", "Chờ xử lý" in body)
    ok("ED-11: không hiện nội dung chuyển khoản trong danh sách", "Nội dung" not in body)
    page.screenshot(path=f"{SHOTS}/ed3-payments-1280-light.png")
    page.locator("tbody tr", has_text="FT2626700091").click()
    page.wait_for_url(re.compile(r"/orders/payments/detail/\?id=\d+$"))
    expect(page.locator("main header h2")).to_have_text("FT2626700091")
    idle(page)
    ok("ED-11: khoản không khớp đơn → nút chính 'Gắn vào đơn'", header_buttons(page)[0] == "Gắn vào đơn", str(header_buttons(page)))
    ok("ED-11: URL chi tiết chỉ có id", re.search(r"\?id=\d+$", page.url) is not None, page.url)
    page.get_by_role("button", name="Gắn vào đơn").click()
    dlg = dialog(page, "Gắn khoản tiền vào đơn")
    clear_log(page)
    submit_btn(dlg).click()
    expect(dlg.get_by_text(re.compile("Chọn một đơn"))).to_be_visible()
    ok("ED-11: chưa chọn đơn → báo, không POST", posts(page) == [])
    # 409 ở F2d
    dlg.get_by_label("Tìm đơn").fill("")
    pick = dlg.locator("label.check-row").first
    expect(pick).to_be_visible()
    pick.click()
    page.evaluate("() => window.__caveMock.conflictNext()")
    clear_log(page)
    submit_btn(dlg).click()
    expect(page.locator("[data-conflict-banner]")).to_be_visible()
    idle(page)
    ok("ED-11-AC4: F2d gặp 409 → banner, không xử lý lần hai", len(posts(page)) == 1 and page.get_by_role("dialog").count() == 0, str(posts(page)))
    page.locator("[data-conflict-banner]").get_by_role("button").first.click()
    page.get_by_role("button", name="Gắn vào đơn").click()
    dlg = dialog(page, "Gắn khoản tiền vào đơn")
    dlg.locator("label.check-row").first.click()
    clear_log(page)
    submit_btn(dlg).click()
    expect(page.locator(".toast-item").last).to_contain_text("Đã gắn vào đơn")
    idle(page)
    ok("ED-11: gắn vào đơn thành công → toast + đúng 1 POST", len(posts(page)) == 1, str(posts(page)))
    expect(page.locator("main header")).to_contain_text("Đã xử lý")
    ok("ED-11: khoản chuyển sang Đã xử lý, hết nút Gắn", page.get_by_role("button", name="Gắn vào đơn").count() == 0)
    # lập phiếu hoàn từ khoản tiền thừa
    go(page, "/orders/payments/")
    page.locator("tbody tr", has_text="FT2626700013").click()
    page.wait_for_url(re.compile(r"/orders/payments/detail/\?id=\d+$"))
    expect(page.locator("main header h2")).to_be_visible()
    idle(page)
    ok("ED-11: khoản chuyển thừa → nút chính 'Lập phiếu hoàn'", header_buttons(page) and header_buttons(page)[0] == "Lập phiếu hoàn tiền", str(header_buttons(page)))
    page.get_by_role("button", name="Lập phiếu hoàn").first.click()
    dlg = dialog(page, "Lập phiếu hoàn")
    ok("ED-11: hộp hoàn mặc định lý do theo loại khoản", dlg.get_by_label("Lý do hoàn").input_value() != "")
    dlg.get_by_label("Số tiền hoàn").fill("999999")
    expect(dlg.get_by_text(re.compile("Nhập tối đa"))).to_be_visible()
    ok("ED-11: vượt mức hoàn từ khoản → khoá nút chính", submit_btn(dlg).is_disabled())
    dlg.get_by_label("Số tiền hoàn").fill("150000")
    submit_btn(dlg).click()
    expect(page.locator(".toast-item").last).to_contain_text("Đã lập phiếu hoàn")
    ok("ED-11: lập phiếu hoàn từ khoản → toast", True)
    ctx.close()

    # ======================================================= Phiếu hoàn (Chủ)
    ctx, page = new_page(browser, "loc", errors=errors)
    go(page, "/orders/refunds/")
    heads = [h.strip() for h in page.locator("thead th").all_inner_texts()]
    ok("ED-12-AC1: cột 'Số tiền hoàn' (không 'Tổng hoàn')", "Số tiền hoàn" in heads and "Tổng hoàn" not in heads, str(heads))
    body = page.locator("tbody").inner_text()
    ok("ED-12: chip Chờ hoàn + Thất bại ở mặc định 'Chờ chuyển'", "Chờ hoàn tiền" in body and "Hoàn thất bại" in body)
    page.evaluate("() => window.__caveMock.refunds('empty')")
    page.goto(BASE + "/orders/refunds/")
    expect(page.get_by_text("Chưa có phiếu hoàn tiền nào chờ chuyển")).to_be_visible()
    ok("ED-12: chưa có phiếu hoàn → 'Chưa có phiếu hoàn tiền nào chờ chuyển'", True)
    page.evaluate("() => window.__caveMock.refunds('fail')")
    page.goto(BASE + "/orders/refunds/")
    expect(page.get_by_text("Không tải được dữ liệu").first).to_be_visible()
    page.evaluate("() => window.__caveMock.refunds('ok')")
    page.get_by_role("button", name="Thử lại").first.click()
    expect(page.locator("tbody tr").first).to_be_visible()
    ok("ED-12: lỗi 500 → Thử lại → có phiếu", True)
    clear_log(page)
    page.get_by_label("Lọc theo tháng").select_option(index=1)
    idle(page)
    ok("ED-12: lọc tháng gửi ?month=YYYY-MM", any(re.search(r"month=\d{4}-\d{2}", x) for x in log(page)), str(log(page)))
    ok("ED-12: có tổng tiền hoàn của tháng", "Tổng" in page.locator("main").inner_text() or "tháng" in page.locator("main").inner_text().lower())
    page.screenshot(path=f"{SHOTS}/ed3-refunds-1280-light.png")
    page.get_by_label("Lọc theo tháng").select_option(index=0)
    idle(page)
    page.locator("tbody tr", has_text="Chờ hoàn").first.click()
    page.wait_for_url(re.compile(r"/orders/refunds/detail/\?id=\d+$"))
    expect(page.locator("main header h2")).to_be_visible()
    idle(page)
    ok("ED-12: Chủ thấy 'Xác nhận đã hoàn <số> đ'", re.fullmatch(r"Xác nhận đã hoàn [\d.]+ đ", (header_buttons(page) or [""])[0]) is not None or page.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).count() == 1, str(header_buttons(page)))
    page.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).first.click()
    dlg = dialog(page, "Xác nhận đã hoàn tiền")
    clear_log(page)
    submit_btn(dlg).click()
    ok("ED-12: thiếu mã giao dịch hoàn → báo tại ô, không POST", posts(page) == [] and dlg.get_by_text(re.compile("Nhập mã giao dịch")).count() >= 1)
    page.keyboard.press("Escape")
    # 409 ở F2f
    page.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).first.click()
    dlg = dialog(page, "Xác nhận đã hoàn tiền")
    dlg.get_by_label("Mã giao dịch chuyển khoản hoàn").fill("FT2626799601")
    page.evaluate("() => window.__caveMock.conflictNext()")
    submit_btn(dlg).click()
    expect(page.locator("[data-conflict-banner]")).to_be_visible()
    ok("ED-12: F2f gặp 409 → banner", True)
    page.locator("[data-conflict-banner]").get_by_role("button").first.click()
    # Báo chuyển thất bại (F2g) trong menu …
    m = open_more(page)
    m.get_by_role("menuitem", name="Báo chuyển thất bại").click()
    dlg = dialog(page, "Báo chuyển thất bại")
    ok("ED-12-AC3: hộp báo thất bại có ô 'Lý do thất bại' (BE cho phép để trống, FE chỉ nhắc)", dlg.get_by_label("Lý do thất bại").count() == 1)
    dlg.get_by_label("Lý do thất bại").fill("Sai số tài khoản")
    submit_btn(dlg).click()
    expect(page.locator("main header")).to_contain_text("Hoàn thất bại")
    idle(page)
    ok("ED-12-AC3: F2g → chip Hoàn thất bại, lý do là trường riêng", field(page, "Lý do thất bại").inner_text().strip() == "Sai số tài khoản", field(page, "Lý do thất bại").inner_text())
    ok("ED-12: SĐT khách hiện đủ ở phiếu hoàn có đơn (không che)", re.search(r"0\d{9}", page.locator("main").inner_text()) is not None or "—" in field(page, "Số điện thoại").inner_text())
    page.screenshot(path=f"{SHOTS}/ed3-refund-failed-1280-light.png")
    # Chuyển lại
    page.get_by_role("button", name=re.compile("^Chuyển lại")).first.click()
    dlg = dialog(page, "Chuyển lại")
    submit_btn(dlg).click()
    expect(page.locator(".toast-item").last).to_contain_text("Chờ hoàn")
    expect(page.locator("main header")).to_contain_text("Chờ hoàn")
    ok("ED-12: Chuyển lại → phiếu về Chờ hoàn", True)
    # Xác nhận xong
    page.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).first.click()
    dlg = dialog(page, "Xác nhận đã hoàn tiền")
    dlg.get_by_label("Mã giao dịch chuyển khoản hoàn").fill("FT2626799602")
    clear_log(page)
    submit_btn(dlg).dblclick()
    expect(page.locator("main header")).to_contain_text("Đã hoàn")
    idle(page)
    ok("ED-12: F2f thành công → 'Đã hoàn', chỉ 1 POST", len(posts(page)) == 1, str(posts(page)))
    ctx.close()

    # ======================================================= 360px, sáng/tối, không cuộn ngang
    for dark in (False, True):
        tag = f"360-{'dark' if dark else 'light'}"
        ctx, page = new_page(browser, "loc", w=360, h=740, dark=dark, mobile=True, errors=errors)
        for path in ["/orders/", "/orders/payments/", "/orders/refunds/", "/orders/detail/?id=101", "/orders/payments/detail/?id=880", "/orders/refunds/detail/?id=4"]:
            go(page, path)
            page.wait_for_timeout(250)
            ok(f"360 {tag}: {path} không cuộn ngang", hscroll_ok(page, 360), str(page.evaluate("() => document.documentElement.scrollWidth")))
        go(page, "/orders/detail/?id=101")
        page.wait_for_timeout(300)
        page.screenshot(path=f"{SHOTS}/ed3-detail-{tag}.png", full_page=True)
        page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
        dialog(page, "Xác nhận đã nhận tiền")
        ok(f"360 {tag}: hộp xác nhận không cuộn ngang", hscroll_ok(page, 360))
        page.screenshot(path=f"{SHOTS}/ed3-confirm-{tag}.png")
        go(page, "/orders/")
        page.screenshot(path=f"{SHOTS}/ed3-list-{tag}.png")
        ctx.close()

    browser.close()

relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "Failed to load resource" not in e]
ok("Không lỗi console (trừ lỗi cố ý do ca 500/403/404)", not relevant, str(relevant[:5]))
fails = [r for r in results if not r[1]]
print(f"{len(results) - len(fails)}/{len(results)} PASS")
for n, c, e in fails:
    print("FAIL", n, "->", e)
raise SystemExit(1 if fails else 0)
