# Review Tech Lead: phạm vi dữ liệu khách theo vai (SR-PII-01, SR-PII-02)

Người review: Tech Lead, ngày 01/10/2026. Phạm vi: phần BE chưa commit (`git diff` + 3 file mới ở `backend/`), đối chiếu
`02-stories.md`, `03-dev-notes.md`, `doc/features/2026-09-30-ra-soat-agy/q1-pii-xac-minh.md`. Không sửa code.
Phần FE (`erp-console/…`, xuất hiện trong lúc review) **không** nằm trong lần review này.

## Kết luận: **REVIEW PASS**

Không có lỗi chặn. Có 2 việc dọn nhỏ và 2 việc tài liệu, phải xong trước khi bắt đầu P8b Lô 4 (mục 4).

## 1. Lệnh kiểm chứng đã chạy (trong lượt review)

| Lệnh | Kết quả |
|---|---|
| `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.sales apps.delivery apps.common apps.accounts apps.reports` (không `--parallel`) | `Ran 1033 tests … OK` |
| `manage.py makemigrations --check --dry-run` | `No changes detected` |
| `python3 scripts/check_naming.py` | `OK - 6554 vi phạm cũ trong 203 file, không phát sinh mới.` |
| Probe tạm ở scratchpad (không để lại trong repo): `nv_kho` gọi `/api/dashboard/summary/` và `/api/dashboard/attention/` với khách có tên/SĐT/địa chỉ giả; NV giao PATCH phiếu đã quá cửa sổ | 2 test OK, chi tiết ở mục 3 |

## 2. Soát từng điểm

### 2.1 Migration `accounts/0012_revoke_customer_view_warehouse_staff`: đạt
- Chỉ có một `RunPython(revoke_view_customer, restore_view_customer)`, không đổi bảng. Dùng `.remove` và `.add`, không dùng `.set`,
  nên Group khác và quyền khác của `nv_kho` không bị đụng. Có test `test_sr_pii_01_ac1_other_groups_untouched_by_forwards`.
- Idempotent cả hai chiều. Không có Group hoặc Permission thì bỏ qua, đúng mẫu `0003` và `0011`. Test
  `test_sr_pii_01_ac4_forwards_idempotent_and_backwards_restores` gọi lại hàm nhiều lần.
- Việc viết thẳng `"nv_kho"` có `# naming: allow` là **đúng và bắt buộc**. Migration phải đóng băng tên Group tại thời điểm chạy.
  Nếu import `roles.WAREHOUSE_STAFF`, sau Lô 4 giá trị hằng thành `warehouse_staff`. Khi đó một DB mới chạy 0012 trước 0013
  sẽ tìm theo tên chưa tồn tại, rồi âm thầm bỏ qua, và `warehouse_staff` giữ `view_customer`. Đó sẽ là lỗi rò dữ liệu cá nhân.
- Thứ tự với Lô 4 đúng, nếu 02c Lô 4 được sửa số (mục 4, việc D1). Thứ tự chạy là 0012 (gỡ quyền theo tên `nv_kho`), rồi 0013
  (đổi tên giữ id). Quyền đi theo id nên `warehouse_staff` vẫn không có `view_customer`. Không có chỗ nào gán lại quyền: chỉ
  `0002` dùng `.set`, và 0002 đã chạy trước.
- Phụ thuộc `sales.0006` thừa nhưng vô hại. Không cần sửa.

### 2.2 `delivery/pii_scope.py`: đạt
- Cửa sổ: `pii_cutoff` là 00:00 giờ VN của ngày `hôm nay − N`. Phiếu kết thúc ngày D còn thấy tới hết ngày D+N, đúng chữ "N ngày
  lịch" ghi trong dev-notes. `TIME_ZONE = "Asia/Ho_Chi_Minh"` nên `localtime`/`get_current_timezone` là giờ VN. Có test mốc
  00:01 ngày D−7 (thấy) và 23:59 ngày D−8 (ẩn).
- Bản Q (`_within_window_q`) và bản Python (`is_note_pii_expired`) khớp nhau. Cả hai đều dùng `completed_at`, thiếu thì dùng `created_at`.
- **`CANCELLED` dùng `created_at`: chấp nhận.** Phiếu chỉ sang `CANCELLED` qua `cancel_paid_order`
  (`sales/orders/services.py:389-391`), là đơn đã huỷ, nên NV giao không còn việc gì cần dữ liệu khách. Lệch luôn theo hướng ẩn sớm
  hơn, tức hướng an toàn. Nếu sau này cần mốc chính xác thì không cần đổi schema, vì mỗi lần huỷ đều sinh `SalesCreditNote.issued_at`.
- **`FAILED` coi là chưa kết thúc: chấp nhận cho lô này.** `FAILED → DELIVERING` hợp lệ (`delivery/services.py:35`). Đường kết
  thúc thật là Quản lý huỷ đơn, khi đó phiếu thành `CANCELLED`. Còn lỗ nhỏ: phiếu `FAILED` mà không ai quyết thì NV giao thấy mãi.
  Xem câu hỏi 🟡 Q-4.
- Chọn **`null`, giữ khoá JSON** là đúng. AC2 cho phép chọn một trong hai. Cách này giữ contract khoá cho FE, và FE chỉ cần nới kiểu.
- Không thấy code chết, ngoại trừ `sees_all_customer_data` (việc S1).

### 2.3 Orders / customers / delivery notes: đạt
- `sales/orders/api.py`: annotate `pii_visible` **sau** `scope_orders_for`, chỉ khi không có full scope. Vai full scope không bị
  annotate và giữ nguyên contract. `cskh` vẫn thấy như cũ vì annotate gộp `customer_service_note_q`. Có test
  `test_sr_pii_02_courier_with_customer_service_role_unchanged_for_own_recent`, và `test_service_orders_list_ok_but_never_sees_unrelated_customer`.
- **Tìm theo SĐT/tên không dò ra đơn quá cửa sổ.** `by_customer &= Q(pii_visible=True)`, còn tìm theo mã đơn vẫn chạy. Đã kiểm:
  `filter_queryset` chạy trên queryset đã annotate. Test `test_sr_pii_02_ac2_search_by_phone_cannot_find_expired_order`
  thử cả SĐT lẫn một phần tên.
- `CourierCustomerSerializer` liệt kê tường minh `id, phone, name, created_at`, có `read_only_fields = fields`. Khách mà NV giao chỉ có
  phiếu quá cửa sổ thì không xuất hiện trong danh sách, và chi tiết trả 404, đúng AC2 và AC5.
- `DeliveryNoteSerializer`: `customer_name`, `address`, `note`, `recipient_name` bị đặt `null`. Không có `recipient_phone` trong field
  list nên không cần che. Các field còn lại (`order` chỉ có id và mã, `lines_summary`, `total_kg`, `label`) không chứa dữ liệu cá nhân.
  Phản hồi của `POST …/status/` và `PATCH` cũng đi qua `get_serializer` nên cũng bị che. Probe đã kiểm PATCH phiếu quá cửa sổ: `note: null`,
  không có tên hay địa chỉ.
- **Người kiêm nhiệm `nv_kho + nv_giao` mất danh bạ: đúng ý Q-1, và đúng BR-PQ-09 (hợp quyền).** Sau 0012, `view_customer` của
  người này chỉ còn đến từ `nv_giao`, mà phạm vi của `nv_giao` là khách của phiếu gán cho mình. Hợp quyền nên cho ra đúng tập đó.
  Nếu giữ hành vi cũ thì kiêm nhiệm sẽ là đường vòng qua Q-1. Sửa `test_s5_ac4…` vì vậy là hợp lệ. Đơn và phiếu của họ vẫn ở
  full scope, đúng Q-2.
- **User không Group nhưng có quyền gán trực tiếp được coi như NV giao: chấp nhận.** Cách này giống `scope_orders_for` đã ghi từ P8
  SR-06, nên không phải hành vi mới. Lưu ý L2 bên dưới.

### 2.4 Ma trận Group
Đã đối chiếu `MatrixTests` với quyền thật của các Group (seed bởi `0002`, `0011`, `0012`):

| Vai | orders | customers | delivery notes |
|---|---|---|---|
| `chu`, `quan_ly` | 200, đủ | 200, đủ field | 200, đủ |
| `nv_kho` | 200, đủ (Q-2) | **403** | 200, đủ |
| `nv_kho+nv_giao` | 200, đủ | 200, chỉ khách của phiếu mình, serializer NV giao | 200, đủ |
| `nv_giao` | 200, phiếu mình; quá cửa sổ thì `null` | 200, phiếu mình trong cửa sổ, serializer NV giao | 200, phiếu mình; quá cửa sổ thì `null` |
| `cskh` | 200 theo BR-GH-18, như cũ | 403 | 403 |
| chưa đăng nhập | 401 | 401 | 401 |

Test có đếm `count > 0` và quét chuỗi sentinel giả. Không phát hiện đường rò dữ liệu cá nhân mới. Không đụng giá vốn: các file sửa
không chạm `AllocationSerializer` hay `CostFieldSerializerMixin`, và bộ test chống rò giá vốn trong `apps.reports` và `apps.sales` vẫn xanh.
Phạm vi cũ (AC5) giữ nguyên: `test_sr_pii_02_ac5_scope_unchanged_other_courier_notes_404` cùng toàn bộ `test_s5_scope_nv_giao.py` xanh.

## 3. Kiểm điểm dev-notes mục 7: "dashboard cho `nv_kho` vẫn trả tên khách và 4 số cuối SĐT"

**Không đúng nữa, câu này đã lỗi thời.** P8 Lô 5 SR-17 đã đóng BM-02.
- Grep `backend/apps/reports/dashboard_api.py`: `recent_orders` chỉ còn `code, amount, status, status_label, expires_at`
  (dòng 79-87, có comment SR-17). `batches`, `alerts`, `activity`, `kpis`, `user` không có field khách nào. `activity.reference`
  chỉ chứa mã chứng từ (`cancel <mã đơn>`, mã hoá đơn, `return <id>`…, xem các chỗ gọi `record_movement`).
- `/api/dashboard/attention/` (`delivery/attention_api.py`) chỉ trả số đếm.
- Chạy thật (probe): `nv_kho` gọi cả hai endpoint, nhận 200. Khoá `summary` là `activity, alerts, as_of, batches, kpis,
  near_expiry_days, recent_orders, user`; khoá một dòng `recent_orders` là `amount, code, expires_at, status, status_label`. Body
  **không** chứa tên, SĐT, 4 số cuối SĐT, địa chỉ, ghi chú hay địa chỉ mặc định giả của khách nào.
- Các đường khác `nv_kho` gọi được và có chứa dữ liệu khách: `refunds` (`nv_kho` không có `view_refund`), `payments`
  (không có `view_paymenttransaction`), `confirmation/*` (không có `confirm_with_customer`), tem (SĐT đã che, đúng thiết kế
  BR-GH-10). Như vậy chỉ còn orders và delivery notes, đúng như Q-2 cho phép.

**Kết luận:** không còn đường dashboard nào trả tên hay SĐT cho `nv_kho`. Cần sửa mục 7 trong `03-dev-notes.md` (việc D2).

## 4. Việc cần làm

### Dọn code (không chặn PASS, be-dev làm trước khi commit)
- **S1.** `backend/apps/delivery/pii_scope.py:62-64`: hàm `sees_all_customer_data` là code chết, không có chỗ nào gọi. Xoá hàm này.
- **S2 (tuỳ chọn).** `backend/apps/sales/customers/api.py:22-27`: `sees_customer_directory` nên đặt cạnh `has_full_delivery_scope`
  trong `apps/common/api.py` để mọi luật phạm vi theo vai nằm một chỗ. Không bắt buộc.

### Tài liệu (bắt buộc trước khi bắt đầu P8b Lô 4)
- **D1. ĐÃ LÀM 01/10 (techlead sửa 02c §1d, §2, §3 Lô 4).** `doc/features/2026-09-30-dat-ten-tieng-anh/02c-giao-viec.md` §3 Lô 4 từng ghi `accounts/migrations/0012_rename_groups_to_english.py`.
  Phải đổi các điểm sau:
  - Migration đổi số thành `0013_rename_groups_to_english.py` và phụ thuộc `accounts.0012_revoke_customer_view_warehouse_staff`.
  - `ai/migrations/0003_rename_ai_keys_to_english.py` phụ thuộc `accounts.0013`.
  - `test_group_rename_migration.py` dùng `MigrationExecutor` từ `0012` tới `0013` (không còn từ `0011` tới `0012`). Tập quyền mong đợi
    của `warehouse_staff` **không** có `sales.view_customer`.
  - Dòng "Được sửa" đổi `migrations/0012_*` thành `migrations/0013_*`.
  - Lô 4 **không** được sửa 0012. Chuỗi `"nv_kho"` trong 0012 giữ nguyên vĩnh viễn, đúng quy tắc "migration đã chạy không đổi".
- **D2.** `03-dev-notes.md`, mục "Điểm cần Duy/techlead biết", ý 7: sửa thành "Đã kiểm, dashboard không còn trả tên/SĐT cho
  `nv_kho` (SR-17 đã đóng BM-02)".
- **D3 (BA).** Cập nhật spec §1.4 và §1.6: bỏ R trên Customer của `nv_kho`, thêm cửa sổ `DELIVERY_PII_RECENT_DAYS` cho `nv_giao`, thêm rule
  **BR-PQ-15** (phạm vi dữ liệu cá nhân theo Group), như đã đề xuất ở q1-pii-xac-minh mục 6.

### Ghi nhận mức Low (không sửa ở lô này)
- **L1. Thiết kế mặc định mở.** `pii_hidden` (`sales/orders/serializers.py:31-34`) mặc định là "hiện" khi không có annotate. `_customer_data_hidden`
  (`delivery/serializers.py:47-50`) mặc định "hiện" khi context thiếu `pii_restricted`. Hiện chỉ đúng một viewset dùng mỗi serializer,
  nên chưa có lỗ. Nếu sau này dùng lại các serializer này ở chỗ khác (AI provider, export) thì phải truyền annotate hoặc context. Ghi
  thành quy ước khi review các lô sau.
- **L2.** User không Group nhưng được gán thẳng `change_customer`/`add_customer` sẽ nhận `CourierCustomerSerializer` (toàn read-only).
  PATCH khi đó trả 200 mà không đổi gì. Thực tế không có tài khoản nào như vậy (superuser đã nằm trong nhóm xem danh bạ), nên bỏ qua.
- **L3.** `pii_scope` dùng ngày lịch, còn `customer_service_note_q` của CSKH dùng 7×24 giờ cuộn. Hai cách khác nhau nhưng đều đúng
  với AC của từng tính năng. Không cần thống nhất.

## 5. Câu hỏi cho Duy
- 🟡 **Q-4.** Phiếu **giao thất bại** mà Quản lý chưa quyết (không giao lại, không huỷ đơn) hiện vẫn để NV giao thấy dữ liệu khách,
  không giới hạn thời gian, vì trạng thái này còn có thể giao lại. Có cần ẩn sau N ngày không? Đề xuất: **chưa cần**. Phiếu thất bại
  đã nằm trong "Cần chú ý" để Quản lý xử lý. Khi Quản lý huỷ đơn, phiếu thành "Đã huỷ" và bị ẩn theo cửa sổ. Nếu Duy muốn ẩn thì
  cần thêm một mốc thời gian lúc thất bại (đổi schema, làm lô riêng).
- Không còn câu hỏi 🔴.

## FE

Người review: Tech Lead, 01/10/2026. Phạm vi: phần `erp-console/` chưa commit (`personalData.ts` + test, `PersonalText.tsx`,
`messages.ts`, `features/orders/{types,mock,components/*}`, `features/deliveries/{types,mock,components/*}`, 2 test mock). Không sửa code,
không build (fe-dev đang chạy Playwright/build).

### Kết luận FE: **REVIEW PASS**

Không có lỗi chặn. Có một việc dọn nhỏ (F1) và một khuyến nghị cho mock (F2), nên làm trước khi commit.

### Lệnh kiểm chứng (chạy trong lượt review)

| Lệnh | Kết quả |
|---|---|
| `cd erp-console && npx tsc --noEmit` | exit 0 |
| `cd erp-console && npm test` | `Test Files 19 passed (19)`, `Tests 230 passed (230)` |
| `python3 scripts/check_naming.py` | `OK - 6554 vi phạm cũ trong 203 file, không phát sinh mới.` |

### Soát từng điểm

- **Chỉ `null` mới là "Đã ẩn": đạt.** `personalText` so `value === null` tuyệt đối; `""` và `undefined` rơi về `whenEmpty`.
  `PersonalText` giữ đúng cách hiện cũ từng màn: `OrderDetailView` địa chỉ rỗng vẫn "chưa có địa chỉ" chữ mờ (`mutedWhenEmpty`),
  tên/SĐT rỗng vẫn "—", danh sách đơn/phiếu rỗng vẫn trống như trước (`whenEmpty=""`). `DeliveryDetailModal` "Người nhận" dùng
  `customer_name === null` làm tín hiệu ẩn, không dựa `recipient_name` (vốn `null` cả khi chỉ là chưa đổi người nhận), đúng.
  Khối "Ghi chú đơn" vẫn ẩn khi `note === ""` như cũ, chỉ hiện thêm khi `null`. Test `personalData.test.ts` phủ đủ 4 nhánh.
- **Kiểu khớp contract BE: đạt.** `OrderListItem.customer_name/customer_phone`, `OrderDetail.customer.{name,phone,address}`,
  `DeliveryNoteItem.customer_name/address/note` đổi thành `string | null`; `recipient_name` vốn đã `string | null`. Không đổi khoá
  JSON nào, đúng quy ước "giữ khoá, giá trị `null`" của BE (03-dev-notes). `tsc` sạch nên mọi chỗ dùng đã xử lý `null`.
- **Vai khác không bị ảnh hưởng: đạt.** Với giá trị chuỗi, mọi chỗ sửa cho ra cùng chữ như trước. Các màn khác đọc `customer_name`
  (`confirmation/*`, `RefundView`, `RefundQueueScreen`, `PaymentView`, `PaymentQueueScreen`, `Mark/Retry/ConfirmRefundForm`) dùng kiểu
  riêng, không đổi, và BE cũng không đổi các endpoint đó.
- **Không gọi thêm API: đạt.** Diff không thêm `apiFetch`/`fetch`; `PersonalText` thuần hiển thị.
- **Form không gửi `null` ngược lên BE: đạt.** `CancelOrderForm`, `ConfirmPaymentForm`, `OrderDetailSheet` (RefundForm `subLabel`) chỉ đổi
  phần hiển thị. `AttachOrderForm` gán `customer_name ?? undefined` vào `QueueOrderRef` là object hiển thị cục bộ cho `onDone`; body
  `resolvePayment` chỉ có `action`, `order_id`, `note`.
- **Không lưu dữ liệu cá nhân vào storage/URL/console: đạt.** Diff không có `console.*`, `localStorage`, `sessionStorage`,
  `searchParams`, `router.push/replace`. `title={personalText(address, "")}` ở `DeliveriesView` là thuộc tính DOM, giống hành vi cũ.
- **Mock không lọt bản thật: đạt.** `features/orders/api.ts` và `features/deliveries/api.ts` vẫn so literal
  `process.env.NEXT_PUBLIC_USE_MOCK === "1"`. Mock dùng tên/địa chỉ giả ("Khách Thử H/I", "Số 8 Đường Thử…").
- **a11y: đạt.** "Đã ẩn (quá 7 ngày)" là chữ thật (không chỉ màu/icon) nên trình đọc màn hình đọc được; class `.muted`
  (`--ink-3`) là pattern đã dùng cho "chưa có địa chỉ". `OrdersScreen` khi `customer_phone` null thì `last4` rỗng, không vẽ phần
  "số điện thoại đuôi", không còn `tel:` rỗng ở `OrderDetailView`.
- **Tên định danh tiếng Anh: đạt.** `personalText`, `PersonalText`, `personalDataHidden`, `piiHidden`, `viewFor`, `inCourierScope`,
  `OLD_COURIER_ORDER_INDEX`, `PII_RECENT_DAYS`. `check_naming` không phát sinh mới.
- **Mock bám BE: đạt về cửa sổ.** Ngày lịch giờ VN, `completed_at` thiếu thì `created_at`, chỉ `COMPLETED`/`CANCELLED`, `FAILED` luôn thấy,
  tìm theo SĐT/tên không khớp đơn đã ẩn, NV giao chỉ thấy phiếu gán cho mình (404 ngoài phạm vi). Đơn 143 thế chỗ đơn cũ thứ 42 nên
  tổng 45 đơn và các id khác không đổi.

### Ghi nhận ngữ cảnh

Người **chỉ** thuộc `nv_giao` không vào được màn Đơn (`/orders/`) hay Giao hàng (`/deliveries/`) trong ERP (`shared/lib/nav.ts`
`!onlyDelivery(me)`; màn "Việc giao của tôi" vẫn là `Placeholder`). Trên production, người thật sự thấy chữ "Đã ẩn" ở hai màn này là
người **kiêm `nv_giao` mà không thuộc `owner`/`manager`/`warehouse_staff`**, ví dụ `customer_service + delivery_staff` (BE
`has_full_delivery_scope` sai). Phần FE lô này vì vậy chủ yếu là phòng thủ đúng contract, và cũng chuẩn bị cho màn "Việc giao của tôi" (S20).

### Việc cần làm

- **F1 (dọn, trước khi commit).** `erp-console/shared/lib/messages.ts:29-31`: khoá `personalDataHidden` chen vào giữa comment
  `/** S7-AC3: mở màn không có quyền. */` và `noViewPermission`, nên comment S7-AC3 giờ treo trên khoá sai. Chuyển khối
  `personalDataHidden` (cả JSDoc) xuống sau `noViewPermissionHint`, hoặc lên trước dòng comment S7-AC3.
- **F2 (khuyến nghị, nên làm cùng lô).** Hai mock dùng `onlyDelivery(me)` để quyết ẩn (`features/orders/mock.ts` `piiHidden`,
  `features/deliveries/mock.ts` `viewFor`/`inCourierScope`), còn BE dùng `not has_full_delivery_scope` (không thuộc
  `owner`/`manager`/`warehouse_staff`). Hệ quả: (a) người chỉ `nv_giao` là người duy nhất mock ẩn, mà họ lại không vào được hai màn,
  nên ở chế độ mock **không màn nào hiện được "Đã ẩn"**, Playwright không bắt được qua giao diện; (b) người kiêm `nv_giao + customer_service`
  trong mock thấy đủ, còn BE thật trả `null`. Sửa: đổi điều kiện thành "có `ROLE.deliveryStaff` và không có
  `ROLE.owner`/`ROLE.manager`/`ROLE.warehouseStaff`" (cùng một hàm, đặt ở chỗ dùng chung nếu cả hai mock cần), và nếu muốn E2E thì thêm
  một user mock kiêm `customer_service + delivery_staff` có phiếu cũ. Không chặn PASS vì contract và phần hiển thị đã đúng.
- **L-FE1 (Low, không sửa lô này).** Chữ "Đã ẩn (quá 7 ngày)" ghi cứng 7, trong khi BE đọc `DELIVERY_PII_RECENT_DAYS` từ env. Nếu Duy đổi
  env thì chữ sai. Khi đổi env phải sửa `MSG.personalDataHidden` và hằng `PII_RECENT_DAYS` trong hai mock; hoặc lô sau BE trả số ngày qua
  `/api/auth/me/` để FE ghép chữ.
- **L-FE2 (Low).** `mockPostDeliveryNoteStatus` và `mockGetDeliveryLabel` không qua `viewFor`; BE thật có che response `POST …/status/`,
  còn tem chỉ người có `delivery.print_label` (không có `nv_giao`) gọi được. Không ảnh hưởng vì NV giao không có nút trên phiếu đã kết thúc.
