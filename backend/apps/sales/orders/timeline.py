"""
Dòng thời gian của một đơn (Lô L7) — READ-ONLY, ghép từ dữ liệu thật + AuditLog.

Nguồn:
- Chứng từ: đặt đơn (`SalesOrder.created_at`), giao dịch tiền (`PaymentTransaction.received_at`),
  hoá đơn (`SalesInvoice.issued_at`), tạo phiếu giao (`DeliveryNote.created_at`), phiếu hoàn
  (`Refund.created_at` / `confirmed_at`, người tạo / người xác nhận).
- AuditLog (BR-PQ-04/05): `cancel_unpaid_expired`, `cancel_paid_order` (đơn);
  `delivery_advance_status`, `delivery_mark_failed` (phiếu giao);
  `return_to_warehouse`, `approve_returntostock` (hàng hoàn về kho, P-08);
  `confirm_payment_manual` chỉ dùng để lấy NGƯỜI xác nhận tay, không thành dòng riêng.

Bất biến: KHÔNG đưa `changes` thô ra ngoài — nhãn tự dựng, chỉ chứa mã chứng từ, số tiền khách
trả/được hoàn, số kg, lý do huỷ. Không giá vốn (BR-PQ-15), không mật khẩu. actor=None → "Hệ thống".
Hoá đơn và phiếu giao do Hệ thống tạo (BR-PQ-11) nên luôn là "Hệ thống".
"""
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Q

from apps.accounts.models import AuditLog
from apps.delivery.models import DeliveryNote
from apps.inventory.models import ReturnToStock
from apps.sales.models import SalesOrder
from apps.sales.utils import kg_str, vnd_display

SYSTEM = "Hệ thống"

ORDER_MODEL = SalesOrder._meta.label
NOTE_MODEL = DeliveryNote._meta.label
RETURN_MODEL = ReturnToStock._meta.label


@dataclass(frozen=True)
class TimelineEvent:
    at: datetime
    kind: str
    label: str
    actor_display: str


def actor_display(user):
    if user is None:
        return SYSTEM
    profile = getattr(user, "staff_profile", None)
    return (profile.display_name if profile else "") or user.get_username()


def _note_status_label(code):
    try:
        return DeliveryNote.Status(code).label
    except ValueError:
        return code or ""


def _audits(order, notes, returns):
    cond = Q(model_name=ORDER_MODEL, object_id=str(order.pk))
    if notes:
        cond |= Q(model_name=NOTE_MODEL, object_id__in=[str(n.pk) for n in notes])
    if returns:
        cond |= Q(model_name=RETURN_MODEL, object_id__in=[str(r.pk) for r in returns])
    return list(
        AuditLog.objects.filter(cond)
        .select_related("actor__staff_profile")
        .order_by("created_at", "id")
    )


def build_timeline(order):
    """Trả list TimelineEvent tăng dần theo thời gian (hoà giờ → giữ thứ tự nghiệp vụ)."""
    invoice = getattr(order, "invoice", None)
    notes = sorted(invoice.delivery_notes.all(), key=lambda n: n.pk) if invoice else []
    notes_by_id = {str(n.pk): n for n in notes}
    returns = sorted((r for n in notes for r in n.returns.all()), key=lambda r: r.pk)
    returns_by_id = {str(r.pk): r for r in returns}
    audits = _audits(order, notes, returns)

    manual_actor = {
        (a.changes or {}).get("bank_txn_id"): a.actor
        for a in audits
        if a.model_name == ORDER_MODEL and a.action == "confirm_payment_manual"
    }

    events = [TimelineEvent(order.created_at, "order_placed",
                            f"Khách đặt đơn {order.code} ({vnd_display(order.total_amount)})", SYSTEM)]

    for p in sorted(order.payments.all(), key=lambda p: (p.received_at, p.pk)):
        who = manual_actor.get(p.bank_txn_id) if p.source == p.Source.MANUAL else None
        events.append(TimelineEvent(
            p.received_at, "payment_received",
            f"Nhận {vnd_display(p.amount)} · {p.get_source_display()} · "
            f"{p.get_match_status_display()} (mã GD {p.bank_txn_id})",
            actor_display(who),
        ))

    if invoice is not None:
        events.append(TimelineEvent(invoice.issued_at, "invoice_issued",
                                    f"Xuất hoá đơn {invoice.code}", SYSTEM))
    for n in notes:
        events.append(TimelineEvent(n.created_at, "delivery_created",
                                    f"Tạo phiếu giao {n.code} (Soạn hàng)", SYSTEM))

    for a in audits:
        event = _audit_event(a, notes_by_id, returns_by_id)
        if event is not None:
            events.append(event)

    if invoice is not None:
        for r in sorted(invoice.refunds.all(), key=lambda r: r.pk):
            events.append(TimelineEvent(
                r.created_at, "refund_created",
                f"Tạo phiếu hoàn {vnd_display(r.amount)}" + (f" — {r.reason}" if r.reason else ""),
                actor_display(r.created_by),
            ))
            if r.confirmed_at is not None:
                events.append(TimelineEvent(
                    r.confirmed_at, "refund_confirmed",
                    f"Đã hoàn {vnd_display(r.amount)} (mã GD {r.bank_txn_ref})",
                    actor_display(r.confirmed_by),
                ))

    # sort ổn định: cùng thời điểm giữ thứ tự thêm vào (đặt → tiền → hoá đơn → phiếu giao …)
    return sorted(events, key=lambda e: e.at)


def _audit_event(a, notes_by_id, returns_by_id):
    who = actor_display(a.actor)
    changes = a.changes or {}
    if a.model_name == ORDER_MODEL:
        if a.action == "cancel_unpaid_expired":
            return TimelineEvent(a.created_at, "auto_cancelled",
                                 "Tự huỷ vì quá hạn giữ chỗ, đã nhả hàng giữ", who)
        if a.action == "cancel_paid_order":
            reason = f" — lý do: {a.note}" if a.note else ""
            return TimelineEvent(a.created_at, "cancelled",
                                 f"Huỷ đơn, hoàn hàng về lô gốc{reason}", who)
        return None
    if a.model_name == NOTE_MODEL:
        note = notes_by_id.get(a.object_id)
        code = note.code if note else a.object_repr
        if a.action == "delivery_advance_status":
            status = changes.get("status") or {}
            to = status.get("to")
            if to == DeliveryNote.Status.COMPLETED:
                return TimelineEvent(a.created_at, "delivered", f"Giao hàng thành công ({code})", who)
            return TimelineEvent(
                a.created_at, "delivery_status",
                f"Phiếu giao {code}: {_note_status_label(status.get('from'))} → {_note_status_label(to)}",
                who,
            )
        if a.action == "delivery_mark_failed":
            attempts = (changes.get("failed_attempts") or {}).get("to")
            label = f"Giao thất bại lần {attempts} ({code})"
            if changes.get("needs_decision"):
                label += " — cần Quản lý/Chủ quyết định"
            return TimelineEvent(a.created_at, "delivery_failed", label, who)
        return None
    if a.model_name == RETURN_MODEL:
        rt = returns_by_id.get(a.object_id)
        if rt is None:
            return None
        if a.action == "return_to_warehouse":
            return TimelineEvent(a.created_at, "return_to_warehouse",
                                 f"Mang hàng về kho {kg_str(rt.qty)} kg — chờ duyệt", who)
        if a.action == "approve_returntostock":
            decision = (changes.get("decision") or {}).get("to")
            try:
                decision_label = ReturnToStock.Decision(decision).label
            except ValueError:
                decision_label = decision or ""
            return TimelineEvent(a.created_at, "return_approved",
                                 f"Duyệt hàng về kho: {decision_label}", who)
    return None
