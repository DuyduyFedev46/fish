# E2E ERP theo design, Lô 5 (Gọi xác nhận ED-15): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3201 &)
#   BASE=http://127.0.0.1:3201 SHOTS=<thư mục ảnh> python3 e2e/ed_batch5_confirmation.py      # tắt server sau khi xong
# Kiểm: cs2 / loc / ql1 vào được, kho1 / giao1 không · dòng ngoài phạm vi che SĐT và không mở được, dòng trong phạm vi hiện đủ số
# (bất biến 9) · tab đúng thứ tự AC1, tên "Gọi báo hoàn tiền" · 7 kết quả cuộc gọi (AC2) · hẹn gọi lại thiếu giờ -> "Chọn thời điểm
# sau dd/mm/yyyy hh:mm." (AC3) · ghi chú có số bị chặn · CSKH không có Quyết định (AC5), Chủ / Quản lý có, huỷ đơn là nút đỏ có xác nhận
# (AC4) · 409 CLAIMED · 409 STALE_STATE -> ConflictBanner · tìm khách · rỗng / tìm không ra · 360px không cuộn ngang ·
# SĐT, tên, địa chỉ không nằm ở localStorage / URL / console.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3201")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)

PHONE_IN = "0900000123"      # đơn 31, trong phạm vi
PHONE_OUT_FULL = "0900000555"  # đơn 40, ngoài phạm vi của CSKH: chỉ Chủ / Quản lý thấy đủ
PHONE_OUT_MASK = "09xx xxx 555"


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


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


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def new_page(browser, user, w=1280, h=860, errors=None):
    errors = errors if errors is not None else []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and "HTTP" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, user)
    return ctx, page, errors


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])")


def row_of(page, code):
    return page.locator("table.lt tbody tr", has_text=code)


def dialog(page):
    return page.get_by_role("dialog")


def pick_tab(page, name):
    page.get_by_role("tab", name=re.compile(rf"^{name}")).click()
    page.wait_for_load_state("networkidle")
    settle(page)


# ---------------------------------------------------------------- vai được vào / không được vào
def role_access(browser):
    for user in ("cs2", "loc", "ql1"):
        ctx, page, errors = new_page(browser, user)
        go(page, "/confirmation/")
        ok(f"{user}: vào được /confirmation/", page.get_by_role("tab").count() >= 6 and page.get_by_text("không có quyền", exact=False).count() == 0, page.url)
        ctx.close()
    for user in ("kho1", "giao1"):
        ctx, page, errors = new_page(browser, user)
        go(page, "/confirmation/")
        ok(f"{user}: /confirmation/ hiện không có quyền", page.get_by_text("không có quyền", exact=False).first.is_visible())
        go(page, "/confirmation/detail/?id=31")
        ok(f"{user}: /confirmation/detail/ hiện không có quyền", page.get_by_text("không có quyền", exact=False).first.is_visible())
        ok(f"{user}: không có mục Gọi xác nhận trong menu", page.locator(".nav a", has_text="Gọi xác nhận").count() == 0)
        ctx.close()


# ---------------------------------------------------------------- danh sách (CSKH)
def queue_customer_service(browser):
    ctx, page, errors = new_page(browser, "cs2")
    go(page, "/confirmation/")
    tabs = [t.strip() for t in page.get_by_role("tab").all_inner_texts()]
    names = [re.sub(r"\s*\d+$", "", t).strip() for t in tabs]
    ok("AC1: tab đúng thứ tự", names == ["Cần gọi ngay", "Hẹn gọi lại", "Cần quyết định", "Gọi báo hoàn tiền", "Chờ gọi", "Tất cả"], str(names))
    ok("AC1: không còn chữ 'Báo hoàn tiền' trần ở tab", not any(n == "Báo hoàn tiền" for n in names))

    body = page.inner_text("main")
    # bất biến 9
    r_in = row_of(page, "SO260928-3F9A01")
    ok("dòng trong phạm vi: hiện đủ SĐT", PHONE_IN in r_in.inner_text(), r_in.inner_text().replace("\n", "|")[:120])
    ok("dòng trong phạm vi: SĐT là liên kết tel:", page.locator(f"a[href='tel:{PHONE_IN}']").count() >= 1)
    r_out = row_of(page, "SO260928-1B7A40")
    ok("dòng ngoài phạm vi: hiện số đã che do BE trả", PHONE_OUT_MASK in r_out.inner_text(), r_out.inner_text().replace("\n", "|")[:120])
    ok("dòng ngoài phạm vi: không lộ số đủ, tên hay địa chỉ", PHONE_OUT_FULL not in body and "Khách Thử K" not in body and "Hải Phòng" not in body and "Ngoài phạm vi gọi" in r_out.inner_text())
    ok("dòng ngoài phạm vi: không phải liên kết / không có tel:", r_out.locator("a").count() == 0 and page.locator("a[href='tel:09xxxxx555']").count() == 0)
    ok("dòng ngoài phạm vi: bấm không đi đâu", (r_out.click() or True) and "/confirmation/detail" not in page.url)

    # AC6 trên danh sách: tiền "đ", giờ dd/mm/yyyy hh:mm, mỗi ô một giá trị
    # Danh sách theo board W1c không có cột Tổng tiền; số tiền xem ở chi tiết, riêng dòng hoàn tiền ghi "Hoàn <số tiền>" ở cột Lý do
    heads_q = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts()]
    ok("danh sách: không có cột Tổng tiền (board W1c)", "Tổng tiền" not in heads_q, str(heads_q))
    ok("giờ dạng dd/mm/yyyy hh:mm", re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", body) is not None)

    # tab "Gọi báo hoàn tiền"
    pick_tab(page, "Gọi báo hoàn tiền")
    ok("tab Gọi báo hoàn tiền: có ghi chú không ghi số tài khoản", page.get_by_text("Không ghi số tài khoản", exact=False).first.is_visible())
    ok("tab Gọi báo hoàn tiền: có đơn SO260928-9C6B27", row_of(page, "SO260928-9C6B27").count() == 1)
    ok("URL tab chỉ mang ?tab=", re.search(r"[?&]tab=REFUND_CALL$", page.url) is not None, page.url)

    # tab "Tất cả" (FE gộp 4 trạng thái)
    pick_tab(page, "Tất cả")
    allrows = page.locator("table.lt tbody tr").count()
    ok("tab Tất cả: gộp đơn của mọi trạng thái (>= 7 dòng)", allrows >= 7, str(allrows))

    # tab Cần quyết định: CSKH thấy dòng nhưng chi tiết không có Quyết định (kiểm ở mục chi tiết)
    pick_tab(page, "Cần quyết định")
    ok("tab Cần quyết định: có SO260928-A40F28", row_of(page, "SO260928-A40F28").count() == 1)

    # tìm trong danh sách: không ra -> trạng thái rỗng khi tìm
    pick_tab(page, "Tất cả")
    page.locator("input[name=q]").fill("zzzkhongco")
    page.wait_for_timeout(300)
    ok("tìm không ra: có câu 'Không có đơn nào khớp'", page.get_by_text("khớp", exact=False).first.is_visible())
    ok("tìm không ra: có nút xoá tìm kiếm", page.get_by_role("button", name=re.compile("Xoá (tìm|bộ lọc)", re.I)).count() >= 1)
    page.locator("input[name=q]").fill("")
    ok("không có lỗi console ở danh sách", not errors, str(errors[:2]))
    ctx.close()


# ---------------------------------------------------------------- danh sách (Chủ / Quản lý): thấy đủ
def queue_owner(browser):
    for user in ("loc", "ql1"):
        ctx, page, _ = new_page(browser, user)
        go(page, "/confirmation/")
        r_out = row_of(page, "SO260928-1B7A40")
        txt = r_out.inner_text()
        ok(f"{user}: dòng đơn 0040 hiện đủ số (đủ quyền xem)", PHONE_OUT_FULL in txt, txt.replace("\n", "|")[:120])
        ok(f"{user}: dòng đơn 0040 mở được", r_out.locator("a").count() >= 1)
        ctx.close()


# ---------------------------------------------------------------- chi tiết + ghi cuộc gọi (CSKH)
def detail_and_call(browser):
    ctx, page, errors = new_page(browser, "cs2")
    go(page, "/confirmation/")
    row_of(page, "SO260928-3F9A01").locator("a").first.click()
    page.wait_for_url(re.compile(r"/confirmation/detail/\?id=31$"))
    settle(page)
    page.get_by_role("heading", name="SO260928-3F9A01").wait_for()
    ok("chi tiết: URL chỉ mang id số", page.url.endswith("/confirmation/detail/?id=31"), page.url)
    body = page.inner_text("main")
    ok("chi tiết: hiện đủ SĐT khách + nút Gọi khách tel:", PHONE_IN in body and page.locator(f"a.btn[href='tel:{PHONE_IN}']").count() == 1)
    ok("chi tiết: có StatusPath, Thông tin, Lịch sử cuộc gọi", page.get_by_text("Lịch sử cuộc gọi").first.is_visible() and page.get_by_text("Đơn & người nhận", exact=True).first.is_visible() and page.get_by_text("Gọi xác nhận", exact=True).first.is_visible() and page.get_by_text("540.000", exact=False).count() >= 1)
    ok("chi tiết: có dòng thời gian", page.get_by_text("Dòng thời gian", exact=False).count() >= 1)
    ok("AI tắt (mặc định): không có khối Trợ lý AI", page.locator("[data-ai-block]").count() == 0)
    ok("AC5: CSKH không có nút Quyết định", page.get_by_role("button", name="Quyết định", exact=True).count() == 0)
    ok("chi tiết: tổng tiền dạng 'đ'", re.search(r"540\.000\s*đ", body) is not None)

    # F2h: ghi kết quả
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    dlg = dialog(page)
    dlg.wait_for()
    labels = [x.strip() for x in dlg.locator("[class*='pickName']").all_inner_texts()]
    exp = ["Đã xác nhận", "Hẹn gọi lại", "Không nghe máy", "Sai số điện thoại", "Khách muốn đổi món", "Khách muốn huỷ đơn"]
    ok("AC2: hộp ghi kết quả có 6 lựa chọn của đơn mới (Đã báo hoàn tiền ở đơn huỷ)", labels == exp, str(labels))
    # lưu khi chưa chọn gì
    dlg.get_by_role("button", name=re.compile("Lưu kết quả")).click()
    ok("bắt buộc chọn kết quả", dlg.get_by_text("Chọn kết quả", exact=False).first.is_visible(), dlg.inner_text()[:80])
    # hẹn gọi lại thiếu giờ -> AC3
    dlg.get_by_label("Hẹn gọi lại", exact=False).first.check() if dlg.get_by_label("Hẹn gọi lại", exact=False).count() and False else None
    dlg.locator("label", has_text="Hẹn gọi lại").first.click()
    dlg.get_by_role("button", name=re.compile("Lưu kết quả")).click()
    err = dlg.locator("[class*='field'] [role='alert'], .alert-box.err, [id$='-err']").all_inner_texts()
    ok("AC3: thiếu giờ -> 'Chọn thời điểm sau dd/mm/yyyy hh:mm.'", any(re.search(r"Chọn thời điểm sau \d{2}/\d{2}/\d{4} \d{2}:\d{2}\.", e) for e in err) or re.search(r"Chọn thời điểm sau \d{2}/\d{2}/\d{4} \d{2}:\d{2}\.", dlg.inner_text()) is not None, dlg.inner_text()[-200:].replace("\n", "|"))
    # giờ trong quá khứ
    dlg.get_by_label("Hẹn gọi lại lúc").fill("2020-01-01T08:00")
    dlg.get_by_role("button", name=re.compile("Lưu kết quả")).click()
    ok("AC3: giờ quá khứ cũng bị chặn", re.search(r"Chọn thời điểm sau", dlg.inner_text()) is not None)
    # ghi chú có số điện thoại
    dlg.get_by_label("Ghi chú", exact=False).fill("khách đổi số 0912 345 678")
    dlg.get_by_role("button", name=re.compile("Lưu kết quả")).click()
    ok("ghi chú có SĐT bị chặn, không gửi đi", re.search(r"số điện thoại", dlg.inner_text().split("Ghi chú", 1)[-1], re.I) is not None and dialog(page).is_visible())
    dlg.get_by_label("Ghi chú", exact=False).fill("")
    # chọn Không nghe máy, ghi
    dlg.locator("label", has_text="Không nghe máy").first.click()
    dlg.get_by_label("Ghi chú", exact=False).fill("Chuông reo không bắt máy")
    dlg.get_by_role("button", name=re.compile("Lưu kết quả")).click()
    dlg.wait_for(state="detached")
    settle(page)
    ok("ghi 'Không nghe máy': hộp đóng, toast + lịch sử có dòng mới", page.get_by_text("Đã ghi không nghe máy", exact=False).count() >= 1 and page.get_by_text("Chuông reo không bắt máy").count() >= 1)
    ok("lần gọi tăng từ 1/3 lên 2/3", "2/3" in page.inner_text("main"))
    ok("lưu thao tác không để SĐT/tên/địa chỉ ở storage hay URL", PHONE_IN not in storage_dump(page) and "Khách Thử" not in storage_dump(page) and PHONE_IN not in page.url)

    # F2i: Hẹn gọi lại từ menu ...
    page.get_by_role("button", name=re.compile("Thêm|Khác|Hành động", re.I)).first.click()
    page.get_by_role("menuitem", name="Hẹn gọi lại").click()
    dlg = dialog(page)
    dlg.wait_for()
    ok("F2i: hộp Hẹn gọi lại chỉ có ô giờ + ghi chú", dlg.get_by_label("Hẹn gọi lại lúc").count() == 1 and dlg.locator("input[type=radio]").count() == 0)
    dlg.get_by_label("Hẹn gọi lại lúc").fill("2030-01-01T08:00")
    dlg.get_by_role("button", name="Lưu hẹn gọi lại").click()
    dlg.wait_for(state="detached")
    settle(page)
    ok("F2i: hẹn xong, trạng thái Hẹn gọi lại", page.get_by_text("Hẹn gọi lại", exact=False).count() >= 2 and page.get_by_text("01/01/2030 08:00").count() >= 1)

    # F2j: đổi người nhận
    page.get_by_role("button", name=re.compile("Thêm|Khác|Hành động", re.I)).first.click()
    page.get_by_role("menuitem", name=re.compile("Đổi người nhận")).click()
    dlg = dialog(page)
    dlg.wait_for()
    dlg.get_by_label("Tên người nhận").fill("")
    dlg.get_by_label("Số điện thoại người nhận").fill("12345")
    dlg.get_by_role("button", name="Lưu thay đổi").click()
    ok("F2j: tên trống, SĐT sai -> báo lỗi từng ô", "Nhập tên người nhận." in dlg.inner_text() and "Số điện thoại chưa đúng" in dlg.inner_text())
    dlg.get_by_label("Tên người nhận").fill("Anh Bình Thử")
    dlg.get_by_label("Số điện thoại người nhận").fill("0911222333")
    dlg.get_by_role("button", name="Lưu thay đổi").click()
    dlg.wait_for(state="detached")
    settle(page)
    ok("F2j: lưu xong, trang hiện người nhận mới", "Anh Bình Thử" in page.inner_text("main"))
    ok("F2j: tên / SĐT người nhận không nằm ở storage hay URL", "Anh Bình Thử" not in storage_dump(page) and "0911222333" not in storage_dump(page) and "Bình" not in page.url)
    ok("không có lỗi console ở chi tiết", not errors, str(errors[:2]))
    page.screenshot(path=os.path.join(SHOTS, "ed5-detail-1280.png"), full_page=True)
    ctx.close()


# ---------------------------------------------------------------- khối Trợ lý AI
def ai_block(browser):
    ctx, page, _ = new_page(browser, "cs2")
    page.wait_for_function("() => typeof window.__caveMock.ai === 'function'")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); }")
    go(page, "/confirmation/detail/?id=31")
    block = page.locator("[data-ai-block]")
    block.wait_for()
    chips = [t.strip() for t in block.locator("[data-ai-starter] button").all_inner_texts()]
    ok("AI bật: khối Trợ lý có chip theo ngữ cảnh cuộc gọi", any("cuộc gọi" in c for c in chips) and any("hẹn gọi lại" in c.lower() for c in chips), str(chips))
    ok("AI: chip không chứa tên / SĐT / địa chỉ khách", not any(re.search(r"\d{9,}|Khách Thử|Đường Thử", c) for c in chips))
    ok("AI: URL và storage không mang dữ liệu khách", PHONE_IN not in page.url and PHONE_IN not in storage_dump(page))
    ctx.close()


# ---------------------------------------------------------------- chi tiết ngoài phạm vi / id sai
def detail_edges(browser):
    ctx, page, _ = new_page(browser, "cs2")
    go(page, "/confirmation/detail/?id=40")
    ok("CSKH mở đơn ngoài phạm vi: 'Không tìm thấy', không lộ số", page.get_by_role("heading", name="Không tìm thấy trang này").is_visible() and PHONE_OUT_FULL not in page.inner_text("body"))
    go(page, "/confirmation/detail/?id=99999")
    ok("id không có: Không tìm thấy", page.get_by_role("heading", name="Không tìm thấy trang này").is_visible())
    go(page, "/confirmation/detail/?id=abc")
    ok("id chữ: Không tìm thấy", page.get_by_role("heading", name="Không tìm thấy trang này").is_visible())
    go(page, "/confirmation/detail/")
    ok("thiếu id: Không tìm thấy", page.get_by_role("heading", name="Không tìm thấy trang này").is_visible())
    # AC5 với đơn Cần quyết định
    go(page, "/confirmation/detail/?id=28")
    page.get_by_role("heading", name="SO260928-A40F28").wait_for()
    ok("AC5: CSKH mở đơn chờ quyết định: không có Quyết định, có câu chờ Chủ / Quản lý", page.get_by_role("button", name="Quyết định", exact=True).count() == 0 and page.get_by_text("chờ Chủ hoặc Quản lý quyết định", exact=False).count() >= 1)
    # đơn đã huỷ cần gọi báo hoàn tiền: kết quả "Đã báo hoàn tiền"
    go(page, "/confirmation/detail/?id=27")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    dlg = dialog(page)
    dlg.wait_for()
    labels = [x.strip() for x in dlg.locator("[class*='pickName']").all_inner_texts()]
    ok("AC2: đơn gọi báo hoàn tiền có 'Đã báo hoàn tiền'", "Đã báo hoàn tiền" in labels and "Đã xác nhận" not in labels, str(labels))
    ctx.close()


# ---------------------------------------------------------------- 409 CLAIMED / STALE
def conflicts(browser):
    ctx, page, _ = new_page(browser, "cs2")
    go(page, "/confirmation/detail/?id=30")
    page.get_by_role("heading", name="SO260928-B27C30").wait_for()
    page.evaluate("() => window.__caveMock.confirmationClaimByOther(30)")
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    page.get_by_text("đang được Chị Lan xử lý", exact=False).first.wait_for()
    ok("409 CLAIMED: hiện đúng câu của BE, hộp ghi không mở", page.get_by_text("đang được Chị Lan xử lý", exact=False).first.is_visible() and dialog(page).count() == 0)
    ok("409 CLAIMED: không hiện ConflictBanner 'Tải lại'", page.get_by_role("button", name="Tải lại").count() == 0)
    ok("409 CLAIMED: không có nút Quyết định / nút bị khoá để ghi", page.get_by_role("button", name="Quyết định", exact=True).count() == 0)

    # đơn 41 đang có người giữ từ đầu
    go(page, "/confirmation/detail/?id=41")
    page.get_by_role("heading", name="SO260928-C05E41").wait_for()
    ok("đơn đang có người giữ: banner cảnh báo ngay khi mở", page.get_by_text("đang được Chị Lan xử lý", exact=False).count() >= 1)
    ok("đơn đang có người giữ: không có nút Ghi kết quả gọi (BE không trả quyền gọi)", page.get_by_role("button", name="Ghi kết quả gọi").count() == 0)
    ok("đơn đang có người giữ: không có nút Quyết định", page.get_by_role("button", name="Quyết định", exact=True).count() == 0)

    # STALE_STATE: job tự huỷ chạy giữa chừng
    go(page, "/confirmation/detail/?id=36")
    page.get_by_role("heading", name="SO260928-E83D36").wait_for()
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    dlg = dialog(page)
    dlg.wait_for()
    page.evaluate("() => window.__caveMock.confirmationArmStale(36)")
    dlg.locator("label", has_text="Đã xác nhận").first.click()
    dlg.get_by_role("button", name=re.compile("Lưu kết quả")).click()
    dlg.get_by_role("button", name="Tải lại").wait_for()
    ok("409 STALE_STATE: hộp giữ nguyên, có 'Tải lại', hiện câu của BE", dlg.get_by_role("alert").count() >= 1 and dlg.get_by_role("button", name="Tải lại").is_visible())
    dlg.get_by_role("button", name="Tải lại").click()
    dlg.wait_for(state="detached")
    settle(page)
    ok("Tải lại: hộp đóng, trang nạp lại", dialog(page).count() == 0 and page.get_by_role("heading", name="SO260928-E83D36").is_visible())
    ctx.close()


# ---------------------------------------------------------------- Quyết định (Chủ / Quản lý)
def decisions(browser):
    for user in ("loc", "ql1"):
        ctx, page, _ = new_page(browser, user)
        go(page, "/confirmation/detail/?id=28")
        page.get_by_role("heading", name="SO260928-A40F28").wait_for()
        btn = page.get_by_role("button", name="Quyết định", exact=True)
        ok(f"AC4 {user}: có nút Quyết định ở đơn chờ quyết định", btn.count() == 1)
        btn.click()
        dlg = dialog(page)
        dlg.wait_for()
        labels = [x.strip() for x in dlg.locator("[class*='pickName']").all_inner_texts()]
        ok(f"AC4 {user}: 3 lựa chọn đúng tên", labels == ["Giao không xác nhận", "Gia hạn thêm", "Huỷ đơn"], str(labels))
        ok(f"AC4 {user}: lựa chọn Huỷ đơn được đánh dấu nguy hiểm", dlg.locator("[class*='pickDanger']").count() == 1)
        dlg.get_by_role("button", name="Lưu quyết định").click()
        ok(f"AC4 {user}: chưa chọn thì báo lỗi, hộp còn mở", dialog(page).is_visible() and re.search(r"Chọn", dlg.inner_text()) is not None)
        # gia hạn thiếu giờ
        dlg.locator("label", has_text="Gia hạn thêm").first.click()
        dlg.get_by_role("button", name="Lưu quyết định").click()
        ok(f"AC4 {user}: gia hạn thiếu giờ -> lỗi từ ô giờ", re.search(r"Chọn thời điểm", dlg.inner_text()) is not None)
        # huỷ đơn: nút đỏ + xác nhận hai bước
        dlg.locator("label", has_text="Huỷ đơn").first.click()
        dlg.get_by_label("không ghi số điện thoại", exact=False).fill("Khách không nghe máy ba lần")
        red = dlg.locator("button.danger")
        ok(f"AC4 {user}: nút Huỷ đơn màu đỏ (btn danger)", red.count() == 1, dlg.locator(".btn").all_inner_texts().__str__())
        red.click()
        ok(f"AC4 {user}: lần bấm đầu chỉ hỏi lại, chưa huỷ", dialog(page).is_visible() and "Xác nhận huỷ đơn" in dlg.inner_text() and "/orders/" not in page.url)
        if user == "loc":
            dlg.locator("button.danger").click()
            page.wait_for_url(re.compile(r"/orders/\?order=\d+&open=refund"), timeout=10_000)
            ok("AC4 loc: huỷ xong chuyển sang hoàn tiền của đơn", True, page.url)
        else:
            # ql1: quay lại, chọn Giao không xác nhận
            dlg.get_by_role("button", name="Quay lại").click()
            dlg.locator("label", has_text="Giao không xác nhận").first.click()
            dlg.get_by_role("button", name="Lưu quyết định").click()
            dlg.wait_for(state="detached")
            settle(page)
            ok("AC4 ql1: giao không xác nhận -> đơn sang Soạn hàng", page.get_by_text("Soạn hàng", exact=False).count() >= 1)
        ctx.close()


# ---------------------------------------------------------------- tìm khách
def search_customer(browser):
    ctx, page, _ = new_page(browser, "cs2")
    go(page, "/confirmation/")
    page.get_by_role("button", name="Tìm khách gọi lại").click()
    dlg = dialog(page)
    dlg.wait_for()
    dlg.get_by_role("button", name=re.compile("Tìm", re.I)).last.click()
    ok("tìm khách: để trống -> báo nhập", "Nhập số điện thoại" in dlg.inner_text())
    dlg.get_by_label("Số điện thoại hoặc mã đơn").fill("0912")
    dlg.get_by_role("button", name=re.compile("Tìm", re.I)).last.click()
    ok("tìm khách: SĐT quá ngắn bị chặn, chưa gửi", "ít nhất 9 chữ số" in dlg.inner_text())
    dlg.get_by_label("Số điện thoại hoặc mã đơn").fill(PHONE_OUT_FULL)
    dlg.get_by_role("button", name=re.compile("Tìm", re.I)).last.click()
    page.wait_for_timeout(500)
    txt = dlg.inner_text()
    ok("tìm khách: đơn ngoài phạm vi hiện số đã che, không hiện tên / số đủ", PHONE_OUT_MASK in txt and PHONE_OUT_FULL not in txt and "Khách Thử K" not in txt, txt.replace("\n", "|")[:200])
    ok("tìm khách: từ khoá không nằm ở URL / storage", PHONE_OUT_FULL not in page.url and PHONE_OUT_FULL not in storage_dump(page))
    dlg.get_by_label("Số điện thoại hoặc mã đơn").fill("0999999999")
    dlg.get_by_role("button", name=re.compile("Tìm", re.I)).last.click()
    page.wait_for_timeout(500)
    ok("tìm khách: không thấy -> câu rỗng", re.search(r"Không (thấy|tìm thấy|có)", dlg.inner_text()) is not None, dlg.inner_text()[-150:].replace("\n", "|"))
    ctx.close()


# ---------------------------------------------------------------- 360px
def mobile(browser):
    ctx, page, errors = new_page(browser, "cs2", 360, 740)
    go(page, "/confirmation/")
    ok("360px: danh sách không cuộn ngang trang", no_hscroll(page))
    ok("360px: bảng nằm trong vùng cuộn của thẻ", page.eval_on_selector("table.lt", "e => !!e.closest('.lt-scroll')"))
    page.screenshot(path=os.path.join(SHOTS, "ed5-queue-360.png"), full_page=True)
    go(page, "/confirmation/detail/?id=31")
    page.get_by_role("heading", name="SO260928-3F9A01").wait_for()
    ok("360px: chi tiết không cuộn ngang", no_hscroll(page))
    small = page.eval_on_selector_all("main .btn, main a.btn", "els => els.filter(e => e.offsetParent !== null).map(e => [e.textContent.trim(), Math.round(e.getBoundingClientRect().height)]).filter(x => x[1] < 40)")
    ok("360px: nút ở chi tiết cao >= 40px", not small, str(small[:3]))
    page.screenshot(path=os.path.join(SHOTS, "ed5-detail-360.png"), full_page=True)
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    dialog(page).wait_for()
    ok("360px: hộp ghi kết quả không cuộn ngang", no_hscroll(page))
    box = page.eval_on_selector("[role=dialog]", "e => { const r = e.getBoundingClientRect(); return [r.left, r.right, window.innerWidth]; }")
    ok("360px: hộp nằm gọn trong màn hình", box[0] >= -1 and box[1] <= box[2] + 1, str(box))
    page.screenshot(path=os.path.join(SHOTS, "ed5-call-modal-360.png"))
    ok("360px: không có lỗi console", not errors, str(errors[:2]))
    ctx.close()


# ---------------------------------------------------------------- vòng sửa sau review (TL5-M1/L1, QA-B1..B9)
def push(page, path):
    page.evaluate("p => window.next.router.push(p)", path)
    page.wait_for_load_state("networkidle")
    settle(page)


def fix_round(browser):
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/confirmation/")
    # B1/B3/B8: cột theo board W1c, vừa khung 1280, "Tổng số kg"
    pick_tab(page, "Tất cả")
    heads = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts()]
    ok("B1/B3 cột đúng thứ tự board W1c", heads == ["Mã đơn", "Khách hàng", "Số điện thoại", "Hàng", "Tổng số kg", "Trạng thái", "Lý do", "Hạn gọi", "Đang gọi", "Lần gọi"], str(heads))
    sc = page.evaluate("() => { const s = document.querySelector('.lt-scroll'); return [s.scrollWidth, s.clientWidth] }")
    ok("B3 1280px: bảng không cuộn ngang", sc[0] <= sc[1] + 1, str(sc))
    chip = page.locator("table.lt tbody tr .stat-chip").first.bounding_box()
    ok("B3 1280px: chip Trạng thái trong khung nhìn", chip and chip["x"] + chip["width"] <= 1280, str(chip))
    cut = page.evaluate("""() => [...document.querySelectorAll('table.lt tbody tr td')].filter(td => td.scrollWidth > td.clientWidth + 1 && /^(\\d{2}\\/|—|\\d+\\/\\d+$)/.test(td.innerText.trim())).map(td => td.innerText.trim())""")
    ok("B3 ô giờ, số lần gọi không bị cắt chữ", not cut, str(cut[:3]))
    page.screenshot(path=os.path.join(SHOTS, "ed5-fix-queue-all-1280.png"))
    ok("B8 không còn chữ 'Tổng kg'", "Tổng kg" not in page.inner_text("main"))
    pick_tab(page, "Cần quyết định")
    cells = [c.strip() for c in row_of(page, "SO260928-A40F28").locator("td").all_inner_texts()]
    ok("B1 tab Cần quyết định: ô Lý do ghi 'Không nghe máy'", cells[6] == "Không nghe máy", str(cells))
    pick_tab(page, "Gọi báo hoàn tiền")
    cells = [c.strip() for c in row_of(page, "SO260928-9C6B27").locator("td").all_inner_texts()]
    ok("B1 tab Gọi báo hoàn tiền: ô Lý do ghi 'Hoàn 280.000 đ'", re.fullmatch(r"Hoàn 280\.000\s*đ", cells[6]) is not None, str(cells))

    # B5/B8/B9: chi tiết đơn Cần quyết định
    go(page, "/confirmation/detail/?id=28")
    page.get_by_role("heading", name="SO260928-A40F28").wait_for()
    steps = [re.sub(r"^check\s*", "", x.strip()) for x in page.locator("ol li[data-state]").all_inner_texts()]
    ok("B5 thanh trạng thái: Chờ gọi > Cần quyết định > Hoàn tất", steps == ["Chờ gọi", "Cần quyết định", "Hoàn tất"], str(steps))
    now = page.locator("li[data-state='current']").all_inner_texts()
    ok("B5 bước hiện tại là 'Cần quyết định', khớp chip", [x.strip() for x in now] == ["Cần quyết định"] and page.locator("header .stat-chip, main .stat-chip").first.inner_text().strip() == "Cần quyết định", str(now))
    main = page.inner_text("main")
    ok("B5 'Tiếp theo' nêu hạn quyết định", "Chọn giao không xác nhận, gia hạn gọi thêm hoặc huỷ đơn trước 28/09/2026 09:55" in main)
    ok("B5 'Đã làm': Khách trả tiền, Gọi 3 lần", "Khách trả tiền" in main and "Gọi 3 lần" in main)
    for lab in ("Người nhận", "Phiếu giao", "Người gọi", "Hạn quyết định", "Tổng số kg"):
        ok(f"B9/B8 chi tiết có trường '{lab}'", page.get_by_text(lab, exact=True).count() >= 1)
    ok("B8 chi tiết không còn 'Tổng khối lượng'", "Tổng khối lượng" not in main)
    ok("B9 'Người gọi' là người ghi cuộc gọi gần nhất", re.search(r"Người gọi\s*\n?\s*CSKH Thử", main) is not None)

    # B2 (phần FE): dòng thời gian trả 403 / 404
    page.evaluate("window.__caveMock.guidanceForceDeliveryStatus(403)")
    push(page, "/confirmation/detail/?id=31")
    page.get_by_text("Bạn không có quyền xem lịch sử này.").wait_for()
    sec = page.locator("section[aria-label='Dòng thời gian']")
    ok("B2 403: câu 'Bạn không có quyền xem lịch sử này.', không nút Thử lại", sec.get_by_role("button").count() == 0 and "Chưa tải được" not in page.inner_text("body"))
    page.screenshot(path=os.path.join(SHOTS, "ed5-fix-history-403.png"))
    page.evaluate("window.__caveMock.guidanceForceDeliveryStatus(404)")
    push(page, "/confirmation/detail/?id=30")
    page.get_by_text("Không tìm thấy lịch sử của đơn này.").wait_for()
    ok("B2 404: câu 'Không tìm thấy lịch sử của đơn này.', không nút Thử lại", page.locator("section[aria-label='Dòng thời gian']").get_by_role("button").count() == 0)
    page.evaluate("window.__caveMock.guidanceForceDeliveryStatus(null)")

    # B6/B7: hộp F2h, F2k: không chữ gợi ý, có bộ đếm, trả focus
    push(page, "/confirmation/detail/?id=31")
    page.get_by_role("heading", name="SO260928-3F9A01").wait_for()
    btn = page.get_by_role("button", name="Ghi kết quả gọi")
    btn.focus()
    page.keyboard.press("Enter")
    dlg = dialog(page)
    dlg.wait_for()
    names = [x.strip() for x in dlg.locator("[class*='pickName']").all_inner_texts()]
    metas = dlg.locator("[class*='pickMeta']").count()
    ok("B6 F2h: 6 lựa chọn, chỉ tên, không dòng gợi ý xám", len(names) == 6 and metas == 0 and "Khách đồng ý nhận hàng" not in dlg.inner_text(), str(names))
    ok("B6 F2h: ô ghi chú có bộ đếm 0/200", "0/200" in dlg.inner_text())
    dlg.get_by_label("Ghi chú", exact=False).fill("khách hẹn chiều")
    ok("B6 F2h: bộ đếm theo số ký tự đã gõ", "15/200" in dlg.inner_text(), dlg.inner_text()[-80:])
    page.screenshot(path=os.path.join(SHOTS, "ed5-fix-F2h.png"))
    page.keyboard.press("Escape")
    dlg.wait_for(state="detached")
    ae = page.evaluate("() => (document.activeElement && document.activeElement.textContent || '').trim()")
    ok("B7 Esc đóng F2h: focus về nút 'Ghi kết quả gọi'", ae in ("Ghi kết quả gọi", "Đang giữ đơn…"), ae)
    btn.click()
    dialog(page).wait_for()
    dialog(page).get_by_role("button", name="Quay lại").click()
    dialog(page).wait_for(state="detached")
    ae = page.evaluate("() => (document.activeElement && document.activeElement.textContent || '').trim()")
    ok("B7 Quay lại đóng F2h (mở bằng chuột): focus về nút 'Ghi kết quả gọi'", ae == "Ghi kết quả gọi", ae)

    push(page, "/confirmation/detail/?id=28")
    page.get_by_role("heading", name="SO260928-A40F28").wait_for()
    dbtn = page.get_by_role("button", name="Quyết định", exact=True)
    dbtn.click()
    dlg = dialog(page)
    dlg.wait_for()
    ok("B6 F2k: 3 lựa chọn, không dòng gợi ý xám", dlg.locator("[class*='pickName']").count() == 3 and dlg.locator("[class*='pickMeta']").count() == 0 and "Kho vẫn soạn" not in dlg.inner_text())
    dlg.locator("label", has_text="Giao không xác nhận").first.click()
    ok("B6 F2k: ô ghi chú có bộ đếm 0/200", "0/200" in dlg.inner_text())
    page.screenshot(path=os.path.join(SHOTS, "ed5-fix-F2k.png"))
    page.keyboard.press("Escape")
    dlg.wait_for(state="detached")
    ae = page.evaluate("() => (document.activeElement && document.activeElement.textContent || '').trim()")
    ok("B7 Esc đóng F2k: focus về nút 'Quyết định'", ae == "Quyết định", ae)

    # TL5-L1: tải lại lỗi thì giữ dữ liệu cũ + cảnh báo (không thay bằng màn lỗi)
    page.evaluate("window.__caveMock.confirmationArmStale(28)")
    dbtn.click()
    dlg = dialog(page)
    dlg.wait_for()
    dlg.locator("label", has_text="Giao không xác nhận").first.click()
    dlg.get_by_label("không ghi số điện thoại", exact=False).fill("Giao luôn")
    dlg.get_by_role("button", name="Lưu quyết định").click()
    dlg.get_by_role("button", name="Tải lại").wait_for()
    page.evaluate("window.__caveMock.confirmationFailNextDetail(1)")
    dlg.get_by_role("button", name="Tải lại").click()
    page.get_by_text("Chưa tải lại được đơn", exact=False).wait_for()
    ok("L1 tải lại lỗi: còn nguyên dữ liệu đơn cũ + cảnh báo, không ra màn lỗi", page.get_by_role("heading", name="SO260928-A40F28").is_visible() and page.locator("li[data-state='current']").count() == 1)
    ok("không có lỗi console ngoài các lỗi chủ ý", not [e for e in errors if "500" not in e and "403" not in e and "404" not in e], str(errors[:2]))
    ctx.close()

    # B4: ô tìm >= 44px ở 360px (gốc ở FilterBar dùng chung, nên /deliveries/ cũng đạt)
    ctx, page, _ = new_page(browser, "ql1", 360, 740)
    for path in ("/confirmation/", "/deliveries/"):
        go(page, path)
        h = page.eval_on_selector("input[name=q]", "e => Math.round(e.getBoundingClientRect().height)")
        hb = page.eval_on_selector("input[name=q]", "e => Math.round(e.closest('.fb-search').getBoundingClientRect().height)")
        ok(f"B4 360px {path}: ô tìm cao >= 44px", h >= 43.5 and hb >= 43.5, f"input {h}, khung {hb}")
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for fn in (role_access, queue_customer_service, queue_owner, detail_and_call, ai_block, detail_edges, conflicts, decisions, search_customer, mobile, fix_round):
        try:
            fn(browser)
        except Exception as exc:  # một nhóm lỗi không làm mất kết quả các nhóm khác
            ok(f"{fn.__name__}: chạy không ném lỗi", False, repr(exc)[:300])
    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} đạt")
sys.exit(1 if failed else 0)
