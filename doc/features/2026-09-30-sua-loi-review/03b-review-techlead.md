# Review Tech Lead — P8 Sửa lỗi review P1–P7

## Lô 1

> Claude (Tech Lead) · 2026-09-30 · Diff chưa commit trên `main` (sau `6c5868e`) · Story SR-01, SR-02, SR-03.

### Kết luận: **REVIEW PASS**

Không có lỗi Critical, High hay Medium. Có 5 việc mức Low, không chặn QA/commit. Nên sửa L1 và L2 cùng lô nếu còn lượt, vì cả hai chỉ đổi 1–2 dòng.

### Lệnh kiểm chứng đã chạy trong lượt review
```
DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.ai apps.accounts apps.common   -> Ran 449 tests  OK
manage.py test apps.ai.execution.tests.test_p8_close_batch_sold apps.accounts.audit.tests.test_p8_cost_keys_scan -v 2 -> Ran 20 tests OK (đủ 13 + 7, tên test khớp dev notes)
manage.py test apps.content.entries                                                                -> Ran 11 tests  OK
manage.py makemigrations --check --dry-run                                                         -> No changes detected
```
Ngoài ra đã chạy thêm một script dò ở scratchpad (không nằm trong repo), gọi `POST /api/ai/commands/inventory.batch.close/call/` theo từng Group. Kết quả: `chu` nhận 200 (proposal C), còn `quan_ly`, `nv_kho`, `nv_giao`, `cskh` đều nhận **404 `COMMAND_UNKNOWN`**. `quan_ly` không có `inventory.close_batch`. Như vậy 404 đến từ nhánh kiểm quyền (effective_level bước 4–5 = OFF), không phải do chính sách AI đang đóng.

### Đối chiếu từng điểm

**Giá vốn (SR-01, bất biến 1)**
- `COST_KEYS` có đủ 8 khoá mà 02b §1.1 yêu cầu (`cost_keys.py:16-18`). Test `test_sr01_ac3_cost_keys_co_du_khoa_tien` khoá cứng danh sách này.
- Đã quét mọi `record_audit(... changes=...)` trong `apps/`. Dòng audit duy nhất ghi số tiền suy ra được giá vốn là `cancel_expired_batch` (`loss_amount`) cùng hai dòng `landed_unit_cost` vốn đã có trong tập khoá. `refunds`, `payments` và `orders` ghi `amount` là giá **bán**, đúng quy ước trong docstring. Không có dòng audit nào chia `amount` cho số kg để ra giá vốn. Timeline có nhánh `record_purchase_cost` đọc `amount`, nhưng hiện chưa service nào ghi action này, nên chưa có đường lọt (xem ghi chú N1).
- Tác động phía AI: `SCRUB_COST_KEYS = COST_KEYS` (`ai/policy/rules.py:106`) và `ai/registry/api.py:101` cũng lọc 8 khoá mới khi người gọi thiếu `view_costprice`. Đã rà các tên khoá mới trong code ngoài test. Ngoài audit, `inventory_value` chỉ xuất hiện ở KPI dashboard, mà KPI này vốn chỉ trả khi `can_cost`. `expired_cost` chỉ có ở `batch_pnl`, vốn chỉ dành cho Chủ. Không có field giá **bán** hay số kg nào trùng tên để bị lọc nhầm (`loss`, `margin`, `gross_profit` không có trong serializer nào). Toàn bộ 449 test AI/accounts/common vẫn xanh. Kết luận: mở rộng tập khoá chỉ siết thêm, không làm mất dữ liệu của người có quyền.
- Bảng `AuditLog` không bị sửa. Việc lọc nằm ở `audit_item → redact_cost` và có test AC4.

**Dữ liệu cá nhân (bất biến 9)**
- Log của job chỉ có `act.pk`, `act.command` và `type(exc).__name__` (`run_due_ai_actions.py:299`, overdue ở `:~88`, `_mark_failed` lỗi ở `:~303`). Không có `str(exc)` hay args. `downgrade_reason` và `note` của dòng `fail_*` là chuỗi cố định, `changes={}`. Test AC4 kiểm bằng sentinel `SECRET-KHACH-GIA-0900000123` qua `assertLogs` ở mức DEBUG, bắt log gốc. Fixture chỉ dùng dữ liệu giả `0900000999` / "Khách Giả A".

**Phân quyền**: Lô này không thêm endpoint hay quyền mới. Ma trận `/api/audit-logs/` có test đủ 6 cột.

**Migration**: không có. `AiAction.Status.FAILED` đã có sẵn trong model (`ai/models/actions.py:31`).

**`run_due_ai_actions` (SR-03)**
- `try/except` nằm **ngoài** `transaction.atomic()` của từng việc (`_process_one`). Khi có lỗi, atomic rollback toàn bộ thay đổi dở dang, kể cả thứ mà view đã ghi. `_mark_failed` mở transaction mới. Test `..._bi_rollback` chứng minh điều này.
- `_mark_failed` idempotent: đọc lại với khoá, lọc `status=SCHEDULED`, không có thì trả `False`. Test `..._khong_de_len_viec_da_doi_trang_thai` và nhánh "chạy lần 2, `call_count == 0`, vẫn 1 dòng `fail_*`" đều đã phủ.
- `skip_locked` hợp lý. Nếu tiến trình khác đang giữ dòng thì tiến trình đó sẽ xử lý, còn việc này giữ `SCHEDULED` và được chạy lại ở lần sau, không mất việc. Có một điểm nhỏ ở L2.
- Bước đẩy việc quá hạn 2 giờ vẫn chạy sau poison pill và mỗi việc bọc try riêng. Test AC3 và AC4 đều assert `overdue.status == ESCALATED`.
- `safety.py`: đã sửa đúng 2 lookup sang `sales_order_id` (FK thật ở `sales/models/payments.py:45`). Đọc lại toàn file không còn lookup sai. Trạng thái chờ duy nhất của `Refund` là `PENDING`, đúng với model.

**Lệch 02b**: không có lệch thực chất. `_process_one(act, registry)` nhận thêm `registry` và việc log nằm trong `_fail_safely` chỉ là khác biệt cách viết, hành vi giữ đúng như 02b §1.3.

**File ngoài danh sách Lô 1**
- `backend/apps/ai/execution/__init__.py` và `backend/apps/content/entries/tests/__init__.py` là 2 file rỗng. **Chấp nhận.** Không đổi hành vi sản phẩm vì import `apps.ai.execution.*` vẫn chạy như cũ, và nhờ 2 file này mà 57 + 11 test trước đây bị bỏ qua giờ được chạy lại. Đã rà toàn bộ `apps/**/tests` và các package cha: không còn chỗ nào thiếu `__init__.py`. Cần commit 2 file này cùng Lô 1 và ghi vào cột "Được sửa" của Lô 1 ở `02c` khi đánh ☑.
- `erp-console/package.json` và `package-lock.json` thuộc SR-02. Diff lock chỉ đổi 4 dòng `@types/node` (đúng AC4).

**Chất lượng test**: assert đều thật. Test quét có chống xanh giả: kiểm các dòng audit có trong DB, kiểm khoá nhạy cảm có trong DB, đếm `ok_responses > 0` với assert 200 từng trang, kiểm `seen_actions ⊇ expected` và kiểm Chủ vẫn thấy `1012340`. Ca AC2 có đối chứng âm (RESOLVED/REFUNDED không chặn).

### Chốt hai "lệch thiết kế" be-dev nêu
1. **403 và 404 ở SR-03**: **404 `COMMAND_UNKNOWN` là hành vi đúng, không sửa code.** Registry cố ý không cho người thiếu quyền biết lệnh có tồn tại. Điều này đã chốt ở `doc/features/2026-09-28-ai-digital-worker/02b-tech-design.md:340,502` ("404 COMMAND_UNKNOWN — cả khi không có quyền"). Ô 403 trong ma trận SR-03 (`02-stories.md`) là lỗi viết story. Điều phối viên cần sửa ô đó thành "404 `COMMAND_UNKNOWN`". Tech Lead không sửa `02*.md`. Test phải assert **đúng 404** chứ không nhận cả 403 và 404 (xem L1).
2. **81234 hay "81.234"**: không phải lệch. "81.234" viết theo kiểu Việt Nam, dấu chấm là dấu phân cách nghìn, tức 81234 đ/kg. Fixture đúng với story, và 81234 × 10 = 812340 khớp sentinel.

### Việc sửa (Low, không chặn)
| # | Mức | File:dòng | Việc |
|---|---|---|---|
| L1 | Low | `backend/apps/ai/execution/tests/test_p8_close_batch_sold.py:302` | Đổi `assertIn(res.status_code, (403, 404))` thành `assertEqual(res.status_code, 404)` và thêm `assertEqual(res.json()["code"], "COMMAND_UNKNOWN")`. Bổ sung một ca đối chứng dương cho `chu` (200) trong cùng test để chứng minh 404 đến từ quyền, không đến từ lệnh bị tắt. |
| L2 | Low | `backend/apps/ai/management/commands/run_due_ai_actions.py:271-275` | Hiện `select_for_update(skip_locked=True).select_related("owner")` khoá luôn dòng `auth_user` của owner trên Postgres. Nếu dòng user đang bị khoá (đăng nhập, sửa hồ sơ), việc sẽ bị bỏ qua và lần chạy sau lại lỗi lại. Nên dùng `select_for_update(skip_locked=True, of=("self",))` hoặc bỏ `select_related`. |
| L3 | Low | `backend/apps/accounts/audit/tests/test_p8_cost_keys_scan.py:160` | Sentinel `"81234"` được tìm trên toàn bộ JSON, gồm cả timestamp có micro giây (ví dụ `.812345`), nên có rủi ro hỏng ngẫu nhiên, dù thấp. Nên tìm sentinel trong `changes` và `note` của từng dòng thay vì cả blob, hoặc dùng số giả khó trùng hơn (ví dụ 97531). |
| L4 | Low (nợ) | `backend/apps/ai/management/commands/run_due_ai_actions.py:34-49` | Nhánh `AI_ENABLED=False` chưa cô lập lỗi từng việc. Rủi ro thấp vì nhánh này chỉ `save` và không dispatch. Để dồn sang Lô 7 hoặc sau. |
| L5 | Low (nợ) | `run_due_ai_actions.py:265-294` | Việc `FAILED` chỉ hiện với owner (`ai/actions/api.py:51`). Nếu owner không phải Chủ thì Chủ chỉ thấy qua Nhật ký `fail_*`, không có trong hộp việc, dù `text` ghi "cần Chủ xem". 02b không yêu cầu điều này. Ghi "để sau": cân nhắc đặt `assignee_group="chu"` và cho hộp việc Chủ lọc cả `FAILED`. |

### Ghi chú
- N1: nhánh `record_purchase_cost` ở `inventory/batches/timeline.py:137-141` đọc khoá `amount` (chi phí mua, tức giá vốn). Hiện chưa service nào ghi action này, nên chưa lọt. Nếu sau này thêm, phải ghi bằng khoá `allocated_amount` hoặc `purchase_cost` (đã có trong `COST_KEYS`), không dùng `amount`.

## Lô 2

> Claude (Tech Lead) · 2026-09-30 · Diff chưa commit trên `main` (sau `64aa7a7`) · Story SR-04, SR-05, SR-06 (BE), SR-07 (FE).

### Kết luận: **REVIEW PASS**

Không có lỗi Critical, High hay Medium. Có 6 việc mức Low. Nên sửa L1 ngay trong lô vì chỉ vài dòng, và lỗi này sinh ra từ câu chữ quá tay của chính 02b §2.4. Các việc còn lại dồn sang Lô 7.

### Lệnh kiểm chứng đã chạy trong lượt review
```
cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.ai apps.sales apps.common   -> Ran 547 tests  OK
cd erp-console && npm test                                                                                     -> Test Files 10 passed, Tests 87 passed
manage.py shell: liệt kê registry                                                                              -> 110 lệnh, 52 lệnh đọc (khớp dev notes)
```

### Đối chiếu từng điểm

**PII qua AI (SR-04, bất biến 9)**
- `SCRUB_PII_KEYS` có đủ 6 khoá mới (`ai/policy/rules.py:94-101`). Hàm `scrub_data` (`ai/execution/scrub.py`) gặp khoá thuộc tập này thì `continue` trước khi đệ quy, nên **cả nhánh bị bỏ**, dù nhánh đó là chuỗi, dict hay list. Hàm lọc cả với Chủ. Test `test_p8_scrub_pii.py` phủ đủ chuỗi, dict, list lồng nhau, khoá SĐT che và khoá viết hoa/thường.
- Test quét `test_p8_pii_sweep.py:131-161` chạy thật trên 52 lệnh đọc × 5 Group. Lệnh `detail` được thử với mọi khoá tra cứu của fixture: pk, mã đơn, mã lô, mã hàng, mã hoá đơn. Fixture chứa đủ 4 sentinel: tên, SĐT và địa chỉ nằm trên đơn, tên người chuyển nằm trong `raw_payload`. Test kiểm sentinel trên chuỗi response, kiểm cả khoá PII, và yêu cầu mọi response dưới 500. Có hai assert chống xanh giả: `ok_total > 0` và `retrieve_ok > 0`, dev ghi được 101 response 200, trong đó 39 là retrieve. Test riêng `sales.salesorder.retrieve` với `chu` assert mã đơn có mặt, PII không có. Log ĐỎ trong dev notes xác nhận đúng thứ tự 02b §2.2: nếu chỉ sửa SR-05 thì retrieve lộ `customer.name`.
- Đã rà các đường lộ PII khác qua AI:
  - Registry **không có** lệnh `sales.customer.*`. `CustomerSerializer` trả `name` và `default_address`, hai khoá này không có trong tập lọc. Nếu sau này lệnh này lọt vào registry thì sẽ lộ (xem N1).
  - `DeliveryNoteSerializer` trả `customer_name` và `address`, bản chi tiết trả thêm `recipient_name`. `RefundSerializer` trả `customer_name` và `customer_phone`. Cả năm khoá này đều bị lọc. Field `label` của phiếu giao chỉ là trạng thái in, không chứa PII.
  - Preview đề xuất mức C chỉ gồm `type` và `code` (`pipeline.py:475-480`). `AiAction.args` không lưu kết quả đọc, và đã có test BR-AI-09.
  - `common.guidance` giờ trả 400 khi gọi qua AI (xem lệch 1). Bản thân provider order cũng không trả PII, đã có test `test_sr06_ac3_guidance_khong_lo_pii_khach`.
- Điểm yếu của test quét: xem L2.

**Lệnh chi tiết (SR-05)**
- `discovery.py:221-228`: `retrieve`, `partial_update`, `update` và `destroy` luôn có `detail=True`. `@action` giữ thuộc tính `detail` như cũ. APIView suy theo pattern. Nhánh APIView ở `:316` dùng chung `_path_has_lookup`, không lặp code. Đã rà FE: không nơi nào gọi `*.partial_update` hay `*.retrieve` qua AI, nên đổi `target="detail"` không làm hỏng luồng FE.
- `pipeline.py:165-201`: ViewSet vẫn kiểm phạm vi qua `get_object`. APIView thì không bao giờ `AttributeError`. Nếu tham số URL khác `{lookup}`, pipeline chặn sớm bằng 400 `BR-AI-01`. Đây là cách đơn giản hơn mà 02b §2.2 đã chấp nhận. SR-05-AC3 có ca đối chứng dương, và có test xác nhận H7 vẫn cấm hẳn `sales.salesorder.partial_update`.

**Phạm vi đơn (SR-06, Tầng 3)**
- Đã so từng dòng: `scope.py::scope_orders_for` **chép nguyên** logic cũ của `SalesOrderViewSet.get_queryset`, gồm `has_full_delivery_scope`, `assigned_q`, nhánh `is_cskh` với `Exists(... cskh_note_q)` và `distinct()`. Thứ tự lọc so với `annotate` trong `get_queryset` cũng giữ nguyên. Import `Exists`, `OuterRef` và `DeliveryNote` trong `orders/api.py` vẫn còn dùng ở chỗ khác, không để lại import chết. `test_sr06_ac4_scope_orders_for_khop_danh_sach_don` so với `GET /api/sales/orders/` trên 7 user, và toàn bộ test cũ của đơn vẫn xanh. Kết luận: **hành vi danh sách không đổi**.
- Guidance order (`next_steps.py:170-182`) dùng chung hàm phạm vi. Cả hai trường hợp "không tồn tại" và "ngoài phạm vi" đều trả `Http404("Không tìm thấy đơn hàng")` với thông điệp cố định. Test `:97-100` và `:163-171` assert body không chứa `DH-OUT-1`.
- Escalate (`ai/actions/services.py:318-327`): `Http404` và `PermissionDenied` (cả Django lẫn DRF) được ném lại nguyên. Lỗi khác thành `BusinessError("Không thể nạp chứng từ.")`, **không còn in `{e}`**. Log chỉ ghi `doc_type` và `type(exc).__name__`. Không còn đường nào đưa nội dung exception ra response hay log.

**Phân quyền**: lô này không thêm endpoint hay quyền mới. Ma trận guidance có đủ 5 Group, cộng user gán quyền trực tiếp, khách 401 và thiếu quyền 403.

**FE nháp Nhập lô (SR-07)**
- `draftStorage.ts::sanitize` chỉ giữ `item_code`, `qty` và `shelf_life_days`, **cả lúc ghi lẫn lúc đọc**, nên dữ liệu cũ có `rate` cũng bị bỏ. Nháp lưu ở `sessionStorage`, khoá `cave_draft_nhap_lo:<userId>`. `NhapLoForm` gọi `purgeLegacyDraft()` khi mở form. Khi `logout`, `AuthProvider.tsx:202` xoá mọi khoá `cave_draft_nhap_lo*` ở cả hai storage. Form nạp nháp xong vẫn ép `rate: ""`. Không còn chỗ nào trong UI ghi giá mua xuống storage.
- Đã xét thứ tự hai effect khi `userId` đổi từ `null` sang id: effect nạp đọc nháp trước, effect lưu chạy sau với state cũ, rồi render kế tiếp ghi lại nháp đúng. Không mất nháp.

### Chốt 5 lệch dev nêu
1. **`dispatch.py` chỉ truyền `pk`, nên `reports.batch_pnl` và `common.guidance` qua AI trả 400**: **chấp nhận cho P8, để sang P9.** SR-05-AC4 cho phép "200 hoặc 400 có thông điệp". Trước lô này hai lệnh đó trả 500, nên không có hồi quy. FE không gọi guidance qua AI mà gọi thẳng `/api/guidance/`. Việc P9: `dispatch_command` ánh xạ tên tham số từ `spec.path` (`batch_id`, `doc_type` + `doc_id`), sau đó bỏ chặn 400 ở `pipeline.py:165-180`. Trước khi mở lại `common.guidance` qua AI phải chạy lại test quét PII.
2. **SR-05-AC3 dùng `delivery.deliverynote.partial_update`**: **chấp nhận.** H7 cấm hẳn `sales.salesorder.partial_update`, và dev đã thêm test xác nhận lệnh đó vẫn 404 với mọi Group. Cơ chế cần kiểm (Tầng 3 qua `get_object` ở bước 6) giống hệt. Điều phối viên nhờ PO sửa chữ ở SR-05-AC3 trong `02-stories.md`.
3. **Escalate của provider batch/refund/payment đổi 400 thành 404/403**: **ổn, giữ nguyên.** Hành vi mới đúng quy ước BR-PQ-12, đúng mã HTTP, và nhất quán với `GET /api/guidance/`. FE `GuidancePanel` hiện `err.message` với mọi mã. `apiFetch` xử lý 403 bằng cách tải lại `me` (có chống lặp) và 404 bằng thông điệp chung. Test cũ vẫn xanh. Ba provider này vẫn đưa `doc_id` vào thông điệp 404. Đó là giá trị người gọi tự gửi nên không phải rò, nhưng nên đồng bộ về thông điệp cố định (L5).
4. **`sales.salesinvoice.*` mất khoá `customer` (id)**: **chấp nhận** theo 02b §2.1 (bỏ cả nhánh). Id khách là khoá nối sang dữ liệu cá nhân, AI không cần nó. Không luồng FE nào đọc khoá này từ kết quả AI.
5. **FE**:
   - (a) `AuthProvider` import `draftStorage` của `purchasing`: chính 02b §2.4 chỉ định cách này nên chấp nhận cho Lô 2. Ở Lô 7 sẽ dọn: chuyển phần dọn `cave_draft_nhap_lo*` vào `shared/lib/drafts.ts` (L4).
   - (b) Ba hàm localStorage cũ ở `features/purchasing/api.ts:43-75`: UI không còn gọi nên hiện không rò, nhưng code chết vẫn ghi `rate` nếu ai đó gọi lại. Xoá ở Lô 7 cùng test `purchasing.test.ts:29` (L3).
   - (c) Sau F5 idempotency key được sinh mới: **nên sửa** (L1). SR-07-AC4 chỉ yêu cầu sinh key mới khi nạp nháp của phiên khác hoặc sau khi gửi thành công, không yêu cầu sinh mới sau F5 của cùng người. Câu "sinh mới mỗi lần mở form" trong 02b §2.4 là quá tay. Nó làm hỏng một phần DW-17-AC3: trường hợp mất mạng, server đã tạo phiếu, người dùng F5 rồi gửi lại sẽ tạo **phiếu nhập thứ hai**, kéo theo tồn kho và giá vốn sai. Key không phải dữ liệu nhạy cảm, nên giữ key trong nháp `sessionStorage` theo user là an toàn.

### Việc sửa
| # | Mức | File:dòng | Việc |
|---|---|---|---|
| L1 | Low (nên sửa trong Lô 2) | `erp-console/features/purchasing/components/draftStorage.ts:15-19, 33-49` · `NhapLoForm.tsx:58, 66-71, 94-100` | Thêm `idempotencyKey?: string` vào `NhapLoDraft`, `sanitize` giữ trường này nếu là chuỗi. `NhapLoForm` dùng `draft.idempotencyKey ?? generateUUID()` và lưu key cùng nháp. Sau khi gửi thành công vẫn `clearDraft` và `handleResetNew` sinh key mới. Đăng xuất đã xoá nháp. Thêm test vitest: cùng user, lưu rồi nạp giữ nguyên key; `rate` vẫn không có. Điều phối viên sửa câu ở 02b §2.4 thành "sinh mới khi không có nháp của chính người này / sau khi gửi thành công". |
| L2 | Low (test) | `backend/apps/ai/registry/tests/test_p8_pii_sweep.py:79-94` | Fixture chưa cho `nv_giao` và `cskh` thấy dữ liệu có PII: phiếu giao chưa gán, cskh chưa có task trong phạm vi. Fixture cũng chưa có `Refund`, và phiếu giao chưa có `recipient_name`/`recipient_phone`. Hiện hai cột `nv_giao`/`cskh` và lệnh `sales.refund.*` chỉ quét trên dữ liệu rỗng. Việc cần làm: gán phiếu cho `nv_giao`, tạo task CSKH trong phạm vi, tạo 1 phiếu hoàn, đặt recipient bằng sentinel, thêm "Khách Giả B" vào `PII_STRINGS`. Làm ở Lô 7 (SR-24). |
| L3 | Low (nợ) | `erp-console/features/purchasing/api.ts:43-75` + `purchasing.test.ts:29` | Xoá `DRAFT_STORAGE_KEY`, `getNhapLoDraft`, `saveNhapLoDraft`, `clearNhapLoDraft` và chuyển test DW-17-AC3 sang `draftStorage`. Làm ở Lô 7 (SR-23). |
| L4 | Low (nợ) | `erp-console/features/auth/components/AuthProvider.tsx:25, 202` | Import chéo module `auth` → ruột `purchasing`. Việc cần làm: chuyển hàm dọn tiền tố `cave_draft_nhap_lo` vào `shared/lib/drafts.ts::clearAllDrafts` (hoặc để `draftStorage` sống ở `shared/lib/`), sau đó bỏ import. Làm ở Lô 7 (SR-23). |
| L5 | Low (nợ) | `backend/apps/sales/refunds/next_steps.py:144`, `inventory/batches/next_steps.py:157`, `sales/payments/next_steps.py:133` | Đổi thông điệp 404 thành chuỗi cố định, không lặp `doc_id`, cho đồng bộ với order. Làm ở Lô 7 (SR-22). |
| L6 | Low (nợ P9) | `backend/apps/ai/execution/dispatch.py:74-79` + `pipeline.py:165-180` | Ánh xạ tham số URL theo `spec.path` để `reports.batch_pnl` chạy được qua AI (lệch 1). |

### Ghi chú
- N1: tập lọc PII vẫn là **denylist theo tên khoá**, đúng quyết định của P8. `CustomerSerializer` (`sales/customers/serializers.py:10`) có `name` và `default_address`, hai khoá này không bị lọc. Hiện lệnh đó không có trong registry. Nếu sau này thêm ViewSet khách, hoặc thêm field PII mang tên khác (`payer_name`, `default_address`…), bắt buộc phải cập nhật `SCRUB_PII_KEYS` và mở rộng fixture test quét. Nên đưa việc chuyển sang allowlist vào P9.
- N2: `pipeline.py:181` chỉ kiểm phạm vi `target_id` khi view có `get_object`. Nếu sau này có **APIView ghi** mang một tham số `<pk>`, đề xuất mức C sẽ được tạo mà không kiểm phạm vi trước. View vẫn tự kiểm khi thực thi, nhưng khi đó `AiAction` đã có. Hiện 4 APIView trong registry đều là lệnh đọc, nên chưa có lỗ.
- Commit: SR-04 và SR-05 phải nằm **cùng commit** (SR-05-AC5).

## Lô 3

> Claude (Tech Lead) · 2026-09-30 · Diff chưa commit trên `main` (sau `6d98ac9`) · Story SR-08, SR-09 (BE + FE), SR-10, SR-11.

### Kết luận: **REVIEW PASS**

Không có lỗi Critical, High hay Medium. Có 4 việc mức Low, không chặn commit, dồn sang Lô 7. Không có migration, không có endpoint mới, không có quyền mới.

### Lệnh kiểm chứng đã chạy trong lượt review
```
cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.inventory apps.delivery apps.sales  -> Ran 542 tests  OK
cd backend && ... manage.py test apps.ai apps.accounts apps.common apps.catalog apps.purchasing apps.reports            -> Ran 592 tests  OK
cd backend && ... manage.py test                                                                                        -> Ran 1241 tests OK (khớp dev notes)
cd backend && ... manage.py makemigrations --check --dry-run                                                            -> No changes detected
cd erp-console && ./node_modules/.bin/tsc --noEmit                                                                      -> sạch
cd erp-console && npm test                                                                                              -> 10 file, 99 test passed
```

### Đối chiếu từng điểm

**Tiền và kho: SR-08 (BR-LO-07)**
- `check_cancel_expired_batch` (`inventory/batches/services.py:271-291`) kiểm EXPIRED trước (nên huỷ lần 2 vẫn trả `BR-LO-03`, AC5), sau đó chặn khi `qty_reserved > 0`. `cancel_expired_batch` gọi hàm kiểm **sau** `select_for_update` trên lô. `reserve` và `release` cũng khoá cùng dòng lô, nên không có khe nào để một đơn giữ chỗ thêm giữa bước kiểm và bước `WRITE_OFF`.
- Đếm đơn qua `_open_orders_count(batch, ("BOOKED",))` với `distinct` trên `order_line__order`. Chỉ đếm BOOKED là đúng: `_record_payment` chuyển đơn sang PROCESSING và trừ kho, nên chỉ BOOKED còn `qty_reserved`. Test `dem_dung_so_don_giu_cho` có ca 2 đơn.
- Không có đường nào nhả giữ chỗ hay huỷ đơn khách. AC2 (thanh toán sau khi bị chặn vẫn ra `PaymentTransaction` MATCHED và hoá đơn) và AC3 (TTL về 0 rồi huỷ được, đúng 1 `WRITE_OFF`) đều có test.
- Guidance (`next_steps.py:95-103`) dùng chung `check_cancel_expired_batch`: không lặp logic, đúng AC4.
- Body lỗi chỉ có kg và số đơn, không có giá vốn hay dữ liệu khách. Có test sentinel (`test_sr08_ac1_400_khong_ro_gia_von_va_du_lieu_khach`). Đây là 400 sớm, nên nhánh audit `loss_amount` không chạy. Nhánh đó đã được SR-01 lọc bằng `COST_KEYS`.

**SR-10 (`publish_batch` có khoá)**
- `@transaction.atomic` + `select_for_update().get(pk=…)`, kiểm DRAFT trên bản đã đọc lại, rồi ghi và trả object mới (`services.py:144-159`). Caller duy nhất là `api.py:59`, và serializer dùng giá trị trả về nên không trả trạng thái cũ.
- `cancel_receipt` (`purchasing/receipts/services.py:176-194`) khoá phiếu → dòng → lô rồi kiểm `status == DRAFT`. `publish_batch` chỉ giữ một khoá (dòng lô), nên không có vòng khoá ngược, không deadlock. Bên nào vào trước thì thắng, bên sau thấy trạng thái mới rồi trả 400. Tranh chấp thật trên PostgreSQL chưa chạy vì test dùng SQLite. Việc chứng minh bằng spy `select_for_update` ở cả hai phía là chấp nhận được.
- Ma trận publish đạt: chu/quan_ly 200, nv_kho/nv_giao/cskh 403, khách 401. JSON của quan_ly không có `purchase_rate`/`landed_unit_cost`.

**SR-09 (`record_call` 409 STALE_STATE)**
- Thứ tự khoá không đổi: phiếu → task, rồi đọc lại cả hai dưới khoá. Kiểm stale nằm ở `delivery/cskh/services.py:142-148`, **trước** máy trạng thái, nên phiếu đã huỷ không bao giờ quay về PREPARING. Ngoài ra không có `CustomerCall` hay audit nào được ghi. Test `_assert_unchanged` kiểm cả hai điều này.
- Nhánh idempotent `request_id` (bước 1) chạy trước kiểm stale và chỉ trả lại cuộc gọi đã có. Hành vi này đúng.
- Body 409 là `{"detail","code"}` với thông điệp cố định: không `extra`, không tên hay SĐT. Có test so khớp nguyên body và quét sentinel. Phân quyền không đổi: 403 cho nv_kho/nv_giao, 401 cho khách, có test ma trận.

**SR-11 (DW-26 idempotent)**
- `_escalate_to_chu` (`sales/payments/auto_confirm.py:180-222`): việc ở trạng thái kết thúc thì `return` trước khi ghi gì. Việc đang ESCALATED mà lý do không đổi cũng `return`. Audit chỉ được ghi khi tạo mới hoặc lý do đổi. Test AC2 phủ 6 trạng thái × 2 lần chạy.
- Audit và log chỉ có `bank_txn_id`, mã đơn, số tiền giao dịch và lý do, không có `raw_payload` hay tên người chuyển. Có test sentinel `test_sr11_khong_ghi_pii_vao_audit_va_action`.

**FE (SR-09-AC4)**
- `isStaleStateError` (`features/cskh/api.ts:145-148`) nhận ra lỗi bằng `ApiError.status === 409 && code === "STALE_STATE"`. `apiFetch` đã truyền `code` từ body. Modal hiện `detail` của BE trong `role="alert"` và khoá mọi nút kết quả cùng ô ghi chú (`actionsBlocked`). Nút "Tải lại" nạp lại hàng chờ rồi đóng modal. Lỗi 409 khác (`CLAIMED`) vẫn đi qua hộp lỗi chung. Nhánh 409 `STALE_STATE` "Đơn vừa được xác nhận bởi người khác" cũng được hưởng nút Tải lại, và như vậy là đúng.
- Sửa mock `req?.url ?? req?.path` (`mock.ts:330`) là đúng: `MockRequest` chỉ có `path` (`shared/lib/http.ts:40`), và `path` có kèm query. Trước bản sửa, tab lọc `?state=` không chạy trong chế độ mock. Mock 409 khớp contract BE. Phiếu mock 36 dùng dữ liệu giả.

### Chốt các lệch be-dev và fe-dev nêu
1. **SR-11-AC3 so `downgrade_reason["text"]` thay vì `code`: đồng ý, 02b §3.4 viết sai.** Mọi lần chuyển Chủ đều mang `code="AI_MISMATCH"`, nên nếu so `code` thì không bao giờ phát hiện được lý do đổi và AC3 không đạt. `text` mới là lý do thật. Điều phối viên sửa câu ở 02b §3.4 thành "`downgrade_reason["text"]` đổi". Lưu ý: nếu lý do có chứa `{exc}` (nhánh lỗi ở `:162`) mà thông điệp exception thay đổi giữa các lần chạy thì mỗi lần sẽ thêm 1 audit. Hiện các thông điệp `BusinessError` của `resolve_payment` là cố định, nên chưa phải lỗi.
2. **Lọc `UNMATCHED` cho toàn job: không có hồi quy DW-26.** Đã kiểm mọi nơi tạo giao dịch:
   - `UNMATCHED` chỉ sinh ở `payments/internal_api.py:103-117`, luôn với `sales_order=None`. `resolve_payment(ATTACH_TO_ORDER)` bỏ trạng thái UNMATCHED ngay khi gắn đơn (`services.py:534-549`). Vậy không tồn tại giao dịch UNMATCHED nào có đơn.
   - Giao dịch OPEN có đơn chỉ gồm ORPHAN, OVERPAID và UNDERPAID (`services.py:263-270`). Ở code cũ, cả ba **chưa bao giờ** được job tự khớp. ORPHAN (đơn đã huỷ) và OVERPAID (đơn không còn BOOKED) đều dừng ở bước e và bị chuyển Chủ. UNDERPAID có `amount < total_amount` ngay lúc tạo. `total_amount` chỉ được gán một lần lúc tạo đơn (`orders/services.py:271`), và ATTACH không đổi `amount` của khoản thiếu, nên ca này luôn dừng ở bước f và bị chuyển Chủ.
   - Kết luận: nhánh `CONFIRM_ORDER` ở code cũ vốn không bao giờ tới được. Bộ lọc mới chỉ bỏ những lần chuyển Chủ trùng với hàng chờ lệch, đúng như AC4 muốn. Không có ca tự khớp thật nào bị mất. Nhánh chết để dọn ở L1.
3. **SR-09: kết quả rác vẫn trả 400 `INVALID_INPUT`, còn phiếu CANCELLED với task không phải REFUND_CALL đổi từ 400 sang 409: đồng ý cả hai.** Kết quả rác là lỗi đầu vào, không phải màn hình cũ. Chữ "mọi kết quả khác" trong AC2 được hiểu là mọi kết quả hợp lệ. Đổi 400 `BR-GH-07` thành 409 là đúng 02b §3.2. Không có test cũ nào phụ thuộc mã cũ, và FE giờ xử lý cả hai ca bằng nút Tải lại. Riêng ca phiếu CANCELLED mà gửi kết quả rác thì trả 409 (vì kiểm stale chạy trước), vẫn chấp nhận được.
4. **201 thay vì 200: giữ 201.** 201 là hành vi hiện có của endpoint (`cskh/api.py:208`: 201 khi tạo, 200 khi trùng `request_id`), và test CS-09 cũ cũng kiểm 201. Chữ "200" trong bảng ma trận SR-09 chỉ có nghĩa là thành công. Điều phối viên nhờ PO sửa thành "201" (hoặc "2xx").
5. **SR-08-AC2 ghi "PAID" nhưng thực tế là "PROCESSING": đúng theo code.** `_record_payment` chuyển thẳng PAID sang PROCESSING khi xuất hoá đơn (`payments/services.py:306-311`). Test kiểm `{PAID, PROCESSING}` cùng với giao dịch MATCHED và hoá đơn là đủ. Nhờ PO sửa chữ AC2.
6. (Không có lệch số 6 riêng. Ý 8 của be-dev về `_open_orders_count` xem ở L3.)
7. **Counter `escalated` đếm cả no-op: chấp nhận, xếp Low (L2).** Chỉ số thống kê của job bị thổi lên, còn Nhật ký và trạng thái việc (thứ AC bảo vệ) thì đúng.
8. **fe-dev: STALE_STATE mới chỉ xử lý ở ghi cuộc gọi: chấp nhận.** BE lô này chỉ đổi `record_call`. Các thao tác khác trong modal vẫn hiện `detail` qua hộp lỗi chung, nên người dùng không bị kẹt, chỉ thiếu nút Tải lại. Gộp vào L4.

### Việc sửa
| # | Mức | File:dòng | Việc |
|---|---|---|---|
| L1 | Low (dọn, Lô 7 / SR-22) | `backend/apps/sales/payments/auto_confirm.py:85-86, 133-147` | Sau bộ lọc UNMATCHED, `p.sales_order` luôn là `None`. Việc cần làm: bỏ nhánh `candidate_orders = [p.sales_order]` và nhánh `CONFIRM_ORDER`, chỉ giữ `ATTACH_TO_ORDER`. Thêm chú thích dẫn tới chốt số 2 ở trên. Test DW-26 hiện có phải xanh y nguyên. |
| L2 | Low (Lô 7) | `backend/apps/sales/payments/auto_confirm.py:69, 80, 102, 106, 117, 128, 163` + `:203-213` | Đổi `_escalate_to_chu` để trả `True` khi thật sự tạo mới hoặc cập nhật, `False` khi no-op. Job chỉ `escalated_count += 1` khi `True`, còn lại cộng vào `skipped` (hoặc thêm khoá `unchanged`). Cùng chỗ đó, khi lý do đổi thì cập nhật luôn `args["reason"]` (hiện chỉ `downgrade_reason` được đổi, `args.reason` giữ lý do cũ). |
| L3 | Low (Lô 5, khi sửa `check_close_batch`) | `backend/apps/inventory/batches/services.py:207-215` | Truy vấn đơn mở trong `check_close_batch` đang lặp lại `_open_orders_count`. Thay bằng `_open_orders_count(batch, OPEN_ORDER_STATUSES)` (02b §3.1 yêu cầu tách hàm dùng chung). |
| L4 | Low (nợ FE, Lô 7 / SR-23) | `erp-console/features/cskh/CskhCallModal.tsx:162` | Dùng cùng `isStaleStateError` + `staleMessage` cho các thao tác đổi người nhận, huỷ xác nhận và quyết định Quản lý, để đơn đã huỷ cũng có nút Tải lại. Không cần đổi BE. |

### Ghi chú
- N1 (có từ trước, không do lô này): `_escalate_to_chu` dùng `get_or_create` theo `(target_model, target_id, command)`. Nếu Chủ đã tạo một đề xuất AI `sales.paymenttransaction.resolve` cho chính giao dịch đó (trạng thái PENDING, CONFIRMED hoặc SCHEDULED), job sẽ chuyển đề xuất ấy sang ESCALATED. Nếu có từ hai dòng trùng khoá trở lên, lệnh sẽ ném `MultipleObjectsReturned`. Nên khoá thêm `actor_kind`/nguồn "job" hoặc chỉ xét việc do job tạo. Để P9.
- N2: tranh chấp thật `cancel_receipt` ∥ `publish_batch` và `cancel_expired_batch` ∥ `reserve` mới chỉ được chứng minh bằng việc đọc code và spy. Khi QA có môi trường PostgreSQL (staging) thì chạy thử hai request song song một lần.
- Chữ trong 02b/02 cần điều phối viên nhờ sửa: 02b §3.4 (`code` thành `text`), SR-09 ma trận ("200" thành "201"), SR-08-AC2 ("PAID" thành "PROCESSING").

## Lô 4

Phạm vi: SR-12 (chứng từ đảo doanh thu), SR-13 (báo cáo lô/kỳ/dashboard trừ chứng từ đảo), SR-14 (lệnh lập bù). Diff chưa commit gồm 14 file sửa và các file mới `sales/models/credit_notes.py`, `sales/credit_notes/`, `sales/migrations/0011_salescreditnote.py`, `sales/management/commands/backfill_credit_notes.py`, `reports/tests/test_p8_pnl_credit_note.py`.

### Kết luận: **REVIEW FAIL — CẦN SỬA 1 lỗi (Medium, rò giá vốn ở Admin)**
Phần nghiệp vụ và công thức tiền đúng 02b §4. Lỗi duy nhất phải sửa là inline Admin để lộ `unit_cost` cho người không có `view_costprice`, trái với 02b §4.2, SR-12-AC8 và bất biến 1. Hiện chưa có nhóm nào được cấp quyền xem model này nên chưa khai thác được, nhưng lời "Admin ẩn `unit_cost`" trong dev-notes là sai và không có test nào bảo vệ. Sửa xong M1 (kèm test) thì PASS, không cần review lại toàn lô. Ngoài ra có 1 điểm tiền (D1) cần Duy quyết. D1 không chặn lô.

### Lệnh kiểm chứng đã chạy trong lượt review
- `DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.sales apps.reports` → `Ran 381 tests … OK`.
- `makemigrations --check --dry-run` → `No changes detected`.
- Probe Admin (script ở scratchpad, DB test): user `is_staff` chỉ có `sales.view_salescreditnote` + `view_salescreditnoteline`, **không** có `inventory.view_costprice`:
  - `/admin/sales/salescreditnote/<id>/change/` → 200, có cột `Giá vốn ảnh chụp (đ/kg)` và ô `<td class="field-unit_cost"><p>110000,0000</p>` → **rò**.
  - `/admin/sales/salescreditnoteline/<id>/change/` và danh sách → không có `unit_cost` (đúng).
- Probe kỳ (DB test): hoá đơn 300.000 ở tháng trước, phiếu hoàn một phần 50.000 xác nhận ở tháng trước, rồi huỷ đơn ở tháng này. `period_pnl(tháng trước)` trước khi huỷ: `refunds=50000, profit=30000`; sau khi huỷ: `refunds=0, profit=80000`. Kỳ tháng này: `revenue=-300000, profit=-80000`. Xem D1.

### Đối chiếu từng điểm
**Công thức (02b §4.4)**
- `batch_pnl` (`reports/services.py:56-63`): doanh thu gộp vẫn lấy phân bổ của hoá đơn chưa huỷ như cũ, rồi trừ Σ dòng chứng từ của lô (`credit_note__sales_invoice__status=ISSUED`). `qty_sold` trừ `reversed_qty`. Bán lại kg đã hoàn tạo phân bổ mới nên chỉ được cộng một lần (SR-13-AC2 có test). Không trừ hai lần: hoá đơn CANCELLED đã bị loại ở vế gộp và cũng bị loại ở vế đảo. Phần chi phí không đổi, đúng vì chi phí lô tính theo kg nhập.
- `period_pnl` (`:141-182`): `revenue = Σ hoá đơn trong kỳ − Σ cn.amount (issued_at ∈ kỳ)`; `cogs −= Σ qty × unit_cost` của dòng chứng từ. Số này khớp đúng giá vốn đã cộng lúc bán, vì dòng chứng từ chép nguyên `silb.qty`/`silb.unit_cost`. Hoá đơn gốc không bị sửa nên doanh thu/giá vốn của kỳ hoá đơn giữ nguyên (SR-13-AC3 có test). Phiếu hoàn của hoá đơn đã có chứng từ bị loại (`:168`), đúng văn bản 02b. Xem D1 cho ca biên.
- `revenue_today` (`dashboard_api.py:63`): trừ `SalesCreditNote.amount` có `issued_at__date=today`. Không lọc trạng thái hoá đơn vẫn đúng, vì chứng từ chỉ được lập cho hoá đơn ISSUED và hoá đơn không bao giờ bị chuyển CANCELLED (grep không có chỗ nào gán `SalesInvoice.Status.CANCELLED`).

**Service & mọi đường huỷ**
- `issue_cancel_credit_note` được gọi ở `orders/services.py:404`, bên trong `with transaction.atomic()` và sau khi đã `select_for_update` đơn. Lỗi trong service làm rollback cả lần huỷ (AC5 có test patch ném lỗi).
- Chỉ có ba nơi gọi `cancel_paid_order`: `orders/api.py:144` (huỷ tay), `delivery/cskh/services.py:624` (quyết định CANCEL), `:786` (`auto_cancel_overdue`). Dòng `:705` chỉ là docstring. AI chỉ khai `sales.cancel_paid_order` trong policy, không có đường thực thi riêng. Không có code nào khác đổi đơn sang CANCELLED.
- Idempotent: dùng `source_key="cancel:<order.pk>"` (unique) và đọc trước khi tạo. `code` unique, `DC-` + tối đa 32 ký tự thì vừa `max_length=40`. Hai lần huỷ đồng thời được khoá đơn xếp hàng. Nếu lệnh lập bù chạy tranh với một lần huỷ tay thì ràng buộc unique sẽ chặn.
- Append-only: `default_permissions=("view",)` cho cả hai model. Không có `.update/.delete` (có test quét mã nguồn). Admin trả `has_add/change/delete=False`. Migration 0011 chỉ có 2 `CreateModel` + 1 `AddIndex`, FK đều `PROTECT` (trừ dòng → chứng từ là `CASCADE`, chấp nhận vì chứng từ không xoá được).

**Không rò giá vốn / PII**
- Không có serializer hay API mới. Timeline (`timeline.py:151`) chỉ có mã chứng từ và `cn.amount` (giá bán). AuditLog `issue_credit_note` (`credit_notes/services.py:56`) ghi `credit_note`, `amount` (giá bán) và `backfilled`, không có khoá giá vốn và không có PII (có test sentinel). Output lệnh lập bù (`backfill_credit_notes.py:70`) chỉ có mã đơn, mã hoá đơn, số tiền bán và mã lô (có test sentinel + chuỗi giá vốn ở cả 3 lần chạy).
- **Admin inline rò `unit_cost`, xem M1.**

**Spec (02b §4.6)**: BR-HT-06, BR-HT-10, BR-BC-03, BR-BC-04 và bảng 12.1 trong `doc/business-process-spec.md` chép đúng văn bản, có ghi "Duy duyệt 30/09". Docstring của `cancel_paid_order`, `confirm_refund` và module `reports/services.py` đã cập nhật (SR-13-AC7).

### Chốt 6 lệch be-dev nêu
1. **Sửa `test_privacy_consent.py::test_gl03_ac7…`: chấp nhận.** Test này là "danh bạ" model của app `sales`, dùng để chặn việc thêm bảng thu dữ liệu cá nhân mà không ai hay. Hai model mới không có field cá nhân nào (đã đọc model), nên thêm 2 tên kèm chú thích đúng là mục đích của test. 02c thiếu file này là do thiếu sót của techlead.
2. **Bộ khoá `batch_pnl` 16 → 18: chấp nhận.** Chỉ thêm khoá theo 02b §4.4. Test mẫu vẫn chứng minh nhóm khác Chủ nhận 403.
3. **Ghi audit khi lập bù: chấp nhận, nên giữ.** Có dấu vết `actor=None`, `backfilled=true`. `AuditLog.created_at` là lúc chạy lệnh, còn `issued_at` của chứng từ mới là mốc nghiệp vụ, đúng thiết kế.
4. **Kỳ dùng `cn.amount`, lô dùng Σ dòng: chấp nhận.** Mỗi báo cáo đảo đúng thứ nó đã cộng (kỳ cộng `invoice.amount`, lô cộng Σ `qty × rate`), nên sau huỷ cả hai về đúng 0, không lệch. Hai báo cáo vốn đã có thể lệch nhau vì làm tròn BR-BH-15 (12.1 đã ghi "có thể lệch nhẹ"). Có thêm lệch dưới 1 đồng do `SalesCreditNoteLine.amount` bị làm tròn 2 số lẻ khi lưu (`credit_notes/services.py:53`, `qty` 3 số lẻ × `rate`), không đáng kể.
5. **`cogs_reversed` cho mọi dòng kể cả `stock_restored=False`: chấp nhận, đúng giả định 🟡(5) ở 02b §10.** Hàng giao thất bại quay về theo P-08: nhập lại rồi bán lại thì phát sinh giá vốn mới ở kỳ bán; nếu huỷ bỏ thì lỗ nằm ở `batch_pnl`, còn `period_pnl` chưa tính lỗ hỏng (để sau). Duy vẫn có thể lật giả định này.
6. **Combo `qty × rate` lệch sẵn: chấp nhận, là nợ có sẵn và ngoài phạm vi.** Dòng chứng từ sao đúng công thức cũ nên sau huỷ lô vẫn về đúng mức trước bán. Đưa vào backlog, không sửa ở Lô 4.

### Việc sửa
| # | Mức | File:dòng | Việc |
|---|---|---|---|
| M1 | **Medium (bắt buộc trước commit)** | `backend/apps/sales/admin.py:132-137` | Inline khai `fields` tường minh có `unit_cost`, lại thêm `has_change_permission=False`, nên Django đưa mọi field trong fieldset thành chỉ đọc và hiện `unit_cost`. `CostHidingMixin` chỉ gỡ được ở `readonly_fields`/`exclude`. Cách sửa: bỏ dòng `fields = …` của inline, hoặc override `get_fields` để lọc `cost_fields` khi `not self._can_see_cost(request)`. Nên thêm `get_fields` vào chính `CostHidingMixin` (`inventory/admin.py:16`) để mọi Admin khai `fields` đều an toàn. Thêm test: staff có `view_salescreditnote(+line)` nhưng không có `view_costprice`, GET `/admin/sales/salescreditnote/<id>/change/` → 200, không có `unit_cost` và không có chuỗi giá vốn; superuser thì thấy. Suite cũ phải xanh. |
| L1 | Low | `erp-console/features/orders/types.ts:90-102` | Thêm `"credit_note_issued"` vào union kind và một dòng `TIMELINE_LOOK` (`OrderDetailView.tsx:86`). Hiện FE rơi về `TIMELINE_DEFAULT` nên không vỡ. Gộp vào Lô 6/7. |
| L2 | Low (tuỳ chọn, trước khi Duy chạy `--apply`) | `backend/apps/sales/management/commands/backfill_credit_notes.py:70` | Dry-run in thêm **tháng huỷ** (tháng của `issued_at` sẽ dùng) và **tháng xác nhận phiếu hoàn** của từng đơn, để Duy thấy kỳ cũ nào sẽ đổi số (xem D1). Chỉ in tháng, không in tiền giá vốn. |

### Cần Duy quyết (tiền) — D1, không chặn Lô 4
**Kỳ cũ có thể đổi số trong một ca hiếm.** Chủ hoàn **một phần** cho hoá đơn (ví dụ giảm giá 50.000) và xác nhận trong tháng 9, rồi tháng 10 huỷ luôn đơn đó. Công thức hiện tại (theo đúng 02b §4.4 do techlead viết) loại **mọi** phiếu hoàn của hoá đơn đã có chứng từ, nên phiếu 50.000 bị gỡ khỏi tháng 9 (lãi tháng 9 tăng từ 30.000 lên 80.000). Tháng 10 bị đảo đủ 300.000. **Tổng hai tháng vẫn đúng** (0 đồng, không trừ hai lần), nhưng số tháng 9 đã báo thì đổi, trái với tinh thần BR-BC-03 "không sửa kỳ cũ". Lệnh lập bù SR-14 cũng gây hiệu ứng này cho các đơn huỷ trước P8 đã có phiếu hoàn ở tháng khác tháng huỷ.
- **Phương án A (giữ nguyên):** chấp nhận, vì ca này hiếm và tổng luôn đúng. Ghi thêm một câu vào BR-HT-06.
- **Phương án B (techlead khuyên):** chỉ loại phiếu hoàn có `confirmed_at ≥ issued_at` của chứng từ. Ở kỳ huỷ, số đảo doanh thu = `cn.amount − Σ phiếu hoàn REFUNDED xác nhận trước lúc huỷ`. Kỳ cũ giữ nguyên, tổng vẫn đúng. Chỉ sửa `period_pnl` và thêm 1 test, `batch_pnl` không đổi. Làm thành story nhỏ ở Lô 7, hoặc sửa cùng M1 nếu Duy chọn trước khi commit.

### Ghi chú
- Chưa có nhóm nào được cấp `view_salescreditnote`, nên hiện chỉ superuser mở được Admin chứng từ. Chủ muốn xem trong ERP thì cần màn hình riêng (theo nguyên tắc "làm xong ở ERP"). Việc này ngoài phạm vi Lô 4 (02b §4.1 đã chốt không có API), đưa vào backlog.
- `period_pnl` có thể âm ở kỳ huỷ (đúng thiết kế). FE báo cáo kỳ và dashboard nên hiển thị được số âm, QA cần kiểm ở lô FE sau.

## Lô 4 — lần 2

Phạm vi: 3 thay đổi sau review lần 1, gồm M1 (Admin inline ẩn `unit_cost`), D1 phương án B (`period_pnl`) và E1/E2 (lập bù ghi vào kỳ chạy lệnh, `batch_pnl` lô đã chốt chỉ trừ chứng từ lập trước `closed_at`). Diff vẫn chưa commit.

### Kết luận: **CẦN SỬA — 1 lỗi nhỏ, chỉ ở test (T1)**
Công thức tiền đạt ở mọi đường đã soát. Kỳ đã qua và lô đã chốt không đổi số, không trừ hai lần, tổng nhiều kỳ về đúng 0. M1 đã sửa đúng và có test bảo vệ. Chỉ còn lỗi T1: 4 test phụ thuộc giờ chạy nên đỏ trong khoảng 00:00–07:00 (giờ VN) ngày 1 mỗi tháng. Sửa T1 xong thì PASS, không cần review lại. Điều phối tự kiểm bằng probe dịch đồng hồ mô tả bên dưới.

### Lệnh kiểm chứng đã chạy trong lượt này
- `DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.sales apps.reports` (không --parallel): `Ran 395 tests … OK`.
- `makemigrations --check --dry-run`: `No changes detected`.
- Probe dịch đồng hồ, script ở scratchpad. Script vá `django.utils.timezone.now` thành giờ thật cộng một độ lệch cố định, rồi chạy test runner.
  - Đặt đồng hồ **2026-10-31 20:00 UTC**, tức 01/11 03:00 giờ VN. `apps.reports.tests.test_p8_pnl_credit_note` cho kết quả `FAILED (failures=4)`, cả 4 lỗi đều là `Decimal('0') != Decimal('250000'/'300000')` (xem T1). Chạy `apps.sales.credit_notes` ở cùng mốc thì `OK`.
  - Đối chứng ở mốc **2026-10-15 10:00 UTC**: chạy cả hai module cho kết quả `Ran 48 tests … OK`. Như vậy test dùng mốc cố định 2026-09/10 vẫn đúng khi chạy trong tháng 10.
- Probe tiền là file test tạm, đặt trong `apps/reports/tests/`, đã xoá sau khi chạy, `git status` sạch. Kết quả `Ran 4 tests … OK`, gồm 4 ca:
  - Đơn huỷ theo luồng cũ ở tháng 7, hoàn đủ ở tháng 8, lập bù bây giờ. Kỳ 7 và kỳ 8 không đổi ở mọi khoá. Kỳ hiện tại có `credit_notes=0`, `cogs_reversed=220000`, `profit=+220000`. Tổng 3 kỳ cho (doanh thu − hoàn) = 0, giá vốn = 0, lãi = 0.
  - Phiếu hoàn tạo trước lúc huỷ nhưng xác nhận sau lúc huỷ. Kỳ huỷ có `credit_notes=300000`, `refunds=0`. Tổng các kỳ bằng 0.
  - Phiếu hoàn và chứng từ có cùng timestamp. Phiếu bị loại, số đảo là 300000 đủ, tổng bằng 0, không trừ hai lần.
  - Hoàn trước lúc huỷ, cùng tháng với tháng huỷ. Kỳ đó có `credit_notes=250000` và `refunds=50000`, tổng bằng 0.

### Soát tiền theo từng đường
Ký hiệu: T = `cn.issued_at`, H = Σ phiếu hoàn REFUNDED có `confirmed_at < T` (`reports/services.py:170-178`).

| Đường | Kỳ đã qua | Kỳ chứa T | Lô | Kết quả |
|---|---|---|---|---|
| Huỷ thường, lô chưa chốt | Kỳ hoá đơn giữ doanh thu gộp. Phiếu hoàn trước T nằm ở kỳ xác nhận của nó | Đảo doanh thu `max(0, amount − H)`, đảo giá vốn toàn bộ dòng. Phiếu hoàn sau T bị loại | Trừ | Đạt |
| Huỷ trước khi chốt, rồi mới chốt | như trên | như trên | `issued_at ≤ closed_at` nên vẫn trừ, lô không đổi khi chốt | Đạt |
| Huỷ sau khi chốt | như trên | như trên | Không trừ, lô giữ nguyên (`services.py:64-67`) | Đạt (thực tế gần như không xảy ra, vì `close_batch` đòi lô không còn đơn mở) |
| Lập bù (E1) | Không đổi, vì T = lúc chạy lệnh nên mọi phiếu hoàn cũ có `confirmed_at < T` và vẫn nằm ở kỳ cũ | Nhận toàn bộ điều chỉnh | Lô chưa chốt thì trừ (số tạm tính). Lô đã chốt thì giữ nguyên | Đạt |
| Hoàn đủ trước lúc huỷ | Giữ nguyên | `credit_notes=0` (không âm), `cogs_reversed` đủ | — | Đạt |
| Cùng timestamp | — | Hai điều kiện `<` và `>=` bù trừ khít nhau: phiếu bị loại, số đảo đủ | — | Đạt |

- **Tổng nhiều kỳ:** gộp − H − (amount − H) = 0 khi H ≤ amount. Nếu H > amount thì `max(0)` chặn không cho số đảo âm, và khi đó phần hoàn vượt được ghi đúng là tiền đã rời túi.
- **Giá vốn và doanh thu ở kỳ hiện tại:** `period_pnl` luôn đảo cả hai vế trong cùng kỳ T. Với D1-B, doanh thu chỉ đảo phần còn lại, còn giá vốn đảo đủ. Cách này đúng, vì phiếu hoàn trước lúc huỷ chỉ là giảm giá hoặc trả tiền và không thu hàng về, còn huỷ mới là lúc thu hàng về. `batch_pnl` không có vế giá vốn bán (chi phí lô = giá mua + phân bổ), nên với lô đã chốt thì cả doanh thu lẫn `qty_sold` đều giữ nguyên và nhất quán với nhau. Kỳ và lô sẽ lệch nhau vĩnh viễn đối với lô đã chốt. Đây là hệ quả Duy đã chấp nhận (E2), và bảng 12.1 đã ghi "có thể lệch".
- **Lô CLOSED mà `closed_at` rỗng:** chỉ `close_batch` (`inventory/batches/services.py:261-264`) đặt CLOSED, và hàm này luôn đặt `closed_at`. `status` và `closed_at` bị khoá ở cả API (`batches/api.py` `locked_fields`) lẫn Admin (`LockedFieldsAdminMixin`). Không có đường mở lại lô. Vì vậy giả định "rỗng thì trừ như cũ" chỉ áp dụng cho dữ liệu tạo bằng tay, chấp nhận được. Nếu production có lô CLOSED từ trước khi có field này thì `closed_at` đã có từ `0001_initial` và `close_batch` luôn điền.
- **Rò giá vốn:** `get_fields` ở `sales/admin.py:139` lọc đúng. Test đỏ trước khi sửa và xanh sau khi sửa, có đối chứng superuser và user có `view_costprice`. `cogs_reversed` chỉ có trong `/api/reports/period/` (chỉ Chủ), và test AC6 đã quét khoá này với các nhóm khác. Không phát sinh đường rò mới.
- **Dashboard (`dashboard_api.py:63`):** trừ đủ `cn.amount`, không tính D1-B. Cách này nhất quán, vì dashboard không trừ phiếu hoàn.

### Việc sửa
| # | Mức | File:dòng | Việc |
|---|---|---|---|
| T1 | **Low, bắt buộc trước commit** vì làm suite đỏ theo giờ | `backend/apps/reports/tests/test_p8_pnl_credit_note.py:308`, `:362`, `:379`, `:418` | Các dòng này dùng `now = timezone.now(); period_pnl(year=now.year, month=now.month)`. `timezone.now()` trả giờ UTC, còn `period_pnl` lọc `issued_at__month` theo `TIME_ZONE=Asia/Ho_Chi_Minh`, nên từ 00:00 đến 07:00 giờ VN ngày 1 mỗi tháng thì tháng bị lệch và test đỏ (đã tái hiện bằng probe). Cách sửa là thay bằng `d = timezone.localdate()` rồi `period_pnl(year=d.year, month=d.month)`, giống test AC6 ở dòng 164. Cách kiểm: suite xanh, và probe dịch đồng hồ tới 2026-10-31 20:00 UTC cho `OK`. |
| L3 | Low, cần Duy biết trước khi chạy `--apply` | `backend/apps/reports/dashboard_api.py:63` | Vào ngày chạy `backfill_credit_notes --apply`, KPI "doanh thu hôm nay" bị trừ toàn bộ số tiền lập bù và có thể âm. Việc này đúng nguyên tắc E1, vì kỳ hiện tại nhận điều chỉnh. Nếu Duy muốn KPI vận hành không bị nhiễu thì lọc `backfilled=False` ở dashboard (`period_pnl` vẫn giữ). Tối thiểu cần ghi câu này vào hướng dẫn chạy lệnh trong 02c. |
| L4 | Low (backlog) | `backend/apps/reports/services.py:170-178`, `:194-199` | `period_pnl` bị N+1: mỗi chứng từ tốn 1 truy vấn phiếu hoàn, mỗi phiếu hoàn tốn 1 truy vấn chứng từ. Số lượng bản ghi nhỏ nên chưa ảnh hưởng. Khi cần thì gom bằng `Subquery`/`prefetch`. |

### Ghi chú
- 02b §4.4 (công thức) chưa phản ánh D1-B, E1 và E2. Techlead sẽ cập nhật 02b theo code hiện tại. 02-stories.md đã có ghi chú đổi AC dưới SR-14 (câu "chỉ trừ chứng từ lập trước `closed_at`" khớp với code `<=`, vì trùng timestamp chỉ xảy ra trong test).
- L1 và L2 của lần 1 vẫn còn hiệu lực. L2 đã được làm một phần: dry-run đã liệt kê riêng lô CLOSED, nhưng chưa in tháng huỷ hay tháng hoàn. Với E1 thì L2 không còn cần thiết, vì lập bù luôn ghi vào kỳ hiện tại.

## Lô 5
> Techlead · 2026-09-30 · Diff chưa commit (`git diff` + file chưa track). Story SR-15, SR-16, SR-17 (+F11).

### Kết luận: **CẦN SỬA — 2 lỗi Low, chỉ ở test (T5-1, T5-2). Code BE/FE đạt.**
Sửa xong 2 test thì Lô 5 PASS, không cần review lại code. Riêng M5-1 (mock lọt bản build thật) là lỗi **có từ trước** (commit `18406ce`, 27/09),
không thuộc diff Lô 5 và không chặn Lô 5, nhưng chặn lần deploy ERP kế tiếp (runbook yêu cầu `grep demo1234 out` = 0).

### Lệnh kiểm chứng đã chạy trong lượt review
- `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.inventory apps.reports apps.delivery apps.ai` → `Ran 547 tests ... OK`.
- `manage.py makemigrations --check --dry-run` → `No changes detected`.
- `cd erp-console && npm test` → `Test Files 10 passed`, `Tests 103 passed`.
- Quét `erp-console/out/` (bản build thật hiện có): chuỗi mock riêng của `features/inventory/mock.ts`, `overview/mock.ts`, `dashboardSummary.mock.ts` = 0.
  Chuỗi mock của `features/auth/mock.ts` (123/139 chuỗi, gồm `password:"demo1234"`, SĐT giả `0909000222`) và `features/catalog/mock.ts` (29/38) **có** trong
  `out/_next/static/chunks/2800-*.js` (nạp ở `/catalog/`, `/purchasing/`). Xem M5-1.

### Đối chiếu từng điểm
| Điểm | Kết quả |
|---|---|
| Migration `inventory/0004` | Đúng 2 operation: `AlterField(movement_type)` thêm `SUPPLIER_RETURN` (15 ký tự, `max_length=16` giữ nguyên) + `CreateModel(BatchSupplierReturn)` (`default_permissions=("view",)`, FK `PROTECT`, `request_id` unique). Không có thay đổi ngoài 2 model. Khớp 02b §5.2. |
| `supplier_refund_amount` không lọt | Response 200/400/403 không có tiền (test sentinel `1234567`). AuditLog: khoá nằm trong `changes`, thuộc `COST_KEYS` (`common/cost_keys.py:19`), `note` audit chỉ ghi kg. Không đăng ký Admin. `BatchSerializer` không thêm field. AI: lệnh `return_to_supplier` trần C + `force_c`; `AiAction.args` qua `scrub_data` lọc `SCRUB_COST_KEYS`; registry chỉ lộ tên field trong schema, không lộ giá trị. `batch_pnl` chỉ Chủ (`view_profitreport`). Đạt. |
| `total_cost`, landed cost, `period_pnl` | `total_cost = purchase_cost + allocated_cost − Σ tiền NCC hoàn` (`reports/services.py`). `landed_unit_cost`, `recompute_landed_cost`, `period_pnl` không đổi (diff không đụng). Đạt. |
| Quy tắc Duy 30/09 (lô đã chốt không đổi số) | Trả NCC từ chối lô chốt (`check_process_expired_stock` → BR-LO-05), nên `total_cost`/`profit` của lô CLOSED không đổi. Logic Lô 4 (`closed_at`) giữ nguyên. Riêng F11 đổi con số **hiển thị** `expired_qty`/`expired_cost` của lô cũ có `WRITE_OFF` do huỷ phiếu nhập. Hai khoá này không cộng vào `total_cost` (TL-4), nên `profit` không đổi. Xem D5-1. |
| F11 `expired_qty` | Lọc `reference__startswith="cancel_expired_batch "`. Chuỗi reference này có từ commit `c0c4272` và chưa đổi lần nào, nên dữ liệu cũ vẫn đếm đúng. `ReturnToStock` WRITE_OFF ghi `qty_change=0` nên trước đây cũng không bị đếm. Đạt. |
| Kho: `SUPPLIER_RETURN` âm, khoá lô | `select_for_update` lô trước mọi phép kiểm; `record_movement(-qty)` khoá lại và chặn âm. Đạt. |
| `request_id` idempotent | Kiểm sau khi khoá lô, nên hai request cùng lô được xếp hàng và request sau thấy bản ghi của request trước (READ COMMITTED đọc lại ở câu lệnh mới). Mã dùng cho lô khác → 400 BR-MH-08 (`services.py:399`), nhưng **chưa có test** (T5-2). Ca lý thuyết: hai request cùng UUID trên hai lô khác nhau chạy đồng thời thì request sau gặp `IntegrityError` → 500. UUID do FE sinh theo từng form nên ca này không xảy ra thực tế. Ghi nhận, không sửa. |
| Tranh chấp với giữ chỗ / huỷ | Còn giữ chỗ → cả hai xác nhận bị chặn (BR-LO-07, `_check_expired_reserved`). Trả NCC ↔ huỷ lô: cùng khoá dòng lô. Huỷ trước thì trả gặp `CANCELLED` → 400. Trả trước thì huỷ có `confirm_qty` cũ → 400 "Tồn đã đổi". Lô EXPIRED không nằm trong `sellable_batches` nên không phát sinh giữ chỗ mới. Đạt. |
| BR-LO-04 gỡ ngoại lệ | `check_close_batch`: `if batch.qty_available > ZERO` → BR-LO-04 với mọi trạng thái. `check_ai_close_batch_conditions` (`ai/execution/safety.py:38`) gọi lại `check_close_batch` nên tự chặn, nhưng **chưa có test** cho vế "luật sàn AI" của SR-15-AC1 (T5-1). Lô CANCELLED tồn 0 vẫn chốt được. Đạt. |
| Attention 403 / khoá mới | `attention_api.py:36-38`: 403 chỉ khi thiếu cả 4 quyền. `expired_batches_open` chỉ trả cho người có `inventory.cancel_expired_batch`, và chỉ là số đếm. Có test cho các ca: chỉ có quyền này thì 200, `quan_ly` không có khoá, `nv_giao` 403, khách 401. Đạt. |
| Dashboard `recent_orders` | Còn đúng 5 khoá `{code, amount, status, status_label, expires_at}`, bỏ `select_related("customer")`, không rẽ nhánh theo nhóm. Test so tập khoá cho chu/quan_ly/nv_kho và quét tên, SĐT, `0456`. Đạt. Các khối khác (`batches`, `alerts`, `activity`) không có dữ liệu khách. `reference` của `SUPPLIER_RETURN` là `supplier_return SR-<id>`, không có tiền. |
| Phân quyền | Action có `required_perms` + `require_perm` + `custom_perm_actions` (Tầng 1+2). Ma trận 5 nhóm + 401 + 404 có test. Không có quyền mới, không có migration Group. Đạt. |
| FE: không lộ tiền hoàn | `ReturnToSupplierResult` không có tiền. Thông báo sau khi lưu chỉ nêu kg. Ô tiền chỉ nhận chữ số, tối đa 12 ký tự (< 10^12, khớp giới hạn BE). Đạt. |
| FE: `confirm_qty` | Hộp "Đã huỷ phần tồn" ghi lại `confirmQty` lúc mở, nêu số kg đó, rồi gửi `decimalKg(confirmQty)`. Lỗi 400 BR-LO-07 hiện `detail` kèm nút "Tải lại". Đạt. |
| FE: chặn bấm đúp | Form trả NCC chặn bằng `submitting` ref cộng nút bị khoá, và `request_id` giữ nguyên suốt phiên form. Hộp huỷ/chốt chỉ chặn bằng state `busy` (`BatchDetailSheet.tsx:105`). Nếu bấm lần hai trước khi React vẽ lại thì request thứ hai nhận 400 (lô đã `CANCELLED`/`CLOSED`), không ghi thêm gì. Low, xem L5-2. |
| FE: Tổng quan không PII | Đã bỏ cột "Khách", bỏ `customer` khỏi `matches`, đổi `RecentOrder` type, mock seed hết tên và SĐT. Vitest quét tên. Đạt. |
| FE: mock lọt build | Các hàm mới của Lô 5 dùng `process.env.NEXT_PUBLIC_USE_MOCK === "1"` viết thẳng tại chỗ, và bản build thật không còn chuỗi mock inventory/overview. Rà các feature khác: `features/content/api.ts:48` (`const isMock` cấp module) và `auth/components/LoginScreen.tsx:16` (`const MOCK`) **không** lọt (terser gập được hằng trong cùng module). `features/catalog/api.ts:5,28,47` dùng `USE_MOCK` **import** từ `shared/lib/http.ts:16` thì terser không gập được, nên cả `catalog/mock.ts` lẫn `auth/mock.ts` (catalog mock import auth mock) lọt vào bản thật. Xem M5-1. |

### Chốt các lệch be-dev và fe-dev nêu
| # | Lệch | Quyết định |
|---|---|---|
| a | `test_cancel_expired.py::test_dw06_ac6_guidance_next_steps_expired_then_cancelled` đổi nhãn và `close` luôn hiện | **Đã chạm điểm dừng theo câu chữ**: test cũ ngoài S04 đỏ vì bỏ ngoại lệ EXPIRED ở tầng Tiếp theo. Tuy vậy assert mới đúng từng chữ với 02b §5.3 ("bỏ điều kiện `status != EXPIRED` ở bước 4") và SR-15-AC3 (nhãn, `close` `allowed=false` + BR-LO-04), không nới kiểm tra nào, và dev đã báo thay vì lặng lẽ sửa. **Chấp nhận**, không cần Duy quyết. Điểm dừng nhằm bắt hành vi *ngoài thiết kế* bị đổi, còn ca này là hành vi thiết kế yêu cầu đổi. |
| b | 3 test ngoài danh sách 02c (`test_discipline.py` 23→24, snapshot registry, `test_cskh_l4 cs15_ac1` +khoá) | **Chấp nhận.** Đây là hệ quả cơ học, trực tiếp của action và khoá mới trong 02b §5.4. Không nới điều kiện nào: `required_perms` vẫn bắt buộc, snapshot chỉ thêm 1 lệnh, tập khoá vẫn so bằng `assertEqual(set)`. Lỗi nằm ở danh sách file của 02c (techlead bỏ sót), không phải lỗi dev. |
| c | Serializer đầu vào dùng chuỗi lỏng | **Chấp nhận.** Service là lớp kiểm thật (`_parse_decimal` loại NaN/Infinity/bool, kiểm số lẻ), nên mọi lỗi đều về một dạng 400 `{code: BR-MH-08}`. Schema AI mô tả field là chuỗi, và vì lệnh ở trần C nên chỉ soạn nháp, không gây rủi ro. |
| d | Chặn số lẻ (>3 kg, >2 tiền) và tiền ≥ 10^12 | **Chấp nhận.** Tránh 500 do vượt `max_digits`, và nhất quán với cột. |
| e | `cancel_expired` không gắn `input_serializer` | **Chấp nhận.** Giữ nguyên registry/snapshot (lệnh `form_only`). `confirm_qty` là tuỳ chọn, nên lệnh AI không gửi thì hành vi vẫn như cũ (đúng SR-15-AC5 "giữ tương thích lệnh AI"). |
| FE-1 | Sửa `shared/lib/dashboardSummary.ts` + `.mock.ts` | **Chấp nhận, bắt buộc phải sửa.** `RecentOrder` là type dùng chung, nếu không sửa thì FE vẫn khai `customer`. 02b §5.7 ghi thiếu file này. |
| FE-2 | `features/guidance/mock.ts` và `features/overview/mock.ts:7` import `features/inventory/mock` | **Chấp nhận tạm** (chỉ là mock, và đã kiểm là không lọt bản thật). Cách này trái quy tắc "module không import ruột module khác". Nên chuyển state lô quá hạn giả sang `shared/lib/expiredBatches.mock.ts` khi có đợt sửa FE sau (L5-3). |
| FE-3 | Danh sách EXPIRED chỉ lấy trang 1 (50 dòng), lọc tồn > 0 ở FE, không có tên mặt hàng/NCC | **Chấp nhận cho Lô 5, ghi nợ L5-1.** Lô EXPIRED tồn 0 chưa chốt vẫn giữ trạng thái EXPIRED. Khi số lô loại này nhiều lên, trang 1 có thể toàn lô tồn 0, và danh sách sẽ ít dòng hơn con số trên thẻ. |

### Việc sửa
| # | Mức | File:dòng | Việc |
|---|---|---|---|
| T5-1 | **Low, trước commit** (AC chưa có bằng chứng) | `backend/apps/inventory/batches/tests/test_p8_lo5_expired_return.py` (lớp `SR15CloseExpiredTests`) | SR-15-AC1 yêu cầu "luật sàn AI chốt lô (DW-25) cũng chặn". Thêm test: lô EXPIRED còn 3 kg, gọi `apps.ai.execution.safety.check_ai_close_batch_conditions(batch)` → `ok is False` và `reason["text"]` chứa "tồn = 0". Kế thừa fixture của `test_p8_close_batch_sold.py:78`. |
| T5-2 | **Low, trước commit** | cùng file (lớp `SR16ReturnToSupplierTests`) | Test cho nhánh `services.py:398-399`: Chủ trả NCC ở lô A với `request_id=X` (200), rồi gửi `request_id=X` cho lô B (EXPIRED, còn tồn) → 400 `BR-MH-08`. Tồn lô B và số `BatchSupplierReturn` của lô B không đổi. |
| M5-1 | **Medium, có từ trước** (không thuộc Lô 5), phải sửa trước lần deploy ERP kế tiếp | `erp-console/features/catalog/api.ts:5`, `:28`, `:47` | Thay `USE_MOCK ? mockX : undefined` bằng `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockX : undefined` viết thẳng tại chỗ (mẫu của Lô 5). Cách kiểm: `npm run build` (bản thật), sau đó `grep -rl "demo1234\|mock-token-\|cave_erp_mock_users" out` phải = 0 (runbook `2026-09-24-erp-console-noi-that/05-deploy-1-runbook.md:50`). Tuỳ chọn: bỏ `export` của `USE_MOCK` ở `shared/lib/http.ts:16` để không ai import lại. Hiện `out/_next/static/chunks/2800-*.js` chứa danh sách tài khoản mock, mật khẩu `demo1234` và SĐT giả. Đây không phải dữ liệu thật và backend không dùng mật khẩu này, nhưng trái quy ước build sạch và làm lộ cấu trúc quyền. |
| L5-1 | Low (backlog Lô 7) | `erp-console/features/inventory/api.ts:67-75`; `backend/apps/inventory/batches/serializers.py:28` (`BatchListQuery`) | BE thêm tham số `has_stock=1` (lọc `qty_available__gt=0`) và các khoá tên (`item_name`, `supplier_name`, `warehouse_name`, `status_label`) cho danh sách lô. FE bỏ lọc phía máy. |
| L5-2 | Low (backlog) | `erp-console/features/inventory/components/BatchDetailSheet.tsx:104-105` | `runSimple` nên chặn bấm đúp bằng `useRef` như `ReturnToSupplierDialog`. Hiện tại lần bấm thứ hai chỉ nhận 400 vô hại. |
| L5-3 | Low (backlog) | `erp-console/features/overview/mock.ts:7`, `erp-console/features/guidance/mock.ts:5` | Chuyển state mock lô quá hạn lên `shared/lib/`. |
| L5-4 | Low (backlog, ngoài phạm vi) | `backend/apps/inventory/batches/timeline.py:50-66`; `backend/apps/ai/execution/safety.py:23` | Thêm nhãn "Trả NCC" cho `SUPPLIER_RETURN` trong Sổ chi tiết. Sửa docstring "tồn = 0 hoặc EXPIRED/CANCELLED" (dev đã ghi nợ). |

### Cần Duy quyết / biết
- **D5-1 (biết, không chặn):** F11 (SR-15-AC6, Duy đã duyệt) làm đổi **số hiển thị** "kg hết hạn / tiền hết hạn" của lô **đã chốt** nếu lô đó có phần tồn bị xoá do huỷ phiếu nhập (trước đây bị đếm nhầm là hết hạn, nay về 0). **Lãi lỗ và tổng chi phí của lô đó không đổi**, vì hai số này chỉ để hiển thị và không cộng vào chi phí. Techlead đề nghị giữ nguyên, vì đây là sửa nhãn sai, không phải đổi con số lời lỗ. Nếu Duy muốn giữ đúng từng chữ quy tắc "lô đã chốt không đổi số" thì dev có thể áp F11 chỉ cho lô chưa chốt (`closed_at` rỗng).
- **M5-1:** sửa theo luồng NHANH riêng, hoặc gộp vào commit Lô 5. Techlead đề nghị gộp vào Lô 6 (lô FE), nhưng phải sửa trước mọi lần deploy ERP.

### Ghi chú
- 02b §5.7 và 02c dòng Lô 5 thiếu các file `shared/lib/dashboardSummary*.ts`, `ai/registry/tests/*`, `delivery/tests/test_cskh_l4.py`. Đây là thiếu sót của techlead, không phải lệch do dev.
- Ô ghi chú ở FE chặn `\d{8,}`, còn BE dùng `has_long_digit_run` (≥ 9 chữ số, tính cả khi có dấu cách). Hai bên lệch nhau nhưng vô hại, vì BE mới là lớp chặn thật.

## Lô 6
Review diff chưa commit (`git diff` + file chưa track): SR-18 BE, SR-19/SR-20 FE ERP, M5-1b/B2 FE Shop, 2 script kiểm. Ngày 2026-09-30.

### Kết luận: **CẦN SỬA — 1 High (F6-1), 1 Medium (F6-2) ở FE ERP. BE SR-18, SR-19, M5-1b Shop đạt.**
QA Lô 6 chưa APPROVED toàn lô (Shop lần 1 REJECTED vì B1 nay đã sửa; CS-11-AC6, X-AC4 còn ⏸). Sau khi sửa F6-1/F6-2 cần QA chạy lại phần ERP.

### Lệnh kiểm chứng đã chạy trong lượt review
```
backend  DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.content   -> Ran 133 tests OK
erp      npm test                                                                          -> 103 passed (103)
erp      grep seed mock nội tuyến (uuid mockAiActions, "MOCK-01", "mock-action-read", "Cá thu Phan Thiết 1kg") trong out/ (bản thật, API_BASE run.app) -> 0 tệp
erp      grep "demo1234|mock-token-|cave_erp_mock_users" out/                               -> 0 tệp (M5-1 của Lô 5 đã hết)
django   lookups.py: IntegerField ngoài miền -> EmptyResultSet (Django 5.1.15), nên cover_image/image_id cực lớn -> 400, không 500
```
Không chạy `npm run build` (điều phối đang build).

### Đối chiếu từng điểm
| Điểm | Kết quả |
|---|---|
| SR-18 tạo bài | `services.py:167-168` và `sanitize.py:172-174`: `entry is None` + có ảnh (bìa hoặc khối) -> 400 BR-ND-07 "Tải ảnh sau khi lưu nháp lần đầu." trước khi tạo gì. Không lộ ảnh có tồn tại hay không (mọi id đều cùng thông điệp). Đạt AC1. |
| SR-18 sửa bài | Bìa lọc `pk=…, entry_id=entry.pk`; ảnh bài khác và ảnh không tồn tại cùng một thông điệp (chống dò id). Khối ảnh lọc `entry_id=entry.pk`. Kiểm `row_version` (409) chạy trước kiểm ảnh. Đạt AC2, AC4 (giới hạn đếm trên ảnh đã được xác nhận thuộc bài). |
| SR-18 `_as_pk` | bool, số âm, 0, danh sách, dict, chuỗi không phải số -> None -> 400. Chuỗi số -> int. Số cực lớn -> Django trả rỗng -> 400. Khối ảnh với `image_id` không phải int vẫn bị bỏ như cũ (`sanitize.py:165`). Đạt. |
| SR-18 lớp 1b công khai | `public_body` lọc `entry_id=version.entry_id`; `_own_cover` dùng cho cả chi tiết lẫn danh sách; `pages/by-role` đi qua `PublicEntryDetailSerializer` nên cũng được che. Test quét chi tiết + danh sách + footer không có `content/<A>/`, `image_id` (path), `alt` của ảnh nháp bài A. Không còn chỗ công khai nào khác đọc `cover_image`/`ContentImage` (đã grep `apps/content`). Đạt AC3. |
| SR-18 ma trận quyền | chu/quan_ly 201/200, nv_kho/nv_giao/cskh 403, khách 401; nhóm không quyền gửi ảnh bài khác nhận 403, không lộ "BR-ND-07". Đạt. |
| SR-19 | `version` chỉ nhận `^\d{1,9}$` > 0; panel chỉ đọc (không nút sửa/khôi phục), nội dung render bằng React, link đi qua `safeHref`, không `dangerouslySetInnerHTML`. 404 -> "Không tìm thấy phiên bản N" + "Về bài"; 403 có thông điệp riêng. URL chỉ `id` + `version`. `nv_kho` không thấy link (giữ nguyên `OrderDetailView`). Đạt AC1–AC3. Mock chính sách 2 phiên bản là chữ bịa. |
| SR-20 chunk | `GuidancePanel` không còn import tĩnh runtime/`commands/call`/`ai/api`; `wllamaMissing` chuyển sang `runtime/messages.ts`; `check-ai-chunks.mjs` XANH (điều phối chạy). Đạt AC1, AC4. |
| SR-20 hành vi | **Không đạt** ở 2 chỗ, xem F6-1, F6-2. |
| M5-1b Shop | `lib/api.ts`, `features/content/api.ts`, `features/site/api.ts` bỏ import tĩnh `./mock`, dùng `await import("./mock")` trong nhánh literal; `MockGatewayPanel` chỉ tạo khi literal mock. Còn đúng 1 import tĩnh `lib/mock` ở `MockGatewayPanel.tsx:11`, file này chỉ được nạp qua nhánh đã bị cắt. Đã grep toàn `frontend/app features lib components`: không còn đường import mock nào khác. Đạt. |
| M5-1b ERP | `features/content/api.ts`: bỏ `const isMock`, literal tại chỗ; `fetchShopCatalog` bọc điều kiện. Các `features/*/api.ts` khác import tĩnh `./mock` nhưng mọi chỗ dùng đều nằm sau literal, và bản thật hiện tại không chứa seed (script + grep canary nội tuyến ở trên). Đạt. |
| B2 | `recallOrderContact` chỉ trả `phone_last4` khớp `^\d{4}$`. Đạt. |
| PII / giá vốn / phân quyền | Không field mới, không serializer mới ở BE; API công khai chỉ bớt dữ liệu. FE không ghi gì mới vào storage/URL (cờ đồng ý AI là boolean có sẵn). Không đụng giá vốn, chứng từ. Không migration (diff BE không có `models/`/`migrations/`). Đạt. |

### Chốt câu hỏi điều phối nêu
1. **SR-18: `restore_entry_version`/`discard_changes`/`publish_entry` không kiểm lại ảnh — không siết trong lô này.** Ba đường này chỉ nạp lại dữ liệu *đã lưu* của chính bài (phiên bản lọc `entry=entry`), không nhận id ảnh từ người dùng, nên không mở lối IDOR mới. Dữ liệu cũ trước SR-18 trỏ ảnh bài khác thì phía công khai đã che (lớp 1b), còn phía ERP người xem vốn có quyền content trên mọi bài nên không vượt quyền. Ghi nợ L6-1 (Low) để phòng thủ nhiều lớp.
2. **`gate-state.ts` + sửa `ai/api.ts`, `ai/consent.ts` (ngoài 02c): chấp nhận về mặt module** (file mỏng, không kéo runtime, không gọi mạng). Nhưng dùng nó làm *nguồn duy nhất* cho cả ba nút là sai, xem F6-1, F6-2.
3. **Nút chỉ hiện sau khi mở tab Trợ lý: là hồi quy.** Trước Lô 6, bật AI thì "Để AI làm" hiện ngay khi mở đơn (DW-14-AC3). Nay mỗi lần tải lại trang (`enabled` là biến module, về `false`) người dùng phải mở tab Trợ lý mới thấy nút. E2E SR-20-AC5 xanh chỉ vì script mở tab Trợ lý trước.
4. **Gọi `/api/ai/status/` bằng fetch thường trong `GuidancePanel`: về hiệu năng thì chấp nhận được** (một GET JSON nhỏ, không kéo byte JS nào; BR-AI-17 nói về code AI và TTI). **Nhưng không được làm**, vì SR-20-AC3 (và C.4 #10 hồ sơ DW) yêu cầu AI tắt thì mở 4 màn phải có **0** request `/api/ai/*`. Mà cũng không cần: backend đã có sẵn tín hiệu. `resolve_step_ai` (`backend/apps/common/guidance/steps.py:47`) trả `ai=null` khi `AI_ENABLED=false`, khi lệnh ở mức OFF, và khi người xem không có mức nào (DW-14-AC8, AC2). Như vậy `step.ai != null` nghĩa là "AI bật và người này được giao AI làm bước này". Tín hiệu đó đi kèm response guidance, không tốn thêm request nào.
5. **"Nhờ" không phải tính năng AI.** DW-23-AC7: "`AI_ENABLED=false` → bấm Nhờ → vẫn chạy (không cần model)". Backend `POST /api/ai/actions/escalate/` không chặn khi AI tắt. Người dùng chính của nút này là NV kho (DW-23-AC1), nhóm hầu như không bao giờ đồng ý tải model. Nay nút bị ẩn khi AI tắt hoặc chưa đồng ý, tức hồi quy một AC đã duyệt, xem F6-1. `features/ai/actions/api.ts` chỉ import `shared/lib/http`, không có chuỗi `/call/`, `wllama`, `new Worker`, nên import tĩnh vào `GuidancePanel` không làm đỏ `check-ai-chunks`.
6. **`check-no-mock.mjs`: đủ tin cậy để làm cổng deploy.** Có đối chứng âm: bản mock ERP ĐỎ 32 chỗ, `demo1234` bị bắt; bản thật XANH. Lỗi nghiêng về phía an toàn (bắt nhầm thì đỏ, không lọt). Có 2 điểm mù cần biết, xem L6-3: (a) script chỉ lấy seed từ tệp tên `mock*.ts`/`Mock*.tsx`, nên mock **nội tuyến** trong `api.ts` không được quét (`ai/actions/api.ts` `mockAiActions`, `ai/commands/call.ts`, `ai/policy|settings|report/api.ts`, trước đây là `content/api.ts fetchShopCatalog`). Lượt này tôi grep tay canary nội tuyến trên `out/`: 0 tệp, nên hiện tại sạch. (b) Không kiểm số seed tối thiểu: nếu sau này đổi tên file mock, script "xanh" với 0 seed.

### Việc sửa
| # | Mức | File:dòng | Việc |
|---|---|---|---|
| F6-1 | **High, trước commit** (hồi quy DW-23-AC1/AC7 đã duyệt) | `erp-console/features/guidance/components/GuidancePanel.tsx:190-192`; `GuidanceAiActions.tsx:44, 83-100, 155-172` | Đưa "Nhờ" ra khỏi khối nạp động, render **tĩnh** trong `StepItem` với điều kiện `!step.allowed && !isSystem && step.key`, **không** phụ thuộc AI hay cờ đồng ý. Có thể tách một component tĩnh nhỏ `features/guidance/components/GuidanceEscalate.tsx` (nút + thông báo), import `escalateStep` từ `@/features/ai/actions/api` như trước Lô 6. Xoá phần "Nhờ" khỏi `GuidanceAiActions`. Kiểm: (1) E2E AI tắt, `kho1` mở chi tiết lô có bước "Chốt lô" `allowed=false`: thấy "Nhờ", lúc mở trang có 0 request `/api/ai/*`, bấm "Nhờ" thì có `POST /api/ai/actions/escalate/` và thông báo "Đã chuyển việc…". (2) Build thật: `check-ai-chunks` XANH, `check-no-mock` XANH, và `grep -rl "a1b2c3d4-e5f6-7890-abcd-ef1234567890" out/` = 0 (mock nội tuyến của `actions/api.ts` không lọt). |
| F6-2 | **Medium, trước commit** (hồi quy DW-14-AC3) | `GuidancePanel.tsx:38, 190`; `GuidanceAiActions.tsx:41` | Điều kiện nạp "Để AI làm" đổi thành `step.ai?.level === "C" && step.command` (tín hiệu server, xem mục 4), **và** cờ đồng ý nếu PO giữ nguyên SR-20-AC2 (xem D6-1). Đọc cờ đồng ý qua một hook nhỏ dùng `subscribeAiConsent`, không dùng `enabled` của gate-state. AI tắt thì `step.ai` luôn null, nên chunk `commands/call` không bao giờ được tải, AC1/AC3 vẫn giữ. Kiểm: E2E AI bật (+ đã đồng ý), **tải lại** `/orders` chi tiết đơn, **không** mở tab Trợ lý: thấy "Để AI làm", bấm thì `POST …/call/`. AI tắt: 0 request `/api/ai/*`, không có nút. Sửa `e2e/p8_lo6_fe_sr19_sr20.py` bỏ bước mở tab Trợ lý ở ca AC5. |
| L6-2 | Low (có thể gộp vào F6-2) | `GuidancePanel.tsx:38, 141` | "Tóm tắt" cần model trên máy (DW-16-AC1), nên giữ điều kiện đồng ý là đúng. Tín hiệu "AI bật" nên lấy `gateEnabled || data.next_steps.some(s => s.ai)` để bớt phụ thuộc việc mở tab. Nếu muốn chính xác hơn, BE có thể thêm `ai_enabled: bool` vào response guidance (endpoint `/api/guidance/…` không nằm dưới `/api/ai/`). Việc này đổi contract, để Lô 7. |
| L6-1 | Low (backlog Lô 7, SR-22) | `backend/apps/content/entries/services.py:679-730` (`restore_entry_version`), `:821-870` (`discard_changes`), `:363` (`publish_entry`) | Phòng thủ nhiều lớp cho dữ liệu cũ: khi nạp lại, `cover_image` không thuộc bài thì đặt `None`; `publish_entry` kiểm lại khối ảnh và bìa phải thuộc bài (400 BR-ND-07). Test: phiên bản cũ trỏ ảnh bài khác, khôi phục thì bìa = None. |
| L6-3 | Low (trước khi gắn vào runbook deploy) | `erp-console/scripts/check-no-mock.mjs`, `frontend/scripts/check-no-mock.mjs` (2 bản giống hệt) | (a) Thêm nguồn seed: các tệp `features/**/api.ts`, `features/ai/commands/call.ts` có chuỗi `NEXT_PUBLIC_USE_MOCK`. Lấy chuỗi `id: "<uuid>"`, `"mock-[a-z0-9-]{4,}"`, `title:`/`name:` có khoảng trắng. (b) `seeds.size < 10` thì exit 2. (c) Ghi bước chạy vào `doc/ops/moi-truong.md` (build thật → `check-no-mock` + `check-ai-chunks` → deploy). Điều phối sửa doc. |

### Cần PO/Duy quyết
- **D6-1 (PO, không chặn nếu làm F6-2 theo AC hiện tại):** SR-20-AC2 ghi "Để AI làm" chỉ hiện khi "`ai_enabled` **và đã đồng ý**". Nhưng "đồng ý" là đồng ý *tải model 1–3 GB về máy* (`AI_MSG.consentBody`), còn "Để AI làm" mức C chỉ gọi server soạn nháp, không cần model. DW-14-AC3 cũng không đòi đồng ý. Giữ AC2 thì người chưa tải model (đa số NV) mất nút "Để AI làm". Techlead đề nghị PO sửa AC2 thành "chỉ khi `step.ai` khác null" (server đã gộp AI_ENABLED + mức + quyền), và chỉ "Tóm tắt" mới cần đồng ý. Nếu PO đổi, dev bỏ điều kiện đồng ý khỏi F6-2.
- **Biết:** "Nhờ" hiện lại khi AI tắt (F6-1) là quay về đúng DW-23-AC7, không phải thay đổi mới.

### Ghi chú
- `frontend/out/` hiện là bản thật trỏ API production (QA/dev build để kiểm); chỉ là thư mục build cục bộ, không deploy.
- 02b §6.3 ghi "đọc trạng thái từ context gate" mà không kiểm tra rằng gate chỉ gọi status khi mở tab. Đây là thiếu sót thiết kế của techlead, fe-dev làm đúng chữ và đã tự nêu hệ quả (lệch 2, 3 trong `03-dev-notes.md`). Nguồn đúng là `step.ai` như F6-2.
- `gate-state.enabled` không đặt lại khi đăng xuất. Sau F6-2 nó chỉ còn dùng cho "Tóm tắt" và cờ đồng ý vẫn chặn nên vô hại. Nếu muốn gọn thì đặt lại trong luồng logout.

## Lô 7

**Kết luận: CẦN SỬA, 1 việc Medium.** Lỗi này có từ trước Lô 7 nhưng nằm đúng trên đường F14 vừa dùng thêm, và sửa chỉ mất 3 dòng. Nên sửa trước commit. Không có lỗi Critical hay High. Các việc Low còn lại không chặn commit.

Kiểm chứng techlead chạy trong lượt này:
- `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.ai apps.sales apps.delivery apps.content apps.inventory apps.common` (không `--parallel`): **Ran 1233 tests, OK**.
- `cd erp-console && npm test`: **11 file, 140 test đạt**.
- `cd frontend && node scripts/test-safe-href.mjs`: **40/40**.
- Không build. Điều phối đã chạy build, `check-no-mock`, `check-ai-chunks` và `makemigrations --check`.

### Soát theo điểm điều phối nêu
| Điểm | Kết quả |
|---|---|
| BM-05 | `confirm_ai_action` và `reject_ai_action` lọc bằng `visible_actions_for(user)` (`actions/services.py:18-30`). Luật này tương đương `retrieve` (`actions/api.py:78-87`): có `manage_ai_policy` thì thấy tất cả, ngoài ra là chủ việc hoặc việc ESCALATED cùng `assignee_group`. Việc ngoài phạm vi và id không tồn tại trả cùng 404 `NOT_FOUND` với cùng thông điệp. Khoá `select_for_update` chỉ áp trên tập đã lọc, nên trạng thái không đổi. Có 11 test, trong đó có ca "không lộ tồn tại giống id không có". **Đạt.** Còn 2 điểm Low (L7-2, L7-3). |
| BM-07 | `_is_cost_authorized` = `can_view_cost` (`inventory.view_costprice`). Quyền `view_profitreport` đứng riêng không còn mở khoá giá vốn. Đã bỏ nhánh `accounts.view_costprice`; codename đó không có trong nhóm nào nên không phát sinh hồi quy. **Đạt.** |
| F07 | `timezone.localtime()` theo `TIME_ZONE="Asia/Ho_Chi_Minh"`, `USE_TZ=True`. Việt Nam không đổi giờ mùa hè. Test có cả biên 06:30 VN và 20:00 VN hôm trước. **Đạt.** |
| F08 | `escalate_expired_windows` khoá `DeliveryNote` trước, sau đó khoá task bằng `select_for_update(of=("self",))`, nên không khoá lại phiếu qua `select_related`. Thứ tự này khớp 02b CSKH §1.5. Test spy mới kiểm thứ tự, chưa có test song song trên Postgres (dev đã ghi là nợ). **Đạt.** |
| F10 | Undo đọc `cancel_action:<act>` và gọi đúng action đó qua `dispatch_command`. Tầng 1–3 do view của action huỷ kiểm theo người hoàn tác, nên **chặt hơn trước**: trước đây `cancel_receipt` bị gọi thẳng, không kiểm quyền. Lệnh không có đường hoàn tác trả 400 `AI_CANNOT_UNDO`, trạng thái vẫn DONE. `required_perms=()` không có tác dụng thật vì `dispatch_command` không đọc trường này. **Hoàn tác khi AI tắt không mở lỗ nào**: chỉ chủ việc hoặc `manage_ai_policy` được gọi. Thao tác chỉ đưa về trạng thái cũ (huỷ lịch, hoặc huỷ chứng từ bằng trạng thái), không sinh việc AI mới, không gọi model, và vẫn bị khoá bởi `undo_until`. **Đạt.** Còn 1 điểm Low về hardening (L7-4). |
| F12 | Không có `chu` active thì hàm trả `False`, ghi log cảnh báo và không giao cho người bất kỳ. `downgrade_reason` và log chỉ còn mã lỗi (`BusinessError.code` hoặc tên lớp lỗi). Đã xoá nhánh chết CONFIRM_ORDER. `_escalate_to_chu` trả `bool` để đếm đúng. `args.reason` được cập nhật cùng lúc. Nợ Lô 3 L1/L2 đã xong. **Đạt.** |
| NoStore | `NoStoreMixin` đứng đầu MRO của `SalesOrderViewSet` và `CustomerViewSet`. Mixin dùng `finalize_response`, nên response 401/403 cũng có header. Có test ma trận. **Đạt.** |
| L6-1 | `_own_cover` bỏ ảnh bìa lạ khi restore/discard, và tính lại `draft_hash` khi bìa bị bỏ. `publish_entry` chặn 400 `BR-ND-07` với ảnh bìa hoặc khối ảnh thuộc bài khác. Id ảnh bị lọc `int`/không phải `bool`. Chọn không tự gỡ khối ảnh lạ trong thân bài mà chặn ở bước đăng là hợp lý, vì tránh tự sửa nội dung của người soạn. **Đạt.** |
| L5-1 contract | `has_stock` chỉ nhận `1`/`true`; giá trị khác bỏ qua, không lỗi. `BatchListQuery.has_stock` chỉ để registry AI đọc; lời gọi AI gửi `True` thì vẫn khớp nhờ `lower()`. Bốn khoá tên đều là tên hoặc nhãn: `supplier`, `warehouse`, `item` là FK NOT NULL và đã `select_related`, nên không có N+1 hay `None`. `nv_kho` vốn có quyền đọc `supplier` (seed 0002). Không thêm field tiền nào. Giá vốn vẫn do `CostFieldSerializerMixin` chặn; test `nv_kho` kiểm cả khoá `COST_KEYS` lẫn số `180000`. **Không lộ giá vốn. Đạt.** |
| F5 | `privacy_consent_required(testing, debug, env)` giữ đúng ngữ nghĩa của `_bool` cũ. Test đổi từ "chép công thức" sang gọi hàm thật. AC10 POST Admin thật khoá được cả hai lớp (`readonly_fields` và `editable=False`). AC9 so đúng tập khoá. **Đạt.** |
| Nợ Lô 1 L4, Lô 2 L2/L3/L4/L5, Lô 3 L4, Lô 4 L1 | Đã xong hết. Fixture quét PII (`SR24Fixture`) nay khẳng định dữ liệu không rỗng. |
| FE safeHref hai bên | Luật hai bên **giống hệt nhau** (so từng dòng); vitest ERP và script Shop chạy cùng 40 payload. Backend `sanitize._is_valid_href` vẫn là lớp chặn cuối, cũng từ chối href không có giao thức. Lệch nhỏ còn lại ghi ở L7-5. |
| Tiptap từ chối href không giao thức | **Không làm hại người viết bài.** Backend vốn đã bỏ các href này khi lưu (`urlsplit("abc").scheme == ""`), nên bài đã lưu không có link nào như vậy, và bản sửa không làm mất dữ liệu cũ. Khác biệt duy nhất: trước đây ERP nhận `abc` rồi backend lặng lẽ xoá link; nay người viết được báo ngay bằng hộp thoại, tức là tốt hơn. Gợi ý UX (tuỳ chọn, không chặn): nếu người viết gõ `www.…` thì tự thêm `https://`. |
| F6 "Not found." | Chỉ thay câu khi `detail === "Not found."` ở nhánh 404/410, còn lại giữ `detail` tiếng Việt của BE. Trong Shop không còn chỗ nào so chuỗi thông điệp. **Đạt.** |
| F7/F8/F9 | Catalog chỉ nạp 1 lần, bài không có thẻ thì không gọi. `ArticleBody` thành client component, nhưng cả hai trang dùng nó (`bai-viet`, `trang`) vốn đã là `"use client"`, nên không mất SEO. `srcSet` và `sizes` đúng cỡ công khai. Mock `xss-mau` chỉ có ở bản mock. mailto/tel dùng thẻ `<a>` thường, không mở tab mới. **Đạt.** |
| F10 FE | Chỉ còn một `getSiteInfo` (cache Promise 5 phút, lỗi thì bỏ cache), và `CheckoutScreen` truyền `siteInfo` xuống `PaymentPanel`. `callHours()` là nguồn giờ duy nhất trên FE. Chỉ render 4 số cuối SĐT. **Đạt.** Việc gộp nguồn giờ ở BE xem đề xuất D7-1. |
| `shared/ui/globals.css` (ngoài phạm vi) | **Chấp nhận.** Đây là sửa lỗi thật, không phải đổi thiết kế: selector `tr:last-child td` có độ ưu tiên (0,2,4) cao hơn `td.m-*` (0,2,3), làm dòng cuối mất `order` khi bảng thành thẻ trên mobile. Nay selector chỉ giữ `border:0`. Dev đã chạy lại 4 bộ e2e của các màn có bảng (Lô 5, SR-07, SR-09, Lô 6) và đều xanh. Ghi thêm vào checklist QA hồi quy mobile 375 cho mọi `table.data`. |
| Timeline `credit_note_issued` | FE chỉ thêm kind và icon; nhãn do BE dựng. Nhãn chỉ có mã chứng từ và số tiền doanh thu, không có giá vốn hay PII. **Đạt.** |
| CSKH stale 3 thao tác | `reportActionError` dùng chung. Nút gửi của cả 3 form bị khoá khi đã stale. **Đạt.** |
| F14 tem | QR vẽ bằng `<img data:image/svg+xml>`, bỏ `dangerouslySetInnerHTML`. `next` chỉ chứa `note` và `print_no` (mã số, không phải PII). **Đạt**, nhưng xem **L7-1**: `safeNext` mà F14 dựa vào có lỗ open redirect. |
| F12 FE spike | `app/ai-spike/` và `spikes/dw02/` đã xoá. `commands.test.ts` trỏ sang bản sao index trong `doc/.../research/`, chấp nhận được. |

### Lệch dev nêu: chốt
1. **DW-11-AC5 403 → 404 (việc của người khác):** **Chấp nhận.** Đây là hệ quả trực tiếp của BM-05. Test cũ được chỉnh để vẫn kiểm BR-AI-04 (403 khi là chủ việc nhưng thiếu quyền lệnh). Việc cần làm: điều phối ghi 1 dòng vào `03-dev-notes.md` của hồ sơ `2026-09-28-ai-digital-worker` rằng DW-11-AC5 nay trả 404 cho việc ngoài phạm vi (P8 BM-05).
2. **DW-19-AC10 đổi tên và đổi kỳ vọng (AI tắt vẫn hoàn tác được):** **Chấp nhận**, đúng SR-22 F10 đã duyệt. Việc cần làm: ghi cùng chỗ như mục 1.
3. **Việc SCHEDULED lỗi ở nhánh AI tắt (và lỗi F12) giữ nguyên trạng thái, không tự chuyển FAILED:** **Chấp nhận cho P8.** Job idempotent: lần chạy sau thử lại, log không chứa PII. Rủi ro là một việc lỗi mãi thì bị thử lại mãi mà không ai biết. Đưa vào backlog P9 (Duy quyết nghiệp vụ): đếm số lần thử, quá N lần thì ESCALATED cho Chủ.
4. **Fixture PII sweep đổi (bỏ gán phiếu trước khi kiểm ngoài phạm vi):** chấp nhận.
5. **Undo giữ mã lỗi gốc (`BR-MH-07`):** chấp nhận, như vậy FE hiện đúng lý do.
6. **L6-1 không gỡ khối ảnh lạ, chỉ chặn khi đăng:** chấp nhận.
7. **V-DW1:** 02b §8 của hồ sơ này đã đúng. Câu sai vẫn còn ở `doc/features/2026-09-28-ai-digital-worker/02c-giao-viec.md:27` ("chỉ mở được ở staging khi `AI_PRODUCTION_READY=false`"). Việc cần làm: **điều phối** sửa thành `AI_PRODUCTION_READY=1` ở staging, production giữ `0`, rồi trỏ về `doc/ops/moi-truong.md` (file ngoài phạm vi dev, là việc sửa doc).

### Việc sửa
| # | Mức | File:dòng | Việc |
|---|---|---|---|
| L7-1 | **Medium, nên sửa trước commit** (có từ `13e7d51`, không phải hồi quy Lô 7) | `erp-console/shared/lib/nav.ts:397-400` (`safeNext`); dùng ở `features/auth/components/LoginScreen.tsx:18-24` | **Open redirect.** `safeNext` chỉ chặn `//`, không chặn `/\` hay ký tự điều khiển. Đã kiểm: `new URL("/\\evil.example/x", origin)` → `https://evil.example/x`. Next app-router gặp URL khác origin thì chuyển trang cứng (`isExternalURL` → `location`). Người **đang đăng nhập** mở `/login/?next=/%5Cevil.example` là bị đẩy ngay sang trang ngoài (`destination(me, next, me.id)` luôn qua điều kiện cùng người). `/%09/evil.example` cũng lọt, vì trình duyệt bỏ tab khi phân giải. Đây là kênh lừa lấy mật khẩu nhân viên ERP. Cách sửa: `safeNext` từ chối khi `next[1] === "/" \|\| next[1] === "\\"` hoặc có ký tự mã ≤ 32 hay trong khoảng 127–159 (cùng luật nhánh nội bộ của `isSafeHref`, có thể tái dùng). Test vitest: `/\evil.example`, `/%5Cevil` (sau decode), `/\t/evil.example`, `//evil`, `/orders/?id=1` (nhận), `/print/label/?note=1&print_no=2` (nhận). |
| L7-2 | Low (dọn) | `backend/apps/ai/actions/api.py:78-87` | `retrieve` còn chép tay bộ lọc. Nên đổi sang `services.visible_actions_for(request.user).filter(id=pk).first()` để BM-05 và `retrieve` không lệch nhau về sau. `get_queryset` scope `mine` cũng dùng được hàm này. |
| L7-3 | Low | `backend/apps/ai/actions/services.py:208-209` | `undo_ai_action` vẫn trả 403 cho việc của người khác, lộ việc có tồn tại (không đồng bộ với BM-05). Rủi ro thấp vì id là UUID. Nên lọc theo chủ việc hoặc `manage_ai_policy`, ngoài phạm vi thì 404. Cần chỉnh test `test_f10_nguoi_ngoai_khong_hoan_tac_duoc_403`. |
| L7-4 | Low (hardening) | `backend/apps/ai/actions/services.py:242`; `backend/apps/ai/registry/discovery.py:234-236` | `hasattr(view_cls, cancel_act)` nhận cả thuộc tính không phải `@action`, ví dụ `destroy`, rồi dispatch bằng POST. Hiện chỉ có `cancel_action:cancel` và registry do code khai, nên chưa khai thác được. Nên kiểm thêm `"post" in getattr(getattr(view_cls, cancel_act), "mapping", {})` ở cả hai chỗ. Nên có thêm 1 test hoàn tác **DONE thật khi AI tắt**; hiện chỉ có ca huỷ lịch và ca id không tồn tại. |
| L7-5 | Low (tài liệu/đồng bộ) | `frontend/features/content/safeHref.ts:5-16`; `backend/apps/content/body/sanitize.py:37-45` | (a) Chú thích Shop đã lỗi thời: vẫn ghi "Luật khớp bản ERP (`convert.ts` → `safeHref`)" và "Chặt hơn ERP ở 2 điểm". Nay hai bản giống hệt, nên sửa chú thích trỏ về `erp-console/features/content/editor/safeHref.ts` như chú thích phía ERP. (b) BE lệch FE: BE bỏ `#neo`, nên FE nhận `#` nhưng lưu xong thì mất link; BE cũng không chặn DEL và C1 không phải khoảng trắng. Dòng 41 có `r"/\ "` thừa dấu cách, là code chết vì dòng 43 đã chặn. Nên để P8b hoặc lô sau. |

### Đề xuất (không chặn)
- **D7-1 (BE, cần Duy vì là câu hiện cho khách):** gộp giờ gọi ở backend. Cách ít rủi ro nhất: `SHOP_CONFIRM_CALL_HOURS = os.getenv("SHOP_CONFIRM_CALL_HOURS", CSKH_WORKING_HOURS)` (`backend/config/settings.py:340`, đọc sau dòng 288), khi đó mặc định chỉ còn một giá trị `07:00-21:00`. Sau đó ở P9 bỏ hẳn `confirm_call_hours` khỏi `site-info` và FE chỉ đọc `cskh_notice.working_hours`. Hiện FE đã chọn một nguồn nên trên cùng một màn không còn hiện hai giờ khác nhau. Lệch chỉ còn giữa hai cấu hình (khi khối CSKH tắt, khách thấy `7:00–20:00`). Câu thông báo đang chờ legal-vn nên đổi giờ cần Duy chốt.
- **D7-2:** nợ N1 (`get_or_create` song song trên Postgres) và test khoá song song F08: giữ ở P9 như dev ghi.

### Định danh mới trong Lô 7 cần đưa vào P8b (không sửa ở Lô 7)
Đối chiếu `doc/features/2026-09-30-dat-ten-tieng-anh/01-ra-soat-dat-ten.md`:
- Đã có trong rà soát: `CskhNotice.tsx` và `CskhNotice.module.css` (dòng 51), `CskhNoticeConfig`, `cskhArmStale` (dòng 67), `NHAP_LO_DRAFT_PREFIX` (dòng 68), `_escalate_to_chu` và `chu_user` (dòng 63).
- **Chưa có, cần bổ sung:** hook mock `window.__caveMock.cskhSetStatus` (`erp-console/features/cskh/mock.ts:799`); `CallNoticeBox` và `callHours` (tên tiếng Anh, nhưng nằm trong file `CskhNotice.tsx` nên đi cùng việc gộp dòng 51); 12 file test mới `test_p8_lo7_*.py` cùng e2e `p8_lo7_fe_erp.py`, `qa-lo7-*.py`, với tên hàm test tiếng Việt không dấu (ví dụ `test_bm05_nv_giao_reject_viec_cua_chu_404_trang_thai_khong_doi`, `test_f10_khong_co_duong_hoan_tac_400`). Nhóm này thuộc mục "Test" (dòng 28–29), chỉ cần cộng số đếm.
- Slug mock `xss-mau` là dữ liệu, không phải định danh code, nên bỏ qua.

### Ghi chú
- Không có migration, không có quyền mới, không có endpoint mới. Chỉ thêm tham số `has_stock` và 4 khoá chỉ đọc vào danh sách lô. Contract khớp với FE ERP (`inventory/api.ts:71-89`).
- Hoàn tác giờ đi qua view, nên người tự tay nhập lô rồi bị rút quyền `change_purchasereceipt` sẽ nhận 403 khi hoàn tác. Trước đây trường hợp này vẫn huỷ được. Hành vi mới đúng với BR-PQ.

## Lô 8

**Kết luận: PASS có điều kiện. Có 1 việc Low cần làm trước commit (L8-1: mock ERP còn viết tiền kiểu `đ`, lệch câu lỗi mới của BE) và 1 việc Medium nên gộp vào lô này (L8-2: `received_date` mặc định đang lấy ngày UTC).** Không có lỗi Critical hay High. Diff không đổi giá trị đang lưu trong DB, không đổi khoá hay kiểu trong contract JSON, không lộ giá vốn hay dữ liệu cá nhân mới.

Kiểm chứng techlead chạy trong lượt này (không build):
- `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.common.tests.test_p8_lo8_vnd_gmt7 apps.delivery.tests.test_p8_lo8_gmt7 apps.delivery.cskh apps.sales.payments apps.sales.refunds`: **Ran 219 tests, OK**.
- `cd frontend && TZ=America/New_York node scripts/test-format.mjs`: **26/26**.
- `cd erp-console && TZ=UTC npx vitest run shared/lib`: **38 test đạt** (gồm `format.test.ts` và `noLocalTime.test.ts`).
- Grep toàn bộ `erp-console/{app,features,shared}` và `frontend/{app,features,components,lib}` tìm các mẫu scanner chưa bắt: `get(Hours|Date|Month|FullYear|Day)()`, `set(Hours|Date)(`, `toISOString().split/substring`, `toDateString`, `toTimeString`, `.toLocaleString(`. Chỉ còn `erp-console/features/orders/mock.ts:907` (xem L8-1). Mọi `new Date(...)` còn lại dùng cho đếm ngược, TTL hoặc so sánh mốc, không dùng để hiển thị.

### Soát theo điểm điều phối nêu
| Điểm | Kết quả |
|---|---|
| FE hiển thị giờ VN | Cả hai FE tách ngày giờ qua **một** `Intl.DateTimeFormat("en-GB", {timeZone: "Asia/Ho_Chi_Minh", hourCycle: "h23"})` rồi dùng `formatToParts`, nên kết quả không phụ thuộc thứ tự chuỗi của locale hay múi giờ máy. Mọi chỗ trước đây cắt chuỗi `slice(11,16)` (chỉ đúng khi BE trả `+07:00`) đã đổi sang hàm chung. **Đạt.** |
| FE "hôm nay" và lọc ngày | `todayInVietnam` được dùng cho bộ lọc đơn (`OrdersScreen.vnDate`), `completed_from` của giao hàng, ngày báo cáo AI và ngày nhập lô mặc định. Các giá trị này là chuỗi `YYYY-MM-DD` và BE lọc bằng `__date` theo `TIME_ZONE=Asia/Ho_Chi_Minh` (`settings.py:133`), nên hai bên hiểu cùng một ngày. "Hôm qua" lùi 24 giờ là đúng vì Việt Nam không đổi giờ mùa hè. **Đạt.** |
| `vnInputToIso` | Ghép `+07:00` vào giá trị ô `datetime-local` rồi `toISOString()` ra `…Z`. BE nhận `DateTimeField` có offset, nên lưu đúng mốc UTC. Chỉ có 2 ô `datetime-local` (CSKH hẹn gọi lại, gia hạn), cả hai đã chặn giá trị rỗng trước khi gọi (`CskhCallModal.tsx:143`, `:243`). Sai định dạng thì trả `""`, BE trả 400 thay vì FE ném `RangeError` như trước. Ô `type="date"` gửi chuỗi ngày thuần, không đổi múi giờ. **Đạt.** |
| BE chuỗi người đọc | `apps/common/formatting.py` chỉ gọi `timezone.localtime`. Hai chỗ trước đây sai thật đã sửa: `cskh/serializers.py:203` (`strftime` trên UTC, lệch 1 ngày khi phiếu tạo lúc 00:00–07:00 VN) và `AuditLog.__str__`. `customer_notices` đổi từ `localtime(x)+30d` sang `localtime(x+30d)`: kết quả như nhau vì không có giờ mùa hè. ISO trong JSON giữ nguyên. **Đạt.** |
| Contract JSON | Khoá và kiểu không đổi (`refund.amount` vẫn là chuỗi `"300000"`, có test khoá). Chỉ **văn bản** thông điệp đổi: câu lỗi S12/S13 `300.000đ` → `300.000 ₫`, `1đ` → `1 ₫`, câu báo khách tự huỷ, lý do chuyển Chủ, tóm tắt việc AI. Trong FE không chỗ nào so khớp hay tách chuỗi thông điệp BE (đã grep). Chỉ mock ERP còn chép kiểu cũ, xem L8-1. |
| `gen_code` lấy ngày VN | Định dạng không đổi (`<prefix><yymmdd>-<6 hex>`), chỉ khác phần ngày cho chứng từ tạo lúc 00:00–07:00 VN. Tính duy nhất vẫn giữ nhờ vòng `exists()` cùng `unique=True` trên `SalesOrder.code` và `SalesInvoice.code`. Không có idempotency nào dựa vào phần ngày (idempotency đơn và phiếu nhập dùng khoá riêng). Adapter `strip_order_retry_suffix` chỉ khớp định dạng. Mã cũ không bị đổi. Không test nào tính mã kỳ vọng theo `now():%y%m%d` (đã grep); test mới cố định `now` = 17:30Z. **Không có rủi ro.** Xem thêm I8-1, một lỗi có từ trước và không do lô này gây ra. |
| Tiền chuỗi Decimal → số | Shop chỉ dùng `Number()` để hiển thị và để tính tổng tạm trong giỏ. Payload `createOrder` chỉ gửi `item_code` và `qty` (`CheckoutScreen.tsx:122-127`), **BE tự tính giá**, nên float ở giỏ không đi vào logic tiền. `CartContext` ép `price` của giỏ cũ về số (`|| 0` khi rác) là đủ. Giỏ vẫn không có dữ liệu cá nhân. BE `format_vnd` dùng `Decimal` và `ROUND_HALF_UP`, không dùng float. **Đạt.** |
| `__str__` admin có tiền (`PurchaseCost`, `PurchaseCostAllocation`, `PurchaseInvoice`, `ItemPrice`, `Refund`, `PaymentTransaction`) | **Không thêm chỗ lộ nào.** Bản cũ đã in `{amount}đ`, bản mới chỉ đổi cách định dạng. `ItemPrice.rate` là giá bán, không nhạy cảm. `str(obj)` cũng được chép vào `AuditLog.object_repr` qua `record_audit`, nhưng không đường nào gọi `record_audit(obj=PurchaseCost/PurchaseInvoice/Allocation)` (đã grep), nên nhật ký không nhận thêm số tiền mua. Không có code nào bật `is_staff` cho nhân viên, nên Admin hiện chỉ superuser vào được. Còn một lỗ tiềm ẩn có từ trước, ghi ở I8-2 (theo bài học M1). |
| Test `noLocalTime.test.ts` | Bắt được các lối cũ hay gặp nhất và có kiểm "quét > 100 file" để không xanh giả. Còn thiếu vài mẫu và Shop chưa có scanner, xem L8-3. Hiện mã nguồn **sạch** với cả các mẫu còn thiếu (đã grep). |
| Phạm vi | Dòng Lô 8 ở `02c-giao-viec.md` vẫn ghi "FE ∥ FE" và **cấm `backend`**, trong khi lô có phần BE (dev-notes "Lô 8 — BE"). Nội dung phần BE đúng tinh thần SR-25. Việc cần làm: điều phối cập nhật dòng 02c (thêm BE, liệt kê file) trước khi đánh ☑, để hồ sơ khớp commit. |

### Chốt đề xuất be-dev: `received_date` mặc định
`backend/apps/purchasing/receipts/services.py:104-105` đang lấy `timezone.now().date()`, tức ngày UTC. Đây **không phải lỗi hiển thị mà là lỗi giá trị nghiệp vụ**: `received_date` là ngày lịch của vựa (VN). Nó quyết định `batch_id` (`inventory/batches/services.py:65`), `expiry_date = received_date + shelf_life` (dòng 64), và thứ tự FEFO khi cùng hạn (`FEFO_ORDER`). Nhánh mặc định này chạy khi client không gửi `received_date` (`NhapLoInput.received_date` có `required=False`), điển hình là lệnh AI `nhap_lo`. Form ERP thì luôn gửi ngày VN. Vựa mua cá ở cảng lúc rạng sáng (khoảng 3–6 giờ), rơi đúng vào khung 00:00–07:00 VN. Khi đó lô bị ghi ngày hôm trước, **hạn dùng sớm 1 ngày** và bị `sellable_batches` (so với `timezone.localdate()`) chặn bán sớm 1 ngày.
→ **Nên sửa, mức Medium (L8-2), gộp vào Lô 8** vì BE đã mở và thay đổi chỉ 1 dòng. **Không cần migration dữ liệu**, vì 3 lý do: (1) không phân biệt được lô nào nhận ngày do người nhập và lô nào nhận ngày mặc định; (2) `batch_id` đã in trên tem QR, là định danh không được đổi; (3) dữ liệu cũ sai về phía an toàn (hạn sớm hơn), không bán hàng quá hạn. Nếu Duy muốn xem lại, chỉ làm truy vấn **đọc** liệt kê lô có `received_date` < `localdate(created_at)` của phiếu nhập, rồi Duy tự quyết từng lô. Không tự sửa.

### Việc sửa
| # | Mức | File:dòng | Việc |
|---|---|---|---|
| L8-1 | **Low, làm trước commit** (mock phải khớp contract thật) | `erp-console/shared/lib/beErrors.mock.ts:77`, `:108`; `erp-console/features/orders/mock.ts:905-907` (`vndD`); `erp-console/e2e/s12_s13_queue.py:174`, `:354-355` | BE đã bỏ `vnd_short`: câu lỗi S12/S13 nay là `300.000 ₫` và `tối thiểu 1 ₫.`. Mock ERP vẫn sinh `300.000đ` và `1đ`, nên ở bản mock người dùng thấy kiểu cũ, trái AC1 "thống nhất một kiểu", và e2e đang khoá kiểu cũ. Sửa: `vndD` → dùng `vnd` của `shared/lib/format.ts` (đổi tên hàm hoặc bỏ hẳn); 2 thông điệp mock → `"Số tiền tối thiểu 1 ₫."`, `"Số tiền hoàn tối thiểu 1 ₫."`; e2e dựng kỳ vọng bằng `" ₫"`. Chạy lại `s12_s13_queue.py` (mock) và `npm test`. |
| L8-2 | **Medium, nên gộp Lô 8** | `backend/apps/purchasing/receipts/services.py:105` | `received_date = timezone.localdate()`. Test mới: `patch("django.utils.timezone.now", return_value=17:30Z ngày 30/09)`, gọi `create_and_submit_receipt` không truyền `received_date`, rồi assert `receipt.received_date == date(2026,10,1)`, `batch_id` chứa `-261001-`, `expiry_date == 2026-10-01 + shelf_life`. Suite cũ không bị ảnh hưởng vì các test hiện có đều truyền `received_date` tường minh (đã grep). Không cần migration. Khi sửa thì bỏ luôn dòng `from django.utils import timezone` trong thân hàm (dòng 94) nếu không còn dùng chỗ khác. |
| L8-3 | Low (siết test) | `erp-console/shared/lib/noLocalTime.test.ts:24-31`; `frontend/scripts/test-format.mjs` | (a) Thêm mẫu cấm: `/\.get(Hours\|Minutes\|Date\|Day\|Month\|FullYear)\(\)/`, `/\.set(Hours\|Date)\(/`, `/toISOString\(\)\.(split\|substring\|substr)\(/`, `/toDateString\|toTimeString/`. Mẫu `Date#toLocaleString` hiện chỉ bắt dạng `new Date(...).toLocaleString(`, còn `d.toLocaleString(` với `d` là Date thì lọt. Nên cấm mọi `.toLocaleString(` ngoài `format.ts`, vì tiền và kg đều đã qua `vnd`/`kg`, sau L8-1 sẽ không còn chỗ vi phạm. Nên thêm mẫu tiền `/\}đ\b\|[0-9]đ\b\|" đ"/` trên file không phải comment. (b) Shop chưa có scanner nguồn: thêm bước quét tương tự vào cuối `test-format.mjs` (không cần thư viện, không đụng `package.json`). |
| L8-4 | Low (đặt tên, AC5) | `frontend/lib/format.ts` (`VN_TIME_ZONE`, `todayVn`, `currentYearVn`) và `erp-console/shared/lib/format.ts` (`VN_TZ`, `todayInVietnam`) | Hai FE đặt tên khác nhau cho cùng một khái niệm. Nên thống nhất một bộ tên, gợi ý `VIETNAM_TIME_ZONE`, `todayInVietnam`, `currentYearInVietnam`. Nếu không kịp thì đưa vào P8b. Tên test Python mới đặt bằng tiếng Việt không dấu (`test_sr25_ac1_format_vnd_dau_cham…`), cộng vào mục "Test" của rà soát đặt tên P8b. |
| N8-1 | Nit | `frontend/lib/types.ts:22-23` | Chú thích "mock trả số" đã lỗi thời, vì mock nay trả chuỗi qua `toWireItem`. |
| N8-2 | Nit | `frontend/app/shop/orders/OrderLookup.tsx:190` | BE trả `refunded_at` dạng ngày thuần `YYYY-MM-DD` (`customer_notices.py:57`), nên hàm đúng nghĩa là `formatDateOnly`. `formatDate` vẫn ra kết quả đúng vì nửa đêm UTC = 07:00 VN cùng ngày, nhưng dữ liệu e2e đang giả `refunded_at` là ISO có giờ, không khớp contract thật. |
| N8-3 | Nit | `backend/apps/common/formatting.py:14-16` | `format_vnd(None)` ném `TypeError`, còn `__str__` cũ in được `Noneđ`. Các cột tiền đều NOT NULL nên thực tế không gặp. Có thể trả `"—"` khi `None` cho đồng bộ với FE. |

### Phát hiện có từ trước (không do Lô 8, đưa backlog)
- **I8-1 (Medium, thanh toán):** `backend/apps/sales/payments/auto_confirm.py:98` tìm mã đơn trong nội dung chuyển khoản bằng `SO-\d{6}-…`, nhưng mã thật sinh bởi `gen_code("SO", …)` (`orders/services.py:201`) là `SO260930-XXXXXX`, **không có gạch sau `SO`** (khớp chú thích `models/orders.py:41`: `^(SO\d{6}-[0-9A-Za-z]{6})`). Vì vậy nhánh dự phòng "đọc mã trong nội dung" không bao giờ khớp đơn thật và luôn chuyển Chủ "Không tìm thấy đơn". Test đang dùng mã giả `SO-260930-…` nên không phát hiện. Cần techlead xem kỹ cùng adapter ở một story riêng (ngân hàng có thể còn bỏ dấu `-`).
- **I8-2 (Medium tiềm ẩn, giá vốn — cùng loại M1):** `backend/apps/purchasing/admin.py` `PurchaseInvoiceAdmin.list_display` có `amount` (tổng tiền mua, chia số kg ra được giá vốn), không có `CostHidingMixin`, và `quan_ly` có `view_purchaseinvoice` (seed `0002:30`). Hiện chưa khai thác được vì không nhân viên nào có `is_staff`. Nhưng hễ bật Admin cho Quản lý là lộ. Nên ẩn `amount` và `__str__` theo `view_costprice`, kèm test Admin như M1.
