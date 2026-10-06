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
