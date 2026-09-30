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
