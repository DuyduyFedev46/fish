"""
Lượt dùng mã giảm giá của đơn (SHOP-3b-04, BR-DM-19, 20, 02b §2.2 và §4).

    hold      : tạo đơn có mã -> giữ một lượt (HELD), đóng băng mã và số tiền giảm.
    mark_used : IPN khớp, cùng giao dịch lập hoá đơn -> USED. Không đổi gì nếu không phải HELD.
    release   : job tự huỷ đơn hết giờ -> RELEASED. Chạy lại không đổi gì (idempotent).

Đơn đã trả rồi bị huỷ (toàn phần hay một phần) KHÔNG gọi `release`: lượt vẫn USED, không trả lượt (BR-DM-20).
Các hàm chỉ đụng `VoucherRedemption` của đơn, KHÔNG khoá `Voucher`: người gọi đã khoá `SalesOrder` (thanh toán, job)
hoặc đã khoá `Voucher` đúng thứ tự (tạo đơn: đơn -> mã -> lô), nên không có đường khoá ngược.
Không có tên, SĐT, địa chỉ (bất biến 9).
"""
from django.utils import timezone

from apps.sales.models import VoucherRedemption

State = VoucherRedemption.State


def hold(*, order, voucher, discount) -> VoucherRedemption:
    return VoucherRedemption.objects.create(
        order=order, voucher=voucher, code=voucher.code, discount_amount=discount, state=State.HELD,
    )


def mark_used(*, order) -> bool:
    """HELD -> USED. Trả True nếu có đổi."""
    return bool(
        VoucherRedemption.objects.filter(order_id=order.pk, state=State.HELD).update(
            state=State.USED, used_at=timezone.now()
        )
    )


def release(*, order) -> bool:
    """HELD -> RELEASED. Trả True nếu có đổi (chạy lại trả False)."""
    return bool(
        VoucherRedemption.objects.filter(order_id=order.pk, state=State.HELD).update(
            state=State.RELEASED, released_at=timezone.now()
        )
    )
