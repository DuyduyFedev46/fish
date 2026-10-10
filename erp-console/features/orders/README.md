# features/orders — Đơn & tiền

Một nhóm 3 tab theo route (ERP theo design Lô 3: ED-09, ED-10, ED-11, ED-12). Mỗi danh sách có trang chi tiết riêng
(`?id=<số>` — URL chỉ chứa id, không chứa tên/SĐT/địa chỉ); thao tác ghi nằm trong hộp thoại (`Modal`). Contract BE:
03-dev-notes.md các mục "Lô L7 / L8 / L9 (BE)" và "Lô 3 (BE)" của hồ sơ `2026-10-01-erp-theo-design`.

| Tab | Danh sách | Chi tiết | Quyền |
|---|---|---|---|
| Đơn hàng | `/orders/` | `/orders/detail/?id=` | `sales.view_salesorder` (không phải người CHỈ giao hàng) |
| Hàng chờ thanh toán | `/orders/payments/` | `/orders/payments/detail/?id=` | chỉ Chủ (`sales.confirm_payment_manual`) |
| Phiếu hoàn | `/orders/refunds/` | `/orders/refunds/detail/?id=` | `sales.view_refund` (Quản lý chỉ xem), thao tác chỉ Chủ |

Trang `app/(console)/orders/**/page.tsx` chỉ gắn `ViewGuard` và đặt `Screen` của module; khối "Trợ lý AI" gắn ở cấp trang
(`AiDocBlockGate`, `targetModel="sales.salesorder"`, `targetId="<mã SO>,<pk>"`) — module này không import `features/ai`.
Đường cũ `/orders/?order=<id>&open=refund` (từ màn gọi xác nhận) chuyển sang `/orders/detail/?id=<id>&open=refund` và mở hộp lập phiếu hoàn.

## Nguyên tắc
- FE không tự suy luật: nút theo `available_actions` của BE (chi tiết đơn/khoản/phiếu); nút không dùng được nằm trong "…"
  (mờ, kèm lý do ngay trên mục). Lỗi BE hiện nguyên văn `detail`; 409 → `ConflictBanner`, không xử lý lần hai.
- Không có "Hoàn tác". SĐT hiện đủ (người dùng ERP có quyền), không lưu tên/SĐT/địa chỉ vào `localStorage`/URL/log.
- Quản lý không thấy giá vốn (`unit_cost` không có key trong JSON), không có nút "Xác nhận đã nhận tiền".

## File
| File | Làm gì |
|---|---|
| `api.ts` | `listOrders/getOrder/confirmPayment/cancelOrder`, `listPayments/getPayment/resolvePayment`, `listRefunds/getRefund`, `createRefund`, `confirmRefund/markRefundFailed/retryRefund` |
| `mock.ts` | mock theo contract BE (45 đơn, phạm vi NV giao, giá vốn theo quyền, BR-TT-03/04/05/08/09/10, BR-HT-01/04/05/09, `conflictNext()` giả lập 409) |
| `types.ts` · `labels.ts` · `messages.ts` | kiểu, nhãn/lựa chọn lọc, câu FE tự sinh |
| `orderDetailModel.ts` | thuần: bảng trạng thái → nút chính/"…"/lý do chặn, các bước StatusPath, timeline suy ra của khoản/phiếu |
| `filters.ts` · `amount.ts` · `refund.ts` | khoảng ngày giờ Việt Nam, đọc ô số tiền (1 ₫ – 12 chữ số), số còn được hoàn |
| `useOrderList.ts` · `usePagedList` (shared) | tải trang, "Tải thêm", bỏ kết quả trễ |
| `useDetail.ts` · `useIdParam.ts` · `DetailGate.tsx` | tải chi tiết theo `?id=` (tải/lỗi/404/không quyền), tải lại sau thao tác; đã có dữ liệu mà tải lại 404 → `scope_lost` (xoá dữ liệu, màn "Bạn không còn quyền xem mục này.", PV-13) |
| `useNow.ts` | đồng hồ giữ chỗ (`mm:ss`, chip tự đổi Đã huỷ khi hết giờ). Danh sách chưa có thanh AI: làm chung ở Lô 17 bằng `AiBarGate` (AI tắt thì 0 request) |
| `orders.module.css` | style riêng (chỉ token) |
| `components/OrdersSectionTabs.tsx` | 3 tab theo route, ẩn tab người dùng không có quyền |
| `components/OrdersScreen.tsx` · `PaymentQueueScreen.tsx` · `RefundQueueScreen.tsx` | ba danh sách (ListPage: tìm, lọc, bảng, tải thêm) |
| `components/OrderDetailScreen.tsx` · `PaymentDetailScreen.tsx` · `RefundDetailScreen.tsx` | ba trang chi tiết (DetailPage) |
| `components/ActionModal.tsx` | khung hộp thao tác dùng chung (nút chính ghi số tiền, chống bấm đúp, lỗi BE, 409) |
| `components/ConfirmPaymentModal.tsx` | F2a: xác nhận đã nhận tiền |
| `components/CancelOrderModal.tsx` | F2b: huỷ đơn 2 bước (chọn lý do → hậu quả) |
| `components/RefundModal.tsx` | F2c: lập phiếu hoàn (từ đơn có hoá đơn hoặc từ khoản tiền), `request_id` UUID chống tạo trùng |
| `components/AttachOrderModal.tsx` · `ConfirmOrderModal.tsx` | F2d: gắn khoản vào đơn · F2e: xác nhận đơn đủ tiền |
| `components/RefundActionModals.tsx` | F2f: xác nhận đã hoàn · F2g: báo chuyển thất bại · chuyển lại |

Chưa làm trong lô này: F2j đổi người nhận/địa chỉ (thuộc `/confirmation`).

## E2E (mock)
`e2e/ed_batch3_orders.py` (giao diện Lô 3), `e2e/s10_s11_orders.py`, `e2e/s12_s13_queue.py`, `e2e/s14_s16_cancel_refund.py`
(luật nghiệp vụ; dùng chung `e2e/orders_common.py`). Hook `window.__caveMock`: `orders("fail"|"empty"|"forbidden"|"detailfail"|"ok")`,
`payments(...)`, `refunds(...)`, `conflictNext()`, `resetOrders()`, `expireOrder(id)`, `orderJson/queueJson/refundQueueJson(user, …)`,
`confirmJson/cancelJson/resolveJson/refundJson/confirmRefundJson/markRefundFailedJson/retryRefundJson(user, …)`, `txnRefundsOf(id)`, `beDetail(key)`.
