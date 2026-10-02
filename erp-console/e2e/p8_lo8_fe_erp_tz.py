# P8 Lô 8 — SR-25 (ERP): tiền VNĐ "x.xxx đ" (UI-RULES §1.6, đổi từ ₫ ở ERP theo design Lô 1), ngày giờ luôn theo giờ Việt Nam (GMT+7) bất kể múi giờ trình duyệt.
# Mock (NEXT_PUBLIC_USE_MOCK=1), dữ liệu giả. Đồng hồ trình duyệt CỐ ĐỊNH ở 2026-09-30T17:30:00Z = 00:30 ngày 01/10 giờ VN
# (qua nửa đêm VN, còn ở New York/Pago Pago vẫn là 30/09) nên giờ hiển thị đúng/sai phân biệt được rõ.
# Chạy:
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out <thư-mục-out-riêng> && (cd <thư-mục-out-riêng> && python3 -m http.server 3219 --bind 127.0.0.1 &)
#   BASE=http://127.0.0.1:3219 SHOTS=<thư mục ảnh> python3 e2e/p8_lo8_fe_erp_tz.py      # tắt server rồi build lại bản thật
import os
import re

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3201")
SHOTS = os.environ.get("SHOTS", "/tmp")
FIXED = "2026-09-30T17:30:00Z"
TZS = ["America/New_York", "UTC", "Pacific/Pago_Pago", "Asia/Ho_Chi_Minh"]  # cuối = mốc đối chiếu (giờ máy = giờ VN)
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


def new_ctx(browser, tz, w=1280, h=900):
    ctx = browser.new_context(viewport={"width": w, "height": h}, timezone_id=tz, locale="vi-VN", reduced_motion="reduce")
    ctx.clock.set_fixed_time(FIXED)
    return ctx


def goto(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)


TIME_TOKENS = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}|\d{2}/\d{2} \d{2}:\d{2}|(?:Cập nhật|Tới|Trả tiền:|Trả tiền lúc|Hẹn gọi lại) \d{2}:\d{2}|Hôm nay|Hôm qua")


def time_tokens(text):
    return TIME_TOKENS.findall(text)


def money_bad(text):
    """Số tiền sai kiểu: dính liền 4+ chữ số trước đ (thiếu dấu chấm), (chữ BE dựng sẵn như nhãn nhật ký vẫn có thể mang ký hiệu ₫: không tính là lỗi)."""
    return re.findall(r"\d{4,}\s?[đ₫](?!\w)", text)


def money_good(text):
    return re.findall(r"\d{1,3}(?:\.\d{3})+ đ(?!\w)", text)


def collect(browser, tz):
    """Trả về dict văn bản các màn (Tổng quan, Đơn + chi tiết, Giao hàng, Lô, Sổ nhập xuất, chi tiết lô, CSKH) dưới múi giờ `tz`."""
    out = {}
    ctx = new_ctx(browser, tz)
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    login(page, "loc")
    goto(page, "/overview/")
    out["overview"] = page.inner_text("body")
    if tz == "America/New_York":
        page.screenshot(path=f"{SHOTS}/lo8-erp-1-tong-quan-ny.png")
    goto(page, "/orders/")
    out["orders"] = page.inner_text("body")
    # ERP theo design Lô 3: chi tiết đơn là trang riêng (/orders/detail/?id=…), không còn hộp thoại
    page.locator("table.lt tbody tr.lt-click").first.click()
    page.wait_for_url("**/orders/detail/**", timeout=10_000)
    dlg = page.locator("main")
    dlg.wait_for(timeout=10_000)
    page.wait_for_timeout(900)
    out["order_detail"] = dlg.inner_text()
    if tz == "America/New_York":
        page.screenshot(path=f"{SHOTS}/lo8-erp-2-don-chi-tiet-ny.png")
    goto(page, "/deliveries/")
    out["deliveries"] = page.inner_text("body")
    # ERP theo design Lô 4: chi tiết phiếu giao là trang riêng (/deliveries/detail/?id=…), không còn hộp thoại
    page.locator("table.lt tbody tr.lt-click").first.click()
    page.wait_for_url("**/deliveries/detail/**", timeout=10_000)
    d2 = page.locator("main")
    d2.wait_for(timeout=10_000)
    page.wait_for_timeout(800)
    out["delivery_detail"] = d2.inner_text()
    goto(page, "/inventory/")
    out["inventory"] = page.inner_text("body")
    if tz == "America/New_York":
        page.screenshot(path=f"{SHOTS}/lo8-erp-3-lo-ny.png")
    # Màn danh sách mới không còn chip "Cập nhật hh:mm" (ERP theo design Lô 7); ý kiểm "giờ hiển thị = giờ VN" của Lô giờ chuyển sang
    # (a) cột "Thời gian" của Sổ nhập xuất, (b) dòng nhập xuất MỚI GHI trên trang chi tiết lô: mock đóng dấu Date.now() (đồng hồ cố định
    # 00:30 giờ VN), nên dòng đó phải hiện đúng "01/10/2026 00:30" dù máy ở múi giờ nào.
    goto(page, "/ledger/")
    page.wait_for_function("() => document.querySelectorAll('table.lt tr.lt-skel').length === 0")
    out["ledger"] = page.inner_text("body")
    if tz == "America/New_York":
        page.screenshot(path=f"{SHOTS}/lo8-erp-3b-so-nhap-xuat-ny.png")
    goto(page, "/inventory/?status=EXPIRED")
    page.wait_for_function("() => document.querySelectorAll('table.lt tr.lt-skel').length === 0")
    page.locator("table.lt tbody tr", has_text="L0908-CT00").first.locator("a").first.click()
    page.locator("[data-testid=qty-available]").wait_for()
    page.wait_for_timeout(600)
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name=re.compile("^Trả nhà cung cấp")).click()
    rts = page.get_by_role("dialog", name="Trả nhà cung cấp")
    rts.get_by_label("Số kg đã trả").fill("1")
    rts.get_by_role("button", name="Ghi nhận đã trả").click()
    rts.wait_for(state="detached", timeout=10_000)
    page.wait_for_timeout(900)
    out["lot_detail"] = page.inner_text("body")
    if tz == "America/New_York":
        page.screenshot(path=f"{SHOTS}/lo8-erp-3c-chi-tiet-lo-ny.png")
    goto(page, "/purchasing/")
    page.wait_for_selector("#received-date", timeout=10_000)
    out["received_date_default"] = page.input_value("#received-date")
    ctx.close()

    ctx = new_ctx(browser, tz)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errs.append(str(e)))
    login(page, "cs1")
    goto(page, "/confirmation/")
    out["cskh"] = page.inner_text("body")
    if tz == "America/New_York":
        page.screenshot(path=f"{SHOTS}/lo8-erp-4-cskh-ny.png")
    # Vòng đi-về giờ nhập: ô datetime-local là GIỜ VN -> hẹn 09:00 phải hiện lại 09:00 (không lệch theo múi giờ máy)
    # Giờ trả tiền nằm ở trang chi tiết phiếu (ô "Trả tiền lúc"), không còn trên thẻ hàng chờ
    page.locator("table.lt tbody tr", has_text="SO260928-E83D36").first.locator("a").first.click()
    page.get_by_role("heading", name="SO260928-E83D36").wait_for(timeout=10_000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    out["cskh_detail"] = re.sub(r"\s+", " ", page.locator("main").inner_text())
    page.get_by_role("link", name="Gọi xác nhận").first.click()
    page.wait_for_load_state("networkidle")
    page.locator("table.lt tbody tr").first.wait_for(timeout=10_000)
    # ERP theo design (ED-15): bảng + trang chi tiết; "Hẹn gọi lại" nằm trong menu "Thao tác khác" và mở hộp thoại riêng
    page.locator("table.lt tbody tr", has_text="SO260928-B27C30").first.locator("a").first.click()
    page.get_by_role("heading", name="SO260928-B27C30").wait_for(timeout=10_000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Thao tác khác").click()
    page.get_by_role("menuitem", name="Hẹn gọi lại").click()
    modal = page.get_by_role("dialog")
    modal.wait_for(timeout=10_000)
    page.wait_for_timeout(500)
    modal.locator("input[type=datetime-local]").fill("2026-10-02T09:00")
    modal.get_by_role("button", name="Lưu hẹn gọi lại").click()
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")
    if page.get_by_role("dialog").count():
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    page.get_by_role("link", name="Gọi xác nhận").first.click()
    page.wait_for_load_state("networkidle")
    page.get_by_role("tab", name="Hẹn gọi lại").click()
    page.wait_for_timeout(700)
    out["cskh_after_callback"] = page.inner_text("body")
    ctx.close()
    out["errs"] = errs
    return out


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        data = {tz: collect(browser, tz) for tz in TZS}

        base = data["Asia/Ho_Chi_Minh"]
        # ---- giá trị tuyệt đối (mốc VN) -> chứng minh đúng, không chỉ nhất quán
        ok("AC2 Tổng quan: 'Cập nhật 00:30' (17:30Z = 00:30 VN)", "Cập nhật 00:30" in base["overview"])
        ok("AC2 Lô: dòng nhập xuất vừa ghi hiện '01/10/2026 00:30' (00:30 giờ VN)", "01/10/2026 00:30" in base["lot_detail"], str(time_tokens(base["lot_detail"])[:6]))
        ok("AC2 Sổ nhập xuất: cột Thời gian có mốc giờ dạng dd/mm/yyyy hh:mm", len(re.findall(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", base["ledger"])) >= 5, str(time_tokens(base["ledger"])[:4]))
        ok("AC2 Đơn hàng: dòng đầu '01/10/2026 00:20'", "01/10/2026 00:20" in base["orders"], str(time_tokens(base["orders"])[:4]))
        # Lô 3: trang chi tiết đơn ghi "Đặt lúc / Tự huỷ lúc" thành 2 dòng nhãn-giá trị và dòng thời gian có giờ ở dòng riêng.
        ok("AC2 Chi tiết đơn: 'Đặt lúc 01/10/2026 00:20', 'Tự huỷ lúc 01/10/2026 00:50', dòng thời gian '01/10/2026 00:20' + 'Khách đặt đơn'",
           all(x in base["order_detail"] for x in ("Đặt lúc\n01/10/2026 00:20", "Tự huỷ lúc\n01/10/2026 00:50", "DÒNG THỜI GIAN\n01/10/2026 00:20\nKhách đặt đơn")),
           repr(base["order_detail"][700:1100]))
        ok("AC4 Ngày nhập lô mặc định = 2026-10-01 (hôm nay VN)", base["received_date_default"] == "2026-10-01", base["received_date_default"])
        ok("AC2 CSKH: chi tiết phiếu 'Trả tiền lúc 28/09/2026 06:00' (06:00+07:00 = 23:00Z hôm trước)", "Trả tiền lúc 28/09/2026 06:00" in base["cskh_detail"], base["cskh_detail"][:200])
        ok("AC2 CSKH: hàng chờ hiện 'Hạn gọi' đúng giờ VN '28/09/2026 09:10'", "28/09/2026 09:10" in base["cskh"])
        ok("AC4 CSKH: hẹn gọi lại nhập 09:00 hiện '02/10/2026 09:00' ở cột Hạn gọi", "02/10/2026 09:00" in base["cskh_after_callback"])

        # ---- mọi múi giờ máy khác phải cho đúng kết quả như giờ VN
        for tz in TZS[:-1]:
            d = data[tz]
            for key in ("overview", "orders", "order_detail", "inventory", "ledger", "lot_detail", "cskh", "cskh_detail", "cskh_after_callback"):
                ok(f"AC2 [{tz}] {key}: giờ/ngày hiển thị = giờ VN ({len(time_tokens(base[key]))} mốc)",
                   time_tokens(d[key]) == time_tokens(base[key]) and len(time_tokens(base[key])) > 0,
                   f"{time_tokens(d[key])[:6]} vs {time_tokens(base[key])[:6]}")
            ok(f"AC4 [{tz}] Ngày nhập lô mặc định = ngày VN", d["received_date_default"] == "2026-10-01", d["received_date_default"])
            ok(f"AC2 [{tz}] HSD phiếu giao dạng dd/mm/yyyy", "20/09/2027" in d["delivery_detail"], "")
            ok(f"[{tz}] không có pageerror", not d["errs"], str(d["errs"][:2]))

        # ---- tiền
        for tz in TZS:
            d = data[tz]
            for key in ("overview", "orders", "order_detail", "inventory", "ledger", "lot_detail", "deliveries", "delivery_detail", "cskh"):
                bad = money_bad(d[key])
                ok(f"AC1 [{tz}] {key}: không có tiền sai kiểu", not bad, str(bad[:3]))
        allmoney = sum(len(money_good(base[k])) for k in ("overview", "orders", "order_detail", "inventory"))
        ok("AC1 có >= 30 số tiền dạng x.xxx đ trên Tổng quan/Đơn/Lô", allmoney >= 30, str(allmoney))

        # ---- mobile 390 + ảnh (giờ máy New York)
        ctx = new_ctx(browser, "America/New_York", 390, 800)
        page = ctx.new_page()
        login(page, "loc")
        goto(page, "/orders/")
        page.locator("table.lt tbody tr.lt-click").first.click()
        page.wait_for_url("**/orders/detail/**", timeout=10_000)
        page.locator("main").wait_for(timeout=10_000)
        page.wait_for_timeout(900)
        ok("mobile 390: không cuộn ngang ở chi tiết đơn",
           page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
        page.screenshot(path=f"{SHOTS}/lo8-erp-5-don-chi-tiet-mobile-ny.png")
        ctx.close()
        browser.close()

    bad = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(bad)}/{len(results)} PASS")
    raise SystemExit(1 if bad else 0)


main()
