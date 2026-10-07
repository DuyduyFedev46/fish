# Sửa lỗi chỉ lộ trên PostgreSQL (08/10)

Production và staging chạy PostgreSQL 16 (Supabase), nhưng test xưa nay chạy SQLite nên một số lỗi lọt. Ngày 08/10 chạy
cả suite trên PostgreSQL 16 cục bộ: Ran 3384, failures=13, errors=51 (main d0854a7). Sau khi sửa: xem mục "Số test".

## Nguyên nhân và cách sửa

| Nhóm | Nguyên nhân | Cách sửa |
|---|---|---|
| 1. `FOR UPDATE cannot be applied to the nullable side of an outer join` (~27 ca: huỷ phiếu nhập, publish lô, claim việc gọi xác nhận, ...) | `select_for_update()` kèm `select_related` tới FK cho phép null (`PurchaseReceiptLine.batch`, `ConfirmationTask.claimed_by`). SQLite bỏ qua khoá nên không lộ. | `select_for_update(of=("self",))`: chỉ khoá dòng của bảng chính, giữ nguyên thứ tự khoá (đơn, rồi phiếu, rồi việc). Sửa 3 chỗ: `purchasing/receipts/services.py` (cancel_receipt; `submit_receipt` không bị lỗi null vì `item` là FK NOT NULL, chỉ bỏ khoá kèm Item), `delivery/confirmation/services.py` (claim_task). Đã rà mọi `select_for_update` trong `backend/apps`: các chỗ còn lại không kèm `select_related`. |
| 2. 7 ca AI trả 502 `AI_DISPATCH_FAILED` | Cùng lỗi nhóm 1: lệnh AI huỷ phiếu nhập gọi `cancel_receipt`, lỗi bị lớp điều phối AI nuốt thành 502. | Hết khi sửa nhóm 1, không sửa thêm. |
| 3. `test_cost_locked_and_overflow` n3 trả 500 | Tràn `numeric(14,4)`: SQLite ném `InvalidOperation` (đã bắt), PostgreSQL ném `DataError` (chưa bắt). | `record_purchase_cost` bắt thêm `DataError` và trả 400 `COST_LANDED_OVERFLOW`, rollback toàn bộ như cũ. |
| 4. `test_shop_labels` `varchar(12)` | Dữ liệu test: trạng thái giả `FUTURE_STATUS` dài 13 ký tự. Code không có lỗ hổng (trạng thái chỉ do hệ thống đặt). | Đổi dữ liệu test thành `FUTURE`. |
| 5. `test_supplier_crud` thứ tự tên | Test so với `sorted()` của Python (theo mã ký tự, "Đ" xếp cuối). PostgreSQL xếp "Đ" cạnh "D" theo collation tiếng Việt. | Không đổi code: thứ tự theo collation của DB là thứ tự đúng cho UI tiếng Việt (truy vấn đã `order_by("name", "id")`, ổn định). Test đổi thành so tập tên, và thứ tự các tên không bắt đầu bằng chữ "Đ". |
| 6a. `test_scope_snapshot` lệch | Hệ quả nhóm 1: bước claim việc gọi lỗi `NotSupportedError` (ảnh chụp ghi `EXC:NotSupportedError`). | Hết khi sửa nhóm 1. |
| 6b. `test_qa_lo4_tien` 404 "Không tìm thấy mục chờ gọi" | Test gọi `/api/confirmation/queue/{task.pk}/decide/`, nhưng route tra theo **id phiếu giao** (`note_id`, xem `ConfirmationLookupByNoteIdTests`). Trên SQLite id việc và id phiếu cùng bằng 1 nên đúng ngẫu nhiên; Postgres không reset sequence giữa test nên lệch. | Test đổi sang `note.pk`. Code không đổi. |
| 7a. 22 ca `seed_qa` bị cổng chặn | DB test PostgreSQL tên `test_*` không chứa "staging". | Chỉ sửa test: `SeedQaBase.setUp` patch `guard.database_facts` thêm hậu tố `_staging` cho DB tên `test_*` trên Postgres. Code cổng `guard.py` không đổi: `postgres`, `prod`, `SEPAY_ENV=PRODUCTION` vẫn bị chặn, test chặn vẫn chạy (tự patch ghi đè). |
| 7b. 2 ca `test_completion_race_postgres` lỗi `(admin, logentry) already exists` | Chạy chung suite: `test_s03_migration` (TransactionTestCase) lùi migration rồi không trả về bản mới nhất, và một flush trước đó khiến `post_migrate` tạo lại ContentType; nạp `serialized_rollback` đụng khoá duy nhất. | (a) `test_s03_migration` thêm `tearDown` migrate về leaf; (b) lớp race xoá ContentType tạo lại trước khi nạp bản serialize (`_fixture_setup`). |

## Chạy suite trên PostgreSQL cục bộ

Cần một cụm PostgreSQL 16 tạm (không phải staging hay production). Django tự tạo và xoá DB `test_*`.

```
cd backend
DJANGO_DEBUG=1 DATABASE_URL=postgres://qa@127.0.0.1:55432/cangca_racetest .venv/bin/python manage.py test --noinput
```

Dùng tên DB riêng cho mỗi người chạy (ví dụ `cangca_pgcompat`): cùng tên thì hai lần chạy song song xoá DB test của nhau
(`--noinput` xoá `test_<tên>` có sẵn), cho ra hàng nghìn lỗi giả. Suite chạy ~5 đến 10 phút. Chạy tuần tự, không dùng `--parallel`. Không bao giờ trỏ `DATABASE_URL` vào staging hay production.

## Số test

Trước (PostgreSQL, main d0854a7): Ran 3384, failures=13, errors=51.
Sau (PostgreSQL 16 cục bộ, DB `cangca_pgcompat`): Ran 3386, OK (không skip, kể cả 2 ca đua thật).
SQLite tuần tự: Ran 3386, OK (skipped=2: hai ca đua chỉ chạy trên Postgres).
`makemigrations --check --dry-run`: No changes detected (không có migration). `scripts/check_naming.py`: OK.

## Review techlead (08/10)

**Kết luận: REVIEW PASS (APPROVED).** Rà diff `main...7259755` (10 file). Không đổi API, quyền, model, không migration
(`makemigrations --check --dry-run`: No changes detected). `scripts/check_naming.py`: OK. Không chạy suite (điều phối viên chạy).

**(1) `select_for_update(of=("self",))`**
- `cancel_receipt` (`purchasing/receipts/services.py:205`): trước đây trên Postgres câu này luôn lỗi (`batch` là OneToOne null
  → LEFT JOIN), nên không có "khoá kèm" nào bị mất. Lô vẫn được khoá riêng ngay dòng sau (`:207`, `Batch...select_for_update()
  .filter(id__in=batch_ids)`), mọi phép kiểm lô (phân bổ chi phí, trạng thái, tồn, sổ kho) chạy trên bản đã khoá. Thứ tự
  phiếu → dòng phiếu → lô giữ nguyên. Không có race mới.
- `submit_receipt` (`:47`): `item` là FK NOT NULL (INNER JOIN), câu cũ không lỗi trên Postgres; thay đổi chỉ bỏ khoá kèm dòng
  `catalog.Item`. Hàm không ghi Item, mã lô sinh bằng uuid, phiếu đã khoá trước bởi `lock_draft_receipt` nên submit song song
  vẫn tuần tự. Bỏ khoá Item là an toàn (bớt tranh chấp). Ghi chú: bảng nhóm 1 nói chỗ này dính lỗi nullable là chưa chính xác.
- `claim_task` (`delivery/confirmation/services.py:70`): `claimed_by` null → câu cũ luôn lỗi trên Postgres. Nay chỉ khoá
  ConfirmationTask, không giữ khoá DeliveryNote, nên không thể ngược thứ tự note → task của `record_call`/`decide` (giữ một
  khoá duy nhất thì không deadlock). `note.status` đọc không khoá: huỷ song song có thể để CSKH nhận một việc vừa huỷ, nhưng
  đây chỉ là khoá mềm, các bước ghi (`record_call` `:136-137`, decide `:544-546`) khoá note rồi kiểm lại. Chấp nhận.
- W37 S2-AC5 (đơn → phiếu ở `sales/orders/completion.py`) không bị đụng.
- Rà thêm các chỗ grep dễ sót: queryset dựng ở hàm khác (`_confirmable_payments`, `visible_actions_for`), related manager
  (`label_prints`, `lines`), manager mặc định (`ActiveReturnManager` chỉ filter, không select_related), các `.filter()`
  sau `select_for_update()`: không chỗ nào còn `select_related` tới FK null. Không có `prefetch_related` đi kèm khoá.

**(2) `costs/services.py:95` bắt `DataError`**: phạm vi `try` chỉ bọc `recompute_landed_cost`, nằm trong `transaction.atomic()`
của chính hàm, nên `BusinessError` thoát khỏi atomic sẽ rollback (hoặc rollback savepoint nếu có atomic ngoài) PurchaseCost,
phân bổ và AuditLog. Lỗi khác (IntegrityError, OperationalError...) không bị nuốt. Thông điệp không chứa số giá vốn; endpoint
chỉ Chủ (`add_purchasecost`). Test `test_n3_landed_cost_over_ten_integer_digits_is_400_by_allocations` khẳng định 0 PurchaseCost,
0 phân bổ, giá vốn lô không đổi. `recompute_landed_cost` chỉ có một caller nên không còn đường tràn nào ra 500.

**(3) Sửa test — không nới sai**
- `test_supplier_crud`: vẫn kiểm đủ tập tên và thứ tự các tên còn lại; đúng vì thứ tự theo collation DB.
- `test_qa_lo4_tien`: route `decide` tra theo `note_id` (`delivery/confirmation/api.py:46,68`, TL5-BE1); test cũ đúng ngẫu nhiên.
- `test_shop_labels`: `status` là `varchar(12)`; `FUTURE` vẫn là mã lạ nên ca kiểm vẫn giữ ý nghĩa.
- `test_seed_qa`: chỉ patch trong test, chỉ thêm `_staging` cho DB Postgres tên `test_*`. `guard.py` không đổi; các test chặn
  `postgres`/`cangca_prod`/host `prod-db`/`SEPAY_ENV=PRODUCTION` tự patch `database_facts` bằng `return_value` (đè lên patch nền)
  nên vẫn chặn thật.
- `test_s03_migration.tearDown`, `_fixture_setup` của test đua: chỉ là dọn trạng thái DB test, không đụng assert.

**Góp ý mức Thấp (không chặn merge, làm khi tiện):**
- L1 `apps/delivery/tests/test_completion_race_postgres.py` (`_fixture_setup`): sau `super()._fixture_setup()` nên gọi
  `ContentType.objects.clear_cache()`. Bộ nhớ đệm ContentType còn giữ id của bản do `post_migrate` tạo lại, trong khi DB đã
  quay về id gốc. Hiện test không dùng `get_for_model` nên chưa lộ.
- L2 `apps/accounts/audit/tests/test_s03_migration.py`: việc trả migration về leaf nằm trong `tearDown`, nên chỉ chạy khi `setUp`
  xong. Nếu `setUp` lỗi giữa chừng thì DB vẫn bị lùi. Nên đăng ký bằng `self.addCleanup(...)` ngay đầu `setUp`.
- L3 (có sẵn từ trước, không phải hồi quy) `purchasing/receipts/services.py:207`: khoá lô không có `order_by("pk")`, trong khi
  `record_purchase_cost` khoá theo pk. Thêm `.order_by("pk")` để hai luồng khoá cùng nhóm lô theo một thứ tự.
- Doc: bảng nhóm 1 nên ghi rằng `submit_receipt` không lỗi mà chỉ bỏ khoá kèm Item.

## QA (08/10)

**Kết luận: REJECTED.** Bản sửa đúng cho các đường từng lỗi 500 (huỷ/ghi nhận phiếu nhập, claim thường, chi phí quá lớn, lệnh AI huỷ phiếu), suite xanh trên cả hai DB. Nhưng QA tìm ra 2 lỗi đồng thời chỉ lộ trên PostgreSQL, cùng một gốc (xem dưới). Nhánh `qa/postgres-compat` HEAD 6673ae4 (main f3a543f + fix de8ff5b). Dữ liệu giả `seed_qa`; DB tạm (`cangca_qapg*`) đã xoá, server đã tắt.

**Tổng: 34 ca · ✅ 30 · ❌ 3 · ⏸ 1**

| # | Ca | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Suite PostgreSQL 16 (DB `cangca_qapg`), tuần tự | ✅ | `Ran 3405 tests in 464.8s — OK` (không skip) |
| 2 | Suite SQLite tuần tự, nhánh gộp | ✅ | `Ran 3405 tests in 336.5s — OK (skipped=2)` (2 ca đua chỉ chạy trên Postgres) |
| 3–30 | API thật trên BE chạy Postgres, bản sửa (28 bước, `scen.py`): huỷ phiếu Nháp (200) và huỷ lại (400 BR-MH-07); ghi nhận phiếu Nháp (200) và ghi nhận lại (400); huỷ phiếu đã ghi nhận lô Nháp (200); `receive-batches` rồi huỷ (201/200); huỷ phiếu có lô đang bán (400 BR-MH-07); chi phí quá lớn (400 `COST_LANDED_OVERFLOW`, 0 bản ghi mới); chi phí thường (201); Quản lý thêm chi phí (403); cs1 claim (200), cs2 claim khi cs1 giữ (409 CLAIMED), cs1 claim lại (200), chưa đăng nhập (401), Chủ claim khi cs1 giữ (409); AI `receive_batches` (đề xuất, xác nhận 200); AI `cancel` phiếu #6 (đề xuất, xác nhận 200, phiếu thành CANCELLED); AI undo lần 2 (400, không 500) | ✅ 25 / ❌ 2 / ⏸ 1 | `scratchpad/qapg/scen_fix.out`. Hai ❌ là claim đồng thời (B1). ⏸: AI undo của lệnh `receive_batches` vì ở cấu hình này lệnh là mức C, sau xác nhận trạng thái CONFIRMED nên undo trả 400 `AI_CANNOT_UNDO` đúng thiết kế; undo chỉ có ở mức B, không bật được mức B cho Chủ mà không đổi cấu hình AI. Đường `cancel_receipt` qua AI đã được kiểm bằng lệnh `cancel` trực tiếp (xanh) |
| 31 | Chứng minh bản sửa có tác dụng: cùng kịch bản trên `main` f3a543f (worktree tạm) | ✅ | `scen_main.out`: 14 đường trả lỗi: huỷ phiếu (5 lần, 500), chi phí quá lớn (500), claim (6 lần, 500), AI xác nhận huỷ phiếu (502 `AI_DISPATCH_FAILED`); ghi nhận phiếu vẫn 200 (khớp review techlead) |
| 32 | Race: huỷ phiếu ∥ thêm chi phí cùng lô, 36 vòng (Postgres, có lệch giờ ngẫu nhiên 0–120 ms) | ✅ không deadlock, không 500/502 | `race.py`; log server không có `deadlock` |
| 33 | Race: huỷ phiếu ∥ huỷ phiếu cùng phiếu, 12 vòng | ✅ | luôn (200, 400) |
| 34 | Race: huỷ phiếu ∥ thêm chi phí, kết quả nhất quán | ❌ | B2 |

### B1 — claim đồng thời: 500 `AttributeError` (High, chặn)

Bước tái hiện: Postgres, hai tài khoản `qa_cs1` và `qa_cs2` cùng lúc `POST /api/confirmation/queue/<note_id>/claim/` cho một việc chưa ai nhận (hai luồng, Barrier). Lặp: lần 1 `[200, 500]`; 6 luồng trên 1 việc `{200: 3, 409: 1, 500: 2}`.
Mong đợi: một 200, còn lại 409 `CLAIMED` (đây là đúng ca "hai người claim cùng lúc → 409" của yêu cầu).
Thực tế: người đến sau chờ khoá, thức dậy thì `task.claimed_by` là `None` dù `claimed_by_id` đã có, dòng `claimer_name = task.claimed_by.get_full_name()` (`delivery/confirmation/services.py:81`) ném `AttributeError` → 500.
Gốc: `select_for_update(of=("self",)).select_related("note", "claimed_by")`. Với `FOR UPDATE OF` bảng chính, Postgres khi tái kiểm tra dòng sau khi chờ khoá (READ COMMITTED) không nạp lại phía bị nối ngoài (LEFT JOIN `claimed_by`), nên nhận về NULL. Dữ liệu không hỏng (chỉ một người giữ), nhưng người dùng thấy lỗi thay vì "đang được X xử lý". Trước bản sửa, `main` luôn 500, nên đây là lỗi còn sót, không phải hồi quy.
Gợi ý sửa: bỏ `claimed_by` khỏi `select_related` của câu khoá, tra người đang giữ bằng `User.objects.get(pk=task.claimed_by_id)` sau khi đã khoá (hoặc `select_related("note")` rồi đọc `claimed_by` lazy). Thêm test hai luồng trên Postgres (`TransactionTestCase`, bỏ qua khi SQLite) cho `claim_task`.

### B2 — thêm chi phí ∥ huỷ phiếu: chi phí lọt vào lô của phiếu đã huỷ (High, chặn; vi phạm BR-MH-07)

Bước tái hiện: `receive-batches` 5 kg → hai luồng cùng lúc `POST /api/purchasing/receipts/<id>/cancel/` và `POST /api/purchasing/costs/` (chi phí 50000, phân bổ vào lô vừa tạo), luồng chi phí chậm hơn ngẫu nhiên 0–120 ms. 36 vòng cho kết quả (huỷ, chi phí): `(200, 400)` ×21, `(400, 201)` ×13, **`(200, 201)` ×2**.
Mong đợi: không bao giờ cả hai cùng thành công (hoặc 400 `BATCH_CANCELLED` cho chi phí, hoặc 400 BR-MH-07 cho huỷ phiếu).
Thực tế: hai vòng cả hai cùng 200/201. Truy vấn DB sau đó: 2 `PurchaseCostAllocation` (id 16, 17) trỏ vào lô `CANCELLED` của phiếu `CANCELLED`.
Gốc (nhiều khả năng cùng cơ chế B1): `record_purchase_cost` khoá lô bằng `select_for_update(of=("self",)).select_related("source_line__receipt")`; người đến sau chờ khoá lô, khi thức dậy phía nối (`source_line.receipt`, nối ngoài vì `source_line` là quan hệ ngược nullable) không được nạp lại nên `_is_cancelled_batch` vẫn thấy phiếu cũ → không chặn. Đoạn này có sẵn từ trước và trên main không bao giờ chạy tới (`cancel_receipt` luôn 500 trên Postgres), nay bản sửa nhóm 1 làm nó lộ ra.
Ảnh hưởng: chi phí mua gắn vào lô của chứng từ đã huỷ (số tiền bị tính vào lô 0 kg, sai giá vốn/lãi lỗ kỳ đó; vi phạm "huỷ bằng trạng thái, không đổi chứng từ đã huỷ"). Cửa sổ hẹp, chỉ Chủ thêm được chi phí.
Gợi ý sửa: sau khi khoá, nạp lại trạng thái phiếu bằng truy vấn riêng (`PurchaseReceipt.objects.filter(lines__batch_id__in=...)`) hoặc `refresh_from_db` lô rồi đọc `source_line.receipt` lazy, thay cho `select_related` qua quan hệ nullable; và khoá phiếu (`select_for_update` theo thứ tự phiếu → lô, giống `cancel_receipt`). Thêm test đua trên Postgres.

### Ghi nhận khác
- Rà `select_for_update(of=("self",))` kèm `select_related` tới quan hệ nullable: `claim_task` (B1) và `record_purchase_cost` (B2) bị; `cancel_receipt` chỉ dùng `line.batch_id` nên an toàn; `submit_receipt` nối trong (`item` NOT NULL), không thấy lỗi qua `submit` đúng 2 lần liên tiếp và test suite. Nên đưa việc "không tin dữ liệu join phía không khoá sau khi chờ khoá" vào hướng dẫn `django-drf-patterns`.
- Dữ liệu cá nhân: lệnh AI và API trên đây không trả/ghi tên, SĐT, địa chỉ (chỉ `display_name` của tài khoản `qa_*`); phản hồi lỗi không chứa giá vốn.

## Sửa theo QA (B1, B2)

Đã sửa 2 lỗi High của QA 08/10. Cùng một gốc: `select_for_update(of=("self",))` kèm `select_related` sang bảng khác. Khi phải chờ khoá, Postgres (READ COMMITTED) chỉ đọc lại dòng của bảng đã khoá. Phía nối không được nạp lại: nối ngoài cho giá trị NULL, nối trong giữ bản cũ.

**Quy tắc mới.** Trong câu có `select_for_update`, không `select_related` qua quan hệ ngược hoặc nullable. Quan hệ cần để quyết định thì đọc bằng truy vấn mới SAU khi đã khoá. Quan hệ cần ổn định thì khoá nó riêng trước, theo thứ tự khoá chung.

### B1 — `claim_task` (`delivery/confirmation/services.py`)
- Chứng minh gốc: test đua xác định (người giữ chưa commit, người thứ hai chờ khoá) đỏ 15/15 vòng với `AttributeError`. Test hai luồng cùng lúc đỏ 15/15 vòng (`['ERROR AttributeError', 'ok']`).
- Sửa: câu khoá chỉ còn `select_for_update(of=("self",))`. `note` và người đang giữ (`User`) đọc bằng truy vấn mới sau khoá. Luôn một 200, người còn lại 409 `CLAIMED` có tên người giữ.

### B2 — `record_purchase_cost` (`purchasing/costs/services.py`), BR-MH-07
- Chứng minh gốc: test đua xác định (huỷ phiếu giữ khoá, chi phí chờ) đỏ 15/15 vòng, chi phí được ghi vào lô của phiếu đã huỷ. Giữ nguyên code mới nhưng đặt lại `select_related("source_line__receipt")` thì vẫn đỏ 15/15. Bỏ `select_related` thì xanh. Vậy gốc là join, không phải thứ tự khoá.
- Sửa: khoá lô (`order_by("pk")`, không select_related), rồi hỏi trạng thái phiếu bằng truy vấn mới `PurchaseReceipt.filter(status=CANCELLED, lines__batch_id__in=…)`. Bỏ hàm `_is_cancelled_batch`.
- Vì sao chọn cách này mà không khoá phiếu trước: `cancel_receipt` khoá phiếu rồi dòng rồi lô. Chi phí chỉ khoá lô và không khoá phiếu, nên không bao giờ giữ lô rồi chờ phiếu, không có chu trình chờ, không deadlock. Hai thứ tự đều đúng.
  - Huỷ vào trước: chi phí chờ khoá lô, thức dậy thấy phiếu CANCELLED, trả 400 `BATCH_CANCELLED`.
  - Chi phí vào trước: huỷ chờ khoá lô, thức dậy thấy `cost_allocations`, trả 400 BR-MH-07 (kiểm sẵn trong `cancel_receipt`).
  - Khoá phiếu trong đường chi phí thì phải thêm một bước khoá nữa mà không được gì thêm, nên bỏ.

### Rà toàn bộ `backend/apps`
Mọi `select_for_update(` (khoảng 75 chỗ) đã được rà. Chỗ có `of=` hoặc `select_related` kèm khoá:

| Vị trí | Xử lý |
|---|---|
| `confirmation.claim_task` | Sửa (B1) |
| `costs.record_purchase_cost` | Sửa (B2) |
| `confirmation.escalate_unreachable` (khoảng dòng 677, `select_related("note")`) | Sửa: bỏ select_related, dùng `note_obj` đã khoá |
| `receipts.submit_receipt` (`select_related("item")`) | Sửa: bỏ select_related, thêm `order_by("pk")` |
| `receipts.cancel_receipt` (`select_related("batch")`, quan hệ nullable; chỉ dùng `batch_id`) | Sửa: bỏ select_related, thêm `order_by("pk")` |
| `run_due_ai_actions._mark_failed` (`select_related("owner")`) | Sửa: bỏ select_related (owner đọc lazy) |

Các chỗ còn lại là `Model.objects.select_for_update().get/filter(...)` không join, hoặc `skip_locked` không join: giữ nguyên. Thứ tự khoá không đổi ở chỗ nào, nên không có rủi ro deadlock mới.

### Test mới (PostgreSQL, bỏ qua trên SQLite)
- `backend/apps/delivery/tests/test_claim_race_postgres.py`: 2 test, mỗi test 15 vòng.
- `backend/apps/purchasing/costs/tests/test_cost_cancel_race_postgres.py`: 2 test, 15 vòng và 30 vòng (lệch giờ 0 đến 50 ms). Cặp kết quả chỉ được là (huỷ ok, chi phí `BATCH_CANCELLED`) hoặc (huỷ `BR-MH-07`, chi phí ok); không có chi phí nào trỏ vào lô của phiếu đã huỷ.
- Trước khi sửa: 45 subtest đỏ (B1 30, B2 15). Sau khi sửa: xanh.

### Kết quả kiểm chứng (08/10, sau sửa)
- PostgreSQL 16, DB riêng `cangca_b12`, toàn suite: `Ran 3409 tests in 282.515s — OK` (không skip).
- SQLite tuần tự, toàn suite: `Ran 3409 tests in 196.660s — OK (skipped=6)` (6 ca đua chỉ chạy trên Postgres).
- `makemigrations --check --dry-run`: No changes detected. `check_naming.py`: OK, không vi phạm mới.

## Review techlead B1/B2 (08/10)

**Kết luận: REVIEW PASS — APPROVED** (commit `ba3b213`). Không có lỗi chặn; 4 ghi chú Low, sửa khi tiện.

### (1) B2 `record_purchase_cost` ∥ `cancel_receipt` (BR-MH-07, giá vốn)
- **Huỷ vào trước, chi phí chờ khoá lô.** `FOR UPDATE` trả bản lô mới nhất; truy vấn `PurchaseReceipt(status=CANCELLED, lines__batch_id__in=…)` là câu lệnh mới nên có snapshot mới (READ COMMITTED) và thấy phiếu CANCELLED → 400 `BATCH_CANCELLED`. Đúng.
- **Cửa sổ huỷ đã khoá phiếu+dòng nhưng chưa tới lô, chi phí khoá lô trước.** Chi phí đọc phiếu thấy SUBMITTED (huỷ chưa commit), ghi allocation, commit, nhả lô. Huỷ lấy được khoá lô, `batch.cost_allocations.exists()` là câu mới nên thấy allocation → 400 BR-MH-07, rollback toàn bộ. Kết quả hợp lệ (chi phí vào lô thật của phiếu còn hiệu lực).
- **Deadlock khi chi phí phân bổ nhiều lô thuộc nhiều phiếu.** Chi phí chỉ giữ khoá lô (cộng FOR KEY SHARE lên lô đã giữ khi insert allocation, `recompute_landed_cost` chỉ save lô đã khoá), không bao giờ chờ phiếu hay dòng. Huỷ chờ phiếu/dòng (chi phí không giữ) và lô. Cả hai khoá lô bằng một câu `ORDER BY pk` (LockRows nằm trên Sort nên khoá theo thứ tự pk). Các lệnh huỷ khác nhau khoá tập lô rời nhau. Không có chu trình chờ.
- Hành vi giữ nguyên: lô không có `source_line` vẫn nhận chi phí; lô CANCELLED do quá hạn (BR-LO-03) vẫn nhận chi phí đến muộn (E-14, BR-GV-02) vì chỉ xét trạng thái phiếu.

### (2) B1 `claim_task`
- Câu khoá chỉ còn bảng `ConfirmationTask`; `note` và `User` người giữ đọc bằng truy vấn mới sau khoá → luôn thấy bản đã commit. `note` không khoá, giống trước (`of=self`), nên không hồi quy.
- 409 `CLAIMED` chỉ chứa `get_full_name()`/`username` của **nhân viên** và `claimed_until`. Không có tên, SĐT hay địa chỉ khách. Không log. Đạt bất biến 9.

### (3) Bốn chỗ sửa thêm
- `escalate_expired_windows` (doc ghi nhầm tên `escalate_unreachable`): vẫn khoá phiếu → task; dùng `note_obj` đã khoá thay `task.note`, đúng hơn bản cũ.
- `submit_receipt`: phiếu → dòng (thêm `order_by("pk")`); `line.item` đọc lazy (thêm N truy vấn nhỏ, chấp nhận được).
- `cancel_receipt`: phiếu → dòng → lô không đổi; chỉ dùng `line.batch_id`.
- `_mark_failed`: `skip_locked` trên một dòng `AiAction`, `owner` đọc lazy; `.first()` thêm ORDER BY pk, vô hại.
- Không còn chỗ nào `select_for_update` kèm `select_related` trong `backend/apps` (đã grep cả chuỗi nhiều dòng).

### (4) Test đua — techlead tự chạy (DB riêng `cangca_tlb12`, đã xoá)
- Code cũ `a69f380` + test mới: `test_b1_waiter…` đỏ 15/15, `test_b1_two_claims…` đỏ 15/15, `test_b2_cost_waiting_on_lock…` đỏ 15/15. Vậy test chờ khoá bắt được lỗi một cách xác định, không pass ngẫu nhiên.
- Code mới `ba3b213`: 3 lần liên tiếp `Ran 4 tests … OK`. SQLite: `OK (skipped=4)`.

### Ghi chú Low (không chặn)
- **L1.** `test_cost_cancel_race_postgres.py:96` có `outcomes_seen` được gán nhưng không bao giờ assert, là code chết. Nên assert `len(outcomes_seen) == 2` (đo được: cả hai cặp đều xuất hiện trong mọi lần chạy) hoặc xoá biến.
- **L2.** `test_b2_cancel_and_cost_at_once_never_both_succeed` **xanh trên code cũ** (`a69f380`, đã chạy): lệch 0–50 ms không tạo ra ca chờ khoá. Lỗi B2 thật chỉ được `test_b2_cost_waiting_on_lock…` bắt. Ghi chú này để tránh hiểu nhầm là test đó canh B2. Cần giữ nó làm test bất biến "không bao giờ cả hai thành công".
- **L3.** Khi xoá `_is_cancelled_batch` (`costs/services.py`), đã mất lý do vì sao không xét `batch.status` (lô huỷ do quá hạn vẫn nhận chi phí muộn, E-14, BR-GV-02). Nên thêm lại một dòng comment cạnh `cancelled_batch_ids` để người sau không “sửa” thành kiểm `batch.status`.
- **L4.** Các test chờ khoá dựa vào `time.sleep(0.4)`. Hiện đỏ 15/15 trên code cũ nên đủ dùng; nếu CI chậm có thể thay bằng vòng chờ `pg_stat_activity.wait_event_type = 'Lock'`.

### Skill
Đã thêm quy tắc "khoá dòng không kèm join; quan hệ dùng để quyết định thì đọc lại sau khoá; test đua có ca chờ khoá" vào `.claude/skills/django-drf-patterns/SKILL.md`, mục Service.

## QA vòng 2 (08/10)

**Kết luận: APPROVED.** B1 và B2 đã sửa, kiểm trên BE thật chạy PostgreSQL 16 (DB riêng `cangca_qapg2_staging`, `seed_qa --allow-non-local`, dữ liệu giả; DB đã xoá, server đã tắt). Nhánh `qa/postgres-compat` HEAD eb3d517. Không sửa code. Suite đầy đủ không chạy lại theo yêu cầu (điều phối viên đã chạy: Postgres 3409 OK, SQLite 3409 OK skipped=6).

**Tổng: 36 ca · ✅ 35 · ❌ 0 · ⏸ 1**

| # | Ca | Kết quả | Bằng chứng (`scratchpad/qapg2/`) |
|---|---|---|---|
| 1 | B1 hai người (qa_cs1 ∥ qa_cs2) claim cùng một việc, Barrier, 24 vòng (reset claim bằng SQL giữa vòng) | ✅ | `claim_race.out`: 24/24 đúng `{200:1, 409:1}`, không 500 |
| 2 | B1 sáu luồng (cs1, cs2, owner, manager, cs1, cs2) cùng một việc, 18 vòng | ✅ | 10 vòng `{200:1, 409:5}`, 8 vòng `{200:2, 409:4}`; 200 thứ hai luôn là chính người đang giữ gọi lại (idempotent). Mọi vòng đúng một người giữ, không 500, không `AttributeError` |
| 3 | Thân 409 không có dữ liệu khách | ✅ | Mọi 409 chỉ có khoá `detail`, `code=CLAIMED`, `claimed_until`; `detail` chỉ có username nhân viên và giờ; không số dài, không mã đơn/phiếu |
| 4 | B2 huỷ phiếu ∥ chi phí, chi phí chậm 0–120 ms (kịch bản vòng 1), 48 vòng | ✅ | `race.out`: `(200,400)` ×48, không `(200,201)` |
| 5 | B2 đảo thứ tự (huỷ chậm 0–120 ms), 48 vòng | ✅ | `race_swap.out`: `(400,201)` ×48 |
| 6 | B2 lệch giờ hai phía 0–30 ms, 48 vòng (kết quả trộn cả hai chiều) | ✅ | `race_both.out`: `(400,201)` ×29, `(200,400)` ×19, không `(200,201)` |
| 7 | DB sau 144 vòng: không có `PurchaseCostAllocation` trỏ lô của phiếu CANCELLED | ✅ | 0 dòng (truy vấn nối allocation → lô → dòng phiếu → phiếu `CANCELLED`); truy vấn có hiệu lực: cùng nối cho 78 allocation ở phiếu SUBMITTED, 90 phiếu CANCELLED |
| 8 | Không deadlock, không 500/502 | ✅ | `race*.out`: danh sách 500/502 rỗng; `server.log`: 0 `deadlock`, 0 `" 500 `/`" 502 `, 0 `Traceback`, 0 `AttributeError` (693 POST) |
| 9 | Huỷ phiếu ∥ huỷ phiếu cùng phiếu (6 vòng × 3 lần chạy) | ✅ | luôn `(200,400)` |
| 10–31 | Hồi quy `scen.py` (28 bước): receive-batches rồi huỷ; huỷ phiếu có lô đang bán 400 BR-MH-07; chi phí quá lớn 400 `COST_LANDED_OVERFLOW` (0 bản ghi mới); chi phí thường 201; Quản lý thêm chi phí 403; claim thường 200, người khác 409, giữ lại 200, chưa đăng nhập 401, Chủ khi cs1 giữ 409; AI `receive_batches` đề xuất + xác nhận; AI `cancel` phiếu → CANCELLED; AI undo lần 2 trả 400 không 500 | ✅ 22 | `scen.out`. Có 5 bước "404" chỉ vì `scen.py` gắn cứng id phiếu #4/#5 của DB vòng 1; không phải lỗi sản phẩm, đã chạy lại bằng `reg.py` (ca 32–36) |
| 32–36 | Hồi quy phiếu Nháp: tạo, huỷ (200), huỷ lại (400 BR-MH-07); tạo, ghi nhận (200), ghi nhận lại (400 màn hình cũ), huỷ phiếu đã ghi nhận (200) | ✅ 5 | `reg.py` |
| — | AI undo của `receive_batches` | ⏸ | Giống vòng 1: lệnh mức C, sau xác nhận là CONFIRMED nên undo 400 `AI_CANNOT_UNDO` đúng thiết kế; không bật mức B mà không đổi cấu hình AI. Đường `cancel_receipt` qua AI đã kiểm bằng lệnh `cancel` |

Lưu ý: ca 4 và 5 mỗi bên chỉ một chiều thắng ổn định theo độ lệch; chiều còn lại và cả hai chiều trộn được phủ ở ca 6, cộng 2 test chờ khoá của techlead (đỏ trên code cũ). Không có lỗi mới.
