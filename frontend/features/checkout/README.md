# features/checkout

```mermaid
flowchart TD
  A["Khách điền thông tin nhận hàng"] --> T{"Cờ tìm địa chỉ bật?"}
  T -- "có, khách bấm Tìm địa chỉ" --> V["Tìm gợi ý VietMap qua máy chủ Cá Về"]
  V --> G["Điền số nhà, hiện gợi ý phường để khách tự chọn"]
  G --> B{"Bấm Đặt hàng"}
  T -- "tắt hoặc khách gõ tay" --> B
  B -- "còn chỗ sai" --> A
  B -- "hết hàng" --> C["Sửa giỏ rồi đặt lại"]
  B -- "mất mạng" --> D["Thử lại cùng mã yêu cầu"]
  B -- "đặt được" --> E["Trang đơn: thanh toán, giữ hàng 30 phút"]
  D --> E
  C --> B
  E --> F["Chuyển khoản quét mã QR"]
  F --> H["Chờ xác nhận tiền"]
  H --> I["Trang đơn: đã thanh toán, theo dõi giao hàng"]
```

Đặt hàng, thanh toán và trang đơn (cũng là trang tra cứu) của Shop, Shop lô 3+4 + VietMap phương án A
(`doc/features/2026-10-06-shop-giao-dien-moi/02b-tech-design.md` §1, §1.9b, §3.3–3.5, §6).

## Nội dung

- `components/CheckoutScreen.tsx` — `/shop/checkout/`: form nhận hàng, ô đồng ý (không tick sẵn), tìm địa chỉ VietMap, gửi đơn,
  các hộp thoại C3 (hết hàng), C4 (mất mạng), C5 (tìm địa chỉ lỗi), C8 (429), C9 (chính sách đổi), X2 (Shop tạm ngưng).
- `components/OrderScreen.tsx` — `/shop/orders/?code=&result=`: tra cứu (F1/F2) và mọi màn đơn. Chọn màn bằng `orderState.ts`.
  Màn con: `PaymentView` (D1, D2, nền D4), `PendingView` (D3), `ExpiredView` (D4 trang), `OrderView` (E1–E5), `LookupForm`.
- `orderState.ts` — `screenFor(order, result, clock)`: trạng thái máy chủ + `result` URL → màn; đồng hồ giữ hàng; dòng thời gian.
- `components/AddressField.tsx`, `AdministrativeUnitPicker.tsx` — địa chỉ có cấu trúc (STA-02): kiểu mới/cũ, tỉnh → [huyện] → xã chọn từ `GET /api/shop/administrative-units/`, ô tìm không dấu, nút "Tìm địa chỉ" (chỉ hiện khi `site-info.address_search_enabled === true`), banner gợi ý phường + nút "Dùng phường này", gửi `delivery_address_parts`.
- `components/AddressSearchSheet.tsx`, `addressSearch.ts` — hộp tìm địa chỉ qua máy chủ Cá Về (`POST /api/shop/address-search/`, `POST /api/shop/address-place/`, 02b §1.9b phương án A): không nạp thư viện bản đồ, không gọi thẳng dịch vụ bản đồ ngoài từ trình duyệt, không xin vị trí, không toạ độ; dòng thông báo VietMap hiện trước request đầu tiên; lỗi 503/mạng đóng hộp rồi mở C5, hai lần lỗi trong phiên thì lần bấm sau mở thẳng C5.
- `formRules.ts`, `reorder.ts` — luật form, dựng lại giỏ ("Đặt lại", "Mua lại"). Thuần TypeScript, có test.
- `requestId.ts` — `client_request_id` (sessionStorage, kèm vân tay giỏ) để không tạo đơn trùng.
- `lookupToken.ts` — mã tra đơn trong sessionStorage (`cangcaloc_order_tokens_v1`), không bao giờ trên URL.
- `gateway.ts` — chuyển sang cổng thanh toán (`fields` giữ nguyên thứ tự, BR-TT-13). `MockGatewayPanel` chỉ có ở mock.

## Quy tắc

- Không lưu tên, SĐT, địa chỉ vào storage, URL hay console. SĐT khách gõ ở form tra đơn bị bỏ ngay khi tra xong.
- Trang đơn công khai không hiện người nhận. Không chữ "hoàn tiền", không tên cổng thanh toán, không nút "Huỷ đơn".
- Gọi API qua `lib/api.ts` (`createOrder`, `lookupOrder`, `startCheckoutSession`, `searchAddress`, `getAddressPlace`) kèm nhánh mock trong `lib/mock.ts`.
