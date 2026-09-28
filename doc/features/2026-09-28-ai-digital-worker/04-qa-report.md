# Báo cáo QA — AI của tôi: nhân viên số, lệnh tự sinh từ API, hướng dẫn theo chứng từ

## Lô 0: DW-01 spike BE, DW-02 spike FE (Số Mac) · Lần 1 · 2026-09-28
- Kết luận: ĐẠT (DW-01 dispatch 100%, 0 query rò, schema nhap_lo 138 token <= 450; DW-02 Recall@5 = 98.0% >= 95%, margin = 0.217).
- Báo cáo chi tiết: `research/02-spike-be.md`, `research/03-spike-fe.md`.

---

## Lô 1a: DW-03 — Khung Tiếp theo · Đã làm trên màn Đơn hàng (+ L-4) · Lần 1 · 2026-09-28

### Kết luận: APPROVED — Khung Tiếp theo · Đã làm trên Đơn hàng đạt 100% AC, bảo đảm bất biến giá vốn, PII và phân quyền

### Tổng: 16 ca · ✅ 16 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/lệnh) |
|---|---|---|
| **DW-03-AC1** | ✅ PASS | `test_dw03_ac1_booked_order_next_steps` (auto_cancel actor=system, confirm_payment allowed=false cho QL, allowed=true cho Chủ) |
| **DW-03-AC2** | ✅ PASS | `test_dw03_ac2_available_actions_match_and_callable` (khớp ma trận 4 Group × BOOKED/PAID/CANCELLED; thao tác thật không 400) |
| **DW-03-AC3** | ✅ PASS | `test_dw03_ac3_timeline_merged_related` (gộp đủ order/invoice/delivery/refund có `doc`, `related` đủ mã, `at` tăng dần) |
| **DW-03-AC4** | ✅ PASS | `test_dw03_ac4_ai_actor_timeline_l4` (L-4: hiện "AI của Chủ", level=C, không hiện "Hệ thống", ẩn `config_version`) |
| **DW-03-AC5** | ✅ PASS | `test_dw03_ac5_no_pii_for_chu` (Bất biến 9: token Chủ không thấy name/phone/address/nội dung CK, không `changes` thô) |
| **DW-03-AC6** | ✅ PASS | `test_dw03_ac6_no_cost_leak` (Bất biến 1: QL & Kho không thấy khoá giá vốn ở bất kỳ tầng nào) |
| **DW-03-AC7** | ✅ PASS | `test_dw03_ac7_permissions` (Thiếu quyền -> 403; ngoài scope NV giao -> 404; anonymous -> 401) |
| **DW-03-AC8** | ✅ PASS | `ConfirmPaymentForm.tsx`, `CancelOrderForm.tsx` (bắt 400, format mã BR, gọi `onError400`), `OrderDetailSheet.tsx` (`guidanceRefreshKey`) |
| **DW-03-AC9** | ✅ PASS | `test_dw03_ac9_ai_disabled` (`AI_ENABLED=False` -> endpoint trả 200, trường `ai=null`) |
| **DW-03-AC10** | ✅ PASS | `test_dw03_ac10_reasons_no_money_amount` (Quét `reasons.py`: không câu nào chứa số tiền) |
| **DW-03-AC11** | ✅ PASS | `GuidancePanel.tsx` (Cô lập lỗi mạng/500, có nút Thử lại, có trạng thái tải và rỗng) |

### Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Biên & Ngoại lệ:** Đơn BOOKED hết hạn TTL có deadline rõ ràng; thao tác bị 400 kích hoạt tải lại guidance đúng 1 lần; guidance lỗi không sập màn hình đơn.
- **Phân quyền (Group × Hành động):**
  - `chu`: Xem đủ guidance, `confirm_payment` allowed=true, xem được `doc`/`timeline`.
  - `quan_ly`: Xem được guidance, `confirm_payment` allowed=false kèm lý do BR-TT-07, `cancel` allowed=true trên đơn PAID chưa giao.
  - `nv_kho`: Xem được guidance đơn trong phạm vi, không thấy nút ngoài thẩm quyền.
  - `nv_giao`: Chỉ xem được đơn gắn với phiếu giao của mình (scope T3), đơn khác trả 404 (giống hệt API chi tiết đơn).
  - Chưa đăng nhập: 401 Unauthorized.
- **Rò giá vốn (Bất biến 1):** Không rò `unit_cost`, `landed_unit_cost`, `rate`, `profit` cho token thiếu `view_costprice`.
- **Rò dữ liệu cá nhân (Bất biến 9):** Guidance endpoint và timeline không chứa tên, SĐT, địa chỉ, nội dung CK giả định của khách.
- **Hồi quy:** Các test suite cũ `test_s10_api.py`, `test_s14_cancel_paid_order.py` xanh 100%.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy
- `cd backend && .venv/bin/python manage.py test apps.sales.orders.tests.test_guidance` -> `Ran 9 tests in 1.482s. OK`
- `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 732 tests in 89.356s. OK. No changes detected.`
- `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch, First Load JS shared giữ nguyên 87.6 kB, route `/orders` 128 kB.
- `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch.

---

## Lô 1b: DW-04 (Phiếu hoàn + Giao dịch lệch) & DW-05 (Lô hàng) · Lần 1 · 2026-09-28

### Kết luận: APPROVED — Lô 1b hoàn thành toàn diện DW-04 và DW-05, bảo vệ nghiêm ngặt Bất biến 1 (Giá vốn) và Bất biến 9 (PII), test_l1_close_batch.py xanh nguyên vẹn

### Tổng: 20 ca · ✅ 20 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/lệnh) |
|---|---|---|
| **DW-04-AC1** | ✅ PASS | `apps.sales.refunds.tests.test_guidance::GuidanceRefundTest.test_dw04_ac1_pending_refund_next_steps_for_manager` (QL: confirm allowed=false, who=Chủ, missing BR-HT-03; Chủ: allowed=true) |
| **DW-04-AC2** | ✅ PASS | `apps.sales.refunds.tests.test_guidance::GuidanceRefundTest.test_dw04_ac2_refund_near_deadline_warning` (cảnh báo GW-02 khi >= 25 ngày) |
| **DW-04-AC3** | ✅ PASS | `apps.sales.refunds.tests.test_guidance::GuidanceRefundTest.test_dw04_ac3_available_actions_and_live_execution`<br>`apps.sales.payments.tests.test_guidance::GuidancePaymentTest.test_dw04_ac3_available_actions_and_live_execution` (khớp available_actions cũ = mới, gọi thật không 400) |
| **DW-04-AC4 (PII)** | ✅ PASS | `apps.sales.payments.tests.test_guidance::GuidancePaymentTest.test_dw04_ac4_no_pii_leak_in_payment_guidance_for_chu` (không rò raw_payload, description, counter_account_name) |
| **DW-04-AC5** | ✅ PASS | `apps.sales.refunds.tests.test_guidance::GuidanceRefundTest.test_dw04_ac5_permissions`<br>`apps.sales.payments.tests.test_guidance::GuidancePaymentTest.test_dw04_ac5_permissions` (nv_kho, nv_giao nhận 403, không lộ bước) |
| **DW-04-AC6** | ✅ PASS | `apps.sales.refunds.tests.test_guidance::GuidanceRefundTest.test_dw04_ac6_stale_action_returns_400_with_br_code` (phiếu đã xác nhận -> thao tác cũ nhận 400 BR-HT-09) |
| **DW-04-AC7** | ✅ PASS | `apps.sales.refunds.tests.test_guidance::GuidanceRefundTest.test_dw04_ac7_guidance_works_when_ai_disabled`<br>`apps.sales.payments.tests.test_guidance::GuidancePaymentTest.test_dw04_ac7_guidance_works_when_ai_disabled` (AI_ENABLED=False -> 200, ai=null) |
| **DW-05-AC1** | ✅ PASS | `apps.inventory.batches.tests.test_guidance::GuidanceBatchTest.test_dw05_ac1_selling_near_expiry_next_steps_for_nv_kho` (lô SELLING còn 10 ngày -> có auto_near_expiry, publish/close allowed=false) |
| **DW-05-AC2** | ✅ PASS | `apps.inventory.batches.tests.test_guidance::GuidanceBatchTest.test_dw05_ac2_close_blocked_when_open_orders_exist` (còn đơn mở -> close allowed=false missing BR-LO-04, gọi API nhận 400 BR-LO-04) |
| **DW-05-AC3 (giá vốn)** | ✅ PASS | `apps.inventory.batches.tests.test_guidance::GuidanceBatchTest.test_dw05_ac3_cost_hidden_in_timeline_for_non_chu` (QL & Kho thấy "Chủ đã chốt lô", "Chủ ghi nhận chi phí mua" không số; Chủ thấy số) |
| **DW-05-AC4 (giá vốn)** | ✅ PASS | `apps.inventory.batches.tests.test_guidance::GuidanceBatchTest.test_dw05_ac4_purchase_cost_warning_has_no_money_numbers` (cảnh báo không chứa số tiền, Chủ và Kho thấy cùng câu) |
| **DW-05-AC5** | ✅ PASS | `apps.inventory.batches.tests.test_guidance::GuidanceBatchTest.test_dw05_ac5_nv_giao_gets_403` (nv_giao nhận 403) |
| **DW-05-AC6 (PII)** | ✅ PASS | `apps.inventory.batches.tests.test_guidance::GuidanceBatchTest.test_dw05_ac6_no_pii_in_stock_ledger_entries` (dòng sổ kho không chứa tên/SĐT/địa chỉ khách) |
| **DW-05-AC7** | ✅ PASS | `apps.inventory.batches.tests.test_guidance::GuidanceBatchTest.test_dw05_ac7_guidance_works_when_ai_disabled` (AI_ENABLED=False -> 200, ai=null) |
| **FE-DW-04** | ✅ PASS | `RefundView.tsx`, `PaymentView.tsx` (tích hợp GuidancePanel) |
| **FE-DW-05** | ✅ PASS | `BatchDetailSheet.tsx`, `InventoryScreen.tsx` (mở sheet chi tiết và tích hợp GuidancePanel) |
| **FE-MOCK** | ✅ PASS | `erp-console/features/guidance/mock.ts` (mock đủ 4 loại chứng từ) |
| **FE-ISOLATION** | ✅ PASS | `GuidancePanel.tsx` (cô lập lỗi mạng/500, có nút Thử lại) |
| **L1-REGRESSION** | ✅ PASS | `apps.inventory.batches.tests.test_l1_close_batch` (20/20 tests xanh sau khi tách check_close_batch) |
| **NO-LEAK-GREP** | ✅ PASS | Code sản phẩm không rò rỉ dữ liệu cá nhân hay giá vốn |

### Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Biên & Ngoại lệ:** Cảnh báo 25 ngày cho phiếu hoàn PENDING; deadline chuyển cận hạn cho lô; chặn chốt lô khi còn đơn mở BOOKED/PAID/PROCESSING.
- **Phân quyền:** Token `chu`, `quan_ly`, `nv_kho`, `nv_giao` được phân định rõ ràng trên từng loại chứng từ; người thiếu quyền nhận HTTP 403 không rò dữ liệu.
- **Rò giá vốn (Bất biến 1):** Đã kiểm tra lọc giá vốn theo quyền `view_costprice` trong timeline lô và cảnh báo; FE ẩn cột giá vốn khi user thiếu quyền.
- **Rò dữ liệu cá nhân (Bất biến 9):** Loại bỏ hoàn toàn `raw_payload`, nội dung CK, tên người chuyển khỏi guidance thanh toán; timeline lô không đưa thông tin khách từ sổ kho.
- **Hồi quy:** `test_l1_close_batch.py` xanh 100% không đổi. Tổng test backend đạt 749 tests xanh.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy
- `cd backend && .venv/bin/python manage.py test apps.sales.refunds.tests.test_guidance apps.sales.payments.tests.test_guidance apps.inventory.batches.tests.test_guidance apps.inventory.batches.tests.test_l1_close_batch` -> `Ran 46 tests in 1.424s. OK`
- `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 749 tests in 36.370s. OK. No changes detected.`
- `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch, First Load JS shared 87.6 kB, 22/22 static pages.
- `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch, 8/8 static pages.

---

## Lô 1c: DW-06 (Chủ huỷ lô quá hạn EXPIRED -> CANCELLED, hạch toán lỗ) · Lần 1 · 2026-09-28

### Kết luận: APPROVED — Nghiệm thu toàn diện Story DW-06: huỷ lô quá hạn đúng nghiệp vụ P-04 (EXPIRED -> CANCELLED), ghi sổ kho xuất huỷ append-only, hạch toán lỗ PnL chuẩn TL-4, chống race condition bằng select_for_update, bảo đảm tuyệt đối Bất biến 1 (giá vốn), Bất biến 9 (PII) và phân quyền 3 tầng.

### Tổng: 14 ca · ✅ 14 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/lệnh) |
|---|---|---|
| **DW-06-AC1** | ✅ PASS | `apps.inventory.batches.tests.test_cancel_expired::CancelExpiredBatchTest.test_dw06_ac1_cancel_expired_success` (lô CANCELLED, 1 dòng WRITE_OFF âm 5 kg, 1 dòng AuditLog, PnL expired_cost = 5 * landed_unit_cost, profit và total_cost không đổi theo TL-4) |
| **DW-06-AC2 (lỗi)** | ✅ PASS | `apps.inventory.batches.tests.test_cancel_expired::CancelExpiredBatchTest.test_dw06_ac2_cancel_non_expired_rejected_br_lo_03` (lô SELLING, NEAR_EXPIRY, DRAFT nhận 400 BR-LO-03 "Chỉ huỷ được lô Quá hạn.", dữ liệu không đổi) |
| **DW-06-AC3 (song song / khoá)** | ✅ PASS | `apps.inventory.batches.tests.test_cancel_expired::CancelExpiredBatchTest.test_dw06_ac3_repeat_cancel_rejected` (atomic + select_for_update, request 2 nhận 400 BR-LO-03, sổ kho chỉ có đúng 1 dòng WRITE_OFF) |
| **DW-06-AC4 (quyền)** | ✅ PASS | `apps.inventory.batches.tests.test_cancel_expired::CancelExpiredBatchTest.test_dw06_ac4_permissions_matrix` (quan_ly, nv_kho, nv_giao nhận 403; khách nhận 401; FE ẩn nút Huỷ lô) |
| **DW-06-AC5 (giá vốn)** | ✅ PASS | `apps.inventory.batches.tests.test_cancel_expired::CancelExpiredBatchTest.test_dw06_ac5_cost_hidden_in_timeline_for_quan_ly` (quan_ly xem timeline thấy "Chủ đã huỷ lô" không số tiền lỗ; Chủ thấy số tiền) |
| **DW-06-AC6 (guidance)** | ✅ PASS | `apps.inventory.batches.tests.test_cancel_expired::CancelExpiredBatchTest.test_dw06_ac6_guidance_next_steps_expired_then_cancelled` (lô EXPIRED có bước Huỷ lô allowed=true, không hiện Chốt lô; sau khi huỷ chuyển sang CANCELLED thì bước kế là Chốt lô) |
| **DW-06-AC7 (AI tắt)** | ✅ PASS | `apps.inventory.batches.tests.test_cancel_expired::CancelExpiredBatchTest.test_dw06_ac7_cancel_expired_when_ai_disabled` (AI_ENABLED=False -> huỷ lô chạy bình thường, BR-AI-10) |
| **MIGRATION-TEST** | ✅ PASS | `apps.inventory.batches.tests.test_cancel_expired::CancelExpiredBatchTest.test_migration_permissions_group_chu_only` (quyền inventory.cancel_expired_batch chỉ gán cho Group chu, 3 Group còn lại không có, rollback sạch) |
| **FE-ACTION-BTN** | ✅ PASS | `erp-console/features/inventory/components/BatchDetailSheet.tsx` (nút Huỷ lô ở header chỉ hiện khi canCancelExpired=true) |
| **FE-CONFIRM-MODAL** | ✅ PASS | `erp-console/features/inventory/components/BatchDetailSheet.tsx` (modal xác nhận nêu rõ mã lô + số kg tồn xuất huỷ, tuyệt đối không nêu số tiền giá vốn, có cờ cancelling chặn đúp click) |
| **FE-API-MOCK** | ✅ PASS | `erp-console/features/inventory/api.ts` (cancelExpiredBatch gọi đúng API contract, mock trả về HTTP 200 CANCELLED) |
| **REPORT-PNL-16KEYS** | ✅ PASS | `apps.reports.tests.test_api.py::BatchPnlApiTests.test_chu_can_view_batch_pnl` (bổ sung expired_qty, expired_cost đủ 16 khoá, giữ vững công thức lãi lỗ TL-4) |
| **L1-CLOSE-REGRESSION** | ✅ PASS | `apps.inventory.batches.tests.test_l1_close_batch` (20/20 tests xanh) |
| **GUIDANCE-REGRESSION** | ✅ PASS | `apps.inventory.batches.tests.test_guidance` (7/7 tests xanh) |

### Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Biên & Ngoại lệ:** Lô EXPIRED còn 5 kg xuất huỷ đúng 5 kg; lô tồn 0 vẫn huỷ và chuyển trạng thái bình thường; `select_for_update` loại bỏ race condition khi 2 request gọi cùng lúc.
- **Phân quyền:** Chỉ duy nhất Group `chu` sở hữu quyền `inventory.cancel_expired_batch`. Mọi Group khác (`quan_ly`, `nv_kho`, `nv_giao`) nhận 403 Forbidden và FE ẩn nút hành động.
- **Rò giá vốn (Bất biến 1):** `BatchSerializer` lọc bỏ `purchase_rate`/`landed_unit_cost` cho ai không có `view_costprice`. Dòng thời gian hiển thị "Chủ đã huỷ lô" không có số tiền lỗ với Quản lý và Kho. Modal xác nhận FE chỉ chứa số kg, không có số tiền.
- **Rò dữ liệu cá nhân (Bất biến 9):** Nghiệp vụ không đụng chạm đến PII khách hàng. Test sử dụng fixture giả định.
- **Hồi quy:** `test_l1_close_batch.py` xanh 20/20 tests. Tổng số test backend đạt **757 tests xanh**. `makemigrations --check --dry-run` sạch. Build console và frontend sạch.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy
- `cd backend && .venv/bin/python manage.py test apps.inventory.batches.tests.test_cancel_expired apps.inventory.batches.tests.test_guidance apps.inventory.batches.tests.test_l1_close_batch apps.reports.tests` -> `Ran 45 tests in 2.158s. OK`
- `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 757 tests in 36.568s. OK. No changes detected.`
- `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch, First Load JS shared 87.6 kB, 22/22 static pages.
- `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch, 8/8 static pages.

---

## Lô 2: Tự đăng ký lệnh + chỉ mục + chọn lệnh 2 bước (DW-07, DW-08, DW-09) · Lần 1 · 2026-09-29

### Kết luận: APPROVED — Lô 2 hoàn thành xuất sắc 100% tiêu chí: registry tự sinh an toàn mặc định, cưỡng chế quyền Tầng 2 trước thân action, FE chọn lệnh 2 bước kiểm soát ngân sách token nghiêm ngặt, bảo vệ tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (PII).

### Tổng: 25 ca · ✅ 25 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/lệnh) |
|---|---|---|
| **DW-07-AC1** | ✅ PASS | `apps.ai.registry.tests.test_discovery::CommandDiscoveryTestCase.test_dw07_ac1_snapshot_khop_file` (94 lệnh khớp hoàn toàn file snapshot `commands_index_snapshot.json`, ID chuẩn `<app>.<model/view>.<action>`, group thuộc thu_mua/ban_hang/cskh, kind read/write) |
| **DW-07-AC2** | ✅ PASS | `apps.ai.registry.tests.test_default_safety::DefaultSafetyTestCase.test_dw07_ac2_feature_moi_khong_khai_gi_an_toan_mac_dinh` (ViewSet thử không khai gì: chỉ Group có `view_*` thấy, sensitivity=cao, channel=local; đọc=A, ghi=C max_level=C; action đọc tay `form_only=true`; quyền đỏ -> red_zone=True; quyền lạ -> trần C ép; không rò giá vốn & PII) |
| **DW-07-AC3** | ✅ PASS | `apps.ai.registry.tests.test_discovery::CommandDiscoveryTestCase.test_dw07_ac3_hard_blocklist`<br>`apps.ai.registry.tests.test_discovery::CommandDiscoveryTestCase.test_dw07_ac3_red_zone_dung_bang_3_quyen` (Chặn 9 prefix cấm gồm `/api/ai/`, suffix tem in, method DELETE/PUT, upload ảnh, quyền `auth.*` và quyền cấm T2, cấm ghi SalesOrder/SalesInvoice, cấm resource customer; tập red_zone=True đúng bằng 6 action có 3 quyền đỏ) |
| **DW-07-AC4** | ✅ PASS | `apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase.test_dw07_ac4_group_matrix` (nv_giao không có purchasing.*, batch.close, reports.*; quan_ly/nv_kho/nv_giao không có báo cáo lãi lỗ; lệnh ngoài quyền -> descriptor trả 404 COMMAND_UNKNOWN giống hệt lệnh không tồn tại) |
| **DW-07-AC5 (giá vốn)** | ✅ PASS | `apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase.test_dw07_ac5_cost_keys_scrubbing_by_role` (quan_ly, nv_kho gọi descriptor `inventory.batch.list` -> `output_fields` không có `purchase_rate`, `landed_unit_cost`; chu có) |
| **DW-07-AC6 (PII)** | ✅ PASS | `apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase.test_dw07_ac6_no_pii_keys_in_output_fields` (Quét descriptor 94 lệnh trên token chu -> 100% không có khoá PII nào trong `output_fields`; không có lệnh trên resource customer) |
| **DW-07-AC7 (ngân sách)** | ✅ PASS | `apps.ai.registry.tests.test_discovery::CommandDiscoveryTestCase.test_dw07_ac7_schema_budget` (mô tả thuộc tính <= 80 ký tự; enum > 20 đổi thành string; schema_tokens_est > 450 tự bật `form_only=True`) |
| **DW-07-AC8 (hiệu năng)** | ✅ PASS | `apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase.test_dw07_ac8_index_no_business_queries` (gọi index chỉ query bảng auth_*/ai_*, không query bất kỳ bảng nghiệp vụ nào như batch, order, receipt; registry build 1 lần/process) |
| **DW-07-AC9 (AI tắt)** | ✅ PASS | `apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase.test_dw07_ac9_ai_disabled` (`AI_ENABLED=False` -> index & descriptor trả 410 AI_DISABLED; endpoint catalog cũ `/api/commands/catalog/` vẫn 200, 7 test `test_catalog.py` xanh 100%) |
| **DW-07-AC10 (lọc lô)** | ✅ PASS | `apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase.test_dw07_ac10_batch_filter_and_fefo` (`BatchViewSet` có `list_query_serializer=BatchListQuery`, lọc `item_code=CA-001` chỉ trả lô của mặt hàng đó và giữ đúng thứ tự FEFO) |
| **DW-08-AC1** | ✅ PASS | `apps.ai.registry.tests.test_discipline::DisciplineTestCase.test_dw08_ac1_moi_custom_action_co_required_perms` (Đúng 18 custom @action hiện có trên 9 ViewSet đều khai báo `required_perms`) |
| **DW-08-AC2** | ✅ PASS | `apps.ai.registry.tests.test_discipline::DisciplineTestCase.test_dw08_ac2_required_perms_khop_require_perm` (AST kiểm tra thân action: các quyền gọi `require_perm` trong thân là tập con của `required_perms` đã khai) |
| **DW-08-AC3 (không đổi hành vi)** | ✅ PASS | `apps.ai.registry.tests.test_discipline::DisciplineTestCase.test_dw08_ac3_403_cung_than_khi_thieu_quyen` (`BusinessModelPermissions` cưỡng chế trước thân action, user thiếu quyền nhận 403 cùng thân `Thiếu quyền: <perm>`; toàn bộ suite test cũ giữ nguyên hành vi) |
| **DW-08-AC4** | ✅ PASS | `apps.ai.registry.tests.test_discipline::DisciplineTestCase.test_dw08_ac4_action_ghi_co_docstring_tieng_viet` (Mọi action ghi đều có docstring tiếng Việt rõ ràng >= 5 ký tự) |
| **DW-08-AC5 (lỗi)** | ✅ PASS | `apps.ai.registry.tests.test_discipline::DisciplineTestCase.test_dw08_ac5_form_only_bao_cao` (Action mới đọc request.data tay bị bắt thành `form_only`; in báo cáo nợ 14 action đọc tay đã biết) |
| **DW-08-AC6** | ✅ PASS | `apps.ai.registry.tests.test_discipline::DisciplineTestCase.test_dw08_ac6_test_id_lenh_on_dinh` (ID lệnh ổn định theo snapshot, registry đủ 94 lệnh) |
| **DW-08-AC7 (AI tắt)** | ✅ PASS | `apps.ai.registry.tests.test_discipline::DisciplineTestCase.test_dw08_ac7_cuong_che_quyen_khi_ai_tat` (`AI_ENABLED=False` -> `BusinessModelPermissions` vẫn cưỡng chế quyền Tầng 2 trả 403 trên UI) |
| **DW-09-AC1** | ✅ PASS | `erp-console/features/ai/commands/commands.test.ts::DW-09-AC1` (Màn tồn kho hỏi "còn bao nhiêu cá thu" -> <= 3 ứng viên, top-1 `inventory.batch.list`; top-1 vượt top-2 quá margin 0.2 -> skipTurnA=true) |
| **DW-09-AC2 (ngân sách)** | ✅ PASS | `erp-console/features/ai/commands/commands.test.ts::DW-09-AC2` (150 lệnh giả × 50 câu mẫu ở n_ctx 2048 & 4096: mọi prompt <= 80% n_ctx; Lượt A <= 5 tên; Lượt B <= 1 schema ở 2048, <= 2 ở 4096; không lọt ID ngoài top-K) |
| **DW-09-AC3** | ✅ PASS | `erp-console/features/ai/commands/commands.test.ts::DW-09-AC3` (Lệnh `form_only=true` hoặc schema > 450 token -> chuyển form điền sẵn, trích xuất tất định kg, item_code, batch_id; không chạy Lượt B) |
| **DW-09-AC4 (lỗi)** | ✅ PASS | `erp-console/features/ai/commands/commands.test.ts::DW-09-AC4` (Không đạt điểm BM25 tối thiểu -> hỏi lại lần 1, 2; lần 3 gợi ý 4 câu mẫu SAMPLE_SUGGESTIONS; 0 lần gọi model) |
| **DW-09-AC5 (không crash)** | ✅ PASS | `erp-console/features/ai/commands/commands.test.ts::DW-09-AC5` (Kết quả đọc mock 500 dòng -> Lượt C chỉ đưa 20 dòng vào prompt, hiện thông báo "còn 480 dòng — xem màn danh sách", không crash tab) |
| **DW-09-AC6 (quyền)** | ✅ PASS | `erp-console/features/ai/commands/commands.test.ts::DW-09-AC6` (Chỉ mục giữ trong RAM JS; `index_version` đổi -> tự động làm mới và xoá descriptor cache; FE không tự thêm lệnh ngoài chỉ mục) |
| **DW-09-AC7 (PII)** | ✅ PASS | `erp-console/features/ai/commands/commands.test.ts::DW-09-AC7` (Không ghi câu hỏi, prompt hay kết quả vào console hay localStorage/URL; chỉ mục lưu trong RAM) |
| **DW-09-AC8 (AI tắt)** | ✅ PASS | `erp-console/features/ai/commands/commands.test.ts::DW-09-AC8` (Index trả 410 -> ném lỗi `AI_DISABLED`, không gây lỗi chunk AI, các màn nghiệp vụ độc lập) |

### Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Ngoại lệ & biên:**
  - ViewSet mới không khai báo bất kỳ metadata AI nào vẫn được cách ly an toàn mặc định (sensitivity=cao, channel=local, mức C, form_only nếu đọc request.data tay, lọc bỏ giá vốn & PII).
  - Lệnh có schema vượt trần 450 token hoặc enum > 20 giá trị tự động thu gọn/chuyển `form_only` tránh tràn ngữ cảnh.
  - Tìm kiếm câu hỏi quá 120 token hoặc không đạt điểm tối thiểu được từ chối an toàn mà không gọi model.
  - Kết quả đọc 500 dòng được cắt gọn an toàn ở 20 dòng.
- **Phân quyền (Bảng vai × Hành động):**
  - `chu`: Thấy đủ 94 lệnh (gồm báo cáo lãi lỗ `batch_pnl`, `period_pnl`, các action chốt lô, xác nhận thanh toán/hoàn tiền), thấy giá vốn trong descriptor `inventory.batch.list`.
  - `quan_ly`: Thấy các lệnh quản lý, không thấy báo cáo lãi lỗ; không thấy trường giá vốn trong descriptor `inventory.batch.list`.
  - `nv_kho`: Thấy các lệnh kho/lô, không thấy lệnh mua hàng/báo cáo/chốt lô; không thấy trường giá vốn.
  - `nv_giao`: Chỉ thấy các lệnh giao hàng/phiếu giao trong phạm vi; không thấy `purchasing.*`, `inventory.batch.close`, `reports.*`.
  - Lệnh ngoài quyền: Descriptor trả HTTP 404 `COMMAND_UNKNOWN` cùng cấu trúc với lệnh không tồn tại, ngăn chặn hoàn toàn việc dò quét endpoint.
  - UI: `BusinessModelPermissions` cưỡng chế `required_perms` trước khi vào thân action, trả 403 `Thiếu quyền: <perm>`.
- **Rò giá vốn (Bất biến 1):**
  - Kiểm tra `GET /api/ai/commands/inventory.batch.list/`: `quan_ly` và `nv_kho` hoàn toàn không có `purchase_rate`, `landed_unit_cost` trong `output_fields`.
  - Lệnh kiểm tra `grep -rn 'fields = "__all__"' backend/apps` trả về **rỗng**.
- **Rò dữ liệu cá nhân (Bất biến 9):**
  - Quét 100% descriptor của 94 lệnh: Không có trường nào thuộc 11 khoá PII (`phone`, `customer_name`, `delivery_address`, `raw_payload`, `content`, `counter_account_name`...) xuất hiện trong `output_fields`.
  - Hoàn toàn không có resource hay lệnh nào liên quan tới `customer`.
  - Không lệnh ghi nào thao tác trực tiếp lên `SalesOrder` và `SalesInvoice`.
  - FE: Quét `grep -rnE "console\.(log|info|debug)|localStorage" erp-console/features/guidance erp-console/features/ai/commands` trả về **rỗng**.
- **Hồi quy:**
  - Toàn bộ backend test suite: **775 tests xanh** (tăng 18 tests so với mốc 757 của Lô 1c).
  - 7 tests catalog cũ `apps/ai/commands/tests/test_catalog.py` xanh 100%.
  - `makemigrations --check --dry-run` sạch `No changes detected`.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy
1. `cd backend && .venv/bin/python manage.py test apps.ai.registry.tests` -> `Ran 18 tests in 0.812s. OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 775 tests in 38.120s. OK. No changes detected.`
3. `cd erp-console && npm test` -> `✓ features/ai/commands/commands.test.ts (8 tests) 8 passed (245ms)`
4. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 22/22 static pages, First Load JS shared by all giữ nguyên 87.6 kB.
5. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 8/8 static pages.
6. `grep -rn 'fields = "__all__"' backend/apps` -> Rỗng hoàn toàn.
7. `grep -rnE "console\.(log|info|debug)|localStorage" erp-console/features/guidance erp-console/features/ai/commands` -> Rỗng hoàn toàn.
8. `grep -rn "ai.manage_ai_policy\|/api/ai/" backend/apps/ai/policy/rules.py` -> 2 kết quả cấm tất định.

---

## Lô 3a: Mức C + AI của tôi + Việc AI (DW-10, DW-11) · Lần 1 · 2026-09-29

### Kết luận: APPROVED — Lô 3a hoàn thành 100% tiêu chí nghiệm thu: lệnh đọc mức A lọc giá vốn và PII triệt để 2 lớp, lệnh ghi mức C tự động tạo nháp đề xuất 15 phút, AuditLog ghi nhận đầy đủ actor_kind=ai và proposal_ref, bảo đảm cưỡng chế đếm ngược 3 giây (V5, BR-AI-14), kiểm kê không tự duyệt (H6, BR-KK-02), không rò giá vốn và PII.

### Tổng: 21 ca · ✅ 21 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/lệnh) |
|---|---|---|
| **DW-10-AC1** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac1_call_read_success` (nv_kho gọi `inventory.batch.list` -> 200 outcome=done, level=A, 5 dòng <= 20 dòng, total=5, truncated=False; 1 `AiAction(kind=read, status=DONE)`, không lưu kết quả vào DB tuân thủ BR-AI-09) |
| **DW-10-AC2 (giá vốn)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac2_cost_keys_scrubbed_for_unauthorized` (Mọi lệnh đọc × quan_ly/nv_kho/nv_giao trên fixture -> JSON response không có bất kỳ khoá giá vốn nào: `purchase_rate`, `landed_unit_cost`, `rate`, `unit_cost`, `profit`, `margin`, `cogs`, Bất biến 1, H3) |
| **DW-10-AC3 (PII)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac3_pii_scrubbed_even_for_chu` (Fixture đơn hàng/khách hàng có PII giả -> gọi mọi lệnh đọc với cả 5 Group gồm `chu`, `quan_ly`, `nv_kho`, `nv_giao`, `cskh` -> 100% chuỗi PII không xuất hiện trong response, AiAction, AuditLog, Bất biến 9, H2) |
| **DW-10-AC4 (chữ tự do)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac4_free_text_scrubbed_for_ai_read`<br>`apps.ai.execution.tests.test_scrub::ScrubTests.test_free_text_scrubbed_for_ai_read` (Các trường chữ tự do `note`, `reason`, `comment`... bị loại bỏ hoàn toàn khi AI đọc để chống indirect prompt injection H10; vẫn giữ nguyên trên UI) |
| **DW-10-AC5 (quyền/IDOR)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac5_permission_and_idor` (nv_giao gọi lệnh ngoài quyền hoặc lệnh không tồn tại -> 404 `COMMAND_UNKNOWN`; target ngoài scope T3 trả 404 y hệt UI; DB không đổi, H1, BR-PQ-12) |
| **DW-10-AC6 (lỗi)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac6_errors_args_and_cloud_channel` (args không phải dict -> 400 `BR-AI-01`; lệnh `channel=cloud` gọi qua endpoint local -> 400 `BR-AI-02`) |
| **DW-10-AC7 (idempotency)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac7_idempotency` (Cùng `idempotency_key` gửi lại cùng args -> trả cùng `action_id`; gửi khác args -> 409 `AI_IDEMPOTENCY_CONFLICT`) |
| **DW-10-AC8 (throttle)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac8_throttling` (Quá tần suất `AI_CALL_RATE` -> 429 `THROTTLED`) |
| **DW-10-AC9 (lỗi 5xx)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac9_view_5xx_returns_502` (View DRF nội bộ gặp 5xx -> pipeline trả 502 `AI_DISPATCH_FAILED`, tuyệt đối không lộ stack trace) |
| **DW-10-AC10 (contextvar)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac10_contextvar_reset_after_call` (Sau khi kết thúc lệnh AI, ngữ cảnh audit được reset sạch sẽ qua `finally`, request UI tiếp theo cùng thread ghi `actor_kind=user`, không bị dính `ai_*`, BR-AI-08) |
| **DW-10-AC11 (AI tắt)** | ✅ PASS | `apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac11_ai_disabled_returns_410` (`AI_ENABLED=False` -> gọi `call` trả 410 `AI_DISABLED`, BR-AI-10) |
| **DW-11-AC1** | ✅ PASS | `apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac1_call_write_creates_proposal_and_auditlog` (nv_kho gọi lệnh ghi `purchasing.purchasereceipt.submit` -> 200 outcome=proposal, level=C, expires_at=+15m; phiếu vẫn DRAFT; AuditLog `propose_...` ghi nhận `actor_kind=ai`, `ai_actor`=nv_kho, `ai_level=C`, BR-AI-06, BR-AI-08) |
| **DW-11-AC2** | ✅ PASS | `apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac2_confirm_success_after_3_seconds` (Mở xem chi tiết >= 3 giây, confirm kèm `confirm_nonce` -> phiếu SUBMITTED; AuditLog thực thi mang `actor_kind=user`, actor=người duyệt, `proposal_ref`=id đề xuất; `AiAction` CONFIRMED, BR-AI-08 Q6) |
| **DW-11-AC3 (lỗi duyệt)** | ✅ PASS | `apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac3_confirm_errors` (Chưa mở chi tiết hoặc mở < 3 giây -> 400 `BR-AI-14`; quá 15 phút -> 410 `AI_ACTION_EXPIRED`; duyệt lần 2 -> 409 `AI_ACTION_ALREADY_DECIDED`; phiếu không đổi) |
| **DW-11-AC4** | ✅ PASS | `apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac4_reject_action` (Nháp bất kỳ bấm reject -> `AiAction` REJECTED, chứng từ không đổi, AuditLog ghi 1 dòng `reject_...`) |
| **DW-11-AC5 (quyền duyệt)** | ✅ PASS | `apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac5_permission_denied_on_confirm` (nv_giao thiếu quyền duyệt phiếu nhập -> 403 `BR-AI-04`; `scope=all` chỉ người có `ai.manage_ai_policy` (Chủ) xem được, người khác 403, H1) |
| **DW-11-AC6 (kiểm kê H6)** | ✅ PASS | `apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac6_stocktake_h6_constraint` (Đề xuất kiểm kê do AI của A nhập -> A bấm duyệt bị từ chối 400 `BR-KK-02` ngay tại `actions/services.py` và service kiểm kê, BR-KK-02, H6) |
| **DW-11-AC7 (giá vốn nháp)** | ✅ PASS | `apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac7_args_preview_scrub_cost_keys` (Đề xuất có `rate` trong args -> nv_kho xem chi tiết thì `args_preview` không có `rate`; chu có `view_costprice` xem chi tiết thì thấy `rate`, Bất biến 1, BR-MH-06) |
| **DW-11-AC8 (PII target)** | ✅ PASS | `apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac8_target_only_type_and_code_no_pii` (Đề xuất trên đơn hàng -> trường `target` chỉ có type + code, hoàn toàn không có tên/SĐT/địa chỉ khách hàng và không có `object_repr`, Bất biến 9) |
| **DW-11-AC9 (AI tắt)** | ✅ PASS | `apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac9_ai_disabled_behavior` (`AI_ENABLED=False` -> confirm trả 410 `AI_DISABLED`; reject và GET xem chi tiết vẫn hoạt động bình thường, BR-AI-10) |
| **DW-11-AC10 (FE)** | ✅ PASS | `erp-console/features/ai/actions/components/ActionDetailModal.tsx`<br>`erp-console/app/(console)/ai/actions/page.tsx` (Màn "Việc AI" có 2 tab Chờ duyệt / Đã xử lý; modal chi tiết có đếm ngược 3 giây bắt buộc trên nút "Đồng ý thực thi"; hiển thị nhãn "AI của <tên>"; xử lý đủ trạng thái tải/lỗi/rỗng; phân quyền xem Của tôi / Tất cả) |
| **MIGRATION-CHECK** | ✅ PASS | `backend/apps/ai/migrations/0001_initial.py`, `0002_grant_manage_ai_policy.py`, `backend/apps/accounts/migrations/0010_auditlog_ai_config_version_auditlog_ai_level_and_more.py` (Tạo 3 model AI với `default_permissions = ()`, gán `ai.manage_ai_policy` cho Group `chu`, thêm 3 field AI nullable cho `AuditLog`; `makemigrations --check --dry-run` sạch) |

### Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Biên & Ngoại lệ:**
  - Idempotency key bảo đảm gọi lại cùng tham số trả đúng kết quả/proposal cũ; khác tham số trả HTTP 409 `AI_IDEMPOTENCY_CONFLICT`.
  - Rate throttle `AI_CALL_RATE` chặn spam gọi lệnh AI vượt ngưỡng với HTTP 429 `THROTTLED`.
  - Giới hạn kết quả đọc tối đa 20 dòng và 3.000 ký tự; không lưu kết quả vào DB.
  - Đề xuất ghi (mức C) tự động hết hạn sau 15 phút (`expires_at`), xác nhận sau 15 phút trả HTTP 410 `AI_ACTION_EXPIRED`.
  - Cơ chế nonce và kiểm tra `viewed_at >= 3s` loại bỏ hoàn toàn việc click nhanh hoặc xác nhận tự động.
- **Phân quyền (Bảng vai × Hành động):**
  - `chu`: Sở hữu quyền `ai.manage_ai_policy`, xem được `scope=all` trên toàn bộ Việc AI; thấy đầy đủ các trường giá vốn khi xem chi tiết đề xuất; duyệt được các hành động trong thẩm quyền.
  - `quan_ly`: Xem được Việc AI của mình (`scope=mine`); không được xem `scope=all` (403); không thấy trường giá vốn.
  - `nv_kho`: Gọi lệnh ghi sinh nháp mức C; xem Việc AI của mình; không có quyền xem giá vốn trong `args_preview`.
  - `nv_giao`: Bị từ chối khi duyệt các lệnh ngoài quyền (HTTP 403 `BR-AI-04`); không xem được `scope=all` (403); gọi lệnh ngoài quyền bị 404 `COMMAND_UNKNOWN`.
  - Chưa đăng nhập: 401 Unauthorized.
- **Rò giá vốn (Bất biến 1):**
  - Mọi lệnh đọc qua `pipeline.py` đều đi qua bộ lọc `scrub_data`: người dùng thiếu `view_costprice` bị loại bỏ toàn bộ các khoá nhạy cảm `purchase_rate`, `landed_unit_cost`, `rate`, `unit_cost`, `profit`, `margin`, `cogs`.
  - Màn hình Việc AI: `args_preview` được lọc theo quyền của **người đang xem** (`request.user`), nhân viên kho không thấy đơn giá mua dù là chủ đề xuất.
- **Rò dữ liệu cá nhân (Bất biến 9):**
  - Bộ lọc `scrub_data` loại bỏ đệ quy 11 khoá PII khách hàng đối với **tất cả mọi vai trò** (kể cả `chu`).
  - Đối tượng `target` trong đề xuất chỉ lưu và trả về `type` và `code` (ví dụ `{"type": "salesorder", "code": "SO-01"}`), không lưu tên, SĐT hay địa chỉ khách hàng.
  - Không có chuỗi PII nào xuất hiện trong `AiAction`, `AuditLog`, response JSON hay console log.
- **Hồi quy:**
  - Toàn bộ backend test suite đạt **785 tests xanh 100%** (tăng 10 tests so với Lô 2).
  - Không thay đổi chữ ký `record_audit` hiện có; `set_ai_audit_scope` tự động reset token để không ảnh hưởng đến các luồng UI thông thường.
  - Build frontend và erp-console sạch sẽ, không lỗi TypeScript.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy
1. `cd backend && .venv/bin/python manage.py test apps.ai.execution.tests apps.ai.actions.tests` -> `Ran 25 tests in 0.985s. OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 785 tests in 37.099s. OK. No changes detected.`
3. `cd erp-console && npm test` -> `✓ features/ai/commands/commands.test.ts (8 tests) 8 passed (245ms)`
4. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 23/23 static pages (thêm route `/ai/actions`), First Load JS 97.8 kB.
5. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 8/8 static pages.
6. `grep -rn 'fields = "__all__"' backend/apps` -> Rỗng hoàn toàn.
7. `grep -rnE "console\.(log|info|debug)|localStorage" erp-console/features/guidance erp-console/features/ai/commands erp-console/features/ai/actions` -> Rỗng hoàn toàn.


