# inventory/stock — Sổ kho (nền cho mọi biến động)

`record_movement`: ghi `StockLedgerEntry` append-only + cập nhật tồn, không cho âm, khoá dòng (`select_for_update`).
Mọi module khác (lô, bán, kiểm kê, hàng hoàn) đổi tồn đều đi qua hàm này.
Endpoint: `/api/inventory/warehouses/`, `/api/inventory/ledger/` (chỉ đọc), `/api/inventory/stock-entries/` (người tạo = người đăng nhập, BR-PQ-16).
