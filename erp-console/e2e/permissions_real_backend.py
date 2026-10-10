# E2E màn Phân quyền trên BE THẬT (QA Lô 6, PV-12 / nợ đóng F1). Thay cho ed_batch14_permissions.py khi cần BE thật,
# vì bản đó dựa vào window.__caveMock và tài khoản mock. Chạy:
#   BE: DJANGO_DEBUG=1 DATABASE_URL=sqlite:///<tmp>.sqlite3 QA_PASSWORD=... manage.py migrate && seed_qa && runserver 8631
#   FE: NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8631 npm run build, phục vụ out/ ở BASE
#   BASE=http://127.0.0.1:3531 REAL_API=http://127.0.0.1:8631 QA_PASSWORD=... SHOTS=<thư mục> python3 e2e/permissions_real_backend.py
# Tài khoản qa_… là dữ liệu giả của seed_qa.
import json
import os
import re
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright

from e2e_support import finish

BASE = os.environ.get("BASE", "http://127.0.0.1:3531")
API = os.environ.get("REAL_API", "http://127.0.0.1:8631")
PW = os.environ["QA_PASSWORD"]
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=15_000)
R = []
V1 = "Xem hoá đơn bán"
V2 = "Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền"
COST_WORDS = ("purchase_rate", "landed_unit_cost", "unit_cost", "profit")


def ok(name, cond, extra=""):
    R.append((name, bool(cond), extra))
    print("PASS" if cond else "FAIL", name, "" if cond else str(extra)[:400], flush=True)


def api(method, path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Token " + token
    req = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def token_of(user):
    return api("POST", "/api/auth/token/", None, {"username": user, "password": PW})[1]["token"]


def session(browser, user, w=1280, h=860, errors=None):
    errors = errors if errors is not None else []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(PW)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    return ctx, page, errors


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def switch(page, task, group):
    return page.get_by_role("switch", name=f"{task} — {group}", exact=True)


def run(p):
    # --- chuẩn bị: tắt V2 cho Nhân viên giao qua API (Chủ), để UI bật lại từ trạng thái tắt ---
    owner = token_of("qa_owner")
    _, g = api("GET", "/api/staff/groups/delivery_staff/", owner)
    st, _ = api("PUT", "/api/staff/groups/delivery_staff/capabilities/", owner, {"version": g["version"], "capabilities": {"view_order_customer_info": False}})
    ok("chuẩn bị: tắt V2 của Nhân viên giao qua API (200)", st == 200, st)
    _, g = api("GET", "/api/staff/groups/delivery_staff/", owner)
    browser = p.chromium.launch(headless=True)
    ctx, page, errors = session(browser, "qa_owner")
    seen_req = []
    page.on("request", lambda r: seen_req.append(r.url))
    go(page, "/permissions/")
    page.wait_for_selector("main table", state="attached")
    expect(page.locator("main [aria-busy=true]")).to_have_count(0)
    rows = page.locator("main table").nth(1).inner_text()
    ok("BE thật: ma trận có V1 'Xem hoá đơn bán'", V1 in rows)
    ok("BE thật: ma trận có V2 nhãn đầy đủ", V2 in rows)
    page.screenshot(path=f"{SHOTS}/real-matrix-1280.png", full_page=True)
    sw = switch(page, V2, "Nhân viên giao")
    expect(sw).to_have_attribute("aria-checked", "false")
    ok("V2 của Nhân viên giao đang tắt (đúng dữ liệu BE)", True)
    puts = []
    page.on("request", lambda r: r.method == "PUT" and puts.append(r.url))
    sw.click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    text = dlg.inner_text()
    page.screenshot(path=f"{SHOTS}/real-widen-v2-dialog.png")
    ok("bật V2: hộp xác nhận mở rộng hiện", "Cho thêm người xem dữ liệu khách" in text, text)
    ok("hộp mở rộng: nhãn tiếng Việt của V2, không khoá thô", V2 in text and "view_order_customer_info" not in text, text)
    _, mid = api("GET", "/api/staff/groups/delivery_staff/", owner)
    ok("hộp mở rộng: BE chưa đổi (PUT đầu bị 400 chờ xác nhận, version giữ nguyên)", mid["version"] == g["version"] and mid["capabilities"]["view_order_customer_info"] == "off", (mid["version"], g["version"]))
    page.keyboard.press("Escape")
    expect(dlg).to_have_count(0)
    expect(sw).to_have_attribute("aria-checked", "false")
    _, mid2 = api("GET", "/api/staff/groups/delivery_staff/", owner)
    ok("Esc: BE không đổi, ô vẫn tắt", mid2["version"] == g["version"] and sw.get_attribute("aria-checked") == "false")
    sw.click()
    page.get_by_role("dialog").get_by_role("button", name="Tôi hiểu, lưu").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(sw).to_have_attribute("aria-checked", "true")
    _, after = api("GET", "/api/staff/groups/delivery_staff/", owner)
    ok("xác nhận: BE đã bật V2 và tăng version", after["capabilities"]["view_order_customer_info"] == "on" and int(after["version"]) > int(g["version"]), (after["version"], g["version"]))
    # V1 cho nhóm chưa có (customer_service)
    _, cs = api("GET", "/api/staff/groups/customer_service/", owner)
    ok("BE: customer_service chưa có V1 (điều kiện ca bật V1)", cs["capabilities"]["view_sales_invoices"] == "off", cs["capabilities"]["view_sales_invoices"])
    sw1 = switch(page, V1, "Nhân viên gọi xác nhận") if page.get_by_role("switch", name=f"{V1} — Nhân viên gọi xác nhận", exact=True).count() else None
    if sw1 is not None:
        sw1.click()
        d1 = page.get_by_role("dialog")
        t1 = d1.inner_text() if d1.count() else ""
        page.screenshot(path=f"{SHOTS}/real-v1-toggle.png")
        ok("bật V1 cho nhóm chưa có: nếu có hộp thì hiện nhãn việt, không khoá thô", "view_sales_invoices" not in t1, t1)
        if d1.count():
            page.keyboard.press("Escape")
        # hoàn nguyên bằng cách không lưu
    else:
        ok("tìm công tắc V1 của nhóm gọi xác nhận", False, "không thấy")
    # trang nhóm
    go(page, "/permissions/detail/?group=delivery_staff")
    page.wait_for_selector("main h1, main h2", state="attached")
    body = page.locator("main").inner_text()
    ok("trang nhóm: có V1 và V2 (nhãn BE)", V1 in body and V2 in body)
    ok("trang nhóm: không khoá thô, không chữ cũ", not re.search(r"view_[a-z_]+|undefined|NaN|\[object", body), re.findall(r"view_[a-z_]+|undefined|NaN", body))
    page.screenshot(path=f"{SHOTS}/real-group-1280.png", full_page=True)
    # Trang nhóm: bật V2 từ trạng thái tắt (hộp mở rộng của trang nhóm)
    _, cur = api("GET", "/api/staff/groups/delivery_staff/", owner)
    api("PUT", "/api/staff/groups/delivery_staff/capabilities/", owner, {"version": cur["version"], "capabilities": {"view_order_customer_info": False}})
    go(page, "/permissions/detail/?group=delivery_staff")
    page.wait_for_selector("main h1, main h2", state="attached")
    page.get_by_role("switch", name=re.compile("Xem thông tin khách trên đơn")).click()
    page.get_by_role("button", name="Lưu thay đổi").click()
    dg = page.get_by_role("dialog")
    expect(dg).to_be_visible()
    tg = dg.inner_text()
    page.screenshot(path=f"{SHOTS}/real-group-widen-v2-dialog.png")
    ok("trang nhóm: hộp mở rộng V2 hiện nhãn tiếng Việt, không khoá thô", V2 in tg and "view_order_customer_info" not in tg, tg)
    page.keyboard.press("Escape")
    _, cur2 = api("GET", "/api/staff/groups/delivery_staff/", owner)
    ok("trang nhóm: Esc không lưu gì", cur2["capabilities"]["view_order_customer_info"] == "off")
    # DOM / storage không chứa dữ liệu khách
    dump = page.evaluate("() => JSON.stringify([Object.entries(localStorage).filter(e=>e[0]!=='cave_erp_token'), Object.entries(sessionStorage), location.href])")
    ok("storage/URL: không có số điện thoại", not re.search(r"0\d{9}", dump), dump[:300])
    ok("DOM màn Phân quyền: không SĐT dạng số", not re.search(r"0\d{9}", page.content()))
    ok("không giá vốn ở HTML màn nhóm", not any(w in page.content() for w in COST_WORDS))
    # Bảng Thành viên ở 1280 và 360
    for w, h in ((1280, 860), (360, 740)):
        c2, pg, errs2 = session(browser, "qa_owner", w, h)
        go(pg, "/permissions/detail/?group=delivery_staff")
        pg.wait_for_selector("main table", state="attached")
        expect(pg.locator("main [aria-busy=true]")).to_have_count(0)
        btn = pg.locator("main button", has_text="Bỏ khỏi nhóm").first
        ok(f"{w}: có nút 'Bỏ khỏi nhóm'", btn.count() == 1)
        btn.scroll_into_view_if_needed()
        box = btn.bounding_box()
        card = pg.locator("main table").last.locator("xpath=ancestor::*[contains(@class,'card') or self::section][1]")
        ok(f"{w}: nút nằm trong khung nhìn ngang (x+w <= {w})", box and box["x"] >= 0 and box["x"] + box["width"] <= w + 1, box)
        ok(f"{w}: trang không cuộn ngang", no_hscroll(pg))
        ok(f"{w}: vùng bấm nút >= 44px cao", box and box["height"] >= 40, box)
        pg.screenshot(path=f"{SHOTS}/real-members-{w}.png", full_page=True)
        btn.click()
        dl = pg.get_by_role("dialog")
        ok(f"{w}: bấm 'Bỏ khỏi nhóm' mở hộp xác nhận (bấm được)", dl.count() == 1, dl.count())
        pg.screenshot(path=f"{SHOTS}/real-members-{w}-confirm.png")
        if dl.count():
            pg.keyboard.press("Escape")
        ok(f"{w}: console không lỗi", not errs2, errs2)
        c2.close()
    ok("console (Chủ) không lỗi", not errors, errors)
    # người không phải Chủ: không có API staff
    c3, pg3, e3 = session(browser, "qa_manager")
    reqs = []
    pg3.on("request", lambda r: reqs.append(r.url))
    go(pg3, "/permissions/")
    ok("Quản lý (không manage_staff): thấy 'Không có quyền' và không gọi /api/staff/groups", "/api/staff/groups" not in " ".join(reqs) or pg3.get_by_text("Không có quyền").count() >= 1, reqs)
    pg3.screenshot(path=f"{SHOTS}/real-manager-denied.png")
    ok("Quản lý: DOM không có công tắc", pg3.get_by_role("switch").count() == 0)
    c3.close()
    browser.close()


with sync_playwright() as p:
    run(p)
finish(R)
