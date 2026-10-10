# SHOP-2-01 AC5 (02b §4): điền slug cho nhóm hiện có.
# Bỏ dấu, `đ`->`d`, chữ thường, nối bằng `-`; trùng thì thêm `-2`, `-3`… theo thứ tự id.
# Hàm slug được CHÉP vào đây (không import code app) để migration không đổi nghĩa khi code đổi.
# Chạy lại an toàn: chỉ điền dòng chưa có slug và tránh mọi slug đang tồn tại. Chiều ngược: đặt null.
import re
import unicodedata

from django.db import migrations
from django.db.models import Q

_MAX_LENGTH = 80
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slugify(text):
    folded = unicodedata.normalize("NFD", str(text or ""))
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn")
    folded = folded.replace("đ", "d").replace("Đ", "D").lower()
    return _NON_ALNUM.sub("-", folded).strip("-")[:_MAX_LENGTH].strip("-") or "group"


def populate_slugs(apps, schema_editor):
    ItemGroup = apps.get_model("catalog", "ItemGroup")
    taken = {s for s in ItemGroup.objects.exclude(slug__isnull=True).exclude(slug="").values_list("slug", flat=True)}
    for group in ItemGroup.objects.filter(Q(slug__isnull=True) | Q(slug="")).order_by("pk"):
        base = _slugify(group.name)
        candidate, counter = base, 2
        while candidate in taken:
            suffix = f"-{counter}"
            candidate = f"{base[: _MAX_LENGTH - len(suffix)].strip('-')}{suffix}"
            counter += 1
        taken.add(candidate)
        group.slug = candidate
        group.save(update_fields=["slug"])


def clear_slugs(apps, schema_editor):
    apps.get_model("catalog", "ItemGroup").objects.update(slug=None)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_itemgroup_slug"),
    ]

    operations = [
        migrations.RunPython(populate_slugs, clear_slugs),
    ]
