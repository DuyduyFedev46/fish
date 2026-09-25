# features/orders — Đơn & tiền

Story: **S8** (chuyển view "Đơn hàng" của bản HTML cũ): 8 đơn gần nhất, 4 số cuối SĐT, thời gian giữ chỗ
còn lại (mốc `expires_at` do BE trả, tự đếm lùi mỗi 30 giây), trạng thái. **S10** sẽ mở rộng: danh sách đầy đủ, lọc, xác nhận tiền, huỷ, hoàn.

- Endpoint hiện tại: `GET /api/dashboard/summary/` (chỉ đọc `as_of`, `kpis`, `recent_orders`), cache chung với Tổng quan.
- Khi sang S10: đổi `getOrders()` sang `GET /api/orders/` — endpoint danh sách back-office, **cần `sales.view_salesorder`** (L2).
- Quyền xem màn (FE): `sales.view_salesorder` và không chỉ thuộc `nv_giao`.
- Tìm kiếm phía máy: mã đơn, khách, trạng thái, 4 số cuối SĐT.

| File | Làm gì |
|---|---|
| `api.ts` | `getOrders()`, `filterOrders()` |
| `mock.ts` | mock endpoint (seed chung) |
| `types.ts` | `OrdersData`, `OrderRow` |
| `components/OrdersScreen.tsx` | màn Đơn |
