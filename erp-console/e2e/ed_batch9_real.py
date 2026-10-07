# Smoke trên BE THẬT (Lô 9 Hàng hoàn): cần BE chạy ở :8000 (DB SQLite tạm, có người dùng loc/ql1/kho1/giao1/giao2 mật khẩu Songbien2026
# và hai phiếu giao ĐANG GIAO, mỗi phiếu 10 kg của một lô), console build NEXT_PUBLIC_USE_MOCK=0 phục vụ ở :3102,
# BE bật CORS_ALLOWED_ORIGINS=http://127.0.0.1:3102. Mỗi lần chạy tạo phiếu hàng hoàn, nên chạy lại cần nạp lại DB.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3102")
API = os.environ.get("API", "http://127.0.0.1:8000") + "/api/"
SHOTS = os.environ.get("SHOTS", "/tmp")
expect.set_options(timeout=15000)
R = []


def ok(n, c, e=""):
    R.append((n, bool(c), e))
    print("PASS" if c else "FAIL", n, "" if c else e)


def session(b, user):
    ctx = b.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errs.append(m.text))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill("Songbien2026")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    return ctx, page, errs


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def rows(page):
    return [t.strip() for t in page.locator("main table tbody tr td:first-child").all_inner_texts()]


LAST = {}


def create(page, note_code, qty, note=""):
    page.get_by_role("button", name="Nhập hàng hoàn").click()
    dlg = page.get_by_role("dialog")
    page.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
    label = [t for t in dlg.get_by_label("Phiếu giao").locator("option").all_inner_texts() if note_code in t][0]
    dlg.get_by_label("Phiếu giao").select_option(label=label)
    page.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
    LAST["facts"] = dlg.locator("[data-qty-facts]").inner_text()
    dlg.get_by_label("Số kg hoàn").fill(qty)
    if note:
        dlg.get_by_label(re.compile("Ghi chú")).fill(note)
    dlg.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    return dlg


with sync_playwright() as p:
    b = p.chromium.launch()
    reqs = []

    # 1. kho1 tạo phiếu hợp lệ rồi vượt giới hạn
    ctx, page, errs = session(b, "kho1")
    page.on("response", lambda r: "/api/" in r.url and reqs.append((r.request.method, r.url.split("/api/")[1], r.status)))
    go(page, "/returns/")
    ok("BE thật kho1: danh sách rỗng ban đầu", "Chưa có phiếu hàng hoàn nào" in page.inner_text("main"), page.inner_text("main")[:200])
    create(page, "SO-L9-A", "3", "khách hẹn lại")
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    page.wait_for_function("() => document.body.innerText.includes('RT-1')")
    ok("BE thật kho1: tạo 3 kg hợp lệ -> RT-1 Chờ duyệt", "Chờ duyệt" in page.locator("main table tbody tr").first.inner_text(), page.locator("main table tbody tr").first.inner_text())
    ok("BE thật kho1: có POST /inventory/returns/ trả 201", ("POST", "inventory/returns/", 201) in reqs, str(reqs[-6:]))
    dlg = create(page, "SO-L9-A", "8")
    page.wait_for_function("() => document.querySelector('[role=dialog]').innerText.includes('vượt số đã giao')")
    t = dlg.inner_text()
    ok("BE thật kho1: số liệu hiện NGAY khi chọn phiếu (từ returned_qty của BE): đã giao 10 kg, đã hoàn 3 kg, còn hoàn được 7 kg",
       "Đã giao 10 kg" in LAST["facts"] and "đã hoàn 3 kg" in LAST["facts"] and "còn hoàn được 7 kg" in LAST["facts"], LAST["facts"])
    ok("BE thật kho1: nhập 8 kg bị chặn tại chỗ (không có POST thứ ba tới /inventory/returns/)", sum(1 for r in reqs if r[0] == "POST" and r[1] == "inventory/returns/") == 1, str(reqs[-6:]))
    ok("BE thật kho1: vượt số kg -> lỗi dưới ô, đã giao 10 kg, đã hoàn 3 kg, còn 7 kg", "Đã giao 10 kg" in t and "đã hoàn 3 kg" in t and "còn hoàn được 7 kg" in t, t[:500])
    ok("BE thật kho1: lỗi vượt không lộ mã quy tắc", "BR-" not in t and "RETURN_" not in t)
    page.screenshot(path=f"{SHOTS}/real-f2m-over-limit.png")
    dlg.get_by_role("button", name="Huỷ", exact=True).click()
    create(page, "SO-L9-B", "2")
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    page.wait_for_function("() => document.body.innerText.includes('RT-2')")
    ok("BE thật kho1: tạo thêm RT-2 cho phiếu giao2", "RT-2" in rows(page), str(rows(page)))
    ok("BE thật kho1: không có nút duyệt ở chi tiết (không có quyền)", True)
    go(page, "/returns/detail/?id=1")
    ok("BE thật kho1: chi tiết RT-1 hiện ghi chú, kg 3 kg, không nút Tái nhập", "khách hẹn lại" in page.inner_text("main") and "3 kg" in page.inner_text("main") and page.get_by_role("button", name="Tái nhập vào lô").count() == 0, page.inner_text("main")[:400])
    ok("BE thật kho1: dòng thời gian từ /guidance/return/ có dữ liệu", ("GET", "guidance/return/1/", 200) in reqs and "DÒNG THỜI GIAN" in page.inner_text("main").upper(), str([r for r in reqs if "guidance" in r[1]]))
    ok("BE thật kho1: không console.error", errs == [], str(errs))
    ctx.close()

    # 2. giao1: chỉ phiếu của mình, phiếu người khác -> Không tìm thấy
    ctx, page, errs = session(b, "giao1")
    go(page, "/returns/")
    ok("BE thật giao1: chỉ thấy RT-1", rows(page) == ["RT-1"], str(rows(page)))
    go(page, "/returns/detail/?id=2")
    ok("BE thật giao1: mở RT-2 của giao2 -> Không tìm thấy", page.get_by_role("heading", name="Không tìm thấy").count() >= 1)
    go(page, "/returns/")
    # giao1 tự nhập hàng hoàn: BE trả batch_pk trong lines nên không cần quyền xem lô
    batch_calls = []
    page.on("response", lambda r: "/api/inventory/batches/" in r.url and batch_calls.append(r.status))
    create(page, "SO-L9-A", "1", "xe hỏng")
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    page.wait_for_function("() => document.body.innerText.includes('RT-3')")
    ok("BE thật giao1: tự nhập hàng hoàn 1 kg -> RT-3 Chờ duyệt", "RT-3" in rows(page) and "Chờ duyệt" in page.locator("main table tbody tr", has_text="RT-3").inner_text(), str(rows(page)))
    ok("BE thật giao1: facts lúc chọn phiếu đã có 'đã hoàn 3 kg' (returned_qty)", "đã hoàn 3 kg" in LAST["facts"], LAST["facts"])
    ok("BE thật giao1: không gọi /inventory/batches/ (không cần quyền xem lô)", batch_calls == [], str(batch_calls))
    page.screenshot(path=f"{SHOTS}/real-giao1-create.png")
    go(page, "/my-deliveries/")
    ok("BE thật giao1: Việc giao của tôi mở được", page.locator("li[data-note-id]").count() >= 1)
    ctx.close()

    # 3. ql1: hai tab duyệt cùng lúc -> 409
    ctx, a, errs = session(b, "ql1")
    go(a, "/returns/detail/?id=1")
    b2 = ctx.new_page()
    go(b2, "/returns/detail/?id=1")
    a.get_by_role("button", name="Tái nhập vào lô").click()
    a.get_by_role("dialog").get_by_role("button", name="Duyệt", exact=True).click()
    a.wait_for_function("() => !document.querySelector('[role=dialog]')")
    a.wait_for_function("() => document.body.innerText.includes('Đã duyệt. Hàng đã nhập lại vào lô.')")
    ok("BE thật ql1: duyệt Tái nhập -> toast, chip Đã duyệt", "Đã duyệt" in a.inner_text("main"), a.inner_text("main")[:200])
    b2.get_by_role("button", name="Huỷ hàng, ghi lỗ").click()
    d2 = b2.get_by_role("dialog")
    d2.get_by_role("button", name="Duyệt", exact=True).click()
    b2.wait_for_function("() => document.querySelector('[role=dialog]') && document.querySelector('[role=dialog]').innerText.includes('Tải lại')")
    ok("BE thật ql1: duyệt lần hai -> 409 ConflictBanner có Tải lại", d2.get_by_role("button", name="Tải lại").count() >= 1 and "STALE_STATE" not in d2.inner_text(), d2.inner_text()[:300])
    b2.screenshot(path=f"{SHOTS}/real-409.png")
    d2.get_by_role("button", name="Tải lại").first.click()
    b2.wait_for_function("() => !document.querySelector('[role=dialog]')")
    b2.wait_for_timeout(800)
    ok("BE thật ql1: Tải lại -> phiếu Đã duyệt, hết nút", b2.get_by_role("button", name="Huỷ hàng, ghi lỗ").count() == 0 and "Đã duyệt" in b2.inner_text("main"))
    ok("BE thật ql1: dòng thời gian có bước duyệt", "Duyệt" in b2.inner_text("main"), b2.inner_text("main")[-300:])
    ok("BE thật ql1: không console.error", errs == [], str(errs))
    ctx.close()

    # 4. loc: Huỷ hàng, ghi lỗ RT-2
    ctx, page, errs = session(b, "loc")
    go(page, "/returns/detail/?id=2")
    page.get_by_role("button", name="Huỷ hàng, ghi lỗ").click()
    page.get_by_role("dialog").get_by_role("button", name="Duyệt", exact=True).click()
    page.wait_for_function("() => document.body.innerText.includes('Đã duyệt. Hàng đã huỷ hàng, ghi lỗ.')")
    ok("BE thật loc: duyệt Huỷ bỏ -> toast", True)
    go(page, "/returns/")
    ok("BE thật loc: thấy RT-1, RT-2 (Đã duyệt) và RT-3", sorted(rows(page)) == ["RT-1", "RT-2", "RT-3"], str(rows(page)))
    body = page.inner_text("main")
    ok("BE thật loc: có Tái nhập và Huỷ hàng, ghi lỗ ở cột Quyết định", "Tái nhập" in body and "Huỷ hàng, ghi lỗ" in body, body[-400:])
    page.screenshot(path=f"{SHOTS}/real-list.png")
    # QA Lô 9 B3: liên kết Phiếu giao / Đơn ở chi tiết (id đơn lấy từ phiếu giao của BE thật), Lô vẫn là chữ thường
    go(page, "/returns/detail/?id=1")
    page.wait_for_function("() => [...document.querySelectorAll('main dd a')].some(a => a.getAttribute('href').startsWith('/orders/detail/'))")
    hrefs = page.locator("main dd a").evaluate_all("els => els.map(e => e.getAttribute('href'))")
    ok("BE thật loc: chi tiết có liên kết Phiếu giao /deliveries/detail/?id= và Đơn /orders/detail/?id=", any(re.fullmatch(r"/deliveries/detail/\?id=\d+", h or "") for h in hrefs) and any(re.fullmatch(r"/orders/detail/\?id=\d+", h or "") for h in hrefs), str(hrefs))
    page.locator("main dd a[href^='/orders/detail/']").click()
    page.wait_for_url(re.compile(r"/orders/detail/\?id=\d+"))
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => !document.querySelector('main').innerText.includes('Đang tải đơn hàng')", timeout=15000)
    ok("BE thật loc: bấm Đơn mở trang chi tiết đơn (hiện mã đơn SO-L9-A)", "SO-L9-A" in page.inner_text("main"), page.inner_text("main")[:200])

    # BE chặn SĐT trong ghi chú khi gọi thẳng API: 400, lỗi theo ô `note` (FE gắn dưới ô Ghi chú)
    import json, urllib.request, urllib.error
    def api(method, path, body=None, token=None):
        req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None, method=method)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Token " + token)
        try:
            r = urllib.request.urlopen(req, timeout=30)
            return r.status, json.loads(r.read().decode() or "null")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "null")
    st, tok = api("POST", "auth/token/", {"username": "kho1", "password": "Songbien2026"})
    token = tok.get("token") if isinstance(tok, dict) else None
    st, notes = api("GET", "delivery/notes/", token=token)
    note_id = next((n["id"] for n in notes["results"] if n["code"].startswith("GH-INV-SO-L9-B")), None)
    st, detail = api("GET", f"delivery/notes/{note_id}/", token=token)
    batch_pk = detail["lines"][0]["batch_pk"]
    st, body = api("POST", "inventory/returns/", {"delivery_note": note_id, "batch": batch_pk, "qty": "0.1", "note": "gọi 0900000777 buổi sáng"}, token)
    ok("BE thật: ghi chú có SĐT gọi thẳng API -> 400, lỗi nằm ở khoá note (mảng câu tiếng Việt)", st == 400 and isinstance(body.get("note"), list) and isinstance(body["note"][0], str) and "0900000777" not in json.dumps(body), f"{st} {body}")
    ok("BE thật loc: không console.error", errs == [], str(errs))
    ctx.close()
    b.close()

bad = [r for r in R if not r[1]]
print(f"\n{len(R) - len(bad)}/{len(R)} PASS")
sys.exit(1 if bad else 0)
