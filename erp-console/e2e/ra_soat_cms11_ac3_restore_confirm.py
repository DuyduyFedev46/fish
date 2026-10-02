"""
Bằng chứng chạy thật (Playwright) cho CMS-11-AC3 — Khôi phục phiên bản khi bản đang soạn có
thay đổi chưa đăng phải hỏi xác nhận trước. Bù bằng chứng còn thiếu (review-cms-golive-fe-qa.md).

Chạy thật: backend :8104, erp-console build tĩnh :3204. Cần bài đã đăng (>=1 phiên bản) và ĐANG
có thay đổi chưa đăng (has_unpublished_changes=true) — chuẩn bị qua API trước khi chạy.

Dùng: python3 erp-console/e2e/ra_soat_cms11_ac3_restore_confirm.py
"""
import re
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3204"
ENTRY_ID = "2"


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
        page.wait_for_timeout(1000)

        # Lô 16 (ED-36): "Lịch sử phiên bản" nằm trong menu "…" (nút "Thêm thao tác") của màn soạn bài.
        more_btn = page.get_by_role("button", name=re.compile("Thêm|Khác|Thao tác")).last
        if more_btn.count() == 0:
            print("FAIL: không tìm thấy menu '…' — dừng test.")
            return 1
        more_btn.click()
        history_item = page.get_by_role("menuitem").filter(has_text="Lịch sử phiên bản").first
        if history_item.count() == 0:
            print("FAIL: không tìm thấy mục 'Lịch sử phiên bản' — dừng test.")
            return 1
        history_item.click()
        page.wait_for_timeout(500)

        restore_btn = page.get_by_role("button", name="Khôi phục phiên bản này").first
        if restore_btn.count() == 0:
            print("FAIL: không tìm thấy nút 'Khôi phục phiên bản này' — dừng test (cần >=1 phiên bản).")
            return 1

        restore_btn.click()
        page.wait_for_timeout(300)

        # Hộp xác nhận "Khôi phục phiên bản này?" (ConfirmModal, role=dialog) phải hiện, có câu nêu bản đang soạn sẽ bị thay.
        confirm = page.get_by_role("dialog").filter(has_text="Khôi phục phiên bản này?")
        if confirm.count() == 0:
            failures.append("AC3: bấm 'Khôi phục phiên bản này' khi có thay đổi chưa đăng nhưng KHÔNG hỏi xác nhận")
        else:
            body = confirm.first.inner_text()
            if "Bản đang soạn" not in body:
                failures.append(f"AC3: nội dung hộp xác nhận không rõ ràng: {body!r}")
            confirm.first.get_by_role("button", name="Quay lại").click()

        # Huỷ hộp thoại (đã dismiss ở trên) -> tiêu đề đang soạn KHÔNG bị đổi
        html = page.content()
        if "sua nhap" not in html:
            failures.append("AC3: huỷ xác nhận nhưng nội dung đang soạn đã bị thay đổi")

        browser.close()

    if failures:
        print("FAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS: CMS-11-AC3 (bằng chứng bổ sung) đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
