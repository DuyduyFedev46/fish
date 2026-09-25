"""
JSON một dòng nhân viên (S41 contract `GET /api/staff/`). Chỉ đọc, dựng tường minh —
không bao giờ có mật khẩu/hash/token (S41-AC10). Không đụng giá vốn.
"""
from django.utils import timezone

from apps.accounts.auth.services import sorted_groups

from . import services


def staff_item(user, *, actor, active_chus) -> dict:
    profile = getattr(user, "staff_profile", None)
    return {
        "id": user.pk,
        "username": user.get_username(),
        "display_name": (profile.display_name if profile else "")
        or user.get_full_name()
        or user.get_username(),
        "phone": profile.phone if profile else "",
        "groups": sorted_groups(g.name for g in user.groups.all()),
        "is_active": user.is_active,
        "last_login": timezone.localtime(user.last_login).isoformat() if user.last_login else None,
        "available_actions": services.available_actions(
            actor=actor, user=user, active_chus=active_chus
        ),
    }
