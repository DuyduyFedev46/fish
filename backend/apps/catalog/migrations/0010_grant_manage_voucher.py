"""
SHOP-3b-01 / BR-DM-23: cấp quyền Tầng 2 `catalog.manage_voucher` ("Quản lý mã giảm giá") CHỈ cho Group `owner`.
Chủ uỷ cho nhóm khác ở màn Phân quyền (việc `manage_voucher`). Mẫu: `sales/0016_grant_view_order_customer_info`.
Lùi: gỡ quyền khỏi nhóm.
"""
from django.db import migrations

GROUPS = ["owner"]
CODENAME = "manage_voucher"


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("catalog"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="catalog", codename=CODENAME)


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(content_type__app_label="catalog", codename=CODENAME).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_rename_groups_to_english"),
        ("catalog", "0009_voucher"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
