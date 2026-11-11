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
