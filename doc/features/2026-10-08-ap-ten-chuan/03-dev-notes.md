# 03 — Ghi chú hiện thực: lô áp tên chuẩn

## FE (fe-dev) — Pha A, nhánh `feat/ten-chuan-fe`

**Phạm vi đã làm:** F1 đến F8 (trừ phần Pha B), F10, F12 (trừ mock Pha B). Chỉ đổi chữ hiển thị. Không đổi giá trị enum, khoá JSON, route.

**Nguồn chữ duy nhất** `erp-console/shared/lib/enums.ts`:
- Sửa theo cột "Chuẩn": `salesOrderStatus.AUTO_CANCELLED` ("Hết giờ giữ chỗ", tông `mute`), `paymentMatchStatus`, `paymentSource.WEBHOOK`,
  `cancelReason` (đủ 6 mã), `refundMethod`, `refundStatus`, `deliveryStatus`, `confirmTaskState.DONE`, `confirmEscalationReason`,
  `confirmCallResult.CONFIRMED_CHANGED`, `unconfirmedDecision`, `stockMovementType.WRITE_OFF`, `returnToStockDecision.WRITE_OFF`,
  `pricingRuleActive.true`, `entryPageRole`, `entryReturnReason`, `entryUnpublishReason`.
- Thêm bảng mới: `paymentEnvironment` (T12, T13), `confirmQueueTab` (T39).

**Xoá bản chép nhãn (dựng từ ENUMS):** `orders/labels.ts` (`STATUS_FILTERS`, `QUEUE_TYPE_FILTERS`, `CANCEL_REASONS`),
`confirmation/confirmationUi.ts` (`CANCEL_REASON_CODES`, `PATH_STEPS`), `confirmation/types.ts` (`QUEUE_TABS`, `CALL_RESULT_OPTIONS`),
`content/messages.ts` (`RETURN_REASONS`, `UNPUBLISH_REASONS`), `content/components/EntrySettings.tsx` (`PAGE_ROLE_OPTIONS`),
`suppliers/suppliersModel.ts` + `SupplierFormModal.tsx` (loại nhà cung cấp), `deliveries/types.ts` + `deliveryUi.ts`, `orders/components/RefundQueueScreen.tsx`,
`orders/messages.ts` (câu tổng tháng của phiếu hoàn tiền), `returns/returnsModel.ts` + `messages.ts`, `catalog/messages.ts` (Đang áp dụng).

**Tên chứng từ và việc:** `nav.ts` ("Hoàn tiền chờ chuyển", short "Hoàn tiền"; "Hàng hoàn", short "Hàng hoàn"); "phiếu hoàn" trơn đổi thành "phiếu hoàn tiền"
ở 40 file chữ; "Tạo phiếu hoàn" thành "Lập phiếu hoàn tiền"; "Giao dịch thanh toán" thành "Khoản tiền về"; "Chọn người giao" (P9);
"Hàng hoàn về kho" thành "Hàng hoàn"; "Huỷ bỏ, ghi lỗ" thành "Huỷ hàng, ghi lỗ"; tab "Phiếu hoàn" thành "Phiếu hoàn tiền".

**F10 (T43):** `ConfirmationQueueItem.auto_cancel_blocked_label?: string | null` (để optional vì BE cũ chưa trả khoá, FE vẫn chạy). Màn chi tiết việc gọi hiện
một dòng gợi ý (alert-box warn) khi khác null. Mock thêm `auto_cancel_blocked_label: null`.

**Mock khớp chữ BE:** orders, customers, guidance, confirmation, deliveries, returns, auth (nhãn quyền P1 "Xác nhận đã nhận tiền"), dashboardSummary.

**Test:** `enums.standardNames.test.ts` (66 dòng T + menu + quy ước OTHER), `noLabelCopies.test.ts` (quét mã nguồn, bỏ comment),
cập nhật 8 test đang khoá chữ cũ. e2e mới `erp-console/e2e/standard_names_all_routes.py`; cập nhật chuỗi mong đợi ở nhiều e2e cũ (`ed_batch3_orders`,
`ed_batch5_confirmation`, `ed_batch9_*`, `late_payment_record`...).

### Kết quả kiểm (chạy trong worktree, 08/10)
- `tsc --noEmit` sạch · `vitest run` 96 file, 1133 test xanh.
- Build `USE_MOCK=0`: sạch; `check-no-mock` XANH; `check-ai-chunks` XANH (48 màn + 2 layout).
- Build `USE_MOCK=1` (AI tắt): `standard_names_all_routes` 9/9 · `ed_batch3_orders` 143/143.
- Build `USE_MOCK=1 AI_FEATURES=1`: `ed_batch5_confirmation` 129/129 · `ed_batch7_inventory` 114/114 (hai bài này có ca AI, nên cần build bật AI;
  build tắt AI thì đúng 2 ca AI báo FAIL, không liên quan lô này).
- `python3 scripts/check_naming.py`: OK, không phát sinh mới.

### Lệch so với 02b (ghi để Tech Lead biết)
1. Nhóm A có `chờ Chủ`. Câu hợp lệ "Phiếu chờ Chủ hoặc Quản lý duyệt" có ở 5 màn (kiểm kê, giao thất bại, gọi xác nhận), nên cả test vitest lẫn e2e chỉ cấm
   đuôi nhãn `— chờ Chủ`, tức regex `— chờ Chủ(?! hoặc)`. Cần Tech Lead xác nhận, hoặc đổi các câu đó.
2. F11 (RefundModal bỏ GATEWAY): `RefundModal.tsx` không có ô chọn phương thức nào, nên không phải sửa.
3. `reportView.ts:47` đã là "Trừ doanh thu đơn huỷ" (khớp C2), giữ nguyên.
4. Nhãn "Soạn hàng" trong câu "Đơn chuyển sang Soạn hàng" của toast gọi xác nhận đổi thành "Phiếu giao chuyển sang Đang soạn hàng", vì đó là trạng thái phiếu giao (T25).
5. `auditModel.test.ts` và `orderDetailModel.test.ts` có sửa 1 chuỗi mong đợi mỗi file (nhãn đến từ ENUMS/messages đã đổi). Không đụng file nguồn Pha B.

### Việc còn nợ (TODO Pha B và F1)
- Sau khi W37 L3 gộp: `auditModel.ts` (F9: P1, P3-P9, P11, T67-T76, W11 `statusLabel` theo `model_name`, W33, W34) và `features/audit/mock.ts`;
  `orderDetailModel.ts` (F7/F8: thanh bước phiếu hoàn tiền, "Lập phiếu hoàn"); `frontend/lib/mock.ts` (F13, Shop: BOOKED "Chờ thanh toán", hoàn tiền T21/T22).
- `noLabelCopies.test.ts`: bỏ 4 file Pha B khỏi `PHASE_B_FILES` rồi cho xanh. `enums.standardNames.test.ts`: thêm `actionLabel()` T67-T76, P1, P3-P9, P11, `auditModel.test.ts` W11.
- `standard_names_all_routes.py`: bỏ `/audit-logs/` và hai route `/permissions/` khỏi `PENDING_ROUTES` (còn chữ cũ: "Xác nhận thanh toán thủ công", "Gán phiếu giao",
  "Giao phiếu cho người giao", "phiếu hoàn"); thêm Shop `/shop/orders/`; chạy lần hai trên BE thật.
- `features/permissions/mock.ts:37,40` (nhánh F1) còn chữ cũ.
- Một số e2e cũ chỉ được thay chuỗi, chưa chạy lại: `qa_ed_batch*`, `ed_batch9_*`, `late_payment_record`, `s12_s13_queue`, `s41_s47_staff`, `note_br_gh_19`, `p8_lo7_fe_erp`, `ed_bonusA_ui`, `ed_batch1_shell`.
