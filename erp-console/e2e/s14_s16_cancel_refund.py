# E2E S14 (huỷ đơn đã thanh toán), S15 (tạo phiếu hoàn từ đơn, chống trùng), S16 (phiếu hoàn: xác nhận / thất bại /
# thử lại): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3141 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s14_s16_cancel_refund.py      # tắt server sau khi xong
#
# Mock theo contract THỰC TẾ BE L9 (features/orders/mock.ts, 03-dev-notes.md "Lô L9 — S14, S15, S16 (BE)"). Đơn mẫu
# dùng ở đây (gieo lại mỗi context mới, sessionStorage):
#   104 PROCESSING, phiếu giao Soạn hàng (PREPARING) — huỷ thành công, hoàn kho
#   107 PROCESSING, phiếu giao Đang giao (DELIVERING) — BR-GH-07
#   108 PROCESSING, phiếu giao Giao thất bại (FAILED) — GIVE_UP_AFTER_FAILED, KHÔNG hoàn kho
#   110 CANCELLED sẵn, có phiếu hoàn PENDING (id 4, gắn sales_invoice) — dùng cho S16 xác nhận
#   Phiếu hoàn FAILED sẵn id 31 (gắn payment_transaction, khoản UNMATCHED 881) — dùng cho S16 thử lại
# Ổn định: KHÔNG ngủ — chờ URL, phần tử, `aria-busy`, `__caveMock.pending() === 0`. Context bật reduced_motion.
# Câu lỗi BE lấy qua window.__caveMock.beDetail (không gõ lại chuỗi).

import os

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3141")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []
expect.set_options(timeout=10_000)


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


def be(page, key, params=None):
    return page.evaluate("([k, p]) => window.__caveMock.beDetail(k, p || undefined)", [key, params])


def cancel_json(page, user, oid, body):
    return page.evaluate("([u, i, b]) => window.__caveMock.cancelJson(u, i, b)", [user, oid, body])


def refund_json(page, user, body):
    return page.evaluate("([u, b]) => window.__caveMock.refundJson(u, b)", [user, body])


def refund_queue_json(page, user):
    return page.evaluate("(u) => window.__caveMock.refundQueueJson(u)", user)


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


def open_order(page, oid):
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    idle(page)
    page.locator(f'.order-open[data-id="{oid}"]').click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    idle(page)
    return dlg


def close_sheet(page):
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)


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

    # ================= Chủ (loc) — menu, S14 luồng thành công + S15 nhanh sau huỷ =================
    ctx, page = new_page()
    login(page, "loc")
    page.wait_for_url("**/overview/")
    labels = nav_labels(page)
    ok("S16: menu Chủ có mục con 'Phiếu hoàn chờ chuyển' ngay sau 'Hàng chờ thanh toán'",
       "Phiếu hoàn chờ chuyển" in labels and labels.index("Phiếu hoàn chờ chuyển") == labels.index("Hàng chờ thanh toán") + 1,
       str(labels))
    ok("S16: mục con thụt vào (lớp .sub)", page.locator(".nav a.sub", has_text="Phiếu hoàn chờ chuyển").count() == 1)

    dlg = open_order(page, 104)
    expect(dlg.locator('[data-action="cancel"]')).to_be_visible()
    clear_log(page)
    dlg.locator('[data-action="cancel"]').click()
    expect(dlg.locator("form.cancel-order")).to_be_visible()

    # Chưa chọn lý do → báo tại chỗ, không gọi API.
    dlg.get_by_role("button", name="Huỷ đơn này").click()
    ok("S14-AC6a: chưa chọn lý do → báo tại ô, không gọi API", "Chọn một lý do huỷ." in dlg.inner_text() and not posts(page))

    # Chọn "Khác" mà để trống ghi chú → báo tại ô, không gọi API (S14-AC6).
    dlg.locator('input[name="reason_code"][value="OTHER"]').check()
    dlg.get_by_role("button", name="Huỷ đơn này").click()
    ok("S14-AC6: OTHER thiếu ghi chú → báo tại ô, không gọi API",
       "phải nhập ghi chú" in dlg.inner_text() and not posts(page))

    # Đổi sang lý do có sẵn rồi gửi — huỷ thành công (S14-AC1, S14-AC7).
    dlg.locator('input[name="reason_code"][value="CUSTOMER_CHANGED_MIND"]').check()
    dlg.get_by_role("button", name="Huỷ đơn này").click()
    idle(page)
    expect(dlg.locator(".cancel-refund-cta")).to_be_visible()
    txt = dlg.inner_text()
    ok("S14-AC1: huỷ thành công, đơn chuyển Đã huỷ + phiếu giao Đã huỷ theo đơn",
       "Đã huỷ đơn" in txt and "hoàn hàng về lô gốc" in txt)
    ok("S14-AC7: hiện ngay nút 'Tạo phiếu hoàn toàn phần' kèm số tiền", "Tạo phiếu hoàn toàn phần" in txt)
    page.screenshot(path=f"{SHOTS}/s14-cancel-result-1280-light.png")

    # S15: bấm CTA mở ngay form lập phiếu hoàn, điền sẵn toàn phần, gửi một lần.
    dlg.locator(".cancel-refund-cta").click()
    expect(dlg.locator("form.refund-form")).to_be_visible()
    reason_value = dlg.locator('form.refund-form textarea[name="note"]').input_value()
    ok("S15: mở từ CTA có lý do điền sẵn theo huỷ đơn", "Huỷ đơn" in reason_value, reason_value)
    dlg.screenshot(path=f"{SHOTS}/s15-refund-from-order-1280-light.png")  # tấm phóng to (page.screenshot từng chụp hụt khung)
    clear_log(page)
    dlg.get_by_role("button", name="Quay lại").click()
    idle(page)
    dlg.locator('[data-action="create_refund"]').click()
    expect(dlg.locator("form.refund-form")).to_be_visible()
    dlg.get_by_role("button", name="Lập phiếu hoàn", exact=False).last.click()
    idle(page)
    ok("S15-AC1: lập phiếu hoàn từ đơn thành công, vào 'Chờ hoàn'", "Chờ hoàn" in dlg.inner_text() or "Đã lập phiếu hoàn" in dlg.inner_text())
    close_sheet(page)

    # ================= S14: GIVE_UP_AFTER_FAILED — KHÔNG hoàn kho (Q8b, S14-AC3) =================
    dlg = open_order(page, 108)
    dlg.locator('[data-action="cancel"]').click()
    dlg.locator('input[name="reason_code"][value="GIVE_UP_AFTER_FAILED"]').check()
    clear_log(page)
    dlg.get_by_role("button", name="Huỷ đơn này").click()
    idle(page)
    ok("S14-AC3: huỷ sau giao thất bại → KHÔNG hoàn kho, tồn lô không đổi", "KHÔNG hoàn kho" in dlg.inner_text())
    close_sheet(page)

    # ================= S14: BR-GH-07 (Đang giao) — kiểm lớp chặn "BE" trực tiếp =================
    r = cancel_json(page, "loc", 107, {"reason_code": "CUSTOMER_CHANGED_MIND", "note": ""})
    ok("S14-AC4: huỷ khi phiếu giao Đang giao → 400 BR-GH-07 nguyên văn", r["body"]["code"] == "BR-GH-07" and r["body"]["detail"] == be(page, "GH_CANCEL_DELIVERING"), str(r))

    # ================= Quyền: NV kho không có nút, gọi thẳng bị 403 (S14-AC8) =================
    ctx2, page2 = new_page()
    login(page2, "kho1")
    page2.wait_for_url("**/overview/")
    dlg2 = open_order(page2, 104)
    ok("S14-AC8: NV kho không thấy nút Huỷ đơn", dlg2.locator('[data-action="cancel"]').count() == 0)
    ok("S16: NV kho không có menu 'Phiếu hoàn chờ chuyển'", "Phiếu hoàn chờ chuyển" not in nav_labels(page2))
    r = cancel_json(page2, "kho1", 104, {"reason_code": "CUSTOMER_CHANGED_MIND", "note": ""})
    ok("S14-AC8: gọi thẳng cancel thiếu quyền → 403", r == {"status": 403})
    close_sheet(page2)
    ctx2.close()

    # ================= S15: chống tạo trùng theo request_id + vượt số còn hoàn =================
    # Đơn 107 (Đang giao, chưa đụng tới ở trên) — lấy đúng id hoá đơn qua devtool, không đoán số.
    order107 = page.evaluate("(id) => window.__caveMock.orderJson('loc', id)", 107)
    inv107 = order107["invoice"]["id"]
    over = refund_json(page, "loc", {"sales_invoice": inv107, "amount": "999999999", "is_partial": False, "reason": "test", "request_id": "11111111-1111-4111-8111-111111111111"})
    ok("S15-AC2: vượt số đã thu → 400 BR-HT-04 câu S15 (Vượt số đã thu...)",
       over["status"] == 400 and over["body"]["code"] == "BR-HT-04" and "Vượt số đã thu" in over["body"]["detail"], str(over))

    rid = "22222222-2222-4222-8222-222222222222"
    first = refund_json(page, "loc", {"sales_invoice": inv107, "amount": "1", "is_partial": True, "reason": "Thử chống trùng", "request_id": rid})
    ok("S15: tạo phiếu hoàn 1đ hợp lệ", first["status"] == 201 and first["body"]["status"] == "PENDING", str(first))
    again = refund_json(page, "loc", {"sales_invoice": inv107, "amount": "1", "is_partial": True, "reason": "Thử chống trùng", "request_id": rid})
    ok("S15-AC4 (Q12): gửi lại cùng request_id → 200 duplicate, vẫn 1 phiếu",
       again["status"] == 200 and again["body"].get("duplicate") is True and again["body"]["id"] == first["body"]["id"], str(again))

    # ================= S16: danh sách + xác nhận (phiếu gắn hoá đơn, id 4) =================
    page.goto(BASE + "/orders/refunds/")
    page.wait_for_load_state("networkidle")
    idle(page)
    expect(page.locator("section[aria-labelledby=refund-h]")).to_be_visible()
    q = refund_queue_json(page, "loc")
    ok("S16: danh sách gồm cả PENDING và FAILED", any(x["status"] == "PENDING" for x in q["results"]) and any(x["status"] == "FAILED" for x in q["results"]), str(q))
    row_pending = next(x for x in q["results"] if x["status"] == "PENDING" and x["sales_invoice"])
    row_failed = next(x for x in q["results"] if x["status"] == "FAILED")
    ok("S16-AC8: SĐT khách là link tel:", page.locator(f'.refund-open[data-id="{row_pending["id"]}"] a[href^="tel:"]').count() == 0)  # link nằm trong tấm, không ở dòng danh sách

    page.locator(f'.refund-open[data-id="{row_pending["id"]}"]').click()
    dlg = page.get_by_role("dialog")
    expect(dlg.locator(".refund-view")).to_be_visible()
    ok("S16-AC8: trong tấm, SĐT khách là link tel:", dlg.locator('a[href^="tel:"]').count() >= 1)
    small = page.evaluate(SMALL_TAPS_JS, 1280)
    dlg.locator('[data-action="confirm"]').click()
    expect(dlg.locator("form.confirm-refund")).to_be_visible()
    clear_log(page)
    dlg.get_by_role("button", name="Xác nhận đã chuyển", exact=True).click()
    ok("S16-AC4: thiếu mã GD → báo tại ô, không gọi API", "mã giao dịch" in dlg.inner_text().lower() and not posts(page))
    dlg.get_by_label("Mã giao dịch chuyển khoản hoàn").fill("HT2626799999")
    dlg.get_by_role("button", name="Xác nhận đã chuyển", exact=True).click()
    idle(page)
    ok("S16-AC1: xác nhận thành công → Đã hoàn", "Đã hoàn" in dlg.inner_text())
    page.screenshot(path=f"{SHOTS}/s16-confirm-result-1280-light.png")
    close_sheet(page)

    r = cancel_json(page, "loc", 104, {"reason_code": "CUSTOMER_CHANGED_MIND", "note": ""})  # đơn 104 đã CANCELLED
    ok("S14: gọi cancel lại trên đơn đã huỷ → 400, không đổi gì", r["status"] == 400 and r["body"]["code"] == "BR-HT-05", str(r))

    # ================= S16: báo thất bại → thử lại (S16-AC3), rồi REFUNDED chặn cả 3 action (S16-AC5) =================
    page.goto(BASE + "/orders/refunds/")
    page.wait_for_load_state("networkidle")
    idle(page)
    page.locator(f'.refund-open[data-id="{row_failed["id"]}"]').click()
    dlg = page.get_by_role("dialog")
    expect(dlg.locator(".refund-view")).to_be_visible()
    ok("S16: phiếu Thất bại hiện lý do lần trước", "Sai số tài khoản" in dlg.inner_text())
    dlg.locator('[data-action="retry"]').click()
    expect(dlg.locator("form.retry-refund")).to_be_visible()
    dlg.get_by_role("button", name="Thử lại", exact=True).click()
    idle(page)
    ok("S16-AC3: thử lại → về Chờ hoàn, có nút Xác nhận/Báo thất bại", "Chờ hoàn" in dlg.inner_text() and dlg.locator('[data-action="confirm"]').count() == 1)

    dlg.locator('[data-action="mark_failed"]').click()
    expect(dlg.locator("form.mark-refund-failed")).to_be_visible()
    dlg.get_by_role("button", name="Báo thất bại", exact=True).click()  # để trống lý do — BE cho phép (blank=True)
    idle(page)
    ok("S16-AC3: báo thất bại (lý do để trống vẫn được — model cho blank) → Thất bại", "Thất bại" in dlg.inner_text())
    close_sheet(page)

    r = page.evaluate("(id) => window.__caveMock.confirmRefundJson('loc', id, {bank_txn_ref: 'x'})", row_pending["id"])
    ok("S16-AC5: phiếu đã REFUNDED (id 4) → confirm lại 400 BR-HT-09", r["body"]["code"] == "BR-HT-09" and r["body"]["detail"] == be(page, "HT_ALREADY_DONE"), str(r))
    r = page.evaluate("(id) => window.__caveMock.markRefundFailedJson('loc', id, {reason: 'x'})", row_pending["id"])
    ok("S16-AC5: phiếu đã REFUNDED → mark-failed 400 BR-HT-09", r["body"]["code"] == "BR-HT-09", str(r))
    r = page.evaluate("(id) => window.__caveMock.retryRefundJson('loc', id)", row_pending["id"])
    ok("S16-AC5: phiếu đã REFUNDED → retry 400 BR-HT-09", r["body"]["code"] == "BR-HT-09", str(r))

    ctx.close()

    # ================= S16-AC7: Quản lý xem được danh sách, KHÔNG có nút; gọi thẳng action → 403 =================
    ctx3, page3 = new_page()
    login(page3, "ql1")
    page3.wait_for_url("**/overview/")
    ok("S16-AC7: menu Quản lý CÓ 'Phiếu hoàn chờ chuyển' (chỉ không có nút)", "Phiếu hoàn chờ chuyển" in nav_labels(page3))
    page3.goto(BASE + "/orders/refunds/")
    page3.wait_for_load_state("networkidle")
    idle(page3)
    expect(page3.locator("section[aria-labelledby=refund-h]")).to_be_visible()
    q2 = refund_queue_json(page3, "ql1")
    ok("S16-AC7: available_actions rỗng với Quản lý dù phiếu đang chờ", all(x["available_actions"] == [] for x in q2["results"]), str(q2))
    if q2["results"]:
        page3.locator(f'.refund-open[data-id="{q2["results"][0]["id"]}"]').click()
        dlg3 = page3.get_by_role("dialog")
        expect(dlg3.locator(".refund-view")).to_be_visible()
        ok("S16-AC7: FE không hiện nút cho Quản lý", dlg3.locator("[data-action]").count() == 0)
        close_sheet(page3)
    ctx3.close()

    # ================= 360×640: không cuộn ngang, vùng bấm ≥ 44px (S16-AC8) =================
    for dark in (False, True):
        tag = f"360-{'dark' if dark else 'light'}"
        ctx4, page4 = new_page(width=360, height=640, dark=dark, mobile=True)
        login(page4, "loc")
        page4.wait_for_url("**/overview/")
        page4.goto(BASE + "/orders/refunds/")
        page4.wait_for_load_state("networkidle")
        idle(page4)
        fonts_ready(page4)
        ok(f"S16 {tag}: danh sách không cuộn ngang", hscroll(page4) <= 360, str(hscroll(page4)))
        small = page4.evaluate(SMALL_TAPS_JS, 360)
        ok(f"S16 {tag}: vùng bấm danh sách ≥ 44px", not small, str(small))
        page4.screenshot(path=f"{SHOTS}/s16-list-{tag}.png")
        row = page4.locator(".refund-open").first
        row.click()
        dlg4 = page4.get_by_role("dialog")
        expect(dlg4.locator(".refund-view")).to_be_visible()
        fonts_ready(page4)
        ok(f"S16 {tag}: tấm chi tiết không cuộn ngang", hscroll(page4) <= 360 and sheet_fits(page4))
        page4.screenshot(path=f"{SHOTS}/s16-detail-{tag}.png")
        act = dlg4.locator("[data-action]").first
        if act.count():
            act.click()
            fonts_ready(page4)
            ok(f"S16 {tag}: bước thao tác không cuộn ngang", sheet_fits(page4))
            small = page4.evaluate(SMALL_TAPS_JS, 360)
            ok(f"S16 {tag}: vùng bấm bước thao tác ≥ 44px", not small, str(small))
            page4.screenshot(path=f"{SHOTS}/s16-action-{tag}.png")
        ctx4.close()

    ctx5, page5 = new_page(width=360, height=640, mobile=True)
    login(page5, "loc")
    page5.wait_for_url("**/overview/")
    page5.goto(BASE + "/orders/")
    page5.wait_for_load_state("networkidle")
    idle(page5)
    ok("S14 360: tab con có 'Phiếu hoàn'", page5.locator(".orders-tabs", has_text="Phiếu hoàn chờ chuyển").count() == 1)
    ctx5.close()

    browser.close()

relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "401" not in e and "403" not in e
            and "500" not in e and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]
ok("Không lỗi console (trừ font/401/403/500 cố ý)", not relevant, str(relevant[:5]))
fails = 0
for n, c, e in results:
    print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + e))
    fails += 0 if c else 1
print(f"{len(results) - fails}/{len(results)} PASS")
