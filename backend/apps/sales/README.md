# sales — Bán hàng (P-05, P-07)

Khách đặt trên Shop → đơn giữ chỗ (TTL) → tiền về (webhook) → hoá đơn trừ kho → (giao hàng ở `delivery`) → huỷ/hoàn tiền.
BR chính: BR-PQ-11 (đơn/hoá đơn chỉ Hệ thống tạo), BR-BH-02/06/07 (giữ chỗ theo lô, chọn lô FEFO), BR-BH-11 (lô chốt lúc tạo đơn), BR-TT-03 (idempotent), BR-HT (hoàn tiền).
Model: `models/` (customers, orders, invoices, payments, refunds, credit_notes). Tiện ích tiền/mã chứng từ: `utils.py`.

| Module | Làm gì |
|---|---|
| `orders/` | tạo đơn + giữ chỗ, job huỷ đơn quá TTL, huỷ đơn đã thanh toán, Shop API đặt/tra đơn |
| `payments/` | nhận tiền (webhook nội bộ / xác nhận tay), xuất hoá đơn, hàng chờ giao dịch lệch |
| `refunds/` | tạo & xác nhận phiếu hoàn tiền |
| `credit_notes/` | chứng từ đảo doanh thu khi huỷ đơn đã thanh toán (BR-HT-10) — xem `credit_notes/README.md` |
| `customers/` | khách hàng, gộp theo số điện thoại |

Doanh thu của đơn huỷ được đảo bằng chứng từ đảo (BR-HT-06/10), phiếu hoàn chỉ là dòng tiền. Lệnh `backfill_credit_notes` lập bù cho đơn huỷ trước P8 (mặc định chỉ in).

`tasks.py` chỉ là điểm vào cho Celery (code thật ở `orders/tasks.py`); command ở `management/commands/`.
