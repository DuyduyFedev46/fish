# inventory/returns — Hàng giao thất bại về kho (P-08, R9)

| File | Việc |
|---|---|
| `scope.py` | `scope_returns_for(user, qs)` và `scope_delivery_notes_for`: người giao chỉ thấy phiếu hàng hoàn của phiếu giao gán cho mình. DÙNG CHUNG cho API và dòng thời gian `return` (`next_steps.py`). |
| `creation.py` | `create_return`: kiểm tra phiếu giao ĐANG GIAO/THẤT BẠI, lô có trong phiếu, tổng kg hoàn (kể cả phiếu hoàn khác của cùng phiếu giao và lô) không vượt kg đã giao; rồi gọi `delivery.services.return_to_warehouse`. |
| `filters.py` | Lọc danh sách: `status` (nhiều giá trị), `month=YYYY-MM` (giờ VN). Sai → 400 `INVALID_FILTER`. |
| `serializers.py` | Field tường minh, có tên hiển thị, `outside_minutes`; không có giá vốn, không có tên/SĐT khách. |
| `api.py` | `/api/inventory/returns/` (list, tạo, chi tiết, PATCH ghi chú) + `POST …/{id}/approve/`. Không DELETE. |
| `services.py` | `apply_return` (duyệt): RESTOCK cộng lại đúng lô gốc (BR-HV-01), WRITE_OFF ghi lỗ; không tự nhập lại kho (BR-HV-02); lô đã chốt không nhận hàng hoàn (BR-HV-04). Quyền `approve_returntostock`. |

`note` là chữ tự do (có thể chứa dữ liệu cá nhân): chỉ nằm trong API này (có `Cache-Control: no-store`), không vào AuditLog,
dòng thời gian, AI (bất biến 9).
