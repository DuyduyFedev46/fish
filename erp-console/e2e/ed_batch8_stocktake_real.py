"""ED-28 trên BE thật (Django 8140 + ERP build MOCK=0 ở 3202). Chạy tay, không nằm trong bộ mock.
Dựng: xem mục "## Lô 8 — FE" ở 03-dev-notes.md. Biến: BASE (mặc định http://127.0.0.1:3202), SHOTS."""
import os, re, sys
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3202")
SHOTS = os.environ.get("SHOTS", "/tmp/real8/shots")
os.makedirs(SHOTS, exist_ok=True)
results = []


def ok(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")


def login(page, user):
    page.goto(BASE + "/login/")
    page.evaluate("() => localStorage.clear()")
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15_000)
    page.wait_for_load_state("networkidle")


def row(page, batch):
    return page.locator(f"li[data-line-row][data-batch='{batch}']")


def fill(page, batch, value, reason=None):
    r = row(page, batch)
    r.locator("input[data-counted]").fill(value)
    if reason is not None:
        r.locator("input[data-reason]").fill(reason)


with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    errors = []

    def new(user, w=1280, h=860):
        ctx = br.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
        pg = ctx.new_page()
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        login(pg, user)
        return pg

    # 1. Nhân viên kho lập phiếu
    page = new("kho1")
    page.goto(BASE + "/stocktake/new/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    page.wait_for_selector("li[data-line-row]")
    ok("BE thật: form liệt kê 7 lô của Kho chính", page.locator("li[data-line-row]").count() == 7, str(page.locator("li[data-line-row]").count()))
    fill(page, 1, "17,5")
    fill(page, 2, "38", "Cân lại thấy dư")
    fill(page, 3, "28")
    page.get_by_role("button", name="Lưu nháp").click()
    page.wait_for_url("**/stocktake/edit/**", timeout=15_000)
    ok("BE thật: lưu nháp nhảy sang trang sửa, URL chỉ mang ?id=", re.search(r"/stocktake/edit/\?id=\d+$", page.url) is not None, page.url)
    rec_id = re.search(r"id=(\d+)", page.url).group(1)
    page.wait_for_selector("li[data-line-row]")
    ok("BE thật: lưu nháp lần đầu ở lại form với đủ 7 dòng (lô chưa có số vẫn còn, không mất lý do đang gõ)", page.locator("li[data-line-row]").count() == 7, str(page.locator("li[data-line-row]").count()))
    page.goto(BASE + f"/stocktake/edit/?id={rec_id}")
    page.wait_for_selector("li[data-line-row]")
    ok("BE thật: mở lại trang sửa từ máy chủ đúng 3 dòng đã đếm", page.locator("li[data-line-row]").count() == 3, str(page.locator("li[data-line-row]").count()))
    ok("BE thật: số đếm lô 1 vẫn 17,5", row(page, 1).locator("input[data-counted]").input_value() in ("17,5", "17.5"), row(page, 1).locator("input[data-counted]").input_value())

    # 2. Sửa: lô 3 hụt 0,5, thêm lô 4 khớp
    fill(page, 3, "27,5")
    ok("BE thật: sửa chưa hiện lô 4 (chỉ lô đã lưu)", row(page, 4).count() == 0)
    page.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    row(page, 4).wait_for(timeout=15_000)
    ok("BE thật: chọn lại kho nạp thêm lô, số đã nhập giữ nguyên", row(page, 3).locator("input[data-counted]").input_value() in ("27,5", "27.5"))
    fill(page, 4, "25")
    page.get_by_role("button", name="Lưu nháp").click()
    page.wait_for_load_state("networkidle")
    page.screenshot(path=f"{SHOTS}/real-edit-1280.png")
    page.get_by_role("button", name="Gửi duyệt").click()
    page.wait_for_timeout(600)
    ok("BE thật: còn lô chưa đếm thì Gửi duyệt không đi tiếp, ở lại trang sửa", "/stocktake/edit/" in page.url, page.url)
    ok("BE thật: dòng chưa đếm báo 'Nhập số đếm của lô này.'", page.get_by_text("Nhập số đếm của lô này.").count() == 3, str(page.get_by_text("Nhập số đếm của lô này.").count()))
    for b in (5, 6, 7):
        row(page, b).get_by_role("button", name=re.compile("Bỏ lô")).click()
    ok("BE thật: bỏ 3 lô chưa đếm, còn 4 dòng", page.locator("li[data-line-row]").count() == 4, str(page.locator("li[data-line-row]").count()))
    page.get_by_role("button", name="Gửi duyệt").click()
    page.wait_for_url("**/stocktake/detail/**", timeout=15_000)
    page.wait_for_selector("[data-totals], table", timeout=15_000)
    body = page.inner_text("body")
    ok("BE thật: chi tiết hiện trạng thái Chờ duyệt/Nháp và mã phiếu KK", re.search(r"KK-?\d", body) is not None, body[:300])
    ok("BE thật: NV kho không có nút Duyệt", page.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0)
    page.screenshot(path=f"{SHOTS}/real-detail-kho1-1280.png")
    detail_url = page.url

    # 3. Quản lý duyệt
    mgr = new("ql1")
    mgr.goto(detail_url)
    mgr.wait_for_load_state("networkidle")
    btn = mgr.get_by_role("button", name="Duyệt và điều chỉnh tồn")
    ok("BE thật: Quản lý (người khác) thấy nút Duyệt", btn.count() == 1)
    mgr.screenshot(path=f"{SHOTS}/real-detail-ql1-1280.png")
    btn.click()
    mgr.get_by_role("button", name="Duyệt phiếu").click()
    mgr.wait_for_function("() => !document.querySelector('[role=dialog]')", timeout=15_000)
    mgr.wait_for_load_state("networkidle")
    ok("BE thật: sau duyệt chip Đã duyệt, không còn nút Duyệt", mgr.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0 and mgr.locator(".stat-chip", has_text="Đã duyệt").count() >= 1)
    mgr.screenshot(path=f"{SHOTS}/real-detail-approved-1280.png")

    # 4. Phiếu 2: ql1 sửa số đếm rồi tự duyệt -> bị chặn; Chủ duyệt được
    page.goto(BASE + "/stocktake/new/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Kho cần đếm").select_option(label="Kho chính")
    page.wait_for_selector("li[data-line-row]")
    fill(page, 5, "60")
    page.get_by_role("button", name="Lưu nháp").click()
    page.wait_for_url("**/stocktake/edit/**", timeout=15_000)
    id2 = re.search(r"id=(\d+)", page.url).group(1)
    mgr.goto(BASE + f"/stocktake/edit/?id={id2}")
    mgr.wait_for_selector("li[data-line-row]")
    fill(mgr, 5, "59")
    mgr.get_by_role("button", name="Lưu nháp").click()
    mgr.wait_for_load_state("networkidle")
    mgr.goto(BASE + f"/stocktake/detail/?id={id2}")
    mgr.wait_for_load_state("networkidle")
    ok("BE thật: người đã sửa số đếm không có nút Duyệt chính", mgr.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 0)
    mgr.get_by_role("button", name="Thao tác khác").click()
    mt = mgr.inner_text("body")
    ok("BE thật: menu … có mục Duyệt bị chặn kèm lý do", "Duyệt và điều chỉnh tồn" in mt)
    mgr.screenshot(path=f"{SHOTS}/real-detail-blocked-1280.png")
    mgr.keyboard.press("Escape")
    owner = new("loc")
    owner.goto(BASE + f"/stocktake/detail/?id={id2}")
    owner.wait_for_load_state("networkidle")
    ok("BE thật: Chủ (người khác) duyệt được", owner.get_by_role("button", name="Duyệt và điều chỉnh tồn").count() == 1)
    owner.get_by_role("button", name="Duyệt và điều chỉnh tồn").click()
    owner.get_by_role("button", name="Duyệt phiếu").click()
    owner.wait_for_function("() => !document.querySelector('[role=dialog]')", timeout=15_000)
    ok("BE thật: Chủ duyệt phiếu 2 thành công", owner.locator(".stat-chip", has_text="Đã duyệt").count() >= 1)

    # 5. Di động 360
    mob = new("kho1", 360, 740)
    mob.goto(BASE + "/stocktake/")
    mob.wait_for_load_state("networkidle")
    ok("BE thật 360px: danh sách không cuộn ngang", mob.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
    mob.screenshot(path=f"{SHOTS}/real-list-360.png")
    mob.goto(detail_url)
    mob.wait_for_load_state("networkidle")
    ok("BE thật 360px: chi tiết không cuộn ngang", mob.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
    mob.screenshot(path=f"{SHOTS}/real-detail-360.png")

    bad = [e for e in errors if not re.search(r"font|Failed to load resource.*(401|403|404)|Failed to fetch RSC payload", e)]
    ok("BE thật: không có console.error/pageerror (ngoài 401/403 chủ ý)", not bad, str(bad[:3]))
    br.close()

print(f"\n{sum(results)}/{len(results)} đạt; phiếu 1 id={rec_id}, phiếu 2 id={id2}")
sys.exit(0 if all(results) else 1)
