"""Dịch vụ nghiệp vụ bài viết và trang nội dung (§4 02b-tech-design)."""
import hashlib
import json
from typing import Any
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


def missing_fields(entry: Entry) -> list[str]:
    """
    Kiểm tra các trường còn thiếu để đủ điều kiện đăng bài (§4.3, BR-ND-03).
    Thứ tự: title, slug, body, category, cover_image, cover_image_alt, description.
    """
    missing: list[str] = []

    if not (entry.title and entry.title.strip()):
        missing.append("title")

    if not (entry.slug and entry.slug.strip()):
        missing.append("slug")

    body = entry.body if isinstance(entry.body, dict) else {}
    blocks = body.get("blocks", []) if isinstance(body.get("blocks"), list) else []
    if len(blocks) < 1:
        missing.append("body")

    if entry.kind == "post":
        if entry.category is None or not entry.category.is_active:
            missing.append("category")
        if entry.cover_image is None:
            missing.append("cover_image")
        elif not (entry.cover_image.alt and entry.cover_image.alt.strip()):
            missing.append("cover_image_alt")

    has_desc = bool(
        (entry.seo_description and entry.seo_description.strip())
        or (entry.excerpt and entry.excerpt.strip())
    )
    if not has_desc:
        missing.append("description")

    return missing


def compute_description(entry: Entry) -> str:
    """
    Mô tả công khai (§4.3, CMS-07-AC5): seo_description nếu có;
    ngược lại excerpt cắt <= CONTENT_DESCRIPTION_MAX (160) tại khoảng trắng cuối cùng,
    bỏ dấu câu treo, không thêm '…' nếu không cắt.
    """
    max_len = getattr(settings, "CONTENT_DESCRIPTION_MAX", 160)
    if entry.seo_description and entry.seo_description.strip():
        return entry.seo_description.strip()[:max_len]

    excerpt = (entry.excerpt or "").strip()
    if len(excerpt) <= max_len:
        return excerpt

    # Cắt tại khoảng trắng cuối cùng <= max_len
    truncated = excerpt[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]

    # Bỏ dấu câu treo ở cuối (. , ; : ! ? -)
    truncated = truncated.rstrip(".,;:!?- ")
    return truncated


def publish_entry(
    *,
    entry: Entry,
    actor,
    row_version: int,
    checklist_confirmed: bool = False,
    acknowledge_warnings: bool = False,
) -> dict:
    """
    Đăng bài viết hoặc trang (§4.5, CMS-07, CMS-08).
    - Kiểm tra row_version
    - Kiểm tra có thay đổi nếu đang published
    - Kiểm tra đủ điều kiện missing_fields (BR-ND-03)
    - Kiểm tra checklist_confirmed (BR-ND-13)
    - Quét cảnh báo an toàn qua scan_entry_warnings (CMS-08)
    - Tạo EntryVersion append-only
    - Cập nhật Entry status="published", row_version += 1, slug_locked=True
    - Ghi AuditLog đúng 1 dòng
    - Trả kết quả publish
    """
    from apps.common.audit import record_audit
    from apps.content.body.scan import scan_entry_warnings
    from apps.content.models.entries import EntryVersion

    with transaction.atomic():
        entry = Entry.objects.select_for_update().get(pk=entry.pk)

        # 1. Kiểm tra row_version (CMS-07-AC6)
        if row_version != entry.row_version:
            raise BusinessError(
                "Bài viết đã được chỉnh sửa bởi người khác (STALE_VERSION).",
                code="STALE_VERSION",
                status_code=409,
            )

        # 2. Không có thay đổi để đăng (CMS-10-AC4)
        if (
            entry.status == "published"
            and entry.published_version
            and entry.draft_hash == entry.published_version.content_hash
        ):
            raise BusinessError("Không có thay đổi để đăng (BR-ND-05).", code="BR-ND-05")

        # 3. Thiếu điều kiện đăng (CMS-07-AC3, BR-ND-03)
        missing = missing_fields(entry)
        if missing:
            raise BusinessError(
                "Bài viết chưa đủ điều kiện xuất bản (BR-ND-03).",
                code="BR-ND-03",
                extra={"missing": missing},
            )

        # 4. Chưa xác nhận checklist tự kiểm (CMS-07-AC4, BR-ND-13)
        if checklist_confirmed is not True:
            raise BusinessError(
                "Chưa xác nhận danh sách tự kiểm trước khi đăng (BR-ND-13).",
                code="BR-ND-13",
            )

        # 5. Cảnh báo an toàn (CMS-08-AC1, AC2)
        warnings = scan_entry_warnings(entry)
        if warnings and acknowledge_warnings is not True:
            raise BusinessError(
                "Phát hiện cảnh báo trước khi xuất bản (CONTENT_WARNINGS).",
                code="CONTENT_WARNINGS",
                status_code=409,
                extra={"warnings": warnings},
            )

        # 6. Tạo phiên bản EntryVersion
        now = timezone.now()
        new_version_num = (entry.published_version.version if entry.published_version else 0) + 1
        description = compute_description(entry)

        version = EntryVersion.objects.create(
            entry=entry,
            version=new_version_num,
            kind=entry.kind,
            title=entry.title,
            slug=entry.slug,
            excerpt=entry.excerpt,
            seo_title=entry.seo_title,
            seo_description=entry.seo_description,
            description=description,
            category=entry.category,
            cover_image=entry.cover_image,
            body=entry.body,
            content_hash=entry.draft_hash,
            restored_from=entry.restored_from,
            published_at=now,
            published_by=actor,
        )

        # 7. Cập nhật Entry
        is_first = entry.first_published_at is None
        entry.status = "published"
        entry.published_version = version
        if is_first:
            entry.first_published_at = now
        entry.last_published_at = now
        restored_from_val = entry.restored_from
        entry.restored_from = None
        entry.return_reason = ""
        entry.row_version += 1
        entry.updated_by = actor
        entry.save(update_fields=[
            "status",
            "published_version",
            "first_published_at",
            "last_published_at",
            "restored_from",
            "return_reason",
            "row_version",
            "updated_by",
            "updated_at",
        ])

        # 8. Ghi AuditLog (CMS-07-AC2, CMS-08-AC5)
        if is_first:
            action = "content_publish"
        elif restored_from_val is not None:
            action = "content_restore_version"
        else:
            action = "content_republish"

        changes = {
            "entry_id": entry.id,
            "version": version.version,
            "kind": entry.kind,
        }
        if restored_from_val is not None:
            changes["restored_from"] = restored_from_val
        if warnings and acknowledge_warnings:
            warning_types = sorted(list({w["type"] for w in warnings}))
            changes["warnings_acknowledged"] = warning_types

        record_audit(
            action=action,
            actor=actor,
            obj=entry,
            changes=changes,
            object_repr=f"Nội dung #{entry.id}",
            note="",
        )

        public_path = f"/bai-viet/?slug={entry.slug}" if entry.kind == "post" else f"/trang/?slug={entry.slug}"
        shop_base = getattr(settings, "SHOP_BASE_URL", "http://localhost:3000").rstrip("/")
        return {
            "status": "published",
            "version": version.version,
            "published_at": version.published_at.isoformat(),
            "public_path": public_path,
            "public_url": f"{shop_base}{public_path}",
        }


UNPUBLISH_REASONS = {"wrong_price", "complaint", "out_of_season", "wrong_content", "other"}


def unpublish_entry(*, entry: Entry, actor: Any, row_version: int, reason: str) -> dict[str, Any]:
    """
    Gỡ bài viết hoặc trang khỏi website công khai (CMS-12, §4.6 02b-tech-design).
    - Chỉ cho phép gỡ từ trạng thái 'published'.
    - Lý do bắt buộc thuộc UNPUBLISH_REASONS.
    - Không cho gỡ trực tiếp trang đang giữ page_role go-live (BR-ND-16).
    - Ghi đúng 1 dòng AuditLog action 'content_unpublish'.
    """
    from apps.common.audit import record_audit

    with transaction.atomic():
        entry = Entry.objects.select_for_update().get(pk=entry.pk)

        # 1. Kiểm tra row_version
        if row_version != entry.row_version:
            raise BusinessError(
                "Bài viết đã được chỉnh sửa bởi người khác (STALE_VERSION).",
                code="STALE_VERSION",
                status_code=409,
            )

        # 2. Kiểm tra trạng thái hiện tại (CMS-12-AC7)
        if entry.status != "published":
            raise BusinessError(
                "Chỉ có thể gỡ bài viết đang ở trạng thái đã đăng (BR-ND-01).",
                code="BR-ND-01",
            )

        # 3. Kiểm tra lý do gỡ (CMS-12-AC1)
        clean_reason = str(reason or "").strip()
        if clean_reason not in UNPUBLISH_REASONS:
            raise BusinessError(
                "Lý do gỡ bài không hợp lệ (BR-ND-15).",
                code="BR-ND-15",
            )

        # 4. Kiểm tra trang giữ vai trò go-live (CMS-15, BR-ND-16)
        if entry.page_role is not None:
            raise BusinessError(
                "Không thể gỡ trực tiếp trang nội dung đang giữ vai trò go-live (BR-ND-16).",
                code="BR-ND-16",
            )

        ver_num = entry.published_version.version if entry.published_version else 1
        entry.status = "unpublished"
        entry.return_reason = clean_reason
        entry.row_version += 1
        entry.updated_by = actor
        entry.save(update_fields=[
            "status",
            "return_reason",
            "row_version",
            "updated_by",
            "updated_at",
        ])

        # Ghi AuditLog
        record_audit(
            action="content_unpublish",
            actor=actor,
            obj=entry,
            changes={
                "entry_id": entry.id,
                "version": ver_num,
                "reason": clean_reason,
            },
            object_repr=f"Nội dung #{entry.id}",
            note="",
        )

        return {
            "status": "unpublished",
            "row_version": entry.row_version,
        }


def discard_changes(*, entry: Entry, actor: Any, row_version: int) -> dict[str, Any]:
    """
    Huỷ các thay đổi nháp đang soạn, khôi phục lại nội dung bản đã đăng (CMS-10-AC3, §4.6).
    - Yêu cầu bài đã từng được xuất bản (published_version is not None).
    - Nạp lại mọi trường nội dung từ published_version.
    - Không ghi AuditLog.
    """
    with transaction.atomic():
        entry = Entry.objects.select_for_update().get(pk=entry.pk)

        # 1. Kiểm tra row_version
        if row_version != entry.row_version:
            raise BusinessError(
                "Bài viết đã được chỉnh sửa bởi người khác (STALE_VERSION).",
                code="STALE_VERSION",
                status_code=409,
            )

        # 2. Kiểm tra có bản published không
        if entry.published_version is None:
            raise BusinessError(
                "Bài viết chưa từng được đăng, không thể huỷ thay đổi (BR-ND-02).",
                code="BR-ND-02",
            )

        ver = entry.published_version
        entry.title = ver.title
        entry.slug = ver.slug
        entry.excerpt = ver.excerpt
        entry.seo_title = ver.seo_title
        entry.seo_description = ver.seo_description
        entry.category = ver.category
        entry.cover_image = ver.cover_image
        entry.body = ver.body
        entry.restored_from = None
        entry.draft_hash = ver.content_hash
        entry.row_version += 1
        entry.updated_by = actor
        entry.save(update_fields=[
            "title",
            "slug",
            "excerpt",
            "seo_title",
            "seo_description",
            "category",
            "cover_image",
            "body",
            "restored_from",
            "draft_hash",
            "row_version",
            "updated_by",
            "updated_at",
        ])

        return entry



