# E2E A2 (hồ sơ doc/features/2026-09-26-anh-mat-hang) trên BACKEND THẬT (Django), KHÔNG mock.
# Tái hiện B1 (04-qa-report.md lô 1, 2026-09-27): màn Danh mục console sập khi nối BE thật vì
# `listItems()` (features/catalog/api.ts) không bóc `results` khỏi trang phân trang DRF
# (`GET /api/catalog/items/` trả {count,next,previous,results}, không phải mảng trần như mock).
#
# Chuẩn bị (giống mẫu e2e/s41_s47_real.py):
#   1) Django:  DATABASE_URL=sqlite:////<tmp>/qa.sqlite3 ITEM_IMAGE_STORAGE=local \
#               CORS_ALLOWED_ORIGINS=http://localhost:3100 .venv/bin/python manage.py migrate
#               rồi bootstrap_masterdata, seed_demo, và tạo User + StaffProfile (must_change_password=False)
#               cho các Group owner/manager/warehouse_staff/delivery_staff (script mẫu ở scratchpad QA, không commit).
#               .venv/bin/python manage.py runserver 8000
#   2) Console: NEXT_PUBLIC_API_BASE=http://localhost:8000 NEXT_PUBLIC_USE_MOCK=0 npm run dev -- -p 3100
#   3) BASE=http://localhost:3100 API=http://localhost:8000 python3 e2e/a2_catalog_real.py
#
# Test này PHẢI ĐỎ cho tới khi B1 được sửa (listItems dùng đúng kiểu Paginated<CatalogItem> và
# trả `.results`, xem đề xuất sửa trong 04-qa-report.md).

import os

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:3100")
API = os.environ.get("API", "http://localhost:8000")
PW = os.environ.get("PW", "Test@12345")
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user, pw=PW):
    page.goto(BASE + "/login")
    page.wait_for_selector("#u", state="visible")
    page.fill("#u", user)
    page.fill("#p", pw)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def check_catalog_loads(browser, user, label):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page_errors = []
    # Next.js dev hiện lỗi runtime trong 1 shadow DOM (<nextjs-portal>) nên page.content()
    # KHÔNG thấy chữ "Unhandled Runtime Error" — phải bắt bằng sự kiện `pageerror` mới đáng tin.
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    login(page, user)
    page.goto(BASE + "/catalog")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(600)
    ok(f"A2 /catalog không ném lỗi runtime chưa bắt với tài khoản {label} (BE thật, không mock)",
       not page_errors, page_errors)
    if not page_errors:
        # Có danh sách mặt hàng thật (seed_demo tạo >=1 mặt hàng) thay vì màn trắng/vỡ.
        ok(f"[{label}] Danh sách mặt hàng render (có ít nhất 1 dòng)",
           page.locator("tbody tr").count() > 0)
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    check_catalog_loads(browser, "loc", "owner")
    check_catalog_loads(browser, "quanly1", "manager")
    check_catalog_loads(browser, "kho1", "warehouse_staff")
    browser.close()

print("\n=== SUMMARY A2 catalog (real BE) ===")
n_ok = sum(1 for _, c, _ in results if c)
for name, c, extra in results:
    print(("PASS" if c else "FAIL"), name, extra)
print(f"{n_ok}/{len(results)} pass")
if n_ok != len(results):
    raise SystemExit(1)
