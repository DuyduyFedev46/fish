# QA độc lập Lô 9 (ED-26) trên BE THẬT: Django :8000 (SQLite tạm nạp bằng fixture, xem qa_ed_batch9_api.py) + console build thật :3102.
#   QA_DB=<sqlite> SHOTS=<thư mục> python3 e2e/qa_ed_batch9_real.py     (cần nạp lại DB trước mỗi lần chạy)
# Chỉ dữ liệu giả. Phiếu giao: RACE=1 (giao1, 10kg lô A), FAILED=2 (giao1, 5kg lô A + 4kg lô B, Giao thất bại), OTHER=3 (giao2),
# RESTOCK=4, WRITEOFF=5 (giao1, 6kg lô A).
import json
import os
import re
import sqlite3
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3102")
SHOTS = os.environ.get("SHOTS", "/tmp")
DB = os.environ["QA_DB"]
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=15000)
R = []
SEEN = []  # (method, path, status, body-text)


def ok(n, c, e=""):
    R.append((n, bool(c)))
    print("PASS" if c else "FAIL", n, "" if c else "  -> " + str(e)[:600], flush=True)


def q(sql, *a):
    c = sqlite3.connect(DB)
    try:
        return c.execute(sql, a).fetchall()
    finally:
        c.close()


def stock(pk):
    return float(q("select qty_available from inventory_batch where id=?", pk)[0][0])


def ledger(pk):
    return q("select movement_type, qty_change, reference from inventory_stockledgerentry where batch_id=? order by id", pk)


def session(b, user, w=1280, h=860, touch=False):
    ctx = b.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", **({"is_mobile": True, "has_touch": True} if touch else {}))
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type in ("error", "warning") and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errs.append(m.type + ": " + m.text))
    page.on("pageerror", lambda e: errs.append("pageerror " + str(e)))

    def on_resp(r):
        if "/api/" in r.url:
            try:
                body = r.text()
            except Exception:
                body = ""
            SEEN.append((r.request.method, r.url.split("/api/")[1], r.status, body, user))
    page.on("response", on_resp)
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill("Songbien2026")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a, nav a, [role=navigation] a", state="attached")
    return ctx, page, errs


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def rows(page):
    return [t.strip() for t in page.locator("main table tbody tr td:first-child").all_inner_texts()]


def open_form(page, note_hint, batch_hint=None):
    page.get_by_role("button", name="Nhập hàng hoàn").click()
    d = page.get_by_role("dialog")
    page.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
    label = [t for t in d.get_by_label("Phiếu giao").locator("option").all_inner_texts() if note_hint in t][0]
    d.get_by_label("Phiếu giao").select_option(label=label)
    page.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null || document.querySelector('[role=dialog] select:nth-of-type(2)') !== null")
    return d


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------- A. giao1 ở 360px: thẻ Mang hàng về kho (phiếu Giao thất bại, 2 lô) ----------
    ctx, page, errs = session(b, "giao1", 360, 780, touch=True)
    reqs_ai = []
    page.on("request", lambda r: reqs_ai.append(r.url) if "/api/ai" in r.url else None)
    go(page, "/my-deliveries/")
    card = page.locator("li[data-status=FAILED]").first
    ok("A1 giao1: thẻ Giao thất bại có nút 'Mang hàng về kho'", card.get_by_role("button", name="Mang hàng về kho").count() == 1)
    page.screenshot(path=f"{SHOTS}/impl-real-mydeliveries-360.png")
    card.get_by_role("button", name="Mang hàng về kho").click()
    d = page.get_by_role("dialog")
    page.wait_for_function("() => document.querySelector('[role=dialog] select') && document.querySelector('[role=dialog] select').value !== ''")
    sel_txt = d.get_by_label("Phiếu giao").evaluate("e => e.options[e.selectedIndex].text")
    ok("A2 F2m mở sẵn đúng phiếu giao thất bại (SO-QA9-FAIL)", "SO-QA9-FAIL" in sel_txt, sel_txt)
    ok("A2 360px: hộp không cuộn ngang", no_hscroll(page))
    # phiếu 2 nhiều lô: phải chọn lô
    page.wait_for_timeout(800)
    selects = d.locator("select")
    print("INFO F2m có", selects.count(), "ô chọn; text:", d.inner_text().replace("\n", " | ")[:400])
    page.screenshot(path=f"{SHOTS}/impl-real-f2m-prefilled-360.png")
    batch_sel = d.get_by_label(re.compile("^Lô"))
    ok("A3 phiếu nhiều lô: có ô chọn Lô (không tự chọn bừa)", batch_sel.count() == 1, d.inner_text()[:300])
    if batch_sel.count() == 1:
        opts = batch_sel.locator("option").all_inner_texts()
        print("INFO các lô:", opts)
        ok("A3 ô Lô liệt kê đúng 2 lô của phiếu (không lô ngoài phiếu)", len([o for o in opts if re.search(r"CA01|TOM01", o)]) == 2, opts)
        a_label = [o for o in opts if "CA01" in o][0]
        batch_sel.select_option(label=a_label)
        page.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
        facts = d.locator("[data-qty-facts]").inner_text()
        ok("A4 kg theo lô: 'Đã giao 5 kg, đã hoàn 0 kg, còn hoàn được 5 kg' (lô A)", "Đã giao 5 kg" in facts and "còn hoàn được 5 kg" in facts, facts)
        d.get_by_label("Số kg hoàn").fill("5,5")
        d.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
        txt = d.inner_text()
        ok("A5 quá kg bị chặn tại ô số kg (5,5 > 5)", page.get_by_role("dialog").count() == 1 and re.search(r"vượt|còn hoàn được 5 kg", txt), txt[:300])
        n_post = sum(1 for s in SEEN if s[0] == "POST" and s[1].startswith("inventory/returns") and s[4] == "giao1")
        ok("A5 chặn trước khi gửi: không có POST nào lên máy chủ", n_post == 0, n_post)
        ok("A5 DB: chưa có phiếu hàng hoàn nào", q("select count(*) from inventory_returntostock")[0][0] == 0)
        page.screenshot(path=f"{SHOTS}/impl-real-f2m-over-360.png")
        d.get_by_label("Số kg hoàn").fill("2")
        d.get_by_label(re.compile("Ghi chú")).fill("khách không nghe máy")
        d.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).dblclick()
        page.wait_for_function("() => !document.querySelector('[role=dialog]')")
        page.wait_for_timeout(800)
        cnt = q("select count(*), min(qty), min(status), min(decision) from inventory_returntostock")[0]
        ok("A6 giao1 gửi 2 kg (bấm đúp): đúng 1 phiếu Chờ duyệt trong DB", cnt[0] == 1 and float(cnt[1]) == 2.0 and cnt[2] == "DRAFT" and cnt[3] == "PENDING", cnt)
    ok("A7 giao1 360: không console error/warning", errs == [], errs)
    ok("A7 giao1: không có request tới /api/ai* khi mở Việc giao của tôi", reqs_ai == [], reqs_ai)
    ctx.close()

    # ---------- B. Hai tab nhập phần còn lại (phiếu RACE 10 kg) ----------
    ctx, t1, errs1 = session(b, "giao1")
    t2 = ctx.new_page()
    t2.on("response", lambda r: SEEN.append((r.request.method, r.url.split("/api/")[1], r.status, "", "giao1")) if "/api/" in r.url else None)
    go(t1, "/returns/")
    go(t2, "/returns/")
    d1 = open_form(t1, "SO-QA9-RACE")
    d2 = open_form(t2, "SO-QA9-RACE")  # tab 2 mở khi tab 1 chưa gửi: số liệu 10 kg
    f2 = t2.locator("[data-qty-facts]").inner_text()
    ok("B1 hai tab cùng thấy 'còn hoàn được 10 kg' trước khi ai gửi", "còn hoàn được 10 kg" in f2, f2)
    d1.get_by_label("Số kg hoàn").fill("6")
    d1.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    t1.wait_for_function("() => !document.querySelector('[role=dialog]')")
    d2.get_by_label("Số kg hoàn").fill("6")
    d2.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    t2.wait_for_function("() => document.querySelector('[role=dialog]') && /vượt số đã giao/.test(document.querySelector('[role=dialog]').innerText)")
    t = t2.get_by_role("dialog").inner_text()
    ok("B2 tab 2 (cũ) gửi 6 kg sau khi tab 1 đã hoàn 6: bị chặn, lỗi gắn ô số kg, số liệu cập nhật 'đã hoàn 6 kg, còn hoàn được 4 kg'", "đã hoàn 6 kg" in t and "còn hoàn được 4 kg" in t, t[:400])
    ok("B2 không lộ mã lỗi/BR trên câu lỗi", not re.search(r"RETURN_|BR-|undefined|NaN", t), t)
    t2.screenshot(path=f"{SHOTS}/impl-real-two-tabs-1280.png")
    d2.get_by_label("Số kg hoàn").fill("4")
    d2.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    t2.wait_for_function("() => !document.querySelector('[role=dialog]')")
    tot = q("select coalesce(sum(qty),0) from inventory_returntostock where delivery_note_id=1")[0][0]
    ok("B3 tab 2 nhập đúng phần còn lại 4 kg được: tổng 10 kg = số đã giao", float(tot) == 10.0, tot)
    d2 = open_form(t2, "SO-QA9-RACE")
    ft = t2.locator("[data-qty-facts]").inner_text()
    ok("B4 hết phần còn lại: 'còn hoàn được 0 kg'", "còn hoàn được 0 kg" in ft, ft)
    d2.get_by_label("Số kg hoàn").fill("0,001")
    d2.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    t2.wait_for_timeout(500)
    ok("B4 thêm 0,001 kg nữa bị chặn", t2.get_by_role("dialog").count() == 1 and float(q("select coalesce(sum(qty),0) from inventory_returntostock where delivery_note_id=1")[0][0]) == 10.0)
    d2.get_by_role("button", name="Huỷ", exact=True).click()
    ok("B5 không console error/warning (2 tab)", errs1 == [], errs1)
    ctx.close()

    # giao1: tạo phiếu cho phiếu RESTOCK/WRITEOFF để duyệt
    ctx, page, errs = session(b, "giao1")
    go(page, "/returns/")
    for hint, kg in (("SO-QA9-RESTOCK", "2,5"), ("SO-QA9-WRITEOFF", "2")):
        dd = open_form(page, hint)
        dd.get_by_label("Số kg hoàn").fill(kg)
        dd.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
        page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    ids = {r[0]: r[1] for r in q("select delivery_note_id, id from inventory_returntostock where delivery_note_id in (4,5)")}
    rid_restock, rid_writeoff = ids[4], ids[5]
    ok("C0 giao1 tạo 2 phiếu cho phiếu RESTOCK và WRITEOFF", len(ids) == 2, ids)
    ctx.close()

    # ---------- C. ql1 duyệt Tái nhập: tồn tăng, sổ có dòng ----------
    ctx, page, errs = session(b, "ql1")
    ok("C1 ql1: không có nút Nhập hàng hoàn (chưa có add_returntostock)", (go(page, "/returns/") or True) and page.get_by_role("button", name="Nhập hàng hoàn").count() == 0)
    s0, l0 = stock(1), len(ledger(1))
    go(page, f"/returns/detail/?id={rid_restock}")
    page.screenshot(path=f"{SHOTS}/impl-real-detail-ql1-1280.png")
    page2 = ctx.new_page()
    page2.on("response", lambda r: SEEN.append((r.request.method, r.url.split("/api/")[1], r.status, "", "ql1")) if "/api/" in r.url else None)
    go(page2, f"/returns/detail/?id={rid_restock}")  # màn cũ cho ca 409
    page.get_by_role("button", name="Tái nhập vào lô").click()
    dd = page.get_by_role("dialog")
    page.screenshot(path=f"{SHOTS}/impl-real-f2n-1280.png")
    dd.get_by_role("button", name="Duyệt", exact=True).dblclick()
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    page.wait_for_timeout(800)
    s1, led = stock(1), ledger(1)
    ok("C2 duyệt Tái nhập 2,5 kg: tồn lô tăng đúng 2,5", abs(s1 - s0 - 2.5) < 1e-6, (s0, s1))
    ok("C2 bấm đúp Duyệt: chỉ 1 dòng RETURN_RESTOCK mới trong sổ (không cộng đôi)", len(led) == l0 + 1 and led[-1][0] == "RETURN_RESTOCK" and float(led[-1][1]) == 2.5, led[-2:])
    ok("C2 giao diện: chip Đã duyệt, hết nút duyệt", "Đã duyệt" in page.inner_text("main") and page.get_by_role("button", name="Tái nhập vào lô").count() == 0)
    # màn cũ (page2 còn nút) duyệt lại -> 409
    page2.get_by_role("button", name="Huỷ hàng, ghi lỗ").click()
    d2 = page2.get_by_role("dialog")
    d2.get_by_role("button", name="Duyệt", exact=True).click()
    page2.wait_for_function("() => document.querySelector('[role=dialog]') && document.querySelector('[role=dialog]').innerText.includes('Tải lại')")
    ok("C3 màn cũ duyệt lần 2: 409 hiện băng xung đột có 'Tải lại', không lộ mã", d2.get_by_role("button", name="Tải lại").count() >= 1 and "STALE" not in d2.inner_text(), d2.inner_text()[:300])
    ok("C3 màn cũ: tồn và sổ không đổi sau 409", abs(stock(1) - s1) < 1e-9 and len(ledger(1)) == len(led))
    ok("C3 phản hồi 409 thật từ BE", any(s[2] == 409 and s[1].startswith(f"inventory/returns/{rid_restock}/approve") for s in SEEN))
    page2.screenshot(path=f"{SHOTS}/impl-real-409-1280.png")
    d2.get_by_role("button", name="Tải lại").first.click()
    page2.wait_for_function("() => !document.querySelector('[role=dialog]')")
    page2.wait_for_timeout(600)
    ok("C3 Tải lại: Đã duyệt, hết nút", page2.get_by_role("button", name="Huỷ hàng, ghi lỗ").count() == 0 and "Đã duyệt" in page2.inner_text("main"))
    ok("C4 ql1 không console error/warning", errs == [], errs)
    ctx.close()

    # ---------- D. loc duyệt Huỷ bỏ: ghi lỗ, tồn không đổi ----------
    ctx, page, errs = session(b, "loc")
    s0, l0 = stock(1), len(ledger(1))
    go(page, f"/returns/detail/?id={rid_writeoff}")
    page.get_by_role("button", name="Huỷ hàng, ghi lỗ").click()
    page.get_by_role("dialog").get_by_role("button", name="Duyệt", exact=True).click()
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    page.wait_for_timeout(800)
    led = ledger(1)
    ok("D1 Huỷ bỏ: tồn lô không đổi", abs(stock(1) - s0) < 1e-9, (s0, stock(1)))
    ok("D1 Huỷ bỏ: sổ có 1 dòng WRITE_OFF ghi lỗ 2 kg", len(led) == l0 + 1 and led[-1][0] == "WRITE_OFF" and "2" in led[-1][2], led[-1:])
    al = q("select action, changes, note from accounts_auditlog where action='approve_returntostock' order by id")
    ok("D2 AuditLog approve_returntostock có cho cả 2 lần duyệt, chỉ ghi quyết định", len(al) == 2 and all(set(json.loads(a[1])) <= {"decision"} for a in al), al)
    ok("D2 AuditLog không có ghi chú tự do/SĐT/tên khách/tiền", not any(re.search(r"khách|0900000|123457|amount|rate", json.dumps(a, ensure_ascii=False)) for a in al), al)
    go(page, "/returns/")
    body = page.inner_text("main")
    ok("D3 loc: danh sách có Tái nhập, Huỷ hàng, ghi lỗ, Chờ duyệt, Đã duyệt; kg dạng '2,5 kg'", all(x in body for x in ("Tái nhập", "Huỷ hàng, ghi lỗ", "Chờ duyệt", "Đã duyệt", "2,5 kg")), body[:500])
    page.screenshot(path=f"{SHOTS}/impl-real-list-loc-1280.png")
    go(page, f"/returns/detail/?id={rid_writeoff}")
    # AI tắt: không có request /actions
    ai_all = sorted({(s[1], s[2], s[3][:80]) for s in SEEN if s[4] == "loc" and s[1].startswith("ai/")})
    print("INFO các lệnh gọi ai/* của loc:", ai_all)
    ok("D4 AI tắt: có hỏi ai/status/ (cổng chạy) nhưng KHÔNG gọi actions/chat/proposals", any(a[0].startswith("ai/status") for a in ai_all) and not any(re.search(r"actions|chat|proposal", a[0]) for a in ai_all), ai_all)
    ok("D5 loc không console error/warning", errs == [], errs)
    ctx.close()

    # ---------- E. giao2: phạm vi hàng ----------
    ctx, page, errs = session(b, "giao2")
    go(page, "/returns/")
    ok("E1 giao2 (chưa có phiếu hoàn của mình): danh sách rỗng, không lộ phiếu giao1", rows(page) == [] and "RT-" not in page.inner_text("main"), rows(page))
    go(page, f"/returns/detail/?id={rid_restock}")
    t = page.inner_text("main")
    ok("E2 giao2 mở phiếu của giao1: 'Không tìm thấy', không lộ kg/lô/ghi chú", page.get_by_role("heading", name="Không tìm thấy").count() >= 1 and not re.search(r"CA01|Cá thu|kg|khách", t), t[:200])
    ok("E2 phản hồi thật là 404", any(s[2] == 404 and s[1].startswith(f"inventory/returns/{rid_restock}") for s in SEEN if s[4] == "giao2"))
    go(page, "/returns/")
    dd = open_form(page, "SO-QA9-OTHER")
    opts = dd.get_by_label("Phiếu giao").locator("option").all_inner_texts()
    ok("E3 giao2 chỉ thấy phiếu giao của mình trong F2m (không có SO-QA9-RACE/FAIL/RESTOCK)", all(not re.search(r"RACE|FAIL|RESTOCK|WRITEOFF", o) for o in opts) and any("OTHER" in o for o in opts), opts)
    ok("E4 giao2 không console error/warning", errs == [], errs)
    ctx.close()

    # ---------- F. kho1 và cs1 ----------
    ctx, page, errs = session(b, "kho1")
    go(page, "/returns/")
    ok("F1 kho1 thấy mọi phiếu (>=4), có Nhập hàng hoàn", len(rows(page)) >= 4 and page.get_by_role("button", name="Nhập hàng hoàn").count() == 1, rows(page))
    go(page, f"/returns/detail/?id={rid_restock}")
    ok("F2 kho1: không nút duyệt ở phiếu", page.get_by_role("button", name="Tái nhập vào lô").count() == 0)
    ctx.close()
    ctx, page, errs = session(b, "cs1")
    go(page, "/returns/")
    ok("F3 cs1: 'Không có quyền', không lộ phiếu", page.get_by_role("heading", name="Không có quyền").count() >= 1 and "RT-" not in page.inner_text("main"))
    cs_calls = [(s[1], s[2]) for s in SEEN if s[4] == "cs1" and s[1].startswith("inventory/returns")]
    ok("F3 cs1: FE không gọi API hàng hoàn, hoặc nếu gọi thì nhận 403 (không có 200)", all(c[1] == 403 for c in cs_calls), cs_calls)
    ctx.close()

    # ---------- G. 360px quản lý, danh sách + chi tiết ----------
    ctx, page, errs = session(b, "ql1", 360, 780, touch=True)
    go(page, "/returns/")
    ok("G1 ql1 360 danh sách không cuộn ngang trang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/impl-real-list-ql1-360.png")
    go(page, f"/returns/detail/?id={rid_writeoff}")
    ok("G2 ql1 360 chi tiết không cuộn ngang trang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/impl-real-detail-ql1-360.png")
    ctx.close()

    # ---------- H. Rà toàn bộ phản hồi API đã thấy: giá vốn, dữ liệu khách ----------
    cost = [(s[1], s[4]) for s in SEEN if s[4] != "loc" and re.search(r"123457|landed_unit_cost|purchase_rate|unit_cost", s[3])]
    ok("H1 mọi phản hồi API mà các vai ql1/kho1/giao1/giao2/cs1 nhận khi dùng màn Lô 9: không có giá vốn (123457/landed/purchase_rate/unit_cost)", cost == [], cost[:5])
    pii = [(s[1], s[4]) for s in SEEN if s[1].startswith(("inventory/returns", "guidance/return")) and re.search(r"Khách SO-QA9|0900000\d\d\d|1 Cảng", s[3])]
    ok("H2 phản hồi hàng hoàn/dòng thời gian: không tên/SĐT/địa chỉ khách", pii == [], pii[:5])
    pii2 = [(s[1], s[4]) for s in SEEN if s[1].startswith("delivery/notes") and s[4] in ("giao1", "giao2") and re.search(r"Khách SO-QA9|0900000\d\d\d", s[3])]
    print("INFO phản hồi delivery/notes cho người giao (cần SĐT/địa chỉ để giao theo thiết kế):", len(pii2), "phản hồi chứa khoá nhận dạng")
    b.close()

bad = [r for r in R if not r[1]]
print(f"\nTỔNG {len(R)} ca, {len(R) - len(bad)} đạt, {len(bad)} lỗi")
sys.exit(1 if bad else 0)
