# Smoke trên BE THẬT (Lô 3 Đơn & tiền) dùng dữ liệu giả cố định của `manage.py seed_qa` (không cứng mã/id của phiên QA cũ).
#   Chuẩn bị và biến môi trường: xem e2e_seed_qa.py (BASE = ERP build NEXT_PUBLIC_USE_MOCK=0, API, SEED_QA_IDS, QA_PASSWORD).
# Viết lại 08/10 (lô dọn e2e): tên chuẩn (Đang soạn hàng, Hết giờ giữ chỗ, Phiếu hoàn tiền, Chờ hoàn tiền), người dùng qa_owner/qa_manager.
# Mỗi lần chạy ghi vào DB: seed lại DB trước khi chạy (đơn BOOKED hết giữ chỗ sau vài phút).
import re
import sys
import uuid

from playwright.sync_api import expect, sync_playwright

from e2e_seed_qa import BASE, ids, order_id, password
from e2e_support import finish

R = []
expect.set_options(timeout=15000)


def ok(n, c, e=""):
    R.append((n, bool(c), e))
    print("PASS" if c else "FAIL", n, "" if c else e, flush=True)


def login(page, user):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(password())
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")


M = ids()
BOOKED = [c for c, v in M["orders"].items() if v["status"] == "BOOKED"]
TARGET = "QA-SO-13"  # đơn Giữ chỗ còn hạn, dành cho ca xác nhận tiền -> huỷ -> hoàn tiền

with sync_playwright() as p:
    b = p.chromium.launch()
    errs, reqs = [], []
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and errs.append(m.text))
    page.on("response", lambda r: "/api/" in r.url and reqs.append((r.request.method, r.url.split("/api/")[1], r.status)))
    login(page, "qa_owner")
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    expect(page.locator("tbody tr.lt-click").first).to_be_visible()
    n = page.locator("tbody tr.lt-click").count()
    ok("BE thật: danh sách đơn có dữ liệu seed_qa (trang đầu có dòng)", n >= 10, str(n))
    heads = [h.strip() for h in page.locator("thead th").all_inner_texts()]
    for col in ("Mã đơn", "Khách hàng", "Trạng thái", "Giao hàng", "Lý do", "Tổng tiền", "Thời gian"):
        ok(f"BE thật: có cột '{col}'", any(h.startswith(col) for h in heads), str(heads))
    body = page.locator("tbody").inner_text()
    # Cột Trạng thái (đơn): Giữ chỗ / Đang xử lý / Đã huỷ; cột Giao hàng (phiếu giao): Đang soạn hàng; cột Lý do: Hết giờ giữ chỗ.
    ok("BE thật: có chip đơn Giữ chỗ / Đang xử lý / Đã huỷ, phiếu giao 'Đang soạn hàng', lý do 'Hết giờ giữ chỗ' (tên chuẩn)",
       all(x in body for x in ["Giữ chỗ", "Đang xử lý", "Đã huỷ", "Đang soạn hàng", "Hết giờ giữ chỗ"]), body[:300])
    page.screenshot(path="/tmp/shots3-real3-list.png")

    # chi tiết đơn Giữ chỗ còn hạn
    page.goto(f"{BASE}/orders/detail/?id={order_id(TARGET)}")
    expect(page.locator("main header h2")).to_be_visible()
    page.wait_for_load_state("networkidle")
    hb = [t.strip() for t in page.locator("main header .btn").all_inner_texts() if t.strip()]
    ok("BE thật: đơn Giữ chỗ -> nút chính 'Xác nhận đã nhận tiền'", hb[:1] == ["Xác nhận đã nhận tiền"], str(hb))
    txt = page.locator("main").inner_text()
    ok("BE thật: chi tiết có SĐT đủ, 'Còn giữ chỗ' mm:ss, StatusPath", re.search(r"0\d{9}", txt) and re.search(r"\d{2}:\d{2}", txt) and "Giữ chỗ" in txt, txt[:200])
    page.screenshot(path="/tmp/shots3-real3-detail.png")
    page.get_by_role("button", name="Xác nhận đã nhận tiền").click()
    d = page.get_by_role("dialog", name="Xác nhận đã nhận tiền")
    expect(d).to_be_visible()
    d.get_by_label("Mã giao dịch ngân hàng").fill("FT-R3-" + uuid.uuid4().hex[:8])
    d.locator("button[type=submit]").click()
    expect(page.locator(".toast-item").last).to_be_visible()
    page.wait_for_load_state("networkidle")
    ok("BE thật: xác nhận đã nhận tiền -> toast + chip đổi, hết nút",
       "Giữ chỗ" not in page.locator("main header").inner_text() and page.get_by_role("button", name="Xác nhận đã nhận tiền").count() == 0,
       page.locator("main header").inner_text())
    ok("BE thật: POST confirm-payment trả 200/201", any(m == "POST" and "confirm-payment" in u and s in (200, 201) for m, u, s in reqs), str([x for x in reqs if x[0] == "POST"]))
    ok("BE thật: 'Huỷ đơn' xuất hiện sau khi đã thanh toán", page.get_by_role("button", name="Huỷ đơn").count() >= 1, str(page.locator("main header .btn").all_inner_texts()))
    page.get_by_role("button", name="Huỷ đơn").first.click()
    d = page.get_by_role("dialog", name="Huỷ đơn")
    d.get_by_label("Lý do huỷ").select_option(value="CUSTOMER_CHANGED_MIND")  # "Khách đổi ý"
    d.locator("button[type=submit]").click()
    d2 = page.get_by_role("dialog", name="Huỷ đơn này?")
    d2.locator("button[type=submit]").click()
    expect(page.locator("main header")).to_contain_text("Đã huỷ")
    page.wait_for_load_state("networkidle")
    ok("BE thật: huỷ đơn -> Đã huỷ", True)
    page.get_by_role("button", name=re.compile("Lập phiếu hoàn tiền")).first.click()
    d = page.get_by_role("dialog", name=re.compile("Lập phiếu hoàn tiền"))
    expect(d).to_be_visible()
    d.locator("button[type=submit]").click()
    expect(page.locator(".toast-item").last).to_contain_text("Đã lập phiếu hoàn tiền")
    ok("BE thật: lập phiếu hoàn tiền từ đơn -> toast", any(m == "POST" and "refunds/create" in u and s in (200, 201) for m, u, s in reqs), str([x for x in reqs if "refund" in x[1]]))

    # phiếu hoàn tiền: seed_qa có sẵn phiếu Chờ hoàn tiền (PENDING), thêm phiếu vừa lập
    page.goto(BASE + "/orders/refunds/")
    page.wait_for_load_state("networkidle")
    expect(page.locator("tbody tr.lt-click").first).to_be_visible()
    ok("BE thật: tab Phiếu hoàn tiền có phiếu Chờ hoàn tiền", "Chờ hoàn tiền" in page.locator("tbody").inner_text())
    page.locator("tbody tr.lt-click", has_text="Chờ hoàn tiền").first.click()
    page.wait_for_url(re.compile(r"/orders/refunds/detail/\?id=\d+$"))
    expect(page.locator("main header h2")).to_be_visible()
    page.wait_for_load_state("networkidle")
    ok("BE thật: chi tiết phiếu hoàn tiền có 'Xác nhận đã hoàn tiền'", page.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).count() == 1)
    page.get_by_role("button", name=re.compile("^Xác nhận đã hoàn")).first.click()
    d = page.get_by_role("dialog", name="Xác nhận đã hoàn tiền")
    d.get_by_label("Mã giao dịch chuyển khoản hoàn").fill("HT-R3-" + uuid.uuid4().hex[:8])
    d.locator("button[type=submit]").click()
    expect(page.locator("main header")).to_contain_text("Đã hoàn tiền")
    ok("BE thật: xác nhận hoàn -> Đã hoàn tiền", True)
    page.goto(BASE + "/orders/payments/")
    page.wait_for_load_state("networkidle")
    ok("BE thật: hàng chờ thanh toán tải được (seed_qa có khoản tiền chờ xử lý)", page.locator("tbody tr").count() > 0)
    page.goto(BASE + "/orders/detail/?id=999999")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text(re.compile("Không tìm thấy|không tồn tại|không có quyền"))).to_be_visible()
    ok("BE thật: id không tồn tại -> màn không tìm thấy", True)
    ok("BE thật: không có lỗi console ngoài 404 cố ý", not [e for e in errs if "404" not in e and "Failed to load resource" not in e and "fonts.g" not in e
                                                                   and "Failed to fetch RSC payload" not in e], str(errs[:3]))  # RSC: prefetch bị huỷ khi goto giữa chừng (máy chủ tĩnh), không phải lỗi app
    bad = [x for x in reqs if x[2] >= 500]
    ok("BE thật: không có phản hồi 5xx", not bad, str(bad))
    ctx.close()

    # Quản lý
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "qa_manager")
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    expect(page.locator("tbody tr.lt-click").first).to_be_visible()
    tabs = [t.strip() for t in page.get_by_role("tab").all_inner_texts()]
    ok("BE thật: Quản lý thấy tab Đơn hàng + Phiếu hoàn tiền, không có Hàng chờ thanh toán", tabs == ["Đơn hàng", "Phiếu hoàn tiền"], str(tabs))
    page.locator("tbody tr.lt-click").first.click()
    page.wait_for_url(re.compile(r"/orders/detail/\?id=\d+$"))
    expect(page.locator("main header h2")).to_be_visible()
    page.wait_for_load_state("networkidle")
    ok("BE thật: Quản lý không có nút 'Xác nhận đã nhận tiền', không thấy 'Giá vốn'",
       page.get_by_role("button", name="Xác nhận đã nhận tiền").count() == 0 and "Giá vốn" not in page.locator("main").inner_text())
    b.close()
finish(R)
