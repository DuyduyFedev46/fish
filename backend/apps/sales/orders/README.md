# sales/orders — Đơn hàng (P-05, P-07 huỷ đơn)

Tạo đơn BOOKED + giữ chỗ theo lô chọn FEFO (BR-BH-02/05/06/07; lô chốt một lần lúc tạo đơn, BR-BH-11), giá & ưu đãi (BR-DM-02/08), đóng băng giá/công thức (BR-BH-08).
Job huỷ đơn quá TTL idempotent (BR-BH-03/04, `tasks.py`); huỷ đơn đã thanh toán hoàn kho lô gốc (BR-HT-05, quyền `cancel_paid_order`).
Endpoint: `POST /api/shop/orders/`, `GET /api/shop/orders/{code}/?phone_last4=` (`shop_api.py`); `/api/sales/orders/` (chỉ đọc) + `POST …/{id}/cancel/`.
S10: list lọc `status` (nhiều, dấu phẩy), `date_from`/`date_to` (ngày tạo, giờ VN), `q` (mã đơn/SĐT, khớp một phần), 20 dòng/trang;
chi tiết có dòng hàng, phân bổ lô (`unit_cost` chỉ với `view_costprice`), hoá đơn, thanh toán, phiếu giao, hoàn tiền, `available_actions`
(`services.available_actions` — luật + quyền). S11: `POST …/{id}/confirm-payment` (chỉ Chủ) gọi `payments.services.confirm_payment_manual`.
L7 bổ sung: `q` tìm thêm theo tên khách (không dấu, không phân biệt hoa thường — `utils.fold_text`); chi tiết thêm
`*_label` (phiếu giao, giao dịch, phiếu hoàn) và `timeline` (`timeline.py` — ghép chứng từ + AuditLog, không giá vốn).
L9 (S14): `cancel` nhận `{"reason_code", "note"}` (`CUSTOMER_CHANGED_MIND|DAMAGED_WHEN_PACKING|GIVE_UP_AFTER_FAILED|OTHER`,
OTHER bắt buộc `note`); chặn khi phiếu giao Đang giao (BR-GH-07) hoặc Hoàn tất (BR-GH-05). Hoàn kho lô gốc CHỈ khi hàng còn
ở kho (Soạn hàng/Chờ lấy) — phiếu Giao thất bại thì KHÔNG hoàn kho (Q8b, tránh cộng kho hai lần với luồng duyệt hàng hoàn
P-08). `available_actions.cancel` cũng ẩn theo cùng luật. `timeline` thêm `refund_failed`/`refund_retry` (S16).
File chính: `services.py`, `shop_api.py`, `api.py`, `timeline.py`, `tasks.py`; `tests/base.py` là dữ liệu nền cho test payments/refunds.

P5 (BR-BH-15, Q6): `create_order` làm tròn `total_amount` về **SỐ NGUYÊN ĐỒNG** (half-up,
`utils.money_vnd`) — dòng đơn (`SalesOrderLine.amount`) vẫn 2 chữ số thập phân như trước.
P1 (BR-TT-01): đặt hàng KHÔNG còn trả `vietqr` (QR giả) — lập tham số thanh toán cổng SePay
nay ở `payments/checkout.py` + `payments/shop_api.py` (`POST /api/shop/orders/{code}/checkout/`).
