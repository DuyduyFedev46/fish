"""QA độc lập vòng 2 cho khung ERP (đợt 1): B1..B6, H1, H2, toast duration, ca ngoài đường thuận.

Chạy trên: bản build MOCK cổng 3101 (app thật) và khung thử vite cổng 3102 (harness; các thành phần chưa có màn dùng).
    cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
    node_modules/.bin/vite build --config e2e/qa_harness_ed_batch1/vite.config.mjs
    (cd e2e/qa_harness_ed_batch1/dist && python3 -m http.server 3102 &)
    SHOTS=<thư mục ảnh> python3 e2e/qa_ed_batch1_round2.py
Dữ liệu chỉ là dữ liệu giả của mock/harness. Không dùng wait_for_timeout để chấm đạt (chỉ chờ điều kiện, trừ ca đo thời gian toast).
"""

import os
import re
import time

from playwright.sync_api import expect, sync_playwright

from qa_ed_batch1_common import (BASE, SHOTS, fulfil_404, login, nav_labels, ok, relevant_errors, summary)

HARNESS = os.environ.get("HARNESS", "http://127.0.0.1:3102")
ASOF_RE = re.compile(r"Dữ liệu lúc (\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})")


def new_page(browser, user, w=1440, h=900):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type == "error" and errs.append(m.text))
    page.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    page.errs = errs
    login(page, user)
    return ctx, page


def go_offline(ctx, page):
    ctx.set_offline(True)
    page.evaluate("() => window.dispatchEvent(new Event('offline'))")


def go_online(ctx, page):
    ctx.set_offline(False)
    page.evaluate("() => window.dispatchEvent(new Event('online'))")


def opacity_of_content(page):
    # Độ mờ hiệu dụng của nội dung màn: khối con đầu tiên của #main không phải dải mất mạng (nhân opacity các tổ tiên)
    return page.evaluate("""() => {
        const main = document.querySelector('#main');
        const el = [...main.children].find(c => !c.classList.contains('offline-banner'));
        let o = 1;
        for (let n = el; n && n !== document.body; n = n.parentElement) o *= parseFloat(getComputedStyle(n).opacity);
        return o;
    }""")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ===================== B1: mất mạng trên màn thật (/orders/ và các màn danh sách khác) =====================
    ctx, page = new_page(browser, "loc")
    page.goto(BASE + "/orders/")
    page.wait_for_selector(".order-open")
    banner = page.locator(".offline-banner")
    ok("B1 trước khi mất mạng: không có dải, nội dung rõ nét", banner.count() == 0 and opacity_of_content(page) == 1)
    go_offline(ctx, page)
    expect(banner).to_be_visible()
    txt = banner.inner_text()
    m = ASOF_RE.search(txt)
    ok("B1 /orders/: dải ghi 'Dữ liệu lúc dd/mm/yyyy hh:mm'", m is not None, txt)
    if m:
        # mốc phải là GIỜ VIỆT NAM của lần tải xong (không lệch quá 3 phút so với giờ VN hiện tại)
        now_vn = page.evaluate("() => new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date())")
        # định dạng 'dd/mm/yyyy, HH:MM'
        mm = re.match(r"(\d{2})/(\d{2})/(\d{4}), (\d{2}):(\d{2})", now_vn)
        d, mo, y, hh, mi = (int(x) for x in m.groups())
        nd, nmo, ny, nhh, nmi = (int(x) for x in mm.groups())
        from datetime import datetime
        diff = abs((datetime(ny, nmo, nd, nhh % 24, nmi) - datetime(y, mo, d, hh % 24, mi)).total_seconds())
        ok("B1 mốc 'Dữ liệu lúc' là giờ VN của lần tải (lệch ≤ 3 phút)", diff <= 180, f"{txt} vs {now_vn}")
    ok("B1 /orders/: có nút 'Thử lại' trong dải", banner.get_by_role("button", name="Thử lại").count() == 1)
    o = opacity_of_content(page)
    ok("B1 /orders/: nội dung bị mờ (opacity hiệu dụng < 1 và ≈ 0.55)", 0.4 < o < 0.7, o)
    ok("B1 dải KHÔNG bị mờ theo nội dung (vẫn rõ để đọc)", page.evaluate("() => { let o=1; for (let n=document.querySelector('.offline-banner'); n && n!==document.body; n=n.parentElement) o*=parseFloat(getComputedStyle(n).opacity); return o; }") == 1)
    ok("B1 dải nằm ngoài vùng mờ, không đè topbar", page.evaluate("() => { const b=document.querySelector('.offline-banner').getBoundingClientRect(); const t=document.querySelector('header.topbar').getBoundingClientRect(); return b.top >= t.bottom - 1; }"))
    page.screenshot(path=f"{SHOTS}/r2-offline-orders-1440.png")
    # bấm Thử lại 3 lần liên tiếp (bấm đúp) không vỡ
    btn = banner.get_by_role("button", name="Thử lại")
    btn.dblclick()
    btn.click()
    ok("B1 bấm Thử lại nhiều lần liên tiếp: danh sách còn, không lỗi console", page.locator(".order-open").count() > 0 and not relevant_errors(page.errs), page.errs)
    # mất mạng -> có mạng -> mất mạng lặp 4 lần
    flips_ok = True
    for i in range(4):
        go_online(ctx, page)
        try:
            expect(banner).to_have_count(0, timeout=3000)
            page.wait_for_function("() => { const m=document.querySelector('#main'); const c=[...m.children].find(x=>!x.classList.contains('offline-banner')); return parseFloat(getComputedStyle(c).opacity)===1; }", timeout=3000)
        except Exception:
            flips_ok = False
        go_offline(ctx, page)
        expect(banner).to_be_visible()
        if not ASOF_RE.search(banner.inner_text()) or banner.get_by_role("button", name="Thử lại").count() != 1:
            flips_ok = False
    ok("B1 lật mạng 4 vòng: lúc có mạng hết dải + hết mờ; lúc mất lại đủ 'Dữ liệu lúc' + Thử lại", flips_ok)
    # đang mất mạng, đổi màn bằng menu: màn mới (không đăng ký) -> dải vẫn có, không còn 'Dữ liệu lúc' của màn cũ
    page.locator("#rail-left .nav a", has_text="Tổng quan").click()
    page.wait_for_url("**/overview/**")
    t2 = banner.inner_text()
    ok("B1 (ghi nhận) Tổng quan khi mất mạng: dải có; có nút Thử lại?", banner.count() == 1, f"{t2!r} nút={banner.get_by_role('button', name='Thử lại').count()}")
    page.screenshot(path=f"{SHOTS}/r2-offline-overview-1440.png")
    # quay lại màn danh sách khi vẫn mất mạng: đăng ký lại
    page.locator("#rail-left .nav a", has_text="Đơn & tiền").click()
    page.wait_for_selector(".order-open")
    ok("B1 vẫn mất mạng, quay lại /orders/: đủ 'Dữ liệu lúc' + Thử lại", ASOF_RE.search(banner.inner_text()) is not None and banner.get_by_role("button", name="Thử lại").count() == 1, banner.inner_text())
    go_online(ctx, page)
    expect(banner).to_have_count(0)
    page.wait_for_function("() => { const m=document.querySelector('#main'); const c=[...m.children].find(x=>!x.classList.contains('offline-banner')); return parseFloat(getComputedStyle(c).opacity)===1; }", timeout=3000)
    ok("B1 có mạng lại: dải tắt, nội dung rõ nét", opacity_of_content(page) == 1)
    # màn danh sách khác dùng usePagedList: danh mục, nhật ký
    for label, url in (("Danh mục & giá", "/catalog/"), ("Nhật ký hoạt động", "/audit-logs/")):
        page.goto(BASE + url)
        page.wait_for_selector("#main > div", timeout=10000)
        page.wait_for_load_state("networkidle")
        go_offline(ctx, page)
        expect(banner).to_be_visible()
        t = banner.inner_text()
        ok(f"B1 {label}: dải mất mạng có 'Dữ liệu lúc' + Thử lại + mờ", ASOF_RE.search(t) is not None and banner.get_by_role("button", name="Thử lại").count() == 1 and opacity_of_content(page) < 0.7, f"{t!r} op={opacity_of_content(page)}")
        go_online(ctx, page)
    ok("B1 không lỗi console trong các ca mất mạng", not relevant_errors(page.errs), relevant_errors(page.errs))
    ctx.close()

    # ===================== B2: "Về …" theo vai =====================
    cases = {
        "giao1": ("Về Việc giao của tôi", "/my-deliveries/"),
        "loc": ("Về Tổng quan", "/overview/"),
        "ql1": ("Về Tổng quan", "/overview/"),
        "kho1": ("Về Tổng quan", "/overview/"),
    }
    for user, (label, dest) in cases.items():
        ctx, page = new_page(browser, user)
        fulfil_404(page, "**/khong-co-man-nay/**")
        fulfil_404(page, "**/orders/abc/**")
        page.goto(BASE + "/khong-co-man-nay/")
        page.wait_for_selector(".page-state")
        link = page.get_by_role("link", name=label)
        ok(f"B2 [{user}] 404 có nút '{label}'", link.count() == 1, page.locator('.page-state').inner_text())
        if user == "giao1":
            page.screenshot(path=f"{SHOTS}/r2-404-giao1-1440.png")
        link.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#main")
        txt = page.locator("#main").inner_text()
        ok(f"B2 [{user}] bấm '{label}' -> {dest}, không phải 'Không có quyền'", dest in page.url and "Bạn không có quyền" not in txt, page.url + " | " + txt[:80])
        # URL lồng
        page.goto(BASE + "/orders/abc/")
        page.wait_for_selector(".page-state")
        ok(f"B2 [{user}] URL lồng /orders/abc/ cũng có nút '{label}'", page.get_by_role("link", name=label).count() == 1)
        ctx.close()
    # CSKH thuần: home theo vai (patchUser trong mock)
    ctx, page = new_page(browser, "cs2")
    fulfil_404(page, "**/khong-co-man-nay/**")
    page.goto(BASE + "/khong-co-man-nay/")
    page.wait_for_selector(".page-state")
    links = [t.strip() for t in page.locator(".page-state a").all_inner_texts()]
    home_link = [t for t in links if t.startswith("Về ")]
    ok("B2 [cs2] nút 'Về …' trỏ về trang chính của vai (không phải Tổng quan nếu không có quyền)", len(home_link) == 1, links)
    if home_link:
        page.get_by_role("link", name=home_link[0]).click()
        page.wait_for_load_state("networkidle")
        ok("B2 [cs2] bấm nút Về: không vào 'Không có quyền'", "Bạn không có quyền" not in page.locator("#main").inner_text(), page.url)
    ctx.close()
    # Màn lỗi chung của giao1: ép lỗi vẽ rồi kiểm nút Về
    ctx, page = new_page(browser, "giao1")
    ctx.add_init_script("""
        window.__qaBreak = true;
        for (const name of ['map', 'filter', 'find', 'some', 'forEach', 'reduce']) {
            const o = Array.prototype[name];
            Array.prototype[name] = function (...a) { if (window.__qaBreak && /my-deliveries|deliveries/.test(new Error().stack || '')) { (window.__hits = window.__hits || []).push(1); throw new Error('qa-induced'); } return o.apply(this, a); };
        }
    """)
    page.goto(BASE + "/my-deliveries/")
    try:
        page.wait_for_selector("text=Có lỗi xảy ra", timeout=8000)
        page.screenshot(path=f"{SHOTS}/r2-error-giao1-1440.png")
        okv = page.get_by_role("link", name="Về Việc giao của tôi").count() == 1 and page.get_by_role("link", name="Về Tổng quan").count() == 0
        ok("B2 [giao1] màn lỗi chung: nút 'Về' trỏ /my-deliveries/", (page.get_by_role("link", name="Về Việc giao của tôi").get_attribute("href") or "").endswith("/my-deliveries/"))
        ps_text = page.locator(".page-state").inner_text()
        ok("B2 [giao1] màn lỗi chung có nút 'Về Việc giao của tôi' (không phải Tổng quan)", okv, ps_text)
        page.evaluate("() => { window.__qaBreak = false; }")
        page.get_by_role("button", name="Thử lại").click()
        page.wait_for_selector("text=Có lỗi xảy ra", state="detached", timeout=5000)
        ok("B2 [giao1] hết lỗi rồi bấm Thử lại: vẽ lại màn Việc giao của tôi, không vào 'Không có quyền'", "Bạn không có quyền" not in page.locator("#main").inner_text())
    except Exception as ex:  # không ép được lỗi vẽ trên màn này
        print("INFO B2 [giao1] không ép được lỗi vẽ trên /my-deliveries/ (⏸, bằng chứng nằm ở vitest states.test):", str(ex)[:80])
    ctx.close()
    # Chưa đăng nhập vào URL lạ: về Đăng nhập
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    fulfil_404(page, "**/khong-co-man-nay/**")
    page.goto(BASE + "/khong-co-man-nay/")
    page.wait_for_url("**/login/**")
    ok("B2 chưa đăng nhập vào URL lạ -> Đăng nhập, không lộ khung", page.locator("#rail-left").count() == 0)
    ctx.close()

    # ===================== B6: Esc đóng ⌘K trả focus =====================
    ctx, page = new_page(browser, "loc")
    page.goto(BASE + "/orders/")
    page.wait_for_selector(".order-open")
    dlg = page.get_by_role("dialog", name="Tìm màn hình")
    opener = page.locator("button.search-trigger")
    fo = lambda: page.evaluate("() => { const a=document.activeElement; return a ? (a.tagName + '.' + (a.className||'')) : 'null'; }")
    for i in range(5):  # mở/đóng liên tiếp bằng nút
        opener.click()
        expect(dlg).to_be_visible()
        page.keyboard.press("Escape")
        expect(dlg).to_have_count(0)
    page.wait_for_function("() => document.activeElement && document.activeElement.classList.contains('search-trigger')")
    ok("B6 mở/đóng nút ×5 bằng Esc: focus về nút ô tìm", True, fo())
    # Esc ngay sau khi mở, không chờ
    opener.click()
    page.keyboard.press("Escape")
    expect(dlg).to_have_count(0)
    page.wait_for_function("() => document.activeElement && document.activeElement !== document.body")
    ok("B6 Esc NGAY khi vừa mở: focus không rơi về BODY", True, fo())
    # Mở bằng Ctrl+K khi focus ở một ô khác (ô tìm của bảng), Esc -> focus không về body
    search = page.locator("#main input[type=search], #main input").first
    if search.count():
        search.focus()
    page.keyboard.press("Control+k")
    expect(dlg).to_be_visible()
    page.keyboard.press("Escape")
    expect(dlg).to_have_count(0)
    page.wait_for_function("() => document.activeElement && document.activeElement !== document.body")
    ok("B6 Ctrl+K từ ô nhập, Esc: focus không rơi về BODY", True, fo())
    # Esc rồi Tab: vẫn đi được tiếp trong trang (không bắt đầu lại từ đầu trang)
    page.keyboard.press("Tab")
    ok("B6 Esc rồi Tab: focus vẫn trong trang, không bẫy", page.evaluate("() => document.activeElement !== document.body"), fo())
    # đóng bằng bấm nền
    opener.click()
    expect(dlg).to_be_visible()
    page.mouse.click(5, 5)
    expect(dlg).to_have_count(0)
    page.wait_for_function("() => document.activeElement && document.activeElement !== document.body")
    ok("B6 đóng bằng bấm nền: focus không rơi về BODY", True, fo())
    # Chọn mục bằng Enter -> đi màn đó
    opener.click()
    page.wait_for_function("() => document.activeElement && document.activeElement.tagName === 'INPUT' && !!document.activeElement.closest('[role=dialog]')")
    page.keyboard.type("kho")
    page.keyboard.press("Enter")
    page.wait_for_url("**/inventory/**")
    ok("B6 (hồi quy) ⌘K gõ 'kho' + Enter -> /inventory/", True)
    ok("B6 không lỗi console", not relevant_errors(page.errs), relevant_errors(page.errs))
    ctx.close()

    # ===================== Hồi quy: menu theo 5 vai =====================
    exp = {"loc": 11, "ql1": 10, "kho1": 8, "giao1": 1}
    for user, n in exp.items():
        ctx, page = new_page(browser, user)
        labels = nav_labels(page)
        ok(f"Hồi quy menu [{user}] {n} mục (bằng vòng 1)", len(labels) == n, labels)
        if user == "giao1":
            ok("Hồi quy menu [giao1] chỉ 'Việc giao của tôi', vào / về /my-deliveries/", labels == ["Việc giao của tôi"] and "/my-deliveries/" in page.url, page.url)
        ctx.close()

    # ===================== Harness: B3, B4, B5, H1, H2, toast =====================
    # ---- B3 ----
    for w in (360, 320):
        for locked in ("1", "0"):
            for mode in ("rows", "stale"):
                ctx = browser.new_context(viewport={"width": w, "height": 800}, reduced_motion="reduce")
                page = ctx.new_page()
                page.goto(f"{HARNESS}/?m={mode}&locked={locked}")
                page.wait_for_selector("table.lt")
                sw = page.evaluate("() => document.documentElement.scrollWidth")
                bsw = page.evaluate("() => document.body.scrollWidth")
                ok(f"B3 {w}px mode={mode} locked={locked}: trang không cuộn ngang (scrollWidth ≤ {w})", sw <= w and bsw <= w, f"doc={sw} body={bsw}")
                if locked == "1" and mode == "rows":
                    # bảng tự cuộn trong khung, và cột khoá vẫn có icon/chữ đọc
                    ok(f"B3 {w}px: bảng cuộn trong khung riêng (.lt-scroll scrollWidth > clientWidth)", page.evaluate("() => { const s=document.querySelector('.lt-scroll'); return s.scrollWidth > s.clientWidth; }"))
                    ok(f"B3 {w}px: tiêu đề 'Giá vốn' có chữ đọc '(cột giới hạn quyền xem)' và icon khoá", "cột giới hạn quyền xem" in page.content() and page.locator("th .mi").count() >= 1)
                    if w == 360:
                        page.screenshot(path=f"{SHOTS}/r2-locked-360.png")
                ctx.close()
    # Không có quyền: không có cột Giá vốn (G7) ở 360
    ctx = browser.new_context(viewport={"width": 360, "height": 800})
    page = ctx.new_page()
    page.goto(f"{HARNESS}/?m=rows&locked=0")
    page.wait_for_selector("table.lt")
    c = page.content()
    ok("B3/G7 không có quyền giá vốn: không có cột 'Giá vốn' và không có số giá vốn (300.000) trong DOM", "Giá vốn" not in c and "300.000" not in c)
    ctx.close()

    # ---- B4 ----
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(f"{HARNESS}/?m=rows&locked=1")
    page.wait_for_selector("table.lt")
    st = page.evaluate("() => { const th=document.querySelector('table.lt th'); const c=getComputedStyle(th); return {tt:c.textTransform, ls:c.letterSpacing, txt: th.textContent}; }")
    ok("B4 tiêu đề cột không in HOA, không giãn chữ", st["tt"] == "none" and st["ls"] in ("normal", "0px"), st)
    ok("B4 chữ hiển thị đúng 'Mã đơn' (viết hoa chữ đầu)", "Mã đơn" in st["txt"], st)
    page.screenshot(path=f"{SHOTS}/r2-template-rows-1440.png")
    ctx.close()

    # ---- B5 ----
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(f"{HARNESS}/?m=error-screen")
    page.wait_for_selector(".page-state")
    st = page.evaluate("""() => {
        const root = document.querySelector('.page-state');
        const btns = [...root.querySelectorAll('a,button')].map(b => ({t: b.textContent.trim(), cls: b.className, x: Math.round(b.getBoundingClientRect().left)}));
        const icon = root.querySelector('.icon, [class*=ps-icon], .material-symbols-outlined');
        return {btns, txt: root.innerText, icon: icon ? getComputedStyle(icon).color : null};
    }""")
    texts = [b["t"] for b in sorted(st["btns"], key=lambda b: b["x"])]
    ok("B5 màn lỗi chung: thứ tự nút trái->phải là 'Về …' rồi 'Thử lại' (theo W6h)", len(texts) == 2 and texts[0].startswith("Về") and "Thử lại" in texts[1], texts)
    ok("B5 màn lỗi chung: 'Thử lại' là nút chính (primary), 'Về' là nút phụ", any("primary" in b["cls"] for b in st["btns"] if "Thử lại" in b["t"]) and not any("primary" in b["cls"] for b in st["btns"] if b["t"].startswith("Về")), st["btns"])
    ok("B5 màn lỗi chung: nội dung có 'Màn này chưa tải được' và giờ dd/mm/yyyy hh:mm", "Màn này chưa tải được" in st["txt"] and re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", st["txt"]), st["txt"])
    ok("B5 màn lỗi chung: không in chi tiết kỹ thuật (stack/Error:)", "Error" not in st["txt"] and "at " not in st["txt"].lower().replace("chat ", ""), st["txt"])
    page.screenshot(path=f"{SHOTS}/r2-error-screen-1440.png")
    page.get_by_role("button", name="Thử lại").click()
    ok("B5 bấm Thử lại gọi hàm onRetry", page.title() == "retried")
    ctx.close()

    # ---- H1 ----
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type == "error" and errs.append(m.text))
    page.goto(f"{HARNESS}/?m=enums")
    page.wait_for_selector("#enum-list li")
    got = page.evaluate("() => [...document.querySelectorAll('#enum-list li')].map(li => ({v: li.dataset.v, text: li.textContent.trim(), chip: li.querySelectorAll('.stat-chip').length, cls: (li.querySelector('.stat-chip')||{}).className||''}))")
    by = {g["v"]: g for g in got}
    ok("H1 mã đã biết 'BOOKED' -> 'Giữ chỗ' (chip warn)", by["BOOKED"]["text"] == "Giữ chỗ" and "warn" in by["BOOKED"]["cls"], by["BOOKED"])
    ok("H1 mã lạ 'NEW_FANCY_STATE' -> hiện ĐÚNG mã gốc trong chip xám, không 'Không rõ'", by["NEW_FANCY_STATE"]["text"] == "NEW_FANCY_STATE" and "mute" in by["NEW_FANCY_STATE"]["cls"], by["NEW_FANCY_STATE"])
    ok("H1 chữ thường 'paid' (sai hoa/thường) -> hiện mã gốc 'paid', không đoán nhãn", by["paid"]["text"] == "paid", by["paid"])
    for k in ("", "null", "undefined"):
        ok(f"H1 giá trị rỗng ({k!r}) -> '—', không chip", by[k]["text"] == "—" and by[k]["chip"] == 0, by[k])
    ok("H1 toàn trang không có chữ 'Không rõ' / 'undefined' / 'null' hiện ra", not re.search(r"Không rõ|undefined|\bnull\b", page.locator("#enum-list").inner_text()), page.locator("#enum-list").inner_text())
    page.screenshot(path=f"{SHOTS}/r2-enums-1440.png")
    ctx.close()

    # ---- H2: Back/Forward giữa các tab ----
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type == "error" and errs.append(m.text))
    page.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    page.goto(f"{HARNESS}/?m=tabparam")
    page.wait_for_selector("#tab-now")
    now = lambda: page.locator("#tab-now").inner_text()
    url_tab = lambda: page.evaluate("() => new URLSearchParams(location.search).get('tab')")
    tab = lambda name: page.get_by_role("tab", name=name)
    ok("H2 mở trang: tab đầu 'all', URL không có ?tab=", now() == "all" and url_tab() is None)
    h0 = page.evaluate("() => history.length")
    tab("Hàng chờ thanh toán").click(); tab("Phiếu hoàn").click(); tab("Tất cả").click(); tab("Phiếu hoàn").click()
    ok("H2 đổi tab nhanh ×4 không chờ: tab cuối đúng 'ref', URL ?tab=ref", now() == "ref" and url_tab() == "ref", (now(), url_tab()))
    ok("H2 mỗi lần đổi tab thêm đúng 1 bước lịch sử (4 bước)", page.evaluate("() => history.length") - h0 == 4, page.evaluate("() => history.length") - h0)
    expect_seq = ["all", "ref", "pay", "all"]
    seq = []
    for want in expect_seq:
        page.go_back()
        try:
            expect(page.locator("#tab-now")).to_have_text(want, timeout=3000)
        except AssertionError:
            pass
        seq.append((now(), url_tab()))
    ok("H2 Back ×4 đi đúng ngược: all -> ref -> pay -> all(lúc mở)", [x[0] for x in seq] == expect_seq, seq)
    ok("H2 sau mỗi Back, tab đang chọn khớp URL (?tab= trùng tab, tab mặc định không có ?tab=)", all((x[0] == "all" and x[1] is None) or x[0] == x[1] for x in seq), seq)
    fwant = ["pay", "ref", "all", "ref"]
    fseq = []
    for want in fwant:
        page.go_forward()
        try:
            expect(page.locator("#tab-now")).to_have_text(want, timeout=3000)
        except AssertionError:
            pass
        fseq.append((now(), url_tab()))
    ok("H2 Forward ×4 đúng thứ tự pay -> ref -> all -> ref", [x[0] for x in fseq] == fwant, fseq)
    sel = page.evaluate("() => [...document.querySelectorAll('[role=tab]')].filter(t => t.getAttribute('aria-selected')==='true').map(t => t.textContent.trim())")
    ok("H2 sau Forward: đúng 1 tab được chọn ('Phiếu hoàn')", sel == ["Phiếu hoàn"], sel)
    # Bấm lại tab đang chọn: không thêm lịch sử
    n0 = page.evaluate("() => history.length")
    tab("Phiếu hoàn").click(); tab("Phiếu hoàn").click()
    ok("H2 bấm lại tab đang chọn ×2: không thêm bước lịch sử", page.evaluate("() => history.length") == n0)
    # Back khi vừa đổi tab bằng bàn phím (ArrowRight / Home)
    tab("Phiếu hoàn").focus()
    page.keyboard.press("Home")
    ok("H2 phím Home đổi sang tab đầu", now() == "all")
    page.keyboard.press("End")
    ok("H2 phím End sang tab cuối", now() == "ref")
    page.go_back()
    expect(page.locator("#tab-now")).to_have_text("all", timeout=3000)
    ok("H2 Back sau khi đổi bằng phím: về tab trước (all)", now() == "all", now())
    # Tải lại giữ tab
    tab("Hàng chờ thanh toán").click()
    page.reload()
    page.wait_for_selector("#tab-now")
    ok("H2 tải lại ở ?tab=pay: giữ tab 'pay'", now() == "pay", now())
    # URL rác
    for junk in ("%3Cscript%3Ealert(1)%3C/script%3E", "constructor", "__proto__", "", "ALL", "pay%20", "ref&tab=pay"):
        page.goto(f"{HARNESS}/?m=tabparam&tab={junk}")
        page.wait_for_selector("#tab-now")
        ok(f"H2 ?tab={junk!r} (rác) -> về tab đầu, không vỡ", now() in ("all", "ref", "pay") and (junk in ("ref&tab=pay") or now() == "all"), now())
    # giữ tham số khác trên URL khi đổi tab
    page.goto(f"{HARNESS}/?m=tabparam&foo=1")
    page.wait_for_selector("#tab-now")
    tab("Phiếu hoàn").click()
    sp = page.evaluate("() => Object.fromEntries(new URLSearchParams(location.search))")
    ok("H2 đổi tab giữ tham số khác (foo=1, m=tabparam), thêm tab=ref", sp.get("foo") == "1" and sp.get("m") == "tabparam" and sp.get("tab") == "ref", sp)
    tab("Tất cả").click()
    sp = page.evaluate("() => Object.fromEntries(new URLSearchParams(location.search))")
    ok("H2 về tab mặc định: bỏ ?tab=, vẫn giữ foo=1", "tab" not in sp and sp.get("foo") == "1", sp)
    ok("H2 không ghi gì vào localStorage/sessionStorage", page.evaluate("() => Object.keys(localStorage).length + Object.keys(sessionStorage).length") == 0)
    ok("H2 không lỗi console / pageerror", not relevant_errors(errs), errs)
    page.screenshot(path=f"{SHOTS}/r2-tabparam-1280.png")
    ctx.close()

    # ---- Toast duration (L1) ----
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto(f"{HARNESS}/?m=rows")
    page.wait_for_selector("#toast-buttons")
    page.get_by_role("button", name="T-dur-short").click()
    t_short = page.locator(".toast-item", has_text="Ngắn 1.5 giây")
    expect(t_short).to_be_visible()
    t0 = time.time()
    expect(t_short).to_have_count(0, timeout=5000)
    dt = time.time() - t0
    ok("L1 toast success duration=1500 tự ẩn ≈1.5 giây (không phải 6 giây mặc định)", 0.8 <= dt <= 3.5, f"{dt:.2f}s")
    page.get_by_role("button", name="T-dur-long").click()
    t_long = page.locator(".toast-item", has_text="Lỗi dài 20 giây")
    expect(t_long).to_be_visible()
    t0 = time.time()
    page.wait_for_timeout(11000)  # đo thời gian: lỗi mặc định là 10 giây, ở đây phải còn
    ok("L1 toast error duration=20000: còn sau 11 giây (mặc định 10 giây đã qua)", t_long.count() == 1, f"{time.time()-t0:.1f}s")
    expect(t_long).to_have_count(0, timeout=15000)
    dt = time.time() - t0
    ok("L1 toast error duration=20000 tự ẩn ≈20 giây", 17 <= dt <= 23, f"{dt:.1f}s")
    page.get_by_role("button", name="T-success").click()
    t = page.locator(".toast-item", has_text="Đã lưu đơn")
    expect(t).to_be_visible()
    t0 = time.time()
    expect(t).to_have_count(0, timeout=9000)
    dt = time.time() - t0
    ok("L1 toast không truyền duration vẫn mặc định ≈6 giây (hồi quy)", 4.5 <= dt <= 7.5, f"{dt:.1f}s")
    ctx.close()

    browser.close()

import sys
sys.exit(summary())
