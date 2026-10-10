# Review P1–P7: tiền, kho, chứng từ và AI tự làm
> **ĐÃ ĐÓNG — lịch sử (rà 11/10).** Lỗi đã sửa ở P8 (`2026-09-30-sua-loi-review`, XONG). Không dời thư mục vì test trong code còn trỏ tới.

> Tech Lead (Claude), 2026-09-30. Nhánh `main`, HEAD `75e5dd3`. Chỉ đọc code, không sửa code sản phẩm, không commit.
> Đối chiếu với: `2026-09-28-sua-loi-bao-mat` (S04, S06, S07), `2026-09-28-cskh-xac-nhan-in-tem` (CS-07, CS-08, CS-09),
> `2026-09-28-ai-digital-worker` (DW-06, DW-18 → DW-27).
>
> **Kết luận: REVIEW FAIL.** Có 4 lỗi mức Cao đã tái hiện được bằng test. Trong đó có một lỗi làm job AI chết cứng, và một lỗi làm
> mất dòng giao dịch tiền khách đã chuyển. Cần sửa xong F01–F05 rồi mới bật AI mức B hoặc bật `CSKH_AUTO_CANCEL_ENABLED` trên staging.

## Cách kiểm chứng
- Test tái hiện đặt ở scratchpad, không nằm trong repo:
  `PYTHONPATH=<scratchpad> DJANGO_DEBUG=1 .venv/bin/python manage.py test review_repro.tests` (R1–R6 bên dưới). Các test này
  kế thừa `CloseBatchAiTests` (test_dw25) và `CskhL3BaseTestCase` (test_cskh_l3), nên dùng đúng dữ liệu dựng sẵn của dự án.
- `manage.py makemigrations --check --dry-run` → `No changes detected`.
- `git diff --name-status 91a9fc3^ HEAD -- backend/**/migrations` → chỉ có file thêm mới (A), không sửa migration cũ.

## Bảng phát hiện

| Mã | Mức | File:dòng | Mô tả | Tái hiện | Đề xuất |
|---|---|---|---|---|---|
| F01 | **Cao** | `backend/apps/ai/execution/safety.py:100-116`; hậu quả ở `backend/apps/ai/management/commands/run_due_ai_actions.py:63-140` | `check_ai_close_batch_conditions` lọc theo `payment_transaction__order_id__in` và `PaymentTransaction.objects.filter(order_id__in=…)`. Model không có field `order` (tên đúng là `sales_order`), nên mọi lô đã từng bán (có `SalesOrderLineBatch`) đều gây `FieldError`. Hậu quả: (a) `POST /api/ai/commands/inventory.batch.close/call/` trả 500. (b) Job `run_due_ai_actions` văng exception ra ngoài vòng lặp, việc AI giữ nguyên `SCHEDULED` và lần chạy sau lại văng. Mọi việc tới hạn xếp sau nó, cùng bước đẩy việc quá hạn 2 giờ, **không bao giờ chạy** (poison pill). Test DW-25 chỉ dựng lô chưa từng bán (`_create_fully_eligible_batch` không có `SalesOrderLineBatch`), tức là chỉ test đường thuận. | R1: lô đủ điều kiện, thêm 1 dòng bán thuộc đơn `COMPLETED`, rồi gọi `check_ai_close_batch_conditions` → `FieldError: Unsupported lookup 'order_id'`. Chạy `call_command("run_due_ai_actions")` → văng `FieldError`, action vẫn `SCHEDULED`. | Đổi thành `payment_transaction__sales_order_id__in` và `sales_order_id__in`. Trong job, bọc từng việc bằng `try/except`: lỗi thì chuyển `ESCALATED`/`FAILED` và ghi log chỉ gồm id, rồi đi tiếp việc sau. Thêm test DW-25 cho lô đã bán, có phiếu hoàn PENDING và có giao dịch OPEN. |
| F02 | **Cao** | `backend/apps/inventory/batches/services.py:246-294` (`check_cancel_expired_batch`, `cancel_expired_batch`) | Huỷ lô quá hạn chỉ kiểm tra `status == EXPIRED`, rồi ghi `WRITE_OFF` toàn bộ `qty_available`, kể cả phần đang giữ chỗ (`qty_reserved`) của đơn BOOKED. Theo C1, job `update_batch_statuses` cố ý không nhả giữ chỗ để đơn giữ trước nửa đêm vẫn thanh toán được. Khi khách của đơn đó chuyển tiền, `issue_invoice` gặp lỗi "Xuất vượt tồn", `_record_payment` rollback, và **không có `PaymentTransaction` nào được ghi**: tiền đã vào tài khoản nhưng không vào sổ, không vào hàng chờ lệch. | R5: tạo đơn BOOKED giữ 2 kg, đặt lô EXPIRED rồi `cancel_expired_batch` → lô `CANCELLED`, avail 0, reserved 2. Gọi `confirm_payment` → `BusinessError: Xuất vượt tồn…`, đơn vẫn BOOKED, không có dòng giao dịch. | Chặn huỷ khi `qty_reserved > 0` hoặc còn đơn mở tham chiếu lô (tái dùng phần kiểm tra của `check_close_batch`), trả 400 `BR-LO-03` kèm số đơn. Cách khác (cần Duy chọn): nhả giữ chỗ và tự huỷ các đơn BOOKED đó trước khi ghi `WRITE_OFF`. Thêm test tương ứng. |
| F03 | **Cao** | `backend/apps/delivery/cskh/services.py:141-166` (`record_call`) | Với task `REFUND_CALL` (đơn đã bị hệ thống tự huỷ, phiếu giao `CANCELLED`, kho đã hoàn, phiếu hoàn PENDING), `record_call` vẫn nhận `CONFIRMED`/`CONFIRMED_CHANGED`. Kết quả là phiếu giao chuyển `CANCELLED → PREPARING` và kho soạn hàng cho một đơn đã huỷ và đang chờ hoàn tiền. `CALLBACK`/`WRONG_NUMBER`/`WANT_*` cũng được nhận và làm task lệch trạng thái. Lỗi xảy ra khi CSKH bấm trên màn hình cũ, hoặc khi tranh với job ở chiều job chạy trước. | R2: `auto_cancel_overdue` → đơn `CANCELLED`, phiếu `CANCELLED`, task `REFUND_CALL`. Sau đó `record_call(CONFIRMED)` → phiếu `PREPARING`, task `DONE`. | Khi `task.state == REFUND_CALL` chỉ cho `UNREACHABLE`/`NOTIFIED`. Khi `note.status == CANCELLED` thì mọi kết quả khác trả 409 `STALE_STATE`. Thêm test cho cả hai thứ tự tranh chấp. |
| F04 | **Cao** (có từ trước, P4 làm nặng thêm) | `backend/apps/sales/orders/services.py:332-402` (`cancel_paid_order` không đổi hoá đơn); `backend/apps/reports/services.py:44-49` (`batch_pnl` chỉ loại hoá đơn `CANCELLED`) | Huỷ đơn đã thanh toán sẽ hoàn kho về lô gốc, nhưng hoá đơn vẫn `ISSUED`. Vì vậy `batch_pnl` vẫn tính doanh thu và số kg đã bán của đơn đã huỷ. Số kg đã hoàn nếu bán lại sẽ bị cộng doanh thu hai lần, làm lô "lãi ảo", và chốt lô sẽ đông cứng con số sai. Job tự huỷ CSKH (CS-08) khiến việc này xảy ra tự động. S07 đã ghi "chưa có service nào đổi hoá đơn sang CANCELLED". | R6: sau khi tự huỷ → đơn `CANCELLED`, hoá đơn `ISSUED`, lô còn đủ 100 kg nhưng `batch_pnl` vẫn cho revenue 300.000, qty_sold 2. | **Cần Duy quyết** một trong hai: (a) `cancel_paid_order` đổi hoá đơn sang `CANCELLED` khi hoàn kho (khớp S07, và `period_pnl` đã lọc `ISSUED`, cần kiểm lại BR-BC-03 với phiếu hoàn); hoặc (b) `batch_pnl` loại các dòng phân bổ thuộc đơn `CANCELLED` có `CANCEL_RESTORE`. Bổ sung BR-BC-04. |
| F05 | Trung bình | `backend/apps/inventory/batches/services.py:145-152` (`publish_batch`) | `publish_batch` không có `atomic`/`select_for_update` và không đọc lại trạng thái. Nó dùng object lấy từ `get_object()` rồi ghi đè `status`. Khi huỷ phiếu nhập (DW-18, có khoá) chạy xong trước, publish vẫn thành công và lô `CANCELLED` bị ghi thành `SELLING`. Như vậy DW-18-AC4 ("huỷ cùng lúc publish → đúng một thao tác thành công") không đạt. Test AC4 hiện chỉ gọi huỷ hai lần liên tiếp. | R3: `create_and_submit_receipt` → lấy object lô → `cancel_receipt` → `publish_batch(object cũ)` → phiếu `CANCELLED`, lô `SELLING`, qty 0. | Bọc `publish_batch` trong `atomic` + `select_for_update().get(pk=…)` rồi mới kiểm `DRAFT`. Thêm test đúng nghĩa AC4 (huỷ trước rồi publish bằng object cũ → 400). |
| F06 | Trung bình | `backend/apps/sales/payments/auto_confirm.py:166-200` (`_escalate_to_chu`) | Job DW-26 không idempotent ở nhánh chuyển Chủ. (a) Mỗi lần chạy (dự kiến 5 phút một lần) lại ghi thêm một dòng AuditLog `escalate_unmatched_payment` cho **mọi** giao dịch OPEN không khớp tuyệt đối (thiếu tiền, ORPHAN, OVERPAID…). AuditLog là bảng append-only nên sẽ phình liên tục. (b) Nếu Chủ đã đóng việc (`REJECTED`/`DONE`…), lần chạy sau lại đặt về `ESCALATED`. | R4: chạy 2 lần → 2 dòng audit. Đặt action `REJECTED` rồi chạy lại → quay về `ESCALATED`. | Chỉ ghi audit khi `created` hoặc khi lý do thay đổi. Không mở lại action đã ở trạng thái kết thúc. Cân nhắc chỉ quét giao dịch `UNMATCHED` (các loại còn lại đã ở hàng chờ lệch của Chủ). |
| F07 | Thấp | `backend/apps/ai/execution/pipeline.py:329` | Hạn mức ngày tính mốc bằng `timezone.now().replace(hour=0…)`. Hàm này trả giờ UTC, nên "ngày" bắt đầu lúc 07:00 giờ Việt Nam. Hệ quả là việc AI tạo từ 00:00 đến 07:00 tính vào hạn mức của hôm trước. | Đọc code (`USE_TZ=True`, `TIME_ZONE=Asia/Ho_Chi_Minh`). | Dùng `timezone.localtime().replace(hour=0, …)`. |
| F08 | Thấp | `backend/apps/delivery/cskh/services.py:660,669` so với `:135-136` | `escalate_expired_windows` khoá task rồi mới khoá phiếu, ngược với thứ tự chuẩn §1.5 (phiếu → task) mà `record_call` dùng. Trên Postgres có thể xảy ra deadlock: một bên bị huỷ, và nếu đó là CSKH thì họ nhận lỗi 500. | Đọc code. | Khoá `DeliveryNote` trước, rồi mới khoá `ConfirmationTask`. |
| F09 | Thấp (cần Duy quyết) | `backend/apps/inventory/batches/services.py:170-173` | `check_close_batch` vẫn cho chốt lô `EXPIRED` còn tồn. Đây là ngoại lệ "tạm thời" từ S04, có từ khi chưa có service huỷ. Nay đã có DW-06, nhưng chốt thẳng lô EXPIRED còn tồn vẫn để `qty_available > 0` trên lô đã chốt và không ghi lỗ hết hạn. Luật sàn AI chốt lô (DW-25) cũng cho qua trường hợp này. | Đọc code và 02b S04 dòng 173. | Bỏ ngoại lệ `EXPIRED` (bắt buộc huỷ lô trước, tức chỉ nhận `CANCELLED` hoặc tồn = 0), sửa test S04 tương ứng. |
| F10 | Thấp | `backend/apps/ai/actions/services.py:177-178, 229-239` | `undo_ai_action` gán cứng `"nhap_lo" in command` → `cancel_receipt` và bỏ qua tên action trong `undo="cancel_action:<act>"`. Nếu sau này có lệnh B khác, hàm có thể huỷ nhầm `PurchaseReceipt` trùng pk, hoặc đánh `UNDONE` mà không đảo gì. Ngoài ra, khi `AI_ENABLED=false` thì người dùng không hoàn tác được việc B vừa làm (410). | Đọc code (hiện chỉ `nhap_lo` đạt được mức B, nên chưa gây lỗi). | Dispatch đúng action huỷ đã khai báo. Không có đường hoàn tác thì trả 400. Cho phép hoàn tác kể cả khi AI tắt. |
| F11 | Thấp | `backend/apps/purchasing/receipts/services.py:212-218`; `backend/apps/reports/services.py:70-75` | Huỷ phiếu nhập ghi bút toán đảo bằng `WRITE_OFF`. `batch_pnl` coi mọi `WRITE_OFF` âm là "lỗ hết hạn", nên lô nhập sai hiện `expired_cost` bằng toàn bộ giá trị lô. | Đọc code. | Lọc theo `reference` hoặc thêm loại chuyển động riêng (chỉ đổi choices, migration nhỏ). Số liệu này chỉ để hiển thị. |
| F12 | Thấp | `backend/apps/sales/payments/auto_confirm.py:158-160,170` | Khi không có user `chu`, việc được giao cho **bất kỳ** user active nào (có thể là `nv_giao`). Chuỗi `{exc}` được ghi vào `downgrade_reason` và log. | Đọc code. | Không có Chủ thì bỏ qua và log cảnh báo. Chỉ ghi mã lỗi `BusinessError.code`. |
| F13 | Thấp (vận hành) | `doc/ops/` và `02c-giao-viec.md` V-DW1 | Không có tài liệu vận hành hay lịch chạy cho `run_due_ai_actions` và `auto_confirm_exact_payments`. Code cần `AI_PRODUCTION_READY=1` **ở staging** để mở vùng đỏ, trần > C và DW-26, trong khi 02c V-DW1 ghi ngược lại ("mở ở staging khi `AI_PRODUCTION_READY=false`"). Tên biến dễ khiến người vận hành đặt nhầm trên production. | `grep` trong `doc/ops/` → không có kết quả. | Ghi vào `doc/ops/moi-truong.md`: staging đặt `AI_PRODUCTION_READY=1` và `AI_WRITE_LEVELS_ALLOWED=B`, production giữ `0`/`C`; lịch chạy các job. Sửa câu V-DW1. |

## Nghi ngờ, chưa xác minh đến cùng
- `run_due_ai_actions` gọi view trong `transaction.atomic()` của vòng lặp. Nếu view gặp lỗi DB ngoài savepoint (IntegrityError mà
  `dispatch_command` nuốt), transaction bị hỏng và `locked_action.save()` sẽ văng `TransactionManagementError`, cùng dạng poison pill
  như F01. Các service hiện có (`close_batch`) đều có `@atomic` riêng nên chưa thấy đường nào kích hoạt. Cách sửa của F01 (bọc
  try/except theo từng việc) cũng chặn luôn trường hợp này.
- Idempotency của `POST /api/ai/commands/<id>/call/` (`pipeline.py:106-131`) là "đọc rồi tạo". Hai request cùng khoá gửi đồng thời sẽ
  đụng `UniqueConstraint` và trả 500 thay vì trả lại kết quả cũ. Ngoài ra, khi phát lại, việc B đã `DONE`/`SCHEDULED` bị trả về dạng
  `outcome="proposal"`. Không ảnh hưởng tiền hay kho, chỉ sai contract hiển thị.
- `test_dw21_ac5` chỉ chứng minh idempotent khi chạy tuần tự (mock dispatch), chưa có test tranh chấp thật với `skip_locked`
  (SQLite không hỗ trợ). Đọc code thấy khoá đúng.

## Đã kiểm, ổn
- **S04 `close_batch`**: `@transaction.atomic` + `select_for_update` **trước** mọi phép kiểm. Có kiểm BR-LO-05 (đã chốt), tồn, giữ chỗ,
  đơn mở (BOOKED/PAID/PROCESSING), hàng hoàn DRAFT, Purchase Invoice, và BR-KK-05 (có phiếu kiểm kê APPROVED, không có phiếu DRAFT).
  Có ghi AuditLog.
- **S06/S07 `batch_pnl`**: `total_cost = purchase_cost + allocated_cost`. Hao hụt, hỏng và hết hạn chỉ để hiển thị. Doanh thu loại hoá
  đơn `CANCELLED`. Hàng hoàn "Huỷ bỏ" ghi ledger `WRITE_OFF` với qty 0 nên không bị đếm trùng vào hết hạn.
- **Throttle**: các scope tra đơn, tạo đơn, checkout, login, cskh_search, public_content, ai_call đều có, mức đọc từ env, và tắt khi
  `TESTING`.
- **CS-08 tự huỷ**: cờ `CSKH_AUTO_CANCEL_ENABLED` mặc định `0`. Khoá theo thứ tự đơn → phiếu → task và đọc lại sau khoá. Chỉ huỷ khi
  phiếu còn `CONFIRMING` (đơn đã sang Soạn hàng thì bỏ qua). Chạy lại không huỷ hay hoàn trùng: task đã là `REFUND_CALL`, và phiếu hoàn
  dùng `request_id = uuid5(order.pk)`. Kho hoàn về đúng lô gốc qua `SalesInvoiceLineBatch` (`CANCEL_RESTORE`). Phiếu hoàn tạo
  `actor=None`, trạng thái PENDING chờ Chủ. Lô đã chốt thì chặn (BR-LO-05). Khi tranh chấp mà CSKH xác nhận trước thì job bỏ qua đúng
  (chiều ngược lại là F03).
- **AI mức B và job**: `effective_level` lấy min của mức user, trần spec, `AI_WRITE_LEVELS_ALLOWED` và trần policy. `global_mode=off`
  trả OFF, kill cá nhân trả C. Job đọc lại `is_active`, kill cá nhân và `effective_level` (gồm cả AI_ENABLED, quyền T1/T2 hiện tại, công
  tắc vùng đỏ). Khoá dùng `skip_locked`, chạy view bằng **đúng user chủ AI** (`force_authenticate(owner)`). Huỷ lịch có khoá dòng, và
  `undo_until = execute_after` nên không tranh với job. Nhánh B hoàn tác bằng trạng thái bọc trong `atomic` cùng AuditLog. Hoàn tác
  `nhap_lo` = `cancel_receipt` (huỷ bằng trạng thái, không xoá dòng nào).
- **Vùng đỏ**: `chot_lo` dùng `undo="defer"` với độ trễ `AI_RED_ZONE_DELAY_MINUTES=30`, công tắc đóng thì trần C, và kiểm lại điều
  kiện sàn khi tới hạn. `xac_nhan_hoan` có `max_level=C` nên không bao giờ lên B, luôn `ESCALATED` cho `chu` và đã bỏ `bank_txn_ref`
  của AI. `confirm_payment_manual` có trần C. DW-26 ghi tiền qua `resolve_payment` sẵn có (không có đường ghi tiền mới), khớp mã đơn
  bằng regex tất định (không đưa `raw_payload` vào model), log chỉ gồm mã GD và mã đơn, và bị chặn bởi `AI_PRODUCTION_READY`,
  `AI_ENABLED` cùng công tắc riêng của Chủ. `update_policy` chặn mở vùng đỏ và trần > C khi `AI_PRODUCTION_READY=false`.
- **Trần kg/tiền của nhập lô**: tính từ `lines[].qty × rate`, khớp đúng field của `NhapLoInput`.
- **DW-06/DW-18**: dùng `atomic` + `select_for_update`, ghi bút toán `WRITE_OFF` append-only, không xoá dòng sổ kho. Quyền:
  `cancel_expired_batch` chỉ `chu` (migration 0009). Huỷ phiếu nhập cho người tạo, `quan_ly` hoặc `chu`. Chặn khi có hoá đơn mua, đã
  phân bổ chi phí, lô không còn DRAFT hoặc đã có chuyển động khác RECEIPT.
- **Migration**: chỉ có file mới. `AlterField` là `Refund.created_by` (cho phép null, để phiếu hoàn do Hệ thống tạo) và thêm choice
  `CANCELLED` cho `PurchaseReceipt.status`. `makemigrations --check` sạch. Không có test nào bị skip.
