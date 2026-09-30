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
