# Đơn hoàn tất (W37) — Review của Tech Lead

> File này cũng có trên nhánh `feat/w37-l1-be` (mục "Review L1 BE (07/10)"). Khi gộp, giữ cả hai mục, BE trước FE.

## Review L1 FE (08/10)

**Phạm vi:** commit `fcfe375` trên `feat/w37-l1-fe`, diff `2dcf666..HEAD` (21 file, chỉ thuộc `erp-console/` và `doc/`).
Đối chiếu với `02b-tech-design.md` §2.1–§2.5 và §6 (L1 FE).

**Kết luận: APPROVED.** Không có lỗi Critical, High hay Medium. Có 5 điểm Low và một nợ chuyển sang L3 (S6-AC8 phần đồng bộ hai
kho mock). Không cái nào chặn QA.

**Lệnh kiểm chứng:** worktree không có `node_modules`, nên Tech Lead **không chạy lại** `tsc`, `vitest` hay build. Kết quả dùng là
số điều phối viên đã chạy: `tsc` sạch; vitest 1031 test xanh; build `NEXT_PUBLIC_USE_MOCK=0` có `check-no-mock` và
`check-ai-chunks` XANH. Review dưới đây làm bằng đọc diff và lần theo nơi gọi.

### Soát theo yêu cầu

| Mục | Kết quả | Chứng cứ |
|---|---|---|
| `order_status` và toast | Đạt | `DeliveryStatusResponse.order_status?: string \| null` (`features/deliveries/api.ts`). `completeToast` (`deliveryUi.ts`) chỉ đổi câu khi giá trị là `"COMPLETED"`; thiếu khoá (BE cũ) thì giữ câu cũ. Dùng ở cả `MyDeliveriesScreen` lẫn `DeliveryDetailScreen`. Có test 3 nhánh |
| BR-GH-24 nhận theo `code`, không vào `CONFLICT_CODES` | Đạt | `isOrderCancelledError` = `ApiError` có `code === "BR-GH-24"`, không xét HTTP status. `shared/ui/form/useSubmit.ts` không bị sửa. Có test khẳng định `isConflictError(BR-GH-24) === false` |
| Hiện câu và tải lại khi gặp BR-GH-24 | Đạt | `ConfirmCompleteModal` hiện đúng `detail`, nút chính đổi thành "Tải lại" (gọi `onConflict`, tức tải lại), ẩn câu lỗi chung. `ReportFailureModal` làm tương tự qua prop mới `onReload`, cả hai nơi gọi đều đã truyền. "Nhận hàng đi giao" ở cả hai màn hiện câu đó rồi tải lại |
| S6 bộ lọc | Đạt | `labels.ts` bỏ lựa chọn `PAID`. "Chưa xong" giữ `BOOKED,PAID,PROCESSING`. Chip `PAID` trong `enums.ts` vẫn còn (S6-AC4) |
| Thanh bước S7 và test bảng | Đạt | `ORDER_STEPS` có 5 bước, bước 2 là `CONFIRMING`. `orderStepKey` chỉ trả `COMPLETED` khi `status === "COMPLETED"`. Bảng ánh xạ `PROCESSING` khớp 02b §6. Test duyệt 6×8 tổ hợp, khẳng định bước Hoàn tất ⇔ chip Hoàn tất (S7-AC3), cộng ca `PROCESSING` + phiếu `COMPLETED` → Đang giao. `OrderDetailScreen.tsx:128` đã truyền `hasInvoice: !!o.invoice`, nên nhánh mới `hasInvoice === false ? "BOOKED"` vẫn đúng. e2e `ed_batch3_orders.py` đổi kỳ vọng theo 5 bước mới |
| Luật dùng chung `orderCompletion.ts` | Đạt | Hàm thuần, khớp từng ca với `completion.is_delivery_finished` của BE: bỏ `CANCELLED`, rỗng là chưa xong, toàn `CANCELLED` là chưa xong. Hai mock đều dùng, test đủ các ca UC-4 |
| Mock không lọt vào bản build thật | Đạt | `orderCompletion.ts` nằm ở `shared/lib`, không có seed. Hàm `siblingStatuses` đặt ngay trong hàm mock export, theo bài học dev ghi lại. `check-no-mock` xanh ở build mock=0 (số của điều phối viên) |
| Không đụng `OrderDetailScreen.tsx`, `CancelOrderModal.tsx`, `frontend/` | Đạt | `git diff --stat` không có ba đường này. Không đụng `shared/ui/**`, `enums.ts`, `features/{permissions,ai,audit,auth,overview}` |
| Dữ liệu cá nhân, giá vốn | Đạt | Không có khoá mới chứa dữ liệu khách. Toast và câu lỗi không ghép tên hay SĐT. Không đụng cột giá vốn. Ảnh trong `shots/` chụp bằng mock (dữ liệu giả) |
| Contract | Khớp 02b | Mock trả 400 `{detail, code: "BR-GH-24", current_status}`, `order_status` có ở mọi nhánh. Hình dạng `refund_summary` khớp §2.5 |

### Chỗ lệch dev đã ghi: quyết định

1. **Hai kho mock không nối nhau.** Chấp nhận ở L1. Lý do: import chéo làm bản build thật giữ seed mock (`check-no-mock` đỏ), và
   ràng buộc đó có thật. Hệ quả là **S6-AC8 mới đạt một nửa**: mock Giao hàng trả `order_status` đúng luật, nhưng trang Đơn của
   mock không đổi theo. Chuyển sang L3. Hướng gợi ý: một kho dùng chung chỉ có ở chế độ mock, đặt trong
   `shared/lib/*.mock.ts` (tiền lệ là `dashboardSummary.mock.ts`), hai mock cùng đọc ghi, rồi chạy lại `check-no-mock`.
   QA **không** chấm S6-AC8 PASS trọn ở L1.
2. Bài học closure trong mock: ghi nhận, không phải lỗi.
3. Bộ dữ liệu riêng cho S6-AC1 (1/2/3/1): chuyển sang L3, cùng mục 1.
4. Đường BR-GH-24 trong hộp xác nhận chưa có e2e trình duyệt: chấp nhận. UI không mở được hộp cho phiếu đã huỷ, và vitest đã phủ
   hàm nhận diện cùng mock 400. Khi L3 nối BE thật, QA dựng ca đua (huỷ đơn sau khi màn đã mở hộp) để chụp thật.
5. Thanh bước đổi qua mô hình, `OrderDetailScreen.tsx` chưa sửa: đúng thiết kế, vì màn đọc `orderPath`.

### Điểm Low (không chặn)

- **L1** `features/orders/types.ts`: `OrderDetail.refund_summary` khai bắt buộc, nhưng BE thật chỉ trả khoá này từ L2. Hiện chưa
  màn nào đọc nên không lỗi lúc chạy. Chọn một trong hai: (a) để `refund_summary?:` cho tới khi L2 gộp; (b) bảo đảm L3 FE chỉ
  gộp sau L2 (đúng thứ tự trong 02b §5.2).
- **L2** `features/orders/mock.ts` (seed): `o.status = isDeliveryFinished([dStatus])`, nhưng `dStatus` lại suy ra từ trạng thái đơn
  đích, nên thực chất vẫn là gán cứng đội lốt luật. Làm lại cùng nợ S6-AC8 ở L3.
- **L3** `features/deliveries/mock.ts`: BR-GH-24 chỉ xét phiếu `CANCELLED`, không xét đơn đã huỷ mà phiếu cũ chưa huỷ (ca nhiều
  phiếu, BE §1.2 có xét). Mock không có ca đó nên chấp nhận được. Ghi lại để mock không bị coi là nguồn đúng.
- **L4** `features/deliveries/api.ts:27`: thêm một dòng trống thừa (nhiễu diff).
- **L5** `deliveries_order_completion.test.ts`: ca "còn phiếu khác" `push`/`pop` vào `MOCK_DELIVERY_NOTES` mà không có
  `try/finally`, và `post(36)` làm đổi trạng thái phiếu 36 cho các ca sau trong cùng file. Nên khôi phục trong `afterEach`.

### Nợ có sẵn (không thuộc lô)
Mock `STALE_STATE` của `status/` trả 409, còn BE trả 400 (02b §2.3). Vô hại vì FE xét theo `code`.

### Gộp nhánh
`03-dev-notes.md` và `03b-review-techlead.md` đều được tạo mới trên cả `feat/w37-l1-be` lẫn `feat/w37-l1-fe`, nên gộp sẽ xung
đột cả file. Cách xử lý: giữ cả hai mục (L1 BE trước, L1 FE sau), không ghi đè mục nào.
