# A4 CSKH — X-AC4: Sau luồng CSKH (gọi xác nhận, đổi người nhận, in tem), localStorage/sessionStorage/
# IndexedDB/URL/console không được chứa tên, SĐT (đủ 10 số) hay địa chỉ khách.
# Dữ liệu giả theo 02-stories.md: "Khách Thử A", "0900000123", "Số 1 Đường Thử".
# Chạy: cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3203 &)
#       python3 e2e/ra_soat_x_ac4_storage.py     # tắt server sau khi xong
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3203")
results = []

# Dữ liệu cá nhân giả cần rà — mẫu tên/SĐT/địa chỉ có trong mock (02-stories.md dùng đúng các chuỗi này)
PHONE_FULL = "0900000123"
NEW_RECIPIENT_PHONE = "0900000456"  # theo mẫu contract CS-12
FULL_NAME_NEEDLES = ["Khách Thử A", "Người Nhận Thử"]
ADDRESS_NEEDLE = "Đường Thử"
# SĐT KHÁCH của kịch bản (không phải SĐT nhân viên "cave_erp_mock_users" — dữ liệu mô phỏng đăng nhập có sẵn
# từ trước, dùng cho MỌI màn ERP, không thuộc phạm vi PII khách của hồ sơ CSKH).
CUSTOMER_PHONE_RE = re.compile(r"0900000123|0900000456")


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


def dump_storage(page):
    return {
        "localStorage": page.evaluate("() => JSON.stringify(localStorage)"),
        "sessionStorage": page.evaluate("() => JSON.stringify(sessionStorage)"),
        "indexedDB": page.evaluate(
            """async () => {
                if (!window.indexedDB || !indexedDB.databases) return '[]';
                try {
                    const dbs = await indexedDB.databases();
                    return JSON.stringify(dbs.map(d => d.name));
                } catch (e) { return 'ERR:' + e; }
            }"""
        ),
    }


def check_pii_absent(label, text):
    ok(f"{label}: không có SĐT khách (0900000123 / 0900000456)", not CUSTOMER_PHONE_RE.search(text), text[:200])
    for needle in FULL_NAME_NEEDLES:
        ok(f"{label}: không có tên '{needle}'", needle not in text)
    ok(f"{label}: không có địa chỉ ('{ADDRESS_NEEDLE}')", ADDRESS_NEEDLE not in text)


console_messages = []
requested_urls = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.on("console", lambda m: console_messages.append(m.text))
    page.on("request", lambda r: requested_urls.append(r.url))

    login(page, "cs1")

    # 1) Mở hàng chờ CSKH, mở chi tiết đơn (tự động claim), đổi người nhận hộ, ghi kết quả cuộc gọi
    page.goto(BASE + "/confirmation/")
    page.wait_for_load_state("networkidle")
    page.locator("text=DH-260928-0001").first.click()
    page.wait_for_timeout(400)

    page.get_by_role("button", name="Đổi người nhận / địa chỉ").click()
    page.wait_for_timeout(200)
    # Điền tên/SĐT người nhận hộ (dữ liệu giả theo contract CS-12)
    name_input = page.locator("input[placeholder*='nhận hộ']").first
    if name_input.count() > 0:
        name_input.fill("Người Nhận Thử")
    phone_inputs = page.locator("input[type='tel'], input[placeholder*='SĐT']")
    if phone_inputs.count() > 0:
        phone_inputs.last.fill(NEW_RECIPIENT_PHONE)
    save_btn = page.get_by_role("button", name=re.compile("Lưu|Cập nhật|Xác nhận đổi"))
    if save_btn.count() > 0:
        save_btn.first.click()
        page.wait_for_timeout(400)

    # Ghi kết quả cuộc gọi: CONFIRMED ("Đã xác nhận") với ghi chú hợp lệ (không SĐT/STK)
    note_box = page.locator("textarea")
    if note_box.count() > 0:
        note_box.first.fill("Giao sau 17h, khách đồng ý")
    page.get_by_text("Đã xác nhận", exact=False).first.click()
    page.wait_for_timeout(600)

    # Bỏ qua "Failed to fetch RSC payload" — hiện tượng đã biết khi serve static export bằng
    # python http.server đơn giản (không phải Next server), không liên quan lỗi nghiệp vụ hay PII.
    real_errors = [
        m for m in console_messages
        if ("error" in m.lower())
        and "favicon" not in m
        and "RSC payload" not in m
    ]
    ok("Luồng CSKH hoàn tất không lỗi JS nghiệp vụ (không văng exception ra console)",
       not real_errors, "; ".join(real_errors[:5]))

    storage_after_cskh = dump_storage(page)
    for key, val in storage_after_cskh.items():
        check_pii_absent(f"CSKH sau khi gọi+đổi người nhận [{key}]", val)

    ok("URL trang CSKH không chứa SĐT/tên trong query", not CUSTOMER_PHONE_RE.search(page.url) and "Thử" not in page.url, page.url)

    # 2) In tem (kho1) — kiểm URL trang in chỉ có note & print_no, không PII trong URL
    # Dùng context mới (tránh RSC prefetch cache của phiên cs1 làm treo điều hướng /login/).
    ctx2 = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx2.new_page()
    page.on("console", lambda m: console_messages.append(m.text))
    page.on("request", lambda r: requested_urls.append(r.url))
    login(page, "kho1")
    page.goto(BASE + "/deliveries/")
    page.wait_for_load_state("networkidle")
    page.get_by_text("GH-HD-0031-PREP").first.click()
    page.wait_for_timeout(400)
    with ctx2.expect_page() as popup_info:
        page.get_by_role("button", name="In tem").click()
    label_page = popup_info.value
    label_page.wait_for_load_state("networkidle")
    label_page.wait_for_timeout(500)

    ok(
        "URL trang in tem chỉ có note & print_no, không có SĐT/tên",
        "note=" in label_page.url and "print_no=" in label_page.url and not CUSTOMER_PHONE_RE.search(label_page.url) and "Thử" not in label_page.url,
        label_page.url,
    )
    label_storage = dump_storage(label_page)
    for key, val in label_storage.items():
        check_pii_absent(f"Trang in tem [{key}]", val)

    # 3) Mọi request URL trong toàn phiên không chứa SĐT/tên trong query string
    bad_urls = [u for u in requested_urls if CUSTOMER_PHONE_RE.search(u) or "Kh%C3%A1ch%20Th%E1%BB%AD" in u or "Th%E1%BB%AD" in u]
    ok("Không có request URL nào chứa SĐT/tên trong query string", len(bad_urls) == 0, str(bad_urls[:5]))

    # 4) Console tổng thể (mọi trang) không có SĐT đầy đủ/tên/địa chỉ
    all_console_text = "\n".join(console_messages)
    check_pii_absent("Console toàn phiên", all_console_text)

    browser.close()

print("\n=== TỔNG KẾT ===")
n_ok = sum(1 for _, c, _ in results if c)
print(f"{n_ok}/{len(results)} PASS")
failed = [(n, e) for n, c, e in results if not c]
if failed:
    print("FAILED:", failed)
    sys.exit(1)
