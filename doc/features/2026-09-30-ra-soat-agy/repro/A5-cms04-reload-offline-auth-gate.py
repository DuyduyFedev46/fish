"""
Repro (ĐỎ — lỗi thật) cho CMS-04-AC2: "sau khi tải lại, nội dung vừa gõ được khôi phục kèm
thông báo" khi mất mạng.

Phát hiện lúc rà soát A5 (2026-09-30-ra-soat-agy) hồ sơ 2026-09-28-cms-viet-bai.

Nguyên nhân: `erp-console/features/auth/components/ConsoleGate.tsx` bắt buộc gọi lại
`/api/auth/me/` mỗi lần tải trang (không cache phiên đăng nhập offline). Khi mạng mất THẬT SỰ
(không chỉ API nội dung mà cả API xác thực cũng không gọi được), `ConsoleGate` render toàn màn
hình "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại." + nút "Thử lại" / "Đăng nhập tài
khoản khác" — CHẶN HẲN truy cập màn soạn bài, nên người dùng KHÔNG thấy được bản nháp đã lưu cục
bộ (`shared/lib/drafts.ts`) cho tới khi có mạng trở lại và xác thực lại thành công.

Điều này ngược với kỳ vọng của CMS-04-AC2 ("sau khi tải lại, nội dung vừa gõ được khôi phục kèm
thông báo") — bản nháp KHÔNG mất (vẫn nằm trong localStorage), nhưng người dùng không thấy được
nó ngay khi cần nhất (đang ở cảng, mất sóng, vừa tải lại trang để xem lại bài).

Cách chạy (cần chuẩn bị theo A5-cms-viet-bai.md — backend thật :8104, erp-console build tĩnh
:3204, user quan_ly `ra_soat_quanly` / `RaSoat123!`, bài nháp id=4):

    python3 doc/features/2026-09-30-ra-soat-agy/repro/A5-cms04-reload-offline-auth-gate.py

Kỳ vọng (AC2): sau reload thấy trình soạn với nội dung "sua khi mat mang" đã khôi phục.
Thực tế: thấy màn lỗi toàn trang "Không kết nối được máy chủ." — script FAIL để chứng minh.
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3204"
ENTRY_ID = "4"


def login(page):
    page.goto(f"{BASE}/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill("ra_soat_quanly")
    page.get_by_label("Mật khẩu").fill("RaSoat123!")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/overview/**", timeout=10000)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        login(page)
        page.goto(f"{BASE}/content/edit/?id={ENTRY_ID}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)

        title_input = page.get_by_placeholder("Nhập tiêu đề (tối đa 200 ký tự)...")
        title_input.fill("sua khi mat mang - repro A5")
        page.wait_for_timeout(400)  # kích hoạt lưu cục bộ qua onChange (drafts.ts)

        # Chặn mọi gọi tới backend (:8104), gồm cả /api/auth/me/ mà ConsoleGate gọi lại lúc tải
        # trang — đây là phần API thật sự "mất mạng"; server tĩnh phục vụ HTML/JS (:3204) vẫn
        # coi như tải được từ cache trình duyệt/CDN, đúng với 4G rớt sóng ở cảng trong đời thực
        # (network-only tới API backend, không phải mất kết nối TCP hoàn toàn).
        page.route("http://localhost:8104/**", lambda route: route.abort())
        page.evaluate("() => window.dispatchEvent(new Event('offline'))")
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        html = page.content()
        page.screenshot(path="/tmp/repro_a5_cms04_reload_offline.png", full_page=True)

        editor_visible = "Nhập tiêu đề" in html or "sua khi mat mang" in html
        blocked_by_gate = "Không kết nối được máy chủ" in html

        print("editor_visible:", editor_visible)
        print("blocked_by_full_page_error:", blocked_by_gate)
        browser.close()

        if blocked_by_gate and not editor_visible:
            print(
                "FAIL (lỗi thật, đúng như mong đợi của repro): ConsoleGate chặn toàn màn hình khi "
                "mất mạng thay vì cho thấy trình soạn + bản nháp đã khôi phục (CMS-04-AC2)."
            )
            return 1
        print("PASS bất ngờ — lỗi có vẻ đã được sửa, cập nhật lại A5-cms-viet-bai.md.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
