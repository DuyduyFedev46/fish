# features/ledger — Sổ nhập xuất

Story: **ED-29** (W5i, Lô 7). Màn `/ledger/`: mọi lần nhập, xuất, điều chỉnh tồn, mới nhất trước. **Chỉ đọc**: không có nút sửa hay xoá.

- Endpoint: `GET /api/inventory/ledger/` (R6), 20 dòng/trang. Lọc ở máy chủ: `batch`, `movement_type` (nhiều, nối dấu phẩy), `warehouse`, `date_from`, `date_to`.
  Tìm theo chữ chỉ chạy trên các dòng đã tải. Lọc sai → 400 `INVALID_FILTER` (màn hiện lỗi chung, không hiện chữ kỹ thuật).
- Quyền xem: `inventory.view_stockledgerentry` (Chủ, Quản lý, Nhân viên kho). Không có cột giá vốn nào ở màn này.
- `balance_after` do BE tính (tồn của lô sau dòng đó). FE không tự cộng trừ.
- Cột Chứng từ: `reference_display` (KK-n, RT-n, SR-n, PR-n, mã hoá đơn, mã đơn, mã lô). Có link khi `referenceRoutes.ts` ghi `ready: true`.
  Hiện chỉ `batch` có trang đích; các loại khác là chữ thường cho tới khi lô tương ứng làm xong trang chi tiết.
- `components/LedgerTable.tsx` dùng chung với tab "Nhập xuất gần đây" ở `/inventory/` và chi tiết lô.

| File | Làm gì |
|---|---|
| `api.ts` | `fetchLedger()`, `ledgerQuery()` |
| `mock.ts` | handler mock R6 (dữ liệu sinh từ kho lô của `features/inventory/mock.ts`) |
| `referenceRoutes.ts` | bảng loại chứng từ → trang đích |
| `types.ts` | `LedgerEntry`, `LedgerParams`, `MovementType` |
| `components/LedgerTable.tsx` | bảng 8 cột dùng chung |
| `components/LedgerScreen.tsx` | màn `/ledger/` |
