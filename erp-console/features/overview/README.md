# features/overview — Tổng quan (ED-08 / board D1)

Màn đầu của Chủ/Quản lý/NV kho. Dải 5 số liệu (Doanh thu, Đơn chờ xử lý, Sắp hết giữ chỗ, Lô cận hạn, Giá trị tồn kho) ·
"Cần chú ý" · "Đơn hàng gần đây" · "Tồn kho theo lô" (thứ tự xuất FEFO). Story gốc **S8**, làm lại theo design ở Lô 15.

- Endpoint: `GET /api/dashboard/summary/` — BE chỉ đòi đăng nhập. Contract + kiểu ở `shared/lib/dashboardSummary.ts`
  (dùng chung với `orders`, `inventory`), cache chung qua `shared/lib/useResource.ts`. Khối "Cần chú ý" gọi riêng
  `GET /api/dashboard/attention/` nên lỗi của khối này không làm hỏng cả màn.
- Quyền xem màn (FE): `reports.view_dashboard` hoặc thuộc `owner`/`manager`/`warehouse_staff` (`shared/lib/nav.ts`).
- **Giá vốn** (bất biến 1, ED-08-AC4): ô "Giá trị tồn kho" và cột "Giá vốn/kg" chỉ có trong DOM khi `user.can_cost`.
- **Dữ liệu cá nhân** (bất biến 9): bảng đơn không có tên khách/SĐT.
- Tìm kiếm dùng ô tìm chung của khung app (⌘K); màn này không có ô tìm riêng.
- Cột "Còn giữ chỗ" đếm ngược mm:ss riêng, không gộp vào Lý do. Đơn Giữ chỗ quá mốc đổi sang "Đã huỷ" ngay tại máy (ED-09-AC5).
- Dòng "đề xuất AI chờ duyệt" (`AiProposalsRow`) chỉ hiện khi có quyền `ai-actions`, AI đang bật và có ≥1 đề xuất; lỗi hay AI tắt thì ẩn (không tải runtime AI).
- Hàng đơn/lô **không bấm được** vì dashboard chỉ trả mã, không có id số (xem 03-dev-notes Lô 15). Dòng cận hạn mở danh sách lô lọc "Cận hạn".
- Mock: `mock.ts` → seed chung `shared/lib/dashboardSummary.mock.ts` (mã đơn đổi sang `SO…` ở đây). Thử lỗi 500 / rỗng:
  `window.__caveMock.dashboard("fail" | "empty")`.

| File | Làm gì |
|---|---|
| `api.ts` | `getOverview()`, `getDashboardAttention()` |
| `mock.ts` | mock endpoint theo người đăng nhập (401 nếu token hỏng) |
| `types.ts` | `OverviewData` = toàn bộ response |
| `view.ts` (+ `.test.ts`) | Logic thuần: dòng cần chú ý, nhãn doanh thu, dòng cận hạn, gom đề xuất AI theo vùng, dòng đơn |
| `overview.module.css` | Style màn (token) |
| `components/OverviewScreen.tsx` | Màn: dải số liệu, 2 thẻ, bảng đơn, bảng lô |
| `components/KpiTiles.tsx` | 5 ô số liệu (ô tồn kho chỉ khi có quyền giá vốn) |
| `components/AttentionBlock.tsx` | "Cần chú ý": việc quá hạn, đề xuất AI, lô cận hạn |
| `components/AiProposalsRow.tsx` | Dòng đề xuất AI chờ duyệt (có cổng, nhẹ) |
