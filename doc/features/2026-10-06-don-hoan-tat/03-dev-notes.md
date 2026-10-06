# Đơn hoàn tất (W37) — Ghi chú dev

## L1 BE (S2 rồi S1) — nhánh `feat/w37-l1-be`

### File đã sửa
- Mới `backend/apps/sales/orders/completion.py`: `is_delivery_finished`, `lock_order_of_note`, `complete_order_if_delivered`, `current_order_status`.
- `backend/apps/delivery/services.py`: `advance_status` và `mark_failed` toàn thân trong một `atomic`, khoá `SalesOrder` rồi `DeliveryNote`, đọc lại sau khoá; BR-GH-24; hằng `ORDER_CANCELLED_MESSAGE`, `ORDER_CANCELLED_CODE` (để hồ sơ huỷ-đơn-đang-giao dùng lại).
- `backend/apps/delivery/api.py`: `set_status` thêm khoá `order_status`.
- `backend/apps/sales/orders/services.py`: `cancel_paid_order` có nhánh đơn `COMPLETED` trả 400 `BR-GH-05`.
- README của `delivery` và `sales/orders` (một dòng).
- Test mới: `sales/orders/tests/test_completion_rule.py`, `delivery/tests/test_order_completion.py`, `delivery/tests/test_completion_race_postgres.py`, helper `reports/tests/financial_snapshot.py`.
- Không migration, không model, không quyền mới.

### Contract thực tế
`POST /api/delivery/notes/{id}/status/` có thêm `order_status` ở mọi nhánh (READY, DELIVERING, COMPLETED, FAILED, lặp `already`):
```json
{"status": "COMPLETED", "already": false, "order_status": "COMPLETED"}
```
Lỗi mới: `400 {"detail": "Đơn đã huỷ — mang hàng về kho.", "code": "BR-GH-24", "current_status": "CANCELLED"}` (cả giao xong, bắt đầu giao, báo thất bại).
`POST /api/sales/orders/{id}/cancel/` trên đơn `COMPLETED`: `400 {"code": "BR-GH-05", "detail": "Đơn đã giao hoàn tất — chỉ còn cách lập phiếu hoàn."}`.
AuditLog đơn: `action=complete_order`, actor rỗng (`actor_kind=system`), `changes={"status":{"from":"PROCESSING","to":"COMPLETED"},"delivery_note":"<mã>","delivery_note_id":<id>}`, không dữ liệu khách.

### BR đã cài
BR-BH-18 (giao xong phiếu cuối thì đơn Hoàn tất; phiếu huỷ không tính), BR-BH-21 (chỉ PROCESSING chuyển), BR-GH-24 (400), BR-GH-05 (huỷ đơn đã Hoàn tất).

### Chứng minh đua Huỷ ∥ Giao xong (T1 b)
Máy dev chỉ có SQLite, nên bằng 5 test tất định (`CancelRaceDeterministicTests`, đối tượng cũ trong bộ nhớ đóng vai bên đến sau) + 3 test thứ tự khoá (`LockOrderTests`, spy `select_for_update`: đơn trước phiếu cho `advance_status`, `mark_failed`, `cancel_paid_order`). Cả 5 ca tất định đỏ trên main (xem dưới) và xanh sau khi sửa. `test_completion_race_postgres.py` (hai luồng, barrier, 20 lần mỗi thứ tự) viết sẵn, `skipUnless(connection.vendor == "postgresql")`, **chưa chạy được ở đây**, ghi nợ, hỏi Duy việc cài Postgres cục bộ.

### Output đỏ trên main trước khi sửa (28 test, 12 failures + 9 errors)
```
FAIL case1 cancel wins, redelivery:        AssertionError: BusinessError not raised
FAIL case2 cancel wins, complete:          AssertionError: BusinessError not raised
FAIL case3 cancel wins, failure report:    'BUSINESS_ERROR' != 'BR-GH-24'
FAIL case4 complete wins, cancel stale:    'PROCESSING' != COMPLETED (đơn không được hoàn tất)
FAIL case5 order cancelled, old note:      AssertionError: BusinessError not raised
FAIL lock order advance_status / mark_failed: SalesOrder not found in [] / [DeliveryNote]
```
Kết quả sau khi sửa: 34 test của L1 xanh.

### Kết quả kiểm
`manage.py test` (DJANGO_DEBUG=1): Ran 3058 tests, OK (skipped=2: hai test Postgres). `makemigrations --check --dry-run`: No changes detected. `check_naming.py`: file L1 sạch; còn 2 file FE có sẵn trên main (`ContactButton.tsx`, `SiteLegalFooter.tsx`, từ `nguoi`) làm script exit 1, không thuộc L1.

### Lệch / giả định so với 02b và story
- S1-AC13: NV kho của repo này **có** `change_deliverynote` (đóng gói). Test dùng người chỉ có `view_deliverynote` để ra 403.
- `test_s1_ac3` dựng hai kỳ và một chứng từ đảo, so `financial_snapshot` trước/sau giao xong (period_pnl 2 kỳ qua service và API, batch_pnl, doanh thu hôm nay, đếm + max id năm bảng chứng từ).
- Hàm `current_order_status` lấy qua `SalesOrder.objects.filter(invoice__pk=...)`, không dùng cache của phiếu.
- Sửa `test_s14_ac5_da_hoan_tat_bi_chan`: trước đây khẳng định đơn kẹt `PROCESSING` sau khi giao xong, nay là `COMPLETED` (đúng S1).
- Nhánh lặp (`already`) vẫn không đụng đơn, đúng 02b §1.2.

### Còn nợ
- Chạy `test_completion_race_postgres.py` trên Postgres thật (T1).
- FE ERP (`order_status`, BR-GH-24), S3 lệnh chuyển bù và các lô sau không thuộc L1 BE.


## L1 FE (ERP, chạy mock theo contract 02b)

Nhánh `feat/w37-l1-fe`. Chỉ sửa `erp-console/`. Không đụng `OrderDetailScreen.tsx`, `CancelOrderModal.tsx`, `frontend/**`.

**Đã làm**
- S1/S2, phía NV giao:
  - `DeliveryStatusResponse.order_status?` (`features/deliveries/api.ts`).
  - Giao xong mà `order_status === "COMPLETED"` thì toast "Đã giao xong. Đơn đã hoàn tất." (`completeToast` ở `deliveryUi.ts`, dùng ở `MyDeliveriesScreen` và `DeliveryDetailScreen`).
  - Lỗi 400 `BR-GH-24` nhận theo `code` (`isOrderCancelledError`), không thêm vào `CONFLICT_CODES`.
    - `ConfirmCompleteModal` và `ReportFailureModal` hiện đúng `detail` của BE ("Đơn đã huỷ — mang hàng về kho.") và đổi nút chính thành "Tải lại".
    - Nút "Nhận hàng đi giao" ở hai màn chỉ hiện câu đó và tải lại.
    - `ReportFailureModal` có prop mới bắt buộc `onReload`.
- S6:
  - `labels.ts` bỏ lựa chọn "Đã thanh toán". "Chưa xong" giữ `BOOKED,PAID,PROCESSING`.
  - `enums.ts` giữ chip `PAID` để đọc dữ liệu cũ.
- S7 (mô hình):
  - `orderDetailModel.ts`: `ORDER_STEPS` 5 bước, bước 2 là `CONFIRMING` "Chờ gọi xác nhận". `orderStepKey` chỉ trả `COMPLETED` khi đơn `COMPLETED`.
  - `orderDetailModel.test.ts` có bảng mọi tổ hợp `order.status × delivery.status`.
- Luật dùng chung: `shared/lib/orderCompletion.ts` (`isDeliveryFinished`, BR-BH-18) kèm test.
- Mock:
  - `deliveries/mock.ts`: mọi phản hồi của `status/` có `order_status` tính bằng luật dùng chung trên mọi phiếu cùng đơn. Phiếu `CANCELLED` mà giao, nhận đi giao hay báo thất bại thì trả 400 `BR-GH-24` kèm `current_status`.
  - `orders/mock.ts`: đơn `COMPLETED` sinh theo luật dùng chung (không gán cứng), có `refund_summary`, mốc "Đã giao — đơn hoàn tất (…)" thay "Giao hàng thành công" khi đơn `COMPLETED`.
  - `orders/types.ts`: `OrderDetail.refund_summary`, `TimelineKind` thêm `order_completed`.
- e2e: `e2e/order_completion_erp.py` (mới). `ed_batch3_orders.py` đổi kỳ vọng thanh bước theo S7.

**Chỗ lệch / nợ**
1. Kho phiếu mock (Giao hàng) và kho đơn mock (Đơn) **không nối nhau**: seed dùng mã đơn khác nhau, nên giao xong ở Việc giao của tôi không đổi đơn bên trang Đơn trong mock. Thử nối bằng import chéo hoặc truyền hàm qua `api.ts` thì `check-no-mock` đỏ (bundler giữ seed mock), nên bỏ.
2. Bài học cho mock: một hàm trong file mock **không export**, được gọi bởi hàm mock export và đọc `MOCK_DELIVERY_NOTES`, làm bản build thật giữ lại seed. Tách hàm phụ ra ngoài thì sai. Phải đặt closure ngay trong hàm export (`siblingStatuses` ở `mockPostDeliveryNoteStatus`).
3. Bộ đơn mock chưa dựng riêng theo S6-AC1 (1/2/3/1). Seed 45 đơn hiện có đã đủ mọi trạng thái, trong đó đơn `COMPLETED` sinh theo luật. Cần kịch bản riêng thì làm ở L3.
4. Đường BR-GH-24 trong hộp xác nhận chưa có e2e trình duyệt: UI không cho bấm giao xong ở phiếu đã huỷ. Hành vi do vitest phủ (mock 400 và nhận diện theo `code`).
5. Thanh bước của chi tiết đơn đã đổi ở mô hình, nhưng `OrderDetailScreen.tsx` chưa sửa. Màn đọc `orderPath` nên nhãn mới hiện ngay, không cần sửa.

**Kiểm chạy thật (07/10)**
- `tsc --noEmit` sạch. `vitest run` 90 file, 1031 test xanh.
- Build `NEXT_PUBLIC_USE_MOCK=0`: `check-no-mock` XANH, `check-ai-chunks` XANH.
- Build `NEXT_PUBLIC_USE_MOCK=1`: `ed_batch3_orders` 143/143, `ed_batch4_delivery` 70/70, `order_completion_erp` 6/6.
- `python3 scripts/check_naming.py`: không báo gì ở `erp-console/` (exit 1 ở main do `frontend/features/site/components/SiteLegalFooter.tsx:60`, có sẵn từ trước, không do lô này).
- Ảnh: `shots/order_completion_toast_360.png`, `order_completion_filter_1280.png`, `order_completion_steps_1280.png`.

## L4 BE (S3 lệnh chuyển bù) — nhánh `feat/w37-l2-l4-be`

### File
- Mới: `backend/apps/sales/management/commands/backfill_completed_orders.py`.
- Sửa: `backend/apps/sales/orders/completion.py` (thêm `backfill_candidates()`, đúng 02b §1.4).
- Mới: `backend/apps/sales/orders/tests/test_backfill_completed_orders.py` (13 test: S3-AC1..AC8, R1, R4, thêm ca phiếu huỷ và phiếu mới nhất).
- Không có route HTTP, không có lệnh AI, không migration.

### Cách chạy (mặc định CHẠY THẬT, khác `backfill_credit_notes`)
```
python manage.py backfill_completed_orders --dry-run   # bước 1: chỉ in "Sẽ chuyển N đơn:" + mã đơn
python manage.py backfill_completed_orders             # bước 2: chạy thật, in "Đã chuyển N đơn." + mã đơn
python manage.py backfill_completed_orders             # bước 3: chạy lại, phải ra "Đã chuyển 0 đơn."
```
Sau bước 3, QA so số báo cáo (kỳ và lô) với số trước khi chạy: phải trùng từng đồng. Production chỉ chạy khi Duy duyệt; không chép
mã đơn production vào doc.

### Hành vi
- Ứng viên: đơn `PROCESSING` có ít nhất một phiếu `COMPLETED`. Mỗi đơn một `transaction.atomic()`: khoá đơn, đọc lại, gọi
  `complete_order_if_delivered(backfill=True)` (cùng luật với đường giao xong, S1). `trigger_note` là phiếu `COMPLETED` có
  `completed_at` mới nhất.
- Đơn `PAID`, đơn có phiếu `FAILED`/đang giao, đơn `CANCELLED` không đổi. Phiếu `CANCELLED` bỏ qua khi xét.
- AuditLog `complete_order`, actor Hệ thống, `changes` = `status`, `delivery_note`, `delivery_note_id`, `backfill: "W37"`.
- Lỗi một đơn: đơn đó rollback, lệnh in "Đã chuyển K đơn trước khi lỗi.", `CommandError` kèm mã đơn (exit khác 0). Đơn trước đã commit,
  chạy lại làm nốt. Thông báo lỗi chỉ có mã đơn và tên lớp lỗi, không dữ liệu khách.
- Output chỉ có mã đơn (test R4 xác nhận không có tên, SĐT, địa chỉ).
- R1: test dựng hoá đơn tháng trước, chứng từ đảo, so `financial_snapshot` trước/sau: bằng nhau.

### Nợ
- `--dry-run` tính lại luật bằng `is_delivery_finished` ngoài khoá, nên giữa dry-run và chạy thật số có thể lệch nếu có thao tác mới. Chấp nhận.

## L2 BE (S4, S5, `refund_summary`) — nhánh `feat/w37-l2-l4-be`

### File
- Sửa: `backend/apps/sales/orders/serializers.py` (`refund_summary` trong `SalesOrderDetailSerializer` + `Meta.fields`). Không sửa
  `api.py`, `scope.py`, `models/`, `batches/services.py`, `next_steps.py`.
- Mới (test): `sales/orders/tests/test_order_detail_completed.py` (10), `sales/refunds/tests/test_refund_completed_order.py` (7,
  S5-AC1..AC7), `inventory/batches/tests/test_close_after_completion.py` (6, S4-AC1..AC5, AC3 gọi lệnh L4).

### Contract `GET /api/sales/orders/{id}/` (chỉ thêm một khoá)
```json
"refund_summary": {"refunded_amount": "200000", "pending_amount": "100000"}
```
Tổng phiếu `REFUNDED` và `PENDING` (chuỗi Decimal, `money_str`), `FAILED` không tính. Không có hoá đơn hoặc không có phiếu: cả hai
`"0"`. Tính từ `invoice.refunds.all()` đã prefetch: thêm phiếu không thêm query (test so 1 phiếu với 3 phiếu). Không có ô dữ liệu khách,
có ở mọi vai xem được đơn (kể cả NV giao ngoài phạm vi, họ vẫn thấy `customer` bị che theo Lô 3).

### Kết quả TDD
- Đỏ thật ở `refund_summary` (KeyError, 5 error). S4 và S5 xanh ngay vì hành vi có từ L1 (02b §1.5, §2.5: "chỉ cần test"); chứng minh
  S5-AC2 không phải xanh giả bằng so kỳ hiện tại phải ĐỔI số, kỳ cũ không đổi.
- S7-AC8 và S5-AC8: đơn `COMPLETED` có `create_refund`, không có `cancel`; hết số còn hoàn thì mất `create_refund`.
- S7-AC10: duyệt đệ quy JSON, không có `unit_cost`, `landed_unit_cost`, `purchase_rate`, `profit`, `pnl`, `cost`.

## L3 FE (S7 chi tiết đơn, S8 Shop) — nhánh `feat/w37-l3-fe`

### Đã làm
- `erp-console/features/orders/components/OrderDetailScreen.tsx`: thanh bước đã đọc `orderPath` từ L1, không phải sửa. Thêm dòng
  `refundSummaryLine(o.refund_summary)` ("Đã hoàn 200.000 đ · Chờ hoàn 100.000 đ", `data-testid="order-refund-summary"`) trong khối
  banner dưới chip; phần bằng 0 bỏ, cả hai bằng 0 hoặc BE cũ chưa trả khoá thì không có dòng. Hàm thuần nằm ở `orderDetailModel.ts`,
  tiền format bằng `vnd()` của `shared/lib/format.ts`.
- Nút chính của đơn `COMPLETED` đổi thành "Lập phiếu hoàn tiền" (S7-AC4). Nút của đơn đã huỷ và mục "…" giữ "Lập phiếu hoàn" cho tới lô áp tên chuẩn.
- `features/audit/auditModel.ts`: `complete_order: "Đơn hoàn tất"`.
- **Nợ L1 (S6-AC8):** `shared/lib/orderLink.mock.ts` là kho nối chỉ có ở mock (hộp thư trong sessionStorage, có bản dự phòng trong
  bộ nhớ). Mock Giao hàng gửi kết quả mỗi lần phiếu đổi (`publishDeliveryOutcome`), mock Đơn đọc ở lần `load()` kế tiếp và áp vào đơn cùng
  `id` (`applyDeliveryOutcomes`). Mock Đơn báo đơn đã huỷ (`publishOrderCancelled`) để mock Giao hàng chặn BR-GH-24 cả khi phiếu cũ chưa huỷ
  (**sửa Low #3**). Tổng quan mock (`features/overview/mock.ts`) lấy `pending_orders` và `recent_orders` từ `mockOrdersOverviewSlice()`, chỉ khi kho đơn
  dùng bộ mẫu hoặc đã nhận kết quả giao hàng (các e2e cũ bám seed riêng của Tổng quan).
- **Seed không còn gán cứng (sửa Low #2):** kịch bản đơn khai `"DELIVERY"` + ghi chú (`preparing`/`delivering`/`failed`/mặc định đã giao); trạng thái đơn suy từ
  phiếu bằng `isDeliveryFinished`.
- **Bộ đơn mẫu S6-AC1:** `localStorage cave_erp_mock_orders_dataset = "completion"` (rồi xoá khoá `cave_erp_mock_orders` trong sessionStorage) cho 7 đơn:
  1 giữ chỗ, 2 đang xử lý (phiếu Đang giao, Giao thất bại), 3 Hoàn tất, 1 huỷ. Đơn id 104 có hai phiếu hoàn REFUNDED 200.000 + PENDING 100.000 (S7-AC5).
- **Shop:** `frontend/lib/mock.ts` thêm bảng `PAID_ORDER_LABELS` theo 02b §2.6; DH-DEMO008 (COMPLETED) hiện badge "Hoàn tất", dòng phiếu "Đã giao"; đơn demo 005–009 dùng
  đúng bảng ("Đang xử lý" thay "Đã thanh toán, đang soạn hàng"). `types.ts` và `OrderLookup.tsx` không cần sửa. Đơn demo 001 và luồng SePay giữ nhãn cũ (e2e `qa_sepay_checkout` bám).

### Kiểm (mock, chạy trong lượt này)
- erp-console: `tsc` sạch; vitest 95 file, 1070 test xanh (thêm `orders_completion_link.test.ts`, ca `refundSummaryLine`, nút COMPLETED).
- Build `NEXT_PUBLIC_USE_MOCK=0`: `check-no-mock` XANH (27 file mock, 255 file build), `check-ai-chunks` XANH.
- Build mock=1 + e2e: `order_completion_detail.py` 16/16, `order_completion_erp.py` 6/6, `ed_batch3_orders.py` 143/143 (đổi kỳ vọng đơn 109 thành "Lập phiếu hoàn tiền").
- frontend: `tsc` sạch, build mock=1 xanh, `order_lookup_completed.py` 4/4, `order_lookup_no_raw_codes.py` 19/19. Chưa build mock=0 cho Shop (không đổi code ngoài `lib/mock.ts`).
- `check_naming.py`: không phát sinh mới.
- Ảnh: `shots/order_completed_detail_360.png`, `order_completed_detail_1280.png`, `shop_order_completed_390.png`.

### Chỗ lệch contract / nợ
- Chưa chạy trên BE thật: e2e "trên BE thật" của 02b L3 cần ghép với L3 BE, việc của điều phối viên/QA.
- Seed phiếu giao và seed đơn của hai mock vẫn khác nhau ở các id trùng (vd đơn 109 hoàn tất bên Đơn, phiếu 39 Đang giao bên Giao hàng); kho nối chỉ đồng bộ từ lúc có thao tác. Hướng nối chiều ngược (Đơn → Giao hàng cho thao tác khác ngoài huỷ) để sau.
- Tổng quan mock chỉ khớp S6-AC5/AC6 khi bật bộ mẫu hoặc sau khi có thao tác giao hàng (xem trên).

## L3 BE (S7 dòng thời gian, S8 Shop) — nhánh `feat/w37-l3-be`

### File
- Sửa `backend/apps/sales/orders/timeline.py` (giữ nguyên bộ lọc dòng AI của lô dọn chữ AI).
- Mới `backend/apps/sales/orders/tests/test_timeline_completed.py` (S7-AC6, AC7, AC9), `test_shop_lookup_completed.py` (S8-AC1..AC5, AC7).
- `shop_api.py`, `shop_labels.py` **không sửa**: bảng nhãn đã đủ 7 dòng (COMPLETED = "Hoàn tất" / "Đã giao", CANCELLED = "Đã huỷ").
- Không model, không migration.

### Hành vi (BR-BH-18, UC-5)
- Dòng AuditLog `complete_order` không có `backfill` cho ra tập `merged_note_ids` (từ `delivery_note_id`). Phiếu thuộc tập này:
  mốc `delivered` đổi nhãn thành `"Đã giao — đơn hoàn tất ({mã phiếu})"`; kind giữ `delivered`. Dòng `complete_order` đó không thành mốc riêng.
- Dòng `complete_order` có `backfill == "W37"`: mốc `order_completed`, nhãn "Hệ thống chuyển đơn sang Hoàn tất (chuyển bù)", người làm "Hệ thống".
  Mốc giao cũ của đơn chuyển bù giữ nhãn "Giao hàng thành công ({mã phiếu})".
- API chi tiết đơn không đổi khoá (`timeline[]` vẫn `at, kind, label, actor_display, doc?`). Nhãn chỉ có mã phiếu; test khoá không có SĐT, tên, địa chỉ, `changes` thô.
- Shop: test khoá bảng 7 dòng, tập khoá phản hồi không đổi, 404 khi sai 4 số (không lộ trạng thái), 429 theo IP và theo mã đơn.

### Kết quả
`manage.py test`: 3228 test, OK (skipped=2). `makemigrations --check`: không đổi. `check_naming.py`: exit 0.

### Nợ
Không. Ghi chú T2 (nhãn phiếu huỷ Shop "Đã huỷ" theo T30, story S8 ghi "Đã huỷ theo đơn") vẫn chờ PO sửa dòng bảng story.

### Sửa sau review L3 FE (08/10, M1: mock lọt vào bản build thật)
- **Câu sai ở mục L3 FE phía trên** ("kho nối chỉ có ở mock nên bản build thật không giữ seed") **không đúng** ở bản `eef6e1b`: build mock=0 chứa
  `cave_erp_mock_order_link` và tên giả "Anh Phúc/Lâm/Khoa". Nguyên nhân gốc có từ trước L3: `features/deliveries/api.ts` import tĩnh `./mock`, mà
  module đó có khai báo cấp module (seed gọi `Date.now()`, bảng tên giả), nên bundler giữ lại phần khai báo cấp module kể cả khi hàm mock đã bị bỏ.
  Bản tương ứng của comment ở `deliveries/mock.ts` đã sửa.
- **Gate:** `scripts/check-no-mock.mjs` quét thêm `*.mock.ts` và thêm bốn loại chuỗi seed: khoá `cave_erp_mock_*`, tên người giả (Anh/Chị/Cô/Bác…),
  SĐT giả 10 số, mã mẫu viết hoa-gạch nối có số (trừ mã luật `BR-`). Chạy trên `eef6e1b` + gate mới: **ĐỎ** ("Anh Khoa", `cave_erp_mock_order_link`).
- **Sửa:** (1) `deliveries/mock.ts`: seed dựng lười trong `buildSeed()`, truy cập qua `mockDeliveryNotes()` (4 test đổi theo). (2) Chỉ làm (1) thì chưa đủ (gate vẫn đỏ), vì
  import tĩnh vẫn giữ khai báo cấp module. `deliveries/api.ts` nay nạp mock bằng `require("./mock")` đặt sau điều kiện `NEXT_PUBLIC_USE_MOCK === "1"`
  (`mockApi()`), nên bản build thật bỏ nhánh và không còn module mock.
- **Kết quả build `NEXT_PUBLIC_USE_MOCK=0`:**
  - `check-no-mock`: XANH (30 file mock, 232 chuỗi seed, 254 file build).
  - `grep -rl "cave_erp_mock\|Anh Ph\|Anh Lâm\|Anh Kh" erp-console/out`: rỗng.
  - Chuỗi seed orders mock `grep -rl "Chị Hoa\|TOM-SU-1\|0901234567\|Khách lẻ\|Bác Tư\|Anh Minh\|FT26267\|cave_erp_mock_orders" out`: rỗng (Low 2).
  - `check-ai-chunks`: XANH.
- Kiểm lại: tsc sạch, vitest 95 file / 1070 test xanh; build mock=1 + e2e: `order_completion_detail` 16/16, `order_completion_erp` 6/6, `ed_batch3_orders` 143/143,
  `ed_batch4_delivery` 70/70.
- Còn lại: `beErrors.mock.ts` (mã luật `BR-…` và câu lỗi BE, không phải dữ liệu giả) vẫn có thể nằm trong bản build; gate cố ý bỏ qua mã `BR-`. Thụt lề trong `buildSeed()` chưa chỉnh để diff nhỏ.
