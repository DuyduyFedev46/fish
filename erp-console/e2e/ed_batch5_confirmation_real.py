# Smoke ERP Gọi xác nhận (ED-15..17, Lô 5) trên BE THẬT với dữ liệu giả của `manage.py seed_qa`: 5 việc gọi đủ trạng thái
# (QA-SO-04/16 Chờ gọi, QA-SO-15 Hẹn gọi lại, QA-SO-14 Cần quyết định, QA-SO-11 Gọi báo hoàn tiền).
#   Chuẩn bị và biến môi trường: xem e2e_seed_qa.py (BASE = ERP build thật, API, SEED_QA_IDS, QA_PASSWORD).
# Phần tích hợp UI <-> BE thật của `qa_ed_batch5_real` (kịch bản QA một lần, cần 6 việc Chờ gọi, 5 việc Cần quyết định, việc ngoài phạm vi của
# cs2 và job tự huỷ: chờ mở rộng seed_qa). Ca ghi (gọi, quyết định) tiêu thụ việc: seed lại DB trước mỗi lần chạy.
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from playwright.sync_api import expect, sync_playwright

from e2e_seed_qa import API, BASE, ids, password
from e2e_support import finish

R = []
PHONE_RE = re.compile(r"(?<!\d)0\d{9}(?!\d)")
expect.set_options(timeout=15_000)
_TOK = {}


def ok(n, c, e=""):
    R.append((n, bool(c), e))
    print("PASS" if c else "FAIL", n, "" if c else str(e)[:300], flush=True)


def call(user, method, path, body=None):
    if user and user not in _TOK:
        req = urllib.request.Request(API + "/api/auth/token/", data=json.dumps({"username": user, "password": password()}).encode(), headers={"Content-Type": "application/json"})
        _TOK[user] = json.load(urllib.request.urlopen(req))["token"]
    h = {"Content-Type": "application/json", **({"Authorization": "Token " + _TOK[user]} if user else {})}
    req = urllib.request.Request(API + path, method=method, headers=h, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as x:
            return x.status, json.load(x)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def session(browser, user):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errs.append(m.text))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(password())
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    return ctx, page, errs


def detail(page, note_id):
    page.goto(f"{BASE}/confirmation/detail/?id={note_id}")
    page.wait_for_load_state("networkidle")
    expect(page.locator("main h2").first).to_be_visible()


M = ids()
NOTE = {code.replace("QA-GH", "QA-SO"): v["id"] for code, v in M["delivery_notes"].items()}  # mã đơn -> id phiếu giao (việc gọi đi theo id phiếu)
PENDING, CALLBACK, ESCALATED, REFUND_CALL = NOTE["QA-SO-16"], NOTE["QA-SO-15"], NOTE["QA-SO-14"], NOTE["QA-SO-11"]


def task(note_id):
    s, b = call("qa_manager", "GET", f"/api/confirmation/queue/{note_id}/")
    return b if s == 200 else {}


with sync_playwright() as p:
    b = p.chromium.launch()
    # ---- API: quyền, đầu vào xấu, không rò
    n_rows, q = 0, {}
    for state in ("PENDING", "CALLBACK", "ESCALATED", "REFUND_CALL"):  # mặc định hàng chờ chỉ trả việc đến giờ gọi: gom theo từng trạng thái
        s, one = call("qa_cs1", "GET", f"/api/confirmation/queue/?state={state}")
        n_rows += len(one["results"]) if s == 200 else -100
        q[state] = one
    ok("API qa_cs1: hàng chờ 200, đủ 5 việc seed_qa (2 Chờ gọi, 1 Hẹn gọi lại, 1 Cần quyết định, 1 Gọi báo hoàn tiền)", n_rows == 5, n_rows)
    ok("API: không khoá giá vốn / lãi trong hàng chờ", not re.search(r"purchase_rate|landed|unit_cost|profit|margin|giá vốn", json.dumps(q)))
    for u in ("qa_warehouse", "qa_courier1"):
        ok(f"API {u}: GET queue -> 403", call(u, "GET", "/api/confirmation/queue/")[0] == 403)
        ok(f"API {u}: POST decide -> 403", call(u, "POST", f"/api/confirmation/queue/{ESCALATED}/decide/", {"decision": "CANCEL", "reason": "x"})[0] == 403)
    ok("API chưa đăng nhập: GET queue -> 401", call(None, "GET", "/api/confirmation/queue/")[0] == 401)
    s, body = call("qa_cs1", "POST", f"/api/confirmation/queue/{ESCALATED}/decide/", {"decision": "CANCEL", "reason": "thử"})
    ok("AC5 API qa_cs1: POST decide -> 403 (CSKH không có quyền Quyết định), việc vẫn Cần quyết định", s == 403 and task(ESCALATED).get("confirm_state") == "ESCALATED", (s, body))
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    s, body = call("qa_cs1", "POST", f"/api/confirmation/queue/{PENDING}/calls/", {"result": "CALLBACK", "callback_at": past})
    ok("API: hẹn gọi lại quá khứ -> 400, không lưu", s == 400 and task(PENDING).get("confirm_state") == "PENDING", (s, body))
    s, body = call("qa_cs1", "POST", f"/api/confirmation/queue/{PENDING}/calls/", {"result": "UNREACHABLE", "note": "gọi 0912345678"})
    ok("API: ghi chú có SĐT -> 400 (BR-GH-19), không lưu", s == 400 and task(PENDING).get("attempts") == 0, (s, body))
    s, body = call("qa_cs1", "POST", f"/api/confirmation/queue/{PENDING}/calls/", {"result": "KHONG_HOP_LE"})
    ok("API: kết quả lạ -> 400", s == 400, (s, body))
    s, body = call("qa_manager", "POST", f"/api/confirmation/queue/{ESCALATED}/decide/", {"decision": "EXTEND", "reason": "thử", "until": (datetime.now(timezone.utc) + timedelta(hours=26)).isoformat()})
    ok("AC4 API: gia hạn > 24 giờ -> 400, việc không đổi", s == 400 and task(ESCALATED).get("confirm_state") == "ESCALATED", (s, body))

    # ---- UI cs1: hàng chờ + ghi cuộc gọi bấm đúp
    ctx, page, errs = session(b, "qa_cs1")
    page.goto(BASE + "/confirmation/")
    page.wait_for_function("() => !document.querySelector('#main .lt-skel') && document.querySelectorAll('#main tbody tr').length > 0")
    tabs = [re.sub(r"\s+", " ", t).strip() for t in page.get_by_role("tab").all_inner_texts()]
    ok("UI: đủ tab (Đến giờ gọi, Hẹn gọi lại, Cần quyết định, Gọi báo hoàn tiền, Chờ gọi, Tất cả)", [re.sub(r" \d+$", "", t) for t in tabs] == ["Đến giờ gọi", "Hẹn gọi lại", "Cần quyết định", "Gọi báo hoàn tiền", "Chờ gọi", "Tất cả"], tabs)
    page.get_by_role("tab", name=re.compile("^Tất cả")).click()
    page.wait_for_function("() => document.body.innerText.includes('5 / 5')")
    body = page.inner_text("main")
    ok("UI: tab Tất cả có 5 đơn với chip đủ nhãn chuẩn", {"Chờ gọi", "Hẹn gọi lại", "Cần quyết định", "Gọi báo hoàn tiền"} <= set(re.findall(r"Chờ gọi|Hẹn gọi lại|Cần quyết định|Gọi báo hoàn tiền", body)) and "QA-SO-11" in body, body[-300:])
    detail(page, PENDING)
    tl0 = page.locator("[data-timeline-row]").count()
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    d = page.get_by_role("dialog")
    d.wait_for()
    d.locator("label", has_text="Không nghe máy").first.click()
    d.get_by_label("Ghi chú", exact=False).fill("Chuông reo không ai bắt máy")
    d.get_by_role("button", name=re.compile("^Lưu kết quả")).dblclick()
    d.wait_for(state="detached")
    page.wait_for_function("(n) => document.querySelectorAll('[data-timeline-row]').length === n", arg=tl0 + 1)
    ok("AC2: bấm đúp 'Lưu kết quả' chỉ ghi 1 lần gọi (lần gọi 1/3)", task(PENDING).get("attempts") == 1, task(PENDING))
    ok("AC2: Dòng thời gian có thêm đúng 1 dòng, không cần nạp lại tay", page.locator("[data-timeline-row]").count() == tl0 + 1)
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_function("(n) => document.querySelectorAll('[data-timeline-row]').length >= n", arg=tl0 + 1)
    ok("AC2: nạp lại trang, dòng thời gian vẫn còn dòng đó", True)
    ok("UI: không có SĐT khách ở URL / storage", not PHONE_RE.search(page.url) and not PHONE_RE.search(page.evaluate("() => JSON.stringify([localStorage, sessionStorage])")))
    detail(page, ESCALATED)
    btns = [x.strip() for x in page.locator("main button, main a.btn").all_inner_texts()]
    ok("AC5 UI: qa_cs1 mở việc Cần quyết định -> không có nút 'Quyết định'", "Quyết định" not in btns, btns)
    ok("UI qa_cs1: không console.error", not errs, errs[:3])
    ctx.close()

    # ---- UI manager: Quyết định (Gia hạn gọi) bấm đúp
    ctx, page, errs = session(b, "qa_manager")
    detail(page, ESCALATED)
    page.get_by_role("button", name="Quyết định", exact=True).click()
    d = page.get_by_role("dialog")
    d.wait_for()
    d.locator("label", has_text="Gia hạn gọi").first.click()
    d.get_by_label(re.compile("^Lý do")).fill("Khách hẹn gọi chiều")
    vn_now = datetime.now(timezone(timedelta(hours=7)))
    d.get_by_label("Gia hạn tới lúc").fill((vn_now + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"))
    d.get_by_role("button", name=re.compile("Lưu quyết định")).dblclick()
    d.wait_for(state="detached")
    page.wait_for_load_state("networkidle")
    ok("AC4: Gia hạn gọi -> việc sang Hẹn gọi lại (bấm đúp chỉ 1 lần)", task(ESCALATED).get("confirm_state") == "CALLBACK", task(ESCALATED))
    ok("UI qa_manager: không console.error", not errs, errs[:3])
    ctx.close()

    # ---- vai không có quyền
    for u in ("qa_warehouse", "qa_courier1"):
        ctx, page, errs = session(b, u)
        ok(f"UI {u}: menu không có 'Gọi xác nhận'", page.locator(".nav a", has_text="Gọi xác nhận").count() == 0)
        page.goto(BASE + "/confirmation/")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_text("không có quyền", exact=False).first).to_be_visible()
        ok(f"UI {u}: vào thẳng /confirmation/ -> 'Không có quyền', DOM không có SĐT khách", not PHONE_RE.search(page.inner_text("body")))
        ctx.close()

    # ---- Nhật ký không chép SĐT / địa chỉ của khách (BR-GH-19, bất biến 9)
    s, logs = call("qa_owner", "GET", "/api/audit-logs/?page=1")
    blob = json.dumps(logs, ensure_ascii=False)
    ok("AuditLog: không chứa SĐT hay địa chỉ giả của khách", s == 200 and not PHONE_RE.search(blob) and "QA-Địa chỉ" not in blob, re.findall(r"0\d{9}", blob)[:3])
    b.close()
finish(R)
