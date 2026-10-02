# P8 Lô 6 (FE) — SR-19 AC1-AC3 (link bằng chứng đồng ý mở đúng phiên bản chính sách) và SR-20 AC3/AC5 (màn nghiệp vụ không tải AI khi AI tắt).
# + F6-2: nút "Để AI làm" hiện theo step.ai của server (không cần đồng ý model, không cần mở tab Trợ lý).
# + F6-1: nút "Nhờ" (DW-23) không phải tính năng AI -> AI tắt vẫn có nút và chạy được.
# VIẾT LẠI sau ERP theo design Lô 3 (02/10): đơn, khoản tiền, phiếu hoàn là TRANG chi tiết (/orders/detail/?id=...), không còn hộp bên phải
# (.order-open, .queue-open, .refund-open, ul.order-list đã bỏ). Ca nào còn đối tượng thì giữ ý cũ trên trang mới; ca nào hết đối tượng thì
# ghi rõ lý do bỏ ngay tại chỗ (dòng "BỎ:"). Lô kho (/inventory) chưa đổi nên giữ nguyên ca F6-1/F6-2 ở đó.
# Chạy trên bản build MOCK phục vụ tĩnh (dữ liệu bịa). Trạng thái mock nằm trong bộ nhớ trang: mỗi context mới bắt đầu từ seed.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out <thư-mục-out-riêng>
#   (cd <thư-mục-out-riêng> && python3 -m http.server 3216 --bind 127.0.0.1 &)
#   BASE=http://127.0.0.1:3216 SHOTS=<thư mục ảnh> python3 e2e/p8_lo6_fe_sr19_sr20.py     # tắt server sau khi xong
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3216")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)
    page.wait_for_timeout(150)


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def ai_calls(page):
    log = page.evaluate("() => window.__caveMock.log.slice()")
    return [e for e in log if "/api/ai/" in str(e)]


def open_order(page, oid):
    """Mở trang chi tiết đơn (tải thẳng: cờ AI mock nằm ở localStorage nên còn nguyên)."""
    page.goto(BASE + f"/orders/detail/?id={oid}")
    page.wait_for_load_state("networkidle")
    expect(page.locator("main header h2")).to_be_visible()
    settle(page)
    return page.locator("main")


def orders_list_ready(page):
    expect(page.locator("tbody tr").first).to_be_visible()
    settle(page)


def sr19(browser):
    errors = []
    # --- AC1: Chủ bấm "Xem phiên bản" từ trang chi tiết đơn có bằng chứng đồng ý (đơn id chẵn) -> panel đúng phiên bản 1
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    login(page, "loc")
    main = open_order(page, 102)
    link = main.get_by_role("link", name="Xem phiên bản")
    ok("SR19-AC1 Chủ thấy liên kết 'Xem phiên bản' ở đơn có bằng chứng", link.count() == 1)
    href = link.get_attribute("href") or ""
    ok("SR19-AC1 href chỉ mang id + version (không dữ liệu cá nhân)", re.fullmatch(r"/content/edit/\?id=\d+&version=\d+", href) is not None, href)
    link.click()
    page.wait_for_url(re.compile(r"/content/edit/"))
    panel = page.locator("[data-policy-version-sheet]")
    expect(panel).to_be_visible()
    expect(panel.get_by_text("MẪU-V1", exact=False)).to_be_visible()
    settle(page)
    ok("SR19-AC1 tiêu đề 'Phiên bản 1 (khách đã đồng ý)'", page.get_by_text("Phiên bản 1 (khách đã đồng ý)").count() >= 1)
    ok("SR19-AC1 hiện nội dung V1, không lẫn V2", "MẪU-V1" in panel.inner_text() and "MẪU-V2" not in panel.inner_text())
    ok("SR19-AC1 giờ ghi rõ giờ Việt Nam", "giờ Việt Nam" in panel.inner_text(), re.sub(r"\s+", " ", panel.inner_text())[:200])
    ok("SR19-AC1 URL không chứa tên/SĐT", not re.search(r"09\d{8}|Chị|Anh", page.url), page.url)
    ok("SR19-AC1 chỉ đọc: panel không có ô nhập", panel.locator("input, textarea, [contenteditable=true]").count() == 0)
    page.screenshot(path=f"{SHOTS}/sr19-ac1-desktop.png")
    page.keyboard.press("Escape")
    expect(panel).to_have_count(0)
    ok("SR19-AC1 Esc đóng panel, vẫn ở trang bài", "/content/edit/" in page.url)
    ctx.close()

    # --- AC2: version không tồn tại (không liên quan trang đơn, giữ nguyên)
    ctx = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "loc")
    page.goto(BASE + "/content/edit/?id=1&version=99")
    panel = page.locator("[data-policy-version-sheet]")
    expect(panel).to_be_visible()
    expect(panel.get_by_text("Không tìm thấy phiên bản 99")).to_be_visible()
    back = panel.get_by_role("button", name="Về bài")
    ok("SR19-AC2 có nút 'Về bài'", back.count() >= 1)
    ok("SR19-AC2 mobile 360 không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/sr19-ac2-mobile360.png")
    back.first.click()
    expect(page.locator("[data-policy-version-sheet]")).to_have_count(0)
    ok("SR19-AC2 'Về bài' đóng panel", True)
    page.goto(BASE + "/content/edit/?id=1&version=2")
    panel = page.locator("[data-policy-version-sheet]")
    expect(panel.get_by_text("MẪU-V2", exact=False)).to_be_visible()
    ok("SR19 version=2 hiện phiên bản 2 (mobile)", page.get_by_text("Phiên bản 2 (khách đã đồng ý)").count() >= 1)
    ok("SR19 mobile 360 không cuộn ngang (v2)", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/sr19-v2-mobile360.png")
    ctx.close()

    # --- AC3: Quản lý thấy liên kết trên trang đơn; NV kho không có đường tới
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "ql1")
    main = open_order(page, 102)
    ok("SR19-AC3 Quản lý thấy liên kết 'Xem phiên bản'", main.get_by_role("link", name="Xem phiên bản").count() == 1)
    ctx.close()

    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "kho1")
    ok("SR19-AC3 NV kho không có mục Đơn hàng để tới liên kết", page.get_by_role("link", name="Đơn hàng").count() == 0)
    page.goto(BASE + "/orders/detail/?id=102")
    page.wait_for_load_state("networkidle")
    ok("SR19-AC3 NV kho không thấy 'Xem phiên bản' trên trang đơn", page.get_by_role("link", name="Xem phiên bản").count() == 0)
    ctx.close()
    return errors


def sr20_off(browser):
    """SR-20-AC3: AI tắt thì màn nghiệp vụ không gọi AI. Danh sách 0 request; trang có khối AI chỉ được hỏi `status` tối đa 1 lần
    (cổng cần biết có hiện khối không, QA Lô 2) và tuyệt đối không có `counts`, `actions`, `commands`, chunk model."""
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    chunk_urls = []
    page.on("request", lambda r: chunk_urls.append(r.url) if re.search(r"wllama|\.wasm|ai-worker", r.url, re.I) else None)
    login(page, "loc")
    page.evaluate("() => window.__caveMock.ai('off')")

    def only_status(calls):
        return len(calls) <= 1 and all("/api/ai/status/" in str(c) for c in calls)

    # /orders (danh sách: 0 request AI, SR-20 / H2) rồi chi tiết đơn (có khối AI)
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    orders_list_ready(page)
    page.wait_for_timeout(300)
    ok("SR20-AC3 /orders (AI tắt): 0 request /api/ai/* (không `counts`)", len(ai_calls(page)) == 0, str(ai_calls(page)))
    ok("SR20-AC3 /orders (AI tắt): không có thanh 'AI đề xuất'", page.locator("[data-ai-bar]").count() == 0)
    page.screenshot(path=f"{SHOTS}/sr20-ac3-orders-desktop.png")
    main = open_order(page, 102)
    expect(page.get_by_text("Đã làm").first).to_be_visible()
    page.wait_for_timeout(300)
    ok("SR20-AC3 chi tiết đơn: chỉ tối đa 1 request /api/ai/status/, không gì khác", only_status(ai_calls(page)), str(ai_calls(page)))
    ok("SR20-AC3 chi tiết đơn: AI tắt không có khối Trợ lý AI, không ô 'Hỏi AI'", page.locator("[data-ai-block]").count() == 0 and page.get_by_label("Hỏi AI về chứng từ này").count() == 0)
    ok("SR20-AC3 AI tắt: không có nút 'Để AI làm'", main.get_by_role("button", name=re.compile("Để AI làm")).count() == 0)
    page.screenshot(path=f"{SHOTS}/sr20-ac3-orders-detail-desktop.png")
    for path, shot, sel in [
        ("/orders/payments/", "payments", "tbody tr"),
        ("/orders/payments/detail/?id=880", "payment-detail", "main header h2"),
        ("/orders/refunds/", "refunds", "tbody tr"),
        ("/orders/refunds/detail/?id=4", "refund-detail", "main header h2"),
    ]:
        page.goto(BASE + path)
        page.wait_for_load_state("networkidle")
        settle(page)
        expect(page.locator(sel).first).to_be_visible()
        page.wait_for_timeout(250)
        if "/detail/" in path:
            # Trang chi tiết khoản tiền / phiếu hoàn có khối Trợ lý AI (01 §3.7): AI tắt thì tối đa 1 request status, không /api/ai/actions, không khối.
            ok(f"SR20-AC3 {path}: chỉ tối đa 1 request /api/ai/status/, không /api/ai/actions", only_status(ai_calls(page)), str(ai_calls(page)))
            ok(f"SR20-AC3 {path}: AI tắt không có khối Trợ lý AI", page.locator("[data-ai-block]").count() == 0)
        else:
            ok(f"SR20-AC3 {path}: 0 request /api/ai/*", len(ai_calls(page)) == 0, str(ai_calls(page)))
        page.screenshot(path=f"{SHOTS}/sr20-ac3-{shot}-desktop.png")
    page.goto(BASE + "/inventory/")
    page.wait_for_load_state("networkidle")
    settle(page)
    expect(page.locator('button[title^="Xem chi tiết lô"]').first).to_be_visible()
    ok("SR20-AC3 /inventory: 0 request /api/ai/*", len(ai_calls(page)) == 0, str(ai_calls(page)))
    page.screenshot(path=f"{SHOTS}/sr20-ac3-inventory-desktop.png")
    ok("SR20-AC3 không tải chunk model/worker AI ở bất kỳ màn nào trên", len(chunk_urls) == 0, str(chunk_urls[:3]))
    ctx.close()
    return errors


def sr20_on(browser):
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); }")
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    orders_list_ready(page)
    ok("SR20-AC5 màn Đơn hàng không có tab Trợ lý (đã bỏ ngăn phải)", page.locator("#rr-tab-ai").count() == 0)
    ok("SR20-AC5 mở danh sách đơn (AI bật) chưa gọi /api/ai/* nào", len(ai_calls(page)) == 0, str(ai_calls(page))[:200])
    open_order(page, 102)
    ask = page.get_by_label("Hỏi AI về chứng từ này")
    expect(ask).to_be_visible()
    ok("SR20-AC5 AI bật + đã đồng ý: trang chi tiết có khối Trợ lý AI + ô hỏi nhanh (khối nạp động)", page.locator("[data-ai-block]").count() == 1)
    ok("SR20-AC5 chưa chạm ô hỏi: chưa gọi lệnh/chat AI, chưa nạp panel", not any("/api/ai/commands" in c or "/chat" in c for c in ai_calls(page)) and page.locator("[data-doc-chat]").count() == 0, str(ai_calls(page))[:200])
    # BỎ: "Để AI làm" ở hộp chi tiết đơn (F6-2) — trang chi tiết mới không còn khối Tiếp theo của GuidancePanel; việc AI đề xuất
    #     nay đi qua khối Trợ lý AI (đề xuất + Đồng ý/Từ chối), được e2e ở ed_batch2_patterns/ed_batch3_fixes (H1).
    page.screenshot(path=f"{SHOTS}/sr20-ac5-before-desktop.png")
    page.evaluate("() => window.__caveMock.clearLog()")
    ask.click()
    expect(page.locator("[data-doc-chat]")).to_be_visible()
    settle(page)
    ok("SR20-AC5 chạm ô hỏi mới nạp panel trợ lý", page.locator("[data-doc-chat]").count() == 1)
    page.screenshot(path=f"{SHOTS}/sr20-ac5-after-desktop.png")
    ctx.close()

    # AI bật nhưng chưa đồng ý model: khung hỏi vẫn có, bấm vào ra thẻ đồng ý, không cuộn ngang ở 360
    ctx = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(false); window.__caveMock.clearLog(); }")
    open_order(page, 102)
    ask = page.get_by_label("Hỏi AI về chứng từ này")
    expect(ask).to_be_visible()
    ok("F6-2 AI bật, CHƯA đồng ý model: khối AI + ô hỏi vẫn hiện (không bắt đồng ý trước)", page.locator("[data-ai-block]").count() == 1)
    ask.click()
    expect(page.get_by_text("Bật trợ lý trên máy")).to_be_visible()
    ok("F6-2 chưa đồng ý: chạm ô hỏi ra thẻ 'Bật trợ lý trên máy', 0 request chat/commands", not any("/chat" in c or "/commands" in c for c in ai_calls(page)), str(ai_calls(page))[:200])
    ok("SR20 mobile 360 không cuộn ngang (chi tiết đơn)", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/sr20-orders-detail-mobile360.png")
    ctx.close()
    return errors


NHO = re.compile("Nhờ")


def commands_status_calls(page):
    return [e for e in ai_calls(page) if "/api/ai/commands" in str(e) or "/api/ai/status" in str(e)]


def escalate_calls(page):
    return [e for e in ai_calls(page) if "/api/ai/actions/escalate" in str(e)]


def press_nho(page, scope, label, shot):
    """Kiểm: có nút 'Nhờ' trong scope, bấm -> thông báo 'Đã chuyển việc cho nhóm', 0 lệnh/status AI, có đúng 1 POST escalate."""
    btn = scope.get_by_role("button", name=NHO).first
    expect(btn).to_be_visible()
    ok(f"F6-1 {label}: AI tắt vẫn có nút 'Nhờ'", scope.get_by_role("button", name=NHO).count() >= 1)
    page.evaluate("() => window.__caveMock.clearLog()")
    btn.click()
    settle(page)
    notice = scope.get_by_text(re.compile("Đã chuyển việc cho nhóm"))
    expect(notice.first).to_be_visible()
    notice.first.evaluate("el => el.scrollIntoView({ block: 'center' })")
    ok(f"F6-1 {label}: bấm 'Nhờ' tạo được việc (thông báo 'Đã chuyển việc cho nhóm')", notice.count() == 1, re.sub(r"\s+", " ", notice.first.inner_text())[:120])
    ok(f"F6-1 {label}: nút chuyển sang 'Đã nhờ (...)' và khoá", scope.get_by_role("button", name=re.compile("Đã nhờ")).first.is_disabled())
    ok(f"F6-1 {label}: 0 request /api/ai/commands|status", len(commands_status_calls(page)) == 0, str(commands_status_calls(page)))
    ok(f"F6-1 {label}: đúng 1 POST /api/ai/actions/escalate/ do người bấm", len(escalate_calls(page)) == 1, str(ai_calls(page))[:200])
    page.screenshot(path=f"{SHOTS}/f61-nho-{shot}-desktop.png")


def open_first_batch(page):
    page.goto(BASE + "/inventory/")
    page.wait_for_load_state("networkidle")
    settle(page)
    page.locator('button[title^="Xem chi tiết lô"]').first.click()
    d = page.get_by_role("dialog")
    expect(d).to_be_visible()
    settle(page)
    return d


def f61_off(browser):
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => window.__caveMock.ai('off')")
    page.evaluate("() => window.__caveMock.clearLog()")
    # BỎ: nút 'Nhờ' ở chi tiết đơn / khoản tiền / phiếu hoàn: ba trang chi tiết mới (ED-09..ED-12) không dùng GuidancePanel nên không có
    #     nút Nhờ/Để AI làm (dev-notes Lô 3, chỗ lệch #6). Các ca này chỉ còn đối tượng ở lô kho (chưa đổi sang mẫu mới).
    page.goto(BASE + "/orders/detail/?id=102")
    page.wait_for_load_state("networkidle")
    settle(page)
    ok("F6-1 đơn (trang mới): AI tắt không có 'Để AI làm'", page.get_by_role("button", name=re.compile("Để AI làm")).count() == 0)
    page.get_by_role("link", name=re.compile("Kho & lô")).first.click()
    page.wait_for_url(re.compile(r"/inventory/?$"))
    page.wait_for_load_state("networkidle")
    settle(page)
    page.locator('button[title^="Xem chi tiết lô"]').first.click()
    d = page.get_by_role("dialog")
    expect(d).to_be_visible()
    settle(page)
    ok("F6-1 lô kho: AI tắt không có 'Để AI làm'", d.get_by_role("button", name=re.compile("Để AI làm")).count() == 0)
    press_nho(page, d, "lô kho", "inventory")
    ctx.close()
    return errors


def f61_on(browser):
    """AI bật + đã đồng ý: 'Nhờ' (lô kho) hiện, hành vi như trước."""
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); window.__caveMock.clearLog(); }")
    d = open_first_batch(page)
    ok("F6-1 AI bật: lô kho có nút 'Nhờ'", d.get_by_role("button", name=NHO).count() >= 1)
    press_nho(page, d, "AI bật (lô kho)", "inventory-ai-on")
    ctx.close()

    ctx = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(false); window.__caveMock.clearLog(); }")
    d = open_first_batch(page)
    press_nho(page, d, "mobile 360 (lô kho)", "inventory-mobile360")
    ok("F6-1 mobile 360 không cuộn ngang (Nhờ + thông báo)", no_hscroll(page))
    ctx.close()
    return errors


def f62(browser):
    errors = []
    # --- step.ai = null (server tắt AI): lô kho tải lại, không 'Để AI làm', 0 request AI; 'Nhờ' vẫn có
    ctx = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('off'); window.__caveMock.aiConsent(true); }")
    page.goto(BASE + "/inventory/")
    page.wait_for_load_state("networkidle")
    settle(page)
    expect(page.locator('button[title^="Xem chi tiết lô"]').first).to_be_visible()
    page.evaluate("() => window.__caveMock.clearLog()")
    page.locator('button[title^="Xem chi tiết lô"]').first.click()
    d = page.get_by_role("dialog")
    expect(d).to_be_visible()
    settle(page)
    expect(d.get_by_role("button", name=NHO).first).to_be_visible()
    ok("F6-2 step.ai=null: không có 'Để AI làm' (kể cả đã đồng ý model)", d.get_by_role("button", name=re.compile("Để AI làm")).count() == 0)
    ok("F6-2 step.ai=null: không có huy hiệu 'AI (C)'", d.get_by_text(re.compile(r"AI \(C\)")).count() == 0)
    ok("F6-2 step.ai=null: 0 request /api/ai/*", len(ai_calls(page)) == 0, str(ai_calls(page)))
    ok("F6-2 step.ai=null: 'Nhờ' vẫn còn", d.get_by_role("button", name=NHO).count() >= 1)
    ok("F6-2 mobile 360 không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/f62-step-ai-null-mobile360.png")
    ctx.close()
    # BỎ: ca "step.ai = {level:C}: bấm 'Để AI làm' -> POST /commands/.../call/" trên chi tiết đơn: trang đơn mới không có nút này (xem trên).
    #     Mock guidance của lô kho không trả step.ai nên cũng không có đối tượng khác để kiểm nhánh này; nhánh vẫn có vitest ở features/guidance.
    return errors


with sync_playwright() as p:
    browser = p.chromium.launch()
    errs = []
    for fn in (sr19, sr20_off, sr20_on, f61_off, f61_on, f62):
        try:
            errs += fn(browser)
        except Exception as e:  # noqa: BLE001
            ok(f"{fn.__name__} chạy hết không lỗi", False, repr(e)[:400])
    browser.close()

bad_errs = [e for e in errs if "favicon" not in e]
ok("Không có console.error", not bad_errs, "; ".join(bad_errs)[:300])
fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} PASS")
sys.exit(1 if fails else 0)
