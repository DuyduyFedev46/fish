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

## Lô 2 — SHOP-2-00 (đổi URL Shop sang tiếng Anh)
- Link đổi: `/gioi-thieu/`→`/about/`, `/trang/?slug=`→`/pages/?slug=`, `/bai-viet/`→`/blog/` trong `components/{shopLinks.ts,ShopFrame,ShopHeader}`, `features/home/HomeScreen`, `features/checkout/CheckoutScreen`, `scripts/test-safe-href.mjs`, e2e `qa-lo6/7/8*`. Slug CMS giữ nguyên.
- Đổi tên `e2e/ra-soat-a2-golive.py` → `e2e/golive_footer_checks.py` (đã sửa tham chiếu trong `qa-lo6-sr21-shop.py`). `lib/` và `features/{catalog,ui-preview}` không có link cũ; `features/cart` không tồn tại.
- Kiểm: grep vùng của tôi = 0; `test-safe-href` 40/40; `tsc` chỉ lỗi ở `.next/types` cũ (route cũ đã dời), cần xoá `.next` rồi build.
- Nợ: `scripts/naming_baseline.json` còn khoá tên file cũ `ra-soat-a2-golive.py`; doc cũ nhắc URL cũ (lịch sử, không sửa).

## Lô 2 · SHOP-2-03, 2-05, 2-06, 2-04 (danh mục, chi tiết, giỏ, gợi ý khi gõ)

Người làm: fe-dev. Nhánh `shop/lo-2-catalog-cart`, chưa commit.

### File đã làm
- Màn: `features/catalog/components/{CatalogScreen,ItemDetailScreen}.tsx`, `features/cart/components/CartScreen.tsx`; route `app/shop/{page,item/page,cart/page}.tsx` (mỏng, bọc Suspense).
- Logic thuần: `features/catalog/{catalogView,cardItem,useSearchSuggest}.ts`, `features/cart/{reconcile,useCartActions}.ts`, `lib/text.ts` (foldVietnamese), `components/useHotline.ts`.
- Component mới: `ui/{SegmentedControl,ToggleButton,Breadcrumb,focusSoon}`, `catalog/{QtyStepper,AddToCart,SideFilter,SortControl}`, `cart/{CartLine,CartSummary,CartBar,MiniCart,CheckoutSteps,RemoveItemDialog}`, `search/SearchSuggest`; viết lại `ProductCard` (thêm `grid`), `SearchBox` (combobox + gợi ý), `CartContext` (`CartEntry`, `ready`, `setQty`, `updateEntries`).
- API/mock: không đổi hàm API (catalog + chi tiết đã có từ lô 1); `lib/mock.ts` thêm `short_note`/`spec`/`storage`/`description` giả cho vài món.
- Xoá: `CatalogGrid`, `AddToCartControl`, `ContactButton`. `ItemCard` tự dựng nút "Liên hệ chúng tôi". `CheckoutScreen`: gỡ bảng dòng giỏ (còn tóm tắt chỉ đọc + "Sửa giỏ hàng"), thêm chuyển về `/shop/cart/` khi giỏ còn món hết.
- Nợ lô 1: thẻ hết hàng không có hotline hợp lệ thì dẫn `/pages/?slug=lien-he` (`contactTarget`); `CART_HREF` = `/shop/cart/`; `<title>` `/shop/*` hết lặp; menu nhóm `aria-current` nhận `group`/`type=combo` từ CatalogScreen và nhóm của món ở trang chi tiết. Sửa kiểu `AboutScreen` (dùng `toCardItem` chung) theo lệnh điều phối.
- e2e: `e2e/catalog_cart_screens.py` (chụp 360/1280, kiểm không cuộn ngang). Đoạn "Còn X kg" trong e2e cũ: grep không còn (lô 1 đã vá).

### Kết quả lệnh (chạy lại sau sửa cuối)
```
npm ci: 0 · tsc: sạch · build (USE_MOCK=0): ✓ Compiled successfully, có /shop, /shop/cart, /shop/item
check-no-mock: XANH — không thấy seed mock nào trong bản build.
test-format 33/33 · test-safe-href 40/40 · test-quantity 45/45 · test-phone 17/17 · test-cart-reconcile 20/20
out/ui-preview/index.html: không tồn tại (đúng)
check_naming: OK - 6444 vi phạm cũ, không phát sinh mới
<title> out/shop: "Shop hải sản cấp đông | Cá Về"; out/shop/cart: "Giỏ hàng | Cá Về"
```
G7: file chạm hết hex (đã đổi 2 hex trong CheckoutScreen sang token); còn `features/content/components/LatestPosts.tsx:40` (`#f8fafc`, file của mkt-brand đã có từ lô 1). `transition: all`: 0.
Ảnh: `shots/lo2/{catalog,catalog-group,catalog-notfound,catalog-toast,search-suggest,item,item-out,item-combo,item-404,cart-empty,cart-changed,cart-blocked,cart-remove-dialog,cart-adjusted}-{360,1280}.png`.

### Lệch thiết kế / contract
1. Dòng giỏ máy tính dựng bằng `<ul>` + CSS grid (không `<table>` có `<th>`) để dùng một DOM cho cả hai khổ.
2. `SuggestItem` dùng `image` (ItemImage) thay `imageUrl`; ô tìm dùng nền mờ `scrim` thay `inert`.
3. Mã giảm giá ("Nhập mã") chưa có ở giỏ: thuộc lô 3b; `CartSummary` đã có prop `discount`.
4. Khối "Đổi trả / Giao hàng" ở trang chi tiết chưa làm (cần tóm tắt CMS, story lô 5). Dòng "Cân đúng số kg" không dựng (S-18).
5. Không đổi tên gốc ảnh, chưa kiểm axe tự động; kiểm tay focus (dialog, dời tiêu điểm sau Thêm/Bỏ).

### Còn nợ
- ERP: 3 nhãn vai trò trang (shipping/payment/complaints) vào `erp-console/shared/lib/enums.ts` khi làm 2b-ERP (chưa làm ở lô này).
- Chạy thêm QA chấm UI-RULES từng màn, kiểm 429/lỗi mạng giỏ bằng QA.

## Lô 2b-ERP · SHOP-2b-01, 2b-02 (ERP)

Người làm: fe-dev. Chưa commit.

- `erp-console/features/catalog`: `types.ts` (CatalogItem + `short_note/spec/storage/origin`, ItemGroup `slug`, `ItemGroupPatch`), `catalogModel.ts` (`ITEM_LIMITS` 60/500/2000, `SHOP_TEXT_FIELDS`, `validateGroupSlug`), `api.ts` (`updateItemGroup`), `permissions.ts` (`changeItemGroup`), `messages.ts`, `mock.ts` (kiểm SĐT/giá/mã lô/độ dài như BE, slug tự sinh/trùng/PATCH), `components/{ItemForm,ItemDetailScreen,ItemGroupModal,ItemGroupList}.tsx`, `catalog.test.ts` (+4 ca).
- Chi tiết món: 4 ô mới sửa tại chỗ chỉ khi có `catalog.change_item` (Chủ); người khác chỉ xem. Form thêm món có khối "Chữ hiển thị trên Shop". Lỗi 400 của BE hiện dưới đúng ô.
- Nhóm hàng: cột "Đường dẫn", nút "Sửa" (chỉ Chủ, `catalog.change_itemgroup`) mở hộp đổi đường dẫn; thêm nhóm có ô đường dẫn tuỳ chọn (bỏ trống BE tự sinh).
- `features/audit/auditModel.ts`: nhãn `update_item`, `update_itemgroup`, `content_load`. `shared/lib/enums.ts`: `entryPageRole` thêm shipping/payment/complaints (`features/content/pageRoles.ts` của mkt-brand vẫn khai riêng, có thể đổi sang ENUMS sau).
- Kiểm: `npm ci` ok; `tsc` sạch; `npm test` 113 file, 1340 ca đạt; build `USE_MOCK=0` xanh; `check-no-mock` XANH; `check-ai-chunks` XANH.
- Ảnh: `shots/lo2/erp-item-edit-1280.png`, `erp-group-list-1280.png`, `erp-group-edit-1280.png` (hộp sửa nhóm báo lỗi trùng).
- Nợ: mock chỉ kiểm chữ bằng bản rút gọn; backend là lớp chặn thật.

## Sửa sau review lô 2
- M1 (ERP): ô Mô tả chuyển vào khối "Chữ hiển thị trên Shop" ở `ItemForm`; trang chi tiết chia 2 nhóm, nhóm "Chữ hiển thị trên Shop" có dòng "Khách thấy: …" và 5 ô sửa tại chỗ có bộ đếm n/max (thêm prop `maxLength` tuỳ chọn cho `InfoField` editable, dùng textarea + counter; `shared/ui/detail/InfoField.tsx`).
- M2: thêm `frontend/scripts/test-catalog-view.mjs` (21 ca: 2-03 AC2, 2-04 AC1/AC3/AC4). Tách logic "Tìm gần đây" sang `features/catalog/recentSearches.ts` (thuần, test được).
- Low: ô tìm không đưa chuỗi giống SĐT lên `?q=`; "Tìm gần đây" tối đa 5 mục, mỗi từ ≤ 40 ký tự; `CartLine` món hết bỏ `aria-label` trên `<li>`, chữ ", đã hết hàng" ẩn nằm trong link tên; `erp-console/features/content/pageRoles.ts` dùng nhãn từ ENUMS.
- Kiểm: FE `tsc` sạch, `test-catalog-view` 21/21, `test-cart-reconcile` 20/20 (không build FE vì QA đang dùng `out/`); `check_naming` không mới. ERP `tsc` sạch, 1340 test đạt, build USE_MOCK=0 xanh.

## Sửa sau QA lô 2
- B1 (ERP): sửa tại chỗ Mô tả/Quy cách/Bảo quản/Nguồn hàng nay hiện đúng câu 400 của BE dưới ô (`fieldSaveErrorMessage` trong `catalogModel.ts`, dùng ở `ItemDetailScreen.saveField`); thêm 2 test (ERP 1342 đạt). ItemForm đã đúng từ trước (đọc `fieldErrors`).
- B2 (G8): `grep -rnE "sellable_qty|CatalogGrid|AddToCartControl" frontend` = 0. Sửa `frontend/README.md`; fixture e2e `qa-lo6-sr21-shop.py`, `qa-lo7-shop-real.py`, `qa-lo8-shop-format.py` sang `{groups, items}` + `stock_level`; ca kiểm "Còn X kg" đổi thành kiểm nhãn "Sắp hết/Hết hàng" và không hiện số kg; `qa-lo8-shop-django.py` đọc `["items"]` + `stock_level`; `content_item_card.py` bỏ tên `CatalogGrid` trong chú thích. Các script e2e chỉ kiểm cú pháp (`py_compile`), chưa chạy lại trên trình duyệt.
- Low: toast không che thanh mua ở trang chi tiết 360 px (`body[data-buy-bar]`); nhóm không tồn tại hiện "Không tìm thấy nhóm hàng" thay vì "· 0 món"; SĐT trong `?q=` đã chặn ở `SearchBox.go` (sửa sau khi QA chạy). Tiêu đề story 2b-01 "Chủ/Quản lý" là việc của PO (code đúng: chỉ Chủ). L3 (title trang CMS 404, 2 thẻ robots) thuộc mkt-brand; L5/L6 dữ liệu CMS/lô 5.
- Kiểm: FE `tsc` sạch, build xanh, check-no-mock XANH, 6 test script đạt; ERP `tsc` sạch, 1342 test đạt, build xanh; check_naming không mới.
