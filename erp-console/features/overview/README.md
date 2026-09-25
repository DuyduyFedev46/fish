# features/overview — Tổng quan

Màn đầu của Chủ/Quản lý/NV kho: 4 KPI (doanh thu hôm nay, đơn chờ xử lý, lô cận hạn, giá trị tồn),
8 đơn gần nhất, cảnh báo cận hạn (≤6), tồn theo lô (≤20, thứ tự xuất FEFO). Story: **S8** (chuyển từ bản HTML cũ, số liệu y như cũ).

- Endpoint: `GET /api/dashboard/summary/` — BE chỉ đòi đăng nhập (`IsAuthenticated`). Contract + kiểu đầy đủ ở
  `shared/lib/dashboardSummary.ts` (dùng chung với `orders`, `inventory`), cache chung qua `shared/lib/useResource.ts`.
- Quyền xem màn (FE): `reports.view_dashboard` hoặc thuộc `chu`/`quan_ly`/`nv_kho` (`shared/lib/nav.ts`).
- Giá vốn: cột "Giá vốn/kg" và ô "Giá trị tồn kho" chỉ hiện khi `user.can_cost` (bất biến #1).
- Tìm kiếm phía máy (mã, khách, mặt hàng, kho, trạng thái; không phân biệt dấu). Nút Làm mới tải lại cả 3 màn.
- Mock: `mock.ts` → seed chung `shared/lib/dashboardSummary.mock.ts`. Thử lỗi 500 / rỗng: đặt
  `localStorage.cave_erp_mock_dashboard = "fail" | "empty"` (hoặc `window.__caveMock.dashboard("fail")`).

| File | Làm gì |
|---|---|
| `api.ts` | `getOverview()`, lọc đơn/lô theo từ khoá |
| `mock.ts` | mock endpoint theo người đăng nhập (401 nếu token hỏng) |
| `types.ts` | `OverviewData` = toàn bộ response |
| `components/OverviewScreen.tsx` | màn Tổng quan (toolbar, KPI, bảng đơn, cận hạn, bảng lô) |
| `components/KpiTiles.tsx` | 4 ô KPI |
