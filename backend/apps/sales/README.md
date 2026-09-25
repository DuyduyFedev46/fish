# sales — Bán hàng (P-05, P-07)

Khách đặt trên Shop → đơn giữ chỗ (TTL) → tiền về (webhook) → hoá đơn trừ kho → (giao hàng ở `delivery`) → huỷ/hoàn tiền.
BR chính: BR-PQ-11 (đơn/hoá đơn chỉ Hệ thống tạo), BR-BH-02/06/07 (giữ chỗ theo lô, chọn lô FEFO), BR-BH-11 (lô chốt lúc tạo đơn), BR-TT-03 (idempotent), BR-HT (hoàn tiền).
Model: `models/` (customers, orders, invoices, payments, refunds). Tiện ích tiền/mã chứng từ: `utils.py`.

| Module | Làm gì |
|---|---|
| `orders/` | tạo đơn + giữ chỗ, job huỷ đơn quá TTL, huỷ đơn đã thanh toán, Shop API đặt/tra đơn |
| `payments/` | nhận tiền (webhook nội bộ / xác nhận tay), xuất hoá đơn, hàng chờ giao dịch lệch |
| `refunds/` | tạo & xác nhận phiếu hoàn tiền |
| `customers/` | khách hàng, gộp theo số điện thoại |

`tasks.py` chỉ là điểm vào cho Celery (code thật ở `orders/tasks.py`); command ở `management/commands/`.
