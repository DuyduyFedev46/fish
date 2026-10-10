"""
Nhãn Shop (khách thấy) khi tra đơn — lô dọn chữ AI, W1 và W2; bảng `state` ở Shop lô 3+4 (SHOP-3-02).

Khách không bao giờ thấy mã thô hay chữ kỹ thuật. Bảng theo `doc/thuat-ngu-va-trang-thai.md` mục 4, cột "Shop"
(T1, T2, T24–T30). Bảng đã áp tên chuẩn (lô áp tên chuẩn, Pha A).
"""

UNKNOWN_STATUS_LABEL = "Đang cập nhật"

# Nhãn khách thấy cho hai trạng thái đơn mà nhãn model không hợp (T1, T2 trong thuat-ngu-va-trang-thai.md mục 4).
SHOP_ORDER_STATUS_LABELS = {
    "BOOKED": "Chờ thanh toán",  # T1
    "AUTO_CANCELLED": "Đã huỷ vì quá giờ thanh toán",  # T2
}

# Nhãn theo `state` tính sẵn của tra đơn (02b §3.4.2, BR-BH-26). Khách không bao giờ thấy mã thô.
SHOP_STATE_LABELS = {
    "awaiting_payment": SHOP_ORDER_STATUS_LABELS["BOOKED"],
    "hold_expired": SHOP_ORDER_STATUS_LABELS["BOOKED"],
    "expired": SHOP_ORDER_STATUS_LABELS["AUTO_CANCELLED"],
    "cancelled": "Đã huỷ",
    "preparing": "Đang chuẩn bị hàng",
    "delivering": "Đang giao",
    "delivery_failed": "Giao không thành công",
    "completed": "Đã giao",
}
PREPARING_CONFIRMING_LABEL = "Đã thanh toán – chờ vựa gọi xác nhận"

SHOP_DELIVERY_STATUS_LABELS = {
    "CONFIRMING": "Chờ vựa gọi xác nhận",  # T24
    "PREPARING": "Đang soạn hàng",  # T25
    "READY": "Đã soạn xong, chờ giao",  # T26
    "DELIVERING": "Đang giao",  # T27
    "COMPLETED": "Đã giao",  # T28
    "FAILED": "Giao chưa thành công, vựa sẽ liên hệ lại",  # T29
    "CANCELLED": "Đã huỷ",  # T30
}


def shop_state_label(state: str, delivery_status: str | None = None) -> str:
    """`preparing` + phiếu giao đang CONFIRMING là câu riêng; còn lại theo bảng."""
    if state == "preparing" and delivery_status == "CONFIRMING":
        return PREPARING_CONFIRMING_LABEL
    return SHOP_STATE_LABELS.get(state, UNKNOWN_STATUS_LABEL)


def shop_delivery_status_label(status: str) -> str:
    return SHOP_DELIVERY_STATUS_LABELS.get(status, UNKNOWN_STATUS_LABEL)
