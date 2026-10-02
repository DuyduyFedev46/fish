# Danh mục & giá (`features/catalog`)

Màn ERP cho Chủ, Quản lý và NV kho (ED-30, ED-31, Lô 13). Tất cả giá ở đây là giá BÁN. Không có giá vốn.

## Trang

| Đường dẫn | Việc | Quyền |
|---|---|---|
| `/catalog/` | Bốn tab (`?tab=items|prices|rules|groups`): Mặt hàng, Bảng giá, Ưu đãi, Nhóm hàng | `catalog.view_item`; tab giá cần `view_itemprice`, tab ưu đãi cần `view_pricingrule`, tab nhóm cần `view_itemgroup` |
| `/catalog/detail/?id=` | Chi tiết mặt hàng: sửa tên và mô tả tại chỗ, Đặt giá mới, tải ảnh, ẩn khỏi Shop, thành phần combo, lịch sử giá, Trợ lý AI, dòng thời gian | `catalog.view_item`; ghi chỉ Chủ |
| `/catalog/new/` và `/catalog/new/?type=BUNDLE` | Thêm mặt hàng, thêm combo (công thức gửi riêng sau khi tạo mặt hàng) | `catalog.add_item` |
| `/catalog/rules/new/` | Tạo ưu đãi giảm giá | `catalog.add_pricingrule` |

NV kho chỉ thấy tab Mặt hàng và không thấy cột hay ô nào của giá (BE không trả `current_price`). Quản lý xem được cả bốn tab, không có nút ghi.

## Quyết định #10 (Duy)

Sửa giá cho phép, nhưng giá nằm trong đơn đã đặt KHÔNG đổi. Giá áp dụng "từ ngày". Vì vậy:

- Hộp "Đặt giá mới" mặc định "Áp dụng từ" là NGÀY MAI (giờ Việt Nam). Ngày trước hôm nay bị chặn ngay trên form, kèm gợi ý "từ ngày mai", vì BE chỉ từ chối lùi ngày khi đã có đơn trong khoảng đó.
- Giá đã có đơn dùng: BE trả `PRICE_USED_BY_ORDERS`, hộp hiện nguyên văn câu của BE (đã bỏ mã quy tắc ở `shared/lib/http.ts`), giữ số đã nhập, nút chính đổi "Thử lại".
- Không có sửa hay xoá một dòng giá cũ. Muốn đổi giá thì đặt giá mới.

## File

- `types.ts`, `api.ts`, `mock.ts`: kiểu, hàm gọi API (mỗi hàm có nhánh mock), dữ liệu mẫu và các chế độ lỗi (`window.__caveMock.catalog("fail" | "empty" | "forbidden" | "detailfail" | "savefail" | "priceUsed" | "pricesfail")`, `resetCatalog()`).
- `permissions.ts`: mã quyền và `catalogAbility(perms)` cho biết người xem được làm gì.
- `catalogModel.ts`: hàm thuần (kiểm form, đổi nháp thành thân gửi, chữ hiển thị). Có test ở `catalog.test.ts`.
- `messages.ts`: toàn bộ chữ tiếng Việt của màn.
- `useCatalogList.ts`, `useCatalogOptions.ts`, `useItemDetail.ts`, `useItemTimeline.ts`: tải danh sách phân trang, danh sách chọn (đọc hết các trang), một mặt hàng, dòng thời gian.
- `components/`: `CatalogScreen` (khung bốn tab), `ItemListTab`, `PriceListTab`, `PricingRuleList`, `ItemGroupList`, `ItemDetailScreen`, `ItemForm`, `PricingRuleForm`, `SetPriceModal`, `ItemGroupModal`, `ImageUploadSheet`, `ItemThumb`.

## Chuyện cần nhớ

- `listItems("all")` vẫn dùng được: form Nhập lô (`features/purchasing`) gọi nó để lấy danh sách chọn mặt hàng.
- Ô tìm ở tab Mặt hàng chỉ lọc trong phần đã tải vì BE chưa có tham số `q`. Bộ lọc nhóm, trạng thái, ảnh, loại chạy phía server.
- Tạo combo là hai bước (mặt hàng rồi từng dòng công thức). Nếu một dòng lỗi, mặt hàng đã có: form khoá phần đã lưu và "Thử lại" chỉ gửi các dòng còn thiếu.
- Bộ lọc, từ khoá, tên, giá không ghi vào URL, localStorage hay log. URL chỉ có id số, `type` và `tab`.
