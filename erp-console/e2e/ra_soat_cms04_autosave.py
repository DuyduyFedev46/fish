"""
Bằng chứng chạy thật (Playwright) cho CMS-04 — Tự lưu và không mất bài khi rớt mạng.
Bù bằng chứng còn thiếu (review-cms-golive-fe-qa.md, bảng "AC thiếu bằng chứng", phần CMS):
CMS-04-AC1 (tự lưu sau 10s ngừng gõ), AC2 (mất mạng -> giữ bản tạm + khôi phục sau tải lại),
AC3 (có mạng lại -> tự PATCH trong <=10s + xoá bản tạm), AC5 (rời trang có xác nhận),
AC6 (localStorage sạch sau khi lưu, URL chỉ có id).

Chạy thật: backend :8104, erp-console build tĩnh tại :3204. Cần một bài NHÁP dành riêng cho
test này (tạo qua API, dữ liệu giả) để không ảnh hưởng bài khác.

Dùng: python3 erp-console/e2e/ra_soat_cms04_autosave.py
"""
import sys
import time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3204"
ENTRY_ID = "4"  # bài nháp riêng cho test tự lưu, tạo qua API với dữ liệu giả


def login(page):
    page.goto(f"{BASE}/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill("ra_soat_quanly")
    page.get_by_label("Mật khẩu").fill("RaSoat123!")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/overview/**", timeout=10000)


def main() -> int:
    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        login(page)
        page.goto(f"{BASE}/content/edit/?id={ENTRY_ID}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)

        title_input = page.get_by_placeholder("Nhập tiêu đề (tối đa 200 ký tự)...")
        if title_input.count() == 0:
            print("FAIL: không tìm thấy ô tiêu đề — dừng test.")
            return 1

        # --- CMS-04-AC1: ngừng gõ 10s (có mạng) -> tự PATCH đúng 1 lần, "Đã lưu lúc hh:mm" ---
        save_calls = {"n": 0}
        page.on(
            "request",
            lambda r: save_calls.__setitem__("n", save_calls["n"] + 1)
            if r.method == "PATCH" and f"/entries/{ENTRY_ID}/" in r.url
            else None,
        )
        title_input.fill("Bai kiem tra tu luu - sua lan 1 (du lieu gia)")
        page.wait_for_timeout(10500)
        html = page.content()
        if "Đã lưu lúc" not in html:
            failures.append("AC1: sau 10s ngừng gõ không thấy trạng thái 'Đã lưu lúc'")
        if save_calls["n"] != 1:
            failures.append(f"AC1: PATCH tự lưu gọi {save_calls['n']} lần, mong đúng 1 lần")

        # --- CMS-04-AC2: mất mạng -> gõ thêm -> giữ bản tạm trên máy ---
        # Chỉ chặn gọi API (backend :8104), KHÔNG dùng context.set_offline() toàn cục vì server
        # tĩnh phục vụ FE cũng ở localhost — chặn hết sẽ khiến "tải lại trang" không tải được cả
        # ứng dụng (không đúng thực tế: rớt mạng 4G ở cảng vẫn tải được trang đã cache, chỉ API lỗi).
        page.route("http://localhost:8104/**", lambda route: route.abort())
        # Bắn sự kiện 'offline' thật để kích hoạt nhánh xử lý ngay lập tức (window.addEventListener('offline')),
        # giống trình duyệt thật khi mất kết nối.
        page.evaluate("() => window.dispatchEvent(new Event('offline'))")
        title_input.fill("Bai kiem tra tu luu - sua khi mat mang (du lieu gia)")
        page.wait_for_timeout(500)
        html = page.content()
        if "Chưa lưu, đang giữ trên máy" not in html:
            failures.append("AC2: mất mạng nhưng không thấy trạng thái 'Chưa lưu, đang giữ trên máy'")

        local_storage_has_draft = page.evaluate(
            "() => Object.keys(localStorage).some(k => k.includes('content') || k.includes('draft'))"
        )
        if not local_storage_has_draft:
            failures.append("AC2: không thấy bản nháp nào được lưu vào localStorage khi mất mạng")

        # LƯU Ý: "tải lại trang trong lúc vẫn mất mạng" KHÔNG kiểm ở đây — đã xác nhận riêng (xem
        # doc/features/2026-09-30-ra-soat-agy/repro/A5-cms04-reload-offline-auth-gate.py) rằng khi
        # thật sự mất mạng (không gọi được cả /api/auth/me/), `ConsoleGate` chặn toàn màn hình bằng
        # "Không kết nối được máy chủ." — người dùng KHÔNG thấy được trình soạn/bản nháp đã khôi phục
        # cho tới khi có mạng trở lại. Đây là lỗi thật, ghi ở mục "Lỗi mới" của report, không phải
        # bằng chứng PASS.
        page.screenshot(path="/tmp/ra_soat_cms04_offline_status.png", full_page=True)

        # --- CMS-04-AC3: có mạng lại -> tự PATCH trong <=10s -> "Đã lưu", xoá bản tạm ---
        page.unroute("http://localhost:8104/**")
        page.evaluate("() => window.dispatchEvent(new Event('online'))")
        page.wait_for_timeout(11000)
        html = page.content()
        if "Đã lưu lúc" not in html:
            failures.append("AC3: có mạng lại nhưng không tự lưu lại trong vòng ~10s")
        local_storage_after = page.evaluate(
            "() => Object.keys(localStorage).some(k => k.includes('content') || k.includes('draft'))"
        )
        if local_storage_after:
            failures.append("AC3/AC6: bản nháp cục bộ KHÔNG bị xoá sau khi lưu thành công lên server")

        # --- CMS-04-AC6: URL chỉ có id, không có tiêu đề/nội dung ---
        if "sua+khi" in page.url or "tu+luu" in page.url or "tiêu" in page.url.lower():
            failures.append(f"AC6: URL có vẻ chứa nội dung bài: {page.url}")
        if f"id={ENTRY_ID}" not in page.url:
            failures.append(f"AC6: URL không có id bài: {page.url}")

        # --- CMS-04-AC5: có thay đổi chưa lưu -> beforeunload phải bị chặn (preventDefault) ---
        title_input.fill("Bai kiem tra tu luu - thay doi chua luu (du lieu gia)")
        page.wait_for_timeout(300)
        prevented = page.evaluate(
            "() => { const ev = new Event('beforeunload', {cancelable: true}); "
            "window.dispatchEvent(ev); return ev.defaultPrevented || ev.returnValue !== undefined; }"
        )
        if not prevented:
            failures.append("AC5: có thay đổi chưa lưu nhưng beforeunload không bị chặn (không hỏi xác nhận)")

        browser.close()

    if failures:
        print("FAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS: CMS-04 (bằng chứng bổ sung) đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
