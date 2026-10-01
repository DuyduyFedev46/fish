# SR-07-AC3 (P8 Lô 2): nháp "Nhập lô" không giữ giá mua giữa các người dùng.
# Chủ (loc) đăng nhập, gõ giá mua 81234, đăng xuất; warehouse_staff (kho1) đăng nhập, mở Nhập lô -> ô giá rỗng,
# localStorage/sessionStorage không chứa 81234. Dữ liệu giả (mock, tài khoản demo).
# Chạy: cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out <thư-mục-riêng>/out
#       (cd <thư-mục-riêng>/out && python3 -m http.server 3212 &)
#       python3 e2e/sr07_receive_batches_draft.py     # tắt server sau khi xong
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3212")
SHOTS = os.environ.get(
    "SHOTS",
    os.path.join(os.path.dirname(__file__), "..", "..", "doc", "features", "2026-09-30-sua-loi-review", "qa-lo2"),
)
RATE = "81234"
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
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
    page.wait_for_selector("input[placeholder='80000']", timeout=10_000)
    page.wait_for_timeout(300)  # để effect tự lưu nháp chạy


def storages(page):
    return page.evaluate(
        "() => ({ local: JSON.stringify(localStorage), session: JSON.stringify(sessionStorage), "
        "localKeys: Object.keys(localStorage), sessionKeys: Object.keys(sessionStorage) })"
    )


def draft_key_of(page):
    """idempotencyKey trong nháp sessionStorage của người đang đăng nhập (chỉ để kiểm, không in ra khoá cá nhân)."""
    return page.evaluate(
        """() => { const k = Object.keys(sessionStorage).find(x => x.startsWith('cave_draft_receive_batches:'));
                   if (!k) return null; try { return JSON.parse(sessionStorage.getItem(k)).idempotencyKey || null } catch (e) { return null } }"""
    )


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # 0) Giả lập máy còn khoá cũ dùng chung (localStorage) có giá mua -> phải bị dọn
    page.goto(BASE + "/login/")
    page.evaluate(
        """(rate) => localStorage.setItem('cave_draft_nhap_lo',
            JSON.stringify({supplierId: 1, lines: [{item_code: 'X', qty: '1', rate}]}))""",
        RATE,
    )

    # 1) Chủ gõ giá mua
    login(page, "loc")
    open_receive_batches(page)
    ok("Khoá cũ ở localStorage bị dọn khi mở Nhập lô", page.evaluate("() => localStorage.getItem('cave_draft_nhap_lo')") is None)
    rate_input = page.locator("input[placeholder='80000']").first
    page.locator("input[placeholder='0.000']").first.fill("12")
    rate_input.fill(RATE)
    page.wait_for_timeout(300)
    ok("Chủ: ô giá mua đang hiện 81234", rate_input.input_value() == RATE)
    st = storages(page)
    ok("Chủ: localStorage/sessionStorage KHÔNG chứa 81234 dù đang gõ", RATE not in st["local"] and RATE not in st["session"], str(st["sessionKeys"]))
    ok("Chủ: nháp nằm ở sessionStorage khoá theo userId", any(k.startswith("cave_draft_receive_batches:") for k in st["sessionKeys"]), str(st["sessionKeys"]))
    key_chu = draft_key_of(page)
    ok("Chủ: nháp có idempotencyKey", bool(key_chu))
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input[placeholder='80000']", timeout=10_000)
    page.wait_for_timeout(300)
    ok("AC4(a) F5 cùng người: giữ đúng idempotencyKey", draft_key_of(page) == key_chu)

    # P8b Lô 3: nháp session khoá CŨ của chính người này -> chuyển sang khoá mới (bỏ giá mua), khoá cũ bị xoá
    uid = page.evaluate("() => Object.keys(sessionStorage).find(x => x.startsWith('cave_draft_receive_batches:')).split(':')[1]")
    page.evaluate(
        """([u, rate]) => {
            sessionStorage.removeItem('cave_draft_receive_batches:' + u);
            sessionStorage.setItem('cave_draft_nhap_lo:' + u, JSON.stringify({supplierId: 1, receivedDate: '2026-09-30',
              lines: [{item_code: 'X', qty: '33', rate, shelf_life_days: null}], idempotencyKey: 'legacy-key-1'}));
        }""",
        [uid, "99999"],
    )
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input[placeholder='80000']", timeout=10_000)
    page.wait_for_timeout(300)
    st = storages(page)
    ok("P8b-L3 khoá cũ của chính người này đã chuyển sang khoá mới và bị xoá", "cave_draft_nhap_lo:" + uid not in st["sessionKeys"] and "cave_draft_receive_batches:" + uid in st["sessionKeys"], str(st["sessionKeys"]))
    ok("P8b-L3 nháp chuyển sang giữ số lượng 33, idempotencyKey cũ, và KHÔNG có giá mua 99999",
       page.locator("input[placeholder='0.000']").first.input_value() == "33" and draft_key_of(page) == "legacy-key-1"
       and "99999" not in st["local"] and "99999" not in st["session"] and page.locator("input[placeholder='80000']").first.input_value() == "")
    page.locator("input[placeholder='80000']").first.fill(RATE)
    page.wait_for_timeout(300)
    page.screenshot(path=os.path.join(SHOTS, "sr07-1-chu-go-gia-81234.png"), full_page=True)

    # 2) Đăng xuất -> mọi khoá nháp Nhập lô biến mất
    logout(page)
    st = storages(page)
    ok("Sau đăng xuất: không còn khoá cave_draft_receive_batches* và cave_draft_nhap_lo* (tiền tố cũ) ở local/session",
       not any(k.startswith(("cave_draft_receive_batches", "cave_draft_nhap_lo")) for k in st["localKeys"] + st["sessionKeys"]),
       f"local={st['localKeys']} session={st['sessionKeys']}")
    ok("Sau đăng xuất: storage không chứa 81234", RATE not in st["local"] and RATE not in st["session"])

    # 3) warehouse_staff đăng nhập trên cùng máy/tab
    login(page, "kho1")
    open_receive_batches(page)
    ok("warehouse_staff: ô giá mua rỗng", page.locator("input[placeholder='80000']").first.input_value() == "")
    ok("warehouse_staff: ô số lượng rỗng (nháp Chủ không sang)", page.locator("input[placeholder='0.000']").first.input_value() == "")
    st = storages(page)
    ok("warehouse_staff: storage không chứa 81234", RATE not in st["local"] and RATE not in st["session"])
    ok("AC4(b) warehouse_staff: idempotencyKey mới, khác của Chủ", bool(draft_key_of(page)) and draft_key_of(page) != key_chu)
    page.screenshot(path=os.path.join(SHOTS, "sr07-2-nv-kho-o-gia-rong.png"), full_page=True)
    key_kho = draft_key_of(page)

    # 4) Nạp lại nháp cùng người (F5): giữ số lượng, giá mua rỗng
    page.locator("input[placeholder='0.000']").first.fill("7")
    page.locator("input[placeholder='80000']").first.fill("55555")
    page.wait_for_timeout(300)
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input[placeholder='80000']", timeout=10_000)
    page.wait_for_timeout(300)
    ok("F5 cùng người: số lượng 7 còn (nháp giữ)", page.locator("input[placeholder='0.000']").first.input_value() == "7")
    ok("F5 cùng người: giá mua rỗng (không lưu)", page.locator("input[placeholder='80000']").first.input_value() == "")
    st = storages(page)
    ok("F5: storage không chứa 55555", "55555" not in st["local"] and "55555" not in st["session"])
    ok("AC4(a) F5 warehouse_staff: giữ đúng key", draft_key_of(page) == key_kho)
    page.screenshot(path=os.path.join(SHOTS, "sr07-3-f5-cung-nguoi.png"), full_page=True)

    # 5) Gửi thành công -> nháp xoá; nhập phiếu tiếp -> key mới
    page.locator("table select").first.select_option(index=1)
    page.locator("input[placeholder='0.000']").first.fill("5")
    page.get_by_role("button", name="Ghi nhận phiếu nhập").click()
    page.wait_for_selector("text=Ghi nhận phiếu nhập thành công", timeout=10_000)
    page.wait_for_timeout(300)
    ok("AC4(c) gửi thành công: nháp bị xoá", draft_key_of(page) is None)
    page.get_by_role("button", name="Nhập phiếu tiếp").click()
    page.wait_for_selector("input[placeholder='80000']", timeout=10_000)
    page.wait_for_timeout(300)
    ok("AC4(c) nhập phiếu tiếp: idempotencyKey mới", bool(draft_key_of(page)) and draft_key_of(page) != key_kho)
    page.screenshot(path=os.path.join(SHOTS, "sr07-4-sau-gui-thanh-cong-key-moi.png"), full_page=True)

    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
