# P8 Lô 6 (FE) — SR-19 AC1-AC3 (link bằng chứng đồng ý mở đúng phiên bản chính sách) và SR-20 AC3/AC5 (màn nghiệp vụ không tải AI khi AI tắt).
# + F6-2: nút "Để AI làm" hiện theo step.ai của server (không cần đồng ý model, không cần mở tab Trợ lý).
# + F6-1: nút "Nhờ" (DW-23) không phải tính năng AI -> AI tắt vẫn có nút và chạy được trên 4 màn (đơn, thanh toán, hoàn tiền, lô kho).
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
    page.locator(f'.order-open[data-id="{oid}"]').click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    expect(dlg.locator("header")).to_be_visible()
    settle(page)
    return dlg


def goto_client(page, path):
    """Đi bằng liên kết trong app (giữ trạng thái mock trong bộ nhớ), không tải lại trang."""
    page.evaluate("(p) => { window.history.pushState({}, '', p); window.dispatchEvent(new PopStateEvent('popstate')); }", path)


def sr19(browser):
    errors = []
    # --- AC1: Chủ bấm "Xem phiên bản" từ chi tiết đơn có bằng chứng đồng ý (đơn id chẵn) -> panel đúng phiên bản 1
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.get_by_role("link", name="Đơn hàng").first.click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    dlg = open_order(page, 102)
    link = dlg.get_by_role("link", name="Xem phiên bản")
    ok("SR19-AC1 Chủ thấy liên kết 'Xem phiên bản' ở đơn có bằng chứng", link.count() == 1)
    href = link.get_attribute("href") or ""
    ok("SR19-AC1 href chỉ mang id + version (không dữ liệu cá nhân)", re.fullmatch(r"/content/edit/\?id=\d+&version=\d+", href) is not None, href)
    link.click()
    page.wait_for_url(re.compile(r"/content/edit/"))
    panel = page.locator("[data-policy-version-sheet]")
    expect(panel).to_be_visible()
    expect(panel.get_by_text("MẪU-V1", exact=False)).to_be_visible()
    settle(page)
    title = page.get_by_role("dialog").first
    ok("SR19-AC1 tiêu đề 'Phiên bản 1 (khách đã đồng ý)'", page.get_by_text("Phiên bản 1 (khách đã đồng ý)").count() >= 1)
    ok("SR19-AC1 hiện nội dung V1, không lẫn V2", "MẪU-V1" in panel.inner_text() and "MẪU-V2" not in panel.inner_text())
    ok("SR19-AC1 giờ ghi rõ giờ Việt Nam", "giờ Việt Nam" in panel.inner_text(), re.sub(r"\s+", " ", panel.inner_text())[:200])
    ok("SR19-AC1 URL không chứa tên/SĐT", not re.search(r"09\d{8}|Chị|Anh", page.url), page.url)
    ok("SR19-AC1 chỉ đọc: panel không có ô nhập", panel.locator("input, textarea, [contenteditable=true]").count() == 0)
    page.screenshot(path=f"{SHOTS}/sr19-ac1-desktop.png")
    # Đóng panel -> về bài (không mất trang)
    page.keyboard.press("Escape")
    expect(panel).to_have_count(0)
    ok("SR19-AC1 Esc đóng panel, vẫn ở trang bài", "/content/edit/" in page.url)
    ctx.close()

    # --- AC2: version không tồn tại
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
    # version hợp lệ trên mobile
    page.goto(BASE + "/content/edit/?id=1&version=2")
    panel = page.locator("[data-policy-version-sheet]")
    expect(panel.get_by_text("MẪU-V2", exact=False)).to_be_visible()
    ok("SR19 version=2 hiện phiên bản 2 (mobile)", page.get_by_text("Phiên bản 2 (khách đã đồng ý)").count() >= 1)
    ok("SR19 mobile 360 không cuộn ngang (v2)", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/sr19-v2-mobile360.png")
    ctx.close()

    # --- AC3: manager thấy liên kết, warehouse_staff không thấy (warehouse_staff không vào được danh sách đơn)
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "ql1")
    page.get_by_role("link", name="Đơn hàng").first.click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    dlg = open_order(page, 102)
    ok("SR19-AC3 Quản lý thấy liên kết 'Xem phiên bản'", dlg.get_by_role("link", name="Xem phiên bản").count() == 1)
    ctx.close()

    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "kho1")
    nav_orders = page.get_by_role("link", name="Đơn hàng")
    ok("SR19-AC3 NV kho không có mục Đơn hàng để tới liên kết", nav_orders.count() == 0)
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    ok("SR19-AC3 NV kho không thấy 'Xem phiên bản' trên /orders", page.get_by_role("link", name="Xem phiên bản").count() == 0)
    ctx.close()
    return errors


def sr20_off(browser):
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => window.__caveMock.ai('off')")
    page.evaluate("() => window.__caveMock.clearLog()")
    # /orders + chi tiết đơn (có GuidancePanel)
    page.get_by_role("link", name="Đơn hàng").first.click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    dlg = open_order(page, 102)
    expect(dlg.get_by_text("Đã làm").first).to_be_visible()
    ok("SR20-AC3 /orders + chi tiết đơn: 0 request /api/ai/*", len(ai_calls(page)) == 0, str(ai_calls(page)))
    ok("SR20-AC3 AI tắt: không có nút 'Để AI làm'", dlg.get_by_role("button", name=re.compile("Để AI làm")).count() == 0)
    page.screenshot(path=f"{SHOTS}/sr20-ac3-orders-detail-desktop.png")
    page.keyboard.press("Escape")
    # payments, refunds, inventory bằng liên kết trong app
    for label, url_re, shot, sel in [
        ("Hàng chờ thanh toán", r"/orders/payments/?$", "payments", ".queue-open"),
        ("Phiếu hoàn chờ chuyển", r"/orders/refunds/?$", "refunds", ".refund-open"),
    ]:
        page.get_by_role("link", name=re.compile(label)).first.click()
        page.wait_for_url(re.compile(url_re))
        page.wait_for_load_state("networkidle")
        settle(page)
        expect(page.locator(sel).first).to_be_visible()
        ok(f"SR20-AC3 /orders/{shot}: 0 request /api/ai/*", len(ai_calls(page)) == 0, str(ai_calls(page)))
        page.screenshot(path=f"{SHOTS}/sr20-ac3-{shot}-desktop.png")
    inv = page.get_by_role("link", name=re.compile("Kho & lô")).first
    inv.click()
    page.wait_for_url(re.compile(r"/inventory/?$"))
    page.wait_for_load_state("networkidle")
    settle(page)
    expect(page.locator('button[title^="Xem chi tiết lô"]').first).to_be_visible()
    ok("SR20-AC3 /inventory: 0 request /api/ai/*", len(ai_calls(page)) == 0, str(ai_calls(page)))
    page.screenshot(path=f"{SHOTS}/sr20-ac3-inventory-desktop.png")
    ctx.close()
    return errors


def sr20_on(browser):
    errors = []
    # Mobile 360 để chụp thêm; ngăn phải mở bằng nút Shell
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); window.__caveMock.clearLog(); }")
    # Mở ngăn phải > tab Trợ lý để cổng AI hỏi trạng thái (status) và công bố "AI bật"
    page.get_by_role("link", name="Đơn hàng").first.click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    opener = page.get_by_role("button", name="Mở ghi chú, trợ lý, hoạt động")
    if opener.count() and opener.first.is_visible():
        opener.first.click()
    page.locator("#rr-tab-ai").click()
    expect(page.locator("#rr-pane-ai")).to_be_visible()
    settle(page)
    calls = ai_calls(page)
    ok("SR20-AC5 mở tab Trợ lý -> có gọi ai/status", any("status" in str(c) for c in calls), str(calls)[:200])
    page.locator("#rr-tab-notes").click()
    dlg = open_order(page, 102)
    btn = dlg.get_by_role("button", name=re.compile("Để AI làm")).first
    expect(btn).to_be_visible()
    ok("SR20-AC5 AI bật + đã đồng ý: thấy nút 'Để AI làm' (khối nạp động)", True)
    page.screenshot(path=f"{SHOTS}/sr20-ac5-before-desktop.png")
    page.evaluate("() => window.__caveMock.clearLog()")
    btn.click()
    settle(page)
    notice = dlg.get_by_text(re.compile("AI đã soạn nháp đề xuất"))
    expect(notice).to_be_visible()
    notice.first.evaluate("el => el.scrollIntoView({ block: 'center' })")
    ok("SR20-AC5 bấm 'Để AI làm' chạy được, có thông báo 'AI đã soạn nháp đề xuất'", notice.count() == 1, re.sub(r"\s+", " ", notice.first.inner_text())[:120])
    ok("SR20-AC5 có gọi lệnh AI khi bấm", len(ai_calls(page)) >= 1, str(ai_calls(page))[:200])
    page.screenshot(path=f"{SHOTS}/sr20-ac5-after-desktop.png")
    ctx.close()

    # Đồng ý chưa cấp -> không có nút
    ctx = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(false); window.__caveMock.clearLog(); }")
    page.get_by_role("link", name="Đơn hàng").first.click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    dlg = open_order(page, 102)
    # F6-2 (Duy chốt 30/09): SR-20-AC2 đổi — "Để AI làm" theo step.ai của server, không cần đồng ý tải model.
    expect(dlg.get_by_role("button", name=re.compile("Để AI làm")).first).to_be_visible()  # khối nạp động: chờ chunk về
    ok("F6-2 AI bật, CHƯA đồng ý model: vẫn thấy 'Để AI làm' (theo step.ai)", dlg.get_by_role("button", name=re.compile("Để AI làm")).count() == 1, f"count={dlg.get_by_role('button', name=re.compile('Để AI làm')).count()}")
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


def f61_off(browser):
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => window.__caveMock.ai('off')")
    page.evaluate("() => window.__caveMock.clearLog()")
    # 1) chi tiết đơn
    page.get_by_role("link", name="Đơn hàng").first.click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    dlg = open_order(page, 102)
    ok("F6-1 đơn: AI tắt không có 'Để AI làm'", dlg.get_by_role("button", name=re.compile("Để AI làm")).count() == 0)
    press_nho(page, dlg, "chi tiết đơn", "orders-detail")
    page.keyboard.press("Escape")
    # 2) thanh toán
    for label, url_re, shot, sel in [
        ("Hàng chờ thanh toán", r"/orders/payments/?$", "payments", ".queue-open"),
        ("Phiếu hoàn chờ chuyển", r"/orders/refunds/?$", "refunds", ".refund-open"),
    ]:
        page.get_by_role("link", name=re.compile(label)).first.click()
        page.wait_for_url(re.compile(url_re))
        page.wait_for_load_state("networkidle")
        settle(page)
        page.locator(sel).first.click()
        d = page.get_by_role("dialog")
        expect(d).to_be_visible()
        settle(page)
        press_nho(page, d, shot, shot)
        page.keyboard.press("Escape")
    # 3) lô kho
    page.get_by_role("link", name=re.compile("Kho & lô")).first.click()
    page.wait_for_url(re.compile(r"/inventory/?$"))
    page.wait_for_load_state("networkidle")
    settle(page)
    page.locator('button[title^="Xem chi tiết lô"]').first.click()
    d = page.get_by_role("dialog")
    expect(d).to_be_visible()
    settle(page)
    press_nho(page, d, "lô kho", "inventory")
    ctx.close()
    return errors


def f61_on(browser):
    """AI bật + đã đồng ý: 'Nhờ' và 'Để AI làm' cùng hiện, hành vi như trước."""
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); window.__caveMock.clearLog(); }")
    page.get_by_role("link", name="Đơn hàng").first.click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    opener = page.get_by_role("button", name="Mở ghi chú, trợ lý, hoạt động")
    if opener.count() and opener.first.is_visible():
        opener.first.click()
    page.locator("#rr-tab-ai").click()
    expect(page.locator("#rr-pane-ai")).to_be_visible()
    settle(page)
    page.locator("#rr-tab-notes").click()
    dlg = open_order(page, 102)
    expect(dlg.get_by_role("button", name=re.compile("Để AI làm")).first).to_be_visible()
    ok("F6-1 AI bật: vẫn có cả 'Để AI làm' và 'Nhờ'", dlg.get_by_role("button", name=NHO).count() >= 1)
    press_nho(page, dlg, "AI bật", "orders-detail-ai-on")
    ctx.close()

    # Mobile 360 (AI bật nhưng chưa đồng ý): 'Nhờ' vẫn có, bấm được, không cuộn ngang
    ctx = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(false); window.__caveMock.clearLog(); }")
    page.get_by_role("link", name="Đơn hàng").first.click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    dlg = open_order(page, 102)
    press_nho(page, dlg, "mobile 360", "orders-detail-mobile360")
    ok("F6-1 mobile 360 không cuộn ngang (Nhờ + thông báo)", no_hscroll(page))
    ctx.close()
    return errors


def f62(browser):
    errors = []
    # --- step.ai = {level:C}: tải lại trang, KHÔNG mở tab Trợ lý, KHÔNG cấp đồng ý -> thấy nút, bấm -> POST call + "AI đã soạn nháp"
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))  # page.goto huỷ prefetch đang bay: không phải lỗi app
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(false); }")
    page.goto(BASE + "/orders/")  # tải lại hẳn trang; cờ mock nằm ở localStorage nên còn nguyên
    page.wait_for_load_state("networkidle")
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    page.evaluate("() => window.__caveMock.clearLog()")
    ok("F6-2 tiền đề: chưa cấp đồng ý tải model", page.evaluate("() => localStorage.getItem('cave_erp_ai_consent') !== '1'"))
    dlg = open_order(page, 102)
    btn = dlg.get_by_role("button", name=re.compile("Để AI làm")).first
    expect(btn).to_be_visible()
    ok("F6-2 step.ai=C: thấy 'Để AI làm' dù chưa mở tab Trợ lý và chưa đồng ý model", dlg.get_by_role("button", name=re.compile("Để AI làm")).count() == 1)
    ok("F6-2 huy hiệu 'AI (C)' hiện ở bước", dlg.get_by_text(re.compile(r"AI \(C\)")).count() >= 1)
    ok("F6-2 mở chi tiết đơn chưa gọi /api/ai/status hay /commands", len(commands_status_calls(page)) == 0, str(ai_calls(page)))
    page.screenshot(path=f"{SHOTS}/f62-de-ai-lam-not-opened-assistant-desktop.png")
    page.evaluate("() => window.__caveMock.clearLog()")
    btn.click()
    settle(page)
    notice = dlg.get_by_text(re.compile("AI đã soạn nháp đề xuất"))
    expect(notice.first).to_be_visible()
    notice.first.evaluate("el => el.scrollIntoView({ block: 'center' })")
    calls = ai_calls(page)
    ok("F6-2 bấm 'Để AI làm' -> đúng 1 POST /api/ai/commands/.../call/", len([c for c in calls if "POST /api/ai/commands/" in str(c) and "/call/" in str(c)]) == 1, str(calls)[:200])
    ok("F6-2 bấm 'Để AI làm' -> thông báo 'AI đã soạn nháp đề xuất'", notice.count() == 1)
    ok("F6-2 không gọi /api/ai/status khi bấm", not any("/api/ai/status" in str(c) for c in calls), str(calls)[:200])
    page.screenshot(path=f"{SHOTS}/f62-de-ai-lam-after-desktop.png")
    # 'Nhờ' vẫn như F6-1 khi cùng có 'Để AI làm'
    ok("F6-2 'Nhờ' vẫn hiện cạnh 'Để AI làm'", dlg.get_by_role("button", name=NHO).count() >= 1)
    ctx.close()

    # --- step.ai = null (server tắt AI): tải lại, không có nút, 0 request AI; 'Nhờ' vẫn có
    ctx = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))  # page.goto huỷ prefetch đang bay: không phải lỗi app
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('off'); window.__caveMock.aiConsent(true); }")
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    page.evaluate("() => window.__caveMock.clearLog()")
    dlg = open_order(page, 102)
    expect(dlg.get_by_role("button", name=NHO).first).to_be_visible()
    ok("F6-2 step.ai=null: không có 'Để AI làm' (kể cả đã đồng ý model)", dlg.get_by_role("button", name=re.compile("Để AI làm")).count() == 0)
    ok("F6-2 step.ai=null: không có huy hiệu 'AI (C)'", dlg.get_by_text(re.compile(r"AI \(C\)")).count() == 0)
    ok("F6-2 step.ai=null: 0 request /api/ai/*", len(ai_calls(page)) == 0, str(ai_calls(page)))
    ok("F6-2 step.ai=null: 'Nhờ' vẫn còn", dlg.get_by_role("button", name=NHO).count() >= 1)
    ok("F6-2 mobile 360 không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/f62-step-ai-null-mobile360.png")
    ctx.close()
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
