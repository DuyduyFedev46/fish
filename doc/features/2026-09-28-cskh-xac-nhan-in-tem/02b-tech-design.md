# CSKH gọi xác nhận → in tem → kho soạn hàng — Thiết kế kỹ thuật
> Tech Lead · 2026-09-28 · Trạng thái: **ĐÃ DUYỆT (Duy 28/09 — theo chốt scope)**
> Nguồn: `01-analysis.md` (ĐÃ DUYỆT, Q-C1…C5), `02-stories.md` (CS-01…CS-18, ĐÃ DUYỆT). Code đọc trên nhánh `wip/autosave`
> commit `cc47542` (28/09). Làm **sau** hồ sơ `2026-09-28-sua-loi-bao-mat` (throttle `apps/common/throttling.py`, sửa tra đơn
> Shop, merge vào `main`). Người hiện thực: Gemini/Antigravity theo `02c-giao-viec.md`.
> Mọi dữ liệu trong JSON mẫu là **giả** (`Khách Thử A`, `0900000123`, `Số 1 Đường Thử`).

## Mục lục
0. Tóm tắt quyết định · 0b. Mặc định 🟡 đã áp · 0c. Chỗ contract khác bản PO (FE bám bản này)
1. Kiến trúc & máy trạng thái
2. Model & migration
3. Quyền, Group `cskh`, phạm vi dữ liệu cá nhân
4. Contract API BE↔FE
5. Job nền (tự chuyển Quản lý, tự huỷ)
6. Tem 100×150 in từ trình duyệt
7. Thông báo cho khách (Shop)
8. Lệnh AI: `required_perms` và danh sách chặn
9. Tham số settings/env
10. Rủi ro bắt buộc + cơ chế chặn + test
11. Thứ tự thực hiện + lô
12. Câu hỏi kỹ thuật · Việc Duy cần làm
13. Review (Việc 3 — để trống)

---

## 0. Tóm tắt quyết định

| # | Quyết định | Căn cứ |
|---|---|---|
| 1 | Thêm trạng thái phiếu giao **`CONFIRMING`** ("Chờ xác nhận") **trước** `PREPARING`. Chỉ phiếu sinh từ signal hoá đơn mới vào `CONFIRMING`; `create_delivery_note()` gọi thẳng giữ mặc định `PREPARING` (test service cũ không đổi). Phiếu cũ trước deploy **không** bị chuyển. | Q-C1, BR-GH-11, CS-04-AC7 |
| 2 | Tình trạng gọi đặt ở **bảng riêng 1–1 `delivery.ConfirmationTask`** (không nhồi vào `DeliveryNote`). `DeliveryNote` chỉ thêm các "sự thật" của phiếu: `confirmed_at/by`, `confirm_skipped`, người nhận hộ. | Giữ `DeliveryNote` gọn; hàng chờ lọc 1 bảng |
| 3 | Bản ghi cuộc gọi **`delivery.CustomerCall`** append-only; lượt in tem **`delivery.LabelPrint`** (không lưu nội dung tem). | BR-GH-12, BR-GH-16, UC-CS-3 |
| 4 | Mốc thời gian **tính lúc đọc** từ tham số (`window_ends_at = first_unreachable_at + W`, `next_call_after = last_unreachable_at + M`, `decide_deadline = escalated_at + D`). Không lưu mốc đã cộng → đổi env có hiệu lực ngay. | Bất biến 7, CS-07-AC6, CS-08-AC8 |
| 5 | Job = **management command `process_cskh_deadlines`**, chạy bằng **Cloud Run Job + Cloud Scheduler `*/5`** — đúng cơ chế đang dùng cho `cancel_expired_orders`/`update_batch_status` (production **không** có Redis/Celery; `CELERY_BEAT_SCHEDULE` chỉ dùng khi dev). **Không có endpoint HTTP** kích job. | `doc/ops/moi-truong.md`, CS-08-AC11 |
| 6 | Tự huỷ đi qua **đúng** `cancel_paid_order(actor=None, reason_code="UNREACHABLE_AUTO")` + `create_invoice_refund(actor=None, request_id=uuid5(…))` → idempotent nhờ khoá dòng + `request_id` tất định. Chỉ chạy khi **`CSKH_AUTO_CANCEL_ENABLED=1`** (mặc định **tắt**) — cổng phát hành chờ `legal-vn`. | Q-C2, BR-HT-10, CS-08 |
| 7 | Nhóm thứ năm **`cskh`** (data migration). Phạm vi dữ liệu cá nhân = Q trên phiếu giao: *(phiếu `CONFIRMING` + task ∈ {PENDING, CALLBACK, ESCALATED})* **hoặc** *(user đã gọi phiếu đó trong `CSKH_PII_RECENT_DAYS` ngày)*. Chu/Quản lý/NV kho giữ phạm vi đầy đủ như hiện nay. | Q-C5, BR-GH-18 |
| 8 | Tem in bằng **trang in riêng `/print/label/?note=<id>&print_no=<n>`** ngoài khung console, `@page 100mm 150mm`, QR sinh **trên máy** (thư viện `qrcode`, như Shop). URL chỉ có id + số lần in. | Q-C4, §7.3 BA |
| 9 | Thông báo khách: key **`cancel_notice`** trong tra đơn Shop + khối **`cskh_notice`** trong endpoint công khai **`GET /api/public/site-info/`** (dùng chung với GL-01 hồ sơ khung go-live — không mở endpoint cấu hình thứ hai). Câu chữ ở BE (hằng số, chờ `legal-vn`). | BR-GH-21, CS-10 |
| 10 | Mọi endpoint mới khai `required_perms` trên `@action`; `/api/cskh/`, `/api/public/` và `…/label/` thuộc **danh sách cấm AI**; khoá PII mới (`recipient_*`, `phone_masked`) vào bộ lọc đầu ra AI. | 02b hồ sơ AI §2.5, §3 |

## 0b. Mặc định 🟡 đã áp (Duy lật được — Duy duyệt theo chốt scope 28/09)

| # | Câu hỏi PO | Chọn | Hệ quả kỹ thuật |
|---|---|---|---|
| 🟡 D1 | Tự huỷ thì ai lập phiếu hoàn? | **Hệ thống tự lập** phiếu hoàn toàn phần `PENDING` (BR-HT-10). Tiền rời túi vẫn chỉ khi Chủ `confirm_refund`. | `Refund.created_by` cho phép `NULL` (= Hệ thống) — migration §2.5 |
| 🟡 D2 | Đồng hồ 30' của Quản lý tính cả ngoài giờ? | **Giờ thật** (không trừ ngoài giờ làm). | Job so `escalated_at + D ≤ now`, không đọc `CSKH_WORKING_HOURS` |
| 🟡 D3 | "Khách muốn huỷ/đổi" có tự huỷ sau 30'? | **Không.** Chỉ `UNREACHABLE`/`WRONG_NUMBER` mới có hạn tự huỷ. | `decide_deadline = null` khi `escalation_reason ∈ {WANT_CANCEL, WANT_CHANGE}` |
| 🟡 D4 | Nhắc việc "gọi báo hoàn" cho ai? | **Người đã gọi đơn đó (trong 7 ngày) + Quản lý + Chủ.** CSKH khác thấy dòng đã che. | Phạm vi BR-GH-18 **không** mở rộng cho `REFUND_CALL` |
| 🟡 D5 | Số tài khoản nhận hoàn đi đường nào? | **Hệ thống không lưu STK ở bất kỳ đâu.** Chủ lấy STK trực tiếp từ khách lúc chuyển khoản (Chủ gọi số của đơn, hoặc CSKH chuyển máy cho Chủ); hệ thống chỉ lưu `bank_txn_ref` khi xác nhận (BR-HT-03 có sẵn). Không dùng Zalo/tin nhắn cá nhân để chuyển STK. | Ghi chú cuộc gọi chặn chuỗi ≥ 9 chữ số (BR-GH-19); màn nhắc việc có câu cố định. Không thêm field. |
| 🟡 D7 | S18/S20/S21 làm ngay sau Lô 2? | **Để backlog** (hồ sơ `2026-09-24-erp-console-noi-that`). | Phiếu READY tới NV giao bằng cách Quản lý gán qua Admin như hiện nay |
| 🟡 Q-C17 | Kiểm kê khi còn hàng "đã trừ sổ, chưa soạn" | **Không code trong hồ sơ này.** Quy định vận hành: không kiểm kê lô còn phiếu `CONFIRMING/PREPARING/READY` tham chiếu; đề xuất story riêng P-09 hiện cột "đã bán chưa xuất" theo lô. | Rủi ro ghi ở §10 |
| 🟡 T-1 | Kiểm vùng giao khi đổi địa chỉ (BR-BH-12) | **Không kiểm** ở V1 (tính năng vùng giao chưa có). | CS-12 chỉ kiểm rỗng/độ dài |
| 🟡 T-2 | Tìm theo SĐT | **Khớp đủ số** (≥ 9 chữ số sau chuẩn hoá) hoặc **mã đơn khớp đúng**; không tìm theo một phần SĐT. | Chặn dò danh sách khách |

## 0c. Chỗ contract khác bản PO (Tech Lead chốt — FE và QA bám bản này)

| Chỗ | `02-stories.md` | Chốt ở đây | Lý do |
|---|---|---|---|
| Dấu `/` cuối | `/api/cskh/queue/31/calls` | **Có `/` cuối** cho mọi path mới (`…/calls/`) | Router DRF; giống endpoint hiện có |
| Trang in | `/deliveries/31/label` | **`/print/label/?note=31&print_no=1`** và **`/print/pick-sheet/?note=31`** | Static export không có route động `[id]`; trang in cần không có Shell |
| `/api/shop/config/` | endpoint mới | **`GET /api/public/site-info/`** khoá `cskh_notice` | Trùng GL-01; một endpoint cấu hình công khai |
| Tra đơn Shop `fulfilment` | khoá mới | **Bỏ.** Dùng `delivery.status` (đã có). Chỉ thêm **một** khoá `cancel_notice`. `status_label` đổi câu khi phiếu `CONFIRMING`. | Ít khoá công khai hơn |
| CS-01-AC4 `/api/sales/customers/{id}/` với `cskh` | 404 | **403** (nhóm `cskh` không có `sales.view_customer`) | Thu tối thiểu: CSKH không cần hồ sơ khách (địa chỉ mặc định, ghi chú). Không lộ dữ liệu ở cả hai cách |
| X-AC6 PATCH phiếu giao | 405 | **Giữ S3-AC3**: `PATCH /api/delivery/notes/{id}/` chỉ sửa được `note`; mọi field mới nằm trong `locked_fields` → 400 `BR-PQ-14`. `CustomerCall`, `LabelPrint` không có endpoint sửa/xoá → 405/404. | Không lật story đã nghiệm thu (S3) |
| `label.needs_void` | số | `label: {"printed", "valid_print_no", "needs_void", "to_void": [1]}` | FE cần biết lần in nào phải huỷ |
| `decide_deadline` | trường lưu | **Tính lúc đọc** (`escalated_at + D`), `null` khi không tự huỷ | §0 #4 |
| `POST /status` phiếu giao | trả `{"status","already"}` | Trả **đủ body phiếu** như hiện nay **+ `already`** | Không phá test S19/S14 đang có |
| 409 | `CLAIMED`, `STALE_STATE` ở `/api/cskh/*` | 409 cho `/api/cskh/*`; **400** `STALE_STATE` cho `POST /api/delivery/notes/{id}/status/` (giữ đúng S19) | Theo từng story |

---

## 1. Kiến trúc & máy trạng thái

### 1.1 Luồng dữ liệu
```
IPN / Chủ xác nhận tay / hàng chờ lệch
  └─► payments.services.issue_invoice (KHÔNG đổi: trừ kho, doanh thu, đơn PROCESSING)
        └─► post_save(SalesInvoice) ─► delivery.signals ─► delivery.cskh.services.start_confirmation(invoice)
              = create_delivery_note(status=CONFIRMING) + ConfirmationTask(state=PENDING)   [1 transaction]

CSKH (ERP /cskh/) ─► /api/cskh/queue/…  ─► delivery.cskh.services (claim, record_call, change_recipient, unconfirm)
Quản lý/Chủ       ─► /api/cskh/queue/{id}/decide/ ─► delivery.cskh.services.decide
                                                        └─ CANCEL ─► sales.orders.services.cancel_paid_order
Cloud Scheduler */5 ─► Cloud Run Job `manage.py process_cskh_deadlines`
                          ├─ escalate_expired_windows(now)
                          └─ auto_cancel_overdue(now)  [chỉ khi CSKH_AUTO_CANCEL_ENABLED]
                               ├─ sales.orders.services.cancel_paid_order(actor=None, reason_code=UNREACHABLE_AUTO)
                               └─ sales.refunds.services.create_invoice_refund(actor=None, request_id=uuid5)
NV kho (ERP /deliveries/) ─► /api/delivery/notes/… (list, detail, status, label, label/print, label/void, lookup)
                              └─ trang /print/label/?note&print_no → window.print()
Khách (Shop) ─► /api/shop/orders/<mã>/?phone_last4 (thêm cancel_notice) · /api/public/site-info/ (cskh_notice)
```

### 1.2 Nơi đặt code (bám module hiện có, không di chuyển file cũ)

| Việc | File |
|---|---|
| Model mới + field mới | `backend/apps/delivery/models.py` (giữ file phẳng; thêm 3 model, Lô 5 thêm `CallScript`) |
| Nghiệp vụ gọi/quyết định/job | `backend/apps/delivery/cskh/services.py` (mới) |
| Phạm vi dữ liệu cá nhân (Q dùng chung) | `backend/apps/delivery/cskh/scope.py` (mới) |
| API hàng chờ CSKH | `backend/apps/delivery/cskh/api.py`, `serializers.py` (mới) |
| Nghiệp vụ tem | `backend/apps/delivery/labels/services.py` (mới); action đặt trên `DeliveryNoteViewSet` (`delivery/api.py`) |
| Soạn hàng (from_status, already, pack perm) | `backend/apps/delivery/services.py` (`advance_status`), `delivery/api.py` |
| Job | `backend/apps/delivery/management/commands/process_cskh_deadlines.py`, `check_cskh_job_health.py` (mới) |
| Tiện ích PII | `backend/apps/common/pii.py` (mới): `mask_phone`, `normalize_phone`, `has_long_digit_run` |
| Huỷ đơn: lý do mới, `CONFIRMING` hoàn kho, đóng task, đổi địa chỉ | `backend/apps/sales/orders/services.py` |
| Phạm vi đơn cho `cskh` | `backend/apps/sales/orders/api.py` (`get_queryset`) |
| Tra đơn Shop + site-info | `backend/apps/sales/orders/shop_api.py`, `backend/apps/common/site_info_api.py` (mới nếu GL-01 chưa có) |
| "Cần chú ý" | `backend/apps/reports/attention_api.py` (mới, cạnh `dashboard_api.py`) |
| Me / nhãn nhóm / nhãn quyền | `backend/apps/accounts/auth/services.py` |
| Route | `backend/config/api_urls.py` |

Module gọi module khác **qua services**: `delivery.cskh.services` → `sales.orders.services.cancel_paid_order`,
`sales.orders.services.update_delivery_address`, `sales.refunds.services.create_invoice_refund`;
`sales.orders.services.cancel_paid_order` → `delivery.cskh.services.close_task_on_cancel` (import **trong hàm** để tránh vòng
import `sales ↔ delivery`).

### 1.3 Máy trạng thái phiếu giao (`DeliveryNote.status`)
```
                       confirm (CSKH) / decide DELIVER (QL)
 hoá đơn ISSUED ─► CONFIRMING ────────────────────────────► PREPARING ──pack──► READY ──► DELIVERING ──► COMPLETED
                      ▲   │  ◄──── unconfirm (chưa in tem) ────┘                              └──► FAILED ──► DELIVERING
                      │   └── cancel_paid_order (QL tay / Hệ thống tự huỷ) ──► CANCELLED
                      └── (không có cạnh nào khác đi vào CONFIRMING)
```
- `ALLOWED_TRANSITIONS[CONFIRMING] = set()` cho `advance_status`: mọi `POST …/status/` trên phiếu `CONFIRMING` → 400
  `BR-GH-11` "Chưa xác nhận với khách". Chỉ `delivery.cskh.services` đổi `CONFIRMING ↔ PREPARING`.
- `cancel_paid_order`: thêm `CONFIRMING` vào `_STOCK_STILL_IN_WAREHOUSE` (hàng còn ở kho → hoàn kho đúng lô gốc, CS-04-AC5).
- `CANCELLED` qua `advance_status` → 400 `BR-GH-07` (hiện đang là thông điệp chung — sửa để có mã).

### 1.4 Máy trạng thái hàng chờ gọi (`ConfirmationTask.state`)
```
PENDING ──UNREACHABLE (chưa đủ N, còn trong W)──► PENDING (attempts+1)
PENDING|CALLBACK ──CALLBACK(callback_at>now)──► CALLBACK (attempts=0, xoá cửa sổ)
PENDING|CALLBACK ──UNREACHABLE (lần thứ N, hoặc now ≥ first+W)──► ESCALATED[UNREACHABLE]     (có hạn tự huỷ)
PENDING|CALLBACK ──WRONG_NUMBER──► ESCALATED[WRONG_NUMBER]                                  (có hạn tự huỷ)
PENDING|CALLBACK ──WANT_CANCEL|WANT_CHANGE──► ESCALATED[WANT_*]                             (KHÔNG hạn — D3)
PENDING|CALLBACK|ESCALATED ──CONFIRMED|CONFIRMED_CHANGED──► DONE   + phiếu → PREPARING
job:  PENDING (attempts≥1, first_unreachable_at + W ≤ now) ──► ESCALATED[UNREACHABLE]
ESCALATED ──decide DELIVER_WITHOUT_CONFIRM──► DONE + phiếu → PREPARING (confirm_skipped)
ESCALATED ──decide EXTEND(until)──► CALLBACK (callback_at=until, attempts=0)
ESCALATED ──decide CANCEL──► DONE (đơn + phiếu CANCELLED qua cancel_paid_order)
job:  ESCALATED[UNREACHABLE|WRONG_NUMBER], escalated_at + D ≤ now, cờ bật, không bị chặn
          ──► REFUND_CALL (đơn/phiếu CANCELLED, phiếu hoàn PENDING, attempts=0)
          (lô đã CLOSED → giữ ESCALATED, auto_cancel_blocked_code="BR-LO-05")
REFUND_CALL ──NOTIFIED──► DONE ;  ──UNREACHABLE──► REFUND_CALL (attempts+1, không hành động tự động)
mọi state mở ──(Quản lý huỷ đơn qua S14)──► DONE        [close_task_on_cancel]
DONE (do CONFIRMED, phiếu PREPARING, chưa có LabelPrint) ──unconfirm──► PENDING + phiếu → CONFIRMING
```
- Kết quả không hợp lệ với state hiện tại (vd `NOTIFIED` khi `PENDING`, `CONFIRMED` khi phiếu đã `PREPARING`) → 409
  `STALE_STATE` kèm `current_status`, `confirm_state`.
- `UNREACHABLE` khi `attempts ≥ 1` và `now < last_unreachable_at + M` → 400 `BR-GH-13` (CS-07-AC2). Luật M **không** áp cho
  `REFUND_CALL`.
- Mỗi lần ghi thành công **xoá khoá mềm** (`claimed_by = NULL`).

### 1.5 Khoá dòng và chống tranh chấp (CS-06-AC3, CS-08-AC6)
**Thứ tự khoá cố định: `SalesOrder` → `DeliveryNote` → `ConfirmationTask`.** Hàm nào không cần khoá tầng trước thì bỏ qua,
nhưng không bao giờ khoá tầng trước **sau** tầng sau.
- `record_call`, `change_recipient`, `unconfirm`: khoá `DeliveryNote` rồi `ConfirmationTask`, đọc lại trạng thái sau khoá.
- `decide`, `auto_cancel_overdue`: khoá `SalesOrder` → `DeliveryNote` → `ConfirmationTask`, đọc lại (task còn `ESCALATED`,
  phiếu còn `CONFIRMING`, đơn còn `PROCESSING`, với job: hạn đã qua), rồi mới gọi `cancel_paid_order` **trong cùng
  transaction** (hàm này khoá lại cùng dòng — không deadlock vì cùng transaction).
- `claim`: chỉ khoá `ConfirmationTask`.
- Postgres: `select_for_update(of=("self",))` khi queryset có `select_related` nullable (tránh lỗi "FOR UPDATE cannot be
  applied to the nullable side of an outer join").
- Bên thua: job → bỏ qua dòng (không lỗi, không AuditLog); API → 409 `STALE_STATE`.

### 1.6 Chống bấm lại / mạng rớt
| Thao tác | Khoá chống trùng | Trả khi trùng |
|---|---|---|
| `POST …/calls/` | `request_id` UUID (unique trên `CustomerCall`) | 200 `duplicate: true`, cùng `call_id`; khác phiếu → 400 |
| `POST …/label/print/` | `request_id` UUID (unique trên `LabelPrint`) | 200 `duplicate: true`, cùng `print_no` |
| `POST …/label/void/` | tự nhiên (đã `voided_at`) | 200 `already: true`, không AuditLog |
| `POST /api/delivery/notes/{id}/status/` | `from_status` | trạng thái hiện tại = `to_status` → 200 `already: true`, không AuditLog |
| `POST …/recipient/` | tự nhiên (so giá trị) | giá trị không đổi → `changed: []`, không AuditLog, không vô hiệu tem |
| Tự huỷ + phiếu hoàn | khoá dòng + `request_id = uuid5(NAMESPACE_URL, "caveve:auto-cancel:<order.pk>")` | job chạy lại không làm gì |

---

## 2. Model & migration

### 2.1 `DeliveryNote` (SỬA — chỉ thêm)
| Field | Kiểu | Ghi chú |
|---|---|---|
| `status` | thêm choice `CONFIRMING = "CONFIRMING", "Chờ xác nhận"` | `max_length=12` đủ; **default giữ `PREPARING`** |
| `confirmed_at` | DateTime null | lúc sang `PREPARING` qua xác nhận hoặc Quản lý bỏ qua |
| `confirmed_by` | FK User `PROTECT` null, `related_name="+"` | |
| `confirm_skipped` | Bool default False | Quản lý chọn "giao không cần xác nhận" (thước đo 1) |
| `recipient_name` | Char(200) blank | **PII mới** (Q-C11 Duy duyệt). Người nhận hộ; rỗng = khách đặt |
| `recipient_phone` | Char(20) blank | **PII mới**. Chuẩn hoá `0xxxxxxxxx`. `SalesOrder.phone` **không đổi** |
| `Meta.permissions` | `confirm_with_customer`, `change_recipient`, `decide_unconfirmed`, `pack_deliverynote`, `print_label` | §3.1 |

`DeliveryNoteViewSet.locked_fields` thêm `confirmed_at, confirmed_by, confirm_skipped, recipient_name, recipient_phone`.
`DeliveryNoteAdmin`: `locked_fields` thêm `confirmed_at, confirmed_by, confirm_skipped` (không PII); **`exclude =
("recipient_name", "recipient_phone")`** — không đưa vào `locked_fields` vì `admin_edit` chép giá trị cũ/mới vào AuditLog.

### 2.2 `ConfirmationTask` (MỚI) — "mục chờ gọi", 1–1 với phiếu
| Field | Kiểu | Ghi chú |
|---|---|---|
| `note` | OneToOne `DeliveryNote` `PROTECT`, `related_name="confirmation"` | |
| `state` | Char(12) choices `PENDING, CALLBACK, ESCALATED, REFUND_CALL, DONE`, `db_index` | API trả `confirm_state = null` khi `DONE` |
| `escalation_reason` | Char(16) blank, choices `UNREACHABLE, WRONG_NUMBER, WANT_CANCEL, WANT_CHANGE` | |
| `attempts` | PositiveSmallInt 0 | lần "không liên lạc được" (hoặc lần gọi báo hoàn khi `REFUND_CALL`) |
| `first_unreachable_at`, `last_unreachable_at` | DateTime null | cửa sổ W, khoảng M |
| `callback_at` | DateTime null | |
| `escalated_at` | DateTime null, `db_index` | gốc tính hạn Quản lý |
| `auto_cancel_blocked_code` | Char(16) blank | `"BR-LO-05"` khi lô đã chốt (CS-08-AC7) |
| `auto_cancelled_at` | DateTime null | có giá trị ⇔ Hệ thống tự huỷ |
| `refund` | FK `sales.Refund` `PROTECT` null | phiếu hoàn tự lập (REFUND_CALL) |
| `claimed_by` | FK User `PROTECT` null, `related_name="+"` | khoá mềm |
| `claimed_until` | DateTime null | |
| `created_at`, `updated_at` | auto | |
| Meta | `default_permissions = ()`; index `(state, escalated_at)` | quyền đi bằng Tầng 2 §3.1 |

`__str__` = `f"Chờ gọi {self.note_id}"` — **không** có tên/SĐT (AuditLog `object_repr` lấy từ đây).

### 2.3 `CustomerCall` (MỚI) — append-only
| Field | Kiểu | Ghi chú |
|---|---|---|
| `note` | FK `DeliveryNote` `PROTECT`, `related_name="calls"` | |
| `result` | Char(20) choices `CONFIRMED, CONFIRMED_CHANGED, UNREACHABLE, WRONG_NUMBER, CALLBACK, WANT_CHANGE, WANT_CANCEL, NOTIFIED` | nhãn tiếng Việt ở `get_result_display` |
| `note_text` | Char(200) blank | API tên `note`. **PII tiềm ẩn** — chặn ≥ 9 chữ số liên tiếp; không log; không vào AuditLog/AI |
| `callback_at` | DateTime null | |
| `created_by` | FK User `PROTECT` (bắt buộc) | người gọi thật (BR-GH-12) |
| `created_at` | auto_now_add, `db_index` | |
| `request_id` | UUID unique null | |
| Meta | `default_permissions = ()`; index `(created_by, created_at)` | phục vụ phạm vi "mình đã gọi trong X ngày" |

Không có endpoint sửa/xoá. Ngoại lệ duy nhất cho append-only: quy trình ẩn danh hoá theo yêu cầu của khách (sau này) được
ghi rỗng `note_text`. `__str__` = `f"Cuộc gọi #{pk} · {result}"`.

### 2.4 `LabelPrint` (MỚI) — lượt in tem
| Field | Kiểu | Ghi chú |
|---|---|---|
| `note` | FK `DeliveryNote` `PROTECT`, `related_name="label_prints"` | |
| `print_no` | PositiveSmallInt | `UniqueConstraint(note, print_no)` |
| `reason` | Char(16) choices `FIRST, REPRINT, ADDRESS_CHANGED` | dấu "IN LẠI – lần n" / "IN LẠI – ĐỔI ĐỊA CHỈ" |
| `printed_by` | FK User `PROTECT` | |
| `printed_at` | auto_now_add | |
| `request_id` | UUID unique null | |
| `superseded_at` | DateTime null | đổi thông tin nhận sau khi in → tem hết hiệu lực |
| `voided_at`, `voided_by` | DateTime null, FK User `PROTECT` null | "Đã huỷ tem giấy" (BR-GH-17) |
| Meta | `default_permissions = ()` | |

**Không lưu nội dung tem** (tính lúc in từ đơn). Tem hiệu lực (`valid_print_no`) = `print_no` lớn nhất có `superseded_at IS
NULL`, và phiếu không `CANCELLED`. Tem cần huỷ = mọi lượt `voided_at IS NULL` và không phải tem hiệu lực.

### 2.5 `Refund.created_by` (SỬA — nới ràng buộc)
`null=True, blank=True` (`NULL` = Hệ thống, BR-HT-10, D1). FE `erp-console` kiểu `created_by: number | null`; hiển thị
"Hệ thống". `timeline.py` đã xử lý `actor_display(None)`.

### 2.6 `CallScript` (MỚI, Lô 5 — CS-18)
`situation` Char(16) choices `FIRST_ORDER, RETURNING, COMBO, GENERAL` (unique), `content` Text (≤ 2.000, kiểm ở service),
`is_active` Bool, `updated_by` FK User `PROTECT`, `updated_at` auto. Quyền T1 mặc định `view/add/change_callscript`;
`default_permissions = ("view", "add", "change")` (không xoá — tắt bằng `is_active`).

### 2.7 Danh sách migration (sinh bằng `makemigrations`, **đọc file sinh ra**; số thứ tự theo `main` lúc làm)
| Lô | Migration | Nội dung |
|---|---|---|
| 1 | `delivery/0004_cskh_confirmation` | AlterField `status` (choice mới); AddField 5 field §2.1; AlterModelOptions `permissions`; CreateModel `ConfirmationTask`, `CustomerCall`, `LabelPrint` (schema cho Lô 1–4 đi một lần) |
| 1 | `accounts/00xx_seed_group_cskh` (RunPython, theo mẫu `0006`) | `create_permissions(delivery)`; `Group.get_or_create("cskh")`; `permissions.add` (không `set`) theo bảng §3.1 cho `cskh`, `quan_ly`, `nv_kho`, `chu`; `reverse` gỡ đúng các quyền đã thêm + xoá Group `cskh`. Chạy 2 lần không đổi gì (CS-01-AC1) |
| 3 | `sales/00xx_refund_created_by_nullable` | AlterField `Refund.created_by` null |
| 5 | `delivery/00xx_callscript` + `accounts/00xx_grant_callscript` | CreateModel `CallScript`; cấp `view/add/change_callscript` cho `chu`, `view_callscript` cho `quan_ly`, `cskh` |

Không data migration nào đụng phiếu giao/đơn cũ (CS-04-AC7). Lưu ý `chu` **không** tự có quyền của model/permission mới
(0002 gán lúc migrate) → migration phải cấp tường minh.

---

## 3. Quyền, Group `cskh`, phạm vi dữ liệu cá nhân

### 3.1 Bảng quyền
| Quyền | Tầng | `chu` | `quan_ly` | `nv_kho` | `nv_giao` | `cskh` |
|---|---|---|---|---|---|---|
| `sales.view_salesorder`, `sales.view_salesorderline` | 1 (lọc T3) | có | có | có | có | **thêm** |
| `delivery.view_deliverynote` | 1 | có | có | có | có | — |
| `delivery.confirm_with_customer` ("Gọi xác nhận đơn") | 2 mới | thêm | thêm | — | — | thêm |
| `delivery.change_recipient` ("Đổi thông tin nhận hàng") | 2 mới | thêm | thêm | — | — | thêm |
| `delivery.decide_unconfirmed` ("Quyết định đơn không liên lạc được") | 2 mới | thêm | thêm | — | — | — |
| `delivery.pack_deliverynote` ("Đóng gói phiếu giao") | 2 mới | thêm | thêm | thêm | — | — |
| `delivery.print_label` ("In / huỷ tem giao") | 2 mới | thêm | thêm | thêm | — | — |
| `delivery.*_callscript` (Lô 5) | 1 | view/add/change | view | — | — | view |

Không cấp cho `cskh`: `sales.view_customer`, `delivery.view_deliverynote`, `sales.view_refund`, `sales.view_salesinvoice`,
`reports.view_dashboard`, `inventory.*`, mọi quyền tiền. `accounts/auth/services.py`: `ROLE_ORDER` thêm `"cskh"` (cuối),
`GROUP_LABELS["cskh"] = "CSKH"`, `CAPABILITY_LABELS` thêm 5 quyền mới (test `test_s47_moi_quyen_meta_permissions_deu_co_nhan`
đòi), `home_for`: nhóm đúng bằng `{"cskh"}` → `"cskh-queue"`.

### 3.2 Phạm vi dòng (Tầng 3) — `delivery/cskh/scope.py`
```python
OPEN_CALL_STATES = ("PENDING", "CALLBACK", "ESCALATED")

def cskh_note_q(user, *, now=None, prefix=""):
    """Q trên DeliveryNote: phiếu CSKH được thấy đủ tên/SĐT/địa chỉ (BR-GH-18)."""
    now = now or timezone.now()
    since = now - timedelta(days=settings.CSKH_PII_RECENT_DAYS)
    p = prefix
    return (Q(**{f"{p}status": "CONFIRMING", f"{p}confirmation__state__in": OPEN_CALL_STATES})
            | Q(**{f"{p}pk__in": CustomerCall.objects.filter(created_by=user, created_at__gte=since)
                                                     .values("note_id")}))

def is_cskh(user) -> bool: ...                      # user.groups.filter(name="cskh").exists()
def note_in_cskh_scope(user, note) -> bool: ...     # dùng cho từng dòng (in_scope)
```
Áp vào (điều kiện chung: `has_full_delivery_scope(user)` → không lọc; ngược lại hợp các phạm vi user có):
| Nơi | Lọc |
|---|---|
| `SalesOrderViewSet.get_queryset` | `Q(invoice__delivery_notes__assigned_to=user)` **∪** (nếu `is_cskh`) `Exists(DeliveryNote.filter(sales_invoice__sales_order=OuterRef("pk")).filter(cskh_note_q(user)))` — dùng `Exists`, không join nhiều tầng + `distinct` |
| `CustomerViewSet` | **không đổi** (`cskh` không có `view_customer` → 403 trước khi tới queryset) |
| `DeliveryNoteViewSet` | không đổi (`cskh` không có `view_deliverynote` → 403) |
| `/api/cskh/queue/` list | mọi task `PENDING/CALLBACK/ESCALATED` (luôn trong phạm vi) + `REFUND_CALL` (dòng ngoài phạm vi thì **che**, §3.3) |
| `/api/cskh/queue/{id}/` và mọi action | Chu/QL: mọi task. `cskh`: `note_in_cskh_scope` sai → **404** |

### 3.3 Serializer — liệt kê field tường minh, tách theo phạm vi
- `CskhQueueItemSerializer.to_representation`: tính `in_scope` một lần; **trong phạm vi** mới thêm `customer_name`, `phone`,
  `address`, `recipient_name`, `recipient_phone`; ngoài phạm vi chỉ thêm `phone_masked` (`mask_phone`: giữ 2 số đầu + 3 số
  cuối → `09xx xxx 123`). Không dùng `fields="__all__"`, không `SerializerMethodField` trả nguyên object.
- Không serializer nào mới trả khoá giá vốn (`unit_cost`, `purchase_rate`, `landed_unit_cost`, `rate`, `cost`, `profit`,
  `margin`) hay đơn giá dòng. Dòng hàng chỉ `item_name`, `qty_kg`, `batch_id`, `expiry_date`.
- Mọi response có PII của `/api/cskh/*` và `…/label/` thêm header **`Cache-Control: no-store`** (mixin `NoStoreMixin` ở
  `apps/common/api.py`, đặt trong `finalize_response`).

---

## 4. Contract API BE↔FE

Quy ước chung: gốc `/api/`, `Authorization: Token …`, lỗi `{"detail","code"}` (+ khoá phụ khi ghi rõ), phân trang
`StandardPagination` 20 dòng, tiền/kg là chuỗi, giờ ISO `+07:00`. `BusinessError` thêm thuộc tính tuỳ chọn `extra: dict` và
lớp con `ConflictError(http_status=409)`; `exception_handler` trộn `extra` vào body (chỉ mã/trạng thái, không PII).

### 4.1 Bảng endpoint
| Method + path | Lô / story | Quyền tối thiểu (T1 → T2 → T3) | Trả PII | AI |
|---|---|---|---|---|
| `GET /api/auth/me/` | 1 / CS-01 | đăng nhập | không | cấm (`/api/auth/`) |
| `GET /api/delivery/notes/` | 1 / CS-02 | `view_deliverynote` → — → NV giao chỉ phiếu của mình | tên, địa chỉ | đọc, lọc PII |
| `GET /api/delivery/notes/{id}/` | 1 / CS-03 | như trên | tên, địa chỉ | đọc, lọc PII |
| `POST /api/delivery/notes/{id}/status/` | 1 / CS-03 | đăng nhập (custom action) → `pack_deliverynote` khi `to_status=READY` → phạm vi phiếu | không | `required_perms=()` + kiểm trong thân |
| `GET /api/sales/orders/` · `{id}/` | 1 / CS-01 | `view_salesorder` → — → + phạm vi `cskh` | có | như hiện nay (lọc PII) |
| `GET /api/cskh/queue/` · `{note_id}/` | 2 / CS-05, CS-09 | đăng nhập → `confirm_with_customer` → §3.2 | **có** | **cấm** |
| `POST /api/cskh/queue/{note_id}/claim/` | 2 / CS-05 | `confirm_with_customer` + phạm vi | không | cấm |
| `POST /api/cskh/search/` | 2 / CS-05 | `confirm_with_customer`; throttle `cskh_search` | có (trong phạm vi) | cấm |
| `POST /api/cskh/queue/{note_id}/calls/` | 2 / CS-06, CS-07, CS-09 | `confirm_with_customer` + phạm vi | không | cấm |
| `POST /api/cskh/queue/{note_id}/unconfirm/` | 2 / CS-06 | `confirm_with_customer` + phạm vi + (người đã xác nhận hoặc có `decide_unconfirmed`) | không | cấm |
| `GET /api/delivery/notes/{id}/label/` | 2 / CS-11 | `view_deliverynote` → `print_label` | **có** (tên, địa chỉ, SĐT che) | **cấm** |
| `POST /api/delivery/notes/{id}/label/print/` | 2 / CS-11, CS-14 | `print_label` | không | cấm |
| `POST /api/cskh/queue/{note_id}/decide/` | 3 / CS-07, CS-13 | `decide_unconfirmed` | không | cấm |
| `GET /api/shop/orders/{mã}/?phone_last4=` | 3 / CS-10 | AllowAny + throttle (hồ sơ sửa lỗi bảo mật) | **không** | cấm (`/api/shop/`) |
| `GET /api/public/site-info/` | 3 / CS-10 | AllowAny, chỉ GET | không | cấm (`/api/public/`) |
| `POST /api/cskh/queue/{note_id}/recipient/` | 4 / CS-12 | `change_recipient` + phạm vi | không (nhận PII vào) | cấm |
| `POST /api/delivery/notes/{id}/label/void/` | 4 / CS-14 | `print_label` | không | cấm |
| `GET /api/dashboard/attention/` | 4 / CS-15 | có ít nhất 1 trong `confirm_with_customer`, `decide_unconfirmed`, `print_label`; khoá theo quyền | không | đọc |
| `GET /api/delivery/notes/lookup/?code=` | 5 / CS-17 | `view_deliverynote` → `print_label` | không | cấm |
| `GET/POST/PATCH /api/cskh/scripts/` | 5 / CS-18 | GET `view_callscript`; POST/PATCH `add/change_callscript` | không | cấm |

Không có endpoint kích job (CS-08-AC11): test assert `resolve()` không có path nào chứa `process_cskh`/`deadlines`, và mọi
token người dùng không làm được việc của job.

### 4.2 Lô 1 — CS-01, CS-02, CS-03
```
GET /api/auth/me/          (người chỉ thuộc cskh)
200 {"id": 12, "username": "cs1", "display_name": "CSKH Thử", "phone": "", "groups": ["cskh"],
     "permissions": ["delivery.change_recipient", "delivery.confirm_with_customer", "sales.view_salesorder", "sales.view_salesorderline"],
     "can_view_cost": false, "can_view_profit": false, "home": "cskh-queue",
     "group_labels": [{"code": "cskh", "label": "CSKH"}],
     "capabilities": [{"code": "delivery.confirm_with_customer", "label": "Gọi xác nhận đơn"},
                      {"code": "delivery.change_recipient", "label": "Đổi thông tin nhận hàng"}],
     "must_change_password": false}

GET /api/delivery/notes/?status=CONFIRMING,PREPARING,READY,DELIVERING,FAILED&page=1
GET /api/delivery/notes/?status=COMPLETED&completed_from=2026-09-28          // "Hoàn tất (hôm nay)", ngày giờ VN
200 {"count": 1, "next": null, "previous": null, "results": [
  {"id": 31, "code": "GH-HD-0001-AB12C", "status": "PREPARING", "status_label": "Soạn hàng",
   "sales_invoice": 7, "invoice_code": "HD-0001", "order": {"id": 101, "code": "DH-260928-0001"},
   "paid_at": "2026-09-28T08:05:00+07:00", "confirmed_at": "2026-09-28T08:20:00+07:00", "confirm_skipped": false,
   "assigned_to": null, "failed_attempts": 0, "note": "", "created_at": "2026-09-28T08:05:01+07:00", "completed_at": null,
   "lines_summary": "Tôm sú L1 2,000 kg · Mực lá 1,000 kg", "total_kg": "3.000",
   "label": {"printed": false, "valid_print_no": null, "needs_void": 0, "to_void": []},
   "customer_name": "Khách Thử A", "address": "Số 1 Đường Thử, P. Thử, Lâm Đồng",
   "available_actions": ["set_status:READY", "print_label"]}]}
```
- Sắp xếp: `CONFIRMING` theo `paid_at` tăng; `PREPARING` theo `confirmed_at` tăng (null trước — phiếu cũ trước deploy), rồi
  `created_at`; còn lại `-created_at`. `CANCELLED` không vào khi FE lọc nhóm hoạt động (giữ hành vi S14).
- `available_actions` phiếu `CONFIRMING` = `[]` (CS-02-AC3). `print_label` chỉ khi `PREPARING/READY` và có `print_label`;
  `reprint_label` khi đã in; `void_label` khi `to_void` không rỗng.
- Không trả SĐT ở list/detail phiếu giao (kho không cần). Không trả đơn giá, thành tiền dòng.
```
GET /api/delivery/notes/31/
200 {…như dòng list…, "lines": [
       {"item_name": "Tôm sú loại 1", "qty_kg": "2.000", "batch_id": "TOM-SU-1-260920-AB12C", "expiry_date": "2027-09-20"}],
     "recipient_name": null}
POST /api/delivery/notes/31/status/   {"to_status": "READY", "from_status": "PREPARING"}
200 {…body phiếu…, "status": "READY", "already": false}   |   200 {…, "status": "READY", "already": true}
400 {"code": "STALE_STATE", "detail": "Phiếu đang ở Đang giao, tải lại để xem.", "current_status": "DELIVERING"}
400 {"code": "BR-GH-11", "detail": "Chưa xác nhận với khách, chưa soạn được."}
400 {"code": "BR-GH-07", "detail": "Đơn đã huỷ, không soạn."}
400 {"code": "BR-GH-05", "detail": "Không chuyển được từ Soạn hàng sang Hoàn tất."}
403 thiếu delivery.pack_deliverynote (to_status=READY)
```
- `lines` lấy từ `SalesInvoiceLineBatch` (dòng đã bán, lô chốt lúc đặt — BR-BH-11), `item_name` = `component_item.name`.
- `from_status` tuỳ chọn (tương thích test cũ). Có `from_status` và `current == to_status` → `already: true`, không ghi.
  Có `from_status` và `current != from_status` → 400 `STALE_STATE`.

### 4.3 Lô 2 — CS-04, CS-05, CS-06, CS-11
```
GET /api/cskh/queue/?state=PENDING|CALLBACK|ESCALATED|REFUND_CALL&page=1
    (không có state: PENDING + CALLBACK có callback_at ≤ now; chỉ phiếu CONFIRMING)
200 {"count": 1, "next": null, "previous": null, "results": [
  {"note_id": 31, "order_id": 101, "order_code": "DH-260928-0001", "note_status": "CONFIRMING",
   "paid_at": "2026-09-28T08:05:00+07:00",
   "confirm_state": "PENDING", "escalation_reason": null, "escalation_label": null,
   "attempts": 1, "max_attempts": 3, "next_call_after": "2026-09-28T09:10:00+07:00",
   "window_ends_at": "2026-09-28T09:30:00+07:00", "callback_at": null, "escalated_at": null,
   "decide_deadline": null, "auto_cancel_blocked": null,
   "claimed_by": null, "claimed_until": null,
   "lines_summary": "Tôm sú L1 2,000 kg", "total_kg": "2.000", "total_amount": "540000",
   "in_scope": true, "customer_name": "Khách Thử A", "phone": "0900000123",
   "address": "Số 1 Đường Thử, P. Thử, Lâm Đồng", "recipient_name": null, "recipient_phone": null}]}
```
- Sắp xếp: PENDING/CALLBACK theo `paid_at` tăng; ESCALATED theo `escalated_at` tăng; REFUND_CALL theo `auto_cancelled_at` tăng.
- `claimed_by` = `{"id": 13, "display_name": "CSKH Hai"}` khi còn hạn, ngược lại `null`.
```
GET /api/cskh/queue/31/
200 {…như trên…, "calls": [
       {"id": 76, "at": "2026-09-28T09:00:00+07:00", "by": {"id": 12, "display_name": "CSKH Thử"},
        "result": "UNREACHABLE", "result_label": "Không nghe máy / thuê bao", "note": ""}],
     "available_actions": ["claim", "call:CONFIRMED", "call:UNREACHABLE", "call:WRONG_NUMBER", "call:CALLBACK",
                           "call:WANT_CHANGE", "call:WANT_CANCEL", "change_recipient"],
     "guidance": null}
POST /api/cskh/queue/31/claim/   {}
200 {"claimed_by": {"id": 12, "display_name": "CSKH Thử"}, "claimed_until": "2026-09-28T09:05:00+07:00"}
409 {"code": "CLAIMED", "detail": "Đơn đang được CSKH Hai xử lý tới 09:14.", "claimed_until": "2026-09-28T09:14:00+07:00"}
POST /api/cskh/search/   {"q": "0900000123"}                     // hoặc mã đơn; GET → 405
200 {"results": [
  {"note_id": 31, "order_code": "DH-260928-0001", "status_label": "Chờ xác nhận", "in_scope": true,
   "customer_name": "Khách Thử A", "phone": "0900000123"},
  {"note_id": 12, "order_code": "DH-260920-0007", "status_label": "Đang giao", "in_scope": false,
   "phone_masked": "09xx xxx 123"}]}
400 {"code": "INVALID_QUERY", "detail": "Nhập đủ số điện thoại hoặc đúng mã đơn."}
```
- `calls[].note` chỉ có khi phiếu trong phạm vi (luôn đúng ở detail vì ngoài phạm vi là 404). `calls` mới nhất trước.
- `available_actions` theo state + quyền + khoá mềm (người khác đang giữ → chỉ `[]`); `change_recipient` chỉ khi có quyền và
  phiếu `CONFIRMING/PREPARING`; `decide:*` khi `ESCALATED` và có `decide_unconfirmed` (Lô 3).
- Search: `q` chuẩn hoá bỏ khoảng trắng/`.`/`-`, `+84`→`0`; ≥ 9 chữ số → khớp **đúng** chữ số của `SalesOrder.phone` hoặc
  `DeliveryNote.recipient_phone`; ngược lại khớp **đúng** mã đơn (không phân biệt hoa thường); còn lại 400. Tối đa 20 dòng,
  mới nhất trước. Throttle `cskh_search` (khoá theo user id) mức `THROTTLE_CSKH_SEARCH` mặc định `30/min`, dùng
  `SettingsRateThrottle` của hồ sơ sửa lỗi bảo mật. Không log `q`.
```
POST /api/cskh/queue/31/calls/
{"result": "CONFIRMED", "note": "Giao sau 17h", "callback_at": null, "request_id": "0b6e1c1e-0000-4000-8000-000000000001"}
201 {"call_id": 77, "note_status": "PREPARING", "confirm_state": null, "attempts": 0, "duplicate": false}
200 {"call_id": 77, "note_status": "PREPARING", "confirm_state": null, "attempts": 0, "duplicate": true}
409 {"code": "STALE_STATE", "detail": "Đơn vừa được xác nhận bởi người khác.", "current_status": "PREPARING", "confirm_state": null}
409 {"code": "CLAIMED", "detail": "Đơn đang được CSKH Hai xử lý tới 09:14.", "claimed_until": "…"}
400 {"code": "BR-GH-19", "detail": "Không ghi SĐT hay số tài khoản vào ghi chú."}
400 {"code": "BR-GH-13", "detail": "Chưa đủ 10 phút kể từ lần gọi trước."}
400 {"code": "BR-GH-07", "detail": "Đơn đã huỷ."}
400 {"code": "INVALID_INPUT", "detail": "Giờ hẹn gọi lại phải ở tương lai."}
POST /api/cskh/queue/31/unconfirm/   {"reason": "Bấm nhầm đơn"}
200 {"note_status": "CONFIRMING", "confirm_state": "PENDING"}
400 {"code": "BR-GH-16", "detail": "Tem đã in — nhờ Quản lý xử lý."}
```
- `result` Lô 2: mọi mã trừ `NOTIFIED`; hệ quả đầy đủ của `UNREACHABLE`/`WRONG_NUMBER` (đếm, cửa sổ, chuyển Quản lý) có từ
  Lô 2 vì cùng service (CS-07 BE nằm Lô 3 chỉ thêm `decide` + job). `note` ≤ 200 ký tự, bỏ `[\s.\-]` rồi tìm `\d{9,}` → 400.
- AuditLog: `delivery_confirmed` (CONFIRMED/CONFIRMED_CHANGED), `delivery_call_recorded` (các mã khác),
  `delivery_escalated`, `delivery_unconfirmed` — `changes` chỉ có mã (`{"result": "UNREACHABLE", "attempts": 2}`,
  `{"status": {"from": "CONFIRMING", "to": "PREPARING"}}`). **Không** chép `note`. `unconfirm.reason` vào `note` của
  AuditLog sau khi qua cùng bộ kiểm BR-GH-19.
```
GET /api/delivery/notes/31/label/                  // xem trước
GET /api/delivery/notes/31/label/?print_no=1       // trang in lấy đúng lần in
200 {"note_code": "GH-HD-0001-AB12C", "order_code": "DH-260928-0001", "print_no": 1, "next_print_no": 2,
     "is_reprint": false, "reprint_reason": null, "barcode_value": "GH-HD-0001-AB12C.1",
     "recipient_name": "Khách Thử A", "recipient_phone_masked": "09xx xxx 123",
     "address": "Số 1 Đường Thử, P. Thử, Lâm Đồng", "packages": "1/1", "total_kg": "3.000",
     "earliest_expiry": "2027-09-20", "paid_text": "ĐÃ THANH TOÁN – không thu thêm"}
400 {"code": "BR-GH-09", "detail": "Chưa xác nhận với khách, chưa in tem."}
400 {"code": "BR-GH-07", "detail": "Đơn đã huỷ, không in tem."}
400 {"code": "BR-GH-16", "detail": "Tem lần 1 không còn hiệu lực, dùng tem lần 2."}
POST /api/delivery/notes/31/label/print/   {"request_id": "0b6e1c1e-0000-4000-8000-000000000002"}
201 {"print_no": 1, "printed_at": "2026-09-28T08:30:00+07:00", "is_reprint": false, "duplicate": false}
200 {"print_no": 1, …, "duplicate": true}
```
- Không có khoá `total_amount`, `price`, `amount` trong JSON tem (CS-11-AC4). SĐT **chỉ** dạng che.
- `recipient_name`/`recipient_phone_masked` lấy người nhận hộ nếu có, ngược lại tên khách / `SalesOrder.phone`.
- AuditLog `label_printed` / `label_reprinted`: `changes={"print_no": n, "reason": "FIRST"}`.

### 4.4 Lô 3 — CS-07, CS-08, CS-09, CS-10
```
POST /api/cskh/queue/31/decide/
{"decision": "DELIVER_WITHOUT_CONFIRM", "reason": "Khách quen, địa chỉ đã giao 2 lần"}
{"decision": "EXTEND", "until": "2026-09-28T17:00:00+07:00", "reason": "Khách nhắn đang họp"}
{"decision": "CANCEL", "reason_code": "UNREACHABLE", "note": ""}     // reason_code ∈ UNREACHABLE | CUSTOMER_CHANGED_MIND | OTHER
200 {"note_status": "PREPARING", "confirm_state": null, "order_id": 101, "suggest_refund_amount": null}
200 {"note_status": "CONFIRMING", "confirm_state": "CALLBACK", "order_id": 101, "suggest_refund_amount": null}
200 {"note_status": "CANCELLED", "confirm_state": null, "order_id": 101, "suggest_refund_amount": "540000"}
409 {"code": "STALE_STATE", "detail": "Đơn đã được xử lý.", "current_status": "CANCELLED", "confirm_state": null}
400 {"code": "BR-GH-13", "detail": "Gia hạn tối đa 24 giờ."}
403 thiếu delivery.decide_unconfirmed
```
- `CANCEL`: thêm `"UNREACHABLE": "Không liên lạc được khách"` vào `CANCEL_REASON_LABELS` (người chọn được, cả ở S14). Mã
  `UNREACHABLE_AUTO` ("Hệ thống tự huỷ — không liên lạc được") nằm ở **bộ riêng** `SYSTEM_CANCEL_REASON_CODES`, API không nhận.
- FE sau `CANCEL` điều hướng `/orders/?order=101&open=refund` (chỉ id) → màn Đơn mở chi tiết + `RefundForm` điền sẵn
  `suggest_refund_amount` (CS-07-AC11). Không import chéo `features/orders` vào `features/cskh`.
- AuditLog `delivery_confirm_skipped`, `delivery_extended`, (`cancel_paid_order` có sẵn); `reason` vào `note` sau bộ kiểm
  BR-GH-19; `changes` chỉ có mã quyết định.
```
GET /api/cskh/queue/?state=REFUND_CALL
200 {"count": 2, "results": [
  {"note_id": 31, "order_id": 101, "order_code": "DH-260928-0001", "note_status": "CANCELLED",
   "confirm_state": "REFUND_CALL", "cancelled_at": "2026-09-28T09:56:00+07:00", "attempts": 0, "max_attempts": 3,
   "refund": {"id": 5, "amount": "540000", "status": "PENDING", "status_label": "Chờ Chủ chuyển",
              "deadline": "2026-10-28", "refunded_at": null},
   "in_scope": true, "customer_name": "Khách Thử A", "phone": "0900000123", "address": "Số 1 Đường Thử, P. Thử, Lâm Đồng"},
  {"note_id": 44, "order_code": "DH-260928-0009", "confirm_state": "REFUND_CALL", "cancelled_at": "…",
   "refund": {"id": 6, "amount": "320000", "status": "PENDING", "status_label": "Chờ Chủ chuyển", "deadline": "2026-10-28", "refunded_at": null},
   "in_scope": false, "phone_masked": "09xx xxx 456"}]}
GET /api/cskh/queue/31/   (REFUND_CALL)  → thêm "guidance": "Không ghi số tài khoản khách vào hệ thống. …"
POST /api/cskh/queue/31/calls/  {"result": "NOTIFIED" | "UNREACHABLE", "note": "", "request_id": "…"}
201 {"call_id": 90, "note_status": "CANCELLED", "confirm_state": null | "REFUND_CALL", "attempts": 0 | 1, "duplicate": false}
```
- `deadline` = ngày (giờ VN) của `refund.created_at` + `REFUND_DEADLINE_DAYS`. `refunded_at` = `confirmed_at` khi `REFUNDED`.
- `guidance` là câu cố định ở BE (D5): "Không ghi số tài khoản khách vào hệ thống. Chủ sẽ lấy số tài khoản trực tiếp từ khách
  khi chuyển khoản."
```
GET /api/shop/orders/DH-260928-0001/?phone_last4=0123
200 {"order_code": "DH-260928-0001", "status": "PROCESSING", "status_label": "Đã thanh toán – chờ vựa gọi xác nhận",
     "total_amount": "540000", "lines": [{"item_code": "TOM-SU-1", "name": "Tôm sú loại 1", "qty": "2.000", "amount": "540000"}],
     "delivery": {"status": "CONFIRMING", "status_label": "Chờ vựa gọi xác nhận"},
     "booked_expires_at": null, "cancel_notice": null}
200 {"order_code": "DH-260928-0001", "status": "CANCELLED", "status_label": "Đã huỷ", …,
     "delivery": {"status": "CANCELLED", "status_label": "Đã huỷ theo đơn"},
     "cancel_notice": {"reason_code": "UNREACHABLE_AUTO",
        "message": "<CHỜ legal-vn: Cá Về đã gọi số điện thoại đặt hàng 3 lần trong 30 phút nhưng không liên lạc được, nên đơn được huỷ tự động…>",
        "refund": {"amount": "540000", "status_label": "Đang chờ hoàn", "deadline": "2026-10-28", "refunded_at": null},
        "contact": "<SHOP_HOTLINE>"}}
```
- `cancel_notice` chỉ khi đơn `CANCELLED` và có hoá đơn; `reason_code` = `"UNREACHABLE_AUTO"` khi task có `auto_cancelled_at`,
  ngược lại `null` (câu chung "Đơn đã được huỷ theo yêu cầu/xử lý của vựa" — CS-10-AC5). `refund` = tổng phiếu hoàn không
  `FAILED`; `status_label` "Đã hoàn" khi mọi phiếu `REFUNDED`, "Đang chờ hoàn" khi còn `PENDING`, `null` khi chưa có phiếu.
- **Không** có khoá tên, SĐT, địa chỉ, người nhận hộ, ghi chú gọi (CS-10-AC6). Test S02-AC3 (hồ sơ sửa lỗi bảo mật, "đúng 7
  khoá") được **sửa có chủ đích** thành 8 khoá (thêm `cancel_notice`) — ghi trong `03-dev-notes.md`.
```
GET /api/public/site-info/      (AllowAny, chỉ GET, Cache-Control: public, max-age=300)
200 {"cskh_notice": {"enabled": true, "working_hours": "07:00-21:00", "max_attempts": 3, "window_minutes": 30,
                     "decision_minutes": 30, "auto_cancel_enabled": false, "refund_deadline_days": 30,
                     "hotline": "<SHOP_HOTLINE>"}}
```
- Nếu GL-01 (hồ sơ khung go-live) làm trước: chỉ **thêm** khoá `cskh_notice` vào view đó. Nếu CSKH làm trước: tạo view với
  **đúng một** khoá `cskh_notice`; GL-01 thêm `seller` sau. GL-04 dùng `cskh_notice.enabled`/`working_hours` thay cho
  `confirm_call_notice`/`confirm_call_hours` (điều phối viên báo PO hồ sơ go-live).
- `enabled` = `CSKH_NOTICE_ENABLED` (mặc định `1`); `auto_cancel_enabled` = `CSKH_AUTO_CANCEL_ENABLED` — FE chỉ hiện câu "có thể
  bị huỷ và hoàn đủ tiền" khi `true`.

### 4.5 Lô 4 — CS-12, CS-13, CS-14, CS-15
```
POST /api/cskh/queue/31/recipient/
{"delivery_address": "Số 2 Đường Thử, P. Thử, Lâm Đồng", "recipient_name": "Người Nhận Thử", "recipient_phone": "0900000456"}
200 {"changed": ["delivery_address", "recipient_name", "recipient_phone"], "label_invalidated": false}
400 {"code": "BR-GH-15", "detail": "Hàng đã soạn xong/đang đi giao — liên hệ Quản lý."}
400 {"code": "BR-BH-14", "detail": "Số điện thoại người nhận không hợp lệ."}
```
- Khoá nào không gửi thì không đổi; gửi `""` cho `recipient_name`/`recipient_phone` = xoá người nhận hộ (phải xoá cả hai).
  `delivery_address` rỗng → 400, > 500 ký tự → 400.
- `delivery_address` ghi đè `SalesOrder.delivery_address` qua `sales.orders.services.update_delivery_address(order, address)`
  (không giữ bản cũ — thu tối thiểu). `SalesOrder.phone`, `Customer.default_address` **không đổi**.
- Có đổi và đang có tem hiệu lực → `LabelPrint.superseded_at = now`, `label_invalidated: true`; lần in sau `reason=ADDRESS_CHANGED`.
- AuditLog `recipient_changed`: `changes={"fields": ["delivery_address", "recipient_name"]}` — **chỉ tên field**.
```
POST /api/cskh/queue/31/calls/  {"result": "WANT_CANCEL", "note": "Khách đổi ý", "request_id": "…"}
201 {"call_id": 81, "note_status": "CONFIRMING", "confirm_state": "ESCALATED", "attempts": 0, "duplicate": false}
   // escalation_label: "Khách muốn huỷ" | "Khách muốn đổi món – huỷ + hoàn + đặt lại"; decide_deadline = null
POST /api/delivery/notes/31/label/print/  {"request_id": "…"}   → 201 {"print_no": 2, "is_reprint": true, …}
POST /api/delivery/notes/31/label/void/   {"print_no": 1}
200 {"print_no": 1, "voided_at": "2026-09-28T10:00:00+07:00", "already": false}
400 {"code": "BR-GH-16", "detail": "Tem lần 2 đang có hiệu lực, không huỷ được."}
GET /api/dashboard/attention/
200 {"cskh_queue_waiting": 2, "cskh_escalated": 1, "cskh_auto_cancel_blocked": 0,
     "refund_calls_open": 1, "labels_not_printed": 1, "labels_to_void": 2}
```
- Khoá theo quyền (khoá không có quyền thì vắng mặt): `cskh_queue_waiting`, `refund_calls_open` ← `confirm_with_customer`;
  `cskh_escalated`, `cskh_auto_cancel_blocked` ← `decide_unconfirmed`; `labels_*` ← `print_label`. Không quyền nào → 403.
- `cskh_queue_waiting`: task `PENDING` (phiếu `CONFIRMING`), `attempts=0`, `paid_at ≤ now − CSKH_QUEUE_ALERT_MINUTES`.
  `labels_not_printed`: phiếu `PREPARING` không có `LabelPrint`, `confirmed_at ≤ now − LABEL_UNPRINTED_ALERT_MINUTES`.
  `labels_to_void`: số lượt in cần huỷ (§2.4). `cskh_escalated`: task `ESCALATED`. Chỉ trả **số đếm**.

### 4.6 Lô 5 — CS-16, CS-17, CS-18
```
GET /api/delivery/notes/lookup/?code=GH-HD-0001-AB12C.1
200 {"note_id": 31, "status": "PREPARING", "print_no": 1, "valid_print_no": 2, "warning": "BR-GH-16"}   // null | BR-GH-16 | BR-GH-07
404 {"detail": "Không tìm thấy phiếu."}
400 {"code": "INVALID_INPUT", "detail": "Mã tem không đúng định dạng."}          // regex ^GH-[A-Z0-9-]{3,40}\.\d{1,3}$
GET /api/cskh/scripts/
200 {"results": [{"situation": "FIRST_ORDER", "situation_label": "Khách mua lần đầu", "content": "…", "is_active": true}]}
POST /api/cskh/scripts/  {"situation": "FIRST_ORDER", "content": "…", "is_active": true}   // Chủ
PATCH /api/cskh/scripts/FIRST_ORDER/  {"is_active": false}
GET /api/cskh/queue/31/ → thêm "scripts": [{"situation": "FIRST_ORDER", "situation_label": "…", "content": "…"}]
```
- CS-16 (phiếu soạn) dùng `GET /api/delivery/notes/{id}/` — không API mới; trang `/print/pick-sheet/?note=31` **không** hiện
  `customer_name`, `address`, `recipient_*` dù JSON có.
- Chọn kịch bản: `FIRST_ORDER` nếu khách không có đơn `PROCESSING/COMPLETED` nào khác; `COMBO` nếu có dòng `bundle_snapshot`
  không rỗng; luôn kèm `GENERAL` nếu bật. Kịch bản không qua AI.
  Khách có đơn khác (không tính đơn đang gọi) ở `PROCESSING/COMPLETED` thì dùng `RETURNING` thay `FIRST_ORDER` (phần bù của quy tắc trên; Tech Lead chấp nhận 06/10).

### 4.7 FE — kiểu, mock, màn
| Module / route | Nội dung | Lô |
|---|---|---|
| `erp-console/shared/lib/nav.ts`, `groups.ts` | `GROUP.cskh`, `GROUP_LABEL.cskh = "CSKH"`, `PERM` mới; `Viewer.home` thêm `"cskh-queue"`; `homePath` → `/cskh/`; mục "Giao hàng" hết Placeholder (Lô 1); mục mới "Gọi xác nhận" `/cskh/` hiện khi có `delivery.confirm_with_customer` (Lô 2) | 1, 2 |
| `features/deliveries/` (mới) + `app/(console)/deliveries/page.tsx` | Bảng nhóm theo trạng thái (thẻ trên điện thoại), chi tiết phiếu, nút Đã đóng gói (`from_status`), In tem, In lại, Đã huỷ tem | 1, 2, 4 |
| `features/cskh/` (mới) + `app/(console)/cskh/page.tsx` | Hàng chờ (lọc 4 state), chi tiết (claim khi mở, `tel:`, nút kết quả ở nửa dưới màn hình), tìm (POST body), đổi người nhận, khối Quyết định, nhắc việc báo hoàn | 2, 3, 4 |
| `app/print/label/page.tsx`, `app/print/pick-sheet/page.tsx` (mới, ngoài `(console)`) | Trang in §6 | 2, 5 |
| `features/orders/labels.ts`, `types.ts`, `OrdersScreen.tsx` | `CONFIRMING`; `Refund.created_by: number | null` ("Hệ thống"); mở chi tiết + RefundForm từ `?order=&open=refund` | 2, 3 |
| `features/overview/components/AttentionBlock.tsx` | 6 khoá, lỗi riêng khối (CS-15-AC6) | 4 |
| `frontend/lib/api.ts`, `types.ts`, `mock.ts`, `app/shop/orders/OrderLookup.tsx`, `features/checkout/components/*` | `cancel_notice`, nhãn `CONFIRMING`, câu báo trước từ `site-info` | 3 |
- Mỗi hàm API mới có nhánh mock trong `features/<module>/mock.ts` (dữ liệu giả, phạm vi `cskh` mô phỏng `in_scope`).
- **Cấm** dùng `useDraft`/`localStorage`/`sessionStorage`/URL cho mọi dữ liệu cá nhân (form đổi người nhận, ghi chú gọi, hàng
  chờ). URL chỉ `note`, `order`, `print_no`, `open`, `state`. Không `console.*` payload.
- Nút có loading + chặn bấm đúp; `request_id` sinh **một lần** khi mở form/bấm, giữ trong state để gửi lại khi thử lại.

---

## 5. Job nền

### 5.1 `process_cskh_deadlines` (Lô 3)
```python
# apps/delivery/cskh/services.py
def escalate_expired_windows(*, now=None) -> int:
    """PENDING, attempts ≥ 1, first_unreachable_at + W ≤ now → ESCALATED[UNREACHABLE], escalated_at = now. Idempotent."""
def auto_cancel_overdue(*, now=None) -> dict:
    """Chỉ khi settings.CSKH_AUTO_CANCEL_ENABLED. ESCALATED[UNREACHABLE|WRONG_NUMBER], auto_cancel_blocked_code == "",
    escalated_at + D ≤ now → khoá đơn→phiếu→task, đọc lại, kiểm lô CLOSED (→ chặn BR-LO-05), cancel_paid_order(actor=None,
    reason="Không liên lạc được khách (Hệ thống tự huỷ)", reason_code="UNREACHABLE_AUTO"),
    create_invoice_refund(amount=refundable_amount(invoice), is_partial=False, actor=None,
                          reason="Tự huỷ: không liên lạc được khách (BR-HT-10)", request_id=uuid5(...)),
    task → REFUND_CALL (refund, auto_cancelled_at=now, attempts=0), record_audit("order_auto_cancelled", actor=None,
    obj=order, changes={"reason_code": "UNREACHABLE_AUTO", "refund_id": refund.pk}). Trả {"cancelled": n, "blocked": m}."""
```
- Mỗi dòng một `transaction.atomic()` riêng (lỗi một dòng không chặn dòng khác); lỗi bất ngờ → `logger.exception` **chỉ mã
  đơn** rồi tiếp. Logger `cangca.delivery.cskh`. Command in ra `Đã chuyển Quản lý n phiếu; tự huỷ m đơn; chặn k đơn.`
- Lô đã `CLOSED` (bất kỳ `SalesInvoiceLineBatch.batch.status == CLOSED`) → không huỷ, ghi `auto_cancel_blocked_code="BR-LO-05"`,
  AuditLog `order_auto_cancel_blocked` một lần (chỉ khi mã còn rỗng → idempotent).
- Doanh thu: không đảo lúc tự huỷ; giảm khi Chủ `confirm_refund` (báo cáo kỳ đã lọc `REFUNDED` theo `confirmed_at` —
  `reports/services.py:117`; CS-08-AC9 giữ nguyên hành vi).
- Cờ tắt: `escalate_expired_windows` **vẫn chạy** (đơn vẫn tới Quản lý); chỉ bước tự huỷ không chạy.

### 5.2 Hạ tầng (Duy làm lúc deploy — không phải việc dev)
- Cloud Run Job `cangca-cskh-deadlines` (+ `cangca-cskh-deadlines-staging`): `python manage.py process_cskh_deadlines`, image và
  env giống `cangca-ttl` (có `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DATABASE_URL`).
- Cloud Scheduler `*/5 * * * *`, múi giờ `Asia/Ho_Chi_Minh`, cùng service account với `cangca-ttl-trigger`.
- Giám sát: `manage.py check_cskh_job_health` → exit 1 khi (cờ bật và) còn task tự huỷ được quá `decide_deadline + 10'`
  (thước đo 2), hoặc task `PENDING` quá `first_unreachable_at + W + 10'`. Lịch chạy như `check_ttl_job_health`.
- Dev chỉ thêm command + ghi lệnh `gcloud` mẫu vào `03-dev-notes.md` (không chạy).

---

## 6. Tem 100×150 in từ trình duyệt (CS-11, CS-14, CS-16)

- Luồng: chi tiết phiếu → `POST …/label/print/` → `window.open("/print/label/?note=31&print_no=1")` (cùng tab trên điện thoại)
  → trang gọi `GET …/label/?print_no=1` → vẽ tem + QR → khi QR xong gọi `window.print()` một lần.
- Trang in nằm ở `app/print/…` (ngoài `(console)`, không Shell, không menu, không tab Trợ lý); dùng `AuthProvider` có sẵn ở
  root layout; chưa đăng nhập → `/login/?next=` (chỉ path, không dữ liệu). 403/400 → màn lỗi, không in.
- CSS: `<style>{"@page{size:100mm 150mm;margin:0}"}</style>` trong component (tránh giới hạn CSS module); khung `100mm×150mm`,
  `overflow:hidden`, địa chỉ dài tự thu cỡ chữ theo bậc (tối thiểu 9pt) và cắt 4 dòng có dấu "…" → luôn **1 trang**
  (CS-11-AC6). Mực đen trắng, không ảnh nền.
- Nội dung tem: mã phiếu, mã đơn, QR (giá trị `barcode_value` — không URL, không SĐT, không tên) + chữ mã dưới QR, người nhận,
  SĐT che, địa chỉ, `packages`, `total_kg`, HSD sớm nhất, `paid_text`, dấu "IN LẠI – lần n" / "IN LẠI – ĐỔI ĐỊA CHỈ". **Không**
  số tiền, giá, giá vốn. Chờ `legal-vn` về ghi nhãn hàng hoá (Q-C6) — nếu phải thêm trường thì thêm vào JSON `label` và AC trước
  khi lên production.
- QR: thư viện `qrcode` (đang dùng ở Shop) nạp bằng `next/dynamic`/`import()` trong trang in, sinh SVG **trên máy**, không gọi
  dịch vụ ngoài. Thêm `qrcode` + `@types/qrcode` vào `erp-console/package.json`.
- Không lưu dữ liệu tem vào storage, không đặt vào URL, không `console.log`. Hộp thoại in "Lưu PDF" là lựa chọn của người dùng —
  quy định vận hành: không lưu tem ra file (ghi vào hướng dẫn kho, BR-GH-17).
- Phiếu soạn (CS-16): `/print/pick-sheet/?note=31` từ `GET /api/delivery/notes/31/`, chỉ mã phiếu, dòng hàng, kg, mã lô, HSD.

---

## 7. Thông báo cho khách (BR-GH-21)

- Kênh V1: **trang tra đơn Shop** (`cancel_notice`) + **cuộc gọi của nhân viên** (nhắc việc `REFUND_CALL`) + **câu báo trước**
  ở bước đặt hàng/trang đặt xong (`cskh_notice`). Không SMS/Zalo/email (gửi PII cho bên thứ ba — chưa duyệt).
- Câu chữ ở BE `apps/sales/orders/customer_notices.py`: `AUTO_CANCEL_MESSAGE` (có chỗ điền `{max_attempts}`, `{window_minutes}`,
  `{refund_deadline_days}`), `MANUAL_CANCEL_MESSAGE`. FE Shop **không** viết cứng câu huỷ; câu báo trước dựng từ số của
  `cskh_notice` theo mẫu `frontend/features/checkout/…` (chữ mẫu cũng chờ `legal-vn`).
- Bản nháp hiện tại đánh dấu `# CHỜ legal-vn` trong code. **Không lên production** khi `legal-vn` chưa duyệt (NĐ 356/2025 —
  quyết định tự động bất lợi phải nêu lý do, số tiền hoàn, hạn hoàn, cách phản hồi). Cổng kỹ thuật: `CSKH_AUTO_CANCEL_ENABLED=0`
  trên production cho tới khi Duy bật.

---

## 8. Lệnh AI: `required_perms` và danh sách chặn

Hồ sơ AI (`2026-09-28-ai-digital-worker/02b` §2.5, §3) chưa hiện thực `AiDeclarable`. Để không vỡ và tự khớp khi AI Lô 2 vào:
- `CskhQueueViewSet`, `DeliveryNoteViewSet` khai **thuộc tính lớp** `required_perms: tuple = ()` (để `@action(required_perms=…)`
  không lỗi khi DRF khởi tạo view) và **vẫn** gọi `require_perm` trong thân action (lớp chặn thật hiện nay).
- Khai trên từng action ghi:
  | Action | `required_perms` |
  |---|---|
  | `cskh.queue.claim`, `calls`, `unconfirm` | `("delivery.confirm_with_customer",)` |
  | `cskh.queue.recipient` | `("delivery.change_recipient",)` |
  | `cskh.queue.decide` | `("delivery.decide_unconfirmed",)` |
  | `deliverynote.set_status` | `()` (quyền tuỳ `to_status`, kiểm trong thân) |
  | `deliverynote.label`, `label_print`, `label_void`, `lookup` | `("delivery.print_label",)` |
  | `cskh.scripts` create/update | `("delivery.add_callscript",)` / `("delivery.change_callscript",)` |
- **Việc cho AI Lô 2** (điều phối viên chuyển hồ sơ AI, không làm ở hồ sơ này): thêm tiền tố `/api/cskh/`, `/api/public/` vào
  "Cấm hẳn"; cấm path khớp `^/api/delivery/notes/\d+/label/`; thêm `recipient_name`, `recipient_phone`,
  `recipient_phone_masked`, `phone_masked` vào khoá PII lọc đầu ra; `note` của cuộc gọi đã thuộc "chữ tự do". Test quét
  registry của AI Lô 2 phải có fixture phiếu `CONFIRMING` + cuộc gọi.
- Luồng CSKH **không gọi AI** (X-AC5): FE không import `features/ai` trong `features/cskh`, `features/deliveries`, `app/print`.

---

## 9. Tham số settings/env (bất biến 7) — `backend/config/settings.py`

| Tên | Mặc định | Dùng ở | Lô |
|---|---|---|---|
| `CSKH_PII_RECENT_DAYS` | 7 | scope | 1 |
| `CSKH_CLAIM_MINUTES` | 5 | claim | 2 |
| `CSKH_MAX_UNREACHABLE_ATTEMPTS` | 3 | N | 2 |
| `CSKH_UNREACHABLE_WINDOW_MINUTES` | 30 | W | 2 |
| `CSKH_MIN_RETRY_MINUTES` | 10 | M | 2 |
| `THROTTLE_CSKH_SEARCH` (vào `CAVEVE_THROTTLE_RATES`) | `30/min` | search | 2 |
| `CSKH_MANAGER_DECISION_MINUTES` | 30 | D | 3 |
| `CSKH_EXTEND_MAX_HOURS` | 24 | decide EXTEND | 3 |
| `CSKH_AUTO_CANCEL_ENABLED` | `0` (**tắt**) | job bước 2, `site-info` | 3 |
| `CSKH_NOTICE_ENABLED` | `1` | `site-info` | 3 |
| `CSKH_WORKING_HOURS` | `"07:00-21:00"` | `site-info` (chỉ hiển thị) | 3 |
| `REFUND_DEADLINE_DAYS` | 30 | hạn hoàn | 3 |
| `SHOP_HOTLINE` | `""` (Duy đặt; rỗng → FE ẩn dòng liên hệ, `check` cảnh báo tên biến) | `cancel_notice`, `site-info` | 3 |
| `CSKH_QUEUE_ALERT_MINUTES` | 60 | attention | 4 |
| `LABEL_UNPRINTED_ALERT_MINUTES` | 15 | attention | 4 |

Đọc bằng `int(os.getenv(...))` như các tham số hiện có; service đọc `settings.X` **lúc chạy** (để `override_settings` có hiệu lực).

---

## 10. Rủi ro bắt buộc + cơ chế chặn + test

| Rủi ro | Cơ chế chặn | Test bắt (tên gợi ý) |
|---|---|---|
| **Rò PII — CSKH xem khách ngoài phạm vi** (Critical) | `cskh_note_q` ở queryset đơn; hàng chờ tính `in_scope` từng dòng; detail/action ngoài phạm vi 404; `cskh` không có `view_customer`/`view_deliverynote` | `test_cs01_scope.py`: CS-01-AC3…AC7 (D1…D6, đổi `CSKH_PII_RECENT_DAYS`); CS-05-AC5, CS-09-AC4: dòng ngoài phạm vi **không có** khoá `customer_name`, `phone`, `address`, `recipient_*` |
| **Rò PII — log** | Không log `request.data`, `q`, `note`; logger chỉ mã đơn/phiếu/kết quả; job log mã đơn | `test_xac1_pii_logs.py`: chạy CS-04…CS-14 + job dưới `assertLogs(level="DEBUG")` trên root; không chuỗi `Khách Thử PII`, `0900000999`, `Số 1 Đường Kiểm Thử`, `ghichu-bimat` |
| **Rò PII — AuditLog** | `changes` chỉ mã/tên field; `note` của AuditLog qua bộ kiểm BR-GH-19; `__str__` model mới không PII; recipient không trong `admin locked_fields` | `test_xac2_audit.py`: quét `changes`, `note`, `object_repr` mọi dòng sinh ra; CS-12-AC7 tìm địa chỉ cũ ở mọi bảng mới |
| **Rò PII — Shop công khai** | `cancel_notice` dựng tay từng khoá; không serializer back-office | CS-10-AC6: đệ quy khoá ∉ {`customer_name`,`phone`,`address`,`delivery_address`,`recipient_*`,`note`, `calls`}; sai 4 số → 404 giống hiện nay |
| **Rò PII — FE lưu/URL** | Không `useDraft`, không storage, URL chỉ id; `Cache-Control: no-store` | X-AC4 (Playwright): quét `localStorage`, `sessionStorage`, IndexedDB, URL request, console; test BE header `no-store` |
| **Rò PII — tem giấy** | SĐT che; tem cũ/huỷ vào `to_void` + nút "Đã huỷ tem"; attention `labels_to_void` | CS-11-AC5, CS-14-AC1…AC5 |
| **Rò PII — ghi chú tự do** | ≤ 200 ký tự, chặn `\d{9,}` sau khi bỏ `[\s.\-]` | CS-06-AC6, CS-09-AC7 (+ biến thể `0900.000.999`, `0900 000 999`, `+84900000999`) |
| **Rò giá vốn** | Serializer mới liệt kê field; dòng hàng lấy tay từ `SalesInvoiceLineBatch` (không `unit_cost`) | `test_xac3_cost_keys.py`: token **mọi** Group (kể cả `chu`) gọi mọi endpoint §4.1; duyệt đệ quy không khoá ∈ {`unit_cost`,`purchase_rate`,`landed_unit_cost`,`rate`,`cost`,`profit`,`margin`}; CS-11-AC4 không `total_amount/price/amount` |
| **Vượt quyền** | T1 perms + T2 `require_perm`/`required_perms` + T3 scope | `test_xac7_matrix.py`: ma trận X-AC7 đủ 6 cột, người không Group 403, chưa đăng nhập 401, kiêm `nv_kho+cskh` = hợp |
| **IDOR** | Mọi action dùng `get_object()` qua queryset đã lọc; `note_id` ngoài phạm vi = 404 | CS-06-AC10, CS-01-AC6 |
| **Tự huỷ sai / huỷ trùng** | Cờ tắt mặc định; khoá dòng + đọc lại; `request_id` uuid5; chỉ `UNREACHABLE/WRONG_NUMBER`; bỏ qua phiếu đã sang `PREPARING`/đơn đã huỷ | CS-08-AC1…AC10 (+ `CSKH_AUTO_CANCEL_ENABLED=0` → không huỷ, vẫn chuyển Quản lý) |
| **Tranh chấp job ↔ Quản lý** | Thứ tự khoá §1.5 | CS-08-AC6: (a) decide trước → job đọc lại bỏ qua; (b) job trước → decide 409; (c) `mock` xác nhận `select_for_update` được gọi đúng thứ tự (mẫu `accounts/staff/tests/test_q1_concurrency.py`) |
| **Chứng từ bị xoá/sửa** | `CustomerCall`, `LabelPrint` không có endpoint ghi ngoài action; FK `PROTECT`; không đăng ký Admin | X-AC6: PATCH/PUT/DELETE → 405/404, dữ liệu không đổi |
| **Hoàn kho sai khi huỷ phiếu `CONFIRMING`** | Thêm `CONFIRMING` vào `_STOCK_STILL_IN_WAREHOUSE` | CS-04-AC5 (ledger `CANCEL_RESTORE` đúng lô gốc), CS-08-AC1 |
| **Đơn kẹt ở `CONFIRMING`** (nút cổ chai, job chết) | attention `cskh_queue_waiting`; `check_cskh_job_health`; Quản lý kiêm CSKH | CS-15-AC2; test command health exit 1/0 |
| **Kiểm kê chênh dương giả** (Q-C17) | Quy định vận hành; story P-09 sau | — (ghi `03-dev-notes.md`, không code) |
| **Test cũ vỡ vì BR-GH-11** | Fixture `make_order_with_note(..., confirmed=True)` mặc định đưa phiếu về `PREPARING` (mô phỏng đã xác nhận: phiếu `PREPARING` + task `DONE`) → test dùng fixture không đổi; test đi qua luồng thanh toán thật dùng helper `confirm_note_for_test(note)` hoặc đổi kỳ vọng `PREPARING`→`CONFIRMING`. Danh sách file sửa có chủ đích ở 02c Lô 2 | Suite xanh sau sửa; không sửa test nào ngoài danh sách |
| **seed_demo không gỡ được phiếu demo** (`PROTECT`) | `seed_demo --remove` đánh dấu cả `ConfirmationTask`/`CustomerCall`/`LabelPrint` của phiếu demo; nhận `CONFIRMING` như `PREPARING` | `apps/accounts/demo/tests/test_d1_seed_demo.py` xanh + 1 test mới |
| **Tên nhóm lạ phá màn Nhân sự** | `ROLE_ORDER`, `GROUP_CODES` thêm `cskh` | CS-01-AC8, test S41/S47 hiện có xanh |

**Test bắt buộc theo endpoint** (skill django-drf-patterns): happy path đúng Group · 403 thiếu quyền + 401 chưa đăng nhập, dữ
liệu không đổi · không rò giá vốn (`nv_kho`, `cskh`) · `BusinessError` → 400/409 đúng `code` · biên (N, W, M, D đúng mốc
±1 phút bằng `mock.patch("django.utils.timezone.now")`/tham số `now=`). Dữ liệu test **chỉ giả**.

---

## 11. Thứ tự thực hiện + lô (chi tiết file/lệnh ở `02c-giao-viec.md`)

| Lô | BE (thứ tự) | FE (mock theo contract §4) | Môi trường |
|---|---|---|---|
| 0 | — hồ sơ `sua-loi-bao-mat` xong, merge `main` | — | — |
| 1 | migration §2.7 Lô 1 → CS-01 (Group, scope, me) → CS-02, CS-03 | `nav/groups`, `features/deliveries` (bảng + chi tiết + Đã đóng gói) | staging được |
| 2 | CS-04 (signal, hoàn kho CONFIRMING, sửa test cũ) → CS-05 → CS-06 → CS-11 | `features/cskh` (hàng chờ, chi tiết, kết quả gọi), In tem + `app/print/label` | **chỉ staging** (production cùng Lô 3) |
| 3 | CS-07 (decide) → CS-08 (job, cờ tắt) → CS-09 → CS-10 | khối Quyết định, nhắc việc báo hoàn, Shop `cancel_notice` + câu báo trước | production **sau** `legal-vn` duyệt câu + Duy bật cờ |
| 4 | CS-12, CS-13, CS-14, CS-15 (song song) | như BE | staging → production |
| 5 | CS-17, CS-18 | CS-16, CS-17, CS-18 | khi còn thời gian |

FE làm song song BE từ contract §4 với mock; khi BE lệch contract → be-dev ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng,
Tech Lead chốt lại file này.

---

## 12. Câu hỏi kỹ thuật · Việc Duy cần làm

**🔴 chặn:** không có. Mọi điểm mở đã chọn mặc định 🟡 (§0b) hoặc chốt contract (§0c).

**Việc Duy cần làm (không phải việc dev):**
1. **D6 — ghi 3 quyết định vào `doc/decisions.md`:** (a) chuỗi phiếu giao có "Chờ xác nhận" trước "Soạn hàng" (sửa 10/09);
   (b) thêm Group thứ năm `cskh` (sửa "bốn Group" 10/09); (c) Hệ thống tự huỷ đơn đã trả tiền khi không liên lạc được và Quản
   lý không xử lý trong 30' (BR-GH-13 sửa, BR-HT-10). Nên ghi luôn D1–D5, D7 theo §0b.
2. Giao `legal-vn`: câu `cancel_notice` + câu báo trước ở checkout (NĐ 356/2025) và quy định ghi nhãn trên tem (Q-C6). Có kết
   quả mới lên production Lô 3 (và CS-11 nếu phải thêm trường).
3. Lúc deploy: tạo Cloud Run Job + Scheduler `*/5` (§5.2) cho staging và production; đặt `SHOP_HOTLINE`; production giữ
   `CSKH_AUTO_CANCEL_ENABLED=0` tới khi (2) xong rồi mới bật.
4. Gán nhân viên vào nhóm `cskh` qua màn Nhân sự; quy định nội bộ: gọi bằng máy/SIM của vựa (Q-C7), xé tem hỏng/tem cũ, không
   lưu tem ra PDF, không kiểm kê lô còn phiếu chưa soạn (Q-C17).
5. Điều phối viên chuyển hai ghi chú sang hồ sơ khác: hồ sơ AI Lô 2 (§8 — tiền tố cấm, khoá PII mới); hồ sơ khung go-live
   (GL-01/GL-04 dùng chung `site-info` + `cskh_notice`, GL-03-AC9 tính thêm khoá `cancel_notice`).

**🟢 để sau:** hạn lưu `CustomerCall.note_text` và ẩn danh hoá theo yêu cầu khách; Redis cho throttle nhiều instance; báo cáo
CSKH (Q-C18); in tự động (C6).

---

## 13. Review (Việc 3 của Tech Lead)
_(Điền sau khi từng lô QA APPROVED: REVIEW PASS / REVIEW FAIL kèm file:dòng.)_
