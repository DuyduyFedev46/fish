"""
CS-01 / 02b §3.1: Tạo Group "cskh" và cấp 5 quyền Tầng 2 mới của delivery cho các Group.

Bảng quyền (02b §3.1):
- cskh: sales.view_salesorder, sales.view_salesorderline, delivery.confirm_with_customer, delivery.change_recipient
- quan_ly: thêm delivery.confirm_with_customer, delivery.change_recipient, delivery.decide_unconfirmed, delivery.pack_deliverynote, delivery.print_label
- nv_kho: thêm delivery.pack_deliverynote, delivery.print_label
- chu: thêm delivery.confirm_with_customer, delivery.change_recipient, delivery.decide_unconfirmed, delivery.pack_deliverynote, delivery.print_label

Chạy 2 lần không đổi gì (idempotent - CS-01-AC1).
"""
from django.db import migrations

CSKH_GROUP_NAME = "cskh"

PERMISSIONS_MAP = {
    "cskh": [
        ("sales", "view_salesorder"),
        ("sales", "view_salesorderline"),
        ("delivery", "confirm_with_customer"),
        ("delivery", "change_recipient"),
    ],
    "quan_ly": [
        ("delivery", "confirm_with_customer"),
        ("delivery", "change_recipient"),
        ("delivery", "decide_unconfirmed"),
        ("delivery", "pack_deliverynote"),
        ("delivery", "print_label"),
    ],
    "nv_kho": [
        ("delivery", "pack_deliverynote"),
        ("delivery", "print_label"),
    ],
    "chu": [
        ("delivery", "confirm_with_customer"),
        ("delivery", "change_recipient"),
        ("delivery", "decide_unconfirmed"),
        ("delivery", "pack_deliverynote"),
        ("delivery", "print_label"),
    ],
}


def _ensure_permissions(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    for app_label in ("delivery", "sales", "auth"):
        try:
            config = global_apps.get_app_config(app_label)
            create_permissions(config, apps=global_apps, verbosity=0)
        except LookupError:
            pass


def grant(apps, schema_editor):
    _ensure_permissions(apps)
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    # Tạo hoặc lấy group cskh
    Group.objects.get_or_create(name=CSKH_GROUP_NAME)

    for group_name, perms_list in PERMISSIONS_MAP.items():
        group = Group.objects.filter(name=group_name).first()
        if not group:
            continue
        for app_label, codename in perms_list:
            perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if perm:
                group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for group_name, perms_list in PERMISSIONS_MAP.items():
        group = Group.objects.filter(name=group_name).first()
        if not group:
            continue
        for app_label, codename in perms_list:
            perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if perm:
                group.permissions.remove(perm)

    Group.objects.filter(name=CSKH_GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_auditlog_ai_config_version_auditlog_ai_level_and_more"),
        ("delivery", "0004_cskh_confirmation"),
        ("sales", "0006_salesorder_checkout_attempts"),
    ]

    operations = [
        migrations.RunPython(grant, revoke),
    ]
