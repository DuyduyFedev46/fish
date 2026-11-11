# 03 · Ghi chú hiện thực (Gemini CLI — Shop UI)

> Nhánh: `gemini/shop-ui` · Phạm vi: `frontend/` và `doc/features/2026-11-11-shop-ui-gemini/`

## Chuẩn bị
- Các file đang sửa dở/chưa track lúc bắt đầu (không đụng, không stage): `.gemini/commands/lam-tiep.toml`, `.gemini/commands/lam-tinh-nang.toml`, `.gemini/settings.json`, `AGENTS.md`, `CLAUDE.md`, `doc/features/2026-10-06-shop-lien-he/03-dev-notes.md`, `doc/ops/moi-truong.md`, `frontend/app/page.tsx`, `GEMINI.md`, `doc/so-do-agent.*`, `scripts/check_shop_ui_scope.py`, `.claude/worktrees/`.

---

## GUI-01 — Mã giảm giá khi kiểm bị lỗi mạng (L1, BR-DM-19, BR-BH-25)

### Kết quả kiểm tra hành vi hiện tại
- Comment ở `CheckoutScreen.tsx:178` ghi *"thiếu kết quả kiểm thì hiện giá chưa giảm và không gửi mã"* là comment cũ sót từ lô 3b.
- Thực tế ở `CheckoutScreen.tsx:242` và `voucherCodeToSend` (`features/cart/voucherView.ts:117`), FE **vẫn luôn gửi mã đã áp** kèm đơn đặt hàng để máy chủ quyết định (sửa lỗi QA B2 lô 7 — không bỏ mã im lặng).
- Do đó theo nhánh thứ hai của phiếu `02c-giao-viec.md`: khi `voucher.code` có giá trị, chưa có `voucher.quote` và lần kiểm lại bị lỗi (`voucher.error !== null`), khối `CartSummary` ở bước đặt hàng hiển thị dòng nhỏ `"Mã <MÃ> · sẽ kiểm khi đặt"`. Cập nhật lại comment ở `CheckoutScreen.tsx` cho khớp thực tế.

### Thay đổi chính
- `frontend/features/cart/voucherView.ts`: thêm hàm thuần `pendingVoucherText(code, hasQuote, hasError)`.
- `frontend/components/cart/CartSummary.tsx`, `CartSummary.module.css`: thêm prop `pendingVoucherNote` hiển thị dòng nhỏ phía trên dòng tổng tiền khi chưa có `discount`.
- `frontend/features/checkout/components/CheckoutScreen.tsx`: truyền `pendingVoucherNote` vào `CartSummary`, cập nhật comment dòng 178.
- `frontend/scripts/test-voucher.mjs`: thêm 4 ca đơn vị (Red → Green, `39/39 ca đạt`).
- `frontend/e2e/shop_full_flow.py`: thêm ca chặn mạng `**/api/shop/vouchers/check/` bằng `route.abort` ở cả 360 px và 1280 px (cả nhánh chặn từ giỏ chưa áp được mã — tổng tóm tắt bằng trang thanh toán `165.000đ` — và nhánh đã áp mã ở giỏ rồi sang đặt hàng bị lỗi mạng — hiện `"Mã X · sẽ kiểm khi đặt"` và máy chủ áp đúng giảm giá ở trang thanh toán `148.500đ`).

### Kết quả lệnh kiểm chứng (GUI-01)
```text
✓ Generating static pages (12/12)
check-no-mock: 4 file mock, 23 chuỗi seed, 65 file build (out/)
check-no-mock: XANH — không thấy seed mock nào trong bản build.
test-cart-reconcile: 20/20 đạt, 0 sai
test-catalog-view: 21/21 đạt, 0 sai
test-format: 33/33 đạt, 0 sai
test-home-content: 37/37 đạt, 0 sai
test-order-state: 81/81 đạt
test-phone: 17/17 đạt, 0 sai
test-quantity: 45/45 đạt, 0 sai
test-safe-href: 40/40 đạt, 0 sai
test-voucher: 39/39 ca đạt
check_naming: OK - 6437 vi phạm cũ trong 173 file, không phát sinh mới.
hex grep: rỗng · transition: all grep: rỗng
======== TỔNG KẾT E2E
PASS  general_rules: 132 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 109 đạt, 0 lỗi, 0 bỏ qua
```

---

## GUI-02 — Hộp "mã hết hiệu lực" (B8) không gạch trùng số khi chưa có giá máy chủ (L3, BR-DM-19)

### Thay đổi chính
- `frontend/features/cart/voucherView.ts`: thêm hàm thuần `hasDistinctDiscountedTotal(discountedPrice, fullPrice)`.
- `frontend/features/checkout/components/CheckoutScreen.tsx`: đổi `voucherGone.discountedPrice` sang `string | null` (`voucher.quote ? voucher.quote.total_after : null`); chỉ render `<del className={s.goneOld}>` khi `hasDistinctDiscountedTotal(...)` là `true`.
- `frontend/scripts/test-voucher.mjs`: thêm 4 ca đơn vị (Red → Green, `43/43 ca đạt`).
- `frontend/e2e/shop_full_flow.py`: thêm kiểm chứng 360 px và 1280 px cho cả hai ca hộp B8 (có `quote` → gạch `148.500đ` rồi hiện `165.000đ`; chưa từng kiểm được `quote` → không có `<del>`, chỉ hiện `165.000đ`, bấm `"Đặt hàng không dùng mã"` tạo đơn thành công).

### Kết quả lệnh kiểm chứng (GUI-02)
```text
✓ Generating static pages (12/12)
check-no-mock: XANH — không thấy seed mock nào trong bản build.
9/9 script test-*.mjs xanh (test-voucher: 43/43 ca đạt)
check_naming: OK - 6437 vi phạm cũ trong 173 file, không phát sinh mới.
hex grep: rỗng · transition: all grep: rỗng
======== TỔNG KẾT E2E
PASS  general_rules: 132 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 115 đạt, 0 lỗi, 0 bỏ qua
```


---

## GUI-03 — Dọn state chết ở giỏ và sửa thụt lề `hotline` (L4)

### Thay đổi chính
- `frontend/features/cart/components/CartScreen.tsx`: xoá state không có biến đọc `const [, setBlocked] = useState(false)`, `useEffect` gọi `setBlocked(false)` và lời gọi `setBlocked(true)` trong `proceed()`; logic chặn đặt hàng vẫn dựa hoàn toàn trên `result.outCount > 0` như thiết kế màn B3.
- `frontend/features/catalog/components/CatalogScreen.tsx`: chỉnh thụt lề prop `hotline={hotline}` ở dòng 204.
- `frontend/features/catalog/components/ItemDetailScreen.tsx`: chỉnh thụt lề prop `hotline={hotline}` ở dòng 98.

### Kết quả lệnh kiểm chứng (GUI-03)
```text
✓ Generating static pages (12/12)
check-no-mock: XANH — không thấy seed mock nào trong bản build.
9/9 script test-*.mjs xanh (20/20, 21/21, 33/33, 37/37, 81/81, 17/17, 45/45, 40/40, 43/43)
check_naming: OK - 6437 vi phạm cũ trong 173 file, không phát sinh mới.
hex grep: rỗng · transition: all grep: rỗng
======== TỔNG KẾT E2E
PASS  general_rules: 132 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 115 đạt, 0 lỗi, 0 bỏ qua
PASS  design_screens (A1,B3,DE11): 9 đạt, 0 lỗi, 0 bỏ qua
```


---

## GUI-04 — Ca E2E giỏ hỏng trong `localStorage` (L5, SHOP-1-01 AC7)

### Thay đổi chính
- `frontend/e2e/shop_general_rules.py`: thêm 4 phép kiểm ở cả 360 px và 1280 px:
  - Ghi trực tiếp `cangcaloc_cart_v1` có hai dòng `price: "abc"` và `price: null` vào `localStorage`, mở `/shop/cart/`: kiểm cả văn bản lẫn DOM HTML (đã loại thẻ `<script>/<style>` của Next.js flight payload) không xuất hiện `NaN`, `undefined`, `Infinity`, không lỗi console, `localStorage` tự chuẩn hoá lại `price` thành chuỗi số nguyên hợp lệ, màn giỏ đối chiếu catalog báo `"Giá đã cập nhật"` (`0đ -> 165.000đ / kg`, `0đ -> 235.000đ / kg`).
  - Ghi lại giỏ hỏng trực tiếp vào `localStorage` rồi mở thẳng `/shop/checkout/`: không `NaN`/`undefined`/`Infinity`, không lỗi console, không hiện dấu gạch ngang `—`.
- Đã thử làm hỏng tạm `CartContext.tsx` (`price: String(price)`, không commit): cả 4 phép kiểm `GUI-04` lập tức đỏ (`FAIL ... 'price': 'NaN'`), sau đó khôi phục lại `CartContext.tsx` và chạy xanh toàn bộ.

### Kết quả lệnh kiểm chứng (GUI-04)
```text
# Khi làm hỏng tạm CartContext.tsx (không commit):
FAIL GUI-04 [360] /shop/cart/ ... ('price': 'NaN')
FAIL GUI-04 [360] /shop/checkout/ ... ('price': 'NaN')
FAIL GUI-04 [1280] /shop/cart/ ... ('price': 'NaN')
FAIL GUI-04 [1280] /shop/checkout/ ... ('price': 'NaN')
== general_rules: 132 PASS, 4 FAIL, 0 SKIP

# Sau khi khôi phục CartContext.tsx:
✓ Generating static pages (12/12)
check-no-mock: XANH — không thấy seed mock nào trong bản build.
9/9 script test-*.mjs xanh
check_naming: OK - 6437 vi phạm cũ trong 173 file, không phát sinh mới.
======== TỔNG KẾT E2E
PASS  general_rules: 136 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 115 đạt, 0 lỗi, 0 bỏ qua
```


---

## GUI-05a — Làm đẹp trang chủ và khung chung (`globals.css`, Header, Footer, BottomNav, ShopFrame, HomeScreen)

### Thay đổi chính
- `frontend/app/globals.css`: bổ sung 12 biến CSS mở rộng giao diện biển sáng (`--surface-tint`, `--surface-warm`, `--border-subtle`, `--accent-border`, `--accent-glow`, `--brand-mid`, `--brand-gradient`, `--surface-gradient`, `--card-gradient`, `--shadow-xs`, `--shadow-card`, `--shadow-elevated`).
- `frontend/components/{ShopFrame,LogoSlot,ShopHeader,ShopFooter,BottomNav}.module.css`: chuyển header sang nền `--brand-gradient` phân tầng rõ với dải trên cùng, nút Giỏ hàng dạng pill có viền sáng, thanh `BottomNav` có chỉ báo cạnh trên cho mục đang chọn, chân trang có viền đỉnh nhấn và đóng thẻ nổi bật khối hỗ trợ Hotline/Email.
- `frontend/features/home/components/HomeScreen.module.css`, `frontend/components/catalog/CategoryTile.module.css`: làm mới hero banner với pill khẩu hiệu, hai thẻ phụ bên phải trên máy tính có viền sắc nét, lưới 6 thẻ danh mục dàn đều toàn khung 1200 px không còn khoảng trống thừa, đưa dải cam kết lên ngay dưới danh mục, đóng khung thẻ sáng đồng bộ cho `"Đang có hàng"`, `"Combo nấu nhanh"`, `"Góc bếp"`.

### Kết quả lệnh kiểm chứng (GUI-05a)
```text
✓ Generating static pages (12/12)
check-no-mock: XANH · 9/9 script test-*.mjs xanh · check_naming: OK
hex grep ngoài globals.css: rỗng · transition: all grep: rỗng
======== TỔNG KẾT E2E
PASS  general_rules: 136 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 115 đạt, 0 lỗi, 0 bỏ qua
PASS  footer_consent: 31 đạt, 0 lỗi, 1 bỏ qua
PASS  design_screens (A1,DK1,HF1,HF2): 10 đạt, 0 lỗi, 0 bỏ qua
```


---

## GUI-05b — Làm đẹp danh mục, chi tiết món, thẻ sản phẩm và tìm kiếm

### Thay đổi chính
- `frontend/components/catalog/{ProductCard,ImageFrame,PriceTag,StockBadge,QtyStepper}.module.css`: thẻ đồng đều chiều cao, khung ảnh nền `--surface-tint` viền mảnh, giá đậm `tabular-nums`, tách rời khoảng cách giữa tag `Combo` và badge `Hết hàng` trên thẻ hẹp 360 px để không chạm nhau.
- `frontend/features/catalog/components/{CatalogScreen,ItemDetailScreen}.module.css`, `frontend/components/catalog/{AddToCart.tsx,AddToCart.module.css,SideFilter.module.css,SortControl.module.css}`, `frontend/components/search/{SearchBox,SearchSuggest}.module.css`: đóng thẻ bộ lọc bên trái, thanh tiêu đề/sắp xếp, hộp chọn mua (`detailBox` nền `--surface-tint` viền `--accent-border`) và thẻ bảng thông tin sản phẩm.

### Kết quả lệnh kiểm chứng (GUI-05b)
```text
✓ Generating static pages (12/12)
check-no-mock: XANH · 9/9 script test-*.mjs xanh · check_naming: OK
hex grep ngoài globals.css: rỗng · transition: all grep: rỗng
======== TỔNG KẾT E2E
PASS  general_rules: 136 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 115 đạt, 0 lỗi, 0 bỏ qua
PASS  design_screens (cụm b — 13 màn + HF): 19 đạt, 0 lỗi, 0 bỏ qua
```


---

## GUI-05c — Làm đẹp giỏ hàng, dòng giỏ, ô mã giảm giá và giỏ mini

### Thay đổi chính
- `frontend/features/cart/components/CartScreen.module.css`, `frontend/components/cart/{CartLine.tsx,CartLine.module.css,VoucherField.module.css,CartBar.module.css,MiniCart.module.css}`: đóng thẻ từng dòng giỏ trên cả 360 px và 1280 px, phân tách rõ trạng thái đổi giá (viền hổ phách) và món hết hàng (nền xám nhạt viền đứt + pill đỏ), hộp nhắc giữ hàng nền `--surface-tint` kèm nút pill `"Mua thêm hàng khác"`, nút `"Nhập mã"` dạng pill trên điện thoại và hộp nhập mã nền ấm trên máy tính, khung hero giỏ trống cân đối.

### Kết quả lệnh kiểm chứng (GUI-05c)
```text
✓ Generating static pages (12/12)
check-no-mock: XANH · 9/9 script test-*.mjs xanh · check_naming: OK
hex grep ngoài globals.css: rỗng · transition: all grep: rỗng
======== TỔNG KẾT E2E
PASS  general_rules: 136 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 115 đạt, 0 lỗi, 0 bỏ qua
PASS  design_screens (cụm c — 12 màn + HF): 18 đạt, 0 lỗi, 0 bỏ qua
```


---

## GUI-05d — Làm đẹp đặt hàng (`/shop/checkout/`), thanh toán, tóm tắt đơn và thanh bước

### Thay đổi chính
- `frontend/components/cart/{CheckoutSteps,CartSummary}.module.css`, `frontend/features/checkout/components/{CheckoutScreen,AddressField,PaymentChoice,PaymentView,PaymentMethod,HoldCountdown,PendingView,ExpiredView,SoldOutSheet}.module.css`: thanh bước dạng pill bo tròn trên máy tính, đóng thẻ nổi bật khối tổng tiền (`totalRow`) và dòng nhắc mã chờ kiểm (`pendingVoucher`), đồng hồ giữ hàng nằm trong khung số trắng có pill mã đơn, hướng dẫn thanh toán đánh số tự động bằng CSS counter trong các thẻ bước rõ ràng.

### Kết quả lệnh kiểm chứng (GUI-05d)
```text
✓ Generating static pages (12/12)
check-no-mock: XANH · 9/9 script test-*.mjs xanh · check_naming: OK
hex grep ngoài globals.css: rỗng · transition: all grep: rỗng
======== TỔNG KẾT E2E
PASS  general_rules: 136 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 115 đạt, 0 lỗi, 0 bỏ qua
PASS  payment_choice: 77 đạt, 0 lỗi, 0 bỏ qua
PASS  design_screens (cụm d — 23 màn + HF): 29 đạt, 0 lỗi, 0 bỏ qua
```


---

## GUI-05e — Làm đẹp tra cứu đơn và chi tiết trạng thái đơn (`/shop/orders/`)

### Thay đổi chính
- `frontend/features/checkout/components/{OrderScreen,LookupForm,OrderView,OrderLines,OrderStatusBadge,OrderTimeline,SuccessBanner,CancelNotice}.module.css`: đóng thẻ form tra cứu cân đối (và tự bỏ khung kép khi nhúng làm `"Tra đơn khác"` trong `OrderView`), mã đơn dạng pill sắc nét kèm nút pill `"Sao chép mã đơn"`, nhãn trạng thái dạng viên thuốc có chấm tròn ngữ nghĩa, trục timeline 5 mốc có quầng sáng ở bước hiện tại và bước lỗi, bảng `"Món trong đơn"` kiểu biên lai rõ nét.

### Kết quả lệnh kiểm chứng (GUI-05e)
```text
✓ Generating static pages (12/12)
check-no-mock: XANH · 9/9 script test-*.mjs xanh · check_naming: OK
hex grep ngoài globals.css: rỗng · transition: all grep: rỗng
======== TỔNG KẾT E2E
PASS  general_rules: 136 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 115 đạt, 0 lỗi, 0 bỏ qua
PASS  design_screens (cụm e — 12 màn + HF): 18 đạt, 0 lỗi, 0 bỏ qua
```


---

## GUI-05f — Làm đẹp trang nội dung CMS (`/pages/`), Góc bếp (`/blog/`), Giới thiệu (`/about/`) và 404

### Thay đổi chính
- `frontend/features/content/components/{PageScreen,ArticleBody,ContactView,HowToBuyView,ContentState,KitchenListView,KitchenArticleView,ArticleItems}.module.css`, `frontend/features/site/components/PolicyNav.module.css`, `frontend/app/about/AboutScreen.module.css`, `frontend/app/not-found.module.css`: đóng thẻ điều hướng chính sách kèm viền trái mục đang xem và pill `Đang xem` trên điện thoại, hộp mục lục nền `--surface-tint` viền trái `--accent`, header chuyên mục Góc bếp đóng khung gọn cùng thẻ bài viết có pill chuyên mục, hero `/about/` nền `--brand-gradient` với huy hiệu số bước tròn `01`–`03`, trang 404 đặt trong thẻ căn giữa với biểu tượng tròn có quầng sáng và pill `404`.

### Kết quả lệnh kiểm chứng tổng lực toàn bộ Shop (GUI-05f + toàn bộ 86 màn thiết kế)
```text
✓ Generating static pages (12/12)
check-no-mock: 4 file mock, 23 chuỗi seed, 68 file build (out/) — XANH
9/9 script test-*.mjs xanh:
  - test-cart-reconcile: 20/20 đạt
  - test-catalog-view: 21/21 đạt
  - test-format: 33/33 đạt
  - test-home-content: 37/37 đạt
  - test-order-state: 81/81 đạt
  - test-phone: 17/17 đạt
  - test-quantity: 45/45 đạt
  - test-safe-href: 40/40 đạt
  - test-voucher: 43/43 ca đạt
check_naming: OK - 6437 vi phạm cũ trong 173 file, không phát sinh mới.
hex grep ngoài globals.css: rỗng · transition: all grep: rỗng
======== TỔNG KẾT E2E
PASS  general_rules: 136 đạt, 0 lỗi, 0 bỏ qua
PASS  full_flow: 115 đạt, 0 lỗi, 0 bỏ qua
PASS  content_pages: 58 đạt, 0 lỗi, 0 bỏ qua
PASS  formats_timezones: 73 đạt, 0 lỗi, 0 bỏ qua
PASS  design_screens: 91 đạt, 0 lỗi, 4 bỏ qua
```
