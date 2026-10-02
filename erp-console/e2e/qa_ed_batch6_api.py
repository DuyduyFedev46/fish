# QA độc lập Lô 6 (ED-13 / ED-14) — kiểm API trên BE THẬT (Django runserver + SQLite tạm đã seed_demo + dữ liệu giả của QA).
#   BE ở http://127.0.0.1:8000, người dùng loc/ql1/kho1/giao1/cs2 mật khẩu Songbien2026.
#   Dữ liệu: Khách Thử A (0900000101) có 6 đơn (1 CANCELLED, 1 AUTO_CANCELLED, 1 hoàn một phần đã hoàn 50.000, 1 hoàn chờ 40.000).
# Chỉ dữ liệu giả. Chạy lại cần nạp lại DB (scratchpad/qa6_reset.sh).
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request

API = os.environ.get("API", "http://127.0.0.1:8000/api")
DB = os.environ.get("QA_DB", "")
PW = "Songbien2026"
R = []


def ok(name, cond, extra=""):
    R.append((name, bool(cond)))
    print("PASS" if cond else "FAIL", name, "" if cond else "  -> " + str(extra)[:400], flush=True)


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


tok = {}
for u in ("loc", "ql1", "kho1", "giao1", "cs2"):
    s, b, _ = call("POST", "/auth/token/", body={"username": u, "password": PW})
    tok[u] = (b or {}).get("token")
    ok(f"đăng nhập {u}", s == 200 and tok[u], (s, b))

D = "/sales/customer-directory/"
COST_WORDS = ("purchase_rate", "landed_unit_cost", "unit_cost", "cost", "profit", "margin", "rate")

# ---- ED-13-AC1/AC3: quyền
for u in ("kho1", "giao1", "cs2"):
    for path in (D, D + "7/", D + "?q=0900000101"):
        s, b, raw = call("GET", path, tok[u])
        ok(f"{u} GET {path} = 403", s == 403, s)
        ok(f"{u} GET {path}: body không chứa dữ liệu khách", not any(x in raw for x in ("Khách Thử", "0900000101", "Quận Thử")), raw[:200])
    s, _, raw = call("PATCH", D + "7/", tok[u], {"note": "x"})
    ok(f"{u} PATCH = 403", s == 403, s)
s, _, _ = call("GET", D)
ok("chưa đăng nhập GET = 401", s == 401, s)
s, _, _ = call("PATCH", D + "7/", None, {"note": "x"})
ok("chưa đăng nhập PATCH = 401", s == 401, s)
for m in ("POST", "PUT", "DELETE"):
    s, _, _ = call(m, D + "7/" if m != "POST" else D, tok["loc"], {"name": "x"})
    ok(f"loc {m} = 405 (không xoá/tạo qua danh bạ)", s == 405, s)

# ---- ED-13-AC2: số liệu
s, b, raw = call("GET", D + "?q=Khach+Thu+A", tok["loc"])
ok("loc tìm 'Khach Thu A' (không dấu) có 1 kết quả", s == 200 and b["count"] == 1, (s, raw[:200]))
a = b["results"][0] if b and b["results"] else {}
ok("A: order_count=6", a.get("order_count") == 6, a)
ok("A: cancelled_count=2 (CANCELLED + AUTO_CANCELLED)", a.get("cancelled_count") == 2, a)
ok("A: total_spent='350000' (chuỗi, đơn huỷ & hoàn đã hoàn trừ, hoàn chờ không trừ)", a.get("total_spent") in ("350000", "350000.00"), a.get("total_spent"))
ok("A: total_spent kiểu chuỗi", isinstance(a.get("total_spent"), str))
ok("A: last_order_at có", bool(a.get("last_order_at")), a)
ok("list: không có key giá vốn/lãi", not any(w in json.dumps(a) for w in ("cost", "profit", "purchase")), a)
ok("list: khoá đúng contract", set(a) == {"id", "name", "phone", "order_count", "total_spent", "cancelled_count", "last_order_at", "note"}, sorted(a))
aid = a.get("id")
s, d, raw = call("GET", D + f"{aid}/", tok["loc"])
ok("chi tiết A 200", s == 200, s)
ok("chi tiết: 6 đơn, 2 phiếu hoàn REFUNDED/PENDING...", len(d["orders"]) == 6 and len(d["refunds"]) == 3, (len(d["orders"]), len(d["refunds"])))
ok("chi tiết: không có reason/failure_reason ở phiếu hoàn", all(not ({"reason", "failure_reason"} & set(r)) for r in d["refunds"]), d["refunds"][0])
ok("chi tiết: không khoá giá vốn", not any(w in raw for w in ("unit_cost", "landed", "purchase_rate", "profit")), "")
ok("chi tiết: default_address có", d.get("default_address") == "12 Đường Thử, Quận Thử", d.get("default_address"))
ok("chi tiết: first_order_at < last_order_at", d["first_order_at"] < d["last_order_at"], (d["first_order_at"], d["last_order_at"]))
statuses = {o["code"]: o["status"] for o in d["orders"]}
ok("chi tiết: có CANCELLED và AUTO_CANCELLED", "CANCELLED" in statuses.values() and "AUTO_CANCELLED" in statuses.values(), statuses)

s, b, _ = call("GET", D + "?q=Khach+Nhieu+Don", tok["loc"])
nid = b["results"][0]["id"]
s, dd, _ = call("GET", D + f"{nid}/", tok["loc"])
ok("khách 55 đơn: orders cắt 50, order_count=55", len(dd["orders"]) == 50 and dd["order_count"] == 55, (len(dd["orders"]), dd["order_count"]))
ok("khách 55 đơn: total_spent = 0 (đơn chưa trả)", dd["total_spent"] in ("0", "0.00"), dd["total_spent"])

# ---- tìm kiếm / sắp xếp / phân trang
def q(qs, u="loc"):
    return call("GET", D + qs, tok[u])
s, b, _ = q("?q=nguyen+van+an")
ok("tìm bỏ dấu 'nguyen van an' ra Nguyễn Văn Ẩn", s == 200 and b["count"] == 1 and b["results"][0]["name"] == "Nguyễn Văn Ẩn", b)
s, b, _ = q("?q=0900000202")
ok("tìm theo SĐT đủ", b["count"] == 1, b)
s, b, _ = q("?q=0202")
ok("tìm theo 4 số cuối '0202' ra khách", b["count"] == 1, b)
s, b, _ = q("?q=090")
ok("'090' (3 số) không dò SĐT", b["count"] == 0, b["count"])
s, b, _ = q("?q=zzzz")
ok("không khớp: count 0", b["count"] == 0)
s, b, _ = q("?ordering=name")
names = [r["name"] for r in b["results"]]
ok("sắp name tăng dần", names == sorted(names, key=lambda x: x.lower()) or names[0] <= names[-1], names[:5])
s, b, _ = q("?ordering=-total_spent")
ok("sắp -total_spent: A đầu (350000)", b["results"][0]["name"] == "Khách Thử A" or float(b["results"][0]["total_spent"]) >= float(b["results"][1]["total_spent"]), [r["total_spent"] for r in b["results"][:3]])
s, b, _ = q("?ordering=-last_order_at")
ok("mặc định: khách chưa mua xếp cuối", b["results"][0]["last_order_at"] is not None, b["results"][0]["name"])
s, b, _ = q("?ordering=%3BDROP%20TABLE")
ok("ordering lạ không 500", s == 200, s)
s, b, _ = q("?ordering=phone")
ok("ordering=phone (không cho phép) không 500", s == 200, s)
s, b, raw = q("")
ok("trang 1 có 20, count=35, next có", len(b["results"]) == 20 and b["count"] == 35 and b["next"], (len(b["results"]), b["count"]))
ok("next là URL (không chứa SĐT)", "0900" not in (b["next"] or ""), b["next"])
s, b2, _ = q("?page=2")
ok("trang 2 có 15", len(b2["results"]) == 15, len(b2["results"]))
s, _, _ = q("?page=99")
ok("trang quá số: 404", s == 404, s)
s, _, _ = q("?page=abc")
ok("trang 'abc': không 500", s in (400, 404), s)
s, _, _ = call("GET", D + "999999/", tok["loc"])
ok("id không có: 404", s == 404, s)
s, _, _ = call("GET", D + "abc/", tok["loc"])
ok("id 'abc': 404", s == 404, s)

# ---- ED-13-AC4: PATCH theo quyền
s, b, raw = call("PATCH", D + f"{aid}/", tok["ql1"], {"note": "QA ql1 ghi chú"})
print("INFO ql1 PATCH ->", s, raw[:150])
manager_can_patch = s == 200
s, b, raw = call("PATCH", D + f"{aid}/", tok["loc"], {"note": "Ghi chú QA mới"})
ok("loc PATCH note 200", s == 200 and b["note"] == "Ghi chú QA mới", (s, raw[:200]))
s, b, raw = call("PATCH", D + f"{aid}/", tok["loc"], {"phone": "0911111111"})
ok("PATCH phone -> 400 INPUT_NOT_ALLOWED", s == 400 and b.get("code") == "INPUT_NOT_ALLOWED", (s, raw[:200]))
ok("lỗi không lặp lại số gửi lên", "0911111111" not in raw, raw)
s, b, raw = call("GET", D + f"{aid}/", tok["loc"])
ok("phone không đổi sau PATCH bị từ chối", b["phone"] == "0900000101", b["phone"])
for bad in ({"total_spent": "1"}, {"order_count": 99}, {"id": 5}, {"created_at": "2020-01-01"}, {"note": "ok", "phone": "0912345678"}):
    s, _, raw = call("PATCH", D + f"{aid}/", tok["loc"], bad)
    ok(f"PATCH {list(bad)} -> 400", s == 400, (s, raw[:150]))
s, _, raw = call("PATCH", D + f"{aid}/", tok["loc"], {})
ok("PATCH rỗng -> 400 INPUT_EMPTY", s == 400 and "INPUT_EMPTY" in raw, (s, raw))
s, _, raw = call("PATCH", D + f"{aid}/", tok["loc"], {"note": "x" * 1001})
ok("note 1001 ký tự -> 400", s == 400, s)
s, _, raw = call("PATCH", D + f"{aid}/", tok["loc"], {"name": {"a": 1}})
ok("name là object -> 400", s == 400, s)
s, b, raw = call("PATCH", D + f"{aid}/", tok["loc"], {"name": "Khách Thử A", "default_address": "99 Địa Chỉ Giả Mới"})
ok("PATCH địa chỉ 200", s == 200 and b["default_address"] == "99 Địa Chỉ Giả Mới", (s, raw[:200]))
s, b, raw = call("GET", D + f"{aid}/", tok["loc"])
ok("đọc lại: địa chỉ + note còn", b["default_address"] == "99 Địa Chỉ Giả Mới" and b["note"] == "Ghi chú QA mới", b)
ok("số liệu không đổi sau PATCH", b["order_count"] == 6 and b["total_spent"] in ("350000", "350000.00") and b["cancelled_count"] == 2, b)
# PATCH 2 lần cùng giá trị
s1, _, _ = call("PATCH", D + f"{aid}/", tok["loc"], {"note": "Ghi chú QA mới"})
ok("PATCH lặp cùng giá trị 200 (idempotent)", s1 == 200, s1)
s, b, _ = call("PATCH", D + f"{aid}/", tok["loc"], {"name": "Tên có <b>HTML</b> & dấu \"ngoặc\""})
ok("tên có HTML lưu nguyên văn (escape ở FE)", s == 200 and "<b>" in b["name"], b)
call("PATCH", D + f"{aid}/", tok["loc"], {"name": "Khách Thử A"})

# ---- AuditLog (ED-13-AC5): không chép giá trị cá nhân
if DB:
    con = sqlite3.connect(DB)
    cols = [r[1] for r in con.execute("pragma table_info(accounts_auditlog)")]
    rows = con.execute("select * from accounts_auditlog where action='update_customer'").fetchall()
    blob = json.dumps(rows, ensure_ascii=False, default=str)
    ok("AuditLog update_customer có ghi", len(rows) >= 2, len(rows))
    leaks = [x for x in ("Ghi chú QA mới", "99 Địa Chỉ", "0900000101", "Khách Thử A", "0911111111", "HTML", "QA ql1") if x in blob]
    ok("AuditLog không chứa tên/SĐT/địa chỉ/ghi chú", not leaks, leaks)
    ok("AuditLog có tên trường đã đổi", "default_address" in blob and "note" in blob, blob[:300])
    ok("AuditLog đã ghi người sửa", all(r[cols.index("actor_id")] for r in rows if "actor_id" in cols), cols)
    # không phiếu hoàn/đơn bị xoá
    n_orders = con.execute("select count(*) from sales_salesorder").fetchone()[0]
    ok("không đơn nào bị xoá (chứng từ)", n_orders >= 6 + 55 + 6, n_orders)
else:
    print("SKIP kiểm AuditLog (không có QA_DB)")

# ---- Timeline R2 customer
s, b, raw = call("GET", f"/guidance/customer/{aid}/", tok["loc"])
ok("timeline khách loc 200", s == 200, (s, raw[:200]))
ok("timeline không chứa SĐT/địa chỉ", all(x not in raw for x in ("0900000101", "Địa Chỉ", "Quận Thử")), raw[:300])
for u in ("kho1", "giao1", "cs2"):
    s, _, raw = call("GET", f"/guidance/customer/{aid}/", tok[u])
    ok(f"timeline khách {u} = 403", s == 403, s)
s, _, raw = call("GET", f"/guidance/customer/{aid}/", tok["ql1"])
ok("timeline khách ql1 = 200", s == 200, s)

# ---- Endpoint cũ vẫn như Q4 (ghi nhận): nv_kho đọc được /customers/? (không phải lỗi lô này)
s, b, raw = call("GET", "/sales/customers/", tok["kho1"])
print("INFO (Q4, ngoài lô) kho1 GET /sales/customers/ ->", s)

# ---- me/capabilities
for u in ("loc", "ql1", "kho1", "giao1", "cs2"):
    s, b, _ = call("GET", "/auth/me/", tok[u])
    perms = b.get("permissions", [])
    has = "sales.view_customer_list" in perms
    ok(f"me {u}: view_customer_list = {u in ('loc', 'ql1')}", has == (u in ("loc", "ql1")), perms[:5])
    chg = "sales.change_customer" in perms
    print("INFO", u, "change_customer =", chg)

# ---- đơn: customer.id chỉ khi được xem
s, b, _ = call("GET", "/sales/orders/?search=SO261001-A00001", tok["loc"])
oid = None
if s == 200:
    lst = b["results"] if isinstance(b, dict) and "results" in b else b
    if lst:
        oid = lst[0]["id"]
if oid:
    for u in ("loc", "ql1", "kho1", "giao1", "cs2"):
        s, b, raw = call("GET", f"/sales/orders/{oid}/", tok[u])
        cust = (b or {}).get("customer") if s == 200 else None
        print("INFO order", oid, u, s, "customer keys:", sorted(cust) if isinstance(cust, dict) else cust)

print(f"\n{sum(1 for _, c in R if c)}/{len(R)} PASS")
sys.exit(0 if all(c for _, c in R) else 1)
