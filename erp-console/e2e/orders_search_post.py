# E2E NEW-1 (Lô 17b): ô tìm ở danh sách đơn ERP gửi từ khoá (SĐT, tên, cả mã đơn) bằng POST /api/sales/orders/search/; SĐT và tên khách KHÔNG
# nằm trong URL của bất kỳ request nào, trong URL trang, localStorage hay sessionStorage. Chạy trên MOCK (đọc `__caveMock.log`) hoặc BE THẬT
# (nghe request của trình duyệt):
#   MOCK:  BASE=http://127.0.0.1:3101 SHOTS=<thư mục> python3 e2e/orders_search_post.py
#   THẬT:  BASE=http://127.0.0.1:3521 REAL_API=http://127.0.0.1:8621 SHOTS=<thư mục> python3 e2e/orders_search_post.py
import json
import os
import re
import sys
import urllib.request

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
REAL = os.environ.get("REAL_API", "")
PASSWORD = "Songbien2026" if REAL else "demo1234"
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=12_000)
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print("PASS" if cond else "FAIL", name, "" if cond else str(extra)[:300], flush=True)


def storage(page):
    # Bỏ kho mock của chính các module (dữ liệu khách GIẢ gieo sẵn, có thể trùng số đang thử); chỉ soi những gì app tự lưu.
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)].map((l) => l.filter(([k]) => !k.startsWith('cave_erp_mock_'))))")


def order_phone(page, oid):
    """SĐT của đơn `oid` để làm từ khoá thử: mock đọc từ `__caveMock.orderJson`, BE thật gọi API bằng token của Chủ."""
    if not REAL:
        return re.sub(r"\D", "", page.evaluate("(i) => window.__caveMock.orderJson('loc', i).customer.phone", oid) or "")
    token = page.evaluate("() => localStorage.getItem('cave_erp_token')")
    data = json.load(urllib.request.urlopen(urllib.request.Request(f"{REAL}/api/sales/orders/{oid}/", headers={"Authorization": "Token " + token})))
    return re.sub(r"\D", "", (data.get("customer") or {}).get("phone") or "")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
        reqs = []  # (method, url, post_data) của request /api/ tới orders (chỉ có ý nghĩa ở BE thật)
        page.on("request", lambda r: reqs.append((r.method, r.url, r.post_data or "")) if "/api/sales/orders" in r.url else None)
        page.goto(BASE + "/login/")
        page.wait_for_load_state("networkidle")
        page.get_by_label("Tài khoản").fill("loc")
        page.get_by_label("Mật khẩu").fill(PASSWORD)
        page.get_by_role("button", name="Đăng nhập").click()
        page.wait_for_selector(".nav a", state="attached")
        page.goto(BASE + "/orders/")
        page.wait_for_load_state("networkidle")
        rows = page.locator("main tbody tr")
        expect(rows.first).to_be_visible()
        total_rows = rows.count()

        # SĐT của một đơn bất kỳ (đọc từ chi tiết, chỉ dùng trong kịch bản), rồi tìm theo 6 số cuối
        rows.first.locator("a").first.click()
        page.wait_for_url(re.compile(r"/orders/detail/\?id=\d+"))
        page.wait_for_load_state("networkidle")
        oid = int(re.search(r"id=(\d+)", page.url).group(1))
        phone = order_phone(page, oid)
        page.goto(BASE + "/orders/")
        page.wait_for_load_state("networkidle")
        expect(rows.first).to_be_visible()
        ok("Đọc được SĐT của một đơn (chỉ để thử, không in ra)", len(phone) >= 9)
        term = phone[-6:] if phone else "zzzz"

        if not REAL:
            page.evaluate("() => window.__caveMock.clearLog()")
        box = page.get_by_role("searchbox", name="Tìm đơn hàng")
        box.fill(term)
        if REAL:
            page.wait_for_timeout(1200)
        else:
            page.wait_for_function("() => window.__caveMock.log.some(x => x.includes('POST /api/sales/orders/search/'))")
            page.wait_for_function("() => window.__caveMock.pending() === 0")
        page.wait_for_load_state("networkidle")

        if REAL:
            posts = [r for r in reqs if r[0] == "POST" and r[1].rstrip("/").endswith("/api/sales/orders/search")]
            ok("Tìm theo SĐT → POST /api/sales/orders/search/", len(posts) >= 1, reqs)
            ok("Thân POST mang từ khoá", any(term in r[2] for r in posts), [r[2] for r in posts])
            ok("Không request nào có SĐT/từ khoá trong URL", not any(term in r[1] for r in reqs), [r[1] for r in reqs])
            ok("Không có GET danh sách đơn mang q=", not any(r[0] == "GET" and "q=" in r[1] for r in reqs), [r[1] for r in reqs])
        else:
            lg = page.evaluate("() => window.__caveMock.log.slice()")
            ok("Tìm theo SĐT → POST /api/sales/orders/search/", any("POST /api/sales/orders/search/" in x for x in lg), lg)
            ok("Không dòng log request nào có SĐT/từ khoá", not any(term in x for x in lg), lg)
            ok("Không có GET danh sách đơn mang q=", not any(x.startswith("GET /api/sales/orders/") and "q=" in x for x in lg), lg)
        n = rows.count()
        ok("Kết quả tìm theo SĐT thu hẹp danh sách (ít nhất 1 dòng, không nhiều hơn tổng)", 1 <= n <= total_rows, f"{n}/{total_rows}")
        ok("URL trang không chứa từ khoá", term not in page.url and "q=" not in page.url, page.url)
        dump = storage(page)
        ok("localStorage/sessionStorage không chứa từ khoá đã gõ", term not in dump, dump[:200])
        page.screenshot(path=f"{SHOTS}/orders-search-post-1280.png")

        # Gõ mã đơn: vẫn POST (GET ?q= chỉ dành cho ⌘K), kết quả còn đúng đơn đó
        code = re.search(r"SO\d{6}-[A-Z0-9]{4,8}", page.locator("main tbody tr").first.inner_text())
        box.fill("")
        page.wait_for_timeout(600)
        if code:
            if not REAL:
                page.evaluate("() => window.__caveMock.clearLog()")
            else:
                reqs.clear()
            box.fill(code.group(0))
            page.wait_for_timeout(1200)
            if REAL:
                ok("Gõ mã đơn cũng đi POST search/", any(r[0] == "POST" and "orders/search" in r[1] for r in reqs) and not any(r[0] == "GET" and "q=" in r[1] for r in reqs), reqs)
            else:
                lg = page.evaluate("() => window.__caveMock.log.slice()")
                ok("Gõ mã đơn cũng đi POST search/", any("POST /api/sales/orders/search/" in x for x in lg) and not any(x.startswith("GET") and "q=" in x for x in lg), lg)
            ok("Gõ mã đơn: danh sách còn đúng đơn đó", page.locator("main tbody tr", has_text=code.group(0)).count() >= 1)

        # Tìm không thấy + sang trang không làm lộ từ khoá
        box.fill("zzqq-khong-co")
        page.wait_for_timeout(1200)
        expect(page.get_by_text(re.compile("Không tìm thấy .* khớp với"))).to_be_visible()
        ok("Tìm không thấy: câu rỗng nêu từ khoá, vẫn không có từ khoá trong URL", "zzqq" not in page.url)
        ok("Không lỗi console", not errors, errors[:3])
        ctx.close()
        b.close()
    bad = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(bad)}/{len(results)} PASS")
    sys.exit(1 if bad else 0)


main()
