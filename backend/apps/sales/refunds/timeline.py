"""
Dòng thời gian cho Phiếu hoàn tiền (Refund) — READ-ONLY, ghép từ Refund + AuditLog.

Bất biến:
- Không rò PII khách; không chép chữ tự do (`Refund.reason`, ghi chú báo thất bại) vào nhãn (Duy quyết 03/10 #3).
- Không rò giá vốn.
- Sửa L-4: actor AI hiện "AI của <tên>" kèm mức, không hiện "Hệ thống".
"""
from dataclasses import dataclass
from datetime import datetime

from apps.accounts.models import AuditLog
from apps.common.ai_visibility import exclude_ai_audit_rows
from apps.sales.models import Refund
from apps.sales.orders.timeline import TimelineEvent, actor_display
from apps.common.formatting import format_vnd_ui

REFUND_MODEL = Refund._meta.label
SYSTEM = "Hệ thống"


def build_refund_timeline(refund: Refund) -> list[TimelineEvent]:
    """
    Trả danh sách TimelineEvent của phiếu hoàn theo thứ tự thời gian.
    """
    events: list[TimelineEvent] = []

    # 1. Sự kiện tạo phiếu hoàn
    events.append(
        TimelineEvent(
            at=refund.created_at,
            kind="refund_created",
            label=f"Lập phiếu hoàn tiền {format_vnd_ui(refund.amount)}",
            actor_display=actor_display(refund.created_by),
            doc="refund",
            actor_kind="user" if refund.created_by else "system",
        )
    )

    # 2. Sự kiện từ AuditLog
    audits = (
        exclude_ai_audit_rows(AuditLog.objects.filter(model_name=REFUND_MODEL, object_id=str(refund.pk)))
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

        if a.action == "mark_refund_failed":
            events.append(
                TimelineEvent(
                    at=a.created_at,
                    kind="refund_failed",
                    label="Báo thất bại",
                    actor_display=who,
                    doc="refund",
                    actor_kind=kind_actor,
                    ai_level=ai_lvl,
                    ai_config_version=ai_cfg,
                )
            )
        elif a.action == "retry_refund":
            events.append(
                TimelineEvent(
                    at=a.created_at,
                    kind="refund_retried",
                    label="Thử hoàn tiền lại",
                    actor_display=who,
                    doc="refund",
                    actor_kind=kind_actor,
                    ai_level=ai_lvl,
                    ai_config_version=ai_cfg,
                )
            )

    # 3. Sự kiện xác nhận hoàn tiền (nếu đã hoàn)
    if refund.confirmed_at is not None:
        ref_text = f" (mã GD {refund.bank_txn_ref})" if refund.bank_txn_ref else ""
        events.append(
            TimelineEvent(
                at=refund.confirmed_at,
                kind="refund_confirmed",
                label=f"Đã hoàn tiền {format_vnd_ui(refund.amount)}{ref_text}",
                actor_display=actor_display(refund.confirmed_by),
                doc="refund",
                actor_kind="user" if refund.confirmed_by else "system",
            )
        )

    return sorted(events, key=lambda e: e.at)
