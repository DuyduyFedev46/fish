# QA độc lập Lô 9 (Hàng hoàn ED-26) ở tầng API trên BE THẬT (Django :8000, SQLite tạm đã nạp qa9/seed.py).
#   QA_DB=<sqlite> API=http://127.0.0.1:8000 python3 e2e/qa_ed_batch9_api.py
# Phiếu giao dựng bằng fixture (id 1..9 theo seed.py): 1 RACE(giao1,10kg) 2 FAILED(giao1, lô A 5kg + lô B 4kg) 3 OTHER(giao2)
# 4 RESTOCK(giao1,6kg) 5 WRITEOFF(giao1,6kg) 6 STALE(giao1,3kg) 7 READY 8 COMPLETED 9 CLOSED(lô B 3kg).
# Chỉ dữ liệu giả. Chạy lại cần nạp lại DB (qa9.base.sqlite3).
import json
import os
import re
import sqlite3
import sys
import threading
import urllib.error
import urllib.request

API = os.environ.get("API", "http://127.0.0.1:8000") + "/api/"
DB = os.environ["QA_DB"]
PW = "Songbien2026"
R = []
TOK = {}
A_PK, B_PK = 1, 2


def ok(name, cond, extra=""):
    R.append((name, bool(cond)))
    print("PASS" if cond else "FAIL", name, "" if cond else "  -> " + str(extra)[:500], flush=True)


def call(user, method, path, body=None, raw=None):
    data = json.dumps(body).encode() if body is not None else raw
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if user:
        req.add_header("Authorization", "Token " + TOK[user])
    try:
        r = urllib.request.urlopen(req, timeout=30)
        txt = r.read().decode()
        return r.status, (json.loads(txt) if txt.strip().startswith(("{", "[")) else txt), dict(r.headers)
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        try:
            return e.code, json.loads(txt), dict(e.headers)
        except Exception:
            return e.code, txt, dict(e.headers)


def db(sql, *a):
    c = sqlite3.connect(DB)
    try:
        return c.execute(sql, a).fetchall()
    finally:
        c.close()


def on_hand(pk):
    # cột tồn của lô (tên cột thật)
    col = "qty_available"
    return float(db(f"select {col} from inventory_batch where id=?", pk)[0][0])


def ledger(pk):
    return db("select movement_type, qty_change, 0, reference from inventory_stockledgerentry where batch_id=? order by id", pk)


def code_of(body):
    return body.get("code") if isinstance(body, dict) else None


for u in ("loc", "ql1", "kho1", "giao1", "giao2", "cs1", "cs2"):
    s, b, _ = call(None, "POST", "auth/token/", {"username": u, "password": PW})
    TOK[u] = b["token"] if s == 200 else None
ok("đăng nhập 7 vai (loc, ql1, kho1, giao1, giao2, cs1, cs2) lấy được token", all(TOK.values()), TOK)

PHONE = "0900000201"
CUST = ("Khách SO-QA9", PHONE, "1 Cảng")


def pii_in(obj):
    t = json.dumps(obj, ensure_ascii=False)
    return [x for x in ("Khách SO-QA9", "0900000", "1 Cảng", "Khách") if x in t]


# ---- 1. Dòng phiếu giao: batch_pk, returned_qty ----
s, d, h = call("giao1", "GET", "delivery/notes/1/")
ok("S1 giao1 xem phiếu giao của mình 200", s == 200, (s, d))
line = d["lines"][0] if s == 200 else {}
ok("S1 dòng phiếu giao có đủ khoá cũ + batch_pk + returned_qty (đúng 6 khoá)", set(line) == {"item_name", "qty_kg", "batch_id", "expiry_date", "batch_pk", "returned_qty"}, line)
ok("S1 batch_pk là số nguyên đúng pk lô; returned_qty = '0.000'", line.get("batch_pk") == A_PK and line.get("returned_qty") == "0.000", line)
txt = json.dumps(d)
ok("S1 JSON phiếu giao không chứa giá vốn (123457, unit_cost, purchase_rate, landed)", not re.search(r"123457|unit_cost|purchase_rate|landed|cost", txt), txt[:300])
s2, d2, _ = call("giao1", "GET", "delivery/notes/2/")
ok("S1b phiếu 2 nhiều lô: hai dòng, mỗi dòng batch_pk riêng", s2 == 200 and sorted(l["batch_pk"] for l in d2["lines"]) == [A_PK, B_PK], d2.get("lines"))
s3, _, _ = call("giao1", "GET", "delivery/notes/3/")
ok("S1c giao1 mở phiếu của giao2 -> 404", s3 == 404, s3)
s3b, d3b, _ = call("giao2", "GET", "delivery/notes/3/")
ok("S1d giao2 xem phiếu của mình", s3b == 200)
for u in ("loc", "ql1", "kho1"):
    st, dd, _ = call(u, "GET", "delivery/notes/1/")
    ok(f"S1e {u} xem được phiếu 1, có batch_pk/returned_qty", st == 200 and dd["lines"][0].get("batch_pk") == A_PK, st)
s_anon, _, _ = call(None, "GET", "delivery/notes/1/")
ok("S1f chưa đăng nhập -> 401", s_anon == 401, s_anon)

# ---- 2. Tạo phiếu hàng hoàn: biên, âm, vượt, lô sai, trạng thái ----
def post_ret(user, note, batch, qty, note_text=None):
    body = {"delivery_note": note, "batch": batch, "qty": qty}
    if note_text is not None:
        body["note"] = note_text
    return call(user, "POST", "inventory/returns/", body)

s, b, _ = post_ret("giao1", 1, A_PK, "0")
ok("S2 qty=0 -> 400", s == 400, (s, b))
s, b, _ = post_ret("giao1", 1, A_PK, "-1")
ok("S2 qty âm -> 400", s == 400, (s, b))
s, b, _ = post_ret("giao1", 1, A_PK, "abc")
ok("S2 qty chữ -> 400", s == 400, (s, b))
s, b, _ = post_ret("giao1", 1, A_PK, "1.2345")
ok("S2 qty 4 chữ số thập phân -> 400", s == 400, (s, b))
s, b, _ = post_ret("giao1", 1, A_PK, "1e2")
ok("S2 qty '1e2' (ký hiệu mũ = 100 kg) vẫn bị chặn vượt số đã giao", s == 400 and code_of(b) == "RETURN_QTY_EXCEEDS", (s, b))
for weird in ("NaN", "Infinity", "-0", " ", "1,5"):
    s, b, _ = post_ret("giao1", 1, A_PK, weird)
    ok(f"S2 qty lạ {weird!r} -> 400, không 500", s == 400, (s, b))
s, b, _ = post_ret("giao1", 1, A_PK, "10.001")
ok("S2 vượt 10.001 > 10 -> 400 RETURN_QTY_EXCEEDS, kèm delivered/already", s == 400 and code_of(b) == "RETURN_QTY_EXCEEDS" and b.get("delivered_qty") and b.get("already_returned_qty") is not None, (s, b))
s, b, _ = post_ret("giao1", 1, B_PK, "1")
ok("S2 lô không thuộc phiếu -> 400 RETURN_BATCH_NOT_IN_NOTE", s == 400 and code_of(b) == "RETURN_BATCH_NOT_IN_NOTE", (s, b))
s, b, _ = post_ret("giao1", 7, A_PK, "1")
ok("S2 phiếu READY (chưa đi giao) -> 400 RETURN_NOTE_STATUS", s == 400 and code_of(b) == "RETURN_NOTE_STATUS", (s, b))
s, b, _ = post_ret("giao1", 8, A_PK, "1")
ok("S2 phiếu COMPLETED -> 400 RETURN_NOTE_STATUS", s == 400 and code_of(b) == "RETURN_NOTE_STATUS", (s, b))
s, b, _ = post_ret("giao1", 3, A_PK, "1")
ok("S2 giao1 tạo hàng hoàn cho phiếu của giao2 -> 404", s == 404, (s, b))
s, b, _ = post_ret("giao1", 999999, A_PK, "1")
ok("S2 phiếu không tồn tại -> 404 (giống phiếu người khác)", s == 404, (s, b))
s, b, _ = post_ret("giao1", 1, 999999, "1")
ok("S2 lô không tồn tại -> 400/404 không 500", s in (400, 404), (s, b))
s, b, _ = call("giao1", "POST", "inventory/returns/", {"delivery_note": 1, "batch": A_PK})
ok("S2 thiếu qty -> 400", s == 400, (s, b))
s, b, _ = post_ret(None, 1, A_PK, "1")
ok("S2 chưa đăng nhập -> 401", s == 401, s)
s, b, _ = post_ret("cs1", 1, A_PK, "1")
ok("S2 cs1 (CSKH thuần) tạo -> 403", s == 403, (s, b))
s, b, _ = post_ret("ql1", 1, A_PK, "1")
ok("S2 ql1 (Quản lý) tạo -> 403 (quyết định #21: chưa có add_returntostock)", s == 403, (s, b))
s, b, _ = post_ret("loc", 6, A_PK, "1")
loc_can_create = s
print("INFO loc tạo hàng hoàn ->", s, str(b)[:120])
n_before = db("select count(*) from inventory_returntostock")[0][0]
ok("S2 chưa phiếu hoàn rác sau các ca lỗi (chỉ phiếu loc nếu loc được tạo)", n_before == (1 if loc_can_create == 201 else 0), n_before)

# ---- 3. Hợp lệ: giao1 tự tạo, kg biên, tổng đúng bằng số giao ----
s, b, h = post_ret("giao1", 1, A_PK, "3")
ok("S3 giao1 tự tạo hàng hoàn 3 kg -> 201, Chờ duyệt, PENDING", s == 201 and b["status"] == "DRAFT" and b["decision"] == "PENDING", (s, b))
first_id = b.get("id")
ok("S3 người tạo = giao1; giờ về do hệ thống ghi (không nhận từ client)", b.get("created_by_name") and b.get("returned_at"), b)
s, b2, _ = call("giao1", "POST", "inventory/returns/", {"delivery_note": 1, "batch": A_PK, "qty": "1", "returned_at": "2020-01-01T00:00:00Z", "status": "APPROVED", "decision": "RESTOCK", "created_by": 1})
ok("S3 client gửi status/decision/returned_at/created_by -> bị từ chối hoặc bỏ qua (không tự duyệt)", (s == 400) or (s == 201 and b2["status"] == "DRAFT" and b2["decision"] == "PENDING" and not b2["returned_at"].startswith("2020")), (s, b2))
if s == 201:
    extra_id = b2["id"]
else:
    extra_id = None
st, dd, _ = call("giao1", "GET", "delivery/notes/1/")
rq = dd["lines"][0]["returned_qty"]
ok("S3 returned_qty trên phiếu giao khớp: 3.000 (+1.000 nếu ca trên nhận) ", rq in ("3.000", "4.000"), rq)
remaining = 10 - float(rq)
s, b, _ = post_ret("giao1", 1, A_PK, f"{remaining + 0.001:.3f}")
ok("S3 vượt đúng 0,001 kg so với phần còn lại -> 400", s == 400 and code_of(b) == "RETURN_QTY_EXCEEDS", (s, b))
s, b, _ = post_ret("giao1", 1, A_PK, f"{remaining:.3f}")
ok("S3 đúng phần còn lại (lô cuối) -> 201", s == 201, (s, b))
s, b, _ = post_ret("giao1", 1, A_PK, "0.001")
ok("S3 hết phần còn lại, thêm 0,001 kg -> 400", s == 400 and code_of(b) == "RETURN_QTY_EXCEEDS", (s, b))
st, dd, _ = call("giao1", "GET", "delivery/notes/1/")
ok("S3 returned_qty = 10.000 sau khi hoàn hết", dd["lines"][0]["returned_qty"] == "10.000", dd["lines"][0])

# ---- 4. Phạm vi xem ----
s, lst, h = call("giao1", "GET", "inventory/returns/")
ids1 = [r["id"] for r in lst["results"]] if s == 200 else None
ok("S4 giao1 liệt kê: không có phiếu của giao2 (phiếu giao 3)", s == 200 and all(r["delivery_note"] != 3 for r in lst["results"]), ids1)
s, lst2, _ = call("giao2", "GET", "inventory/returns/")
ok("S4 giao2 (không có phiếu hoàn) -> rỗng", s == 200 and lst2["count"] == 0, lst2)
s, g, _ = call("giao2", "GET", f"inventory/returns/{first_id}/")
ok("S4 giao2 mở phiếu hoàn của giao1 -> 404", s == 404, (s, g))
s, g, _ = call("giao2", "PATCH", f"inventory/returns/{first_id}/", {"note": "x"})
ok("S4 giao2 PATCH phiếu của giao1 -> 404/403 (không sửa được)", s in (403, 404), (s, g))
s, g, _ = call("giao2", "POST", f"inventory/returns/{first_id}/approve/", {"decision": "RESTOCK"})
ok("S4 giao2 duyệt phiếu của giao1 -> 403/404", s in (403, 404), (s, g))
s, g, _ = call("giao2", "GET", f"guidance/return/{first_id}/")
ok("S4 giao2 xem dòng thời gian phiếu của giao1 -> 404/403 (không lộ)", s in (403, 404), (s, str(g)[:200]))
for u in ("loc", "ql1", "kho1"):
    s, l, _ = call(u, "GET", "inventory/returns/")
    ok(f"S4 {u} thấy phiếu của mọi người", s == 200 and l["count"] >= 2, (s, l.get("count") if isinstance(l, dict) else l))
s, l, _ = call("cs1", "GET", "inventory/returns/")
ok("S4 cs1 (CSKH thuần) -> 403", s == 403, (s, l))
s, l, _ = call("cs2", "GET", "inventory/returns/")
ok("S4 cs2 (CSKH + giao hàng) -> 200, rỗng (chỉ phiếu của mình)", s == 200 and l["count"] == 0, (s, l))
s, l, _ = call(None, "GET", "inventory/returns/")
ok("S4 chưa đăng nhập -> 401", s == 401, s)
for bad in ("status=XYZ", "month=2026-13", "month=abc", "page=999", "page=abc", "page=0"):
    s, l, _ = call("kho1", "GET", "inventory/returns/?" + bad)
    ok(f"S4 tham số lọc xấu '{bad}' không gây 500", s < 500, (s, str(l)[:200]))
for bad in ("abc", "0", "99999999999999999999", "-1"):
    s, l, _ = call("kho1", "GET", f"inventory/returns/{bad}/")
    ok(f"S4 id xấu '{bad}' -> 404, không 500", s in (404, 400), (s, str(l)[:120]))

# ---- 5. Dữ liệu cá nhân / giá vốn trong JSON hàng hoàn ----
s, one, h = call("kho1", "GET", f"inventory/returns/{first_id}/")
ok("S5 JSON phiếu hoàn không có tên/SĐT/địa chỉ khách", pii_in(one) == [], pii_in(one))
ok("S5 JSON phiếu hoàn không có giá vốn", not re.search(r"123457|unit_cost|purchase_rate|landed|cost|amount|rate", json.dumps(one)), one)
ok("S5 Cache-Control no-store ở phản hồi hàng hoàn (note là chữ tự do)", "no-store" in h.get("Cache-Control", ""), h.get("Cache-Control"))
ok("S5 danh sách hàng hoàn: các khoá khai tường minh (không có field lạ)", set(one) == {"id", "code", "delivery_note", "delivery_note_code", "order_code", "batch", "batch_code", "item_name", "qty", "left_warehouse_at", "returned_at", "outside_minutes", "decision", "decision_label", "status", "status_label", "created_by", "created_by_name", "approved_by", "approved_by_name", "created_at", "note"}, sorted(one))
for u in ("kho1", "giao1"):
    s, tl, _ = call(u, "GET", f"guidance/return/{first_id}/")
    ok(f"S5 dòng thời gian của phiếu hoàn ({u}) không chứa tên/SĐT/địa chỉ khách", s == 200 and pii_in(tl) == [], (s, pii_in(tl) if s == 200 else tl))
    ok(f"S5 dòng thời gian ({u}) không chứa giá vốn", s == 200 and not re.search(r"123457|unit_cost|purchase_rate", json.dumps(tl)), s)
# ghi chú có SĐT qua API (FE chặn, BE?)
s, b, _ = post_ret("kho1", 4, A_PK, "1", note_text="Khách hẹn gọi 0900000777 buổi sáng")
phone_note_id = b.get("id") if s == 201 else None
print("INFO BE nhận ghi chú có SĐT khi gọi thẳng API:", s)
ok("S5 [B1 đã sửa] ghi chú có SĐT gọi thẳng API -> 400, khoá note, không lộ SĐT trong phản hồi", s == 400 and "note" in (b if isinstance(b, dict) else {}) and "0900000777" not in json.dumps(b), (s, b))
for variant in ("gọi 0900 000 777", "stk 0900.000.777", "+84 900 000 777", "84900000777", "số 0900-000-777"):
    s2_, b2_, _ = post_ret("kho1", 4, A_PK, "1", note_text=variant)
    ok(f"S5 BE chặn biến thể SĐT {variant!r}", s2_ == 400, (s2_, b2_))
ok("S5 các lần bị chặn không để lại phiếu nào có SĐT trong DB", db("select count(*) from inventory_returntostock where note like '%0900%000%777%' or note like '%84900000777%'")[0][0] == 0)
for okay in ("Mua 2 kg lúc 14h30", "xe hỏng giữa đường 12km"):
    s2_, b2_, _ = post_ret("kho1", 4, A_PK, "0.001", note_text=okay)
    ok(f"S5 ghi chú thường {okay!r} không bị chặn nhầm", s2_ == 201, (s2_, b2_))
s2_, b2_, _ = call("loc", "PATCH", f"inventory/returns/{b2_.get('id', 0)}/", {"note": "gọi 0900000777"}) if isinstance(b2_, dict) and b2_.get("id") else (0, {}, None)
ok("S5 PATCH ghi chú có SĐT cũng không lọt (400 hoặc 403)", s2_ in (400, 403), s2_)
al = db("select action, changes, note from accounts_auditlog where note like ? or changes like ?", "%0900000777%", "%0900000777%")
ok("S5 SĐT trong ghi chú không lọt vào AuditLog", not al, al)

# ---- 6. Duyệt ----
s, b, _ = post_ret("giao1", 4, A_PK, "2.5", note_text="xe hỏng")
rid_restock = b["id"]
s, b, _ = post_ret("giao1", 5, A_PK, "2")
rid_writeoff = b["id"]
s, b, _ = post_ret("giao1", 6, A_PK, "1")
rid_stale = b["id"]
for u, want in (("kho1", 403), ("giao1", 403), ("cs1", 403), ("cs2", 403), (None, 401)):
    s, b, _ = call(u, "POST", f"inventory/returns/{rid_restock}/approve/", {"decision": "RESTOCK"})
    ok(f"S6 {u or 'chưa đăng nhập'} duyệt -> {want} (AC5)", s == want, (s, b))
s, b, _ = call("ql1", "POST", f"inventory/returns/{rid_restock}/approve/", {})
ok("S6 duyệt không chọn quyết định -> 400 RETURN_DECISION_REQUIRED", s == 400 and code_of(b) == "RETURN_DECISION_REQUIRED", (s, b))
s, b, _ = call("ql1", "POST", f"inventory/returns/{rid_restock}/approve/", {"decision": "PENDING"})
ok("S6 quyết định PENDING -> 400", s == 400, (s, b))
s, b, _ = call("ql1", "POST", f"inventory/returns/{rid_restock}/approve/", {"decision": "hack"})
ok("S6 quyết định lạ -> 400", s == 400, (s, b))
ok("S6 các ca lỗi trên không đổi trạng thái phiếu", db("select status, decision from inventory_returntostock where id=?", rid_restock)[0] == ("DRAFT", "PENDING"), db("select status, decision from inventory_returntostock where id=?", rid_restock))
before = on_hand(A_PK); led_before = len(ledger(A_PK))
s, b, _ = call("ql1", "POST", f"inventory/returns/{rid_restock}/approve/", {"decision": "RESTOCK"})
after = on_hand(A_PK); led = ledger(A_PK)
ok("S6 ql1 duyệt Tái nhập -> 200, Đã duyệt, RESTOCK", s == 200 and b["status"] == "APPROVED" and b["decision"] == "RESTOCK", (s, b))
ok("S6 tồn lô tăng đúng 2,5 kg", abs(after - before - 2.5) < 1e-6, (before, after))
ok("S6 sổ nhập xuất có dòng RETURN_RESTOCK +2.5 mới", len(led) == led_before + 1 and led[-1][0] == "RETURN_RESTOCK" and float(led[-1][1]) == 2.5, led[-2:])
ok("S6 dòng sổ ghi tham chiếu phiếu, không có tên/SĐT khách", not any(x in led[-1][3] for x in ("Khách", "0900000")), led[-1])
ok("S6 người duyệt = ql1 ghi trong phiếu", b.get("approved_by_name") != "", b.get("approved_by_name"))
s, b, _ = call("ql1", "POST", f"inventory/returns/{rid_restock}/approve/", {"decision": "RESTOCK"})
ok("S6 duyệt lần 2 cùng người -> 409 STALE_STATE", s == 409 and code_of(b) == "STALE_STATE", (s, b))
s, b, _ = call("loc", "POST", f"inventory/returns/{rid_restock}/approve/", {"decision": "WRITE_OFF"})
ok("S6 người khác duyệt lại với quyết định khác -> 409", s == 409, (s, b))
ok("S6 duyệt lần 2 không cộng tồn lần nữa", abs(on_hand(A_PK) - after) < 1e-6 and len(ledger(A_PK)) == len(led), (on_hand(A_PK), after))
s, b, _ = call("ql1", "PATCH", f"inventory/returns/{rid_restock}/", {"note": "sửa sau duyệt"})
ok("S6 ql1 sửa ghi chú phiếu đã duyệt -> bị từ chối 4xx (PATCH không có quyền)", s in (400, 403, 405), (s, b))
s, b, _ = call("loc", "PATCH", f"inventory/returns/{rid_restock}/", {"note": "sửa sau duyệt", "qty": "99"})
ok("S6 ngay cả Chủ cũng không sửa được phiếu hoàn đã duyệt (4xx)", s in (400, 403, 405), (s, b))
ok("S6 qty phiếu đã duyệt vẫn 2.500", float(db("select qty from inventory_returntostock where id=?", rid_restock)[0][0]) == 2.5)
s, b, _ = call("ql1", "PATCH", f"inventory/returns/{rid_stale}/", {"qty": "99"})
ok("S6 sửa qty phiếu Chờ duyệt -> bị từ chối 4xx", s in (400, 403, 405), (s, b))
s, b, _ = call("ql1", "DELETE", f"inventory/returns/{rid_stale}/")
ok("S6 DELETE phiếu hoàn -> 405 (chứng từ không xoá)", s == 405, (s, b))
ok("S6 phiếu vẫn còn trong DB", db("select count(*) from inventory_returntostock where id=?", rid_stale)[0][0] == 1)

before = on_hand(A_PK); led_before = len(ledger(A_PK))
s, b, _ = call("loc", "POST", f"inventory/returns/{rid_writeoff}/approve/", {"decision": "WRITE_OFF"})
led = ledger(A_PK)
ok("S6 loc duyệt Huỷ hàng, ghi lỗ -> 200, WRITE_OFF", s == 200 and b["decision"] == "WRITE_OFF" and b["status"] == "APPROVED", (s, b))
ok("S6 tồn lô KHÔNG tăng khi huỷ bỏ", abs(on_hand(A_PK) - before) < 1e-6, (before, on_hand(A_PK)))
ok("S6 sổ có dòng WRITE_OFF ghi lỗ 2 kg (qty_change 0, tham chiếu ghi kg lỗ)", len(led) == led_before + 1 and led[-1][0] == "WRITE_OFF" and "2" in led[-1][3], led[-1:])
al = db("select action, actor_id, changes from accounts_auditlog where action like '%returntostock%' or action like '%return%' order by id")
ok("S6 AuditLog có approve_returntostock (người duyệt + quyết định)", any(a[0] == "approve_returntostock" for a in al), al[-5:])
ok("S6 AuditLog không chứa SĐT/ghi chú tự do", not any("xe hỏng" in json.dumps(x, ensure_ascii=False) or "0900000" in json.dumps(x, ensure_ascii=False) for x in al), al)
ok("S6 AuditLog ghi cả return_to_warehouse khi tạo", any(a[0] == "return_to_warehouse" for a in al), [a[0] for a in al])
ok("S6 AuditLog changes không tính ngược ra giá vốn (không có số tiền)", not any(re.search(r"123457|amount|rate|cost", a[2] or "") for a in al), al[-3:])

# stale: người khác duyệt trước rồi tab cũ bấm duyệt
s, b, _ = call("ql1", "POST", f"inventory/returns/{rid_stale}/approve/", {"decision": "RESTOCK"})
s2, b2, _ = call("loc", "POST", f"inventory/returns/{rid_stale}/approve/", {"decision": "RESTOCK"})
ok("S6 màn cũ: người thứ hai duyệt sau -> 409", s == 200 and s2 == 409, (s, s2, b2))

# ---- 7. Duyệt Tái nhập vào lô đã chốt ----
s, b, _ = post_ret("giao1", 9, B_PK, "1")
rid_closed = b["id"]
# mô phỏng lô B đã chốt (đặt trạng thái bằng SQL trên DB tạm) rồi duyệt Tái nhập
c = sqlite3.connect(DB); c.execute("update inventory_batch set status='CLOSED' where id=?", (B_PK,)); c.commit(); c.close()
bb = on_hand(B_PK); lb = len(ledger(B_PK))
s, b, _ = call("ql1", "POST", f"inventory/returns/{rid_closed}/approve/", {"decision": "RESTOCK"})
ok("S7 duyệt Tái nhập vào lô đã chốt -> bị từ chối 4xx (BR-HV-04), không 500", s in (400, 409, 422), (s, b))
ok("S7 lô đã chốt: tồn không đổi, sổ không thêm dòng, phiếu vẫn Chờ duyệt", abs(on_hand(B_PK) - bb) < 1e-9 and len(ledger(B_PK)) == lb and db("select status from inventory_returntostock where id=?", rid_closed)[0][0] == "DRAFT")
s, b, _ = post_ret("giao1", 2, B_PK, "1")
ok("S7 tạo hàng hoàn vào lô đã chốt -> 400 RETURN_BATCH_CLOSED (lần 2, sau sửa B4)", s == 400 and isinstance(b, dict) and b.get("code") == "RETURN_BATCH_CLOSED", (s, b))
ok("S7 tạo vào lô đã chốt bị chặn thì không có phiếu mới nào (DB)", db("select count(*) from inventory_returntostock where delivery_note_id=2 and batch_id=?", B_PK)[0][0] == 0)
c = sqlite3.connect(DB); c.execute("update inventory_batch set status='ACTIVE' where id=?", (B_PK,)); c.commit(); c.close()

# ---- 8. Hai yêu cầu đồng thời (SQLite có thể khoá DB: chỉ ghi nhận) ----
res = []
def worker(user, note, qty):
    res.append(post_ret(user, note, A_PK, qty)[0])
# phiếu 2 (giao1; lô A 5kg): hai request 3 kg cùng lúc
ths = [threading.Thread(target=worker, args=("giao1", 2, "3")) for _ in range(2)]
[t.start() for t in ths]; [t.join() for t in ths]
print("INFO đồng thời 2 x 3 kg vào phiếu 5 kg ->", sorted(res))
tot = db("select coalesce(sum(qty),0) from inventory_returntostock where delivery_note_id=2 and batch_id=?", A_PK)[0][0]
ok("S8 hai POST 3 kg đồng thời vào phiếu 5 kg: tổng đã ghi nhận không vượt 5 kg", float(tot) <= 5.0 + 1e-9, (sorted(res), tot))

# phiếu giao nhiều lô: returned_qty từng lô độc lập
st, dd, _ = call("giao1", "GET", "delivery/notes/2/")
rets = {l["batch_pk"]: l["returned_qty"] for l in dd["lines"]}
ok("S8b phiếu nhiều lô: returned_qty từng lô độc lập (A có 3 kg do đồng thời; B 0 kg vì ca S7 tạo vào lô đã chốt nay bị BE chặn)", float(rets.get(A_PK, 0)) in (0.0, 3.0) and rets.get(B_PK) == "0.000", rets)

n_fail = sum(1 for _, c in R if not c)
print(f"\nTỔNG {len(R)} ca, {len(R) - n_fail} đạt, {n_fail} lỗi")
sys.exit(1 if n_fail else 0)
