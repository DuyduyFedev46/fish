"""
M-1/B5 (rà soát bảo mật 15/11): tạo bảng `django_cache` cho `DatabaseCache` (cache dùng chung giữa worker
gunicorn và các instance Cloud Run, để throttle đếm chung). Giống `manage.py createcachetable`, nhưng chạy trong
`migrate` nên job `cangca-migrate` tự tạo, không cần bước tay. Idempotent: bảng đã có thì bỏ qua.
"""
from django.apps.registry import Apps
from django.db import migrations, models

CACHE_TABLE = "django_cache"


def _cache_entry_model():
    class CacheEntry(models.Model):
        cache_key = models.CharField(max_length=255, unique=True, primary_key=True)
        value = models.TextField()
        expires = models.DateTimeField(db_index=True)

        class Meta:
            apps = Apps()  # registry riêng, không đăng ký vào project
            app_label = "accounts"
            db_table = CACHE_TABLE

    return CacheEntry


def create_cache_table(apps, schema_editor):
    if CACHE_TABLE in schema_editor.connection.introspection.table_names():
        return
    schema_editor.create_model(_cache_entry_model())


def drop_cache_table(apps, schema_editor):
    if CACHE_TABLE in schema_editor.connection.introspection.table_names():
        schema_editor.delete_model(_cache_entry_model())


class Migration(migrations.Migration):
    dependencies = [("accounts", "0018_rename_create_refund_label")]
    operations = [migrations.RunPython(create_cache_table, drop_cache_table)]
