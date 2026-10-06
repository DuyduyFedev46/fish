# CHỜ legal-vn: Nội dung thông báo tự huỷ và huỷ đơn cho khách hàng theo NĐ 356/2025.
"""
Thông báo cho khách hàng khi đơn bị huỷ (BR-GH-21, CS-10, 02b §4.4, §7).
Tuân thủ:
- Các con số lấy từ cấu hình động (settings), không viết cứng.
- Không lộ bất kỳ thông tin cá nhân khách (tên, SĐT, địa chỉ, người nhận hộ).
- Không lộ giá vốn.
"""
from datetime import timedelta
from django.conf import settings

from apps.common.formatting import format_local_date, format_vnd
from apps.sales.models import Refund, SalesOrder


# CHỜ legal-vn: Câu thông báo tự huỷ khi không liên lạc được
AUTO_CANCEL_MESSAGE_TEMPLATE = (
    "Cá Về đã gọi số điện thoại đặt hàng {max_attempts} lần trong {window_minutes} phút "
    "nhưng không liên lạc được, nên đơn được huỷ tự động để hoàn tiền lại cho quý khách. "
    "Số tiền {amount} sẽ được hoàn trong vòng {refund_deadline_days} ngày. "
    "Vui lòng liên hệ hotline {hotline} nếu cần hỗ trợ."
)

# CHỜ legal-vn: Câu thông báo khi đơn huỷ thủ công
MANUAL_CANCEL_MESSAGE = "Đơn đã được huỷ theo yêu cầu/xử lý của vựa."


def build_cancel_notice(order: SalesOrder) -> dict | None:
    """
    Dựng cấu trúc cancel_notice cho Shop tra cứu đơn (CS-10, 02b §4.4).
    Chỉ trả khi đơn CANCELLED và có hoá đơn.
    """
    if order.status != SalesOrder.Status.CANCELLED:
        return None

    invoice = getattr(order, "invoice", None)
    if invoice is None:
        return None

    # Kiểm tra xem có phải do Hệ thống tự huỷ không
    dn = invoice.delivery_notes.first()
    task = getattr(dn, "confirmation", None) if dn else None
    is_auto = bool(task and task.auto_cancelled_at)
    reason_code = "UNREACHABLE_AUTO" if is_auto else None

    # Tính toán thông tin hoàn tiền
    refunds = list(invoice.refunds.exclude(status=Refund.Status.FAILED))
    refund_days = getattr(settings, "REFUND_DEADLINE_DAYS", 30)

    if refunds:
        total_amount = sum(r.amount for r in refunds)
        all_refunded = all(r.status == Refund.Status.REFUNDED for r in refunds)
        if all_refunded:
            status_label = "Đã hoàn tiền"
            latest_confirmed = max((r.confirmed_at for r in refunds if r.confirmed_at), default=None)
            refunded_at = (
                format_local_date(latest_confirmed)
                if latest_confirmed
                else None
            )
        else:
            status_label = "Đang chờ hoàn tiền"
            refunded_at = None

        earliest_created = min((r.created_at for r in refunds if r.created_at), default=order.created_at)
        deadline_date = earliest_created + timedelta(days=refund_days)
        deadline_str = format_local_date(deadline_date)

        refund_data = {
            "amount": str(int(total_amount)),
            "status_label": status_label,
            "deadline": deadline_str,
            "refunded_at": refunded_at,
        }
    else:
        refund_data = {
            "amount": str(int(order.total_amount)),
            "status_label": "Đang chờ hoàn tiền",
            "deadline": format_local_date(order.created_at + timedelta(days=refund_days)),
            "refunded_at": None,
        }

    max_attempts = getattr(settings, "CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS", 3)
    window_minutes = getattr(settings, "CONFIRMATION_UNREACHABLE_WINDOW_MINUTES", 30)
    hotline = getattr(settings, "SHOP_HOTLINE", "")

    if is_auto:
        msg = AUTO_CANCEL_MESSAGE_TEMPLATE.format(
            max_attempts=max_attempts,
            window_minutes=window_minutes,
            amount=format_vnd(refund_data["amount"]),
            refund_deadline_days=refund_days,
            hotline=hotline,
        )
    else:
        msg = MANUAL_CANCEL_MESSAGE

    return {
        "reason_code": reason_code,
        "message": msg,
        "refund": refund_data,
        "contact": hotline,
    }
