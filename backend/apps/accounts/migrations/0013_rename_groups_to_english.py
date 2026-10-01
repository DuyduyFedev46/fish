"""
P8b Lô 4 (R2 Critical): đổi tên 5 Group sang tiếng Anh, GIỮ NGUYÊN id.

    chu -> owner, quan_ly -> manager, nv_kho -> warehouse_staff, nv_giao -> delivery_staff, cskh -> customer_service

Chỉ `Group.objects.filter(name=cũ).update(name=mới)`: id không đổi nên `auth_group_permissions` (quyền của Group)
và `auth_user_groups` (thành viên) đi theo, không phải sao chép hay gán lại. Tuyệt đối không xoá rồi tạo lại Group.

- Có cả tên cũ lẫn tên mới của cùng một vai: dừng (RuntimeError), không đổi gì, để người vận hành xử lý tay.
- Chỉ có tên mới, hoặc không có Group nào: bỏ qua (chạy lại không đổi gì).
- Reverse đổi ngược về tên cũ theo cùng quy tắc.
- Chỉ in số lượng, không in tên người dùng.

Thứ tự: phụ thuộc thêm các migration ở app khác gán quyền theo TÊN Group cũ (`ai/0002`, `content/0002`,
`sales/0010`) để trên DB mới chúng chạy TRƯỚC khi đổi tên. Các migration cũ KHÔNG được sửa: chúng đóng băng tên cũ.
"""
from django.db import migrations

# Tên đóng băng tại thời điểm migration; không import `accounts.roles` vì hằng đó sẽ còn đổi.
RENAMES = (
    ("chu", "owner"),  # naming: allow - tên Group tại thời điểm migration, đóng băng
    ("quan_ly", "manager"),  # naming: allow - tên Group tại thời điểm migration, đóng băng
    ("nv_kho", "warehouse_staff"),  # naming: allow - tên Group tại thời điểm migration, đóng băng
    ("nv_giao", "delivery_staff"),  # naming: allow - tên Group tại thời điểm migration, đóng băng
    ("cskh", "customer_service"),  # naming: allow - tên Group tại thời điểm migration, đóng băng
)


def _rename(apps, pairs):
    Group = apps.get_model("auth", "Group")
    names = {name for pair in pairs for name in pair}
    existing = set(Group.objects.filter(name__in=names).values_list("name", flat=True))
    for source, target in pairs:
        if source in existing and target in existing:
            raise RuntimeError(
                f"Group '{source}' và '{target}' cùng tồn tại; không tự gộp. Xử lý tay rồi chạy lại migrate."
            )
    renamed = 0
    for source, target in pairs:
        if source in existing:
            renamed += Group.objects.filter(name=source).update(name=target)
    if renamed:
        print(f"  accounts: đã đổi tên {renamed} Group (giữ id)")
    return renamed


def rename_groups_forward(apps, schema_editor):
    _rename(apps, RENAMES)


def rename_groups_backward(apps, schema_editor):
    _rename(apps, tuple((target, source) for source, target in RENAMES))


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_revoke_customer_view_warehouse_staff"),
        ("ai", "0002_grant_manage_ai_policy"),
        ("content", "0002_grant_content_perms"),
        ("sales", "0010_grant_view_privacy_consent"),
    ]

    operations = [
        migrations.RunPython(rename_groups_forward, rename_groups_backward),
    ]
