"""
S03 (AI Native ERP) — AuditLog thêm actor_kind / ai_actor / proposal_ref (BR-AI-08, Q6).

- 3 field backward-compatible: default `actor_kind="user"`, ai_actor/proposal_ref rỗng —
  dòng cũ giữ nguyên giá trị (bất biến 8, lý do ghi ở 01-analysis §4.4).
- Backfill actor_kind: actor null → system, còn lại → user (default schema đã là user).
- Gán `accounts.view_auditlog` cho chu + quan_ly (theo mẫu 0002/0006: quyền Group phải đi
  bằng data migration để dev/staging/prod không lệch). nv_kho/nv_giao KHÔNG có (S03-AC5).
  Lưu ý: perm `view_auditlog` đã tồn tại từ 0001 qua `default_permissions=("view",)` —
  chu đã có từ 0002 (mọi perm business apps) nên lệnh add là no-op an toàn.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_actor_kind(apps, schema_editor):
    AuditLog = apps.get_model("accounts", "AuditLog")
    AuditLog.objects.filter(actor__isnull=True).update(actor_kind="system")


def _perm(apps):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    # post_migrate chưa chạy trong lúc migrate → tự sinh permission của app accounts.
    create_permissions(global_apps.get_app_config("accounts"), apps=global_apps, verbosity=0)
    Permission = apps.get_model("auth", "Permission")
    return Permission.objects.get(content_type__app_label="accounts", codename="view_auditlog")


def grant_view_auditlog(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    perm = _perm(apps)
    for group in Group.objects.filter(name__in=["chu", "quan_ly"]):
        group.permissions.add(perm)


def revoke_view_auditlog(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perm = Permission.objects.filter(
        content_type__app_label="accounts", codename="view_auditlog"
    ).first()
    if perm:
        for group in Group.objects.filter(name__in=["chu", "quan_ly"]):
            group.permissions.remove(perm)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_grant_change_item_image"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="actor_kind",
            field=models.CharField(
                choices=[("user", "Người dùng"), ("system", "Hệ thống"), ("ai", "AI (thay người dùng)")],
                default="user",
                max_length=10,
                verbose_name="Loại tác nhân",
            ),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="ai_actor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="AI thay cho ai",
            ),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="proposal_ref",
            field=models.CharField(blank=True, max_length=64, verbose_name="Mã đề xuất AI"),
        ),
        migrations.RunPython(backfill_actor_kind, migrations.RunPython.noop),
        migrations.RunPython(grant_view_auditlog, revoke_view_auditlog),
    ]
