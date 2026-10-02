# Kế toán: hoá đơn bán, hoá đơn mua, chi phí phụ (ED-33, ED-34)

Ba việc: xem **Hoá đơn bán** (chỉ đọc), xem và thêm **Hoá đơn mua**, xem và thêm **Chi phí phụ** của lô nhập (chia vào giá vốn). Hai màn đường dẫn riêng: `/accounting/sales-invoices/` và `/accounting/purchase-invoices/`. Danh sách hoá đơn mua và chi phí cũng còn nằm ở tab của màn Mua hàng (Lô 10) nên hai component danh sách nhận `panelId` và `homeHref` để dùng được ở cả hai nơi.

| File | Việc của file |
|---|---|
| `types.ts` | Kiểu dữ liệu: hoá đơn mua, chi phí phụ, hoá đơn bán (`SalesInvoiceRow`, `SalesInvoiceTotals`). |
| `api.ts` | Hàm gọi API, gồm `fetchSalesInvoices(params, page)` (Lô 12). Có nhánh mock khi `NEXT_PUBLIC_USE_MOCK=1`. |
| `money.ts` | Ô tiền, kiểm tra số tiền, `suggestedAmount` (gợi ý số tiền hoá đơn từ tiền mua, làm tròn đồng). |
| `receiptOptions.ts` | Phần thuần cho bộ chọn phiếu nhập: nhãn, gộp trang tải thêm, giữ phiếu đang chọn. |
| `costAllocation.ts`, `months.ts` | Chia chi phí vào lô; danh sách tháng lọc. |
| `components/SalesInvoiceListScreen.tsx` | Hoá đơn bán: tìm, lọc trạng thái và ngày xuất, tổng ở chân bảng, ghi chú về đơn huỷ. |
| `components/PurchaseAccountingScreen.tsx` | Màn "Hoá đơn mua & chi phí" có hai tab theo quyền. |
| `components/PurchaseInvoiceList.tsx`, `PurchaseInvoiceForm.tsx` | Danh sách và hộp "Thêm hoá đơn mua" (có "Đã trả tiền" + "Trả lúc"). |
| `components/PurchaseCostList.tsx`, `PurchaseCostForm.tsx` | Danh sách chi phí phụ và form nhập chi phí. |
| `components/ReceiptSelect.tsx` | Bộ chọn phiếu nhập có lọc nhà cung cấp ở máy chủ và "Tải thêm" (BE chưa có tìm theo chữ cho phiếu nhập). |
| `accounting.module.css` | Kiểu riêng, chỉ dùng token trong `DESIGN.md`. |
| `mock.ts` | Dữ liệu giả (xem mục Mock). |

## Quyền

- Hoá đơn bán: `sales.view_salesinvoice` (Chủ, Quản lý, Nhân viên kho). Cột Giá vốn, Lãi gộp và dòng Lãi gộp ở chân bảng chỉ có khi người xem có quyền xem giá vốn. Tên khách chỉ có khi có quyền xem khách hàng; nếu không thì cả cột ẩn.
- Hoá đơn mua: Chủ và Quản lý xem (Quản lý thấy số tiền, quyết định D-3); chỉ Chủ thêm.
- Chi phí phụ: chỉ Chủ.
- Người không có quyền vào thẳng URL thấy "Không có quyền", màn không gọi API.

## Mock

`window.__caveMock.salesInvoices("ok" | "fail")` cho hoá đơn bán (27 hoá đơn, 3 đã huỷ, tên khách bịa có "(mẫu)"). Phần hoá đơn mua / chi phí dùng mock của `features/purchasing`.
