# delivery — Soạn & giao hàng (P-06, P-08 phía NV giao)

Phiếu giao tự tạo khi hoá đơn bán được xuất (`signals.py`). State machine PREPARING → READY → DELIVERING → COMPLETED/FAILED;
COMPLETED không quay lui (BR-GH-05); thất bại quá ngưỡng cần quyết định (BR-GH-04); NV giao chỉ thấy phiếu của mình (BR-PQ-12).
Endpoint: `/api/delivery/notes/` (list lọc `?status=` nhiều giá trị, dấu phẩy), `POST /api/delivery/notes/{id}/status/`.
App 1 tính năng → giữ phẳng (`services.py`, `api.py`, `serializers.py`, `models.py`, `tests/`).

**S14 (Lô L9, sales/orders):** thêm trạng thái `CANCELLED` ("Đã huỷ theo đơn") — không tới qua `advance_status`/`set_status`
mà do `apps.sales.orders.services.cancel_paid_order` gán thẳng khi huỷ đơn đã thanh toán (BR-GH-07). Không quay lui, giống
COMPLETED. Lọc `?status=PREPARING,READY,...` giúp phiếu CANCELLED tự vắng mặt khỏi danh sách hoạt động mặc định.
