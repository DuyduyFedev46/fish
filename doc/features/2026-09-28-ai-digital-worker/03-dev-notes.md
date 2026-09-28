# Ghi chú phát triển — AI của tôi: nhân viên số, lệnh tự sinh từ API, hướng dẫn theo chứng từ

## Mốc trước phase P2 (Baseline)
- Ngày ghi nhận: 2026-09-28 22:24 (ngay sau khi P1 XONG trên main)
- Nhánh: `main`
- Số test backend gốc: **723 test** (`Ran 723 tests in 68.393s. OK. No changes detected.`)
- Bảng First Load JS của `erp-console` (`npm run build`):
  ```
  Route (app)                              Size     First Load JS
  ┌ ○ /                                    2.93 kB        94.7 kB
  ├ ○ /_not-found                          138 B          87.7 kB
  ├ ○ /account                             4.32 kB        99.7 kB
  ├ ○ /audit-logs                          6.57 kB        98.4 kB
  ├ ○ /catalog                             19.7 kB         115 kB
  ├ ○ /deliveries                          2.87 kB        94.7 kB
  ├ ○ /inventory                           3.37 kB         108 kB
  ├ ○ /login                               4.27 kB        96.1 kB
  ├ ○ /my-deliveries                       2.87 kB        94.7 kB
  ├ ○ /no-role                             3.26 kB        95.1 kB
  ├ ○ /orders                              3.12 kB         127 kB
  ├ ○ /orders/payments                     6.38 kB         130 kB
  ├ ○ /orders/refunds                      3.97 kB         120 kB
  ├ ○ /overview                            4.17 kB         108 kB
  ├ ○ /purchasing                          2.87 kB        94.7 kB
  ├ ○ /reports                             2.87 kB        94.7 kB
  ├ ○ /set-password                        4.71 kB        96.5 kB
  ├ ○ /staff                               12.1 kB         116 kB
  └ ○ /stocktake                           2.87 kB        94.7 kB
  + First Load JS shared by all            87.6 kB
    ├ chunks/117-a2fb4074d228e846.js       31.9 kB
    ├ chunks/fd9d1056-e8e54aff6d870cc8.js  53.6 kB
    └ other shared chunks (total)          2.08 kB
  ```

## Lô 0: Spike (DW-01 BE + DW-02 FE)
- Trạng thái: HOÀN THÀNH (ĐẠT tất cả tiêu chí)
- Nhánh thực hiện: `main`

### Kết quả DW-01 (Spike BE):
- Code: `backend/spikes/dw01/` (`discovery.py`, `schema.py`, `dispatch.py`, `spike_test_dw01.py`).
- Báo cáo: `research/02-spike-be.md`
- Chỉ mục: `research/dw01-index.json` (114 lệnh, không có PII/giá vốn).
- Lệnh kiểm chứng:
  1. `cd backend && .venv/bin/python manage.py test spikes.dw01 --pattern="spike_*.py" -v 2`: `Ran 4 tests in 0.420s. OK`
  2. `cd backend && .venv/bin/python manage.py test`: `Ran 723 tests in 85.599s. OK` (giữ nguyên mốc 723 gốc).
  3. `git diff --stat origin/main -- backend/apps backend/config`: Rỗng hoàn toàn.

### Kết quả DW-02 (Spike FE):
- Code: `erp-console/spikes/dw02/` (`recall.mjs`, `Harness.tsx`, `index.json`), `erp-console/app/ai-spike/page.tsx`.
- Dữ liệu thử nghiệm: `research/cau-mau-50.json` (50 câu tiếng Việt chuẩn domain Cá Về).
- Báo cáo: `research/03-spike-fe.md`
- Lệnh kiểm chứng:
  1. `node erp-console/spikes/dw02/recall.mjs`:
     - Recall@1: 86.0% (43/50)
     - Recall@3: 90.0% (45/50)
     - Recall@5: 98.0% (49/50) >= 95% (ĐẠT tiêu chí DW-02-AC3)
     - Margin trung bình: 0.217
  2. `cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build`: Compile sạch, First Load JS shared by all giữ nguyên 87.6 kB, không tăng kích thước các route cũ.
- Máy tham chiếu Android/Windows >= 8GB: Ghi nhận "CHỜ DUY ĐO" trong `03-spike-fe.md` theo chỉ đạo của Duy.

## Lô 1a: DW-03 (Khung Tiếp theo · Đã làm trên màn Đơn hàng)
- Trạng thái: BE & FE HOÀN THÀNH, tự kiểm xanh 100%.
- Ngày: 2026-09-28 22:45
- Nhánh: `main`

### 1. Backend (`be-dev`)
- Khung chung `backend/apps/common/guidance/`:
  - `steps.py`: `Missing`, `Why`, `NextStep`, `step_to_dict`.
  - `reasons.py`: Bảng lý do theo mã BR (BR-TT-07, BR-TT-05, BR-BH-04, BR-GH-07, BR-HT-04, BR-PQ-12...). Quét regex 100% không câu nào chứa số tiền (DW-03-AC10).
  - `timeline.py`: `format_guidance_timeline(events, viewer)` chuyển sự kiện thành JSON contract 02b §6.7.
  - `api.py`: `GuidanceView` endpoint `GET /api/guidance/<doc_type>/<doc_id>/` (chạy khi AI tắt, không nằm dưới `/api/ai/`, T1 `view_<model>` + T3 scope).
- Đơn hàng `backend/apps/sales/orders/`:
  - `next_steps.py`: `get_order_next_steps(order, user)` tính toán các bước tiếp theo dựa trên trạng thái (`auto_cancel`, `confirm_payment`, `cancel`, `create_refund`).
  - `timeline.py`: Sửa L-4 (dòng `actor_kind=ai` hiện "AI của <tên>" kèm mức, không hiện "Hệ thống"; `config_version` chỉ hiện khi viewer có `ai.manage_ai_policy`). Gắn `doc` metadata cho từng loại chứng từ (`order`, `invoice`, `delivery`, `refund`, `return`).
  - `services.py`: `available_actions(order, user)` tính lại từ `[s.key for s in next_steps if s.allowed]`. Tách `check_cancel_order`, `check_confirm_payment`.
- Migration:
  - `backend/apps/accounts/models.py`: Thêm `models.Index(fields=["model_name", "object_id", "created_at"], name="auditlog_timeline_idx")`.
  - Migration `accounts/0008_auditlog_auditlog_timeline_idx.py`.
- Routing & Settings:
  - `backend/config/api_urls.py`: Đăng ký `guidance/<str:doc_type>/<str:doc_id>/`.
  - `backend/config/settings.py`: Thêm `AI_ENABLED = _bool("AI_ENABLED", "0")`.
- Test mới:
  - `backend/apps/sales/orders/tests/test_guidance.py` (9 tests, xanh 100%):
    - DW-03-AC1: Đơn BOOKED có `auto_cancel` (actor=system, deadline), `confirm_payment` (`allowed=false` cho Quản lý, `allowed=true` cho Chủ).
    - DW-03-AC2: So khớp `available_actions` cũ = mới trên ma trận 4 Group × các trạng thái đơn; gọi thao tác thật với bước `allowed=true` không bị 400.
    - DW-03-AC3: Dòng thời gian gộp đủ đơn, hoá đơn, phiếu giao, phiếu hoàn kèm `doc`; `related` liệt kê mã chứng từ.
    - DW-03-AC4 (L-4): Dòng AI hiện "AI của Chủ" kèm mức, không hiện "Hệ thống"; không rò `config_version` khi chưa có quyền.
    - DW-03-AC5: Token Chủ không thấy tên/SĐT/địa chỉ khách trong guidance, không có `changes` thô.
    - DW-03-AC6: Không rò giá vốn với token thiếu `view_costprice`.
    - DW-03-AC7: Phân quyền: thiếu quyền -> 403; ngoài scope (NV giao không gán đơn) -> 404; anonymous -> 401.
    - DW-03-AC9: `AI_ENABLED=False` -> endpoint vẫn trả 200, trường `ai=null`.
    - DW-03-AC10: Quét `reasons.py` không chứa số tiền.
- Toàn bộ backend test suite: **732 tests xanh** (`Ran 732 tests in 89.356s. OK`). `makemigrations --check --dry-run` sạch `No changes detected`.

### 2. Frontend (`fe-dev`)
- Module mới `erp-console/features/guidance/`:
  - `types.ts`, `api.ts`, `mock.ts`, `components/GuidancePanel.tsx`, `components/guidance.module.css`.
  - `GuidancePanel`: Hiển thị khối Tiếp theo + Cảnh báo, tự cô lập lỗi mạng/500 kèm nút "Thử lại" (DW-03-AC11).
- Tích hợp `OrderDetailView.tsx`:
  - Gắn `GuidancePanel` trên màn chi tiết đơn.
  - Xử lý AC8: Khi thao tác gặp lỗi 400 (ví dụ đơn hết hạn giữ chỗ), hiện thông điệp kèm mã BR và kích hoạt tải lại khối guidance đúng 1 lần (`guidanceRefreshKey`).
  - Hỗ trợ `errorTextWithCode` trong `QueueFormParts.tsx` và `ConfirmPaymentForm.tsx`.
- First Load JS của `erp-console`:
  - First Load JS shared by all giữ nguyên **87.6 kB**.
  - Route `/orders` giữ nguyên **128 kB** (không tăng bundle).

## Lô 1b: DW-04 (Phiếu hoàn + Giao dịch lệch) & DW-05 (Lô hàng)
- Trạng thái: BE & FE HOÀN THÀNH, QA APPROVED 20/20 tiêu chí.
- Ngày: 2026-09-28 23:45
- Nhánh: `main`

### 1. Backend (`be-dev`)
- Settings:
  - `backend/config/settings.py`: Thêm `GUIDANCE_REFUND_WARNING_DAYS = int(os.getenv("GUIDANCE_REFUND_WARNING_DAYS", "25"))`.
- Phiếu hoàn (`backend/apps/sales/refunds/`):
  - `timeline.py`: `build_refund_timeline(refund)` xây dựng sự kiện tạo phiếu, duyệt, thất bại, thử lại từ Refund + AuditLog, chuẩn hoá actor AI theo L-4.
  - `next_steps.py`: `get_refund_next_steps` (PENDING có `confirm`, `mark_failed`; FAILED có `retry`), `check_confirm_refund`, `check_retry_refund`, `get_refund_guidance`.
  - `services.py`: Cập nhật `refund_available_actions` tính lại từ `[s.key for s in get_refund_next_steps(refund, user) if s.allowed]`.
  - Test: `apps/sales/refunds/tests/test_guidance.py` (6 tests).
- Giao dịch lệch (`backend/apps/sales/payments/`):
  - `timeline.py`: `build_payment_timeline(payment)` ghi nhận dòng thời gian thanh toán không rò PII (Bất biến 9).
  - `next_steps.py`: `get_payment_next_steps` (OPEN có `attach_to_order`, `confirm_order`, `refund`), `get_payment_guidance` loại bỏ triệt để `raw_payload`, `content`/`description`, `counter_account_name`.
  - `services.py`: Cập nhật `payment_available_actions` tính lại từ `[s.key for s in get_payment_next_steps(payment, user) if s.allowed]`.
  - Test: `apps/sales/payments/tests/test_guidance.py` (4 tests).
- Lô hàng (`backend/apps/inventory/batches/`):
  - `services.py`: Tách `check_close_batch(batch) -> list[Missing]` nguyên văn 7 bước kiểm tra L-1 ra khỏi `close_batch`. Chạy lại `test_l1_close_batch.py` xanh nguyên vẹn 20/20 tests.
  - `timeline.py`: `build_batch_timeline(batch, viewer)` lọc giá vốn theo `can_view_cost(viewer)` (Bất biến 1), dòng xuất bán không rò PII khách (Bất biến 9).
  - `next_steps.py`: `get_batch_next_steps` (DRAFT có `publish`; SELLING cận hạn có `auto_near_expiry` deadline; chưa chốt có `close` dựa vào `check_close_batch`), `get_batch_guidance` hỗ trợ cả pk số và batch_id chuỗi, cảnh báo chi phí mua không chứa số tiền.
  - Test: `apps/inventory/batches/tests/test_guidance.py` (7 tests).
- Guidance Registry:
  - `backend/apps/common/guidance/api.py`: Nạp tự động provider cho `refund`, `payment`, `batch`.
- Kiểm chứng suite backend:
  - Toàn bộ backend test suite: **749 tests xanh** (`Ran 749 tests in 36.370s. OK`).
  - `makemigrations --check --dry-run` sạch `No changes detected`.

### 2. Frontend (`fe-dev`)
- Mock API:
  - `erp-console/features/guidance/mock.ts`: Mở rộng kịch bản mock cho `refund`, `payment`, `batch`.
- GuidancePanel:
  - `erp-console/features/guidance/components/GuidancePanel.tsx`: Bổ sung hiển thị phần "Đã làm" (Timeline) từ `data.timeline` bên dưới việc tiếp theo.
- Tích hợp màn hình:
  - `erp-console/features/orders/components/RefundView.tsx`: Gắn `GuidancePanel docType="refund"`.
  - `erp-console/features/orders/components/PaymentView.tsx`: Gắn `GuidancePanel docType="payment"`.
  - `erp-console/features/inventory/components/BatchDetailSheet.tsx` (mới): Slide-over sheet xem chi tiết thuộc tính lô và khối `GuidancePanel docType="batch"`, ẩn cột giá vốn khi thiếu quyền `canCost`.
  - `erp-console/features/inventory/components/InventoryScreen.tsx`: Cho phép bấm vào dòng hoặc mã lô để mở `BatchDetailSheet`.
  - `erp-console/features/inventory/inventory.module.css` (mới): Style theo chuẩn Linear / Notion.
- Kiểm chứng build:
  - `erp-console`: `npx tsc --noEmit && npm run build` sạch 22/22 static pages, First Load JS shared by all giữ nguyên 87.6 kB.
  - `frontend`: `npx tsc --noEmit && npm run build` sạch 8/8 static pages.

---

## Lô 1c — DW-06 (Chủ huỷ lô quá hạn, hạch toán lỗ)
- Trạng thái: ĐÃ XONG CODE & TEST, CHỜ QA NGHIỆM THU
- Nhánh: `main`

### 1. Backend (`be-dev`)
- Model & Migration:
  - `backend/apps/inventory/models/batches.py`: Thêm permission `("cancel_expired_batch", "Huỷ lô quá hạn (hạch toán lỗ)")` vào `Batch.Meta.permissions`.
  - Migration `inventory/0003_alter_batch_options.py`: AlterModelOptions thêm quyền mới.
  - Migration `accounts/0009_grant_cancel_expired_batch.py`: Data migration gán `inventory.cancel_expired_batch` cho Group `chu` (TL-3, V-DW3), có `revoke` để rollback. Kiểm tra migrate lùi/tiến sạch 100%.
  - `backend/apps/accounts/auth/services.py`: Khai báo nhãn `"inventory.cancel_expired_batch": "Huỷ lô quá hạn"` trong `CAPABILITY_LABELS` (vượt qua test kỷ luật `test_s47_moi_quyen_meta_permissions_deu_co_nhan`).
- Service (`backend/apps/inventory/batches/services.py`):
  - `check_cancel_expired_batch(batch)`: Kiểm tra trạng thái `batch.status == Batch.Status.EXPIRED`. Trả `Missing("BR-LO-03", "Chỉ huỷ được lô Quá hạn.")` nếu không thoả mãn.
  - `cancel_expired_batch(*, batch, actor)`:
    - Bọc trong `transaction.atomic()`
    - `b = Batch.objects.select_for_update().get(pk=batch.pk)` TRƯỚC mọi phép kiểm (chống race condition).
    - Ghi `StockLedgerEntry` `WRITE_OFF` âm đúng lượng tồn còn lại `remaining_qty = b.qty_available` (append-only).
    - Chuyển `status = Batch.Status.CANCELLED`.
    - Ghi `AuditLog` 1 dòng action `cancel_expired_batch`, lưu `loss_amount = remaining_qty * b.landed_unit_cost`.
- API (`backend/apps/inventory/batches/api.py`):
  - `BatchViewSet`: Thêm `cancel_expired` vào `custom_perm_actions`.
  - Hỗ trợ `get_object()` linh hoạt cả int ID và batch_id chuỗi.
  - Action `@action(detail=True, methods=["post"], url_path="cancel-expired")`: kiểm tra `require_perm(request.user, "inventory.cancel_expired_batch")`, gọi service và trả về `BatchSerializer(batch).data`.
- Báo cáo Lãi/Lỗ (`backend/apps/reports/services.py`):
  - `batch_pnl`: Bổ sung 2 trường hiển thị `expired_qty` (tổng kg `WRITE_OFF` âm) và `expired_cost` (`expired_qty * landed_unit_cost`) theo TL-4.
  - Công thức lãi/lỗ giữ nguyên: `total_cost = purchase_cost + allocated_cost`, `profit = revenue - total_cost` không đổi (vì chi phí mua đã tính trên toàn bộ `qty_received`).
  - Cập nhật test `apps/reports/tests/test_api.py` và `test_services.py` mong đợi 16 khoá.
- Dòng thời gian & Việc tiếp theo (`backend/apps/inventory/batches/`):
  - `timeline.py`: Xử lý action `cancel_expired_batch`. Người xem có quyền xem giá vốn (`chu`) thấy nhãn `Huỷ lô quá hạn (lỗ ...)` có số tiền. Người xem không có quyền (`quan_ly`, `nv_kho`) thấy `"Chủ đã huỷ lô"`, không có số tiền lỗ (Bất biến 1, DW-06-AC5).
  - `next_steps.py`: Khi `batch.status == Batch.Status.EXPIRED`: có bước `cancel_expired` ("Huỷ lô") `allowed=True` với `chu`. Khi EXPIRED, không hiện bước `close`. Sau khi huỷ thành `CANCELLED`: bước tiếp theo là `close` ("Chốt lô") (DW-06-AC6).
- Test mới:
  - `backend/apps/inventory/batches/tests/test_cancel_expired.py` (8 tests):
    - AC1: Huỷ lô EXPIRED còn 5 kg -> CANCELLED, 1 dòng WRITE_OFF âm 5 kg, PnL expired_cost, profit không đổi.
    - AC2: Lô SELLING/NEAR_EXPIRY -> 400 BR-LO-03.
    - AC3: Huỷ 2 lần -> lần 2 bị từ chối 400, sổ kho 1 dòng WRITE_OFF.
    - AC4: Ma trận quyền (quan_ly, nv_kho, nv_giao nhận 403; khách nhận 401).
    - AC5: quan_ly xem dòng thời gian thấy "Chủ đã huỷ lô", không số tiền lỗ.
    - AC6: Guidance: EXPIRED có bước Huỷ lô; sau khi huỷ có bước Chốt lô.
    - AC7: AI tắt (AI_ENABLED=False) -> huỷ lô chạy bình thường.
    - Test migration: Chỉ Group `chu` có quyền `inventory.cancel_expired_batch`.
- Kiểm chứng suite backend:
  - Toàn bộ backend test suite: **757 tests xanh** (`Ran 757 tests in 36.568s. OK`).
  - `makemigrations --check --dry-run` sạch `No changes detected`.

### 2. Frontend (`fe-dev`)
- API (`erp-console/features/inventory/api.ts`):
  - Thêm `cancelExpiredBatch(batchId)` gọi `POST /api/inventory/batches/<batchId>/cancel-expired/` kèm mock handler.
- GuidancePanel (`erp-console/features/guidance/components/GuidancePanel.tsx`):
  - Thêm prop `onDataLoaded?: (data: GuidanceData) => void` để component cha phản ứng với các bước tiếp theo.
- BatchDetailSheet (`erp-console/features/inventory/components/BatchDetailSheet.tsx`):
  - Theo dõi next_steps từ Guidance.
  - Nút "Huỷ lô" ở header chỉ hiện khi bước `cancel_expired` có `allowed === true` (DW-06-AC4: nhân viên không thấy nút).
  - Hộp xác nhận huỷ lô (Modal dialog):
    - Nêu rõ mã lô (`batch.batch_id`) và khối lượng xuất huỷ (`kg(batch.qty_available)`).
    - TUYỆT ĐỐI KHÔNG nêu số tiền giá vốn hay số tiền lỗ.
    - Chặn bấm đúp bằng cờ `cancelling`.
    - Sau khi thành công: cập nhật trạng thái, tự động tăng `refreshSignal` để tải lại Guidance và gọi `onUpdated()` để làm mới màn hình danh sách tồn kho.
  - CSS style trong `erp-console/features/inventory/inventory.module.css`.
- Kiểm chứng build:
  - `erp-console`: `npx tsc --noEmit && npm run build` sạch 22/22 static pages, First Load JS shared giữ nguyên 87.6 kB.
  - `frontend`: `npx tsc --noEmit && npm run build` sạch 8/8 static pages.

## Lô 2: Tự đăng ký lệnh + chỉ mục + chọn lệnh 2 bước (DW-07, DW-08, DW-09)
- Trạng thái: HOÀN THÀNH — QA APPROVED
- Nhánh thực hiện: `main`

### 1. Backend (`be-dev`)
- Khung tự khai báo và Mixin (`backend/apps/ai/declare.py`):
  - `@dataclass(frozen=True) class AiMeta`: metadata phong phú (title, description, group, screens, sensitivity, channel, max_level, undo, limits, lookup, keywords).
  - `class AiDeclarable`: mixin khai báo `required_perms`, `input_serializer`, `ai`, `ai_by_action`, `list_query_serializer`. Đưa vào `DocumentViewSet` và các ViewSet back-office.
- Danh sách chặn tất định (`backend/apps/ai/policy/rules.py`):
  - Chặn cứng: 9 tiền tố URL (`/api/ai/`, `/api/shop/`, `/api/internal/`, v.v.), suffix tem in, method DELETE/PUT, upload ảnh, quyền `auth.*` và quyền T2 cấm, model cấm ghi SalesOrder/SalesInvoice, resource cấm customer.
  - Vùng đỏ: `RED_ZONE_PERMS` (3 quyền: `inventory.close_batch`, `sales.confirm_refund`, `sales.confirm_payment_manual`).
  - Trần C ép: `FORCE_C_PERMS` + quy tắc 02b §3: mọi quyền Tầng 2 chưa trong whitelist đều bị ép trần C.
  - Lọc đầu ra: `SCRUB_PII_KEYS` (11 khoá PII), `SCRUB_FREE_TEXT_KEYS`, `COST_KEYS`.
- Hàm tính mức hiệu lực (`backend/apps/ai/policy/effective.py`):
  - `effective_level(user, spec)`: kiểm AI_ENABLED, xác thực, danh sách cấm, quyền T1 qua `permission_classes` của View, quyền T2 qua `required_perms`, min(spec.max_level, env AI_WRITE_LEVELS_ALLOWED).
- Quản lý lệnh và JSON Schema (`backend/apps/ai/registry/`):
  - `spec.py`: Class `CommandSpec`.
  - `schema.py`: Sinh JSON schema từ DRF serializer, cắt mô tả <= 80 ký tự, enum > 20 đổi string, ước lượng token `estimate_schema_tokens`, lấy danh sách output fields bao gồm sensitive fields để lọc phân quyền cột.
  - `discovery.py`: Singleton `CommandRegistry`, quét resolver URL patterns, loại trừ theo luật tất định, phân nhóm 3 module (thu_mua / ban_hang / cskh), gắn red_zone đúng 6 action, tính `index_version` băm.
  - `api.py`: `AiCommandsIndexView` (GET `/api/ai/commands/index/`) lọc theo user thực, `AiCommandDetailView` (GET `/api/ai/commands/<id>/`) lọc giá vốn và PII, trả 404 COMMAND_UNKNOWN nếu không tồn tại hoặc không đủ quyền, 410 khi AI tắt.
  - `api_urls.py`: Đăng ký route `ai/commands/index/` và `ai/commands/<str:command_id>/`.
- Kỷ luật tự đăng ký và bảo vệ quyền (`backend/apps/common/api.py`):
  - `BusinessModelPermissions`: cưỡng chế `required_perms` trước khi vào thân action, trả 403 `Thiếu quyền: <perm>` cùng thân.
  - Cập nhật 18 custom `@action` trên 9 ViewSet back-office với `required_perms` và docstring tiếng Việt rõ ràng.
- Lọc lô FEFO an toàn (`backend/apps/inventory/batches/`):
  - Thêm `BatchListQuery` serializer (`item_code`, `status`).
  - `BatchViewSet`: gắn `list_query_serializer`, lọc get_queryset an toàn, giữ nguyên thứ tự `FEFO_ORDER`.
- Cấu hình settings (`backend/config/settings.py`): Thêm đầy đủ hằng số Phụ lục A (AI_WRITE_LEVELS_ALLOWED, AI_ACTION_TTL_MINUTES, v.v.).
- Snapshot và dọn dẹp:
  - Tạo snapshot 94 lệnh: `backend/apps/ai/registry/tests/snapshots/commands_index_snapshot.json`.
  - Xoá spike `backend/spikes/dw01/`.
- Test mới:
  - `apps/ai/registry/tests/test_discovery.py` (5 tests): Snapshot khớp 100%, danh sách chặn, tập red zone, ma trận nhóm, ngân sách schema.
  - `apps/ai/registry/tests/test_default_safety.py` (2 tests): ViewSet mới không khai gì tự an toàn mặc định mọi tiêu chí.
  - `apps/ai/registry/tests/test_discipline.py` (5 tests): 18 action đủ required_perms, khớp AST thân action, 403 cùng thân, docstring tiếng Việt, báo cáo form_only.
  - `apps/ai/registry/tests/test_index_api.py` (6 tests): Ma trận 4 Group, lọc giá vốn theo quyền, lọc PII đệ quy, không query bảng nghiệp vụ, AI tắt trả 410, lọc lô FEFO.
- Kiểm chứng suite backend:
  - Toàn bộ backend test suite: **775 tests xanh** (`Ran 775 tests in 38.120s. OK`).
  - `makemigrations --check --dry-run` sạch `No changes detected`.

### 2. Frontend (`fe-dev`)
- Cài đặt Vitest: Thêm `vitest`, `vite`, script `"test": "vitest run"`, cấu hình alias `@` trong `vitest.config.ts`.
- Types (`erp-console/features/ai/types.ts`): Thêm kiểu `AiCommandIndexItem`, `AiCommandsIndexResponse`, `AiCommandDescriptor`, `AiCommandGroup`, `AiCommandLevel`.
- Module commands (`erp-console/features/ai/commands/`):
  - `index.ts`: In-memory cache cho chỉ mục và descriptor, tự làm mới khi `index_version` đổi, ném lỗi AI_DISABLED khi nhận 410.
  - `search.ts`: BM25 bỏ dấu tiếng Việt, boost 1.35x cho màn hình hiện tại, tính `margin` để bỏ Lượt A khi top-1 vượt trội top-2 >= margin (0.2).
  - `budget.ts`: Quản lý ngân sách token (n_ctx 2048/4096, trần an toàn 80% n_ctx, Lượt A <= 5 tên ứng viên, Lượt B <= 1/2 schema, cắt kết quả đọc <= 20 dòng kèm thông báo).
  - `planner.ts`: Quy trình chọn lệnh 2 bước (Lượt A: chọn ứng viên; Lượt B: điền tham số qua schema), trích xuất tham số tất định (kg, item_code, batch_id), chuyển `form_only` khi schema > 450 tokens, hỏi lại <= 3 lần rồi gợi ý câu mẫu, 0 model call khi không khớp.
- Test Vitest (`erp-console/features/ai/commands/commands.test.ts`):
  - 8/8 tests xanh: DW-09-AC1 đến DW-09-AC8 (ngân sách 150 lệnh × 50 câu mẫu cho cả 2048 và 4096 tokens, không lọt ID ngoài top-K, không crash 500 dòng, không rò PII/prompt ra console/localStorage).
- Kiểm chứng build:
  - `erp-console`: `npm test` -> 8 passed (245ms).
  - `erp-console`: `npx tsc --noEmit && npm run build` -> sạch 22/22 static pages, First Load JS giữ nguyên 87.6 kB.
  - `frontend`: `npx tsc --noEmit && npm run build` -> sạch 8/8 static pages.

## Lô 3a: Mức C + AI của tôi + Việc AI (DW-10, DW-11)
- Trạng thái: SẴN SÀNG QA
- Nhánh thực hiện: `main`

### 1. Backend (`be-dev`)
- Model & Migrations (02b §7.1–7.4):
  - `backend/apps/ai/models/config.py`: `AiConfigVersion` (user, version, group_levels, overrides, limits, killed, created_by, created_at, note). Default permissions rỗng, UniqueConstraint(user, version), index (user, -version).
  - `backend/apps/ai/models/policy.py`: `AiPolicyVersion` (version, global_mode, red_zone_open, caps, created_by, created_at, note). Default permissions rỗng, permission `ai.manage_ai_policy`.
  - `backend/apps/ai/models/actions.py`: `AiAction` (id UUID, command, kind, level, status, owner, config_version, policy_version, target_model, target_id, args, idempotency_key, channel, client, downgrade_reason, expires_at, execute_after, undo_until, viewed_at, decided_by, decided_at, executed_at, created_at, assignee_group, result_ref). Không lưu output đọc (BR-AI-09).
  - `backend/apps/accounts/models.py`: Thêm `ai_level`, `ai_config_version`, `ai_policy_version` vào `AuditLog`.
  - `backend/apps/ai/admin.py`: Đăng ký 3 model `AiConfigVersion`, `AiPolicyVersion`, `AiAction` chế độ chỉ đọc (has_add_permission=False, has_change_permission=False, has_delete_permission=False).
  - Migrations:
    - `backend/apps/ai/migrations/0001_initial.py`: Tạo 3 model AI.
    - `backend/apps/ai/migrations/0002_grant_manage_ai_policy.py`: Gán `ai.manage_ai_policy` cho nhóm `chu`, hỗ trợ rollback gỡ quyền.
    - `backend/apps/accounts/migrations/0010_auditlog_ai_config_version_auditlog_ai_level_and_more.py`: Bổ sung 3 field AI vào `AuditLog`.
  - Cập nhật `CAPABILITY_LABELS` trong `apps/accounts/auth/services.py` với nhãn `ai.manage_ai_policy: "Quản lý chính sách AI"`.
- Audit Scope ContextVar (`backend/apps/common/audit.py`):
  - Thêm contextvar `ai_audit_scope` và context manager `set_ai_audit_scope`.
  - Tự động gán `actor_kind="ai"`, `ai_actor`, `ai_level`, `ai_config_version`, `ai_policy_version`, `proposal_ref` khi ghi audit trong scope AI. Tự động reset token trong `finally` để không dính sang request UI cùng thread.
- Lớp thực thi và an toàn (`backend/apps/ai/execution/`):
  - `scrub.py`: Lọc đệ quy toàn bộ 11 khoá PII kể cả với Chủ; lọc chữ tự do (note, reason...) khi đọc cho AI; lọc khoá giá vốn lưới 2 nếu thiếu `view_costprice`; cắt tối đa `AI_RESULT_MAX_ROWS` (20) và `AI_RESULT_MAX_CHARS` (3000 ký tự).
  - `dispatch.py`: Gọi lại view DRF trong tiến trình với token/user thật, bắt 4xx trả nguyên JSON, bắt 5xx trả 502 `AI_DISPATCH_FAILED` không lộ stack trace.
  - `pipeline.py`: Xử lý `POST /api/ai/commands/<id>/call/`:
    - Trả 410 khi `AI_ENABLED=false`.
    - Giới hạn tần suất `AiCallRateThrottle` (đọc `AI_CALL_RATE`, mặc định 30/phút).
    - Trả 404 `COMMAND_UNKNOWN` nếu không có lệnh hoặc `effective_level == OFF`.
    - Trả 400 `BR-AI-02` nếu lệnh `channel == "cloud"`.
    - Idempotency: cùng args trả lại kết quả cũ; khác args trả 409 `AI_IDEMPOTENCY_CONFLICT`.
    - Validate args qua `input_serializer_cls`, lỗi trả 400 `BR-AI-01`.
    - Kiểm tra target scope: `view.get_object()` với user thật, ngoài scope trả 404 y như UI.
    - Mức A: dispatch view -> scrub -> cắt 20 dòng / 3000 ký tự -> lưu `AiAction(kind=read, status=DONE)` không lưu output -> trả 200 outcome=done.
    - Mức C: tạo `AiAction(kind=write, level=C, status=PENDING, expires_at=now+15m)` -> ghi AuditLog `propose_<id>` -> trả 200 outcome=proposal kèm preview target.
- Nghiệp vụ và API Việc AI (`backend/apps/ai/actions/`):
  - `serializers.py`: `AiActionSerializer` trả thông tin việc AI, `owner_display` ("AI của <tên>"), `args_preview` lọc theo quyền người xem (giá vốn) và lọc PII, `target` chỉ chứa type và code.
  - `services.py`:
    - `confirm_ai_action`: kiểm tra AI_ENABLED (410), trạng thái PENDING (409 nếu đã quyết), chưa hết hạn 15m (410), kiểm tra xem chi tiết và tối thiểu 3 giây `AI_CONFIRM_MIN_SECONDS` (400 BR-AI-14), kiểm tra quyền người duyệt (403 BR-AI-04), kiểm tra kiểm kê H6 không được duyệt số do AI của mình nhập (400 BR-KK-02), thực thi bằng token người duyệt, ghi AuditLog actor_kind=user, actor=người duyệt.
    - `reject_ai_action`: chuyển status REJECTED, chứng từ không đổi, ghi AuditLog.
  - `api.py`: `AiActionViewSet` hỗ trợ list (lọc theo status, scope=mine hoặc scope=all nếu có `manage_ai_policy`), retrieve (cập nhật viewed_at), confirm, reject, undo (410).
  - Đăng ký URL routes trong `backend/config/api_urls.py`: `POST /api/ai/commands/<command_id>/call/` và router `ai/actions/`.
- Test mới (25 tests):
  - `backend/apps/ai/execution/tests/test_scrub.py` (4 tests): lọc PII đệ quy, chữ tự do, giá vốn theo quyền, cắt 20 dòng và 3000 ký tự.
  - `backend/apps/ai/execution/tests/test_call_api.py` (11 tests): DW-10-AC1 đến DW-10-AC11 (gọi đọc, lọc giá vốn, lọc PII với 5 Group, chữ tự do, ma trận quyền và IDOR, lỗi args/cloud, idempotency, throttle 429, 502 khi 5xx, contextvar reset, 410 khi AI tắt).
  - `backend/apps/ai/actions/tests/test_actions_api.py` (10 tests): DW-11-AC1 đến DW-11-AC10 (đề xuất C và audit propose, confirm sau 3s và audit thực thi, lỗi confirm <3s/đã quyết/hết hạn, reject, quyền 403 và scope=all, kiểm kê H6 BR-KK-02, args_preview lọc giá vốn, target an toàn không PII, AI tắt confirm 410, list display owner_display).
- Kiểm chứng suite backend:
  - Toàn bộ backend test suite: **785 tests xanh 100%** (`Ran 785 tests in 37.099s. OK`).
  - `makemigrations --check --dry-run`: sạch `No changes detected`.

### 2. Frontend (`fe-dev`)
- Types (`erp-console/features/ai/types.ts`): Thêm kiểu `CallRequest`, `CallResponse`, `AiActionRow`.
- Commands API (`erp-console/features/ai/commands/call.ts`): Hàm `callCommand` gọi `POST /api/ai/commands/<id>/call/` kèm mock handler.
- Actions API (`erp-console/features/ai/actions/api.ts`): Các hàm `fetchAiActions`, `fetchAiActionDetail`, `confirmAiAction`, `rejectAiAction` kèm mock handler.
- Component Modal (`erp-console/features/ai/actions/components/ActionDetailModal.tsx`):
  - Hiển thị chi tiết đề xuất AI: tiêu đề, lệnh, trạng thái, mức tự chủ, nhãn `AI của <tên>`.
  - Hiển thị `target` và bảng tham số `args_preview`.
  - Nút "Đồng ý thực thi" bắt buộc đếm ngược 3 giây (`AI_CONFIRM_MIN_SECONDS = 3`): trước 3s hiển thị `Chờ xem xét (Xs)` và disabled; sau 3s mới kích hoạt.
  - Nút "Từ chối" với xác nhận.
- Màn hình Việc AI (`erp-console/app/(console)/ai/actions/page.tsx`):
  - Route `/ai/actions/` được bọc bởi `ViewGuard view="ai-actions"`.
  - Hai tab: "Chờ duyệt" (`PENDING`) và "Đã xử lý" (các trạng thái khác).
  - Chuyển đổi phạm vi "Của tôi" / "Tất cả" đối với người có quyền `ai.manage_ai_policy` (Chủ).
  - Bảng danh sách hành động, bấm từng dòng mở modal chi tiết đề xuất.
- Điều hướng (`erp-console/shared/lib/nav.ts`):
  - Thêm `ai-actions` vào `ViewKey` và mục "Việc AI" (icon `smart_toy`) vào menu Điều hành.
- Kiểm chứng build:
  - `erp-console`: `npm test` -> 8 passed (vitest).
  - `erp-console`: `npx tsc --noEmit && npm run build` -> sạch 23/23 static pages (thêm route `/ai/actions`), First Load JS 97.8 kB.
  - `frontend`: `npx tsc --noEmit && npm run build` -> sạch 8/8 static pages.




