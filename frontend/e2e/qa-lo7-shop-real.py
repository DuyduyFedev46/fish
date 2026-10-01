"""
P8 Lô 7 — FE Shop, bản build THẬT (NEXT_PUBLIC_USE_MOCK=0, API giả localhost:8199 chặn bằng page.route):
  F7   bài có 3 thẻ mặt hàng -> đúng 1 request /api/shop/catalog/, 0 request /api/shop/catalog/<mã>/;
       bài không có thẻ -> 0 request catalog; catalog lỗi -> thẻ báo hết hàng, bài vẫn đọc được.
  F10  màn checkout (form + màn thanh toán) -> site-info <= 1 request; hai khối cùng đọc 1 nguồn giờ;
       trang tra đơn (ConfirmCallNotice tự tải) -> 1 request.
  F6   apiFetch 404 {"detail":"Not found."} / 410 / 404 tiếng Việt -> trang hiện chữ Việt, không lộ "Not found.".
Dữ liệu 100% giả.

    cd frontend && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8199 npm run build
    cp -R out/. <scratch>/real/ ; (cd <scratch>/real && python3 -m http.server 3107 --bind 127.0.0.1 &)
    QA_BASE=http://127.0.0.1:3107 QA_SHOT_DIR=doc/features/2026-09-30-sua-loi-review/qa-lo7 python3 e2e/qa-lo7-shop-real.py
"""
import json
import os
import re
import sys
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BASE = os.environ.get("QA_BASE", "http://127.0.0.1:3107")
SHOT_DIR = os.environ.get("QA_SHOT_DIR", "/tmp")
API = "http://localhost:8199"
CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"}

SELLER = {"name": "Vựa Thử Nghiệm QA", "business_type": "Hộ kinh doanh", "registration_no": "0000000001",
          "tax_code": "0000000002", "address": "1 Đường Giả, Phường Giả, Tỉnh Giả", "phone": "0900000000",
          "email": "lienhe@example.com"}
POLICY = {"enabled": True, "working_hours": "07:00-21:00", "max_attempts": 3, "window_minutes": 30, "decision_minutes": 60,
        "auto_cancel_enabled": True, "refund_deadline_days": 7, "hotline": "1900000000"}
SITE = {"seller": SELLER, "seller_complete": True, "privacy_consent_required": False, "confirm_call_notice": True,
        "confirm_call_hours": "7:00–20:00", "confirmation_policy": POLICY, "cskh_notice": POLICY}
CODES = ["CA-QA-01", "CA-QA-02", "CA-QA-03"]
CATALOG = [{"item_code": c, "name": f"Cá QA giả định {i+1}", "group": "ca", "item_type": "SIMPLE", "unit": "Kg",
            "price": "100000", "sellable_qty": "50", "image": None} for i, c in enumerate(CODES)]
CATALOG[2]["sellable_qty"] = "0"  # thẻ thứ 3 hết hàng
LINKS = [{"title": "Chính sách bảo mật", "slug": "chinh-sach-bao-mat"}]


def entry(blocks, kind="post", slug="bai-thu"):
    return {"kind": kind, "slug": slug, "title": "Bài thử QA", "seo_title": "", "description": "", "excerpt": "",
            "category": None, "cover_image": None, "body": {"type": "doc", "blocks": blocks},
            "published_at": "2026-09-28T00:00:00Z", "updated_at": "2026-09-28T00:00:00Z", "version": 1,
            "effective_from": None, "author": "Cá Về"}


PARA = {"type": "paragraph", "children": [{"text": "Đoạn văn giả."}]}
CARDS = [{"type": "item_card", "item_code": c} for c in CODES]
from datetime import datetime, timedelta, timezone
ORDER_201 = {"order_code": "DH-QA-0001", "total_amount": "100000",
             "booked_expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")}

failures, total = [], 0


def check(label, cond, detail=""):
    global total
    total += 1
    ok = bool(cond)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f"  <{detail}>" if (detail and not ok) else ""))
    if not ok:
        failures.append(label)


def resp(route, body, status=200):
    route.fulfill(status=status, content_type="application/json", headers=CORS, body=json.dumps(body))


def setup(page, cfg=None):
    cfg = cfg or {}
    calls = []
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))

    def api(route):
        req = route.request
        path = urlparse(req.url).path
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=CORS)
        calls.append((req.method, path))
        if path == "/api/public/site-info/":
            return resp(route, cfg.get("site", SITE))
        if path == "/api/public/content/footer-links/":
            return resp(route, LINKS)
        if path == "/api/public/content/pages/by-role/privacy/":
            return resp(route, cfg.get("privacy", {"detail": "x"}), 200 if "privacy" in cfg else 404)
        if path.startswith("/api/public/content/entries/") and path != "/api/public/content/entries/":
            spec = cfg.get("entry")
            return resp(route, spec[1], spec[0]) if isinstance(spec, tuple) else resp(route, spec)
        if path == "/api/shop/catalog/":
            spec = cfg.get("catalog", CATALOG)
            return resp(route, spec[1], spec[0]) if isinstance(spec, tuple) else resp(route, spec)
        if path == "/api/shop/orders/" and req.method == "POST":
            return resp(route, ORDER_201, 201)
        return resp(route, {"detail": "Not found."}, 404)

    page.route(f"{API}/**", api)
    return calls, errs


def n(calls, path):
    return sum(1 for m, p in calls if p == path)


def goto(page, path):
    page.goto(f"{BASE}{path}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)

        # ---------------- F7 ----------------
        ctx = b.new_context(viewport={"width": 390, "height": 800})
        page = ctx.new_page()
        calls, errs = setup(page, {"entry": entry([PARA] + CARDS)})
        goto(page, "/bai-viet/?slug=bai-thu")
        cat = n(calls, "/api/shop/catalog/")
        detail = [pp for m, pp in calls if pp.startswith("/api/shop/catalog/") and pp != "/api/shop/catalog/"]
        check("F7 bài 3 thẻ mặt hàng -> đúng 1 request /api/shop/catalog/", cat == 1, str(calls))
        check("F7 bài 3 thẻ -> 0 request /api/shop/catalog/<mã>/", not detail, str(detail))
        body = page.inner_text("article") if page.locator("article").count() else page.inner_text("body")
        check("F7 thẻ 1 và 2 hiện tên + giá VNĐ (chuỗi giá từ API được đổi số)", "Cá QA giả định 1" in body and "Cá QA giả định 2" in body and "100.000" in body, body[:300])
        check("F7 thẻ 3 (sellable_qty=0) báo hết hàng, không hiện nút mua", "hết hàng" in body.lower() or "tạm hết" in body.lower(), body[-300:])
        check("F7 không pageerror", not errs, str(errs))
        page.screenshot(path=f"{SHOT_DIR}/lo7-f7-bai-3-the-390.png", full_page=True)
        ctx.close()

        ctx = b.new_context()
        page = ctx.new_page()
        calls, errs = setup(page, {"entry": entry([PARA])})
        goto(page, "/bai-viet/?slug=bai-thu")
        check("F7 bài KHÔNG có thẻ -> 0 request catalog", n(calls, "/api/shop/catalog/") == 0, str(calls))
        ctx.close()

        ctx = b.new_context()
        page = ctx.new_page()
        calls, errs = setup(page, {"entry": entry([PARA] + CARDS), "catalog": (500, {"detail": "lỗi"})})
        goto(page, "/bai-viet/?slug=bai-thu")
        check("F7 catalog 500 -> vẫn 1 request (không thử lại từng thẻ), bài vẫn đọc được, không pageerror",
              n(calls, "/api/shop/catalog/") == 1 and "Đoạn văn giả." in page.inner_text("body") and not errs, str(calls) + str(errs))
        ctx.close()

        # ---------------- F10 ----------------
        ctx = b.new_context(viewport={"width": 390, "height": 800})
        page = ctx.new_page()
        calls, errs = setup(page)
        goto(page, "/shop/")
        page.get_by_role("button", name="Thêm vào giỏ").first.click()
        base_n = n(calls, "/api/public/site-info/")
        calls.clear()
        goto(page, "/shop/checkout/")
        check("F10 mở checkout (form) -> site-info đúng 1 request (footer + form dùng chung)", n(calls, "/api/public/site-info/") == 1, str(n(calls, "/api/public/site-info/")))
        txt = page.locator('[data-testid="confirmation-policy-notice"]').inner_text()
        check("F10 khối CSKH ở form hiện giờ 07:00-21:00 (nguồn confirmation_policy.working_hours)", "07:00-21:00" in txt and "7:00–20:00" not in txt, txt)
        page.screenshot(path=f"{SHOT_DIR}/lo7-f10-checkout-form-390.png", full_page=True)
        page.fill("#name", "Khách QA Ẩn Danh")
        page.fill("#phone", "0912345678")
        page.fill("#address", "999 Đường Bí Mật QA")
        page.get_by_role("button", name=re.compile("Đặt hàng")).click()
        page.wait_for_timeout(700)
        check("F10 sau khi đặt hàng thành công -> tổng site-info trên màn checkout vẫn <= 1", n(calls, "/api/public/site-info/") <= 1, str(n(calls, "/api/public/site-info/")))
        body = page.inner_text("body")
        check("F10 màn thanh toán hiện 'Đặt hàng thành công'", "Đặt hàng thành công" in body)
        call_box = page.locator('[data-testid="confirm-call-notice"]')
        policy_box = page.locator('[data-testid="confirmation-policy-notice"]')
        check("F10 hộp 'sẽ gọi số đuôi ...' hiện đúng 1 lần và giờ = 07:00-21:00 (cùng nguồn với khối CSKH)",
              call_box.count() == 1 and "07:00-21:00" in call_box.inner_text() and "5678" in call_box.inner_text(), call_box.inner_text() if call_box.count() else "none")
        check("F10 khối CSKH ở màn thanh toán hiện đúng 1 lần, cùng giờ", policy_box.count() == 1 and "07:00-21:00" in policy_box.inner_text() and "Sau khi thanh toán" in policy_box.inner_text())
        check("F10 SĐT đầy đủ không lộ ra ngoài form (chỉ 4 số cuối)", "0912345678" not in body)
        check("F10 không pageerror", not errs, str(errs))
        page.screenshot(path=f"{SHOT_DIR}/lo7-f10-thanh-toan-390.png", full_page=True)
        ctx.close()

        # cờ CSKH tắt -> giờ lấy từ confirm_call_hours, không có khối CSKH
        ctx = b.new_context()
        page = ctx.new_page()
        calls, errs = setup(page, {"site": dict(SITE, confirmation_policy=None, cskh_notice=None)})
        goto(page, "/shop/")
        page.get_by_role("button", name="Thêm vào giỏ").first.click()
        goto(page, "/shop/checkout/")
        page.fill("#name", "Khách QA Ẩn Danh"); page.fill("#phone", "0912345678"); page.fill("#address", "999 Đường Bí Mật QA")
        page.get_by_role("button", name=re.compile("Đặt hàng")).click()
        page.wait_for_timeout(700)
        cb = page.locator('[data-testid="confirm-call-notice"]')
        check("F10 confirmation_policy=null và cskh_notice=null -> hộp gọi xác nhận dùng confirm_call_hours (7:00–20:00), không có khối CSKH",
              cb.count() == 1 and "7:00–20:00" in cb.inner_text() and page.locator('[data-testid="confirmation-policy-notice"]').count() == 0, cb.inner_text() if cb.count() else "none")
        ctx.close()

        # P8b Lô 3: BE mới chỉ trả confirmation_policy; BE cũ chỉ trả cskh_notice -> khối thông báo và giờ gọi vẫn đúng
        only_new = {k: v for k, v in SITE.items() if k != "cskh_notice"}
        only_old = {k: v for k, v in SITE.items() if k != "confirmation_policy"}
        for label, site in (("chỉ confirmation_policy (BE mới)", only_new), ("chỉ cskh_notice (BE cũ)", only_old)):
            ctx = b.new_context()
            page = ctx.new_page()
            calls, errs = setup(page, {"site": site})
            goto(page, "/shop/")
            page.get_by_role("button", name="Thêm vào giỏ").first.click()
            goto(page, "/shop/checkout/")
            box = page.locator('[data-testid="confirmation-policy-notice"]')
            check(f"P8b-L3 {label}: form hiện khối thông báo, giờ 07:00-21:00", box.count() == 1 and "07:00-21:00" in box.inner_text(), box.inner_text() if box.count() else "none")
            page.fill("#name", "Khách QA Ẩn Danh"); page.fill("#phone", "0912345678"); page.fill("#address", "999 Đường Bí Mật QA")
            page.get_by_role("button", name=re.compile("Đặt hàng")).click()
            page.wait_for_timeout(700)
            cb = page.locator('[data-testid="confirm-call-notice"]')
            check(f"P8b-L3 {label}: hộp 'gọi số đuôi' dùng giờ 07:00-21:00, không pageerror", cb.count() == 1 and "07:00-21:00" in cb.inner_text() and not errs, cb.inner_text() if cb.count() else "none")
            ctx.close()

        # site-info lỗi -> checkout không vỡ, không khối nào hiện
        ctx = b.new_context()
        page = ctx.new_page()
        calls, errs = setup(page, {"privacy": {"slug": "chinh-sach-bao-mat", "title": "CS", "version": 1, "version_id": 9, "effective_from": "2026-09-28T00:00:00Z"}})
        page.route(f"{API}/api/public/site-info/", lambda r: r.abort("failed"))  # đăng ký sau -> ưu tiên cao hơn
        goto(page, "/shop/")
        page.get_by_role("button", name="Thêm vào giỏ").first.click()
        goto(page, "/shop/checkout/")
        check("F10 site-info lỗi (có chính sách, mặc định bắt buộc đồng ý) -> form vẫn hiện, không khối CSKH, không pageerror",
              page.locator("#phone").count() == 1 and page.locator('[data-testid="confirmation-policy-notice"]').count() == 0 and not errs, str(errs))
        ctx.close()

        # trang tra đơn: ConfirmCallNotice tự tải -> 1 request
        ctx = b.new_context()
        page = ctx.new_page()
        calls, errs = setup(page)
        goto(page, "/shop/orders/")
        check("F10 trang tra đơn -> site-info đúng 1 request (footer + ConfirmCallNotice dùng chung cache)", n(calls, "/api/public/site-info/") == 1, str(n(calls, "/api/public/site-info/")))
        ctx.close()

        # ---------------- F6 ----------------
        for label, spec in [("404 DRF 'Not found.'", (404, {"detail": "Not found."})), ("410", (410, {"detail": "Bài đã gỡ"})),
                            ("404 tiếng Việt", (404, {"detail": "Không tìm thấy"}))]:
            ctx = b.new_context()
            page = ctx.new_page()
            calls, errs = setup(page, {"entry": spec})
            goto(page, "/bai-viet/?slug=khong-co")
            body = page.inner_text("body")
            check(f"F6 [{label}] trang bài không hiện chữ tiếng Anh 'Not found', không pageerror, không trắng",
                  "Not found" not in body and len(body.strip()) > 80 and not errs, body[:200] + str(errs))
            ctx.close()

        b.close()
    print(f"\nTổng {total} ca, {len(failures)} FAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
