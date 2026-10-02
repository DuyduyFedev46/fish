# features/inventory — Kho & lô

Story: **ED-23** (Tồn theo lô), **ED-24** (trang chi tiết lô), **ED-25** (Điều chỉnh tồn, chỉ đọc, và tab Kho). Lô 7 của "ERP theo design".
Sổ nhập xuất toàn kho nằm ở `features/ledger/`.

## Màn hình

- `/inventory/` — ba tab (một `useTabParam`, `?tab=`): **Tồn theo lô** · **Điều chỉnh tồn** (chỉ đọc, quyết định D-1) · **Kho**.
  Tab Tồn theo lô có thêm panel "Nhập xuất gần đây" (8 dòng, link sang `/ledger/`). `?status=` lọc theo trạng thái lô
  (thẻ "Lô quá hạn còn tồn" ở Tổng quan dẫn vào đây với `status=EXPIRED`); giá trị lạ bị bỏ qua.
- `/inventory/detail/?id=` — trang chi tiết lô (khung `DetailPage`): đường trạng thái, thông tin lô, số lượng và giá vốn,
  Nhập xuất của lô (kèm Tồn sau), đơn lấy hàng từ lô, dòng thời gian, khối Trợ lý AI. Thao tác nằm ở menu "Thao tác khác".

## Thao tác (chỉ đọc `next_steps` + quyền, BE là lớp chặn thật)

| Thao tác | Ai | Điểm cần nhớ |
|---|---|---|
| Mở bán lô (`publishBatch`) | Chủ, Quản lý | gửi 1 lần dù bấm đúp; không có ô giá |
| Đã trả nhà cung cấp (`returnToSupplier`) | Chủ | form kg + tiền hoàn + ghi chú; `request_id` sinh khi mở form; tiền hoàn không hiện lại sau khi lưu |
| Huỷ phần tồn, ghi lỗ (`cancelExpiredBatch`) | Chủ | gửi `confirm_qty` = tồn đang hiển thị; lệch thì BE báo 400, FE tải lại tồn |
| Chốt lô (`closeBatch`) | Chủ | khoá kèm lý do khi còn tồn; lô có lãi/lỗ thì hiện "Lãi/lỗ lô" trong hộp xác nhận |

Không có "Ngừng bán lô" (quyết định D-2) và không có nút Điều chỉnh tồn (D-1: điều chỉnh đi qua Kiểm kê).

## Giá vốn (bất biến 1)

Cột và dòng "Giá mua/kg", "Giá vốn/kg", "Lãi/lỗ lô" chỉ hiện khi người dùng có quyền xem giá vốn; BE bỏ hẳn khoá khi thiếu quyền.
Quản lý không thấy các cột này. Mock phản ánh đúng điều đó (`purchase_rate`/`landed_unit_cost` chỉ trả cho Chủ).

## File

| File | Làm gì |
|---|---|
| `api.ts` | `fetchBatches`, `fetchBatch`, `fetchBatchOptions`, `fetchOrdersByBatch`, `fetchBatchProfit`, `publishBatch`, `cancelExpiredBatch`, `returnToSupplier`, `closeBatch`, `fetchWarehouses`, `fetchAllWarehouses`, `addWarehouse`, `fetchStockEntries`. Nhánh mock viết thẳng `process.env.NEXT_PUBLIC_USE_MOCK === "1"` ở từng chỗ (để bản thật không chứa dữ liệu mẫu; `check-no-mock`) |
| `types.ts` | kiểu theo contract R1–R5 của 02b |
| `mock.ts` | mock đủ lô theo từng trạng thái, tồn/giữ chỗ thay đổi được khi thao tác, 409/400 cũ để thử |
| `lotView.ts` (+ test) | hàm thuần: quyền theo lô, nhãn, lý do khoá, đọc `?id=`/`?status=`, đổi số kg |
| `components/InventoryScreen.tsx` | khung ba tab |
| `components/LotsTab.tsx`, `StockEntriesTab.tsx`, `WarehousesTab.tsx` | nội dung từng tab |
| `components/BatchDetailScreen.tsx`, `BatchSections.tsx` | trang chi tiết và các khối con; khối Trợ lý AI do trang `app/(console)/inventory/detail/page.tsx` ghép qua prop `renderAi` (màn không import `features/ai`) |
| `components/PublishBatchModal.tsx`, `ReturnToSupplierModal.tsx`, `CancelExpiredModal.tsx`, `CloseBatchModal.tsx`, `AddWarehouseModal.tsx` | các hộp xác nhận (khung `Modal` chung) |
| `components/useActionSubmit.tsx` | hook gửi một lần + xử lý lỗi chung cho các thao tác |
| `inventory.module.css` | kiểu riêng của module, chỉ dùng token trong DESIGN.md |

Công cụ thử ở mock: `window.__caveMock.expiredSetQty("L0908-CT00", 2)` (đổi tồn "phía máy chủ"), `expiredState()`, `expiredReset()`.
