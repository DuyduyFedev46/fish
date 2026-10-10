"""
Bằng chứng chạy thật (Playwright) cho CMS-06 — Thẻ mặt hàng dẫn sang Shop.
Bù bằng chứng còn thiếu (review-cms-golive-fe-qa.md, bảng "AC thiếu bằng chứng", phần CMS):
CMS-06-AC3 (giá cập nhật lúc khách xem, không cần đăng lại bài), CMS-06-AC4 (UTM đúng),
CMS-06-AC5 (mặt hàng ngưng bán -> ẩn thẻ, phần còn lại của bài vẫn hiện), CMS-06-AC7 (chỉ gọi API công khai + shop
catalog, không lộ khoá cấm).

Cập nhật lô 5b (SHOP-5-05, mkt-brand): thẻ trong bài là ProductCard `row` + AddToCart trong khối "Món dùng trong bài"
(thay ItemCard cũ). Món ngưng bán / không còn trong catalog thì ẩn thẻ (AC2), món hết hiện "Liên hệ chúng tôi".
Thêm chế độ `add` kiểm "Thêm 1 kg" -> bộ tăng giảm + toast "Xem giỏ" (AC3, như SHOP-2-03 AC3).

LƯU Ý (phát hiện khi viết bằng chứng này): định dạng hiển thị giá ("165000.00đ" thay vì
"165.000 đ") có lỗi ở `frontend/lib/format.ts::formatVnd` (chuỗi giá từ API không được ép kiểu
Number trước khi gọi `toLocaleString`) — lỗi này áp dụng cho TOÀN BỘ Shop (lưới danh mục,
/shop/item), không riêng CMS. Script này chỉ kiểm phần thuộc AC (link UTM, cơ chế cập nhật giá
theo thời gian thực, fallback hết hàng, phạm vi gọi API) — KHÔNG assert đúng định dạng "x.xxx đ"
vì hiện đang sai thật (xem repro riêng `doc/features/2026-09-30-ra-soat-agy/repro/A5-format-vnd-string-price.py`).

Chạy thật, dữ liệu giả sinh bởi `manage.py seed_demo` + bài QA tự tạo qua API (không phải dữ
liệu thật của vựa). Cần chạy trước:
  cd backend && manage.py seed_demo   (tạo mặt hàng CA-THU, GHE-XANH có tồn)
  bài "bai-kiem-tra-the-mat-hang-ra-soat" có 2 khối item_card: CA-THU và GHE-XANH, đã đăng.

Dùng: python3 frontend/e2e/content_item_card.py [baseline|after-price-change|after-deactivate|add]
"""
import sys
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3104"
SLUG = "bai-kiem-tra-the-mat-hang-ra-soat"
FORBIDDEN_KEYS = [
    "purchase_rate", "landed_unit_cost", "unit_cost", "rate", "cost", "profit",
    "created_by", "updated_by", "username", "email",
]
ALLOWED_HOSTS = {"localhost"}
# site-info thuộc footer pháp lý (hồ sơ khung-go-live, thêm sau CMS) — không phải một phần của
# "trang bài công khai có thẻ" mà CMS-06-AC7 mô tả; ERP nội bộ thật sự (vd /api/content/, /api/sales/)
# vẫn phải bị chặn.
ALLOWED_EXTRA_PUBLIC_PATHS = ("/api/public/site-info/", "/api/public/content/footer-links/")


def get_price_number(page, code: str) -> float | None:
    card_text = page.eval_on_selector_all(
        f'a[href*="code={code}"]',
        "els => els.length ? (els[0].closest('li') || els[0]).textContent : ''",
    ) or ""
    import re
    m = re.search(r"(\d[\d.,]*)\s*đ", card_text)
    if not m:
        return None
    raw = m.group(1)
    # Định dạng đúng dùng dấu chấm/phẩy làm phân cách nghìn (vd "165.000"); định dạng lỗi hiện tại
    # (formatVnd nhận chuỗi thay vì số) in ra dạng thập phân "165000.00" — phân biệt bằng việc có
    # đúng 1 dấu chấm/phẩy và đúng 2 chữ số sau nó thì coi là phần thập phân, bỏ đi.
    if re.fullmatch(r"\d+[.,]\d{2}", raw):
        raw = raw[:-3]
    else:
        raw = raw.replace(".", "").replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def main() -> int:
    failures = []
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        requests_seen = []
        page.on("request", lambda r: requests_seen.append(r.url))
        page.goto(f"{BASE}/blog/?slug={SLUG}")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("article", timeout=10000)
        page.wait_for_timeout(800)  # chờ ItemCard fetch xong (client-side)

        page.screenshot(path=f"/tmp/ra_soat_cms06_{mode}.png", full_page=True)

        if mode == "baseline":
            links = page.eval_on_selector_all(
                'a[href*="/shop/item/"]', "els => els.map(e => e.getAttribute('href'))"
            )
            ca_thu_link = next((h for h in links if "code=CA-THU" in h), None)
            if not ca_thu_link:
                failures.append("AC4: không tìm thấy link sang trang món CA-THU trong khối 'Món dùng trong bài'")
            else:
                qs = dict(pair.split("=") for pair in ca_thu_link.split("?", 1)[1].split("&"))
                expected = {
                    "code": "CA-THU",
                    "utm_source": "caveve_web",
                    "utm_medium": "bai_viet",
                    "utm_campaign": SLUG,
                }
                if qs != expected:
                    failures.append(f"AC4: tham số UTM sai. có={qs} mong={expected}")

            price = get_price_number(page, "CA-THU")
            if price != 165000:
                failures.append(f"AC3 (baseline): giá CA-THU hiển thị không đúng 165000 (đọc được {price})")

        elif mode == "after-price-change":
            price = get_price_number(page, "CA-THU")
            if price != 260000:
                failures.append(
                    f"AC3: sau khi đổi giá Shop (165000->260000) mà KHÔNG đăng lại bài, "
                    f"thẻ phải hiện giá mới 260000 (đọc được {price})"
                )

        elif mode == "after-deactivate":
            # SHOP-5-05 AC2: món ngưng bán (không còn trong catalog) -> ẩn thẻ, không hiện thẻ "mã hàng" trống.
            if page.locator('a[href*="code=GHE-XANH"]').count() != 0:
                failures.append("AC2: món GHE-XANH đã ngưng bán nhưng thẻ vẫn hiện trong bài")
            if "GHE-XANH" in page.inner_text("body"):
                failures.append("AC2: mã hàng thô GHE-XANH lộ ra chữ trên trang")
            # phần còn lại của bài (thẻ CA-THU) vẫn hiển thị đủ, không vỡ trang
            ca_thu_price = get_price_number(page, "CA-THU")
            if ca_thu_price is None:
                failures.append("AC5: phần còn lại của bài (thẻ CA-THU) không hiển thị khi thẻ khác lỗi")

        elif mode == "add":
            # SHOP-5-05 AC3 (như SHOP-2-03 AC3): "Thêm 1 kg" -> bộ tăng giảm "1 kg", toast có "Xem giỏ".
            btn = page.locator('li:has(a[href*="code=CA-THU"]) button', has_text="Thêm 1 kg").first
            if btn.count() == 0:
                failures.append("AC3: không thấy nút 'Thêm 1 kg' cho CA-THU")
            else:
                btn.click()
                page.wait_for_timeout(300)
                card = page.locator('li:has(a[href*="code=CA-THU"])').first
                if "1 kg" not in card.inner_text():
                    failures.append("AC3: sau khi thêm, thẻ không hiện bộ tăng giảm '1 kg'")
                if page.get_by_role("link", name="Xem giỏ").count() == 0:
                    failures.append("AC3: không thấy toast có link 'Xem giỏ'")
                stored = page.evaluate("localStorage.getItem('cangcaloc_cart_v1') || ''")
                if "CA-THU" not in stored:
                    failures.append("AC3: giỏ (localStorage) chưa có CA-THU")

        # CMS-06-AC7: chỉ gọi API công khai nội dung + shop catalog (+ footer pháp lý, tính năng sau)
        bad_requests = []
        for u in requests_seen:
            if "/api/" not in u:
                continue
            if "/api/public/content/" in u or "/api/shop/catalog/" in u:
                continue
            if any(path in u for path in ALLOWED_EXTRA_PUBLIC_PATHS):
                continue
            bad_requests.append(u)
        if bad_requests:
            failures.append(f"AC7: có request tới API nội bộ ngoài phạm vi cho phép: {bad_requests}")
        hosts = {urlparse(u).hostname for u in requests_seen if urlparse(u).hostname}
        unexpected = hosts - ALLOWED_HOSTS
        if unexpected:
            failures.append(f"AC7: có request tới host ngoài allowlist: {unexpected}")
        page_html = page.content()
        for key in FORBIDDEN_KEYS:
            if f'"{key}"' in page_html:
                failures.append(f"AC7: HTML có khoá cấm '{key}'")

        browser.close()

    if failures:
        print(f"FAIL ({mode}):")
        for f in failures:
            print(" -", f)
        return 1
    print(f"PASS ({mode}): CMS-06 bằng chứng bổ sung đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
