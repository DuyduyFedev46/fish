# E2E ERP (W37 L3 FE, mock): bộ đơn mẫu S6-AC1, chi tiết đơn Hoàn tất (S7-AC1, AC4, AC5), nối mock Giao hàng ↔ Đơn (S6-AC8).
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3201 --bind 127.0.0.1 &)
#   SHOTS=<thư mục ảnh> python3 e2e/order_completion_detail.py      # tắt server sau khi xong
# Bộ mẫu bật bằng localStorage cave_erp_mock_orders_dataset=completion (1 giữ chỗ · 2 đang xử lý · 3 hoàn tất · 1 huỷ).
import os
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3201")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def new_page(browser, user, w=1280, h=860, touch=False):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", **({"is_mobile": True, "has_touch": True} if touch else {}))
    ctx.add_init_script("localStorage.setItem('cave_erp_mock_orders_dataset','completion')")
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill("demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)
    return ctx, page, errors


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    settle(page)


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def rows(page):
    return page.locator("tbody tr").count()


def steps_state(page):
    return page.locator("ol li").evaluate_all("els => els.slice(0, 5).map(e => [e.innerText.replace('check', '').trim(), e.dataset.state])")


def sample_filters(browser):
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/orders/")
    sel = page.get_by_label("Lọc theo trạng thái")
    sel.select_option(label="Chưa xong")
    settle(page)
    ok("S6-AC1: 'Chưa xong' hiện đúng 3 đơn (1 giữ chỗ + 2 đang xử lý)", rows(page) == 3, str(rows(page)))
    sel.select_option(label="Hoàn tất")
    settle(page)
    ok("S6-AC3: 'Hoàn tất' hiện đúng 3 đơn", rows(page) == 3, str(rows(page)))
    ok("S6-AC3: chip mỗi dòng là Hoàn tất", page.locator("tbody tr").filter(has_text="Hoàn tất").count() == 3)
    ctx.close()


def completed_detail(browser):
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/orders/detail/?id=104")
    ok("S7-AC1: chip Hoàn tất", page.locator("header, [data-testid], .chip").filter(has_text="Hoàn tất").count() > 0)
    st = steps_state(page)
    labels = [x[0] for x in st]
    ok("S7-AC1: không có bước 'Đã thanh toán'", "Đã thanh toán" not in labels, str(labels))
    ok("S7-AC1: thanh bước sáng tới Hoàn tất", st[-1] == ["Hoàn tất", "current"] and all(x[1] == "done" for x in st[:-1]), str(st))
    expect(page.get_by_test_id("order-refund-summary")).to_have_text("Đã hoàn tiền 200.000 đ · Chờ hoàn tiền 100.000 đ")
    ok("S7-AC5: dòng 'Đã hoàn tiền 200.000 đ · Chờ hoàn tiền 100.000 đ' dưới chip", True)
    expect(page.get_by_role("button", name="Lập phiếu hoàn tiền")).to_be_visible()
    ok("S7-AC4: nút chính 'Lập phiếu hoàn tiền'", True)
    page.get_by_role("button", name="Thao tác khác").click()
    menu = page.get_by_role("menu").inner_text()
    ok("S7-AC4: mục '…' không có 'Huỷ đơn'", "Huỷ đơn" not in menu, menu)
    page.keyboard.press("Escape")
    page.screenshot(path=os.path.join(SHOTS, "order_completed_detail_1280.png"))
    ok("chi tiết 1280: không console.error", not errors, str(errors)[:200])
    ctx.close()

    ctx, page, errors = new_page(browser, "ql1", 360, 740, touch=True)
    go(page, "/orders/detail/?id=104")
    expect(page.get_by_test_id("order-refund-summary")).to_be_visible()
    ok("chi tiết 360px: không cuộn ngang", no_hscroll(page))
    page.screenshot(path=os.path.join(SHOTS, "order_completed_detail_360.png"), full_page=True)
    ctx.close()

    # Đơn không phiếu hoàn: không có dòng tóm tắt (cả hai bằng 0 thì bỏ).
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/orders/detail/?id=105")
    ok("S7-AC5: đơn Hoàn tất chưa có phiếu hoàn không có dòng tóm tắt", page.get_by_test_id("order-refund-summary").count() == 0)
    ctx.close()


def linked_mocks(browser):
    # Chủ vựa mở Giao hàng, giao xong phiếu Đang giao → đơn mock tự Hoàn tất, Tổng quan đếm lại (S6-AC5, AC6, AC8).
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/orders/detail/?id=103")
    before = steps_state(page)
    ok("S7-AC2: đơn đang xử lý (phiếu Giao thất bại) đứng ở Đang giao, chưa sáng Hoàn tất", ("Đang giao", "current") in [tuple(x) for x in before], str(before))
    go(page, "/deliveries/detail/?id=33")
    page.get_by_role("button", name="Đã giao xong").first.click()
    dlg = page.get_by_role("dialog", name="Xác nhận đã giao xong")
    expect(dlg).to_be_visible()
    dlg.get_by_role("button", name="Đã giao xong").click()
    expect(page.get_by_text("Đã giao xong. Đơn đã hoàn tất.")).to_be_visible()
    go(page, "/orders/detail/?id=103")
    st = steps_state(page)
    ok("S6-AC8: giao xong phiếu → đơn mock sang Hoàn tất (bước Hoàn tất sáng)", st[-1] == ["Hoàn tất", "current"], str(st))
    go(page, "/orders/")
    sel = page.get_by_label("Lọc theo trạng thái")
    sel.select_option(label="Chưa xong")
    settle(page)
    ok("S6-AC6: 'Chưa xong' còn 2 đơn sau khi giao xong", rows(page) == 2, str(rows(page)))
    ok("không console.error", not errors, str(errors)[:200])
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for fn in (sample_filters, completed_detail, linked_mocks):
        try:
            fn(browser)
        except Exception as e:  # noqa: BLE001
            ok(f"{fn.__name__}: chạy hết không văng", False, repr(e)[:400])
    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
