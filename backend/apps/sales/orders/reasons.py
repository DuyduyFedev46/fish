"""
Lý do hiển thị ở danh sách đơn (ERP theo design, Lô 3, R3 trong 02b §3.8). READ-ONLY.

`order_reason(order)` trả `{"code", "label"}` hoặc `None`. Chỉ trả NHÃN cố định theo mã (không bao giờ
chữ tự do như ghi chú huỷ, lý do phiếu hoàn): các chữ đó có thể chứa SĐT, tên khách (bất biến 9).

Thứ tự ưu tiên:
1. `AUTO_CANCELLED` → "Hết giờ giữ chỗ" (BR-BH-03).
2. `CANCELLED` → nhãn của `SalesCreditNote.reason_code` (BR-HT-05); không có mã thì xét tiếp.
3. Có giao dịch `UNDERPAID` còn mở → "Chuyển thiếu tiền" (BR-TT-04).
4. Phiếu giao mới nhất ở `FAILED` → nhãn `failure_reason` của phiếu (B5, Lô 4); chưa có hoặc để trống
   thì "Giao thất bại" (BR-GH-04).

Gọi trên queryset đã `prefetch_related("payments", "invoice__credit_notes", "invoice__delivery_notes")`
để không phát sinh truy vấn theo từng dòng.
"""
from apps.delivery.models import DeliveryNote
from apps.sales.models import PaymentTransaction, SalesOrder

from . import services

AUTO_CANCELLED_CODE = "AUTO_CANCELLED"
CANCELLED_CODE = "CANCELLED"
UNDERPAID_CODE = "UNDERPAID"
DELIVERY_FAILED_CODE = "DELIVERY_FAILED"

_CANCEL_LABELS = {**services.CANCEL_REASON_LABELS, **services.SYSTEM_CANCEL_REASON_CODES}


def _reason(code, label):
    return {"code": code, "label": label}


def _cancel_reason(invoice):
    if invoice is None:
        return None
    notes = sorted(invoice.credit_notes.all(), key=lambda n: n.pk)
    if not notes or not notes[-1].reason_code:
        return None
    code = notes[-1].reason_code
    if code not in _CANCEL_LABELS:  # L2: chỉ trả mã thuộc tập cố định, mã lạ → nhãn chung
        return _reason(CANCELLED_CODE, "Đã huỷ")
    return _reason(code, _CANCEL_LABELS[code])


def _has_open_underpaid(order):
    return any(
        p.match_status == PaymentTransaction.MatchStatus.UNDERPAID
        and p.resolution_status == PaymentTransaction.ResolutionStatus.OPEN
        for p in order.payments.all()
    )


def _failed_delivery_reason(invoice):
    if invoice is None:
        return None
    notes = sorted(invoice.delivery_notes.all(), key=lambda n: n.pk)
    if not notes or notes[-1].status != DeliveryNote.Status.FAILED:
        return None
    note = notes[-1]
    code = getattr(note, "failure_reason", "") or ""  # field của B5 (Lô 4), chưa có thì rỗng
    if code:
        return _reason(code, note.get_failure_reason_display())
    return _reason(DELIVERY_FAILED_CODE, "Giao thất bại")


def order_reason(order):
    if order.status == SalesOrder.Status.AUTO_CANCELLED:
        return _reason(AUTO_CANCELLED_CODE, "Hết giờ giữ chỗ")
    invoice = getattr(order, "invoice", None)
    if order.status == SalesOrder.Status.CANCELLED:
        cancelled = _cancel_reason(invoice)
        if cancelled is not None:
            return cancelled
    if _has_open_underpaid(order):
        return _reason(UNDERPAID_CODE, "Chuyển thiếu tiền")
    return _failed_delivery_reason(invoice)
