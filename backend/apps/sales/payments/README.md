# sales/payments — Thanh toán & hoá đơn bán (P-05)

`confirm_payment` idempotent theo `bank_txn_id` (BR-TT-03); thiếu tiền → UNDERPAID (BR-TT-04); đơn đã huỷ → ORPHAN (BR-TT-05).
Khớp đủ → `issue_invoice`: trừ kho thật, ghi doanh thu (BR-TT-06), `SalesInvoiceLineBatch` là nguồn giá vốn (BR-BH-06).
`confirm_payment_manual` (S11, BR-TT-08): Chủ xác nhận tay trên ĐƠN Giữ chỗ/Tự huỷ — cùng lõi `_record_payment` với webhook,
source=MANUAL, AuditLog `confirm_payment_manual` actor=Chủ; trùng mã GD cùng đơn → trả kết quả cũ (`duplicate`), khác đơn → 400 BR-TT-03.
`payment_outcome` dựng kết quả PAID/UNDERPAID/ORPHAN cho phản hồi. `parse_positive_amount` dùng chung với webhook.
Endpoint: `POST /api/internal/payments/sepay-webhook/` (adapter, service token — `internal_api.py`); `/api/sales/invoices/` (chỉ đọc,
action `confirm-payment` cũ ĐÃ GỠ — nay ở `POST /api/sales/orders/{id}/confirm-payment`, xem orders/); `/api/sales/payments/` (hàng chờ giao dịch lệch).
