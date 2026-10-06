"""
PV-07 / BR-PQ-38 (Q-4, Duy chốt 02/10/2026): cấp quyền Tầng 2 `sales.view_order_customer_info` ("Xem thông tin khách
trên đơn & hoá đơn", việc V2) cho cả 5 nhóm: `owner`, `manager`, `warehouse_staff`, `delivery_staff`, `customer_service`.

V2 mặc định BẬT cho mọi nhóm để ngày đầu hành vi giữ như hôm nay (NV kho vẫn thấy tên khách trên đơn, Duy duyệt D-1
06/10); Chủ tự tắt cho nhóm nào muốn đóng. V1 "Xem hoá đơn bán" không cần migration (quyền `view_salesinvoice(line)` đã có).
Tên Group là tên tiếng Anh sau `accounts/0013_rename_groups_to_english`. Mẫu: `sales/0013_grant_view_customer_list`.
Lùi: gỡ quyền khỏi 5 nhóm.
"""
from django.db import migrations

GROUPS = ["owner", "manager", "warehouse_staff", "delivery_staff", "customer_service"]
CODENAME = "view_order_customer_info"


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("sales"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="sales", codename=CODENAME)


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(content_type__app_label="sales", codename=CODENAME).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_rename_groups_to_english"),
        ("sales", "0015_salesorder_view_order_customer_info"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
