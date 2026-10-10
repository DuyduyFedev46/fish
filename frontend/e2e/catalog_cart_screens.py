"""Chụp các màn danh mục, chi tiết, giỏ ở 360 và 1280 (mock). SHOP-2-03…2-06.
Chạy: NEXT_PUBLIC_USE_MOCK=1 npm run dev -- -p 3107 rồi python3 e2e/catalog_cart_screens.py
"""
import json, os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("QA_BASE", "http://localhost:3107")
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../doc/features/2026-10-06-shop-giao-dien-moi/shots/lo2"))
os.makedirs(OUT, exist_ok=True)
CART = [
    {"item_code": "MUC-ONG", "name": "Mực ống", "unit": "kg", "price": "170000", "qty": 1},
    {"item_code": "CA-THU-KHUC", "name": "Cá thu cắt khúc", "unit": "kg", "price": "150000", "qty": 1.5},
    {"item_code": "CUA-HOANG-DE", "name": "Cua hoàng đế", "unit": "kg", "price": "950000", "qty": 1},
    {"item_code": "COMBO-LAU-HAISAN", "name": "Combo lẩu hải sản", "unit": "combo", "price": "380000", "qty": 1},
]
OLD = [{"item_code": "MUC-ONG", "name": "Mực ống", "unit": "Kg", "price": 180000, "qty": 0.3}]

def run():
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h, tag in ((360, 780, "360"), (1280, 860, "1280")):
            ctx = b.new_context(viewport={"width": w, "height": h})
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            def shot(name, full=False):
                pg.wait_for_timeout(500)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                assert sw <= w + 1, f"{name}: cuộn ngang {sw}>{w}"
                pg.screenshot(path=f"{OUT}/{name}-{tag}.png", full_page=full)
            def setcart(c):
                # Đợi giỏ nạp xong rồi ghi và rời trang, để trang cũ không ghi đè lại.
                pg.wait_for_timeout(1200)
                pg.evaluate("c => localStorage.setItem('cangcaloc_cart_v1', JSON.stringify(c))", c)
                pg.goto("about:blank")
            pg.goto(BASE + "/shop/"); setcart([])
            pg.goto(BASE + "/shop/"); pg.wait_for_selector("article"); shot("catalog")
            pg.goto(BASE + "/shop/?group=muc"); pg.wait_for_selector("article"); shot("catalog-group")
            pg.goto(BASE + "/shop/?q=xyz"); pg.wait_for_selector("text=Không tìm thấy"); shot("catalog-notfound")
            pg.goto(BASE + "/shop/"); pg.wait_for_selector("article")
            pg.locator("button[aria-label^='Thêm 1 kg Mực ống']").first.click(); shot("catalog-toast")
            # gợi ý khi gõ
            box = pg.locator("input[type=search]:visible").first
            box.fill("muc"); pg.wait_for_selector("[role=option]"); shot("search-suggest")
            pg.goto(BASE + "/shop/item/?code=MUC-ONG"); pg.wait_for_selector("h1"); shot("item")
            pg.goto(BASE + "/shop/item/?code=CUA-HOANG-DE"); pg.wait_for_selector("text=đang hết"); shot("item-out")
            pg.goto(BASE + "/shop/item/?code=COMBO-LAU-HAISAN"); pg.wait_for_selector("text=Trong combo"); shot("item-combo")
            pg.goto(BASE + "/shop/item/?code=KHONG-CO"); pg.wait_for_selector("text=Không tìm thấy món này"); shot("item-404")
            setcart([]); pg.goto(BASE + "/shop/cart/"); pg.wait_for_selector("h2:has-text('Giỏ hàng đang trống')"); shot("cart-empty")
            setcart(CART); pg.goto(BASE + "/shop/cart/"); pg.wait_for_selector("text=Món này đã hết"); shot("cart-changed")
            pg.get_by_role("button", name="Tiếp tục", exact=False).filter(has_text="Tiếp tục").first.click()
            pg.wait_for_selector("[role=alert]:has-text('Bỏ món đã hết')"); shot("cart-blocked")
            pg.locator("[data-line-remove]").first.click(); pg.wait_for_timeout(300)
            pg.locator("button[aria-label^='Bỏ Mực ống khỏi giỏ']:visible").first.click(); pg.wait_for_selector("dialog[open]"); shot("cart-remove-dialog")
            setcart(OLD); pg.goto(BASE + "/shop/cart/"); pg.wait_for_selector("text=Số lượng đã chỉnh"); shot("cart-adjusted")
            assert not errs, errs
            ctx.close()
        b.close()
    print("xong", OUT)

run()
