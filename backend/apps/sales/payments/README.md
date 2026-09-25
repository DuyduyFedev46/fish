# sales/payments — Thanh toán & hoá đơn bán (P-05)

`confirm_payment` idempotent theo `bank_txn_id` (BR-TT-03); thiếu tiền → UNDERPAID (BR-TT-04); đơn đã huỷ → ORPHAN (BR-TT-05).
Khớp đủ → `issue_invoice`: trừ kho thật, ghi doanh thu (BR-TT-06), `SalesInvoiceLineBatch` là nguồn giá vốn (BR-BH-06).
Endpoint: `POST /api/internal/payments/sepay-webhook/` (adapter, service token — `internal_api.py`); `/api/sales/invoices/` (chỉ đọc)
+ `POST …/{id}/confirm-payment/` (chỉ Chủ, E-05); `/api/sales/payments/` (hàng chờ giao dịch lệch).
