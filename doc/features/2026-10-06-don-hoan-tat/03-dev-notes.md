# W37 đơn hoàn tất: ghi chú dev

## L1 FE (ERP, chạy mock theo contract 02b)

Nhánh `feat/w37-l1-fe`. Chỉ sửa `erp-console/`. Không đụng `OrderDetailScreen.tsx`, `CancelOrderModal.tsx`, `frontend/**`.

**Đã làm**
- S1/S2, phía NV giao:
  - `DeliveryStatusResponse.order_status?` (`features/deliveries/api.ts`).
  - Giao xong mà `order_status === "COMPLETED"` thì toast "Đã giao xong. Đơn đã hoàn tất." (`completeToast` ở `deliveryUi.ts`, dùng ở `MyDeliveriesScreen` và `DeliveryDetailScreen`).
  - Lỗi 400 `BR-GH-24` nhận theo `code` (`isOrderCancelledError`), không thêm vào `CONFLICT_CODES`.
    - `ConfirmCompleteModal` và `ReportFailureModal` hiện đúng `detail` của BE ("Đơn đã huỷ — mang hàng về kho.") và đổi nút chính thành "Tải lại".
    - Nút "Nhận hàng đi giao" ở hai màn chỉ hiện câu đó và tải lại.
    - `ReportFailureModal` có prop mới bắt buộc `onReload`.
- S6:
  - `labels.ts` bỏ lựa chọn "Đã thanh toán". "Chưa xong" giữ `BOOKED,PAID,PROCESSING`.
  - `enums.ts` giữ chip `PAID` để đọc dữ liệu cũ.
- S7 (mô hình):
  - `orderDetailModel.ts`: `ORDER_STEPS` 5 bước, bước 2 là `CONFIRMING` "Chờ gọi xác nhận". `orderStepKey` chỉ trả `COMPLETED` khi đơn `COMPLETED`.
  - `orderDetailModel.test.ts` có bảng mọi tổ hợp `order.status × delivery.status`.
- Luật dùng chung: `shared/lib/orderCompletion.ts` (`isDeliveryFinished`, BR-BH-18) kèm test.
- Mock:
  - `deliveries/mock.ts`: mọi phản hồi của `status/` có `order_status` tính bằng luật dùng chung trên mọi phiếu cùng đơn. Phiếu `CANCELLED` mà giao, nhận đi giao hay báo thất bại thì trả 400 `BR-GH-24` kèm `current_status`.
  - `orders/mock.ts`: đơn `COMPLETED` sinh theo luật dùng chung (không gán cứng), có `refund_summary`, mốc "Đã giao — đơn hoàn tất (…)" thay "Giao hàng thành công" khi đơn `COMPLETED`.
  - `orders/types.ts`: `OrderDetail.refund_summary`, `TimelineKind` thêm `order_completed`.
- e2e: `e2e/order_completion_erp.py` (mới). `ed_batch3_orders.py` đổi kỳ vọng thanh bước theo S7.

**Chỗ lệch / nợ**
1. Kho phiếu mock (Giao hàng) và kho đơn mock (Đơn) **không nối nhau**: seed dùng mã đơn khác nhau, nên giao xong ở Việc giao của tôi không đổi đơn bên trang Đơn trong mock. Thử nối bằng import chéo hoặc truyền hàm qua `api.ts` thì `check-no-mock` đỏ (bundler giữ seed mock), nên bỏ.
2. Bài học cho mock: một hàm trong file mock **không export**, được gọi bởi hàm mock export và đọc `MOCK_DELIVERY_NOTES`, làm bản build thật giữ lại seed. Tách hàm phụ ra ngoài thì sai. Phải đặt closure ngay trong hàm export (`siblingStatuses` ở `mockPostDeliveryNoteStatus`).
3. Bộ đơn mock chưa dựng riêng theo S6-AC1 (1/2/3/1). Seed 45 đơn hiện có đã đủ mọi trạng thái, trong đó đơn `COMPLETED` sinh theo luật. Cần kịch bản riêng thì làm ở L3.
4. Đường BR-GH-24 trong hộp xác nhận chưa có e2e trình duyệt: UI không cho bấm giao xong ở phiếu đã huỷ. Hành vi do vitest phủ (mock 400 và nhận diện theo `code`).
5. Thanh bước của chi tiết đơn đã đổi ở mô hình, nhưng `OrderDetailScreen.tsx` chưa sửa. Màn đọc `orderPath` nên nhãn mới hiện ngay, không cần sửa.

**Kiểm chạy thật (07/10)**
- `tsc --noEmit` sạch. `vitest run` 90 file, 1031 test xanh.
- Build `NEXT_PUBLIC_USE_MOCK=0`: `check-no-mock` XANH, `check-ai-chunks` XANH.
- Build `NEXT_PUBLIC_USE_MOCK=1`: `ed_batch3_orders` 143/143, `ed_batch4_delivery` 70/70, `order_completion_erp` 6/6.
- `python3 scripts/check_naming.py`: không báo gì ở `erp-console/` (exit 1 ở main do `frontend/features/site/components/SiteLegalFooter.tsx:60`, có sẵn từ trước, không do lô này).
- Ảnh: `shots/order_completion_toast_360.png`, `order_completion_filter_1280.png`, `order_completion_steps_1280.png`.
