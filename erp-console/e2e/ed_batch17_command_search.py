# E2E ED-07 (⌘K nhảy theo mã chứng từ, Lô 17b H1). Chạy được trên bản MOCK và trên BE THẬT:
#   MOCK:  NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#          BASE=http://127.0.0.1:3101 SHOTS=<thư mục> python3 e2e/ed_batch17_command_search.py
#   THẬT:  BE chạy ở REAL_API (đã seed_demo, người dùng mật khẩu Songbien2026), console build NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=<REAL_API>
#          BASE=http://127.0.0.1:3521 REAL_API=http://127.0.0.1:8621 SHOTS=<thư mục> python3 e2e/ed_batch17_command_search.py
# Kiểm: AC1 gõ mã đơn, mã phiếu giao, mã lô, PR-n, KK-n, RT-n thì Enter mở đúng chi tiết · AC2 mã đúng mẫu mà không có → "Không tìm thấy
# chứng từ khớp với <mã>" · AC3 giao1 gõ mã phiếu của người khác → không tìm thấy (như mã không tồn tại) · gõ tên khách hay SĐT
# → 0 request, không có dòng "Mở chứng từ" · URL/storage không chứa từ khoá · 360px không cuộn ngang.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
REAL = os.environ.get("REAL_API", "")
PASSWORD = "Songbien2026" if REAL else "demo1234"
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=12_000)
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print("PASS" if cond else "FAIL", name, "" if cond else str(extra)[:300], flush=True)


def new_page(browser, user, w=1280, h=860):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(PASSWORD)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_load_state("networkidle")
    return ctx, page, errors


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def first_cell_codes(page, path, pattern):
    """Mã khớp `pattern` đọc từ chữ hiện trên một màn (bảng hoặc thẻ), để không gõ cứng mã trong kịch bản."""
    go(page, path)
    page.wait_for_function("() => document.querySelector('main') && document.querySelector('main').innerText.length > 40")
    page.wait_for_timeout(800)
    found = []
    for m in re.findall(pattern, page.locator("main").inner_text().upper()):
        if m not in found:
            found.append(m)
    return found


def open_cmd(page):
    page.keyboard.press("Control+k")
    box = page.get_by_role("combobox", name="Tìm màn hình")
    expect(box).to_be_visible()
    return box


def type_and_enter(page, text):
    box = open_cmd(page)
    box.fill(text)
    return box


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx, page, errors = new_page(b, "loc")
        # Request tới các endpoint tra chứng từ (đơn, phiếu giao, lô). Màn Tổng quan không gọi các endpoint này, nên ô ⌘K gõ tên/SĐT phải giữ số này ở 0.
        api_calls = []
        page.on("request", lambda r: api_calls.append(r.url) if re.search(r"/api/(sales/orders|delivery/notes|inventory/batches|customer-directory)", r.url) else None)

        orders = first_cell_codes(page, "/orders/", r"SO\d{6}-[A-Z0-9]{4,8}")
        ok("Có mã đơn mẫu để thử", bool(orders), orders)
        order_code = orders[0]

        # AC1 đơn
        go(page, "/overview/")
        box = type_and_enter(page, order_code.lower())
        row = page.locator("[data-cmd-code]")
        expect(row).to_be_visible()
        ok("AC1: gõ mã đơn → có dòng 'Mở chứng từ' ở đầu danh sách", order_code in row.inner_text() and "Mở chứng từ" in row.inner_text(), row.inner_text())
        box.press("Enter")
        page.wait_for_url(re.compile(r"/orders/detail/\?id=\d+"))
        page.wait_for_load_state("networkidle")
        try:
            expect(page.locator("main")).to_contain_text(order_code)
            on_page = True
        except AssertionError:
            on_page = False
        ok("AC1: Enter mở đúng chi tiết đơn (mã nằm trên trang)", on_page, page.url)
        ok("AC1: URL chỉ mang id, không mang từ khoá", order_code not in page.url and "q=" not in page.url, page.url)
        page.screenshot(path=f"{SHOTS}/ed17-cmd-order-1280.png")

        # AC2 mã đúng mẫu nhưng không có
        go(page, "/overview/")
        box = type_and_enter(page, "SO261007-ZZZZZZ")
        box.press("Enter")
        res = page.locator("[data-cmd-code-result]")
        expect(res).to_be_visible()
        ok("AC2: mã đơn không có → 'Không tìm thấy chứng từ khớp với SO261007-ZZZZZZ'", res.inner_text().strip() == "Không tìm thấy chứng từ khớp với SO261007-ZZZZZZ", res.inner_text())
        ok("AC2: vẫn ở trang cũ, hộp chưa đóng", "/overview/" in page.url and page.get_by_role("dialog").count() == 1, page.url)
        page.screenshot(path=f"{SHOTS}/ed17-cmd-notfound-1280.png")
        box.fill("SO261007-ZZZZZY")
        ok("AC2: gõ tiếp thì câu cũ biến mất", page.locator("[data-cmd-code-result]").count() == 0)
        page.keyboard.press("Escape")

        # phiếu giao, lô
        notes = first_cell_codes(page, "/deliveries/", r"GH-[A-Z0-9-]{3,}")
        if notes:
            go(page, "/overview/")
            box = type_and_enter(page, notes[0])
            box.press("Enter")
            page.wait_for_url(re.compile(r"/deliveries/detail/\?id=\d+"))
            ok("AC1: mã phiếu giao → mở chi tiết phiếu giao", True, page.url)
        else:
            ok("Có mã phiếu giao mẫu để thử", False, "danh sách Giao hàng rỗng")
        batches = first_cell_codes(page, "/inventory/", r"[A-Z0-9]+(?:-[A-Z0-9]+)+")
        batch_code = next((c for c in batches if re.search(r"\d", c) and not c.startswith(("SO", "GH-", "PR-", "KK-", "RT-"))), None)
        if batch_code:
            go(page, "/overview/")
            box = type_and_enter(page, batch_code)
            box.press("Enter")
            page.wait_for_url(re.compile(r"/inventory/detail/\?id=\d+"))
            ok("AC1: mã lô → mở chi tiết lô", True, page.url)
        else:
            ok("Có mã lô mẫu để thử", False, batches)

        # mã theo id: mở thẳng, không cần API tra
        for text, want in (("PR-1", "/purchasing/detail/?id=1"), ("kk-1", "/stocktake/detail/?id=1"), ("RT-1", "/returns/detail/?id=1")):
            go(page, "/overview/")
            box = type_and_enter(page, text)
            box.press("Enter")
            page.wait_for_url(re.compile(re.escape(want) + r"$"))
            ok(f"AC1: {text} mở thẳng {want}", True, page.url)

        # tên khách / SĐT: không có dòng mã, không request tra chứng từ
        go(page, "/overview/")
        page.wait_for_timeout(500)
        before = len(api_calls)
        for text in ("Chị Hoa", "0901234567", "nguyen van an", "hoa"):
            box = type_and_enter(page, text)
            page.wait_for_timeout(400)
            ok(f"Gõ '{text}': không có dòng 'Mở chứng từ'", page.locator("[data-cmd-code]").count() == 0)
            box.press("Enter")  # Enter chỉ nhảy menu (nếu có mục khớp), không tra mã
            page.wait_for_timeout(400)
            if "/overview/" not in page.url:
                go(page, "/overview/")
                page.wait_for_timeout(500)
                before = len(api_calls)
            elif page.get_by_role("dialog").count():
                page.keyboard.press("Escape")
        ok("Gõ tên khách / SĐT: 0 request tra chứng từ từ ô ⌘K", len(api_calls) == before, api_calls[before:])
        ok("URL và storage không chứa từ khoá đã gõ", "0901234567" not in page.url and "0901234567" not in page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)].map((l) => l.filter(([k]) => !k.startsWith('cave_erp_mock_'))))"))
        ok("loc: không lỗi console", not errors, errors[:3])
        ctx.close()

        # AC3: giao1 tra mã phiếu của người khác
        ctx2, pg2, errors2 = new_page(b, "giao1")
        mine = first_cell_codes(pg2, "/my-deliveries/", r"GH-[A-Z0-9-]{3,}") if True else []
        other = [c for c in notes if c not in mine]
        if other:
            go(pg2, "/my-deliveries/")
            box = type_and_enter(pg2, other[0])
            box.press("Enter")
            res = pg2.locator("[data-cmd-code-result]")
            expect(res).to_be_visible()
            ok("AC3: giao1 gõ mã phiếu của người khác → 'Không tìm thấy chứng từ khớp với …', không lộ phiếu", res.inner_text().strip() == f"Không tìm thấy chứng từ khớp với {other[0]}" and "/deliveries/detail" not in pg2.url, res.inner_text())
            pg2.screenshot(path=f"{SHOTS}/ed17-cmd-giao1-notfound-1280.png")
        else:
            ok("AC3: có phiếu của người khác để thử", False, notes)
        ctx2.close()

        # 360px
        ctx3, pg3, errors3 = new_page(b, "loc", w=360, h=740)
        go(pg3, "/overview/")
        box = type_and_enter(pg3, order_code)
        expect(pg3.locator("[data-cmd-code]")).to_be_visible()
        ok("360px: bảng ⌘K không cuộn ngang", pg3.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
        pg3.screenshot(path=f"{SHOTS}/ed17-cmd-order-360.png")
        ctx3.close()
        b.close()

    bad = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(bad)}/{len(results)} PASS")
    sys.exit(1 if bad else 0)


main()
