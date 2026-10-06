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

## FE (fe-dev) — Pha B (08/10, sau khi W37 L3 vào main 00da7e8, merge sạch không xung đột)

**Đã làm:**
- `auditModel.ts` (F9): nhãn P1, P3-P9, P11; thêm T67-T76 (gồm `item_image_remove` đã có); T2 cho `order_auto_cancelled`/`cancel_unpaid_expired`; `complete_order` giữ "Đơn hoàn tất".
  W34: bỏ nhãn chết `auto_cancel`, `confirm_payment` (BE không ghi), bỏ `confirm_proposal` khỏi `AUDIT_FILTER_ACTIONS`.
  W11 (review M2): `statusLabel` chọn bảng theo `model_name` (`sales.SalesOrder`, `sales.Refund`, `delivery.DeliveryNote`, `inventory.Batch`,
  `inventory.StockReconciliation`, `inventory.ReturnToStock`); model lạ hoặc thiếu thì không in trạng thái. `changeSummary(changes, modelName)`; mock Nhật ký đổi `model` sang nhãn Django, thêm 2 dòng mẫu.
- `orderDetailModel.ts`, `OrderDetailScreen.tsx`: "Lập phiếu hoàn tiền" ở mọi chỗ (Low 1), thanh bước phiếu hoàn tiền và dòng `refundSummaryLine` lấy từ ENUMS ("Đã hoàn tiền x · Chờ hoàn tiền y").
- M1 (review Pha A): `confirmation/messages.ts` (`hintWantChange`), `escalationHint()` trong `confirmationUi.ts`; màn chi tiết hiện dòng "Huỷ đơn, hoàn tiền rồi đặt lại đơn mới" khi `escalation_reason === "WANT_CHANGE"`. Có vitest.
- Shop `frontend/lib/mock.ts` (F13): BOOKED "Chờ thanh toán", hoàn tiền "Đang chờ hoàn tiền"; `order_lookup_no_raw_codes.py` cập nhật.
- Test: bỏ `PHASE_B_FILES`; `enums.standardNames.test.ts` thêm 36 ca `actionLabel`; `auditModel.test.ts` thêm ca W11 (phiếu giao FAILED "Giao thất bại", COMPLETED "Đã giao", phiếu hoàn FAILED "Hoàn thất bại").
  e2e `standard_names_all_routes.py`: `/audit-logs/` ra khỏi `PENDING_ROUTES` (còn `/permissions/` do F1), thêm kiểm Nhật ký và Shop qua `SHOP_BASE`.

**Kiểm (08/10):** tsc sạch · vitest 97 file, 1182 test xanh · ERP build mock=0 + `check-no-mock` (30 file mock, 233 chuỗi seed) + `check-ai-chunks` XANH · Shop `tsc` và build mock=1 sạch ·
`check_naming` OK. e2e (ERP build mock=1 AI=1): `standard_names_all_routes` 11/11 (kèm Shop 19/19), `ed_batch3_orders` 143/143, `ed_batch5` 129/129, `ed_batch7_inventory` 114/114,
`late_payment_record` 32/32, `s12_s13_queue` 66/66, `s41_s47_staff` 74/74, `note_br_gh_19` 10/10, `ed_bonusA_ui` 49/49, `ed_batch1_shell` 56/56, `order_completion_erp` 6/6, `order_completion_detail` 16/16.
Shop: `order_lookup_no_raw_codes` 19/19, `order_lookup_completed` 4/4.

**Còn lại:** `ed_batch9_returns` 133/139. Sáu ca FAIL là lọc tháng và phạm vi danh sách (RT-4 của tháng trước), cộng "F2m SĐT không nằm trong storage". Không liên quan nhãn,
có vẻ phụ thuộc ngày chạy. Chưa kiểm trên main nên chưa khẳng định là lỗi có sẵn. `ed_batch9_real`, `qa_ed_batch*` (cần BE thật) chưa chạy. `features/permissions/mock.ts` (F1) còn chữ cũ.
