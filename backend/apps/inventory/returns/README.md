# inventory/returns — Hàng giao thất bại về kho (P-08)

NV giao chỉ tạo phiếu (ở `delivery.services.return_to_warehouse`); duyệt ở đây: RESTOCK cộng lại đúng lô gốc (BR-HV-01),
WRITE_OFF ghi lỗ; không tự nhập lại kho (BR-HV-02); lô đã chốt không nhận hàng hoàn (BR-HV-04). Quyền `approve_returntostock`.
Endpoint: `/api/inventory/returns/` + `POST …/{id}/approve/`.
