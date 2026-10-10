# Kiểm tra hiển thị thật: prototype Shop Cá Về

Ngày 2026-10-07. Chỉ đọc. Không sửa file thiết kế, không đụng repo `fish`.

## Cách làm

- **Dựng template:** `render-audit/tools/build.js` đọc `<script type="text/x-dc">` và chạy class `Component` với `DCLogic` giả lập. `props` lấy `default` trong `data-props`, `state` lấy từ constructor, còn `setState` không làm gì. Script thay `{{path}}`, mở `sc-for`/`sc-if` ở mức chuỗi (để `sc-for` trong `<tbody>` không bị trình duyệt đẩy ra ngoài bảng), bỏ các `onClick="{{fn}}"` và chuyển `<helmet>` vào `<head>`. Cả 79 board dựng xong, không còn `{{` hay `sc-` thô, không có biến `undefined`.
- **Chụp ảnh:** `tools/shoot.js` dùng playwright-core và Chromium 1194 headless. Board 390 chụp ở 390 px, board `expand: fill` chụp ở 1280 và 768 px, board cố định 880/1280 chụp đúng bề rộng. Trước khi chụp, script cho mọi animation vào chạy hết (`finish()`); animation lặp vô hạn thì dừng ở khung 0. Lần chụp đầu chưa làm bước này nên thấy lỗi giả: C3 và C1b lệch 8–15 px, popover của DesktopToast bị mờ.
- **Đo:** `scrollWidth` của trang; đáy thật của nội dung theo dòng chảy (so với `h`); thanh và popup `position:absolute`; hộp bị tràn (`scrollWidth/scrollHeight > client`); chữ trong nút xuống dòng; SVG bị bóp; ảnh vỡ; chữ đè nhau. Sau đó xem bằng mắt từng ảnh (ghép sheet, cắt phóng to chỗ nghi lỗi).
- **Giới hạn:** Google Fonts bị chặn, máy dùng font Inter cài sẵn, cùng họ chữ nên số đo gần như trùng. `Card-states.dc.html` và `Desktop.dc.html` không có trong `canvas.json` nên không kiểm.
- **Kết quả nằm ở** `scratchpad/render-audit/`: `html/` (bản đã dựng), `shots/` (104 ảnh), `sheets/` (ảnh ghép, ảnh cắt), `metrics.json`.

## Tóm tắt

| | Số board |
|---|---|
| Tổng | 79 (104 ảnh chụp) |
| **OK** | **48** |
| **Lỗi** | **31**: 11 board có lỗi hiển thị thật (A8, B3, Home, G1, G2, Product, DesktopCategory, DesktopNotFound, DesktopSearchSuggest, HeaderFooter-Mobile, CMP-5), 20 board chỉ sai `h` (bị cắt hoặc dư quá 200 px) |
| Tràn ngang | 1 board: HeaderFooter-Mobile (901 > 880). Không trang co giãn nào tràn ngang ở 768 |
| Ảnh hoặc icon vỡ | 0 (thiết kế chưa có `<img>`, icon đều là SVG nội tuyến). Có 3 SVG bị bóp nhẹ, xem bảng |

### Top 10 lỗi nặng nhất

1. **A8-SearchSuggest (390):** panel gợi ý `#sg-panel` đặt `top:76px; z-index:3` nên **đè lên ô tìm** (form nằm ở 68–112 px, z-index 2). Khách không thấy chữ "mực" đang gõ, chỉ còn mép viền xanh. Sửa: đặt `top:116px` (ngay dưới ô tìm, cách 4 px).
2. **DesktopSearchSuggest (1280):** nút xoá `.clr` (dấu X) bị luật `.srch > button` (độ ưu tiên 0,1,1) đè lên `.clr` (0,1,0). Nút nhận nền xanh `#1F66D1`, cao 40 px, padding 22 px, nên hiện thành **một hình tròn xanh trống** cạnh nút "Tìm"; icon X màu xám đậm gần như không thấy trên nền xanh. Sửa: viết `.srch > button[type=submit]` cho nút Tìm, hoặc `.srch > .clr{background:transparent;padding:0;height:36px}`.
3. **CMP-4-Product và CMP-5-Cart-Order:** nội dung thật cao 7368 và 8834 px, nhưng `h` chỉ là 5900 và 7500, nên **mất 1468 px và 1334 px** cuối bảng đặc tả. CMP-4 mất phần CategoryTile; CMP-5 mất OrderLines (phần cuối) và SuccessBanner. Dev sẽ không thấy các component này.
4. **16/23 board desktop co giãn bị cắt đáy ở 1280:** nội dung cao hơn `h` từ 79 đến 507 px nên footer (và có nơi cả nội dung) bị cắt trên canvas. Nặng nhất: Landing +507, DesktopProduct +460, DesktopHome +415, DesktopToast +401, DesktopOutOfStock +369.
5. **G2-KitchenArticle (390):** vùng cuộn trong cao 1536 px nhưng nội dung cao 2211 px, nên **footer bị ẩn gần hết**. Chỉ còn một dải 30 px thấy nửa logo "Cá Về" kẹp trên BottomNav, nhìn như lỗi.
6. **Product (390):** dòng "Đổi trả: [chính sách…]" bị thanh đáy "Thêm vào giỏ / Chọn mua" (top 1164) **che mất nửa chữ**. Nội dung kết thúc ở 1244 px.
7. **Home (390) và G1-KitchenList (390):** footer bị cắt dưới BottomNav. Ở Home footer dài tới 2233 > 2150, dải pháp lý và ô logo Bộ Công Thương bị tab bar che. Ở G1 vùng cuộn hụt 107 px, mất dòng Email và logo BCT.
8. **HeaderFooter-Mobile (880):** bảng F1 tràn ngang 21 px (`scrollWidth` 901), do chuỗi code `[link xác nhận online.gov.vn]` không xuống dòng. Cột "Nhãn" bị bóp còn khoảng 60 px nên mỗi từ một dòng ("Chính / sách / quyền / riêng tư"). Thêm vào đó `h` thiếu 258 px.
9. **Nút "Liên hệ chúng tôi" cạnh "Bỏ khỏi giỏ" (món đã hết):** ở CMP-5 (CartLine, điện thoại) chữ **xuống 2 dòng** ("Liên hệ chúng / tôi") và icon điện thoại bị bóp từ 15 còn 13,8 px. Ở B3-CartChanged chữ chạm sát viền, không còn padding, và hàng nút rộng hơn cột 12 px.
10. **Ở 768 px, DesktopCategory và DesktopNotFound:** cột "Danh mục" bên trái chuyển thành danh sách dọc rộng hết màn, cao khoảng 290 px, nên đẩy kết quả và sản phẩm xuống dưới màn hình đầu. Nên đổi thành hàng chip cuộn ngang (giống Main 390) khi màn hẹp hơn khoảng 1024 px.

Ghi chú thêm, không tính vào lỗi hiển thị: **header và footer có hai phiên bản**. HeaderFooter-Desktop (spec), Góc bếp (2 trang) và Landing dùng header có dải trên cùng, "Hotline / [hotline]" xếp 2 dòng, ô logo BCT dạng chữ chờ. Khoảng 19 trang Desktop khác dùng header không có dải trên, "Hotline [hotline]" một dòng, badge BCT. Trang đặt hàng cũng lệch spec H2/F2: trang ghi "Thanh toán an toàn | Hotline", spec ghi "Đặt hàng an toàn · Cần hỗ trợ? [hotline]". Cần chốt một bản.

## Bảng chi tiết

Quy ước "Thực/h": board điện thoại ghi đáy nội dung thật so với `h`; board co giãn ghi chiều cao trang ở khổ đó so với `h`.

### Điện thoại 390

| Board | Khổ | Thực/h | Kết quả | Lỗi cụ thể (vị trí, phần tử) | Đề xuất |
|---|---|---|---|---|---|
| Main | 390 | 844/844 | OK | Thanh giỏ (đáy) đúng chỗ. Chip "Combo" bị cắt mép phải là có chủ ý (cuộn ngang) | — |
| A4-Toast | 390 | 812/844 | OK | Toast nằm trên CartBar, cách 40 px, đúng chỗ | — |
| A5-NotFound | 390 | 599/844 | OK | — | — |
| A6-Offline | 390 | 727/844 | OK | — | — |
| A7-OutOfStock | 390 | 725/844 | OK | — | — |
| A0-Loading | 390 | 844/844 | OK | Skeleton chạy xuống dưới BottomNav, chấp nhận được với khung đang tải | — |
| **A8-SearchSuggest** | 390 | — | **Lỗi** | `#sg-panel` `top:76px` đè ô tìm (68–112 px), không thấy chữ đang gõ | `top:116px` |
| **A9-ComboDetail** | 390 | 956/1240 | **Lỗi (h)** | Dư khoảng 208 px trắng giữa "Tạm tính" và thanh đáy | `h` = 1040 |
| Cart | 390 | 844 | OK | Danh sách, ghi chú và thanh tổng đúng chỗ | — |
| B2-RemoveConfirm | 390 | 844 | OK | Dialog căn giữa, nút không méo | — |
| **B3-CartChanged** | 390 | 553/844 | **Lỗi (nhẹ)** | Món hết: nút "Liên hệ chúng tôi" không còn padding, chữ chạm viền; hàng nút tràn cột 12 px | Cho 2 nút `flex:1 1 0; min-width:0; white-space:nowrap`, rút nhãn còn "Liên hệ", hoặc xếp 2 nút thành 2 hàng |
| B4-CartEmpty | 390 | 626/844 | OK | — | — |
| Checkout | 390 | 809/1000 | OK | — | — |
| C1b-MapPicker | 390 | 844 | OK | Sheet và bản đồ đúng chỗ (sau khi chạy hết animation) | — |
| C1c-AddressFilled | 390 | 804/1000 | OK | — | — |
| C2-Invalid | 390 | 946/1000 | OK | — | — |
| C3-SoldOut | 390 | 844 | OK | Ghi chú nhẹ: "không đủ hàng" rớt riêng chữ "hàng" xuống dòng | Bọc cụm trạng thái bằng `white-space:nowrap` (tuỳ chọn) |
| C4-NetworkError | 390 | 844 | OK | — | — |
| C5-LocationDenied | 390 | 844 | OK | — | — |
| Payment | 390 | 587/844 | OK | — | — |
| D2-PayCancelled | 390 | 483/844 | OK | — | — |
| D3-PayPending | 390 | 576/844 | OK | — | — |
| D4-Expired | 390 | 844 | OK | — | — |
| D5-Underpaid | 390 | 543/844 | OK | — | — |
| D6-LeavePayment | 390 | 844 | OK | — | — |
| Success | 390 | 802/1240 | **Lỗi (h)** | Dư khoảng 360 px trắng trên thanh đáy | `h` = 900 |
| E2-Cancelled | 390 | 510/844 | OK | — | — |
| **E3-Delivered** | 390 | 635/1240 | **Lỗi (h)** | Dư khoảng 527 px trắng | `h` = 844 |
| E4-DeliveryFailed | 390 | 564/844 | OK | Dấu "!" ở mốc timeline tràn 2 px, mắt thường không thấy | — |
| F1-Lookup | 390 | 464/844 | OK | — | — |
| F2-LookupNotFound | 390 | 495/844 | OK | — | — |
| **G1-KitchenList** | 390 | 1283+64/1240 | **Lỗi** | Vùng cuộn 1176 px, nội dung 1283 px: footer mất dòng Email và ô logo BCT dưới BottomNav | `h` = 1350 |
| **G2-KitchenArticle** | 390 | 2211+64/1600 | **Lỗi** | Footer ẩn gần hết, chỉ lộ nửa logo "Cá Về" trên BottomNav | `h` = 2280, hoặc dừng board ngay trước footer |
| **Home** | 390 | 2233/2150 | **Lỗi** | Footer cắt 83 px; dải pháp lý và ô logo BCT bị BottomNav che | `h` = 2240 |
| P1-Policy | 390 | 1017/1240 | **Lỗi (h)** | Dư 223 px | `h` = 1040 |
| P2-Contact | 390 | 479/844 | OK | — | — |
| P3-HowToBuy | 390 | 869/1240 | **Lỗi (h)** | Dư 371 px | `h` = 900 |
| **Product** | 390 | 1244+76/1240 | **Lỗi** | Dòng "Đổi trả: […]" bị thanh "Thêm vào giỏ / Chọn mua" che nửa | `h` = 1320 |

### Máy tính co giãn (`expand: fill`), chụp ở 1280 và 768

Không trang nào tràn ngang ở 768. Ở 768 bố cục chuyển sang 1 cột hoặc lưới 3 cột đúng cách, trừ các ghi chú trong bảng.

| Board | 1280: thực/h | 768: thực | Kết quả | Lỗi cụ thể | Đề xuất |
|---|---|---|---|---|---|
| DesktopHome | 2015/1600 | 3268 | **Lỗi (h)** | Ở 1280 cắt 415 px (footer, dải 3 lợi ích). Cột "Combo nấu nhanh" hẹp nên tên xuống dòng xấu ("Combo nướng cuối / tuần"). Ở 768: lưới danh mục 4+2 và sản phẩm 3+2 bị lẻ hàng (nhẹ) | `h` = 2020; nới cột combo hoặc cho nút "Chọn mua" xuống dưới tên |
| DesktopCategory | 1304/1100 | 2285 | **Lỗi** | Ở 1280 cắt 204 px. Ở 768: sidebar "Danh mục" thành danh sách dọc khoảng 290 px, đẩy sản phẩm xuống dưới màn đầu | `h` = 1310; dưới khoảng 1024 px đổi sidebar thành hàng chip cuộn ngang |
| DesktopProduct | 1560/1100 | 2718 | **Lỗi (h)** | Ở 1280 cắt 460 px (Thông tin SP, Mô tả, footer) | `h` = 1560 |
| DesktopComboDetail | 1325/1100 | 2068 | **Lỗi (h)** | Ở 1280 cắt 225 px | `h` = 1330 |
| DesktopCart | 900/900 | 1135 | OK | — | — |
| DesktopCartChanged | 900/900 | 1087 | OK | Ghi chú nhẹ: hàng món hết (nền xám) sát mép đáy thẻ, thiếu padding dưới | Thêm `padding-bottom:4px` cho thẻ |
| DesktopCheckout | 900/900 | 1288 | OK | Ghi chú nhẹ: tay kéo resize của textarea địa chỉ nằm sát nút "Bản đồ" | `resize:none` hoặc `vertical` có chừa lề |
| DesktopInvalid | 905/900 | 1383 | OK | Lệch 5 px, không đáng kể (tay kéo resize như trên) | — |
| DesktopPayment | 900/900 | 1151 | OK | — | — |
| DesktopPayCancelled | 900/900 | 981 | OK | — | — |
| DesktopPayPending | 900/900 | 900 | OK | — | — |
| DesktopUnderpaid | 900/900 | 1084 | OK | — | — |
| DesktopSuccess | 1250/1150 | 1776 | **Lỗi (h)** | Ở 1280 cắt 100 px footer | `h` = 1250 |
| DesktopToast | 1301/900 | 1888 | **Lỗi (h)** | Ở 1280 cắt 401 px (hàng sản phẩm 2, footer). Popover giỏ mini và toast đúng chỗ | `h` = 1310 |
| DesktopLookup | 1077/900 | 1284 | **Lỗi (h)** | Ở 1280 cắt 177 px footer | `h` = 1080 |
| DesktopNotFound | 1071/900 | 1639 | **Lỗi** | Ở 1280 cắt 171 px. Ở 768 cùng lỗi sidebar như DesktopCategory | `h` = 1080; sidebar thành chip |
| DesktopOffline | 919/900 | 1126 | OK | Lệch 19 px | (tuỳ chọn) `h` = 920 |
| DesktopOutOfStock | 1469/1100 | 2140 | **Lỗi (h)** | Ở 1280 cắt 369 px | `h` = 1470 |
| DesktopLoading | 1231/1100 | 2048 | **Lỗi (h)** | Ở 1280 cắt 131 px | `h` = 1240 |
| DesktopContact | 1092/900 | 1526 | **Lỗi (h)** | Ở 1280 cắt 192 px. Ghi chú nhẹ: 5 thẻ trong lưới 4 cột để lẻ "Giờ làm việc" | `h` = 1100; dùng lưới 5 cột hoặc 3+2 |
| DesktopOrderStates | 1683/1400 | 1972 | **Lỗi (h)** | Ở 1280 cắt 283 px | `h` = 1690 |
| DesktopPolicy | 1502/1300 | 2225 | **Lỗi (h)** | Ở 1280 cắt 202 px | `h` = 1510 |
| DesktopKitchenList | 1365/1200 | 1921 | **Lỗi (h)** | Ở 1280 cắt 165 px. Header phiên bản khác: "Hotline / [hotline]" 2 dòng, ô BCT chữ chờ 2 dòng | `h` = 1370 |
| DesktopKitchenArticle | 1579/1500 | 2444 | **Lỗi (h)** | Ở 1280 cắt 79 px. Header như trên | `h` = 1580 |
| Landing | 3207/2700 | 3981 | **Lỗi (h)** | Ở 1280 cắt 507 px (khối "Hôm nay cảng có gì?" và footer). Tiêu đề "Giá theo kg, cân đúng số bạn / đặt" rớt một chữ xuống dòng | `h` = 3210; `text-wrap:balance` cho h2 |

### Máy tính cố định 1280×800 (popup, dialog)

| Board | Khổ | Kết quả | Lỗi cụ thể | Đề xuất |
|---|---|---|---|---|
| DesktopModalSoldOut | 1280 | OK | Dialog không tràn; nút đều | — |
| DesktopModalExpired | 1280 | OK | — | — |
| DesktopMapPicker | 1280 | OK | — | — |
| **DesktopSearchSuggest** | 1280 | **Lỗi** | Nút xoá `.clr` trong ô tìm hiện thành hình tròn xanh 40 px, không thấy icon X (bị `.srch > button` đè) | `.srch > button[type=submit]{…}` hoặc tăng độ ưu tiên cho `.clr` |
| DesktopRemoveConfirm | 1280 | OK | — | — |
| DesktopNetworkError | 1280 | OK | — | — |
| DesktopLeavePayment | 1280 | OK | — | — |

### Bảng spec cố định

| Board | Khổ | Thực/h | Kết quả | Lỗi cụ thể | Đề xuất |
|---|---|---|---|---|---|
| HeaderFooter-Desktop | 1280 | 2456/2600 | OK | Dư 144 px (dưới ngưỡng) | (tuỳ chọn) `h` = 2460 |
| **HeaderFooter-Mobile** | 880 | 2858/2600 | **Lỗi** | Tràn ngang 21 px (bảng F1, chuỗi code online.gov.vn); cột "Nhãn" bị bóp nên mỗi từ một dòng; cắt 258 px | `code{overflow-wrap:anywhere}` + `table-layout:fixed` với cột nhãn khoảng 110 px; `h` = 2860 |
| CMP-1-Tokens | 1280 | 4743/4800 | OK | — | — |
| CMP-2-Buttons | 1280 | 4570/4600 | OK | Badge "3" làm icon giỏ co 22 → 21,3 px, không thấy bằng mắt | — |
| CMP-3-Inputs | 1280 | 4752/4800 | OK | — | — |
| **CMP-4-Product** | 1280 | 7368/5900 | **Lỗi** | Cắt 1468 px: mất phần CategoryTile và cuối ImageFrame | `h` = 7370 |
| **CMP-5-Cart-Order** | 1280 | 8834/7500 | **Lỗi** | Cắt 1334 px: mất OrderLines (cuối) và SuccessBanner. CartLine "Đã hết": nút "Liên hệ chúng tôi" xuống 2 dòng, icon bị bóp 15 → 13,8 px | `h` = 8840; sửa nút như ở B3 |
| CMP-6-Navigation | 1280 | 9869/9890 | OK | Badge "99+" lệch ra ngoài nút 4 px, có chủ ý | — |
| CMP-7-Overlay-Feedback | 1280 | 11763/11770 | OK | — | — |

## Danh sách `h` cần chỉnh trong `canvas.json`

| Board | `h` hiện tại | `h` đề xuất | Lý do |
|---|---|---|---|
| Home.dc.html | 2150 | **2240** | Footer bị cắt dưới BottomNav |
| Product.dc.html | 1240 | **1320** | Dòng Đổi trả bị thanh đáy che |
| G1-KitchenList.dc.html | 1240 | **1350** | Footer bị cắt |
| G2-KitchenArticle.dc.html | 1600 | **2280** | Footer ẩn gần hết (hoặc cắt board trước footer) |
| A9-ComboDetail.dc.html | 1240 | **1040** | Dư 208 px |
| Success.dc.html | 1240 | **900** | Dư khoảng 360 px |
| E3-Delivered.dc.html | 1240 | **844** | Dư khoảng 527 px |
| P1-Policy.dc.html | 1240 | **1040** | Dư 223 px |
| P3-HowToBuy.dc.html | 1240 | **900** | Dư 371 px |
| DesktopHome.dc.html | 1600 | **2020** | Cắt 415 px ở 1280 |
| DesktopCategory.dc.html | 1100 | **1310** | Cắt 204 px |
| DesktopProduct.dc.html | 1100 | **1560** | Cắt 460 px |
| DesktopComboDetail.dc.html | 1100 | **1330** | Cắt 225 px |
| DesktopSuccess.dc.html | 1150 | **1250** | Cắt 100 px |
| DesktopToast.dc.html | 900 | **1310** | Cắt 401 px |
| DesktopLookup.dc.html | 900 | **1080** | Cắt 177 px |
| DesktopNotFound.dc.html | 900 | **1080** | Cắt 171 px |
| DesktopOutOfStock.dc.html | 1100 | **1470** | Cắt 369 px |
| DesktopLoading.dc.html | 1100 | **1240** | Cắt 131 px |
| DesktopContact.dc.html | 900 | **1100** | Cắt 192 px |
| DesktopOrderStates.dc.html | 1400 | **1690** | Cắt 283 px |
| DesktopPolicy.dc.html | 1300 | **1510** | Cắt 202 px |
| DesktopKitchenList.dc.html | 1200 | **1370** | Cắt 165 px |
| DesktopKitchenArticle.dc.html | 1500 | **1580** | Cắt 79 px |
| Landing.dc.html | 2700 | **3210** | Cắt 507 px |
| HeaderFooter-Mobile.dc.html | 2600 | **2860** | Cắt 258 px (sửa tràn ngang trước) |
| CMP-4-Product.dc.html | 5900 | **7370** | Cắt 1468 px |
| CMP-5-Cart-Order.dc.html | 7500 | **8840** | Cắt 1334 px |
| *(tuỳ chọn)* DesktopOffline.dc.html | 900 | 920 | Lệch 19 px |
| *(tuỳ chọn)* HeaderFooter-Desktop.dc.html | 2600 | 2460 | Dư 144 px |

Lưu ý với board co giãn: `h` đề xuất tính theo khổ 1280. Ở 768 các trang này cao hơn 1,3–2 lần (xem cột "768: thực"). Nếu canvas giữ cố định `h` khi thu hẹp thì phần dưới vẫn bị cắt. Đó là giới hạn của canvas, không phải lỗi bố cục.

## Đã sửa (2026-10-07, bước DESIGN)

Sửa trực tiếp trong `scratchpad/canvas/project/`, không đụng `canvas.json` và repo `fish`. Dựng và chụp lại toàn bộ 79 board
(`scratchpad/fix/`: `html/`, `shots/`, `metrics.json`; công cụ `fix/tools/` đọc `h` từ `$preview` của từng file). Kết quả sau sửa:
không board nào tràn ngang (kể cả 768), không board nào có nội dung vượt `h` ở 390/880/1280 (trừ A0 và Cart: skeleton/khoảng đệm
chạy dưới thanh đáy là chủ ý), cân thẻ đóng bằng HTMLParser 0 lỗi.

### Lỗi hiển thị
- **A8:** panel gợi ý `top: 116px` (dưới ô tìm 4 px); ô tìm thêm lề phải 12 px.
- **DesktopSearchSuggest:** luật nút "Tìm" thành `.srch > button[type=submit]`, nút xoá X hết bị tô xanh.
- **Home, G1, G2, Product:** tăng `h` (và vùng cuộn trong G1/G2) để footer/dòng "Đổi trả" không bị BottomNav/thanh mua che.
- **HeaderFooter-Mobile:** bảng `table-layout: fixed` (cột 30% / 33% / phần còn lại), `code` được xuống dòng (`overflow-wrap: anywhere`); hết tràn 21 px.
- **CMP-5, B3:** nút món hết đổi nhãn thành "Liên hệ" (aria-label đầy đủ), hai nút chia đôi `flex: 1 1 0; min-width: 0; nowrap`; icon không còn bị bóp.
- **DesktopCategory, DesktopNotFound:** dưới 1024 px cột "Danh mục" thành hàng chip cuộn ngang (media query), tiêu đề cột ẩn trực quan.
- **Khác:** DesktopHome cột Combo rộng hơn (tên không còn gãy); DesktopContact lưới `minmax(200px)` (5 thẻ một hàng ở 1280, 3+2 ở 768);
  DesktopCartChanged thẻ bảng thêm đệm đáy 16; textarea địa chỉ (DesktopCheckout, DesktopInvalid) `resize: none`; C3 "không đủ hàng" không gãy dòng;
  Landing `h1,h2{text-wrap: balance}`.

### Header/footer máy tính thống nhất
Mọi trang Desktop* (trừ DesktopVoucher, theo lệnh không sửa) dùng bản của HeaderFooter-Desktop: H1 + F1 cho trang mua sắm, H2 ("Đặt hàng an toàn ·
Cần hỗ trợ? [hotline]") + F2 (nền trắng, 3 link mở tab mới) cho Giỏ, Đặt hàng, Thanh toán và các popup trên nền các bước đó. Link: Tra cứu đơn →
DesktopLookup (cả spec), Cách mua → DesktopPolicy#cach-mua, Liên hệ → DesktopContact, Góc bếp → DesktopKitchenList, Về Cá Về → Landing; logo ở
DesktopPayment → DesktopLeavePayment (popup rời trang theo spec).

### Câu chữ và pháp lý
CMP-7 bỏ "chỉ còn 2 kg" (thành "Món này không đủ hàng") và "theo lô mới"; CMP-4/CMP-5 bỏ "bỏ ngay + Hoàn tác" (luôn qua popup B2), bỏ "gọi API sau";
Landing "0,5 kg" → "1 kg", bỏ "Hôm nay cảng có gì", "Xem hàng hôm nay", "lô mới về", nút "Kiểm tra khu vực giao" thành link chính sách giao hàng,
"Không ưng thì đổi" thành "Hàng có vấn đề, báo Cá Về"; Home/DesktopHome bỏ "Lô mới vừa nhập kho", ô "Lô mới về" thành "Tất cả"; C3, CMP-7 "khỏi đơn" → "khỏi giỏ";
C1 (và C1c, C2, C4) + D1 điện thoại thêm dòng "Phí giao · Báo khi xác nhận đơn". Footer mọi khổ: "Chính sách đổi trả và hoàn tiền" + "Cơ chế giải quyết
khiếu nại"; DesktopPolicy và P1 menu 6 chính sách (đổi trả thêm mục "Xử lý tiền đã chuyển khi đơn huỷ").

### `h` mới (`$preview.height`, kèm chiều cao/min-height root nếu có)
Quy tắc: nội dung thật + thanh đáy + ≤ 40 px; màn điện thoại tối thiểu 844, trang máy tính co giãn tối thiểu 800 (một khung nhìn).

| File | h cũ | h mới |
|---|---|---|
| A9-ComboDetail | 1240 | 1040 |
| C1c-AddressFilled | 1000 | 844 |
| C2-Invalid | 1000 | 900 |
| Checkout | 1000 | 844 |
| E3-Delivered | 1240 | 844 |
| Home | 2150 | 2310 |
| G1-KitchenList | 1240 | 1360 (vùng cuộn 1296) |
| G2-KitchenArticle | 1600 | 2290 (vùng cuộn 2226) |
| P3-HowToBuy | 1240 | 880 |
| Product | 1240 | 1330 |
| Success | 1240 | 920 |
| DesktopCart | 900 | 800 |
| DesktopCartChanged | 900 | 800 |
| DesktopCheckout | 900 | 800 |
| DesktopInvalid | 900 | 860 |
| DesktopPayCancelled | 900 | 800 |
| DesktopPayPending | 900 | 800 |
| DesktopPayment | 900 | 800 |
| DesktopUnderpaid | 900 | 800 |
| DesktopCategory | 1100 | 1370 |
| DesktopComboDetail | 1100 | 1390 |
| DesktopContact | 900 | 970 |
| DesktopHome | 1600 | 2040 |
| DesktopKitchenArticle | 1500 | 1620 |
| DesktopKitchenList | 1200 | 1410 |
| DesktopLoading | 1100 | 1300 |
| DesktopLookup | 900 | 1140 |
| DesktopNotFound | 900 | 1140 |
| DesktopOffline | 900 | 980 |
| DesktopOrderStates | 1400 | 1750 |
| DesktopOutOfStock | 1100 | 1530 |
| DesktopPolicy | 1300 | 1680 |
| DesktopProduct | 1100 | 1630 |
| DesktopSuccess | 1150 | 1310 |
| DesktopToast | 900 | 1370 |
| Landing | 2700 | 3250 |
| HeaderFooter-Desktop | 2600 | 2510 |
| HeaderFooter-Mobile | 2600 | 3000 |
| CMP-1-Tokens | 4800 | 4760 |
| CMP-3-Inputs | 6000 (canvas 4800) | 5940 |
| CMP-4-Product | 5900 | 7420 |
| CMP-5-Cart-Order | 7500 | 8890 |
| CMP-6-Navigation | 9890 (canvas 8000) | 9950 |

Giữ nguyên (đã khớp): các màn 844 còn lại, P1-Policy 1240 (nội dung 1211 sau khi thêm mục), CMP-2 4600, CMP-7 11770 (canvas.json đang ghi 8000),
các popup máy tính 800. **`canvas.json` chưa đổi** (theo lệnh): cần chép cột "h mới" vào `boards[*].h`.
