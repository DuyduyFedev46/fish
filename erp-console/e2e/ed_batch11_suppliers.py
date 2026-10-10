# E2E ERP theo design Lô 11 (Nhà cung cấp, ED-22): chạy trên bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
#   BASE=http://127.0.0.1:3101 SHOTS=<thư mục ảnh> python3 e2e/ed_batch11_suppliers.py      # tắt server sau khi xong
# Trạng thái mock nằm trong bộ nhớ trang: page.goto làm về seed, nên luồng ghi đi bằng bấm menu / bấm dòng, không gõ URL.
# Kiểm: loc thấy Tổng tiền mua · ql1 không có cột/ô/số tiền trong DOM nhưng thêm/sửa/ngừng được · kho1 xem được, không Thêm/Sửa, "Ngừng hợp tác" bị chặn ·
# giao1 / cs2 không có menu và vào thẳng thì "không có quyền" · tên trùng (hai dạng 400) · ngừng rồi bật lại · 360px · đường sai · không rò dữ liệu cá nhân ra storage/URL.
import json
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shots"))
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)

SMALL_TAPS_JS = """() => [...document.querySelectorAll('button, a, input, select')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y < innerHeight
      && !e.classList.contains('sr-only') && !e.matches('input[type=checkbox]') && (r.height < 44 || (!['INPUT', 'SELECT'].includes(e.tagName) && r.width < 44));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""

PHONE = re.compile(r"\b0\d{9}\b")
NAME_TAKEN = "Đã có nhà cung cấp trùng tên này."


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
    page.evaluate("(m) => window.__caveMock.suppliers(m)", mode)


def goto_list(page, soft=True):
    """Vào danh sách: bấm menu nếu có (giữ trạng thái mock), nếu không (điện thoại) gõ URL."""
    link = page.locator(".nav a", has_text="Nhà cung cấp").first
    if soft and link.count() and link.is_visible():
        link.click()
    else:
        page.goto(BASE + "/suppliers/")
    page.wait_for_url("**/suppliers/**")
    return wait_table(page)


def wait_table(page):
    t = page.locator("table.lt").first
    expect(t.locator("tbody tr").first).to_be_visible()
    expect(t.locator("tr.lt-skel")).to_have_count(0)
    return t


def heads(t):
    return [re.sub(r"\s+", " ", h).split(" lock")[0].split("lock")[0].strip() for h in t.locator("thead th").all_inner_texts()]


def open_supplier(page, name):
    t = page.locator("table.lt").first
    t.locator("tbody tr", has_text=name).first.locator("a").first.click()
    page.wait_for_url("**/suppliers/detail/**")
    page.wait_for_selector("#supplier-detail", timeout=10_000)
    settle(page)


def more_items(page):
    page.get_by_role("button", name="Thao tác khác").click()
    items = [re.sub(r"\s+", " ", x).strip() for x in page.get_by_role("menuitem").all_inner_texts()]
    return items


def pick_more(page, label):
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^" + re.escape(label))).click()


def storage_dump(page):
    # Bỏ kho mock của các module khác (khách, đơn, tài khoản GIẢ gieo sẵn khi Tổng quan tải; có thể trùng số điện thoại đang thử). Chỉ soi những gì màn Nhà cung cấp tự lưu.
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage).filter(([k]) => !k.startsWith('cave_erp_mock_')), Object.entries(sessionStorage).filter(([k]) => !k.startsWith('cave_erp_mock_')), location.href])")


def personal_clean(page, extra=()):
    dump = storage_dump(page)
    bad = [x for x in (*extra, "0901234567", "0912345678", "Đầu mối Cảng cá", "Anh Ba") if x in dump]
    return not bad, str(bad)


# ---------------------------------------------------------------- Chủ (loc)
def run_owner(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    t = goto_list(page)

    h = heads(t)
    ok("Chủ: cột đủ ED-22 gồm Tổng tiền mua", h == ["Nhà cung cấp", "Loại", "Số điện thoại", "Số phiếu nhập", "Lần nhập gần nhất", "Trạng thái", "Tổng tiền mua"], str(h))
    ok("Chủ: 'Đang hiện 7 / 7 nhà cung cấp'", page.get_by_text("Đang hiện 7 / 7 nhà cung cấp").is_visible())
    first = [c.strip() for c in t.locator("tbody tr", has_text="Đầu mối Cảng cá").first.locator("td").all_inner_texts()]
    ok("Chủ: tổng tiền mua là VNĐ (4 phiếu đã ghi nhận, bỏ phiếu nháp)", re.search(r"37\.451\.000", first[-1]) is not None, str(first))
    ok("Chủ: số phiếu chỉ tính đã ghi nhận (4)", first[3] == "4", str(first))
    ok("Chủ: số điện thoại hiện đủ (dữ liệu đối tác)", "0901234567" in first[2], str(first))
    ok("Chủ: nhà cung cấp chưa nhập lần nào hiện 0 phiếu và gạch '—'", [c.strip() for c in t.locator("tbody tr", has_text="Vựa Phước Hải").first.locator("td").all_inner_texts()][3:5] == ["0", "—"])
    ok("Chủ: không có chữ NCC/SĐT trên giao diện", "NCC" not in body(page) and "SĐT" not in body(page))
    ok("Chủ: có nút 'Thêm nhà cung cấp'", page.get_by_role("button", name="Thêm nhà cung cấp").count() == 1)
    page.screenshot(path=f"{SHOTS}/ed11-loc-1-danh-sach.png")

    # Tìm + lọc
    page.get_by_role("searchbox").or_(page.get_by_placeholder("Tìm tên hoặc số điện thoại")).first.fill("vua ca lagi")
    expect(t.locator("tbody tr")).to_have_count(1)
    ok("Tìm 'vua ca lagi' (không dấu) → Vựa cá Lagi", "Vựa cá Lagi" in t.locator("tbody tr").first.inner_text())
    page.get_by_role("button", name="Xoá tìm kiếm").first.click()
    expect(t.locator("tbody tr")).to_have_count(7)
    page.get_by_label("Lọc theo loại").select_option(label="Doanh nghiệp")
    expect(t.locator("tbody tr")).to_have_count(3)
    ok("Lọc Doanh nghiệp → 3 dòng", all("Doanh nghiệp" in r for r in t.locator("tbody tr").all_inner_texts()))
    page.get_by_label("Lọc theo trạng thái").select_option(label="Ngừng hợp tác")
    expect(page.get_by_text("Không có nhà cung cấp nào khớp bộ lọc")).to_be_visible()
    ok("Lọc loại + trạng thái không khớp → trạng thái rỗng có gợi ý bỏ lọc", page.get_by_text("Đổi hoặc bỏ bộ lọc để xem thêm.").is_visible())
    page.get_by_label("Lọc theo loại").select_option(label="Mọi loại")
    expect(t.locator("tbody tr")).to_have_count(1)
    ok("Lọc Ngừng hợp tác → Chị Tư Hòn Rơm", "Chị Tư Hòn Rơm" in t.locator("tbody tr").first.inner_text())
    page.get_by_label("Lọc theo trạng thái").select_option(label="Mọi trạng thái")
    expect(t.locator("tbody tr")).to_have_count(7)

    # --- Thêm: kiểm tên trống, tên trùng, rồi thêm thật
    n0 = t.locator("tbody tr").count()
    page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
    dlg = page.get_by_role("dialog", name="Thêm nhà cung cấp")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    ok("Thêm: tên trống → báo lỗi dưới ô, không đóng hộp", dlg.is_visible() and dlg.get_by_text("Nhập tên nhà cung cấp.").count() >= 1, dlg.inner_text()[:100])
    dlg.get_by_label("Tên").fill("  vựa CÁ lagi (anh ba)  ")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    expect(dlg.get_by_text(NAME_TAKEN).first).to_be_visible()
    ok("Thêm: tên trùng (không phân biệt hoa thường) → báo trùng, hộp còn mở, giữ nguyên chữ đã gõ", dlg.is_visible() and dlg.get_by_label("Tên").input_value().strip() == "vựa CÁ lagi (anh ba)")
    ok("Thêm: lỗi trùng tên hiện đúng một chỗ", dlg.get_by_text(NAME_TAKEN).count() == 1, str(dlg.get_by_text(NAME_TAKEN).count()))
    ok("Thêm: nút chính đổi 'Thử lại' sau lỗi", dlg.get_by_role("button", name=re.compile("Thử lại")).count() == 1)
    # B1 (QA Lô 11): gõ tên khác sau lỗi trùng → mọi lỗi cũ biến mất (không nhảy lên đầu hộp), nút về "Lưu nhà cung cấp"
    dlg.get_by_label("Tên").fill("Vựa Cát")
    ok("Thêm: gõ tên khác sau lỗi trùng → không còn câu lỗi nào trong hộp", dlg.get_by_role("alert").count() == 0 and dlg.get_by_text(NAME_TAKEN).count() == 0, dlg.inner_text()[:160])
    ok("Thêm: gõ tên khác sau lỗi trùng → nút chính về 'Lưu nhà cung cấp' (không còn 'Thử lại')", dlg.get_by_role("button", name="Lưu nhà cung cấp").count() == 1 and dlg.get_by_role("button", name=re.compile("Thử lại")).count() == 0)
    dlg.get_by_label("Tên").fill("Vựa Cát Bà")
    dlg.get_by_label("Số điện thoại").fill("0977111222")
    dlg.get_by_role("button", name=re.compile("Thử lại|Lưu nhà cung cấp")).click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã thêm nhà cung cấp.")).to_be_visible()
    expect(t.locator("tbody tr")).to_have_count(n0 + 1)
    ok("Thêm: hàng mới hiện trong danh sách, đang hợp tác", "Vựa Cát Bà" in t.inner_text())

    # --- Chi tiết
    open_supplier(page, "Đầu mối Cảng cá Phan Thiết")
    ok("Chi tiết: tiêu đề + chip Đang hợp tác", page.locator("main h2").first.inner_text().strip() == "Đầu mối Cảng cá Phan Thiết" and page.get_by_text("Đang hợp tác").first.is_visible())
    ok("Chi tiết: khối Thông tin + Mua hàng", page.get_by_text("Thông tin nhà cung cấp").count() >= 1 and page.get_by_text("Mua hàng", exact=True).count() >= 1)
    ok("Chi tiết: Chủ thấy 'Tổng tiền mua'", page.get_by_text("Tổng tiền mua").count() >= 1 and "37.451.000" in body(page))
    rt = page.locator("section[aria-label='Phiếu nhập'] table.lt")
    expect(rt.locator("tbody tr").first).to_be_visible()
    rh = heads(rt)
    ok("Chi tiết: bảng Phiếu nhập có cột Tiền mua cho Chủ", rh == ["Mã phiếu", "Nhập lúc", "Mặt hàng", "Số kg", "Tiền mua", "Trạng thái"], str(rh))
    ok("Chi tiết: 5 phiếu (kể cả nháp), có chip 'Nháp'", rt.locator("tbody tr").count() == 5 and "Nháp" in rt.inner_text(), str(rt.locator("tbody tr").count()))
    bt = page.locator("section[aria-label='Lô đang bán'] table.lt")
    expect(bt.locator("tbody tr").first).to_be_visible()
    ok("Chi tiết: 3 lô đang bán (còn hàng) của nhà cung cấp", bt.locator("tbody tr").count() == 3, str(bt.locator("tbody tr").count()))
    ok("Chi tiết: bảng lô không lộ giá vốn", "Giá vốn" not in bt.inner_text() and "Giá mua" not in bt.inner_text())
    ok("Chi tiết: dòng thời gian có việc 'Thêm nhà cung cấp' và 'Ghi nhận phiếu nhập'", page.locator("#supplier-timeline").inner_text().count("Ghi nhận phiếu nhập") >= 1 and "Thêm nhà cung cấp" in page.locator("#supplier-timeline").inner_text())
    ok("Chi tiết: không có chữ NCC", "NCC" not in body(page))
    items = more_items(page)
    ok("Chi tiết: menu '…' có Ngừng hợp tác + Xem nhật ký (không Xoá)", any(i.startswith("Ngừng hợp tác") for i in items) and any(i.startswith("Xem nhật ký") for i in items) and not any("Xoá" in i for i in items), str(items))
    page.keyboard.press("Escape")
    page.screenshot(path=f"{SHOTS}/ed11-loc-2-chi-tiet.png", full_page=True)

    # Xem nhật ký → cuộn tới dòng thời gian
    pick_more(page, "Xem nhật ký")
    ok("Xem nhật ký: dòng thời gian nhận tiêu điểm", page.evaluate("() => document.activeElement && document.activeElement.id") == "supplier-timeline")

    # Sửa tại chỗ ghi chú
    page.get_by_role("button", name="Sửa ghi chú").click()
    ed = page.get_by_label("Ghi chú").first
    ed.fill("Giao hàng trước 4 giờ sáng.")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    expect(page.get_by_text("Đã lưu nhà cung cấp.")).to_be_visible()
    expect(page.locator("main")).to_contain_text("Giao hàng trước 4 giờ sáng.")
    ok("Sửa tại chỗ: ghi chú đổi", "Giao hàng trước 4 giờ sáng." in body(page))
    # Sửa tại chỗ: tên trùng ném lỗi dưới ô
    page.get_by_role("button", name="Sửa tên").click()
    # B3 (QA Lô 11): để trống tên → đúng câu "Nhập tên nhà cung cấp.", không phải câu chung
    page.get_by_label("Tên").first.fill("")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    ok("Sửa tại chỗ: tên trống → 'Nhập tên nhà cung cấp.'", page.get_by_text("Nhập tên nhà cung cấp.").count() >= 1 and page.get_by_text("Nhập giá trị cho ô này.").count() == 0)
    page.get_by_label("Tên").first.fill("Anh Sáu Cửa Lò")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    expect(page.get_by_text(NAME_TAKEN).first).to_be_visible()
    ok("Sửa tại chỗ: tên trùng → lỗi dưới ô, giữ chữ đang gõ", page.get_by_label("Tên").first.input_value() == "Anh Sáu Cửa Lò")
    page.get_by_role("button", name="Huỷ").first.click()
    ok("Sửa tại chỗ: Huỷ → tên cũ còn nguyên", page.locator("main h2").first.inner_text().strip() == "Đầu mối Cảng cá Phan Thiết")

    # Sửa bằng hộp (Primary)
    page.get_by_role("button", name="Sửa", exact=True).first.click()
    dlg = page.get_by_role("dialog", name="Sửa nhà cung cấp")
    dlg.get_by_role("button", name="Lưu thay đổi").click()
    ok("Sửa hộp: chưa đổi gì → báo 'Chưa có gì thay đổi để lưu.', không đóng", dlg.is_visible() and dlg.get_by_text("Chưa có gì thay đổi để lưu.").count() == 1)
    ok("Sửa hộp: không có ô 'Đang hợp tác' (đổi trạng thái chỉ qua hộp xác nhận)", dlg.get_by_label("Đang hợp tác").count() == 0)
    dlg.get_by_role("radio", name="Cá nhân").check()
    dlg.get_by_role("button", name="Lưu thay đổi").click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã lưu nhà cung cấp.").first).to_be_visible()
    expect(page.locator("main")).to_contain_text("Cá nhân")
    ok("Sửa hộp: loại đổi thành Cá nhân", page.get_by_text("Cá nhân").count() >= 1)

    # Ngừng hợp tác: Huỷ không đổi → xác nhận → bật lại
    pick_more(page, "Ngừng hợp tác")
    dlg = page.get_by_role("dialog", name="Ngừng hợp tác với nhà cung cấp này?")
    ok("Ngừng hợp tác: hỏi lại, nêu hậu quả", dlg.is_visible() and "Phiếu nhập và lô cũ giữ nguyên" in dlg.inner_text())
    dlg.get_by_role("button", name="Huỷ").click()
    dlg.wait_for(state="detached")
    ok("Ngừng hợp tác: bấm Huỷ → vẫn Đang hợp tác", page.get_by_text("Đang hợp tác").first.is_visible())
    pick_more(page, "Ngừng hợp tác")
    dlg = page.get_by_role("dialog", name="Ngừng hợp tác với nhà cung cấp này?")
    dlg.get_by_role("button", name="Ngừng hợp tác").click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã ngừng hợp tác.")).to_be_visible()
    expect(page.locator("main h2").first.locator("xpath=..")).to_contain_text("Ngừng hợp tác")
    ok("Ngừng hợp tác: chip đổi 'Ngừng hợp tác', hiện 'Bật lại hợp tác' trong menu", page.locator("main").get_by_text("Ngừng hợp tác").first.is_visible() and any(i.startswith("Bật lại hợp tác") for i in more_items(page)))
    page.keyboard.press("Escape")
    expect(page.locator("#supplier-timeline")).to_contain_text("Ngừng hợp tác")
    ok("Ngừng hợp tác: dòng thời gian ghi lại việc", "Ngừng hợp tác" in page.locator("#supplier-timeline").inner_text())
    page.screenshot(path=f"{SHOTS}/ed11-loc-3-da-ngung.png", full_page=True)
    pick_more(page, "Bật lại hợp tác")
    dlg = page.get_by_role("dialog", name="Bật lại hợp tác?")
    dlg.get_by_role("button", name="Bật lại hợp tác").click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã bật lại hợp tác.")).to_be_visible()
    expect(page.locator("main h2").first.locator("xpath=..")).to_contain_text("Đang hợp tác")
    ok("Bật lại hợp tác: trở về Đang hợp tác", any(i.startswith("Ngừng hợp tác") for i in more_items(page)))
    page.keyboard.press("Escape")

    # Quay về danh sách bằng link, dữ liệu mới còn
    page.get_by_role("link", name="Nhà cung cấp").first.click()
    t = wait_table(page)
    ok("Quay lại danh sách: tên và loại mới còn", "Cá nhân" in t.locator("tbody tr", has_text="Đầu mối Cảng cá").first.inner_text())

    clean, extra = personal_clean(page, ("0977111222", "Vựa Cát Bà"))
    ok("Không có SĐT/tên nhà cung cấp trong storage hay URL", clean, extra)
    ctx.close()


# ---------------------------------------------------------------- Quản lý (ql1)
def run_manager(browser, errors):
    ctx, page = new_page(browser, "ql1", errors=errors)
    t = goto_list(page)
    h = heads(t)
    ok("ql1: danh sách KHÔNG có cột Tổng tiền mua", "Tổng tiền mua" not in h and len(h) == 6, str(h))
    ok("ql1: trang không có chữ 'Tổng tiền mua' trong DOM", "Tổng tiền mua" not in page.content())
    ok("ql1: không có số tiền đồng nào trong bảng", not re.search(r"\d\.\d{3}\s?đ", t.inner_text()), t.inner_text()[:80])
    ok("ql1: có nút 'Thêm nhà cung cấp'", page.get_by_role("button", name="Thêm nhà cung cấp").count() == 1)

    page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
    dlg = page.get_by_role("dialog", name="Thêm nhà cung cấp")
    dlg.get_by_label("Tên").fill("Anh Tư Bến Tre")
    dlg.get_by_role("radio", name="Doanh nghiệp").check()
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã thêm nhà cung cấp.")).to_be_visible()
    expect(t.locator("tbody tr", has_text="Anh Tư Bến Tre")).to_have_count(1)
    ok("ql1: thêm được", "Anh Tư Bến Tre" in t.inner_text())

    open_supplier(page, "Đầu mối Cảng cá Phan Thiết")
    ok("ql1: chi tiết không có 'Tổng tiền mua'", "Tổng tiền mua" not in page.content() and "37.451.000" not in body(page))
    rt = page.locator("section[aria-label='Phiếu nhập'] table.lt")
    expect(rt.locator("tbody tr").first).to_be_visible()
    rh = heads(rt)
    ok("ql1: bảng Phiếu nhập không có cột Tiền mua", rh == ["Mã phiếu", "Nhập lúc", "Mặt hàng", "Số kg", "Trạng thái"], str(rh))
    ok("ql1: có nút Sửa, sửa được", page.get_by_role("button", name="Sửa", exact=True).count() >= 1)
    page.get_by_role("button", name="Sửa số điện thoại").click()
    page.get_by_label("Số điện thoại").first.fill("0966222333")
    page.get_by_role("button", name="Lưu", exact=True).first.click()
    expect(page.get_by_text("Đã lưu nhà cung cấp.")).to_be_visible()
    expect(page.locator("main")).to_contain_text("0966222333")
    ok("ql1: sửa số điện thoại tại chỗ", "0966222333" in body(page))
    pick_more(page, "Ngừng hợp tác")
    dlg = page.get_by_role("dialog", name="Ngừng hợp tác với nhà cung cấp này?")
    dlg.get_by_role("button", name="Ngừng hợp tác").click()
    dlg.wait_for(state="detached")
    expect(page.get_by_text("Đã ngừng hợp tác.")).to_be_visible()
    ok("ql1: ngừng hợp tác được", True)
    clean, extra = personal_clean(page, ("0966222333", "Anh Tư Bến Tre"))
    ok("ql1: không có SĐT/tên nhà cung cấp trong storage hay URL", clean, extra)
    ctx.close()


# ---------------------------------------------------------------- Kho (kho1): xem, không sửa
def run_warehouse(browser, errors):
    ctx, page = new_page(browser, "kho1", errors=errors)
    t = goto_list(page)
    ok("kho1: xem được danh sách", t.locator("tbody tr").count() == 7)
    ok("kho1: không có cột Tổng tiền mua", "Tổng tiền mua" not in heads(t) and "Tổng tiền mua" not in page.content())
    ok("kho1: KHÔNG có nút 'Thêm nhà cung cấp'", page.get_by_role("button", name="Thêm nhà cung cấp").count() == 0)
    open_supplier(page, "Vựa cá Lagi")
    ok("kho1: chi tiết không có nút Sửa, không có bút sửa tại chỗ", page.get_by_role("button", name="Sửa", exact=True).count() == 0 and page.get_by_role("button", name=re.compile("^Sửa ")).count() == 0)
    page.get_by_role("button", name="Thao tác khác").click()
    item = page.get_by_role("menuitem", name=re.compile("^Ngừng hợp tác"))
    ok("kho1: 'Ngừng hợp tác' bị chặn có lý do", item.count() == 1 and (item.get_attribute("aria-disabled") == "true" or item.is_disabled()) and "Chỉ Chủ và Quản lý" in page.locator("body").inner_text(), str(item.count()))
    page.keyboard.press("Escape")
    ok("kho1: thấy phiếu nhập (không số tiền) và lô đang bán", page.locator("section[aria-label='Phiếu nhập'] table.lt").count() == 1 and "Tiền mua" not in body(page))
    page.screenshot(path=f"{SHOTS}/ed11-kho1-chi-tiet.png", full_page=True)
    ctx.close()


# ---------------------------------------------------------------- Giao hàng / CSKH: không vào được
def run_denied(browser, errors):
    for user in ("giao1", "cs2"):
        ctx, page = new_page(browser, user, errors=errors)
        ok(f"{user}: không có mục 'Nhà cung cấp' trong menu", page.locator(".nav a", has_text="Nhà cung cấp").count() == 0 and "Nhà cung cấp" not in " ".join(page.locator(".nav").all_inner_texts()))
        page.goto(BASE + "/suppliers/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        txt = body(page)
        ok(f"{user}: vào thẳng /suppliers/ → không có quyền, không có bảng", ("quyền" in txt.lower()) and page.locator("table.lt").count() == 0, txt[:120])
        ok(f"{user}: không có dữ liệu nhà cung cấp trên trang", "Đầu mối Cảng cá" not in txt and not PHONE.search(txt))
        page.goto(BASE + "/suppliers/detail/?id=1")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        txt = body(page)
        ok(f"{user}: vào thẳng chi tiết → không có quyền", ("quyền" in txt.lower()) and "Đầu mối Cảng cá" not in txt, txt[:120])
        ctx.close()


# ---------------------------------------------------------------- Đường sai
def run_offpath(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    for bad in ("", "?id=abc", "?id=-3", "?id=0", "?id=99999"):
        page.goto(BASE + "/suppliers/detail/" + bad)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(400)
        txt = body(page)
        ok(f"Chi tiết {bad or '(không id)'}: báo không tìm thấy, không trắng trang, có đường về", ("Không tìm thấy" in txt or "không tồn tại" in txt or "Không có" in txt) and page.get_by_role("link", name=re.compile("Nhà cung cấp")).count() >= 1, txt[:150])
        ok(f"Chi tiết {bad or '(không id)'}: không có dữ liệu nhà cung cấp lọt ra", "Đầu mối Cảng cá" not in txt)

    # Lỗi máy chủ danh sách → thử lại được
    page.goto(BASE + "/suppliers/")
    page.wait_for_load_state("networkidle")
    set_mode(page, "fail")
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("button", name="Thử lại").first).to_be_visible()
    ok("Danh sách lỗi 500: có thông báo + nút Thử lại, không trắng trang", "Máy chủ đang bận" in body(page) or "Không tải được" in body(page) or "Thử lại" in body(page))
    set_mode(page, "ok")
    page.get_by_role("button", name="Thử lại").first.click()
    wait_table(page)
    ok("Danh sách: bấm Thử lại → có dữ liệu", page.locator("table.lt tbody tr").count() == 7)

    # Rỗng
    set_mode(page, "empty")
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text("Chưa có nhà cung cấp nào")).to_be_visible()
    ok("Danh sách rỗng: có gợi ý + nút Thêm cho Chủ", page.get_by_role("button", name="Thêm nhà cung cấp").count() >= 1 and "Thêm nhà cung cấp để chọn khi nhập lô." in body(page))
    page.screenshot(path=f"{SHOTS}/ed11-loc-rong.png")

    # 403 từ BE
    set_mode(page, "forbidden")
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    ok("Danh sách 403 từ máy chủ: hiện 'không có quyền'", "quyền" in body(page).lower() and page.locator("table.lt").count() == 0)

    # Chi tiết lỗi
    set_mode(page, "detailfail")
    page.goto(BASE + "/suppliers/detail/?id=1")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    ok("Chi tiết lỗi 500: có thông báo và nút Thử lại", page.get_by_role("button", name="Thử lại").count() >= 1)
    set_mode(page, "ok")
    page.get_by_role("button", name="Thử lại").first.click()
    page.wait_for_selector("#supplier-detail", timeout=10_000)
    ok("Chi tiết: Thử lại → hiện nhà cung cấp", "Đầu mối Cảng cá Phan Thiết" in body(page))

    # Bảng phụ lỗi không làm hỏng cả trang
    set_mode(page, "receiptsfail")
    page.goto(BASE + "/suppliers/detail/?id=1")
    page.wait_for_selector("#supplier-detail", timeout=10_000)
    settle(page)
    ok("Phiếu nhập lỗi: trang vẫn có thông tin, bảng báo lỗi riêng + Thử lại", "Đầu mối Cảng cá Phan Thiết" in body(page) and "Chưa tải được phiếu nhập" in body(page))
    set_mode(page, "batchesfail")
    page.goto(BASE + "/suppliers/detail/?id=1")
    page.wait_for_selector("#supplier-detail", timeout=10_000)
    settle(page)
    ok("Lô đang bán lỗi: bảng báo lỗi riêng, phiếu nhập vẫn hiện", "Chưa tải được lô đang bán" in body(page) and page.locator("section[aria-label='Phiếu nhập'] table.lt tbody tr").count() >= 1)

    # Lưu lỗi giữ nguyên giá trị; race tên trùng dạng {detail, code}
    set_mode(page, "ok")
    page.goto(BASE + "/suppliers/")
    wait_table(page)
    set_mode(page, "savefail")
    page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
    dlg = page.get_by_role("dialog", name="Thêm nhà cung cấp")
    dlg.get_by_label("Tên").fill("Vựa Thử Lỗi")
    dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
    expect(dlg.get_by_role("button", name=re.compile("Thử lại"))).to_be_visible()
    ok("Lưu lỗi 500: hộp còn mở, giữ chữ đã gõ, hiện lỗi, nút 'Thử lại'", dlg.is_visible() and dlg.get_by_label("Tên").input_value() == "Vựa Thử Lỗi" and dlg.get_by_role("alert").count() >= 1)
    set_mode(page, "racename")
    dlg.get_by_role("button", name=re.compile("Thử lại")).click()
    expect(dlg.get_by_text(NAME_TAKEN).first).to_be_visible()
    ok("Tên trùng dạng {detail, code:SUPPLIER_NAME_TAKEN} cũng báo đúng", dlg.is_visible() and dlg.get_by_text(NAME_TAKEN).count() == 1, str(dlg.get_by_text(NAME_TAKEN).count()))
    dlg.get_by_label("Tên").fill("Vựa Thử Lỗi 2")
    ok("Tên trùng dạng {detail, code}: gõ tên khác → hết lỗi, không có alert ở đầu hộp", dlg.get_by_role("alert").count() == 0 and dlg.get_by_text(NAME_TAKEN).count() == 0, dlg.inner_text()[:160])
    dlg.get_by_label("Tên").fill("x" * 201)
    dlg.get_by_role("button", name=re.compile("Thử lại|Lưu nhà cung cấp")).click()
    ok("Tên quá 200 ký tự bị chặn hoặc báo", dlg.get_by_text(re.compile("tối đa 200")).count() >= 1 or dlg.get_by_label("Tên").input_value().__len__() <= 200)
    dlg.get_by_role("button", name="Huỷ").click()
    dlg.wait_for(state="detached")
    set_mode(page, "ok")
    ok("Huỷ hộp Thêm → không có hàng mới", page.locator("table.lt tbody tr", has_text="Vựa Thử Lỗi").count() == 0)
    # Escape đóng hộp
    page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)
    ok("Escape đóng hộp Thêm", True)
    set_mode(page, "ok")
    ctx.close()


# ---------------------------------------------------------------- 360px
def run_mobile(browser, errors):
    ctx, page = new_page(browser, "loc", w=360, h=800, mobile=True, errors=errors)
    page.goto(BASE + "/suppliers/")
    t = wait_table(page)
    settle(page)
    ok("360px: danh sách không cuộn ngang trang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360px: danh sách mọi vùng bấm >= 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/ed11-loc-360-danh-sach.png")
    page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
    dlg = page.get_by_role("dialog", name="Thêm nhà cung cấp")
    expect(dlg).to_be_visible()
    ok("360px: hộp Thêm không cuộn ngang, nút trong khung nhìn", no_hscroll(page) and dlg.get_by_role("button", name="Lưu nhà cung cấp").is_visible())
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360px: hộp Thêm vùng bấm >= 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/ed11-loc-360-them.png")
    dlg.get_by_role("button", name="Huỷ").click()
    dlg.wait_for(state="detached")
    t.locator("tbody tr", has_text="Đầu mối Cảng cá").first.locator("a").first.click()
    page.wait_for_selector("#supplier-detail", timeout=10_000)
    settle(page)
    ok("360px: chi tiết không cuộn ngang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360px: chi tiết vùng bấm >= 44px", not small, str(small))
    pencils = page.locator('button[aria-label^="Sửa "]')
    sizes = [pencils.nth(i).bounding_box() for i in range(pencils.count())]
    ok("360px: bút chì sửa tại chỗ có vùng bấm thật >= 44x44", len(sizes) >= 1 and all(b and b["width"] >= 44 and b["height"] >= 44 for b in sizes), str(sizes))
    ok("360px: Chủ vẫn thấy 'Tổng tiền mua' ở chi tiết", "37.451.000" in body(page))
    page.screenshot(path=f"{SHOTS}/ed11-loc-360-chi-tiet.png", full_page=True)
    ctx.close()

    ctx, page = new_page(browser, "ql1", w=360, h=800, mobile=True, errors=errors)
    page.goto(BASE + "/suppliers/")
    wait_table(page)
    ok("360px ql1: không cuộn ngang, không có Tổng tiền mua", no_hscroll(page) and "Tổng tiền mua" not in page.content())
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
                    ok(f"{fn.__name__}: chạy hết không ngoại lệ", False, repr(e)[:400])
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
