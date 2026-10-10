# CHỜ legal-vn / S-12: câu `message` là bản A tạm; thời hạn đọc từ settings.SHOP_CANCEL_CALLBACK_WITHIN.
"""
Thông báo cho khách khi đơn bị huỷ hoặc huỷ một phần, ở trang đơn Shop (SHOP-4-05, BR-HT-12, 02b §3.4.3).

Khác bản CS-10 cũ: KHÔNG có khối `refund` (hạn hoàn, đã hoàn, trạng thái phiếu hoàn). Shop chỉ nói lý do (nhãn cố định),
số tiền phần bị huỷ và "Cá Về sẽ gọi vào số điện thoại đặt hàng trong <thời hạn>". Không bao giờ đưa chữ tự do
(`cancel_note`, `Refund.reason`) hay dữ liệu cá nhân vào kết quả (bất biến 9).
"""
from decimal import Decimal

from django.conf import settings

from apps.common.formatting import format_vnd
from apps.sales.models import Refund, SalesOrder
from apps.sales.utils import money_str

DEFAULT_LABEL = "Cá Về đã huỷ đơn này"

# Bảng nhãn công khai CỐ ĐỊNH: mã lạ, rỗng hay OTHER đều rơi về câu chung.
PUBLIC_CANCEL_REASON_LABELS = {
    "CUSTOMER_CHANGED_MIND": "Huỷ theo yêu cầu của bạn",
    "DAMAGED_WHEN_PACKING": "Hàng không đạt khi soạn",
    "GIVE_UP_AFTER_FAILED": "Giao không thành công",
    "UNREACHABLE": "Không liên lạc được để xác nhận đơn",
    "UNREACHABLE_AUTO": "Không liên lạc được để xác nhận đơn",
    "PAID_AFTER_EXPIRY": "Hết giờ giữ hàng, tiền về sau",
    "PARTIAL": "Một phần đơn không giao được",
}


def public_reason_label(reason_code) -> str:
    return PUBLIC_CANCEL_REASON_LABELS.get(reason_code or "", DEFAULT_LABEL)


def _vnd_text(amount) -> str:
    """278000 -> "278.000đ" (UI-RULES §1.1)."""
    return format_vnd(amount).replace(" ₫", "đ")


def _notice(*, scope, reason_code, amount) -> dict:
    if reason_code not in PUBLIC_CANCEL_REASON_LABELS:
        reason_code = "OTHER"  # mã lạ/rỗng/OTHER: không lộ mã nội bộ, nhãn là câu chung
    within = settings.SHOP_CANCEL_CALLBACK_WITHIN
    return {
        "scope": scope,
        "reason_code": reason_code,
        "reason_label": public_reason_label(reason_code),
        "cancelled_amount": money_str(amount),
        "message": f"Cá Về sẽ gọi vào số điện thoại đặt hàng trong {within} để trả lại {_vnd_text(amount)}.",
        "hotline": settings.SHOP_HOTLINE,
        "policy_url": settings.SHOP_CANCEL_POLICY_URL,
    }


def _is_auto_cancelled_by_system(invoice, note) -> bool:
    task = getattr(note, "confirmation", None) if note is not None else None
    return bool(task and task.auto_cancelled_at)


def late_payment_total(order) -> Decimal:
    """Σ tiền về của đơn tự huỷ, bỏ dòng nghi trùng (02b §3.4.3)."""
    return sum((p.amount for p in order.payments.filter(duplicate_warning="")), Decimal("0"))


def build_cancel_notice(order: SalesOrder, *, note=None) -> dict | None:
    """`None` khi đơn không thuộc ba ca của bảng §3.4.3 (kể cả `expired`, đơn Hoàn tất có phiếu hoàn)."""
    status = order.status
    invoice = getattr(order, "invoice", None)

    if status == SalesOrder.Status.CANCELLED:
        reason = ""
        amount = order.total_amount
        if invoice is not None:
            amount = invoice.amount
            credit = invoice.credit_notes.order_by("-issued_at", "-id").first()
            reason = credit.reason_code if credit else ""
        if _is_auto_cancelled_by_system(invoice, note):
            reason = "UNREACHABLE_AUTO"
        return _notice(scope="full", reason_code=reason, amount=amount)

    if status == SalesOrder.Status.AUTO_CANCELLED:
        if not order.payments.exists():
            return None
        return _notice(scope="full", reason_code="PAID_AFTER_EXPIRY", amount=late_payment_total(order))

    if status == SalesOrder.Status.PROCESSING and invoice is not None:
        partial = [
            r for r in invoice.refunds.filter(is_partial=True).exclude(status=Refund.Status.FAILED)
        ]
        if partial:
            return _notice(scope="partial", reason_code="PARTIAL", amount=sum((r.amount for r in partial), Decimal("0")))
    return None
