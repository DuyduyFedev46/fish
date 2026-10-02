# Nhà cung cấp (ED-22)

Danh bạ nơi vựa nhập hàng: xem, tìm, lọc theo loại và trạng thái, mở hồ sơ, thêm, sửa, ngừng hợp tác và bật lại. Không có xoá (BE trả 405). Số điện thoại nhà cung cấp là dữ liệu đối tác nên hiện đủ, nhưng không đưa lên URL hay storage.

| File | Việc của file |
|---|---|
| `types.ts` | Kiểu dữ liệu theo contract BE Lô 11: nhà cung cấp, dòng phiếu nhập (R10), dòng lô đang bán (R5), gói tạo / sửa. |
| `api.ts` | Hàm gọi API: `listSuppliers`, `getSupplier`, `createSupplier`, `updateSupplier`, `setSupplierActive`, `listSupplierReceipts`, `listSupplierBatches`, `getSupplierTimeline`. Có nhánh mock khi `NEXT_PUBLIC_USE_MOCK=1`. |
| `suppliersModel.ts` | Phần thuần (không React): bộ lọc, giới hạn độ dài, kiểm tra ô nhập, gói PATCH chỉ gồm trường đổi, nhận ra lỗi trùng tên ở cả hai dạng 400 của BE. |
| `messages.ts` | Câu chữ tiếng Việt do FE tự sinh. Lỗi nghiệp vụ của BE được hiện nguyên văn. |
| `useSupplierList.ts` | Tải danh sách theo từ khoá, loại, trạng thái, có "Tải thêm" (50 dòng mỗi trang). |
| `useSupplierDetail.ts` | Đọc `?id=` (chỉ nhận số nguyên dương) và tải hồ sơ. |
| `useSupplierRelated.ts` | Bảng Phiếu nhập (có "Tải thêm") và bảng Lô đang bán của nhà cung cấp; mỗi bảng lỗi riêng, không làm hỏng cả trang. |
| `useSupplierTimeline.ts` | Dòng thời gian của nhà cung cấp, tải lại sau mỗi lần lưu. |
| `components/SupplierListScreen.tsx` | Màn danh sách; cột "Tổng tiền mua" khoá cho Chủ. |
| `components/SupplierDetailScreen.tsx` | Màn chi tiết: sửa tại chỗ (tên, số điện thoại, ghi chú), khối Mua hàng chỉ đọc, hai bảng, dòng thời gian, khối AI do trang truyền vào. |
| `components/SupplierFormModal.tsx` | Hộp "Thêm nhà cung cấp" và "Sửa nhà cung cấp". |
| `components/ConfirmActiveModal.tsx` | Hộp hỏi lại trước khi ngừng hợp tác hoặc bật lại. |
| `suppliers.module.css` | Kiểu riêng, chỉ dùng token trong `DESIGN.md`. |
| `mock.ts` | Dữ liệu giả để chạy khi chưa có BE (xem mục Mock). |
| `suppliers.test.ts` | Kiểm thử đơn vị: truy vấn, mô hình, quyền, giá vốn, trùng tên, ngừng / bật lại. |

## Quyền

- Xem: `purchasing.view_supplier` (Chủ, Quản lý, Nhân viên kho). Người khác vào thẳng URL thấy "Không có quyền".
- Thêm / sửa / ngừng hợp tác: `purchasing.add_supplier`, `purchasing.change_supplier` (Chủ, Quản lý).
- "Tổng tiền mua" và "Tiền mua" của phiếu: chỉ Chủ (`inventory.view_costprice`). Với người khác cột và ô không có trong DOM.
- Bảng Phiếu nhập cần `purchasing.view_purchasereceipt`, bảng Lô đang bán cần `inventory.view_batch`.

## Mock

`window.__caveMock.suppliers(chế_độ)` với `ok`, `fail`, `empty`, `forbidden`, `detailfail`, `savefail`, `racename`, `receiptsfail`, `batchesfail`. Chế độ lưu ở `localStorage` (khoá `cave_erp_mock_suppliers_mode`), không chứa dữ liệu nhà cung cấp. Dữ liệu giả về trạng thái đầu mỗi khi tải lại trang.
