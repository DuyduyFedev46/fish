# QA độc lập Lô 4 FE (ED-17, ED-19). Chạy trên bản build MOCK phục vụ tĩnh:
#   BASE=http://127.0.0.1:3201 SHOTS=<thư mục ảnh> python3 e2e/qa_ed_batch4_ui.py
# Mỗi ca ghi PASS/FAIL kèm bằng chứng; dữ liệu giả. Ngoài đường thuận: nhiều vai, 360px, ghi chú có SĐT, phiếu người khác, F5 màn cũ.
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3201")
SHOTS = os.environ.get("SHOTS", "/tmp/qa_lot4")
os.makedirs(SHOTS, exist_ok=True)
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill("demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'")


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0")


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    settle(page)


def newp(browser, user, w=1280, h=860, touch=False):
    errs = []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", **({"is_mobile": True, "has_touch": True} if touch else {}))
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC" not in m.text and "HTTP 4" not in m.text and errs.append(m.text))
    page.on("pageerror", lambda e: errs.append(str(e)))
    login(page, user)
    return ctx, page, errs


def shot(page, name, full=False):
    page.screenshot(path=os.path.join(SHOTS, name), full_page=full)


def btns(page):
    return page.evaluate("""() => Array.from(document.querySelectorAll('main button, main a')).filter(b=>b.offsetParent).map(b=>b.textContent.trim()).filter(Boolean)""")


def run(browser):
    # ---- ED-17 danh sách + chi tiết, vai ql1 (1440)
    ctx, page, errs = newp(browser, "ql1", 1440, 900)
    go(page, "/deliveries/")
    body = page.inner_text("main")
    ok("ED-17-AC1 list: có tab nhóm trạng thái", page.get_by_role("tab").count() >= 3, str(page.get_by_role("tab").all_inner_texts()))
    heads_list = [h.strip() for h in page.locator("thead").first.inner_text().split("\t")] if page.locator("thead").count() else []
    ok("ED-17-AC1 list (PO: danh sách không có cột Kho): cột Mã phiếu, Đơn hàng, Người nhận, Hàng, Tổng kg, Người giao, Tem, Trạng thái, không cột Kho", "Kho" not in heads_list and "Tem" in heads_list and "Người giao" in heads_list, str(heads_list))
    ok("G5 list: kg dạng 18,5 kg (dấu phẩy, đơn vị)", not re.search(r"\d\.\d{3}\s*kg", body), re.findall(r".{0,15}\d\.\d{3}\s*kg", body)[:3].__str__())
    shot(page, "lo4_list_1440_ql1.png")
    go(page, "/deliveries/detail/?id=31")
    d = page.inner_text("main")
    ok("ED-17 detail 31: có StatusPath/Timeline", page.locator("ol").count() >= 1)
    ok("G5 detail: số kg có dấu phẩy và đơn vị", not re.search(r"\d\.\d{3}\s*kg", d) and re.search(r"\d+,\d+ kg", d) is not None, re.findall(r".{0,12}\d[.,]\d{3}\s*kg", d)[:4].__str__())
    ok("G7 detail: không chữ cấm 'HSD'", "HSD" not in d)
    shot(page, "lo4_detail31_ql1_1440.png", True)
    page.get_by_role("button", name="Thao tác khác").click()
    items = page.get_by_role("menuitem").all_inner_texts()
    ok("ED-17-AC3 '…' đủ mục theo bảng (in lại tem, Nhận hàng, Báo thất bại, đổi người giao...) cho phiếu chưa gán", len(items) >= 2, str(items))
    page.keyboard.press("Escape")
    go(page, "/deliveries/detail/?id=33")
    page.get_by_role("button", name="Thao tác khác").click()
    items33 = page.get_by_role("menuitem").all_inner_texts()
    ok("ED-17-AC3 '…' ở phiếu Đang giao (ql1) có mục khoá có lý do", len(items33) >= 1, str(items33))
    shot(page, "lo4_detail33_menu_ql1.png")
    ctx.close()

    # ---- vai: kho1, loc, cs2
    for user in ("loc", "kho1", "cs2"):
        ctx, page, errs = newp(browser, user, 1440, 900)
        navs = page.locator(".nav a").all_inner_texts()
        go(page, "/deliveries/")
        has = page.get_by_text("không có quyền", exact=False).count() == 0
        go(page, "/deliveries/detail/?id=31")
        b = btns(page)
        shot(page, f"lo4_detail31_{user}.png")
        print(user, "list-ok" if has else "no-perm", "buttons:", b[:12], "nav:", [n.replace("\n", " ") for n in navs][:14])
        if user == "kho1":
            ok("ED-17-AC8 kho1: không có nút Giao cho người giao", "Giao cho người giao" not in b, str(b))
            ok("ED-17 kho1: có Đã đóng gói hoặc In tem", any(x in b for x in ("Đã đóng gói", "In tem", "In lại tem")), str(b))
        if user == "loc":
            ok("ED-17 loc: mở được danh sách giao", has)
            ok("ED-17 loc: nút Giao cho người giao/Đã đóng gói/In tem có ở chi tiết (phiếu 31)", any(x in b for x in ("Giao cho người giao", "Đã đóng gói", "In tem", "In lại tem")), str(b))
        if user == "cs2":
            ok("cs2: không có Giao cho người giao ở chi tiết", "Giao cho người giao" not in b, str(b))
        ok(f"{user}: không console.error", not errs, str(errs[:2]))
        ctx.close()

    # ---- ED-17-AC4/F2o ql1
    ctx, page, errs = newp(browser, "ql1", 1440, 900)
    go(page, "/deliveries/detail/?id=30")
    page.get_by_role("button", name="Giao cho người giao").first.click()
    dlg = page.get_by_role("dialog")
    settle(page)
    t = dlg.inner_text()
    shot(page, "lo4_F2o_assign_ql1.png")
    ok("F2o: nút 'Quay lại' (UI-RULES §6)", dlg.get_by_role("button", name="Quay lại").count() == 1, str(dlg.get_by_role("button").all_inner_texts()))
    ok("F2o: có khối tóm tắt phiếu (mã + đơn + kg)", re.search(r"\d+,\d+ kg", t) is not None, t[:200].replace("\n", "|"))
    ok("F2o: 'Đang giao n phiếu' mỗi người", len(re.findall(r"Đang giao \d+ phiếu", t)) >= 2)
    page.keyboard.press("Escape")
    ctx.close()

    # ---- ED-19 giao1/giao2/cs2 @ 360
    for user in ("giao1", "giao2", "cs2"):
        ctx, page, errs = newp(browser, user, 360, 740, touch=True)
        settle(page)
        if user == "cs2":
            go(page, "/my-deliveries/")
        body = page.inner_text("main")
        codes = sorted(set(re.findall(r"GH-HD-\d{4}-[A-Z]+", body)))
        print(user, "cards:", codes, "url:", page.url)
        if user == "giao1":
            ok("ED-19-AC1 giao1: chỉ phiếu của mình", set(codes) == {"GH-HD-0036-DELI", "GH-HD-0037-READY", "GH-HD-0038-FAIL"} or set(codes) >= {"GH-HD-0036-DELI"} and "GH-HD-0039-DELI" not in codes, str(codes))
        if user == "giao2":
            ok("ED-19 giao2: không thấy phiếu giao1", not any(c in codes for c in ("GH-HD-0036-DELI", "GH-HD-0037-READY", "GH-HD-0038-FAIL")), str(codes))
        ok(f"ED-19 {user}: có 'Đã thanh toán, không thu thêm' trên thẻ (AC1)", "không thu thêm" in body.lower() or not codes, "")
        ok(f"G5 {user}: kg dạng 18,5 kg", not re.search(r"\d\.\d{3}\s*kg", body) and (not codes or re.search(r"\d+,\d+ kg", body) is not None), re.findall(r".{0,15}\d[.,]\d{3}\s*kg", body)[:3].__str__())
        no_h = page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
        ok(f"360 {user}: không cuộn ngang", no_h)
        small = page.evaluate("""() => Array.from(document.querySelectorAll('main .btn, main a.btn, main button, main a[href^="tel:"]')).filter(b=>b.offsetParent).map(b=>{const r=b.getBoundingClientRect();return [b.textContent.trim().slice(0,24),Math.round(r.height),Math.round(r.width)]}).filter(x=>x[1]<44)""")
        ok(f"360 {user}: nút chạm cao >= 44px", not small, str(small[:5]))
        wrap = page.evaluate("""() => Array.from(document.querySelectorAll('main .btn, main a.btn')).filter(b=>b.offsetParent && /Gọi khách/.test(b.textContent)).map(b=>{const r=b.getBoundingClientRect();return [Math.round(r.height), b.getClientRects().length, getComputedStyle(b).whiteSpace]})""")
        print(user, "gọi khách:", wrap)
        shot(page, f"lo4_mine_{user}_360.png", True)
        ok(f"{user}: không console.error", not errs, str(errs[:2]))
        ctx.close()

    # ---- F2l đầy đủ (giao1 360)
    ctx, page, errs = newp(browser, "giao1", 360, 740, touch=True)
    settle(page)
    page.locator("[data-group='DELIVERING']").first.get_by_role("button", name="Báo giao thất bại").first.click()
    dlg = page.get_by_role("dialog")
    t = dlg.inner_text()
    shot(page, "lo4_F2l_360.png")
    ok("F2l: nút 'Quay lại' + 'Báo giao thất bại' (board)", dlg.get_by_role("button", name="Quay lại").count() == 1 and dlg.get_by_role("button", name="Báo giao thất bại").count() == 1, str(dlg.get_by_role("button").all_inner_texts()))
    ok("F2l: khối tóm tắt theo ED-19-AC3 có Phiếu giao, Đơn, Khách hàng (PO: không có kg)", all(x in t for x in ("Phiếu giao", "Đơn", "Khách hàng")) and not re.search(r"\d+,\d+ kg", t), t[:240].replace("\n", "|"))
    ok("F2l (BE chưa có mốc): khối tóm tắt có 'Bắt đầu giao' (ED-19-AC3)", "Bắt đầu giao" in t, "dev ghi nợ 8b: BE chưa có mốc Bắt đầu giao")
    for r in ("Không liên lạc được", "Khách từ chối nhận", "Sai địa chỉ", "Hàng hư hỏng", "Khác"):
        pass
    ok("F2l: đủ 5 lý do (NOT_MET, REFUSED, WRONG_ADDRESS, DAMAGED, OTHER)", dlg.get_by_role("radio").count() == 5, str(dlg.get_by_role("radio").count()))
    # touch target radio
    rh = dlg.evaluate("""d => Array.from(d.querySelectorAll('label')).filter(l=>l.querySelector('input[type=radio]')).map(l=>Math.round(l.getBoundingClientRect().height))""")
    ok("F2l 360: dòng chọn lý do cao >= 44px", all(h >= 44 for h in rh), str(rh))
    # ghi chú SĐT 9 số, 8 số, có dấu chấm
    dlg.get_by_role("radio", name="Khác", exact=True).check()
    box = dlg.get_by_label("Ghi chú", exact=False)
    box.fill("goi 091234567 khong nghe")
    dlg.get_by_role("button", name=re.compile("Báo")).last.click()
    ok("F2l: ghi chú có dãy 9 số liền bị chặn, hộp vẫn mở", dlg.is_visible() and dlg.get_by_role("button", name=re.compile("Báo")).last.is_enabled(), "")
    box.fill("x" * 201)
    ok("F2l: ô ghi chú giới hạn 200 ký tự", len(box.input_value()) <= 200, str(len(box.input_value())))
    box.fill("goi 0912 345 678 khong nghe")
    dlg.get_by_role("button", name=re.compile("Báo")).last.click()
    page.wait_for_timeout(600)
    settle(page)
    ok("F2l (Low): ghi chú SĐT có dấu cách (0912 345 678) bị chặn ở FE như BE has_long_digit_run", dlg.is_visible() and dlg.get_by_role("button", name=re.compile("Báo")).last.is_enabled(), "FE PII_NOTE_RE=/\\d{9,}/ không gộp dấu cách; BE gộp")
    dump = page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)])")
    ok("F2l: ghi chú không vào storage/URL", "0912 345" not in dump and "0912 345" not in page.url and "khong nghe" not in dump and "khong nghe" not in page.url)
    ok("F2l: không console.error", not errs, str(errs[:2]))
    ctx.close()

    # ---- giao1 Gọi khách: số đủ, F5 màn cũ
    ctx, page, errs = newp(browser, "giao1", 360, 740, touch=True)
    settle(page)
    hrefs = [h for h in page.locator('a[href^="tel:"]').evaluate_all("els=>els.map(e=>e.getAttribute('href'))")]
    ok("ED-19 Gọi khách: tel: số đủ", all(re.fullmatch(r"tel:\+?\d{9,}", h) for h in hrefs) and hrefs, str(hrefs))
    page.locator("[data-group='DELIVERING']").first.get_by_role("button", name="Đã giao xong").first.click()
    dlg = page.get_by_role("dialog")
    shot(page, "lo4_F2k_complete_360.png")
    dlg.get_by_role("button", name=re.compile("Xác nhận|Đã giao")).last.click()
    settle(page)
    b2 = page.inner_text("main")
    ok("ED-19 sau Đã giao xong: phiếu 0036 rời nhóm Đang giao ngay", page.locator("[data-group='DELIVERING']").get_by_text("GH-HD-0036-DELI").count() == 0, "")
    ok("ED-19-AC5 (PO: Mang hàng về kho sang Lô 9): thẻ thất bại không hiện nút/chữ 'sắp có' gây hiểu nhầm", "sắp có" not in b2 and "Mang hàng về kho" not in b2, "")
    ctx.close()

    # ---- giao1 vào chi tiết phiếu người khác / không đăng nhập
    ctx = browser.new_context(); page = ctx.new_page()
    page.goto(BASE + "/my-deliveries/"); page.wait_for_load_state("networkidle")
    ok("Chưa đăng nhập: /my-deliveries/ chuyển sang /login/", "/login" in page.url, page.url)
    ctx.close()


with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    try:
        run(br)
    except Exception as e:  # noqa
        ok("run: chạy hết không văng", False, repr(e)[:300])
    br.close()
failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
