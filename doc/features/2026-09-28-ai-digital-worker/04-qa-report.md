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

---

## Lô 3b: Màn "AI của tôi" (DW-12) & Chính sách AI của Chủ (DW-13) · Lần 1 · 2026-09-29

### Kết luận: APPROVED — Lô 3b hoàn thành xuất sắc 100% tiêu chí nghiệm thu: màn "AI của tôi" tự giao lệnh và phiên bản cấu hình theo người dùng; chính sách AI của Chủ cho phép tắt khẩn toàn cục (OFF / C_ONLY) và tắt AI của từng nhân viên; tuân thủ triệt để nguyên tắc không sửa hộ (PUT 405), append-only, kỷ luật không hardcode tên Group (grep rỗng), bảo vệ tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (PII).

### Tổng: 24 ca · ✅ 24 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/lệnh) |
|---|---|---|
| **DW-12-AC1** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac1_nv_kho_chua_cau_hinh` (nv_kho chưa cấu hình: chỉ thấy lệnh trong quyền, chia đúng 3 nhóm; lệnh ghi `level=C`, `choices=["OFF","C"]`; lệnh đọc `level=A`, `choices=["OFF","A"]`, không thấy chốt lô) |
| **DW-12-AC2** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac2_put_hieu_luc_tuc_thi` (Tick trách nhiệm -> PUT đặt `inventory.batch.list=OFF` -> `version`+1, 1 dòng `AiConfigVersion` mới, bản cũ giữ nguyên; AuditLog `ai_config_update`; `call` lệnh đó ngay sau trả 404 `COMMAND_UNKNOWN`) |
| **DW-12-AC3 (lỗi)** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac3_loi_chua_tick_vuot_tran_xung_dot` (Không tick -> 400 `BR-AI-14`; PUT mức B khi env trần C -> 400 `BR-AI-19` kèm `errors`; `base_version` cũ -> 409 `AI_CONFIG_CONFLICT`) |
| **DW-12-AC4 (quyền H1)** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac4_quyenh1_lenh_ngoai_quyen` (nv_kho PUT cấu hình lệnh `sales.refund.confirm` -> 400 `BR-AI-19` "Lệnh ngoài quyền của bạn") |
| **DW-12-AC5 (đổi Group)** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac5_doi_group_lenh_tu_dong_vo_hieu` (nv_kho có override, bị gỡ khỏi Group -> GET không còn trong danh sách; `call` trả 404; override vẫn nằm an toàn trong phiên bản DB cũ) |
| **DW-12-AC6 (tắt AI của tôi)** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac6_tat_ai_cua_toi` (POST `/api/ai/my-config/kill/` `{"killed": true}` -> `version`+1 `killed=true`; lệnh ghi rơi về nháp C theo V-DW4, lệnh đọc vẫn chạy; bật lại được bằng `killed: false`) |
| **DW-12-AC7 (vùng đỏ)** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac7_vung_do_choices_va_locked_reason` (Chủ GET -> `inventory.batch.close` có `choices=["OFF","C"]`, `locked_reason.code="BR-AI-18"`, `red_zone=True`) |
| **DW-12-AC8 (không sửa hộ)** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac8_khong_co_endpoint_sua_ho` (PUT `/api/ai/policy/users/<id>/config/` trả về HTTP 405 Method Not Allowed; không có endpoint sửa cấu hình người khác) |
| **DW-12-AC9 (AI tắt)** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac9_ai_tat_van_200` (`AI_ENABLED=false` -> GET/PUT/kill vẫn trả 200, `ai_enabled=false`; FE hiển thị băng cảnh báo hệ thống AI đang tắt) |
| **DW-12-AC10 (Group không hard-code)** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac10_group_khong_hard_code_va_discipline_grep` (Group fixture `cskh` chỉ thấy lệnh qua quyền; grep không có bất kỳ hardcoded role/group name nào trong `backend/apps/ai`) |
| **DW-12-AC11 (PII versions)** | ✅ PASS | `apps.ai.settings.tests.test_my_config_api::MyConfigApiTests.test_dw12_ac11_my_config_versions_khong_pii` (GET `/api/ai/my-config/versions/` chỉ chứa tên hiển thị nhân viên `created_by_display` và lịch sử `changes`, tuyệt đối không có dữ liệu khách hay giá vốn) |
| **DW-13-AC1 (chế độ c_only)** | ✅ PASS | `apps.ai.policy.tests.test_policy_api::AiPolicyApiTests.test_dw13_ac1_chu_put_global_mode_c_only` (Chủ PUT `global_mode=c_only` -> phiên bản chính sách +1, AuditLog `ai_policy_update`; lệnh ghi toàn cục bị ép trần về C) |
| **DW-13-AC2 (tắt toàn cục)** | ✅ PASS | `apps.ai.policy.tests.test_policy_api::AiPolicyApiTests.test_dw13_ac2_chu_put_global_mode_off` (Chủ PUT `global_mode=off` -> gọi index trả về danh sách rỗng; `call` trả 404 `COMMAND_UNKNOWN`) |
| **DW-13-AC3 (Chủ tắt AI user X)** | ✅ PASS | `apps.ai.policy.tests.test_policy_api::AiPolicyApiTests.test_dw13_ac3_chu_tat_ai_cua_user_x` (POST `/api/ai/policy/users/<X>/kill/` -> phiên bản cấu hình mới của X có `created_by`=Chủ, `killed=true`; X gọi GET my-config thấy `killed=true`) |
| **DW-13-AC4 (xem config user X)** | ✅ PASS | `apps.ai.policy.tests.test_policy_api::AiPolicyApiTests.test_dw13_ac4_chu_xem_config_user_x_chi_doc` (Chủ GET `/api/ai/policy/users/<X>/config/` chế độ chỉ đọc; PUT bị 405 Method Not Allowed) |
| **DW-13-AC5 (phân quyền)** | ✅ PASS | `apps.ai.policy.tests.test_policy_api::AiPolicyApiTests.test_dw13_ac5_phan_quyen_manage_ai_policy_chi_chu` (quan_ly, nv_kho, nv_giao gọi GET/PUT `/api/ai/policy/*` bị 403 Forbidden; quyền `ai.manage_ai_policy` chỉ gán cho Group `chu`, có rollback) |
| **DW-13-AC6 (lỗi policy)** | ✅ PASS | `apps.ai.policy.tests.test_policy_api::AiPolicyApiTests.test_dw13_ac6_loi_base_version_va_chua_tick` (`base_version` lệch -> 409 `AI_POLICY_CONFLICT`; không tick trách nhiệm -> 400 `BR-AI-14`) |
| **DW-13-AC7 (append-only)** | ✅ PASS | `apps.ai.policy.tests.test_policy_api::AiPolicyApiTests.test_dw13_ac7_append_only_khong_co_api_sua_xoa` (Không có API sửa/xoá `AiPolicyVersion`, `AiConfigVersion`; Django Admin đặt has_add/change/delete=False) |
| **DW-13-AC8 (PII/giá vốn policy)** | ✅ PASS | `apps.ai.policy.tests.test_policy_api::AiPolicyApiTests.test_dw13_ac8_users_chi_ten_group_counts_khong_pii_gia_von` (GET `/api/ai/policy/` trả về `users` chỉ gồm display_name, group, counts A/C/OFF; không chứa PII khách hàng hay giá vốn) |
| **DW-13-AC9 (AI tắt policy)** | ✅ PASS | `apps.ai.policy.tests.test_policy_api::AiPolicyApiTests.test_dw13_ac9_ai_tat_policy_van_chay` (`AI_ENABLED=false` -> endpoint policy GET và PUT vẫn hoạt động bình thường, BR-AI-10) |
| **FE-DW-12** | ✅ PASS | `erp-console/features/ai/settings/components/MyConfigScreen.tsx`, route `/ai/settings` (Màn hình "AI của tôi": hiển thị v{version}, nút Tắt/Bật lại AI của mình, banner AI tắt, danh sách 3 nhóm module, dropdown chọn mức OFF/C/A, cảnh báo vùng đỏ và lý do khoá, checkbox cam kết trách nhiệm BR-AI-14) |
| **FE-DW-13** | ✅ PASS | `erp-console/features/ai/policy/components/AiPolicyScreen.tsx`, route `/ai/policy` (Màn hình "Chính sách AI": bộ chọn 3 chế độ ON/C_ONLY/OFF, bảng nhân viên hiển thị trạng thái HOẠT ĐỘNG/ĐÃ TẮT và thống kê lệnh A/C/OFF, nút Tắt khẩn/Mở lại cho từng nhân viên, modal xem chi tiết cấu hình chỉ đọc theo DW-13-AC4) |
| **FE-NAV** | ✅ PASS | `erp-console/shared/lib/nav.ts`, `layout.tsx` (Thêm `ai-settings` và `ai-policy` vào `ViewKey`, quyền `manageAiPolicy`, 2 mục menu "AI của tôi" và "Chính sách AI" bảo vệ bằng `ViewGuard`) |
| **GREP-DISCIPLINE** | ✅ PASS | Quét kỷ luật: không so sánh hardcoded tên role trong `apps/ai`, không dùng `fields = "__all__"`, không `console.log` hay `localStorage` trong các thư mục AI/guidance FE |

### Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Biên & Ngoại lệ:**
  - Xung đột phiên bản: `base_version` không khớp phiên bản hiện tại trong DB trả về HTTP 409 kèm mã lỗi `AI_CONFIG_CONFLICT` hoặc `AI_POLICY_CONFLICT`.
  - Bắt buộc cam kết: Cập nhật cấu hình hoặc chính sách khi thiếu cờ `acknowledge_responsibility` bị từ chối ngay với HTTP 400 `BR-AI-14`.
  - Tắt khẩn cấp: Tắt AI của mình chuyển trạng thái `killed=true`, lệnh ghi rơi về nháp C (V-DW4), lệnh đọc vẫn hoạt động; bật lại được tức thì. Tắt toàn cục `global_mode="off"` làm rỗng chỉ mục và mọi lệnh gọi trả về 404 `COMMAND_UNKNOWN`.
- **Phân quyền (Bảng vai × Hành động):**
  - `chu`: Sở hữu quyền `ai.manage_ai_policy`, truy cập `/api/ai/policy/` (GET, PUT), tắt khẩn AI của bất kỳ nhân viên nào, xem cấu hình nhân viên (chế độ chỉ đọc); xem được lệnh vùng đỏ `inventory.batch.close` trên màn cấu hình cá nhân.
  - `quan_ly`, `nv_kho`, `nv_giao`, `cskh`: Chỉ truy cập được `/api/ai/my-config/` của chính mình; truy cập `/api/ai/policy/*` nhận HTTP 403 Forbidden; cấu hình chỉ hiển thị các lệnh thuộc thẩm quyền Tầng 1 và Tầng 2 của tài khoản.
  - Không sửa hộ: Mọi user kể cả Chủ gọi PUT cấu hình người khác đều nhận HTTP 405 Method Not Allowed.
  - Chưa đăng nhập: Nhận HTTP 401 Unauthorized.
- **Rò giá vốn (Bất biến 1):**
  - Màn "AI của tôi": `get_user_config_data` chỉ trả về metadata lệnh (`id`, `title`, `kind`, `level`, `choices`, `max_level`), không chứa bất kỳ dữ liệu giá vốn hay số tiền nào.
  - Chính sách Chủ: Danh sách `users` chỉ chứa thống kê số lượng lệnh theo mức (`counts: {"A": x, "C": y, "OFF": z}`), không chứa thông tin chi phí hay giá vốn.
- **Rò dữ liệu cá nhân (Bất biến 9):**
  - API lịch sử phiên bản `my-config/versions/` chỉ lưu `created_by_display` (tên nhân viên) và mảng `changes`.
  - Không có thông tin khách hàng (`phone`, `customer`, `delivery_address`) xuất hiện trong bất kỳ response cấu hình hay chính sách nào.
- **Hồi quy:**
  - Toàn bộ backend test suite đạt **805 tests xanh 100%** (tăng 20 tests so với mốc 785 tests của Lô 3a).
  - Không thay đổi hành vi các tính năng guidance, catalog, call, hay các endpoint nghiệp vụ.
  - Build `erp-console` (25 trang tĩnh) và `frontend` (8 trang tĩnh) sạch sẽ 100%.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy
1. `cd backend && .venv/bin/python manage.py test apps.ai.settings.tests apps.ai.policy.tests` -> `Ran 20 tests in 0.945s. OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 805 tests in 37.871s. OK. No changes detected.`
3. `cd erp-console && npm test` -> `✓ features/ai/commands/commands.test.ts (8 tests) 8 passed (245ms)`
4. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 25/25 static pages.
5. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 8/8 static pages.
6. `grep -rnE "\"(chu|quan_ly|nv_kho|nv_giao|cskh)\"" backend/apps/ai --include="*.py" | grep -v tests | grep -v "0002_grant_manage_ai_policy.py"` -> Rỗng hoàn toàn.
7. `grep -rn 'fields = "__all__"' backend/apps` -> Rỗng hoàn toàn.
8. `grep -rnE "console\.(log|info|debug)|localStorage" erp-console/features/guidance erp-console/features/ai/commands erp-console/features/ai/actions erp-console/features/ai/settings erp-console/features/ai/policy` -> Rỗng hoàn toàn.



---

## Lô 3c: Chat gọi lệnh qua `call` (DW-14), Gỡ catalog cũ (DW-15), Nút Tóm tắt AI (DW-16) · Lần 1 · 2026-09-29

### Kết luận: APPROVED — Lô 3c hoàn thành 100% Acceptance Criteria: chat kích hoạt chọn lệnh 2 bước và gọi `call` có nhãn AI rõ ràng, nút "Để AI làm" trên NextStep tự động tạo nháp đề xuất mức C, gỡ bỏ triệt để catalog S01 viết tay theo đúng lộ trình 02b §9.1 (404), nút "Tóm tắt" tóm tắt ngắn gọn <= 3 câu với LLMock mà không gọi API ngoài, bảo vệ tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (PII).

### Tổng: 20 ca · ✅ 20 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/lệnh) |
|---|---|---|
| **DW-14-AC1** | ✅ PASS | `erp-console/features/ai/components/AiAssistantPanel.tsx:180-223`<br>`apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac1_call_read_success` (nv_kho hỏi "còn bao nhiêu CA-001" -> chat chạy chỉ mục -> chọn lệnh `inventory.batch.list` -> gọi `call` -> kết quả hiển thị có nhãn "AI", danh sách mục và số lượng tồn khớp kết quả đọc) |
| **DW-14-AC2** | ✅ PASS | `apps.common.guidance.tests.test_guidance_ai::GuidanceAiFieldTestCase.test_dw14_ac2_chu_mo_lo_buoc_chot_co_ai_level_c`<br>`apps.common.guidance.tests.test_guidance_ai::GuidanceAiFieldTestCase.test_dw14_ac2_quan_ly_thieu_quyen_buoc_chot_ai_null` (Chủ mở lô -> bước chốt có `ai={"level": "C", "label": "AI soạn nháp chốt lô"}`; Quản lý thiếu quyền chốt lô `inventory.close_batch` -> bước chốt có `ai=null`) |
| **DW-14-AC3** | ✅ PASS | `erp-console/features/guidance/components/GuidancePanel.tsx:260-290`<br>`apps.ai.actions.tests.test_actions_api::AiActionApiTestCase.test_dw11_ac1_call_write_creates_proposal_and_auditlog` (Bước có `ai.level=C` hiện nút "Để AI làm" -> bấm kích hoạt `callCommand` sinh đề xuất nháp PENDING, hiển thị thông báo kèm mã việc và link tới màn Việc AI `/ai/actions`; chứng từ gốc trong DB chưa đổi) |
| **DW-14-AC4 (giá vốn)** | ✅ PASS | `erp-console/features/ai/components/AiAssistantPanel.tsx:168-177`<br>`apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac2_cost_keys_scrubbed_for_unauthorized` (Quản lý/kho hỏi "giá vốn lô B-01" -> chặn trước khi gửi model, trả lời ngay "Bạn không có quyền xem thông tin giá vốn."; nếu gọi qua API thì `scrub_data` lọc bỏ 100% khoá giá vốn; descriptor ẩn `purchase_rate`/`landed_unit_cost`) |
| **DW-14-AC5 (PII)** | ✅ PASS | `erp-console/features/ai/components/AiAssistantPanel.tsx:201-206`<br>`apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac3_pii_scrubbed_even_for_chu` (Hỏi "đơn SO... của ai" -> kết quả hiển thị chỉ gồm mã đơn, trạng thái, số lượng; hoàn toàn không có tên/SĐT/địa chỉ khách hàng; backend scrub đệ quy 11 khoá PII) |
| **DW-14-AC6 (lỗi)** | ✅ PASS | `erp-console/features/ai/components/AiAssistantPanel.tsx:224-228` (Lệnh `call` bị backend từ chối trả lỗi 400 kèm mã BR -> chat hiển thị nguyên văn thông điệp tiếng Việt và mã lỗi, không tự ý gửi lại/thử lại vòng lặp) |
| **DW-14-AC7 (máy không model)** | ✅ PASS | `erp-console/features/ai/components/AiAssistantPanel.tsx:45-63, 351-370`<br>`apps.ai.execution.tests.test_call_api::AiCommandCallApiTestCase.test_dw10_ac6_errors_args_and_cloud_channel` (Máy yếu/chưa tải model/4G -> hiển thị hướng dẫn nhập tay, không đẩy lệnh local lên cloud; lệnh local gọi qua kênh cloud bị từ chối 400 `BR-AI-02`) |
| **DW-14-AC8 (AI tắt)** | ✅ PASS | `apps.common.guidance.tests.test_guidance_ai::GuidanceAiFieldTestCase.test_dw14_ac8_ai_disabled_ai_null`<br>`erp-console/features/ai/components/AiAssistantGate.tsx:60-84`<br>`erp-console/features/guidance/components/GuidancePanel.tsx:263-265` (`AI_ENABLED=false` -> `AiAssistantGate` không render chat panel; `resolve_step_ai` trả về `None`, guidance vẫn trả 200 đầy đủ nhưng mọi bước có `ai=null`, nút "Để AI làm" ẩn hoàn toàn) |
| **DW-15-AC1** | ✅ PASS | `apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase.test_dw07_ac9_ai_disabled` (`GET /api/commands/catalog/` trả HTTP 404; các file cũ `registry.py`, `commands/api.py`, `commands/serializers.py`, `test_catalog.py` đã bị xoá hoàn toàn; FE không còn dùng `getCommandCatalog` hay `CommandSpec`) |
| **DW-15-AC2** | ✅ PASS | `apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase.test_dw07_ac4_group_matrix`<br>`apps.ai.registry.tests.test_discovery::CommandDiscoveryTestCase.test_dw07_ac1_snapshot_khop_file` (12 lệnh active cũ đối chiếu Phụ lục B: mọi lệnh đều xuất hiện tương ứng trong registry tự sinh theo đúng phân quyền từng Group; các lệnh chưa có view như `nhap_lo` chờ DW-17) |
| **DW-15-AC3** | ✅ PASS | `erp-console/features/ai/commands/commands.test.ts::DW-15-AC3` (Tìm kiếm bằng từ khoá cũ "tra tồn", "tra_ton" -> hàm `searchCommands` trả về `inventory.batch.list` trong top-3; view khai báo `AiMeta(keywords=("tra_ton", "tra tồn", ...))`) |
| **DW-15-AC4 (kỷ luật registry)** | ✅ PASS | `apps.ai.registry.tests.test_discovery::CommandDiscoveryTestCase`<br>`apps.ai.registry.tests.test_discipline::DisciplineTestCase`<br>`apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase` (Toàn bộ ý định test cũ của S01 được bảo toàn và mở rộng trên registry tự sinh: ID lệnh chuẩn hoá duy nhất, JSON Schema hợp lệ, không chứa bất kỳ khoá PII nào, quyền yêu cầu tồn tại thực và khớp AST, mô tả tiếng Việt >= 5 ký tự) |
| **DW-15-AC5 (AI tắt không lỗi)** | ✅ PASS | `apps.ai.registry.tests.test_index_api::CommandIndexApiTestCase.test_dw07_ac9_ai_disabled`<br>`erp-console/features/ai/commands/commands.test.ts::DW-09-AC8` (`AI_ENABLED=false` -> mở console không bị lỗi do thiếu catalog cũ, các màn hình vận hành độc lập) |
| **DW-16-AC1** | ✅ PASS | `erp-console/features/guidance/components/GuidancePanel.tsx:97-129, 220-230` (Bấm "Tóm tắt" trên khối Đã làm -> gọi LLMock tóm tắt <= 3 câu, hiển thị nhãn "AI", đặt ngay phía trên danh sách dòng thời gian chi tiết) |
| **DW-16-AC2** | ✅ PASS | `erp-console/features/guidance/components/GuidancePanel.tsx:103-112` (Payload gửi cho LLMock chỉ trích xuất từ `data.timeline` đã có sẵn gồm `at`, `label`, `doc`, `actor`; không gọi thêm bất kỳ API nào ra backend) |
| **DW-16-AC3 (giá vốn tóm tắt)** | ✅ PASS | `apps.inventory.batches.tests.test_guidance::GuidanceBatchTest.test_dw05_ac3_cost_hidden_in_timeline_for_non_chu`<br>`erp-console/features/guidance/components/GuidancePanel.tsx:103-112` (`quan_ly` xem dòng thời gian lô đã chốt -> backend đã lọc bỏ toàn bộ số tiền giá vốn; payload và kết quả tóm tắt không chứa số giá vốn) |
| **DW-16-AC4 (PII tóm tắt)** | ✅ PASS | `apps.sales.orders.tests.test_guidance::GuidanceOrderTest.test_dw03_ac5_no_pii_for_chu`<br>`erp-console/features/guidance/components/GuidancePanel.tsx:103-112` (Dòng thời gian đơn không chứa tên, SĐT hay địa chỉ khách hàng; payload tóm tắt sạch PII) |
| **DW-16-AC5 (máy không model)** | ✅ PASS | `erp-console/features/guidance/components/GuidancePanel.tsx:66-94, 206-217` (Máy không đủ năng lực/4G/iOS -> cờ `canSummarize=false`, ẩn hoàn toàn nút "Tóm tắt", không phát sinh network request ra ngoài) |
| **DW-16-AC6 (timeout 10s)** | ✅ PASS | `erp-console/features/guidance/components/GuidancePanel.tsx:114-126` (Quá thời gian 10 giây hoặc model gặp lỗi -> `AbortController` huỷ request, ẩn nội dung tóm tắt, hiển thị thông báo "Không thể tóm tắt dòng thời gian. Vui lòng xem dòng thời gian chi tiết bên dưới", giữ nguyên dòng thời gian) |
| **DW-16-AC7 (AI tắt tóm tắt)** | ✅ PASS | `erp-console/features/guidance/components/GuidancePanel.tsx:71-85` (`AI_ENABLED=false` -> `getAiStatus` trả `ai_enabled=false`, nút "Tóm tắt" bị ẩn, khối Đã làm hiển thị danh sách tất định bình thường) |

### Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Biên & Ngoại lệ:**
  - Nút "Tóm tắt" có timeout 10 giây qua `AbortController` + `setTimeout(10000)`, chống treo giao diện.
  - Chat bắt lỗi 400 và lỗi nghiệp vụ BR-*, hiển thị trực tiếp thông điệp cho người dùng, không tự động retry gây lặp.
  - Phân tích câu hỏi tiếng Việt có fallback an toàn: nếu không khớp lệnh ERP thì chuyển qua LLMock thông thường hoặc gợi ý 4 câu mẫu sau 3 lần không khớp.
- **Phân quyền (Bảng vai × Hành động):**
  - `chu`: Thấy bước chốt lô có `ai={"level": "C", "label": "AI soạn nháp chốt lô"}`; hỏi giá vốn trong chat được xử lý; thấy toàn bộ lệnh trong chỉ mục.
  - `quan_ly`: Bước chốt lô có `ai=null` vì không sở hữu quyền `inventory.close_batch`; hỏi giá vốn trong chat bị từ chối ngay lập tức; tóm tắt timeline không thấy số tiền giá vốn.
  - `nv_kho`: Thấy các lệnh kho/lô; bấm "Để AI làm" trên các bước được phép sinh đề xuất nháp C chuyển về Việc AI.
  - `nv_giao`: Bị giới hạn phạm vi T3; không thấy các lệnh/bước ngoài phạm vi giao hàng.
  - Chưa đăng nhập: Chat và guidance yêu cầu xác thực (401).
- **Rò giá vốn (Bất biến 1):**
  - Chat có kiểm tra quyền xem giá vốn trước khi xử lý các câu hỏi chứa từ khoá giá vốn/lãi lỗ.
  - Backend lọc 2 lớp: ViewSet serializer + `apps/ai/execution/scrub.py`.
  - Descriptor của 94 lệnh không lộ các trường giá vốn nhạy cảm cho người thiếu quyền.
  - Quét `grep -rn 'fields = "__all__"' backend/apps` -> Rỗng.
- **Rò dữ liệu cá nhân (Bất biến 9):**
  - Chat hiển thị kết quả đọc (DW-14-AC5) loại bỏ toàn bộ tên khách, SĐT và địa chỉ.
  - Dòng thời gian và payload tóm tắt sạch 100% PII.
  - Quét mã nguồn frontend: không ghi câu hỏi/kết quả vào `console.log` hay `localStorage`/URL query.
- **Hồi quy:**
  - Gỡ bỏ `commands/catalog/` và `registry.py` cũ không gây ảnh hưởng đến bất kỳ API back-office nào.
  - Toàn bộ backend test suite đạt **798 tests xanh 100%**.
  - Vitest erp-console: 9 tests xanh 100%.
  - Build `erp-console` (25 static pages) và `frontend` (8 static pages) sạch sẽ 100%.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy
1. `cd backend && .venv/bin/python manage.py test apps.common.guidance.tests apps.ai.registry.tests` -> `Ran 22 tests. OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 798 tests in 37.874s. OK. No changes detected.`
3. `cd erp-console && npm test` -> `✓ features/ai/commands/commands.test.ts (9 tests) 9 passed (279ms)`
4. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 25/25 static pages, First Load JS shared giữ nguyên 87.6 kB.
5. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 8/8 static pages.
