"""
Dòng thời gian cho Giao dịch thanh toán (PaymentTransaction) — READ-ONLY.

Bất biến:
- Không rò PII: tuyệt đối không đưa raw_payload, nội dung CK, tên người chuyển vào bất kỳ dòng nào (DW-04-AC4).
- Không rò giá vốn.
- Sửa L-4: actor AI hiện "AI của <tên>" kèm mức, không hiện "Hệ thống".
"""
from apps.accounts.models import AuditLog
from apps.common.ai_visibility import exclude_ai_audit_rows
from apps.sales.models import PaymentTransaction
from apps.sales.orders.timeline import TimelineEvent, actor_display
from apps.common.formatting import format_vnd_ui

PAYMENT_MODEL = PaymentTransaction._meta.label
SYSTEM = "Hệ thống"


def build_payment_timeline(payment: PaymentTransaction) -> list[TimelineEvent]:
    """
    Trả danh sách TimelineEvent của giao dịch thanh toán theo thứ tự thời gian.
    """
    events: list[TimelineEvent] = []

    # 1. Sự kiện nhận giao dịch
    received_time = payment.received_at or payment.created_at
    events.append(
        TimelineEvent(
            at=received_time,
            kind="payment_received",
            label=f"Nhận giao dịch thanh toán {format_vnd_ui(payment.amount)} (mã GD {payment.bank_txn_id})",
            actor_display=SYSTEM,
            doc="payment",
            actor_kind="system",
        )
    )

    # 2. Sự kiện từ AuditLog
    audits = (
        exclude_ai_audit_rows(AuditLog.objects.filter(model_name=PAYMENT_MODEL, object_id=str(payment.pk)))
        .select_related("actor__staff_profile", "ai_actor__staff_profile")
        .order_by("created_at", "id")
    )

    for a in audits:
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

        if a.action == "record_late_payment":
            # BR-TT-18: nhãn chuẩn, chỉ mã GD + số tiền của chính giao dịch; không chép chữ tự do (#3).
            events.append(
                TimelineEvent(
                    at=a.created_at,
                    kind="payment_recorded_late",
                    label=f"Ghi tay tiền về muộn {format_vnd_ui(payment.amount)} (mã GD {payment.bank_txn_id})",
                    actor_display=who,
                    doc="payment",
                    actor_kind=kind_actor,
                    ai_level=ai_lvl,
                    ai_config_version=ai_cfg,
                )
            )
        if a.action == "resolve_payment":
            code = (a.changes or {}).get("resolution") or ""
            try:
                res_val = PaymentTransaction.Resolution(code).label  # mã chuẩn → nhãn; không chép `note` tự gõ
            except ValueError:
                res_val = "Đã xử lý"
            events.append(
                TimelineEvent(
                    at=a.created_at,
                    kind="payment_resolved",
                    label=f"Xử lý giao dịch ({res_val})",
                    actor_display=who,
                    doc="payment",
                    actor_kind=kind_actor,
                    ai_level=ai_lvl,
                    ai_config_version=ai_cfg,
                )
            )

    # 3. Mốc xử lý nếu đã RESOLVED nhưng chưa có trong AuditLog
    if payment.resolution_status == PaymentTransaction.ResolutionStatus.RESOLVED and payment.resolved_at:
        already_has = any(e.kind == "payment_resolved" for e in events)
        if not already_has:
            res_label = payment.get_resolution_display() or "Đã xử lý"
            events.append(
                TimelineEvent(
                    at=payment.resolved_at,
                    kind="payment_resolved",
                    label=f"Xử lý giao dịch ({res_label})",
                    actor_display=actor_display(payment.resolved_by),
                    doc="payment",
                    actor_kind="user" if payment.resolved_by else "system",
                )
            )

    return sorted(events, key=lambda e: e.at)
