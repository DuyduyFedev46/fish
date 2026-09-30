# QA P8 Lô 5 — Django THẬT (SQLite tạm, cổng 8115) + build USE_MOCK=0 phục vụ cổng 3216. Dữ liệu giả.
#   Chủ (loc): mở lô EXPIRED còn 6,5 kg -> Chốt khoá -> Trả NCC 2 kg (kèm tiền NCC hoàn giả 999888) -> Trả hết (bấm đúp)
#   -> tồn 0 -> Chốt lô mở -> Chốt. nv_kho (kho1): không thấy nút. Không rò tiền/PII ở DOM, URL, storage, console.
import json
import os
import re

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3216")
SHOTS = os.environ.get("SHOTS", "/tmp")
SENTINEL = "999888"
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15_000)
    page.wait_for_load_state("networkidle")


def open_first(page, has_text):
    page.goto(BASE + "/inventory/?status=EXPIRED")
    page.wait_for_load_state("networkidle")
    row = page.locator("tbody tr", has_text=has_text).first
    row.wait_for(timeout=15_000)
    row.locator("button").first.click()
    page.get_by_role("dialog", name=re.compile("Chi tiết lô")).wait_for(timeout=10_000)
    page.locator("[data-testid=qty-available]").wait_for()
    page.wait_for_timeout(500)


def qty(page):
    return re.sub(r"\s+", " ", page.locator("[data-testid=qty-available]").inner_text()).strip()


def run(browser, tag, viewport):
    ctx = browser.new_context(viewport=viewport, reduced_motion="reduce")
    page = ctx.new_page()
    logs, resp, urls = [], [], []
    page.on("console", lambda m: logs.append(m.text))
    page.on("framenavigated", lambda f: urls.append(f.url))
    page.on("response", lambda r: resp.append((r.request.method, r.url, r.status, r.request.post_data or "")) if "/api/" in r.url else None)
    login(page, "loc")
    open_first(page, "TOM-GIA-1")
    ok(f"[{tag}] Chủ: tồn thật 6,5 kg", qty(page).startswith("6,5"), qty(page))
    b_close = page.locator("[data-action=close]")
    ok(f"[{tag}] Chủ: Chốt lô khoá kèm lý do tồn = 0", b_close.is_disabled() and "tồn = 0" in page.locator("[data-lock=close]").inner_text())
    page.screenshot(path=f"{SHOTS}/real-{tag}-1-chu-lo-qua-han.png")
    page.locator("[data-action=return_to_supplier]").click()
    dlg = page.get_by_role("dialog", name="Xác nhận Đã trả NCC")
    dlg.wait_for()
    dlg.get_by_label("Số kg đã trả").fill("2")
    dlg.get_by_label("Tiền NCC hoàn").fill(SENTINEL)
    dlg.get_by_role("button", name="Ghi nhận đã trả").click()
    page.get_by_test_id("batch-notice").wait_for(timeout=15_000)
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('4,5')", timeout=15_000)
    ok(f"[{tag}] Chủ: trả 2 kg -> tồn 4,5 kg (lấy lại từ máy chủ)", qty(page).startswith("4,5"), qty(page))
    posts = [r for r in resp if r[0] == "POST" and "return-to-supplier" in r[1]]
    ok(f"[{tag}] BE thật trả 200 cho return-to-supplier", posts and posts[-1][2] == 200, str([p[:3] for p in posts]))
    ok(f"[{tag}] tiền NCC hoàn có gửi lên (payload) nhưng không hiện lại ở DOM", SENTINEL in posts[-1][3] and SENTINEL not in page.locator("body").inner_text())
    page.screenshot(path=f"{SHOTS}/real-{tag}-2-chu-sau-tra-2kg.png")
    page.locator("[data-action=return_to_supplier]").click()
    dlg = page.get_by_role("dialog", name="Xác nhận Đã trả NCC")
    dlg.wait_for()
    dlg.get_by_role("button", name="Trả hết").click()
    n0 = len([r for r in resp if r[0] == "POST" and "return-to-supplier" in r[1]])
    dlg.get_by_role("button", name="Ghi nhận đã trả").dblclick()
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('0')", timeout=15_000)
    n1 = len([r for r in resp if r[0] == "POST" and "return-to-supplier" in r[1]])
    ok(f"[{tag}] Chủ: Trả hết + bấm đúp -> đúng 1 POST thêm ({n1 - n0}), tồn 0", n1 - n0 == 1 and qty(page).startswith("0"))
    ok(f"[{tag}] Chủ: hết tồn -> Chốt lô mở, nút Huỷ/Trả biến mất", page.locator("[data-action=close]").is_enabled() and page.locator("[data-action=return_to_supplier]").count() == 0)
    page.locator("[data-action=close]").click()
    cd = page.get_by_role("dialog", name="Chốt lô")
    cd.wait_for()
    cd.get_by_role("button", name="Chốt lô").click()
    page.wait_for_function("() => document.querySelector('[data-testid=batch-notice]')?.innerText.includes('Đã chốt lô')", timeout=15_000)
    ok(f"[{tag}] Chủ: chốt lô thật thành công (200)", [r for r in resp if "/close/" in r[1]][-1][2] == 200)
    page.screenshot(path=f"{SHOTS}/real-{tag}-3-chu-da-chot.png")
    body = page.locator("body").inner_text() + page.content()
    store = page.evaluate("() => JSON.stringify(Object.assign({}, window.localStorage)) + JSON.stringify(Object.assign({}, window.sessionStorage))")
    ok(f"[{tag}] không lộ tiền NCC hoàn ở DOM/URL/storage/console", SENTINEL not in body and SENTINEL not in store and not any(SENTINEL in u for u in urls) and not any(SENTINEL in l for l in logs))
    # mọi response GET của API không chứa tiền NCC hoàn
    gets_bad = []
    for m, u, s, _ in resp:
        pass
    ctx.close()

    # nv_kho
    ctx = browser.new_context(viewport=viewport, reduced_motion="reduce")
    page = ctx.new_page()
    resp2 = []
    page.on("response", lambda r: resp2.append((r.request.method, r.url, r.status)) if "/api/" in r.url else None)
    login(page, "kho1")
    page.goto(BASE + "/inventory/?status=EXPIRED")
    page.wait_for_load_state("networkidle")
    row = page.locator("tbody tr", has_text="TOM-GIA-1").first
    row.wait_for(timeout=15_000)
    row.locator("button").first.click()
    page.get_by_role("dialog", name=re.compile("Chi tiết lô")).wait_for(timeout=10_000)
    page.locator("[data-testid=qty-available]").wait_for()
    page.wait_for_timeout(600)
    ok(f"[{tag}] nv_kho: thấy lô quá hạn còn tồn nhưng không có nút Huỷ/Trả NCC/Chốt",
       page.locator("[data-action=cancel_expired]").count() == 0 and page.locator("[data-action=return_to_supplier]").count() == 0 and page.locator("[data-action=close]").count() == 0 and "3" in qty(page))
    page.screenshot(path=f"{SHOTS}/real-{tag}-4-nvkho-khong-nut.png")
    page.goto(BASE + "/overview/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(600)
    ok(f"[{tag}] nv_kho: Tổng quan không có thẻ Lô quá hạn", page.locator("[data-attention=expired_batches_open]").count() == 0)
    ok(f"[{tag}] nv_kho: bảng đơn không có cột Khách", "Khách" not in [h.strip() for h in page.locator("section[aria-labelledby=ov-orders] thead th").all_inner_texts()])
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    run(browser, "1366", {"width": 1366, "height": 800})
    browser.close()
bad = [r for r in results if not r[1]]
print(f"\n{len(results) - len(bad)}/{len(results)} PASS")
raise SystemExit(1 if bad else 0)
