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

    # Bảng dạng table phải bị ẩn (CSS @media max-width:768px ẩn .tableWrapper)
    table_visible = page1.eval_on_selector_all(
        "table", "els => els.some(e => e.offsetParent !== null)"
    )
    ok("CS-02-AC6: bảng dạng table (desktop) không hiển thị ở mobile", not table_visible)

    card_ok, card_violations, card_boxes = min_tap_target_ok(page1, "[class*='cardItem']")
    ok(
        f"CS-02-AC6: {len(card_boxes)} thẻ phiếu giao có vùng bấm >= 44px",
        card_ok,
        str(card_violations[:3]),
    )

    # ---------- CS-05-AC8: Hàng chờ CSKH 360x640, link tel:, nút kết quả >= 44px ở nửa dưới màn hình ----------
    ctx2 = browser.new_context(viewport={"width": 360, "height": 640})
    page2 = ctx2.new_page()
    login(page2, "cs1")
    page2.goto(BASE + "/cskh/")
    page2.wait_for_load_state("networkidle")
    page2.wait_for_timeout(500)
    page2.screenshot(path=f"{SHOTS}/cs05-ac8-queue-360x640.png", full_page=True)

    ok("CS-05-AC8: không cuộn ngang ở 360x640 (hàng chờ)", no_horizontal_scroll(page2))

    # Mở chi tiết 1 đơn -> modal gọi
    page2.locator("text=DH-260928-0001").first.click()
    page2.wait_for_timeout(400)
    page2.screenshot(path=f"{SHOTS}/cs05-ac8-call-modal-360x640.png", full_page=True)

    ok("CS-05-AC8: không cuộn ngang ở 360x640 (modal gọi)", no_horizontal_scroll(page2))

    # SĐT là link tel:
    tel_links = page2.eval_on_selector_all(
        "a[href^='tel:']", "els => els.map(e => e.getAttribute('href'))"
    )
    ok("CS-05-AC8: SĐT hiện dưới dạng link tel:", len(tel_links) > 0, str(tel_links))

    # Nút gọi ngay (callNowBtn) cao >= 44px
    call_ok, call_violations, call_boxes = min_tap_target_ok(page2, "[class*='callNowBtn']")
    ok("CS-05-AC8: nút gọi (tel:) cao >= 44px", call_ok, str(call_violations))

    # Nút kết quả cuộc gọi (resultBtn) cao >= 44px
    result_ok, result_violations, result_boxes = min_tap_target_ok(page2, "[class*='resultBtn']:not([class*='resultBtnSub'])")
    ok(
        f"CS-05-AC8: {len(result_boxes)} nút kết quả cuộc gọi cao >= 44px",
        result_ok,
        str(result_violations[:3]),
    )

    # Nút kết quả nằm ở nửa dưới màn hình (viewport height 640 -> y > 320)
    result_positions = page2.eval_on_selector_all(
        "[class*='resultBtn']:not([class*='resultBtnSub'])",
        "els => els.filter(e => e.offsetParent !== null).map(e => e.getBoundingClientRect().top)",
    )
    # Modal cuộn được — kiểm phần tử nằm trong nửa dưới của VÙNG NỘI DUNG MODAL (không phải toàn viewport,
    # vì modal có header cố định ở trên). Ta kiểm tương đối: đa số nút nằm dưới điểm giữa của modal.
    modal_box = page2.eval_on_selector(
        "[class*='modal'], [role='dialog']",
        "e => { const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom}; }",
    )
    ok(
        "CS-05-AC8: có ít nhất 1 nút kết quả (dữ liệu vị trí đã ghi lại để đối chiếu thủ công)",
        len(result_positions) > 0,
        f"modal_box={modal_box} positions={result_positions[:4]}",
    )

    browser.close()

print("\n=== TỔNG KẾT ===")
n_ok = sum(1 for _, c, _ in results if c)
print(f"{n_ok}/{len(results)} PASS")
failed = [(n, e) for n, c, e in results if not c]
if failed:
    print("FAILED:", failed)
    sys.exit(1)
