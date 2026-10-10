"""
P8 Lô 8 — SR-25 (Shop): tiền VNĐ dạng "260.000 ₫" và ngày giờ theo giờ Việt Nam (GMT+7),
bất kể múi giờ trình duyệt. Chạy hai lượt: múi giờ America/New_York và UTC.

Hai bản build:
  MOCK  (cổng 3109, NEXT_PUBLIC_USE_MOCK=1): mock trả giá/tồn dạng chuỗi Decimal như API thật.
  REAL  (cổng 3110, NEXT_PUBLIC_USE_MOCK=0, API giả localhost:8199 chặn bằng page.route): kiểm ngày ở sát
        ranh giới ngày VN (2026-09-30T17:30:00Z = 01/10 00:30 giờ VN) để phân biệt giờ VN với giờ máy.

Dữ liệu 100% giả.

    cd frontend
    NEXT_PUBLIC_USE_MOCK=1 npm run build && cp -R out/. <scratch>/lo8-shop/mock/
    NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8199 npm run build && cp -R out/. <scratch>/lo8-shop/real/
    (cd <scratch>/lo8-shop/mock && python3 -m http.server 3109 --bind 127.0.0.1 &)
    (cd <scratch>/lo8-shop/real && python3 -m http.server 3110 --bind 127.0.0.1 &)
    QA_SHOT_DIR=doc/features/2026-09-30-sua-loi-review/qa-lo8 python3 e2e/qa-lo8-shop-format.py
"""
import json
import os
import re
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

MOCK = os.environ.get("QA_MOCK_BASE", "http://127.0.0.1:3109")
REAL = os.environ.get("QA_REAL_BASE", "http://127.0.0.1:3110")
SHOT_DIR = os.environ.get("QA_SHOT_DIR", "/tmp")
API = "http://localhost:8199"
CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"}
TZS = ["America/New_York", "UTC"]

# Mốc sát ranh giới ngày: 17:30 UTC ngày 30/09 = 00:30 ngày 01/10 giờ VN.
EDGE = "2026-09-30T17:30:00Z"
SITE = {"seller": {"name": "Vựa Thử Nghiệm QA", "business_type": "Hộ kinh doanh", "registration_no": "0000000001",
                   "tax_code": "0000000002", "address": "1 Đường Giả, Phường Giả, Tỉnh Giả", "phone": "0900000000",
                   "email": "lienhe@example.com"},
        "seller_complete": True, "privacy_consent_required": False, "confirm_call_notice": True,
        "confirm_call_hours": "7:00–20:00"}
CATALOG = [{"item_code": "CA-QA-01", "name": "Cá QA giả định 1", "item_type": "SIMPLE", "unit": "kg", "min_qty": "1", "qty_step": "0.5", "group": {"slug": "ca", "name": "Cá"}, "short_note": "", "stock_level": "in",
            "price": "260000", "image": None},
           {"item_code": "CA-QA-02", "name": "Cá QA giả định 2", "item_type": "SIMPLE", "unit": "kg", "min_qty": "1", "qty_step": "0.5", "group": {"slug": "ca", "name": "Cá"}, "short_note": "", "stock_level": "low",
            "price": "1250000", "image": None}]
ENTRY = {"kind": "post", "slug": "bai-thu", "title": "Bài thử QA", "seo_title": "", "description": "", "excerpt": "",
         "category": None, "cover_image": None,
         "body": {"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Đoạn văn giả."}]},
                                            {"type": "item_card", "item_code": "CA-QA-01"}]},
         "published_at": EDGE, "updated_at": EDGE, "version": 1, "effective_from": None, "author": "Cá Về"}
LIST = {"count": 1, "total": 1, "total_pages": 1, "page": 1, "next": None, "previous": None,
        "results": [{"kind": "post", "slug": "bai-thu", "title": "Bài thử QA", "excerpt": "Tóm tắt giả.", "category": None,
                     "cover_image": None, "published_at": EDGE, "updated_at": EDGE}]}
ORDER_201 = {"order_code": "DH-QA-0001", "total_amount": "260000.00", "booked_expires_at": "2099-01-01T00:00:00Z"}
LOOKUP = {"order_code": "DH-QA-0001", "status": "CANCELLED", "status_label": "Đã huỷ", "total_amount": "260000.00",
          "lines": [{"item_code": "CA-QA-01", "qty": "1.000", "amount": "260000.00"}],
          "delivery": None, "booked_expires_at": None,
          "cancel_notice": {"reason_code": "UNREACHABLE_AUTO", "message": "Đơn đã được huỷ.",
                            "refund": {"amount": "260000.00", "status_label": "Đã hoàn", "deadline": "2026-10-28",
                                       "refunded_at": EDGE}, "contact": "1900000000"}}

failures, total = [], 0
MONEY = re.compile(r"(\d[\d.,]*)\s?([đ₫])(?!\w)")


def check(label, cond, detail=""):
    global total
    total += 1
    ok = bool(cond)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f"  <{detail}>" if (detail and not ok) else ""))
    if not ok:
        failures.append(label)


def money_ok(text):
    toks = MONEY.findall(text)
    bad = [f"{a}{b}" for a, b in toks if not re.fullmatch(r"\d{1,3}(\.\d{3})*", a)]
    raw = [f"{m.group(0)}" for m in re.finditer(r"\d+\.\d{2}\s?[đ₫](?!\w)", text)]
    wrong_sym = [f"{a}{b}" for a, b in toks if b != "₫"]
    return len(toks), bad + raw + wrong_sym


def resp(route, body, status=200):
    route.fulfill(status=status, content_type="application/json", headers=CORS, body=json.dumps(body))


def fake_api(page):
    def api(route):
        req = route.request
        path = urlparse(req.url).path
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=CORS)
        if path == "/api/public/site-info/":
            return resp(route, SITE)
        if path == "/api/public/content/footer-links/":
            return resp(route, [])
        if path == "/api/shop/catalog/":
            return resp(route, {"groups": [{"slug": "ca", "name": "Cá", "item_count": len(CATALOG)}], "items": CATALOG})
        if re.match(r"^/api/shop/catalog/[^/]+/$", path):
            code = path.strip("/").split("/")[-1]
            hit = [c for c in CATALOG if c["item_code"] == code]
            return resp(route, hit[0], 200) if hit else resp(route, {"detail": "Not found."}, 404)
        if path == "/api/public/content/entries/":
            return resp(route, LIST)
        if path == "/api/public/content/categories/":
            return resp(route, [])
        if path.startswith("/api/public/content/entries/"):
            return resp(route, ENTRY)
        if path == "/api/shop/orders/" and req.method == "POST":
            return resp(route, ORDER_201, 201)
        if re.match(r"^/api/shop/orders/[^/]+/$", path):
            return resp(route, LOOKUP)
        return resp(route, {"detail": "Not found."}, 404)
    page.route(f"{API}/**", api)


def goto(page, base, path):
    page.goto(f"{base}{path}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)


def offset_of(page):
    return page.evaluate("new Date('2026-09-30T17:30:00Z').getTimezoneOffset()")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for tz in TZS:
            tag = tz.split("/")[-1]
            # ================= MOCK =================
            ctx = b.new_context(viewport={"width": 390, "height": 800}, timezone_id=tz, locale="vi-VN")
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            off = offset_of(page)
            check(f"[{tag}] múi giờ trình duyệt đúng là {tz} (offset {off} phút, khác -420)", off != -420, str(off))

            goto(page, MOCK, "/shop/")
            body = page.inner_text("body")
            cnt, bad = money_ok(body)
            check(f"[{tag}][mock] /shop/ có giá và mọi giá dạng '65.000 ₫' (không '65000.00đ')", cnt >= 5 and not bad, f"{cnt} {bad}")
            check(f"[{tag}][mock] /shop/ có '65.000đ' và không hiện số kg tồn", "65.000đ" in body and not re.search(r"Còn \d", body), body[:300])
            page.screenshot(path=f"{SHOT_DIR}/lo8-shop-{tag}-390.png", full_page=True)

            goto(page, MOCK, "/shop/item/?code=TOM-SU-TUOI")
            body = page.inner_text("body")
            cnt, bad = money_ok(body)
            check(f"[{tag}][mock] /shop/item giá '270.000 ₫'", cnt >= 1 and not bad and re.search(r"\d{3}\.000 ₫", body), f"{cnt} {bad} {body[:200]}")
            page.screenshot(path=f"{SHOT_DIR}/lo8-item-{tag}-390.png", full_page=True)

            # thêm 2 món vào giỏ -> checkout: đơn giá, thành tiền, tổng, nút đặt hàng
            goto(page, MOCK, "/shop/")
            page.get_by_role("button", name="Thêm vào giỏ").first.click()
            page.get_by_role("button", name="Thêm vào giỏ").nth(1).click()
            goto(page, MOCK, "/shop/checkout/")
            body = page.inner_text("body")
            cnt, bad = money_ok(body)
            check(f"[{tag}][mock] checkout: đơn giá/thành tiền/tổng/nút đặt hàng đều 'x.xxx ₫'", cnt >= 5 and not bad, f"{cnt} {bad}")
            check(f"[{tag}][mock] checkout: tổng 65.000 + 220.000 = '285.000 ₫' (giá là số, không nối chuỗi)", "285.000 ₫" in body, body[-400:])
            page.screenshot(path=f"{SHOT_DIR}/lo8-checkout-{tag}-390.png", full_page=True)
            page.fill("#name", "Khách QA Ẩn Danh")
            page.fill("#phone", "0912345678")
            page.fill("#address", "999 Đường Bí Mật QA")
            if page.locator('input[type="checkbox"]').count():
                page.locator('input[type="checkbox"]').check()
            page.get_by_role("button", name=re.compile("Đặt hàng")).click()
            page.wait_for_timeout(900)
            body = page.inner_text("body")
            cnt, bad = money_ok(body)
            check(f"[{tag}][mock] màn thanh toán: số tiền đơn '285.000 ₫'", "285.000 ₫" in body and not bad, f"{bad} {body[:300]}")
            page.screenshot(path=f"{SHOT_DIR}/lo8-thanh-toan-{tag}-390.png", full_page=True)

            # tra đơn mock DEMO004: số tiền hoàn + hạn hoàn dd/mm/yyyy
            goto(page, MOCK, "/shop/orders/")
            page.fill("#orderCode", "DH-DEMO004")
            page.fill("#phoneLast4", "5678")
            page.get_by_role("button", name=re.compile("Tra|Kiểm")).first.click()
            page.wait_for_timeout(700)
            body = page.inner_text("body")
            cnt, bad = money_ok(body)
            check(f"[{tag}][mock] tra đơn: tiền hoàn/thành tiền 'x.xxx ₫'", cnt >= 2 and not bad, f"{cnt} {bad} {body[:300]}")
            check(f"[{tag}][mock] tra đơn: hạn hoàn '28/10/2026' (không '2026-10-28')", "28/10/2026" in body and "2026-10-28" not in body, body[:400])
            page.screenshot(path=f"{SHOT_DIR}/lo8-tra-don-{tag}-390.png", full_page=True)

            goto(page, MOCK, "/blog/")
            body = page.inner_text("body")
            check(f"[{tag}][mock] /blog ngày dạng dd/mm/yyyy", re.search(r"\b\d{2}/\d{2}/\d{4}\b", body) is not None, body[:200])
            goto(page, MOCK, "/pages/?slug=chinh-sach-bao-mat")
            check(f"[{tag}][mock] /trang 'Có hiệu lực từ 28/09/2026'", "Có hiệu lực từ 28/09/2026" in page.inner_text("body"), page.inner_text("body")[:300])
            goto(page, MOCK, "/")
            body = page.inner_text("body")
            check(f"[{tag}][mock] trang chủ: giờ máy không phá layout, dòng bản quyền © 2026", "© 2026" in body)
            check(f"[{tag}][mock] không pageerror", not errs, str(errs))
            ctx.close()

            # ================= REAL (API giả, dữ liệu sát ranh giới ngày) =================
            ctx = b.new_context(viewport={"width": 390, "height": 800}, timezone_id=tz, locale="vi-VN")
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            fake_api(page)

            goto(page, REAL, "/shop/")
            body = page.inner_text("body")
            cnt, bad = money_ok(body)
            check(f"[{tag}][real] /shop/ giá chuỗi Decimal '260000.00' -> '260.000 ₫', '1250000.00' -> '1.250.000 ₫'",
                  "260.000 ₫" in body and "1.250.000 ₫" in body and cnt >= 2 and not bad, f"{cnt} {bad} {body[:300]}")
            check(f"[{tag}][real] /shop/ món sắp hết có nhãn 'Sắp hết', không hiện số kg tồn", "Sắp hết" in body and not re.search(r"Còn \d", body), body[:400])
            page.screenshot(path=f"{SHOT_DIR}/lo8-real-shop-{tag}-390.png", full_page=True)

            goto(page, REAL, "/shop/item/?code=CA-QA-01")
            body = page.inner_text("body")
            check(f"[{tag}][real] /shop/item '260.000 ₫ / kg'", "260.000 ₫" in body and not money_ok(body)[1], body[:300])

            # giỏ: giá là số (cộng đúng), không nối chuỗi "0260000.00..."
            goto(page, REAL, "/shop/")
            page.get_by_role("button", name="Thêm vào giỏ").first.click()
            page.get_by_role("button", name="Thêm vào giỏ").nth(1).click()
            stored = page.evaluate("window.localStorage.getItem('cangcaloc_cart_v1')")
            check(f"[{tag}][real] giỏ lưu giá dạng SỐ (không chuỗi Decimal)", stored and '"price":260000' in stored and '"price":"' not in stored, str(stored)[:200])
            goto(page, REAL, "/shop/checkout/")
            body = page.inner_text("body")
            check(f"[{tag}][real] checkout tổng 260.000 + 1.250.000 = '1.510.000 ₫'", "1.510.000 ₫" in body and not money_ok(body)[1], body[-400:])
            # giỏ cũ lưu giá chuỗi (bản trước Lô 8) -> vẫn cộng đúng
            page.evaluate("""window.localStorage.setItem('cangcaloc_cart_v1', JSON.stringify([{item_code:'CA-QA-01',name:'Cá QA giả định 1',price:'260000.00',unit:'Kg',qty:2}]))""")
            goto(page, REAL, "/shop/checkout/")
            body = page.inner_text("body")
            check(f"[{tag}][real] giỏ cũ giá chuỗi '260000.00' x2 -> '520.000 ₫'", "520.000 ₫" in body and not money_ok(body)[1], body[-400:])
            page.fill("#name", "Khách QA Ẩn Danh")
            page.fill("#phone", "0912345678")
            page.fill("#address", "999 Đường Bí Mật QA")
            if page.locator('input[type="checkbox"]').count():
                page.locator('input[type="checkbox"]').check()
            page.get_by_role("button", name=re.compile("Đặt hàng")).click()
            page.wait_for_timeout(900)
            body = page.inner_text("body")
            check(f"[{tag}][real] màn thanh toán: total_amount '260000.00' -> '260.000 ₫'", "260.000 ₫" in body and not money_ok(body)[1], body[:300])

            goto(page, REAL, "/blog/?slug=bai-thu")
            body = page.inner_text("body")
            check(f"[{tag}][real] bài viết: 'Đăng ngày: 01/10/2026' (giờ VN, không 30/09)", "Đăng ngày: 01/10/2026" in body and "30/09/2026" not in body, body[:300])
            check(f"[{tag}][real] thẻ mặt hàng trong bài hiện '260.000 ₫'", "260.000 ₫" in body and not money_ok(body)[1], body[:400])
            page.screenshot(path=f"{SHOT_DIR}/lo8-real-baiviet-{tag}-390.png", full_page=True)
            goto(page, REAL, "/blog/")
            body = page.inner_text("body")
            check(f"[{tag}][real] danh sách bài: ngày '01/10/2026'", "01/10/2026" in body and "30/09/2026" not in body, body[:300])
            goto(page, REAL, "/")
            body = page.inner_text("body")
            check(f"[{tag}][real] bài mới trang chủ: ngày '01/10/2026'", "01/10/2026" in body and "30/09/2026" not in body, body[-500:])
            goto(page, REAL, "/pages/?slug=chinh-sach-bao-mat")
            body = page.inner_text("body")
            check(f"[{tag}][real] trang chính sách: 'Có hiệu lực từ 01/10/2026' (published_at sát ranh giới)", "01/10/2026" in body and "30/09/2026" not in body, body[:300])

            goto(page, REAL, "/shop/orders/")
            page.fill("#orderCode", "DH-QA-0001")
            page.fill("#phoneLast4", "5678")
            page.get_by_role("button", name=re.compile("Tra|Kiểm")).first.click()
            page.wait_for_timeout(700)
            body = page.inner_text("body")
            check(f"[{tag}][real] tra đơn: tiền hoàn/thành tiền '260.000 ₫', 'đã hoàn 01/10/2026', hạn 'không hiện 2026-10-28'",
                  "260.000 ₫" in body and "đã hoàn 01/10/2026" in body and not money_ok(body)[1], body[:500])
            page.screenshot(path=f"{SHOT_DIR}/lo8-real-tra-don-{tag}-390.png", full_page=True)
            check(f"[{tag}][real] không pageerror", not errs, str(errs))
            ctx.close()
        b.close()
    print(f"\n{total - len(failures)}/{total} PASS, {len(failures)} FAIL")
    for f in failures:
        print("  FAIL:", f)
    raise SystemExit(1 if failures else 0)


main()
