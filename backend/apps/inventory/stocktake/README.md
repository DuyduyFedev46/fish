# inventory/stocktake — Kiểm kê & hao hụt (P-09)

Duyệt phiếu kiểm kê → điều chỉnh tồn theo số đếm (movement RECONCILE). Người duyệt ≠ người nhập số (BR-KK-02);
chênh dương phải ghi lý do (BR-KK-04, kiểm lúc nhập số). Lúc duyệt áp đúng chênh lệch đã chụp lúc nhập (BR-KK-09, đề xuất, chờ Duy chốt); phiếu rỗng không duyệt được (`RECON_EMPTY`). Quyền duyệt `approve_stockreconciliation`.
Endpoint: `/api/inventory/reconciliations/` + `POST …/{id}/approve/`.
