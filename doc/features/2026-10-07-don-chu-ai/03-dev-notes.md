# Lô dọn chữ AI — ghi chú hiện thực

## FE (ERP và Shop)

**Cờ AI (W39).** `aiVisible(me)` ở `erp-console/shared/lib/features.ts` = cờ build đứng đầu `&&` rồi `me?.ai_features_enabled === true`; `me` chưa tải = tắt.
Đã thay ở 12 file đọc cờ (GuidancePanel, escalation.ts, GuidanceEscalate, ConfirmationAiBlock, AuditLogScreen, AiDocBlockGate, AiProposalsRow, Shell, AiBlockFrame, DetailPage, AiFeatureGuard, nav.ts).
Ngoài `features.ts` (và test) không file nào import `AI_FEATURES_ENABLED` (test grep ở `features.test.ts`). `escalatableStep(data, me)` nhận thêm `me`.
`Me` / `Viewer` thêm `ai_features_enabled?`. Mock `/me`: mặc định true; `sessionStorage["caveve_mock_be_ai"]="off"` giả lập BE tắt.

**Dọn chữ.** Nội dung: bỏ cột "AI" và ghi chú "AI soạn nháp" khi tắt (`entryNote(row, aiOn)`). `DetailPage` aria-label "Lịch sử" khi không có khe AI. `nav.ts` mô tả Nhật ký bỏ chữ AI.
`Timeline.tsx` và `GuidancePanel` bỏ chip "AI" lặp. Tiêu đề topbar trang `/ai/*` khi tắt không nhắc tên mục AI (Shell). Nhật ký: khi giao diện tắt, lọc thêm ở FE các dòng `actor_kind=ai` hoặc có `proposal_ref` (phòng ca BE bật, FE tắt).
Xoá `RightRail.tsx`, `AiBar.tsx`, `StatusChip.tsx`, `status.ts`; sửa harness `e2e/qa_harness_ed_batch1`, comment ListPage/AiAssistantGate, README.

**Ghi chú (BR-GH-19).** `CancelOrderModal`: `CANCEL_NOTE_MAX = 200` (có bộ đếm); 400 `BR-GH-19` hiện dưới ô, quay về form, giữ chữ. `DecideModal`: cùng cách (lỗi vào ô lý do, bỏ bước hỏi lại huỷ). Chi tiết đơn có dòng "Ghi chú huỷ" (`cancel_note`), chi tiết hàng chờ có "Lý do quyết định" (`decision_note`) khi không rỗng. Mock trả BR-GH-19 và hai field này.

**Shop.** `OrderLookup.tsx` in `delivery.status_label` (thiếu thì "Đang cập nhật"). Mock dùng nhãn T24–T30 và "Đã huỷ vì quá giờ thanh toán"; thêm đơn mẫu DH-DEMO005..009 phủ các trạng thái phiếu giao; khoá localStorage mock đổi `v2`→`v3`.
Kèm việc điều phối: đổi id `thong-tin-nguoi-ban` → `seller-info` (ContactButton, SiteLegalFooter) cho `check_naming`.

**Kiểm (chạy thật).** `tsc` ERP và Shop sạch; vitest 90 file / 1020 test xanh; ERP build mock=0 + `check-no-mock` XANH + `check-ai-chunks` XANH (48 màn + 2 layout); Shop build mock=0 sạch; `check_naming.py` OK.
E1 `erp-console/e2e/ai_text_hidden_all_routes.py` (mock): build 0 → 24/24 (BE tắt/bật × Chủ/Quản lý); build 1 → 14/14 (gồm ca BE tắt = W39 và ca đối chứng có chữ AI). 0 request `/api/ai/`.
E2 `frontend/e2e/order_lookup_no_raw_codes.py`: 19/19. E3 `erp-console/e2e/note_br_gh_19.py`: 10/10. Ảnh: `/tmp/don-ai-shots/e3-cancel-error-mobile.png`, `e2-order-lookup-mobile.png` (ngoài repo).

**Lệch / nợ.**
- `features/permissions/mock.ts` còn khoá `ai_policy` (không được sửa ở lô này, thuộc F1): E1 mock in dòng "NỢ" cho `/permissions/` khi AI tắt và bỏ qua; E1 trên BE thật phải sạch.
- Ở DecideModal, máy khách đã chặn số dài trước (`noteError`) nên đường BE trả BR-GH-19 chỉ được khoá bằng vitest ở mock (`decisionNote.test.ts`), không bằng e2e UI.
- E1/E3 chỉ chạy trên mock; E1 trên BE thật là việc của QA.
- `03-dev-notes.md` này chỉ có mục FE; BE ghi mục riêng khi merge (có thể xung đột nội dung file, giữ cả hai mục).

---

# Lô dọn chữ AI — ghi chú dev

**Sửa theo review (3 việc Low).** L1: harness batch2 có stub `AuthProvider` (alias trong `vite.config.mjs`). L2: xoá code chết `byAi` (Timeline.tsx, Timeline.module.css `.ai`, detailAdapters.ts và test). L3: `OrderDetailScreen` đổi biến thành `beAiEnabled`.

## BE (be-dev, nhánh `feat/don-chu-ai-be`)

### File đã sửa/thêm (đúng danh sách 02b mục 4)
- MỚI `backend/apps/common/ai_visibility.py` — `ai_features_enabled()` (cờ env `AI_ENABLED`, không dùng công tắc tắt khẩn) và
  `exclude_ai_audit_rows(qs)` (thân hàm chuyển từ `exclude_ai_rows`).
- `apps/accounts/audit/serializers.py`: `exclude_ai_rows = exclude_ai_audit_rows` (giữ tên cũ, test TL-D3-L4 không đổi).
- `apps/accounts/auth/services.py` (`describe_user`): thêm `ai_features_enabled`, `capabilities` bỏ `ai.*` khi tắt.
- `apps/accounts/capabilities/registry.py`: `AI_CAPABILITY_KEYS`, `visible_capabilities()`, `visible_keys()`.
  `services.py`: `capability_states`, `describe_group.registry`, `_validate_changes`, `_capability_events`,
  `capability_change_label` dùng bản lọc. `CAPABILITIES`/`BY_KEY` giữ nguyên.
- Lọc dòng AI trước khi cắt `limit`: `common/guidance/audit_timeline.py`, `sales/orders/timeline.py`,
  `sales/payments/timeline.py`, `sales/refunds/timeline.py`, `inventory/batches/timeline.py`,
  `inventory/stocktake/services.py` (`_last_editor_name`), `inventory/stocktake/queries.py` (subquery `latest`),
  `inventory/stocktake/serializers.py` (nhánh AI trả "Hệ thống" khi cờ tắt).
- MỚI `apps/sales/orders/shop_labels.py` + `shop_api.py` dùng nó (W1, W2). Không đổi `choices`, không migration.

### Contract thực tế (khớp 02b, không đổi shape)
`GET /api/auth/me/` thêm `"ai_features_enabled": bool`; tắt thì `capabilities` không có `ai.manage_ai_policy`,
`permissions` giữ nguyên. Ma trận: tắt thì `registry`/`capabilities` không có `ai_policy`; `PUT {"ai_policy": ...}` -> 400
`INPUT_NOT_ALLOWED`, dữ liệu không đổi. Shop tra đơn: chỉ đổi chuỗi `status_label`, `delivery.status_label`.

### Test (cả hai nhánh cờ)
MỚI: `common/tests/test_ai_visibility.py`, `accounts/auth/tests/test_ai_features_flag.py`,
`accounts/capabilities/tests/test_ai_hidden.py`, `sales/orders/tests/test_ai_rows_hidden.py` (5 builder + Nhật ký +
limit sau lọc + khoá `step.ai=null`), `inventory/stocktake/tests/test_ai_rows_hidden.py`, `sales/orders/tests/test_shop_labels.py`.
Test cũ chuyển sang `override_settings(AI_ENABLED=True)` vì kiểm nhánh bật: `test_s47_me_labels` (1 ca),
`capabilities/test_api_read|test_api_write|test_requires` (3 class), `orders/test_guidance` (DW-03-AC4). Hai test key contract của `/me`
thêm `ai_features_enabled`.

### Chỗ lệch / điều cần biết
1. Nhãn phiếu giao CANCELLED ở Shop nay là "Đã huỷ" cho mọi ca (trước: "Đã huỷ theo đơn"), theo T30 đã duyệt.
2. "6 builder" ở 02b thực tế là 5 builder dòng thời gian (audit_timeline, order, payment, refund, batch) cộng
   `_last_editor_name` của kiểm kê; không có builder dòng thời gian riêng cho kiểm kê.
3. Dòng thời gian chi tiết đơn (`SalesOrderDetailSerializer.get_timeline`) không có `actor_kind`; test khoá bằng `build_timeline`.
4. Dòng nhật ký đổi quyền cũ có khoá `ai_policy` bị ẩn khi tắt (sự kiện chỉ chứa khoá AI bỏ hẳn; sự kiện lẫn thì chỉ tính khoá không AI).
5. Ca Shop labels viết cùng lúc với code (chưa chạy RED riêng); các ca còn lại đã kiểm RED bằng cách vô hiệu hoá bộ lọc.
6. Q1 (Duy): giữ nguyên dòng `ai_config_*`/`ai_policy_*` do Chủ đổi.
