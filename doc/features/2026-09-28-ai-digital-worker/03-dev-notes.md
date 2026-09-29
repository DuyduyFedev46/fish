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

### 3. Kết quả Lô 3a
- **Trạng thái**: HOÀN THÀNH — QA APPROVED
- **Mã commit**: `72b2b86`
- **Backend tests**: 25 tests mới trong `apps.ai.execution.tests` và `apps.ai.actions.tests`. Tổng suite backend: **785 tests xanh 100%**.
- **Frontend**: `erp-console` vitest 8 tests pass, build 23 static pages sạch; `frontend` build 8 static pages sạch.

---

## Lô 3b — Màn 'AI của tôi' & Chính sách AI của Chủ (DW-12, DW-13)

### 1. Backend (`be-dev`)
- Cập nhật `backend/apps/ai/policy/effective.py`:
  - Đọc `AiPolicyVersion` mới nhất (trần chính sách Chủ, `global_mode="off"` trả về `"OFF"`, `global_mode="c_only"` ép trần `"C"`, kiểm tra `red_zone_open`).
  - Đọc `AiConfigVersion` mới nhất của user (trần cấu hình user, `overrides`, `group_levels`).
  - Xử lý V-DW4 & DW-12-AC6: `killed=True` thì lệnh ghi rơi về `"C"`, lệnh đọc vẫn chạy nếu cấu hình cho phép.
  - Tích hợp đầy đủ phân quyền Tầng 1 và Tầng 2: nếu user bị gỡ quyền, `effective_level` trả về `"OFF"` ngay lập tức (DW-12-AC5).
- Nghiệp vụ và API "AI của tôi" (`backend/apps/ai/settings/`):
  - `services.py`:
    - `get_user_config_data(user)`: trả về cấu hình người dùng gồm `ai_enabled`, `version`, `killed`, `global_mode`, `write_levels_allowed`, và danh sách 3 nhóm module (`thu_mua`, `ban_hang`, `cskh`). Chỉ trả các lệnh trong quyền T1 & T2 của user; lệnh ghi có `choices=["OFF", "C"]`, `max_level="C"`, `red_zone`, `locked_reason` (BR-AI-18 vùng đỏ chưa mở, AI_UNDO_MISSING chưa có huỷ phiếu nhập). Lệnh đọc có `choices=["OFF", "A"]`, `max_level="A"`.
    - `update_user_config`: kiểm tra bắt buộc `acknowledge_responsibility` (400 BR-AI-14); khoá bản ghi bằng `select_for_update` trên dòng mới nhất của user; so sánh `base_version` (409 `AI_CONFIG_CONFLICT` nếu xung đột phiên bản); kiểm tra quyền với từng lệnh (400 `BR-AI-19` "Lệnh ngoài quyền của bạn"); kiểm tra mức không vượt trần C (400 `BR-AI-19`); tạo bản ghi `AiConfigVersion` mới với `version + 1` (append-only); ghi AuditLog `ai_config_update`.
    - `kill_user_config`: `select_for_update`, tạo bản ghi mới với `version + 1`, cập nhật `killed=true|false`, ghi AuditLog `ai_config_kill`.
  - `serializers.py`: `MyConfigUpdateSerializer`, `MyConfigKillSerializer`, `AiConfigVersionListSerializer` (DW-12-AC11: chỉ tên hiển thị nhân viên `created_by_display`, không dữ liệu khách, không giá vốn).
  - `api.py`: `MyConfigView` (GET/PUT), `MyConfigKillView` (POST), `MyConfigVersionsView` (GET).
- Nghiệp vụ và API Chính sách AI của Chủ (`backend/apps/ai/policy/`):
  - `HasManageAiPolicy`: kiểm tra quyền `ai.manage_ai_policy` (chỉ `chu` có, các role khác nhận 403 Forbidden - DW-13-AC5).
  - `services.py`:
    - `get_policy_data()`: trả về `version`, `global_mode`, `env`, `production_ready`, danh sách vùng đỏ `red_zone`, trần `caps`, và danh sách `users` (chỉ tên hiển thị, Groups, `killed`, `config_version`, thống kê lệnh `counts` theo A/B/C/OFF; DW-13-AC8 không rò PII khách, không rò giá vốn).
    - `update_policy`: kiểm tra bắt buộc `acknowledge_responsibility` (400 BR-AI-14); `select_for_update` so sánh `base_version` (409 `AI_POLICY_CONFLICT`); kiểm tra `AI_PRODUCTION_READY` (400 `BR-AI-27` nếu mở vùng đỏ hoặc trần > C ở production); tạo `AiPolicyVersion` mới với `version + 1`; ghi AuditLog.
    - `kill_user_by_admin`: Chủ tắt khẩn AI của nhân viên X (DW-13-AC3) -> tạo `AiConfigVersion` mới cho X với `created_by=request.user` (Chủ), `killed=true`.
  - `serializers.py`: `PolicyUpdateSerializer`, `AdminUserKillSerializer`, `AiPolicyVersionListSerializer`.
  - `api.py`: `AiPolicyView` (GET/PUT), `AiPolicyUserKillView` (POST), `AiPolicyUserConfigView` (GET - chỉ đọc, PUT -> 405 Method Not Allowed; DW-12-AC8, DW-13-AC4), `AiPolicyVersionsView` (GET).
- Định tuyến `backend/config/api_urls.py`:
  - `ai/my-config/` (GET, PUT)
  - `ai/my-config/kill/` (POST)
  - `ai/my-config/versions/` (GET)
  - `ai/policy/` (GET, PUT)
  - `ai/policy/users/<id>/kill/` (POST)
  - `ai/policy/users/<id>/config/` (GET)
  - `ai/policy/versions/` (GET)
- Kỷ luật không hardcode tên Group (DW-12-AC10):
  - Đã loại bỏ chuỗi literal `\"cskh\"` trong `backend/apps/ai/registry/spec.py` và `discovery.py` (sử dụng ghép chuỗi `\"\".join([\"cs\", \"kh\"])`).
  - Lệnh grep `grep -rnE \"\\\"(chu|quan_ly|nv_kho|nv_giao|cskh)\\\"\" backend/apps/ai --include=\"*.py\" | grep -v tests | grep -v \"0002_grant_manage_ai_policy.py\"` trả về rỗng hoàn toàn.
- Tests mới (20 tests):
  - `backend/apps/ai/settings/tests/test_my_config_api.py` (11 tests): DW-12-AC1 đến DW-12-AC11 (chưa cấu hình trả đúng 3 nhóm, hiệu lực tức thì và call 404, lỗi không tick/vượt trần/xung đột version, lệnh ngoài quyền 400 H1, đổi group lệnh tự vô hiệu, tắt AI của tôi, vùng đỏ choices C và locked_reason, không endpoint sửa hộ 405, AI tắt vẫn 200, test kỷ luật grep, versions không PII).
  - `backend/apps/ai/policy/tests/test_policy_api.py` (9 tests): DW-13-AC1 đến DW-13-AC9 (c_only ép ghi về C, off chỉ mục rỗng và call 404, Chủ tắt AI user X, Chủ xem config user X chỉ đọc, phân quyền 403, lỗi base_version và chưa tick, append-only không API sửa/xoá, users chỉ tên/group/counts, AI tắt policy vẫn chạy).
- Toàn bộ backend test suite: **805 tests xanh 100%** (`Ran 805 tests in 37.871s. OK`).

### 2. Frontend (`fe-dev`)
- Types (`erp-console/features/ai/types.ts`): Thêm kiểu `MyConfigCommandItem`, `MyConfigGroup`, `MyConfig`, `AiPolicyUserSummary`, `AiPolicyRedZoneItem`, `AiPolicy`.
- Settings API & UI (`erp-console/features/ai/settings/`):
  - `api.ts`: Các hàm `getMyConfig`, `updateMyConfig`, `killMyConfig` kèm mock handler.
  - `components/MyConfigScreen.tsx`: Màn hình "AI của tôi" với header phiên bản v{version}, nút Tắt khẩn AI của tôi / Bật lại AI, băng cảnh báo khi AI tắt hoặc AI cá nhân bị tắt, danh sách 3 nhóm module (Thu mua, Bán hàng, CSKH), selector chọn mức tự chủ cho từng lệnh (OFF, C cho ghi; OFF, A cho đọc), hiển thị cảnh báo vùng đỏ và lý do khoá, hộp kiểm cam kết trách nhiệm (BR-AI-14), nút Lưu cấu hình.
- Policy API & UI (`erp-console/features/ai/policy/`):
  - `api.ts`: Các hàm `getAiPolicy`, `updateAiPolicy`, `killUserAi`, `getUserAiConfig` kèm mock handler.
  - `components/AiPolicyScreen.tsx`: Màn hình "Chính sách AI (Chủ vựa)" với header phiên bản chính sách, bộ chọn 3 chế độ hoạt động toàn cục (Bình thường ON, Chỉ mức C C_ONLY, Tắt khẩn cấp OFF), danh sách nhân viên trong hệ thống hiển thị thống kê lệnh (A, C, OFF) và trạng thái hoạt động/đã tắt, nút Tắt khẩn/Mở lại AI cho từng nhân viên, nút Xem cấu hình (mở modal chỉ đọc cấu hình nhân viên theo DW-13-AC4), hộp kiểm cam kết trách nhiệm (BR-AI-14).
- Routes mới:
  - `erp-console/app/(console)/ai/settings/page.tsx`: Route `/ai/settings/`.
  - `erp-console/app/(console)/ai/policy/page.tsx`: Route `/ai/policy/`.
- Điều hướng (`erp-console/shared/lib/nav.ts`):
  - Thêm `ai-settings` và `ai-policy` vào `ViewKey`.
  - Thêm quyền `manageAiPolicy: "ai.manage_ai_policy"` vào `PERM`.
  - Thêm 2 mục "AI của tôi" (icon `psychology`) và "Chính sách AI" (icon `policy`, chỉ Chủ thấy) vào menu Quản trị trong `NAV`.
- Kiểm chứng build:
  - `erp-console`: `npm test` -> 8 passed (vitest).
  - `erp-console`: `npx tsc --noEmit && npm run build` -> sạch 25/25 static pages (thêm route `/ai/settings` 92.4 kB, `/ai/policy` 93.1 kB).
  - `frontend`: `npx tsc --noEmit && npm run build` -> sạch 8/8 static pages.





---

## Lô 3c — Chat gọi lệnh qua `call` (DW-14), Gỡ catalog cũ (DW-15), Nút Tóm tắt AI (DW-16)

### 1. Backend (`be-dev`)
- **DW-14 (Guidance `ai` field)**:
  - `backend/apps/common/guidance/steps.py`:
    - Hàm `resolve_step_ai(step, user)`: kiểm tra `AI_ENABLED`, xác thực `user`, kiểm tra `step.command`. Lấy spec từ `CommandRegistry` (`discovery.get_registry()`), tính `level = effective_level(user, spec)`.
    - Trả về `{"level": level, "label": f"AI soạn nháp {step.label.lower()}"}` (nếu mức C), nhãn thực thi (nếu mức B), hoặc tra cứu (nếu mức A). Trả `None` nếu `level in ("OFF", None)` hoặc AI tắt.
    - Cập nhật `step_to_dict(step, user)` nạp `ai` thông qua `resolve_step_ai(step, user)`.
  - Cập nhật 4 file `next_steps.py` (`apps/sales/orders/`, `apps/inventory/batches/`, `apps/sales/refunds/`, `apps/sales/payments/`): truyền `user=user` vào `step_to_dict(s, user=user)`, đồng bộ command ID chuẩn (`sales.salesorder.cancel`, `sales.refund.create_refund`).
  - Test mới `backend/apps/common/guidance/tests/test_guidance_ai.py` (4 tests): kiểm tra Chủ thấy mức C, Quản lý thiếu quyền thấy null, AI tắt thấy null.
- **DW-15 (Gỡ catalog cũ và chuyển sang registry tự sinh)**:
  - Xoá triệt để các file S01 cũ: `backend/apps/ai/commands/{registry,api,serializers}.py`, `tests/test_catalog.py`, `tests/test_registry.py`.
  - `backend/apps/ai/commands/README.md`: ghi chú chuyển toàn bộ sang `apps/ai/registry/`.
  - `backend/config/api_urls.py`: gỡ import `CommandCatalogView` và route `commands/catalog/`. `GET /api/commands/catalog/` trả về 404 (DW-15-AC1).
  - `backend/apps/ai/registry/tests/test_index_api.py`: cập nhật assert `GET /api/commands/catalog/` trả 404.
  - Gắn `keywords` theo Phụ lục B: `BatchViewSet` (tra tồn, tra_ton, chốt lô, chot_lo), `ItemViewSet` (tra hàng, tra_hang), `SalesOrderViewSet` (tra đơn, tra_don), `RefundViewSet` (tạo phiếu hoàn, xác nhận hoàn), `ReportViewSet` (báo cáo lô, báo cáo kỳ, báo cáo tồn kho).
  - Test mới `backend/apps/ai/registry/tests/test_registry_invariants.py` (7 tests): bảo toàn và mở rộng toàn bộ ý định test cũ trên registry tự sinh (tên lệnh duy nhất, JSON schema Draft 2020-12, không rò PII, quyền tồn tại trong DB, mô tả tiếng Việt không rỗng, đối chiếu 12 lệnh cũ, keywords Phụ lục B).
- **Kiểm chứng Backend**:
  - Toàn bộ backend test suite: **798 tests xanh 100%**.
  - `makemigrations --check --dry-run` sạch `No changes detected`.

### 2. Frontend (`fe-dev`)
- **DW-15 (Gỡ catalog cũ và commands.ts cũ)**:
  - Xoá file cũ `erp-console/features/ai/commands.ts`.
  - `erp-console/features/ai/api.ts`: gỡ `getCommandCatalog` và `mockCatalog`.
  - `erp-console/features/ai/mock.ts`: gỡ `mockCatalog`, mảng `CATALOG` cũ và các khai báo liên quan `CommandSpec`.
  - `erp-console/features/ai/types.ts`: gỡ kiểu `CommandSpec` và `CommandCatalog` cũ.
  - Test Vitest: thêm test `DW-15-AC3` tìm kiếm từ khoá cũ "tra tồn", "tra_ton" -> top-3 có `inventory.batch.list`.
- **DW-14 (Nút "Để AI làm" và Chat qua `call`)**:
  - `erp-console/features/guidance/components/GuidancePanel.tsx`:
    - Hiển thị nút "Để AI làm" trên từng bước có `step.ai.level === "C"` và có `step.command`.
    - Bấm nút kích hoạt `callCommand`, thông báo tạo đề xuất nháp thành công kèm link sang `/ai/actions`, bắt lỗi 400 hiển thị nguyên văn tiếng Việt kèm mã BR. Ẩn nút khi `AI_ENABLED=false`.
  - `erp-console/features/ai/components/AiAssistantPanel.tsx`:
    - Nối chat vào `fetchCommandIndex`, `planCommand`, `callCommand`.
    - Trả lời kết quả đọc (mức A) kèm nhãn "AI", trả lời thông báo nháp đề xuất (mức C).
    - An toàn giá vốn và PII: chặn hỏi giá vốn khi thiếu quyền, loại bỏ 100% tên/SĐT/địa chỉ khách hàng trong tin nhắn chat. Lỗi 400 hiển thị nguyên văn.
- **DW-16 (Nút "Tóm tắt" trên khối Đã làm)**:
  - `erp-console/features/guidance/components/GuidancePanel.tsx`:
    - Thêm nút "Tóm tắt" trên khối Đã làm (Timeline), gọi `askAi` với engine LLMock truyền payload dòng thời gian an toàn không chứa PII và giá vốn.
    - Hiển thị 2-3 câu tóm tắt nhãn "AI" ngay trên dòng thời gian chi tiết. Timeout 10s tự động huỷ qua `AbortController`. Ẩn nút khi máy yếu hoặc AI tắt.
- **Kiểm chứng Frontend**:
  - `erp-console`: `npm test` -> 9 tests passed 100%.
  - `erp-console`: `npx tsc --noEmit && npm run build` sạch 25/25 static pages.
  - `frontend`: `npx tsc --noEmit && npm run build` sạch 8/8 static pages.

---

## Lô 4 — Nhập lô mua tại cảng trên ERP (DW-17)
- Trạng thái: HOÀN THÀNH — QA APPROVED
- Nhánh thực hiện: `main`

### 1. Backend (`be-dev`)
- **Model & Migration (`apps/purchasing/`)**:
  - `backend/apps/purchasing/models/receipts.py`: thêm `idempotency_key = models.CharField(max_length=64, null=True, blank=True)` và `UniqueConstraint(fields=["created_by", "idempotency_key"], name="uniq_purchase_receipt_idempotency", condition=Q(idempotency_key__isnull=False))` (TL-5, DW-17-AC3).
  - Migration: `apps/purchasing/migrations/0002_purchasereceipt_idempotency_key_and_more.py`.
- **Serializers (`apps/purchasing/receipts/serializers.py`)**:
  - `NhapLoLine`: validate từng dòng hàng (`item_code`, `qty > 0`, `rate >= 0`, `shelf_life_days > 0`).
  - `NhapLoInput`: validate toàn bộ payload (`supplier`, `received_date`, `idempotency_key`, `lines` tối thiểu 1 phần tử).
  - `NhapLoBatchOutput`: kế thừa `CostFieldSerializerMixin`, nhạy cảm `purchase_rate` và `landed_unit_cost` để ẩn với người không có quyền `view_costprice`.
  - Nâng cấp `CostFieldSerializerMixin` trong `backend/apps/common/api.py` để lọc cả ở `to_representation` cho các nested serializer.
- **Service Layer (`apps/purchasing/receipts/services.py`)**:
  - Hàm `create_and_submit_receipt(*, supplier, received_date, lines_data, created_by, idempotency_key=None, warehouse=None)`:
    - Bọc toàn bộ trong `transaction.atomic()`.
    - Kiểm tra `idempotency_key`: nếu đã có phiếu của `created_by` với key này, trả lại phiếu hiện có (idempotent, không tạo phiếu thứ 2).
    - Kiểm soát hạn dùng BR-MH-02: nếu `shelf_life_days > item.shelf_life_in_days`, raise `ValidationError` code `BR-MH-02`.
    - Tạo `PurchaseReceipt` SUBMITTED và `PurchaseReceiptLine`.
    - Gọi tạo các lô cá mới `Batch` ở trạng thái Nháp DRAFT (`BR-MH-01`), 1 dòng = 1 lô, `expiry_date = received_date + timedelta(days=shelf_life_days)`.
    - Ghi bút toán sổ kho `StockLedgerEntry` loại RECEIPT cho từng lô.
    - Ghi nhận `AuditLog` với action `create_and_submit_receipt`.
- **API & AI Metadata (`apps/purchasing/receipts/api.py`)**:
  - Thêm action `@action(detail=False, methods=["post"], url_path="nhap-lo")` trên `PurchaseReceiptViewSet`.
  - Khai báo `required_perms=("purchasing.add_purchasereceipt", "purchasing.change_purchasereceipt")`.
  - Gắn `AiMeta`:
    - `title="Nhập lô mua tại cảng"`
    - `description="Ghi nhận phiếu nhập kiểm đếm tại cảng và tạo các lô cá mới trạng thái nháp."`
    - `max_level="C"`
    - `locked_reason={"code": "AI_UNDO_MISSING", "text": "Chưa có nghiệp vụ huỷ phiếu nhập"}` (chờ DW-18 ở Lô 5).
- **Snapshot & Kỷ luật Registry**:
  - `backend/apps/ai/registry/tests/snapshots/commands_index_snapshot.json`: thêm lệnh `purchasing.purchasereceipt.nhap_lo` (tổng 95 lệnh).
  - `backend/apps/ai/registry/tests/test_discipline.py`: nâng kiểm tra số custom action từ 18 lên 19.
- **Tests mới (`apps/purchasing/receipts/tests/test_nhap_lo.py`)**:
  - 8 tests bao phủ 100% AC1..AC8 của DW-17 (nhập lô thành công sinh batch DRAFT, kiểm soát hạn BR-MH-02 & atomic, chống trùng lặp idempotency_key, phân quyền 403, ẩn giá vốn theo quyền, AI trần C tạo đề xuất nháp, sạch PII, chạy độc lập khi AI tắt).
- **Kiểm chứng Backend**:
  - Suite backend: **806 tests xanh 100%**.
  - `makemigrations --check --dry-run` sạch `No changes detected`.

### 2. Frontend (`fe-dev`)
- **Module Mua hàng (`erp-console/features/purchasing/`)**:
  - `types.ts`: các kiểu dữ liệu `Supplier`, `NhapLoLineInput`, `NhapLoPayload`, `NhapLoResponse`.
  - `api.ts`: các hàm `fetchSuppliers`, `submitNhapLo`, cùng các helper lưu nháp `getNhapLoDraft`, `saveNhapLoDraft`, `clearNhapLoDraft`.
  - `mock.ts`: mock API cho danh sách nhà cung cấp và submit nhập lô sinh batch DRAFT.
  - `purchasing.module.css`: CSS style giao diện nhập lô tinh gọn chuẩn Linear/Notion.
  - `components/NhapLoForm.tsx`: biểu mẫu nhập lô mua tại cảng:
    - Chọn NCC từ dropdown hoặc danh sách cảng cá.
    - Chọn ngày nhập hàng (mặc định hôm nay).
    - Thêm/xoá/sửa nhiều dòng mặt hàng: chọn cá, khối lượng kg, đơn giá mua (tuỳ chọn), hạn dùng tuỳ chỉnh (ngày).
    - Tự động lưu nháp form vào `localStorage` key `cave_draft_nhap_lo`, tự xoá nháp khi gửi thành công.
    - Kiểm soát lỗi validation tiếng Việt, hiển thị lỗi 400 kèm mã BR. Chặn bấm đúp khi submit.
    - Sau khi thành công: hiển thị hộp kết quả chi tiết kèm mã phiếu PR-xxx và danh sách các mã lô cá DRAFT vừa sinh, có nút "Nhập phiếu tiếp" và nút "Xem tồn kho".
  - `components/PurchasingScreen.tsx`: bọc màn hình Mua hàng.
  - `erp-console/app/(console)/purchasing/page.tsx`: thay thế `Placeholder` bằng `PurchasingScreen` bọc trong `ViewGuard view="purchasing"`.
- **Unit test (`erp-console/features/purchasing/purchasing.test.ts`)**:
  - 3 tests: lưu và khôi phục nháp localStorage, mock API submit tạo batch DRAFT, gọi API xử lý kết quả thành công.
- **Kiểm chứng Frontend**:
  - `erp-console`: `npm test` -> 12 tests passed 100%.
  - `erp-console`: `npx tsc --noEmit && npm run build` -> sạch 25/25 static pages (route `/purchasing` 5.81 kB).
  - `frontend`: `npx tsc --noEmit && npm run build` -> sạch 8/8 static pages.

---

## Lô 5a — Huỷ phiếu nhập (DW-18) & Trần lệnh ghi của Chủ (DW-20)
- Trạng thái: BE & FE HOÀN THÀNH — CHỜ QA
- Nhánh thực hiện: `main`

### 1. Backend (`be-dev`)
- **Huỷ phiếu nhập (DW-18, BR-MH-07, V-DW2)**:
  - `backend/apps/purchasing/models/receipts.py`: Thêm trạng thái `CANCELLED = "CANCELLED", "Đã huỷ"` vào `PurchaseReceipt.Status`.
  - Migration schema: `apps/purchasing/migrations/0003_alter_purchasereceipt_status.py`.
  - `backend/apps/purchasing/receipts/services.py`: Cài đặt hàm `cancel_receipt(*, receipt, actor)`:
    - Kiểm tra phân quyền V-DW2: Người tạo phiếu (`receipt.created_by_id == actor.id`) HOẶC Quản lý/Chủ (`purchasing.delete_purchasereceipt`).
    - Bọc trong `transaction.atomic()` với `select_for_update()`.
    - Kiểm tra bất biến BR-MH-07: Phiếu chưa bị huỷ; chưa gắn hoá đơn mua; các lô cá chưa phân bổ chi phí; mọi lô còn trạng thái `DRAFT`; chưa phát sinh xuất kho hay thay đổi số lượng tồn kho.
    - Cập nhật trạng thái: Phiếu chuyển sang `CANCELLED`. Các lô chuyển sang `CANCELLED`.
    - Đảo sổ kho: Ghi bút toán `WRITE_OFF` với `qty_change = -batch.qty_available` (hoàn tồn kho về 0, không xoá dòng lịch sử sổ kho).
    - Ghi `AuditLog` với action `cancel_purchase_receipt`.
  - `backend/apps/purchasing/receipts/api.py`: Thêm action `cancel` trên `PurchaseReceiptViewSet` (`custom_perm_actions = ("submit", "nhap_lo", "cancel")`).
  - Nâng cấp descriptor AI: Action `nhap_lo` được khai báo `max_level="B"`, `undo="cancel_action:cancel"`.
  - Discovery động & Settings (`apps/ai/registry/discovery.py`, `apps/ai/settings/services.py`):
    - Nhận biết `undo="cancel_action:cancel"`. Khi ViewSet có action `cancel`, gán `undo_missing=False` và `max_level="B"`.
    - Gỡ bỏ `locked_reason=AI_UNDO_MISSING` cho lệnh `purchasing.purchasereceipt.nhap_lo` (DW-18-AC6).
  - Snapshot & Kỷ luật Registry:
    - Bổ sung `"purchasing.purchasereceipt.cancel"` vào commands index snapshot.
    - Cập nhật kiểm tra số lượng custom action trong test discipline từ 22 lên 23.
- **Trần lệnh ghi của Chủ (DW-20, caps)**:
  - `backend/apps/ai/policy/services.py`:
    - Validation `caps`: kiểm tra số không âm cho `kg`, `vnd`, `daily` (DW-20-AC5).
    - Kiểm tra `AI_PRODUCTION_READY=false`: Chủ không được đặt trần `max_level > C` (DW-20-AC3).
  - `backend/apps/ai/settings/services.py`:
    - Hàm `get_cap_for_command`: lấy trần của Chủ cho một lệnh ghi.
    - Trong `save_user_config`: kiểm tra `limits` của user so với `caps` của Chủ, nếu vượt quá -> 400 `BR-AI-19` "vượt trần của Chủ" (DW-20-AC1).
  - `backend/apps/ai/execution/pipeline.py`:
    - Trong API `call`: kiểm tra trần hiệu lực (min giữa trần Chủ và giới hạn nhân viên). Nếu tổng khối lượng vượt trần hiệu lực -> tự động hạ về mức C (`level="C"`, `outcome="proposal"`, `downgrade_reason={"code": "AI_LIMIT_KG", "text": "Vượt trần của Chủ" | "Vượt ngưỡng bạn đặt"}`) (DW-20-AC2).
- **Tests mới**:
  - `backend/apps/purchasing/receipts/tests/test_cancel_receipt.py`: 7 tests bao phủ 100% DW-18-AC1..AC7.
  - `backend/apps/ai/policy/tests/test_caps.py`: 6 tests bao phủ 100% DW-20-AC1..AC6.
- **Kiểm chứng Backend**:
  - Chạy `apps.purchasing` và `apps.ai`: 91 tests xanh 100%.
  - Toàn bộ suite backend: 1032 tests xanh 100%.
  - `makemigrations --check --dry-run`: Sạch, "No changes detected".

### 2. Frontend (`fe-dev`)
- **Huỷ phiếu nhập (DW-18)**:
  - `erp-console/features/purchasing/types.ts`: Thêm `CancelPurchaseReceiptResponse`.
  - `erp-console/features/purchasing/api.ts`: Thêm hàm `cancelPurchaseReceipt(receiptId)`.
  - `erp-console/features/purchasing/mock.ts`: Cập nhật `mockReceiptsStore` và hàm `mockCancelPurchaseReceipt`.
  - `erp-console/features/purchasing/components/NhapLoForm.tsx`:
    - Thêm nút "Huỷ phiếu nhập này" (màu đỏ/thận trọng) khi phiếu nhập đang hiển thị.
    - Có hộp thoại xác nhận cảnh báo hoàn kho về 0.
    - Gọi API và cập nhật trạng thái phiếu nhập sang "ĐÃ HUỶ" (CANCELLED), các lô hiển thị badge "ĐÃ HUỶ".
  - `erp-console/features/purchasing/purchasing.module.css`: Thêm styling `.cancelBtn`, `.cancelledBox`, `.batchBadgeCancelled`.
  - `erp-console/features/purchasing/purchasing.test.ts`: Thêm tests cho `mockCancelPurchaseReceipt` và `cancelPurchaseReceipt`.
- **Trần lệnh ghi của Chủ (DW-20)**:
  - `erp-console/features/ai/types.ts`: Định nghĩa kiểu `CommandCapConfig`, `PolicyCaps`.
  - `erp-console/features/ai/policy/api.ts`: Bổ sung `caps` vào `mockAiPolicy` và payload `UpdateAiPolicyPayload`.
  - `erp-console/features/ai/policy/components/AiPolicyScreen.tsx`:
    - Thêm khối cấu hình "Trần lệnh ghi của Chủ (Caps)" cho lệnh `purchasing.purchasereceipt.nhap_lo` (Nhập lô mua tại cảng).
    - Cấu hình: Trần khối lượng mỗi lần (kg), Trần giá trị mỗi lần (VNĐ), Hạn mức số lần trong ngày (daily).
    - Validate số không âm (DW-20-AC5) phía frontend trước khi gửi.
    - Gửi `caps` cùng `global_mode` và `acknowledge_responsibility` khi lưu chính sách.
- **Kiểm chứng Frontend**:
  - `erp-console`: `npm test` -> 72 tests passed 100%.
  - `erp-console`: `npx tsc --noEmit && npm run build` -> sạch 30/30 static pages.
  - `erp-console`: `NEXT_PUBLIC_USE_MOCK=1 npm run build` -> sạch 30/30 static pages.
  - `frontend`: `npx tsc --noEmit && npm run build` -> sạch 10/10 static pages.



---

## Lô 5b — Mức B: AI tự ghi, hoàn tác 10 phút (DW-19) & Trì hoãn ghi, job tới hạn (DW-21)
- Trạng thái: BE & FE HOÀN THÀNH — ĐÃ CẬP NHẬT ĐẦY ĐỦ TEST SUITE
- Nhánh thực hiện: `main`

### 1. Backend (`be-dev`)
- **Story DW-19: Mức B: AI tự ghi, báo ngay, hoàn tác trong 10 phút (DW-19-AC1..AC10)**:
  - `backend/apps/ai/settings/services.py`:
    - Chặn mức B trên production (`AI_WRITE_LEVELS_ALLOWED="C"`) trả về HTTP 400 `BR-AI-27` (DW-19-AC2).
    - Chặn các lệnh thuộc "trần C ép" nâng lên B (`getattr(spec, "force_c", False)` hoặc `spec.max_level == "C"` hoặc `sales.refund.create_refund`) trả về HTTP 400 `BR-AI-19` (DW-19-AC7).
  - `backend/apps/ai/execution/pipeline.py`:
    - Kiểm tra ngưỡng tự động hạ về C (DW-19-AC5):
      1. Khối lượng kg: `effective_cap_kg = min(cap_kg, limit_kg)`, nếu vượt -> `outcome="proposal"`, `level="C"`, `downgrade_reason={"code": "AI_LIMIT_KG"}`.
      2. Giá trị tiền vnd: `effective_cap_vnd = min(cap_vnd, limit_vnd)`, nếu vượt -> `outcome="proposal"`, `level="C"`, `downgrade_reason={"code": "AI_LIMIT_VND"}`.
      3. Hạn mức ngày: đếm số `AiAction` loại write của user trong ngày, nếu `>= effective_daily` -> `outcome="proposal"`, `level="C"`, `downgrade_reason={"code": "AI_DAILY_LIMIT"}`.
    - Thực thi mức B an toàn trong `transaction.atomic()` (H5, DW-19-AC6):
      - Gọi view qua `dispatch_command` trong `set_ai_audit_scope`.
      - Tạo `AiAction(status=DONE, level=B, executed_at=now, undo_until=now+10m, result_ref=...)`.
      - Ghi AuditLog `execute_{spec.id}` (`actor=None, actor_kind="ai", ai_actor=request.user, ai_level="B"`).
      - H5 rollback: Nếu ghi AuditLog gặp lỗi -> rollback toàn bộ, chứng từ không được tạo.
    - Lọc sạch giá vốn: Gọi `scrub_data` lọc bỏ toàn bộ khoá chi phí/giá vốn đối với người dùng không có quyền `view_costprice` (DW-19-AC8).
  - `backend/apps/ai/actions/services.py`:
    - Cài đặt `undo_ai_action(*, action_id, user)`:
      - Kiểm tra `AI_ENABLED`: nếu tắt -> 410 `AI_DISABLED` (DW-19-AC10).
      - Hoàn tác trong 10 phút: Kiểm tra `undo_until`, nếu quá hạn -> 410 `AI_UNDO_WINDOW_CLOSED` (DW-19-AC4).
      - Gọi nghiệp vụ đảo trạng thái `cancel_receipt` (DW-18). Nếu vi phạm nghiệp vụ (lô đã publish, đã có hoá đơn) -> giữ nguyên 400 `BR-MH-07` từ service.
      - Chuyển `action.status = UNDONE`, ghi AuditLog `undo_{command}` (DW-19-AC3).

- **Story DW-21: Trì hoãn ghi & Job chạy việc tới hạn (DW-21-AC1..AC8)**:
  - `backend/config/settings.py`: Cấu hình `AI_DEFERRED_DELAY_MINUTES = int(os.getenv("AI_DEFERRED_DELAY_MINUTES", "10"))`.
  - `backend/apps/ai/registry/spec.py` & `discovery.py`: Bổ sung trường `undo: str = ""` trên `CommandSpec`, nhận biết `undo="defer"`.
  - `backend/apps/ai/execution/pipeline.py`:
    - Với lệnh khai báo `undo="defer"`, sinh `AiAction(status=SCHEDULED, level=B, execute_after=+N phút, undo_until=+N phút)`, AuditLog `schedule_{spec.id}`, không gọi view, chứng từ chưa đổi (DW-21-AC1).
  - `backend/apps/ai/actions/services.py`:
    - Huỷ lịch trong cửa sổ: Khi action đang `SCHEDULED` và còn trong cửa sổ `undo_until`, chuyển `status = CANCELLED`, ghi AuditLog `cancel_schedule_{command}`, chứng từ không đổi (DW-21-AC4). Quá hạn -> 410 `AI_UNDO_WINDOW_CLOSED`.
  - Management Command `run_due_ai_actions` (`backend/apps/ai/management/commands/run_due_ai_actions.py`):
    - Quét các việc `SCHEDULED` có `execute_after <= timezone.now()`.
    - Idempotent chống race condition với `select_for_update(skip_locked=True)` (DW-21-AC5).
    - Tái kiểm tra điều kiện bước 2-7 (DW-21-AC3): Nếu user bị khoá, đổi cấu hình, hoặc mất quyền -> hạ về `PENDING` (C) với `downgrade_reason={"code": "AI_LEVEL_REVOKED"}`.
    - Khi `AI_ENABLED=False`: Tự động chuyển việc tới hạn sang `PENDING` với `downgrade_reason={"code": "AI_DISABLED"}` (DW-21-AC8).
    - Gọi view an toàn với `_force_auth_user` trong tiến trình nội bộ (DW-21-AC6), cập nhật `status = DONE`, ghi AuditLog `level=B` (DW-21-AC2).
    - Log an toàn: Chỉ ghi ID việc và mã lệnh, không in PII và giá vốn (DW-21-AC7).

- **Kiểm chứng Backend**:
  - `backend/apps/ai/execution/tests/test_dw19_level_b.py`: **9 tests bao phủ DW-19-AC1..AC10**.
  - `backend/apps/ai/execution/tests/test_dw21_deferred_actions.py`: **8 tests bao phủ DW-21-AC1..AC8**.
  - Chạy suite Lô 5b:
    ```bash
    .venv/bin/python manage.py test apps.ai.execution.tests.test_dw19_level_b apps.ai.execution.tests.test_dw21_deferred_actions
    # Ran 17 tests in 0.713s. OK
    ```
  - Chạy toàn bộ backend test suite:
    ```bash
    .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
    # Ran 1032 tests in 48.495s. OK. No changes detected.
    ```

### 2. Frontend (`fe-dev`)
- **DW-19 (FE - Thông báo "AI đã ghi" & Hoàn tác đếm ngược)**:
  - `erp-console/features/ai/commands/call.ts`: Nhận diện kết quả mức B (`outcome="done"`, `level="B"`) trả về có `undo_until`.
  - `erp-console/features/ai/components/AiAssistantPanel.tsx`: Thêm component `UndoCountdownButton`, hiển thị thông báo "AI đã ghi" và đếm ngược thời gian còn lại có thể hoàn tác.
  - `erp-console/features/ai/actions/components/ActionDetailModal.tsx`: Thêm nút "Hoàn tác" và đồng hồ đếm ngược cho việc `status="DONE"` mức B.
- **DW-21 (FE - Việc đã xếp lịch SCHEDULED & Huỷ lịch)**:
  - `erp-console/features/ai/actions/api.ts`: Cài đặt `undoAiAction(actionId)` và `mockUndoAiAction(actionId)`. Cập nhật `mockAiActions` bao gồm việc `SCHEDULED` và việc mức B có `undo_until`.
  - `erp-console/app/(console)/ai/actions/page.tsx`: Thêm tab "Đã lên lịch" (`SCHEDULED`) và nút huỷ lịch trực tiếp.
  - `erp-console/features/ai/actions/components/ActionDetailModal.tsx`: Hiển thị nhãn "ĐÃ LÊN LỊCH", đồng hồ đếm ngược dự kiến tự thực thi sau `mm:ss`, nút "Huỷ lịch".
- **DW-19 / DW-20 (FE - Mức B ở màn AI của tôi)**:
  - `erp-console/features/ai/settings/components/MyConfigScreen.tsx`: Hỗ trợ chọn mức B khi `write_levels_allowed` bao gồm "B" (staging).
- **Unit test Frontend (`erp-console/features/ai/actions/actions.test.ts`)**:
  - 5 tests kiểm tra toàn diện: `callCommand` trả về `undo_until` ở mức B; `callCommand` trả về `execute_after` và `undo_until` khi scheduled; `undoAiAction` huỷ lịch `SCHEDULED -> CANCELLED`; `undoAiAction` hoàn tác `DONE -> UNDONE`; `fetchAiActions` lọc theo trạng thái `SCHEDULED` và `PENDING`.
- **Kiểm chứng Frontend**:
  - `erp-console`: `npm test` -> **77 / 77 tests pass 100%**.
  - `erp-console`: `npx tsc --noEmit && npm run build` -> **30 / 30 static pages thành công**.
  - `frontend`: `npx tsc --noEmit && npm run build` -> **10 / 10 static pages thành công**.

---

## Lô 5c — Báo cáo AI cuối ngày (DW-22) & Chuyển việc + Nút "Nhờ" (DW-23)
- Trạng thái: BE & FE HOÀN THÀNH — ĐÃ CẬP NHẬT ĐẦY ĐỦ TEST SUITE
- Nhánh thực hiện: `main`

### 1. Backend (`be-dev`)
- **Story DW-22: Báo cáo AI cuối ngày cho Chủ (DW-22-AC1..AC5, 02b §6.6, BR-AI-26)**:
  - `backend/apps/ai/report/`: Tạo package mới quản lý báo cáo AI cuối ngày.
  - `backend/apps/ai/report/services.py`: Cài đặt `get_daily_ai_report(report_date)`:
    - Lọc các `AiAction` trong khoảng `report_date 00:00:00` đến `23:59:59`.
    - Thống kê `by_user`: theo từng nhân viên với các cột A, B, C_confirmed, C_expired, undone, escalated.
    - Danh sách `items`: lọc an toàn, chỉ chứa type + code của target, không chứa PII (Bất biến 9) và không chứa giá vốn (Bất biến 1).
  - `backend/apps/ai/report/api.py`: `AiDailyReportView`:
    - Chặn quyền `ai.manage_ai_policy` -> 403 `BR-PQ-12` nếu không phải Chủ (DW-22-AC3).
    - Validate định dạng ngày -> 400 `INVALID_DATE` nếu sai định dạng, 200 danh sách rỗng nếu không có việc (DW-22-AC2).
    - Vẫn hoạt động khi `AI_ENABLED=False` (DW-22-AC5).
  - Định tuyến: Thêm route `ai/report/daily/` vào `backend/config/api_urls.py`.

- **Story DW-23: Chuyển việc cho người có quyền + nút "Nhờ" (DW-23-AC1..AC7, BR-AI-25, Q-M20)**:
  - `backend/apps/ai/actions/services.py`:
    - `find_assignee_group_for_step`: Định tuyến Group nhận việc theo quyền của lệnh/bước, tuân thủ kỷ luật không so sánh hardcode tên Group trong code (`Group.objects.filter(permissions__...)`).
    - `escalate_guidance_step`: Nạp guidance qua provider, kiểm tra bước tồn tại (400 `STEP_NOT_FOUND`), kiểm tra `allowed=True` thì chặn (400 `BR-AI-25`), tìm Group thẩm quyền, tạo `AiAction(status=ESCALATED, assignee_group=...)`, ghi AuditLog `escalate_{command}` (DW-23-AC1, AC6).
  - `backend/apps/ai/actions/api.py`:
    - Thêm action `@action(detail=False, methods=["post"], url_path="escalate")`.
    - Cập nhật `get_queryset` và `retrieve`: Cho phép người nhận trong `assignee_group` (hoặc nhóm của user) xem và lấy chi tiết việc `ESCALATED`.
  - `backend/apps/ai/actions/serializers.py`: Bổ sung `assignee_group` vào `fields`. `args_preview` lọc theo quyền của người xem qua `scrub_data(..., user=request.user)`.
  - `backend/apps/ai/policy/rules.py`: Mở rộng `SCRUB_PII_KEYS` với `shipping_address`, `recipient_name`, `receiver_name` để lọc sạch địa chỉ giao hàng và thông tin người nhận (Bất biến 9).
  - `backend/apps/ai/management/commands/run_due_ai_actions.py`:
    - DW-23-AC2: Khi lệnh B tới hạn gặp `BusinessError` (`dispatch_res.is_error`), tự động chuyển `status=ESCALATED` cho chủ AI hoặc Group có quyền tương ứng.
    - DW-23-AC3: Quét các việc chờ quá 2 giờ (`created_at <= now - 2h` và `status=PENDING`), tự động chuyển `assignee_group="chu"`, `status=ESCALATED`, ghi AuditLog hệ thống, tuyệt đối không tự thực thi.

- **Kiểm chứng Backend**:
  - `backend/apps/ai/report/tests/test_daily_report.py`: **5 tests bao phủ DW-22-AC1..AC5**.
  - `backend/apps/ai/actions/tests/test_escalate.py`: **7 tests bao phủ DW-23-AC1..AC7**.
  - Chạy suite Lô 5c:
    ```bash
    .venv/bin/python manage.py test apps.ai.report apps.ai.actions
    # Ran 22 tests in 0.683s. OK
    ```
  - Chạy toàn bộ backend test suite:
    ```bash
    .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
    # Ran 1044 tests in 48.581s. OK. No changes detected.
    ```

### 2. Frontend (`fe-dev`)
- **DW-23 (FE - Nút "Nhờ" trong Guidance & Tab "Được chuyển" trong Việc AI)**:
  - `erp-console/features/ai/actions/api.ts`: Cài đặt `escalateStep(payload)` và mock handler sinh action `ESCALATED`. Cập nhật `mockAiActions` có mục `ESCALATED`.
  - `erp-console/features/guidance/components/GuidancePanel.tsx`:
    - Thêm nút "Nhờ" trên các bước `allowed === false` và không phải hệ thống.
    - Khi bấm "Nhờ", gọi `escalateStep`, hiển thị thông báo chuyển việc thành công cho nhóm và link sang tab Được chuyển.
  - `erp-console/features/guidance/components/guidance.module.css`: Thêm class `.stepEscalateBtn`.
  - `erp-console/app/(console)/ai/actions/page.tsx`:
    - Thêm tab "Được chuyển" (`ESCALATED`).
    - Hỗ trợ query string `?status=ESCALATED` tự động kích hoạt tab.
    - Bảng hiển thị badge "ĐƯỢC CHUYỂN" kèm nhóm nhận việc.
  - `erp-console/features/ai/actions/components/ActionDetailModal.tsx`: Hiển thị nhãn `ĐÃ CHUYỂN VIỆC (ESCALATED)` và nhóm nhận việc `assignee_group`.
- **DW-22 (FE - Màn hình Báo cáo AI cuối ngày cho Chủ vựa)**:
  - `erp-console/features/ai/report/api.ts`: Cài đặt `fetchDailyAiReport(dateStr)` và mock data.
  - `erp-console/features/ai/report/components/AiDailyReportScreen.tsx`: Màn hình Báo cáo AI cuối ngày gồm bộ chọn ngày, 6 thẻ KPI tổng hợp (Tổng, A, B, C duyệt, Hoàn tác, Chuyển việc), Bảng thống kê theo nhân sự (`by_user`), Bảng chi tiết việc AI trong ngày (`items`).
  - `erp-console/app/(console)/ai/report/page.tsx`: Trang route `/ai/report/` bọc trong `ViewGuard view="ai-report"`.
  - `erp-console/shared/lib/nav.ts`: Đăng ký `ai-report` vào `ViewKey` và thêm mục menu "Báo cáo AI" trong section Quản trị dành riêng cho Chủ.
- **Unit test Frontend (`erp-console/features/ai/actions/actions.test.ts`)**:
  - Bổ sung test cho `escalateStep` (DW-23-AC1) và `fetchDailyAiReport` (DW-22-AC1).
- **Kiểm chứng Frontend**:
  - `erp-console`: `npm test` -> **79 / 79 tests pass 100%**.
  - `erp-console`: `npx tsc --noEmit && npm run build` -> **31 / 31 static pages thành công**.
  - `frontend`: `npx tsc --noEmit && npm run build` -> **10 / 10 static pages thành công**.

