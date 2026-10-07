# Thiết kế Shop Cá Về (bản thiết kế 06/10/2026, chờ Duy duyệt)

- **Canvas gốc** (xem trực quan, bấm thử được): https://claude.ai/artifact/SPSQLR5rMEtuBFreYbK96J
- `screens/*.dc.html`: HTML tĩnh, style inline. Mở bằng trình duyệt để xem. Icon và font cần mạng. Thẻ `<sc-if>`, `<sc-for>`, `{{…}}` và khối `<script type="text/x-dc">` là cú pháp của canvas, khi code thì thay bằng state React. Dev đọc cấu trúc, khoảng cách, màu và chữ từ HTML.
- `canvas.json`: vị trí và tên từng màn trên canvas.
- **Luật bắt buộc: `UI-RULES.md`.** Đặc tả từng component (47 cái: giải phẫu, biến thể, trạng thái, props, a11y): **`COMPONENTS.md`**, kèm 7 bảng hình `screens/CMP-*.dc.html`. Cách code: `HUONG-DAN-CODE.md`. Chia lô: `PLAN.md`. Prompt dán cho Claude Code: `PROMPT.md`.
- Đối chiếu thiết kế với code và backend hiện tại: `DOI-CHIEU-CODE.md` (Tech Lead, 06/10).
- Dữ liệu trên thiết kế là **dữ liệu giả**. Ô có ngoặc vuông `[…]` là chỗ chờ số liệu thật. Ô "LOGO" chờ file Duy upload.

## Cách đọc
- Mỗi luồng là một hàng: màn đầu là **happy case**, các màn sau là **lỗi hoặc ngoại lệ** của bước đó.
- Tên có `[Popup]` hoặc `[Toast]`: lớp phủ nằm trên màn cha. Trên điện thoại là bottom sheet, dialog hoặc toast; trên máy tính là hộp thoại giữa màn.
- Một trang Next.js responsive phục vụ cả bản điện thoại (390 px) và bản máy tính (1280 px). Hai bộ màn là hai khổ của cùng một trang.
- Mã E-0x khớp bảng ngoại lệ trong `doc/business-process-spec.md`.

## Chốt của Duy trong đợt thiết kế này (06/10/2026), cần ghi `doc/decisions.md` ở lô 0
1. Bố cục bán lẻ kiểu Long Châu. Token giữ theo `DESIGN.md` (một màu nhấn `#1F66D1`).
2. Giá theo kg, **tối thiểu 1 kg**, bước 0,5 kg (bước 0,5 do thiết kế đề xuất, chờ Duy xác nhận). Combo tính theo combo.
3. Tồn kho chỉ hiện "Còn hàng / Sắp hết / Hết", **không hiện số kg**. Hết hàng thì hiện nút **"Liên hệ chúng tôi"**.
4. Không hiện ngày nhập lô.
5. Bỏ hoá đơn điện tử.
6. Shop không hiện luồng hoàn tiền. Đơn huỷ sau khi đã trả tiền ghi "Cá Về sẽ gọi cho bạn".
7. Địa chỉ giao là **một ô**, có nút mở **Google Maps** để tìm, ghim rồi tự điền. Duy đồng ý gửi địa chỉ cho Google; chính sách quyền riêng tư phải nêu việc này.
8. Thanh toán xong thì vào thẳng **trang đơn hàng, cũng là trang tra cứu đơn**. Không có màn "thành công" riêng.
9. Trang đơn hàng công khai **không hiện người nhận** (tên, số điện thoại, địa chỉ), theo bất biến 9. Mã đơn giữ dạng `SO…` như code.

## Danh mục màn (72 màn + 7 bảng component)

### Điện thoại · A Chọn hàng

| File | Màn | Khổ |
|---|---|---|
| `screens/Home.dc.html` | A1 · Happy · Trang chủ | 390×2150 |
| `screens/Main.dc.html` | A2 · Happy · Danh mục | 390×844 |
| `screens/Product.dc.html` | A3 · Happy · Chi tiết sản phẩm | 390×1240 |
| `screens/A4-Toast.dc.html` | A4 · [Popup] Đã thêm vào giỏ | 390×844 |
| `screens/A5-NotFound.dc.html` | A5 · Lỗi · Tìm không thấy | 390×844 |
| `screens/A6-Offline.dc.html` | A6 · Lỗi · Mất mạng, không tải được hàng | 390×844 |
| `screens/A7-OutOfStock.dc.html` | A7 · Ngoại lệ · Sản phẩm tạm hết | 390×844 |
| `screens/A0-Loading.dc.html` | A8 · Trạng thái · Đang tải | 390×844 |
| `screens/A8-SearchSuggest.dc.html` | A9 · [Popup] Gợi ý khi gõ tìm | 390×844 |
| `screens/A9-ComboDetail.dc.html` | A10 · Happy · Chi tiết combo | 390×1240 |

### Điện thoại · B Giỏ hàng

| File | Màn | Khổ |
|---|---|---|
| `screens/Cart.dc.html` | B1 · Happy · Giỏ hàng | 390×844 |
| `screens/B2-RemoveConfirm.dc.html` | B2 · [Popup] Xác nhận bỏ món | 390×844 |
| `screens/B3-CartChanged.dc.html` | B3 · Ngoại lệ · Giá đổi / món đã hết trong giỏ | 390×844 |
| `screens/B4-CartEmpty.dc.html` | B4 · Ngoại lệ · Giỏ trống | 390×844 |

### Điện thoại · C Đặt hàng

| File | Màn | Khổ |
|---|---|---|
| `screens/Checkout.dc.html` | C1 · Happy · Thông tin nhận hàng | 390×1000 |
| `screens/C1b-MapPicker.dc.html` | C1b · [Popup] Chọn vị trí trên Google Maps | 390×844 |
| `screens/C1c-AddressFilled.dc.html` | C1c · Happy · Địa chỉ tự điền từ bản đồ | 390×1000 |
| `screens/C2-Invalid.dc.html` | C2 · Lỗi · Nhập thiếu / sai | 390×1000 |
| `screens/C3-SoldOut.dc.html` | C3 · [Popup] Hết hàng lúc đặt (E-06) | 390×844 |
| `screens/C4-NetworkError.dc.html` | C4 · [Popup] Lỗi kết nối khi đặt | 390×844 |
| `screens/C5-LocationDenied.dc.html` | C5 · [Popup] Không lấy được vị trí / bản đồ lỗi | 390×844 |

### Điện thoại · D Thanh toán

| File | Màn | Khổ |
|---|---|---|
| `screens/Payment.dc.html` | D1 · Happy · Thanh toán | 390×844 |
| `screens/D2-PayCancelled.dc.html` | D2 · Lỗi · Huỷ / lỗi trên SePay → thanh toán lại | 390×844 |
| `screens/D3-PayPending.dc.html` | D3 · Ngoại lệ · Đang chờ xác nhận tiền | 390×844 |
| `screens/D4-Expired.dc.html` | D4 · [Popup] Hết giờ giữ hàng (E-01) | 390×844 |
| `screens/D5-Underpaid.dc.html` | D5 · Ngoại lệ · Chuyển thiếu tiền (E-02) | 390×844 |
| `screens/D6-LeavePayment.dc.html` | D6 · [Popup] Rời trang thanh toán? | 390×844 |

### Điện thoại · E Sau thanh toán

| File | Màn | Khổ |
|---|---|---|
| `screens/Success.dc.html` | E1 · Happy · Thanh toán xong → vào thẳng trang đơn hàng (tra cứu) | 390×1240 |
| `screens/E2-Cancelled.dc.html` | E2 · Ngoại lệ · Đơn bị huỷ → Cá Về gọi lại (E-03, E-07) | 390×844 |
| `screens/E3-Delivered.dc.html` | E3 · Happy · Đơn đã giao | 390×1240 |
| `screens/E4-DeliveryFailed.dc.html` | E4 · Ngoại lệ · Giao không thành công (E-08) | 390×844 |

### Điện thoại · F Tra cứu & trang phụ

| File | Màn | Khổ |
|---|---|---|
| `screens/F1-Lookup.dc.html` | F1 · Happy · Tra cứu đơn (mã + SĐT) | 390×844 |
| `screens/F2-LookupNotFound.dc.html` | F2 · Lỗi · Không tìm thấy đơn | 390×844 |
| `screens/P1-Policy.dc.html` | F3 · Trang chính sách (mẫu) | 390×1240 |
| `screens/P2-Contact.dc.html` | F4 · Trang liên hệ | 390×844 |
| `screens/P3-HowToBuy.dc.html` | F5 · Trang cách mua hàng | 390×1240 |
| `screens/G1-KitchenList.dc.html` | F6 · Góc bếp · danh sách | 390×1240 |
| `screens/G2-KitchenArticle.dc.html` | F7 · Góc bếp · bài viết | 390×1600 |

### Máy tính

| File | Màn | Khổ |
|---|---|---|
| `screens/DesktopHome.dc.html` | Happy · 1 · Trang chủ | 1280×1600 co giãn |
| `screens/DesktopCategory.dc.html` | Happy · 2 · Danh mục | 1280×1100 co giãn |
| `screens/DesktopProduct.dc.html` | Happy · 3 · Chi tiết sản phẩm | 1280×1100 co giãn |
| `screens/DesktopCart.dc.html` | Happy · 4 · Giỏ hàng | 1280×900 co giãn |
| `screens/DesktopCheckout.dc.html` | Happy · 5 · Thông tin nhận hàng | 1280×900 co giãn |
| `screens/DesktopPayment.dc.html` | Happy · 6 · Thanh toán | 1280×900 co giãn |
| `screens/DesktopSuccess.dc.html` | Happy · 7 · Đơn hàng (sau thanh toán) | 1280×1150 co giãn |
| `screens/DesktopModalSoldOut.dc.html` | [Popup] Hết hàng lúc đặt (E-06) | 1280×800 |
| `screens/DesktopModalExpired.dc.html` | [Popup] Hết giờ giữ hàng (E-01) | 1280×800 |
| `screens/DesktopMapPicker.dc.html` | [Popup] Chọn vị trí trên Google Maps | 1280×800 |
| `screens/DesktopSearchSuggest.dc.html` | [Popup] Gợi ý khi gõ tìm | 1280×800 |
| `screens/DesktopRemoveConfirm.dc.html` | [Popup] Xác nhận bỏ món | 1280×800 |
| `screens/DesktopNetworkError.dc.html` | [Popup] Lỗi kết nối khi đặt | 1280×800 |
| `screens/DesktopLeavePayment.dc.html` | [Popup] Rời trang thanh toán? | 1280×800 |
| `screens/DesktopNotFound.dc.html` | Lỗi · Tìm không thấy | 1280×900 co giãn |
| `screens/DesktopOutOfStock.dc.html` | Ngoại lệ · Sản phẩm hết hàng | 1280×1100 co giãn |
| `screens/DesktopInvalid.dc.html` | Lỗi · Nhập thiếu / sai | 1280×900 co giãn |
| `screens/DesktopPayCancelled.dc.html` | Lỗi · Thanh toán chưa thành công | 1280×900 co giãn |
| `screens/DesktopPayPending.dc.html` | Ngoại lệ · Đang chờ xác nhận tiền | 1280×900 co giãn |
| `screens/DesktopLookup.dc.html` | Lỗi · Tra cứu không thấy đơn | 1280×900 co giãn |
| `screens/DesktopToast.dc.html` | [Toast] Đã thêm vào giỏ + giỏ mini | 1280×900 co giãn |
| `screens/DesktopLoading.dc.html` | Trạng thái · Đang tải | 1280×1100 co giãn |
| `screens/DesktopOffline.dc.html` | Lỗi · Mất mạng | 1280×900 co giãn |
| `screens/DesktopComboDetail.dc.html` | Happy · Chi tiết combo | 1280×1100 co giãn |
| `screens/DesktopCartChanged.dc.html` | Ngoại lệ · Giỏ đổi giá / món hết | 1280×900 co giãn |
| `screens/DesktopUnderpaid.dc.html` | Ngoại lệ · Chuyển thiếu tiền (E-02) | 1280×900 co giãn |
| `screens/DesktopOrderStates.dc.html` | Đơn hàng · Đã giao / Giao không thành công / Bị huỷ | 1280×1400 co giãn |
| `screens/DesktopPolicy.dc.html` | Trang chính sách + cách mua hàng | 1280×1300 co giãn |
| `screens/DesktopContact.dc.html` | Trang liên hệ | 1280×900 co giãn |
| `screens/DesktopKitchenList.dc.html` | Góc bếp · danh sách | 1280×1200 co giãn |
| `screens/DesktopKitchenArticle.dc.html` | Góc bếp · bài viết | 1280×1500 co giãn |

### Đặc tả header/footer & landing

| File | Màn | Khổ |
|---|---|---|
| `screens/Landing.dc.html` | Landing page — giới thiệu thương hiệu | 1280×2700 co giãn |
| `screens/HeaderFooter-Mobile.dc.html` | Header & footer · điện thoại (đặc tả từng link) | 880×2600 |
| `screens/HeaderFooter-Desktop.dc.html` | Header & footer · máy tính (đặc tả từng link) | 1280×2600 |

### Bảng component (đặc tả hình: biến thể × trạng thái × thông số)

| File | Nội dung |
|---|---|
| `screens/CMP-1-Tokens.dc.html` | Component · 1 · Token (màu, chữ, khoảng cách, bo góc, bóng, chuyển động, icon) |
| `screens/CMP-2-Buttons.dc.html` | Component · 2 · Nút, chip, link, công tắc |
| `screens/CMP-3-Inputs.dc.html` | Component · 3 · Ô nhập, địa chỉ, tìm kiếm, tóm tắt lỗi |
| `screens/CMP-4-Product.dc.html` | Component · 4 · Thẻ sản phẩm, nhãn tồn, giá, bộ tăng giảm |
| `screens/CMP-5-Cart-Order.dc.html` | Component · 5 · Giỏ, thanh toán, đơn hàng |
| `screens/CMP-6-Navigation.dc.html` | Component · 6 · Header, điều hướng, footer |
| `screens/CMP-7-Overlay-Feedback.dc.html` | Component · 7 · Popup, toast, banner, trạng thái |
