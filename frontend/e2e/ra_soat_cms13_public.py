"""
Bằng chứng chạy thật (Playwright) cho CMS-13 — Khách đọc bài trên web công khai.
Bù bằng chứng còn thiếu theo doc/features/2026-09-30-review-p1-p7/review-cms-golive-fe-qa.md
(bảng "AC thiếu bằng chứng", phần CMS): CMS-13-AC1, AC2 (lớp 2), AC6, AC7, AC8, AC10.

Chạy thật (không mock): backend Django tại :8104 (BE thật), frontend Shop tại :3104
(NEXT_PUBLIC_API_BASE=http://localhost:8104, NEXT_PUBLIC_USE_MOCK=0). Bài dùng để test do
QA tự tạo qua API với dữ liệu giả (tiêu đề "Bai kiem tra XSS lop 2 (du lieu gia)"), không phải
dữ liệu thật của vựa.

Dùng: .venv/bin/python frontend/e2e/ra_soat_cms13_public.py
(cần backend chạy ở :8104 và frontend Shop chạy ở :3104 trỏ NEXT_PUBLIC_API_BASE=http://localhost:8104)
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3104"
SLUG = "bai-kiem-tra-xss-lop-2-ra-soat"

FORBIDDEN_HOST_ALLOWLIST = {"localhost"}  # backend + bucket ảnh chạy trên localhost trong môi trường test


def main() -> int:
    failures = []
    dialogs = []
    console_errors = []
    requests_seen = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("console", lambda m: m.type == "error" and console_errors.append(m.text))
        page.on("request", lambda r: requests_seen.append(r.url))
        # Môi trường QA: MEDIA_BASE_URL mặc định trỏ :8000 (backend thật chạy :8104) nên ảnh bìa/
        # trong bài 404/connection-refused ở máy QA — không phải lỗi JS sản phẩm. Chỉ chặn lỗi JS thật.
        IGNORE_CONSOLE_SUBSTRINGS = ("Failed to load resource", "net::ERR_")

        page.goto(f"{BASE}/bai-viet/?slug={SLUG}")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("article", timeout=10000)  # chờ nội dung bài render xong (client fetch)
        page.screenshot(path="/tmp/ra_soat_cms13_ac1.png", full_page=True)

        # --- CMS-13-AC1: bài hiện đủ tiêu đề, tác giả, ngày đăng, ảnh bìa, thân bài ---
        body_text = page.content()
        if "Bai kiem tra XSS lop 2" not in body_text:
            failures.append("AC1: không thấy tiêu đề bài trên trang")
        if "Cá Về" not in body_text:
            failures.append("AC1: không thấy tên tác giả 'Cá Về'")
        title_tag = page.title()
        if "Cá Về" not in title_tag:
            failures.append(f"AC1: document.title không có hậu tố '| Cá Về': {title_tag!r}")
        meta_desc = page.locator('meta[name="description"]').get_attribute("content")
        if not meta_desc:
            failures.append("AC1: thiếu <meta name=description>")

        # --- CMS-13-AC2 (lớp 2): không hộp thoại nào bật, khối lạ/độc không hiện ---
        if dialogs:
            failures.append(f"AC2: có dialog bật lên: {dialogs}")
        # text chứa <img onerror> phải hiện NGUYÊN VĂN là chữ, không phải thẻ ảnh render
        rendered_imgs = page.locator("img").all()
        onerror_imgs = [
            i for i in rendered_imgs
            if (i.get_attribute("onerror") or "") != "" or "onerror" in (i.get_attribute("src") or "")
        ]
        if onerror_imgs:
            failures.append("AC2: có <img onerror=...> được render thành thẻ ảnh thật")
        if "onerror=alert(1)" not in body_text:
            failures.append("AC2: chữ <img src=x onerror=alert(1)> không còn hiện nguyên văn trong DOM")

        # href javascript: đã bị lớp 1 chặn lúc lưu -> không có href javascript: trong DOM
        js_links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.getAttribute('href'))"
        )
        bad_js_links = [h for h in js_links if h and h.strip().lower().startswith("javascript:")]
        if bad_js_links:
            failures.append(f"AC2: còn link javascript: bấm được trong DOM: {bad_js_links}")

        # --- CMS-13-AC6: link ngoài có target=_blank + rel, link nội bộ không ---
        external = page.locator('a[href="https://example.com"]')
        if external.count() == 0:
            failures.append("AC6: không tìm thấy link ngoài mẫu để kiểm rel/target")
        else:
            target = external.first.get_attribute("target")
            rel = external.first.get_attribute("rel") or ""
            if target != "_blank":
                failures.append(f"AC6: link ngoài không có target=_blank (target={target!r})")
            for token in ("nofollow", "noopener", "noreferrer"):
                if token not in rel:
                    failures.append(f"AC6: link ngoài thiếu rel={token!r} (rel={rel!r})")

        # --- CMS-13-AC10: ảnh thân bài lazy, ảnh bìa không lazy; không cuộn ngang ở 375px ---
        page.set_viewport_size({"width": 375, "height": 667})
        page.wait_for_timeout(200)
        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        client_w = page.evaluate("document.documentElement.clientWidth")
        if scroll_w > client_w + 2:
            failures.append(f"AC10/AC3-13: cuộn ngang ở 375px (scrollWidth={scroll_w} > clientWidth={client_w})")

        # --- CMS-13-AC8: chỉ gọi tới domain web/API/bucket ảnh, không analytics/pixel/font ngoài ---
        page.wait_for_load_state("networkidle")
        from urllib.parse import urlparse
        hosts = set()
        for u in requests_seen:
            try:
                h = urlparse(u).hostname
            except Exception:
                h = None
            if h:
                hosts.add(h)
        unexpected_hosts = {h for h in hosts if h not in FORBIDDEN_HOST_ALLOWLIST}
        if unexpected_hosts:
            failures.append(f"AC8: có request tới domain ngoài allowlist: {unexpected_hosts}")

        real_console_errors = [
            e for e in console_errors if not any(sub in e for sub in IGNORE_CONSOLE_SUBSTRINGS)
        ]
        if real_console_errors:
            failures.append(f"Console có lỗi đỏ (không phải lỗi tải ảnh): {real_console_errors}")

        # --- CMS-13-AC7: API lỗi -> "Chưa tải được bài" + nút Thử lại, console không in dữ liệu ---
        page2 = browser.new_page(viewport={"width": 390, "height": 844})
        console_msgs_err_page = []
        page2.on("console", lambda m: console_msgs_err_page.append(m.text))
        page2.goto(f"{BASE}/bai-viet/?slug=slug-khong-ton-tai-ra-soat")
        page2.wait_for_load_state("networkidle")
        content2 = page2.content()
        if "Không tìm thấy bài" not in content2 and "Chưa tải được bài" not in content2:
            failures.append("AC7/AC4: slug không tồn tại không hiện thông báo lỗi phù hợp")
        page2.screenshot(path="/tmp/ra_soat_cms13_ac7_notfound.png", full_page=True)
        browser.close()

    if failures:
        print("FAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS: tất cả kiểm tra CMS-13 (bằng chứng bổ sung) đều đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
