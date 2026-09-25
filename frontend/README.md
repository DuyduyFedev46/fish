# Cảng cá Lộc — Frontend (Next.js)

Frontend cho vựa cá Lộc — hai mặt tiền tách biệt:

- **Landing** (`/`): trang giới thiệu, tối ưu SEO, không có giao dịch.
- **Shop** (`/shop`): bảng giá, giỏ hàng, checkout, tra cứu đơn hàng.

Xem hợp đồng đầy đủ tại `../doc/BUILD-PLAN.md` (mục "Contract D — Next.js frontend"
và "Shop API (công khai)").

## Chạy dự án

Yêu cầu Node 18+ (khuyến nghị Node 24).

```bash
npm install
npm run dev
```

Mở http://localhost:3000.

Build production:

```bash
npm run build
npm run start
```

> Nếu môi trường không có mạng khi bạn nhận dự án này, `npm install` sẽ thất bại vì
> chưa tải được các gói trong `package.json` (next, react, qrcode, ...). Chạy lại
> `npm install` khi có mạng — toàn bộ mã nguồn (app/**, components/**, lib/**) đã
> được viết sẵn và không cần chỉnh sửa gì thêm để chạy được sau khi cài xong.

## Cấu hình môi trường

Sao chép `.env.example` thành `.env.local` và chỉnh nếu cần:

```bash
cp .env.example .env.local
```

Biến môi trường:

- `NEXT_PUBLIC_API_BASE` — URL gốc của Django API (Shop API công khai). Mặc định
  `http://localhost:8000` khi không set.
- `NEXT_PUBLIC_USE_MOCK` — đặt `1` để Shop dùng dữ liệu mock có sẵn trong
  `lib/mock.ts` (không cần backend chạy). Đặt `0`/bỏ trống để gọi thẳng API thật
  qua `NEXT_PUBLIC_API_BASE`.

Khi dùng mock, có sẵn 1 đơn mẫu để test trang tra cứu đơn hàng ngay:
- Mã đơn: `DH-DEMO001`
- 4 số cuối SĐT: `6789`

Đặt một đơn mới qua `/shop/checkout` cũng lưu được vào bộ nhớ mock (tồn tại
trong suốt phiên `npm run dev` hiện tại) nên có thể tra cứu lại ngay sau khi đặt.

## Cấu trúc thư mục

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout (html/body, metadata mặc định)
│   ├── globals.css             # CSS thuần dùng chung cho cả Landing và Shop
│   ├── page.tsx                # Landing "/"
│   ├── not-found.tsx
│   └── shop/
│       ├── layout.tsx          # Layout riêng cho Shop: CartProvider + header/footer
│       ├── page.tsx            # "/shop" — bảng giá (GET /api/shop/catalog/)
│       ├── [itemCode]/
│       │   └── page.tsx        # "/shop/[itemCode]" — chi tiết mặt hàng/combo
│       ├── checkout/
│       │   └── page.tsx        # "/shop/checkout" — giỏ hàng + đặt hàng + VietQR + đếm ngược TTL
│       └── orders/
│           ├── page.tsx        # "/shop/orders" — wrapper server component (đọc ?code=)
│           └── OrderLookup.tsx # Form tra cứu đơn (mã đơn + 4 số cuối SĐT)
├── components/
│   ├── CartContext.tsx         # Giỏ hàng dạng React Context + đồng bộ localStorage
│   ├── ShopHeader.tsx / ShopFooter.tsx
│   ├── CatalogGrid.tsx         # Danh sách mặt hàng theo nhóm
│   ├── AddToCartControl.tsx    # Bộ chọn số kg + nút thêm vào giỏ
│   ├── QrCode.tsx              # Render VietQR từ vietqr.payload (thư viện qrcode)
│   └── CountdownTimer.tsx      # Đếm ngược TTL từ booked_expires_at
├── lib/
│   ├── types.ts                # Kiểu dữ liệu khớp Shop API contract
│   ├── api.ts                  # Hàm gọi API (thật hoặc mock tuỳ NEXT_PUBLIC_USE_MOCK)
│   ├── mock.ts                 # Dữ liệu + hành vi mock cho toàn bộ Shop API
│   └── format.ts                # Định dạng tiền VND / số kg
├── package.json
├── tsconfig.json
├── next.config.mjs
├── .env.example
└── .gitignore
```

## Ghi chú theo hợp đồng nghiệp vụ

- Bán theo **Kg**, giá niêm yết — không có trường/phí giao hàng (đã outscope theo
  URD/BUILD-PLAN). Địa chỉ giao hàng là bắt buộc khi đặt.
- Guest checkout — không đăng nhập, khách gộp theo số điện thoại.
- Tra cứu đơn dùng **mã đơn + 4 số cuối số điện thoại** (không cần tài khoản).
- Đơn giữ chỗ (`BOOKED`) tự huỷ sau TTL (mặc định nghiệp vụ 30 phút) — trang
  checkout hiển thị đồng hồ đếm ngược tính từ `booked_expires_at` do API trả về.
- VietQR ở giai đoạn này là payload tĩnh giả lập từ backend
  (`{"payload","amount","content"}`) — FE chỉ có nhiệm vụ render QR từ `payload`,
  không tự sinh nội dung chuyển khoản.
