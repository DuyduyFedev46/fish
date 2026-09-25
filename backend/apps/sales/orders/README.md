# sales/orders — Đơn hàng (P-05, P-07 huỷ đơn)

Tạo đơn BOOKED + giữ chỗ FIFO theo lô (BR-BH-02/05/06/07), giá & ưu đãi (BR-DM-02/08), đóng băng giá/công thức (BR-BH-08).
Job huỷ đơn quá TTL idempotent (BR-BH-03/04, `tasks.py`); huỷ đơn đã thanh toán hoàn kho lô gốc (BR-HT-05, quyền `cancel_paid_order`).
Endpoint: `POST /api/shop/orders/`, `GET /api/shop/orders/{code}/?phone_last4=` (`shop_api.py`); `/api/sales/orders/` (chỉ đọc) + `POST …/{id}/cancel/`.
File chính: `services.py`, `shop_api.py`, `api.py`, `tasks.py`; `tests/base.py` là dữ liệu nền cho test payments/refunds.
