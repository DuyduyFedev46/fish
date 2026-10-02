# Kiểm kê (ED-28)

Phiếu kiểm kê: đếm số thực tế từng LÔ, so với tồn trên sổ, người có quyền duyệt rồi thì tồn kho được điều chỉnh.
Chủ, Quản lý và Nhân viên kho vào được. Nhân viên giao và CSKH không có mục này.

## Màn hình

| Đường dẫn | Màn | File |
|---|---|---|
| `/stocktake/` | Danh sách phiếu (W2c): lọc kho, trạng thái, tìm; cột kho, số lô, hụt, dư | `components/StocktakeListScreen.tsx` |
| `/stocktake/new/` | Lập phiếu (F1f) | `components/StocktakeForm.tsx` (`mode="new"`) |
| `/stocktake/edit/?id=` | Sửa số đếm phiếu chờ duyệt | `components/StocktakeForm.tsx` (`mode="edit"`) |
| `/stocktake/detail/?id=` | Chi tiết (W2g): đường đi trạng thái, bảng chênh lệch, Trợ lý AI, dòng thời gian, nút Duyệt | `components/StocktakeDetailScreen.tsx` |

URL chỉ mang `?id=`. Không có tên khách, số điện thoại hay địa chỉ ở module này; chỉ có tên nhân viên.

## File trong module

- `types.ts`: kiểu dữ liệu theo contract thật của BE (`backend/apps/inventory/stocktake/`).
- `api.ts`: gọi `/api/inventory/reconciliations/…`, nạp kho và lô còn tồn. Mỗi hàm có nhánh mock.
- `mock.ts`: BE giả có trạng thái (lưu `localStorage` chỉ để thử khi `NEXT_PUBLIC_USE_MOCK=1`). Công cụ thử ở `window.__caveMock` (xem cuối file).
- `stocktakeUi.ts`: hàm thuần (đọc số kg, kiểm dòng, câu lỗi của BE). Có test ở `stocktakeUi.test.ts`.
- `stocktake.module.css`: kiểu của form và trang chi tiết, chỉ dùng token.

## Quy tắc đã nối

- Chọn kho chỉ để nạp lô còn tồn (`batches/?warehouse=&has_stock=1`); phiếu tính theo lô.
- Lô đếm nhiều hơn sổ phải ghi lý do (BR-KK-04). Không nhập số âm, không trùng lô.
- Tồn hệ thống hiện trong form chỉ để xem trước; BE chụp lại tồn mỗi lần lưu (BR-KK-01).
- Người lập phiếu và người đã sửa số đếm không tự duyệt được (BR-KK-02, BR-KK-08): nút Duyệt nằm mờ trong "…" kèm lý do BE trả.
- Hai người cùng sửa: BE trả 409 `STALE_STATE`, màn hiện ConflictBanner "Phiếu vừa được <tên> sửa lúc …".
- Không có số tiền: chênh lệch chỉ tính bằng kg (bất biến 1).
- Không xoá phiếu (BR-PQ-10).
