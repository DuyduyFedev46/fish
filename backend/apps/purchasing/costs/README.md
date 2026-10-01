# purchasing/costs — Chi phí mua & giá vốn lô (P-03)

`record_purchase_cost`: ghi chi phí + phân bổ vào lô theo kg (mặc định, BR-GV-04) / theo giá trị / số truyền sẵn, rồi tính lại
`landed_unit_cost` (BR-GV-01/03). Lô đã chốt không nhận chi phí (BR-GV-02). Chỉ Chủ (`add_purchasecost`).
Endpoint: `/api/purchasing/costs/`.

R12 (Lô 12): `GET /api/purchasing/costs/?cost_type=ICE,TRANSPORT&month=YYYY-MM&page=` (`filters.py`, 20 dòng/trang) và `…/{id}/`. Thêm `cost_type_label`, `allocation_method_label`, `batch_count`. Tiền chi phí phụ là giá vốn: đọc cần `view_purchasecost` VÀ `view_costprice` (`api.py::check_permissions`), nếu không 403 và không có thân nào lộ số.
