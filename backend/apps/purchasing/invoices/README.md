# purchasing/invoices — Hoá đơn mua (BR-MH-04)

Hoá đơn mua tách khỏi phiếu nhập, phải có trước khi chốt lô (kiểm ở `inventory/batches` `close_batch`).
Hiện chỉ CRUD (chưa có `services.py`); người tạo = người đăng nhập (BR-PQ-16, test ở `apps/common/tests/test_s4_actor_fields.py`).
Endpoint: `/api/purchasing/invoices/`.

R11 (Lô 12): `GET /api/purchasing/invoices/?is_paid=&supplier=&month=YYYY-MM&page=` (`filters.py`, 20 dòng/trang). Thêm `code` ("#id"), `supplier_name`, `receipt_code`, `is_paid_label`. D-3: Quản lý thấy `amount` (không thuộc `COST_KEYS`); ghi vẫn chỉ Chủ.

Lô 17a (luật ghi, `PurchaseInvoiceSerializer.validate()` trên giá trị đã gộp, BR-MH-03/BR-MH-04): 400 `AMOUNT_NOT_POSITIVE` (`amount <= 0`), `INVOICE_SUPPLIER_MISMATCH` (phiếu nhập của nhà cung cấp khác), `PAID_AT_REQUIRED` (đã trả mà thiếu `paid_at`), `PAID_AT_IN_FUTURE`, `PAID_AT_WHEN_UNPAID` (chưa trả mà có `paid_at`). PATCH không gửi `is_paid`/`paid_at` thì bỏ qua luật `paid_at`, nên dòng cũ `is_paid=True, paid_at=NULL` vẫn sửa được số tiền. Không đổi model, không migration. Test: `tests/test_invoice_validation.py`.
