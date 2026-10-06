# E2E CSKH Lô 5 FE (CS-16 phiếu soạn, CS-17 quét mã tem, CS-18 kịch bản gọi): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3201 &)
#   BASE=http://127.0.0.1:3201 SHOTS=<thư mục ảnh> python3 e2e/confirmation_scripts_tag_lookup.py      # tắt server và xoá out/ sau khi xong
# Kiểm: phân quyền 5 vai (loc, ql1, kho1, giao1, cs1) cho 3 màn · DOM phiếu soạn không có tên, SĐT, địa chỉ, ghi chú đơn, giá, khổ 100x150 mm
# · NV giao và CSKH thấy "Không có quyền" và KHÔNG có request chi tiết phiếu nào (CS-16-AC4) · mã tem sai (SĐT, thiếu số) bị chặn ở máy khách,
# không có request lookup · tem cũ (vàng), đơn huỷ (đỏ), 404, tem còn hiệu lực mở thẳng phiếu · máy quét USB (gõ + Enter) · camera giả (BarcodeDetector)
# · kịch bản có SĐT bị chặn, không có POST · Chủ soạn, tắt, và chi tiết gọi hiện/ẩn kịch bản · không request /api/ai/ · 360px và 1280px không cuộn ngang
# · dữ liệu khách không nằm ở localStorage / URL / console.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3201")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)

# Chữ bịa của mock (features/deliveries/mock.ts, phiếu 31).
PII_STRINGS = ["Khách Thử A", "Đường Thử", "Lâm Đồng", "Giao trước 11h", "0900 000 031", "0900000031", "DH-260928-0001"]
PHONE_TYPO = "0900000123"


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


def new_page(browser, user, w=1280, h=860, errors=None, **ctx_args):
    errors = errors if errors is not None else []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", **ctx_args)
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and "HTTP" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, user)
    return ctx, page, errors


def log_of(page):
    return page.evaluate("() => [...window.__caveMock.log]")


def no_permission(page):
    return page.get_by_text("Bạn không có quyền xem mục này").count() > 0


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])")


def body_text(page):
    return page.evaluate("() => document.body.innerText")


def lookup(page, code):
    box = page.get_by_label("Mã tem")
    box.fill(code)
    box.press("Enter")  # máy quét USB gõ như bàn phím rồi nhấn Enter
    page.wait_for_load_state("networkidle")
    settle(page)


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    errors = []

    # ---------------- Phân quyền 5 vai ----------------
    # loc: cả ba việc, soạn được kịch bản.
    ctx, page, _ = new_page(browser, "loc", errors=errors)
    go(page, "/deliveries/")
    ok("loc: Giao hàng có nút Quét mã tem", page.get_by_role("link", name="Quét mã tem").count() == 1)
    go(page, "/deliveries/lookup/")
    ok("loc: mở được màn Quét mã tem", page.get_by_label("Mã tem").count() == 1 and not no_permission(page))
    go(page, "/confirmation/")
    ok("loc: Gọi xác nhận có nút Kịch bản gọi", page.get_by_role("link", name="Kịch bản gọi").count() == 1)
    go(page, "/confirmation/scripts/")
    ok("loc: Kịch bản gọi có nút Sửa và công tắc Tắt", page.get_by_role("button", name="Sửa").count() >= 1 and page.get_by_role("button", name="Tắt", exact=True).count() >= 1)
    ok("loc: tình huống chưa soạn có nút Soạn kịch bản", page.get_by_role("button", name="Soạn kịch bản").count() >= 1)
    ctx.close()

    # ql1: tra tem được; kịch bản chỉ đọc.
    ctx, page, _ = new_page(browser, "ql1", errors=errors)
    go(page, "/deliveries/lookup/")
    ok("ql1: mở được màn Quét mã tem", page.get_by_label("Mã tem").count() == 1)
    go(page, "/confirmation/scripts/")
    ok("ql1: Kịch bản gọi chỉ đọc (không Sửa, không Soạn, không Tắt)",
       page.get_by_role("heading", name="Kịch bản gọi").count() >= 1
       and page.get_by_role("button", name="Sửa").count() == 0
       and page.get_by_role("button", name="Soạn kịch bản").count() == 0
       and page.get_by_role("button", name="Tắt", exact=True).count() == 0)
    txt = body_text(page)
    ok("ql1: chỉ thấy kịch bản đang bật (không có Đã tắt, không có Đơn có combo)", "Đã tắt" not in txt and "Đơn có combo" not in txt)
    ok("ql1: thấy nội dung kịch bản", "Rã đông" in txt)
    go(page, "/print/pick-sheet/?note=31")
    page.wait_for_selector("[data-testid=pick-sheet]")
    ok("ql1: mở được phiếu soạn", True)
    ctx.close()

    # kho1: tra tem + phiếu soạn được; kịch bản bị chặn.
    ctx, page, _ = new_page(browser, "kho1", errors=errors)
    go(page, "/deliveries/lookup/")
    ok("kho1: mở được màn Quét mã tem", page.get_by_label("Mã tem").count() == 1)
    go(page, "/confirmation/scripts/")
    ok("kho1: Kịch bản gọi -> Không có quyền", no_permission(page))
    ok("kho1: không gọi API kịch bản", not any("/scripts/" in r for r in log_of(page)), str(log_of(page)))
    ctx.close()

    # giao1: không tra tem, không phiếu soạn (dù API chi tiết trả 200 cho phiếu của mình), không kịch bản.
    ctx, page, _ = new_page(browser, "giao1", errors=errors)
    go(page, "/deliveries/lookup/")
    ok("giao1: Quét mã tem -> Không có quyền", no_permission(page))
    go(page, "/confirmation/scripts/")
    ok("giao1: Kịch bản gọi -> Không có quyền", no_permission(page))
    # Phiếu 33 gán cho giao1: chi tiết trả 200 cho họ. Trang phiếu soạn vẫn phải chặn và không gọi chi tiết.
    go(page, "/print/pick-sheet/?note=33")
    page.wait_for_selector("text=Không có quyền")
    ok("giao1: phiếu soạn của chính phiếu mình -> Không có quyền (CS-16-AC4)", page.get_by_role("heading", name="Không có quyền").count() == 1)
    ok("giao1: không có request chi tiết phiếu nào", not any("/api/delivery/notes/" in r for r in log_of(page)), str(log_of(page)))
    ok("giao1: DOM không có phiếu soạn", page.locator("[data-testid=pick-sheet]").count() == 0)
    ctx.close()

    # cs1: kịch bản chỉ đọc; không tra tem, không phiếu soạn.
    ctx, page, _ = new_page(browser, "cs1", errors=errors)
    go(page, "/deliveries/")
    ok("cs1: Giao hàng không có nút Quét mã tem", page.get_by_role("link", name="Quét mã tem").count() == 0)
    go(page, "/deliveries/lookup/")
    ok("cs1: Quét mã tem -> Không có quyền", no_permission(page))
    go(page, "/print/pick-sheet/?note=31")
    page.wait_for_selector("text=Không có quyền")
    ok("cs1: phiếu soạn -> Không có quyền, không request chi tiết", page.get_by_role("heading", name="Không có quyền").count() == 1 and not any("/api/delivery/notes/" in r for r in log_of(page)))
    go(page, "/confirmation/scripts/")
    ok("cs1: Kịch bản gọi chỉ đọc", page.get_by_role("button", name="Sửa").count() == 0 and page.get_by_role("button", name="Soạn kịch bản").count() == 0 and "Rã đông" in body_text(page))
    # CS-18-AC1: chi tiết gọi của khách lần đầu hiện kịch bản.
    go(page, "/confirmation/detail/?id=31")
    page.wait_for_selector("text=Kịch bản gọi")
    sec = page.get_by_role("region", name="Kịch bản gọi")
    ok("cs1: chi tiết gọi hiện kịch bản Khách mua lần đầu (AC1)", "Khách mua lần đầu" in sec.inner_text() and "Chào anh/chị, em gọi từ Cá Về" in sec.inner_text())
    ok("cs1: kịch bản đã tắt (Đơn có combo) không hiện", "Đơn có combo" not in sec.inner_text())
    ctx.close()

    # ---------------- CS-16: phiếu soạn ----------------
    ctx, page, _ = new_page(browser, "kho1", errors=errors)
    go(page, "/print/pick-sheet/?note=31")
    page.wait_for_selector("[data-testid=pick-sheet]")
    sheet = page.locator("[data-testid=pick-sheet]")
    html = page.content()
    text = body_text(page)
    ok("pick-sheet: có mã phiếu, 2 dòng hàng, kg, mã lô, HSD",
       "GH-HD-0031-PREP" in text and "Tôm sú loại 1" in text and "Mực lá Phan Thiết" in text and "2,5 kg" in text and "TOM-SU-1-260920-AB12C" in text and "HSD 20/09/2027" in text and "3,5 kg" in text)
    leaks = [p for p in PII_STRINGS if p in html or p in text]
    ok("pick-sheet: DOM không có tên, SĐT, địa chỉ, ghi chú đơn, mã đơn (AC2)", not leaks, str(leaks))
    ok("pick-sheet: DOM không có giá (đ, ₫, giá)", not re.search(r"\d\s?(đ|₫)|giá|VNĐ", text, re.I))
    ok("pick-sheet: khổ giấy 100x150 mm trong @page", "100mm 150mm" in html)
    w = sheet.evaluate("el => el.getBoundingClientRect().width")
    ok("pick-sheet: bề ngang tờ ≈ 100 mm (378 px)", 370 <= w <= 386, str(w))
    ok("pick-sheet: URL chỉ mang id phiếu", page.url.endswith("/print/pick-sheet/?note=31"))
    ok("pick-sheet: không dữ liệu khách ở localStorage", not any(p in storage_dump(page) for p in PII_STRINGS))
    page.screenshot(path=f"{SHOTS}/pick-sheet-1280.png", full_page=True)
    # Trạng thái khác Soạn hàng
    go(page, "/print/pick-sheet/?note=47")
    page.wait_for_selector("text=Đơn đã huỷ, không soạn, xé tem.")
    ok("pick-sheet: phiếu huỷ -> cảnh báo đỏ, không có phiếu", page.locator(".alert-box.err").count() == 1 and page.locator("[data-testid=pick-sheet]").count() == 0)
    go(page, "/print/pick-sheet/?note=30")
    page.wait_for_selector("text=chưa xác nhận với khách")
    ok("pick-sheet: phiếu chưa xác nhận -> cảnh báo vàng", page.locator(".alert-box.warn").count() == 1)
    go(page, "/print/pick-sheet/?note=999")
    page.wait_for_selector("text=Không tìm thấy phiếu")
    ok("pick-sheet: phiếu không có -> Không tìm thấy phiếu", True)
    go(page, "/print/pick-sheet/")
    page.wait_for_selector("text=thiếu mã phiếu")
    ok("pick-sheet: thiếu ?note -> báo thiếu mã phiếu", True)
    # Nút mở từ chi tiết phiếu giao
    go(page, "/deliveries/detail/?id=31")
    page.wait_for_selector("h2:has-text('GH-HD-0031-PREP')")
    page.get_by_role("button", name="Thao tác khác").click()
    with page.expect_popup() as pop:
        page.get_by_role("menuitem", name="In phiếu soạn").click()
    popup = pop.value
    popup.wait_for_load_state()
    ok("detail: menu … có In phiếu soạn, mở tab /print/pick-sheet/?note=31", popup.url.endswith("/print/pick-sheet/?note=31"), popup.url)
    popup.close()
    # Phiếu đã đóng gói: không có mục In phiếu soạn
    go(page, "/deliveries/detail/?id=32")
    page.wait_for_selector("h2:has-text('GH-HD-0032-READY')")
    page.get_by_role("button", name="Thao tác khác").click()
    ok("detail: phiếu Chờ lấy không có mục In phiếu soạn", page.get_by_role("menuitem", name="In phiếu soạn").count() == 0)
    ctx.close()

    # ---------------- CS-17: quét / gõ mã tem ----------------
    ctx, page, _ = new_page(browser, "kho1", errors=errors)
    go(page, "/deliveries/lookup/")
    page.get_by_label("Mã tem").wait_for()
    ok("lookup: ô mã tem tự focus (máy quét USB gõ ngay được)", page.evaluate("() => document.activeElement && document.activeElement.name === 'tag-code'"))
    page.evaluate("() => window.__caveMock.clearLog()")
    # SĐT gõ nhầm: chặn ở máy khách, KHÔNG có request lookup (QA L1)
    lookup(page, PHONE_TYPO)
    ok("lookup: SĐT gõ nhầm bị chặn, có lỗi dưới ô", page.get_by_text("Mã tem không đúng").count() >= 1)
    ok("lookup: SĐT gõ nhầm KHÔNG lên request nào", not any("lookup" in r for r in log_of(page)), str(log_of(page)))
    ok("lookup: câu lỗi không lặp lại SĐT đã gõ", PHONE_TYPO not in page.locator("main, body").first.inner_text().replace(page.get_by_label("Mã tem").input_value(), ""))
    lookup(page, "GH-HD-0032-READY")
    ok("lookup: thiếu .số lần in bị chặn, không request", not any("lookup" in r for r in log_of(page)))
    lookup(page, "")
    ok("lookup: ô trống -> 'Nhập hoặc quét mã trên tem.'", page.get_by_text("Nhập hoặc quét mã trên tem.").count() >= 1)
    # 404
    lookup(page, "GH-HD-9999-NONE.1")
    page.wait_for_selector("text=Không tìm thấy phiếu")
    ok("lookup: mã không có phiếu -> Không tìm thấy phiếu (404)", page.get_by_role("alert").filter(has_text="Không tìm thấy phiếu").count() == 1)
    ok("lookup: sau 404 ô mã vẫn focus để quét tiếp", page.evaluate("() => document.activeElement && document.activeElement.name === 'tag-code'"))
    page.screenshot(path=f"{SHOTS}/lookup-404-1280.png")
    # Tem cũ: vàng + nút Mở phiếu
    lookup(page, "GH-HD-0046-REPR.1")
    page.wait_for_selector("[data-testid=lookup-result]")
    alert = page.locator("[data-testid=lookup-result] .alert-box")
    ok("lookup: tem cũ -> cảnh báo VÀNG 'dùng tem lần 2'", "warn" in alert.get_attribute("class") and "Tem này không còn hiệu lực, dùng tem lần 2." in alert.inner_text())
    ok("lookup: tem cũ không hiện mã luật BR-", "BR-" not in body_text(page))
    page.screenshot(path=f"{SHOTS}/lookup-old-tag-1280.png")
    page.get_by_role("button", name="Mở phiếu").click()
    page.wait_for_url(re.compile(r"/deliveries/detail/\?id=46$"))
    ok("lookup: Mở phiếu -> chi tiết phiếu 46", True)
    # Đơn huỷ: đỏ
    go(page, "/deliveries/lookup/")
    lookup(page, "gh-hd-0047-canc.1")  # chữ thường: chuẩn hoá sang hoa
    page.wait_for_selector("[data-testid=lookup-result]")
    alert = page.locator("[data-testid=lookup-result] .alert-box")
    ok("lookup: đơn huỷ -> cảnh báo ĐỎ 'xé tem'", "err" in alert.get_attribute("class") and "Đơn đã huỷ, không soạn, xé tem." in alert.inner_text())
    page.screenshot(path=f"{SHOTS}/lookup-cancelled-1280.png")
    # Tem còn hiệu lực: mở thẳng phiếu
    go(page, "/deliveries/lookup/")
    lookup(page, "GH-HD-0032-READY.1")
    page.wait_for_url(re.compile(r"/deliveries/detail/\?id=32$"))
    ok("lookup: tem còn hiệu lực -> mở thẳng chi tiết phiếu 32 (AC1)", True)
    ok("lookup: URL chi tiết chỉ mang id", "GH-" not in page.url)
    ok("lookup: không có dữ liệu khách trong localStorage", not any(p in storage_dump(page) for p in PII_STRINGS + [PHONE_TYPO]))
    ctx.close()

    # Camera giả: BarcodeDetector trả mã tem, camera là thiết bị giả của Chromium.
    cam_browser = pw.chromium.launch(args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
    ctx = cam_browser.new_context(viewport={"width": 1280, "height": 860}, permissions=["camera"], reduced_motion="reduce")
    ctx.add_init_script("""
      window.BarcodeDetector = class { constructor(){} async detect(){ return [{rawValue: 'GH-HD-0046-REPR.1'}]; } };
    """)
    page = ctx.new_page()
    login(page, "kho1")
    go(page, "/deliveries/lookup/")
    page.get_by_role("button", name="Quét bằng camera").click()
    page.wait_for_selector("[data-testid=lookup-result]", timeout=10_000)
    ok("camera: BarcodeDetector đọc mã -> ra kết quả tem cũ", "dùng tem lần 2" in body_text(page))
    ok("camera: quét xong tự tắt camera", page.get_by_role("button", name="Quét bằng camera").count() == 1)
    ctx.close()
    cam_browser.close()

    # Không có BarcodeDetector: không có nút camera, vẫn gõ tay được
    ctx = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    ctx.add_init_script("delete window.BarcodeDetector;")
    page = ctx.new_page()
    login(page, "kho1")
    go(page, "/deliveries/lookup/")
    ok("camera: trình duyệt không có BarcodeDetector -> không có nút camera, ô gõ tay vẫn có", page.get_by_role("button", name="Quét bằng camera").count() == 0 and page.get_by_label("Mã tem").count() == 1)
    ctx.close()

    # ---------------- CS-18: soạn kịch bản ----------------
    ctx, page, _ = new_page(browser, "loc", errors=errors)
    go(page, "/confirmation/scripts/")
    page.wait_for_selector("text=Khách mua lần đầu")
    page.screenshot(path=f"{SHOTS}/scripts-owner-1280.png", full_page=True)
    ok("scripts: Chủ thấy cả kịch bản đã tắt (Đơn có combo, chip Đã tắt)", "Đơn có combo" in body_text(page) and page.get_by_text("Đã tắt").count() == 1)
    # Soạn "Khách quen" có SĐT -> chặn ở máy khách
    page.evaluate("() => window.__caveMock.clearLog()")
    page.get_by_role("region", name="Kịch bản: Khách quen").get_by_role("button", name="Soạn kịch bản").click()
    dlg = page.get_by_role("dialog")
    dlg.get_by_label("Nội dung kịch bản").fill("Chào chị, gọi số 0900 000 123 để đổi giờ giao.")
    dlg.get_by_role("button", name="Lưu kịch bản").click()
    page.wait_for_selector("text=Kịch bản không được chứa số điện thoại")
    ok("scripts: nội dung có SĐT bị chặn ở máy khách", dlg.get_by_text("Kịch bản không được chứa số điện thoại hay dãy số dài").count() == 1)
    ok("scripts: SĐT bị chặn KHÔNG có request POST", not any(r.startswith("POST") and "/scripts/" in r for r in log_of(page)), str(log_of(page)))
    ok("scripts: ô lỗi có aria-invalid", dlg.get_by_label("Nội dung kịch bản").get_attribute("aria-invalid") == "true")
    dlg.get_by_label("Nội dung kịch bản").fill("")
    dlg.get_by_role("button", name="Lưu kịch bản").click()
    ok("scripts: nội dung rỗng bị chặn", dlg.get_by_text("Nhập nội dung kịch bản.").count() == 1)
    page.screenshot(path=f"{SHOTS}/scripts-modal-error-1280.png")
    dlg.get_by_label("Nội dung kịch bản").fill("Chào chị, em nhắc chị cất hàng vào ngăn mát ngay khi nhận.")
    dlg.get_by_role("button", name="Lưu kịch bản").click()
    page.wait_for_selector("text=Đã soạn kịch bản.")
    settle(page)
    ok("scripts: Chủ soạn Khách quen thành công", page.get_by_role("region", name="Kịch bản: Khách quen").get_by_text("cất hàng vào ngăn mát").count() == 1)
    ok("scripts: POST gửi đúng contract", any(r == "POST /api/confirmation/scripts/" for r in log_of(page)), str(log_of(page)))
    # Sửa
    page.get_by_role("region", name="Kịch bản: Khách quen").get_by_role("button", name="Sửa").click()
    dlg = page.get_by_role("dialog")
    ok("scripts: hộp Sửa mở với nội dung cũ", "cất hàng vào ngăn mát" in dlg.get_by_label("Nội dung kịch bản").input_value())
    dlg.get_by_role("button", name="Quay lại").click()
    # Tắt "Khách mua lần đầu" rồi mở chi tiết gọi: không còn hiện (AC2)
    first = page.get_by_role("region", name="Kịch bản: Khách mua lần đầu")
    first.get_by_role("button", name="Tắt", exact=True).click()
    page.wait_for_selector("text=Đã tắt kịch bản.")
    settle(page)
    ok("scripts: tắt -> chip Đã tắt, nút đổi thành Bật", first.get_by_text("Đã tắt").count() == 1 and first.get_by_role("button", name="Bật", exact=True).count() == 1)
    ok("scripts: PATCH /scripts/FIRST_ORDER/", any(r == "PATCH /api/confirmation/scripts/FIRST_ORDER/" for r in log_of(page)))
    page.get_by_role("link", name="Gọi xác nhận").first.click()  # quay lại bằng điều hướng trong app (mock còn giữ trạng thái)
    page.wait_for_url(re.compile(r"/confirmation/$"))
    settle(page)
    page.locator("table.lt tbody tr", has_text="SO260928-3F9A01").first.click()
    page.wait_for_selector("h2:has-text('SO260928-3F9A01')")
    page.wait_for_selector("text=Lời dặn chung")
    sec = page.get_by_role("region", name="Kịch bản gọi")
    ok("scripts: Chủ tắt kịch bản -> chi tiết gọi không hiện Khách mua lần đầu (AC2), vẫn hiện Lời dặn chung", "Khách mua lần đầu" not in sec.inner_text() and "Lời dặn chung" in sec.inner_text())
    ctx.close()

    # ---------------- 360px và 1280px, không AI ----------------
    for who, w in (("loc", 360), ("kho1", 360), ("cs1", 360), ("loc", 1280)):
        ctx, page, _ = new_page(browser, who, w=w, h=800, errors=errors)
        paths = ["/confirmation/scripts/", "/confirmation/detail/?id=31"] if who in ("cs1", "loc") else []
        if who in ("kho1", "loc"):
            paths += ["/deliveries/lookup/", "/print/pick-sheet/?note=31"]
        for path in paths:
            go(page, path)
            page.wait_for_load_state("networkidle")
            if "pick-sheet" in path:
                page.wait_for_selector("[data-testid=pick-sheet]")
            ok(f"{w}px {who} {path}: không cuộn ngang", no_hscroll(page))
            ok(f"{w}px {who} {path}: không request /api/ai/", not any("/api/ai/" in r for r in log_of(page)), str(log_of(page)))
        if w == 360 and who == "kho1":
            go(page, "/deliveries/lookup/")
            lookup(page, "GH-HD-0046-REPR.1")
            page.wait_for_selector("[data-testid=lookup-result]")
            page.screenshot(path=f"{SHOTS}/lookup-old-tag-360.png", full_page=True)
            # nút bấm >= 44px
            h = page.get_by_role("button", name="Mở phiếu").evaluate("el => el.getBoundingClientRect().height")
            ok("360px: nút Mở phiếu cao >= 40px", h >= 40, str(h))
            go(page, "/print/pick-sheet/?note=31")
            page.wait_for_selector("[data-testid=pick-sheet]")
            page.screenshot(path=f"{SHOTS}/pick-sheet-360.png", full_page=True)
        if w == 360 and who == "cs1":
            go(page, "/confirmation/detail/?id=31")
            page.wait_for_selector("text=Kịch bản gọi")
            page.screenshot(path=f"{SHOTS}/confirmation-detail-scripts-360.png", full_page=True)
        if w == 360 and who == "loc":
            go(page, "/confirmation/scripts/")
            page.wait_for_selector("text=Khách mua lần đầu")
            page.screenshot(path=f"{SHOTS}/scripts-owner-360.png", full_page=True)
        if w == 1280 and who == "loc":
            go(page, "/confirmation/detail/?id=31")
            page.wait_for_selector("text=Kịch bản gọi")
            page.screenshot(path=f"{SHOTS}/confirmation-detail-scripts-1280.png", full_page=True)
            go(page, "/deliveries/lookup/")
            page.screenshot(path=f"{SHOTS}/lookup-empty-1280.png")
        ctx.close()

    ok("console: không lỗi, không log dữ liệu khách", not errors and not any(p in " ".join(errors) for p in PII_STRINGS), str(errors[:3]))
    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
