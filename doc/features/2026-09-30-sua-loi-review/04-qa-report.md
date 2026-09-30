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
