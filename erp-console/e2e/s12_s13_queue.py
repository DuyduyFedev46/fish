# E2E S12 (hàng chờ thanh toán) và S13 (phiếu hoàn từ khoản tiền lệch) trên bản build MOCK phục vụ tĩnh, theo giao diện ERP theo
# design Lô 3 (tab theo route, trang chi tiết khoản /orders/payments/detail/?id=, hộp thoại, toast). Phần giao diện đã có thêm ở
# e2e/ed_batch3_orders.py; kịch bản này giữ các luật nghiệp vụ theo contract BE: loại lệch, gắn đơn, xác nhận đơn, BR-TT-04/05/09,
# BR-HT-01/04, request_id, quyền Quản lý / NV kho.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s12_s13_queue.py      # tắt server sau khi xong
import re

from playwright.sync_api import expect, sync_playwright

from orders_common import (SHOTS, be, clear_log, dialog, fonts_ready, go, header_buttons, header_text, hscroll, idle, log, login, make_new_page,
                           nav_labels, ok, open_order, open_payment, posts, qjson, submit_btn, tab_labels, toast_text, finish)

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
QLIST = "GET /api/sales/payments/?resolution_status=OPEN"


def rows(page):
    return page.locator("tbody tr")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []

    # ================= Chủ (loc) — danh sách =================
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    clear_log(page)
    go(page, "/orders/payments/")
    expect(rows(page).first).to_be_visible()
    ok("S12: mở màn gọi GET /api/sales/payments/?resolution_status=OPEN", any(x.startswith(QLIST) for x in log(page)), str(log(page)))
    ok("S12: hàng chờ là tab của 'Đơn & tiền' (menu trái sáng đúng 1 mục)",
       tab_labels(page) == ["Đơn hàng", "Hàng chờ thanh toán", "Phiếu hoàn tiền"] and page.locator(".nav a.active").count() == 1, str(tab_labels(page)))
    j = qjson(page)
    ok("S12-AC1 (mock theo BE): hàng chờ OPEN không có MATCHED, có đủ 4 loại lệch",
       all(r["match_status"] != "MATCHED" and r["resolution_status"] == "OPEN" for r in j["results"])
       and {r["match_status"] for r in j["results"]} == {"UNDERPAID", "ORPHAN", "OVERPAID", "UNMATCHED"}, str([r["match_status"] for r in j["results"]]))
    ok("S12-AC1: số dòng = count BE (5)", rows(page).count() == j["count"] == 5, str(rows(page).count()))
    txt = rows(page).all_inner_texts()
    ok("S12-AC1: mỗi dòng có loại lệch + số tiền (đ) + mã GD",
       all("đ" in t and "FT" in t for t in txt) and any("Chuyển thiếu" in t for t in txt) and any("Không khớp đơn" in t for t in txt)
       and any("Chuyển thừa" in t for t in txt) and any("Về sau khi đơn đã huỷ" in t for t in txt), str(txt[:2]))
    ok("BR-PQ-15: JSON hàng chờ không có field giá vốn", "unit_cost" not in str(j) and "landed" not in str(j))
    # lọc loại lệch
    clear_log(page)
    page.get_by_label("Lọc theo loại khoản tiền").select_option(label="Không khớp đơn")
    expect(rows(page)).to_have_count(2)
    idle(page)
    ok("S12: lọc 'Không khớp đơn' gửi match_status=UNMATCHED", any("match_status=UNMATCHED" in x for x in log(page)), str(log(page)))
    page.get_by_label("Lọc theo loại khoản tiền").select_option(index=0)
    expect(rows(page)).to_have_count(5)

    # S12-AC4: khoản thiếu chưa đủ → chỉ 'refund'; CONFIRM_ORDER gọi thẳng → BR-TT-09
    under = next(r for r in j["results"] if r["match_status"] == "UNDERPAID")
    ok("S12-AC4: khoản thiếu chưa đủ → available_actions chỉ có refund", under["available_actions"] == ["refund"], str(under["available_actions"]))
    r = page.evaluate("([id]) => window.__caveMock.resolveJson('loc', id, {action: 'CONFIRM_ORDER', note: ''})", [under["id"]])
    o = under["order"]
    money = lambda v: f"{int(v):,}".replace(",", ".") + " ₫"
    exp = be(page, "TT_NOT_ENOUGH", {"paid": money(o["paid_total"]), "total": money(o["total_amount"])})
    ok("S12-AC4: CONFIRM_ORDER khi chưa đủ → 400 BR-TT-09 'Tổng tiền đã nhận … < tổng đơn …'", r["status"] == 400 and r["body"]["code"] == "BR-TT-09" and r["body"]["detail"] == exp, str(r))
    open_payment(page, under["id"])
    ok("S12: trang khoản thiếu hiện Còn thiếu + nút chính 'Lập phiếu hoàn' (không 'Xác nhận đơn đủ tiền')",
       "Còn thiếu" in page.locator("main").inner_text() and header_buttons(page)[:1] == ["Lập phiếu hoàn tiền"] and "Xác nhận đơn đủ tiền" not in page.locator("main").inner_text(), str(header_buttons(page)))

    # ---- S12-AC2: gắn khoản không khớp 540.000 vào đơn 101 ----
    open_payment(page, 880)
    ok("S12: khoản không khớp → 'Gắn vào đơn' là nút chính, 'Lập phiếu hoàn' trong '…'",
       header_buttons(page)[:1] == ["Gắn vào đơn"], str(header_buttons(page)))
    page.get_by_role("button", name="Gắn vào đơn").click()
    dlg = dialog(page, "Gắn khoản tiền vào đơn")
    clear_log(page)
    submit_btn(dlg).click()
    expect(dlg.get_by_text("Chọn một đơn trong danh sách để gắn.")).to_be_visible()
    ok("S12: chưa chọn đơn → báo tại chỗ, KHÔNG gọi API", posts(page) == [], str(log(page)))
    dlg.get_by_label("Tìm đơn").fill("chi hoa")
    page.wait_for_function("() => window.__caveMock.log.some(x => x.includes('q=chi'))")
    idle(page)
    pick = dlg.locator("label.check-row").first
    expect(pick).to_be_visible()
    ok("S12: bước gắn đơn tìm đơn Giữ chỗ bằng API đơn (status=BOOKED)", any("status=BOOKED" in x for x in log(page)), str(log(page)))
    ok("S12: đơn 101 (540.000 đ) được đánh dấu 'Bằng số tiền'", "Bằng số tiền" in pick.inner_text(), pick.inner_text())
    pick.click()
    dlg.get_by_label("Ghi chú").fill("Khách ghi sai nội dung CK")
    clear_log(page)
    submit_btn(dlg).dblclick()
    expect(page.locator(".toast-item").last).to_contain_text("Đã gắn vào đơn")
    idle(page)
    ok("S12: bấm đúp → chỉ 1 POST resolve", posts(page) == ["POST /api/sales/payments/880/resolve/"], str(posts(page)))
    ok("S12-AC2: khoản RESOLVED, hết nút Gắn, ghi người xử lý + ghi chú",
       "Đã xử lý" in header_text(page) and page.get_by_role("button", name="Gắn vào đơn").count() == 0 and "Khách ghi sai nội dung CK" in page.locator("main").inner_text())
    o101 = page.evaluate("() => window.__caveMock.orderJson('loc', 101)")
    ok("S12-AC2: đơn 101 chuyển Đang xử lý, có hoá đơn và giao dịch FT2626700091 Khớp",
       o101["status"] == "PROCESSING" and o101["invoice"] and any(x["bank_txn_id"] == "FT2626700091" and x["match_status"] == "MATCHED" for x in o101["payments"]), str(o101["status"]))
    page.screenshot(path=f"{SHOTS}/s12-attach-result-1280-light.png")
    go(page, "/orders/payments/")
    expect(rows(page).first).to_be_visible()
    ok("S12: danh sách tải lại, khoản 880 rời hàng chờ (còn 4)", rows(page).count() == 4 and page.locator("tbody tr", has_text="FT2626700091").count() == 0, str(rows(page).count()))
    r = page.evaluate("() => window.__caveMock.resolveJson('loc', 880, {action: 'ATTACH_TO_ORDER', order_id: 101, note: ''})")
    ok("S12-AC6: resolve lần nữa trên khoản đã đóng → 400 BR-TT-09", r["status"] == 400 and r["body"]["detail"] == be(page, "TT_ALREADY_RESOLVED"), str(r))

    # ---- S12-AC5: đơn tự huỷ trong lúc chờ → BR-TT-05 nguyên văn ----
    open_payment(page, 881)
    page.get_by_role("button", name="Gắn vào đơn").click()
    dlg = dialog(page, "Gắn khoản tiền vào đơn")
    dlg.locator("label.check-row", has_text="SO").first.wait_for()
    idle(page)
    page.evaluate("() => window.__caveMock.expireOrder(102)")
    dlg.get_by_label("Tìm đơn").fill("")
    code102 = page.evaluate("() => window.__caveMock.orderJson('loc', 102).code")
    dlg.get_by_label("Tìm đơn").fill(code102)
    page.wait_for_function("(c) => window.__caveMock.log.some(x => x.includes('q=' + encodeURIComponent(c)) || x.includes('q=' + c))", arg=code102)
    idle(page)
    # đơn 102 đã tự huỷ nên không còn trong danh sách Giữ chỗ; gọi thẳng luật mock như BE (đơn chọn trước khi hết giờ)
    r = page.evaluate("() => window.__caveMock.resolveJson('loc', 881, {action: 'ATTACH_TO_ORDER', order_id: 102, note: ''})")
    ok("S12-AC5: đơn đã tự huỷ → 400 BR-TT-05 nguyên văn", r["status"] == 400 and r["body"]["detail"] == be(page, "TT_ORDER_CANCELLED"), str(r))
    ok("S12-AC5: khoản vẫn OPEN, đơn không khôi phục",
       any(x["id"] == 881 and x["order"] is None for x in qjson(page)["results"]) and page.evaluate("() => window.__caveMock.orderJson('loc', 102).status") == "AUTO_CANCELLED")
    page.keyboard.press("Escape")
    ctx.close()

    # ---- S12-AC3: đơn 106 có 2 khoản thiếu cộng đủ → CONFIRM_ORDER đóng cả hai ----
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    total106 = int(page.evaluate("() => window.__caveMock.orderJson('loc', 106).total_amount"))
    r = page.evaluate("() => window.__caveMock.confirmJson('loc', 106, {bank_txn_id: 'FT2626799106', amount: '100000'})")
    ok("S12-AC3: chuyển bù 100.000 cho đơn 106 → vẫn thiếu, ghi UNDERPAID", r["status"] in (200, 201), str(r))
    unders = [x for x in qjson(page)["results"] if x["order"] and x["order"]["id"] == 106]
    ok("S12-AC3: đơn 106 có 2 khoản thiếu (BR-TT-04 theo từng giao dịch), tổng đã nhận = tổng đơn",
       len(unders) == 2 and all(x["match_status"] == "UNDERPAID" for x in unders) and int(unders[0]["order"]["paid_total"]) == total106, str(unders))
    ok("S12-AC3: đủ rồi → available_actions có confirm_order", all("confirm_order" in x["available_actions"] for x in unders))
    open_payment(page, unders[0]["id"])
    ok("S12-AC3: nút chính 'Xác nhận đơn đủ tiền'", header_buttons(page)[:1] == ["Xác nhận đơn đủ tiền"], str(header_buttons(page)))
    page.get_by_role("button", name="Xác nhận đơn đủ tiền").first.click()
    dlg = dialog(page, "Xác nhận đơn đã đủ tiền")
    ok("S12: không cảnh báo thiếu khi đã đủ; nêu 'cùng được đóng'", "đơn còn thiếu" not in dlg.inner_text() and "cùng được đóng" in dlg.inner_text(), dlg.inner_text()[:300])
    dlg.get_by_label("Ghi chú").fill("Khách đã chuyển bù FT2626799106")
    clear_log(page)
    submit_btn(dlg).dblclick()
    expect(page.locator(".toast-item").last).to_contain_text("Đã xác nhận đơn")
    idle(page)
    ok("S12: bấm đúp → 1 POST resolve", len(posts(page)) == 1, str(posts(page)))
    ok("S12-AC3: toast 'Đã đóng 2 khoản'", "2 khoản" in toast_text(page), toast_text(page))
    resolved = qjson(page, status="RESOLVED")["results"]
    ok("S12-AC3: CẢ HAI khoản của đơn 106 RESOLVED/CONFIRMED",
       sorted(x["id"] for x in resolved if x["order"] and x["order"]["id"] == 106 and x["resolution"] == "CONFIRMED") == sorted(x["id"] for x in unders), str(resolved))
    ctx.close()

    # ---- S13: phiếu hoàn cho khoản về sau khi đơn tự huỷ (ORPHAN) ----
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    orphan = next(x for x in qjson(page)["results"] if x["match_status"] == "ORPHAN")
    amt = int(orphan["amount"])
    open_payment(page, orphan["id"])
    ok("S13: khoản ORPHAN chỉ có nút 'Lập phiếu hoàn'", header_buttons(page) == ["Lập phiếu hoàn tiền"] and orphan["available_actions"] == ["refund"], str(header_buttons(page)))
    page.get_by_role("button", name="Lập phiếu hoàn").first.click()
    dlg = dialog(page, "Lập phiếu hoàn")
    ok("S13: số tiền mặc định = số còn được hoàn", dlg.get_by_label("Số tiền hoàn").input_value().replace(".", "") == str(amt), dlg.get_by_label("Số tiền hoàn").input_value())
    ok("S13: lý do điền sẵn theo loại lệch", dlg.get_by_label("Lý do hoàn").input_value() == "Tiền về sau khi đơn tự huỷ")
    clear_log(page)
    dlg.get_by_label("Lý do hoàn").fill("")
    submit_btn(dlg).click()
    expect(dlg.get_by_text("Nhập lý do hoàn")).to_be_visible()
    ok("S13: lý do trống → báo tại ô, KHÔNG gọi API", posts(page) == [], str(log(page)))
    dlg.get_by_label("Lý do hoàn").fill("Tiền về sau khi đơn tự huỷ")
    dlg.get_by_label("Số tiền hoàn").fill(str(amt - 100000))
    submit_btn(dlg).dblclick()
    expect(page.locator(".toast-item").last).to_contain_text("Đã lập phiếu hoàn")
    idle(page)
    ok("S13: bấm đúp → 1 POST refunds/create", posts(page) == ["POST /api/sales/refunds/create/"], str(posts(page)))
    refs = page.evaluate("([id]) => window.__caveMock.txnRefundsOf(id)", [orphan["id"]])
    ok("S13-AC1: phiếu PENDING, request_id là UUID v4", len(refs) == 1 and refs[0]["status"] == "PENDING" and UUID.match(refs[0]["request_id"] or ""), str(refs))
    after = next(x for x in qjson(page)["results"] if x["id"] == orphan["id"])
    ok("S13-AC1: khoản vẫn OPEN, còn được hoàn 100.000", after["resolution_status"] == "OPEN" and after["refundable_amount"] == "100000", str(after))
    # S13-AC3: vượt số còn hoàn
    page.get_by_role("button", name="Lập phiếu hoàn").first.click()
    dlg = dialog(page, "Lập phiếu hoàn")
    dlg.get_by_label("Số tiền hoàn").fill("150000")
    expect(dlg.get_by_text(re.compile("Nhập tối đa"))).to_be_visible()
    ok("S13-AC3: vượt số còn hoàn → báo tại ô + khoá nút chính", submit_btn(dlg).is_disabled())
    r = page.evaluate("([id]) => window.__caveMock.refundJson('loc', {payment_transaction: id, amount: '150000', reason: 'x', request_id: crypto.randomUUID()})", [orphan["id"]])
    ok("S13-AC3: gọi thẳng vượt số còn hoàn → lỗi BE nguyên văn 'tối đa 100.000 ₫'", r["status"] == 400 and r["body"]["detail"] == be(page, "HT_OVER_REFUNDABLE", {"max": "100.000 ₫"}), str(r))
    page.keyboard.press("Escape")
    # S13-AC2: phiếu được xác nhận (S16) → khoản RESOLVED/REFUNDED
    page.evaluate("([id]) => window.__caveMock.confirmRefund(id, 'FTREF1')", [refs[0]["id"]])
    ok("S13-AC2: phiếu xác nhận → khoản RESOLVED/REFUNDED", any(x["id"] == orphan["id"] and x["resolution"] == "REFUNDED" for x in qjson(page, status="RESOLVED")["results"]))
    # AC4 / AC6 / request_id
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
    r = page.evaluate("() => window.__caveMock.refundJson('loc', {payment_transaction: 881, amount: '0.5', reason: 'x', request_id: crypto.randomUUID()})")
    ok("Tối thiểu 1đ: phiếu hoàn 0,5 → 400 'Số tiền hoàn tối thiểu 1 ₫.'", r["status"] == 400 and r["body"]["detail"] == be(page, "HT_AMOUNT_MIN"), str(r))
    # OVERPAID
    over = next(x for x in qjson(page)["results"] if x["match_status"] == "OVERPAID")
    ok("P5/BR-TT-10: khoản chuyển thừa gắn đơn đã xong, chỉ còn 'refund'", over["order"] is not None and over["available_actions"] == ["refund"], str(over))
    open_payment(page, over["id"])
    ok("P5: trang chuyển thừa hiện loại 'Chuyển thừa' + đơn Hoàn tất + nút 'Lập phiếu hoàn'",
       "Chuyển thừa" in page.locator("main").inner_text() and "Hoàn tất" in page.locator("main").inner_text() and header_buttons(page)[:1] == ["Lập phiếu hoàn tiền"])
    ctx.close()

    # ---- Bổ sung tiền (L8): chuyển thừa ngay lần đầu ----
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    total102 = int(page.evaluate("() => window.__caveMock.orderJson('loc', 102).total_amount"))
    open_order(page, 102)
    page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    dlg = dialog(page, "Xác nhận đã nhận tiền")
    dlg.get_by_label("Mã giao dịch ngân hàng").fill("FT2626799600")
    dlg.get_by_label("Số tiền đã nhận").fill(str(total102 + 60000))
    ok("Bổ sung tiền: nhiều hơn tổng đơn → nhắc phần thừa vào hàng chờ", "phần thừa vào hàng chờ" in dlg.inner_text(), dlg.inner_text()[-200:])
    submit_btn(dlg).click()
    expect(page.locator(".toast-item").last).to_contain_text("chuyển thừa")
    idle(page)
    thua = [x for x in qjson(page)["results"] if x["bank_txn_id"] == "FT2626799600-THUA"]
    ok("Bổ sung tiền: hàng chờ có dòng FT…-THUA 60.000 OVERPAID/OPEN, chỉ refund, đơn Đang xử lý",
       len(thua) == 1 and thua[0]["amount"] == "60000" and thua[0]["match_status"] == "OVERPAID" and thua[0]["available_actions"] == ["refund"]
       and thua[0]["order"]["status"] == "PROCESSING" and thua[0]["order"]["paid_total"] == str(total102), str(thua))
    go(page, "/orders/payments/")
    ok("Bổ sung tiền: màn hàng chờ có dòng -THUA", page.locator("tbody tr", has_text="FT2626799600-THUA").count() == 1)
    open_payment(page, thua[0]["id"])
    page.get_by_role("button", name="Lập phiếu hoàn").first.click()
    dlg = dialog(page, "Lập phiếu hoàn")
    clear_log(page)
    # ĐỔI (QA B4, 02/10): ô tiền chỉ nhận số nguyên; '0.5' thành 5 đ (hợp lệ), nên ca biên là 0 và 00.
    for bad in ["0", "00"]:
        dlg.get_by_label("Số tiền hoàn").fill(bad)
        submit_btn(dlg).click()
        expect(dlg.get_by_text(re.compile("trở lên"))).to_be_visible()
    ok("Tối thiểu 1đ: ô phiếu hoàn 0 / 00 → báo tại ô, KHÔNG gọi API", posts(page) == [], str(log(page)))
    ctx.close()

    # ---- Trạng thái lỗi / rỗng / 403 ----
    ctx, page = make_new_page(browser, errors)
    login(page, "loc")
    go(page, "/orders/payments/")
    for mode, check in [("fail", "Thử lại"), ("empty", "Không còn khoản tiền nào chờ xử lý"), ("forbidden", "Bạn không có quyền xem mục này")]:
        page.evaluate("([m]) => window.__caveMock.payments(m)", [mode])
        page.reload()
        expect(page.get_by_text(check).first).to_be_visible()
        ok(f"S12: trạng thái '{mode}' hiện đúng", True)
        page.screenshot(path=f"{SHOTS}/s12-state-{mode}-1280-light.png")
    ctx.close()

    # ---- S12-AC7: Quản lý / NV kho ----
    for user in ("ql1", "kho1"):
        ctx, page = make_new_page(browser, errors)
        login(page, user)
        clear_log(page)
        page.goto(__import__("orders_common").BASE + "/orders/payments/")
        expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
        idle(page)
        ok(f"S12-AC7: {user} gõ URL → chặn, KHÔNG gọi /api/sales/payments/", not any("/api/sales/payments/" in x for x in log(page)), str(log(page)))
        r = page.evaluate(f"() => window.__caveMock.resolveJson('{user}', 881, {{action: 'CONFIRM_ORDER'}})")
        ok(f"S12-AC7: {user} resolve → 403", r["status"] == 403, str(r))
        go(page, "/orders/")
        expect(rows(page).first).to_be_visible()
        tabs = tab_labels(page)
        if user == "ql1":
            ok("S12/S16: ql1 thấy tab 'Đơn hàng' + 'Phiếu hoàn', không có 'Hàng chờ thanh toán'", tabs == ["Đơn hàng", "Phiếu hoàn tiền"], str(tabs))
        else:
            ok("S12: kho1 không có tab 'Hàng chờ thanh toán'", "Hàng chờ thanh toán" not in tabs, str(tabs))
        ctx.close()

    # ---- 360px ----
    for dark in (False, True):
        tag = "360-" + ("dark" if dark else "light")
        ctx, page = make_new_page(browser, errors, 360, 640, dark=dark, mobile=True)
        login(page, "loc")
        go(page, "/orders/payments/")
        expect(rows(page).first).to_be_visible()
        fonts_ready(page)
        ok(f"S12 {tag}: danh sách không cuộn ngang", hscroll(page) <= 361, str(hscroll(page)))
        page.screenshot(path=f"{SHOTS}/s12-list-{tag}.png")
        open_payment(page, 880)
        fonts_ready(page)
        ok(f"S12 {tag}: chi tiết khoản không cuộn ngang", hscroll(page) <= 361, str(hscroll(page)))
        page.get_by_role("button", name="Gắn vào đơn").click()
        dialog(page, "Gắn khoản tiền vào đơn")
        ok(f"S12 {tag}: hộp gắn đơn không cuộn ngang", hscroll(page) <= 361, str(hscroll(page)))
        page.screenshot(path=f"{SHOTS}/s12-attach-{tag}.png")
        ctx.close()

    browser.close()

finish(errors)
