# Đặc tả component Shop Cá Về

> `ux-designer` · 2026-10-07 · Trạng thái: **CHỜ DUYỆT**.
> Tài liệu cho `fe-dev` code giao diện Shop (`frontend/`) đúng thiết kế, và cho `qa-tester` có sẵn ca để kiểm.
> Nguồn: `screens/*.dc.html` (hình, chữ, trạng thái), `UI-RULES.md` (luật), `HUONG-DAN-CODE.md` (cách code),
> `PLAN.md` (lô), `DOI-CHIEU-CODE.md` (contract, khoảng trống), `DESIGN.md` gốc repo (token), số chuẩn `SO-CHUAN.md`.
> Bảng component trực quan trên canvas: **CMP-1-Tokens … CMP-7-Overlay-Feedback** (thư mục `screens/`; lúc viết tài liệu này
> các file `CMP-*` chưa có trong worktree, khi có thì đối chiếu thêm).
> **Số chuẩn thắng màn.** Khi file màn dùng số khác số chuẩn (vd. bo 16 cho hộp thoại máy tính), tài liệu này ghi số chuẩn
> và liệt kê chỗ lệch ở mục "Chỗ đã chuẩn hoá". Muốn đổi số chuẩn thì hỏi Duy, không tự đổi trong code.

## Mục lục

- [Nguyên tắc chung](#nguyên-tắc-chung) (có mục [Token cần thêm vào DESIGN.md](#token-cần-thêm-vào-designmd))
- [Bảng tổng hợp: Component → Lô → file code](#bảng-tổng-hợp-component--lô--file-code)
- [Chỗ đã chuẩn hoá so với file màn](#chỗ-đã-chuẩn-hoá-so-với-file-màn)
- [Điểm cần chốt trước khi code](#điểm-cần-chốt-trước-khi-code)
- **A. Điều khiển cơ bản:** [1 Button](#1-button) · [2 IconButton](#2-iconbutton) · [3 Chip](#3-chip) · [4 SegmentedControl](#4-segmentedcontrol) ·
  [5 Link](#5-link) · [6 Toggle](#6-toggle) · [7 TextField](#7-textfield) · [8 AddressField + MapPicker](#8-addressfield--mappicker) ·
  [9 Checkbox](#9-checkbox) · [10 SearchBox + SearchSuggest](#10-searchbox--searchsuggest) · [11 FormErrorSummary](#11-formerrorsummary)
- **B. Hàng hoá:** [12 ProductCard](#12-productcard) · [13 StockBadge](#13-stockbadge) · [14 PriceTag](#14-pricetag) · [15 QtyStepper](#15-qtystepper) ·
  [16 AddToCart](#16-addtocart) · [17 ImageFrame](#17-imageframe) · [18 CategoryTile](#18-categorytile)
- **C. Giỏ hàng:** [19 CartLine](#19-cartline) · [20 CartSummary](#20-cartsummary) · [21 CartBar](#21-cartbar) · [22 MiniCart](#22-minicart)
- **D. Đặt hàng và đơn:** [23 CheckoutSteps](#23-checkoutsteps) · [24 HoldCountdown](#24-holdcountdown) · [25 PaymentMethod](#25-paymentmethod) ·
  [26 OrderTimeline](#26-ordertimeline) · [27 OrderStatusBadge](#27-orderstatusbadge) · [28 OrderLines](#28-orderlines) · [29 SuccessBanner](#29-successbanner)
- **E. Khung trang và điều hướng:** [30 ShopHeader](#30-shopheader) · [31 BottomNav](#31-bottomnav) · [32 ShopFooter](#32-shopfooter) ·
  [33 Breadcrumb](#33-breadcrumb) · [34 SideFilter](#34-sidefilter) · [35 SortControl](#35-sortcontrol) · [36 PolicyNav](#36-policynav) · [37 LogoSlot](#37-logoslot)
- **F. Lớp phủ và phản hồi:** [38 Dialog](#38-dialog) · [39 BottomSheet](#39-bottomsheet) · [40 FullscreenSheet](#40-fullscreensheet) ·
  [41 Dropdown/Popover](#41-dropdownpopover) · [42 Toast](#42-toast) · [43 Banner/Alert](#43-banneralert) · [44 EmptyState](#44-emptystate) ·
  [45 ErrorState](#45-errorstate) · [46 Skeleton](#46-skeleton) · [47 Spinner](#47-spinner)
- [Ánh xạ màn → component](#ánh-xạ-màn--component)
- [Tự soát](#tự-soát)

---

## Nguyên tắc chung

### 1. Token là CSS variables trong `frontend/app/globals.css`, không hard-code hex

Khai báo một lần ở `:root` (lô 1). Component chỉ dùng `var(--…)`. Lệnh kiểm `grep -rnE "#[0-9A-Fa-f]{6}" frontend/components frontend/app frontend/features | grep -v globals.css` phải ra 0.
Giá trị lấy từ `SO-CHUAN.md` (trùng `DESIGN.md`). Token đánh dấu **mới** chưa có trong `DESIGN.md`: lô 1 thêm vào `DESIGN.md` (chỉ thêm, theo `PLAN.md`), không tự đặt màu khác.

| Nhóm | Biến CSS → giá trị |
|---|---|
| Nền | `--canvas` #FBFBFC · `--surface` #FFFFFF · `--surface-2` #F4F4F6 · `--surface-3` #EBEBEF |
| Viền | `--border` #E4E4E9 · `--border-strong` #D4D4DB · `--border-input` #8C8C98 |
| Chữ | `--ink` #17171C · `--ink-2` #4E4E58 · `--ink-3` #686874 |
| Nhấn | `--accent` #1F66D1 · `--accent-hover` #1A57B5 · `--accent-text` #1A5BC0 · `--accent-soft` #EBF2FE · `--on-accent` #FFFFFF · `--focus` #1F66D1 |
| Thương hiệu (**mới**) | `--brand-deep` #0E3A73 (banner, footer, nút "Tìm" header máy tính) · `--brand-deep-hover` #0A2C59 (hover nút "Tìm") · `--on-brand-muted` #D6E4FA (chữ phụ trên `brand-deep`; xem cảnh báo tương phản bên dưới) |
| Trạng thái | `--good` #157F3D / `--good-soft` #E9F7EE · `--warn` #A85A07 / `--warn-soft` #FDF3E3 · `--crit` #C0312B / `--crit-hover` #A82823 / `--crit-soft` #FCEDEC · `--on-crit` #FFFFFF |
| Viền trạng thái (**mới**) | `--crit-border` #F2C9C6 (viền FormErrorSummary) · `--good-border` #BFE5CC (viền SuccessBanner máy tính) |
| Lớp phủ (**mới**) | `--overlay` rgba(23,23,28,0.48) · `--overlay-light` rgba(23,23,28,0.24) (chỉ sau gợi ý tìm kiếm) |
| Bo góc | `--radius-sm` 6 (badge, tag) · `--radius-md` 8 (nút thường, ô nhập, stepper) · `--radius-lg` 10 (thẻ điện thoại, khối) · `--radius-card` 12 **mới** (thẻ máy tính, banner, section) · `--radius-xl` 14 (dialog) · `--radius-sheet` 16 **mới** (mép trên sheet) · `--radius-full` 999 (pill: chip, CTA chính, badge số) |
| Bóng (**mới**, Shop) | `--shadow-sm` 0 1px 2px rgba(23,23,28,.12) · `--shadow-bar` 0 -4px 16px rgba(23,23,28,.08) · `--shadow-pop` 0 12px 32px rgba(23,23,28,.12) · `--shadow-modal` 0 24px 64px rgba(23,23,28,.28) · `--shadow-card-hover` 0 6px 20px rgba(23,23,28,.06) (hover thẻ sản phẩm máy tính, đi cùng viền `--border-strong`) |
| Khoảng cách | `--space-1` 4 · `-2` 8 · `-3` 12 · `-4` 16 · `-5` 20 · `-6` 24 · `-8` 32 · `-10` 40 · `-12` 48 |
| Chiều cao | `--h-btn-lg` 48 · `--h-btn-md` 44 · `--h-btn-sm` 36 (chỉ máy tính) · `--h-input` 44 · `--h-chip` 40 · `--h-chip-brand` 32 · `--h-header` 56 · `--h-bottom-nav` 64 · `--h-buy-bar` 72 |
| Chuyển động | `--dur-press` 120ms · `--dur-color` 150ms · `--dur-swap` 180ms · `--dur-toast` 200ms · `--dur-sheet` 240ms (260ms cho sheet cao) · `--ease-out` cubic-bezier(.23,1,.32,1) · `--ease-drawer` cubic-bezier(.32,.72,0,1) · `--toast-hide` 3000ms · `--skeleton-cycle` 1.4s |
| z-index (theo `DESIGN.md`) | `--z-header` 10 · `--z-bottom-bar` 20 · `--z-popover` 25 · `--z-scrim` 30 · `--z-toast` 50 · `--z-dialog` 60 |

**Chữ** (Inter 400/500/600 qua `next/font`, số luôn `font-variant-numeric: tabular-nums`, class `.num`):
`display` 24/600/1.25 −0.015em · `title` 17/600/1.3 · `section` 15/600 · `body` 14/400/1.5 · `label` 13/500 · `caption` 12/500 · `micro` 11/600 (**chỉ** badge số) ·
giá thẻ 17/600 **`ink`** (mọi biến thể thẻ) · giá trang chi tiết và mọi tổng tiền 24/600 **`accent-text`** · đơn vị giá 12–14/500 `ink-2` · **ô nhập 16 px** (bắt buộc).
Landing được tới 60 (chỉ `Landing`, banner trang chủ máy tính).

**Focus:** `:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px }`. Trên nền `accent` hoặc `brand-deep`: viền trắng, offset −4px.
Ô nhập: viền `accent` + `box-shadow: 0 0 0 3px var(--accent-soft)`.

**Nhấn:** `:active:not(:disabled) { transform: scale(.97) }` 120ms `--ease-out`. **Hover chỉ trong `@media (hover: hover) and (pointer: fine)`** (mọi bảng "Trạng thái" bên dưới đều theo luật này).
Không `transition: all`; chỉ chuyển `transform`, `opacity`, `background-color`, `border-color`, `color`.
`prefers-reduced-motion: reduce`: bỏ scale và translate, giữ đổi màu.

**Cảnh báo tương phản (đo theo số chuẩn).** `--on-brand-muted` #D6E4FA trên `--accent` #1F66D1 chỉ đạt **≈4,2:1**, dưới AA cho chữ thường.
Vậy chữ phụ trên nền `accent` (tagline header, dải trên máy tính) dùng `--on-accent` (trắng, 5,4:1). `--on-brand-muted` chỉ dùng trên `--brand-deep` (≈8,7:1) và trên nền `--ink` (toast).
Placeholder dùng `--ink-3` (5,3:1), **không** dùng `--border-input` #8C8C98 như file màn (3,3:1, trượt AA).

**Dark mode:** token cũ có giá trị dark trong `DESIGN.md`. Token mới (bảng dưới) chưa có giá trị dark. Xem câu hỏi Q-UX-1.

### Token cần thêm vào DESIGN.md

Lô 1 **chỉ thêm** các token này vào `DESIGN.md` (frontmatter + bảng mô tả), rồi khai biến trong `globals.css`. Không đổi token cũ.

| Token | Giá trị | Dùng cho |
|---|---|---|
| `brand-deep` | #0E3A73 | banner trang chủ, footer F1, nút "Tìm" header máy tính (không dùng `accent` cho nút này) |
| `brand-deep-hover` | #0A2C59 | hover nút "Tìm", hover nút trên nền `brand-deep` |
| `on-brand-muted` | #D6E4FA | chữ phụ trên `brand-deep` và trên `ink` (toast) |
| `crit-border` | #F2C9C6 | viền khối tóm tắt lỗi (FormErrorSummary) |
| `good-border` | #BFE5CC | viền SuccessBanner máy tính |
| `overlay` | rgba(23,23,28,0.48) | lớp phủ dialog, sheet |
| `overlay-light` | rgba(23,23,28,0.24) | nền sau gợi ý tìm kiếm điện thoại |
| `radius-card` | 12px | thẻ máy tính, banner, section |
| `radius-sheet` | 16px | mép trên sheet |
| `shadow-sm` | 0 1px 2px rgba(23,23,28,.12) | ô đang chọn của SegmentedControl |
| `shadow-bar` | 0 -4px 16px rgba(23,23,28,.08) | thanh dính đáy, BottomNav, BottomSheet |
| `shadow-pop` | 0 12px 32px rgba(23,23,28,.12) | dropdown, giỏ mini, toast |
| `shadow-modal` | 0 24px 64px rgba(23,23,28,.28) | dialog, hộp thoại lớn |
| `shadow-card-hover` | 0 6px 20px rgba(23,23,28,.06) | hover thẻ sản phẩm máy tính (kèm viền `border-strong`) |

### 2. Responsive mobile-first

- Viết CSS cho điện thoại trước (thiết kế ở 390, phải chạy ở **360 không cuộn ngang**), rồi mở rộng bằng `@media (min-width: 768px)` (`md`) và `@media (min-width: 1024px)` (`lg`, lưới 4 cột).
- Container máy tính: `max-width: 1200px; margin: 0 auto; padding: 0 24px`. Lề điện thoại 16.
- Một component responsive cho cả hai khổ. Không làm hai component riêng cho điện thoại và máy tính.
- Vùng chạm ≥ 44 trên điện thoại; từ `md` (chuột) tối thiểu 40 (theo `DESIGN.md`). Chip 40 có vùng chạm mở rộng tới 44 (xem Chip).
- Thanh dính đáy, BottomNav, sheet: cộng `env(safe-area-inset-bottom)`. Khung dùng `100dvh`, không `100vh`.

### 3. Dữ liệu qua props, không gọi API trong component

- Component trong `components/ui/`, `components/catalog/`, `components/cart/` là **trình bày**: nhận dữ liệu và callback qua props, không gọi `lib/api.ts`, không đọc `localStorage`.
- Chỉ **container trang** (`app/**/page.tsx` và các `*Screen.tsx` trong `features/`) gọi `lib/api.ts`, đọc `useCart()`, rồi truyền xuống.
- Tiền là chuỗi Decimal từ API (`"278000"`), chỉ định dạng ở lớp hiển thị bằng `formatVnd` (`lib/format.ts`). Không cộng tiền bằng float để ra số khách phải trả; tổng thanh toán luôn lấy từ BE.
- Kiểu dùng chung, khai trong `lib/types.ts`:

```ts
export type StockLevel = 'in' | 'low' | 'out';      // không bao giờ là số kg
export type SaleUnit = 'kg' | 'combo';
export type GroupIcon = 'fish' | 'shrimp' | 'squid' | 'crab' | 'combo';
export type Money = string;                          // chuỗi Decimal, ví dụ "278000"
```

### 4. Kỹ thuật chung

- Shop **không có Tailwind**. Style viết bằng CSS Modules (`*.module.css`, có sẵn trong Next, không thêm thư viện) cạnh component, đọc biến từ `globals.css`.
- Không thêm thư viện UI. Hộp thoại dùng thẻ `<dialog>` gốc + `showModal()` (có top layer, nền `inert`, phím Esc). Muốn dùng thư viện focus trap thì hỏi điều phối viên.
- Icon: SVG nội tuyến nét 1,6–2 như file màn, gom vào `components/ui/Icon.tsx`, luôn `aria-hidden="true"`. `DESIGN.md` ghi Material Symbols cho ERP; xem Q-UX-2.
- Không ghi dữ liệu cá nhân vào `console`, `localStorage`, URL. Giỏ chỉ giữ mã hàng và số lượng.

---

## Bảng tổng hợp: Component → Lô → file code

> Thêm 07/10: **48. VoucherField** → lô 3b → `components/cart/VoucherField.tsx` (xem cuối file).


Lô theo `PLAN.md`. "Mới" là file chưa có. ⚠ = file mới **chưa nằm trong cột "Được sửa"** của lô trong `PLAN.md`/`DOI-CHIEU-CODE.md` §5; điều phối viên cần bổ sung vào phiếu 02c trước khi giao.

| # | Component | Lô | File code |
|---|---|---|---|
| 1 | Button | 1 | mới `components/ui/Button.tsx` |
| 2 | IconButton | 1 | mới `components/ui/IconButton.tsx` (+ `CartBadge` trong cùng file) |
| 3 | Chip | 2 (chip lọc, tìm gần đây; chip header "Tìm nhiều" bỏ, chốt 10/10) | mới `components/ui/Chip.tsx` |
| 4 | SegmentedControl | 2 | mới `components/ui/SegmentedControl.tsx` |
| 5 | Link | 1 | mới `components/ui/TextLink.tsx` (export `TextLink`, tránh trùng `next/link`) |
| 6 | Toggle | 2 | mới `components/ui/ToggleButton.tsx` |
| 7 | TextField | 3 | mới `components/ui/TextField.tsx` |
| 8 | AddressField + MapPicker | 3 | mới `features/checkout/components/AddressField.tsx`, mới `features/checkout/components/AddressMapPicker.tsx` |
| 9 | Checkbox | 3 | mới `components/ui/Checkbox.tsx` |
| 10 | SearchBox + SearchSuggest | 1 (SearchBox) · 2 (Suggest) | mới `components/search/SearchBox.tsx`, `components/search/SearchSuggest.tsx` ⚠(lô 2) |
| 11 | FormErrorSummary | 3 | mới `components/ui/FormErrorSummary.tsx` |
| 12 | ProductCard | 1 (biến thể `rail`, `row`) · 2 (`grid`) | mới `components/catalog/ProductCard.tsx` ⚠(lô 2); thay phần thẻ trong `components/CatalogGrid.tsx` và `features/content/components/ItemCard.tsx` |
| 13 | StockBadge | 2 | mới `components/catalog/StockBadge.tsx` ⚠ |
| 14 | PriceTag | 1 | mới `components/catalog/PriceTag.tsx` |
| 15 | QtyStepper | 2 | mới `components/catalog/QtyStepper.tsx` ⚠; bỏ stepper trong `AddToCartControl.tsx` và `CheckoutScreen.tsx:178-260` |
| 16 | AddToCart | 2 | viết lại `components/AddToCartControl.tsx` thành `components/catalog/AddToCart.tsx` ⚠ |
| 17 | ImageFrame | 1 | viết lại `components/ItemImageFrame.tsx` thành `components/catalog/ImageFrame.tsx` (giữ logic `srcSet`/`sizes`/`onError`) |
| 18 | CategoryTile | 1 | mới `components/catalog/CategoryTile.tsx` |
| 19 | CartLine | 2 | mới `components/cart/CartLine.tsx` ⚠ (đổi tên type `CartLine` trong `CartContext.tsx` thành `CartEntry` để khỏi trùng) |
| 20 | CartSummary | 2 (giỏ) · 3 (đặt hàng) · 4 (thanh toán) | mới `components/cart/CartSummary.tsx` ⚠ |
| 21 | CartBar | 2 | mới `components/cart/CartBar.tsx` ⚠ |
| 22 | MiniCart | 2 | mới `components/cart/MiniCart.tsx` ⚠ |
| 23 | CheckoutSteps | 2 | mới `components/cart/CheckoutSteps.tsx` ⚠ |
| 24 | HoldCountdown | 4 | viết lại `components/CountdownTimer.tsx` thành `features/checkout/components/HoldCountdown.tsx` |
| 25 | PaymentMethod | 4 | mới `features/checkout/components/PaymentMethod.tsx`; thay `PaymentPanel.tsx` |
| 26 | OrderTimeline | 4 | mới `features/checkout/components/OrderTimeline.tsx` |
| 27 | OrderStatusBadge | 4 | mới `features/checkout/components/OrderStatusBadge.tsx` |
| 28 | OrderLines | 4 | mới `features/checkout/components/OrderLines.tsx` |
| 29 | SuccessBanner | 4 | mới `features/checkout/components/SuccessBanner.tsx`; gỡ khối tương ứng trong `OrderPaymentPanel.tsx` |
| 30 | ShopHeader | 1 | viết lại `components/ShopHeader.tsx` (+ `ShopHeader.module.css`) |
| 31 | BottomNav | 1 | mới `components/BottomNav.tsx` |
| 32 | ShopFooter | 1 | viết lại `components/ShopFooter.tsx`; gộp `features/site/components/SiteLegalFooter.tsx` |
| 33 | Breadcrumb | 2 | mới `components/ui/Breadcrumb.tsx` |
| 34 | SideFilter | 2 | mới `components/catalog/SideFilter.tsx` ⚠ |
| 35 | SortControl | 2 | mới `components/catalog/SortControl.tsx` ⚠ |
| 36 | PolicyNav | 5 | mới `features/site/components/PolicyNav.tsx` |
| 37 | LogoSlot | 1 | mới `components/LogoSlot.tsx` |
| 38 | Dialog | 1 | mới `components/ui/Dialog.tsx` (+ `useReturnFocus.ts`) |
| 39 | BottomSheet | 1 | mới `components/ui/Sheet.tsx` (export `BottomSheet`) |
| 40 | FullscreenSheet | 1 (dùng ở lô 3) | mới `components/ui/FullscreenSheet.tsx` |
| 41 | Dropdown/Popover | 1 | mới `components/ui/Popover.tsx` |
| 42 | Toast | 1 | mới `components/ui/Toast.tsx` (`ToastProvider`, `useToast`) |
| 43 | Banner/Alert | 1 | mới `components/ui/Banner.tsx` |
| 44 | EmptyState | 1 | mới `components/ui/EmptyState.tsx` |
| 45 | ErrorState | 1 | mới `components/ui/ErrorState.tsx` |
| 46 | Skeleton | 1 | mới `components/ui/Skeleton.tsx` (+ preset `ProductCardSkeleton`) |
| 47 | Spinner | 1 | mới `components/ui/Spinner.tsx` |

---

## Chỗ đã chuẩn hoá so với file màn

Dev code theo cột "Dùng". Khi QA so ảnh với file màn, các chỗ này **không phải lỗi**.

| Chỗ | File màn | Dùng | Lý do |
|---|---|---|---|
| Bo dialog máy tính | 16 | 14 (`--radius-xl`) | số chuẩn |
| Bo thẻ, section máy tính | 16 | 12 (`--radius-card`) | số chuẩn |
| Bóng dialog điện thoại | 0 16px 48px .24 | `--shadow-modal` | số chuẩn chỉ có 1 bóng modal |
| Bóng sheet, toast, menu con | nhiều giá trị | `--shadow-bar` (sheet), `--shadow-pop` (toast, dropdown, giỏ mini) | số chuẩn |
| Nút "Tìm" header máy tính | `accent`, hover `accent-hover` | `--brand-deep`, hover `--brand-deep-hover` | số chuẩn + điều phối viên chốt |
| Ô tìm, ô nhập máy tính | 15 px, bo 10 | giống điện thoại: cao 44, bo 8, chữ 16 (ô tìm header vẫn là pill 48 có nút "Tìm") | ô nhập 16 bắt buộc; điều phối viên chốt |
| Ô tra cứu (F1, F2) | cao 48 | 44 | `--h-input` |
| Tên SP + giá trang chi tiết máy tính | 28 / 30 | 24 / 24 | `display`, giá chi tiết 24 |
| H1 trang đơn máy tính | 26 | 24 | `display` |
| Tổng tiền chính (giỏ, đặt hàng, thanh toán, đơn) | 20 / 22 / 24 | 24/600 `accent-text` | một cỡ cho "số tiền chính" |
| Giá trên thẻ (lưới máy tính 18 `accent-text`; hàng cuộn trang chủ 16 `accent-text`, đặt sau ghi chú) | như trái | 17/600 `ink`; hàng cuộn: giá đặt **trước** ghi chú | điều phối viên chốt: giá thẻ màu `ink`, `accent-text` chỉ cho giá chi tiết và tổng tiền |
| Nhãn BottomNav | 11/500 | 12/500 (`caption`) | `micro` 11 chỉ cho badge số |
| Badge giỏ máy tính | 12/600 | 11/600 (`micro`) | badge số |
| Chữ phụ trên nền `accent` | `on-brand-muted` | `on-accent` (trắng) | tương phản AA |
| Placeholder | #8C8C98 | `--ink-3` | tương phản AA |
| Chip trên nền thương hiệu | rgba(255,255,255,.14) | nền `--accent-hover`, chữ trắng (6,8:1) | không hard-code rgba |
| Đường kẻ trong footer | rgba(255,255,255,.14) | `--accent-hover` | như trên |
| Link "Xem giỏ" trong toast | #A9C8F7 | `--on-brand-muted` | token có sẵn |
| "© 2026" footer | #A9C4EE | `--on-brand-muted`, năm lấy từ `currentYearInVietnam()` | token; không hard-code năm |
| Nền ô địa chỉ đã điền | #F5FAF6 | `--good-soft` | token |
| Viền khối tóm tắt lỗi (C2) và SuccessBanner máy tính | #F2C9C6, #BFE5CC | `--crit-border`, `--good-border` (token mới, điều phối viên chốt) | giữ như màn, đưa vào token |
| Viền banner lỗi/cảnh báo khác (D2, F2, B3, E4) | #F3CFCC, #F3DDB8… | không viền | `DESIGN.md`: alert chỉ nền `*-soft`; chỉ hai chỗ trên có token viền |
| Nhãn "Hết hàng" trên ảnh thẻ máy tính và A7 | `crit-soft`/`crit`; `surface-2` + viền | nền `--surface-3`, chữ `--ink-2`, không viền (điều phối viên chốt) | hết hàng không phải lỗi; đỏ chỉ cho lỗi |
| Hover thẻ sản phẩm máy tính | viền `border-strong` + 0 6px 20px .06 | giữ như màn: `--border-strong` + `--shadow-card-hover` | điều phối viên chốt |
| Nút thêm trên thẻ máy tính, stepper máy tính | pill 22, bo 10 | bo 8 cả hai khổ | số chuẩn (stepper 8); nút và stepper cùng hình để đổi mượt |
| Stepper trang chi tiết máy tính | cao 48 | 44 | số chuẩn |
| Nút "Chọn mua" thẻ trang chủ | cao 40 | **giữ 40** pill (điều phối viên chốt), vùng chạm mở rộng tới 44 bằng `::before` `inset: -2px 0` | kiểu Long Châu |
| Nút trừ của stepper ở mức tối thiểu (thẻ, giỏ) | icon "−" | icon thùng rác, bấm mở Dialog B2 | điều phối viên chốt |
| Nút xoá dòng giỏ (B1), nút đóng banner (E1), nút xoá chữ ô bản đồ | 36 / 36 / 32 | 44 | vùng chạm |
| Link trong khối tóm tắt lỗi, link footer | min-height 32 / 40 | 44 (điện thoại), 40 (máy tính) | vùng chạm |
| Menu "Chính sách" máy tính | `<button>` | `<a>` + `aria-current="page"` | là điều hướng |
| Gợi ý tìm kiếm điện thoại | `role="region"` + link | combobox + listbox như bản máy tính | một mẫu truy cập cho cả hai khổ |
| Header H2 máy tính (Giỏ, Đặt hàng, Thanh toán) | `DesktopCart` nền xanh cao 72; đặc tả nền trắng cao 68 | theo đặc tả `HeaderFooter-Desktop` (nền trắng), cao 76 | đặc tả link là nguồn; số chuẩn tầng chính ~76 |
| Logo trang chủ điện thoại | trỏ `Landing` | trỏ `/` ("Cá Về — trang chủ") | theo `HeaderFooter-Mobile` |
| Thẻ ở danh mục điện thoại: bớt dưới 1 kg | tự bỏ món | mở Dialog bỏ món | UI-RULES §1.2 |
| Dòng "Combo … · 1" ở Payment | "· 1" | "· 1 combo" | đơn vị luôn hiện |
| Chữ "/kg" trong gợi ý tìm | "/kg" | "/ kg" | một cách viết |
| Số đồng hồ giữ hàng | 40 (điện thoại), 44 (máy tính) | 40 cả hai khổ | số chuẩn chưa có cỡ này, xem Q-UX-3 |

---

## Điểm cần chốt trước khi code

Câu đã mở sẵn trong `PLAN.md` (Q2, Q4, Q6, Q7, Q8, Q9, bước 0,5 kg) **đã được Duy trả lời 10/10** (xem `PLAN.md` mục Điều kiện đầu vào). Câu mới từ tài liệu này:

| Mã | Câu hỏi | Mặc định nếu chưa trả lời |
|---|---|---|
| Q-UX-1 | Shop có dark mode ngay V1 không? Nếu có, cần giá trị dark cho `brand-deep`, `on-brand-muted`, `overlay*`, `shadow-*`. | V1 chỉ light; chặn `prefers-color-scheme: dark` bằng `color-scheme: light` |
| Q-UX-2 | Icon Shop dùng bộ SVG nét như thiết kế, hay Material Symbols như ERP? | SVG như thiết kế, gom ở `Icon.tsx` |
| Q-UX-3 | Thêm cỡ "số đồng hồ" 40/600 vào `SO-CHUAN.md`? | dùng 40/600 |
| Q-UX-4 | Nút "Đặt hàng" khi chưa tick đồng ý: màn C1 vẽ nút **tắt** + dòng nhắc; `DESIGN.md` cấm tắt nút vì thiếu ô. | Nút **luôn bấm được**; bấm khi chưa tick thì hiện lỗi ở ô đồng ý và trong FormErrorSummary |
| Q-UX-5 | BottomNav ở F1/F2 (tra cứu đơn): màn vẽ có, UI-RULES §4.5 không liệt kê. | ĐÃ CHỐT (Duy 10/10, D9): hiện ở tra cứu đơn (tab "Đơn hàng" đang chọn); UI-RULES §4.5 đã sửa |
| Q-UX-6 | Danh mục điện thoại có cả CartBar (A2) và BottomNav (A0). | Có món trong giỏ: CartBar nằm **trên** BottomNav; giỏ trống: chỉ BottomNav |
| Q-UX-7 | ĐÃ CHỐT (điều phối, 07/10): câu A7 đổi thành "Món này đang hết. Liên hệ để hỏi khi nào có hàng." | — |

**Cho `techlead` (contract UI cần):**
- Thời lượng giữ hàng để vẽ thanh tiến độ (`hold_minutes` hoặc `booked_at`) và giờ máy chủ (`server_now`) để đồng hồ không lệch giờ máy khách. Câu "30 phút" trên màn lấy từ field này, không hard-code.
- Bảng trạng thái đơn hiển thị (enum → nhãn) cho OrderStatusBadge và OrderTimeline; mốc `placed_at`, `paid_at`, `delivered_at` (BE-5).
- Tên biến môi trường Maps: `HUONG-DAN-CODE.md` ghi `NEXT_PUBLIC_GOOGLE_MAPS_KEY`, `DOI-CHIEU-CODE.md` ghi `NEXT_PUBLIC_GOOGLE_MAPS_KEY`. Chốt một tên ở 02b.
- `site-info.seller.zalo`, `return_report_hours` (BE-7; **không** `search_chips`, chốt 10/10); nhóm có `parent_slug` (L-20) cho menu con máy tính.
- Lỗi hết hàng có cấu trúc `lines[].stock_level: 'out' | 'short'` (BE-3) cho popup C3.

---

# A. Điều khiển cơ bản

## 1. Button

1. **Công dụng.** Nút hành động cho mọi thao tác chính, phụ và phá huỷ. **Dùng ở:** mọi màn; mẫu rõ nhất ở `Cart`, `Checkout`, `Payment`, `B2-RemoveConfirm`, `DesktopRemoveConfirm`, `C4-NetworkError`.
2. **Giải phẫu.** (a) icon đầu, tuỳ chọn · (b) nhãn · (c) icon cuối, tuỳ chọn · (d) Spinner khi đang gửi (thay icon đầu).
3. **Biến thể.**

| `variant` | Khi nào | Ví dụ trên màn |
|---|---|---|
| `primary` | hành động chính, **một nút mỗi vùng** | "Đặt hàng", "Thanh toán", "Chọn mua", "Thử lại" |
| `outline` | hành động phụ cùng cấp với nút chính | "Thêm vào giỏ", "Thêm 1 kg", "Tra cứu đơn", "Gọi Cá Về" |
| `secondary` | lựa chọn trung tính, huỷ bước | "Giữ lại", "Liên hệ chúng tôi", "Quay lại giỏ hàng", "Rời trang" |
| `ghost` | lối thoát nhẹ | "Để sau", "Nhập tay" |
| `danger` | xác nhận phá huỷ (bước cuối) | "Bỏ khỏi giỏ" trong dialog |
| `danger-text` | phá huỷ ngay trong dòng, chưa phải bước cuối | "Bỏ khỏi giỏ" ở dòng món đã hết (B3) |
| `on-brand` | nút trên nền `brand-deep` | "Gọi [hotline]" footer, "Xem hàng" banner |
| `on-brand-outline` | nút phụ trên nền `brand-deep` | "Nhắn Zalo" footer |

`size`: `lg` 48 (CTA chính, thanh đáy, dialog dạng xếp dọc) · `md` 44 (mặc định) · `sm` 36 (**chỉ ≥ md**, thanh phụ như sắp xếp).
`shape`: `pill` (999) cho CTA `lg`; `rounded` (8) cho còn lại.

4. **Kích thước và khoảng cách.**

| | Điện thoại | Máy tính |
|---|---|---|
| Cao | lg 48 · md 44 | lg 48 · md 44 · sm 36 |
| Đệm ngang | lg 0 24 · md 0 16 | lg 0 24 · md 0 16 · sm 0 14 |
| Khoảng icon–chữ | 8 | 8 |
| Icon | 16–18 | 16–18 |
| Bề rộng | CTA thanh đáy `fullWidth`; hai nút cạnh nhau chia lưới 2 cột, gap 10 → 12 (`--space-3`) | theo nội dung, CTA trong khung tóm tắt `fullWidth` |

5. **Token.** Chữ 14/600 ở cả hai khổ (file máy tính dùng 15/600 cho `lg`; thống nhất về 14/600), `tabular-nums` nếu có số.

| Biến thể | Nền | Chữ/icon | Viền |
|---|---|---|---|
| primary | `--accent` #1F66D1 | `--on-accent` #FFFFFF | không |
| outline | `--surface` #FFFFFF | `--accent-text` #1A5BC0 | 1px `--accent` |
| secondary | `--surface` | `--ink` #17171C | 1px `--border-strong` #D4D4DB |
| ghost | trong suốt | `--ink-2` #4E4E58 | không |
| danger | `--crit` #C0312B | `--on-crit` #FFFFFF | không |
| danger-text | `--surface` | `--crit` | 1px `--border-strong` |
| on-brand | `--surface` | `--brand-deep` #0E3A73 | không |
| on-brand-outline | trong suốt | `--on-accent` | 1px `--on-brand-muted` #D6E4FA |

Bo `--radius-md` 8 hoặc `--radius-full`. Không bóng.

6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | như bảng token |
| hover (chỉ `hover:hover`) | primary → nền `--accent-hover` #1A57B5 · outline → nền `--accent-soft` · secondary, ghost → nền `--surface-2` · danger → `--crit-hover` #A82823 · danger-text → nền `--crit-soft` · on-brand → nền `--accent-soft` · on-brand-outline → nền `--brand-deep-hover`; 150ms |
| nhấn | `scale(.97)` 120ms `--ease-out` |
| focus-visible | viền 2px `--focus`, offset 2; trên nền `accent`/`brand-deep`: viền trắng offset −4 |
| disabled | nền `--surface-3` #EBEBEF, chữ `--ink-3` #686874, không viền, `cursor: not-allowed`, không scale. **Chỉ dùng** khi đang gửi hoặc đơn hết hạn (D4); luôn có chữ giải thích gần nút |
| đang tải | `aria-busy="true"`, `disabled`, Spinner 18 thay icon đầu, nhãn đổi theo `loadingText` ("Đang đặt…"); giữ nguyên nền (không giảm opacity như file C4) và giữ bề rộng tối thiểu để nút không co |
| lỗi | nút không đổi; lỗi hiện ở Banner/FormErrorSummary cạnh nút |
| chọn | không áp dụng (dùng Toggle) |

7. **Hành vi.** Bấm đúp bị chặn khi `loading`. `href` có giá trị thì render `<a>` (qua `next/link` nếu là route nội bộ), không lồng `<button>` trong `<a>`. `type` mặc định `"button"` để khỏi submit nhầm form. `tel:` và link ngoài dùng biến thể Link hoặc Button có `href`.
8. **Props (TypeScript).**

```ts
type ButtonVariant = 'primary' | 'outline' | 'secondary' | 'ghost' | 'danger' | 'danger-text' | 'on-brand' | 'on-brand-outline';
interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'type'> {
  variant?: ButtonVariant;          // 'primary'
  size?: 'lg' | 'md' | 'sm';        // 'md'
  shape?: 'rounded' | 'pill';       // 'rounded' (lg mặc định 'pill')
  type?: 'button' | 'submit';       // 'button'
  loading?: boolean;                // false
  loadingText?: string;             // undefined: giữ nhãn cũ
  iconStart?: React.ReactNode;
  iconEnd?: React.ReactNode;
  fullWidth?: boolean;              // false
  href?: string;                    // có thì render <a>
  external?: boolean;               // false; true: target="_blank" rel="noopener"
}
```

9. **Truy cập.** Dùng `<button>`/`<a>` gốc. Nhãn chữ là tên truy cập; icon `aria-hidden`. Khi `loading`, nhãn hiện "Đang …" để trình đọc màn hình biết. Disabled phải đi kèm lý do hiển thị (vd. D4 "Hết thời gian giữ hàng").
10. **Câu chữ.** Động từ rõ: "Thêm 1 kg", "Xem giỏ", "Đặt hàng", "Thanh toán lại", "Liên hệ chúng tôi", "Tiếp tục: nhập thông tin nhận hàng", "Giữ lại", "Bỏ khỏi giỏ", "Thử lại", "Để sau".
11. **Không được.** Hai nút `primary` cạnh nhau. Tắt nút vì thiếu ô (Q-UX-4). Dùng `danger` cho hành động không phá huỷ. Đặt `transition: all`. Dùng `<div onClick>`.
12. **Code.** Mới `frontend/components/ui/Button.tsx` + `Button.module.css`. Thay các lớp `.btn .btn-primary` trong `globals.css` dần theo lô.

## 2. IconButton

1. **Công dụng.** Nút chỉ có icon: quay lại, giỏ, gọi, tra đơn, đóng, xoá. **Dùng ở:** `HeaderFooter-Mobile` (H1–H4), `Cart` (xoá dòng), `A5-NotFound` (xoá từ khoá), `Success` (đóng banner), `DesktopRemoveConfirm` (X).
2. **Giải phẫu.** (a) vùng bấm vuông · (b) icon · (c) `CartBadge` tuỳ chọn ở góc trên phải.
3. **Biến thể.** `ghost` (nền sáng, mặc định) · `on-brand` (icon trắng trên header `accent`) · `close` (X trong dialog/banner, tròn) · `danger-ghost` (xoá dòng giỏ máy tính).
4. **Kích thước và khoảng cách.** Vùng bấm 44×44 cả hai khổ. Icon 20–22 (header), 18 (xoá dòng), 16–20 (đóng). `CartBadge`: cao 18 (điện thoại) / 20 (máy tính), `min-width` bằng cao, đệm ngang 5–6, đặt `top: 2px; right: 0`.
5. **Token.** Icon `--ink`; `on-brand` icon `--on-accent`; xoá dòng icon `--ink-3`. Bo `--radius-md` (ghost), `--radius-full` (close). Badge: bo `--radius-full`, chữ `micro` 11/600 `tabular-nums`; trên header trắng nền `--accent` chữ `--on-accent`; trên header `accent` nền `--surface` chữ `--accent-text`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | nền trong suốt |
| hover | ghost/close → nền `--surface-2`; on-brand → nền `--accent-hover`; danger-ghost → nền `--crit-soft`, icon `--crit` |
| nhấn | `scale(.97)` |
| focus-visible | viền 2px `--focus` offset 2; on-brand: viền trắng offset −4 |
| disabled | icon `--ink-3`, không phản hồi |
| đang tải / lỗi / chọn | không áp dụng |

Badge đổi số: hiện bằng fade + `scale(.96→1)` 180ms `--ease-out`.
7. **Hành vi.** Badge giỏ là **số món** (số dòng trong giỏ), không phải tổng kg. Ẩn badge khi 0. Nút quay lại trang con gọi `history.back()`; nếu không có lịch sử (vào từ link chia sẻ) thì đi `/shop/`. Ở bước đặt hàng, quay lại luôn về `/shop/cart/`.
8. **Props.**

```ts
interface IconButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'type' | 'aria-label'> {
  label: string;                    // bắt buộc, thành aria-label
  icon: IconName;
  variant?: 'ghost' | 'on-brand' | 'close' | 'danger-ghost';  // 'ghost'
  href?: string;                    // có thì render <a>
  badgeCount?: number;              // undefined: không badge; 0: ẩn badge
}
```

9. **Truy cập.** `aria-label` bắt buộc, ghi rõ đối tượng: "Bỏ Cá thu cắt khúc khỏi giỏ", "Đóng thông báo", "Xoá từ khoá". Giỏ: `aria-label="Giỏ hàng, 3 món"` (0 món: "Giỏ hàng"); badge `aria-hidden` vì số đã nằm trong nhãn.
10. **Câu chữ.** "Cá Về — trang chủ", "Gọi hotline Cá Về", "Tra cứu đơn hàng", "Giỏ hàng, N món", "Quay lại", "Quay lại giỏ hàng", "Tìm sản phẩm", "Đóng".
11. **Không được.** Vùng bấm < 44. Thiếu `aria-label`. Badge hiện tổng kg. Badge hiện "0".
12. **Code.** Mới `frontend/components/ui/IconButton.tsx` (export thêm `CartBadge`).

## 3. Chip

1. **Công dụng.** Viên nhỏ để lọc nhóm hàng, gợi ý từ khoá, tìm gần đây. **Dùng ở:** `Main`, `A4-Toast`, `A5-NotFound`, `A6-Offline` (lọc), `A8-SearchSuggest` (tìm gần đây), `G1-KitchenList` (lọc chuyên mục). **Bỏ dải chip "Tìm nhiều"** ở `Home`/`HeaderFooter-Mobile` (chốt 10/10): biến thể `on-brand` không dùng ở V1.
2. **Giải phẫu.** (a) icon đầu tuỳ chọn (đồng hồ ở "tìm gần đây") · (b) nhãn.
3. **Biến thể.**

| `variant` | Phần tử | Khi nào |
|---|---|---|
| `filter` | `<a>` có `aria-current` (đổi URL) hoặc `<button aria-pressed>` (lọc tại chỗ) | hàng nhóm hàng ở danh mục, chuyên mục Góc bếp |
| `link` | `<a>` | gợi ý nhóm ở trạng thái rỗng, tìm gần đây |
| ~~`on-brand`~~ | `<a>` | ~~"Tìm nhiều" trên header trang chủ~~ — bỏ (chốt 10/10), không code |

4. **Kích thước và khoảng cách.**

| | filter | link | on-brand |
|---|---|---|---|
| Cao hiển thị | 40 | 44 | 32 |
| Vùng chạm | 44 (giả `::before` `inset: -2px 0`) | 44 | 44 (`::before` `inset: -6px 0`) |
| Đệm ngang | 0 14 | 0 18 (gợi ý) · 0 14 (gần đây) | 0 12 |
| Khoảng cách giữa chip | 8 | 8 | 8 |

Hàng chip điện thoại cuộn ngang, đệm `12 16`, ẩn thanh cuộn, mép phải mờ dần bằng `mask-image` (chỉ hình, không chữ).
5. **Token.** Bo `--radius-full`. Chữ `label` 13/500 (link gợi ý dùng 14/500).
filter tắt: nền `--surface`, chữ `--ink-2`, viền 1px `--border-strong`. filter bật: nền `--accent`, chữ `--on-accent`, viền `--accent`.
link: nền `--surface`, chữ `--ink`, viền `--border-strong`, icon `--ink-3`.
on-brand: nền `--accent-hover` #1A57B5, chữ `--on-accent`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | filter tắt, link → nền `--surface-2`; on-brand → nền `--brand-deep` |
| nhấn | `scale(.97)` |
| focus-visible | viền 2px `--focus` offset 2; on-brand: viền trắng |
| chọn | filter bật như token; `aria-current="page"` hoặc `aria-pressed="true"` |
| disabled / đang tải / lỗi | không áp dụng; khi danh mục đang tải, hàng chip là Skeleton |

7. **Hành vi.** Chip nhóm trên danh mục đổi URL `/shop/?group=<slug>` (combo: `?type=combo`), nên dùng `<a>` + `aria-current="page"` để nút Back hoạt động. Không có chip "Tìm nhiều" và không có `search_chips` (chốt 10/10). Chip "tìm gần đây" mở `/shop/?q=`.
8. **Props.**

```ts
interface ChipProps {
  label: string;
  variant?: 'filter' | 'link';                // 'filter' ('on-brand' bỏ cùng chip "Tìm nhiều", chốt 10/10)
  href?: string;                              // có: <a>
  selected?: boolean;                         // false (filter)
  onClick?: () => void;                       // filter tại chỗ (không href)
  icon?: IconName;
}
```

9. **Truy cập.** Hàng chip lọc bọc `<nav aria-label="Danh mục">`. Không dùng `tabindex` > 0. Trạng thái chọn có cả màu lẫn thuộc tính ARIA.
10. **Câu chữ.** "Tất cả", "Cá", "Tôm", "Mực", "Cua ghẹ", "Combo" (tên nhóm lấy từ catalog).11. **Không được.** Chip filter cao < 40 hoặc không có vùng chạm 44. Dùng chip để chạy hành động phá huỷ. Ghi số kg trong chip.
12. **Code.** Mới `frontend/components/ui/Chip.tsx`.

## 4. SegmentedControl

1. **Công dụng.** Chọn một trong vài giá trị ngang hàng, hiện tất cả cùng lúc. **Dùng ở:** `DesktopCategory` (sắp xếp: Mặc định / Giá thấp đến cao / Giá cao đến thấp). Điện thoại dùng SortControl dạng sheet.
2. **Giải phẫu.** (a) nhãn nhóm "Sắp xếp" (hiện chữ, `aria-hidden` nếu đã có `legend`) · (b) các ô lựa chọn.
3. **Biến thể.** Chỉ `pills` (ô tách rời, bo tròn), vì màn hiện có chỉ dùng dạng này.
4. **Kích thước và khoảng cách.** Máy tính: ô cao 36 (`sm`), đệm 0 14, khoảng 6, nhãn nhóm cách ô đầu 4. Không dùng trên điện thoại.
5. **Token.** Bo `--radius-full`. Chữ `label` 13/500. Tắt: nền `--surface`, chữ `--ink-2`, viền 1px `--border-strong`. Bật: nền `--accent`, chữ `--on-accent`, viền `--accent`, bóng `--shadow-sm`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | ô tắt → nền `--surface-2` |
| nhấn | `scale(.97)` |
| focus-visible | viền 2px `--focus` offset 2 quanh ô đang focus |
| chọn | như token "bật" |
| disabled | chữ `--ink-3`, không phản hồi (chưa có màn nào cần) |
| đang tải / lỗi | không áp dụng |

7. **Hành vi.** Đổi giá trị cập nhật URL `?sort=` (`default` · `price_asc` · `price_desc`) và sắp xếp tại chỗ. Món hết hàng **luôn xếp cuối**, bất kể thứ tự đang chọn.
8. **Props.**

```ts
interface SegmentedControlProps<T extends string> {
  legend: string;                              // "Sắp xếp"
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  name: string;                                // cho nhóm radio
}
```

9. **Truy cập.** Dựng bằng `<fieldset>` + `<legend>` + `<input type="radio">` ẩn bằng CSS, nhãn là `<label>` hiển thị như ô. Trình duyệt tự lo phím ← → và đọc "đã chọn". Không dùng `aria-pressed` như file màn.
10. **Câu chữ.** "Sắp xếp", "Mặc định", "Giá thấp đến cao", "Giá cao đến thấp".
11. **Không được.** Hơn 4 lựa chọn. Dùng cho thao tác bật/tắt độc lập (dùng Toggle).
12. **Code.** Mới `frontend/components/ui/SegmentedControl.tsx`.

## 5. Link

1. **Công dụng.** Liên kết chữ: trong đoạn văn, điều hướng phụ, `tel:`, `mailto:`, Zalo. **Dùng ở:** `Checkout` (chính sách quyền riêng tư), `Home` ("Xem tất cả"), `F2-LookupNotFound` (hotline trong lỗi), `P1-Policy`, `HeaderFooter-*` (footer, dải trên).
2. **Giải phẫu.** (a) chữ · (b) icon cuối tuỳ chọn (mũi tên, mở tab mới).
3. **Biến thể.** `inline` (trong câu) · `standalone` ("Xem tất cả", "Mua thêm hàng khác") · `nav` (breadcrumb, menu) · `on-brand` (footer, dải trên) · `danger-inline` (link trong khối lỗi).
4. **Kích thước và khoảng cách.** `inline` theo dòng chữ. `standalone`, `nav`, `on-brand`: `min-height` 44 (điện thoại), 40 (máy tính), căn giữa dọc. Icon 16, cách chữ 6.
5. **Token.** inline/standalone: chữ `--accent-text` #1A5BC0, hover `--accent-hover`. nav: `--ink-2`, hover `--accent-text`. on-brand: `--on-brand-muted` trên `brand-deep`, hover `--on-accent`; trên nền `accent`: `--on-accent`. danger-inline: `--crit`, 600. Chữ theo ngữ cảnh (body/label/caption).
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | inline luôn gạch chân (`text-underline-offset: 2px`) để không phân biệt chỉ bằng màu; các biến thể khác không gạch |
| hover | đổi màu như token + gạch chân; 150ms |
| nhấn | standalone: `scale(.97)`; inline: không |
| focus-visible | viền 2px `--focus` offset 2; on-brand: viền trắng |
| chọn | `aria-current="page"`: chữ `--ink` 500 (breadcrumb) hoặc `--accent-text` 600 (menu) |
| disabled / đang tải / lỗi | không áp dụng |

7. **Hành vi.** Route nội bộ qua `next/link`. Link ngoài (Zalo, logo Bộ Công Thương) và link chính sách ở bước đặt hàng (F2) mở tab mới: `target="_blank" rel="noopener"`. `tel:` hiện cả số trên máy tính (máy tính không gọi được, L-30).
8. **Props.**

```ts
interface TextLinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  href: string;
  variant?: 'inline' | 'standalone' | 'nav' | 'on-brand' | 'danger-inline';  // 'inline'
  external?: boolean;          // false
  current?: boolean;           // false -> aria-current="page"
  iconEnd?: IconName;
}
```

9. **Truy cập.** Chữ link có nghĩa khi đứng một mình. Link mở tab mới thêm chữ ẩn " (mở tab mới)". Không dùng link cho hành động không điều hướng (dùng Button).
10. **Câu chữ.** "chính sách quyền riêng tư", "Xem tất cả", "Mua thêm hàng khác", "Cách mua hàng", "Về Cá Về".
11. **Không được.** "Bấm vào đây". Link inline không gạch chân. Đưa SĐT khách hoặc mã tra cứu vào `href`.
12. **Code.** Mới `frontend/components/ui/TextLink.tsx`.

## 6. Toggle

1. **Công dụng.** Nút bật/tắt dạng ô: chọn nhanh số kg, chọn ảnh trong thư viện. **Dùng ở:** `Product`, `DesktopProduct` (ô 1 kg / 1,5 kg / 2 kg / 3 kg; ảnh nhỏ). Không có công tắc (switch) trên màn nào; **không dựng switch**.
2. **Giải phẫu.** (a) ô · (b) nhãn hoặc ảnh nhỏ.
3. **Biến thể.** `preset` (ô chữ, chọn số kg) · `thumb` (ảnh nhỏ).
4. **Kích thước và khoảng cách.** preset: cao 44, lưới 4 cột đều, gap 8 (máy tính 12). thumb: 56×56 (điện thoại, hàng ngang gap 8); máy tính lưới 4 cột tỉ lệ 1:1, gap 12.
5. **Token.** Bo `--radius-md`. preset tắt: nền `--surface`, chữ `--ink` 14/600 `tabular-nums`, viền 1px `--border-strong`. preset bật: nền `--accent-soft`, chữ `--accent-text`, viền 2px `--accent`. thumb tắt: viền 1px `--border`; bật: viền 2px `--accent`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | tắt → nền `--surface-2` (preset), viền `--border-strong` (thumb) |
| nhấn | `scale(.97)` |
| focus-visible | viền 2px `--focus` offset 2 |
| chọn | như token "bật"; `aria-pressed="true"` |
| disabled | chữ `--ink-3` (khi món hết hàng thì cả khối chọn kg không hiện, xem A7) |
| đang tải / lỗi | không áp dụng |

7. **Hành vi.** Ô preset sinh từ dữ liệu, không hard-code: `[min, min+step, min+2·step, min+4·step]` (với `min_qty` 1 và `qty_step` 0,5 ra đúng 1 · 1,5 · 2 · 3 như màn). Bấm preset đặt QtyStepper về giá trị đó. QtyStepper đổi tới giá trị không có trong preset thì không ô nào bật. Combo không có preset. Thumb đổi ảnh lớn; chỉ có 1 ảnh thì ẩn cả hàng thumb (L-22).
8. **Props.**

```ts
interface ToggleButtonProps {
  pressed: boolean;
  onPressedChange: (pressed: boolean) => void;
  label: string;                // preset: "1,5 kg"; thumb: "Ảnh 2 trên 3"
  variant?: 'preset' | 'thumb'; // 'preset'
  imageSrc?: string;            // thumb
}
```

9. **Truy cập.** `<button aria-pressed>`. Nhóm preset bọc `role="group"` có `aria-labelledby` trỏ tiêu đề "Chọn số kg".
10. **Câu chữ.** "Chọn số kg", "1 kg", "1,5 kg", "2 kg", "3 kg" (dấu phẩy thập phân kiểu Việt).
11. **Không được.** Preset vượt tồn hay gợi ý số kg còn lại. Dựng switch. Dùng dấu chấm thập phân "1.5 kg".
12. **Code.** Mới `frontend/components/ui/ToggleButton.tsx`.

## 7. TextField

1. **Công dụng.** Ô nhập một dòng hoặc nhiều dòng có nhãn, gợi ý và lỗi. **Dùng ở:** `Checkout`, `C2-Invalid`, `DesktopCheckout`, `DesktopInvalid`, `F1-Lookup`, `F2-LookupNotFound`, `Success` (tra đơn khác).
2. **Giải phẫu.** (a) nhãn trên ô · (b) ô (`input` hoặc `textarea`) · (c) khe cuối ô (`endSlot`, vd. nút Bản đồ) · (d) dòng gợi ý · (e) dòng lỗi có icon.
3. **Biến thể.** `text` · `tel` · `multiline` (textarea 2 dòng). Ô tra đơn mã: `autocapitalize="characters"`, `spellcheck={false}`.
4. **Kích thước và khoảng cách.** Ô cao 44 (textarea 2 dòng ≈ 64), đệm 0 12 (textarea 10 12), bo 8, chữ 16 — **máy tính giống hệt điện thoại**. Nhãn cách ô 6. Ô cách dòng gợi ý/lỗi 6. Các field trong một khối cách nhau 16 (`--space-4`; file màn ghi 14).
5. **Token.** Nhãn `label` 13/500 `--ink-2`. Chữ trong ô **16/400** `--ink`. Placeholder `--ink-3`. Nền `--surface`. Viền 1px `--border-input` #8C8C98. Bo `--radius-md`. Gợi ý `caption` 12/500 `--ink-3`. Lỗi `caption` 12/500 `--crit` + icon 14.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | như token |
| hover | không đổi (ô nhập không cần hover) |
| focus-visible | viền `--accent` + `box-shadow: 0 0 0 3px var(--accent-soft)`, 150ms |
| disabled | nền `--surface-2`, chữ `--ink-3` (khi form đang gửi: dùng `readOnly`, không `disabled`, để dữ liệu vẫn đọc được) |
| đang tải | không áp dụng |
| lỗi | viền `--crit`; focus: viền `--crit` + vòng 3px `--crit-soft`; `aria-invalid="true"`; dòng lỗi hiện dưới ô thay dòng gợi ý |
| chọn | không áp dụng |

7. **Hành vi.** Kiểm khi rời ô (`blur`) và khi bấm gửi; không báo lỗi khi người dùng đang gõ lần đầu. Sửa đúng thì lỗi tắt ngay khi gõ. Luật SĐT theo câu trên màn ("10 chữ số, bắt đầu bằng 0"), luật thật chờ chốt L-19; FE và BE dùng cùng một luật. Bỏ khoảng trắng hai đầu trước khi gửi. Giá trị form **không** lưu `localStorage`/URL; giữ trong state để lỗi mạng (C4) không mất dữ liệu.
8. **Props.**

```ts
interface TextFieldProps {
  id: string;
  name: string;                            // 'name' | 'phone' | 'delivery_address' | 'order_code'
  label: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  type?: 'text' | 'tel';                   // 'text'
  multiline?: boolean;                     // false
  rows?: number;                           // 2
  placeholder?: string;
  hint?: string;
  error?: string;                          // có: aria-invalid + dòng lỗi
  required?: boolean;                      // false
  autoComplete?: string;                   // 'name' | 'tel' | 'street-address' | 'off'
  inputMode?: 'text' | 'tel' | 'numeric';
  readOnly?: boolean;                      // false
  endSlot?: React.ReactNode;
}
```

9. **Truy cập.** `<label for>` thật. `aria-describedby` trỏ cả gợi ý lẫn lỗi. `required` để trình đọc báo "bắt buộc". Lỗi không chỉ bằng màu (có icon và chữ).
10. **Câu chữ.** Nhãn: "Họ và tên", "Số điện thoại", "Địa chỉ giao hàng", "Mã đơn", "Số điện thoại đặt hàng". Placeholder: "Nguyễn Văn A", "09xx xxx xxx", "SO…". Gợi ý: "Mã đơn hiện ngay sau khi bạn đặt hàng, bắt đầu bằng SO". Lỗi: "Nhập họ tên người nhận", "Số điện thoại cần 10 chữ số, bắt đầu bằng 0".
11. **Không được.** Chữ ô < 16 px. Placeholder thay nhãn. Lỗi chung chung ("Không hợp lệ"). Chặn dán. Ghi giá trị ô vào log. Ở form tra đơn, **không** gắn `aria-invalid` cho từng ô khi không tìm thấy đơn (UI-RULES §3.2).
12. **Code.** Mới `frontend/components/ui/TextField.tsx`; thay các ô trong `CheckoutScreen.tsx:262-345` và `app/shop/orders/OrderLookup.tsx`.

## 8. AddressField + MapPicker

1. **Công dụng.** Một ô địa chỉ giao hàng (gõ tay được) cộng nút "Bản đồ" mở Google Maps để tìm, ghim rồi tự điền chuỗi địa chỉ. **Dùng ở:** `Checkout`, `C1b-MapPicker`, `C1c-AddressFilled`, `C2-Invalid`, `C5-LocationDenied`, `DesktopCheckout`, `DesktopMapPicker`.
2. **Giải phẫu.**
   - AddressField: (a) tiêu đề khối là `<label>` "Địa chỉ giao hàng" · (b) Banner thành công tuỳ chọn · (c) khung chứa textarea 2 dòng + nút "Bản đồ" bên phải · (d) gợi ý "Thêm hẻm, tầng, toà nhà nếu có." hoặc dòng lỗi.
   - MapPicker (trong FullscreenSheet): (a) thanh đầu: nút đóng X + tiêu đề · (b) ô tìm địa chỉ (combobox) + danh sách gợi ý · (c) vùng bản đồ: ghim giữa có nhãn "Giao tới đây" (**không** có nút "Vị trí của tôi", chốt 10/10, BR-BH-29) · (b2) dòng thông báo Google ngay dưới ô tìm, hiện ngay khi sheet mở · (d) chân: địa chỉ đang chọn + nút "Xác nhận vị trí này".
3. **Biến thể.** AddressField: `empty` · `filled-from-map` (C1c) · `error` (C2). MapPicker: điện thoại là FullscreenSheet; máy tính là hộp thoại lớn.
4. **Kích thước và khoảng cách.**

| Phần | Điện thoại | Máy tính |
|---|---|---|
| Khung ô | textarea 2 dòng (≈64), đệm 10 12; nút Bản đồ rộng 64, cao bằng khung | như điện thoại |
| MapPicker | sheet cách mép trên 24, mép trên bo 16; đầu 56; ô tìm 44 (đệm 12 16 8); chân đệm 14 16 16 + safe-area | hộp thoại `min(960px, 100vw - 48px)` × `min(640px, 100dvh - 48px)`, bo 14 |
| Dòng gợi ý địa chỉ | đệm 10 12, icon 18, gap 10 | như điện thoại |
| Dòng thông báo Google | chữ `caption` 12–13, đệm 0 16 8, ngay dưới ô tìm | như điện thoại |
| CTA xác nhận | `lg` 48 pill, rộng đầy | như điện thoại |

5. **Token.** Khung: viền 1px `--border-input`, bo `--radius-md`, nền `--surface`. Nút Bản đồ: nền `--accent-soft`, chữ `caption` 12/600 `--accent-text`, icon 20 `--accent-text`, viền trái 1px `--border`. Đã điền: viền `--good`, nền `--good-soft`, Banner `success`. Danh sách gợi ý: nền `--surface`, viền `--border`, bo `--radius-lg`, bóng `--shadow-pop`; dòng đang chọn nền `--accent-soft`; dòng 1 14/600, dòng 2 `caption` `--ink-2`. Nhãn "Giao tới đây": nền `--ink`, chữ `--on-accent` 12/500, bo `--radius-sm`. Ghim `--accent`. Dòng thông báo Google: chữ `--ink-2`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | khung `--border-input` |
| hover | nút Bản đồ: nền giữ `--accent-soft`, chữ và icon → `--accent-hover`; dòng gợi ý địa chỉ → nền `--surface-2` |
| nhấn | nút Bản đồ, CTA: `scale(.97)` |
| focus-visible | khung `:focus-within`: viền `--accent` + vòng 3px `--accent-soft`; nút Bản đồ: viền 2px `--focus` |
| disabled | khi form đang gửi: textarea `readOnly`, nút Bản đồ ẩn tương tác (`disabled`) |
| đang tải | bấm "Bản đồ": sheet mở ngay, vùng bản đồ là Skeleton + Spinner (chữ ẩn "Đang tải bản đồ") trong lúc nạp script; dòng thông báo Google đã hiện từ lúc này |
| lỗi | ô trống khi gửi: viền `--crit` + "Nhập địa chỉ giao hàng hoặc chọn trên bản đồ". Bản đồ nạp lỗi: Dialog C5 |
| chọn | sau khi xác nhận: biến thể `filled-from-map` (Banner thành công + viền `--good`) cho tới khi khách sửa tay thì về mặc định |

7. **Hành vi.**
   - Script Google Maps **chỉ nạp khi bấm "Bản đồ"** (tạo thẻ `<script>` lúc mở, không nạp ở trang khác). Key qua biến `NEXT_PUBLIC_*` lúc build (tên chờ techlead chốt). Places Autocomplete: `componentRestrictions: { country: 'vn' }`, `language: 'vi'`, dùng session token. Giữ chữ "Google" theo điều khoản.
   - Ô tìm trong sheet: gõ để gợi ý; chọn gợi ý thì ghim bay tới đó. Kéo bản đồ thì ghim đứng giữa, địa chỉ dưới chân cập nhật (đảo toạ độ → chữ).
   - Dòng thông báo hiện **ngay khi sheet mở**, trước khi script nạp xong: "Bản đồ do Google cung cấp. Chữ bạn gõ và vị trí bạn ghim sẽ được gửi tới Google. Không muốn dùng, bạn đóng lại và gõ địa chỉ trực tiếp." (`05-phap-ly.md` §1.2b, BR-BH-29).
   - **Không có nút "Vị trí của tôi"**, không gọi Geolocation của trình duyệt (chốt 10/10: vị trí thiết bị là dữ liệu nhạy cảm theo NĐ 356/2025). Bản đồ nạp lỗi → Dialog C5, chỉ còn "Nhập tay".
   - "Xác nhận vị trí này": điền **chuỗi** địa chỉ vào textarea, đóng sheet, focus textarea (con trỏ cuối chuỗi) để khách thêm hẻm/tầng. **Không lưu toạ độ** ở đâu cả (state, storage, request).
   - Đóng X: không đổi giá trị ô.
   - Sheet mở: animation `translateY(100%)→0` 260ms `--ease-drawer`.
8. **Props.**

```ts
interface AddressFieldProps {
  id?: string;                         // 'f-addr'
  name?: string;                       // 'delivery_address'
  value: string;
  onChange: (value: string) => void;
  error?: string;
  filledFromMap?: boolean;             // false
  readOnly?: boolean;                  // false
  onOpenMap: () => void;
}
interface AddressMapPickerProps {
  open: boolean;
  onClose: () => void;                 // không đổi địa chỉ
  onConfirm: (address: string) => void; // chỉ chuỗi, không toạ độ
  onManualEntry: () => void;           // từ Dialog C5 "Nhập tay"
  apiKey: string;
}
```

9. **Truy cập.** Nút Bản đồ `aria-label="Tìm và chọn địa chỉ trên bản đồ"`. Sheet `role="dialog" aria-modal="true" aria-labelledby` tiêu đề; mở thì focus ô tìm; đóng trả focus về nút Bản đồ. Ô tìm `role="combobox" aria-expanded aria-controls aria-activedescendant`, danh sách `role="listbox"`, dòng `role="option" aria-selected`; ↑ ↓ Enter Esc. Vùng bản đồ `aria-label="Bản đồ, kéo để chỉnh ghim"` (không dùng `role="application"`: ô tìm đã là cách dùng bằng phím). Địa chỉ dưới chân `aria-live="polite"`. Banner "Đã điền…" là `role="status"`.
10. **Câu chữ.** "Địa chỉ giao hàng", placeholder "Bấm để tìm trên bản đồ, hoặc gõ địa chỉ", "Bản đồ", "Thêm hẻm, tầng, toà nhà nếu có.", "Đã điền địa chỉ từ bản đồ.", "Chọn vị trí giao hàng", "Đóng, quay lại nhập tay", "Tìm địa chỉ", "Giao tới đây", "Xác nhận vị trí này", dòng thông báo Google (mục 7). C5 chỉ còn ca bản đồ nạp lỗi, nút "Nhập tay"; câu tiêu đề cũ "Chưa lấy được vị trí của bạn" không dùng nữa, câu mới chờ ux-designer sửa màn C5 `[copy]`.
11. **Không được.** Tách địa chỉ thành nhiều ô (tỉnh, phường…) như C3/C4 còn sót (L-28). Nạp Maps ở mọi trang. Lưu hoặc gửi toạ độ. Xin quyền định vị (V1 không có nút vị trí). Nạp bản đồ trước khi hiện dòng thông báo Google. Ghi địa chỉ vào log/console. Chặn khách sửa tay sau khi điền từ bản đồ.
12. **Code.** Mới `features/checkout/components/AddressField.tsx`, `features/checkout/components/AddressMapPicker.tsx` (tên theo `DOI-CHIEU-CODE.md` §5 lô 3).

## 9. Checkbox

1. **Công dụng.** Ô đồng ý xử lý dữ liệu cá nhân trước khi đặt hàng. **Dùng ở:** `Checkout`, `C1c-AddressFilled`, `C2-Invalid`, `DesktopCheckout`, `DesktopInvalid`.
2. **Giải phẫu.** (a) ô vuông · (b) đoạn chữ có link chính sách · (c) dòng lỗi tuỳ chọn.
3. **Biến thể.** Chỉ một: ô đồng ý (consent).
4. **Kích thước và khoảng cách.** Ô 20×20, lệch xuống 2 để thẳng dòng chữ đầu. Ô cách chữ 12. Cả hàng là `<label>`, vùng chạm ≥ 44 cao. Khối đệm 16.
5. **Token.** `accent-color: var(--accent)`. Chữ body 14/400 `--ink-2`. Link `inline`. Lỗi `caption` `--crit`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | chưa tick (không tick sẵn) |
| hover | không đổi |
| focus-visible | viền 2px `--focus` offset 2 quanh ô |
| disabled | khi đang gửi: không đổi được (`disabled`), chữ giữ màu |
| đang tải | không áp dụng |
| lỗi | bấm "Đặt hàng" khi chưa tick: dòng lỗi dưới, `aria-invalid="true"`, có mục trong FormErrorSummary (Q-UX-4) |
| chọn | tick |

7. **Hành vi.** Mở form là **chưa tick** (đồng ý phải chủ động). BE trả 409 `POLICY_CHANGED` (L-17): bỏ tick, hiện Banner cảnh báo phía trên ô, cuộn tới ô. Shop chưa có chính sách bảo mật (GL-03-AC5): không hiện form, hiện Banner "Shop tạm chưa nhận đơn" như code hiện có. Link chính sách mở tab mới để không mất dữ liệu đang nhập.
8. **Props.**

```ts
interface CheckboxProps {
  id: string;
  name: string;                    // 'privacy_consent'
  checked: boolean;
  onChange: (checked: boolean) => void;
  children: React.ReactNode;       // câu đồng ý kèm link
  error?: string;
  disabled?: boolean;              // false
}
```

9. **Truy cập.** `<input type="checkbox">` gốc trong `<label>`. `aria-describedby` trỏ dòng lỗi. Link trong nhãn vẫn bấm được riêng.
10. **Câu chữ.** "Tôi đồng ý để Cá Về dùng họ tên, số điện thoại và địa chỉ này để giao đơn hàng, theo chính sách quyền riêng tư." Câu lỗi: `[copy]` (gợi ý theo màn: "Đánh dấu đồng ý ở trên để đặt hàng."). Câu chính sách cần `legal-vn` duyệt khi thêm Google Maps.
11. **Không được.** Tick sẵn. Tắt nút "Đặt hàng" thay cho báo lỗi (Q-UX-4). Ô < 20 hoặc vùng chạm < 44.
12. **Code.** Mới `frontend/components/ui/Checkbox.tsx`; thay ô đồng ý trong `CheckoutScreen.tsx`.

## 10. SearchBox + SearchSuggest

1. **Công dụng.** Ô tìm sản phẩm và danh sách gợi ý khi gõ. **Dùng ở:** `Home`, `HeaderFooter-Mobile` (H1, H2), `Main`, `A0-Loading`, `A5-NotFound`, `A8-SearchSuggest`, `DesktopCategory`, `DesktopSearchSuggest`, `HeaderFooter-Desktop`.
2. **Giải phẫu.**
   - SearchBox: (a) `<form role="search">` · (b) icon kính lúp · (c) `input type="search"` · (d) nút xoá từ khoá (khi có chữ) · (e) nút "Tìm" (chỉ máy tính).
   - SearchSuggest: (a) dòng trạng thái ẩn ("2 gợi ý cho “mực”") · (b) tiêu đề "Gợi ý" · (c) tối đa 5 dòng món: ảnh 44, tên (phần khớp đậm), giá/đơn vị · (d) dòng "Xem tất cả kết quả cho “…”" · (e) khối "Tìm gần đây": tiêu đề + nút "Xoá" + chip.
3. **Biến thể.** SearchBox: `brand` (trên header nền `accent`) · `page` (trong trang danh mục) · `trigger` (trang chủ điện thoại: là link trông như ô tìm, mở `/shop/?focus=search`). SearchSuggest: một biến thể, vị trí khác theo khổ.
4. **Kích thước và khoảng cách.**

| Phần | Điện thoại | Máy tính |
|---|---|---|
| SearchBox `brand` | cao 44, bo 999, đệm 0 6 0 16 | cao 48, bo 999, đệm 4 4 4 20, nút "Tìm" cao 40 đệm 0 20 bo 999 |
| SearchBox `page` | cao 44, bo 8, đệm 0 12 | không dùng (máy tính tìm ở header) |
| Nút xoá | 44×44 trong ô | 40×40 |
| Panel gợi ý | cách lề 16 hai bên, ngay dưới ô (cách 8) | dưới ô tìm header, rộng bằng ô |
| Dòng món | `min-height` 60, đệm 8 16, gap 12 | `min-height` 56, đệm 8 16 |
| "Xem tất cả" | cao 48, đệm 0 16 | cao 48 |
| Chip gần đây | 44 | 44 |

5. **Token.** `page`: nền `--surface`, viền 1px `--border-input`, icon `--ink-3`, chữ 16 `--ink`, placeholder `--ink-3`. `brand`: nền `--surface`, không viền. Nút "Tìm": nền `--brand-deep` #0E3A73 (không dùng `accent`), chữ `--on-accent` 14/600. Panel: nền `--surface`, viền `--border`, bo `--radius-card` 12, bóng `--shadow-pop`. Nền sau panel (chỉ điện thoại): `--overlay-light`. Tiêu đề nhóm `caption` 12/600 `--ink-3`. Phần khớp 600 `--ink`. Giá 14/600 `tabular-nums` + đơn vị 12/500 `--ink-2`. "Xem tất cả": chữ 14/600 `--accent-text`, viền trên `--border`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | như token |
| hover | dòng gợi ý → nền `--surface-2`; nút "Tìm" → nền `--brand-deep-hover` #0A2C59 |
| nhấn | nút "Tìm", nút xoá, dòng gợi ý: `scale(.97)` (dòng: chỉ đổi nền `--surface-3`) |
| focus-visible | `page`: viền `--accent` + vòng 3px `--accent-soft` (`:focus-within`); `brand`: vòng 3px `--on-brand-muted`; dòng gợi ý đang chọn bằng phím: nền `--accent-soft` |
| disabled | không áp dụng |
| đang tải | catalog chưa tải xong: không mở panel, Enter vẫn gửi `/shop/?q=` |
| lỗi | không có gợi ý: panel chỉ còn dòng "Xem tất cả kết quả cho “…”" (+ "Tìm gần đây" nếu có) |
| chọn | dòng đang trỏ bằng ↑ ↓: nền `--accent-soft`, `aria-selected="true"` |

7. **Hành vi.**
   - Gõ **từ 2 ký tự** mới mở gợi ý; tối đa **5 món**. Lọc tại chỗ trên catalog đã tải, so khớp **bỏ dấu** (không gọi endpoint mới). Thứ tự như danh mục: món hết xếp cuối.
   - Enter (không chọn dòng nào) → `/shop/?q=<từ khoá>`; lưu từ khoá vào "Tìm gần đây" (`localStorage` khoá `shop_recent_searches_v1`, chỉ từ khoá; số lượng giữ: techlead chốt). "Xoá" xoá cả danh sách.
   - Bấm dòng món → `/shop/item/?code=`. Esc đóng panel, giữ chữ. Tab ra ngoài hoặc bấm nền → đóng.
   - `/shop/?focus=search` (từ kính lúp H2) tự focus ô `page`.
   - Panel hiện: opacity + `translateY(-4px)→0`, 180ms `--ease-out`.
8. **Props.**

```ts
interface SearchBoxProps {
  variant?: 'brand' | 'page' | 'trigger';   // 'page'
  defaultValue?: string;
  placeholder?: string;
  autoFocus?: boolean;                      // false
  action?: string;                          // '/shop/'
  suggestions?: SuggestItem[];              // container lọc sẵn, tối đa 5
  recentQueries?: string[];
  onQueryChange?: (q: string) => void;
  onClearRecent?: () => void;
}
interface SuggestItem { itemCode: string; name: string; price: Money; unit: SaleUnit; group: GroupIcon; imageUrl?: string; }
```

9. **Truy cập.** Input `role="combobox" aria-autocomplete="list" aria-expanded aria-controls aria-activedescendant`; danh sách `role="listbox"`, dòng `role="option"`. Nhãn ẩn "Tìm sản phẩm" (`<label class="sr-only">`). Dòng trạng thái `role="status"` đọc số gợi ý. Nền mờ phía sau `inert`. Nút xoá `aria-label="Xoá từ khoá"`; "Xoá" lịch sử `aria-label="Xoá lịch sử tìm gần đây"`.
10. **Câu chữ.** Placeholder: header "Tìm cá, tôm, mực, combo…", trang danh mục "Tìm cá, tôm, mực…", máy tính "Tìm cá thu, mực ống, tôm sú, combo lẩu…". "Tìm", "Gợi ý", "Xem tất cả kết quả cho “mực”", "Tìm gần đây", "Xoá".
11. **Không được.** Gọi API mỗi lần gõ. Lưu gì khác ngoài từ khoá. Chữ ô < 16 px. Mở panel khi mới focus mà chưa gõ (trừ khi có "Tìm gần đây").
12. **Code.** Mới `components/search/SearchBox.tsx` (lô 1, chỉ gửi form), `components/search/SearchSuggest.tsx` (lô 2) ⚠.

## 11. FormErrorSummary

1. **Công dụng.** Khối liệt kê các ô còn sai, mỗi mục là link nhảy tới ô. **Dùng ở:** `C2-Invalid`, `DesktopInvalid`.
2. **Giải phẫu.** (a) icon lỗi · (b) tiêu đề "Còn N chỗ cần sửa" · (c) danh sách link tên ô.
3. **Biến thể.** Một biến thể.
4. **Kích thước và khoảng cách.** Đệm 12 14, bo 10, cách bước đặt hàng 8, lề 16 (điện thoại); máy tính nằm đầu cột form, rộng bằng cột. Link `min-height` 44 (điện thoại) / 40 (máy tính), cách nhau ngang 16, xuống dòng khi hẹp.
5. **Token.** Nền `--crit-soft` #FCEDEC, viền 1px `--crit-border` #F2C9C6. Icon 18 `--crit`. Tiêu đề 14/600 `--crit`. Link `danger-inline` 14/500 `--crit`, gạch chân.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | ẩn khi không có lỗi |
| hover | link → `--crit-hover` |
| focus-visible | khối nhận focus (`tabindex="-1"`): viền 2px `--focus` offset 2; link: như Link |
| lỗi | hiện sau khi bấm gửi mà còn lỗi |
| disabled / đang tải / chọn | không áp dụng |

7. **Hành vi.** Bấm "Đặt hàng" còn lỗi → hiện khối, **dời focus vào khối**, cuộn lên. Bấm link → focus vào ô tương ứng (`scroll-margin-top` = cao header + 8), không chỉ cuộn. Sửa xong một ô thì số N giảm; hết lỗi thì khối biến mất. Thứ tự mục theo thứ tự ô trên form.
8. **Props.**

```ts
interface FormErrorSummaryProps {
  errors: { fieldId: string; label: string }[];   // rỗng: không render
  focusOnMount?: boolean;                          // true
}
```

9. **Truy cập.** `role="alert"` khi xuất hiện, `aria-labelledby` tiêu đề. Mỗi ô lỗi vẫn có `aria-invalid` + `aria-describedby` riêng.
10. **Câu chữ.** "Còn 3 chỗ cần sửa" (1 chỗ: "Còn 1 chỗ cần sửa"); mục là tên ô: "Họ và tên", "Số điện thoại", "Địa chỉ giao hàng", "Đồng ý xử lý dữ liệu" `[copy]`.
11. **Không được.** Dùng cho form tra đơn (F2 dùng Banner chung, không chỉ ra ô sai). Chép nội dung khách nhập vào khối.
12. **Code.** Mới `frontend/components/ui/FormErrorSummary.tsx`.

---

# B. Hàng hoá

## 12. ProductCard

1. **Công dụng.** Thẻ một mặt hàng trong lưới, hàng ngang hoặc danh sách combo. **Dùng ở:** `Main`, `A4-Toast`, `DesktopCategory`, `DesktopToast` (lưới); `Home`, `DesktopHome` (hàng "Đang có hàng", "Combo nấu nhanh").
2. **Giải phẫu.** (a) ImageFrame (StockBadge góc trên phải, tag "Combo" góc trên trái) · (b) tên (h3, tối đa 2 dòng) · (c) PriceTag · (d) ghi chú ngắn (`short_note`) · (e) hành động: AddToCart hoặc "Liên hệ chúng tôi". Giá luôn đặt **trước** ghi chú (kể cả `rail`, khác file `Home` đang đặt sau).
3. **Biến thể.**

| `variant` | Bố cục | Hành động |
|---|---|---|
| `grid` | dọc, ảnh 3:2 | AddToCart ("Thêm 1 kg" → stepper) |
| `rail` (hàng cuộn trang chủ, kiểu Long Châu) | dọc, rộng cố định 156, ảnh 1:1, cuộn ngang | nút pill "Chọn mua" cao 40, **dẫn sang trang chi tiết** (không thêm vào giỏ) |
| `row` | ngang: ảnh 72 + chữ + mũi tên, cả dòng là link | không có nút |

4. **Kích thước và khoảng cách.**

| Phần | Điện thoại | Máy tính |
|---|---|---|
| Lưới `grid` | 2 cột, gap 12, lề 16 | `repeat(auto-fill, minmax(196px, 1fr))`, gap 14 → 16; `lg` ≥ 4 cột |
| Thẻ | đệm 8, gap 4, bo 10 | đệm 12, gap 4, bo 12 |
| Ảnh | 3:2 (grid), 1:1 (rail), 72×72 (row), bo 8, cách tên 4 | như điện thoại |
| Tên | `min-height` 2 dòng | như điện thoại |
| Ghi chú | `min-height` 18 | như điện thoại |
| Nút | `grid`: cao 44, cách ghi chú 6, rộng đầy, bo 8 · `rail`: pill cao 40, rộng đầy, cách trên 4, vùng chạm 44 (`::before` `inset: -2px 0`) | như điện thoại |
| `rail` | rộng 156, hàng gap 10 → 12, đệm cuối 16 | không dùng; máy tính hiện `grid` |

5. **Token.** Thẻ nền `--surface`, viền 1px `--border` (`rail`, `row`: không viền, nằm trên khối nền trắng), bo `--radius-lg` (điện thoại) / `--radius-card` (máy tính), không bóng khi đứng yên. Tên 14/500 (máy tính 15/500), line-height 1.3, `--ink`. Giá **mọi biến thể thẻ**: `--ink` (`grid` 17/600, `rail`/`row` 16/600); không dùng `accent-text` trên thẻ. Nút "Chọn mua" `rail`: Button `primary` pill. Ghi chú `caption` `--ink-3`. Tag "Combo": nền `--surface`, viền `--border`, chữ `caption` `--ink-2`, cao 22, bo `--radius-sm`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | như token |
| hover (máy tính) | viền thẻ → `--border-strong` + bóng `--shadow-card-hover` (0 6px 20px rgba(23,23,28,.06)), 150ms; không nhấc thẻ (không `translateY`) |
| nhấn | chỉ phần tử bấm được (tên, nút) phản hồi; thẻ không scale |
| focus-visible | trên link tên và nút, viền 2px `--focus` |
| disabled | không áp dụng |
| đang tải | `ProductCardSkeleton` cùng kích thước |
| lỗi | không áp dụng ở thẻ (lỗi tải ở cấp danh sách: ErrorState) |
| chọn | đã có trong giỏ: hành động là stepper nền `accent` (xem AddToCart) |
| hết hàng | ảnh `opacity: .55` (nhãn trên ảnh không mờ), tên và giá `--ink-2`, nút thành "Liên hệ chúng tôi" (`secondary`, icon điện thoại, `tel:`) |
| sắp hết | StockBadge `low` trên ảnh |

7. **Hành vi.** Danh sách luôn xếp **món hết xuống cuối**. Bấm tên hoặc ảnh → `/shop/item/?code=`. `rail` "Chọn mua" → trang chi tiết (không thêm vào giỏ). Không hiện số kg tồn, ngày nhập, mã lô. Thẻ là trình bày; container (`CatalogGrid`) nối `useCart()` và truyền `quantityInCart` + callback.
8. **Props.**

```ts
interface ProductCardItem {
  itemCode: string;
  name: string;
  unit: SaleUnit;
  price: Money;
  stockLevel: StockLevel;
  shortNote?: string;
  image?: ItemImage | null;
  group: GroupIcon;
  isCombo: boolean;
  minQty: number;          // từ API min_qty
  qtyStep: number;         // từ API qty_step
}
interface ProductCardProps {
  item: ProductCardItem;
  variant?: 'grid' | 'rail' | 'row';   // 'grid'
  href: string;
  hotline: string;
  quantityInCart?: number;             // 0: chưa có trong giỏ (đây là số lượng khách chọn, không phải tồn)
  onAdd?: (qty: number) => void;
  onChangeQty?: (qty: number) => void;
  onRequestRemove?: () => void;
}
```

9. **Truy cập.** `<article aria-labelledby>` trỏ tên. Ảnh trong thẻ: `alt=""` khi đã có tên bên dưới (tránh đọc hai lần); link ảnh `tabindex="-1" aria-hidden` để chỉ một điểm dừng Tab cho tên. StockBadge có chữ nên trình đọc nghe "Sắp hết". Nút có `aria-label` đủ tên món (xem AddToCart).
10. **Câu chữ.** "Thêm 1 kg", "Thêm 1 combo", "Liên hệ chúng tôi", "Chọn mua", "Combo", "Sắp hết", "/ kg", "/ combo". Ghi chú lấy từ dữ liệu (vd. "Cắt khúc dày 2–3 cm").
11. **Không được.** Hiện "Còn X kg". Ẩn giá khi hết hàng. Nhấc thẻ khi hover hoặc dùng bóng nặng hơn `--shadow-card-hover`. Tô giá thẻ bằng `accent-text`. Cho nút "Chọn mua" ở `rail` thêm thẳng vào giỏ. Lồng thẻ trong thẻ. Gọi API trong thẻ.
12. **Code.** Mới `components/catalog/ProductCard.tsx` ⚠(lô 2); thay phần thẻ trong `components/CatalogGrid.tsx` (bỏ dòng "Còn X kg" `CatalogGrid.tsx:49-50`) và `features/content/components/ItemCard.tsx`.

## 13. StockBadge

1. **Công dụng.** Nhãn mức tồn: Còn hàng · Sắp hết · Hết hàng. **Không bao giờ có số.** **Dùng ở:** `Main`, `Home`, `DesktopCategory` (trên ảnh); `Product`, `A7-OutOfStock`, `DesktopProduct`, `DesktopOutOfStock` (dưới giá và trên ảnh).
2. **Giải phẫu.** (a) icon (đồng hồ cát, dấu tích, vòng cấm) · (b) chữ.
3. **Biến thể.**

| `placement` | `in` | `low` | `out` |
|---|---|---|---|
| `overlay` (trên ảnh) | không render | nhãn hổ phách "Sắp hết" | nhãn trung tính "Hết hàng" |
| `inline` (dưới giá) | icon tích + "Còn hàng" | icon + "Sắp hết" | icon cấm + "Hết hàng" |

`size`: `sm` (thẻ) · `md` (ảnh trang chi tiết).
4. **Kích thước và khoảng cách.** overlay `sm`: cao 22, đệm 0 6, cách góc ảnh 6 (máy tính 8), icon 12, gap 3. overlay `md`: cao 26, đệm 0 10, cách góc 10. inline: icon 14, gap 4, không nền.
5. **Token.** Bo `--radius-sm`. overlay `low`: nền `--warn-soft`, chữ/icon `--warn`, `caption` 12/500. overlay `out`: nền `--surface-3` #EBEBEF, chữ `--ink-2` #4E4E58, không viền, không dùng `crit` (`md`: 13/600). inline `in`: `--good` `caption`; `low`: `--warn`; `out`: `--ink-2`.
6. **Trạng thái.** Tĩnh. mặc định / hover / nhấn / focus / disabled / đang tải / lỗi / chọn: không áp dụng (không bấm được).
7. **Hành vi.** Chỉ nhận `'in' | 'low' | 'out'` từ field `stock_level` (BE-1). **Không** suy `'low'` ở FE (ngưỡng nằm ở settings BE). `sellable_qty` bị gỡ khỏi Shop API ở lô 2 cùng lúc với BE-1 (chốt 10/10, S-09), nên không có lớp map tạm từ số kg.
8. **Props.**

```ts
interface StockBadgeProps {
  level: StockLevel;                       // 'in' | 'low' | 'out' — không có prop nhận số kg
  placement?: 'overlay' | 'inline';        // 'overlay'
  size?: 'sm' | 'md';                      // 'sm'
}
```

9. **Truy cập.** Chữ luôn hiện (không chỉ màu). Icon `aria-hidden`.
10. **Câu chữ.** "Còn hàng", "Sắp hết", "Hết hàng".
11. **Không được.** Nhận hoặc hiện số kg ("Còn 2 kg", "Chỉ còn ít"). Dùng `crit` (đỏ) cho hết hàng. Hiện nhãn "Còn hàng" trên ảnh thẻ.
12. **Code.** Mới `components/catalog/StockBadge.tsx` ⚠.

## 14. PriceTag

1. **Công dụng.** Hiện giá theo đơn vị (kg hoặc combo), giá cũ khi đổi giá, và tổng tiền. **Dùng ở:** `Main`, `Product`, `A9-ComboDetail`, `Cart`, `B3-CartChanged`, `Checkout`, `Payment`, `Success`, bản máy tính tương ứng.
2. **Giải phẫu.** (a) giá cũ gạch ngang (tuỳ chọn) · (b) mũi tên (tuỳ chọn) · (c) số tiền · (d) đơn vị "/ kg" hoặc "/ combo".
3. **Biến thể.**

| `size` | Số | Đơn vị | Dùng |
|---|---|---|---|
| `card` | 17/600 `--ink` | 13/500 `--ink-2` | thẻ lưới |
| `rail` | 16/600 `--ink` | 12/500 `--ink-2` | thẻ trang chủ, gợi ý tìm |
| `detail` | 24/600 `--accent-text` | 14/500 `--ink-2` | trang chi tiết |
| `meta` | `caption` 12/500 `--ink-3`, cả số lẫn đơn vị | — | đơn giá trong dòng giỏ |
| `total` | 24/600 `--accent-text` | không đơn vị | tổng tiền hàng, cần thanh toán, đã thanh toán |
| `line` | 14/600 `--ink` | không đơn vị | thành tiền một dòng |

4. **Kích thước và khoảng cách.** Số và đơn vị cùng đường chân chữ (`align-items: baseline`), cách 4 (chi tiết máy tính 6). Giá cũ cách mũi tên 6.
5. **Token.** `tabular-nums`. Màu theo bảng: **giá trên thẻ luôn `--ink`**; giá trang chi tiết và mọi tổng tiền `--accent-text` #1A5BC0. Hết hàng: số `--ink-2` (`tone="muted"`). Giá cũ `<del>` `--ink-3`; giá mới 600 `--ink`.
6. **Trạng thái.** Tĩnh. Chỉ có `tone`: `default` · `accent` · `muted` (hết hàng, đơn đã huỷ). hover / nhấn / focus / disabled / đang tải / lỗi / chọn: không áp dụng.
7. **Hành vi.** Định dạng bằng `formatVnd` → "278.000đ" (chấm phân nghìn, "đ" liền số; kiểm `formatVnd` cho đúng mẫu này). Đơn vị theo `unit` của mặt hàng: `kg` → "/ kg", `combo` → "/ combo" (L-06: không để combo hiện "/ kg").
8. **Props.**

```ts
interface PriceTagProps {
  amount: Money;
  unit?: SaleUnit | null;                    // null: không hiện đơn vị
  size?: 'card' | 'rail' | 'detail' | 'meta' | 'total' | 'line';   // 'card'
  tone?: 'default' | 'accent' | 'muted';     // theo size
  previousAmount?: Money;                    // có: hiện giá cũ gạch ngang
}
```

9. **Truy cập.** Giá cũ có chữ ẩn "Giá cũ ", giá mới "Giá mới " (theo B3). Đơn vị đọc liền: "278.000 đồng / ki-lô-gam" do trình đọc tự xử lý; không thêm `aria-label` đè.
10. **Câu chữ.** "278.000đ", "/ kg", "/ combo".
11. **Không được.** Tính tiền bằng float để hiện số phải trả. Bỏ đơn vị ở giá mặt hàng. Viết "/kg" không cách. Hiện giá vốn.
12. **Code.** Mới `components/catalog/PriceTag.tsx`.

## 15. QtyStepper

1. **Công dụng.** Tăng giảm số lượng theo luật bán: kg (tối thiểu 1, bước 0,5) hoặc combo (tối thiểu 1, bước 1). **Dùng ở:** `Main`, `A4-Toast`, `DesktopCategory` (trên thẻ); `Product`, `A9-ComboDetail`, `DesktopProduct` (chọn số lượng); `Cart`, `B3-CartChanged`, `DesktopCart` (dòng giỏ).
2. **Giải phẫu.** (a) nút trừ: icon "−", hoặc **icon thùng rác khi ở mức tối thiểu** trong `mode="cart"` · (b) giá trị + đơn vị · (c) nút "+".
3. **Biến thể.**

| `variant` | Hình | Dùng |
|---|---|---|
| `filled` | nền `accent`, icon trắng | trên thẻ sau khi đã thêm |
| `outline` | viền `border-strong`, nền trắng | trang chi tiết, dòng giỏ |

`mode`: `select` (trang chi tiết: giá trị chưa vào giỏ) · `cart` (thẻ và dòng giỏ: giá trị đang trong giỏ).
`size`: `md` 44 · `sm` 40 (dòng giỏ, theo số chuẩn "giỏ 40").
4. **Kích thước và khoảng cách.**

| | Điện thoại | Máy tính |
|---|---|---|
| Cao | md 44 · sm 40 | như điện thoại |
| Nút ± | 44×44 (sm: 40×40; vùng chạm vẫn ≥ 44 nhờ đệm hàng) | 44×44 · 40×40 |
| Ô giá trị | `min-width` 64 (sm 60), căn giữa | `min-width` 72 |
| `filled` | rộng đầy thẻ | rộng đầy thẻ |

5. **Token.** Bo `--radius-md` (cả hai khổ). `outline`: viền 1px `--border-strong`, icon `--ink`. `filled`: nền `--accent`, icon/chữ `--on-accent`. Giá trị 14/600 `tabular-nums` (sm: 13/600).
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | nút ± `outline` → nền `--surface-2`; `filled` → nền `--accent-hover` cho nút đang trỏ |
| nhấn | nút ±: `scale(.97)` |
| focus-visible | `outline`: viền 2px `--focus` offset 2; `filled`: viền trắng offset −4 |
| disabled | `mode="select"` (trang chi tiết, chưa vào giỏ) ở 1 kg / 1 combo: nút "−" **disabled** (`aria-disabled="true"`, icon `--ink-3`, bấm không làm gì, vẫn focus được để nghe lý do "Tối thiểu 1 kg") |
| ở mức tối thiểu, `mode="cart"` | nút trừ đổi icon "−" → **thùng rác** (cùng màu icon của biến thể: `--on-accent` trên `filled`, `--ink` trên `outline`); đổi icon bằng fade 150ms; bấm mở Dialog B2, không bỏ ngay |
| đang tải | không áp dụng (đổi số là tức thì, giỏ ở client) |
| lỗi | không áp dụng; vượt tồn chỉ biết khi đặt hàng (popup C3) |
| chọn | không áp dụng |

7. **Hành vi.**
   - `min` = `min_qty`, `step` = `qty_step` từ API (kg: 1 và 0,5; combo: 1 và 1). Giá trị luôn là `min + k·step`.
   - Tính bằng số bước nguyên (`Math.round(value / step)`) rồi nhân lại, để không trôi số thực (1,5 + 0,5 ≠ 1,9999).
   - `mode="cart"` (thẻ và giỏ): ở mức `min`, nút trừ hiện icon thùng rác; bấm **không tự xoá**, gọi `onRequestRemove()` → container mở Dialog "Bỏ … khỏi giỏ?" (B2). Chọn "Giữ lại" thì số lượng giữ nguyên ở `min`.
   - `mode="select"` (trang chi tiết, chưa vào giỏ): nút trừ disabled ở `min`.
   - "+" không có trần ở FE (FE không biết số kg tồn); BE kiểm khi đặt (C3).
   - Hiện số kiểu Việt: "1 kg", "1,5 kg", "2 combo".
8. **Props.**

```ts
interface QtyStepperProps {
  value: number;
  min: number;                         // từ min_qty
  step: number;                        // từ qty_step
  unit: SaleUnit;
  itemName: string;                    // cho aria-label
  mode?: 'select' | 'cart';            // 'cart'
  variant?: 'outline' | 'filled';      // 'outline'
  size?: 'md' | 'sm';                  // 'md'
  onChange: (next: number) => void;
  onRequestRemove?: () => void;        // bắt buộc khi mode='cart'
}
```

9. **Truy cập.** Bọc `role="group" aria-label="Số lượng {tên món}"`. Nút: "Thêm 0,5 kg {tên}" / "Bớt 0,5 kg {tên}" (combo: "Thêm 1 combo {tên}"); ở mức `min` trong `mode="cart"` nút thùng rác có nhãn "Bỏ {tên} khỏi giỏ". Giá trị `aria-live="polite"` (trang chi tiết); ở thẻ và giỏ dùng vùng live chung của trang ("Đã cập nhật Mực ống làm sạch").
10. **Câu chữ.** "Tối thiểu 1 kg" (đặt cạnh stepper ở trang chi tiết, số lấy từ `min_qty`), "Chọn số kg", "Số combo".
11. **Không được.** Cho xuống dưới `min` hoặc ra số không thuộc bước. Tự xoá món khi bấm thùng rác (luôn qua Dialog B2). Hiện thùng rác ở trang chi tiết (ở đó nút trừ chỉ disabled). Ô nhập số tự do (màn không có). Chặn "+" theo tồn ước đoán. Bước 0,1 như code cũ.
12. **Code.** Mới `components/catalog/QtyStepper.tsx` ⚠; bỏ stepper trong `components/AddToCartControl.tsx:26-56` và `CheckoutScreen.tsx:207,215`.

## 16. AddToCart

1. **Công dụng.** Cụm hành động mua của một mặt hàng: nút "Thêm 1 kg" biến thành stepper, hoặc thanh mua ở trang chi tiết. **Dùng ở:** `Main`, `A4-Toast`, `DesktopCategory`, `DesktopToast` (thẻ); `Product`, `A9-ComboDetail`, `A7-OutOfStock`, `DesktopProduct`, `DesktopOutOfStock`, `DesktopComboDetail` (thanh mua).
2. **Giải phẫu.**
   - `card`: (a) nút `outline` "Thêm 1 kg" **hoặc** (b) QtyStepper `filled` **hoặc** (c) Button `secondary` "Liên hệ chúng tôi".
   - `detail`: (a) khối "Chọn số kg" (Toggle preset + QtyStepper `select` + "Tối thiểu 1 kg") · (b) "Tạm tính" · (c) thanh: "Thêm vào giỏ" (`outline` lg pill) + "Chọn mua" (`primary` lg pill). Hết hàng: thanh thành "Gọi [hotline]" (`primary`) + "Nhắn Zalo" (`outline`).
3. **Biến thể.** `card` · `detail`.
4. **Kích thước và khoảng cách.** `card`: cao 44, rộng đầy, bo 8. `detail` điện thoại: thanh dính đáy cao ≈72 + safe-area, đệm 10 16 16, lưới 2 cột gap 12, bóng `--shadow-bar`. `detail` máy tính: không dính; hai nút trong cột phải, `repeat(auto-fit, minmax(160px, 1fr))`, gap 12; "Tạm tính" là khối nền `--surface-2` bo 12 đệm 14 16.
5. **Token.** Nút "Thêm 1 kg": `outline` (viền `--accent`, chữ `--accent-text` 14/600). Stepper: `filled`. "Tạm tính": nhãn body `--ink-2`, số `title` 17/600 `--ink` cả hai khổ (chưa phải tổng đơn nên không dùng 24 `accent-text`; file máy tính ghi 22).
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | chưa có trong giỏ: nút "Thêm 1 kg" |
| hover | nút `outline` → nền `--accent-soft` |
| nhấn | `scale(.97)` |
| focus-visible | như Button / QtyStepper |
| disabled | không dùng; hết hàng thay bằng "Liên hệ chúng tôi" |
| đang tải | không áp dụng (thêm vào giỏ là tức thì) |
| lỗi | không áp dụng ở đây |
| chọn | đã trong giỏ: stepper `filled` hiện số lượng trong giỏ |

7. **Hành vi.**
   - Bấm "Thêm 1 kg" → thêm `min_qty` vào giỏ, nút đổi sang stepper bằng fade + `scale(.96→1)` 180ms `--ease-out`; **focus chuyển tới nút "+" của stepper** (nút cũ biến mất nên không để focus rơi). Bớt về dưới `min` → Dialog bỏ món; bỏ xong thì nút "Thêm 1 kg" quay lại và nhận focus.
   - Sau khi thêm: điện thoại hiện Toast "Đã thêm 1 kg {tên} vào giỏ" + "Xem giỏ"; máy tính hiện Toast tối + MiniCart. Badge giỏ +1 khi là món mới.
   - Trang chi tiết: "Thêm vào giỏ" cộng số đang chọn vào dòng sẵn có (giữ hành vi `addItem` hiện tại), ở lại trang, báo Toast. "Chọn mua" = thêm rồi chuyển `/shop/cart/`.
   - Hết hàng: thẻ hiện "Liên hệ chúng tôi" (`tel:`); trang chi tiết hiện "Gọi [hotline]" + "Nhắn Zalo" (Zalo chưa có thì chỉ còn nút gọi, rộng đầy).
   - Giỏ giữ chỗ? **Không.** Thêm vào giỏ không giữ hàng; giữ 30 phút chỉ bắt đầu khi bấm "Đặt hàng".
8. **Props.**

```ts
interface AddToCartProps {
  item: ProductCardItem;
  variant: 'card' | 'detail';
  quantityInCart: number;                 // 0: chưa có
  hotline: string;
  zaloUrl?: string;
  onAdd: (qty: number) => void;           // container gọi addItem + toast
  onChangeQty: (qty: number) => void;
  onRequestRemove: () => void;
  onBuyNow?: (qty: number) => void;       // 'detail': thêm rồi tới /shop/cart/
}
```

9. **Truy cập.** Nút thẻ: `aria-label="Thêm 1 kg {tên} vào giỏ"` (combo: "Thêm 1 combo {tên} vào giỏ"). "Liên hệ chúng tôi": `aria-label="Liên hệ Cá Về hỏi hàng {tên}"`. Vùng `aria-live="polite"` của trang đọc "Đã cập nhật {tên}" / "Đã bỏ {tên} khỏi giỏ".
10. **Câu chữ.** "Thêm 1 kg", "Thêm 1 combo", "Thêm vào giỏ", "Chọn mua", "Liên hệ chúng tôi", "Gọi [hotline]", "Nhắn Zalo", "Tạm tính", "Tối thiểu 1 kg". Máy tính dưới "Tạm tính": "Cân đúng số kg bạn đặt" `[copy]` (có trên `DesktopProduct`; cần `mkt-brand` xác nhận vì là lời hứa).
11. **Không được.** Thêm dưới `min_qty`. Hiện "Hết hàng" dạng nút bị khoá (code cũ). Nói "đã giữ hàng" khi thêm vào giỏ. Hứa "báo khi có hàng".
12. **Code.** Viết lại `components/AddToCartControl.tsx` thành `components/catalog/AddToCart.tsx` ⚠.

## 17. ImageFrame

1. **Công dụng.** Khung ảnh mặt hàng có tỉ lệ cố định, ảnh dự phòng theo nhóm, nhãn "Ảnh minh hoạ" và bộ đếm ảnh. **Dùng ở:** mọi thẻ, dòng giỏ, gợi ý tìm, `Product`, `A7-OutOfStock`, `A9-ComboDetail`, `DesktopProduct`.
2. **Giải phẫu.** (a) khung tỉ lệ cố định · (b) `<img>` hoặc ảnh dự phòng (icon nhóm) · (c) khe góc trên trái/phải (tag, StockBadge) · (d) "Ảnh minh hoạ" góc dưới trái · (e) bộ đếm "1/3" góc dưới phải.
3. **Biến thể.** `ratio`: `3/2` (thẻ lưới) · `1/1` (thẻ trang chủ, chi tiết điện thoại) · `4/3` (chi tiết máy tính) · `square` cố định (44, 48, 56, 64, 68, 72 cho dòng/thumb).
4. **Kích thước và khoảng cách.** Bo 8 (thẻ, dòng), 12 (ảnh lớn trang chi tiết). Icon dự phòng: 32 (thẻ điện thoại), 40 (thẻ máy tính), 96 (chi tiết điện thoại), 120 (chi tiết máy tính), 22–30 (dòng). Nhãn góc cách mép 10 (chi tiết) / 6–8 (thẻ). "Ảnh minh hoạ" và bộ đếm cao 24 (máy tính 26).
5. **Token.** Nền `--surface-2`. Icon dự phòng nét `--ink-3` (ảnh lớn: `--border-input`). "Ảnh minh hoạ": nền `--surface`, viền `--border`, chữ `caption` `--ink-2`, bo `--radius-sm`. Bộ đếm: nền `--ink`, chữ `--on-accent` `caption`, bo `--radius-full`, `tabular-nums`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | ảnh thật |
| đang tải | khung giữ tỉ lệ (không nhảy bố cục), nền `--surface-2` |
| lỗi | `onError` → ảnh dự phòng (không request thêm) |
| hết hàng | `dimmed`: chỉ lớp ảnh `opacity: .55`; nhãn góc giữ nguyên độ đậm |
| hover / nhấn / focus / disabled / chọn | không áp dụng (khung không bấm được; link bọc ngoài lo focus) |

7. **Hành vi.** Giữ logic `srcSet`/`sizes` của `ItemImageFrame.tsx`: thẻ `loading="lazy"` không tải bản `detail`; trang chi tiết `eager`. Có `width`/`height` để chống CLS. Bộ đếm chỉ hiện khi > 1 ảnh (L-22: hiện tại BE chỉ có 1 ảnh/mặt hàng). Ảnh minh hoạ (`is_illustration`) luôn có nhãn.
8. **Props.**

```ts
interface ImageFrameProps {
  image?: ItemImage | null;
  alt: string;                         // '' khi tên đã hiện cạnh ảnh
  group: GroupIcon;                    // icon dự phòng
  ratio?: '3/2' | '1/1' | '4/3';       // '3/2'
  squareSize?: 44 | 48 | 56 | 64 | 68 | 72;   // dùng thay ratio cho dòng/thumb
  loadingPriority?: 'lazy' | 'eager';  // 'lazy'
  dimmed?: boolean;                    // false
  topLeft?: React.ReactNode;           // tag "Combo"
  topRight?: React.ReactNode;          // StockBadge
  counter?: { current: number; total: number };
}
```

9. **Truy cập.** Ảnh trang chi tiết có `alt` (mô tả ảnh hoặc tên món). Ảnh dự phòng trang chi tiết `role="img" aria-label="{tên}"`; trong thẻ thì `aria-hidden`. Bộ đếm có chữ ẩn "Ảnh 1 trên 3".
10. **Câu chữ.** "Ảnh minh hoạ".
11. **Không được.** Khung không tỉ lệ (gây CLS). Mờ cả nhãn "Hết hàng". Tải ảnh `detail` ở lưới. Hard-code màu trong SVG (dùng `currentColor`).
12. **Code.** Viết lại `components/ItemImageFrame.tsx` thành `components/catalog/ImageFrame.tsx`.

## 18. CategoryTile

1. **Công dụng.** Ô icon nhóm hàng để vào danh mục. **Dùng ở:** `Home`, `DesktopHome`.
2. **Giải phẫu.** (a) ô icon · (b) tên nhóm · (c) số món (chỉ máy tính).
3. **Biến thể.** `sm` (điện thoại, lưới 5 cột) · `md` (máy tính, có số món).
4. **Kích thước và khoảng cách.** `sm`: ô icon 48, icon 26, tên cách ô 6, đệm dọc 4 8; lưới 5 cột gap 4 trong khối đệm 14 8 8. `md`: ô icon 60, icon 32; lưới `repeat(auto-fill, minmax(140px, 1fr))`. Cả ô là link, vùng chạm ≥ 44.
5. **Token.** Ô icon nền `--accent-soft`, icon `--accent-text`, bo `--radius-card` 12. Tên `caption` 12/500 `--ink` (`md`: 14/500). Số món `caption` `--ink-3` `tabular-nums`. Khối chứa nền `--surface`, bo `--radius-card`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | nền ô → `--surface-2` (cả ô), bo `--radius-md` |
| nhấn | `scale(.97)` |
| focus-visible | viền 2px `--focus` quanh ô |
| đang tải | Skeleton ô vuông + vạch chữ |
| disabled / lỗi / chọn | không áp dụng |

7. **Hành vi.** Link `/shop/?group=<slug>`; Combo → `/shop/?type=combo`. Số món đếm ở FE từ catalog (số mặt hàng trong nhóm). Nhóm không có món nào thì ẩn ô. Ô "Lô mới về" **bỏ** (D7, chốt 10/10), không code.
8. **Props.**

```ts
interface CategoryTileProps {
  label: string;
  href: string;
  icon: GroupIcon;
  itemCount?: number;            // số mặt hàng, không phải kg
  size?: 'sm' | 'md';            // 'sm'
}
```

9. **Truy cập.** Một link, tên truy cập = tên nhóm (+ ", 5 món" ở `md`). Icon `aria-hidden`. Lưới bọc `<nav aria-label="Danh mục">`.
10. **Câu chữ.** "Cá", "Tôm", "Mực", "Cua ghẹ", "Combo"; "5 món".
11. **Không được.** Hiện số kg. Dùng ảnh nặng thay icon. Thêm ô "Lô mới về" (đã bỏ, D7).
12. **Code.** Mới `components/catalog/CategoryTile.tsx`.

---

# C. Giỏ hàng

## 19. CartLine

1. **Công dụng.** Một dòng món trong giỏ: ảnh, tên, đơn giá, số lượng, thành tiền, xoá; có trạng thái đổi giá và hết hàng. **Dùng ở:** `Cart`, `B2-RemoveConfirm`, `B3-CartChanged`, `DesktopCart`, `DesktopCartChanged`, `DesktopRemoveConfirm`.
2. **Giải phẫu.** (a) ảnh · (b) tên (link tới chi tiết ở máy tính) · (c) nút xoá · (d) đơn giá (giá cũ → giá mới khi đổi) · (e) tag "Giá đã cập nhật" · (f) QtyStepper · (g) thành tiền. Hết hàng: (d) thành dòng "1 kg · 290.000đ / kg · không tính vào tổng", thêm "Món này đã hết" và hai nút.
3. **Biến thể.** `layout`: `list` (điện thoại) · `table-row` (máy tính, bảng 5 cột: Sản phẩm · Đơn giá · Số lượng · Thành tiền · Xoá). `status`: `ok` · `price-changed` · `out`.
4. **Kích thước và khoảng cách.**

| | Điện thoại | Máy tính |
|---|---|---|
| Dòng | đệm 14 16, gap 12, kẻ dưới 1px | ô bảng đệm 16 12, kẻ trên 1px |
| Ảnh | 68 bo 8 | 64 bo 8 |
| Nút xoá | 44, kéo lên `margin: -12px -12px 0 0` | 44 |
| Stepper | `sm` 40 | `sm` 40 |
| Hai nút (hết hàng) | lưới 2 cột gap 8, cao 44 | cùng hàng, cao 44 |

5. **Token.** Nền `--surface`. Tên 14/500 `--ink`. Đơn giá PriceTag `meta`. Thành tiền PriceTag `line`. Nút xoá icon `--ink-3`. Tag "Giá đã cập nhật": nền `--warn-soft`, chữ `--warn` `caption`, cao 22, bo `--radius-sm`. Dòng hết hàng: nền `--canvas`, ảnh `opacity: .5`, tên `--ink-2`, "Món này đã hết" 13/600 `--ink-2` + icon. Bảng máy tính: tiêu đề cột 13/500 `--ink-3`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | máy tính: nút xoá → nền `--crit-soft`, icon `--crit`; không tô cả hàng |
| nhấn | nút: `scale(.97)` |
| focus-visible | trên từng nút/link |
| disabled | không áp dụng |
| đang tải | `CartLineSkeleton` khi đang tải lại catalog để so giá |
| lỗi | `price-changed`, `out` như giải phẫu |
| chọn | không áp dụng |

7. **Hành vi.** Mở giỏ thì container tải lại catalog, so giá đã lưu lúc thêm (`price` trong giỏ) với giá hiện hành và `stock_level` → gán `status`. Bấm xoá (thùng rác hoặc "Bỏ khỏi giỏ") **luôn qua Dialog xác nhận** (UI-RULES §5.4). Bớt dưới tối thiểu → cùng Dialog. Bỏ xong: vùng live đọc "Đã bỏ {tên} khỏi giỏ", focus về tên dòng kế tiếp (hết dòng thì về tiêu đề "Giỏ hàng"). Món `out` không tính vào tạm tính. Đổi giá: tag hiện tới khi rời trang giỏ, sau đó giá mới thành giá lưu.
8. **Props.**

```ts
interface CartLineProps {
  line: {
    itemCode: string; name: string; unit: SaleUnit; qty: number;
    unitPrice: Money; previousUnitPrice?: Money;
    image?: ItemImage | null; group: GroupIcon; shortNote?: string;
    minQty: number; qtyStep: number;
  };
  status?: 'ok' | 'price-changed' | 'out';   // 'ok'
  layout?: 'list' | 'table-row';             // 'list'
  href: string;
  hotline: string;
  onChangeQty: (qty: number) => void;
  onRequestRemove: () => void;
}
```

9. **Truy cập.** Điện thoại `<ul>/<li>`; máy tính `<table>` có `<th scope="col">`, cột xoá có tiêu đề ẩn "Xoá". Dòng hết hàng `aria-label="{tên}, đã hết hàng"`. Nút xoá "Bỏ {tên} khỏi giỏ". Giá cũ/mới có chữ ẩn.
10. **Câu chữ.** "Giá đã cập nhật", "Món này đã hết", "không tính vào tổng", "Liên hệ chúng tôi", "Bỏ khỏi giỏ". Dưới danh sách: "Mua tối thiểu 1 kg mỗi món." (máy tính thêm "Hàng được giữ 30 phút sau khi đặt. Khi còn nằm trong giỏ, hàng chưa được giữ." — số phút lấy từ setting, xem phần techlead).
11. **Không được.** Xoá không hỏi. Hiện số kg còn lại khi hết. Tính món hết vào tổng. Lưu tên khách/giá vốn vào giỏ.
12. **Code.** Mới `components/cart/CartLine.tsx` ⚠; bỏ phần giỏ trong `features/checkout/components/CheckoutScreen.tsx:178-260`.

## 20. CartSummary

1. **Công dụng.** Khối tóm tắt tiền và nút đi tiếp ở giỏ, đặt hàng, thanh toán. **Dùng ở:** `Cart`, `B3-CartChanged`, `Checkout`, `C2-Invalid`, `Payment`, `D2-PayCancelled`, `DesktopCart`, `DesktopCheckout`, `DesktopPayment`.
2. **Giải phẫu.** (a) tiêu đề (máy tính) · (b) danh sách món rút gọn (máy tính, bước đặt hàng) · (c) "Tạm tính" · (d) dòng "Giảm giá (mã …) −…" khi có (UI-RULES §2b) · (e) kẻ · (f) dòng tổng + câu "Đã gồm giao hàng. Bạn trả một lần, không trả thêm khi nhận hàng." ngay dưới (BR-BH-30) · (g) CTA. **Không** có dòng "Phí giao" và **không** có nút "Huỷ đơn" (chốt 10/10, BR-BH-28).
3. **Biến thể.** `context`: `cart` · `checkout` · `payment` · `payment-retry`. `layout`: `bar` (điện thoại, dính đáy) · `aside` (máy tính, cột phải dính).
4. **Kích thước và khoảng cách.**

| | `bar` (điện thoại) | `aside` (máy tính) |
|---|---|---|
| Vị trí | `position: fixed` đáy, + safe-area | `position: sticky; top: 24px` cột phải `flex: 1 1 300px` |
| Đệm | 14 16 16 (checkout/payment 12 16 16) | 20 |
| Khoảng dòng | 8 | 12 |
| CTA | `lg` 48 pill rộng đầy, cách tổng 4 | `lg` 48 pill rộng đầy |
| Trang phía trên | chừa `padding-bottom` bằng chiều cao bar | — |

5. **Token.** Nền `--surface`. `bar`: bóng `--shadow-bar`. `aside`: bo `--radius-card`, không bóng. Nhãn dòng body `--ink-2`. Tổng: nhãn 14/600 `--ink`, số PriceTag `total` 24/600 `--accent-text`. Kẻ 1px `--border`. Tiêu đề `aside` `title` 17/600.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | như token |
| hover / nhấn / focus | theo Button |
| disabled | `payment` khi đơn hết hạn (D4): CTA disabled `--surface-3` |
| đang tải | CTA "Đặt hàng" → "Đang đặt…" + Spinner; "Thanh toán" → `loadingText` `[copy]` |
| lỗi | lỗi gửi: Dialog C4 (giữ dữ liệu); hết hàng: Sheet C3 |
| chọn | không áp dụng |

7. **Hành vi.** `cart`: tổng = tổng món còn hàng; có món hết → nhãn "Tạm tính (2 món còn hàng)", CTA "Tiếp tục với 2 món còn hàng". `checkout`: CTA "Đặt hàng" submit form; gửi kèm `client_request_id` (sinh một lần khi mở form, giữ qua các lần "Thử lại") để không tạo đơn trùng (L-11). `payment`: tổng lấy **từ BE** (`total_amount`), không cộng lại ở FE. Không có dòng phí giao. Dòng giảm giá (nếu có) lấy số từ BE (BR-DM-19).
8. **Props.**

```ts
interface CartSummaryProps {
  context: 'cart' | 'checkout' | 'payment' | 'payment-retry';
  layout?: 'bar' | 'aside';               // theo breakpoint, container quyết
  itemCount: number;                      // số món
  availableCount?: number;                // < itemCount khi có món hết
  subtotal?: Money;                       // cart
  total: Money;                           // payment: từ BE
  lines?: { name: string; qtyText: string; amount: Money }[];   // aside ở checkout
  cta: { label: string; href?: string; onClick?: () => void; loading?: boolean; loadingText?: string; disabled?: boolean; form?: string };
  discount?: { code: string; amount: Money };                   // dòng giảm giá, số từ BE
}
```

9. **Truy cập.** `aside` có `aria-labelledby` tiêu đề. Tổng đổi (khi sửa giỏ) đọc qua vùng live của trang, không đặt `aria-live` trên cả khối. CTA `type="submit" form="checkout-form"` khi nằm ngoài form.
10. **Câu chữ.** "Tạm tính", "Giảm giá (mã …)", "Tổng tiền hàng", "Đã gồm giao hàng. Bạn trả một lần, không trả thêm khi nhận hàng." (BR-BH-30; dòng khu vực giao Phan Thiết (D 11/10); ranh giới và đơn ngoài vùng tạm theo `doc/ops/hoi-loc.md` L1–L2), "Tiếp tục: nhập thông tin nhận hàng" (điện thoại), "Tiếp tục" (máy tính), "Tóm tắt đơn", "Đơn hàng (3 món)", "3 món · tổng tiền hàng", "Đặt hàng", "Cần thanh toán", "Thanh toán", "Thanh toán lại".
11. **Không được.** Dòng "Phí giao", hiện phí giao bằng số hoặc "Miễn phí". Nút "Huỷ đơn". Tự tính tổng thanh toán ở FE. Hai CTA chính. Che nội dung trang (thiếu `padding-bottom`).
12. **Code.** Mới `components/cart/CartSummary.tsx` ⚠.

## 21. CartBar

1. **Công dụng.** Thanh dính đáy ở danh mục điện thoại: số món, tổng, "Xem giỏ". **Dùng ở:** `Main`, `A4-Toast`.
2. **Giải phẫu.** Một link lớn: (a) "N món · {tổng}" · (b) "Xem giỏ" + mũi tên.
3. **Biến thể.** Một biến thể; chỉ điện thoại (< `md`). Máy tính dùng MiniCart + badge header.
4. **Kích thước và khoảng cách.** Khung: đệm 8 16 16 + safe-area. Link cao 48, đệm 0 16, bo 8, hai đầu `space-between`. Có BottomNav thì CartBar nằm ngay trên BottomNav (Q-UX-6).
5. **Token.** Khung nền `--surface`, bóng `--shadow-bar`. Link nền `--accent`, chữ `--on-accent` 14/600, số `tabular-nums`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | hiện khi giỏ ≥ 1 món |
| hover | nền `--accent-hover` |
| nhấn | `scale(.97)` |
| focus-visible | viền trắng offset −4 |
| ẩn | giỏ 0 món |
| disabled / đang tải / lỗi / chọn | không áp dụng |

Xuất hiện: `translateY(100%)→0` 240ms `--ease-drawer`; reduced motion: hiện tức thì.
7. **Hành vi.** Link `/shop/cart/`. Số món = số dòng giỏ; tổng = tạm tính client (chỉ để xem, không phải số thanh toán). Trang chừa `padding-bottom` bằng cao bar (+ BottomNav).
8. **Props.**

```ts
interface CartBarProps { itemCount: number; subtotal: Money; href?: string /* '/shop/cart/' */ }
```

9. **Truy cập.** Tên link đọc liền: "3 món · 867.000đ · Xem giỏ". `z-index: var(--z-bottom-bar)`. Không bẫy focus.
10. **Câu chữ.** "{n} món · {tổng}", "Xem giỏ".
11. **Không được.** Hiện tổng kg. Hiện khi giỏ trống. Che Toast (Toast nằm trên bar).
12. **Code.** Mới `components/cart/CartBar.tsx` ⚠.

## 22. MiniCart

1. **Công dụng.** Popover giỏ nhanh (rộng 360, bóng `--shadow-pop`) nổi góc phải sau khi thêm món trên máy tính; **chỉ để xem nhanh, không sửa số lượng, không xoá món**. **Dùng ở:** `DesktopToast`.
2. **Giải phẫu.** (a) tiêu đề "Giỏ hàng (3 món)" + nút đóng · (b) danh sách dòng: ảnh 44, tên, số lượng, thành tiền · (c) "Tạm tính" + số · (d) "Xem giỏ".
3. **Biến thể.** Một biến thể; chỉ ≥ `md`.
4. **Kích thước và khoảng cách.** Rộng 360 (`max-width: calc(100% - 48px)`), đặt góc phải trong container dưới header, cùng cột với Toast (Toast trên, MiniCart dưới, cách 8). Đệm 16, gap 12. Dòng đệm 10 0, kẻ trên 1px.
5. **Token.** Nền `--surface`, viền `--border`, bo `--radius-card`, bóng `--shadow-pop`. Tiêu đề `section` 15/600 + số món 500 `--ink-3`. Số lượng `caption` `--ink-3`. Thành tiền 14/500. Tạm tính PriceTag `total`. Nút `primary` lg pill rộng đầy.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | mở sau khi thêm món |
| hover | nút đóng → nền `--surface-2`; nút "Xem giỏ" như Button |
| nhấn / focus-visible | như Button, IconButton |
| ẩn | đóng |
| disabled / đang tải / lỗi / chọn | không áp dụng |

Hiện: opacity + `translateY(-4px)→0` 180ms `--ease-out`.
7. **Hành vi.** Mở khi thêm món; **không lấy focus** (khách đang ở lưới). Đóng bằng nút X, Esc (khi focus ở trong), bấm ra ngoài, hoặc tự đóng sau 3 s nếu chuột/focus không ở trong (dừng đếm khi hover/focus). Thêm món khác khi đang mở: cập nhật nội dung, đếm lại.
8. **Props.**

```ts
interface MiniCartProps {
  open: boolean;
  onClose: () => void;
  lines: { itemCode: string; name: string; qtyText: string; amount: Money; group: GroupIcon; image?: ItemImage | null }[];
  itemCount: number;
  subtotal: Money;
  cartHref?: string;          // '/shop/cart/'
}
```

9. **Truy cập.** `<section aria-labelledby>` không modal. Nút đóng "Đóng giỏ hàng nhanh". Thông báo đã thêm đi qua Toast `role="status"`, MiniCart không có `aria-live` riêng.
10. **Câu chữ.** "Giỏ hàng (3 món)", "Tạm tính", "Xem giỏ".
11. **Không được.** Bẫy focus như dialog. Mở trên điện thoại. Hiện stepper/xoá trong giỏ nhanh (sửa ở trang giỏ).
12. **Code.** Mới `components/cart/MiniCart.tsx` ⚠.

---

# D. Đặt hàng và đơn

## 23. CheckoutSteps

1. **Công dụng.** Chỉ báo 3 bước: Giỏ hàng → Nhận hàng → Thanh toán. **Dùng ở:** `Cart`, `Checkout`, `C2-Invalid`, `Payment`, `D4-Expired`, `D6-LeavePayment`, `DesktopCart`, `DesktopCheckout`, `DesktopPayment`.
2. **Giải phẫu.** Điện thoại: mỗi bước = vạch + nhãn. Máy tính: chấm số + đường nối + nhãn.
3. **Biến thể.** `bar` (điện thoại) · `dots` (máy tính, đặt cạnh H1).
4. **Kích thước và khoảng cách.** `bar`: lưới 3 cột gap 6 → 8, đệm 12 16, vạch cao 4 bo 999, nhãn cách vạch 6. `dots`: chấm 28, đường nối 48×2, khoảng 10–12.
5. **Token.** Nền khối `--surface`. Nhãn `caption` 12/500 (máy tính 14/500). Xong: vạch/chấm `--accent`, chữ `--ink-2` (máy tính `--ink`). Hiện tại: vạch/chấm `--accent`, chữ `--accent-text` 600. Chưa tới: vạch `--surface-3`, chấm viền `--border-strong` nền `--surface`, chữ `--ink-3`. Số trong chấm 13/600 `--on-accent` (chưa tới: `--ink-3`).
6. **Trạng thái.** Tĩnh theo `current`. hover / nhấn / focus / disabled / đang tải / lỗi: không áp dụng (không bấm được). Chọn = bước hiện tại.
7. **Hành vi.** Không phải link (quay lại dùng nút header). Ở trang đơn sau khi trả tiền thì không hiện.
8. **Props.**

```ts
interface CheckoutStepsProps { current: 1 | 2 | 3; variant?: 'bar' | 'dots' /* theo breakpoint */ }
```

9. **Truy cập.** `<ol aria-label="Bước đặt hàng">`, bước hiện tại `aria-current="step"`, bước xong có chữ ẩn "(xong)".
10. **Câu chữ.** "1. Giỏ hàng", "2. Nhận hàng", "3. Thanh toán" (máy tính bỏ "1." vì đã có số trong chấm).
11. **Không được.** Biến thành link cho nhảy bước. Thêm bước thứ tư.
12. **Code.** Mới `components/cart/CheckoutSteps.tsx` ⚠.

## 24. HoldCountdown

1. **Công dụng.** Đồng hồ đếm ngược thời gian giữ hàng của đơn đang chờ thanh toán. **Dùng ở:** `Payment`, `D2-PayCancelled`, `D4-Expired` (00:00), `D6-LeavePayment` (giờ hết hạn), `DesktopPayment`, `DesktopPayCancelled`.
2. **Giải phẫu.** (a) dòng mã đơn · (b) dòng giải thích · (c) số mm:ss · (d) thanh tiến độ.
3. **Biến thể.** `created` (D1: "Đơn SO… đã được tạo" / "Cá Về đang giữ hàng cho bạn trong") · `retry` (D2: "Đơn SO… chưa thanh toán" / "Cá Về còn giữ hàng cho bạn trong") · `deadline` (D6: hiện giờ hết hạn "21:05", không đếm).
4. **Kích thước và khoảng cách.** Điện thoại: khối căn giữa, đệm 20 16, gap 6, bo 12, lề 16. Máy tính: khối ngang (chữ trái, số phải), đệm 24, gap 16 32, bo 12. Số 40/600 cả hai khổ (Q-UX-3). Thanh cao 4, bo 999, rộng đầy.
5. **Token.** Nền `--surface`. Dòng mã `label` 13/500 `--ink-2`, mã đơn 600 `--ink` `tabular-nums`. Dòng giải thích 13/400 `--ink-2`. Số `tabular-nums`, `letter-spacing: -0.015em`: > 5 phút `--accent-text`; ≤ 5 phút `--warn`; 00:00 `--crit`. Thanh: rãnh `--surface-3`, phần còn lại cùng màu số.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | đếm từng giây, màu `accent-text` |
| sắp hết (≤ 5 phút) | số và thanh `--warn` (đổi màu 150ms) |
| hết giờ | 00:00 `--crit`, thanh rỗng; CTA thanh toán disabled; mở Dialog D4 khi BE xác nhận |
| đang tải | chưa có `booked_expires_at`: Skeleton số |
| lỗi | mất mạng khi kiểm trạng thái: vẫn đếm theo giờ đã có |
| hover / nhấn / focus / disabled / chọn | không áp dụng |

7. **Hành vi.**
   - Tính từ `booked_expires_at` (BE) trừ giờ hiện tại; nếu BE trả `server_now` thì bù lệch giờ máy khách.
   - Tỉ lệ thanh = còn lại / tổng thời gian giữ; tổng lấy từ BE (contract cần bổ sung). Chưa có field thì **ẩn thanh**, không hard-code 30 phút.
   - Thanh co bằng `transform: scaleX()` (gốc trái), không animate `width`.
   - Tới 00:00: gọi lại tra đơn; chỉ mở D4 khi trạng thái là `AUTO_CANCELLED`; trong lúc chờ BE, nút thanh toán disabled kèm chữ `[copy]`.
   - Mốc 5 phút lấy từ UI-RULES §2.4 (là ngưỡng hiển thị, không phải luật nghiệp vụ).
8. **Props.**

```ts
interface HoldCountdownProps {
  orderCode: string;
  expiresAt: string;                 // ISO từ BE
  holdMinutes?: number;              // từ BE; thiếu thì ẩn thanh
  serverNow?: string;                // bù lệch giờ
  variant?: 'created' | 'retry' | 'deadline';   // 'created'
  warnBelowSeconds?: number;         // 300
  onExpire?: () => void;
}
```

9. **Truy cập.** Số `role="timer" aria-live="off"` (không đọc mỗi giây), `aria-label="Còn 18 phút 24 giây"` cập nhật mỗi phút. Một vùng `aria-live="polite"` riêng báo một lần ở mốc 5 phút và 1 phút `[copy]`. Màu đổi luôn kèm số.
10. **Câu chữ.** "Đơn SO… đã được tạo", "Cá Về đang giữ hàng cho bạn trong", "Đơn SO… chưa thanh toán", "Cá Về còn giữ hàng cho bạn trong", "Đơn SO… giữ hàng tới", "Thời gian giữ hàng còn lại".
11. **Không được.** Bắt đầu đếm khi thêm vào giỏ. Đếm theo giờ máy khách mà bỏ `expiresAt`. Hard-code "30 phút" hay 1800 giây. Đọc mỗi giây cho trình đọc màn hình. Animate `width`.
12. **Code.** Viết lại `components/CountdownTimer.tsx` thành `features/checkout/components/HoldCountdown.tsx` (giữ hàm `formatRemaining`).

## 25. PaymentMethod

1. **Công dụng.** Hiện phương thức thanh toán duy nhất: chuyển khoản Chuyển khoản ngân hàng. **Dùng ở:** `Payment`, `DesktopPayment`.
2. **Giải phẫu.** (a) tiêu đề "Phương thức thanh toán" · (b) thẻ: ô icon QR · tên · mô tả · dấu tích.
3. **Biến thể.** Một biến thể, chỉ đọc.
4. **Kích thước và khoảng cách.** Khối đệm 16, bo 12, gap 12. Thẻ đệm 12, gap 12, bo 10. Ô icon 40 bo 8, icon 22. Dấu tích 20.
5. **Token.** Thẻ: viền 2px `--accent`, nền `--accent-soft`. Ô icon nền `--surface`, icon `--accent-text`. Tên 14/600 `--ink`. Mô tả `caption` `--ink-2`. Dấu tích `--accent-text`.
6. **Trạng thái.** Luôn "đã chọn". hover / nhấn / focus / disabled / đang tải / lỗi: không áp dụng (không bấm được).
7. **Hành vi.** Không có lựa chọn khác nên **không** render radio. Nút "Thanh toán" nằm ở CartSummary `payment`; bấm thì gọi `POST /api/shop/orders/<code>/checkout/` rồi chuyển sang SePay; lỗi gọi API → Banner `crit` `[copy]` trên nút, giữ đồng hồ.
8. **Props.**

```ts
interface PaymentMethodProps { method?: 'vietqr_sepay' /* duy nhất */ }
```

9. **Truy cập.** Khối `<section aria-labelledby>`; thẻ là nội dung tĩnh, không `role="radio"`.
10. **Câu chữ.** "Phương thức thanh toán", "Chuyển khoản qua VietQR", "Quét mã bằng app ngân hàng bất kỳ, xác nhận tự động".
11. **Không được.** Thêm COD, ví, thẻ. Dựng radio một lựa chọn. Hiện số tài khoản ngân hàng ở đây (SePay lo).
12. **Code.** Mới `features/checkout/components/PaymentMethod.tsx`; thay `PaymentPanel.tsx`.

## 26. OrderTimeline

1. **Công dụng.** Dòng thời gian trạng thái đơn, có nhánh lỗi màu hổ phách. **Dùng ở:** `Success`, `E3-Delivered`, `E4-DeliveryFailed`, `D3-PayPending` (biến thể thanh toán), `DesktopSuccess`, `DesktopOrderStates`, `DesktopPayPending`.
2. **Giải phẫu.** Mỗi bước: (a) chấm · (b) đường nối · (c) nhãn · (d) dòng phụ (giờ, cách trả, việc đang làm).
3. **Biến thể.**

| `variant` | Bước | Hình |
|---|---|---|
| `order` | Đã đặt → Đã thanh toán → Đang chuẩn bị hàng → Đang giao → Đã giao | điện thoại dọc; máy tính ngang 5 cột |
| `payment` | Đặt đơn → Chờ ngân hàng → Thanh toán xong | 3 vạch ngang (như CheckoutSteps), vạch hiện tại nhấp nháy |

4. **Kích thước và khoảng cách.** Dọc: chấm 12 (bước lỗi 16), cột chấm rộng 12, chữ cách chấm 12, đường nối 2 rộng `min-height` 18, đệm dưới mỗi bước 8. Ngang (máy tính): chấm 24 có dấu tích 13, đường nối 2, gap chữ 10, đệm phải 8. `payment`: vạch 4, lưới 3 cột gap 6, chữ cách vạch 8.
5. **Token.** Xong: chấm/đường `--good`, nhãn 14/500 `--ink`. Hiện tại: chấm viền 3px `--accent` nền `--accent-soft` (ngang) / trong suốt (dọc), nhãn 600 `--accent-text`, đường sau `--border`. Chưa tới: chấm `--border-strong` (ngang: viền 2px `--border-strong` nền `--surface`), nhãn `--ink-3`. Lỗi: chấm `--warn` có dấu "!" trắng, đường trước `--warn`, nhãn 600 `--warn`. Dòng phụ `caption` `--ink-3`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | theo dữ liệu |
| đang tải | Skeleton 5 dòng |
| lỗi giao (E4) | bước "Đang giao" thành lỗi, dòng phụ "chưa giao được" |
| `payment` đang chờ | vạch giữa nhấp nháy opacity 1 → .35, chu kỳ 1.4s; reduced motion: đứng yên |
| hover / nhấn / focus / disabled / chọn | không áp dụng |

7. **Hành vi.** Dựng từ trạng thái đơn + `delivery.status` + mốc giờ (BE-5) qua hàm `buildOrderTimeline(order)` trong container. Thiếu mốc giờ thì ẩn giờ, không hiện "—". Đơn **đã huỷ không hiện timeline** (E2 dùng OrderStatusBadge + Banner). D3 tự kiểm lại mỗi 5 s (giữ nhịp code hiện có).
8. **Props.**

```ts
interface TimelineStep {
  key: 'placed' | 'paid' | 'preparing' | 'shipping' | 'delivered' | 'awaiting_bank';
  label: string;
  state: 'done' | 'current' | 'upcoming' | 'failed';
  detail?: string;          // "Kho đóng thùng giữ lạnh", "Chuyển khoản ngân hàng", "chưa giao được"
  time?: string;            // đã định dạng giờ Việt Nam
}
interface OrderTimelineProps {
  steps: TimelineStep[];
  variant?: 'order' | 'payment';               // 'order'
  orientation?: 'vertical' | 'horizontal';     // theo breakpoint
}
```

9. **Truy cập.** `<ol aria-label="Tiến trình đơn">`, bước hiện tại `aria-current="step"`. Mỗi bước có chữ ẩn trạng thái: "(đã xong)", "(đang làm)", "(chưa tới)", "(chưa giao được)". Màu không phải nguồn tin duy nhất.
10. **Câu chữ.** "Đã đặt", "Đã thanh toán", "Đang chuẩn bị hàng" (máy tính "Đang chuẩn bị"), "Đang giao", "Đã giao", "Kho đóng thùng giữ lạnh", "Chuyển khoản ngân hàng", "chưa giao được", "Đơn đã tạo, giữ hàng", "Đã nhận tiền". `payment`: "Đặt đơn", "Chờ ngân hàng", "Thanh toán xong", "Tự kiểm tra lại sau mỗi 5 giây", "Đã chờ 0:04".
11. **Không được.** Hiện người nhận, shipper, SĐT. Dùng đỏ cho giao thất bại. Bịa mốc giờ.
12. **Code.** Mới `features/checkout/components/OrderTimeline.tsx`.

## 27. OrderStatusBadge

1. **Công dụng.** Nhãn trạng thái đơn ngắn gọn cạnh tiêu đề "Trạng thái". **Dùng ở:** `Success`, `E2-Cancelled`, `E3-Delivered`, `E4-DeliveryFailed`, `D5-Underpaid`, `DesktopOrderStates`.
2. **Giải phẫu.** Chữ (không icon).
3. **Biến thể.** Năm tông (điều phối viên chốt), mỗi trạng thái hiển thị thuộc một tông:

| Tông | Nền / chữ | `status` → nhãn |
|---|---|---|
| `warn` | `--warn-soft` #FDF3E3 / `--warn` #A85A07 | `awaiting_payment` → "Chờ thanh toán" · `delivery_failed` → "Chưa giao được" |
| `neutral` | `--surface-3` #EBEBEF / `--ink-2` #4E4E58 | `awaiting_bank` → "Đang chờ xác nhận tiền" · `awaiting_review` → "Chờ cửa hàng xác nhận" |
| `accent` | `--accent-soft` #EBF2FE / `--accent-text` #1A5BC0 | `preparing` → "Đang chuẩn bị" · `shipping` → "Đang giao" |
| `good` | `--good-soft` #E9F7EE / `--good` #157F3D | `delivered` → "Đã giao" |
| `crit` | `--crit-soft` #FCEDEC / `--crit` #C0312B | `cancelled` → "Đã huỷ" |

Lưu ý so với màn: D5 vẽ "Chờ cửa hàng xác nhận" màu hổ phách → đổi sang `neutral`; E2 ghi "Đơn đã huỷ" → nhãn chuẩn "Đã huỷ". Bảng enum BE → `status` do techlead cấp (02b).
4. **Kích thước và khoảng cách.** Đệm 4 8, cao ≈ 24, bo `--radius-sm` 6 (cả hai khổ; E2 và D5 vẽ pill 999, thống nhất về 6).
5. **Token.** `caption` 12/600. Màu theo bảng.
6. **Trạng thái.** Tĩnh. hover / nhấn / focus / disabled / đang tải / lỗi / chọn: không áp dụng.
7. **Hành vi.** Map từ trạng thái BE trong container; component chỉ nhận khoá hiển thị.
8. **Props.**

```ts
type OrderDisplayStatus =
  | 'awaiting_payment' | 'delivery_failed'          // warn
  | 'awaiting_bank' | 'awaiting_review'             // neutral
  | 'preparing' | 'shipping'                        // accent
  | 'delivered'                                     // good
  | 'cancelled';                                    // crit
interface OrderStatusBadgeProps { status: OrderDisplayStatus }
```

9. **Truy cập.** Chữ là nội dung; không cần ARIA thêm.
10. **Câu chữ.** Như bảng.
11. **Không được.** Hiện mã enum thô (code cũ in `delivery.status` thô). Dùng chữ "hoàn tiền".
12. **Code.** Mới `features/checkout/components/OrderStatusBadge.tsx`.

## 28. OrderLines

1. **Công dụng.** Danh sách món trong đơn kèm tiền, dùng ở trang thanh toán và trang đơn. **Dùng ở:** `Payment`, `D2-PayCancelled`, `D4-Expired`, `Success`, `E2-Cancelled`, `E3-Delivered`, `E4-DeliveryFailed`, `DesktopSuccess`, `DesktopOrderStates`.
2. **Giải phẫu.** (a) tiêu đề ("Tóm tắt" hoặc "Món trong đơn") · (b) dòng: [ảnh 48 trên máy tính] tên · số lượng | tiền · (c) dòng "Giảm giá (mã …) −…" khi có · (d) dòng tổng. **Không** có dòng phí giao (chốt 10/10, BR-BH-30).
3. **Biến thể.** `summary` (thanh toán: chữ `--ink-2`, không dòng tổng vì tổng ở CartSummary) · `order` (có tổng "Đã thanh toán") · `cancelled` (chữ `--ink-3`, không tổng).
4. **Kích thước và khoảng cách.** Khối đệm 16 (máy tính 20 24), bo 12, gap 8. Dòng máy tính đệm 12 0, gap 14, kẻ dưới 1px. Tổng cách trên 8, kẻ trên 1px.
5. **Token.** Tên 14/400 (máy tính 14/500); số lượng `--ink-3` 400 `tabular-nums`; tiền 14/400–500 `tabular-nums`. Tổng: nhãn 14/600, số `total` 24/600 `--accent-text` (máy tính) hoặc 14/600 `--ink` (điện thoại, theo màn E1; giữ nhất quán: dùng 14/600 trên điện thoại vì nằm trong khối, không phải tổng chính của màn).
6. **Trạng thái.** Tĩnh. Đang tải: Skeleton 3 dòng. hover / nhấn / focus / disabled / lỗi / chọn: không áp dụng.
7. **Hành vi.** Dòng lấy từ BE (`lines` của đơn: `name`, `unit`, `qty`, `amount`), không từ giỏ client. Số lượng hiện theo đơn vị: "1 kg", "1,5 kg", "1 combo". Mua lại / Đặt lại dựng giỏ từ `lines` (container).
8. **Props.**

```ts
interface OrderLinesProps {
  title: string;                                      // "Tóm tắt" | "Món trong đơn"
  lines: { itemCode: string; name: string; unit: SaleUnit; qty: string; amount: Money; group?: GroupIcon; image?: ItemImage | null }[];
  variant?: 'summary' | 'order' | 'cancelled';        // 'order'
  total?: Money;
  totalLabel?: string;                                // "Đã thanh toán"
  showThumbs?: boolean;                               // máy tính true
  discount?: { code: string; amount: Money };         // dòng giảm giá, số từ BE
}
```

9. **Truy cập.** `<section aria-labelledby>` + `<ul>`. Có thể dùng `<dl>` cho dòng tổng.
10. **Câu chữ.** "Tóm tắt", "Món trong đơn", "Đã thanh toán", "Giảm giá (mã …)", "Tổng tiền hàng · đã thanh toán".
11. **Không được.** Hiện người nhận (tên, SĐT, địa chỉ) — **bỏ hẳn khối "Giao tới"** (Q1 đã chốt). Hiện giá vốn, mã lô.
12. **Code.** Mới `features/checkout/components/OrderLines.tsx`.

## 29. SuccessBanner

1. **Công dụng.** Banner xanh "Thanh toán thành công" trên đầu trang đơn ngay sau khi trả tiền. **Dùng ở:** `Success`, `DesktopSuccess`.
2. **Giải phẫu.** (a) vòng tròn có dấu tích · (b) tiêu đề · (c) một câu · (d) nút đóng.
3. **Biến thể.** Một biến thể; máy tính xếp ngang một dòng (tiêu đề · câu).
4. **Kích thước và khoảng cách.** Điện thoại: lề 12 16 0, đệm 14, gap 12, vòng 36. Máy tính: đệm 10 8 10 16, vòng 32. Nút đóng 44.
5. **Token.** Nền `--good-soft`, bo `--radius-card`; điện thoại không viền, máy tính viền 1px `--good-border` #BFE5CC. Vòng nền `--good`, dấu tích `--on-accent`. Tiêu đề 14/600 `--good`. Câu 13/400 `--ink` (máy tính `--good`). Nút đóng icon `--good`, hover nền `--surface` .
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | hiện khi về từ SePay `result=success` **và** đơn đã ghi nhận tiền |
| hover | nút đóng → nền `--surface` |
| nhấn / focus-visible | như IconButton |
| ẩn | sau khi bấm đóng |
| disabled / đang tải / lỗi / chọn | không áp dụng |

Hiện: opacity + `translateY(-8px)→0`, 200ms `--ease-out`; vòng tích: opacity + `scale(.96→1)` 180ms. Reduced motion: hiện tức thì.
7. **Hành vi.** `result=success` nhưng đơn còn chờ tiền → **không** hiện banner, hiện màn D3 (OrderTimeline `payment`). Đóng thì nhớ trong `sessionStorage` khoá `shop_paid_banner_dismissed` (giá trị: mã đơn, không có dữ liệu cá nhân). Tải lại trang không hiện lại sau khi đã đóng.
8. **Props.**

```ts
interface SuccessBannerProps { onDismiss: () => void; message?: string }
```

9. **Truy cập.** `role="status"` (đọc một lần). Không lấy focus; focus đầu trang là H1 "Đơn hàng SO…". Nút đóng `aria-label="Đóng thông báo thanh toán thành công"`.
10. **Câu chữ.** "Thanh toán thành công". Điện thoại: "Cá Về sẽ gọi xác nhận trước khi giao." Máy tính dùng **cùng câu đó**; bỏ ý "báo phí giao" (chốt 10/10: không thu thêm khi nhận hàng, BR-BH-30).
11. **Không được.** Hiện khi tiền chưa về. Thêm pháo hoa/confetti. Hiện người nhận.
12. **Code.** Mới `features/checkout/components/SuccessBanner.tsx`; gỡ khối tương ứng trong `OrderPaymentPanel.tsx`.

---

# E. Khung trang và điều hướng

## 30. ShopHeader

1. **Công dụng.** Header Shop theo ngữ cảnh: trang chủ, khi cuộn/danh mục, trang con, các bước đặt hàng; máy tính 2 tầng hoặc rút gọn. **Dùng ở:** `HeaderFooter-Mobile`, `HeaderFooter-Desktop`, mọi màn.
2. **Giải phẫu.**
   - H1 (điện thoại): LogoSlot + tagline · IconButton gọi · tra đơn · giỏ (badge) · SearchBox `brand`. **Không** có hàng Chip "Tìm nhiều" (chốt 10/10).
   - H2: LogoSlot · kính lúp (link `/shop/?focus=search`) · giỏ.
   - H3: quay lại · tiêu đề giữa · giỏ.
   - H4: quay lại · tiêu đề trái · nhãn "Bảo mật".
   - Máy tính `full`: dải trên (câu giới thiệu · "Cách mua hàng" · "Về Cá Về") · tầng chính (LogoSlot · SearchBox `brand` + "Tìm" · Hotline · Tra cứu đơn · Giỏ hàng + badge) · thanh menu nhóm (Cá · Tôm · Mực · Cua ghẹ · Combo · Góc bếp · … · Về Cá Về) + Popover nhóm con.
   - Máy tính `compact`: LogoSlot · vạch dọc · "Đặt hàng an toàn" · "Cần hỗ trợ? [hotline]".
3. **Biến thể.** `variant`: `home` (H1) · `sticky` (H2) · `sub` (H3) · `checkout` (H4). `desktopVariant`: `full` (Trang chủ, Danh mục, Chi tiết, Góc bếp, trang đơn, trang phụ) · `compact` (Giỏ, Đặt hàng, Thanh toán).
4. **Kích thước và khoảng cách.**

| | Điện thoại | Máy tính |
|---|---|---|
| H1 | đệm 8 16 14, gap 10; hàng logo 44; ô tìm 44 (thấp hơn ≈140 của màn vẽ vì bỏ hàng chip) | — |
| H2/H3/H4 | cao 56, đệm 0 6 (H2: 0 6 0 16) | — |
| `full` | — | dải trên 40 · tầng chính ≈76 (đệm 14 24, gap 24–28) · menu 48 |
| `compact` | — | cao 76, đệm 0 24, gap 24 |
| Nút hành động tầng chính | — | cao 44, đệm 0 12, bo 999, gap 8 |
| Link menu | — | cao 48, đệm 0 14 |

5. **Token.** H1 và tầng chính `full`: nền `--accent`; chữ/icon `--on-accent`; tagline và câu dải trên `--on-accent` (không dùng `on-brand-muted` trên `accent`, xem cảnh báo tương phản). Đường kẻ dưới dải trên `--accent-hover`. Nút "Tìm" `--brand-deep`. Badge trên nền `accent`: nền `--surface`, chữ `--accent-text`. H2/H3/H4/menu/`compact`: nền `--surface`, kẻ dưới 1px `--border`, icon `--ink`, tiêu đề H3 `section` 15/600, H4 `title` 17/600; badge nền `--accent`. Menu: link 14/500 `--ink`; hiện tại `--accent-text` 600 + gạch dưới trong `inset 0 -2px 0 var(--accent)`. "Bảo mật" và "Đặt hàng an toàn": icon khoá `--good`, chữ `caption` `--good` (máy tính 16/600 `--ink` → dùng `section` 15/600). Hotline tầng chính: nhãn "Hotline" `caption` `--on-accent`, số 600.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | nút tầng chính → nền `--accent-hover`; link menu → `--accent-text` + nền `--accent-soft`; link dải trên → nền `--accent-hover` |
| nhấn | `scale(.97)` |
| focus-visible | trên nền `accent`: viền trắng; trên nền trắng: viền `--focus` |
| chọn | link menu nhóm đang xem: `aria-current="page"`; "Tra cứu đơn" khi ở trang tra cứu: nền `--accent-hover` 600 |
| đang tải | danh sách nhóm chưa có: menu hiện Skeleton vạch chữ; hotline chưa có: ẩn nút gọi |
| disabled / lỗi | không áp dụng |

7. **Hành vi.**
   - Điện thoại trang chủ: H1 thu về H2 dính (`position: sticky; top: 0`) khi cuộn qua ô tìm (IntersectionObserver trên một phần tử đánh dấu). H2 xuất hiện `translateY(-100%)→0` 240ms `--ease-drawer`.
   - Máy tính `full`: **chỉ tầng chính dính**; dải trên và menu cuộn đi.
   - H3 quay lại: `history.back()`, không có lịch sử → `/shop/`. H4 quay lại → `/shop/cart/`. Trang thanh toán đơn đang giữ: quay lại và logo mở Dialog D6 "Rời trang thanh toán?" trước khi đi (`onBrandClick`/`onBack` chặn).
   - Menu nhóm máy tính: link "Cá" đi `/shop/?group=ca`; nhóm có nhóm con thì có nút mũi tên riêng mở Popover (hover hoặc bấm), Esc đóng. Chưa có dữ liệu nhóm con (L-20) thì không render nút mũi tên.
   - Badge = **số món**, ẩn khi 0.
   - Ô tìm H1 điện thoại là `trigger` (link tới `/shop/?focus=search`) theo `Home`.
8. **Props.**

```ts
interface NavGroup { slug: string; label: string; href: string; children?: { label: string; href: string }[] }
interface ShopHeaderProps {
  variant: 'home' | 'sticky' | 'sub' | 'checkout';
  desktopVariant?: 'full' | 'compact';            // 'full'
  title?: string;                                  // H3/H4
  backHref?: string;                               // H4: '/shop/cart/'
  onBack?: (e: React.MouseEvent) => void;          // chặn rời trang thanh toán
  onBrandClick?: (e: React.MouseEvent) => void;
  cartCount: number;                               // số món
  hotline?: string;
  groups?: NavGroup[];
  currentGroupSlug?: string;
  currentPath?: string;                            // để đặt aria-current
}
```

9. **Truy cập.** `<header>` landmark. Menu `<nav aria-label="Danh mục sản phẩm">`; dải nút `<nav aria-label="Tài khoản và giỏ">`. Nút mở menu con `aria-expanded aria-controls`. Link "Bỏ qua tới nội dung chính" là phần tử đầu trang (ẩn tới khi focus) `[copy]`. Logo `aria-label="Cá Về — trang chủ"`. "Bảo mật" là chữ, không phải nút.
10. **Câu chữ.** "Từ cảng về bếp nhà bạn", "Hải sản cấp đông theo lô · mua từ 1 kg · giao tận nhà" (số 1 kg lấy từ `min_qty`), "Cách mua hàng", "Về Cá Về", "Hotline", "Tra cứu đơn", "Giỏ hàng", "Tìm", "Góc bếp", "Xem tất cả cá →", "Bảo mật", "Đặt hàng an toàn", "Cần hỗ trợ? [hotline]", "Chi tiết sản phẩm", "Chi tiết combo", "Thông tin nhận hàng", "Thanh toán", "Tra cứu đơn hàng", "Chính sách", "Liên hệ", "Góc bếp".
11. **Không được.** Logo, giỏ hay menu ở H4. Badge tổng kg. Chạy chữ (marquee) ở dải trên. Header dính cả 3 tầng trên máy tính. `?nhom=` (dùng `?group=`, L-13).
12. **Code.** Viết lại `components/ShopHeader.tsx` (+ `ShopHeader.module.css`); link giỏ đổi từ `/shop/checkout` sang `/shop/cart/`; `CartProvider` chuyển lên `app/layout.tsx` (lô 1).

## 31. BottomNav

1. **Công dụng.** Thanh điều hướng đáy điện thoại: Trang chủ · Danh mục · Giỏ hàng · Đơn hàng. **Dùng ở:** `HeaderFooter-Mobile` (N1), `A0-Loading`, `F1-Lookup`, `F2-LookupNotFound`; trang Góc bếp.
2. **Giải phẫu.** 4 mục bằng nhau: icon 22 + nhãn; mục Giỏ có CartBadge.
3. **Biến thể.** Một biến thể; ẩn từ `md`.
4. **Kích thước và khoảng cách.** Cao 64 + `env(safe-area-inset-bottom)`, lưới 4 cột, icon cách nhãn 2. Trang có BottomNav chừa `padding-bottom` tương ứng.
5. **Token.** Nền `--surface`, bóng `--shadow-bar`. Nhãn `caption` 12/500 `--ink-2`, icon `--ink-2`. Mục hiện tại: icon `--accent`, nhãn `--accent-text` 600.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | như token |
| hover | không áp dụng (chỉ điện thoại) |
| nhấn | `scale(.97)` trên icon + nhãn |
| focus-visible | viền 2px `--focus` offset −4 trong ô |
| chọn | `aria-current="page"` + màu nhấn |
| disabled / đang tải / lỗi | không áp dụng |

7. **Hành vi.** Hiện ở Trang chủ, Danh mục, Góc bếp, Tra cứu đơn (D9, chốt 10/10). Ẩn ở Chi tiết, Giỏ, các bước đặt hàng, trang đơn sau thanh toán. Đích: `/`, `/shop/`, `/shop/cart/`, `/shop/orders/`. Badge giỏ = số món như header.
8. **Props.**

```ts
interface BottomNavProps { current: 'home' | 'catalog' | 'cart' | 'orders' | null; cartCount: number }
```

9. **Truy cập.** `<nav aria-label="Điều hướng chính">`. Mục Giỏ: tên "Giỏ hàng, 3 món". `z-index: var(--z-bottom-bar)`.
10. **Câu chữ.** "Trang chủ", "Danh mục", "Giỏ hàng", "Đơn hàng".
11. **Không được.** Hơn 4 mục. Hiện trên máy tính. Nhãn 11 px (dùng 12). Che nội dung cuối trang.
12. **Code.** Mới `frontend/components/BottomNav.tsx`.

## 32. ShopFooter

1. **Công dụng.** Chân trang đầy đủ (F1) và rút gọn (F2), gộp dải pháp lý người bán. **Dùng ở:** `HeaderFooter-Mobile`, `HeaderFooter-Desktop`, `Home`, `DesktopCategory`, `DesktopSuccess`, `G1-KitchenList`, trang phụ.
2. **Giải phẫu.**
   - F1: (a) LogoSlot + một câu giới thiệu · (b) nút "Gọi [hotline]" + "Nhắn Zalo" (điện thoại) / danh sách Hotline · Zalo · Email (máy tính) · (c) nhóm "Mua hàng" · (d) nhóm "Chính sách" (link từ CMS; đủ 6 trang go-live thì có "Cơ chế giải quyết khiếu nại", BR-ND-20) · (e) nhóm "Về Cá Về" · (f) dải pháp lý: tên doanh nghiệp · MST · địa chỉ · GCN ĐKKD · email · biểu tượng đã thông báo Bộ Công Thương (chỉ khi có link, D12) · ©.
   - F2: dải một hàng: tên DN · MST · © + 3 link chính sách.
3. **Biến thể.** `full` (F1) · `compact` (F2, Giỏ, Đặt hàng, Thanh toán).
4. **Kích thước và khoảng cách.**

| | Điện thoại | Máy tính |
|---|---|---|
| F1 khung | đệm 20 16, gap 4 | container 1200, đệm 40 24 28, lưới 1.4fr 1fr 1fr 1fr gap 32 |
| Nút gọi/Zalo | lưới 2 cột gap 8, cao 44 pill | không (dạng link) |
| Nhóm | `<details>` tóm tắt cao 48, link `min-height` 44 | tiêu đề cách list 10, link `min-height` 40 |
| Dải pháp lý | đệm trên 14, gap 6 | kẻ trên, đệm 18 24 24, hai đầu `space-between` |
| Logo Bộ Công Thương | 120×44 | 132×48 |
| F2 | đệm 16, xuống dòng | đệm 16 24, gap 8 24 |

5. **Token.** F1: nền `--brand-deep`, chữ `--on-brand-muted` body 14; logo/tên/tiêu đề nhóm `--on-accent` 600; link Link `on-brand`; đường kẻ `--accent-hover`; dải pháp lý `caption` 12. Nút "Gọi": Button `on-brand`; "Nhắn Zalo": `on-brand-outline`. F2: nền `--surface`, kẻ trên `--border`, chữ `caption` `--ink-2`, link `--accent-text`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | link F1 → `--on-accent` + gạch chân; link F2 → `--accent-hover` |
| nhấn | nút gọi/Zalo `scale(.97)` |
| focus-visible | F1 viền trắng; F2 viền `--focus` |
| chọn | link trang đang xem `aria-current="page"` (vd. "Góc bếp") |
| mở/đóng nhóm (điện thoại) | mũi tên xoay 180° 150ms; "Mua hàng" mở sẵn |
| đang tải | `site-info` chưa có: ẩn dòng thiếu, không hiện chữ chờ `[…]` |
| disabled / lỗi | không áp dụng |

7. **Hành vi.** Nhóm "Chính sách" render từ CMS footer-links (`GET /api/public/content/footer-links/`), link dạng `/trang/?slug=` (L-13). Thông tin người bán từ `site-info.seller`. Zalo từ BE-7; chưa có thì ẩn nút/dòng Zalo. Logo Bộ Công Thương chỉ hiện khi có link xác nhận (mở tab mới). Năm © = `currentYearInVietnam()`. F2: link chính sách mở **tab mới** (không mất đơn đang điền). Điện thoại ở Giỏ/Đặt hàng/Thanh toán: dùng F2.
8. **Props.**

```ts
interface ShopFooterProps {
  variant?: 'full' | 'compact';                    // 'full'
  seller: { name: string; taxCode: string; address: string; businessLicense?: string; email?: string };
  hotline?: string;
  zaloUrl?: string;
  policyLinks: { label: string; href: string }[];
  bctVerifyUrl?: string;
  currentPath?: string;
}
```

9. **Truy cập.** `<footer>`; mỗi nhóm máy tính là `<nav aria-labelledby>` với tiêu đề h2. Điện thoại dùng `<details>/<summary>` gốc. Link tab mới có chữ ẩn "(mở tab mới)".
10. **Câu chữ.** "Hải sản cấp đông theo lô, giá tính theo kg, giao tận nhà.", "Gọi [hotline]", "Nhắn Zalo", "Mua hàng": "Hàng đang có", "Combo nấu nhanh", "Cách mua hàng", "Tra cứu đơn"; "Chính sách": "Chính sách đổi trả và hoàn tiền", "Chính sách giao hàng", "Chính sách thanh toán", "Chính sách quyền riêng tư", "Điều kiện giao dịch chung" (trang `terms`, không ghi "Điều khoản sử dụng"; chốt 07/10, 10/10), "Cơ chế giải quyết khiếu nại" (tên link lấy từ CMS); "Về Cá Về": "Giới thiệu", "Góc bếp", "Liên hệ"; "MST", "Địa chỉ:", "GCN ĐKKD số … do … cấp ngày …", "Email:", "© 2026 Cá Về".
11. **Không được.** Hard-code link chính sách khi CMS đã có. Hiện chữ chờ `[…]` trên production. Widget chat bên thứ ba. Form liên hệ. Hard-code năm.
12. **Code.** Viết lại `components/ShopFooter.tsx`; gộp `features/site/components/SiteLegalFooter.tsx` (gỡ khỏi `app/layout.tsx:23`).

## 33. Breadcrumb

1. **Công dụng.** Đường dẫn vị trí trang. **Dùng ở:** `DesktopCategory`, `DesktopProduct`, `DesktopOutOfStock`, `DesktopToast`, `DesktopPolicy`, `DesktopContact`, `DesktopKitchenList`, `P1-Policy` (điện thoại).
2. **Giải phẫu.** `<ol>`: link · dấu "/" · … · trang hiện tại (chữ).
3. **Biến thể.** Một biến thể; điện thoại chỉ dùng ở trang chính sách (trang khác đã có H3).
4. **Kích thước và khoảng cách.** Gap 6 (điện thoại 4), xuống dòng khi dài. Máy tính cách nội dung dưới 14. Link điện thoại có đệm dọc để vùng chạm ≥ 44.
5. **Token.** Máy tính `label` 13/400; điện thoại `caption` 12/500. Link `--ink-2`; "/" `--ink-3`; hiện tại `--ink` 500.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | link → `--accent-text` + gạch chân |
| focus-visible | viền 2px `--focus` |
| chọn | mục cuối `aria-current="page"` |
| nhấn / disabled / đang tải / lỗi | không áp dụng |

7. **Hành vi.** Mục cuối không là link. Tên dài cắt 1 dòng có "…" trên máy tính (`text-overflow`), trình đọc vẫn đọc đủ.
8. **Props.**

```ts
interface BreadcrumbProps { items: { label: string; href?: string }[] }   // phần tử cuối là trang hiện tại
```

9. **Truy cập.** `<nav aria-label="Đường dẫn">`, dấu "/" `aria-hidden`.
10. **Câu chữ.** "Trang chủ", "Hàng đang có", "Chính sách", tên nhóm, tên món.
11. **Không được.** Dùng breadcrumb thay nút quay lại trên điện thoại. Đặt link ở mục cuối.
12. **Code.** Mới `frontend/components/ui/Breadcrumb.tsx`.

## 34. SideFilter

1. **Công dụng.** Cột lọc nhóm hàng có đếm món trên máy tính. **Dùng ở:** `DesktopCategory`, `DesktopToast`, `DesktopNotFound`, `DesktopLoading`, `DesktopOffline`.
2. **Giải phẫu.** (a) khối: tiêu đề "Danh mục" + danh sách mục (tên + số món) · (b) khối luật mua bên dưới.
3. **Biến thể.** Một biến thể; chỉ ≥ `md`. Điện thoại dùng hàng Chip.
4. **Kích thước và khoảng cách.** Cột `flex: 1 1 220px`. Khối đệm 16 12, bo 12, mục `min-height` 44, đệm 0 10, gap 2. Số món: `min-width` 24, cao 22, đệm 0 7, bo 999. Khối luật đệm 14 16, bo 12, cách khối trên 12.
5. **Token.** Khối nền `--surface`. Tiêu đề `section` 15/600. Mục tắt: 14/500 `--ink`, nền trong suốt; số món nền `--surface-2` chữ `--ink-2` `caption` 600. Mục bật: nền `--accent-soft`, chữ `--accent-text` 600; số món nền `--accent` chữ `--on-accent`. Khối luật: nền `--accent-soft`, chữ `label` 13/500 `--accent-text`, icon 18.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | mục tắt → nền `--surface-2` |
| nhấn | `scale(.97)` |
| focus-visible | viền 2px `--focus` |
| chọn | như "bật", `aria-current="page"` |
| đang tải | Skeleton 6 vạch |
| disabled / lỗi | không áp dụng |

7. **Hành vi.** Mục là **link** đổi URL `/shop/?group=` (giữ `q` và `sort`), không là nút `aria-pressed` như file màn, để Back và chia sẻ link đúng. Số món đếm ở FE. Câu luật dựng từ `min_qty`/`qty_step` của catalog.
8. **Props.**

```ts
interface SideFilterProps {
  groups: { slug: string | 'all'; label: string; count: number; href: string }[];
  currentSlug: string | 'all';
  rulesText?: string;
}
```

9. **Truy cập.** `<aside aria-labelledby>` + `<nav>`. Tiêu đề trang (`h1` "Cá · 5 món") đổi theo lọc; vùng `role="status"` đọc "{n} món".
10. **Câu chữ.** "Danh mục", "Tất cả hải sản", tên nhóm. Luật: "Giá tính theo kg. Mua tối thiểu 1 kg, tăng từng 0,5 kg. Combo tính theo combo."
11. **Không được.** Dùng checkbox nhiều lựa chọn (màn chọn một). Đếm kg.
12. **Code.** Mới `components/catalog/SideFilter.tsx` ⚠.

## 35. SortControl

1. **Công dụng.** Đổi thứ tự danh sách: Mặc định · Giá thấp đến cao · Giá cao đến thấp. **Dùng ở:** `Main`, `A4-Toast` (điện thoại); `DesktopCategory` (máy tính).
2. **Giải phẫu.** Điện thoại: (a) đếm "N sản phẩm" bên trái · (b) nút "Sắp xếp: …" + mũi tên bên phải → BottomSheet danh sách lựa chọn. Máy tính: SegmentedControl.
3. **Biến thể.** `sheet` (< `md`) · `segmented` (≥ `md`).
4. **Kích thước và khoảng cách.** Điện thoại: hàng đệm 0 16 4; nút cao 44, đệm 0 4, icon 14 cách chữ 4. Sheet: mỗi lựa chọn cao 48. Máy tính: như SegmentedControl, cạnh `h1` trong khối đệm 10 12 10 18, bo 12.
5. **Token.** Đếm `label` 13 `--ink-2` (số `tabular-nums`). Nút: `label` 13/500 `--ink-2`, nền trong suốt. Lựa chọn trong sheet: body 14 `--ink`; đang chọn: 600 `--accent-text` + dấu tích.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | nút → `--ink` |
| nhấn | `scale(.97)` |
| focus-visible | viền 2px `--focus` |
| chọn | lựa chọn hiện tại có dấu tích và `aria-checked="true"` |
| disabled / đang tải / lỗi | không áp dụng |

7. **Hành vi.** Giá trị trong URL `?sort=default|price_asc|price_desc`. Chọn trong sheet là áp dụng ngay và đóng sheet, focus về nút. Món hết luôn ở cuối.
8. **Props.**

```ts
type SortValue = 'default' | 'price_asc' | 'price_desc';
interface SortControlProps { value: SortValue; onChange: (v: SortValue) => void; resultCount: number }
```

9. **Truy cập.** Nút `aria-haspopup="dialog" aria-expanded`. Sheet chứa `<fieldset>` radio gốc. Nhãn đầy đủ cho trình đọc: "Sắp xếp theo giá thấp đến cao".
10. **Câu chữ.** "Sắp xếp: Mặc định", "Sắp xếp: Giá ↑", "Sắp xếp: Giá ↓" (nút điện thoại); "Mặc định", "Giá thấp đến cao", "Giá cao đến thấp" (sheet và máy tính); "{n} sản phẩm".
11. **Không được.** Dùng `<select>` gốc (lệch thiết kế, khó chạm). Đưa món hết lên đầu khi sắp xếp giá.
12. **Code.** Mới `components/catalog/SortControl.tsx` ⚠.

## 36. PolicyNav

1. **Công dụng.** Điều hướng giữa các trang chính sách và mục lục trong trang. **Dùng ở:** `P1-Policy`, `P3-HowToBuy`, `DesktopPolicy`.
2. **Giải phẫu.** (a) Mục lục trong trang (link neo) · (b) danh sách "Các chính sách" (điện thoại, cuối trang) hoặc cột trái "Chính sách" (máy tính) · (c) link "Cách mua hàng" (máy tính, dưới kẻ).
3. **Biến thể.** `toc` (mục lục) · `list` (điện thoại) · `aside` (máy tính, dính).
4. **Kích thước và khoảng cách.** `toc`: khối đệm 8 12, bo 10, link `min-height` 44, gap icon 8. `list`: đệm 12 16, dòng `min-height` 44 kẻ dưới. `aside`: `flex: 1 1 240px`, `position: sticky; top: 24px`, đệm 16 12, bo 12, mục 44 đệm 0 12 bo 8, gap 2.
5. **Token.** `toc`: nền `--surface-2`, tiêu đề 13/600 `--ink-3`, link `--accent-text`. `list`: nền `--surface`, tiêu đề `section` 15/600; mục hiện tại `--ink` 600 + "Đang xem" `caption` `--ink-3`; mục khác `--accent-text` 500 + mũi tên `--ink-3`. `aside`: nền `--surface`; mục 14/500 `--ink`; hiện tại nền `--accent-soft` chữ `--accent-text` 600.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | `aside` mục → nền `--surface-2`; link → gạch chân |
| focus-visible | viền 2px `--focus` |
| chọn | `aria-current="page"` |
| đang tải | Skeleton 5 vạch |
| nhấn / disabled / lỗi | không áp dụng |

7. **Hành vi.** Danh sách từ CMS (footer-links), link `/trang/?slug=`. Mục lục sinh từ các `h2` có `id` trong nội dung; tiêu đề có `scroll-margin-top` = cao header + 8. Mục là `<a>`, không là `<button>` như `DesktopPolicy`.
8. **Props.**

```ts
interface PolicyNavProps {
  policies: { slug: string; label: string; href: string }[];
  currentSlug: string;
  toc?: { id: string; label: string }[];
  extraLinks?: { label: string; href: string }[];   // "Cách mua hàng"
  variant: 'toc' | 'list' | 'aside';
}
```

9. **Truy cập.** `<nav aria-labelledby>` cho từng khối. Mục lục là `<ol>`.
10. **Câu chữ.** "Mục lục", "Các chính sách", "Chính sách", "Đang xem", "Cách mua hàng", tên 5 chính sách.
11. **Không được.** Dùng button cho mục điều hướng. Hard-code danh sách khi CMS có. Hiện nhãn "[Nội dung chờ legal-vn duyệt]" trên production.
12. **Code.** Mới `features/site/components/PolicyNav.tsx`.

## 37. LogoSlot

1. **Công dụng.** Chỗ logo + chữ "Cá Về", chờ Duy upload file logo. **Dùng ở:** header H1/H2, `compact`, footer F1, `Landing`.
2. **Giải phẫu.** (a) ảnh logo (khi có) · (b) chữ "Cá Về" · (c) tagline (chỉ H1).
3. **Biến thể.** `size`: 28 (H2) · 30 (H1 điện thoại) · 36 (`compact`, footer máy tính) · 40 (H1 máy tính). `tone`: `light` (nền trắng) · `brand` (nền `accent` hoặc `brand-deep`).
4. **Kích thước và khoảng cách.** Ảnh vuông theo `size`, bo 8, cách chữ 8 (≥36: 10). Chữ: 17/600 (điện thoại), `display` 24/600 (H1 máy tính), 20 → `title` 17/600 cho `compact` và footer điện thoại; tagline `caption` 12.
5. **Token.** `light`: chữ `--brand-deep`. `brand`: chữ `--on-accent`; tagline `--on-accent` (trên `accent`) hoặc `--on-brand-muted` (trên `brand-deep`).
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| hover | không đổi màu (đã là link logo) |
| nhấn | `scale(.97)` |
| focus-visible | viền 2px theo nền |
| đang tải | ảnh có `width`/`height` cố định, không nhảy |
| lỗi | ảnh hỏng → chỉ còn chữ "Cá Về" |
| disabled / chọn | không áp dụng |

7. **Hành vi.** **Chưa có file logo: chỉ hiện chữ "Cá Về"**; không render ô nét đứt "LOGO" của file thiết kế. Có file: đặt ở `frontend/public/`, `<img>` có `width`/`height` (static export). Link `/` (trang thanh toán: chặn bằng D6).
8. **Props.**

```ts
interface LogoSlotProps {
  size?: 28 | 30 | 36 | 40;        // 28
  tone?: 'light' | 'brand';        // 'light'
  showTagline?: boolean;           // false
  src?: string;                    // undefined: chỉ chữ
  href?: string;                   // '/'
  onClick?: (e: React.MouseEvent) => void;
}
```

9. **Truy cập.** Link `aria-label="Cá Về — trang chủ"`; ảnh bên trong `alt=""`.
10. **Câu chữ.** "Cá Về", "Từ cảng về bếp nhà bạn".
11. **Không được.** Dùng chữ `cangca` hay "Lộc". Gradient/glow cho logo. Để ô "LOGO" trên production.
12. **Code.** Mới `frontend/components/LogoSlot.tsx`.

---

# F. Lớp phủ và phản hồi

## 38. Dialog

1. **Công dụng.** Hộp thoại giữa màn cho xác nhận và thông báo chặn. **Dùng ở:** `B2-RemoveConfirm`, `C4-NetworkError`, `C5-LocationDenied`, `D4-Expired`, `D6-LeavePayment`, `DesktopRemoveConfirm`, `DesktopNetworkError`, `DesktopLeavePayment`, `DesktopModalExpired`, `DesktopModalSoldOut` (máy tính của C3).
2. **Giải phẫu.** (a) lớp phủ · (b) hộp: [ô icon tròn] · tiêu đề · mô tả · [nội dung thêm] · hàng nút · [nút X trên máy tính] · [ghi chú nhỏ cuối, chỉ D4].
3. **Biến thể.**

| `kind` | Bố cục | Ví dụ |
|---|---|---|
| `confirm` | chữ trái, 2 nút chia đôi | B2 bỏ món |
| `alert` | ô icon tròn trên, chữ giữa, nút xếp dọc rộng đầy | C4, C5, D4, D6 |

`tone` của ô icon: `neutral` (`surface-2`/`ink-2`, C4) · `info` (`accent-soft`/`accent-text`, D6) · `warn` (`warn-soft`/`warn`, C5) · `crit` (`crit-soft`/`crit`, D4). `size`: `sm` 440 · `md` 480 (máy tính, nội dung có danh sách).
4. **Kích thước và khoảng cách.**

| | Điện thoại | Máy tính |
|---|---|---|
| Rộng | `calc(100% - 48px)` (lề 24) | 440 / 480, `max-width: calc(100% - 32px)` |
| Đệm | confirm 20; alert 24 20 16 (D4/D6: 24 20 20) | 24 (alert: 28/32 24 24) |
| Gap | 8–10 | confirm 20 giữa khối chữ và nút; alert 8–12 |
| Ô icon | 52–56 | 52–56 |
| Nút | confirm: md 44 bo 8, lưới 2 cột gap 10 → 12; alert: lg 48 pill + phụ md 44, xếp dọc gap 8 | lg 48 pill, confirm lưới 2 cột gap 10 → 12 |
| Nút X | không có | 44, góc trên phải |

5. **Token.** Lớp phủ `--overlay`. Hộp nền `--surface`, bo `--radius-xl` 14, bóng `--shadow-modal`. Tiêu đề `title` 17/600 (file máy tính 19 → 17). Mô tả body `--ink-2`; mã đơn trong mô tả 600 `--ink` `tabular-nums`. Ghi chú cuối `caption` `--ink-3`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mở | lớp phủ fade 200ms; hộp opacity 0→1 + `scale(.96→1)` 200ms `--ease-out`; reduced motion: chỉ fade |
| đóng | đảo lại, 150ms |
| hover / nhấn / focus | theo Button, IconButton |
| đang tải | nút chính có `loading` ("Thử lại" khi đang gửi lại); không đóng được khi đang gửi |
| lỗi | gửi lại vẫn lỗi: giữ Dialog, đổi mô tả không cần; Spinner tắt |
| disabled / chọn | không áp dụng |

7. **Hành vi.**
   - Dùng `<dialog>` gốc + `showModal()`: nền tự `inert`, Esc phát sự kiện `cancel`.
   - Mở: lưu `document.activeElement`; focus vào nút **ít rủi ro nhất** ("Giữ lại", "Ở lại thanh toán", "Thử lại") hoặc vào tiêu đề (`tabindex="-1"`) khi nội dung cần đọc trước. Đóng: trả focus về phần tử đã lưu.
   - Khoá cuộn trang khi mở (`overflow: hidden` trên `html`, `scrollbar-gutter: stable` để không giật).
   - Bấm lớp phủ: đóng nếu `dismissible` (B2, D6, C5); D4 không có đóng bằng lớp phủ (thông báo bắt buộc đọc), vẫn đóng bằng Esc/nút.
   - Máy tính luôn có nút X (UI-RULES §5.2).
   - Phá huỷ: nút `danger` bên phải, nút giữ lại bên trái; focus mặc định ở nút giữ lại.
8. **Props.**

```ts
interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: React.ReactNode;
  kind?: 'confirm' | 'alert';                       // 'confirm'
  icon?: { name: IconName; tone: 'neutral' | 'info' | 'warn' | 'crit' };
  actions: React.ReactNode;                         // các Button
  footnote?: React.ReactNode;                       // D4
  size?: 'sm' | 'md';                               // 'sm'
  dismissible?: boolean;                            // true
  closeLabel?: string;                              // aria-label nút X (máy tính)
  initialFocusRef?: React.RefObject<HTMLElement>;
  busy?: boolean;                                   // false: true thì chặn đóng
  children?: React.ReactNode;
}
```

9. **Truy cập.** `role="dialog"` (ngầm từ `<dialog>`), `aria-modal="true"`, `aria-labelledby` tiêu đề, `aria-describedby` mô tả. Giữ focus bên trong, Esc đóng, trả focus về nút mở. Ô icon `aria-hidden`.
10. **Câu chữ.** B2: "Bỏ {tên} khỏi giỏ?" / "Mỗi món mua tối thiểu 1 kg. Bớt nữa sẽ bỏ món này khỏi giỏ." / "Giữ lại" / "Bỏ khỏi giỏ"; X "Đóng, giữ lại {tên}". C4: "Chưa gửi được đơn" / "Đơn chưa được tạo. Kiểm tra mạng rồi thử lại." / "Thử lại" / "Để sau". C5: xem AddressField. D4: "Hết thời gian giữ hàng" / "Đơn SO… đã tự huỷ sau 30 phút chưa thanh toán. Hàng đã trả lại kho, bạn chưa bị trừ tiền." (số phút từ BE) / "Đặt lại đơn này" / "Về trang chủ" / ghi chú "Đã chuyển khoản rồi? Liên hệ [hotline], Cá Về sẽ kiểm tra và gọi lại cho bạn." D6: "Rời trang thanh toán?" / "Đơn SO… vẫn được giữ tới hết 21:05. Bạn có thể quay lại thanh toán từ Tra cứu đơn." / "Ở lại thanh toán" / "Rời trang".
11. **Không được.** Mở dialog cho phản hồi nhanh (dùng Toast). Hai lớp dialog chồng nhau (C5 mở từ MapPicker: đóng sheet hoặc đặt C5 trong sheet, không chồng hai modal cùng cấp). Dùng `window.confirm`. Dùng chữ "hoàn tiền".
12. **Code.** Mới `frontend/components/ui/Dialog.tsx` + `useReturnFocus.ts`.

## 39. BottomSheet

1. **Công dụng.** Tấm trượt từ đáy trên điện thoại cho danh sách lựa chọn và thông báo có danh sách; máy tính tự thành Dialog. **Dùng ở:** `C3-SoldOut` (máy tính: `DesktopModalSoldOut`), sheet sắp xếp (SortControl).
2. **Giải phẫu.** (a) lớp phủ · (b) tấm: thanh kéo · [ô icon] · tiêu đề · mô tả · nội dung (danh sách) · nút.
3. **Biến thể.** `list` (lựa chọn, vd. sắp xếp) · `notice` (C3: icon + danh sách món + 2 nút).
4. **Kích thước và khoảng cách.** Điện thoại: dính đáy, rộng đầy, bo trên 16, đệm 8 16 20 + safe-area; thanh kéo 36×4 cách nội dung 16; `max-height: calc(100dvh - 24px)`, nội dung cuộn bên trong. C3: ô icon 44 cách tiêu đề 12; danh sách viền 1px bo 12, dòng đệm 12 gap 12, ảnh 44; nút lg 48 pill, cách 16 và 8. Máy tính (≥ `md`): Dialog `md` 480 có nút X.
5. **Token.** Lớp phủ `--overlay`. Tấm nền `--surface`, bo `--radius-sheet`, bóng `--shadow-bar`. Thanh kéo `--border-strong` bo 999. Tiêu đề `title` 17/600 (file 18 → 17). Danh sách C3: viền `--border`; dòng "không đủ hàng" `--warn` 600; dòng "Đã hết · sẽ bỏ khỏi đơn" `--ink-2` 600; ảnh món hết `opacity: .5`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mở | `translateY(100%)→0` 260ms `--ease-drawer`; lớp phủ fade; reduced motion: fade |
| đóng | trượt xuống 240ms |
| hover / nhấn / focus | theo phần tử bên trong |
| đang tải | "Cập nhật giỏ và đặt lại": Button `loading` |
| lỗi | đặt lại vẫn hết hàng: nội dung sheet cập nhật theo lỗi mới |
| disabled / chọn | `list`: lựa chọn đang chọn có dấu tích |

7. **Hành vi.** Đóng bằng: nút trong sheet, Esc, chạm lớp phủ. Kéo xuống để đóng là tuỳ chọn (không bắt buộc ở V1); thanh kéo chỉ là gợi ý hình. C3: mở khi BE trả lỗi `OUT_OF_STOCK` có cấu trúc (BE-3); dòng `short` có nút "Đổi thành 1 kg" (= `min_qty`, không suy ra tồn), dòng `out` có "Liên hệ chúng tôi". "Cập nhật giỏ và đặt lại" áp các thay đổi vào giỏ rồi gửi lại với một `client_request_id` **mới** (giỏ đã khác, đơn trước chưa được tạo); "Quay lại giỏ hàng" về `/shop/cart/`.
8. **Props.**

```ts
interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: React.ReactNode;
  icon?: { name: IconName; tone: 'warn' | 'info' | 'neutral' };
  children?: React.ReactNode;
  actions?: React.ReactNode;
  initialFocus?: 'title' | 'first-action';   // 'title'
  closeLabel?: string;                       // nút X khi thành Dialog trên máy tính
}
```

9. **Truy cập.** Như Dialog: `role="dialog" aria-modal="true"`, giữ focus, Esc, trả focus. Thanh kéo `aria-hidden`. Tiêu đề nhận focus đầu (`tabindex="-1"`) để trình đọc đọc tình huống trước nút.
10. **Câu chữ.** C3: "Một số món vừa hết hàng" / "Có khách vừa đặt trước bạn." / "Bạn đặt 2 kg · không đủ hàng" / "Đổi thành 1 kg" / "Đã hết · sẽ bỏ khỏi đơn" / "Liên hệ chúng tôi" / "Cập nhật giỏ và đặt lại" / "Quay lại giỏ hàng". Máy tính X: "Đóng thông báo hết hàng".
11. **Không được.** Hiện số kg còn lại ("còn 1 kg"), mã lô hay chuỗi lỗi thô của server. Dùng sheet cho xác nhận phá huỷ (dùng Dialog). Thiếu cách đóng không cần kéo.
12. **Code.** Mới `frontend/components/ui/Sheet.tsx` (export `BottomSheet`).

## 40. FullscreenSheet

1. **Công dụng.** Tấm gần toàn màn cho tác vụ dài có thanh đầu và chân riêng (chọn vị trí bản đồ). **Dùng ở:** `C1b-MapPicker`, `DesktopMapPicker`.
2. **Giải phẫu.** (a) lớp phủ · (b) thanh đầu: nút đóng X (trái) + tiêu đề · (c) thân co giãn · (d) chân cố định.
3. **Biến thể.** Một biến thể; máy tính thành hộp thoại lớn.
4. **Kích thước và khoảng cách.** Điện thoại: `top: 24px`, đáy 0, rộng đầy, bo trên 16; thanh đầu 56, đệm 0 6, kẻ dưới; chân đệm 14 16 16 + safe-area, kẻ trên. Máy tính: `min(960px, 100vw - 48px)` × `min(640px, 100dvh - 48px)`, căn giữa, bo 14.
5. **Token.** Lớp phủ `--overlay`. Nền `--surface`. Điện thoại bo `--radius-sheet`; máy tính bo `--radius-xl`, bóng `--shadow-modal`. Tiêu đề `title` 17/600 (file 16 → 17). Kẻ `--border`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mở | điện thoại `translateY(100%)→0` 260ms `--ease-drawer`; máy tính opacity + `scale(.96→1)` 200ms |
| đóng | đảo lại |
| đang tải | thân hiện Skeleton (do nội dung quyết) |
| hover / nhấn / focus / lỗi / disabled / chọn | theo nội dung |

7. **Hành vi.** Như Dialog (`<dialog>` + `showModal()`), Esc và X đóng. Chạm lớp phủ không đóng (tác vụ dài, tránh mất thao tác). Nút X đặt bên trái trên điện thoại (theo C1b), bên phải trên máy tính.
8. **Props.**

```ts
interface FullscreenSheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  closeLabel: string;                 // "Đóng, quay lại nhập tay"
  footer?: React.ReactNode;
  initialFocusRef?: React.RefObject<HTMLElement>;
  children: React.ReactNode;
}
```

9. **Truy cập.** `aria-modal`, `aria-labelledby` tiêu đề, giữ focus, trả focus về nút mở.
10. **Câu chữ.** "Chọn vị trí giao hàng", "Đóng, quay lại nhập tay".
11. **Không được.** Dùng cho thông báo ngắn. Phủ kín cả status bar trên điện thoại (chừa 24).
12. **Code.** Mới `frontend/components/ui/FullscreenSheet.tsx`.

## 41. Dropdown/Popover

1. **Công dụng.** Lớp nổi neo dưới một phần tử, **không modal**: menu nhóm con, gợi ý tìm kiếm, giỏ nhanh. **Dùng ở:** `HeaderFooter-Desktop` (nhóm con "Cá"), `A8-SearchSuggest`, `DesktopSearchSuggest`, `DesktopToast` (giỏ nhanh).
2. **Giải phẫu.** (a) phần tử neo (nút/ô) · (b) bảng nổi · (c) nội dung.
3. **Biến thể.** `menu` (lưới link 2 cột, rộng 520) · `listbox` (gợi ý tìm, rộng theo ô) · `panel` (giỏ nhanh, rộng 360).
4. **Kích thước và khoảng cách.** Cách phần tử neo 8. `menu`: đệm 16, lưới 2 cột gap 4 16, link cao 40 (máy tính), "Xem tất cả" chiếm 2 cột. `listbox`, `panel`: xem SearchSuggest, MiniCart.
5. **Token.** Nền `--surface`, viền `--border`, bo `--radius-card`, bóng `--shadow-pop`. Link `menu` 14/500 `--ink` (đầu mục "Xem tất cả cá →" `--accent-text` 600). Nền mờ sau `listbox` trên điện thoại: `--overlay-light`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mở | opacity + `translateY(-4px)→0` 180ms `--ease-out`; reduced motion: tức thì |
| hover | link → nền `--surface-2`, chữ `--accent-text` |
| focus-visible | viền 2px `--focus` |
| chọn | `listbox`: dòng đang trỏ nền `--accent-soft` |
| đang tải / lỗi / disabled | theo nội dung |

7. **Hành vi.** Mở bằng bấm hoặc focus; `menu` còn mở khi rê chuột (có độ trễ đóng để chuột đi chéo không tắt). Đóng: Esc (trả focus về phần tử neo), bấm ra ngoài, Tab ra khỏi bảng. Định vị bằng CSS `position: absolute` trong khung neo; không thêm thư viện định vị. `z-index: var(--z-popover)`.
8. **Props.**

```ts
interface PopoverProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  anchorRef: React.RefObject<HTMLElement>;
  placement?: 'bottom-start' | 'bottom-end';   // 'bottom-start'
  width?: number | 'anchor';                    // 'anchor'
  openOnHover?: boolean;                        // false
  labelledBy?: string;
  children: React.ReactNode;
}
```

9. **Truy cập.** `menu`: mẫu disclosure (nút có `aria-expanded aria-controls`, bảng là vùng chứa link), **không** dùng `role="menu"` vì là điều hướng. `listbox`: theo combobox (SearchSuggest). `panel`: `<section aria-labelledby>`. Mở bằng hover luôn có cách mở tương đương bằng phím.
10. **Câu chữ.** "Cá thu", "Cá ngừ", "Cá nục", "Cá bớp", "Xem tất cả cá →" (dữ liệu từ nhóm con).
11. **Không được.** Bẫy focus như dialog. Chỉ mở được bằng hover. Che ô tìm.
12. **Code.** Mới `frontend/components/ui/Popover.tsx`.

## 42. Toast

1. **Công dụng.** Phản hồi nhanh, tự ẩn, không chặn thao tác. **Dùng ở:** `A4-Toast`, `DesktopToast`.
2. **Giải phẫu.** (a) icon tích · (b) câu · (c) hành động tuỳ chọn ("Xem giỏ").
3. **Biến thể.** Điện thoại: nổi đáy, có "Xem giỏ". Máy tính: nổi góc phải dưới header, icon trong vòng xanh, không có hành động (đi kèm MiniCart).
4. **Kích thước và khoảng cách.** Điện thoại: `left/right: 16px`, đáy = trên CartBar/BottomNav 12 (không có thanh: 16 + safe-area); `min-height` 48, đệm 4 4 4 14, gap 10; nút "Xem giỏ" cao 44 đệm 0 12. Máy tính: rộng 360, đệm 10 10 10 14, vòng icon 24.
5. **Token.** Nền `--ink`, chữ `--on-accent` 14/500, bo `--radius-lg` (máy tính `--radius-card`), bóng `--shadow-pop`. "Xem giỏ" `--on-brand-muted` 600 (13,9:1 trên `ink`). Vòng icon máy tính `--good`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| vào | opacity + `translateY(8px)→0` 200ms `--ease-out` (máy tính `translateY(-4px)`) |
| ra | opacity → 0, 150ms |
| hover / focus bên trong | dừng đếm giờ ẩn |
| nhấn "Xem giỏ" | `scale(.97)` |
| focus-visible "Xem giỏ" | viền trắng offset −4 |
| disabled / đang tải / lỗi / chọn | không áp dụng |

7. **Hành vi.** Tự ẩn sau **3 s**. Một toast một lúc: toast mới thay toast cũ. Không dùng toast cho lỗi cần sửa hay thông tin quan trọng (dùng Banner/Dialog). Nằm trên CartBar, không che nút.
8. **Props.**

```ts
interface ToastOptions { message: string; action?: { label: string; href: string }; tone?: 'neutral' | 'success' }
// ToastProvider bọc app; component gọi:
const { show } = useToast();   // show(options: ToastOptions): void
```

9. **Truy cập.** Một vùng `role="status" aria-live="polite"` **luôn có trong DOM** (ở `ToastProvider`), toast chèn chữ vào đó để trình đọc đọc chắc chắn. Không lấy focus. Thời gian 3 s là đủ cho câu ngắn; thông tin vẫn thấy được ở badge/giỏ.
10. **Câu chữ.** "Đã thêm 1 kg Mực ống làm sạch vào giỏ" (điện thoại), "Đã thêm 1 kg Mực ống làm sạch" (máy tính), "Xem giỏ".
11. **Không được.** Toast cho lỗi đặt hàng. Toast xếp chồng. Tự ẩn dưới 3 s. Che CartBar.
12. **Code.** Mới `frontend/components/ui/Toast.tsx`; thay chữ "Đã thêm ✓" 1,5 s trong `AddToCartControl.tsx`.

## 43. Banner/Alert

1. **Công dụng.** Khối thông báo trong trang theo mức: thông tin, thành công, cảnh báo, lỗi. **Dùng ở:** `Main` (dải "mua từ 1 kg"), `Cart` (tối thiểu 1 kg), `B3-CartChanged`, `C1c-AddressFilled`, `A7-OutOfStock`, `A9-ComboDetail`, `D2-PayCancelled`, `D5-Underpaid`, `E2-Cancelled`, `E4-DeliveryFailed`, `F2-LookupNotFound`, `DesktopCategory` (luật mua).
2. **Giải phẫu.** (a) icon 18 · (b) tiêu đề tuỳ chọn · (c) một câu · (d) hành động/link tuỳ chọn.
3. **Biến thể.** `tone`: `info` · `success` · `warn` · `crit`. `layout`: `inset` (khối trong lề) · `full-bleed` (sát hai mép, dưới header: B3) · `strip` (dải 32 căn giữa một dòng: "Hải sản cấp đông theo lô · mua từ 1 kg").
4. **Kích thước và khoảng cách.** `inset`: đệm 12 14 (lớn: 14 16), gap 10, bo 10 (máy tính 12), lề 16. `full-bleed`: đệm 12 16, kẻ dưới. `strip`: cao 32, icon 14, gap 6.
5. **Token.** Không viền màu. info: nền `--accent-soft`, chữ/icon `--accent-text`. success: `--good-soft` / `--good`. warn: `--warn-soft` / `--warn`. crit: `--crit-soft` / `--crit`. Tiêu đề 14/600 màu trạng thái; câu body `--ink-2` (info, success một dòng: màu trạng thái 13/500). `strip`: `label` 13/500.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | tĩnh |
| hiện sau thao tác | opacity + `translateY(-6px)→0` 200ms |
| hover / nhấn / focus | chỉ trên link/nút bên trong |
| disabled / đang tải / chọn | không áp dụng |

7. **Hành vi.** Không có nút đóng (trừ SuccessBanner). Banner hiện do thao tác (lỗi tra đơn, thanh toán chưa xong) mới dùng vai trò live. Câu luật mua dựng từ `min_qty`/`qty_step`. E2 hiện lý do huỷ từ `cancel_notice.reason_label` (bảng nhãn công khai cố định, L-14); không bao giờ hiện ghi chú tự do.
8. **Props.**

```ts
interface BannerProps {
  tone: 'info' | 'success' | 'warn' | 'crit';
  title?: string;
  children?: React.ReactNode;
  layout?: 'inset' | 'full-bleed' | 'strip';   // 'inset'
  icon?: IconName | null;                      // theo tone
  live?: 'off' | 'polite' | 'assertive';       // 'off'; crit sau thao tác: 'assertive' (role="alert")
  action?: React.ReactNode;
}
```

9. **Truy cập.** crit sau thao tác: `role="alert"`; success/warn sau thao tác: `role="status"`; banner tĩnh: không vai trò. Icon `aria-hidden`; nghĩa nằm ở chữ.
10. **Câu chữ.** "Hải sản cấp đông theo lô · mua từ 1 kg"; "Mua tối thiểu 1 kg mỗi món."; "Giỏ hàng có thay đổi từ lần trước"; "Đã điền địa chỉ từ bản đồ."; "Nếu một món trong combo hết, combo tạm ngưng bán."; D2 "Thanh toán chưa thành công" / "Bạn đã huỷ hoặc ngân hàng báo lỗi. Đơn vẫn đang được giữ."; D5 "Cá Về đang kiểm tra giao dịch và sẽ gọi cho bạn. Vui lòng không chuyển thêm khi chưa được hướng dẫn."; E2 "Cá Về sẽ gọi cho bạn" / "Nhân viên sẽ gọi vào số điện thoại đặt hàng để xử lý số tiền 867.000đ bạn đã thanh toán. Cần gấp, bạn gọi [hotline]." (chờ `legal-vn`, L-08); E4 "Shipper chưa liên lạc được với bạn. Cá Về sẽ gọi để hẹn lại giờ giao."; F2 "Không tìm thấy đơn khớp mã và số điện thoại. Kiểm tra lại, hoặc gọi [hotline]."; A7 xem Q-UX-7.
11. **Không được.** Chữ "hoàn tiền", tiến độ hoàn, hạn hoàn. Nói ô nào sai ở F2. Viền trái màu dày. Hứa "giao trong ngày", "miễn phí giao", "báo khi có hàng".
12. **Code.** Mới `frontend/components/ui/Banner.tsx`; thay khối huỷ/hoàn trong `app/shop/orders/OrderLookup.tsx:160-205` ở lô 4.

## 44. EmptyState

1. **Công dụng.** Trạng thái rỗng có một hướng đi tiếp. **Dùng ở:** `A5-NotFound`, `B4-CartEmpty`, `Cart` (nhánh rỗng), `DesktopNotFound`, `DesktopCart` (nhánh rỗng); trang 404.
2. **Giải phẫu.** (a) ô icon tròn · (b) tiêu đề · (c) một câu · (d) gợi ý (chip nhóm) · (e) hành động: một nút chính, hoặc kẻ + "Liên hệ chúng tôi để hỏi hàng".
3. **Biến thể.** `search` (tìm không thấy: chip nhóm + liên hệ) · `cart` (giỏ trống: một nút "Xem hàng đang có") · `page` (404: một nút về trang chủ).
4. **Kích thước và khoảng cách.** Khối lề 16, đệm 32 20 24 (giỏ: 32 16), bo 12, căn giữa, gap 8. Ô icon 64 (icon 30); giỏ: icon 40 không ô. Câu `max-width` 280. Chip cách câu 12, gap 8. Kẻ cách 16 8. Máy tính: đệm 48 24, bo 12.
5. **Token.** Nền `--surface`, viền `--border` (giỏ: không viền), bo `--radius-card`. Ô icon nền `--surface-2`, icon `--ink-3`. Tiêu đề `title` 17/600. Câu body `--ink-2`. Nút giỏ: `primary` md 44 pill. "Liên hệ…": `secondary` md 44, rộng đầy, icon điện thoại.
6. **Trạng thái.** Tĩnh; hover / nhấn / focus theo phần tử con. đang tải / lỗi / disabled / chọn: không áp dụng (có component riêng).
7. **Hành vi.** Dòng đếm phía trên "0 sản phẩm cho “cá hồi”" `aria-live="polite"`. Chip gợi ý = các nhóm có hàng. Giữ header, ô tìm và hàng lọc phía trên như bình thường.
8. **Props.**

```ts
interface EmptyStateProps {
  icon: IconName;
  title: string;
  description?: string;
  primaryAction?: { label: string; href: string };
  suggestions?: { label: string; href: string }[];
  contactHref?: string;              // 'tel:…' -> nút "Liên hệ chúng tôi để hỏi hàng"
  framed?: boolean;                  // true (giỏ: false)
}
```

9. **Truy cập.** `<section aria-labelledby>` tiêu đề (h2). Chip gợi ý trong `<ul aria-label="Nhóm hàng gợi ý">`.
10. **Câu chữ.** "Không tìm thấy “cá hồi”" / "Thử từ khoá khác hoặc xem các nhóm hàng bên dưới" / "Liên hệ chúng tôi để hỏi hàng"; "Giỏ hàng đang trống" / "Xem hàng đang có". 404: `[copy]`.
11. **Không được.** Nhiều hơn một hành động chính. Minh hoạ lớn chiếm màn. Hứa "sẽ có hàng".
12. **Code.** Mới `frontend/components/ui/EmptyState.tsx`; restyle `app/not-found.tsx` (lô 1).

## 45. ErrorState

1. **Công dụng.** Lỗi tải dữ liệu cấp trang/khối, có "Thử lại". **Dùng ở:** `A6-Offline`, `DesktopOffline`.
2. **Giải phẫu.** (a) ô icon tròn (wifi gạch) · (b) tiêu đề · (c) một câu cách sửa · (d) nút "Thử lại" · (e) khung xương mờ phía dưới (gợi ý chỗ hàng sẽ hiện).
3. **Biến thể.** `network` (mất mạng/lỗi tải). Trang Shop công khai không có 403.
4. **Kích thước và khoảng cách.** Như EmptyState (đệm 28 20 24). Nút md 44, đệm 0 22, cách câu 10. Khung xương mờ cách 16, lưới như danh sách thật.
5. **Token.** Như EmptyState. Nút `primary` icon làm mới. Khung xương phía dưới `opacity: .5`, **đứng yên** (không nhấp nháy).
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| mặc định | hiện khi tải lỗi |
| đang tải (bấm Thử lại) | nút `loading` (Spinner, giữ chữ "Thử lại"), `aria-busy` trên vùng nội dung |
| thành công | thay bằng nội dung; focus về `h1` trang |
| lỗi lần nữa | giữ nguyên, nút trở lại bình thường |
| hover / nhấn / focus | theo Button |

7. **Hành vi.** Header, ô tìm và hàng lọc **vẫn hiện**. Không tự thử lại liên tục. Sự kiện `online` của trình duyệt có thể tự gọi thử lại một lần.
8. **Props.**

```ts
interface ErrorStateProps { title: string; description: string; onRetry: () => void; retrying?: boolean; showGhostGrid?: boolean /* true */ }
```

9. **Truy cập.** `role="alert"` khi xuất hiện. Nút có nhãn chữ. Khung xương `aria-hidden`.
10. **Câu chữ.** "Chưa tải được hàng" / "Kiểm tra kết nối mạng rồi thử lại" / "Thử lại".
11. **Không được.** Hiện mã lỗi kỹ thuật, chuỗi lỗi server. Xoá header/lọc khi lỗi.
12. **Code.** Mới `frontend/components/ui/ErrorState.tsx`; thay banner lỗi không có nút trong `app/shop/page.tsx`.

## 46. Skeleton

1. **Công dụng.** Khung xương đúng hình trong lúc tải. **Dùng ở:** `A0-Loading`, `DesktopLoading`; giỏ khi so giá, trang đơn khi tra.
2. **Giải phẫu.** Các vạch/khối thay cho phần tử thật: chip, dòng đếm, thẻ (ảnh, 2 dòng tên, giá, ghi chú, nút).
3. **Biến thể.** Nguyên tử `Skeleton` + preset: `ProductCardSkeleton`, `ChipRowSkeleton`, `CartLineSkeleton`, `OrderSkeleton`.
4. **Kích thước và khoảng cách.** Bằng phần tử thật. Thẻ: ảnh 3:2 bo 8; tên 14 cao, rộng 90% và 60%; giá 20 cao rộng 55%; ghi chú 12 cao rộng 70%; nút 44 bo 8. Chip 40 cao, rộng 48–76, bo 999. Gap trong thẻ 8.
5. **Token.** Nền `--surface-3`, bo `--radius-sm` (khối có bo riêng giữ bo thật). Thẻ chứa: như ProductCard.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| đang tải | opacity 1 → .55, chu kỳ **1.4s** ease-in-out, lặp; reduced motion: đứng yên |
| tĩnh (dưới ErrorState) | đứng yên, `opacity: .5` |
| hover / nhấn / focus / disabled / lỗi / chọn | không áp dụng |

7. **Hành vi.** Header, ô tìm vẫn hiện thật. Số thẻ xương = số thẻ vừa một màn (điện thoại 4, máy tính 8). Dừng animation khi ra khỏi màn hình.
8. **Props.**

```ts
interface SkeletonProps { width?: number | string; height?: number | string; radius?: 'sm' | 'md' | 'lg' | 'full'; animated?: boolean /* true */ }
interface ProductCardSkeletonProps { count?: number /* 4 */ }
```

9. **Truy cập.** Vùng nội dung `aria-busy="true"`; một `role="status"` chữ ẩn "Đang tải hàng"; mọi khối xương `aria-hidden`.
10. **Câu chữ.** "Đang tải hàng" (ẩn).
11. **Không được.** Spinner toàn trang thay cho xương. Khung xương khác hình nội dung thật (gây nhảy).
12. **Code.** Mới `frontend/components/ui/Skeleton.tsx`; thay chữ "Đang tải…" trong `app/shop/page.tsx`.

## 47. Spinner

1. **Công dụng.** Vòng quay nhỏ báo đang xử lý ở chỗ hẹp (trong nút, chờ ngân hàng). **Dùng ở:** `C4-NetworkError` (nút "Đang đặt…"), `D3-PayPending` (vòng lớn), `DesktopPayPending`.
2. **Giải phẫu.** (a) vòng rãnh · (b) cung quay.
3. **Biến thể.** `size`: 16 · 18 (trong nút) · 36 (D3, trong ô tròn 72 nền `accent-soft`).
4. **Kích thước và khoảng cách.** Nét 2.2–2.4. Trong nút cách chữ 8–10.
5. **Token.** Cung `currentColor` (trong nút `primary`: `--on-accent`; D3: `--accent`). Rãnh: trong nút không có; D3 `--border`. Ô tròn D3 nền `--accent-soft`.
6. **Trạng thái.**

| Trạng thái | Thay đổi |
|---|---|
| quay | xoay 360° 800–900ms tuyến tính, lặp |
| reduced motion | quay chậm 2,4–3 s (vẫn cần dấu hiệu đang chạy) |
| hover / nhấn / focus / disabled / lỗi / chọn | không áp dụng |

7. **Hành vi.** Luôn đi kèm chữ ("Đang đặt…", "Đang chờ xác nhận thanh toán"). Chỉ quay khi đang hiện trên màn.
8. **Props.**

```ts
interface SpinnerProps { size?: 16 | 18 | 36 /* 18 */; label?: string /* chữ ẩn khi không có chữ hiện cạnh */ }
```

9. **Truy cập.** SVG `aria-hidden`. Nếu không có chữ hiện cạnh thì có `role="status"` + `label` ẩn.
10. **Câu chữ.** "Đang đặt…", "Đang chờ xác nhận thanh toán".
11. **Không được.** Spinner một mình không chữ. Spinner toàn trang khi có thể dùng Skeleton.
12. **Code.** Mới `frontend/components/ui/Spinner.tsx`.

---

## Ánh xạ màn → component

Khung chung (ShopHeader, ShopFooter, BottomNav, LogoSlot, Toast) không ghi lại ở từng dòng trừ khi có điểm riêng.

| Màn (điện thoại · máy tính) | Route | Component |
|---|---|---|
| `Home` · `DesktopHome` (A1) | `/` | ShopHeader `home`/`full` · SearchBox `trigger`/`brand` · Banner (khối khuyến mãi dùng Button `on-brand`; không dùng chữ "Lô mới vừa nhập kho", D7) · CategoryTile · ProductCard `rail` + `row` · PriceTag · ImageFrame · StockBadge · ShopFooter `full` · BottomNav |
| `Main` · `DesktopCategory` (A2) | `/shop/` | ShopHeader `sticky`/`full` · Banner `strip` · SearchBox `page` · Chip `filter` · SortControl / SegmentedControl · SideFilter · Breadcrumb · ProductCard `grid` · AddToCart · QtyStepper · StockBadge · PriceTag · ImageFrame · CartBar · BottomNav · Dialog (bỏ món) |
| `A4-Toast` · `DesktopToast` | `/shop/` | như A2 + Toast · MiniCart · Popover |
| `A5-NotFound` · `DesktopNotFound` | `/shop/?q=` | như A2 + EmptyState `search` · Chip `link` · Button `secondary` |
| `A6-Offline` · `DesktopOffline` | `/shop/` | như A2 + ErrorState · Skeleton (tĩnh) |
| `A0-Loading` · `DesktopLoading` | `/shop/` | ShopHeader · SearchBox · Skeleton (`ChipRowSkeleton`, `ProductCardSkeleton`) · BottomNav |
| `A8-SearchSuggest` · `DesktopSearchSuggest` | ô tìm | SearchBox · SearchSuggest · Popover `listbox` · Chip `link` (tìm gần đây) |
| `Product` · `DesktopProduct` (A3) | `/shop/item/?code=` | ShopHeader `sub`/`full` · Breadcrumb · ImageFrame + Toggle `thumb` · StockBadge `inline` · PriceTag `detail` · Toggle `preset` · QtyStepper `select` · AddToCart `detail` · Toast/MiniCart |
| `A7-OutOfStock` · `DesktopOutOfStock` | `/shop/item/?code=` | như A3 + StockBadge `out` (`overlay md` + `inline`) · ImageFrame `dimmed` · Banner `info` (Q-UX-7) · AddToCart `detail` (Gọi + Zalo) |
| `A9-ComboDetail` · `DesktopComboDetail` (A10) | `/shop/item/?code=` | như A3, đơn vị `combo` · bảng thành phần · Banner `info` (combo tạm ngưng) · QtyStepper `select` bước 1 |
| `Cart` · `DesktopCart` (B1) | `/shop/cart/` | ShopHeader `checkout`-like (H3 không giỏ) / `compact` · CheckoutSteps · CartLine · QtyStepper `sm` · Banner `info` · CartSummary `cart` · ShopFooter `compact` |
| `B2-RemoveConfirm` · `DesktopRemoveConfirm` | `/shop/cart/` | Dialog `confirm` + Button `secondary`/`danger` |
| `B3-CartChanged` · `DesktopCartChanged` | `/shop/cart/` | Banner `warn` `full-bleed` · CartLine `price-changed`/`out` · PriceTag (giá cũ) · CartSummary (món còn hàng) |
| `B4-CartEmpty` | `/shop/cart/` | EmptyState `cart` |
| `Checkout` · `DesktopCheckout` (C1) | `/shop/checkout/` | ShopHeader `checkout`/`compact` · CheckoutSteps · TextField · AddressField · Checkbox · CartSummary `checkout` · ShopFooter `compact` |
| `C1b-MapPicker` · `DesktopMapPicker` | `/shop/checkout/` | FullscreenSheet · AddressMapPicker · Skeleton · Spinner |
| `C1c-AddressFilled` | `/shop/checkout/` | AddressField `filled-from-map` · Banner `success` |
| `C2-Invalid` · `DesktopInvalid` | `/shop/checkout/` | FormErrorSummary · TextField (lỗi) · AddressField (lỗi) · Checkbox (lỗi, Q-UX-4) |
| `C3-SoldOut` · `DesktopModalSoldOut` | `/shop/checkout/` | BottomSheet `notice` (máy tính thành Dialog `md`) · ImageFrame |
| `C4-NetworkError` · `DesktopNetworkError` | `/shop/checkout/` | Button `loading` · Spinner · Dialog `alert` `neutral` |
| `C5-LocationDenied` | `/shop/checkout/` | Dialog `alert` `warn` (chỉ còn ca bản đồ nạp lỗi; bỏ "Vị trí của tôi", chốt 10/10) |
| `Payment` · `DesktopPayment` (D1) | `/shop/orders/?code=` | ShopHeader `checkout`/`compact` · CheckoutSteps · HoldCountdown `created` · PaymentMethod · OrderLines `summary` · CartSummary `payment` |
| `D2-PayCancelled` · `DesktopPayCancelled` | `/shop/orders/?code=&result=cancel` | Banner `crit` · HoldCountdown `retry` · OrderLines · CartSummary `payment-retry` (không có nút "Huỷ đơn", BR-BH-28) |
| `D3-PayPending` · `DesktopPayPending` | `/shop/orders/?code=&result=success` (còn chờ) | Spinner 36 · OrderStatusBadge `awaiting_bank` (nếu hiện nhãn) · OrderTimeline `payment` · Button `outline` |
| `D4-Expired` · `DesktopModalExpired` | `/shop/orders/` | HoldCountdown (00:00) · Dialog `alert` `crit` |
| `D5-Underpaid` · `DesktopUnderpaid` | `/shop/orders/` | OrderStatusBadge `awaiting_review` · bảng đối chiếu tiền · Banner `warn` |
| `D6-LeavePayment` · `DesktopLeavePayment` | `/shop/orders/` | Dialog `alert` `info` · HoldCountdown `deadline` |
| `Success` · `DesktopSuccess` (E1) | `/shop/orders/?code=&result=success` | ShopHeader `sub`/`full` · SuccessBanner · OrderStatusBadge · OrderTimeline · OrderLines `order` · TextField (tra đơn khác) · ShopFooter `full`. **Không** khối người nhận |
| `E2-Cancelled` | `/shop/orders/` | OrderStatusBadge `cancelled` · Banner `info` (Cá Về sẽ gọi) · OrderLines `cancelled` |
| `E3-Delivered` | `/shop/orders/` | OrderStatusBadge `delivered` · OrderTimeline · OrderLines · Button `outline` ("Gọi [hotline]", số giờ từ BE-7) |
| `E4-DeliveryFailed` | `/shop/orders/` | Banner `warn` · OrderStatusBadge `delivery_failed` · OrderTimeline (`failed`) · OrderLines |
| `DesktopOrderStates` | `/shop/orders/` | E2 + E3 + E4 bản máy tính |
| `F1-Lookup` · `DesktopLookup` | `/shop/orders/` | ShopHeader `sub` · TextField (mã, SĐT) · Button · BottomNav (Q-UX-5) |
| `F2-LookupNotFound` | `/shop/orders/` | Banner `crit` (không chỉ ô sai) · TextField (không `aria-invalid`) |
| `P1-Policy` · `DesktopPolicy` (F3) | `/trang/?slug=` | ShopHeader `sub`/`full` · Breadcrumb · PolicyNav `toc` + `list`/`aside` · Link |
| `P2-Contact` · `DesktopContact` (F4) | chờ Q7 | ShopHeader · Breadcrumb · Button (Gọi, Zalo) · Link (`mailto:`). **Không form** |
| `P3-HowToBuy` (F5) | chờ Q7 | ShopHeader `sub` · PolicyNav · `<details>` FAQ (số liệu 1 kg / 0,5 kg / 30 phút lấy từ setting) |
| `G1-KitchenList` · `DesktopKitchenList` | `/bai-viet/` | ShopHeader · Chip `filter` · Breadcrumb · ShopFooter `full` · BottomNav |
| `G2-KitchenArticle` · `DesktopKitchenArticle` | `/bai-viet/` | ShopHeader `sub`/`full` · Breadcrumb · ProductCard `row` (món liên quan) · ShopFooter |
| `Landing` | `/gioi-thieu/` | ShopHeader `full` · LogoSlot · Button · ProductCard `rail` · ShopFooter `full` |
| 404 | `app/not-found.tsx` | ShopHeader `sticky`/`full` · EmptyState `page` · ShopFooter `full` |

---

## Tự soát

Đã soát theo `web-design-guidelines`, `fixing-accessibility`, `baseline-ui` (bản đọc, không chạy script):

- **Tên truy cập:** mọi IconButton có `aria-label` nêu đối tượng; nút trong thẻ ghi tên món; link mở tab mới có chữ ẩn.
- **Bàn phím và focus:** Dialog/BottomSheet/FullscreenSheet dùng `<dialog>` gốc, giữ focus, Esc, trả focus; AddToCart dời focus khi nút đổi thành stepper; FormErrorSummary nhận focus; Popover không bẫy focus; combobox dùng `aria-activedescendant`.
- **Ngữ nghĩa:** lọc nhóm và menu chính sách là link + `aria-current` (không phải button); sắp xếp là radio gốc; bảng giỏ máy tính có `th scope`; danh sách là `ul/ol`.
- **Form:** nhãn thật, `aria-describedby` cho gợi ý và lỗi, `aria-invalid`, ô nhập 16 px, không chặn dán; tra đơn không chỉ ra ô sai.
- **Thông báo:** Toast có vùng live cố định; giỏ cập nhật đọc qua `aria-live="polite"`; đồng hồ không đọc mỗi giây.
- **Tương phản:** phát hiện 2 cặp trượt AA ở file màn (`on-brand-muted` trên `accent`, placeholder `border-input`) và đã đổi; trạng thái luôn có chữ hoặc icon kèm màu.
- **Vùng chạm:** nâng mọi nút 32–40 lên 44 trên điện thoại; chip 40 có vùng chạm 44.
- **Chuyển động:** chỉ `transform`/`opacity`/màu; 120–260 ms; tôn trọng `prefers-reduced-motion`; thanh đồng hồ dùng `scaleX` thay `width`; bỏ `scale(.8)` 320ms của banner máy tính.
- **Baseline:** không gradient, không glow, z-index theo thang cố định, `100dvh`, safe-area cho thanh dính đáy. Mục "MUST Tailwind/`cn`" của `baseline-ui` không áp dụng vì Shop không dùng Tailwind (theo `HUONG-DAN-CODE.md` §7: không thêm thư viện).
- **Nghiệp vụ:** giá theo kg / combo, tối thiểu 1 kg bước 0,5, combo bước 1, dưới tối thiểu mở Dialog; tồn chỉ `in/low/out`, không prop nhận số kg; hết hàng "Liên hệ chúng tôi"; không ngày nhập, mã lô, giá vốn; địa chỉ một ô + Maps nạp khi bấm, không lưu toạ độ; không hoá đơn điện tử; không chữ "hoàn tiền"; trang đơn không hiện người nhận; mã đơn `SO…`; badge giỏ là số món.
- **Dữ liệu mẫu:** chỉ dùng tên giả "Nguyễn Văn A", "09xx xxx xxx", ô `[…]` của file màn; không có dữ liệu thật.


---

## 48. VoucherField (mã giảm giá, chốt 07/10)

1. **Công dụng**: nhập và áp một mã giảm giá cho đơn. **Dùng ở**: `Cart`, `B5-VoucherSheet`, `B6-VoucherApplied`, `B7-VoucherError`, `B8-VoucherInvalidAtOrder`, `DesktopCart`, `DesktopVoucher`; dòng giảm giá ở `Payment`, `Success`, `DesktopPayment`. Bảng hình: `screens/CMP-3-Inputs.dc.html` (section cuối).
2. **Giải phẫu**: (điện thoại) dòng "Mã giảm giá · Nhập mã ›" trong tóm tắt giỏ → BottomSheet gồm tiêu đề, ô nhập, nút "Áp dụng", câu "Mỗi đơn dùng 1 mã.", dòng lỗi. (Máy tính) nhãn + ô nhập + nút "Áp dụng" ngay trong CartSummary. Sau khi áp: chip mã (good-soft) + nút bỏ mã + dòng "Giảm giá −…".
3. **Biến thể**: `trigger-row` (điện thoại), `sheet` (điện thoại), `inline` (máy tính), `applied` (chip).
4. **Kích thước**: ô nhập 44, chữ 16, bo 8; nút "Áp dụng" rộng cố định 104 (điện thoại, primary) / nút viền md 44 (máy tính, để không tranh với "Tiếp tục"); chip cao 32, bo 999; nút X trong chip vùng chạm 44.
5. **Token**: ô `border-input`, focus `focus` + ring `accent-soft`; lỗi `crit` + `crit-soft`; chip `good-soft`/`good`; dòng giảm giá chữ `good`; thông tin "ưu đãi lợi hơn" `ink-2` + icon i (không dùng crit).
6. **Trạng thái**: trống (nút tắt) · đang gõ (chữ tự in hoa, bỏ khoảng trắng; nút bật) · đang kiểm (spinner trong nút, `aria-busy`, ô khoá) · đã áp (chip + dòng giảm + tổng mới, toast "Đã áp mã …") · lỗi (viền crit, `aria-invalid`, dòng lỗi dưới ô) · ưu đãi đang áp lợi hơn (thông tin, không phải lỗi) · hết hiệu lực lúc đặt (Dialog B8).
7. **Hành vi**: mỗi đơn tối đa 1 mã; áp mã mới thay mã cũ. Không cộng dồn với ưu đãi tự động (PricingRule), hệ thống lấy cái lợi hơn (Duy duyệt 10/10). Kiểm mã qua API (BE-11), không tự tính ở FE. Enter trong ô = bấm "Áp dụng". Gõ lại sau lỗi thì ẩn lỗi. Bỏ mã → quay về trạng thái trống, tổng cũ. Mã lưu cùng giỏ (máy khách); khi đặt hàng gửi `voucher_code`, server kiểm lại.
8. **Props**:
```ts
type VoucherError = 'INVALID' | 'EXPIRED' | 'MIN_ORDER' | 'USED_UP' | 'BETTER_PROMO' | 'NETWORK';
interface VoucherFieldProps {
  variant: 'trigger-row' | 'sheet' | 'inline';
  appliedCode?: string;            // có thì hiện chip
  discountAmount?: number;         // đồng
  checking?: boolean;
  error?: VoucherError;
  minOrderAmount?: number;         // cho câu MIN_ORDER
  onApply: (code: string) => void;
  onRemove: () => void;
  onOpenSheet?: () => void;        // trigger-row
}
```
9. **Truy cập**: label "Mã giảm giá" gắn ô; lỗi `role="alert"` + `aria-describedby`; áp hoặc bỏ mã báo qua `aria-live="polite"`; nút X `aria-label="Bỏ mã CAVE10"`; sheet theo luật BottomSheet (giữ tiêu điểm, Esc).
10. **Câu chữ**: "Mã giảm giá" · "Nhập mã" · "Áp dụng" · "Mỗi đơn dùng 1 mã." · "Đã áp mã {MÃ}" · "Giảm giá −{tiền}" · "Bỏ mã". Lỗi: "Mã không đúng hoặc đã hết hạn." · "Đơn cần từ {tiền} để dùng mã này." · "Mã đã hết lượt dùng." · "Ưu đãi đang áp đã có lợi hơn mã này." · "Chưa kiểm được mã. Thử lại." · Dialog: "Mã {MÃ} không còn dùng được" / "Đơn sẽ tính theo giá chưa giảm." / "Đặt hàng không dùng mã" · "Quay lại giỏ".
11. **Không được**: tự tính số tiền giảm ở FE; cộng dồn nhiều mã; đặt hàng với giá khác giá khách đã thấy mà không hỏi (B8); hiện mã riêng của khách khác; ghi mã vào log kèm số điện thoại.
12. **Code**: mới `frontend/components/cart/VoucherField.tsx`; sửa `components/cart/CartSummary.tsx`, `features/checkout/*` (gửi `voucher_code`); `lib/api.ts` (`checkVoucher`). Lô **3b** trong `PLAN.md`.
