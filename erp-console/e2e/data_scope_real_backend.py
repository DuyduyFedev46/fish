# E2E ERP trên BACKEND THẬT cho phạm vi dữ liệu cấu hình: PV-13 (mất quyền giữa chừng), PV-14 (khối "Dữ liệu bạn xem được"),
# §2.7 (chữ ô khách). Bổ sung cho data_scope_loss_account.py (chạy bản MOCK) theo 02b §6.1.6 ca 1-15. Dữ liệu là bộ giả của `seed_qa`.
#
# Dựng (mọi đường dẫn tạm đặt tuỳ ý; mật khẩu các tài khoản qa_ lấy từ biến môi trường, không có trong mã):
#   BE : DJANGO_DEBUG=1 DATABASE_URL=sqlite:///<tmp>.sqlite3 CORS_ALLOWED_ORIGINS=<BASE> THROTTLE_LOGIN_IP=10000/min THROTTLE_LOGIN_USER=10000/hour
#        manage.py migrate && bootstrap_masterdata && QA_PASSWORD=... seed_qa --manifest <ids.json> && runserver <cổng>
#        rồi lùi ngày phiếu nháp (chỉ DB tạm): manage.py shell -c "from apps.purchasing.models import PurchaseReceipt as R; ...update(created_at=now-1 ngày)"
#   FE : NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=<API> npm run build, phục vụ out/ ở BASE
#   Chạy: BASE=... REAL_API=... SEED_QA_IDS=<ids.json> QA_PASSWORD=... SHOTS=<thư mục> python3 e2e/data_scope_real_backend.py [tên-ca ...]
# Dữ liệu phụ cho ca 'courier_expired' (chỉ DB tạm): lùi completed_at của phiếu QA-GH-08 về 10 ngày trước (manage.py shell, DeliveryNote.objects.filter(code=...).update(...)).
# Máy chủ tĩnh: python http.server mặc định đứt kết nối khi trình duyệt tải trước nhiều RSC; dùng ThreadingHTTPServer có request_queue_size lớn.
# Cách gây "Tải lại" trên BE thật: thao tác ghi kế tiếp được trả giả (409 hoặc 200) bằng page.route; MỌI yêu cầu GET (đọc chi tiết)
# vẫn đi tới BE thật, nên 404/dữ liệu là phản hồi thật của BE sau khi Chủ thu hẹp phạm vi qua API thật.
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from playwright.sync_api import expect, sync_playwright

from e2e_support import finish

BASE = os.environ.get("BASE", "http://127.0.0.1:3731")
API = os.environ.get("REAL_API", "http://127.0.0.1:8731").rstrip("/")
PW = os.environ["QA_PASSWORD"]
SHOTS = os.environ.get("SHOTS", "/tmp")
IDS = json.load(open(os.environ.get("SEED_QA_IDS", "/tmp/seed_qa_ids.json"), encoding="utf-8"))
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=15_000)
R = []
LOST = "Bạn không còn quyền xem mục này."
EARLIER_DAY = "Phiếu tạo từ hôm trước. Nhờ Quản lý xử lý tiếp."
HIDDEN = "Đã ẩn (không có quyền xem thông tin khách)"
# Dữ liệu khách giả của seed_qa: "Khách QA Giả NN", SĐT 09000000NN (NN 01-20), "QA-Địa chỉ giả số N".
PII = re.compile(r"Khách QA Giả|09000000(?:0[1-9]|1\d|20)\b|QA-Địa chỉ giả")


def ok(name, cond, extra=""):
    R.append((name, bool(cond), extra))
    print("PASS" if cond else "FAIL", name, "" if cond else str(extra)[:300], flush=True)


def api(method, path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Token " + token
    req = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"null")
        except Exception:
            return e.code, raw.decode()


_tokens = {}


def token_of(user):
    if user not in _tokens:
        _tokens[user] = api("POST", "/api/auth/token/", None, {"username": user, "password": PW})[1]["token"]
    return _tokens[user]


def set_group(group, scopes=None, caps=None, widen=False):
    """Chủ đặt phạm vi/việc của nhóm qua API thật (Chủ là người duy nhất được phép)."""
    owner = token_of("qa_owner")
    g = api("GET", f"/api/staff/groups/{group}/", owner)[1]
    body = {"version": g["version"]}
    if scopes:
        body["scopes"] = scopes
    if caps is not None:
        body["capabilities"] = caps
    if widen:
        body["confirm_customer_data_widening"] = True
    st, resp = api("PUT", f"/api/staff/groups/{group}/capabilities/", owner, body)
    assert st == 200, (group, scopes, caps, st, resp)


def login(browser, user, w=1280, h=860):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(m.text))
    page.on("pageerror", lambda e: logs.append("PAGEERROR " + str(e)))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(PW)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    return ctx, page, logs


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def fake_next_write(page, status=409, body=None):
    """Thao tác ghi (POST/PATCH/PUT/DELETE) kế tiếp tới /api/ được trả giả đúng MỘT lần; GET và OPTIONS đi tới BE thật."""
    if body is None:
        body = {"detail": "Bản ghi vừa được người khác xử lý.", "code": "STALE_STATE", "updated_by_name": "Quản lý",
                "updated_at": datetime.now(timezone.utc).isoformat()}
    state = {"done": False}

    def handler(route):
        req = route.request
        if req.method in ("GET", "HEAD", "OPTIONS") or state["done"]:
            return route.continue_()
        state["done"] = True
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body),
                      headers={"access-control-allow-origin": BASE, "access-control-allow-credentials": "true"})

    page.route(re.compile(re.escape(API) + r"/api/.*"), handler)
    return state


FIBER_SCAN = r"""
(patternSource) => {
  const re = new RegExp(patternSource);
  const el = document.querySelector('main') || document.body;
  const key = Object.keys(el).find(k => k.startsWith('__reactFiber$'));
  if (!key) return {error: 'no-fiber'};
  let root = el[key];
  while (root.return) root = root.return;
  const seen = new WeakSet();
  const hits = [];
  function scan(v, depth, path) {
    if (v == null || depth > 6) return;
    if (typeof v === 'string') { if (re.test(v)) hits.push(path); return; }
    if (typeof v !== 'object') return;
    if (typeof Node !== 'undefined' && v instanceof Node) return;
    if (seen.has(v)) return;
    seen.add(v);
    if (v.$$typeof && v.props) { scan(v.props, depth + 1, path + '.props'); return; }
    for (const k of Object.keys(v).slice(0, 80)) { try { scan(v[k], depth + 1, path + '.' + k); } catch (e) {} }
  }
  let visited = 0;
  function walk(f, depth) {
    while (f) {
      visited++;
      const name = f.type && (f.type.name || f.type.displayName) || String(f.tag);
      scan(f.memoizedProps, 0, 'props:' + name);
      let h = f.memoizedState, i = 0;
      if (h && typeof h === 'object' && 'next' in h && 'memoizedState' in h) {
        while (h && i < 60) { scan(h.memoizedState, 0, 'hook' + i + ':' + name); h = h.next; i++; }
      } else if (h) scan(h, 0, 'state:' + name);
      if (f.child) walk(f.child, depth + 1);
      f = f.sibling;
    }
  }
  walk(root, 0);
  return {hits, visited};
}
"""


def storage_dump(page):
    return page.evaluate("() => JSON.stringify({l: {...localStorage}, s: {...sessionStorage}, url: location.href, cookie: document.cookie})")


def assert_scope_lost(page, logs, label, list_path, extra=None, no_extra=None):
    expect(page.get_by_test_id("scope-lost")).to_be_visible()
    body = page.locator("body").inner_text()
    ok(f"{label}: có câu '{LOST}'", LOST in body, body[:200])
    link = page.get_by_role("link", name="Về danh sách")
    ok(f"{label}: có liên kết 'Về danh sách' → {list_path}", link.count() == 1 and (link.get_attribute("href") or "").rstrip("/") == list_path.rstrip("/"), link.count())
    ok(f"{label}: DOM không còn tên/SĐT/địa chỉ khách QA", not PII.search(page.locator("html").inner_html()), PII.findall(page.locator("html").inner_html())[:3])
    scan = page.evaluate(FIBER_SCAN, PII.pattern)
    ok(f"{label}: React state/props hiển thị (cây fiber hiện tại, {scan.get('visited')} nút) không còn dữ liệu khách", not scan.get("error") and not scan.get("hits"), scan)
    ok(f"{label}: console không có dữ liệu khách", not any(PII.search(t) for t in logs), [t[:120] for t in logs if PII.search(t)][:3])
    dump = storage_dump(page)
    ok(f"{label}: localStorage/sessionStorage/URL/cookie không có dữ liệu khách", not PII.search(dump), dump[:200])
    if extra:
        ok(f"{label}: có câu phụ '{extra}'", extra in body, body[:300])
    if no_extra:
        ok(f"{label}: KHÔNG có câu phụ '{no_extra}'", no_extra not in body)
    page.screenshot(path=f"{SHOTS}/scope-lost-{re.sub(r'[^a-z0-9]+', '-', label.lower())[:40]}.png")


def positive_control(page, label):
    """Trước khi thu hẹp: trang chi tiết có dữ liệu khách trong DOM và máy quét cây fiber phát hiện được (chứng minh máy quét có hiệu lực)."""
    html = page.locator("html").inner_html()
    scan = page.evaluate(FIBER_SCAN, PII.pattern)
    has_dom = bool(PII.search(html))
    ok(f"{label}: [đối chứng] trước khi thu hẹp, DOM có dữ liệu khách giả", has_dom)
    ok(f"{label}: [đối chứng] máy quét fiber thấy dữ liệu khách trong state/props", bool(scan.get("hits")), scan)


RESTORE = []


def restore_all():
    while RESTORE:
        group, scopes = RESTORE.pop()
        try:
            set_group(group, scopes=scopes, widen=True)
        except AssertionError as e:
            print("RESTORE FAIL", group, e)


def narrow(group, scopes, restore):
    set_group(group, scopes=scopes)
    RESTORE.append((group, restore))


# ---------------------------------------------------------------- các ca
def receipt_case(browser, user, scopes, label, earlier_day):
    ctx, page, logs = login(browser, user)
    go(page, "/purchasing/detail/?id=%d" % IDS["receipts"]["QA-RECEIPT-DRAFT"])
    expect(page.get_by_role("button", name="Ghi nhận phiếu")).to_be_visible()
    narrow("warehouse_staff", scopes, {"receipts": "all"})
    page.get_by_role("button", name="Ghi nhận phiếu").click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    # Hộp xác nhận có thể cần bước nhập; tìm nút gửi cuối.
    submit = dlg.locator("button.primary, button[type=submit]").last
    submit.click()
    page.wait_for_timeout(1500)
    txt = page.locator("body").inner_text()
    ok(f"{label} [thao tác ghi bị 404]: không toast lỗi đỏ, không trắng trang", len(txt.strip()) > 50 and not page.locator(".toast.error, [data-toast=error]").count(), txt[:200])
    page.screenshot(path=f"{SHOTS}/receipt-{user}-after-submit.png")
    reload_btn = page.get_by_role("button", name="Tải lại")
    ok(f"{label} [thao tác ghi bị 404]: hộp hiện nút 'Tải lại' (I3: 2 bước là đúng)", reload_btn.count() >= 1, txt[:300])
    if reload_btn.count():
        reload_btn.first.click()
    assert_scope_lost(page, logs, label, "/purchasing", extra=EARLIER_DAY if earlier_day else None, no_extra=None if earlier_day else EARLIER_DAY)
    link = page.get_by_role("link", name="Về danh sách")
    link.click()
    page.wait_for_url(re.compile(r"/purchasing/?$"))
    ok(f"{label}: bấm 'Về danh sách' → /purchasing/", True)
    ctx.close()
    restore_all()


def case_receipt_not_creator(browser):
    # Ca 1 (techlead bắt buộc) + ca 3 (AC1 trên thao tác ghi): K+G mở phiếu của qa_warehouse, Chủ đặt receipts=created_by_me.
    receipt_case(browser, "qa_warehouse_courier", {"receipts": "created_by_me"}, "Phiếu nhập · không phải người tạo · created_by_me", False)


def case_receipt_earlier_day(browser):
    # Ca 2 + 3: chính người tạo, phiếu hôm qua, created_by_me_today.
    receipt_case(browser, "qa_warehouse", {"receipts": "created_by_me_today"}, "Phiếu nhập · người tạo, phiếu hôm qua · created_by_me_today", True)


def generic_case(browser, label, user, path, group, scopes, restore, list_path, trigger, control=True):
    ctx, page, logs = login(browser, user)
    go(page, path)
    try:
        page.wait_for_selector("main h1, main h2, main header", state="attached")
    except Exception:
        print("DEBUG url:", page.url, "| body:", page.locator("body").inner_text()[:300].replace("\n", " / "), flush=True)
        page.screenshot(path=f"{SHOTS}/debug-open-{user}.png")
        raise
    page.wait_for_timeout(1200)
    if control:
        positive_control(page, label)
    else:
        ok(f"{label}: [đối chứng] API chi tiết không có tên/SĐT/địa chỉ khách (màn không hiện dữ liệu khách)", not PII.search(page.locator('html').inner_html()))
    narrow(group, scopes, restore)
    trigger(page)
    assert_scope_lost(page, logs, label, list_path)
    page.get_by_role("link", name="Về danh sách").click()
    try:
        page.wait_for_url(re.compile(re.escape(list_path) + r"/?$"), timeout=10_000)
    except Exception:
        pass
    ok(f"{label}: bấm 'Về danh sách' về {list_path}", page.url.rstrip("/").endswith(list_path.rstrip("/")), page.url)
    ctx.close()
    restore_all()


def click_conflict_reload(page):
    expect(page.locator("[data-conflict-banner]")).to_be_visible()
    page.locator("[data-conflict-banner]").get_by_role("button").first.click()


def trigger_order(page):
    fake_next_write(page, 409)
    page.get_by_role("button", name="Huỷ đơn").click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    dlg.locator("select").first.select_option(index=1)
    dlg.get_by_role("button", name="Tiếp tục").click()
    page.wait_for_timeout(500)
    d2 = page.get_by_role("dialog")
    if d2.count() and d2.locator("button.primary, button[type=submit]").count():
        d2.locator("button.primary, button[type=submit]").last.click()
    click_conflict_reload(page)


def case_order(browser):
    generic_case(browser, "Đơn hàng · Quản lý, orders → assigned_deliveries", "qa_manager", "/orders/detail/?id=%d" % IDS["orders"]["QA-SO-04"]["id"],
                 "manager", {"orders": "assigned_deliveries"}, {"orders": "all"}, "/orders", trigger_order)


FIBER_RELOAD = r"""
() => {
  // Phiếu hoàn tiền: người không phải Chủ không có thao tác ghi nào trên màn (xác nhận/đánh dấu hỏng chỉ Chủ, BR-PQ-32) và Chủ không bị
  // thu hẹp được (S-5) nên KHÔNG có nút nào gây "tải lại". Gọi ĐÚNG hàm `reload` của useDetail (useCallback(() => run(true))) lấy từ cây fiber:
  // phần còn lại (GET thật tới BE, 404 thật, chuyển trạng thái, vẽ màn) là mã sản phẩm chạy thật.
  const el = document.querySelector('main');
  const key = Object.keys(el).find(k => k.startsWith('__reactFiber$'));
  let f = el[key].child;  // chỉ xét cây con của <main> (màn đang mở), không xét Shell
  let found = null;
  function walk(n) {
    while (n && !found) {
      const name = n.type && (n.type.name || n.type.displayName);
      let h = n.memoizedState, i = 0;
      if (n.tag === 0 && h && typeof h === 'object' && 'next' in h) {
        const fns = [];
        while (h && i < 40) {
          const v = h.memoizedState;
          if (Array.isArray(v) && typeof v[0] === 'function' && v[0].length === 0 && /\(!0\)|\(true\)/.test(String(v[0]))) fns.push(v[0]);
          h = h.next; i++;
        }
        if (fns.length) found = fns[0];
      }
      if (n.child) walk(n.child);
      n = n.sibling;
    }
  }
  walk(f);
  if (!found) return 'not-found';
  found();
  return 'called';
}
"""


def trigger_refund(page):
    res = page.evaluate(FIBER_RELOAD)
    ok("Phiếu hoàn tiền: tìm và gọi được hàm reload của useDetail qua fiber (cách gây tải lại duy nhất, xem chú thích)", res == "called", res)
    page.wait_for_timeout(1500)


def case_refund(browser):
    generic_case(browser, "Phiếu hoàn tiền · Quản lý, orders → assigned_deliveries", "qa_manager",
                 "/orders/refunds/detail/?id=%d" % IDS["refunds"]["QA-REFUND-PENDING"]["id"],
                 "manager", {"orders": "assigned_deliveries"}, {"orders": "all"}, "/orders/refunds", trigger_refund)


def trigger_customer(page):
    fake_next_write(page, 200, {})
    page.get_by_role("button", name="Sửa tên").click()
    inp = page.locator("main input:visible").first
    inp.fill("Khách QA Giả đổi tên")
    inp.press("Enter")
    page.wait_for_timeout(1500)


def case_customer(browser):
    generic_case(browser, "Khách hàng · Quản lý, customers → assigned_deliveries", "qa_manager", "/customers/detail/?id=%d" % IDS["customers"]["0900000004"],
                 "manager", {"customers": "assigned_deliveries"}, {"customers": "all"}, "/customers", trigger_customer)


def trigger_return(page):
    fake_next_write(page, 200, {})
    page.get_by_role("button", name="Huỷ hàng, ghi lỗ").click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    dlg.locator("button.primary, button[type=submit]").last.click()
    page.wait_for_timeout(1500)


def case_return(browser):
    generic_case(browser, "Hàng hoàn · Quản lý, returns → assigned_deliveries", "qa_manager", "/returns/detail/?id=%d" % IDS["returns"]["QA-RETURN-DRAFT"],
                 "manager", {"returns": "assigned_deliveries"}, {"returns": "all"}, "/returns", trigger_return, control=False)


def trigger_delivery(page):
    fake_next_write(page, 409)
    page.get_by_role("button", name="Giao cho người giao").click()
    dlg = page.get_by_role("dialog")
    expect(dlg).to_be_visible()
    dlg.get_by_text("QA Giao 2 (giả)").click()
    dlg.get_by_role("button", name="Giao phiếu").click()
    page.wait_for_timeout(800)
    btn = page.get_by_role("button", name="Tải lại")
    expect(btn.first).to_be_visible()
    btn.first.click()


def case_delivery(browser):
    generic_case(browser, "Phiếu giao · Quản lý, deliveries → assigned", "qa_manager", "/deliveries/detail/?id=%d" % IDS["delivery_notes"]["QA-GH-04"]["id"],
                 "manager", {"deliveries": "assigned"}, {"deliveries": "all"}, "/deliveries", trigger_delivery)


def trigger_confirmation(page):
    fake_next_write(page, 409)
    page.locator("main :text('Gọi khách')").first.click()  # nhận gọi (POST claim) bị trả 409 → banner xung đột
    click_conflict_reload(page)


def case_confirmation(browser):
    # Task 2 đã gọi xong bởi qa_cs1 (seed). Quản lý (all_pending) thấy; thu hẹp pending_or_called_recently thì ngoài phạm vi.
    generic_case(browser, "Gọi xác nhận · Quản lý, confirmation → pending_or_called_recently", "qa_manager", "/confirmation/detail/?id=2",
                 "manager", {"confirmation": "pending_or_called_recently"}, {"confirmation": "all_pending"}, "/confirmation", trigger_confirmation)


def case_first_open(browser):
    # Ca 6 + AC6: mở lần đầu (URL) mục ngoài phạm vi → "Không tìm thấy trang này", KHÔNG dùng câu mất quyền.
    ctx, page, logs = login(browser, "qa_courier1")
    ctx2, page2, logs2 = login(browser, "qa_cs1")
    go(page2, "/orders/detail/?id=%d" % IDS["orders"]["QA-SO-01"]["id"])
    page2.wait_for_timeout(1200)
    b2 = page2.locator("body").inner_text()
    ok("Mở lần đầu đơn ngoài phạm vi của CSKH (qa_cs1): 'Không tìm thấy trang này', không câu mất quyền, không lộ khách",
       "Không tìm thấy trang này" in b2 and LOST not in b2 and not PII.search(page2.locator("html").inner_html()), b2[:200])
    ctx2.close()
    for label, path in (("phiếu giao của qa_courier2", "/deliveries/detail/?id=%d" % IDS["delivery_notes"]["QA-GH-09"]["id"]),
                        ("đơn (NV giao bị chặn cả màn Đơn)", "/orders/detail/?id=%d" % IDS["orders"]["QA-SO-04"]["id"]),
                        ("phiếu nhập", "/purchasing/detail/?id=1")):
        go(page, path)
        page.wait_for_timeout(1200)
        body = page.locator("body").inner_text()
        if "orders" in path:
            ok(f"Mở lần đầu {label}: màn 'Không có quyền' của cổng, không câu mất quyền, không lộ dữ liệu khách", LOST not in body and not PII.search(page.locator("html").inner_html()), body[:100])
            continue
        if "purchasing" in path:
            ok(f"Mở lần đầu {label} (NV giao không có quyền xem phiếu nhập): không dùng câu mất quyền", LOST not in body, body[:150])
        else:
            ok(f"Mở lần đầu {label}: 'Không tìm thấy trang này', không câu mất quyền", "Không tìm thấy trang này" in body and LOST not in body, body[:200])
        ok(f"Mở lần đầu {label}: không lộ dữ liệu khách", not PII.search(page.locator("html").inner_html()))
    ctx.close()


def case_http_500(browser):
    # AC4: chặn GET chi tiết trả 500 sau khi đã mở → hành vi lỗi cũ (Thử lại), KHÔNG vào scope_lost.
    ctx, page, logs = login(browser, "qa_manager")
    oid = IDS["orders"]["QA-SO-04"]["id"]
    go(page, f"/orders/detail/?id={oid}")
    page.wait_for_timeout(1200)
    fake_next_write(page, 409)
    page.get_by_role("button", name="Huỷ đơn").click()
    dlg = page.get_by_role("dialog")
    dlg.locator("select").first.select_option(index=1)
    dlg.get_by_role("button", name="Tiếp tục").click()
    page.wait_for_timeout(500)
    d2 = page.get_by_role("dialog")
    if d2.count() and d2.locator("button.primary, button[type=submit]").count():
        d2.locator("button.primary, button[type=submit]").last.click()
    expect(page.locator("[data-conflict-banner]")).to_be_visible()

    def h(route):
        if route.request.method == "GET" and re.search(rf"/api/sales/orders/{oid}/?(\?.*)?$", route.request.url):
            return route.fulfill(status=500, content_type="application/json", body='{"detail":"x"}', headers={"access-control-allow-origin": BASE})
        route.fallback()
    page.route(re.compile(re.escape(API) + r"/api/sales/orders/\d+/?.*"), h)
    page.locator("[data-conflict-banner]").get_by_role("button").first.click()
    page.wait_for_timeout(1500)
    body = page.locator("body").inner_text()
    ok("AC4: tải lại bị 500 → KHÔNG vào màn mất quyền", LOST not in body and page.get_by_test_id("scope-lost").count() == 0, body[:200])
    ok("AC4: tải lại bị 500 → giữ màn đơn (còn mã đơn) và có nút Thử lại", "QA-SO-04" in body and page.get_by_role("button", name="Thử lại").count() >= 1, body[:300])
    page.screenshot(path=f"{SHOTS}/ac4-500.png")
    ctx.close()
    # receipt: GET 500 sau khi mở, bấm Ghi nhận (404 thật) không áp dụng; kiểm bằng 500 trên GET chi tiết phiếu nhập qua nút Thử lại ở timeline.


def case_load_more(browser):
    # AC3: "Tải thêm" gặp 404 → tải lại trang 1, không lặp request. Dùng thật: BE trả 404 cho ?page=2 khi chỉ có 1 trang;
    # chỉ sửa trường `next` của trang 1 để nút "Tải thêm" hiện (không đủ dữ liệu seed cho 2 trang).
    ctx, page, logs = login(browser, "qa_warehouse")
    calls = []

    def h(route):
        req = route.request
        url = req.url
        if req.method == "GET":
            calls.append(url)
            if "page=2" not in url:
                resp = route.fetch()
                data = resp.json()
                data["next"] = API + "/api/sales/orders/?page=2"
                return route.fulfill(response=resp, json=data, headers={"access-control-allow-origin": BASE})
        route.continue_()
    page.route(re.compile(re.escape(API) + r"/api/sales/orders/(\?.*)?$"), h)
    go(page, "/orders/")
    page.wait_for_timeout(1500)
    more = page.get_by_role("button", name=re.compile("Tải thêm"))
    ok("AC3: danh sách đơn hiện nút 'Tải thêm' (next giả)", more.count() == 1)
    narrow("warehouse_staff", {"orders": "assigned_deliveries"}, {"orders": "all"})
    calls.clear()
    more.click()
    page.wait_for_timeout(2500)
    page2 = [c for c in calls if "page=2" in c]
    page1 = [c for c in calls if "page=2" not in c]
    ok("AC3: sau 404 của trang 2 gọi lại trang 1 đúng 1 lần và không lặp (page=2: 1, page=1: 1)", len(page2) == 1 and len(page1) == 1, (len(page2), len(page1), calls))
    main = page.locator("main").inner_text()
    ok("AC3: không hộp lỗi 'moreError'; danh sách theo phạm vi mới (rỗng, không còn mã đơn QA-SO)", "QA-SO-" not in main, main[:200])
    page.wait_for_timeout(1500)
    ok("AC3: không có vòng lặp yêu cầu sau 1,5 giây nữa", len(calls) == 2, len(calls))
    page.screenshot(path=f"{SHOTS}/ac3-load-more.png")
    ctx.close()
    restore_all()


def case_list_refresh(browser):
    # Ca 8 (AC3): đang mở danh sách đơn của qa_warehouse (thấy mọi đơn), Chủ thu hẹp orders → assigned_deliveries,
    # người dùng làm mới bằng nút "Thử lại" của dải mất mạng (offline rồi online) → danh sách ngắn lại, không hộp lỗi.
    ctx, page, logs = login(browser, "qa_warehouse")
    go(page, "/orders/")
    expect(page.locator("table tbody tr").first).to_be_visible()
    before = page.locator("table tbody tr").count()
    ok("Danh sách đơn: trước khi thu hẹp có dòng", before >= 10, before)
    narrow("warehouse_staff", {"orders": "assigned_deliveries"}, {"orders": "all"})
    # Dải mất mạng của Shell hiện khi trình duyệt phát sự kiện offline; nút "Thử lại" của dải gọi lại danh sách (mạng thật vẫn thông).
    page.evaluate("() => { Object.defineProperty(navigator, 'onLine', {get: () => false, configurable: true}); window.dispatchEvent(new Event('offline')); }")
    btn = page.get_by_role("button", name="Thử lại")
    expect(btn.first).to_be_visible()
    btn.first.click()
    page.evaluate("() => { Object.defineProperty(navigator, 'onLine', {get: () => true, configurable: true}); window.dispatchEvent(new Event('online')); }")
    page.wait_for_timeout(2000)
    main = page.locator("main").inner_text()
    after = page.locator("table tbody tr").count()
    ok("Danh sách đơn sau thu hẹp+làm mới: ngắn lại (không còn mã QA-SO)", "QA-SO-" not in main and after < before, (before, after, main[:200]))
    ok("Danh sách đơn sau thu hẹp+làm mới: không hộp lỗi", "Chưa tải được" not in main and page.get_by_role("button", name="Thử lại").count() == 0, main[:200])
    ok("Danh sách đơn: không lộ dữ liệu khách sau thu hẹp", not PII.search(page.locator("html").inner_html()))
    page.screenshot(path=f"{SHOTS}/ac3-list-refresh.png")
    ctx.close()
    restore_all()


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def block(page):
    return page.locator("[data-testid=data-scopes]")


def row(page, key):
    return block(page).locator(f"[data-scope={key}]")


def open_account(page):
    go(page, "/account/")
    expect(block(page)).to_be_visible()


def case_account(browser):
    # PV-14 trên BE thật: khối "Dữ liệu bạn xem được" của các vai qa_*, 360 và 1280, không cuộn ngang.
    for user, expect_rows in (
        ("qa_courier1", {"orders": ("Đơn có phiếu giao gán cho tôi", "theo nhóm Nhân viên giao"), "invoices": ("Không xem", None),
                         "receipts": ("Không xem", None), "confirmation": ("Không xem", None), "audit_log": ("Không xem", None)}),
        ("qa_warehouse_courier", {"orders": ("Tất cả đơn", "theo nhóm Nhân viên kho"), "invoices": ("Hoá đơn của tất cả đơn", "theo nhóm Nhân viên kho"),
                                  "customers": ("Khách của phiếu giao gán cho tôi", "theo nhóm Nhân viên giao")}),
        ("qa_warehouse", {"orders": ("Tất cả đơn", "theo nhóm Nhân viên kho"), "receipts": ("Tất cả phiếu", "theo nhóm Nhân viên kho"), "customers": ("Không xem", None)}),
        ("qa_manager", {"orders": ("Tất cả đơn", "theo nhóm Quản lý"), "customers": ("Tất cả khách", "theo nhóm Quản lý")}),
        ("qa_cs1", {"orders": ("Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận", "theo nhóm"), "confirmation": ("Phiếu đang chờ gọi hoặc tôi đã gọi", "theo nhóm")}),
        ("qa_owner", {"confirmation": ("Mọi phiếu chờ gọi", "theo nhóm Chủ"), "audit_log": ("Tất cả", None)}),
        ("qa_superuser", {"orders": ("Tất cả đơn", None), "confirmation": ("Mọi phiếu chờ gọi", None)}),
    ):
        for w, h in ((360, 800), (1280, 860)):
            ctx, page, logs = login(browser, user, w, h)
            open_account(page)
            b = block(page)
            txt = b.inner_text()
            ok(f"PV-14 {user} {w}px: đủ 8 dòng", b.locator("[data-scope]").count() == 8, b.locator("[data-scope]").count())
            ok(f"PV-14 {user} {w}px: tiêu đề 'Dữ liệu bạn xem được' và câu 'Chỉ để xem, không đổi ở đây.'", "Dữ liệu bạn xem được" in txt and "Chỉ để xem, không đổi ở đây." in txt)
            for key, (main_text, sub) in expect_rows.items():
                rt = row(page, key).inner_text()
                ok(f"PV-14 {user} {w}px: dòng {key} có '{main_text}'" + (f" và '{sub}'" if sub else ""), main_text in rt and (sub is None or sub in rt), rt)
            ok(f"PV-14 {user} {w}px: khối chỉ để xem (không nút/ô nhập/liên kết)", b.locator("button, input, select, textarea, a").count() == 0)
            ok(f"PV-14 {user} {w}px: không cuộn ngang", no_hscroll(page))
            if user == "qa_superuser":
                ok("PV-14 superuser: có dòng 'Toàn bộ (quản trị hệ thống)'", "Toàn bộ (quản trị hệ thống)" in b.locator("[data-testid=data-scope-superuser]").inner_text())
                ok("PV-14 superuser: không chữ phụ 'theo nhóm/theo quyền'", "theo nhóm" not in txt and "theo quyền" not in txt)
            else:
                ok(f"PV-14 {user}: không có dòng 'Toàn bộ' (chỉ superuser)", b.locator("[data-testid=data-scope-superuser]").count() == 0)
            ok(f"PV-14 {user} {w}px: không có giá vốn/dữ liệu khách trong khối", not PII.search(txt) and not re.search(r"purchase_rate|unit_cost|landed", txt))
            b.screenshot(path=f"{SHOTS}/pv14-{user}-{w}.png")
            # Lỗi console thật (bỏ nhiễu của máy chủ tĩnh Python: tải trước RSC, kết nối đóng) không được có.
            real = [x for x in logs if not re.search(r"RSC payload|Failed to load resource|ERR_", x)]
            ok(f"PV-14 {user} {w}px: console không lỗi", not real, real[:2])
            ctx.close()


def case_account_refresh(browser):
    # BR-PQ-36 + PV-14-AC6: Chủ đổi D6 của nhóm kho → "Tải lại quyền" ở Tài khoản của qa_warehouse đổi dòng Phiếu nhập; me kế tiếp thấy ngay.
    ctx, page, logs = login(browser, "qa_warehouse")
    open_account(page)
    ok("BR-PQ-36: trước đổi, Phiếu nhập = 'Tất cả phiếu'", "Tất cả phiếu" in row(page, "receipts").inner_text(), row(page, "receipts").inner_text())
    narrow("warehouse_staff", {"receipts": "created_by_me_today"}, {"receipts": "all"})
    page.get_by_role("button", name="Tải lại quyền").click()
    expect(row(page, "receipts")).to_contain_text("Do tôi tạo trong ngày")
    ok("BR-PQ-36: sau 'Tải lại quyền', Phiếu nhập = 'Do tôi tạo trong ngày' theo nhóm Nhân viên kho", "theo nhóm Nhân viên kho" in row(page, "receipts").inner_text(), row(page, "receipts").inner_text())
    ctx.close()
    restore_all()


def case_nogroup(browser):
    # PV-14-AC2: người không nhóm (có quyền gán riêng) → /me 200 với 8 dòng "Không xem"; mọi API ERP 403 AUTH_NO_ROLE; UI vào màn "chưa có nhóm".
    t = token_of("qa_nogroup")
    st, me = api("GET", "/api/auth/me/", t)
    ok("nogroup: /me 200 với 8 dòng 'Không xem', via_group null", st == 200 and len(me["data_scopes"]) == 8 and all(d["value"] == "none" and d["via_group"] is None and d["value_label"] == "Không xem" for d in me["data_scopes"]), me.get("data_scopes"))
    codes = []
    for path in ("/api/sales/orders/", "/api/delivery/notes/", "/api/inventory/returns/", "/api/purchasing/receipts/", "/api/sales/customers/", "/api/sales/invoices/", "/api/confirmation/queue/", "/api/sales/refunds/"):
        s, b = api("GET", path, t)
        codes.append((path, s, b.get("code") if isinstance(b, dict) else None))
    ok("nogroup: mọi API ERP đều 403 AUTH_NO_ROLE", all(s == 403 and c == "AUTH_NO_ROLE" for _, s, c in codes), codes)
    ctx = browser.new_context(viewport={"width": 360, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill("qa_nogroup")
    page.get_by_label("Mật khẩu").fill(PW)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_timeout(2500)
    body = page.locator("body").inner_text()
    ok("nogroup: UI đưa tới màn 'chưa có nhóm', không lộ dữ liệu khách", "no-role" in page.url and not PII.search(page.locator("html").inner_html()), (page.url, body[:200]))
    page.screenshot(path=f"{SHOTS}/nogroup.png")
    ctx.close()


def case_hidden_v2(browser):
    # §2.7 + câu 7: Chủ tắt V2 của warehouse_staff.
    set_group("warehouse_staff", caps={"view_order_customer_info": False})
    RESTORE.append(("warehouse_staff", None))
    try:
        ctx, page, logs = login(browser, "qa_warehouse")
        go(page, "/orders/")
        expect(page.locator("table tbody tr").first).to_be_visible()
        main = page.locator("main").inner_text()
        ok("§2.7 V2 tắt: danh sách đơn ghi 'Đã ẩn (không có quyền xem thông tin khách)', không lộ tên/SĐT", HIDDEN in main and not PII.search(page.locator("html").inner_html()), main[:200])
        go(page, "/orders/detail/?id=%d" % IDS["orders"]["QA-SO-04"]["id"])
        page.wait_for_timeout(1200)
        main = page.locator("main").inner_text()
        ok("§2.7 V2 tắt: chi tiết đơn có ít nhất 3 chỗ ghi lý do ẩn (tên, SĐT, địa chỉ) và không lộ giá trị", main.count(HIDDEN) >= 3 and not PII.search(page.locator("html").inner_html()), main.count(HIDDEN))
        page.screenshot(path=f"{SHOTS}/v2-off-order-detail.png")
        go(page, "/accounting/sales-invoices/")
        expect(page.locator("table tbody tr").first).to_be_visible()
        ok("§2.7 V2 tắt: danh sách hoá đơn bán KHÔNG có cột Khách hàng", page.locator("table thead th", has_text="Khách hàng").count() == 0)
        ok("§2.7 V2 tắt: hoá đơn bán không lộ tên/SĐT", not PII.search(page.locator("html").inner_html()))
        # Câu 7 (decisions 08/10): phiếu giao KHÔNG áp V2 → NV kho vẫn thấy đủ.
        go(page, "/deliveries/detail/?id=%d" % IDS["delivery_notes"]["QA-GH-04"]["id"])
        page.wait_for_timeout(1500)
        html = page.locator("main").inner_text()
        ok("Hồi quy câu 7: NV kho (V2 tắt) vẫn thấy tên khách trên phiếu giao", "Khách QA Giả 04" in html, html[:300])
        ok("Hồi quy câu 7: vẫn thấy SĐT khách trên phiếu giao", "0900000004" in html, html[:300])
        ok("Hồi quy câu 7: vẫn thấy địa chỉ giao trên phiếu giao", "QA-Địa chỉ giả số 4" in html, html[:300])
        ok("Hồi quy câu 7: phiếu giao không ghi 'Đã ẩn (không có quyền xem thông tin khách)'", HIDDEN not in html)
        page.screenshot(path=f"{SHOTS}/v2-off-delivery-note.png")
        ctx.close()
        # Phiếu hoàn tiền (Quản lý): tắt V2 của manager.
        set_group("manager", caps={"view_order_customer_info": False})
        RESTORE.append(("manager", None))
        ctx, page, logs = login(browser, "qa_manager")
        go(page, "/orders/refunds/")
        page.wait_for_timeout(1500)
        main = page.locator("main").inner_text()
        ok("§2.7 V2 tắt: danh sách phiếu hoàn tiền không lộ tên/SĐT", not PII.search(page.locator("html").inner_html()), main[:300])
        go(page, "/orders/refunds/detail/?id=%d" % IDS["refunds"]["QA-REFUND-PENDING"]["id"])
        page.wait_for_timeout(1500)
        main = page.locator("main").inner_text()
        ok("§2.7 V2 tắt: chi tiết phiếu hoàn tiền ghi 'Đã ẩn (không có quyền xem thông tin khách)', không lộ tên/SĐT", HIDDEN in main and not PII.search(page.locator("html").inner_html()), main[:400])
        page.screenshot(path=f"{SHOTS}/v2-off-refund-detail.png")
        ctx.close()
    finally:
        set_group("manager", caps={"view_order_customer_info": True}, widen=True)
        set_group("warehouse_staff", caps={"view_order_customer_info": True}, widen=True)
        RESTORE[:] = [r for r in RESTORE if r[1] is not None]
    # Bật lại (có xác nhận) → hiện tên.
    ctx, page, logs = login(browser, "qa_warehouse")
    go(page, "/orders/")
    expect(page.locator("table tbody tr").first).to_be_visible()
    ok("§2.7 bật lại V2: danh sách đơn hiện lại tên khách, không còn chữ 'Đã ẩn (không có quyền…)'", "Khách QA Giả" in page.locator("main").inner_text() and HIDDEN not in page.locator("main").inner_text())
    ctx.close()


def case_courier_expired(browser):
    # Hồi quy (ca 15): phiếu của NV giao đã kết thúc quá cửa sổ → "Đã ẩn (quá 7 ngày)" (QA-GH-08 đã lùi completed_at 10 ngày, chỉ DB tạm).
    ctx, page, logs = login(browser, "qa_courier1")
    go(page, "/deliveries/detail/?id=%d" % IDS["delivery_notes"]["QA-GH-08"]["id"])
    page.wait_for_timeout(1500)
    main = page.locator("main").inner_text()
    ok("Hồi quy: phiếu quá cửa sổ của NV giao ghi 'Đã ẩn (quá 7 ngày)'", "Đã ẩn (quá 7 ngày)" in main, main[:300])
    ok("Hồi quy: phiếu quá cửa sổ không lộ tên/SĐT/địa chỉ khách", not PII.search(page.locator("html").inner_html()))
    page.screenshot(path=f"{SHOTS}/courier-expired.png")
    go(page, "/my-deliveries/")
    page.wait_for_timeout(1500)
    ok("Hồi quy: 'Việc giao của tôi' không lộ dữ liệu khách của phiếu quá hạn (QA-GH-08)", "QA-Địa chỉ giả số 8" not in page.locator("html").inner_html() and "0900000008" not in page.locator("html").inner_html())
    ctx.close()


CASES = {k[5:]: v for k, v in globals().items() if k.startswith("case_")}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(CASES)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name in wanted:
            print(f"--- {name}", flush=True)
            try:
                CASES[name](browser)
            except Exception as e:  # ghi nhận ca lỗi kịch bản, vẫn khôi phục cấu hình
                import traceback
                traceback.print_exc()
                ok(f"CA {name} chạy hết không lỗi kịch bản", False, repr(e))
                restore_all()
        browser.close()
    finish(R)
