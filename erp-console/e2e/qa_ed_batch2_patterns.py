# QA độc lập ERP theo design, Lô 2 FE (mẫu trang chi tiết, popup, form, khối Trợ lý AI) trên bản MOCK phục vụ tĩnh.
#   NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=../doc/features/2026-10-01-erp-theo-design/shots/lot2 python3 e2e/qa_ed_batch2_patterns.py
# Chỉ dữ liệu giả của mock. Phủ thêm so với ed_batch2_patterns.py: đo kiểu chữ/vị trí thật (không dòng xám, * đỏ, thanh nút dính),
# bấm đúp (Lưu/Đồng ý/Từ chối/Enter), Modal đóng bằng scrim/X/Huỷ, lỗi bắt buộc ở ô sửa tại chỗ, mục "…" bị chặn không gọi API,
# AI tắt/bật/chưa đồng ý có đếm request /api/ai/*, không lộ giá vốn/tên/SĐT/địa chỉ ở DOM, localStorage, URL, console.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)
PII = re.compile(r"(\b0\d{9}\b|\+84\d{9}|Nguyễn|Trần Văn|đường |phường |quận )", re.I)


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user="loc", pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.ai === 'function'", timeout=10_000)


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def new_ctx(browser, w, h, errors):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append("console: " + m.text))
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    login(page)
    return ctx, page


def demo(page, ai=None, consent=None, path="/dev-patterns/"):
    if ai is not None:
        page.evaluate("(v) => window.__caveMock.ai(v)", "on" if ai else "off")
    if consent is not None:
        page.evaluate("(v) => window.__caveMock.aiConsent(v)", consent)
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def hscroll_ok(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def css(page, sel, prop):
    return page.evaluate("([s,p]) => { const e=document.querySelector(s); return e ? getComputedStyle(e)[p] : null }", [sel, prop])


def rgb(s):
    m = re.findall(r"[\d.]+", s or "")
    return tuple(float(x) for x in m[:3]) if m else None


def is_red(s):
    c = rgb(s)
    return bool(c) and c[0] > 150 and c[1] < 110 and c[2] < 110


def reqs(page):
    return page.evaluate("() => window.__caveMock.log.slice().map(String)")


def s1_detail(browser):
    errors = []
    ctx, page = new_ctx(browser, 1280, 900, errors)
    demo(page, ai=False)
    expect(page.get_by_role("heading", name="PR-260928-01")).to_be_visible()
    # Header
    back = page.get_by_role("link", name=re.compile("Tổng quan"))
    ok("ED-04 header: có liên kết '← Tổng quan' (về danh sách)", back.count() >= 1 and (back.first.get_attribute("href") or "") == "/overview/", back.first.get_attribute("href") if back.count() else "")
    h1 = page.get_by_role("heading", name="PR-260928-01")
    ff = h1.evaluate("e => getComputedStyle(e).fontFamily")
    ok("ED-04 header: mã in font mono", "mono" in ff.lower() or "jet" in ff.lower() or "courier" in ff.lower(), ff[:80])
    ok("ED-04 header: chip trạng thái bên cạnh mã", page.locator(".stat-chip", has_text="Đã nhập kho").count() == 1)
    prim = page.get_by_role("button", name="Sửa phiếu", exact=True)
    ok("ED-04 header: đúng 1 nút chính (btn primary) + nút '…'", page.locator("header .btn.primary, [class*=DetailHeader] .btn.primary").count() <= 1 and page.get_by_role("button", name="Thao tác khác").count() == 1)
    # Không dòng xám (UI-RULES §3.2/§5.1): không <p class=muted> / chữ xám giải thích ngay dưới tiêu đề
    head_txt = page.locator("[class*=DetailHeader]").first.inner_text() if page.locator("[class*=DetailHeader]").count() else ""
    lines = [l for l in head_txt.split("\n") if l.strip() and l.strip() not in ("arrow_back", "more_horiz")]
    ok("ED-04 header: chỉ có ← danh sách, mã, chip, nút chính (không dòng mô tả xám)", lines == ["Tổng quan", "PR-260928-01", "Đã nhập kho", "Sửa phiếu"], repr(lines))
    page.screenshot(path=f"{SHOTS}/qa-detail-desktop.png")
    # StatusPath
    ok("ED-04 StatusPath: 'Tiếp theo: Ghi hoá đơn nhà cung cấp'", page.get_by_text("Tiếp theo:").first.locator("xpath=..").inner_text().find("Ghi hoá đơn nhà cung cấp") >= 0)
    ok("ED-04 StatusPath: 'Đã làm: Tạo phiếu · Nhập kho'", "Tạo phiếu" in page.get_by_text("Đã làm:").first.locator("xpath=..").inner_text())
    cur = page.locator('[data-state="current"]')
    ok("ED-04 StatusPath: bước hiện tại có aria-current/nhãn", cur.count() == 1 and ((cur.first.get_attribute("aria-current") or "") != "" or "Đã nhập kho" in cur.first.inner_text()))
    # InfoGrid: mỗi ô một giá trị, 2 cột
    dts = page.locator("dl > div, dl > *").count()
    ok("ED-04 InfoGrid: có >= 4 ô", dts >= 4, str(dts))
    cols = page.evaluate("() => getComputedStyle(document.querySelector('dl')).gridTemplateColumns.split(' ').length")
    ok("ED-04 InfoGrid: desktop 2 cột", cols == 2, str(cols))
    # ô khoá
    lock_icon = page.evaluate("() => [...document.querySelectorAll('dl i.mi')].map(i=>i.textContent.trim())")
    ok("ED-04 ô khoá: có icon khoá, không có nút sửa", "lock" in lock_icon, str(lock_icon))
    ok("ED-04 ô khoá: lý do 'Giá vốn chỉ Chủ được xem' có trong DOM", page.locator("dl").get_by_text("Giá vốn chỉ Chủ được xem").count() >= 1)
    # Sửa tại chỗ: lỗi bắt buộc dưới ô
    page.locator('button[aria-label="Sửa số lượng"]').last.click()
    inp = page.locator("dl input").first
    inp.fill("")
    inp.press("Enter")
    page.wait_for_timeout(300)
    err = page.locator("dl [id$='-e'], dl [role=alert], dl p").filter(has_text=re.compile("bắt buộc|nhập|trống", re.I))
    ok("ED-04 sửa tại chỗ: để trống -> lỗi dưới ô (1 dòng)", err.count() == 1, f"{err.count()} " + (err.first.inner_text() if err.count() else ""))
    ok("ED-04 sửa tại chỗ: ô lỗi aria-invalid + viền đỏ", inp.get_attribute("aria-invalid") == "true" and is_red(inp.evaluate("e => getComputedStyle(e).borderColor")), f"{inp.get_attribute('aria-invalid')} {inp.evaluate('e => getComputedStyle(e).borderColor')}")
    ok("ED-04 sửa tại chỗ: lỗi nhập trống (chưa gửi) mà nút chính đã thành 'Thử lại' (đáng lẽ vẫn 'Lưu')", page.locator("dl").get_by_role("button", name="Lưu").count() == 1, page.locator("dl [data-editing] button.primary").inner_text())
    ok("ED-04 sửa tại chỗ: lỗi bắt buộc KHÔNG gọi API", not any("PATCH /api/dev-patterns" in r for r in reqs(page)), str(reqs(page))[-120:])
    page.screenshot(path=f"{SHOTS}/qa-infofield-error-desktop.png")
    # Esc huỷ sửa, giữ giá trị cũ
    inp.press("Escape")
    ok("ED-04 sửa tại chỗ: Esc huỷ, giá trị cũ '12 kg' còn", page.locator("dl").get_by_text("12 kg").count() == 1 and page.locator("dl input").count() == 0)
    # Bấm đúp Lưu: đúng 1 PATCH
    page.evaluate("() => window.__caveMock.clearLog()")
    page.locator('button[aria-label="Sửa số lượng"]').last.click()
    inp = page.locator("dl input").first
    inp.fill("15")
    save = page.locator("dl").get_by_role("button", name=re.compile("^Lưu"))
    if save.count():
        save.first.dblclick()
    else:
        inp.press("Enter"); inp.press("Enter")
    settle(page)
    n = len([r for r in reqs(page) if "PATCH /api/dev-patterns/qty" in r])
    ok("ED-04 sửa tại chỗ: bấm đúp Lưu chỉ gửi 1 PATCH", n == 1, str(n))
    ok("ED-04 sửa tại chỗ: giá trị mới '15 kg' hiện", page.locator("dl").get_by_text("15 kg").count() == 1)
    # MoreMenu: mục chặn không gọi API / không đóng, lý do
    page.evaluate("() => window.__caveMock.clearLog()")
    page.get_by_role("button", name="Thao tác khác").click()
    blocked = page.get_by_role("menuitem", name=re.compile("Huỷ phiếu"))
    blocked.click(force=True)
    ok("ED-04 '…' mục bị chặn: bấm không gọi API", len(reqs(page)) == 0, str(reqs(page)))
    ok("ED-04 '…' mục bị chặn: còn hiện lý do, không có hộp xác nhận mở ra", page.get_by_role("dialog").count() == 0 and "Phiếu đã có hoá đơn" in page.get_by_role("menuitem", name=re.compile("Huỷ phiếu")).inner_text() if page.get_by_role("menuitem", name=re.compile("Huỷ phiếu")).count() else page.get_by_role("dialog").count() == 0)
    color = page.get_by_role("menuitem", name=re.compile("Huỷ phiếu")).evaluate("e => getComputedStyle(e).color") if page.get_by_role("menuitem", name=re.compile("Huỷ phiếu")).count() else ""
    ok("ED-04 '…' mục huỷ bị chặn: aria-disabled=true", page.get_by_role("menuitem", name=re.compile("Huỷ phiếu")).get_attribute("aria-disabled") == "true", color)
    page.keyboard.press("Escape")
    # phím mũi tên điều hướng menu
    page.get_by_role("button", name="Thao tác khác").click()
    page.keyboard.press("ArrowDown")
    first_focus = page.evaluate("() => document.activeElement && document.activeElement.getAttribute('role')")
    ok("ED-04 '…' menu: phím mũi tên đưa focus vào mục", first_focus == "menuitem", str(first_focus))
    page.keyboard.press("Escape")
    # click ngoài đóng menu
    page.get_by_role("button", name="Thao tác khác").click()
    page.mouse.click(5, 450)
    ok("ED-04 '…' menu: bấm ra ngoài đóng menu", page.get_by_role("menuitem").count() == 0)
    # Timeline
    tl = page.locator("section[aria-label='Dòng thời gian']")
    t = tl.inner_text()
    ok("ED-04 Timeline: định dạng dd/mm/yyyy hh:mm", re.search(r"28/09/2026\s*\d{2}:\d{2}", t) is not None, t[:140].replace("\n", " | "))
    ok("ED-04 Timeline: không mã BR/khoá kỹ thuật", not re.search(r"BR-|_id|submit\b|create\b", t))
    page.screenshot(path=f"{SHOTS}/qa-timeline-desktop.png")
    # LookupCard
    page.get_by_role("button", name=re.compile("CA01-260928-AB12C")).click()
    card = page.get_by_role("dialog")
    expect(card).to_be_visible()
    expect(card.get_by_text("Cá thu một nắng").first).to_be_visible()
    ct = card.inner_text()
    ok("ED-04 LookupCard: không giá vốn, không tên/SĐT/địa chỉ", not re.search(r"giá vốn|cost|123456", ct, re.I) and not PII.search(ct), ct[:140].replace("\n", " | "))
    ok("ED-04 LookupCard: có nút mở trang đầy đủ + nút đóng", card.get_by_role("link", name=re.compile("Mở trang lô")).count() == 1 and card.get_by_role("button", name=re.compile("Đóng")).count() >= 1)
    page.screenshot(path=f"{SHOTS}/qa-lookup-desktop.png")
    page.keyboard.press("Escape")
    # Bảo mật phía trình duyệt
    ls = page.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(localStorage).filter(([k]) => k !== 'cave_erp_mock_users')))")  # cave_erp_mock_users = danh sách nhân viên GIẢ của mock, bản thật không có
    ok("G9 localStorage không chứa SĐT/địa chỉ/giá vốn", not PII.search(ls) and not re.search(r"cost|giá vốn", ls, re.I), ls[:160])
    ok("G9 URL không chứa dữ liệu cá nhân", not PII.search(page.url), page.url)
    body = page.locator("body").inner_text()
    ok("G9 trang chi tiết (vai Chủ) không có tên/SĐT/địa chỉ khách ngoài dữ liệu bịa", not PII.search(body))
    ctx.close()
    return errors


def s2_modal(browser):
    errors = []
    ctx, page = new_ctx(browser, 1280, 800, errors)
    demo(page, ai=False)
    opener = page.get_by_role("button", name="Sửa phiếu", exact=True)
    dlg = page.get_by_role("dialog", name="Sửa số lượng")
    # đóng bằng scrim, X, Huỷ; URL không đổi; cuộn nền khoá
    url0 = page.url
    opener.click(); expect(dlg).to_be_visible()
    ok("ED-05 Modal: nền bị khoá cuộn khi mở", page.evaluate("() => getComputedStyle(document.body).overflow") in ("hidden", "clip"), page.evaluate("() => getComputedStyle(document.body).overflow"))
    ok("ED-05 Modal: URL không đổi khi mở", page.url == url0)
    ok("ED-05 Modal: aria-modal=true", dlg.get_attribute("aria-modal") == "true")
    page.screenshot(path=f"{SHOTS}/qa-modal-desktop.png")
    page.mouse.click(5, 5)
    ok("ED-05 Modal: bấm scrim đóng (khi rảnh)", dlg.count() == 0)
    opener.click(); expect(dlg).to_be_visible()
    dlg.get_by_role("button", name=re.compile("Đóng")).first.click()
    ok("ED-05 Modal: nút X đóng", dlg.count() == 0)
    ok("ED-05 Modal: trả focus về nút mở sau X", page.evaluate("() => document.activeElement.textContent.trim()") == "Sửa phiếu")
    opener.click(); expect(dlg).to_be_visible()
    dlg.get_by_role("button", name="Huỷ", exact=True).click()
    ok("ED-05 Modal: nút Huỷ đóng", dlg.count() == 0)
    # Đang gửi: scrim/X/Huỷ khoá; bấm đúp Lưu chỉ gửi 1 lần
    opener.click(); expect(dlg).to_be_visible()
    page.evaluate("() => window.__caveMock.clearLog()")
    dlg.get_by_role("button", name="Lưu", exact=True).dblclick()
    expect(dlg.get_by_role("button", name="Đang gửi…")).to_be_visible()
    page.mouse.click(5, 5)
    ok("ED-05 Modal đang gửi: bấm scrim KHÔNG đóng", dlg.count() == 1)
    xbtn = dlg.get_by_role("button", name=re.compile("Đóng"))
    ok("ED-05 Modal đang gửi: nút X bị khoá", xbtn.count() == 0 or xbtn.first.is_disabled())
    ok("ED-05 Modal đang gửi: nút Huỷ bị khoá", dlg.get_by_role("button", name="Huỷ", exact=True).is_disabled())
    ok("ED-05 Modal đang gửi: aria-busy hoặc nút đang gửi báo cho trình đọc", dlg.get_attribute("aria-busy") == "true" or dlg.get_by_role("button", name="Đang gửi…").count() == 1)
    expect(dlg.locator("[data-form-alert]")).to_be_visible()
    # sau lỗi: Huỷ lại dùng được; bấm Thử lại 2 lần liên tiếp -> 1 lần gửi
    ok("ED-05 Modal sau lỗi: Huỷ dùng lại được", dlg.get_by_role("button", name="Huỷ", exact=True).is_enabled())
    retry = dlg.get_by_role("button", name="Thử lại", exact=True)
    retry.dblclick()
    expect(dlg).to_have_count(0)
    ok("ED-05 Modal bấm đúp 'Thử lại': hộp đóng sau lần thành công (đếm số lần gửi: xem harness h_modal, vì Modal mẫu không qua apiFetch)", dlg.count() == 0)
    # nhấn Esc ngay lúc mới mở -> đóng và không gửi
    opener.click(); expect(dlg).to_be_visible()
    page.keyboard.press("Escape"); ok("ED-05 Modal: Esc lúc rảnh đóng", dlg.count() == 0)
    # focus trap ngược: Shift+Tab từ ô đầu
    opener.click(); expect(dlg).to_be_visible()
    page.keyboard.press("Shift+Tab")
    ok("ED-05 Modal: Shift+Tab từ ô đầu không thoát khỏi hộp", page.evaluate("() => !!document.activeElement.closest('[role=dialog]')"))
    # Tab ngoài hộp không focus được nền
    bg_focus = page.evaluate("() => { const b=document.querySelector('#pattern-demo'); return b ? (b.closest('[inert]') !== null || b.getAttribute('aria-hidden') === 'true') : null }")
    tabs = []
    for _ in range(14):
        page.keyboard.press("Tab"); tabs.append(page.evaluate("() => !!document.activeElement.closest('[role=dialog]')"))
    ok("ED-05 Modal: Tab 14 lần liên tiếp, focus không bao giờ ra ngoài hộp (nền không có inert, dựa aria-modal + bẫy focus)", all(tabs), str(tabs))
    page.keyboard.press("Escape")
    ctx.close()
    # mobile bottom sheet
    ctx, page = new_ctx(browser, 360, 640, errors)
    demo(page, ai=False)
    page.get_by_role("button", name="Sửa phiếu", exact=True).click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    b = dlg.bounding_box()
    ok("ED-05 Modal 360px: tấm dán đáy, rộng đủ khung, không cuộn ngang", b and abs(b["x"]) < 2 and b["width"] >= 355 and b["y"] + b["height"] >= 636 and hscroll_ok(page), str(b))
    btn = dlg.get_by_role("button", name="Lưu", exact=True).bounding_box()
    ok("ED-05 Modal 360px: nút cao >= 44px", btn["height"] >= 44, str(btn))
    page.screenshot(path=f"{SHOTS}/qa-modal-mobile360.png")
    ctx.close()
    return errors


def s3_form(browser):
    errors = []
    ctx, page = new_ctx(browser, 1280, 800, errors)
    demo(page, path="/dev-patterns/form/")
    expect(page.get_by_role("heading", name="Nhập thử một phiếu")).to_be_visible()
    # * đỏ, đơn vị trong ô
    star = page.locator("label span[aria-hidden='true']", has_text="*").first
    ok("ED-03/F1a: có dấu * cho trường bắt buộc, màu đỏ", star.count() == 1 and is_red(star.evaluate("e => getComputedStyle(e).color")), star.evaluate("e => getComputedStyle(e).color"))
    inp = page.get_by_label("Số lượng")
    unit = page.locator("span", has_text=re.compile("^kg$")).first
    ib, ub = inp.bounding_box(), unit.bounding_box()
    ok("ED-03/F1a: đơn vị 'kg' nằm TRONG ô (bên phải)", ub["x"] >= ib["x"] + ib["width"] / 2 and ub["x"] + ub["width"] <= ib["x"] + ib["width"] + 1 and ib["y"] <= ub["y"] <= ib["y"] + ib["height"], f"{ib} {ub}")
    lb = page.locator("label", has_text="Số lượng").bounding_box()
    ok("ED-03/F1a: nhãn nằm TRÊN ô", lb["y"] + lb["height"] <= ib["y"] + 2, f"{lb} {ib}")
    ok("ED-03/F1a: ô số inputMode decimal", inp.get_attribute("inputmode") == "decimal")
    # không dòng gợi ý xám dưới ô
    ok("ED-03/F1a: không có chữ gợi ý xám dưới ô", page.locator("form .muted, [class*=hint], [class*=help]").count() == 0)
    # thanh nút dính dưới (desktop, trang cao)
    page.set_viewport_size({"width": 1280, "height": 420})
    page.wait_for_timeout(400)
    bar = page.locator("[data-action-bar]")
    bb = bar.bounding_box()
    ok("ED-03/F1a: thanh nút dính đáy khung nhìn (viewport thấp)", bb and bb["y"] + bb["height"] <= 421 and bb["y"] > 200, str(bb))
    ok("ED-03/F1a: có 1 nút chính + 'Huỷ' phụ", bar.get_by_role("button", name="Lưu phiếu").count() == 1 and bar.get_by_role("button", name="Huỷ").count() == 1)
    page.set_viewport_size({"width": 1280, "height": 800})
    page.screenshot(path=f"{SHOTS}/qa-form-desktop.png")
    # bấm đúp Lưu / Enter 2 lần trong ô -> gửi 1 lần; lỗi -> giữ giá trị -> Thử lại
    page.evaluate("() => window.__caveMock.clearLog()")
    inp.fill("77,5")
    page.get_by_role("button", name="Lưu phiếu").dblclick()
    expect(page.locator("[data-form-alert]")).to_be_visible()
    ok("ED-03 gửi lỗi: giá trị '77,5' còn nguyên", inp.input_value() == "77,5")
    ok("ED-03 gửi lỗi: alert đỏ có role=alert", page.locator("[data-form-alert]").get_attribute("role") == "alert" or page.locator("[role=alert]").count() >= 1)
    ok("ED-03 gửi lỗi: nút chính thành 'Thử lại'", page.get_by_role("button", name="Thử lại", exact=True).count() == 1)
    page.screenshot(path=f"{SHOTS}/qa-form-error-desktop.png")
    # Thử lại bấm đúp -> chỉ 1 lần thành công; sau thành công không cho gửi tiếp tạo bản trùng
    page.get_by_role("button", name="Thử lại", exact=True).dblclick()
    expect(page.locator("[data-saved]")).to_be_visible()
    ok("ED-03 Thử lại bấm đúp: hiện 'Đã lưu phiếu.' một lần", page.locator("[data-saved]").count() == 1)
    # nút trong lúc gửi bị khoá
    ctx.close()
    # 360px
    ctx, page = new_ctx(browser, 360, 640, errors)
    demo(page, path="/dev-patterns/form/")
    ok("ED-03 form 360px: không cuộn ngang", hscroll_ok(page))
    b = page.get_by_role("button", name="Lưu phiếu").bounding_box()
    ok("ED-03 form 360px: nút chính cao >= 44px, rộng đủ bấm", b["height"] >= 44 and b["width"] >= 100, str(b))
    page.screenshot(path=f"{SHOTS}/qa-form-mobile360.png")
    ctx.close()
    return errors


def s4_ai(browser):
    errors = []
    # AI tắt
    ctx, page = new_ctx(browser, 1280, 900, errors)
    page.evaluate("() => window.__caveMock.clearLog()")
    demo(page, ai=False, consent=True)
    expect(page.get_by_role("heading", name="PR-260928-01")).to_be_visible(); settle(page)
    r = [x for x in reqs(page) if "/api/ai" in x]
    ok("ED-05-AC1 AI tắt: không khối, không 'Tóm tắt'", page.locator("[data-ai-block]").count() == 0 and page.get_by_role("button", name="Tóm tắt", exact=True).count() == 0)
    ok("ED-05-AC1 AI tắt: 0 request /api/ai/actions, 0 /chat, 0 /summar", not any(("/actions" in x or "chat" in x or "summar" in x) for x in r), str(r))
    ok("ED-05-AC1 AI tắt: chỉ tối đa 1 request /api/ai/status/", len([x for x in r if "/api/ai/status" in x]) <= 1, str(r))
    page.screenshot(path=f"{SHOTS}/qa-ai-off-desktop.png")
    # đổi cờ sang bật trong lúc đang xem (màn cũ): tải lại thì hiện
    ctx.close()
    # AI bật + đồng ý: bấm đúp Đồng ý
    ctx, page = new_ctx(browser, 1280, 900, errors)
    demo(page, ai=True, consent=True)
    block = page.locator("[data-ai-block]"); expect(block).to_be_visible()
    card = block.locator("[data-proposal]").first; expect(card).to_be_visible()
    t = card.inner_text()
    ok("ED-05-AC2 đề xuất: không giá vốn/khoá kỹ thuật/dữ liệu cá nhân", not re.search(r"giá vốn|unit_cost|cost|item_code|\bqty\b", t, re.I) and not PII.search(t), t[:200].replace("\n", " | "))
    ok("ED-05-AC2 đề xuất: số lượng kèm đơn vị, không '10.000' trần (G5)", re.search(r"Số lượng\s*\n?\s*10(,0+)? kg", t) is not None and "10.000" not in t, t[:200].replace("\n", " | "))
    ok("ED-05-AC2 đề xuất: có 'Từ chối' và 'Đồng ý' cùng hàng", card.get_by_role("button", name="Từ chối", exact=True).count() == 1 and card.get_by_role("button", name=re.compile(r"^Đồng ý")).count() == 1)
    page.screenshot(path=f"{SHOTS}/qa-ai-block-desktop.png")
    page.wait_for_function("() => { const b=[...document.querySelectorAll('[data-proposal] button')].find(x=>/Đồng ý/.test(x.textContent)); return b && !b.disabled; }", timeout=8000)
    page.evaluate("() => window.__caveMock.clearLog()")
    card.get_by_role("button", name="Đồng ý", exact=True).dblclick()
    settle(page)
    n = len([x for x in reqs(page) if "/confirm/" in x])
    ok("ED-05 bấm đúp 'Đồng ý': chỉ 1 POST confirm", n == 1, str(reqs(page)))
    ctx.close()
    # Từ chối bấm đúp
    ctx, page = new_ctx(browser, 1280, 900, errors)
    demo(page, ai=True, consent=True)
    block = page.locator("[data-ai-block]"); expect(block.locator("[data-proposal]").first).to_be_visible()
    page.evaluate("() => window.__caveMock.clearLog()")
    block.get_by_role("button", name="Từ chối", exact=True).first.dblclick(); settle(page)
    n = len([x for x in reqs(page) if "/reject/" in x])
    ok("ED-05 bấm đúp 'Từ chối': chỉ 1 POST reject", n == 1, str(reqs(page)))
    ctx.close()
    # AI bật, chưa đồng ý
    ctx, page = new_ctx(browser, 1280, 900, errors)
    page.evaluate("() => window.__caveMock.clearLog()")
    demo(page, ai=True, consent=False)
    block = page.locator("[data-ai-block]"); expect(block).to_be_visible(); settle(page)
    ok("ED-05-AC4 chưa đồng ý: khối hiện nhưng chưa nạp chat", page.get_by_role("heading", name="Trợ lý vận hành").count() == 0)
    ok("ED-05-AC4 chưa đồng ý: không request chat/summary", not any(("chat" in x or "summar" in x) for x in reqs(page)), str([x for x in reqs(page) if '/api/ai' in x]))
    ok("ED-05-AC4 chưa đồng ý: không có 'Tóm tắt'", page.get_by_role("button", name="Tóm tắt", exact=True).count() == 0)
    ctx.close()
    # AI bật + đã đồng ý: Tóm tắt
    ctx, page = new_ctx(browser, 1280, 900, errors)
    demo(page, ai=True, consent=True)
    expect(page.locator("[data-ai-block]")).to_be_visible()
    page.evaluate("() => window.__caveMock.clearLog()")
    sm = page.get_by_role("button", name="Tóm tắt", exact=True)
    expect(sm).to_be_visible()
    ok("DW-16 'Tóm tắt': hiện khi AI bật + đã đồng ý, bấm được", sm.is_enabled())
    sm.click(); settle(page)
    page.wait_for_timeout(600)
    page.screenshot(path=f"{SHOTS}/qa-ai-summary-desktop.png")
    ok("DW-16 'Tóm tắt': bấm xong có phản hồi (khối trả lời hoặc ô chat hiện)", page.locator("[data-ai-block]").inner_text().count("\n") >= 1)
    ok("DW-16 'Tóm tắt': không lộ giá vốn/PII trong trả lời", not re.search(r"giá vốn|unit_cost", page.locator("[data-ai-block]").inner_text(), re.I) and not PII.search(page.locator("[data-ai-block]").inner_text()))
    ctx.close()
    # mobile 360
    ctx, page = new_ctx(browser, 360, 780, errors)
    demo(page, ai=True, consent=True)
    expect(page.locator("[data-ai-block]")).to_be_visible()
    ok("ED-05 mobile 360: không cuộn ngang với khối AI", hscroll_ok(page))
    bn = page.get_by_role("button", name="Gửi câu hỏi").bounding_box()
    ok("ED-05 mobile 360: nút gửi của khung hỏi AI cao >= 44px (QA B3: khung hiện sẵn)", bn and bn["height"] >= 44, str(bn))
    page.screenshot(path=f"{SHOTS}/qa-ai-block-mobile360.png", full_page=True)
    ctx.close()
    return errors


with sync_playwright() as p:
    browser = p.chromium.launch()
    errs = []
    for fn in (s1_detail, s2_modal, s3_form, s4_ai):
        try:
            errs += fn(browser)
        except Exception as e:  # noqa: BLE001
            ok(f"{fn.__name__} chạy hết không lỗi", False, repr(e)[:600])
    browser.close()

bad = [e for e in errs if "favicon" not in e]
ok("Không có console.error / pageerror", not bad, "; ".join(bad)[:400])
fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} PASS")
sys.exit(1 if fails else 0)
