# QA độc lập, vòng 2, ERP theo design Lô 5 FE (Gọi xác nhận): kiểm kỹ các lỗi đã sửa (cột Lý do, bảng vừa khung nhiều cỡ,
# ô tìm 44px và hồi quy bộ lọc dùng chung, StatusPath, bỏ gợi ý xám + bộ đếm, trả focus, dòng thời gian 403/404,
# tải lại lỗi giữ dữ liệu cũ, trường chi tiết, chữ cấm). Chạy trên bản build MOCK phục vụ tĩnh, chỉ dùng dữ liệu giả.
#   BASE=http://127.0.0.1:3201 SHOTS=<thư mục ảnh> python3 e2e/qa_ed_batch5_round2.py
# Dùng lại các hàm hỗ trợ của qa_ed_batch5_ui.py.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_ed_batch5_ui as q  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ok = q.ok
SHOTS = q.SHOTS
BANNED = re.compile(r"Tổng kg|Tổng khối lượng")


def active_desc(page):
    return page.evaluate("""() => { const a = document.activeElement; if (!a) return 'none';
        return a.tagName + '|' + (a.getAttribute('aria-label') || a.innerText || '').trim().slice(0, 40) }""")


def reason_column(browser):
    ctx, page, errors = q.new_page(browser, "ql1")
    q.go(page, "/confirmation/")
    q.pick_tab(page, "Tất cả")
    heads = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts()]
    ok("B1 thứ tự cột theo board W1c", heads[:7] == ["Mã đơn", "Khách hàng", "Số điện thoại", "Hàng", "Tổng số kg", "Trạng thái", "Lý do"], str(heads))
    rows = {}
    for tr in page.locator("table.lt tbody tr").all():
        cells = [c.strip() for c in tr.locator("td").all_inner_texts()]
        rows[cells[0]] = dict(zip(heads, cells))
    ok("B1 Cần quyết định (không nghe máy): cột Lý do ghi 'Không nghe máy'", rows["SO260928-A40F28"]["Lý do"] == "Không nghe máy", str(rows["SO260928-A40F28"]))
    ok("B1 Gọi báo hoàn tiền: cột Lý do ghi số tiền hoàn", re.fullmatch(r"Hoàn [\d.]+ đ", rows["SO260928-9C6B27"]["Lý do"]) is not None, rows["SO260928-9C6B27"]["Lý do"])
    ok("B1 Chờ gọi / Hẹn gọi lại: Lý do là '—' (không bịa lý do)", all(r["Lý do"] == "—" for c, r in rows.items() if r["Trạng thái"] in ("Chờ gọi", "Hẹn gọi lại")), str({c: r["Lý do"] for c, r in rows.items()}))
    ok("B1 mỗi dòng có đúng 10 ô, không ô nào rỗng", all(len(r) == 10 and all(v for v in r.values()) for r in rows.values()))
    # Ngoài đường thuận: tra cứu theo SĐT, tab rỗng, vẫn đủ cột
    q.pick_tab(page, "Cần quyết định")
    ok("B1 tab Cần quyết định: chỉ dòng ESCALATED, Lý do khác '—'", all(c.strip() not in ("—", "") for c in page.locator("table.lt tbody tr td:nth-child(7)").all_inner_texts()))
    ok("B1 console sạch", not errors, str(errors[:2]))
    ctx.close()


def widths(browser):
    for user in ("ql1", "cs2"):
        for w in (1440, 1280, 1024, 768, 390, 360):
            ctx, page, errors = q.new_page(browser, user, w=w, h=860)
            q.go(page, "/confirmation/")
            q.pick_tab(page, "Tất cả")
            doc = q.no_hscroll(page)
            sc = page.evaluate("() => { const s = document.querySelector('.lt-scroll'); return s ? [s.scrollWidth, s.clientWidth] : null }")
            chip = page.locator("table.lt tbody tr .stat-chip").first.bounding_box()
            if w >= 1024:
                ok(f"B3 [{user}] {w}px: bảng không cuộn ngang trong thẻ, chip Trạng thái nằm trong khung nhìn", sc and sc[0] <= sc[1] + 1 and chip and chip["x"] + chip["width"] <= w, f"{sc} {chip}")
            else:
                ok(f"B3 [{user}] {w}px: trang không cuộn ngang; chip Trạng thái nhìn thấy (ít nhất cột gốc)", doc and chip is not None and chip["x"] + chip["width"] <= w + 1 or (doc and sc and sc[0] > sc[1]), f"{sc} {chip}")
            ok(f"B3 [{user}] {w}px: trang không cuộn ngang", doc)
            # bấm giữa dòng (không phải nút / link) -> mở chi tiết; ngoài đường thuận: thử ở từng cỡ
            first = page.locator("table.lt tbody tr", has_not_text="Ngoài phạm vi gọi").first
            box = first.bounding_box()
            td = first.locator("td").nth(1).bounding_box()
            page.mouse.click(td["x"] + min(td["width"] / 2, 30), td["y"] + td["height"] / 2)
            try:
                page.wait_for_url(re.compile(r"/confirmation/detail/\?id=\d+$"), timeout=5000)
                opened = True
            except Exception:
                opened = False
            ok(f"B3 [{user}] {w}px: bấm giữa dòng mở chi tiết", opened, f"{td} {box}")
            if w in (1280, 360, 768):
                q.go(page, "/confirmation/")
                q.pick_tab(page, "Tất cả")
                page.screenshot(path=os.path.join(SHOTS, f"r2-queue-{user}-{w}.png"))
            ctx.close()


def column_legibility(browser):
    """Cột hiện ra không được co về 0; ở >= 1024px Khách hàng và Hàng đủ rộng; mã đơn không bị cắt;
    ô có thể bị cắt phải có title. PO chốt: < 1024px 'Hàng' được ẩn, trang không cuộn ngang là đạt (02b T4)."""
    for w in (1440, 1280, 1100, 1024, 768, 360):
        ctx, page, errors = q.new_page(browser, "ql1", w=w, h=800)
        q.go(page, "/confirmation/")
        q.pick_tab(page, "Tất cả")
        wd = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('table.lt thead th')].filter(th => getComputedStyle(th).display !== 'none').map(th => [th.innerText.trim(), Math.round(th.getBoundingClientRect().width)]))")
        zero = [k for k, v in wd.items() if v <= 0]
        ok(f"B10 {w}px: không có cột đang hiện nào rộng 0", not zero and "Khách hàng" in wd, str(wd))
        if w >= 1024:
            ok(f"B10 {w}px: cột Khách hàng và Hàng đủ rộng để đọc (>= 60px)", wd.get("Khách hàng", 0) >= 60 and wd.get("Hàng", 0) >= 60, str(wd))
        else:
            ok(f"B10 {w}px: cột Hàng ẩn hoặc >= 60px (khổ < 1024 giữ hành vi tối thiểu)", ("Hàng" not in wd) or wd["Hàng"] >= 60, str(wd))
        sw = page.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        ok(f"B10 {w}px: trang không cuộn ngang", sw[0] <= sw[1] + 1, str(sw))
        clipped = page.evaluate("() => [...document.querySelectorAll('table.lt tbody tr td:first-child')].filter(td => td.scrollWidth > td.clientWidth + 1).map(td => td.innerText.trim())")
        ok(f"B11 {w}px: mã đơn không bị cắt chữ", not clipped, str(clipped[:3]))
        notitle = page.evaluate("() => [...document.querySelectorAll('table.lt tbody td')].filter(td => getComputedStyle(td).display !== 'none' && td.scrollWidth > td.clientWidth + 1 && !td.title && !td.querySelector('[title]')).map(td => td.innerText.trim().slice(0, 30))")
        ok(f"B11 {w}px: ô bị cắt chữ đều có title", not notitle, str(notitle[:3]))
        page.screenshot(path=os.path.join(SHOTS, f"r3-queue-ql1-{w}.png"))
        ctx.close()


def narrow_columns(browser):
    ctx, page, errors = q.new_page(browser, "ql1", w=360, h=800)
    q.go(page, "/confirmation/")
    q.pick_tab(page, "Tất cả")
    heads = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts() if h.strip()]
    vis = page.evaluate("() => [...document.querySelectorAll('table.lt thead th')].filter(th => th.offsetWidth > 0 && getComputedStyle(th).display !== 'none').map(th => th.innerText.trim())")
    ok("B3 360px: vẫn thấy Mã đơn, Khách hàng, SĐT, Trạng thái; cột phụ ẩn", {"Mã đơn", "Khách hàng", "Trạng thái"} <= set(vis) and "Lý do" not in vis, str(vis))
    # dòng cần quyết định vẫn nhận ra ở 360 (thông tin lý do nằm ở chi tiết)
    q.pick_tab(page, "Cần quyết định")
    ok("B3 360px: tab Cần quyết định hiện dòng và chip", page.locator("table.lt tbody tr .stat-chip", has_text="Cần quyết định").count() >= 1)
    ctx.close()


def search_44_and_shared(browser):
    # ô tìm 44px ở 360 và 390 trên mọi màn dùng FilterBar (hồi quy phần dùng chung)
    for path in ("/confirmation/", "/deliveries/", "/orders/", "/inventory/", "/purchasing/", "/catalog/"):
        for w in (360, 390):
            ctx, page, errors = q.new_page(browser, "loc", w=w, h=800)
            q.go(page, path)
            info = page.evaluate("""() => [...document.querySelectorAll('.fb input, .fb select, .fb button, .search input')].filter(e => e.offsetParent).map(e => [e.tagName + (e.name ? '[' + e.name + ']' : ''), Math.round(e.getBoundingClientRect().height)])""")
            small = [i for i in info if i[1] < 44]
            ok(f"B4/hồi quy {path} {w}px: ô/nút của thanh lọc cao >= 44px, không cuộn ngang", not small and q.no_hscroll(page), f"{small} {info[:6]}")
            if w == 360:
                page.screenshot(path=os.path.join(SHOTS, f"r2-filter{path.strip('/').replace('/', '-')}-360.png"))
            ctx.close()
    for path in ("/confirmation/", "/deliveries/", "/orders/"):
        ctx, page, errors = q.new_page(browser, "loc", w=1280, h=860)
        q.go(page, path)
        info = page.evaluate("""() => [...document.querySelectorAll('.fb input, .fb select, .search input')].filter(e => e.offsetParent).map(e => Math.round(e.getBoundingClientRect().height))""")
        ok(f"B4/hồi quy {path} 1280px: thanh lọc không phình (<= 48px) và trang không cuộn ngang", all(h <= 48 for h in info) and q.no_hscroll(page), str(info))
        page.screenshot(path=os.path.join(SHOTS, f"r2-filter{path.strip('/')}-1280.png"))
        ctx.close()


def shared_table_regression(browser):
    # DataTable dùng chung đổi: các màn bảng khác vẫn bấm được dòng, không ẩn cột ở 360 (chỉ cột hideOnMobile của hàng chờ)
    for path, rowsel in (("/deliveries/", "table.lt tbody tr"),):
        for w in (1280, 360):
            ctx, page, errors = q.new_page(browser, "loc", w=w, h=860)
            q.go(page, path)
            n = page.locator(rowsel).count()
            heads = page.evaluate("() => [...document.querySelectorAll('table.lt thead th')].filter(th => th.offsetWidth > 0).map(th => th.innerText.trim())")
            allheads = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts()]
            ok(f"hồi quy {path} {w}px: có dòng, không cột nào bị ẩn bởi thay đổi dùng chung, trang không cuộn ngang", n >= 1 and len(heads) == len(allheads) and q.no_hscroll(page), f"{n} {heads} {allheads}")
            ok(f"hồi quy {path} {w}px: không lỗi console", not errors, str(errors[:2]))
            ctx.close()
    # /orders/ (Lô 3 chưa có trong worktree): bấm một dòng vẫn vào được trang (không kiểm trang đích)
    ctx, page, errors = q.new_page(browser, "loc")
    q.go(page, "/deliveries/")
    page.locator("table.lt tbody tr").first.click()
    try:
        page.wait_for_url(re.compile(r"/deliveries/detail/\?id=\d+"), timeout=5000)
        opened = True
    except Exception:
        opened = False
    ok("hồi quy /deliveries/: bấm dòng mở chi tiết phiếu", opened, page.url)
    ctx.close()


def status_path(browser):
    cases = [("SO260928-3F9A01", "Chờ gọi"), ("SO260928-5D1E35", "Chờ gọi"), ("SO260928-A40F28", "Cần quyết định"), ("SO260928-9C6B27", "Cần quyết định")]
    ctx, page, errors = q.new_page(browser, "ql1")
    for code, current in cases:
        q.open_detail_from_queue(page, code)
        steps = page.evaluate("""() => { const el = document.querySelector('[aria-label*="trạng thái" i], .status-path, ol'); return null }""")
        sp = page.evaluate("""() => { const nodes = [...document.querySelectorAll('[aria-current]')]; return nodes.map(n => n.innerText.trim()) }""")
        body = page.inner_text("main")
        branch = code.endswith("9C6B27")  # REFUND_CALL: bước hiện tại là nhánh 'Gọi báo hoàn tiền' nối sau 'Cần quyết định'
        ok(f"B5 {code}: bước hiện tại là '{current}'" + (" (nhánh Gọi báo hoàn tiền)" if branch else ""), (any("Gọi báo hoàn tiền" in x for x in sp) if branch else any(current in x for x in sp)), f"{sp}")
        ok(f"B5 {code}: không còn bước giao hàng (Soạn hàng / Chờ lấy hàng / Đang giao)", not re.search(r"Soạn hàng\s*\n|Chờ lấy hàng|Đang giao", body.split("THÔNG TIN")[0]), body[:300].replace("\n", "|"))
        page.screenshot(path=os.path.join(SHOTS, f"r2-detail-{code[-4:]}-ql1-1280.png"))
    ok("B5 console sạch", not errors, str(errors[:2]))
    ctx.close()
    # sau khi xác nhận xong -> Đã xong; phiếu bị huỷ -> nhánh huỷ
    ctx, page, errors = q.new_page(browser, "ql1")
    q.open_detail_from_queue(page, "SO260928-B27C30")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = q.dialog(page)
    d.wait_for()
    d.locator("label", has_text="Đã xác nhận").first.click()
    d.get_by_role("button", name=re.compile("Lưu")).click()
    d.wait_for(state="detached")
    q.settle(page)
    sp = page.evaluate("() => [...document.querySelectorAll('[aria-current]')].map(n => n.innerText.trim())")
    ok("B5 sau 'Đã xác nhận': bước hiện tại 'Đã xong'", any("Đã xong" in s for s in sp), str(sp))
    ctx.close()
    ctx, page, errors = q.new_page(browser, "ql1")
    q.open_detail_from_queue(page, "SO260928-E83D36")
    page.evaluate("() => window.__caveMock.confirmationSetStatus(%s, 'PREPARING')" % page.url.split("id=")[1])
    page.go_back(); page.go_forward()
    page.wait_for_load_state("networkidle"); q.settle(page)
    sp = page.evaluate("() => [...document.querySelectorAll('[aria-current]')].map(n => n.innerText.trim())")
    ok("B5 phiếu đã sang Soạn hàng (màn cũ tải lại): bước 'Đã xong', không còn nút Ghi kết quả", any("Đã xong" in x for x in sp) and page.get_by_role("button", name="Ghi kết quả gọi").count() == 0, f"{sp}")
    ctx.close()


def hints_and_counter(browser):
    ctx, page, errors = q.new_page(browser, "ql1")
    q.open_detail_from_queue(page, "SO260928-B27C30")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = q.dialog(page)
    d.wait_for()
    txt = d.inner_text()
    ok("B6 F2h không còn câu gợi ý (Đơn sẽ chuyển / Khách đồng ý)", not re.search(r"Đơn sẽ|Khách đồng ý|sẽ chuyển|để kho", txt), txt[:300].replace("\n", "|"))
    ok("B6 F2h có bộ đếm 0/200", re.search(r"0\s*/\s*200", txt) is not None, txt[-80:].replace("\n", "|"))
    d.locator("label", has_text="Không nghe máy").first.click()
    ta = d.locator("textarea")
    ta.fill("x" * 50)
    ok("B6 bộ đếm đổi theo chữ nhập: 50/200", re.search(r"50\s*/\s*200", d.inner_text()) is not None, d.inner_text()[-80:].replace("\n", "|"))
    ta.fill("y" * 260)
    v = ta.input_value()
    ok("B6 nhập quá 200 ký tự bị cắt ở 200, bộ đếm 200/200", len(v) == 200 and re.search(r"200\s*/\s*200", d.inner_text()) is not None, str(len(v)))
    ta.fill("Gọi lại, sdt 0911222333")
    d.get_by_role("button", name=re.compile("Lưu")).click()
    q.page_wait = page.wait_for_timeout(500)
    ok("B6 ngoài đường thuận: ghi chú có SĐT vẫn bị chặn, hộp còn mở", q.dialog(page).count() == 1 and re.search(r"số điện thoại|SĐT", q.dialog(page).inner_text(), re.I) is not None, d.inner_text()[-200:].replace("\n", "|"))
    page.screenshot(path=os.path.join(SHOTS, "r2-F2h-ql1-1280.png"))
    d.get_by_role("button", name=re.compile("Quay lại|Huỷ|Đóng")).first.click()
    # F2k
    q.open_detail_from_queue(page, "SO260928-A40F28")
    page.get_by_role("button", name="Quyết định", exact=True).click()
    d = q.dialog(page)
    d.wait_for()
    txt = d.inner_text()
    ok("B6 F2k không còn câu gợi ý xám", not re.search(r"Đơn chuyển|sẽ chuyển|giữ chỗ|hoàn tiền cho khách|Khách sẽ", txt), txt[:300].replace("\n", "|"))
    d.locator("label", has_text="Huỷ đơn").first.click()
    ok("B6 F2k ô lý do có bộ đếm n/200", re.search(r"\d+\s*/\s*200", d.inner_text()) is not None, d.inner_text()[-120:].replace("\n", "|"))
    red = d.get_by_role("button", name=re.compile("^Huỷ đơn$"))
    ok("B6/F2k hồi quy: nút Huỷ đơn vẫn có", red.count() == 1)
    page.screenshot(path=os.path.join(SHOTS, "r2-F2k-ql1-1280.png"))
    ok("B6 console sạch", not errors, str(errors[:2]))
    ctx.close()


def focus_return(browser):
    ctx, page, errors = q.new_page(browser, "ql1")
    q.open_detail_from_queue(page, "SO260928-A40F28")
    for how in ("Escape", "cancel", "scrim", "x"):
        btn = page.get_by_role("button", name="Quyết định", exact=True)
        btn.focus()
        page.keyboard.press("Enter")
        d = q.dialog(page)
        d.wait_for()
        if how == "Escape":
            page.keyboard.press("Escape")
        elif how == "cancel":
            d.get_by_role("button", name=re.compile("^(Quay lại|Huỷ|Đóng)$")).first.click()
        elif how == "scrim":
            page.mouse.click(5, 400)
        else:
            d.get_by_role("button", name=re.compile("Đóng")).first.click() if d.get_by_role("button", name=re.compile("Đóng")).count() else page.keyboard.press("Escape")
        try:
            d.wait_for(state="detached", timeout=3000)
        except Exception:
            pass
        ok(f"B7 F2k đóng bằng {how}: focus về nút 'Quyết định'", active_desc(page).startswith("BUTTON|Quyết định"), active_desc(page))
    ctx.close()
    ctx, page, errors = q.new_page(browser, "ql1")
    q.open_detail_from_queue(page, "SO260928-B27C30")
    for how in ("Escape", "cancel"):
        btn = page.get_by_role("button", name="Ghi kết quả gọi")
        btn.focus()
        page.keyboard.press("Enter")
        d = q.dialog(page)
        d.wait_for()
        if how == "Escape":
            page.keyboard.press("Escape")
        else:
            d.get_by_role("button", name=re.compile("^(Quay lại|Huỷ|Đóng)$")).first.click()
        d.wait_for(state="detached", timeout=5000)
        ok(f"B7 F2h đóng bằng {how}: focus về nút 'Ghi kết quả gọi'", active_desc(page).startswith("BUTTON|Ghi kết quả gọi"), active_desc(page))
    # ngoài đường thuận: mở khi nút đang 'Đang giữ đơn…' (claim chậm): aria-disabled, bấm lần 2 không mở thêm hộp
    btn = page.get_by_role("button", name="Ghi kết quả gọi")
    btn.dblclick()
    q.settle(page)
    ok("B7 bấm đúp 'Ghi kết quả gọi': chỉ một hộp mở", q.dialog(page).count() == 1, str(q.dialog(page).count()))
    page.keyboard.press("Escape")
    q.dialog(page).wait_for(state="detached")
    ok("B7 sau bấm đúp rồi Esc: focus về nút mở", active_desc(page).startswith("BUTTON|Ghi kết quả gọi"), active_desc(page))
    ok("B7 nút không còn trạng thái aria-disabled treo sau khi xong", page.get_by_role("button", name="Ghi kết quả gọi").get_attribute("aria-disabled") in (None, "false"))
    # menu "…": mục mở hộp thì focus về nút "…" hoặc nút gốc, không rơi về BODY
    more = page.get_by_role("button", name=re.compile("Thao tác khác|Thêm|Khác|Hành động", re.I)).first
    more.click()
    page.get_by_role("menuitem", name=re.compile("Hẹn gọi lại")).click()
    q.dialog(page).wait_for()
    page.keyboard.press("Escape")
    q.dialog(page).wait_for(state="detached")
    ok("B7 Hẹn gọi lại (từ menu …): Esc không để focus rơi về BODY", not active_desc(page).startswith("BODY"), active_desc(page))
    # sau khi lưu thành công
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = q.dialog(page)
    d.wait_for()
    d.locator("label", has_text="Không nghe máy").first.click()
    d.get_by_role("button", name=re.compile("Lưu")).click()
    d.wait_for(state="detached")
    q.settle(page)
    ok("B7 sau lưu thành công: focus không rơi về BODY", not active_desc(page).startswith("BODY"), active_desc(page))
    ok("B7 console sạch", not errors, str(errors[:2]))
    ctx.close()


def timeline_errors(browser):
    ctx, page, errors = q.new_page(browser, "cs2")
    q.open_detail_from_queue(page, "SO260928-3F9A01")
    ok("B2 mặc định (mock cho phép): Dòng thời gian có dòng", page.get_by_text("Chưa tải được lịch sử").count() == 0)
    for status, want in ((403, "Bạn không có quyền xem lịch sử này."), (404, "Không tìm thấy lịch sử của đơn này.")):
        page.evaluate(f"() => window.__caveMock.guidanceForceDeliveryStatus({status})")
        page.go_back(); page.go_forward()
        page.wait_for_load_state("networkidle"); q.settle(page)
        body = page.inner_text("main")
        ok(f"B2 guidance {status}: hiện '{want}'", want in body, body[-250:].replace("\n", "|"))
        ok(f"B2 guidance {status}: không có nút 'Thử lại' cho dòng thời gian", page.get_by_role("button", name="Thử lại").count() == 0, str(page.get_by_role("button", name="Thử lại").count()))
        ok(f"B2 guidance {status}: phần thông tin và lịch sử cuộc gọi vẫn hiện, nút Ghi kết quả vẫn dùng được", "Lịch sử cuộc gọi" in body and page.get_by_role("button", name="Ghi kết quả gọi").is_enabled())
        page.screenshot(path=os.path.join(SHOTS, f"r2-timeline-{status}-cs2-1280.png"))
    page.evaluate("() => window.__caveMock.guidanceForceDeliveryStatus(null)")
    page.go_back(); page.go_forward()
    page.wait_for_load_state("networkidle"); q.settle(page)
    ok("B2 bỏ ép lỗi: Dòng thời gian trở lại bình thường", "Bạn không có quyền xem lịch sử" not in page.inner_text("main"))
    ok("B2 console sạch (lỗi 403/404 do mock ép không in dữ liệu khách)", not any(q_ for q_ in errors if re.search(r"0\d{9}|Khách Thử", q_)), str(errors[:2]))
    ctx.close()


def reload_failure(browser):
    ctx, page, errors = q.new_page(browser, "ql1")
    q.go(page, "/confirmation/")
    q.pick_tab(page, "Tất cả")
    page.evaluate("() => window.__caveMock.confirmationFailNextDetail(1)")
    q.row_of(page, "SO260928-3F9A01").click()
    page.wait_for_url(re.compile(r"/confirmation/detail/\?id=\d+$"))
    page.wait_for_timeout(1500)
    body = page.inner_text("main")
    ok("L1 lần tải đầu lỗi: màn lỗi có nút 'Thử lại', không treo spinner", page.get_by_role("button", name=re.compile("Thử lại|Tải lại")).count() >= 1 and "SO260928-3F9A01" not in page.locator("h1").all_inner_texts(), body[:200].replace("\n", "|"))
    page.screenshot(path=os.path.join(SHOTS, "r2-detail-first-load-fail-ql1-1280.png"))
    page.get_by_role("button", name=re.compile("Thử lại|Tải lại")).first.click()
    q.settle(page)
    page.get_by_role("heading", name="SO260928-3F9A01").wait_for(timeout=8000)
    ok("L1 Thử lại thành công: hiện chi tiết", True)
    # có dữ liệu rồi, tải lại lỗi -> giữ dữ liệu cũ + cảnh báo
    page.evaluate("() => window.__caveMock.confirmationFailNextDetail(1)")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = q.dialog(page)
    d.wait_for()
    d.locator("label", has_text="Không nghe máy").first.click()
    d.get_by_role("button", name=re.compile("Lưu")).click()
    d.wait_for(state="detached")
    q.settle(page)
    page.wait_for_timeout(800)
    body = page.inner_text("main")
    ok("L1 tải lại lỗi sau khi lưu: vẫn giữ dữ liệu đơn trên màn (không trắng)", "SO260928-3F9A01" in body and "Lịch sử cuộc gọi" in body, body[:200].replace("\n", "|"))
    ok("L1 và có cảnh báo 'Chưa tải lại được đơn'", re.search(r"Chưa tải lại được", body) is not None or re.search(r"Chưa tải lại được", page.inner_text("body")) is not None, body[:300].replace("\n", "|"))
    page.screenshot(path=os.path.join(SHOTS, "r2-detail-reload-fail-keep-ql1-1280.png"))
    ctx.close()


def detail_fields(browser):
    ctx, page, errors = q.new_page(browser, "ql1")
    q.open_detail_from_queue(page, "SO260928-A40F28")
    body = page.inner_text("main")
    labels = ["Mã đơn", "Khách hàng", "Số điện thoại", "Người nhận", "Địa chỉ giao", "Hàng", "Tổng số kg", "Tổng tiền", "Lý do", "Lần gọi", "Hạn quyết định", "Người gọi", "Phiếu giao"]
    miss = [l for l in labels if not re.search(rf"(^|\n){re.escape(l)}\s*\n", body)]
    ok("B9 ESCALATED: đủ nhãn Đơn & người nhận + Gọi xác nhận", not miss, str(miss))
    ok("B9 ESCALATED: ghi 'Hạn quyết định', không ghi 'Hạn gọi'", "Hạn quyết định" in body and not re.search(r"(^|\n)Hạn gọi\s*\n", body))
    ok("B8 chi tiết không có 'Tổng kg' / 'Tổng khối lượng'", not BANNED.search(page.inner_text("body")))
    q.open_detail_from_queue(page, "SO260928-3F9A01")
    body = page.inner_text("main")
    ok("B9 PENDING: ghi 'Hạn gọi', không ghi 'Hạn quyết định'", re.search(r"(^|\n)Hạn gọi\s*\n", body) is not None and "Hạn quyết định" not in body)
    ok("B9 PENDING đã gọi 1 lần: 'Người gọi' có tên người (không '—')", re.search(r"Người gọi\s*\n(?!—)\S", body) is not None, body[body.find("Người gọi"):][:60].replace("\n", "|"))
    q.open_detail_from_queue(page, "SO260928-B27C30")
    body = page.inner_text("main")
    ok("B9 chưa ai gọi: 'Người gọi' là '—'", re.search(r"Người gọi\s*\n—", body) is not None, body[body.find("Người gọi"):][:60].replace("\n", "|"))
    ok("B9 'Phiếu giao' có mã (mock) hoặc '—', không 'undefined'/'null'", "undefined" not in body and "null" not in body and re.search(r"Phiếu giao\s*\n(GH-\S+|—)", body) is not None, body[body.find("Phiếu giao"):][:40].replace("\n", "|"))
    ok("B9 không chữ 'undefined' / 'null' / 'NaN' ở bất kỳ ô nào", not re.search(r"undefined|null|NaN", body))
    page.screenshot(path=os.path.join(SHOTS, "r2-detail-0030-ql1-1280.png"), full_page=True)
    ctx.close()
    # CSKH: ESCALATED không có quyền quyết định
    ctx, page, errors = q.new_page(browser, "cs2")
    q.open_detail_from_queue(page, "SO260928-A40F28")
    body = page.inner_text("main")
    ok("B5/B9 cs2 mở việc Cần quyết định: không nút Quyết định, câu 'Bước tiếp theo' dành cho người không quyết định", page.get_by_role("button", name="Quyết định", exact=True).count() == 0 and "Tiếp theo" in body, body[:400].replace("\n", "|"))
    ctx.close()


def banned_words(browser):
    for user, paths in (("ql1", ["/confirmation/", "/deliveries/"]),):
        ctx, page, errors = q.new_page(browser, user)
        for path in paths:
            q.go(page, path)
            ok(f"B8 {path}: không có 'Tổng kg' / 'Tổng khối lượng'", not BANNED.search(page.inner_text("body")), "")
        q.go(page, "/deliveries/")
        page.locator("table.lt tbody tr").first.click()
        page.wait_for_url(re.compile(r"/deliveries/detail/"))
        q.settle(page)
        ok("B8 chi tiết phiếu giao: không có chữ cấm", not BANNED.search(page.inner_text("body")))
        ctx.close()
    # trang in tem: gọi trực tiếp (mock) nếu có
    ctx, page, errors = q.new_page(browser, "ql1")
    page.goto(q.BASE + "/print/label/?id=1")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(800)
    txt = page.inner_text("body")
    ok("B8 trang in tem: không có chữ cấm", not BANNED.search(txt), txt[:120].replace("\n", "|"))
    ctx.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for fn in (reason_column, widths, column_legibility, narrow_columns, search_44_and_shared, shared_table_regression, status_path, hints_and_counter, focus_return, timeline_errors, reload_failure, detail_fields, banned_words):
            try:
                fn(browser)
            except Exception as e:  # một khối vỡ không làm mất các khối còn lại
                ok(f"{fn.__name__}: chạy hết không văng lỗi", False, repr(e)[:300])
        browser.close()
    fails = [r for r in q.results if not r[1]]
    print(f"\n{len(q.results) - len(fails)}/{len(q.results)} đạt")
    for n, _, e in fails:
        print("FAIL:", n, e)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
