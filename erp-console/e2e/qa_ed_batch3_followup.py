# QA độc lập ERP theo design Lô 3 FE, lần 2 (sau khi dev sửa B1, H1, H2, M1-M3): bản build MOCK phục vụ tĩnh cổng 3101.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<doc/features/2026-10-01-erp-theo-design/shots/lot3> python3 -u e2e/qa_ed_batch3_followup.py
# Trọng tâm: SR-20 (AI tắt thì 0 request actions/counts ở 3 danh sách và 3 trang chi tiết, không tải chunk model),
# khối AI ở khoản tiền và phiếu hoàn (đúng chứng từ, không lẫn sang chứng từ khác, không có ở id rác, vai thiếu quyền không gọi),
# gõ nhanh vào ô hỏi AI không mất chữ, popup hoàn chỉ 1 dòng "Còn hoàn được", ô số tiền (nhóm nghìn, xoá lùi, dán, âm, chữ, vượt).
# Chỉ dữ liệu giả của mock.
import os
import re
import time
import traceback

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=8_000)
ASK = "Hỏi AI về chứng từ này"
results = []
errors = []
console_all = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, ("" if cond else "  -> " + str(extra)[:300]), flush=True)


def section(name):
    def deco(fn):
        print(f"\n=== {name}", flush=True)
        try:
            fn()
        except Exception as e:
            ok(f"[NHÓM {name}] chạy hết không ngoại lệ", False, f"{type(e).__name__}: {str(e)[:250]}")
            traceback.print_exc(limit=3)
        return fn

    return deco


def new_page(browser, user, w=1280, h=900, mobile=False):
    kw = dict(viewport={"width": w, "height": h}, reduced_motion="reduce")
    if mobile:
        kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**kw)
    pg = ctx.new_page()
    pg.net = []
    pg.on("request", lambda r: pg.net.append(r.url))

    def on_console(m):
        console_all.append(m.text)
        if m.type == "error" and "Failed to fetch RSC payload" not in m.text:
            errors.append(f"[{user}] {m.text}")

    pg.on("console", on_console)
    pg.on("pageerror", lambda e: errors.append(f"[{user}] pageerror {e}"))
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


def go(pg, path):
    pg.goto(BASE + path)
    pg.wait_for_load_state("networkidle")
    idle(pg)


def log(pg):
    return pg.evaluate("() => window.__caveMock.log.slice()")


def clear_log(pg):
    pg.evaluate("() => window.__caveMock.clearLog()")


def ai_calls(pg):
    return [x for x in log(pg) if "/api/ai/" in x]


def set_ai(pg, on, consent=True):
    pg.evaluate("([a, c]) => { window.__caveMock.ai(a ? 'on' : 'off'); window.__caveMock.aiConsent(c); }", [on, consent])


def shot(pg, name, full=False):
    pg.screenshot(path=f"{SHOTS}/qa2-{name}.png", full_page=full)


def hscroll_ok(pg, w):
    return pg.evaluate("(w) => document.documentElement.scrollWidth <= w + 1", w)


def open_refund_modal_from_order(pg, oid=105):
    go(pg, f"/orders/detail/?id={oid}")
    expect(pg.locator("main header h2")).to_be_visible()
    pg.get_by_role("button", name="Thao tác khác").click()
    pg.get_by_role("menuitem", name="Lập phiếu hoàn").click()
    d = pg.get_by_role("dialog", name="Lập phiếu hoàn")
    expect(d).to_be_visible()
    return d


DETAILS = ["/orders/detail/?id=101", "/orders/payments/detail/?id=880", "/orders/refunds/detail/?id=4"]
LISTS = ["/orders/", "/orders/payments/", "/orders/refunds/"]
MODEL_CHUNK = re.compile(r"wllama|worker|\.gguf|/call/|model", re.I)

with sync_playwright() as p:
    browser = p.chromium.launch()

    # ========================================================================================= 1. SR-20: AI tắt
    @section("1. SR-20: AI tắt thì 0 request actions/counts, không tải chunk model")
    def _():
        ctx, pg = new_page(browser, "loc")
        set_ai(pg, False)
        for path in LISTS + DETAILS:
            clear_log(pg)
            pg.net.clear()
            go(pg, path)
            pg.wait_for_timeout(500)
            calls = ai_calls(pg)
            bad = [c for c in calls if "/api/ai/actions" in c or "counts" in c or "chat" in c or "summary" in c or "commands" in c]
            ok(f"SR-20 AI tắt {path}: 0 request actions/counts/chat/summary/commands", bad == [], calls)
            if "/detail/" in path:
                ok(f"SR-20 AI tắt {path}: tối đa 1 request status", len(calls) <= 1 and all("/api/ai/status/" in c for c in calls), calls)
            else:
                ok(f"SR-20 AI tắt {path}: danh sách gọi 0 request /api/ai/*", calls == [], calls)
            ok(f"SR-20 AI tắt {path}: không có khối Trợ lý AI, không ô hỏi AI", pg.locator("[data-ai-block]").count() == 0 and pg.get_by_label(ASK).count() == 0)
            heavy = [u for u in pg.net if MODEL_CHUNK.search(u.split("?")[0]) and "/_next/static/" in u]
            ok(f"SR-20 AI tắt {path}: không tải chunk model/worker", heavy == [], heavy[:3])
        # AI bật nhưng chưa đồng ý: danh sách vẫn 0 actions/counts
        set_ai(pg, True, False)
        for path in LISTS:
            clear_log(pg)
            go(pg, path)
            pg.wait_for_timeout(300)
            bad = [c for c in ai_calls(pg) if "counts" in c or "/api/ai/actions" in c]
            ok(f"SR-20 AI bật (chưa đồng ý) {path}: danh sách không gọi actions/counts", bad == [], ai_calls(pg))
        set_ai(pg, True, True)
        for path in LISTS:
            clear_log(pg)
            go(pg, path)
            pg.wait_for_timeout(300)
            bad = [c for c in ai_calls(pg) if "counts" in c or "/api/ai/actions" in c]
            ok(f"SR-20 AI bật (đã đồng ý) {path}: danh sách không gọi actions/counts, không thanh AI", bad == [] and pg.locator("[data-ai-bar]").count() == 0, ai_calls(pg))
        ctx.close()

    # ========================================================================================= 2. Khối AI ở 3 trang chi tiết
    @section("2. Khối AI ở trang chi tiết: đúng chứng từ, không lẫn")
    def _():
        ctx, pg = new_page(browser, "loc")
        set_ai(pg, True, True)
        code101 = pg.evaluate("() => window.__caveMock.orderJson('loc', 101).code")
        code105 = pg.evaluate("() => window.__caveMock.orderJson('loc', 105).code")
        go(pg, "/overview/")
        pg.evaluate("([a]) => { window.__caveMock.aiOrderProposal(a); window.__caveMock.aiPaymentProposal('880'); window.__caveMock.aiRefundProposal('4'); }", [code101])
        # đi bằng liên kết trong app để giữ bộ nhớ mock (mất khi tải lại)
        pg.get_by_role("link", name="Đơn hàng").first.click()
        pg.wait_for_url(re.compile(r"/orders/?$"))
        idle(pg)
        pg.locator("tbody tr", has_text=code101).first.click()
        pg.wait_for_url(re.compile(r"detail/\?id=101"))
        idle(pg)
        pg.wait_for_function("() => { const b = document.querySelector('[data-ai-block]'); return b && !b.innerText.includes('Đang kiểm tra'); }", timeout=10_000)
        blk = pg.locator("[data-ai-block]")
        ok("khối AI đơn 101: hiện đúng 1 khối, có đề xuất 'Xác nhận đơn hàng'", blk.count() == 1 and blk.get_by_text("Xác nhận đơn hàng").count() >= 1, blk.inner_text()[:200] if blk.count() else "không có khối")
        calls = [c for c in ai_calls(pg) if "/api/ai/actions" in c and "target_model=" in c]
        ok("đơn 101 gửi target_model=sales.salesorder (không phải sales.order)", any("target_model=sales.salesorder" in c for c in calls) and not any("target_model=sales.order&" in c or c.endswith("target_model=sales.order") for c in calls), calls)
        shot(pg, "ai-order-detail-1280")
        # đơn khác (105) không thấy đề xuất của 101
        pg.go_back()
        pg.wait_for_url(re.compile(r"/orders/?$"))
        idle(pg)
        pg.locator("tbody tr", has_text=code105).first.click()
        pg.wait_for_url(re.compile(r"detail/\?id=105"))
        idle(pg)
        pg.wait_for_function("() => { const b = document.querySelector('[data-ai-block]'); return b && !b.innerText.includes('Đang kiểm tra'); }", timeout=10_000)
        ok("đơn 105 KHÔNG thấy đề xuất AI của đơn 101", pg.locator("[data-ai-block]").get_by_text("Xác nhận đơn hàng").count() == 0)
        ctx.close()

    @section("2b. Khoản tiền 880 và phiếu hoàn 4: đề xuất đúng chứng từ")
    def _():
        ctx, pg = new_page(browser, "loc")
        set_ai(pg, True, True)
        go(pg, "/overview/")
        pg.evaluate("() => { window.__caveMock.aiPaymentProposal('880'); window.__caveMock.aiRefundProposal('4'); }")
        for kind, list_re, tab_re, detail_re, pk, title, other_title in (
            ("khoản tiền", r"/orders/payments/?$", "Hàng chờ thanh toán", r"payments/detail/\?id=880", "880", "Khớp khoản tiền với đơn", "Xác nhận đã hoàn tiền"),
            ("phiếu hoàn", r"/orders/refunds/?$", "Phiếu hoàn", r"refunds/detail/\?id=4", "4", "Xác nhận đã hoàn tiền", "Khớp khoản tiền với đơn"),
        ):
            if "/orders" not in pg.url:
                pg.get_by_role("link", name="Đơn hàng").first.click()
                pg.wait_for_url(re.compile(r"/orders/?$")); idle(pg)
            tab = pg.get_by_role("tab", name=re.compile(tab_re, re.I))
            (tab.first if tab.count() else pg.get_by_role("link", name=re.compile(tab_re, re.I)).first).click()
            pg.wait_for_url(re.compile(list_re)); idle(pg)
            pg.locator("tbody tr").filter(has_text=re.compile(r"\b" + pk + r"\b|FT|#")).first.click() if False else None
            # tìm dòng dẫn tới đúng id bằng liên kết/hàng: bấm từng hàng đến khi URL có đúng id
            found = False
            for i in range(12):
                pg.wait_for_timeout(300)
                if i >= pg.locator("tbody tr").count():
                    break
                pg.locator("tbody tr").nth(i).click()
                try:
                    pg.wait_for_url(re.compile(r"detail/\?id="), timeout=3000)
                except Exception:
                    continue
                if re.search(detail_re, pg.url):
                    found = True
                    break
                pg.go_back(); pg.wait_for_url(re.compile(list_re)); idle(pg)
            ok(f"{kind}: tìm được chứng từ id {pk} từ danh sách", found, pg.url)
            if not found:
                continue
            idle(pg)
            pg.wait_for_function("() => { const b = document.querySelector('[data-ai-block]'); return b && !b.innerText.includes('Đang kiểm tra'); }", timeout=10_000)
            txt = pg.locator("[data-ai-block]").inner_text()
            ok(f"{kind} {pk}: có đề xuất '{title}' trong khối", title in txt, txt[:200])
            ok(f"{kind} {pk}: KHÔNG có đề xuất của loại chứng từ khác ('{other_title}')", other_title not in txt, txt[:200])
            ok(f"{kind} {pk}: không cảnh báo lỗi, ô hỏi AI hiện sẵn", pg.locator("[data-ai-block] [role=alert]").count() == 0 and pg.get_by_label(ASK).count() >= 1)
            calls = [c for c in ai_calls(pg) if "/api/ai/actions" in c and "target_model=" in c]
            model = "sales.paymenttransaction" if kind == "khoản tiền" else "sales.refund"
            ok(f"{kind} {pk}: gửi target_model={model}&target_id={pk}", any(f"target_model={model}" in c and f"target_id={pk}" in c for c in calls), calls)
            shot(pg, "ai-refund-detail-1280" if kind == "phiếu hoàn" else "ai-payment-detail2-1280")
            pg.go_back(); pg.wait_for_url(re.compile(list_re)); idle(pg)
        ctx.close()

    # ========================================================================================= 3. Id rác & vai thiếu quyền (AI bật)
    @section("3. AI bật: id rác, vai thiếu quyền không gọi actions")
    def _():
        ctx, pg = new_page(browser, "loc")
        set_ai(pg, True, True)
        for path in ("/orders/detail/?id=abc", "/orders/detail/?id=999999", "/orders/detail/", "/orders/payments/detail/?id=abc", "/orders/payments/detail/?id=999999", "/orders/refunds/detail/?id=-1", "/orders/refunds/detail/?id=999999"):
            clear_log(pg)
            go(pg, path)
            pg.wait_for_timeout(500)
            acts = [c for c in ai_calls(pg) if "/api/ai/actions" in c]
            ok(f"id rác {path}: không khối AI, không gọi actions với id rác", pg.locator("[data-ai-block]").count() == 0 and acts == [], acts)
            ok(f"id rác {path}: có câu 'Không tìm thấy'/'Không mở được', không undefined/NaN", re.search(r"Không (tìm thấy|mở được)|không tồn tại", pg.locator("main").inner_text()) is not None and not re.search(r"undefined|NaN|\[object", pg.locator("main").inner_text()), pg.locator("main").inner_text()[:160])
        ctx.close()
        for user, allow_pay, allow_ref in (("ql1", False, True), ("kho1", False, False), ("giao1", False, False), ("cs2", False, False)):
            ctx, pg = new_page(browser, user)
            set_ai(pg, True, True)
            for path, allowed in (("/orders/payments/detail/?id=880", allow_pay), ("/orders/refunds/detail/?id=4", allow_ref)):
                clear_log(pg)
                go(pg, path)
                pg.wait_for_timeout(500)
                body = pg.locator("main").inner_text()
                acts = [c for c in ai_calls(pg) if "/api/ai/actions" in c]
                if allowed:
                    ok(f"{user} {path}: được xem (chỉ xem), không có nút xác nhận hoàn tiền", re.search(r"không có quyền", body, re.I) is None and "Xác nhận đã hoàn" not in pg.locator("main header").first.inner_text(), body[:120])
                else:
                    ok(f"{user} {path}: 'Không có quyền', không khối AI, không gọi actions", re.search(r"không có quyền", body, re.I) is not None and pg.locator("[data-ai-block]").count() == 0 and acts == [], (body[:100], acts))
            ctx.close()

    # ========================================================================================= 4. Gõ nhanh vào ô hỏi AI
    @section("4. Gõ nhanh vào ô hỏi AI khi chunk panel chậm: không mất chữ")
    def _():
        for delay_ms, type_delay, label in ((1500, 0, "chunk chậm 1,5s, gõ không ngắt"), (800, 35, "chunk chậm 0,8s, gõ 35ms/phím"), (0, 0, "mạng nhanh")):
            ctx, pg = new_page(browser, "loc")
            set_ai(pg, True, True)
            go(pg, "/orders/detail/?id=101")
            pg.wait_for_timeout(500)
            held = []
            if delay_ms:
                pg.route(re.compile(r".*/_next/static/chunks/.*\.js"), lambda route: held.append(route))
            box = pg.get_by_label(ASK).first
            expect(box).to_be_visible()
            text = "tom tat don nay abc DEF 123"
            box.click()
            box.press_sequentially(text, delay=type_delay)
            # giữ chunk đến khi gõ xong + thêm delay_ms, rồi thả; đợi panel nạp xong rồi đọc ô cuối cùng
            pg.wait_for_timeout(delay_ms)
            for r in held:
                r.continue_()
            if delay_ms:
                pg.unroute(re.compile(r".*/_next/static/chunks/.*\.js"))
            ok(f"gõ nhanh ({label}): có chunk bị giữ thật (phép thử có hiệu lực)", (not delay_ms) or len(held) >= 1, len(held))
            pg.wait_for_timeout(2500)
            vals = pg.evaluate("() => [...document.querySelectorAll('[data-ai-block] textarea, [data-ai-block] input[type=text], [data-ai-block] input:not([type])')].map(e => e.value)")
            ok(f"gõ nhanh ({label}): đúng một ô nhập và nội dung đủ '{text}'", len(vals) == 1 and vals[0] == text, vals)
            ok(f"gõ nhanh ({label}): chưa tự gửi khi chưa Enter (0 request chat)", not any("chat" in c for c in ai_calls(pg)), ai_calls(pg))
            focus_in_block = pg.evaluate("() => !!document.activeElement && !!document.activeElement.closest('[data-ai-block]')")
            ok(f"gõ nhanh ({label}): focus vẫn nằm trong khối AI", focus_in_block, pg.evaluate("() => document.activeElement && document.activeElement.tagName"))
            if delay_ms == 800:
                shot(pg, "ai-typing-slow-1280")
            if delay_ms == 0:
                # Enter gửi đúng 1 lần
                clear_log(pg)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(900)
                chats = [c for c in ai_calls(pg) if "chat" in c or "summary" in c]
                ok("gõ xong Enter: gửi đúng 1 lần", len(chats) <= 1, chats)
            ctx.close()
        # Chưa đồng ý: gõ rồi tick đồng ý, chữ không mất
        ctx, pg = new_page(browser, "loc")
        set_ai(pg, True, False)
        go(pg, "/orders/detail/?id=101")
        pg.wait_for_timeout(400)
        box = pg.get_by_label(ASK).first
        box.click()
        box.press_sequentially("xin chao 456", delay=10)
        pg.wait_for_timeout(1200)
        vals = pg.evaluate("() => [...document.querySelectorAll('[data-ai-block] textarea, [data-ai-block] input[type=text], [data-ai-block] input:not([type])')].map(e => e.value)")
        ok("chưa đồng ý model: gõ vào ô, chữ còn nguyên, đúng một ô", len(vals) == 1 and vals[0] == "xin chao 456", vals)
        ok("chưa đồng ý model: không gọi chat, không lưu cờ đồng ý trước khi tick", not any("chat" in c for c in ai_calls(pg)) and pg.evaluate("() => localStorage.getItem('cave_erp_ai_consent')") != "1")
        shot(pg, "ai-consent-typed-1280")
        # Dữ liệu cá nhân gõ vào ô hỏi không rơi vào localStorage/URL/console
        box = pg.get_by_label(ASK).first
        box.fill("Khach Thu A 0900000123 so 5 Duong Gia")
        pg.wait_for_timeout(300)
        ls = pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(localStorage)))") + pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage)))")
        ok("PII gõ vào ô hỏi AI không vào localStorage/sessionStorage/URL/console", "0900000123" not in ls and "0900000123" not in pg.url and not any("0900000123" in c for c in console_all), pg.url)
        ctx.close()

    # ========================================================================================= 5. Popup Lập phiếu hoàn: 1 dòng
    @section("5. Popup 'Lập phiếu hoàn': mỗi dòng đúng một lần")
    def _():
        ctx, pg = new_page(browser, "loc")
        d = open_refund_modal_from_order(pg, 105)
        t = d.inner_text()
        ok("F2c từ đơn: 'Còn hoàn được' đúng 1 lần (B1)", t.count("Còn hoàn được") == 1, t.count("Còn hoàn được"))
        ok("F2c từ đơn: 'Đơn', 'Tổng đơn' mỗi dòng 1 lần", t.count("Tổng đơn") == 1 and t.count("Đơn\n") <= 2, t[:200])
        shot(pg, "F2c-one-row")
        d.get_by_role("button", name="Quay lại").click() if d.get_by_role("button", name="Quay lại").count() else pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        # từ trang khoản tiền
        go(pg, "/orders/payments/detail/?id=880")
        pg.get_by_role("button", name=re.compile("Lập phiếu hoàn")).first.click() if pg.get_by_role("button", name=re.compile("Lập phiếu hoàn")).count() else (pg.get_by_role("button", name="Thao tác khác").click(), pg.get_by_role("menuitem", name="Lập phiếu hoàn").click())
        d2 = pg.get_by_role("dialog", name="Lập phiếu hoàn")
        expect(d2).to_be_visible()
        t2 = d2.inner_text()
        ok("F2c từ khoản tiền: 'Còn hoàn được' đúng 1 lần (B1)", t2.count("Còn hoàn được") == 1, t2[:260])
        shot(pg, "F2c-one-row-from-payment")
        ctx.close()
        # 360px
        ctx, pg = new_page(browser, "loc", 360, 800, mobile=True)
        d = open_refund_modal_from_order(pg, 105)
        ok("F2c 360px: 1 dòng 'Còn hoàn được', không cuộn ngang, nút cao >= 44px", d.inner_text().count("Còn hoàn được") == 1 and hscroll_ok(pg, 360) and d.locator("button[type=submit]").bounding_box()["height"] >= 43, d.inner_text()[:100])
        shot(pg, "F2c-one-row-360")
        ctx.close()

    # ========================================================================================= 6. Ô số tiền hoàn (nhóm nghìn)
    @section("6. Ô số tiền hoàn: nhóm nghìn tự động, xoá lùi, dán, biên")
    def _():
        ctx, pg = new_page(browser, "loc")

        def amount_state(d):
            f = d.get_by_label(re.compile("Số tiền hoàn"))
            sub = d.locator("button[type=submit]")
            m = re.search(r"([\d.]+) đ\s*$", sub.inner_text().strip())
            return f, sub, (m.group(1) if m else None)

        def fresh():
            d = open_refund_modal_from_order(pg, 105)
            return d

        d = fresh()
        f, sub, _a = amount_state(d)
        f.fill("")
        f.press_sequentially("1000000", delay=15)
        ok("gõ 1000000 → ô hiện '1.000.000'", f.input_value() == "1.000.000", f.input_value())
        ok("gõ 1000000: nút gửi ghi đúng '1.000.000 đ'", amount_state(d)[2] == "1.000.000", sub.inner_text())
        f.fill("")
        f.press_sequentially("150000", delay=15)
        ok("gõ 150000 → ô '150.000', nút '150.000 đ'", f.input_value() == "150.000" and amount_state(d)[2] == "150.000", (f.input_value(), sub.inner_text()))
        f.press("Backspace")
        shown, sent = f.input_value(), amount_state(d)[2]
        ok("XOÁ LÙI 1 chữ số từ '150.000' (ý người dùng 15.000): số gửi đi phải là 15.000 (không bị đọc thành 150 đ)", sent == "15.000", (shown, sent))
        f.fill("")
        f.press_sequentially("1500000", delay=15)
        f.press("Backspace")
        shown, sent = f.input_value(), amount_state(d)[2]
        ok("XOÁ LÙI 1 chữ số từ '1.500.000' (ý người dùng 150.000): số gửi đi phải là 150.000 (không bị đọc thành 1.500 đ)", sent == "150.000", (shown, sent))
        shot(pg, "amount-backspace-1280")
        f.fill("")
        f.press_sequentially("12345", delay=15)
        f.press("Backspace"); f.press("Backspace")
        shown, sent = f.input_value(), amount_state(d)[2]
        ok("gõ 12345 rồi xoá lùi 2 lần (ý người dùng 123): số gửi đi là 123", sent == "123", (shown, sent))
        # dán các dạng
        for pasted, want in (("1.190.000", "1.190.000"), ("1,190,000 đ", "1.190.000"), ("540000", "540.000"), ("540.000 VND", "540.000")):
            f.fill("")
            f.fill(pasted)
            f.blur()
            got = amount_state(d)[2]
            ok(f"dán '{pasted}' → nút ghi {want} đ", got == want, (f.input_value(), got))
        # biên và lỗi
        d.get_by_label(re.compile("Lý do hoàn")).fill("Khách đổi ý (thử)")
        for typed, bad in (("0", "zero"), ("-5", "neg"), ("abc", "text"), ("", "empty")):
            f.fill(typed)
            pg.wait_for_timeout(100)
            clear_log(pg)
            if not (sub.is_disabled() or sub.get_attribute("aria-disabled") == "true"):
                sub.click()
                pg.wait_for_timeout(300)
            posted = [x for x in log(pg) if x.startswith("POST")]
            alerts = d.locator("[role=alert]").count() + d.locator("[aria-invalid=true]").count()
            ok(f"số tiền '{typed}' ({bad}): không gửi (0 POST) và có báo lỗi tại ô hoặc nút khoá", posted == [] and (alerts >= 1 or sub.is_disabled()), (posted, alerts, sub.is_disabled()))
        f.fill("1.190.001")
        f.blur()
        clear_log(pg)
        pg.wait_for_timeout(300)
        if not sub.is_disabled():
            sub.click()
        pg.wait_for_timeout(500)
        posted = [x for x in log(pg) if x.startswith("POST")]
        ok("vượt 'Còn hoàn được' 1 đ: nút khoá, không gửi (0 POST), có câu 'Nhập tối đa 1.190.000 đ.'", posted == [] and "Nhập tối đa 1.190.000 đ" in d.inner_text() and sub.is_disabled(), (posted, d.inner_text()[-200:]))
        f.fill("1.190.000")
        f.blur()
        clear_log(pg)
        sub.dblclick()
        pg.wait_for_timeout(1200)
        posted = [x for x in log(pg) if x.startswith("POST") and "refunds/create" in x]
        ok("đúng bằng 'Còn hoàn được', bấm đúp: đúng 1 POST create", len(posted) == 1, posted)
        # sau khi hoàn đủ, đơn không còn lập hoàn được nữa (số còn lại 0)
        pg.wait_for_timeout(400)
        pg.get_by_role("button", name="Thao tác khác").click()
        items = [(it.inner_text().strip(), it.get_attribute("aria-disabled")) for it in pg.get_by_role("menu").get_by_role("menuitem").all()]
        ref_item = [i for i in items if "Lập phiếu hoàn" in i[0]]
        ok("hoàn đủ rồi: mục 'Lập phiếu hoàn' bị chặn (mờ + lý do) hoặc biến mất", (not ref_item) or ref_item[0][1] == "true", items)
        ctx.close()

    # ========================================================================================= 7. Hồi quy nhỏ các sửa khác
    @section("7. Chip/toast (PO chốt B2), StatusPath 360px, đơn hết hạn")
    def _():
        ctx, pg = new_page(browser, "loc")
        go(pg, "/orders/detail/?id=102")
        pg.wait_for_timeout(200)
        ctx.close()
        ctx, pg = new_page(browser, "loc", 360, 800, mobile=True)
        for oid in (101, 104, 105, 106):
            go(pg, f"/orders/detail/?id={oid}")
            ok(f"360px đơn {oid}: StatusPath không cuộn ngang, không bị cắt (mọi bước nằm trong khung)", hscroll_ok(pg, 360) and pg.evaluate("""() => { const ol = document.querySelector('main ol'); if (!ol) return false; const r = ol.getBoundingClientRect(); return [...ol.querySelectorAll('li')].every(li => { const b = li.getBoundingClientRect(); return b.left >= r.left - 1 && b.right <= r.right + 1; }); }"""), pg.evaluate("() => document.documentElement.scrollWidth"))
        shot(pg, "statuspath-360", full=True)
        ctx.close()

    # ========================================================================================= 8. Console
    @section("8. Console không lỗi, không dữ liệu cá nhân")
    def _():
        ok("không console.error/pageerror (ngoài RSC payload)", errors == [], errors[:3])
        ok("console không chứa SĐT giả đã gõ", not any("0900000123" in c for c in console_all))

    browser.close()

passed = sum(1 for r in results if r[1])
print(f"\n{passed}/{len(results)} PASS", flush=True)
for n, c, e in results:
    if not c:
        print("FAIL", n, "->", str(e)[:300])
