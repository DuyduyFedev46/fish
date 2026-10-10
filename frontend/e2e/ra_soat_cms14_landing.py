"""
Bằng chứng chạy thật (Playwright) cho trang giới thiệu `/gioi-thieu/` (SHOP-1-08) và trang 404 (SHOP-1-09).
Landing cũ ở `/` đã chuyển sang `/gioi-thieu/` (decisions 2026-10-10, SHOP-1-08 AC4), nên kịch bản CMS-14 cũ trỏ sang đây.

Chạy thật: backend tại :8104 đã chạy `manage.py load_shop_content --author <chủ> --publish` (dữ liệu giả),
frontend build tĩnh (NEXT_PUBLIC_USE_MOCK=0, NEXT_PUBLIC_API_BASE trỏ :8104) phục vụ tại :3104.

Dùng: python3 frontend/e2e/ra_soat_cms14_landing.py [normal|api-down|not-found]
- normal    : chữ nội dung lấy từ CMS, H1 + nút "Xem hàng đang có" -> /shop/, không cụm khẳng định bị chặn (AC1, AC5).
- api-down  : API nội dung bị chặn -> trạng thái lỗi có nút "Thử lại", không trắng trang (06-marketing C7).
- not-found : /khong-co-trang-nay/ -> trang 404 có hai nút, title đúng, có noindex (SHOP-1-09 AC1).
"""
import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3104"
BLOCKED = ("hút chân không", "Cân đúng", "ngay tại cảng", "tươi sống", "miễn phí giao")


def check_normal(page, failures):
    page.goto(f"{BASE}/gioi-thieu/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    html = page.content()
    if page.locator("h1", has_text="Từ cảng về bếp nhà bạn").count() != 1:
        failures.append("AC1: thiếu H1 'Từ cảng về bếp nhà bạn'")
    if "Chúng tôi mua tại cảng, theo từng lô" not in html:
        failures.append("AC1: không thấy chữ lấy từ trang CMS gioi-thieu")
    link = page.get_by_role("link", name="Xem hàng đang có").first
    if link.count() == 0 or "/shop/" not in (link.get_attribute("href") or ""):
        failures.append("AC1: nút 'Xem hàng đang có' không trỏ /shop/")
    for phrase in BLOCKED:
        if phrase in html:
            failures.append(f"AC5: HTML có cụm bị chặn '{phrase}'")
    if page.get_by_text("kg tồn").count() or page.locator("text=/Còn \\d+([,.]\\d+)? kg/").count():
        failures.append("AC2 (G1): có số kg tồn trên thẻ hàng")


def check_api_down(page, failures):
    page.route("**/api/public/content/**", lambda route: route.abort())
    page.goto(f"{BASE}/gioi-thieu/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    html = page.content()
    if "Chưa tải được trang" not in html:
        failures.append("C7: API lỗi nhưng không hiện 'Chưa tải được trang'")
    if page.get_by_role("button", name="Thử lại").count() == 0:
        failures.append("C7: thiếu nút 'Thử lại'")
    if len(html) < 2000:
        failures.append(f"C7: trang có vẻ trắng (dài {len(html)} ký tự)")


def check_not_found(page, failures):
    page.goto(f"{BASE}/khong-co-trang-nay/")
    page.wait_for_load_state("networkidle")
    if page.title() != "Không tìm thấy trang — Cá Về":
        failures.append(f"1-09 AC1: title sai: {page.title()!r}")
    robots = page.locator('meta[name="robots"]').first
    if robots.count() == 0 or "noindex" not in (robots.get_attribute("content") or ""):
        failures.append("1-09 AC1: thiếu meta robots noindex")
    if page.locator("h1", has_text="Không tìm thấy trang này").count() != 1:
        failures.append("1-09 AC1: thiếu tiêu đề 'Không tìm thấy trang này'")
    for name, href in (("Về trang chủ", "/"), ("Xem hàng đang có", "/shop/")):
        link = page.get_by_role("link", name=name).first
        if link.count() == 0 or (link.get_attribute("href") or "").rstrip("/") != href.rstrip("/"):
            failures.append(f"1-09 AC1: nút '{name}' không trỏ {href}")


def main() -> int:
    failures = []
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
    checks = {"normal": check_normal, "api-down": check_api_down, "not-found": check_not_found}
    if mode not in checks:
        print(f"Chế độ không hợp lệ: {mode}")
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 360, "height": 800})
        checks[mode](page, failures)
        page.screenshot(path=f"/tmp/ra_soat_gioi_thieu_{mode}.png", full_page=True)
        browser.close()

    if failures:
        print(f"FAIL ({mode}):")
        for f in failures:
            print(" -", f)
        return 1
    print(f"PASS ({mode}): /gioi-thieu/ và 404 đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
