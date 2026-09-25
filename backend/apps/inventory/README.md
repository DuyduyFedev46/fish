# inventory — Kho & lô (P-04, P-08, P-09)

Tồn quản lý THEO LÔ (BR-KK-01); mọi biến động kho ghi vào sổ append-only `StockLedgerEntry`.
Field nhạy cảm `Batch.purchase_rate`, `Batch.landed_unit_cost` chỉ lộ với `view_costprice`.
Model: `models/` (warehouses, batches, stock, stocktake, returns).

| Module | Làm gì |
|---|---|
| `batches/` | sinh lô, FIFO + giữ chỗ, publish/chốt lô, giá vốn lô, job trạng thái theo hạn |
| `stock/` | sổ chuyển động kho, kho, phiếu điều chỉnh kho |
| `stocktake/` | kiểm kê & hao hụt |
| `returns/` | duyệt hàng giao thất bại về kho |

Job hằng ngày: `manage.py update_batch_status` (gọi `batches.services.update_batch_statuses`).
