"""QA độc lập đợt 1: mẫu danh sách + trạng thái + toast, chạy THẬT trong trình duyệt bằng khung thử (harness).

Vì chưa màn nào dùng ListPage/DataTable/FilterBar/Tabs/AiBar/Chip/Toast (nối ở đợt 3 trở đi), harness dựng một trang
chỉ để vẽ các thành phần ấy với dữ liệu giả, dùng đúng globals.css/tokens.css của app. Harness: thư mục qa_harness_ed_batch1/
(vite build; xem README ở đó). Chạy:  HARNESS=http://127.0.0.1:3102 python3 e2e/qa_ed_batch1_template.py
Toàn dữ liệu giả (mã SO..., số tiền bịa).
"""

import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

from qa_ed_batch1_common import SHOTS, ok, summary

H = os.environ.get("HARNESS", "http://127.0.0.1:3102")
errors = []


def open_(browser, mode, w=1440, h=900, extra="", offline=False):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", locale="vi-VN", timezone_id="America/New_York")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{H}/?m={mode}{extra}")
    page.wait_for_selector(".lp")
    page.evaluate("() => document.fonts.ready")
    return ctx, page


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ---------- đường thuận: có dòng ----------
    ctx, page = open_(browser, "rows")
    t = page.locator("table.lt")
    heads = t.locator("thead th").all_inner_texts()
    ok("ED-04 bảng đủ cột khai báo (Mã đơn, Trạng thái, Tổng tiền, Tạo lúc)", [x.strip().lower() for x in heads] == ["mã đơn", "trạng thái", "tổng tiền", "tạo lúc"], heads)
    first = t.locator("tbody tr").first
    cells = first.locator("td").all_inner_texts()
    ok("UI-RULES §1.6 tiền có 'đ', dấu chấm nghìn, không số lẻ", cells[2].strip() == "540.000 đ", cells)
    ok("UI-RULES §1.5 ngày giờ dd/mm/yyyy hh:mm theo GMT+7 (03:30Z -> 10:30), dù máy ở múi giờ khác",
       re.fullmatch(r"02/10/2026 10:30", cells[3].strip()) is not None, cells[3])
    body_text = page.locator("table.lt tbody").inner_text()
    ok("Không lộ ISO/₫/'T03:30' ra màn", not re.search(r"\d{4}-\d{2}-\d{2}T|₫|Z\b", body_text), body_text[:200])
    ok("ED-04 chip trạng thái có chữ tiếng Việt (không hiện mã BOOKED/PAID)", "Giữ chỗ" in body_text and "BOOKED" not in body_text and "AUTO_CANCELLED" not in body_text)
    ok("ED-04 AUTO_CANCELLED hiện 'Đã huỷ'", "Đã huỷ" in body_text)
    ok("UI-RULES §4 cột số/tiền căn phải", page.evaluate("() => getComputedStyle(document.querySelector('table.lt tbody tr td:nth-child(3)')).textAlign") in ("right", "end"))
    ok("UI-RULES §4 mã đơn dùng lớp mono (font mono do app nạp; harness không nạp font nên không đo họ chữ)", "mono" in (t.locator("tbody tr td").first.get_attribute("class") or ""))
    ok("ED-04 không có nút 'Làm mới' ở danh sách", page.get_by_text("Làm mới").count() == 0)
    ok("ED-04 nút tạo mới ở góc phải hàng tiêu đề", page.locator(".lp-head").get_by_role("button", name="Tạo đơn").is_visible()
       and page.locator(".lp-actions").bounding_box()["x"] > page.locator(".lp-head h2").bounding_box()["x"] + 300)
    order = page.evaluate("() => [...document.querySelector('.lp').children].map(c => c.className.split(' ')[0])")
    ok("UI-RULES §4 thứ tự khối: tiêu đề · tab · lọc · thanh AI · bảng · chân", order[:6] == ["lp-head", "tabs", "fb", "ai-bar", "lt-card", "lp-foot"], order)
    ok("ED-04 AiBar hiện 'AI · Có 2 đề xuất' và nút Xem", "Có 2 đề xuất" in page.locator(".ai-bar").inner_text() and page.locator(".ai-bar-view").is_visible())
    ok("ED-04 FilterBar: 'Đang hiện 4 / 4 đơn'", "Đang hiện 4 / 4 đơn" in page.locator(".fb-summary").inner_text())
    page.screenshot(path=f"{SHOTS}/template-rows-1440.png")

    # bấm dòng -> đi chi tiết; bấm nút trong dòng thì không
    t.locator("tbody tr").nth(1).locator("td").nth(2).click()
    page.wait_for_function("() => document.title === 'pushed:/orders/2/'")
    ok("ED-04 bấm vào dòng (ô bất kỳ) -> trang chi tiết /orders/2/", True)
    ok("ED-04 ô đầu của dòng là liên kết thật (mở tab mới/bàn phím được)", t.locator("tbody tr").first.locator("td a.lt-link").get_attribute("href") == "/orders/1/")
    ok("ED-04 dòng không có href chỉ ở cột đầu (một liên kết/ dòng, không lồng)", t.locator("tbody tr").first.locator("a").count() == 1)

    # tab bằng bàn phím
    tabs = page.get_by_role("tab")
    tabs.first.focus()
    page.keyboard.press("ArrowRight")
    ok("Tabs: ArrowRight chuyển sang tab 2, aria-selected đúng, roving tabindex",
       tabs.nth(1).get_attribute("aria-selected") == "true" and tabs.nth(1).get_attribute("tabindex") == "0" and tabs.first.get_attribute("tabindex") == "-1")
    page.keyboard.press("End")
    ok("Tabs: End -> tab cuối", tabs.nth(2).get_attribute("aria-selected") == "true")
    page.keyboard.press("ArrowRight")
    ok("Tabs: vòng lại tab đầu", tabs.first.get_attribute("aria-selected") == "true")
    ok("Tabs: tab có số đếm 0 không hiện số, >0 hiện", page.locator(".tab-count").count() == 2)
    ok("ED-04 'Hàng chờ thanh toán' và 'Phiếu hoàn' là tab hiện được ở 1440px (không bị display:none)", tabs.nth(1).is_visible() and tabs.nth(2).is_visible())

    # lọc + tìm
    page.get_by_label("Trạng thái").select_option("PAID")
    ok("FilterBar: chọn 'Đã thanh toán' -> còn 1 dòng, tóm tắt cập nhật", t.locator("tbody tr").count() == 1 and "1 / 4" in page.locator(".fb-summary").inner_text())
    page.get_by_label("Trạng thái").select_option("")
    page.get_by_role("searchbox", name="Tìm đơn").fill("Hoa Nguyen 0901234567")
    ok("ED-03-AC2 gõ từ khoá không khớp -> 'Không tìm thấy đơn hàng khớp với “…”' + nút Xoá tìm kiếm",
       page.get_by_text("Không tìm thấy đơn hàng khớp với “Hoa Nguyen 0901234567”").is_visible() and page.get_by_role("button", name="Xoá tìm kiếm").count() >= 1)
    page.screenshot(path=f"{SHOTS}/template-search-empty-1440.png")
    stor = page.evaluate("() => JSON.stringify([localStorage, sessionStorage])")
    ok("G10 từ khoá (giả lập tên + SĐT) không vào URL/localStorage/sessionStorage", "Nguyen" not in stor + page.url and "0901234567" not in stor + page.url + page.evaluate("() => document.title"))
    page.get_by_role("button", name="Xoá tìm kiếm").last.click()
    ok("ED-03-AC2 bấm Xoá tìm kiếm -> bảng hiện lại đầy đủ 4 dòng, ô tìm trống", t.locator("tbody tr").count() == 4 and page.get_by_role("searchbox", name="Tìm đơn").input_value() == "")
    # từ khoá có ký tự HTML
    page.get_by_role("searchbox", name="Tìm đơn").fill('<img src=x onerror="document.title=\'XSS\'">')
    ok("ED-03-AC2 từ khoá chứa HTML được thoát (không chạy mã)", page.title() != "XSS" and page.locator(".state-title img").count() == 0
       and "<img" in page.locator(".state-title").inner_text())
    page.get_by_role("searchbox", name="Tìm đơn").fill("A" * 400)
    ok("ED-03-AC2 từ khoá rất dài không làm vỡ bố cục (không cuộn ngang)", page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))
    page.get_by_role("button", name="Xoá tìm kiếm").first.click()
    ctx.close()

    # ---------- trống / đang tải / lỗi / mờ ----------
    ctx, page = open_(browser, "empty")
    st = page.locator(".lt-state")
    ok("ED-03-AC1 danh sách trống: icon + tiêu đề + 1 câu nói khi nào có dữ liệu",
       st.locator(".state-ic").is_visible() and "Chưa có đơn hàng nào" in st.inner_text() and "Đơn mới sẽ hiện ở đây" in st.inner_text())
    ok("ED-03-AC1 trạng thái trống: header cột và bộ lọc vẫn hiện", page.locator("table.lt thead th").count() == 4 and page.locator(".fb").is_visible())
    page.screenshot(path=f"{SHOTS}/template-empty-1440.png")
    ctx.close()

    ctx, page = open_(browser, "loading")
    ok("ED-03-AC3 đang tải: có khung xương, aria-busy, thông báo cho trình đọc màn hình",
       page.locator("tr.lt-skel").count() >= 4 and page.locator(".lt-card").get_attribute("aria-busy") == "true"
       and "Đang tải dữ liệu" in page.locator(".lt-card [role=status]").inner_text())
    ok("ED-03-AC3 đang tải: tiêu đề cột và bộ lọc vẫn hiện", page.locator("table.lt thead th").count() == 4 and page.locator(".fb").is_visible())
    geo_loading = page.evaluate("() => ['.lp-head','.tabs','.fb','.lt-card thead'].map(s => Math.round(document.querySelector(s).getBoundingClientRect().top))")
    ok("ED-03-AC3 skeleton không có chữ giả/số giả", "đ" not in page.locator("tr.lt-skel").first.inner_text() and page.locator("tr.lt-skel").first.inner_text().strip() == "")
    page.screenshot(path=f"{SHOTS}/template-loading-1440.png")
    ctx.close()
    ctx, page = open_(browser, "rows")
    geo_rows = page.evaluate("() => ['.lp-head','.tabs','.fb','.lt-card thead'].map(s => Math.round(document.querySelector(s).getBoundingClientRect().top))")
    ok("ED-03-AC3 không nhảy bố cục: vị trí tiêu đề/tab/lọc/đầu bảng khi tải = khi có dữ liệu (lệch ≤ 2px)",
       all(abs(a - b) <= 2 for a, b in zip(geo_loading, geo_rows)), (geo_loading, geo_rows))
    ctx.close()

    ctx, page = open_(browser, "error")
    ok("Bảng lỗi: có thông báo, role=alert, nút Thử lại", page.locator(".state-err[role=alert]").is_visible() and page.get_by_role("button", name="Thử lại").is_visible())
    page.get_by_role("button", name="Thử lại").click()
    ok("Bảng lỗi: bấm Thử lại gọi lại hàm tải", page.locator(".toast-item").count() == 1)
    page.screenshot(path=f"{SHOTS}/template-error-1440.png")
    ctx.close()

    ctx, page = open_(browser, "stale")
    op = page.evaluate("() => getComputedStyle(document.querySelector('.lt-card.is-stale')).opacity")
    ok("ED-03-AC4 (bảng) khi stale: dữ liệu mờ (opacity<1)", float(op) < 1, op)
    ctx.close()

    # ---------- cột giá vốn ----------
    ctx, page = open_(browser, "rows", extra="&locked=0")
    ok("G7 người không có quyền: cột 'Giá vốn' và số giá vốn KHÔNG có trong DOM", "Giá vốn" not in page.content() and "300.000" not in page.locator("table.lt").inner_text())
    ctx.close()
    ctx, page = open_(browser, "rows", extra="&locked=1")
    th = page.locator("table.lt thead th", has_text="Giá vốn")
    ok("G7 cột giá vốn có icon khoá + chữ đọc cho trình đọc màn hình", th.locator(".mi, i").count() >= 1 and "cột giới hạn quyền xem" in th.text_content())
    ctx.close()

    # ---------- bố cục ----------
    for w in (1280, 1440):
        ctx, page = open_(browser, "rows", w, 800)
        ok(f"G-bố cục {w}px: danh sách không cuộn ngang trang", page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))
        ctx.close()
    ctx, page = open_(browser, "rows", 360, 740, extra="&locked=0")
    ok("T4 360px (không có cột giá vốn): danh sách không cuộn ngang trang", page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))
    ctx.close()
    ctx, page = open_(browser, "rows", 360, 740, extra="&locked=1")
    ok("T4 360px (CÓ cột giá vốn/khoá): danh sách không cuộn ngang trang (span sr-only absolute thoát khỏi vùng cuộn)", page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"),
       page.evaluate("() => [document.documentElement.scrollWidth, innerWidth]"))
    disp = page.evaluate("() => getComputedStyle(document.querySelector('table.lt tbody tr')).display")
    ok("T4 360px: dòng chuyển dạng thẻ (có nhãn cột data-label) hoặc cuộn trong khung bảng, không vỡ", disp in ("block", "grid", "flex") or page.evaluate("() => getComputedStyle(document.querySelector('.lt-scroll')).overflowX") in ("auto", "scroll"), disp)
    small = page.evaluate("""() => [...document.querySelectorAll('.lp button, .lp a, .lp select, .lp input, [role=tab]')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.height < 44 && r.width < 44) }).map(e => (e.tagName + '.' + (e.className || '') + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height)))""")
    ok("T4 360px: vùng bấm >= 44px ở ít nhất một chiều (tab, nút, ô lọc)", not small, small[:6])
    page.screenshot(path=f"{SHOTS}/template-rows-360.png", full_page=True)
    ctx.close()

    # ---------- Toast ----------
    ctx, page = open_(browser, "rows")
    page.get_by_role("button", name="T-success").click()
    ti = page.locator(".toast-item")
    ok("ED-03-AC7 toast thành công: role=status, có nút đóng", ti.get_attribute("role") == "status" and ti.get_by_role("button", name="Đóng thông báo").is_visible())
    box = page.locator(".toast-stack").bounding_box()
    vp = page.viewport_size
    ok("ED-03-AC7 toast nằm góc DƯỚI PHẢI", box["x"] + box["width"] > vp["width"] - 60 and box["y"] + box["height"] > vp["height"] - 60, (box, vp))
    ok("ED-03-AC7 toast thường KHÔNG có nút Hoàn tác", ti.get_by_role("button", name="Hoàn tác").count() == 0)
    page.get_by_role("button", name="T-warn").click()
    page.get_by_role("button", name="T-error").click()
    page.wait_for_timeout(400)  # chỉ để ảnh chụp đủ nét sau hiệu ứng vào; không dùng để chấm
    page.screenshot(path=f"{SHOTS}/toast-stack-1440.png")
    page.locator(".toast-item .toast-close").nth(2).click()
    page.locator(".toast-item .toast-close").nth(1).click()
    ti.get_by_role("button", name="Đóng thông báo").click()
    ok("ED-03-AC7 bấm đóng -> toast biến mất", page.locator(".toast-item").count() == 0)
    page.get_by_role("button", name="T-error").click()
    ok("ED-03-AC7 toast lỗi: role=alert", page.locator(".toast-item.error").get_attribute("role") == "alert")
    page.screenshot(path=f"{SHOTS}/toast-error-1440.png")
    page.locator(".toast-item .toast-close").click()
    page.get_by_role("button", name="T-warn").click()
    ok("ED-03-AC7 toast cảnh báo có lớp warn", page.locator(".toast-item.warn").count() == 1)
    page.locator(".toast-item .toast-close").click()
    page.get_by_role("button", name="T-undo").click()
    ok("ED-03-AC7 toast có Hoàn tác khi thao tác truyền undo", page.get_by_role("button", name="Hoàn tác").is_visible())
    page.get_by_role("button", name="Hoàn tác").click()
    ok("ED-03-AC7 bấm Hoàn tác -> gọi undo và đóng toast", page.title() == "undone" and page.locator(".toast-item").count() == 0)
    page.get_by_role("button", name="T-many").click()
    ok("ED-03-AC7 bắn 6 toast liên tiếp: chỉ giữ tối đa 4, không tràn khỏi màn", page.locator(".toast-item").count() == 4
       and page.locator(".toast-stack").bounding_box()["y"] >= 0, page.locator(".toast-item").count())
    ok("ED-03-AC7 vùng toast aria-live=polite", page.locator(".toast-stack").get_attribute("aria-live") == "polite")
    ok("ED-03-AC7 toast không chứa SĐT/địa chỉ (chuỗi thử)", not re.search(r"0\d{9}", page.locator(".toast-stack").inner_text()))
    ctx.close()

    # tự ẩn + dừng khi rê chuột (dùng đồng hồ giả)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.clock.install()
    page.goto(f"{H}/?m=rows")
    page.wait_for_selector(".lp")
    page.get_by_role("button", name="T-success").click()
    page.clock.run_for(3000)
    ok("ED-03-AC7 toast còn sau 3 giây", page.locator(".toast-item").count() == 1)
    page.locator(".toast-item").hover()
    page.clock.run_for(20000)
    ok("ED-03-AC7 rê chuột vào: dừng đếm, không tự ẩn dù quá 20 giây", page.locator(".toast-item").count() == 1)
    page.mouse.move(5, 5)
    page.clock.run_for(7000)
    ok("ED-03-AC7 bỏ chuột ra: tự ẩn sau thời gian của loại success (≈6 giây)", page.locator(".toast-item").count() == 0)
    page.get_by_role("button", name="T-error").click()
    page.clock.run_for(7000)
    ok("ED-03-AC7 toast lỗi ở lại lâu hơn (còn sau 7 giây)", page.locator(".toast-item").count() == 1)
    page.clock.run_for(4000)
    ok("ED-03-AC7 toast lỗi tự ẩn sau ≈10 giây", page.locator(".toast-item").count() == 0)
    ctx.close()

    # ---------- màn trạng thái ----------
    ctx, page = open_.__wrapped__(browser) if False else (None, None)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(f"{H}/?m=error-screen")
    page.wait_for_selector(".page-state")
    btns = page.locator(".page-state-actions > *").all_inner_texts()
    ok("ED-03-AC6 màn lỗi chung: tiêu đề 'Có lỗi xảy ra', nút Thử lại + Về Tổng quan", "Có lỗi xảy ra" in page.locator(".state-title").inner_text() and any("Thử lại" in b for b in btns) and any("Về Tổng quan" in b for b in btns))
    ok("UI-RULES §6.4 / W6h thứ tự nút: Về Tổng quan trước, Thử lại sau (theo bản thiết kế)", [b.split("\n")[-1].strip() for b in btns][0] == "Về Tổng quan",
       btns)
    page.get_by_role("button", name="Thử lại").click()
    ok("ED-03-AC6 Thử lại gọi hàm reset", page.title() == "retried")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(f"{H}/?m=notfound-screen")
    page.wait_for_selector(".page-state")
    ok("ED-03-AC6 màn 404: 'Không tìm thấy trang này' + nút Về Tổng quan -> /overview/",
       "Không tìm thấy trang này" in page.locator(".state-title").inner_text() and page.get_by_role("link", name="Về Tổng quan").get_attribute("href") == "/overview/")
    ctx.close()

    # ---------- mất mạng (thành phần dùng riêng) ----------
    ctx, page = open_(browser, "rows")
    ctx.set_offline(True)
    page.wait_for_selector(".offline-banner")
    ok("ED-03-AC4 (thành phần) mất mạng khi KHÔNG truyền onRetry/asOf: dải chỉ có chữ, không Thử lại/không 'Dữ liệu lúc'",
       page.locator(".offline-banner button").count() == 0 and "Dữ liệu lúc" not in page.locator(".offline-banner").inner_text())
    ctx.close()

    browser.close()

rel = [e for e in errors if "Failed to load resource" not in e and "fonts.g" not in e]
ok("Không lỗi console / pageerror trong harness", not rel, rel[:5])
sys.exit(summary())
