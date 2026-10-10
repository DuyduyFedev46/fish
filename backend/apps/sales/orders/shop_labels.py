"""
Nhãn Shop (khách thấy) khi tra đơn — lô dọn chữ AI, W1 và W2.

Khách không bao giờ thấy mã thô hay chữ kỹ thuật. Bảng theo `doc/thuat-ngu-va-trang-thai.md` mục 4, cột "Shop"
(T1, T2, T24–T30). Bảng đã áp tên chuẩn (lô áp tên chuẩn, Pha A).
"""

UNKNOWN_STATUS_LABEL = "Đang cập nhật"

# Chỉ ghi đè trạng thái đơn mà nhãn model không hợp với khách; còn lại dùng `get_status_display()`.
SHOP_ORDER_STATUS_LABELS = {
    "BOOKED": "Chờ thanh toán",  # T1
    "AUTO_CANCELLED": "Đã huỷ vì quá giờ thanh toán",  # T2
}

SHOP_DELIVERY_STATUS_LABELS = {
    "CONFIRMING": "Chờ vựa gọi xác nhận",  # T24
    "PREPARING": "Đang soạn hàng",  # T25
    "READY": "Đã soạn xong, chờ giao",  # T26
    "DELIVERING": "Đang giao",  # T27
    "COMPLETED": "Đã giao",  # T28
    "FAILED": "Giao chưa thành công, vựa sẽ liên hệ lại",  # T29
    "CANCELLED": "Đã huỷ",  # T30
}


def shop_order_status_label(order) -> str:
    return SHOP_ORDER_STATUS_LABELS.get(order.status) or order.get_status_display()


def shop_delivery_status_label(status: str) -> str:
    return SHOP_DELIVERY_STATUS_LABELS.get(status, UNKNOWN_STATUS_LABEL)
