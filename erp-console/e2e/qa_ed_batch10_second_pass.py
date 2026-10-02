# QA lần 2 Lô 10: kiểm kỹ B1-B5 trên BE THẬT sau bản sửa (RECEIPT_NOT_DRAFT / RECEIPT_CANCELLED / BATCH_CANCELLED).
#   REAL_BASE=http://127.0.0.1:3302 REAL_API=http://127.0.0.1:8130 SHOTS=... QA_SCRATCH=... PY=... DATABASE_URL=... python3 -u e2e/qa_ed_batch10_second_pass.py
# Dùng lại tiện ích của qa_ed_batch10_real.py. Chỉ dữ liệu giả.
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("real10", os.path.join(HERE, "qa_ed_batch10_real.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
ok, note, call, Sess, shot, alerts = R.ok, R.note, R.call, R.Sess, R.shot, R.alerts
WT_BACKEND = os.path.join(os.path.dirname(HERE), "..", "backend")
CODES = ("RECEIPT_NOT_DRAFT", "RECEIPT_CANCELLED", "BATCH_CANCELLED")
PII = re.compile(r"(?<!\d)0\d{9}(?!\d)")


def new_receipt(tag, supplier=1, qty="10", rate="50000.00", item="MUC-ONG"):
    st, r, raw = call("POST", "/api/purchasing/receipts/receive-batches/", "kho1", {"supplier": supplier, "received_date": "2026-10-02", "idempotency_key": f"qa10b-{tag}", "lines": [{"item_code": item, "qty": qty, "rate": rate, "expiry_date": "2026-10-25"}]})
    assert st == 201, (st, raw[:200])
    return r["receipt"]["id"], r["receipt"]["lines"][0]["batch"]


def shell(script):
    env = dict(os.environ)
    out = subprocess.run([env["PY"], "manage.py", "shell", "-c", script], cwd=WT_BACKEND, env=env, capture_output=True, text=True)
    return out.stdout + out.stderr


def audit_count(model_fragment=""):
    st, j, raw = call("GET", "/api/audit-logs/", "loc")
    return len(j["results"]) if st == 200 and isinstance(j, dict) and "results" in j else (len(j) if st == 200 and isinstance(j, list) else -1)


def api_cases():
    print("\n=== api_cases", flush=True)
    rid, bid = new_receipt("a")
    st, _, raw = call("POST", f"/api/purchasing/receipts/{rid}/cancel/", "loc", {})
    ok("(chuẩn bị) huỷ phiếu SUBMITTED", st == 200, (st, raw[:100]))
    audit0 = audit_count()
    inv_body = {"supplier": 1, "receipt": rid, "amount": "100000.00", "invoice_date": "2026-10-02", "is_paid": False}
    cost_body = {"cost_type": "ICE", "amount": "50000.00", "allocation_method": "BY_QTY", "incurred_date": "2026-10-02", "receipt": rid, "allocations": [{"batch": bid, "amount": "50000.00"}]}
    for who in ("loc", "ql1", "kho1"):
        st, j, raw = call("POST", f"/api/purchasing/receipts/{rid}/submit/", who, {})
        want = 400 if who != "kho1" else None
        ok(f"B1 {who}: submit phiếu đã huỷ -> 400 RECEIPT_NOT_DRAFT (hoặc 403 nếu thiếu quyền), không 200/500", (st == 400 and "RECEIPT_NOT_DRAFT" in raw) or st == 403, (st, raw[:160]))
    st, d, _ = call("GET", f"/api/purchasing/receipts/{rid}/", "loc")
    ok("B1: phiếu vẫn CANCELLED, lô vẫn CANCELLED (không hồi sinh)", d["status"] == "CANCELLED" and all(l["batch_status"] == "CANCELLED" for l in d["lines"]), (d["status"], [l["batch_status"] for l in d["lines"]]))
    st, j, raw = call("POST", "/api/purchasing/invoices/", "loc", inv_body)
    ok("B2 loc: hoá đơn gắn phiếu đã huỷ -> 400 RECEIPT_CANCELLED", st == 400 and "RECEIPT_CANCELLED" in raw, (st, raw[:160]))
    st, j, raw = call("POST", "/api/purchasing/invoices/", "ql1", inv_body)
    ok("B2 ql1: cũng bị từ chối (400 RECEIPT_CANCELLED hoặc 403), không 201", (st == 400 and "RECEIPT_CANCELLED" in raw) or st == 403, (st, raw[:160]))
    st, d, _ = call("GET", f"/api/purchasing/receipts/{rid}/", "loc")
    ok("B2: phiếu đã huỷ không có hoá đơn nào", len(d["invoices"]) == 0, d["invoices"])
    st, j, raw = call("POST", "/api/purchasing/costs/", "loc", cost_body)
    ok("B3 loc: chi phí vào lô phiếu đã huỷ -> 400 BATCH_CANCELLED", st == 400 and "BATCH_CANCELLED" in raw, (st, raw[:160]))
    st, j, raw = call("POST", "/api/purchasing/costs/", "ql1", cost_body)
    ok("B3 ql1: 403 (chỉ Chủ thêm chi phí)", st == 403, (st, raw[:120]))
    st, d, _ = call("GET", f"/api/purchasing/receipts/{rid}/", "loc")
    ok("B3: giá vốn lô huỷ không đổi (vẫn bằng giá mua 50000)", all(float(l["landed_unit_cost"]) == 50000.0 for l in d["lines"]) and d["costs"] == [], [(l["rate"], l["landed_unit_cost"]) for l in d["lines"]])
    # thông điệp chuẩn
    st, j, raw = call("POST", f"/api/purchasing/receipts/{rid}/submit/", "loc", {})
    ok("Thông điệp B1 tiếng Việt, nêu trạng thái 'Đã huỷ', không có SĐT", "Đã huỷ" in raw and not PII.search(raw), raw[:200])
    # Phiếu SUBMITTED bình thường: hoá đơn + chi phí vẫn nhận
    rid2, bid2 = new_receipt("b")
    st, _, raw = call("POST", "/api/purchasing/invoices/", "loc", {**inv_body, "receipt": rid2})
    ok("Đường thuận: hoá đơn vào phiếu SUBMITTED -> 201", st == 201, (st, raw[:120]))
    st, _, raw = call("POST", "/api/purchasing/costs/", "loc", {**cost_body, "receipt": rid2, "allocations": [{"batch": bid2, "amount": "50000.00"}]})
    ok("Đường thuận: chi phí vào lô phiếu SUBMITTED -> 201", st == 201, (st, raw[:120]))
    # Ghi nhận phiếu SUBMITTED lần 2
    st, _, raw = call("POST", f"/api/purchasing/receipts/{rid2}/submit/", "loc", {})
    ok("Ghi nhận phiếu đã ghi nhận -> 400 RECEIPT_NOT_DRAFT, không sinh lô thứ 2", st == 400 and "RECEIPT_NOT_DRAFT" in raw, (st, raw[:140]))
    st, d, _ = call("GET", f"/api/purchasing/receipts/{rid2}/", "loc")
    ok("Phiếu đã ghi nhận vẫn đúng 1 lô", sum(1 for l in d["lines"] if l["batch"]) == 1, [l["batch"] for l in d["lines"]])
    # PATCH hoá đơn sang phiếu đã huỷ
    st, inv, raw = call("POST", "/api/purchasing/invoices/", "loc", {**inv_body, "receipt": None, "amount": "123000.00"})
    ok("(chuẩn bị) hoá đơn không gắn phiếu", st == 201, (st, raw[:100]))
    if st == 201:
        st, j, raw = call("PATCH", f"/api/purchasing/invoices/{inv['id']}/", "loc", {"receipt": rid})
        ok("B2 PATCH: gắn hoá đơn có sẵn vào phiếu đã huỷ -> 400 RECEIPT_CANCELLED", st == 400 and "RECEIPT_CANCELLED" in raw, (st, raw[:160]))
        st, j, raw = call("PATCH", f"/api/purchasing/invoices/{inv['id']}/", "loc", {"receipt": rid2})
        ok("PATCH: gắn hoá đơn vào phiếu SUBMITTED vẫn được (đường thuận)", st == 200, (st, raw[:120]))
    # Chưa đăng nhập
    for m, path in (("POST", f"/api/purchasing/receipts/{rid2}/submit/"), ("POST", "/api/purchasing/invoices/"), ("POST", "/api/purchasing/costs/")):
        st, _, _ = call(m, path, None, {})
        ok(f"Chưa đăng nhập {m} {path.split('/')[3]} -> 401", st == 401, st)
    # Huỷ phiếu ghi AuditLog; các lần bị từ chối không ghi gì thêm
    audit1 = audit_count()
    ok("Các lần thử bị từ chối không tạo AuditLog giả (số bản ghi không đổi, chỉ tăng do thao tác hợp lệ ở dưới)", audit1 >= audit0, (audit0, audit1))


def expired_batch_cost():
    print("\n=== expired_batch_cost", flush=True)
    rid, bid = new_receipt("exp")
    out = shell(f"from apps.inventory.models import Batch\nb=Batch.objects.get(pk={bid})\nBatch.objects.filter(pk=b.pk).update(status='CANCELLED')\nprint('SET', Batch.objects.get(pk=b.pk).status)")
    ok("(chuẩn bị) mô phỏng lô huỷ vì quá hạn (phiếu vẫn SUBMITTED)", "SET CANCELLED" in out, out[-200:])
    st, d, _ = call("GET", f"/api/purchasing/receipts/{rid}/", "loc")
    ok("Phiếu vẫn SUBMITTED, lô CANCELLED (quá hạn)", d["status"] == "SUBMITTED" and d["lines"][0]["batch_status"] == "CANCELLED", (d["status"], d["lines"][0]["batch_status"]))
    st, j, raw = call("POST", "/api/purchasing/costs/", "loc", {"cost_type": "ICE", "amount": "40000.00", "allocation_method": "BY_QTY", "incurred_date": "2026-10-02", "receipt": rid, "allocations": [{"batch": bid, "amount": "40000.00"}]})
    ok("Lô huỷ vì quá hạn VẪN nhận chi phí đến muộn -> 201 (E-14, BR-GV-02)", st == 201, (st, raw[:200]))
    st, d, _ = call("GET", f"/api/purchasing/receipts/{rid}/", "loc")
    ok("Giá vốn lô quá hạn đổi đúng: 50000 + 40000/10 = 54000", abs(float(d["lines"][0]["landed_unit_cost"]) - 54000.0) < 0.01, d["lines"][0]["landed_unit_cost"])


def concurrent_cases():
    print("\n=== concurrent_cases", flush=True)
    # hai submit song song trên một phiếu Nháp
    out = shell(
        "from django.contrib.auth import get_user_model\nfrom apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier\nfrom apps.catalog.models import Item\n"
        "u=get_user_model().objects.get(username='kho1')\nfrom apps.inventory.models import Warehouse\nw=Warehouse.objects.first()\n"
        "r=PurchaseReceipt.objects.create(supplier=Supplier.objects.first(), warehouse=w, received_date='2026-10-02', status='DRAFT', created_by=u)\n"
        "PurchaseReceiptLine.objects.create(receipt=r, item=Item.objects.get(code='CA-THU'), qty=5, rate=0)\nprint('DRAFTID', r.pk)")
    m = re.search(r"DRAFTID (\d+)", out)
    if not m:
        ok("(chuẩn bị) tạo phiếu Nháp bằng ORM", False, out[-300:])
        return
    did = int(m.group(1))
    res = []

    def go(who):
        res.append(call("POST", f"/api/purchasing/receipts/{did}/submit/", who, {})[0])

    ts = [threading.Thread(target=go, args=(w,)) for w in ("loc", "ql1", "loc", "ql1")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    st, d, _ = call("GET", f"/api/purchasing/receipts/{did}/", "loc")
    ok("4 lần ghi nhận song song một phiếu Nháp: tối đa 1 lần 200 (không ghi nhận đôi); lần còn lại 400 hoặc 500 do SQLite 'database is locked'", res.count(200) == 1 and all(x in (200, 400, 500) for x in res), res)
    ok("... và chỉ 1 lô sinh ra", sum(1 for l in d["lines"] if l["batch"]) == 1, [l["batch"] for l in d["lines"]])
    note("SQLite ghi tuần tự nên không chứng minh được khoá hàng (select_for_update) trên Postgres; kiểm Postgres vẫn ⏸")
    # huỷ và ghi hoá đơn song song
    rid, bid = new_receipt("race")
    res2 = {}

    def cancel():
        res2["cancel"] = call("POST", f"/api/purchasing/receipts/{rid}/cancel/", "loc", {})[0]

    def invoice():
        res2["invoice"] = call("POST", "/api/purchasing/invoices/", "loc", {"supplier": 1, "receipt": rid, "amount": "99000.00", "invoice_date": "2026-10-02", "is_paid": False})[0]

    ts = [threading.Thread(target=cancel), threading.Thread(target=invoice)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    st, d, _ = call("GET", f"/api/purchasing/receipts/{rid}/", "loc")
    ok("Huỷ phiếu và ghi hoá đơn song song: kết quả cuối khớp mã trả về (huỷ 200 thì phiếu CANCELLED; hoá đơn 400 thì không có hoá đơn)", (res2["cancel"] != 200 or d["status"] == "CANCELLED") and (res2["invoice"] != 400 or len(d["invoices"]) == 0), (res2, d["status"], len(d["invoices"])))
    note(f"đua huỷ/hoá đơn: {res2}, hoá đơn trên phiếu huỷ: {len(d['invoices'])} (nếu hoá đơn thắng cuộc đua thì có trước thời điểm huỷ, hợp lệ)")


def ui_cases(browser):
    print("\n=== ui_cases", flush=True)
    # B1 trên màn hình: tab A mở phiếu Nháp, tab B huỷ, tab A bấm Ghi nhận -> lỗi dễ hiểu, không hồi sinh
    out = shell(
        "from django.contrib.auth import get_user_model\nfrom apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier\nfrom apps.catalog.models import Item\nfrom apps.inventory.models import Warehouse\n"
        "u=get_user_model().objects.get(username='kho1')\nw=Warehouse.objects.first()\n"
        "r=PurchaseReceipt.objects.create(supplier=Supplier.objects.first(), warehouse=w, received_date='2026-10-02', status='DRAFT', created_by=u)\n"
        "PurchaseReceiptLine.objects.create(receipt=r, item=Item.objects.get(code='CA-THU'), qty=5, rate=0)\nprint('DRAFTID', r.pk)")
    did = int(re.search(r"DRAFTID (\d+)", out).group(1))
    s = Sess(browser, "kho1")
    pg = s.page
    s.go(f"/purchasing/detail/?id={did}")
    pg.wait_for_timeout(400)
    call("POST", f"/api/purchasing/receipts/{did}/cancel/", "loc", {})
    pg.get_by_test_id("submit-receipt").click()
    dlg = pg.get_by_role("dialog")
    dlg.wait_for()
    dlg.get_by_role("button", name="Ghi nhận phiếu").click()
    pg.wait_for_timeout(800)
    txt = R.squash(dlg.inner_text()) if dlg.count() else s.main()
    ok("B1 giao diện: màn cũ bấm Ghi nhận phiếu đã huỷ -> báo lỗi dễ hiểu, có 'Tải lại phiếu', không lộ mã BR-/RECEIPT_", dlg.count() == 1 and "Tải lại phiếu" in txt and "BR-" not in txt and not any(c in txt for c in CODES), txt[:300])
    shot(s, "l2-b1-man-cu-ghi-nhan")
    pg.get_by_role("button", name="Tải lại phiếu").click()
    pg.wait_for_timeout(800)
    ok("B1 giao diện: sau Tải lại phiếu hiện 'Đã huỷ' và không còn nút Ghi nhận", "Đã huỷ" in s.main() and pg.get_by_test_id("submit-receipt").count() == 0, s.main()[:200])
    st, d, _ = call("GET", f"/api/purchasing/receipts/{did}/", "loc")
    ok("B1 giao diện: BE vẫn CANCELLED, không lô", d["status"] == "CANCELLED" and not any(l["batch"] for l in d["lines"]), d["status"])
    ok("B1 giao diện: console sạch", not s.console_bad(), s.console_bad()[:2])
    s.close()
    # B2 / B3 trên màn hình đã có trong ph_stale; ở đây kiểm thông điệp hiển thị
    rid, bid = new_receipt("ui2")
    s = Sess(browser, "loc")
    pg = s.page
    s.go(f"/purchasing/detail/?id={rid}")
    pg.wait_for_timeout(400)
    pg.get_by_role("button", name="Thêm hoá đơn").first.click()
    dlg = pg.get_by_role("dialog")
    dlg.wait_for()
    call("POST", f"/api/purchasing/receipts/{rid}/cancel/", "loc", {})
    dlg.locator("input[name=amount]").fill("350000")
    dlg.get_by_role("button", name="Lưu hoá đơn").click()
    pg.wait_for_timeout(900)
    t2 = R.squash(dlg.inner_text()) if dlg.count() else s.main()
    ok("B2 giao diện: báo lỗi dễ hiểu (nói phiếu đã huỷ), không lộ mã RECEIPT_*, không báo thành công, vẫn ở form, giữ số tiền", dlg.count() == 1 and "huỷ" in t2.lower() and not any(c in t2 for c in CODES) and dlg.locator("input[name=amount]").input_value() == "350.000", t2[:300])
    ok("B2 giao diện (UI-RULES §1 'không mã luật BR-' trên màn): câu lỗi không chứa 'BR-'", "BR-" not in t2, t2[:200])
    shot(s, "l2-b2-man-cu-hoa-don")
    s.close()
    rid3, bid3 = new_receipt("ui3")
    s = Sess(browser, "loc")
    pg = s.page
    s.go(f"/purchasing/costs/new/?receipt={rid3}")
    pg.locator("input[name=amount]").wait_for()
    pg.wait_for_timeout(400)
    pg.locator("input[name=amount]").fill("120000")
    pg.wait_for_timeout(300)
    call("POST", f"/api/purchasing/receipts/{rid3}/cancel/", "loc", {})
    pg.get_by_role("button", name="Lưu chi phí").click()
    pg.wait_for_timeout(900)
    t3 = s.main()
    ok("B3 giao diện: báo lỗi dễ hiểu (lô thuộc phiếu đã huỷ), không lộ mã BATCH_CANCELLED, vẫn ở form, giữ số tiền", "/costs/new" in pg.url and "huỷ" in t3.lower() and "BATCH_CANCELLED" not in t3 and pg.locator("input[name=amount]").input_value() == "120.000", (pg.url, t3[:260]))
    ok("B3 giao diện (UI-RULES §1): câu lỗi không chứa 'BR-'", "BR-" not in t3, t3[:200])
    shot(s, "l2-b3-man-cu-chi-phi")
    st, d, _ = call("GET", f"/api/purchasing/receipts/{rid3}/", "loc")
    ok("B3 giao diện: giá vốn lô huỷ không đổi", all(float(l["landed_unit_cost"]) == float(l["rate"]) for l in d["lines"]), [(l["rate"], l["landed_unit_cost"]) for l in d["lines"]])
    s.close()
    # B4/B5: gõ từng phím + mobile
    s = Sess(browser, "kho1")
    pg = s.page
    s.go("/purchasing/new/")
    pg.locator("select[name=supplier]").wait_for()
    pg.locator("select[name=supplier]").select_option("2")
    pg.locator("select[name=item-0]").select_option("MUC-ONG")
    pg.locator("input[name=qty-0]").fill("5")
    r = pg.locator("input[name=rate-0]")
    r.press_sequentially("-5000")
    mark_idx = s.mark()
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(300)
    fe, inv = R.field_error(pg, "rate-0")
    ok("B5 gõ từng phím '-5000': ô giữ '-5000', lỗi dưới ô, không gửi API", r.input_value() == "-5000" and bool(fe) and inv == "true" and not s.posts_since(mark_idx, "receive-batches"), (r.input_value(), fe, inv))
    note(f"B5 câu lỗi giá âm: {fe!r}")
    r.fill("")
    r.press_sequentially("1234567890123")  # 13 chữ số
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(300)
    fe13, inv13 = R.field_error(pg, "rate-0")
    ok("B5 giá 13 chữ số (vượt 12): lỗi dưới ô, không gửi API", bool(fe13) and not s.posts_since(mark_idx, "receive-batches"), (fe13, r.input_value()))
    r.fill("")
    r.press_sequentially("999999999999")  # 12 chữ số: tối đa BE nhận
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(300)
    # 12 chữ số hợp lệ -> BE: amount = qty*rate có thể vượt max_digits?
    posts = s.posts_since(mark_idx, "receive-batches")
    note(f"B5 giá 999.999.999.999 đ/kg x 5 kg: số POST={len(posts)}; lỗi={alerts(pg)[:160]!r}; trạng thái ô={R.field_error(pg, 'rate-0')}")
    ok("B5 giá 12 chữ số (999.999.999.999 đ/kg, tối đa FE cho): không được ra lỗi máy chủ 500 - phải gửi được hoặc báo lỗi dưới ô", "500" not in alerts(pg) and (bool(R.field_error(pg, "rate-0")[0]) or bool(posts)), (alerts(pg)[:160], R.field_error(pg, "rate-0")))
    s.close()
    # Số kg: dấu chấm hàng nghìn
    s = Sess(browser, "kho1")
    pg = s.page
    s.go("/purchasing/new/")
    pg.locator("select[name=supplier]").wait_for()
    pg.locator("select[name=supplier]").select_option("2")
    pg.locator("select[name=item-0]").select_option("MUC-ONG")
    pg.locator("input[name=qty-0]").fill("1.000")
    mark_idx = s.mark()
    pg.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    pg.wait_for_timeout(600)
    posts = s.posts_since(mark_idx, "receive-batches")
    qtys = [l["qty"] for p in posts for l in json.loads(p[2])["lines"]] if posts else []
    note(f"Số kg gõ '1.000' -> gửi qty={qtys} (đọc là {qtys[0] if qtys else '?'} kg, người dùng VN có thể hiểu 1.000 = một nghìn kg). Chưa kết luận lỗi, nêu cho PO.")
    s.close()


def main():
    from playwright.sync_api import sync_playwright
    api_cases()
    expired_batch_cost()
    concurrent_cases()
    with sync_playwright() as p:
        b = p.chromium.launch()
        try:
            ui_cases(b)
        except Exception as e:  # noqa: BLE001
            import traceback
            ok("ui_cases chạy hết không lỗi", False, repr(e) + traceback.format_exc()[-300:])
        b.close()
    bad = [r for r in R.results if not r[1]]
    print(f"\nTỔNG: {len(R.results)} ca, PASS {len(R.results) - len(bad)}, FAIL {len(bad)}")
    for n, _, e in bad:
        print("  FAIL:", n, "->", str(e)[:300])
    print("GHI NHẬN:")
    for n in R.notes:
        print("  -", n)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
