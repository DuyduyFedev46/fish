# Lô 7 FE — kịch bản 1 trên Django THẬT (SQLite tạm + seed_demo), build USE_MOCK=0.
#   BASE=http://127.0.0.1:3302 (static) · API=http://127.0.0.1:8113 · loc / Songbien2026 · SHOTS=<thư mục ảnh>
#   Django: DJANGO_DEBUG=1 DATABASE_URL=sqlite:///<tmp> migrate + bootstrap_masterdata + seed_demo + tạo loc (owner)
#   CORS_ALLOWED_ORIGINS=$BASE runserver 127.0.0.1:8113 --noreload
# Dữ liệu giả. Chủ: Kho & lô -> mở 1 lô -> phần Sổ nhập xuất có Tồn sau -> Sổ nhập xuất toàn kho -> Kho -> không lỗi console.
import os
import re

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3302")
SHOTS = os.environ.get("SHOTS", "/tmp")
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1366, "height": 800}, reduced_motion="reduce")
    page = ctx.new_page()
    logs, bad = [], []
    page.on("console", lambda m: logs.append(m.text) if m.type == "error" else None)
    page.on("response", lambda r: bad.append((r.url, r.status)) if "/api/" in r.url and r.status >= 400 else None)
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", "loc")
    page.fill("#p", "Songbien2026")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15_000)
    page.wait_for_load_state("networkidle")
    page.goto(BASE + "/inventory/")
    page.wait_for_load_state("networkidle")
    page.locator("table.lt tbody tr:not(.lt-skel)").first.wait_for(timeout=15_000)
    n = page.locator("table.lt tbody tr:not(.lt-skel)").count()
    ok("Kho & lô thật: có dòng lô từ seed_demo", n >= 5, str(n))
    heads = [h.strip() for h in page.locator("table.lt thead th").all_inner_texts()]
    ok("Chủ thấy cột giá vốn", any("vốn" in h.lower() for h in heads), str(heads))
    page.screenshot(path=f"{SHOTS}/ed7-real-1-kho-lo.png")
    page.locator("table.lt tbody tr:not(.lt-skel) td a").first.click()
    page.wait_for_url(re.compile(r"/inventory/detail/\?id=\d+"), timeout=10_000)
    page.get_by_text("Tồn sau").first.wait_for(timeout=15_000)
    ok("Chi tiết lô thật: có Sổ nhập xuất với Tồn sau", page.get_by_text("Tồn sau").count() >= 1)
    ok("Chi tiết lô thật: không rơi vào 404/lỗi", page.get_by_text("Không tìm thấy trang này").count() == 0 and page.get_by_text("Không tải được").count() == 0)
    page.screenshot(path=f"{SHOTS}/ed7-real-2-chi-tiet-lo.png", full_page=True)
    page.goto(BASE + "/ledger/")
    page.wait_for_load_state("networkidle")
    page.locator("table.lt tbody tr:not(.lt-skel)").first.wait_for(timeout=15_000)
    ok("Sổ nhập xuất thật: có dòng", page.locator("table.lt tbody tr:not(.lt-skel)").count() >= 1)
    ok("Sổ nhập xuất thật: có 'Đang hiện'", page.get_by_text(re.compile(r"Đang hiện \d+")).count() >= 1)
    page.screenshot(path=f"{SHOTS}/ed7-real-3-so-nhap-xuat.png")
    page.goto(BASE + "/inventory/?tab=warehouses")
    page.wait_for_load_state("networkidle")
    page.get_by_text("Kho chính").first.wait_for(timeout=15_000)
    ok("Tab Kho thật: có Kho chính", True)
    # BE hiện chưa có GET /api/ai/status/ (cổng Trợ lý AI dùng chung, Lô 2) -> 404 đã biết, ghi ở dev-notes; ngoài lỗi đó thì sạch.
    other = [x for x in bad if "/api/ai/status/" not in x[0]]
    ok("Không có lỗi API (ngoài ai/status đã biết)", not other, str(other))
    ok("Console chỉ có lỗi 404 của ai/status", len(logs) == len(bad) and not other, str(logs[:3]))
    b.close()
bads = [r for r in results if not r[1]]
print(f"\n{len(results) - len(bads)}/{len(results)} PASS")
raise SystemExit(1 if bads else 0)
