# features/inventory — Kho & lô

Story: **S8** (chuyển view "Kho & Lô" của bản HTML cũ + tab "Hoạt động" của cột phải). **S25** sẽ thêm mở bán / chốt lô.

- Endpoint hiện tại: `GET /api/dashboard/summary/` (đọc `batches`, `user`, `activity`), cache chung với Tổng quan.
- Giá vốn (bất biến #1, S8-AC2/AC3): cột "Giá vốn/kg" chỉ hiện khi `user.can_cost`. BE bỏ hẳn key `unit_cost`
  khi thiếu `inventory.view_costprice` — BE là lớp chặn thật, FE chỉ ẩn cho gọn.
- Khi sang S25: đổi `getInventory()` sang danh sách lô riêng — **cần `inventory.view_batch`**; sổ kho cần
  `inventory.view_stockledgerentry` (L2: GET danh sách back-office đòi quyền view_*).
- Quyền xem màn (FE): `inventory.view_batch`. Tab "Hoạt động" cũng chỉ tải khi có quyền này, và chỉ khi được mở.

## Lô Quá hạn còn tồn (P8 Lô 5 — SR-15, SR-16, BR-LO-07, BR-MH-08)

- `/inventory/?status=EXPIRED` (thẻ "Lô quá hạn còn tồn" ở Tổng quan → Cần chú ý) đọc `GET /api/inventory/batches/?status=EXPIRED`
  (trang đầu, chỉ giữ lô còn tồn). Danh sách này chỉ có mã mặt hàng, không có tên NCC/kho nên bỏ hai cột đó.
- Chi tiết lô Quá hạn vẽ nút theo `next_steps` (chỉ Chủ thấy; lô đang giữ chỗ thì khoá kèm lý do):
  **Xác nhận Đã huỷ phần tồn** (gửi `confirm_qty` = tồn đang hiển thị), **Xác nhận Đã trả NCC** (form kg + tiền NCC hoàn + ghi chú,
  `request_id` sinh khi mở form), **Chốt lô** (khoá kèm lý do khi còn tồn, BR-LO-04). Tiền NCC hoàn không hiện lại sau khi lưu.
- Công cụ thử ở mock: `window.__caveMock.expiredSetQty("L0908-CT00", 2)` (đổi tồn "phía máy chủ"), `expiredState()`, `expiredReset()`.

| File | Làm gì |
|---|---|
| `api.ts` | `getInventory()`, `getActivity()`, `filterBatches()`, `getBatchesByStatus()`, `cancelExpiredBatch()`, `returnToSupplier()`, `closeBatch()` |
| `mock.ts` | mock endpoint (seed chung; `unit_cost` theo quyền) + 3 lô quá hạn bịa và trạng thái trong bộ nhớ |
| `types.ts` | `InventoryData`, `ActivityData`, `BatchRow`, `LedgerActivity`, `ReturnToSupplierInput/Result`, `BatchApiRow` |
| `components/InventoryScreen.tsx` | màn Kho & lô (+ chế độ lọc theo `?status=`) |
| `components/BatchDetailSheet.tsx` | chi tiết lô + nút thao tác lô Quá hạn |
| `components/ReturnToSupplierDialog.tsx` | form Đã trả NCC |
| `components/ModalDialog.tsx` | hộp thoại nhỏ mở trên tấm chi tiết (bẫy Tab/Esc riêng) |
| `components/ActivityFeed.tsx` | tab "Hoạt động" (8 dòng sổ kho), ghép vào cột phải ở `app/(console)/layout.tsx` |
