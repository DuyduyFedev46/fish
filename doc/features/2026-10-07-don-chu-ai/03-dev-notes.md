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
