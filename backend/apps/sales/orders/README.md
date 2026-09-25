# sales/orders — Đơn hàng (P-05, P-07 huỷ đơn)

Tạo đơn BOOKED + giữ chỗ theo lô chọn FEFO (BR-BH-02/05/06/07; lô chốt một lần lúc tạo đơn, BR-BH-11), giá & ưu đãi (BR-DM-02/08), đóng băng giá/công thức (BR-BH-08).
Job huỷ đơn quá TTL idempotent (BR-BH-03/04, `tasks.py`); huỷ đơn đã thanh toán hoàn kho lô gốc (BR-HT-05, quyền `cancel_paid_order`).
Endpoint: `POST /api/shop/orders/`, `GET /api/shop/orders/{code}/?phone_last4=` (`shop_api.py`); `/api/sales/orders/` (chỉ đọc) + `POST …/{id}/cancel/`.
S10: list lọc `status` (nhiều, dấu phẩy), `date_from`/`date_to` (ngày tạo, giờ VN), `q` (mã đơn/SĐT, khớp một phần), 20 dòng/trang;
chi tiết có dòng hàng, phân bổ lô (`unit_cost` chỉ với `view_costprice`), hoá đơn, thanh toán, phiếu giao, hoàn tiền, `available_actions`
(`services.available_actions` — luật + quyền). S11: `POST …/{id}/confirm-payment` (chỉ Chủ) gọi `payments.services.confirm_payment_manual`.
L7 bổ sung: `q` tìm thêm theo tên khách (không dấu, không phân biệt hoa thường — `utils.fold_text`); chi tiết thêm
`*_label` (phiếu giao, giao dịch, phiếu hoàn) và `timeline` (`timeline.py` — ghép chứng từ + AuditLog, không giá vốn).
File chính: `services.py`, `shop_api.py`, `api.py`, `timeline.py`, `tasks.py`; `tests/base.py` là dữ liệu nền cho test payments/refunds.
