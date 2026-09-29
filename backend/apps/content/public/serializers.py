"""
Serializers cho API công khai nội dung (§8.6 02b-tech-design).
Không dùng ModelSerializer, dict dựng tường minh, tuyệt đối không có khoá cấm (Bất biến 1, 9).
"""

from typing import Any, Dict, List, Optional
from apps.catalog.images.storage import get_storage
from apps.content.body.sanitize import normalize_body
from apps.content.models.images import ContentImage


def _image_urls(ci: ContentImage) -> Dict[str, str]:
    storage = get_storage()
    entry_id = ci.entry_id
    image_id = ci.image_id
    return {
        size: storage.url(f"content/{entry_id}/{image_id}/{size}.webp")
        for size in ("sm", "md", "lg")
    }


def public_body(version: Any) -> Dict[str, Any]:
    """
    Lớp 1b (server, lúc trả công khai §6.1 02b-tech-design):
    Chạy lại normalize_body(strict=False) và chuyển khối image thành:
    {"type": "image", "alt": "...", "caption": "...", "width": ..., "height": ..., "urls": {"sm": "...", "md": "...", "lg": "..."}}
    Loại bỏ hoàn toàn trường image_id để không lộ ID nội bộ.
    """
    raw_body = version.body if isinstance(version.body, dict) else {}
    normalized = normalize_body(raw_body, strict=False)
    blocks = normalized.get("blocks", [])

    # Thu thập tất cả image_ids trong body
    image_ids = []
    for b in blocks:
        if b.get("type") == "image":
            img_id = b.get("image_id")
            if isinstance(img_id, int):
                image_ids.append(img_id)

    image_map: Dict[int, ContentImage] = {}
    if image_ids:
        for img in ContentImage.objects.filter(pk__in=image_ids):
            image_map[img.pk] = img

    public_blocks = []
    for b in blocks:
        if b.get("type") == "image":
            img_id = b.get("image_id")
            img = image_map.get(img_id) if isinstance(img_id, int) else None
            if img:
                public_blocks.append({
                    "type": "image",
                    "alt": img.alt or str(b.get("alt") or ""),
                    "caption": str(b.get("caption") or ""),
                    "width": img.width,
                    "height": img.height,
                    "urls": _image_urls(img),
                })
            # Nếu không tìm thấy ảnh thì bỏ qua để không lộ khối ảnh hỏng
        else:
            public_blocks.append(b)

    return {
        "type": "doc",
        "blocks": public_blocks,
    }


class PublicEntryDetailSerializer:
    @staticmethod
    def to_representation(entry: Any, version: Any) -> Dict[str, Any]:
        cat_data = None
        if entry.kind == "post" and version.category:
            cat_data = {
                "slug": version.category.slug,
                "name": version.category.name,
            }

        cover_data = None
        if version.cover_image:
            ci = version.cover_image
            cover_data = {
                "alt": ci.alt,
                "width": ci.width,
                "height": ci.height,
                "urls": _image_urls(ci),
            }

        published_at_dt = entry.first_published_at or version.published_at
        updated_at_dt = version.published_at

        return {
            "kind": entry.kind,
            "slug": entry.slug,
            "title": version.title,
            "seo_title": version.seo_title or "",
            "description": version.description or "",
            "excerpt": version.excerpt or "",
            "category": cat_data,
            "cover_image": cover_data,
            "body": public_body(version),
            "published_at": published_at_dt.isoformat() if published_at_dt else "",
            "updated_at": updated_at_dt.isoformat() if updated_at_dt else "",
            "version": version.version,
            "effective_from": updated_at_dt.isoformat() if updated_at_dt else "",
            "author": "Cá Về",
        }


class PublicEntryListSerializer:
    @staticmethod
    def to_representation(entry: Any, version: Any) -> Dict[str, Any]:
        cat_data = None
        if entry.kind == "post" and version.category:
            cat_data = {
                "slug": version.category.slug,
                "name": version.category.name,
            }

        cover_data = None
        if version.cover_image:
            ci = version.cover_image
            cover_data = {
                "alt": ci.alt,
                "width": ci.width,
                "height": ci.height,
                "urls": _image_urls(ci),
            }

        published_at_dt = entry.first_published_at or version.published_at

        return {
            "slug": entry.slug,
            "title": version.title,
            "excerpt": version.excerpt or "",
            "category": cat_data,
            "cover_image": cover_data,
            "published_at": published_at_dt.isoformat() if published_at_dt else "",
        }


class PublicCategorySerializer:
    @staticmethod
    def to_representation(category: Any) -> Dict[str, Any]:
        return {
            "slug": category.slug,
            "name": category.name,
            "description": category.description or "",
        }
