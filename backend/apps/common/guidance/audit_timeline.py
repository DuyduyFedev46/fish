"""
Provider guidance "chỉ dòng thời gian" (Lô 2, R2 — 02b §3.8).

`make_audit_timeline_provider(...)` dựng hàm provider cho `GET /api/guidance/<loại>/<id>/` của các đối tượng
chưa có "Tiếp theo": phiếu nhập, kiểm kê, hàng hoàn, phiếu giao, mặt hàng, nhà cung cấp, khách, nhân viên.
Kết quả luôn `next_steps: []`, `warnings: []`; câu "Tiếp theo" của các loại này là bảng tĩnh ở FE.

Quyền đọc = quyền xem chính đối tượng đó (T1 `view_<model>` + T3 scope của API chi tiết), truyền vào qua
`view_perm` và `scope_fn`. Thiếu quyền → 403 trước, không có hoặc ngoài phạm vi → 404 (thông điệp cố định,
không lặp lại id người gọi gửi lên).

Bất biến:
- Nhãn dòng do code dựng từ bảng `action_labels`. KHÔNG đưa `AuditLog.changes`, `note`, `object_repr` ra ngoài
  (đó là nơi có thể chứa tên, SĐT, địa chỉ, ghi chú tự do của khách; bất biến 9) và không có số tiền/giá vốn
  (bất biến 1). Chỉ có: việc đã làm, người làm (nhân viên hoặc "Hệ thống" hoặc "AI của <nhân viên>"), giờ.
- Hành động chưa có trong bảng nhãn hiện nhãn chung "Có thay đổi", không lộ mã hành động nội bộ.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional, Union

from django.conf import settings
from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from apps.common.guidance.timeline import format_guidance_timeline

SYSTEM = "Hệ thống"
GENERIC_LABEL = "Có thay đổi"
MAX_ID_DIGITS = 18  # chặn số quá lớn gây OverflowError ở DB
NOT_FOUND_MESSAGE = "Không tìm thấy chứng từ."
DEFAULT_TIMELINE_MAX_ROWS = 200


def timeline_max_rows() -> int:
    """Số dòng AuditLog tối đa một timeline (settings.GUIDANCE_TIMELINE_MAX_ROWS, bất biến 7)."""
    return int(getattr(settings, "GUIDANCE_TIMELINE_MAX_ROWS", DEFAULT_TIMELINE_MAX_ROWS))

PermCheck = Union[str, Callable[[Any], bool]]
ActionLabel = Union[str, Callable[[Any], str]]


@dataclass(frozen=True)
class _Event:
    at: datetime
    kind: str
    label: str
    actor_display: str
    doc: str
    actor_kind: str = "system"
    ai_level: Optional[str] = None
    ai_config_version: Optional[int] = None


def _staff_name(user) -> str:
    """Tên hiển thị của NHÂN VIÊN (không phải khách). None → "Hệ thống"."""
    if user is None:
        return SYSTEM
    profile = getattr(user, "staff_profile", None)
    return (profile.display_name if profile else "") or user.get_username()


def _audit_event(row, *, doc_type: str, action_labels: dict[str, ActionLabel]) -> _Event:
    from apps.accounts.models import AuditLog

    spec = action_labels.get(row.action)
    label = spec(row) if callable(spec) else (spec or GENERIC_LABEL)

    ai_level = None
    ai_cfg = None
    if row.actor_kind == AuditLog.ActorKind.AI:
        who = f"AI của {_staff_name(row.ai_actor)}"
        actor_kind = "ai"
        ai_level = row.ai_level or "C"
        ai_cfg = row.ai_config_version
    elif row.actor_kind == AuditLog.ActorKind.USER and row.actor is not None:
        who = _staff_name(row.actor)
        actor_kind = "user"
    else:
        who = SYSTEM
        actor_kind = "system"

    return _Event(
        at=row.created_at,
        kind=row.action,
        label=label,
        actor_display=who,
        doc=doc_type,
        actor_kind=actor_kind,
        ai_level=ai_level,
        ai_config_version=ai_cfg,
    )


def make_audit_timeline_provider(
    model,
    view_perm: PermCheck,
    scope_fn: Optional[Callable[[Any, Any], Any]] = None,
    *,
    doc_type: str,
    code_fn: Callable[[Any], str],
    action_labels: dict[str, ActionLabel],
    created_label: Optional[str] = None,
    creator_attr: Optional[str] = None,
    no_store: bool = False,
    exclude_actions: frozenset[str] = frozenset(),
):
    """
    model         : model của đối tượng; AuditLog đọc theo `model._meta.label` + pk.
    view_perm     : codename quyền ("app.view_x") hoặc hàm `user -> bool`.
    scope_fn      : `(user, queryset) -> queryset`, phạm vi dòng giống API chi tiết (T3).
    doc_type      : khoá loại trong URL, ghi vào `doc.type` và `timeline[].doc`.
    code_fn       : `obj -> mã hiển thị` (PR-12, KK-3…). Không dùng tên/SĐT khách.
    action_labels : `AuditLog.action -> nhãn` (chuỗi hoặc hàm nhận dòng AuditLog).
    created_label : nếu có, thêm dòng "tạo" theo `obj.created_at`.
    creator_attr  : tên field FK tới User của người tạo (nếu có).
    no_store      : True với đối tượng gắn dữ liệu khách → response gắn `Cache-Control: no-store`.
    exclude_actions: các `AuditLog.action` bỏ khỏi timeline (nhiễu, vd. "logout" của nhân viên).
    Timeline chỉ lấy `timeline_max_rows()` dòng AuditLog MỚI nhất; thừa thì `timeline_truncated: true`.
    """

    def _allowed(user) -> bool:
        if callable(view_perm):
            return bool(view_perm(user))
        return bool(user.has_perm(view_perm))

    def provider(doc_id: str, user: Any, request: Optional[Any] = None) -> dict[str, Any]:
        from apps.accounts.models import AuditLog

        if not _allowed(user):
            raise PermissionDenied("Bạn không có quyền xem lịch sử này.")

        raw = str(doc_id)
        if not raw.isdigit() or len(raw) > MAX_ID_DIGITS:
            raise Http404(NOT_FOUND_MESSAGE)

        qs = model._default_manager.all()
        if scope_fn is not None:
            qs = scope_fn(user, qs)
        obj = qs.filter(pk=int(raw)).first()
        if obj is None:
            # Thông điệp cố định: không phân biệt "không tồn tại" với "ngoài phạm vi".
            raise Http404(NOT_FOUND_MESSAGE)

        events: list[_Event] = []
        created_at = getattr(obj, "created_at", None)
        if created_label and created_at is not None:
            creator = getattr(obj, creator_attr, None) if creator_attr else None
            events.append(_Event(
                at=created_at,
                kind=f"{doc_type}_created",
                label=created_label,
                actor_display=_staff_name(creator),
                doc=doc_type,
                actor_kind="user" if creator is not None else "system",
            ))

        limit = timeline_max_rows()
        newest_first = (
            AuditLog.objects.filter(model_name=model._meta.label, object_id=str(obj.pk))
            .exclude(action__in=exclude_actions)
            .select_related("actor__staff_profile", "ai_actor__staff_profile")
            .order_by("-created_at", "-id")[: limit + 1]  # lấy dư 1 dòng để biết có bị cắt không
        )
        rows = list(newest_first)
        truncated = len(rows) > limit
        rows = list(reversed(rows[:limit]))  # đảo lại: cũ → mới
        events.extend(_audit_event(r, doc_type=doc_type, action_labels=action_labels) for r in rows)
        events.sort(key=lambda e: e.at)

        status_value = getattr(obj, "status", None)
        status_label = getattr(obj, "get_status_display", None)
        doc = {
            "type": doc_type,
            "id": obj.pk,
            "code": code_fn(obj),
            "status": status_value,
            "status_label": status_label() if callable(status_label) else None,
        }
        return {
            "doc": doc,
            "next_steps": [],
            "warnings": [],
            "timeline": format_guidance_timeline(events, viewer=user),
            "timeline_truncated": truncated,
            "related": [],
        }

    provider.no_store = no_store  # GuidanceView đọc cờ này để gắn Cache-Control
    return provider
