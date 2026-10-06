"""Lô áp tên chuẩn (02b mục 3.3): quét mọi route ERP, không còn chữ cũ (nhóm A) và chip/ô đúng chữ chuẩn (nhóm B).

Chạy trên bản build MOCK (dữ liệu giả). Mỗi lần chỉ giữ một bản `out/`:
    cd erp-console
    NEXT_PUBLIC_USE_MOCK=1 npm run build
    (cd out && python3 -m http.server 3219 --bind 127.0.0.1 &) ; BASE=http://127.0.0.1:3219 python3 e2e/standard_names_all_routes.py
    # tắt server sau khi xong
Vai: loc (Chủ) và ql1 (Quản lý). Nguồn chữ: doc/thuat-ngu-va-trang-thai.md mục 4.
Shop (tuỳ chọn): đặt SHOP_BASE=http://127.0.0.1:3220 (bản build mock của frontend/) để quét thêm /shop/orders/: BOOKED, AUTO_CANCELLED,
có hoàn tiền, đủ trạng thái phiếu giao, cấm mã thô.
TODO: chạy lần hai trên BE thật (staging local, dữ liệu giả) khi có.
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3219")
ROUTES = [
    "/overview/", "/orders/", "/orders/payments/", "/orders/refunds/", "/orders/detail/?id=1", "/orders/payments/detail/?id=1",
    "/orders/refunds/detail/?id=1", "/customers/", "/customers/detail/?id=1", "/confirmation/", "/confirmation/detail/?id=31",
    "/confirmation/scripts/", "/deliveries/", "/deliveries/detail/?id=1", "/deliveries/lookup/", "/my-deliveries/",
    "/purchasing/", "/purchasing/detail/?id=1", "/suppliers/", "/suppliers/detail/?id=1", "/inventory/", "/inventory/detail/?id=1",
    "/returns/", "/returns/detail/?id=1", "/stocktake/", "/stocktake/detail/?id=1", "/ledger/", "/catalog/", "/catalog/detail/?id=1",
    "/reports/", "/accounting/sales-invoices/", "/accounting/purchase-invoices/", "/content/", "/content/categories/",
    "/content/edit/?id=44", "/staff/", "/staff/detail/?id=1", "/permissions/", "/permissions/detail/?group=manager&code=manager",
    "/audit-logs/", "/account/",
]

# Nhóm A: chuỗi con trên innerText (không phân biệt hoa thường với regex phiếu hoàn).
GROUP_A = [
    "TTL", "Webhook", "Sandbox", "Production", "Khớp — đã xác nhận", "Về sau khi đơn tự huỷ", "Hư khi đóng hàng",
    "Hư hỏng khi soạn hàng", "Bỏ sau khi giao thất bại", "Bỏ giao sau khi thất bại", "chưa hiện thực", "Hàng hoàn về kho",
    "Trả hàng về kho", "trả về kho", "hàng về kho:", "phiếu hàng về kho", "đảo doanh thu", "hoá đơn điều chỉnh", "phiếu giảm trừ",
    "Phiếu hoàn chờ chuyển", "Tạo phiếu hoàn", "Thử hoàn lại", "Publish", "hạch toán", "Huỷ bỏ, ghi lỗ", "Mục chờ gọi CSKH",
    "Phiếu giao hàng", "Giao dịch thanh toán", "Phiếu nhập kho", "Phiếu điều chỉnh kho", "Trả NCC", "Trả lô về nhà cung cấp",
    "Giao không xác nhận", "Gia hạn thêm", "Gia hạn giao", "Bỏ qua bước", "Cần gọi ngay", "Xác nhận thanh toán thủ công",
    "Giao phiếu cho người giao", "Gán phiếu giao", "Đóng gói phiếu giao", "Điều khoản mua hàng", "Đổi trả hoàn tiền",
    "Combo dạng gói", "Khách muốn đổi món –",
]
# "chờ Chủ" chỉ cấm khi là đuôi nhãn ("... — chờ Chủ"); câu "chờ Chủ hoặc Quản lý duyệt" là lời văn hợp lệ.
GROUP_A_REGEX = [r"— chờ Chủ(?! hoặc)", r"phiếu hoàn(?! tiền)", r"\bBR-"]
# Nhóm B: chữ của một chip (.stat-chip) không được là một trong các giá trị cũ. Chip trùng nhãn chuẩn khác thì không cấm toàn trang.
CHIP_BANNED = {
    "/deliveries/": {"Chờ xác nhận", "Soạn hàng", "Hoàn tất"},
    "/deliveries/detail/?id=1": {"Chờ xác nhận", "Soạn hàng", "Hoàn tất"},
    "/my-deliveries/": {"Chờ xác nhận", "Soạn hàng", "Hoàn tất"},
    "/orders/detail/?id=1": {"Chờ xác nhận", "Soạn hàng"},
    "/confirmation/": {"Hoàn tất", "Sai số", "Khách muốn huỷ", "Khách muốn đổi"},
    "/confirmation/detail/?id=31": {"Hoàn tất", "Sai số", "Khách muốn huỷ", "Khách muốn đổi"},
    "/orders/refunds/": {"Chờ hoàn", "Đã hoàn", "Thất bại"},
    "/orders/refunds/detail/?id=1": {"Chờ hoàn", "Đã hoàn", "Thất bại"},
    "/orders/payments/detail/?id=1": {"Chờ hoàn", "Đã hoàn", "Thất bại"},
    "/catalog/": {"Đang bật"},
    "/content/": {"Bảo mật"},
}
# TODO F1: Phân quyền còn chữ cũ vì features/permissions/mock.ts thuộc nhánh F1. Chỉ in cảnh báo, không đỏ; bỏ khỏi danh sách khi F1 gộp.
PENDING_ROUTES = {"/permissions/", "/permissions/detail/?group=manager&code=manager"}
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:300]), flush=True)


def login(page, user):
    page.goto(BASE + "/login/")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")


def visible_text(page):
    """innerText cộng aria-label / title / placeholder (chữ hiển thị hoặc đọc ra)."""
    return page.evaluate(
        """() => {
          const parts = [document.body.innerText];
          for (const el of document.querySelectorAll("[aria-label],[title],[placeholder]"))
            for (const a of ["aria-label", "title", "placeholder"]) { const v = el.getAttribute(a); if (v) parts.push(v); }
          return parts.join("\\n");
        }"""
    )


def chips(page):
    return [t.strip() for t in page.locator(".stat-chip").all_inner_texts()]


def sweep(browser, user):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, user)
    found, chip_hits, shown = {}, {}, {}
    for route in ROUTES:
        page.goto(BASE + route)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(250)
        text = visible_text(page)
        hits = [w for w in GROUP_A if w in text]
        hits += [r for r in GROUP_A_REGEX if re.search(r, text, re.I if "phiếu" in r else 0)]
        if hits:
            found[route] = hits[:4]
        cs = chips(page)
        shown[route] = cs
        bad = CHIP_BANNED.get(route, set()) & set(cs)
        if bad:
            chip_hits[route] = sorted(bad)
    pending = {r: w for r, w in found.items() if r in PENDING_ROUTES}
    found = {r: w for r, w in found.items() if r not in PENDING_ROUTES}
    if pending:
        print(f"WARN [{user}] còn chữ cũ ở route chờ Pha B/F1: {pending}", flush=True)
    ok(f"[{user}] nhóm A: 0 chữ cấm ở {len(ROUTES) - len(PENDING_ROUTES)} route (trừ route chờ Pha B/F1)", not found, found)
    ok(f"[{user}] nhóm B: 0 chip mang chữ cũ", not chip_hits, chip_hits)
    if user == "loc":
        all_chips = {c for cs in shown.values() for c in cs}
        # Đối chứng dương: quét không rỗng và chữ chuẩn có xuất hiện.
        ok(f"[{user}] đơn AUTO_CANCELLED hiện chip 'Hết giờ giữ chỗ'", "Hết giờ giữ chỗ" in shown.get("/orders/", []), shown.get("/orders/"))
        ok(f"[{user}] chip phiếu giao dùng chữ chuẩn", bool({"Chờ gọi xác nhận", "Đang soạn hàng", "Đã giao"} & all_chips), sorted(all_chips)[:30])
        ok(f"[{user}] chip phiếu hoàn tiền dùng chữ chuẩn", bool({"Chờ hoàn tiền", "Đã hoàn tiền", "Hoàn thất bại"} & all_chips), sorted(all_chips)[:30])
        page.goto(BASE + "/orders/refunds/")
        page.wait_for_load_state("networkidle")
        ok(f"[{user}] menu: 'Hoàn tiền chờ chuyển' không còn 'Phiếu hoàn chờ chuyển'", "Phiếu hoàn chờ chuyển" not in page.inner_text("body"))
        page.goto(BASE + "/returns/")
        page.wait_for_load_state("networkidle")
        nav = page.locator("nav").all_inner_texts()
        ok(f"[{user}] menu có 'Hàng hoàn', không còn 'Hàng hoàn về kho'", any("Hàng hoàn" in t for t in nav) and not any("Hàng hoàn về kho" in t for t in nav), nav)
        # Nhật ký (T67-T76, W11, T49): cột Thao tác không còn "Thao tác khác", cột Người không còn "Người dùng".
        page.goto(BASE + "/audit-logs/")
        page.wait_for_load_state("networkidle")
        cells = page.locator("tbody td").all_inner_texts()
        ok(f"[{user}] Nhật ký: không có ô 'Thao tác khác' hay 'Người dùng'", not any(c.strip() in ("Thao tác khác", "Người dùng") for c in cells), [c for c in cells if c.strip() in ("Thao tác khác", "Người dùng")][:3])
        body = page.inner_text("main")
        ok(f"[{user}] Nhật ký: phiếu giao FAILED dịch là 'Giao thất bại' (W11), tem dùng 'In tem giao'", "Đang giao → Giao thất bại" in body and "In tem giao" in body, body[:200])
    ctx.close()


SHOP_CASES = [  # (mã đơn, 4 số cuối SĐT, chữ phải có)
    ("DH-DEMO002", "1234", "Chờ thanh toán"), ("DH-DEMO003", "4321", "Đã huỷ vì quá giờ thanh toán"),
    ("DH-DEMO004", "5678", "Đang chờ hoàn tiền"), ("DH-DEMO005", "5001", "Chờ vựa gọi xác nhận"),
    ("DH-DEMO006", "5002", "Đã soạn xong, chờ giao"), ("DH-DEMO007", "5003", "Đang giao"),
    ("DH-DEMO008", "5004", "Đã giao"), ("DH-DEMO009", "5005", "Giao chưa thành công, vựa sẽ liên hệ lại"),
]
RAW = re.compile(r"\b(CONFIRMING|PREPARING|READY|DELIVERING|COMPLETED|FAILED|CANCELLED|BOOKED|AUTO_CANCELLED)\b")


def shop_sweep(browser):
    shop = os.environ.get("SHOP_BASE")
    if not shop:
        print("SKIP Shop: chưa đặt SHOP_BASE", flush=True)
        return
    page = browser.new_context(viewport={"width": 390, "height": 800}, reduced_motion="reduce").new_page()
    for code, last4, want in SHOP_CASES:
        page.goto(shop + "/shop/orders/")
        page.wait_for_load_state("networkidle")
        page.fill("#orderCode", code)
        page.fill("#phoneLast4", last4)
        page.locator("form button[type=submit]").click()
        page.locator(".status-badge").wait_for(timeout=8000)
        body = page.inner_text("main")
        ok(f"[Shop {code}] có '{want}', không mã thô, không chữ cấm nhóm A", want in body and not RAW.search(body) and not [w for w in GROUP_A if w in body], body[-200:])


with sync_playwright() as p:
    browser = p.chromium.launch()
    for user in ("loc", "ql1"):
        sweep(browser, user)
    shop_sweep(browser)
    browser.close()
passed = sum(1 for _, c, _ in results if c)
print(f"== {passed}/{len(results)} PASS")
sys.exit(0 if passed == len(results) else 1)
