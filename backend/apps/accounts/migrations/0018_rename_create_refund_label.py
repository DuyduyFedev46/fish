"""
Đổi tên hiển thị quyền `sales.create_refund` thành "Lập phiếu hoàn tiền" (P7, bổ sung cho 0017).

Django không cập nhật `auth_permission.name` của quyền đã có. Chỉ đổi cột `name`; idempotent; có chiều ngược.
"""
from django.db import migrations

APP_LABEL = "sales"
CODENAME = "create_refund"
NEW_NAME = "Lập phiếu hoàn tiền"
OLD_NAME = "Tạo phiếu hoàn tiền"


def _set_name(apps, name):
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.filter(content_type__app_label=APP_LABEL, codename=CODENAME).update(name=name)


def rename_forward(apps, schema_editor):
    _set_name(apps, NEW_NAME)


def rename_backward(apps, schema_editor):
    _set_name(apps, OLD_NAME)


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("accounts", "0017_rename_permission_labels"),
        ("sales", "0018_alter_refund_create_permission_label"),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_backward),
    ]
