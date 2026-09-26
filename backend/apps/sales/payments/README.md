# sales/payments — Thanh toán & hoá đơn bán (P-05)

`confirm_payment` idempotent theo `bank_txn_id` (BR-TT-03); thiếu tiền → UNDERPAID (BR-TT-04); đơn đã huỷ → ORPHAN (BR-TT-05).
Khớp đủ → `issue_invoice`: trừ kho thật, ghi doanh thu (BR-TT-06), `SalesInvoiceLineBatch` là nguồn giá vốn (BR-BH-06).
`confirm_payment_manual` (S11, BR-TT-08): Chủ xác nhận tay trên ĐƠN Giữ chỗ/Tự huỷ — cùng lõi `_record_payment` với webhook,
source=MANUAL, AuditLog `confirm_payment_manual` actor=Chủ; trùng mã GD cùng đơn → trả kết quả cũ (`duplicate`), khác đơn → 400 BR-TT-03.
`payment_outcome` dựng kết quả PAID/UNDERPAID/ORPHAN cho phản hồi. `parse_positive_amount` dùng chung với webhook.
Endpoint: `POST /api/internal/payments/sepay-webhook/` (adapter, service token — `internal_api.py`); `/api/sales/invoices/` (chỉ đọc,
action `confirm-payment` cũ ĐÃ GỠ — nay ở `POST /api/sales/orders/{id}/confirm-payment`, xem orders/); `/api/sales/payments/` (hàng chờ giao dịch lệch).

**S12 — hàng chờ lệch (BR-TT-09, Lô L8).** `PaymentTransaction.resolution_status` (OPEN/RESOLVED, null = giao dịch khớp),
`resolution` (ATTACHED/CONFIRMED/REFUNDED), `resolved_by/at`, `resolution_note`. Giao dịch lệch vào OPEN ngay khi ghi
(`initial_resolution_status`). **BR-TT-10 (P5):** tiền về cho đơn đã thanh toán → `OVERPAID`, vào hàng chờ để Chủ hoàn.
`resolve_payment`: `ATTACH_TO_ORDER` (giao dịch không khớp → đơn Giữ chỗ) / `CONFIRM_ORDER` (tổng các khoản thiếu còn mở
≥ tổng đơn, Q9) → hoá đơn + PROCESSING, đóng giao dịch, AuditLog `resolve_payment` (gắn thiếu: `attach_payment`, vẫn OPEN).
Khoá ĐƠN → GIAO DỊCH. `mark_payment_refunded`: gọi từ `refunds.confirm_refund` (S13). `payment_available_actions`: luật + quyền.
Endpoint (chỉ Chủ, `confirm_payment_manual`): `GET /api/sales/payments/?resolution_status=OPEN&match_status=…`,
`GET /api/sales/payments/{id}/`, `POST /api/sales/payments/{id}/resolve` (có/không `/`).

**Lô L8 — bổ sung tiền (quyết định Duy 2026-09-26).** `validate_amount`/`parse_positive_amount`: tối thiểu **1đ** sau làm tròn
0,01 (BR-TT-08) → tay 400 BR-TT-08, webhook 400 WEBHOOK_INVALID_INPUT, phiếu hoàn 400 BR-HT-04. **BR-TT-10 mở rộng:** chuyển
thừa ngay lần đầu cho đơn Giữ chỗ (webhook, tay, hoặc `ATTACH_TO_ORDER`) → dòng MATCHED mang đúng tổng đơn + `split_overpaid`
tạo dòng OVERPAID `<mã GD>-THUA` (OPEN, `raw_payload.split_from`) cho phần thừa, AuditLog `split_overpaid_payment`.
`overpaid_amount(payment)` tra phần thừa; phản hồi webhook/xác nhận tay/resolve có thêm `overpaid_amount` khi có.

**Cổng thanh toán SePay (P1/P3, doc/features/2026-09-26-sepay-cong-thanh-toan, ĐÃ DUYỆT).**
- `checkout.py` (P1, BR-TT-01/13/14/17): `build_checkout_params(order=…)` ký tham số hosted
  checkout (HMAC-SHA256, `_sign`/`_signature_string` cô lập — GIẢ ĐỊNH chuỗi ký, xem
  `03-dev-notes.md`). Chỉ đơn `BOOKED` còn TTL; khoá `SEPAY_SECRET_KEY` không rời server.
  `SalesOrder.checkout_attempts` đếm số lần lập tham số — từ lần 2 thêm hậu tố `-<n>` vào
  `order_invoice_number` (Q5), khớp `strip_order_retry_suffix` bên adapter.
  Endpoint Shop: `POST /api/shop/orders/{order_code}/checkout/` (`shop_api.py`, AllowAny —
  không cần 4 số cuối SĐT vì response không có PII).
- `internal_api.py` (P3, BR-TT-02/03/14/15): `POST /api/internal/payments/sepay-ipn/` — CÙNG
  contract body với webhook cũ, chạy chung `_handle_payment_ipn`/`confirm_payment`, chỉ khác
  `source=PaymentTransaction.Source.GATEWAY`. `environment_for_source` gắn
  `PaymentTransaction.environment` (SANDBOX/PRODUCTION) theo `settings.SEPAY_ENV` — CHỈ cho
  nguồn GATEWAY. `DUPLICATE_MANUAL_WARNING`: OVERPAID mới (mã GD khác) trùng số tiền với một
  khoản đã MATCHED qua xác nhận tay (MANUAL) của cùng đơn → gắn `duplicate_warning` (UC-5,
  BR-TT-15) thay vì để hiện như tiền thừa bình thường.
- Webhook biến động số dư cũ (`Source.WEBHOOK`, `/sepay-webhook/`) GIỮ NGUYÊN hành vi, không
  tắt ở Django (route đó tắt phía **adapter**, theo cấu hình `SEPAY_BANK_WEBHOOK_ENABLED`).
