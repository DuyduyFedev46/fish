# purchasing/invoices — Hoá đơn mua (BR-MH-04)

Hoá đơn mua tách khỏi phiếu nhập, phải có trước khi chốt lô (kiểm ở `inventory/batches` `close_batch`).
Hiện chỉ CRUD (chưa có `services.py`); người tạo = người đăng nhập (BR-PQ-16, test ở `apps/common/tests/test_s4_actor_fields.py`).
Endpoint: `/api/purchasing/invoices/`.
