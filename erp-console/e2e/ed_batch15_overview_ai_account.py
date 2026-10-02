# E2E ERP theo design, Lô 15 (ED-06 Tài khoản, ED-08 Tổng quan + AI của tôi, ED-41 Nhật ký + Chính sách AI + Báo cáo AI, ED-42):
# chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out /tmp/out15 && (cd /tmp/out15 && python3 -m http.server 3951 &)
#   BASE=http://127.0.0.1:3951 SHOTS=shots/lo15 python3 e2e/ed_batch15_overview_ai_account.py      # tắt server sau khi xong
# Kiểm 5 vai (loc, ql1, kho1, giao1, cs2):
#  - Tổng quan: loc thấy 5 ô + giá trị tồn + cột Giá vốn/kg; ql1/kho1 KHÔNG có ô giá trị tồn, không có cột/giá vốn trong DOM; giao1/cs2: Không có quyền.
#    Dòng "đề xuất AI chờ duyệt" chỉ khi AI bật; lỗi 500 báo rõ + Thử lại; mã đơn SO…; không tên/SĐT khách.
#  - Nhật ký: loc/ql1 xem + lọc loại AI + tìm không ra + Tải thêm; kho1/giao1/cs2: Không có quyền và KHÔNG có request audit-logs.
#  - AI của tôi: loc/ql1/kho1/cs2 mở được, giao1 bị chặn; lưu thiếu ô trách nhiệm thì báo tại ô, KHÔNG gọi API; ngưỡng sai thì báo đỏ;
#    lưu đúng thì có thông báo; Tắt trợ lý có hỏi lại.
#  - Chính sách AI + Báo cáo AI: chỉ loc; ql1/kho1/giao1/cs2 Không có quyền. Báo cáo: lùi ngày thành rỗng, lỗi 500 báo rõ, ngày sau bị khoá hôm nay.
#  - Tài khoản: cả 5 vai; đổi mật khẩu sai mật khẩu hiện tại, nhập lại không khớp (không gọi API), thành công; phiên đăng nhập ghi giờ;
#    đăng xuất xoá mốc giờ. Tên/SĐT không nằm ở URL, localStorage (ngoài kho giả cave_erp_mock_*), sessionStorage.
#  - 360px không cuộn ngang, không icon rỗng (font tập con thiếu glyph), không lỗi console.
import os
import re

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3951")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)
PHONE_RE = re.compile(r"0\d{9}")
BAD_WORDS = ("undefined", "NaN", "[object", "BR-AI", "AI_POLICY")
MISSING_ICONS = "() => [...new Set([...document.querySelectorAll('.mi')].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.textContent))]"


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user, pw="demo1234", wait_nav=True):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    if wait_nav:
        page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    settle(page)


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def missing_icons(page):
    return page.evaluate(MISSING_ICONS)


def new_page(browser, user, w=1280, h=860, errors=None, ai=False, wait_nav=True):
    errors = errors if errors is not None else []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, user, wait_nav=wait_nav)
    if ai:
        page.evaluate("() => window.__caveMock.ai('on')")
    return ctx, page, errors


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage).filter(e => e[0] !== 'cave_erp_token' && !e[0].startsWith('cave_erp_mock_')), Object.entries(sessionStorage).filter(e => !e[0].startsWith('cave_erp_mock_'))])")


def log(page):
    return page.evaluate("() => window.__caveMock.log.slice()")


def clear_log(page):
    page.evaluate("() => window.__caveMock.clearLog()")


def no_perm(page):
    return page.get_by_role("heading", name=page.evaluate("() => window.__caveMock.msg.noViewPermission")).count() == 1


def main_text(page):
    return page.locator("main").inner_text()


def clean_text(name, text):
    ok(f"{name}: không có chữ lỗi (undefined, NaN, mã BE thô)", not any(w in text for w in BAD_WORDS), next((w for w in BAD_WORDS if w in text), ""))


def toast_text(page):
    return page.locator(".toast-item").first.inner_text()


# ---------------------------------------------------------------- Tổng quan
def overview_owner(browser):
    ctx, page, errors = new_page(browser, "loc", ai=True)
    go(page, "/overview/")
    expect(page.locator(".tile[data-kpi]").first).to_be_visible()
    kpis = page.locator(".tile[data-kpi]")
    keys = [kpis.nth(i).get_attribute("data-kpi") for i in range(kpis.count())]
    ok("loc: 5 ô số liệu gồm giá trị tồn kho", keys == ["revenue", "pending", "soon", "near", "inventory"], str(keys))
    text = main_text(page)
    ok("loc: có cột Giá vốn/kg và giá trị tồn", "Giá vốn/kg" in text and page.locator(".tile[data-kpi=inventory] .val").inner_text().strip() != "")
    ok("loc: mã đơn dạng SO…, không còn DH-", bool(re.search(r"\bSO\d", text)) and "DH-" not in text)
    ok("loc: bảng đơn có cột Còn giữ chỗ riêng, đang đếm mm:ss", "Còn giữ chỗ" in text and bool(re.search(r"\b\d{2}:\d{2}\b", text)))
    ok("loc: không tên/SĐT khách", not PHONE_RE.search(text), "")
    ok("loc: khối Cần chú ý có dòng lô quá hạn bấm sang kho lọc EXPIRED",
       page.locator("[data-attention=expired_batches_open] a").get_attribute("href") == "/inventory/?status=EXPIRED")
    ai_row = page.locator("[data-attention=ai_proposals]")
    expect(ai_row).to_be_visible()
    ok("loc (AI bật): có dòng đề xuất AI chờ duyệt, bấm sang /ai/actions/", ai_row.get_by_role("link").get_attribute("href") == "/ai/actions/" and "đề xuất AI chờ duyệt" in ai_row.inner_text())
    ok("loc: không icon rỗng, không cuộn ngang", missing_icons(page) == [] and no_hscroll(page), str(missing_icons(page)))
    clean_text("loc tổng quan", text)
    page.screenshot(path=f"{SHOTS}/lo15-overview-loc-1280.png", full_page=True)

    # Dark mode giữ đọc được (không chữ trắng trên nền trắng): chỉ kiểm tương phản tối thiểu của số liệu
    page.evaluate("() => document.documentElement.setAttribute('data-theme','dark')")
    c = page.evaluate("() => { const e = document.querySelector('.tile[data-kpi=revenue] .val'); const s = getComputedStyle(e); return [s.color, getComputedStyle(document.body).backgroundColor]; }")
    ok("loc: giao diện tối, số liệu khác màu nền", c[0] != c[1], str(c))
    page.screenshot(path=f"{SHOTS}/lo15-overview-loc-dark.png", full_page=True)
    page.evaluate("() => document.documentElement.removeAttribute('data-theme')")

    # Lỗi 500 → báo rõ + Thử lại; rồi phục hồi
    page.evaluate("() => window.__caveMock.dashboard('fail')")
    page.goto(BASE + "/overview/")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("button", name="Thử lại").first).to_be_visible()
    ok("loc: dashboard lỗi 500 → báo lỗi + Thử lại, không trắng trang", page.get_by_role("button", name="Thử lại").count() >= 1)
    # mock `dashboard()` ghi vào localStorage → đặt lại rồi bấm Thử lại
    page.evaluate("() => window.__caveMock.dashboard('ok')")
    page.get_by_role("button", name="Thử lại").first.click()
    expect(page.locator(".tile[data-kpi]").first).to_be_visible()
    ok("loc: bấm Thử lại → số liệu hiện lại", page.locator(".tile[data-kpi]").count() == 5)

    # Dashboard rỗng
    page.evaluate("() => window.__caveMock.dashboard('empty')")
    page.goto(BASE + "/overview/")
    page.wait_for_load_state("networkidle")
    settle(page)
    expect(page.get_by_text("Chưa có đơn nào")).to_be_visible()
    ok("loc: dashboard rỗng → 'Chưa có đơn nào' và 'Chưa có lô nào'", page.get_by_text("Chưa có lô nào đang hoạt động").count() == 1)
    ok("loc: rỗng vẫn có dòng 'Không có lô cận hạn'", "Không có lô cận hạn" in main_text(page))
    page.evaluate("() => window.__caveMock.dashboard('ok')")

    ok("loc: không lỗi console", errors == [], str(errors))
    ctx.close()

    # AI tắt (mặc định mock) → không có dòng đề xuất AI, không có request /api/ai/actions
    ctx, page, errors = new_page(browser, "loc")
    clear_log(page)
    go(page, "/overview/")
    expect(page.locator(".tile[data-kpi]").first).to_be_visible()
    page.wait_for_timeout(400)
    settle(page)
    ok("loc (AI tắt): không có dòng đề xuất AI", page.locator("[data-attention=ai_proposals]").count() == 0)
    ok("loc (AI tắt): không gọi đếm đề xuất AI", not any("ai/actions" in e for e in log(page)), str([e for e in log(page) if "ai" in e]))
    ctx.close()

    # 360px
    ctx, page, errors = new_page(browser, "loc", w=360, h=800, ai=True)
    go(page, "/overview/")
    expect(page.locator(".tile[data-kpi]").first).to_be_visible()
    ok("loc 360px: không cuộn ngang trang", no_hscroll(page))
    ok("loc 360px: không icon rỗng", missing_icons(page) == [], str(missing_icons(page)))
    page.screenshot(path=f"{SHOTS}/lo15-overview-loc-360.png", full_page=True)
    ctx.close()


def overview_no_cost(browser, user):
    ctx, page, errors = new_page(browser, user)
    go(page, "/overview/")
    expect(page.locator(".tile[data-kpi]").first).to_be_visible()
    html = page.content()
    text = main_text(page)
    ok(f"{user}: KHÔNG có ô giá trị tồn kho", page.locator(".tile[data-kpi=inventory]").count() == 0 and page.locator(".tile[data-kpi]").count() == 4)
    ok(f"{user}: KHÔNG có cột Giá vốn/kg và chữ giá vốn trong DOM", "Giá vốn" not in text and "Giá trị tồn kho" not in text and "unit_cost" not in html, "")
    ok(f"{user}: không tên/SĐT khách", not PHONE_RE.search(text))
    ok(f"{user}: không cuộn ngang, không icon rỗng", no_hscroll(page) and missing_icons(page) == [], str(missing_icons(page)))
    ok(f"{user}: không lỗi console", errors == [], str(errors))
    page.screenshot(path=f"{SHOTS}/lo15-overview-{user}-1280.png", full_page=True)
    ctx.close()
    ctx, page, errors = new_page(browser, user, w=360, h=800)
    go(page, "/overview/")
    expect(page.locator(".tile[data-kpi]").first).to_be_visible()
    ok(f"{user} 360px: không cuộn ngang trang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo15-overview-{user}-360.png", full_page=True)
    ctx.close()


def overview_forbidden(browser, user):
    ctx, page, errors = new_page(browser, user)
    clear_log(page)
    go(page, "/overview/")
    ok(f"{user}: Tổng quan → Không có quyền", no_perm(page))
    ok(f"{user}: không gọi dashboard", not any("dashboard" in e for e in log(page)), str(log(page)))
    ctx.close()


# ---------------------------------------------------------------- Nhật ký
def audit(browser):
    ctx, page, errors = new_page(browser, "loc", ai=True)
    go(page, "/audit-logs/")
    expect(page.locator("main tbody tr").first).to_be_visible()
    rows = page.locator("main tbody tr")
    first = rows.count()
    text = main_text(page)
    ok("loc: nhật ký có dòng, có cột Người làm / Người duyệt / Thao tác / Thay đổi", first > 0 and all(h in text for h in ("Người làm", "Người duyệt", "Thao tác", "Thay đổi")), str(first))
    ok("loc: không SĐT, không JSON thô, không chữ lỗi", not PHONE_RE.search(text) and "{" not in text)
    clean_text("loc nhật ký", text)
    ok("loc: không icon rỗng, không cuộn ngang", missing_icons(page) == [] and no_hscroll(page), str(missing_icons(page)))
    page.screenshot(path=f"{SHOTS}/lo15-audit-loc-1280.png", full_page=True)
    # lọc Loại = AI
    page.get_by_role("group", name="Lọc theo loại người làm").get_by_role("button", name="AI", exact=True).click()
    settle(page)
    expect(page.locator("main tbody tr").first).to_be_visible()
    ai_rows = page.locator("main tbody tr").count()
    ok("loc: lọc loại AI → ít dòng hơn tổng và mọi dòng có nhãn AI", 0 < ai_rows <= first and page.locator("main tbody tr", has_text="AI").count() == ai_rows, f"{ai_rows}/{first}")
    page.get_by_role("group", name="Lọc theo loại người làm").get_by_role("button", name="Tất cả", exact=True).click()
    settle(page)
    # tìm không ra → trạng thái rỗng có lối thoát
    page.get_by_role("searchbox", name="Tìm trong nhật ký đã tải").fill("zzzz-khong-co-ma-nay")
    expect(page.get_by_text(re.compile("Không tìm thấy dòng nhật ký khớp với"))).to_be_visible()
    ok("loc: tìm không ra → báo rỗng nêu từ khoá, không bảng trống trơn", True)
    page.get_by_role("searchbox", name="Tìm trong nhật ký đã tải").fill("")
    # khoảng ngày ở tương lai xa → rỗng; xoá đi → có lại
    page.locator('input[aria-label="Từ ngày"]').fill("2030-01-01")
    expect(page.get_by_text("Không có dòng nào khớp bộ lọc")).to_be_visible()
    ok("loc: khoảng ngày không có dòng nào → báo rỗng theo bộ lọc", True)
    page.locator('input[aria-label="Từ ngày"]').fill("")
    expect(page.locator("main tbody tr").first).to_be_visible()
    # Tải thêm
    more = page.get_by_role("button", name="Tải thêm")
    if more.count():
        more.click()
        settle(page)
        ok("loc: Tải thêm → nhiều dòng hơn", page.locator("main tbody tr").count() > first, f"{first}→{page.locator('main tbody tr').count()}")
    else:
        ok("loc: Tải thêm (mock có 24 dòng, trang 20)", False, "không thấy nút")
    ok("loc: không lỗi console", errors == [], str(errors))
    ctx.close()

    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/audit-logs/")
    expect(page.locator("main tbody tr").first).to_be_visible()
    ok("ql1: xem được nhật ký", page.locator("main tbody tr").count() > 0)
    ok("ql1: ô lọc 'Mọi người' ẩn (danh sách nhân viên chỉ Chủ gọi được)", page.get_by_label("Lọc theo người làm").count() == 0)
    clear_log(page)
    ctx.close()

    ctx, page, errors = new_page(browser, "loc", w=360, h=800, ai=True)
    go(page, "/audit-logs/")
    expect(page.locator("main tbody tr, main .lt-card").first).to_be_visible()
    ok("loc 360px: nhật ký không cuộn ngang trang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo15-audit-loc-360.png", full_page=True)
    ctx.close()

    for user in ("kho1", "giao1", "cs2"):
        ctx, page, errors = new_page(browser, user)
        clear_log(page)
        go(page, "/audit-logs/")
        ok(f"{user}: nhật ký → Không có quyền", no_perm(page))
        ok(f"{user}: KHÔNG có request audit-logs", not any("audit-logs" in e for e in log(page)), str(log(page)))
        ctx.close()


# ---------------------------------------------------------------- AI của tôi
def my_ai(browser):
    ctx, page, errors = new_page(browser, "loc", ai=True)
    go(page, "/ai/settings/")
    expect(page.get_by_text("AI của bạn đang bật")).to_be_visible()
    text = main_text(page)
    ok("loc: AI của tôi hiện trạng thái, bảng mức tự chủ, nhóm việc", "Thu mua" in text and "Bán hàng" in text and "Hỏi trước khi làm" in text)
    ok("loc: không icon rỗng, không cuộn ngang", missing_icons(page) == [] and no_hscroll(page), str(missing_icons(page)))
    clean_text("loc AI của tôi", text)
    page.screenshot(path=f"{SHOTS}/lo15-ai-settings-loc-1280.png", full_page=True)

    # Lưu khi chưa tích trách nhiệm → báo tại ô, KHÔNG gọi PUT
    radios = page.get_by_role("radiogroup", name="Mức tự chủ của việc Nhập lô mua tại cảng")
    radios.locator('input[value="OFF"]').check()
    clear_log(page)
    page.get_by_role("button", name="Lưu cài đặt").click()
    expect(page.get_by_text("Tích vào ô này để lưu cài đặt.")).to_be_visible()
    ok("loc: chưa tích trách nhiệm → báo tại ô, không gọi API lưu", not any(e.startswith("PUT") for e in log(page)), str(log(page)))
    # Việc không hoàn tác được bị khoá ở mức Hỏi trước
    locked = page.get_by_role("radiogroup", name="Mức tự chủ của việc Gửi phiếu nhập kho").locator("input:disabled")
    ok("loc: việc không hoàn tác được: mức Tự ghi bị khoá", locked.count() >= 1, str(locked.count()))
    # Ngưỡng sai → báo đỏ, không gọi API
    radios.locator('input[value="B"]').check()
    limit = page.get_by_label("Tối đa mỗi lần").first
    limit.fill("-5")
    page.get_by_label("Tôi chịu trách nhiệm về mọi việc AI làm thay tôi theo cài đặt này.").check()
    clear_log(page)
    page.get_by_role("button", name="Lưu cài đặt").click()
    expect(page.get_by_text("Có ô ngưỡng chưa đúng")).to_be_visible()
    ok("loc: ngưỡng âm → báo đỏ, không gọi API lưu", not any(e.startswith("PUT") for e in log(page)), str(log(page)))
    limit.fill("150")
    page.get_by_role("button", name="Lưu cài đặt").click()
    expect(page.locator(".toast-item").first).to_be_visible()
    ok("loc: lưu đúng → có thông báo 'Đã lưu cài đặt AI'", "Đã lưu cài đặt AI" in toast_text(page), toast_text(page))
    ok("loc: ô trách nhiệm tự bỏ tích sau khi lưu (mỗi lần lưu tích lại)", not page.get_by_label("Tôi chịu trách nhiệm về mọi việc AI làm thay tôi theo cài đặt này.").is_checked())
    # Tắt trợ lý: hỏi lại, Esc không đổi gì
    page.get_by_role("button", name="Tắt trợ lý").click()
    expect(page.get_by_role("dialog")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)
    ok("loc: Esc đóng hộp hỏi, trợ lý vẫn bật", page.get_by_text("AI của bạn đang bật").count() == 1)
    page.get_by_role("button", name="Tắt trợ lý").click()
    page.get_by_role("dialog").get_by_role("button", name="Tắt trợ lý").click()
    expect(page.get_by_text("AI của bạn đang tắt")).to_be_visible()
    ok("loc: xác nhận tắt → hiện 'AI của bạn đang tắt' và nút Bật lại", page.get_by_role("button", name="Bật lại").count() == 1)
    ok("loc: không lỗi console", errors == [], str(errors))
    ctx.close()

    # AI tắt cho cả vựa (mặc định mock)
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/ai/settings/")
    expect(page.get_by_text("Trợ lý đang tắt cho cả vựa")).to_be_visible()
    ok("loc (AI tắt cả vựa): báo rõ, cài đặt vẫn xem được", page.get_by_role("button", name="Lưu cài đặt").count() == 1)
    ctx.close()

    for user in ("ql1", "kho1", "cs2"):
        ctx, page, errors = new_page(browser, user, ai=True)
        go(page, "/ai/settings/")
        expect(page.get_by_text("AI của bạn đang bật")).to_be_visible()
        ok(f"{user}: mở được AI của tôi", True)
        ok(f"{user}: không cuộn ngang, không icon rỗng", no_hscroll(page) and missing_icons(page) == [], str(missing_icons(page)))
        ctx.close()
    ctx, page, errors = new_page(browser, "giao1", ai=True)
    go(page, "/ai/settings/")
    ok("giao1: AI của tôi → Không có quyền", no_perm(page))
    ctx.close()

    ctx, page, errors = new_page(browser, "loc", w=360, h=800, ai=True)
    go(page, "/ai/settings/")
    expect(page.get_by_text("AI của bạn đang bật")).to_be_visible()
    ok("loc 360px: AI của tôi không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo15-ai-settings-loc-360.png", full_page=True)
    ctx.close()


# ---------------------------------------------------------------- Chính sách AI
def policy(browser):
    ctx, page, errors = new_page(browser, "loc", ai=True)
    go(page, "/ai/policy/")
    expect(page.get_by_text("Chế độ cho cả vựa")).to_be_visible()
    text = main_text(page)
    ok("loc: Chính sách AI có chế độ, việc nhạy cảm, trần, tắt khẩn, danh sách nhân viên",
       all(t in text for t in ("Chế độ cho cả vựa", "Việc nhạy cảm", "Tắt trợ lý cho cả vựa", "AI của nhân viên")))
    ok("loc: không icon rỗng, không cuộn ngang", missing_icons(page) == [] and no_hscroll(page), str(missing_icons(page)))
    clean_text("loc chính sách AI", text)
    page.screenshot(path=f"{SHOTS}/lo15-ai-policy-loc-1280.png", full_page=True)

    # Lưu thiếu ô trách nhiệm → báo tại ô, không PUT
    page.get_by_role("radio", name=re.compile("Luôn hỏi trước")).check()
    clear_log(page)
    page.get_by_role("button", name="Lưu chính sách").click()
    expect(page.get_by_text("Tích vào ô này để lưu chính sách.")).to_be_visible()
    ok("loc: chưa tích trách nhiệm → báo tại ô, không gọi API lưu", not any(e.startswith("PUT") for e in log(page)), str(log(page)))
    page.get_by_label("Tôi chịu trách nhiệm về chính sách AI này cho cả vựa.").check()
    page.get_by_role("button", name="Lưu chính sách").click()
    expect(page.locator(".toast-item").first).to_be_visible()
    ok("loc: lưu đúng → thông báo 'Đã lưu chính sách AI'", "Đã lưu chính sách AI" in toast_text(page), toast_text(page))
    # Bật việc nhạy cảm cần xác nhận lại
    sw = page.get_by_role("switch").first
    before = sw.get_attribute("aria-checked")
    sw.click()
    ok("loc: công tắc việc nhạy cảm đổi trạng thái", sw.get_attribute("aria-checked") != before)
    # Xem cài đặt của nhân viên: chỉ đọc
    page.get_by_role("button", name="Xem cài đặt").first.click()
    expect(page.get_by_role("dialog")).to_be_visible()
    ok("loc: xem cài đặt nhân viên: hộp chỉ-xem, không có nút Lưu", page.get_by_role("dialog").get_by_role("button", name=re.compile("Lưu")).count() == 0)
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)
    # Tắt toàn bộ AI: hỏi lại, Esc không gọi API
    clear_log(page)
    page.get_by_role("button", name="Tắt toàn bộ AI ngay").click()
    expect(page.get_by_role("dialog")).to_be_visible()
    page.keyboard.press("Escape")
    ok("loc: Esc ở hộp tắt khẩn → không gọi API", not any(e.startswith("POST") or e.startswith("PUT") for e in log(page)), str(log(page)))
    page.get_by_role("button", name="Tắt toàn bộ AI ngay").click()
    page.get_by_role("dialog").get_by_role("button", name="Tắt toàn bộ AI ngay").click()
    expect(page.get_by_text(re.compile("AI đang tắt cho cả vựa"))).to_be_visible()
    ok("loc: xác nhận tắt khẩn → banner AI đang tắt, nút tắt bị khoá", page.get_by_role("button", name="Tắt toàn bộ AI ngay").is_disabled())
    ok("loc: không lỗi console", errors == [], str(errors))
    ctx.close()

    ctx, page, errors = new_page(browser, "loc", w=360, h=800, ai=True)
    go(page, "/ai/policy/")
    expect(page.get_by_text("Chế độ cho cả vựa")).to_be_visible()
    ok("loc 360px: Chính sách AI không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo15-ai-policy-loc-360.png", full_page=True)
    ctx.close()

    for user in ("ql1", "kho1", "giao1", "cs2"):
        ctx, page, errors = new_page(browser, user, ai=True)
        clear_log(page)
        go(page, "/ai/policy/")
        ok(f"{user}: Chính sách AI → Không có quyền, không gọi API chính sách", no_perm(page) and not any("ai/policy" in e for e in log(page)), str(log(page)))
        ctx.close()


# ---------------------------------------------------------------- Báo cáo AI
def report(browser):
    ctx, page, errors = new_page(browser, "loc", ai=True)
    go(page, "/ai/report/")
    expect(page.get_by_text("Nhật ký việc AI trong ngày")).to_be_visible()
    text = main_text(page)
    ok("loc: báo cáo có dải số, Theo nhân viên, Nhật ký việc AI", all(t in text for t in ("Tổng việc AI", "Theo nhân viên", "Nhật ký việc AI trong ngày", "Cộng")))
    nums = {}
    cells = page.locator("[role=group][aria-label='Tổng việc AI'] > div")
    for i in range(cells.count()):
        lab, val = cells.nth(i).inner_text().split("\n")[:2]
        nums[lab.strip()] = int(val.strip())
    parts = sum(v for k, v in nums.items() if k != "Tổng việc AI")
    ok("loc: Tổng việc AI = cộng sáu cột (board W4d)", nums.get("Tổng việc AI") == parts and parts > 0, str(nums))
    ok("loc: không SĐT, không icon rỗng, không cuộn ngang", not PHONE_RE.search(text) and missing_icons(page) == [] and no_hscroll(page), str(missing_icons(page)))
    clean_text("loc báo cáo AI", text)
    page.screenshot(path=f"{SHOTS}/lo15-ai-report-loc-1280.png", full_page=True)
    ok("loc: hôm nay → nút Ngày sau bị khoá", page.get_by_role("button", name="Ngày sau").is_disabled())

    # Lùi 3 ngày → rỗng (mock): báo rõ, không bảng trống trơn
    for _ in range(3):
        page.get_by_role("button", name="Ngày trước").click()
        settle(page)
    expect(page.get_by_text("Chưa có việc AI nào trong ngày")).to_be_visible()
    ok("loc: ngày không có việc AI → báo rỗng rõ ràng", page.get_by_text("Không có việc AI nào trong ngày này").count() == 1)
    ok("loc: lùi ngày rồi nút Ngày sau mở lại", page.get_by_role("button", name="Ngày sau").is_enabled())
    page.screenshot(path=f"{SHOTS}/lo15-ai-report-empty-1280.png", full_page=True)
    # Nhập ngày tương lai bằng tay → kéo về hôm nay (không có báo cáo của tương lai)
    page.get_by_label("Ngày báo cáo").fill("2099-01-01")
    settle(page)
    ok("loc: gõ ngày tương lai → kéo về hôm nay", page.get_by_label("Ngày báo cáo").input_value() != "2099-01-01", page.get_by_label("Ngày báo cáo").input_value())
    # Lỗi 500
    page.evaluate("() => window.__caveMock.aiReportFail(true)")
    # các ngày đã xem được nhớ lại (không gọi lại), nên lùi tới ngày CHƯA xem mới ra lỗi
    for _ in range(5):
        page.get_by_role("button", name="Ngày trước").click()
    expect(page.get_by_role("button", name="Thử lại").first).to_be_visible()
    ok("loc: báo cáo lỗi 500 → báo lỗi + Thử lại", True)
    page.evaluate("() => window.__caveMock.aiReportFail(false)")
    page.get_by_role("button", name="Thử lại").first.click()
    settle(page)
    expect(page.get_by_role("button", name="Thử lại")).to_have_count(0)
    ok("loc: Thử lại sau khi phục hồi → hết lỗi", True)
    ok("loc: không lỗi console", errors == [], str(errors))
    ctx.close()

    ctx, page, errors = new_page(browser, "loc", w=360, h=800, ai=True)
    go(page, "/ai/report/")
    expect(page.get_by_text("Nhật ký việc AI trong ngày")).to_be_visible()
    ok("loc 360px: Báo cáo AI không cuộn ngang trang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo15-ai-report-loc-360.png", full_page=True)
    ctx.close()

    for user in ("ql1", "kho1", "giao1", "cs2"):
        ctx, page, errors = new_page(browser, user, ai=True)
        clear_log(page)
        go(page, "/ai/report/")
        ok(f"{user}: Báo cáo AI → Không có quyền, không gọi API báo cáo", no_perm(page) and not any("daily-report" in e or "ai/report" in e for e in log(page)), str(log(page)))
        ctx.close()


# ---------------------------------------------------------------- Tài khoản
def account(browser, user, full=False):
    ctx, page, errors = new_page(browser, user, ai=True)
    page.evaluate("() => window.__caveMock && 0")
    go(page, "/account/")
    expect(page.locator(".who-card")).to_be_visible()
    text = main_text(page)
    ok(f"{user}: Tài khoản có Tên đăng nhập, Số điện thoại, Vai trò", all(t in text for t in ("Tên đăng nhập", "Số điện thoại", "Vai trò")) and page.locator(".who-card .group-tag").count() >= 1)
    ok(f"{user}: có 'Việc bạn được làm', 'Mục bạn thấy trên menu', 'Bảo mật và đăng nhập'", all(t in text for t in ("Việc bạn được làm", "Mục bạn thấy trên menu", "Bảo mật và đăng nhập")))
    ok(f"{user}: phiên đăng nhập ghi giờ dạng dd/mm/yyyy hh:mm và 'Máy này'", bool(re.search(r"Đăng nhập từ \d{2}/\d{2}/\d{4} \d{2}:\d{2}", text)) and "Máy này" in text, text[text.find("Phiên"):][:80])
    ok(f"{user}: có hàng Đổi mật khẩu và Đăng xuất", page.get_by_role("button", name="Đổi mật khẩu").count() == 1 and page.get_by_role("button", name="Đăng xuất").count() >= 1)
    ai_link = page.get_by_role("link", name="Mở cài đặt AI")
    ok(f"{user}: link 'Mở cài đặt AI' khớp quyền (giao1 không có)", ai_link.count() == (0 if user == "giao1" else 1))
    ok(f"{user}: không icon rỗng, không cuộn ngang", missing_icons(page) == [] and no_hscroll(page), str(missing_icons(page)))
    clean_text(f"{user} tài khoản", text)
    # Lưu trữ + URL: chỉ có mốc giờ, không tên/SĐT
    dump = storage_dump(page)
    me_phone = page.evaluate("() => (document.querySelector('.who-card a[href^=\"tel:\"]')||{}).textContent || ''").strip()
    ok(f"{user}: localStorage/sessionStorage chỉ có mốc giờ đăng nhập (ngoài kho giả), không SĐT", "cave_erp_signed_in_at" in dump and not PHONE_RE.search(dump) and (not me_phone or me_phone not in dump), dump[:160])
    ok(f"{user}: URL không có dữ liệu cá nhân", not PHONE_RE.search(page.url))
    page.screenshot(path=f"{SHOTS}/lo15-account-{user}-1280.png", full_page=True)

    # Tải lại quyền → toast
    page.get_by_role("button", name="Tải lại quyền").click()
    expect(page.locator(".toast-item").first).to_be_visible()
    ok(f"{user}: Tải lại quyền → thông báo 'Đã tải lại quyền'", "Đã tải lại quyền" in toast_text(page), toast_text(page))

    if full:
        # Đổi mật khẩu: nhập lại không khớp → báo tại ô, KHÔNG gọi API
        page.get_by_role("button", name="Đổi mật khẩu").click()
        dlg = page.get_by_role("dialog", name="Đổi mật khẩu")
        expect(dlg).to_be_visible()
        ok(f"{user}: mở tấm đổi mật khẩu, focus vào ô Mật khẩu hiện tại", page.evaluate("() => document.activeElement && document.activeElement.id") == "cp-old")
        dlg.locator("#cp-old").fill("demo1234")
        dlg.locator("#cp-new").fill("Cavang2026x")
        dlg.locator("#cp-again").fill("Cavang2026y")
        clear_log(page)
        dlg.get_by_role("button", name="Đổi mật khẩu").click()
        expect(dlg.get_by_text("Hai mật khẩu không khớp")).to_be_visible()
        ok(f"{user}: nhập lại không khớp → báo tại ô, không gọi API", not any("change-password" in e for e in log(page)), str(log(page)))
        # Sai mật khẩu hiện tại → lỗi BE nguyên văn
        dlg.locator("#cp-again").fill("Cavang2026x")
        dlg.locator("#cp-old").fill("sai-mat-khau-1")
        dlg.get_by_role("button", name="Đổi mật khẩu").click()
        expect(dlg.get_by_role("alert").filter(has_text="Mật khẩu hiện tại không đúng")).to_be_visible()
        ok(f"{user}: sai mật khẩu hiện tại → lỗi nguyên văn, tấm vẫn mở", dlg.count() == 1)
        # Mật khẩu yếu → lỗi BE
        dlg.locator("#cp-old").fill("demo1234")
        dlg.locator("#cp-new").fill("12345678")
        dlg.locator("#cp-again").fill("12345678")
        dlg.get_by_role("button", name="Đổi mật khẩu").click()
        expect(dlg.get_by_role("alert").first).to_be_visible()
        ok(f"{user}: mật khẩu toàn số → bị từ chối, tấm vẫn mở", dlg.count() == 1)
        # Huỷ
        dlg.get_by_role("button", name="Huỷ").click()
        expect(page.get_by_role("dialog")).to_have_count(0)
        ok(f"{user}: Huỷ đóng tấm, không đổi mật khẩu", True)
        # Thành công
        page.get_by_role("button", name="Đổi mật khẩu").click()
        dlg = page.get_by_role("dialog", name="Đổi mật khẩu")
        dlg.locator("#cp-old").fill("demo1234")
        dlg.locator("#cp-new").fill("Cavang2026x")
        dlg.locator("#cp-again").fill("Cavang2026x")
        dlg.get_by_role("button", name="Đổi mật khẩu").click()
        expect(page.get_by_role("dialog")).to_have_count(0)
        expect(page.locator(".toast-item").filter(has_text="Đã đổi mật khẩu").first).to_be_visible()
        ok(f"{user}: đổi mật khẩu thành công → tấm đóng + thông báo", True)
        ok(f"{user}: mật khẩu không nằm trong storage/URL", "Cavang2026x" not in storage_dump(page) and "Cavang2026x" not in page.url)

        # Đăng xuất: xoá mốc giờ, về trang đăng nhập
        page.get_by_role("button", name="Đăng xuất").last.click()
        page.wait_for_url(re.compile(r"/login/"))
        has_stamp = page.evaluate("() => localStorage.getItem('cave_erp_signed_in_at')")
        ok(f"{user}: đăng xuất → về /login/ và xoá mốc giờ đăng nhập", has_stamp is None, str(has_stamp))
    ok(f"{user}: không lỗi console", errors == [], str(errors))
    ctx.close()


def account_mobile(browser):
    ctx, page, errors = new_page(browser, "kho1", w=360, h=800, ai=True)
    go(page, "/account/")
    expect(page.locator(".who-card")).to_be_visible()
    ok("kho1 360px: Tài khoản không cuộn ngang trang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo15-account-kho1-360.png", full_page=True)
    page.get_by_role("button", name="Đổi mật khẩu").click()
    expect(page.get_by_role("dialog")).to_be_visible()
    ok("kho1 360px: tấm đổi mật khẩu không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo15-account-kho1-360-sheet.png")
    ctx.close()


def login_screens(browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    ok("đăng nhập: gợi ý ô tài khoản 'vd: tam.kho'", page.get_by_label("Tài khoản").get_attribute("placeholder") == "vd: tam.kho")
    # bỏ trống → báo tại ô, không gọi API
    page.get_by_role("button", name="Đăng nhập").click()
    expect(page.get_by_role("alert").first).to_be_visible()
    ok("đăng nhập: bỏ trống → báo tại ô tài khoản", page.evaluate("() => document.activeElement.id") == "u")
    page.get_by_label("Tài khoản").fill("loc")
    page.get_by_label("Mật khẩu").fill("sai-mat-khau")
    page.get_by_role("button", name="Đăng nhập").click()
    expect(page.locator(".alert-box.err")).to_be_visible()
    ok("đăng nhập: sai mật khẩu → báo lỗi, ở lại /login/", "/login" in page.url)
    ok("đăng nhập 360px: không cuộn ngang", no_hscroll(page))
    ok("đăng nhập: chưa đăng nhập thì chưa có mốc giờ", page.evaluate("() => localStorage.getItem('cave_erp_signed_in_at')") is None)
    page.screenshot(path=f"{SHOTS}/lo15-login-360.png")
    ctx.close()

    # admin (chưa phân quyền) → màn "Tài khoản chưa được phân quyền"
    ctx, page, errors = new_page(browser, "admin", w=360, h=780, wait_nav=False)
    page.wait_for_url(re.compile(r"/no-role/"))
    expect(page.get_by_role("heading", name="Tài khoản chưa được phân quyền")).to_be_visible()
    ok("admin: màn chưa phân quyền có tên tài khoản + 'Nhờ Chủ vựa cấp quyền'", "Nhờ Chủ vựa cấp quyền" in page.locator("main").inner_text() and "admin" in page.locator("main").inner_text())
    ok("admin 360px: không cuộn ngang, không icon rỗng", no_hscroll(page) and missing_icons(page) == [], str(missing_icons(page)))
    page.screenshot(path=f"{SHOTS}/lo15-no-role-360.png")
    ctx.close()

    # kho5 (còn mật khẩu tạm) → Đặt mật khẩu mới
    ctx, page, errors = new_page(browser, "kho5", w=360, h=780, wait_nav=False)
    page.wait_for_url(re.compile(r"/set-password/"))
    expect(page.get_by_role("heading", name="Đặt mật khẩu mới")).to_be_visible()
    ok("kho5: màn đặt mật khẩu mới có tên + nút Đăng xuất, KHÔNG có nút Huỷ", page.get_by_role("button", name="Huỷ").count() == 0 and page.get_by_role("button", name="Đăng xuất").count() == 1)
    ok("kho5 360px: không cuộn ngang, không icon rỗng", no_hscroll(page) and missing_icons(page) == [], str(missing_icons(page)))
    page.screenshot(path=f"{SHOTS}/lo15-set-password-360.png")
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    overview_owner(browser)
    overview_no_cost(browser, "ql1")
    overview_no_cost(browser, "kho1")
    overview_forbidden(browser, "giao1")
    overview_forbidden(browser, "cs2")
    audit(browser)
    my_ai(browser)
    policy(browser)
    report(browser)
    account(browser, "loc", full=True)
    for u in ("ql1", "kho1", "giao1", "cs2"):
        account(browser, u, full=(u == "cs2"))
    account_mobile(browser)
    login_screens(browser)
    browser.close()

bad = [r for r in results if not r[1]]
print(f"\n{len(results) - len(bad)}/{len(results)} PASS")
for name, _, extra in bad:
    print("FAIL:", name, extra)
raise SystemExit(1 if bad else 0)
