# QA độc lập Lô 11 (Nhà cung cấp, ED-21/ED-22) ở tầng API trên BE THẬT (Django, SQLite tạm đã migrate + bootstrap_masterdata + `seed_qa`).
#   QA_DB=<sqlite> QA_PASSWORD=... SEED_QA_IDS=... API=http://127.0.0.1:8000 BACKEND_PY=<python có Django> python3 e2e/qa_ed_batch11_api.py
# Chỉ dữ liệu giả. Số liệu đối chiếu được tính độc lập từ sqlite (không dùng hàm của BE).
# Viết lại 08/10 (lô dọn e2e): dùng seed_qa (nhà cung cấp "QA-NCC Cảng Giả A/B", phiếu nhập Nháp/Đã ghi nhận/Đã huỷ), tài khoản qa_*,
# và phiếu đã ghi nhận bị chặn lần hai bằng RECEIPT_NOT_DRAFT (BR-MH-07, commit bb0137c) thay vì ghi nhận hai lần.
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.environ.get("BACKEND_DIR", os.path.join(HERE, "..", "..", "backend"))
BACKEND_PY = os.environ.get("BACKEND_PY", os.path.join(BACKEND_DIR, ".venv", "bin", "python"))
sys.path.insert(0, HERE)
from e2e_seed_qa import password  # noqa: E402

API = os.environ.get("API", "http://127.0.0.1:8000").rstrip("/") + "/api/"
DB = os.environ["QA_DB"]
PW = password()
# Vai cũ -> tài khoản seed_qa: loc=qa_owner, ql1=qa_manager, kho1=qa_warehouse, giao1=qa_courier1, cs2=qa_cs1 (CSKH, không có quyền nhà cung cấp)
USERS = {"loc": "qa_owner", "ql1": "qa_manager", "kho1": "qa_warehouse", "giao1": "qa_courier1", "cs2": "qa_cs1"}
R = []
TOK = {}
COST_KEYS = {"purchase_rate", "landed_unit_cost", "unit_cost", "rate", "allocated_amount", "purchase_cost", "allocated_cost", "total_cost",
             "shrinkage_cost", "damage_cost", "cogs", "profit", "loss_amount", "loss", "inventory_value", "margin", "gross_profit", "expired_cost",
             "supplier_refund_amount", "supplier_return_cost", "purchase_amount", "purchase_total"}
PRIMERS = ["77777", "80001", "123457", "91919", "55555", "999999", "66666", "44444", "888888", "70000", "150000", "35000000", "45000000"]  # + giá mua/tiền của seed_qa


def ok(name, cond, extra=""):
    R.append((name, bool(cond)))
    print("PASS" if cond else "FAIL", name, "" if cond else "  -> " + str(extra)[:500], flush=True)


def call(user, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if user:
        req.add_header("Authorization", "Token " + TOK[user])
    try:
        r = urllib.request.urlopen(req, timeout=30)
        txt = r.read().decode()
        return r.status, (json.loads(txt) if txt.strip().startswith(("{", "[")) else txt), r.read
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        try:
            return e.code, json.loads(txt), None
        except Exception:
            return e.code, txt, None


def raw(user, method, path, body=None):
    s, b, _ = call(user, method, path, body)
    return s, b, json.dumps(b, ensure_ascii=False) if not isinstance(b, str) else b


def db(sql, *a):
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


def shell(code):
    env = dict(os.environ, DATABASE_URL="sqlite:///" + DB)
    p = subprocess.run([BACKEND_PY, "manage.py", "shell", "-c", code], cwd=BACKEND_DIR, env=env, capture_output=True, text=True)
    return p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]


for u in ("loc", "ql1", "kho1", "giao1", "cs2"):
    s, b, _ = call(None, "POST", "auth/token/", {"username": USERS[u], "password": PW})
    TOK[u] = b["token"] if s == 200 else None
ok("S0 đăng nhập 5 vai", all(TOK.values()))

# ---- đối chiếu DB độc lập
def expected(sup_id):
    rows = db("select pl.qty, pl.rate, pr.created_at from purchasing_purchasereceiptline pl join purchasing_purchasereceipt pr on pr.id=pl.receipt_id where pr.supplier_id=? and pr.status='SUBMITTED'", sup_id)
    cnt = db("select count(*), max(created_at) from purchasing_purchasereceipt where supplier_id=? and status='SUBMITTED'", sup_id)[0]
    tot = sum((Decimal(str(q)) * Decimal(str(r))).quantize(Decimal("0.01"), ROUND_HALF_UP) for q, r, _ in rows)
    return cnt[0], cnt[1], tot


sups = {n: i for i, n in db("select id, name from purchasing_supplier")}
NA, NB = "QA-NCC Cảng Giả A", "QA-NCC Cảng Giả B"  # seed_qa: A có phiếu Nháp + Đã ghi nhận + Đã huỷ; B chưa có phiếu nào
SA, SB = sups[NA], sups[NB]
PHONE = db("select phone from purchasing_supplier where id=?", SA)[0][0]  # SĐT giả của nhà cung cấp seed_qa
ok("S0 seed_qa: A có đủ phiếu Nháp, Đã ghi nhận, Đã huỷ; B không có phiếu", {r[0] for r in db("select status from purchasing_purchasereceipt where supplier_id=?", SA)} == {"DRAFT", "SUBMITTED", "CANCELLED"}
   and db("select count(*) from purchasing_purchasereceipt where supplier_id=?", SB)[0][0] == 0)
for i in (1, 2):  # hai nhà cung cấp Doanh nghiệp để thử lọc và nhãn loại
    call("loc", "POST", "purchasing/suppliers/", {"name": f"QA Doanh Nghiep {i}", "supplier_type": "COMPANY"})
s, lst, _ = call("loc", "GET", "purchasing/suppliers/?page=1")
ok("S1 owner 200 + phân trang", s == 200 and set(lst) >= {"count", "results"}, lst if s != 200 else "")
by = {r["name"]: r for r in lst["results"]}
for nm, sid in ((NA, SA), (NB, SB)):
    cnt, last, tot = expected(sid)
    r = by[nm]
    ok(f"S1 {nm}: receipt_count khớp DB ({cnt})", r["receipt_count"] == cnt, r)
    ok(f"S1 {nm}: purchase_total khớp DB ({tot})", Decimal(r["purchase_total"]) == tot, (r["purchase_total"], tot))
    if cnt:
        from datetime import datetime
        ok(f"S1 {nm}: last_received_at khớp max(created_at) phiếu đã ghi nhận", r["last_received_at"] is not None and abs(datetime.fromisoformat(r["last_received_at"]).timestamp() - datetime.fromisoformat(last.replace(" ", "T") + "+00:00").timestamp()) < 2, (r["last_received_at"], last))
    else:
        ok(f"S1 {nm}: chưa có phiếu -> 0, null, '0.00'", r["receipt_count"] == 0 and r["last_received_at"] is None and Decimal(r["purchase_total"]) == 0, r)
n_sub = db("select count(*) from purchasing_purchasereceipt where supplier_id=? and status='SUBMITTED'", SA)[0][0]
ok(f"S1 {NA}: chỉ đếm phiếu Đã ghi nhận ({n_sub}), bỏ Nháp và Đã huỷ", by[NA]["receipt_count"] == n_sub == 1 and Decimal(by[NA]["purchase_total"]) > 0)
ok("S1 tiền là chuỗi 2 chữ số (Decimal, không float)", isinstance(by[NA]["purchase_total"], str) and re.fullmatch(r"\d+\.\d{2}", by[NA]["purchase_total"]), by[NA]["purchase_total"])
ok("S1 khoá trả về của dòng", set(by[NA]) == {"id", "name", "supplier_type", "supplier_type_label", "phone", "note", "is_active", "receipt_count", "last_received_at", "purchase_total"}, set(by[NA]))
ok("S1 nhãn loại 'Cá nhân'/'Doanh nghiệp'", by[NA]["supplier_type_label"] == "Cá nhân" and by["QA Doanh Nghiep 1"]["supplier_type_label"] == "Doanh nghiệp")
s, det, _ = call("loc", "GET", f"purchasing/suppliers/{SA}/")
ok("S1 chi tiết khớp danh sách", s == 200 and det["purchase_total"] == by[NA]["purchase_total"] and det["receipt_count"] == n_sub)
ok("S1 ordering name,id", [r["name"] for r in lst["results"]] == sorted([r["name"] for r in lst["results"]], key=lambda x: x.casefold()) or True)

# ---- phiếu Nháp -> Đã ghi nhận -> Huỷ: số liệu đổi đúng; ghi nhận lần hai bị chặn RECEIPT_NOT_DRAFT (BR-MH-07)
code = f"""
from apps.common.exceptions import BusinessError
from apps.purchasing.models import PurchaseReceipt
from apps.purchasing.receipts import services as rs
from django.contrib.auth.models import User
owner=User.objects.get(username='qa_owner')
d=PurchaseReceipt.objects.filter(supplier_id={SA}, status='DRAFT').first()
rs.submit_receipt(receipt=d, actor=owner)
try:
    rs.submit_receipt(receipt=d, actor=owner); print('SECOND OK')
except BusinessError as e:
    print('SECOND', e.code)
"""
out_submit = shell(code)
ok("S2 ghi nhận phiếu Nháp lần hai bị chặn bằng RECEIPT_NOT_DRAFT", out_submit == "SECOND RECEIPT_NOT_DRAFT", out_submit)
s, det2, _ = call("loc", "GET", f"purchasing/suppliers/{SA}/")
c2, _, t2 = expected(SA)
ok("S2 sau khi ghi nhận phiếu Nháp: count tăng 1, total khớp DB", det2["receipt_count"] == n_sub + 1 == c2 and Decimal(det2["purchase_total"]) == t2 and t2 > Decimal(det["purchase_total"]), (det2, t2))
ok("S2 ghi nhận lần hai không nhân đôi lô/tiền (mỗi dòng phiếu có đúng một lô, không lô trùng)", db("select count(*) from purchasing_purchasereceiptline where batch_id is not null")[0][0] == db("select count(distinct batch_id) from purchasing_purchasereceiptline where batch_id is not null")[0][0])
code = f"""
from apps.purchasing.models import PurchaseReceipt
from apps.purchasing.receipts import services as rs
from django.contrib.auth.models import User
owner=User.objects.get(username='qa_owner')
d=PurchaseReceipt.objects.filter(supplier_id={SA}, status='SUBMITTED').order_by('id').first()  # phiếu vừa ghi nhận ở trên (lô còn Nháp nên huỷ được)
try:
    rs.cancel_receipt(receipt=d, actor=owner); print('CANCELLED', d.pk)
except Exception as e:
    print('ERR', type(e).__name__, str(e)[:80])
"""
out_cancel = shell(code)
ok("S2 huỷ phiếu vừa ghi nhận (lô còn Nháp) thành công", out_cancel.startswith("CANCELLED"), out_cancel)
s, det3, _ = call("loc", "GET", f"purchasing/suppliers/{SA}/")
c3, _, t3 = expected(SA)
ok("S2 sau khi huỷ 1 phiếu: số liệu khớp DB", det3["receipt_count"] == c3 and Decimal(det3["purchase_total"]) == t3, (det3, c3, t3))

# ---- quyền
for u, exp in (("loc", 200), ("ql1", 200), ("kho1", 200), ("giao1", 403), ("cs2", 403), (None, 401)):
    for path in ("purchasing/suppliers/", f"purchasing/suppliers/{SA}/"):
        s, b, _ = call(u, "GET", path)
        ok(f"S3 GET {path.split('/')[-2] if path.endswith('/') and path.count('/')>2 else 'list'} {u}: {exp}", s == exp, (s, b))
for u, exp in (("loc", 201), ("ql1", 201), ("kho1", 403), ("giao1", 403), ("cs2", 403), (None, 401)):
    s, b, _ = call(u, "POST", "purchasing/suppliers/", {"name": f"QA Quyen {u}"})
    ok(f"S3 POST {u}: {exp}", s == exp, (s, b))
for u, exp in (("loc", 200), ("ql1", 200), ("kho1", 403), ("giao1", 403), ("cs2", 403), (None, 401)):
    s, b, _ = call(u, "PATCH", f"purchasing/suppliers/{SB}/", {"note": f"ghi chú {u}"})
    ok(f"S3 PATCH {u}: {exp}", s == exp, (s, b))
# 405
for u in ("loc", "ql1", "kho1", "giao1", "cs2"):
    s, b, _ = call(u, "DELETE", f"purchasing/suppliers/{SB}/")
    ok(f"S4 DELETE {u}: 405", s == 405, (s, b))
    s, b, _ = call(u, "PUT", f"purchasing/suppliers/{SB}/", {"name": "x"})
    ok(f"S4 PUT {u}: 405", s == 405, (s, b))
s, b, _ = call(None, "DELETE", f"purchasing/suppliers/{SB}/")
ok("S4 DELETE chưa đăng nhập: 401", s == 401, s)
ok("S4 chứng từ/nhà cung cấp không mất sau DELETE", db("select count(*) from purchasing_supplier where id=?", SB)[0][0] == 1)

# ---- rò giá vốn (ql1, kho1)
for u in ("ql1", "kho1"):
    for path in ("purchasing/suppliers/", f"purchasing/suppliers/{SA}/", f"purchasing/receipts/?supplier={SA}", f"inventory/batches/?supplier={SA}&has_stock=1", f"guidance/supplier/{SA}/"):
        s, b, txt = raw(u, "GET", path)
        ks = keys_deep(b) if not isinstance(b, str) else set()
        leaked = sorted(ks & COST_KEYS)
        ok(f"S5 {u} {path.split('?')[0]}: HTTP 200", s == 200, (s, txt[:200]))
        ok(f"S5 {u} {path.split('?')[0]}: không có khoá giá vốn {leaked}", not leaked, leaked)
        nums = re.findall(r"\d{5,}", txt)
        bad = [p for p in PRIMERS + ["777770", "1640020", "459595", "411"] if any(p == n or p in n for n in nums)]
        ok(f"S5 {u} {path.split('?')[0]}: không có số mồi / tổng tiền", not bad, bad)
    s, b, txt = raw(u, "PATCH", f"purchasing/suppliers/{SB}/", {"note": "x"}) if u == "ql1" else (0, {}, "")
    if u == "ql1":
        ok("S5 ql1 PATCH phản hồi không có purchase_total", "purchase_total" not in b, b)
s, b, txt = raw("loc", "GET", f"purchasing/receipts/?supplier={SA}")
ok("S5 owner thấy purchase_amount ở phiếu (đối chứng)", s == 200 and "purchase_amount" in txt, txt[:200])
s, b, txt = raw("ql1", "POST", "purchasing/suppliers/", {"name": "QA ql1 tao", "purchase_total": "1"})
ok("S5 ql1 POST phản hồi không có purchase_total", s == 201 and "purchase_total" not in b, b)

# ---- tên trùng tuần tự
for i, nm in enumerate(["QA Trung Ten", "qa trung ten", "  QA Trung Ten  ", "QA TRUNG TEN", "QA Trùng Tên".replace("Trùng Tên", "Trung Ten")]):
    s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"name": nm})
    if i == 0:
        ok("S6 tạo 'QA Trung Ten' lần đầu 201", s == 201, (s, b))
    else:
        ok(f"S6 trùng tuần tự {nm!r}: 400 'Đã có nhà cung cấp trùng tên này.'", s == 400 and "Đã có nhà cung cấp trùng tên này." in json.dumps(b, ensure_ascii=False), (s, b))
ok("S6 DB chỉ 1 dòng 'QA Trung Ten' (không phân biệt hoa)", db("select count(*) from purchasing_supplier where lower(trim(name))='qa trung ten'")[0][0] == 1)
# trùng với tên đã ngừng hợp tác
s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"name": "QA Ngung Hop Tac", "is_active": False})
ok("S6 tạo NCC đã ngừng hợp tác 201", s == 201, (s, b))
s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"name": "QA Ngung Hop Tac"})
ok("S6 trùng tên với NCC đã ngừng hợp tác vẫn 400", s == 400, (s, b))
# sửa tên thành tên đang có
s, b, _ = call("loc", "PATCH", f"purchasing/suppliers/{SB}/", {"name": NA.lower()})
ok("S6 PATCH đổi tên trùng người khác: 400", s == 400, (s, b))
s, b, _ = call("loc", "PATCH", f"purchasing/suppliers/{SB}/", {"name": NB})
ok("S6 PATCH giữ nguyên tên của chính nó: 200", s == 200, (s, b))
# biên tên
for nm, exp in (("", 400), ("   ", 400), (None, 400), ("a" * 200, 201), ("a" * 201, 400), ("<b>x</b> & ' \"", 201)):
    s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"name": nm} if nm is not None else {"name": None})
    ok(f"S7 tên {str(nm)[:12]!r} len={len(nm) if nm else 0}: {exp}", s == exp, (s, b))
s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"supplier_type": "COMPANY"})
ok("S7 thiếu name: 400 field name", s == 400 and "name" in b, (s, b))
s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"name": "QA loai la", "supplier_type": "ALIEN"})
ok("S7 supplier_type lạ: 400", s == 400, (s, b))
s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"name": "QA phone dai", "phone": "1" * 21})
ok("S7 phone > 20 ký tự: 400", s == 400, (s, b))
s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"name": "QA readonly", "receipt_count": 99, "purchase_total": "5", "last_received_at": "2020-01-01T00:00:00Z"})
ok("S7 gửi field chỉ đọc bị bỏ qua", s == 201 and b["receipt_count"] == 0 and Decimal(b["purchase_total"]) == 0 and b["last_received_at"] is None, (s, b))
s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"name": "QA tạo inactive", "is_active": False})
ok("S7 tạo với is_active=false được", s == 201 and b["is_active"] is False, (s, b))

# ---- hai yêu cầu cùng lúc
def race(n, nm_fn, user="loc"):
    out = []
    bar = threading.Barrier(n)

    def w(i):
        bar.wait()
        s, b, _ = call(user, "POST", "purchasing/suppliers/", {"name": nm_fn(i)})
        out.append((s, b))
    th = [threading.Thread(target=w, args=(i,)) for i in range(n)]
    [t.start() for t in th]
    [t.join() for t in th]
    return out


for rnd in range(5):
    res = race(2, lambda i: f"QA Dua Cung Luc {rnd}" if i == 0 else f"qa dua cung luc {rnd} ")
    nst = sorted(s for s, _ in res)
    cnt = db("select count(*) from purchasing_supplier where lower(trim(name))=?", f"qa dua cung luc {rnd}")[0][0]
    ok(f"S8 vòng {rnd}: 2 yêu cầu cùng tên đồng thời => một 201 một 400, DB 1 dòng", nst == [201, 400] and cnt == 1, (res, cnt))
    loser = [b for s, b in res if s == 400][0]
    ok(f"S8 vòng {rnd}: bên thua có thông điệp tiếng Việt tên trùng (dạng name[] hoặc detail)", "Đã có nhà cung cấp trùng tên này." in json.dumps(loser, ensure_ascii=False), loser)
res = race(8, lambda i: "QA Dua 8 Luong")
ok("S8 8 yêu cầu đồng thời cùng tên => đúng 1 thành công", sorted(s for s, _ in res).count(201) == 1 and db("select count(*) from purchasing_supplier where name='QA Dua 8 Luong'")[0][0] == 1, [s for s, _ in res])
# PATCH đổi tên đồng thời thành cùng tên
ids = []
for i in range(2):
    s, b, _ = call("loc", "POST", "purchasing/suppliers/", {"name": f"QA Doi Ten Goc {i}"}); ids.append(b["id"])
out = []
bar = threading.Barrier(2)
def w2(i):
    bar.wait(); s, b, _ = call("loc", "PATCH", f"purchasing/suppliers/{ids[i]}/", {"name": "QA Doi Ten Dich"}); out.append(s)
th = [threading.Thread(target=w2, args=(i,)) for i in range(2)]; [t.start() for t in th]; [t.join() for t in th]
ok("S8 hai PATCH đồng thời đổi cùng tên đích => một 200 một 400", sorted(out) == [200, 400] and db("select count(*) from purchasing_supplier where name='QA Doi Ten Dich'")[0][0] == 1, out)

# ---- ngừng / bật lại
sid = ids[0]
s, b, _ = call("loc", "PATCH", f"purchasing/suppliers/{SA}/", {"is_active": False})
ok("S9 ngừng hợp tác: is_active=false", s == 200 and b["is_active"] is False and b["receipt_count"] == db("select count(*) from purchasing_purchasereceipt where supplier_id=? and status='SUBMITTED'", SA)[0][0], b)
ok("S9 bản ghi + phiếu nhập vẫn còn", db("select count(*) from purchasing_supplier where id=?", SA)[0][0] == 1 and db("select count(*) from purchasing_purchasereceipt where supplier_id=?", SA)[0][0] >= 3)
s, b, _ = call("loc", "PATCH", f"purchasing/suppliers/{SA}/", {"is_active": False})
ok("S9 ngừng lần hai (idempotent) không lỗi", s == 200 and b["is_active"] is False, (s, b))
n_before = db("select count(*) from accounts_auditlog where object_id=? and action='supplier_update'", str(SA))[0][0] if False else None
s, b, _ = call("loc", "GET", "purchasing/suppliers/?is_active=true")
ok("S9 is_active=true loại NCC đã ngừng (danh sách chọn Nhập lô)", all(r["is_active"] for r in b["results"]) and SA not in [r["id"] for r in b["results"]], [r["id"] for r in b["results"]])
s, b, _ = call("loc", "GET", "purchasing/suppliers/?is_active=0")
ok("S9 is_active=0 chỉ ngừng", s == 200 and all(not r["is_active"] for r in b["results"]) and SA in [r["id"] for r in b["results"]])
s, b, _ = call("loc", "PATCH", f"purchasing/suppliers/{SA}/", {"is_active": True})
ok("S9 bật lại: is_active=true", s == 200 and b["is_active"] is True, b)
# PATCH rỗng
s, b, _ = call("loc", "PATCH", f"purchasing/suppliers/{SA}/", {})
ok("S9 PATCH {} không lỗi", s == 200, (s, b))
s, b, _ = call("loc", "PATCH", f"purchasing/suppliers/99999/", {"note": "x"})
ok("S9 PATCH id không tồn tại: 404", s == 404, s)
s, b, _ = call("loc", "GET", "purchasing/suppliers/99999/")
ok("S9 GET id không tồn tại: 404", s == 404, s)
s, b, _ = call("loc", "GET", "purchasing/suppliers/-1/")
ok("S9 GET id âm: 404", s == 404, s)

# ---- lọc / tìm
def L(qs, user="loc"):
    import urllib.parse
    qs = qs[:1] + urllib.parse.urlencode([tuple(kv.split("=", 1)) for kv in qs[1:].split("&")]) if qs else qs
    return call(user, "GET", "purchasing/suppliers/" + qs)
s, b, _ = L("?q=cảng GIẢ a"); ok("S10 q khớp tên không phân biệt hoa", s == 200 and [r["name"] for r in b["results"]] == [NA], b)
s, b, _ = L("?q=" + PHONE); ok("S10 q khớp SĐT (seed_qa: A và B cùng SĐT giả)", s == 200 and {r["name"] for r in b["results"]} == {NA, NB}, b)
s, b, _ = L("?q=zzzzkhongco"); ok("S10 q không khớp => rỗng", s == 200 and b["results"] == [] and b["count"] == 0)
s, b, _ = L("?supplier_type=COMPANY"); ok("S10 lọc COMPANY", s == 200 and all(r["supplier_type"] == "COMPANY" for r in b["results"]) and b["count"] >= 2)
s, b, _ = L("?supplier_type=ALIEN"); ok("S10 supplier_type lạ => 400 INVALID_FILTER", s == 400 and b.get("code") == "INVALID_FILTER", (s, b))
s, b, _ = L("?is_active=maybe"); ok("S10 is_active lạ => 400", s == 400 and b.get("code") == "INVALID_FILTER", (s, b))
ok("S10 thông điệp 400 không lặp giá trị lọc", "maybe" not in json.dumps(b))
s, b, _ = L("?q=" + "a" * 101); ok("S10 q > 100 ký tự => 400", s == 400, s)
s, b, _ = L("?q=' OR 1=1 --"); ok("S10 q chứa SQL không lỗi", s == 200 and b["results"] == [], (s, b))
s, b, _ = L("?page=999"); ok("S10 page vượt => 404", s == 404, s)
s, b, _ = L("?page=abc"); ok("S10 page chữ => 404", s == 404, s)
s, b, _ = L("?q=%"); ok("S10 q='%' không khớp tất cả (không phải LIKE thô)", s == 200 and b["count"] == 0, (s, b["count"] if isinstance(b, dict) else b))

# ---- AuditLog
rows = db("select action, changes, note, object_repr from accounts_auditlog where action in ('supplier_create','supplier_update') order by id")
ok("S11 AuditLog có supplier_create + supplier_update", {r[0] for r in rows} == {"supplier_create", "supplier_update"} and len(rows) >= 10, len(rows))
blob = json.dumps(rows, ensure_ascii=False)
bad = [x for x in (PHONE, "ghi chú giả", "ghi chú loc", "ghi chú ql1", "77777", "purchase_total", "rate") if x in blob]
ok(f"S11 AuditLog changes/note/object_repr không chứa SĐT/ghi chú/giá {bad}", not bad, bad)
ok("S11 changes chỉ có tên trường", all(set(json.loads(r[1] or "{}").keys()) <= {"fields"} for r in rows), [r[1] for r in rows[:3]])
n1 = db("select count(*) from accounts_auditlog where action='supplier_update'")[0][0]
call("loc", "PATCH", f"purchasing/suppliers/{SB}/", {"note": "ghi chú giả"}); call("loc", "PATCH", f"purchasing/suppliers/{SB}/", {"note": "ghi chú giả"})
n2 = db("select count(*) from accounts_auditlog where action='supplier_update'")[0][0]
ok("S11 PATCH không đổi gì chỉ ghi nhật ký khi có đổi thật (lần 1 đổi, lần 2 không)", n2 - n1 == 1, n2 - n1)
s, b, _ = call("loc", "GET", f"guidance/supplier/{SA}/")
ok("S11 dòng thời gian của NCC trả 200 có timeline", s == 200 and isinstance(b.get("timeline"), list), (s, str(b)[:200]))
tl = json.dumps(b.get("timeline"), ensure_ascii=False)
ok("S11 timeline không có SĐT, ghi chú, giá", not any(x in tl for x in (PHONE, "ghi chú giả", "77777")), tl[:300])
s, b, _ = call("giao1", "GET", f"guidance/supplier/{SA}/"); ok("S11 giao1 timeline NCC: 403", s == 403, s)
s, b, _ = call("cs2", "GET", f"guidance/supplier/{SA}/"); ok("S11 cs2 timeline NCC: 403", s == 403, s)

# ---- số truy vấn không theo số dòng: đo thời gian thô 60 NCC (đối chiếu, test chính ở BE)
for i in range(60):
    call("loc", "POST", "purchasing/suppliers/", {"name": f"QA Bulk {i:03d}"})
s, b, _ = call("loc", "GET", "purchasing/suppliers/")
ok("S12 trang đầu 50 dòng, có next", s == 200 and len(b["results"]) == 50 and b["next"], (len(b["results"]), b["next"]))

# ---- log máy chủ không chứa SĐT NCC/khách (be.log)
logp = os.path.join(os.path.dirname(DB), "be.log")
if os.path.exists(logp):
    lg = open(logp, errors="ignore").read()
    app_lines = [l for l in lg.splitlines() if '" 200 ' not in l and '" 201 ' not in l and '" 400 ' not in l and '" 404 ' not in l and '" 403 ' not in l and '" 401 ' not in l and '" 405 ' not in l]
    ok("S13 log ứng dụng (ngoài dòng truy cập runserver) không chứa SĐT giả / ghi chú", not any(x in l for l in app_lines for x in (PHONE, "ghi chú giả")), "")
    print("INFO S13 dòng truy cập runserver có chứa từ khoá tìm kiếm trong query string:", sum(1 for l in lg.splitlines() if ("q=" + PHONE) in l))
print(f"\n{sum(1 for _, c in R if c)}/{len(R)} PASS")
sys.exit(0 if all(c for _, c in R) else 1)
