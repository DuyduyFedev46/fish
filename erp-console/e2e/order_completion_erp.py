# E2E ERP (W37 L1: đơn Hoàn tất, phía FE mock): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3201 &)
#   SHOTS=<thư mục ảnh> python3 e2e/order_completion_erp.py      # tắt server sau khi xong
# Kiểm: NV giao bấm Đã giao xong thì toast nói "Đơn đã hoàn tất" (S1) · bộ lọc đơn không còn "Đã thanh toán", còn "Chưa xong" (S6) ·
# thanh bước của đơn có 5 bước, "Chờ gọi xác nhận" thay "Đã thanh toán", đơn Hoàn tất sáng bước Hoàn tất (S7) · 360px không cuộn ngang.
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


def courier_completes(browser):
    ctx, page, errors = new_page(browser, "giao1", 360, 740, touch=True)
    settle(page)
    page.locator("[data-group='DELIVERING']").first.get_by_role("button", name="Đã giao xong").first.click()
    dlg = page.get_by_role("dialog", name="Xác nhận đã giao xong")
    expect(dlg).to_be_visible()
    dlg.get_by_role("button", name="Đã giao xong").click()
    toast = page.get_by_text("Đã giao xong. Đơn đã hoàn tất.")
    expect(toast).to_be_visible()
    ok("S1: giao xong phiếu cuối thì toast 'Đã giao xong. Đơn đã hoàn tất.'", True)
    page.screenshot(path=os.path.join(SHOTS, "order_completion_toast_360.png"))
    ok("giao1 360px: không cuộn ngang", no_hscroll(page))
    ok("không console.error", not errors, str(errors)[:200])
    ctx.close()


def orders_filter_and_steps(browser):
    ctx, page, errors = new_page(browser, "ql1")
    go(page, "/orders/")
    options = page.get_by_label("Lọc theo trạng thái").locator("option").all_inner_texts()
    ok("S6: bộ lọc không còn 'Đã thanh toán'", "Đã thanh toán" not in options, str(options))
    ok("S6: bộ lọc còn 'Chưa xong' và 'Đang xử lý' và 'Hoàn tất'", all(x in options for x in ("Chưa xong", "Đang xử lý", "Hoàn tất")), str(options))
    page.screenshot(path=os.path.join(SHOTS, "order_completion_filter_1280.png"))
    go(page, "/orders/detail/?id=109")
    steps = [t.strip().removeprefix("check").strip() for t in page.locator("ol li").all_inner_texts()][:5]
    ok("S7: thanh bước 5 bước, Chờ gọi xác nhận thay Đã thanh toán", steps == ["Giữ chỗ", "Chờ gọi xác nhận", "Soạn hàng", "Đang giao", "Hoàn tất"], str(steps))
    page.screenshot(path=os.path.join(SHOTS, "order_completion_steps_1280.png"))
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for fn in (courier_completes, orders_filter_and_steps):
        try:
            fn(browser)
        except Exception as e:  # noqa: BLE001
            ok(f"{fn.__name__}: chạy hết không văng", False, repr(e)[:300])
    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
