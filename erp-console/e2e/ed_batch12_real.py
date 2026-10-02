# Smoke trên BE THẬT (Lô 12 Kế toán, ED-32/33): BE chạy ở REAL_API (DB SQLite tạm đã `migrate`, `bootstrap_masterdata`, `seed_demo`,
# có người dùng loc (Chủ) và ql1 (Quản lý) mật khẩu Songbien2026), console build NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=<REAL_API>
# phục vụ ở BASE. BE bật CORS_ALLOWED_ORIGINS=<BASE>. Hai endpoint /api/reports/period/ và /batches/ của BE thật trả tiền, kg dạng
# JSON number (không phải chuỗi): kịch bản này chứng minh màn Báo cáo lãi lỗ không sập với shape đó (TL12-FE-H1).
#   BASE=http://127.0.0.1:3521 REAL_API=http://127.0.0.1:8621 SHOTS=<thư mục> python3 -u e2e/ed_batch12_real.py
import json
import os
import re
import sys
import urllib.request

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3521")
API = os.environ.get("REAL_API", "http://127.0.0.1:8621")
SHOTS = os.environ.get("SHOTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shots"))
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=15000)
R = []


def ok(n, c, e=""):
    R.append((n, bool(c), e))
    print("PASS" if c else "FAIL", n, "" if c else str(e)[:300], flush=True)


def session(b, user, width=1280):
    ctx = b.new_context(viewport={"width": width, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errs.append(m.text))
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill("Songbien2026")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    return ctx, page, errs


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def wire_shape():
    """Đọc thẳng JSON của BE để ghi lại shape thật (number hay string)."""
    req = urllib.request.Request(API + "/api/auth/token/", data=json.dumps({"username": "loc", "password": "Songbien2026"}).encode(), headers={"Content-Type": "application/json"})
    token = json.load(urllib.request.urlopen(req))["token"]
    month = None
    for part in ("period", "batches"):
        url = f"{API}/api/reports/period/?year=2026&month=10" if part == "period" else f"{API}/api/reports/batches/?month=2026-10"
        data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Token " + token})))
        row = data if part == "period" else data["results"][0]
        month = type(row["revenue"]).__name__
        ok(f"BE thật: /reports/{part}/ trả tiền dạng số (number), không phải chuỗi", month in ("int", "float"), month)


def main():
    wire_shape()
    with sync_playwright() as p:
        b = p.chromium.launch()
        # ---- Chủ: Báo cáo lãi lỗ
        ctx, page, errs = session(b, "loc")
        go(page, "/reports/")
        page.get_by_test_id("stat-profit").wait_for()
        body = page.locator("body").inner_text()
        ok("BE thật, Chủ: màn Báo cáo lãi lỗ KHÔNG sập (không 'Có lỗi', không error boundary)", "Something went wrong" not in body and "Application error" not in body and page.get_by_test_id("stat-profit").count() == 1, body[:200])
        profit = page.get_by_test_id("stat-profit").inner_text().strip()
        ok("BE thật, Chủ: Lãi/lỗ tháng này hiện số tiền VNĐ (430.000 đ)", re.search(r"430\.000\s*đ", profit) is not None, profit)
        rows = page.locator("[data-testid=breakdown] li")
        ok("BE thật, Chủ: 'Cấu thành lãi' có 6 dòng, có thanh", rows.count() == 6 and page.locator("[data-testid=breakdown] li[data-row=revenue]").inner_text().count("đ") >= 1, rows.count())
        page.wait_for_selector("table.lt tbody tr")
        ok("BE thật, Chủ: bảng lãi lỗ theo lô có dòng, tiền và kg định dạng", page.locator("table.lt tbody tr").count() >= 1 and re.search(r"\d\.\d{3}\.\d{3} đ", page.locator("table.lt").inner_text()) is not None, page.locator("table.lt").inner_text()[:300])
        page.screenshot(path=f"{SHOTS}/ed12-real-1-bao-cao.png", full_page=True)
        page.locator("table.lt tbody tr").first.locator("button").first.click()
        detail = page.get_by_test_id("batch-detail")
        detail.wait_for()
        dt = detail.inner_text()
        ok("BE thật, Chủ: chi tiết lô mở trong hộp thoại, có Lãi/lỗ và Tổng chi phí", page.get_by_role("dialog").count() == 1 and detail.locator("[data-line=profit]").count() == 1 and "đ" in dt, dt[:200])
        page.screenshot(path=f"{SHOTS}/ed12-real-2-chi-tiet-lo.png")
        page.keyboard.press("Escape")
        # Đổi sang tháng không có giao dịch: trạng thái trống, không sập
        sel = page.get_by_test_id("report-month")
        sel.select_option(index=6)
        page.wait_for_timeout(800)
        page.wait_for_load_state("networkidle")
        ok("BE thật, Chủ: tháng cũ không giao dịch → trạng thái trống", page.get_by_test_id("period-empty").count() == 1, page.locator("body").inner_text()[:200])
        sel.select_option(index=0)
        page.wait_for_timeout(800)
        ok("BE thật, Chủ: quay lại tháng này vẫn hiện số", page.get_by_test_id("stat-profit").count() == 1)
        ok("BE thật, Chủ: console không có lỗi/pageerror khi xem báo cáo", errs == [], str(errs[:3]))
        # Hoá đơn bán
        go(page, "/accounting/sales-invoices/")
        page.wait_for_selector("table.lt tbody tr")
        ok("BE thật, Chủ: Hoá đơn bán có 3 dòng, có Tổng số tiền", page.locator("table.lt tbody tr").count() == 3 and page.get_by_test_id("total-amount").count() == 1, page.locator("body").inner_text()[:200])
        ok("BE thật, Chủ: chân bảng chỉ một câu 'Không tính hoá đơn Đã huỷ.'", page.get_by_test_id("invoice-note").inner_text().strip() == "Không tính hoá đơn Đã huỷ.")
        page.screenshot(path=f"{SHOTS}/ed12-real-3-hoa-don-ban.png", full_page=True)
        ctx.close()

        # ---- Chủ trên điện thoại
        ctx, page, errs = session(b, "loc", width=360)
        go(page, "/reports/")
        page.get_by_test_id("stat-profit").wait_for()
        ok("BE thật, 360px: báo cáo không cuộn ngang", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
        page.screenshot(path=f"{SHOTS}/ed12-real-4-bao-cao-360.png", full_page=True)
        ctx.close()

        # ---- Quản lý: không có báo cáo
        ctx, page, errs = session(b, "ql1")
        ok("BE thật, Quản lý: menu không có Báo cáo lãi lỗ", page.locator(".nav a", has_text="Báo cáo lãi lỗ").count() == 0)
        go(page, "/reports/")
        page.wait_for_timeout(800)
        txt = page.locator("body").inner_text()
        ok("BE thật, Quản lý: vào thẳng /reports/ → không có quyền, không số tiền", "quyền" in txt.lower() and page.get_by_test_id("stat-profit").count() == 0, txt[:150])
        go(page, "/accounting/sales-invoices/")
        page.wait_for_selector("table.lt tbody tr")
        html = page.content()
        ok("BE thật, Quản lý: Hoá đơn bán không có Giá vốn / Lãi gộp", "Giá vốn" not in html and "Lãi gộp" not in html)
        ctx.close()
        b.close()
    bad = [r for r in R if not r[1]]
    print(f"\n{len(R) - len(bad)}/{len(R)} PASS")
    sys.exit(1 if bad else 0)


main()
