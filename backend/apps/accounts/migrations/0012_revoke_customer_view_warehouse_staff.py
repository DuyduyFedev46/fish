"""
SR-PII-01 (Q-1, Duy chốt 01/10): NV kho không cần danh bạ khách -> gỡ `sales.view_customer` khỏi Group `nv_kho`.

Chỉ đổi gán quyền, không đổi bảng. Group khác không đổi. NV kho vẫn xem đơn hàng và phiếu giao
(đủ tên, SĐT, địa chỉ) vì quyền đó đến từ `sales.view_salesorder` và `delivery.view_deliverynote`.

Tên Group viết thẳng "nv_kho" (không import `accounts.roles`): migration phải đóng băng theo tên Group
tại thời điểm chạy; khi Lô 4 đổi tên Group, migration này vẫn trúng đúng Group lúc đó.
Idempotent: gỡ lại khi đã gỡ thì không đổi gì. Reverse trả quyền lại (`add`, cũng idempotent).
"""
from django.db import migrations

WAREHOUSE_STAFF_GROUP = "nv_kho"  # naming: allow - tên Group tại thời điểm migration, đóng băng
APP_LABEL = "sales"
CODENAME = "view_customer"


def _group_and_permission(apps):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    group = Group.objects.filter(name=WAREHOUSE_STAFF_GROUP).first()
    permission = Permission.objects.filter(content_type__app_label=APP_LABEL, codename=CODENAME).first()
    return group, permission


def revoke_view_customer(apps, schema_editor):
    group, permission = _group_and_permission(apps)
    if group is not None and permission is not None:
        group.permissions.remove(permission)


def restore_view_customer(apps, schema_editor):
    group, permission = _group_and_permission(apps)
    if group is not None and permission is not None:
        group.permissions.add(permission)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_seed_group_cskh"),
        ("sales", "0006_salesorder_checkout_attempts"),
    ]

    operations = [
        migrations.RunPython(revoke_view_customer, restore_view_customer),
    ]
