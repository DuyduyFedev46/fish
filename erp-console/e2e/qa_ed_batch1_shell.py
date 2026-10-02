"""QA độc lập đợt 1: hành vi khung (sidebar, avatar, ⌘K, 404, lỗi chung, mất mạng, bố cục) trên bản build MOCK.

Phủ ED-01-AC1/AC2/AC3, ED-03-AC6, ED-03-AC4 (phần khung), T3, T4, T5, G10 và ca ngoài đường thuận:
localStorage rác, bàn phím, ⌘K gõ tên/SĐT khách, 404 cho người chỉ thuộc nhóm giao, lỗi render rồi Thử lại,
mất mạng rồi có mạng lại, cuộn ngang ở 1280/1440/360.
Ảnh lưu ở $SHOTS (mặc định /tmp/qa_ed_batch1); toàn dữ liệu giả của mock.
"""

import re
import sys

from playwright.sync_api import expect, sync_playwright

from qa_ed_batch1_common import (BASE, FULL_ORDER, SHOTS, fonts_ready, fulfil_404, login, nav_labels, ok, relevant_errors,
                                 summary)

errors = []
console_all = []


def new_page(browser, user, width=1440, height=900, **kw):
    ctx = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce", **kw)
    page = ctx.new_page()
    page.on("console", lambda m: (console_all.append(m.text), m.type == "error" and errors.append(m.text)))
    login(page, user)
    return ctx, page


def settle(page):
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => document.querySelector('#main') && document.querySelector('#main').innerText.trim().length > 0")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ===================== Sidebar =====================
    ctx, page = new_page(browser, "loc")
    page.wait_for_url("**/overview/")
    settle(page)
    fonts_ready(page)
    rail = page.locator("#rail-left")
    ok("ED-01-AC2 mở rộng rộng 240px", abs(rail.bounding_box()["width"] - 240) <= 1)
    ok("ED-01-AC2 nút thu gọn có nhãn đọc và aria-expanded=true",
       page.get_by_test_id("sidebar-toggle").get_attribute("aria-expanded") == "true"
       and page.get_by_test_id("sidebar-toggle").get_attribute("aria-label") == "Thu gọn menu")
    page.screenshot(path=f"{SHOTS}/sidebar-open-1440.png")
    # bằng bàn phím
    page.get_by_test_id("sidebar-toggle").focus()
    page.keyboard.press("Enter")
    expect(page.locator("#rail-left.collapsed")).to_have_count(1)
    page.wait_for_function("() => Math.abs(document.querySelector('#rail-left').getBoundingClientRect().width - 60) <= 1")
    ok("ED-01-AC2 thu gọn bằng bàn phím (Enter) còn 60px", abs(rail.bounding_box()["width"] - 60) <= 1, rail.bounding_box())
    ok("ED-01-AC2 vùng nội dung dịch sang trái theo (bắt đầu ở x=60)", abs(page.locator(".center").bounding_box()["x"] - 60) <= 1)
    ok("ED-01-AC2 thu gọn: nhãn chữ và tiêu đề nhóm không hiện", not page.locator("#rail-left .nav-label").first.is_visible()
       and page.locator("#rail-left .nav-h").first.is_hidden())
    links = page.locator("#rail-left .nav a")
    no_tip = [links.nth(i).get_attribute("aria-label") for i in range(links.count())
              if not (links.nth(i).get_attribute("title") and links.nth(i).get_attribute("title") == links.nth(i).get_attribute("aria-label"))]
    ok("ED-01-AC2 thu gọn: mọi mục đều có tooltip (title) và tên đọc (aria-label)", not no_tip, no_tip)
    ok("ED-01-AC2 thu gọn: mục đang mở vẫn tô", page.locator("#rail-left .nav a[aria-current=page]").count() == 1)
    ok("ED-01-AC2 thu gọn: icon không bị cắt (rộng liên kết >= 32px, không cuộn ngang trong menu)",
       page.evaluate("() => { const n = document.querySelector('#rail-left'); return n.scrollWidth <= n.clientWidth + 1 }")
       and all(links.nth(i).bounding_box()["width"] >= 32 for i in range(links.count())))
    page.screenshot(path=f"{SHOTS}/sidebar-collapsed-1440.png")
    # đổi trang bằng bấm menu: vẫn thu gọn
    links.nth(1).click()
    page.wait_for_url("**/orders/")
    settle(page)
    ok("ED-01-AC2 sang màn khác (không tải lại) vẫn thu gọn", page.locator("#rail-left.collapsed").count() == 1)
    page.reload()
    page.wait_for_selector("#rail-left .nav a", state="attached")
    ok("ED-01-AC2 tải lại vẫn thu gọn 60px", page.locator("#rail-left.collapsed").count() == 1 and abs(rail.bounding_box()["width"] - 60) <= 1)
    # không nháy: ngay khi DOM tải xong đã đúng trạng thái? (đọc trước khi vẽ lần đầu)
    page.get_by_test_id("sidebar-toggle").click()
    page.wait_for_function("() => Math.abs(document.querySelector('#rail-left').getBoundingClientRect().width - 240) <= 1")
    ok("ED-01-AC2 mở lại 240px", abs(rail.bounding_box()["width"] - 240) <= 1)
    # giá trị rác
    for junk in ['<img src=x onerror=alert(1)>', "", "collapsed ", "null", "undefined", "{}", "1", "x" * 20000]:
        page.evaluate("(v) => localStorage.setItem('cave_ui_sidebar', v)", junk)
        page.reload()
        page.wait_for_selector("#rail-left .nav a", state="attached")
        settle(page)
        good = page.locator("#rail-left.collapsed").count() == 0 and abs(rail.bounding_box()["width"] - 240) <= 1 and len(nav_labels(page)) == 12
        ok(f"ED-01-AC2 localStorage rác ({junk[:14]!r}) -> mở rộng, menu đủ, không vỡ", good)
    page.evaluate("() => localStorage.setItem('cave_ui_sidebar', 'collapsed')")
    page.reload()
    page.wait_for_selector("#rail-left .nav a", state="attached")
    # bóp cửa sổ <768 khi đang 'collapsed' trong localStorage -> ngăn kéo đầy đủ chữ
    page.set_viewport_size({"width": 360, "height": 740})
    page.get_by_role("button", name="Mở menu").click()
    expect(page.locator("#rail-left.open")).to_be_visible()
    ok("T4 360 + localStorage 'collapsed': ngăn kéo vẫn đủ chữ, rộng > 200px",
       page.locator("#rail-left .nav-label").first.is_visible() and page.locator("#rail-left").bounding_box()["width"] > 200,
       page.locator("#rail-left").bounding_box())
    page.keyboard.press("Escape")
    page.evaluate("() => localStorage.removeItem('cave_ui_sidebar')")
    ctx.close()

    # ===================== Topbar + avatar (bàn phím) =====================
    ctx, page = new_page(browser, "loc")
    settle(page)
    top = page.locator("header.topbar")
    ok("ED-01-AC1 topbar: tên màn bên trái, ô tìm và avatar bên phải",
       top.locator("h1").inner_text() == "Tổng quan" and top.locator(".search-trigger").is_visible() and top.locator(".avatar-btn").is_visible())
    bb = {k: top.locator(s).bounding_box() for k, s in {"h1": "h1", "search": ".search-trigger", "avatar": ".avatar-btn"}.items()}
    ok("ED-01-AC1 thứ tự trái -> phải: tên màn, ô tìm, avatar", bb["h1"]["x"] < bb["search"]["x"] < bb["avatar"]["x"], bb)
    ok("ED-01-AC1 không có nút 'Làm mới', 'Đăng xuất' rời, đổi sáng/tối ở topbar",
       top.get_by_text("Làm mới").count() == 0 and top.get_by_role("button", name="Đăng xuất").count() == 0
       and top.locator(".theme-toggle").count() == 0 and top.get_by_role("button", name=re.compile("sáng|tối|giao diện", re.I)).count() == 0)
    ok("ED-01-AC1 ô tìm ghi phím tắt ⌘K", "⌘K" in top.locator(".search-trigger").inner_text())
    avatar = page.locator(".avatar-btn")
    avatar.focus()
    ok("avatar: aria-haspopup=menu, aria-expanded=false khi đóng", avatar.get_attribute("aria-haspopup") == "menu" and avatar.get_attribute("aria-expanded") == "false")
    page.keyboard.press("Enter")
    expect(page.locator("[role=menu]")).to_be_visible()
    focused = lambda: page.evaluate("() => document.activeElement && document.activeElement.innerText.trim().split('\\n').pop().trim()")
    page.wait_for_function("() => document.activeElement && document.activeElement.getAttribute('role') === 'menuitem'")
    ok("ED-01-AC3 Enter mở menu và focus vào mục đầu 'Tài khoản của tôi'", focused() == "Tài khoản của tôi", focused())
    page.keyboard.press("ArrowDown")
    ok("avatar: mũi tên xuống -> 'AI của tôi'", focused() == "AI của tôi", focused())
    page.keyboard.press("ArrowDown")
    ok("avatar: mũi tên xuống -> 'Đăng xuất'", focused() == "Đăng xuất", focused())
    page.keyboard.press("ArrowDown")
    ok("avatar: mũi tên xuống ở cuối quay vòng về mục đầu", focused() == "Tài khoản của tôi", focused())
    page.keyboard.press("ArrowUp")
    ok("avatar: mũi tên lên ở đầu quay vòng về 'Đăng xuất'", focused() == "Đăng xuất", focused())
    page.keyboard.press("Home")
    ok("avatar: Home -> mục đầu", focused() == "Tài khoản của tôi")
    page.keyboard.press("End")
    ok("avatar: End -> mục cuối", focused() == "Đăng xuất")
    page.screenshot(path=f"{SHOTS}/avatar-menu-open-1440.png")
    page.keyboard.press("Escape")
    expect(page.locator("[role=menu]")).to_have_count(0)
    ok("ED-01-AC3 Esc đóng menu và trả focus về nút avatar", page.evaluate("() => document.activeElement.classList.contains('avatar-btn')"))
    # Space mở
    page.keyboard.press("Space")
    ok("avatar: phím Space mở menu", page.locator("[role=menu]").count() == 1)
    page.wait_for_function("() => document.activeElement && document.activeElement.getAttribute('role') === 'menuitem'")
    page.keyboard.press("Tab")
    expect(page.locator("[role=menu]")).to_have_count(0)
    ok("avatar: Tab ra ngoài thì đóng menu", True)
    # ArrowDown trên nút
    avatar.focus()
    page.keyboard.press("ArrowDown")
    ok("avatar: ArrowDown trên nút mở menu", page.locator("[role=menu]").count() == 1)
    # bấm ra ngoài
    page.mouse.click(600, 500)
    ok("avatar: bấm ra ngoài đóng menu", page.locator("[role=menu]").count() == 0)
    # Enter trên 'AI của tôi'
    avatar.focus()
    page.keyboard.press("Enter")
    page.wait_for_function("() => document.activeElement && document.activeElement.getAttribute('role') === 'menuitem'")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_url("**/ai/settings/")
    ok("ED-01-AC3 Enter trên 'AI của tôi' mở màn AI của tôi, menu đóng", page.locator("[role=menu]").count() == 0 and page.locator("header.topbar h1").inner_text() == "AI của tôi",
       page.locator("header.topbar h1").inner_text())
    avatar.click()
    page.get_by_role("menuitem", name="Tài khoản của tôi").click()
    page.wait_for_url("**/account/")
    settle(page)
    ok("ED-01-AC3 'Tài khoản của tôi' mở màn tài khoản", page.locator("header.topbar h1").inner_text() == "Tài khoản của tôi")
    # đăng xuất bằng bàn phím
    avatar.focus()
    page.keyboard.press("Enter")
    page.wait_for_function("() => document.activeElement && document.activeElement.getAttribute('role') === 'menuitem'")
    page.keyboard.press("End")
    page.keyboard.press("Enter")
    page.wait_for_url("**/login/**")
    ok("ED-01-AC3 Đăng xuất (bàn phím) -> màn Đăng nhập, token đã xoá",
       "/login" in page.url and not page.evaluate("() => localStorage.getItem('cave_erp_token')"), page.url)
    page.goto(BASE + "/orders/")
    page.wait_for_url("**/login/**")
    ok("ED-01-AC3 sau đăng xuất: vào lại /orders/ bị đưa về Đăng nhập", "/login" in page.url)
    page.go_back()
    page.wait_for_load_state("networkidle")
    ok("ED-01-AC3 sau đăng xuất bấm Back không thấy lại dữ liệu nội bộ", page.locator("#rail-left .nav a").count() == 0)
    ctx.close()

    # ===================== ⌘K =====================
    ctx, page = new_page(browser, "loc")
    page.goto(BASE + "/orders/")
    settle(page)
    # lấy tên và SĐT khách giả đang hiện trên màn Đơn để thử tìm bằng ⌘K
    page.wait_for_function("() => document.querySelectorAll('#main table tbody tr, #main .ocard, #main li').length > 2")
    body_text = page.locator("#main").inner_text()
    phones = re.findall(r"0\d{2,3}[ .]?\d{3}[ .]?\d{3,4}", body_text)
    phones = list(dict.fromkeys(phones))[:3]
    names = re.findall(r"(?:Nguyễn|Trần|Lê|Phạm|Hoàng|Khách)[ \wÀ-ỹ]{2,22}", body_text)
    names = list(dict.fromkeys(n.strip() for n in names))[:4]
    codes = list(dict.fromkeys(re.findall(r"SO\d{6}-[0-9A-F]{6}", body_text)))[:2]
    ok("(chuẩn bị) lấy được dữ liệu giả để dò ⌘K", bool(names or phones or codes), (names, phones, codes))
    log_before = page.evaluate("() => window.__caveMock.log.length")
    probes = names + phones + codes + ["Nguyen", "0912", "09", "SO2609", "ao dai"]
    leaked = []
    for q in probes:
        page.keyboard.press("Meta+k")
        dlg = page.get_by_role("dialog", name="Tìm màn hình")
        expect(dlg).to_be_visible()
        page.get_by_role("combobox", name="Tìm màn hình").fill(q)
        opts = [t.strip() for t in page.locator(".cmd").get_by_role("option").all_inner_texts()]
        if opts:
            leaked.append((q, opts))
        page.keyboard.press("Escape")
    ok("ED-01 ⌘K không tìm ra mục nào khi gõ tên/SĐT/mã đơn khách (T5, G10)", not leaked, leaked)
    ok("ED-01 ⌘K không gọi API nào khi gõ", page.evaluate("() => window.__caveMock.log.length") == log_before)
    # bỏ các khoá 'cave_erp_mock_*' (kho dữ liệu giả của chính bản mock, không có ở bản thật)
    stored = page.evaluate("() => JSON.stringify(Object.entries(localStorage).filter(([k]) => !k.startsWith('cave_erp_mock_')).concat(Object.entries(sessionStorage).filter(([k]) => !k.startsWith('cave_erp_mock_'))))")
    ok("G10 ⌘K: từ khoá/tên/SĐT không nằm trong localStorage/sessionStorage/URL (trừ kho mock)",
       not any(q.lower() in (stored + page.url).lower() for q in probes if len(q) > 3), stored[:300])
    dlg = page.get_by_role("dialog", name="Tìm màn hình")
    page.keyboard.press("Control+k")
    expect(dlg).to_be_visible()
    page.wait_for_function("() => document.activeElement && document.activeElement.getAttribute('role') === 'combobox'")
    ok("ED-01 ⌘K mở bằng Ctrl+K, ô gõ nhận focus", True)
    page.keyboard.press("Escape")
    expect(dlg).to_have_count(0)
    ok("ED-01 ⌘K: Esc đóng", True)
    ok("ED-01 ⌘K: sau khi đóng, focus quay lại ô tìm/nút kích hoạt (a11y)",
       page.evaluate("() => document.activeElement && document.activeElement.tagName !== 'BODY'"),
       "focus rơi về BODY sau Esc (Low, a11y)")
    page.get_by_role("button", name="Tìm màn hình").first.click()
    expect(dlg).to_be_visible()
    ok("ED-01 ⌘K mở bằng bấm ô tìm", True)
    page.get_by_role("combobox", name="Tìm màn hình").fill("nhat ky")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_url("**/audit-logs/")
    ok("ED-01 ⌘K: gõ 'nhat ky' (không dấu) + Enter nhảy tới Nhật ký hoạt động", "/audit-logs" in page.url)
    settle(page)
    page.screenshot(path=f"{SHOTS}/cmdk-1440.png")
    page.keyboard.press("Control+k")
    page.locator(".cmd").get_by_role("option").first.wait_for()
    page.wait_for_function("() => document.querySelector('.cmd input').value === '' && document.querySelectorAll('.cmd [role=option]').length > 3")
    labels_in_cmd = page.locator(".cmd [role=option] > span").all_inner_texts()
    expected_menu = nav_labels(page)
    ok("ED-01 ⌘K khi chưa gõ: danh sách = đúng menu của vai", labels_in_cmd == expected_menu, (labels_in_cmd, expected_menu))
    page.screenshot(path=f"{SHOTS}/cmdk-open-1440.png")
    page.keyboard.press("Escape")
    ctx.close()
    # ⌘K của giao1: không thấy mục nào ngoài 'Việc giao của tôi'
    ctx, page = new_page(browser, "giao1")
    settle(page)
    page.keyboard.press("Control+k")
    labels_in_cmd = page.locator(".cmd [role=option] > span").all_inner_texts()
    ok("⌘K vai giao1: chỉ có 'Việc giao của tôi'", labels_in_cmd == ["Việc giao của tôi"], labels_in_cmd)
    page.get_by_role("combobox", name="Tìm màn hình").fill("don")
    ok("⌘K vai giao1: gõ 'don' không ra mục Đơn & tiền", page.locator(".cmd").get_by_role("option").count() == 0)
    page.keyboard.press("Escape")
    ctx.close()

    # ===================== 404 trong khung =====================
    for user in ("loc", "giao1"):
        ctx, page = new_page(browser, user)
        settle(page)
        fulfil_404(page, "**/khong-co-man-nay/**")
        fulfil_404(page, "**/orders/abc/**")
        page.goto(BASE + "/khong-co-man-nay/")
        page.wait_for_selector(".page-state")
        expect(page.get_by_text("Không tìm thấy trang này")).to_be_visible()
        ok(f"ED-03-AC6 [{user}] 404 trong khung: có sidebar, topbar, avatar", page.locator("#rail-left .nav a").count() > 0
           and page.locator("header.topbar .avatar-btn").is_visible())
        # Vòng 2 (B2): nút về nhà theo vai: giao1 về "Việc giao của tôi", các vai còn lại về "Tổng quan".
        home_label = "Về Việc giao của tôi" if user == "giao1" else "Về Tổng quan"
        ok(f"ED-03-AC6 [{user}] 404 có nút '{home_label}'", page.get_by_role("link", name=home_label).count() == 1)
        if user == "loc":
            page.screenshot(path=f"{SHOTS}/404-1440.png")
        if user == "giao1":
            page.screenshot(path=f"{SHOTS}/404-giao1-1440.png")
            page.get_by_role("link", name=home_label).click()
            page.wait_for_load_state("networkidle")
            settle(page)
            txt = page.locator("#main").inner_text()
            ok("ED-03-AC6 [giao1] nút về nhà ở 404 không dẫn tới màn 'Không có quyền' (ngõ cụt)",
               "Bạn không có quyền xem mục này" not in txt, page.url + " | " + txt[:80])
        # URL lạ lồng nhau
        page.goto(BASE + "/orders/abc/")
        page.wait_for_selector(".page-state")
        ok(f"ED-03-AC6 [{user}] URL lạ lồng nhau /orders/abc/ cũng ra 404 trong khung", page.get_by_text("Không tìm thấy trang này").is_visible()
           and page.locator("#rail-left .nav a").count() > 0)
        ctx.close()
    # chưa đăng nhập vào URL lạ -> về Đăng nhập, không lộ khung
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    fulfil_404(page, "**/khong-co-man-nay/**")
    page.goto(BASE + "/khong-co-man-nay/")
    page.wait_for_url("**/login/**")
    ok("ED-03-AC6 chưa đăng nhập vào URL lạ -> Đăng nhập (không lộ khung app)", page.locator("#rail-left").count() == 0)
    ctx.close()

    # ===================== Lỗi chung + Thử lại =====================
    ctx, page = new_page(browser, "loc")
    page.goto(BASE + "/stocktake/")
    settle(page)
    page.evaluate("""() => {
        window.__qaBreak = true;
        const o2 = Number.prototype.toLocaleString;
        Number.prototype.toLocaleString = function (...a) { if (window.__qaBreak) throw new Error('qa-induced render error SECRET-NAME-0901'); return o2.apply(this, a); };
    }""")
    page.locator("#rail-left .nav a", has_text="Tổng quan").click()
    page.wait_for_selector("[role=alert] .state-title", timeout=15000)
    ok("ED-03-AC6 lỗi vẽ màn -> 'Có lỗi xảy ra' trong khung (còn sidebar + topbar)",
       page.get_by_role("heading", name="Có lỗi xảy ra").is_visible() and page.locator("#rail-left .nav a").count() > 5
       and page.locator("header.topbar").is_visible())
    ok("ED-03-AC6 màn lỗi có nút 'Thử lại' và 'Về Tổng quan'", page.get_by_role("button", name="Thử lại").is_visible()
       and page.get_by_role("link", name="Về Tổng quan").is_visible())
    ok("ED-03-AC6 màn lỗi không in chi tiết kỹ thuật ra màn", "SECRET-NAME" not in page.locator("#main").inner_text()
       and "qa-induced" not in page.locator("#main").inner_text())
    page.screenshot(path=f"{SHOTS}/error-1440.png")
    # menu vẫn đi tiếp được khi một màn lỗi
    page.evaluate("() => { window.__qaBreak = false }")
    page.get_by_role("button", name="Thử lại").click()
    page.wait_for_function("() => !document.querySelector('#main [role=alert] .state-title')")
    settle(page)
    ok("ED-03-AC6 'Thử lại' khi hết lỗi: màn Tổng quan vẽ lại bình thường", page.locator("header.topbar h1").inner_text() == "Tổng quan"
       and "Có lỗi xảy ra" not in page.locator("#main").inner_text())
    # thử lại khi vẫn còn lỗi: không vòng lặp chết, vẫn đi tiếp bằng menu
    page.evaluate("() => { window.__qaBreak = true }")
    page.locator("#rail-left .nav a", has_text="Kiểm kê").click()
    page.wait_for_url("**/stocktake/")
    page.evaluate("() => { window.__qaBreak = false }")
    settle(page)
    ok("ED-03-AC6 sang màn khác bằng menu khi màn trước đang lỗi: vẽ bình thường", "Có lỗi xảy ra" not in page.locator("#main").inner_text())
    leak = [c for c in console_all if "SECRET-NAME" in c]
    ok("Bất biến 9: nội dung lỗi (giả lập có tên) không bị đẩy ra console bởi khung", not leak, leak[:2])
    ctx.close()
    # giao1 gặp lỗi: nút 'Về Tổng quan'
    ctx, page = new_page(browser, "giao1")
    page.goto(BASE + "/my-deliveries/")
    settle(page)
    ctx.close()

    # ===================== Mất mạng =====================
    ctx, page = new_page(browser, "loc")
    page.goto(BASE + "/orders/")
    settle(page)
    page.wait_for_function("() => document.querySelectorAll('#main table tbody tr, #main li').length > 2")
    ok("ED-03-AC4 có mạng: không có banner", page.locator(".offline-banner").count() == 0)
    ctx.set_offline(True)
    expect(page.locator(".offline-banner")).to_be_visible()
    txt = page.locator(".offline-banner").inner_text()
    ok("ED-03-AC4 mất mạng: banner 'Mất kết nối. Đang thử lại…'", "Mất kết nối. Đang thử lại…" in txt, txt)
    ok("ED-03-AC4 banner có role=alert", page.locator(".offline-banner").get_attribute("role") == "alert")
    ok("ED-03-AC4 banner nằm dưới topbar, trên nội dung (không che menu)",
       page.locator(".offline-banner").bounding_box()["y"] >= page.locator("header.topbar").bounding_box()["y"] + page.locator("header.topbar").bounding_box()["height"] - 1)
    ok("ED-03-AC4 banner có nút 'Thử lại'", page.locator(".offline-banner").get_by_role("button", name="Thử lại").count() == 1)
    ok("ED-03-AC4 banner ghi 'Dữ liệu lúc dd/mm/yyyy hh:mm'", re.search(r"Dữ liệu lúc \d{2}/\d{2}/\d{4} \d{2}:\d{2}", txt) is not None, txt)
    dim = page.evaluate("() => { const n = document.querySelector('#main .is-stale'); return n ? getComputedStyle(n).opacity : null }")
    ok("ED-03-AC4 dữ liệu cũ mờ đi khi mất mạng", dim is not None and float(dim) < 1, dim)
    page.screenshot(path=f"{SHOTS}/offline-1440.png")
    # vẫn đi menu được (không bị khoá)
    ok("ED-03-AC4 mất mạng: menu vẫn dùng được (sidebar còn nhấn được)", page.locator("#rail-left .nav a").first.is_enabled())
    ctx.set_offline(False)
    expect(page.locator(".offline-banner")).to_have_count(0)
    ok("ED-03-AC4 có mạng lại: banner tự tắt", True)
    ctx.close()

    # ===================== Hồi quy: tab của /orders/ + định dạng ngày/tiền trên màn thật =====================
    ctx, page = new_page(browser, "loc")
    page.goto(BASE + "/orders/")
    settle(page)
    tabs = page.locator("nav.orders-tabs a")
    names = [t.strip() for t in tabs.all_inner_texts()]
    ok("Hồi quy ED-01 (dev-notes #7): trên 1440px /orders/ thấy 3 tab Đơn hàng / Hàng chờ thanh toán / Phiếu hoàn chờ chuyển",
       any("Hàng chờ thanh toán" in n for n in names) and any("Phiếu hoàn" in n for n in names) and all(tabs.nth(i).is_visible() for i in range(tabs.count())), names)
    page.locator("nav.orders-tabs a", has_text="Hàng chờ thanh toán").click()
    page.wait_for_url("**/orders/payments/")
    page.wait_for_function("() => document.querySelector('#main') && document.querySelector('#main').innerText.length > 20")
    ok("Hồi quy: bấm tab 'Hàng chờ thanh toán' mở màn thanh toán (không trắng, không lỗi)", "Có lỗi xảy ra" not in page.locator("#main").inner_text() and page.locator("#main").inner_text().strip() != "")
    page.locator("nav.orders-tabs a", has_text="Phiếu hoàn").click()
    page.wait_for_url("**/orders/refunds/")
    page.wait_for_function("() => document.querySelector('#main') && document.querySelector('#main').innerText.length > 20")
    ok("Hồi quy: bấm tab 'Phiếu hoàn chờ chuyển' mở màn phiếu hoàn", "Có lỗi xảy ra" not in page.locator("#main").inner_text())
    page.screenshot(path=f"{SHOTS}/orders-tabs-desktop-1440.png")
    bad_fmt = []
    for r in ["/overview/", "/orders/", "/orders/payments/", "/orders/refunds/", "/deliveries/", "/purchasing/", "/inventory/", "/stocktake/", "/catalog/", "/reports/", "/staff/", "/audit-logs/", "/content/"]:
        page.goto(BASE + r)
        settle(page)
        txt = page.locator("#main").inner_text()
        for pat, why in ((r"\d{4}-\d{2}-\d{2}T\d{2}:", "ISO timestamp"), (r"\b\d{1,2}:\d{2}\s?(AM|PM)\b", "giờ 12h"), (r"\d{1,2}/\d{1,2}/\d{4}, \d{1,2}:\d{2}:\d{2}", "định dạng en-US"),
                         (r"\d\s?₫", "ký hiệu ₫ thay vì đ"), (r"\b(null|undefined|NaN|\[object Object\])\b", "giá trị rỗng lộ ra")):
            m = re.search(pat, txt)
            if m:
                bad_fmt.append((r, why, txt[max(0, m.start() - 25):m.end() + 10].replace("\n", " ")))
    ok("§1.5/1.6 định dạng: 13 màn thật không lộ ISO/₫/12h/null/NaN", not bad_fmt, bad_fmt[:6])
    ctx.close()

    # ===================== Cuộn ngang, đủ vai và màn =====================
    for width, height in ((1280, 800), (1440, 900)):
        for user, routes in (("loc", ["/overview/", "/orders/", "/orders/payments/", "/orders/refunds/", "/deliveries/", "/purchasing/", "/inventory/",
                                      "/stocktake/", "/catalog/", "/reports/", "/content/", "/staff/", "/audit-logs/", "/ai/settings/", "/account/"]),
                             ("giao1", ["/my-deliveries/"])):
            ctx, page = new_page(browser, user, width, height)
            bad = []
            for r in routes:
                page.goto(BASE + r)
                settle(page)
                page.wait_for_timeout(400) if False else None
                w = page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth, document.querySelector('#main').scrollWidth, document.querySelector('#main').clientWidth]")
                if w[0] > w[1] or w[2] > w[3] + 1:
                    bad.append((r, w))
            ok(f"G-bố cục {width}px [{user}] {len(routes)} màn: không có thanh cuộn ngang", not bad, bad)
            if width == 1280 and user == "loc":
                # thu gọn rồi kiểm lại
                page.evaluate("() => localStorage.setItem('cave_ui_sidebar','collapsed')")
                bad2 = []
                for r in routes:
                    page.goto(BASE + r)
                    settle(page)
                    w = page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
                    if w[0] > w[1]:
                        bad2.append((r, w))
                ok(f"G-bố cục {width}px thu gọn sidebar: không cuộn ngang", not bad2, bad2)
            ctx.close()

    # 360: drawer và menu đáy, không cuộn ngang
    for user, routes in (("loc", ["/overview/", "/orders/", "/deliveries/", "/inventory/", "/staff/", "/account/"]), ("kho1", ["/overview/", "/inventory/"]),
                         ("giao1", ["/my-deliveries/"])):
        ctx, page = new_page(browser, user, 360, 740, device_scale_factor=2, is_mobile=True, has_touch=True)
        bad = []
        for r in routes:
            page.goto(BASE + r)
            settle(page)
            w = page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
            if w[0] > w[1]:
                bad.append((r, w))
        ok(f"T4 360px [{user}]: không cuộn ngang ở {len(routes)} màn", not bad, bad)
        if user != "giao1":
            ok(f"T4 360px [{user}]: có menu đáy và nút mở ngăn kéo", page.locator(".bottom-nav").is_visible() and page.get_by_role("button", name="Mở menu").is_visible())
            page.get_by_role("button", name="Mở menu").click()
            expect(page.locator("#rail-left.open")).to_be_visible()
            ok(f"T4 360px [{user}]: ngăn kéo hiện đủ mục menu", len([x for x in page.locator("#rail-left .nav a").all() if x.is_visible()]) == len(nav_labels(page)))
            ok(f"T4 360px [{user}]: không có nút thu gọn trong ngăn kéo", not page.get_by_test_id("sidebar-toggle").is_visible())
            if user == "loc":
                page.screenshot(path=f"{SHOTS}/drawer-360.png")
            page.keyboard.press("Escape")
        else:
            ok("T4 360px [giao1]: chỉ có 1 mục thì không có menu đáy", page.locator(".bottom-nav").count() == 0 or not page.locator(".bottom-nav").is_visible())
        ctx.close()
    # 768 và 1024 (thông tin thêm, ngoài phạm vi duyệt)
    for width in (768, 1024):
        ctx, page = new_page(browser, "loc", width, 800)
        bad = []
        for r in ["/overview/", "/orders/", "/inventory/"]:
            page.goto(BASE + r)
            settle(page)
            w = page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
            if w[0] > w[1]:
                bad.append((r, w))
        ok(f"(thêm) {width}px: không cuộn ngang ở 3 màn", not bad, bad)
        ctx.close()

    browser.close()

rel = relevant_errors(errors)
ok("Không lỗi console (trừ font/401/offline cố ý)", not [e for e in rel if "SECRET-NAME" not in e and "qa-induced" not in e], rel[:5])
sys.exit(summary())
