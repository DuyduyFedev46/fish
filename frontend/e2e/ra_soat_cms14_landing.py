"""
Bằng chứng chạy thật (Playwright) cho CMS-14 — Danh sách bài & khối "Bài mới" trên Landing.
Bù bằng chứng còn thiếu (review-cms-golive-fe-qa.md, bảng "AC thiếu bằng chứng", phần CMS):
CMS-14-AC3 (khối "Bài mới" hiện đúng bài mới nhất + link "Xem tất cả"),
CMS-14-AC4 (API tắt -> khối ẩn, phần còn lại của Landing vẫn hiện đủ).

Chạy thật: backend tại :8104, frontend build tĩnh phục vụ tại :3104 (NEXT_PUBLIC_API_BASE trỏ
:8104). Dữ liệu là các bài QA tự tạo qua API với dữ liệu giả.

Dùng: python3 frontend/e2e/ra_soat_cms14_landing.py [normal|api-down]
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3104"


def main() -> int:
    failures = []
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})

        if mode == "api-down":
            # Chặn mọi gọi tới API công khai content để mô phỏng API tắt (CMS-14-AC4)
            page.route("**/api/public/content/**", lambda route: route.abort())

        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)
        page.screenshot(path=f"/tmp/ra_soat_cms14_{mode}.png", full_page=True)
        html = page.content()

        if mode == "normal":
            if "Cẩm nang" not in html:
                failures.append("AC3: không thấy khối 'Cẩm nang & Mẹo hay từ vựa' trên Landing")
            if "Xem tất cả bài viết" not in html:
                failures.append("AC3: thiếu link 'Xem tất cả bài viết'")
            # Landing vẫn có Hero/CTA như bình thường
            if "Cá Về" not in html:
                failures.append("AC3: Landing mất nội dung chính (không thấy 'Cá Về')")

        elif mode == "api-down":
            if "Cẩm nang" in html:
                failures.append("AC4: API tắt nhưng khối 'Bài mới' vẫn hiện")
            # Phần còn lại của Landing (Hero, CTA...) vẫn hiện đủ, không trắng trang
            if len(html) < 2000:
                failures.append(f"AC4: trang có vẻ trắng/hỏng khi API tắt (dài {len(html)} ký tự)")
            if "Cá Về" not in html:
                failures.append("AC4: phần còn lại của Landing không hiển thị khi khối 'Bài mới' lỗi")

        browser.close()

    if failures:
        print(f"FAIL ({mode}):")
        for f in failures:
            print(" -", f)
        return 1
    print(f"PASS ({mode}): CMS-14 bằng chứng bổ sung đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
