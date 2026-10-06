"""
CS-18 (2026-09-28-cskh-xac-nhan-in-tem, Lô 5, 02b §2.7 và §3.1): cấp quyền Tầng 1 của `CallScript`.

- `owner`: view + add + change (soạn kịch bản).
- `manager`, `customer_service`: chỉ view.
- `warehouse_staff`, `delivery_staff`: không có.
Đặt trong app `delivery` (không tạo migration `accounts/`, vì có thể trùng số với việc phạm vi dữ liệu).
Dùng `add`, không `set`: chạy 2 lần không đổi gì. Mẫu: `0006_grant_assign_deliverynote`.
"""
from django.db import migrations

GRANTS = {
    "owner": ["view_callscript", "add_callscript", "change_callscript"],
    "manager": ["view_callscript"],
    "customer_service": ["view_callscript"],
}


def _ensure_permissions():
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("delivery"), apps=global_apps, verbosity=0)


def grant(apps, schema_editor):
    _ensure_permissions()
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for group_name, codenames in GRANTS.items():
        group = Group.objects.filter(name=group_name).first()
        if not group:
            continue
        for perm in Permission.objects.filter(content_type__app_label="delivery", codename__in=codenames):
            group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for group_name, codenames in GRANTS.items():
        group = Group.objects.filter(name=group_name).first()
        if not group:
            continue
        for perm in Permission.objects.filter(content_type__app_label="delivery", codename__in=codenames):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_rename_groups_to_english"),
        ("delivery", "0008_callscript"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
