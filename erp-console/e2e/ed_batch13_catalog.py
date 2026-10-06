# E2E ERP theo design Lô 13 (Danh mục & giá, ED-30 / ED-31): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3701 --bind 127.0.0.1 &)
#   BASE=http://127.0.0.1:3701 SHOTS=<thư mục ảnh> python3 e2e/ed_batch13_catalog.py      # tắt server sau khi xong
# Trạng thái mock nằm trong bộ nhớ trang: page.goto làm về seed, nên luồng ghi đi bằng bấm menu / tab / dòng, không gõ URL.
# Kiểm: loc (Chủ) đủ 4 tab + thêm/sửa/đặt giá · ql1 chỉ xem (có giá, không có nút ghi) · kho1 chỉ tab Mặt hàng, KHÔNG có giá ·
# giao1 / cs2 không có menu, vào thẳng thì "không có quyền" · đường sai: giá đã có đơn dùng (quyết định #10), lùi ngày, mã trùng,
# tên nhóm trùng, phần trăm > 100, lỗi 500 / rỗng / 403 / lưu lỗi · 360px và 1280px · không rò dữ liệu ra storage hay URL.
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3701")
SHOTS = os.environ.get("SHOTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shots"))
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)

VN = timezone(timedelta(hours=7))
TODAY = datetime.now(VN).date()
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
TOMORROW_ISO = (TODAY + timedelta(days=1)).isoformat()
TOMORROW_VN = (TODAY + timedelta(days=1)).strftime("%d/%m/%Y")

SMALL_TAPS_JS = """() => [...document.querySelectorAll('button, a, input, select')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y < innerHeight
      && !e.classList.contains('sr-only') && !e.classList.contains('lt-link') && !e.matches('input[type=checkbox]') && (r.height < 44 || (!['INPUT', 'SELECT'].includes(e.tagName) && r.width < 44));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""

PHONE = re.compile(r"\b0\d{9}\b")
USED_DETAIL = "Giá này đã áp vào đơn hàng, không sửa được."
ITEM_HEADS = ["Mặt hàng", "Mã hàng", "Nhóm", "Giá niêm yết", "Áp dụng từ", "Hạn dùng", "Trạng thái", "Ảnh"]
ITEM_HEADS_NO_PRICE = ["Mặt hàng", "Mã hàng", "Nhóm", "Hạn dùng", "Trạng thái", "Ảnh"]


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra if not cond else "")


def new_page(browser, user, w=1366, h=900, mobile=False, errors=None):
    opts = {"viewport": {"width": w, "height": h}, "reduced_motion": "reduce"}
    if mobile:
        opts.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**opts)
    page = ctx.new_page()
    if errors is not None:
        page.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and "Failed to load resource" not in m.text and errors.append(f"[{user}] {m.text}"))
        page.on("pageerror", lambda e: errors.append(f"[{user}] {e}"))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")
    return ctx, page


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)
    page.wait_for_timeout(120)


def body(page):
    return page.locator("body").inner_text()


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def set_mode(page, mode):
    page.evaluate("(m) => window.__caveMock.catalog(m)", mode)


def wait_table(page):
    t = page.locator("table.lt").first
    expect(t.locator("tbody tr").first).to_be_visible()
    expect(t.locator("tr.lt-skel")).to_have_count(0)
    return t


def goto_catalog(page, soft=True):
    """Vào màn: bấm menu nếu có (giữ trạng thái mock), nếu không (điện thoại) gõ URL."""
    link = page.locator(".nav a", has_text="Danh mục & giá").first
    if soft and link.count() and link.is_visible():
        link.click()
    else:
        page.goto(BASE + "/catalog/")
    page.wait_for_url("**/catalog/**")
    return wait_table(page)


def heads(t):
    return [re.sub(r"\s+", " ", h).split(" lock")[0].split("lock")[0].strip() for h in t.locator("thead th").all_inner_texts()]


def tab(page, name):
    page.get_by_role("tab", name=name).click()
    return wait_table(page)


def open_item(page, name):
    t = page.locator("table.lt").first
    t.locator("tbody tr", has_text=name).first.locator("a").first.click()
    page.wait_for_url("**/catalog/detail/**")
    page.wait_for_selector("#item-detail", timeout=10_000)
    settle(page)


def more_items(page):
    page.get_by_role("button", name="Thao tác khác").click()
    return [re.sub(r"\s+", " ", x).strip() for x in page.get_by_role("menuitem").all_inner_texts()]


def pick_more(page, label):
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^" + re.escape(label))).click()


def storage_dump(page):
    # Bỏ kho tài khoản mock của module đăng nhập (số điện thoại giả của nhân viên mẫu, có từ trước Lô 13, không thuộc Danh mục).
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage).filter(([k]) => k !== 'cave_erp_mock_users'), Object.entries(sessionStorage), location.href])")


def personal_clean(page, extra=()):
    dump = storage_dump(page)
    bad = [x for x in extra if x in dump]
    return not bad and not PHONE.search(dump), str(bad)


def section_rows(page, label):
    return page.locator(f"section[aria-label='{label}'] table.lt tbody tr")


# ---------------------------------------------------------------- Chủ (loc)
def run_owner(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    t = goto_catalog(page)
    tabs = [x.strip() for x in page.get_by_role("tab").all_inner_texts()]
    ok("Chủ: có đủ 4 tab", tabs == ["Mặt hàng", "Bảng giá", "Ưu đãi", "Nhóm hàng"], str(tabs))
    h = heads(t)
    ok("Chủ: cột mặt hàng đủ ED-30 (một giá trị mỗi ô)", h == ITEM_HEADS, str(h))
    ok("Chủ: 'Đang hiện 8 / 11 mặt hàng' + nút Tải thêm", page.get_by_text("Đang hiện 8 / 11 mặt hàng").is_visible() and page.get_by_role("button", name="Tải thêm").count() == 1)
    ok("Chủ: có 'Thêm mặt hàng' và 'Thêm combo'", page.get_by_role("link", name="Thêm mặt hàng").count() >= 1 and page.get_by_role("link", name="Thêm combo").count() == 1)
    ok("Chủ: không có chữ giá vốn / mã BR trên màn", "Giá vốn" not in body(page) and not re.search(r"BR-[A-Z]+-\d+", body(page)))
    row = [c.strip() for c in t.locator("tbody tr", has_text="Cá thu cắt khúc").first.locator("td").all_inner_texts()]
    ok("Chủ: Cá thu hiện giá niêm yết 220.000", any("220.000" in c for c in row), str(row))
    page.screenshot(path=f"{SHOTS}/lo13-loc-1-mat-hang.png")
    page.get_by_role("button", name="Tải thêm").click()
    expect(t.locator("tbody tr")).to_have_count(11)
    ok("Chủ: Tải thêm → 11 dòng", page.get_by_role("button", name="Tải thêm").count() == 0)

    # Lọc + tìm
    page.get_by_role("searchbox").or_(page.get_by_placeholder("Tìm tên, mã mặt hàng…")).first.fill("tom")
    expect(t.locator("tbody tr")).to_have_count(2)
    ok("Tìm 'tom' (không dấu) → Tôm sú + Tôm thẻ", "Tôm sú" in t.inner_text() and "Tôm thẻ" in t.inner_text())
    page.get_by_role("button", name="Xoá tìm kiếm").first.click()
    expect(t.locator("tbody tr")).to_have_count(11)
    page.get_by_label("Loại", exact=True).select_option(label="Combo")
    expect(t.locator("tbody tr")).to_have_count(1)
    ok("Lọc loại Combo → Combo lẩu hải sản", "Combo lẩu hải sản" in t.inner_text())
    page.get_by_label("Loại", exact=True).select_option(label="Mọi loại")
    page.get_by_label("Trạng thái", exact=True).select_option(label="Đang ẩn")
    expect(t.locator("tbody tr")).to_have_count(1)
    ok("Lọc Đang ẩn → Ghẹ biển", "Ghẹ biển" in t.inner_text())
    page.get_by_label("Nhóm hàng", exact=True).select_option(label="Cá")
    expect(page.get_by_text("Không có mặt hàng nào khớp")).to_be_visible()
    ok("Lọc nhóm + trạng thái không khớp → rỗng có gợi ý bỏ lọc", page.get_by_text("Bỏ bớt bộ lọc để xem toàn bộ danh mục.").is_visible())
    page.get_by_label("Trạng thái", exact=True).select_option(label="Mọi trạng thái")
    page.get_by_label("Nhóm hàng", exact=True).select_option(label="Mọi nhóm")
    expect(t.locator("tbody tr").first).to_be_visible()

    # --- Chi tiết + đặt giá (quyết định #10)
    open_item(page, "Cá thu cắt khúc")
    ok("Chi tiết: tiêu đề + chip Đang kinh doanh", page.locator("main h2").first.inner_text().strip() == "Cá thu cắt khúc" and page.get_by_text("Đang kinh doanh").first.is_visible())
    ok("Chi tiết: Thông tin + Giá niêm yết 220.000 + Lịch sử giá", "thông tin mặt hàng" in body(page).lower() and "220.000" in body(page) and page.locator("section[aria-label='Lịch sử giá']").count() == 1)
    ok("Chi tiết: lịch sử giá có 2 dòng (giá cũ đã đóng + giá hiện tại)", section_rows(page, "Lịch sử giá").count() == 2, str(section_rows(page, "Lịch sử giá").count()))
    ok("Chi tiết: không có giá vốn", "Giá vốn" not in body(page))
    items = more_items(page)
    ok("Chi tiết: menu '…' có Ẩn khỏi Shop + Xem dòng thời gian (không Xoá)", any(i.startswith("Ẩn khỏi Shop") for i in items) and any(i.startswith("Xem dòng thời gian") for i in items) and not any("Xoá" in i for i in items), str(items))
    page.keyboard.press("Escape")
    page.screenshot(path=f"{SHOTS}/lo13-loc-2-chi-tiet.png", full_page=True)

    page.get_by_role("button", name="Đặt giá mới").first.click()
    dlg = page.get_by_role("dialog", name="Đặt giá mới")
    expect(dlg).to_be_visible()
    ok("Đặt giá: 'Áp dụng từ' mặc định là NGÀY MAI", dlg.get_by_label(re.compile("^Áp dụng từ")).input_value() == TOMORROW_ISO, dlg.get_by_label(re.compile("^Áp dụng từ")).input_value())
    ok("Đặt giá: hiện giá đang áp dụng, không có ô giá vốn", "Giá đang áp dụng" in dlg.inner_text() and "Giá vốn" not in dlg.inner_text())
    dlg.get_by_role("button", name="Lưu giá mới").click()
    ok("Đặt giá: để trống giá → 'Nhập giá bán.', hộp còn mở", dlg.is_visible() and dlg.get_by_text("Nhập giá bán.").count() >= 1)
    dlg.get_by_label(re.compile("^Giá bán")).fill("0")
    dlg.get_by_role("button", name="Lưu giá mới").click()
    ok("Đặt giá: giá 0 → báo phải lớn hơn 0", dlg.get_by_text(re.compile("Giá bán phải lớn hơn 0")).count() >= 1)
    dlg.get_by_label(re.compile("^Giá bán")).fill("230000")
    dlg.get_by_label(re.compile("^Áp dụng từ")).fill(YESTERDAY)
    dlg.get_by_role("button", name="Lưu giá mới").click()
    ok("Đặt giá: lùi ngày (hôm qua) → CHẶN ngay trên form, gợi ý 'từ ngày mai'", dlg.is_visible() and dlg.get_by_text(re.compile("Chọn từ ngày mai")).count() >= 1 and TOMORROW_VN in dlg.inner_text(), dlg.inner_text()[:200])
    ok("Đặt giá: lùi ngày không gọi máy chủ (giá chưa có dòng mới)", section_rows(page, "Lịch sử giá").count() == 2)
    dlg.get_by_label(re.compile("^Áp dụng từ")).fill(TOMORROW_ISO)
    dlg.get_by_label(re.compile("^Áp dụng đến")).fill(TOMORROW_ISO)
    dlg.get_by_label(re.compile("^Áp dụng đến")).fill(YESTERDAY)
    dlg.get_by_role("button", name="Lưu giá mới").click()
    ok("Đặt giá: ngày kết thúc trước ngày bắt đầu → báo lỗi dưới ô", dlg.is_visible() and dlg.get_by_text(re.compile("Ngày kết thúc phải sau hoặc bằng ngày bắt đầu")).count() >= 1)
    dlg.get_by_label(re.compile("^Áp dụng đến")).fill("")
    dlg.get_by_role("button", name=re.compile("^(Lưu giá mới|Thử lại)")).click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã đặt giá mới.")).to_be_visible()
    settle(page)
    ok("Đặt giá: hàng mới vào lịch sử giá (3 dòng)", section_rows(page, "Lịch sử giá").count() == 3 and "230.000" in page.locator("section[aria-label='Lịch sử giá']").inner_text(), str(section_rows(page, "Lịch sử giá").count()))
    ok("Đặt giá: giá đang áp dụng hôm nay KHÔNG đổi (giá mới từ ngày mai)", "220.000" in page.locator("main").inner_text())
    expect(page.locator("#item-timeline")).to_contain_text("Đặt giá")
    ok("Đặt giá: dòng thời gian ghi lại việc đặt giá", "Đặt giá" in page.locator("#item-timeline").inner_text())

    # --- Giá đã có đơn dùng (BE PRICE_USED_BY_ORDERS)
    set_mode(page, "priceUsed")
    page.get_by_role("button", name="Đặt giá mới").first.click()
    dlg = page.get_by_role("dialog", name="Đặt giá mới")
    dlg.get_by_label(re.compile("^Giá bán")).fill("240000")
    dlg.get_by_label(re.compile("^Áp dụng từ")).fill((TODAY + timedelta(days=2)).isoformat())
    dlg.get_by_role("button", name="Lưu giá mới").click()
    expect(dlg.get_by_text(re.compile(USED_DETAIL))).to_be_visible()
    ok("Giá đã có đơn dùng: hiện NGUYÊN VĂN câu của máy chủ, hộp còn mở", dlg.is_visible() and dlg.get_by_text(re.compile(USED_DETAIL)).count() == 1)
    ok("Giá đã có đơn dùng: giữ nguyên giá đã nhập, nút chính 'Thử lại'", dlg.get_by_label(re.compile("^Giá bán")).input_value().replace(".", "").replace(",", "").replace(" ", "").startswith("240000") and dlg.get_by_role("button", name=re.compile("Thử lại")).count() == 1)
    ok("Giá đã có đơn dùng: không lộ mã PRICE_USED_BY_ORDERS", "PRICE_USED_BY_ORDERS" not in dlg.inner_text())
    page.screenshot(path=f"{SHOTS}/lo13-loc-3-gia-da-co-don.png")
    dlg.get_by_role("button", name="Huỷ").click()
    dlg.wait_for(state="detached")
    set_mode(page, "ok")

    # --- Sửa tại chỗ + ẩn/hiện
    page.get_by_role("button", name="Sửa tên mặt hàng").click()
    page.get_by_label("Tên mặt hàng").first.fill("")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    ok("Sửa tên: để trống → 'Nhập tên mặt hàng.'", page.get_by_text("Nhập tên mặt hàng.").count() >= 1)
    page.get_by_label("Tên mặt hàng").first.fill("Cá thu cắt khúc loại 1")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    expect(page.get_by_text("Đã lưu thay đổi.")).to_be_visible()
    expect(page.locator("main h2").first).to_have_text("Cá thu cắt khúc loại 1")
    ok("Sửa tên tại chỗ: tiêu đề đổi", True)
    pick_more(page, "Ẩn khỏi Shop")
    expect(page.get_by_text("Đã ẩn khỏi Shop.")).to_be_visible()
    expect(page.get_by_text("Đang ẩn").first).to_be_visible()
    ok("Ẩn khỏi Shop: chip đổi 'Đang ẩn', menu có 'Hiện lại trên Shop'", any(i.startswith("Hiện lại trên Shop") for i in more_items(page)))
    page.keyboard.press("Escape")
    pick_more(page, "Hiện lại trên Shop")
    expect(page.get_by_text("Đã hiện lại trên Shop.")).to_be_visible()
    expect(page.get_by_text("Đang kinh doanh").first).to_be_visible()
    ok("Hiện lại trên Shop: trở về Đang kinh doanh", page.get_by_text("Đang ẩn").count() == 0 or not page.get_by_text("Đang ẩn").first.is_visible())

    # Combo: bảng thành phần
    page.get_by_role("link", name="Danh mục & giá").first.click()
    wait_table(page)
    open_item(page, "Combo lẩu hải sản")
    ok("Combo: có bảng 'Thành phần' 3 dòng, không có giá vốn", section_rows(page, "Thành phần").count() == 3 and "Giá vốn" not in body(page), str(section_rows(page, "Thành phần").count()))
    page.screenshot(path=f"{SHOTS}/lo13-loc-4-combo.png", full_page=True)

    # --- Thêm mặt hàng
    page.get_by_role("link", name="Danh mục & giá").first.click()
    wait_table(page)
    page.get_by_role("link", name="Thêm mặt hàng").first.click()
    page.wait_for_url("**/catalog/new/**")
    page.get_by_label(re.compile("^Mã hàng")).wait_for()
    page.get_by_role("button", name="Lưu mặt hàng").click()
    ok("Thêm mặt hàng: để trống → báo lỗi dưới ô, không rời trang", page.get_by_text("Nhập mã hàng.").count() >= 1 and "/catalog/new" in page.url)
    page.get_by_label(re.compile("^Mã hàng")).fill("ca-thu")
    page.get_by_label(re.compile("^Tên mặt hàng")).fill("Cá thu thử")
    page.get_by_label(re.compile("^Nhóm hàng")).select_option(label="Cá")
    page.get_by_role("button", name="Lưu mặt hàng").click()
    expect(page.get_by_text(re.compile("Mã này đã được dùng"))).to_be_visible()
    ok("Thêm mặt hàng: mã trùng (khác hoa thường) → báo dưới ô Mã, giữ chữ đã gõ", page.get_by_label(re.compile("^Tên mặt hàng")).input_value() == "Cá thu thử" and "/catalog/new" in page.url)
    ok("Thêm mặt hàng: nút chính đổi 'Thử lại' sau lỗi", page.get_by_role("button", name=re.compile("Thử lại")).count() >= 1)
    page.screenshot(path=f"{SHOTS}/lo13-loc-5-ma-trung.png")
    page.get_by_label(re.compile("^Mã hàng")).fill("CA-THU-2")
    page.get_by_role("button", name=re.compile("^(Lưu mặt hàng|Thử lại)")).click()
    page.wait_for_url("**/catalog/detail/**")
    page.wait_for_selector("#item-detail", timeout=10_000)
    ok("Thêm mặt hàng: lưu xong sang chi tiết, có toast", page.locator("main h2").first.inner_text().strip() == "Cá thu thử")

    # --- Thêm combo
    page.get_by_role("link", name="Danh mục & giá").first.click()
    wait_table(page)
    page.get_by_role("link", name="Thêm combo").click()
    page.wait_for_url("**/catalog/new/**")
    page.get_by_label(re.compile("^Mã hàng")).wait_for()
    ok("Thêm combo: có khối Thành phần combo, không có ô Quản lý theo lô", page.get_by_text("Thành phần combo").count() >= 1 and page.get_by_text("Quản lý theo lô").count() == 0)
    page.get_by_label(re.compile("^Mã hàng")).fill("COMBO-NHAU")
    page.get_by_label(re.compile("^Tên mặt hàng")).fill("Combo nhậu")
    page.get_by_label(re.compile("^Nhóm hàng")).select_option(label="Combo")
    page.get_by_role("button", name="Lưu combo").click()
    # B13-1 (ED-30-AC3): dòng công thức còn trống hoàn toàn = chưa có dòng nào → báo ở vùng công thức, không báo dưới dòng trống.
    ok("Thêm combo: công thức còn trống → hiện 'Thêm ít nhất một mặt hàng vào công thức.'", page.get_by_text("Thêm ít nhất một mặt hàng vào công thức.").count() == 1)
    ok("Thêm combo: công thức trống → không báo 'Chọn mặt hàng.' / 'Nhập số kg.' dưới dòng trống", page.get_by_text("Chọn mặt hàng.").count() == 0 and page.get_by_text("Nhập số kg.").count() == 0)
    ok("Thêm combo: công thức trống → ở lại form, không tạo", "/catalog/new" in page.url and page.get_by_role("button", name="Lưu combo").count() == 1)
    page.screenshot(path=f"{SHOTS}/lo13-loc-4f-combo-cong-thuc-trong.png", full_page=True)
    # Dòng đã chọn mặt hàng mà chưa nhập kg thì vẫn báo từng dòng như cũ.
    page.get_by_label(re.compile("^Thành phần")).first.select_option(label="Mực ống")
    page.get_by_role("button", name="Lưu combo").click()
    ok("Thêm combo: có mặt hàng, thiếu số kg → 'Nhập số kg.' dưới dòng, không còn câu công thức", page.get_by_text("Nhập số kg.").count() == 1 and page.get_by_text("Thêm ít nhất một mặt hàng vào công thức.").count() == 0 and "/catalog/new" in page.url)
    page.get_by_label(re.compile("^Thành phần")).first.select_option(label="Mực ống")
    page.get_by_label(re.compile("^Số kg mỗi combo")).first.fill("0.5")
    page.get_by_role("button", name="Thêm thành phần").click()
    page.get_by_label(re.compile("^Thành phần")).nth(1).select_option(label="Tôm thẻ")
    page.get_by_label(re.compile("^Số kg mỗi combo")).nth(1).fill("0.2")
    page.get_by_role("button", name=re.compile("^(Lưu combo|Thử lại)")).click()
    page.wait_for_url("**/catalog/detail/**")
    page.wait_for_selector("#item-detail", timeout=10_000)
    settle(page)
    ok("Thêm combo: sang chi tiết, bảng Thành phần có 2 dòng", section_rows(page, "Thành phần").count() == 2, str(section_rows(page, "Thành phần").count()))

    # --- Tab Bảng giá
    page.get_by_role("link", name="Danh mục & giá").first.click()
    wait_table(page)
    t = tab(page, "Bảng giá")
    h = heads(t)
    ok("Bảng giá: cột đủ ED-31", h == ["Mặt hàng", "Giá bán (đ)", "Áp dụng từ", "Áp dụng đến"], str(h))
    expect(page.get_by_text(re.compile(r"Đang hiện \d+ / \d+ mức giá"))).to_be_visible()
    n_prices = t.locator("tbody tr").count()
    ok("Bảng giá: 13 mức giá seed + 1 mức vừa đặt cho Cá thu = 14", n_prices == 14, str(n_prices))
    ok("Bảng giá: có 'Đặt giá mới' cho Chủ", page.get_by_role("button", name="Đặt giá mới").count() == 1)
    page.screenshot(path=f"{SHOTS}/lo13-loc-6-bang-gia.png")
    page.get_by_role("button", name="Đặt giá mới").click()
    dlg = page.get_by_role("dialog", name="Đặt giá mới")
    dlg.get_by_role("button", name="Lưu giá mới").click()
    ok("Bảng giá: chưa chọn mặt hàng → 'Chọn mặt hàng.'", dlg.get_by_text("Chọn mặt hàng.").count() >= 1)
    expect(dlg.get_by_label(re.compile("^Mặt hàng")).locator("option", has_text="Mực ống")).to_have_count(1)
    dlg.get_by_label(re.compile("^Mặt hàng")).select_option(label="Mực ống")
    dlg.get_by_label(re.compile("^Giá bán")).fill("199000")
    dlg.get_by_role("button", name=re.compile("^(Lưu giá mới|Thử lại)")).click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã đặt giá mới.")).to_be_visible()
    expect(t.locator("tbody tr")).to_have_count(n_prices + 1)
    ok("Bảng giá: mức giá mới hiện ngay trong bảng", "199.000" in t.inner_text())

    # --- Tab Ưu đãi
    t = tab(page, "Ưu đãi")
    h = heads(t)
    ok("Ưu đãi: cột đủ", h == ["Ưu đãi", "Áp dụng cho", "Điều kiện", "Mức giảm", "Từ ngày", "Đến ngày", "Trạng thái", "Thao tác"], str(h))
    ok("Ưu đãi: 3 dòng seed", t.locator("tbody tr").count() == 3)
    page.get_by_label("Trạng thái", exact=True).select_option(label="Đã tắt")
    expect(t.locator("tbody tr")).to_have_count(1)
    ok("Ưu đãi: lọc Đã tắt → 1 dòng", "Khuyến mãi cuối tuần cũ" in t.inner_text())
    page.get_by_label("Trạng thái", exact=True).select_option(label="Mọi trạng thái")
    expect(t.locator("tbody tr")).to_have_count(3)
    page.get_by_role("button", name="Tắt Mua từ 5 kg cá thu giảm 5%").click()
    expect(page.get_by_text("Đã tắt ưu đãi.")).to_be_visible()
    ok("Ưu đãi: bấm Tắt → nút đổi thành Bật", page.get_by_role("button", name="Bật Mua từ 5 kg cá thu giảm 5%").count() == 1)
    page.get_by_role("button", name="Bật Mua từ 5 kg cá thu giảm 5%").click()
    expect(page.get_by_text("Đã bật ưu đãi.")).to_be_visible()
    page.screenshot(path=f"{SHOTS}/lo13-loc-7-uu-dai.png")

    page.get_by_role("link", name="Tạo ưu đãi").click()
    page.wait_for_url("**/catalog/rules/new/**")
    page.get_by_label(re.compile("^Tên ưu đãi")).wait_for()
    page.get_by_role("button", name="Tạo ưu đãi", exact=True).first.click()
    ok("Tạo ưu đãi: để trống → 'Nhập tên ưu đãi.'", page.get_by_text("Nhập tên ưu đãi.").count() >= 1 and "/rules/new" in page.url)
    page.get_by_label(re.compile("^Tên ưu đãi")).fill("Đơn từ 300.000 giảm 10%")
    page.get_by_role("radio", name="Theo đơn, tổng từ M đồng").check()
    page.get_by_label(re.compile("^Đơn từ")).fill("300000")
    page.get_by_label(re.compile("^Mức giảm")).fill("150")
    page.get_by_role("button", name="Tạo ưu đãi", exact=True).first.click()
    ok("Tạo ưu đãi: giảm 150% → chặn ('không được lớn hơn 100')", page.get_by_text(re.compile("không được lớn hơn 100")).count() >= 1 and "/rules/new" in page.url)
    page.screenshot(path=f"{SHOTS}/lo13-loc-8-tao-uu-dai-loi.png")
    page.get_by_label(re.compile("^Mức giảm")).fill("10")
    page.get_by_role("button", name=re.compile("^(Tạo ưu đãi|Thử lại)$")).first.click()
    page.wait_for_url("**/catalog/**tab=rules**")
    t = wait_table(page)
    ok("Tạo ưu đãi: quay về tab Ưu đãi, có dòng mới", t.locator("tbody tr").count() == 4 and "Đơn từ 300.000 giảm 10%" in t.inner_text(), str(t.locator("tbody tr").count()))

    # --- Tab Nhóm hàng
    t = tab(page, "Nhóm hàng")
    h = heads(t)
    ok("Nhóm hàng: cột đủ", h == ["Nhóm hàng", "Nhóm cha", "Số mặt hàng"], str(h))
    ok("Nhóm hàng: 6 nhóm seed", t.locator("tbody tr").count() == 6)
    page.get_by_label("Nhóm cha", exact=True).select_option(label="Hải sản tươi")
    expect(t.locator("tbody tr")).to_have_count(4)
    ok("Nhóm hàng: lọc nhóm cha Hải sản tươi → 4 nhóm con", True)
    page.get_by_label("Nhóm cha", exact=True).select_option(label="Mọi nhóm cha")
    expect(t.locator("tbody tr")).to_have_count(6)
    page.get_by_role("button", name="Thêm nhóm hàng").click()
    dlg = page.get_by_role("dialog", name="Thêm nhóm hàng")
    dlg.get_by_role("button", name="Thêm nhóm hàng").click()
    ok("Thêm nhóm: tên trống → 'Nhập tên nhóm hàng.'", dlg.is_visible() and dlg.get_by_text("Nhập tên nhóm hàng.").count() >= 1)
    dlg.get_by_label(re.compile("^Tên nhóm hàng")).fill("cá")
    dlg.get_by_role("button", name="Thêm nhóm hàng").click()
    expect(dlg.get_by_text(re.compile("Tên này đã có"))).to_be_visible()
    ok("Thêm nhóm: tên trùng (không phân biệt hoa thường) → báo dưới ô, hộp còn mở", dlg.is_visible() and dlg.get_by_label(re.compile("^Tên nhóm hàng")).input_value() == "cá")
    dlg.get_by_label(re.compile("^Tên nhóm hàng")).fill("Đồ khô")
    dlg.get_by_label(re.compile("^Nhóm nhóm cha|^Nhóm cha")).select_option(label="Hải sản tươi")
    dlg.get_by_role("button", name=re.compile("^(Thêm nhóm hàng|Thử lại)")).click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã thêm nhóm hàng.")).to_be_visible()
    expect(t.locator("tbody tr")).to_have_count(7)
    ok("Thêm nhóm: dòng mới hiện trong bảng", "Đồ khô" in t.inner_text())

    clean, extra = personal_clean(page, ("CA-THU-2", "Combo nhậu", "Đồ khô", "199000"))
    ok("Không có dữ liệu nhập tay trong storage hay URL", clean, extra)
    ctx.close()


# ---------------------------------------------------------------- Quản lý (ql1): chỉ xem
def run_manager(browser, errors):
    ctx, page = new_page(browser, "ql1", errors=errors)
    t = goto_catalog(page)
    tabs = [x.strip() for x in page.get_by_role("tab").all_inner_texts()]
    ok("ql1: thấy đủ 4 tab (có quyền xem giá, ưu đãi, nhóm)", tabs == ["Mặt hàng", "Bảng giá", "Ưu đãi", "Nhóm hàng"], str(tabs))
    ok("ql1: cột mặt hàng có giá niêm yết", heads(t) == ITEM_HEADS, str(heads(t)))
    ok("ql1: không có nút Thêm mặt hàng / Thêm combo", page.get_by_role("link", name=re.compile("^Thêm ")).count() == 0)
    ok("ql1: không có giá vốn", "Giá vốn" not in body(page))
    open_item(page, "Cá thu cắt khúc")
    ok("ql1: chi tiết không có 'Đặt giá mới', không có bút sửa tại chỗ", page.get_by_role("button", name="Đặt giá mới").count() == 0 and page.get_by_role("button", name=re.compile("^Sửa ")).count() == 0)
    ok("ql1: vẫn thấy lịch sử giá", section_rows(page, "Lịch sử giá").count() == 2)
    page.get_by_role("button", name="Thao tác khác").click()
    item = page.get_by_role("menuitem", name=re.compile("^Ẩn khỏi Shop"))
    ok("ql1: 'Ẩn khỏi Shop' bị chặn có lý do 'Chỉ Chủ vựa'", item.count() == 1 and (item.get_attribute("aria-disabled") == "true" or item.is_disabled()) and "Chỉ Chủ vựa được đổi" in body(page))
    page.keyboard.press("Escape")
    page.screenshot(path=f"{SHOTS}/lo13-ql1-chi-tiet.png", full_page=True)
    page.get_by_role("link", name="Danh mục & giá").first.click()
    wait_table(page)
    t = tab(page, "Bảng giá")
    ok("ql1: Bảng giá không có nút 'Đặt giá mới'", page.get_by_role("button", name="Đặt giá mới").count() == 0 and t.locator("tbody tr").count() == 13)
    t = tab(page, "Ưu đãi")
    ok("ql1: Ưu đãi không có 'Tạo ưu đãi' và nút Tắt/Bật", page.get_by_role("link", name="Tạo ưu đãi").count() == 0 and page.get_by_role("button", name=re.compile("^(Tắt|Bật) ")).count() == 0)
    t = tab(page, "Nhóm hàng")
    ok("ql1: Nhóm hàng không có 'Thêm nhóm hàng'", page.get_by_role("button", name="Thêm nhóm hàng").count() == 0)
    page.goto(BASE + "/catalog/new/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    ok("ql1: vào thẳng /catalog/new/ → không có quyền, không có form", "quyền" in body(page).lower() and page.get_by_label(re.compile("^Mã hàng")).count() == 0)
    page.goto(BASE + "/catalog/rules/new/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    ok("ql1: vào thẳng /catalog/rules/new/ → không có quyền", "quyền" in body(page).lower() and page.get_by_label(re.compile("^Tên ưu đãi")).count() == 0)
    ctx.close()


# ---------------------------------------------------------------- Kho (kho1): không thấy giá
def run_warehouse(browser, errors):
    ctx, page = new_page(browser, "kho1", errors=errors)
    t = goto_catalog(page)
    ok("kho1: xem được danh sách (trang đầu 8 dòng)", t.locator("tbody tr").count() == 8)
    ok("kho1: KHÔNG có cột giá niêm yết / áp dụng từ", heads(t) == ITEM_HEADS_NO_PRICE, str(heads(t)))
    ok("kho1: không có số tiền đồng nào trong bảng", not re.search(r"\d\.\d{3}\s?đ", t.inner_text()), t.inner_text()[:80])
    tabs = [x.strip() for x in page.get_by_role("tab").all_inner_texts()]
    ok("kho1: chỉ có tab Mặt hàng và Nhóm hàng (không có Bảng giá, Ưu đãi)", tabs == ["Mặt hàng", "Nhóm hàng"], str(tabs))
    ok("kho1: không có Thêm mặt hàng / Thêm combo", page.get_by_role("link", name=re.compile("^Thêm ")).count() == 0)
    ok("kho1: DOM không có chữ 'Giá niêm yết'", "Giá niêm yết" not in page.content())
    page.screenshot(path=f"{SHOTS}/lo13-kho1-mat-hang.png")
    gt = tab(page, "Nhóm hàng")
    ok("kho1: tab Nhóm hàng xem được, không có nút Thêm nhóm hàng", gt.locator("tbody tr").count() == 6 and page.get_by_role("button", name="Thêm nhóm hàng").count() == 0)
    page.goto(BASE + "/catalog/?tab=prices")
    t = wait_table(page)
    ok("kho1: gõ ?tab=prices → vẫn chỉ thấy tab Mặt hàng, không có bảng giá", heads(t) == ITEM_HEADS_NO_PRICE and "Giá bán" not in page.content())
    page.goto(BASE + "/catalog/?tab=rules")
    t = wait_table(page)
    ok("kho1: gõ ?tab=rules → không thấy ưu đãi", "Mua từ 5 kg" not in body(page))
    page.goto(BASE + "/catalog/")
    wait_table(page)
    open_item(page, "Cá thu cắt khúc")
    ok("kho1: chi tiết không có giá, lịch sử giá, nút Đặt giá mới", "Giá niêm yết" not in page.content() and page.locator("section[aria-label='Lịch sử giá']").count() == 0 and page.get_by_role("button", name="Đặt giá mới").count() == 0)
    ok("kho1: chi tiết không có bút sửa", page.get_by_role("button", name=re.compile("^Sửa ")).count() == 0)
    page.screenshot(path=f"{SHOTS}/lo13-kho1-chi-tiet.png", full_page=True)
    ctx.close()


# ---------------------------------------------------------------- Giao hàng / CSKH: không vào được
def run_denied(browser, errors):
    for user in ("giao1", "cs2"):
        ctx, page = new_page(browser, user, errors=errors)
        ok(f"{user}: không có mục 'Danh mục & giá' trong menu", page.locator(".nav a", has_text="Danh mục & giá").count() == 0)
        for path in ("/catalog/", "/catalog/detail/?id=1", "/catalog/new/", "/catalog/rules/new/"):
            page.goto(BASE + path)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            txt = body(page)
            ok(f"{user}: vào thẳng {path} → không có quyền, không có bảng", "quyền" in txt.lower() and page.locator("table.lt").count() == 0 and "Cá thu" not in txt, txt[:120])
        ctx.close()


# ---------------------------------------------------------------- Đường sai
def run_offpath(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    for bad in ("", "?id=abc", "?id=-3", "?id=0", "?id=99999"):
        page.goto(BASE + "/catalog/detail/" + bad)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(400)
        txt = body(page)
        ok(f"Chi tiết {bad or '(không id)'}: báo không tìm thấy, không trắng trang", ("Không tìm thấy" in txt or "không tồn tại" in txt or "Không có" in txt) and "Cá thu" not in txt, txt[:150])

    # Lỗi máy chủ danh sách → thử lại được
    page.goto(BASE + "/catalog/")
    page.wait_for_load_state("networkidle")
    set_mode(page, "fail")
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("button", name="Thử lại").first).to_be_visible()
    ok("Danh sách lỗi 500: có thông báo + nút Thử lại, không trắng trang", page.locator("table.lt tbody tr").count() == 0)
    page.screenshot(path=f"{SHOTS}/lo13-loc-loi-500.png")
    set_mode(page, "ok")
    page.get_by_role("button", name="Thử lại").first.click()
    wait_table(page)
    ok("Danh sách: bấm Thử lại → có dữ liệu", page.locator("table.lt tbody tr").count() == 8)

    # Rỗng
    set_mode(page, "empty")
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text("Chưa có mặt hàng nào")).to_be_visible()
    ok("Danh sách rỗng: gợi ý + nút Thêm mặt hàng cho Chủ", page.get_by_role("link", name="Thêm mặt hàng").count() >= 1 and "Thêm mặt hàng đầu tiên" in body(page))
    page.screenshot(path=f"{SHOTS}/lo13-loc-rong.png")

    # 403 từ BE
    set_mode(page, "forbidden")
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    ok("Danh sách 403 từ máy chủ: hiện 'không có quyền', không bảng", "quyền" in body(page).lower() and page.locator("table.lt").count() == 0)

    # Chi tiết lỗi
    set_mode(page, "detailfail")
    page.goto(BASE + "/catalog/detail/?id=1")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    ok("Chi tiết lỗi 500: có thông báo và nút Thử lại", page.get_by_role("button", name="Thử lại").count() >= 1)
    set_mode(page, "ok")
    page.get_by_role("button", name="Thử lại").first.click()
    page.wait_for_selector("#item-detail", timeout=10_000)
    ok("Chi tiết: Thử lại → hiện mặt hàng", "Cá thu cắt khúc" in body(page))

    # Lịch sử giá lỗi không làm hỏng cả trang
    set_mode(page, "pricesfail")
    page.goto(BASE + "/catalog/detail/?id=1")
    page.wait_for_selector("#item-detail", timeout=10_000)
    settle(page)
    ok("Lịch sử giá lỗi: trang vẫn có thông tin, bảng báo lỗi riêng + Thử lại", "Cá thu cắt khúc" in body(page) and "Chưa tải được lịch sử giá" in body(page) and page.get_by_role("button", name="Thử lại").count() >= 1)
    page.screenshot(path=f"{SHOTS}/lo13-loc-lich-su-gia-loi.png", full_page=True)
    set_mode(page, "ok")

    # Lưu lỗi giữ nguyên giá trị: thêm mặt hàng
    page.goto(BASE + "/catalog/")
    wait_table(page)
    set_mode(page, "savefail")
    page.get_by_role("link", name="Thêm mặt hàng").first.click()
    page.wait_for_url("**/catalog/new/**")
    page.get_by_label(re.compile("^Mã hàng")).fill("LOI-LUU")
    page.get_by_label(re.compile("^Tên mặt hàng")).fill("Mặt hàng thử lỗi")
    page.get_by_label(re.compile("^Nhóm hàng")).select_option(label="Cá")
    page.get_by_role("button", name="Lưu mặt hàng").click()
    expect(page.get_by_role("button", name=re.compile("Thử lại")).first).to_be_visible()
    ok("Lưu lỗi 500: form giữ chữ đã nhập, có alert, nút 'Thử lại'", page.get_by_label(re.compile("^Tên mặt hàng")).input_value() == "Mặt hàng thử lỗi" and page.get_by_role("alert").count() >= 1)
    set_mode(page, "ok")
    page.get_by_role("button", name=re.compile("Thử lại")).first.click()
    page.wait_for_url("**/catalog/detail/**")
    ok("Lưu lỗi rồi Thử lại → tạo được, không tạo trùng", True)
    ctx.close()


# ---------------------------------------------------------------- 360px và 1280px
def run_mobile(browser, errors):
    ctx, page = new_page(browser, "loc", w=360, h=800, mobile=True, errors=errors)
    page.goto(BASE + "/catalog/")
    t = wait_table(page)
    settle(page)
    ok("360px: danh sách không cuộn ngang trang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360px: danh sách mọi vùng bấm >= 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/lo13-loc-360-mat-hang.png")
    t.locator("tbody tr", has_text="Cá thu cắt khúc").first.locator("a").first.click()
    page.wait_for_selector("#item-detail", timeout=10_000)
    settle(page)
    ok("360px: chi tiết không cuộn ngang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360px: chi tiết vùng bấm >= 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/lo13-loc-360-chi-tiet.png", full_page=True)
    page.get_by_role("button", name="Đặt giá mới").first.click()
    dlg = page.get_by_role("dialog", name="Đặt giá mới")
    expect(dlg).to_be_visible()
    ok("360px: hộp Đặt giá mới không cuộn ngang, nút trong khung nhìn", no_hscroll(page) and dlg.get_by_role("button", name="Lưu giá mới").is_visible())
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360px: hộp Đặt giá mới vùng bấm >= 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/lo13-loc-360-dat-gia.png")
    dlg.get_by_role("button", name="Huỷ").click()
    dlg.wait_for(state="detached")
    for path, shot in (("/catalog/?tab=prices", "360-bang-gia"), ("/catalog/?tab=rules", "360-uu-dai"), ("/catalog/?tab=groups", "360-nhom-hang")):
        page.goto(BASE + path)
        wait_table(page)
        settle(page)
        ok(f"360px: {path} không cuộn ngang", no_hscroll(page))
        page.screenshot(path=f"{SHOTS}/lo13-loc-{shot}.png")
    for path, shot in (("/catalog/new/", "360-them-mat-hang"), ("/catalog/new/?type=BUNDLE", "360-them-combo"), ("/catalog/rules/new/", "360-tao-uu-dai")):
        page.goto(BASE + path)
        page.get_by_role("heading", level=2).first.wait_for()
        settle(page)
        ok(f"360px: {path} không cuộn ngang", no_hscroll(page))
        small = page.evaluate(SMALL_TAPS_JS)
        ok(f"360px: {path} vùng bấm >= 44px", not small, str(small))
        page.screenshot(path=f"{SHOTS}/lo13-loc-{shot}.png", full_page=True)
    ctx.close()

    ctx, page = new_page(browser, "kho1", w=360, h=800, mobile=True, errors=errors)
    page.goto(BASE + "/catalog/")
    wait_table(page)
    ok("360px kho1: không cuộn ngang, không có giá niêm yết", no_hscroll(page) and "Giá niêm yết" not in page.content())
    ctx.close()

    ctx, page = new_page(browser, "loc", w=1280, h=800, errors=errors)
    page.goto(BASE + "/catalog/")
    wait_table(page)
    settle(page)
    ok("1280px: danh sách không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo13-loc-1280-mat-hang.png")
    page.get_by_role("tab", name="Ưu đãi").click()
    wait_table(page)
    page.screenshot(path=f"{SHOTS}/lo13-loc-1280-uu-dai.png")
    ctx.close()


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for fn in (run_owner, run_manager, run_warehouse, run_denied, run_offpath, run_mobile):
                try:
                    fn(browser, errors)
                except Exception as e:  # một kịch bản đổ không che các kịch bản khác
                    ok(f"{fn.__name__}: chạy hết không ngoại lệ", False, repr(e)[:600])
        finally:
            browser.close()
    ok("Không có console.error / pageerror", not errors, "; ".join(errors[:5]))
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
    if failed:
        for n, _, e in failed:
            print("FAIL:", n, e)
        sys.exit(1)


if __name__ == "__main__":
    main()
