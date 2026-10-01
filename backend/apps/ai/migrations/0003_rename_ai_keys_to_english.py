"""
P8b Lô 4 (R2/R5): đổi khoá AI sang tiếng Anh. Giá trị giữ nguyên.

- `AiAction.assignee_group` (tên Group cũ -> mới) và `AiAction.command` (id lệnh nhập lô cũ -> mới): UPDATE, đây là dữ liệu vận hành.
- `AiConfigVersion` / `AiPolicyVersion` là append-only: KHÔNG sửa dòng cũ. Với phiên bản MỚI NHẤT của mỗi user (cấu hình) và của
  chính sách, nếu còn khoá cũ thì THÊM một phiên bản mới mang khoá tiếng Anh, ghi chú "P8b: đổi khoá sang tiếng Anh, giá trị giữ nguyên".
  Các phiên bản cũ hơn giữ nguyên; chỗ đọc chúng đi qua `apps/ai/registry/legacy_ids.py`.
- Chạy lại: không thêm gì (phiên bản mới nhất đã hết khoá cũ). Reverse: đổi ngược AiAction, thêm phiên bản mang khoá cũ
  (không xoá, không sửa dòng nào).
- Chỉ in số lượng, không in tên người dùng.

Mọi bảng ánh xạ đóng băng tại đây (không import `legacy_ids`/`roles`) để migration không đổi nghĩa khi code đổi tiếp.
"""
from django.db import migrations
from django.db.models import Q

NOTE_FORWARD = "P8b: đổi khoá sang tiếng Anh, giá trị giữ nguyên"
NOTE_BACKWARD = "P8b rollback: trả khoá về tên cũ, giá trị giữ nguyên"

COMMAND_IDS = {
    "purchasing.purchasereceipt.nhap_lo": "purchasing.purchasereceipt.receive_batches",  # naming: allow - id cũ
}
COMMAND_ALIASES = {
    "nhap_lo": "receive_batches",  # naming: allow - khoá cũ
}
GROUP_KEYS = {
    "thu_mua": "purchasing",  # naming: allow - khoá cũ
    "ban_hang": "sales",  # naming: allow - khoá cũ
    "cskh": "customer_service",  # naming: allow - khoá cũ
}
ASSIGNEE_GROUPS = {
    "chu": "owner",  # naming: allow - tên Group cũ
    "quan_ly": "manager",  # naming: allow - tên Group cũ
    "nv_kho": "warehouse_staff",  # naming: allow - tên Group cũ
    "nv_giao": "delivery_staff",  # naming: allow - tên Group cũ
    "cskh": "customer_service",  # naming: allow - tên Group cũ
}


def _invert(mapping):
    return {value: key for key, value in mapping.items()}


def _map_command_key(key, ids, aliases):
    return aliases.get(ids.get(key, key), ids.get(key, key))


def _map_mapping(mapping, mapper):
    """Đổi khoá của dict; khi khoá đích đã có sẵn trong nguồn thì giữ giá trị của khoá đích."""
    if not isinstance(mapping, dict):
        return {}
    out = {}
    for key, value in mapping.items():
        new_key = mapper(key)
        if new_key != key and new_key in mapping:
            continue
        out[new_key] = value
    return out


def _changed(before, after):
    return (before if isinstance(before, dict) else {}) != after


def _rename_actions(apps, command_ids, assignees):
    """Đổi lệnh và nhóm nhận việc; trả SỐ DÒNG bị đổi (một dòng đổi cả hai vẫn tính một)."""
    AiAction = apps.get_model("ai", "AiAction")
    touched = AiAction.objects.filter(Q(command__in=list(command_ids)) | Q(assignee_group__in=list(assignees))).count()
    for old, new in command_ids.items():
        AiAction.objects.filter(command=old).update(command=new)
    for old, new in assignees.items():
        AiAction.objects.filter(assignee_group=old).update(assignee_group=new)
    return touched


def _append_versions(apps, *, command_ids, aliases, group_keys, note):
    """Thêm phiên bản mới (append-only) cho cấu hình mới nhất của mỗi user và chính sách mới nhất nếu còn khoá cần đổi."""
    AiConfigVersion = apps.get_model("ai", "AiConfigVersion")
    AiPolicyVersion = apps.get_model("ai", "AiPolicyVersion")

    def command_mapper(key):
        return _map_command_key(key, command_ids, aliases)

    def group_mapper(key):
        return group_keys.get(key, key)

    configs = 0
    seen_users = set()
    for latest in AiConfigVersion.objects.order_by("user_id", "-version"):
        if latest.user_id in seen_users:
            continue
        seen_users.add(latest.user_id)
        group_levels = _map_mapping(latest.group_levels, group_mapper)
        overrides = _map_mapping(latest.overrides, command_mapper)
        limits = _map_mapping(latest.limits, command_mapper)
        if not (
            _changed(latest.group_levels, group_levels)
            or _changed(latest.overrides, overrides)
            or _changed(latest.limits, limits)
        ):
            continue
        AiConfigVersion.objects.create(
            user_id=latest.user_id,
            version=latest.version + 1,
            group_levels=group_levels,
            overrides=overrides,
            limits=limits,
            killed=latest.killed,
            created_by_id=latest.created_by_id,
            note=note,
        )
        configs += 1

    policies = 0
    latest_policy = AiPolicyVersion.objects.order_by("-version").first()
    if latest_policy is not None:
        caps = _map_mapping(latest_policy.caps, command_mapper)
        if _changed(latest_policy.caps, caps):
            AiPolicyVersion.objects.create(
                version=latest_policy.version + 1,
                global_mode=latest_policy.global_mode,
                red_zone_open=latest_policy.red_zone_open,
                caps=caps,
                created_by_id=latest_policy.created_by_id,
                note=note,
            )
            policies = 1
    return configs, policies


def _report(actions, configs, policies):
    if actions or configs or policies:
        print(f"  ai: {actions} việc AI, {configs} phiên bản cấu hình, {policies} phiên bản chính sách")


def rename_ai_keys_forward(apps, schema_editor):
    actions = _rename_actions(apps, COMMAND_IDS, ASSIGNEE_GROUPS)
    configs, policies = _append_versions(
        apps, command_ids=COMMAND_IDS, aliases=COMMAND_ALIASES, group_keys=GROUP_KEYS, note=NOTE_FORWARD
    )
    _report(actions, configs, policies)


def rename_ai_keys_backward(apps, schema_editor):
    actions = _rename_actions(apps, _invert(COMMAND_IDS), _invert(ASSIGNEE_GROUPS))
    configs, policies = _append_versions(
        apps,
        command_ids=_invert(COMMAND_IDS),
        aliases=_invert(COMMAND_ALIASES),
        group_keys=_invert(GROUP_KEYS),
        note=NOTE_BACKWARD,
    )
    _report(actions, configs, policies)


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0002_grant_manage_ai_policy"),
        ("accounts", "0013_rename_groups_to_english"),
    ]

    operations = [
        migrations.RunPython(rename_ai_keys_forward, rename_ai_keys_backward),
    ]
