"""Lô áp tên chuẩn (02b mục 3.3): quét mọi route ERP, không còn chữ cũ (nhóm A) và chip/ô đúng chữ chuẩn (nhóm B).

Chạy trên bản build MOCK (dữ liệu giả). Mỗi lần chỉ giữ một bản `out/`:
    cd erp-console
    NEXT_PUBLIC_USE_MOCK=1 npm run build
    (cd out && python3 -m http.server 3219 --bind 127.0.0.1 &) ; BASE=http://127.0.0.1:3219 python3 e2e/standard_names_all_routes.py
    # tắt server sau khi xong
Vai: loc (Chủ) và ql1 (Quản lý). Nguồn chữ: doc/thuat-ngu-va-trang-thai.md mục 4.
TODO Pha B: thêm Shop /shop/orders/ (BOOKED, AUTO_CANCELLED, có hoàn tiền, có phiếu giao, cấm mã thô), cột Thao tác Nhật ký
(Thao tác khác) có dữ liệu mock sau khi auditModel.ts được sửa, và chạy lần hai trên BE thật (staging local).
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
# TODO Pha B / F1: các route này còn chữ cũ vì nguồn chữ nằm ở file chưa đụng được (Nhật ký: auditModel.ts chờ W37 L3;
# Phân quyền: features/permissions/mock.ts thuộc nhánh F1). Chỉ in cảnh báo, không đỏ. Bỏ khỏi danh sách khi các file đó được sửa.
PENDING_ROUTES = {"/audit-logs/", "/permissions/", "/permissions/detail/?group=manager&code=manager"}
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
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    for user in ("loc", "ql1"):
        sweep(browser, user)
    browser.close()
passed = sum(1 for _, c, _ in results if c)
print(f"== {passed}/{len(results)} PASS")
sys.exit(0 if passed == len(results) else 1)
