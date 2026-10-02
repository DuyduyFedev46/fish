# A4 CSKH — CS-02-AC6 (bảng phiếu giao mobile 360x640) & CS-05-AC8 (hàng chờ CSKH mobile 360x640).
# Chạy: cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3203 &)
#       SHOTS=<thư mục ảnh> python3 e2e/ra_soat_cs02_cs05_mobile_360.py     # tắt server sau khi xong
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3203")
SHOTS = os.environ.get("SHOTS", "/tmp")
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


def no_horizontal_scroll(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )


def min_tap_target_ok(page, selector, min_px=44):
    """Trả (ok, list vi phạm) cho các phần tử khớp selector đang hiển thị."""
    boxes = page.eval_on_selector_all(
        selector,
        """(els) => els
            .filter(e => e.offsetParent !== null)
            .map(e => { const r = e.getBoundingClientRect(); return {w: r.width, h: r.height, text: (e.innerText||'').slice(0,30)}; })
        """,
    )
    violations = [b for b in boxes if b["h"] < min_px - 0.5]
    return len(violations) == 0 and len(boxes) > 0, violations, boxes


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ---------- CS-02-AC6: Bảng phiếu giao 360x640, dạng thẻ, không cuộn ngang, vùng bấm >= 44px ----------
    ctx1 = browser.new_context(viewport={"width": 360, "height": 640})
    page1 = ctx1.new_page()
    login(page1, "kho1")
    page1.goto(BASE + "/deliveries/")
    page1.wait_for_load_state("networkidle")
    page1.wait_for_timeout(500)
    page1.screenshot(path=f"{SHOTS}/cs02-ac6-deliveries-360x640.png", full_page=True)

    ok("CS-02-AC6: không cuộn ngang ở 360x640", no_horizontal_scroll(page1))

    # ERP theo design (ED-04): danh sách là bảng cuộn NGAY TRONG thẻ (.lt-scroll), không cuộn cả trang; dòng bấm được cao >= 44px.
    in_scroll = page1.eval_on_selector_all(
        "table.lt", "els => els.length > 0 && els.every(e => !!e.closest('.lt-scroll'))"
    )
    ok("CS-02-AC6: bảng nằm trong vùng cuộn riêng của thẻ (không đẩy trang rộng ra)", in_scroll)

    row_ok, row_violations, row_boxes = min_tap_target_ok(page1, "table.lt tbody tr.lt-click")
    ok(
        f"CS-02-AC6: {len(row_boxes)} dòng phiếu giao có vùng bấm >= 44px",
        row_ok,
        str(row_violations[:3]),
    )

    # ---------- CS-05-AC8: Hàng chờ CSKH 360x640, link tel:, nút kết quả >= 44px ở nửa dưới màn hình ----------
    ctx2 = browser.new_context(viewport={"width": 360, "height": 640})
    page2 = ctx2.new_page()
    login(page2, "cs1")
    page2.goto(BASE + "/confirmation/")
    page2.wait_for_load_state("networkidle")
    page2.wait_for_timeout(500)
    page2.screenshot(path=f"{SHOTS}/cs05-ac8-queue-360x640.png", full_page=True)

    ok("CS-05-AC8: không cuộn ngang ở 360x640 (hàng chờ)", no_horizontal_scroll(page2))

    # SĐT là link tel: ở danh sách
    tel_links = page2.eval_on_selector_all("a[href^='tel:']", "els => els.map(e => e.getAttribute('href'))")
    ok("CS-05-AC8: SĐT hiện dưới dạng link tel: ở danh sách", len(tel_links) > 0, str(tel_links))

    # ERP theo design (ED-15): bấm dòng mở trang chi tiết /confirmation/detail/?id=<số>; nút Gọi khách (tel:) và Ghi kết quả gọi nằm ở header
    page2.locator("table.lt tbody tr", has_text="SO260928-3F9A01").locator("a").first.click()
    page2.wait_for_url("**/confirmation/detail/?id=31")
    page2.get_by_role("heading", name="SO260928-3F9A01").wait_for()
    page2.wait_for_timeout(400)
    page2.screenshot(path=f"{SHOTS}/cs05-ac8-detail-360x640.png", full_page=True)
    ok("CS-05-AC8: không cuộn ngang ở 360x640 (chi tiết đơn)", no_horizontal_scroll(page2))

    call_ok, call_violations, call_boxes = min_tap_target_ok(page2, "a.btn[href^='tel:']")
    ok("CS-05-AC8: nút Gọi khách (tel:) cao >= 44px", call_ok, str(call_violations))
    rec_ok, rec_violations, rec_boxes = min_tap_target_ok(page2, "button.btn.primary")
    ok("CS-05-AC8: nút Ghi kết quả gọi cao >= 44px", rec_ok, str(rec_violations))

    # Hộp ghi kết quả: không cuộn ngang, các lựa chọn kết quả cao >= 44px, nằm gọn trong màn hình
    page2.get_by_role("button", name="Ghi kết quả gọi").click()
    page2.get_by_role("dialog").wait_for()
    page2.wait_for_timeout(300)
    page2.screenshot(path=f"{SHOTS}/cs05-ac8-call-modal-360x640.png")
    ok("CS-05-AC8: không cuộn ngang ở 360x640 (hộp ghi kết quả)", no_horizontal_scroll(page2))
    pick_ok, pick_violations, pick_boxes = min_tap_target_ok(page2, "[role='dialog'] label[class*='pick']")
    ok(f"CS-05-AC8: {len(pick_boxes)} lựa chọn kết quả cuộc gọi cao >= 44px", pick_ok and len(pick_boxes) >= 6, str(pick_violations[:3]))
    box = page2.eval_on_selector("[role='dialog']", "e => { const r = e.getBoundingClientRect(); return [r.left, r.right, window.innerWidth]; }")
    ok("CS-05-AC8: hộp nằm gọn trong chiều ngang màn hình", box[0] >= -1 and box[1] <= box[2] + 1, str(box))

    browser.close()

print("\n=== TỔNG KẾT ===")
n_ok = sum(1 for _, c, _ in results if c)
print(f"{n_ok}/{len(results)} PASS")
failed = [(n, e) for n, c, e in results if not c]
if failed:
    print("FAILED:", failed)
    sys.exit(1)
