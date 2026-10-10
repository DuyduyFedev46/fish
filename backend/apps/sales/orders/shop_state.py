"""
Trạng thái đơn tính sẵn cho trang đơn Shop (SHOP-3-02, BR-BH-26, 02b §3.4.2, §6.3).

BE tính `state` để FE chỉ ánh xạ màn (E6), không tự suy từ `status` + giờ. Module chỉ ĐỌC, không đổi trạng thái đơn.
Server luôn thắng: `awaiting_payment` -> `hold_expired` khi quá `booked_expires_at` mà job chưa chạy.
"""
from apps.delivery.models import DeliveryNote
from apps.sales.models import SalesOrder

from .shop_labels import SHOP_DELIVERY_STATUS_LABELS, shop_state_label

S = DeliveryNote.Status
O = SalesOrder.Status

# `delivery.step` công khai theo trạng thái phiếu giao (02b §3.4.2). CANCELLED/không phiếu -> không có khối.
_DELIVERY_STEP = {
    S.CONFIRMING: "preparing",
    S.PREPARING: "preparing",
    S.READY: "preparing",
    S.DELIVERING: "delivering",
    S.COMPLETED: "delivered",
    S.FAILED: "failed",
}


def latest_delivery_note(order):
    invoice = getattr(order, "invoice", None)
    if invoice is None:
        return None
    return invoice.delivery_notes.order_by("-created_at", "-id").first()


def has_payment_transaction(order) -> bool:
    return order.payments.exists()


def order_state(order, *, now, note=None, has_payment=False) -> str:
    status = order.status
    if status == O.BOOKED:
        expires = order.booked_expires_at
        return "hold_expired" if expires is not None and now >= expires else "awaiting_payment"
    if status == O.AUTO_CANCELLED:
        return "cancelled" if has_payment else "expired"
    if status == O.CANCELLED:
        return "cancelled"
    if status == O.COMPLETED:
        return "completed"
    note_status = note.status if note is not None else None
    if note_status == S.FAILED:
        return "delivery_failed"
    if note_status in (S.DELIVERING, S.COMPLETED):
        # Phiếu đã giao xong nhưng đơn chưa Hoàn tất (còn phiếu khác): vẫn "đang giao".
        return "delivering"
    return "preparing"


def delivery_block(note):
    if note is None or note.status not in _DELIVERY_STEP:
        return None
    return {
        "step": _DELIVERY_STEP[note.status],
        "step_label": SHOP_DELIVERY_STATUS_LABELS.get(note.status, ""),
    }


def state_label(state, note) -> str:
    return shop_state_label(state, note.status if note is not None else None)
