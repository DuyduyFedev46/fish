# P8 Lô 5 (SR-15/SR-17) trên BACKEND THẬT: lô Quá hạn còn tồn -> Trả nhà cung cấp -> Trả hết -> Chốt lô; warehouse_staff không có nút.
# Dùng dữ liệu giả cố định của `manage.py seed_qa` (lô QA-LO-03 Quá hạn còn 6,5 kg), người dùng qa_owner / qa_warehouse (mật khẩu QA_PASSWORD).
#   Chuẩn bị và biến môi trường: xem e2e_seed_qa.py (BASE = ERP build thật, API, SEED_QA_IDS, QA_PASSWORD).
# Viết lại 08/10 (lô dọn e2e) theo màn hiện tại: Kho & lô là bảng + trang chi tiết lô (Lô 7), thao tác ở menu "Thao tác khác", không còn hộp
# "Chi tiết lô" và `data-action`. Ghi vào DB: seed lại trước mỗi lần chạy. Không rò tiền nhà cung cấp hoàn ở DOM, URL, storage, console.
import os
import re

from playwright.sync_api import expect, sync_playwright

from e2e_seed_qa import BASE, ids, password
from e2e_support import finish

SHOTS = os.environ.get("SHOTS", "/tmp")
SENTINEL = "999888"  # tiền nhà cung cấp hoàn giả: chỉ được gửi lên, không hiện lại
LOT = "QA-LO-03"
results = []
expect.set_options(timeout=15_000)


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra, flush=True)


def login(page, user):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(password())
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")


def open_lot(page):
    page.goto(f"{BASE}/inventory/detail/?id={ids()['batches'][LOT]['id']}")
    page.wait_for_selector("[data-testid=qty-available]")
    page.wait_for_load_state("networkidle")


def qty(page):
    return re.sub(r"\s+", " ", page.locator("[data-testid=qty-available]").inner_text()).strip()


def menu_items(page):
    page.get_by_role("button", name="Thao tác khác").click()
    items = [re.sub(r"\s+", " ", x).strip() for x in page.get_by_role("menuitem").all_inner_texts()]
    return items


def pick(page, label):
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^" + re.escape(label))).click()


def run(browser, tag, viewport):
    ctx = browser.new_context(viewport=viewport, reduced_motion="reduce")
    page = ctx.new_page()
    logs, resp, urls = [], [], []
    page.on("console", lambda m: logs.append(m.text))
    page.on("framenavigated", lambda f: urls.append(f.url))
    page.on("response", lambda r: resp.append((r.request.method, r.url, r.status, r.request.post_data or "")) if "/api/" in r.url else None)
    login(page, "qa_owner")
    open_lot(page)
    ok(f"[{tag}] Chủ: tồn thật 6,5 kg", qty(page).startswith("6,5"), qty(page))
    items = menu_items(page)
    close = [i for i in items if i.startswith("Chốt lô")]
    ok(f"[{tag}] Chủ: Chốt lô mờ kèm lý do còn tồn", len(close) == 1 and " · " in close[0] and "6,5" in close[0], str(items))
    page.keyboard.press("Escape")
    page.screenshot(path=f"{SHOTS}/real-{tag}-1-chu-lo-qua-han.png")
    pick(page, "Trả nhà cung cấp")
    dlg = page.get_by_role("dialog", name="Trả nhà cung cấp")
    dlg.wait_for()
    dlg.get_by_label("Số kg đã trả").fill("2")
    dlg.get_by_label("Tiền nhà cung cấp hoàn").fill(SENTINEL)
    dlg.get_by_role("button", name="Ghi nhận đã trả").click()
    dlg.wait_for(state="detached")
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('4,5')")
    ok(f"[{tag}] Chủ: trả 2 kg -> tồn 4,5 kg (lấy lại từ máy chủ)", qty(page).startswith("4,5"), qty(page))
    posts = [r for r in resp if r[0] == "POST" and "return-to-supplier" in r[1]]
    ok(f"[{tag}] BE thật trả 200 cho return-to-supplier", posts and posts[-1][2] == 200, str([p[:3] for p in posts]))
    ok(f"[{tag}] tiền hoàn của nhà cung cấp có gửi lên (payload) nhưng không hiện lại ở DOM", SENTINEL in posts[-1][3] and SENTINEL not in page.locator("body").inner_text())
    page.screenshot(path=f"{SHOTS}/real-{tag}-2-chu-sau-tra-2kg.png")
    pick(page, "Trả nhà cung cấp")
    dlg = page.get_by_role("dialog", name="Trả nhà cung cấp")
    dlg.wait_for()
    dlg.get_by_label("Số kg đã trả").fill("4,5")  # trả hết phần còn lại
    n0 = len([r for r in resp if r[0] == "POST" and "return-to-supplier" in r[1]])
    dlg.get_by_role("button", name="Ghi nhận đã trả").dblclick()
    dlg.wait_for(state="detached")
    page.wait_for_function("() => document.querySelector('[data-testid=qty-available]').innerText.startsWith('0')")
    n1 = len([r for r in resp if r[0] == "POST" and "return-to-supplier" in r[1]])
    ok(f"[{tag}] Chủ: trả hết + bấm đúp -> đúng 1 POST thêm ({n1 - n0}), tồn 0", n1 - n0 == 1 and qty(page).startswith("0"))
    items = menu_items(page)
    ok(f"[{tag}] Chủ: hết tồn -> không còn mục Trả / Huỷ phần tồn mở được", not [i for i in items if re.match(r"Trả|Huỷ", i) and " · " not in i], str(items))
    close_open = [i for i in items if i == "Chốt lô"]
    if close_open:
        pick(page, "Chốt lô")
        cd = page.get_by_role("dialog", name="Chốt lô")
        cd.wait_for()
        cd.get_by_role("button", name="Chốt lô").click()
        cd.wait_for(state="detached")
        page.wait_for_function("() => document.querySelector('main').innerText.includes('Đã chốt')")
        ok(f"[{tag}] Chủ: chốt lô thật thành công (200)", [r for r in resp if "/close/" in r[1]][-1][2] == 200)
    else:
        # Chưa chốt được vì thiếu điều kiện khác (vd chưa có hoá đơn mua): phải khoá kèm lý do tiếng Việt, không lỗi
        why = [i for i in items if i.startswith("Chốt lô")]
        ok(f"[{tag}] Chủ: hết tồn nhưng chưa chốt được thì 'Chốt lô' mờ kèm lý do", len(why) == 1 and " · " in why[0] and "BR-" not in why[0], str(items))
    page.keyboard.press("Escape")
    page.screenshot(path=f"{SHOTS}/real-{tag}-3-chu-sau-tra-het.png")
    body = page.locator("body").inner_text() + page.content()
    store = page.evaluate("() => JSON.stringify(Object.assign({}, window.localStorage)) + JSON.stringify(Object.assign({}, window.sessionStorage))")
    ok(f"[{tag}] không lộ tiền hoàn của nhà cung cấp ở DOM/URL/storage/console",
       SENTINEL not in body and SENTINEL not in store and not any(SENTINEL in u for u in urls) and not any(SENTINEL in l for l in logs))
    ctx.close()

    # warehouse_staff
    ctx = browser.new_context(viewport=viewport, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "qa_warehouse")
    open_lot(page)
    items = menu_items(page)
    page.keyboard.press("Escape")
    ok(f"[{tag}] warehouse_staff: thấy lô, không có mục Huỷ / Trả nhà cung cấp / Chốt", not [i for i in items if re.match(r"Trả|Huỷ|Chốt", i)], str(items))
    page.screenshot(path=f"{SHOTS}/real-{tag}-4-nvkho-khong-nut.png")
    page.goto(BASE + "/overview/")
    page.wait_for_selector("[data-kpi]")
    page.wait_for_load_state("networkidle")
    ok(f"[{tag}] warehouse_staff: Tổng quan không có thẻ Lô quá hạn", page.locator("[data-attention=expired_batches_open]").count() == 0)
    heads = [h.strip() for h in page.locator(".lt-card:has(h2:text-is('Đơn hàng gần đây')) thead th").all_inner_texts()]
    ok(f"[{tag}] warehouse_staff: bảng đơn không có cột Khách", heads and "Khách" not in heads, str(heads))
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    run(browser, "1366", {"width": 1366, "height": 800})
    browser.close()
finish(results)
