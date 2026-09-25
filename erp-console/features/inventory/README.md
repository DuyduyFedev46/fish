# features/inventory — Kho & lô

Story: **S8** (chuyển view "Kho & Lô" của bản HTML cũ + tab "Hoạt động" của cột phải). **S25** sẽ thêm mở bán / chốt lô.

- Endpoint hiện tại: `GET /api/dashboard/summary/` (đọc `batches`, `user`, `activity`), cache chung với Tổng quan.
- Giá vốn (bất biến #1, S8-AC2/AC3): cột "Giá vốn/kg" chỉ hiện khi `user.can_cost`. BE bỏ hẳn key `unit_cost`
  khi thiếu `inventory.view_costprice` — BE là lớp chặn thật, FE chỉ ẩn cho gọn.
- Khi sang S25: đổi `getInventory()` sang danh sách lô riêng — **cần `inventory.view_batch`**; sổ kho cần
  `inventory.view_stockledgerentry` (L2: GET danh sách back-office đòi quyền view_*).
- Quyền xem màn (FE): `inventory.view_batch`. Tab "Hoạt động" cũng chỉ tải khi có quyền này, và chỉ khi được mở.

| File | Làm gì |
|---|---|
| `api.ts` | `getInventory()`, `getActivity()`, `filterBatches()` |
| `mock.ts` | mock endpoint (seed chung; `unit_cost` theo quyền người đăng nhập) |
| `types.ts` | `InventoryData`, `ActivityData`, `BatchRow`, `LedgerActivity` |
| `components/InventoryScreen.tsx` | màn Kho & lô |
| `components/ActivityFeed.tsx` | tab "Hoạt động" (8 dòng sổ kho), ghép vào cột phải ở `app/(console)/layout.tsx` |
