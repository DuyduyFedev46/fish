# inventory/stock — Sổ kho (nền cho mọi biến động)

`record_movement`: ghi `StockLedgerEntry` append-only + cập nhật tồn, không cho âm, khoá dòng (`select_for_update`).
Mọi module khác (lô, bán, kiểm kê, hàng hoàn) đổi tồn đều đi qua hàm này.
Endpoint: `/api/inventory/warehouses/`, `/api/inventory/ledger/` (chỉ đọc), `/api/inventory/stock-entries/` (người tạo = người đăng nhập, BR-PQ-16).

## Endpoint cho màn ERP (R6, R7, R7b)
- `GET /api/inventory/ledger/` (Sổ nhập xuất, chỉ đọc): `balance_after` tính bằng truy vấn con tương quan (không dùng `Window`, vì `Window` chạy sau `WHERE` nên sai khi lọc). Lọc `batch`, `movement_type` (nhiều, ngăn cách phẩy), `warehouse`, `item`, `date_from/date_to`. `references.py` dịch chuỗi `reference` thành `reference_display` + `reference_link {kind,id}`; tra mã hoá đơn/đơn hàng gộp tối đa 2 truy vấn mỗi trang.
- `GET/POST/PATCH /api/inventory/warehouses/`: `active_batch_count`, `total_qty` (chỉ lô còn tồn). Thêm kho qua `warehouse_services.create_warehouse` (kiểm tên trống/dài/trùng, ghi AuditLog). Không có DELETE.
- `GET /api/inventory/stock-entries/` (R7b): lọc `purpose`, `date_from/date_to`. Đợt này chỉ đọc: tạo phiếu không đổi tồn, không ghi sổ (D-1).
- `filters.py`: đọc tham số lọc. Sai dạng thì 400 `INVALID_FILTER`, không lặp lại giá trị đã gửi. `date_*` tính theo giờ Việt Nam.
- Test: `tests/base.py` (dữ liệu nền, kiểm rò giá vốn), `test_ledger_api.py`, `test_warehouses_api.py`, `test_stock_entries_api.py`.

