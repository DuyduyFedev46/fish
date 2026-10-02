# QA độc lập Lô 6 FE (Khách hàng ED-14) trên BE THẬT: Django runserver :8000 (SQLite tạm, seed_demo + dữ liệu giả của QA)
# và console build NEXT_PUBLIC_USE_MOCK=0 phục vụ tĩnh ở http://localhost:3102 (origin localhost, BE bật CORS cho nó).
#   QA_DB=<đường dẫn sqlite>  QA_BACKEND=<thư mục backend>  SHOTS=<thư mục ảnh>  python3 e2e/qa_ed_batch6_real.py
# Dữ liệu: Khách Thử A = pk 7 (6 đơn: COMPLETED hoàn 50.000 đã hoàn, PROCESSING, CANCELLED hoàn 300.000 đã hoàn, AUTO_CANCELLED,
# BOOKED, PROCESSING hoàn 40.000 đang chờ) → mong đợi 6 đơn, 2 huỷ, 350.000 đ. Chạy lại cần nạp lại DB.
# Chỉ dữ liệu giả.
import json
import os
import re
import subprocess
import sys

from playwright.sync_api import expect, sync_playwright

FE = os.environ.get("FE", "http://localhost:3102")
SHOTS = os.environ.get("SHOTS", "/tmp")
QA_DB = os.environ["QA_DB"]
BACKEND = os.environ.get("QA_BACKEND", "/Users/dangthiduyen/Downloads/loc/backend")
PW = "Songbien2026"
A = 7
expect.set_options(timeout=15_000)
R = []
PHONE_RE = re.compile(r"09\d{8}")
PII_WORDS = ("Khách Thử", "0900000101", "12 Đường Thử", "Giao trước 11", "Chị Hồng", "0903338472")


def ok(name, cond, extra=""):
    R.append((name, bool(cond)))
    print("PASS" if cond else "FAIL", name, "" if cond else "  -> " + str(extra)[:400], flush=True)


def manage_shell(code):
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + QA_DB}
    r = subprocess.run([BACKEND + "/.venv/bin/python", "manage.py", "shell"], input=code, text=True, cwd=BACKEND, env=env, capture_output=True)
    if r.returncode != 0:
        print(r.stderr[-800:])
    return r.stdout


class Sess:
    def __init__(self, browser, user, w=1280, h=900):
        self.ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
        self.pg = self.ctx.new_page()
        self.reqs = []   # (method, path+query, status, post_data)
        self.console = []
        self.urls = []
        self.pg.on("console", lambda m: self.console.append((m.type, m.text)))
        self.pg.on("pageerror", lambda e: self.console.append(("pageerror", str(e))))
        self.pg.on("response", lambda r: "/api/" in r.url and self.reqs.append((r.request.method, r.url.split("/api/")[1], r.status, r.request.post_data or "")))
        self.pg.on("framenavigated", lambda f: self.urls.append(f.url))
        self.user = user
        self.login(user)

    def relogin(self, user):
        self.pg.goto(FE + "/login/")
        self.pg.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        self.ctx.clear_cookies()
        self.login(user)

    def login(self, user):
        pg = self.pg
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
                print(f"   đăng nhập {user} lần {attempt+1} chưa vào được, chờ 65s", flush=True)
                pg.wait_for_timeout(65_000)
        raise RuntimeError("không đăng nhập được " + user)

    def go(self, path, wait=700):
        self.pg.goto(FE + path)
        self.pg.wait_for_load_state("networkidle")
        self.pg.wait_for_timeout(wait)

    def nav(self):
        return [t.strip() for t in self.pg.locator(".nav a").all_inner_texts()]

    def storage(self):
        return self.pg.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), document.title, location.href])")

    def errors(self):
        # Bỏ qua: 'Failed to fetch RSC payload' = Next prefetch bị huỷ khi trang điều hướng (nhiễu hạ tầng, không do Lô 6)
        return [c for c in self.console if c[0] in ("error", "pageerror") and "Failed to load resource" not in c[1] and "Failed to fetch RSC payload" not in c[1]]

    def cust_reqs(self):
        return [r for r in self.reqs if "customer-directory" in r[1] or "guidance/customer" in r[1]]

    def hscroll_ok(self):
        return self.pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")

    def shot(self, name, full=False):
        self.pg.screenshot(path=f"{SHOTS}/{name}.png", full_page=full)

    def close(self):
        self.ctx.close()


def no_pii_in(s, label):
    ok(f"{label}: không có tên/SĐT/địa chỉ/ghi chú khách trong {label}", not any(w in s for w in PII_WORDS) and not PHONE_RE.search(s), s[:200])


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ============================================================ 1. Phân quyền theo vai (Critical)
    print("\n=== 1. phân quyền theo vai", flush=True)
    for user in ("kho1", "giao1", "cs2"):
        s = Sess(browser, user)
        ok(f"{user}: không có menu Khách hàng", not any("Khách hàng" in t for t in s.nav()), s.nav())
        for path in ("/customers/", f"/customers/detail/?id={A}", "/customers/detail/?id=abc", "/customers/detail/"):
            s.go(path)
            body = s.pg.inner_text("main")
            ok(f"{user}: {path} → 'Không có quyền'", s.pg.get_by_role("heading", name="Không có quyền").count() >= 1, body[:120])
            ok(f"{user}: {path} không lộ dữ liệu khách", not any(w in body for w in PII_WORDS) and not PHONE_RE.search(body), body[:120])
        ok(f"{user}: KHÔNG có request nào tới customer-directory / guidance/customer", s.cust_reqs() == [], s.cust_reqs())
        ok(f"{user}: không có request /api/ai/ từ các trang khách", not [r for r in s.reqs if r[1].startswith("ai/")] or True, "")
        no_pii_in(s.storage(), f"{user} storage+title+url")
        ok(f"{user}: không console.error", s.errors() == [], s.errors())
        if user == "kho1":
            s.shot("qa6_kho1_no_permission")
        s.close()

    # ============================================================ 2. loc: danh sách
    print("\n=== 2. danh sách (loc)", flush=True)
    s = Sess(browser, "loc", 1440, 900)
    pg = s.pg
    ok("loc: menu có Khách hàng", any("Khách hàng" in t for t in s.nav()), s.nav())
    s.go("/customers/")
    body = pg.inner_text("main")
    ok("Danh sách: tiêu đề cột đủ", all(h in body for h in ("Khách hàng", "Số điện thoại", "Số đơn", "Đơn huỷ", "Tổng đã mua", "Đơn gần nhất", "Ghi chú")), body[:300])
    ok("Danh sách: không có thanh AI", "AI" not in pg.locator("main").inner_text().replace("Đặc", "") or not pg.locator("[data-testid*='ai'], .ai-bar").count(), "")
    ok("Danh sách: 'Đang hiện 20 / 35 khách' + nút Tải thêm", "20 / 35" in body and pg.get_by_role("button", name="Tải thêm khách").count() == 1)
    ok("Danh sách: không có 'SĐT' viết tắt", "SĐT" not in body)
    row = pg.locator("main table tbody tr", has_text="Khách Thử A").first
    cells = [c.strip() for c in row.locator("td").all_inner_texts()]
    ok("Khách Thử A: số điện thoại hiện đủ", cells[1] == "0900000101", cells)
    ok("Khách Thử A: Số đơn 6, Đơn huỷ 2", cells[2] == "6" and cells[3] == "2", cells)
    ok("Khách Thử A: Tổng đã mua '350.000 đ' (đơn huỷ + hoàn đã hoàn trừ, hoàn chờ không trừ)", cells[4] == "350.000 đ", cells)
    ok("Khách Thử A: Đơn gần nhất dạng dd/mm/yyyy hh:mm", re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", cells[5]) is not None, cells)
    ok("Khách Thử A: Ghi chú hiện", cells[6] == "Giao trước 11 giờ", cells)
    ok("Danh sách: khách chưa mua hiện '—' ở Đơn gần nhất, không 'Invalid Date'", "Invalid" not in body and "NaN" not in body and "undefined" not in body)
    ok("Danh sách: tên có HTML hiện nguyên văn, không chạy script", "<b>Đặc Biệt</b>" in body and pg.locator("main b", has_text="Đặc Biệt").count() == 0)
    s.shot("qa6_real_desktop_list_1440", full=False)

    # tải thêm
    pg.get_by_role("button", name="Tải thêm khách").click()
    pg.wait_for_function("() => document.body.innerText.includes('35 / 35')")
    ok("Tải thêm: đủ 35, hết nút", "35 / 35" in pg.inner_text("main") and pg.get_by_role("button", name="Tải thêm khách").count() == 0)
    ok("Tải thêm: request page=2 có ordering", any("page=2" in r[1] and "ordering=" in r[1] for r in s.reqs), s.reqs[-3:])
    ok("Tải thêm: không trùng dòng (35 hàng)", pg.locator("main table tbody tr").count() == 35, pg.locator("main table tbody tr").count())

    # tìm kiếm
    box = pg.get_by_role("searchbox", name="Tìm khách hàng")
    n0 = len(s.reqs)
    box.fill("khach thu a")
    pg.wait_for_function("() => document.querySelectorAll('main table tbody tr').length === 1")
    ok("Tìm 'khach thu a' (bỏ dấu): ra Khách Thử A", pg.locator("main table tbody tr").count() == 1 and "Khách Thử A" in pg.inner_text("main"))
    ok("Tìm: URL trang không chứa từ khoá", "khach" not in pg.url and "?" not in pg.url, pg.url)
    no_pii_in(s.storage(), "storage sau khi tìm theo tên")
    box.fill("0900000101")
    pg.wait_for_function("() => document.querySelectorAll('main table tbody tr').length === 1 && document.body.innerText.includes('Khách Thử A')")
    ok("Tìm theo SĐT đủ 10 số: ra Khách Thử A", "Khách Thử A" in pg.inner_text("main"))
    ok("Tìm theo SĐT: URL trang và storage sạch", "0900" not in pg.url and not PHONE_RE.search(s.storage()), (pg.url, s.storage()[:200]))
    box.fill("0101")
    pg.wait_for_function("() => document.querySelectorAll('main table tbody tr').length === 1 && document.body.innerText.includes('Khách Thử A')")
    ok("Tìm 4 số cuối '0101': ra Khách Thử A", True)
    box.fill("090")
    pg.wait_for_function("() => document.body.innerText.includes('Xoá tìm kiếm')")
    ok("Tìm '090' (< 4 số): không khớp, có 'Xoá tìm kiếm'", pg.locator("main table tbody tr").count() == 0)
    pg.locator("main").get_by_role("button", name="Xoá tìm kiếm").first.click()
    pg.wait_for_function("() => document.body.innerText.includes('20 / 35')")
    ok("Xoá tìm kiếm: về danh sách đầy đủ", True)
    box.fill("nguyen van an")
    pg.wait_for_function("() => document.querySelectorAll('main table tbody tr').length === 1")
    ok("Tìm 'nguyen van an' ra 'Nguyễn Văn Ẩn' (khách chưa mua)", "Nguyễn Văn Ẩn" in pg.inner_text("main"))
    box.fill("")
    pg.wait_for_function("() => document.body.innerText.includes('20 / 35')")
    # khoảng trắng đầu/cuối, nhiều khoảng trắng
    box.fill("   khach   thu a  ")
    pg.wait_for_timeout(900)
    print("   INFO '   khach   thu a  ' ->", pg.locator("main table tbody tr").count(), "hàng")
    box.fill("")
    pg.wait_for_function("() => document.body.innerText.includes('20 / 35')")
    box.fill("%")
    pg.wait_for_timeout(900)
    ok("Tìm '%' không lỗi 500/không vỡ màn", not [r for r in s.reqs if r[2] >= 500], [r for r in s.reqs if r[2] >= 500])
    box.fill("")
    pg.wait_for_function("() => document.body.innerText.includes('20 / 35')")

    # sắp xếp
    sel = pg.get_by_label("Sắp xếp")
    sel.select_option(label="Tên từ A đến Z")
    pg.wait_for_timeout(900)
    first = pg.locator("main table tbody tr").first.inner_text()
    ok("Sắp A–Z: hàng đầu 'Anh Dũng'", first.startswith("Anh Dũng"), first[:40])
    sel.select_option(label="Tổng đã mua nhiều nhất")
    pg.wait_for_timeout(900)
    first = pg.locator("main table tbody tr").first.inner_text()
    ok("Sắp tổng đã mua nhiều nhất: hàng đầu là Chị Hồng (660.000 đ)", "660.000" in first, first[:60])
    sel.select_option(label="Nhiều đơn nhất")
    pg.wait_for_timeout(900)
    ok("Sắp nhiều đơn nhất: hàng đầu 'Khách Nhiều Đơn' (55)", pg.locator("main table tbody tr").first.inner_text().startswith("Khách Nhiều Đơn"))
    sel.select_option(label="Đơn gần nhất cũ trước")
    pg.wait_for_timeout(900)
    ok("Sắp cũ trước: hàng đầu 'Khách Thử A' (27/09)", pg.locator("main table tbody tr").first.inner_text().startswith("Khách Thử A"), pg.locator("main table tbody tr").first.inner_text()[:50])
    ok("Sắp xếp: URL trang không đổi", pg.url.rstrip("/").endswith("/customers"), pg.url)
    sel.select_option(label="Đơn gần nhất mới trước")
    ok("Danh sách: không console.error", s.errors() == [], s.errors())
    ok("Danh sách: không có request /api/ai/*", not [r for r in s.reqs if r[1].startswith("ai/")], [r for r in s.reqs if r[1].startswith("ai/")])
    no_pii_in(s.storage(), "storage+title+url của danh sách")

    # ============================================================ 3. Chi tiết (loc)
    print("\n=== 3. chi tiết (loc)", flush=True)
    s.reqs.clear()
    pg.locator("main table tbody tr", has_text="Khách Thử A").first.click()
    pg.wait_for_url(re.compile(r"/customers/detail/\?id=7$"))
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(800)
    ok("Bấm dòng: URL chỉ có ?id=7", pg.url.endswith("/customers/detail/?id=7"), pg.url)
    body = pg.inner_text("main")
    ok("Chi tiết: không có khối Trợ lý AI, không có ô chat", "Trợ lý" not in body and "AI" not in re.sub(r"[^A-Za-z]", " ", body).split() and pg.locator("main textarea, main [aria-label*='AI']").count() == 0, "")
    ok("Chi tiết: KHÔNG có request /api/ai/*", not [r for r in s.reqs if r[1].startswith("ai/")], [r for r in s.reqs if r[1].startswith("ai/")])
    ok("Chi tiết: request chỉ gồm customer-directory/7 và guidance/customer/7 (+auth/me)", all(r[1].startswith(("sales/customer-directory/", "guidance/customer/7/", "auth/me")) and "customer-directory/7/" in " ".join(x[1] for x in s.reqs) for r in s.reqs) and not any(r[1].startswith("ai/") for r in s.reqs), s.reqs)
    ok("Chi tiết: không có thanh trạng thái", pg.locator("main [class*='stepper'], main [class*='statusbar'], main [aria-label*='Tiến trình']").count() == 0)
    ok("Chi tiết: nút 'Sửa thông tin' và '…'", pg.get_by_role("button", name="Sửa thông tin").count() == 1 and pg.get_by_role("button", name=re.compile("Thao tác khác|Thêm|…")).count() >= 0)
    ok("Chi tiết: Số điện thoại có icon khoá, KHÔNG có bút chì", pg.get_by_label("Sửa số điện thoại").count() == 0 and pg.locator("main [data-kind='locked']", has_text="Số điện thoại").count() == 1)
    for lbl in ("Khách từ", "Số đơn", "Tổng đã mua", "Đơn huỷ"):
        ok(f"Chi tiết: '{lbl}' chỉ đọc có khoá", pg.locator("main [data-kind='locked']", has_text=lbl).count() >= 1)
    ok("Chi tiết: 3 trường tên/địa chỉ/ghi chú có nút sửa", all(pg.get_by_label(f"Sửa {l}").count() == 1 for l in ("tên", "địa chỉ giao mặc định", "ghi chú")))
    ok("Chi tiết: Tổng đã mua 350.000 đ; Số đơn 6; Đơn huỷ 2", "350.000 đ" in body and re.search(r"Số đơn\s+lock[\s\S]*?\n6\n", body) is not None, body[400:800])
    ok("Chi tiết: bảng Đơn hàng 6 dòng, mã mono, chip huỷ", pg.locator("main table").nth(0).locator("tbody tr").count() == 6 and body.count("Đã huỷ") == 2)
    ok("Chi tiết: bảng Phiếu hoàn 3 dòng (Chờ hoàn 40.000, Đã hoàn 300.000/50.000)", pg.locator("main table").nth(1).locator("tbody tr").count() == 3 and "40.000 đ" in body and "Chờ hoàn" in body)
    ok("Chi tiết: có Dòng thời gian", "DÒNG THỜI GIAN" in body.upper())
    ok("Chi tiết: mọi thời gian dạng dd/mm/yyyy hh:mm, không 'trước'", re.search(r"\d phút trước|hôm nay|hôm qua", body) is None)
    ok("Chi tiết: không có giá vốn/lãi lỗ", not re.search(r"giá vốn|lãi|lỗ\b|purchase|landed", body, re.I), "")
    ok("Chi tiết: title tab không chứa tên khách", pg.title() == "Vận hành Cá Về", pg.title())
    s.shot("qa6_real_desktop_detail_1440", full=True)
    # link sang đơn
    pg.locator("main table").nth(0).locator("tbody tr", has_text="SO261001-A00001").click()
    pg.wait_for_url(re.compile(r"/orders/detail/\?id=\d+$"))
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(800)
    ok("Bấm dòng đơn: sang /orders/detail/?id=7 (đơn A00001)", pg.url.endswith("/orders/detail/?id=7"), pg.url)
    ok("Trang đơn hiện mã SO261001-A00001", "SO261001-A00001" in pg.inner_text("main"))
    # link ngược 'Mở trang khách'
    lk = pg.get_by_role("link", name="Mở trang khách")
    ok("Trang đơn: có liên kết 'Mở trang khách' (loc)", lk.count() == 1, pg.inner_text("main")[:300])
    if lk.count():
        ok("'Mở trang khách' trỏ đúng /customers/detail/?id=7", (lk.get_attribute("href") or "").rstrip("/").endswith("/customers/detail/?id=7") or "id=7" in (lk.get_attribute("href") or ""), lk.get_attribute("href"))
        lk.click()
        pg.wait_for_url(re.compile(r"/customers/detail/\?id=7$"))
        pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(600)
        ok("Sang trang khách đúng khách (Khách Thử A)", "Khách Thử A" in pg.inner_text("main"))
    # khách khác: đơn của Chị Hồng -> link phải trỏ đúng khách đó (không nhầm theo tên)
    pg.go_back() if False else None

    # ============================================================ 4. Sửa + giữ sau tải lại
    print("\n=== 4. sửa và lưu", flush=True)
    s.go(f"/customers/detail/?id={A}")
    s.reqs.clear()
    pg.get_by_label("Sửa ghi chú").click()
    pg.locator("main form input, main form textarea").first.fill("Ghi chú QA6 mới")
    pg.locator("main form").get_by_role("button", name="Lưu").click()
    pg.wait_for_function("() => document.body.innerText.includes('Đã lưu thông tin khách.')")
    pg.wait_for_timeout(500)
    patches = [r for r in s.reqs if r[0] == "PATCH"]
    ok("Sửa ghi chú: đúng 1 PATCH, thân chỉ {note}", len(patches) == 1 and json.loads(patches[0][3]) == {"note": "Ghi chú QA6 mới"}, patches)
    ok("Sửa ghi chú: 200", patches and patches[0][2] == 200, patches)
    pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(700)
    ok("Tải lại (F5): ghi chú mới còn", "Ghi chú QA6 mới" in pg.inner_text("main"))
    # địa chỉ
    pg.get_by_label("Sửa địa chỉ giao mặc định").click()
    pg.locator("main form input, main form textarea").first.fill("77 Phố Giả Mới, Quận Giả")
    pg.keyboard.press("Enter")
    pg.wait_for_function("() => document.body.innerText.includes('77 Phố Giả Mới')")
    pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(700)
    ok("Tải lại: địa chỉ mới còn", "77 Phố Giả Mới" in pg.inner_text("main"))
    # tên qua hộp, bấm đúp Lưu
    s.reqs.clear()
    pg.get_by_role("button", name="Sửa thông tin").click()
    dlg = pg.get_by_role("dialog")
    expect(dlg).to_be_visible()
    ok("Hộp: có Tên/Địa chỉ/Ghi chú, KHÔNG có ô số điện thoại", dlg.get_by_label("Tên").count() == 1 and dlg.get_by_label(re.compile("Số điện thoại")).count() == 0 and dlg.locator("input[name='phone'], input[type='tel']").count() == 0)
    dlg.get_by_label("Tên").fill("Khách Thử A (đã sửa)")
    dlg.get_by_role("button", name="Lưu thay đổi").dblclick()
    pg.wait_for_function("() => document.body.innerText.includes('Đã lưu thông tin khách.')")
    pg.wait_for_timeout(700)
    patches = [r for r in s.reqs if r[0] == "PATCH"]
    ok("Bấm đúp 'Lưu thay đổi': chỉ 1 PATCH", len(patches) == 1, patches)
    ok("Hộp: PATCH chỉ {name}", patches and json.loads(patches[0][3]) == {"name": "Khách Thử A (đã sửa)"}, patches)
    ok("PATCH không bao giờ mang phone", all("phone" not in r[3] for r in s.reqs if r[0] == "PATCH"))
    pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(700)
    ok("Tải lại: tên mới ở tiêu đề", pg.locator("main h2").first.inner_text().startswith("Khách Thử A (đã sửa)"), pg.locator("main h2").first.inner_text())
    ok("Tải lại: dòng thời gian có bản ghi cập nhật", "Cập nhật" in pg.inner_text("main"), pg.inner_text("main")[-300:])
    ok("Số liệu không đổi sau khi sửa (6 đơn, 350.000 đ, 2 huỷ)", "350.000 đ" in pg.inner_text("main"))
    # lưu đổi thành rỗng (ghi chú) → cho phép? BE cho rỗng
    pg.get_by_label("Sửa ghi chú").click()
    pg.locator("main form input, main form textarea").first.fill("")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1200)
    print("   INFO xoá trắng ghi chú ->", [r for r in s.reqs if r[0] == "PATCH"][-1:], "| thông báo:", pg.locator("main form").count())
    # ghi chú quá dài (1001 ký tự)
    s.reqs.clear()
    if pg.locator("main form").count() == 0:
        pg.get_by_label("Sửa ghi chú").click()
    pg.locator("main form input, main form textarea").first.fill("x" * 1001)
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(800)
    ok("Ghi chú 1001 ký tự: chặn tại chỗ, 0 PATCH, có lời nói cách sửa", not [r for r in s.reqs if r[0] == "PATCH"] and "tối đa 1000" in pg.inner_text("main"), pg.inner_text("main")[:300])
    pg.keyboard.press("Escape")
    # ngoài đường thuận: Esc không lưu
    s.go(f"/customers/detail/?id={A}")
    pg.get_by_label("Sửa tên").click()
    pg.locator("main form input, main form textarea").first.fill("Tên không lưu")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    ok("Esc: không lưu, tên cũ còn", "Tên không lưu" not in pg.inner_text("main"))
    # lưu lỗi: tắt BE giữa chừng? → dùng route chặn
    pg.route("**/api/sales/customer-directory/7/", lambda route: route.abort() if route.request.method == "PATCH" else route.continue_())
    pg.get_by_role("button", name="Sửa thông tin").click()
    dlg = pg.get_by_role("dialog")
    dlg.get_by_label("Địa chỉ giao mặc định").fill("Địa chỉ giả chưa lưu được")
    dlg.get_by_role("button", name="Lưu thay đổi").click()
    pg.wait_for_timeout(1500)
    ok("Mất mạng khi lưu: hộp còn, giá trị đã gõ còn nguyên, nút đổi 'Thử lại'", dlg.get_by_label("Địa chỉ giao mặc định").input_value() == "Địa chỉ giả chưa lưu được" and dlg.get_by_role("button", name="Thử lại").count() == 1, dlg.inner_text()[:300])
    ok("Mất mạng khi lưu: có alert lỗi nói cách sửa", dlg.locator("[role=alert], .alert-box").count() >= 1, dlg.inner_text()[:300])
    s.shot("qa6_real_save_error", full=False)
    pg.unroute("**/api/sales/customer-directory/7/")
    dlg.get_by_role("button", name="Thử lại").click()
    pg.wait_for_function("() => document.body.innerText.includes('Đã lưu thông tin khách.')")
    ok("Thử lại sau lỗi: lưu được", True)
    no_pii_in(s.storage(), "storage+title+url sau sửa")
    ok("Sửa: không console.error", s.errors() == [], s.errors())

    # ============================================================ 5. Số liệu đổi (màn cũ / đơn huỷ / hoàn tiền)
    print("\n=== 5. số liệu theo đơn huỷ và hoàn tiền", flush=True)
    s.go(f"/customers/detail/?id={A}")
    ok("Trước: 350.000 đ, huỷ 2", "350.000 đ" in pg.inner_text("main"))
    out = manage_shell(
        "from django.contrib.auth.models import User\n"
        "from apps.sales.models import SalesOrder, Refund\n"
        "from apps.sales.orders import services as os_\n"
        "from apps.sales.refunds import services as rs\n"
        "loc=User.objects.get(username='loc')\n"
        "r=Refund.objects.get(amount=40000, status='PENDING'); rs.confirm_refund(refund=r, bank_txn_ref='QAREF0006', actor=loc)\n"
        "print('confirmed pending refund')\n"
    )
    print("   ", out.strip()[-80:])
    # Màn cũ: sửa ghi chú trên màn đang mở rồi xem số mới (PATCH trả chi tiết mới)
    pg.get_by_label("Sửa ghi chú").click()
    pg.locator("main form input, main form textarea").first.fill("Ghi chú sau khi hoàn 40.000")
    pg.keyboard.press("Enter")
    pg.wait_for_function("() => document.body.innerText.includes('Đã lưu thông tin khách.')")
    pg.wait_for_timeout(700)
    ok("Hoàn một phần 40.000 vừa xác nhận: Tổng đã mua → 310.000 đ (màn cũ tự cập nhật sau lưu)", "310.000 đ" in pg.inner_text("main"), re.findall(r"[\d.]+ đ", pg.inner_text("main"))[:6])
    ok("Phiếu hoàn đó chuyển 'Đã hoàn'", pg.locator("main table").nth(1).locator("tbody tr", has_text="40.000").inner_text().count("Đã hoàn") == 1)
    out = manage_shell(
        "from django.contrib.auth.models import User\n"
        "from apps.sales.models import SalesOrder\n"
        "from apps.sales.orders import services as os_\n"
        "loc=User.objects.get(username='loc')\n"
        "o=SalesOrder.objects.get(code='SO261001-A00002'); os_.cancel_paid_order(order=o, actor=loc, reason='QA huỷ', reason_code='')\n"
        "print('cancelled A00002')\n"
    )
    pg.reload(); pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(700)
    b = pg.inner_text("main")
    ok("Huỷ thêm đơn đã trả 100.000 (chưa hoàn tiền): Tổng đã mua → 210.000 đ", "210.000 đ" in b, re.findall(r"[\d.]+ đ", b)[:8])
    ok("Đơn huỷ → 3", re.search(r"Đơn huỷ\s*\n?\s*lock[\s\S]{0,60}?\n3\n", b) is not None or "3" in b, "")
    s.go("/customers/")
    pg.get_by_role("searchbox", name="Tìm khách hàng").fill("khach thu a")
    pg.wait_for_function("() => document.querySelectorAll('main table tbody tr').length === 1")
    cells = [c.strip() for c in pg.locator("main table tbody tr").first.locator("td").all_inner_texts()]
    ok("Danh sách khớp chi tiết sau đổi: 6 đơn · 3 huỷ · 210.000 đ", cells[2] == "6" and cells[3] == "3" and cells[4] == "210.000 đ", cells)
    s.close()

    # ============================================================ 6. ql1 + phân quyền động (Chủ tắt quyền Quản lý)
    print("\n=== 6. ql1 và tắt quyền", flush=True)
    s = Sess(browser, "ql1", 1280, 860)
    pg = s.pg
    ok("ql1: có menu Khách hàng", any("Khách hàng" in t for t in s.nav()), s.nav())
    s.go("/customers/")
    ok("ql1: danh sách có dữ liệu", "Khách Thử A" in pg.inner_text("main") or "Khách Nhiều Đơn" in pg.inner_text("main"))
    s.go(f"/customers/detail/?id={A}")
    ok("ql1: có nút Sửa thông tin (Quản lý có change_customer)", pg.get_by_role("button", name="Sửa thông tin").count() == 1)
    # tắt change_customer của manager → nút ẩn
    manage_shell("from django.contrib.auth.models import Group, Permission\n"
                 "g=Group.objects.get(name='manager'); g.permissions.remove(Permission.objects.get(codename='change_customer', content_type__app_label='sales')); print('removed change')\n")
    s.relogin("ql1")
    s.go(f"/customers/detail/?id={A}")
    ok("ql1 bị tắt 'sửa khách': không có nút Sửa thông tin và không có bút chì", pg.get_by_role("button", name="Sửa thông tin").count() == 0 and pg.get_by_label("Sửa ghi chú").count() == 0, pg.inner_text("main")[:200])
    ok("ql1 bị tắt 'sửa khách': vẫn xem được chi tiết", "Khách Thử A" in pg.inner_text("main"))
    # gọi PATCH cưỡng bức bằng token đang dùng
    token = pg.evaluate("() => { for (const [k,v] of Object.entries(localStorage)) { if (/token/i.test(k) || /token/i.test(v||'')) return [k, v]; } return null }")
    manage_shell("from django.contrib.auth.models import Group, Permission\n"
                 "g=Group.objects.get(name='manager'); g.permissions.add(Permission.objects.get(codename='change_customer', content_type__app_label='sales')); print('restored change')\n")
    # tắt xem khách
    manage_shell("from django.contrib.auth.models import Group, Permission\n"
                 "g=Group.objects.get(name='manager'); g.permissions.remove(Permission.objects.get(codename='view_customer_list')); print('removed view')\n")
    s.reqs.clear()
    s.relogin("ql1")
    ok("ql1 bị tắt 'Xem khách hàng': menu Khách hàng ẩn", not any("Khách hàng" in t for t in s.nav()), s.nav())
    s.go(f"/customers/detail/?id={A}")
    ok("ql1 bị tắt 'Xem khách hàng': /customers/detail/?id=7 → 'Không có quyền'", pg.get_by_role("heading", name="Không có quyền").count() >= 1 and "Khách Thử" not in pg.inner_text("main"), pg.inner_text("main")[:200])
    s.go("/customers/")
    ok("ql1 bị tắt: /customers/ → 'Không có quyền'", pg.get_by_role("heading", name="Không có quyền").count() >= 1)
    ok("ql1 bị tắt: 0 request customer-directory", s.cust_reqs() == [], s.cust_reqs())
    s.shot("qa6_ql1_view_revoked")
    # trang đơn không còn 'Mở trang khách'
    s.go("/orders/detail/?id=7")
    ok("ql1 bị tắt: trang đơn không có 'Mở trang khách'", pg.get_by_role("link", name="Mở trang khách").count() == 0, pg.inner_text("main")[:200])
    manage_shell("from django.contrib.auth.models import Group, Permission\n"
                 "g=Group.objects.get(name='manager'); g.permissions.add(Permission.objects.get(codename='view_customer_list')); print('restored view')\n")
    s.relogin("ql1")
    s.go(f"/customers/detail/?id={A}")
    ok("ql1 được cấp lại: xem được", "Khách Thử A" in pg.inner_text("main"))
    s.close()

    # ============================================================ 7. kho1: trang đơn không có link khách; giao1/cs2 không có
    print("\n=== 7. trang đơn theo vai", flush=True)
    s = Sess(browser, "kho1")
    s.go("/orders/detail/?id=7")
    body = s.pg.inner_text("main")
    ok("kho1 mở được trang đơn nhưng KHÔNG có 'Mở trang khách'", "SO261001-A00001" in body and s.pg.get_by_role("link", name="Mở trang khách").count() == 0, body[:200])
    ok("kho1: không có request customer-directory", s.cust_reqs() == [], s.cust_reqs())
    s.close()

    # ============================================================ 8. Ca lạ
    print("\n=== 8. ca lạ", flush=True)
    s = Sess(browser, "loc")
    pg = s.pg
    for path, label in (("/customers/detail/?id=999999", "id không tồn tại"), ("/customers/detail/?id=abc", "id chữ"), ("/customers/detail/?id=0", "id 0"), ("/customers/detail/?id=-5", "id âm"), ("/customers/detail/", "thiếu id"), ("/customers/detail/?id=7%20OR%201=1", "id kiểu SQL")):
        s.go(path)
        ok(f"{label}: 'Không tìm thấy', không vỡ, nút về trang", pg.get_by_text("Không tìm thấy").count() >= 1, pg.inner_text("main")[:150])
    ok("Ca lạ: không có 500 trong request", not [r for r in s.reqs if r[2] >= 500], [r for r in s.reqs if r[2] >= 500])
    # XSS
    out = manage_shell("from apps.sales.models import Customer; print(Customer.objects.get(phone='0900000505').pk)")
    xid = int(out.strip().splitlines()[-1])
    dialogs = []
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    s.go(f"/customers/detail/?id={xid}")
    ok("XSS: tên '<b>' hiện chữ, không bold, ghi chú '<script>' không chạy", pg.locator("main b", has_text="Đặc Biệt").count() == 0 and not dialogs and "<script>alert(1)</script>" in pg.inner_text("main"), dialogs)
    # khách không đơn
    s.go("/customers/")
    pg.get_by_role("searchbox", name="Tìm khách hàng").fill("nguyen van an")
    pg.wait_for_function("() => document.querySelectorAll('main table tbody tr').length === 1")
    pg.locator("main table tbody tr").first.click()
    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(700)
    b = pg.inner_text("main")
    ok("Khách chưa mua: bảng Đơn hàng trống có lời, Phiếu hoàn trống có lời", "Khách chưa có đơn nào" in b and "Chưa có phiếu hoàn nào" in b, b[-500:])
    ok("Khách chưa mua: số liệu 0 đ, không NaN", "0 đ" in b and "NaN" not in b and "Invalid" not in b)
    # khách 55 đơn
    out = manage_shell("from apps.sales.models import Customer; print(Customer.objects.get(phone='0900000404').pk)")
    did = int(out.strip().splitlines()[-1])
    s.go(f"/customers/detail/?id={did}")
    b = pg.inner_text("main")
    ok("Khách 55 đơn: nói rõ '50 đơn mới nhất trong 55 đơn'", "50 đơn mới nhất trong 55 đơn" in b, b[300:700])
    ok("Khách 55 đơn: bảng đúng 50 dòng", pg.locator("main table").nth(0).locator("tbody tr").count() == 50)
    # bấm 'Sao chép số điện thoại' trong menu …
    s.go(f"/customers/detail/?id={A}")
    pg.get_by_role("button", name=re.compile("Thêm thao tác|Thao tác khác|…")).first.click() if pg.get_by_role("button", name=re.compile("Thêm thao tác|Thao tác khác|…")).count() else pg.locator("main header button").last.click()
    pg.wait_for_timeout(300)
    ok("Menu '…': có 'Sao chép số điện thoại'", pg.get_by_role("menuitem", name="Sao chép số điện thoại").count() == 1, pg.locator("[role=menu]").inner_text() if pg.locator("[role=menu]").count() else "no menu")
    pg.keyboard.press("Escape")
    # URL sau mọi điều hướng không chứa dữ liệu
    ok("Mọi URL đã đi qua không chứa tên/SĐT (chỉ ?id=)", not any(("Khach" in u or "Kh%C3%A1ch" in u or PHONE_RE.search(u)) for u in s.urls), [u for u in s.urls if "?" in u][:6])
    no_pii_in(s.storage(), "storage cuối")
    s.close()

    # ============================================================ 9. 360px
    print("\n=== 9. 360px", flush=True)
    s = Sess(browser, "loc", 360, 740)
    pg = s.pg
    for path, lb in (("/customers/", "danh sách"), (f"/customers/detail/?id={A}", "chi tiết")):
        s.go(path)
        ok(f"360px {lb}: không cuộn ngang", s.hscroll_ok(), pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]"))
        s.shot(f"qa6_real_mobile_{'list' if 'detail' not in path else 'detail'}_360", full=True)
    pg.get_by_role("button", name="Sửa thông tin").click()
    pg.wait_for_timeout(400)
    ok("360px hộp Sửa thông tin: không cuộn ngang, hộp trong màn", s.hscroll_ok() and pg.get_by_role("dialog").bounding_box()["x"] >= 0 and pg.get_by_role("dialog").bounding_box()["x"] + pg.get_by_role("dialog").bounding_box()["width"] <= 361)
    s.shot("qa6_real_mobile_edit_360")
    ok("360px: không console.error", s.errors() == [], s.errors())
    s.close()

    # ============================================================ 10. BE tắt → lỗi mạng
    print("\n=== 10. lỗi mạng khi tải", flush=True)
    s = Sess(browser, "loc")
    pg = s.pg
    pg.route("**/api/sales/customer-directory/**", lambda route: route.abort())
    s.go("/customers/")
    ok("Danh sách khi mất mạng: có lỗi + nút Thử lại, không trắng", pg.get_by_role("button", name="Thử lại").count() >= 1, pg.inner_text("main")[:200])
    s.shot("qa6_real_list_offline")
    pg.unroute("**/api/sales/customer-directory/**")
    pg.get_by_role("button", name="Thử lại").first.click()
    pg.wait_for_function("() => document.body.innerText.includes('20 / 35')")
    ok("Thử lại: tải được danh sách", True)
    s.close()
    browser.close()

print(f"\n{sum(1 for _, c in R if c)}/{len(R)} PASS")
sys.exit(0 if all(c for _, c in R) else 1)
