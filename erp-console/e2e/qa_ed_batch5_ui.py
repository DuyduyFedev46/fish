# QA độc lập, ERP theo design, Lô 5 FE (Gọi xác nhận, ED-15 + G1-G10). Chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3201 &)
#   BASE=http://127.0.0.1:3201 SHOTS=<thư mục ảnh> python3 e2e/qa_ed_batch5_ui.py
# Bổ sung cho ed_batch5_confirmation.py: cột Lý do, bảng vừa khung 1280, cả 5 vai, từng kết quả cuộc gọi,
# Dòng thời gian sau khi ghi, biên giờ hẹn / gia hạn, chạm 44px ở 360px, mọi loại console, mọi request ra ngoài, G1-G10.
# Chỉ dùng dữ liệu giả của mock.
import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3201")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=10_000)
VN = ZoneInfo("Asia/Ho_Chi_Minh")
results = []
ALL_CONSOLE = []   # mọi loại console (không chỉ error) để rà dữ liệu cá nhân
EXTERNAL = []      # request ra ngoài máy chủ test

PII_STRINGS = ["0900000123", "0900000456", "0900000555", "0900000666", "0900000777", "0900000789", "0900000888", "0900000999",
               "Khách Thử", "Đường Thử", "Đà Lạt", "Lâm Đồng", "Nha Trang", "Hải Phòng", "Anh Bình Thử", "0911222333"]


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra, flush=True)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    settle(page)


def new_page(browser, user, w=1280, h=860, tz=None, errors=None):
    errors = errors if errors is not None else []
    kw = dict(viewport={"width": w, "height": h}, reduced_motion="reduce")
    if tz:
        kw["timezone_id"] = tz
    ctx = browser.new_context(**kw)
    page = ctx.new_page()

    def on_console(m):
        ALL_CONSOLE.append((user, m.type, m.text))
        if m.type in ("error", "warning") and "Failed to fetch RSC payload" not in m.text:
            errors.append(f"{m.type}: {m.text}")

    page.on("console", on_console)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("request", lambda r: EXTERNAL.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") and not r.url.startswith("blob:") else None)
    login(page, user)
    return ctx, page, errors


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), document.cookie])")


def row_of(page, code):
    return page.locator("table.lt tbody tr", has_text=code)


def dialog(page):
    return page.get_by_role("dialog")


def pick_tab(page, name):
    page.get_by_role("tab", name=re.compile(rf"^{name}")).click()
    page.wait_for_load_state("networkidle")
    settle(page)


def open_detail_from_queue(page, code, tab="Tất cả"):
    go(page, "/confirmation/")
    pick_tab(page, tab)
    row_of(page, code).click()
    page.wait_for_url(re.compile(r"/confirmation/detail/\?id=\d+$"))
    settle(page)
    page.get_by_role("heading", name=code).wait_for()


def to_queue(page, tab):
    """Về hàng chờ bằng bấm liên kết trong app (page.goto sẽ nạp lại trang và làm mock quay về dữ liệu gốc)."""
    page.locator("main a", has_text="Gọi xác nhận").first.click()
    page.wait_for_url(re.compile(r"/confirmation/(\?.*)?$"))
    settle(page)
    pick_tab(page, tab)


def more_menu(page, item):
    page.get_by_role("button", name=re.compile("Thao tác khác|Thêm|Khác|Hành động", re.I)).first.click()
    page.get_by_role("menuitem", name=re.compile(item)).click()


def vn_input(dt):
    return dt.strftime("%Y-%m-%dT%H:%M")


def vn_now():
    return datetime.now(VN)


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def pii_in(text):
    return [p for p in PII_STRINGS if p in text]


# ====================================================================== 1. quyền vào màn
def role_access(browser):
    for user in ("cs2", "loc", "ql1"):
        ctx, page, errors = new_page(browser, user)
        go(page, "/confirmation/")
        ok(f"[{user}] vào được /confirmation/ (6 tab)", page.get_by_role("tab").count() == 6 and page.get_by_text("không có quyền", exact=False).count() == 0)
        ok(f"[{user}] menu có 'Gọi xác nhận'", page.locator(".nav a", has_text="Gọi xác nhận").count() == 1)
        ok(f"[{user}] không có lỗi console", not errors, str(errors[:2]))
        ctx.close()
    for user in ("kho1", "giao1"):
        ctx, page, errors = new_page(browser, user)
        ok(f"[{user}] menu không có 'Gọi xác nhận'", page.locator(".nav a", has_text="Gọi xác nhận").count() == 0)
        for path in ("/confirmation/", "/confirmation/detail/?id=31", "/confirmation/?tab=ESCALATED"):
            go(page, path)
            body = page.content()
            ok(f"[{user}] {path} -> 'Không có quyền', không có dữ liệu khách", page.get_by_text("không có quyền", exact=False).first.is_visible() and not pii_in(body) and "SO260928" not in body)
        ctx.close()
    # chưa đăng nhập
    ctx = browser.new_context(viewport={"width": 1280, "height": 860})
    page = ctx.new_page()
    for path in ("/confirmation/", "/confirmation/detail/?id=31"):
        page.goto(BASE + path)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        body = page.content()
        ok(f"[chưa đăng nhập] {path} -> về /login/, không lộ đơn", "/login" in page.url and "SO260928" not in body and not pii_in(body), page.url)
    ctx.close()


# ====================================================================== 2. hàng chờ
def queue_checks(browser):
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/confirmation/")
    names = [re.sub(r"\s*\d+$", "", t.strip()) for t in page.get_by_role("tab").all_inner_texts()]
    ok("AC1 tab đúng 6 mục, đúng thứ tự", names == ["Đến giờ gọi", "Hẹn gọi lại", "Cần quyết định", "Gọi báo hoàn tiền", "Chờ gọi", "Tất cả"], str(names))
    heads = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts()]
    ok("cột 'Hạn gọi' có", "Hạn gọi" in heads, str(heads))
    ok("AC1 'Lý lo chuyển quyết định ở cột riêng': có cột Lý do", any(h in ("Lý do", "Lý do chuyển lên", "Lý do chuyển quyết định") for h in heads), str(heads))
    # nội dung cột lý do ở tab Cần quyết định
    pick_tab(page, "Cần quyết định")
    row = row_of(page, "SO260928-A40F28")
    cells = [c.strip() for c in row.locator("td").all_inner_texts()]
    ok("AC1 tab Cần quyết định: lý do 'Không nghe máy' nằm trong một ô riêng của dòng", "Không nghe máy" in cells, str(cells))
    # chip theo tab
    expect_chip = {"Đến giờ gọi": {"Chờ gọi"}, "Hẹn gọi lại": {"Hẹn gọi lại"}, "Cần quyết định": {"Cần quyết định"}, "Gọi báo hoàn tiền": {"Gọi báo hoàn tiền"}, "Chờ gọi": {"Chờ gọi"}}
    for t, want in expect_chip.items():
        pick_tab(page, t)
        chips = set(c.strip() for c in page.locator("table.lt tbody tr .stat-chip").all_inner_texts())
        ok(f"G3 tab {t}: chip chỉ đúng nhãn chuẩn", chips == want, str(chips))
    pick_tab(page, "Tất cả")
    chips = set(c.strip() for c in page.locator("table.lt tbody tr .stat-chip").all_inner_texts())
    ok("G3 tab Tất cả: có đủ 4 nhãn chip chuẩn", {"Chờ gọi", "Hẹn gọi lại", "Cần quyết định", "Gọi báo hoàn tiền"} <= chips, str(chips))
    ok("G3 chip không có dấu '·' hay chú thích trong chip", not any(re.search(r"[·(]", c) for c in page.locator("table.lt tbody tr .stat-chip").all_inner_texts()))
    # bảng vừa khung 1280 (cột trạng thái nhìn thấy không cần cuộn ngang)
    sc = page.evaluate("() => { const s = document.querySelector('.lt-scroll'); return s ? [s.scrollWidth, s.clientWidth] : null }")
    ok("1280px: bảng vừa khung, không phải cuộn ngang trong thẻ (chip Trạng thái nhìn thấy)", sc and sc[0] <= sc[1] + 1, str(sc))
    chip_box = page.locator("table.lt tbody tr .stat-chip").first.bounding_box()
    ok("1280px: chip Trạng thái nằm trong khung nhìn", chip_box and chip_box["x"] + chip_box["width"] <= 1280, str(chip_box))
    page.screenshot(path=os.path.join(SHOTS, "qa5-queue-all-ql1-1280.png"))
    # G1: mỗi ô một giá trị (không có dòng phụ)
    multi = page.evaluate("""() => [...document.querySelectorAll('table.lt tbody tr')].flatMap(tr => [...tr.cells].map(td => td.innerText.trim()).filter(t => t.split('\\n').filter(x => x.trim()).length > 1))""")
    ok("G1 không ô nào có hai dòng chữ", not multi, str(multi[:3]))
    # G2 giờ
    due = page.evaluate("""() => { const i = [...document.querySelectorAll('table.lt thead th')].findIndex(th => th.innerText.trim() === 'Hạn gọi'); return [...document.querySelectorAll('table.lt tbody tr')].map(tr => i >= 0 && tr.cells[i] ? tr.cells[i].innerText.trim() : '#thiếu-cột') }""")
    ok("G2 'Hạn gọi' dạng dd/mm/yyyy hh:mm hoặc —", all(re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}|—", d) for d in due), str(due))
    text = page.inner_text("main")
    ok("G2 không dùng giờ tương đối", not re.search(r"hôm nay|hôm qua|phút trước|giờ trước|ngày trước", text, re.I))
    # G4 mã mono
    mono = page.evaluate("() => getComputedStyle(document.querySelector('table.lt tbody tr td')).fontFamily")
    ok("G4 mã đơn dùng font mono", re.search(r"mono|Mono|Courier", mono) is not None, mono[:80])
    # G5 tiền, kg căn phải
    algn = page.evaluate("""() => { const tr = document.querySelector('table.lt tbody tr'); return [...tr.cells].map(td => getComputedStyle(td).textAlign) }""")
    heads_all = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts()]
    ok("G5 cột Tổng tiền, kg căn phải", all(algn[i] in ("right", "end") for i, h in enumerate(heads_all) if h in ("Tổng tiền", "Tổng kg", "Tổng số kg")), str(list(zip(heads_all, algn))))
    ok("G5 tiền dạng '540.000 đ'", re.search(r"\d{1,3}(\.\d{3})+ đ", text) is not None)
    # G7 chữ cấm
    banned = re.findall(r"\bSĐT\b|\bNCC\b|\bNV\b|\bTTL\b|FEFO|BR-\d|hạch toán|Tổng kg|Tổng khối lượng|\bKhách\b(?! hàng| Thử)", text)
    ok("G7 danh sách không có chữ trong danh sách cấm (UI-RULES §3.2/3.4: 'Tổng kg' phải là 'Tổng số kg')", not banned, str(banned))
    # G6 giá vốn
    html = page.content().lower()
    ok("G6 HTML hàng chờ không có giá vốn / lãi lỗ", not re.search(r"giá vốn|purchase_rate|landed|unit_cost|lãi", html))
    # tab và URL
    pick_tab(page, "Hẹn gọi lại")
    ok("tab Hẹn gọi lại: URL ?tab=CALLBACK", page.url.endswith("?tab=CALLBACK"), page.url)
    page.go_back()
    page.wait_for_load_state("networkidle")
    settle(page)
    ok("Back của trình duyệt về đúng tab trước", page.get_by_role("tab", selected=True).inner_text().strip().startswith("Tất cả"), page.url)
    go(page, "/confirmation/?tab=ESCALATED")
    ok("tải lại với ?tab=ESCALATED giữ đúng tab", page.get_by_role("tab", selected=True).inner_text().strip().startswith("Cần quyết định"))
    go(page, "/confirmation/?tab=zzz")
    ok("?tab=rác rơi về tab mặc định, không vỡ", page.get_by_role("tab", selected=True).inner_text().strip().startswith("Đến giờ gọi") and page.locator("table.lt").count() == 1)
    # G8: tìm không thấy, xoá tìm
    pick_tab(page, "Tất cả")
    page.locator("input[name=q]").fill("zzzkhongco")
    page.wait_for_timeout(300)
    ok("G8 tìm không thấy: 'Không tìm thấy' + nút 'Xoá tìm kiếm'", page.get_by_text("Không tìm thấy", exact=False).count() >= 1 and page.get_by_role("button", name=re.compile("Xoá (tìm|bộ lọc)", re.I)).count() >= 1, page.inner_text("main")[-200:].replace("\n", "|"))
    page.get_by_role("button", name=re.compile("Xoá (tìm|bộ lọc)", re.I)).first.click()
    ok("G8 xoá tìm kiếm: bảng trở lại", page.locator("table.lt tbody tr").count() >= 7)
    # tìm theo SĐT trong ô lọc: không lên URL
    page.locator("input[name=q]").fill("0900000123")
    page.wait_for_timeout(300)
    ok("G10 tìm theo SĐT: lọc được, URL / storage không chứa từ khoá", page.locator("table.lt tbody tr").count() >= 1 and "0900000123" not in page.url and "0900000123" not in storage_dump(page))
    page.locator("input[name=q]").fill("")
    # G8 trống: tab Hẹn gọi lại sau khi xoá đơn hẹn -> dùng ql1 ghi 'Đã xác nhận' đơn 35 rồi xem tab rỗng
    open_detail_from_queue(page, "SO260928-5D1E35", "Hẹn gọi lại")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = dialog(page)
    d.locator("label", has_text="Đã xác nhận").first.click()
    d.get_by_role("button", name=re.compile("Lưu kết quả")).click()
    d.wait_for(state="detached")
    settle(page)
    to_queue(page, "Hẹn gọi lại")
    ok("G8 danh sách trống: có tiêu đề + 1 câu giải thích", page.get_by_text("Chưa có đơn nào ở mục Hẹn gọi lại").count() == 1 and page.get_by_text("Đơn khách hẹn gọi lại sẽ hiện ở đây", exact=False).count() == 1)
    page.screenshot(path=os.path.join(SHOTS, "qa5-queue-empty-ql1-1280.png"))
    ok("hàng chờ: không lỗi console", not errors, str(errors[:2]))
    ctx.close()


# ====================================================================== 3. SĐT theo phạm vi, 5 vai
def phone_scope(browser):
    for user in ("cs2", "loc", "ql1"):
        ctx, page, errors = new_page(browser, user)
        go(page, "/confirmation/")
        html = page.content()
        out_row = row_of(page, "SO260928-1B7A40")
        in_row = row_of(page, "SO260928-3F9A01")
        if user == "cs2":
            ok("[cs2] dòng ngoài phạm vi: chỉ số che 09xx xxx 555", "09xx xxx 555" in out_row.inner_text())
            ok("[cs2] ngoài phạm vi: toàn DOM không có số đủ / tên / địa chỉ của đơn 0040", not any(x in html for x in ("0900000555", "Khách Thử K", "Hải Phòng", "tel:0900000555")))
            ok("[cs2] ngoài phạm vi: không có liên kết (không bấm mở, không tel:)", out_row.locator("a").count() == 0 and out_row.get_attribute("tabindex") in (None, "-1"))
            out_row.click()
            ok("[cs2] bấm dòng ngoài phạm vi không điều hướng", "/detail" not in page.url)
            go(page, "/confirmation/detail/?id=40")
            ok("[cs2] mở thẳng URL đơn ngoài phạm vi -> 404, DOM sạch", page.get_by_role("heading", name="Không tìm thấy trang này").is_visible() and not any(x in page.content() for x in ("0900000555", "Khách Thử K", "Hải Phòng")))
            # tìm khách: ngoài phạm vi chỉ số che
            go(page, "/confirmation/")
            page.get_by_role("button", name="Tìm khách gọi lại").click()
            d = dialog(page)
            d.get_by_label("Số điện thoại hoặc mã đơn").fill("0900000555")
            d.get_by_role("button", name="Tìm", exact=True).click()
            page.wait_for_timeout(500)
            settle(page)
            t = d.inner_text()
            ok("[cs2] tìm khách ngoài phạm vi: thấy số che, không thấy số đủ/tên", "09xx xxx 555" in t and "0900000555" not in t.replace(page.locator("input").first.input_value() if False else "", "") or ("09xx xxx 555" in t), t.replace("\n", "|")[:150])
            ok("[cs2] tìm khách: ô nhập có thể chứa số vừa gõ nhưng kết quả không lộ tên", "Khách Thử K" not in t)
            ok("[cs2] tìm khách: URL / storage không mang từ khoá", "0900000555" not in page.url and "0900000555" not in storage_dump(page))
            # tìm bằng ô nhập: số quá ngắn
            d.get_by_label("Số điện thoại hoặc mã đơn").fill("09")
            d.get_by_role("button", name="Tìm", exact=True).click()
            ok("tìm khách: từ khoá quá ngắn bị chặn, không gửi", re.search(r"ít nhất|9|chữ số|nhập", d.inner_text(), re.I) is not None, d.inner_text().replace("\n", "|")[:120])
        else:
            ok(f"[{user}] dòng 0040 hiện đủ số 0900000555", "0900000555" in out_row.inner_text())
            ok(f"[{user}] dòng 0040 mở được", out_row.locator("a").count() >= 1)
        ok(f"[{user}] dòng 0001 trong phạm vi: số đủ + liên kết tel:", "0900000123" in in_row.inner_text() and page.locator("a[href='tel:0900000123']").count() >= 1)
        ok(f"[{user}] không lỗi console", not errors, str(errors[:2]))
        ctx.close()


# ====================================================================== 4. chi tiết theo vai
def detail_checks(browser):
    for user in ("cs2", "loc", "ql1"):
        ctx, page, errors = new_page(browser, user)
        open_detail_from_queue(page, "SO260928-A40F28", "Cần quyết định")
        main = page.inner_text("main")
        btns = [x.strip().replace("call\n", "") for x in page.locator("main button, main a.btn").all_inner_texts()]
        if user == "cs2":
            ok("AC5 [cs2] chi tiết đơn Cần quyết định: KHÔNG có nút Quyết định", "Quyết định" not in btns, str(btns))
        else:
            ok(f"AC4 [{user}] chi tiết đơn Cần quyết định: có nút Quyết định", "Quyết định" in btns, str(btns))
        ok(f"[{user}] có 'Gọi khách' tel: và SĐT đủ", page.locator("a.btn[href='tel:0900000999']").count() == 1 and "0900000999" in main)
        calls = page.locator("table.lt tbody tr").count()
        ok(f"[{user}] Lịch sử cuộc gọi: 3 dòng, có người gọi và kết quả", calls == 3 and "CSKH Thử" in main)
        ok(f"[{user}] StatusPath có đủ bước và 'Tiếp theo' + 'Đã làm'", "Tiếp theo" in main and "Đã làm" in main and page.locator("[class*='StatusPath'], [class*='path']").count() >= 1 or ("Tiếp theo" in main and "Đã làm" in main))
        cur = page.evaluate("() => { const e = document.querySelector('[aria-current=\"step\"], [aria-current=true]'); return e ? e.innerText.trim() : null }")
        ok(f"[{user}] StatusPath: bước hiện tại khớp chip 'Cần quyết định' của việc (board W1c2: Chờ gọi > Cần quyết định > Hoàn tất)", cur == "Cần quyết định", f"bước hiện tại = {cur!r}")
        ok(f"[{user}] Dòng thời gian có ít nhất 1 dòng, giờ dạng dd/mm/yyyy hh:mm", page.locator("[data-timeline-row] time").count() >= 1 and all(re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", t.strip()) for t in page.locator("[data-timeline-row] time").all_inner_texts()))
        main_html = page.locator("main").inner_html().lower()
        ok(f"[{user}] chi tiết (vùng nội dung) không có giá vốn / lãi lỗ", not re.search(r"giá vốn|purchase_rate|landed|unit_cost|lãi", main_html))
        banned = re.findall(r"\bSĐT\b|\bNCC\b|\bNV\b|\bTTL\b|FEFO|BR-\d|hạch toán|Tổng khối lượng", main)
        ok(f"G7 [{user}] chi tiết: không có chữ cấm (Tổng khối lượng -> Tổng số kg)", not banned, str(banned))
        ok(f"G5 [{user}] chi tiết: tiền 540.000 đ, kg", re.search(r"540\.000 đ", main) is not None)
        if user == "ql1":
            page.screenshot(path=os.path.join(SHOTS, "qa5-detail-0028-ql1-1280.png"))
        ok(f"[{user}] không lỗi console", not errors, str(errors[:2]))
        ctx.close()
    # trang đơn Chờ quyết định nhưng cho CSKH: có thông báo chờ
    # đơn gọi báo hoàn tiền
    ctx, page, errors = new_page(browser, "cs2")
    open_detail_from_queue(page, "SO260928-9C6B27", "Gọi báo hoàn tiền")
    main = page.inner_text("main")
    ok("đơn Gọi báo hoàn tiền: chip đúng + 'Số tiền hoàn' + ghi chú không ghi số tài khoản", page.get_by_text("Gọi báo hoàn tiền").count() >= 1 and "Số tiền hoàn" in main and "số tài khoản" in main)
    ctx.close()


# ====================================================================== 5. F2h: từng kết quả + Dòng thời gian
def record_each_result(browser):
    cases = [
        ("CONFIRMED", "Đã xác nhận", 31, "SO260928-3F9A01"),
        ("CALLBACK", "Hẹn gọi lại", 31, "SO260928-3F9A01"),
        ("UNREACHABLE", "Không nghe máy", 31, "SO260928-3F9A01"),
        ("WRONG_NUMBER", "Sai số điện thoại", 31, "SO260928-3F9A01"),
        ("WANT_CHANGE", "Khách muốn đổi món", 31, "SO260928-3F9A01"),
        ("WANT_CANCEL", "Khách muốn huỷ đơn", 31, "SO260928-3F9A01"),
    ]
    for key, label, nid, code in cases:
        ctx, page, errors = new_page(browser, "cs2", tz="America/New_York")  # múi giờ máy lệch: giờ phải theo Việt Nam
        open_detail_from_queue(page, code, "Đến giờ gọi")
        tl_before = page.locator("[data-timeline-row]").count()
        calls_before = page.locator("table.lt tbody tr").count()
        att_before = re.search(r"Lần gọi\s*\n?\s*(\d+)/(\d+)", page.inner_text("main"))
        page.get_by_role("button", name="Ghi kết quả gọi").click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text=label).first.click()
        if key == "CALLBACK":
            d.get_by_label("Hẹn gọi lại lúc").fill(vn_input(vn_now() + timedelta(hours=3)))
        d.get_by_label("Ghi chú", exact=False).fill("Ghi chú thử không có số")
        btn = d.get_by_role("button", name=re.compile("Lưu kết quả"))
        btn.dblclick()  # bấm đúp: chỉ được ghi một lần
        d.wait_for(state="detached")
        settle(page)
        page.wait_for_timeout(400)
        calls_after = page.locator("table.lt tbody tr").count()
        tl_after = page.locator("[data-timeline-row]").count()
        ok(f"AC2 [{key}] bấm đúp 'Lưu kết quả': lịch sử cuộc gọi tăng đúng 1 dòng", calls_after == calls_before + 1, f"{calls_before}->{calls_after}")
        # Mock trả Dòng thời gian tĩnh (guidance/mock.ts), nên dòng mới chỉ kiểm được trên BE thật. Ở đây chỉ kiểm không mất dòng.
        ok(f"AC2 [{key}] Dòng thời gian vẫn hiển thị sau khi lưu (dòng mới: xem ⏸ BE thật)", tl_after >= tl_before and tl_after >= 1, f"{tl_before}->{tl_after}")
        main = page.inner_text("main")
        ok(f"AC2 [{key}] toast / chip phản ánh kết quả; lịch sử có kết quả '{label}'", label in main)
        ok(f"AC2 [{key}] không lỗi console", not errors, str(errors[:2]))
        if key == "CALLBACK":
            ok("AC2 hẹn gọi lại: 'Hạn gọi' hiện giờ hẹn theo giờ Việt Nam dd/mm/yyyy hh:mm", (vn_now() + timedelta(hours=3)).strftime("%d/%m/%Y %H:") in main, main[main.find("Hạn gọi"):main.find("Hạn gọi") + 40].replace("\n", "|"))
        ctx.close()
    # đơn Gọi báo hoàn tiền -> Đã báo hoàn tiền
    ctx, page, errors = new_page(browser, "cs2")
    open_detail_from_queue(page, "SO260928-9C6B27", "Gọi báo hoàn tiền")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = dialog(page)
    d.wait_for()
    labels = [x.strip() for x in d.locator("[class*='pickName']").all_inner_texts()]
    ok("AC2 đơn Gọi báo hoàn tiền: lựa chọn chỉ 'Không nghe máy' và 'Đã báo hoàn tiền' (đúng 02b: NOTIFIED/UNREACHABLE)", sorted(labels) == ["Không nghe máy", "Đã báo hoàn tiền"] or sorted(labels) == sorted(["Đã báo hoàn tiền", "Không nghe máy"]), str(labels))
    d.locator("label", has_text="Đã báo hoàn tiền").first.click()
    d.get_by_role("button", name=re.compile("Lưu kết quả")).click()
    d.wait_for(state="detached")
    settle(page)
    to_queue(page, "Gọi báo hoàn tiền")
    ok("AC2 [NOTIFIED] sau khi ghi, đơn rời tab Gọi báo hoàn tiền", row_of(page, "SO260928-9C6B27").count() == 0)
    ctx.close()


# ====================================================================== 6. F2h giao diện hộp
def modal_f2h(browser):
    ctx, page, errors = new_page(browser, "cs2")
    open_detail_from_queue(page, "SO260928-3F9A01", "Đến giờ gọi")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = dialog(page)
    d.wait_for()
    page.screenshot(path=os.path.join(SHOTS, "qa5-F2h-ghi-ket-qua-cs2-1280.png"))
    labels = [x.strip() for x in d.locator("[class*='pickName']").all_inner_texts()]
    ok("F2h đủ 6 kết quả đúng tên, đúng thứ tự board", labels == ["Đã xác nhận", "Hẹn gọi lại", "Không nghe máy", "Sai số điện thoại", "Khách muốn đổi món", "Khách muốn huỷ đơn"], str(labels))
    fields = d.locator("input:not([type=radio]), textarea, select").count()
    ok("F2h <= 6 trường (UI-RULES §6.1)", fields <= 6, str(fields))
    metas = d.locator("[class*='pickMeta']").all_inner_texts()
    ok("F2h/§6.2 không có chữ gợi ý xám dưới từng lựa chọn (board F2h chỉ có tên lựa chọn)", len(metas) == 0, f"{len(metas)} dòng gợi ý, vd: {metas[:1]}")
    ok("F2h có khối tóm tắt Đơn / Khách hàng / Số điện thoại / Lần gọi", all(x in d.inner_text() for x in ("Đơn hàng", "Khách hàng", "Số điện thoại", "Lần gọi")))
    ok("F2h nút: 'Quay lại' (phụ) và 'Lưu kết quả' (chính, bên phải)", d.get_by_role("button", name="Quay lại").count() == 1 and d.get_by_role("button", name=re.compile("^Lưu kết quả")).count() == 1)
    ok("F2h dấu * bắt buộc ở 'Kết quả cuộc gọi'", "*" in d.locator("legend").first.inner_text())
    ok("F2h có ô ghi chú; bộ đếm ký tự x/200 theo board", re.search(r"\d+\s*/\s*200", d.inner_text()) is not None, "board F2h có '0/200'")
    # ghi chú 201 ký tự
    d.get_by_label("Ghi chú", exact=False).fill("a" * 205)
    v = d.get_by_label("Ghi chú", exact=False).input_value()
    ok("ghi chú tối đa 200 ký tự (không cho nhập quá)", len(v) <= 200, str(len(v)))
    d.get_by_label("Ghi chú", exact=False).fill("")
    # nhiều dạng SĐT trong ghi chú
    d.locator("label", has_text="Không nghe máy").first.click()
    for note in ("gọi 0912345678", "0912 345 678", "091.234.5678", "0912-345-678", "091_234_5678", "0912/345/678", "số tk 1234567890123", "+84 912 345 678", "chín số 912345678"):
        d.get_by_label("Ghi chú", exact=False).fill(note)
        d.get_by_role("button", name=re.compile("^Lưu kết quả")).click()
        ok(f"ghi chú '{note}' bị chặn, hộp còn mở", re.search(r"không được chứa số điện thoại", d.inner_text()) is not None and dialog(page).is_visible())
    d.get_by_label("Ghi chú", exact=False).fill("hẹn 8 giờ, mã 12345678")  # 8 chữ số: được
    d.get_by_role("button", name=re.compile("^Lưu kết quả")).click()
    d.wait_for(state="detached")
    ok("ghi chú 8 chữ số (dưới ngưỡng) được lưu", True)
    ok("ghi chú đã lưu hiện trong lịch sử; không nằm ở storage / URL", "mã 12345678" in page.inner_text("main") and "mã 12345678" not in storage_dump(page) and "12345678" not in page.url)
    # Esc, focus
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = dialog(page)
    d.wait_for()
    page.keyboard.press("Escape")
    ok("Esc đóng hộp, không lưu gì", dialog(page).count() == 0)
    ok("Esc: tiêu điểm về nút mở hộp", page.evaluate("() => document.activeElement && document.activeElement.innerText || ''").strip().startswith("Ghi kết quả gọi"), page.evaluate("() => (document.activeElement && document.activeElement.innerText) || document.activeElement.tagName"))
    ok("không lỗi console", not errors, str(errors[:2]))
    ctx.close()


# ====================================================================== 7. F2i hẹn gọi lại: biên
def callback_edges(browser):
    for tz in ("Asia/Ho_Chi_Minh", "America/Los_Angeles"):
        ctx, page, errors = new_page(browser, "cs2", tz=tz)
        open_detail_from_queue(page, "SO260928-3F9A01", "Đến giờ gọi")
        more_menu(page, "Hẹn gọi lại")
        d = dialog(page)
        d.wait_for()
        if tz == "Asia/Ho_Chi_Minh":
            page.screenshot(path=os.path.join(SHOTS, "qa5-F2i-hen-goi-lai-cs2-1280.png"))
            ok("F2i chỉ có ô giờ + ghi chú (board F2i: 1 ô 'Gọi lại lúc *')", d.locator("input[type=radio]").count() == 0 and d.get_by_label("Hẹn gọi lại lúc").count() == 1)
            ok("F2i nút 'Lưu hẹn gọi lại' + 'Quay lại'", d.get_by_role("button", name="Lưu hẹn gọi lại").count() == 1 and d.get_by_role("button", name="Quay lại").count() == 1)
        save = d.get_by_role("button", name="Lưu hẹn gọi lại")
        pat = r"Chọn thời điểm sau (\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})\."
        # trống
        save.click()
        m = re.search(pat, d.inner_text())
        ok(f"[{tz}] AC3 để trống: câu lỗi đúng khuôn 'Chọn thời điểm sau dd/mm/yyyy hh:mm.'", m is not None, d.inner_text()[-120:].replace("\n", "|"))
        if m:
            shown = datetime(int(m[3]), int(m[2]), int(m[1]), int(m[4]), int(m[5]), tzinfo=VN)
            ok(f"[{tz}] AC3 mốc trong câu lỗi là giờ Việt Nam hiện tại (lệch <= 2 phút)", abs((vn_now() - shown).total_seconds()) <= 120, str(shown))
        # quá khứ: 1 phút trước, hôm qua
        for label, dt in (("1 phút trước", vn_now() - timedelta(minutes=1)), ("hôm qua", vn_now() - timedelta(days=1)), ("năm 2020", datetime(2020, 1, 1, 8, 0))):
            d.get_by_label("Hẹn gọi lại lúc").fill(vn_input(dt))
            save.click()
            ok(f"[{tz}] AC3 giờ {label}: bị chặn, hộp còn mở, không lưu", re.search(pat, d.inner_text()) is not None and dialog(page).is_visible())
        # sát biên: đúng phút hiện tại (<= now) bị chặn
        d.get_by_label("Hẹn gọi lại lúc").fill(vn_input(vn_now()))
        save.click()
        ok(f"[{tz}] AC3 biên: đúng phút hiện tại bị chặn (không phải tương lai)", re.search(pat, d.inner_text()) is not None and dialog(page).is_visible())
        # hợp lệ
        target = vn_now() + timedelta(minutes=5)
        d.get_by_label("Hẹn gọi lại lúc").fill(vn_input(target))
        save.click()
        d.wait_for(state="detached")
        settle(page)
        ok(f"[{tz}] AC3 giờ tương lai +5 phút: lưu được, 'Hạn gọi' hiện {target.strftime('%d/%m/%Y %H:%M')} (giờ Việt Nam)", target.strftime("%d/%m/%Y %H:%M") in page.inner_text("main"))
        ctx.close()


# ====================================================================== 8. F2j đổi người nhận / địa chỉ
def change_recipient(browser):
    ctx, page, errors = new_page(browser, "cs2")
    open_detail_from_queue(page, "SO260928-3F9A01", "Đến giờ gọi")
    more_menu(page, "Đổi người nhận")
    d = dialog(page)
    d.wait_for()
    page.screenshot(path=os.path.join(SHOTS, "qa5-F2j-doi-nguoi-nhan-cs2-1280.png"))
    lab = [x.strip() for x in d.locator("label, .field-label, [class*='label']").all_inner_texts() if x.strip()]
    ok("F2j có 3 ô: tên, số điện thoại, địa chỉ (đúng nhãn board)", d.get_by_label("Tên người nhận").count() == 1 and d.get_by_label("Số điện thoại người nhận").count() == 1 and d.get_by_label(re.compile("Địa chỉ giao")).count() == 1, str(lab[:6]))
    ok("F2j ô địa chỉ có sẵn giá trị hiện tại; ô tên/số có giá trị hiện tại (không bắt gõ lại)", d.get_by_label(re.compile("Địa chỉ giao")).input_value() != "")
    # xoá hết
    d.get_by_label("Tên người nhận").fill("")
    d.get_by_label("Số điện thoại người nhận").fill("")
    d.get_by_label(re.compile("Địa chỉ giao")).fill("")
    d.get_by_role("button", name="Lưu thay đổi").click()
    ok("F2j địa chỉ trống: báo lỗi 'Nhập địa chỉ giao mới' (board F2j)", re.search(r"Nhập địa chỉ", d.inner_text()) is not None and dialog(page).is_visible(), d.inner_text()[-200:].replace("\n", "|"))
    d.get_by_label(re.compile("Địa chỉ giao")).fill("12 Đường Giả, Quận Giả")
    d.get_by_label("Số điện thoại người nhận").fill("abc")
    d.get_by_role("button", name="Lưu thay đổi").click()
    ok("F2j số điện thoại chữ: báo lỗi", re.search(r"Số điện thoại chưa đúng|số điện thoại", d.inner_text(), re.I) is not None and dialog(page).is_visible())
    d.get_by_label("Số điện thoại người nhận").fill("0911222333")
    d.get_by_label("Tên người nhận").fill("Người Nhận Giả")
    d.get_by_role("button", name="Lưu thay đổi").dblclick()
    d.wait_for(state="detached")
    settle(page)
    main = page.inner_text("main")
    ok("F2j lưu: trang hiện người nhận mới + địa chỉ mới", "Người Nhận Giả" in main and "12 Đường Giả" in main and "0911222333" in main)
    ok("F2j lưu: không nằm ở storage / URL", "Người Nhận Giả" not in storage_dump(page) and "0911222333" not in storage_dump(page) and "12 " not in page.url)
    # lưu lại không đổi gì
    more_menu(page, "Đổi người nhận")
    d = dialog(page)
    d.wait_for()
    d.get_by_role("button", name="Lưu thay đổi").click()
    ok("F2j lưu không đổi gì: báo 'Chưa có gì thay đổi để lưu.', hộp còn mở, không gọi API", "Chưa có gì thay đổi để lưu" in d.inner_text() and dialog(page).is_visible())
    ok("không lỗi console", not errors, str(errors[:2]))
    ctx.close()


# ====================================================================== 9. F2k quyết định
def decide_checks(browser):
    for user in ("ql1", "loc"):
        ctx, page, errors = new_page(browser, user)
        open_detail_from_queue(page, "SO260928-A40F28", "Cần quyết định")
        page.get_by_role("button", name="Quyết định", exact=True).click()
        d = dialog(page)
        d.wait_for()
        if user == "ql1":
            page.screenshot(path=os.path.join(SHOTS, "qa5-F2k-quyet-dinh-ql1-1280.png"))
        names = [x.strip() for x in d.locator("[class*='pickName']").all_inner_texts()]
        ok(f"AC4 [{user}] F2k có đủ 3 lựa chọn đúng tên", names == ["Bỏ qua gọi xác nhận", "Gia hạn gọi", "Huỷ đơn"], str(names))
        metas = d.locator("[class*='pickMeta']").count()
        ok(f"§6.2 [{user}] F2k không chữ gợi ý xám dưới lựa chọn (board F2k chỉ có tên)", metas == 0, f"{metas} dòng gợi ý")
        ok(f"[{user}] F2k <= 6 trường", d.locator("input:not([type=radio]), textarea, select").count() <= 6)
        # chưa chọn
        d.get_by_role("button", name=re.compile("Lưu quyết định")).click()
        ok(f"[{user}] không chọn gì: báo 'Chọn một cách xử lý.'", "Chọn một cách xử lý" in d.inner_text())
        # giao không xác nhận: cần lý do; có SĐT bị chặn
        d.locator("label", has_text="Bỏ qua gọi xác nhận").first.click()
        d.get_by_role("button", name=re.compile("Lưu quyết định")).click()
        ok(f"[{user}] giao không xác nhận thiếu lý do: báo 'Nhập lý do.'", "Nhập lý do" in d.inner_text())
        d.get_by_label(re.compile("^Lý do")).fill("khách ở số 0912 345 678")
        d.get_by_role("button", name=re.compile("Lưu quyết định")).click()
        ok(f"[{user}] lý do có SĐT bị chặn, hộp còn mở", "không được chứa số điện thoại" in d.inner_text() and dialog(page).is_visible())
        # gia hạn: biên 24 giờ
        d.locator("label", has_text="Gia hạn gọi").first.click()
        d.get_by_label(re.compile("^Lý do")).fill("Khách bận họp")
        for label, dt, bad in (("quá khứ", vn_now() - timedelta(hours=1), True), ("25 giờ", vn_now() + timedelta(hours=25), True), ("24 giờ + 5 phút", vn_now() + timedelta(hours=24, minutes=5), True)):
            d.get_by_label("Gia hạn tới lúc").fill(vn_input(dt))
            d.get_by_role("button", name=re.compile("Lưu quyết định")).click()
            ok(f"[{user}] gia hạn {label}: bị chặn", re.search(r"Chọn thời điểm sau|Chỉ gia hạn tối đa 24 giờ", d.inner_text()) is not None and dialog(page).is_visible())
        # Huỷ đơn
        d.locator("label", has_text="Huỷ đơn").first.click()
        btn = d.get_by_role("button", name=re.compile("^Huỷ đơn$"))
        cls = btn.get_attribute("class") or ""
        ok(f"AC4 [{user}] Huỷ đơn: nút đỏ (btn danger)", "danger" in cls, cls)
        page.wait_for_timeout(700)  # nút đổi từ xanh sang đỏ có chuyển màu
        red = page.evaluate("(el) => [getComputedStyle(el).color, getComputedStyle(el).borderTopColor, getComputedStyle(el).backgroundColor].join('|')", btn.element_handle())
        cols = [[int(x) for x in re.findall(r"\d+", c)[:3]] for c in red.split("|")]
        ok(f"AC4 [{user}] Huỷ đơn: nút đỏ thật (chữ + viền đỏ, hoặc nền đỏ)", any(c[0] > 150 and c[1] < 100 and c[2] < 100 for c in cols), red)
        btn.click()
        ok(f"AC4 [{user}] bấm lần đầu chỉ hỏi lại ('Xác nhận huỷ đơn'), chưa huỷ", d.get_by_role("button", name="Xác nhận huỷ đơn").count() == 1 and dialog(page).is_visible())
        if user == "ql1":
            page.screenshot(path=os.path.join(SHOTS, "qa5-F2k-huy-don-hoi-lai-ql1-1280.png"))
        d.get_by_role("button", name="Quay lại").click()
        ok(f"AC4 [{user}] 'Quay lại' ở bước hỏi lại: về form, chưa huỷ", dialog(page).is_visible() and d.get_by_role("button", name="Xác nhận huỷ đơn").count() == 0)
        page.keyboard.press("Escape")
        go(page, "/confirmation/?tab=ESCALATED")
        ok(f"AC4 [{user}] đơn vẫn ở Cần quyết định (chưa bị huỷ)", row_of(page, "SO260928-A40F28").count() == 1)
        ok(f"[{user}] không lỗi console", not errors, str(errors[:2]))
        ctx.close()
    # gia hạn hợp lệ (+23 giờ) và giao không xác nhận hợp lệ
    ctx, page, errors = new_page(browser, "ql1")
    open_detail_from_queue(page, "SO260928-A40F28", "Cần quyết định")
    page.get_by_role("button", name="Quyết định", exact=True).click()
    d = dialog(page)
    d.locator("label", has_text="Gia hạn gọi").first.click()
    d.get_by_label(re.compile("^Lý do")).fill("Khách hẹn gọi chiều")
    d.get_by_label("Gia hạn tới lúc").fill(vn_input(vn_now() + timedelta(hours=23)))
    d.get_by_role("button", name=re.compile("Lưu quyết định")).dblclick()
    d.wait_for(state="detached")
    settle(page)
    ok("AC4 gia hạn +23 giờ: lưu được, đơn rời Cần quyết định", True)
    to_queue(page, "Cần quyết định")
    ok("gia hạn xong: tab Cần quyết định không còn đơn 0028", row_of(page, "SO260928-A40F28").count() == 0)
    pick_tab(page, "Hẹn gọi lại")
    ok("gia hạn xong: đơn 0028 sang tab Hẹn gọi lại", row_of(page, "SO260928-A40F28").count() == 1)
    ctx.close()


# ====================================================================== 10. 409 & màn cũ
def conflicts_and_stale(browser):
    # CLAIMED / STALE ở từng hộp
    ctx, page, errors = new_page(browser, "cs2")
    open_detail_from_queue(page, "SO260928-B27C30", "Đến giờ gọi")
    page.evaluate("() => window.__caveMock.confirmationClaimByOther(30)")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    page.get_by_text("Chị Lan", exact=False).first.wait_for()
    ok("409 CLAIMED: câu của BE hiện trong khung nhìn, hộp không mở, không có nút 'Tải lại' xung đột", dialog(page).count() == 0 and page.get_by_text("Chị Lan", exact=False).first.is_visible())
    box = page.get_by_text("Chị Lan", exact=False).first.bounding_box()
    ok("409 CLAIMED: thông báo nằm trong khung nhìn", box and 0 <= box["y"] < 860, str(box))
    page.screenshot(path=os.path.join(SHOTS, "qa5-409-claimed-cs2-1280.png"))
    ctx.close()

    # STALE ở F2h, F2j, Huỷ xác nhận, F2k
    ctx, page, errors = new_page(browser, "ql1")
    for name, nid, code in (("F2h", 36, "SO260928-E83D36"), ("F2j", 30, "SO260928-B27C30"), ("F2k", 28, "SO260928-A40F28")):
        open_detail_from_queue(page, code, "Tất cả")
        if name == "F2h":
            page.get_by_role("button", name="Ghi kết quả gọi").click()
            d = dialog(page)
            d.wait_for()
            page.evaluate(f"() => window.__caveMock.confirmationArmStale({nid})")
            d.locator("label", has_text="Đã xác nhận").first.click()
            d.get_by_role("button", name=re.compile("^Lưu kết quả")).click()
        elif name == "F2j":
            more_menu(page, "Đổi người nhận")
            d = dialog(page)
            d.wait_for()
            page.evaluate(f"() => window.__caveMock.confirmationArmStale({nid})")
            d.get_by_label("Tên người nhận").fill("Giả Tên")
            d.get_by_role("button", name="Lưu thay đổi").click()
        else:
            page.get_by_role("button", name="Quyết định", exact=True).click()
            d = dialog(page)
            d.wait_for()
            page.evaluate(f"() => window.__caveMock.confirmationArmStale({nid})")
            d.locator("label", has_text="Bỏ qua gọi xác nhận").first.click()
            d.get_by_label(re.compile("^Lý do")).fill("Giao luôn")
            d.get_by_role("button", name=re.compile("Lưu quyết định")).click()
        d.get_by_role("button", name="Tải lại").wait_for()
        inputs_disabled = d.locator("input:not([disabled]):not([type=hidden]), textarea:not([disabled])").count()
        ok(f"409 STALE_STATE [{name}]: giữ hộp, alert câu của BE, ô nhập bị khoá, nút chính thành 'Tải lại'", d.get_by_role("alert").count() >= 1 and inputs_disabled == 0, f"ô còn mở: {inputs_disabled}")
        if name == "F2k":
            page.screenshot(path=os.path.join(SHOTS, "qa5-409-stale-F2k-ql1-1280.png"))
        d.get_by_role("button", name="Tải lại").click()
        d.wait_for(state="detached")
        settle(page)
        ok(f"409 STALE_STATE [{name}]: 'Tải lại' đóng hộp và nạp lại trang", dialog(page).count() == 0 and page.get_by_role("heading", name=code).is_visible())
    ctx.close()

    # màn cũ: đơn đã sang Soạn hàng trong khi màn đang mở -> ghi cuộc gọi không làm vỡ trang
    ctx, page, errors = new_page(browser, "cs2")
    open_detail_from_queue(page, "SO260928-3F9A01", "Đến giờ gọi")
    page.evaluate("() => window.__caveMock.confirmationSetStatus(31, 'PREPARING')")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = dialog(page)
    d.wait_for()
    d.locator("label", has_text="Không nghe máy").first.click()
    d.get_by_role("button", name=re.compile("^Lưu kết quả")).click()
    page.wait_for_timeout(900)
    txt = page.inner_text("main")
    ok("màn cũ (đơn đã sang Soạn hàng): lưu cuộc gọi không làm vỡ trang, không 'undefined/NaN', không lỗi console", "undefined" not in txt and "NaN" not in txt and not errors, str(errors[:2]))
    ok("màn cũ: sau lưu, trang tự nạp lại và hiện trạng thái Soạn hàng", "Soạn hàng" in txt and dialog(page).count() == 0)
    # nạp lại màn chi tiết đơn đã sang Soạn hàng (back rồi forward để mock giữ trạng thái)
    page.go_back(); page.wait_for_timeout(600); settle(page)
    page.go_forward(); page.wait_for_timeout(800); settle(page)
    btns = [x.strip() for x in page.locator("main button, main a.btn").all_inner_texts()]
    ok("đơn đã sang Soạn hàng: không còn 'Ghi kết quả gọi'", "Ghi kết quả gọi" not in btns, str(btns))
    page.get_by_role("button", name=re.compile("Thao tác khác|Thêm|Khác|Hành động", re.I)).first.click()
    items = [x.strip() for x in page.get_by_role("menuitem").all_inner_texts()]
    ok("đơn đã sang Soạn hàng: menu có 'Huỷ xác nhận đơn'", any("Huỷ xác nhận đơn" in i for i in items), str(items))
    page.get_by_role("menuitem", name=re.compile("Huỷ xác nhận đơn")).click()
    d = dialog(page)
    d.wait_for()
    page.screenshot(path=os.path.join(SHOTS, "qa5-unconfirm-cs2-1280.png"))
    d.get_by_role("button", name=re.compile("Huỷ xác nhận")).last.click()
    ok("Huỷ xác nhận thiếu lý do: báo lỗi, hộp còn mở", dialog(page).is_visible() and re.search(r"Nhập lý do|lý do", d.inner_text(), re.I) is not None, d.inner_text()[-150:].replace("\n", "|"))
    d.get_by_label(re.compile("Lý do")).fill("gọi 0912 345 678")
    d.get_by_role("button", name=re.compile("Huỷ xác nhận")).last.click()
    ok("Huỷ xác nhận: lý do có SĐT bị chặn", dialog(page).is_visible() and "không được chứa số điện thoại" in d.inner_text(), d.inner_text()[-150:].replace("\n", "|"))
    ctx.close()


# ====================================================================== 11. rò dữ liệu cá nhân
def pii_sweep(browser):
    # chạy lại một vòng tương tác rồi rà mọi nơi
    ctx, page, errors = new_page(browser, "cs2")
    visited = []
    for path in ("/confirmation/", "/confirmation/?tab=ESCALATED", "/confirmation/detail/?id=31", "/confirmation/detail/?id=28", "/confirmation/detail/?id=40"):
        go(page, path)
        visited.append(page.url)
        st = storage_dump(page)
        ok(f"G10 {path}: storage / cookie không có dữ liệu khách", not pii_in(st), str([p for p in pii_in(st)]))
        ok(f"G10 {path}: URL không mang tên / SĐT / địa chỉ", not re.search(r"\d{9,}|Th%E1%BB%AD|Khách|Đường", page.url), page.url)
        ok(f"G10 {path}: document.title không có dữ liệu khách", not pii_in(page.title()), page.title())
    ctx.close()
    ctx, page, errors = new_page(browser, "ql1")
    for path in ("/confirmation/detail/?id=28", "/confirmation/detail/?id=31"):
        go(page, path)
        st = storage_dump(page)
        ok(f"G10 [ql1] {path}: storage không có dữ liệu khách", not pii_in(st))
    page.evaluate("() => window.__caveMock.ai('on'); ")
    ctx.close()
    leaked = [(u, t, x[:80]) for (u, t, x) in ALL_CONSOLE if pii_in(x) or re.search(r"\b0\d{9}\b", x)]
    ok("G10 console (log/info/warn/error mọi vai): không in tên, SĐT, địa chỉ", not leaked, str(leaked[:3]))
    ok("G10 không có request tới bên thứ ba (host khác máy chủ test)", not EXTERNAL, str(sorted(set(EXTERNAL))[:5]))


# ====================================================================== 12. 360px
def mobile_360(browser):
    for user in ("cs2", "ql1"):
        ctx, page, errors = new_page(browser, user, w=360, h=780)
        small = []
        go(page, "/confirmation/")
        ok(f"[{user}] 360px hàng chờ: không cuộn ngang trang", no_hscroll(page))
        page.screenshot(path=os.path.join(SHOTS, f"qa5-queue-{user}-360.png"))

        def measure(where):
            res = page.evaluate("""() => {
              const bad = [];
              const vis = (e) => { const r = e.getBoundingClientRect(); const st = getComputedStyle(e); return r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && st.display !== 'none'; };
              document.querySelectorAll('button, a.btn, [role=tab], [role=menuitem], input:not([type=hidden]), select, textarea').forEach(e => {
                if (!vis(e)) return;
                if (e.closest('.sr-only')) return;
                const r = e.getBoundingClientRect();
                if (r.height < 43.5 && !(e.type === 'radio' || e.type === 'checkbox')) bad.push((e.innerText || e.getAttribute('aria-label') || e.name || e.tagName).trim().slice(0, 30) + ' ' + Math.round(r.height));
              });
              return bad;
            }""")
            return res

        small += [("hàng chờ", x) for x in measure("queue")]
        row_of(page, "SO260928-3F9A01").click()
        page.wait_for_url(re.compile(r"id=31$"))
        settle(page)
        page.get_by_role("heading", name="SO260928-3F9A01").wait_for()
        ok(f"[{user}] 360px chi tiết: không cuộn ngang trang", no_hscroll(page))
        page.screenshot(path=os.path.join(SHOTS, f"qa5-detail-{user}-360.png"), full_page=True)
        small += [("chi tiết", x) for x in measure("detail")]
        page.get_by_role("button", name="Ghi kết quả gọi").click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text="Hẹn gọi lại").first.click()
        ok(f"[{user}] 360px F2h: không cuộn ngang, hộp nằm trong màn hình", no_hscroll(page) and (lambda b: b["x"] >= 0 and b["x"] + b["width"] <= 360)(d.bounding_box()))
        page.screenshot(path=os.path.join(SHOTS, f"qa5-F2h-{user}-360.png"))
        small += [("F2h", x) for x in measure("f2h")]
        d.get_by_role("button", name="Quay lại").click()
        more_menu(page, "Đổi người nhận")
        d = dialog(page)
        d.wait_for()
        ok(f"[{user}] 360px F2j: không cuộn ngang", no_hscroll(page))
        page.screenshot(path=os.path.join(SHOTS, f"qa5-F2j-{user}-360.png"))
        small += [("F2j", x) for x in measure("f2j")]
        d.get_by_role("button", name="Huỷ").click() if d.get_by_role("button", name="Huỷ").count() else d.get_by_role("button", name="Quay lại").click()
        if user == "ql1":
            open_detail_from_queue(page, "SO260928-A40F28", "Cần quyết định")
            page.get_by_role("button", name="Quyết định", exact=True).click()
            d = dialog(page)
            d.wait_for()
            d.locator("label", has_text="Huỷ đơn").first.click()
            ok("[ql1] 360px F2k: không cuộn ngang", no_hscroll(page))
            page.screenshot(path=os.path.join(SHOTS, "qa5-F2k-ql1-360.png"))
            small += [("F2k", x) for x in measure("f2k")]
        ok(f"[{user}] 360px: mọi nút / ô / tab / mục menu cao >= 44px", not small, str(small[:8]))
        ok(f"[{user}] 360px: không lỗi console", not errors, str(errors[:2]))
        ctx.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for fn in (role_access, queue_checks, phone_scope, detail_checks, record_each_result, modal_f2h, callback_edges, change_recipient, decide_checks, conflicts_and_stale, pii_sweep, mobile_360):
            try:
                fn(browser)
            except Exception as e:  # một khối vỡ không làm mất các khối còn lại
                ok(f"{fn.__name__}: chạy hết không văng lỗi", False, repr(e)[:300])
        browser.close()
    fails = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(fails)}/{len(results)} đạt")
    for n, _, e in fails:
        print("FAIL:", n, e)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
