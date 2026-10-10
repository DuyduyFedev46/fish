# SHOP-2-01 (02b §4): đường dẫn nhóm hàng để lọc `/shop/?group=<slug>`.
# Bước 1/3: thêm cột cho phép null (chưa unique) để dòng cũ không vỡ; 0006 điền, 0007 khoá unique.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_alter_item_options_alter_item_item_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemgroup",
            name="slug",
            field=models.SlugField(blank=True, max_length=80, null=True, verbose_name="Đường dẫn"),
        ),
    ]
