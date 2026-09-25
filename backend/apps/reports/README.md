# reports — Báo cáo lãi lỗ & bảng điều hành (P-10)

`services.py`: lãi lỗ theo lô (nguồn sự thật, BR-BC-04/05) và theo tháng (BR-BC-01..03) — tính lại từ sales/inventory/purchasing, không có bảng riêng.
`api.py`: `/api/reports/batch/{batch_id}/`, `/api/reports/period/?year&month` — chỉ `view_profitreport`.
`dashboard_api.py`: `/api/dashboard/summary/` — chỉ `reports.view_dashboard` (chu/quan_ly/nv_kho, S6) (KPI, đơn gần đây, tồn theo lô; giá vốn — `kpis.inventory_value`, `batches[].unit_cost` — chỉ có key khi có `view_costprice`; test `tests/test_dashboard_cost_leak.py`).
`models.py`: `ProfitReport` chỉ để giữ quyền `view_profitreport` và `view_dashboard` (S6; gán Group ở `accounts/migrations/0003`). App nhỏ → giữ phẳng.
