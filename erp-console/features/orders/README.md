# features/orders — Đơn & tiền

**L9 (S14, S15, S16):** huỷ đơn đã thanh toán, lập phiếu hoàn từ đơn có hoá đơn, và màn con thứ ba
"Phiếu hoàn chờ chuyển" (`/orders/refunds/`, `sales.view_refund` — Chủ và Quản lý, hành động
xác nhận/thất bại/thử lại chỉ Chủ có `sales.confirm_refund`). Contract thật: 03-dev-notes.md
"Lô L9 — S14, S15, S16 (BE)".
- `POST /api/sales/orders/{id}/cancel/` `{reason_code, note}` → `available_actions` có `cancel`.
- `POST /api/sales/refunds/create/` nhánh `sales_invoice` (S15) — dùng chung `RefundForm.tsx` với nhánh
  `payment_transaction` (S13) qua prop `target: {kind: "payment"|"invoice", ...}`.
- `GET /api/sales/refunds/?status=PENDING,FAILED`, `POST /api/sales/refunds/{id}/confirm|mark-failed|retry/`.

**L8 (S12, S13):** hàng chờ thanh toán lệch là **màn con** `/orders/payments/` của "Đơn & tiền" (menu con, chỉ Chủ —
`sales.confirm_payment_manual`). Đặt trong CÙNG module vì cần tìm đơn (API đơn), mở chi tiết đơn liên quan và dùng chung ô số
tiền với S11 — tách module riêng sẽ phải import chéo vào ruột `orders`. Contract thật: 03-dev-notes.md "Lô L8 — S12, S13 (BE)".
- `GET /api/sales/payments/?resolution_status=OPEN|RESOLVED&match_status=&page=`, `GET /api/sales/payments/{id}/`
- `POST /api/sales/payments/{id}/resolve/` `{action: ATTACH_TO_ORDER, order_id, note}` | `{action: CONFIRM_ORDER, note}`
- `POST /api/sales/refunds/create/` `{payment_transaction, amount, reason, request_id}`

Story: **S10** (danh sách + chi tiết đơn) và **S11** (Chủ xác nhận đã nhận tiền thủ công) — lô L7. Thay list 8 đơn đọc từ
`/api/dashboard/summary/` (S8) bằng endpoint đơn riêng. Contract thực tế: `03-dev-notes.md` mục "Lô L7 — S10, S11 (BE)".

- `GET /api/sales/orders/?status=A,B&date_from=&date_to=&q=&page=` — 20 dòng/trang; `q` khớp một phần mã đơn hoặc SĐT (BE lọc).
- `GET /api/sales/orders/{id}/` — khách, dòng hàng, phân bổ lô (`unit_cost` chỉ có key khi có `view_costprice`), hoá đơn,
  thanh toán, giao hàng, hoàn tiền, `available_actions`. Ngoài phạm vi (NV giao, S5) → 404.
- `POST /api/sales/orders/{id}/confirm-payment/` `{bank_txn_id, amount}` → `PAID` / `UNDERPAID` / `ORPHAN` (+ `duplicate`).
  Cần `sales.confirm_payment_manual` (chỉ Chủ). Nút chỉ hiện khi `available_actions` có `confirm_payment` (đơn Giữ chỗ và Tự huỷ).
- Quyền xem màn (menu, `ViewGuard`): `sales.view_salesorder` và không phải người CHỈ thuộc `nv_giao`.
- FE không tự suy luật: nút theo `available_actions`; kết quả xác nhận theo `result` BE; lỗi BE hiện nguyên văn `detail`.
  `cancel` (S14) mở `CancelOrderForm`; `create_refund` (S15) mở `RefundForm` với `target.kind: "invoice"`.

| File | Làm gì |
|---|---|
| `api.ts` | `listOrders()`, `getOrder()`, `confirmPayment()` |
| `mock.ts` | mock 3 endpoint theo contract BE L7 (45 đơn, phạm vi NV giao, giá vốn theo quyền, luật BR-TT-03/04/05/08) |
| `types.ts` | `OrderListItem`, `OrderDetail`, `ConfirmPaymentResult`… |
| `labels.ts` | nhãn/tông trạng thái phiếu giao, giao dịch, phiếu hoàn (chép TextChoices BE); lựa chọn lọc |
| `messages.ts` | câu FE tự sinh của module |
| `useOrderList.ts` | tải trang 1 theo bộ lọc, "Tải thêm", bỏ kết quả trễ, sửa một dòng tại chỗ |
| `useNow.ts` | đồng hồ đếm lùi giữ chỗ (`mm:ss` theo `reserved_until` BE trả) |
| `orders.module.css` | style riêng của màn (chỉ token) |
| `components/OrdersScreen.tsx` | màn danh sách: tìm, lọc trạng thái/ngày, danh sách, tải thêm, toast |
| `components/OrderDetailSheet.tsx` | tấm chi tiết (tải, lỗi, chuyển bước xác nhận, báo kết quả) |
| `components/OrderDetailView.tsx` | nội dung chi tiết + thanh nút theo `available_actions` |
| `components/ConfirmPaymentForm.tsx` | S11: bước xác nhận đã nhận tiền (hậu quả, chống bấm đúp, lỗi BE) |
| `amount.ts` | `parseAmount` dùng chung cho mọi ô số tiền (S11 xác nhận tiền, S13 phiếu hoàn): tối thiểu 1 ₫, tối đa 12 chữ số |
| `usePagedList.ts` | khung tải danh sách phân trang DRF dùng chung (đơn S10, hàng chờ S12) |
| `components/OrdersTabs.tsx` | tab con Đơn hàng · Hàng chờ thanh toán (chỉ điện thoại, chỉ người mở được hàng chờ) |
| `components/PaymentQueueScreen.tsx` | S12: hàng chờ thanh toán lệch — lọc Đang chờ/Đã xử lý + loại lệch, tải thêm, mở khoản / mở đơn liên quan |
| `components/PaymentSheet.tsx` · `PaymentView.tsx` | S12: tấm chi tiết khoản tiền, nút theo `available_actions`, tải lại khoản sau thao tác |
| `components/AttachOrderForm.tsx` | S12: gắn khoản không khớp vào đơn (tìm đơn qua API đơn) |
| `components/ConfirmOrderForm.tsx` | S12: xác nhận đơn khi khách đã chuyển bù |
| `components/RefundForm.tsx` | S13 + S15: lập phiếu hoàn — `target.kind: "payment"` (không hoá đơn) hoặc `"invoice"` (đơn có hoá đơn), `request_id` UUID chống tạo trùng |
| `components/QueueFormParts.tsx` | mảnh chung của các bước trên + khoá gửi chống bấm đúp |
| `refund.ts` | `refundableOfOrder()` — số còn được hoàn của một đơn, tính từ `total_amount` + `refunds[]` (BE chưa trả field riêng) |
| `components/CancelOrderForm.tsx` | S14: huỷ đơn — chọn lý do (radio, OTHER bắt buộc ghi chú), hậu quả theo `stock_restored` |
| `components/RefundQueueScreen.tsx` | S16: danh sách phiếu hoàn chờ chuyển (`status=PENDING,FAILED`), tải thêm |
| `components/RefundSheet.tsx` · `RefundView.tsx` | S16: tấm chi tiết phiếu hoàn, nút theo `available_actions` |
| `components/ConfirmRefundForm.tsx` · `MarkRefundFailedForm.tsx` · `RetryRefundForm.tsx` | S16: ba bước xác nhận/thất bại/thử lại |

E2E: `e2e/s10_s11_orders.py`, `e2e/s12_s13_queue.py`, `e2e/s14_s16_cancel_refund.py` (mock). Mock hàng chờ:
`__caveMock.payments("fail"|"empty"|"forbidden"|"ok")`, `__caveMock.expireOrder(id)`,
`__caveMock.confirmRefund(refundId, ref)` (nay chạy qua đúng luật S16 dưới danh "Lộc"), `__caveMock.queueJson(username, status)`,
`__caveMock.resolveJson(username, id, body)`, `__caveMock.refundJson(username, body)`, `__caveMock.txnRefundsOf(txnId)`.
Mock đơn: `__caveMock.orders("fail"|"empty"|"forbidden"|"detailfail"|"ok")`, `__caveMock.resetOrders()`,
`__caveMock.orderJson(username, id)`, `__caveMock.cancelJson(username, id, body)`. Mock phiếu hoàn chờ chuyển:
`__caveMock.refunds("fail"|"empty"|"forbidden"|"ok")`, `__caveMock.refundQueueJson(username)`,
`__caveMock.confirmRefundJson/markRefundFailedJson/retryRefundJson(username, id, body)`.
