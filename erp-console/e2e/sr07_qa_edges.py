# QA P8 Lô 2 — SR-07: ca NGOÀI đường thuận của nháp "Nhập lô" (bổ sung cho sr07_receive_batches_draft.py).
# Dữ liệu giả. Hai chế độ:
#   MODE=mock  BASE=http://127.0.0.1:3212  (build NEXT_PUBLIC_USE_MOCK=1, tài khoản demo1234)
#   MODE=real  BASE=http://127.0.0.1:3213  API=http://127.0.0.1:8123  (Django thật + DB sqlite tạm, loc/kho1 mật khẩu PW)
#     build:  NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8123 npm run build
#     Django: DATABASE_URL=sqlite:///<tmp>.sqlite3 manage.py migrate + bootstrap_masterdata, tạo loc (owner), kho1 (warehouse_staff),
#             1 Item CA-GIA-1, 1 Supplier; CORS_ALLOWED_ORIGINS=<BASE> runserver 127.0.0.1:8123 --noreload
# Ca: tab khác / phiên (context) khác · hết phiên không bấm đăng xuất · khoá cũ + đăng xuất mà chưa mở form ·
#     nháp hỏng / nháp cũ có rate · console + URL sạch · (real) bấm đúp gửi, mất mạng sau khi server đã ghi rồi F5 gửi lại.
import json
import os
import sys

from playwright.sync_api import sync_playwright

MODE = os.environ.get("MODE", "mock")
BASE = os.environ.get("BASE", "http://127.0.0.1:3212")
API = os.environ.get("API", "http://127.0.0.1:8123")
PW = os.environ.get("PW", "demo1234" if MODE == "mock" else "Songbien2026")
SHOTS = os.environ.get("SHOTS", "/tmp")
RATE = "81234"
RSUB = "81000"  # ô giá có step=1000 -> số hợp lệ để gửi thật
results = []
console_msgs = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def watch(page):
    page.on("console", lambda m: console_msgs.append((m.type, m.text)))
    page.on("pageerror", lambda e: console_msgs.append(("pageerror", str(e))))


def login(page, user):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", PW)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15_000)
    page.wait_for_load_state("networkidle")


def logout(page):
    page.goto(BASE + "/account/")
    page.wait_for_load_state("networkidle")
    page.locator("button.btn.danger", has_text="Đăng xuất").click()
    page.wait_for_url("**/login/**", timeout=10_000)
    page.wait_for_load_state("networkidle")


def open_receive_batches(page):
    page.goto(BASE + "/purchasing/")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input[placeholder='80000']", timeout=15_000)
    page.wait_for_timeout(400)


def storages(page):
    return page.evaluate(
        "() => ({ local: JSON.stringify(localStorage), session: JSON.stringify(sessionStorage), "
        "localKeys: Object.keys(localStorage), sessionKeys: Object.keys(sessionStorage) })"
    )


def draft_of(page):
    return page.evaluate(
        """() => { const k = Object.keys(sessionStorage).find(x => x.startsWith('cave_draft_receive_batches:'));
                   if (!k) return null; try { return JSON.parse(sessionStorage.getItem(k)) } catch (e) { return null } }"""
    )


def key_of(page):
    d = draft_of(page)
    return (d or {}).get("idempotencyKey")


def rate_box(page):
    return page.locator("input[placeholder='80000']").first


def pick_supplier(page):
    sel = page.locator("select").first
    if sel.input_value() == "":
        sel.select_option(index=1)


def qty_box(page):
    return page.locator("input[placeholder='0.000']").first


def no_rate(page, val=RATE):
    st = storages(page)
    return val not in st["local"] and val not in st["session"]


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ---------- A. Tab khác cùng người, cùng trình duyệt ----------
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    watch(page)
    login(page, "loc")
    open_receive_batches(page)
    qty_box(page).fill("12")
    rate_box(page).fill(RATE)
    page.wait_for_timeout(400)
    key1 = key_of(page)
    ok("A0 tab 1: có nháp + key", bool(key1) and draft_of(page)["lines"][0]["qty"] == "12")
    tab2 = ctx.new_page()
    watch(tab2)
    open_receive_batches(tab2)
    ok("A1 tab 2 (cùng người): ô số lượng rỗng, ô giá rỗng (sessionStorage không chia sẻ giữa tab)",
       qty_box(tab2).input_value() == "" and rate_box(tab2).input_value() == "")
    ok("A2 tab 2: key khác tab 1", bool(key_of(tab2)) and key_of(tab2) != key1)
    ok("A3 tab 2: storage không chứa 81234", no_rate(tab2))
    ok("A4 localStorage dùng chung giữa 2 tab không chứa 81234", RATE not in storages(page)["local"])
    tab2.close()

    # ---------- B. Phiên/trình duyệt khác (context riêng) ----------
    ctx_b = browser.new_context(viewport={"width": 1280, "height": 900})
    pb = ctx_b.new_page()
    watch(pb)
    login(pb, "loc")
    open_receive_batches(pb)
    ok("B1 phiên khác (cùng Chủ): ô rỗng, không nháp của phiên 1", qty_box(pb).input_value() == "" and rate_box(pb).input_value() == "")
    ok("B2 phiên khác: key khác", bool(key_of(pb)) and key_of(pb) != key1)
    ctx_b.close()

    # ---------- C. Hết phiên (không bấm đăng xuất): Chủ gõ giá -> token mất -> warehouse_staff vào cùng tab ----------
    page.screenshot(path=os.path.join(SHOTS, "qa-sr07-C0-chu-dang-go.png"), full_page=True)
    tok_key = page.evaluate("() => Object.keys(localStorage).find(k => /token/i.test(k)) || null")
    ok("C0 tìm thấy khoá token để giả lập hết phiên", tok_key is not None, str(tok_key))
    page.evaluate("(k) => localStorage.removeItem(k)", tok_key)  # như 401 hết hạn: token mất, không qua logout()
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    login(page, "kho1")
    open_receive_batches(page)
    ok("C1 hết phiên rồi warehouse_staff vào cùng tab: ô số lượng + ô giá rỗng", qty_box(page).input_value() == "" and rate_box(page).input_value() == "")
    ok("C2 storage không chứa 81234", no_rate(page))
    # C2b: nháp của Chủ (userId khác) còn sót ở sessionStorage cùng tab -> warehouse_staff không đọc được
    page.evaluate("() => sessionStorage.setItem('cave_draft_receive_batches:1', JSON.stringify({supplierId: 1, receivedDate: '2026-09-30', lines: [{item_code: '', qty: '77', shelf_life_days: null}], idempotencyKey: 'key-cua-chu'}))")
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input[placeholder='80000']", timeout=15_000)
    page.wait_for_timeout(400)
    ok("C2b nháp của Chủ (userId 1) còn ở sessionStorage: warehouse_staff không thấy (qty rỗng) và không dùng key của Chủ", qty_box(page).input_value() != "77" and page.evaluate("() => { const k = Object.keys(sessionStorage).find(x => x.startsWith('cave_draft_receive_batches:') && !x.endsWith(':1')); return k ? JSON.parse(sessionStorage.getItem(k)).idempotencyKey : null }") not in (None, "key-cua-chu"))
    dumped = storages(page)["session"]
    ok("C3 nháp còn sót của Chủ (nếu có) không chứa trường rate", '"rate"' not in dumped and "rate" not in dumped.replace("idempotencyKey", ""), dumped[:200])
    ok("C4 key của warehouse_staff khác key của Chủ", key_of(page) != key1 and bool(key_of(page)))
    page.screenshot(path=os.path.join(SHOTS, "qa-sr07-C1-nv-kho-sau-het-phien.png"), full_page=True)
    logout(page)

    # ---------- D. Khoá cũ có giá mua, đăng xuất mà CHƯA mở Nhập lô ----------
    page.goto(BASE + "/login/")
    page.evaluate("(r) => localStorage.setItem('cave_draft_nhap_lo', JSON.stringify({lines:[{item_code:'X',qty:'1',rate:r}]}))", RATE)
    login(page, "loc")
    page.goto(BASE + "/account/")
    page.wait_for_load_state("networkidle")
    ok("D0 (điều kiện) khoá cũ còn nguyên khi chưa mở Nhập lô", page.evaluate("() => localStorage.getItem('cave_draft_nhap_lo')") is not None)
    logout(page)
    ok("D1 đăng xuất (chưa mở Nhập lô) xoá khoá cũ có giá mua", page.evaluate("() => localStorage.getItem('cave_draft_nhap_lo')") is None and no_rate(page))

    # ---------- E. Nháp hỏng / nháp theo userId nhưng có rate (định dạng cũ) ----------
    login(page, "loc")
    open_receive_batches(page)
    uid = page.evaluate("() => { const k = Object.keys(sessionStorage).find(x => x.startsWith('cave_draft_receive_batches:')); return k ? k.split(':')[1] : null }")
    ok("E0 lấy được userId từ khoá nháp", uid is not None, str(uid))
    page.evaluate("([u]) => sessionStorage.setItem('cave_draft_receive_batches:' + u, '{hỏng')", [uid])
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input[placeholder='80000']", timeout=15_000)
    ok("E1 nháp JSON hỏng: form vẫn mở, ô rỗng", rate_box(page).input_value() == "" and qty_box(page).input_value() == "")
    page.evaluate(
        "([u, r]) => sessionStorage.setItem('cave_draft_receive_batches:' + u, JSON.stringify({supplierId: 1, receivedDate: '2026-09-30', "
        "lines: [{item_code: '', qty: '9', rate: r, shelf_life_days: null}], idempotencyKey: 'k-cu'}))",
        [uid, RATE],
    )
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input[placeholder='80000']", timeout=15_000)
    page.wait_for_timeout(400)
    ok("E2 nháp cũ có rate: ô số lượng 9 còn, ô giá rỗng", qty_box(page).input_value() == "9" and rate_box(page).input_value() == "")
    ok("E3 sau khi nạp, nháp ghi lại đã bỏ rate (storage không còn 81234)", no_rate(page), storages(page)["session"][:200])
    ok("E4 key trong nháp cũ được giữ (cùng người)", key_of(page) == "k-cu")

    # ---------- F. URL + console ----------
    ok("F1 URL không có query/giá mua/dữ liệu cá nhân", "?" not in page.url and RATE not in page.url, page.url)
    bad = [m for m in console_msgs if RATE in m[1] or "0900" in m[1]]
    ok("F2 console không có 81234 hay SĐT", not bad, str(bad)[:200])
    # "Failed to fetch RSC payload" = prefetch của Next bị huỷ khi page.goto() chuyển trang giữa chừng (http.server tĩnh) — nhiễu môi trường, không thuộc SR-07.
    errs = [m for m in console_msgs if m[0] in ("error", "pageerror") and "favicon" not in m[1] and "Failed to fetch RSC payload" not in m[1]]
    ok("F3 console/pageerror không có lỗi đỏ", not errs, str(errs)[:300])
    logout(page)
    ctx.close()

    # ---------- R. (chỉ real) gửi thật: bấm đúp, mất mạng sau khi server đã ghi rồi F5 gửi lại ----------
    if MODE == "real":
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        watch(page)
        login(page, "loc")
        tok = page.evaluate("() => localStorage.getItem('cave_erp_token')")
        H = {"Authorization": f"Token {tok}"}

        def receipts():
            r = ctx.request.get(API + "/api/purchasing/receipts/", headers=H)
            j = r.json()
            return j["results"] if isinstance(j, dict) and "results" in j else j

        base_n = len(receipts())
        posts = []
        page.on("request", lambda rq: rq.method == "POST" and "receive-batches" in rq.url and posts.append(json.loads(rq.post_data or "{}")))

        # R1: bấm đúp
        open_receive_batches(page)
        pick_supplier(page)
        page.locator("table select").first.select_option(index=1)
        qty_box(page).fill("3")
        rate_box(page).fill(RSUB)
        btn = page.get_by_role("button", name="Ghi nhận phiếu nhập")
        btn.dblclick()
        page.wait_for_selector("text=Ghi nhận phiếu nhập thành công", timeout=15_000)
        page.wait_for_timeout(500)
        ok("R1 bấm đúp: số POST gửi lên <= 2 và cùng key; server chỉ ghi 1 phiếu", len(receipts()) - base_n == 1 and len({b.get("idempotency_key") for b in posts}) == 1,
           f"posts={len(posts)} receipts_moi={len(receipts()) - base_n}")
        ok("R1b sau thành công: storage không chứa 81000", no_rate(page, RSUB))
        page.get_by_role("button", name="Nhập phiếu tiếp").click()
        page.wait_for_selector("input[placeholder='80000']", timeout=10_000)
        page.wait_for_timeout(400)

        # R2: server đã ghi nhưng mạng đứt lúc trả về -> người dùng F5 rồi gửi lại
        posts.clear()
        state = {"n": 0}

        def flaky(route):
            state["n"] += 1
            if state["n"] == 1:
                route.fetch()  # server thật xử lý và GHI phiếu
                route.abort()  # nhưng trình duyệt không nhận được phản hồi
            else:
                route.continue_()

        page.route("**/api/purchasing/receipts/receive-batches/", flaky)
        before = len(receipts())
        pick_supplier(page)
        page.locator("table select").first.select_option(index=1)
        qty_box(page).fill("4")
        rate_box(page).fill(RSUB)
        page.wait_for_timeout(400)
        key_before = key_of(page)
        page.get_by_role("button", name="Ghi nhận phiếu nhập").click()
        page.wait_for_timeout(1500)
        ok("R2a mạng đứt: form còn, chưa báo thành công", page.locator("text=Ghi nhận phiếu nhập thành công").count() == 0)
        ok("R2b server đã ghi 1 phiếu dù trình duyệt không nhận phản hồi", len(receipts()) - before == 1, str(len(receipts()) - before))
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("input[placeholder='80000']", timeout=15_000)
        page.wait_for_timeout(400)
        ok("R2c F5: nháp giữ số lượng 4, giá rỗng, cùng key", qty_box(page).input_value() == "4" and rate_box(page).input_value() == "" and key_of(page) == key_before,
           f"key_before={bool(key_before)} same={key_of(page) == key_before}")
        ok("R2d F5: storage không chứa 81000", no_rate(page, RSUB))
        pick_supplier(page)
        if page.locator("table select").first.input_value() == "":
            page.locator("table select").first.select_option(index=1)  # mặt hàng chưa được nháp lưu -> chọn lại
        rate_box(page).fill(RSUB)  # người dùng gõ lại giá vì không được lưu
        page.get_by_role("button", name="Ghi nhận phiếu nhập").click()
        page.wait_for_timeout(1500)
        ok("R2e gửi lại cùng key: server KHÔNG tạo phiếu thứ hai", len(receipts()) - before == 1, str(len(receipts()) - before))
        page.screenshot(path=os.path.join(SHOTS, "qa-sr07-R2-gui-lai-sau-f5.png"), full_page=True)
        page.unroute("**/api/purchasing/receipts/receive-batches/")
        ok("R3 storage cuối không chứa 81000", no_rate(page, RSUB))
        errs = [m for m in console_msgs if m[0] == "pageerror"]
        ok("R4 không có pageerror", not errs, str(errs)[:200])
        ctx.close()

    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
