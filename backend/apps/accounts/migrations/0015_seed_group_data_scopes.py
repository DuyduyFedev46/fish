"""
PV-02 (BR-PQ-33, UC-5 bước 1): gieo phạm vi dữ liệu theo nhóm bằng ĐÚNG hiện trạng, để ngày bật tính năng không ai đổi quyền.

Giá trị chép cứng ở đây, không import `data_scopes/catalog.py` (migration phải đóng băng; test `test_seed_migration`
kiểm 0015 == `catalog.defaults`). Tên nhóm là tên tiếng Anh sau `0013_rename_groups_to_english`.

- `GroupAccessConfig(row_version=1)` cho 5 nhóm (kể cả `owner`). Không có dòng phạm vi cho `owner` (luôn rộng nhất).
- Mặc định theo bảng contract 02-stories.md: Q (manager) và K (warehouse_staff) thấy tất cả như hôm nay; G (delivery_staff)
  chỉ phiếu gán cho mình; C (customer_service) đơn gán cho mình hoặc trong phạm vi gọi.
- D7 `customers` = `all` nếu nhóm ĐANG có `sales.view_customer_list` lúc migrate (đọc quyền thực tế, Chủ có thể đã đổi qua
  ma trận B4); còn lại G = `assigned_deliveries`, nhóm khác = `none`. Chạy sau `sales/0013` nên Q đã có quyền này.
- D4 của G lưu `pending_or_called_recently` (rank 0, ô mờ vì G không có việc gọi xác nhận).
- Idempotent: `get_or_create`, KHÔNG ghi đè giá trị đã có. Không đụng quyền Tầng 1/2 của bất kỳ nhóm nào.
- Lùi: xoá các dòng của 5 nhóm (bảng sẽ bị 0014 xoá tiếp nếu lùi hẳn).
"""
from django.db import migrations

ROLE_GROUPS = ("owner", "manager", "warehouse_staff", "delivery_staff", "customer_service")
CUSTOMER_LIST_PERMISSION = ("sales", "view_customer_list")

# nhóm -> (orders, deliveries, confirmation, returns, receipts). `customers` tính riêng theo quyền lúc migrate.
DEFAULTS = {
    "manager": ("all", "all", "all_pending", "all", "all"),
    "warehouse_staff": ("all", "all", "all_pending", "all", "all"),
    "delivery_staff": ("assigned_deliveries", "assigned", "pending_or_called_recently", "assigned_deliveries", "all"),
    "customer_service": (
        "assigned_or_confirmation", "assigned", "pending_or_called_recently", "assigned_deliveries", "all",
    ),
}
OBJECT_KEYS = ("orders", "deliveries", "confirmation", "returns", "receipts")


def _customers_value(group, has_customer_list):
    if has_customer_list:
        return "all"
    return "assigned_deliveries" if group.name == "delivery_staff" else "none"


def seed_group_data_scopes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    GroupAccessConfig = apps.get_model("accounts", "GroupAccessConfig")
    GroupDataScope = apps.get_model("accounts", "GroupDataScope")
    app_label, codename = CUSTOMER_LIST_PERMISSION
    for group in Group.objects.filter(name__in=ROLE_GROUPS):
        GroupAccessConfig.objects.get_or_create(group=group, defaults={"row_version": 1})
        if group.name not in DEFAULTS:
            continue  # owner: không lưu dòng phạm vi
        has_customer_list = group.permissions.filter(content_type__app_label=app_label, codename=codename).exists()
        values = dict(zip(OBJECT_KEYS, DEFAULTS[group.name]))
        values["customers"] = _customers_value(group, has_customer_list)
        for key, value in values.items():
            GroupDataScope.objects.get_or_create(group=group, object_key=key, defaults={"value": value})


def unseed_group_data_scopes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    groups = Group.objects.filter(name__in=ROLE_GROUPS)
    apps.get_model("accounts", "GroupDataScope").objects.filter(group__in=groups).delete()
    apps.get_model("accounts", "GroupAccessConfig").objects.filter(group__in=groups).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0014_group_data_scopes"),
        ("sales", "0013_grant_view_customer_list"),
    ]

    operations = [migrations.RunPython(seed_group_data_scopes, unseed_group_data_scopes)]
