# features/checkout

Luồng thanh toán cổng SePay (VietQR) cho Shop — story P4 của
`doc/features/2026-09-26-sepay-cong-thanh-toan/`.

## Nội dung

- `gateway.ts` — `redirectToGateway(session)`: dựng `<form method="POST">` với đúng thứ tự
  `session.fields` rồi submit sang `session.checkout_url`. Không tính tiền, không ký, không
  thêm/bớt/sắp lại field — chỉ chuyển tiếp dữ liệu máy chủ đã lập sẵn (BR-TT-13).
  `goToMockGateway(orderCode, amount)` — chỉ dùng ở chế độ mock, điều hướng GET tới trang
  giả lập cổng của chính Shop (static export không có route nhận POST thật).
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

## Hợp đồng — đã đối chiếu với BE (P1/P3, `03-dev-notes.md`)

- `POST /api/shop/orders/<code>/checkout/` trả `{checkout_url, fields: [{name, value}, …],
  environment}`. `fields` là **mảng có thứ tự** (chữ ký HMAC phụ thuộc thứ tự) — FE không
  được thêm/bớt/sắp lại/đổi tên field, chỉ render thành `<input type="hidden">` theo đúng
  thứ tự rồi submit `<form method="POST" action={checkout_url}>` (`gateway.ts`,
  `redirectToGateway`).
- `GET /api/shop/orders/<code>/?phone_last4=...` **CHƯA** trả `booked_expires_at` (chỉ có ở
  response đặt hàng) và **CHƯA** trả `name` mỗi dòng (chỉ `item_code`, `qty`, `amount`).
  `lib/api.ts` (`mapOrderStatus`) tự suy `is_paid`/`is_expired` từ `status` thô
  (BOOKED/PAID/PROCESSING/COMPLETED/CANCELLED/AUTO_CANCELLED) và hiện tạm mã hàng khi
  thiếu tên. Thiếu `booked_expires_at` thì `OrderPaymentPanel` ẩn đồng hồ đếm ngược thay vì
  suy đoán — nút "Thanh toán lại" vẫn dùng được vì BE tự chặn khi hết hạn.
- `success_url`/`cancel_url`/`error_url` trỏ về `/shop/orders?code=...&result=success|cancel|error`.
- Chế độ mock (`lib/mock.ts`) trả **cùng kiểu trên dây** (`WireOrderStatus`,
  `WireCreateOrderResponse`) qua một hàm map duy nhất trong `lib/api.ts`, và trả đủ
  `booked_expires_at` + tên hàng (đầy đủ hơn API thật hôm nay) để luồng đếm ngược chạy được
  khi demo — không dùng `fields` của mock để điều hướng thật (static export không có route
  nhận POST), xem `goToMockGateway`.

Còn nợ (BE cần bổ sung để hết giả lập phần đếm ngược trên trang tra đơn):
thêm `booked_expires_at` và tên mặt hàng vào `GET /api/shop/orders/<code>/`.
