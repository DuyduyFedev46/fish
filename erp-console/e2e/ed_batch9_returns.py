# E2E ERP theo design, Lô 9 (Hàng hoàn ED-26): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   SHOTS=<thư mục ảnh> python3 e2e/ed_batch9_returns.py      # tắt server sau khi xong
# Kiểm: giao1 chỉ thấy phiếu của mình, mở phiếu người khác -> "Không tìm thấy" · kho1, ql1, loc thấy tất cả ·
# cs1 (CSKH thuần) không có menu, vào URL thì "Không có quyền"; cs2 (kế thừa quyền giao hàng) vào được nhưng chỉ thấy phiếu của mình (không có) ·
# nút Nhập hàng hoàn theo quyền; nút Tái nhập / Huỷ bỏ chỉ cho Chủ, Quản lý khi Chờ duyệt ·
# nhập vượt số đã giao -> lỗi dưới ô số kg (không mã BR) · nhập hợp lệ -> phiếu mới Chờ duyệt · ghi chú có số điện thoại bị chặn ·
# duyệt Tái nhập và Huỷ bỏ đều chạy; duyệt lần hai (máy khác duyệt trước) -> 409 -> ConflictBanner -> Tải lại ·
# "Mang hàng về kho" ở Việc giao của tôi mở F2m có sẵn phiếu · lỗi tải, rỗng, 403, chi tiết lỗi · id sai -> Không tìm thấy ·
# 360px không cuộn ngang · ghi chú / SĐT không nằm ở URL / localStorage / sessionStorage / console.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)
PHONE_RE = re.compile(r"0\d{9}")
BAD_WORDS = ("BR-HV", "BR-PQ", "SĐT", "RETURN_QTY", "RETURN_BATCH", "STALE_STATE", "undefined", "NaN", "[object")


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
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


def new_page(browser, user, w=1280, h=860, errors=None, touch=False):
    errors = errors if errors is not None else []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", **({"is_mobile": True, "has_touch": True} if touch else {}))
    page = ctx.new_page()
    # Lỗi HTTP 4xx/5xx chủ ý (ca lạ) tự sinh dòng "Failed to load resource": không tính.
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, user)
    return ctx, page, errors


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])")


def nav_labels(page):
    return [t.strip() for t in page.locator(".nav a").all_inner_texts()]


def codes(page):
    return [c.strip() for c in page.locator("main table tbody tr td:first-child").all_inner_texts()]


def wait_rows(page, n):
    page.wait_for_function("(n) => document.querySelectorAll('main table tbody tr td:first-child').length === n && [...document.querySelectorAll('main table tbody tr td:first-child')].every(e => e.innerText.startsWith('RT-'))", arg=n)


def dialog(page):
    return page.get_by_role("dialog")


def roles(browser):
    # cs1: CSKH thuần, không có quyền xem hàng hoàn
    ctx, page, errors = new_page(browser, "cs1")
    ok("cs1: menu không có Hàng hoàn", not any("Hàng hoàn" in t for t in nav_labels(page)), str(nav_labels(page)))
    go(page, "/returns/")
    ok("cs1: /returns/ hiện 'Không có quyền'", page.get_by_role("heading", name="Không có quyền").count() >= 1)
    go(page, "/returns/detail/?id=1")
    ok("cs1: /returns/detail/ hiện 'Không có quyền', không lộ phiếu", page.get_by_role("heading", name="Không có quyền").count() >= 1 and "RT-1" not in page.inner_text("main"))
    ok("cs1: không console.error", errors == [], str(errors))
    ctx.close()

    # cs2: trong dữ liệu mẫu kế thừa quyền của nhân viên giao -> vào được nhưng chỉ thấy phiếu của mình
    ctx, page, errors = new_page(browser, "cs2")
    go(page, "/returns/")
    ok("cs2: danh sách chỉ phiếu của mình (không có phiếu nào)", len(codes(page)) == 0 or all(c.startswith("RT-") for c in codes(page)), str(codes(page)))
    go(page, "/returns/detail/?id=1")
    ok("cs2: mở phiếu người khác -> Không tìm thấy", page.get_by_role("heading", name="Không tìm thấy").count() >= 1)
    ctx.close()

    # giao1: chỉ phiếu của mình
    ctx, page, errors = new_page(browser, "giao1")
    ok("giao1: menu có Hàng hoàn", any("Hàng hoàn" in t for t in nav_labels(page)))
    go(page, "/returns/")
    got = codes(page)
    ok("giao1: chỉ thấy RT-1, RT-5 và RT-6 (phiếu giao của mình)", sorted(got) == ["RT-1", "RT-5", "RT-6"], str(got))
    ok("giao1: có nút Nhập hàng hoàn", page.get_by_role("button", name="Nhập hàng hoàn").count() == 1)
    go(page, "/returns/detail/?id=2")
    ok("giao1: mở RT-2 của giao2 -> Không tìm thấy, không lộ ghi chú", page.get_by_role("heading", name="Không tìm thấy").count() >= 1 and "từ chối" not in page.inner_text("main"))
    go(page, "/returns/detail/?id=1")
    ok("giao1: mở RT-1 của mình được", "RT-1" in page.inner_text("main"))
    ok("giao1: không có nút Tái nhập / Huỷ bỏ (không có quyền duyệt)", page.get_by_role("button", name="Tái nhập vào lô").count() == 0 and page.get_by_role("button", name="Huỷ hàng, ghi lỗ").count() == 0)
    ok("giao1: không console.error", errors == [], str(errors))
    ctx.close()

    for user in ("kho1", "ql1", "loc"):
        ctx, page, errors = new_page(browser, user)
        ok(f"{user}: menu có Hàng hoàn, bấm được", any("Hàng hoàn" in t for t in nav_labels(page)))
        page.locator(".nav a", has_text="Hàng hoàn").first.click()
        page.wait_for_url(re.compile(r"/returns/?$"))
        settle(page)
        body = page.inner_text("main")
        ok(f"{user}: danh sách đủ cột, không cột Lý do", all(h in body for h in ("Mã phiếu", "Phiếu giao", "Lô", "Mặt hàng", "Số kg", "Ngoài kho lạnh", "Trạng thái", "Quyết định", "Ghi chú")) and "Lý do" not in body)  # 1280px: Người nhập ẩn (khung < 1100px), có ở 1440px
        ok(f"{user}: thấy cả phiếu của người giao khác (RT-1, RT-2, RT-3, RT-5, RT-6)", sorted(codes(page)) == ["RT-1", "RT-2", "RT-3", "RT-5", "RT-6"], str(codes(page)))
        ok(f"{user}: kg dạng 'n kg', giờ dạng dd/mm/yyyy, không từ cấm", re.search(r"\d(,\d+)? kg", body) is not None and not any(w in body for w in BAD_WORDS))
        # Lô bổ sung A (#21): Quản lý có inventory.add_returntostock (BE migration 0008) nên cũng có nút Nhập hàng hoàn.
        ok(f"{user}: có nút Nhập hàng hoàn", page.get_by_role("button", name="Nhập hàng hoàn").count() == 1)
        page.locator("main table tbody tr", has_text="RT-1").click()
        page.wait_for_url(re.compile(r"/returns/detail/\?id=1"))
        settle(page)
        approve = page.get_by_role("button", name="Tái nhập vào lô").count() == 1 and page.get_by_role("button", name="Huỷ hàng, ghi lỗ").count() == 1
        ok(f"{user}: nút Tái nhập / Huỷ bỏ " + ("có" if user != "kho1" else "KHÔNG có") + " ở phiếu Chờ duyệt", approve == (user != "kho1"))
        ok(f"{user}: không console.error", errors == [], str(errors))
        ctx.close()


def list_filters(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/returns/")
    ok("Lọc: mặc định tháng hiện tại (RT-4 của tháng trước không có)", "RT-4" not in codes(page))
    page.get_by_label("Lọc theo trạng thái").select_option("DRAFT")
    wait_rows(page, 3)
    ok("Lọc Chờ duyệt: chỉ phiếu Chờ duyệt", sorted(codes(page)) == ["RT-1", "RT-2", "RT-5"], str(codes(page)))
    page.get_by_label("Lọc theo trạng thái").select_option("APPROVED")
    wait_rows(page, 1)
    ok("Lọc Đã duyệt: RT-3", codes(page) == ["RT-3"], str(codes(page)))
    page.get_by_label("Lọc theo trạng thái").select_option("CANCELLED")
    wait_rows(page, 1)
    ok("Lọc Đã huỷ: RT-6 (Lô bổ sung A #8)", codes(page) == ["RT-6"], str(codes(page)))
    page.get_by_label("Lọc theo trạng thái").select_option("")
    page.get_by_label("Lọc theo tháng").select_option("")
    wait_rows(page, 6)
    ok("Mọi tháng: có RT-4", "RT-4" in codes(page))
    box = page.get_by_role("searchbox", name="Tìm phiếu hàng hoàn")
    box.fill("tôm")
    wait_rows(page, 1)
    ok("Tìm 'tôm': RT-1", codes(page) == ["RT-1"], str(codes(page)))
    ok("Từ khoá không nằm trong URL / storage", "tom" not in page.url.lower() and "tôm" not in storage_dump(page))
    box.fill("zzzz-khong-co")
    page.wait_for_function("() => document.body.innerText.includes('Xoá tìm kiếm')")
    ok("Tìm không thấy: có 'Xoá tìm kiếm'", page.locator("main table tbody tr").count() == 0)
    ok("Không console.error", errors == [], str(errors))
    ctx.close()


def states(browser):
    for mode, expected in (("empty", "Chưa có phiếu hàng hoàn nào"), ("fail", "Không tải được dữ liệu")):
        ctx, page, errors = new_page(browser, "loc")
        go(page, "/returns/")
        page.evaluate("(m) => window.__caveMock.returns(m)", mode)
        go(page, "/returns/")
        ok(f"Trạng thái {mode}: hiện '{expected}'", expected in page.inner_text("main"), page.inner_text("main")[:200])
        if mode == "fail":
            ok("Lỗi tải: có nút Thử lại", page.get_by_role("button", name="Thử lại").count() >= 1)
            page.evaluate("(m) => window.__caveMock.returns(m)", "ok")
            page.get_by_role("button", name="Thử lại").first.click()
            page.wait_for_function("() => document.body.innerText.includes('RT-1')")
            ok("Thử lại: danh sách trở về", "RT-1" in codes(page))
        ctx.close()
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/returns/")
    page.evaluate("(m) => window.__caveMock.returns(m)", "forbidden")
    go(page, "/returns/")
    ok("403 từ máy chủ: hiện 'Không có quyền'", page.get_by_role("heading", name="Không có quyền").count() >= 1)
    page.evaluate("(m) => window.__caveMock.returns(m)", "detailfail")
    go(page, "/returns/detail/?id=1")
    ok("Chi tiết lỗi máy chủ: có nút Thử lại", page.get_by_role("button", name="Thử lại").count() >= 1)
    page.evaluate("(m) => window.__caveMock.returns(m)", "ok")
    for bad in ("", "?id=abc", "?id=0", "?id=99999"):
        go(page, "/returns/detail/" + bad)
        ok(f"Chi tiết {bad or '(không id)'}: Không tìm thấy", page.get_by_role("heading", name="Không tìm thấy").count() >= 1)
    ctx.close()


def layout_links_errors(browser):
    """QA Lô 9 B2/B3 và hai lỗi BE mới: bảng vừa khung, màu cảnh báo quá 2 giờ, liên kết, RETURN_BATCH_CLOSED, 400 ô ghi chú."""
    # B2: không cuộn ngang trong khung bảng ở 1280, 1440 (và 1100); cột Ghi chú nằm trọn trong khung
    for w in (1280, 1440, 1100):
        ctx, page, errors = new_page(browser, "ql1", w=w, h=900)
        go(page, "/returns/")
        page.wait_for_function("() => document.querySelectorAll('main table tbody tr').length > 0")
        m = page.evaluate("""() => {
          const wrap = document.querySelector('.lt-scroll'); const ths = [...document.querySelectorAll('main table thead th')].filter(e => getComputedStyle(e).display !== 'none');
          const last = ths[ths.length - 1].getBoundingClientRect(); const wr = wrap.getBoundingClientRect();
          return {sw: wrap.scrollWidth, cw: wrap.clientWidth, lastRight: Math.round(last.right), wrapRight: Math.round(wr.right), cols: ths.map(e => e.innerText.trim())};
        }""")
        ok(f"B2 {w}px: bảng không cuộn ngang trong khung", m["sw"] <= m["cw"] + 1, str(m))
        ok(f"B2 {w}px: cột Ghi chú nằm trọn trong khung", "Ghi chú" in m["cols"] and m["lastRight"] <= m["wrapRight"] + 1, str(m))
        ok(f"B2 {w}px: trang không cuộn ngang", no_hscroll(page))
        if w == 1280:
            ok("B2 1280px: khung hẹp hơn 1100px thì ẩn cột phụ Người nhập, còn 9 cột", "Người nhập" not in m["cols"] and len(m["cols"]) == 9, str(m["cols"]))
            page.screenshot(path=f"{SHOTS}/lo9-b2-list-1280.png")
        if w == 1440:
            ok("B2 1440px: đủ 10 cột", len(m["cols"]) == 10, str(m["cols"]))
            page.screenshot(path=f"{SHOTS}/lo9-b2-list-1440.png")
            long_note = page.locator("main table tbody tr", has_text="RT-3").locator("td").last
            ok("B2: ghi chú dài cắt chữ kèm title đủ câu", long_note.locator("[title]").count() == 1 and "Sai địa chỉ, giao lại" in (long_note.locator("[title]").get_attribute("title") or ""))
        ok(f"B2 {w}px: không console.error", errors == [], str(errors))
        ctx.close()

    # B3: màu cảnh báo quá 2 giờ (list + detail), liên kết theo quyền
    ctx, page, errors = new_page(browser, "ql1", w=1280, h=900)
    go(page, "/returns/")
    warn = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--warn').trim()")
    def color_of(loc):
        return loc.evaluate("e => getComputedStyle(e).color")
    probe = page.evaluate("""() => { const s = document.createElement('span'); s.style.color = 'var(--warn)'; document.body.appendChild(s); const c = getComputedStyle(s).color; s.remove(); return c; }""")
    row1 = page.locator("main table tbody tr", has_text="RT-1")   # 135 phút = quá 2 giờ
    row2 = page.locator("main table tbody tr", has_text="RT-2")   # 55 phút
    ok("B3 danh sách: 2 giờ 15 phút tô màu warn", row1.locator(".warn-text").count() == 1 and color_of(row1.locator(".warn-text")) == probe, probe)
    ok("B3 danh sách: 55 phút không tô", row2.locator(".warn-text").count() == 0)
    ok("B3 danh sách: màu cảnh báo là token (có giá trị --warn)", bool(warn), warn)
    go(page, "/returns/detail/?id=1")
    ok("B3 chi tiết: Ngoài kho lạnh quá 2 giờ tô màu warn", page.locator("main .warn-text").count() == 1 and color_of(page.locator("main .warn-text")) == probe)
    ok("B3 chi tiết: chữ hiện '2 giờ 15 phút'", "2 giờ 15 phút" in page.locator("main .warn-text").inner_text())
    note_link = page.locator("main dd a", has_text="GH-HD-0038-FAIL")
    ok("B3 chi tiết: Phiếu giao là liên kết /deliveries/detail/?id=38", note_link.count() == 1 and note_link.get_attribute("href") == "/deliveries/detail/?id=38", str(note_link.count()))
    page.wait_for_function("() => [...document.querySelectorAll('main dd a')].some(a => a.getAttribute('href').startsWith('/orders/detail/'))")
    order_link = page.locator("main dd a", has_text="SO260928-A00008")
    ok("B3 chi tiết: Đơn là liên kết /orders/detail/?id=<id đơn>", order_link.count() == 1 and re.fullmatch(r"/orders/detail/\?id=\d+", order_link.get_attribute("href") or "") is not None, order_link.get_attribute("href") if order_link.count() else "không có")
    ok("B3 chi tiết: Lô vẫn là chữ thường (Lô 7 chưa có màn)", page.locator("main dd a", has_text="TOM-SU-1").count() == 0 and "TOM-SU-1-260920-AB12C" in page.inner_text("main"))
    page.screenshot(path=f"{SHOTS}/lo9-b3-detail-1280.png")
    page.locator("main dd a", has_text="GH-HD-0038-FAIL").click()
    page.wait_for_url(re.compile(r"/deliveries/detail/\?id=38"))
    settle(page)
    ok("B3: bấm Phiếu giao mở trang chi tiết phiếu giao", "GH-HD-0038-FAIL" in page.inner_text("main"))
    go(page, "/returns/detail/?id=2")
    ok("B3 chi tiết: 55 phút không tô cảnh báo", page.locator("main .warn-text").count() == 0)
    ok("B3: không console.error", errors == [], str(errors))
    ctx.close()

    # kho1: Phiếu giao luôn có link; Đơn là link khi menu có "Đơn & tiền" (cùng điều kiện canView), không thì chữ thường
    ctx, page, errors = new_page(browser, "kho1")
    go(page, "/returns/detail/?id=1")
    ok("B3 kho1: Phiếu giao là liên kết", page.locator("main dd a", has_text="GH-HD-0038-FAIL").count() == 1)
    has_orders = any("Đơn & tiền" in t for t in nav_labels(page))
    page.wait_for_timeout(600)
    ok("B3 kho1: Đơn là liên kết đúng khi người xem có màn Đơn", (page.locator("main dd a", has_text="SO260928-A00008").count() == 1) == has_orders, str(has_orders))
    ctx.close()
    # giao1: phiếu của mình, link Phiếu giao
    ctx, page, errors = new_page(browser, "giao1")
    go(page, "/returns/detail/?id=1")
    ok("B3 giao1: Phiếu giao là liên kết, mã đơn chữ thường", page.locator("main dd a", has_text="GH-HD-0038-FAIL").count() == 1 and page.locator("main dd a", has_text="SO260928-A00008").count() == 0)
    ctx.close()

    # RETURN_BATCH_CLOSED -> dưới ô Lô; 400 ô ghi chú từ BE -> dưới ô Ghi chú
    for mode, label, expect_text, field_label in (
        ("batchclosed", "RETURN_BATCH_CLOSED", "đã chốt", "Lô"),
        ("noterejected", "400 ô ghi chú", "dãy số dài", "Ghi chú"),
    ):
        ctx, page, errors = new_page(browser, "kho1")
        go(page, "/returns/")
        page.evaluate("(m) => window.__caveMock.returns(m)", mode)
        page.get_by_role("button", name="Nhập hàng hoàn").click()
        dlg = dialog(page)
        page.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
        dlg.get_by_label("Phiếu giao").select_option(label=[t for t in dlg.get_by_label("Phiếu giao").locator("option").all_inner_texts() if "GH-HD-0039-DELI" in t][0])
        page.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
        dlg.get_by_label("Số kg hoàn").fill("0.1")
        if mode == "noterejected":
            dlg.get_by_label(re.compile("Ghi chú")).fill("khách hẹn lại ngày mai")
        dlg.get_by_role("button", name="Gửi duyệt").click()
        page.wait_for_function("(t) => document.querySelector('[role=dialog]').innerText.includes(t)", arg=expect_text)
        group = dlg.locator("[data-invalid]")
        ok(f"{label}: đúng một ô bị đánh dấu lỗi, là ô {field_label}", group.count() == 1 and field_label in group.first.inner_text(), str(group.all_inner_texts()))
        ok(f"{label}: câu lỗi hiện dưới ô {field_label}", expect_text in group.first.inner_text(), group.first.inner_text()[:300])
        ok(f"{label}: không có alert đầu hộp, không lộ mã", dlg.locator("[role=alert]").count() == 0 and not any(w in dlg.inner_text() for w in BAD_WORDS), str(dlg.locator("[role=alert]").all_inner_texts()))
        page.screenshot(path=f"{SHOTS}/lo9-err-{mode}-1280.png")
        if mode == "noterejected":
            dlg.get_by_label(re.compile("Ghi chú")).fill("khách hẹn lại chiều")
        else:
            dlg.get_by_label(re.compile("Lô")).first.select_option(index=0)
        ok(f"{label}: sửa ô thì câu lỗi biến mất", dlg.locator("[data-invalid]").count() == 0 or expect_text not in dlg.inner_text(), dlg.inner_text()[:300])
        page.evaluate("(m) => window.__caveMock.returns(m)", "ok")
        ok(f"{label}: không console.error", errors == [], str(errors))
        ctx.close()


def create_flow(browser):
    ctx, page, errors = new_page(browser, "kho1")
    go(page, "/returns/")
    page.get_by_role("button", name="Nhập hàng hoàn").click()
    dlg = dialog(page)
    expect(dlg.get_by_label("Phiếu giao")).to_be_visible()
    page.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
    note_labels = dlg.get_by_label("Phiếu giao").locator("option").all_inner_texts()
    ok("F2m: chỉ liệt kê phiếu Đang giao / Giao thất bại", any("GH-HD-0038-FAIL" in t for t in note_labels) and any("GH-HD-0033-DELI" in t for t in note_labels), str(note_labels))
    ok("F2m: Rời kho lúc / Về kho lúc chỉ đọc", dlg.locator("[data-time=left]").count() == 1 and dlg.locator("[data-time=returned]").count() == 1 and dlg.locator("input[type=datetime-local]").count() == 0)
    ok("F2m: nút Huỷ và Gửi duyệt", dlg.get_by_role("button", name="Huỷ").count() >= 1 and dlg.get_by_role("button", name="Gửi duyệt").count() == 1)
    # bỏ trống -> lỗi tại chỗ
    dlg.get_by_role("button", name="Gửi duyệt").click()
    ok("F2m: bỏ trống -> 'Chọn phiếu giao.'", "Chọn phiếu giao." in dlg.inner_text())
    dlg.get_by_label("Phiếu giao").select_option(label=[t for t in note_labels if "GH-HD-0038-FAIL" in t][0])
    page.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
    facts = dlg.locator("[data-qty-facts]").inner_text()
    ok("F2m: hiện ngay 'Đã giao 1 kg, đã hoàn 0,5 kg, còn hoàn được 0,5 kg' (lô tự chọn vì phiếu có 1 lô)", "Đã giao 1 kg" in facts and "đã hoàn 0,5 kg" in facts and "còn hoàn được 0,5 kg" in facts, facts)
    dlg.get_by_label("Số kg hoàn").fill("0")
    dlg.get_by_role("button", name="Gửi duyệt").click()
    ok("F2m: số kg 0 -> lỗi dưới ô", "lớn hơn 0" in dlg.inner_text())
    # chặn tại chỗ: phiếu 38 đã giao 1, đã hoàn 0,5 -> còn 0,5; nhập 0,6 bị chặn trước khi gửi
    dlg.get_by_label("Số kg hoàn").fill("0.6")
    dlg.get_by_role("button", name="Gửi duyệt").click()
    txt = dlg.inner_text()
    ok("F2m: nhập vượt số còn hoàn được -> chặn tại chỗ, lỗi dưới ô số kg", "vượt số đã giao" in txt and "chỉ còn hoàn được 0,5 kg" in txt, txt[:400])
    ok("F2m: chặn tại chỗ không đổi nút chính thành Thử lại (chưa gửi lên BE)", dlg.get_by_role("button", name="Gửi duyệt").count() == 1 and dlg.get_by_role("button", name="Thử lại").count() == 0)
    ok("F2m: lỗi vượt không lộ mã BR / RETURN_", not any(w in txt for w in BAD_WORDS))
    page.screenshot(path=f"{SHOTS}/f2m-over-limit-1280.png")
    # TL9-M2: người khác vừa hoàn thêm 0,1 kg (FE chưa biết) -> nhập 0,45 qua được FE, BE báo vượt; sửa ô thì lỗi không nhảy lên đầu hộp
    page.evaluate("() => window.__caveMock.returnsAddHidden(38, 0.1)")
    dlg.get_by_label("Số kg hoàn").fill("0.45")
    dlg.get_by_role("button", name="Gửi duyệt").click()
    page.wait_for_function("() => document.querySelector('[role=dialog]').innerText.includes('đã hoàn 0,6 kg')")
    ok("F2m: BE báo vượt -> lỗi dưới ô số kg, số liệu mới 'đã hoàn 0,6 kg'", "chỉ còn hoàn được 0,4 kg" in dlg.inner_text(), dlg.inner_text()[:400])
    ok("F2m: lỗi BE gắn ô, không có alert đầu hộp", dlg.locator("[role=alert]").count() == 0, str(dlg.locator("[role=alert]").all_inner_texts()))
    dlg.get_by_label("Số kg hoàn").fill("0.2")
    ok("F2m: sửa ô sau lỗi vượt kg -> câu lỗi biến mất, không nhảy lên đầu hộp", "vượt số đã giao" not in dlg.inner_text() and dlg.locator("[role=alert]").count() == 0, dlg.inner_text()[:400])
    ok("F2m: sau lỗi BE số liệu cập nhật 'đã hoàn 0,6 kg, còn hoàn được 0,4 kg'", "đã hoàn 0,6 kg" in dlg.locator("[data-qty-facts]").inner_text() and "còn hoàn được 0,4 kg" in dlg.locator("[data-qty-facts]").inner_text())
    # ghi chú có số điện thoại bị chặn
    dlg.get_by_label("Số kg hoàn").fill("0.2")
    dlg.get_by_label(re.compile("Ghi chú")).fill("gọi 0987000123 giúp")
    dlg.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    ok("F2m: ghi chú có số điện thoại bị chặn", "không được chứa số điện thoại" in dlg.inner_text())
    ok("F2m: số điện thoại không nằm trong storage / URL", "0987000123" not in storage_dump(page) and "0987000123" not in page.url)
    dlg.get_by_label(re.compile("Ghi chú")).fill("khách hẹn lại ngày mai")
    dlg.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    settle(page)
    ok("F2m: gửi hợp lệ -> đóng hộp, hiện toast", page.get_by_text("Đã gửi phiếu hàng hoàn").count() >= 1)
    page.wait_for_function("() => document.body.innerText.includes('RT-7')")
    row = page.locator("main table tbody tr", has_text="RT-7")
    ok("Phiếu mới RT-7 ở trạng thái Chờ duyệt, 0,2 kg", "Chờ duyệt" in row.inner_text() and "0,2 kg" in row.inner_text(), row.inner_text())
    ok("Ghi chú phiếu mới không nằm ở storage / URL", "khách hẹn lại" not in storage_dump(page) and "khách" not in page.url)
    ok("Không console.error", errors == [], str(errors))
    ctx.close()


def approve_flow(browser):
    for label, btn, done_text in (("Tái nhập", "Tái nhập vào lô", "Đã duyệt. Hàng đã nhập lại vào lô."), ("Huỷ bỏ", "Huỷ hàng, ghi lỗ", "Đã duyệt. Hàng đã huỷ hàng, ghi lỗ.")):
        ctx, page, errors = new_page(browser, "ql1")
        go(page, "/returns/")
        page.locator("main table tbody tr", has_text="RT-1").click()
        page.wait_for_url(re.compile(r"/returns/detail/\?id=1"))
        settle(page)
        page.get_by_role("button", name=btn).click()
        dlg = dialog(page)
        ok(f"F2n ({label}): có tóm tắt Lô, Mặt hàng, Số kg, Ngoài kho lạnh", all(t in dlg.inner_text() for t in ("Lô", "Mặt hàng", "Số kg", "Ngoài kho lạnh")), dlg.inner_text()[:300])
        ok(f"F2n ({label}): nút Quay lại và Duyệt", dlg.get_by_role("button", name="Quay lại").count() >= 1 and dlg.get_by_role("button", name="Duyệt", exact=True).count() == 1)
        ok(f"F2n ({label}): quyết định chọn sẵn theo nút đã bấm", dlg.get_by_role("radio", checked=True).count() == 1)
        if label == "Tái nhập":
            page.screenshot(path=f"{SHOTS}/f2n-approve-1280.png")
        dlg.get_by_role("button", name="Duyệt", exact=True).click()
        page.wait_for_function("() => !document.querySelector('[role=dialog]')")
        settle(page)
        body = page.inner_text("main")
        ok(f"Duyệt {label}: toast + chip Đã duyệt + hết nút", page.get_by_text(done_text).count() >= 1 and "Đã duyệt" in body and page.get_by_role("button", name=btn).count() == 0, body[:200])
        ok(f"Duyệt {label}: dòng thời gian có bước duyệt", "Duyệt " in page.locator("main").inner_text())
        ctx.close()

    # F2n không chọn quyết định: dùng nút rồi bỏ chọn không thể (radio) -> kiểm Quay lại không gọi gì
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/returns/detail/?id=2")
    page.get_by_role("button", name="Tái nhập vào lô").click()
    dialog(page).get_by_role("button", name="Quay lại").click()
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    ok("F2n: Quay lại đóng hộp, phiếu vẫn Chờ duyệt", "Chờ duyệt" in page.inner_text("main") and page.get_by_role("button", name="Tái nhập vào lô").count() == 1)

    # 409: máy khác duyệt trước
    page.evaluate("() => window.__caveMock.returnsMarkApproved(2)")
    page.get_by_role("button", name="Huỷ hàng, ghi lỗ").click()
    dlg = dialog(page)
    dlg.get_by_role("button", name="Duyệt", exact=True).click()
    page.wait_for_function("() => document.querySelector('[role=dialog]') && document.querySelector('[role=dialog]').innerText.includes('Tải lại')")
    ok("409: ConflictBanner có nút Tải lại, không lộ STALE_STATE", dlg.get_by_role("button", name="Tải lại").count() >= 1 and "STALE_STATE" not in dlg.inner_text(), dlg.inner_text()[:300])
    page.screenshot(path=f"{SHOTS}/f2n-409-1280.png")
    dlg.get_by_role("button", name="Tải lại").first.click()
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    settle(page)
    ok("Tải lại sau 409: phiếu Đã duyệt, hết nút duyệt", page.get_by_role("button", name="Huỷ hàng, ghi lỗ").count() == 0 and "Đã duyệt" in page.inner_text("main"))
    ok("Không console.error", errors == [], str(errors))
    ctx.close()


def my_deliveries(browser):
    ctx, page, errors = new_page(browser, "giao1", w=360, h=780, touch=True)
    go(page, "/my-deliveries/")
    card = page.locator("li[data-status=FAILED]").first
    ok("Việc giao của tôi: thẻ Giao thất bại có nút 'Mang hàng về kho'", card.get_by_role("button", name="Mang hàng về kho").count() == 1)
    ok("Việc giao của tôi: thẻ Đang giao KHÔNG có nút Mang hàng về kho", page.locator("li[data-status=DELIVERING]").first.get_by_role("button", name="Mang hàng về kho").count() == 0)
    code = card.locator("span").first.inner_text().strip()
    card.get_by_role("button", name="Mang hàng về kho").click()
    dlg = dialog(page)
    page.wait_for_function("() => document.querySelector('[role=dialog] select').value !== ''")
    sel = dlg.get_by_label("Phiếu giao")
    ok("Mang hàng về kho: F2m mở, phiếu giao điền sẵn", code in sel.evaluate("e => e.options[e.selectedIndex].text"), code)
    page.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
    dlg.get_by_label("Số kg hoàn").fill("0.2")
    page.screenshot(path=f"{SHOTS}/f2m-prefilled-360.png")
    ok("Mang hàng về kho 360px: không cuộn ngang", no_hscroll(page))
    dlg.get_by_role("button", name="Gửi duyệt").click()
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    ok("Mang hàng về kho: gửi xong có toast", page.get_by_text("Đã gửi phiếu hàng hoàn").count() >= 1)
    ok("Không console.error", errors == [], str(errors))
    ctx.close()


def mobile(browser):
    ctx, page, errors = new_page(browser, "loc", w=360, h=780, touch=True)
    go(page, "/returns/")
    ok("360px: danh sách không cuộn ngang trang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/list-360.png")
    go(page, "/returns/detail/?id=1")
    ok("360px: chi tiết không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/detail-360.png")
    page.get_by_role("button", name="Tái nhập vào lô").click()
    ok("360px: hộp Duyệt không cuộn ngang trang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/f2n-360.png")
    ctx.close()
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/returns/")
    page.screenshot(path=f"{SHOTS}/list-1280.png")
    go(page, "/returns/detail/?id=3")
    page.screenshot(path=f"{SHOTS}/detail-approved-1280.png")
    ok("Phiếu Đã duyệt: có người duyệt + quyết định, không nút duyệt", "Người duyệt" in page.inner_text("main") and page.get_by_role("button", name="Tái nhập vào lô").count() == 0)
    ctx.close()


def privacy(browser):
    ctx, page, errors = new_page(browser, "kho1")
    for path in ("/returns/", "/returns/detail/?id=1", "/returns/detail/?id=3"):
        go(page, path)
        dump = storage_dump(page)
        ok(f"{path}: ghi chú / tên khách không nằm ở storage", all(w not in dump for w in ("Khách không nghe máy", "Khách từ chối", "Sai địa chỉ")), dump[:200])
        ok(f"{path}: URL chỉ có id", "Khách" not in page.url and "note" not in page.url)
        ok(f"{path}: không số điện thoại trên trang", not PHONE_RE.search(page.inner_text("main")))
    ok("Không console.error / log dữ liệu cá nhân", errors == [], str(errors))
    ctx.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for fn in (roles, list_filters, states, layout_links_errors, create_flow, approve_flow, my_deliveries, mobile, privacy):
            try:
                fn(browser)
            except Exception as e:  # noqa: BLE001
                ok(f"{fn.__name__}: chạy hết không lỗi", False, repr(e)[:400])
        browser.close()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
