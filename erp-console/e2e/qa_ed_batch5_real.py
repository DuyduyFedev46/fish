# QA độc lập, ERP theo design, Lô 5 FE (Gọi xác nhận) trên BACKEND THẬT: Django + SQLite tạm, ERP build NEXT_PUBLIC_USE_MOCK=0.
# Dữ liệu 100% giả (seed_demo + đơn "Khách Thử ..."). Không bao giờ trỏ vào DB thật.
# Biến: QA_ERP (vd http://127.0.0.1:3202), QA_API (http://127.0.0.1:8120), QA_DB (đường dẫn SQLite tạm), QA_SHOTS,
#       QA_JOB (lệnh chạy job process_confirmation_deadlines), QA_IDS (JSON: mã phiếu cho từng ca; xem hàm main).
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

ERP = os.environ.get("QA_ERP", "http://127.0.0.1:3202")
API = os.environ.get("QA_API", "http://127.0.0.1:8120")
DB = os.environ["QA_DB"]
SHOTS = os.environ.get("QA_SHOTS", "/tmp")
JOB = os.environ["QA_JOB"]
IDS = json.loads(os.environ.get("QA_IDS", "{}"))
PII = ["0900000555", "Khách Thử K", "Số 9 Đường Thử", "Hải Phòng", "0900000700", "0900000701", "0900000801", "0911222333", "Người Nhận Giả", "12 Đường Giả"]
results = []
CONSOLE = []
EXTERNAL = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, ("" if cond else f"<{str(extra)[:300]}>"), flush=True)


_TOK = {}


def token(u):
    if u in _TOK:
        return _TOK[u]
    _TOK[u] = _token(u)
    return _TOK[u]


def _token(u):
    r = urllib.request.Request(API + "/api/auth/token/", data=json.dumps({"username": u, "password": "demo1234"}).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r))["token"]


def call(user, method, path, body=None):
    h = {"Content-Type": "application/json"}
    if user:
        h["Authorization"] = "Token " + token(user)
    r = urllib.request.Request(API + path, method=method, headers=h, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r) as x:
            return x.status, json.load(x)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def sql(q, *a):
    con = sqlite3.connect(DB)
    try:
        return con.execute(q, a).fetchall()
    finally:
        con.close()


def task(pk):
    r = sql("select state, attempts, escalation_reason from delivery_confirmationtask where id=?", pk)[0]
    return {"state": r[0], "attempts": r[1], "reason": r[2]}


def audit_text(since_id):
    rows = sql("select action, changes, note from accounts_auditlog where id>?", since_id)
    return rows


def last_audit_id():
    return sql("select coalesce(max(id),0) from accounts_auditlog")[0][0]


def new_page(browser, user, w=1280, h=860, tz=None):
    kw = dict(viewport={"width": w, "height": h}, reduced_motion="reduce")
    if tz:
        kw["timezone_id"] = tz
    ctx = browser.new_context(**kw)
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: (CONSOLE.append((user, m.type, m.text)), errs.append(m.text) if m.type in ("error", "warning") else None))
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("request", lambda r: EXTERNAL.append(r.url) if not r.url.startswith(ERP) and not r.url.startswith(API) and not r.url.startswith(("data:", "blob:")) else None)
    page.goto(ERP + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15_000)
    page.wait_for_load_state("networkidle")
    return ctx, page, errs


def detail(page, note_id, heading=None):
    page.goto(ERP + f"/confirmation/detail/?id={note_id}")
    page.wait_for_load_state("networkidle")
    if heading:
        page.get_by_role("heading", name=heading).wait_for(timeout=15_000)
    page.wait_for_timeout(500)


def dialog(page):
    return page.get_by_role("dialog")


def more(page, item):
    page.get_by_role("button", name=re.compile("Thao tác khác|Thêm|Khác|Hành động", re.I)).first.click()
    page.get_by_role("menuitem", name=re.compile(item)).click()


def storage(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), document.cookie])")


def pii_in(t):
    return [p for p in PII if p in t]


def main():
    since = last_audit_id()
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)

        # ---------------- API: quyền + phạm vi dữ liệu cá nhân ----------------
        st, q = call("cs2", "GET", "/api/confirmation/queue/?state=REFUND_CALL")
        rows = q["results"]
        out = [r for r in rows if r["order_code"] == IDS["OUT_CODE"]]
        ok("API cs2: hàng chờ có dòng ngoài phạm vi (REFUND_CALL)", st == 200 and len(out) == 1, [r["order_code"] for r in rows])
        if out:
            o = out[0]
            ok("API cs2: dòng ngoài phạm vi chỉ có phone_masked, tên / SĐT / địa chỉ rỗng", not o["customer_name"] and not o["phone"] and not o["address"] and o["phone_masked"].startswith("09xx"), {k: o[k] for k in ("customer_name", "phone", "address", "phone_masked")})
        ok("API cs2: không có khoá giá vốn / lãi trong JSON hàng chờ", not re.search(r"purchase_rate|landed|unit_cost|cost|profit|margin|giá vốn", json.dumps(q)), "")
        for u in ("kho1", "giao1"):
            ok(f"API {u}: GET queue -> 403", call(u, "GET", "/api/confirmation/queue/")[0] == 403)
            ok(f"API {u}: POST decide -> 403", call(u, "POST", f"/api/confirmation/queue/{IDS['E5']}/decide/", {"decision": "CANCEL", "reason": "x"})[0] == 403)
        ok("API chưa đăng nhập: GET queue -> 401", call(None, "GET", "/api/confirmation/queue/")[0] == 401)
        s, body = call("cs2", "POST", f"/api/confirmation/queue/{IDS['E5']}/decide/", {"decision": "CANCEL", "reason": "thử"})
        ok("AC5 API cs2: POST decide -> 403 (CSKH không có quyền Quyết định)", s == 403, (s, body))
        ok("AC5 sau 403 đơn vẫn Cần quyết định, không đổi", task(IDS["E5"])["state"] == "ESCALATED")
        s, body = call("cs2", "GET", f"/api/confirmation/queue/{IDS['OUT_NOTE']}/")
        ok("API cs2: chi tiết đơn ngoài phạm vi -> 404, không lộ dữ liệu", s == 404 and not pii_in(json.dumps(body)), (s, body))
        s, body = call("cs2", "POST", f"/api/confirmation/queue/{IDS['P3']}/calls/", {"result": "CALLBACK", "callback_at": "2020-01-01T00:00:00+07:00"})
        ok("API: hẹn gọi lại quá khứ -> 400, không lưu", s == 400 and task(IDS["P3"])["state"] == "PENDING", (s, body))
        s, body = call("cs2", "POST", f"/api/confirmation/queue/{IDS['P3']}/calls/", {"result": "UNREACHABLE", "note": "gọi 0912345678"})
        ok("API: ghi chú có SĐT -> 400 (BR-GH-19), không lưu", s == 400 and task(IDS["P3"])["attempts"] == 0, (s, body))
        s, body = call("cs2", "POST", f"/api/confirmation/queue/{IDS['P3']}/calls/", {"result": "KHONG_HOP_LE"})
        ok("API: kết quả lạ -> 400", s == 400, (s, body))

        # ---------------- UI cs2: hàng chờ + phạm vi ----------------
        ctx, page, errs = new_page(b, "cs2")
        page.goto(ERP + "/confirmation/")
        page.wait_for_load_state("networkidle")
        page.get_by_role("tab", name=re.compile("^Gọi báo hoàn tiền")).click()
        page.wait_for_timeout(800)
        html = page.content()
        row = page.locator("table.lt tbody tr", has_text=IDS["OUT_CODE"])
        ok("UI cs2 (BE thật): dòng ngoài phạm vi hiện số che 09xx xxx 555", row.count() == 1 and "09xx xxx 555" in row.inner_text(), row.inner_text() if row.count() else "không thấy dòng")
        ok("UI cs2 (BE thật): toàn DOM không chứa tên / SĐT đủ / địa chỉ đơn ngoài phạm vi", not pii_in(html), pii_in(html))
        page.screenshot(path=os.path.join(SHOTS, "qa5-real-queue-refund-cs2-1280.png"))
        page.get_by_role("tab", name=re.compile("^Tất cả")).click()
        page.wait_for_timeout(800)
        ok("UI cs2 (BE thật): tab Tất cả có nhiều dòng, chip đủ nhãn chuẩn", page.locator("table.lt tbody tr").count() >= 8 and {"Chờ gọi", "Hẹn gọi lại", "Cần quyết định", "Gọi báo hoàn tiền"} <= set(c.strip() for c in page.locator("table.lt tbody tr .stat-chip").all_inner_texts()))
        page.screenshot(path=os.path.join(SHOTS, "qa5-real-queue-all-cs2-1280.png"))
        detail(page, IDS["OUT_NOTE"])
        ok("UI cs2 (BE thật): mở thẳng đơn ngoài phạm vi -> 'Không tìm thấy', DOM sạch", page.get_by_text("Không tìm thấy", exact=False).first.is_visible() and not pii_in(page.content()))
        ok("UI cs2 (BE thật): không lỗi console", not [e for e in errs if "404" not in e and "Failed to load resource" not in e], errs[:3])
        ctx.close()

        # ---------------- ghi cuộc gọi: bấm đúp = 1 lần; Dòng thời gian có dòng mới; AuditLog không có SĐT ----------------
        ctx, page, errs = new_page(b, "cs2", tz="America/New_York")
        detail(page, IDS["P1"], IDS["P1_CODE"])
        tl0 = page.locator("[data-timeline-row]").count()
        g0 = call("cs2", "GET", f"/api/guidance/delivery/{IDS['P1']}/")[1]
        n_g0 = len(g0.get("timeline", [])) if isinstance(g0, dict) else -1
        page.get_by_role("button", name="Ghi kết quả gọi").click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text="Không nghe máy").first.click()
        d.get_by_label("Ghi chú", exact=False).fill("Chuông reo không ai bắt máy")
        d.get_by_role("button", name=re.compile("^Lưu kết quả")).dblclick()
        d.wait_for(state="detached", timeout=15_000)
        page.wait_for_timeout(1200)
        n_calls = sql("select count(*) from delivery_customercall where note_id=?", IDS["P1"])[0][0]
        ok("AC2 (BE thật): bấm đúp 'Lưu kết quả' chỉ ghi 1 cuộc gọi trong DB", n_calls == 1 and task(IDS["P1"])["attempts"] == 1, (n_calls, task(IDS["P1"])))
        tl1 = page.locator("[data-timeline-row]").count()
        ok("AC2 (BE thật): Dòng thời gian có dòng mới sau khi lưu (không cần nạp lại tay)", tl1 == tl0 + 1, f"{tl0}->{tl1}")
        g1 = call("cs2", "GET", f"/api/guidance/delivery/{IDS['P1']}/")[1]
        n_g1 = len(g1.get("timeline", [])) if isinstance(g1, dict) else -1
        ok("AC2 (BE thật): API Dòng thời gian của phiếu có thêm dòng sau khi ghi cuộc gọi", n_g1 == n_g0 + 1, f"{n_g0}->{n_g1}: {json.dumps(g1.get('timeline', [])[:3], ensure_ascii=False)[:300]}")
        page.screenshot(path=os.path.join(SHOTS, "qa5-real-detail-after-call-cs2-1280.png"))
        # nạp lại: dòng thời gian vẫn có
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)
        tl2 = page.locator("[data-timeline-row]").count()
        ok("AC2 (BE thật): nạp lại trang, Dòng thời gian vẫn có dòng đó", tl2 >= tl1, f"{tl1}->{tl2}")
        ok("AC2 (BE thật): không lỗi console", not [e for e in errs if "Failed to load resource" not in e], errs[:3])
        ctx.close()

        # ---------------- Đã xác nhận ----------------
        ctx, page, errs = new_page(b, "cs2")
        detail(page, IDS["P2"], IDS["P2_CODE"])
        page.get_by_role("button", name="Ghi kết quả gọi").click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text="Đã xác nhận").first.click()
        d.get_by_role("button", name=re.compile("^Lưu kết quả")).click()
        d.wait_for(state="detached", timeout=15_000)
        page.wait_for_timeout(1000)
        st_note = sql("select status from delivery_deliverynote where id=?", IDS["P2"])[0][0]
        ok("AC2 (BE thật): 'Đã xác nhận' -> phiếu sang Soạn hàng (PREPARING)", st_note == "PREPARING", st_note)
        ok("AC2 (BE thật): trang hiện 'Soạn hàng' sau lưu", "Soạn hàng" in page.inner_text("main"))
        # màn cũ: cùng đơn, mở màn ghi gọi lần nữa từ API cũ -> BE trả 409/400 hiểu được
        s, body = call("cs2", "POST", f"/api/confirmation/queue/{IDS['P2']}/calls/", {"result": "CONFIRMED"})
        ok("Màn cũ (BE thật): ghi 'Đã xác nhận' lần hai trên phiếu đã Soạn hàng -> 4xx (không tạo thêm cuộc gọi)", s in (400, 409) and sql("select count(*) from delivery_customercall where note_id=?", IDS["P2"])[0][0] == 1, (s, body))
        # Huỷ xác nhận đơn
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)
        more(page, "Huỷ xác nhận đơn")
        d = dialog(page)
        d.wait_for()
        d.get_by_role("button", name=re.compile("Huỷ xác nhận")).last.click()
        ok("Huỷ xác nhận thiếu lý do: báo lỗi, hộp còn mở (BE thật)", dialog(page).is_visible() and re.search(r"lý do", d.inner_text(), re.I) is not None, d.inner_text()[-150:])
        d.get_by_label(re.compile("Lý do")).fill("Khách đổi ý, chưa soạn hàng")
        d.get_by_role("button", name=re.compile("Huỷ xác nhận")).last.click()
        d.wait_for(state="detached", timeout=15_000)
        page.wait_for_timeout(1000)
        ok("Huỷ xác nhận (BE thật): phiếu về CONFIRMING", sql("select status from delivery_deliverynote where id=?", IDS["P2"])[0][0] == "CONFIRMING")
        ctx.close()

        # ---------------- Hẹn gọi lại: giờ theo VN dù máy ở New York ----------------
        ctx, page, errs = new_page(b, "cs2", tz="America/New_York")
        detail(page, IDS["P3"], IDS["P3_CODE"])
        more(page, "Hẹn gọi lại")
        d = dialog(page)
        d.wait_for()
        # giờ Việt Nam hiện tại + 3 giờ
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        target = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")) + timedelta(hours=3)
        d.get_by_label("Hẹn gọi lại lúc").fill(target.strftime("%Y-%m-%dT%H:%M"))
        d.get_by_role("button", name="Lưu hẹn gọi lại").click()
        d.wait_for(state="detached", timeout=15_000)
        page.wait_for_timeout(1000)
        s, body = call("cs2", "GET", f"/api/confirmation/queue/{IDS['P3']}/")
        cb = body.get("callback_at") if isinstance(body, dict) else None
        ok("AC3 (BE thật, máy ở New York): BE nhận đúng thời điểm hẹn (UTC) = giờ VN đã chọn", cb and abs((datetime.fromisoformat(cb.replace("Z", "+00:00")) - target.astimezone(ZoneInfo("UTC"))).total_seconds()) <= 120, cb)
        ok("AC3 (BE thật): màn hiện 'Hạn gọi' đúng giờ VN đã chọn", target.strftime("%d/%m/%Y %H:%M") in page.inner_text("main"), page.inner_text("main")[:400].replace("\n", "|"))
        ctx.close()

        # ---------------- WANT_CHANGE + đổi người nhận ----------------
        ctx, page, errs = new_page(b, "cs2")
        detail(page, IDS["P4"], IDS["P4_CODE"])
        page.get_by_role("button", name="Ghi kết quả gọi").click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text="Khách muốn đổi món").first.click()
        d.get_by_role("button", name=re.compile("^Lưu kết quả")).click()
        d.wait_for(state="detached", timeout=15_000)
        page.wait_for_timeout(800)
        t4 = task(IDS["P4"])
        ok("AC2 (BE thật): 'Khách muốn đổi món' -> việc chuyển Cần quyết định, lý do WANT_CHANGE", t4["state"] == "ESCALATED" and t4["reason"] == "WANT_CHANGE", t4)
        ctx.close()
        ctx, page, errs = new_page(b, "cs2")
        detail(page, IDS["P5"], IDS["P5_CODE"])
        more(page, "Đổi người nhận")
        d = dialog(page)
        d.wait_for()
        d.get_by_label("Tên người nhận").fill("Người Nhận Giả")
        d.get_by_label("Số điện thoại người nhận").fill("0911222333")
        d.get_by_label(re.compile("Địa chỉ giao")).fill("12 Đường Giả, Quận Giả")
        d.get_by_role("button", name="Lưu thay đổi").click()
        d.wait_for(state="detached", timeout=15_000)
        page.wait_for_timeout(1000)
        main = page.inner_text("main")
        ok("F2j (BE thật): lưu đổi người nhận -> màn hiện người nhận / số / địa chỉ mới", "Người Nhận Giả" in main and "0911222333" in main and "12 Đường Giả" in main, main[:400])
        ok("F2j (BE thật): storage / URL không chứa dữ liệu khách", not pii_in(storage(page)) and not pii_in(page.url), storage(page)[:200])
        ctx.close()

        # ---------------- mất mạng khi lưu ----------------
        ctx, page, errs = new_page(b, "cs2")
        detail(page, IDS["P6"], IDS["P6_CODE"])
        page.get_by_role("button", name="Ghi kết quả gọi").click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text="Không nghe máy").first.click()
        ctx.set_offline(True)
        d.get_by_role("button", name=re.compile("^Lưu kết quả")).click()
        page.wait_for_timeout(1500)
        ok("Mất mạng khi lưu: hộp còn mở, có thông báo lỗi, không ghi gì", dialog(page).is_visible() and sql("select count(*) from delivery_customercall where note_id=?", IDS["P6"])[0][0] == 0 and re.search(r"mạng|thử lại|không gửi", dialog(page).inner_text(), re.I) is not None, dialog(page).inner_text()[-200:])
        page.screenshot(path=os.path.join(SHOTS, "qa5-real-offline-cs2-1280.png"))
        ctx.set_offline(False)
        d.get_by_role("button", name=re.compile("Lưu kết quả|Thử lại")).last.click()
        d.wait_for(state="detached", timeout=15_000)
        page.wait_for_timeout(800)
        ok("Mất mạng rồi có mạng, bấm lại: đúng 1 cuộc gọi trong DB", sql("select count(*) from delivery_customercall where note_id=?", IDS["P6"])[0][0] == 1)
        ctx.close()

        # ---------------- Quyết định: ql1 / loc ----------------
        ctx, page, errs = new_page(b, "cs2")
        detail(page, IDS["E5"], IDS["E5_CODE"])
        btns = [x.strip() for x in page.locator("main button, main a.btn").all_inner_texts()]
        ok("AC5 (BE thật): cs2 mở việc Cần quyết định -> không có nút 'Quyết định'", "Quyết định" not in btns, btns)
        ctx.close()

        ctx, page, errs = new_page(b, "ql1")
        detail(page, IDS["E2"], IDS["E2_CODE"])
        page.get_by_role("button", name="Quyết định", exact=True).click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text="Gia hạn thêm").first.click()
        d.get_by_label(re.compile("^Lý do")).fill("Khách hẹn gọi chiều")
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        d.get_by_label("Gia hạn tới lúc").fill((datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"))
        d.get_by_role("button", name=re.compile("Lưu quyết định")).dblclick()
        d.wait_for(state="detached", timeout=15_000)
        page.wait_for_timeout(1000)
        ok("AC4 (BE thật): Gia hạn thêm -> việc sang Hẹn gọi lại, chỉ 1 lần (bấm đúp)", task(IDS["E2"])["state"] == "CALLBACK", task(IDS["E2"]))
        # gia hạn quá 24 giờ -> chặn ở BE
        s, body = call("ql1", "POST", f"/api/confirmation/queue/{IDS['E1']}/decide/", {"decision": "EXTEND", "reason": "thử", "until": (datetime.now(ZoneInfo("UTC")) + timedelta(hours=26)).isoformat()})
        ok("AC4 (BE thật): gia hạn > 24 giờ -> 400, việc không đổi", s == 400 and task(IDS["E1"])["state"] == "ESCALATED", (s, body))
        # Huỷ đơn
        detail(page, IDS["E3"], IDS["E3_CODE"])
        page.get_by_role("button", name="Quyết định", exact=True).click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text="Huỷ đơn").first.click()
        sel = d.locator("select").first
        opts = [o for o in sel.locator("option").all_inner_texts() if o.strip() and not o.strip().startswith(("Chọn", "—"))]
        print("   lý do huỷ (select):", opts)
        sel.select_option(label=opts[0])
        d.get_by_role("button", name=re.compile("^Huỷ đơn$")).click()
        page.wait_for_timeout(400)
        ok("AC4 (BE thật): bấm 'Huỷ đơn' lần đầu chỉ hỏi lại, chưa huỷ", task(IDS["E3"])["state"] == "ESCALATED" and d.get_by_role("button", name="Xác nhận huỷ đơn").count() == 1)
        d.get_by_role("button", name="Xác nhận huỷ đơn").click()
        page.wait_for_timeout(2500)
        t3 = task(IDS["E3"])
        ok("AC4 (BE thật): xác nhận huỷ -> việc kết thúc (DONE; REFUND_CALL chỉ do job tự huỷ), phiếu bị huỷ", t3["state"] == "DONE" and sql("select status from delivery_deliverynote where id=?", IDS["E3"])[0][0] == "CANCELLED", t3)
        ok("AC4 (BE thật): sau huỷ chuyển sang màn Đơn hàng để lập phiếu hoàn (URL có ?order & open=refund)", "/orders" in page.url and "open=refund" in page.url, page.url)
        ok("AC4 (BE thật): URL sau huỷ không chứa dữ liệu khách", not pii_in(page.url))
        page.screenshot(path=os.path.join(SHOTS, "qa5-real-after-cancel-ql1-1280.png"))
        ctx.close()

        ctx, page, errs = new_page(b, "loc")
        detail(page, IDS["E4"], IDS["E4_CODE"])
        page.get_by_role("button", name="Quyết định", exact=True).click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text="Giao không xác nhận").first.click()
        d.get_by_label(re.compile("^Lý do")).fill("Khách quen, giao luôn")
        d.get_by_role("button", name=re.compile("Lưu quyết định")).click()
        d.wait_for(state="detached", timeout=15_000)
        page.wait_for_timeout(800)
        ok("AC4 (BE thật, loc): Giao không xác nhận -> phiếu sang Soạn hàng", sql("select status from delivery_deliverynote where id=?", IDS["E4"])[0][0] == "PREPARING")
        ctx.close()

        # ---------------- 409 STALE_STATE thật: job tự huỷ chạy trong lúc ql1 mở hộp ----------------
        ctx, page, errs = new_page(b, "ql1")
        detail(page, IDS["STALE_NOTE"], IDS["STALE_CODE"])
        page.get_by_role("button", name="Quyết định", exact=True).click()
        d = dialog(page)
        d.wait_for()
        d.locator("label", has_text="Giao không xác nhận").first.click()
        d.get_by_label(re.compile("^Lý do")).fill("Giao luôn")
        out = subprocess.run(JOB, shell=True, capture_output=True, text=True).stdout
        ok("409 STALE (BE thật): job tự huỷ đã huỷ đơn trong lúc hộp mở", re.search(r"tự huỷ [1-9]", out) is not None, out[-200:])
        d.get_by_role("button", name=re.compile("Lưu quyết định")).click()
        d.get_by_role("button", name="Tải lại").wait_for(timeout=15_000)
        ok("409 STALE (BE thật): hộp giữ nguyên, có alert câu của BE, ô nhập khoá", d.get_by_role("alert").count() >= 1 and d.locator("input:not([disabled]):not([type=hidden]), textarea:not([disabled])").count() == 0, d.inner_text()[-250:])
        ok("409 STALE (BE thật): phiếu vẫn CANCELLED, không ai giao", sql("select status from delivery_deliverynote where id=?", IDS["STALE_NOTE"])[0][0] == "CANCELLED")
        page.screenshot(path=os.path.join(SHOTS, "qa5-real-409-stale-ql1-1280.png"))
        d.get_by_role("button", name="Tải lại").click()
        page.wait_for_timeout(1200)
        ok("409 STALE (BE thật): 'Tải lại' đóng hộp, trang hiện trạng thái mới", dialog(page).count() == 0)
        ctx.close()

        # ---------------- giữ phiếu: claim bởi người khác (cs1 giữ, cs2 bấm) ----------------
        ctx, page, errs = new_page(b, "cs2")
        detail(page, IDS["CLAIM_NOTE"], IDS["CLAIM_CODE"])
        s, body = call("cs1", "POST", f"/api/confirmation/queue/{IDS['CLAIM_NOTE']}/claim/", {})
        page.get_by_role("button", name="Ghi kết quả gọi").click()
        page.wait_for_timeout(1200)
        ok("409 CLAIMED (BE thật): cs1 đang giữ -> cs2 không mở được hộp, thấy câu của BE (tên người giữ)", dialog(page).count() == 0 and re.search(r"đang được .* xử lý", page.inner_text("main")) is not None, page.inner_text("main")[:300])
        page.screenshot(path=os.path.join(SHOTS, "qa5-real-409-claimed-cs2-1280.png"))
        ctx.close()

        # ---------------- AuditLog + rò dữ liệu ----------------
        rows = audit_text(since)
        blob = json.dumps(rows, ensure_ascii=False)
        ok("AC6 (BE thật): AuditLog có bản ghi cho các hành động (gọi / xác nhận / đổi người nhận / quyết định)", len(rows) >= 6, len(rows))
        ok("AC6 (BE thật): AuditLog (changes, note) không chứa SĐT / tên / địa chỉ khách", not pii_in(blob) and not re.search(r"\b0\d{9}\b", blob), re.findall(r"\b0\d{9}\b", blob)[:3])
        ok("AuditLog: không chứa khoá giá vốn", not re.search(r"purchase_rate|landed|unit_cost|giá vốn", blob), "")
        ok("AuditLog: không tính ngược được giá vốn (không có tiền ÷ kg cùng lúc trong một bản ghi)", not any(("amount" in (r[1] or "") and "kg" in (r[1] or "") and "qty" in (r[1] or "")) for r in rows), [r[1][:120] for r in rows][:2])
        actions = sorted(set(r[0] for r in rows))
        print("   audit actions:", actions)
        leaked = [(u, t, x[:90]) for (u, t, x) in CONSOLE if pii_in(x) or re.search(r"\b0\d{9}\b", x)]
        ok("Console (mọi loại, mọi vai, BE thật): không in dữ liệu khách", not leaked, leaked[:3])
        ok("Không request tới bên thứ ba (BE thật)", not EXTERNAL, sorted(set(EXTERNAL))[:3])

        # ---------------- vai khác trên UI ----------------
        for u in ("kho1", "giao1"):
            ctx, page, errs = new_page(b, u)
            ok(f"UI {u} (BE thật): menu không có 'Gọi xác nhận'", page.locator(".nav a", has_text="Gọi xác nhận").count() == 0)
            page.goto(ERP + "/confirmation/")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            ok(f"UI {u} (BE thật): vào thẳng /confirmation/ -> 'Không có quyền', DOM sạch", page.get_by_text("không có quyền", exact=False).first.is_visible() and not pii_in(page.content()) and "SO261002" not in page.content())
            ctx.close()
        b.close()
    fails = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(fails)}/{len(results)} đạt")
    for n, _, e in fails:
        print("FAIL:", n, str(e)[:300])
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
