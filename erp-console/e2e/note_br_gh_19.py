"""E3 (lô dọn chữ AI): ghi chú huỷ đơn / lý do quyết định (BR-GH-19) trên bản build MOCK, dữ liệu giả.
Chạy: BASE=http://127.0.0.1:3219 python3 e2e/note_br_gh_19.py   (out/ phục vụ tĩnh, xem ai_text_hidden_all_routes.py)"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3219")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:300]), flush=True)


def login(page, user):
    page.goto(BASE + "/login/")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_context(viewport={"width": 390, "height": 800}, reduced_motion="reduce").new_page()
    login(page, "loc")
    # --- huỷ đơn
    page.goto(BASE + "/orders/detail/?id=104")
    page.wait_for_load_state("networkidle")
    ok("đơn chưa huỷ: không có dòng 'Ghi chú huỷ'", page.get_by_text("Ghi chú huỷ").count() == 0)
    page.locator("main").get_by_role("button", name="Huỷ đơn").first.click()
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    dlg.get_by_label("Lý do huỷ", exact=False).first.select_option("CUSTOMER_CHANGED_MIND")
    note = dlg.locator("textarea")
    ok("ô ghi chú maxLength 200", note.get_attribute("maxlength") == "200", note.get_attribute("maxlength"))
    bad = "Khách đưa số 0901234567 để hoàn"
    note.fill(bad)
    dlg.get_by_role("button", name="Tiếp tục").click() if dlg.get_by_role("button", name="Tiếp tục").count() else dlg.locator("button.primary, button.btn.primary").last.click()
    page.wait_for_timeout(300)
    dlg.get_by_role("button", name="Huỷ đơn").last.click()
    page.wait_for_timeout(500)
    ok("hộp vẫn mở sau lỗi BR-GH-19", page.get_by_role("dialog").count() == 1)
    err_text = page.get_by_role("dialog").inner_text()
    ok("lỗi hiện dưới ô ghi chú", "Không ghi SĐT hay số tài khoản" in err_text, err_text[:200])
    ok("chữ đã gõ còn nguyên", page.get_by_role("dialog").locator("textarea").input_value() == bad)
    page.screenshot(path=f"{SHOTS}/e3-cancel-error-mobile.png")
    page.get_by_role("dialog").locator("textarea").fill("Khách đổi ý, hoàn tiền")
    page.get_by_role("dialog").locator("button.primary, button.btn.primary").last.click()
    page.wait_for_timeout(300)
    page.get_by_role("dialog").get_by_role("button", name="Huỷ đơn").last.click()
    page.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=8000)
    page.wait_for_load_state("networkidle")
    page.get_by_text("Ghi chú huỷ").first.wait_for(timeout=8000)
    ok("sửa lại thì huỷ được, chi tiết hiện 'Ghi chú huỷ'", page.get_by_text("Ghi chú huỷ").count() >= 1 and "Khách đổi ý, hoàn tiền" in page.inner_text("main"))
    # --- quyết định CSKH
    page.goto(BASE + "/confirmation/detail/?id=28")
    page.wait_for_load_state("networkidle")
    ok("chưa quyết định: không có dòng 'Lý do quyết định'", page.get_by_text("Lý do quyết định").count() == 0)
    page.get_by_role("button", name="Quyết định").first.click()
    dlg = page.get_by_role("dialog")
    dlg.wait_for()
    dlg.get_by_label("Bỏ qua gọi xác nhận").check()
    dlg.locator("textarea").fill("Khách quen 0901234567")
    dlg.get_by_role("button", name="Lưu quyết định").click()
    page.wait_for_timeout(400)
    # Máy khách đã chặn trước (noteError); đường BE trả BR-GH-19 được vitest khoá ở mock (decisionNote.test.ts).
    ok("quyết định: hộp vẫn mở + lỗi dưới ô lý do", page.get_by_role("dialog").count() == 1 and "không được chứa số điện thoại" in page.get_by_role("dialog").inner_text())
    ok("quyết định: chữ còn nguyên", page.get_by_role("dialog").locator("textarea").input_value() == "Khách quen 0901234567")
    page.get_by_role("dialog").locator("textarea").fill("Khách quen, giao luôn")
    page.get_by_role("dialog").get_by_role("button", name="Lưu quyết định").click()
    page.wait_for_function("() => document.querySelectorAll('[role=dialog]').length === 0", timeout=8000)
    page.get_by_text("Lý do quyết định").first.wait_for(timeout=8000)
    ok("chi tiết hiện 'Lý do quyết định'", "Khách quen, giao luôn" in page.inner_text("main"))
    browser.close()
passed = sum(1 for _, c, _ in results if c)
print(f"== {passed}/{len(results)} PASS")
sys.exit(0 if passed == len(results) else 1)
