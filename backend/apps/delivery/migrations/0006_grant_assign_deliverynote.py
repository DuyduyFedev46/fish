"""
B6 / BR-GH-23 (ERP theo design, Lô 4): cấp quyền Tầng 2 `delivery.assign_deliverynote` cho Group `owner`, `manager`.

Chỉ Chủ và Quản lý giao hoặc đổi người giao. `warehouse_staff`, `delivery_staff`, `customer_service` KHÔNG có:
người giao đã có `change_deliverynote` để báo kết quả, không được tự chia việc cho nhau (BR-PQ-12).
Tên Group là tên tiếng Anh sau `accounts/0013_rename_groups_to_english`; migration này phụ thuộc vào đó nên tên khớp.
Mẫu: `sales/0010_grant_view_privacy_consent`.
"""
from django.db import migrations

GROUPS = ["owner", "manager"]


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("delivery"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="delivery", codename="assign_deliverynote")


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(
        content_type__app_label="delivery", codename="assign_deliverynote"
    ).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_rename_groups_to_english"),
        ("delivery", "0005_deliverynote_failure_reason_and_more"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
