"""
B1 (ERP theo design, Lô 8): thêm `StockReconciliation.updated_at` để phát hiện hai người sửa cùng lúc (409 STALE_STATE).

Chỉ thêm. Phiếu đã có điền `updated_at = created_at` (một lệnh UPDATE, không đụng cột khác). Lùi về 0004 chỉ bỏ cột.
"""
from django.db import migrations, models
from django.db.models import F


def backfill_updated_at(apps, schema_editor):
    Reconciliation = apps.get_model("inventory", "StockReconciliation")
    # Cột vừa thêm: AddField điền "bây giờ" cho dòng cũ (auto_now), nên ghi đè mọi dòng bằng ngày tạo.
    Reconciliation.objects.update(updated_at=F("created_at"))


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_batchsupplierreturn'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockreconciliation',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, help_text='Phiên bản phiếu: client gửi lại khi sửa dòng, lệch thì 409 STALE_STATE (B1, W6f).', null=True, verbose_name='Cập nhật lúc'),
        ),
        migrations.RunPython(backfill_updated_at, migrations.RunPython.noop),
    ]
