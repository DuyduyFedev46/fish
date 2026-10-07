# Sửa lỗi chỉ lộ trên PostgreSQL (08/10)

Production và staging chạy PostgreSQL 16 (Supabase), nhưng test xưa nay chạy SQLite nên một số lỗi lọt. Ngày 08/10 chạy
cả suite trên PostgreSQL 16 cục bộ: Ran 3384, failures=13, errors=51 (main d0854a7). Sau khi sửa: xem mục "Số test".

## Nguyên nhân và cách sửa

| Nhóm | Nguyên nhân | Cách sửa |
|---|---|---|
| 1. `FOR UPDATE cannot be applied to the nullable side of an outer join` (~27 ca: huỷ phiếu nhập, publish lô, claim việc gọi xác nhận, ...) | `select_for_update()` kèm `select_related` tới FK cho phép null (`PurchaseReceiptLine.batch`, `ConfirmationTask.claimed_by`). SQLite bỏ qua khoá nên không lộ. | `select_for_update(of=("self",))`: chỉ khoá dòng của bảng chính, giữ nguyên thứ tự khoá (đơn, rồi phiếu, rồi việc). Sửa 3 chỗ: `purchasing/receipts/services.py` (cancel_receipt, submit_receipt), `delivery/confirmation/services.py` (claim_task). Đã rà mọi `select_for_update` trong `backend/apps`: các chỗ còn lại không kèm `select_related`. |
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
