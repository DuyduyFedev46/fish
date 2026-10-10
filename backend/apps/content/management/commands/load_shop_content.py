"""
Lệnh nạp nội dung Shop vào CMS (SHOP-1-07; 02b §3.7.6; decisions 2026-10-10 "Nạp nội dung CMS").

    manage.py load_shop_content --author <username> [--publish] [--overwrite] [--environment production] [--source <thư mục>]

- Mặc định nạp ở trạng thái **Nháp** (production). `--publish` đăng luôn (chỉ nhận khi `SEPAY_ENV != "PRODUCTION"`, staging);
  bài Góc bếp được gắn ảnh bìa tạm có nhãn "Ảnh minh hoạ" để đủ điều kiện đăng (BR-ND-03).
- `SEPAY_ENV == "PRODUCTION"` thì phải có `--environment production`, không thì từ chối (AC6).
- Idempotent theo slug và `page_role`: trang/bài đã có mà người khác sửa (updated_by khác tác giả lệnh) hoặc nháp khác bản lệnh
  đã nạp lần trước -> in "bỏ qua: đã sửa", trừ khi có `--overwrite` (AC3). Bản đã nạp ghi vào AuditLog `content_load` (mã nội dung + hash).
- Mọi ghi đi qua `entries.services` (save_draft, publish_entry), `categories.services`, `images.services` — không ghi thẳng model.
- Chặn SĐT ngoài danh sách được phép (hotline/SĐT người bán trong settings được phép) và cụm khẳng định chưa có nguồn (AC4, AC5).
  Không in lại số điện thoại ra màn hình (bất biến 9).
"""
import io
import json
import os
import re
import shutil
import unicodedata
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.content.body.sanitize import normalize_body
from apps.content.body.scan import PHONE_RE, get_phone_allowlist, normalize_phone_digits, scan_entry_warnings
from apps.content.body.slug import normalize_name_key
from apps.content.categories.services import create_category
from apps.content.entries.services import calculate_content_hash, missing_fields, publish_entry, save_draft
from apps.content.images.services import upload_content_image
from apps.content.management.content_markup import lines_to_blocks
from apps.content.models.categories import Category
from apps.content.models.entries import Entry

DEFAULT_SOURCE = Path(__file__).resolve().parents[1] / "shop_content"
LOAD_ACTION = "content_load"
# "Phí giao": Shop không có dòng phí giao (BR-BH-30, UI-RULES §2.3, QA lô 1 B1).
DEFAULT_BLOCKED_CLAIMS = ("miễn phí giao", "Phí giao", "hút chân không", "cấp đông ngay tại cảng", "Cân đúng", "tươi sống")
PLACEHOLDER_ALT_PREFIX = "Ảnh minh hoạ"
# Màu ảnh tạm theo token DESIGN.md: accent-soft (nền) và surface-3 (dải dưới).
PLACEHOLDER_BACKGROUND = (0xEB, 0xF2, 0xFE)
PLACEHOLDER_BAND = (0xEB, 0xEB, 0xEF)


class EntrySkipped(Exception):
    """Trang/bài bị bỏ qua có chủ đích (không phải lỗi)."""


def _nfc_lower(text: str) -> str:
    return unicodedata.normalize("NFC", str(text or "")).lower()


def _format_kg(value) -> str:
    """Decimal('0.5') -> '0,5'; Decimal('1') -> '1' (số kiểu Việt Nam)."""
    number = Decimal(str(value)).normalize()
    text = format(number, "f")
    return text.replace(".", ",")


class Command(BaseCommand):
    help = "Nạp nội dung Shop (trang, chuyên mục, bài Góc bếp) vào CMS. Mặc định Nháp; --publish để đăng (staging)."

    def add_arguments(self, parser):
        parser.add_argument("--author", required=True, help="Tên đăng nhập người tạo (cần quyền content.publish_entry).")
        parser.add_argument("--publish", action="store_true", help="Đăng luôn (chỉ staging, SEPAY_ENV khác PRODUCTION).")
        parser.add_argument("--overwrite", action="store_true", help="Ghi đè cả trang đã có người sửa tay.")
        parser.add_argument("--environment", default="", help="Bắt buộc 'production' khi SEPAY_ENV=PRODUCTION.")
        parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Thư mục chứa categories.json, pages.json, posts.json.")

    # ------------------------------------------------------------------ chuẩn bị
    def handle(self, *args, **options):
        sepay_env = str(getattr(settings, "SEPAY_ENV", "")).strip().upper()
        environment = str(options["environment"] or "").strip().lower()
        self.publish = bool(options["publish"])
        self.overwrite = bool(options["overwrite"])
        if sepay_env == "PRODUCTION" and environment != "production":
            raise CommandError(
                "Đang trỏ vào môi trường PRODUCTION. Chạy lại với --environment production để xác nhận (SHOP-1-07 AC6)."
            )
        if self.publish and (sepay_env == "PRODUCTION" or environment == "production"):
            raise CommandError("Môi trường thật chỉ nạp Nháp; Duy/Lộc duyệt rồi bấm Đăng ở ERP. Bỏ cờ --publish.")

        user_model = get_user_model()
        try:
            self.author = user_model.objects.get(username=options["author"])
        except user_model.DoesNotExist as exc:
            raise CommandError("Không có tài khoản tác giả này.") from exc
        if not self.author.has_perm("content.publish_entry"):
            raise CommandError("Tài khoản tác giả cần quyền content.publish_entry (nhóm Chủ hoặc Quản lý).")

        source = Path(options["source"])
        try:
            categories = self._read(source / "categories.json")["categories"]
            pages = self._read(source / "pages.json")["pages"]
            posts = self._read(source / "posts.json")["posts"]
        except (OSError, ValueError, KeyError) as exc:
            raise CommandError(f"Không đọc được file nguồn: {exc}") from exc

        self.variables = self._variables()
        self.allowed_phones = self._allowed_phones()
        self.blocked_claims = [
            _nfc_lower(c) for c in getattr(settings, "CONTENT_BLOCKED_CLAIMS", DEFAULT_BLOCKED_CLAIMS) if str(c).strip()
        ]
        self.counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0, "published": 0}
        self.errors: list[str] = []

        category_ids = self._load_categories(categories)
        for spec in pages:
            self._process(spec, kind="page", category_ids=category_ids)
        for spec in posts:
            self._process(spec, kind="post", category_ids=category_ids)

        c = self.counts
        self.stdout.write(
            f"Tổng: tạo {c['created']}, cập nhật {c['updated']}, không đổi {c['unchanged']}, "
            f"bỏ qua {c['skipped']}, đăng {c['published']}, lỗi {len(self.errors)}."
        )
        if self.errors:
            raise CommandError(f"Có {len(self.errors)} trang/bài không nạp được: " + "; ".join(self.errors))

    @staticmethod
    def _read(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _variables(self) -> dict:
        hotline = str(getattr(settings, "SHOP_HOTLINE", "") or "").strip()
        if len(re.sub(r"\D", "", hotline)) < 8:
            hotline = "[hotline]"  # chưa cấu hình số thật -> giữ chỗ chờ (AC7, AC8)
        return {
            "{hotline}": hotline,
            "{hold_minutes}": str(settings.SALES_ORDER_TTL_MINUTES),
            "{min_qty_kg}": _format_kg(getattr(settings, "SHOP_MIN_QTY_KG", Decimal("1"))),
            "{qty_step_kg}": _format_kg(getattr(settings, "SHOP_QTY_STEP_KG", Decimal("0.5"))),
            "{cancel_callback_within}": str(getattr(settings, "SHOP_CANCEL_CALLBACK_WITHIN", "1 ngày làm việc")),
        }

    def _allowed_phones(self) -> set[str]:
        # get_phone_allowlist đã gồm SHOP_HOTLINE và SELLER_PHONE (SHOP-5-01 AC5).
        return set(get_phone_allowlist())

    def _fill(self, text) -> str:
        text = str(text or "")
        for key, value in self.variables.items():
            text = text.replace(key, value)
        return text

    # ------------------------------------------------------------------ chuyên mục
    def _load_categories(self, categories: list[dict]) -> dict:
        ids = {}
        for spec in categories:
            name = str(spec["name"]).strip()
            existing = Category.objects.filter(name_key=normalize_name_key(name)).first()
            if existing is None:
                existing = create_category(
                    name=name, description=spec.get("description", ""), order=spec.get("order", 0)
                )
                self.stdout.write(f"tạo chuyên mục: {existing.slug}")
            else:
                self.stdout.write(f"chuyên mục đã có: {existing.slug}")
            ids[normalize_name_key(name)] = existing.pk
        return ids

    # ------------------------------------------------------------------ trang / bài
    def _process(self, spec: dict, *, kind: str, category_ids: dict):
        slug = str(spec.get("slug") or "").strip()
        self.pending_uploads: list[str] = []
        try:
            with transaction.atomic():
                result = self._process_one(spec, kind=kind, slug=slug, category_ids=category_ids)
            self.stdout.write(f"{result}: {slug}")
        except EntrySkipped as exc:
            self.counts["skipped"] += 1
            self.stdout.write(f"bỏ qua: {exc}: {slug}")
        except (BusinessError, ValueError) as exc:
            message = f"{slug}: {exc}{self._discard_uploads()}"
            self.errors.append(message)
            self.stderr.write(f"lỗi: {message}")
        except Exception:
            self._discard_uploads()
            raise

    def _discard_uploads(self) -> str:
        """DB đã rollback: dọn tệp ảnh tạm vừa tải của trang/bài lỗi (review lô 1, L6).

        Kho `local` (dev/test): xoá thư mục ảnh. Kho `gcs`: tài khoản dịch vụ không có quyền xoá (BR-DM-14),
        nên chỉ báo lại để người vận hành biết; tệp mồ côi không được bản ghi nào trỏ tới.
        """
        paths, self.pending_uploads = self.pending_uploads, []
        if not paths:
            return ""
        backend = str(getattr(settings, "ITEM_IMAGE_STORAGE", "local")).strip().lower()
        media_root = str(getattr(settings, "MEDIA_ROOT", "") or "")
        if backend != "local" or not media_root:
            return " (ảnh tạm đã tải lên kho chưa xoá được vì kho không cho xoá, BR-DM-14)"
        for prefix in paths:
            shutil.rmtree(os.path.join(media_root, prefix), ignore_errors=True)
        return ""

    def _build_data(self, spec: dict, *, kind: str, category_ids: dict) -> dict:
        title = self._fill(spec["title"])
        texts = [
            title,
            self._fill(spec.get("excerpt", "")),
            self._fill(spec.get("seo_title", "")),
            self._fill(spec.get("seo_description", "")),
        ]
        lines = [self._fill(line) for line in spec.get("body", [])]
        self._check_texts(texts + lines)

        blocks = []
        for block in lines_to_blocks(lines):
            if block["type"] == "item_card" and not self._item_available(block["item_code"]):
                continue  # chỉ chèn thẻ hàng có thật, đang bán, có giá (cms-cho-mkt §9)
            blocks.append(block)

        data = {
            "kind": kind,
            "slug": spec["slug"],
            "title": title,
            "excerpt": texts[1],
            "seo_title": texts[2],
            "seo_description": texts[3],
            "body": {"type": "doc", "blocks": blocks},
        }
        if kind == "post":
            category_id = category_ids.get(normalize_name_key(spec.get("category", "")))
            if category_id is None:
                raise ValueError("chuyên mục không có trong categories.json")
            data["category"] = category_id
        else:
            data["category"] = None
            data["page_role"] = spec.get("page_role") or None
            data["show_in_footer"] = bool(spec.get("show_in_footer", False))
            data["footer_order"] = int(spec.get("footer_order", 0))
        return data

    def _check_texts(self, texts: list[str]):
        for text in texts:
            for match in PHONE_RE.finditer(text):
                if normalize_phone_digits(match.group(0)) not in self.allowed_phones:
                    raise ValueError(
                        "có số điện thoại không thuộc danh sách được phép (CONTENT_PHONE_ALLOWLIST, SHOP_HOTLINE)"
                    )
            lowered = _nfc_lower(text)
            for claim in self.blocked_claims:
                if claim in lowered:
                    raise ValueError(f"có cụm khẳng định chưa có nguồn \"{claim}\" (S-18, BR-ND-21)")

    @staticmethod
    def _item_available(code: str) -> bool:
        from apps.catalog.models import Item
        from apps.catalog.pricing.services import effective_price

        item = Item.objects.filter(code=code, is_active=True).first()
        return item is not None and effective_price(item) is not None

    def _find_existing(self, data: dict):
        entry = Entry.objects.filter(slug=data["slug"]).first()
        role = data.get("page_role")
        if role:
            holder = Entry.objects.filter(page_role=role).first()
            if holder is not None and (entry is None or holder.pk != entry.pk):
                raise EntrySkipped(f"vai trò {role} đã có trang khác giữ")
        return entry

    @staticmethod
    def _last_loaded_hash(entry: Entry):
        from apps.accounts.models import AuditLog

        log = (
            AuditLog.objects.filter(action=LOAD_ACTION, model_name=Entry._meta.label, object_id=str(entry.pk))
            .order_by("-id")
            .first()
        )
        return (log.changes or {}).get("draft_hash") if log else None

    def _desired_hash(self, entry: Entry, data: dict) -> str:
        body = normalize_body(data["body"], entry=entry, cover_image_id=entry.cover_image_id)
        return calculate_content_hash(
            kind=data["kind"],
            title=data["title"],
            slug=entry.slug,
            excerpt=data["excerpt"][:500],
            seo_title=data["seo_title"][:200],
            seo_description=data["seo_description"][:300],
            category_id=data["category"],
            cover_image_id=entry.cover_image_id,
            body=body,
        )

    def _process_one(self, spec: dict, *, kind: str, slug: str, category_ids: dict) -> str:
        data = self._build_data(spec, kind=kind, category_ids=category_ids)
        entry = self._find_existing(data)
        result = "không đổi"

        if entry is None:
            entry = save_draft(data=data, actor=self.author)
            result = "tạo mới"
            self.counts["created"] += 1
        else:
            last_hash = self._last_loaded_hash(entry)
            edited = (
                last_hash is None
                or entry.updated_by_id != self.author.pk
                or entry.draft_hash != last_hash
            )
            if edited and not self.overwrite:
                role = data.get("page_role") if kind == "page" else None
                if role and entry.page_role is None:
                    # SHOP-5-02 (BR-ND-20): trang bắt buộc đã nạp từ trước và đã được sửa tay -> chỉ gắn vai trò,
                    # giữ nguyên nội dung Lộc sửa. Không ghi AuditLog content_load để lần sau vẫn nhận ra "đã sửa".
                    save_draft(entry=entry, data={"page_role": role}, actor=self.author)
                    self.counts["skipped"] += 1
                    return f"bỏ qua: đã sửa; gắn vai trò {role}, nội dung giữ nguyên"
                raise EntrySkipped("đã sửa")
            flags_same = kind == "post" or (
                entry.page_role == data["page_role"]
                and entry.show_in_footer == data["show_in_footer"]
                and entry.footer_order == data["footer_order"]
            )
            if not (flags_same and entry.kind == kind and self._desired_hash(entry, data) == entry.draft_hash):
                payload = {k: v for k, v in data.items() if k != "slug"}
                entry = save_draft(entry=entry, data=payload, actor=self.author)
                result = "cập nhật"
                self.counts["updated"] += 1

        if self.publish and kind == "post" and entry.cover_image_id is None:
            # Kiểm đủ điều kiện đăng TRƯỚC khi tải ảnh, để lỗi đăng không để lại tệp ảnh mồ côi (L6).
            entry.refresh_from_db()
            self._assert_publishable(entry, ignore_cover=True)
            entry = self._attach_placeholder_cover(entry)
            if result == "không đổi":
                result = "cập nhật"
                self.counts["updated"] += 1

        if result != "không đổi" or self._last_loaded_hash(entry) != entry.draft_hash:
            record_audit(
                LOAD_ACTION,
                actor=self.author,
                obj=entry,
                changes={"entry_id": entry.pk, "draft_hash": entry.draft_hash},
                note="Lệnh nạp nội dung Shop",
            )

        if self.publish:
            entry.refresh_from_db()
            already = (
                entry.status == "published"
                and entry.published_version is not None
                and entry.published_version.content_hash == entry.draft_hash
            )
            if not already:
                self._publish(entry)
                result = f"{result}, đã đăng"
        elif result == "không đổi":
            self.counts["unchanged"] += 1
        if result == "không đổi" and self.publish:
            self.counts["unchanged"] += 1
        return result

    @staticmethod
    def _assert_publishable(entry: Entry, *, ignore_cover: bool = False) -> list:
        """Thiếu trường (BR-ND-03) hoặc có cảnh báo khác SĐT (giá vốn, món không bán) -> dừng trang/bài này."""
        ignored = {"cover_image", "cover_image_alt"} if ignore_cover else set()
        missing = [field for field in missing_fields(entry) if field not in ignored]
        if missing:
            raise ValueError("chưa đủ điều kiện đăng, thiếu: " + ", ".join(missing))
        warnings = scan_entry_warnings(entry)
        # SĐT đã kiểm trước khi lưu (chỉ còn số được phép); mọi cảnh báo loại khác phải dừng.
        others = sorted({w["type"] for w in warnings if w.get("type") != "phone_like"})
        if others:
            raise ValueError("có cảnh báo trước khi đăng: " + ", ".join(others))
        return warnings

    def _publish(self, entry: Entry):
        warnings = self._assert_publishable(entry)
        publish_entry(
            entry=entry,
            actor=self.author,
            row_version=entry.row_version,
            checklist_confirmed=True,
            acknowledge_warnings=bool(warnings),
        )
        self.counts["published"] += 1

    def _attach_placeholder_cover(self, entry: Entry) -> Entry:
        """Ảnh bìa tạm (staging) có nhãn "Ảnh minh hoạ" ở mô tả ảnh, để bài đủ điều kiện đăng (decisions 10/10, UI-RULES §1.6)."""
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (1600, 900), PLACEHOLDER_BACKGROUND)
        ImageDraw.Draw(image).rectangle([0, 780, 1600, 900], fill=PLACEHOLDER_BAND)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        upload = SimpleUploadedFile("placeholder-cover.png", buffer.getvalue(), content_type="image/png")
        alt = f"{PLACEHOLDER_ALT_PREFIX}: {entry.title}"[:200]
        cover = upload_content_image(entry=entry, file=upload, alt=alt, actor=self.author)
        self.pending_uploads.append(f"content/{entry.pk}/{cover.image_id}")
        return save_draft(entry=entry, data={"cover_image": cover.pk}, actor=self.author)
