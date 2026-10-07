"""QA độc lập đợt 1: menu và chặn truy cập theo vai (ED-01-AC1/AC5/AC6, ED-03-AC8, G9, UI-RULES §2.1, §8.1).

Vai mock: loc (chủ), ql1 (quản lý), kho1 (kho + giao), giao1 (chỉ giao), cs2 (gọi xác nhận + giao),
cùng hai ca ngoài đường thuận: CSKH thuần (patchUser) và tài khoản không nhóm (admin).
In ra bảng vai x đường dẫn để dán vào báo cáo.
"""

import json
import sys

from playwright.sync_api import sync_playwright

from qa_ed_batch1_common import (BASE, EXPECTED_MENU, FULL_ORDER, SECTION_OF, SECTION_ORDER, SHOTS, fonts_ready, is_subsequence, login,
                                 nav_heads, nav_labels, ok, relevant_errors, summary)

ROUTES = ["/overview/", "/orders/", "/orders/payments/", "/orders/refunds/", "/confirmation/", "/deliveries/",
          "/my-deliveries/", "/purchasing/", "/inventory/", "/stocktake/", "/ledger/", "/catalog/", "/reports/", "/content/",
          "/customers/", "/suppliers/", "/returns/", "/accounting/sales-invoices/", "/accounting/purchase-invoices/", "/permissions/",
          "/content/categories/", "/staff/", "/audit-logs/", "/ai/policy/", "/ai/report/", "/ai/settings/",
          "/ai/actions/", "/account/"]
USERS = ["loc", "ql1", "kho1", "giao1", "cs2"]
NO_PERMISSION_TITLE = "Bạn không có quyền xem mục này"


def outcome(page, path):
    """'noperm' | 'ok' | 'error' | 'notfound' — dựa trên chữ hiển thị thật."""
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("#rail-left, .page-state", state="attached")
    # chờ màn vẽ xong: có h1 topbar và một trong (nội dung, thông báo)
    page.wait_for_function("() => document.querySelector('#main') && document.querySelector('#main').innerText.trim().length > 0")
    text = page.locator("#main").inner_text()
    if NO_PERMISSION_TITLE in text:
        return "noperm"
    if "Có lỗi xảy ra" in text:
        return "error"
    if "Không tìm thấy trang này" in text:
        return "notfound"
    return "ok"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    errors = []
    matrix = {}
    menu_of = {}
    apilog_noperm = {}

    for user in USERS:
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        page = ctx.new_page()
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        login(page, user)
        labels = nav_labels(page)
        heads = nav_heads(page)
        menu_of[user] = labels
        ok(f"[{user}] menu theo thứ tự UI-RULES §2.1", is_subsequence(labels, FULL_ORDER), str(labels))
        ok(f"[{user}] nhóm menu theo thứ tự §2.1 và chỉ hiện nhóm có mục", is_subsequence(heads, SECTION_ORDER) and
           set(heads) == {SECTION_OF[x] for x in labels if SECTION_OF[x]}, f"{heads} / {labels}")
        # mục nằm đúng nhóm
        group_ok = True
        current = ""
        for node in page.locator("#rail-left .nav-group").all():
            h = node.locator(".nav-h")
            sec = h.inner_text().strip() if h.count() else ""
            for t in node.locator("a").all_inner_texts():
                if SECTION_OF[t.split("\n")[-1].strip()] != sec:
                    group_ok = False
        ok(f"[{user}] mỗi mục nằm đúng nhóm §2.1", group_ok)
        ok(f"[{user}] topbar không có 'Làm mới', không nút sáng/tối",
           page.get_by_text("Làm mới").count() == 0 and page.locator(".theme-toggle").count() == 0
           and page.get_by_role("button", name="Chế độ sáng").count() + page.get_by_role("button", name="Chế độ tối").count() == 0)
        # menu mở ra được từng mục bằng bấm thật
        broken = []
        for lab in labels:
            link = page.locator("#rail-left .nav a", has_text=lab).first
            href = link.get_attribute("href")
            link.click()
            page.wait_for_url("**" + href)
            page.wait_for_load_state("networkidle")
            page.wait_for_function("() => document.querySelector('#main') && document.querySelector('#main').innerText.trim().length > 0")
            text = page.locator("#main").inner_text()
            h1 = page.locator("header.topbar h1").inner_text().strip()
            cur = page.locator("#rail-left .nav a[aria-current=page]").all_inner_texts()
            if NO_PERMISSION_TITLE in text or "Có lỗi xảy ra" in text or "Không tìm thấy trang" in text:
                broken.append(f"{lab}: màn lỗi/không quyền")
            elif h1 != lab or [c.split('\n')[-1].strip() for c in cur] != [lab]:
                broken.append(f"{lab}: h1={h1!r} cur={cur}")
        ok(f"[{user}] bấm từng mục menu đều mở đúng màn, tô đúng mục, tên màn ở topbar khớp", not broken, broken)

        # ma trận truy cập trực tiếp
        row = {}
        for path in ROUTES:
            page.evaluate("() => window.__caveMock && window.__caveMock.clearLog && window.__caveMock.clearLog()") if False else None
            row[path] = outcome(page, path)
        matrix[user] = row
        ctx.close()

    # ---------- khẳng định theo story ----------
    m = matrix
    # Mục AI chỉ có khi build bật AI (NEXT_PUBLIC_AI_FEATURES=1). Build tắt AI: các đường dẫn /ai/* trả "Không tìm thấy trang này".
    ai_on = "Chính sách AI" in menu_of["loc"]
    AI_ROUTES = {"/ai/policy/", "/ai/report/", "/ai/settings/", "/ai/actions/"}
    denied = "noperm" if ai_on else "notfound"
    ok("ED-01-AC5 giao1: menu đúng việc của vai ('Việc giao của tôi', 'Hàng hoàn' để Mang hàng về kho)", menu_of["giao1"] == EXPECTED_MENU["giao1"], str(menu_of["giao1"]))
    ok("ED-01-AC5 giao1: Đơn & tiền, Giao hàng, Tổng quan, báo cáo, nhân sự... đều không có quyền khi vào thẳng URL",
       all(m["giao1"][r] == (denied if r in AI_ROUTES else "noperm") for r in ["/overview/", "/orders/", "/orders/payments/", "/orders/refunds/", "/deliveries/",
                                              "/purchasing/", "/inventory/", "/stocktake/", "/ledger/", "/catalog/", "/reports/", "/content/",
                                              "/staff/", "/audit-logs/", "/ai/report/", "/confirmation/"]),
       {r: m["giao1"][r] for r in ROUTES})
    # Có sẵn từ gốc (màn AI chưa chuyển, thuộc lô 15): /ai/policy/ không bọc ViewGuard nên vai nào cũng thấy khung màn.
    ok("G9 /ai/policy/ chặn người không phải chủ (build tắt AI: không có trang)", m["ql1"]["/ai/policy/"] == denied and m["giao1"]["/ai/policy/"] == denied,
       {u: m[u]["/ai/policy/"] for u in USERS})
    ok("ED-01-AC5 giao1 mở 'Việc giao của tôi' và 'Tài khoản của tôi' được", m["giao1"]["/my-deliveries/"] == "ok" and m["giao1"]["/account/"] == "ok",
       {r: m["giao1"][r] for r in ["/my-deliveries/", "/account/"]})
    ok("ED-03-AC8 kho1 mở thẳng URL Báo cáo lãi lỗ: không có quyền", m["kho1"]["/reports/"] == "noperm", m["kho1"]["/reports/"])
    ok("ED-03-AC8 ql1 mở thẳng URL Báo cáo lãi lỗ: không có quyền", m["ql1"]["/reports/"] == "noperm", m["ql1"]["/reports/"])
    ok("ED-03-AC8 chủ mở được Báo cáo lãi lỗ", m["loc"]["/reports/"] == "ok", m["loc"]["/reports/"])
    ok("G9 kho1, ql1 không vào được Nhân sự", m["kho1"]["/staff/"] == "noperm" and m["ql1"]["/staff/"] == "noperm")
    ok("G9 kho1 không vào được Nhật ký hoạt động; ql1 vào được", m["kho1"]["/audit-logs/"] == "noperm" and m["ql1"]["/audit-logs/"] == "ok",
       (m["kho1"]["/audit-logs/"], m["ql1"]["/audit-logs/"]))
    ok("G9 ql1/kho1 không vào được hàng chờ thanh toán (chỉ chủ)", m["ql1"]["/orders/payments/"] == "noperm" and m["kho1"]["/orders/payments/"] == "noperm")
    # đồng bộ menu và bảo vệ màn: mục menu hiện thì vào được, khớp 1-1
    label_route = {"Tổng quan": "/overview/", "Đơn & tiền": "/orders/", "Khách hàng": "/customers/", "Gọi xác nhận": "/confirmation/", "Giao hàng": "/deliveries/",
                   "Việc giao của tôi": "/my-deliveries/", "Mua hàng": "/purchasing/", "Nhà cung cấp": "/suppliers/", "Kho & lô": "/inventory/",
                   "Hàng hoàn": "/returns/", "Kiểm kê": "/stocktake/", "Sổ nhập xuất": "/ledger/", "Chính sách AI": "/ai/policy/", "Báo cáo AI": "/ai/report/",
                   "Danh mục & giá": "/catalog/", "Báo cáo lãi lỗ": "/reports/", "Hoá đơn bán": "/accounting/sales-invoices/",
                   "Hoá đơn mua & chi phí": "/accounting/purchase-invoices/", "Nội dung": "/content/", "Nhân sự": "/staff/", "Phân quyền": "/permissions/",
                   "Nhật ký hoạt động": "/audit-logs/"}
    mismatch = []
    for user in USERS:
        shown = {label_route[l] for l in menu_of[user]}
        for lab, route in label_route.items():
            allowed = m[user][route] == "ok"
            if (route in shown) != allowed:
                mismatch.append(f"{user} {route}: menu={route in shown} màn={m[user][route]}")
    ok("G9 menu và chặn URL khớp nhau cho cả 5 vai (mục menu hiện <=> vào được màn)", not mismatch, mismatch)
    ok("Không màn nào báo lỗi hay 404 với vai bất kỳ (trừ /ai/* ở build tắt AI)",
       all(v not in ("error", "notfound") for r in m.values() for p_, v in r.items() if ai_on or p_ not in AI_ROUTES),
       [(u, p_, v) for u, r in m.items() for p_, v in r.items() if v in ("error", "notfound") and (ai_on or p_ not in AI_ROUTES)])

    # ---------- ca ngoài đường thuận ----------
    # 1) CSKH thuần (không kèm nhóm giao): đổi nhóm bằng patchUser
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.on("console", lambda m_: m_.type == "error" and errors.append(m_.text))
    login(page, "cs2")
    page.evaluate("() => window.__caveMock.patchUser('cs2', {groups: ['customer_service']})")
    page.reload()
    page.wait_for_selector("#rail-left .nav a", state="attached")
    labels = nav_labels(page)
    ok("CSKH thuần: menu không có Việc giao của tôi, Tổng quan, kho, kế toán, quản trị",
       labels == ["Đơn & tiền", "Gọi xác nhận", "Giao hàng"], str(labels))
    page.goto(BASE + "/reports/")
    page.wait_for_function("() => document.querySelector('#main') && document.querySelector('#main').innerText.trim().length > 0")
    ok("CSKH thuần: Báo cáo lãi lỗ -> không có quyền", NO_PERMISSION_TITLE in page.locator("#main").inner_text())
    page.goto(BASE + "/inventory/")
    page.wait_for_function("() => document.querySelector('#main') && document.querySelector('#main').innerText.trim().length > 0")
    ok("CSKH thuần: Kho & lô -> không có quyền", NO_PERMISSION_TITLE in page.locator("#main").inner_text())
    page.evaluate("() => window.__caveMock.resetUsers()")
    ctx.close()

    # 2) ED-01-AC6: gỡ quyền thì menu đổi mà không sửa code
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "ql1")
    before = nav_labels(page)
    page.evaluate("() => window.__caveMock.patchUser('ql1', {denied_perms: ['catalog.view_item', 'content.view_entry']})")
    page.reload()
    page.wait_for_selector("#rail-left .nav a", state="attached")
    after = nav_labels(page)
    ok("ED-01-AC6 gỡ quyền xem mặt hàng + nội dung -> 2 mục biến mất sau khi tải lại, mục khác còn",
       ("Danh mục & giá" in before and "Nội dung" in before) and "Danh mục & giá" not in after and "Nội dung" not in after
       and after == [x for x in before if x not in ("Danh mục & giá", "Nội dung")], f"{before} -> {after}")
    page.goto(BASE + "/catalog/")
    page.wait_for_function("() => document.querySelector('#main') && document.querySelector('#main').innerText.trim().length > 0")
    ok("ED-01-AC6 vào thẳng URL mục đã bị gỡ quyền -> không có quyền", NO_PERMISSION_TITLE in page.locator("#main").inner_text())
    # thêm quyền: mục hiện đủ theo thứ tự §2.1 khi mọi quyền menu đều có
    page.evaluate("""() => window.__caveMock.patchUser('ql1', {denied_perms: [], extra_perms: [
        'sales.view_customer_list','purchasing.view_supplier','inventory.view_returntostock','inventory.view_stockledgerentry',
        'purchasing.view_purchasecost','accounts.manage_staff','ai.manage_ai_policy']})""")
    page.reload()
    page.wait_for_selector("#rail-left .nav a", state="attached")
    labels = nav_labels(page)
    ok("ED-01-AC6 cấp thêm quyền: mục Nhân sự hiện ra (và mục AI nếu build bật AI), vẫn đúng thứ tự §2.1",
       ("Chính sách AI" in labels and "Báo cáo AI" in labels or not ai_on) and "Nhân sự" in labels and is_subsequence(labels, FULL_ORDER), str(labels))
    page.screenshot(path=f"{SHOTS}/roles-ql1-extra-perms.png")
    page.evaluate("() => window.__caveMock.resetUsers()")
    ctx.close()

    # 3) tài khoản không nhóm và mật khẩu tạm
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "admin", wait_nav=False)
    page.wait_for_url("**/no-role/")
    ok("Tài khoản không nhóm: về màn 'chưa được phân quyền', không có sidebar", page.locator("#rail-left").count() == 0)
    page.goto(BASE + "/orders/")
    page.wait_for_load_state("networkidle")
    ok("Tài khoản không nhóm: URL nghiệp vụ không vẽ menu và không cho xem", page.locator("#rail-left .nav a").count() == 0)
    ctx.close()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    login(page, "kho5", wait_nav=False)
    page.wait_for_url("**/set-password/**")
    page.goto(BASE + "/inventory/")
    page.wait_for_url("**/set-password/**")
    ok("Mật khẩu tạm (kho5): vào URL khác bị đưa về Đặt mật khẩu mới", "/set-password" in page.url, page.url)
    ctx.close()

    # 4) chưa đăng nhập
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(BASE + "/orders/")
    page.wait_for_url("**/login/**")
    ok("Chưa đăng nhập: /orders/ -> màn Đăng nhập, không có sidebar", page.locator("#rail-left").count() == 0, page.url)
    ctx.close()
    ok("Không lỗi console trong các ca vai", not relevant_errors(errors), relevant_errors(errors)[:5])
    browser.close()

print("MATRIX " + json.dumps({"menu": menu_of, "routes": matrix}, ensure_ascii=False))
sys.exit(summary())
