# QA — P8 Sửa lỗi review P1–P7

## Lô 1 — SR-01, SR-02, SR-03 · lần 1 · 2026-09-30

### Kết luận: APPROVED — 0 lỗi Critical/High/Medium; mọi AC chạy thật xanh, test đỏ trên HEAD và xanh trên working tree
### Tổng: 55 ca · ✅ 54 · ❌ 0 · ⏸ 1 (tranh chấp 2 tiến trình job cần Postgres, không phải AC)

Phạm vi: code chưa commit trong working tree (`safety.py`, `run_due_ai_actions.py`, `cost_keys.py`, `erp-console/package*.json`, 2 file `__init__.py`,
2 file test của dev). Lô 1 không có AC giao diện (SR-02 là cài đặt phụ thuộc, SR-01/03 là BE) nên không cần Playwright; bằng chứng là lệnh chạy thật.
Không sửa code sản phẩm. QA thêm 2 file test: `backend/apps/accounts/audit/tests/test_p8_lo1_qa_edges.py` (4 test),
`backend/apps/ai/execution/tests/test_p8_lo1_qa_edges.py` (11 test).

## Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| SR-01-AC1 quan_ly không thấy `loss_amount`, JSON không chứa `812340` | ✅ | `test_sr01_ac1_...` xanh. **Đỏ trên HEAD** (worktree `git archive HEAD` + test mới): 4 FAIL / 20. Thêm QA `test_qa_filter_actor_kind_va_action_khac_van_khong_lo` (6 biến thể lọc) |
| SR-01-AC2 Chủ thấy đủ | ✅ | `test_sr01_ac2_chu_thay_du_loss_amount` (`812340`); trong scan còn thấy `1012340` |
| SR-01-AC3 quét mọi khoá tiền | ✅ | `test_sr01_ac3_quet_...`: đủ 3 dòng audit (`recompute_landed_cost`, `cancel_expired_batch`, `close_batch`), khoá nhạy cảm có thật trong DB, `ok_responses > 0`, quét đệ quy `changes` + `note`; `test_sr01_ac3_cost_keys_co_du_khoa_tien` khoá 8 khoá. `return_batch_to_supplier` chưa có (Lô 5) — ghi nhận, không tính |
| SR-01-AC4 AuditLog không bị sửa | ✅ | `test_sr01_ac4_...` + QA `test_qa_khong_co_route_chi_tiet_hay_ghi` (POST/PUT/PATCH/DELETE = 405, `/audit-logs/<id>/` = 404, bản gốc vẫn còn `loss_amount`) |
| SR-02-AC1 tái hiện `npm ci` lỗi | ✅ | Đỏ trên HEAD: `package.json`+lock từ `git show HEAD:` vào thư mục tạm, `npm ci` → `ERESOLVE could not resolve ... vitest@5.0.2 ... @types/node@20.19.43`, exit 1 |
| SR-02-AC2 `npm ci` sạch (không cờ) — erp-console | ✅ | `rm -rf node_modules && npm ci --cache <scratchpad>` → `added 189 packages`, exit 0; grep `ERESOLVE|legacy` = 0 dòng; lock không đổi sau `ci` |
| SR-02-AC2 `npm ci` sạch — frontend | ✅ | `rm -rf node_modules && npm ci` exit 0, không ERESOLVE; `git status frontend` sạch (không sửa gì) |
| SR-02-AC3 erp-console: tsc + build + test | ✅ | `tsc --noEmit` exit 0; `npm run build` exit 0; `npm test` 9 files / 79 tests passed |
| SR-02-AC3 frontend: tsc + build | ✅ | `tsc --noEmit` exit 0; `npm run build` exit 0 |
| SR-02-AC4 diff lock chỉ do `@types/node` | ✅ | `git diff --stat erp-console`: 2 file, 5+/5-; chỉ đổi dòng `@types/node` (devDependencies ×2 + khối `node_modules/@types/node` 20.19.43→22.20.4). Không thư viện nào thêm/bớt, `next/react/vitest/vite/typescript` không đổi |
| SR-03-AC1 lô đã bán không `FieldError` | ✅ | `test_sr03_ac1_...` xanh; đỏ trên HEAD: `FieldError: Unsupported lookup 'order_id'` |
| SR-03-AC2a phiếu hoàn PENDING (theo hoá đơn / theo giao dịch) chặn chốt | ✅ | 2 test riêng xanh (đỏ trên HEAD); đối chứng RESOLVED/REFUNDED không chặn |
| SR-03-AC2b `PaymentTransaction` OPEN chặn chốt | ✅ | `test_sr03_ac2b_...` xanh |
| SR-03-AC3 poison pill R1b | ✅ | `test_sr03_ac3_job_khong_chet_...` (DONE, lô CLOSED, việc sau DONE, việc quá hạn 2 giờ ESCALATED) + `..._con_phieu_hoan_pending_thi_escalated`. **Repro R1 gốc** chạy lại: `test_r1_safety_crashes_for_sold_batch` → `AssertionError: Exception not raised`; `test_r1_job_poison_pill` → `R1 job: no crash`, `R1 action status after job: DONE` |
| SR-03-AC4 exception bất kỳ → FAILED, log sạch, idempotent | ✅ | `test_sr03_ac4_...` (sentinel `SECRET-KHACH-GIA-0900000123` không có trong log DEBUG/AuditLog/`downgrade_reason`, rollback thay đổi dở, chạy lần 2 `call_count == 0`). QA thêm 2 poison pill + 1 việc tốt ở giữa, và poison pill thật không mock |
| SR-03-AC5 API không 500 | ✅ | `test_sr03_ac5_api_chu_lo_da_ban_khong_500` (200 `scheduled`), `..._giao_dich_open_ha_muc_c` (200 `proposal`); QA thêm ca phiếu hoàn PENDING → 200 `proposal`, body không chứa tên/SĐT/địa chỉ giả |

## Ngoại lệ & biên (ca QA bổ sung, ngoài đường thuận)
| Ca | Kết quả | Test |
|---|---|---|
| Lô đã từng bán (phân bổ bán + đơn COMPLETED + hoá đơn) rồi chốt qua AI | ✅ | dev AC1/AC3 + `test_qa_job_chay_2_lan_viec_done_khong_chot_lai` |
| Phiếu hoàn PENDING của đơn **khác lô** không chặn nhầm; lô kia vẫn bị chặn | ✅ | `test_qa_phieu_hoan_pending_cua_don_KHAC_lo_khong_chan` |
| Lô bán qua 2 đơn, chỉ 1 đơn có giao dịch OPEN → chặn | ✅ | `test_qa_lo_ban_qua_nhieu_don_chi_can_mot_don_vuong_la_chan` |
| Lô chưa từng bán (nhánh `order_ids` rỗng) vẫn đúng | ✅ | `test_qa_lo_chua_tung_ban_van_dung` |
| Job chạy 2 lần, việc ESCALATED: không nhân đôi audit `escalate_*`, lô không bị chốt | ✅ | `test_qa_job_chay_2_lan_viec_escalated_khong_nhan_doi` |
| Job chạy 2 lần, việc DONE: chỉ 1 audit `execute_*` | ✅ | `test_qa_job_chay_2_lan_viec_done_khong_chot_lai` |
| Màn hình cũ: việc đổi trạng thái (không còn SCHEDULED) giữa lúc job đọc và khoá → job không dispatch | ✅ | `test_qa_viec_da_bi_huy_giua_chung_khong_bi_job_chay` |
| Poison pill **thật** (không mock, `target_id` lô không tồn tại) → FAILED/ESCALATED, việc sau vẫn DONE | ✅ | `test_qa_exception_that_khong_mock_target_khong_ton_tai_thanh_failed` |
| 2 poison pill (đầu, cuối) + việc tốt ở giữa: FAILED/DONE/FAILED, đúng 2 dòng `fail_*`, không sentinel PII | ✅ | `test_qa_hai_poison_pill_o_giua_va_cuoi_viec_tot_o_giua_van_done` |
| Chính bước ghi FAILED lỗi (DB) → job không văng, việc lỗi còn SCHEDULED (không mất, lần sau thử lại), việc sau vẫn chạy | ✅ | `test_qa_mark_failed_loi_thi_job_van_chay_tiep` |
| Bấm đúp cùng `idempotency_key` → 1 `AiAction`, lần 2 200 | ✅ | `test_qa_api_bam_dup_khong_tao_2_viec_khi_cung_khoa` |
| Hai tiến trình job đồng thời (`skip_locked`) | ⏸ | SQLite không hỗ trợ khoá dòng; chưa kiểm được đồng thời thật. Logic đọc: chỉ đổi khi còn SCHEDULED. Ghi nhận cho lô kiểm trên Postgres staging |

## Phân quyền
| Group | `GET /api/audit-logs/` | `POST /api/ai/commands/inventory.batch.close/call/` |
|---|---|---|
| chu | ✅ 200, thấy `loss_amount` | ✅ 200 (`scheduled` / hạ `proposal` C khi còn phiếu hoàn/giao dịch OPEN) |
| quan_ly | ✅ 200, không có `loss_amount` | ✅ 404 `COMMAND_UNKNOWN` |
| nv_kho | ✅ 403 | ✅ 404 `COMMAND_UNKNOWN` |
| nv_giao | ✅ 403 | ✅ 404 `COMMAND_UNKNOWN` |
| cskh | ✅ 403 | ✅ 404 `COMMAND_UNKNOWN` |
| khách (chưa đăng nhập) | ✅ 401 | ✅ 401 |

Ghi nhận cho điều phối (không phải lỗi code): ô `403` trong ma trận SR-03 của `02-stories.md` là lỗi viết story, đúng là 404 `COMMAND_UNKNOWN`
(Tech Lead đã chốt ở `03b`; registry cố ý ẩn lệnh với người thiếu quyền). Cần sửa chữ ở 02-stories (QA không sửa file `02*.md`).

## Rò giá vốn
- ✅ `quan_ly` gọi `/api/audit-logs/` sau `recompute_landed_cost` → `cancel_expired_batch` → `close_batch`: không khoá nào ∈ `COST_KEYS` trong mọi `changes` ở mọi trang (đếm 200 > 0, phân trang), không có `81234`/`101234`/`812340`/`1012340` trong `changes` + `note`. `nv_kho`/`nv_giao`/`cskh` 403 nên không thấy gì.
- ✅ Tính ngược tiền ÷ kg: `note` của `cancel_expired_batch` chỉ có số kg (`cancel_expired_batch 10.000kg`), `changes` còn `qty` nhưng không còn `loss_amount`. Đã rà thủ công toàn bộ 79 lời gọi `record_audit(` trong `apps/`: khoá tiền còn lại là `amount`, `bank_amount`, `refund_amount`, `overpaid_amount`, `total_amount`, `paid_total`, `suggest_refund_amount` — đều là giá **bán**/tiền khách trả, không chia được ra giá vốn; `landed_unit_cost` (2 dòng) đã nằm trong `COST_KEYS`.
- ✅ Đường đọc thứ hai của cùng dòng audit: `GET /api/guidance/batch/<id>/` — quan_ly thấy "Chủ đã huỷ lô" không số, Chủ thấy "Huỷ lô quá hạn (lỗ ...)" (test có assert cả hai để không xanh giả).
- ✅ Không có route chi tiết `/audit-logs/<id>/` và không có tham số lọc/tìm theo giá trị `changes` (không có "oracle" dò số).
- ✅ Không lọc nhầm: rà tên khoá mới trong serializer/dashboard (`loss`, `margin`, `gross_profit` không có ở đâu; `inventory_value` chỉ ở KPI dashboard đã gắn `can_cost`; `expired_cost` chỉ ở `batch_pnl` của Chủ). Toàn bộ suite AI/accounts/common vẫn xanh.
- ✅ Khoá mới ghi vào `AuditLog` ở Lô 1: chỉ `fail_inventory.batch.close` (không `changes`, `note` cố định); không có số tiền, không có tên/SĐT/địa chỉ khách.
- ✅ AI registry: quan_ly gọi `/api/ai/commands/index/` (không rỗng); không có lệnh đọc audit-log trong registry. `SCRUB_COST_KEYS = COST_KEYS` nên 8 khoá mới cũng bị lọc khỏi kết quả lệnh AI (siết thêm, suite AI xanh).

## Rò dữ liệu cá nhân
- ✅ Log job: chỉ `id việc + mã lệnh + tên lớp exception`. Bắt bằng `assertLogs(level="DEBUG")` trên root logger với exception chứa sentinel `SECRET-KHACH-GIA-0900000123` (RuntimeError và KeyError): không có sentinel, không `str(exc)`.
- ✅ Dòng audit `fail_*` và `AiAction.downgrade_reason/args/result_ref`: không chứa sentinel.
- ✅ Response API `inventory.batch.close/call/` với đơn của "Khách Giả A" / `0900000999` / "Số 1 Đường Giả": body không chứa tên, SĐT, địa chỉ.
- ✅ Nhật ký (`/api/audit-logs/`) không thêm trường cá nhân ở Lô 1. Không có FE/console/`localStorage`/URL ở lô này (không có thay đổi FE ngoài `package*.json`).
- Dữ liệu test và fixture: chỉ số/tên giả. Không có ảnh chụp.

## Hồi quy
| Lệnh | Kết quả |
|---|---|
| `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` (không `--parallel`), lần 1 (trước khi QA thêm test) | ✅ `Ran 1140 tests ... OK` |
| Như trên, sau khi QA thêm 15 test | ✅ `Ran 1155 tests ... OK` |
| `manage.py makemigrations --check --dry-run` | ✅ `No changes detected` |
| `cd adapter && .venv/bin/python -m pytest -q` | ✅ `68 passed` |
| Test trước đây bị bỏ qua vì thiếu `__init__.py` (57 test `apps/ai/execution/tests/` + 11 test `content/entries/tests/`) | ✅ nay được discover và xanh trong 1140/1155 |
| Test của dev trên **HEAD** (không có bản sửa) | ✅ đỏ đúng lý do: `Ran 20 tests`, FAILED (failures=4, errors=13); 10 lỗi `FieldError: Unsupported lookup 'order_id'`; 3 test không đỏ là ca đối chứng (AC2, ma trận, AC4) |

## Lỗi
Không có lỗi chặn (Critical/High/Medium). Ghi nhận không chặn (Low / nợ, đã có trong `03b`, không phát sinh mới từ QA):
- N1 (Low, nợ L4 của `03b`): nhánh `AI_ENABLED=False` của `run_due_ai_actions` chưa cô lập lỗi từng việc. Chỉ `save`, không dispatch nên rủi ro thấp.
- N2 (Low, nợ L5 của `03b`): việc `FAILED` chỉ hiện với owner; nếu owner không phải Chủ thì Chủ thấy qua Nhật ký `fail_*`, không có trong hộp việc.
- N3 (tài liệu): ô `403` trong ma trận SR-03 của `02-stories.md` nên sửa thành `404 COMMAND_UNKNOWN`.
- N4 (chưa kiểm được): tranh chấp 2 tiến trình job cùng lúc cần Postgres (SQLite không có `SELECT ... FOR UPDATE`).

## Lệnh đã chạy (tóm tắt output)
```
backend  DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test                       -> Ran 1140 tests OK ; sau khi thêm test QA: Ran 1155 tests OK
backend  manage.py makemigrations --check --dry-run                                                -> No changes detected
backend  manage.py test apps.accounts.audit.tests.test_p8_lo1_qa_edges                             -> Ran 4 OK
backend  manage.py test apps.ai.execution.tests.test_p8_lo1_qa_edges                               -> Ran 11 OK
HEAD-copy (git archive HEAD backend + 2 test dev)  manage.py test ...test_p8_cost_keys_scan ...test_p8_close_batch_sold
                                                                                                   -> Ran 20, FAILED (failures=4, errors=13)  [đỏ trên HEAD]
repro R1 (PYTHONPATH=scratchpad ... review_repro.tests.R1AiCloseBatchSoldBatch)                    -> "Exception not raised" ; "R1 job: no crash" ; status DONE
adapter  .venv/bin/python -m pytest -q                                                             -> 68 passed
erp-console  rm -rf node_modules && npm ci --cache <scratchpad>                                    -> added 189 packages, exit 0, 0 dòng ERESOLVE/legacy
erp-console  npx tsc --noEmit -> 0 ; npm run build -> 0 ; npm test -> 9 files, 79 tests passed
frontend     rm -rf node_modules && npm ci --cache <scratchpad> -> exit 0 ; npx tsc --noEmit -> 0 ; npm run build -> 0
HEAD package.json+lock (thư mục tạm)  npm ci                                                       -> npm error code ERESOLVE (vitest@5.0.2 vs @types/node 20.19.43), exit 1  [đỏ trên HEAD]
```
