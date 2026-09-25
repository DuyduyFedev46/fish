"""
Fixture phân quyền — data migration (business-process-spec.md §14).

Tạo 4 Group cộng dồn (chu, quan_ly, nv_kho, nv_giao) và gán permission theo
ma trận Tầng 1 (mục 1.4) + Tầng 2 (mục 1.5). BẮT BUỘC là data migration, không
bấm tay trong Admin — nếu không thì môi trường dev/staging/prod lệch nhau.

Ghi chú:
- `chu` = toàn quyền (thực tế superuser) nhưng vẫn định nghĩa Group tường minh (1.3).
- Ký hiệu letters: c=add, r=view, u=change, d=delete. `*` (phạm vi dòng/cột) là
  kiểm soát Tầng 3 ở queryset/serializer (Phase 3) — ở mức Group vẫn cấp perm gốc.
- Perm nhạy cảm (close_batch, add_purchasecost, confirm_refund,
  confirm_payment_manual, view_costprice, view_profitreport, manage_staff) chỉ `chu`.
"""
from django.db import migrations

BUSINESS_APPS = ["accounts", "catalog", "purchasing", "inventory", "sales", "delivery", "reports"]

LETTER_TO_ACTION = {"c": "add", "r": "view", "u": "change", "d": "delete"}

# --- Tầng 1: ma trận CRUD (model_name -> letters) --------------------------
QUAN_LY = {
    # Master data: chỉ xem
    "itemgroup": "r", "item": "r", "bundleline": "r",
    "pricelist": "r", "itemprice": "r", "pricingrule": "r",
    "warehouse": "r", "batch": "r",
    # Vận hành được uỷ
    "supplier": "cru", "customer": "cru",
    "purchasereceipt": "cru", "purchasereceiptline": "cru",
    "purchaseinvoice": "r",
    "deliverynote": "cru",
    "stockentry": "cru",
    "stockreconciliation": "cru", "stockreconciliationline": "cru",
    "returntostock": "r",
    "refund": "cru",
    # Chỉ xem
    "salesorder": "r", "salesorderline": "r",
    "salesinvoice": "r", "salesinvoiceline": "r",
    "stockledgerentry": "r", "paymenttransaction": "r",
    "staffprofile": "r",
}
NV_KHO = {
    "itemgroup": "r", "item": "r", "bundleline": "r",
    "supplier": "r", "customer": "r", "warehouse": "r", "batch": "r",
    "purchasereceipt": "cru", "purchasereceiptline": "cru",  # * trong ngày, phiếu của mình
    "salesorder": "r", "salesorderline": "r",
    "salesinvoice": "r", "salesinvoiceline": "r",  # * ẩn giá vốn (Tầng 3)
    "deliverynote": "cru",
    "returntostock": "cr",
    "stockentry": "cru",
    "stockreconciliation": "cru", "stockreconciliationline": "cru",
    "stockledgerentry": "r",
    "staffprofile": "r",  # * hồ sơ của mình (Tầng 3)
}
NV_GIAO = {
    "customer": "r",              # * khách thuộc phiếu được gán
    "salesorder": "r", "salesorderline": "r",  # * đơn thuộc phiếu được gán
    "deliverynote": "ru",         # * chỉ phiếu gán cho mình, chỉ sửa trạng thái
    "returntostock": "cr",
    "staffprofile": "r",          # * hồ sơ của mình
}

# --- Tầng 2: custom permission (codename) ----------------------------------
CUSTOM_QUAN_LY = [
    "publish_batch",
    "approve_stockreconciliation",
    "approve_returntostock",
    "cancel_paid_order",
    "create_refund",
]
# nv_kho / nv_giao: không có custom perm Tầng 2.

# Quyền quản trị User (auth) — quan_ly/nv_* chỉ xem; chu toàn quyền.
AUTH_VIEW_USER = ["view_user"]


def expand(spec):
    return [f"{LETTER_TO_ACTION[ch]}_{model}" for model, letters in spec.items() for ch in letters]


def seed(apps, schema_editor):
    # Đảm bảo Permission đã tồn tại: post_migrate chạy SAU khi migrate xong, nên
    # trong RunPython ta chủ động sinh permission cho mọi app.
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    for config in global_apps.get_app_configs():
        create_permissions(config, apps=global_apps, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    def perms_by_codenames(codenames):
        found = Permission.objects.filter(codename__in=codenames)
        missing = set(codenames) - set(found.values_list("codename", flat=True))
        if missing:
            raise RuntimeError(f"Thiếu permission (sai codename?): {sorted(missing)}")
        return list(found)

    # chu: tất cả perm của các app nghiệp vụ + quản trị user/group của auth.
    chu, _ = Group.objects.get_or_create(name="chu")
    chu_perms = list(Permission.objects.filter(content_type__app_label__in=BUSINESS_APPS))
    chu_perms += list(
        Permission.objects.filter(
            content_type__app_label="auth",
            content_type__model__in=["user", "group"],
        )
    )
    chu.permissions.set(chu_perms)

    quan_ly, _ = Group.objects.get_or_create(name="quan_ly")
    quan_ly.permissions.set(
        perms_by_codenames(expand(QUAN_LY) + CUSTOM_QUAN_LY + AUTH_VIEW_USER)
    )

    nv_kho, _ = Group.objects.get_or_create(name="nv_kho")
    nv_kho.permissions.set(perms_by_codenames(expand(NV_KHO) + AUTH_VIEW_USER))

    nv_giao, _ = Group.objects.get_or_create(name="nv_giao")
    nv_giao.permissions.set(perms_by_codenames(expand(NV_GIAO) + AUTH_VIEW_USER))


def unseed(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["chu", "quan_ly", "nv_kho", "nv_giao"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("catalog", "0001_initial"),
        ("purchasing", "0001_initial"),
        ("inventory", "0002_initial"),
        ("sales", "0001_initial"),
        ("delivery", "0002_initial"),
        ("reports", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
