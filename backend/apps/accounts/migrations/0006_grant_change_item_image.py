"""
A2 (doc/features/2026-09-26-anh-mat-hang) — gán `catalog.change_item_image` cho chu, quan_ly.

Theo mẫu 0002/0003: quyền Group PHẢI đi bằng data migration để dev/staging/prod không
lệch (Q3, Duy 2026-09-26). nv_kho/nv_giao KHÔNG có — chỉ xem ảnh trong console
(`catalog.view_item`, đã có).
"""
from django.db import migrations

GROUPS = ["chu", "quan_ly"]


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    # post_migrate chưa chạy trong lúc migrate → tự sinh Permission của app catalog.
    create_permissions(global_apps.get_app_config("catalog"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="catalog", codename="change_item_image")


def grant(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(perm)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(
        content_type__app_label="catalog", codename="change_item_image"
    ).first()
    if perm:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_demorecord"),
        ("catalog", "0003_alter_item_options_itemimage"),
    ]

    operations = [migrations.RunPython(grant, revoke)]
