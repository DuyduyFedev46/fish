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
