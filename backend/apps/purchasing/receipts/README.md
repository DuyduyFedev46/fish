# purchasing/receipts — Nhà cung cấp & phiếu nhập (P-02)

`submit_receipt`: mỗi dòng nhập sinh MỘT lô (BR-MH-01), hạn dùng chỉ được sửa xuống (BR-MH-02), idempotent.
Nhà cung cấp để chung module này (chỉ là CRUD phục vụ phiếu nhập). Đơn giá mua `rate` ẩn nếu thiếu `view_costprice`.
Endpoint: `/api/purchasing/suppliers/`, `/api/purchasing/receipts/` + `POST …/{id}/submit/`.
