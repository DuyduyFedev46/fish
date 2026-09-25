"""
S6 — gán quyền `reports.view_dashboard` (mục "Tổng quan" của console) cho chu, quan_ly, nv_kho.

Theo mẫu 0002: quyền Group PHẢI đi bằng data migration để dev/staging/prod không lệch.
nv_giao không có: người chỉ thuộc nv_giao vào thẳng "Việc giao của tôi" (S6-AC3, S7-AC2).
`chu` được gán tường minh vì 0002 chỉ gán các perm tồn tại lúc chạy 0002.
"""
from django.db import migrations

GROUPS = ["chu", "quan_ly", "nv_kho"]


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    # post_migrate chưa chạy trong lúc migrate → tự sinh Permission của app reports.
    create_permissions(global_apps.get_app_config("reports"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="reports", codename="view_dashboard")


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(
        content_type__app_label="reports", codename="view_dashboard"
    ).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_seed_permission_groups"),
        ("reports", "0002_view_dashboard_permission"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
