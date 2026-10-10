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
- ✅ Trang tĩnh thuần (không có nội dung CMS) → server component, không fetch. Trang đọc CMS (`/about/`,
  `/pages/?slug=`, `/blog/`) là client component gọi API công khai lúc chạy.

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
- Áp dụng bắt buộc cho `erp-console/`.

### Shop mới (`frontend/`, đợt `2026-10-06-shop-giao-dien-moi`, 02b §1.1 và §1.10)

```
app/                 route mỏng: / (HomeScreen) · /about/ · /pages/?slug= · /blog/ (?slug=, ?category=) · /shop/ · /shop/item/?code=
                     · /shop/cart/ · /shop/checkout/ · /shop/orders/ · /ui-preview/ (chỉ build khi NEXT_PUBLIC_UI_PREVIEW=1)
components/          ShopFrame (khung: header + main + footer + BottomNav theo props), ShopHeader, ShopFooter, BottomNav,
                     LogoSlot, CartContext
components/ui|catalog|cart|search/   component TRÌNH BÀY: props vào, callback ra, không gọi API, không đọc storage
features/<module>/   home · catalog · cart · checkout · content · site · ui-preview — mỗi màn là components/<X>Screen.tsx
lib/                 api.ts · types.ts · mock.ts (chỉ fe-dev sửa) · format.ts · quantity.ts · text.ts
```
- Mỗi màn tự bọc `ShopFrame` (bảng header/footer/BottomNav theo route ở 02b §1.4). Chỉ `*Screen.tsx` và
  `ShopHeader`/`ShopFooter` được gọi API. Không barrel, import bằng `@/`.
- URL tiếng Anh (decisions 11/10): `/about/`, `/pages/?slug=`, `/blog/?category=`. Production chưa chạy nên **không giữ** đường cũ
  `/gioi-thieu/`, `/trang/`, `/bai-viet/`, `?chuyen-muc=`. Slug nội dung CMS là dữ liệu, giữ tiếng Việt.
- Catalog `GET /api/shop/catalog/` trả `{groups, items}`; tồn kho chỉ `stock_level` (`in`/`low`/`out`), không có `sellable_qty`.
- Code Shop cũ bị xoá dần theo lô (02b §1.11): `CatalogGrid`, `AddToCartControl`, `ContactButton` (lô 2), `CountdownTimer`,
  `OrderLookup`, `features/checkout/storage.ts`, `phone_last4` (lô 3+4). Không viết thêm code dựa vào các file này.

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
- Thời gian giữ chỗ/TTL hiển thị bằng đồng hồ đếm ngược (Shop mới: `HoldCountdown` ở lô 3+4, thay `CountdownTimer`) —
  lấy mốc hết hạn từ backend, không tự tính.

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
- Shop: làm đúng `doc/design/shop/` (`UI-RULES.md`, `COMPONENTS.md`), xem skill `caveve-ui`. ERP: `doc/design/erp/UI-RULES.md`.

## Kiểm tra trước khi báo xong

```bash
cd frontend && npx tsc --noEmit && npm run build     # phải sạch, không lỗi type
```
Đổi hành vi người dùng thấy được → báo QA test E2E (skill `e2e-playwright`).
Không deploy Firebase khi chưa được Duy duyệt.

## Đặt tên (P8b, Duy chốt 01/10)

Định danh trong code (hàm, biến, class, module, thư mục, file, test, script, route API, khoá JSON, biến env, Group,
`data-testid`, id lệnh AI, khoá lưu trình duyệt) là **tiếng Anh chuẩn, không viết tắt tiếng Việt**. Chữ hiển thị cho người
dùng, comment, docstring và tài liệu vẫn tiếng Việt. Viết tắt chỉ dùng khi là chuẩn quốc tế: `VN`, `VND`, `pnl`, `id`, `url`.
Không đưa mã lô giao việc (`lo7`, `l8`, `p8_lo5`) vào tên; mã lô/story ghi trong docstring.

| Khái niệm | Dùng | Không dùng |
|---|---|---|
| Vai (Group) | `owner` `manager` `warehouse_staff` `delivery_staff` `customer_service` | `chu` `quan_ly` `nv_kho` `nv_giao` `cskh` |
| Người giao trên một phiếu | `courier` | `nv_giao` |
| Việc gọi xác nhận đơn | `confirmation` | `cskh` (module, route, khoá JSON, env) |
| Nhập lô | `receive_batches`, `ReceiveBatches*` | `nhap_lo`, `NhapLo*` |
| Lệnh AI: nhóm / mức nhạy cảm | `purchasing` `sales` `customer_service` / `high` `medium` `low` | `thu_mua` `ban_hang` / `cao` `trung_binh` `thap` |
| Giờ Việt Nam | `VN_TIME_ZONE`, `todayInVietnam()`, `today_in_vietnam()` | `VN_TZ`, `todayVn`, `vn_today` |
| Bản rà soát QA / bổ sung | `review_*` / `extra`, `followup` | `ra_soat_*` / `bosung` |

Giữ nguyên (không đổi): migration đã chạy, `AuditLog.action` đã ghi, dòng phiên bản cấu hình AI cũ, dữ liệu demo (username `kho1`, `chu_vua`..., slug, mã hàng), keyword AI có dấu, chuỗi `cangca`.
Bảng đầy đủ: `doc/features/2026-09-30-dat-ten-tieng-anh/02c-giao-viec.md` mục 1. Bảng gốc ở skill `caveve-domain`; sửa ở đó trước. URL Shop đã đổi sang tiếng Anh 11/10 (`/about/`, `/pages/?slug=`, `/blog/?category=`).

**Kiểm bằng máy** (Python 3 stdlib, chạy từ gốc repo, dưới 10 giây, không cần venv):
`python3 scripts/check_naming.py`. Exit 1 khi file MỚI có định danh tiếng Việt, hoặc số vi phạm của một file TĂNG so với
`scripts/naming_baseline.json`; in file, dòng, token. Script không xét chuỗi hiển thị, comment, docstring. Danh sách từ chặn và
allowlist ở `scripts/naming_blocklist.txt`. Chạy lệnh này trước khi báo xong mọi việc có sửa code.

Áp dụng cho FE (Shop và ERP): tên file/thư mục component, component, hook, type, khoá JSON đọc từ API, view key, route,
`data-testid`, khoá `localStorage`/`sessionStorage`, class CSS Module. Ngoại lệ cũ (thư mục `bai-viet/`, `trang/`, tham số `chuyen-muc`) đã bỏ: từ
11/10 route Shop là `about/`, `pages/`, `blog/`, tham số `category` (decisions 11/10). Nhãn trên giao diện vẫn tiếng Việt.
