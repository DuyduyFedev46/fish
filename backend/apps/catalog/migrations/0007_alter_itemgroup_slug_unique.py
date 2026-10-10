# SHOP-2-01 (02b §4): bước 3/3 — slug bắt buộc và duy nhất (0006 đã điền hết).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0006_populate_itemgroup_slug"),
    ]

    operations = [
        migrations.AlterField(
            model_name="itemgroup",
            name="slug",
            field=models.SlugField(blank=True, max_length=80, unique=True, verbose_name="Đường dẫn"),
        ),
    ]
