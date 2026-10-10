# Ghi chú dev FE (Shop làm lại)

## Lô 1 · khung chung (SHOP-1-01…1-06 + contract danh mục mới)

Người làm: fe-dev. Nhánh `shop/lo-1-khung-chung`, chưa commit.

### File đã làm
- Nền: `app/globals.css` (token), `app/legacy.css` (class cũ, biến cũ trỏ về token, không hex), `app/layout.tsx` (Inter qua next/font, CartProvider + ToastProvider ở gốc), `next.config.mjs` (cờ `NEXT_PUBLIC_UI_PREVIEW`), `DESIGN.md` (chỉ thêm 14 token, không dòng xoá).
- `components/ui/`: Button, IconButton (+CartBadge), Chip, TextLink, Icon, Dialog, Sheet (BottomSheet), FullscreenSheet, Popover, Toast, Banner, EmptyState, ErrorState, Skeleton, Spinner, `useModalDialog.ts`, `useReturnFocus.ts`, `cx.ts`.
- `components/catalog/`: PriceTag, StockBadge, ImageFrame, CategoryTile, ProductCard (`rail`, `row`). `components/search/SearchBox.tsx`.
- Khung: `ShopFrame`, `ShopHeader` (H1-H4, máy tính full/compact), `ShopFooter` (F1/F2 gộp dải pháp lý), `BottomNav`, `LogoSlot`, `shopLinks.ts`, `CartContext.tsx` (badge = số dòng, đọc giỏ hỏng không lỗi).
- Trang chủ: `app/page.tsx` + `features/home/` (HomeScreen, content.ts, README). `features/catalog/groupIcon.ts`.
- `/ui-preview/`: `app/ui-preview/page.preview.tsx`, `features/ui-preview/`.
- `lib/`: `types.ts` (CatalogResponse, StockLevel, SaleUnit, Money, GroupIcon, đã bỏ `sellable_qty`), `api.ts` (`getCatalog()` trả `{groups, items}`, cache 30 giây, `fresh` để thử lại), `mock.ts` (khớp contract 02b §3.1, seed nội bộ `mock_stock` không ra ngoài), `format.ts` (+`formatPriceVnd`, `formatTimeDayVn`), `quantity.ts`, `scripts/test-quantity.mjs`, `scripts/test-format.mjs` (thêm ca).
- Bọc ShopFrame: `app/shop/{page,item/page,checkout/page,orders/page}.tsx`, `app/bai-viet/page.tsx`, `app/trang/page.tsx`. Vá kiểu tối thiểu: `CatalogGrid`, `AddToCartControl`, `features/content/components/{ArticleBody,ItemCard}.tsx`, e2e `ra-soat-a2-golive.py` (chỉ fixture catalog).
- Đã xoá: landing cũ ở `app/page.tsx`, `ItemImageFrame.tsx`, `SiteLegalFooter.{tsx,module.css}`, `CartProvider` trong `app/shop/layout.tsx`, mọi hex/token cũ trong globals.

### Kết quả lệnh (chạy lại trong lượt này)
```
Run `npm audit` for details.
tsc: sạch
 ✓ Compiled successfully
 ✓ Generating static pages (11/11)
check-no-mock: 4 file mock, 35 chuỗi seed, 49 file build (out/)
check-no-mock: XANH — không thấy seed mock nào trong bản build.
test-format: 33/33 đạt, 0 sai (TZ=mặc định, lib/format.ts)
test-safe-href: 40/40 đạt, 0 sai (features/content/safeHref.ts)
test-quantity: 45/45 đạt, 0 sai (lib/quantity.ts)
out/ui-preview/index.html: không tồn tại (đúng)
 ✓ Compiled successfully
└ ○ /ui-preview                          0 B                0 B
```
- `NEXT_PUBLIC_UI_PREVIEW=1 NEXT_PUBLIC_USE_MOCK=1 npm run build`: thành công, có route `/ui-preview`.
- G7 (file lô chạm, trừ globals.css): 0 dòng. `grep -rn "transition: all" frontend/app frontend/components frontend/features`: 0 dòng. `python3 scripts/check_naming.py`: OK, không vi phạm mới.
- Playwright (build mock): 360 px và 1280 px không cuộn ngang (scrollWidth = 360 / 1280), 0 request tới fonts.googleapis.com / fonts.gstatic.com, 0 lỗi console. Dialog, Dialog cảnh báo, BottomSheet, FullscreenSheet: `role="dialog"` + `aria-modal="true"`, Tab/Shift+Tab 20 lần không ra khỏi hộp, Esc đóng, tiêu điểm về nút đã mở (cả 360 và 1280). Toast `role="status"`, tự ẩn sau 3 giây.
- Ảnh: `shots/lo1/home-360.png`, `home-1280.png`, `ui-preview-360.png`, `ui-preview-1280.png`, `ui-preview-dialog-360.png`.
- G4: N/A ở lô 1 (nút "Chọn mua" chỉ dẫn sang trang chi tiết; `lib/quantity.ts` + test sẵn cho lô 2).

### Lệch thiết kế / contract
1. Ô tìm H1 điện thoại là `<form>` + `<input>` thật (như `HeaderFooter-Mobile`), không phải link `trigger` như `Home.dc.html` và COMPONENTS #10: đích `/shop/?focus=search` chưa tồn tại ở lô 1 và SHOP-1-03 AC6 cần gõ rồi Enter. Biến thể `trigger` chưa làm.
2. Dải cam kết theo chốt mới của techlead: 3 ô điện thoại, 2 ô máy tính, không có "Cân đúng".
3. Nút giỏ và thanh đáy đi tới `/shop/checkout/` (đích tạm, 02b §9); đổi `CART_HREF` trong `components/shopLinks.ts` ở lô 2.
4. ProductCard lô 1 chỉ có `rail` và `row`. Trên máy tính hàng "Đang có hàng" dùng `rail` chuyển thành lưới 5 thẻ; biến thể `grid` + AddToCart làm ở lô 2.
5. Header máy tính dùng `display: contents` để chỉ tầng chính dính (dải trên và menu cuộn đi) mà vẫn là `<header>`.
6. Mỗi header/footer hiện tại có hai bản (điện thoại, máy tính) chuyển bằng CSS `display:none`; footer là một bản duy nhất (`<details>` mở sẵn từ 768 px).
7. Hotline lấy `seller.phone` rồi tới `confirmation_policy.hotline` (02b §6.5). Khoá site-info mở rộng (`zalo`, `registration_issued_by/on`, `website_notice_url/image`) đọc tuỳ chọn trong `ShopFrame`, chưa có dữ liệu thật nên nút Zalo và biểu tượng thông báo đang ẩn.
8. Chữ alt/nhãn của biểu tượng thông báo website ("Đã thông báo website thương mại điện tử") chưa được legal-vn duyệt (06-marketing K9); chỉ hiện khi có link.
9. Vì layout gốc không còn header/footer, các trang của mkt-brand/legacy phải tự bọc ShopFrame. Tôi bọc `bai-viet`/`trang` (đổi `<main>` thành `<div>` để khỏi lồng `<main>`) và đổi hex và `transition: all` trong `trang.module.css`, `bai-viet.module.css`, `bai-viet/page.tsx` sang token để qua G7 (file lô 5 sẽ viết lại).
10. Thêm link "Bỏ qua tới nội dung chính" (chỉ hiện khi focus) và icon `lock`, `snowflake`, `wifi-off`, `ban`, `hourglass` ngoài danh sách 02b §1.5.

### Còn nợ
- Dải chữ đầu trang máy tính ("mua từ 1 kg") đang là hằng trong `ShopFrame.tsx`; nên lấy từ `policies.min_qty_kg` khi lô 5 có.
- `app/page.tsx` giữ metadata đơn giản để mkt-brand hoàn thiện (1-09).
- e2e `ra-soat-a2-golive.py`: mới sửa fixture catalog; các ca "footer đủ 7 thông tin" theo footer cũ cần người sửa e2e viết lại cho footer mới (lô 7).
- Nhánh có Google Maps key, SearchSuggest, CartBar, MiniCart: lô sau.
- Chưa chạy `fixing-accessibility` dạng công cụ; đã kiểm tay bằng Playwright (focus trap, Esc, trả focus, aria-current, vùng chạm 44 px).

### Sửa theo review 03b (M2, L2–L4)
- M2: viết lại phần footer của `frontend/e2e/ra-soat-a2-golive.py` theo F1/F2 mới: dải pháp lý (tên, MST, địa chỉ, GCN ĐKKD nơi/ngày cấp, tel:, mailto:, không chữ chờ, ẩn khối logo khi chưa có link), nhóm "Chính sách" đúng 6 link theo CMS (có "Điều kiện giao dịch chung", "Cơ chế giải quyết khiếu nại", không "Điều khoản sử dụng"), gỡ 1 trang, `footer-links` lỗi ẩn nhóm mà dải pháp lý vẫn còn, F2 3 link mở tab mới, 375 px không cuộn ngang và link ≥ 44 px (mở nhóm Chính sách trước khi đo). Chạy trên bản `out/` tĩnh (`QA_BASE=http://127.0.0.1:3106`): mọi ca GL-01, GL-02, F2 đạt (các ca khác của file còn bám màn cũ, chưa thuộc phạm vi này).
- L2: bỏ kiểu `SellerExtras`, `ShopFrame` đọc thẳng `seller?.zalo`… từ `SellerInfo`.
- L3: bỏ regex đổi nhãn footer, dùng `l.title` của CMS.
- L4: `noticeUrl` và `noticeImage` chỉ nhận `https:` và phải qua `isSafeHref` (`ShopFooter.tsx`).
- `npx tsc --noEmit`: sạch. Không chạy `npm ci`/`npm run build` (QA đang build); sửa `ShopFrame`/`ShopFooter` chưa có trong `out/`, cần build lại khi QA xong.

### Sửa theo QA lô 1 (B2, Low title)
- B2: thêm `frontend/lib/phone.ts` (`validHotline`, `pickHotline`): chỉ nhận chuỗi gồm chữ số, khoảng trắng, dấu + ở đầu, đủ 8–15 chữ số; loại "1900 xxxx", "[hotline]". `ShopFrame`, `HomeScreen`, `ContactButton` đều dùng hàm này; không có số hợp lệ thì ẩn nút gọi và dòng hotline (header, footer, nút Liên hệ). Test: `node scripts/test-phone.mjs` 17/17 đạt. `npx tsc --noEmit` sạch. Không build (điều phối build lại).
- Low: `app/shop/layout.tsx` đặt title mặc định trọn "Shop hải sản cấp đông | Cá Về" và template "%s | Cá Về", hết lặp tên ở `/shop/*`.
