# L7-1: đã đăng nhập mà mở /login/?next=<địa chỉ ngoài> thì phải ở lại cùng origin (không mở trang lạ).
# Mock (NEXT_PUBLIC_USE_MOCK=1). Chạy: BASE=http://127.0.0.1:3217 python3 e2e/l7_1_open_redirect.py
import os
import sys
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3217")
ORIGIN = urlparse(BASE).netloc
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


PAYLOADS = [
    ("/%5Cevil.example", "gạch chéo + gạch ngược"),
    ("/%09/evil.example", "tab giữa hai gạch chéo"),
    ("//evil.example", "protocol-relative"),
    ("https://evil.example", "https tuyệt đối"),
    ("javascript:alert(1)", "javascript:"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for user in ("kho1",):
        for raw, label in PAYLOADS:
            ctx = browser.new_context(viewport={"width": 375, "height": 667})
            page = ctx.new_page()
            hosts = []
            page.on("request", lambda r: hosts.append(urlparse(r.url).netloc) if r.is_navigation_request() else None)
            page.goto(BASE + "/login/")
            page.wait_for_load_state("networkidle")
            page.fill("#u", user)
            page.fill("#p", "demo1234")
            page.get_by_role("button", name="Đăng nhập").click()
            page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
            page.wait_for_load_state("networkidle")
            # đã đăng nhập: mở lại trang đăng nhập với next độc hại
            page.goto(BASE + "/login/?next=" + raw)
            page.wait_for_timeout(1500)
            page.wait_for_load_state("networkidle")
            here = urlparse(page.url)
            ok(f"L7-1 [{label}] ở lại cùng origin ({page.url})", here.netloc == ORIGIN)
            ok(f"L7-1 [{label}] không có điều hướng tới host lạ", all(h in ("", ORIGIN) for h in hosts), str(sorted(set(hosts))))
            ok(f"L7-1 [{label}] rơi về trang mặc định, không phải /login/ hay đường dẫn độc", "/login/" not in here.path and "evil" not in page.url)
            ctx.close()
    # hợp lệ: đăng nhập lại cùng người thì vẫn quay lại đúng trang đang dở
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto(BASE + "/login/")
    page.fill("#u", "kho1")
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.goto(BASE + "/login/?next=/print/label/%3Fnote%3D32%26print_no%3D1")
    page.wait_for_function("() => window.location.pathname.startsWith('/print/label/')", timeout=10_000)
    ok("L7-1 next hợp lệ vẫn được theo", "note=32" in page.url and "print_no=1" in page.url, page.url)
    ctx.close()
    browser.close()

fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} PASS")
sys.exit(1 if fails else 0)
