# 03b — Review Tech Lead: lô áp tên chuẩn (FE)

## Review FE Pha A (08/10)

> Tech Lead · `feat/ten-chuan-fe` @ `3ea03dd`, diff `9b1238c..3ea03dd` (94 file) · đối chiếu `02b-tech-design.md` mục 1.2, 3.2, 3.3
> và `03-dev-notes.md` mục FE Pha A.

**Kết luận: APPROVED cho Pha A, kèm điều kiện gộp.** Pha A **không được gộp riêng vào main**. Phải gộp cùng FE Pha B, và Pha B phải xong M1 và M2
dưới đây. Lý do: riêng Pha A làm lộ hai chỗ sai mà Pha A chưa xử lý.

### Lệnh đã tự chạy
- `tsc --noEmit`: sạch.
- `npx vitest run shared/lib`: 18 file, 273 test xanh.
- Worktree đang có thay đổi Pha B chưa commit (`features/audit/**`, e2e), nên hai lệnh trên chạy trên HEAD cộng phần Pha B đó. Tôi không
  reset worktree của dev. Kết quả vitest 1133 và e2e của dev chưa được tôi chạy lại.

### Theo từng điểm
| Điểm | Kết quả |
|---|---|
| `enums.ts` đúng bảng mục 4 | Đạt. Đã đối chiếu từng dòng T2–T66 có ở ERP. Thêm `paymentEnvironment` (T12, T13) và `confirmQueueTab` (T39). `cancelReason` có đủ 6 mã. Ô chọn huỷ tay chỉ lấy 4 mã người dùng được chọn (`orders/labels.ts`) và hộp quyết định lấy 3 mã (`confirmationUi.ts`), đúng hành vi cũ. Nhóm lọc "Đã huỷ" vẫn gộp `CANCELLED,AUTO_CANCELLED` (Q-2) |
| Xoá 6 bản chép | Đạt, kèm các bản chép phụ (`confirmation/types.ts` tab và kết quả gọi, `deliveries/types.ts`, `deliveryUi.ts`, `RefundQueueScreen.tsx`, `returnsModel.ts`, `catalog/messages.ts`). File mới chỉ import thêm `ENUMS`, không file nào import mock |
| `noLabelCopies.test.ts` | Đủ chặt cho mục tiêu "không còn chữ cũ". Quét `features/`, `shared/`, `app/` kể cả mock, bỏ comment, có kiểm sàn > 100 file. Có 4 file Pha B được miễn tạm (`PHASE_B_FILES`), phải gỡ ở Pha B. Giới hạn: test chỉ chặn chữ **cũ**, không chặn việc chép lại chữ **mới** ngoài `enums.ts`. Chấp nhận, vì mock có quyền mô phỏng nhãn BE |
| Lệch 1: regex `— chờ Chủ(?! hoặc)` | **Chấp nhận.** Thứ cần cấm là đuôi nhãn "— chờ Chủ" (T3–T7). Câu "chờ Chủ hoặc Quản lý duyệt" là lời văn đúng nghiệp vụ |
| Lệch 2–5 | Chấp nhận. F11 không có ô chọn nên không phải sửa. `reportView.ts` đã đúng C2. Toast "Phiếu giao chuyển sang Đang soạn hàng" đúng T25 |
| e2e `standard_names_all_routes.py` | Đủ cho Pha A: nhóm A trên `innerText` cùng `aria-label`/`title`/`placeholder`, nhóm B theo `.stat-chip` từng route, đối chứng dương ("Hết giờ giữ chỗ", chip phiếu giao, chip phiếu hoàn tiền, menu), chạy hai vai. Còn nợ ở Pha B: gỡ `PENDING_ROUTES`, thêm Shop `/shop/orders/`, thêm cột Thao tác của Nhật ký, chạy lần hai trên BE thật |
| F10 (T43) | Đạt. Hiện một dòng `alert-box warn role="status"` khi `auto_cancel_blocked_label` khác null. Khoá để optional nên BE cũ vẫn chạy |
| Mock lọt bản build | Đạt. Không có import mock mới ngoài file mock. Dev chạy `check-no-mock` trên bản `USE_MOCK=0`: xanh. Phiếu M5-1b đã quét cả `*.mock.ts` (sửa ở W37 L3) |
| Dữ liệu cá nhân / giá vốn | Không thêm field, nhãn đều là hằng. Không ghi log hay storage |

### Bắt buộc ở Pha B (điều kiện gộp)
- **M1, mất hướng dẫn xử lý WANT_CHANGE (T37).** BE Pha A đã bỏ đuôi "– huỷ + hoàn + đặt lại" khỏi `escalation_label`. Theo ghi chú T37 của
  mục 4, phần hướng dẫn chuyển thành dòng gợi ý dưới chip. FE Pha A chưa thêm dòng này: `ConfirmationDetailScreen.tsx:320` chỉ in "Lý do: Khách
  muốn đổi món". Nếu BE gộp trước thì nhân viên CSKH không còn thấy cách xử lý. Cần thêm một dòng gợi ý (chữ đặt ở `confirmation/messages.ts`)
  khi `escalation_reason === "WANT_CHANGE"`, ví dụ "Huỷ đơn, hoàn tiền, rồi nhờ khách đặt lại", kèm vitest.
  (Lỗi do 02b mục F10 chỉ ghi T43, sót phần này. Tech Lead nhận.)
- **M2, W11 nặng thêm khi đổi chữ.** `auditModel.ts` `statusLabel` vẫn dò lần lượt `STATUS_TABLES` (salesOrder → refund → delivery…). Sau Pha A,
  `FAILED` của phiếu giao hiện thành "Hoàn thất bại" (trước là "Thất bại"), và `COMPLETED` của phiếu giao hiện thành "Hoàn tất" (đúng phải là
  "Đã giao"). F9 ở Pha B phải chọn bảng theo `model_name` như 02b mô tả. Test trong `auditModel.test.ts` phải có cả hai ca này.

### Ghi chú thêm (không chặn)
- Khi gỡ `PHASE_B_FILES` và `PENDING_ROUTES`, ghi lại trong dev-notes số route và số file thực quét, để QA so được.
- `features/permissions/mock.ts:37,40` còn chữ cũ thuộc nhánh F1. Sau khi F1 gộp thì gỡ `features/permissions/` khỏi `SKIP_PREFIXES`.
