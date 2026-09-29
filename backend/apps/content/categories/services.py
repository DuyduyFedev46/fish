"""Nghiệp vụ quản lý chuyên mục (§4.7 02b-tech-design)."""
from django.db import models
from apps.common.exceptions import BusinessError
from apps.content.body.slug import normalize_name_key, slugify_vi
from apps.content.models.categories import Category


def create_category(*, name: str, description: str = "", order: int = 0) -> Category:
    """Tạo chuyên mục mới: tên duy nhất (bỏ dấu/chữ thường), slug tự sinh."""
    name = str(name or "").strip()
    if not name:
        raise BusinessError("Tên chuyên mục không được để trống.", code="BR-ND-04")

    name_key = normalize_name_key(name)
    if Category.objects.filter(name_key=name_key).exists():
        raise BusinessError(f"Chuyên mục '{name}' đã tồn tại (BR-ND-04).", code="BR-ND-04")

    base_slug = slugify_vi(name, max_len=80) or "chuyen-muc"
    slug = base_slug
    n = 2
    while Category.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{n}"
        n += 1

    return Category.objects.create(
        name=name,
        name_key=name_key,
        slug=slug,
        description=str(description or "").strip(),
        order=int(order or 0),
        is_active=True,
    )


def update_category(*, category: Category, data: dict) -> Category:
    """Sửa chuyên mục: đổi tên giữ slug; ngừng dùng chặn khi còn bài Đã đăng."""
    if "name" in data:
        new_name = str(data["name"] or "").strip()
        if not new_name:
            raise BusinessError("Tên chuyên mục không được để trống.", code="BR-ND-04")
        name_key = normalize_name_key(new_name)
        if Category.objects.filter(name_key=name_key).exclude(pk=category.pk).exists():
            raise BusinessError(f"Chuyên mục '{new_name}' đã tồn tại (BR-ND-04).", code="BR-ND-04")
        category.name = new_name
        category.name_key = name_key
        # slug giữ nguyên (CMS-02-AC3)

    if "description" in data:
        category.description = str(data["description"] or "").strip()

    if "order" in data:
        category.order = int(data["order"] or 0)

    if "is_active" in data:
        new_active = bool(data["is_active"])
        if not new_active and category.is_active:
            # CMS-02-AC4: đếm bài status=published thuộc chuyên mục (theo Entry.category và published_version.category)
            from apps.content.models.entries import Entry

            published_qs = (
                Entry.objects.filter(
                    models.Q(category=category) | models.Q(published_version__category=category),
                    status="published",
                )
                .distinct()
                .order_by("-id")
            )
            total = published_qs.count()
            if total > 0:
                sample = list(published_qs.values("id", "title")[:5])
                raise BusinessError(
                    f"Chuyên mục còn {total} bài đang đăng, không thể ngừng dùng (BR-ND-02).",
                    code="BR-ND-02",
                    extra={"entries": sample, "total": total},
                )
            category.is_active = False
        elif new_active and not category.is_active:
            category.is_active = True

    category.save()
    return category
