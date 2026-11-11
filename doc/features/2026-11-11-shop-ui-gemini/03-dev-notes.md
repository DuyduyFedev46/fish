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
