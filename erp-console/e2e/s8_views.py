# E2E S8 (Tổng quan · Đơn · Kho & lô): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/s8_views.py          # tắt server sau khi xong
#
# S8-AC1 (so với bản cũ): đặt LEGACY_BASE = URL phục vụ bản HTML cũ (index.html). Kịch bản lấy ĐÚNG JSON mock
# mà console mới dùng (window.__caveMock.dashboardJson), bơm vào bản cũ bằng page.route (chặn API Cloud Run),
# rồi so từng ô: KPI, 8 đơn, ≤20 lô, cận hạn, 8 dòng sổ kho. Không có LEGACY_BASE → bỏ qua phần so sánh.

import json
import os
import re

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
LEGACY_BASE = os.environ.get("LEGACY_BASE")  # vd http://127.0.0.1:3102/index.html
SHOTS = os.environ.get("SHOTS", "/tmp")
LEGACY_API = "https://cangca-api-675411800433.asia-southeast1.run.app"
SUMMARY = "GET /api/dashboard/summary/"
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()


def set_mode(page, mode):
    page.evaluate(f"() => localStorage.setItem('cave_erp_mock_dashboard', '{mode}')")


def mock_log(page):
    return page.evaluate("() => window.__caveMock.log.slice()")


def clear_log(page):
    page.evaluate("() => window.__caveMock.clearLog()")


def norm(s):
    """Chuẩn hoá ô để so bản cũ/mới: bỏ ₫, kg, khoảng trắng; ',' → '.'; 'MM-DD' → 'DD/MM'."""
    s = (s or "").replace(" ", " ").replace("₫", "").replace("kg", "").strip()
    m = re.fullmatch(r"(\d{2})-(\d{2})", s)
    if m:
        s = f"{m.group(2)}/{m.group(1)}"
    return re.sub(r"\s+", "", s).replace(",", ".")


def table_rows(page, tbody_selector, skip=()):
    rows = page.eval_on_selector_all(
        tbody_selector + " tr",
        # Bỏ chữ của icon Material (.mi) ở CẢ bản cũ lẫn mới: UI3 bỏ icon trang trí trong ô (cá, icon trạng thái),
        # so sánh vẫn là chữ dữ liệu của từng ô.
        "trs => trs.map(tr => [...tr.querySelectorAll('td')].filter(td => getComputedStyle(td).display !== 'none')"
        ".map(td => { const c = td.cloneNode(true); c.querySelectorAll('.mi').forEach(i => i.remove()); return c.textContent; }))",
    )
    return [[norm(c) for i, c in enumerate(r) if i not in skip] for r in rows]


def fonts_ready(page):
    """Chờ font icon tải xong trước khi đo/chụp — điều kiện, không ngủ (QA Q2, lô L6b)."""
    page.wait_for_function("() => document.fonts.status === 'loaded'")


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth")


SMALL_TAPS_JS = """() => [...document.querySelectorAll('button, a, input')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y < innerHeight
      && (r.height < 44 || (e.tagName !== 'INPUT' && r.width < 44));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []

    # ================= Desktop 1280 — Chủ (loc) =================
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.wait_for_url("**/overview/")
    set_mode(page, "ok")
    page.reload()
    expect(page.locator(".tile[data-kpi=revenue] .val")).not_to_have_text("—")
    fonts_ready(page)
    page.screenshot(path=f"{SHOTS}/s8-desktop-1280-overview-chu.png")

    new_kpis = {k: norm(page.locator(f".tile[data-kpi={k}] .val").inner_text()) for k in ["revenue", "pending", "near", "inventory"]}
    new_ov_orders = table_rows(page, "section[aria-labelledby=ov-orders] tbody")
    new_ov_batches = table_rows(page, "section[aria-labelledby=ov-batches] tbody")
    new_alerts = page.eval_on_selector_all(".alerts .alert", "els => els.map(e => { const c = e.cloneNode(true); c.querySelectorAll('.mi').forEach(i => i.remove()); return c.textContent; })")
    ok("AC1 Tổng quan: 8 đơn gần nhất", len(new_ov_orders) == 8, str(len(new_ov_orders)))
    ok("AC1 Tổng quan: lô ≤ 20, có dữ liệu", 0 < len(new_ov_batches) <= 20, str(len(new_ov_batches)))
    ok("AC3 Tổng quan Chủ: có cột Giá vốn/kg", page.locator("section[aria-labelledby=ov-batches] th", has_text="Giá vốn/kg").count() == 1)
    ok("AC3 Chủ: KPI giá trị tồn có số", new_kpis["inventory"] not in ("—", ""), new_kpis["inventory"])

    # Refresh: đúng 1 request mới
    clear_log(page)
    page.get_by_role("button", name="Làm mới").click()
    page.wait_for_function("s => window.__caveMock.log.includes(s)", arg=SUMMARY)
    expect(page.get_by_role("button", name="Làm mới")).to_be_enabled()
    ok("Làm mới → gọi lại summary 1 lần", mock_log(page) == [SUMMARY], str(mock_log(page)))

    # Cache chung: sang Kho & lô bằng menu + mở tab Hoạt động → không request thêm
    clear_log(page)
    page.locator(".nav a", has_text="Kho & lô").click()
    page.wait_for_url("**/inventory/")
    expect(page.locator("th", has_text="Giá vốn/kg")).to_have_count(1)
    page.get_by_role("tab", name="Hoạt động").click()
    expect(page.locator(".feed .fev")).to_have_count(8)
    ok("3 màn + Hoạt động dùng chung 1 response (không gọi thêm)", mock_log(page) == [], str(mock_log(page)))
    new_inv = table_rows(page, ".screen tbody")
    new_feed = page.eval_on_selector_all(".feed .fev", "els => els.map(e => e.querySelector('p').textContent + '|' + e.querySelector('time').textContent)")
    ok("AC3 Kho & lô Chủ: ô giá vốn có tiền", all("₫" in c for c in page.eval_on_selector_all(".screen tbody tr td:nth-child(6)", "t => t.map(x => x.textContent)")))
    page.get_by_role("tab", name="Trợ lý").click()
    ok("Trợ lý: 'đang được nối, sắp có' (bỏ regex)", page.get_by_text("Trợ lý đang được nối, sắp có").is_visible())
    page.screenshot(path=f"{SHOTS}/s8-desktop-1280-inventory-chu.png")

    # Tìm kiếm phía máy (bỏ dấu)
    search = page.get_by_placeholder("Tìm lô, mặt hàng, NCC, kho…")
    search.fill("ca thu")
    expect(page.locator(".screen tbody tr")).to_have_count(2)
    items = page.eval_on_selector_all(".screen tbody tr td:nth-child(2)", "t => t.map(x => x.textContent)")
    ok("Tìm 'ca thu' (không dấu) → chỉ các lô Cá thu", len(items) == 2 and all("Cá thu" in i for i in items), str(items))
    search.fill("zzz-khong-co")
    expect(page.get_by_text("Không khớp tìm kiếm")).to_be_visible()
    page.get_by_role("button", name="Xoá tìm").click()
    ok("Xoá tìm → hiện lại đủ lô", page.locator(".screen tbody tr").count() == len(new_inv))

    # Đơn
    page.locator(".nav a", has_text="Đơn & tiền").click()
    page.wait_for_url("**/orders/")
    expect(page.locator(".screen tbody tr")).to_have_count(8)
    new_orders = table_rows(page, ".screen tbody", skip=(4,))
    countdown = page.eval_on_selector_all(".screen tbody tr td:nth-child(5)", "t => t.map(x => x.textContent)")
    ok("Đơn: cột giữ chỗ còn có đếm lùi cho đơn BOOKED", any("′" in c for c in countdown), str(countdown))
    page.get_by_placeholder("Tìm mã đơn, khách, 4 số cuối SĐT…").fill("4561")
    expect(page.locator(".screen tbody tr")).to_have_count(1)
    ok("Đơn: tìm theo 4 số cuối SĐT", page.locator(".screen tbody tr").count() == 1)
    page.screenshot(path=f"{SHOTS}/s8-desktop-1280-orders-chu.png")

    summary_json = page.evaluate("() => window.__caveMock.dashboardJson('loc')")

    # AC4: API 500
    set_mode(page, "fail")
    page.goto(BASE + "/overview/")
    expect(page.get_by_text("Không tải được dữ liệu, thử lại")).to_be_visible()
    ok("AC4 có nút Thử lại, không trắng trang", page.get_by_role("button", name="Thử lại").is_visible() and page.locator(".nav").is_visible())
    set_mode(page, "ok")
    page.get_by_role("button", name="Thử lại").click()
    expect(page.locator(".tile[data-kpi=revenue]")).to_be_visible()
    ok("AC4 Thử lại sau khi hết lỗi → hiện số liệu", True)
    # Rỗng
    set_mode(page, "empty")
    page.reload()
    expect(page.get_by_text("Không có lô cận hạn.")).to_be_visible()
    # UI3: câu rỗng cụ thể theo bảng (kèm câu hướng dẫn) thay cho "Chưa có dữ liệu" chung.
    ok("Rỗng: bảng đơn báo 'Chưa có đơn nào', bảng lô báo 'Chưa có lô nào đang hoạt động'",
       page.locator("section[aria-labelledby=ov-orders] tbody").get_by_text("Chưa có đơn nào", exact=True).is_visible()
       and page.locator("section[aria-labelledby=ov-batches] tbody").get_by_text("Chưa có lô nào đang hoạt động", exact=True).is_visible())

    # Review #3: ô "Lô cận hạn" ghi số ngày theo near_expiry_days (cấp gốc) của BE, không cứng "14"
    set_mode(page, "ok")
    page.reload()
    near_json = page.evaluate("() => window.__caveMock.dashboardJson('loc')")
    days = near_json.get("near_expiry_days")
    expect(page.locator(".tile[data-kpi=near] .foot")).to_have_text(f"trong {days} ngày tới")
    ok("Review #3: có near_expiry_days (cấp gốc) → 'trong N ngày tới' lấy từ BE", days == 14, str(days))
    ok("Review #3: near_expiry_days KHÔNG nằm trong kpis (kpis giữ 4 key như BE)", "near_expiry_days" not in near_json["kpis"], str(near_json["kpis"]))
    set_mode(page, "nodays")
    page.reload()
    expect(page.locator(".tile[data-kpi=near] .val")).not_to_have_text("—")
    foot = page.locator(".tile[data-kpi=near] .foot").inner_text()
    ok("Review #3: BE cũ thiếu near_expiry_days → ẩn số ngày (không bịa 14)", "ngày tới" not in foot and foot.strip() != "", foot)
    set_mode(page, "ok")

    # Review #1: 403 ỔN ĐỊNH (luật FE/BE lệch) → mỗi lần mount màn không gọi lại /api/auth/me/
    set_mode(page, "forbidden")
    page.goto(BASE + "/overview/")
    page.wait_for_function("() => window.__caveMock.log.filter(x => x === 'GET /api/auth/me/').length >= 2")
    expect(page.get_by_role("button", name="Thử lại")).to_be_visible()
    page.wait_for_load_state("networkidle")
    # Chuyển màn bằng menu (điều hướng phía máy, AuthProvider giữ nguyên). Next đôi khi rơi về tải lại cả trang
    # ("Failed to fetch RSC payload" do prefetch bị huỷ bởi page.goto trước đó) — lần đó app khởi động lại nên gọi /me
    # là đúng; chỉ chấm các lần điều hướng mềm (dấu window.__softNav còn).
    soft = []
    for label, url in [("Kho & lô", "inventory"), ("Đơn & tiền", "orders"), ("Tổng quan", "overview"), ("Kho & lô", "inventory")]:
        clear_log(page)
        page.evaluate("() => { window.__softNav = true; }")
        page.locator(".nav a", has_text=label).click()
        page.wait_for_url(f"**/{url}/")
        page.wait_for_function("s => window.__caveMock && window.__caveMock.log.includes(s)", arg=SUMMARY)
        expect(page.get_by_role("button", name="Thử lại")).to_be_visible()
        if page.evaluate("() => window.__softNav === true"):
            soft.append((url, mock_log(page)))
    ok("Review #1: 403 ổn định, mount lại màn (điều hướng mềm) → gọi summary nhưng KHÔNG gọi lại /me",
       len(soft) >= 2 and all(lg == [SUMMARY] for _, lg in soft), str(soft))
    ok("Review #1: 403 ổn định → không báo 'Quyền vừa thay đổi'", page.locator(".perm-notice").count() == 0)
    set_mode(page, "ok")
    ctx.close()

    # ================= Review #1: có view_batch/view_salesorder nhưng THIẾU reports.view_dashboard =================
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.evaluate("() => window.__caveMock.patchUser('kho1', {denied_perms: ['reports.view_dashboard']})")
    login(page, "kho1")
    page.wait_for_url("**/deliveries/")
    labels = [l.split("\n")[-1].strip() for l in page.locator(".nav a").all_inner_texts()]
    ok("Review #1 kho1 thiếu view_dashboard: menu KHÔNG có Tổng quan / Đơn & tiền / Kho & lô",
       labels == ["Giao hàng", "Việc giao của tôi", "Mua hàng", "Kiểm kê", "Danh mục & giá"], str(labels))
    for path in ["/orders/", "/inventory/"]:
        page.goto(BASE + path)
        page.wait_for_load_state("networkidle")
        expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
        lg = mock_log(page)
        ok(f"Review #1 kho1 gõ {path}: ViewGuard chặn, không gọi summary, /me đúng 1 lần", lg == ["GET /api/auth/me/"], str(lg))
    page.get_by_role("tab", name="Hoạt động").click()
    expect(page.get_by_text("Bạn không có quyền xem sổ kho.")).to_be_visible()
    ok("Review #1 kho1 tab Hoạt động: báo không có quyền, không gọi summary", SUMMARY not in mock_log(page), str(mock_log(page)))
    page.screenshot(path=f"{SHOTS}/review-desktop-1280-kho1-no-dashboard.png")
    ctx.close()

    # ================= Quản lý (ql1) — S8-AC2 =================
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "ql1")
    page.wait_for_url("**/overview/")
    expect(page.locator(".tile[data-kpi=inventory] .val")).to_have_text("—")
    ok("AC2 Quản lý: KPI giá trị tồn ẩn", page.get_by_text("cần quyền xem giá vốn").is_visible())
    ok("AC2 Quản lý: Tổng quan không có cột giá vốn", page.locator("th", has_text="Giá vốn").count() == 0)
    page.goto(BASE + "/inventory/")
    expect(page.locator(".screen tbody tr").first).to_be_visible()
    ok("AC2 Quản lý: Kho & lô không có cột giá vốn", page.locator("th", has_text="Giá vốn").count() == 0 and "₫" not in page.locator(".screen tbody").inner_text())
    ql_json = page.evaluate("() => window.__caveMock.dashboardJson('ql1')")
    ok("AC2 JSON (mock theo BE) không có key unit_cost", all("unit_cost" not in b for b in ql_json["batches"]) and len(ql_json["batches"]) > 0)
    ok("AC2 JSON (mock theo BE L6) không có key kpis.inventory_value", "inventory_value" not in ql_json["kpis"], str(ql_json["kpis"]))
    ok("Review #3: kpis của Quản lý đúng 4 key như BE; near_expiry_days ở cấp gốc",
       sorted(ql_json["kpis"]) == ["booked_soon", "near_expiry", "pending_orders", "revenue_today"] and ql_json.get("near_expiry_days") == 14,
       str(sorted(ql_json["kpis"])))
    page.screenshot(path=f"{SHOTS}/s8-desktop-1280-inventory-quanly.png")
    ctx.close()

    # ================= Menu theo quyền THẬT của /api/auth/me/ (S6) =================
    for user, expected in [
        ("ql1", ["Tổng quan", "Đơn & tiền", "Giao hàng", "Kho & lô", "Mua hàng", "Kiểm kê", "Danh mục & giá"]),
        # nv_kho có catalog.view_item thật → thấy "Danh mục & giá" (điều phối chốt; phần giá ẩn ở S38/S39)
        ("kho1", ["Tổng quan", "Đơn & tiền", "Giao hàng", "Việc giao của tôi", "Kho & lô", "Mua hàng", "Kiểm kê", "Danh mục & giá"]),
    ]:
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page = ctx.new_page()
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        login(page, user)
        page.wait_for_url("**/overview/")
        expect(page.locator(".tile[data-kpi=revenue]")).to_be_visible()
        labels = [l.split("\n")[-1].strip() for l in page.locator(".nav a").all_inner_texts()]
        ok(f"Menu {user} theo quyền thật (Tổng quan = reports.view_dashboard)", labels == expected, str(labels))
        ok(f"{user}: Tổng quan không có cột giá vốn", page.locator("th", has_text="Giá vốn").count() == 0)
        ctx.close()

    # ================= giao1 — S8-AC5 =================
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "giao1")
    page.wait_for_url("**/my-deliveries/")
    for path in ["/overview/", "/inventory/", "/orders/"]:
        page.goto(BASE + path)
        page.wait_for_load_state("networkidle")
        expect(page.get_by_text("Bạn không có quyền xem mục này")).to_be_visible()
        log = mock_log(page)
        ok(f"AC5 giao1 {path}: chặn, không gọi summary", log == ["GET /api/auth/me/"], str(log))
    page.get_by_role("button", name="Mở ghi chú, trợ lý, hoạt động").click() if page.get_by_role("button", name="Mở ghi chú, trợ lý, hoạt động").is_visible() else None
    page.get_by_role("tab", name="Hoạt động").click()
    expect(page.get_by_text("Bạn không có quyền xem sổ kho.")).to_be_visible()
    ok("giao1 tab Hoạt động: báo không có quyền, không gọi API",
       page.get_by_text("Bạn không có quyền xem sổ kho.").is_visible() and mock_log(page) == ["GET /api/auth/me/"], str(mock_log(page)))
    ctx.close()

    # ================= Mobile 360 =================
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, device_scale_factor=2, is_mobile=True, has_touch=True, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(page, "loc")
    page.wait_for_url("**/overview/")
    expect(page.locator(".tile[data-kpi=revenue]")).to_be_visible()
    fonts_ready(page)
    for path, shot in [("/overview/", "overview"), ("/orders/", "orders"), ("/inventory/", "inventory")]:
        if path != "/overview/":
            page.goto(BASE + path)
            expect(page.locator(".screen tbody tr").first).to_be_visible()
            fonts_ready(page)
        ok(f"360 {path} không cuộn ngang", no_hscroll(page) <= 360, str(no_hscroll(page)))
        small = page.evaluate(SMALL_TAPS_JS)
        ok(f"360 {path} vùng bấm ≥44px", not small, str(small))
        page.screenshot(path=f"{SHOTS}/s8-mobile-360-{shot}.png")
    page.get_by_role("button", name="Mở ghi chú, trợ lý, hoạt động").click()
    page.get_by_role("tab", name="Hoạt động").click()
    expect(page.locator(".feed .fev")).to_have_count(8)
    ok("360 ngăn kéo Hoạt động không cuộn ngang", no_hscroll(page) <= 360)
    page.screenshot(path=f"{SHOTS}/s8-mobile-360-activity.png")
    page.keyboard.press("Escape")
    set_mode(page, "fail")
    page.goto(BASE + "/overview/")
    expect(page.get_by_text("Không tải được dữ liệu, thử lại")).to_be_visible()
    page.screenshot(path=f"{SHOTS}/s8-mobile-360-error.png")
    set_mode(page, "ok")
    ctx.close()

    # ================= S8-AC1: so với bản HTML cũ =================
    if LEGACY_BASE:
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        ctx.add_init_script("localStorage.setItem('cave_token', 'legacy-e2e')")
        page = ctx.new_page()
        hits = []

        def fulfil(route):
            if route.request.method == "OPTIONS":
                route.fulfill(status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"})
                return
            hits.append(route.request.url)
            route.fulfill(status=200, content_type="application/json", body=json.dumps(summary_json),
                          headers={"Access-Control-Allow-Origin": "*"})

        page.route(LEGACY_API + "/**", fulfil)

        def legacy_utf8(route):
            # File cũ không có <meta charset>; http.server không gửi charset → ép UTF-8 như Firebase Hosting.
            resp = route.fetch()
            route.fulfill(response=resp, headers={**resp.headers, "content-type": "text/html; charset=utf-8"})

        page.route(LEGACY_BASE, legacy_utf8)
        page.goto(LEGACY_BASE)
        page.wait_for_function("() => document.getElementById('kRev').textContent !== '—'")
        old_kpis = {k: norm(page.locator(sel).text_content()) for k, sel in
                    [("revenue", "#kRev"), ("pending", "#kPending"), ("near", "#kNear"), ("inventory", "#kInv")]}
        old_ov_orders = table_rows(page, "#ovOrders")
        old_ov_batches = table_rows(page, "#ovBatches")
        old_orders = table_rows(page, "#tbOrders", skip=(4,))
        old_inv = table_rows(page, "#tbInv")
        old_alerts = page.eval_on_selector_all("#ovAlerts .alert", "els => els.map(e => { const c = e.cloneNode(true); c.querySelectorAll('.mi').forEach(i => i.remove()); return c.textContent; })")
        old_feed = page.eval_on_selector_all("#feed .fev", "els => els.map(e => e.querySelector('p').textContent + '|' + e.querySelector('time').textContent)")
        ctx.close()

        def feed_norm(rows):
            return [norm(r.replace("(", " ").replace(")", " ")) for r in rows]

        def alert_norm(rows):
            return [norm(r) for r in rows]

        ok("AC1 bản cũ đã gọi API (JSON bơm vào)", len(hits) >= 1, str(hits))
        ok("AC1 KPI trùng bản cũ", new_kpis == old_kpis, f"mới={new_kpis} cũ={old_kpis}")
        ok("AC1 Tổng quan: 8 đơn trùng", new_ov_orders == old_ov_orders, f"\nmới={new_ov_orders}\ncũ={old_ov_orders}")
        ok("AC1 Tổng quan: bảng lô trùng", new_ov_batches == old_ov_batches, f"\nmới={new_ov_batches[:2]}\ncũ={old_ov_batches[:2]}")
        ok("AC1 cận hạn trùng", alert_norm(new_alerts) == alert_norm(old_alerts), f"\nmới={new_alerts}\ncũ={old_alerts}")
        ok("AC1 8 dòng sổ kho trùng", feed_norm(new_feed) == feed_norm(old_feed), f"\nmới={new_feed}\ncũ={old_feed}")
        ok("AC1 màn Đơn trùng (trừ cột đếm lùi)", new_orders == old_orders, f"\nmới={new_orders[:2]}\ncũ={old_orders[:2]}")
        ok("AC1 màn Kho & lô trùng", new_inv == old_inv, f"\nmới={new_inv[:2]}\ncũ={old_inv[:2]}")
    else:
        print("SKIP AC1 so với bản cũ (không có LEGACY_BASE)")

    browser.close()

# "Failed to fetch RSC payload": Next prefetch bị huỷ khi kịch bản page.goto/đóng context giữa chừng
# (log server = BrokenPipe, file index.txt vẫn 200) — không phải lỗi app.
relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "401" not in e
            and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]
ok("Không lỗi console (trừ font/401/500 cố ý)", not relevant, str(relevant[:5]))
fails = 0
for n, c, e in results:
    print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + e))
    fails += 0 if c else 1
print(f"{len(results) - fails}/{len(results)} PASS")
