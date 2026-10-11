"""
Đối chiếu 86 màn thiết kế Shop (doc/design/shop/README.md, bảng danh mục) với bản dựng thật (SHOP-7-01 AC1, AC2, G6).

Mỗi màn: dựng đúng trạng thái trên BE thật (đơn thật tạo bằng API, IPN giả lập, đổi tồn/mã bằng lệnh BE; riêng lỗi mạng,
429, 409, 503 dùng chặn/giả phản hồi bằng `page.route` theo contract 02b), chụp ở 360 (điện thoại) hoặc 1280 (máy tính),
render file `screens/*.dc.html` cùng khổ, ghép ảnh cạnh nhau (trái = thiết kế, phải = bản dựng) vào
`shots/lo7/screens/<mã>-<khổ>-sbs.png`, và tự kiểm: không cuộn ngang, không lỗi JS, cụm chữ của thiết kế (bỏ ô [..] và số)
có mặt trên trang. Kết luận PASS/FAIL về bố cục/câu chữ/trạng thái do người xem ảnh ghi (QA), không do kịch bản tự chấm.

Màn không dựng được: C1b/C1c (bản đồ cần khoá Google Maps), D5/DesktopUnderpaid (chuyển thiếu tiền, "không code V1"),
E6 và 2 bảng HeaderFooter (đặc tả, không phải màn).  Kết quả ghi ở `result-design_screens.json` và `screens/manifest.json`.
"""
import datetime as dt
import json
import re
import uuid
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

from shop_e2e_lib import *

R = Report("design_screens")
OUT = shots_dir("screens")
CACHE = workdir() / "design_png"
CACHE.mkdir(exist_ok=True)
tok = login_token()
now = dt.datetime.now(dt.timezone.utc)
SUF = uuid.uuid4().hex[:4].upper()
MANIFEST = []


# ----------------------------------------------------------------------------- dữ liệu nền (đơn ở đủ trạng thái)
def create_voucher(code, **kw):
    d = dict(code=code, name="Mã e2e " + code, kind="PERCENT", value="10", max_discount="50000", min_order_amount="100000",
             starts_at=(now - dt.timedelta(days=1)).isoformat(), ends_at=(now + dt.timedelta(days=30)).isoformat(),
             total_uses=100, customer_terms="Giảm 10%, tối đa 50.000đ")
    d.update(kw)
    api("POST", "/api/catalog/vouchers/", d, token=tok)


V_OK = "SCR" + SUF
create_voucher(V_OK)
create_voucher("EXP" + SUF, starts_at=(now - dt.timedelta(days=9)).isoformat(), ends_at=(now - dt.timedelta(days=1)).isoformat())


def order(items, *, voucher=None, phone=FAKE_PHONE):
    st, o = create_order_api(items, voucher=voucher, phone=phone)
    assert st == 201, (st, o)
    return o


def paid(o):
    st, r = pay_order(o["order_code"], o["total_amount"])
    assert r["matched"], r
    return o


FX = {}
FX["booked"] = order([("CA-THU", "1.5"), ("COMBO-BEP-NHA", "1")], voucher=V_OK)
FX["booked_plain"] = order([("CA-THU", "1.5"), ("COMBO-BEP-NHA", "1")])
FX["hold_expired"] = order([("GHE-XANH", "1")])
expire_hold(FX["hold_expired"]["order_code"])
FX["expired"] = order([("GHE-XANH", "1")])
expire_hold(FX["expired"]["order_code"])
FX["paid"] = paid(order([("CA-THU", "1.5"), ("COMBO-BEP-NHA", "1")], voucher=V_OK))
FX["delivered"] = paid(order([("CA-THU", "2")]))
FX["failed"] = paid(order([("BACH-TUOC", "1")]))
FX["cancelled"] = paid(order([("GHE-XANH", "1")]))
FX["partial"] = paid(order([("CA-THU", "1"), ("BACH-TUOC", "1")]))
FX["delivering"] = paid(order([("CA-HOI-NU", "1")]))
FX["confirming"] = paid(order([("CA-HOI-NU", "1")]))
set_delivery_status(FX["delivered"]["order_code"], "COMPLETED")
manage_shell("from apps.sales.models import SalesOrder\nSalesOrder.objects.filter(code=%r).update(status='COMPLETED')" % FX["delivered"]["order_code"])
set_delivery_status(FX["failed"]["order_code"], "FAILED")
set_delivery_status(FX["delivering"]["order_code"], "DELIVERING")
set_delivery_status(FX["confirming"]["order_code"], "CONFIRMING")
cancel_paid(FX["cancelled"]["order_code"])
manage_shell(
    "from apps.sales.models import SalesOrder\nfrom apps.sales.refunds import services\nfrom django.contrib.auth import get_user_model\n"
    f"o=SalesOrder.objects.get(code={FX['partial']['order_code']!r})\nu=get_user_model().objects.get(username='qa_owner')\n"
    "services.create_refund(invoice=o.invoice, amount=100000, is_partial=True, reason='Một phần hàng không đạt (giả)', actor=u)\n")
run_expiry_job()   # FX['expired'] -> AUTO_CANCELLED

CATALOG = api("GET", "/api/shop/catalog/")[1]["items"]
POST_SLUG = None
st, ents = api("GET", "/api/public/content/entries/?kind=post")
if st == 200:
    rows = ents.get("results", ents) if isinstance(ents, dict) else ents
    POST_SLUG = rows[0]["slug"] if rows else None


# ----------------------------------------------------------------------------- tiện ích trình duyệt
class Ctx:
    def __init__(self, browser, width):
        self.width = width
        h = 844 if width < 600 else 800
        self.ctx = browser.new_context(viewport={"width": width, "height": h})
        self.page = self.ctx.new_page()
        self.watch = PageWatch(self.page)

    def close(self):
        self.ctx.close()


def set_cart(page, lines):
    page.goto(SHOP + "/shop/orders/")
    page.wait_for_load_state("networkidle")
    page.evaluate("(l)=>localStorage.setItem('cangcaloc_cart_v1', JSON.stringify(l))", lines)


def cart_line(code, qty, name=None, price=None, unit="kg"):
    item = next(i for i in CATALOG if i["item_code"] == code)
    return {"item_code": code, "name": name or item["name"], "unit": item["unit"], "price": price or item["price"], "qty": qty}


def open_order(page, key, query=""):
    o = FX[key]
    page.goto(SHOP + "/shop/orders/")
    page.wait_for_load_state("networkidle")
    page.evaluate("(a)=>sessionStorage.setItem('cangcaloc_order_tokens_v1', JSON.stringify({[a[0]]:a[1]}))", [o["order_code"], o["lookup_token"]])
    goto(page, f"/shop/orders/?code={o['order_code']}{query}", 900)


def fill_form(page, phone=FAKE_PHONE):
    page.fill("#f-name", FAKE_NAME)
    page.fill("#f-phone", phone)
    page.fill("#f-addr", FAKE_ADDRESS)
    if page.locator("#f-consent").count():
        page.locator("#f-consent").check()


def to_checkout(page, lines):
    set_cart(page, lines)
    goto(page, "/shop/checkout/", 900)


STD_CART = lambda: [cart_line("CA-THU", 1.5), cart_line("COMBO-BEP-NHA", 1), cart_line("MUC-ONG", 1)]

def hold_runs_out(c):
    """D4 là popup khi đồng hồ về 0 LÚC KHÁCH ĐANG XEM (AC3, job chưa chạy): dựng đơn còn 5 giây rồi chờ."""
    o = order([("GHE-XANH", "1")])
    FX["hold_live"] = o
    expire_hold_in(o["order_code"], 5)
    open_order(c.page, "hold_live")
    c.page.wait_for_selector("[role=dialog]", timeout=20000)
    c.page.wait_for_timeout(600)
    return c.page


# ----------------------------------------------------------------------------- các màn
S = []   # (id, nhãn, file thiết kế, khổ, kiểu chụp, hàm dựng, ghi chú)


def screen(sid, label, design, width, mode="full", note=""):
    def deco(fn):
        S.append((sid, label, design, width, mode, fn, note))
        return fn
    return deco


M, D = 360, 1280

# ---- A Chọn hàng (điện thoại)
@screen("A1", "Trang chủ", "Home", M)
def _(c): goto(c.page, "/"); return c.page

@screen("A2", "Danh mục", "Main", M)
def _(c): goto(c.page, "/shop/"); return c.page

@screen("A3", "Chi tiết sản phẩm", "Product", M)
def _(c): goto(c.page, "/shop/item/?code=CA-THU"); return c.page

@screen("A4", "[Popup] Đã thêm vào giỏ", "A4-Toast", M, "viewport")
def _(c):
    goto(c.page, "/shop/")
    c.page.get_by_role("button", name=re.compile(r"^Thêm 1\s(kg|combo)")).nth(2).evaluate("e => e.click()"); c.page.wait_for_timeout(700)
    return c.page

@screen("A5", "Lỗi · Tìm không thấy", "A5-NotFound", M, "viewport")
def _(c): goto(c.page, "/shop/?q=zzzkhongco"); return c.page

@screen("A6", "Lỗi · Mất mạng, không tải được hàng", "A6-Offline", M, "viewport")
def _(c):
    c.page.route("**/api/shop/catalog/", lambda r: r.abort("internetdisconnected"))
    goto(c.page, "/shop/"); return c.page

@screen("A7", "Ngoại lệ · Sản phẩm tạm hết", "A7-OutOfStock", M)
def _(c): goto(c.page, "/shop/item/?code=TOM-SU-1"); return c.page

@screen("A8", "Trạng thái · Đang tải", "A0-Loading", M, "viewport")
def _(c):
    c.page.route("**/api/shop/catalog/", lambda r: None)    # treo yêu cầu: giữ trạng thái đang tải
    c.page.goto(SHOP + "/shop/"); c.page.wait_for_timeout(1200); return c.page

@screen("A9", "[Popup] Gợi ý khi gõ tìm", "A8-SearchSuggest", M, "viewport")
def _(c):
    goto(c.page, "/shop/")
    box = c.page.locator("input[type=search]:visible").first
    box.click(); box.fill("muc"); c.page.wait_for_timeout(900); return c.page

@screen("A10", "Chi tiết combo", "A9-ComboDetail", M)
def _(c): goto(c.page, "/shop/item/?code=COMBO-BEP-NHA"); return c.page

# ---- B Giỏ hàng & mã
@screen("B1", "Giỏ hàng", "Cart", M, "viewport")
def _(c): set_cart(c.page, STD_CART()); goto_cart(c.page); return c.page

@screen("B2", "[Popup] Xác nhận bỏ món", "B2-RemoveConfirm", M, "viewport")
def _(c):
    set_cart(c.page, [cart_line("CA-THU", 1)]); goto_cart(c.page)
    c.page.get_by_role("button", name=re.compile(r"^Bỏ Cá thu")).first.click() if False else None
    c.page.get_by_role("button", name=re.compile(r"^Bỏ Cá thu khỏi giỏ")).first.click(); c.page.wait_for_timeout(500)
    return c.page

@screen("B3", "Ngoại lệ · Giá đổi / món đã hết trong giỏ", "B3-CartChanged", M, "viewport")
def _(c):
    set_cart(c.page, [cart_line("CA-THU", 1.5, price="150000"), cart_line("TOM-SU-1", 1), cart_line("MUC-ONG", 1)])
    goto_cart(c.page); c.page.wait_for_timeout(800); return c.page

@screen("B4", "Ngoại lệ · Giỏ trống", "B4-CartEmpty", M, "viewport")
def _(c): goto(c.page, "/shop/cart/"); return c.page

@screen("B5", "[Popup] Nhập mã giảm giá", "B5-VoucherSheet", M, "viewport")
def _(c):
    set_cart(c.page, STD_CART()); goto_cart(c.page)
    c.page.get_by_role("button", name="Nhập mã").click(); c.page.wait_for_timeout(500); return c.page

@screen("B6", "Happy · Đã áp mã giảm giá", "B6-VoucherApplied", M, "viewport")
def _(c):
    set_cart(c.page, STD_CART()); goto_cart(c.page)
    c.page.get_by_role("button", name="Nhập mã").click(); c.page.wait_for_timeout(400)
    c.page.locator("input[type=text]:visible").last.fill(V_OK)
    c.page.get_by_role("button", name="Áp dụng").locator("visible=true").last.click(); c.page.wait_for_timeout(1500); return c.page

@screen("B7", "Lỗi · Mã giảm giá không dùng được", "B7-VoucherError", M, "viewport")
def _(c):
    set_cart(c.page, STD_CART()); goto_cart(c.page)
    c.page.get_by_role("button", name="Nhập mã").click(); c.page.wait_for_timeout(400)
    c.page.locator("input[type=text]:visible").last.fill("EXP" + SUF)
    c.page.get_by_role("button", name="Áp dụng").locator("visible=true").last.click(); c.page.wait_for_timeout(1200); return c.page

# ---- C Đặt hàng
@screen("C1", "Happy · Thông tin nhận hàng", "Checkout", M, "viewport")
def _(c): to_checkout(c.page, STD_CART()); return c.page

@screen("C1b", "[Popup] Chọn vị trí trên Google Maps", "C1b-MapPicker", M, "viewport", "needs-maps-key")
def _(c):
    to_checkout(c.page, STD_CART())
    c.page.get_by_role("button", name=re.compile("Tìm và chọn địa chỉ")).click(); c.page.wait_for_timeout(1200)
    return c.page

@screen("C1c", "Happy · Địa chỉ tự điền từ bản đồ", "C1c-AddressFilled", M, "viewport", "needs-maps-key")
def _(c): return None

@screen("C2", "Lỗi · Nhập thiếu / sai", "C2-Invalid", M, "viewport")
def _(c):
    to_checkout(c.page, STD_CART())
    c.page.fill("#f-phone", "12345")
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(600); return c.page

@screen("C3", "[Popup] Hết hàng lúc đặt (E-06)", "C3-SoldOut", M, "viewport")
def _(c):
    to_checkout(c.page, [cart_line("CA-HOI-NU", 1), cart_line("MUC-ONG", 2), cart_line("CA-THU", 1)])
    fill_form(c.page)
    stock_set("CA-HOI-NU", 0); stock_set("MUC-ONG", 1)
    try:
        c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(1500)
    finally:
        pass
    c._restore = lambda: (stock_set("CA-HOI-NU", 20), stock_set("MUC-ONG", 2))
    return c.page

@screen("C4", "[Popup] Lỗi kết nối khi đặt", "C4-NetworkError", M, "viewport")
def _(c):
    to_checkout(c.page, STD_CART()); fill_form(c.page)
    c.page.route("**/api/shop/orders/", lambda r: r.abort("internetdisconnected"))
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(1500); return c.page

@screen("C5", "[Popup] Không lấy được vị trí / bản đồ lỗi", "C5-LocationDenied", M, "viewport", "needs-maps-key")
def _(c):
    to_checkout(c.page, STD_CART())
    c.page.get_by_role("button", name=re.compile("Tìm và chọn địa chỉ")).click(); c.page.wait_for_timeout(1200); return c.page

@screen("C6", "[Popup] Mã hết hiệu lực lúc đặt", "B8-VoucherInvalidAtOrder", M, "viewport")
def _(c):
    code = "GON" + uuid.uuid4().hex[:5].upper()
    create_voucher(code)
    set_cart(c.page, STD_CART()); goto_cart(c.page)
    c.page.get_by_role("button", name="Nhập mã").click(); c.page.wait_for_timeout(400)
    c.page.locator("input[type=text]:visible").last.fill(code)
    c.page.get_by_role("button", name="Áp dụng").locator("visible=true").last.click(); c.page.wait_for_timeout(1000)
    c.page.get_by_role("button", name=re.compile("^Tiếp tục")).click(); c.page.wait_for_url(re.compile("checkout"))
    c.page.wait_for_selector(f"text=Mã giảm giá ({code})", timeout=10000)
    fill_form(c.page)
    vid = [v for v in api("GET", "/api/catalog/vouchers/?status=running", token=tok)[1]["results"] if v["code"] == code][0]["id"]
    api("POST", f"/api/catalog/vouchers/{vid}/disable/", {"reason": "OTHER", "note": "e2e"}, token=tok)
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(1500); return c.page

@screen("C7", "Ngoại lệ · Shop tạm ngưng nhận đơn", "X2-ShopPaused", M, "viewport")
def _(c):
    to_checkout(c.page, STD_CART()); fill_form(c.page)
    c.page.route("**/api/shop/orders/", lambda r: r.fulfill(status=503, content_type="application/json", body=json.dumps(
        {"detail": "Shop tạm chưa nhận đơn.", "code": "SHOP_CLOSED"})))
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(1500); return c.page

@screen("C8", "[Popup] Thao tác quá nhanh (429)", "X3-TooManyRequests", M, "viewport")
def _(c):
    to_checkout(c.page, STD_CART()); fill_form(c.page)
    c.page.route("**/api/shop/orders/", lambda r: r.fulfill(status=429, headers={"Retry-After": "60"}, content_type="application/json",
                                                            body=json.dumps({"detail": "Request was throttled. Expected available in 60 seconds."})))
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(1500); return c.page

@screen("C9", "[Popup] Chính sách vừa cập nhật (409)", "X4-PolicyChanged", M, "viewport")
def _(c):
    to_checkout(c.page, STD_CART()); fill_form(c.page)
    c.page.route("**/api/shop/orders/", lambda r: r.fulfill(status=409, content_type="application/json", body=json.dumps(
        {"detail": "Chính sách vừa cập nhật, vui lòng xem và đồng ý lại.", "code": "POLICY_CHANGED",
         "current": {"version": 2, "version_id": 999999, "slug": "quyen-rieng-tu"}})))
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(1500); return c.page

# ---- D Thanh toán
@screen("D1", "Happy · Thanh toán", "Payment", M, "viewport")
def _(c): open_order(c.page, "booked"); return c.page

@screen("D2", "Lỗi · Huỷ / lỗi trên cổng thanh toán", "D2-PayCancelled", M, "viewport")
def _(c): open_order(c.page, "booked", "&result=cancel"); return c.page

@screen("D3", "Ngoại lệ · Đang chờ xác nhận tiền", "D3-PayPending", M, "viewport")
def _(c): open_order(c.page, "booked", "&result=success"); return c.page

@screen("D4", "[Popup] Hết giờ giữ hàng (E-01)", "D4-Expired", M, "viewport")
def _(c): return hold_runs_out(c)

@screen("D5", "Ngoại lệ · Chuyển thiếu tiền (E-02)", "D5-Underpaid", M, "viewport", "not-coded-v1")
def _(c): return None

@screen("D6", "[Popup] Rời trang thanh toán?", "D6-LeavePayment", M, "viewport")
def _(c):
    open_order(c.page, "booked")
    c.page.get_by_role("button", name=re.compile("^Quay lại")).first.click(); c.page.wait_for_timeout(600); return c.page

# ---- E Sau thanh toán
@screen("E1", "Happy · Thanh toán xong → trang đơn hàng", "Success", M)
def _(c): open_order(c.page, "paid", "&result=success"); return c.page

@screen("E2", "Ngoại lệ · Đơn bị huỷ → Cá Về gọi lại", "E2-Cancelled", M, "viewport")
def _(c): open_order(c.page, "cancelled"); return c.page

@screen("E3", "Happy · Đơn đã giao", "E3-Delivered", M, "viewport")
def _(c): open_order(c.page, "delivered"); return c.page

@screen("E4", "Ngoại lệ · Giao không thành công", "E4-DeliveryFailed", M, "viewport")
def _(c): open_order(c.page, "failed"); return c.page

@screen("E5", "Ngoại lệ · Huỷ một phần đơn", "E5-PartialCancel", M)
def _(c): open_order(c.page, "partial"); return c.page

@screen("E6", "Đặc tả · Trạng thái đơn quyết định màn hiển thị", "E6-StatusRules", D, "spec", "spec-not-screen")
def _(c): return None

# ---- F Tra cứu & trang phụ
@screen("F1", "Happy · Tra cứu đơn", "F1-Lookup", M, "viewport")
def _(c): goto(c.page, "/shop/orders/"); return c.page

@screen("F2", "Lỗi · Không tìm thấy đơn", "F2-LookupNotFound", M, "viewport")
def _(c):
    goto(c.page, "/shop/orders/")
    c.page.wait_for_selector("#lookup-code", timeout=15000); c.page.fill("#lookup-code", "SO000000-ZZZZZZ"); c.page.fill("#lookup-phone", "0900000002")
    c.page.get_by_role("button", name="Tra cứu").click(); c.page.wait_for_timeout(1500); return c.page

@screen("F3", "Trang chính sách (mẫu)", "P1-Policy", M)
def _(c): goto(c.page, "/pages/?slug=doi-tra"); return c.page

@screen("F4", "Trang liên hệ", "P2-Contact", M, "viewport")
def _(c): goto(c.page, "/pages/?slug=lien-he"); return c.page

@screen("F5", "Trang cách mua hàng", "P3-HowToBuy", M)
def _(c): goto(c.page, "/pages/?slug=cach-mua-hang"); return c.page

@screen("F6", "Góc bếp · danh sách", "G1-KitchenList", M)
def _(c): goto(c.page, "/blog/"); return c.page

@screen("F7", "Góc bếp · bài viết", "G2-KitchenArticle", M)
def _(c): goto(c.page, f"/blog/?slug={POST_SLUG}"); return c.page

@screen("F8", "Lỗi · Không tìm thấy trang (404)", "X1-NotFound404", M, "viewport")
def _(c): c.page.goto(SHOP + "/khong-co-trang-nay/"); c.page.wait_for_load_state("networkidle"); c.page.wait_for_timeout(500); return c.page

# ---- Máy tính · luồng mua
@screen("DK1", "Máy tính · Trang chủ", "DesktopHome", D)
def _(c): goto(c.page, "/"); return c.page

@screen("DK2", "Máy tính · Danh mục", "DesktopCategory", D)
def _(c): goto(c.page, "/shop/"); return c.page

@screen("DK3", "Máy tính · Chi tiết sản phẩm", "DesktopProduct", D)
def _(c): goto(c.page, "/shop/item/?code=CA-THU"); return c.page

@screen("DK4", "Máy tính · Giỏ hàng", "DesktopCart", D)
def _(c): set_cart(c.page, STD_CART()); goto_cart(c.page); return c.page

@screen("DK5", "Máy tính · Thông tin nhận hàng", "DesktopCheckout", D)
def _(c): to_checkout(c.page, STD_CART()); return c.page

@screen("DK6", "Máy tính · Thanh toán", "DesktopPayment", D)
def _(c): open_order(c.page, "booked"); return c.page

@screen("DK7", "Máy tính · Đơn hàng sau thanh toán", "DesktopSuccess", D)
def _(c): open_order(c.page, "paid", "&result=success"); return c.page

# ---- Máy tính · popup
@screen("DP1", "Máy tính · [Popup] Hết hàng lúc đặt", "DesktopModalSoldOut", D, "viewport")
def _(c):
    to_checkout(c.page, [cart_line("CA-HOI-NU", 1), cart_line("MUC-ONG", 2), cart_line("CA-THU", 1)]); fill_form(c.page)
    stock_set("CA-HOI-NU", 0); stock_set("MUC-ONG", 1)
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(1500)
    c._restore = lambda: (stock_set("CA-HOI-NU", 20), stock_set("MUC-ONG", 2))
    return c.page

@screen("DP2", "Máy tính · [Popup] Hết giờ giữ hàng", "DesktopModalExpired", D, "viewport")
def _(c): return hold_runs_out(c)

@screen("DP3", "Máy tính · [Popup] Chọn vị trí Google Maps", "DesktopMapPicker", D, "viewport", "needs-maps-key")
def _(c):
    to_checkout(c.page, STD_CART())
    c.page.get_by_role("button", name=re.compile("Tìm và chọn địa chỉ")).click(); c.page.wait_for_timeout(1200); return c.page

@screen("DP4", "Máy tính · [Popup] Gợi ý khi gõ tìm", "DesktopSearchSuggest", D, "viewport")
def _(c):
    goto(c.page, "/shop/")
    box = c.page.locator("input[type=search]:visible").first
    box.click(); box.fill("muc"); c.page.wait_for_timeout(900); return c.page

@screen("DP5", "Máy tính · [Popup] Xác nhận bỏ món", "DesktopRemoveConfirm", D, "viewport")
def _(c):
    set_cart(c.page, [cart_line("CA-THU", 1)]); goto_cart(c.page)
    c.page.get_by_role("button", name=re.compile(r"^Bỏ Cá thu khỏi giỏ")).first.click(); c.page.wait_for_timeout(500); return c.page

@screen("DP6", "Máy tính · [Popup] Lỗi kết nối khi đặt", "DesktopNetworkError", D, "viewport")
def _(c):
    to_checkout(c.page, STD_CART()); fill_form(c.page)
    c.page.route("**/api/shop/orders/", lambda r: r.abort("internetdisconnected"))
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(1500); return c.page

@screen("DP7", "Máy tính · [Popup] Rời trang thanh toán?", "DesktopLeavePayment", D, "viewport")
def _(c):
    open_order(c.page, "booked")
    c.page.get_by_role("link", name=re.compile("trang chủ", re.I)).first.click(); c.page.wait_for_timeout(600); return c.page

# ---- Máy tính · lỗi & ngoại lệ
@screen("DE1", "Máy tính · Lỗi · Tìm không thấy", "DesktopNotFound", D)
def _(c): goto(c.page, "/shop/?q=zzzkhongco"); return c.page

@screen("DE2", "Máy tính · Ngoại lệ · Sản phẩm hết hàng", "DesktopOutOfStock", D)
def _(c): goto(c.page, "/shop/item/?code=TOM-SU-1"); return c.page

@screen("DE3", "Máy tính · Lỗi · Nhập thiếu / sai", "DesktopInvalid", D)
def _(c):
    to_checkout(c.page, STD_CART()); c.page.fill("#f-phone", "12345")
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(600); return c.page

@screen("DE4", "Máy tính · Lỗi · Thanh toán chưa thành công", "DesktopPayCancelled", D)
def _(c): open_order(c.page, "booked", "&result=cancel"); return c.page

@screen("DE5", "Máy tính · Ngoại lệ · Đang chờ xác nhận tiền", "DesktopPayPending", D)
def _(c): open_order(c.page, "booked", "&result=success"); return c.page

@screen("DE6", "Máy tính · Lỗi · Tra cứu không thấy đơn", "DesktopLookup", D)
def _(c):
    goto(c.page, "/shop/orders/")
    c.page.wait_for_selector("#lookup-code", timeout=15000); c.page.fill("#lookup-code", "SO000000-ZZZZZZ"); c.page.fill("#lookup-phone", "0900000002")
    c.page.get_by_role("button", name="Tra cứu").click(); c.page.wait_for_timeout(1500); return c.page

@screen("DE7", "Máy tính · [Toast] Đã thêm vào giỏ + giỏ mini", "DesktopToast", D)
def _(c):
    goto(c.page, "/shop/")
    c.page.get_by_role("button", name=re.compile(r"^Thêm 1\s(kg|combo)")).nth(2).evaluate("e => e.click()"); c.page.wait_for_timeout(700); return c.page

@screen("DE8", "Máy tính · Trạng thái · Đang tải", "DesktopLoading", D)
def _(c):
    c.page.route("**/api/shop/catalog/", lambda r: None)
    c.page.goto(SHOP + "/shop/"); c.page.wait_for_timeout(1200); return c.page

@screen("DE9", "Máy tính · Lỗi · Mất mạng", "DesktopOffline", D)
def _(c):
    c.page.route("**/api/shop/catalog/", lambda r: r.abort("internetdisconnected"))
    goto(c.page, "/shop/"); return c.page

@screen("DE10", "Máy tính · Happy · Chi tiết combo", "DesktopComboDetail", D)
def _(c): goto(c.page, "/shop/item/?code=COMBO-BEP-NHA"); return c.page

@screen("DE11", "Máy tính · Ngoại lệ · Giỏ đổi giá / món hết", "DesktopCartChanged", D)
def _(c):
    set_cart(c.page, [cart_line("CA-THU", 1.5, price="150000"), cart_line("TOM-SU-1", 1), cart_line("MUC-ONG", 1)])
    goto(c.page, "/shop/cart/", 2000); return c.page

@screen("DE12", "Máy tính · Ngoại lệ · Chuyển thiếu tiền", "DesktopUnderpaid", D, "full", "not-coded-v1")
def _(c): return None

@screen("DE13", "Máy tính · Mã giảm giá đã áp", "DesktopVoucher", D)
def _(c):
    set_cart(c.page, STD_CART()); goto_cart(c.page)
    box = c.page.locator("input[type=text]:visible").last
    box.fill(V_OK); c.page.get_by_role("button", name="Áp dụng").locator("visible=true").last.click(); c.page.wait_for_timeout(1500); return c.page

@screen("DE14", "Máy tính · Ngoại lệ · Shop tạm ngưng nhận đơn", "DesktopShopPaused", D)
def _(c):
    to_checkout(c.page, STD_CART()); fill_form(c.page)
    c.page.route("**/api/shop/orders/", lambda r: r.fulfill(status=503, content_type="application/json", body=json.dumps(
        {"detail": "Shop tạm chưa nhận đơn.", "code": "SHOP_CLOSED"})))
    c.page.get_by_role("button", name="Đặt hàng").click(); c.page.wait_for_timeout(1500); return c.page

# ---- Máy tính · đơn hàng & trang phụ
@screen("DO1", "Máy tính · Đơn · Đã giao", "DesktopOrderStates", D, "full", "states-3:delivered")
def _(c): open_order(c.page, "delivered"); return c.page

@screen("DO2", "Máy tính · Đơn · Giao không thành công", "DesktopOrderStates", D, "full", "states-3:failed")
def _(c): open_order(c.page, "failed"); return c.page

@screen("DO3", "Máy tính · Đơn · Bị huỷ", "DesktopOrderStates", D, "full", "states-3:cancelled")
def _(c): open_order(c.page, "cancelled"); return c.page

@screen("DO4", "Máy tính · Trang chính sách", "DesktopPolicy", D, "full", "policy+howto")
def _(c): goto(c.page, "/pages/?slug=doi-tra"); return c.page

@screen("DO5", "Máy tính · Trang cách mua hàng (nửa dưới DesktopPolicy)", "DesktopPolicy", D, "full", "policy+howto")
def _(c): goto(c.page, "/pages/?slug=cach-mua-hang"); return c.page

@screen("DO6", "Máy tính · Trang liên hệ", "DesktopContact", D)
def _(c): goto(c.page, "/pages/?slug=lien-he"); return c.page

@screen("DO7", "Máy tính · Góc bếp · danh sách", "DesktopKitchenList", D)
def _(c): goto(c.page, "/blog/"); return c.page

@screen("DO8", "Máy tính · Góc bếp · bài viết", "DesktopKitchenArticle", D)
def _(c): goto(c.page, f"/blog/?slug={POST_SLUG}"); return c.page

@screen("DO9", "Máy tính · 404", "DesktopNotFound404", D, "viewport")
def _(c): c.page.goto(SHOP + "/khong-co-trang-nay/"); c.page.wait_for_load_state("networkidle"); c.page.wait_for_timeout(500); return c.page

# ---- Đặc tả header/footer + landing
@screen("HF1", "Đặc tả Header & footer · điện thoại", "HeaderFooter-Mobile", M, "full", "spec-headerfooter")
def _(c): goto(c.page, "/"); return c.page

@screen("HF2", "Đặc tả Header & footer · máy tính", "HeaderFooter-Desktop", D, "full", "spec-headerfooter")
def _(c): goto(c.page, "/"); return c.page

@screen("L1", "Landing giới thiệu thương hiệu · máy tính", "Landing", D)
def _(c): goto(c.page, "/about/"); return c.page

@screen("L2", "Landing giới thiệu thương hiệu · điện thoại", "LandingMobile", M)
def _(c): goto(c.page, "/about/"); return c.page


def goto_cart(page):
    goto(page, "/shop/cart/")
    page.wait_for_selector("text=Tóm tắt đơn", timeout=10000)
    page.wait_for_timeout(500)


# ----------------------------------------------------------------------------- chạy + ghép ảnh
def render_design(browser, name, width):
    png = CACHE / f"{name}.png"
    txt = CACHE / f"{name}.txt"
    if png.exists() and txt.exists():
        return png, txt.read_text()
    pg = browser.new_page(viewport={"width": 1280 if width >= 600 else 390, "height": 900})
    pg.goto("file://" + str(DESIGN_DIR / f"{name}.dc.html"))
    pg.wait_for_timeout(1300)
    pg.screenshot(path=str(png), full_page=True)
    text = pg.inner_text("x-dc")
    pg.close()
    txt.write_text(text)
    return png, text


def phrases(text):
    out = []
    for line in text.split("\n"):
        line = line.replace(" ", " ").strip()
        if len(line) < 6 or "[" in line or "{{" in line or re.fullmatch(r"[\d.,\sđ₫kg%·:\-−+/]+", line):
            continue
        out.append(line)
    return out


def norm(s):
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip().lower()


def side_by_side(design_png, actual_png, out_png, label, mobile):
    a = Image.open(design_png).convert("RGB")
    b = Image.open(actual_png).convert("RGB")
    cap_w = 620 if not mobile else 420
    def fit(im):
        ratio = cap_w / im.width
        h = min(int(im.height * ratio), 2400)
        return im.resize((cap_w, int(im.height * ratio))).crop((0, 0, cap_w, h))
    a, b = fit(a), fit(b)
    h = max(a.height, b.height) + 28
    canvas = Image.new("RGB", (a.width + b.width + 30, h), "white")
    canvas.paste(a, (0, 28)); canvas.paste(b, (a.width + 30, 28))
    d = ImageDraw.Draw(canvas)
    d.text((6, 6), f"THIẾT KẾ  |  {label}", fill=(200, 0, 0))
    d.text((a.width + 36, 6), "BẢN DỰNG", fill=(0, 120, 0))
    canvas.save(out_png)


def header_footer_links_check():
    """HF1/HF2 là bảng đặc tả từng link (không phải màn): kiểm href thật của đầu trang và chân trang theo bảng."""
    expected = {
        "header": ["/", "/shop/orders/", "/shop/cart/", "/pages/?slug=cach-mua-hang", "/about/"],
        "footer": ["/shop/", "/pages/?slug=cach-mua-hang", "/shop/orders/", "/pages/?slug=doi-tra", "/pages/?slug=giao-hang",
                   "/pages/?slug=thanh-toan", "/pages/?slug=quyen-rieng-tu", "/pages/?slug=dieu-khoan", "/pages/?slug=khieu-nai",
                   "/about/", "/blog/", "/pages/?slug=lien-he"],
    }
    with sync_playwright() as p2:
        br = p2.chromium.launch()
        for width in (360, 1280):
            c = Ctx(br, width)
            goto(c.page, "/", 900)
            try:
                c.page.wait_for_selector("footer a[href*='slug=']", timeout=10000)
                c.page.wait_for_selector("header a[href^='tel:'], footer a[href^='tel:']", timeout=10000)
            except Exception:  # noqa: BLE001
                pass
            for part, sel in (("header", "header"), ("footer", "footer")):
                if width < 600 and part == "footer":
                    for b in c.page.locator("footer button[aria-expanded=false]").all():
                        b.click()
                hrefs = [h.replace(SHOP, "") for h in c.page.eval_on_selector_all(f"{sel} a[href]", "e=>e.map(x=>x.getAttribute('href'))")]
                hrefs = [h if "?" in h or h.endswith("/") or h.startswith("tel:") or h.startswith("mailto:") else h + "/" for h in hrefs]
                miss = [h for h in expected[part] if h not in hrefs]
                if width < 600 and part == "header":
                    miss = [h for h in miss if h not in ("/pages/?slug=cach-mua-hang", "/about/")]   # điện thoại: header gọn (H1), hai link này nằm ở chân trang
                R.ok(f"HF {part} ({width}): có đủ link theo bảng đặc tả", not miss, miss)
            tel = c.page.locator("header a[href^='tel:'], footer a[href^='tel:']").count()
            R.ok(f"HF ({width}): có link gọi hotline (tel:)", tel >= 1, tel)
            c.close()
        br.close()


def main():
    only = os.environ.get("SCREENS")
    wanted = set(only.split(",")) if only else None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for sid, label, design, width, mode, fn, note in S:
            if wanted and sid not in wanted:
                continue
            row = {"id": sid, "label": label, "design": design, "width": width, "note": note}
            if note in ("not-coded-v1", "spec-not-screen") or (note == "needs-maps-key" and sid in ("C1c",)):
                why = {"not-coded-v1": "D5/Underpaid: chuyển thiếu tiền 'không code V1' (decisions)", "spec-not-screen": "E6 là bảng đặc tả, không phải màn",
                       "needs-maps-key": "cần khoá Google Maps"}[note]
                R.skip(f"{sid} {label}", why)
                row["status"] = "skip"; row["why"] = why
                MANIFEST.append(row)
                render_design(browser, design, width)
                continue
            c = Ctx(browser, width)
            try:
                page = fn(c)
                if note == "needs-maps-key":
                    pass
                full = mode == "full"
                png = OUT / f"{sid}-{width}.png"
                page.screenshot(path=str(png), full_page=full)
                dpng, dtext = render_design(browser, design, width)
                sbs = OUT / f"{sid}-{width}-sbs.png"
                side_by_side(dpng, png, sbs, f"{sid} {label}", width < 600)
                actual_text = norm(page.inner_text("body") + " " + " ".join(page.eval_on_selector_all("[aria-label]", "e=>e.map(x=>x.getAttribute('aria-label'))")))
                missing = [ph for ph in phrases(dtext) if norm(ph) not in actual_text]
                hscroll = page.evaluate("document.documentElement.scrollWidth") > width
                errs = c.watch.console_errors() + c.watch.errors
                row.update({"status": "ok", "png": str(png.name), "sbs": str(sbs.name), "missing": missing[:12], "hscroll": hscroll,
                            "console_errors": errs[:3], "url": page.url.replace(SHOP, "")})
                raw = re.findall(r"\b(BOOKED|PAID|PROCESSING|COMPLETED|CANCELLED|AUTO_CANCELLED|CONFIRMING|PREPARING|READY|DELIVERING|FAILED|SO_FAR)\b|\bTTL\b|undefined|NaN|\[object", page.inner_text("body"))
                row["raw_codes"] = [r for r in raw][:3]
                R.ok(f"{sid} {label} ({width}): chụp được, không cuộn ngang, không lỗi JS, không mã trạng thái thô/TTL/undefined", not hscroll and not errs and not raw, (hscroll, errs[:2], raw[:3]))
            except Exception as e:  # noqa: BLE001
                try:
                    c.page.screenshot(path=str(OUT / f"{sid}-{width}-error.png"))
                    row["error_body"] = c.page.inner_text("body")[:300]
                except Exception:  # noqa: BLE001
                    pass
                row.update({"status": "error", "error": str(e)[:300]})
                R.ok(f"{sid} {label} ({width}): dựng được trạng thái", False, str(e)[:300])
            finally:
                if hasattr(c, "_restore"):
                    c._restore()
                c.close()
            MANIFEST.append(row)
        browser.close()
    header_footer_links_check()
    (OUT / "manifest.json").write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=1))
    R.finish()


if __name__ == "__main__":
    main()
