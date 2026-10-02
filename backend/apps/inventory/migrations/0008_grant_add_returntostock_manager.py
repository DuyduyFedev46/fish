"""
#21 (Duy chốt 02/10): cấp quyền `inventory.add_returntostock` cho Group `manager` để Quản lý tạo phiếu hàng hoàn.

Quản lý vốn chỉ đọc + duyệt (`accounts/0002`). Chủ đã có đủ quyền; nhân viên kho, người giao đã có quyền tạo.
Đảo ngược được: gỡ quyền khỏi `manager`. Tên Group là tên tiếng Anh sau `accounts/0013_rename_groups_to_english`.
Mẫu: `delivery/0006_grant_assign_deliverynote`.
"""
from django.db import migrations

GROUPS = ["manager"]
APP_LABEL = "inventory"
CODENAME = "add_returntostock"


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config(APP_LABEL), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label=APP_LABEL, codename=CODENAME)


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(content_type__app_label=APP_LABEL, codename=CODENAME).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_rename_groups_to_english"),
        ("inventory", "0007_returntostock_cancelled_status"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
