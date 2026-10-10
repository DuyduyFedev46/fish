# Đơn hoàn tất (W37) — Review của Tech Lead

## Review L1 BE (07/10)

**Phạm vi:** commit `3e59e50` trên nhánh `feat/w37-l1-be`, diff `2dcf666..HEAD`, 12 file. Đối chiếu với `02b-tech-design.md` §1.2–§1.4,
§2.1–§2.3, §4 và §6 (L1).

**Kết luận: APPROVED.** Không có lỗi Critical, High hay Medium. Có 5 điểm Low, sửa ở lô sau hoặc khi tiện, không chặn QA.

### Lệnh Tech Lead tự chạy trong worktree
- `manage.py test apps.delivery apps.sales.orders apps.reports` (DJANGO_DEBUG=1): chạy 679 test, 2 test skip (Postgres), 1 lỗi.
  Lỗi đó là `Missing staticfiles manifest entry for 'admin/css/base.css'`, do worktree không có thư mục `backend/staticfiles/`.
  Chạy cùng test trên checkout chính thì OK. Đây là môi trường, không phải code.
- `manage.py test` toàn bộ: chạy 3058 test, `errors=33`, `skipped=2`. Cả 33 lỗi đều là test trang admin, cùng một thông báo
  thiếu manifest staticfiles. Đếm bằng `grep -c "Missing staticfiles manifest"` ra 33, khớp đúng số lỗi. Không có FAIL nào.
- `makemigrations --check --dry-run`: No changes detected.
- `python3 scripts/check_naming.py`: exit 1. Nguyên nhân là 2 file FE đã có sẵn trên main (`ContactButton.tsx`,
  `SiteLegalFooter.tsx`, token `nguoi`). Các file L1 không có vi phạm.

QA nên chạy toàn bộ test trên checkout có `staticfiles`, hoặc chạy `collectstatic` vào thư mục tạm. Không commit thư mục đó.

### Soát theo 02b

| Mục | Kết quả | Chứng cứ |
|---|---|---|
| Thứ tự khoá đơn rồi phiếu, đọc lại sau khoá | Đạt | `delivery/services.py` `_lock_order_then_note` gọi `completion.lock_order_of_note`, rồi mới gọi `_lock_note`. `lock_order_of_note` lấy `sales_order_id` bằng `values_list` (không khoá), rồi `select_for_update().get(pk=…)`, không có join. Áp cho cả `advance_status` và `mark_failed`. `cancel_paid_order` vẫn khoá đơn rồi mới khoá phiếu. `LockOrderTests` kiểm cả ba đường bằng spy `QuerySet.select_for_update` |
| Toàn thân hàm trong `atomic` | Đạt | Việc xét luật, `save`, `record_audit` của phiếu và `complete_order_if_delivered` đều nằm trong một `transaction.atomic()`. `test_s1_ac9` patch AuditLog của đơn cho raise, rồi kiểm phiếu vẫn `DELIVERING`, `completed_at` rỗng, đơn `PROCESSING`, số AuditLog không đổi (dòng của phiếu cũng bị rollback) |
| BR-GH-24 trả 400 | Đạt | `_raise_if_cancelled` xét cả phiếu `CANCELLED` lẫn đơn `CANCELLED`/`AUTO_CANCELLED`, chạy trước BR-GH-07 với đích `DELIVERING`/`COMPLETED` và chạy trong `mark_failed`. Đích `READY` vẫn trả `BR-GH-07`, đúng §1.2 bước 4. API trả `detail`, `code`, `current_status` đúng contract §2.1 (`test_s2_ac2_api_…`) |
| Nhánh `already` | Đạt | Nằm sau bước xét huỷ. Nhánh này trả về sớm, không ghi gì và không đụng đơn. `test_s1_ac4` kiểm số AuditLog của phiếu và của đơn không tăng, và `order_status` vẫn trả `COMPLETED`. `order_status` có mặt ở mọi nhánh (`test_order_status_present_on_every_branch`) và được đọc mới từ DB |
| Huỷ đơn đã Hoàn tất | Đạt | `cancel_paid_order` có nhánh `COMPLETED` → `BR-GH-05`, đặt ngay sau khi khoá, dùng đúng câu thông báo §2.2. Ca tất định 4 kiểm không sinh chứng từ đảo và không có `CANCEL_RESTORE` |
| AuditLog Hệ thống không chứa dữ liệu cá nhân | Đạt | `changes` có tập khoá cố định `status`, `delivery_note`, `delivery_note_id`, `note=""`, `actor=None`, `actor_kind=system`. `test_s1_ac2` so nguyên dict và kiểm không có SĐT, tên hay địa chỉ giả. Dòng của phiếu vẫn ghi người bấm |
| `financial_snapshot` | Đạt | Gồm `period_pnl` của mọi tháng theo giờ VN (cả qua service lẫn API `?year&month`, API này nhận đúng tham số), `batch_pnl` mọi lô cộng API danh sách lô, doanh thu hôm nay, và số dòng + `max(id)` của 5 bảng chứng từ. `pending_orders` cố ý bỏ ngoài. `test_s1_ac3` dựng hai kỳ (hoá đơn lùi 40 ngày) và một chứng từ đảo |
| Test Postgres skip theo T1 (b) | Đạt | `@skipUnless(connection.vendor == "postgresql")`. Docstring cấm trỏ vào staging hoặc production. Mỗi thứ tự khoá chạy 20 lần, có barrier và timeout 5 giây. Test chưa từng chạy, xem điểm L3 |
| Marker `naming: allow` | **Duyệt** | Hai dòng gán bí danh `self.courier, self.manager(, self.owner) = self.giao, self.ql(, self.chu)` để code mới dùng tên tiếng Anh, còn thuộc tính cũ là của `OrderApiBase` dùng chung. Marker có lý do. Đã có tiền lệ y hệt ở `test_timeline_no_free_text.py:30-31` và `test_auditlog_note_no_free_text.py:56`. Đổi tên `OrderApiBase` nằm ngoài phạm vi |
| Sửa test cũ S14-AC5 | **Duyệt** | `test_s14_ac5_da_hoan_tat_bi_chan` trước đây khẳng định đơn giữ `PROCESSING` sau khi giao xong. Đó chính là lỗi W37. Nay test khẳng định `COMPLETED` đúng theo S1, vẫn giữ các assert `BR-GH-05` và "không có `cancel` trong `available_actions`". Ý định của test (huỷ bị chặn sau khi giao xong) không bị nới |
| Không rò giá vốn | Đạt | Không đụng serializer, `AllocationSerializer` hay `CostFieldSerializerMixin`. Phản hồi chỉ thêm `order_status` (mã trạng thái). Dòng AuditLog không có số tiền hay giá |
| Phân quyền | Đạt | Không thêm route hay quyền. Có test cho S1-AC11 (404), AC12 (PATCH/PUT bị chặn), AC13 (403), S2-AC6 (403) và 401 |
| Lệch so với 02b | Chấp nhận | S1-AC13 dùng người chỉ có `view_deliverynote`, vì NV kho thật có `change_deliverynote` (đóng gói). Các mục còn lại khớp 02b |

### Điểm Low (không chặn)
- **L1** `sales/orders/completion.py`, `lock_order_of_note`: kiểu trả về khai `-> SalesOrder`, nhưng hàm có thể trả `None`. Sửa
  thành `SalesOrder | None`.
- **L2** `completion.py`, `complete_order_if_delivered`: hàm truy vấn lại `invoice_id` từ `order.pk`. Có thể dùng thẳng
  `trigger_note.sales_invoice_id` và bớt một query. Nếu sửa thì lệnh S3 (L4) phải truyền đúng phiếu của đơn đó.
- **L3** `delivery/tests/test_completion_race_postgres.py`: test chưa từng chạy, nên chưa biết chính test có đúng không. Đáng ngờ
  nhất là chỗ gọi `OrderApiBase.setUp(self)` trên một `TransactionTestCase` cùng `serialized_rollback`. Ghi nợ theo T1. Lần
  đầu có Postgres thì phải chạy file này trước khi tin kết quả.
- **L4** `test_order_completion.py`, `test_order_status_present_on_every_branch`: biến `order`, `order2`, `note2` không dùng.
  Cách lấy kết quả qua `self._pack_response` lòng vòng, nên trả thẳng response từ helper.
- **L5** `test_order_completion.py`, `test_s1_ac3_…`: `import datetime` và `timezone` nằm trong thân hàm. Nên đưa lên đầu file.

### Việc cho lô sau
- **PV Lô 4** (`delivery/scope.py`) phải giữ hai điều. Một, NV giao vẫn thấy phiếu `CANCELLED` được gán cho mình, nếu không
  `test_s2_ac2_api_returns_400_br_gh_24_for_cancelled_order` sẽ trả 404. Hai, giữ khoá `order_status`.
- **Hồ sơ huỷ đơn đang giao** dùng lại `ORDER_CANCELLED_MESSAGE`, `ORDER_CANCELLED_CODE` và `completion.lock_order_of_note`.

> File này cũng có trên nhánh `feat/w37-l1-be` (mục "Review L1 BE (07/10)"). Khi gộp, giữ cả hai mục, BE trước FE.

## Review L1 FE (08/10)

**Phạm vi:** commit `fcfe375` trên `feat/w37-l1-fe`, diff `2dcf666..HEAD` (21 file, chỉ thuộc `erp-console/` và `doc/`).
Đối chiếu với `02b-tech-design.md` §2.1–§2.5 và §6 (L1 FE).

**Kết luận: APPROVED.** Không có lỗi Critical, High hay Medium. Có 5 điểm Low và một nợ chuyển sang L3 (S6-AC8 phần đồng bộ hai
kho mock). Không cái nào chặn QA.

**Lệnh kiểm chứng:** worktree không có `node_modules`, nên Tech Lead **không chạy lại** `tsc`, `vitest` hay build. Kết quả dùng là
số điều phối viên đã chạy: `tsc` sạch; vitest 1031 test xanh; build `NEXT_PUBLIC_USE_MOCK=0` có `check-no-mock` và
`check-ai-chunks` XANH. Review dưới đây làm bằng đọc diff và lần theo nơi gọi.

### Soát theo yêu cầu

| Mục | Kết quả | Chứng cứ |
|---|---|---|
| `order_status` và toast | Đạt | `DeliveryStatusResponse.order_status?: string \| null` (`features/deliveries/api.ts`). `completeToast` (`deliveryUi.ts`) chỉ đổi câu khi giá trị là `"COMPLETED"`; thiếu khoá (BE cũ) thì giữ câu cũ. Dùng ở cả `MyDeliveriesScreen` lẫn `DeliveryDetailScreen`. Có test 3 nhánh |
| BR-GH-24 nhận theo `code`, không vào `CONFLICT_CODES` | Đạt | `isOrderCancelledError` = `ApiError` có `code === "BR-GH-24"`, không xét HTTP status. `shared/ui/form/useSubmit.ts` không bị sửa. Có test khẳng định `isConflictError(BR-GH-24) === false` |
| Hiện câu và tải lại khi gặp BR-GH-24 | Đạt | `ConfirmCompleteModal` hiện đúng `detail`, nút chính đổi thành "Tải lại" (gọi `onConflict`, tức tải lại), ẩn câu lỗi chung. `ReportFailureModal` làm tương tự qua prop mới `onReload`, cả hai nơi gọi đều đã truyền. "Nhận hàng đi giao" ở cả hai màn hiện câu đó rồi tải lại |
| S6 bộ lọc | Đạt | `labels.ts` bỏ lựa chọn `PAID`. "Chưa xong" giữ `BOOKED,PAID,PROCESSING`. Chip `PAID` trong `enums.ts` vẫn còn (S6-AC4) |
| Thanh bước S7 và test bảng | Đạt | `ORDER_STEPS` có 5 bước, bước 2 là `CONFIRMING`. `orderStepKey` chỉ trả `COMPLETED` khi `status === "COMPLETED"`. Bảng ánh xạ `PROCESSING` khớp 02b §6. Test duyệt 6×8 tổ hợp, khẳng định bước Hoàn tất ⇔ chip Hoàn tất (S7-AC3), cộng ca `PROCESSING` + phiếu `COMPLETED` → Đang giao. `OrderDetailScreen.tsx:128` đã truyền `hasInvoice: !!o.invoice`, nên nhánh mới `hasInvoice === false ? "BOOKED"` vẫn đúng. e2e `ed_batch3_orders.py` đổi kỳ vọng theo 5 bước mới |
| Luật dùng chung `orderCompletion.ts` | Đạt | Hàm thuần, khớp từng ca với `completion.is_delivery_finished` của BE: bỏ `CANCELLED`, rỗng là chưa xong, toàn `CANCELLED` là chưa xong. Hai mock đều dùng, test đủ các ca UC-4 |
| Mock không lọt vào bản build thật | Đạt | `orderCompletion.ts` nằm ở `shared/lib`, không có seed. Hàm `siblingStatuses` đặt ngay trong hàm mock export, theo bài học dev ghi lại. `check-no-mock` xanh ở build mock=0 (số của điều phối viên) |
| Không đụng `OrderDetailScreen.tsx`, `CancelOrderModal.tsx`, `frontend/` | Đạt | `git diff --stat` không có ba đường này. Không đụng `shared/ui/**`, `enums.ts`, `features/{permissions,ai,audit,auth,overview}` |
| Dữ liệu cá nhân, giá vốn | Đạt | Không có khoá mới chứa dữ liệu khách. Toast và câu lỗi không ghép tên hay SĐT. Không đụng cột giá vốn. Ảnh trong `shots/` chụp bằng mock (dữ liệu giả) |
| Contract | Khớp 02b | Mock trả 400 `{detail, code: "BR-GH-24", current_status}`, `order_status` có ở mọi nhánh. Hình dạng `refund_summary` khớp §2.5 |

### Chỗ lệch dev đã ghi: quyết định

1. **Hai kho mock không nối nhau.** Chấp nhận ở L1. Lý do: import chéo làm bản build thật giữ seed mock (`check-no-mock` đỏ), và
   ràng buộc đó có thật. Hệ quả là **S6-AC8 mới đạt một nửa**: mock Giao hàng trả `order_status` đúng luật, nhưng trang Đơn của
   mock không đổi theo. Chuyển sang L3. Hướng gợi ý: một kho dùng chung chỉ có ở chế độ mock, đặt trong
   `shared/lib/*.mock.ts` (tiền lệ là `dashboardSummary.mock.ts`), hai mock cùng đọc ghi, rồi chạy lại `check-no-mock`.
   QA **không** chấm S6-AC8 PASS trọn ở L1.
2. Bài học closure trong mock: ghi nhận, không phải lỗi.
3. Bộ dữ liệu riêng cho S6-AC1 (1/2/3/1): chuyển sang L3, cùng mục 1.
4. Đường BR-GH-24 trong hộp xác nhận chưa có e2e trình duyệt: chấp nhận. UI không mở được hộp cho phiếu đã huỷ, và vitest đã phủ
   hàm nhận diện cùng mock 400. Khi L3 nối BE thật, QA dựng ca đua (huỷ đơn sau khi màn đã mở hộp) để chụp thật.
5. Thanh bước đổi qua mô hình, `OrderDetailScreen.tsx` chưa sửa: đúng thiết kế, vì màn đọc `orderPath`.

### Điểm Low (không chặn)

- **L1** `features/orders/types.ts`: `OrderDetail.refund_summary` khai bắt buộc, nhưng BE thật chỉ trả khoá này từ L2. Hiện chưa
  màn nào đọc nên không lỗi lúc chạy. Chọn một trong hai: (a) để `refund_summary?:` cho tới khi L2 gộp; (b) bảo đảm L3 FE chỉ
  gộp sau L2 (đúng thứ tự trong 02b §5.2).
- **L2** `features/orders/mock.ts` (seed): `o.status = isDeliveryFinished([dStatus])`, nhưng `dStatus` lại suy ra từ trạng thái đơn
  đích, nên thực chất vẫn là gán cứng đội lốt luật. Làm lại cùng nợ S6-AC8 ở L3.
- **L3** `features/deliveries/mock.ts`: BR-GH-24 chỉ xét phiếu `CANCELLED`, không xét đơn đã huỷ mà phiếu cũ chưa huỷ (ca nhiều
  phiếu, BE §1.2 có xét). Mock không có ca đó nên chấp nhận được. Ghi lại để mock không bị coi là nguồn đúng.
- **L4** `features/deliveries/api.ts:27`: thêm một dòng trống thừa (nhiễu diff).
- **L5** `deliveries_order_completion.test.ts`: ca "còn phiếu khác" `push`/`pop` vào `MOCK_DELIVERY_NOTES` mà không có
  `try/finally`, và `post(36)` làm đổi trạng thái phiếu 36 cho các ca sau trong cùng file. Nên khôi phục trong `afterEach`.

### Nợ có sẵn (không thuộc lô)
Mock `STALE_STATE` của `status/` trả 409, còn BE trả 400 (02b §2.3). Vô hại vì FE xét theo `code`.

### Gộp nhánh
`03-dev-notes.md` và `03b-review-techlead.md` đều được tạo mới trên cả `feat/w37-l1-be` lẫn `feat/w37-l1-fe`, nên gộp sẽ xung
đột cả file. Cách xử lý: giữ cả hai mục (L1 BE trước, L1 FE sau), không ghi đè mục nào.

## Review L2 + L4 BE (08/10)

**Phạm vi:** nhánh `feat/w37-l2-l4-be`, hai commit `b2f5042` (L4, S3) và `3678db9` (L2, S4 + S5 + `refund_summary`), diff
`ebe7006..HEAD` gồm 8 file. Đối chiếu với `02b-tech-design.md` §1.5, §1.7, §2.5, §4 và §6 (L2, L4).

**Kết luận: APPROVED.** Không có lỗi Critical, High hay Medium. Có 3 điểm Low, không chặn QA.

### Lệnh Tech Lead tự chạy trong worktree
- 5 file test của W37 (`test_backfill_completed_orders`, `test_order_detail_completed`, `test_refund_completed_order`,
  `test_close_after_completion`, `delivery/tests/test_order_completion`): **OK**.
- `manage.py test apps.sales apps.inventory apps.delivery apps.reports` (DJANGO_DEBUG=1): chạy 1664 test, `errors=12`, `skipped=2`.
  Cả 12 lỗi là test trang admin, lỗi thiếu manifest staticfiles vì worktree không có `backend/staticfiles/`. Lỗi này cùng loại
  với lỗi đã ghi ở review L1 BE và không do code. Không có FAIL nào.
- `makemigrations --check --dry-run`: No changes detected.
- `check_naming.py`: exit 1. Nguyên nhân là 2 file FE đã có sẵn trên main. Không có dòng nào thuộc `backend/`.

### Soát theo yêu cầu

| Mục | Kết quả | Chứng cứ |
|---|---|---|
| `refund_summary` chỉ là số tiền | Đạt | `serializers.py`, `get_refund_summary` trả đúng hai khoá `refunded_amount` và `pending_amount`, giá trị qua `money_str`. Test kiểm tập khoá và không có SĐT/tên |
| Phiếu FAILED không tính | Đạt | Chỉ cộng `REFUNDED` và `PENDING`. Test có đủ ba loại phiếu và trường hợp đơn không có hoá đơn (`"0"/"0"`) |
| Không thêm query | Đạt | Dùng `invoice.refunds.all()` đã prefetch (`orders/api.py`). `test_no_extra_queries_for_refund_summary` so số query khi có 1 phiếu và khi có 3 phiếu, kết quả bằng nhau |
| Không đụng phần che dữ liệu của Lô 3 | Đạt | `customer_hidden_reason`, `get_customer` và `pii_hidden` không đổi. Khoá mới chỉ được chèn vào `Meta.fields`. NV giao bị giới hạn phạm vi vẫn thấy `refund_summary`. Đây là tiền, không phải dữ liệu cá nhân, và cùng mức với danh sách `refunds` đã lộ sẵn cho người đó |
| S3, mỗi đơn một giao dịch có khoá | Đạt | `with transaction.atomic()` → `select_for_update().get(pk=…)` → `complete_order_if_delivered(backfill=True)`. Luật xét lại trong khoá, dùng chung với S1. Lệnh chỉ khoá đơn; mọi đường đổi phiếu đều khoá đơn trước (L1), nên lệnh tuần tự với giao xong và huỷ |
| S3, idempotent | Đạt | `backfill_candidates` chỉ lấy đơn `PROCESSING`. Chạy lần hai in "Đã chuyển 0 đơn", số AuditLog không tăng (S3-AC3) |
| S3, AuditLog Hệ thống không có dữ liệu cá nhân | Đạt | `changes` gồm `status`, `delivery_note`, `delivery_note_id`, `backfill: "W37"`. `actor=None`, `actor_kind=system`. Phiếu gây ra là phiếu `COMPLETED` có `completed_at` mới nhất (có test). Output của lệnh (cả `--dry-run`) và câu lỗi chỉ có mã đơn và tên lớp exception, không in nội dung exception |
| S3, `--dry-run` tính ngoài khoá | Đạt | `_dry_run` đọc không khoá, chỉ dùng `is_delivery_finished`, không ghi DB, không AuditLog (S3-AC4). Kết quả dry-run có thể lệch với lúc chạy thật nếu giữa hai lần có thao tác. Như vậy là đúng ý: dry-run chỉ để ước lượng |
| S3, exit code | Đạt | Lỗi ở một đơn → đơn đó rollback → `CommandError` (exit 1), in số đơn đã chuyển. Chạy lại thì làm nốt (S3-AC7: đơn 1 xong, đơn 2 và 3 còn `PROCESSING`, lần sau chuyển 2). Lỗi ở AuditLog cũng rollback đơn đó |
| S3, không có route HTTP | Đạt | Test duyệt toàn bộ `get_resolver().url_patterns`, không có đường nào chứa `backfill`. Đoán URL thì nhận 404/405 |
| S3, `financial_snapshot` hai kỳ không đổi | Đạt | `test_s3_ac5_r1_…`: hoá đơn lùi 40 ngày, có chứng từ đảo ở kỳ hiện tại. Snapshot trước và sau bằng nhau, tính cả `period_pnl` qua service lẫn API, `batch_pnl` và 5 bảng chứng từ |
| S5, hoàn tiền đơn Hoàn tất | Đạt | AC1–AC7 đủ. AC2 so `financial_snapshot`: kỳ cũ không đổi số, chỉ kỳ của `confirmed_at` đổi. Đơn giữ `COMPLETED` cả khi hoàn toàn phần (AC3). Có các ca chặn: BR-HT-04, BR-GH-05, phân quyền |
| S4, chốt lô | Đạt | `inventory/batches/services.py` không bị sửa, đúng 02b §1.5. Test khoá `OPEN_ORDER_STATUSES` không đổi. AC2: đơn `PROCESSING` có phiếu `FAILED` vẫn chặn, đúng câu thông báo. AC3: chạy lệnh S3 rồi chốt được. AC4: các vai thiếu quyền nhận 403 và 401, không có AuditLog. AC5: Quản lý và NV kho không thấy `purchase_rate`, `landed_unit_cost` hay giá thử 99999 |
| Không rò giá vốn | Đạt | `refund_summary` không chứa giá vốn. Thêm test S7-AC10 (duyệt đệ quy, không có khoá giá vốn với `manager` và `warehouse_staff`) |
| Marker `naming: allow` | **Duyệt** cả 4 dòng | Các dòng gán bí danh hoặc lặp qua thuộc tính fixture cũ (`self.chu`, `self.quan_ly`, `self.nv_kho`, `self.nv_giao` của `test_l1_close_batch`; `self.kho` của `OrderApiBase`). Có ghi lý do. Cùng tiền lệ đã duyệt ở L1. Đổi tên fixture dùng chung nằm ngoài phạm vi |

### Điểm Low (không chặn)
- **L1** `backfill_completed_orders.py`, `_dry_run`: mỗi đơn chạy một query đọc trạng thái phiếu (N+1). Không đáng kể với dữ liệu
  hiện có. Nếu sau này nhiều đơn thì gom một query `values_list("sales_invoice__sales_order_id", "status")`.
- **L2** `test_close_after_completion.py`: `setUp` gọi thẳng `l1.CloseBatchS04Tests.setUp(self)` và mượn method của lớp khác.
  Cách này chạy được nhưng phụ thuộc vào nội bộ file test L1 cũ. Khi có dịp thì rút về fixture dùng chung.
- **L3** Lệnh in danh sách mã đơn đã chuyển. Đúng S3-AC4, nhưng khi chạy production thì **không chép output vào doc hay commit**
  (repo công khai). Nhắc lại trong bước chạy production của `03-dev-notes.md`.

## Review L3 BE (08/10)

**Phạm vi:** commit `af05872` trên nhánh `feat/w37-l3-be`, diff `c0e5522..HEAD`. Gồm `timeline.py`, hai file test mới và
dev-notes. `shop_api.py` không bị sửa. Đối chiếu với 02b §1.6, §2.5 (timeline), §2.6 (Shop) và §4 (R4).

**Kết luận: APPROVED.** Không có lỗi Critical, High hay Medium. Có 3 điểm Low, không chặn QA.

### Lệnh Tech Lead tự chạy trong worktree
- `manage.py test apps.sales.orders apps.delivery` (DJANGO_DEBUG=1): chạy 636 test, `errors=1`, `skipped=2`. Lỗi duy nhất là
  `test_f5b_gl03_ac10_admin_…`, do thiếu manifest staticfiles vì worktree không có `backend/staticfiles/`. Lỗi này có từ trước và
  thuộc môi trường, không do code.
- `apps.common.tests.test_ai_visibility`: OK.
- `makemigrations --check --dry-run`: sạch.
- `check_naming.py`: **OK (exit 0)**, không phát sinh vi phạm mới.

### Soát theo yêu cầu

| Mục | Kết quả | Chứng cứ |
|---|---|---|
| Logic gộp mốc | Đạt | `merged_note_ids` lấy từ AuditLog `complete_order` không có `backfill`, khoá theo `delivery_note_id`. Mốc `delivery_advance_status → COMPLETED` của phiếu thuộc tập này có nhãn "Đã giao — đơn hoàn tất (mã)", kind `delivered`, người làm là NV giao. Phiếu khác giữ "Giao hàng thành công (mã)". Dòng `complete_order` thường trả `None` (đã gộp). Dòng có `backfill == "W37"` thành mốc `order_completed` "Hệ thống chuyển đơn sang Hoàn tất (chuyển bù)", người làm là Hệ thống. Khớp 02b §1.6, S7-AC6 và AC7 |
| Không dữ liệu cá nhân hay `changes` thô | Đạt | Nhãn tự dựng, chỉ ghép mã phiếu. `test_s7_ac9` kiểm JSON timeline không có SĐT, tên, địa chỉ, và cũng không có chuỗi `complete_order`, `delivery_note_id` hay `changes` |
| Lọc dòng AI của lô dọn chữ vẫn giữ | Đạt | `_audits` vẫn bọc `exclude_ai_audit_rows(...)`, diff không đụng hàm này. `complete_order` là dòng Hệ thống, không có `proposal_ref`, nên không bị lọc. Test `test_ai_visibility` xanh |
| Shop đủ 7 dòng | Đạt | `TABLE` khớp đúng 02b §2.6. Dòng CANCELLED đã theo T30 "Đã huỷ" như chốt T2. Assert cả `status_label` lẫn `delivery.status_label`, và nhãn ≠ mã thô. `shop_api.py` không sửa vì bảng nhãn của lô dọn chữ đã đủ, đúng điều kiện ở 02b §6 L3 |
| Shop 404/429 | Đạt | Sai 4 số cuối trả 404, thân phản hồi không có "Hoàn tất", "COMPLETED" hay "Đã giao" (S8-AC4). Có test throttle theo IP và test throttle theo mã đơn đổi IP, đều ra 429 (S8-AC5). Tập khoá phản hồi bằng đúng tập khoá của đơn đang xử lý (S8-AC3). Khách không đăng nhập không đổi được trạng thái (AC7) |
| Giá vốn, phân quyền | Đạt | Không đụng serializer hay route. Timeline không có số tiền mới |

### Điểm Low (không chặn)
- **L1** `timeline.py`: hai điều kiện "có phải chuyển bù" không cùng một dạng. Tập gộp xét `not changes.get("backfill")`, còn
  nhánh hiện mốc xét `changes.get("backfill") != BACKFILL_MARKER`. Nếu sau này có giá trị `backfill` khác "W37", dòng đó sẽ
  không được gộp mà cũng không hiện. Nên dùng chung một hàm `_is_backfill(changes)`.
- **L2** `test_timeline_completed.py`, `test_s7_ac7`: test dựng dữ liệu cũ bằng cách **xoá dòng AuditLog** (`.delete()`) của bảng
  append-only. Trong test thì vô hại, nhưng là mẫu xấu dễ bị chép lại. Nên dựng như `BackfillBase._legacy` (đặt thẳng trạng
  thái phiếu và đơn), không xoá AuditLog.
- **L3** Cùng dòng đó có marker `# naming: allow - dựng dữ liệu cũ`, nhưng dòng không có định danh tiếng Việt nào, nên marker
  thừa và gây nhiễu cho lần soát marker sau. Bỏ marker (hoặc bỏ cả dòng nếu sửa theo L2).

Ghi chú hành vi, không phải lỗi: khi AI tắt mà phiếu được AI bấm giao xong thì dòng giao bị lọc. Đơn khi đó vẫn có chip Hoàn tất,
nhưng timeline không có mốc gộp. Lệnh AI đang tắt toàn hệ thống và chưa có lệnh AI nào giao phiếu, nên chưa phải xử lý.

## Review L3 FE (08/10)

**Phạm vi:** commit `eef6e1b` trên `feat/w37-l3-fe` (diff `c0e5522..eef6e1b`, 17 file ở `erp-console/`, `frontend/`, `doc/`). Nhánh
đã merge L3 BE (HEAD `37146dc`). Đối chiếu với 02b §2.5, §2.6, §6 (L3) và các Low của review L1 FE.

**Kết luận: CHANGES REQUESTED.** Có một lỗi Medium (M1, mock lọt vào bản build thật). Không có lỗi Critical hay High. Mọi mục
nghiệp vụ còn lại đều đạt; sửa M1 xong thì Tech Lead chỉ soát lại phần M1.

### Lệnh Tech Lead tự chạy
Build trong bản sao ở thư mục scratchpad (`rsync` mã nguồn, mượn `node_modules` của checkout chính). Worktree **không** bị sửa.
- `NEXT_PUBLIC_USE_MOCK=0 npm run build` của `eef6e1b`: build xanh. `check-no-mock` báo XANH (27 file mock, 43 chuỗi seed).
- Tìm thẳng trong `out/`: `grep -rl "cave_erp_mock_order_link" out` → **có**, ở `out/_next/static/chunks/23-9edda6ada01b774d.js`.
  Chunk này được nạp ở `/my-deliveries/`, `/print/label/`, `/print/pick-sheet/`.
- So với gốc `c0e5522`: build cùng lệnh, chuỗi `cave_erp_mock` **không có** trong `out/`. Tức là L3 làm phát sinh thêm.
- `tsc`, `vitest` và build Shop không chạy lại. Dùng số điều phối viên đã chạy trên nhánh đã merge: tsc sạch, vitest 1070,
  `check-ai-chunks` xanh, Shop build xanh.

### M1 (Medium): kho nối `orderLink.mock.ts` lọt vào bản build thật, và `check-no-mock` không bắt được
- **Chứng cứ:** trong chunk ở trên có `let T="cave_erp_mock_order_link";function v(){…sessionStorage…}let p={outcomes:[],cancelled:[]}`.
  Ngay sau đó là các lời gọi ở cấp module của `features/deliveries/mock.ts` (`E(10,8),E(10,8)…`, bảng tên người giao giả,
  bảng lý do thất bại).
- **Nguyên nhân gốc:** `features/deliveries/mock.ts` đã bị giữ lại trong bản build thật **từ trước L3**. Ở `c0e5522`, chunk
  `8984-*.js` đã chứa `{4:"Anh Phúc",7:"Anh Lâm",14:"Anh Khoa"}`. Module này có code chạy ở cấp module (gọi `Date.now()` để
  dựng seed) nên bundler không bỏ được. L3 thêm `import … from "@/shared/lib/orderLink.mock"` vào đúng module đó, nên kho nối
  bị kéo theo.
- **Vì sao gate không bắt:** `scripts/check-no-mock.mjs` chỉ quét file khớp `/^mock[^/]*\.ts$/` và `/^Mock.*\.tsx$/`. Hai file
  `orderLink.mock.ts` và `dashboardSummary.mock.ts` không khớp mẫu, và bảng tên giả của deliveries mock cũng không nằm trong
  danh sách chuỗi seed. Câu trong dev-notes và comment ở `deliveries/mock.ts` ("file nối chỉ có ở mock nên bản build thật
  không giữ seed") vì vậy **sai**.
- **Mức độ:** không có dữ liệu cá nhân thật hay giá vốn. Phần lọt là code chết và dữ liệu giả. Tuy vậy, L1 đã đặt "mock không
  lọt vào bản build thật" làm tiêu chí đạt, và gate đang báo xanh giả.
- **Yêu cầu sửa (trong L3 FE):**
  1. `check-no-mock.mjs` quét thêm `*.mock.ts` (mẫu `/\.mock\.ts$/`). Có thể thêm chuỗi đặc trưng tự rút từ khoá `KEY`. Sau
     bước này gate phải **đỏ** trên `eef6e1b`.
  2. Bỏ phần cấp module của `features/deliveries/mock.ts` khỏi bản build thật. Cách gợi ý: dựng seed lười trong một hàm
     (`MOCK_DELIVERY_NOTES` thành getter hoặc khởi tạo khi gọi lần đầu), không gọi hàm ở cấp module. Hoặc chuyển phần gọi
     `publishDeliveryOutcome` và `isOrderCancelledInMock` vào nhánh `if (process.env.NEXT_PUBLIC_USE_MOCK === "1")`.
  3. Kiểm lại: build mock=0, rồi `grep -rl "cave_erp_mock_order_link\|Anh Ph" erp-console/out` phải rỗng và `check-no-mock`
     xanh. Đầu ra lệnh grep ghi vào dev-notes.
  4. Sửa comment ở `deliveries/mock.ts:772-773` và câu tương ứng trong dev-notes cho đúng sự thật.

  Nếu bước 2 phình ra ngoài phạm vi W37, điều phối viên có thể tách bảng tên giả (lỗi có từ trước) thành nợ riêng. Khi đó L3
  vẫn phải làm bước 1 và bảo đảm `orderLink.mock.ts` không còn trong `out/`.

### Các mục còn lại: đạt

| Mục | Kết quả | Chứng cứ |
|---|---|---|
| `refundSummaryLine` | Đạt | Hàm thuần trong `orderDetailModel.ts`. Bỏ phần bằng 0. Cả hai bằng 0 hoặc thiếu khoá (BE cũ) thì không vẽ dòng. Số tiền format bằng `vnd`. Màn chỉ vẽ `<p data-testid="order-refund-summary">` dưới chip, chip vẫn là Hoàn tất (S7-AC5). Có test |
| Nút "Lập phiếu hoàn tiền" | Đạt | Đơn `COMPLETED` có `create_refund` thì nút chính là "Lập phiếu hoàn tiền" (S7-AC4). Không có mục Huỷ vì BE không trả `cancel`. Quyền vẫn theo `available_actions` (S7-AC8) |
| `complete_order` trong `auditModel` | Đạt | `complete_order: "Đơn hoàn tất"` |
| Bộ đơn mẫu S6-AC1 | Đạt | `PLAN_COMPLETION` có 7 đơn: 1 giữ chỗ, 2 đang xử lý (đang giao, giao thất bại), 3 hoàn tất (một đơn có REFUNDED 200.000 và PENDING 100.000), 1 huỷ. Bật bằng khoá mock `cave_erp_mock_orders_dataset` |
| Low #2 của L1 (gán cứng) | Đã xử lý | Kế hoạch khai `"DELIVERY"` cùng thẻ phiếu. Trạng thái đơn suy từ trạng thái phiếu qua `isDeliveryFinished`, không còn suy ngược từ đơn |
| Low #3 của L1 (đơn huỷ, phiếu cũ chưa huỷ) | Đã xử lý | `isOrderCancelledInMock(order.id)` chặn BR-GH-24 như BE §1.2. Mock Đơn gọi `publishOrderCancelled` khi huỷ. Phần này dính M1 vì đi qua kho nối |
| Kho nối mock: chức năng | Đạt | Mock Giao hàng gửi kết quả, mock Đơn đọc ở lần tải sau (S6-AC8). Tổng quan mock lấy `pending_orders` và đơn gần đây từ kho đơn khi dùng bộ mẫu hoặc đã có kết quả nối. Không có dữ liệu khách trong hộp (chỉ id đơn và mã trạng thái) |
| Shop mock theo §2.6 | Đạt | `PAID_ORDER_LABELS`: CONFIRMING thì "Đã thanh toán – chờ vựa gọi xác nhận"; READY, DELIVERING, FAILED thì "Đang xử lý"; COMPLETED thì "Hoàn tất" và phiếu "Đã giao" (S8-AC6). Hết chuỗi lạc "Đã thanh toán, đang soạn hàng" cho READY, DELIVERING, FAILED. Có e2e `frontend/e2e/order_lookup_completed.py` |
| Sửa kỳ vọng `ed_batch3_orders` | Duyệt | Đơn 109 (`COMPLETED`) đổi kỳ vọng nút từ "Lập phiếu hoàn" sang "Lập phiếu hoàn tiền", đúng S7-AC4. Không nới kỳ vọng nào khác |
| Không đụng vùng cấm | Đạt | Không sửa `shared/ui/**`, `enums.ts`, `features/permissions/**`. `OrderDetailScreen.tsx` được sửa đúng như 02b §6 L3 cho phép |

### Low (không chặn)
- **L1** Cùng một thao tác có hai nhãn. Nút chính của đơn `COMPLETED` là "Lập phiếu hoàn tiền", còn mục "…" và đơn đã huỷ vẫn là
  "Lập phiếu hoàn". Để lô áp tên chuẩn thống nhất một nhãn.
- **L2** `features/overview/mock.ts` import `@/features/orders/mock` (mock gọi chéo, có tiền lệ). Sau khi sửa M1, kiểm cùng lúc
  rằng chuỗi seed của orders mock vẫn không có trong `out/`.

### Re-review sau f79f622 (08/10)

**Kết luận: APPROVED.** M1 đã đóng. Kết luận của toàn mục "Review L3 FE" nay là APPROVED, còn 2 điểm Low đã ghi ở trên (không chặn).

**Soát `git show f79f622`:**
- `features/deliveries/mock.ts`: seed chuyển thành `buildSeed()`, dựng lười qua `mockDeliveryNotes()`. Không còn code nào chạy ở
  cấp module. Mọi chỗ đọc `MOCK_DELIVERY_NOTES` đã đổi sang `mockDeliveryNotes()` và cùng trỏ một mảng, nên các thao tác vẫn đổi
  tại chỗ như cũ.
- `features/deliveries/api.ts`: bỏ import tĩnh. `mockApi()` chỉ `require("./mock")` khi `NEXT_PUBLIC_USE_MOCK === "1"`, và chỉ
  được gọi trong nhánh `isMock`. Bản build thật bỏ được cả nhánh này. Hàm, route và contract không đổi.
- `scripts/check-no-mock.mjs`: quét thêm `*.mock.ts`, thêm 4 loại chuỗi seed (khoá `cave_erp_mock_*`, tên người giả, SĐT giả 10
  số, mã mẫu viết hoa có số, trừ `BR-`). Số chuỗi tăng từ 43 lên 232.
- Test chỉ đổi cách lấy kho (`mockDeliveryNotes()`), không nới assert nào. Ca "còn phiếu khác" đã có `try/finally` (đóng Low L5 của L1).
- Comment ở `deliveries/mock.ts` đã sửa cho đúng.

**Lệnh Tech Lead tự chạy** (bản sao trong scratchpad lấy bằng `git archive f79f622`, mượn `node_modules` của checkout chính):
- `NEXT_PUBLIC_USE_MOCK=0 npm run build`: xanh.
- `grep -rlE "cave_erp_mock|Anh Ph|Anh Lâm|Anh L\xe2m|Anh Kh|TOM-SU-1|DH-260928|0900000" out`: **rỗng**.
- `check-no-mock.mjs` trên bản build mới: XANH (30 file mock, 232 chuỗi, 254 file build).
- Chạy `check-no-mock.mjs` **mới** trên bản build **cũ** của eef6e1b: **ĐỎ**, bắt đúng 2 chỗ lọt là "Anh Khoa" (tên giả của
  deliveries mock) và `cave_erp_mock_order_link`. Gate nay có tác dụng thật.
- Không chạy lại vitest hay e2e. Dùng số fe-dev báo (vitest 1070, e2e xanh). Điều phối viên nên chạy lại vitest trên nhánh trước
  khi commit gộp.

Ghi chú: `features/returns/mock.ts` import `deliveries/mock`. Đây là mock gọi mock nên vô hại, và bản build mới đã sạch.
