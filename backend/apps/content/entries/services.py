"""Dịch vụ nghiệp vụ bài viết và trang nội dung (§4 02b-tech-design)."""
import hashlib
import json
import uuid
from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone
from apps.common.exceptions import BusinessError
from apps.content.body.slug import slugify_vi, suggest_unique_slug
from apps.content.body.sanitize import normalize_body
from apps.content.models.entries import Entry
from apps.content.models.images import ContentImage


PROTECTED_FIELDS = {
    "status",
    "published_version",
    "first_published_at",
    "last_published_at",
    "source",
    "created_by",
    "created_at",
}


def calculate_content_hash(
    *,
    kind: str,
    title: str,
    slug: str,
    excerpt: str,
    seo_title: str,
    seo_description: str,
    category_id: int | None,
    cover_image_id: int | None,
    body: dict,
) -> str:
    """Tính sha256 JSON chuẩn của nội dung (§4.4 02b-tech-design)."""
    payload = {
        "body": body,
        "category_id": category_id,
        "cover_image_id": cover_image_id,
        "excerpt": excerpt or "",
        "kind": kind,
        "seo_description": seo_description or "",
        "seo_title": seo_title or "",
        "slug": slug,
        "title": title or "",
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def save_draft(*, entry: Entry | None = None, data: dict, actor) -> Entry:
    """
    Lưu nháp bài viết / trang nội dung (§4.2 02b-tech-design).
    - Tạo mới hoặc cập nhật bản đang soạn
    - Khoá lạc quan row_version (409 STALE_VERSION)
    - Chuẩn hoá slug (gợi ý suggestion khi trùng)
    - Chuẩn hoá thân bài qua normalize_body (BR-ND-06, BR-ND-07)
    - Không ghi AuditLog cho lưu nháp (CMS-03-AC10)
    """
    # 1. Chặn các trường hệ thống không được sửa trực tiếp
    for field in PROTECTED_FIELDS:
        if field in data:
            raise BusinessError(f"Không được sửa trường hệ thống '{field}' (BR-PQ-14).", code="BR-PQ-14")

    # 2. Kiểm tra quyền sửa field trang chính sách (CMS-15-AC8)
    policy_fields = {"page_role", "show_in_footer", "footer_order"}
    if any(k in data for k in policy_fields):
        if not actor.has_perm("content.publish_entry"):
            raise BusinessError(
                "Bạn không có quyền sửa thuộc tính trang chính sách (BR-PQ-12).",
                code="BR-PQ-12",
                status_code=403,
            )

    title_max = getattr(settings, "CONTENT_TITLE_MAX", 200)
    title = data.get("title")
    if title is not None:
        title = str(title)
        if len(title) > title_max:
            raise BusinessError(f"Tiêu đề không được vượt quá {title_max} ký tự (BR-ND-01).", code="BR-ND-01")

    with transaction.atomic():
        if entry is not None:
            # Cập nhật: select_for_update và kiểm tra row_version
            entry = Entry.objects.select_for_update().get(pk=entry.pk)
            req_version = data.get("row_version")
            if req_version is not None:
                try:
                    req_version = int(req_version)
                except (ValueError, TypeError):
                    pass
            if req_version is not None and req_version != entry.row_version:
                raise BusinessError(
                    "Bài viết đã được chỉnh sửa bởi người khác (STALE_VERSION).",
                    code="STALE_VERSION",
                    status_code=409,
                )



        # Xử lý slug
        if entry is None:
            # Tạo mới
            raw_slug = data.get("slug")
            if raw_slug is not None and str(raw_slug).strip():
                slug = slugify_vi(str(raw_slug).strip())
                if not slug:
                    raise BusinessError("Đường dẫn (slug) không hợp lệ (BR-ND-04).", code="BR-ND-04")
            elif title and title.strip():
                slug = slugify_vi(title.strip())
            else:
                slug = f"bai-{uuid.uuid4().hex[:6]}"

            if Entry.objects.filter(slug=slug).exists():
                suggestion = suggest_unique_slug(slug)
                raise BusinessError(
                    "Đường dẫn bài viết đã tồn tại (BR-ND-04).",
                    code="BR-ND-04",
                    extra={"suggestion": suggestion},
                )
        else:
            # Sửa
            if "slug" in data:
                raw_slug = data.get("slug")
                if raw_slug is None or not str(raw_slug).strip():
                    raise BusinessError("Đường dẫn (slug) không hợp lệ (BR-ND-04).", code="BR-ND-04")
                slug = slugify_vi(str(raw_slug).strip())
                if not slug:
                    raise BusinessError("Đường dẫn (slug) không hợp lệ (BR-ND-04).", code="BR-ND-04")

                # Không cho đổi slug nếu đã từng đăng (CMS-07-AC7)
                if entry.first_published_at is not None and slug != entry.slug:
                    raise BusinessError("Không thể đổi đường dẫn bài đã đăng (BR-ND-04).", code="BR-ND-04")

                if slug != entry.slug and Entry.objects.filter(slug=slug).exclude(pk=entry.pk).exists():
                    suggestion = suggest_unique_slug(slug, exclude_id=entry.pk)
                    raise BusinessError(
                        "Đường dẫn bài viết đã tồn tại (BR-ND-04).",
                        code="BR-ND-04",
                        extra={"suggestion": suggestion},
                    )
            else:
                slug = entry.slug

        # Cover image
        cover_image = entry.cover_image if entry else None
        if "cover_image" in data:
            cov_id = data.get("cover_image")
            if cov_id:
                # Kiểm tra ảnh thuộc cùng bài
                if entry and not ContentImage.objects.filter(pk=cov_id, entry=entry).exists():
                    raise BusinessError("Ảnh bìa không thuộc bài viết này (BR-ND-07).", code="BR-ND-07")
                try:
                    cover_image = ContentImage.objects.get(pk=cov_id)
                except ContentImage.DoesNotExist:
                    raise BusinessError("Ảnh bìa không tồn tại (BR-ND-07).", code="BR-ND-07")
            else:
                cover_image = None

        # Body
        cov_id_val = cover_image.pk if cover_image else None
        if "body" in data:
            body = normalize_body(data["body"], entry=entry, cover_image_id=cov_id_val)
        else:
            body = entry.body if entry else {"type": "doc", "blocks": []}

        # Category
        category_id = entry.category_id if entry else None
        if "category" in data:
            category_id = data.get("category")

        # Excerpt & SEO
        excerpt = str(data.get("excerpt", entry.excerpt if entry else ""))[:500]
        seo_title = str(data.get("seo_title", entry.seo_title if entry else ""))[:200]
        seo_description = str(data.get("seo_description", entry.seo_description if entry else ""))[:300]
        kind = data.get("kind", entry.kind if entry else "post")
        if kind not in ("post", "page"):
            kind = "post"

        if entry and entry.first_published_at is not None and "kind" in data and data["kind"] != entry.kind:
            raise BusinessError("Không thể đổi loại nội dung đã từng đăng (BR-ND-01).", code="BR-ND-01")

        draft_hash = calculate_content_hash(
            kind=kind,
            title=title if title is not None else (entry.title if entry else ""),
            slug=slug,
            excerpt=excerpt,
            seo_title=seo_title,
            seo_description=seo_description,
            category_id=category_id,
            cover_image_id=cov_id_val,
            body=body,
        )

        page_role = data.get("page_role", entry.page_role if entry else None)
        show_in_footer = bool(data.get("show_in_footer", entry.show_in_footer if entry else False))
        footer_order = int(data.get("footer_order", entry.footer_order if entry else 0))

        if page_role:
            # Kiểm tra page_role trùng với trang khác
            qs_role = Entry.objects.filter(page_role=page_role)
            if entry:
                qs_role = qs_role.exclude(pk=entry.pk)
            if qs_role.exists():
                raise BusinessError("Vai trò trang chính sách này đã được sử dụng (BR-ND-16).", code="BR-ND-16")

        try:
            if entry is None:
                entry = Entry.objects.create(
                    kind=kind,
                    title=title or "",
                    slug=slug,
                    category_id=category_id,
                    excerpt=excerpt,
                    seo_title=seo_title,
                    seo_description=seo_description,
                    cover_image=cover_image,
                    body=body,
                    draft_hash=draft_hash,
                    page_role=page_role,
                    show_in_footer=show_in_footer,
                    footer_order=footer_order,
                    source="human",
                    row_version=1,
                    created_by=actor,
                    updated_by=actor,
                )
            else:
                if title is not None:
                    entry.title = title
                entry.slug = slug
                entry.category_id = category_id
                entry.excerpt = excerpt
                entry.seo_title = seo_title
                entry.seo_description = seo_description
                entry.cover_image = cover_image
                entry.body = body
                entry.draft_hash = draft_hash
                if "page_role" in data:
                    entry.page_role = page_role
                if "show_in_footer" in data:
                    entry.show_in_footer = show_in_footer
                if "footer_order" in data:
                    entry.footer_order = footer_order
                entry.row_version += 1
                entry.updated_by = actor
                entry.save()
        except IntegrityError as exc:
            if "slug" in str(exc).lower():
                suggestion = suggest_unique_slug(slug, exclude_id=entry.pk if entry else None)
                raise BusinessError(
                    "Đường dẫn bài viết đã tồn tại (BR-ND-04).",
                    code="BR-ND-04",
                    extra={"suggestion": suggestion},
                ) from exc
            raise

    return entry


def delete_draft(*, entry: Entry, actor) -> None:
    """
    Xoá nháp chưa từng đăng (CMS-03-AC8, BR-ND-02).
    - Bài đã từng đăng (đang published hoặc unpublished) -> 400 BR-ND-02
    - Bài nháp chưa từng đăng -> xoá cứng DB, cascade xoá ContentImage, không ghi AuditLog
    """
    if entry.first_published_at is not None or entry.published_version_id is not None:
        raise BusinessError("Không thể xoá bài viết đã từng đăng (BR-ND-02).", code="BR-ND-02")
    entry.delete()
