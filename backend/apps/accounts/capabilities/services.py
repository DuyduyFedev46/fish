"""
Nghiệp vụ ma trận phân quyền (B4, đề xuất BR-PQ-32) — đọc nhóm × việc và đổi quyền của nhóm.

Luật ghi `set_group_capabilities` (chống leo quyền, 02b §3 B4 + §4):
1. Chỉ Chủ (hoặc superuser) ghi được, kể cả khi người gọi có `manage_staff` gán trực tiếp (403).
2. Nhóm `owner` bị khoá (`GROUP_LOCKED`): Chủ luôn đủ quyền, không ai gỡ được quyền cốt lõi của Chủ.
3. Việc `owner_only` không bật được cho nhóm khác (`BR-PQ-32`).
4. Chỉ nhận khoá trong registry (`INPUT_NOT_ALLOWED`) và chỉ thêm/bớt đúng `perms` của việc đó; permission ngoài
   registry không bao giờ bị đụng.
5. Việc `requires` việc khác (`pack_print` cần `deliver`) phải đổi cùng lúc: bật/tắt lệch là `CAPABILITY_REQUIRES` (M1).
6. Mọi thay đổi ghi `AuditLog` `change_group_capabilities`; `changes` chỉ chứa mã việc và trạng thái on/off/partial.
Cả yêu cầu hợp lệ toàn bộ hoặc không đổi gì (một lỗi → không việc nào được áp).
"""
from django.contrib.auth.models import Group, Permission, User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.auth.services import GROUP_LABELS, sorted_groups
from apps.accounts.models import AuditLog
from apps.accounts.staff.services import StaffPermissionError, actor_is_owner
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError

from . import registry

ACTION_CHANGE_CAPABILITIES = "change_group_capabilities"
ACTION_CHANGE_STAFF_GROUPS = "staff_groups_change"  # do apps/accounts/staff/services.set_groups ghi
GROUP_MODEL = Group._meta.label  # "auth.Group"
USER_MODEL = User._meta.label  # "auth.User"

OWNER_ONLY_CODE = "BR-PQ-32"
GROUP_LOCKED_CODE = "GROUP_LOCKED"
INPUT_CODE = "INPUT_NOT_ALLOWED"
INVALID_INPUT_CODE = "INVALID_INPUT"
REQUIRES_CODE = "CAPABILITY_REQUIRES"
GROUP_NOT_FOUND_CODE = "GROUP_NOT_FOUND"
TIMELINE_MAX_EVENTS = 200

STATE_LABEL_VERB = {registry.STATE_ON: "Bật", registry.STATE_OFF: "Tắt", registry.STATE_PARTIAL: "Đổi"}


# --- đọc ---------------------------------------------------------------------------


def codename_of(permission) -> str:
    return f"{permission.content_type.app_label}.{permission.codename}"


def capability_state(capability, held) -> str:
    """`on` khi nhóm có đủ perms, `off` khi không có cái nào, `partial` khi thiếu một phần."""
    have = sum(1 for perm in capability.perms if perm in held)
    if have == len(capability.perms):
        return registry.STATE_ON
    return registry.STATE_OFF if have == 0 else registry.STATE_PARTIAL


def capability_states(held) -> dict:
    return {c.key: capability_state(c, held) for c in registry.CAPABILITIES}


def display_name(user) -> str:
    """Tên hiển thị của NHÂN VIÊN (không phải khách). None → "Hệ thống"."""
    if user is None:
        return "Hệ thống"
    profile = getattr(user, "staff_profile", None)
    return (profile.display_name if profile else "") or user.get_full_name() or user.get_username()


def _local_iso(moment):
    return timezone.localtime(moment).isoformat() if moment else None


def _role_groups():
    """5 Group có sẵn theo thứ tự vai, kèm quyền (một lần truy vấn, không N+1)."""
    found = {g.name: g for g in Group.objects.filter(name__in=roles.ALL_ROLES).prefetch_related(
        "permissions__content_type")}
    return [found[code] for code in roles.ALL_ROLES if code in found]


def _held(group) -> set:
    return {codename_of(p) for p in group.permissions.all()}


def _active_members(group):
    return list(
        User.objects.filter(groups=group, is_active=True)
        .select_related("staff_profile").order_by("username")
    )


def _last_changes(group_ids):
    """{group_id: AuditLog mới nhất `change_group_capabilities`}."""
    rows = (
        AuditLog.objects.filter(action=ACTION_CHANGE_CAPABILITIES, model_name=GROUP_MODEL,
                                object_id__in=[str(i) for i in group_ids])
        .select_related("actor__staff_profile").order_by("created_at", "id")
    )
    latest = {}
    for row in rows:  # tăng dần: dòng sau đè dòng trước
        latest[int(row.object_id)] = row
    return latest


def _summary(group, held, members, last_row) -> dict:
    return {
        "id": group.pk,
        "code": group.name,
        "label": GROUP_LABELS.get(group.name, group.name),
        "member_count": len(members),
        "members": [{"id": u.pk, "display_name": display_name(u)} for u in members],
        "can_view_cost": "inventory.view_costprice" in held,
        "last_changed_at": _local_iso(last_row.created_at) if last_row else None,
        "last_changed_by": display_name(last_row.actor) if last_row else None,
        "capabilities": capability_states(held),
    }


def list_groups() -> list:
    groups = _role_groups()
    last = _last_changes([g.pk for g in groups])
    return [_summary(g, _held(g), _active_members(g), last.get(g.pk)) for g in groups]


def get_group_or_404(code):
    if code not in roles.ALL_ROLES:
        raise BusinessError("Không tìm thấy nhóm quyền.", code=GROUP_NOT_FOUND_CODE, status_code=404)
    group = Group.objects.filter(name=code).prefetch_related("permissions__content_type").first()
    if group is None:
        raise BusinessError("Không tìm thấy nhóm quyền.", code=GROUP_NOT_FOUND_CODE, status_code=404)
    return group


def _added_at(group, users) -> dict:
    """{user_id: lúc được thêm vào nhóm}. Suy từ AuditLog (Django không lưu thời điểm gán nhóm);
    người chưa có dòng nhật ký (gán bằng migration/seed) lấy ngày tạo tài khoản."""
    code = group.name
    added = {}
    rows = (
        AuditLog.objects.filter(model_name=USER_MODEL, object_id__in=[str(u.pk) for u in users],
                                action__in=[ACTION_CHANGE_STAFF_GROUPS, "staff_create"])
        .order_by("created_at", "id")
    )
    for row in rows:
        groups = (row.changes or {}).get("groups") or {}
        before, after = groups.get("from") or [], groups.get("to") or []
        uid = int(row.object_id)
        if code in after and code not in before:
            added[uid] = row.created_at
        elif code in before and code not in after:
            added.pop(uid, None)
    return {u.pk: added.get(u.pk) or u.date_joined for u in users}


def _members_detail(group) -> list:
    users = list(User.objects.filter(groups=group).select_related("staff_profile").prefetch_related("groups")
                 .order_by("username"))
    added = _added_at(group, users)
    return [
        {
            "id": u.pk,
            "display_name": display_name(u),
            "username": u.get_username(),
            "other_groups": sorted_groups(g.name for g in u.groups.all() if g.pk != group.pk),
            "is_active": u.is_active,
            "added_at": _local_iso(added[u.pk]),
        }
        for u in users
    ]


def _event(row, label, group_code):
    if row.actor_kind == AuditLog.ActorKind.USER and row.actor is not None:
        actor = {"kind": "user", "display": display_name(row.actor)}
    else:
        actor = {"kind": "system", "display": "Hệ thống"}
    return {"at": _local_iso(row.created_at), "kind": row.action, "label": label, "doc": "group", "actor": actor,
            "_sort": (row.created_at, row.pk)}


def _capability_events(group):
    rows = (AuditLog.objects.filter(action=ACTION_CHANGE_CAPABILITIES, model_name=GROUP_MODEL,
                                    object_id=str(group.pk))
            .select_related("actor__staff_profile").order_by("-created_at", "-id")[:TIMELINE_MAX_EVENTS])
    for row in rows:
        for key, change in (row.changes or {}).items():
            capability = registry.BY_KEY.get(key)
            verb = STATE_LABEL_VERB.get((change or {}).get("to"), "Đổi")
            name = capability.label if capability else "một việc"
            yield _event(row, f"{verb} việc {name}", group.name)


def _membership_events(group):
    """Thêm/bớt thành viên của ĐÚNG nhóm này, mới nhất trước, tối đa `TIMELINE_MAX_EVENTS` dòng.

    Lọc ở DB theo mã nhóm có trong `groups.from`/`groups.to` (so chuỗi con, chạy cả SQLite lẫn Postgres) rồi kiểm lại
    chính xác ở Python, nên đổi nhóm của nhóm khác không đẩy sự kiện của nhóm này ra khỏi cửa sổ quét."""
    code = group.name
    rows = (AuditLog.objects.filter(action=ACTION_CHANGE_STAFF_GROUPS, model_name=USER_MODEL)
            .filter(Q(changes__groups__from__icontains=code) | Q(changes__groups__to__icontains=code))
            .select_related("actor__staff_profile").order_by("-created_at", "-id"))
    picked = []
    for row in rows.iterator(chunk_size=500):
        groups = (row.changes or {}).get("groups") or {}
        before, after = groups.get("from") or [], groups.get("to") or []
        if code in after and code not in before:
            picked.append((row, "Thêm {name} vào nhóm"))
        elif code in before and code not in after:
            picked.append((row, "Bớt {name} khỏi nhóm"))
        if len(picked) >= TIMELINE_MAX_EVENTS:
            break
    users = {u.pk: u for u in User.objects.filter(pk__in=[int(r.object_id) for r, _ in picked])
             .select_related("staff_profile")}
    for row, template in picked:
        who = users.get(int(row.object_id))
        yield _event(row, template.format(name=display_name(who) if who else "nhân viên"), code)


def group_timeline(group) -> list:
    """Dòng thời gian của nhóm, cũ → mới: đổi việc của nhóm + thêm/bớt thành viên. Chỉ nhãn do code dựng
    (không `changes` thô, không ghi chú)."""
    events = sorted([*_capability_events(group), *_membership_events(group)], key=lambda e: e["_sort"])
    events = events[-TIMELINE_MAX_EVENTS:]
    for event in events:
        event.pop("_sort")
    return events


def group_scopes(code, held) -> dict:
    """Phạm vi dữ liệu chỉ đọc. `customers` theo quyền thực tế của nhóm (M2), phần còn lại theo bảng cố định."""
    scopes = dict(registry.GROUP_SCOPES.get(code, {}))
    if registry.CUSTOMER_DIRECTORY_PERM in held:
        scopes["customers"] = registry.SCOPE_ALL_CUSTOMERS
    return scopes


def describe_group(code) -> dict:
    group = get_group_or_404(code)
    held = _held(group)
    members = _active_members(group)
    last = _last_changes([group.pk]).get(group.pk)
    body = _summary(group, held, members, last)
    body.update({
        "members": _members_detail(group),
        "registry": [
            {"key": c.key, "label": c.label, "section": c.section, "owner_only": c.owner_only,
             "requires": list(c.requires)}
            for c in registry.CAPABILITIES
        ],
        "scopes": group_scopes(group.name, held),
        "timeline": group_timeline(group),
    })
    return body


def capability_change_label(row) -> str:
    """Nhãn một dòng AuditLog `change_group_capabilities` (dùng cho provider guidance `group`)."""
    changes = row.changes or {}
    if len(changes) == 1:
        (key, change), = changes.items()
        capability = registry.BY_KEY.get(key)
        return f"{STATE_LABEL_VERB.get((change or {}).get('to'), 'Đổi')} việc {capability.label if capability else 'một việc'}"
    return f"Đổi quyền của nhóm ({len(changes)} việc)"


# --- ghi ---------------------------------------------------------------------------


def _validate_changes(changes) -> dict:
    if not isinstance(changes, dict) or not changes:
        raise BusinessError("Cần gửi ít nhất một việc muốn đổi.", code=INVALID_INPUT_CODE)
    for key, value in changes.items():
        if key not in registry.BY_KEY:
            raise BusinessError("Có việc không nằm trong danh sách phân quyền.", code=INPUT_CODE)
        if not isinstance(value, bool):
            raise BusinessError("Giá trị mỗi việc phải là bật (true) hoặc tắt (false).", code=INVALID_INPUT_CODE)
    return changes


def _check_requires(changes, held):
    """M1: sau khi áp `changes`, việc đang bật (on/partial) phải có đủ việc gốc `requires` ở trạng thái `on`.
    Chỉ xét cặp có việc nằm trong yêu cầu, nên dữ liệu cũ lệch ở chỗ không đụng tới không chặn thay đổi khác.
    Phải đổi hai việc CÙNG MỘT yêu cầu thì mới qua."""

    def final_state(key):
        if key in changes:
            return registry.STATE_ON if changes[key] else registry.STATE_OFF
        return capability_state(registry.BY_KEY[key], held)

    for capability in registry.CAPABILITIES:
        for root_key in capability.requires:
            if capability.key not in changes and root_key not in changes:
                continue
            root = registry.BY_KEY[root_key]
            if final_state(capability.key) == registry.STATE_OFF or final_state(root_key) == registry.STATE_ON:
                continue
            if root_key in changes:  # đang tắt việc gốc
                message = (f"Không tắt được \"{root.label}\" khi \"{capability.label}\" còn bật. "
                           f"Hãy tắt cả hai việc cùng lúc.")
            else:  # đang bật việc phụ thuộc
                message = (f"Không bật được \"{capability.label}\" khi \"{root.label}\" đang tắt. "
                           f"Hãy bật cả hai việc cùng lúc.")
            raise BusinessError(message, code=REQUIRES_CODE)


@transaction.atomic
def set_group_capabilities(*, group_code, changes, actor):
    """Bật/tắt việc cho nhóm. Trả mô tả chi tiết nhóm sau khi đổi. Xem docstring module cho luật."""
    if not actor_is_owner(actor):
        raise StaffPermissionError("Chỉ Chủ mới đổi được quyền của nhóm.")
    if group_code not in roles.ALL_ROLES:
        raise BusinessError("Không tìm thấy nhóm quyền.", code=GROUP_NOT_FOUND_CODE, status_code=404)
    if group_code == registry.LOCKED_GROUP:
        raise BusinessError("Nhóm Chủ luôn đủ quyền, không sửa được.", code=GROUP_LOCKED_CODE)
    changes = _validate_changes(changes)
    for key, wanted in changes.items():
        if wanted and registry.BY_KEY[key].owner_only:
            raise BusinessError("Việc này chỉ nhóm Chủ được làm.", code=OWNER_ONLY_CODE)

    group = Group.objects.select_for_update().filter(name=group_code).first()
    if group is None:
        raise BusinessError("Không tìm thấy nhóm quyền.", code=GROUP_NOT_FOUND_CODE, status_code=404)
    held = {codename_of(p) for p in group.permissions.select_related("content_type")}
    _check_requires(changes, held)
    audit = {}
    for key, wanted in changes.items():
        capability = registry.BY_KEY[key]
        before = capability_state(capability, held)
        if wanted and before != registry.STATE_ON:
            group.permissions.add(*_permissions(capability))
            held.update(capability.perms)
        elif not wanted and before != registry.STATE_OFF:
            group.permissions.remove(*_permissions(capability))
            held.difference_update(capability.perms)
        after = capability_state(capability, held)
        if after != before:
            audit[key] = {"from": before, "to": after}
    if audit:
        record_audit(ACTION_CHANGE_CAPABILITIES, actor=actor, obj=group, changes=audit)
    return describe_group(group_code)


def _permissions(capability):
    """Đối tượng Permission của một việc. Thiếu codename → lỗi rõ (test registry bắt trước khi tới đây)."""
    found = []
    for perm in capability.perms:
        app_label, codename = perm.split(".")
        found.append(Permission.objects.get(content_type__app_label=app_label, codename=codename))
    return found
