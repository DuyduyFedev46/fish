# Shop cho khách (`frontend/`)

> Cập nhật 02/10/2026, theo code `main` `bf62b81`.
> Hợp đồng thanh toán chi tiết: `frontend/features/checkout/README.md`. `frontend/README.md` đã cũ ở vài chỗ (xem cuối file).

## Là gì

Trang giới thiệu và Shop cho khách. Khách **không đăng nhập** (guest checkout, gộp theo SĐT). Next.js 14 (App Router),
**xuất tĩnh** ra `out/`, đưa lên Firebase Hosting (site `cangca-loc`, staging `cangca-loc-staging`). Mọi dữ liệu lấy từ API công khai của Django lúc chạy.

## Trang

| Route | Nội dung | API dùng |
|---|---|---|
| `/` | Trang giới thiệu (SEO), bài viết mới | `public/content/entries/` |
| `/shop/` | Bảng giá theo nhóm, tồn khả dụng | `shop/catalog/` |
| `/shop/item/?code=<mã hàng>` | Chi tiết mặt hàng hoặc combo | `shop/catalog/{item_code}/` |
| `/shop/checkout/` | Giỏ hàng, form giao hàng, đặt đơn, nút thanh toán VietQR, đồng hồ giữ chỗ | `shop/orders/`, `shop/orders/{code}/checkout/` |
| `/shop/orders/?code=...` | Tra đơn bằng mã đơn và 4 số cuối SĐT, thanh toán lại | `shop/orders/{code}/?phone_last4=` |
| `/bai-viet/` | Danh sách và chi tiết bài viết (`?chuyen-muc=`) | `public/content/...` |
| `/trang/` | Trang chính sách (bảo mật, điều kiện giao dịch, đổi trả, thông tin người bán) | `public/content/pages/by-role/{role}/` |

Chân trang hiện thông tin người bán và liên kết chính sách (`public/site-info/`, `public/content/footer-links/`).
Route chi tiết dùng query string (`?code=`) thay cho route động vì xuất tĩnh không dựng trước được trang cho mã hàng chưa biết.
URL công khai `/bai-viet/`, `/trang/`, `?chuyen-muc=` giữ tiếng Việt (ngoại lệ có chủ đích của quy tắc đặt tên).

## Cấu trúc thư mục

```
frontend/
  app/                    route (page.tsx, layout.tsx), app/shop/layout.tsx bọc CartProvider
  components/             thành phần cũ dùng chung: CartContext, ShopHeader/Footer, CatalogGrid, AddToCartControl,
                          CountdownTimer, ItemImageFrame
  features/
    checkout/             luồng thanh toán cổng SePay: gateway.ts (dựng form POST), storage.ts, PaymentPanel,
                          OrderPaymentPanel, CheckoutScreen, MockGatewayPanel (cổng giả khi mock)
    content/              bài viết, thẻ mặt hàng trong bài, ArticleBody, safeHref.ts (chặn link nguy hiểm)
    site/                 thông tin người bán, chân trang pháp lý, thông báo gọi xác nhận đơn
  lib/                    api.ts (MỌI gọi Shop API đi qua đây), mock.ts, types.ts, format.ts (tiền, kg, giờ VN)
  scripts/                check-no-mock.mjs, test-format.mjs, test-safe-href.mjs
  e2e/                    kịch bản Playwright (Python)
  next.config.mjs         output: "export", trailingSlash
  firebase.json / firebase.staging.json   Hosting production / staging (staging có header noindex)
```

Code mới đặt trong `features/<module>/`. `components/` và `lib/` là phần có từ đầu, giữ nguyên quy ước "mọi gọi API qua `lib/api.ts`".

## Thanh toán

1. Đặt đơn: `POST /api/shop/orders/` trả mã đơn và `booked_expires_at` (hạn giữ chỗ).
2. Bấm "Thanh toán bằng VietQR": `POST /api/shop/orders/{code}/checkout/` trả `checkout_url` và mảng `fields` có thứ tự.
   `features/checkout/gateway.ts` dựng `<form method="POST">` với đúng thứ tự field rồi submit sang SePay. FE **không** tính tiền, không ký, không đổi field.
3. SePay đưa khách về `/shop/orders/?code=...&result=success|cancel|error`. Trang tra đơn hiện trạng thái thật từ API.
   Về trang `success` chưa có nghĩa đã trả tiền; chỉ IPN qua adapter mới xác nhận.

Dữ liệu cá nhân: giỏ hàng trong `localStorage` chỉ giữ mã hàng, tên hàng, giá và số kg, không có dữ liệu khách. `sessionStorage` nhớ tạm mã đơn và 4 số cuối SĐT để khách vừa quay về từ cổng không phải gõ lại.
Không lưu tên, SĐT đầy đủ, địa chỉ vào storage hay URL.

## Mock

`NEXT_PUBLIC_USE_MOCK=1` thì `lib/mock.ts` (và `features/*/mock.ts`) trả dữ liệu giả, không cần backend. Có cổng SePay giả
(`MockGatewayPanel`, bật khi URL có `?mock_gateway=1`) để đi hết luồng thanh toán. Mã đơn mẫu để tra thử nằm trong `lib/mock.ts`.

`.env.example` để `NEXT_PUBLIC_USE_MOCK=1`, nên `.env.local` chép từ đó sẽ bật mock khi chạy máy mình.

## Lệnh

```bash
cd frontend
npm ci
NEXT_PUBLIC_USE_MOCK=1 npm run dev                       # mock -> http://localhost:3000
NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev   # nối Django máy mình
npm run build                                            # build tĩnh ra out/, phải sạch
node scripts/test-format.mjs && node scripts/test-safe-href.mjs   # kiểm hàm định dạng, chặn link
```

**Build để deploy** (chỉ khi Duy yêu cầu): luôn truyền biến **trực tiếp** trên dòng lệnh, vì `frontend/.env.local` (mock) đè lên `.env.production`.

```bash
NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=<URL API staging> npm run build
node scripts/check-no-mock.mjs out      # bản build thật không được chứa chuỗi mock
firebase deploy --only hosting --config firebase.staging.json --project keolai-63ec1     # staging
```

URL API từng môi trường và lệnh production: `doc/ops/moi-truong.md`.

## E2E

Kịch bản Playwright (Python) ở `frontend/e2e/`, ví dụ `qa_sepay_checkout.py` (luồng thanh toán mock), `qa-lo8-shop-django.py` (với backend thật),
`ra_soat_cms13_public.py` (bài viết công khai). Đọc đầu mỗi file để biết cần build mock hay backend thật.

## `frontend/README.md` đã cũ ở đâu (tại `bf62b81`)

- Ghi route `/shop/[itemCode]`. Thực tế là `/shop/item/?code=`.
- Ghi "VietQR là payload tĩnh giả lập từ backend". Đã thay bằng cổng SePay (`features/checkout/`).
- Không nhắc `features/`, `/bai-viet/`, `/trang/`, `scripts/check-no-mock.mjs`.
- Ghi build bằng `npm run build && npm run start`. Shop là web tĩnh, deploy bằng Firebase, không dùng `next start`.
- `features/checkout/README.md` ghi tra đơn "CHƯA trả `booked_expires_at`". Backend nay đã trả trường này khi đơn còn `BOOKED`.
