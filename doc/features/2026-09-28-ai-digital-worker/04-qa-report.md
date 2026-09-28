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
