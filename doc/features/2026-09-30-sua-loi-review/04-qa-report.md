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

---

## Lô 2 — SR-04, SR-05, SR-06, SR-07 · lần 1 · 2026-09-30

### Kết luận: APPROVED — 0 lỗi Critical/High/Medium; mọi AC chạy thật xanh, test đỏ trên HEAD và xanh trên working tree; 3 ghi nhận Low và 1 giới hạn thiết kế (G1) cần Tech Lead/PO chốt, không chặn
### Tổng: 44 ca · ✅ 43 · ❌ 0 · ⏸ 1 (SR-05-AC5 "cùng commit": chưa có commit, để điều phối kiểm khi commit)

Cách đếm: 16 ca theo AC (SR-04 x3, SR-05 x5, SR-06 x4, SR-07 x4) + 28 ca ngoài đường thuận / phân quyền / hồi quy ở các bảng dưới. Mỗi script Playwright (nhiều
điểm kiểm) tính là 1 ca trong bảng ngoại lệ; số điểm kiểm ghi cạnh.

Phạm vi: code chưa commit trong working tree (`rules.py`, `discovery.py`, `pipeline.py`, `actions/services.py`, `orders/scope.py`, `orders/api.py`, `orders/next_steps.py`,
`draftStorage.ts`, `NhapLoForm.tsx`, `AuthProvider.tsx` + test dev). Không sửa code sản phẩm. QA thêm: `backend/apps/ai/registry/tests/test_p8_qa_lo2_sweep.py` (4 test),
`backend/apps/sales/orders/tests/test_p8_qa_lo2_matrix.py` (12 test), `erp-console/e2e/sr07_qa_edges.py` (Playwright, 2 chế độ mock/real), ảnh trong `qa-lo2/qa-sr07-*.png`.
Dữ liệu chỉ là giả (Khách Giả Bí Mật, 0900000xxx, Số 1 Đường Giả, NGUYEN VAN GIA, mật khẩu demo).

## Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| SR-04-AC1 nv_kho `dashboard_summary` không có "Khách Giả Bí Mật" | ✅ | `test_sr04_ac1_nv_kho_dashboard_khong_lo_ten_khach` (còn assert có mã đơn -> không xanh giả vì rỗng) + bản Chủ. Đỏ trên HEAD (xem dưới) |
| SR-04-AC2 `customer` chuỗi/dict/list + `recipient_phone`, `phone_last4`, `phone_masked` bị bỏ cả nhánh | ✅ | `test_p8_scrub_pii` 6 test xanh (gồm hoa/thường, tập khoá đủ khoá mới) |
| SR-04-AC3 quét mọi lệnh đọc (list + retrieve) x 5 Group | ✅ | Dev `test_sr04_ac3_quet_...` xanh (ok_total > 0, retrieve_ok > 0). **QA bù, dữ liệu CÓ TRONG PHẠM VI** (techlead L2): `RichScopeSweep.test_quet_5_group_tren_du_lieu_trong_pham_vi`. Số response 200: chu 42, quan_ly 38, nv_kho 28, **nv_giao 5, cskh 3** (chi tiết 19/17/14/2/2); 0 vi phạm với 10 chuỗi (tên, SĐT, địa chỉ, tên người chuyển, người nhận + SĐT người nhận, ghi chú phiếu/khách, địa chỉ mặc định) và 0 khoá PII; quét thêm regex khoá `phone|address|recipient|payer|customer|contact|holder|receiver|sender|email` ngoài tập lọc: **không có khoá nào** |
| SR-05-AC1 `inventory.batch.retrieve` Chủ 200 | ✅ | `test_sr05_ac1_chu_retrieve_lo_tra_du_lieu` xanh; đỏ trên HEAD (502 `AI_DISPATCH_FAILED`) |
| SR-05-AC2 mọi `retrieve`/`partial_update`/`update`/`destroy` có `detail=True` | ✅ | `test_sr05_ac2_...` xanh (duyệt toàn registry, `seen > 0`) |
| SR-05-AC3 nv_giao đề xuất mức C ngoài phạm vi -> 404 `NOT_FOUND`, không AiAction | ✅ | Dùng `delivery.deliverynote.partial_update` (H7 cấm `sales.salesorder.partial_update`, techlead đã chốt): `test_sr05_ac3_...` xanh, đối chứng phiếu gán cho mình = 200 `proposal`; `test_sr05_ac3_salesorder_partial_update_khong_ton_tai_trong_registry` 5 Group đều 404. QA thêm `test_orders_retrieve_nv_giao_chi_thay_don_cua_minh` (đơn của mình 200, đơn khác 404, không PII) |
| SR-05-AC4 `reports.batch_pnl` + `target_id` không 500 | ✅ | Dev `test_sr05_ac4_...` (Chủ, 400 `BR-AI-01` có thông điệp, đã chấp nhận). QA `test_batch_pnl_va_guidance_qua_ai_khong_500`: 5 Group x {batch_pnl pk, batch_pnl batch_id, common.guidance} không 500 |
| SR-05-AC5 SR-04 và SR-05 cùng commit, test quét xanh | ⏸ | Test quét xanh trong cùng working tree (SR-04-AC3). Chưa commit nên "cùng commit" chưa kiểm được; điều phối commit 2 SR chung |
| SR-06-AC1 cskh guidance đơn ngoài phạm vi -> 404, chi tiết đơn vẫn 404 | ✅ | `test_sr06_ac1_cskh_don_ngoai_pham_vi_404` xanh; `test_sr06_ac1_body_404_khong_lo_thong_tin` (body không lặp `DH-OUT-1`). Đỏ trên HEAD |
| SR-06-AC2 escalate đơn ngoài phạm vi -> 404 | ✅ | Dev 4 test xanh. QA: `test_escalate_matrix_ngoai_pham_vi_404_khong_tao_gi` cskh/giao/giao2/direct -> 404, số `AiAction` và `AuditLog` không đổi, body không có mã đơn |
| SR-06-AC3 trong phạm vi 200; nv_giao phiếu mình 200/khác 404; user gán quyền trực tiếp như ViewSet | ✅ | Dev 6 test xanh + QA `test_ma_tran_guidance_5_group_x_2_don_x_khach` (bảng Group bên dưới) |
| SR-06-AC4 một hàm `scope_orders_for` dùng chung, test cũ danh sách đơn xanh nguyên | ✅ | `ScopeOrdersForTests` xanh; toàn bộ test cũ của `apps/sales` trong 1202 test xanh; **so sánh trước/sau** danh sách + chi tiết (bảng dưới): giống hệt |
| SR-07-AC1 lưu nháp có `rate` -> đọc lại không có `rate` | ✅ | vitest `draftStorage.test.ts` 11 test xanh (`npm test` 90 passed). Đỏ trên HEAD: kịch bản Playwright của dev thấy 81234 trong `localStorage` |
| SR-07-AC2 khoá `cave_draft_nhap_lo:<userId>` ở sessionStorage; đăng xuất xoá cả khoá cũ ở local | ✅ | vitest + Playwright dev (mock, 18/18) + QA D0/D1 (khoá cũ còn nguyên khi chưa mở form, đăng xuất xoá) |
| SR-07-AC3 chạy thật: Chủ gõ 81234, đăng xuất, nv_kho mở form -> ô giá rỗng, storage không có 81234 | ✅ | `python e2e/sr07_nhap_lo_draft.py` 18/18; QA lặp lại trên **Django thật** 32/32. Ảnh: `qa-lo2/sr07-1..4-*.png` (dev) và `qa-lo2/qa-sr07-C0/C1/R2-*.png` (QA) |
| SR-07-AC4 key idempotency mới khi nạp nháp phiên khác / sau gửi thành công | ✅ | vitest (a)(b)(c) + Playwright 4(a)(b)(c); QA A2/B2/C4 (tab/phiên/người khác -> key khác) và R2e (Django thật: sau F5 giữ đúng key, gửi lại không tạo phiếu thứ 2) |

Bước tái hiện SR-07-AC3 (trình duyệt thật, ảnh `qa-sr07-C0` -> `C1`): (1) đăng nhập Chủ (`loc`), Kho > Nhập lô, gõ số lượng 12 và Đơn giá mua 81234; (2) bấm Đăng xuất;
(3) đăng nhập `kho1`, mở Nhập lô: ô số lượng và ô giá rỗng; (4) devtools > Application: `localStorage`/`sessionStorage` không có chuỗi 81234.

## Ngoại lệ & biên (ngoài đường thuận)
| # | Ca | Kết quả | Bằng chứng |
|---|---|---|---|
| E1 | Điều kiện quét thật: đơn có trong phạm vi nv_giao (phiếu gán) và cskh (task PENDING), đơn kia ngoài phạm vi nv_giao | ✅ | `test_fixture_that_su_nam_trong_pham_vi` (chống cột rỗng, techlead L2) |
| E2 | Chủ cũng không thấy PII qua AI (Chủ không được miễn lọc) | ✅ | trong E-quét: cột `chu` 42 response 200, 0 vi phạm; `test_sr04_ac1_chu_...` |
| E3 | `AiAction.args/result_ref/downgrade_reason` + `AuditLog.note/changes` sau khi quét không chứa PII | ✅ | `test_ai_action_va_audit_khong_chua_pii_sau_quet` |
| E4 | Tra dò mã: đơn ngoài phạm vi và mã không tồn tại cho cùng status + cùng body, không lặp mã | ✅ | `test_404_khong_phan_biet_ton_tai_va_ngoai_pham_vi` |
| E5 | Tra guidance theo pk số (nhánh `isdigit`) không vòng qua phạm vi | ✅ | `test_guidance_theo_id_so_cung_ton_trong_pham_vi` |
| E6 | Danh sách đơn theo nhóm: chu/ql/kho thấy cả 2, cskh và giao chỉ đơn trong phạm vi, giao khác thấy rỗng | ✅ | `test_danh_sach_don_khong_doi_giua_cac_nhom` |
| E7 | **So sánh trước/sau** (HEAD-copy vs working tree, 8 đơn: gán nv_giao, gán giao khác, gán quyền trực tiếp, cskh đã gọi xong, chưa thanh toán; 7 user): list, list có `search`+`ordering`, chi tiết x8, guidance x8 | ✅ | `list`/`list2`/`detail` **giống hệt** ở cả 7 user (cùng thứ tự id). Chỉ `guidance` đổi, đúng ý: cskh 8/8 -> 6/8, user gán quyền trực tiếp 8/8 -> 1/8, trùng đúng danh sách/chi tiết. Script: scratchpad `qa_lo2_cmp` |
| E8 | Escalate ngoại phạm vi không lộ mã, không AiAction/AuditLog | ✅ | xem AC SR-06-AC2 |
| E9 | Escalate của Chủ không bị 404 phạm vi; không PII trong body | ✅ | `test_escalate_chu_khong_bi_chan_boi_pham_vi_va_khong_pii` |
| E10 | Escalate trong phạm vi -> 201; bấm lần 2 không 500; args/audit không PII | ✅ | `test_escalate_trong_pham_vi_201_hai_lan_va_khong_lo_pii`. Ghi nhận N2 (lần 2 tạo thêm việc) |
| E11 | Provider ném lỗi lạ (chuỗi có tên + SĐT giả) -> 400 `DOC_NOT_FOUND` thông điệp cố định; log chỉ có `RuntimeError`, không có chuỗi lỗi | ✅ | `test_escalate_loi_khac_khong_lo_exception_ra_response` (kiểm cả response và log `assertLogs`) |
| E12 | `inventory.batch.retrieve` x 6 user + khách: chu/ql/kho 200; giao/cskh/direct 404; khách 401/403 | ✅ | `test_batch_retrieve_theo_group` |
| E13 | `batch.retrieve` với ql/kho: không có `purchase_rate`, `landed_unit_cost`, `110000` | ✅ | cùng test (chỉ Chủ có) |
| E14 | `target_id` không tồn tại -> 404, không AiAction; thiếu `target_id` -> 400 `BR-AI-01` | ✅ | 2 test QA |
| E15 | Sửa SR-05 mà chưa sửa SR-04 sẽ lộ PII (thứ tự merge) | ✅ (ghi lại) | Dev đã ghi ở `03-dev-notes`; QA xác nhận E1..E3 quét xanh chỉ khi có cả hai |
| E16 | FE mock, 23 điểm kiểm: A tab khác cùng người (sessionStorage không chia sẻ, key khác), B phiên (context) khác, C hết phiên không bấm Đăng xuất rồi nv_kho vào cùng tab, D khoá cũ có giá + đăng xuất khi chưa mở Nhập lô, E nháp JSON hỏng / nháp cũ có `rate` (nạp xong ghi lại đã bỏ rate), F URL không query + console sạch | ✅ | `MODE=mock BASE=http://127.0.0.1:3212 python e2e/sr07_qa_edges.py` -> 23/23 |
| E17 | FE **Django thật** (sqlite tạm, CORS, bản build `NEXT_PUBLIC_USE_MOCK=0`), 32 điểm kiểm: A-F như E16 + R1 bấm đúp gửi (chỉ 1 phiếu, cùng key), R2 mạng đứt sau khi server đã ghi -> F5 (giữ số lượng + đúng key, giá rỗng) -> gửi lại **không tạo phiếu thứ 2**, R3/R4 storage cuối sạch, không pageerror | ✅ | `MODE=real BASE=http://127.0.0.1:3213 API=http://127.0.0.1:8123 python e2e/sr07_qa_edges.py` -> 32/32. Ghi chú: `Failed to fetch RSC payload .../deliveries/` là prefetch bị huỷ do `page.goto` trên `http.server` tĩnh (môi trường), đã lọc trong script và ghi trong script |
| E18 | Phân quyền FE: nv_kho vẫn vào được Nhập lô như trước (không bị chặn nhầm) | ✅ | E16/E17 (nv_kho `kho1` mở form, gửi phiếu thật) |
| E19 | Đỏ trên HEAD, BE: `git archive HEAD` backend + 31 test dev | ✅ | 21/31 đỏ (đúng các test tái hiện), 10 test đối chứng xanh |
| E20 | Đỏ trên HEAD, FE: build HEAD của erp-console + script Playwright dev | ✅ | script dev fail nhiều điểm kiểm trên bản build HEAD; điểm chính: 81234 nằm trong `localStorage` (chứng minh rò giá mua) |
| E21 | Đỏ trên HEAD, test quét bù của QA | ✅ | `test_p8_qa_lo2_sweep` trên HEAD-copy: 2 fail + 1 error (`retrieve` 502) |
| E22 | Đối chiếu Lô 1: lọc `loss_amount`, khoá tiền vẫn chạy (không hồi quy) | ✅ | trong 1202 test xanh |

## Phân quyền (Group x hành động)
Tách theo 2 lệnh gọi, đều đã chạy thật:

| `GET /api/guidance/order/<mã>/` | chu | quan_ly | nv_kho | nv_giao (phiếu mình) | nv_giao khác | cskh | gán quyền trực tiếp | khách |
|---|---|---|---|---|---|---|---|---|
| đơn trong phạm vi | 200 | 200 | 200 | 200 | 404 | 200 | 404 (chưa gán phiếu) | 401 |
| đơn ngoài phạm vi | 200 | 200 | 200 | 404 | 404 | 404 | 404 | 401 |

| Hành động | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| `POST /api/ai/actions/escalate/` đơn ngoài phạm vi | 400 hoặc 201, không 404 (kiểm bằng chu) | chưa kiểm riêng (cùng nhánh quyền đầy đủ) | chưa kiểm riêng | 404 | 404 | chưa kiểm (route yêu cầu đăng nhập) |
| `inventory.batch.retrieve` (AI) | 200 (có giá vốn) | 200 (không giá vốn) | 200 (không giá vốn) | 404 | 404 | 401/403 |
| mọi lệnh đọc AI (quét, dữ liệu trong phạm vi) | 42 x 200, 0 PII | 38 x 200, 0 PII | 28 x 200, 0 PII | 5 x 200, 0 PII | 3 x 200, 0 PII | không thuộc quét |
| `GET /api/sales/orders/` (không đổi) | mọi đơn | mọi đơn | mọi đơn | đơn phiếu mình | đơn trong phạm vi gọi | 401 |

## Rò giá vốn
Không phát hiện. AI `batch.retrieve`: chỉ Chủ thấy `purchase_rate`, `landed_unit_cost`; quan_ly/nv_kho không (E13). Khoá nháp FE không chứa `rate` (Đơn giá mua) ở bất kỳ storage nào
(vitest + Playwright mock + real, kể cả sau F5, sau gửi thành công, sau đăng xuất, hết phiên, nháp cũ). Khoá `idempotencyKey` là chuỗi ngẫu nhiên, không tính ngược ra giá vốn.
AuditLog/AiAction sau quét (E3) không có khoá tiền. HTML export tĩnh: ô giá mua chỉ là ô nhập, không có giá trị dựng sẵn.

## Rò dữ liệu cá nhân
Không phát hiện trong phạm vi AC (bất biến 9).
- Quét 5 Group x mọi lệnh đọc (list + retrieve), gồm nv_giao/cskh **có dữ liệu trong phạm vi**: 0 chuỗi PII, 0 khoá PII, không khoá "giống PII" ngoài tập lọc.
- Guidance đơn (`doc`) không chứa tên/SĐT/địa chỉ; body 404 và 400 không lặp mã đơn hoặc chuỗi lỗi; log escalate chỉ ghi `type(exc).__name__`.
- `AiAction.args`, `AuditLog.note/changes` sau quét: sạch.
- FE: URL không có query hay dữ liệu cá nhân, console không có chuỗi giá/SĐT, storage chỉ chứa số lượng/nhà cung cấp/key ngẫu nhiên. Nháp không chứa tên/SĐT khách (Nhập lô không có trường này).
- Ảnh/report: chỉ dữ liệu giả.

**G1 (giới hạn thiết kế, không phải lỗi AC — cần Tech Lead/PO chốt).** Bộ lọc là danh sách khoá (denylist), nên **chữ tự do do nhân viên gõ** không bị lọc.
Tái hiện: fixture QA lúc đầu ghi lý do phiếu hoàn = "Khách Giả Bí Mật dặn giao chiều" (`refund_services.create_refund(reason=...)`), rồi mọi Group (chu, quan_ly, nv_kho, nv_giao, cskh)
gọi `sales.salesorder.retrieve` cho đơn đó -> 200 và `timeline[].label` = "Tạo phiếu hoàn 270.000 ₫ — Khách Giả Bí Mật dặn giao chiều" (do `orders/timeline.py:136` nối `r.reason`).
Cùng chuỗi đó cũng hiện ở API đơn thường (đúng quyền), nên không phải hồi quy của Lô 2; nhưng kênh AI gửi cho mô hình bên ngoài thì H2 nói "không bao giờ". Khuyến nghị: bỏ `reason`/ghi chú
tự do khỏi timeline khi đi qua AI, hoặc thêm `label` vào danh sách lọc cho lệnh đọc đơn. Nếu PO coi chữ tự do là PII thì đây thành Medium chặn; hiện ghi nhận vì AC SR-04 chỉ định nghĩa sentinel tên/SĐT/địa chỉ và `reason` cố ý trung tính trong test.

## Hồi quy
| Chức năng liền kề | Kết quả | Bằng chứng |
|---|---|---|
| Toàn backend | ✅ | 1202 test OK (1186 của dev + 16 QA), không `--parallel` |
| `makemigrations --check` | ✅ | No changes detected |
| adapter | ✅ | 68 passed |
| Danh sách/chi tiết đơn (P4, P5) | ✅ | so sánh trước/sau giống hệt (E7) |
| Lô 1 (lọc `loss_amount`, khoá tiền, job AI) | ✅ | nằm trong 1202 test |
| erp-console `npm ci` (không cờ) / `tsc` / `build` / `npm test` | ✅ | xem lệnh; 90 test |
| AI guidance/escalate của đơn trong phạm vi vẫn chạy | ✅ | E9/E10 (201, 400 nghiệp vụ `STEP_NOT_FOUND`, `BR-AI-25`) |

## Lỗi
Không có lỗi chặn. Ghi nhận (Low, không chặn):
- **N1 (Low) — `sr07`: khoá cũ có giá chỉ bị dọn khi mở Nhập lô hoặc đăng xuất, không phải lúc đăng nhập.** Máy còn khoá `cave_draft_nhap_lo` cũ trong `localStorage` sau khi deploy vẫn giữ giá đến lần mở form/đăng xuất kế (D1 chứng minh đăng xuất dọn). FE không đọc khoá đó, chỉ devtools thấy. Đề xuất dọn ở `AuthProvider` khi khởi động.
- **N2 (Low) — Escalate bấm lần 2 tạo thêm 1 việc "Nhờ" cùng bước.** Có từ trước Lô 2 (logic không đổi): 2 `AiAction` ESCALATED cùng `target_id` + `step_key`. Không mất tiền/kho; đề xuất khoá chống trùng hoặc dùng `idempotency_key`.
- **N3 (Low) — nháp của người hết phiên (không đăng xuất) còn ở `sessionStorage` của tab.** Không chứa `rate`, người khác không đọc được vì khoá theo userId và bị dọn khi tab đóng.
- Nợ Tech Lead L2–L6 ở `03b` là nợ đã biết, không tính lỗi QA mới. Với L2 (quét trên dữ liệu rỗng) QA đã bù `RichScopeSweep`.
- Ngoài phạm vi lô, nhìn thấy khi chạy thật: nv_kho thấy và nhập được ô "Đơn giá mua" ở Nhập lô (hành vi có từ trước; giá do nv_kho tự nhập nên không phải rò).

## Lệnh đã chạy (tóm tắt output)
```
backend  DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test                       -> Ran 1186 OK (trước khi thêm test QA); sau khi thêm: Ran 1202 tests OK, 51 s
backend  manage.py makemigrations --check --dry-run                                                -> No changes detected
backend  manage.py test apps.ai.registry.tests.test_p8_qa_lo2_sweep                                -> Ran 4 OK (200: chu 42, ql 38, kho 28, giao 5, cskh 3; khoá giống-PII ngoài tập lọc: {})
backend  manage.py test apps.sales.orders.tests.test_p8_qa_lo2_matrix                              -> Ran 12 OK
HEAD-copy (git archive HEAD backend + 31 test dev)  manage.py test ...                             -> 21/31 đỏ (đúng test tái hiện SR-04/05/06)
HEAD-copy + test_p8_qa_lo2_sweep                                                                   -> FAILED (failures=2, errors=1) [đỏ trên HEAD]
so sánh trước/sau  PYTHONPATH=<scratchpad> manage.py test qa_lo2_cmp (HEAD-copy và working tree)   -> list/list2/detail giống hệt, guidance đổi đúng (cskh 8->6, direct 8->1)
adapter  .venv/bin/python -m pytest -q                                                             -> 68 passed
erp-console  rm -rf node_modules && npm ci --cache <scratchpad>                                    -> exit 0, 0 dòng ERESOLVE/legacy
erp-console  npx tsc --noEmit -> 0 ; npm run build -> 0 ; npm test                                 -> 90 passed (draftStorage.test.ts 11)
Playwright  python e2e/sr07_nhap_lo_draft.py (mock, port 3212)                                     -> 18/18 PASS  (đỏ trên bản build HEAD)
Playwright  MODE=mock python e2e/sr07_qa_edges.py                                                  -> 23/23 PASS
Playwright  MODE=real (Django thật sqlite, port 3213 + 8123) python e2e/sr07_qa_edges.py           -> 32/32 PASS
```

---

## Lô 3 — SR-08, SR-09, SR-10, SR-11 · lần 1 · 2026-09-30

### Kết luận: APPROVED — 0 lỗi Critical/High/Medium; mọi AC chạy thật xanh (test đỏ trên HEAD, xanh trên working tree); tranh chấp hai thứ tự xanh; 1 ca ⏸ (đồng thời thật trên Postgres) chuyển cho bước staging; 6 ghi nhận Low không chặn
### Tổng: 78 ca · ✅ 77 · ❌ 0 · ⏸ 1 (khoá dòng thật `select_for_update` khi 2 giao dịch chạy song song: SQLite bỏ qua khoá, máy này không có Postgres/Docker)

Cách đếm: 16 ca theo AC (SR-08 x5, SR-09 x4, SR-10 x3, SR-11 x4) + 52 test QA bổ sung (22 SR-08/10, 13 SR-09, 17 SR-11) + 4 ca tái hiện R2–R5 chạy 2 lần
+ 2 kịch bản Playwright (mock 22 điểm kiểm, Django thật 11 điểm kiểm) + 3 ca hồi quy/build (backend đầy đủ + `makemigrations`, adapter, erp-console) + 1 ca ⏸.

Phạm vi: code chưa commit trong working tree (`inventory/batches/services.py`, `next_steps.py`, `delivery/cskh/services.py`, `sales/payments/auto_confirm.py`,
`erp-console/features/cskh/*` + 39 test của dev). Không sửa code sản phẩm. QA thêm 3 file test BE và 1 script Playwright:
- `backend/apps/inventory/batches/tests/test_p8_lo3_qa_edges.py` (22 test: SR-08 `QaSR08Edges` 15, SR-10 `QaSR10Edges` 7)
- `backend/apps/delivery/tests/test_p8_lo3_qa_edges.py` (13 test SR-09)
- `backend/apps/sales/payments/tests/test_p8_lo3_qa_edges.py` (17 test SR-11)
- `erp-console/e2e/sr09_ac4_real_backend.py` (Playwright, Django thật, 11 điểm kiểm); ảnh `qa-lo3/qa-sr09-real-desktop-1280-*.png`.
Dữ liệu chỉ là giả (Khách Thử A/E, 0900000xxx, Số 1/5 Đường Thử, mật khẩu demo).

## Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| SR-08-AC1 (R5) lô EXPIRED còn giữ chỗ -> 400 `BR-LO-07` "Còn 2,000 kg đang giữ chỗ của 1 đơn…", lô vẫn EXPIRED, không `WRITE_OFF` | ✅ | `test_sr08_ac1_r5_...`, `..._dem_dung_so_don_giu_cho`, `..._400_khong_ro_gia_von_va_du_lieu_khach` xanh. Repro R5 chạy 2 lần: cả 2 lần bị chặn, output y hệt. Đỏ trên HEAD |
| SR-08-AC2 tiền không mất: thanh toán sau khi bị chặn huỷ vẫn thành công | ✅ | `test_sr08_ac2_...` + QA `test_qa_race_huy_lo_truoc_bi_chan_roi_thanh_toan_sau_khong_mat_tien` (có `PaymentTransaction`, hoá đơn 1, đơn sang **PROCESSING** chứ không phải PAID, khớp quyết định Tech Lead; stories ghi "PAID" là chữ cũ) |
| SR-08-AC3 giữ chỗ về 0 (TTL) -> huỷ lô 200, `WRITE_OFF` đúng `qty_available` | ✅ | `test_sr08_ac3_...` x2 + QA `test_qa_ttl_job_chay_2_lan_va_nhieu_don` |
| SR-08-AC4 guidance: `cancel_expired` `allowed=false`, `missing` có `BR-LO-07` | ✅ | `test_sr08_ac4_...` x2 + QA `test_qa_guidance_tung_group_...` (5 Group) |
| SR-08-AC5 huỷ lần 2 -> 400 `BR-LO-03`, không ghi thêm ledger | ✅ | `test_sr08_ac5_...`; QA `test_qa_lo_da_chot_hoac_da_huy_khong_huy_lai` (CANCELLED/CLOSED/SOLD_OUT, ledger không đổi) |
| SR-09-AC1 (R2) `record_call(CONFIRMED)` sau tự huỷ -> 409 `STALE_STATE` "Đơn đã bị huỷ — tải lại màn hình."; phiếu CANCELLED, task `REFUND_CALL` | ✅ | `test_sr09_ac1_r2_...` xanh; repro R2 chạy 2 lần bị chặn. Đỏ trên HEAD |
| SR-09-AC2 `REFUND_CALL` chỉ nhận `UNREACHABLE`/`NOTIFIED`; mọi kết quả khác 409 | ✅ | `test_sr09_ac2_...` x3 (tham số hoá từng kết quả). QA `test_qa_chu_huy_tay_roi_cskh_bam_moi_ket_qua_deu_409` chạy cả 7 kết quả trên đơn **huỷ tay**. Kết quả rác `KHONG_CO` vẫn 400 `INVALID_INPUT` (đúng quyết định Tech Lead) |
| SR-09-AC3 tranh chấp hai chiều: (a) CSKH trước, job sau -> job bỏ qua; (b) job trước, CSKH sau -> như AC1 | ✅ | Dev `test_sr09_ac3a/ac3b`; QA bù cả hai thứ tự ở mức đầy đủ: `test_qa_race_cskh_xac_nhan_truoc_job_bo_qua_va_khong_hoan_tien`, `test_qa_race_job_truoc_roi_luong_bao_hoan_tien_van_chay` |
| SR-09-AC4 API 409 body `{"detail","code":"STALE_STATE"}`; FE hiện thông điệp + "Tải lại" | ✅ | Backend: `test_sr09_ac4_api_...` x2 + QA `test_qa_huy_tay_api_409_body_dung_hop_dong` (body **chính xác** 2 khoá). FE: xem "FE SR-09-AC4" ngay dưới: mock 22/22 và **Django thật** 11/11 |
| SR-10-AC1 (R3) `publish_batch(object cũ)` sau `cancel_receipt` -> 400 `BR-MH-05`, lô vẫn CANCELLED | ✅ | `test_sr10_ac1_r3_...`, `..._api_publish_lo_da_huy_400_br_mh_05`; repro R3 chạy 2 lần bị chặn. Đỏ trên HEAD |
| SR-10-AC2 `atomic` + `select_for_update().get(pk)` rồi mới kiểm DRAFT; publish lần 2 -> 400 | ✅ | `test_sr10_ac2_...` x3 + QA `test_qa_object_cu_la_draft_nhung_db_da_o_trang_thai_khac` (6 trạng thái DB, không ghi đè); trình tự khoá kiểm bằng spy (xem E2) |
| SR-10-AC3 luồng thuận DRAFT -> SELLING, AuditLog `publish_batch` như cũ | ✅ | `test_sr10_ac3_...`, `test_sr10_ma_tran_group_chu_200`; QA `test_qa_publish_tra_ve_object_moi_trang_thai_selling` |
| SR-11-AC1 (R4) 1 giao dịch UNMATCHED OPEN, chạy 2 lần -> đúng 1 dòng `escalate_unmatched_payment` | ✅ | `test_sr11_ac1_r4_...`; repro R4 chạy 2 lần bị chặn. QA bù **mọi đường lý do** x2 lần chạy (E-SR11, 8 ca) đều đúng 1 dòng |
| SR-11-AC2 Chủ đặt REJECTED/DONE/CANCELLED/EXPIRED/UNDONE/FAILED -> chạy lại giữ nguyên, không thêm audit | ✅ | `test_sr11_ac2_...` x2 (6 trạng thái) |
| SR-11-AC3 lý do đổi -> +1 dòng audit, cập nhật `downgrade_reason` (so sánh `["text"]`) | ✅ | `test_sr11_ac3_...` x2; QA `test_qa_don_doi_trang_thai_giua_2_lan_chay_them_dung_1_dong` (đơn đổi BOOKED -> CANCELLED giữa 2 lần: +1 dòng, sau đó ổn định) |
| SR-11-AC4 chỉ quét `UNMATCHED`; ORPHAN/OVERPAID/UNDERPAID không tạo việc | ✅ | `test_sr11_ac4_...` x2 |

### FE SR-09-AC4 (bằng chứng chạy thật, không đọc code)
| # | Lệnh / bước | Kết quả |
|---|---|---|
| F1 | Build mock `NEXT_PUBLIC_USE_MOCK=1 npm run build`, chép `out` sang thư mục riêng ở scratchpad, `python3 -m http.server 3213`, `SHOTS=<dir> python3 e2e/sr09_ac4_stale_state.py` | **22/22 PASS** (desktop 1280x800 và mobile 375x667: thông điệp đúng `detail`, nằm trong khung nhìn, nút Tải lại cao >= 44 px, nút kết quả bị khoá, không cuộn ngang, Tải lại đóng modal, phiếu sang tab báo hoàn tiền, console không có SĐT/tên). Đã xem ảnh: chữ đỏ "Đơn đã bị huỷ — tải lại màn hình." + nút "Tải lại" xanh, không bị cắt ở 375 px |
| F2 | **Django thật** (SQLite tạm, cổng 8113, `CSKH_AUTO_CANCEL_ENABLED=1`, `CORS_ALLOWED_ORIGINS=http://127.0.0.1:3214`), seed phiếu ESCALATED (UNREACHABLE) bằng dữ liệu giả; build `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8113 NEXT_PUBLIC_USE_MOCK=0`, phục vụ ở 3214; `TRIGGER_CMD=... python3 e2e/sr09_ac4_real_backend.py` | **11/11 PASS**. Cs1 đăng nhập, mở tab "Cần quyết định", mở màn gọi; **job `auto_cancel_overdue` chạy ở backend** (`{'cancelled': 1}`) trong lúc màn còn mở; bấm "Đã xác nhận" -> `POST /api/cskh/queue/1/calls/` **409** đúng 1 lần (không gửi lại); màn hiện "Đơn đã bị huỷ — tải lại màn hình." + "Tải lại"; bấm -> modal đóng, phiếu qua tab "Báo hoàn tiền". Ảnh: `qa-lo3/qa-sr09-real-desktop-1280-1-409.png`, `...-2-refund-tab.png` |
| F3 | Kiểm DB sau F2 | phiếu CANCELLED, đơn CANCELLED, 1 Refund, 1 `order_auto_cancelled`, **0** `delivery_confirmed`, cuộc gọi duy nhất là UNREACHABLE cũ (không có CONFIRMED) |
| F4 | Kiểm đường khác trên phiếu đã huỷ (curl với Django thật) | Chủ: `calls` CONFIRMED 409 `STALE_STATE`; `decide` DELIVER_WITHOUT_CONFIRM / EXTEND / CANCEL cùng 409 `STALE_STATE` "Đơn đã được xử lý." (không đổi gì); cs1 (không có `decide_unconfirmed`) `decide` 403 |
| F5 | Rà PII: console, URL, `localStorage`/`sessionStorage`, log Django | không chứa SĐT/tên/địa chỉ khách (F1 và F2 đều có điểm kiểm; `grep` log Django 0 khớp) |

Bước tái hiện SR-09-AC4 (Django thật): (1) seed 1 đơn đã thanh toán, gọi cs1 `UNREACHABLE`, đặt task ESCALATED; (2) cs1 vào `/cskh/`, tab "Cần quyết định", mở phiếu;
(3) trong backend chạy `auto_cancel_overdue(now=now+31 phút)`; (4) bấm "Đã xác nhận" trên màn cũ; (5) thấy cảnh báo + "Tải lại", bấm "Tải lại".

## Ngoại lệ & biên (ngoài đường thuận)
Mọi ca dưới đây là test QA tự viết, đều xanh trên working tree; **trên HEAD (git archive)**: SR-08/10 đỏ 14 F + 1 E, SR-09 đỏ 6 F + 10 E (subTest), SR-11 đỏ 10 F, nên không phải test rỗng.

| # | Ca | Kết quả | Bằng chứng (test) |
|---|---|---|---|
| E1 | Lô đã từng bán: đơn A đã PAID + đơn B BOOKED 3 kg: bị chặn -> B thanh toán -> huỷ lô ghi `WRITE_OFF` -95, tổng ledger = 0, hoá đơn A không đổi | ✅ | `test_qa_lo_da_tung_ban_don_da_tra_khong_bi_dem_va_khong_bi_dong_vao` |
| E2 | Trình tự khoá: spy thấy lock lô trước `check_cancel_expired_batch`; `reserve`/`release` cũng khoá đúng dòng lô; publish khoá trước khi kiểm DRAFT | ✅ | `test_qa_khoa_lo_truoc_khi_kiem_dieu_kien_huy`, `test_qa_khoa_lo_o_reserve_va_release_cung_dong_lo`, `test_sr10_ac2_doc_lai_co_khoa_...` |
| E3 | **Tranh chấp A**: thanh toán đơn giữ chỗ TRƯỚC, huỷ lô SAU -> huỷ lô 200, `WRITE_OFF` -96, không mất tiền | ✅ | `test_qa_race_thanh_toan_truoc_huy_lo_sau` |
| E4 | **Tranh chấp B**: huỷ lô TRƯỚC (bị chặn 400) rồi thanh toán -> thành công, không giao dịch mồ côi | ✅ | `test_qa_race_huy_lo_truoc_bi_chan_roi_thanh_toan_sau_khong_mat_tien` |
| E5 | Job TTL huỷ giữ chỗ chạy 2 lần (1 rồi 0), reserved = 0, sau đó huỷ lô được | ✅ | `test_qa_ttl_job_chay_2_lan_va_nhieu_don` |
| E6 | Đơn nhiều dòng cùng lô = 1 đơn; giữ chỗ ở lô khác không chặn lô này; biên 0,001 kg vẫn chặn; lô SELLING còn giữ chỗ -> `BR-LO-03` (không phải `BR-LO-07`) | ✅ | `test_qa_don_nhieu_dong_cung_lo_dem_la_1_don`, `..._giu_cho_o_lo_khac_...`, `..._gia_tri_bien_...`, `..._lo_dang_ban_...` |
| E7 | Lô CANCELLED/CLOSED/SOLD_OUT huỷ lại -> `BR-LO-03`, ledger không đổi | ✅ | `test_qa_lo_da_chot_hoac_da_huy_khong_huy_lai` |
| E8 | AuditLog: bị chặn không ghi; thành công đúng 1 dòng, bấm lần 2 không thêm; audit-logs của quan_ly không có `loss_amount` | ✅ | `test_qa_audit_khong_ghi_khi_bi_chan_va_ghi_1_dong_khi_thanh_cong` |
| E9 | SR-10 màn hình cũ: object DRAFT cũ nhưng DB đã SELLING/NEAR_EXPIRY/SOLD_OUT/EXPIRED/CANCELLED/CLOSED -> `BR-MH-05`, DB không bị ghi đè | ✅ | `test_qa_object_cu_la_draft_nhung_db_da_o_trang_thai_khac` |
| E10 | **Tranh chấp C1** publish trước, `cancel_receipt` sau -> `BR-MH-07`, lô vẫn SELLING | ✅ | `test_qa_race_publish_truoc_huy_phieu_sau` |
| E11 | **Tranh chấp C2** `cancel_receipt` trước, publish sau qua API -> 400 `BR-MH-05`, tồn 0 | ✅ | `test_qa_race_huy_phieu_truoc_publish_sau_qua_api` |
| E12 | Bấm đúp publish qua API: 200 / 400 / 400, 1 dòng audit; id không tồn tại 404; chưa đăng nhập 401 | ✅ | `test_qa_bam_dup_api_chi_1_lan_thanh_cong`, `test_qa_id_khong_ton_tai_va_chua_dang_nhap` |
| E13 | SR-09: Chủ **huỷ tay** (không phải job), CSKH bấm cả 7 kết quả -> 409 `STALE_STATE`, không thêm cuộc gọi, không `delivery_confirmed` | ✅ | `test_qa_chu_huy_tay_roi_cskh_bam_moi_ket_qua_deu_409` |
| E14 | SR-09: job `auto_cancel_overdue` chạy 2 lần (1 rồi 0): 1 Refund, 1 `order_auto_cancelled`, hoá đơn gốc còn nguyên | ✅ | `test_qa_job_tu_huy_chay_2_lan_chi_huy_1_lan` |
| E15 | SR-09 **tranh chấp D1**: CSKH xác nhận trước, job sau -> job bỏ qua, không hoàn tiền; người thứ hai bấm lại -> 409 "vừa được xác nhận", phiếu vẫn PREPARING, 1 `delivery_confirmed` | ✅ | `test_qa_race_cskh_xac_nhan_truoc_job_bo_qua_va_khong_hoan_tien` |
| E16 | SR-09 **tranh chấp D2**: job trước, CSKH sau; luồng báo hoàn tiền vẫn chạy (UNREACHABLE attempts=1, NOTIFIED -> DONE), rồi CONFIRMED/UNREACHABLE/NOTIFIED lần nữa -> 409 | ✅ | `test_qa_race_job_truoc_roi_luong_bao_hoan_tien_van_chay` |
| E17 | SR-09 người đang giữ (claim) bị job huỷ ngang: cs1 và cs2 bấm -> đều 409 `STALE_STATE` (không phải CLAIMED) | ✅ | `test_qa_cskh_dang_giu_phieu_bi_job_huy_ngang_roi_bam_xac_nhan` |
| E18 | SR-09 `request_id`: UNREACHABLE trên REFUND_CALL bấm đúp cùng id -> cuộc gọi cũ, attempts giữ 1; CONFIRMED bị chặn cùng id thử lại vẫn 409 và không ghi gì | ✅ | `test_qa_request_id_bam_dup_tren_refund_call`, `test_qa_request_id_cua_lan_bi_chan_409_...` |
| E19 | SR-09 hồi quy đường thuận: CONFIRMED trên phiếu bình thường vẫn 201 (PREPARING); kết quả rác vẫn 400; xác nhận rồi bấm lần 2 -> 409 "vừa được xác nhận" | ✅ | `test_qa_luong_thuan_confirmed_van_201`, `test_qa_ket_qua_rac_...`, `test_qa_da_xac_nhan_roi_bam_lan_2_...` |
| E20 | SR-11 mọi đường chuyển Chủ chạy 2 lần: nghi trùng, sai môi trường, không có đơn, mã đơn không tồn tại, **đơn đã bán (PROCESSING)**, đơn đã huỷ, thiếu tiền, thừa tiền -> mỗi đường đúng 1 dòng audit, 1 `AiAction` ESCALATED, không tự đổi đơn | ✅ | 8 test `test_qa_ly_do_*` |
| E21 | SR-11 đơn đổi trạng thái giữa 2 lần chạy -> lý do đổi -> +1 dòng, rồi ổn định | ✅ | `test_qa_don_doi_trang_thai_giua_2_lan_chay_them_dung_1_dong` |
| E22 | SR-11 đường thuận khớp tuyệt đối chạy 2 lần (confirmed 1 rồi 0): 1 audit `auto_confirm_exact_match`, đúng 1 hoá đơn, đơn PROCESSING, không `AiAction` | ✅ | `test_qa_khop_tuyet_doi_chay_2_lan_chi_ghi_tien_1_lan` |
| E23 | SR-11 hai giao dịch cùng đơn: giao dịch đầu khớp, giao dịch sau chuyển Chủ đúng 1 lần (3 lần chạy), 1 hoá đơn | ✅ | `test_qa_hai_giao_dich_cung_don_cai_thu_hai_chuyen_chu_dung_1_lan` |
| E24 | SR-11 giao dịch RESOLVED không bị quét; cờ tắt (công tắc Chủ đóng / `AI_ENABLED=False` / chưa sẵn sàng production) không ghi gì; lệnh `auto_confirm_exact_payments` chạy 2 lần -> 1 audit; audit cũ không bị sửa | ✅ | `test_qa_giao_dich_da_resolved_...`, 3 test cờ, `test_qa_management_command_chay_2_lan`, `test_qa_audit_khong_xoa_va_khong_sua_khi_chay_lai` |
| E25 | Đồng thời thật (2 giao dịch song song, `select_for_update` có tác dụng) cho 3 cặp tranh chấp | ⏸ | SQLite bỏ qua khoá; đã kiểm gián tiếp bằng spy trình tự khoá (E2) và giao thoa xác định theo cả 2 thứ tự (E3/E4/E10/E11/E15/E16). Cần chạy lại trên Postgres staging (xem "Lệnh đã chạy" cuối) |

## Phân quyền (Group x hành động)
| Hành động | chu | quan_ly | nv_kho | nv_giao | cskh | khách | Bằng chứng |
|---|---|---|---|---|---|---|---|
| `POST /api/inventory/batches/<id>/cancel-expired/` | 200 / 400 nghiệp vụ | 403 | 403 | 403 | 403 | 401 | `test_sr08_ma_tran_group_cancel_expired`, `test_qa_chua_dang_nhap_va_id_khong_ton_tai`, `test_qa_400_thieu_quyen_khong_lo_chi_tiet` (body 403 không rò) |
| `POST …/publish/` | 200 / 400 | 200 / 400 | 403 | 403 | 403 | 401 | `test_sr10_ma_tran_group_publish`, `test_sr10_ma_tran_group_chu_200` |
| `POST /api/cskh/queue/<id>/calls/` CONFIRMED trên REFUND_CALL | 409 | 409 | 403 | 403 | 409 (nếu đã gọi phiếu) / **404** nếu chưa từng gọi (ngoài phạm vi BR-GH-18) | 401 | `test_sr09_ma_tran_group_refund_call_confirmed`, `test_qa_phan_quyen_stale_khach_401_va_nhom_khong_quyen_403`. Ghi chú: cs2 chưa từng gọi phiếu nhận 404 (đúng BR-GH-18, không lộ trạng thái/PII); stories không nêu trường hợp này |
| `…/calls/` NOTIFIED/UNREACHABLE trên REFUND_CALL | 201 | 201 | 403 | 403 | 201 | 401 | `test_sr09_ma_tran_group_refund_call_notified_unreachable`. Mã thành công là **201** (không phải 200 như ma trận stories; Tech Lead đã chốt) |
| `…/decide/` trên phiếu đã huỷ (curl, Django thật) | 409 `STALE_STATE` | 409 (cùng logic) | 403 | 403 | 403 (thiếu `decide_unconfirmed`) | 401 | F4 |
| SR-11 job Hệ thống | không áp dụng: không có endpoint mới | | | | | | |

## Rò giá vốn
| Kênh | Kết quả | Bằng chứng |
|---|---|---|
| Body lỗi `BR-LO-07` chỉ có kg + số đơn, không có giá | ✅ | `test_sr08_ac1_400_khong_ro_gia_von_va_du_lieu_khach`; QA `test_qa_guidance_tung_group_...` và `test_qa_400_thieu_quyen_...` quét `COST_KEYS` cho user thiếu `view_costprice` |
| AuditLog `changes`/`note` của publish, huỷ lô, `order_auto_cancelled`, `escalate_unmatched_payment`, `auto_confirm_exact_match` | ✅ | `test_qa_audit_publish_khong_co_gia_von_hay_pii`, `test_qa_audit_khong_ghi_khi_bi_chan_...` (audit-logs quan_ly không có `loss_amount`), `test_qa_khong_ro_pii_hay_gia_von_trong_nhat_ky_action_va_log` (quét `unit_cost`, `landed_unit_cost`, `purchase_rate`, `loss_amount`, `gross_profit`) |
| Khoá mới ghi audit/`AiAction.args` có tính ngược ra giá vốn (tiền ÷ kg)? | ✅ không | `args` của `AiAction` chỉ có `payment_id` và `reason` (chữ lý do, số tiền giao dịch/đơn là giá bán, không phải giá vốn). `WRITE_OFF` -95/-96 kg ghi ở ledger nội bộ, không trả qua API cho Group thiếu quyền |
| Body 409 `STALE_STATE` (calls/decide) | ✅ | chỉ có `detail`, `code` (và `current_status`, `confirm_state` ở decide), không có tiền/kg/giá vốn |

## Rò dữ liệu cá nhân
| Kênh | Kết quả | Bằng chứng |
|---|---|---|
| Body lỗi BR-LO-07 không tên/SĐT/địa chỉ khách | ✅ | `test_sr08_ac1_400_...`, `test_qa_guidance_tung_group_khong_ro_gia_von_va_pii` (5 Group) |
| Body 409 STALE_STATE và log Django khi CSKH bấm màn cũ | ✅ | `test_qa_khong_ro_pii_trong_log_body_va_audit_khi_409` (bắt log root DEBUG, sentinel tên/SĐT/địa chỉ, 0 khớp); grep log Django thật (F2) 0 khớp |
| Nhóm cskh chưa từng gọi phiếu không thấy gì (404, body không có sentinel) | ✅ | `test_qa_phan_quyen_stale_khach_401_va_nhom_khong_quyen_403` |
| SR-11: `raw_payload` có tên/SĐT/địa chỉ người chuyển không lọt vào `AuditLog` (`note`, `changes`), `AiAction.args`/`downgrade_reason`, log job | ✅ | `test_qa_khong_ro_pii_hay_gia_von_trong_nhat_ky_action_va_log`; log job có mã GD/mã đơn (không rỗng nên kiểm không vô nghĩa) |
| FE: console, URL, `localStorage`/`sessionStorage` | ✅ | F1 và F2 (điểm kiểm riêng) |
| Ảnh chụp và report chỉ dữ liệu giả | ✅ | Khách Thử E, 0900000555, Số 5 Đường Thử |

## Hồi quy
| Chức năng liền kề | Kết quả | Bằng chứng |
|---|---|---|
| Toàn backend | ✅ | **1293 test OK** = 1241 trước đó + 52 test QA, không `--parallel`, 86 s |
| `makemigrations --check --dry-run` | ✅ | No changes detected |
| adapter | ✅ | 68 passed |
| Lô 1, Lô 2 (lọc `loss_amount`, khoá tiền, PII AI, guidance) | ✅ | nằm trong 1293 test |
| SR-11 đường thuận DW-26 (`test_dw26_auto_confirm.py`) | ✅ | nằm trong 1293 test; QA E22 chạy lại đường thuận 2 lần |
| erp-console `npm ci` (không `--legacy-peer-deps`, `--cache` ở scratchpad) / `tsc --noEmit` / `npm run build` / `npm test` | ✅ | `npm ci` exit 0, 189 packages, 0 dòng ERESOLVE; `package.json` và `package-lock.json` **không đổi** (md5 trước/sau khớp); tsc exit 0; build exit 0; vitest 10 file / 99 test |
| `out/` của erp-console sau khi QA | ✅ | đã build lại bản thật (`.env.production`, `USE_MOCK=0`): không còn chuỗi mock (`mockGetCskhQueue`, `DH-260928-0036`), không trỏ 127.0.0.1:8113, trỏ đúng API Cloud Run. Đã tắt server 3213/3214/8113 |

## Lỗi
Không có lỗi chặn. Ghi nhận (Low, không chặn):
- **N1 (Low) — SR-11: `get_or_create` có thể đẩy sang ESCALATED một `AiAction` đang PENDING/CONFIRMED/SCHEDULED của cùng giao dịch, và `MultipleObjectsReturned` nếu có 2 việc cùng khoá.** Chỉ xảy ra khi Chủ đã có việc chưa đóng cho đúng giao dịch đó; job hiện không kiểm. Đề xuất Tech Lead quyết định chỉ nâng khi trạng thái là ESCALATED/PROPOSED, hoặc dùng `filter().first()`.
- **N2 (Low) — SR-11: bộ đếm `escalated` trong kết quả job đếm cả lần không làm gì (idempotent no-op); `args["reason"]` giữ lý do cũ sau khi lý do đổi (chỉ `downgrade_reason` cập nhật).** Không ảnh hưởng tiền/kho/Nhật ký; chỉ gây hiểu sai thống kê job và dữ liệu `args`. Đề xuất cập nhật `args` cùng `downgrade_reason` và chỉ đếm khi thực sự ghi.
- **N3 (Low) — SR-08: chữ "0 đơn" khi `qty_reserved > 0` mà không có đơn BOOKED nào giữ chỗ** (chỉ tạo được bằng sửa DB trực tiếp, không qua nghiệp vụ). Thông điệp vẫn chặn đúng; đề xuất thêm "(dữ liệu lệch, báo Quản lý)" khi n = 0.
- **N4 (Low) — SR-09 FE: khi màn ở trạng thái STALE, chỉ nút kết quả bị khoá; khối "Cần Quản lý quyết định" (Giao không xác nhận / Gia hạn / Huỷ đơn / Xác nhận chuyển soạn hàng) vẫn bấm được và nút "Tải lại" chỉ có ở `record_call`.** BE chặn an toàn (409 `STALE_STATE`, không đổi gì, xem F4), nhưng người dùng bấm nhầm sẽ nhận thông báo lỗi khác ("Đơn đã được xử lý.") mà không có nút Tải lại. Nằm ngoài AC4; đề xuất tái sử dụng `isStaleStateError` cho cả `decide`. Cũng: cs1 thấy nút quyết định dù không có quyền `decide_unconfirmed` (403) — hành vi có từ trước.
- **N5 (Low) — lệch chữ giữa tài liệu và code (không lỗi code).** (a) stories SR-09 ma trận ghi NOTIFIED/UNREACHABLE "200", thực tế 201; (b) SR-08-AC2 ghi "đơn PAID", thực tế PROCESSING; (c) 02b §3.4 ghi so sánh `code`, code so sánh `downgrade_reason["text"]`; (d) `repro/README` ghi R2 = SR-09 và R3 = SR-10 theo thứ tự ngược với tên; Tech Lead đã chốt (a)-(c) ở `03b`, cần sửa chữ ở stories/02b/README khi PO rảnh.
- **N6 (Low, hiển thị mock) — dòng "Cá thu 2,000 kg · 2.000 kg" lặp hai lần định dạng số** trong khung thông tin đơn (thấy ở ảnh mock lẫn Django thật). Có từ trước lô này, không thuộc SR-09; báo FE.
- Cảnh báo bảo mật hạ tầng ngoài phạm vi: `npm ci` báo 27 lỗ hổng gói (25 moderate, 1 high, 1 critical) trong `erp-console`; không do lô này thay đổi (lockfile không đổi). Đề xuất lên lịch `npm audit` riêng.

## Lệnh đã chạy (tóm tắt output)
```
backend  DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test                        -> Ran 1293 tests OK, 86 s (baseline 1241 + 52 QA)
backend  manage.py makemigrations --check --dry-run                                                 -> No changes detected
backend  manage.py test apps.inventory.batches.tests.test_p8_lo3_qa_edges                          -> Ran 22 OK
backend  manage.py test apps.delivery.tests.test_p8_lo3_qa_edges                                   -> Ran 13 OK
backend  manage.py test apps.sales.payments.tests.test_p8_lo3_qa_edges                             -> Ran 17 OK
HEAD-copy (git archive HEAD backend) + test dev Lô 3 (39)                                           -> 31 F + 3 E (đỏ đúng)
HEAD-copy + 3 file test QA                                                                          -> SR-08/10: F14 E1 · SR-09: F6 E10 · SR-11: F10 (đỏ đúng)
repro R2-R5 (doc/.../repro, tests.py) chạy 2 lần liên tiếp trên working tree                        -> R2, R3, R4, R5 bị chặn cả 2 lần, output giống hệt (R6 = Lô 4, vẫn lỗi cũ là đúng)
adapter  .venv/bin/python -m pytest -q                                                              -> 68 passed
erp-console  npm ci --cache <scratchpad> (không --legacy-peer-deps)                                 -> exit 0; lockfile md5 không đổi
erp-console  npx tsc --noEmit -> 0 ; npm run build -> 0 ; npm test                                  -> 99 passed (10 file)
Playwright  NEXT_PUBLIC_USE_MOCK=1 build -> http.server 3213 -> python3 e2e/sr09_ac4_stale_state.py -> 22/22 PASS (2 viewport)
Playwright  Django thật (SQLite tạm, cổng 8113) + build USE_MOCK=0 phục vụ 3214 -> e2e/sr09_ac4_real_backend.py (TRIGGER_CMD chạy auto_cancel_overdue) -> 11/11 PASS; DB: 0 delivery_confirmed, 1 Refund
erp-console  npm run build (bản thật, không mock) sau khi QA                                          -> exit 0; out/ không còn mock
Việc còn lại (⏸ E25): chạy ba cặp tranh chấp với 2 kết nối song song trên Postgres staging (ví dụ 2 luồng: cancel_expired_batch ↔ confirm_payment, publish_batch ↔ cancel_receipt, auto_cancel_overdue ↔ record_call) và xác nhận không deadlock, không dữ liệu lệch.
```

## Lô 4 — SR-12, SR-13, SR-14 (chứng từ đảo doanh thu, có migration 0011) · lần 1 · 2026-09-30

### Kết luận: APPROVED — 0 lỗi Critical/High/Medium; mọi AC chạy thật xanh, kể cả AC mới Duy đổi 30/09 (lập bù `issued_at` = lúc chạy, lô chốt không đổi, D1-B); mọi kịch bản so số kỳ cũ TRƯỚC/SAU đều bằng nhau ở mọi khoá; 1 ca ⏸ (tranh chấp song song thật cần Postgres); 4 ghi nhận Low không chặn
### Tổng: 64 ca · ✅ 63 · ❌ 0 · ⏸ 1 (2 giao dịch huỷ đồng thời trên Postgres staging: máy này không có Postgres, SQLite bỏ qua khoá dòng)

Cách đếm: 19 ca theo AC (SR-12 x8, SR-13 x7, SR-14 x4) + 38 test QA bổ sung độc lập với test của dev (mỗi `test_` = 1 ca) + 3 ca migration (sqlmigrate / migrate sạch + rollback + migrate lại /
`makemigrations --check`) + 1 ca tái hiện R6 + 2 ca hồi quy (backend đầy đủ, adapter) + 1 ca ⏸.

Phạm vi: code chưa commit trong working tree (`sales/credit_notes/services.py`, `sales/models/credit_notes.py`, migration `0011_salescreditnote`, `sales/orders/services.py`,
`sales/orders/timeline.py`, `sales/refunds/services.py`, `sales/admin.py`, `reports/services.py`, `reports/dashboard_api.py`, `management/commands/backfill_credit_notes.py` + 48 test của dev).
Không sửa code sản phẩm. QA thêm 2 file test (38 test):
- `backend/apps/sales/credit_notes/tests/test_qa_lo4_tien.py` (23 test: mọi đường huỷ, tiền nhiều kịch bản, lô/combo/ranh giới `closed_at`)
- `backend/apps/sales/credit_notes/tests/test_qa_lo4_backfill_leak.py` (15 test: lệnh lập bù, rò giá vốn/PII, Admin HTML thật, append-only, ma trận Group)
Không có FE thay đổi nên không chạy npm/Playwright (lô này chỉ BE). Dữ liệu chỉ là giả (Khách Giả Bí Mật, 0900000xxx, Số 1 Đường Thử; giá vốn mồi 123457 để dò rò theo chuỗi).
Không chạy `backfill_credit_notes --apply` với DB thật; mọi lần `--apply` nằm trong test trên DB test tạm. `backend/db.sqlite3` không bị đụng (mtime 13:51, trước phiên QA).

## Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| SR-12-AC1 (job tự huỷ → 1 chứng từ, hoá đơn giữ ISSUED) | ✅ | test dev `sr12_ac1` + QA `QAPathsTests` job 2 đơn (1 đơn lỗi); so `values()` hoá đơn trước/sau bằng nhau |
| SR-12-AC2 (huỷ tay, `created_by`) | ✅ | dev `sr12_ac2` chu/quan_ly; QA CSKH decide CANCEL → `created_by=ql1` |
| SR-12-AC3 (2 lô → 2 dòng) | ✅ | dev `sr12_ac3`; QA combo BUNDLE 2 lô thành phần về 0 |
| SR-12-AC4 (idempotent) | ✅ | QA: huỷ tay 2 lần → 4xx; decide lần 2 → 4xx; job chạy lại; thứ tự A→B và B→A; ràng buộc DB unique `source_key`/`code` (IntegrityError) — luôn 1 chứng từ |
| SR-12-AC5 (atomic, rollback) | ✅ | dev `sr12_ac5`; QA decide CANCEL lỗi lập chứng từ → đơn giữ trạng thái cũ, không CANCEL_RESTORE; job: đơn lỗi không kéo đơn khác |
| SR-12-AC6 (giao thất bại → `stock_restored=false`) | ✅ | dev `sr12_ac6`; QA lập bù đọc đúng `stock_restored=False` từ AuditLog |
| SR-12-AC7 (append-only) | ✅ | QA: superuser GET add/delete → 403, POST change/delete/action delete_selected không đổi bản ghi; mọi route API `credit-notes` (5 dạng x 5 phương thức x 5 user) → 404/405; PATCH/PUT/DELETE hoá đơn → 403/404/405 và hoá đơn vẫn ISSUED; không Group nào có add/change/delete; chỉ có 2 quyền `view_*`; ProtectedError khi xoá hoá đơn/lô có chứng từ |
| SR-12-AC8 (timeline + không rò giá vốn) | ✅ | QA quét response 5 Group x 12+ URL (đếm 200 > 0 mỗi nhóm); timeline có đúng 1 `credit_note_issued`, không giá vốn/PII; AuditLog `issue_credit_note` khoá = `{credit_note, amount, backfilled}` |
| SR-13-AC1 (lô, R6) | ✅ | repro R6 → `revenue 0.00000 qty_sold 0.000`; dev + QA `batch_pnl` `reversed_qty`/`reversed_revenue` |
| SR-13-AC2 (bán lại không cộng đôi) | ✅ | QA: huỷ → bán lại 2 kg → huỷ lại: đảo luỹ kế 4 kg / 600.000, `qty_sold`/`revenue` về 0, không âm |
| SR-13-AC3 (kỳ cũ không đổi) | ✅ | QA 10 kịch bản: hoá đơn 2 tháng trước / hoàn một phần / hoàn đủ / cùng tháng / hoàn sau huỷ / 2 phiếu hoàn khác kỳ / hoàn tạo trước xác nhận sau / job + hoàn; kỳ n≥1 giữ nguyên MỌI khoá; Σ profit và Σ cogs các kỳ = 0 |
| SR-13-AC4 (phiếu hoàn không trừ đôi; hoàn không có chứng từ vẫn trừ) | ✅ | QA hoàn sau huỷ / hoàn cùng kỳ (không trừ đôi); D1-B: hoàn 50.000 xác nhận trước huỷ → kỳ đó trừ, kỳ huỷ đảo 250.000; dev test hoá đơn không chứng từ vẫn trừ |
| SR-13-AC5 (dashboard `revenue_today`) | ✅ | QA: hôm nay 300.000 → 0 → −300.000 khi huỷ hoá đơn hôm qua (số âm đúng E1, xem L3) |
| SR-13-AC6 (ma trận báo cáo) | ✅ | QA `QAPermMatrixTests`: period/batch/dashboard chu 200/200/200; ql, kho 403/403/200; giao, cskh 403 x3; khách 401 x3 |
| SR-13-AC7 (docstring/spec) | ✅ | đọc diff: `confirm_refund`, spec BR-HT-06/BR-HT-10/BR-BC-04 ghi "Duy duyệt 30/09" (đây là kiểm chữ, không phải hành vi) |
| SR-14-AC1 (dry-run không ghi + liệt kê lô CLOSED) | ✅ | QA `CaptureQueriesContext`: 0 câu INSERT/UPDATE/DELETE; đếm CN và AuditLog trước/sau bằng nhau; in mã đơn/hoá đơn/số tiền/lô; dòng riêng "đơn … · lô … — lãi lỗ lô giữ nguyên" chỉ ở lô chốt |
| SR-14-AC2 (AC mới: `issued_at` = lúc chạy, `backfilled`, `created_by=None`) | ✅ | QA: 3 chứng từ, `issued_at` cách bây giờ < 5 phút, không phải ngày huỷ gốc, kỳ n≥1 bằng nhau mọi khoá, kỳ hiện tại `credit_notes` = 1.150.000 (300k + 300k + 250k sau trừ hoàn 50k + 300k huỷ mới), `cogs_reversed` đúng; lô CLOSED `batch_pnl` không đổi, lô còn mở được đảo |
| SR-14-AC3 (chạy 2 lần) | ✅ | QA: lần 2 in "0 đơn"/"Đã lập 0", `issued_at` từng chứng từ, AuditLog, số kỳ không đổi; lỗi giữa chừng (đơn 2 raise) → đơn 2 rollback, chạy lại lập đúng 1, không nhân đôi |
| SR-14-AC4 (output không PII/giá vốn) | ✅ | QA quét output dry-run + apply + apply lần 2: không tên/SĐT/địa chỉ, không `unit_cost`/`landed`/"giá vốn"/123457/220000 |

## Ngoại lệ & biên (ngoài đường thuận)
| Ca | Kết quả | Bằng chứng |
|---|---|---|
| Đơn còn PAID / đã huỷ mới (đã có chứng từ) không bị lập bù chọn | ✅ | QA backfill: DRY-RUN đúng 3 đơn, đơn PAID không có chứng từ |
| Đơn huỷ khi chưa thanh toán → không chứng từ | ✅ | QA `QAPathsTests` |
| Lô chốt trước huỷ: không đổi; chốt sau huỷ: giữ số đã đảo | ✅ | QA `QABatchTests` |
| Ranh giới `issued_at == closed_at` trừ; `+1µs` không trừ | ✅ | QA |
| Đơn 2 lô, 1 lô đã chốt: lô chốt đứng yên, lô còn lại đảo | ✅ | QA |
| Hoàn đủ trước huỷ → `credit_notes` = 0 (không âm) | ✅ | QA kịch bản hoàn đủ |
| Màn hình cũ: quản lý bấm CANCEL lần 2 sau CSKH đã huỷ | ✅ | QA 4xx, 1 chứng từ |
| `stock_restored=False` vẫn đảo cả doanh thu và `cogs_reversed` | ✅ | QA (ghi nhận: hàng chưa về kho nhưng vẫn đảo giá vốn theo thiết kế 02b) |
| Migration `sqlmigrate sales 0011` chỉ CREATE (2 bảng + 6 chỉ mục), không ALTER/DROP/UPDATE dữ liệu | ✅ | 19 dòng SQL |
| `migrate` trên SQLite sạch, `migrate sales 0010` (rollback), `migrate` lại | ✅ | lần lượt "Applying sales.0011 OK" / "Unapplying sales.0011 OK" / "Applying sales.0011 OK"; sau đó 2 bảng có, 0 dòng |
| `makemigrations --check --dry-run` | ✅ | No changes detected |
| Tranh chấp thật: 2 giao dịch cùng huỷ 1 đơn trên Postgres | ⏸ | không có Postgres; hai thứ tự tuần tự A→B và B→A xanh; ràng buộc unique DB chặn nhân đôi |

## Phân quyền (Group x hành động)
Khảo sát bằng chạy thật, mỗi ô là mã HTTP thực (đã đếm 200 > 0 cho từng nhóm để tránh xanh giả).
| Hành động | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| `GET /api/reports/period/`, `/api/reports/batch/<id>/` | 200 | 403 | 403 | 403 | 403 | 401 |
| `GET /api/dashboard/summary/` | 200 | 200 | 200 | 403 | 403 | 401 |
| Ghi (POST/PATCH/PUT/DELETE) mọi URL chứng từ | 404/405 | 404/405 | 404/405 | 404/405 | 404/405 | 401 |
| Admin thêm/sửa/xoá chứng từ (superuser cũng vậy) | 403 | 403 | 403 | 403 | 403 | n/a |
Ghi chú: huỷ đơn `sales.cancel_paid_order` (403 với nv_kho/nv_giao/cskh) đã có dev test `sr12_ac2_ma_tran_group`; CSKH decide CANCEL cần `delivery.decide_unconfirmed` (ql 200).

## Rò giá vốn
| Điểm kiểm | Kết quả | Bằng chứng |
|---|---|---|
| JSON 12+ endpoint x 5 Group (đơn, hoá đơn, guidance, dashboard, audit-logs, cskh queue, delivery notes, lô, ledger, report period/batch) | ✅ | QA `test_khong_ro_gia_von_va_pii_...`: nhóm thiếu `view_costprice` không có khoá giá vốn/`unit_cost`/`cogs_reversed`/`reversed_revenue`/"landed" và không có chuỗi 123457; đếm 200 mỗi nhóm > 0 |
| Admin HTML thật, staff thiếu `view_costprice` (7 trang: changelist, change, history, changelist dòng, change dòng, 2 kết quả tìm kiếm) | ✅ | không có "Giá vốn"/`unit_cost`/`field-unit_cost`/123457 |
| Đối chứng: staff có `view_costprice` thấy "Giá vốn ảnh chụp" và 123457 | ✅ | chứng minh ca kiểm nhạy, không xanh giả |
| AuditLog `issue_credit_note` | ✅ | `changes` chỉ `{credit_note, amount, backfilled}`; không có `qty`/khoá giá vốn |
| Tiền ÷ kg | ✅ | `reversed_revenue / reversed_qty` = 150.000 (giá BÁN), khác giá vốn 123457/110.000; chỉ Chủ đọc được (report 403 với nhóm khác); `amount` audit không kèm kg |
| Timeline đơn (2 đơn x 5 Group) | ✅ | 1 sự kiện `credit_note_issued`, không giá vốn/PII |
| Output lệnh backfill (dry-run, apply, apply lần 2) | ✅ | không giá vốn |

## Rò dữ liệu cá nhân
| Điểm kiểm | Kết quả | Bằng chứng |
|---|---|---|
| Shop công khai tra đơn đã huỷ có chứng từ | ✅ | không chứa `credit_note`/`DC-`/giá vốn/tên/địa chỉ; SĐT đầy đủ không trả |
| Chưa đăng nhập vào mọi URL nội bộ | ✅ | 401 |
| Log `cangca.delivery.cskh` khi 1 đơn lỗi khi job tự huỷ | ✅ | `assertLogs`: không chứa tên/SĐT/địa chỉ giả |
| AuditLog + timeline + output lệnh | ✅ | không PII |
| Chứng từ Admin | ✅ | chứng từ không lưu tên/SĐT/địa chỉ (chỉ FK hoá đơn); trang Admin HTML không chứa PII giả |
| Chứa PII ở `localStorage`/console/URL | n/a | lô BE, không đổi FE |

## Hồi quy
| Điểm kiểm | Kết quả | Bằng chứng |
|---|---|---|
| Toàn bộ backend | ✅ | `Ran 1379 tests OK` (baseline 1341 + 38 QA), 61 s, không `--parallel` |
| Adapter | ✅ | `68 passed` |
| Repro R6 | ✅ | `review_repro.tests.R6PnlAfterAutoCancel` OK, in "order CANCELLED invoice ISSUED, pnl revenue 0.00000 qty_sold 0.000" (trước Lô 4 là doanh thu 300000) |
| Repro R1–R5 (lô trước) | ✅ | vẫn chặn đúng: R2 `ConflictError` "Đơn đã bị huỷ", R3 `BusinessError BR-MH-05`, R5 `BusinessError` "Còn 2,000 kg đang giữ chỗ", R4 ok, R1 không còn crash. Các test repro bị "đỏ" vì bug đã hết (đúng kỳ vọng), không phải hồi quy |
| `reports`, `sales`, `delivery`, `inventory` liền kề | ✅ | nằm trong 1379 test |

## Lỗi
Không có lỗi chặn. Ghi nhận (Low, không chặn):
- **N1 (Low) — SR-13-AC5/E1: KPI "doanh thu hôm nay" bị trừ vào NGÀY chạy `--apply`, có thể âm** (thấy ở QA: hôm nay 300.000 → 0 → −300.000 khi huỷ hoá đơn hôm qua). Đúng theo quyết định Duy E1 ("kỳ hiện tại nhận điều chỉnh"), nhưng Duy nên biết khi chạy lập bù trên production: KPI ngày đó sẽ giảm đúng bằng tổng đơn huỷ cũ. Đề xuất chạy ngoài giờ xem số, hoặc ghi chú trên dashboard.
- **N2 (Low) — Combo BUNDLE: `SalesInvoiceLineBatch.qty` là kg thành phần, còn `rate` là giá combo**, nên `qty × rate` của dòng chứng từ khác `amount` chứng từ khi đơn là combo (nợ có sẵn từ trước, `amount` vẫn đúng và về 0 ở `batch_pnl`). Không đổi tiền; ghi nhận để Tech Lead xem khi nào có báo cáo theo dòng.
- **N3 (Low) — `period_pnl` tính `credit_notes` cho từng chứng từ nên có N+1 truy vấn phiếu hoàn** (đã là L4 ở `03b`). Đề xuất gom 1 truy vấn khi số chứng từ tăng.
- **N4 (Low, FE, đã có ở `03b` L1) — union kiểu timeline FE chưa có `credit_note_issued`**: sự kiện hiển thị được ở API nhưng FE cần thêm nhãn/icon. Không đổi tiền/dữ liệu.
- Lưu ý (không phải lỗi): 02b §4.4/§4.5 viết trước quyết định Duy 30/09 nên còn chữ "lập bù `issued_at` = ngày huỷ gốc"; code và stories mới là chuẩn. Đề xuất Tech Lead cập nhật chữ trong 02b.

## Lệnh đã chạy (tóm tắt output)
```
backend  manage.py test apps.sales.credit_notes.tests.test_qa_lo4_tien                              -> Ran 23 OK
backend  manage.py test apps.sales.credit_notes.tests.test_qa_lo4_backfill_leak                     -> Ran 15 OK (lần đầu 2 đỏ do số kỳ vọng SAI trong test QA: quên đơn o5 huỷ mới và đếm audit; đã sửa test, không phải lỗi sản phẩm)
backend  DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test                        -> Ran 1379 tests OK, 61 s
backend  manage.py makemigrations --check --dry-run                                                 -> No changes detected
backend  manage.py sqlmigrate sales 0011                                                            -> 2 CREATE TABLE, 6 CREATE INDEX, BEGIN/COMMIT
DATABASE_URL=sqlite:///<scratchpad>/qa-lo4/clean.sqlite3  manage.py migrate                        -> ... sales.0011 OK
DATABASE_URL=...clean.sqlite3  manage.py migrate sales 0010                                        -> Unapplying sales.0011 OK (2 bảng biến mất)
DATABASE_URL=...clean.sqlite3  manage.py migrate                                                    -> Applying sales.0011 OK (2 bảng có, 0 dòng)
repro R6 (gói tạm review_repro trong scratchpad, PYTHONPATH)                                        -> OK, revenue 0.00000 qty_sold 0.000; R2..R5 chặn, R1 hết crash
adapter  .venv/bin/python -m pytest -q                                                              -> 68 passed
(Không chạy `backfill_credit_notes --apply` trên DB thật; không đụng backend/db.sqlite3.)
Việc còn lại (⏸): 2 luồng huỷ cùng 1 đơn song song trên Postgres staging (`cancel_paid_order` ↔ `auto_cancel_overdue`), xác nhận không deadlock và không nhân đôi chứng từ.
Trước khi chạy `--apply` trên staging/production: chạy dry-run, đọc danh sách lô CLOSED và ước lượng KPI hôm nay (N1).
```


---

## Lô 5 — SR-15, SR-16, SR-17 + M5-1 (lô quá hạn còn tồn, trả NCC, dashboard bỏ tên khách, cắt mock khỏi bản thật; có migration `inventory/0004`) · lần 1 · 2026-09-30

### Kết luận: REJECTED — 1 lỗi chặn B1 (rò `supplier_refund_amount` ra Django Admin, trang chi tiết Nhật ký, cho tài khoản `is_staff` không phải Chủ). Mọi AC nghiệp vụ SR-15/16/17 và M5-1 đều xanh khi chạy thật; B1 là lỗ hổng CŨ của `AuditLogAdmin` (không lọc `changes` cho mọi khoá giá vốn), Lô 5 thêm một khoá mới đi qua đó. Sửa nhỏ (mục B1), chạy lại 1 test.
### Tổng: 86 ca · ✅ 84 · ❌ 1 · ⏸ 1

Cách đếm: 19 ca theo AC (SR-15 x7, SR-16 x8, SR-17 x4) + 5 ca M5-1 + 3 ca migration + 45 test QA bổ sung (44 + 1 ở `reports`, mỗi `test_` = 1 ca; 1 trong đó là ❌ B1) + 3 ca FE chạy thật (script mock 1366px, script mock 375px, luồng Django thật) + 10 ca hồi quy/build (backend đầy đủ, `makemigrations --check`, adapter, `npm ci` x2, `tsc` x2, `npm test` erp, build x2) + 1 ca ⏸.

Phạm vi: code chưa commit trong working tree (`inventory/batches/{services,api,serializers,next_steps}.py`, `inventory/models/{stock,supplier_returns,__init__}.py`, migration `0004_batchsupplierreturn`, `delivery/attention_api.py`, `reports/{services,dashboard_api}.py`, `erp-console/features/{inventory,overview,cskh,catalog,guidance}`, `frontend/{lib/api.ts,features/*}` + 55 + 13 test của dev). Không sửa code sản phẩm. QA thêm:
- `backend/apps/inventory/batches/tests/test_p8_lo5_qa_edges.py` (44 test: luồng đủ, lô đã bán, tranh chấp 2 thứ tự, `confirm_qty`, `request_id`, fuzz biên, ma trận Group, rò tiền NCC hoàn, AI, bất biến)
- `backend/apps/reports/tests/test_p8_lo5_qa_edges.py` (1 test: số kỳ không đổi)
- `erp-console/e2e/p8_lo5_qa_real_backend.py` (Playwright với Django thật)
- Ảnh QA chạy thật: `qa-lo5/qa-real-1366-*.png` (Django thật), `qa-lo5/qa-m51-*.png` (bản mock M5-1). Toàn bộ dữ liệu là giả (Khách Giả Năm/Sáu, `0900000456`, `0900000789`, Số 5 Đường Giả, tiền NCC hoàn mồi `1234567` và `999888`). `backend/db.sqlite3` không bị đụng (md5 `25ea4d9b…7dc` trước = sau).

## Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| SR-15-AC1 (EXPIRED còn tồn không chốt; API + luật sàn AI) | ✅ | dev 4 test luật sàn + QA `test_qa_expired_con_ton_khong_chot_duoc_moi_duong` (đủ kiểm kê vẫn 400 `BR-LO-04`); AI: QA job `run_due_ai_actions` chạy 2 lần → ESCALATED, audit/action không nhân đôi, lô vẫn EXPIRED 40 kg; Chủ bấm confirm đề xuất AI (mở chi tiết + đủ 3 giây) → 400 `BR-LO-04`, action vẫn PENDING |
| SR-15-AC2 (tồn 0 → chốt; CANCELLED chốt như cũ) | ✅ | QA `test_qa_flow_tra_nhieu_lan_ton_0_roi_chot` (3 lần trả 30/30/40 → tồn 0 → chốt cần kiểm kê BR-KK-05 → có kiểm kê thì CLOSED); `..._tra_mot_phan_roi_huy_phan_con_lai_roi_chot`; CANCELLED tồn 0 chốt được |
| SR-15-AC3 (Tiếp theo 3 bước) | ✅ | dev test guidance; FE thật: Playwright thấy 2 nút bật + Chốt khoá kèm "tồn = 0" (mock 77/77, Django thật 12/12) |
| SR-15-AC4 (thẻ Cần chú ý, ma trận quyền) | ✅ | QA `test_qa_attention_ma_tran` (chu 200 có khoá = 1; các nhóm khác 200 không có khoá hoặc 403; khách 401), `..._dem_theo_trang_thai` (đang bán 0 → EXPIRED 1 → +lô 2 = 2 → trả hết lô 2 = 1 → huỷ = 0), `test_qa_nguoi_chi_co_quyen_cancel_expired_van_lam_duoc` (200 `{"expired_batches_open": 1}`) |
| SR-15-AC5 (`confirm_qty` khớp màn hình) | ✅ | QA 4 ca: dạng số khớp (`100`, `100.000`, ` 100 `, `1E+2`, số nguyên/thực) → huỷ; lệch/rác (`99.999`, `0`, `-100`, `abc`, `NaN`, `Infinity`, `1e999`, `1,5`, `True`…) → 400, dữ liệu không đổi, không 5xx; không gửi/null/rỗng → chạy như cũ; trả 30 kg giữa chừng rồi bấm huỷ với 100 → 400 "Tồn đã đổi (70,000 kg)", tải lại rồi huỷ 70 → 200 |
| SR-15-AC6 (F11 `expired_qty` chỉ đếm huỷ lô quá hạn) | ✅ | QA lô có phiếu nhập bị huỷ (DW-18) rồi CLOSED: `expired_qty=0`, `total_cost = purchase+allocated`, `profit = revenue − total_cost` không đổi; lô trả 60 + huỷ 40 → `expired_qty=40` (chỉ phần huỷ) |
| SR-15-AC7 (FE chạy thật) | ✅ | Playwright mock `p8_lo5_fe_lo_qua_han.py` 1366px + 375px = **77/77 PASS**; Playwright Django thật `p8_lo5_qa_real_backend.py` = **12/12 PASS**: `loc` (Chủ) thấy tồn 6,5 kg, Chốt khoá; `kho1` (nv_kho) không có nút Huỷ/Trả/Chốt và không thấy thẻ. Ảnh `qa-real-1366-1..4` |
| SR-16-AC1 (trả 3/5 kg: tồn, sổ kho, bản ghi, audit) | ✅ | dev + QA: mỗi lần trả 1 dòng `SUPPLIER_RETURN`, 1 `BatchSupplierReturn`, 1 AuditLog; tổng biến động sổ kho = tồn; lô vẫn EXPIRED. Django thật: DB sau khi chạy có 2 bản ghi (2,000 kg/999888 và 4,500 kg/0), sổ kho lô 1 tổng 0, AuditLog đúng `return_batch_to_supplier` x2 + `close_batch` |
| SR-16-AC2 (trả hết → chốt) | ✅ | QA luồng đủ (xem SR-15-AC2) + Django thật: Trả hết (bấm đúp) → tồn 0 → Chốt lô mở → CLOSED (200) |
| SR-16-AC3 (lãi lỗ) | ✅ | dev + QA: lô đã bán 98 kg rồi trả 98 kg tiền 2.000.000 → `revenue`, `qty_sold`, `purchase_cost`, `allocated_cost`, `landed_unit_cost` không đổi; `total_cost −= 2.000.000`, `profit += 2.000.000`; `supplier_return_qty=100`, `supplier_refund_amount=3 x 1234567` ở lô đã chốt |
| SR-16-AC4 (biên) | ✅ | QA fuzz `qty` 27 giá trị rác/biên (0, âm, `100.001`, `1e12`, `NaN`, `Infinity`, `sNaN`, chữ số Ả Rập/full-width, list/dict/bool/null, thiếu) → 400 không đổi dữ liệu; hợp lệ biên `0.001` và `99.999`; tiền âm/`0.001`/`1e13`/`NaN`/`bool` → 400, `0`/rỗng/null/`0.01`/`999999999999.99` → 200; ghi chú >500 ký tự, giống SĐT/số tài khoản → 400; lô CLOSED/CANCELLED → 400 `BR-LO-05`; còn giữ chỗ → 400 `BR-LO-07` |
| SR-16-AC5 (bấm đúp `request_id`) | ✅ | QA 10 lần cùng `request_id` → 10 x 200 cùng `return_id`, đúng 1 dòng sổ kho, 1 bản ghi, 1 AuditLog; cùng `request_id` body khác → trả bản cũ (5 kg/111), không ghi đè; `request_id` của lô khác → 400 `BR-MH-08` không ghi; gửi lại sau khi lô đã bị huỷ → 200 bản cũ, sổ kho không đổi; Django thật bấm đúp → đúng 1 POST |
| SR-16-AC6 (không rò giá vốn) | ✅ (kèm B1, xem mục Lỗi) | response trả về chỉ có `{batch_id, status, qty_available, returned_qty, return_id}`; quét GET x 5 Group x 19 URL, đếm 200 > 30 (chu/quan_ly/nv_kho mỗi nhóm > 5): quan_ly/nv_kho/nv_giao/cskh không thấy `1234567`, `supplier_refund_amount`, `supplier_return_qty`; Nhật ký quan_ly không có khoá; Chủ thấy. **Riêng Admin HTML: ❌ B1** |
| SR-16-AC7 (AI trần C) | ✅ | `spec.max_level=="C"`, `force_c`; QA gọi lệnh qua API thật → 200 `outcome=proposal`, `level=C`, kho không đổi vì AI |
| SR-16-AC8 (FE chạy thật) | ✅ | mock 77/77 (1366 + 375, hộp form, `inputMode=decimal`, focus, chặn vượt tồn ngay ở form, 400 tiếng Việt + "Tải lại tồn", bấm đúp = 1 request, sau lưu không hiện lại tiền); Django thật 12/12 (POST `return-to-supplier` thật → 200, tồn lấy lại từ máy chủ 4,5 kg, không lộ `999888` ở DOM/URL/storage/console) |
| SR-17-AC1 (tái hiện: không `customer`/`phone_last4`) | ✅ | QA `test_qa_dashboard_5_khoa_moi_group_khong_pii_dem_200`: 2 đơn có tên/SĐT/địa chỉ giả (+ tên người chuyển `NGUYEN VAN GIA` trong `raw_payload`) → JSON của chu/quan_ly/nv_kho không chứa `Khách Giả Năm`, `Khách Giả Sáu`, `0900000456/789`, `0456`, `0789`, địa chỉ, `NGUYEN VAN GIA`, `phone_last4`, `customer`, `recipient`; có mã đơn (dữ liệu không rỗng) |
| SR-17-AC2 (5 khoá mọi nhóm) | ✅ | `set(row)=={code, amount, status, status_label, expires_at}` ở chu/quan_ly/nv_kho (đếm 3 x 200); nv_giao/cskh/không nhóm 403, khách 401 |
| SR-17-AC3 (FE chạy thật) | ✅ | Playwright mock 1366 + 375: cột chỉ còn 3 (Mã đơn, Giá trị, Trạng thái), DOM/HTML không có 9 tên khách mock cũ, placeholder không nhắc "khách", không cuộn ngang; nv_kho cũng vậy; console không có SĐT. Django thật: nv_kho không có cột Khách |
| SR-17-AC4 (AI `reports.dashboard_summary`) | ✅ | dev (SR-04-AC1 + `test_p8_pii_sweep`), chạy lại trong bộ đầy đủ 1492 OK |
| M5-1 build thật không lọt mock | ✅ | `NEXT_PUBLIC_USE_MOCK=0` + API Cloud Run truyền trực tiếp: erp-console và frontend `npm run build` OK; `grep -rlE "demo1234|0900000|Khách Giả|mockGet|mockSiteInfo" out/` = **0 file** ở cả hai; erp thêm `expiredSetQty|L0908-CT00|__caveMock` = 0; frontend không có `127.0.0.1`/`localhost:8000`. **Đối chứng dương:** cùng lệnh grep trên bản mock ra 3 file ở mỗi FE (grep không "xanh giả") |
| M5-1 build mock vẫn chạy mock | ✅ | frontend `NEXT_PUBLIC_USE_MOCK=1` (mặc dù `.env.local` cũng đặt 1): `/shop/` liệt kê Cá basa/Cá thu/Tôm sú…; thêm giỏ → `/shop/checkout/` thấy hàng, đặt hàng với dữ liệu giả → "Đặt hàng thành công" mã `DH-260930-xxxx` 65.000đ → "Thanh toán bằng VietQR" → sang trang cổng SePay GIẢ LẬP (`mock_gateway=1`); `/shop/orders/` tra `DH-DEMO001` + `6789` → "Đã thanh toán, đang soạn hàng"; erp-console: `/catalog/` "Danh mục & giá" 6 mặt hàng mock, `/inventory/` 11 lô; không lỗi trang (`pageerror` rỗng). Ảnh `qa-m51-*` |
| M5-1 rebuild bản thật cuối phiên | ✅ | build lại cả hai: frontend `out/` không còn chuỗi mock, chỉ trỏ `cangca-api-675411800433…` (Cloud Run); erp `out/` không mock, không trỏ `127.0.0.1:8115` |

## Ngoại lệ & biên (ngoài đường thuận)
| # | Tình huống | Kết quả | Bằng chứng |
|---|---|---|---|
| E1 | Lô đã từng bán (98 kg đã PAID) rồi trả NCC | ✅ | doanh thu/kg bán không đổi; đơn cũ vẫn PROCESSING; đơn PAID còn tham chiếu lô vẫn chặn chốt (BR-LO-04) dù tồn 0 |
| E2 | Tồn 0 rồi khách huỷ đơn đã thanh toán → hoàn 2 kg về lô EXPIRED | ✅ | tồn 2 kg, thẻ Cần chú ý sáng lại (0 → 1), trả tiếp 2 kg được, sổ kho khớp 0 |
| E3 | Lô đã CLOSED: trả NCC, huỷ phần tồn, chốt lại | ✅ | 3 lần đều 400 (`BR-LO-05`), snapshot (tồn, sổ kho, bản ghi, AuditLog) không đổi, `batch_pnl` lô đã chốt bằng nhau từng khoá; trả NCC ở lô KHÁC không đổi số lô đã chốt |
| E4 | Tranh chấp thứ tự A: đơn giữ chỗ 4 kg trước, lô hết hạn | ✅ | trả và huỷ đều 400 `BR-LO-07`, snapshot không đổi; job TTL chạy 2 lần (1 rồi 0); nhả giữ chỗ xong thì trả 100 kg được |
| E5 | Tranh chấp thứ tự B: trả NCC/huỷ trước, rồi mới đặt/giữ chỗ | ✅ | trả 50 kg rồi đặt đơn trên lô quá hạn → `BusinessError`, không giữ chỗ; đơn giữ chỗ đã thanh toán trước khi trả → tồn 96 kg, trả 97 → 400, trả 96 → 200, đơn PROCESSING nguyên vẹn |
| E6 | Màn hình cũ: huỷ xong rồi bấm trả; trả xong rồi bấm huỷ với `confirm_qty` cũ | ✅ | cả hai 400 `BR-LO-07`, không ghi gì; FE thật: 400 hiện đúng `detail`, "Tải lại tồn" cập nhật, thao tác lại thành công (mock, cả 2 kích thước) |
| E7 | Kỳ (`period_pnl`) khi trả NCC và huỷ lô quá hạn | ✅ | `revenue`, `cogs` kỳ không đổi (đúng thiết kế: kỳ tính giá vốn hàng đã bán); API kỳ của quan_ly không có khoá `supplier_refund` |
| E8 | Cờ bật/tắt | ✅ | không có cờ mới ở Lô 5; AI bật/tắt: AI tắt → 410 `AI_DISABLED` (bằng chứng test QA đầu tiên phải bật cờ mới có 200, không xanh giả) |
| E9 | Method/Content-Type lạ | ✅ | GET/PUT/DELETE → 405; JSON hỏng → 4xx; multipart/form-urlencoded → 200 (DRF phân giải) |
| E10 | Tranh chấp song song thật (2 giao dịch DB cùng lúc: trả NCC ↔ huỷ lô ↔ đơn giữ chỗ; cùng `request_id` cho 2 lô cùng lúc) | ⏸ | máy này không có Postgres; SQLite bỏ qua `select_for_update`. Cần chạy trên staging (xem Ghi nhận L5) |

## Phân quyền (Group x hành động)
Chạy thật (`QaPermissionMatrixTests`, đếm 200 > 0; nhóm không có quyền: tồn kho không đổi và response không chứa số tiền):
| | chu | quan_ly | nv_kho | nv_giao | cskh | không nhóm | khách |
|---|---|---|---|---|---|---|---|
| `POST …/return-to-supplier/` | 200 | 403 | 403 | 403 | 403 | 403 | 401 |
| `POST …/cancel-expired/` | 200 | 403 | 403 | 403 | 403 | 403 | 401 |
| `POST …/close/` (lô EXPIRED còn tồn) | 400 `BR-LO-04` | 403 | 403 | 403 | 403 | 403 | 401 |
| thẻ `expired_batches_open` | có | không | không | không | không | 403 | 401 |
| `GET /api/dashboard/summary/` | 200 | 200 | 200 | 403 | 403 | 403 | 401 |
| tạo `BatchSupplierReturn` bởi người khác Chủ | — | 0 | 0 | 0 | 0 | 0 | — |
403 luôn đứng trước validation (body rác vẫn 403). Người chỉ có quyền `inventory.cancel_expired_batch` (+ xem lô) làm được trả NCC và thấy thẻ (200 thay vì 403) như AC4. FE: nv_kho không thấy nút/thẻ (Playwright thật + mock).

## Rò giá vốn
- ✅ Response của trả NCC không có tiền hay khoá giá vốn (`find_keys(COST_KEYS)` rỗng).
- ✅ 5 Group x 19 URL GET (lô, chi tiết theo `id` và `batch_id`, `guidance/batch`, sổ kho, audit-logs, báo cáo lô, báo cáo kỳ, dashboard, attention, `ai/actions`, `ai/commands/index`, `ai/report/daily`…): > 30 response 200, nhóm khác Chủ không thấy `1234567`, dạng `1,234,567`, `supplier_refund_amount`, `supplier_return_qty`. Nhật ký `quan_ly` có đúng 1 dòng `return_batch_to_supplier`, không khoá giá vốn.
- ✅ Tính ngược tiền ÷ kg: người thiếu `view_costprice` chỉ thấy `qty` (kg) trong Nhật ký, không thấy tiền → không suy ra được giá vốn/kg; `note` chỉ là chữ cố định.
- ✅ Ghi chú người dùng nhập (`note` của bản ghi trả NCC) không lọt vào AuditLog, timeline, guidance, sổ kho, danh sách lô.
- ✅ Django thật: `999888` không có ở DOM, URL, `localStorage`/`sessionStorage`, console; payload có gửi nhưng không hiện lại sau khi lưu.
- ✅ AI: lệnh trả NCC chỉ soạn nháp (C); quan_ly/nv_kho/nv_giao/cskh gọi `ai/actions`, `commands/index`, `report/daily` (đếm 200 > 0) không thấy tiền.
- ❌ **Admin HTML: B1** — trang chi tiết Nhật ký (`/admin/accounts/auditlog/<id>/change/`) hiện nguyên `changes` cho `is_staff` quan_ly/nv_kho. Đối chứng cùng trang với khoá CŨ `purchase_rate` cũng lộ, tức lỗ hổng có sẵn.
- ✅ Admin còn lại: `BatchSupplierReturn` không đăng ký Admin (superuser vào `/admin/inventory/batchsupplierreturn/` = 404), trang Lô/Sổ kho của staff không có tiền; quyền của model chỉ có `view_batchsupplierreturn`.

## Rò dữ liệu cá nhân
- ✅ Dashboard JSON (chu/quan_ly/nv_kho): không tên, SĐT (cả 4 số cuối), địa chỉ, tên người chuyển khoản; tập khoá đúng 5.
- ✅ FE: DOM/HTML không có tên khách mock; console không có SĐT (Playwright mock + Django thật); URL không chứa dữ liệu cá nhân.
- ✅ AuditLog trả NCC: `changes = {qty, supplier_refund_amount}`, `note` không có tên/SĐT/địa chỉ.
- ✅ Ảnh và report chỉ dùng dữ liệu giả. Không có tra đơn công khai mới ở Lô 5 nên không có ca giới hạn tần suất mới.

## Chứng từ bất biến & AuditLog
- ✅ Không có endpoint xoá/sửa bản ghi trả NCC (DELETE 404); xoá lô có bản ghi trả NCC → `ProtectedError`; xoá người tạo → `ProtectedError`; Group không có quyền add/change/delete.
- ✅ AuditLog: mỗi hành động Tầng 2 đúng 1 dòng (`return_batch_to_supplier`, `cancel_expired_batch`, `close_batch`); 400 không ghi dòng nào.

## Hồi quy
- ✅ Bộ backend đầy đủ (không `--parallel`): **1492 test OK** (1447 gốc + 44 + 1 test QA; 1 expected failure là B1), 106 s; `makemigrations --check` = No changes.
- ✅ adapter: 68 passed.
- ✅ Lô 1–4 không đỏ (chạy trong bộ đầy đủ); Lô 3 (`STALE_STATE`, huỷ lô quá hạn) và Lô 4 (chứng từ đảo, `batch_pnl` lô chốt) vẫn đúng: `test_qa_lo4_*` OK.
- ✅ erp-console: `npm ci` (không `--legacy-peer-deps`) exit 0, `tsc --noEmit` exit 0, `npm test` 10 file / **103 test** OK, build OK. frontend: `npm ci` exit 0, `tsc` exit 0, build OK (không có script `npm test`).
- Ghi nhận: `npm audit` báo lỗ hổng phụ thuộc có sẵn (erp 27: 25 moderate, 1 high, 1 critical; frontend 2: 1 high, 1 critical); không thuộc Lô 5.

## Lỗi
### B1 — `supplier_refund_amount` lộ ra Django Admin (trang chi tiết Nhật ký) cho tài khoản `is_staff` không phải Chủ · Critical theo bảng mức (rò giá vốn) nhưng phạm vi hẹp · AC SR-16-AC6 / tiêu chí "không lọt Admin HTML"
- **Bước tái hiện** (test đỏ được giữ dưới `expectedFailure`): `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.inventory.batches.tests.test_p8_lo5_qa_edges.QaLeakTests.test_qa_admin_html_khong_lo_tien_ncc_voi_nhan_vien_khong_phai_chu` (bỏ dòng `@unittest.expectedFailure` để thấy đỏ). Thủ công: tạo `quan_ly` với `is_staff=True`; Chủ trả NCC 10 kg kèm tiền `1234567`; đăng nhập `/admin/` bằng tài khoản đó, mở `/admin/accounts/auditlog/<id>/change/`. Ca đối chứng `QaAdminAuditBaselineTests` cho thấy khoá cũ `purchase_rate` trong `changes` cũng lộ y hệt.
- **Mong đợi**: người không có `inventory.view_costprice` không thấy các khoá thuộc `COST_KEYS` (kể cả `supplier_refund_amount`) ở bất kỳ đầu ra nào, gồm Admin (bất biến 1). API `/api/audit-logs/` đã lọc đúng (`redact_cost`), Admin thì không.
- **Thực tế**: `apps/accounts/admin.py::AuditLogAdmin` hiển thị nguyên `changes` (JSON) trong trang chi tiết; `is_staff` + `view_auditlog` là đủ.
- **Ảnh hưởng**: rò giá vốn/tiền NCC hoàn cho nhân viên vào được Admin. Phạm vi hẹp: ứng dụng không bao giờ tự đặt `is_staff` và `UserAdmin` chỉ dành cho superuser, nên cần Duy/superuser chủ động cấp quyền Admin cho người không phải Chủ. Lỗ hổng có từ trước Lô 5 (ảnh hưởng mọi khoá giá vốn trong `changes`); Lô 5 thêm một khoá mới đi qua đó nên nằm trong tiêu chí lô này.
- **Đề xuất sửa (BE, nhỏ)**: trong `AuditLogAdmin` thêm `get_exclude`/`get_readonly_fields` bỏ hẳn cột `changes` khi `not request.user.has_perm("inventory.view_costprice")`, hoặc hiển thị `redact_cost(obj.changes)`; kèm test giữ nguyên ca `QaLeakTests…admin_html…` (bỏ `expectedFailure`) và đổi `assertIn` ở `QaAdminAuditBaselineTests` thành `assertNotIn`. Nếu Duy chấp nhận rủi ro (chưa cấp `is_staff` cho ai ngoài Chủ), điều phối viên có thể hạ B1 thành ghi nhận và chuyển sang Lô sau; QA giữ REJECTED theo bảng mức đến khi có quyết định đó.

### Ghi nhận (Low/không chặn)
- **L5-1** `qty` chấp nhận `"1_0"` (= 10, Python `Decimal` cho phép gạch dưới) và `request_id` chấp nhận số nguyên `12345` (DRF `UUIDField` ép thành UUID). Vô hại (Chủ-only, giá trị hợp lệ) nhưng khoá chống bấm đúp yếu hơn UUID ngẫu nhiên.
- **L5-2** Response trả `qty_available` bằng số thực JSON (ví dụ tồn 99,999 → `99.998999999999995…` khi đọc lại bằng `Decimal(float)`); chỉ ảnh hưởng hiển thị, FE làm tròn; sổ kho lưu `Decimal` đúng.
- **L5-3** Không có trần cho `supplier_refund_amount` (chấp nhận tới 999.999.999.999,99): `total_cost` của lô có thể âm. Chỉ Chủ nhập; cân nhắc cảnh báo khi tiền hoàn > giá mua lô.
- **L5-4** Timeline nhãn `SUPPLIER_RETURN` còn chung chung (nợ L5-4 của dev, đã ghi ở dev notes).
- **L5-5 (⏸ E10)** Tranh chấp song song thật và trường hợp cùng `request_id` gửi đồng thời cho 2 lô khác nhau (có thể `IntegrityError` → 500 thay vì 400 trên Postgres, không chứng minh được trên SQLite) cần chạy trên staging trước khi lên production.
- **L5-6** Ảnh chụp headless hiện tên biểu tượng Material Symbols dạng chữ cái vì font tải từ CDN, không phải lỗi sản phẩm.
- `period_pnl` không cộng tiền NCC hoàn (đúng thiết kế: kỳ tính giá vốn hàng bán, không tính hàng trả NCC) — chỉ để Duy biết khi đối chiếu số lô và số kỳ.

## Lệnh đã chạy (tóm tắt output)
```
backend  DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test                           -> Ran 1492 tests OK (expected failures=1), 106 s (baseline dev: 1447)
backend  manage.py makemigrations --check --dry-run                                                   -> No changes detected
backend  manage.py test apps.inventory.batches.tests.test_p8_lo5_qa_edges                             -> Ran 44 OK (expected failures=1 = B1); lần đầu 5 đỏ do kỳ vọng SAI trong test QA (số float, "1_0", request_id int, 0,001 vs 0,000), đã sửa test, không phải lỗi sản phẩm; riêng B1 là lỗi thật
backend  manage.py test apps.reports.tests.test_p8_lo5_qa_edges                                       -> Ran 1 OK
backend  DATABASE_URL=sqlite:///<scratchpad>/qa-lo5/clean.sqlite3 manage.py sqlmigrate inventory 0004 -> 1 CREATE TABLE, index, BEGIN/COMMIT
backend  ... clean.sqlite3 manage.py migrate / migrate inventory 0003 / migrate                        -> Applying inventory.0004 OK / Unapplying OK (bảng biến mất) / Applying OK
adapter  ../backend/.venv/bin/python -m pytest -q                                                     -> 68 passed
erp      npm ci --cache <scratchpad>/npm-cache ; npx tsc --noEmit ; npm test                          -> exit 0 ; exit 0 ; 10 file / 103 test OK
frontend npm ci --cache <scratchpad>/npm-cache ; npx tsc --noEmit                                     -> exit 0 ; exit 0
erp      NEXT_PUBLIC_USE_MOCK=1 npm run build -> out copy sang scratchpad; python3 -m http.server 3215 ; BASE=http://127.0.0.1:3215 python3 e2e/p8_lo5_fe_lo_qua_han.py   -> 77/77 PASS (1366px + 375px); nhiễu console chỉ là "Failed to fetch RSC payload" do http.server tĩnh
Django thật  SQLite tạm <scratchpad>/qa-lo5/real.sqlite3, migrate + seed 2 lô EXPIRED + 2 user (loc/chu, kho1/nv_kho), runserver 127.0.0.1:8115 (CORS 127.0.0.1:3216)
erp      NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8115 npm run build ; http.server 3216 ; python3 e2e/p8_lo5_qa_real_backend.py                          -> 12/12 PASS; DB sau: lô 1 CLOSED tồn 0, 2 bản ghi trả NCC (2,000/999888 và 4,500/0), sổ kho lô 1 tổng 0, AuditLog return x2 + close
M5-1     NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=<Cloud Run> npm run build (erp, frontend) ; grep -rlE "demo1234|0900000|Khách Giả|mockGet|mockSiteInfo" out/   -> 0 file / 0 file
M5-1     đối chứng dương: cùng grep trên bản mock                                                     -> 3 file / 3 file
M5-1     frontend NEXT_PUBLIC_USE_MOCK=1 npm run build ; http.server 3217 ; Playwright /shop/, /shop/checkout/, /shop/orders/ (DH-DEMO001/6789)  -> catalog mock, đặt hàng mock, cổng SePay giả lập, tra đơn mock đều chạy; erp mock /catalog/, /inventory/ có dữ liệu mock
M5-1     rebuild bản thật cuối phiên (erp, frontend) + grep                                           -> 0 file mock; frontend chỉ trỏ Cloud Run
md5 backend/db.sqlite3                                                                                -> 25ea4d9bb8dc1de7533a236dc6ab07e4 (không đổi)
(Đã tắt mọi server 3215/3216/3217/8115. Không commit, không deploy.)
Việc còn lại (⏸): chạy E10 trên staging (Postgres) trước khi lên production; sau khi sửa B1 chạy lại `test_p8_lo5_qa_edges` (bỏ expectedFailure) + bộ backend đầy đủ.
```

---

## Lô 5 — lần 2 (kiểm lại B1) · 2026-09-30

### Kết luận: APPROVED — B1 (Critical) đã sửa, kiểm bằng HTML Admin thật ở 20 đường x 2 nhóm staff + Chủ + superuser; không lỗi mới
### Tổng lần 2: 8 ca mới/đổi · ✅ 8 · ❌ 0 · ⏸ 0 (E10 Postgres vẫn ⏸ từ lần 1, chuyển sang staging)

### Theo ca
| Ca | Kết quả | Bằng chứng |
|---|---|---|
| B1-1 quan_ly + nv_kho (is_staff, có `view_auditlog`, KHÔNG có `view_costprice`) quét 20 đường Admin của AuditLog: danh sách, `?q=` (theo hành động / theo chuỗi tiền / theo giá trị khoá cũ), lọc `action`/`model_name`/`actor_kind`, `date_hierarchy` (`created_at__year`), sắp xếp `?o=`, change view (dòng trả NCC, khoá cũ `purchase_rate`, khoá lồng `lines[].unit_cost` + `meta.purchase_cost`, `changes={}`, `changes=None`), `?_popup=1`, `/<id>/` (302 về change), `/history/`, `/delete/`, `/add/`, `/export/` | ✅ | `QaAdminB1MatrixTests.test_qa_b1_quan_ly_va_nv_kho_khong_thay_gia_von_o_moi_duong_admin`: mỗi nhóm >= 12 phản hồi 200 (`assertGreaterEqual(n200, 12)`), 0 trang chứa `1234567`, `7654321`, `5550001`, `5550002`, `supplier_refund_amount`, `purchase_rate`, `unit_cost`, `purchase_cost` |
| B1-2 khoá không nhạy cảm vẫn hiện (không ẩn quá tay), dòng rỗng/None không 5xx | ✅ | `..._khoa_khong_nhay_cam_van_hien_...`: `status`, `qty`, `meta.ok` hiện với quan_ly; change view `changes={}`/`None` trả 200 |
| B1-3 Chủ (is_staff) + superuser thấy đủ | ✅ | `..._chu_va_superuser_thay_du_o_change_view`: mỗi người > 8 phản hồi 200; thấy `7654321`, `supplier_refund_amount`, `1234567`, `5550001` |
| B1-4 append-only: POST sửa / POST xoá / action `delete_selected` bị từ chối (không 5xx); số dòng, `changes`, `note` trong DB không đổi sau khi staff/superuser xem hoặc thử sửa (bản ẩn không ghi đè dữ liệu gốc) | ✅ | `..._khong_sua_khong_xoa_nhat_ky_...` |
| B1-5 4 ca dev đã đổi (bỏ `expectedFailure`, đối chứng Chủ/superuser) chạy lại | ✅ | `QaLeakTests.test_qa_admin_html_...` + `QaAdminAuditBaselineTests` (2 ca) đều xanh; đỏ -> xanh so với lần 1 |
| B1-6 đối chứng đột biến (không sửa code sản phẩm): `mock.patch("apps.accounts.admin.can_view_cost", return_value=True)` rồi chạy đúng ca B1-1 | ✅ | Ca đỏ (change view, `?_popup=1`, `/<id>/` lộ) -> test QA thật sự bắt được lỗi; bản thật thì xanh |
| Hồi quy: full backend | ✅ | `Ran 1497 tests ... OK` (1493 của điều phối + 4 ca QA mới), 0 expected failure |
| Hồi quy: migration / adapter / db.sqlite3 | ✅ | `makemigrations --check --dry-run` = No changes detected; adapter `68 passed`; md5 `db.sqlite3` = `25ea4d9b...e4` không đổi |

### Phân quyền Admin AuditLog (HTML thật)
| Người xem | Thấy dòng Nhật ký | Thấy khoá COST_KEYS / tiền NCC hoàn | Sửa / xoá |
|---|---|---|---|
| quan_ly (is_staff + view_auditlog) | có (200) | không (đã lọc bởi `redact_cost`) | không |
| nv_kho (is_staff + view_auditlog) | có (200) | không | không |
| Chủ (is_staff, có `view_costprice`) | có | có (đủ) | không |
| superuser | có | có (đủ) | không (`has_delete/change/add_permission` = False) |
| Chưa đăng nhập / nv_giao / cskh không is_staff | về trang đăng nhập Admin (lần 1: đã kiểm) | không | không |

### Rò giá vốn / dữ liệu cá nhân
- Giá vốn: đã đóng ở mọi đường Admin của AuditLog (B1). Khoá suy ra được giá vốn (tiền ÷ kg) `supplier_refund_amount` và khoá cũ `purchase_rate` không còn trong HTML cho người thiếu quyền, kể cả khi lồng trong list/dict.
- Ghi chú kiểm thử: trang tìm kiếm dội lại đúng chuỗi người xem gõ (ô `q` và link lọc) — đã loại phần dội lại khỏi phép dò để khỏi báo lỗi giả; `search_fields` chỉ gồm `action`, `object_repr`, `object_id` nên không dò ngược được nội dung `changes` qua ô tìm kiếm (ca `?q=1234567` cho 200 và không có dòng nào khớp qua `changes`).
- Dữ liệu cá nhân: không đổi so với lần 1 (không có tên/SĐT/địa chỉ trong trang Nhật ký; dữ liệu toàn giả).
- Còn lại (Low, chấp nhận): trường `note` của AuditLog không được lọc — theo quy ước chỉ chứa mô tả (vd. `return_batch_to_supplier 5kg`, không có tiền). Ca quét không tìm thấy số tiền trong `note`.

### Lỗi
Không có lỗi chặn nào còn lại. B1 đóng. Ghi nhận Low L5-1..L5-6 từ lần 1 không đổi, không chặn.

### Lệnh đã chạy lần 2
```
backend  manage.py test apps.inventory.batches.tests.test_p8_lo5_qa_edges.QaAdminB1MatrixTests      -> lần đầu 2 đỏ do kỳ vọng SAI của test QA (khoá `cost_price` không thuộc COST_KEYS; `note` dòng trả NCC không rỗng; ô tìm kiếm dội lại chuỗi gõ) -> sửa test, xanh
backend  manage.py test apps.inventory.batches.tests.test_p8_lo5_qa_edges                           -> Ran 49 OK
backend  đột biến patch can_view_cost=True (file tạm, đã xoá)                                       -> ca B1-1 đỏ như kỳ vọng
backend  DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test                        -> Ran 1497 tests in 107.7s OK
backend  manage.py makemigrations --check --dry-run                                                 -> No changes detected
adapter  ../backend/.venv/bin/python -m pytest -q                                                   -> 68 passed
md5 backend/db.sqlite3                                                                              -> 25ea4d9bb8dc1de7533a236dc6ab07e4 (không đổi)
Playwright/FE: không chạy lại (FE không đổi kể từ lần 1; kết quả lần 1 giữ nguyên: erp 77/77 + 12/12, M5-1 sạch)
```
Việc còn lại (⏸): E10 tranh chấp song song thật trên staging (Postgres) trước khi lên production. Không commit, không deploy.

---

## Lô 6 — SR-21 (phần Shop) · 2026-09-30

### Kết luận: REJECTED (phần Shop) — mọi AC GL-01..GL-04 có bằng chứng chạy thật và đạt, nhưng phát hiện B1 (Medium): bản build thật `NEXT_PUBLIC_USE_MOCK=0` vẫn chứa mã và dữ liệu mock
Phạm vi lượt này: chỉ `frontend/`. Không build, không chạy, không sửa `erp-console/` (fe-dev đang sửa song song). Không sửa code sản phẩm. Không commit, không deploy.

### Tổng: 322 ca · ✅ 319 · ❌ 1 · ⏸ 2 (+ 1 ghi nhận Low)
- `frontend/e2e/ra-soat-a2-golive.py` chạy lại trên code hiện tại: 43/43 ✅.
- `frontend/e2e/qa-lo6-sr21-shop.py` (script bù mới): 279 ca, 277 ✅, 1 ❌ (M5-1 → B1), 1 Low (B2, không làm đỏ exit code).
- ⏸ 2 mục thuộc `erp-console/` (CS-11-AC6, X-AC4), xem cuối mục này.

### Theo AC
Bằng chứng A2 = `frontend/e2e/ra-soat-a2-golive.py`. Bằng chứng bù = `frontend/e2e/qa-lo6-sr21-shop.py`. Ảnh nằm ở `doc/features/2026-09-30-sua-loi-review/qa-lo6/`.

| Mã AC | Kết quả | Bằng chứng (script / ảnh) và ca ngoài đường thuận |
|---|---|---|
| GL-01-AC2 (footer Shop hiện người bán) | ✅ | A2 + script bù. Ảnh `gl01-ac2-shop-footer.png`, `sr21-gl01-footer-shop-1280.png`. Ngoài đường thuận: footer có ở mọi route (`/shop/`, checkout, tra đơn, trang nội dung), không trùng với `footer.site-footer` của layout Shop |
| GL-01-AC5 (site-info lỗi) | ✅ | A2 + script bù. Ảnh `gl01-ac5-site-info-error.png`. Ngoài đường thuận: `/api/public/site-info/` trả 500 và timeout → trang vẫn dùng được, không vỡ, không lộ stack |
| GL-01-AC6 | ✅ | Script bù: dữ liệu người bán chỉ là dữ liệu doanh nghiệp, không có tên/SĐT/địa chỉ khách |
| GL-02-AC1..AC4 (link chính sách trong footer) | ✅ | A2 + script bù. Ngoài đường thuận: `footer-links` rỗng, một link thiếu, link lỗi API |
| GL-02-AC5 (mobile) | ✅ | A2 (`gl02-ac5-mobile-375.png`) + script bù (`sr21-gl02-footer-375-chu-dai.png`, chuỗi dài, không tràn ngang, không cuộn ngang ở 375px) |
| GL-03-AC2 (ô đồng ý ở checkout) | ✅ | A2 (`gl03-ac2-checkout-consent.png`) + bù (`sr21-gl03-ac2-checkout-375.png`). Ngoài đường thuận: chưa tích thì không gửi được đơn, payload không có `privacy_consent` thì Shop không tự gửi |
| GL-03-AC4 (409 POLICY_CHANGED) | ✅ | A2 (`gl03-ac4-policy-changed.png`) + bù (`sr21-gl03-ac4-409-375.png`). Ngoài đường thuận: sau 409 giỏ hàng còn nguyên, ô đồng ý bị bỏ tích, gửi lại bằng `policy_version_id` mới thì được |
| GL-03-AC5 (503 Shop tạm chưa nhận đơn) | ✅ | A2 (`gl03-ac5-shop-closed.png`) + bù (`sr21-gl03-ac5-503-375.png`). Ngoài đường thuận: nút đặt bị khoá, giỏ hàng giữ nguyên |
| GL-03-AC8 (sau đặt đơn) | ✅ | Script bù, ảnh `sr21-gl03-ac8-sau-dat-don-1280.png`. Bấm đúp nút đặt chỉ gửi 1 POST; storage sau đặt đơn không có PII |
| GL-04-AC1 (ConfirmCallNotice bật) | ✅ | A2 (`gl04-ac1-notice-on.png`) + bù (`sr21-gl04-ac1-notice-375.png`). Ngoài đường thuận: cờ `confirm_call_notice` tắt thì không hiện |
| GL-04-AC2 (màn quay về) | ✅ | A2 (`gl04-ac2-return-success.png`) + bù (`sr21-gl04-ac2-return-375.png`). Ngoài đường thuận: quay về bằng URL `?code=..&result=success` khi sessionStorage trống, không hiện số cuối, không vỡ |
| GL-04-AC3 (chỉ 4 số cuối) | ✅ (kèm Low B2) | Bù: khối thông báo chỉ hiện 4 số cuối. Ca đối kháng (sessionStorage bị sửa thành SĐT đầy đủ) làm lộ B2 |
| GL-04-AC4, AC5 | ✅ | A2 + script bù |
| Phát hiện thêm: M5-1 (bản build thật không lọt mock) | ❌ B1 | Script bù quét `frontend/out/`, xem B1 |
| CS-11-AC6 (PDF tem 1 trang 100x150mm, QR) | ⏸ | Thuộc `erp-console/`, không chạy lượt này (xem cuối mục) |
| X-AC4 (storage/URL/console CSKH) | ⏸ | Thuộc `erp-console/`, không chạy lượt này (xem cuối mục) |

### Ngoại lệ và biên (đã phủ trong script bù)
- Bấm đúp nút đặt hàng: 1 POST.
- Trạng thái đã đổi: chính sách đổi phiên bản giữa lúc mở checkout và lúc gửi (409), Shop đóng cửa (503) giữa chừng.
- API lỗi/timeout: site-info, footer-links, privacy, entries.
- Cờ bật/tắt: `confirm_call_notice`.
- Chuỗi rất dài ở footer 375px.
- Đối kháng: sessionStorage bị sửa thủ công.

### Phân quyền
Phần Shop công khai, không có Group. Không có endpoint quản trị nào được gọi từ `frontend/`. Ca chưa đăng nhập: toàn bộ luồng chạy không cần token.

### Rò giá vốn
Payload gửi cổng thanh toán và mọi request từ Shop được quét: không có khoá giá vốn (`cost`, `cost_price`, `avg_cost`, `landed_cost`). Đạt.

### Rò dữ liệu cá nhân
Hàm `sweep_pii` chạy sau mỗi luồng chính, kiểm tra: `localStorage`, `sessionStorage`, cookie, `history.state`, URL hiện tại, console, pageerror, URL của mọi request, và host đích chỉ thuộc `{origin, localhost:8199, pay-sandbox.qa.example}` (không bên thứ ba ngoài cổng thanh toán). Giỏ hàng chỉ giữ `item_code,name,price,unit,qty`. Đạt.
- Đối chứng dương (chống xanh giả): cấy PII giả vào storage, console, request URL và URL, cả 4 detector đều bắt được (`scratchpad/qa-lo6-sr21/ctrl.py`).
- Chỉ dùng dữ liệu giả (`Khách Thử`, `0900000xxx`, địa chỉ mẫu). Ảnh chụp không chứa dữ liệu thật.

### Hồi quy
`ra-soat-a2-golive.py` 43/43 xanh. `npx tsc --noEmit` exit 0. `npm run build` thành công. `npm ci` không cần `--legacy-peer-deps`, không ERESOLVE.

### Lỗi
#### B1 — Bản build thật vẫn chứa mã và seed mock · Medium · M5-1 (kèm GL-03/GL-04 vì cùng bundle)
Bước tái hiện:
1. `cd frontend && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-675411800433.asia-southeast1.run.app npm run build`
2. `grep -rlE "DH-DEMO00|CA-BASA-PHILE|cangcaloc_mock_orders" frontend/out`
Mong đợi: không có file nào (bản build thật không mang mock).
Thực tế: khớp chunk `frontend/out/_next/static/chunks/116-14e277bb1ef9e7d2.js`, tải trên mọi trang. Seed mock (mã đơn `DH-DEMO00x`, mặt hàng mẫu, key `cangcaloc_mock_orders`) nằm trong bundle production.
Ảnh hưởng: Shop production tải thêm mã mock và dữ liệu giả; vi phạm M5-1 (bản thật không lọt mock). Dữ liệu là giả nên không phải rò PII thật. Lưu ý: kết luận "M5-1 sạch" ở Lô 5 dùng mẫu grep không khớp seed thật của `lib/mock.ts` nên bỏ sót. Gợi ý cho FE: `lib/api.ts` / `lib/mock.ts` cần điều kiện tĩnh `process.env.NEXT_PUBLIC_USE_MOCK === "1"` ở chỗ import để bundler cắt nhánh (import động hoặc điều kiện tĩnh).
Kiểm lại sau sửa: cùng lệnh grep trên phải rỗng; chạy lại `frontend/e2e/qa-lo6-sr21-shop.py` (ca M5-1 chuyển xanh).

#### B2 — `recallOrderContact` không kiểm 4 chữ số · Low · GL-04-AC3
Bước tái hiện: đặt `sessionStorage["cangcaloc_last_order_contact_v1"] = {"order_code":"DH-DEMO001","phone_last4":"0900000123"}` rồi mở `/shop/orders/?code=DH-DEMO001&result=success`.
Mong đợi: bỏ qua giá trị không đúng 4 chữ số.
Thực tế: SĐT đầy đủ được đưa vào ô `#phoneLast4` và vào query `?phone_last4=`. Khối thông báo vẫn chỉ hiện 4 số cuối. Không xảy ra ở luồng thường (chỉ khi storage bị sửa tay), nên ghi nhận Low, không chặn.
Gợi ý: validate `/^\d{4}$/` trong `frontend/features/checkout/storage.ts`.

#### INFO — F10
Thuộc Lô 7, không xử lý ở đây.

### CS-11-AC6 và X-AC4: ⏸ (chạy lại ở QA Lô 6 cuối, sau khi fe-dev xong `erp-console/`)
Lý do: yêu cầu giao việc cấm build/đụng `erp-console/` lượt này. Lệnh cần chạy (theo `doc/features/2026-09-30-ra-soat-agy/A4-cskh-in-tem.md`):
```
cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build
cd erp-console/out && python3 -m http.server 3203 &
cd erp-console/e2e && SHOTS=<thư mục ảnh> python3 ra_soat_cs11_ac6_label_pdf.py   # kỳ vọng 5/5 (cần pypdf)
cd erp-console/e2e && python3 ra_soat_x_ac4_storage.py                             # kỳ vọng 32/32
# sau đó build lại bản thật: cd erp-console && npm run build (không để bản mock trong out/)
```

### Lệnh đã chạy (Lô 6, phần Shop)
```
frontend  npm ci --cache <scratchpad>/npm-cache   -> OK, không ERESOLVE (lần đầu EACCES ở ~/.npm/_cacache: lỗi môi trường, không phải lockfile)
frontend  npx tsc --noEmit                        -> exit 0
frontend  NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8199 npm run build -> OK; copy out/ sang scratchpad/qa-lo6-sr21/
serve     python3 -m http.server 3106 (thư mục scratchpad/qa-lo6-sr21)
QA_BASE=http://localhost:3106 python3 frontend/e2e/ra-soat-a2-golive.py -> 43/43 PASS
QA_BASE=http://localhost:3106 QA_OUT_DIR=<scratchpad>/qa-lo6-sr21 QA_SHOT_DIR=<qa-lo6> python3 frontend/e2e/qa-lo6-sr21-shop.py -> 277 PASS, 1 FAIL (M5-1), 1 LOW (B2)
frontend  NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-675411800433.asia-southeast1.run.app npm run build -> OK; frontend/out/ là bản thật (không còn localhost:8199), nhưng vẫn còn seed mock (B1)
```
Lần chạy đầu của script bù có 2 lỗi do chính script QA (strict-mode locator `footer` khớp 2 phần tử; thời điểm chuyển trang ở ca "Quay lại cửa hàng"), đã sửa trong script, không phải lỗi sản phẩm.
Không đụng `erp-console/`, không sửa code sản phẩm (chỉ thêm biến `QA_BASE` vào script E2E `ra-soat-a2-golive.py`), không commit, không deploy.

---

## Lô 6 — SR-18, SR-19, SR-20, SR-21 (ERP + Shop) + M5-1b, B2, F6-1, F6-2 · lần 2 (QA cuối) · 2026-09-30

### Kết luận: APPROVED — mọi AC Lô 6 có bằng chứng chạy thật (kể cả backend thật + mạng thật), B1 (M5-1b) đã đóng, không còn lỗi chặn
Phạm vi: code chưa commit trong working tree. Không sửa code sản phẩm. Chỉ sửa 1 fixture test (xem L6-4). Không commit, không deploy. Đã dừng mọi server tạm (3106, 3203, 3216, 3218, 8116).

### Tổng: 0 ❌ trên mọi bộ dưới đây (E2E/tập lệnh: 74 + 52 + 5 + 32 + 279 + 46 = 488 ca ✅; vitest 103; BE 1523 + 34) · ⏸ 1 ô ma trận (cskh trên backend thật) · 4 ghi nhận Low/INFO
| Bộ | Kết quả |
|---|---|
| Backend toàn bộ (`manage.py test`, không `--parallel`) | 1523 OK (baseline 1523), `makemigrations --check` sạch |
| SR-18 riêng (repro A5 + ca QA thêm + test dev + sanitize) | 34 OK |
| erp-console `npm test` (vitest) | 103/103 |
| E2E ERP bản mock `p8_lo6_fe_sr19_sr20.py` (cổng 3216) | 74/74 |
| E2E ERP backend thật (Django 8116 + build thật 3218, mạng thật) `qa_lo6_real.py` + `qa_lo6_real_f61.py` | 52 ✅ (+1 báo đỏ giả, xem L6-5) |
| SR-21 ERP: `ra_soat_cs11_ac6_label_pdf.py` / `ra_soat_x_ac4_storage.py` | 5/5 / 32/32 (đóng ⏸ lượt trước) |
| SR-21 Shop: `qa-lo6-sr21-shop.py` trên build thật | 279 ca, 0 FAIL, 0 LOW |
| Shop `ra-soat-a2-golive.py` | 46/46 (sau khi sửa fixture, L6-4) |
| `check-ai-chunks.mjs` (bản thật) | XANH exit 0; đỏ trên build HEAD (đối chứng dương) |
| `check-no-mock.mjs` erp + frontend | XANH trên build thật; ĐỎ (36 chỗ) trên build mock (đối chứng dương) |

### Theo AC
| Mã AC | Kết quả | Bằng chứng và ca ngoài đường thuận |
|---|---|---|
| SR-18-AC1 (tạo bài với ảnh bài khác) | ✅ | Repro `A5-f1-idor-cover-image-on-create.py` chuyển đỏ sang xanh (HEAD: 201, cây làm việc: 400 `BR-ND-07`). Ngoài đường thuận: các kiểu cover lạ (bool, số âm, 0, chuỗi chữ) xử lý qua `_as_pk`, không 500 (bộ 34 OK) |
| SR-18-AC2 (sửa bài với ảnh bài khác) | ✅ | Test dev + `qa_lo6_sr18.py`: 400; ảnh cùng bài vẫn gán được (không chặn nhầm); ảnh trong `body` bài khác cũng bị chặn (strict) |
| SR-18-AC3 (tầng 1b, API công khai không lộ ảnh nháp bài khác) | ✅ | `test_p8_sr18_public.py` + ca QA: bài đã đăng có cover/body trỏ ảnh bài khác thì API công khai không trả URL/alt của ảnh đó (không trả ALT-A-SECRET) |
| SR-18-AC4 (Group) | ✅ | chu/quan_ly/cskh được tạo-sửa nội dung; nv_kho/nv_giao 403 trước cả khi kiểm ảnh; chưa đăng nhập 401 |
| SR-19-AC1 (đơn có bằng chứng, link Xem phiên bản đúng V đã đồng ý) | ✅ | Mạng thật: đơn #1 (đồng ý v1, chính sách đã lên v2) có link `?id=1&version=1`, panel hiện "MAU-QA-V1" và không có "MAU-QA-V2"; GET `/versions/1/` 200. Ảnh `real-sr19-1-order.png`, `real-sr19-2-panel-v1.png`. Ngoài đường thuận: đơn #2 không có bằng chứng thì không có link; `version=2` hiện V2 |
| SR-19-AC2 (không tìm thấy) | ✅ | `version=99` mạng thật 404 -> "Không tìm thấy phiên bản 99" + nút "Về bài" đóng panel (`real-sr19-3-notfound.png`). Ca URL lạ ở bản mock (bộ 74 ca): tham số `version` không hợp lệ (`^\d{1,9}$`, >0) bị bỏ qua, không vỡ |
| SR-19-AC3 (Group) | ✅ | Mạng thật: chu và quan_ly 200 (thấy link); nv_kho và nv_giao 403 khi gọi API, vào thẳng URL không thấy nội dung, `/orders` không có link; chưa đăng nhập 401. Panel chỉ đọc (không input/textarea/nút khôi phục) |
| SR-20-AC1/AC2 (Nhờ luôn hiện, "Để AI làm" theo `step.ai`) | ✅ | Mock 74/74 + mạng thật: AI tắt thì "Nhờ" có, "Để AI làm" không có. AI bật (`step.ai=C`): có cả hai. `step.ai=null` kể cả đã đồng ý model: không có huy hiệu và không có nút. Không cần đồng ý tải model để thấy "Để AI làm" |
| SR-20-AC3 (mở màn khi AI tắt: 0 request `/api/ai/commands|status`) | ✅ | Mạng thật: `/orders` + chi tiết, `/orders/payments`, `/orders/refunds`, `/inventory` đều 0 request `/api/ai/*` (guidance thật 200). Bấm đúp "Nhờ": đúng 1 POST `/api/ai/actions/escalate/` (201) — ngoại lệ hợp lệ theo quyết định Duy |
| SR-20-AC4 (F5 không tự mở tab Trợ lý) | ✅ | Mock: tải lại trang không mở tab Trợ lý và không gọi `/api/ai/status` |
| SR-20-AC5 ("Tóm tắt" cần đồng ý) | ✅ | Mock: chưa đồng ý thì không có "Tóm tắt"; đồng ý rồi thì có. Ghi nhận L6-2 |
| M5-1b (mock không lọt build thật) | ✅ | `check-no-mock.mjs`: XANH build thật (erp 13 file mock/32 chuỗi/134 file; shop 4/27/43); ĐỎ build mock. grep canary (`DH-DEMO00x`, "Vựa Thử Nghiệm", SĐT giả) trong `out/` rỗng. Đóng B1 lượt trước |
| B2 (`recallOrderContact` chỉ nhận 4 chữ số) | ✅ | Script Shop ca đối kháng: storage bị sửa thành SĐT đầy đủ hoặc không đủ 4 số -> không hiện, không đưa vào URL/ô nhập |
| F6-1 ("Nhờ" ở mọi màn) | ✅ | Mock + mạng thật (nv_kho, lô Nháp, desktop và 360px): thấy "Nhờ", không cuộn ngang, 1 POST escalate, AuditLog `escalate_inventory.batch.publish` được ghi (`changes` rỗng, `note` chỉ có nhãn bước + mã lô + nhóm, không có tiền/kg/PII) |
| F6-2 ("Để AI làm" theo `step.ai`) | ✅ | Mock: bấm thì đúng 1 POST `/api/ai/commands/sales.refund.create/call/`, thông báo "AI đã soạn nháp", không gọi `/status` |
| SR-21 ERP (CS-11-AC6 tem PDF, X-AC4 storage) | ✅ | 5/5 và 32/32 (đóng ⏸). QR tem không chứa SĐT; console/storage không có tên/địa chỉ |
| SR-21 Shop (GL-01..GL-04) | ✅ | 279/279 trên build thật sau M5-1b; A2 46/46 |

### Ngoại lệ và biên
- Bấm đúp "Nhờ": đúng 1 POST (cả desktop và 360px, mạng thật). Nhờ ở 2 phiên riêng tạo 2 bản ghi `ESCALATED` (L6-3).
- Thao tác trên màn cũ: đơn #1 đã lên chính sách v2 vẫn mở đúng v1. Version không tồn tại trả 404 rõ ràng.
- Đăng nhập hạn chế tần suất: lần login thứ 2 liên tiếp trong vài giây bị 429 (đúng thiết kế, không phải lỗi).
- Cờ AI bật/tắt, `step.ai` null/C, đồng ý model có/chưa: đủ 4 tổ hợp ở mock.
- Bản mock có `beforeunload` khi đang soạn dở: chỉ INFO.

### Phân quyền (Group x hành động)
| Hành động | chu | quan_ly | cskh | nv_kho | nv_giao | chưa đăng nhập |
|---|---|---|---|---|---|---|
| Xem phiên bản chính sách (`/versions/N/`) | 200 | 200 | ⏸ (chưa seed cskh ở backend thật) | 403 | 403 | 401 |
| Tạo/sửa bài kèm ảnh (SR-18) | 201/200 | 201/200 | 201/200 | 403 | 403 | 401 |
| Nút "Nhờ" ở màn nghiệp vụ (nhóm có màn) | thấy | thấy | n/a | thấy (bước chưa được phép) | thấy | n/a |
Ghi chú: ô ⏸ do DB thật của QA không seed người dùng cskh; phía SR-18 cskh đã chạy ở test BE (bộ 34). Không chấm ✅ cho ô này.

### Rò giá vốn
- AuditLog `escalate_*`: `changes` = `{}`, `note` = "Chuyển việc <nhãn> (batch #2) cho nhóm quan_ly". Không có tiền, không có kg, không tính ngược được giá vốn.
- `ai_aiaction.args` = `{doc_type, doc_id, step_key, label}`, không có số tiền.
- Panel phiên bản và JSON `/versions/N/`: chỉ nội dung chính sách + người đăng + giờ, không có field giá.

### Rò dữ liệu cá nhân
- Mạng thật: storage (`cave_erp_token`, `cave_erp_last_user`), URL, mọi request URL, console: không có tên/SĐT/địa chỉ khách (chỉ dữ liệu giả).
- Shop 279 ca: quét localStorage/sessionStorage/cookie/URL/console/mọi request ở cả đường lỗi: sạch. Chỉ gọi origin + API + cổng thanh toán.
- Không có URL/mã đơn nào mang SĐT; `phone_last4` chỉ 4 số cuối và được B2 kiểm tra.
- Ảnh và log dùng dữ liệu giả 100%.

### Chứng từ bất biến và AuditLog
Không thao tác xoá chứng từ nào trong Lô 6. Hành động escalate (Tầng 2) đều ghi AuditLog (2 bản ghi tương ứng 2 lần bấm ở 2 viewport).

### Hồi quy
Backend 1523 OK; `makemigrations --check` sạch; vitest 103/103; erp và shop `tsc --noEmit` exit 0; `npm ci` không `--legacy-peer-deps`, không ERESOLVE; `npm run build` OK cả hai; Shop A2 46/46; ERP CS-11 5/5, X-AC4 32/32.

### Lỗi
Không có lỗi chặn. Ghi nhận không chặn:
- **L6-2 (Low, theo thiết kế):** "Tóm tắt" chỉ hiện sau khi người dùng đã mở tab Trợ lý (gate-state fail-closed) — đúng quyết định Duy 30/09 nhưng nên ghi vào hướng dẫn.
- **L6-3 (Low, backlog):** hai phiên riêng (desktop rồi mobile) cùng nhờ một lô/bước tạo 2 bản ghi `ESCALATED` (chưa khử trùng lặp ở server). Bấm đúp trong 1 phiên thì chỉ 1 POST.
- **L6-4 (Low, đã sửa trong test):** fixture `ra-soat-a2-golive.py` mã cứng `booked_expires_at=2026-09-30T12:30:00Z`; quá 12:30Z ngày 30/09 thì đơn "hết hạn giữ chỗ" nên ca GL-04-AC1 đỏ giả. Không phải lỗi sản phẩm (đã chứng minh: đổi fixture sang `2099-01-01` thì 46/46). Đã sửa trong `frontend/e2e/ra-soat-a2-golive.py`.
- **L6-5 (INFO):** ở E2E mạng thật, ca "console không lỗi (Chủ)" đỏ giả vì Chrome ghi "Failed to load resource: 404" cho chính lệnh `version=99` mà ca đó cố ý gọi (404 kỳ vọng).

### Lệnh đã chạy (tóm tắt output)
```
cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test   -> Ran 1523 tests OK
manage.py makemigrations --check --dry-run                                          -> No changes detected
manage.py test repro_mod.qa_repro_a5 repro_mod.qa_lo6_sr18 apps.content...sr18* ... -> Ran 34 tests OK
cd erp-console && npm ci && npx tsc --noEmit (0) && npm test (103 passed) && npm run build (OK)
node scripts/check-ai-chunks.mjs   -> XANH (đỏ trên build HEAD)   | node scripts/check-no-mock.mjs -> XANH (đỏ trên build mock)
python3 erp-console/e2e/p8_lo6_fe_sr19_sr20.py -> 74/74 ; ra_soat_cs11_ac6_label_pdf.py 5/5 ; ra_soat_x_ac4_storage.py 32/32
Django thật 8116 (sqlite giả) + build thật 3218 -> qa_lo6_real.py + qa_lo6_real_f61.py : 52 PASS (+1 đỏ giả L6-5)
cd frontend && npm ci && npx tsc --noEmit (0) && npm run build (OK, base local) ; check-no-mock XANH ; build mock -> ĐỎ (36)
python3 frontend/e2e/qa-lo6-sr21-shop.py -> 279 ca, 0 FAIL ; ra-soat-a2-golive.py -> 46/46 (sau sửa fixture)
Build cuối (NEXT_PUBLIC_USE_MOCK=0, API_BASE=https://cangca-api-...run.app) cả 2 FE -> OK; check-no-mock XANH; check-ai-chunks XANH; không còn chuỗi localhost trong out/
```
Ảnh: `doc/features/2026-09-30-sua-loi-review/qa-lo6/` (`real-sr19-*.png`, `real-sr20-*.png`, `real-f61-*.png`, ...), toàn bộ dữ liệu giả.
