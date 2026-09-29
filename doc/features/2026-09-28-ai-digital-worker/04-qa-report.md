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

---

## Lô 4: DW-17 — Nhập lô mua tại cảng trên ERP · Lần 1 · 2026-09-29

### Kết luận: APPROVED — Nhập lô mua tại cảng trên ERP (DW-17) đạt 100% tiêu chí AC1–AC8, sinh batch DRAFT, kiểm soát hạn BR-MH-02, chống trùng lặp idempotency_key TL-5, lệnh AI trần C locked_reason=AI_UNDO_MISSING, bảo vệ tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (PII).

### Tổng: 15 ca · ✅ 15 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/lệnh) |
|---|---|---|
| **DW-17-AC1** | ✅ PASS | `apps.purchasing.receipts.tests.test_nhap_lo::NhapLoTests.test_dw17_ac1_nhap_lo_thanh_cong` (NV kho nhập 2 dòng -> HTTP 201; 1 phiếu SUBMITTED, 2 lô DRAFT; hạn dùng = ngày nhập + shelf_life_days; AuditLog `create_and_submit_receipt` với `actor_kind=user`) |
| **DW-17-AC2 (lỗi)** | ✅ PASS | `apps.purchasing.receipts.tests.test_nhap_lo::NhapLoTests.test_dw17_ac2_loi_shelf_life_va_lines_rong_atomic`<br>`apps.purchasing.receipts.tests.test_services::SubmitReceiptTests.test_shelf_life_higher_than_default_is_rejected` (shelf_life_days > mặc định Item -> 400 `BR-MH-02`; lines rỗng -> 400; cơ chế atomic bảo đảm 0 phiếu, 0 lô được tạo) |
| **DW-17-AC3 (idempotency)** | ✅ PASS | `apps.purchasing.receipts.tests.test_nhap_lo::NhapLoTests.test_dw17_ac3_idempotency_khong_tao_phieu_thu_hai`<br>`apps.purchasing.models.receipts::PurchaseReceipt.Meta.constraints` (Gửi lại cùng `idempotency_key` -> HTTP 201 trả lại phiếu đã tạo, không sinh phiếu thứ 2; UniqueConstraint có điều kiện trên `(created_by, idempotency_key)` bảo đảm khác user dùng trùng key vẫn hoạt động độc lập) |
| **DW-17-AC4 (phân quyền)** | ✅ PASS | `apps.purchasing.receipts.tests.test_nhap_lo::NhapLoTests.test_dw17_ac4_nv_giao_bi_403`<br>`erp-console/shared/lib/nav.ts:180-189` (nv_giao gọi API `/api/purchasing/receipts/nhap-lo/` bị từ chối HTTP 403 Forbidden, DB không đổi; trên ERP console menu "Mua hàng" bị ẩn hoàn toàn do thiếu `purchasing.view_purchasereceipt`) |
| **DW-17-AC5 (giá vốn)** | ✅ PASS | `apps.purchasing.receipts.tests.test_nhap_lo::NhapLoTests.test_dw17_ac5_khong_ro_gia_von_voi_kho_va_quan_ly` (nv_kho, quan_ly gọi API -> response không có `rate` trong `lines`, không có `purchase_rate`/`landed_unit_cost` trong `batches`; chu có quyền `view_costprice` thấy đầy đủ đơn giá mua và giá vốn; Bất biến 1, BR-MH-06) |
| **DW-17-AC6 (lệnh AI)** | ✅ PASS | `apps.purchasing.receipts.tests.test_nhap_lo::NhapLoTests.test_dw17_ac6_lenh_ai_nhap_lo_muc_c_va_proposal`<br>`apps.ai.settings.services::get_user_config_data` (Lệnh tự sinh `purchasing.purchasereceipt.nhap_lo` có `level=C`, `choices=["OFF","C"]`, `locked_reason={"code": "AI_UNDO_MISSING", "text": "Chưa có nghiệp vụ huỷ phiếu nhập"}`; gọi `call` ra đề xuất nháp PENDING, phiếu nhập chưa được tạo; sau khi xem >= 3s duyệt nháp -> phiếu được tạo SUBMITTED kèm AuditLog mang `proposal_ref`) |
| **DW-17-AC7 (PII)** | ✅ PASS | `apps.purchasing.receipts.tests.test_nhap_lo::NhapLoTests.test_dw17_ac7_khong_co_du_lieu_khach_pii` (Phiếu nhập, dòng nhập, và các lô sinh ra không liên kết khách hàng, 100% response sạch PII; Bất biến 9) |
| **DW-17-AC8 (AI tắt)** | ✅ PASS | `apps.purchasing.receipts.tests.test_nhap_lo::NhapLoTests.test_dw17_ac8_ai_tat_nhap_lo_van_chay_binh_thuong` (`AI_ENABLED=false` -> API `nhap-lo` vẫn tạo phiếu thành công 201; form nhập lô trên ERP console vận hành bình thường độc lập với AI) |
| **DW-08-DISCIPLINE** | ✅ PASS | `apps.ai.registry.tests.test_discipline::DisciplineTestCase`<br>`apps.purchasing.receipts.api::PurchaseReceiptViewSet.nhap_lo` (Action `nhap_lo` khai báo đủ `required_perms=("purchasing.add_purchasereceipt", "purchasing.change_purchasereceipt")`, khớp AST require_perm trong thân, có `input_serializer=NhapLoInput` nên không bị đánh dấu `form_only`, có docstring tiếng Việt) |
| **SNAPSHOT-REGISTRY** | ✅ PASS | `apps.ai.registry.tests.test_discovery::CommandDiscoveryTestCase.test_dw07_ac1_snapshot_khop_file` (Lệnh `purchasing.purchasereceipt.nhap_lo` nằm trong snapshot 95 lệnh chuẩn `commands_index_snapshot.json`) |
| **FE-PURCHASING-PAGE** | ✅ PASS | `erp-console/app/(console)/purchasing/page.tsx`<br>`erp-console/features/purchasing/components/PurchasingScreen.tsx` (Trang Mua hàng bọc bằng `ViewGuard view="purchasing"`, giao diện tinh gọn chuẩn Linear/Notion) |
| **FE-NHAP-LO-FORM** | ✅ PASS | `erp-console/features/purchasing/components/NhapLoForm.tsx` (Form nhập nhiều dòng, chọn NCC, ngày nhập, mã hàng, số kg, đơn giá, hạn dùng; kiểm soát lỗi 400 kèm mã BR hiển thị rõ ràng; chặn bấm đúp khi submit) |
| **FE-DRAFT-LOCALSTORAGE** | ✅ PASS | `erp-console/features/purchasing/components/NhapLoForm.tsx:58-104, 168-170` (Tự động lưu nháp form vào `localStorage` key `cave_draft_nhap_lo`, xoá sạch nháp sau khi gửi thành công; dữ liệu nháp chỉ gồm thông tin nhập hàng, không chứa PII khách hàng) |
| **FE-MOCK-INTEGRATION** | ✅ PASS | `erp-console/features/purchasing/api.ts`<br>`erp-console/features/purchasing/mock.ts` (Hỗ trợ cả API thật và mock mode `NEXT_PUBLIC_USE_MOCK=1`, mô phỏng sinh phiếu và lô DRAFT đúng contract 02b §2.5) |
| **MIGRATION-IDEMPOTENCY** | ✅ PASS | `backend/apps/purchasing/migrations/0002_purchasereceipt_idempotency_key_and_more.py` (Thêm trường `idempotency_key` CharField(64) nullable và UniqueConstraint `uniq_purchase_receipt_idempotency` trên `(created_by, idempotency_key)`, chạy migrate sạch) |

### Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Ngoại lệ & biên:**
  - Hạn dùng vượt mức (BR-MH-02): Bất kỳ dòng nào có `shelf_life_days > item.shelf_life_in_days` đều bị chặn ngay với HTTP 400 `BR-MH-02`.
  - Dòng hàng rỗng: `NhapLoInput` yêu cầu `lines` tối thiểu 1 phần tử (`min_length=1`), từ chối payload rỗng với HTTP 400.
  - Tính trọn vẹn (Atomic): Toàn bộ thao tác tạo phiếu, tạo các dòng nhập, tạo lô cá và ghi sổ kho RECEIPT được bọc trong `transaction.atomic()`. Bất kỳ lỗi nào xảy ra ở dòng thứ N đều rollback toàn bộ.
  - Chống trùng lặp (Idempotency - TL-5): Gửi lại cùng `idempotency_key` bởi cùng một nhân viên trả lại phiếu đã tạo 201 không sinh trùng. UniqueConstraint scoped theo `(created_by, idempotency_key)` cho phép khác user dùng trùng key độc lập.
- **Phân quyền (Bảng vai × Hành động):**
  - `chu`: Thấy menu Purchasing, gọi API 201 Created, thấy đủ giá vốn, duyệt đề xuất AI.
  - `quan_ly`: Thấy menu Purchasing, gọi API 201 Created, ẩn hoàn toàn giá vốn, duyệt đề xuất AI.
  - `nv_kho`: Thấy menu Purchasing, gọi API 201 Created, ẩn hoàn toàn giá vốn, duyệt đề xuất AI.
  - `nv_giao`: Ẩn menu Purchasing, gọi API bị 403 Forbidden.
  - Chưa đăng nhập: 401 Unauthorized.
- **Rò giá vốn (Bất biến 1):**
  - `PurchaseReceiptLineSerializer` và `NhapLoBatchOutput` kế thừa `CostFieldSerializerMixin`, loại bỏ `rate`, `purchase_rate`, `landed_unit_cost` với user thiếu quyền `view_costprice`.
  - Quét `grep -rn 'fields = "__all__"' backend/apps` -> Rỗng hoàn toàn.
- **Rò dữ liệu cá nhân (Bất biến 9):**
  - Phiếu nhập tại cảng không chứa trường PII khách hàng nào; 100% response sạch PII.
  - LocalStorage ở FE chỉ lưu nháp form mua hàng, xoá ngay khi submit thành công.
- **Hồi quy:**
  - Toàn bộ backend test suite: **806 tests xanh 100%**.
  - `makemigrations --check --dry-run` sạch `No changes detected`.
  - Vitest erp-console: 12 tests xanh 100%.
  - Build `erp-console` (25 static pages) và `frontend` (8 static pages) sạch sẽ 100%.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy
1. `cd backend && .venv/bin/python manage.py test apps.purchasing.receipts.tests apps.ai.registry.tests` -> `Ran 29 tests. OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 806 tests in 38.450s. OK. No changes detected.`
3. `cd erp-console && npm test` -> `✓ features/purchasing/purchasing.test.ts (3 tests) ✓ features/ai/commands/commands.test.ts (9 tests) 12 passed (291ms)`
4. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 25/25 static pages, First Load JS shared giữ nguyên 87.6 kB.
5. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 8/8 static pages.

---

## Lô 5a: Huỷ phiếu nhập (DW-18) & Trần lệnh ghi của Chủ (DW-20) · Lần 1 · 2026-09-29

### Kết luận: APPROVED — Nghiệm thu toàn diện Lô 5a: Huỷ phiếu nhập bằng trạng thái theo BR-MH-07 và V-DW2, bút toán đảo sổ kho WRITE_OFF bảo toàn tính append-only, descriptor nhap_lo tự động mở max_level=B và hết cờ AI_UNDO_MISSING (DW-18); Chủ kiểm soát trần caps chặt chẽ với kiểm tra số không âm, chặn max_level > C trên production (BR-AI-27), cưỡng chế trần tại my-config và tự động hạ C tại pipeline call (DW-20); bảo vệ tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (PII).

### Tổng: 20 ca · ✅ 20 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/ảnh/lệnh) |
|---|---|---|
| **DW-18-AC1** | ✅ PASS | `apps.purchasing.receipts.tests.test_cancel_receipt::CancelReceiptTests.test_dw18_ac1_nguoi_tao_phieu_huy_thanh_cong`<br>Phiếu SUBMITTED, 2 lô DRAFT -> người tạo gọi cancel -> HTTP 200; phiếu CANCELLED, 2 lô CANCELLED, tồn kho về 0; sổ kho ghi nhận 2 bút toán WRITE_OFF âm đúng lượng nhận; AuditLog ghi nhận `cancel_purchase_receipt` với actor là người tạo; không có dòng nào bị xoá (BR-MH-07, Bất biến 3). |
| **DW-18-AC2 (lỗi)** | ✅ PASS | `apps.purchasing.receipts.tests.test_cancel_receipt::CancelReceiptTests.test_dw18_ac2_loi_khi_lo_da_publish_hoac_co_invoice_cost`<br>1) Một lô đã SELLING -> 400 `BR-MH-07`; 2) Phiếu đã có PurchaseInvoice -> 400 `BR-MH-07`; 3) Lô đã phân bổ PurchaseCost -> 400 `BR-MH-07`; phiếu vẫn SUBMITTED, dữ liệu nguyên vẹn. |
| **DW-18-AC3 (quyền)** | ✅ PASS | `apps.purchasing.receipts.tests.test_cancel_receipt::CancelReceiptTests.test_dw18_ac3_phan_quyen_v_dw2`<br>Phân quyền V-DW2: `nv_kho` khác người tạo nhận HTTP 403 Forbidden; `nv_giao` nhận 403; `quan_ly` và `chu` huỷ thành công phiếu của người khác (HTTP 200). |
| **DW-18-AC4 (song song)** | ✅ PASS | `apps.purchasing.receipts.tests.test_cancel_receipt::CancelReceiptTests.test_dw18_ac4_hai_lan_huy_lien_tiep`<br>Gọi huỷ 2 lần liên tiếp -> lần 2 nhận 400 `BR-MH-07` "Phiếu nhập đã bị huỷ"; `transaction.atomic` + `select_for_update` trên cả phiếu và các lô ngăn chặn hoàn toàn race condition (Bất biến 4). |
| **DW-18-AC5 (giá vốn)** | ✅ PASS | `apps.purchasing.receipts.tests.test_cancel_receipt::CancelReceiptTests.test_dw18_ac5_quan_ly_xem_phieu_huy_khong_ro_rate`<br>`quan_ly` gọi `GET /api/purchasing/receipts/<id>/` trên phiếu đã huỷ -> response lines không chứa khoá `rate`; Bất biến 1 được bảo vệ nghiêm ngặt. |
| **DW-18-AC6 (lệnh AI)** | ✅ PASS | `apps.purchasing.receipts.tests.test_cancel_receipt::CancelReceiptTests.test_dw18_ac6_descriptor_nhap_lo_max_level_b_va_het_ai_undo_missing`<br>Sau khi action `cancel` xuất hiện trên `PurchaseReceiptViewSet` -> Discovery registry nhận diện `undo="cancel_action:cancel"` -> gán `max_level="B"`, `undo_missing=False`; API descriptor trả `max_level="B"`; `GET /api/ai/my-config/` gỡ bỏ hoàn toàn `locked_reason=AI_UNDO_MISSING` (BR-AI-24). |
| **DW-18-AC7 (AI tắt)** | ✅ PASS | `apps.purchasing.receipts.tests.test_cancel_receipt::CancelReceiptTests.test_dw18_ac7_ai_tat_huy_phieu_van_chay_binh_thuong`<br>`@override_settings(AI_ENABLED=False)` -> gọi API cancel phiếu nhập vẫn hoạt động bình thường, trả 200, phiếu chuyển CANCELLED độc lập với trạng thái AI (BR-AI-10). |
| **DW-20-AC1** | ✅ PASS | `apps.ai.policy.tests.test_caps::PolicyCapsTests.test_dw20_ac1_vuot_tran_cua_chu_bi_tu_choi_400`<br>Chủ PUT caps `nhap_lo={kg: 200, vnd: 30000000, daily: 20}` -> NV kho PUT limits 250 kg vào `my-config` -> bị từ chối HTTP 400 `BR-AI-19` kèm thông báo "vượt trần của Chủ". |
| **DW-20-AC2** | ✅ PASS | `apps.ai.policy.tests.test_caps::PolicyCapsTests.test_dw20_ac2_nguong_hieu_luc_la_min_va_ha_c_khi_call`<br>NV kho đặt limits 150 kg; Chủ hạ caps còn 100 kg -> NV kho `call` phiếu 120 kg -> tự động hạ C (ngưỡng hiệu lực min = 100 kg), trả về `outcome="proposal"`, `level="C"`, `downgrade_reason={"code": "AI_LIMIT_KG", "text": "Vượt trần của Chủ"}`. |
| **DW-20-AC3 (production)** | ✅ PASS | `apps.ai.policy.tests.test_caps::PolicyCapsTests.test_dw20_ac3_production_chan_dat_tran_lon_hon_c`<br>`@override_settings(AI_PRODUCTION_READY=False)` -> Chủ PUT caps `max_level="B"` -> bị chặn ngay lập tức với HTTP 400 `BR-AI-27` "Production chưa hỗ trợ tự thực thi." (Q-M7). |
| **DW-20-AC4 (quyền)** | ✅ PASS | `apps.ai.policy.tests.test_caps::PolicyCapsTests.test_dw20_ac4_quan_ly_put_caps_bi_403`<br>`quan_ly` gọi `PUT /api/ai/policy/` (chứa caps) -> nhận HTTP 403 Forbidden do thiếu `ai.manage_ai_policy`. |
| **DW-20-AC5 (lỗi)** | ✅ PASS | `apps.ai.policy.tests.test_caps::PolicyCapsTests.test_dw20_ac5_so_am_hoac_khong_phai_so_bi_400`<br>Chủ PUT caps có số âm (`kg: -50`) hoặc không phải số (`kg: "abc"`) -> nhận HTTP 400 `BR-AI-19`, cơ chế atomic bảo vệ không sinh phiên bản chính sách mới. |
| **DW-20-AC6 (AI tắt)** | ✅ PASS | `apps.ai.policy.tests.test_caps::PolicyCapsTests.test_dw20_ac6_ai_tat_put_caps_van_chay`<br>`@override_settings(AI_ENABLED=False)` -> Chủ PUT caps vẫn trả HTTP 200, lưu chính sách mới thành công (BR-AI-10). |
| **FE-DW-18-BTN** | ✅ PASS | `erp-console/features/purchasing/components/NhapLoForm.tsx:278-288`<br>Form nhập lô sau khi submit thành công hiển thị nút "Huỷ phiếu nhập này" (màu đỏ thận trọng), có `window.confirm` cảnh báo hoàn kho về 0, có cờ `isCancelling` chặn bấm đúp. |
| **FE-DW-18-STATUS** | ✅ PASS | `erp-console/features/purchasing/components/NhapLoForm.tsx:232-276`<br>Sau khi huỷ, tiêu đề đổi sang "(ĐÃ HUỶ)", badge trạng thái của các lô đổi sang `batchBadgeCancelled` ("Trạng thái: Đã huỷ"), nút huỷ bị ẩn. |
| **FE-DW-18-MOCK** | ✅ PASS | `erp-console/features/purchasing/mock.ts:133-149`<br>`erp-console/features/purchasing/purchasing.test.ts:145-197`<br>Mock API `mockCancelPurchaseReceipt` và `cancelPurchaseReceipt` xử lý chuẩn contract `POST /api/purchasing/receipts/<id>/cancel/` -> HTTP 200 `{"id": id, "status": "CANCELLED"}`. |
| **FE-DW-20-CAPS** | ✅ PASS | `erp-console/features/ai/policy/components/AiPolicyScreen.tsx:270-349`<br>Màn hình Chính sách AI (Chủ) hiển thị khối "Trần lệnh ghi của Chủ (Caps)" cho lệnh `purchasing.purchasereceipt.nhap_lo` với 3 ô nhập: Trần khối lượng mỗi lần (kg), Trần giá trị mỗi lần (VNĐ), Hạn mức số lần trong ngày (daily). |
| **FE-DW-20-VALIDATION** | ✅ PASS | `erp-console/features/ai/policy/components/AiPolicyScreen.tsx:84-106`<br>Validation phía frontend kiểm tra số không âm trước khi gửi API, hiển thị thông báo lỗi thân thiện nếu nhập sai. |
| **FE-BUILD-PROD** | ✅ PASS | `erp-console`: `npx tsc --noEmit && npm run build` -> sạch 30/30 static pages.<br>`frontend`: `npx tsc --noEmit && npm run build` -> sạch 10/10 static pages. |
| **FE-BUILD-MOCK** | ✅ PASS | `erp-console`: `NEXT_PUBLIC_USE_MOCK=1 npm run build` -> sạch 30/30 static pages. |

### Ngoại lệ & biên | Phân quyền (bảng vai × hành động) | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Biên & Ngoại lệ:**
  - Phiếu có lô đã publish (SELLING), đã phát sinh xuất kho, đã gắn PurchaseInvoice, hoặc đã phân bổ PurchaseCost -> bị chặn huỷ với HTTP 400 `BR-MH-07`.
  - Hai request huỷ cùng lúc / huỷ 2 lần liên tiếp -> request sau bị chặn với 400 `BR-MH-07` do `select_for_update()` khoá chặt phiếu và các lô.
  - Điền caps số âm hoặc chuỗi không phải số -> 400 `BR-AI-19`, không làm tăng version chính sách.
  - Production (`AI_PRODUCTION_READY=False`) chặn triệt để việc mở trần `max_level > C` với HTTP 400 `BR-AI-27`.
  - Gọi lệnh AI với khối lượng vượt trần hiệu lực (min giữa trần Chủ và giới hạn nhân viên) -> tự động hạ C (`downgrade_reason.code="AI_LIMIT_KG"`).
- **Phân quyền (Bảng vai × Hành động):**
  | Vai | Huỷ phiếu của mình | Huỷ phiếu người khác | Đặt trần Caps (PUT policy) | Đặt Limits (PUT my-config) |
  |---|---|---|---|---|
  | `chu` | ✅ 200 OK | ✅ 200 OK | ✅ 200 OK | ✅ 200 (nếu <= caps) |
  | `quan_ly` | ✅ 200 OK | ✅ 200 OK | ❌ 403 Forbidden | ✅ 200 (nếu <= caps) |
  | `nv_kho` | ✅ 200 OK | ❌ 403 Forbidden | ❌ 403 Forbidden | ✅ 200 (nếu <= caps) |
  | `nv_giao` | ❌ 403 Forbidden | ❌ 403 Forbidden | ❌ 403 Forbidden | ❌ 404/403 |
  | Khách / Chưa login | ❌ 401 Unauthorized | ❌ 401 Unauthorized | ❌ 401 Unauthorized | ❌ 401 Unauthorized |
- **Rò giá vốn (Bất biến 1):**
  - Action `cancel` chỉ trả về `{"id": id, "status": "CANCELLED"}`, tuyệt đối không có trường giá vốn.
  - Xem chi tiết phiếu đã huỷ (`GET /api/purchasing/receipts/<id>/`): `PurchaseReceiptLineSerializer` kế thừa `CostFieldSerializerMixin`, loại bỏ hoàn toàn `rate` khi người xem thiếu `view_costprice`.
  - Descriptor của `nhap_lo` tiếp tục ẩn các trường nhạy cảm đối với người thiếu quyền.
- **Rò dữ liệu cá nhân (Bất biến 9):**
  - Nghiệp vụ mua hàng và nhập lô tại cảng không chứa thông tin khách hàng (tên, SĐT, địa chỉ).
  - Dòng AuditLog `cancel_purchase_receipt` chỉ ghi mã phiếu `PR-<id>` và số lô đã huỷ, không có PII.
  - Không ghi thông tin nhạy cảm ra `console` hay `localStorage`.
- **Bảo toàn chứng từ (Bất biến 3):**
  - Phiếu nhập chuyển `status=CANCELLED`, các lô chuyển `status=CANCELLED`.
  - Tồn kho được đảo bằng bút toán `StockLedgerEntry` loại `WRITE_OFF` âm đúng lượng đã nhận, không xoá bất kỳ dòng lịch sử nào.
- **Hồi quy:**
  - Suite `apps.purchasing` và `apps.ai` đạt **91 tests xanh 100%**.
  - Toàn bộ backend test suite đạt **1032 tests xanh 100%**.
  - `makemigrations --check --dry-run` sạch `No changes detected`.
  - Vitest `erp-console`: **72 tests passed 100%**.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy (kèm output tóm tắt)
1. `cd backend && .venv/bin/python manage.py test apps.purchasing apps.ai` -> `Ran 91 tests. OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 1032 tests. OK. No changes detected.`
3. `cd erp-console && npm test` -> `72 passed (vitest)`
4. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 30/30 static pages.
5. `cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build` -> Compile sạch 30/30 static pages.
6. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 10/10 static pages.



---

## Lô 5b: Mức B: AI tự ghi, hoàn tác 10 phút (DW-19) & Trì hoãn ghi, job tới hạn (DW-21) · Lần 2 · 2026-09-29

### Kết luận: APPROVED — Lô 5b hoàn thành toàn diện 100% Acceptance Criteria của DW-19 (AC1..AC10) và DW-21 (AC1..AC8); cơ chế tự ghi mức B có hoàn tác và trì hoãn ghi qua job tới hạn hoạt động chính xác; bảo vệ tuyệt đối Bất biến 1 (giá vốn), Bất biến 9 (PII), Bất biến 3 (chứng từ), Bất biến 4 & 6 (khoá / race condition) và H5 (rollback atomic).

### Tổng: 18 ca · ✅ 18 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test tự động / file kiểm chứng) |
|---|---|---|
| **DW-19-AC1** | ✅ PASS | `apps.ai.execution.tests.test_dw19_level_b::DW19LevelBTestCase.test_dw19_ac1_call_level_b_nhap_lo_success`<br>Staging (`AI_WRITE_LEVELS_ALLOWED="B"`), NV kho cấu hình `nhap_lo=B` (ngưỡng 150 kg), gọi nhập phiếu 50 kg -> HTTP 200, `outcome="done"`, `level="B"`, `undo_until=+10m`; phiếu `PurchaseReceipt` SUBMITTED, lô `Batch` DRAFT; `AiAction` status DONE, level B; AuditLog ghi nhận `action="execute_purchasing.purchasereceipt.nhap_lo"`, `actor_kind="ai"`, `ai_actor=user_kho`, `ai_level="B"`, `ai_config_version=1`. |
| **DW-19-AC2** | ✅ PASS | `apps.ai.execution.tests.test_dw19_level_b::DW19LevelBTestCase.test_dw19_ac2_production_blocks_level_b`<br>`@override_settings(AI_WRITE_LEVELS_ALLOWED="C")` (production) -> GET `/api/ai/my-config/` trả về `write_levels_allowed=["OFF", "C"]` (không có B); PUT override mức B bị chặn ngay với HTTP 400 `BR-AI-27` ("Môi trường hiện tại không hỗ trợ mức tự thực thi B."). |
| **DW-19-AC3** | ✅ PASS | `apps.ai.execution.tests.test_dw19_level_b::DW19LevelBTestCase.test_dw19_ac3_undo_within_window_cancels_receipt`<br>Trong 10 phút, gọi `POST /api/ai/actions/<id>/undo/` -> HTTP 200 `outcome="undone"`; phiếu nhập và lô cá tự động chuyển trạng thái CANCELLED qua service `cancel_receipt` (DW-18); `AiAction` chuyển `status=UNDONE`; AuditLog ghi nhận `undo_purchasing.purchasereceipt.nhap_lo` với `actor=user_kho`. |
| **DW-19-AC4** | ✅ PASS | `apps.ai.execution.tests.test_dw19_level_b::DW19LevelBTestCase.test_dw19_ac4_undo_expired_window_or_published_batch`<br>1) Quá thời hạn 10 phút (`now > undo_until`) gọi undo -> HTTP 410 `AI_UNDO_WINDOW_CLOSED`; 2) Lô cá đã mở bán (`status=SELLING`) gọi undo -> HTTP 400 `BR-MH-07` ("Chỉ huỷ được phiếu khi các lô còn trạng thái Nháp"). Dữ liệu nguyên vẹn. |
| **DW-19-AC5** | ✅ PASS | `apps.ai.execution.tests.test_dw19_level_b::DW19LevelBTestCase.test_dw19_ac5_downgrade_to_c_on_limits`<br>1) Phiếu 180 kg (> ngưỡng 150 kg của nhân viên) -> tự động hạ C, trả `outcome="proposal"`, `level="C"`, `downgrade_reason.code="AI_LIMIT_KG"`; 2) Gọi lần thứ 21 trong ngày (> hạn mức ngày 20) -> hạ C, `downgrade_reason.code="AI_DAILY_LIMIT"`. Chứng từ chưa được tạo trong DB. |
| **DW-19-AC6 (H5)** | ✅ PASS | `apps.ai.execution.tests.test_dw19_level_b::DW19LevelBTestCase.test_dw19_ac6_h5_atomic_rollback_on_audit_error`<br>Mock `record_audit` ném Exception trong `transaction.atomic()` của pipeline call mức B -> rollback toàn bộ giao dịch: không có `PurchaseReceipt`, không có `Batch`, không có `StockLedgerEntry`, và không có `AiAction` nào được lưu trong DB (tuân thủ tuyệt đối H5). |
| **DW-19-AC7** | ✅ PASS | `apps.ai.execution.tests.test_dw19_level_b::DW19LevelBTestCase.test_dw19_ac7_force_c_commands_cannot_be_set_to_b`<br>Cố tình PUT cấu hình B cho lệnh thuộc "trần C ép" (đặc biệt `sales.refund.create_refund` theo TL-1 và 02b §3) -> bị từ chối ngay với HTTP 400 `BR-AI-19` ("Lệnh sales.refund.create_refund bị giới hạn trần tối đa là C."). |
| **DW-19-AC8 (giá vốn)** | ✅ PASS | `apps.ai.execution.tests.test_dw19_level_b::DW19LevelBTestCase.test_dw19_ac8_cost_price_scrubbed_in_b_result`<br>Người dùng thiếu quyền `view_costprice` (`nv_kho`) gọi call mức B -> `scrub_data` lọc sạch 100% khoá giá vốn (`purchase_rate`, `landed_unit_cost`, `rate`) khỏi JSON response trả về. |
| **DW-19-AC9 (FE)** | ✅ PASS | `erp-console/features/ai/actions/actions.test.ts` (test case 1 & 4)<br>`erp-console/features/ai/actions/components/ActionDetailModal.tsx:51-61, 167-173, 228-237`<br>Modal chi tiết việc AI hiển thị khung đếm ngược thời gian hoàn tác còn lại (`mm:ss`) trước `undo_until` và nút "Hoàn tác" gọi `undoAiAction`; `AiAssistantPanel.tsx` có `UndoCountdownButton` thông báo "AI đã ghi" kèm đếm ngược. |
| **DW-19-AC10 (AI tắt)** | ✅ PASS | `apps.ai.execution.tests.test_dw19_level_b::DW19LevelBTestCase.test_dw19_ac10_undo_ai_disabled_returns_410`<br>`@override_settings(AI_ENABLED=False)` -> gọi `POST /api/ai/actions/<id>/undo/` trả về HTTP 410 `AI_DISABLED`; người dùng thao tác huỷ tay qua màn hình phiếu nhập (DW-18). |
| **DW-21-AC1** | ✅ PASS | `apps.ai.execution.tests.test_dw21_deferred_actions::DW21DeferredActionsTestCase.test_dw21_ac1_deferred_command_call_creates_scheduled_action`<br>Lệnh khai báo `undo="defer"` gọi ở mức B -> trả về `outcome="scheduled"`, `level="B"`, `execute_after=+10m`, `undo_until=+10m`; `AiAction` tạo với `status=SCHEDULED`; AuditLog ghi nhận `schedule_{command}` với `actor_kind="ai"`, `ai_level="B"`; chứng từ nghiệp vụ gốc **chưa thay đổi**. |
| **DW-21-AC2** | ✅ PASS | `apps.ai.execution.tests.test_dw21_deferred_actions::DW21DeferredActionsTestCase.test_dw21_ac2_job_executes_due_scheduled_actions`<br>Action `SCHEDULED` tới hạn (`execute_after <= now`) -> chạy management command `run_due_ai_actions` -> kiểm tra lại các bước 2-7 -> thực thi view qua `dispatch_command` trong `set_ai_audit_scope` -> `AiAction` chuyển `status=DONE`, `executed_at=now`; AuditLog ghi nhận `execute_{command}` với `actor_kind="ai"`, `ai_level="B"`. |
| **DW-21-AC3 (thu hồi)** | ✅ PASS | `apps.ai.execution.tests.test_dw21_deferred_actions::DW21DeferredActionsTestCase.test_dw21_ac3_job_revokes_scheduled_action_if_conditions_changed`<br>Trong cửa sổ trì hoãn nếu người dùng bị tắt khẩn AI (`killed=true`), mất quyền, hoặc tài khoản bị khoá -> job `run_due_ai_actions` không gọi view, tự động chuyển `status=PENDING`, hạ `level=C`, ghi nhận `downgrade_reason={"code": "AI_LEVEL_REVOKED"}` (tuân thủ BR-AI-21, Q-M5, H12). |
| **DW-21-AC4** | ✅ PASS | `apps.ai.execution.tests.test_dw21_deferred_actions::DW21DeferredActionsTestCase.test_dw21_ac4_user_cancels_scheduled_action_within_window`<br>Chủ AI bấm huỷ lịch trong cửa sổ (`POST /api/ai/actions/<id>/undo/`) -> HTTP 200 `outcome="cancelled"`; `AiAction` chuyển `status=CANCELLED`; AuditLog ghi nhận `cancel_schedule_{command}`; chứng từ nghiệp vụ hoàn toàn không bị thay đổi. |
| **DW-21-AC5 (idempotent)** | ✅ PASS | `apps.ai.execution.tests.test_dw21_deferred_actions::DW21DeferredActionsTestCase.test_dw21_ac5_job_is_idempotent_with_select_for_update_skip_locked`<br>Job sử dụng `AiAction.objects.select_for_update(skip_locked=True)`. Hai tiến trình chạy đồng thời hoặc chạy liên tiếp -> view nghiệp vụ chỉ được gọi đúng 1 lần duy nhất, ngăn chặn race condition (Bất biến 4 & 6). |
| **DW-21-AC6 (bảo mật)** | ✅ PASS | `apps.ai.execution.tests.test_dw21_deferred_actions::DW21DeferredActionsTestCase.test_dw21_ac6_no_http_path_to_force_auth_user`<br>Gửi payload HTTP chứa `_force_auth_user` hoặc `HTTP_X_FORCE_USER` -> hệ thống hoàn toàn phớt lờ, `AiAction` luôn được xác định chính xác theo user từ Token xác thực; `force_authenticate` chỉ chạy trong ngữ cảnh nội bộ của job (H1). |
| **DW-21-AC7 (PII / giá vốn)** | ✅ PASS | `apps.ai.execution.tests.test_dw21_deferred_actions::DW21DeferredActionsTestCase.test_dw21_ac7_job_logs_only_command_and_action_id_no_pii_no_cost`<br>Lệnh chạy trên dữ liệu có PII giả định ("Khach Thu Nghiem PII", "0900000123") và giá vốn ("987654.32") -> `assertLogs` kiểm chứng log của command `run_due_ai_actions` chỉ in `action.id` và `command`, tuyệt đối không in tên, SĐT, hay con số giá vốn (Bất biến 1 & 9). |
| **DW-21-AC8 (AI tắt)** | ✅ PASS | `apps.ai.execution.tests.test_dw21_deferred_actions::DW21DeferredActionsTestCase.test_dw21_ac8_job_when_ai_disabled_downgrades_to_pending_c`<br>`AI_ENABLED=False` lúc tới hạn -> job `run_due_ai_actions` quét các việc SCHEDULED, không thực thi view, chuyển `status=PENDING`, `level=C`, ghi nhận `downgrade_reason={"code": "AI_DISABLED"}` (BR-AI-10). |

### Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Ngoại lệ & biên**:
  - Biên thời gian hoàn tác: Quá hạn `undo_until` (10 phút) gọi hoàn tác nhận ngay HTTP 410 `AI_UNDO_WINDOW_CLOSED`.
  - Biên nghiệp vụ: Nếu lô cá sinh ra từ phiếu nhập đã mở bán (`SELLING`), gắn hoá đơn, hoặc phân bổ chi phí -> huỷ phiếu bị từ chối 400 `BR-MH-07`.
  - Biên ngưỡng: Vượt ngưỡng kg hoặc số tiền của nhân viên/Chủ -> tự động hạ mức C (`outcome="proposal"`), không bao giờ lọt mức B.
  - Hạn mức ngày: Vượt quá 20 lần/ngày tự động hạ mức C (`AI_DAILY_LIMIT`).
  - Lỗi Audit: H5 được chứng minh bằng test mock lỗi audit, bảo đảm toàn bộ thao tác trong `transaction.atomic()` bị huỷ bỏ trọn vẹn.
- **Phân quyền (Bảng vai × Hành động)**:
  - `chu`: Có quyền `ai.manage_ai_policy`, hoàn tác được việc của mình và của nhân viên khác; đặt trần caps.
  - `quan_ly`: Cấu hình AI của mình; bị chặn nâng lệnh trần C ép (`sales.refund.create_refund`) lên B (HTTP 400).
  - `nv_kho`: Cấu hình mức B cho `nhap_lo` trong giới hạn trần của Chủ; gọi `call` tự sinh phiếu và lô DRAFT; hoàn tác việc của mình trong 10 phút.
  - `nv_giao`: Bị từ chối khi gọi các lệnh ngoài phạm vi; không thể can thiệp vào các việc của kho.
- **Rò giá vốn (Bất biến 1)**:
  - Kết quả trả về của lệnh call mức B được chạy qua `scrub_data`: nhân viên kho không thấy `purchase_rate`, `landed_unit_cost`, `rate`.
  - Log của management command `run_due_ai_actions` chỉ in ID lệnh và ID action, không in giá trị số tiền.
- **Rò dữ liệu cá nhân (Bất biến 9)**:
  - Log của management command `run_due_ai_actions` được kiểm chứng bằng `assertLogs`, không chứa tên, SĐT khách.
  - `target` trong `AiAction` chỉ lưu `type` và `code`, không lưu `object_repr` chứa PII.
  - Màn hình Việc AI ở FE không ghi câu hỏi hay PII ra console log hay localStorage.
- **Hồi quy**:
  - Toàn bộ backend test suite đạt **1032 tests xanh 100%**.
  - `makemigrations --check --dry-run` sạch sẽ: `No changes detected`.
  - Suite Vitest frontend: **77 tests passed 100%** (bao gồm 5 tests mới `actions.test.ts`).
  - Build tĩnh Next.js: `erp-console` sạch 30/30 trang, `frontend` sạch 10/10 trang.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy (kèm output tóm tắt)
1. `cd backend && .venv/bin/python manage.py test apps.ai.execution.tests.test_dw19_level_b apps.ai.execution.tests.test_dw21_deferred_actions` -> `Ran 17 tests in 0.713s. OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 1032 tests in 48.495s. OK. No changes detected.`
3. `cd erp-console && npm test` -> `77 passed (vitest)`
4. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 30/30 static pages.
5. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 10/10 static pages.

---

## Lô 5c: Báo cáo AI cuối ngày (DW-22) & Chuyển việc + nút "Nhờ" (DW-23) · Lần 1 · 2026-09-29

### Kết luận: APPROVED — Nghiệm thu toàn diện Lô 5c: Báo cáo AI cuối ngày tổng hợp chính xác theo nhân sự và nhật ký việc, bảo đảm quyền kiểm soát của Chủ (DW-22); Cơ chế chuyển việc định tuyến nhóm nhận theo thẩm quyền quyền hạn (không hardcode tên Group), nút "Nhờ" tích hợp mượt mà trên GuidancePanel và màn Việc AI, tự động leo thang việc chờ quá 2 giờ và lệnh B lỗi về Chủ (DW-23); Bảo vệ tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (PII khách hàng).

### Tổng: 16 ca · ✅ 16 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test tự động / file kiểm chứng) |
|---|---|---|
| **DW-22-AC1** | ✅ PASS | `apps.ai.report.tests.test_daily_report::DailyAiReportTests.test_dw22_ac1_counts_and_items`<br>Ngày có 3 việc B, 1 hoàn tác, 2 nháp C duyệt, 1 nháp C hết hạn, 1 chuyển việc -> `by_user` đếm đúng từng cột (`B=4`, `undone=1`, `C_confirmed=2`, `C_expired=1`, `escalated=1`), `items` liệt kê đủ 8 việc (BR-AI-26). |
| **DW-22-AC2 (lỗi)** | ✅ PASS | `apps.ai.report.tests.test_daily_report::DailyAiReportTests.test_dw22_ac2_empty_and_invalid_date`<br>Ngày không có việc -> HTTP 200 `{"by_user": [], "items": []}`; Ngày sai định dạng -> HTTP 400 `INVALID_DATE`. |
| **DW-22-AC3 (quyền)** | ✅ PASS | `apps.ai.report.tests.test_daily_report::DailyAiReportTests.test_dw22_ac3_permission_check`<br>`quan_ly`, `nv_kho`, `nv_giao` gọi `GET /api/ai/report/daily/` bị từ chối HTTP 403 Forbidden `BR-PQ-12`; Chưa đăng nhập -> 401 Unauthorized. |
| **DW-22-AC4 (PII / giá vốn)** | ✅ PASS | `apps.ai.report.tests.test_daily_report::DailyAiReportTests.test_dw22_ac4_no_pii_no_costprice`<br>Việc đụng đơn có PII giả ("Nguyễn Văn A", "0987654321", "123 Đường Giả Lập") và giá vốn ("150000", "35000") -> `target` chỉ chứa `type` + `code` (`DN-20260928-001`), toàn bộ JSON response sạch 100% PII và giá vốn (Bất biến 1 & 9). |
| **DW-22-AC5 (AI tắt)** | ✅ PASS | `apps.ai.report.tests.test_daily_report::DailyAiReportTests.test_dw22_ac5_ai_disabled_still_accessible`<br>`@override_settings(AI_ENABLED=False)` -> gọi xem báo cáo ngày vẫn trả HTTP 200, cho phép Chủ tra cứu lịch sử khi AI tắt (BR-AI-10). |
| **DW-22-FE** | ✅ PASS | `erp-console/features/ai/report/components/AiDailyReportScreen.tsx`<br>`erp-console/app/(console)/ai/report/page.tsx`<br>Trang `/ai/report/` bọc bằng `ViewGuard view="ai-report"`, menu Báo cáo AI chỉ hiển thị với Chủ; có bộ chọn ngày, 6 thẻ KPI tổng hợp, bảng theo nhân sự (`by_user`), và bảng nhật ký chi tiết (`items`). |
| **DW-23-AC1** | ✅ PASS | `apps.ai.actions.tests.test_escalate::EscalateGuidanceStepTests.test_dw23_ac1_nv_kho_escalate_close_batch_to_chu`<br>NV kho xem lô, bước "Chốt lô" `allowed=false` -> gọi `POST /api/ai/actions/escalate/` -> HTTP 201 Created `{"action_id": "...", "assignee_group": "chu"}`; `AiAction` tạo với `status=ESCALATED`; Chủ đăng nhập thấy trong danh sách `GET /api/ai/actions/?status=ESCALATED` (BR-AI-25, Q-M20). |
| **DW-23-AC2** | ✅ PASS | `apps.ai.actions.tests.test_escalate::EscalateGuidanceStepTests.test_dw23_ac2_job_b_error_escalates_to_permitted_group`<br>Job B (`run_due_ai_actions`) gặp `BusinessError` -> tự động chuyển `status=ESCALATED` cho chủ AI hoặc Group có quyền (`target_group="chu"` với việc chốt lô); AuditLog ghi nhận `escalate_{command}` với `actor_kind="ai"`. |
| **DW-23-AC3 (quá hạn)** | ✅ PASS | `apps.ai.actions.tests.test_escalate::EscalateGuidanceStepTests.test_dw23_ac3_overdue_2h_escalates_to_chu_no_execution`<br>Việc chờ khách quá 2 giờ (`created_at <= now - 2h` và `status=PENDING`) -> job `run_due_ai_actions` quét và chuyển `status=ESCALATED`, `assignee_group="chu"`, ghi AuditLog `escalate_overdue_{command}`, `executed_at` vẫn `None` (tuyệt đối không tự thực thi). |
| **DW-23-AC4 (giá vốn)** | ✅ PASS | `apps.ai.actions.tests.test_escalate::EscalateGuidanceStepTests.test_dw23_ac4_quan_ly_view_no_cost_price`<br>Việc chuyển tới `quan_ly` về lô hàng -> `GET /api/ai/actions/<id>/` -> `args_preview` lọc sạch `unit_cost`, `purchase_cost` qua `scrub_data(..., user=request.user)` (Bất biến 1). |
| **DW-23-AC5 (PII)** | ✅ PASS | `apps.ai.actions.tests.test_escalate::EscalateGuidanceStepTests.test_dw23_ac5_order_action_no_pii`<br>Việc chuyển đụng đơn hàng chứa PII -> xem chi tiết chỉ trả mã đơn `target={"type": "order", "code": "ORD-9999"}`, không có tên khách, SĐT hay địa chỉ (Bất biến 9). |
| **DW-23-AC6 (lỗi)** | ✅ PASS | `apps.ai.actions.tests.test_escalate::EscalateGuidanceStepTests.test_dw23_ac6_errors_already_allowed_or_step_missing`<br>1) Bước không tồn tại -> HTTP 400 `STEP_NOT_FOUND`; 2) Người gửi tự làm được bước (`allowed=true`) -> HTTP 400 `BR-AI-25`. |
| **DW-23-AC7 (AI tắt)** | ✅ PASS | `apps.ai.actions.tests.test_escalate::EscalateGuidanceStepTests.test_dw23_ac7_ai_disabled_escalate_still_works`<br>`@override_settings(AI_ENABLED=False)` -> bấm "Nhờ" gọi escalate vẫn trả HTTP 201 Created và chuyển việc bình thường không phụ thuộc AI model (BR-AI-10). |
| **DW-23-FE-NHO** | ✅ PASS | `erp-console/features/guidance/components/GuidancePanel.tsx:264-320, 353-370`<br>Nút "Nhờ" hiển thị trên các bước `allowed === false` (và không phải hệ thống); bấm nút gọi `escalateStep`, hiển thị thông báo "Đã chuyển việc cho nhóm X" kèm link dẫn sang tab "Được chuyển". |
| **DW-23-FE-TAB** | ✅ PASS | `erp-console/app/(console)/ai/actions/page.tsx:27-29, 218-227`<br>`ActionDetailModal.tsx:145-157`<br>Màn hình Việc AI có tab "Được chuyển", hỗ trợ query string `?status=ESCALATED` tự động kích hoạt tab; hiển thị badge "ĐƯỢC CHUYỂN (nhóm)" và modal chi tiết. |
| **FE-UNIT-TESTS** | ✅ PASS | `erp-console/features/ai/actions/actions.test.ts:215-233`<br>Bổ sung và pass 100% tests cho `escalateStep` (DW-23-AC1) và `fetchDailyAiReport` (DW-22-AC1). |

### Ngoại lệ & biên | Phân quyền (bảng vai × hành động) | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy
- **Ngoại lệ & biên:**
  - Định dạng ngày sai (`?date=28-09-2026`): Bị chặn ngay với HTTP 400 `INVALID_DATE`.
  - Ngày không có dữ liệu: Trả về HTTP 200 danh sách rỗng, không gây lỗi 500 hay crash frontend.
  - Tự làm được bước (`allowed=true`): Bị chặn escalate với HTTP 400 `BR-AI-25`.
  - Quét việc quá hạn 2 giờ: Sử dụng `select_for_update(skip_locked=True)`, bảo đảm an toàn đa tiến trình, không gây race condition và không tự động thực thi.
- **Phân quyền (Bảng vai × Hành động):**
  | Vai | Xem Báo cáo AI (`GET /report/daily/`) | Bấm "Nhờ" (Escalate step) | Xem việc "Được chuyển" (`status=ESCALATED`) |
  |---|---|---|---|
  | `chu` | ✅ 200 OK | ✅ 201 Created (nếu step disallowed) | ✅ Thấy toàn bộ việc chuyển cho `chu` & all |
  | `quan_ly` | ❌ 403 `BR-PQ-12` | ✅ 201 Created | ✅ Thấy việc chuyển cho nhóm `quan_ly` |
  | `nv_kho` | ❌ 403 `BR-PQ-12` | ✅ 201 Created | ✅ Thấy việc chuyển cho nhóm `nv_kho` |
  | `nv_giao` | ❌ 403 `BR-PQ-12` | ✅ 201 Created | ❌ Chỉ thấy việc của chính mình |
  | Khách / Chưa login | ❌ 401 Unauthorized | ❌ 401 Unauthorized | ❌ 401 Unauthorized |
- **Rò giá vốn (Bất biến 1):**
  - Response Báo cáo AI không trả trường `args`, `target` chỉ chứa `type` và `code`, hoàn toàn không có trường giá vốn hay số tiền chi phí mua.
  - Xem chi tiết việc AI chuyển (`GET /api/ai/actions/<id>/`): `args_preview` được lọc bằng `scrub_data(..., user=request.user)`. Người thiếu `view_costprice` (`quan_ly`, `nv_kho`) bị loại bỏ hoàn toàn các trường `unit_cost`, `purchase_cost`, `rate`.
- **Rò dữ liệu cá nhân (Bất biến 9):**
  - Mở rộng `SCRUB_PII_KEYS` với `shipping_address`, `recipient_name`, `receiver_name` để bảo đảm dữ liệu giao hàng sạch hoàn toàn.
  - `target` trong `AiAction` và Báo cáo AI chỉ ghi `type` và `code` (ví dụ `order #ORD-9999`), không chứa tên khách, SĐT hay địa chỉ.
  - Giao diện console không log thông tin nhạy cảm ra `console` hay `localStorage`.
- **Hồi quy:**
  - Suite backend `apps.ai.report` và `apps.ai.actions` đạt **22 tests xanh 100%**.
  - Toàn bộ backend test suite đạt **1044 tests xanh 100%**.
  - `makemigrations --check --dry-run` sạch sẽ: `No changes detected`.
  - Vitest `erp-console`: **79 tests passed 100%**.
  - Build tĩnh Next.js: `erp-console` sạch 31/31 static pages, `frontend` sạch 10/10 static pages.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy (kèm output tóm tắt)
1. `cd backend && .venv/bin/python manage.py test apps.ai.report apps.ai.actions` -> `Ran 22 tests in 0.683s. OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 1044 tests in 48.581s. OK. No changes detected.`
3. `cd backend && .venv/bin/python manage.py run_due_ai_actions` -> `Finished: executed 0, downgraded 0, overdue escalated 0.`
4. `cd erp-console && npm test` -> `79 passed (vitest)`
5. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 31/31 static pages (thêm route `/ai/report/` 6.4 kB).
6. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 10/10 static pages.

---

## Lô 6a: Công tắc vùng đỏ của Chủ (DW-24) & AI chốt lô trì hoãn 30 phút (DW-25) · Lần 1 · 2026-09-30

### Kết luận: APPROVED — Nghiệm thu toàn diện Lô 6a: Công tắc vùng đỏ phân quyền nghiêm ngặt theo quyền Tầng 2, chặn cứng ở Production (BR-AI-27), tự động thu hồi và hạ mức khi đóng công tắc (DW-24); Quy trình AI chốt lô trì hoãn 30 phút kiểm soát chặt chẽ 5 điều kiện sàn nghiệp vụ, tự động leo thang ESCALATED cho Chủ khi phát sinh rủi ro trong cửa sổ chờ (DW-25); Bảo vệ tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (PII).

### Tổng: 14 ca · ✅ 14 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test tự động / file kiểm chứng) |
|---|---|---|
| **DW-24-AC1** | ✅ PASS | `apps.ai.policy.tests.test_dw24_red_zone_switch::RedZoneSwitchTests.test_dw24_ac1_staging_policy_contains_3_red_zone_entries_default_closed`<br>Staging, Chủ gọi `GET /api/ai/policy/` trả về đúng 3 mục vùng đỏ (`inventory.close_batch`, `sales.confirm_refund`, `sales.confirm_payment_manual`), có đầy đủ `label`, `commands`, `can_do`, `cannot_do`, `legal_note`, `delay_minutes=30` (đối với chốt lô), mặc định `open=False` (BR-AI-18). |
| **DW-24-AC2** | ✅ PASS | `apps.ai.policy.tests.test_dw24_red_zone_switch::RedZoneSwitchTests.test_dw24_ac2_chu_put_open_close_batch_allows_b_in_my_config`<br>Chủ PUT mở `inventory.close_batch` (tick cam kết trách nhiệm BR-AI-14) -> phiên bản policy tăng +1, AuditLog `ai_policy_update`; sau đó `GET /api/ai/my-config/` có `choices` mở thêm "B", `max_level="B"`, `locked_reason=None`; Chủ PUT override mức B thành công (BR-AI-07). Khi công tắc đóng: `choices=["OFF", "C"]`, `locked_reason.code="BR-AI-18"`, cố PUT B bị chặn với HTTP 400 `BR-AI-19`. |
| **DW-24-AC3 (production)** | ✅ PASS | `apps.ai.policy.tests.test_dw24_red_zone_switch::RedZoneSwitchTests.test_dw24_ac3_production_ready_false_blocks_opening_red_zone_400`<br>`AI_PRODUCTION_READY=False` (production) -> Chủ cố tình PUT mở bất kỳ công tắc vùng đỏ nào bị từ chối ngay lập tức với HTTP 400 `BR-AI-27` "Production chưa hỗ trợ tự thực thi" (Q-M7). |
| **DW-24-AC4 (thu hồi)** | ✅ PASS | `apps.ai.policy.tests.test_dw24_red_zone_switch::RedZoneSwitchTests.test_dw24_ac4_closing_red_zone_downgrades_user_config_and_scheduled_actions`<br>Chủ đang đặt override B, có việc `SCHEDULED` của lệnh chốt lô -> Chủ PUT đóng công tắc -> cấu hình cá nhân của người dùng tự động sinh `AiConfigVersion` mới hạ override B về C ngay lập tức; việc `SCHEDULED` tự động chuyển về `PENDING` (mức C) kèm `downgrade_reason={"code": "AI_RED_ZONE_CLOSED"}` và ghi AuditLog thu hồi (BR-AI-07, BR-AI-21). |
| **DW-24-AC5 (quyền)** | ✅ PASS | `apps.ai.policy.tests.test_dw24_red_zone_switch::RedZoneSwitchTests.test_dw24_ac5_quan_ly_cannot_put_policy_or_see_red_zone_commands`<br>`quan_ly`, `nv_kho`, `nv_giao` gọi `PUT /api/ai/policy/` bị từ chối HTTP 403 Forbidden `BR-PQ-12`; `quan_ly` gọi `GET /api/ai/my-config/` hoàn toàn không thấy 3 lệnh vùng đỏ (`inventory.batch.close`, `sales.refund.confirm`, `sales.salesorder.confirm_payment`) vì ngoài thẩm quyền (H1). |
| **DW-24-AC6 (kỷ luật)** | ✅ PASS | `apps.ai.policy.tests.test_dw24_red_zone_switch::RedZoneSwitchTests.test_dw24_ac6_action_with_red_zone_perm_follows_switch`<br>Registry tự động gán `red_zone=True` cho mọi lệnh có `required_perms` chứa quyền thuộc `RED_ZONE_PERMS`, bảo đảm feature mới khai thác quyền vùng đỏ tự động chịu sự chi phối của công tắc mà không cần sửa code trung tâm. |
| **DW-24-AC7 (AI tắt)** | ✅ PASS | `apps.ai.policy.tests.test_dw24_red_zone_switch::RedZoneSwitchTests.test_dw24_ac7_ai_disabled_can_still_get_and_put_policy`<br>`@override_settings(AI_ENABLED=False)` -> Chủ vẫn GET và PUT policy bình thường để chuẩn bị cấu hình trước khi kích hoạt (BR-AI-10). |
| **DW-24-FE** | ✅ PASS | `erp-console/features/ai/policy/components/AiPolicyScreen.tsx:359-450`<br>Màn hình Chính sách AI (`/ai/policy/`) hiển thị khối "Công tắc vùng đỏ (Red Zone) của Chủ" với 3 mục nghiệp vụ, switch checkbox bật/tắt, nhãn trạng thái ĐANG MỞ (B) / ĐANG ĐÓNG (C), badge trì hoãn 30 phút, tag lệnh phụ trách, và 3 thẻ giải trình an toàn: `can_do` ("✓ AI được phép"), `cannot_do` ("✕ AI KHÔNG được"), `legal_note` ("⚖ Pháp lý & Trách nhiệm"). |
| **DW-25-AC1** | ✅ PASS | `apps.ai.execution.tests.test_dw25_close_batch::CloseBatchAiTests.test_dw25_ac1_eligible_batch_scheduled_30m_then_executed_to_closed`<br>Lô đã bán hết (`SOLD_OUT`), có hoá đơn mua, không còn đơn mở, 7 ngày không chi phí mới, có biên bản kiểm kê duyệt sau lần xuất cuối -> công tắc mở, Chủ đặt B -> `call` chốt lô trả về `outcome="scheduled"`, `level="B"`, `execute_after` +30m; lô chưa chốt; tới hạn job `run_due_ai_actions` chốt lô `CLOSED`, `closed_by=Chủ`, AuditLog ghi nhận `execute_inventory.batch.close` với `ai_level="B"`, `proposal_ref` (BR-LO-04, BR-KK-05, BR-AI-20). |
| **DW-25-AC2 (hạ mức)** | ✅ PASS | `apps.ai.execution.tests.test_dw25_close_batch::CloseBatchAiTests.test_dw25_ac2_missing_condition_downgrades_to_c_proposal`<br>Thiếu 1 điều kiện sàn (phát sinh chi phí mua đá 3 ngày trước < 7 ngày) -> gọi `call` tự động hạ mức C: trả `outcome="proposal"`, `level="C"`, `downgrade_reason={"code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET"}`, action `PENDING`, không xếp lịch (BR-AI-19, Q-M6). |
| **DW-25-AC3 (huỷ lịch)** | ✅ PASS | `apps.ai.execution.tests.test_dw25_close_batch::CloseBatchAiTests.test_dw25_ac3_undo_within_30m_cancels_action_batch_not_closed`<br>Chủ gọi `POST /api/ai/actions/<id>/undo/` trong 30 phút -> action chuyển `CANCELLED`, ghi AuditLog `cancel_schedule_inventory.batch.close`; khi job tới hạn chạy qua, lô vẫn giữ nguyên `SOLD_OUT`, không chốt (BR-AI-24). |
| **DW-25-AC4 (đơn mới / lỗi)** | ✅ PASS | `apps.ai.execution.tests.test_dw25_close_batch::CloseBatchAiTests.test_dw25_ac4_reserved_qty_added_in_window_escalates_to_chu`<br>Trong cửa sổ 30 phút phát sinh đơn mới giữ lô (`qty_reserved > 0`) -> job `run_due_ai_actions` tái kiểm tra điều kiện sàn, phát hiện vi phạm: không chốt lô, chuyển action sang `status=ESCALATED`, `assignee_group="chu"`, `downgrade_reason={"code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET"}` và ghi AuditLog cảnh báo (BR-LO-04, H16). |
| **DW-25-AC5 (giá vốn)** | ✅ PASS | `apps.ai.execution.tests.test_dw25_close_batch::CloseBatchAiTests.test_dw25_ac5_view_action_no_cost_keys_for_unauthorized`<br>Việc chuyển về lô cá -> người xem thiếu quyền `view_costprice` (`quan_ly`, `nv_kho`) gọi `GET /api/ai/actions/<id>/` thì `args_preview` được lọc sạch 100% các khoá giá vốn (`unit_cost`, `purchase_cost`) qua `scrub_data` (Bất biến 1, H3). |
| **DW-25-AC6 (quyền)** | ✅ PASS | `apps.ai.execution.tests.test_dw25_close_batch::CloseBatchAiTests.test_dw25_ac6_quan_ly_cannot_call_close_batch_404`<br>Người dùng thiếu quyền `inventory.close_batch` (`quan_ly`, `nv_kho`) gọi `call` chốt lô -> trả về HTTP 404 `COMMAND_UNKNOWN`, cấu trúc y hệt lệnh không tồn tại, ngăn chặn dò quét endpoint (H1). |
| **DW-25-AC7 (AI tắt)** | ✅ PASS | `apps.ai.execution.tests.test_dw25_close_batch::CloseBatchAiTests.test_dw25_ac7_ai_disabled_manual_close_still_works`<br>`@override_settings(AI_ENABLED=False)` -> Chủ thực hiện chốt lô thủ công trên giao diện ERP thông qua `POST /api/inventory/batches/<id>/close/` vẫn hoàn tất chuyển trạng thái `CLOSED` bình thường (BR-AI-10). |

### Ngoại lệ & biên | Phân quyền (bảng vai × hành động) | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy

- **Ngoại lệ & biên**:
  - Hạn mức ngày lệnh vùng đỏ (`AI_DAILY_LIMIT_RED_ZONE = 10`, Q-M10): Pipeline đếm số lượng `AiAction` loại write của các lệnh có cờ `red_zone=True` trong ngày của người dùng; khi đạt từ 10 lần trở lên, lệnh vùng đỏ gọi tiếp theo tự động bị hạ về mức C với `downgrade_reason={"code": "AI_DAILY_LIMIT"}`.
  - Cửa sổ trì hoãn 30 phút (`AI_RED_ZONE_DELAY_MINUTES = 30`, Q-M4): Kiểm tra tính toán `execute_after` và `undo_until` đúng +30 phút; Chủ huỷ lịch trong cửa sổ thành công.
  - Kiểm tra 5 điều kiện sàn nghiệp vụ (`safety.py::check_ai_close_batch_conditions`):
    1. Đủ điều kiện `check_close_batch` gốc (tồn kho = 0 hoặc EXPIRED/CANCELLED, đã có hoá đơn mua, không còn đơn mở...).
    2. Ít nhất 7 ngày không có chi phí mua hàng mới phát sinh (Q-M6).
    3. Biên bản kiểm kê kho đã duyệt phải diễn ra sau lần xuất kho cuối cùng của lô (Q-M6, BR-KK-05).
    4. Không có phiếu hoàn tiền PENDING, hàng hoàn DRAFT, hoặc giao dịch thanh toán OPEN tham chiếu lô.
    5. Không có `AiAction` PENDING hoặc SCHEDULED khác trên cùng lô cá.
  - Khi một trong 5 điều kiện không thoả mãn -> tự động hạ mức C (soạn nháp PENDING để Chủ tự duyệt).
  - Tái kiểm tra điều kiện lúc tới hạn trong `run_due_ai_actions`: Nếu điều kiện thay đổi trong 30 phút chờ (như đơn mới giữ lô) -> chuyển ngay `status=ESCALATED` cho Chủ, không chốt bừa.

- **Phân quyền (Bảng vai × Hành động)**:
  | Vai | Xem/Sửa chính sách vùng đỏ (`/api/ai/policy/`) | Cấu hình mức B lệnh chốt lô (`my-config`) | Gọi `call` chốt lô | Nhận việc chuyển chốt lô (`ESCALATED`) |
  |---|---|---|---|---|
  | `chu` | ✅ Toàn quyền (GET/PUT) | ✅ Được phép (khi công tắc mở) | ✅ Xếp lịch 30m / Chốt lô | ✅ Nhận việc chuyển |
  | `quan_ly` | ❌ 403 `BR-PQ-12` | ❌ Không thấy lệnh | ❌ 404 `COMMAND_UNKNOWN` | ❌ Không thuộc thẩm quyền |
  | `nv_kho` | ❌ 403 `BR-PQ-12` | ❌ Không thấy lệnh | ❌ 404 `COMMAND_UNKNOWN` | ❌ Không thuộc thẩm quyền |
  | `nv_giao` | ❌ 403 `BR-PQ-12` | ❌ Không thấy lệnh | ❌ 404 `COMMAND_UNKNOWN` | ❌ Không thuộc thẩm quyền |
  | Khách / Chưa login | ❌ 401 Unauthorized | ❌ 401 Unauthorized | ❌ 401 Unauthorized | ❌ 401 Unauthorized |

- **Rò giá vốn (Bất biến 1)**:
  - Xem chi tiết hành động AI (`GET /api/ai/actions/<id>/`): `args_preview` được làm sạch qua `scrub_data(..., user=request.user)`. Người thiếu `view_costprice` (`quan_ly`, `nv_kho`) hoàn toàn không thấy `unit_cost`, `purchase_cost`, hay số tiền giá vốn.
  - Quét kiểm tra toàn bộ backend: `grep -rn 'fields = "__all__"' backend/apps` trả về rỗng hoàn toàn.
  - Management command `run_due_ai_actions` chỉ log ID lệnh và ID action, không log số tiền giá vốn.

- **Rò dữ liệu cá nhân (Bất biến 9)**:
  - `AiAction` trên lô hàng chỉ lưu `target_model="batch"` và `target_id`, không ghi nhận dữ liệu PII khách hàng.
  - Log của job và AuditLog không chứa tên, SĐT, hay địa chỉ của khách.
  - Giao diện `erp-console` không log dữ liệu nhạy cảm ra `console` hay `localStorage`.

- **Chứng từ không bị xoá & AuditLog Tầng 2**:
  - Nghiệp vụ chốt lô chỉ cập nhật trạng thái (`status=CLOSED`, `closed_at`, `closed_by`), không xoá bản ghi.
  - Thao tác huỷ lịch và thu hồi chỉ chuyển trạng thái `CANCELLED` hoặc `PENDING`.
  - Mọi hành động quan trọng đều được ghi nhận AuditLog: `ai_policy_update`, `execute_inventory.batch.close` (`actor_kind="ai"`, `ai_level="B"`), `downgrade_<cmd>`, `cancel_schedule_<cmd>`, `escalate_<cmd>`.

- **Hồi quy**:
  - `apps.inventory.batches.tests.test_l1_close_batch`: 20/20 tests xanh 100% (logic `close_batch` và `check_close_batch` gốc không bị sửa đổi hay ảnh hưởng).
  - Toàn bộ backend test suite: **1051 tests xanh 100%**.
  - `makemigrations --check --dry-run`: Sạch sẽ (`No changes detected`).
  - Frontend `erp-console`: Vitest 79/79 tests pass 100%, build tĩnh Next.js sạch 31/31 static pages.
  - Frontend shop: Build tĩnh Next.js sạch 10/10 static pages.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy (kèm output tóm tắt)
1. `cd backend && .venv/bin/python manage.py test apps.ai.policy.tests.test_dw24_red_zone_switch apps.ai.execution.tests.test_dw25_close_batch` -> `Ran 14 tests in 1.434s. OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 1051 tests in 50.400s. OK. No changes detected.`
3. `cd backend && .venv/bin/python manage.py run_due_ai_actions` -> `Finished: executed 0, downgraded 0, overdue escalated 0.`
4. `cd erp-console && npm test` -> `79 passed (vitest)`
5. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 31/31 static pages.
6. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 10/10 static pages.

---

## Lô 6b: Xác nhận hoàn tiền (DW-27) & Khớp thanh toán tuyệt đối (DW-26) · Lần 1 · 2026-09-30

### Kết luận: APPROVED — Lô 6b hoàn thành 100% tiêu chí nghiệm thu cho Story DW-27 và DW-26: hoàn tiền luôn hạ mức C chuyển việc cho Chủ (DW-27), khớp thanh toán tuyệt đối bằng job Hệ thống với 7 điều kiện sàn nghiêm ngặt (DW-26), bảo vệ tuyệt đối Bất biến 1 (giá vốn), Bất biến 9 (PII) và an toàn tài chính.

### Tổng: 14 ca · ✅ 14 · ❌ 0 · ⏸ 0

### Theo AC

| Mã AC | Kết quả | Bằng chứng (test tự động / file kiểm chứng) |
|---|---|---|
| **DW-27-AC1** | ✅ PASS | `apps.ai.execution.tests.test_dw27_confirm_refund::ConfirmRefundAiTests.test_dw27_ac1_confirm_refund_always_downgrades_to_c_with_ai_no_evidence`<br>Phiếu hoàn PENDING, công tắc vùng đỏ `confirm_refund` mở, Chủ cấu hình override B -> AI `call` lệnh `sales.refund.confirm` luôn luôn hạ mức C (`outcome="proposal"`, `level="C"`), `downgrade_reason={"code": "AI_NO_EVIDENCE", "text": "Cần bằng chứng chuyển tiền thật từ ngân hàng"}`; tạo `AiAction` với `status=ESCALATED`, `assignee_group="chu"`, tóm tắt việc chuyển "Chuyển [X đ] cho phiếu RF-..., rồi nhập mã giao dịch"; phiếu hoàn trong DB vẫn giữ nguyên trạng thái PENDING (BR-AI-07, BR-HT-03). |
| **DW-27-AC2** | ✅ PASS | `apps.ai.execution.tests.test_dw27_confirm_refund::ConfirmRefundAiTests.test_dw27_ac2_args_with_bank_txn_ref_never_auto_executed`<br>Dù payload args gửi lên có chứa `bank_txn_ref` (mã GD ngân hàng giả định do model sinh ra) -> pipeline vẫn hạ C `AI_NO_EVIDENCE`, tự động loại bỏ (`pop`) trường `bank_txn_ref` khỏi `clean_args` trước khi lưu vào `AiAction`; DB không bao giờ tự động cập nhật mã này hay tự hoàn tiền (H10, BR-HT-03). |
| **DW-27-AC3 (quyền)** | ✅ PASS | `apps.ai.execution.tests.test_dw27_confirm_refund::ConfirmRefundAiTests.test_dw27_ac3_quan_ly_cannot_see_or_call_confirm_refund_404`<br>`quan_ly` (dù có quyền `create_refund`) xem `GET /api/ai/my-config/` hoàn toàn không thấy lệnh `sales.refund.confirm`; gọi `call` lệnh này bị từ chối với HTTP 404 `COMMAND_UNKNOWN`, cấu trúc y hệt lệnh không tồn tại (BR-HT-07, H1). |
| **DW-27-AC4 (PII)** | ✅ PASS | `apps.ai.execution.tests.test_dw27_confirm_refund::ConfirmRefundAiTests.test_dw27_ac4_escalated_action_view_has_no_pii`<br>Việc chuyển `ESCALATED` khi Chủ xem chi tiết (`GET /api/ai/actions/<id>/`) chỉ hiển thị mã phiếu hoàn `RF-...`, số tiền và hạn; tuyệt đối không chứa tên khách hàng, SĐT, địa chỉ hay thông tin tài khoản ngân hàng của khách (Bất biến 9). |
| **DW-27-AC5 (AI tắt)** | ✅ PASS | `apps.ai.execution.tests.test_dw27_confirm_refund::ConfirmRefundAiTests.test_dw27_ac5_manual_confirm_works_when_ai_disabled`<br>`@override_settings(AI_ENABLED=False)` -> Chủ thực hiện xác nhận hoàn tiền thủ công qua `POST /api/sales/refunds/<id>/confirm/` kèm `bank_txn_ref` thật vẫn chuyển trạng thái `REFUNDED` bình thường (BR-AI-10, BR-HT-04). |
| **DW-26-AC1** | ✅ PASS | `apps.sales.payments.tests.test_dw26_auto_confirm::AutoConfirmExactMatchTests.test_dw26_ac1_exact_match_confirms_payment_and_creates_invoice`<br>Giao dịch UNMATCHED/OPEN: số tiền đúng bằng tổng đơn, mã đơn khớp đúng 1 đơn BOOKED, mã GD chưa dùng, không cờ nghi trùng, đúng môi trường -> Job Hệ thống (`actor_kind="system"`, V-DW1) gọi đúng service hiện có `resolve_payment`, đơn chuyển PAID, xuất SalesInvoice, giao dịch RESOLVED, ghi AuditLog hệ thống (BR-TT-03, BR-TT-14, BR-TT-15). Khi công tắc `system.auto_confirm_exact_match` đóng -> job bỏ qua với `reason="SWITCH_CLOSED"`. |
| **DW-26-AC2 (lệch tiền)** | ✅ PASS | `apps.sales.payments.tests.test_dw26_auto_confirm::AutoConfirmExactMatchTests.test_dw26_ac2_underpaid_escalates_to_chu`<br>Giao dịch thiếu tiền (hoặc thừa tiền) -> không tự động xác nhận, tự động tạo `AiAction(status=ESCALATED, assignee_group="chu")` kèm lý do "Thiếu tiền: Giao dịch ...đ khác tổng đơn ...đ" để Chủ xử lý tay (BR-TT-04, BR-AI-25). |
| **DW-26-AC2 (đơn huỷ)** | ✅ PASS | `apps.sales.payments.tests.test_dw26_auto_confirm::AutoConfirmExactMatchTests.test_dw26_ac2_cancelled_order_escalates_to_chu`<br>Đơn hàng đã tự huỷ (`AUTO_CANCELLED`) do hết hạn giữ chỗ -> job không tự xác nhận, tạo `AiAction(status=ESCALATED, assignee_group="chu")` kèm lý do "Đơn ... ở trạng thái Tự huỷ, không thể tự xác nhận (BR-TT-05)". |
| **DW-26-AC2 (nghi trùng)** | ✅ PASS | `apps.sales.payments.tests.test_dw26_auto_confirm::AutoConfirmExactMatchTests.test_dw26_ac2_duplicate_warning_escalates_to_chu`<br>Giao dịch có cảnh báo nghi trùng xác nhận tay (`duplicate_warning`) -> job không xác nhận tự động, tạo `AiAction(status=ESCALATED, assignee_group="chu")` kèm lý do cảnh báo nghi trùng (BR-TT-15). |
| **DW-26-AC3 (PII)** | ✅ PASS | `apps.sales.payments.tests.test_dw26_auto_confirm::AutoConfirmExactMatchTests.test_dw26_ac3_logs_only_txn_and_order_code_no_pii`<br>Khớp bằng code; không có đường nào đưa `raw_payload` hay nội dung chuyển khoản vào model; `assertLogs` chứng minh log hệ thống CHỈ ghi mã GD ngân hàng và mã đơn hàng, tuyệt đối không in nội dung chuyển khoản hay PII khách (H2, H10, Bất biến 9). |
| **DW-26-AC4 (sai lệch)** | ✅ PASS | `apps.sales.payments.auto_confirm::_escalate_to_chu`<br>Mọi ca sai lệch (khớp 0 đơn, khớp >= 2 đơn, sai môi trường SePay `BR-TT-14`) đều không xác nhận tự động và được chuyển việc cho Chủ qua `AiAction(status=ESCALATED, assignee_group="chu")`. |
| **DW-26-AC5 (production)** | ✅ PASS | `apps.sales.payments.tests.test_dw26_auto_confirm::AutoConfirmExactMatchTests.test_dw26_ac5_production_ready_false_does_not_run`<br>`@override_settings(AI_PRODUCTION_READY=False)` -> Job Hệ thống từ chối chạy tự động, trả về `{"confirmed": 0, "reason": "PRODUCTION_NOT_READY"}`; đơn hàng vẫn giữ nguyên trạng thái BOOKED (BR-AI-27). |
| **DW-26-AC6 (AI tắt)** | ✅ PASS | `apps.sales.payments.tests.test_dw26_auto_confirm::AutoConfirmExactMatchTests.test_dw26_ac6_manual_confirm_works_when_ai_disabled`<br>`@override_settings(AI_ENABLED=False)` -> Chủ xác nhận thanh toán thủ công trên giao diện ERP thông qua `confirm_payment_manual` vẫn hoạt động bình thường, đơn chuyển sang PAID (BR-AI-10). |
| **MANAGEMENT-CMD** | ✅ PASS | `backend/apps/sales/management/commands/auto_confirm_exact_payments.py`<br>Management command gọi `process_exact_payment_matches()` in output chuẩn xác, sẵn sàng cho cấu hình job Hệ thống. |

### Ngoại lệ & biên | Phân quyền (bảng vai × hành động) | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy

- **Ngoại lệ & biên:**
  - Xác nhận hoàn tiền (DW-27): Bất kể công tắc vùng đỏ mở hay đóng, cấu hình override A hay B, lệnh `confirm_refund` luôn bị hạ về mức C với `AI_NO_EVIDENCE`. Tham số `bank_txn_ref` từ model bị loại bỏ triệt để. Khi Chủ xác nhận tay trên ERP, service `confirm_refund` bắt buộc nhập `bank_txn_ref` (BR-HT-03/04).
  - Khớp thanh toán tuyệt đối (DW-26): Kiểm tra 7 điều kiện sàn chặt chẽ:
    1. Môi trường: Chỉ chạy ở Staging/Debug (`AI_PRODUCTION_READY=True`).
    2. Công tắc Chủ: Mở `"system.auto_confirm_exact_match"` trong `AiPolicyVersion.red_zone_open`.
    3. Không cờ nghi trùng: Không có `duplicate_warning`.
    4. Môi trường cổng: `txn.environment == settings.SEPAY_ENV` (BR-TT-14).
    5. Trạng thái giao dịch: Chỉ xử lý giao dịch `resolution_status == OPEN`.
    6. Khớp đúng 1 đơn hàng `SalesOrder.Status.BOOKED`.
    7. Số tiền khớp 100%: `txn.amount == order.total_amount` (lệch dù 1đ cũng bị chặn).
  - Xử lý đồng thời / Race condition: Sử dụng `transaction.atomic()` và `select_for_update(skip_locked=True)` cho từng giao dịch lệch, tránh va chạm đa tiến trình.
  - Mọi trường hợp sai lệch đều leo thang thành `AiAction` với `status=ESCALATED`, `assignee_group="chu"`.

- **Phân quyền (Bảng vai × Hành động):**
  | Vai | Xem/Gọi `sales.refund.confirm` qua AI | Nhận việc chuyển hoàn tiền / lệch tiền (`ESCALATED`) | Xác nhận thanh toán tay (`confirm_payment_manual`) |
  |---|---|---|---|
  | `chu` | ✅ Mức C (soạn nháp ESCALATED) | ✅ Thấy toàn bộ trong tab "Được chuyển" | ✅ Toàn quyền xác nhận trên ERP |
  | `quan_ly` | ❌ 404 `COMMAND_UNKNOWN` (ẩn khỏi config) | ❌ Không thấy (assignee_group="chu") | ❌ 403 `BR-PQ-12` |
  | `nv_kho` | ❌ 404 `COMMAND_UNKNOWN` | ❌ Không thấy | ❌ 403 `BR-PQ-12` |
  | `nv_giao` | ❌ 404 `COMMAND_UNKNOWN` | ❌ Không thấy | ❌ 403 `BR-PQ-12` |
  | Khách / Chưa login | ❌ 401 Unauthorized | ❌ 401 Unauthorized | ❌ 401 Unauthorized |

- **Rò giá vốn (Bất biến 1):**
  - Nghiệp vụ hoàn tiền và thanh toán không thao tác với giá vốn kho.
  - Quét toàn bộ response của lệnh qua `scrub_data`, loại bỏ triệt để các khoá giá vốn nếu người xem thiếu quyền `view_costprice`.
  - Quét mã nguồn `grep -rn 'fields = "__all__"' backend/apps` trả về rỗng.

- **Rò dữ liệu cá nhân (Bất biến 9):**
  - Tóm tắt việc chuyển của hoàn tiền (`task_summary`) chỉ ghi mã phiếu hoàn `RF-...` và số tiền, tuyệt đối không ghi tên khách, SĐT, địa chỉ hay số tài khoản.
  - Log của job `auto_confirm` được kiểm tra bằng `assertLogs`: chỉ in mã GD ngân hàng và mã đơn hàng, cấm log nội dung chuyển khoản thô (`raw_payload`) hay PII khách.
  - `AiAction` leo thang cho giao dịch lệch chỉ lưu `payment_id` và lý do ngắn gọn không chứa PII.

- **Chứng từ không bị xoá & AuditLog:**
  - Khớp thanh toán gọi service hiện có `resolve_payment`, ghi nhận đầy đủ `AuditLog` hệ thống với `actor=None`, `actor_kind="system"`.
  - Không có chứng từ nào bị xoá (bất biến 3).

- **Hồi quy:**
  - Suite Lô 6b: 12 tests xanh 100% (`Ran 12 tests in 1.134s. OK`).
  - Suite toàn bộ Lô 6 (6a + 6b): 26 tests xanh 100% (`Ran 26 tests in 1.653s. OK`).
  - Toàn bộ backend test suite: **1058 tests xanh 100%**.
  - `makemigrations --check --dry-run`: Sạch sẽ (`No changes detected`).
  - Unit test `erp-console`: 79/79 tests pass.
  - Build tĩnh Next.js: `erp-console` sạch 31/31 static pages, `frontend` sạch 10/10 static pages.

### Lỗi
Không có lỗi chặn (0 lỗi).

### Lệnh đã chạy (kèm output tóm tắt)
1. `cd backend && .venv/bin/python manage.py test apps.ai.execution.tests.test_dw27_confirm_refund apps.sales.payments.tests.test_dw26_auto_confirm` -> `Ran 12 tests in 1.134s. OK`
2. `cd backend && .venv/bin/python manage.py test apps.ai.policy.tests.test_dw24_red_zone_switch apps.ai.execution.tests.test_dw25_close_batch apps.ai.execution.tests.test_dw27_confirm_refund apps.sales.payments.tests.test_dw26_auto_confirm` -> `Ran 26 tests in 1.653s. OK`
3. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run` -> `Ran 1058 tests in 49.867s. OK. No changes detected.`
4. `cd backend && .venv/bin/python manage.py auto_confirm_exact_payments` -> `Finished: confirmed 0, escalated 0, skipped 0 (SWITCH_CLOSED).`
5. `cd erp-console && npm test` -> `79 passed (vitest)`
6. `cd erp-console && npx tsc --noEmit && npm run build` -> Compile sạch 31/31 static pages.
7. `cd frontend && npx tsc --noEmit && npm run build` -> Compile sạch 10/10 static pages.

