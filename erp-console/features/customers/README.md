# Khách hàng (ED-14)

Danh bạ khách của vựa: xem, tìm, sắp xếp, mở hồ sơ, sửa tên, địa chỉ giao mặc định và ghi chú. Số điện thoại là khoá của khách nên chỉ đọc.

| File | Việc của file |
|---|---|
| `types.ts` | Kiểu dữ liệu theo contract BE (`customer-directory`): dòng danh sách, chi tiết, đơn, phiếu hoàn, gói PATCH. |
| `api.ts` | Hàm gọi API: `listCustomers`, `getCustomer`, `updateCustomer`, `getCustomerTimeline`. Có nhánh mock khi `NEXT_PUBLIC_USE_MOCK=1`. |
| `customersModel.ts` | Phần thuần (không React): các kiểu sắp xếp, giới hạn độ dài, kiểm tra ô nhập, tính gói PATCH chỉ gồm trường đổi, chọn câu lỗi. |
| `messages.ts` | Câu chữ tiếng Việt do FE tự sinh. Lỗi nghiệp vụ của BE được hiện nguyên văn. |
| `useCustomerList.ts` | Tải danh sách theo từ khoá và kiểu sắp xếp, có "Tải thêm". |
| `useCustomerDetail.ts` | Đọc `?id=` (chỉ nhận số nguyên dương) và tải hồ sơ khách. |
| `useCustomerTimeline.ts` | Tải dòng thời gian của khách, tải lại sau mỗi lần lưu. |
| `components/CustomerListScreen.tsx` | Màn danh sách. |
| `components/CustomerDetailScreen.tsx` | Màn chi tiết: sửa tại chỗ, bảng đơn, bảng phiếu hoàn, dòng thời gian. Không có khối AI. |
| `components/EditCustomerModal.tsx` | Hộp "Sửa thông tin" (tên, địa chỉ, ghi chú). |
| `customers.module.css` | Kiểu riêng, chỉ dùng token trong `DESIGN.md`. |
| `mock.ts` | Dữ liệu giả để chạy khi chưa có BE (xem mục Mock). |
| `customers.test.ts` | Kiểm thử đơn vị: mô hình, câu truy vấn, quyền, tìm kiếm, sắp xếp, PATCH. |

## Dữ liệu cá nhân

Tên, số điện thoại, địa chỉ chỉ nằm trong bộ nhớ của trang. Không đưa vào URL (chỉ có `?id=`), `localStorage`, `sessionStorage`, nhật ký trình duyệt hay AI. Từ khoá tìm kiếm chỉ nằm trong trạng thái của màn, không lên URL.

## Quyền

- Xem danh sách và hồ sơ: `sales.view_customer_list` (Chủ, Quản lý).
- Sửa: thêm `sales.change_customer`. Người không có quyền xem vào thẳng URL thì thấy "Không có quyền".

## Mock

`window.__caveMock.customers(chế_độ)` với `ok`, `fail`, `empty`, `forbidden`, `detailfail`, `patchfail`. Chế độ lưu ở `localStorage` (khoá `cave_erp_mock_customers_mode`), không chứa dữ liệu khách. Dữ liệu giả về trạng thái đầu mỗi khi tải lại trang.
