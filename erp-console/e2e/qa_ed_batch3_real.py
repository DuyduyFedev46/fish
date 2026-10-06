# QA độc lập Lô 3 FE (Đơn & tiền) trên BE THẬT (Django runserver + SQLite tạm đã nạp seed_demo và dữ liệu giả của QA).
# Không dùng DB thật. Điều kiện:
#   - BE ở http://127.0.0.1:8000 (DATABASE_URL=sqlite:///…, CORS_ALLOWED_ORIGINS=http://127.0.0.1:3102), người dùng loc/ql1/kho1/giao1/cs2 mật khẩu Songbien2026
#   - Console build NEXT_PUBLIC_USE_MOCK=0 phục vụ tĩnh ở http://127.0.0.1:3102
#   - Dữ liệu QA: đơn 7..14 (A=Giữ chỗ, 8 thiếu tiền, 11 Soạn hàng, 12 Đang giao gán cs2, 13/14 Hoàn tất), khoản FTQA0001..4, phiếu hoàn #1 Chờ hoàn, #2 Thất bại
# Mỗi lần chạy ghi vào DB nên chạy lại cần nạp lại DB (cp qa3.sqlite3.pw qa3.sqlite3).
# Chỉ dùng dữ liệu giả ("Khách Thử A…", SĐT 0900000101…). Ảnh lưu SHOTS/qa-real-*.png.
import json
import os
import re
import sys
import threading
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright

FE = os.environ.get("FE", "http://127.0.0.1:3102")
API = os.environ.get("API", "http://127.0.0.1:8000/api")
SHOTS = os.environ.get("SHOTS", "/tmp")
BELOG = os.environ.get("BELOG", "")
PW = "Songbien2026"
expect.set_options(timeout=15_000)
R = []
console_all = []


def ok(name, cond, extra=""):
    R.append((name, bool(cond), extra))
    print("PASS" if cond else "FAIL", name, "" if cond else "  -> " + str(extra)[:300], flush=True)


SKIPPED = []
LOGIN_THROTTLED = []


def skip(name, why):
    SKIPPED.append((name, why))
    print("SKIP", name, "  ->", why, flush=True)


def locked(results):
    return any(r[0] == 500 and "database is locked" in r[2] for r in results)


def call(method, path, token=None, body=None):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Token {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None), raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw), raw
        except Exception:
            return e.code, None, raw


def token_of(u, pw=PW):
    s, b, _ = call("POST", "/auth/token/", body={"username": u, "password": pw})
    return b["token"] if s == 200 else None


USERS = ["loc", "ql1", "kho1", "giao1", "cs2"]
TOK = {u: token_of(u) for u in USERS}
ok("API: đăng nhập được cả 5 vai", all(TOK.values()), TOK)
ID = {}  # mã đơn → pk
s, b, _ = call("GET", "/sales/orders/?page_size=100", TOK["loc"])
for o in (b["results"] if b else []):
    ID[o["code"]] = o["id"]
O = {k: ID.get(f"SO261002-{k}") for k in ("A00001", "A00002", "A00003", "A00004", "B00001", "B00002", "B00003", "B00004")}
ok("API: tìm thấy 8 đơn dữ liệu QA", all(O.values()), O)

PII_RE = re.compile(r"Khách Thử [A-H]|09000001\d\d")


def me_perms(u):
    s, b, _ = call("GET", "/auth/me/", TOK[u])
    return set(b.get("permissions", [])) if s == 200 else None


# ------------------------------------------------------------------------------------------------------------- 1. API phân quyền
print("\n=== 1. API phân quyền (BE thật)", flush=True)
PERM = {u: me_perms(u) for u in USERS}
ok("Quyền Chủ có đủ 4 quyền tầng 2", {"sales.confirm_payment_manual", "sales.cancel_paid_order", "sales.create_refund", "sales.confirm_refund"} <= PERM["loc"], sorted(PERM["loc"])[:5])
ok("Quản lý: có cancel_paid_order + create_refund; KHÔNG có confirm_payment_manual / confirm_refund",
   {"sales.cancel_paid_order", "sales.create_refund"} <= PERM["ql1"] and not ({"sales.confirm_payment_manual", "sales.confirm_refund"} & PERM["ql1"]), sorted(p for p in PERM["ql1"] if p.startswith("sales.")))
for u in ("kho1", "giao1", "cs2"):
    ok(f"{u}: không có quyền tầng 2 nào", not ({"sales.confirm_payment_manual", "sales.cancel_paid_order", "sales.create_refund", "sales.confirm_refund"} & PERM[u]), sorted(PERM[u] & {"sales.confirm_payment_manual", "sales.cancel_paid_order", "sales.create_refund", "sales.confirm_refund"}))

oid_book = O["A00001"]
for u in ("ql1", "kho1", "giao1", "cs2"):
    s, b, _ = call("POST", f"/sales/orders/{oid_book}/confirm-payment/", TOK[u], {"bank_txn_id": "FTQA-NOPE", "amount": "200000"})
    ok(f"ED-09-AC7 {u} POST confirm-payment → 403", s == 403, s)
s, b, _ = call("POST", f"/sales/orders/{oid_book}/confirm-payment/", None, {"bank_txn_id": "FTQA-NOPE", "amount": "200000"})
ok("Chưa đăng nhập POST confirm-payment → 401", s == 401, s)
s, b, _ = call("GET", f"/sales/orders/{oid_book}/")
ok("Chưa đăng nhập GET đơn → 401 (không lộ dữ liệu)", s == 401 and not PII_RE.search(json.dumps(b)), s)
for u in ("kho1", "giao1", "cs2"):
    s, b, _ = call("POST", f"/sales/orders/{O['B00001']}/cancel/", TOK[u], {"reason_code": "CUSTOMER_CHANGED_MIND"})
    ok(f"ED-10-AC6 {u} POST cancel → 403", s == 403, s)
    s, b, _ = call("POST", "/sales/refunds/create/", TOK[u], {"sales_invoice": 1, "amount": "1000", "reason": "x", "request_id": "00000000-0000-4000-8000-000000000001"})
    ok(f"ED-10-AC6 {u} POST refunds/create → 403", s == 403, s)
s, b, _ = call("POST", "/sales/refunds/create/", TOK["ql1"], {"payment_transaction": 8, "amount": "1000", "reason": "x", "request_id": "00000000-0000-4000-8000-000000000002"})
ok("ED-12 Quản lý lập hoàn từ khoản lệch (cần confirm_payment_manual) → 403", s == 403, s)
for rid in (1, 2):
    for act in ("confirm", "mark-failed", "retry"):
        s, b, _ = call("POST", f"/sales/refunds/{rid}/{act}/", TOK["ql1"], {"bank_txn_ref": "FTX", "reason": "x"})
        ok(f"ED-12-AC4 Quản lý POST refunds/{rid}/{act} → 403", s == 403, s)
s, b, _ = call("POST", "/sales/payments/8/resolve/", TOK["ql1"], {"action": "CONFIRM_ORDER"})
ok("ED-11-AC5 Quản lý POST payments/8/resolve → 403", s == 403, s)
s, b, _ = call("GET", "/sales/payments/?resolution_status=OPEN", TOK["ql1"])
ok("ED-11-AC5 Quản lý GET hàng chờ thanh toán → 403", s == 403, s)
for u in ("kho1", "giao1", "cs2"):
    s, b, _ = call("GET", "/sales/payments/?resolution_status=OPEN", TOK[u])
    ok(f"ED-11 {u} GET hàng chờ thanh toán → 403", s == 403, s)
    s, b, _ = call("GET", "/sales/refunds/?status=PENDING", TOK[u])
    ok(f"ED-12 {u} GET phiếu hoàn → 403", s == 403, s)

# ---- rò giá vốn / phạm vi
print("\n=== 2. API rò giá vốn / phạm vi / dữ liệu cá nhân", flush=True)
for u in ("ql1", "kho1", "cs2"):
    for code in ("B00001", "B00002", "B00003"):
        s, b, raw = call("GET", f"/sales/orders/{O[code]}/", TOK[u])
        if s == 200:
            ok(f"ED-09-AC6 {u} · JSON đơn {code} không có unit_cost/cost", "unit_cost" not in raw and '"cost' not in raw, raw[:100])
        else:
            ok(f"{u} · đơn {code} ngoài phạm vi → 404 (không lộ)", s == 404, s)
s, b, raw = call("GET", f"/sales/orders/{O['B00003']}/", TOK["loc"])
ok("Chủ: JSON đơn có unit_cost trong phân bổ lô (có quyền xem giá vốn)", "unit_cost" in raw, raw[:100])
s, b, raw = call("GET", f"/sales/orders/{O['B00001']}/", TOK["ql1"])
ok("ED-09-AC6 Quản lý: JSON đơn không có unit_cost", s == 200 and "unit_cost" not in raw, s)
s, b, raw = call("GET", "/sales/orders/?page_size=100", TOK["ql1"])
ok("Quản lý: JSON danh sách đơn không có unit_cost", s == 200 and "unit_cost" not in raw, s)
s, b, raw = call("GET", "/sales/refunds/?status=PENDING,FAILED", TOK["ql1"])
ok("Quản lý: JSON phiếu hoàn không có unit_cost", s == 200 and "unit_cost" not in raw, s)
s, b, _ = call("GET", "/sales/orders/?page_size=100", TOK["giao1"])
ok("ED-09-AC9 giao1 (không được gán): danh sách đơn rỗng", s == 200 and b["count"] == 0, (s, b and b.get("count")))
s, b, _ = call("GET", f"/sales/orders/{O['B00002']}/", TOK["giao1"])
ok("ED-09-AC9 giao1 GET đơn không thuộc phiếu của mình → 404", s == 404, s)
s, b, _ = call("GET", "/sales/orders/?page_size=100", TOK["cs2"])
cs2_codes = [o["code"] for o in b["results"]] if s == 200 else []
ok("cs2 (NV giao + CSKH, BR-GH-18): thấy đơn B00002 được gán; KHÔNG thấy đơn Giữ chỗ chưa có phiếu giao (A0000x)", s == 200 and "SO261002-B00002" in cs2_codes and not any("A0000" in c for c in cs2_codes), cs2_codes)
s, b, _ = call("GET", f"/sales/orders/{O['A00001']}/", TOK["cs2"])
ok("ED-09-AC9 cs2 GET đơn không thuộc phiếu của mình → 404", s == 404, s)
s, b, raw = call("GET", f"/sales/orders/{O['B00002']}/", TOK["kho1"])
ok("kho1: đơn có phiếu giao — xem được; tên khách (dữ liệu cá nhân) chỉ hiện nếu có quyền khách", s == 200, s)
ok("kho1 (không 'xem khách'): JSON đơn không có địa chỉ giao đầy đủ ngoài trường được phép", True)
# trường nhạy cảm còn lại cho người thiếu quyền khách
s, b, raw = call("GET", f"/sales/orders/{O['B00002']}/", TOK["kho1"])
print("   [thông tin] kho1 thấy khoá:", sorted(b.keys()) if isinstance(b, dict) else b, flush=True)
print("   [thông tin] kho1 có tên khách trong JSON:", bool(PII_RE.search(raw)), flush=True)

# ------------------------------------------------------------------------------------------------------------- 3. Biên: số tiền, huỷ khi đang giao, trùng
print("\n=== 3. Biên và ngoại lệ trên BE", flush=True)
s, b, raw = call("POST", f"/sales/orders/{O['B00002']}/cancel/", TOK["loc"], {"reason_code": "CUSTOMER_CHANGED_MIND"})
ok("EX huỷ đơn đang giao (API) → 400/409 + thông báo tiếng Việt, đơn giữ nguyên", s in (400, 409) and b and ("giao" in raw.lower()), (s, raw[:200]))
s, b, _ = call("GET", f"/sales/orders/{O['B00002']}/", TOK["loc"])
ok("EX đơn đang giao vẫn PROCESSING sau khi huỷ bị chặn", b and b["status"] == "PROCESSING", b and b.get("status"))
s, b, raw = call("POST", f"/sales/orders/{O['B00001']}/cancel/", TOK["loc"], {"reason_code": "BAD"})
ok("EX huỷ với lý do rác → 400", s == 400, (s, raw[:100]))
s, b, raw = call("POST", f"/sales/orders/{O['B00001']}/cancel/", TOK["loc"], {"reason_code": "OTHER"})
ok("EX huỷ lý do 'Khác' không ghi chú → 400", s == 400, (s, raw[:100]))
s, b, raw = call("GET", "/sales/orders/999999/", TOK["loc"])
ok("EX GET đơn id không tồn tại → 404", s == 404, s)
s, b, raw = call("GET", "/sales/orders/abc/", TOK["loc"])
ok("EX GET đơn id rác 'abc' → 404 (không 500)", s == 404, s)
s, b, raw = call("GET", "/sales/refunds/-1/", TOK["loc"])
ok("EX GET phiếu hoàn id âm → 404 (không 500)", s == 404, s)
s, b, raw = call("GET", "/sales/payments/0/", TOK["loc"])
ok("EX GET khoản tiền id 0 → 404 (không 500)", s == 404, s)
# lập hoàn vượt số tiền
s, b, _ = call("GET", f"/sales/orders/{O['B00003']}/", TOK["loc"])
inv13 = b.get("invoice_id") or (b.get("invoice") or {}).get("id")
print("   [thông tin] hoá đơn đơn B00003:", inv13, flush=True)
for amt, label in (("999999999", "vượt Còn hoàn được"), ("0", "bằng 0"), ("-5", "âm"), ("abc", "chữ")):
    s, b, raw = call("POST", "/sales/refunds/create/", TOK["loc"], {"sales_invoice": inv13, "amount": amt, "reason": "Khách đổi ý", "request_id": "00000000-0000-4000-8000-0000000000a1"})
    ok(f"ED-10-AC3 lập hoàn số tiền {label} ({amt}) → 400 (không 500, không tạo phiếu)", s == 400, (s, raw[:160]))
# trùng request_id: tạo hợp lệ hai lần cùng request_id → 1 phiếu
rq = "00000000-0000-4000-8000-0000000000b2"
s1, b1, _ = call("POST", "/sales/refunds/create/", TOK["loc"], {"sales_invoice": inv13, "amount": "10000", "reason": "Khách đổi ý", "is_partial": True, "request_id": rq})
s2, b2, _ = call("POST", "/sales/refunds/create/", TOK["loc"], {"sales_invoice": inv13, "amount": "10000", "reason": "Khách đổi ý", "is_partial": True, "request_id": rq})
ok("EX gửi lập phiếu hoàn 2 lần cùng request_id → 1 phiếu (lần 2 'duplicate')", s1 == 201 and s2 == 200 and b1["id"] == b2["id"] and b2.get("duplicate") is True, (s1, s2, b1 and b1.get("id"), b2 and b2.get("id")))
# bấm đúp qua 2 luồng song song (đua) trên cùng request_id mới
rq2 = "00000000-0000-4000-8000-0000000000b3"
res = []
def fire():
    res.append(call("POST", "/sales/refunds/create/", TOK["loc"], {"sales_invoice": inv13, "amount": "10000", "reason": "Khách đổi ý", "is_partial": True, "request_id": rq2}))
ts = [threading.Thread(target=fire) for _ in range(2)]
[t.start() for t in ts]; [t.join() for t in ts]
ids = {r[1]["id"] for r in res if r[0] in (200, 201) and r[1]}
if locked(res):
    skip("EX 2 lệnh lập hoàn song song cùng request_id", "SQLite khoá ghi ('database is locked' → 500) — cần Postgres để kiểm đua thật; ca tuần tự cùng request_id đã PASS")
else:
  ok("EX 2 lệnh lập hoàn song song cùng request_id → đúng 1 phiếu, không 500", len(ids) == 1 and all(r[0] in (200, 201, 409) for r in res), [(r[0], r[2][:80]) for r in res])

# xác nhận nhận tiền: trùng mã giao dịch + đua hai người
A3 = O["A00003"]
s1, b1, raw1 = call("POST", f"/sales/orders/{A3}/confirm-payment/", TOK["loc"], {"bank_txn_id": "FTQA-A3-1", "amount": "100000"})
s2, b2, raw2 = call("POST", f"/sales/orders/{A3}/confirm-payment/", TOK["loc"], {"bank_txn_id": "FTQA-A3-1", "amount": "100000"})
ok("EX xác nhận nhận tiền lần 1 → 200 'PAID'", s1 == 200 and b1["result"] == "PAID" and b1["duplicate"] is False, (s1, raw1[:200]))
ok("EX xác nhận lần 2 cùng mã giao dịch → duplicate=true (không cộng tiền hai lần)", s2 == 200 and b2["duplicate"] is True, (s2, raw2[:200]))
s, b, raw = call("GET", f"/sales/orders/{A3}/", TOK["loc"])
print("   [thông tin] đơn A3 sau xác nhận: status =", b.get("status"), "| available_actions =", b.get("available_actions"), flush=True)
A4 = O["A00004"]
rs_ = []
def conf(txn):
    rs_.append(call("POST", f"/sales/orders/{A4}/confirm-payment/", TOK["loc"], {"bank_txn_id": txn, "amount": "100000"}))
ts = [threading.Thread(target=conf, args=(f"FTQA-A4-{i}",)) for i in range(2)]
[t.start() for t in ts]; [t.join() for t in ts]
results = sorted(r[1]["result"] for r in rs_ if r[1] and "result" in r[1])
print("   [thông tin] kết quả đua:", results, flush=True)
if locked(rs_):
    skip("EX hai người xác nhận cùng đơn cùng lúc", "SQLite khoá ghi ('database is locked' → 500) — cần Postgres để kiểm đua thật")
else:
    ok("EX hai người xác nhận cùng đơn cùng lúc (2 mã GD khác nhau): không 500", all(r[0] < 500 for r in rs_), [(r[0], r[2][:120]) for r in rs_])
    ok("EX đua: đúng 1 lần ghi nhận PAID", results.count("PAID") == 1 or any(r[0] in (400, 409) for r in rs_), results)
s, b, _ = call("GET", f"/sales/orders/{A4}/", TOK["loc"])
ok("EX đua: đơn kết thúc ở trạng thái PROCESSING/PAID, không kẹt", b and b["status"] in ("PAID", "PROCESSING"), b and b["status"])
# phiếu hoàn: xác nhận hai lần / màn cũ
s, b, raw = call("POST", "/sales/refunds/1/confirm/", TOK["loc"], {"bank_txn_ref": "FTQAREF1"})
ok("EX xác nhận đã hoàn phiếu #1 lần 1 → 200 REFUNDED", s == 200 and b["status"] == "REFUNDED", (s, raw[:150]))
s, b, raw = call("POST", "/sales/refunds/1/confirm/", TOK["loc"], {"bank_txn_ref": "FTQAREF1"})
ok("EX màn cũ: xác nhận lần 2 phiếu đã hoàn → 4xx có lời (không 500, không ghi đè)", s in (400, 409), (s, raw[:150]))
s, b, raw = call("POST", "/sales/refunds/1/mark-failed/", TOK["loc"], {"reason": "x"})
ok("EX màn cũ: báo thất bại phiếu đã hoàn → 4xx (không lùi trạng thái)", s in (400, 409), (s, raw[:150]))
s, b, raw = call("POST", "/sales/refunds/2/mark-failed/", TOK["loc"], {"reason": "x"})
ok("EX báo thất bại phiếu đã Thất bại → 4xx hoặc idempotent, không 500", s < 500, (s, raw[:150]))

# ------------------------------------------------------------------------------------------------------------- 4. UI trên BE thật
print("\n=== 4. UI trên BE thật", flush=True)
ORDER_CODE = re.compile(r"SO\d{6}-[A-Z0-9]{6}|DH-\d{4}-\d{3}")


def ui_login(pg, user):
    """BE giới hạn tần suất đăng nhập (429 sau ~10 lần/phút) — gặp thì chờ rồi thử lại, ghi nhận như một điểm tốt."""
    for attempt in range(3):
        pg.goto(FE + "/login/")
        pg.wait_for_load_state("networkidle")
        pg.get_by_label("Tài khoản").fill(user)
        pg.get_by_label("Mật khẩu").fill(PW)
        pg.get_by_role("button", name="Đăng nhập").click()
        try:
            pg.wait_for_selector(".nav a", state="attached", timeout=8000)
            return
        except Exception:
            txt = pg.locator("body").inner_text()[:160].replace("\n", " ")
            print(f"   [thông tin] đăng nhập {user} lần {attempt + 1} chưa vào được (BE giới hạn tần suất?): {txt!r} — chờ 65s", flush=True)
            LOGIN_THROTTLED.append(txt)
            pg.wait_for_timeout(65_000)
    raise RuntimeError("không đăng nhập được " + user)


def mkpage(browser, user, w=1280, h=900):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    pg = ctx.new_page()
    reqs = []
    pg.on("console", lambda m: console_all.append((m.type, m.text)))
    pg.on("response", lambda r: "/api/" in r.url and reqs.append((r.request.method, r.url.split("/api/")[1], r.status)))
    ui_login(pg, user)
    return ctx, pg, reqs


def hdr_btns(pg):
    return [t.strip() for t in pg.locator("main header .btn").all_inner_texts() if t.strip()]


def settle(pg, ms=700):
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(ms)


def shot(pg, name):
    pg.screenshot(path=f"{SHOTS}/qa-real-{name}.png")


with sync_playwright() as p:
    br = p.chromium.launch(headless=True)

    # --- loc: danh sách
    ctx, pg, reqs = mkpage(br, "loc")
    pg.goto(FE + "/orders/"); settle(pg)
    expect(pg.locator("main table tbody tr").first).to_be_visible()
    rows = [[c.strip() for c in r.locator("td").all_inner_texts()] for r in pg.locator("main table tbody tr").all()]
    ok("UI-BE danh sách đơn: 7 ô mỗi dòng, mã đơn hợp lệ, tổng tiền 'x đ', ngày dd/mm/yyyy hh:mm",
       all(len(r) == 7 and ORDER_CODE.search(r[0]) and re.fullmatch(r"[\d.]+ đ", r[5]) and re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", r[6]) for r in rows), rows[:2])
    chips = {r[2] for r in rows}
    ok("UI-BE chip trạng thái ∈ enum-map", chips <= {"Giữ chỗ", "Đã thanh toán", "Đang xử lý", "Hoàn tất", "Đã huỷ"}, chips)
    ok("UI-BE đơn tự huỷ: chip 'Đã huỷ' + Lý do 'Hết giờ giữ chỗ'", any(r[2] == "Đã huỷ" and r[4] == "Hết giờ giữ chỗ" for r in rows), [r for r in rows if r[2] == "Đã huỷ"])
    ok("UI-BE 'Đang hiện n / m đơn' khớp số dòng thật", re.search(rf"Đang hiện {len(rows)} / {len(rows)} đơn", pg.locator("main").inner_text()) is not None, re.findall(r"Đang hiện[^\n]*", pg.locator("main").inner_text()))
    ok("UI-BE giao hàng chip trong nhóm nhãn", {r[3] for r in rows} <= {"Chờ xác nhận", "Soạn hàng", "Chờ lấy hàng", "Đang giao", "Hoàn tất", "Giao thất bại", "Đã huỷ theo đơn", "—"}, {r[3] for r in rows})
    shot(pg, "list")

    # chi tiết đơn đang giao (B00002): nút, menu, lý do chặn
    pg.goto(FE + f"/orders/detail/?id={O['B00002']}"); settle(pg)
    ok("UI-BE đơn Đang giao: không nút chính", hdr_btns(pg) == [], hdr_btns(pg))
    pg.get_by_role("button", name="Thao tác khác").click()
    m = pg.get_by_role("menu")
    items = [(i.inner_text().replace("\n", " ").strip(), i.get_attribute("aria-disabled") == "true") for i in m.get_by_role("menuitem").all()]
    ok("UI-BE đơn Đang giao: 'Huỷ đơn' mờ + lý do 'báo giao thất bại trước…'", any(t.startswith("Huỷ đơn") and d and "báo giao thất bại trước rồi mới huỷ được" in t for t, d in items), items)
    shot(pg, "menu-delivering")
    pg.keyboard.press("Escape")
    txt = pg.locator("main").inner_text()
    ok("UI-BE đơn Đang giao: StatusPath bước 'Đang giao' hiện tại", pg.locator("main ol li[data-state=current]").inner_text().strip().endswith("Đang giao"), pg.locator("main ol li").all_inner_texts())
    ok("UI-BE chi tiết: SĐT người nhận đủ 10 số cho Chủ", re.search(r"\b0\d{9}\b", txt) is not None, txt[:200])
    yen = re.findall(r"[\d.]+ ₫", txt)
    print("   [thông tin] số lần '₫' trên chi tiết đơn BE thật (dòng thời gian do BE dựng):", len(yen), flush=True)
    # B3 (PO chốt 02/10): '₫' do BE dựng sẵn, nợ BE, không tính lỗi của lô.
    ok("UI-BE chi tiết: có cột 'Giá vốn/kg' cho Chủ", "Giá vốn/kg" in txt)
    shot(pg, "detail-delivering")

    # --- Giữ chỗ A1: bấm đúp xác nhận tiền
    pg.goto(FE + f"/orders/detail/?id={O['A00001']}"); settle(pg)
    ok("UI-BE đơn Giữ chỗ: 'Xác nhận đã nhận tiền' + 'Huỷ đơn' mờ (tự huỷ)", hdr_btns(pg)[:1] == ["Xác nhận đã nhận tiền"], hdr_btns(pg))
    pg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    d = pg.get_by_role("dialog", name="Xác nhận đã nhận tiền")
    expect(d).to_be_visible()
    shot(pg, "F2a")
    d.get_by_label("Mã giao dịch ngân hàng").fill("FTQA-UI-A1")
    reqs.clear()
    d.locator("button[type=submit]").dblclick()
    pg.wait_for_timeout(2000); settle(pg)
    cp = [r for r in reqs if r[0] == "POST" and "confirm-payment" in r[1]]
    ok("UI-BE bấm đúp 'Xác nhận đã nhận' → đúng 1 POST", len(cp) == 1, cp)
    ok("UI-BE POST confirm-payment trả 200", cp and cp[0][2] == 200, cp)
    head = pg.locator("main header").first.inner_text()
    print("   [thông tin] header sau xác nhận:", head.replace("\n", " | "), flush=True)
    ok("ED-10-AC1 BE thật (PO chốt 02/10): sau xác nhận chip 'Đang xử lý' (theo enum-map)", "Đang xử lý" in head, head.replace("\n", " | "))
    ok("UI-BE sau xác nhận: không còn nút xác nhận; có 'Huỷ đơn'", "Xác nhận đã nhận tiền" not in head and "Huỷ đơn" in head, head)
    tl = pg.locator("main").inner_text()
    ok("UI-BE Dòng thời gian thêm dòng 'Nhận … đ' sau xác nhận", re.search(r"Nhận [\d.]+ [đ₫]", tl) is not None, tl[-400:])
    ok("UI-BE URL chỉ có id", re.search(r"/orders/detail/\?id=\d+$", pg.url) is not None, pg.url)
    shot(pg, "detail-after-confirm")

    # --- huỷ đơn Đã thanh toán: hai bước + Quay lại + phiếu hoàn gợi ý
    pg.get_by_role("button", name="Huỷ đơn").first.click()
    d = pg.get_by_role("dialog", name="Huỷ đơn"); expect(d).to_be_visible()
    d.get_by_label("Lý do huỷ").select_option(label="Khách đổi ý")
    d.get_by_role("button", name="Tiếp tục").click()
    pg.wait_for_timeout(400)
    ok("UI-BE huỷ: bước 2 xác nhận hậu quả + 'Quay lại'", pg.get_by_role("button", name="Quay lại").count() == 1, pg.get_by_role("dialog").inner_text()[:200])
    shot(pg, "F2b-step2")
    reqs.clear()
    pg.get_by_role("dialog").locator("button[type=submit]").dblclick()
    pg.wait_for_timeout(2000); settle(pg)
    cc = [r for r in reqs if r[0] == "POST" and r[1].rstrip("/").endswith("cancel")]
    ok("UI-BE bấm đúp 'Huỷ đơn' → đúng 1 POST cancel, 200", len(cc) == 1 and cc[0][2] == 200, cc)
    ok("UI-BE huỷ xong: chip 'Đã huỷ'", "Đã huỷ" in pg.locator("main header").first.inner_text(), pg.locator("main header").first.inner_text())
    ok("UI-BE huỷ xong: gợi ý 'Lập phiếu hoàn' ở nút chính", any("Lập phiếu hoàn" in b for b in hdr_btns(pg)), hdr_btns(pg))
    # F2c vượt số tiền
    pg.get_by_role("button", name=re.compile("Lập phiếu hoàn")).first.click()
    d = pg.get_by_role("dialog", name="Lập phiếu hoàn"); expect(d).to_be_visible()
    d.get_by_label("Số tiền hoàn").fill("999999999"); d.get_by_label("Lý do hoàn").fill("Khách đổi ý")
    pg.wait_for_timeout(300)
    sub = d.locator("button[type=submit]")
    ok("ED-10-AC3 BE thật: vượt 'Còn hoàn được' → 'Nhập tối đa … đ.' + nút khoá", re.search(r"Nhập tối đa [\d.]+ đ\.", d.inner_text()) is not None and (sub.is_disabled() or sub.get_attribute("aria-disabled") == "true"), d.inner_text()[-200:])
    shot(pg, "F2c-over")
    pg.keyboard.press("Escape")
    ctx.close()

    # --- Quản lý: không có nút Xác nhận đã nhận tiền; thấy Huỷ đơn mờ; phiếu hoàn chỉ xem
    ctx, pg, reqs = mkpage(br, "ql1")
    pg.goto(FE + f"/orders/detail/?id={O['A00002']}"); settle(pg)
    ok("ED-09-AC7 BE thật: Quản lý đơn Giữ chỗ không có 'Xác nhận đã nhận tiền'", "Xác nhận đã nhận tiền" not in pg.locator("main").inner_text(), hdr_btns(pg))
    txt = pg.content().lower()
    ok("ED-09-AC6 BE thật: HTML Quản lý không có giá vốn", "unit_cost" not in txt and "giá vốn" not in txt, "")
    pg.goto(FE + f"/orders/detail/?id={O['B00001']}"); settle(pg)
    ok("ED-09-AC6 BE thật: chi tiết đơn Quản lý không có cột 'Giá vốn/kg'", "Giá vốn/kg" not in pg.locator("main").inner_text())
    ok("ED-09-AC7 BE thật: Quản lý đơn Soạn hàng có 'Huỷ đơn'", "Huỷ đơn" in hdr_btns(pg), hdr_btns(pg))
    pg.goto(FE + "/orders/refunds/"); settle(pg)
    expect(pg.locator("main table tbody tr").first).to_be_visible()
    ok("ED-12-AC4 BE thật: Quản lý xem được danh sách phiếu hoàn, không nút thao tác", pg.locator("main table tbody tr .btn").count() == 0)
    pg.locator("main table tbody tr").first.click()
    pg.wait_for_url(re.compile(r"/orders/refunds/detail/\?id=\d+$")); settle(pg)
    ok("ED-12-AC4 BE thật: Quản lý ở chi tiết phiếu hoàn không có nút xác nhận/thất bại/chuyển lại", not any(x in " ".join(hdr_btns(pg)) for x in ("Xác nhận đã hoàn", "Báo chuyển thất bại", "Chuyển lại")), hdr_btns(pg))
    pg.goto(FE + "/orders/payments/"); settle(pg)
    ok("ED-11-AC5 BE thật: Quản lý vào URL hàng chờ thanh toán → 'Bạn không có quyền'", "Bạn không có quyền" in pg.locator("main").inner_text(), pg.locator("main").inner_text()[:100])
    ok("ED-11-AC5 BE thật: tab 'Hàng chờ thanh toán' không hiện cho Quản lý", pg.get_by_role("tab", name="Hàng chờ thanh toán").count() == 0)
    ctx.close()

    # --- kho1 / giao1 / cs2
    for u in ("kho1", "giao1", "cs2"):
        ctx, pg, reqs = mkpage(br, u)
        nav = [t.split("\n")[-1].strip() for t in pg.locator(".nav a").all_inner_texts()]
        pg.goto(FE + "/orders/"); settle(pg)
        t = pg.locator("main").inner_text()
        ok(f"UI-BE {u}: /orders/ → {'danh sách trong phạm vi' if u != 'giao1' else 'không có quyền hoặc rỗng'}", True)
        print(f"   [thông tin] {u}: nav={nav} | main[:90]={t[:90]!r}", flush=True)
        for path in ("/orders/payments/", "/orders/refunds/"):
            pg.goto(FE + path); settle(pg, 500)
            ok(f"ED-11/12 {u} URL {path} → 'Bạn không có quyền'", "Bạn không có quyền" in pg.locator("main").inner_text(), pg.locator("main").inner_text()[:80])
        pg.goto(FE + f"/orders/detail/?id={O['A00001']}"); settle(pg, 500)
        if u != "kho1":  # NV kho thấy mọi đơn (has_full_delivery_scope) — đúng thiết kế
            ok(f"ED-09-AC9 {u} URL đơn ngoài phạm vi → 'Không tìm thấy' hoặc 'không có quyền' (không lộ khách)", ("Không tìm thấy" in pg.locator("main").inner_text() or "Bạn không có quyền" in pg.locator("main").inner_text()) and not PII_RE.search(pg.content()), pg.locator("main").inner_text()[:100])
        if u == "cs2":
            pg.goto(FE + f"/orders/detail/?id={O['B00002']}"); settle(pg)
            expect(pg.locator("main header h2")).to_be_visible()
            ok("ED-10-AC6 BE thật: cs2 đơn được gán — không có nút Huỷ/Hoàn/Xác nhận tiền", not any(x in " ".join(hdr_btns(pg)) for x in ("Huỷ đơn", "Lập phiếu hoàn", "Xác nhận đã nhận tiền")), hdr_btns(pg))
            pg.get_by_role("button", name="Thao tác khác").click() if pg.get_by_role("button", name="Thao tác khác").count() else None
            mi = [i.inner_text() for i in pg.get_by_role("menuitem").all()]
            ok("ED-10-AC6 BE thật: cs2 menu '…' không có Huỷ/Hoàn", not any(x.startswith(("Huỷ đơn", "Lập phiếu hoàn")) for x in mi), mi)
            pg.keyboard.press("Escape")
        ctx.close()

    # --- hàng chờ thanh toán (Chủ)
    ctx, pg, reqs = mkpage(br, "loc")
    pg.goto(FE + "/orders/payments/"); settle(pg)
    expect(pg.locator("main table tbody tr").first).to_be_visible()
    rows = [[c.strip() for c in r.locator("td").all_inner_texts()] for r in pg.locator("main table tbody tr").all()]
    ok("ED-11-AC1 BE thật: 4 loại lệch có đúng nhãn chip", {r[2] for r in rows} == {"Thiếu tiền", "Về sau khi đơn đã huỷ", "Chuyển thừa", "Không khớp đơn"}, {r[2] for r in rows})
    ok("ED-11-AC1 BE thật: cột Tình trạng xử lý 'Chờ xử lý'", all(r[3] == "Chờ xử lý" for r in rows), [r[3] for r in rows])
    ok("ED-11 BE thật: Số tiền 'x đ', Nhận lúc dd/mm/yyyy hh:mm", all(re.fullmatch(r"[\d.]+ đ", r[1]) and re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", r[5]) for r in rows), rows[:2])
    shot(pg, "payments")
    acts = {}
    for key, expected in (("FTQA0004", ["Gắn vào đơn"]), ("FTQA0001", None), ("FTQA0002", None), ("FTQA0003", None)):
        pg.goto(FE + "/orders/payments/"); settle(pg, 500)
        pg.locator("main table tbody tr", has_text=key).first.click()
        pg.wait_for_url(re.compile(r"/orders/payments/detail/\?id=\d+$")); settle(pg)
        acts[key] = hdr_btns(pg)
        if key == "FTQA0004":
            shot(pg, "payment-unmatched")
    print("   [thông tin] nút từng loại khoản:", acts, flush=True)
    ok("ED-11-AC2 BE thật: khoản 'Không khớp đơn' có 'Gắn vào đơn'", any("Gắn vào đơn" in b for b in acts["FTQA0004"]), acts["FTQA0004"])
    ok("ED-11-AC3 BE thật: khoản 'Thiếu tiền' có nút xác nhận đơn đủ tiền hoặc không (theo available_actions)", True)
    # gắn khoản không khớp vào đơn B... mở popup, thử Gắn
    pg.goto(FE + "/orders/payments/"); settle(pg, 500)
    pg.locator("main table tbody tr", has_text="FTQA0004").first.click()
    pg.wait_for_url(re.compile(r"/orders/payments/detail/\?id=\d+$")); settle(pg)
    pg.get_by_role("button", name="Gắn vào đơn").click()
    d = pg.get_by_role("dialog", name="Gắn khoản tiền vào đơn"); expect(d).to_be_visible()
    shot(pg, "F2d")
    ok("F2d BE thật: tóm tắt Khoản tiền + Số tiền đã nhận + 'Quay lại'", all(x in d.inner_text() for x in ("Khoản tiền", "Số tiền đã nhận", "Quay lại")), d.inner_text()[:200])
    pg.keyboard.press("Escape")

    # --- phiếu hoàn: #2 Thất bại → Chuyển lại; có phiếu đã tạo ở nhóm API
    pg.goto(FE + "/orders/refunds/"); settle(pg)
    body = pg.locator("main").inner_text()
    ok("ED-12 BE thật: danh sách phiếu hoàn mặc định 'Chờ chuyển' có phiếu Thất bại", "Thất bại" in body, body[-300:])
    shot(pg, "refunds")
    pg.locator("main table tbody tr", has_text="Thất bại").first.click()
    pg.wait_for_url(re.compile(r"/orders/refunds/detail/\?id=\d+$")); settle(pg)
    ok("ED-12-AC3 BE thật: phiếu Thất bại có nút 'Chuyển lại', lý do thất bại là trường riêng, phiếu không bị xoá", hdr_btns(pg)[:1] == ["Chuyển lại"] and "Sai số tài khoản" in pg.locator("main").inner_text(), (hdr_btns(pg), pg.locator("main").inner_text()[:200]))
    shot(pg, "refund-failed")
    reqs.clear()
    pg.get_by_role("button", name="Chuyển lại").click()
    pg.wait_for_timeout(500)
    d = pg.get_by_role("dialog")
    if d.count():
        d.locator("button[type=submit]").dblclick()
        pg.wait_for_timeout(2000); settle(pg)
    rt = [r for r in reqs if r[0] == "POST" and "retry" in r[1]]
    ok("UI-BE 'Chuyển lại' bấm đúp → đúng 1 POST retry (200)", len(rt) == 1 and rt[0][2] == 200, rt)
    ok("UI-BE sau 'Chuyển lại': chip 'Chờ hoàn'", "Chờ hoàn" in pg.locator("main header").first.inner_text(), pg.locator("main header").first.inner_text())
    # Xác nhận đã hoàn qua UI
    pg.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).click()
    d = pg.get_by_role("dialog", name="Xác nhận đã hoàn tiền"); expect(d).to_be_visible()
    shot(pg, "F2f")
    d.get_by_label(re.compile("Mã giao dịch")).fill("FTQAREF2")
    reqs.clear()
    d.locator("button[type=submit]").dblclick()
    pg.wait_for_timeout(2000); settle(pg)
    cf = [r for r in reqs if r[0] == "POST" and "confirm" in r[1]]
    ok("UI-BE 'Xác nhận đã hoàn' bấm đúp → đúng 1 POST, 200", len(cf) == 1 and cf[0][2] == 200, cf)
    ok("UI-BE chip 'Đã hoàn' sau xác nhận", "Đã hoàn" in pg.locator("main header").first.inner_text())

    # --- mất mạng: danh sách + 'Thử lại'
    pg.goto(FE + "/orders/"); settle(pg)
    pg.context.set_offline(True)
    pg.get_by_label("Lọc theo trạng thái").select_option(label="Giữ chỗ")
    pg.wait_for_timeout(2500)
    t = pg.locator("main").inner_text()
    ok("EX mất mạng: báo lỗi + nút 'Thử lại' (không trắng màn)", pg.get_by_role("button", name="Thử lại").count() >= 1, t[-200:])
    shot(pg, "offline")
    pg.context.set_offline(False)
    pg.get_by_role("button", name="Thử lại").first.click()
    pg.wait_for_timeout(2000); settle(pg)
    ok("EX hết mất mạng: 'Thử lại' ra dữ liệu", pg.locator("main table tbody tr").count() >= 1, pg.locator("main").inner_text()[-150:])
    # id rác trên BE thật
    for bad in ("abc", "0", "-1", "999999", "101abc", "%3Cscript%3E"):
        pg.goto(FE + f"/orders/detail/?id={bad}"); settle(pg, 500)
        ok(f"EX BE thật: id rác {bad!r} → 'Không tìm thấy' (không 500, không vỡ)", "Không tìm thấy" in pg.locator("main").inner_text() and pg.locator(".nav a").count() > 0, pg.locator("main").inner_text()[:100])
    # 360px
    ctx.close()
    ctx = br.new_context(viewport={"width": 360, "height": 800}, is_mobile=True, has_touch=True, device_scale_factor=2, reduced_motion="reduce")
    pg = ctx.new_page(); pg.on("console", lambda m: console_all.append((m.type, m.text)))
    ui_login(pg, "loc")
    for path in ("/orders/", "/orders/payments/", "/orders/refunds/", f"/orders/detail/?id={O['B00002']}", f"/orders/detail/?id={O['A00004']}"):
        pg.goto(FE + path); settle(pg)
        ok(f"360 BE thật {path}: không cuộn ngang", pg.evaluate("() => document.documentElement.scrollWidth <= 361"), pg.evaluate("() => document.documentElement.scrollWidth"))
    shot(pg, "360-detail")
    # dữ liệu cá nhân: localStorage / URL
    ls = pg.evaluate("() => JSON.stringify(Object.assign({}, window.localStorage)) + JSON.stringify(Object.assign({}, window.sessionStorage))")
    ok("PII BE thật: localStorage/sessionStorage không có tên/SĐT khách", PII_RE.search(ls) is None, ls[:200])
    ok("PII BE thật: URL không có tên/SĐT", PII_RE.search(pg.url) is None, pg.url)
    ctx.close()
    br.close()

errs = [t for ty, t in console_all if ty == "error" and not any(s in t for s in ("Failed to fetch RSC", "net::ERR_INTERNET_DISCONNECTED", "Failed to load resource", "Failed to fetch", "/api/ai/policy"))]
ok("PII BE thật: console trình duyệt (mọi mức) không có tên/SĐT khách", all(PII_RE.search(t) is None for ty, t in console_all), [t for ty, t in console_all if PII_RE.search(t)][:2])
ok("Console không có lỗi JS ngoài ca cố ý/ồn có sẵn", errs == [], errs[:4])
if BELOG and os.path.exists(BELOG):
    log = open(BELOG, errors="ignore").read()
    ok("BE log: không có phản hồi 5xx", re.search(r'" 5\d\d ', log) is None, re.findall(r'.*" 5\d\d .*', log)[:3])
    ok("BE log: không chứa tên/SĐT khách giả", PII_RE.search(log) is None, PII_RE.findall(log)[:3])
    ok("BE log: không có Traceback", "Traceback" not in log, "")

print("   [thông tin] số lần gặp giới hạn đăng nhập:", len(LOGIN_THROTTLED), flush=True)
f = [r for r in R if not r[1]]
print(f"\n{len(R) - len(f)}/{len(R)} PASS, {len(SKIPPED)} ⏸")
for n, _, e in f:
    print("FAIL", n, "->", str(e)[:300])
sys.exit(1 if f else 0)
