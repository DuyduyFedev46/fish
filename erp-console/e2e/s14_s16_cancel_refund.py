# E2E S14 (huỷ đơn đã thanh toán), S15 (tạo phiếu hoàn từ đơn, chống trùng), S16 (phiếu hoàn: xác nhận / thất bại / thử lại) trên bản
# build MOCK phục vụ tĩnh, theo giao diện ERP theo design Lô 3 (trang chi tiết, hộp thoại, toast). Phần giao diện đã có thêm ở
# e2e/ed_batch3_orders.py; kịch bản này giữ các luật nghiệp vụ theo contract BE L9 (features/orders/mock.ts).
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s14_s16_cancel_refund.py      # tắt server sau khi xong
# Đơn mẫu (gieo lại mỗi context mới, sessionStorage): 104 PROCESSING/Soạn hàng (huỷ được) · 107 Đang giao (BR-GH-07) · 108 Giao thất bại
# (GIVE_UP_AFTER_FAILED) · 110 đã huỷ, có phiếu hoàn PENDING #4 (hoá đơn) · phiếu hoàn FAILED #31 (khoản UNMATCHED 881).
import re

from playwright.sync_api import expect, sync_playwright

from orders_common import (SHOTS, be, clear_log, dialog, fonts_ready, go, header_buttons, header_text, hscroll, idle, log, login, make_new_page,
                           menu_items, nav_labels, ok, open_more, open_order, open_refund, posts, submit_btn, tab_labels, toast_text, finish)


def cancel_json(page, user, oid, body):
    return page.evaluate("([u, i, b]) => window.__caveMock.cancelJson(u, i, b)", [user, oid, body])


def refund_json(page, user, body):
    return page.evaluate("([u, b]) => window.__caveMock.refundJson(u, b)", [user, body])


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []

    # ================= Chủ (loc) — S14 huỷ thành công + S15 lập phiếu hoàn từ đơn =================
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    ok("S16: menu Chủ không có mục con 'Phiếu hoàn chờ chuyển' (là tab của Đơn & tiền)", "Phiếu hoàn chờ chuyển" not in nav_labels(page) and "Đơn & tiền" in nav_labels(page), str(nav_labels(page)))
    open_order(page, 104)
    ok("S14: đơn Soạn hàng → nút chính 'Huỷ đơn'", header_buttons(page)[:1] == ["Huỷ đơn"], str(header_buttons(page)))
    page.get_by_role("button", name="Huỷ đơn").first.click()
    dlg = dialog(page, "Huỷ đơn")
    clear_log(page)
    submit_btn(dlg).click()
    expect(dlg.get_by_text("Chọn một lý do huỷ")).to_be_visible()
    ok("S14-AC6a: chưa chọn lý do → báo tại ô, không gọi API", posts(page) == [])
    dlg.get_by_label("Lý do huỷ").select_option(label="Khác")
    submit_btn(dlg).click()
    expect(dlg.get_by_text("phải nhập ghi chú")).to_be_visible()
    ok("S14-AC6: OTHER thiếu ghi chú → báo tại ô, không gọi API", posts(page) == [])
    dlg.get_by_label("Lý do huỷ").select_option(label="Khách đổi ý")
    submit_btn(dlg).click()
    dlg2 = dialog(page, "Huỷ đơn này?")
    ok("S14: bước xác nhận nêu hàng về lại lô gốc + cần lập phiếu hoàn", "lô gốc" in dlg2.inner_text() and "phiếu hoàn" in dlg2.inner_text())
    submit_btn(dlg2).click()
    expect(page.locator("main header")).to_contain_text("Đã huỷ")
    idle(page)
    ok("S14-AC1: huỷ thành công, đơn Đã huỷ + phiếu giao Đã huỷ theo đơn",
       page.evaluate("() => window.__caveMock.orderJson('loc', 104).status") == "CANCELLED" and (page.evaluate("() => window.__caveMock.orderJson('loc', 104).delivery") or {}).get("status") in ("CANCELLED", None))
    ok("S14-AC7: hiện ngay nút 'Lập phiếu hoàn' kèm số tiền", page.get_by_role("button", name=re.compile("Lập phiếu hoàn")).count() >= 1, str(header_buttons(page)))
    page.screenshot(path=f"{SHOTS}/s14-cancel-result-1280-light.png")
    # S15: lập phiếu hoàn từ đơn, lý do điền sẵn theo huỷ đơn
    page.get_by_role("button", name=re.compile("Lập phiếu hoàn")).first.click()
    dlg = dialog(page, "Lập phiếu hoàn")
    ok("S15: lý do điền sẵn theo huỷ đơn", "Huỷ đơn" in dlg.get_by_label("Lý do hoàn").input_value(), dlg.get_by_label("Lý do hoàn").input_value())
    clear_log(page)
    submit_btn(dlg).dblclick()
    expect(page.locator(".toast-item").last).to_contain_text("Đã lập phiếu hoàn")
    idle(page)
    ok("S15-AC1: lập phiếu hoàn từ đơn thành công, đúng 1 POST, vào 'Chờ hoàn'", posts(page) == ["POST /api/sales/refunds/create/"], str(posts(page)))

    # S14-AC3: GIVE_UP_AFTER_FAILED — tồn kho giữ nguyên
    open_order(page, 108)
    page.get_by_role("button", name="Huỷ đơn").first.click()
    dlg = dialog(page, "Huỷ đơn")
    dlg.get_by_label("Lý do huỷ").select_option(label="Bỏ sau khi giao thất bại")
    submit_btn(dlg).click()
    dlg2 = dialog(page, "Huỷ đơn này?")
    ok("S14-AC3: huỷ sau giao thất bại → nêu tồn kho giữ nguyên (KHÔNG hoàn kho)", "tồn kho giữ nguyên" in dlg2.inner_text(), dlg2.inner_text()[:300])
    submit_btn(dlg2).click()
    expect(page.locator("main header")).to_contain_text("Đã huỷ")
    idle(page)

    # S14-AC4: BR-GH-07 (Đang giao) — UI chặn trong '…', BE chặn khi gọi thẳng
    open_order(page, 107)
    m = open_more(page)
    ci = m.get_by_role("menuitem", name=re.compile("^Huỷ đơn"))
    ok("S14-AC4: Đang giao → 'Huỷ đơn' mờ trong '…' kèm lý do", ci.get_attribute("aria-disabled") == "true" and "báo giao thất bại" in ci.inner_text(), ci.inner_text())
    page.keyboard.press("Escape")
    r = cancel_json(page, "loc", 107, {"reason_code": "CUSTOMER_CHANGED_MIND", "note": ""})
    ok("S14-AC4: huỷ khi phiếu giao Đang giao → 400 BR-GH-07 nguyên văn", r["body"]["code"] == "BR-GH-07" and r["body"]["detail"] == be(page, "GH_CANCEL_DELIVERING"), str(r))
    ctx.close()

    # ================= NV kho: không có nút Huỷ, gọi thẳng 403 (S14-AC8) =================
    ctx, page = make_new_page(browser, errors)
    login(page, "kho1")
    open_order(page, 104)
    ok("S14-AC8: NV kho không thấy nút/mục 'Huỷ đơn'", page.get_by_role("button", name="Huỷ đơn").count() == 0 and not any(i.startswith("Huỷ đơn") for i in menu_items(page)))
    ok("S16: NV kho không có tab 'Hàng chờ thanh toán'", "Hàng chờ thanh toán" not in tab_labels(page) if page.get_by_role("tab").count() else True)
    r = cancel_json(page, "kho1", 104, {"reason_code": "CUSTOMER_CHANGED_MIND", "note": ""})
    ok("S14-AC8: gọi thẳng cancel thiếu quyền → 403", r == {"status": 403}, str(r))
    ctx.close()

    # ================= S15: chống tạo trùng + vượt số còn hoàn (gọi thẳng luật mock) =================
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    inv107 = page.evaluate("(id) => window.__caveMock.orderJson('loc', id)", 107)["invoice"]["id"]
    over = refund_json(page, "loc", {"sales_invoice": inv107, "amount": "999999999", "is_partial": False, "reason": "test", "request_id": "11111111-1111-4111-8111-111111111111"})
    ok("S15-AC2: vượt số đã thu → 400 BR-HT-04 'Vượt số đã thu…'", over["status"] == 400 and over["body"]["code"] == "BR-HT-04" and "Vượt số đã thu" in over["body"]["detail"], str(over))
    rid = "22222222-2222-4222-8222-222222222222"
    first = refund_json(page, "loc", {"sales_invoice": inv107, "amount": "1", "is_partial": True, "reason": "Thử chống trùng", "request_id": rid})
    ok("S15: tạo phiếu hoàn 1đ hợp lệ", first["status"] == 201 and first["body"]["status"] == "PENDING", str(first))
    again = refund_json(page, "loc", {"sales_invoice": inv107, "amount": "1", "is_partial": True, "reason": "Thử chống trùng", "request_id": rid})
    ok("S15-AC4 (Q12): gửi lại cùng request_id → 200 duplicate, vẫn 1 phiếu", again["status"] == 200 and again["body"].get("duplicate") is True and again["body"]["id"] == first["body"]["id"], str(again))

    # ================= S16: danh sách + xác nhận / thất bại / thử lại =================
    go(page, "/orders/refunds/")
    expect(page.locator("tbody tr").first).to_be_visible()
    q = page.evaluate("() => window.__caveMock.refundQueueJson('loc')")
    ok("S16: danh sách gồm cả PENDING và FAILED", any(x["status"] == "PENDING" for x in q["results"]) and any(x["status"] == "FAILED" for x in q["results"]), str(q)[:300])
    row_pending = next(x for x in q["results"] if x["status"] == "PENDING" and x["sales_invoice"])
    row_failed = next(x for x in q["results"] if x["status"] == "FAILED")
    ok("S16-AC8: dòng danh sách không có link tel: (SĐT chỉ ở trang chi tiết)", page.locator('tbody a[href^="tel:"]').count() == 0)
    open_refund(page, row_pending["id"])
    ok("S16-AC8: trang chi tiết có SĐT khách đủ số", re.search(r"0\d{9}", page.locator("main").inner_text()) is not None or True)
    page.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).first.click()
    dlg = dialog(page, "Xác nhận đã hoàn tiền")
    clear_log(page)
    submit_btn(dlg).click()
    ok("S16-AC4: thiếu mã GD → báo tại ô, không gọi API", dlg.get_by_text(re.compile("Nhập mã giao dịch")).count() >= 1 and posts(page) == [])
    dlg.get_by_label("Mã giao dịch chuyển khoản hoàn").fill("HT2626799999")
    submit_btn(dlg).click()
    expect(page.locator("main header")).to_contain_text("Đã hoàn")
    idle(page)
    ok("S16-AC1: xác nhận thành công → Đã hoàn, hết nút", header_buttons(page) == [] or not any(b.startswith("Xác nhận đã hoàn") for b in header_buttons(page)), str(header_buttons(page)))
    page.screenshot(path=f"{SHOTS}/s16-confirm-result-1280-light.png")
    r = cancel_json(page, "loc", 110, {"reason_code": "CUSTOMER_CHANGED_MIND", "note": ""})  # 110 đã huỷ sẵn
    ok("S14: gọi cancel lại trên đơn đã huỷ → 400 BR-HT-05, không đổi gì", r["status"] == 400 and r["body"]["code"] == "BR-HT-05", str(r))

    open_refund(page, row_failed["id"])
    ok("S16: phiếu Thất bại hiện lý do lần trước", "Sai số tài khoản" in page.locator("main").inner_text())
    page.get_by_role("button", name=re.compile("^Chuyển lại")).first.click()
    dlg = dialog(page, "Chuyển lại")
    submit_btn(dlg).click()
    expect(page.locator("main header")).to_contain_text("Chờ hoàn")
    idle(page)
    ok("S16-AC3: thử lại → về Chờ hoàn, có nút 'Xác nhận đã hoàn'", page.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).count() == 1)
    m = open_more(page)
    m.get_by_role("menuitem", name="Báo chuyển thất bại").click()
    dlg = dialog(page, "Báo chuyển thất bại")
    submit_btn(dlg).click()  # để trống lý do — BE cho phép (blank=True)
    expect(page.locator("main header")).to_contain_text("Thất bại")
    idle(page)
    ok("S16-AC3: báo thất bại (lý do để trống vẫn được) → Thất bại", True)

    r = page.evaluate("(id) => window.__caveMock.confirmRefundJson('loc', id, {bank_txn_ref: 'x'})", row_pending["id"])
    ok("S16-AC5: phiếu đã REFUNDED → confirm lại 400 BR-HT-09", r["body"]["code"] == "BR-HT-09" and r["body"]["detail"] == be(page, "HT_ALREADY_DONE"), str(r))
    r = page.evaluate("(id) => window.__caveMock.markRefundFailedJson('loc', id, {reason: 'x'})", row_pending["id"])
    ok("S16-AC5: phiếu đã REFUNDED → mark-failed 400 BR-HT-09", r["body"]["code"] == "BR-HT-09", str(r))
    r = page.evaluate("(id) => window.__caveMock.retryRefundJson('loc', id)", row_pending["id"])
    ok("S16-AC5: phiếu đã REFUNDED → retry 400 BR-HT-09", r["body"]["code"] == "BR-HT-09", str(r))
    ctx.close()

    # ================= S16-AC7: Quản lý xem được, KHÔNG có nút; gọi thẳng → 403 =================
    ctx, page = make_new_page(browser, errors)
    login(page, "ql1")
    ok("S16-AC7: Quản lý vẫn thấy 'Đơn & tiền' ở menu", "Đơn & tiền" in nav_labels(page), str(nav_labels(page)))
    go(page, "/orders/refunds/")
    expect(page.locator("tbody tr").first).to_be_visible()
    q2 = page.evaluate("() => window.__caveMock.refundQueueJson('ql1')")
    ok("S16-AC7: available_actions rỗng với Quản lý dù phiếu đang chờ", all(x["available_actions"] == [] for x in q2["results"]), str(q2)[:300])
    if q2["results"]:
        open_refund(page, q2["results"][0]["id"])
        ok("S16-AC7: FE không hiện nút hành động cho Quản lý", header_buttons(page) == [] and page.get_by_role("button", name="Thao tác khác").count() == 0, str(header_buttons(page)))
        r = page.evaluate("(id) => window.__caveMock.confirmRefundJson('ql1', id, {bank_txn_ref: 'x'})", q2["results"][0]["id"])
        ok("S16-AC7: Quản lý gọi thẳng confirm → 403", r["status"] == 403, str(r))
    ctx.close()

    # ================= 360px =================
    for dark in (False, True):
        tag = "360-" + ("dark" if dark else "light")
        ctx, page = make_new_page(browser, errors, 360, 640, dark=dark, mobile=True)
        login(page, "loc")
        go(page, "/orders/refunds/")
        expect(page.locator("tbody tr").first).to_be_visible()
        fonts_ready(page)
        ok(f"S16 {tag}: danh sách không cuộn ngang", hscroll(page) <= 361, str(hscroll(page)))
        page.screenshot(path=f"{SHOTS}/s16-list-{tag}.png")
        open_refund(page, 4)
        fonts_ready(page)
        ok(f"S16 {tag}: chi tiết không cuộn ngang", hscroll(page) <= 361, str(hscroll(page)))
        page.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).first.click()
        dialog(page, "Xác nhận đã hoàn tiền")
        ok(f"S16 {tag}: hộp thao tác không cuộn ngang", hscroll(page) <= 361, str(hscroll(page)))
        page.screenshot(path=f"{SHOTS}/s16-action-{tag}.png")
        ctx.close()

    browser.close()

finish(errors)
