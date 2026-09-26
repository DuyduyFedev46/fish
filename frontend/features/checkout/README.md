# features/checkout

Luồng thanh toán cổng SePay (VietQR) cho Shop — story P4 của
`doc/features/2026-09-26-sepay-cong-thanh-toan/`.

## Nội dung

- `gateway.ts` — `redirectToGateway(session)`: điều hướng trình duyệt sang trang cổng
  (GET query string hoặc POST form ẩn, tuỳ `session.gateway_method`). Không tính tiền,
  không ký, chỉ chuyển tiếp dữ liệu máy chủ đã lập sẵn (BR-TT-13).
- `storage.ts` — nhớ tạm `{order_code, phone_last4}` trong `sessionStorage` để trang tra
  đơn không bắt khách gõ lại SĐT khi vừa quay về từ cổng (PA, spec §7.1).
- `components/PaymentPanel.tsx` — màn "đặt hàng thành công" trên trang checkout: tổng
  tiền, đồng hồ giữ chỗ, nút "Thanh toán bằng VietQR".
- `components/OrderPaymentPanel.tsx` — phần thanh toán trên trang tra đơn: đã thanh
  toán / đang chờ IPN / hết hạn / chưa thanh toán + nút thanh toán lại.
- `components/CheckoutScreen.tsx` — toàn bộ màn `/shop/checkout/` (giỏ hàng → form giao
  hàng → `PaymentPanel`). `app/shop/checkout/page.tsx` chỉ còn bọc `Suspense`.
- `components/MockGatewayPanel.tsx` — trang "cổng SePay" giả lập, chỉ render khi
  `NEXT_PUBLIC_USE_MOCK=1` **và** URL có `?mock_gateway=1` (do `lib/mock.ts` sinh ra khi
  gọi `startCheckoutSession` ở chế độ mock). Dùng để QA/E2E đi hết luồng mà không cần
  mạng thật hay khoá SePay thật.

## Vì sao hàm gọi API không nằm ở đây

`startCheckoutSession` (lập tham số thanh toán, story P1) và các hàm Shop API khác đều
nằm trong `lib/api.ts` + nhánh mock trong `lib/mock.ts`, theo quy ước sẵn có của toàn bộ
Shop (`nextjs-shop-patterns`: "mọi call đi qua `lib/api.ts`"). `features/checkout/` chỉ
gom phần **UI và tiện ích trình bày** riêng cho luồng thanh toán, để bắt đầu chia theo
module tính năng mà không phải refactor toàn bộ `lib/` hiện có.

## Hợp đồng còn là giả định

`PaymentCheckoutSession` (trong `lib/types.ts`) và endpoint
`POST /api/shop/orders/<code>/checkout-session/` là **giả định của FE**, dựng theo
`02-stories.md` P1 (BE làm song song). Khi mục "P1 (BE)" xuất hiện trong
`03-dev-notes.md` của hồ sơ, đối chiếu lại: tên endpoint, tên field trong `fields`,
`gateway_method` (GET hay POST), và field `is_paid` / `is_expired` /
`booked_expires_at` trên `GET /api/shop/orders/<code>/`.
