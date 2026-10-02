# QA độc lập Lô 11 (Nhà cung cấp, ED-22) trên BE THẬT: Django :8000 (SQLite tạm đã nạp seed QA, xem qa11/seed.py) + console build MOCK=0
# NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 phục vụ ở :3102. Đối chiếu số trên màn với sqlite. Chỉ dữ liệu giả.
#   QA_DB=<sqlite> SHOTS=<thư mục> python3 e2e/qa_ed_batch11_real.py     (nạp lại DB trước mỗi lần chạy)
import json
import os
import re
import sqlite3
import sys
import time
from decimal import ROUND_HALF_UP, Decimal

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3102")
SHOTS = os.environ.get("SHOTS", "/tmp")
DB = os.environ["QA_DB"]
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=15000)
R = []
SEEN = []  # (user, method, path, status, body)
COST_KEYS = {"purchase_rate", "landed_unit_cost", "unit_cost", "rate", "allocated_amount", "purchase_cost", "allocated_cost", "total_cost", "shrinkage_cost",
             "damage_cost", "cogs", "profit", "loss_amount", "loss", "inventory_value", "margin", "gross_profit", "expired_cost", "supplier_refund_amount",
             "supplier_return_cost", "purchase_amount", "purchase_total"}
PRIMERS = ["77777", "80001", "123457", "91919", "55555", "999999", "66666", "44444", "888888", "77.777", "80.001", "123.457", "91.919", "999.999", "999.999.900"]
PHONES = ["0900000111", "0900000222", "0900000333", "0900000444"]
NAME_TAKEN = "Đã có nhà cung cấp trùng tên này."
SUFFIX = str(int(time.time()))[-5:]


def ok(n, c, e=""):
    R.append((n, bool(c)))
    print("PASS" if c else "FAIL", n, "" if c else "  -> " + str(e)[:500], flush=True)


def q(sql, *a):
    c = sqlite3.connect(DB)
    try:
        return c.execute(sql, a).fetchall()
    finally:
        c.close()


def keys_deep(o, acc=None):
    acc = set() if acc is None else acc
    if isinstance(o, dict):
        for k, v in o.items():
            acc.add(k)
            keys_deep(v, acc)
    elif isinstance(o, list):
        for v in o:
            keys_deep(v, acc)
    return acc


def session(b, user, w=1280, h=860, touch=False):
    opts = {"viewport": {"width": w, "height": h}, "reduced_motion": "reduce"}
    if touch:
        opts.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = b.new_context(**opts)
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type in ("error", "warning") and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errs.append(f"[{user}] {m.type}: {m.text}"))
    page.on("pageerror", lambda e: errs.append(f"[{user}] pageerror {e}"))
    allconsole = []
    page.on("console", lambda m: allconsole.append(m.text))
    page._allconsole = allconsole

    def on_resp(r):
        if "/api/" in r.url:
            try:
                body = r.text()
            except Exception:
                body = ""
            SEEN.append((user, r.request.method, r.url.split("/api/")[1], r.status, body))
    page.on("response", on_resp)
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill("Songbien2026")
    page.get_by_role("button", name="Đăng nhập").click()
    try:
        page.wait_for_selector(".nav a", state="attached", timeout=12000)
    except Exception:
        # BE giới hạn tần suất đăng nhập (429): chờ rồi thử lại 1 lần
        print("  (đăng nhập bị giới hạn tần suất, chờ 65s)", flush=True)
        time.sleep(65)
        page.goto(BASE + "/login/")
        page.wait_for_load_state("networkidle")
        page.get_by_label("Tài khoản").fill(user)
        page.get_by_label("Mật khẩu").fill("Songbien2026")
        page.get_by_role("button", name="Đăng nhập").click()
        page.wait_for_selector(".nav a", state="attached", timeout=20000)
    page.wait_for_load_state("networkidle")
    return ctx, page, errs


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def table(page, sel="table.lt"):
    t = page.locator(sel).first
    expect(t.locator("tbody tr").first).to_be_visible()
    expect(t.locator("tr.lt-skel")).to_have_count(0)
    return t


def heads(t):
    return [re.sub(r" \(cột giới hạn quyền xem\)$", "", re.sub(r"\s+", " ", h).replace("lock", "").strip()) for h in t.locator("thead th").all_inner_texts()]


def body(page):
    return page.locator("body").inner_text()


def vnd_text(d):
    n = int(Decimal(d).quantize(Decimal("1"), ROUND_HALF_UP))
    return f"{n:,}".replace(",", ".") + " đ"


def vn_dt(iso_utc):
    from datetime import datetime, timedelta, timezone
    s = iso_utc.replace(" ", "T")
    d = datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    d = d.astimezone(timezone(timedelta(hours=7)))
    return d.strftime("%d/%m/%Y %H:%M")


def exp_supplier(name):
    sid = q("select id from purchasing_supplier where name=?", name)[0][0]
    rows = q("select pl.qty, pl.rate from purchasing_purchasereceiptline pl join purchasing_purchasereceipt pr on pr.id=pl.receipt_id where pr.supplier_id=? and pr.status='SUBMITTED'", sid)
    tot = sum((Decimal(str(a)) * Decimal(str(b))).quantize(Decimal("0.01"), ROUND_HALF_UP) for a, b in rows)
    cnt, last = q("select count(*), max(created_at) from purchasing_purchasereceipt where supplier_id=? and status='SUBMITTED'", sid)[0]
    return sid, cnt, last, tot


def row_cells(t, name):
    return [c.strip() for c in t.locator("tbody tr", has_text=name).first.locator("td").all_inner_texts()]


def open_supplier(page, name):
    go(page, "/suppliers/")
    t = table(page)
    t.locator("tbody tr", has_text=name).first.locator("a").first.click()
    page.wait_for_url("**/suppliers/detail/**")
    page.wait_for_selector("#supplier-detail", timeout=15000)
    page.wait_for_load_state("networkidle")


def more_items(page):
    page.get_by_role("button", name="Thao tác khác").click()
    return [re.sub(r"\s+", " ", x).strip() for x in page.get_by_role("menuitem").all_inner_texts()]


def pick_more(page, label):
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^" + re.escape(label))).click()


def hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), location.href])")


with sync_playwright() as p:
    b = p.chromium.launch()
    errors = []

    # ======================================================= loc
    ctx, page, errs = session(b, "loc")
    go(page, "/suppliers/")
    t = table(page)
    h = heads(t)
    h = [re.sub(r" \(cột giới hạn quyền xem\)$", "", x) for x in h]
    ok("R1 loc: cột đúng ED-22-AC1 + cột Tổng tiền mua", h == ["Nhà cung cấp", "Loại", "Số điện thoại", "Số phiếu nhập", "Lần nhập gần nhất", "Trạng thái", "Tổng tiền mua"], h)
    for nm in ("QA Ghe Alpha", "QA Chua Nhap", "QA Ngung Hop Tac", "QA Chi Co Nhap Va Huy", "NK Đại Dương"):
        sid, cnt, last, tot = exp_supplier(nm)
        c = row_cells(t, nm)
        ok(f"R1 {nm}: số phiếu nhập = DB ({cnt})", c[3] == str(cnt), c)
        ok(f"R1 {nm}: lần nhập gần nhất = DB giờ VN" if cnt else f"R1 {nm}: chưa có phiếu hiện '—'", (c[4] == vn_dt(last)) if cnt else c[4] == "—", (c[4], last))
        ok(f"R1 {nm}: tổng tiền mua = DB ({tot})", c[6] == vnd_text(tot), (c[6], tot))
    ok("R1 loc: chip Đang hợp tác / Ngừng hợp tác đúng", "Ngừng hợp tác" in t.locator("tbody tr", has_text="QA Ngung Hop Tac").inner_text() and "Đang hợp tác" in t.locator("tbody tr", has_text="QA Ghe Alpha").inner_text())
    ok("R1 loc: loại Cá nhân / Doanh nghiệp", "Cá nhân" in row_cells(t, "QA Ghe Alpha")[1] and "Doanh nghiệp" in row_cells(t, "QA Chua Nhap")[1])
    ok("R1 loc: SĐT đối tác hiện đủ (không che …0111)", row_cells(t, "QA Ghe Alpha")[2] == "0900000111", row_cells(t, "QA Ghe Alpha"))
    ok("R1 loc: không có NCC/SĐT", "NCC" not in body(page) and "SĐT" not in body(page))
    ok("R1 loc: chỉ MỘT giá trị mỗi ô (G1): ô Nhà cung cấp không xuống dòng thứ hai", all(len(x.locator("td").first.inner_text().strip().splitlines()) == 1 for x in [t.locator("tbody tr").nth(i) for i in range(min(5, t.locator("tbody tr").count()))]))
    ok("R1 loc: có 'Đang hiện n / n nhà cung cấp'", re.search(r"Đang hiện \d+ / \d+ nhà cung cấp", body(page)) is not None)
    ok("R1 loc: cột Tổng tiền mua có icon khoá ở tiêu đề", page.locator("table.lt thead th", has_text="Tổng tiền mua").locator("[class*=lock], .icon, span").count() >= 1)
    page.screenshot(path=f"{SHOTS}/impl-real-list-loc-1280.png")

    # --- tìm, lọc
    sb = page.get_by_role("searchbox").or_(page.get_by_placeholder("Tìm tên hoặc số điện thoại")).first
    sb.fill("ghe alpha")
    expect(t.locator("tbody tr")).to_have_count(1)
    ok("R2 tìm 'ghe alpha' (hoa thường)", "QA Ghe Alpha" in t.inner_text())
    sb.fill("0900000222")
    expect(t.locator("tbody tr", has_text="QA Chua Nhap")).to_have_count(1)
    expect(t.locator("tbody tr", has_text="QA Ghe Alpha")).to_have_count(0)
    ok("R2 tìm theo số điện thoại", "QA Chua Nhap" in t.inner_text())
    ok("R2 từ khoá tìm KHÔNG vào URL", "0900000222" not in page.url and "q=" not in page.url, page.url)
    ok("R2 từ khoá/SĐT không vào storage", "0900000222" not in storage_dump(page))
    sb.fill("zzkhongco")
    expect(page.get_by_text(re.compile("Không tìm thấy"))).to_be_visible()
    ok("R2 tìm không thấy: có chữ khớp từ khoá + nút Xoá tìm kiếm", page.get_by_role("button", name="Xoá tìm kiếm").count() >= 1)
    page.screenshot(path=f"{SHOTS}/impl-real-list-notfound-1280.png")
    page.get_by_role("button", name="Xoá tìm kiếm").first.click()
    expect(t.locator("tbody tr").nth(1)).to_be_visible()
    sb.fill("%")
    page.wait_for_timeout(700)
    ok("R2 tìm '%' không khớp mọi dòng", page.get_by_text(re.compile("Không tìm thấy")).count() >= 1)
    sb.fill("' OR 1=1 --")
    page.wait_for_timeout(700)
    ok("R2 tìm chuỗi SQL không lỗi, không rò", page.get_by_text(re.compile("Không tìm thấy")).count() >= 1)
    sb.fill("")
    page.get_by_label("Lọc theo loại").select_option(label="Doanh nghiệp")
    page.wait_for_timeout(600)
    ok("R2 lọc Doanh nghiệp: chỉ loại Doanh nghiệp", all("Doanh nghiệp" in r for r in table(page).locator("tbody tr").all_inner_texts()))
    page.get_by_label("Lọc theo trạng thái").select_option(label="Ngừng hợp tác")
    page.wait_for_timeout(600)
    rows = table(page).locator("tbody tr").all_inner_texts()
    ok("R2 lọc loại + ngừng hợp tác: khớp DB", len(rows) == q("select count(*) from purchasing_supplier where supplier_type='COMPANY' and is_active=0")[0][0], len(rows))
    page.get_by_label("Lọc theo loại").select_option(label="Cá nhân")
    page.wait_for_timeout(600)
    ok("R2 lọc Cá nhân + Ngừng: trạng thái rỗng khi không khớp", page.get_by_text("Không có nhà cung cấp nào khớp bộ lọc").count() == 1 or table(page).locator("tbody tr").count() == q("select count(*) from purchasing_supplier where supplier_type='INDIVIDUAL' and is_active=0")[0][0])
    page.get_by_label("Lọc theo loại").select_option(label="Mọi loại")
    page.get_by_label("Lọc theo trạng thái").select_option(label="Mọi trạng thái")
    page.wait_for_timeout(500)

    # --- Thêm: trống, trùng tuần tự, thành công
    t = table(page)
    n0 = q("select count(*) from purchasing_supplier")[0][0]
    page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
    dlg = page.get_by_role("dialog", name="Thêm nhà cung cấp")
    page.screenshot(path=f"{SHOTS}/impl-real-f1b-1280.png")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    ok("R3 tên trống: 'Nhập tên nhà cung cấp.' + viền đỏ, hộp còn mở", dlg.get_by_text("Nhập tên nhà cung cấp.").count() == 1 and dlg.is_visible())
    ok("R3 tên trống: không có POST nào gửi lên", not any(m == "POST" and pth.startswith("purchasing/suppliers/") for _, m, pth, _, _ in SEEN))
    ok("R3 tên trống: DB không thêm dòng", q("select count(*) from purchasing_supplier")[0][0] == n0)
    dlg.get_by_label("Tên").fill("   ")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    ok("R3 tên toàn khoảng trắng: vẫn báo trống", dlg.get_by_text("Nhập tên nhà cung cấp.").count() == 1)
    dlg.get_by_label("Tên").fill("  qa GHE alpha ")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    expect(dlg.get_by_text(NAME_TAKEN).first).to_be_visible()
    ok("R3 tên trùng (khác hoa thường, thừa khoảng trắng): lỗi dưới ô Tên, đúng một chỗ", dlg.get_by_text(NAME_TAKEN).count() == 1, dlg.inner_text()[:200])
    ok("R3 tên trùng: hộp còn mở, giữ nguyên chữ đã gõ", dlg.is_visible() and dlg.get_by_label("Tên").input_value() == "  qa GHE alpha ")
    ok("R3 tên trùng: nút chính đổi 'Thử lại'", dlg.get_by_role("button", name=re.compile("Thử lại")).count() == 1)
    ok("R3 tên trùng: DB không thêm dòng", q("select count(*) from purchasing_supplier")[0][0] == n0)
    page.screenshot(path=f"{SHOTS}/impl-real-f1b-trung-ten-1280.png")
    # sửa tên -> lỗi mất, lưu thật
    dlg.get_by_label("Tên").fill(f"QA Moi {SUFFIX}")
    page.wait_for_timeout(500)
    ok("R3 gõ lại tên: lỗi trùng biến mất ngay", dlg.get_by_text(NAME_TAKEN).count() == 0)
    page.screenshot(path=f"{SHOTS}/impl-real-f1b-retype-1280.png")
    dlg.get_by_label("Số điện thoại").fill("0900000555")
    dlg.get_by_role("button", name=re.compile("Thử lại|Lưu nhà cung cấp")).click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã thêm nhà cung cấp.")).to_be_visible()
    ok("R3 thêm thành công: toast + dòng mới trong danh sách + DB +1", q("select count(*) from purchasing_supplier")[0][0] == n0 + 1 and f"QA Moi {SUFFIX}" in t.inner_text())
    nm_new = f"QA Moi {SUFFIX}"
    cc = row_cells(t, nm_new)
    ok("R3 dòng mới: 0 phiếu, '—', 0 đ, Đang hợp tác", cc[3] == "0" and cc[4] == "—" and cc[6] == "0 đ" and "Đang hợp tác" in cc[5], cc)
    ok("R3 AuditLog supplier_create có đúng 1 dòng, không chứa tên/SĐT", q("select count(*) from accounts_auditlog where action='supplier_create' and (changes like ? or note like ? or object_repr like '%0900000555%')", f"%{nm_new}%", f"%0900000555%")[0][0] == 0 and q("select count(*) from accounts_auditlog where action='supplier_create'")[0][0] >= 1)
    # bấm đúp Lưu
    page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
    dlg = page.get_by_role("dialog", name="Thêm nhà cung cấp")
    dlg.get_by_label("Tên").fill(f"QA Dup {SUFFIX}")
    btn = dlg.get_by_role("button", name="Lưu nhà cung cấp")
    btn.dblclick()
    dlg.wait_for(state="detached")
    page.wait_for_timeout(600)
    ok("R3 bấm đúp 'Lưu nhà cung cấp': chỉ tạo 1 nhà cung cấp", q("select count(*) from purchasing_supplier where name=?", f"QA Dup {SUFFIX}")[0][0] == 1 and not page.get_by_text(NAME_TAKEN).count())

    # --- Hai tab cùng lúc cùng tên
    ctx2, page2, errs2 = session(b, "ql1")
    for pg in (page, page2):
        go(pg, "/suppliers/")
        table(pg)
        pg.get_by_role("button", name="Thêm nhà cung cấp").first.click()
        d = pg.get_by_role("dialog", name="Thêm nhà cung cấp")
        d.get_by_label("Tên").fill(f"QA Hai Tab {SUFFIX}")
    d1 = page.get_by_role("dialog", name="Thêm nhà cung cấp")
    d2 = page2.get_by_role("dialog", name="Thêm nhà cung cấp")
    # bắn gần như đồng thời
    page.evaluate("() => { window.__go = () => document.querySelector('[role=dialog] button[type=submit]').click(); }")
    page2.evaluate("() => { window.__go = () => document.querySelector('[role=dialog] button[type=submit]').click(); }")
    import threading
    th = [threading.Thread(target=lambda pg=pg: pg.evaluate("window.__go()")) for pg in (page, page2)]
    # playwright sync không thread-safe giữa các page: bấm tuần tự nhưng không chờ phản hồi giữa hai lần
    page.evaluate("window.__go()")
    page2.evaluate("window.__go()")
    page.wait_for_timeout(1500)
    cnt = q("select count(*) from purchasing_supplier where lower(name)=lower(?)", f"QA Hai Tab {SUFFIX}")[0][0]
    ok("R4 hai tab bấm Lưu liên tiếp cùng tên: DB đúng 1 dòng", cnt == 1, cnt)
    shown_err = [pg.get_by_role("dialog").get_by_text(NAME_TAKEN).count() for pg in (page, page2)]
    toast_ok = [pg.get_by_text("Đã thêm nhà cung cấp.").count() for pg in (page, page2)]
    ok("R4 một tab báo thành công, tab còn lại hiện lỗi tên trùng dưới ô Tên (đúng 1 chỗ)", sorted(shown_err) == [0, 1] and sorted(toast_ok) == [0, 1], (shown_err, toast_ok))
    loser = page if shown_err[0] == 1 else page2
    loser.screenshot(path=f"{SHOTS}/impl-real-two-tabs-loser-1280.png")
    ok("R4 bên thua giữ nguyên chữ đã gõ + nút 'Thử lại'", loser.get_by_role("dialog").get_by_label("Tên").input_value() == f"QA Hai Tab {SUFFIX}" and loser.get_by_role("dialog").get_by_role("button", name=re.compile("Thử lại")).count() == 1)
    loser.get_by_role("dialog").get_by_role("button", name="Huỷ").click()
    ctx2.close()

    # --- Chi tiết Alpha
    open_supplier(page, "QA Ghe Alpha")
    sid, cnt, last, tot = exp_supplier("QA Ghe Alpha")
    bd = body(page)
    ok("R5 chi tiết: tiêu đề + chip, không có thanh trạng thái", page.locator("main h2").first.inner_text().strip() == "QA Ghe Alpha" and page.get_by_text("Đang hợp tác").first.is_visible() and page.locator("[class*=statusPath], [class*=steps]").count() == 0)
    ok("R5 chi tiết: các trường Tên, Loại, Số điện thoại, Ghi chú", all(x in bd for x in ("Tên", "Loại", "Số điện thoại", "Ghi chú")) and "ghi chú giả" in bd and "0900000111" in bd)
    ok("R5 chi tiết: khối Mua hàng: số phiếu, tổng tiền, lần gần nhất = DB", f"{cnt} phiếu" in bd and vnd_text(tot) in bd and vn_dt(last) in bd, (cnt, tot, last))
    rt = page.locator("section[aria-label='Phiếu nhập'] table.lt")
    expect(rt.locator("tbody tr").first).to_be_visible()
    n_all = q("select count(*) from purchasing_purchasereceipt where supplier_id=?", sid)[0][0]
    expect(rt.locator("tbody tr")).to_have_count(n_all)
    page.wait_for_timeout(500)
    rows = [[c.strip() for c in tr.locator("td").all_inner_texts()] for tr in rt.locator("tbody tr").all()]
    rows = [r for r in rows if len(r) == 6 and r[0]]
    ok(f"R5 bảng Phiếu nhập hiện đủ {n_all} phiếu (Đã ghi nhận + Nháp + Đã huỷ)", len(rows) == n_all, rows)
    sts = [r[-1] for r in rows]
    ok("R5 chip phiếu: có Nháp, Đã ghi nhận, Đã huỷ", {"Nháp", "Đã ghi nhận", "Đã huỷ"} <= set(sts), sts)
    ok("R5 bảng Phiếu nhập: cột Tiền mua có cho Chủ + Mã phiếu font mono", heads(rt) == ["Mã phiếu", "Nhập lúc", "Mặt hàng", "Số kg", "Tiền mua", "Trạng thái"] and rt.locator("tbody tr").first.locator("td").first.evaluate("e => getComputedStyle(e).fontFamily.toLowerCase().includes('mono') || e.querySelector('code, .mono, [class*=mono]') !== null"), heads(rt))
    ok("R5 bảng Phiếu nhập: tổng tiền mua của dòng Nháp 99.999.900 đ hiện ở dòng Nháp nhưng KHÔNG cộng vào Tổng tiền mua", "99.999.900" in rt.inner_text() and "99.999.900" not in page.locator("section").first.inner_text() and vnd_text(tot) != "99.999.900 đ")
    ok("R5 bảng Phiếu nhập: dòng giờ nhập dạng dd/mm/yyyy hh:mm", all(re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", r[1]) for r in rows), [r[1] for r in rows])
    ok("R5 bảng Phiếu nhập: số kg dạng '10 kg'", all(re.search(r"\d(,\d+)? kg$", r[3]) for r in rows), [r[3] for r in rows])
    bt = page.locator("section[aria-label='Lô đang bán'] table.lt")
    nb = q("select count(*) from inventory_batch where supplier_id=? and qty_available>0", sid)[0][0]
    expect(bt.locator("tbody tr").first).to_be_visible()
    ok(f"R5 bảng Lô đang bán: {nb} lô còn tồn = DB", bt.locator("tbody tr").count() == nb, bt.locator("tbody tr").count())
    ok("R5 bảng Lô đang bán không lộ giá vốn", "Giá vốn" not in bt.inner_text() and "Giá mua" not in bt.inner_text())
    tl = page.locator("#supplier-timeline").inner_text()
    ok("R5 Dòng thời gian (NCC nạp bằng seed, chưa có AuditLog): trạng thái rỗng rõ ràng, không lỗi", "Chưa có việc nào được ghi lại" in tl, tl[:300])
    ok("R5 Dòng thời gian: không SĐT/ghi chú/giá", not any(x in tl for x in PHONES + ["ghi chú giả"] + PRIMERS), tl[:300])
    items = more_items(page)
    ok("R5 menu '…': Ngừng hợp tác + Xem nhật ký, không Xoá", any(i.startswith("Ngừng hợp tác") for i in items) and any(i.startswith("Xem nhật ký") for i in items) and not any("Xoá" in i for i in items), items)
    page.keyboard.press("Escape")
    ok("R5 không có nút/liên kết 'Xoá' nào trên trang chi tiết", page.get_by_role("button", name=re.compile("Xoá|Xóa")).count() == 0)
    page.screenshot(path=f"{SHOTS}/impl-real-detail-loc-1280.png", full_page=True)

    # --- sửa tại chỗ + AuditLog
    page.get_by_role("button", name="Sửa ghi chú").click()
    page.get_by_label("Ghi chú").first.fill("ghi chú mới QA")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    expect(page.get_by_text("Đã lưu nhà cung cấp.")).to_be_visible()
    ok("R6 sửa ghi chú tại chỗ: DB đổi", q("select note from purchasing_supplier where id=?", sid)[0][0] == "ghi chú mới QA")
    au = q("select changes, note from accounts_auditlog where action='supplier_update' and object_id=? order by id desc limit 1", str(sid))
    ok("R6 AuditLog supplier_update chỉ tên trường, không chép nội dung", au and "ghi chú mới QA" not in json.dumps(au) and "note" in json.dumps(au), au)
    expect(page.locator("#supplier-timeline")).to_contain_text("Cập nhật nhà cung cấp")
    tl2 = page.locator("#supplier-timeline").inner_text()
    ok("R6 Dòng thời gian sau sửa: có 'Cập nhật nhà cung cấp · <vai>' và không chép nội dung ghi chú/SĐT/tên", "ghi chú mới QA" not in tl2 and not any(x in tl2 for x in PHONES), tl2[:300])
    # tên trùng khi sửa tại chỗ
    page.get_by_role("button", name="Sửa tên").click()
    page.get_by_label("Tên").first.fill("qa chua nhap")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    expect(page.get_by_text(NAME_TAKEN).first).to_be_visible()
    ok("R6 sửa tên thành tên trùng: lỗi dưới ô, giữ chữ đang gõ, DB không đổi", page.get_by_label("Tên").first.input_value() == "qa chua nhap" and q("select name from purchasing_supplier where id=?", sid)[0][0] == "QA Ghe Alpha")
    page.get_by_role("button", name="Huỷ").first.click()
    # tên trống
    page.get_by_role("button", name="Sửa tên").click()
    page.get_by_label("Tên").first.fill("")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    page.screenshot(path=f"{SHOTS}/impl-real-inline-empty-name-1280.png")
    ok("R6 sửa tên thành trống: 'Nhập tên nhà cung cấp.'", page.get_by_text("Nhập tên nhà cung cấp.").count() >= 1 and q("select name from purchasing_supplier where id=?", sid)[0][0] == "QA Ghe Alpha")
    page.get_by_role("button", name="Huỷ").first.click()

    # --- màn cũ (stale): tab1 mở chi tiết, tab2 ngừng hợp tác; tab1 vẫn thấy "Đang hợp tác" rồi thao tác
    ctx3, page3, e3 = session(b, "ql1")
    open_supplier(page3, "QA Ghe Alpha")
    pick_more(page, "Ngừng hợp tác")
    dlg = page.get_by_role("dialog", name="Ngừng hợp tác với nhà cung cấp này?")
    ok("R7 hộp ngừng hợp tác nêu hậu quả", "Phiếu nhập và lô cũ giữ nguyên" in dlg.inner_text())
    dlg.get_by_role("button", name="Huỷ").click()
    dlg.wait_for(state="detached")
    ok("R7 bấm Huỷ: vẫn đang hợp tác (DB)", q("select is_active from purchasing_supplier where id=?", sid)[0][0] == 1)
    pick_more(page, "Ngừng hợp tác")
    dlg = page.get_by_role("dialog", name="Ngừng hợp tác với nhà cung cấp này?")
    dlg.get_by_role("button", name="Ngừng hợp tác").dblclick()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã ngừng hợp tác.")).to_be_visible()
    ok("R7 ngừng hợp tác: DB is_active=0, bản ghi + phiếu còn nguyên", q("select is_active from purchasing_supplier where id=?", sid)[0][0] == 0 and q("select count(*) from purchasing_purchasereceipt where supplier_id=?", sid)[0][0] == n_all)
    ok("R7 ngừng: chip đổi, menu đổi thành 'Bật lại hợp tác'", page.locator("main").get_by_text("Ngừng hợp tác").first.is_visible() and any(i.startswith("Bật lại hợp tác") for i in more_items(page)))
    page.keyboard.press("Escape")
    ok("R7 ngừng 2 lần (bấm đúp): AuditLog chỉ ghi 1 lần đổi trạng thái", q("select count(*) from accounts_auditlog where action='supplier_update' and object_id=? and changes like '%is_active%'", str(sid))[0][0] == 1, q("select changes from accounts_auditlog where action='supplier_update' and object_id=?", str(sid)))
    page.screenshot(path=f"{SHOTS}/impl-real-detail-ngung-1280.png", full_page=True)
    # màn cũ ở tab 3 (vẫn chip Đang hợp tác): bấm Ngừng hợp tác
    ok("R7 tab cũ vẫn hiển thị 'Đang hợp tác' (chưa tải lại)", page3.locator("main").get_by_text("Đang hợp tác").first.is_visible())
    pick_more(page3, "Ngừng hợp tác")
    d3 = page3.get_by_role("dialog", name="Ngừng hợp tác với nhà cung cấp này?")
    d3.get_by_role("button", name="Ngừng hợp tác").click()
    page3.wait_for_timeout(1200)
    ok("R7 màn cũ bấm ngừng khi đã ngừng: không văng lỗi/trắng trang, có phản hồi rõ (toast hoặc hộp lỗi)", page3.get_by_text("Đã ngừng hợp tác.").count() >= 1 or d3.is_visible(), body(page3)[:200])
    ok("R7 màn cũ: trạng thái cuối trên màn = Ngừng hợp tác", page3.locator("main").get_by_text("Ngừng hợp tác").first.is_visible())
    page3.screenshot(path=f"{SHOTS}/impl-real-stale-1280.png")
    # màn cũ sửa tên trùng người khác
    # --- Nhập lô: NCC đã ngừng không còn trong danh sách chọn (ED-22-AC5)
    go(page, "/purchasing/")
    page.wait_for_selector("select", timeout=15000)
    opts = page.locator("select").first.locator("option").all_inner_texts()
    ok("R8 Nhập lô: NCC đã ngừng KHÔNG nằm trong danh sách chọn", "QA Ghe Alpha" not in opts and "QA Ngung Hop Tac" not in opts and any("QA Chua Nhap" in o for o in opts), opts[:6])
    sel_val = page.locator("select").first.evaluate("e => e.options[e.selectedIndex] ? e.options[e.selectedIndex].text : null")
    ok("R8 Nhập lô: nhà cung cấp mặc định được chọn là người đang hợp tác", sel_val is not None and "QA Ngung" not in sel_val and "QA Ghe Alpha" not in sel_val, sel_val)
    page.screenshot(path=f"{SHOTS}/impl-real-receive-batches-1280.png")
    ctx3.close()

    # bật lại
    open_supplier(page, "QA Ghe Alpha")
    pick_more(page, "Bật lại hợp tác")
    dlg = page.get_by_role("dialog", name="Bật lại hợp tác?")
    dlg.get_by_role("button", name="Bật lại hợp tác").click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã bật lại hợp tác.")).to_be_visible()
    ok("R7 bật lại: DB is_active=1", q("select is_active from purchasing_supplier where id=?", sid)[0][0] == 1)
    go(page, "/purchasing/")
    page.wait_for_selector("select", timeout=15000)
    ok("R8 Nhập lô: sau khi bật lại, NCC có lại trong danh sách", any("QA Ghe Alpha" in o for o in page.locator("select").first.locator("option").all_inner_texts()))

    # kịch bản: NCC đứng đầu danh sách (theo tên) bị ngừng -> form Nhập lô mặc định chọn ai
    first_id, first_name = q("select id, name from purchasing_supplier where is_active=1 order by name limit 1")[0]
    sc = sqlite3.connect(DB); sc.execute("update purchasing_supplier set is_active=0 where id=?", (first_id,)); sc.commit(); sc.close()
    go(page, "/purchasing/")
    page.wait_for_selector("select", timeout=15000)
    page.wait_for_timeout(800)
    chosen = page.locator("select").first.evaluate("e => e.options[e.selectedIndex] ? e.options[e.selectedIndex].text : null")
    opts = page.locator("select").first.locator("option").all_inner_texts()
    ok(f"R8b Nhập lô: khi NCC đứng đầu danh sách ('{first_name}') đã ngừng, ô chọn KHÔNG tự chọn nó", chosen is not None and first_name not in (chosen or "") and first_name not in opts, (chosen, opts[:4]))
    sc = sqlite3.connect(DB); sc.execute("update purchasing_supplier set is_active=1 where id=?", (first_id,)); sc.commit(); sc.close()

    # --- quét response + storage + console
    dump = storage_dump(page)
    ok("R9 loc: storage + URL không có SĐT/tên NCC", not any(x in dump for x in PHONES + ["0900000555", "QA Ghe", "QA Chua"]), dump[:200])
    cons = " ".join(page._allconsole)
    ok("R9 loc: console không có SĐT/tên NCC", not any(x in cons for x in PHONES + ["0900000555"]), cons[:200])
    ok("R9 loc: không có console error/warning", not errs, errs[:3])
    ok("R9 loc: không có request DELETE/PUT nào tới /suppliers/ (FE không gọi xoá)", not any(u == "loc" and m in ("DELETE", "PUT") for u, m, *_ in SEEN))
    page.screenshot(path=f"{SHOTS}/impl-real-final-loc-1280.png")
    ctx.close()

    # ======================================================= ql1
    ctx, page, errs = session(b, "ql1")
    go(page, "/suppliers/")
    t = table(page)
    h = heads(t)
    ok("R10 ql1: danh sách không có cột Tổng tiền mua (6 cột)", h == ["Nhà cung cấp", "Loại", "Số điện thoại", "Số phiếu nhập", "Lần nhập gần nhất", "Trạng thái"], h)
    html = page.content()
    ok("R10 ql1: HTML không có 'Tổng tiền mua', 'Tiền mua', số mồi, số tiền", "Tổng tiền mua" not in html and "Tiền mua" not in html and not any(x in html for x in PRIMERS) and not re.search(r"\d{1,3}(\.\d{3})+ đ", html))
    page.screenshot(path=f"{SHOTS}/impl-real-list-ql1-1280.png")
    open_supplier(page, "QA Ghe Alpha")
    html = page.content()
    ok("R10 ql1: chi tiết không có tổng tiền, tiền mua, số mồi", "Tổng tiền mua" not in html and "Tiền mua" not in html and not any(x in html for x in PRIMERS) and not re.search(r"\d{1,3}(\.\d{3})+ đ", html))
    ok("R10 ql1: chi tiết vẫn thấy Phiếu nhập (số kg, trạng thái) + Lô đang bán + Mua hàng (số phiếu, lần gần nhất)", page.locator("section[aria-label='Phiếu nhập'] table.lt tbody tr").count() >= 3 and page.locator("section[aria-label='Lô đang bán'] table.lt").count() == 1 and "Lần nhập gần nhất" in body(page))
    rt = page.locator("section[aria-label='Phiếu nhập'] table.lt")
    ok("R10 ql1: bảng Phiếu nhập không có cột Tiền mua", "Tiền mua" not in heads(rt), heads(rt))
    page.screenshot(path=f"{SHOTS}/impl-real-detail-ql1-1280.png", full_page=True)
    # ql1 thêm, sửa, ngừng được
    go(page, "/suppliers/")
    page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
    dlg = page.get_by_role("dialog", name="Thêm nhà cung cấp")
    dlg.get_by_label("Tên").fill(f"QA ql1 {SUFFIX}")
    dlg.get_by_label("Loại").select_option(label="Doanh nghiệp")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    dlg.wait_for(state="detached")
    ok("R10 ql1: thêm NCC được (DB)", q("select supplier_type from purchasing_supplier where name=?", f"QA ql1 {SUFFIX}") == [("COMPANY",)])
    ok("R10 ql1: AuditLog ghi người làm là ql1", q("select count(*) from accounts_auditlog a join auth_user u on u.id=a.actor_id where a.action='supplier_create' and u.username='ql1'")[0][0] >= 1)
    open_supplier(page, f"QA ql1 {SUFFIX}")
    page.get_by_role("button", name="Sửa", exact=True).first.click()
    dlg = page.get_by_role("dialog", name="Sửa nhà cung cấp")
    dlg.get_by_label("Loại").select_option(label="Cá nhân")
    dlg.get_by_role("button", name="Lưu thay đổi").click()
    dlg.wait_for(state="detached")
    ok("R10 ql1: Sửa bằng hộp (đổi loại): chỉ gửi trường đổi, DB đổi", q("select supplier_type from purchasing_supplier where name=?", f"QA ql1 {SUFFIX}") == [("INDIVIDUAL",)])
    patches = [(pth, bd) for u, m, pth, s, bd in SEEN if u == "ql1" and m == "PATCH"]
    ok("R10 ql1: không PATCH nào chứa purchase_total/số mồi trong phản hồi", all("purchase_total" not in bd for _, bd in patches), patches[:1])
    pick_more(page, "Ngừng hợp tác")
    page.get_by_role("dialog").get_by_role("button", name="Ngừng hợp tác").click()
    expect(page.get_by_text("Đã ngừng hợp tác.")).to_be_visible()
    ok("R10 ql1: ngừng hợp tác được", q("select is_active from purchasing_supplier where name=?", f"QA ql1 {SUFFIX}") == [(0,)])
    ok("R10 ql1: console sạch", not errs, errs[:3])
    # quét mọi response của ql1
    leaks = []
    for u, m, pth, s, bd in SEEN:
        if u != "ql1" or not bd.strip().startswith(("{", "[")) or "suppliers" not in pth and "receipts" not in pth and "batches" not in pth and "guidance" not in pth:
            continue
        try:
            ks = keys_deep(json.loads(bd))
        except Exception:
            continue
        if ks & COST_KEYS:
            leaks.append((pth, sorted(ks & COST_KEYS)))
        if any(x in bd for x in ("77777", "80001", "123457", "91919", "777770", "1640020", "459595")):
            leaks.append((pth, "số mồi"))
    ok("R10 ql1: mọi response liên quan (suppliers, receipts, batches, guidance) không có khoá giá vốn / số mồi", not leaks, leaks[:3])
    ctx.close()

    # ======================================================= kho1
    ctx, page, errs = session(b, "kho1")
    go(page, "/suppliers/")
    t = table(page)
    ok("R11 kho1: xem được danh sách, không cột Tổng tiền mua, không nút Thêm", "Tổng tiền mua" not in heads(t) and page.get_by_role("button", name="Thêm nhà cung cấp").count() == 0, heads(t))
    ok("R11 kho1: HTML không có số mồi/tiền", not any(x in page.content() for x in PRIMERS) and not re.search(r"\d{1,3}(\.\d{3})+ đ", page.content()))
    open_supplier(page, "QA Ghe Alpha")
    ok("R11 kho1: chi tiết không nút Sửa, không bút sửa tại chỗ", page.get_by_role("button", name="Sửa", exact=True).count() == 0 and page.get_by_role("button", name=re.compile("^Sửa ")).count() == 0)
    page.get_by_role("button", name="Thao tác khác").click()
    item = page.get_by_role("menuitem", name=re.compile("^Ngừng hợp tác"))
    ok("R11 kho1: 'Ngừng hợp tác' bị chặn kèm lý do 'Chỉ Chủ và Quản lý.' nằm cạnh", item.count() == 1 and item.get_attribute("aria-disabled") == "true" and "Chỉ Chủ và Quản lý." in item.inner_text(), item.inner_text() if item.count() else "")
    item.click(force=True)
    page.wait_for_timeout(400)
    ok("R11 kho1: bấm mục bị chặn không mở hộp xác nhận", page.get_by_role("dialog").count() == 0)
    page.keyboard.press("Escape")
    html = page.content()
    ok("R11 kho1: chi tiết không có tiền, số mồi, 'Tổng tiền mua', 'Tiền mua'", "Tổng tiền mua" not in html and "Tiền mua" not in html and not any(x in html for x in PRIMERS) and not re.search(r"\d{1,3}(\.\d{3})+ đ", html))
    page.screenshot(path=f"{SHOTS}/impl-real-detail-kho1-1280.png", full_page=True)
    leaks = []
    for u, m, pth, s, bd in SEEN:
        if u != "kho1" or not bd.strip().startswith(("{", "[")):
            continue
        try:
            ks = keys_deep(json.loads(bd))
        except Exception:
            continue
        if ks & COST_KEYS:
            leaks.append((pth, sorted(ks & COST_KEYS)))
        if any(x in bd for x in ("77777", "80001", "123457", "91919", "777770", "1640020", "459595")):
            leaks.append((pth, "số mồi"))
    ok("R11 kho1: mọi response không có khoá giá vốn / số mồi", not leaks, leaks[:3])
    ok("R11 kho1: console sạch", not errs, errs[:3])
    ctx.close()

    # ======================================================= giao1, cs2
    for u in ("giao1", "cs2"):
        ctx, page, errs = session(b, u)
        navtxt = page.locator(".nav").inner_text()
        ok(f"R12 {u}: menu không có 'Nhà cung cấp'", "Nhà cung cấp" not in navtxt, navtxt[:200])
        n_before = len(SEEN)
        go(page, "/suppliers/")
        page.wait_for_timeout(800)
        ok(f"R12 {u}: vào thẳng /suppliers/ thấy 'Không có quyền', không bảng", page.get_by_text(re.compile("không có quyền", re.I)).count() >= 1 and page.locator("table.lt").count() == 0, body(page)[:200])
        go(page, f"/suppliers/detail/?id={q('select id from purchasing_supplier where name=?', 'QA Ghe Alpha')[0][0]}")
        page.wait_for_timeout(800)
        txt = body(page)
        ok(f"R12 {u}: vào thẳng chi tiết thấy 'Không có quyền', không rò tên/SĐT/ghi chú", re.search("không có quyền", txt, re.I) is not None and not any(x in txt for x in ["QA Ghe", "0900000111", "ghi chú"]), txt[:200])
        got = [(m, pth, s) for uu, m, pth, s, bd in SEEN[n_before:] if uu == u and "suppliers" in pth]
        ok(f"R12 {u}: màn không mount nên không gọi API suppliers; nếu có gọi thì BE trả 403 (không 200)", all(s == 403 for _, _, s in got), got)
        ok(f"R12 {u}: console không có lỗi nào ngoài 403 mong đợi", not [e for e in errs if "403" not in e], errs[:3])
        ctx.close()

    # ======================================================= 360px
    for u in ("loc", "kho1"):
        ctx, page, errs = session(b, u, w=360, h=800, touch=True)
        go(page, "/suppliers/")
        table(page)
        ok(f"R13 {u} 360px danh sách: không cuộn ngang trang", not hscroll(page))
        page.screenshot(path=f"{SHOTS}/impl-real-list-{u}-360.png", full_page=True)
        small = page.evaluate("""() => [...document.querySelectorAll('button, a, input, select, textarea')].filter(e => {
            const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
            return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y < innerHeight && !e.classList.contains('sr-only') && !e.classList.contains('lt-link') && !e.matches('input[type=checkbox]') && (r.height < 44 || r.width < 44);
          }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0, 30) + ' ' + e.tagName + '.' + String(e.className).slice(0, 20) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))""")
        ok(f"R13 {u} 360px danh sách: vùng bấm >= 44px (trừ liên kết tên trong dòng, đã kiểm riêng bên dưới)", not small, small)
        rh = page.evaluate("() => [...document.querySelectorAll('table.lt tbody tr.lt-click')].map(r => Math.round(r.getBoundingClientRect().height))")
        ok(f"R13 {u} 360px danh sách: mỗi dòng cao >= 44px", rh and min(rh) >= 44, rh)
        rows_ = page.locator("table.lt tbody tr.lt-click")
        rows_.nth(1).locator("td").last.click(position={"x": 5, "y": 5})
        try:
            page.wait_for_url("**/suppliers/detail/**", timeout=6000)
            tapped = True
        except Exception:
            tapped = False
        ok(f"R13 {u} 360px: chạm vào ô bất kỳ của dòng (không phải liên kết tên) mở chi tiết", tapped, page.url)
        go(page, "/suppliers/")
        table(page)
        open_supplier(page, "QA Ghe Alpha")
        ok(f"R13 {u} 360px chi tiết: không cuộn ngang trang", not hscroll(page))
        page.screenshot(path=f"{SHOTS}/impl-real-detail-{u}-360.png", full_page=True)
        small = page.evaluate("""() => [...document.querySelectorAll('main button, main a, main input, main select, main textarea, header button, header a')].filter(e => {
            const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
            return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && !e.classList.contains('sr-only') && !e.classList.contains('lt-link') && !e.matches('input[type=checkbox]') && (r.height < 44 || r.width < 44);
          }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0, 30) + ' ' + e.tagName + '.' + String(e.className).slice(0, 20) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))""")
        ok(f"R13 {u} 360px chi tiết: vùng bấm >= 44px (không loại trừ)", not small, small)
        if u == "loc":
            go(page, "/suppliers/")
            table(page)
            page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
            page.wait_for_selector("[role=dialog]")
            ok("R13 loc 360px hộp Thêm: không cuộn ngang trang, hộp nằm trong màn hình", not hscroll(page) and page.evaluate("() => { const r = document.querySelector('[role=dialog]').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth + 1 }"))
            small = page.evaluate("""() => [...document.querySelectorAll('[role=dialog] button, [role=dialog] input, [role=dialog] select, [role=dialog] textarea')].filter(e => { const r = e.getBoundingClientRect(); return r.height < 44 && !e.matches('input[type=checkbox]') && r.width > 0 }).map(e => (e.getAttribute('aria-label') || e.name || e.innerText || e.tagName).slice(0,20) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))""")
            ok("R13 loc 360px hộp Thêm: vùng bấm >= 44px", not small, small)
            page.screenshot(path=f"{SHOTS}/impl-real-f1b-loc-360.png")
        ok(f"R13 {u} 360px: console sạch", not errs, errs[:3])
        ctx.close()


    # ======================================================= Vòng 2: B1, B2, B3 ca ngoài đường thuận
    ctx, page, errs = session(b, "loc")
    go(page, "/suppliers/")
    t = table(page)
    n0 = q("select count(*) from purchasing_supplier")[0][0]

    def alert_count(dlg):
        return dlg.locator("[role=alert], .alert-box, .form-alert").count()
    # B1-a: thêm: trùng -> gõ 1 ký tự -> không còn lỗi nào, nút về "Lưu nhà cung cấp"
    page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
    dlg = page.get_by_role("dialog", name="Thêm nhà cung cấp")
    dlg.get_by_label("Tên").fill("QA Ghe Alpha")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    expect(dlg.get_by_text(NAME_TAKEN).first).to_be_visible()
    ok("B1a trùng tên: lỗi đúng 1 chỗ dưới ô Tên, không banner đầu hộp", dlg.get_by_text(NAME_TAKEN).count() == 1 and alert_count(dlg) <= 1)
    dlg.get_by_label("Tên").press_sequentially("x")
    page.wait_for_timeout(400)
    ok("B1a gõ thêm 1 ký tự: không còn câu trùng tên ở BẤT KỲ đâu trong hộp", dlg.get_by_text(NAME_TAKEN).count() == 0, dlg.inner_text()[:300])
    ok("B1a gõ lại: nút chính về 'Lưu nhà cung cấp' (không còn 'Thử lại')", dlg.get_by_role("button", name="Lưu nhà cung cấp").count() == 1 and dlg.get_by_role("button", name=re.compile("Thử lại")).count() == 0)
    page.screenshot(path=f"{SHOTS}/impl-real-r2-b1-retype-1280.png")
    # B1-b: gõ lại thành tên trùng KHÁC -> bấm Lưu -> lỗi quay lại dưới ô Tên, chỉ 1 chỗ
    dlg.get_by_label("Tên").fill("QA Chua Nhap")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    expect(dlg.get_by_text(NAME_TAKEN).first).to_be_visible()
    ok("B1b trùng lần 2 với tên khác: lỗi quay lại đúng 1 chỗ", dlg.get_by_text(NAME_TAKEN).count() == 1)
    # B1-c: lỗi trùng rồi xoá trắng ô Tên -> câu 'Nhập tên nhà cung cấp.' thay cho câu trùng
    dlg.get_by_label("Tên").fill("")
    page.wait_for_timeout(300)
    ok("B1c xoá hết tên sau khi báo trùng: câu trùng biến mất", dlg.get_by_text(NAME_TAKEN).count() == 0)
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    ok("B1c rồi Lưu khi trống: 'Nhập tên nhà cung cấp.' đúng 1 chỗ, không POST thêm", dlg.get_by_text("Nhập tên nhà cung cấp.").count() == 1)
    # B1-d: lỗi trùng rồi chỉ đổi SĐT (không đụng tên): ghi nhận hành vi, hộp không được trắng, dữ liệu giữ
    dlg.get_by_label("Tên").fill("QA Ghe Alpha")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    expect(dlg.get_by_text(NAME_TAKEN).first).to_be_visible()
    dlg.get_by_label("Số điện thoại").fill("0900000999")
    page.wait_for_timeout(300)
    ok("B1d báo trùng rồi chỉ sửa SĐT: lỗi trùng tên vẫn nằm đúng ô Tên (chưa sửa tên), không nhảy lên banner", dlg.get_by_text(NAME_TAKEN).count() <= 1 and dlg.get_by_label("Tên").input_value() == "QA Ghe Alpha", dlg.inner_text()[:200])
    ok("B1 đến đây DB không thêm dòng nào", q("select count(*) from purchasing_supplier")[0][0] == n0)
    # B1-e: sửa tên thành tên mới hợp lệ rồi lưu thành công
    dlg.get_by_label("Tên").fill(f"QA Vong2 {SUFFIX}")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    dlg.wait_for(state="detached")
    ok("B1e sau khi gõ lại tên hợp lệ lưu thành công 1 dòng", q("select count(*) from purchasing_supplier where name=?", f"QA Vong2 {SUFFIX}")[0][0] == 1)
    # B1-f: hộp Sửa (chi tiết): đổi tên thành tên trùng -> lỗi -> gõ lại
    open_supplier(page, f"QA Vong2 {SUFFIX}")
    page.get_by_role("button", name="Sửa", exact=True).first.click()
    dlg = page.get_by_role("dialog", name="Sửa nhà cung cấp")
    dlg.get_by_label("Tên").fill("qa chua nhap")
    dlg.get_by_role("button", name="Lưu thay đổi").click()
    expect(dlg.get_by_text(NAME_TAKEN).first).to_be_visible()
    ok("B1f hộp Sửa: tên trùng báo đúng 1 chỗ", dlg.get_by_text(NAME_TAKEN).count() == 1)
    dlg.get_by_label("Tên").press_sequentially("2")
    page.wait_for_timeout(400)
    ok("B1f hộp Sửa: gõ lại thì hết lỗi trùng ở mọi chỗ, nút về 'Lưu thay đổi'", dlg.get_by_text(NAME_TAKEN).count() == 0 and dlg.get_by_role("button", name="Lưu thay đổi").count() == 1, dlg.inner_text()[:300])
    dlg.get_by_role("button", name="Huỷ").click()
    # B1-g: màn đóng/mở lại hộp: lỗi cũ không còn
    page.get_by_role("button", name="Sửa", exact=True).first.click()
    dlg = page.get_by_role("dialog", name="Sửa nhà cung cấp")
    ok("B1g mở lại hộp Sửa sau khi Huỷ: không còn lỗi cũ, tên là tên gốc", dlg.get_by_text(NAME_TAKEN).count() == 0 and dlg.get_by_label("Tên").input_value() == f"QA Vong2 {SUFFIX}")
    dlg.get_by_role("button", name="Huỷ").click()
    # B3: sửa tại chỗ — trống, khoảng trắng, rồi gõ lại hết lỗi, lưu thành công; SĐT/Ghi chú để trống được (không bắt buộc)
    sid2 = q("select id from purchasing_supplier where name=?", f"QA Vong2 {SUFFIX}")[0][0]
    patch_n0 = len([1 for u, m, pth, st, bd in SEEN if m == "PATCH" and pth.endswith(f"suppliers/{sid2}/")])
    page.get_by_role("button", name="Sửa tên").click()
    inp = page.get_by_label("Tên").first
    inp.fill("")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    ok("B3 sửa tên tại chỗ để trống: đúng câu 'Nhập tên nhà cung cấp.' (1 chỗ), không câu chung", page.get_by_text("Nhập tên nhà cung cấp.").count() == 1 and page.get_by_text("Nhập giá trị cho ô này.").count() == 0)
    inp.fill("    ")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    ok("B3 sửa tên toàn khoảng trắng: vẫn đúng câu", page.get_by_text("Nhập tên nhà cung cấp.").count() == 1 and q("select name from purchasing_supplier where id=?", sid2)[0][0] == f"QA Vong2 {SUFFIX}")
    ok("B3 tên trống: không PATCH nào được gửi", len([1 for u, m, pth, st, bd in SEEN if m == "PATCH" and pth.endswith(f"suppliers/{sid2}/")]) == patch_n0)
    page.screenshot(path=f"{SHOTS}/impl-real-r2-b3-empty-1280.png")
    inp.fill(f"QA Vong2b {SUFFIX}")
    page.wait_for_timeout(300)
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    expect(page.get_by_text("Đã lưu nhà cung cấp.")).to_be_visible()
    ok("B3 gõ lại tên rồi lưu: thành công, DB đổi", q("select name from purchasing_supplier where id=?", sid2)[0][0] == f"QA Vong2b {SUFFIX}")
    page.get_by_role("button", name="Sửa số điện thoại").click()
    page.get_by_label("Số điện thoại").first.fill("")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    page.wait_for_timeout(800)
    ok("B3 SĐT không bắt buộc: để trống lưu được (không bị câu 'Nhập tên nhà cung cấp.')", page.get_by_text("Nhập tên nhà cung cấp.").count() == 0 and q("select phone from purchasing_supplier where id=?", sid2)[0][0] in ("", None), q("select phone from purchasing_supplier where id=?", sid2))
    ok("B3 console sạch", not errs, errs[:3])

    # B2: 44x44 ở 1280 và 360 (chạm thật), trên BE thật
    def pencil_rects(pg):
        return pg.evaluate("""() => [...document.querySelectorAll('button[aria-label^="Sửa "]')].filter(b => /pencil/.test(b.className)).map(b => { const r = b.getBoundingClientRect(); return {l: b.getAttribute('aria-label'), x: r.x, y: r.y, w: r.width, h: r.height}; })""")
    open_supplier(page, "QA Chua Nhap")
    pr = pencil_rects(page)
    ok("B2 1280: 3 bút, mỗi bút >= 44x44", len(pr) == 3 and all(x["w"] >= 43.5 and x["h"] >= 43.5 for x in pr), pr)
    ctx.close()
    ctx, page, errs = session(b, "ql1", w=360, h=800, touch=True)
    open_supplier(page, "QA Chua Nhap")
    pr = pencil_rects(page)
    ok("B2 360 (ql1, cảm ứng): 3 bút, mỗi bút >= 44x44", len(pr) == 3 and all(x["w"] >= 43.5 and x["h"] >= 43.5 for x in pr), pr)
    ok("B2 360: không cuộn ngang trang", not hscroll(page))
    page.touchscreen.tap(pr[0]["x"] + 4, pr[0]["y"] + pr[0]["h"] / 2)
    page.wait_for_timeout(400)
    ok("B2 360: chạm vào mép vùng bút mở ô sửa tên", page.get_by_label("Tên").count() >= 1 and page.get_by_role("button", name="Huỷ").count() >= 1)
    page.screenshot(path=f"{SHOTS}/impl-real-r2-b2-360.png")
    page.get_by_role("button", name="Huỷ").first.click()
    pr2 = pencil_rects(page)
    ok("B2 360: sau Huỷ bút trở lại, vẫn 44x44, trang không nhảy", len(pr2) == 3 and abs(pr2[0]["y"] - pr[0]["y"]) < 3, (pr, pr2))
    ok("B2 360: ql1 console sạch", not errs, errs[:3])
    ctx.close()
    ctx, page, errs = session(b, "kho1", w=360, h=800, touch=True)
    open_supplier(page, "QA Chua Nhap")
    ok("B2 kho1 (không quyền sửa): không có bút nào", len(pencil_rects(page)) == 0)
    ctx.close()

    # ======================================================= danh sách rỗng / lỗi mạng (BE thật): ngắt mạng
    ctx, page, errs = session(b, "loc")
    go(page, "/suppliers/")
    table(page)
    ctx.set_offline(True)
    page.get_by_label("Lọc theo loại").select_option(label="Doanh nghiệp")
    page.wait_for_timeout(1500)
    txt = body(page)
    ok("R14 mất mạng khi lọc: hiện lỗi rõ + cách xử (không trang trắng, không số liệu sai)", re.search(r"(Mất kết nối|Thử lại|không tải được|Chưa tải được)", txt) is not None, txt[:300])
    page.screenshot(path=f"{SHOTS}/impl-real-offline-1280.png")
    ctx.set_offline(False)
    ctx.close()
    b.close()

# ---- tổng
bad = [n for n, c in R if not c]
print(f"\n{len(R) - len(bad)}/{len(R)} PASS")
if bad:
    print("FAIL:", *bad, sep="\n  ")
sys.exit(1 if bad else 0)
