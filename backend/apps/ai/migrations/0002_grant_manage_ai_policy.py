"""
02b §7.2 / DW-13-AC5: Gán quyền Tầng 2 `ai.manage_ai_policy` cho Group `chu`.

Chỉ Chủ mới có quyền quản lý chính sách AI, tắt khẩn toàn cục, tắt AI của nhân viên,
và xem toàn bộ việc AI (BR-AI-22, BR-PQ-12).
quan_ly, nv_kho, nv_giao, cskh KHÔNG có quyền này.
"""
from django.db import migrations

GROUPS = ["chu"]


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("ai"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="ai", codename="manage_ai_policy")


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(
        content_type__app_label="ai", codename="manage_ai_policy"
    ).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_initial"),
        ("accounts", "0002_seed_permission_groups"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
