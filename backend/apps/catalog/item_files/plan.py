"""
Kiểm tra nghiệp vụ từng dòng và dựng kế hoạch xem trước nhập mặt hàng từ Excel (FISH-66 S5, S6; 02b §3.5, §4.2–§4.4, §5.1).

- Truy vấn DB số lượng hằng số (O(1) số câu SQL theo số dòng trong file, trừ khi có dòng đặt giá lùi ngày cần kiểm đơn hàng).
- Kiểm đủ mọi lỗi trong file (không dừng ở lỗi đầu), trả tối đa 2000 lỗi kèm `error_count` và `error_row_count`.
- Áp quy tắc C-1: ô chữ không bắt buộc để trống → giữ nguyên giá trị hiện có trong DB (không xoá chữ cũ).
- Áp quy tắc Q-TL-2 = A: kiểm `public_text_error` (BR-DM-25) cho cả `name` và 5 trường chữ công khai khi tạo mới hoặc đổi chữ.
"""
import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import re
import unicodedata

from django.conf import settings
from django.db.models.functions import Lower
from django.utils import timezone

from apps.catalog.items.public_text import PUBLIC_TEXT_LIMITS, public_text_error
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.catalog.pricing.services import EFFECTIVE_ORDER, check_new_price
from apps.common.exceptions import BusinessError

from .columns import (
    ALL_COLUMNS,
    COLUMNS_BY_KEY,
    EDITABLE_ITEM_KEYS,
    PUBLIC_TEXT_KEYS,
)
from .reader import (
    NO_PRICE_LIST_MSG,
    ParsedCell,
    ParsedWorkbook,
    file_limits_payload,
    invalid_file_error,
)
from .workbook import FLAG_NO, FLAG_YES, clean_excel_text

CODE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
INT_STR_RE = re.compile(r"^\d+$")
DOT_THOUSANDS_RE = re.compile(r"^\d{1,3}(\.\d{3})+$")
DATE_VN_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

MAX_ERRORS_RETURNED = 2000
MAX_PRICE_VND = 1_000_000_000
MAX_SHELF_LIFE_DAYS = 3650
DEFAULT_NEW_SHELF_LIFE_DAYS = 365
TEMPLATE_EXAMPLE_CODE = "VD-001"
DISPLAY_TRUNCATE_LEN = 120

COLUMN_ORDER = {col.header: idx for idx, col in enumerate(ALL_COLUMNS)}

UNCACHED_FORMULA_MSG = "Ô có công thức, hãy dán giá trị."
INVALID_PRICE_MSG = "Giá phải là số nguyên đồng lớn hơn 0."
INVALID_DATE_MSG = "Ngày áp dụng phải ghi dạng dd/mm/yyyy (ví dụ 20/11/2026) hoặc định dạng ngày Excel."
DATE_WITHOUT_PRICE_MSG = "Có ngày áp dụng mà chưa có giá mới."
FLAG_VALUES_MSG = "Ghi Có hoặc Không."
SHELF_LIFE_MSG = "Hạn dùng mặc định phải là số nguyên từ 1 đến 3.650 ngày."

READONLY_WARNING_MESSAGES = {
    "Giá bán hiện hành": "Cột Giá bán hiện hành chỉ để xem, không đổi giá. Muốn đổi giá, ghi vào cột Giá mới.",
    "Loại": "Cột Loại chỉ để xem, không đổi loại mặt hàng.",
    "Đơn vị": "Cột Đơn vị chỉ để xem, mọi mặt hàng tính theo Kg.",
}


def _norm_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    cleaned = clean_excel_text(str(value)).strip()
    return unicodedata.normalize("NFC", cleaned)


def normalize_item_code(value: object) -> str:
    """Mã hàng đã chuẩn hoá, dạng chữ thường: nguồn DUY NHẤT để so và khoá mã (kế hoạch bước 7 và khoá bước 6)."""
    return _norm_text(value).lower()


def _norm_group_key(name: str) -> str:
    return " ".join(_norm_text(name).split()).casefold()


def _is_blank(cell: ParsedCell | None) -> bool:
    if cell is None:
        return True
    if cell.is_formula and not cell.has_cached_value:
        return False
    if cell.value is None:
        return True
    if isinstance(cell.value, str) and cell.value.strip() == "":
        return True
    return False


def _parse_flag(cell: ParsedCell | None, default_value: bool | None) -> tuple[bool | None, str | None]:
    if cell is not None and cell.is_formula and not cell.has_cached_value:
        return None, UNCACHED_FORMULA_MSG
    if _is_blank(cell):
        if default_value is None:
            return None, FLAG_VALUES_MSG
        return default_value, None
    raw = cell.value if cell is not None else None
    if isinstance(raw, bool):
        return raw, None
    text = _norm_text(raw).casefold()
    if text == FLAG_YES.casefold():
        return True, None
    if text == FLAG_NO.casefold():
        return False, None
    return None, FLAG_VALUES_MSG


def _parse_int_exact(raw) -> int | None:
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw) if raw.is_integer() else None
    if isinstance(raw, Decimal):
        return int(raw) if raw == int(raw) else None
    text = _norm_text(raw)
    if INT_STR_RE.match(text):
        return int(text)
    if DOT_THOUSANDS_RE.match(text):
        return int(text.replace(".", ""))
    return None


def _parse_price_vnd(cell: ParsedCell | None) -> tuple[int | None, str | None]:
    if cell is not None and cell.is_formula and not cell.has_cached_value:
        return None, UNCACHED_FORMULA_MSG
    if _is_blank(cell):
        return None, None
    val = _parse_int_exact(cell.value if cell is not None else None)
    if val is None or val <= 0 or val > MAX_PRICE_VND:
        return None, INVALID_PRICE_MSG
    return val, None


def _parse_excel_date(cell: ParsedCell | None) -> tuple[datetime.date | None, str | None]:
    if cell is not None and cell.is_formula and not cell.has_cached_value:
        return None, UNCACHED_FORMULA_MSG
    if _is_blank(cell):
        return None, None
    raw = cell.value if cell is not None else None
    if isinstance(raw, datetime.datetime):
        return raw.date(), None
    if isinstance(raw, datetime.date):
        return raw, None
    text = _norm_text(raw)
    m = DATE_VN_RE.match(text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime.date(year, month, day), None
        except ValueError:
            return None, INVALID_DATE_MSG
    try:
        return datetime.date.fromisoformat(text), None
    except ValueError:
        return None, INVALID_DATE_MSG


def _format_dup_rows(rows: list[int]) -> str:
    if len(rows) == 2:
        return f"{rows[0]} và {rows[1]}"
    return ", ".join(str(r) for r in rows[:-1]) + f" và {rows[-1]}"


def _truncate_display(text: str) -> str:
    if len(text) <= DISPLAY_TRUNCATE_LEN:
        return text
    return text[:DISPLAY_TRUNCATE_LEN] + "…"


def _format_field_value(field: str, value) -> str:
    if field in ("is_active", "has_batch_no", "has_expiry_date"):
        return FLAG_YES if value else FLAG_NO
    return str(value)


def load_import_db_state(lower_codes: set[str]):
    """
    Nạp trạng thái DB hiện tại cho tập `lower_codes` bằng số truy vấn cố định (02b §4.4):
    1. PriceList mặc định
    2. Toàn bộ ItemGroup
    3. Item khớp Lower(code)
    4. ItemPrice của bảng giá mặc định cho các Item tìm được
    """
    default_price_list = PriceList.objects.filter(is_default=True).first()

    groups_by_key: dict[str, ItemGroup] = {}
    duplicate_group_keys: set[str] = set()
    for g in ItemGroup.objects.all():
        gkey = _norm_group_key(g.name)
        if gkey in groups_by_key:
            duplicate_group_keys.add(gkey)
        else:
            groups_by_key[gkey] = g

    items_by_code: dict[str, Item] = {}
    items_by_lower: dict[str, Item] = {}
    if lower_codes:
        qs = (
            Item.objects.select_related("item_group")
            .annotate(code_lower=Lower("code"))
            .filter(code_lower__in=lower_codes)
        )
        for item in qs:
            items_by_code[item.code] = item
            items_by_lower[item.code_lower] = item

    prices_by_item_id: dict[int, list[ItemPrice]] = {}
    if default_price_list is not None and items_by_lower:
        item_ids = [it.pk for it in items_by_lower.values()]
        price_qs = (
            ItemPrice.objects.filter(price_list=default_price_list, item_id__in=item_ids)
            .order_by(*EFFECTIVE_ORDER)
        )
        for p in price_qs:
            prices_by_item_id.setdefault(p.item_id, []).append(p)

    return default_price_list, groups_by_key, duplicate_group_keys, items_by_code, items_by_lower, prices_by_item_id


def compute_data_fingerprint(
    *,
    default_price_list_id: int | None,
    today: datetime.date,
    lower_codes: set[str],
    group_keys: set[str],
    items_by_lower: dict[str, Item],
    groups_by_key: dict[str, ItemGroup],
    prices_by_item_id: dict[int, list[ItemPrice]],
    normalized_plan: dict,
) -> str:
    """Tính dấu vân tay SHA-256 tất định cho trạng thái DB và kế hoạch nhập (02b §5.1)."""
    item_entries = []
    for lc in sorted(lower_codes):
        item = items_by_lower.get(lc)
        if item is None:
            item_entries.append(["missing", lc])
            continue
        prices = sorted(prices_by_item_id.get(item.pk, ()), key=lambda x: x.pk)
        item_entries.append([
            "item",
            item.pk,
            item.code,
            _norm_text(item.name),
            item.item_group_id,
            item.item_type,
            item.stock_uom,
            item.is_active,
            item.shelf_life_in_days,
            item.has_batch_no,
            item.has_expiry_date,
            _norm_text(item.short_note),
            _norm_text(item.spec),
            _norm_text(item.storage),
            _norm_text(item.origin),
            _norm_text(item.description),
            [
                [
                    p.pk,
                    str(p.rate),
                    p.valid_from.isoformat(),
                    p.valid_upto.isoformat() if p.valid_upto else None,
                ]
                for p in prices
            ],
        ])
    group_entries = []
    for gk in sorted(group_keys):
        g = groups_by_key.get(gk)
        group_entries.append([gk, g.pk if g is not None else None])
    blob = json.dumps(
        {
            "price_list_id": default_price_list_id,
            "today": today.isoformat(),
            "items": item_entries,
            "groups": group_entries,
            "plan": normalized_plan,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _compute_price_flags(
    old_rate: Decimal | None,
    new_rate_int: int,
    valid_from: datetime.date,
    today: datetime.date,
) -> list[str]:
    flags = []
    new_dec = Decimal(new_rate_int)
    if old_rate is not None and old_rate > 0:
        factor = Decimal(settings.ITEM_IMPORT_PRICE_ZERO_FACTOR)
        alert_pct = Decimal(settings.ITEM_IMPORT_PRICE_ALERT_PERCENT)
        if new_dec >= old_rate * factor or new_dec * factor <= old_rate:
            flags.append("check_zeros")
        if abs(new_dec - old_rate) * Decimal(100) >= old_rate * alert_pct:
            flags.append("large_change")
    if valid_from < today:
        flags.append("backdated")
    return flags


def build_import_plan(parsed: ParsedWorkbook, *, today: datetime.date | None = None) -> dict:
    """Kiểm từng dòng của `parsed` và tạo kế hoạch xem trước (hoặc ném `IMPORT_INVALID_ROWS` nếu có lỗi)."""
    today = today or timezone.localdate()

    rows_by_lower_code: dict[str, list[int]] = {}
    raw_codes_by_row: dict[int, str] = {}
    group_keys: set[str] = set()

    for row in parsed.rows:
        c_code = row.cells.get("code")
        code_str = "" if _is_blank(c_code) else _norm_text(c_code.value)
        raw_codes_by_row[row.row_number] = code_str
        if code_str and code_str.upper() != TEMPLATE_EXAMPLE_CODE:
            rows_by_lower_code.setdefault(normalize_item_code(code_str), []).append(row.row_number)

        c_group = row.cells.get("item_group")
        if not _is_blank(c_group):
            group_keys.add(_norm_group_key(c_group.value))

    lower_codes = set(rows_by_lower_code.keys())
    (
        default_price_list,
        groups_by_key,
        duplicate_group_keys,
        items_by_code,
        items_by_lower,
        prices_by_item_id,
    ) = load_import_db_state(lower_codes)

    if default_price_list is None:
        raise invalid_file_error("no_price_list", NO_PRICE_LIST_MSG)

    def _current_effective_price(item_id: int) -> ItemPrice | None:
        for p in prices_by_item_id.get(item_id, ()):
            if p.valid_from <= today and (p.valid_upto is None or p.valid_upto >= today):
                return p
        return None

    all_errors: list[dict] = []
    warnings: list[dict] = []

    preview_rows: list[dict] = []
    normalized_creates: list[dict] = []
    normalized_updates: list[dict] = []
    normalized_prices: list[dict] = []

    created_count = 0
    updated_count = 0
    price_changed_count = 0
    visibility_changed_count = 0
    unchanged_count = 0

    for row in parsed.rows:
        rnum = row.row_number
        row_errors: list[tuple[str, str]] = []
        code_str = raw_codes_by_row[rnum]
        code_display = code_str or ""

        # 1. Mã hàng
        c_code = row.cells.get("code")
        existing: Item | None = None
        if c_code is not None and c_code.is_formula and not c_code.has_cached_value:
            row_errors.append(("Mã hàng", UNCACHED_FORMULA_MSG))
        elif not code_str:
            row_errors.append(("Mã hàng", "Nhập mã hàng."))
        elif len(code_str) > 40 or not CODE_RE.match(code_str):
            row_errors.append(("Mã hàng", "Mã hàng tối đa 40 ký tự, chỉ gồm chữ, số, dấu chấm, gạch ngang hoặc gạch dưới."))
        elif code_str.upper() == TEMPLATE_EXAMPLE_CODE:
            code_display = TEMPLATE_EXAMPLE_CODE
            row_errors.append(("Mã hàng", "Đây là dòng ví dụ, hãy xoá hoặc đổi mã."))
        else:
            dup_rows = rows_by_lower_code.get(code_str.lower(), [])
            if len(dup_rows) > 1:
                row_errors.append((
                    "Mã hàng",
                    f"Mã {code_str} lặp ở dòng {_format_dup_rows(dup_rows)}. Mỗi mã chỉ ghi một dòng.",
                ))
            existing = items_by_code.get(code_str)
            existing_ci = items_by_lower.get(code_str.lower())
            if existing is None and existing_ci is not None:
                row_errors.append((
                    "Mã hàng",
                    f"Mã {code_str} gần trùng mã {existing_ci.code} đã có. Sửa đúng mã.",
                ))

        # 2. Tên mặt hàng
        c_name = row.cells.get("name")
        name_val = ""
        if c_name is not None and c_name.is_formula and not c_name.has_cached_value:
            row_errors.append(("Tên", UNCACHED_FORMULA_MSG))
        else:
            name_val = "" if _is_blank(c_name) else _norm_text(c_name.value)
            if not name_val:
                row_errors.append(("Tên", "Nhập tên mặt hàng."))
            elif existing is None or name_val != _norm_text(existing.name):
                if len(name_val) > 200:
                    row_errors.append(("Tên", "Tên mặt hàng tối đa 200 ký tự."))
                else:
                    pub_err = public_text_error(name_val)
                    if pub_err:
                        row_errors.append(("Tên", pub_err))

        # 3. Nhóm hàng
        c_group = row.cells.get("item_group")
        target_group: ItemGroup | None = None
        if c_group is not None and c_group.is_formula and not c_group.has_cached_value:
            row_errors.append(("Nhóm hàng", UNCACHED_FORMULA_MSG))
        else:
            group_str = "" if _is_blank(c_group) else _norm_text(c_group.value)
            gkey = _norm_group_key(group_str)
            if not group_str:
                row_errors.append(("Nhóm hàng", "Nhập nhóm hàng."))
            elif gkey in duplicate_group_keys:
                row_errors.append(("Nhóm hàng", f'Có nhiều nhóm tên "{group_str}". Sửa tên nhóm ở ERP trước.'))
            elif gkey not in groups_by_key:
                row_errors.append((
                    "Nhóm hàng",
                    f'Nhóm "{group_str}" chưa có. Tạo nhóm ở ERP trước hoặc sửa đúng tên nhóm.',
                ))
            else:
                target_group = groups_by_key[gkey]
                if existing is not None and existing.is_bundle and target_group.pk != existing.item_group_id:
                    row_errors.append((
                        "Nhóm hàng",
                        "Combo chỉ sửa tên, chữ, giá và đang kinh doanh bằng file. Đổi Nhóm hàng ở form combo.",
                    ))

        # 4. Loại (chỉ đọc với món đã có; món mới chặn tạo Combo)
        c_type = row.cells.get("item_type")
        if c_type is not None and c_type.is_formula and not c_type.has_cached_value:
            row_errors.append(("Loại", UNCACHED_FORMULA_MSG))
        else:
            type_str = "" if _is_blank(c_type) else _norm_text(c_type.value)
            if existing is not None:
                if type_str and type_str.casefold() != existing.get_item_type_display().casefold():
                    warnings.append({
                        "row": rnum,
                        "code": code_display,
                        "column": "Loại",
                        "message": READONLY_WARNING_MESSAGES["Loại"],
                    })
            else:
                if type_str.casefold() in ("combo", "bundle"):
                    row_errors.append(("Loại", "Tạo combo mới làm ở form combo ERP."))
                elif type_str and type_str.casefold() != Item.ItemType.SIMPLE.label.casefold():
                    row_errors.append(("Loại", "Loại mặt hàng chỉ nhận 'Mặt hàng thường' khi thêm từ Excel."))

        # 5. Đơn vị (chỉ đọc)
        c_uom = row.cells.get("stock_uom")
        if c_uom is not None and c_uom.is_formula and not c_uom.has_cached_value:
            row_errors.append(("Đơn vị", UNCACHED_FORMULA_MSG))
        else:
            uom_str = "" if _is_blank(c_uom) else _norm_text(c_uom.value)
            expected_uom = existing.stock_uom if existing is not None else "Kg"
            if uom_str and uom_str.casefold() != expected_uom.casefold():
                warnings.append({
                    "row": rnum,
                    "code": code_display,
                    "column": "Đơn vị",
                    "message": READONLY_WARNING_MESSAGES["Đơn vị"],
                })

        # 6. Cờ Đang kinh doanh (bắt buộc), Quản lý theo lô, Có hạn dùng
        is_active_val, err_active = _parse_flag(row.cells.get("is_active"), None)
        if err_active:
            row_errors.append(("Đang kinh doanh", err_active))

        c_batch = row.cells.get("has_batch_no")
        has_batch_val, err_batch = _parse_flag(
            c_batch, existing.has_batch_no if existing is not None else True
        )
        if err_batch:
            row_errors.append(("Quản lý theo lô", err_batch))
        elif (
            existing is not None
            and existing.is_bundle
            and not _is_blank(c_batch)
            and has_batch_val != existing.has_batch_no
        ):
            row_errors.append((
                "Quản lý theo lô",
                "Combo chỉ sửa tên, chữ, giá và đang kinh doanh bằng file. Đổi Quản lý theo lô ở form combo.",
            ))

        c_expiry = row.cells.get("has_expiry_date")
        has_expiry_val, err_expiry = _parse_flag(
            c_expiry, existing.has_expiry_date if existing is not None else True
        )
        if err_expiry:
            row_errors.append(("Có hạn dùng", err_expiry))
        elif (
            existing is not None
            and existing.is_bundle
            and not _is_blank(c_expiry)
            and has_expiry_val != existing.has_expiry_date
        ):
            row_errors.append((
                "Có hạn dùng",
                "Combo chỉ sửa tên, chữ, giá và đang kinh doanh bằng file. Đổi Có hạn dùng ở form combo.",
            ))

        # 7. Hạn dùng mặc định (ngày)
        c_shelf = row.cells.get("shelf_life_in_days")
        shelf_val = existing.shelf_life_in_days if existing is not None else DEFAULT_NEW_SHELF_LIFE_DAYS
        if c_shelf is not None and c_shelf.is_formula and not c_shelf.has_cached_value:
            row_errors.append(("Hạn dùng mặc định (ngày)", UNCACHED_FORMULA_MSG))
        elif not _is_blank(c_shelf):
            parsed_shelf = _parse_int_exact(c_shelf.value if c_shelf else None)
            if parsed_shelf is None:
                row_errors.append(("Hạn dùng mặc định (ngày)", SHELF_LIFE_MSG))
            elif existing is not None and existing.is_bundle and parsed_shelf != existing.shelf_life_in_days:
                row_errors.append((
                    "Hạn dùng mặc định (ngày)",
                    "Combo chỉ sửa tên, chữ, giá và đang kinh doanh bằng file. Đổi Hạn dùng mặc định (ngày) ở form combo.",
                ))
            elif (parsed_shelf < 1 or parsed_shelf > MAX_SHELF_LIFE_DAYS) and not (
                existing is not None and parsed_shelf == existing.shelf_life_in_days
            ):
                row_errors.append(("Hạn dùng mặc định (ngày)", SHELF_LIFE_MSG))
            else:
                shelf_val = parsed_shelf

        # 8. 5 cột chữ công khai (C-1: ô trống giữ nguyên giá trị cũ trong DB)
        public_values: dict[str, str] = {}
        for key in PUBLIC_TEXT_KEYS:
            col_header = COLUMNS_BY_KEY[key].header
            cell = row.cells.get(key)
            if cell is not None and cell.is_formula and not cell.has_cached_value:
                row_errors.append((col_header, UNCACHED_FORMULA_MSG))
                continue
            if _is_blank(cell):
                public_values[key] = _norm_text(getattr(existing, key)) if existing is not None else ""
                continue
            text = _norm_text(cell.value)
            db_clean = _norm_text(getattr(existing, key)) if existing is not None else None
            if existing is None or text != db_clean:
                limit = PUBLIC_TEXT_LIMITS[key]
                if len(text) > limit:
                    row_errors.append((col_header, f"Tối đa {limit} ký tự."))
                    continue
                pub_err = public_text_error(text)
                if pub_err:
                    row_errors.append((col_header, pub_err))
                    continue
            public_values[key] = text

        # 9. Giá bán hiện hành (chỉ đọc) + Giá mới + Ngày áp dụng giá mới
        cur_price_obj = _current_effective_price(existing.pk) if existing is not None else None
        cur_rate_dec = cur_price_obj.rate if cur_price_obj is not None else None
        cur_rate_int = int(cur_rate_dec) if cur_rate_dec is not None else None
        item_prices = prices_by_item_id.get(existing.pk, []) if existing is not None else []

        c_cur_price = row.cells.get("current_price")
        if c_cur_price is not None and not _is_blank(c_cur_price):
            parsed_cur = _parse_int_exact(c_cur_price.value)
            if parsed_cur != cur_rate_int:
                warnings.append({
                    "row": rnum,
                    "code": code_display,
                    "column": "Giá bán hiện hành",
                    "message": READONLY_WARNING_MESSAGES["Giá bán hiện hành"],
                })

        c_new_price = row.cells.get("new_price")
        c_new_from = row.cells.get("new_price_from")
        new_from_was_blank = _is_blank(c_new_from)
        new_rate_int, err_price = _parse_price_vnd(c_new_price)
        if err_price:
            row_errors.append(("Giá mới", err_price))

        valid_from_date: datetime.date | None = None
        if _is_blank(c_new_price) and not err_price:
            if not new_from_was_blank:
                _, err_date = _parse_excel_date(c_new_from)
                row_errors.append(("Ngày áp dụng giá mới", err_date or DATE_WITHOUT_PRICE_MSG))
        elif new_rate_int is not None:
            if new_from_was_blank:
                valid_from_date = today
            else:
                parsed_date, err_date = _parse_excel_date(c_new_from)
                if err_date:
                    row_errors.append(("Ngày áp dụng giá mới", err_date))
                else:
                    valid_from_date = parsed_date

        if new_rate_int is not None and valid_from_date is not None:
            # Nếu Giá mới = giá hiện hành và ô Ngày áp dụng để trống (hoặc bằng ngày hiệu lực của giá hiện hành mở) → coi là không đổi (02b §4.3).
            if (
                cur_price_obj is not None
                and cur_rate_int == new_rate_int
                and cur_price_obj.valid_upto is None
                and (new_from_was_blank or valid_from_date == cur_price_obj.valid_from)
            ):
                new_rate_int = None
                valid_from_date = None
            else:
                try:
                    check_new_price(
                        price_list=default_price_list,
                        item=existing,
                        valid_from=valid_from_date,
                        valid_upto=None,
                        existing_prices=item_prices,
                    )
                except BusinessError as exc:
                    row_errors.append(("Ngày áp dụng giá mới", str(exc)))

        if row_errors:
            for col_name, msg in row_errors:
                all_errors.append({
                    "row": rnum,
                    "code": code_display,
                    "column": col_name,
                    "message": msg,
                })
            continue

        if all_errors:
            continue

        assert target_group is not None
        assert is_active_val is not None
        assert has_batch_val is not None
        assert has_expiry_val is not None

        row_changes_list: list[dict] = []
        has_non_visibility_change = False
        has_visibility_change = False

        if existing is None:
            normalized_creates.append({
                "code": code_display,
                "name": name_val,
                "item_group_id": target_group.pk,
                "is_active": is_active_val,
                "shelf_life_in_days": shelf_val,
                "has_batch_no": has_batch_val,
                "has_expiry_date": has_expiry_val,
                **public_values,
            })
        else:
            candidate_values = {
                "name": name_val,
                "item_group": _norm_text(target_group.name),
                "is_active": is_active_val,
                "shelf_life_in_days": shelf_val,
                "has_batch_no": has_batch_val,
                "has_expiry_date": has_expiry_val,
                **public_values,
            }
            existing_values = {
                "name": _norm_text(existing.name),
                "item_group": _norm_text(existing.item_group.name),
                "is_active": existing.is_active,
                "shelf_life_in_days": existing.shelf_life_in_days,
                "has_batch_no": existing.has_batch_no,
                "has_expiry_date": existing.has_expiry_date,
                **{k: _norm_text(getattr(existing, k)) for k in PUBLIC_TEXT_KEYS},
            }
            changed_fields_payload = {}
            for key in EDITABLE_ITEM_KEYS:
                if candidate_values[key] != existing_values[key]:
                    if key == "item_group":
                        changed_fields_payload["item_group_id"] = target_group.pk
                    else:
                        changed_fields_payload[key] = candidate_values[key]
                    row_changes_list.append({
                        "field": key,
                        "label": COLUMNS_BY_KEY[key].header,
                        "old": _truncate_display(_format_field_value(key, existing_values[key])),
                        "new": _truncate_display(_format_field_value(key, candidate_values[key])),
                    })
                    if key == "is_active":
                        has_visibility_change = True
                    else:
                        has_non_visibility_change = True

            if changed_fields_payload:
                normalized_updates.append({
                    "code": existing.code,
                    "fields": changed_fields_payload,
                })

        price_entry: dict | None = None
        if new_rate_int is not None and valid_from_date is not None:
            new_dec = Decimal(new_rate_int)
            if cur_rate_dec is not None and cur_rate_dec > 0 and cur_rate_int is not None:
                diff_int = new_rate_int - cur_rate_int
                pct_dec = (
                    Decimal(diff_int) * Decimal(100) / cur_rate_dec
                ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                old_str = str(cur_rate_int)
                diff_amount_str = str(diff_int)
                diff_pct_str = f"{pct_dec:.1f}"
            else:
                old_str = None
                diff_amount_str = None
                diff_pct_str = None

            flags = _compute_price_flags(cur_rate_dec, new_rate_int, valid_from_date, today)
            price_entry = {
                "old": old_str,
                "new": str(new_rate_int),
                "valid_from": valid_from_date.isoformat(),
                "change_amount": diff_amount_str,
                "change_percent": diff_pct_str,
                "flags": flags,
            }
            normalized_prices.append({
                "code": code_display if existing is None else existing.code,
                "rate": str(new_rate_int),
                "valid_from": valid_from_date.isoformat(),
            })

        is_changed_row = (existing is None) or bool(row_changes_list) or (price_entry is not None)
        if not is_changed_row:
            unchanged_count += 1
            continue

        # Tính shop_state (T-8, 02b §3.5): selling | hidden | will_show | will_hide
        if existing is None:
            # S5-AC2 & 02b §3.5: món mới đang kinh doanh và có giá mới → will_show
            # Giá mới có hiệu lực từ ngày mai trở đi thì hôm nay món chưa hiện trên Shop (T-8: cần giá hiệu lực hôm nay).
            price_effective_today = (
                price_entry is not None and valid_from_date is not None and valid_from_date <= today
            )
            shop_state = "will_show" if (is_active_val and price_effective_today) else "hidden"
        elif existing.is_active and not is_active_val:
            shop_state = "will_hide"
        elif not existing.is_active and is_active_val:
            has_price_after = (cur_price_obj is not None) or (
                price_entry is not None and valid_from_date is not None and valid_from_date <= today
            )
            shop_state = "will_show" if has_price_after else "hidden"
        else:
            if not is_active_val:
                shop_state = "hidden"
            elif cur_price_obj is None and price_entry is not None and valid_from_date is not None and valid_from_date <= today:
                shop_state = "will_show"
            elif cur_price_obj is not None or (
                price_entry is not None and valid_from_date is not None and valid_from_date <= today
            ):
                shop_state = "selling"
            else:
                shop_state = "hidden"

        if existing is None:
            created_count += 1
        else:
            if has_non_visibility_change:
                updated_count += 1
            if has_visibility_change:
                visibility_changed_count += 1
        if price_entry is not None:
            price_changed_count += 1

        preview_rows.append({
            "row": rnum,
            "code": code_display if existing is None else existing.code,
            "action": "create" if existing is None else "update",
            "name": name_val,
            "item_group": target_group.name,
            "changes": row_changes_list,
            "price": price_entry,
            "is_active_after": is_active_val,
            "shop_state": shop_state,
        })

    if all_errors:
        all_errors.sort(key=lambda e: (e["row"], COLUMN_ORDER.get(e["column"], 999)))
        error_count = len(all_errors)
        error_row_count = len({e["row"] for e in all_errors})
        errors_truncated = error_count > MAX_ERRORS_RETURNED
        raise BusinessError(
            f"File có {error_count} lỗi ở {error_row_count} dòng. Chưa ghi gì.",
            code="IMPORT_INVALID_ROWS",
            extra={
                "error_count": error_count,
                "error_row_count": error_row_count,
                "errors_truncated": errors_truncated,
                "errors": all_errors[:MAX_ERRORS_RETURNED],
                "limits": file_limits_payload(),
            },
        )

    will_show_count = sum(1 for r in preview_rows if r["shop_state"] == "will_show")
    will_hide_count = sum(1 for r in preview_rows if r["shop_state"] == "will_hide")
    has_changes = len(preview_rows) > 0

    summary = {
        "total_rows": len(parsed.rows),
        "created": created_count,
        "updated": updated_count,
        "price_changed": price_changed_count,
        "visibility_changed": visibility_changed_count,
        "unchanged": unchanged_count,
        "will_show_on_shop": will_show_count,
        "will_hide_from_shop": will_hide_count,
    }

    normalized_plan = {
        "creates": normalized_creates,
        "updates": normalized_updates,
        "prices": normalized_prices,
        "summary": summary,
    }

    data_fingerprint = compute_data_fingerprint(
        default_price_list_id=default_price_list.pk,
        today=today,
        lower_codes=lower_codes,
        group_keys=group_keys,
        items_by_lower=items_by_lower,
        groups_by_key=groups_by_key,
        prices_by_item_id=prices_by_item_id,
        normalized_plan=normalized_plan,
    )

    return {
        "has_changes": has_changes,
        "summary": summary,
        "rows": preview_rows,
        "warnings": warnings,
        "limits": file_limits_payload(),
        "_normalized_plan": normalized_plan,
        "_data_fingerprint": data_fingerprint,
        "_lower_codes": sorted(lower_codes),
        "_group_keys": sorted(group_keys),
    }
