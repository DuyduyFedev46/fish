# purchasing/receipts — Nhà cung cấp & phiếu nhập (P-02)

`submit_receipt`: mỗi dòng nhập sinh MỘT lô (BR-MH-01), hạn dùng chỉ được sửa xuống (BR-MH-02), idempotent.
Nhà cung cấp để chung module này (chỉ là CRUD phục vụ phiếu nhập). Đơn giá mua `rate` ẩn nếu thiếu `view_costprice`.
Endpoint: `/api/purchasing/suppliers/`, `/api/purchasing/receipts/` + `POST …/{id}/submit/`.
Đọc (R10, W2a/W2b): `GET /api/purchasing/receipts/` (20 dòng/trang; lọc `status`, `supplier`, `month=YYYY-MM`, `date_from`,
`date_to`, `has_invoice`; sai → 400 `INVALID_FILTER`) và `GET …/{id}/` (dòng nhập kèm lô, hoá đơn mua, chi phí phụ).
Tiền mua (`purchase_amount`), `rate`, `landed_unit_cost`, `costs`, số tiền hoá đơn chỉ cho `view_costprice`. Lọc ở `filters.py`.
Nhà cung cấp (B3, `supplier_queries.py`, `supplier_services.py`): `GET /api/purchasing/suppliers/` (lọc `q`, `supplier_type`, `is_active`)
và `…/{id}/` kèm `receipt_count`, `last_received_at`, `purchase_total`. Chỉ phiếu Đã ghi nhận được tính. `purchase_total` là tiền mua,
chỉ cho `view_costprice`. `POST`/`PATCH` ghi AuditLog chỉ tên trường (không chép SĐT), tên không được trùng.
