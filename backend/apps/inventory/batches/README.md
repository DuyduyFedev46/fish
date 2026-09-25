# inventory/batches — Lô hàng (P-04)

Sinh lô (`create_batch`), lô bán được = đang bán/cận hạn **và** còn hạn (`sellable_batches`, BR-LO-02), chọn lô FEFO — hạn sớm nhất trước, cùng hạn thì nhập trước (`allocate_fefo`, `FEFO_ORDER`; alias cũ `allocate_fifo`) + giữ chỗ (BR-BH-02/05/11),
publish (BR-MH-05) / chốt lô (BR-LO-04/05), tính lại giá vốn lô (BR-GV-01/03), job trạng thái theo hạn idempotent (BR-LO-01/02/06).
Endpoint: `/api/inventory/batches/` + `POST …/{id}/publish/`, `POST …/{id}/close/`; giá vốn ẩn nếu thiếu `view_costprice`.
Test rò giá vốn: `tests/test_api.py`. `tests/base.py` là dữ liệu nền cho test stock/stocktake/returns.
