# 04 · Báo cáo QA (Gemini CLI — Shop UI)

> Nhánh: `gemini/shop-ui` · Kiểm thử thực tế trên trình duyệt Chromium (Playwright) ở 360 px và 1280 px với BE Django + SQLite tạm. Dữ liệu cá nhân 100% giả.

## GUI-01 — Mã giảm giá khi kiểm bị lỗi mạng

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Chặn mạng `/api/shop/vouchers/check/` ngay từ giỏ (chưa áp được mã), đặt đơn: số tiền ở tóm tắt bằng số tiền trang thanh toán (360 + 1280) | `page.route("**/api/shop/vouchers/check/", abort)` → nhập mã ở giỏ báo `"Chưa kiểm được mã"` → sang `/shop/checkout/` tóm tắt `165.000đ` → đặt đơn → trang thanh toán `165.000đ` | **PASS** (360 px & 1280 px) | `shots/flow/05-cart-360.png`, `shots/flow/09-payment-360.png` |
| Đã áp mã ở giỏ, sang `/shop/checkout/` bị chặn mạng `/api/shop/vouchers/check/`: hiện dòng nhỏ `"Mã X · sẽ kiểm khi đặt"` ở khối tóm tắt (360 + 1280) | Áp mã `FLOW…` ở giỏ (`−16.500đ`) → bật `route.abort` cho `/api/shop/vouchers/check/` → vào `/shop/checkout/` đợi hết debounce kiểm mã → kiểm DOM + nhìn ảnh chụp | **PASS** (360 px & 1280 px) | `shots/gui-01/35-checkout-voucher-pending-360.png`, `shots/gui-01/35-checkout-voucher-pending-1280.png` |
| Đặt đơn khi đang ở trạng thái `"Mã X · sẽ kiểm khi đặt"`: mã vẫn gửi lên máy chủ, trang thanh toán hiện đúng số tiền giảm thật (ngoài đường thuận) | Điền form dữ liệu giả → bấm `"Đặt hàng"` → mở trang thanh toán `/shop/orders/?code=…` → kiểm dòng giảm giá `−16.500đ` và cần thanh toán `148.500đ` | **PASS** (360 px & 1280 px) | `shots/gui-01/35b-payment-voucher-applied-360.png`, `shots/gui-01/35b-payment-voucher-applied-1280.png` |
| Hồi quy bất biến (không rò giá vốn, không rò dữ liệu cá nhân, không mã hex rời, không cuộn ngang, axe-core 360) | Chạy `run_shop_e2e.py --suite general_rules --suite full_flow` + `check_naming.py` | **PASS** (`general_rules`: 132/132, `full_flow`: 109/109) | — |

## GUI-02 — Hộp "mã hết hiệu lực" (B8) gạch rồi in lại cùng một số

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Ca có giảm (đã lấy được `quote` từ máy chủ trước khi mã bị tắt): vẫn gạch giá giảm cũ rồi in tổng chưa giảm đúng như màn `B8*` | Áp mã ở giỏ → sang `/shop/checkout/` đợi hiện `Mã giảm giá (…) −16.500đ` → tắt mã qua API → bấm `"Đặt hàng"` → kiểm `<del>` = `148.500đ`, `<strong>` = `165.000đ` | **PASS** (360 px & 1280 px) | `shots/gui-02/36-b8-with-quote-360.png`, `shots/gui-02/36-b8-with-quote-1280.png` |
| Ca chưa từng kiểm được `quote` (ngoài đường thuận: chặn mạng `/api/shop/vouchers/check/` ở đặt hàng rồi mã bị tắt): ẩn `<del>`, chỉ hiện tổng `165.000đ` | Áp mã ở giỏ → chặn `/api/shop/vouchers/check/` → vào `/shop/checkout/` → tắt mã qua API → bấm `"Đặt hàng"` → kiểm `dialog del` count = `0`, chỉ còn `<strong>165.000đ</strong>` | **PASS** (360 px & 1280 px) | `shots/gui-02/36b-b8-without-quote-360.png`, `shots/gui-02/36b-b8-without-quote-1280.png` |
| Bấm `"Đặt hàng không dùng mã"` từ hộp B8 không `quote` | Click nút chính trong dialog → đơn tạo thành công với giá gốc `165.000đ` | **PASS** (360 px & 1280 px) | — |
| Hồi quy bất biến | `run_shop_e2e.py --suite general_rules --suite full_flow` | **PASS** (`general_rules`: 132/132, `full_flow`: 115/115) | — |


## GUI-03 — Dọn state chết ở giỏ và sửa thụt lề `hotline`

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| `tsc`, build tĩnh (`USE_MOCK=0`), toàn bộ `test-*.mjs` xanh | Chạy đủ chuỗi lệnh mục 4 `GEMINI.md` + `check_naming.py` | **PASS** (9/9 bộ test đơn vị xanh, 0 lỗi TS) | — |
| Giỏ có món hết hàng & món đổi giá (ngoài đường thuận — màn B3 / DE11): vẫn hiện cảnh báo đỏ `"Bỏ món đã hết để đặt hàng."` và chặn sang bước nhận hàng | Dựng giỏ có `TOM-SU-1` hết hàng + `CA-THU` đổi giá trên trình duyệt 360 px và 1280 px, kiểm ảnh chụp thực tế | **PASS** (360 px & 1280 px) | `shots/gui-03/b3-cart-blocked-360.png`, `shots/gui-03/b3-cart-blocked-1280.png` |
| Hồi quy bất biến | `run_shop_e2e.py --suite general_rules --suite full_flow --suite design_screens` | **PASS** (`general_rules`: 132/132, `full_flow`: 115/115) | — |


## GUI-04 — Ca E2E giỏ hỏng trong `localStorage`

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Ghi giỏ có giá `"abc"` và `null` vào `localStorage`, mở `/shop/cart/` (ngoài đường thuận): không `NaN`/`undefined`/`Infinity`, không lỗi console, tự đối chiếu lại giá catalog | Kịch bản Playwright `shop_general_rules.py` ở 360 px và 1280 px + xem ảnh chụp | **PASS** (360 px & 1280 px) | `shots/gui-04/corrupt-cart-360.png`, `shots/gui-04/corrupt-cart-1280.png` |
| Ghi giỏ có giá `"abc"` và `null` vào `localStorage`, mở thẳng `/shop/checkout/` (ngoài đường thuận): không `NaN`/`undefined`/`Infinity`, không lỗi console | Kịch bản Playwright `shop_general_rules.py` ở 360 px và 1280 px + xem ảnh chụp | **PASS** (360 px & 1280 px) | `shots/gui-04/corrupt-checkout-360.png`, `shots/gui-04/corrupt-checkout-1280.png` |
| Thử làm hỏng tạm `CartContext.tsx` (không commit) để thấy ca đỏ | Đổi tạm `parseStoredCart` trả `String(price)` → build → chạy `general_rules` → xác nhận `4 FAIL` → `git checkout -- frontend/components/CartContext.tsx` | **PASS** (Red → Green xác thực) | — |
| Hồi quy bất biến | `run_shop_e2e.py --suite general_rules --suite full_flow` | **PASS** (`general_rules`: 136/136, `full_flow`: 115/115) | — |


## GUI-05a — Trang chủ và khung chung (Header, Footer, BottomNav)

| Tiêu chí | Cách kiểm | Kết quả | Ảnh trước → sau |
|---|---|---|---|
| Bố cục trang chủ ở 360 px và 1280 px đẹp, cân đối, đủ thông tin & chức năng, không cuộn ngang, đạt tương phản axe-core AA | So trực quan ảnh trước/sau trên trình duyệt thật + chạy `general_rules`, `full_flow`, `design_screens` | **PASS** (360 px & 1280 px) | `shots/gui-05/a-home-before-360.png` → `shots/gui-05/a-home-after-360.png`; `shots/gui-05/a-home-before-1280.png` → `shots/gui-05/a-home-after-1280.png` |
| Ngoài đường thuận (`site-info` người bán rỗng / lỗi mạng) & đủ toàn bộ link HF1/HF2 ở Header + Footer | Chạy `footer_consent` (31/31 PASS) + `HF header/footer` 360 & 1280 | **PASS** | — |


## GUI-05b — Danh mục, chi tiết món, thẻ sản phẩm và tìm kiếm

| Tiêu chí | Cách kiểm | Kết quả | Ảnh trước → sau |
|---|---|---|---|
| Danh mục (`/shop/`) ở 360 px và 1280 px: lưới thẻ đều, tag `Combo` không đè badge `Hết hàng`, bộ lọc & tìm kiếm mượt | So trực quan ảnh trước/sau + chạy `design_screens` (`A2,DK2,A9,DP4`), `general_rules`, `full_flow` | **PASS** (360 px & 1280 px) | `shots/gui-05/b-catalog-before-360.png` → `shots/gui-05/b-catalog-after-360.png`; `shots/gui-05/b-catalog-before-1280.png` → `shots/gui-05/b-catalog-after-1280.png` |
| Chi tiết món (`/shop/item/?code=CA-THU`) ở 360 px và 1280 px: hộp chọn mua và bảng thông tin đóng thẻ rõ ràng | So trực quan ảnh trước/sau + `design_screens` (`A3,DK3,A10,DE10`) | **PASS** (360 px & 1280 px) | `shots/gui-05/b-item-before-360.png` → `shots/gui-05/b-item-after-360.png`; `shots/gui-05/b-item-before-1280.png` → `shots/gui-05/b-item-after-1280.png` |
| Ngoài đường thuận (món hết hàng `A7/DE2`, mất mạng `A6/DE9`, tìm không thấy `DE1`) | Kịch bản `design_screens` + `full_flow` | **PASS** | `shots/gui-05/b-outofstock-before-360.png` → `shots/gui-05/b-outofstock-after-360.png`; `shots/gui-05/b-outofstock-before-1280.png` → `shots/gui-05/b-outofstock-after-1280.png` |


## GUI-05c — Giỏ hàng (`/shop/cart/`), ô mã giảm giá, giỏ mini

| Tiêu chí | Cách kiểm | Kết quả | Ảnh trước → sau |
|---|---|---|---|
| Giỏ hàng đủ món ở 360 px và 1280 px: thẻ món thoáng, số tiền `tabular-nums`, hộp mã giảm giá rõ nét, không cuộn ngang | So trực quan ảnh trước/sau + `design_screens` (`B1,DK4,B5,B6,DE13,DE7`) | **PASS** (360 px & 1280 px) | `shots/gui-05/c-cart-before-360.png` → `shots/gui-05/c-cart-after-360.png`; `shots/gui-05/c-cart-before-1280.png` → `shots/gui-05/c-cart-after-1280.png` |
| Ngoài đường thuận (giỏ trống `B4`, giỏ có món hết & đổi giá `B3/DE11`, mã lỗi `B7`) | Kịch bản `design_screens` + `general_rules` + `full_flow` | **PASS** | `shots/gui-05/c-cart-empty-before-360.png` → `shots/gui-05/c-cart-empty-after-360.png`; `shots/gui-05/c-cart-changed-before-1280.png` → `shots/gui-05/c-cart-changed-after-1280.png` |


## GUI-05d — Đặt hàng (`/shop/checkout/`) và thanh toán

| Tiêu chí | Cách kiểm | Kết quả | Ảnh trước → sau |
|---|---|---|---|
| Màn nhập thông tin nhận hàng (`C1/DK5`) ở 360 px và 1280 px: thanh bước, form, thẻ QR và tóm tắt đơn sắc nét, cuộn đáy không bị thanh dính che | So trực quan ảnh trước/sau + `payment_choice` (77/77 PASS) + `design_screens` (`C1,DK5`) | **PASS** (360 px & 1280 px) | `shots/gui-05/d-checkout-before-360.png` → `shots/gui-05/d-checkout-after-360.png`; `shots/gui-05/d-checkout-before-1280.png` → `shots/gui-05/d-checkout-after-1280.png` |
| Màn thanh toán & đếm ngược giữ hàng (`D1/DK6`) ở 360 px và 1280 px: khung đồng hồ, 3 bước hướng dẫn và tổng tiền rõ ràng | So trực quan ảnh trước/sau + `design_screens` (`D1,DK6,D3,DE5`) | **PASS** (360 px & 1280 px) | `shots/gui-05/d-payment-before-360.png` → `shots/gui-05/d-payment-after-360.png`; `shots/gui-05/d-payment-before-1280.png` → `shots/gui-05/d-payment-after-1280.png` |
| Ngoài đường thuận (nhập thiếu/sai `C2/DE3`, hết hàng lúc đặt `C3/DP1`, mất mạng `C4/DP6`, hết giờ giữ `D4/DP2`, shop đóng `C7/DE14`, 429 `C8`, 409 `C9`) | Kịch bản `design_screens` + `payment_choice` + `full_flow` | **PASS** | `shots/gui-05/d-invalid-before-360.png` → `shots/gui-05/d-invalid-after-360.png`; `shots/gui-05/d-invalid-before-1280.png` → `shots/gui-05/d-invalid-after-1280.png` |


## GUI-05e — Tra cứu đơn và chi tiết trạng thái đơn (`/shop/orders/`)

| Tiêu chí | Cách kiểm | Kết quả | Ảnh trước → sau |
|---|---|---|---|
| Màn tra cứu đơn (`F1/DE6`) ở 360 px và 1280 px: thẻ form, thông báo không tìm thấy và khối hỗ trợ cân đối, không lộ SĐT lên URL | So trực quan ảnh trước/sau + `design_screens` (`F1,F2,DE6`) + `full_flow` | **PASS** (360 px & 1280 px) | `shots/gui-05/e-lookup-before-360.png` → `shots/gui-05/e-lookup-after-360.png`; `shots/gui-05/e-lookup-before-1280.png` → `shots/gui-05/e-lookup-after-1280.png` |
| Màn chi tiết đơn sau thanh toán (`E1/DK7`) ở 360 px và 1280 px: pill mã đơn, timeline 5 mốc, biên lai món và `"Tra đơn khác"` rõ ràng, không lộ dữ liệu người nhận | So trực quan ảnh trước/sau + `design_screens` (`E1,DK7,E3,DO1`) + `full_flow` | **PASS** (360 px & 1280 px) | `shots/gui-05/e-order-before-360.png` → `shots/gui-05/e-order-after-360.png`; `shots/gui-05/e-order-before-1280.png` → `shots/gui-05/e-order-after-1280.png` |
| Ngoài đường thuận (đơn bị huỷ `E2/DO3`, giao không thành công `E4/DO2`, huỷ một phần `E5`) | Kịch bản `design_screens` | **PASS** | `shots/gui-05/e-cancelled-after-360.png`, `shots/gui-05/e-cancelled-after-1280.png` |


## GUI-05f — Trang nội dung CMS, Góc bếp, Giới thiệu và 404

| Tiêu chí | Cách kiểm | Kết quả | Ảnh trước → sau |
|---|---|---|---|
| Trang chính sách, liên hệ, cách mua hàng (`/pages/?slug=…`) ở 360 px và 1280 px: mục lục, điều hướng bên, link nội văn bản có gạch chân (axe AA) | So trực quan ảnh trước/sau + `content_pages` (58/58 PASS) + `design_screens` (`F3,F4,F5,DO4,DO5,DO6`) | **PASS** (360 px & 1280 px) | `shots/gui-05/f-policy-before-360.png` → `shots/gui-05/f-policy-after-360.png`; `shots/gui-05/f-policy-before-1280.png` → `shots/gui-05/f-policy-after-1280.png` |
| Góc bếp danh sách & bài viết (`/blog/`) ở 360 px và 1280 px: chip chuyên mục không tràn, thẻ bài viết & thẻ món trong bài đẹp | So trực quan ảnh trước/sau + `content_pages` + `design_screens` (`F6,F7,DO7,DO8`) | **PASS** (360 px & 1280 px) | `shots/gui-05/f-blog-before-360.png` → `shots/gui-05/f-blog-after-360.png`; `shots/gui-05/f-blog-before-1280.png` → `shots/gui-05/f-blog-after-1280.png` |
| Trang Giới thiệu (`/about/`) và trang 404 (ngoài đường thuận — đường dẫn không tồn tại) ở 360 px và 1280 px | So trực quan ảnh trước/sau + `content_pages` + `design_screens` (`L1,L2,F8,DO9`) | **PASS** (360 px & 1280 px) | `shots/gui-05/f-about-before-360.png` → `shots/gui-05/f-about-after-360.png`; `shots/gui-05/f-about-before-1280.png` → `shots/gui-05/f-about-after-1280.png`; `shots/gui-05/f-404-before-360.png` → `shots/gui-05/f-404-after-360.png`; `shots/gui-05/f-404-before-1280.png` → `shots/gui-05/f-404-after-1280.png` |
| Hồi quy tổng lực toàn bộ 86 màn thiết kế + múi giờ + bất biến | `run_shop_e2e.py --suite general_rules --suite full_flow --suite content_pages --suite formats_timezones --suite design_screens` | **PASS — APPROVED** (`136 + 115 + 58 + 73 + 91` đạt, `0` lỗi) | — |


## GUI-05 (tinh chỉnh theo Mẫu B do PO Duy duyệt)

| Tiêu chí | Cách kiểm | Kết quả | Ảnh cập nhật |
|---|---|---|---|
| Thanh tìm kiếm viên thuốc 42 px (`max-width: 520px` căn giữa) trên máy tính và 40 px trên điện thoại; đệm trên/dưới Header 16 px rõ ràng, không chạm viền kể cả khi mở gợi ý & vòng sáng focus | Xem trực tiếp ảnh Playwright 360 px & 1280 px (`A1, A2, A9, DK1, DK2, DP4`) + chạy `design_screens` (91/91 PASS) | **PASS** (360 px & 1280 px) | `shots/gui-05/a-home-after-1280.png`, `shots/gui-05/a-home-after-360.png`, `shots/gui-05/b-catalog-after-1280.png`, `shots/gui-05/b-catalog-after-360.png` |
| Bỏ hộp viền bao ngoài khối `"Đang có hàng"` trên trang chủ máy tính; khôi phục đầy đủ đệm trên/dưới của Footer (`.top`, `.legal`, `.reserveNav`) | Xem trực tiếp ảnh Playwright + `footer_consent` (31/31 PASS) + `general_rules` (136/136 PASS) + `full_flow` (115/115 PASS) | **PASS — APPROVED** | `shots/gui-05/a-home-after-1280.png`, `shots/gui-05/a-home-after-360.png` |


## GUI-06 — Nút chat Zalo nổi trên mọi trang Shop

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Hiển thị nút tròn nổi góc dưới phải trên trang chủ, chi tiết món, giỏ hàng ở 360 px và 1280 px; có `aria-label`, focus được bằng bàn phím, `href="https://zalo.me/..."`, `target="_blank"`, `rel*="noopener"` | Kịch bản Playwright `shop_general_rules.py` ở 360 px & 1280 px: kiểm toạ độ bounding box không đè lên `BottomNav` / nút `"Thêm vào giỏ"` / thanh giỏ cố định, ẩn trên `/shop/checkout/` | **PASS — ĐẠT** (360 px & 1280 px) | `shots/gui-06/zalo-home-360.png`, `shots/gui-06/zalo-home-1280.png`, `shots/gui-06/zalo-item-360.png`, `shots/gui-06/zalo-item-1280.png`, `shots/gui-06/zalo-cart-360.png`, `shots/gui-06/zalo-cart-1280.png` |
| Ngoài đường thuận: `site-info` trả `seller.zalo: ""` → không render nút Zalo nổi | Giả lập `/api/public/site-info/` trả `zalo: ""` trên trình duyệt 360 px & 1280 px, kiểm `[data-testid='zalo-floating-btn']` count = `0` | **PASS — ĐẠT** (360 px & 1280 px) | `shots/gui-06/zalo-absent-home-360.png`, `shots/gui-06/zalo-absent-home-1280.png` |


## GUI-07 — Ảnh cho các mục danh mục: combo, cá, ghẹ, mực, tôm…

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Khối danh mục ở trang chủ và dải chip đầu trang `/shop/` hiện ảnh đại diện từ món đầu tiên có ảnh trong mục (`alt`, `loading="lazy"`, khung `1:1` không giật bố cục) | Giả lập catalog có món gắn ảnh hợp lệ (`COMBO-BEP-NHA`, `CA-THU`, `GHE-XANH`) trên trình duyệt 360 px & 1280 px, kiểm `naturalWidth > 0` và xem ảnh chụp | **PASS — ĐẠT** (360 px & 1280 px) | `shots/gui-07/home-categories-360.png`, `shots/gui-07/home-categories-1280.png`, `shots/gui-07/catalog-categories-360.png`, `shots/gui-07/catalog-categories-1280.png` |
| Ngoài đường thuận: mục chưa có ảnh (`Tôm`) hoặc ảnh món bị lỗi mạng (`CA-HOI-NU` trả 404 → `onError`) tự động lui về khung SVG nội bộ, không hiện icon ảnh vỡ | Giả lập `broken-cat-img.png` trả 404 trên trình duyệt 360 px & 1280 px, kiểm thẻ chuyển sang SVG fallback sạch sẽ | **PASS — ĐẠT** (360 px & 1280 px) | `shots/gui-07/home-categories-360.png`, `shots/gui-07/catalog-categories-1280.png` |


## GUI-08 — Đổi chữ "từ 1 kg" theo mức mua tối thiểu mới 0,5 kg

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Bỏ mọi chữ viết cứng `"1 kg"` về mức tối thiểu; khi `min_qty = "0.5"`, ghi chú danh mục hiện `"Mua tối thiểu 0,5 kg"`, nút thẻ món hiện `"Thêm 0,5 kg"`, bấm ở `0,5 kg` mở hộp xác nhận `"Mỗi món mua tối thiểu 0,5 kg. Bớt nữa sẽ bỏ món này khỏi giỏ."` | Kịch bản Playwright `shop_general_rules.py` ở 360 px & 1280 px + `grep -rn "1 kg"` + bộ test `test-quantity.mjs` (`65/65`), `test-cart-reconcile.mjs` (`24/24`) | **PASS — ĐẠT** (360 px & 1280 px) | `shots/gui-08/catalog-min-05kg-360.png`, `shots/gui-08/catalog-min-05kg-1280.png`, `shots/gui-08/cart-remove-dialog-05kg-360.png`, `shots/gui-08/cart-remove-dialog-05kg-1280.png` |
| Ngoài đường thuận / tương thích động: khi API catalog trả `min_qty = "1"` (hoặc `"1.0"`), giao diện tự động hiện `"Thêm 1 kg"` và `"Mua tối thiểu 1 kg"` (không viết cứng `0,5 kg` trong component) | Chạy toàn bộ `full_flow` (`115/115 PASS`) và `design_screens` (`91/91 PASS`) với dữ liệu seed `min_qty = 1.0` của backend hiện tại | **PASS — ĐẠT** | — |


## GUI-09 — Tìm ảnh minh hoạ trên mạng cho các món đang bán

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| 6 ảnh món (`BACH-TUOC`, `CA-HOI-NU`, `CA-THU`, `GHE-XANH`, `MUC-ONG`, `TOM-SU-1`) đúng loài, tươi/sống, không chữ/watermark/mặt người, cạnh ngắn ≥ 1200 px, ≤ 10 MB, giấy phép thương mại miễn phí Wikimedia Commons ghi đủ trong `nguon-anh.md` | Kiểm kích thước pixel/dung lượng + xem trực tiếp từng ảnh bằng mắt + kiểm bảng nguồn trong `anh-san-pham/nguon-anh.md` | **PASS — ĐẠT** (6/6 ảnh đạt chuẩn) | `anh-san-pham/{BACH-TUOC,CA-HOI-NU,CA-THU,GHE-XANH,MUC-ONG,TOM-SU-1}.jpg` |


## GUI-10 — Banner trang chủ thiếu hình

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Ca 1 (slide CMS không có ảnh): hiển thị nền biển đêm kèm minh hoạ SVG nội bộ (hải đăng, tàu cá, la bàn, đàn cá), chữ trắng tương phản cao, đúng 1 thẻ `<h1>` | Kịch bản Playwright `shop_general_rules.py` ở 360 px & 1280 px + xem ảnh chụp | **PASS — ĐẠT** (360 px & 1280 px) | `shots/gui-10/banner-slide-no-image-360.png`, `shots/gui-10/banner-slide-no-image-1280.png` |
| Ca 2 (ngoài đường thuận — CMS `home-banner` trả 404 hoặc rỗng): vẫn hiện banner mặc định cùng nền minh hoạ SVG nội bộ, `<h1>Cá Về: hải sản cấp đông theo lô</h1>`, dòng phụ từ `stripText`, nút `"Xem hàng đang có"` → `/shop/` | Giả lập `/api/public/content/entries/?code=home-banner` trả 404 ở 360 px & 1280 px, kiểm DOM + xem ảnh chụp | **PASS — ĐẠT** (360 px & 1280 px) | `shots/gui-10/banner-cms-404-360.png`, `shots/gui-10/banner-cms-404-1280.png` |
| Ca 3 (slide CMS có ảnh thật): hiển thị ảnh nền phủ lớp tối (`::after`) giúp chữ trắng đọc rõ, ẩn SVG minh hoạ dự phòng | Giả lập slide CMS có `image` hợp lệ ở 360 px & 1280 px, kiểm DOM + xem ảnh chụp | **PASS — ĐẠT** (360 px & 1280 px) | `shots/gui-10/banner-slide-with-image-360.png`, `shots/gui-10/banner-slide-with-image-1280.png` |
| Phần (c) — 3 ảnh banner ngang có giấy phép thương mại miễn phí lưu tại `anh-san-pham/banner/` kèm nguồn trong `nguon-anh.md` | Xem trực tiếp 3 ảnh `banner-{1,2,3}.jpg` (cảng cá Lăng Cô, Nha Trang, Mũi Né Phan Thiết) + kiểm kích thước ≥ 1704 px | **PASS — ĐẠT** | `anh-san-pham/banner/banner-{1,2,3}.jpg` |
| Hồi quy tổng lực toàn bộ Shop (`general_rules`, `full_flow`, `design_screens`, `content_pages`) | `run_shop_e2e.py --skip-build --suite general_rules --suite full_flow --suite design_screens --suite content_pages` | **PASS — APPROVED** (`168 + 115 + 91 + 58` đạt, `0` lỗi) | — |


## GUI-11 — Gỡ ô "Chuyển khoản quét mã QR · Tiền về đủ là đơn tự xác nhận" ở trang chủ

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Trang chủ không còn chữ `"Tiền về đủ là đơn tự xác nhận"` và `"Chuyển khoản quét mã QR"` ở khối bên cạnh banner; thẻ `"Combo nấu nhanh"` tự cân chiều cao 252 px ngang bằng hero banner trên máy tính (1280 px), không cuộn ngang ở 360 px & 1280 px | Kịch bản Playwright `shop_general_rules.py` + `shop_design_screens.py` (`A1`, `DK1`) + xem ảnh chụp 360 px & 1280 px | **PASS — ĐẠT** (360 px & 1280 px) | `shots/gui-11/home-no-pay-tile-360.png`, `shots/gui-11/home-no-pay-tile-1280.png` |
| Không ảnh hưởng thông tin thanh toán ở trang đặt hàng (`/shop/checkout/`), trang thanh toán (`/shop/orders/?code=…`) và trang chính sách | Chạy trọn bộ `general_rules` (`170/170 PASS`), `full_flow` (`115/115 PASS`), `design_screens` (`91/91 PASS`) | **PASS — APPROVED** | — |
