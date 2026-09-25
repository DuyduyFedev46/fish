# features/orders — Đơn & tiền

Story: **S10** (danh sách + chi tiết đơn) và **S11** (Chủ xác nhận đã nhận tiền thủ công) — lô L7. Thay list 8 đơn đọc từ
`/api/dashboard/summary/` (S8) bằng endpoint đơn riêng. Contract thực tế: `03-dev-notes.md` mục "Lô L7 — S10, S11 (BE)".

- `GET /api/sales/orders/?status=A,B&date_from=&date_to=&q=&page=` — 20 dòng/trang; `q` khớp một phần mã đơn hoặc SĐT (BE lọc).
- `GET /api/sales/orders/{id}/` — khách, dòng hàng, phân bổ lô (`unit_cost` chỉ có key khi có `view_costprice`), hoá đơn,
  thanh toán, giao hàng, hoàn tiền, `available_actions`. Ngoài phạm vi (NV giao, S5) → 404.
- `POST /api/sales/orders/{id}/confirm-payment/` `{bank_txn_id, amount}` → `PAID` / `UNDERPAID` / `ORPHAN` (+ `duplicate`).
  Cần `sales.confirm_payment_manual` (chỉ Chủ). Nút chỉ hiện khi `available_actions` có `confirm_payment` (đơn Giữ chỗ và Tự huỷ).
- Quyền xem màn (menu, `ViewGuard`): `sales.view_salesorder` và không phải người CHỈ thuộc `nv_giao`.
- FE không tự suy luật: nút theo `available_actions`; kết quả xác nhận theo `result` BE; lỗi BE hiện nguyên văn `detail`.
  `cancel` (S14), `create_refund` (S15) có trong `available_actions` nhưng chưa có màn → chưa vẽ nút.

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

E2E: `e2e/s10_s11_orders.py` (mock). Mock trong DevTools: `__caveMock.orders("fail"|"empty"|"forbidden"|"detailfail"|"ok")`,
`__caveMock.resetOrders()`, `__caveMock.orderJson(username, id)`.
