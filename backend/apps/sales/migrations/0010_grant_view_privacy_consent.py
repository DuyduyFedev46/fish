"""
GL-05 / BR-PQ: Gán quyền Tầng 2 mới `sales.view_privacy_consent` cho Group `chu` và `quan_ly`.

Chỉ Chủ và Quản lý mới có quyền xem bằng chứng đồng ý xử lý dữ liệu của đơn (GL-05-AC1, GL-05-AC3).
nv_kho, nv_giao, cskh KHÔNG có quyền này.
"""
from django.db import migrations

GROUPS = ["chu", "quan_ly"]


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("sales"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="sales", codename="view_privacy_consent")


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(
        content_type__app_label="sales", codename="view_privacy_consent"
    ).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_seed_permission_groups"),
        ("sales", "0009_salesorder_view_privacy_consent"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
