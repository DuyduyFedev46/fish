# E2E ERP theo design, Lô 2 (mẫu trang chi tiết, popup, form, khối Trợ lý AI): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/ed_batch2_patterns.py      # tắt server sau khi xong
# Dùng trang nội bộ /dev-patterns/ và /dev-patterns/form/ (chỉ có ở bản mock). Mỗi kịch bản dùng context mới để trạng thái mock về seed.
# Kiểm: Modal (Esc, trả focus, khoá khi đang gửi, giữ Tab) · form lỗi -> "Thử lại" giữ nguyên giá trị · MoreMenu mục khoá có lý do ·
# 409 -> ConflictBanner · LookupCard không lộ giá vốn/khách · Timeline không mã BR · khối AI ẩn khi AI tắt, hiện khi bật,
# Đồng ý đếm ngược, chat chỉ nạp khi đã đồng ý · "Tóm tắt" trở lại khi AI bật + đã đồng ý · không console.error · mobile 360.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)


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


def open_demo(page, ai=None, consent=None, path="/dev-patterns/"):
    """Đặt cờ AI mock rồi tải thẳng trang demo (cờ nằm ở localStorage nên còn nguyên sau khi tải)."""
    if ai is not None:
        page.evaluate("(v) => window.__caveMock.ai(v)", "on" if ai else "off")
    if consent is not None:
        page.evaluate("(v) => window.__caveMock.aiConsent(v)", consent)
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def new_page(browser, w, h, errors, touch=False):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", **({"is_mobile": True, "has_touch": True} if touch else {}))
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("response", lambda r: r.status >= 400 and errors.append(f"HTTP {r.status} {r.url}"))
    login(page)
    return ctx, page


def focus_inside(page, sel):
    return page.evaluate("(s) => { const r = document.querySelector(s); return !!r && r.contains(document.activeElement); }", sel)


def modal_and_form(browser):
    errors = []
    ctx, page = new_page(browser, 1280, 860, errors)
    open_demo(page, ai=False)
    opener = page.get_by_role("button", name="Sửa phiếu", exact=True)
    expect(opener).to_be_visible()

    # --- Modal: mở, focus trong hộp, Esc đóng, trả focus
    opener.focus()
    opener.click()
    dlg = page.get_by_role("dialog", name="Sửa số lượng")
    expect(dlg).to_be_visible()
    ok("Modal: focus nằm trong hộp khi mở", focus_inside(page, '[role="dialog"]'))
    ok("Modal: ô đầu (autoFocus) được focus", page.evaluate("() => document.activeElement && document.activeElement.tagName === 'INPUT'"))
    inside = True
    for _ in range(8):
        page.keyboard.press("Tab")
        inside = inside and focus_inside(page, '[role="dialog"]')
    ok("Modal: Tab 8 lần vẫn ở trong hộp (giữ focus)", inside)
    for _ in range(8):
        page.keyboard.press("Shift+Tab")
        inside = inside and focus_inside(page, '[role="dialog"]')
    ok("Modal: Shift+Tab vẫn ở trong hộp", inside)
    page.keyboard.press("Escape")
    expect(dlg).to_have_count(0)
    ok("Modal: Esc đóng", True)
    ok("Modal: trả focus về nút đã mở nó", page.evaluate("() => document.activeElement && document.activeElement.textContent.trim() === 'Sửa phiếu'"))

    # --- Gửi lỗi: giữ giá trị, nút thành "Thử lại"; đang gửi thì Esc bị khoá
    opener.click()
    expect(dlg).to_be_visible()
    qty = dlg.get_by_label("Số lượng")
    qty.fill("33")
    save = dlg.get_by_role("button", name="Lưu", exact=True)
    save.click()
    ok("Đang gửi: nút đổi 'Đang gửi…' và bị khoá", dlg.get_by_role("button", name="Đang gửi…").is_disabled())
    page.keyboard.press("Escape")
    ok("Đang gửi: Esc KHÔNG đóng hộp (khoá)", dlg.count() == 1)
    alert = dlg.locator("[data-form-alert]")
    expect(alert).to_be_visible()
    ok("Lỗi: alert đỏ hiện lý do", "mạng chập chờn" in alert.inner_text(), alert.inner_text()[:80])
    ok("Lỗi: nút chính thành 'Thử lại'", dlg.get_by_role("button", name="Thử lại", exact=True).count() == 1)
    ok("Lỗi: giá trị đã nhập còn nguyên", qty.input_value() == "33", qty.input_value())
    page.screenshot(path=f"{SHOTS}/ed2-modal-error-desktop.png")
    dlg.get_by_role("button", name="Thử lại", exact=True).click()
    expect(dlg).to_have_count(0)
    ok("Thử lại thành công: hộp đóng", True)

    # --- Form page (mobile 360): thanh hành động dính đáy, lỗi -> Thử lại, giữ giá trị
    ctx2 = browser.new_context(viewport={"width": 360, "height": 640}, reduced_motion="reduce")
    p2 = ctx2.new_page()
    p2.on("console", lambda m: m.type == "error" and errors.append(m.text))
    login(p2)
    open_demo(p2, path="/dev-patterns/form/")
    expect(p2.get_by_role("heading", name="Nhập thử một phiếu")).to_be_visible()
    p2.get_by_label("Số lượng").fill("45")
    bar = p2.locator("[data-action-bar]")
    box = bar.bounding_box()
    ok("FormPage mobile: thanh hành động nằm trong khung nhìn (dính đáy)", box is not None and box["y"] + box["height"] <= 640 + 1, str(box))
    ok("FormPage mobile: nút chính cao >= 44px", p2.get_by_role("button", name="Lưu phiếu").bounding_box()["height"] >= 44)
    p2.get_by_role("button", name="Lưu phiếu").click()
    expect(p2.locator("[data-form-alert]")).to_be_visible()
    ok("FormPage lỗi: nút thành 'Thử lại'", p2.get_by_role("button", name="Thử lại", exact=True).count() == 1)
    ok("FormPage lỗi: giá trị còn nguyên", p2.get_by_label("Số lượng").input_value() == "45")
    ok("FormPage mobile 360: không cuộn ngang", no_hscroll(p2))
    p2.screenshot(path=f"{SHOTS}/ed2-form-error-mobile360.png")
    p2.get_by_role("button", name="Thử lại", exact=True).click()
    expect(p2.locator("[data-saved]")).to_be_visible()
    ok("FormPage: Thử lại thành công hiện 'Đã lưu phiếu.'", True)
    ctx2.close()
    ctx.close()
    return errors


def detail_blocks(browser):
    errors = []
    ctx, page = new_page(browser, 1280, 900, errors)
    open_demo(page, ai=False)
    expect(page.get_by_role("heading", name="PR-260928-01")).to_be_visible()

    # --- MoreMenu: mục bị khoá hiện lý do ngay cạnh nhãn
    page.get_by_role("button", name="Thao tác khác").click()
    blocked = page.get_by_role("menuitem", name=re.compile("Huỷ phiếu"))
    expect(blocked).to_be_visible()
    ok("MoreMenu: mục khoá có aria-disabled", blocked.get_attribute("aria-disabled") == "true")
    ok("MoreMenu: lý do hiện cạnh nhãn", "Phiếu đã có hoá đơn" in blocked.inner_text(), blocked.inner_text())
    page.screenshot(path=f"{SHOTS}/ed2-moremenu-desktop.png")
    page.keyboard.press("Escape")
    expect(page.get_by_role("menuitem").first).to_have_count(0)
    ok("MoreMenu: Esc đóng và trả focus về nút '…'", page.evaluate("() => document.activeElement.getAttribute('aria-label') === 'Thao tác khác'"))

    # --- Timeline: không mã BR, có nhãn AI
    tl = page.locator("[data-timeline-row]")
    ok("Timeline: có 2 dòng", tl.count() == 2, str(tl.count()))
    txt = page.locator("section[aria-label='Dòng thời gian']").inner_text()
    ok("Timeline: không in mã BR", not re.search(r"BR-\d", txt), txt[:120])
    ok("Timeline: có nhãn AI ở dòng AI làm", "AI" in txt)
    ok("Timeline: giờ Việt Nam (03:20 UTC -> 10:20)", "10:20" in txt, txt[:160])

    # --- StatusPath
    sp = page.locator("[data-state]")
    ok("StatusPath: 1 hiện tại, có bước đã qua và chưa tới", page.locator('[data-state="current"]').count() == 1 and page.locator('[data-state="done"]').count() >= 1 and page.locator('[data-state="todo"]').count() >= 1)
    ok("StatusPath: có 'Tiếp theo' và 'Đã làm'", page.get_by_text("Tiếp theo:").count() == 1 and page.get_by_text("Đã làm:").count() >= 1)

    # --- Sửa tại chỗ + 409 -> ConflictBanner
    pencil = page.locator('button[aria-label="Sửa số lượng"]').last
    pencil.click()
    box = page.locator("dl input").first
    box.fill("409")
    box.press("Enter")
    banner = page.locator("[data-conflict-banner]")
    expect(banner).to_be_visible()
    ok("409: ConflictBanner hiện, nói rõ 'vừa được ... sửa'", "vừa được" in banner.inner_text(), banner.inner_text()[:100])
    ok("409: banner có tên người sửa và giờ Việt Nam từ thân 409 của BE", "Lộc" in banner.inner_text() and "10:30" in banner.inner_text(), banner.inner_text()[:120])
    editing_dt = page.locator("[data-editing] dt")
    ok("Sửa tại chỗ: nhãn ô InfoField không hiện trùng với nhãn Field (chỉ còn cho trình đọc màn hình)", editing_dt.count() == 1 and editing_dt.first.bounding_box()["width"] <= 2, str(editing_dt.first.bounding_box()))
    ok("Sửa tại chỗ: đúng một nhãn 'Số lượng' nhìn thấy trong ô", page.locator("[data-editing] label:visible").count() == 1)
    ok("409: ô sửa giữ nguyên giá trị đang gõ (không mất)", page.locator("dl input").first.input_value() == "409")
    page.screenshot(path=f"{SHOTS}/ed2-conflict-desktop.png")
    banner.get_by_role("button", name="Tải lại").click()
    expect(banner).to_have_count(0)
    ok("409: bấm Tải lại -> banner mất, trang được yêu cầu tải lại", page.locator("[data-reload-count='1']").count() == 1)

    # --- M1: 409 KHÔNG phải xung đột sửa (CLAIMED) -> lỗi thường giữ lý do của BE, không banner "vừa được ... sửa"
    page.locator("dl input").first.fill("410")
    page.locator("dl input").first.press("Enter")
    expect(page.locator("[data-editing]")).to_contain_text("đang có người nhận xử lý")
    ok("M1: 409 CLAIMED hiện lý do của BE", "đang có người nhận xử lý" in page.locator("[data-editing]").inner_text(), page.locator("[data-editing]").inner_text()[:140])
    ok("M1: 409 CLAIMED KHÔNG hiện ConflictBanner", page.locator("[data-conflict-banner]").count() == 0)
    # --- B5: ô sửa tại chỗ để trống -> lỗi dưới ô, nút vẫn là "Lưu" (không "Thử lại")
    page.locator("dl input").first.fill("")
    page.locator("dl input").first.press("Enter")
    ok("B5: để trống -> có lỗi dưới ô", "Nhập" in page.locator("[data-editing]").inner_text() or "bắt buộc" in page.locator("[data-editing]").inner_text(), page.locator("[data-editing]").inner_text()[:140])
    ok("B5: nút chính vẫn là 'Lưu', không phải 'Thử lại'", page.locator("[data-editing]").get_by_role("button", name="Lưu", exact=True).count() == 1 and page.locator("[data-editing]").get_by_role("button", name="Thử lại").count() == 0)
    page.screenshot(path=f"{SHOTS}/ed2-inplace-empty-desktop.png")

    # --- LookupCard: không lộ giá vốn / khách
    page.get_by_role("button", name=re.compile("CA01-260928-AB12C")).click()
    card = page.get_by_role("dialog")
    expect(card).to_be_visible()
    expect(card.get_by_text("Cá thu một nắng").first).to_be_visible()
    ct = card.inner_text()
    ok("LookupCard: hiện thông tin lô", "Còn bán" in ct and "18" in ct, ct[:120])
    ok("LookupCard: không có giá vốn", "123456" not in ct and "123.456" not in ct and "Giá vốn" not in ct)
    link = card.get_by_role("link", name=re.compile("Mở trang lô"))
    ok("LookupCard: nút mở trang đầy đủ trỏ đúng route", (link.get_attribute("href") or "").startswith("/inventory/detail/?id=1"), link.get_attribute("href") or "")
    page.screenshot(path=f"{SHOTS}/ed2-lookup-desktop.png")
    page.keyboard.press("Escape")
    expect(card).to_have_count(0)
    ok("LookupCard: Esc đóng", True)

    # --- Giá vốn khoá: có icon + lý do cho trình đọc màn hình
    locked = page.locator("dl").get_by_text("Giá vốn chỉ Chủ được xem")
    ok("InfoField khoá: có lý do (đọc được bằng trình đọc màn hình)", locked.count() >= 1)
    ctx.close()
    return errors


def ai_block(browser):
    errors = []
    # --- AI tắt: không có khối, và demo không gọi đề xuất AI
    ctx, page = new_page(browser, 1280, 900, errors)
    page.evaluate("() => window.__caveMock.clearLog()")
    open_demo(page, ai=False, consent=True)
    expect(page.get_by_role("heading", name="PR-260928-01")).to_be_visible()
    settle(page)
    ok("AI tắt: không có khối Trợ lý AI", page.locator("[data-ai-block]").count() == 0)
    log = page.evaluate("() => window.__caveMock.log.slice()")
    ok("AI tắt: không gọi /api/ai/actions", not any("/api/ai/actions" in str(e) for e in log), str([e for e in log if "/api/ai" in str(e)]))
    ok("AI tắt: không có nút 'Tóm tắt' dù đã đồng ý", page.get_by_role("button", name="Tóm tắt", exact=True).count() == 0)
    ctx.close()

    # --- AI bật + đã đồng ý: khối hiện, Đồng ý đếm ngược, bấm Đồng ý -> hết đề xuất + trang được báo; "Tóm tắt" trở lại
    ctx, page = new_page(browser, 1280, 900, errors)
    open_demo(page, ai=True, consent=True)
    block = page.locator("[data-ai-block]")
    expect(block).to_be_visible()
    card = block.locator("[data-proposal]").first
    expect(card).to_be_visible()
    ok("AI bật: hiện đề xuất đúng chứng từ", "Xác nhận phiếu nhập hàng" in card.inner_text(), card.inner_text()[:80])
    ok("AI bật: hiện người đề xuất 'AI của Lộc'", "AI của Lộc" in card.inner_text())
    ok("AI bật: bảng thay đổi có nhãn tiếng Việt, không lộ khoá kỹ thuật", "Số lượng" in card.inner_text() and "qty" not in card.inner_text() and "item_code" not in card.inner_text())
    confirm = card.get_by_role("button", name=re.compile(r"^Đồng ý"))
    ok("Đồng ý: ban đầu bị khoá, nhãn có số giây chờ (BR-AI-14)", confirm.is_disabled() and re.search(r"\(\d\)", confirm.inner_text()) is not None, confirm.inner_text())
    page.screenshot(path=f"{SHOTS}/ed2-ai-block-desktop.png")
    page.wait_for_function("() => { const b=[...document.querySelectorAll('[data-proposal] button')].find(x=>/Đồng ý/.test(x.textContent)); return b && !b.disabled; }", timeout=8000)
    ok("Đồng ý: sau ~3 giây được bấm", not card.get_by_role("button", name=re.compile(r"^Đồng ý")).is_disabled())
    page.evaluate("() => window.__caveMock.clearLog()")
    # B4: 3 lần bấm Đồng ý trong CÙNG một nhịp (trước khi React kịp khoá nút) vẫn chỉ 1 POST
    page.evaluate("() => { const b=[...document.querySelectorAll('[data-proposal] button')].find(x=>x.textContent.trim()==='Đồng ý'); b.click(); b.click(); b.click(); }")
    expect(block.get_by_text("Chưa có đề xuất nào cho chứng từ này.")).to_be_visible()
    log = page.evaluate("() => window.__caveMock.log.slice()")
    ok("B4: 3 lần bấm cùng nhịp -> đúng 1 POST confirm", len([e for e in log if "POST /api/ai/actions/" in str(e) and "/confirm/" in str(e)]) == 1, str(log)[:200])
    ok("Đồng ý: báo trang tải lại chứng từ (onApplied)", page.locator("[data-applied-count='1']").count() == 1)
    ok("AI bật + đã đồng ý: có nút 'Tóm tắt' (DW-16)", page.get_by_role("button", name="Tóm tắt", exact=True).count() == 1)
    # B3: khung hỏi nhanh (chip + ô nhập + nút gửi) hiện sẵn, KHÔNG cần bấm nút "Hỏi trợ lý"; panel chỉ nạp khi chạm vào
    starter = block.locator("[data-ai-starter]")
    ok("B3: chip + ô nhập + nút gửi hiện sẵn trong khối", starter.count() == 1 and starter.get_by_role("textbox").count() == 1 and starter.get_by_role("button", name="Gửi câu hỏi").count() == 1)
    ok("B3: có chip gợi ý", starter.locator("button").count() >= 3)
    ok("B3: chưa nạp panel trợ lý khi chưa chạm", page.get_by_role("heading", name="Trợ lý vận hành").count() == 0)
    starter.get_by_role("textbox").focus()
    expect(page.get_by_role("heading", name="Trợ lý vận hành")).to_be_visible()
    ok("B3: chạm vào ô nhập nạp panel trợ lý (nạp động)", True)
    expect(block.get_by_role("textbox")).to_be_focused()
    ok("B3: focus được chuyển sang ô nhập của panel, gõ tiếp được ngay", True)
    page.keyboard.type("Phiếu này đã nhập chưa?")
    ok("B3: chữ gõ sau khi chạm nằm trong ô của panel", block.get_by_role("textbox").input_value() == "Phiếu này đã nhập chưa?", block.get_by_role("textbox").input_value())
    ok("B3: khung tĩnh nhường chỗ cho panel (không còn 2 ô nhập)", block.get_by_role("textbox").count() == 1)
    ctx.close()

    # B3: bấm chip -> panel nạp và gửi luôn câu đó
    ctx, page = new_page(browser, 1280, 900, errors)
    open_demo(page, ai=True, consent=True)
    block = page.locator("[data-ai-block]")
    expect(block.locator("[data-ai-starter]")).to_be_visible()
    chip = block.locator("[data-ai-starter] button").first
    chip_text = chip.inner_text().strip()
    chip.click()
    expect(page.get_by_role("heading", name="Trợ lý vận hành")).to_be_visible()
    expect(block.get_by_text(chip_text).first).to_be_visible()
    ok("B3: bấm chip -> panel nạp và câu của chip được gửi", True, chip_text)
    ctx.close()

    # --- AI bật, chưa đồng ý: có đề xuất nhưng chat đòi đồng ý, chưa nạp trợ lý, không có 'Tóm tắt'
    ctx, page = new_page(browser, 1280, 900, errors)
    open_demo(page, ai=True, consent=False)
    block = page.locator("[data-ai-block]")
    expect(block).to_be_visible()
    ok("Chưa đồng ý: vẫn thấy đề xuất để duyệt (không cần model)", block.locator("[data-proposal]").count() == 1)
    ok("Chưa đồng ý: không có nút 'Tóm tắt'", page.get_by_role("button", name="Tóm tắt", exact=True).count() == 0)
    block.locator("[data-ai-starter]").get_by_role("textbox").focus()
    enable = block.get_by_role("button", name="Bật trợ lý")
    expect(enable).to_be_visible()
    ok("Chưa đồng ý: nút 'Bật trợ lý' khoá tới khi tick ô đồng ý", enable.is_disabled())
    ok("Chưa đồng ý: chưa nạp trợ lý", page.get_by_role("heading", name="Trợ lý vận hành").count() == 0)
    # Từ chối đề xuất
    block.get_by_role("button", name="Từ chối", exact=True).click()
    expect(block.get_by_text("Chưa có đề xuất nào cho chứng từ này.")).to_be_visible()
    ok("Từ chối: đề xuất biến mất khỏi khối", True)
    ctx.close()

    # --- M2: tải chi tiết đề xuất lỗi -> báo lỗi + "Thử lại", Đồng ý không kẹt ở "Đồng ý (3)", ngừng đếm
    ctx, page = new_page(browser, 1280, 900, errors)
    page.evaluate("() => window.__caveMock.aiDetailFail(true)")
    open_demo(page, ai=True, consent=True)
    block = page.locator("[data-ai-block]")
    expect(block.get_by_role("alert")).to_be_visible()
    ok("M2: lỗi tải chi tiết hiện thông báo rõ", "Chưa mở được chi tiết" in block.inner_text(), block.inner_text()[:160])
    retry = block.get_by_role("button", name="Thử lại")
    ok("M2: có nút 'Thử lại'", retry.count() >= 1)
    page.wait_for_timeout(4500)
    labels = [b.inner_text().strip() for b in block.locator("[data-proposal] button").all()]
    ok("M2: sau 4,5 giây nút Đồng ý không kẹt ở số đếm", not any(re.match(r"Đồng ý \(\d\)", x) for x in labels), str(labels))
    ok("M2: Đồng ý vẫn khoá (không có chi tiết thì không được duyệt)", block.get_by_role("button", name=re.compile(r"^Đồng ý")).first.is_disabled())
    page.evaluate("() => window.__caveMock.aiDetailFail(false)")
    retry.first.click()
    page.wait_for_function("() => { const b=[...document.querySelectorAll('[data-proposal] button')].find(x=>/Đồng ý/.test(x.textContent)); return b && !b.disabled; }", timeout=9000)
    ok("M2: Thử lại thành công -> hết lỗi, Đồng ý mở sau thời gian chờ", block.get_by_role("alert").count() == 0)
    page.screenshot(path=f"{SHOTS}/ed2-ai-detail-error-desktop.png")
    ctx.close()

    # --- Mobile 360: khối AI không cuộn ngang
    ctx, page = new_page(browser, 360, 780, errors, touch=True)
    open_demo(page, ai=True, consent=False)
    expect(page.locator("[data-ai-block]")).to_be_visible()
    ok("Mobile 360: trang chi tiết không cuộn ngang", no_hscroll(page))
    st = page.locator("[data-ai-starter]")
    ok("Mobile 360: ô hỏi AI và nút gửi cao >= 44px", st.get_by_role("textbox").bounding_box()["height"] >= 44 and st.get_by_role("button", name="Gửi câu hỏi").bounding_box()["height"] >= 44 and st.locator("button").first.bounding_box()["height"] >= 44)
    page.screenshot(path=f"{SHOTS}/ed2-detail-mobile360.png", full_page=True)
    page.get_by_role("button", name="Thao tác khác").click()
    page.screenshot(path=f"{SHOTS}/ed2-moremenu-mobile360.png")
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Sửa phiếu", exact=True).click()
    expect(page.get_by_role("dialog")).to_be_visible()
    ok("Mobile 360: popup là tấm trượt đáy, không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/ed2-modal-mobile360.png")
    ctx.close()
    return errors


with sync_playwright() as p:
    browser = p.chromium.launch()
    errs = []
    for fn in (modal_and_form, detail_blocks, ai_block):
        try:
            errs += fn(browser)
        except Exception as e:  # noqa: BLE001
            ok(f"{fn.__name__} chạy hết không lỗi", False, repr(e)[:500])
    browser.close()

bad = [e for e in errs if "favicon" not in e]
ok("Không có console.error / pageerror", not bad, "; ".join(bad)[:400])
fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} PASS")
sys.exit(1 if fails else 0)
