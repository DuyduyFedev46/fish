"""
Dịch vụ tải và nhập file Excel mặt hàng (FISH-66 S3, S4, S5, S6; BR-DM-27/28, BR-PQ-04/05).

Chỉ đọc/ghi `Item`, `ItemGroup`, `ItemPrice` — không join `Batch`/`PurchaseReceiptLine`, nên file và kết quả
không bao giờ chứa giá vốn.
"""
import datetime
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models.functions import Lower
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.items.filters import apply_item_filters
from apps.catalog.items.serializers import user_can_view_item_price
from apps.catalog.models import Item, PriceList
from apps.catalog.pricing.services import CURRENT_PRICES_ATTR, prefetch_current_prices, set_item_price
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError, ConflictError

from .columns import PUBLIC_TEXT_KEYS, columns_for
from .plan import TEMPLATE_EXAMPLE_CODE, build_import_plan, normalize_item_code
from .reader import read_import_workbook
from .token import (
    check_preview_token_expiry,
    issue_preview_token,
    verify_preview_token_signature,
)
from .workbook import build_items_workbook

TEMPLATE_FILENAME = "mau-hang-ban.xlsx"

DATA_CHANGED_MSG = "Mặt hàng vừa được sửa sau lúc bạn xem trước. Chưa ghi gì. Bấm Xem trước lại để so với dữ liệu mới."
ALREADY_APPLIED_MSG = "Lượt nhập này đã ghi rồi."
IMPORT_AUDIT_NOTE = "Nhập từ file Excel"


def can_see_prices(user):
    return user_can_view_item_price(user)


def export_filename(now=None):
    """Tên file theo giờ Việt Nam: hang-ban-YYYYMMDD-HHmm.xlsx."""
    return timezone.localtime(now).strftime("hang-ban-%Y%m%d-%H%M.xlsx")


def _item_row(item, *, with_prices):
    row = {
        "code": item.code,
        "name": item.name,
        "item_group": item.item_group.name,
        "item_type": item.get_item_type_display(),
        "stock_uom": item.stock_uom,
        "is_active": item.is_active,
        "shelf_life_in_days": item.shelf_life_in_days,
        "has_batch_no": item.has_batch_no,
        "has_expiry_date": item.has_expiry_date,
        "short_note": item.short_note,
        "spec": item.spec,
        "storage": item.storage,
        "origin": item.origin,
        "description": item.description,
    }
    if with_prices:
        prices = getattr(item, CURRENT_PRICES_ATTR, None) or []
        row["current_price"] = prices[0].rate if prices else None
    return row


def export_items(*, user, params):
    """Trả `(bytes xlsx, số món)`; ghi AuditLog `export_items` chỉ có số đếm (không tên món, không bộ lọc)."""
    with_prices = can_see_prices(user)
    queryset = Item.objects.select_related("item_group").order_by("code")
    queryset = apply_item_filters(queryset, params)  # sai bộ lọc → BusinessError INVALID_FILTER, chưa ghi nhật ký
    if with_prices:
        queryset = queryset.prefetch_related(prefetch_current_prices())
    rows = [_item_row(item, with_prices=with_prices) for item in queryset]
    content = build_items_workbook(columns_for(with_prices=with_prices), rows)
    record_audit("export_items", actor=user, changes={"rows": len(rows), "with_prices": with_prices})
    return content, len(rows)


def export_template(*, user):
    """File mẫu: cùng bộ cột theo quyền, một dòng ví dụ GIẢ. Không đọc DB, không ghi nhật ký."""
    with_prices = can_see_prices(user)
    example = {
        "code": TEMPLATE_EXAMPLE_CODE,
        "name": "Cá ví dụ",
        "item_group": "Nhóm ví dụ",
        "item_type": Item.ItemType.SIMPLE.label,
        "stock_uom": "Kg",
        "is_active": True,
        "shelf_life_in_days": 365,
        "has_batch_no": True,
        "has_expiry_date": True,
    }
    if with_prices:
        example["new_price"] = 150000
        example["new_price_from"] = timezone.localdate() + datetime.timedelta(days=1)
    content = build_items_workbook(columns_for(with_prices=with_prices), [example])
    return content, 1


def get_import_limits() -> dict:
    """Trả các ngưỡng nhập Excel từ settings (02b §3.4)."""
    return {
        "max_rows": settings.ITEM_IMPORT_MAX_ROWS,
        "max_bytes": settings.ITEM_IMPORT_MAX_BYTES,
        "preview_ttl_minutes": settings.ITEM_IMPORT_PREVIEW_TTL_MINUTES,
    }


def preview_import(*, user, uploaded_file, today: datetime.date | None = None, now: int | None = None) -> dict:
    """
    Đọc file `.xlsx` và dựng kế hoạch xem trước (S5, 02b §3.5).
    Không ghi DB, không ghi AuditLog.
    """
    parsed = read_import_workbook(uploaded_file)
    plan = build_import_plan(parsed, today=today)
    if plan["has_changes"]:
        preview_token, expires_at, _ = issue_preview_token(
            user_id=user.pk,
            file_sha256=parsed.file_sha256,
            data_fingerprint=plan["_data_fingerprint"],
            now=now,
        )
    else:
        preview_token = None
        expires_at = None

    return {
        "preview_token": preview_token,
        "expires_at": expires_at,
        "has_changes": plan["has_changes"],
        "summary": plan["summary"],
        "rows": plan["rows"],
        "warnings": plan["warnings"],
        "limits": plan["limits"],
    }


def commit_import(
    *,
    user,
    uploaded_file,
    preview_token: str,
    today: datetime.date | None = None,
    now: int | None = None,
) -> dict:
    """
    Xác nhận và ghi toàn bộ thay đổi đã xem trước trong một giao dịch nguyên tử (S6, 02b §3.6, §5.3, §7).
    """
    # Bước 2 (§5.3): kiểm chữ ký phiếu trước khi đọc file nếu phiếu trống/sai chữ ký, hoặc kiểm cấp file + sha256 file.
    payload = verify_preview_token_signature(preview_token, user_id=user.pk)
    parsed = read_import_workbook(uploaded_file)
    verify_preview_token_signature(
        preview_token,
        user_id=user.pk,
        file_sha256=parsed.file_sha256,
    )

    import_ref = payload["n"]
    expected_fingerprint = payload["d"]

    with transaction.atomic():
        # Bước 3: Khoá bảng giá mặc định làm khoá tuần tự hoá chung cho mọi lượt nhập (02b D3, §5.3).
        default_price_list = (
            PriceList.objects.select_for_update().filter(is_default=True).order_by("pk").first()
        )

        # Bước 4: Chống bấm đúp / gửi lại cùng phiếu (kiểm trước hạn phiếu).
        existing_audit = (
            AuditLog.objects.filter(action="import_items", changes__import_ref=import_ref)
            .order_by("-id")
            .first()
        )
        if existing_audit is not None:
            prev = existing_audit.changes if isinstance(existing_audit.changes, dict) else {}
            raise ConflictError(
                ALREADY_APPLIED_MSG,
                code="IMPORT_ALREADY_APPLIED",
                extra={
                    "created": prev.get("created", 0),
                    "updated": prev.get("updated", 0),
                    "price_changed": prev.get("price_changed", 0),
                    "visibility_changed": prev.get("visibility_changed", 0),
                },
            )

        # Bước 5: Kiểm hạn phiếu xem trước (410 IMPORT_PREVIEW_EXPIRED).
        check_preview_token_expiry(payload, now=now)

        # Bước 6: Khoá các Item liên quan theo thứ tự pk tăng dần, KHÔNG select_related (luật khoá Postgres).
        lower_codes = {
            normalize_item_code(r.cells["code"].value)
            for r in parsed.rows
            if r.cells.get("code") is not None and r.cells["code"].value is not None
        }
        lower_codes.discard("")
        if lower_codes:
            list(
                Item.objects.annotate(code_lower=Lower("code"))
                .select_for_update()
                .filter(code_lower__in=lower_codes)
                .order_by("pk")
            )

        # Bước 7: Dựng lại kế hoạch dưới khoá và đối chiếu dấu vân tay dữ liệu.
        try:
            plan = build_import_plan(parsed, today=today)
        except BusinessError as exc:
            raise ConflictError(DATA_CHANGED_MSG, code="IMPORT_DATA_CHANGED") from exc

        if plan["_data_fingerprint"] != expected_fingerprint or not plan["has_changes"]:
            raise ConflictError(DATA_CHANGED_MSG, code="IMPORT_DATA_CHANGED")

        normalized = plan["_normalized_plan"]
        summary = plan["summary"]

        items_map: dict[str, Item] = {}
        if lower_codes:
            for it in Item.objects.annotate(code_lower=Lower("code")).filter(code_lower__in=lower_codes):
                items_map[it.code] = it

        # Bước 8a: Tạo Item mới.
        for c_spec in normalized.get("creates", ()):
            try:
                item = Item.objects.create(
                    code=c_spec["code"],
                    name=c_spec["name"],
                    item_group_id=c_spec["item_group_id"],
                    item_type=Item.ItemType.SIMPLE,
                    stock_uom="Kg",
                    is_active=c_spec["is_active"],
                    shelf_life_in_days=c_spec["shelf_life_in_days"],
                    has_batch_no=c_spec["has_batch_no"],
                    has_expiry_date=c_spec["has_expiry_date"],
                    short_note=c_spec.get("short_note", ""),
                    spec=c_spec.get("spec", ""),
                    storage=c_spec.get("storage", ""),
                    origin=c_spec.get("origin", ""),
                    description=c_spec.get("description", ""),
                )
            except IntegrityError as exc:
                raise ConflictError(DATA_CHANGED_MSG, code="IMPORT_DATA_CHANGED") from exc

            items_map[item.code] = item
            populated_fields = [
                "code",
                "name",
                "item_group",
                "is_active",
                "shelf_life_in_days",
                "has_batch_no",
                "has_expiry_date",
                *(k for k in PUBLIC_TEXT_KEYS if c_spec.get(k)),
            ]
            record_audit(
                "create_item",
                actor=user,
                obj=item,
                changes={"fields": sorted(populated_fields)},
                note=IMPORT_AUDIT_NOTE,
            )

        # Bước 8b: Cập nhật Item đã có (AuditLog chỉ ghi tên trường đã đổi, không chép chữ tự do — bất biến 9).
        for u_spec in normalized.get("updates", ()):
            item = items_map.get(u_spec["code"])
            if item is None:
                raise ConflictError(DATA_CHANGED_MSG, code="IMPORT_DATA_CHANGED")
            fields_dict = u_spec["fields"]
            update_cols = []
            audit_fields = []
            for key, val in fields_dict.items():
                setattr(item, key, val)
                update_cols.append(key)
                audit_fields.append("item_group" if key == "item_group_id" else key)
            item.save(update_fields=update_cols)
            record_audit(
                "update_item",
                actor=user,
                obj=item,
                changes={"fields": sorted(audit_fields)},
                note=IMPORT_AUDIT_NOTE,
            )

        # Bước 8c: Đặt giá mới qua set_item_price (nếu phát sinh đơn mới/chồng lấn sau lúc preview → 409 IMPORT_DATA_CHANGED).
        price_specs = normalized.get("prices", ())
        if price_specs and default_price_list is None:
            raise ConflictError(DATA_CHANGED_MSG, code="IMPORT_DATA_CHANGED")
        for p_spec in price_specs:
            item = items_map.get(p_spec["code"])
            if item is None:
                raise ConflictError(DATA_CHANGED_MSG, code="IMPORT_DATA_CHANGED")
            valid_from = datetime.date.fromisoformat(p_spec["valid_from"])
            rate_dec = Decimal(p_spec["rate"])
            try:
                set_item_price(
                    price_list=default_price_list,
                    item=item,
                    rate=rate_dec,
                    valid_from=valid_from,
                    valid_upto=None,
                    actor=user,
                )
            except BusinessError as exc:
                raise ConflictError(DATA_CHANGED_MSG, code="IMPORT_DATA_CHANGED") from exc

        # Bước 9: Ghi AuditLog tổng kết lượt nhập.
        audit_summary = {
            "import_ref": import_ref,
            "rows": summary["total_rows"],
            "created": summary["created"],
            "updated": summary["updated"],
            "price_changed": summary["price_changed"],
            "visibility_changed": summary["visibility_changed"],
        }
        record_audit("import_items", actor=user, changes=audit_summary)

        codes = sorted({r["code"] for r in plan["rows"]})
        return {
            "created": summary["created"],
            "updated": summary["updated"],
            "price_changed": summary["price_changed"],
            "visibility_changed": summary["visibility_changed"],
            "codes": codes,
        }
