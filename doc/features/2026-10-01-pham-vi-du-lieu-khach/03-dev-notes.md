# Phạm vi dữ liệu khách theo vai: ghi chú dev

Luồng NHANH, 2026-10-01. Story: `02-stories.md` (SR-PII-01, SR-PII-02). Quyết định Duy: Q-1, Q-2, Q-3 ở `doc/features/2026-09-30-ra-soat-agy/q1-pii-xac-minh.md`.

## BE

### File đã sửa / thêm
- Mới `backend/apps/accounts/migrations/0012_revoke_customer_view_warehouse_staff.py`: data migration gỡ `sales.view_customer` khỏi Group `nv_kho`.
- Mới `backend/apps/delivery/pii_scope.py`: nguồn duy nhất cho cửa sổ xem dữ liệu khách của NV giao.
- Sửa `backend/apps/sales/customers/api.py`, `serializers.py`: NV giao chỉ thấy khách trong cửa sổ, serializer riêng `CourierCustomerSerializer`.
- Sửa `backend/apps/sales/orders/api.py`, `serializers.py`: ẩn dữ liệu khách của đơn quá cửa sổ, giới hạn tìm kiếm theo SĐT/tên.
- Sửa `backend/apps/delivery/api.py`, `serializers.py`: ẩn dữ liệu khách của phiếu quá cửa sổ.
- Sửa `backend/config/settings.py`: thêm `DELIVERY_PII_RECENT_DAYS` (env cùng tên, mặc định 7). Ghi vào `doc/ops/moi-truong.md`.
- Test mới `backend/apps/common/tests/test_customer_data_scope.py` (32 test). Sửa 1 test cũ `test_s5_scope_nv_giao.py::test_s5_ac4_kiem_nhiem_nv_kho_va_nv_giao_thay_moi_don` (xem "Điểm cần Duy/techlead biết").

### Migration `accounts/0012_revoke_customer_view_warehouse_staff`
- Operations: một `RunPython(revoke_view_customer, restore_view_customer)`. Không đổi bảng; `sqlmigrate` chỉ in `BEGIN; ... COMMIT;`.
- `revoke_view_customer`: `group.permissions.remove(sales.view_customer)` cho Group `nv_kho`. Idempotent, chạy lại không đổi. Group khác không đụng tới (có test).
- Reverse `restore_view_customer`: `add` lại quyền, cũng idempotent.
- Phụ thuộc: `accounts.0011_seed_group_cskh`, `sales.0006_salesorder_checkout_attempts`. Lô 4 dùng số `0013`.
- Đã chạy trên SQLite sạch: `migrate` OK (nv_kho mất quyền, `chu`, `quan_ly`, `nv_giao` giữ, `cskh` vốn không có), `migrate accounts 0011` trả quyền lại, `migrate` lần nữa gỡ lại.

### Contract thay đổi
Quy ước chọn: **giữ khoá JSON, giá trị `null`** khi dữ liệu khách bị ẩn. Vai khác (`chu`, `quan_ly`, `nv_kho`, `cskh`) không đổi khoá, không đổi giá trị.

Cửa sổ: phiếu giao gán cho NV giao ở trạng thái `COMPLETED` hoặc `CANCELLED` thì còn thấy tới **hết ngày lịch thứ N** kể từ ngày kết thúc (giờ VN), N = `DELIVERY_PII_RECENT_DAYS`. Từ 00:00 ngày kế tiếp thì ẩn. Phiếu chưa kết thúc, kể cả `FAILED` (có thể quay lại `DELIVERING`), luôn thấy. Mốc kết thúc là `completed_at`; phiếu `CANCELLED` không có mốc riêng nên dùng `created_at`.

| Endpoint | NV giao, phiếu còn trong cửa sổ | NV giao, phiếu quá cửa sổ |
|---|---|---|
| `GET /api/sales/orders/` | như cũ | dòng vẫn có, `customer_name: null`, `customer_phone: null` |
| `GET /api/sales/orders/<id>/` | như cũ | `customer: {"name": null, "phone": null, "address": null}`, mọi khoá khác như cũ |
| `GET /api/sales/orders/?q=` | tìm mã, SĐT, tên như cũ | tìm theo mã đơn vẫn chạy; tìm theo SĐT hoặc tên không khớp đơn này (chống dò) |
| `GET /api/delivery/notes/`, `/<id>/`, response của `POST .../status/` | như cũ | dòng vẫn có (mã, trạng thái, số kg, dòng hàng), `customer_name: null`, `address: null`, `note: null`; chi tiết thêm `recipient_name: null` |
| `GET /api/sales/customers/`, `/<id>/` | chỉ `id`, `phone`, `name`, `created_at` | khách chỉ có phiếu quá cửa sổ **không được trả** (vắng trong danh sách, chi tiết 404); khách còn phiếu trong cửa sổ vẫn hiện |

Ví dụ khách của NV giao (đã bỏ `note`, `default_address`):
```json
{"id": 12, "phone": "0911000001", "name": "Sentinel Ten Alpha", "created_at": "2026-09-30T08:00:00+07:00"}
```
Vai khác ở `/api/sales/customers/`: `chu`, `quan_ly` vẫn đủ `id, phone, name, default_address, note, created_at`. `nv_kho`: 403 cả danh sách và chi tiết. `cskh`: vẫn 403 như cũ.

Phạm vi dòng giữ nguyên (AC5): NV giao ngoài phiếu của mình vẫn 404.

### Business rule
- BR-PQ-12 (phạm vi dòng NV giao), bất biến 9 (dữ liệu cá nhân chỉ lộ cho ai cần). Đề xuất mã rule BR-PQ-15 (phạm vi dữ liệu cá nhân theo Group) do BA ghi vào spec như q1-pii-xac-minh đã nêu.

### Test (đỏ -> xanh)
- Đỏ trước: 13 failure và 2 error trên 32 test (cửa sổ 8 ngày vẫn lộ, nv_kho vẫn 200 ở customers, `note`/`default_address` còn ở nv_giao, thiếu migration). Sau khi cài: 32 test xanh.
- Ma trận Group x 3 endpoint: `chu`, `quan_ly`, `nv_kho`, `nv_giao`, `cskh`, kiêm nhiệm `nv_kho + nv_giao`, chưa đăng nhập (401), có đếm `count > 0` và quét chuỗi sentinel giả.
- Ca phiếu kết thúc 6 ngày (vẫn thấy) và 8 ngày (ẩn); mốc biên 00:01 ngày D-7 (thấy) và 23:59 ngày D-8 (ẩn) theo giờ VN; đổi `DELIVERY_PII_RECENT_DAYS` bằng `override_settings`.
- `nv_kho`: 403 customers, vẫn thấy tên, SĐT đầy đủ, địa chỉ ở orders và delivery notes.
- Toàn bộ backend: `Ran 1746 tests ... OK` (gốc 1714, thêm 32). `makemigrations --check --dry-run`: No changes detected. `python3 scripts/check_naming.py`: OK, không phát sinh mới.

### Điểm cần Duy/techlead biết
1. **Người kiêm nhiệm `nv_kho + nv_giao`** không còn thấy toàn bộ danh bạ khách: quyền `view_customer` của họ nay đến từ `nv_giao` nên họ chỉ thấy khách của phiếu gán cho mình (theo đề xuất A.2 của techlead), nếu không thì kiêm nhiệm vòng qua được Q-1. Đơn và phiếu giao của họ vẫn full scope (Q-2). Vì vậy đã sửa test cũ `test_s5_ac4_...` (kỳ vọng cũ: thấy cả 4 khách).
2. **Phiếu CANCELLED không có mốc kết thúc** trong DB. Dùng `created_at` thay, nên có thể ẩn dữ liệu sớm hơn 7 ngày kể từ lúc huỷ (phiên bản an toàn cho dữ liệu cá nhân). Muốn chính xác thì cần thêm cột (đổi schema, cần Duy duyệt) hoặc đọc `AuditLog`.
3. **`FAILED` coi là chưa kết thúc** (trạng thái tạm, có thể giao lại), nên phiếu FAILED cũ vẫn thấy dữ liệu khách. Nếu Duy muốn "thất bại quá N ngày thì ẩn" cần thêm mốc thời gian lúc FAILED (hiện chỉ có `failed_attempts`).
4. Tên Group trong migration 0012 viết thẳng `"nv_kho"` thay vì `roles.WAREHOUSE_STAFF`, theo mẫu 0011: migration phải đóng băng tên Group lúc chạy; nếu import `roles` mà Lô 4 đổi giá trị thì 0012 trên DB mới sẽ không tìm thấy Group và bỏ qua âm thầm. Dòng có `# naming: allow` kèm lý do.
5. Khách có phiếu của nhiều NV giao: mỗi người chỉ thấy theo phiếu gán cho mình.
6. Người dùng không thuộc Group nào nhưng được gán quyền trực tiếp: coi như NV giao (phạm vi và serializer của NV giao, chỉ đọc).
7. Dashboard không còn trả tên khách hay 4 số cuối SĐT cho `nv_kho` (SR-17 đã đóng BM-02, techlead chạy thật xác nhận). Mục này trong bản ghi đầu của tôi sai, đã bỏ.

## Việc FE cần làm (giao `fe-dev`, không bắt buộc để không vỡ)
ERP không crash khi nhận `null` (các chỗ dùng đều đã có `|| "—"` hoặc render rỗng), nhưng nên chỉnh để hiển thị đúng ở màn NV giao:
- `erp-console/features/orders/types.ts` (`customer_name`, `customer_phone`, `customer.name/phone/address`) và `features/deliveries/types.ts` (`customer_name`, `address`, `note`): đổi kiểu thành `string | null`.
- `features/orders/components/OrderDetailView.tsx` (dòng 222-239): khi `customer.address` là `null` đang hiện chuỗi `ORDERS_MSG.noAddress` ("chưa có địa chỉ"); nên hiện "Đã ẩn (quá 7 ngày)" cho trường hợp `null` của NV giao. Cùng ý cho `OrderDetailSheet.tsx:177`, `CancelOrderForm.tsx:82`, `ConfirmPaymentForm.tsx:112`, và `DeliveriesView.tsx:135-174`, `DeliveryDetailModal.tsx:235-240`.
- Không còn `tel:` link khi `phone` là `null` (OrderDetailView đã có nhánh `phone ? <a> : ...`).
- Không có màn ERP nào gọi `/api/sales/customers/` nên không bị ảnh hưởng bởi 403 của `nv_kho` hay serializer mới.

## FE

Lô NHANH, 2026-10-01, chỉ trong `erp-console/`. Không gọi thêm API, không đổi màn của vai khác.

### Quyết định hiển thị
- Khi BE trả `null` (dữ liệu khách bị ẩn theo thời hạn) hiện chữ mờ thống nhất **"Đã ẩn (quá 7 ngày)"** (`MSG.personalDataHidden`). Trường rỗng thật (`""`, ví dụ khách chưa có địa chỉ) hiện như cũ ("Chưa có địa chỉ", "—").
- Một nguồn duy nhất: `shared/lib/personalData.ts` (`personalText`) và `shared/ui/PersonalText.tsx`. Chữ "7 ngày" viết cứng theo yêu cầu của Duy; nếu đổi `DELIVERY_PII_RECENT_DAYS` thì chữ này phải sửa tay ở `shared/lib/messages.ts`.
- Danh sách Giao hàng: khi cả tên và địa chỉ đều `null` chỉ hiện MỘT dòng "Đã ẩn", không lặp hai dòng.
- Hàng SĐT ở chi tiết đơn: `null` thì không có link `tel:`.

### Phân biệt "đã ẩn" và "rỗng thật"
- Đơn: `customer_name`, `customer_phone`, `customer.{name,phone,address}` chỉ `null` khi bị ẩn, nên `null` là tín hiệu đủ tin cậy.
- Phiếu giao: `customer_name`, `address`, `note` BE trả `""` khi rỗng thật (`or ""`), `null` khi ẩn, nên dùng được.
- **Ngoại lệ, BE không phân biệt được:** `recipient_name` ở chi tiết phiếu là `obj.recipient_name or None`, tức rỗng thật cũng là `null`. FE không dùng nó làm tín hiệu, mà lấy `customer_name === null` để biết "đã ẩn" (`DeliveryDetailModal`). Nếu muốn dùng `recipient_name` thì BE cần trả `""` cho rỗng thật.

### File đã sửa / thêm
- Mới: `shared/lib/personalData.ts`, `shared/ui/PersonalText.tsx`; thêm `MSG.personalDataHidden` ở `shared/lib/messages.ts`.
- Kiểu `string | null`: `features/orders/types.ts` (`OrderListItem.customer_name/customer_phone`, `OrderDetail.customer.*`), `features/deliveries/types.ts` (`customer_name`, `address`, `note`).
- Hiển thị: `OrderDetailView` (Khách, SĐT, Địa chỉ), `OrderDetailSheet` (subLabel), `CancelOrderForm`, `ConfirmPaymentForm`, `OrdersScreen` (dòng danh sách), `AttachOrderForm`, `DeliveriesView` (bảng và thẻ), `DeliveryDetailModal` (Người nhận, Địa chỉ giao, Ghi chú đơn).
- Không đụng: các màn hoàn tiền và hàng chờ thanh toán (kiểu `customer_name?: string` riêng, vai NV giao không vào được), module `confirmation`.
- Mock: `features/orders/mock.ts` ẩn dữ liệu cho người có phạm vi giao hạn chế (xem F2 bên dưới) với đơn có phiếu COMPLETED/CANCELLED kết thúc trước đầu ngày (hôm nay − 7), tìm theo SĐT/tên không khớp đơn đã ẩn. Đơn cũ thứ 42 (id 143) được đặt lại thành đơn của giao1 giao xong ~10 ngày trước (tổng vẫn 45 đơn). `features/deliveries/mock.ts` thêm phiếu 40 (hoàn tất 10 ngày trước, giao1, bị ẩn) và 41 (hoàn tất hôm qua, giao1, còn thấy); NV giao chỉ thấy phiếu gán cho mình.

### Lưu ý
- NV giao thuần (chỉ nhóm nv_giao) **không vào được** `/orders/` và `/deliveries/` trên ERP (menu ẩn, `ViewGuard` chặn; màn "Việc giao của tôi" còn là Placeholder S20). Người thực sự thấy chữ "Đã ẩn" ở hai màn này hiện nay là người kiêm nhiệm có nv_giao mà không có chủ/quản lý/NV kho, ví dụ cskh + nv_giao (xem F2). Lượt trước phải tạm tắt `ViewGuard` để chụp; lượt F2 không còn cần (không đụng `ViewGuard`).
- Mock bỏ qua `completed_from` nên tab "Hoàn tất (hôm nay)" của mock hiện cả phiếu 10 ngày trước (BE thật không hiện).

### Kiểm
- Đỏ trước: 3 file test mới (`shared/lib/personalData.test.ts`, `features/orders/orders_personal_data.test.ts`, `features/deliveries/deliveries_personal_data.test.ts`) fail; sau khi cài xanh.
- `npx tsc --noEmit`: sạch. `npm test`: 19 file, 230 test xanh.
- Playwright trên build mock (cổng 3251, giao1, desktop 1280 và 360px, assert DOM): 20 PASS, 0 FAIL. Gồm: danh sách và chi tiết đơn cũ hiện "Đã ẩn (quá 7 ngày)" (3 trường, không link `tel:`, không còn "Chưa có địa chỉ"); đơn mới thấy tên và SĐT; Giao hàng: phiếu cũ "đã ẩn" đúng 1 lần, phiếu mới thấy tên; modal phiếu cũ ẩn Người nhận, Địa chỉ, Ghi chú; không cuộn ngang ở 360px; Chủ vẫn thấy đủ dữ liệu đơn 143. Ảnh (không bắt buộc xem): `scratchpad/pii-fe/*.png`.
- Build thật (`NEXT_PUBLIC_USE_MOCK=0 npm run build`): sạch; `check-no-mock`: XANH; `check-ai-chunks`: XANH; `python3 scripts/check_naming.py`: exit 0.

### Sửa theo review Tech Lead (F1, F2)

- **F1.** `shared/lib/messages.ts`: khối `personalDataHidden` (kèm JSDoc) chuyển xuống sau `noViewPermissionHint`; comment S7-AC3 về lại đúng khoá `noViewPermission`.
- **F2.** Hàm dùng chung `hasLimitedCourierScope(me)` trong `shared/lib/personalData.ts`: có `ROLE.deliveryStaff` và KHÔNG có `ROLE.owner`/`ROLE.manager`/`ROLE.warehouseStaff` (đảo của BE `has_full_delivery_scope`). Thay `onlyDelivery(me)` ở `features/orders/mock.ts` (`inScope`, `piiHidden`) và `features/deliveries/mock.ts` (`viewFor`, `inCourierScope`); cả hai cùng dùng hàm này cho phạm vi "chỉ thấy phiếu gán cho mình" và việc ẩn dữ liệu khách. `nav.ts` (`onlyDelivery`) giữ nguyên vì chỉ quyết menu. Khác BE: `Me` không có `is_superuser` nên mock không xét superuser (superuser mock `admin` không có Group nên không bị ảnh hưởng).
- **User mock mới `cs2`** (id 12, "Chị Đào", cskh + nv_giao, mật khẩu `demo1234`, dữ liệu giả) trong `features/auth/mock.ts`. Đơn 142 (giao xong 11 ngày trước, gán cs2) thế chỗ đơn cũ thứ 41 nên tổng vẫn 45 đơn. Phiếu 42 (hoàn tất 11 ngày trước, bị ẩn) và 43 (hoàn tất hôm qua, thấy đủ), cùng gán cs2.
- **Test:** `hasLimitedCourierScope` (6 trường hợp tổ hợp Group), phiếu cs2 ẩn/hiện và kho1 thấy đủ, đơn 142 cs2 ẩn và kho1 thấy đủ.
- **Playwright** (build mock, cổng 3252, assert DOM, không tắt `ViewGuard`, 1280px và 360px): đăng nhập `cs2`, vào được `/orders/` và `/deliveries/`; Đơn: chỉ 1 đơn gán cho mình, dòng và chi tiết đơn 142 hiện "Đã ẩn (quá 7 ngày)" ở 3 trường; Giao hàng: phiếu 42 "đã ẩn" đúng 1 lần, phiếu 43 thấy tên, không lộ "Khách Thử K"/địa chỉ phiếu cũ; modal phiếu 42 ẩn Người nhận, Địa chỉ, Ghi chú; không cuộn ngang; đối chứng `kho1` và `loc` thấy đủ tên phiếu 42. Kết quả: 22 PASS, 0 FAIL (22 assert gồm cả hai cỡ màn). Server 3252 đã tắt.
- **Kiểm:** `npx tsc --noEmit` sạch; `npm test` 19 file, 236 test xanh; build thật (`NEXT_PUBLIC_USE_MOCK=0`) sạch; `check-no-mock` XANH; `check-ai-chunks` XANH; `python3 scripts/check_naming.py` exit 0, không vi phạm mới. `out/` là bản thật.
