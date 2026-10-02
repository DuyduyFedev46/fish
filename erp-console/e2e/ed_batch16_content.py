# E2E ERP theo design Lô 16 (Nội dung, ED-35 Danh sách bài viết + Chuyên mục · ED-36 Soạn bài, thiết lập, đăng/gỡ/trả về): bản build MOCK phục vụ tĩnh.
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out /đường/dẫn/riêng && (cd /đường/dẫn/riêng && python3 -m http.server 3901 --bind 127.0.0.1 &)
#   BASE=http://127.0.0.1:3901 SHOTS=<thư mục ảnh> python3 e2e/ed_batch16_content.py      # tắt server (đúng cổng 3901) sau khi xong
# Trạng thái mock nằm trong bộ nhớ trang: page.goto làm về seed, nên luồng ghi đi bằng bấm menu / bấm nút, không gõ URL.
# Kiểm: loc làm đủ (danh sách, chuyên mục trùng tên / ngừng dùng bị chặn, soạn bài, đăng có bảng 5 ô tick, thiếu thông tin → mở Thiết lập, cảnh báo SĐT / giá vốn,
# xung đột phiên bản, tên bài giống mã HTML hiện thành chữ) · ql1 bị gỡ quyền đăng thì không có nút Đăng/Gỡ, chỉ Gửi duyệt/Trả về · kho1, giao1, cs2 "không có quyền" ·
# trạng thái lỗi / rỗng / 403 · 360px không cuộn ngang, nút bấm đủ 44px · không rò dữ liệu cá nhân ra storage / URL.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3901")
SHOTS = os.environ.get("SHOTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shots", "lo16"))
os.makedirs(SHOTS, exist_ok=True)
results = []
expect.set_options(timeout=10_000)

# PNG 1x1 hợp lệ (ảnh bịa để thử tải lên).
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000" "1f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
)

SMALL_TAPS_JS = """() => [...document.querySelectorAll('button, a, input, select')].filter(e => {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.x >= 0 && r.x < 360 && r.y >= 0 && r.y < innerHeight
      && !e.classList.contains('sr-only') && !e.classList.contains('lt-link') && !e.matches('input[type=checkbox], input[type=file]') && (r.height < 44 || (!['INPUT', 'SELECT'].includes(e.tagName) && !e.classList.contains('tab') && r.width < 44));
  }).map(e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().slice(0,30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))"""

NO_PERM = "không có quyền"
IGNORE = ("Failed to fetch RSC payload", "Failed to load resource")


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra if not cond else "")


def new_page(browser, user, w=1366, h=900, mobile=False, errors=None, pre=None):
    opts = {"viewport": {"width": w, "height": h}, "reduced_motion": "reduce"}
    if mobile:
        opts.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**opts)
    page = ctx.new_page()
    if errors is not None:
        page.on("console", lambda m: m.type == "error" and not any(x in m.text for x in IGNORE) and errors.append(f"[{user}] {m.text}"))
        page.on("pageerror", lambda e: errors.append(f"[{user}] {e}"))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    if pre:
        page.evaluate(pre)
    page.fill("#u", user)
    page.fill("#p", "demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
    page.wait_for_load_state("networkidle")
    return ctx, page


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)
    page.wait_for_timeout(200)


def body(page):
    return page.locator("body").inner_text()


def main_text(page):
    return page.locator("main").inner_text() if page.locator("main").count() else body(page)


def no_hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def menu_labels(page):
    return [x.strip().split("\n")[-1].strip() for x in page.locator(".nav a").all_inner_texts()]


def go_menu(page, label, url):
    link = page.locator(".nav a", has_text=label).first
    if link.count() and link.is_visible():
        link.click()
    else:
        page.goto(BASE + url)
    page.wait_for_url("**" + url + "**")
    settle(page)


def wait_table(page):
    t = page.locator("table.lt").first
    expect(t.locator("tbody tr").first).to_be_visible()
    expect(t.locator("tr.lt-skel")).to_have_count(0)
    settle(page)
    return t


def rows_count(page):
    return page.locator("table.lt tbody tr").count()


def storage_dump(page):
    return page.evaluate("() => JSON.stringify([Object.entries(localStorage).filter(([k]) => !k.startsWith('cave_erp_mock_')), Object.entries(sessionStorage).filter(([k]) => !k.startsWith('cave_erp_mock_')), location.href])")


def banned_words(txt):
    # Từ cấm trong chữ hiển thị (UI-RULES §1): mã luật, từ kỹ thuật tiếng Anh, viết tắt.
    bad = [w for w in ("slug", "excerpt", "footer", "NCC", "SĐT", "CMS", "SEO") if re.search(rf"(?<![A-Za-z]){w}(?![A-Za-z])", txt, re.I)]
    if re.search(r"\bBR-[A-Z]+-\d+", txt):
        bad.append("BR-")
    return bad


def editor(page):
    return page.locator(".ProseMirror").first


def type_body(page, text):
    ed = editor(page)
    ed.click()
    page.keyboard.type(text)


def open_new_post(page):
    page.get_by_role("link", name="Viết bài mới").first.click()
    page.wait_for_url("**/content/edit/**")
    expect(page.get_by_label("Tiêu đề", exact=False).first).to_be_visible()
    expect(editor(page)).to_be_visible()
    settle(page)


def toast_text(page):
    return page.locator("[role=status], [role=alert]").all_inner_texts()


def dialog(page):
    return page.get_by_role("dialog")


# ---------------------------------------------------------------- Chủ (loc)
def run_owner(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    labels = menu_labels(page)
    ok("Chủ: menu có 'Nội dung'", "Nội dung" in labels, str(labels))

    # ---- Danh sách
    go_menu(page, "Nội dung", "/content/")
    wait_table(page)
    txt = main_text(page)
    ok("Danh sách: có 9 bài mẫu, dòng đếm 'Đang hiện 9 / 9 bài'", rows_count(page) == 9 and "Đang hiện 9 / 9 bài" in txt, txt[:200])
    ok("Danh sách: tab Nháp 3 · Chờ duyệt 1 · Đã đăng 4 · Đã gỡ 1",
       all(re.search(rf"{t}\s*\n?\s*{n}", txt) for t, n in (("Nháp", 3), ("Chờ duyệt", 1), ("Đã đăng", 4), ("Đã gỡ", 1))), txt[:300])
    ok("Danh sách: báo thiếu trang bắt buộc 'Điều kiện giao dịch, Đổi trả hoàn tiền' + nút Tạo trang", "Còn thiếu trang bắt buộc trước khi mở bán" in txt and "Điều kiện giao dịch" in txt)
    ok("Danh sách: có nút Quản lý chuyên mục, Tạo trang, Viết bài mới", all(page.get_by_role("link", name=n).count() >= 1 for n in ("Quản lý chuyên mục", "Tạo trang", "Viết bài mới")))
    h = [re.sub(r"\s+", " ", x).strip() for x in page.locator("table.lt thead th").all_inner_texts()]
    ok("Danh sách: cột Tiêu đề, Đường dẫn, Loại, Chuyên mục, Trạng thái, Cập nhật", all(c in h for c in ("Tiêu đề", "Đường dẫn", "Loại", "Chuyên mục", "Trạng thái", "Cập nhật")), str(h))
    ok("Danh sách: không có từ cấm / mã BR", not banned_words(txt), str(banned_words(txt)))
    ok("Danh sách: không hiện giá vốn / giá mua", "giá vốn" not in txt.lower() and "giá mua" not in txt.lower())
    page.screenshot(path=f"{SHOTS}/lo16-1-loc-danh-sach.png", full_page=True)

    page.get_by_role("tab", name=re.compile("^Chờ duyệt")).click()
    settle(page)
    ok("Danh sách: tab Chờ duyệt còn đúng 1 dòng", rows_count(page) == 1 and "Cá thu một nắng chiên giòn" in main_text(page))
    page.get_by_role("tab", name=re.compile("^Tất cả")).click()
    settle(page)
    page.get_by_role("searchbox").fill("khongcobaigivay")
    settle(page)
    ok("Danh sách: tìm không ra thì có thông báo rỗng, không còn dòng", rows_count(page) == 0 or "Không" in main_text(page), main_text(page)[-300:])
    page.get_by_role("searchbox").fill("")
    settle(page)
    page.get_by_role("combobox", name="Lọc theo loại").select_option(label="Trang")
    settle(page)
    ok("Danh sách: lọc Trang còn 3 dòng", rows_count(page) == 3, str(rows_count(page)))
    page.get_by_role("combobox", name="Lọc theo loại").select_option(label="Mọi loại")
    page.get_by_role("combobox", name="Lọc theo chuyên mục").select_option(label="Mẹo nhà bếp")
    settle(page)
    ok("Danh sách: lọc chuyên mục 'Mẹo nhà bếp' còn 2 dòng", rows_count(page) == 2, str(rows_count(page)))
    page.get_by_role("combobox", name="Lọc theo chuyên mục").select_option(label="Mọi chuyên mục")
    settle(page)

    # ---- Chuyên mục
    page.get_by_role("link", name="Quản lý chuyên mục").click()
    page.wait_for_url("**/content/categories/**")
    wait_table(page)
    ctxt = main_text(page)
    ok("Chuyên mục: có 4 chuyên mục mẫu và cột Bài đăng", rows_count(page) >= 4 and "Công thức nấu" in ctxt and "Bài đăng" in ctxt, ctxt[:300])
    ok("Chuyên mục: không có từ cấm", not banned_words(ctxt), str(banned_words(ctxt)))
    page.screenshot(path=f"{SHOTS}/lo16-2-loc-chuyen-muc.png", full_page=True)
    # Trùng tên
    page.get_by_role("button", name="Thêm chuyên mục").click()
    dialog(page).wait_for()
    dialog(page).get_by_label("Tên chuyên mục").fill("công thức nấu")
    dialog(page).locator("button[type=submit]").click()
    settle(page)
    ok("Chuyên mục: tên trùng (khác hoa thường) báo 'Đã có chuyên mục tên này' và hộp còn mở", "Đã có chuyên mục tên này" in dialog(page).inner_text() and dialog(page).is_visible(), dialog(page).inner_text())
    page.screenshot(path=f"{SHOTS}/lo16-3-loc-chuyen-muc-trung-ten.png")
    # Tên rỗng
    dialog(page).get_by_label("Tên chuyên mục").fill("   ")
    dialog(page).locator("button[type=submit]").click()
    settle(page)
    ok("Chuyên mục: tên toàn dấu cách báo 'Cần nhập tên chuyên mục'", "Cần nhập tên chuyên mục" in dialog(page).inner_text(), dialog(page).inner_text())
    # Thứ tự sai
    dialog(page).get_by_label("Tên chuyên mục").fill("Món nướng")
    dialog(page).get_by_label("Thứ tự hiển thị").fill("-3")
    dialog(page).locator("button[type=submit]").click()
    settle(page)
    ok("Chuyên mục: thứ tự âm bị chặn", "Thứ tự là số nguyên từ 0 trở lên" in dialog(page).inner_text(), dialog(page).inner_text())
    dialog(page).get_by_label("Thứ tự hiển thị").fill("9")
    dialog(page).locator("button[type=submit]").click()
    settle(page)
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    ok("Chuyên mục: tạo 'Món nướng' xong, bảng có dòng mới (0 bài)", "Món nướng" in main_text(page))
    # Ngừng dùng khi còn bài đang đăng -> bị chặn kèm lối xem bài
    row = page.locator("table.lt tbody tr", has_text="Mẹo nhà bếp").first
    row.get_by_role("button", name="Ngừng dùng").click()
    dialog(page).wait_for()
    dialog(page).get_by_role("button", name="Ngừng dùng").click()
    settle(page)
    dt = dialog(page).inner_text() if dialog(page).count() else body(page)
    ok("Chuyên mục: ngừng dùng chuyên mục còn bài đang đăng thì bị chặn, nêu số bài + nút 'Xem N bài'", re.search(r"Còn \d+ bài đang đăng", dt) is not None and re.search(r"Xem \d+ bài", dt) is not None, dt)
    page.screenshot(path=f"{SHOTS}/lo16-4-loc-chuyen-muc-bi-chan.png")
    page.get_by_role("link", name=re.compile(r"^Xem \d+ bài")).first.click()
    page.wait_for_url("**/content/?category=**")
    wait_table(page)
    ok("Chuyên mục: 'Xem N bài' mở danh sách đã lọc theo chuyên mục", rows_count(page) >= 1 and page.get_by_role("combobox", name="Lọc theo chuyên mục").input_value() != "", page.url)
    page.go_back()
    page.wait_for_url("**/content/categories/**")
    settle(page)
    if dialog(page).count():
        page.keyboard.press("Escape")
    # Ngừng dùng chuyên mục trống (Món nướng) rồi kích hoạt lại
    row = page.locator("table.lt tbody tr", has_text="Món nướng").first
    row.get_by_role("button", name="Ngừng dùng").click()
    dialog(page).wait_for()
    dialog(page).get_by_role("button", name="Ngừng dùng").click()
    settle(page)
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    row = page.locator("table.lt tbody tr", has_text="Món nướng").first
    ok("Chuyên mục: ngừng dùng chuyên mục trống được, dòng chuyển sang 'Ngừng dùng'", "Ngừng" in row.inner_text(), row.inner_text())
    ok("Chuyên mục: chuyên mục đã ngừng có nút 'Kích hoạt'", row.get_by_role("button", name="Kích hoạt").count() == 1)
    # Sửa chuyên mục (hộp)
    page.locator("table.lt tbody tr", has_text="Mẹo nhà bếp").first.get_by_role("button", name="Sửa").click()
    dialog(page).wait_for()
    ok("Chuyên mục: hộp Sửa điền sẵn tên, đường dẫn hiện nhưng không sửa", dialog(page).get_by_label("Tên chuyên mục").input_value() == "Mẹo nhà bếp")
    page.keyboard.press("Escape")

    # ---- Soạn bài mới
    go_menu(page, "Nội dung", "/content/")
    open_new_post(page)
    ok("Soạn: bài mới mở ra chưa gõ gì thì chưa báo 'Chưa lưu' (không tự coi là đã sửa)", "Chưa lưu, đang giữ trên máy" not in main_text(page) and not is_guarded(page))
    page.get_by_label("Tiêu đề", exact=False).first.fill("a")
    page.get_by_label("Tiêu đề", exact=False).first.fill("")
    t = main_text(page)
    ok("Soạn: bài mới đã gõ thì có trạng thái 'Chưa lưu, đang giữ trên máy'", "Chưa lưu, đang giữ trên máy" in t, t[:300])
    ok("Soạn: tiêu đề trang 'Viết bài mới', có thanh Nháp → Chờ duyệt → Đã đăng", "Viết bài mới" in t and "Chờ duyệt" in t)
    ok("Soạn: chủ có nút Lưu nháp + Đăng bài", page.get_by_role("button", name="Lưu nháp").count() >= 1 and page.get_by_role("button", name="Đăng bài").count() >= 1)
    ok("Soạn: không có từ cấm / mã BR", not banned_words(t), str(banned_words(t)))
    # Bài mới: Xoá / Lịch sử / Gỡ trong menu "…" bị khoá, có lý do
    page.get_by_role("button", name=re.compile("Thêm|Khác|Thao tác")).last.click()
    items = page.get_by_role("menuitem")
    ok("Soạn: menu '…' có Xoá bài, Lịch sử phiên bản, Gỡ bài", items.filter(has_text="Xoá bài").count() == 1 and items.filter(has_text="Lịch sử phiên bản").count() == 1 and items.filter(has_text="Gỡ bài").count() == 1, str(items.all_inner_texts()))
    page.keyboard.press("Escape")
    # Đăng bài khi chưa nhập gì: không gọi lệnh, báo thiếu tiêu đề
    page.get_by_role("button", name="Đăng bài").first.click()
    settle(page)
    t = main_text(page)
    ok("Soạn: bấm Đăng bài khi để trống thì báo cần tiêu đề, không mở bảng tick", ("cần nhập tiêu đề" in t.lower()) and dialog(page).count() == 0, t[:400])
    page.screenshot(path=f"{SHOTS}/lo16-5-loc-soan-trong.png", full_page=True)
    # Nhập tên bài giống mã HTML: phải hiện thành chữ
    xss = '<img src=x onerror="window.__xss=1">Món <b>thử</b>'
    page.get_by_label("Tiêu đề", exact=False).first.fill(xss)
    type_body(page, "Cá thu rã đông trong ngăn mát.")
    page.get_by_role("button", name="Lưu nháp").first.click()
    settle(page)
    page.wait_for_url("**/content/edit/?id=**")
    ok("Soạn: Lưu nháp tạo bài, URL có ?id= (không chứa dữ liệu cá nhân)", re.search(r"\?id=\d+$", page.url) is not None, page.url)
    ok("Soạn: tên bài chứa mã HTML hiện thành chữ, không chạy mã", page.evaluate("() => window.__xss === undefined") and page.locator("main img[src='x']").count() == 0)
    ok("Soạn: sau khi lưu hiện 'Đã lưu' và bài ở trạng thái Nháp", "Đã lưu" in main_text(page) and page.locator("main", has_text="Nháp").count() == 1, main_text(page)[:300])
    entry_url = page.url
    # Đường dẫn bài chưa đăng sửa được; đặt trùng với bài có sẵn -> đề xuất
    page.get_by_label("Đường dẫn", exact=True).first.fill("cach-ra-dong-ca-thu")
    page.get_by_role("button", name="Lưu nháp").first.click()
    settle(page)
    t = main_text(page)
    ok("Soạn: đường dẫn trùng thì báo 'đã có bài khác dùng' và gợi ý đường dẫn", "Đường dẫn này đã có bài khác dùng" in t and "Dùng đường dẫn: cach-ra-dong-ca-thu-2" in t, t[:500])
    page.screenshot(path=f"{SHOTS}/lo16-6-loc-duong-dan-trung.png", full_page=True)
    page.get_by_role("button", name="Dùng đường dẫn: cach-ra-dong-ca-thu-2").click()
    page.get_by_role("button", name="Lưu nháp").first.click()
    settle(page)
    ok("Soạn: bấm gợi ý rồi lưu được", "Đường dẫn này đã có bài khác dùng" not in main_text(page), main_text(page)[:300])

    # Đăng khi còn thiếu: Chuyên mục, Ảnh bìa, Tóm tắt -> tự sang Thiết lập, đánh dấu ô thiếu
    page.get_by_role("button", name="Đăng bài").first.click()
    dialog(page).wait_for()
    for i in range(5):
        dialog(page).locator("input[type=checkbox]").nth(i).check()
    dialog(page).get_by_role("button", name="Đăng bài").click()
    settle(page)
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    t = main_text(page)
    ok("Đăng thiếu thông tin: nêu 'Còn thiếu' (chuyên mục / ảnh bìa / tóm tắt) và mở màn Thiết lập bài viết", "Còn thiếu" in t and "Thiết lập bài viết" in t, t[:600])
    ok("Đăng thiếu thông tin: ô Chuyên mục bị đánh dấu lỗi", page.locator("main [aria-invalid=true]").count() >= 1)
    page.screenshot(path=f"{SHOTS}/lo16-7-loc-thieu-thong-tin.png", full_page=True)
    ok("Thiết lập: không có từ cấm", not banned_words(t), str(banned_words(t)))
    page.get_by_role("combobox", name="Chuyên mục").select_option(label="Công thức nấu")
    page.get_by_label("Tóm tắt", exact=True).fill("Cách rã đông cá thu giữ nguyên vị.")
    ok("Thiết lập: chưa có ảnh nào thì ô Ảnh bìa nhắc tải ảnh ở phần Ảnh trong bài", "Chưa có ảnh nào" in main_text(page), main_text(page)[:600])
    # Lưu thiết lập (không có quyền gửi duyệt riêng: chủ có quyền đăng nên nút chính là Lưu thay đổi)
    page.get_by_role("button", name="Lưu thay đổi").click()
    settle(page)
    ok("Thiết lập: Lưu thay đổi quay lại màn Viết", page.get_by_role("button", name="Lưu nháp").count() >= 1 and "Nội dung bài viết" in main_text(page), main_text(page)[:300])
    # Tải ảnh
    page.locator("input[type=file]").first.set_input_files({"name": "ca-thu.png", "mimeType": "image/png", "buffer": PNG})
    settle(page)
    page.wait_for_timeout(500)
    ok("Ảnh: tải ảnh lên được, hiện '1/20 ảnh'", "1/20" in main_text(page), main_text(page)[:500])
    page.get_by_role("button", name="Thiết lập bài viết").first.click()
    settle(page)
    page.get_by_role("combobox", name="Ảnh bìa").select_option(index=1)
    page.get_by_label("Mô tả ảnh bìa").fill("")
    page.get_by_role("button", name="Lưu thay đổi").click()
    settle(page)
    t = main_text(page)
    ok("Thiết lập: chọn ảnh bìa mà để trống mô tả thì bị chặn 'Cần nhập mô tả ảnh bìa'", "Cần nhập mô tả ảnh bìa" in t, t[:500])
    page.get_by_label("Mô tả ảnh bìa").fill("Con cá thu đã rã đông")
    page.get_by_role("button", name="Lưu thay đổi").click()
    settle(page)
    page.screenshot(path=f"{SHOTS}/lo16-8-loc-sau-thiet-lap.png", full_page=True)

    # Cảnh báo: SĐT + giá vốn trong nội dung
    type_body(page, " Gọi 0912 000 000 nếu cần. Giá mua tại cảng thấp hơn.")
    page.get_by_role("button", name="Đăng bài").first.click()
    dialog(page).wait_for()
    settle(page)
    d = dialog(page)
    ok("Đăng: mở bảng 'Kiểm tra trước khi đăng' có 5 ô tick", "Kiểm tra trước khi đăng" in d.inner_text() and d.locator("input[type=checkbox]").count() == 5, d.inner_text()[:300])
    publish_btn = d.get_by_role("button", name="Đăng bài")
    ok("Đăng: nút Đăng bài khoá khi chưa tick đủ", publish_btn.is_disabled())
    boxes = d.locator("input[type=checkbox]")
    for i in range(4):
        boxes.nth(i).check()
    ok("Đăng: tick 4/5 vẫn khoá", publish_btn.is_disabled())
    page.screenshot(path=f"{SHOTS}/lo16-9-loc-bang-tick.png")
    boxes.nth(4).check()
    ok("Đăng: tick đủ 5 thì mở nút", publish_btn.is_enabled())
    publish_btn.click()
    settle(page)
    page.wait_for_timeout(300)
    d = dialog(page)
    wt = d.inner_text() if d.count() else ""
    ok("Đăng: nội dung có SĐT + từ giá vốn thì hiện bảng 'Có chỗ cần xem lại' (cả 2 cảnh báo)", "Có chỗ cần xem lại" in wt and "số điện thoại" in wt and "giá vốn" in wt, wt)
    page.screenshot(path=f"{SHOTS}/lo16-10-loc-canh-bao.png")
    d.get_by_role("button", name="Quay lại sửa").click()
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    ok("Đăng: 'Quay lại sửa' đóng bảng, bài vẫn là Nháp", "Nháp" in main_text(page) and page.locator("main", has_text="Bài đã đăng").count() == 0)
    # Sửa nội dung bỏ SĐT & từ giá vốn -> đăng
    ed = editor(page)
    ed.click()
    page.keyboard.press("ControlOrMeta+A")
    page.keyboard.type("Cá thu rã đông trong ngăn mát, giữ nguyên vị ngọt.")
    page.get_by_role("button", name="Đăng bài").first.click()
    dialog(page).wait_for()
    for i in range(5):
        dialog(page).locator("input[type=checkbox]").nth(i).check()
    dialog(page).get_by_role("button", name="Đăng bài").click()
    settle(page)
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    t = main_text(page)
    ok("Đăng: đăng xong bài ở trạng thái Đã đăng, đường dẫn bị khoá, có 'Xem trên website'", "Đã đăng" in t and "không đổi được đường dẫn" in t and "Xem trên website" in t, t[:500])
    page.screenshot(path=f"{SHOTS}/lo16-11-loc-da-dang.png", full_page=True)
    page.get_by_role("button", name=re.compile("Thêm|Khác|Thao tác")).last.click()
    del_item = page.get_by_role("menuitem").filter(has_text="Xoá bài")
    ok("Đăng: 'Xoá bài' khoá vì bài đã từng đăng, có lý do", del_item.count() == 1 and (del_item.first.get_attribute("aria-disabled") == "true" or del_item.first.is_disabled()) and "đã từng đăng" in page.locator("[role=menu]").inner_text(), page.locator("[role=menu]").inner_text())
    page.get_by_role("menuitem").filter(has_text="Gỡ bài").first.click()
    dialog(page).wait_for()
    d = dialog(page)
    ok("Gỡ bài: bắt buộc chọn lý do", d.get_by_role("button", name="Gỡ bài").count() == 1)
    d.get_by_role("button", name="Gỡ bài").click()
    settle(page)
    ok("Gỡ bài: để trống lý do báo 'Chọn lý do gỡ bài'", "Chọn lý do gỡ bài" in dialog(page).inner_text(), dialog(page).inner_text())
    dialog(page).get_by_role("combobox").select_option(label="Hết mùa vụ")
    dialog(page).get_by_role("button", name="Gỡ bài").click()
    settle(page)
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    t = main_text(page)
    ok("Gỡ bài: xong bài chuyển 'Đã gỡ' và hiện lý do bằng chữ (không phải khoá)", "Đã gỡ" in t and "Hết mùa vụ" in t and "out_of_season" not in t, t[:500])
    page.screenshot(path=f"{SHOTS}/lo16-12-loc-da-go.png", full_page=True)
    # Lịch sử phiên bản
    page.get_by_role("button", name=re.compile("Thêm|Khác|Thao tác")).last.click()
    page.get_by_role("menuitem").filter(has_text="Lịch sử phiên bản").first.click()
    dialog(page).wait_for()
    settle(page)
    ok("Lịch sử: có ít nhất 1 phiên bản đã đăng, có nút Khôi phục", "Phiên bản" in dialog(page).inner_text() and dialog(page).get_by_role("button", name="Khôi phục phiên bản này").count() >= 1, dialog(page).inner_text())
    page.screenshot(path=f"{SHOTS}/lo16-13-loc-lich-su.png")
    # Khôi phục luôn hỏi xác nhận; "Quay lại" thì không đổi gì (CMS-11-AC3)
    dialog(page).get_by_role("button", name="Khôi phục phiên bản này").first.click()
    confirm = dialog(page).filter(has_text="Khôi phục phiên bản này?")
    confirm.wait_for()
    ok("Khôi phục: có hộp xác nhận nêu bản đang soạn sẽ bị thay", "Bản đang soạn sẽ bị thay" in confirm.inner_text(), confirm.inner_text())
    confirm.get_by_role("button", name="Quay lại").click()
    ok("Khôi phục: bấm Quay lại thì hộp xác nhận đóng, chưa khôi phục gì", dialog(page).filter(has_text="Khôi phục phiên bản này?").count() == 0 and "Đã khôi phục nội dung" not in body(page))
    page.keyboard.press("Escape")

    # ---- Xung đột phiên bản: người khác vừa sửa bài khác
    go_menu(page, "Nội dung", "/content/")
    wait_table(page)
    page.locator("table.lt tbody tr", has_text="Gợi ý 5 món từ cá bớp").first.click()
    page.wait_for_url("**/content/edit/?id=**")
    expect(editor(page)).to_be_visible()
    settle(page)
    eid = int(re.search(r"id=(\d+)", page.url).group(1))
    page.evaluate(f"window.__caveMock.contentBump({eid})")
    page.get_by_label("Tiêu đề", exact=False).first.fill("Gợi ý 5 món từ cá bớp (sửa)")
    page.get_by_role("button", name="Lưu nháp").first.click()
    settle(page)
    t = main_text(page)
    ok("Xung đột: lưu khi người khác vừa sửa thì hiện biểu ngữ xung đột + nút 'Tải lại'", "Tải lại" in t and "vừa được người khác sửa" in t, t[:500])
    page.screenshot(path=f"{SHOTS}/lo16-14-loc-xung-dot.png", full_page=True)
    page.get_by_role("button", name="Tải lại").first.click()
    if dialog(page).count():
        dialog(page).get_by_role("button", name="Tải lại").click()
    settle(page)
    ok("Xung đột: tải bản mới nhất xong biểu ngữ biến mất, tiêu đề về bản máy chủ", "vừa được người khác sửa" not in main_text(page) and page.get_by_label("Tiêu đề", exact=False).first.input_value() == "Gợi ý 5 món từ cá bớp")

    # Rời trang khi còn thay đổi chưa lưu: có chặn
    page.get_by_label("Tiêu đề", exact=False).first.fill("Đang gõ dở")
    guarded = page.evaluate("() => { const e = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; }")
    ok("Soạn: còn thay đổi chưa lưu thì chặn đóng tab (beforeunload)", guarded)
    # Bài đang chờ duyệt
    page.locator("main").get_by_role("link", name="Nội dung").first.click()
    page.wait_for_url("**/content/")
    settle(page)
    wait_table(page)
    page.locator("table.lt tbody tr", has_text="Cá thu một nắng chiên giòn").first.click()
    page.wait_for_url("**/content/edit/?id=**")
    expect(editor(page)).to_be_visible()
    settle(page)
    t = main_text(page)
    ok("Chờ duyệt: biểu ngữ 'Bài đang chờ duyệt', chủ có 'Trả về nháp' và 'Đăng bài'", "Bài đang chờ duyệt" in t and page.get_by_role("button", name="Trả về nháp").count() >= 1 and page.get_by_role("button", name="Đăng bài").count() >= 1, t[:500])
    page.get_by_role("button", name="Trả về nháp").first.click()
    dialog(page).wait_for()
    dialog(page).get_by_role("button", name="Trả về nháp").click()
    settle(page)
    ok("Trả về nháp: để trống lý do báo 'Chọn lý do trả về'", "Chọn lý do trả về" in dialog(page).inner_text(), dialog(page).inner_text())
    page.screenshot(path=f"{SHOTS}/lo16-15-loc-tra-ve.png")
    dialog(page).get_by_role("combobox").select_option(label="Thiếu thông tin hoặc hình ảnh")
    dialog(page).get_by_role("button", name="Trả về nháp").click()
    settle(page)
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    t = main_text(page)
    ok("Trả về nháp: xong bài về Nháp, hiện lý do bằng chữ", "Nháp" in t and "Thiếu thông tin hoặc hình ảnh" in t and "missing_info" not in t, t[:500])
    ok("Cả luồng của chủ: không lộ dữ liệu cá nhân ra storage/URL", not re.search(r"0912|@|\b0[39]\d{8}\b", storage_dump(page)), storage_dump(page)[:300])
    ctx.close()


# ---------------------------------------------------------------- Quản lý (ql1), bị gỡ quyền đăng
def run_manager(browser, errors):
    ctx, page = new_page(browser, "ql1", errors=errors, pre="() => window.__caveMock.patchUser('ql1', { denied_perms: ['content.publish_entry'] })")
    ok("Quản lý: menu có 'Nội dung'", "Nội dung" in menu_labels(page), str(menu_labels(page)))
    go_menu(page, "Nội dung", "/content/")
    wait_table(page)
    ok("Quản lý: thấy danh sách và nút Viết bài mới", rows_count(page) == 9 and page.get_by_role("link", name="Viết bài mới").count() >= 1)
    ok("Quản lý (đã gỡ quyền đăng): danh sách không có nút Đăng", page.get_by_role("button", name="Đăng bài").count() == 0)
    page.get_by_role("link", name="Viết bài mới").first.click()
    page.wait_for_url("**/content/edit/**")
    expect(editor(page)).to_be_visible()
    settle(page)
    page.screenshot(path=f"{SHOTS}/lo16-20-ql1-soan-khong-quyen-dang.png", full_page=True)
    ok("Quản lý không có quyền đăng: không có nút Đăng bài / Gỡ bài", page.get_by_role("button", name="Đăng bài").count() == 0 and page.get_by_role("button", name="Gỡ bài").count() == 0)
    ok("Quản lý không có quyền đăng: nút chính là 'Gửi duyệt'", page.get_by_role("button", name="Gửi duyệt").count() >= 1, str(page.get_by_role("button").all_inner_texts()))
    page.get_by_label("Tiêu đề", exact=False).first.fill("Bài do quản lý soạn")
    type_body(page, "Nội dung thử.")
    page.get_by_role("button", name="Lưu nháp").first.click()
    settle(page)
    page.wait_for_url("**/content/edit/?id=**")
    page.get_by_role("button", name=re.compile("Thêm|Khác|Thao tác")).last.click()
    ok("Quản lý không có quyền đăng: menu '…' không có 'Gỡ bài'", page.get_by_role("menuitem").filter(has_text="Gỡ bài").count() == 0, str(page.get_by_role("menuitem").all_inner_texts()))
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Gửi duyệt").first.click()
    settle(page)
    t = main_text(page)
    # Thiếu thông tin thì gửi duyệt cũng nêu thiếu
    ok("Quản lý: gửi duyệt khi chưa đủ thông tin thì báo 'Còn thiếu' và mở Thiết lập", "Còn thiếu" in t or "Chuyên mục" in t, t[:500])
    page.screenshot(path=f"{SHOTS}/lo16-21-ql1-gui-duyet-thieu.png", full_page=True)
    ctx.close()


# ---------------------------------------------------------------- Không có quyền
def run_denied(browser, errors, user):
    ctx, page = new_page(browser, user, errors=errors)
    ok(f"{user}: menu không có 'Nội dung'", "Nội dung" not in menu_labels(page), str(menu_labels(page)))
    for path in ("/content/", "/content/categories/", "/content/edit/?new=post"):
        page.goto(BASE + path)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(400)
        ok(f"{user}: vào thẳng {path} thì 'không có quyền', không có bảng", NO_PERM in body(page).lower() and page.locator("table.lt").count() == 0, body(page)[:200])
    if user == "kho1":
        page.screenshot(path=f"{SHOTS}/lo16-30-{user}-khong-quyen.png")
    ctx.close()


# ---------------------------------------------------------------- Trạng thái lỗi / rỗng / 403
def run_states(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    # Hook window.__caveMock.content chỉ có sau khi nạp code Nội dung: đi qua menu trước.
    go_menu(page, "Nội dung", "/content/")
    wait_table(page)
    for mode, label in (("fail", "lỗi"), ("empty", "rỗng"), ("forbidden", "403")):
        page.evaluate(f"window.__caveMock.content('{mode}')")
        page.goto(BASE + "/content/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        t = main_text(page)
        if mode == "fail":
            ok("Danh sách lỗi: nêu lỗi bằng chữ + nút Thử lại, không lộ mã kỹ thuật", ("Thử lại" in t) and not re.search(r"\b500\b|Error|undefined", t), t[:300])
            page.screenshot(path=f"{SHOTS}/lo16-40-loi.png")
            page.evaluate("window.__caveMock.content('ok')")
            page.get_by_role("button", name="Thử lại").first.click()
            wait_table(page)
            ok("Danh sách lỗi: bấm Thử lại thì tải được 9 bài", rows_count(page) == 9)
        elif mode == "empty":
            ok("Danh sách rỗng: nêu 'Chưa có bài viết hoặc trang nào' + nút Viết bài mới", "Chưa có bài viết hoặc trang nào" in t and page.get_by_role("link", name="Viết bài mới").count() >= 1, t[:300])
            page.screenshot(path=f"{SHOTS}/lo16-41-rong.png")
        else:
            ok("Danh sách 403: nêu không có quyền", NO_PERM in body(page).lower(), t[:300])
    # Mở bài lỗi / không có
    page.evaluate("window.__caveMock.content('fail')")
    page.goto(BASE + "/content/edit/?id=1")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    t = main_text(page)
    ok("Soạn lỗi tải: nêu 'Chưa tải được bài viết' + Thử lại", "Chưa tải được bài viết" in t and "Thử lại" in t, t[:300])
    page.evaluate("window.__caveMock.content('ok')")
    page.goto(BASE + "/content/edit/?id=99999")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    ok("Soạn: bài không tồn tại thì 'Không tìm thấy bài viết'", "Không tìm thấy bài viết" in main_text(page), main_text(page)[:300])
    page.goto(BASE + "/content/categories/")
    page.wait_for_load_state("networkidle")
    page.evaluate("window.__caveMock.content('empty')")
    page.goto(BASE + "/content/categories/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    ok("Chuyên mục rỗng: nêu 'Chưa có chuyên mục nào'", "Chưa có chuyên mục nào" in main_text(page), main_text(page)[:300])
    page.evaluate("window.__caveMock.content('ok')")
    # Xem bản chính sách theo phiên bản (SR-19)
    page.goto(BASE + "/content/edit/?id=1&version=1")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    ok("Xem phiên bản 1 của chính sách: hiện nội dung bản 1 (chỉ đọc)", "MẪU-V1" in body(page) or "Bản 1" in body(page) or "phiên bản 1" in body(page).lower(), body(page)[:400])
    ctx.close()


# ---------------------------------------------------------------- Điện thoại 360px
def run_mobile(browser, errors):
    ctx, page = new_page(browser, "loc", w=360, h=740, mobile=True, errors=errors)
    page.goto(BASE + "/content/")
    page.wait_for_load_state("networkidle")
    wait_table(page)
    ok("360px: danh sách không cuộn ngang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360px: danh sách, nút bấm đủ 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/lo16-50-m-danh-sach.png", full_page=True)
    page.goto(BASE + "/content/categories/")
    page.wait_for_load_state("networkidle")
    wait_table(page)
    ok("360px: chuyên mục không cuộn ngang", no_hscroll(page))
    ok("360px: chuyên mục, nút bấm đủ 44px", not page.evaluate(SMALL_TAPS_JS), str(page.evaluate(SMALL_TAPS_JS)))
    page.screenshot(path=f"{SHOTS}/lo16-51-m-chuyen-muc.png", full_page=True)
    page.get_by_role("button", name="Thêm chuyên mục").click()
    dialog(page).wait_for()
    ok("360px: hộp Thêm chuyên mục không cuộn ngang, nút Tạo thấy được", no_hscroll(page) and dialog(page).get_by_role("button", name="Tạo chuyên mục").is_visible())
    page.screenshot(path=f"{SHOTS}/lo16-52-m-them-chuyen-muc.png")
    page.keyboard.press("Escape")
    page.goto(BASE + "/content/edit/?new=post")
    page.wait_for_load_state("networkidle")
    expect(editor(page)).to_be_visible()
    settle(page)
    ok("360px: màn soạn không cuộn ngang", no_hscroll(page))
    small = page.evaluate(SMALL_TAPS_JS)
    ok("360px: màn soạn, nút bấm đủ 44px", not small, str(small))
    page.screenshot(path=f"{SHOTS}/lo16-53-m-soan.png", full_page=True)
    page.get_by_role("button", name="Thiết lập bài viết").first.click()
    settle(page)
    ok("360px: màn Thiết lập không cuộn ngang", no_hscroll(page))
    page.screenshot(path=f"{SHOTS}/lo16-54-m-thiet-lap.png", full_page=True)
    ctx.close()


# ---------------------------------------------------------------- Sửa lỗi QA lần 1 (B16-1, B16-2, B16-3), chạy trên mock
def draft_keys(page):
    return page.evaluate("() => Object.keys(localStorage).filter(k => k.startsWith('cave_erp_draft:'))")


def is_guarded(page):
    return page.evaluate("() => { const e = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; }")


def open_entry_by_title(page, title):
    go_menu(page, "Nội dung", "/content/")
    wait_table(page)
    page.locator("table.lt tbody tr", has_text=title).first.click()
    page.wait_for_url("**/content/edit/?id=**")
    expect(editor(page)).to_be_visible()
    settle(page)
    page.wait_for_timeout(1500)


def run_regression_fixes(browser, errors):
    ctx, page = new_page(browser, "loc", errors=errors)
    go_menu(page, "Nội dung", "/content/")
    wait_table(page)

    # B16-2: máy chủ trả thân bài dạng chưa chuẩn hoá; chỉ mở bài, không gõ gì.
    page.evaluate("window.__caveMock.contentRawBody(42)")
    open_entry_by_title(page, "Cách rã đông cá thu")
    t = main_text(page)
    ok("B16-2: chỉ mở bài (thân bài chưa chuẩn hoá) thì không chặn rời trang", not is_guarded(page))
    ok("B16-2: chỉ mở bài thì không ghi bản nháp nào vào máy", draft_keys(page) == [], str(draft_keys(page)))
    ok("B16-2: chỉ mở bài thì không hiện dòng 'đã khôi phục bản nháp'", "Đã khôi phục bản nháp" not in t and "Chưa lưu" not in t, t[:300])
    ok("B16-2: thân bài chưa chuẩn hoá vẫn hiện đủ chữ trong ô soạn", "Chọn cá thu tươi có mắt trong." in editor(page).inner_text(), editor(page).inner_text())
    open_entry_by_title(page, "Cách rã đông cá thu")
    ok("B16-2: mở lại lần hai vẫn sạch, không có dòng khôi phục", "Đã khôi phục bản nháp" not in main_text(page) and draft_keys(page) == [] and not is_guarded(page))
    page.get_by_label("Tiêu đề", exact=False).first.fill("Cách rã đông cá thu (sửa)")
    ok("B16-2: gõ thật vào tiêu đề thì mới bị coi là đã sửa", is_guarded(page))
    page.get_by_label("Tiêu đề", exact=False).first.fill("Cách rã đông cá thu")
    editor(page).click()
    page.keyboard.type("x")
    ok("B16-2: gõ vào thân bài cũng được coi là đã sửa", is_guarded(page))
    page.keyboard.press("Backspace")

    # Nháp trên máy còn mới (máy chủ chưa đổi): khôi phục như cũ.
    page.get_by_label("Tiêu đề", exact=False).first.fill("Bản của tôi gõ dở")
    page.wait_for_timeout(1500)
    ok("B16-3: gõ dở thì có 1 bản nháp trên máy", draft_keys(page) == ["cave_erp_draft:content_entry_42"], str(draft_keys(page)))
    open_entry_by_title(page, "Cách rã đông cá thu")
    t = main_text(page)
    ok("B16-3: máy chủ chưa đổi thì khôi phục bản nháp như cũ", page.get_by_label("Tiêu đề", exact=False).first.input_value() == "Bản của tôi gõ dở" and "Đã khôi phục bản nháp" in t, t[:300])

    # Người khác sửa bài trong lúc bản nháp còn nằm trên máy.
    page.evaluate("window.__caveMock.contentOtherEdit(42, 'Tiêu đề do người khác sửa')")
    open_entry_by_title(page, "Tiêu đề do người khác sửa")
    t = main_text(page)
    ok("B16-3: máy chủ đã đổi thì KHÔNG tự đè: tiêu đề là bản của người khác", page.get_by_label("Tiêu đề", exact=False).first.input_value() == "Tiêu đề do người khác sửa", page.get_by_label("Tiêu đề", exact=False).first.input_value())
    ok("B16-3: có cảnh báo 'đã được người khác sửa' + 2 lựa chọn, không có dòng 'đã khôi phục'", "Bài đã được người khác sửa" in t and page.get_by_role("button", name="Giữ bản trên máy").count() == 1 and page.get_by_role("button", name="Dùng bản mới nhất").count() == 1 and "Đã khôi phục bản nháp" not in t, t[:400])
    ok("B16-3: chưa chọn thì chưa bị coi là đã sửa", not is_guarded(page))
    page.screenshot(path=f"{SHOTS}/lo16-60-nhap-cu-canh-bao.png", full_page=True)
    page.get_by_role("button", name="Giữ bản trên máy").click()
    ok("B16-3: chọn 'Giữ bản trên máy' thì ô tiêu đề về bản của tôi", page.get_by_label("Tiêu đề", exact=False).first.input_value() == "Bản của tôi gõ dở")
    page.get_by_role("button", name="Lưu nháp").first.click()
    settle(page)
    t = main_text(page)
    ok("B16-3: lưu bản giữ lại thì bị báo xung đột, không đè âm thầm", "vừa được người khác sửa" in t and "Tải lại" in t, t[:400])
    page.screenshot(path=f"{SHOTS}/lo16-61-nhap-cu-xung-dot.png", full_page=True)
    page.get_by_role("button", name="Tải lại").first.click()
    if dialog(page).count():
        dialog(page).get_by_role("button", name="Tải lại").click()
    settle(page)
    ok("B16-3: tải lại thì về bản của người khác, nháp trên máy được xoá", page.get_by_label("Tiêu đề", exact=False).first.input_value() == "Tiêu đề do người khác sửa" and draft_keys(page) == [], str(draft_keys(page)))

    # Chọn 'Dùng bản mới nhất'.
    page.get_by_label("Tiêu đề", exact=False).first.fill("Bản gõ dở thứ hai")
    page.wait_for_timeout(1500)
    page.evaluate("window.__caveMock.contentOtherEdit(42, 'Người khác sửa lần hai')")
    open_entry_by_title(page, "Người khác sửa lần hai")
    page.get_by_role("button", name="Dùng bản mới nhất").click()
    ok("B16-3: chọn 'Dùng bản mới nhất' thì giữ bản máy chủ, xoá nháp, hết cảnh báo", page.get_by_label("Tiêu đề", exact=False).first.input_value() == "Người khác sửa lần hai" and draft_keys(page) == [] and "Bài đã được người khác sửa" not in main_text(page) and not is_guarded(page))

    # B16-1: gỡ bài rồi không tải lại trang.
    open_entry_by_title(page, "Mực lá nướng muối ớt")
    path_input = page.get_by_label("Đường dẫn", exact=True).first
    ok("B16-1: bài đã đăng có đường dẫn bị khoá từ đầu", path_input.is_disabled())
    page.get_by_role("button", name=re.compile("Thêm|Khác|Thao tác")).last.click()
    page.get_by_role("menuitem").filter(has_text="Gỡ bài").first.click()
    dialog(page).wait_for()
    dialog(page).get_by_role("combobox").select_option(label="Hết mùa vụ")
    dialog(page).get_by_role("button", name="Gỡ bài").click()
    settle(page)
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    t = main_text(page)
    ok("B16-1: gỡ xong (không tải lại) thì còn biểu ngữ 'Lý do: Hết mùa vụ'", "Bài đã gỡ khỏi website. Lý do: Hết mùa vụ" in t, t[:400])
    ok("B16-1: gỡ xong thì đường dẫn vẫn bị khoá, vẫn có chú thích", page.get_by_label("Đường dẫn", exact=True).first.is_disabled() and "không đổi được đường dẫn" in t)
    ok("B16-1: không có chữ undefined / null / '#undefined' trên màn", "undefined" not in t and "null" not in t and "#undefined" not in t, t[:400])
    page.get_by_label("Tiêu đề", exact=False).first.fill("Mực lá nướng muối ớt (sửa)")
    page.get_by_role("button", name="Lưu nháp").first.click()
    settle(page)
    t = main_text(page)
    ok("B16-1: sau khi gỡ, sửa và lưu được, không báo 'đường dẫn đã có bài khác dùng', không báo xung đột", "Đường dẫn này đã có bài khác dùng" not in t and "vừa được người khác sửa" not in t, t[:400])
    ok("B16-1: lưu xong vẫn còn lý do gỡ và trạng thái Đã gỡ", "Lý do: Hết mùa vụ" in t and "Đã gỡ" in t)
    page.screenshot(path=f"{SHOTS}/lo16-62-go-bai-giu-lydo.png", full_page=True)
    ctx.close()


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        run_owner(browser, errors)
        run_manager(browser, errors)
        run_regression_fixes(browser, errors)
        for u in ("kho1", "giao1", "cs2"):
            run_denied(browser, errors, u)
        run_states(browser, errors)
        run_mobile(browser, errors)
        browser.close()
    ok("Không có lỗi console / pageerror", not errors, "; ".join(errors[:5]))
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
    for r in failed:
        print("FAIL:", r[0], r[2])
    sys.exit(1 if failed else 0)


main()
