# purchasing/invoices — Hoá đơn mua (BR-MH-04)

Hoá đơn mua tách khỏi phiếu nhập, phải có trước khi chốt lô (kiểm ở `inventory/batches` `close_batch`).
Hiện chỉ CRUD (chưa có `services.py`); người tạo = người đăng nhập (BR-PQ-16, test ở `apps/common/tests/test_s4_actor_fields.py`).
Endpoint: `/api/purchasing/invoices/`.

R11 (Lô 12): `GET /api/purchasing/invoices/?is_paid=&supplier=&month=YYYY-MM&page=` (`filters.py`, 20 dòng/trang). Thêm `code` ("#id"), `supplier_name`, `receipt_code`, `is_paid_label`. D-3: Quản lý thấy `amount` (không thuộc `COST_KEYS`); ghi vẫn chỉ Chủ.
