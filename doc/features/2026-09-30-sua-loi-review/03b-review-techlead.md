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
