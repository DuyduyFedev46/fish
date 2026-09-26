# E2E S12 (hàng chờ thanh toán lệch) và S13 (phiếu hoàn cho khoản không có hoá đơn): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s12_s13_queue.py      # tắt server sau khi xong
#
# Mock theo contract THỰC TẾ BE L8 (features/orders/mock.ts, 03-dev-notes.md "Lô L8 — S12, S13 (BE)"). Hàng chờ gieo sẵn
# (mỗi context mới gieo lại, sessionStorage):
#   106 UNDERPAID FT2626700002 (đơn Giữ chỗ, thiếu 100.000) · 119 ORPHAN FT2626700019 (520.000, đơn tự huỷ)
#   113 OVERPAID FT2626700013 (150.000, đơn đã hoàn tất — P5/BR-TT-10) · 880 UNMATCHED FT2626700091 540.000 (= đơn 101)
#   881 UNMATCHED FT2626700092 185.000 · lịch sử: 870 ORPHAN đã hoàn (RESOLVED/REFUNDED)
# Ổn định: KHÔNG ngủ — chờ URL, phần tử, `aria-busy`, `__caveMock.pending() === 0`. Context bật reduced_motion.
# Câu lỗi BE lấy qua window.__caveMock.beDetail (không gõ lại chuỗi).

import os
import re

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []
expect.set_options(timeout=10_000)
QLIST = "GET /api/sales/payments/?resolution_status=OPEN"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


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


def rows(page):
    return page.locator("ul.queue-list > li")


def list_ready(page):
    expect(page.locator("section[aria-labelledby=queue-h]")).to_be_visible()
    expect(page.locator("section[aria-busy=true]")).to_have_count(0)
    idle(page)


def open_txn(page, pid):
    page.locator(f'.queue-open[data-id="{pid}"]').click()
    dlg = page.get_by_role("dialog")
    expect(dlg.locator(".payment-view")).to_be_visible()
    idle(page)
    return dlg


def close_sheet(page):
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)


def be(page, key, params=None):
    return page.evaluate("([k, p]) => window.__caveMock.beDetail(k, p || undefined)", [key, params])


def qjson(page, user="loc", status="OPEN"):
    return page.evaluate("([u, s]) => window.__caveMock.queueJson(u, s)", [user, status])


def nav_labels(page):
    return [t.split("\n")[-1].strip() for t in page.locator(".nav a").all_inner_texts()]


def fonts_ready(page):
    page.wait_for_function("() => document.fonts.status === 'loaded'")


def hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth")


def sheet_fits(page):
    return page.evaluate("() => { const s = document.querySelector('.sheet'); return !s || s.scrollWidth <= s.clientWidth; }")


def posts(page):
    return [x for x in log(page) if x.startswith("POST")]


SMALL_TAPS_JS = """(w) => [...document.querySelectorAll('button, a, input, select, textarea')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < w && r.y < innerHeight && r.bottom > 0
      && !e.closest('.sr-only') && !(e.type === 'radio')
      && (r.height < 44 || (e.tagName !== 'INPUT' && e.tagName !== 'SELECT' && e.tagName !== 'TEXTAREA' && r.width < 44));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""


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
    labels = nav_labels(page)
    ok("S12: menu Chủ có mục con 'Hàng chờ thanh toán' ngay dưới 'Đơn & tiền'",
       "Hàng chờ thanh toán" in labels and labels.index("Hàng chờ thanh toán") == labels.index("Đơn & tiền") + 1, str(labels))
    ok("S12: mục con thụt vào (lớp .sub)", page.locator(".nav a.sub", has_text="Hàng chờ thanh toán").count() == 1)
    clear_log(page)
    page.locator(".nav a", has_text="Hàng chờ thanh toán").click()
    page.wait_for_url("**/orders/payments/")
    list_ready(page)
    ok("S12: mở màn gọi GET /api/sales/payments/?resolution_status=OPEN", QLIST in log(page), str(log(page)))
    ok("S12: tiêu đề = 'Hàng chờ thanh toán', chỉ mục con sáng (không sáng cả 'Đơn & tiền')",
       page.locator(".topbar h1").inner_text() == "Hàng chờ thanh toán"
       and page.locator(".nav a.active").all_inner_texts()[-1].split("\n")[-1].strip() == "Hàng chờ thanh toán"
       and page.locator(".nav a.active").count() == 1)
    ok("S12: máy tính không hiện tab con (đã có menu con)", not page.locator(".orders-tabs").is_visible())

    # S12-AC1: không có MATCHED; mỗi dòng có loại lệch, số tiền, đơn liên quan
    j = qjson(page)
    ok("S12-AC1 (mock theo BE): hàng chờ OPEN không có MATCHED, có đủ 4 loại lệch",
       all(r["match_status"] != "MATCHED" and r["resolution_status"] == "OPEN" for r in j["results"])
       and {r["match_status"] for r in j["results"]} == {"UNDERPAID", "ORPHAN", "OVERPAID", "UNMATCHED"}, str([r["match_status"] for r in j["results"]]))
    ok("S12-AC1: số dòng = count BE (5)", rows(page).count() == j["count"] == 5, str(rows(page).count()))
    expect(page.locator("#queue-h + .sub")).to_have_text("5 khoản")
    txt = rows(page).all_inner_texts()
    ok("S12-AC1: mỗi dòng có loại lệch + số tiền (₫) + mã GD",
       all("₫" in t and "FT" in t for t in txt) and any("Thiếu tiền" in t for t in txt) and any("Không khớp đơn" in t for t in txt)
       and any("Chuyển thừa" in t for t in txt) and any("Về sau khi đơn tự huỷ" in t for t in txt), str(txt[:2]))
    ok("S12-AC1: khoản không khớp ghi 'Chưa gắn đơn'; khoản có đơn ghi mã SO…",
       "Chưa gắn đơn" in page.locator('.queue-open[data-id="880"]').inner_text()
       and all(("SO" in t) != ("Chưa gắn đơn" in t) for t in txt), str(txt))
    ok("BR-PQ-15: JSON hàng chờ không có field giá vốn", "unit_cost" not in str(j) and "landed" not in str(j))
    fonts_ready(page)
    page.screenshot(path=f"{SHOTS}/s12-list-1280-light.png")

    # Lọc loại lệch
    clear_log(page)
    page.get_by_label("Loại lệch").select_option(label="Không khớp đơn")
    expect(rows(page)).to_have_count(2)
    idle(page)
    ok("S12: lọc 'Không khớp đơn' gửi ?match_status=UNMATCHED", log(page)[-1] == QLIST + "&match_status=UNMATCHED", str(log(page)))
    page.get_by_label("Loại lệch").select_option(label="Mọi loại lệch")
    expect(rows(page)).to_have_count(5)
    idle(page)

    # Dòng thiếu tiền chỉ có 300/540 → không có nút xác nhận (BE giả định 1); gọi thẳng → BR-TT-09 (S12-AC4)
    under = next(r for r in j["results"] if r["match_status"] == "UNDERPAID")
    ok("S12-AC4: khoản thiếu chưa đủ → available_actions KHÔNG có confirm_order (chỉ refund)", under["available_actions"] == ["refund"], str(under["available_actions"]))
    r = page.evaluate("([id]) => window.__caveMock.resolveJson('loc', id, {action: 'CONFIRM_ORDER', note: ''})", [under["id"]])
    o = under["order"]
    exp = be(page, "TT_NOT_ENOUGH", {"paid": f"{int(o['paid_total']):,}".replace(",", ".") + "đ", "total": f"{int(o['total_amount']):,}".replace(",", ".") + "đ"})
    ok("S12-AC4: CONFIRM_ORDER khi chưa đủ → 400 BR-TT-09 'Tổng tiền đã nhận … < tổng đơn …'",
       r["status"] == 400 and r["body"]["code"] == "BR-TT-09" and r["body"]["detail"] == exp, str(r))
    dlg = open_txn(page, under["id"])
    ok("S12: tấm khoản thiếu hiện Tổng đơn / Đã nhận / Còn thiếu + nút 'Xem đơn'",
       "Còn thiếu" in dlg.inner_text() and dlg.locator(".open-order").is_visible())
    ok("S12-AC4: không có nút 'Xác nhận đơn (khách đã bù)' khi chưa đủ", dlg.get_by_role("button", name="Xác nhận đơn (khách đã bù)").count() == 0)
    page.screenshot(path=f"{SHOTS}/s12-detail-under-1280-light.png")
    close_sheet(page)

    # ---- S12-AC2: gắn khoản không khớp 540.000 vào đơn 101 (Giữ chỗ 540.000) ----
    dlg = open_txn(page, 880)
    ok("S12: khoản không khớp → nút 'Gắn vào đơn' + 'Lập phiếu hoàn' theo available_actions",
       dlg.get_by_role("button", name="Gắn vào đơn").is_visible() and dlg.get_by_role("button", name="Lập phiếu hoàn").is_visible())
    page.screenshot(path=f"{SHOTS}/s12-detail-unmatched-1280-light.png")
    clear_log(page)
    dlg.get_by_role("button", name="Gắn vào đơn").click()
    form = dlg.locator("form.attach-order")
    expect(form).to_be_visible()
    expect(form.locator(".attach-pick label").first).to_be_visible()
    idle(page)
    ok("S12: bước gắn đơn tìm đơn Giữ chỗ bằng API đơn (?status=BOOKED)", "GET /api/sales/orders/?status=BOOKED" in log(page), str(log(page)))
    ok("S12: focus vào ô tìm đơn", page.evaluate("() => document.activeElement && document.activeElement.name === 'order_q'"))
    row101 = form.locator('.attach-pick label[data-id="101"]')
    ok("S12: đơn 101 (540.000 ₫) được đánh dấu 'Bằng số tiền'", "Bằng số tiền" in row101.inner_text(), row101.inner_text())
    clear_log(page)
    form.locator("button[type=submit]").click()
    expect(form.get_by_text("Chọn một đơn trong danh sách để gắn.")).to_be_visible()
    ok("S12: chưa chọn đơn → báo tại chỗ, KHÔNG gọi API", posts(page) == [], str(log(page)))
    # tìm theo tên (BE lọc, bỏ dấu)
    form.get_by_label("Tìm đơn theo mã, tên khách hoặc SĐT").fill("chi hoa")
    page.wait_for_function("() => window.__caveMock.log.some(x => x.includes('q=chi'))")
    idle(page)
    expect(form.locator(".attach-pick label")).to_have_count(1)
    row101.click()
    q = form.locator("h3").inner_text()
    ok("S12: câu hỏi nêu số tiền + mã đơn", "540.000 ₫" in q and "SO" in q, q)
    ok("S12: nêu hậu quả (Đang xử lý, không hoàn tác, nhật ký)",
       "Đang xử lý" in form.inner_text() and "Không hoàn tác" in form.inner_text() and "Nhật ký" in form.inner_text())
    form.get_by_label("Ghi chú").fill("Khách ghi sai nội dung CK")
    page.screenshot(path=f"{SHOTS}/s12-attach-1280-light.png")
    clear_log(page)
    form.locator("button[type=submit]").dblclick()
    expect(dlg.locator(".queue-result")).to_be_visible()
    idle(page)
    ok("S12: bấm đúp → chỉ 1 POST resolve", posts(page) == ["POST /api/sales/payments/880/resolve/"], str(posts(page)))
    res = dlg.locator(".queue-result").inner_text()
    ok("S12-AC2: báo 'Đã gắn vào đơn SO…', đơn Đang xử lý, có phiếu giao", "Đã gắn vào đơn" in res and "Đang xử lý" in res and "GH-" in res, res)
    ok("S12-AC2: tải lại khoản (GET /api/sales/payments/880/)", "GET /api/sales/payments/880/" in log(page), str(log(page)))
    expect(dlg.locator("#pq-resolved")).to_be_visible()
    ok("S12-AC2: khoản RESOLVED, ghi người (Lộc) + ghi chú, hết nút",
       "Lộc" in dlg.inner_text() and "Khách ghi sai nội dung CK" in dlg.inner_text() and dlg.locator("[data-action]").count() == 0)
    page.screenshot(path=f"{SHOTS}/s12-attach-result-1280-light.png")
    # Mở chi tiết đơn liên quan — tải mới, thấy trạng thái sau thao tác
    dlg.locator(".open-order").click()
    od = page.get_by_role("dialog")
    expect(od.locator("header .status")).to_have_text("Đang xử lý")
    idle(page)
    ok("S12-AC2: chi tiết đơn 101 cập nhật: Đang xử lý, có hoá đơn, giao dịch FT2626700091 Khớp",
       "INV" in od.inner_text() and "FT2626700091" in od.inner_text() and "Khớp — đã xác nhận" in od.inner_text())
    close_sheet(page)
    expect(page.locator(".alert-box.ok")).to_contain_text("Đã gắn vào đơn")
    ok("S12: đóng tấm → thông báo nổi", True)
    list_ready(page)
    ok("S12: danh sách tải lại, khoản 880 rời hàng chờ Đang chờ", page.locator('.queue-open[data-id="880"]').count() == 0 and rows(page).count() == 4)
    r = page.evaluate("() => window.__caveMock.resolveJson('loc', 880, {action: 'ATTACH_TO_ORDER', order_id: 101, note: ''})")
    ok("S12-AC6: resolve lần nữa trên khoản đã đóng → 400 BR-TT-09",
       r["status"] == 400 and r["body"]["detail"] == be(page, "TT_ALREADY_RESOLVED"), str(r))

    # ---- S12-AC5: đơn tự huỷ trong lúc chờ → BR-TT-05 nguyên văn, không đổi gì ----
    dlg = open_txn(page, 881)
    dlg.get_by_role("button", name="Gắn vào đơn").click()
    form = dlg.locator("form.attach-order")
    expect(form.locator('.attach-pick label[data-id="102"]')).to_be_visible()
    idle(page)
    page.evaluate("() => window.__caveMock.expireOrder(102)")
    form.locator('.attach-pick label[data-id="102"]').click()
    form.locator("button[type=submit]").click()
    expect(form.locator(".queue-error")).to_be_visible()
    ok("S12-AC5: đơn đã tự huỷ → lỗi BE nguyên văn (BR-TT-05), vẫn ở bước gắn",
       form.locator(".queue-error > span").inner_text().strip() == be(page, "TT_ORDER_CANCELLED") and form.is_visible(), form.locator(".queue-error").inner_text())
    page.screenshot(path=f"{SHOTS}/s12-error-1280-light.png")
    ok("S12-AC5: khoản vẫn OPEN, đơn không khôi phục",
       any(x["id"] == 881 and x["order"] is None for x in qjson(page)["results"])
       and page.evaluate("() => window.__caveMock.orderJson('loc', 102).status") == "AUTO_CANCELLED")
    form.get_by_role("button", name="Quay lại").click()
    page.wait_for_function("() => document.activeElement && document.activeElement.dataset.action === 'attach_to_order'")
    ok("S12: Quay lại → về chi tiết, focus về nút thao tác", True)
    close_sheet(page)

    # ---- S12-AC3: đơn 106 có 2 khoản thiếu cộng đủ → CONFIRM_ORDER đóng cả hai ----
    page.goto(BASE + "/orders/")
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    idle(page)
    total106 = int(page.evaluate("() => window.__caveMock.orderJson('loc', 106).total_amount"))
    page.locator('.order-open[data-id="106"]').click()
    od = page.get_by_role("dialog")
    expect(od.locator("header")).to_be_visible()
    idle(page)
    od.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    od.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799106")
    od.get_by_label("Số tiền đã nhận").fill("100000")
    od.locator("form.confirm-payment button[type=submit]").click()
    expect(od.locator(".confirm-result")).to_contain_text("còn thiếu")
    idle(page)
    close_sheet(page)
    page.goto(BASE + "/orders/payments/")
    list_ready(page)
    unders = [x for x in qjson(page)["results"] if x["order"] and x["order"]["id"] == 106]
    ok("S12-AC3: đơn 106 có 2 khoản thiếu (BR-TT-04 khớp theo từng giao dịch), tổng đã nhận = tổng đơn",
       len(unders) == 2 and all(x["match_status"] == "UNDERPAID" for x in unders) and int(unders[0]["order"]["paid_total"]) == total106, str(unders))
    ok("S12-AC3: đủ rồi → available_actions có confirm_order", all("confirm_order" in x["available_actions"] for x in unders))
    dlg = open_txn(page, unders[0]["id"])
    clear_log(page)
    dlg.get_by_role("button", name="Xác nhận đơn (khách đã bù)").click()
    form = dlg.locator("form.confirm-order")
    expect(form).to_be_visible()
    ok("S12: bước xác nhận đơn không cảnh báo thiếu khi đã đủ", form.locator(".confirm-short").count() == 0)
    ok("S12: nêu 'Mọi khoản chuyển thiếu của đơn này cùng được đóng'", "cùng được đóng" in form.inner_text())
    page.screenshot(path=f"{SHOTS}/s12-confirm-1280-light.png")
    form.get_by_label("Ghi chú").fill("Khách đã chuyển bù FT2626799106")
    form.locator("button[type=submit]").dblclick()
    expect(dlg.locator(".queue-result")).to_be_visible()
    idle(page)
    ok("S12: bấm đúp → 1 POST resolve", len(posts(page)) == 1, str(posts(page)))
    res = dlg.locator(".queue-result").inner_text()
    ok("S12-AC3: báo 'Đã xác nhận đơn … Đang xử lý … Đã đóng 2 khoản'", "Đã xác nhận đơn" in res and "Đang xử lý" in res and "2 khoản" in res, res)
    resolved = qjson(page, status="RESOLVED")["results"]
    ok("S12-AC3: CẢ HAI khoản của đơn 106 RESOLVED/CONFIRMED",
       sorted(x["id"] for x in resolved if x["order"] and x["order"]["id"] == 106 and x["resolution"] == "CONFIRMED") == sorted(x["id"] for x in unders), str(resolved))
    close_sheet(page)
    list_ready(page)
    page.get_by_role("button", name="Đã xử lý").click()
    list_ready(page)
    ok("S12: tab 'Đã xử lý' gửi resolution_status=RESOLVED và hiện cách xử lý", "resolution_status=RESOLVED" in log(page)[-1]
       and "Đã xác nhận đơn" in page.locator("ul.queue-list").inner_text() and "Đã gắn vào đơn" in page.locator("ul.queue-list").inner_text())
    page.screenshot(path=f"{SHOTS}/s12-resolved-1280-light.png")
    page.get_by_role("button", name="Đang chờ").click()
    list_ready(page)

    # ---- S13: phiếu hoàn cho khoản về sau khi đơn tự huỷ (ORPHAN 119, 520.000) ----
    orphan = next(x for x in qjson(page)["results"] if x["match_status"] == "ORPHAN")
    amt = int(orphan["amount"])
    dlg = open_txn(page, orphan["id"])
    ok("S13: khoản ORPHAN chỉ có nút 'Lập phiếu hoàn'", [b.get_attribute("data-action") for b in dlg.locator("[data-action]").all()] == ["refund"])
    dlg.get_by_role("button", name="Lập phiếu hoàn").click()
    form = dlg.locator("form.refund-form")
    expect(form).to_be_visible()
    ok("S13: số tiền mặc định = số còn được hoàn", form.get_by_label("Số tiền hoàn").input_value() == str(amt), form.get_by_label("Số tiền hoàn").input_value())
    ok("S13: lý do điền sẵn theo loại lệch", form.get_by_label("Lý do hoàn").input_value() == "Tiền về sau khi đơn tự huỷ")
    ok("S13: nêu tiền CHƯA rời tài khoản + vẫn trong hàng chờ + không trừ doanh thu",
       "CHƯA rời" in form.inner_text() and "vẫn nằm trong hàng chờ" in form.inner_text() and "không trừ vào doanh thu" in form.inner_text())
    page.screenshot(path=f"{SHOTS}/s13-refund-1280-light.png")
    clear_log(page)
    form.get_by_label("Lý do hoàn").fill("")
    form.locator("button[type=submit]").click()
    expect(form.get_by_text("Nhập lý do hoàn")).to_be_visible()
    form.get_by_label("Lý do hoàn").fill("Tiền về sau khi đơn tự huỷ")
    form.get_by_label("Số tiền hoàn").fill("0")
    form.locator("button[type=submit]").click()
    expect(form.locator(".field-err")).to_be_visible()
    ok("S13: lý do trống / số tiền 0 → báo tại ô, KHÔNG gọi API", posts(page) == [], str(log(page)))
    form.get_by_label("Số tiền hoàn").fill(str(amt - 100000))
    form.locator("button[type=submit]").dblclick()
    expect(dlg.locator(".queue-result")).to_be_visible()
    idle(page)
    ok("S13: bấm đúp → 1 POST refunds/create", posts(page) == ["POST /api/sales/refunds/create/"], str(posts(page)))
    refs = page.evaluate("([id]) => window.__caveMock.txnRefundsOf(id)", [orphan["id"]])
    ok("S13-AC1: phiếu PENDING, request_id là UUID v4", len(refs) == 1 and refs[0]["status"] == "PENDING" and UUID.match(refs[0]["request_id"] or ""), str(refs))
    after = next(x for x in qjson(page)["results"] if x["id"] == orphan["id"])
    ok("S13-AC1: khoản vẫn OPEN, còn được hoàn 100.000", after["resolution_status"] == "OPEN" and after["refundable_amount"] == "100000", str(after))
    expect(dlg.locator(".refundable-left")).to_contain_text("100.000")
    ok("S13: tấm hiện 'Còn được hoàn 100.000 ₫', vẫn còn nút hoàn", dlg.get_by_role("button", name="Lập phiếu hoàn").is_visible())
    # S13-AC3: tạo thêm 150.000 → BR-HT-04 nguyên văn
    dlg.get_by_role("button", name="Lập phiếu hoàn").click()
    form = dlg.locator("form.refund-form")
    form.get_by_label("Số tiền hoàn").fill("150000")
    expect(form.get_by_text("Nhiều hơn số còn được hoàn")).to_be_visible()
    form.locator("button[type=submit]").click()
    expect(form.locator(".queue-error")).to_be_visible()
    ok("S13-AC3: vượt số còn hoàn → lỗi BE nguyên văn 'tối đa 100.000đ'",
       form.locator(".queue-error > span").inner_text().strip() == be(page, "HT_OVER_REFUNDABLE", {"max": "100.000đ"}), form.locator(".queue-error").inner_text())
    page.screenshot(path=f"{SHOTS}/s13-error-1280-light.png")
    form.get_by_role("button", name="Quay lại").click()
    close_sheet(page)
    # S13-AC2: xác nhận phiếu (S16, giả lập) → khoản RESOLVED/REFUNDED
    page.evaluate("([id]) => window.__caveMock.confirmRefund(id, 'FTREF1')", [refs[0]["id"]])
    ok("S13-AC2: phiếu xác nhận → khoản RESOLVED/REFUNDED",
       any(x["id"] == orphan["id"] and x["resolution"] == "REFUNDED" for x in qjson(page, status="RESOLVED")["results"]))
    # S13-AC4 / AC6 / request_id (gọi thẳng luật mock như API)
    r = page.evaluate("([id]) => window.__caveMock.refundJson('loc', {sales_invoice: 41, payment_transaction: id, amount: '1000', reason: 'x', request_id: crypto.randomUUID()})", [881])
    ok("S13-AC4: gửi cả sales_invoice và payment_transaction → 400 BR-HT-01", r["status"] == 400 and r["body"]["code"] == "BR-HT-01", str(r))
    r = page.evaluate("() => window.__caveMock.refundJson('ql1', {payment_transaction: 881, amount: '1000', reason: 'x', request_id: crypto.randomUUID()})")
    ok("S13-AC6: Quản lý tạo phiếu hoàn gắn giao dịch → 403", r["status"] == 403, str(r))
    rid = page.evaluate("() => crypto.randomUUID()")
    r1 = page.evaluate("([u]) => window.__caveMock.refundJson('loc', {payment_transaction: 881, amount: '1000', reason: 'x', request_id: u})", [rid])
    r2 = page.evaluate("([u]) => window.__caveMock.refundJson('loc', {payment_transaction: 881, amount: '1000', reason: 'x', request_id: u})", [rid])
    ok("S13: cùng request_id → 201 rồi 200 duplicate, cùng một phiếu",
       r1["status"] == 201 and r2["status"] == 200 and r2["body"].get("duplicate") is True and r1["body"]["id"] == r2["body"]["id"], str((r1, r2)))
    r = page.evaluate("() => window.__caveMock.refundJson('loc', {payment_transaction: 881, amount: '1000', reason: 'x', request_id: 'abc'})")
    ok("S13: request_id không phải UUID → 400 BR-HT-01", r["status"] == 400 and r["body"]["detail"] == be(page, "HT_REQUEST_ID_INVALID"), str(r))

    # ---- OVERPAID (P5 / BR-TT-10) ----
    over = next(x for x in qjson(page)["results"] if x["match_status"] == "OVERPAID")
    ok("P5/BR-TT-10: khoản chuyển thừa gắn đơn đã xong, chỉ còn 'refund'", over["order"] is not None and over["available_actions"] == ["refund"], str(over))
    dlg = open_txn(page, over["id"])
    ok("P5: tấm chuyển thừa hiện dòng 'Thừa'", "Thừa" in dlg.inner_text())
    close_sheet(page)

    # ---- Trạng thái: lỗi / rỗng / 403 ----
    for mode, check in [("fail", "Thử lại"), ("empty", "Không còn khoản tiền lệch nào"), ("forbidden", "không được cấp quyền")]:
        page.evaluate("([m]) => window.__caveMock.payments(m)", [mode])
        page.reload()
        expect(page.get_by_text(check).first).to_be_visible()
        ok(f"S12: trạng thái '{mode}' hiện đúng", True)
        if mode == "forbidden":
            ok("S12: 403 dùng icon khoá", page.locator(".state-err .mi", has_text="lock").count() == 1)
        page.screenshot(path=f"{SHOTS}/s12-state-{mode}-1280-light.png")
    page.evaluate("() => window.__caveMock.payments('ok')")
    ctx.close()

    # ================= L8 bổ sung tiền (Duy 2026-09-26): chuyển thừa ngay lần đầu + tối thiểu 1đ =================
    ctx, page = new_page()
    login(page, "loc")
    page.wait_for_url("**/overview/")
    page.goto(BASE + "/orders/")
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    idle(page)
    total102 = int(page.evaluate("() => window.__caveMock.orderJson('loc', 102).total_amount"))
    page.locator('.order-open[data-id="102"]').click()
    od = page.get_by_role("dialog")
    expect(od.locator("header")).to_be_visible()
    idle(page)
    od.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    od.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799600")
    od.get_by_label("Số tiền đã nhận").fill(str(total102 + 60000))
    ok("Bổ sung tiền: ô số tiền nhiều hơn tổng đơn → nhắc phần thừa vào hàng chờ", "phần thừa vào hàng chờ" in od.locator("form.confirm-payment").inner_text())
    od.locator("form.confirm-payment button[type=submit]").click()
    expect(od.locator(".confirm-result")).to_be_visible()
    idle(page)
    res = od.locator(".confirm-result").inner_text()
    ok("Bổ sung tiền: xác nhận PAID + báo 'Khách chuyển thừa 60.000 ₫ — đã đưa vào hàng chờ để hoàn'",
       "Đã xác nhận nhận tiền" in res and "Khách chuyển thừa 60.000 ₫ — đã đưa vào hàng chờ để hoàn" in res, res)
    ok("Bổ sung tiền: chi tiết đơn có dòng -THUA 'Chuyển thừa' cạnh dòng khớp",
       od.locator("code", has_text="FT2626799600-THUA").count() >= 1 and "Chuyển thừa" in od.inner_text())
    ok("Bổ sung tiền: thông báo có liên kết 'Mở hàng chờ thanh toán'", od.locator(".confirm-result a.queue-link").is_visible())
    thua = [x for x in qjson(page)["results"] if x["bank_txn_id"] == "FT2626799600-THUA"]
    ok("Bổ sung tiền: hàng chờ có dòng FT…-THUA 60.000 OVERPAID/OPEN, chỉ refund, đơn Đang xử lý",
       len(thua) == 1 and thua[0]["amount"] == "60000" and thua[0]["match_status"] == "OVERPAID" and thua[0]["available_actions"] == ["refund"]
       and thua[0]["order"]["status"] == "PROCESSING" and thua[0]["order"]["paid_total"] == str(total102), str(thua))
    od.locator(".confirm-result a.queue-link").click()
    page.wait_for_url("**/orders/payments/")
    list_ready(page)
    ok("Bổ sung tiền: bấm liên kết → hàng chờ, có dòng -THUA", page.locator(".queue-list", has_text="FT2626799600-THUA").count() == 1)
    r = page.evaluate("([id]) => window.__caveMock.refundJson('loc', {payment_transaction: id, amount: '0.5', reason: 'x', request_id: crypto.randomUUID()})", [thua[0]["id"]])
    ok("Tối thiểu 1đ: phiếu hoàn 0,5 → 400 'Số tiền hoàn tối thiểu 1đ.'", r["status"] == 400 and r["body"]["detail"] == be(page, "HT_AMOUNT_MIN"), str(r))
    r = page.evaluate("() => window.__caveMock.confirmJson('loc', 101, {bank_txn_id: 'FT-MIN-1', amount: '0.5'})")
    ok("Tối thiểu 1đ: xác nhận tay 0,5 → 400 'Số tiền tối thiểu 1đ.'", r["status"] == 400 and r["body"]["detail"] == be(page, "TT_AMOUNT_MIN"), str(r))
    dlg = open_txn(page, thua[0]["id"])
    dlg.get_by_role("button", name="Lập phiếu hoàn").click()
    form = dlg.locator("form.refund-form")
    clear_log(page)
    for bad in ["0,5", "0.99"]:
        form.get_by_label("Số tiền hoàn").fill(bad)
        form.locator("button[type=submit]").click()
        expect(form.get_by_text("Số tiền phải từ 1 ₫ trở lên")).to_be_visible()
    ok("Tối thiểu 1đ: ô phiếu hoàn 0,5 / 0.99 → báo tại ô, KHÔNG gọi API", posts(page) == [], str(log(page)))
    ctx.close()

    # ================= S12-AC7: Quản lý / NV kho — không menu con, gõ URL bị chặn, không gọi API =================
    for user in ("ql1", "kho1"):
        ctx, page = new_page()
        login(page, user)
        page.wait_for_url(re.compile(r".*/(overview|orders)/$"))
        idle(page)
        ok(f"S12-AC7: {user} không có menu con 'Hàng chờ thanh toán'", "Hàng chờ thanh toán" not in nav_labels(page), str(nav_labels(page)))
        clear_log(page)
        page.goto(BASE + "/orders/payments/")
        expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
        idle(page)
        ok(f"S12-AC7: {user} gõ URL → chặn, KHÔNG gọi /api/sales/payments/", not any("/api/sales/payments/" in x for x in log(page)), str(log(page)))
        r = page.evaluate(f"() => window.__caveMock.resolveJson('{user}', 881, {{action: 'CONFIRM_ORDER'}})")
        ok(f"S12-AC7: {user} resolve → 403", r["status"] == 403, str(r))
        page.goto(BASE + "/orders/")
        expect(page.locator("ul.order-list > li").first).to_be_visible()
        if user == "ql1":
            # S16 (L9): ql1 có sales.view_refund → tab con VẪN hiện, nhưng chỉ "Phiếu hoàn chờ chuyển" (không có
            # "Hàng chờ thanh toán", vì thiếu confirm_payment_manual).
            ok("S12/S16: ql1 tab con chỉ có 'Phiếu hoàn chờ chuyển', không có 'Hàng chờ thanh toán'",
               page.locator(".orders-tabs", has_text="Phiếu hoàn chờ chuyển").count() == 1
               and page.locator(".orders-tabs", has_text="Hàng chờ thanh toán").count() == 0)
        else:
            ok(f"S12: {user} không thấy tab con ở màn Đơn", page.locator(".orders-tabs").count() == 0)
        ctx.close()

    # ================= Ảnh + đo: 360 và 1280, sáng và tối =================
    for width, height, mobile in [(360, 640, True), (1280, 800, False)]:
        for dark in (False, True):
            tag = f"{width}-{'dark' if dark else 'light'}"
            ctx, page = new_page(width, height, dark=dark, mobile=mobile)
            login(page, "loc")
            page.wait_for_url("**/overview/")
            if width == 360:
                page.goto(BASE + "/orders/")
                expect(page.locator(".orders-tabs")).to_be_visible()
                bl = [t.split("\n")[-1].strip() for t in page.locator(".bottom-nav").locator("a, button").all_inner_texts()]
                ok(f"S12 {tag}: menu đáy không có mục con, ≤ 5 mục", "Hàng chờ" not in bl and len(bl) <= 5, str(bl))
                page.locator(".orders-tabs a", has_text="Hàng chờ thanh toán").click()
                page.wait_for_url("**/orders/payments/")
                ok(f"S12 {tag}: tab con 'Hàng chờ thanh toán' đang chọn, menu đáy sáng 'Đơn'",
                   page.locator('.orders-tabs a[aria-current="page"]').inner_text() == "Hàng chờ thanh toán"
                   and "Đơn" in page.locator(".bottom-nav a.active").inner_text())
            else:
                page.goto(BASE + "/orders/payments/")
            list_ready(page)
            fonts_ready(page)
            if width == 360:
                ok(f"S12 {tag}: danh sách không cuộn ngang", hscroll(page) <= 360, str(hscroll(page)))
                small = page.evaluate(SMALL_TAPS_JS, 360)
                ok(f"S12 {tag}: vùng bấm danh sách ≥ 44px", not small, str(small))
            page.screenshot(path=f"{SHOTS}/s12-list-{tag}.png")
            dlg = open_txn(page, 880)
            fonts_ready(page)
            if width == 360:
                ok(f"S12 {tag}: tấm chi tiết không cuộn ngang", hscroll(page) <= 360 and sheet_fits(page))
                small = page.evaluate(SMALL_TAPS_JS, 360)
                ok(f"S12 {tag}: vùng bấm chi tiết ≥ 44px", not small, str(small))
            page.screenshot(path=f"{SHOTS}/s12-detail-{tag}.png")
            dlg.get_by_role("button", name="Gắn vào đơn").click()
            expect(dlg.locator(".attach-pick label").first).to_be_visible()
            idle(page)
            dlg.locator('.attach-pick label[data-id="101"]').click()
            if width == 360:
                ok(f"S12 {tag}: bước gắn đơn không cuộn ngang", sheet_fits(page))
                small = page.evaluate(SMALL_TAPS_JS, 360)
                ok(f"S12 {tag}: vùng bấm bước gắn đơn ≥ 44px", not small, str(small))
            page.screenshot(path=f"{SHOTS}/s12-attach-{tag}.png")
            dlg.get_by_role("button", name="Quay lại").click()
            dlg.get_by_role("button", name="Lập phiếu hoàn").click()
            expect(dlg.locator("form.refund-form")).to_be_visible()
            if width == 360:
                ok(f"S13 {tag}: bước lập phiếu hoàn không cuộn ngang", sheet_fits(page))
                small = page.evaluate(SMALL_TAPS_JS, 360)
                ok(f"S13 {tag}: vùng bấm bước hoàn ≥ 44px", not small, str(small))
            page.screenshot(path=f"{SHOTS}/s13-refund-{tag}.png")
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
