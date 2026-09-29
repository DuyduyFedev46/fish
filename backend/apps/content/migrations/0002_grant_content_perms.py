"""
Gán 8 quyền của app content cho Group chu và quan_ly (CMS-01-AC1, §2.6 02b-tech-design).
nv_kho và nv_giao KHÔNG có quyền nào của app content.
"""
from django.db import migrations

GROUPS = ["chu", "quan_ly"]
CONTENT_PERMS = [
    "add_category",
    "change_category",
    "view_category",
    "add_entry",
    "change_entry",
    "delete_entry",
    "view_entry",
    "publish_entry",
]


def grant(apps, schema_editor):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    # post_migrate chưa chạy trong lúc migrate -> tự sinh Permission của app content
    create_permissions(global_apps.get_app_config("content"), apps=global_apps, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    perms = list(
        Permission.objects.filter(content_type__app_label="content", codename__in=CONTENT_PERMS)
    )
    for group in Group.objects.filter(name__in=GROUPS):
        group.permissions.add(*perms)


def revoke(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    perms = list(
        Permission.objects.filter(content_type__app_label="content", codename__in=CONTENT_PERMS)
    )
    if perms:
        for group in Group.objects.filter(name__in=GROUPS):
            group.permissions.remove(*perms)


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0001_initial"),
        ("accounts", "0002_seed_permission_groups"),
    ]

    operations = [
        migrations.RunPython(grant, revoke),
    ]
