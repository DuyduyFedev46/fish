"""
DW-06 / TL-3 / V-DW3: Gán quyền Tầng 2 mới `inventory.cancel_expired_batch` cho Group `chu`.

Chỉ Chủ mới có quyền huỷ lô quá hạn để hạch toán lỗ (BR-LO-03, BR-PQ-12).
nv_kho, quan_ly, nv_giao KHÔNG có quyền này.
"""
from django.db import migrations

GROUPS = ["chu"]


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("inventory"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="inventory", codename="cancel_expired_batch")


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(
        content_type__app_label="inventory", codename="cancel_expired_batch"
    ).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_auditlog_auditlog_timeline_idx"),
        ("inventory", "0003_alter_batch_options"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
