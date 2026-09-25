# E2E S10 (danh sách + chi tiết đơn) và S11 (Chủ xác nhận đã nhận tiền): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s10_s11_orders.py      # tắt server sau khi xong
#
# Mock theo contract THỰC TẾ BE L7 (features/orders/mock.ts). Đơn mẫu (gieo lại mỗi context mới, sessionStorage):
#   101 Chị Hoa 0901234567 · Giữ chỗ 540.000 ₫ · 102 Giữ chỗ còn ~3′ · 103 Tự huỷ · 106 Giữ chỗ đã chuyển thiếu (webhook FT2626700002)
# Ổn định: KHÔNG ngủ — chờ URL, phần tử, `aria-busy`, `__caveMock.pending() === 0`. Context bật reduced_motion.
# Câu lỗi BE lấy qua window.__caveMock.beDetail (không gõ lại chuỗi).

import os
import re
import datetime

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []
expect.set_options(timeout=10_000)
LIST = "GET /api/sales/orders/"


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()


def log(page):
    return page.evaluate("() => window.__caveMock.log.slice()")


def clear_log(page):
    page.evaluate("() => window.__caveMock.clearLog()")


def idle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0")


def list_ready(page):
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    expect(page.locator("section[aria-busy=true]")).to_have_count(0)
    idle(page)


def rows(page):
    return page.locator("ul.order-list > li")


def open_order(page, oid):
    page.locator(f'.order-open[data-id="{oid}"]').click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    expect(dlg.locator("header")).to_be_visible()  # chi tiết đã tải
    idle(page)
    return dlg


def close_sheet(page):
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)


def be(page, key, params=None):
    return page.evaluate("([k, p]) => window.__caveMock.beDetail(k, p || undefined)", [key, params])


def nav_labels(page):
    return [t.split("\n")[-1].strip() for t in page.locator(".nav a").all_inner_texts()]


def fonts_ready(page):
    page.wait_for_function("() => document.fonts.status === 'loaded'")


def hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth")


SMALL_TAPS_JS = """(w) => [...document.querySelectorAll('button, a, input, select')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < w && r.y < innerHeight && r.bottom > 0
      && !e.closest('.sr-only') && (r.height < 44 || (e.tagName !== 'INPUT' && e.tagName !== 'SELECT' && r.width < 44));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""


def vn_today():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime("%Y-%m-%d")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []

    def new_page(width=1280, height=800, dark=False, mobile=False):
        kw = dict(viewport={"width": width, "height": height}, reduced_motion="reduce", color_scheme="dark" if dark else "light")
        if mobile:
            kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
        ctx = browser.new_context(**kw)
        pg = ctx.new_page()
        pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
        return ctx, pg

    # ================= Chủ (loc) — 1280 =================
    ctx, page = new_page()
    login(page, "loc")
    page.wait_for_url("**/overview/")
    ok("Menu Chủ có 'Đơn & tiền'", "Đơn & tiền" in nav_labels(page), str(nav_labels(page)))
    clear_log(page)
    page.locator(".nav a", has_text="Đơn & tiền").click()
    page.wait_for_url("**/orders/")
    list_ready(page)
    lg = log(page)
    ok("S10: màn Đơn gọi GET /api/sales/orders/ (không còn đọc /api/dashboard/summary/)",
       lg == [LIST] or lg == ["GET /api/auth/me/", LIST], str(lg))
    ok("S10-AC1: 20 dòng/trang", rows(page).count() == 20, str(rows(page).count()))
    expect(page.locator("#orders-h + .sub")).to_have_text("Đang hiện 20 / 45 đơn")
    ok("S10: đầu khối ghi 'Đang hiện 20 / 45 đơn'", True)
    fonts_ready(page)
    page.screenshot(path=f"{SHOTS}/s10-list-1280-light.png")

    # Tải thêm (phân trang DRF ?page=)
    clear_log(page)
    page.get_by_role("button", name="Tải thêm đơn").click()
    expect(rows(page)).to_have_count(40)
    idle(page)
    ok("S10: Tải thêm gọi ?page=2 và nối thêm 20 dòng", log(page) == [LIST + "?page=2"], str(log(page)))
    page.get_by_role("button", name="Tải thêm đơn").click()
    expect(rows(page)).to_have_count(45)
    ok("S10: hết trang → không còn nút Tải thêm", page.get_by_role("button", name="Tải thêm đơn").count() == 0)
    ids = page.eval_on_selector_all(".order-open", "b => b.map(x => x.dataset.id)")
    ok("S10: không trùng dòng khi nối trang", len(ids) == len(set(ids)), str(len(ids)))

    # Lọc trạng thái (S10-AC1)
    clear_log(page)
    page.get_by_label("Trạng thái").select_option(label="Giữ chỗ")
    expect(page.locator("#orders-h + .sub")).to_have_text("3 đơn")
    idle(page)
    ok("S10-AC1: lọc Giữ chỗ gửi ?status=BOOKED", log(page)[-1] == LIST + "?status=BOOKED", str(log(page)))
    labels = page.eval_on_selector_all("ul.order-list .status", "s => s.map(x => x.textContent.trim())")
    ok("S10-AC1: chỉ còn đơn Giữ chỗ", labels and all(l == "Giữ chỗ" for l in labels), str(labels))
    ok("S10-AC5 (danh sách): đơn Giữ chỗ có 'còn N′'", all("còn" in t for t in page.locator("ul.order-list > li").all_inner_texts()))
    # + ngày hôm nay
    clear_log(page)
    page.get_by_label("Ngày đặt").select_option(label="Hôm nay")
    idle(page)
    today = vn_today()
    ok("S10-AC1: lọc 'Hôm nay' gửi date_from/date_to = ngày VN hôm nay",
       log(page)[-1] == f"{LIST}?status=BOOKED&date_from={today}&date_to={today}", str(log(page)))
    # Khoảng ngày sai → báo tại ô, không gọi API
    page.get_by_label("Ngày đặt").select_option(label="Chọn khoảng ngày")
    idle(page)
    page.get_by_label("Từ ngày").fill("2026-09-24")  # mới có "Từ ngày" → lọc hợp lệ, được gọi API
    idle(page)
    clear_log(page)
    page.get_by_label("Đến ngày").fill("2026-09-20")
    expect(page.get_by_text("Ngày bắt đầu đang sau ngày kết thúc")).to_be_visible()
    idle(page)
    ok("Khoảng ngày ngược → báo tại ô, không gọi API", log(page) == [], str(log(page)))
    page.get_by_label("Ngày đặt").select_option(label="Mọi ngày")
    page.get_by_label("Trạng thái").select_option(label="Mọi trạng thái")
    list_ready(page)

    # Tìm theo SĐT (S10-AC2) — BE lọc, khớp một phần
    clear_log(page)
    page.get_by_placeholder("Tìm mã đơn, tên khách hoặc SĐT…").fill("0901234")
    expect(rows(page)).to_have_count(1)
    idle(page)
    ok("S10-AC2: q=0901234 → có đơn của Chị Hoa", "Chị Hoa" in rows(page).first.inner_text() and (LIST + "?q=0901234") in log(page), str(log(page)))
    # L7 bổ sung (BE): q khớp cả tên khách, bỏ dấu
    clear_log(page)
    page.get_by_placeholder("Tìm mã đơn, tên khách hoặc SĐT…").fill("chi hoa")
    page.wait_for_function("() => window.__caveMock.log.some(x => x.includes('q=chi'))")  # chờ hết trễ 300 ms của ô tìm
    idle(page)
    expect(rows(page)).to_have_count(1)
    ok("L7 bổ sung: tìm tên không dấu 'chi hoa' → đơn của Chị Hoa (BE lọc, q=chi hoa)",
       rows(page).count() == 1 and any(x.startswith(LIST + "?q=chi") for x in log(page)), str(log(page)))
    page.get_by_placeholder("Tìm mã đơn, tên khách hoặc SĐT…").fill("zzz-khong-co")
    expect(page.get_by_text("Không có đơn khớp bộ lọc")).to_be_visible()
    page.get_by_role("button", name="Bỏ lọc").click()
    expect(rows(page)).to_have_count(20)
    ok("Bỏ lọc → về 20 dòng đầu, ô tìm trống", page.get_by_placeholder("Tìm mã đơn, tên khách hoặc SĐT…").input_value() == "")
    list_ready(page)

    # Chi tiết đơn 101 (Chủ): đếm lùi mm:ss, giá vốn có, nút xác nhận có
    dlg = open_order(page, 101)
    t1 = dlg.locator(".hold-countdown [role=timer]").inner_text()
    ok("S10-AC5: đếm lùi giữ chỗ dạng mm:ss", re.fullmatch(r"\d{2}:\d{2}", t1) is not None, t1)
    page.wait_for_function("t => document.querySelector('.hold-countdown [role=timer]').textContent !== t", arg=t1)
    ok("S10-AC5: đồng hồ chạy (giây đổi)", True)
    ok("S10: chi tiết có SĐT là link tel:", dlg.locator('a[href="tel:0901234567"]').count() == 1)
    parts = [re.sub(r"\s*\d+$", "", t.strip()) for t in dlg.locator("section > h3").all_inner_texts()]
    ok("S10: có Hàng / Phân bổ lô / Thanh toán / Giao hàng / Hoàn tiền / Dòng thời gian",
       parts == ["Hàng", "Phân bổ lô", "Thanh toán", "Giao hàng", "Hoàn tiền", "Dòng thời gian"], str(parts))
    j = page.evaluate("() => window.__caveMock.orderJson('loc', 101)")
    ok("S10-AC4 (mock theo BE): Chủ có key unit_cost", all("unit_cost" in a for a in j["allocations"]) and j["allocations"], str(j["allocations"]))
    ok("S10-AC4: Chủ thấy 'Vốn …/kg' ở phân bổ lô", dlg.locator(".alloc-cost").count() == len(j["allocations"]))
    ok("S11: đơn Giữ chỗ + Chủ → available_actions có confirm_payment, nút hiện",
       "confirm_payment" in j["available_actions"] and dlg.get_by_role("button", name="Xác nhận đã nhận tiền").is_visible())
    fonts_ready(page)
    page.screenshot(path=f"{SHOTS}/s10-detail-1280-light.png")

    # S11: xác nhận — bước hậu quả, kiểm ô trống, chống bấm đúp
    dlg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    form = dlg.locator("form.confirm-payment")
    expect(form).to_be_visible()
    q_text = form.locator("h3").inner_text()
    ok("S11: câu hỏi xác nhận nêu số tiền + mã đơn", "540.000 ₫" in q_text and j["code"] in q_text, q_text)
    ok("S11: focus vào ô mã giao dịch", page.evaluate("() => document.activeElement && document.activeElement.name === 'bank_txn_id'"))
    ok("S11: số tiền mặc định = tổng đơn", form.get_by_label("Số tiền đã nhận").input_value() == "540000")
    ok("S11: nêu hậu quả (Đang xử lý, trừ kho, phiếu giao; không hoàn tác)",
       "Đang xử lý" in form.inner_text() and "Không hoàn tác" in form.inner_text())
    page.screenshot(path=f"{SHOTS}/s11-confirm-1280-light.png")
    clear_log(page)
    form.get_by_role("button", name="Xác nhận đã nhận 540.000 ₫").click()
    expect(form.get_by_text("Nhập mã giao dịch ngân hàng để đối chiếu sau này.")).to_be_visible()
    ok("S11: mã GD trống → báo tại ô, KHÔNG gọi API", log(page) == [] and form.get_by_label("Mã giao dịch ngân hàng").get_attribute("aria-invalid") == "true", str(log(page)))
    form.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799001")
    btn = form.get_by_role("button", name="Xác nhận đã nhận 540.000 ₫")
    btn.dblclick()
    expect(dlg.locator(".confirm-result")).to_be_visible()
    idle(page)
    posts = [x for x in log(page) if x.startswith("POST")]
    ok("S11-AC4: bấm đúp → chỉ 1 POST confirm-payment", posts == ["POST /api/sales/orders/101/confirm-payment/"], str(posts))
    res = dlg.locator(".confirm-result").inner_text()
    ok("S11-AC1: báo PAID ngay trong chi tiết (mã đơn + phiếu giao)", "Đã xác nhận nhận tiền đơn" in res and "GH-" in res, res)
    expect(dlg.locator("header .status")).to_have_text("Đang xử lý")
    ok("S11-AC1: chi tiết tải lại → Đang xử lý, có hoá đơn, phiếu giao Soạn hàng, giao dịch Xác nhận tay",
       "INV" in dlg.inner_text() and "Soạn hàng" in dlg.inner_text() and "Xác nhận tay" in dlg.inner_text())
    ok("S11: đơn đã xử lý → không còn nút xác nhận", dlg.get_by_role("button", name="Xác nhận đã nhận tiền").count() == 0)
    kinds = dlg.locator(".order-timeline li[data-kind]").evaluate_all("l => l.map(x => x.dataset.kind)")
    ok("L7 bổ sung: timeline của BE theo kind (đặt → tiền → hoá đơn → phiếu giao)",
       kinds == ["order_placed", "payment_received", "invoice_issued", "delivery_created"], str(kinds))
    actors = dlg.locator(".order-timeline .tl-actor").all_inner_texts()
    ok("L7 bổ sung: actor_display — xác nhận tay = người bấm (Lộc), còn lại 'Hệ thống'",
       [a.replace("·", "").strip() for a in actors] == ["Hệ thống", "Lộc", "Hệ thống", "Hệ thống"], str(actors))
    ok("L7 bổ sung: có timeline BE → không còn chú thích 'Ghép tạm'", "Ghép tạm" not in dlg.inner_text())
    page.screenshot(path=f"{SHOTS}/s11-result-1280-light.png")
    close_sheet(page)
    expect(page.locator(".alert-box.ok")).to_contain_text("Đã xác nhận nhận tiền đơn")
    ok("S11: đóng tấm → thông báo nổi (toast)", True)
    ok("S11: dòng trong danh sách cập nhật Đang xử lý", "Đang xử lý" in page.locator('.order-open[data-id="101"]').inner_text())

    # S11-AC5: webhook đã ghi FT2626700002 cho đơn 106 → xác nhận tay cùng mã = duplicate
    dlg = open_order(page, 106)
    dlg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626700002")
    clear_log(page)
    dlg.locator("form.confirm-payment button[type=submit]").click()
    expect(dlg.locator(".confirm-result")).to_be_visible()
    res = dlg.locator(".confirm-result").inner_text()
    ok("S11-AC5: trùng mã GD (webhook ghi trước) → báo 'đã được ghi trước đó', không xử lý lần hai",
       "đã được ghi trước đó" in res and "còn thiếu" in res, res)
    idle(page)
    ok("S11-AC5: đơn vẫn Giữ chỗ, vẫn 1 giao dịch", dlg.locator("header .status").inner_text() == "Giữ chỗ"
       and dlg.locator("code", has_text="FT2626700002").count() == 1)  # timeline cũng nhắc mã GD → đếm ở danh sách thanh toán
    close_sheet(page)

    # BR-TT-03: mã đã ghi cho đơn KHÁC → lỗi BE nguyên văn; amount 0 → lỗi BE nguyên văn
    dlg = open_order(page, 102)
    dlg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626700002")
    dlg.locator("form.confirm-payment button[type=submit]").click()
    expect(dlg.locator(".confirm-error > span")).to_have_text(be(page, "TT_TXN_OTHER"))
    ok("BR-TT-03: mã GD của đơn khác → hiện nguyên văn detail BE, ở lại form", dlg.locator("form.confirm-payment").is_visible())
    page.screenshot(path=f"{SHOTS}/s11-error-1280-light.png")
    # B13 (QA L7): ô mã GD tối đa 100 ký tự, gợi ý "Mã FT… trên sao kê", giữ chữ hướng dẫn, tự trim
    txn_in = dlg.get_by_label("Mã giao dịch ngân hàng")
    ok("B13: ô mã GD maxlength=100 + placeholder 'Mã FT… trên sao kê'",
       txn_in.get_attribute("maxlength") == "100" and txn_in.get_attribute("placeholder") == "Mã FT… trên sao kê",
       f'{txn_in.get_attribute("maxlength")} {txn_in.get_attribute("placeholder")}')
    ok("B13: vẫn giữ chữ hướng dẫn mã GD", "Chép từ tin nhắn hoặc sao kê ngân hàng" in dlg.locator("form.confirm-payment").inner_text())
    txn_in.fill("X" * 150)
    ok("B13: gõ/dán 150 ký tự → ô chỉ giữ 100", len(txn_in.input_value()) == 100, str(len(txn_in.input_value())))
    txn_in.fill("  FT2626799002  ")
    dlg.get_by_label("Số tiền đã nhận").focus()
    ok("B13: rời ô mã GD → tự trim", txn_in.input_value() == "FT2626799002", repr(txn_in.input_value()))
    # B13: số tiền ngoài miền → báo tại ô, focus về ô, KHÔNG gửi POST
    amt_in = dlg.get_by_label("Số tiền đã nhận")
    bad = [
        ("123456789012345", "Số tiền quá lớn: tối đa 12 chữ số (999.999.999.999 ₫). Đối chiếu lại số trên sao kê."),
        ("99999999999999", "Số tiền quá lớn: tối đa 12 chữ số (999.999.999.999 ₫). Đối chiếu lại số trên sao kê."),
        ("1e20", "Chỉ nhập chữ số, vd 540000 hoặc 540.000."),
        ("0", "Số tiền phải từ 1 ₫ trở lên (tiền VND không có số lẻ). Nhập đúng số khách đã chuyển."),
        ("0,004", "Số tiền phải từ 1 ₫ trở lên (tiền VND không có số lẻ). Nhập đúng số khách đã chuyển."),
        ("0.001", "Số tiền phải từ 1 ₫ trở lên (tiền VND không có số lẻ). Nhập đúng số khách đã chuyển."),
        ("-5", "Số tiền không được âm. Nhập đúng số khách đã chuyển, vd 540000."),
        ("-540000", "Số tiền không được âm. Nhập đúng số khách đã chuyển, vd 540000."),
    ]
    for raw, msg in bad:
        amt_in.fill(raw)
        clear_log(page)
        dlg.locator("form.confirm-payment button[type=submit]").click()
        err = dlg.locator("form.confirm-payment .field-err")
        expect(err).to_contain_text(msg)
        idle(page)
        ok(f"B13: số tiền {raw!r} → báo tại ô, aria-invalid, focus ô, bỏ câu BE cũ, KHÔNG POST",
           log(page) == [] and amt_in.get_attribute("aria-invalid") == "true"
           and page.evaluate("() => document.activeElement && document.activeElement.name === 'amount'")
           and amt_in.input_value() == raw and dlg.locator(".confirm-error").count() == 0,
           f"{log(page)} {amt_in.input_value()!r} {amt_in.get_attribute('aria-invalid')} "
           f"{page.evaluate('() => document.activeElement && document.activeElement.name')} {dlg.locator('.confirm-error').count()}")
        if raw == "123456789012345":
            page.screenshot(path=f"{SHOTS}/s11-amount-toobig-1280-light.png")
    amt_in.fill("5")
    ok("B13: sửa ô → lỗi tại ô biến mất", dlg.locator("form.confirm-payment .field-err").count() == 0
       and amt_in.get_attribute("aria-invalid") is None)
    amt_in.fill("999.999.999.999")
    ok("B13: đúng 12 chữ số (999.999.999.999) hợp lệ, đọc lại + nút ghi số",
       amt_in.input_value() == "999999999999"
       and dlg.get_by_role("button", name="Xác nhận đã nhận 999.999.999.999 ₫").count() == 1, amt_in.input_value())
    amt_in.fill("100000,5")
    ok("B13: phần lẻ dưới 1 ₫ bị bỏ ('100000,5' → 100000)", amt_in.input_value() == "100000", amt_in.input_value())
    before = len(page.evaluate("() => window.__caveMock.orderJson('loc', 102)")["payments"])
    api_bad = [page.evaluate("([a]) => window.__caveMock.confirmJson('loc', 102, {bank_txn_id: 'FT-B13-' + a, amount: a})", [a])
               for a in ["0.004", "0.001", "123456789012345", "1e20", "-5", "0"]]
    after = len(page.evaluate("() => window.__caveMock.orderJson('loc', 102)")["payments"])
    ok("B13 mock theo BE: amount 0.004/0.001/15 chữ số/1e20/-5/0 gọi thẳng → 400 BR-TT-08, không ghi giao dịch",
       all(r["status"] == 400 and r["body"]["code"] == "BR-TT-08" for r in api_bad) and before == after,
       str([r["status"] for r in api_bad]) + f" {before}->{after}")
    # S11-AC2: thiếu tiền
    dlg.get_by_label("Số tiền đã nhận").fill("100.000")
    ok("S11: ô số tiền chỉ giữ chữ số", dlg.get_by_label("Số tiền đã nhận").input_value() == "100000")
    ok("S11: báo 'Ít hơn tổng đơn' khi sửa số tiền", "Ít hơn tổng đơn" in dlg.locator("form.confirm-payment").inner_text())
    dlg.locator("form.confirm-payment button[type=submit]").click()
    expect(dlg.locator(".confirm-result")).to_contain_text("còn thiếu")
    idle(page)
    ok("S11-AC2: UNDERPAID → đơn vẫn Giữ chỗ, giao dịch 'Thiếu tiền'",
       dlg.locator("header .status").inner_text() == "Giữ chỗ" and "Thiếu tiền" in dlg.inner_text())
    close_sheet(page)
    ok("S11-AC2: UNDERPAID không bật toast", page.locator(".alert-box.ok").count() == 0)

    # S11-AC3: đơn đã tự huỷ → ORPHAN, không khôi phục
    dlg = open_order(page, 103)
    ok("S11: đơn Tự huỷ vẫn có nút theo available_actions", dlg.get_by_role("button", name="Xác nhận đã nhận tiền").is_visible())
    dlg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    ok("S11: đơn Tự huỷ nêu hậu quả 'KHÔNG khôi phục đơn'", "KHÔNG khôi phục" in dlg.inner_text())
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799003")
    dlg.locator("form.confirm-payment button[type=submit]").click()
    expect(dlg.locator(".confirm-result")).to_contain_text("Đơn đã tự huỷ nên không khôi phục")
    idle(page)
    ok("S11-AC3: ORPHAN → đơn vẫn Tự huỷ, giao dịch 'Đến sau khi đơn đã huỷ'",
       dlg.locator("header .status").inner_text().startswith("Tự huỷ") and "Đến sau khi đơn đã huỷ" in dlg.inner_text())
    close_sheet(page)

    # L7 bổ sung: nhãn BE (*_label) + timeline có giao thất bại, người giao
    j108 = page.evaluate("() => window.__caveMock.orderJson('loc', 108)")
    ok("L7 bổ sung (mock theo BE): có match_status_label, source_label, delivery.status_label",
       j108["payments"][0].get("match_status_label") == "Khớp — đã xác nhận" and j108["payments"][0].get("source_label") == "Webhook SePay"
       and j108["delivery"].get("status_label") == "Giao thất bại", str(j108["payments"][0]))
    dlg = open_order(page, 108)
    ok("L7 bổ sung: hiện nhãn BE 'Webhook SePay' ở thanh toán", "Webhook SePay" in dlg.inner_text())
    failed = dlg.locator('.order-timeline li[data-kind="delivery_failed"]')
    ok("L7 bổ sung: timeline có 'Giao thất bại' kèm người giao (Anh Phúc)",
       failed.count() == 1 and "Anh Phúc" in failed.inner_text(), failed.inner_text() if failed.count() else "")
    close_sheet(page)

    # Trạng thái lỗi / rỗng / 403 / lỗi chi tiết
    page.evaluate("() => window.__caveMock.orders('fail')")
    page.reload()
    expect(page.get_by_text("Không tải được dữ liệu, thử lại")).to_be_visible()
    page.screenshot(path=f"{SHOTS}/s10-state-fail-1280-light.png")
    page.evaluate("() => window.__caveMock.orders('ok')")
    page.get_by_role("button", name="Thử lại").click()
    list_ready(page)
    ok("Lỗi 500 → Thử lại → có danh sách", rows(page).count() == 20)
    page.evaluate("() => window.__caveMock.orders('empty')")
    page.reload()
    expect(page.get_by_text("Chưa có đơn nào")).to_be_visible()
    ok("Rỗng: 'Chưa có đơn nào' + nút làm mới", page.get_by_role("button", name="Làm mới danh sách").is_visible())
    page.screenshot(path=f"{SHOTS}/s10-state-empty-1280-light.png")
    page.evaluate("() => window.__caveMock.orders('forbidden')")
    page.reload()
    expect(page.locator(".state-err .mi", has_text="lock")).to_be_visible()
    ok("403 từ API → hộp lỗi icon khoá + câu BE", page.get_by_text(be(page, "DRF_FORBIDDEN")).is_visible())
    page.evaluate("() => window.__caveMock.orders('detailfail')")
    page.reload()
    list_ready(page)
    page.locator('.order-open[data-id="104"]').click()
    expect(page.get_by_role("dialog").get_by_role("button", name="Thử lại")).to_be_visible()
    ok("Chi tiết lỗi 500 → hộp lỗi trong tấm + Thử lại", True)
    page.evaluate("() => window.__caveMock.orders('ok')")
    page.get_by_role("dialog").get_by_role("button", name="Thử lại").click()
    expect(page.get_by_role("dialog").locator("header")).to_be_visible()
    ok("Chi tiết: Thử lại → có dữ liệu", True)
    close_sheet(page)
    ctx.close()

    # ================= Quản lý (ql1) — không giá vốn, không nút xác nhận =================
    ctx, page = new_page()
    login(page, "ql1")
    page.wait_for_url("**/overview/")
    page.goto(BASE + "/orders/")
    list_ready(page)
    dlg = open_order(page, 101)
    j = page.evaluate("() => window.__caveMock.orderJson('ql1', 101)")
    ok("S10-AC3 (mock theo BE): Quản lý KHÔNG có key unit_cost", j["allocations"] and all("unit_cost" not in a for a in j["allocations"]), str(j["allocations"]))
    ok("S10-AC3: Quản lý thấy phân bổ lô (mã lô, kg) nhưng không có 'Vốn'",
       dlg.locator(".alloc-list li").count() == len(j["allocations"]) and dlg.locator(".alloc-cost").count() == 0 and "Vốn" not in dlg.inner_text())
    ok("S11-AC7: Quản lý → available_actions không có confirm_payment, không có nút",
       "confirm_payment" not in j["available_actions"] and dlg.get_by_role("button", name="Xác nhận đã nhận tiền").count() == 0)
    page.screenshot(path=f"{SHOTS}/s10-detail-1280-quanly.png")
    close_sheet(page)
    ctx.close()

    # ================= NV kho thiếu reports.view_dashboard: menu Đơn vẫn hiện (bỏ điều kiện tạm TODO(S10)) =================
    ctx, page = new_page()
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.evaluate("() => window.__caveMock.patchUser('kho1', {denied_perms: ['reports.view_dashboard']})")
    login(page, "kho1")
    page.wait_for_url("**/orders/")
    ok("kho1 thiếu view_dashboard: trang đầu là Đơn & tiền, menu có Đơn, không có Tổng quan / Kho & lô",
       "Đơn & tiền" in nav_labels(page) and "Tổng quan" not in nav_labels(page) and "Kho & lô" not in nav_labels(page), str(nav_labels(page)))
    list_ready(page)
    ok("kho1: màn Đơn có dữ liệu (không bị 403)", rows(page).count() == 20)
    ctx.close()

    # ================= giao1 (chỉ nv_giao): menu không có Đơn, gõ URL bị chặn, không gọi API =================
    ctx, page = new_page()
    login(page, "giao1")
    page.wait_for_url("**/my-deliveries/")
    ok("S10-AC6: giao1 không có menu 'Đơn & tiền'", "Đơn & tiền" not in nav_labels(page), str(nav_labels(page)))
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
    idle(page)
    ok("S10-AC6: giao1 gõ /orders/ → chặn, không gọi API đơn", log(page) == ["GET /api/auth/me/"], str(log(page)))
    ctx.close()

    # ================= Ảnh + đo: 360 và 1280, sáng và tối =================
    for width, height, mobile in [(360, 640, True), (1280, 800, False)]:
        for dark in (False, True):
            tag = f"{width}-{'dark' if dark else 'light'}"
            ctx, page = new_page(width, height, dark=dark, mobile=mobile)
            login(page, "loc")
            page.wait_for_url("**/overview/")
            page.goto(BASE + "/orders/")
            list_ready(page)
            fonts_ready(page)
            if width == 360:
                ok(f"S10-AC7 {tag}: danh sách không cuộn ngang", hscroll(page) <= 360, str(hscroll(page)))
                small = page.evaluate(SMALL_TAPS_JS, 360)
                ok(f"S10-AC7 {tag}: vùng bấm danh sách ≥ 44px", not small, str(small))
            page.screenshot(path=f"{SHOTS}/s10-list-{tag}.png")
            dlg = open_order(page, 101)
            fonts_ready(page)
            if width == 360:
                ok(f"S10-AC7 {tag}: chi tiết là tấm đáy, không cuộn ngang",
                   hscroll(page) <= 360 and page.evaluate("() => { const s = document.querySelector('.sheet'); return s.scrollWidth <= s.clientWidth; }"))
                small = page.evaluate(SMALL_TAPS_JS, 360)
                ok(f"S10-AC7 {tag}: vùng bấm trong chi tiết ≥ 44px", not small, str(small))
            page.screenshot(path=f"{SHOTS}/s10-detail-{tag}.png")
            dlg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
            expect(dlg.locator("form.confirm-payment")).to_be_visible()
            if width == 360:
                ok(f"S11 {tag}: bước xác nhận không cuộn ngang",
                   page.evaluate("() => { const s = document.querySelector('.sheet'); return s.scrollWidth <= s.clientWidth; }"))
                small = page.evaluate(SMALL_TAPS_JS, 360)
                ok(f"S11 {tag}: vùng bấm bước xác nhận ≥ 44px", not small, str(small))
            page.screenshot(path=f"{SHOTS}/s11-confirm-{tag}.png")
            dlg.get_by_label("Mã giao dịch ngân hàng").fill(f"FT26267{width}{int(dark)}")
            dlg.locator("form.confirm-payment button[type=submit]").click()
            expect(dlg.locator(".confirm-result")).to_be_visible()
            idle(page)
            page.screenshot(path=f"{SHOTS}/s11-result-{tag}.png")
            ctx.close()

    browser.close()

relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "401" not in e and "403" not in e
            and "500" not in e and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]
ok("Không lỗi console (trừ font/401/403/500 cố ý)", not relevant, str(relevant[:5]))
fails = 0
for n, c, e in results:
    print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + e))
    fails += 0 if c else 1
print(f"{len(results) - fails}/{len(results)} PASS")
