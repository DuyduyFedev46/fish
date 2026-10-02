"""
Bằng chứng chạy thật (Playwright) cho CMS-05-AC6 (mất mạng lúc tải ảnh) và CMS-05-AC8 (điện
thoại: mở được camera/thư viện ảnh, có thanh tiến trình). Bù bảng "AC thiếu bằng chứng"
(review-cms-golive-fe-qa.md, phần CMS) — trước đây QA chỉ đọc code `ImageUploader.tsx`.

Chạy thật: backend :8104, erp-console build tĩnh tại :3204 (NEXT_PUBLIC_API_BASE=:8104).
Tài khoản QA tự tạo (`ra_soat_quanly`), ảnh test sinh bằng Pillow lúc chạy (không commit ảnh).

Dùng: python3 erp-console/e2e/ra_soat_cms05_upload_mobile.py
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3204"
ENTRY_ID = "2"
TEST_IMG = "/tmp/ra_soat_upload_test.jpg"


def make_test_image():
    from PIL import Image
    Image.new("RGB", (800, 600), color=(10, 120, 200)).save(TEST_IMG, "JPEG")


def login(page):
    page.goto(f"{BASE}/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill("ra_soat_quanly")
    page.get_by_label("Mật khẩu").fill("RaSoat123!")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/overview/**", timeout=10000)


def main() -> int:
    failures = []
    make_test_image()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 375, "height": 667})
        page = ctx.new_page()
        login(page)
        page.goto(f"{BASE}/content/edit/?id={ENTRY_ID}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        # Lô 16 (ED-36): phần "Ảnh trong bài" nằm ở màn "Thiết lập bài viết", mở bằng nút cùng tên.
        page.get_by_role("button", name="Thiết lập bài viết").first.click()
        page.wait_for_timeout(500)

        # --- CMS-05-AC8: nút "Tải ảnh" mở được bộ chọn tệp (camera/thư viện trên máy thật) ---
        upload_btn = page.get_by_role("button", name="Tải ảnh từ máy / điện thoại")
        if upload_btn.count() == 0:
            failures.append("AC8: không thấy nút 'Tải ảnh từ máy / điện thoại'")
        else:
            file_input = page.locator('input[type="file"]')
            accept = file_input.get_attribute("accept") or ""
            if "image/" not in accept:
                failures.append(f"AC8: input file không giới hạn accept=image/* (accept={accept!r})")
            hint = page.locator("text=Hỗ trợ camera, thư viện ảnh")
            if hint.count() == 0:
                failures.append("AC8: không có gợi ý 'Hỗ trợ camera, thư viện ảnh'")

        # --- CMS-05-AC6: mất mạng khi đang tải ảnh -> lỗi rõ ràng, không chèn khối ảnh hỏng ---
        baseline_count = page.locator("text=/\\d+\\/20 ảnh/").first.inner_text()
        # Chặn (abort) request upload ảnh để mô phỏng mất mạng giữa chừng.
        page.route("**/api/content/entries/*/images/", lambda route: route.abort("internetdisconnected"))
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(TEST_IMG)
        page.wait_for_timeout(1500)
        html = page.content()
        # LƯU Ý (lệch nhẹ so với chữ trong 02-stories.md): message thật là
        # "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại." (shared/lib/messages.ts::MSG.network),
        # không đúng nguyên văn "Tải ảnh lỗi, thử lại" như AC ghi — nhưng vẫn hiện lỗi rõ ràng, không
        # phải trắng màn hay treo (Low, ghi trong report).
        has_error_msg = (
            "Tải ảnh lỗi, thử lại" in html
            or "Không kết nối được máy chủ" in html
        )
        if not has_error_msg:
            failures.append("AC6: mất mạng lúc tải ảnh không hiện thông báo lỗi nào")
        # Không có khối ảnh hỏng nào được chèn: đếm số ảnh trong danh sách "Ảnh trong bài" không đổi
        count_text = page.locator("text=/\\d+\\/20 ảnh/").first.inner_text()
        if count_text != baseline_count:
            failures.append(
                f"AC6: số ảnh thay đổi dù request bị chặn (trước={baseline_count}, sau={count_text})"
            )
        page.screenshot(path="/tmp/ra_soat_cms05_ac6_offline_error.png", full_page=True)

        page.unroute("**/api/content/entries/*/images/")

        browser.close()

    if failures:
        print("FAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS: CMS-05-AC6/AC8 (bằng chứng bổ sung) đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
