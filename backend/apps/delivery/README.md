# delivery — Soạn & giao hàng (P-06, P-08 phía NV giao)

Phiếu giao tự tạo khi hoá đơn bán được xuất (`signals.py`). State machine PREPARING → READY → DELIVERING → COMPLETED/FAILED;
COMPLETED không quay lui (BR-GH-05); thất bại quá ngưỡng cần quyết định (BR-GH-04); NV giao chỉ thấy phiếu của mình (BR-PQ-12).
Endpoint: `/api/delivery/notes/` (list lọc `?status=` nhiều giá trị, dấu phẩy), `POST /api/delivery/notes/{id}/status/`.
App 1 tính năng → giữ phẳng (`services.py`, `api.py`, `serializers.py`, `models.py`, `tests/`).

**Module con `confirmation/`** (việc gọi xác nhận đơn cho CSKH, trước đây tên `cskh/`; đổi tên P8b Lô 1): `services.py` (nghiệp vụ hàng chờ, ghi
kết quả gọi, hạn giờ), `scope.py` (phạm vi dữ liệu cá nhân của vai CSKH, BR-GH-18), `serializers.py`, `api.py`. Từ P8b Lô 3: route
`/api/confirmation/...` (route cũ `/api/cskh/...` là alias tới Lô 5, cùng một view), env `CONFIRMATION_*` (env `CSKH_*` là fallback),
lệnh `process_confirmation_deadlines` / `check_confirmation_job_health` (tên cũ bọc gọi), logger `cangca.delivery.confirmation`.
Cả hai tiền tố route nằm trong `FORBIDDEN_PREFIXES` của AI vì trả tên, SĐT, địa chỉ khách.

**S14 (Lô L9, sales/orders):** thêm trạng thái `CANCELLED` ("Đã huỷ theo đơn") — không tới qua `advance_status`/`set_status`
mà do `apps.sales.orders.services.cancel_paid_order` gán thẳng khi huỷ đơn đã thanh toán (BR-GH-07). Không quay lui, giống
COMPLETED. Lọc `?status=PREPARING,READY,...` giúp phiếu CANCELLED tự vắng mặt khỏi danh sách hoạt động mặc định.
