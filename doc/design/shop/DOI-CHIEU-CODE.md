# Đối chiếu thiết kế Shop mới (prototype 06/10) với code hiện tại

> **Cập nhật 11/10:** một số mục ở đây đã bị thay bởi chốt 10–11/10: bỏ BE-6 (không nút Huỷ đơn), bỏ `search_chips`, mã BR-BH-18/19 thay bằng BR-BH-22…30 và BR-DM-17…25, **bỏ dải chip "Tìm nhiều"**, **bỏ câu "Phí giao: báo khi xác nhận"** (thay bằng "Đã gồm giao hàng…", BR-BH-30). URL Shop nay là `/about/`, `/pages/?slug=`, `/blog/` (11/10). Bảng lô chuẩn: 02b §7.1 của hồ sơ `2026-10-06-shop-giao-dien-moi`. Khi lệch, theo `PLAN.md`, `doc/business-process-spec.md` và `doc/decisions.md`.

> Tech Lead · 2026-10-06 · CHỈ ĐỌC, không sửa repo.

> **Cập nhật sau đối chiếu (06/10):** thiết kế đã sửa theo 3 câu. **Q1:** đã bỏ khối "Giao tới" trên mọi trang đơn hàng.
> **Q3:** popup không đủ hàng chỉ ghi "không đủ hàng", không nêu số kg. **Q5:** mã đơn giữ `SO…` như code, nên không làm BE-8.
> Các câu còn mở là Q2, Q4, Q6, Q7, Q8, Q9 (mục 6), xem thêm `PLAN.md`.
> Nguồn thiết kế: `scratchpad/canvas/project/` (59 board; bỏ `Desktop.dc.html`, `Card-states.dc.html`).
> Code đối chiếu: `frontend/` (HEAD `e73acec`), `backend/apps/catalog/items/shop_api.py`,
> `backend/apps/sales/orders/shop_api.py`, `backend/apps/sales/payments/{shop_api,checkout}.py`, `config/api_urls.py`,
> `doc/business-process-spec.md`, `doc/decisions.md`, `DESIGN.md`, skill `caveve-ui`, `nextjs-shop-patterns`.

Quy ước mức độ: **Critical** (rò dữ liệu cá nhân / giá vốn, chặn go-live) · **High** (sai nghiệp vụ hoặc thiếu API, không code được đúng)
· **Medium** (cần quyết định hoặc việc BE nhỏ) · **Low** (chỉnh FE / câu chữ).

---

## 1. Màn thiết kế → route Next.js → hiện trạng → API → khoảng trống

Nguyên tắc: **một trang Next.js responsive phục vụ cả bản điện thoại (390 px) và máy tính (1280 px)**. Popup trên điện thoại là
bottom sheet, trên máy tính là hộp thoại giữa màn (ghi chú legend trong `canvas.json`). Static export nên giữ kiểu query string
(`?code=`, `?slug=`), không dùng route động `[x]`.

### 1.1 Khung chung (header, footer, điều hướng)

| Thành phần (board) | Đích code | Đã có? | Dữ liệu cần | BE có chưa | Khoảng trống |
|---|---|---|---|---|---|
| H1 header trang chủ (logo, gọi, tra đơn, giỏ + badge, ô tìm, chip "Tìm nhiều") · Desktop H1 2 tầng + menu nhóm + dropdown nhóm con | `components/ShopHeader.tsx` (viết lại, có biến thể) | Có bản đơn giản (`ShopHeader.tsx:1-25`: logo, "Tra cứu đơn", "Giỏ hàng") | hotline, danh sách nhóm (slug, tên, nhóm con), chip tìm nhiều, số món trong giỏ | hotline: `site-info.confirmation_policy.hotline` (`settings.py:304` `SHOP_HOTLINE`). Nhóm: chỉ có **tên nhóm lá** trong catalog (`shop_api.py:22`), `ItemGroup` không có slug (`catalog/models/items.py:12-23`). Chip: **chưa có** | Viết lại header 4 biến thể H1/H2/H3/H4; badge phải là **số món** (code đang là tổng kg `ShopHeader.tsx:7,19`); link giỏ đổi từ `/shop/checkout` sang `/shop/cart` |
| H2 header dính / danh mục · H3 trang con (quay lại `history.back()` dự phòng `/shop`) · H4 đặt hàng (không logo, không giỏ, chữ "Bảo mật") · Desktop H2 rút gọn (Giỏ, Đặt hàng, Thanh toán) | cùng file, prop `variant` | Không | như trên | — | Mới hoàn toàn |
| N1 thanh điều hướng đáy (Trang chủ, Danh mục, Giỏ, Đơn hàng) | **mới** `components/BottomNav.tsx` | Không | số món | — | Hiện ở Trang chủ, Danh mục, Góc bếp; ẩn ở Chi tiết, Giỏ, các bước đặt hàng |
| F1 footer đầy đủ (gọi, Zalo, 3 nhóm link, dải pháp lý, logo BCT) · F2 footer rút gọn (Giỏ, Đặt hàng, Thanh toán) | `components/ShopFooter.tsx` (viết lại) + gộp `features/site/components/SiteLegalFooter.tsx` | Một phần: `ShopFooter.tsx` chỉ 2 dòng; dải người bán + link chính sách CMS nằm ở `SiteLegalFooter` gắn **root layout** (`app/layout.tsx:23`) | tên DN, MST, địa chỉ, ĐKKD, email (có ở `site-info.seller`), **Zalo** (chưa có), link chính sách (có `GET /api/public/content/footer-links/`) | seller: có. Zalo: **chưa**. Footer links: có (CMS `show_in_footer`) | Nhóm "Chính sách" nên render từ CMS footer-links thay vì hard-code 5 link; thêm `zalo` vào site-info; F2 mở link chính sách ở tab mới |
| Logo | `frontend/public/` | Không (chữ "Cá Về") | file logo | — | Duy upload sau → dựng chữ "Cá Về" làm dự phòng, chừa chỗ ảnh 40 px |

Hệ quả cấu trúc: trang chủ `/`, `/bai-viet/`, `/trang/` đều có header có badge giỏ, nên **`CartProvider` phải chuyển từ
`app/shop/layout.tsx:16` lên `app/layout.tsx`**. Footer pháp lý hiện gắn ở root layout cho mọi trang, sẽ bị thay bằng F1/F2.

### 1.2 Luồng mua hàng

| Màn (điện thoại · máy tính) | Route đích | Đã có trong code? | API / field cần | BE có chưa (file:dòng) | Khoảng trống |
|---|---|---|---|---|---|
| **A1** Trang chủ · **Happy 1** Trang chủ (banner, lưới nhóm + đếm món, "Đang có hàng", "Combo nấu nhanh", Góc bếp, cam kết) | `/` (`app/page.tsx` viết lại) | **Không.** `/` hiện là Landing (`app/page.tsx:62-155`) | catalog (tên, giá, đơn vị, `stock_level`, ghi chú ngắn, ảnh, nhóm), bài viết mới | catalog: `GET /api/shop/catalog/` (`catalog/items/shop_api.py:33-44`) thiếu `stock_level`, `unit` combo, ghi chú ngắn, slug nhóm. Bài viết: có (`features/content/components/LatestPosts.tsx`) | Trang mới. Đếm món theo nhóm tính ở FE từ catalog. Ô "Lô mới về" (DesktopHome) cần quy tắc, xem L-24 |
| Landing thương hiệu | `/gioi-thieu/` (**mới**, chuyển nội dung từ `app/page.tsx`) | Có nội dung landing ở `/`, khác bố cục | 3 món mẫu (giá thật) | catalog | Đổi route; sửa link "Vào Shop" về `/`; e2e `ra_soat_cms14_landing.py` sẽ vỡ |
| **A2** Danh mục · **Happy 2** Danh mục (cột lọc nhóm + đếm, sắp xếp Mặc định/Giá ↑/Giá ↓, thẻ có "Thêm 1 kg" → stepper, hết hàng xuống cuối + "Liên hệ chúng tôi", thanh "N món · tổng · Xem giỏ") | `/shop/?q=&group=&type=combo&sort=&focus=search` | Một phần: `app/shop/page.tsx` + `components/CatalogGrid.tsx` liệt kê theo nhóm, hiện "Còn X kg" | như A1 + `min_qty`, `qty_step` | thiếu như trên | Viết lại lưới, lọc, sắp xếp, stepper trên thẻ (FE lọc/sắp xếp tại chỗ vì catalog nhỏ) |
| **A4** Toast "Đã thêm vào giỏ" | trong `/shop/` và chi tiết | Một phần (`AddToCartControl.tsx` đổi chữ nút "Đã thêm ✓" 1,5 s) | — | — | Toast có `aria-live`, nút "Xem giỏ" |
| **A5** Tìm không thấy · Desktop "Lỗi · Tìm không thấy" | `/shop/?q=` (trạng thái rỗng) | Không (chưa có tìm kiếm) | — | — | FE |
| **A6** Mất mạng · **A8** Đang tải (skeleton) | `/shop/` | Một phần (chữ "Đang tải…", banner lỗi, **không có nút thử lại**) | — | — | Skeleton + nút "Thử lại" |
| **A9** Gợi ý khi gõ tìm (tối đa 5 món, "Tìm gần đây") · Desktop popup gợi ý | ô tìm trong header | Không | danh sách món | Không cần endpoint mới: lọc bỏ dấu trên catalog đã tải (vài chục món) | FE; "Tìm gần đây" lưu `localStorage` khoá tiếng Anh (vd `shop_recent_searches_v1`), không phải dữ liệu cá nhân |
| **A3** Chi tiết sản phẩm · **Happy 3** (thư viện ảnh 1/3, mã hàng, nút chọn nhanh 1/1,5/2/3 kg, stepper 0,5, "Tạm tính", bảng thông tin: Quy cách, Bảo quản, Nguồn hàng, Mô tả, cách rã đông) | `/shop/item/?code=` | Có (`app/shop/item/page.tsx`), chỉ tên, giá, "Còn X kg", combo thành phần | `spec`, `storage`, `origin`, `description`, nhiều ảnh, `min_qty`, `qty_step`, `stock_level` | `description` có trong model (`items.py`, field `description`) nhưng **API không trả**; spec/storage/origin **chưa có**; ảnh chỉ 1 (`catalog/models/images.py:24` OneToOne) | Field mới cần migration + màn ERP để Lộc nhập. Thư viện nhiều ảnh: xem L-22 |
| **A7** Sản phẩm tạm hết · Desktop "Sản phẩm hết hàng" (gọi + Zalo, không có nút mua) | `/shop/item/?code=` | Một phần (nút "Hết hàng" bị khoá) | `stock_level="out"`, Zalo | Zalo chưa có | FE |
| **A10** Chi tiết combo (bảng thành phần + kg, stepper theo combo, "Nếu một món hết, combo tạm ngưng") | `/shop/item/?code=` | Một phần (`item/page.tsx:64-76` có danh sách thành phần, nhưng giá hiện "/ kg") | `unit="combo"`, `bundle_components[].qty_per_bundle` | thành phần: có (`shop_api.py:58-66`); `unit` combo: **sai**, luôn `"Kg"` (`shop_api.py:24`) | Xem L-06 |
| **B1** Giỏ hàng · **Happy 4** (bảng món, stepper, "Phí giao: báo khi xác nhận", stepper bước 1-2-3) | `/shop/cart/` (**mới**) | Giỏ đang nằm chung trong `/shop/checkout/` (`CheckoutScreen.tsx:178-260`), +/- theo 1 kg (`:207,215`) | giá hiện hành, `stock_level`, đơn vị | catalog | Tách route; stepper theo `qty_step`; xuống dưới `min_qty` thì hỏi bỏ món (B2) |
| **B2** Xác nhận bỏ món · Desktop popup | `/shop/cart/` | Không (nút × xoá ngay) | — | — | FE |
| **B3** Giá đổi / món đã hết trong giỏ (giá cũ gạch, giá mới, món hết không tính vào tổng) | `/shop/cart/` | Không | giá hiện hành + `stock_level` từng món | **Giá cũ không cần BE**: giỏ đã lưu `price` lúc thêm (`CartContext.tsx:13-19`). FE tải lại catalog khi mở giỏ rồi so | FE so giá; tuỳ chọn BE `cart/quote` (mục 4, BE-9) để tính cả ưu đãi PricingRule |
| **B4** Giỏ trống + gợi ý | `/shop/cart/` | Một phần (một dòng chữ) | catalog | có | FE |
| **C1** Thông tin nhận hàng · **Happy 5** (họ tên, SĐT, **một ô địa chỉ** + nút Bản đồ, ô đồng ý, tóm tắt đơn) | `/shop/checkout/` (bỏ phần giỏ) | Có form 3 ô + đồng ý chính sách (`CheckoutScreen.tsx:262-345`) | `POST /api/shop/orders/` | Có (`sales/orders/shop_api.py:33-65`); `delivery_address` là **một chuỗi** (`:52`) → **khớp** thiết kế một ô | Giữ trạng thái "Shop tạm chưa nhận đơn" (`CheckoutScreen.tsx:83-97`, GL-03-AC5) dù thiết kế không vẽ |
| **C1b** Chọn vị trí Google Maps · **C1c** Địa chỉ tự điền · **C5** Không lấy được vị trí · Desktop popup bản đồ | popup trong `/shop/checkout/` | Không | Google Maps JS + Places Autocomplete + Geocoding (đảo toạ độ → chữ) | Không cần BE (chỉ gửi chuỗi địa chỉ cuối cùng) | Cần API key, CSP, chính sách quyền riêng tư, xem L-10 |
| **C2** Nhập thiếu/sai (tóm tắt lỗi có link nhảy tới ô) · Desktop "Nhập thiếu / sai" | `/shop/checkout/` | Một phần (lỗi dưới từng ô, không có khối tóm tắt, không dời tiêu điểm) | — | BE chặn địa chỉ rỗng (`orders/services.py:183-184`) | Luật SĐT lệch, xem L-19 |
| **C3** Hết hàng lúc đặt E-06 (từng món: "đổi thành 1 kg" / "đã hết, sẽ bỏ") · Desktop popup | `/shop/checkout/` | Không (chỉ in `err.message`) | lỗi **có cấu trúc** từng dòng | **Chưa**: BE ném chuỗi `"Không đủ tồn khả dụng cho {code}: thiếu {x}kg"` (`inventory/batches/services.py:112-114`) | Xem L-03 |
| **C4** Lỗi kết nối khi đặt (Thử lại / Để sau) · Desktop popup | `/shop/checkout/` | Một phần (banner lỗi) | khoá chống trùng | **Chưa** | Xem L-11 |
| **D1** Thanh toán · **Happy 6** (đơn đã tạo, đồng hồ giữ hàng, tóm tắt món, nút "Thanh toán qua cổng SePay") | đề xuất **`/shop/orders/?code=`** trạng thái BOOKED (giữ được khi tải lại trang) | Có dạng state trong `CheckoutScreen` → `PaymentPanel.tsx` (mất khi F5) | `POST /api/shop/orders/<code>/checkout/` + tóm tắt món | checkout: có (`payments/shop_api.py:19-31`). Response tạo đơn **không có dòng món** (`orders/shop_api.py:58-65`) | Đề xuất BE trả `lines` + `lookup_token` khi tạo đơn (BE-4) |
| **D2** Huỷ / lỗi trên SePay → thanh toán lại (+ nút **"Huỷ đơn"**) · Desktop "Thanh toán chưa thành công" | `/shop/orders/?code=&result=cancel\|error` | Có nhánh cancel/error + "Thanh toán lại" (`OrderPaymentPanel.tsx:84-115`) | URL quay về; **khách tự huỷ đơn BOOKED** | URL quay về: có, cả 3 về `/shop/orders?code=…&result=…` (`payments/checkout.py:63-76`). Huỷ đơn: **chưa có endpoint/service** | Xem L-07 |
| **D3** Đang chờ xác nhận tiền (tự kiểm 5 giây) · Desktop | `/shop/orders/?code=&result=success` khi còn BOOKED | Có (poll 5 s `OrderLookup.tsx:12,68-80`, chữ "Đang chờ xác nhận…") | lookup | có | Dựng lại giao diện tiến trình |
| **D4** Hết giờ giữ hàng E-01 · Desktop popup | `/shop/orders/` khi `AUTO_CANCELLED` | Một phần (`OrderPaymentPanel.tsx:62-71`) | dòng món để "Đặt lại đơn này" | lookup trả `lines` có `item_code`, `name`, `qty` (`orders/shop_api.py:113-121`) | FE dựng lại giỏ từ `lines` |
| **D5** Chuyển thiếu tiền E-02 (cần / đã nhận / còn thiếu) | `/shop/orders/` | Không | trạng thái giao dịch lệch + số đã nhận | **Chưa** trả (model có `PaymentTransaction.MatchStatus.UNDERPAID`, `sales/models/payments.py:20`) | Xem L-15 |
| **D6** Rời trang thanh toán? · Desktop popup | `/shop/orders/` trạng thái BOOKED | Không | `booked_expires_at` | có ở lookup (`orders/shop_api.py:99-102`) | FE chặn link nội bộ (logo, quay lại) bằng hộp thoại; `beforeunload` chỉ là hộp mặc định trình duyệt |
| **E1** Thanh toán xong → trang đơn · **Happy 7** (banner thành công, dòng thời gian Đặt/Thanh toán/Chuẩn bị/Giao/Đã giao, món, **"Giao tới [Họ tên] · SĐT · địa chỉ"**, "Tra đơn khác") | `/shop/orders/?code=&result=success` | Một phần (badge trạng thái, bảng món, `ConfirmCallNotice`) | mốc giờ (đặt, trả tiền, giao), trạng thái giao, người nhận | mốc giờ: **chưa trả**. Giao: có `delivery.status/status_label` (`:84-97`). Người nhận: **không được trả** | **Critical L-01** |
| **E2** Đơn bị huỷ E-03/E-07 (lý do, "Cá Về sẽ gọi để xử lý số tiền") | `/shop/orders/` | Có khối huỷ + **chi tiết hoàn tiền** (`OrderLookup.tsx:160-205`) | lý do công khai, số tiền đã trả | `cancel_notice` có `reason_code` (chỉ `UNREACHABLE_AUTO`), `message`, `refund{amount,status_label,deadline,refunded_at}`, `contact` (`orders/customer_notices.py:44,69-103`) | Thiết kế ẩn hoàn tiền (L-08); thiếu nhãn lý do (L-14) |
| **E3** Đơn đã giao (mốc giao, "báo vấn đề trong [số] giờ", "Mua lại") | `/shop/orders/` | Một phần | `delivered_at`, số giờ báo lỗi | `DeliveryNote.completed_at` có trong model (`delivery/models.py:57`), **chưa trả**; số giờ: **chưa có** setting | BE-5, BE-7 |
| **E4** Giao không thành công E-08 | `/shop/orders/` | Một phần (in `delivery.status` thô `OrderLookup.tsx:233-236`) | `delivery.status=FAILED` | có (`delivery/models.py:23`) | FE map nhãn |
| **F1** Tra cứu đơn (**mã + SĐT**) · **F2** Không tìm thấy · Desktop "Tra cứu không thấy đơn" | `/shop/orders/` | Có, nhưng **mã + 4 số cuối** (`OrderLookup.tsx:121`, `app/shop/orders/page.tsx:19`) | tra bằng SĐT đầy đủ | **Chưa**: `GET …?phone_last4=` (`orders/shop_api.py:74-82`) | **High L-02** |

### 1.3 Trang phụ

| Màn | Route đích | Đã có? | API | BE | Khoảng trống |
|---|---|---|---|---|---|
| **F3** Chính sách (mẫu đổi trả: breadcrumb, mục lục, danh sách chính sách) | Thiết kế ghi `/trang/doi-tra` … **Đề xuất giữ `/trang/?slug=doi-tra`** | Có `app/trang/page.tsx` đọc `?slug=` | `GET /api/public/content/entries/<slug>/` | có | Path `/trang/doi-tra` không chạy được với static export nếu không thêm rewrite Firebase (L-13). Restyle + khối "Các chính sách" từ footer-links |
| **F4** Liên hệ (gọi, Zalo, email, địa chỉ, giờ làm việc) | đề xuất `/lien-he/` tĩnh đọc `site-info` (hoặc trang CMS `?slug=lien-he`) | Không | `site-info` | thiếu `zalo`; giờ làm việc dùng `confirmation_policy.working_hours` | Cần Duy chọn route |
| **F5** Cách mua hàng (5 bước + FAQ) | `/trang/?slug=cach-mua-hang` (trang CMS) hoặc trang tĩnh | Không | CMS | có | Nội dung có số liệu nghiệp vụ (1 kg, 0,5 kg, 30 phút) nên nên lấy từ setting nếu làm tĩnh |
| Góc bếp | `/bai-viet/` | Có (`app/bai-viet/page.tsx`) | có | có | Chỉ restyle + header/footer mới |
| 404 | `app/not-found.tsx` | Có (bản tối giản) | — | — | Restyle |

---

## 2. Chỗ thiết kế lệch nghiệp vụ hoặc code

### Critical

**L-01 · Trang đơn hiện tên, SĐT và địa chỉ giao đầy đủ qua API công khai.**
E1 (`Success.dc.html`), E3, E4, `DesktopSuccess.dc.html` có khối "Giao tới [Họ tên] · 09xx xxx [3 số cuối] · [Số nhà, đường],
[Phường/xã], [Tỉnh/thành]". Bất biến 9: "API công khai (`AllowAny`) **không bao giờ** trả tên, SĐT hay địa chỉ đầy đủ". `ShopOrderLookupView`
hiện đúng luật, không trả field nào trong số này (`orders/shop_api.py:107-125`). Xác minh bằng SĐT đầy đủ cũng không đổi luật,
vì ai biết mã đơn và SĐT của người khác (người nhà, shipper, ai cầm phiếu giao) đều đọc được địa chỉ.
→ **Cần Duy chốt**: (a) bỏ khối "Giao tới" (khuyến nghị), hoặc (b) chỉ trả bản đã che: tên viết tắt (`N*** A`), SĐT `mask_phone`
(`apps/common/pii.py:24`), địa chỉ chỉ phần sau dấu phẩy cuối (tỉnh/thành). Vì địa chỉ là một chuỗi tự do nên cách (b) không chắc che đủ.
Test bắt buộc: lookup trả JSON không chứa `customer.name`, `phone`, `delivery_address` gốc.

### High

**L-02 · Tra đơn bằng mã + SĐT đầy đủ, BE chỉ nhận 4 số cuối qua query string.**
BE: `GET /api/shop/orders/<code>/?phone_last4=` (`orders/shop_api.py:74-82`); FE: `lib/api.ts:158`, form "4 số cuối" `OrderLookup.tsx:121`.
Đổi sang SĐT đầy đủ thì xác minh mạnh hơn, nhưng **không được để SĐT trong URL** (log truy cập Cloud Run, lịch sử trình duyệt; bất biến 9 "FE không
lưu dữ liệu cá nhân vào URL"). Hiện `sessionStorage` giữ `phone_last4` để tự tra khi quay về từ SePay (`features/checkout/storage.ts`). Nếu chuyển
sang SĐT đầy đủ thì FE không được giữ số đầy đủ trong trình duyệt.
→ BE mới `POST /api/shop/orders/lookup/` body `{order_code, phone}` hoặc `{order_code, token}`; so khớp sau `normalize_phone` (Shop lưu SĐT đúng
như khách gõ, có thể `+84…`, `sales/customers/services.py:30-32`). Khi tạo đơn, BE trả `lookup_token` ký bằng `django.core.signing` (chỉ chứa mã đơn,
có hạn). FE giữ token trong `sessionStorage` thay cho 4 số cuối. Giữ throttle `ShopLookupIpThrottle`/`ShopLookupOrderThrottle`. Không log SĐT.

**L-03 · Popup C3 hiện "Bạn đặt 2 kg · còn 1 kg", trái chốt "không hiện số kg".**
BE còn ghép số kg thiếu và mã hàng vào chuỗi lỗi công khai (`inventory/batches/services.py:112-114`) và lộ **mã lô nội bộ** ở lỗi giữ chỗ
(`:128` `"Lô {b.batch_id} không còn đủ…"`). FE in nguyên `err.message` (`CheckoutScreen.tsx:162`).
→ BE trả lỗi có cấu trúc: `400 {"code":"OUT_OF_STOCK","detail":"Một số món vừa hết hàng.","lines":[{"item_code","stock_level":"out"|"short"}]}`,
không có số kg, không có mã lô. **Cần Duy chốt** C3 có được hiện "còn X kg" ở đúng lúc đặt không. Nếu không thì đổi nút thành "Bỏ món này"
hoặc "Giảm số kg" và để BE báo lại.

**L-04 · API công khai trả số kg tồn (`sellable_qty`), FE hiện "Còn X kg".**
`catalog/items/shop_api.py:26`; FE `CatalogGrid.tsx:49-50`, `item/page.tsx:57-58`, dòng phụ đề `app/shop/page.tsx:29` ("tồn kho hiển thị là số lượng còn khả dụng").
Chốt mới là chỉ hiện "Sắp hết" / "Hết". Nếu FE chỉ ẩn mà API vẫn trả số thì đối thủ vẫn đọc được tồn kho theo giờ.
→ BE thêm `stock_level: "in"|"low"|"out"` và **bỏ `sellable_qty`** khỏi Shop API sau khi FE chuyển xong. Ngưỡng "Sắp hết" đọc từ settings
(bất biến 7). `out` khi tồn < `min_qty` (khách không mua nổi 1 kg thì coi là hết). BR-BH-01 ("Tồn khả dụng **hiển thị** trên Shop = …") cần sửa câu chữ.
**Cần ghi quyết định + sửa BR-BH-01.**

**L-05 · Tối thiểu 1 kg, bước 0,5 kg: FE cho 0,1 kg, BE chỉ chặn ≤ 0, không có BR.**
FE: `AddToCartControl.tsx:30,37-38,43` (min/step 0,1); giỏ +/- 1 kg nên 1,5 → 0,5 kg vẫn qua (`CheckoutScreen.tsx:207`). BE: `orders/services.py:218-219`
chỉ `qty > 0`; ai gọi thẳng API vẫn đặt được 0,1 kg. Không có BR nào quy định mức tối thiểu.
→ BR mới (đề xuất **BR-BH-18**: SIMPLE đặt ≥ `SHOP_MIN_QTY_KG` = 1 và là bội của `SHOP_QTY_STEP_KG` = 0,5; BUNDLE là số nguyên ≥ 1), BE kiểm
trong `create_order`, catalog trả `min_qty`, `qty_step`.
Hệ quả nghiệp vụ cần Duy biết: **phần đuôi lô dưới 1 kg (hoặc lẻ 0,3 kg) không bán được online**, sẽ thành tồn chết rồi đi vào kiểm kê/huỷ.
→ 🔴 Q4. **Cần ghi quyết định + story.**

**L-06 · Combo tính theo combo, nhưng BR-DM-01 ghi "mọi mặt hàng bán theo Kg" và API trả `unit: "Kg"` cho combo.**
BE thực ra đã tính combo theo **số combo**: tồn combo = số combo ráp được (`catalog/items/services.py:24-35`, BR-DM-06), giữ chỗ = định mức × số combo
(`orders/services.py:238-239`). Nhưng `_item_public` luôn trả `"unit": "Kg"` (`catalog/items/shop_api.py:24`), FE hiện "/ kg" cho combo
(`CatalogGrid.tsx:41`, `item/page.tsx:54`), và BE vẫn nhận 1,5 combo.
→ Sửa BR-DM-01: "SIMPLE bán theo kg; BUNDLE bán theo combo, số nguyên". API trả `unit: "kg"|"combo"`. **Cần ghi quyết định.**

**L-07 · Nút "Huỷ đơn" ở D2 (khách tự huỷ đơn đang giữ chỗ): chưa có endpoint, service, BR.**
`orders/services.py` chỉ có `cancel_unpaid_expired` (job TTL, `:280`) và `cancel_paid_order` (ERP, cần quyền `cancel_paid_order`, `:333`).
→ Service mới `cancel_booked_by_customer(order, actor=None)`: chỉ nhận đơn BOOKED, `select_for_update`, nhả giữ chỗ, ghi `AuditLog` (actor = Hệ thống,
action riêng), idempotent. Endpoint `POST /api/shop/orders/<code>/cancel/` cần token hoặc SĐT (không cho huỷ đơn người khác chỉ bằng mã đơn). Tiền về
sau khi khách huỷ thì đi đường BR-TT-05 có sẵn. Cần quyết định trạng thái đích: `AUTO_CANCELLED` (sai nghĩa "quá TTL") hay `CANCELLED` (đang dùng cho
huỷ đơn đã trả tiền, có hoá đơn và CreditNote) hay trạng thái mới. **Cần story + BR mới (BR-BH-19).** Nếu bỏ nút này thì không cần BE.

### Medium

**L-08 · Thiết kế ẩn hoàn tiền ("Cá Về sẽ gọi"), còn BE và FE hiện đang hiện chi tiết hoàn tiền.**
`build_cancel_notice` trả `refund{amount,status_label,deadline,refunded_at}`. Câu tự huỷ còn nói "sẽ được hoàn trong vòng {N} ngày"
(`orders/customer_notices.py:17-22,69-81`). FE in đủ (`OrderLookup.tsx:178-195`). Câu "chưa có luồng hoàn tiền" **không đúng với hệ thống**:
ERP đã có `Refund` + `create_refund`/`confirm_refund` (decisions 2026-09-10). Đúng ra là chưa có hoàn tiền **tự động**, và Shop không hiện tiến độ hoàn.
→ FE chỉ hiện câu "Cá Về sẽ gọi để xử lý số tiền X đ" + hotline. BE nên đổi `message` cho khớp (câu chữ đang đánh dấu "CHỜ legal-vn"). Chuyện này
lật nội dung đã nghiệm thu ở CS-10 (`customer_notices.py`). **Cần ghi quyết định** và nhờ legal-vn duyệt câu, vì NĐ 356 và Luật BVQLNTD yêu cầu báo cho
khách cách xử lý tiền.

**L-09 · "Phí giao: báo khi xác nhận đơn" (giỏ, checkout, thanh toán, landing).**
Khớp decisions 2026-09-09 (phí giao nằm ngoài hệ thống, BR-BH-10). Nhưng khách đã trả 100% qua VietQR rồi mới biết phí giao, và hệ thống không có cách thu
khoản này. Rủi ro pháp lý: website TMĐT phải công bố đủ chi phí trước khi khách đặt. → 🔴 Q6 cho Duy, **legal-vn** duyệt câu.

**L-10 · Google Maps chọn địa chỉ.**
- Dữ liệu: ô tìm gửi từng chữ địa chỉ, nút "Vị trí của tôi" gửi toạ độ, và trình duyệt gửi IP cho Google (máy chủ ở nước ngoài). Duy đã đồng ý, nhưng bất biến 9
  còn đòi **chính sách quyền riêng tư nêu rõ** và checklist go-live mục 6b. → **Cần ghi quyết định** + legal-vn sửa chính sách quyền riêng tư trước go-live.
- Chỉ nạp script Maps khi khách bấm "Bản đồ" (`next/dynamic` / tạo thẻ script lúc mở popup), không nạp ở mọi trang. **Không lưu toạ độ** (thêm field cá nhân
  mới cần lý do + Duy duyệt). Chỉ chuỗi địa chỉ cuối cùng vào `delivery_address`.
- Kỹ thuật: biến `NEXT_PUBLIC_GOOGLE_MAPS_KEY` (truyền lúc build như các `NEXT_PUBLIC_*` khác); khoá giới hạn HTTP referrer (`cangca-loc.web.app`,
  domain staging, domain thật) + giới hạn API (Maps JavaScript, Places, Geocoding); bật billing và hạn mức; dùng session token của Places để giảm phí;
  `componentRestrictions: {country: "vn"}`, `language: "vi"`; giữ chữ "Google" theo điều khoản Places.
- CSP: `frontend/firebase.json` **chưa có** header CSP nên hôm nay không chặn. Nếu thêm CSP (nên làm trước go-live) phải mở `script-src` / `connect-src` /
  `img-src` cho `maps.googleapis.com`, `maps.gstatic.com`, `*.googleapis.com`, cùng `NEXT_PUBLIC_API_BASE` và ảnh CMS.

**L-11 · C4 "Thử lại" có thể tạo đơn trùng.** Nếu request tạo đơn tới BE nhưng mất phản hồi, bấm "Thử lại" sẽ tạo đơn BOOKED thứ hai và **giữ chỗ gấp đôi 30
phút**, làm hàng hiện "hết" oan. → Body thêm `client_request_id` (UUID do FE sinh mỗi lần mở form). BE lưu field unique nullable trên `SalesOrder` (migration),
trùng thì trả lại đơn cũ. Cache không dùng được vì Cloud Run nhiều instance.

**L-12 · Mã đơn "CV-…" vs BE `SO<yymmdd>-XXXXXX`.** `sales/utils.py:33-38`, gọi ở `orders/services.py:201`; placeholder FE `DH-260913-1234`
(`OrderLookup.tsx:117`). Đổi tiền tố chỉ tác động đơn mới; SePay dùng mã đơn làm `order_invoice_number` nên vẫn chạy. → 🔴 Q5. Nếu giữ `SO` thì sửa chữ
trong thiết kế ("bắt đầu bằng CV-").

**L-13 · Route trong đặc tả header/footer chưa có hoặc không chạy với static export.**
- `/` đang là Landing → thành Trang chủ Shop; Landing sang `/gioi-thieu/` (mới).
- `/shop/cart` chưa có (giỏ nằm trong `/shop/checkout`).
- `/trang/doi-tra`, `/trang/lien-he`, `/trang/cach-mua-hang` là path; code dùng `/trang/?slug=` (`app/trang/page.tsx`). Route động cần `generateStaticParams`
  (slug do CMS tạo lúc chạy nên không biết trước). Nếu muốn path đẹp thì phải thêm rewrite `"/trang/**" → "/trang/index.html"` trong `firebase.json` và đọc
  `pathname` ở client. Cách này cần thử trước với router của Next 14. **Khuyến nghị giữ `?slug=`** (CLAUDE.md cũng ghi giữ URL công khai `/trang/`).
- `?nhom=ca` đặt tên tham số tiếng Việt, trái luật đặt tên P8b (chỉ `chuyen-muc` được miễn) → dùng `?group=ca`.
- 21 chỗ trong `frontend/e2e/*.py` trỏ route/landing cũ, sẽ phải sửa theo.

**L-14 · E2 hiện lý do huỷ cụ thể ("Lô hàng không đạt khi soạn").** BE công khai chỉ có `reason_code` cho `UNREACHABLE_AUTO`
(`customer_notices.py:44`). Mã lý do huỷ nằm ở `CreditNote.reason_code` (`sales/models/credit_notes.py:35`; danh sách `CANCEL_REASON_LABELS`,
`orders/services.py:311-317`). → BE trả `cancel_notice.reason_label` lấy từ **bảng nhãn công khai cố định** theo mã. `OTHER` thì trả câu chung.
**Không bao giờ** trả ghi chú tự do (decisions 06/10 chiều: ghi chú có thể chứa SĐT).

**L-15 · D5 thiếu tiền.** Lookup không trả trạng thái giao dịch lệch. Thực tế V1 gần như không xảy ra: cổng SePay cố định số tiền, còn webhook ngân hàng thì tắt
(decisions 2026-09-26). → Ưu tiên thấp: BE trả `payment_issue: {"kind":"UNDERPAID","received_amount","missing_amount"} | null` từ `PaymentTransaction`
(`sales/models/payments.py:20,50`). Không trả `raw_payload` (có tên người chuyển).

**L-16 · Dòng thời gian E1/E3/E4 cần mốc giờ.** Lookup chưa trả `placed_at` (`SalesOrder.created_at`), `paid_at` (giao dịch MATCHED), `delivered_at`
(`DeliveryNote.completed_at`). Thêm vào response, không có dữ liệu cá nhân.

**L-17 · Thiết kế thiếu trạng thái đã có trong code.** "Shop tạm chưa nhận đơn" khi chưa có chính sách bảo mật (GL-03-AC5, `CheckoutScreen.tsx:83-97`);
lỗi 409 `POLICY_CHANGED` buộc đồng ý lại (`:141-155`); khối giờ gọi xác nhận `ConfirmCallNotice`/`ConfirmationPolicyNotice` (GL-04). FE phải giữ các trạng thái
này trong giao diện mới.

### Low

- **L-18** Badge giỏ là số món, code đang cộng kg (`ShopHeader.tsx:7,19`, `CartContext.tsx:92`). Thêm `lineCount`.
- **L-19** SĐT: thiết kế báo "10 chữ số, bắt đầu bằng 0". FE nhận `^(0|\+84)\d{9,10}$` (`CheckoutScreen.tsx:28`), BE ERP nhận `0\d{9,10}`
  (`sales/customers/services.py:30-31`). Chốt một luật, đặt ở cả FE và BE.
- **L-20** `ItemGroup` không có slug, cây nhóm con (`parent`) không lộ ra Shop. Dropdown "Cá thu, Cá ngừ…" trên desktop đòi dữ liệu nhóm hai cấp.
- **L-21** Token màu Shop lệch DESIGN.md: `globals.css:1-22` dùng primary `#0a6e8c` + accent cam `#e8912c`. Thiết kế mới dùng `#1F66D1`, `ink`, `border`… như ERP.
  Font: Shop dùng font hệ thống, DESIGN.md quy định Inter. Đề xuất `next/font/google` (tự host lúc build, không gọi Google lúc chạy) thay `<link>`.
- **L-22** Thư viện ảnh "1/3" + hàng ảnh nhỏ: BE chỉ 1 ảnh/mặt hàng (`catalog/models/images.py:24` OneToOne, có lý do ở docstring). V1: ẩn bộ đếm khi chỉ có 1 ảnh.
- **L-23** Trường thông tin sản phẩm (ghi chú ngắn trên thẻ "Cắt khúc dày 2–3 cm", Quy cách, Bảo quản, Nguồn hàng, cách rã đông): chưa có field; `description`
  có nhưng API không trả. Thêm field là đổi schema, cần lý do trong hồ sơ tính năng (bất biến 8) và màn ERP để nhập.
- **L-24** Ô "Lô mới về (4 món)" (DesktopHome) và banner "Lô mới vừa nhập kho": cần quy tắc "mới" (vd có lô mở bán trong N ngày). Không lộ ngày nhập nhưng sát
  chốt "không hiện ngày nhập lô". → 🔴 Q8, khuyến nghị V1 bỏ ô này, banner để chữ tĩnh.
- **L-25** Chip "Tìm nhiều — Lộc chọn trong ERP": chưa có model hay màn ERP. V1 đề xuất lấy 4 nhóm đầu hoặc biến cấu hình.
- **L-26** Ưu đãi PricingRule (BR-DM-08) có thể giảm tổng đơn, nhưng giỏ/checkout trong thiết kế không có dòng giảm. Tổng giỏ FE (`CartContext.tsx:93-96`) có thể
  khác `total_amount` BE. Trang thanh toán phải lấy tổng từ BE (đang đúng). Nếu muốn hiện ưu đãi trước khi đặt thì cần BE-9.
- **L-27** Chú thích FE đã cũ: `lib/types.ts:68,99,137,149` và `features/checkout/README.md:41-42` ghi lookup "CHƯA trả" `name` và `booked_expires_at`,
  nhưng BE đã trả (`orders/shop_api.py:99-102,116`). Dọn khi viết lại.
- **L-28** C3/C4 vẽ địa chỉ dạng "[Tỉnh/thành] [Phường/xã] [Số nhà]", còn sót từ form cũ nhiều ô. Đúng là một ô.
- **L-29** Bỏ hoá đơn điện tử: Shop chưa từng có HĐĐT nên không đụng code. Nghĩa vụ HĐĐT theo hình thức pháp lý của Lộc vẫn mở
  (`doc/ops/go-live-phap-ly.md` mục 7) → ghi quyết định là "Shop không hiển thị/không xuất", legal-vn xác nhận.
- **L-30** Nút "Liên hệ chúng tôi" khi hết hàng là `tel:`. Trên máy tính phải hiện số để khách đọc (đặc tả H1 desktop đã ghi).

---

## 3. Chốt mới của Duy so với `decisions.md` / BR: cần ghi quyết định hoặc story

| Chốt | Trái / chạm vào | Việc cần |
|---|---|---|
| Giá theo kg, tối thiểu 1 kg, bước 0,5 kg | Chưa có BR; BE nhận mọi qty > 0 | **Ghi quyết định + BR mới BR-BH-18 + story BE/FE.** Kèm câu trả lời về đuôi lô < 1 kg (Q4) |
| Combo tính theo combo | **BR-DM-01** ("mọi mặt hàng bán theo Kg") | **Ghi quyết định, sửa BR-DM-01**; story BE (unit, qty nguyên) |
| Hết hàng → "Liên hệ chúng tôi"; không hiện ngày nhập lô | Không trái. Code chưa hiện ngày nhập | FE. Ô "Lô mới về" xem Q8 |
| Chỉ hiện "Sắp hết"/"Hết", không hiện số kg | **BR-BH-01** (chữ "hiển thị"); Shop API đang trả `sellable_qty` | **Ghi quyết định, sửa câu BR-BH-01; story BE** `stock_level` + bỏ `sellable_qty` |
| Bỏ hoá đơn điện tử | Không trái decisions; chạm go-live mục 7 | Ghi quyết định + legal-vn |
| Chưa có luồng hoàn tiền ("Cá Về sẽ gọi") | decisions 2026-09-10 (Refund có trong hệ thống); nội dung CS-10 `cancel_notice` | **Ghi quyết định**: Shop không hiện tiến độ hoàn, ERP giữ nguyên Refund. Story sửa câu thông báo (legal-vn) |
| Địa chỉ một ô + Google Maps | Bất biến 9 (bên thứ ba, nước ngoài; chính sách phải nêu) | **Ghi quyết định** (Duy đồng ý gửi Google) + legal-vn cập nhật chính sách quyền riêng tư. Story FE |
| Thanh toán xong vào thẳng trang tra cứu đơn | Khớp BR-TT-12 và `_return_urls` (`payments/checkout.py:63-76`) | Không cần BE. FE |
| Logo Duy upload sau | — | FE chừa chỗ |
| Bố cục kiểu Long Châu | `caveve-ui` / DESIGN.md (Linear/Notion, một màu nhấn). Thiết kế vẫn dùng token DESIGN.md nên không vỡ | Ghi một dòng quyết định "Shop: bố cục bán lẻ kiểu Long Châu, token giữ DESIGN.md" để reviewer UI không chấm sai |
| (phát sinh) Tra đơn bằng SĐT đầy đủ | Bất biến 9 có ví dụ "mã đơn + SĐT"; code dùng 4 số cuối | Story BE+FE (L-02) |
| (phát sinh) Khách tự huỷ đơn đang giữ chỗ | Không có BR | **Story + BR mới BR-BH-19** (L-07) |
| (phát sinh) Khối "Giao tới" trên trang đơn | **Bất biến 9**, Critical | **Duy chốt bỏ hoặc che** (Q1) |

---

## 4. Việc BE cần làm để thiết kế chạy được

Không có việc nào đụng giá vốn: serializer Shop là dict tường minh (`_item_public`), không dùng serializer back-office. Mỗi việc có test chống rò dữ liệu cá nhân và
test lỗi nghiệp vụ.

| Mã | Việc | Contract đề xuất | Migration | Mức |
|---|---|---|---|---|
| BE-1 | Catalog công khai: `stock_level`, `unit`, `min_qty`, `qty_step`, nhóm có slug; **bỏ `sellable_qty`** khi FE chuyển xong | Thẻ: `{item_code, name, item_type, unit:"kg"\|"combo", price:"278000", stock_level:"in"\|"low"\|"out", min_qty:"1", qty_step:"0.5", group:{slug,name,parent_slug}, short_note, image}`. Settings: `SHOP_MIN_QTY_KG`, `SHOP_QTY_STEP_KG`, `SHOP_LOW_STOCK_KG`, `SHOP_LOW_STOCK_COMBO` | `ItemGroup.slug` (unique) + data migration slugify tên hiện có | High |
| BE-2 | Chi tiết mặt hàng: `description`, `spec`, `storage`, `origin`, `short_note` | thêm vào `GET /api/shop/catalog/<code>/` | `Item` thêm 4 field `blank=True` (`description` đã có) | Medium |
| BE-3 | Kiểm số lượng trong `create_order` (BR-BH-18, combo nguyên) + lỗi hết hàng có cấu trúc, không lộ kg/mã lô | `400 {"code":"INVALID_QTY"\|"OUT_OF_STOCK", "detail", "lines":[{item_code, stock_level}]}` | — | High |
| BE-4 | Response tạo đơn: thêm `lines`, `lookup_token`; nhận `client_request_id` chống trùng | `201 {order_code,total_amount,booked_expires_at,lines:[{item_code,name,unit,qty,amount}],lookup_token}` | `SalesOrder.client_request_id` (UUID, unique, null) | Medium |
| BE-5 | Tra đơn mới bằng SĐT đầy đủ hoặc token, qua POST; thêm mốc giờ, nhãn lý do huỷ, `unit` từng dòng, `payment_issue`; (tuỳ Q1) người nhận đã che | `POST /api/shop/orders/lookup/` `{order_code, phone}` \| `{order_code, token}` → như response hiện tại + `placed_at, paid_at, delivered_at, cancel_notice.reason_label, payment_issue`. Giữ GET `phone_last4` tới khi FE chuyển xong rồi gỡ | — | High |
| BE-6 | Khách huỷ đơn BOOKED | `POST /api/shop/orders/<code>/cancel/` `{token}\|{phone}` → `200 {order_code,status}`; service `cancel_booked_by_customer` idempotent, nhả giữ chỗ, AuditLog | Tuỳ quyết định trạng thái (có thể cần choice mới) | High nếu giữ nút |
| BE-7 | `site-info` thêm `zalo`, `return_report_hours` (E3 "[số] giờ"), có thể thêm `search_chips` | `seller.zalo`, `policies.return_report_hours`, `search_chips:[…]` từ settings/env | — | Low |
| BE-8 | Tiền tố mã đơn `CV` (nếu Duy chốt) | `gen_code("CV", SalesOrder)` | — | Low |
| BE-9 | (Tuỳ chọn) báo giá giỏ: giá hiện hành, mức tồn, ưu đãi, tổng; không giữ chỗ | `POST /api/shop/cart/quote/` `{items}` → `{lines:[{item_code,price,stock_level,amount}],discount_total,total}`. Dùng lại bước 1–2 của `create_order` | — | Low (B3 làm được bằng FE) |
| BE-11 | **Mã giảm giá (mới, chốt 07/10)**: model `Voucher` (mã, kiểu AMOUNT/PERCENT, giá trị, trần giảm, đơn tối thiểu, hiệu lực từ–đến, tổng lượt, đang bật), ghi nhận dùng mã trên đơn (đơn ↔ mã ↔ số tiền giảm, đóng băng lúc tạo đơn như BR-BH-08), API kiểm mã công khai có throttle, ERP để Lộc tạo/tắt mã, AuditLog. Quy tắc với PricingRule: không cộng dồn, lấy lợi hơn | `POST /api/shop/vouchers/check/` `{code, items}` → `{valid, discount_amount, reason_code: INVALID\|EXPIRED\|MIN_ORDER\|USED_UP\|BETTER_PROMO, min_amount?}`; `POST /api/shop/orders/` nhận `voucher_code`; lỗi `VOUCHER_INVALID` khi đặt | `Voucher`, `SalesOrder.voucher` (+ số tiền giảm) | High (lật quyết định cũ, cần BR mới) |
| BE-10 | Dọn câu lỗi giữ chỗ lộ mã lô (`inventory/batches/services.py:128`) khi trả về Shop | gộp vào BE-3 | — | Low |

Gợi ý tìm kiếm (A9) và "giá cũ" (B3) **không cần BE**. Catalog chỉ vài chục món, FE tải một lần rồi lọc bỏ dấu tại chỗ. Giá cũ nằm sẵn trong giỏ `localStorage`.
ERP cần thêm màn để Lộc nhập field mới (BE-2), slug nhóm (BE-1) và chip tìm kiếm (BE-7). Đây là việc `erp-console/`, xếp ở lô riêng.

---

## 5. Đề xuất chia lô (theo quy trình 02c của CLAUDE.md)

Điều kiện đầu vào: Duy trả lời 🔴 Q1–Q8, ghi `decisions.md` + BR (điều phối viên làm, không phải dev), rồi chạy luồng ĐẦY ĐỦ: BA → PO (`02-stories.md`) →
Tech Lead (`02b-tech-design.md` chốt contract mục 4). Lệnh kiểm chứng mỗi lô: `cd frontend && npx tsc --noEmit && npm run build && node scripts/check-no-mock.mjs`;
BE: `cd backend && .venv/bin/python manage.py test apps.catalog apps.sales && .venv/bin/python manage.py makemigrations --check --dry-run`; `python3 scripts/check_naming.py`.

| ☐ | Lô | Nội dung (màn) | BE / FE | Được sửa | Không được đụng |
|---|---|---|---|---|---|
| ☐ | 0 | Ghi quyết định + BR (BR-DM-01, BR-BH-01, BR-BH-18/19); legal-vn: chính sách quyền riêng tư (Google), câu phí giao, câu huỷ/hoàn | Điều phối + legal-vn | `doc/decisions.md`, `doc/business-process-spec.md`, `doc/ops/` | code |
| ☐ | 1 | Khung chung: token DESIGN.md vào `globals.css`, Inter qua `next/font`, `CartProvider` lên root, header H1–H4, BottomNav, footer F1/F2 (gộp `SiteLegalFooter`), `/gioi-thieu/` (chuyển Landing), `/` trang chủ A1 dựng tạm bằng catalog hiện có, 404 | FE | `frontend/app/layout.tsx`, `app/page.tsx`, **mới** `app/gioi-thieu/page.tsx`, `app/shop/layout.tsx`, `app/globals.css`, `app/not-found.tsx`, `components/ShopHeader.tsx`, `components/ShopFooter.tsx`, **mới** `components/BottomNav.tsx`, `features/site/components/SiteLegalFooter.tsx`, `frontend/e2e/*` liên quan | `lib/api.ts`, `lib/types.ts`, `features/checkout/*`, `backend/` |
| ☐ | 2 | BE-1, BE-3, BE-10 ∥ FE danh mục A2/A4–A9, chi tiết A3/A7/A10, giỏ B1–B4 (`/shop/cart/`), `AddToCartControl` theo `min_qty`/`qty_step`/`unit`, badge số món. FE mock theo contract BE-1 | BE ∥ FE | BE: `backend/apps/catalog/models/items.py`, migration mới `catalog`, `catalog/items/shop_api.py`, `catalog/items/services.py`, `sales/orders/services.py` (kiểm qty), `sales/orders/shop_api.py` (lỗi), `inventory/batches/services.py` (câu lỗi), `config/settings.py`, tests. FE: `app/shop/page.tsx`, `app/shop/item/page.tsx`, **mới** `app/shop/cart/page.tsx`, `components/CatalogGrid.tsx`, `components/AddToCartControl.tsx`, `components/CartContext.tsx`, `lib/types.ts`, `lib/mock.ts`, `lib/api.ts` (chỉ catalog) | migration cũ, `payments/*`, `features/checkout/*` |
| ☐ | 3 | BE-4, BE-5, (BE-6 nếu giữ nút Huỷ) ∥ FE checkout C1–C5 (`/shop/checkout/` bỏ phần giỏ, Maps lazy-load, tóm tắt lỗi, popup hết hàng, chống bấm đúp + `client_request_id`) | BE ∥ FE | BE: `sales/models/orders.py` (+migration `client_request_id`), `sales/orders/shop_api.py`, `sales/orders/services.py`, `sales/orders/customer_notices.py`, `config/api_urls.py`, `apps/common/throttling.py`, tests. FE: `features/checkout/components/CheckoutScreen.tsx`, **mới** `features/checkout/components/AddressMapPicker.tsx`, `features/checkout/storage.ts` (token), `lib/api.ts`, `lib/types.ts`, `lib/mock.ts` | `payments/checkout.py` (URL quay về giữ nguyên), `adapter/` |
| ☐ | 4 | FE trang đơn = trang tra cứu: D1–D6, E1–E4, F1–F2 trên `/shop/orders/` (header H2/F2 khi BOOKED), dựng lại giỏ từ `lines`, hộp "Rời trang?" | FE | `app/shop/orders/page.tsx`, `app/shop/orders/OrderLookup.tsx`, `features/checkout/components/OrderPaymentPanel.tsx`, `PaymentPanel.tsx` (gộp/bỏ), `features/checkout/README.md` | `backend/` (contract đã chốt ở lô 3) |
| ☐ | 5 | Trang phụ: chính sách `/trang/?slug=` (F3), liên hệ (F4), cách mua (F5), `/bai-viet/` restyle; BE-7 `site-info` | BE nhỏ ∥ FE | FE: `app/trang/*`, `app/bai-viet/*`, **mới** `app/lien-he/page.tsx` (nếu Q7 chọn tĩnh), `features/site/*`, `features/content/*`. BE: `apps/common/site_info*` hoặc nơi đang dựng `site-info`, `config/settings.py` | `content/models` |
| ☐ | 6 | ERP: màn sửa field mặt hàng mới, slug nhóm, (chip tìm kiếm) | BE nhỏ ∥ FE ERP | `erp-console/features/items/*` (hoặc module mặt hàng hiện có), API ERP mặt hàng tương ứng | Shop |
| ☐ | 7 | QA E2E toàn luồng 360 px + 1280 px, gỡ GET `phone_last4` + `sellable_qty` khỏi Shop API (sau khi FE mới lên staging) | QA + BE | `frontend/e2e/`, `sales/orders/shop_api.py`, `catalog/items/shop_api.py` | — |

Thứ tự: 0 → (1 ∥ BE của 2) → FE của 2 → 3 → 4 → 5 → 6 → 7. Lô 1 chạy song song với BE lô 2 được, vì lô 1 không đổi contract.
Điểm dừng hỏi Duy: contract lệch 02b; bất kỳ field cá nhân mới (vd toạ độ); đổi trạng thái đơn (BE-6).

---

## 6. Câu hỏi 🔴 cho Duy

1. **Q1 (Critical)** Khối "Giao tới [tên · SĐT · địa chỉ]" trên trang đơn: bỏ hẳn (khuyến nghị), hay hiện bản đã che (tên viết tắt, `09xx xxx 123`, chỉ tỉnh/thành)?
2. **Q2** Tra đơn bằng SĐT đầy đủ (khuyến nghị, kèm token phiên) thay cho 4 số cuối: đồng ý chứ?
3. **Q3** Popup C3 có được nói "còn 1 kg" lúc đặt không, hay chỉ nói "món này không đủ hàng"?
4. **Q4** Đuôi lô dưới 1 kg (hoặc số lẻ không chia hết 0,5) thì sao: cho khách mua "phần còn lại", để Lộc bán ngoài, hay chấp nhận thành tồn chết?
5. **Q5** Đổi tiền tố mã đơn sang `CV`? (đơn cũ giữ `SO…`)
6. **Q6** Phí giao "báo khi xác nhận": khách trả phí bằng cách nào (tiền mặt khi nhận)? legal-vn cần câu công bố trước khi đặt.
7. **Q7** Liên hệ / cách mua: trang tĩnh (`/lien-he/`, `/cach-mua-hang/`) hay trang CMS (`/trang/?slug=`)? Chính sách giữ `/trang/?slug=` thay path `/trang/doi-tra`?
8. **Q8** Ô "Lô mới về" và banner "Lô mới vừa nhập kho": bỏ, hay định nghĩa "mới" là lô mở bán trong N ngày?
9. **Q9** Nút "Huỷ đơn" ở D2: giữ (cần BE-6 + BR mới) hay bỏ (đơn tự huỷ sau 30 phút)?

---

## 7. Kết luận

Thiết kế **đủ để FE dựng giao diện**: phủ đủ luồng, có ca lỗi, đặc tả từng link và cả hai khổ màn. Lô 1 (khung, token, header/footer, route mới) làm ngay được.
Nhưng thiết kế **chưa đủ để code trọn luồng mua**, vì ba lý do. (1) Có một chỗ Critical về dữ liệu cá nhân: khối "Giao tới" trên trang đơn công khai trái bất biến 9,
phải bỏ hoặc che. (2) Bốn chốt mới của Duy chạm BR đã ghi (BR-DM-01 combo, BR-BH-01 hiện tồn, mức tối thiểu 1 kg/bước 0,5 chưa có BR, ẩn hoàn tiền trái nội dung
CS-10) và hai việc phát sinh chưa có BR (khách tự huỷ đơn, tra bằng SĐT đầy đủ). Các mục này phải ghi `decisions.md` và viết story trước khi dev. (3) BE thiếu
contract cho `stock_level`/`unit`/`min_qty`, lỗi hết hàng có cấu trúc, tra đơn qua POST + token, mốc giờ đơn, chống tạo đơn trùng, và các field thông tin sản phẩm
(cần migration và màn ERP). Ngoài ra cần legal-vn cho chính sách quyền riêng tư (Google Maps), câu phí giao và câu báo huỷ/hoàn; cần API key Google Maps giới hạn
referrer. Trả lời 9 câu 🔴 rồi chạy BA → PO → Tech Lead (02b) là vào lô 2 được.
