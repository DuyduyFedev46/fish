"""
P8b Lô 4: xem trước (CHỈ ĐỌC) việc đổi tên Group và khoá AI sang tiếng Anh, chạy trước `migrate` trên staging/production.

    python manage.py preview_group_rename

In SỐ LƯỢNG, không in tên đăng nhập, họ tên, SĐT hay địa chỉ (bất biến 9):
- từng vai: tên đang có trong DB, id, số quyền, số thành viên;
- xung đột (cùng lúc có tên cũ lẫn tên mới -> migration sẽ dừng);
- số Group lạ (ngoài 5 tên cũ và 5 tên mới; điểm dừng của 02c: có thì xem lại trước khi migrate, không in tên);
- số việc AI còn lệnh/nhóm nhận việc tên cũ, số user và chính sách còn khoá cũ trong phiên bản mới nhất.

Không ghi gì vào DB. Đối chiếu kết quả trước và sau `migrate`: id, số quyền, số thành viên của từng vai phải giống hệt.
"""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.ai.models import AiAction
from apps.ai.models.config import AiConfigVersion
from apps.ai.models.policy import AiPolicyVersion
from apps.ai.registry import legacy_ids


def _latest_config_per_user():
    seen = set()
    for config in AiConfigVersion.objects.order_by("user_id", "-version"):
        if config.user_id not in seen:
            seen.add(config.user_id)
            yield config


class Command(BaseCommand):
    help = "Xem trước (chỉ đọc) việc đổi tên Group và khoá AI sang tiếng Anh. Chỉ in số lượng."

    def handle(self, *args, **options):
        out = self.stdout.write
        conflicts = 0
        out("Vai (Group):")
        for old_name, new_name in legacy_ids.LEGACY_ASSIGNEE_GROUPS.items():
            old = Group.objects.filter(name=old_name).first()
            new = Group.objects.filter(name=new_name).first()
            if old and new:
                conflicts += 1
                out(f"  XUNG ĐỘT: cùng có '{old_name}' và '{new_name}' (migration sẽ dừng)")
                continue
            group = old or new
            if group is None:
                out(f"  {new_name}: không có Group nào (migration bỏ qua)")
                continue
            state = "tên cũ, sẽ đổi" if old else "đã là tên mới"
            out(
                f"  {group.name}: id={group.pk} ({state}), "
                f"{group.permissions.count()} quyền, {group.user_set.count()} thành viên"
            )

        known_names = set(legacy_ids.LEGACY_ASSIGNEE_GROUPS) | set(legacy_ids.LEGACY_ASSIGNEE_GROUPS.values())
        unknown_groups = Group.objects.exclude(name__in=known_names).count()
        out(f"Group lạ (ngoài 10 tên cũ và mới): {unknown_groups}")

        legacy_commands = list(legacy_ids.LEGACY_COMMAND_IDS)
        actions_command = AiAction.objects.filter(command__in=legacy_commands).count()
        actions_group = AiAction.objects.filter(assignee_group__in=legacy_ids.LEGACY_ASSIGNEE_GROUPS).count()
        configs = sum(
            1
            for c in _latest_config_per_user()
            if legacy_ids.has_legacy_keys(group_levels=c.group_levels, overrides=c.overrides, limits=c.limits)
        )
        latest_policy = AiPolicyVersion.objects.order_by("-version").first()
        policies = int(bool(latest_policy and legacy_ids.has_legacy_keys(caps=latest_policy.caps)))
        out("Khoá AI:")
        out(f"  việc AI còn mã lệnh cũ: {actions_command}")
        out(f"  việc AI còn nhóm nhận việc tên cũ: {actions_group}")
        out(f"  user có cấu hình mới nhất còn khoá cũ (sẽ thêm phiên bản mới): {configs}")
        out(f"  chính sách mới nhất còn khoá cũ (sẽ thêm phiên bản mới): {policies}")
        out(f"Xung đột: {conflicts}")
