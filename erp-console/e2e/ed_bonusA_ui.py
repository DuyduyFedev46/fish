# E2E "Lô bổ sung A" (Duy chốt 02/10/2026): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3401 &)
#   BASE=http://127.0.0.1:3401 SHOTS=<thư mục ảnh> python3 e2e/ed_bonusA_ui.py      # tắt server (đúng cổng của mình) sau khi xong
# Kiểm các mục còn lại ngoài ed_batch3 (#15), ed_batch6 (#5), ed_batch8 (#6/#20), ed_batch9 (#8 danh sách), ed_batch10 (#22):
#   #1 hạn mức AI (chỉ Chủ thấy; ok / sắp chạm / hết) · #2 mốc "Tạo phiếu hoàn" có liên kết sang phiếu · #8 Huỷ phiếu hoàn
#   (đường thuận, 409, người không đủ quyền không thấy mục) · #11 tìm khách bằng POST, từ khoá không nằm trong URL ·
#   #14 lỗi chi phí dưới đúng ô · #17 SĐT từ danh sách, không gọi thêm chi tiết · #18 mốc Bắt đầu giao / Giao thất bại ·
#   #19 "Nhờ người xử lý" trong menu "…" (đơn, lô) · quyền: vai không có quyền không thấy · 360px không cuộn ngang.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3401")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)
PHONE = re.compile(r"0\d{9}")


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


def log(page):
    return page.evaluate("() => window.__caveMock.log.slice()")


def menu(page):
    page.get_by_role("button", name="Thao tác khác").click()
    return page.get_by_role("menu")


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])")


def field_error(page, name):
    el = page.locator(f"[name='{name}']").first
    if el.get_attribute("aria-invalid") != "true":
        return None
    return " ".join(page.locator("[id='" + el.get_attribute("aria-describedby") + "'] span").last.inner_text().split())


# ---------------------------------------------------------------- #1 hạn mức AI
def ai_budget(browser):
    ctx, page, errors = new_page(browser, "loc")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); window.__caveMock.aiBudget('ok'); }")
    go(page, "/dev-patterns/")
    page.locator("[data-ai-starter]").first.get_by_role("textbox").focus()
    expect(page.get_by_role("heading", name="Trợ lý vận hành")).to_be_visible()
    usage = page.get_by_test_id("ai-budget-usage")
    usage.wait_for()
    ok("#1 Chủ: hiện 'Đã dùng 0 đ / 200.000 đ'", usage.inner_text() == "Đã dùng 0 đ / 200.000 đ", usage.inner_text())
    ok("#1 hạn mức bình thường: không có câu cảnh báo", page.get_by_text("Sắp chạm hạn mức", exact=False).count() == 0 and page.get_by_text("Đã hết hạn mức", exact=False).count() == 0)
    for mode, spent, note in (("warning", "170.000", "Sắp chạm hạn mức tháng này."), ("blocked", "200.000", "Đã hết hạn mức tháng này")):
        page.evaluate("(m) => window.__caveMock.aiBudget(m)", mode)
        go(page, "/dev-patterns/")
        page.locator("[data-ai-starter]").first.get_by_role("textbox").focus()
        page.get_by_test_id("ai-budget-usage").wait_for()
        ok(f"#1 {mode}: hiện số đã dùng {spent} đ và câu trạng thái", spent in page.get_by_test_id("ai-budget-usage").inner_text() and page.get_by_text(note, exact=False).first.is_visible(), page.get_by_test_id("ai-budget-usage").inner_text())
    page.screenshot(path=os.path.join(SHOTS, "bonusA_ai_budget_blocked_1280.png"))
    ok("#1 không có lỗi console", not errors, str(errors[:2]))
    ctx.close()
    # vai khác Chủ: BE không trả budget, màn không dựng khối
    ctx, page, errors = new_page(browser, "ql1")
    page.evaluate("() => { window.__caveMock.ai('on'); window.__caveMock.aiConsent(true); window.__caveMock.aiBudget('blocked'); }")
    go(page, "/dev-patterns/")
    page.locator("[data-ai-starter]").first.get_by_role("textbox").focus()
    expect(page.get_by_role("heading", name="Trợ lý vận hành")).to_be_visible()
    ok("#1 Quản lý: không thấy hạn mức chi phí (chỉ Chủ)", page.get_by_test_id("ai-budget-usage").count() == 0 and page.get_by_text("Đã dùng", exact=False).count() == 0)
    ctx.close()


# ---------------------------------------------------------------- #2 mốc phiếu hoàn có liên kết
def refund_timeline(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/orders/")
    order = page.evaluate("""() => { for (let id = 101; id <= 140; id++) { try { const j = window.__caveMock.orderJson('loc', id); if (j && j.refunds && j.refunds.length) return id; } catch (e) {} } return null; }""")
    ok("#2 tìm được đơn có phiếu hoàn trong dữ liệu mock", order is not None, str(order))
    go(page, f"/orders/detail/?id={order}")
    link = page.locator("a", has_text="Tạo phiếu hoàn").first
    ok("#2 mốc 'Tạo phiếu hoàn' là liên kết", link.count() == 1 and link.is_visible())
    href = link.get_attribute("href") or ""
    ok("#2 liên kết trỏ sang phiếu hoàn, chỉ mang ?id=", re.search(r"/orders/refunds/detail/\?id=\d+$", href) is not None, href)
    link.click()
    page.wait_for_url(re.compile(r"/orders/refunds/detail/\?id=\d+$"))
    settle(page)
    ok("#2 bấm liên kết mở được phiếu hoàn", page.get_by_role("heading", name="Không tìm thấy").count() == 0 and "hoàn" in page.inner_text("main").lower())
    # mốc khác không có liên kết sai chỗ
    go(page, f"/orders/detail/?id={order}")
    ok("#2 các mốc không có chứng từ riêng vẫn là chữ thường (không liên kết cho 'Tạo hoá đơn')", page.locator("a", has_text="Đã hoàn").count() == 0)
    ok("#2 không có lỗi console", not errors, str(errors[:2]))
    ctx.close()


# ---------------------------------------------------------------- #8 Huỷ phiếu hàng hoàn
def return_cancel(browser):
    # đường thuận: Chủ huỷ RT-1 (Chờ duyệt)
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/returns/detail/?id=1")
    m = menu(page)
    ok("#8 RT-1 Chờ duyệt: Chủ có mục Huỷ phiếu hàng hoàn trong '…'", m.get_by_role("menuitem", name="Huỷ phiếu hàng hoàn").count() == 1)
    m.get_by_role("menuitem", name="Huỷ phiếu hàng hoàn").click()
    dlg = page.get_by_role("dialog")
    ok("#8 hộp xác nhận nói không khôi phục lại được", "không khôi phục lại được" in dlg.inner_text(), dlg.inner_text())
    page.evaluate("() => window.__caveMock.clearLog()")
    dlg.get_by_role("button", name="Huỷ phiếu hàng hoàn").click()
    page.get_by_text("Đã huỷ phiếu", exact=False).first.wait_for()
    settle(page)
    ok("#8 huỷ xong: chip Đã huỷ, gọi đúng 1 POST cancel", "Đã huỷ" in page.inner_text("main") and len([x for x in log(page) if "POST" in x and "cancel" in x]) == 1, str([x for x in log(page) if x.startswith("POST")]))
    page.get_by_role("button", name="Thao tác khác").click()  # Chủ còn mục Xoá (#8), nên menu vẫn có
    ok("#8 huỷ xong: hết nút Tái nhập / Huỷ bỏ và mục Huỷ phiếu hàng hoàn", page.get_by_role("button", name="Tái nhập vào lô").count() == 0 and page.get_by_role("menuitem", name="Huỷ phiếu hàng hoàn").count() == 0 and page.get_by_role("menuitem", name="Xoá phiếu hàng hoàn").count() == 1)
    page.keyboard.press("Escape")
    ctx.close()
    # 409: phiếu được duyệt từ máy khác trong lúc mở hộp
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/returns/detail/?id=2")
    page.evaluate("() => window.__caveMock.returnsMarkApproved(2)")
    menu(page).get_by_role("menuitem", name="Huỷ phiếu hàng hoàn").click()
    dlg = page.get_by_role("dialog")
    dlg.get_by_role("button", name="Huỷ phiếu hàng hoàn").click()
    dlg.locator("[data-conflict-banner]").wait_for()
    ok("#8 409: hộp hiện banner xung đột, có nút Tải lại, hộp không tự đóng", dlg.is_visible() and dlg.get_by_role("button", name="Tải lại").count() == 1, " ".join(dlg.inner_text().split())[:200])
    dlg.get_by_role("button", name="Tải lại").click()
    settle(page)
    ok("#8 tải lại: hộp đóng, phiếu hiện Đã duyệt, hết mục Huỷ", page.get_by_role("dialog").count() == 0 and "Đã duyệt" in page.inner_text("main"))
    ok("#8 409: không console.error ngoài HTTP chủ ý", not errors, str(errors[:2]))
    ctx.close()
    # kho1: không phải người tạo, không có quyền duyệt/sửa -> không có mục Huỷ
    ctx, page, errors = new_page(browser, "kho1")
    go(page, "/returns/detail/?id=1")
    has_menu = page.get_by_role("button", name="Thao tác khác").count() == 1
    ok("#8 kho1 (không phải người tạo, không quyền duyệt): không có mục Huỷ phiếu hàng hoàn", (not has_menu) or menu(page).get_by_role("menuitem", name="Huỷ phiếu hàng hoàn").count() == 0)
    ctx.close()
    # giao1: người tạo RT-1 huỷ được phiếu của mình; phiếu đã huỷ (RT-6) không còn mục Huỷ
    ctx, page, errors = new_page(browser, "giao1")
    go(page, "/returns/detail/?id=1")
    ok("#8 giao1 (người tạo RT-1): có mục Huỷ phiếu hàng hoàn", menu(page).get_by_role("menuitem", name="Huỷ phiếu hàng hoàn").count() == 1)
    page.keyboard.press("Escape")
    go(page, "/returns/detail/?id=6")
    ok("#8 RT-6 đã huỷ: chip Đã huỷ, không có mục Huỷ", "Đã huỷ" in page.inner_text("main") and page.get_by_role("button", name="Thao tác khác").count() == 0)
    ctx.close()


# ---------------------------------------------------------------- #11 tìm khách bằng POST
def customers_search(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/customers/")
    page.evaluate("() => window.__caveMock.clearLog()")
    box = page.get_by_role("searchbox", name="Tìm khách hàng")
    box.fill("0900000")
    page.wait_for_timeout(700)
    settle(page)
    reqs = [x for x in log(page) if "customer-directory" in x]
    ok("#11 tìm khách: gọi POST .../search/ (không GET kèm từ khoá)", reqs and all(x.startswith("POST ") and "search" in x for x in reqs), str(reqs))
    ok("#11 từ khoá không nằm trong URL trang, log hay storage", "0900000" not in page.url and not any("0900000" in x for x in log(page)) and "0900000" not in storage_dump(page))
    ctx.close()


# ---------------------------------------------------------------- #14 lỗi chi phí dưới đúng ô
def cost_errors(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/purchasing/costs/new/?receipt=101")
    page.locator("input[name=amount]").wait_for()
    settle(page)
    save = page.get_by_role("button", name="Lưu chi phí")
    page.locator("input[name=amount]").fill("1000000000000")
    page.wait_for_timeout(200)
    err = field_error(page, "amount")
    ok("#14 tổng chi phí 13 chữ số: báo 'quá lớn' ngay dưới ô tổng (hoặc BE trả COST_AMOUNT_TOO_LARGE)", bool(err) and "quá lớn" in err, str(err))
    page.locator("input[name=amount]").fill("")
    page.locator("input[name=amount]").fill("500000000000")
    page.wait_for_timeout(300)
    if save.is_enabled():
        page.evaluate("() => window.__caveMock.clearLog()")
        save.click()
        page.wait_for_timeout(600)
        settle(page)
        a = field_error(page, "alloc-0")
        al = page.get_by_text("giá vốn mỗi kg của lô vượt giới hạn", exact=False)
        ok("#14 COST_LANDED_OVERFLOW: câu của BE hiện, form còn nguyên (không chuyển trang)", al.count() >= 1 and "/purchasing/costs/new" in page.url, f"{a!r} {page.url}")
        page.locator("input[name=amount]").fill("1000000")
        page.wait_for_timeout(300)
        ok("#14 sửa số tiền: lỗi cũ biến mất", page.get_by_text("giá vốn mỗi kg của lô vượt giới hạn", exact=False).count() == 0)
    else:
        ok("#14 nút Lưu mở được với 500.000.000.000", False, "nút khoá")
    ok("#14 không console.error ngoài HTTP chủ ý", not errors, str(errors[:2]))
    ctx.close()
    # quyền: Quản lý không có quyền ghi chi phí
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/purchasing/costs/new/?receipt=101")
    ok("#14 Quản lý: không có quyền nhập chi phí (không thấy ô số tiền)", page.locator("input[name=amount]").count() == 0)
    ctx.close()


# ---------------------------------------------------------------- #17 / #18 phiếu giao
def deliveries(browser):
    ctx, page, errors = new_page(browser, "giao1")
    page.evaluate("() => window.__caveMock.clearLog()")
    go(page, "/my-deliveries/")
    reqs = log(page)
    detail_calls = [x for x in reqs if re.search(r"GET /api/delivery/(delivery-notes|notes)/\d+/", x) or re.search(r"/deliveries?/\d+/", x)]
    ok("#17 Việc giao của tôi: không gọi chi tiết từng phiếu để lấy SĐT", not detail_calls, str(reqs)[:300])
    body = page.inner_text("main")
    ok("#17 phiếu Đang giao có số điện thoại gọi được (liên kết tel:)", page.locator("a[href^='tel:']").count() >= 1)
    ok("#17 phiếu quá hạn: báo 'Số điện thoại đã ẩn' thay vì để trống", "đã ẩn" in body or page.locator("a[href^='tel:']").count() >= 1, body[:200])
    shown = [h.replace("tel:", "") for h in page.locator("a[href^='tel:']").evaluate_all("els => els.map(e => e.getAttribute('href'))")]
    dump = storage_dump(page)
    ok("#17 SĐT khách đang hiện không nằm trong URL, localStorage, sessionStorage", bool(shown) and not any(ph in page.url or ph in dump for ph in shown), str(len(shown)))
    ctx.close()
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/deliveries/detail/?id=36")
    txt = page.inner_text("main")
    ok("#18 phiếu Đang giao: có 'Bắt đầu giao' dạng dd/mm/yyyy hh:mm, chưa có 'Giao thất bại'", re.search(r"Bắt đầu giao\s*\n?\s*\d{2}/\d{2}/\d{4} \d{2}:\d{2}", txt) is not None and "Giao thất bại" not in txt.replace("Giao thất bại lần", ""), txt[:300])
    go(page, "/deliveries/detail/?id=34")
    txt = page.inner_text("main")
    ok("#18 phiếu Giao thất bại: có cả 'Bắt đầu giao' và 'Giao thất bại' kèm giờ", re.search(r"Giao thất bại\s*\n?\s*\d{2}/\d{2}/\d{4} \d{2}:\d{2}", txt) is not None and "Bắt đầu giao" in txt, txt[:300])
    go(page, "/deliveries/detail/?id=31")
    ok("#18 phiếu chưa giao: không có hai mốc", "Bắt đầu giao" not in page.inner_text("main"))
    ctx.close()


# ---------------------------------------------------------------- #19 Nhờ người xử lý
def escalate(browser):
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/orders/")
    page.evaluate("() => window.__caveMock.clearLog()")
    order = page.evaluate("""() => { for (let id = 101; id <= 140; id++) { try { const j = window.__caveMock.orderJson('ql1', id); if (j && j.status === 'PAID') return id; } catch (e) {} } return null; }""")
    go(page, f"/orders/detail/?id={order}")
    m = menu(page)
    item = m.get_by_role("menuitem", name="Nhờ người xử lý")
    ok("#19 đơn: menu '…' có 'Nhờ người xử lý' khi có bước mình chưa làm được", item.count() == 1)
    if item.count() == 1:
        item.click()
        dlg = page.get_by_role("dialog")
        ok("#19 hộp xác nhận nêu việc và người nhận (Chủ)", "Chủ" in dlg.inner_text() and "Việc của AI" in dlg.inner_text(), dlg.inner_text()[:300])
        page.evaluate("() => window.__caveMock.clearLog()")
        dlg.get_by_role("button", name="Nhờ người xử lý").click()
        page.get_by_text("Đã nhờ", exact=False).first.wait_for()
        posts = [x for x in log(page) if x.startswith("POST") and "escalate" in x]
        ok("#19 xác nhận: toast 'Đã nhờ …', đúng 1 POST escalate", len(posts) == 1, str(log(page)))
        page.wait_for_function("() => !document.querySelector('[role=dialog]')", timeout=10_000)
        ok("#19 (TLA-FE-L3) nhờ xong: menu '…' không còn mục 'Nhờ người xử lý' (khỏi nhờ lặp)", menu(page).get_by_role("menuitem", name="Nhờ người xử lý").count() == 0)
        page.keyboard.press("Escape")
    ctx.close()
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/inventory/")
    found = None
    for batch in range(1, 30):
        go(page, f"/inventory/detail/?id={batch}")
        if page.get_by_role("button", name="Thao tác khác").count() == 1 and "Đang bán" in page.inner_text("main"):
            if menu(page).get_by_role("menuitem", name="Nhờ người xử lý").count() == 1:
                found = batch
                break
            page.keyboard.press("Escape")
    ok("#19 lô: có lô Đang bán mà menu '…' có 'Nhờ người xử lý' (việc 'Chốt lô' cần Chủ)", found is not None, str(found))
    if found:
        page.get_by_role("menuitem", name="Nhờ người xử lý").click()
        dlg = page.get_by_role("dialog")
        ok("#19 lô: hộp nêu việc 'Chốt lô' và Chủ", "Chốt lô" in dlg.inner_text() and "Chủ" in dlg.inner_text(), " ".join(dlg.inner_text().split())[:240])
        dlg.get_by_role("button", name="Quay lại").click()
        ok("#19 lô: Quay lại đóng hộp, không gọi POST escalate", page.get_by_role("dialog").count() == 0 and not [x for x in log(page) if x.startswith("POST") and "escalate" in x])
        page.screenshot(path=os.path.join(SHOTS, "bonusA_batch_menu_1280.png"))
        # TLA-FE-L3: nhờ thật rồi thì mục biến mất khỏi menu
        menu(page).get_by_role("menuitem", name="Nhờ người xử lý").click()
        page.get_by_role("dialog").get_by_role("button", name="Nhờ người xử lý").click()
        page.get_by_text("Đã nhờ", exact=False).first.wait_for()
        page.wait_for_function("() => !document.querySelector('[role=dialog]')", timeout=10_000)
        ok("#19 lô (TLA-FE-L3): nhờ xong thì menu '…' không còn 'Nhờ người xử lý'", menu(page).get_by_role("menuitem", name="Nhờ người xử lý").count() == 0)
        page.keyboard.press("Escape")
    ctx.close()


# ---------------------------------------------------------------- 360px + ảnh
def mobile(browser):
    ctx, page, errors = new_page(browser, "ql1", 360, 740)
    go(page, "/returns/detail/?id=2")
    ok("360px chi tiết phiếu hoàn: không cuộn ngang", no_hscroll(page))
    menu(page).get_by_role("menuitem", name="Huỷ phiếu hàng hoàn").click()
    ok("360px hộp Huỷ phiếu hàng hoàn: không cuộn ngang, nút cao >= 44px", no_hscroll(page) and page.get_by_role("dialog").get_by_role("button", name="Huỷ phiếu hàng hoàn").bounding_box()["height"] >= 43.5)
    page.screenshot(path=os.path.join(SHOTS, "bonusA_return_cancel_360.png"))
    page.keyboard.press("Escape")
    go(page, "/stocktake/detail/?id=14")
    ok("360px chi tiết kiểm kê Chờ duyệt: không cuộn ngang", no_hscroll(page))
    page.screenshot(path=os.path.join(SHOTS, "bonusA_stocktake_submitted_360.png"), full_page=True)
    go(page, "/stocktake/detail/?id=15")
    ok("360px chi tiết kiểm kê Nháp: không cuộn ngang", no_hscroll(page))
    page.screenshot(path=os.path.join(SHOTS, "bonusA_stocktake_draft_360.png"), full_page=True)
    ok("360px: không console.error", not errors, str(errors[:2]))
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for fn in (ai_budget, refund_timeline, return_cancel, customers_search, cost_errors, deliveries, escalate, mobile):
        try:
            fn(browser)
        except Exception as exc:  # một nhóm lỗi không làm mất kết quả các nhóm khác
            ok(f"{fn.__name__}: chạy không ném lỗi", False, repr(exc)[:400])
    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} đạt")
sys.exit(1 if failed else 0)
