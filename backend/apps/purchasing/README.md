# purchasing — Mua hàng (P-02, P-03)

Mua trực tiếp tại cảng (không PO): phiếu nhập sinh lô → hoá đơn mua → chi phí phụ phân bổ vào giá vốn lô.
BR chính: BR-MH-01 (1 dòng nhập = 1 lô), BR-MH-02 (hạn chỉ sửa xuống), BR-MH-04, BR-GV-01..04.
Model: `models/` (suppliers, receipts, invoices, costs).

| Module | Làm gì |
|---|---|
| `receipts/` | nhà cung cấp + phiếu nhập, action `submit` sinh lô |
| `invoices/` | hoá đơn mua (CRUD, chưa có nghiệp vụ riêng) |
| `costs/` | chi phí mua + phân bổ lô (landed cost) — chỉ Chủ |
