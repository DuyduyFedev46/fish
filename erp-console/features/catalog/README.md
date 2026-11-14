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
- `components/`: `CatalogScreen` (khung bốn tab), `ItemListTab`, `PriceListTab`, `PricingRuleList`, `ItemGroupList`, `ItemDetailScreen`, `ItemForm`, `PricingRuleForm`, `SetPriceModal`, `ItemGroupModal`, `ImageUploadModal`, `ItemThumb`.

## Chuyện cần nhớ

- `listItems("all")` vẫn dùng được: form Nhập lô (`features/purchasing`) gọi nó để lấy danh sách chọn mặt hàng.
- Ô tìm ở tab Mặt hàng chỉ lọc trong phần đã tải vì BE chưa có tham số `q`. Bộ lọc nhóm, trạng thái, ảnh, loại chạy phía server.
- Tạo combo là hai bước (mặt hàng rồi từng dòng công thức). Nếu một dòng lỗi, mặt hàng đã có: form khoá phần đã lưu và "Thử lại" chỉ gửi các dòng còn thiếu.
- Bộ lọc, từ khoá, tên, giá không ghi vào URL, localStorage hay log. URL chỉ có id số, `type` và `tab`.

## Mã giảm giá (SHOP-3b-02)

Màn riêng `/vouchers/` (danh sách), `/vouchers/new/`, `/vouchers/edit/?id=`. Chỉ người có `catalog.manage_voucher` (Chủ, hoặc người Chủ uỷ) thấy menu và vào được; người khác nhận "không có quyền" và không có request nào được gọi.

- `voucherModel.ts`: hàm thuần (kiểm form, nháp ↔ thân gửi, trường khoá khi mã đã chạy, đọc lỗi `fields` của BE). Giờ nhập là GMT+7 qua `vnInputToIso`. Test ở `voucher.test.ts`.
- `voucherMock.ts`: mock đúng 02b §3.9 (chỉ chạy khi `NEXT_PUBLIC_USE_MOCK=1`), gọi từ `mock.ts`; `window.__caveMock.resetCatalog()` đưa mã về seed.
- `components/VoucherList`, `VoucherForm` (tạo và sửa), `VoucherDisableDialog` (bắt chọn lý do), `VoucherRedemptions` (chỉ mã đơn, số giảm, giờ, trạng thái, không có thông tin khách).
- Mã và kiểu giảm không đổi sau khi tạo; từ `starts_at` chỉ sửa được theo hướng có lợi cho khách (BR-DM-22). Không có nút xoá.

## Tải và nhập file Excel mặt hàng (FISH-66)

Hồ sơ: `doc/features/2026-11-14-hang-ban-excel-dong-lanh/` (02a, 02b §3 và §10; S3–S6).

- Endpoint tải: `GET /api/catalog/items/export/?item_group=&is_active=&item_type=&has_image=` và `GET /api/catalog/items/export-template/`. Trả file .xlsx, tên lấy từ `Content-Disposition`, số món từ `X-Row-Count`. Số cột do BE quyết theo quyền (Chủ, Quản lý 17 cột; NV kho 14 cột, không có giá bán).
- Endpoint nhập: `GET /api/catalog/items/import/limits/`, `POST /api/catalog/items/import/preview/` (`multipart/form-data: file`), `POST /api/catalog/items/import/commit/` (`multipart/form-data: file, preview_token`). Chỉ người có đủ 4 quyền `IMPORT_PERMS` mới gọi được.
- `itemFilesApi.ts`, `itemFilesTypes.ts`, `itemFilesModel.ts`, `itemFilesMock.ts` (`window.__caveMock.itemFiles("ok" | "fail" | "forbidden" | "rowErrors" | "noChanges" | "dataChanged" | "expired" | "alreadyApplied")`). Hàm tải chung `apiDownload` ở `shared/lib/http.ts`, lưu file bằng `saveBlob` ở `shared/lib/download.ts`.
- `components/ItemFileActions.tsx`: nút "Tải file Excel" và menu "…" có "Tải file mẫu" cho ai có `catalog.view_item`. Nút "Nhập từ Excel" hiện khi `ability.canImport` (trỏ `/catalog/import/`).
- `components/ItemImportScreen.tsx`, `ImportPreview.tsx`, `ImportErrors.tsx`, `ImportConfirmModal.tsx`: luồng M2–M6 theo 02a §3–§5.
- FE không đọc hay ghi xlsx. File và `preview_token` chỉ nằm trong state của trang, không vào URL hay storage. Test ở `itemFilesDownload.test.ts` và `itemFiles.test.ts`.
