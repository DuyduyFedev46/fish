"""
Dòng thời gian cho Lô hàng (Batch) — READ-ONLY, ghép từ Batch + StockLedgerEntry + AuditLog.

Bất biến:
- Không rò giá vốn: kiểm qua can_view_cost(viewer) (DW-05-AC3, Bất biến 1).
- Không rò PII khách: dòng xuất kho không chứa tên, SĐT, địa chỉ khách (DW-05-AC6, Bất biến 9).
- Sửa L-4: actor AI hiện "AI của <tên>" kèm mức, không hiện "Hệ thống".
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from apps.accounts.models import AuditLog
from apps.common.cost_keys import can_view_cost
from apps.inventory.models import Batch, StockLedgerEntry
from apps.sales.orders.timeline import TimelineEvent, actor_display
from apps.sales.utils import kg_str
from apps.common.formatting import format_vnd_ui

BATCH_MODEL = Batch._meta.label
SYSTEM = "Hệ thống"


def build_batch_timeline(batch: Batch, viewer: Optional[Any] = None) -> list[TimelineEvent]:
    """
    Trả danh sách TimelineEvent của lô theo thứ tự thời gian.
    Lọc giá vốn theo quyền viewer.
    """
    events: list[TimelineEvent] = []
    user_can_see_cost = can_view_cost(viewer)

    # 1. Sự kiện tạo / nhập lô
    events.append(
        TimelineEvent(
            at=batch.created_at,
            kind="batch_created",
            label=f"Nhập lô {batch.qty_received} kg",
            actor_display=SYSTEM,
            doc="batch",
            actor_kind="system",
        )
    )

    # 2. Các dòng sổ kho (StockLedgerEntry)
    entries = (
        StockLedgerEntry.objects.filter(batch=batch)
        .select_related("created_by__staff_profile")
        .order_by("created_at", "id")
    )
    for entry in entries:
        t = entry.movement_type
        qty = abs(entry.qty_change)
        qty_display = kg_str(qty)
        if t == StockLedgerEntry.MovementType.SALE:
            # Bất biến 9: KHÔNG đưa thông tin khách vào label
            lbl = f"Xuất bán {qty_display} kg"
        elif t == StockLedgerEntry.MovementType.RECEIPT:
            lbl = f"Nhập kho {qty_display} kg"
        elif t == StockLedgerEntry.MovementType.RETURN_RESTOCK:
            lbl = f"Hàng hoàn tái nhập {qty_display} kg"
        elif t == StockLedgerEntry.MovementType.CANCEL_RESTORE:
            lbl = f"Hoàn kho huỷ đơn {qty_display} kg"
        elif t == StockLedgerEntry.MovementType.WRITE_OFF:
            lbl = f"Xuất huỷ {qty_display} kg"
        elif t == StockLedgerEntry.MovementType.RECONCILE:
            lbl = f"Kiểm kê / điều chỉnh {qty_display} kg"
        else:
            lbl = f"Biến động kho {qty_display} kg"

        events.append(
            TimelineEvent(
                at=entry.created_at,
                kind=f"stock_{t.lower()}",
                label=lbl,
                actor_display=actor_display(entry.created_by),
                doc="batch",
                actor_kind="user" if entry.created_by else "system",
            )
        )

    # 3. Sự kiện từ AuditLog
    audits = (
        AuditLog.objects.filter(model_name=BATCH_MODEL, object_id=str(batch.pk))
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

        if a.action == "publish_batch":
            events.append(
                TimelineEvent(
                    at=a.created_at,
                    kind="batch_published",
                    label="Mở bán lô",
                    actor_display=who,
                    doc="batch",
                    actor_kind=kind_actor,
                    ai_level=ai_lvl,
                    ai_config_version=ai_cfg,
                )
            )
        elif a.action == "close_batch":
            # DW-05-AC3: quan_ly và nv_kho thấy "Chủ đã chốt lô" không có số; chu thấy số
            if user_can_see_cost:
                cost_val = (a.changes or {}).get("landed_unit_cost", {}).get("final", batch.landed_unit_cost)
                cost_text = f" (giá vốn {format_vnd_ui(cost_val)}/kg)" if cost_val else ""
                label_close = f"Chốt lô{cost_text}"
            else:
                label_close = "Chủ đã chốt lô"

            events.append(
                TimelineEvent(
                    at=a.created_at,
                    kind="batch_closed",
                    label=label_close,
                    actor_display=who,
                    doc="batch",
                    actor_kind=kind_actor,
                    ai_level=ai_lvl,
                    ai_config_version=ai_cfg,
                )
            )
        elif a.action == "record_purchase_cost":
            # DW-05-AC3: quan_ly và nv_kho thấy "Chủ ghi nhận chi phí mua" không số; chu thấy số
            if user_can_see_cost:
                amount_val = (a.changes or {}).get("amount") or (a.changes or {}).get("allocated_amount")
                amount_text = f" ({format_vnd_ui(amount_val)})" if amount_val else ""
                label_cost = f"Ghi nhận chi phí mua{amount_text}"
            else:
                label_cost = "Chủ ghi nhận chi phí mua"

            events.append(
                TimelineEvent(
                    at=a.created_at,
                    kind="purchase_cost_recorded",
                    label=label_cost,
                    actor_display=who,
                    doc="batch",
                    actor_kind=kind_actor,
                    ai_level=ai_lvl,
                    ai_config_version=ai_cfg,
                )
            )
        elif a.action == "cancel_expired_batch":
            # DW-06-AC5: quan_ly và nv_kho thấy "Chủ đã huỷ lô" không số; chu thấy số (hoặc nhãn huỷ)
            if user_can_see_cost:
                loss_val = (a.changes or {}).get("loss_amount")
                loss_text = f" (lỗ {format_vnd_ui(loss_val)})" if loss_val else ""
                label_cancel = f"Huỷ lô quá hạn{loss_text}"
            else:
                label_cancel = "Chủ đã huỷ lô"

            events.append(
                TimelineEvent(
                    at=a.created_at,
                    kind="batch_cancelled",
                    label=label_cancel,
                    actor_display=who,
                    doc="batch",
                    actor_kind=kind_actor,
                    ai_level=ai_lvl,
                    ai_config_version=ai_cfg,
                )
            )

    return sorted(events, key=lambda e: e.at)
