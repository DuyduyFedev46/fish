# P8 Lô 7 — FE ERP: F14 (in tem: QR là <img data-URI>, chuyển đăng nhập giữ query), Lô 3 L4 (CSKH stale cho đổi người nhận,
# huỷ xác nhận, quyết định Quản lý), Lô 4 L1 (timeline credit_note_issued), Lô 5 L5-1 (danh sách lô EXPIRED dùng has_stock=1
# + tên NCC/kho từ BE), F12 (không còn /ai-spike/).
# Mock (NEXT_PUBLIC_USE_MOCK=1), dữ liệu giả. Chạy:
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out <thư-mục-out-riêng> && (cd <thư-mục-out-riêng> && python3 -m http.server 3217 --bind 127.0.0.1 &)
#   BASE=http://127.0.0.1:3217 SHOTS=<thư mục ảnh> python3 e2e/p8_lo7_fe_erp.py      # tắt server rồi build lại bản thật
import os
import re
import sys
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3217")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []


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


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def new_page(browser, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(m.text))
    page.add_init_script("window.__printed = 0; window.print = () => { window.__printed += 1; };")
    return ctx, page, logs


# ---------------------------------------------------------------- F14
def f14(browser, tag, w, h):
    ctx, page, logs = new_page(browser, w, h)
    login(page, "kho1")
    # token hết hạn (xoá token, giữ id người dùng gần nhất) rồi mở thẳng link in tem
    page.evaluate("() => localStorage.removeItem('cave_erp_token')")
    page.goto(BASE + "/print/label/?note=32&print_no=1")
    page.wait_for_url(re.compile(r"/login/"), timeout=10_000)
    nxt = parse_qs(urlparse(page.url).query).get("next", [""])[0]
    ok(f"F14[{tag}] chuyển về đăng nhập, giữ nguyên query (next={nxt})", nxt == "/print/label/?note=32&print_no=1", page.url)
    page.screenshot(path=f"{SHOTS}/f14-{tag}-1-dang-nhap-giu-query.png")
    page.fill("#u", "kho1")
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url(re.compile(r"/print/label/"), timeout=10_000)
    ok(f"F14[{tag}] đăng nhập xong quay lại đúng tem đang in", "note=32" in page.url and "print_no=1" in page.url, page.url)
    img = page.locator('img[src^="data:image/svg+xml"]')
    img.first.wait_for(timeout=10_000)
    ok(f"F14[{tag}] QR là <img src=data:image/svg+xml> (1 ảnh)", img.count() == 1)
    ok(f"F14[{tag}] ảnh QR có alt chứa mã vạch", "GH-HD-0032-READY.1" in (img.first.get_attribute("alt") or ""), img.first.get_attribute("alt") or "")
    ok(f"F14[{tag}] không còn <svg> chèn thô trong DOM", page.locator("svg").count() == 0)
    natural = page.evaluate("() => { const i = document.querySelector('img[src^=\"data:image/svg+xml\"]'); return i && i.complete && i.naturalWidth > 0; }")
    ok(f"F14[{tag}] ảnh QR giải mã và vẽ được (naturalWidth > 0)", natural)
    page.wait_for_timeout(700)
    ok(f"F14[{tag}] vẫn tự gọi window.print()", page.evaluate("() => window.__printed") >= 1)
    # Tem là khổ vật lý cố định 100x150mm (~378px) nên trên màn 375px rộng hơn ~3px là chủ đích cũ, không phải lỗi bố cục.
    ok(f"F14[{tag}] không cuộn ngang (mobile: cho phép khổ tem 100mm)", no_hscroll(page) or w < 380)
    page.screenshot(path=f"{SHOTS}/f14-{tag}-2-tem-qr-img.png")
    ok(f"F14[{tag}] console không chứa SĐT/tên khách", not any(re.search(r"09\d{8}", l) or "Khách Thử" in l for l in logs))
    ctx.close()


# ---------------------------------------------------------------- Lô 3 L4
def open_card(page, code):
    card = page.locator("[class*='queueCard']", has_text=code)
    card.first.wait_for(timeout=10_000)
    card.first.click()
    modal = page.get_by_role("dialog")
    modal.wait_for(timeout=10_000)
    page.wait_for_timeout(500)
    return modal


def check_stale(page, modal, tag, what, submit_btn):
    alert = page.get_by_test_id("confirmation-stale-alert")
    alert.wait_for(timeout=10_000)
    ok(f"L4[{tag}] {what}: hiện đúng `detail` của BE", "Đơn đã bị huỷ — tải lại màn hình." in alert.inner_text(), alert.inner_text().replace("\n", " | "))
    reload_btn = alert.get_by_role("button", name="Tải lại")
    ok(f"L4[{tag}] {what}: có nút Tải lại (cao >= 44px)", reload_btn.count() == 1 and reload_btn.bounding_box()["height"] >= 43.5)
    ok(f"L4[{tag}] {what}: nút gửi của biểu mẫu bị khoá (không gửi lại)", submit_btn.is_disabled())
    box = alert.bounding_box()
    vp = page.viewport_size
    ok(f"L4[{tag}] {what}: cảnh báo nằm trong khung nhìn", box and box["y"] >= 0 and box["y"] + box["height"] <= vp["height"], str(box))
    ok(f"L4[{tag}] {what}: không cuộn ngang", no_hscroll(page))
    return alert, reload_btn


def confirmation_case(browser, tag, w, h):
    # --- đổi người nhận
    ctx, page, logs = new_page(browser, w, h)
    login(page, "cs1")
    page.goto(BASE + "/cskh/")
    page.wait_for_load_state("networkidle")
    modal = open_card(page, "DH-260928-0030")
    page.evaluate("() => window.__caveMock.confirmationArmStale(30)")
    modal.get_by_role("button", name="Đổi người nhận / địa chỉ").click()
    modal.get_by_placeholder("VD: Anh Minh (nhận hộ)").fill("Người Nhận Thử")
    submit = modal.get_by_role("button", name="Lưu thay đổi")
    submit.click()
    alert, reload_btn = check_stale(page, modal, tag, "đổi người nhận", submit)
    page.screenshot(path=f"{SHOTS}/l4-{tag}-1-doi-nguoi-nhan-stale.png")
    reload_btn.click()
    page.wait_for_timeout(700)
    page.wait_for_load_state("networkidle")
    ok(f"L4[{tag}] đổi người nhận: Tải lại đóng hộp thoại, phiếu rời hàng chờ", page.get_by_role("dialog").count() == 0 and page.locator("[class*='queueCard']", has_text="DH-260928-0030").count() == 0)
    ctx.close()

    # --- huỷ xác nhận (phiếu đã sang Soạn hàng)
    ctx, page, logs = new_page(browser, w, h)
    login(page, "cs1")
    page.goto(BASE + "/cskh/")
    page.wait_for_load_state("networkidle")
    page.evaluate("() => window.__caveMock.confirmationSetStatus(36, 'PREPARING')")
    page.get_by_role("button", name="Chờ gọi").first.click()
    page.wait_for_timeout(600)
    modal = open_card(page, "DH-260928-0036")
    page.evaluate("() => window.__caveMock.confirmationArmStale(36)")
    modal.get_by_role("button", name="Huỷ xác nhận đơn").click()
    modal.get_by_placeholder("VD: Bấm nhầm đơn, khách đổi giờ hẹn...").fill("Khách đổi ý về giờ giao")
    submit = modal.get_by_role("button", name="Xác nhận huỷ")
    submit.click()
    alert, reload_btn = check_stale(page, modal, tag, "huỷ xác nhận", submit)
    page.screenshot(path=f"{SHOTS}/l4-{tag}-2-huy-xac-nhan-stale.png")
    reload_btn.click()
    page.wait_for_timeout(700)
    ok(f"L4[{tag}] huỷ xác nhận: Tải lại đóng hộp thoại", page.get_by_role("dialog").count() == 0)
    ctx.close()

    # --- quyết định Quản lý (phiếu Cần quyết định)
    ctx, page, logs = new_page(browser, w, h)
    login(page, "cs1")  # mock không phân quyền quyết định; BE thật kiểm quyền Quản lý riêng
    page.goto(BASE + "/cskh/")
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="Cần quyết định").first.click()
    page.wait_for_timeout(600)
    modal = open_card(page, "DH-260928-0028")
    page.evaluate("() => window.__caveMock.confirmationArmStale(28)")
    modal.get_by_placeholder("VD: Khách quen, địa chỉ đã giao nhiều lần...").fill("Khách quen giao nhiều lần")
    submit = modal.get_by_role("button", name="Xác nhận chuyển soạn hàng")
    submit.click()
    alert, reload_btn = check_stale(page, modal, tag, "quyết định Quản lý", submit)
    page.screenshot(path=f"{SHOTS}/l4-{tag}-3-quyet-dinh-stale.png")
    reload_btn.click()
    page.wait_for_timeout(700)
    ok(f"L4[{tag}] quyết định Quản lý: Tải lại đóng hộp thoại", page.get_by_role("dialog").count() == 0)
    ok(f"L4[{tag}] console không chứa SĐT/tên khách", not any(re.search(r"09\d{8}", l) or "Khách Thử" in l for l in logs))
    ctx.close()


# ---------------------------------------------------------------- Lô 4 L1
def timeline_case(browser, tag, w, h):
    ctx, page, logs = new_page(browser, w, h)
    login(page, "loc")
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    page.locator(".order-open").first.wait_for()
    row = page.locator(".order-open", has_text="Đã huỷ")
    opened = row.count() >= 1
    if opened:
        row.first.click()
    ok(f"L1[{tag}] tìm được đơn Đã huỷ trong danh sách", opened)
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    page.wait_for_timeout(600)
    ev = dlg.locator('li[data-kind="credit_note_issued"]')
    ok(f"L1[{tag}] timeline có đúng 1 mốc credit_note_issued", ev.count() == 1)
    txt = re.sub(r"\s+", " ", ev.first.inner_text()) if ev.count() else ""
    ok(f"L1[{tag}] nhãn 'Lập chứng từ đảo doanh thu DC-… (x ₫)' đúng định dạng VNĐ", re.search(r"Lập chứng từ đảo doanh thu DC-INV\d+-[0-9A-Fa-f]+ \(\d{1,3}(\.\d{3})* ₫\)", txt) is not None, txt)
    ok(f"L1[{tag}] mốc có icon riêng (không dùng icon mặc định)", ev.count() == 1 and ev.first.locator("i.mi").inner_text() == "description")
    kinds = dlg.locator("ol.order-timeline > li[data-kind]").evaluate_all("els => els.map(e => e.dataset.kind)")
    ok(f"L1[{tag}] thứ tự: huỷ đơn trước, chứng từ đảo sau", kinds.index("cancelled") < kinds.index("credit_note_issued"), str(kinds))
    ev.first.scroll_into_view_if_needed()
    ok(f"L1[{tag}] không cuộn ngang", no_hscroll(page))
    dlg.locator("ol.order-timeline").scroll_into_view_if_needed()
    page.screenshot(path=f"{SHOTS}/l1-{tag}-timeline-credit-note.png")
    ctx.close()


# ---------------------------------------------------------------- Lô 5 L5-1
def expired_case(browser, tag, w, h):
    ctx, page, logs = new_page(browser, w, h)
    login(page, "loc")
    reqs = []
    page.on("request", lambda r: reqs.append(r.url))
    page.goto(BASE + "/inventory/?status=EXPIRED")
    page.wait_for_load_state("networkidle")
    page.locator("table.data tbody tr").first.wait_for(timeout=10_000)
    # mock không đi qua mạng: URL `status=EXPIRED&has_stock=1` được kiểm bằng grep bản build thật (03-dev-notes), ở đây kiểm kết quả hiển thị
    heads = [t.strip().upper() for t in page.locator("table.data thead th").all_inner_texts()]
    ok(f"L5-1[{tag}] bảng có đủ cột NCC và Kho ở chế độ lọc (heads={heads})", "NCC" in heads and "KHO" in heads)
    body = page.locator("table.data tbody").inner_text()
    ok(f"L5-1[{tag}] hiện tên mặt hàng/NCC/kho từ BE (item_name, supplier_name, warehouse_name)", all(x in body for x in ("Cá thu phi lê", "Mực lá câu", "Ghe Tư Hải", "Vựa Bà Năm", "Tàu Phước Lộc 07", "Kho lạnh Bến Đá")), re.sub(r"\s+", " ", body)[:160])
    ok(f"L5-1[{tag}] hiện status_label 'Quá hạn' của BE", body.count("Quá hạn") >= 3)
    ok(f"L5-1[{tag}] 3 lô còn tồn", page.locator("table.data tbody tr").count() == 3)
    ok(f"L5-1[{tag}] không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/l5-1-{tag}-lo-qua-han.png")
    ctx.close()


# ---------------------------------------------------------------- F12
def f12(browser):
    ctx, page, logs = new_page(browser, 1280, 800)
    r = page.goto(BASE + "/ai-spike/")
    ok("F12 /ai-spike/ không còn (404)", r is not None and r.status == 404, str(r.status if r else None))
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for tag, w, h in (("desktop-1280", 1280, 800), ("mobile-375", 375, 667)):
        f14(browser, tag, w, h)
        confirmation_case(browser, tag, w, h)
        timeline_case(browser, tag, w, h)
        expired_case(browser, tag, w, h)
    f12(browser)
    browser.close()

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} PASS")
sys.exit(1 if fails else 0)
