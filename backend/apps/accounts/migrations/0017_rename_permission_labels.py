"""
Đổi tên hiển thị của quyền Tầng 2 theo bảng tên chuẩn (lô áp tên chuẩn, P1–P4, P9, P10, P12, P13).

Django KHÔNG cập nhật `auth_permission.name` của quyền đã tồn tại khi `Meta.permissions` đổi nhãn
(`post_migrate` chỉ tạo quyền còn thiếu). Nếu không có migration này, Django Admin ở staging/production vẫn hiện
"Publish lô ra Shop". Migration chỉ sửa cột `name` theo (app_label, codename); không đụng codename, gán Group
hay dữ liệu nghiệp vụ. Idempotent (chạy hai lần cùng kết quả) và có chiều ngược trả về tên cũ.
"""
from django.db import migrations

# (app_label, codename, tên mới, tên cũ)
PERMISSION_RENAMES = [
    ("sales", "confirm_payment_manual", "Xác nhận đã nhận tiền", "Xác nhận thanh toán thủ công"),  # P1
    ("inventory", "publish_batch", "Mở bán lô", "Publish lô ra Shop"),  # P2
    ("inventory", "cancel_expired_batch", "Huỷ lô quá hạn (ghi lỗ)", "Huỷ lô quá hạn (hạch toán lỗ)"),  # P3
    ("inventory", "approve_returntostock", "Duyệt hàng hoàn", "Duyệt hàng hoàn về kho"),  # P4
    ("delivery", "assign_deliverynote", "Chọn người giao", "Giao phiếu cho người giao"),  # P9
    ("delivery", "pack_deliverynote", "Soạn hàng", "Đóng gói phiếu giao"),  # P10
    ("reports", "view_profitreport", "Xem báo cáo lãi lỗ", "Xem báo cáo giá vốn / lãi lỗ"),  # P12
    ("reports", "view_dashboard", "Xem Tổng quan", "Xem Tổng quan vận hành"),  # P12
    ("catalog", "change_item_image", "Sửa ảnh mặt hàng", "Thêm / thay / gỡ ảnh mặt hàng"),  # P13
]


def _apply(apps, *, to_new: bool):
    Permission = apps.get_model("auth", "Permission")
    for app_label, codename, new_name, old_name in PERMISSION_RENAMES:
        Permission.objects.filter(content_type__app_label=app_label, codename=codename).update(
            name=new_name if to_new else old_name
        )


def rename_forward(apps, schema_editor):
    _apply(apps, to_new=True)


def rename_backward(apps, schema_editor):
    _apply(apps, to_new=False)


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("accounts", "0016_alter_auditlog_actor_kind_alter_staffprofile_status"),
        ("sales", "0017_alter_paymenttransaction_options_and_more"),
        ("delivery", "0011_alter_confirmationtask_options_and_more"),
        ("inventory", "0010_alter_batch_options_and_more"),
        ("catalog", "0004_alter_item_options_alter_item_item_type_and_more"),
        ("content", "0003_alter_entry_page_role"),
        ("reports", "0003_alter_profitreport_options"),
        ("purchasing", "0004_alter_purchasereceipt_options"),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_backward),
    ]
