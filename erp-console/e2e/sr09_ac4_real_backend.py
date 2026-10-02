# QA P8 Lô 3 — SR-09-AC4 với Django THẬT (không mock): mở màn gọi, chạy job tự huỷ ở backend, bấm "Đã xác nhận"
# -> BE trả 409 STALE_STATE -> màn hiện thông điệp + "Tải lại" -> bấm -> phiếu sang tab báo hoàn tiền. Dữ liệu giả.
# Giao diện ERP theo design (bảng + trang chi tiết + hộp F2h). Chuẩn bị (xem QA report Lô 3): Django SQLite tạm cổng 8113 (CSKH_AUTO_CANCEL_ENABLED=1, CORS 127.0.0.1:3214),
#   seed 1 phiếu ESCALATED (UNREACHABLE, escalated_at quá 31 phút; user cs1 pass demo1234), build erp-console với NEXT_PUBLIC_API_BASE=http://127.0.0.1:8113 USE_MOCK=0,
#   phục vụ thư mục out ở cổng 3214. Biến: BASE, SHOTS, TRIGGER_CMD (lệnh chạy job trong backend, shell; vd `python manage.py process_confirmation_deadlines`).
import json
import os
import re
import subprocess
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3214")
SHOTS = os.environ.get("SHOTS", "/tmp")
TRIGGER_CMD = os.environ["TRIGGER_CMD"]
DETAIL = "Đơn đã bị huỷ — tải lại màn hình."
PII = ("0900000555", "Khách Thử E", "Số 5 Đường Thử")
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def run_case(browser, tag, viewport, trigger):
    ctx = browser.new_context(viewport=viewport)
    page = ctx.new_page()
    logs, responses, urls = [], [], []
    page.on("console", lambda m: logs.append(m.text))
    page.on("framenavigated", lambda f: urls.append(f.url))
    page.on("response", lambda r: responses.append((r.request.method, r.url, r.status)) if "/api/" in r.url else None)
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", "cs1")
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")
    page.goto(BASE + "/confirmation/")
    page.wait_for_load_state("networkidle")
    # ERP theo design (ED-15): hàng chờ là bảng; phiếu ESCALATED nằm ở mục "Cần quyết định".
    page.get_by_role("tab", name=re.compile(r"^Cần quyết định")).click()
    row = page.locator("table.lt tbody tr")
    page.locator("table.lt tbody tr a").first.wait_for(timeout=10_000)  # chờ hết dòng khung xương
    ok(f"[{tag}] hàng chờ thật mục Cần quyết định có 1 phiếu", row.count() == 1, f"count={row.count()}")
    code = row.first.locator("td").first.inner_text().strip()
    # Bấm dòng (cả dòng là vùng bấm) mở trang chi tiết; "Ghi kết quả gọi" mở hộp F2h.
    row.first.locator("a").first.click()
    page.get_by_role("heading", name=code).wait_for(timeout=10_000)
    page.get_by_role("button", name="Ghi kết quả gọi").click()
    modal = page.get_by_role("dialog")
    modal.get_by_text("Đã xác nhận", exact=False).first.wait_for(timeout=10_000)
    page.wait_for_timeout(500)
    ok(f"[{tag}] chưa có cảnh báo stale trước khi bấm", modal.get_by_role("alert").count() == 0)

    if trigger:
        out = subprocess.run(TRIGGER_CMD, shell=True, capture_output=True, text=True).stdout
        print("   backend:", [l for l in out.splitlines() if "tự huỷ" in l])
        ok(f"[{tag}] job tự huỷ ở backend đã huỷ 1 đơn", "tự huỷ 1 đơn" in out or "'cancelled': 1" in out, out.strip()[-160:])

    responses.clear()
    modal.locator("label", has_text="Đã xác nhận").first.click()
    modal.get_by_role("button", name="Lưu kết quả").click()
    alert = modal.get_by_role("alert").first
    alert.wait_for(timeout=10_000)
    post = [r for r in responses if r[0] == "POST" and "/calls/" in r[1]]
    ok(f"[{tag}] BE thật trả 409 cho POST /calls/", post and post[-1][2] == 409, str(post))
    ok(f"[{tag}] chỉ gửi 1 POST (không gửi lại)", len(post) == 1, str(len(post)))
    ok(f"[{tag}] hiện đúng thông điệp `detail` của BE", DETAIL in alert.inner_text(), alert.inner_text().replace("\n", " | "))
    ok(f"[{tag}] các lựa chọn kết quả bị khoá", modal.locator("input[type=radio]").first.is_disabled())
    page.screenshot(path=f"{SHOTS}/real-{tag}-1-409.png")
    modal.get_by_role("button", name="Tải lại").click()
    page.wait_for_timeout(800)
    page.wait_for_load_state("networkidle")
    ok(f"[{tag}] bấm Tải lại: hộp đóng", page.get_by_role("dialog").count() == 0)
    ok(f"[{tag}] bấm Tải lại: chi tiết nạp lại, phiếu sang Gọi báo hoàn tiền", page.get_by_role("heading", name=code).is_visible() and page.get_by_text("Gọi báo hoàn tiền", exact=False).count() >= 1)
    page.goto(BASE + "/confirmation/")
    page.wait_for_load_state("networkidle")
    page.get_by_role("tab", name=re.compile(r"^Gọi báo hoàn tiền")).click()
    page.wait_for_timeout(800)
    ok(f"[{tag}] phiếu nằm ở mục Gọi báo hoàn tiền (REFUND_CALL)", page.locator("table.lt tbody tr", has_text=code).count() == 1)
    page.screenshot(path=f"{SHOTS}/real-{tag}-2-refund-tab.png")
    ls = page.evaluate("() => JSON.stringify(Object.assign({}, window.localStorage)) + JSON.stringify(Object.assign({}, window.sessionStorage))")
    blob_logs = "\n".join(logs)
    ok(f"[{tag}] console/URL/localStorage không chứa SĐT/tên/địa chỉ khách",
       not any(s in blob_logs or s in ls or any(s in u for u in urls) for s in PII))
    ctx.close()


if __name__ == "__main__":
    with sync_playwright() as p:
        b = p.chromium.launch()
        run_case(b, "desktop-1280", {"width": 1280, "height": 800}, True)
        b.close()
    bad = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(bad)}/{len(results)} PASS")
    sys.exit(1 if bad else 0)
