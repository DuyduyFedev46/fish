# Smoke ERP Khách hàng (ED-13/ED-14, Lô 6) trên BE THẬT với dữ liệu giả của `manage.py seed_qa` (20 khách "Khách QA Giả nn", SĐT 09000000nn).
#   Chuẩn bị và biến môi trường: xem e2e_seed_qa.py (BASE = ERP build thật, API, SEED_QA_IDS, QA_PASSWORD).
# Thay cho hai kịch bản QA một lần `qa_ed_batch6_real` / `qa_ed_batch6_api` (cứng "Khách Thử A", 35 khách, số liệu của phiên QA cũ): giữ phần
# tích hợp UI <-> BE thật (danh sách, tìm bằng POST, chi tiết, quyền, không rò dữ liệu cá nhân); số liệu và serializer do test BE phủ
# (backend/apps/sales/customers/tests/test_directory_*.py). Chỉ đọc và sửa ghi chú của khách giả; seed lại trước mỗi lần chạy.
import re

from playwright.sync_api import expect, sync_playwright

from e2e_seed_qa import BASE, ids, password
from e2e_support import finish

R = []
PHONE_RE = re.compile(r"(?<!\d)0\d{9}(?!\d)")
expect.set_options(timeout=15_000)


def ok(n, c, e=""):
    R.append((n, bool(c), e))
    print("PASS" if c else "FAIL", n, "" if c else str(e)[:300], flush=True)


def session(browser, user):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    errs, reqs, urls = [], [], []
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errs.append(m.text))
    page.on("framenavigated", lambda f: urls.append(f.url))
    page.on("request", lambda r: reqs.append((r.method, r.url)) if "/api/" in r.url else None)
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(password())
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    return ctx, page, errs, reqs, urls


def nav(page):
    return [t.strip() for t in page.locator(".nav a").all_inner_texts()]


M = ids()
FIRST_PHONE = "0900000001"
CUSTOMER_ID = M["customers"][FIRST_PHONE]

with sync_playwright() as p:
    b = p.chromium.launch()
    # Vai không có quyền: không menu, vào thẳng URL thì "Không có quyền", không lộ dữ liệu khách, không gọi customer-directory
    for user in ("qa_warehouse", "qa_courier1", "qa_cs1"):
        ctx, page, errs, reqs, _ = session(b, user)
        ok(f"{user}: menu không có Khách hàng", not any("Khách hàng" in t for t in nav(page)), nav(page))
        page.goto(BASE + "/customers/")
        page.wait_for_load_state("networkidle")
        ok(f"{user}: /customers/ hiện 'Không có quyền', không bảng khách", page.get_by_role("heading", name="Không có quyền").count() >= 1 and page.locator("main table").count() == 0)
        page.goto(f"{BASE}/customers/detail/?id={CUSTOMER_ID}")
        page.wait_for_load_state("networkidle")
        ok(f"{user}: chi tiết khách 'Không có quyền', không lộ SĐT", page.get_by_role("heading", name="Không có quyền").count() >= 1 and not PHONE_RE.search(page.inner_text("main")))
        ok(f"{user}: không có request tới customer-directory", not [r for r in reqs if "customer-directory" in r[1]], reqs[-3:])
        ctx.close()

    ctx, page, errs, reqs, urls = session(b, "qa_owner")
    ok("qa_owner: menu có Khách hàng", any("Khách hàng" in t for t in nav(page)), nav(page))
    page.locator(".nav a", has_text="Khách hàng").first.click()
    page.wait_for_url(re.compile(r"/customers/?$"))
    page.wait_for_function("() => document.body.innerText.includes('20 / 20')")  # "Đang hiện 20 / 20 khách": danh sách tải xong
    body = page.inner_text("main")
    ok("Danh sách: có cột Khách hàng, Số điện thoại, Số đơn, Đơn huỷ, Tổng đã mua, Đơn gần nhất", all(h in body for h in ("Khách hàng", "Số điện thoại", "Số đơn", "Đơn huỷ", "Tổng đã mua", "Đơn gần nhất")), body[:200])
    rows_n = page.locator("main table tbody tr").count()
    ok("Danh sách: đủ 20 khách của seed_qa, không còn nút Tải thêm", rows_n == 20 and page.get_by_role("button", name="Tải thêm khách").count() == 0, (rows_n, re.findall(r"\d+ / \d+", body)))
    ok("Danh sách: tên giả 'Khách QA Giả', không chữ 'SĐT' viết tắt", "Khách QA Giả" in body and "SĐT" not in body, body[-200:])
    ok("Danh sách: không 'Invalid Date', 'NaN', 'undefined'", not any(x in body for x in ("Invalid", "NaN", "undefined")))
    # Tìm kiếm: tên bỏ dấu (không có SĐT trong URL), SĐT đủ 10 số, < 4 chữ số không dò theo SĐT
    box = page.get_by_role("searchbox", name="Tìm khách hàng")
    box.fill("khach qa gia 01")
    page.wait_for_function("() => document.querySelectorAll('main table tbody tr').length === 1")
    ok("Tìm 'khach qa gia 01' (bỏ dấu): ra đúng 1 khách", "Khách QA Giả 01" in page.inner_text("main"))
    box.fill(FIRST_PHONE)
    page.wait_for_function("() => document.querySelectorAll('main table tbody tr').length === 1")
    ok("Tìm theo SĐT đủ 10 số: ra đúng khách đó", FIRST_PHONE in page.inner_text("main"))
    ok("Tìm kiếm: từ khoá và SĐT không vào URL / storage", "khach" not in page.url and FIRST_PHONE not in page.url and FIRST_PHONE not in page.evaluate("() => JSON.stringify([localStorage, sessionStorage])"), page.url)
    ok("Tìm kiếm đi bằng POST (SĐT không nằm trong URL request nào)", not [r for r in reqs if FIRST_PHONE in r[1]], [r for r in reqs if FIRST_PHONE in r[1]])
    box.fill("090")
    page.wait_for_function("() => document.body.innerText.includes('Xoá tìm kiếm')")
    ok("Tìm '090' (dưới 4 chữ số): không dò theo số điện thoại", page.locator("main table tbody tr").count() == 0)
    box.fill("")
    expect(page.locator("main table tbody tr").first).to_be_visible()
    # Chi tiết
    page.goto(f"{BASE}/customers/detail/?id={CUSTOMER_ID}")
    expect(page.locator("main h2").first).to_be_visible()
    page.wait_for_load_state("networkidle")
    d = page.inner_text("main")
    ok("Chi tiết: URL chỉ có ?id=", re.fullmatch(r".*/customers/detail/\?id=\d+", page.url) is not None, page.url)
    ok("Chi tiết: hiện tên và SĐT giả đủ cho Chủ, có Dòng thời gian", "Khách QA Giả 01" in d and FIRST_PHONE in d and "DÒNG THỜI GIAN" in d.upper(), d[:200])
    ok("Chi tiết: không giá vốn / lãi lỗ", not re.search(r"giá vốn|lãi|lỗ\b|purchase|landed", d, re.I))
    ok("Chi tiết: không có thời gian tương đối", re.search(r"\d phút trước|hôm nay|hôm qua", d) is None)
    ok("Chi tiết: tiêu đề tab không chứa tên khách", page.title() == "Vận hành Cá Về", page.title())
    ok("Chi tiết: PATCH nào cũng không mang phone", all("phone" not in (r[1] or "") for r in reqs if r[0] == "PATCH"))
    ok("Không có request /api/ai/* từ các trang khách", not [r for r in reqs if "/api/ai/" in r[1]])
    ok("Không console.error", not errs, errs[:3])
    ctx.close()

    ctx, page, errs, reqs, _ = session(b, "qa_manager")
    ok("qa_manager: menu có Khách hàng", any("Khách hàng" in t for t in nav(page)), nav(page))
    page.goto(BASE + "/customers/")
    expect(page.locator("main table tbody tr").first).to_be_visible()
    ok("qa_manager: xem được danh sách khách", page.locator("main table tbody tr").count() >= 1)
    b.close()
finish(R)
