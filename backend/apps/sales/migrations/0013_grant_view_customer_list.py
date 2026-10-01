"""
B2 / BR-PQ-31 (ERP theo design, Lô 6): cấp quyền Tầng 2 `sales.view_customer_list` ("Xem khách hàng")
cho Group `owner`, `manager`.

Chỉ Chủ và Quản lý xem danh bạ khách. `warehouse_staff`, `delivery_staff`, `customer_service` KHÔNG có:
người giao chỉ thấy khách của phiếu giao của mình qua quyền Tầng 1 `view_customer` (BR-PQ-12, SR-PII-01).
Tên Group là tên tiếng Anh sau `accounts/0013_rename_groups_to_english`; migration này phụ thuộc vào đó nên tên khớp.
Mẫu: `sales/0010_grant_view_privacy_consent`.
"""
from django.db import migrations

GROUPS = ["owner", "manager"]


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("sales"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="sales", codename="view_customer_list")


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(
        content_type__app_label="sales", codename="view_customer_list"
    ).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_rename_groups_to_english"),
        ("sales", "0012_customer_view_customer_list"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
