"""
Bằng chứng chạy thật (Playwright) cho CMS-03-AC13 — Màn soạn bài trên điện thoại (375×667).
Bù bằng chứng còn thiếu theo doc/features/2026-09-30-review-p1-p7/review-cms-golive-fe-qa.md
(bảng "AC thiếu bằng chứng", phần CMS): trước đây QA chỉ đọc file CSS, chưa đo thật trên trình
duyệt.

Chạy thật: backend Django tại :8104 (BE thật, KHÔNG mock), erp-console build tĩnh phục vụ ở
:3204 (NEXT_PUBLIC_API_BASE=http://localhost:8104). Tài khoản QA tự tạo (`ra_soat_quanly`,
nhóm manager), dữ liệu giả.

Dùng: python3 erp-console/e2e/ra_soat_cms03_ac13_mobile.py
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3204"
ENTRY_ID = "2"  # bài nháp/đã đăng do QA tạo qua API (dữ liệu giả)


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
        ctx = browser.new_context(viewport={"width": 375, "height": 667})
        page = ctx.new_page()
        login(page)

        page.goto(f"{BASE}/content/edit/?id={ENTRY_ID}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        page.screenshot(path="/tmp/ra_soat_cms03_ac13_full.png", full_page=True)

        # 1. Không cuộn ngang
        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        client_w = page.evaluate("document.documentElement.clientWidth")
        if scroll_w > client_w + 2:
            failures.append(f"Cuộn ngang ở 375px (scrollWidth={scroll_w} > clientWidth={client_w})")

        # 2. Mọi nút thanh công cụ có vùng chạm >= 44x44 px
        boxes = page.eval_on_selector_all(
            "button",
            "els => els.map(e => { const r = e.getBoundingClientRect(); "
            "return {t: (e.textContent||'').trim().slice(0,24), w: r.width, h: r.height}; })",
        )
        too_small = [b for b in boxes if b["w"] > 0 and (b["w"] < 44 or b["h"] < 44)]
        if too_small:
            failures.append(f"Nút thao tác nhỏ hơn 44x44px: {too_small}")
        if len(boxes) < 10:
            failures.append(f"Chỉ tìm thấy {len(boxes)} nút — có thể trang chưa tải xong toolbar")

        # 3. Nút "Lưu nháp" luôn thấy được kể cả khi vùng nhìn thấy bị thu hẹp (mô phỏng bàn phím mở)
        save_btn = page.get_by_role("button", name="Lưu nháp")
        if save_btn.count() == 0:
            failures.append("Không tìm thấy nút 'Lưu nháp'")
        else:
            visible_before = save_btn.first.is_visible()
            page.set_viewport_size({"width": 375, "height": 260})  # mô phỏng bàn phím ảo chiếm ~400px
            page.wait_for_timeout(300)
            visible_after = save_btn.first.is_visible()
            box = save_btn.first.bounding_box()
            in_viewport = bool(box) and box["y"] >= 0 and (box["y"] + box["height"]) <= 260 + 2
            page.screenshot(path="/tmp/ra_soat_cms03_ac13_keyboard_open.png")
            if not (visible_before and visible_after and in_viewport):
                failures.append(
                    f"Nút 'Lưu nháp' không còn thấy được khi vùng nhìn thấy bị thu hẹp "
                    f"(visible_before={visible_before}, visible_after={visible_after}, box={box})"
                )

        browser.close()

    if failures:
        print("FAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS: CMS-03-AC13 (bằng chứng bổ sung) đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
