# delivery — Soạn & giao hàng (P-06, P-08 phía NV giao)

Phiếu giao tự tạo khi hoá đơn bán được xuất (`signals.py`). State machine PREPARING → READY → DELIVERING → COMPLETED/FAILED;
COMPLETED không quay lui (BR-GH-05); thất bại quá ngưỡng cần quyết định (BR-GH-04); NV giao chỉ thấy phiếu của mình (BR-PQ-12).
Endpoint: `/api/delivery/notes/`, `POST /api/delivery/notes/{id}/status/`. App 1 tính năng → giữ phẳng
(`services.py`, `api.py`, `serializers.py`, `models.py`, `tests/`).
