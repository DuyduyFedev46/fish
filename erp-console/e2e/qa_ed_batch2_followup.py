# QA ERP theo design, Lô 2 FE lần 2: kiểm lại các lỗi đã sửa (B1 chữ tự do, B2 đơn vị, B3 khung hỏi nhanh, B4 bấm 3 lần, B5 ô trống,
# M1 409, M2 tải chi tiết lỗi) bằng ca NGOÀI đường thuận. Chỉ dữ liệu giả.
#   Phần A (apiFetch thật, Playwright chặn mạng): khung riêng cổng 3103 (xem qa_ed_batch2_harness.py cách dựng).
#   Phần B (bản mock, panel AI thật): `python3 -m http.server 3101` trong erp-console/out (build NEXT_PUBLIC_USE_MOCK=1).
#   SHOTS=../doc/features/2026-10-01-erp-theo-design/shots/lot2 python3 e2e/qa_ed_batch2_followup.py
import os
import re
import sys

HARNESS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa_ed_batch2_harness.py"), encoding="utf-8").read()
exec(HARNESS.rsplit("with sync_playwright() as p:", 1)[0])  # dùng lại helper: ok, reply, new_ctx, open_mode, ai_routes, ACTION, NOW_MINUS

MOCK = os.environ.get("MOCK_BASE", "http://127.0.0.1:3101")
FAKE_PHONE = "0900000123"


def panel_text(page):
    return page.locator("[data-ai-block]").inner_text()


# ---------------------------------------------------------------- Phần A
def a_b1_b2(browser, errors):
    # B1: chữ tự do (note và các khoá cùng loại) KHÔNG hiện; nhiều cách ghi SĐT/tên giả
    free_keys = {
        "note": f"Giao cho Nguyễn Văn A, SĐT {FAKE_PHONE}",
        "reason": f"Khách {FAKE_PHONE} đổi ý",
        "description": "Gọi anh Bình 0900000456",
        "message": "12 đường Thử, quận 1",
        "comment": "Chị Lan",
        "customer_name": "Trần Thị B",
        "phone": FAKE_PHONE,
        "delivery_address": "34 đường Giả",
        "unit_cost": "555111",
        "landed_unit_cost": "666222",
        "purchase_rate": "777333",
    }
    ctx, page = new_ctx(browser, errors=errors)
    args = {"item_code": "CA-001", "qty": "10.000", **free_keys}
    ai_routes(page, args=args)
    open_mode(page, "ai")
    card = page.locator("[data-proposal]"); expect(card).to_be_visible()
    t = card.inner_text()
    leaked = [v for v in free_keys.values() if v in t] + [x for x in ("Nguyễn", "Trần Thị", "đường", "Bình", "Lan") if x in t]
    ok("B1 args_preview có note/reason/description/message/comment/tên/SĐT/địa chỉ/giá vốn: KHÔNG giá trị nào hiện ra", not leaked, str(leaked) + " | " + t.replace("\n", " | ")[:200])
    ok("B1 vẫn hiện khoá có cấu trúc (Mã hàng, Số lượng)", "Mã hàng" in t and "CA-001" in t and "Số lượng" in t)
    ok("B1 DOM toàn khối không chứa SĐT giả (kể cả thuộc tính ẩn)", FAKE_PHONE not in page.locator("[data-ai-block]").evaluate("e => e.outerHTML"))
    page.screenshot(path=f"{SHOTS}/qa2-ai-note-pii-desktop.png")
    ctx.close()
    # SĐT giả nằm trong khoá ngoài danh sách nhưng cũng trong toàn bộ body trang: không trong localStorage/URL/console
    ctx, page = new_ctx(browser, errors=errors)
    msgs = []
    page.on("console", lambda m: msgs.append(m.text))
    ai_routes(page, args={"item_code": "CA-001", "qty": "1.000", "note": f"SĐT {FAKE_PHONE}"})
    open_mode(page, "ai"); expect(page.locator("[data-proposal]")).to_be_visible()
    st = page.evaluate("() => JSON.stringify([localStorage, sessionStorage, location.href])")
    ok("B1 SĐT giả không vào localStorage/sessionStorage/URL/console", FAKE_PHONE not in st and not any(FAKE_PHONE in m for m in msgs), st[:200])
    ctx.close()

    # B2: định dạng số lượng và tiền, biên
    cases = [
        ({"qty": "10.000"}, "Số lượng", "10 kg"),
        ({"qty": "0.500"}, "Số lượng", "0,5 kg"),
        ({"qty": "12.345"}, "Số lượng", "12,345 kg"),
        ({"quantity": "2.500"}, "Số lượng", "2,5 kg"),
        ({"qty": 7}, "Số lượng", "7 kg"),
        ({"qty": "1250.000"}, "Số lượng", "1.250 kg"),
        ({"refund_amount": "150000.00"}, "Số tiền hoàn", "150.000 đ"),
    ]
    for extra, label, want in cases:
        ctx, page = new_ctx(browser, errors=errors)
        ai_routes(page, args={"item_code": "CA-001", **extra})
        open_mode(page, "ai"); card = page.locator("[data-proposal]"); expect(card).to_be_visible()
        t = card.inner_text().replace("\n", " | ")
        ok(f"B2 {extra} -> '{want}'", f"{label} | {want}" in t, t[:160])
        ctx.close()
    for extra in ({"qty": "abc"}, {"qty": ""}, {"qty": None}, {"qty": {"x": 1}}, {"qty": True}):
        ctx, page = new_ctx(browser, errors=errors)
        ai_routes(page, args={"item_code": "CA-001", **extra})
        open_mode(page, "ai"); card = page.locator("[data-proposal]"); expect(card).to_be_visible()
        t = card.inner_text()
        ok(f"B2 giá trị lạ {extra}: bỏ dòng, không in chuỗi thô/NaN/undefined/[object", "Số lượng" not in t and not re.search(r"NaN|undefined|null|\[object|abc", t), t.replace("\n", " | ")[:140])
        ctx.close()
    ctx, page = new_ctx(browser, errors=errors)
    ai_routes(page, args={"item_code": "CA-001", "qty": "-3.000"})
    open_mode(page, "ai"); card = page.locator("[data-proposal]"); expect(card).to_be_visible()
    t = card.inner_text().replace("\n", " | ")
    ok("B2 biên: qty âm vẫn hiện có đơn vị (người duyệt thấy bất thường)", "kg" in t, t[:120])
    ctx.close()
    # args rỗng / null: không vỡ
    for a in ({}, None):
        ctx, page = new_ctx(browser, errors=errors)
        ai_routes(page, args=a if a is not None else {})
        open_mode(page, "ai"); card = page.locator("[data-proposal]"); expect(card).to_be_visible()
        ok(f"B2 args_preview {a!r}: thẻ đề xuất vẫn hiện nút Từ chối/Đồng ý", card.get_by_role("button", name="Từ chối", exact=True).count() == 1)
        ctx.close()


def a_m1(browser, errors):
    # 02b: xung đột = code STALE_STATE/STALE_VERSION (mọi status) HOẶC 409 có updated_at. Còn lại là lỗi thường.
    cases = [
        (409, {"detail": "Phiếu đã đổi.", "code": "STALE_STATE"}, True, "409 + STALE_STATE"),
        (400, {"detail": "Phiếu đã đổi.", "code": "STALE_STATE"}, True, "400 + STALE_STATE (kiểu của delivery)"),
        (409, {"detail": "Phiếu đã đổi.", "code": "STALE_VERSION"}, True, "409 + STALE_VERSION"),
        (409, {"detail": "Phiếu đã đổi.", "updated_at": "2026-10-02T03:30:00Z", "updated_by_name": "Hạnh"}, True, "409 trơn có updated_at"),
        (409, {"detail": "Phiếu đang có người nhận xử lý.", "code": "CLAIMED"}, False, "409 CLAIMED"),
        (409, {"detail": "Cảnh báo nội dung.", "code": "CONTENT_WARNINGS"}, False, "409 CONTENT_WARNINGS"),
        (409, {"detail": "Đã xử lý rồi."}, False, "409 trơn không mã"),
        (500, {"detail": "boom"}, False, "500"),
    ]
    for status, body, is_conflict, name in cases:
        ctx, page = new_ctx(browser, errors=errors)
        page.route(API + "/**", (lambda st, b: lambda r: reply(r, st, b))(status, body))
        open_mode(page, "form")
        page.get_by_label("Số lượng").fill("40")
        page.get_by_role("button", name=re.compile("^(Lưu|Gửi)")).first.click()
        page.wait_for_timeout(500)
        banner = page.locator("[data-conflict-banner]").count()
        alert = page.locator("[data-form-alert]").count()
        t = page.locator("body").inner_text()
        ok(f"M1 {name}: {'banner xung đột' if is_conflict else 'alert thường, KHÔNG banner'}", (banner == 1 and alert == 0) if is_conflict else (banner == 0 and alert == 1), f"banner={banner} alert={alert}")
        ok(f"M1 {name}: giá trị đang gõ '40' còn", page.get_by_label("Số lượng").input_value() == "40")
        if not is_conflict and status == 409:
            ok(f"M1 {name}: giữ lý do của BE", body["detail"][:12] in t, t[:0])
        ok(f"M1 {name}: không in undefined/null/NaN/Invalid", not re.search(r"undefined|\bnull\b|NaN|Invalid", t))
        if name == "409 + STALE_STATE":
            page.screenshot(path=f"{SHOTS}/qa2-conflict-banner-desktop.png")
        if name == "409 CLAIMED":
            page.screenshot(path=f"{SHOTS}/qa2-claimed-plain-error-desktop.png")
        ctx.close()
    # sau 409 xung đột, nút Tải lại bấm được; sau lỗi thường nút chính là "Thử lại"
    ctx, page = new_ctx(browser, errors=errors)
    page.route(API + "/**", lambda r: reply(r, 409, {"detail": "Phiếu đang có người nhận xử lý.", "code": "CLAIMED"}))
    open_mode(page, "form")
    page.get_by_label("Số lượng").fill("40")
    page.get_by_role("button", name=re.compile("^(Lưu|Gửi)")).first.click(); page.wait_for_timeout(400)
    ok("M1 CLAIMED: nút chính thành 'Thử lại' (gửi lại được)", page.get_by_role("button", name="Thử lại", exact=True).count() == 1)
    ctx.close()


def a_m2(browser, errors):
    # chi tiết đề xuất tải lỗi -> báo lỗi + Thử lại, Đồng ý khoá, Từ chối vẫn dùng, bộ đếm không chạy mãi
    for label, resp in (("500", (500, {"detail": "boom"})), ("404", (404, {"detail": "x"}))):
        ctx, page = new_ctx(browser, errors=errors)
        log = ai_routes(page, detail=resp)
        open_mode(page, "ai")
        block = page.locator("[data-ai-block]"); expect(block).to_be_visible()
        page.wait_for_timeout(1200)
        t = block.inner_text().replace("\n", " | ")
        ok(f"M2 chi tiết {label}: hiện lỗi tiếng Việt + 'Thử lại'", block.locator("[role=alert]").count() >= 1 and block.get_by_role("button", name="Thử lại").count() >= 1, t[:220])
        card = block.locator("[data-proposal]")
        ok(f"M2 chi tiết {label}: nút Đồng ý khoá, nhãn trơn (không kẹt 'Đồng ý (3)')", card.count() == 1 and card.get_by_role("button", name="Đồng ý", exact=True).is_disabled() and "Đồng ý (" not in card.inner_text(), card.inner_text().replace("\n", " | ")[:140])
        page.wait_for_timeout(4200)
        ok(f"M2 chi tiết {label}: sau 4 giây vẫn khoá, vẫn không số đếm", card.get_by_role("button", name="Đồng ý", exact=True).is_disabled() and "Đồng ý (" not in card.inner_text())
        n_before = len([x for x in log if x.endswith("/confirm/")])
        card.get_by_role("button", name="Đồng ý", exact=True).click(force=True)
        page.wait_for_timeout(300)
        ok(f"M2 chi tiết {label}: bấm Đồng ý (bị khoá) không gọi /confirm/", len([x for x in log if x.endswith("/confirm/")]) == n_before)
        ok(f"M2 chi tiết {label}: Từ chối vẫn dùng được", card.get_by_role("button", name="Từ chối", exact=True).is_enabled())
        page.screenshot(path=f"{SHOTS}/qa2-ai-detail-error-{label}-desktop.png")
        ctx.close()
    # Thử lại: lần 1 lỗi, lần 2 thành công -> Đồng ý mở sau thời gian chờ; spam Thử lại không sinh nhiều chi tiết
    ctx, page = new_ctx(browser, errors=errors)
    state = {"n": 0}
    log = []
    def h(route):
        req = route.request
        if req.method == "OPTIONS":
            return reply(route)
        path = req.url.replace(API, ""); log.append(f"{req.method} {path}")
        if path.startswith("/api/ai/status"):
            return reply(route, 200, {"ai_enabled": True})
        if re.match(r"/api/ai/actions/\?", path):
            return reply(route, 200, {"count": 1, "next": None, "previous": None, "results": [dict(ACTION)]})
        if path.endswith("/confirm/"):
            return reply(route, 200, {"status": "DONE"})
        if re.match(r"/api/ai/actions/[\w-]+/$", path):
            state["n"] += 1
            if state["n"] == 1:
                return reply(route, 500, {"detail": "boom"})
            row = dict(ACTION); row["confirm_nonce"] = "n"; row["viewable_from"] = NOW_MINUS(0)
            return reply(route, 200, row)
        return reply(route, 404, {})
    page.route(API + "/**", h)
    open_mode(page, "ai")
    block = page.locator("[data-ai-block]"); expect(block.get_by_role("button", name="Thử lại")).to_be_visible()
    block.get_by_role("button", name="Thử lại").click()
    card = block.locator("[data-proposal]")
    ok("M2 Thử lại thành công: lỗi biến mất", block.locator("[role=alert]").count() == 0, block.inner_text().replace("\n", " | ")[:140])
    expect(card.get_by_role("button", name="Đồng ý", exact=True)).to_be_enabled(timeout=8000)
    ok("M2 Thử lại: Đồng ý mở sau thời gian chờ, tải chi tiết đúng 2 lần (1 lỗi + 1 thành công)", state["n"] == 2, str(state["n"]))
    ctx.close()


def a_b4(browser, errors):
    # B4: ref chặn bấm 3 lần trong một nhịp, với cả confirm/reject, sau đó lỗi -> mở khoá lại được
    for kind, name in (("confirm", "Đồng ý"), ("reject", "Từ chối")):
        ctx, page = new_ctx(browser, errors=errors)
        log = ai_routes(page)
        open_mode(page, "ai")
        card = page.locator("[data-proposal]"); expect(card).to_be_visible()
        expect(card.get_by_role("button", name="Đồng ý", exact=True)).to_be_enabled(timeout=8000)
        page.evaluate("(n) => { const b=[...document.querySelectorAll('[data-proposal] button')].find(x=>x.textContent.trim()===n); for (let i=0;i<5;i++) b.click(); }", name)
        page.wait_for_timeout(700)
        n = len([x for x in log if x.endswith(f"/{kind}/")])
        ok(f"B4 '{name}' bấm 5 lần cùng một tác vụ JS -> đúng 1 POST", n == 1, str(n))
        ctx.close()
    # confirm lỗi 500 xong: bấm lại được (ref đã thả)
    ctx, page = new_ctx(browser, errors=errors)
    log = ai_routes(page, confirm=(500, {"detail": "boom"}))
    open_mode(page, "ai")
    card = page.locator("[data-proposal]"); expect(card).to_be_visible()
    btn = card.get_by_role("button", name="Đồng ý", exact=True); expect(btn).to_be_enabled(timeout=8000)
    btn.click(); page.wait_for_timeout(500)
    btn.click(); page.wait_for_timeout(500)
    ok("B4 sau lỗi 500, ref được thả: bấm lại gửi lần 2 (tổng 2 POST)", len([x for x in log if x.endswith("/confirm/")]) == 2, str(log[-4:]))
    ctx.close()
    # Từ chối bị 409 -> thông báo, ref thả, danh sách tải lại
    ctx, page = new_ctx(browser, errors=errors)
    log = ai_routes(page, reject=(409, {"detail": "x"}))
    open_mode(page, "ai")
    card = page.locator("[data-proposal]"); expect(card).to_be_visible()
    card.get_by_role("button", name="Từ chối", exact=True).click(); page.wait_for_timeout(500)
    ok("B4 Từ chối 409: báo 'đã được xử lý hoặc hết hạn' + tải lại danh sách", "đã được xử lý hoặc hết hạn" in panel_text(page) and len([x for x in log if "/actions/?" in x]) >= 2, panel_text(page).replace("\n", " | ")[:200])
    ctx.close()


# ---------------------------------------------------------------- Phần B (bản mock, panel AI thật)
def mock_login(page):
    page.goto(MOCK + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill("loc")
    page.get_by_label("Mật khẩu").fill("demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.ai === 'function'", timeout=15_000)


def mock_demo(page, ai, consent):
    mock_login(page)
    page.evaluate("([a, c]) => { window.__caveMock.ai(a ? 'on' : 'off'); window.__caveMock.aiConsent(c); }", [ai, consent])
    page.goto(MOCK + "/dev-patterns/")
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)
    page.evaluate("() => window.__caveMock.clearLog()")


def mlog(page):
    return page.evaluate("() => window.__caveMock.log.slice().map(String)")


def b_b3(browser, errors):
    # AI tắt: không khung hỏi nhanh, không /api/ai/* ngoài tối đa 1 status
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    urls = []
    page.on("request", lambda r: urls.append(r.url))
    mock_demo(page, ai=False, consent=True)
    page.wait_for_timeout(800)
    ai = [x for x in mlog(page) if "/api/ai" in x]
    ok("B3 AI tắt: không khối AI, không khung hỏi nhanh, không ô 'Hỏi AI'", page.locator("[data-ai-block]").count() == 0 and page.locator("[data-ai-starter]").count() == 0 and page.get_by_placeholder(re.compile("Hỏi AI")).count() == 0)
    ok("B3 AI tắt: /api/ai/* chỉ tối đa 1 GET status, không actions/chat/commands/summary", set(ai) <= {"GET /api/ai/status/"} and len(ai) <= 1, str(ai))
    ok("B3 AI tắt: không tải chunk model/worker (wllama, .gguf, worker)", not any(re.search(r"wllama|\.gguf|worker", u, re.I) for u in urls))
    page.screenshot(path=f"{SHOTS}/qa2-ai-off-desktop.png")
    ctx.close()

    # AI bật + đã đồng ý: khung hiện sẵn; panel CHƯA nạp
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    msgs = []
    page.on("console", lambda m: msgs.append(m.text))
    urls = []
    page.on("request", lambda r: urls.append(r.url))
    mock_demo(page, ai=True, consent=True)
    st = page.locator("[data-ai-starter]"); expect(st).to_be_visible()
    ok("B3 khung hỏi nhanh hiện sẵn: 2 chip, ô nhập 'Hỏi AI về chứng từ này', nút gửi", st.locator("button").count() == 3 and page.get_by_label("Hỏi AI về chứng từ này").count() == 1 and page.get_by_role("button", name="Gửi câu hỏi").count() == 1, st.inner_text().replace("\n", " | "))
    ok("B3 nút gửi khoá khi ô trống", page.get_by_role("button", name="Gửi câu hỏi").is_disabled())
    ok("B3 chưa chạm: panel chưa nạp (không 'TRỢ LÝ VẬN HÀNH'), 0 request commands/chat", "TRỢ LÝ VẬN HÀNH" not in page.locator("main").inner_text().upper() and not any(("/commands" in x or "chat" in x) for x in mlog(page)), str(mlog(page))[:240])
    page.screenshot(path=f"{SHOTS}/qa2-ai-starter-desktop.png")
    # gõ trong ô tĩnh KHÔNG làm gì ngoài focus -> panel nạp
    inp = page.get_by_label("Hỏi AI về chứng từ này")
    inp.click(); page.wait_for_timeout(1500)
    ok("B3 chạm ô: panel nạp, khung tĩnh nhường chỗ (còn đúng 1 ô nhập hỏi)", page.locator("[data-ai-starter]").count() == 0 and "TRỢ LÝ VẬN HÀNH" in page.locator("[data-ai-block]").inner_text().upper())
    focused = page.evaluate("() => { const a=document.activeElement; return a ? a.tagName + ':' + (a.getAttribute('aria-label')||a.placeholder||'') : '' }")
    ok("B3 chạm ô: focus chuyển sang ô nhập của panel (gõ tiếp được)", focused.startswith(("INPUT", "TEXTAREA")), focused)
    page.keyboard.type("còn bao nhiêu cá thu")
    ok("B3 gõ tiếp: chữ vào ô panel đủ, không mất ký tự", page.evaluate("() => document.activeElement.value") == "còn bao nhiêu cá thu", page.evaluate("() => document.activeElement.value"))
    page.screenshot(path=f"{SHOTS}/qa2-ai-focus-panel-desktop.png")
    ctx.close()

    # Bấm chip -> panel nạp và gửi câu
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    mock_demo(page, ai=True, consent=True)
    chip = page.locator("[data-ai-starter] button").first
    q = chip.inner_text()
    chip.dblclick(); page.wait_for_timeout(2500)
    t = page.locator("[data-ai-block]").inner_text()
    ok("B3 bấm chip (kể cả bấm đúp): panel nạp và câu hỏi được gửi ĐÚNG 1 lần", t.count(q) == 1 and "TRỢ LÝ VẬN HÀNH" in t.upper(), f"count={t.count(q)}")
    ok("B3 bấm chip: có câu trả lời của trợ lý (dữ liệu giả)", "Mình đang ở chế độ thử" in t or "AI" in t)
    page.screenshot(path=f"{SHOTS}/qa2-ai-chip-sent-desktop.png")
    ctx.close()

    # Chạm ô -> panel nạp -> gõ câu -> gửi bằng Enter hoặc nút gửi của panel
    for how in ("enter", "button"):
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        mock_demo(page, ai=True, consent=True)
        page.get_by_label("Hỏi AI về chứng từ này").click()
        pin = page.locator("[data-ai-block] input[aria-label]").last
        expect(pin).to_be_focused()
        pin.fill("   ")
        pin.press("Enter"); page.wait_for_timeout(500)
        ok(f"B3 ({how}) chỉ khoảng trắng: Enter không gửi (không có câu trả lời nào)", "Số liệu giả" not in page.locator("[data-ai-block]").inner_text())
        pin.fill("Lô nào sắp hết hạn?")
        if how == "enter":
            pin.press("Enter")
        else:
            page.locator("[data-ai-block] button[type=submit]").click()
        page.wait_for_timeout(2500)
        t = page.locator("[data-ai-block]").inner_text()
        ok(f"B3 ({how}) gõ câu rồi gửi: câu hỏi xuất hiện đúng 1 lần, có trả lời", t.count("Lô nào sắp hết hạn?") == 1 and "Số liệu giả" in t.split("Lô nào sắp hết hạn?")[-1], t.replace("\n", " | ")[-200:])
        ctx.close()

    # Mạng chậm: chạm ô rồi gõ NGAY khi chunk trợ lý chưa về -> ký tự có mất không?
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    mock_demo(page, ai=True, consent=True)
    held = []
    page.route(re.compile(r".*/_next/static/chunks/.*\.js"), lambda r: held.append(r))
    page.get_by_label("Hỏi AI về chứng từ này").click()
    page.keyboard.type("abcdef", delay=60)
    page.wait_for_timeout(300)
    mid = page.locator("[data-ai-block]").inner_text().replace("\n", " | ")
    for r in held:
        r.continue_()
    page.wait_for_timeout(5000)
    got = page.evaluate("() => { const a=document.activeElement; return a && a.value !== undefined ? a.value : null }")
    ok("B3 mạng chậm: gõ ngay sau khi chạm ô (chunk chưa về) -> ký tự gõ trong lúc chờ KHÔNG bị mất", got == "abcdef", f"ô panel = {got!r}; trong lúc chờ khối hiện: {mid[-120:]}")
    page.screenshot(path=f"{SHOTS}/qa2-ai-slow-chunk-desktop.png")
    ctx.close()

    # Bàn phím: Tab tới chip rồi Enter
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    mock_demo(page, ai=True, consent=True)
    page.locator("[data-ai-starter] button").first.focus()
    page.keyboard.press("Enter"); page.wait_for_timeout(2000)
    ok("B3 bàn phím: Enter trên chip gửi câu hỏi", "TRỢ LÝ VẬN HÀNH" in page.locator("[data-ai-block]").inner_text().upper())
    ctx.close()

    # Bật nhưng CHƯA đồng ý: khung hiện; chạm -> thẻ đồng ý, chưa gọi chat/model
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    mock_demo(page, ai=True, consent=False)
    expect(page.locator("[data-ai-starter]")).to_be_visible()
    page.locator("[data-ai-starter] button").first.click(); page.wait_for_timeout(1500)
    t = page.locator("[data-ai-block]").inner_text()
    ok("B3 chưa đồng ý + bấm chip: hiện thẻ đồng ý, chưa có panel/trả lời, 0 request commands/chat", "TRỢ LÝ VẬN HÀNH" not in t.upper() and re.search(r"đồng ý", t, re.I) is not None and not any(("/commands" in x or "chat" in x) for x in mlog(page)), t.replace("\n", " | ")[-260:])
    agree = page.locator("[data-ai-block]").get_by_role("button", name="Bật trợ lý")
    cb = page.locator("[data-ai-block] input[type=checkbox]")
    ok("B3 chưa đồng ý: nút đồng ý khoá tới khi tick", cb.count() == 1 and agree.count() == 1 and agree.is_disabled())
    page.screenshot(path=f"{SHOTS}/qa2-ai-consent-card-desktop.png")
    st = page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), location.href])")
    ok("B3 chưa đồng ý: localStorage/sessionStorage/URL không chứa SĐT giả, chưa ghi cờ đồng ý", FAKE_PHONE not in st, st[:160])
    cb.check(); agree.click(); page.wait_for_timeout(2500)
    t = page.locator("[data-ai-block]").inner_text()
    ok("B3 đồng ý xong: panel nạp (câu chuyển giao được xử lý, không văng lỗi)", "TRỢ LÝ VẬN HÀNH" in t.upper(), t.replace("\n", " | ")[-200:])
    ctx.close()

    # Mobile 360
    ctx = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce", has_touch=True, is_mobile=True)
    page = ctx.new_page()
    mock_demo(page, ai=True, consent=True)
    expect(page.locator("[data-ai-starter]")).to_be_visible()
    hs = page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
    hts = page.evaluate("() => [...document.querySelectorAll('[data-ai-starter] button')].map(b => Math.round(b.getBoundingClientRect().height))")
    inh = page.get_by_label("Hỏi AI về chứng từ này").bounding_box()
    ok("B3 360px: không cuộn ngang; chip và nút gửi cao >= 44px; ô nhập cao >= 44px", hs and all(h >= 44 for h in hts) and inh["height"] >= 44, f"hscroll_ok={hs} {hts} input={inh['height']}")
    page.get_by_role("button", name=re.compile("^Tóm tắt lịch sử")).tap(); page.wait_for_timeout(2500)
    page.screenshot(path=f"{SHOTS}/qa2-ai-chip-sent-mobile360.png", full_page=True)
    ok("B3 360px: bấm chip bằng chạm gửi được, không cuộn ngang", page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1") and "TRỢ LÝ VẬN HÀNH" in page.locator("[data-ai-block]").inner_text().upper())
    ctx.close()

    # Tải lại trang: câu đang gõ không được giữ
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    mock_demo(page, ai=True, consent=True)
    page.get_by_label("Hỏi AI về chứng từ này").fill("câu nháp")
    page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
    ok("B3 tải lại trang: ô nhập rỗng (không lưu nháp)", page.get_by_label("Hỏi AI về chứng từ này").input_value() == "")
    ctx.close()


def b_b5(browser, errors):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    mock_demo(page, ai=False, consent=True)
    page.locator('button[aria-label="Sửa số lượng"]').last.click()
    inp = page.locator("dl input").first
    inp.fill(""); page.get_by_role("button", name="Lưu", exact=True).click(); page.wait_for_timeout(300)
    ok("B5 để trống rồi bấm Lưu: nút chính vẫn 'Lưu', không 'Thử lại'", page.get_by_role("button", name="Lưu", exact=True).count() == 1 and page.get_by_role("button", name="Thử lại", exact=True).count() == 0)
    ok("B5 để trống: lỗi dưới ô 1 dòng, 0 request PATCH", page.locator("dl [role=alert], dl p, dl [id$='-e']").filter(has_text=re.compile("nhập|trống", re.I)).count() == 1 and not any("PATCH" in x for x in mlog(page)), str(mlog(page)))
    inp.fill("   "); page.get_by_role("button", name="Lưu", exact=True).click(); page.wait_for_timeout(300)
    ok("B5 chỉ khoảng trắng: vẫn là lỗi nhập, không gửi", not any("PATCH" in x for x in mlog(page)) and page.get_by_role("button", name="Lưu", exact=True).count() == 1)
    inp.fill("9"); page.wait_for_timeout(200)
    ok("B5 gõ tiếp thì lỗi biến mất", page.locator("dl [id$='-e']").filter(has_text=re.compile("nhập|trống", re.I)).count() == 0 and inp.get_attribute("aria-invalid") != "true")
    page.get_by_role("button", name="Lưu", exact=True).click(); page.wait_for_timeout(800)
    ok("B5 nhập hợp lệ rồi Lưu: đúng 1 PATCH", len([x for x in mlog(page) if "PATCH" in x]) == 1, str(mlog(page)))
    page.screenshot(path=f"{SHOTS}/qa2-inplace-after-empty-desktop.png")
    ctx.close()
    # 409 STALE_STATE ở ô sửa tại chỗ rồi thử lại: gõ 409 (mock trả xung đột) -> banner; gõ 410 -> CLAIMED lỗi thường
    for val, expect_banner in (("409", True), ("410", False)):
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        page = ctx.new_page()
        mock_demo(page, ai=False, consent=True)
        page.locator('button[aria-label="Sửa số lượng"]').last.click()
        page.locator("dl input").first.fill(val)
        page.get_by_role("button", name="Lưu", exact=True).click(); page.wait_for_timeout(800)
        ok(f"M1 sửa tại chỗ gõ {val}: {'banner xung đột' if expect_banner else 'lỗi thường giữ lý do BE, không banner'}", (page.locator("[data-conflict-banner]").count() == 1) == expect_banner, page.locator("body").inner_text()[:0])
        ctx.close()


def main():
    errs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for fn in (a_b1_b2, a_m1, a_m2, a_b4, b_b3, b_b5):
            try:
                fn(browser, errs)
            except Exception as e:  # noqa: BLE001
                ok(f"{fn.__name__} chạy hết không lỗi", False, repr(e)[:700])
        browser.close()
    bad = [e for e in errs if "favicon" not in e]
    ok("Không pageerror (lỗi JS chưa bắt)", not bad, "; ".join(bad)[:300])
    fails = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(fails)}/{len(results)} PASS")
    sys.exit(1 if fails else 0)


main()
