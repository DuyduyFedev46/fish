# inventory/stocktake — Kiểm kê & hao hụt (P-09)

Duyệt phiếu kiểm kê → điều chỉnh tồn theo số đếm (movement RECONCILE). Người duyệt ≠ người nhập số (BR-KK-02);
chênh dương phải ghi lý do (BR-KK-04). Quyền duyệt `approve_stockreconciliation`.
Endpoint: `/api/inventory/reconciliations/` + `POST …/{id}/approve/`.
