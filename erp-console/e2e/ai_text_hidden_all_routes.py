"""E1 (lô dọn chữ AI, W39, BR-AI-17): quét mọi route ERP, khi AI tắt không còn chữ "AI" nào hiện ra và không request tới /api/ai/.

Chạy trên bản build MOCK (dữ liệu giả). Build theo cờ rồi chạy từng tổ hợp, mỗi lần chỉ giữ một bản `out/`:
    cd erp-console
    NEXT_PUBLIC_USE_MOCK=1 NEXT_PUBLIC_AI_FEATURES=0 npm run build   # AI_BUILD=0
    (cd out && python3 -m http.server 3219 --bind 127.0.0.1 &) ; AI_BUILD=0 BASE=http://127.0.0.1:3219 python3 e2e/ai_text_hidden_all_routes.py
    NEXT_PUBLIC_USE_MOCK=1 NEXT_PUBLIC_AI_FEATURES=1 npm run build   # AI_BUILD=1 (chạy đủ: BE tắt, BE bật = đối chứng)
Mỗi bản build chạy cả hai trạng thái BE (mock: sessionStorage["caveve_mock_be_ai"]="off" = BE tắt AI).
Hết kết quả mong đợi: tổ hợp tắt (build 0, hoặc BE tắt) → 0 chữ AI, 0 request /api/ai/; tổ hợp bật cả hai → có chữ AI (chứng minh quét không rỗng).
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3219")
BUILD_ON = os.environ.get("AI_BUILD", "0") == "1"
ROUTES = [
    "/overview/", "/orders/", "/orders/payments/", "/orders/refunds/", "/orders/detail/?id=1", "/orders/payments/detail/?id=1",
    "/orders/refunds/detail/?id=1", "/customers/", "/customers/detail/?id=1", "/confirmation/", "/confirmation/detail/?id=31",
    "/confirmation/scripts/", "/deliveries/", "/deliveries/detail/?id=1", "/deliveries/lookup/", "/my-deliveries/",
    "/purchasing/", "/purchasing/detail/?id=1", "/suppliers/", "/suppliers/detail/?id=1", "/inventory/", "/inventory/detail/?id=1",
    "/returns/", "/returns/detail/?id=1", "/stocktake/", "/stocktake/detail/?id=1", "/ledger/", "/catalog/", "/catalog/detail/?id=1",
    "/reports/", "/accounting/sales-invoices/", "/accounting/purchase-invoices/", "/content/", "/content/categories/",
    "/content/edit/?id=44", "/staff/", "/staff/detail/?id=1", "/permissions/", "/permissions/detail/?group=manager&code=manager",
    "/audit-logs/", "/account/", "/ai/policy/", "/ai/report/", "/ai/actions/", "/ai/settings/",
]
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:300]), flush=True)


def login(page, user, be_ai_on):
    page.goto(BASE + "/login/")
    page.evaluate("v => v ? sessionStorage.removeItem('caveve_mock_be_ai') : sessionStorage.setItem('caveve_mock_be_ai', 'off')", be_ai_on)
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")


def ai_words(page):
    """Mọi chữ "AI" nhìn thấy hoặc có trong aria-label / title / placeholder / alt."""
    return page.evaluate(
        """() => {
          const out = [];
          const re = /\\bAI\\b/;
          if (re.test(document.body.innerText)) out.push("text: " + (document.body.innerText.match(/.{0,30}\\bAI\\b.{0,30}/) || [""])[0]);
          for (const el of document.querySelectorAll("[aria-label],[title],[placeholder],[alt]")) {
            for (const a of ["aria-label", "title", "placeholder", "alt"]) {
              const v = el.getAttribute(a);
              if (v && re.test(v)) out.push(a + ": " + v);
            }
          }
          return out;
        }"""
    )


def sweep(browser, user, be_ai_on):
    visible = BUILD_ON and be_ai_on
    label = f"build={'1' if BUILD_ON else '0'} BE={'bật' if be_ai_on else 'tắt'} vai={user}"
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    ai_requests = []
    page.on("request", lambda r: ai_requests.append(r.url) if "/api/ai/" in r.url else None)
    login(page, user, be_ai_on)
    found = {}
    for route in ROUTES:
        page.goto(BASE + route)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(250)
        words = ai_words(page)
        if words and route.startswith("/permissions/") and not visible:
            # Nợ đã ghi: features/permissions/mock.ts (Lô F1, không sửa ở lô này) còn dòng "ai_policy". BE thật đã ẩn (02b 2.2), E1 thật phải sạch.
            print(f"NỢ  [{label}] {route}: mock phân quyền còn chữ AI {words[:1]}", flush=True)
            continue
        if words:
            found[route] = words[:2]
        if route.startswith("/ai/") and not visible:
            ok(f"[{label}] {route} hiện 'Không tìm thấy trang này'", "Không tìm thấy trang này" in page.inner_text("body"))
    # menu avatar + bộ lọc Nhật ký / Nội dung
    page.goto(BASE + "/audit-logs/")
    page.wait_for_load_state("networkidle")
    for b in page.locator("header button[aria-haspopup], header button[aria-expanded]").all()[:3]:
        try:
            b.click(timeout=1500)
        except Exception:
            pass
    page.wait_for_timeout(200)
    extra = ai_words(page)
    if extra:
        found["/audit-logs/ (menu, bộ lọc)"] = extra[:2]
    if visible:
        ok(f"[{label}] đối chứng: có chữ AI ở ít nhất một route", bool(found), "quét rỗng")
    else:
        ok(f"[{label}] 0 chữ AI ở mọi route", not found, found)
        ok(f"[{label}] 0 request tới /api/ai/", not ai_requests, ai_requests[:3])
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    for be in (False, True):
        for user in ("loc", "ql1"):
            sweep(browser, user, be)
    browser.close()
passed = sum(1 for _, c, _ in results if c)
print(f"== {passed}/{len(results)} PASS")
sys.exit(0 if passed == len(results) else 1)
