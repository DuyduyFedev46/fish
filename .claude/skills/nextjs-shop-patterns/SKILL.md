---
name: nextjs-shop-patterns
description: Pattern frontend Cá Về — Next.js 14 App Router ở chế độ static export (Firebase Hosting), client component fetch lúc chạy, lib/api.ts + mock mode, giỏ hàng, VietQR, UI tiếng Việt, hiệu năng React. Dùng khi viết hoặc sửa bất cứ gì trong frontend/ hoặc erp-console/.
---

# Next.js Shop theo cách của Cá Về

Nguồn tham khảo: `react-best-practices`, `web-design-guidelines` (vercel-labs/agent-skills),
`nextjs-developer` (Jeffallan/claude-skills), `frontend-developer` (wshobson/agents).
Đã lọc chỉ giữ phần áp dụng được cho **static export**.

## Ràng buộc gốc — static export

`next.config.mjs` có `output: "export"` → **không có server lúc chạy**:
- ❌ Không Server Actions, không Route Handlers (`app/api/*`), không `cookies()`/`headers()`,
  không ISR/revalidate, không middleware, không `next/image` tối ưu (đã `unoptimized`).
- ❌ Route động `[code]` cần `generateStaticParams` — thường **tránh**; dùng query string
  (`/shop/item/?code=CA01`) như code hiện có.
- ✅ Trang cần dữ liệu thật → `"use client"` + `useEffect` gọi `lib/api.ts` lúc chạy.
- ✅ Trang tĩnh thuần (landing, SEO) → server component, không fetch.

## Cấu trúc thư mục — chia theo MODULE TÍNH NĂNG (Duy yêu cầu 2026-09-24)

```
app/                 chỉ route, mỏng — page.tsx import màn hình từ features/<x>
features/<module>/   api.ts · mock.ts · types.ts · components/ · README.md (module làm gì, story, endpoint)
shared/ui/           component dùng chung (Shell, Icon, StateBox…)
shared/lib/          http.ts (apiFetch), format.ts, tiện ích chung
README.md            sơ đồ thư mục + giải thích từng file cấu hình gốc bằng 1 dòng
```
- Module không import vào ruột module khác; dùng chung thì đưa lên `shared/` (hoặc `features/auth`).
- Không barrel `index.ts`; import bằng alias `@/`.
- Áp dụng bắt buộc cho `erp-console/`. `frontend/` (Shop) đang theo cấu trúc cũ `components/` + `lib/` —
  chuyển dần khi có đợt sửa Shop.

## Gọi API

- **Mọi** call đi qua `lib/api.ts` (`apiFetch`) — không `fetch` rải rác trong component.
- Hàm mới phải có nhánh mock tương ứng trong `lib/mock.ts` (khi `NEXT_PUBLIC_USE_MOCK=1`)
  để FE làm song song được khi BE chưa xong. Kiểu dữ liệu khai ở `lib/types.ts`, khớp
  đúng JSON của serializer Django.
- Lỗi → `ApiError(message, status)`; UI hiện `message` tiếng Việt, không hiện stack.
- Shop là **công khai**: chỉ gọi `/api/shop/*`. Không bao giờ hiển thị giá vốn/lãi lỗ ở Shop.
- Back-office (`erp-console/`) dùng token DRF (`/api/auth/token/`); ẩn giá vốn theo quyền
  `view_costprice` — nhưng **backend mới là lớp chặn thật**, FE chỉ ẩn cho gọn.

## Component & trạng thái

- Mỗi trang dữ liệu có đủ 3 trạng thái: **đang tải · lỗi (có nút thử lại) · rỗng**.
- Huỷ cập nhật state khi unmount (`let active = true` … cleanup) như `app/shop/page.tsx`.
- Giỏ hàng qua `components/CartContext.tsx`; không tạo store thứ hai.
- Tiền: format bằng `lib/format.ts` (VND, không số lẻ). Khối lượng theo `Kg`.
- Thời gian giữ chỗ/TTL hiển thị bằng `CountdownTimer` — lấy mốc hết hạn từ backend,
  không tự tính.

## Hiệu năng (lọc từ Vercel best practices)

- Gọi song song các request độc lập (`Promise.all`), không nối đuôi.
- Import trực tiếp file, tránh barrel `index.ts`; thư viện nặng (vd QR) → `next/dynamic`.
- `useMemo`/`useCallback` chỉ khi có đo được re-render thừa; state để gần nơi dùng.
- Danh sách có `key` ổn định (mã sản phẩm), không dùng index.

## UI / UX / a11y

- Toàn bộ chữ tiếng Việt có dấu; brand là **"Cá Về"**.
- Mobile-first (khách mua trên điện thoại), vùng bấm ≥ 44px, ô nhập số dùng `inputMode="decimal"`.
- Nút có trạng thái disabled + loading khi submit; chặn bấm đúp khi đặt đơn.
- Ảnh có `alt`, form có `label`, tương phản đủ, focus thấy được.
- Làm giao diện mới/redesign → có thể dùng thêm skill `design-taste-frontend`.

## Kiểm tra trước khi báo xong

```bash
cd frontend && npx tsc --noEmit && npm run build     # phải sạch, không lỗi type
```
Đổi hành vi người dùng thấy được → báo QA test E2E (skill `e2e-playwright`).
Không deploy Firebase khi chưa được Duy duyệt.
