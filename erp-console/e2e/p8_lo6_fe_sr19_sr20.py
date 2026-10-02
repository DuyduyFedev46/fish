# P8 Lô 6 (FE) — SR-19 AC1-AC3 (link bằng chứng đồng ý mở đúng phiên bản chính sách) và SR-20 AC3/AC5 (màn nghiệp vụ không tải AI khi AI tắt).
# + F6-2: nút "Để AI làm" hiện theo step.ai của server (không cần đồng ý model, không cần mở tab Trợ lý).
# + F6-1: nút "Nhờ" (DW-23) không phải tính năng AI -> AI tắt vẫn có nút và chạy được trên 4 màn (đơn, thanh toán, hoàn tiền, lô kho).
# ERP theo design Lô 7: màn Kho & lô là bảng + trang chi tiết lô (/inventory/detail/?id=); ca "lô kho" viết lại theo trang đó (xem các ghi chú "Lô 7" bên dưới).
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


def lot_links(page):
    """Danh sách lô của /inventory/: chờ hết dòng khung chờ rồi trả về các liên kết mở chi tiết lô (ô đầu mỗi dòng)."""
    page.wait_for_function("() => document.querySelectorAll('table.lt tr.lt-skel').length === 0", timeout=10_000)
    return page.locator("table.lt tbody tr a")


def open_first_lot(page):
    """Mở chi tiết lô đầu tiên bằng liên kết trong bảng (giữ trạng thái mock), chờ số tồn hiện."""
    lot_links(page).first.click()
    page.wait_for_url(re.compile(r"/inventory/detail/\?id=\d+"))
    page.locator("[data-testid=qty-available]").wait_for(timeout=10_000)
    settle(page)
    page.wait_for_timeout(500)


AI_RUN = re.compile(r"/api/ai/commands|/call/|/api/ai/actions")


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
    expect(lot_links(page).first).to_be_visible()
    ok("SR20-AC3 /inventory: 0 request /api/ai/*", len(ai_calls(page)) == 0, str(ai_calls(page)))
    page.screenshot(path=f"{SHOTS}/sr20-ac3-inventory-desktop.png")
    # Lô 7: chi tiết lô là trang riêng; AI tắt thì không có khối Trợ lý và không có lệnh AI nào chạy.
    open_first_lot(page)
    ok("SR20-AC3 /inventory/detail: AI tắt, không có lệnh AI (commands, call, actions)", not [c for c in ai_calls(page) if AI_RUN.search(str(c))], str(ai_calls(page)))
    ok("SR20-AC3 /inventory/detail: AI tắt, không có khối Trợ lý (ô hỏi nhanh, 'Để AI làm')",
       page.get_by_role("button", name="Tóm tắt lịch sử chứng từ này").count() == 0 and page.get_by_role("button", name=re.compile("Để AI làm")).count() == 0)
    page.screenshot(path=f"{SHOTS}/sr20-ac3-inventory-detail-desktop.png")
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
    # ED Lô 1: không còn ngăn phải / tab Trợ lý. "Để AI làm" theo step.ai của server (F6-2), không cần ai/status.
    page.get_by_role("link", name="Đơn hàng").first.click()
    page.wait_for_url(re.compile(r"/orders/?$"))
    expect(page.locator("ul.order-list > li").first).to_be_visible()
    settle(page)
    ok("SR20-AC5 màn Đơn hàng không có tab Trợ lý (đã bỏ ngăn phải)", page.locator("#rr-tab-ai").count() == 0)
    ok("SR20-AC5 mở danh sách đơn chưa gọi ai/status", not any("status" in str(c) for c in ai_calls(page)), str(ai_calls(page))[:200])
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


def sr20_inventory_on(browser):
    """Lô 7 (thay phần lô kho của ca AI bật): AI bật + đã đồng ý, trang chi tiết lô có khối Trợ lý, hỏi đúng chứng từ lô."""
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); window.__caveMock.clearLog(); }")
    page.get_by_role("link", name=re.compile("Kho & lô")).first.click()
    page.wait_for_url(re.compile(r"/inventory/?$"))
    page.wait_for_load_state("networkidle")
    settle(page)
    ok("SR20-AC5 /inventory (danh sách) AI bật: chưa gọi AI", len(ai_calls(page)) == 0, str(ai_calls(page)))
    lot_links(page).filter(has_text="L0908-CT00").first.click()
    page.locator("[data-testid=qty-available]").wait_for(timeout=10_000)
    settle(page)
    page.wait_for_timeout(600)
    ok("SR20-AC5 chi tiết lô AI bật: có khối Trợ lý (ô hỏi nhanh)", page.get_by_role("button", name="Tóm tắt lịch sử chứng từ này").count() == 1)
    asks = [c for c in ai_calls(page) if "target_model=inventory.batch" in str(c)]
    ok("SR20-AC5 khối Trợ lý hỏi theo mã lô VÀ pk (TL7-M1: 'L0908-CT00,901')", asks and "L0908-CT00" in str(asks[-1]) and "901" in str(asks[-1]), str(asks)[:200])
    ok("SR20-AC5 mở chi tiết lô chưa chạy lệnh AI nào (chỉ khi người dùng chạm)", not [c for c in ai_calls(page) if AI_RUN.search(str(c)) and "/call/" in str(c)], str(ai_calls(page))[:200])
    page.screenshot(path=f"{SHOTS}/sr20-ac5-inventory-detail-ai-on-desktop.png")
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
    # 3) lô kho. Lô 7: trang chi tiết lô KHÔNG còn nút "Nhờ" (đó là nút của tấm GuidancePanel cũ, đã bị thay bằng khối Trợ lý
    #    AiBlockFrame, chỉ hiện khi AI bật; việc ESCALATED khi AI tắt để Lô 15). Ý kiểm của F6-1 là "AI tắt vẫn làm được việc
    #    thật" nên viết lại thành: menu 'Thao tác khác' của lô quá hạn vẫn đủ mục, mở được hộp Trả nhà cung cấp, 0 lệnh AI.
    page.get_by_role("link", name=re.compile("Kho & lô")).first.click()
    page.wait_for_url(re.compile(r"/inventory/?$"))
    page.wait_for_load_state("networkidle")
    settle(page)
    page.evaluate("() => window.__caveMock.clearLog()")
    lot_links(page).filter(has_text="L0908-CT00").first.click()
    page.locator("[data-testid=qty-available]").wait_for(timeout=10_000)
    settle(page)
    page.get_by_role("button", name="Thao tác khác").click()
    items = [re.sub(r"\s+", " ", x).strip() for x in page.get_by_role("menuitem").all_inner_texts()]
    ok("F6-1 lô kho: AI tắt, menu 'Thao tác khác' vẫn đủ mục xử lý lô quá hạn", any(i.startswith("Trả nhà cung cấp") for i in items) and any(i.startswith("Huỷ phần tồn") for i in items), str(items))
    page.get_by_role("menuitem", name=re.compile("^Trả nhà cung cấp")).click()
    rts = page.get_by_role("dialog", name="Trả nhà cung cấp")
    expect(rts).to_be_visible()
    ok("F6-1 lô kho: AI tắt, mở được hộp 'Trả nhà cung cấp' và 0 lệnh AI", not [c for c in ai_calls(page) if AI_RUN.search(str(c))], str(ai_calls(page)))
    page.screenshot(path=f"{SHOTS}/f61-lo-kho-ai-tat-desktop.png")
    page.keyboard.press("Escape")
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
    for fn in (sr19, sr20_off, sr20_on, sr20_inventory_on, f61_off, f61_on, f62):
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
