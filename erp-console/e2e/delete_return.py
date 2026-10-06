# E2E ERP #8 (Xoá phiếu hàng hoàn), chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3108 &)
#   BASE=http://127.0.0.1:3108 SHOTS=<thư mục ảnh> python3 e2e/delete_return.py      # tắt server sau khi xong
# Kiểm: Chủ xoá phiếu Nháp (hộp nói "Số kg ... không được nhập lại kho", về danh sách, toast, phiếu biến mất) · phiếu Đã huỷ có nút xoá nhưng
# hộp không có câu nhập kho · phiếu Đã duyệt không có nút · Quản lý không thấy nút · 400 hiện nguyên câu BE · 409 hiện ConflictBanner "Tải lại" ·
# 360px không cuộn ngang · không console.error.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3108")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)
NOT_RESTOCK = "Số kg trên phiếu này sẽ không được nhập lại kho."
# Lớp http bỏ mã quy tắc "(BR-…)" khỏi câu hiện cho người dùng (UI-RULES), phần chữ còn lại giữ nguyên câu của BE.
BE_400 = "Phiếu hàng hoàn đã duyệt (đã nhập lại kho hoặc ghi lỗ) không xoá được."


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


def new_page(browser, user, w=1280, h=860, errors=None):
    errors = errors if errors is not None else []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    login(page, user)
    return ctx, page, errors


def menu_items(page):
    btn = page.get_by_role("button", name="Thao tác khác")
    if btn.count() == 0:
        return []
    btn.click()
    items = [t.strip() for t in page.get_by_role("menuitem").all_inner_texts()]
    page.keyboard.press("Escape")
    return items


def open_delete(page):
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^Xoá phiếu hàng hoàn")).click()
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    return dlg


def hscroll_ok(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def owner(browser):
    ctx, page, errors = new_page(browser, "loc")
    go(page, "/returns/detail/?id=5")
    ok("Chủ: RT-5 (Chờ duyệt) có mục Xoá phiếu hàng hoàn", any(i.startswith("Xoá phiếu hàng hoàn") for i in menu_items(page)), str(menu_items(page)))
    dlg = open_delete(page)
    ok("Chủ: hộp xác nhận nói số kg không nhập lại kho (TL-D8-L3)", NOT_RESTOCK in dlg.inner_text(), dlg.inner_text()[:300])
    page.screenshot(path=f"{SHOTS}/delete-draft-1280.png")
    dlg.get_by_role("button", name="Xoá phiếu hàng hoàn").click()
    page.wait_for_url(re.compile(r"/returns/?$"))
    settle(page)
    ok("Chủ: xoá xong về danh sách", re.search(r"/returns/?$", page.url) is not None, page.url)
    ok("Chủ: có toast 'Đã xoá phiếu hàng hoàn.'", page.get_by_text("Đã xoá phiếu hàng hoàn.").count() >= 1)
    page.wait_for_function("() => document.querySelectorAll('main table tbody tr td:first-child').length > 0")
    codes = [c.strip() for c in page.locator("main table tbody tr td:first-child").all_inner_texts()]
    ok("Chủ: RT-5 không còn trong danh sách", "RT-5" not in codes and "RT-1" in codes, str(codes))
    page.screenshot(path=f"{SHOTS}/delete-done-1280.png")

    go(page, "/returns/detail/?id=6")
    ok("Chủ: RT-6 (Đã huỷ) có mục Xoá", any(i.startswith("Xoá phiếu hàng hoàn") for i in menu_items(page)))
    dlg = open_delete(page)
    ok("Chủ: phiếu Đã huỷ, hộp không có câu nhập kho", NOT_RESTOCK not in dlg.inner_text())
    dlg.get_by_role("button", name="Quay lại").click()
    dlg.wait_for(state="detached")

    go(page, "/returns/detail/?id=3")
    ok("Chủ: RT-3 (Đã duyệt) không có mục Xoá", not any(i.startswith("Xoá") for i in menu_items(page)), str(menu_items(page)))

    # 400: máy khác duyệt trước, FE còn thấy nút
    go(page, "/returns/detail/?id=1")
    dlg = open_delete(page)
    page.evaluate("() => window.__caveMock.returnsMarkApproved(1)")
    dlg.get_by_role("button", name="Xoá phiếu hàng hoàn").click()
    dlg.get_by_role("alert").wait_for()
    ok("Chủ: 400 hiện câu của BE (không kèm mã BR)", BE_400 in dlg.inner_text() and "BR-" not in dlg.inner_text(), dlg.inner_text()[:300])
    ok("Chủ: nút chính đổi 'Thử lại'", dlg.get_by_role("button", name=re.compile("Thử lại")).count() == 1)

    # 409
    go(page, "/returns/detail/?id=2")
    dlg = open_delete(page)
    page.evaluate("() => window.__caveMock.returnsStaleDelete(2)")
    dlg.get_by_role("button", name="Xoá phiếu hàng hoàn").click()
    dlg.locator("[data-conflict-banner]").wait_for()
    ok("Chủ: 409 hiện banner kèm nút Tải lại", dlg.get_by_role("button", name="Tải lại").count() == 1)
    page.screenshot(path=f"{SHOTS}/delete-409-1280.png")
    dlg.get_by_role("button", name="Tải lại").click()
    dlg.wait_for(state="detached")
    ok("Chủ: không console.error", errors == [], str(errors))
    ctx.close()


def manager(browser):
    ctx, page, errors = new_page(browser, "ql1")
    for pid in (1, 6):
        go(page, f"/returns/detail/?id={pid}")
        ok(f"Quản lý: RT-{pid} không có mục Xoá", not any(i.startswith("Xoá") for i in menu_items(page)), str(menu_items(page)))
    ok("Quản lý: không console.error", errors == [], str(errors))
    ctx.close()


def mobile(browser):
    ctx, page, errors = new_page(browser, "loc", w=360, h=740)
    go(page, "/returns/detail/?id=1")
    dlg = open_delete(page)
    ok("360px: hộp xoá không cuộn ngang", hscroll_ok(page))
    box = dlg.get_by_role("button", name="Xoá phiếu hàng hoàn").bounding_box()
    ok("360px: nút Xoá cao >= 44px", box is not None and box["height"] >= 44, str(box))
    page.screenshot(path=f"{SHOTS}/delete-draft-360.png")
    ok("360px: không console.error", errors == [], str(errors))
    ctx.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for fn in (owner, manager, mobile):
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
