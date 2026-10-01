# QA ERP theo design, Lô 2 FE: các ca CHỈ làm được với apiFetch thật (mất mạng khi gửi, 400/409/410/500, AI stub) — khung thử riêng.
#   node_modules/.bin/vite build --config e2e/qa_harness_ed_batch2/vite.config.mjs
#   (cd e2e/qa_harness_ed_batch2/dist && python3 -m http.server 3103 &)
#   SHOTS=../doc/features/2026-10-01-erp-theo-design/shots/lot2 python3 e2e/qa_ed_batch2_harness.py ; pkill -f "http.server 3103"
# Playwright chặn mạng http://api.qa.test/** (page.route). Chỉ dữ liệu giả.
import json
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3103")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
API = "http://api.qa.test"
results = []
expect.set_options(timeout=8_000)
CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"}
PII = re.compile(r"(\b0\d{9}\b|Nguyễn|đường |555111|unit_cost|giá vốn)", re.I)


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def reply(route, status=200, body=None, delay=0, raw=None, ctype="application/json"):
    if route.request.method == "OPTIONS":
        return route.fulfill(status=204, headers=CORS)
    route.fulfill(status=status, headers=CORS, content_type=ctype, body=raw if raw is not None else json.dumps(body if body is not None else {}))


def new_ctx(browser, w=1280, h=800, errors=None):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    ctx.add_init_script("localStorage.setItem('cave_erp_token','qa-token')")
    page = ctx.new_page()
    if errors is not None:
        page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    return ctx, page


def open_mode(page, m):
    page.goto(f"{BASE}/?m={m}")
    page.wait_for_load_state("networkidle")


def sent(page):
    return page.evaluate("() => window.__sent.slice()")


def red(s):
    n = [float(x) for x in re.findall(r"[\d.]+", s or "")][:3]
    return len(n) == 3 and n[0] > 150 and n[1] < 110 and n[2] < 110


def h_form(browser, errors):
    for label, handler in (
        ("mất mạng (abort)", lambda r: r.abort("internetdisconnected") if r.request.method != "OPTIONS" else reply(r)),
        ("HTTP 500 thân HTML", lambda r: reply(r, 500, raw="<html><body>Traceback (most recent call last): File views.py</body></html>", ctype="text/html")),
        ("HTTP 502 không thân", lambda r: reply(r, 502, raw="")),
    ):
        ctx, page = new_ctx(browser, errors=errors)
        mode = {"fail": True}
        def make(handler, mode):
            def h(route):
                if mode["fail"]:
                    handler(route)
                else:
                    reply(route, 200, {"ok": True})
            return h
        page.route(API + "/**", make(handler, mode))
        open_mode(page, "form")
        inp = page.get_by_label("Số lượng")
        inp.fill("33,5")
        page.get_by_role("button", name="Lưu phiếu").dblclick()
        expect(page.locator("[data-form-alert]")).to_be_visible()
        txt = page.locator("[data-form-alert]").inner_text()
        ok(f"ED-05-AC5/{label}: giá trị '33,5' còn nguyên", inp.input_value() == "33,5")
        ok(f"ED-05-AC5/{label}: alert đỏ là câu tiếng Việt, không lộ stack/HTML/URL kỹ thuật", bool(txt.strip()) and not re.search(r"Traceback|<html|views\.py|api\.qa\.test|TypeError|Failed to fetch|NetworkError", txt), txt[:120])
        ok(f"ED-05-AC5/{label}: nút chính thành 'Thử lại'", page.get_by_role("button", name="Thử lại", exact=True).count() == 1)
        n_before = len(sent(page))
        ok(f"ED-05-AC6/{label}: bấm đúp lúc gửi chỉ phát 1 lần", n_before == 1, str(n_before))
        if label.startswith("mất mạng"):
            page.screenshot(path=f"{SHOTS}/qa-form-network-lost-desktop.png")
        mode["fail"] = False
        page.get_by_role("button", name="Thử lại", exact=True).click()
        expect(page.locator("[data-done='1']")).to_be_visible()
        ok(f"ED-05-AC5/{label}: Thử lại thành công, alert mất", page.locator("[data-form-alert]").count() == 0)
        ctx.close()

    # 400 lỗi theo ô
    ctx, page = new_ctx(browser, errors=errors)
    page.route(API + "/**", lambda r: reply(r, 400, {"quantity": ["Nhập số kg lớn hơn 0."]}))
    open_mode(page, "form")
    page.get_by_label("Số lượng").fill("0")
    page.get_by_role("button", name="Lưu phiếu").click()
    f = page.locator("[data-invalid]")
    expect(f).to_be_visible()
    ok("ED-05-AC3 BE 400 theo ô: ô viền đỏ + đúng 1 dòng lỗi dưới ô", red(page.get_by_label("Số lượng").evaluate("e => getComputedStyle(e).borderColor")) and f.locator("p").count() == 1, f.inner_text()[:80])
    ok("ED-05-AC3: lỗi theo ô nối aria-describedby/aria-invalid", page.get_by_label("Số lượng").get_attribute("aria-invalid") == "true" and bool(page.get_by_label("Số lượng").get_attribute("aria-describedby")))
    ok("ED-05-AC3: giá trị '0' giữ nguyên sau lỗi", page.get_by_label("Số lượng").input_value() == "0")
    page.screenshot(path=f"{SHOTS}/qa-form-field-error-desktop.png")
    ctx.close()

    # 409
    ctx, page = new_ctx(browser, errors=errors)
    page.route(API + "/**", lambda r: reply(r, 409, {"detail": "Phiếu vừa được người khác cập nhật.", "code": "STALE_STATE", "updated_at": "2026-10-02T03:30:00Z", "updated_by_name": "Hạnh"}))
    open_mode(page, "form")
    page.get_by_label("Số lượng").fill("40")
    page.get_by_role("button", name="Lưu phiếu").click()
    bn = page.locator("[data-conflict-banner]")
    expect(bn).to_be_visible()
    t = bn.inner_text()
    ok("ED-05/W6f 409: banner 'Phiếu vừa được Hạnh sửa lúc 10:30 …' (giờ Việt Nam)", "Hạnh" in t and "10:30" in t and "02/10/2026" in t, t[:140].replace("\n", " "))
    ok("ED-05/W6f 409: có nút 'Tải lại', không alert đỏ chung", bn.get_by_role("button", name="Tải lại").count() == 1 and page.locator("[data-form-alert]").count() == 0)
    ok("ED-05/W6f 409: giá trị đang gõ '40' không mất", page.get_by_label("Số lượng").input_value() == "40")
    page.screenshot(path=f"{SHOTS}/qa-conflict-desktop.png")
    ctx.close()

    # 409 xung đột sửa (STALE_STATE) nhưng thân thiếu tên/giờ -> vẫn banner, không in rác
    ctx, page = new_ctx(browser, errors=errors)
    page.route(API + "/**", lambda r: reply(r, 409, {"detail": "Xung đột", "code": "STALE_STATE"}))
    open_mode(page, "form")
    page.get_by_role("button", name="Lưu phiếu").click()
    bn = page.locator("[data-conflict-banner]")
    expect(bn).to_be_visible()
    t = bn.inner_text()
    ok("W6f 409 STALE_STATE thiếu tên/giờ: banner vẫn rõ ràng, không in 'undefined'/'null'/'Invalid'", not re.search(r"undefined|null|Invalid|NaN", t), t[:120].replace("\n", " "))
    ctx.close()

    # Techlead M1: 409 KHÔNG phải xung đột sửa (CLAIMED, hoặc 409 trơn không mã) -> lỗi thường giữ lý do của BE, không banner
    for body, reason in (
        ({"detail": "Phiếu đang có người nhận xử lý.", "code": "CLAIMED"}, "đang có người nhận xử lý"),
        ({"detail": "Xung đột"}, "Xung đột"),
    ):
        ctx, page = new_ctx(browser, errors=errors)
        page.route(API + "/**", (lambda b: lambda r: reply(r, 409, b))(body))
        open_mode(page, "form")
        page.get_by_role("button", name="Lưu phiếu").click()
        alert = page.locator("[data-form-alert]")
        expect(alert).to_be_visible()
        ok(f"M1 409 {body.get('code', 'không mã')}: alert thường giữ lý do của BE, không banner 'vừa được ... sửa'", reason in alert.inner_text() and page.locator("[data-conflict-banner]").count() == 0, alert.inner_text()[:100])
        ctx.close()


def h_triple(browser, errors):
    # Cùng một tác vụ JS bấm 3 lần: useSubmit phải chặn bằng ref (UI-RULES §6.6 / ED-05-AC6)
    for mode, opener, btn_sel, label in (
        ("form", None, "[data-action-bar] button.primary", "FormPage"),
        ("modal", "#open", "[role=dialog] button.primary", "Modal"),
        ("header", "button[aria-label='Sửa số lượng']", "[data-editing] button.primary", "InfoField sửa tại chỗ"),
    ):
        ctx, page = new_ctx(browser, errors=errors)
        pend = []
        def make(pend):
            def h(route):
                if route.request.method == "OPTIONS":
                    return reply(route)
                pend.append(1)
                reply(route, 200, {})
            return h
        page.route(API + "/**", make(pend))
        open_mode(page, mode)
        if opener:
            page.locator(opener).click()
        if mode == "header":
            page.locator("dl input").first.fill("8")
        page.evaluate("(s) => { const b=document.querySelector(s); b.click(); b.click(); b.click(); }", btn_sel)
        page.wait_for_timeout(700)
        ok(f"ED-05-AC6 {label}: 3 lần click cùng tác vụ -> chỉ 1 request", len(sent(page)) == 1, str(sent(page)))
        ctx.close()


def h_modal(browser, errors):
    ctx, page = new_ctx(browser, errors=errors)
    state = {"mode": "hang"}
    def h(route):
        if route.request.method == "OPTIONS":
            return reply(route)
        if state["mode"] == "hang":
            state["pending"] = route
            return
        reply(route, 200, {})
    page.route(API + "/**", h)
    open_mode(page, "modal")
    page.locator("#open").click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    dlg.get_by_label("Số lượng").fill("21")
    dlg.get_by_role("button", name="Lưu", exact=True).click()
    expect(dlg.get_by_role("button", name="Đang gửi…")).to_be_visible()
    page.keyboard.press("Escape")
    page.mouse.click(5, 5)
    ok("ED-05 Modal đang gửi (request treo): Esc + scrim KHÔNG đóng", dlg.count() == 1)
    dlg.get_by_role("button", name="Đang gửi…").click(force=True)
    ok("ED-05 Modal đang gửi: bấm tiếp nút vẫn chỉ 1 request", len(sent(page)) == 1, str(sent(page)))
    # đứt mạng giữa chừng
    state["pending"].abort("internetdisconnected")
    expect(dlg.locator("[data-form-alert]")).to_be_visible()
    ok("ED-05 Modal sau đứt mạng: giữ giá trị, hiện 'Thử lại', mở khoá Esc/Huỷ", dlg.get_by_label("Số lượng").input_value() == "21" and dlg.get_by_role("button", name="Thử lại", exact=True).count() == 1 and dlg.get_by_role("button", name="Huỷ", exact=True).is_enabled())
    page.screenshot(path=f"{SHOTS}/qa-modal-network-lost-desktop.png")
    state["mode"] = "ok"
    dlg.get_by_role("button", name="Thử lại", exact=True).click()
    expect(dlg).to_have_count(0)
    ok("ED-05 Modal: Thử lại thành công đóng hộp, trả focus về nút mở", page.evaluate("() => document.activeElement && document.activeElement.id") == "open", page.evaluate("() => document.activeElement && document.activeElement.outerHTML.slice(0,60)"))
    ok("ED-05 Modal: tổng 2 request (1 đứt, 1 ok)", len(sent(page)) == 2, str(sent(page)))
    ctx.close()


def h_field(browser, errors):
    ctx, page = new_ctx(browser, errors=errors)
    open_mode(page, "field")
    f = page.locator("#fields")
    ok("ED-05-AC3 Field: đúng 1 dòng lỗi, viền đỏ, biểu tượng lỗi", f.locator("p").count() == 1 and red(f.get_by_label("Số kg").evaluate("e => getComputedStyle(e).borderColor")))
    ok("ED-05-AC3 Field: không chữ gợi ý xám dưới ô khi không lỗi", f.locator("p").count() == 1)
    stars = f.locator("label span[aria-hidden='true']").count()
    ok("ED-05-AC3 Field: '*' chỉ ở trường bắt buộc (2 trường)", stars == 2, str(stars))
    ok("ED-05-AC3 Field: đơn vị đ/kg trong ô, select/textarea không đơn vị", f.get_by_text("đ", exact=True).count() == 1 and f.get_by_text("kg", exact=True).count() == 1)
    page.screenshot(path=f"{SHOTS}/qa-field-states-desktop.png")
    ctx.close()


def h_header(browser, errors):
    ctx, page = new_ctx(browser, errors=errors)
    ok_calls = []
    page.route(API + "/**", lambda r: (ok_calls.append(r.request.method), reply(r, 200, {})))
    open_mode(page, "header")
    bad = page.locator('[data-state="bad"]')
    ok("ED-04 StatusPath kết thúc xấu: có bước 'Đã huỷ' tông đỏ, bước sau không tô", bad.count() == 1 and page.locator('[data-state="current"]').count() == 0 and page.locator('[data-state="done"]').count() == 1, f"{bad.count()}")
    ok("ED-04 StatusPath: next=null thì không có dòng 'Tiếp theo: …' (hoặc báo hết việc)", page.get_by_text("Tiếp theo:").count() == 0)
    page.screenshot(path=f"{SHOTS}/qa-statuspath-badend-desktop.png")
    ok("ED-04 header: không nút chính khi không truyền (không nút rỗng)", page.locator("header button.btn.primary").count() == 0)
    page.get_by_role("button", name="Thao tác khác").click()
    dg = page.get_by_role("menuitem", name="Xoá nháp")
    ok("ED-04 '…' mục huỷ/xoá còn dùng được: chữ đỏ, không mờ", red(dg.locator("span").first.evaluate("e => getComputedStyle(e).color")) and dg.get_attribute("aria-disabled") != "true", dg.locator("span").first.evaluate("e => getComputedStyle(e).color"))
    bl = page.get_by_role("menuitem", name=re.compile("Chốt lô"))
    bl.focus()
    page.keyboard.press("Enter"); page.keyboard.press("Space")
    ok("ED-04 '…' mục bị chặn: Enter/Space không kích hoạt, menu còn mở", page.locator("#chosen").inner_text() == "" and page.get_by_role("menuitem").count() == 2)
    ok("ED-04 '…' mục bị chặn: focus được (để đọc lý do), lý do 'Lô còn 18,5 kg.' cạnh nhãn", "Lô còn 18,5 kg." in bl.inner_text())
    page.screenshot(path=f"{SHOTS}/qa-moremenu-blocked-desktop.png")
    dg.click()
    ok("ED-04 '…' mục xoá: chọn được -> gọi onSelect, menu đóng", page.locator("#chosen").inner_text() == "xoa" and page.get_by_role("menuitem").count() == 0)
    # Timeline rỗng
    ok("ED-04 Timeline rỗng: không vỡ trang (không 'undefined')", "undefined" not in page.locator("body").inner_text())
    # sửa tại chỗ: mất mạng
    ctx.close()
    ctx, page = new_ctx(browser, errors=errors)
    mode = {"m": "net"}
    def h(r):
        if r.request.method == "OPTIONS":
            return reply(r)
        if mode["m"] == "net":
            return r.abort("internetdisconnected")
        reply(r, 200, {})
    page.route(API + "/**", h)
    open_mode(page, "header")
    page.locator('button[aria-label="Sửa số lượng"]').click()
    i = page.locator("dl input").first
    i.fill("9")
    i.press("Enter")
    expect(page.locator("[data-editing] p", has_text=re.compile("mạng|chưa lưu", re.I))).to_be_visible()
    ok("ED-04 sửa tại chỗ mất mạng: ô vẫn mở, giữ '9', lỗi dưới ô", i.input_value() == "9" and page.locator("[data-editing] button.primary").inner_text() == "Thử lại")
    page.screenshot(path=f"{SHOTS}/qa-infofield-network-lost-desktop.png")
    mode["m"] = "ok"
    page.locator("[data-editing] button.primary").click()
    expect(page.locator("dl").get_by_text("9 kg")).to_be_visible()
    ok("ED-04 sửa tại chỗ: Thử lại thành công -> '9 kg', trả focus về bút chì", page.evaluate("() => document.activeElement.getAttribute('aria-label')") == "Sửa số lượng")
    ctx.close()
    # trang không vòng đời
    ctx, page = new_ctx(browser, errors=errors)
    open_mode(page, "header-empty")
    ok("ED-04 đối tượng không vòng đời: không StatusPath, không nút '…', không nút chính", page.locator("[data-state]").count() == 0 and page.get_by_role("button", name="Thao tác khác").count() == 0)
    ctx.close()


import datetime as _dt
def NOW_MINUS(sec):
    return (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=sec)).strftime("%Y-%m-%dT%H:%M:%SZ")


ACTION = {
    "id": "11111111-2222-3333-4444-555555555555", "command": "purchasing.purchasereceipt.submit", "title": "Xác nhận phiếu nhập hàng", "level": "C",
    "status": "PENDING", "owner_display": "AI của Lộc", "created_at": NOW_MINUS(60), "expires_at": None, "execute_after": None,
    "undo_until": None, "target": {"type": "purchasing.purchasereceipt", "code": "PR-260928-01"}, "downgrade_reason": None, "result_ref": None,
    "args_preview": {"item_code": "CA-001", "qty": "10.000"},
}


def ai_routes(page, status=None, actions=None, detail=None, confirm=None, reject=None, log=None, args=None):
    log = log if log is not None else []
    def h(route):
        req = route.request
        if req.method == "OPTIONS":
            return reply(route)
        path = req.url.replace(API, "")
        log.append(f"{req.method} {path}")
        if path.startswith("/api/ai/status"):
            return reply(route, *(status or (200, {"ai_enabled": True, "cloud_enabled": False, "model": None, "budget": None})))
        if re.match(r"/api/ai/actions/\?", path):
            row = dict(ACTION); row["args_preview"] = args or ACTION["args_preview"]
            return reply(route, *(actions or (200, {"count": 1, "next": None, "previous": None, "results": [row]})))
        if path.endswith("/confirm/"):
            if confirm and confirm[1] is None:
                return reply(route, confirm[0], raw="<html>Server Error</html>", ctype="text/html")
            return reply(route, *(confirm or (200, {"status": "DONE"})))
        if path.endswith("/reject/"):
            return reply(route, *(reject or (200, {"status": "REJECTED"})))
        if re.match(r"/api/ai/actions/[\w-]+/$", path):
            row = dict(ACTION); row["args_preview"] = args or ACTION["args_preview"]
            row["confirm_nonce"] = "abc123"; row["viewable_from"] = NOW_MINUS(10)
            return reply(route, *(detail or (200, row)))
        return reply(route, 404, {"detail": "x"})
    page.route(API + "/**", h)
    return log


def h_ai(browser, errors):
    # AI tắt: không khối, không gọi /actions
    ctx, page = new_ctx(browser, errors=errors)
    log = ai_routes(page, status=(200, {"ai_enabled": False}))
    open_mode(page, "ai"); page.wait_for_timeout(500)
    ok("ED-05-AC1 AI tắt (API thật): không khối AI, 0 request /api/ai/actions", page.locator("[data-ai-block]").count() == 0 and not any("/actions" in x for x in log), str(log))
    ctx.close()
    # status lỗi 500 -> fail-closed
    ctx, page = new_ctx(browser, errors=errors)
    log = ai_routes(page, status=(500, {"detail": "boom"}))
    open_mode(page, "ai"); page.wait_for_timeout(500)
    ok("ED-05-AC1 status 500: fail-closed, không khối, 0 /actions", page.locator("[data-ai-block]").count() == 0 and not any("/actions" in x for x in log), str(log))
    ctx.close()
    # mạng đứt ở status
    ctx, page = new_ctx(browser, errors=errors)
    page.route(API + "/**", lambda r: reply(r) if r.request.method == "OPTIONS" else r.abort("internetdisconnected"))
    open_mode(page, "ai"); page.wait_for_timeout(500)
    ok("ED-05-AC1 mất mạng khi hỏi status: không khối, trang không vỡ", page.locator("[data-ai-block]").count() == 0 and page.get_by_role("heading", name="PR-260928-01").count() == 1)
    ctx.close()
    # 403 danh sách -> ẩn khối
    ctx, page = new_ctx(browser, errors=errors)
    ai_routes(page, actions=(403, {"detail": "Bạn không có quyền."}))
    open_mode(page, "ai"); page.wait_for_timeout(600)
    ok("ED-05 danh sách đề xuất 403 (thiếu quyền): khối ẩn hẳn", page.locator("[data-ai-block]").count() == 0, str(page.locator("[data-ai-block]").count()))
    ctx.close()
    # danh sách 500 -> báo lỗi + Thử lại
    ctx, page = new_ctx(browser, errors=errors)
    ai_routes(page, actions=(500, {"detail": "boom"}))
    open_mode(page, "ai")
    expect(page.locator("[data-ai-block]")).to_be_visible()
    ok("ED-05 danh sách đề xuất 500: hiện lỗi tiếng Việt + 'Thử lại', không nói 'Chưa có đề xuất'", page.locator("[data-ai-block] [role=alert]").count() == 1 and page.locator("[data-ai-block]").get_by_role("button", name="Thử lại").count() == 1 and "Chưa có đề xuất" not in page.locator("[data-ai-block]").inner_text(), page.locator("[data-ai-block]").inner_text()[:140].replace("\n", " "))
    page.screenshot(path=f"{SHOTS}/qa-ai-list-error-desktop.png")
    ctx.close()
    # giá vốn / PII trong args_preview (BE lọc sẵn, FE là lớp 2)
    ctx, page = new_ctx(browser, errors=errors)
    ai_routes(page, args={"item_code": "CA-001", "qty": "10.000", "unit_cost": "555111", "landed_unit_cost": "666222", "customer_phone": "0912345678", "recipient_name": "Nguyễn Văn A", "address": "12 đường Thử", "customer": {"name": "Nguyễn A"}, "note": "Giao cho Nguyễn Văn A, SĐT 0912345678"})
    open_mode(page, "ai")
    card = page.locator("[data-proposal]")
    expect(card).to_be_visible()
    t = card.inner_text()
    ok("ED-04-AC9/AC10 FE là lớp phụ: khoá giá vốn/tên/SĐT/địa chỉ KHÔNG hiện trong đề xuất", not re.search(r"555111|666222|12 đường|customer|unit_cost|Giá vốn", t) and "Mã hàng" in t, t.replace("\n", " | ")[:200])
    ok("ED-04-AC10 khoá chữ tự do `note` không được hiện nguyên văn (BE coi là chữ tự do, có thể chứa tên/SĐT khách)", "Nguyễn" not in t and "0912345678" not in t, t.replace("\n", " | ")[:260])
    page.screenshot(path=f"{SHOTS}/qa-ai-note-pii-desktop.png")
    qty_row = [l for l in t.split("\n") if l.strip()]
    ok("G5 'Số lượng' đề xuất AI: BE trả qty '10.000' (Decimal 3 số lẻ = 10 kg) -> FE phải hiện '10 kg'/'10,0 kg', không '10.000' trần", re.search(r"10(,0+)? ?kg", t) is not None, t.replace("\n", " | ")[:200])
    ctx.close()

    # Đồng ý: các nhánh lỗi
    for label, conf, expect_msg in (
        ("409 đã xử lý", (409, {"detail": "đã xử lý", "code": "ALREADY"}), "đã được xử lý"),
        ("410 hết hạn", (410, {"detail": "hết hạn"}), "đã được xử lý"),
        ("500 thân HTML", (500, None), "Lỗi máy chủ"),
        ("403 thiếu quyền", (403, {"detail": "Bạn không có quyền đồng ý đề xuất này."}), "quyền"),
    ):
        ctx, page = new_ctx(browser, errors=errors)
        log = ai_routes(page, confirm=conf)
        open_mode(page, "ai")
        card = page.locator("[data-proposal]"); expect(card).to_be_visible()
        btn = card.get_by_role("button", name="Đồng ý", exact=True)
        expect(btn).to_be_enabled(timeout=8000)
        btn.click()
        page.wait_for_timeout(700)
        txt = page.locator("[data-ai-block]").inner_text()
        ok(f"ED-05 Đồng ý {label}: có thông báo tiếng Việt trong khối", expect_msg.lower() in txt.lower(), txt.replace("\n", " | ")[:200])
        ok(f"ED-05 Đồng ý {label}: không báo 'đã áp dụng' (onApplied không chạy)", page.evaluate("() => window.__applied || 0") == 0)
        ok(f"ED-05 Đồng ý {label}: 1 POST confirm", len([x for x in log if x.endswith('/confirm/')]) == 1, str(log))
        ctx.close()
    # mất mạng khi Đồng ý: nút mở lại, không áp dụng
    ctx, page = new_ctx(browser, errors=errors)
    state = {"n": 0}
    log = []
    def h(route):
        req = route.request
        if req.method == "OPTIONS":
            return reply(route)
        path = req.url.replace(API, "")
        log.append(f"{req.method} {path}")
        if path.endswith("/confirm/"):
            return route.abort("internetdisconnected")
        row = dict(ACTION)
        if path.startswith("/api/ai/status"):
            return reply(route, 200, {"ai_enabled": True})
        if re.match(r"/api/ai/actions/\?", path):
            return reply(route, 200, {"count": 1, "next": None, "previous": None, "results": [row]})
        row["confirm_nonce"] = "n"; row["viewable_from"] = NOW_MINUS(10)
        return reply(route, 200, row)
    page.route(API + "/**", h)
    open_mode(page, "ai")
    card = page.locator("[data-proposal]"); expect(card).to_be_visible()
    btn = card.get_by_role("button", name="Đồng ý", exact=True); expect(btn).to_be_enabled(timeout=8000)
    btn.click(); page.wait_for_timeout(600)
    txt = page.locator("[data-ai-block]").inner_text()
    ok("ED-05 Đồng ý khi mất mạng: có lỗi tiếng Việt, đề xuất còn, nút Đồng ý dùng lại được", page.locator("[data-ai-block] [role=alert]").count() == 1 and card.count() == 1 and card.get_by_role("button", name="Đồng ý", exact=True).is_enabled(), txt.replace("\n", " | ")[:200])
    page.screenshot(path=f"{SHOTS}/qa-ai-confirm-network-lost-desktop.png")
    ctx.close()
    # Hai lần bấm cùng một khung hình (JS)
    for kind, name in (("confirm", "Đồng ý"), ("reject", "Từ chối")):
        ctx, page = new_ctx(browser, errors=errors)
        log = ai_routes(page)
        open_mode(page, "ai")
        card = page.locator("[data-proposal]"); expect(card).to_be_visible()
        expect(card.get_by_role("button", name="Đồng ý", exact=True)).to_be_enabled(timeout=8000)
        page.evaluate("(n) => { const b=[...document.querySelectorAll('[data-proposal] button')].find(x=>x.textContent.trim()===n); b.click(); b.click(); b.click(); }", name)
        page.wait_for_timeout(700)
        n = len([x for x in log if x.endswith(f"/{kind}/")])
        ok(f"ED-05-AC6 '{name}': 3 lần click trong cùng 1 tác vụ JS -> chỉ 1 POST {kind}", n == 1, str(n))
        ctx.close()
    # Bấm đúp kiểu người thật (2 lần cách ~40ms); BE trả sau ~300ms như thật (giữ request rồi mới trả)
    for kind, name in (("confirm", "Đồng ý"), ("reject", "Từ chối")):
        ctx, page = new_ctx(browser, errors=errors)
        held = []
        log = []
        def make(held, log):
            def h(route):
                req = route.request
                if req.method == "OPTIONS":
                    return reply(route)
                path = req.url.replace(API, "")
                log.append(f"{req.method} {path}")
                if path.endswith("/confirm/") or path.endswith("/reject/"):
                    held.append(route)
                    return
                row = dict(ACTION)
                if path.startswith("/api/ai/status"):
                    return reply(route, 200, {"ai_enabled": True})
                if re.match(r"/api/ai/actions/\?", path):
                    return reply(route, 200, {"count": 0 if held else 1, "next": None, "previous": None, "results": [] if held else [row]})
                row["confirm_nonce"] = "n"; row["viewable_from"] = NOW_MINUS(10)
                return reply(route, 200, row)
            return h
        page.route(API + "/**", make(held, log))
        open_mode(page, "ai")
        card = page.locator("[data-proposal]"); expect(card).to_be_visible()
        expect(card.get_by_role("button", name="Đồng ý", exact=True)).to_be_enabled(timeout=8000)
        card.get_by_role("button", name=name, exact=True).click(click_count=2, delay=40)
        page.wait_for_timeout(300)
        for r in held:
            reply(r, 200, {"status": "DONE"})
        page.wait_for_timeout(500)
        n = len([x for x in log if x.endswith(f"/{kind}/")])
        ok(f"ED-05-AC6 '{name}': bấm đúp kiểu người thật (40ms, BE trả sau 300ms) chỉ 1 POST {kind}", n == 1, str(n))
        ctx.close()
    # màn cũ: đề xuất đã bị người khác xử lý (danh sách rỗng sau tải lại)
    ctx, page = new_ctx(browser, errors=errors)
    log = ai_routes(page, confirm=(409, {"detail": "x"}))
    open_mode(page, "ai")
    card = page.locator("[data-proposal]"); expect(card).to_be_visible()
    expect(card.get_by_role("button", name="Đồng ý", exact=True)).to_be_enabled(timeout=8000)
    # sau 409 danh sách tải lại trả rỗng
    ctx.unroute(API + "/**") if False else None
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    errs = []
    for fn in (h_form, h_triple, h_modal, h_field, h_header, h_ai):
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
