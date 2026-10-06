"""
Dòng thời gian của một đơn (Lô L7) — READ-ONLY, ghép từ dữ liệu thật + AuditLog.

Nguồn:
- Chứng từ: chứng từ đảo doanh thu (`SalesCreditNote.issued_at`, BR-HT-10), đặt đơn (`SalesOrder.created_at`), giao dịch tiền (`PaymentTransaction.received_at`),
  hoá đơn (`SalesInvoice.issued_at`), tạo phiếu giao (`DeliveryNote.created_at`), phiếu hoàn
  (`Refund.created_at` / `confirmed_at`, người tạo / người xác nhận).
- AuditLog (BR-PQ-04/05): `cancel_unpaid_expired`, `cancel_paid_order` (đơn); `complete_order` (W37 S7: gộp vào mốc giao,
  riêng dòng chuyển bù `backfill` thành mốc `order_completed`);
  `delivery_advance_status`, `delivery_mark_failed` (phiếu giao);
  `return_to_warehouse`, `approve_returntostock`, `cancel_returntostock` (hàng hoàn về kho, P-08);
  `confirm_payment_manual` chỉ dùng để lấy NGƯỜI xác nhận tay, không thành dòng riêng.

Bất biến: KHÔNG đưa `changes` thô ra ngoài — nhãn tự dựng, chỉ chứa mã chứng từ, số tiền khách
trả/được hoàn (viết "x.xxx đ", `format_vnd_ui`), số kg, lý do huỷ dạng mã chuẩn đã map sang nhãn.
KHÔNG ghép chữ tự do (`Refund.reason`, `AuditLog.note`, ghi chú huỷ, lý do báo hoàn thất bại — có thể chứa SĐT/tên,
bất biến 9; Duy quyết 03/10 #3): lý do "Khác" chỉ hiện "Lý do khác", chi tiết xem ở chính chứng từ.
Không giá vốn (BR-PQ-15), không mật khẩu. actor=None → "Hệ thống".
Hoá đơn và phiếu giao do Hệ thống tạo (BR-PQ-11) nên luôn là "Hệ thống".
"""
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Q

from apps.accounts.models import AuditLog
from apps.common.ai_visibility import exclude_ai_audit_rows
from apps.delivery.models import DeliveryNote
from apps.inventory.models import ReturnToStock
from apps.sales.orders.completion import BACKFILL_MARKER, COMPLETE_ORDER_ACTION
from apps.sales.models import PaymentTransaction, Refund, SalesOrder
from apps.sales.utils import kg_str
from apps.common.formatting import format_vnd_ui

SYSTEM = "Hệ thống"

ORDER_MODEL = SalesOrder._meta.label
NOTE_MODEL = DeliveryNote._meta.label
RETURN_MODEL = ReturnToStock._meta.label
REFUND_MODEL = Refund._meta.label
PAYMENT_MODEL = PaymentTransaction._meta.label


@dataclass(frozen=True)
class TimelineEvent:
    at: datetime
    kind: str
    label: str
    actor_display: str
    doc: str = "order"
    doc_id: int | None = None  # pk chứng từ để FE làm link (chi tiết đơn: `doc: {type, id}`); None = không link
    actor_kind: str = "system"  # "system" | "user" | "ai"
    ai_level: str | None = None
    ai_config_version: int | None = None


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


def _cancel_reason_label(changes, note):
    """Lý do huỷ đơn cho nhãn dòng thời gian: CHỈ nhãn của mã chuẩn (Duy quyết 03/10 #3, bất biến 9).

    Mã "OTHER" hoặc audit cũ không có mã mà có ghi chú → "Lý do khác". Không bao giờ ghép chữ tự gõ.
    """
    from apps.sales.orders import services as order_services  # trễ: tránh vòng import

    code = (changes or {}).get("reason_code") or ""
    if code == "OTHER":
        return "Lý do khác"
    label = order_services.CANCEL_REASON_LABELS.get(code) or order_services.SYSTEM_CANCEL_REASON_CODES.get(code)
    if label:
        return label
    return "Lý do khác" if note else ""


def _audits(order, notes, returns, refunds):
    cond = Q(model_name=ORDER_MODEL, object_id=str(order.pk))
    # #15 (BR-TT-18): khoản ghi tay tiền về muộn không có audit trên đơn; lấy NGƯỜI ghi từ audit trên giao dịch.
    late_ids = [str(p.pk) for p in order.payments.all() if p.source == p.Source.MANUAL]
    if late_ids:
        cond |= Q(model_name=PAYMENT_MODEL, object_id__in=late_ids, action="record_late_payment")
    if notes:
        cond |= Q(model_name=NOTE_MODEL, object_id__in=[str(n.pk) for n in notes])
    if returns:
        cond |= Q(model_name=RETURN_MODEL, object_id__in=[str(r.pk) for r in returns])
    if refunds:
        cond |= Q(model_name=REFUND_MODEL, object_id__in=[str(r.pk) for r in refunds])
    return list(
        exclude_ai_audit_rows(AuditLog.objects.filter(cond))
        .select_related("actor__staff_profile", "ai_actor__staff_profile")
        .order_by("created_at", "id")
    )



def build_timeline(order):
    """Trả list TimelineEvent tăng dần theo thời gian (hoà giờ → giữ thứ tự nghiệp vụ)."""
    invoice = getattr(order, "invoice", None)
    notes = sorted(invoice.delivery_notes.all(), key=lambda n: n.pk) if invoice else []
    notes_by_id = {str(n.pk): n for n in notes}
    returns = sorted((r for n in notes for r in n.returns.all()), key=lambda r: r.pk)
    returns_by_id = {str(r.pk): r for r in returns}
    refunds = sorted(invoice.refunds.all(), key=lambda r: r.pk) if invoice is not None else []
    refunds_by_id = {str(r.pk): r for r in refunds}
    audits = _audits(order, notes, returns, refunds)
    # W37 S7 (BR-BH-18): phiếu làm đơn Hoàn tất qua đường giao xong (không phải chuyển bù) gộp vào mốc giao.
    merged_note_ids = {
        str((a.changes or {}).get("delivery_note_id"))
        for a in audits
        if a.model_name == ORDER_MODEL and a.action == COMPLETE_ORDER_ACTION
        and not (a.changes or {}).get("backfill")
    }

    manual_actor = {
        (a.changes or {}).get("bank_txn_id"): a.actor
        for a in audits
        if (a.model_name == ORDER_MODEL and a.action == "confirm_payment_manual")
        or (a.model_name == PAYMENT_MODEL and a.action == "record_late_payment")
    }

    events = [
        TimelineEvent(
            order.created_at, "order_placed",
            f"Khách đặt đơn {order.code} ({format_vnd_ui(order.total_amount)})", SYSTEM,
            doc="order", actor_kind="system",
        )
    ]

    for p in sorted(order.payments.all(), key=lambda p: (p.received_at, p.pk)):
        who_user = manual_actor.get(p.bank_txn_id) if p.source == p.Source.MANUAL else None
        events.append(TimelineEvent(
            p.received_at, "payment_received",
            f"Nhận {format_vnd_ui(p.amount)} · {p.get_source_display()} · "
            f"{p.get_match_status_display()} (mã GD {p.bank_txn_id})",
            actor_display(who_user),
            doc="order",
            actor_kind="user" if who_user else "system",
        ))

    if invoice is not None:
        events.append(TimelineEvent(
            invoice.issued_at, "invoice_issued",
            f"Xuất hoá đơn {invoice.code}", SYSTEM,
            doc="invoice", actor_kind="system",
        ))
    for n in notes:
        events.append(TimelineEvent(
            n.created_at, "delivery_created",
            f"Tạo phiếu giao {n.code} (Soạn hàng)", SYSTEM,
            doc="delivery", actor_kind="system",
        ))

    for a in audits:
        event = _audit_event(a, notes_by_id, returns_by_id, refunds_by_id, merged_note_ids)
        if event is not None:
            events.append(event)

    if invoice is not None:
        for r in refunds:
            events.append(TimelineEvent(
                r.created_at, "refund_created",
                # Bất biến 9: KHÔNG ghép `Refund.reason` (chữ tự do, có thể chứa SĐT/tên). Lý do xem ở phiếu hoàn.
                f"Tạo phiếu hoàn {format_vnd_ui(r.amount)}",
                actor_display(r.created_by),
                doc="refund", doc_id=r.pk,
                actor_kind="user" if r.created_by else "system",
            ))
            if r.confirmed_at is not None:
                events.append(TimelineEvent(
                    r.confirmed_at, "refund_confirmed",
                    f"Đã hoàn {format_vnd_ui(r.amount)} (mã GD {r.bank_txn_ref})",
                    actor_display(r.confirmed_by),
                    doc="refund",
                    actor_kind="user" if r.confirmed_by else "system",
                ))

    if invoice is not None:
        for cn in invoice.credit_notes.all():
            events.append(TimelineEvent(
                cn.issued_at, "credit_note_issued",
                f"Lập chứng từ đảo doanh thu {cn.code} ({format_vnd_ui(cn.amount)})",
                actor_display(cn.created_by),
                doc="invoice",
                actor_kind="user" if cn.created_by else "system",
            ))

    # sort ổn định: cùng thời điểm giữ thứ tự thêm vào (đặt → tiền → hoá đơn → phiếu giao …)
    return sorted(events, key=lambda e: e.at)


def _audit_event(a, notes_by_id, returns_by_id, refunds_by_id, merged_note_ids=frozenset()):
    if a.actor_kind == AuditLog.ActorKind.AI:
        who = f"AI của {actor_display(a.ai_actor)}"
        kind_actor = "ai"
        ai_lvl = getattr(a, "ai_level", None) or "C"
        ai_cfg = getattr(a, "ai_config_version", None)
    elif a.actor_kind == AuditLog.ActorKind.USER:
        who = actor_display(a.actor)
        kind_actor = "user"
        ai_lvl = None
        ai_cfg = None
    else:
        who = SYSTEM
        kind_actor = "system"
        ai_lvl = None
        ai_cfg = None

    changes = a.changes or {}
    if a.model_name == ORDER_MODEL:
        if a.action == "cancel_unpaid_expired":
            return TimelineEvent(
                a.created_at, "auto_cancelled",
                "Tự huỷ vì quá hạn giữ chỗ, đã nhả hàng giữ", who,
                doc="order", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
            )
        if a.action == "cancel_paid_order":
            reason_label = _cancel_reason_label(changes, a.note)
            reason = f" — lý do: {reason_label}" if reason_label else ""
            restored = changes.get("stock_restored", True)  # S14: FAILED thì không hoàn kho (Q8b)
            label = "Huỷ đơn, hoàn hàng về lô gốc" if restored else "Huỷ đơn (hàng đang ở người giao, chưa hoàn kho)"
            return TimelineEvent(
                a.created_at, "cancelled", f"{label}{reason}", who,
                doc="order", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
            )
        if a.action == COMPLETE_ORDER_ACTION:
            if changes.get("backfill") != BACKFILL_MARKER:
                return None  # đã gộp vào mốc "Đã giao — đơn hoàn tất"
            return TimelineEvent(
                a.created_at, "order_completed", "Hệ thống chuyển đơn sang Hoàn tất (chuyển bù)", SYSTEM,
                doc="order", actor_kind="system",
            )
        return None
    if a.model_name == NOTE_MODEL:
        note = notes_by_id.get(a.object_id)
        code = note.code if note else a.object_repr
        if a.action == "delivery_advance_status":
            status = changes.get("status") or {}
            to = status.get("to")
            if to == DeliveryNote.Status.COMPLETED:
                label = (
                    f"Đã giao — đơn hoàn tất ({code})" if a.object_id in merged_note_ids
                    else f"Giao hàng thành công ({code})"
                )
                return TimelineEvent(
                    a.created_at, "delivered", label, who,
                    doc="delivery", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
                )
            return TimelineEvent(
                a.created_at, "delivery_status",
                f"Phiếu giao {code}: {_note_status_label(status.get('from'))} → {_note_status_label(to)}",
                who,
                doc="delivery", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
            )
        if a.action == "delivery_mark_failed":
            attempts = (changes.get("failed_attempts") or {}).get("to")
            label = f"Giao thất bại lần {attempts} ({code})"
            if changes.get("needs_decision"):
                label += " — cần Quản lý/Chủ quyết định"
            return TimelineEvent(
                a.created_at, "delivery_failed", label, who,
                doc="delivery", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
            )
        return None
    if a.model_name == RETURN_MODEL:
        rt = returns_by_id.get(a.object_id)
        if rt is None:
            return None
        if a.action == "return_to_warehouse":
            # Phiếu đã huỷ không còn "chờ duyệt" (TLA-L1); dòng huỷ riêng ngay sau đó.
            pending = "" if rt.status == ReturnToStock.Status.CANCELLED else " — chờ duyệt"
            return TimelineEvent(
                a.created_at, "return_to_warehouse",
                f"Mang hàng về kho {kg_str(rt.qty)} kg{pending}", who,
                doc="return", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
            )
        if a.action == "cancel_returntostock":
            return TimelineEvent(
                a.created_at, "return_cancelled",
                f"Huỷ phiếu hàng về kho {kg_str(rt.qty)} kg", who,
                doc="return", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
            )
        if a.action == "approve_returntostock":
            decision = (changes.get("decision") or {}).get("to")
            try:
                decision_label = ReturnToStock.Decision(decision).label
            except ValueError:
                decision_label = decision or ""
            return TimelineEvent(
                a.created_at, "return_approved",
                f"Duyệt hàng về kho: {decision_label}", who,
                doc="return", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
            )
        return None
    if a.model_name == REFUND_MODEL:
        r = refunds_by_id.get(a.object_id)
        if r is None:
            return None
        if a.action == "mark_refund_failed":
            # Quyết định 03/10 #3: không chép lý do tự gõ; lý do xem ở chính phiếu hoàn.
            label = f"Phiếu hoàn {format_vnd_ui(r.amount)} chuyển thất bại"
            return TimelineEvent(
                a.created_at, "refund_failed", label, who,
                doc="refund", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
            )
        if a.action == "retry_refund":
            return TimelineEvent(
                a.created_at, "refund_retry",
                f"Thử chuyển lại phiếu hoàn {format_vnd_ui(r.amount)}", who,
                doc="refund", actor_kind=kind_actor, ai_level=ai_lvl, ai_config_version=ai_cfg,
            )
        return None
    return None
