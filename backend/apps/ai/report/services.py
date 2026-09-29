"""
Dịch vụ Báo cáo AI cuối ngày (02b §6.6, DW-22).
Bảo vệ tuyệt đối:
- Bất biến 1: Không chứa bất kỳ giá vốn hay chi phí nào.
- Bất biến 9: Không chứa dữ liệu cá nhân khách hàng (PII).
"""
import datetime
from django.utils import timezone

from apps.ai.models import AiAction
from apps.ai.registry.discovery import get_registry


def get_daily_ai_report(report_date: datetime.date) -> dict:
    """
    Tạo báo cáo tổng hợp hành động AI trong một ngày (DW-22-AC1, AC2).
    """
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(
        datetime.datetime.combine(report_date, datetime.time.min), tz
    )
    end_dt = timezone.make_aware(
        datetime.datetime.combine(report_date, datetime.time.max), tz
    )

    actions = (
        AiAction.objects.filter(created_at__gte=start_dt, created_at__lte=end_dt)
        .select_related("owner")
        .order_by("-created_at")
    )

    registry = get_registry()

    # Thống kê theo người dùng (by_user)
    users_map: dict[int, dict] = {}
    items = []

    for action in actions:
        owner = action.owner
        if owner.id not in users_map:
            users_map[owner.id] = {
                "user_id": owner.id,
                "display_name": owner.get_full_name() or owner.username,
                "A": 0,
                "B": 0,
                "C_confirmed": 0,
                "C_expired": 0,
                "undone": 0,
                "escalated": 0,
            }

        stats = users_map[owner.id]
        if action.level == AiAction.Level.A or action.kind == AiAction.Kind.READ:
            stats["A"] += 1
        elif action.level == AiAction.Level.B:
            stats["B"] += 1
        elif action.level == AiAction.Level.C:
            if action.status == AiAction.Status.CONFIRMED:
                stats["C_confirmed"] += 1
            elif action.status == AiAction.Status.EXPIRED:
                stats["C_expired"] += 1

        if action.status == AiAction.Status.UNDONE:
            stats["undone"] += 1
        elif action.status == AiAction.Status.ESCALATED:
            stats["escalated"] += 1

        # Tạo item chi tiết không rò PII và giá vốn (DW-22-AC4, Bất biến 1 & 9)
        spec = registry.get(action.command)
        title = spec.title if spec else action.command

        target_info = None
        if action.target_model or action.target_id:
            target_info = {
                "type": action.target_model or "document",
                "code": action.target_id or "",
            }

        items.append(
            {
                "id": str(action.id),
                "command": action.command,
                "title": title,
                "level": action.level,
                "status": action.status,
                "owner_display": owner.get_full_name() or owner.username,
                "created_at": action.created_at.isoformat(),
                "target": target_info,
                "result_ref": action.result_ref,
            }
        )

    return {
        "date": report_date.isoformat(),
        "by_user": list(users_map.values()),
        "items": items,
    }
