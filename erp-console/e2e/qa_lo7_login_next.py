"""QA Lô 7 (do QA viết): open redirect ở đường ĐĂNG NHẬP MỚI (chưa có phiên) với next độc hại. ERP mock (3218)."""
import os, sys
from urllib.parse import urlparse, quote
from playwright.sync_api import sync_playwright
BASE = os.environ.get("BASE", "http://127.0.0.1:3218"); ORIGIN = urlparse(BASE).netloc
PAY = ["/%5Cevil.example", "/%09/evil.example", "//evil.example", "///evil.example", "/%2F/evil.example", "/%2F%2Fevil.example",
       "https://evil.example", "http://evil.example/x", "javascript:alert(1)", "%5C%5Cevil.example", "/%0d%0aevil.example",
       "/%20/evil.example", "/%7F/evil.example", "evil.example", "/" + "a" * 3000, "/..//evil.example", "/.//evil.example"]
res = []
def ok(n, c, e=""):
    res.append(bool(c)); print(("PASS " if c else "FAIL ") + n + ("" if c else f"  <{e}>"))
with sync_playwright() as p:
    b = p.chromium.launch()
    for raw in PAY:
        ctx = b.new_context(viewport={"width": 390, "height": 800}); page = ctx.new_page()
        navs, dialogs = [], []
        ctx.route(lambda u: urlparse(u).hostname == "evil.example", lambda r: (navs.append(r.request.url), r.abort()))
        page.on("request", lambda r: navs.append(r.url) if r.is_navigation_request() and urlparse(r.url).netloc not in ("", ORIGIN) else None)
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.goto(BASE + "/login/?next=" + raw); page.wait_for_load_state("networkidle")
        page.fill("#u", "kho1"); page.fill("#p", "demo1234")
        page.get_by_role("button", name="Đăng nhập").click()
        page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10000)
        page.wait_for_timeout(800)
        u = urlparse(page.url)
        label = raw[:40]
        ok(f"login mới next={label!r}: ở lại origin", u.netloc == ORIGIN, page.url)
        ok(f"login mới next={label!r}: không điều hướng/request tới host lạ, không dialog", not navs and not dialogs, str(navs) + str(dialogs))
        ctx.close()
    b.close()
print(f"Tổng {len(res)} ca, {res.count(False)} FAIL"); sys.exit(1 if False in res else 0)
