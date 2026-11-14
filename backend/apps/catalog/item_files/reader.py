"""
Đọc và kiểm tra an toàn file .xlsx tải lên ở bước xem trước/xác nhận nhập mặt hàng (FISH-66, 02b §3.5, §4.1, §6.1).

- Kiểm kích thước nén (ITEM_IMPORT_MAX_BYTES) và kích thước giải nén trong zip (ITEM_IMPORT_MAX_UNPACKED_BYTES, ≤ 2000 mục).
- Từ chối .xls, .csv, file giả đổi đuôi, .xlsm hoặc file chứa macro (`macroEnabled` / `vbaProject.bin`).
- Mở bằng openpyxl ở chế độ `read_only=True, keep_links=False, keep_vba=False` (defusedxml chặn XXE/billion laughs).
- Mở song song `data_only=True` và `data_only=False` để bắt công thức và kiểm giá trị lưu sẵn.
"""
from dataclasses import dataclass
import hashlib
import io
import zipfile

from django.conf import settings
import openpyxl
import openpyxl.xml

from apps.common.exceptions import BusinessError

from .columns import ALL_COLUMNS, COLUMNS_BY_HEADER, REQUIRED_HEADERS
from .workbook import SHEET_ITEMS

MAX_ZIP_ENTRIES = 2000
ZIP_MAGIC = b"PK\x03\x04"
# Chỉ quét tối đa số cột của mẫu cộng chút dư (để vẫn bắt được cột lạ sát bên phải), không quét cột rác xa hơn (M1).
SCAN_EXTRA_COLS = 8
# Trần cứng số dòng đã quét (kể cả dòng trống) tính theo bội của số dòng tối đa (M1, 02b §13.3).
SCAN_ROWS_FACTOR = 2
SCAN_ROWS_SLACK = 10

NOT_XLSX_MSG = "Chỉ nhận file .xlsx. Trong Excel chọn Lưu thành → Sổ làm việc Excel (.xlsx)."
UNREADABLE_MSG = "Không đọc được file này. Mở lại bằng Excel, lưu thành .xlsx rồi chọn lại."
EMPTY_FILE_MSG = "File chưa có dòng mặt hàng nào."
NO_PRICE_LIST_MSG = "Chưa có bảng giá mặc định. Báo quản trị tạo bảng giá Bán lẻ trước."


@dataclass(frozen=True)
class ParsedCell:
    value: object
    is_formula: bool = False
    has_cached_value: bool = True


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    cells: dict


@dataclass(frozen=True)
class ParsedWorkbook:
    file_sha256: str
    headers: tuple
    rows: tuple


def file_limits_payload() -> dict:
    return {
        "max_rows": settings.ITEM_IMPORT_MAX_ROWS,
        "max_bytes": settings.ITEM_IMPORT_MAX_BYTES,
    }


def format_vn_int(val: int) -> str:
    return f"{int(val):,}".replace(",", ".")


def format_vn_mb(max_bytes: int) -> str:
    mb_unit = 1024 * 1024
    if max_bytes >= mb_unit and max_bytes % mb_unit == 0:
        return f"{format_vn_int(max_bytes // mb_unit)} MB"
    mb_val = max_bytes / mb_unit
    if mb_val >= 1:
        return f"{mb_val:.1f}".replace(".", ",") + " MB"
    kb_val = max(1, round(max_bytes / 1024))
    return f"{format_vn_int(kb_val)} KB"


def invalid_file_error(reason: str, detail: str, *, columns: list[str] | None = None) -> BusinessError:
    extra = {
        "reason": reason,
        "limits": file_limits_payload(),
    }
    if columns is not None:
        extra["columns"] = list(columns)
    return BusinessError(detail, code="IMPORT_INVALID_FILE", extra=extra)


def _file_too_large_error() -> BusinessError:
    mb_str = format_vn_mb(settings.ITEM_IMPORT_MAX_BYTES)
    return invalid_file_error(
        "too_large",
        f"File quá {mb_str}. Xoá bớt dòng hoặc tách thành hai file.",
    )


def _check_zip_container(raw_bytes: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_ZIP_ENTRIES:
                raise invalid_file_error("unreadable", UNREADABLE_MSG)
            total_unpacked = sum(info.file_size for info in infos)
            if total_unpacked > settings.ITEM_IMPORT_MAX_UNPACKED_BYTES:
                raise invalid_file_error("unreadable", UNREADABLE_MSG)
            names = set(zf.namelist())
            if any(name.lower().endswith("vbaproject.bin") for name in names):
                raise invalid_file_error("not_xlsx", NOT_XLSX_MSG)
            if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                raise invalid_file_error("unreadable", UNREADABLE_MSG)
            content_types = zf.read("[Content_Types].xml")
            if b"macroEnabled" in content_types or b"vbaProject" in content_types:
                raise invalid_file_error("not_xlsx", NOT_XLSX_MSG)
            if b"spreadsheetml.sheet.main+xml" not in content_types:
                raise invalid_file_error("not_xlsx", NOT_XLSX_MSG)
    except BusinessError:
        raise
    except Exception as exc:
        raise invalid_file_error("unreadable", UNREADABLE_MSG) from exc


def _too_many_rows_error(max_rows):
    rows_str = format_vn_int(max_rows)
    return invalid_file_error(
        "too_many_rows",
        f"File quá {rows_str} dòng. Tách thành nhiều file, mỗi file tối đa {rows_str} dòng.",
    )


def _parse_headers(header_cells):
    indexed = []
    seen = set()
    duplicates = []
    unknowns = []
    for idx, cell in enumerate(header_cells):
        raw = getattr(cell, "value", None)
        title = str(raw).strip() if raw is not None else ""
        if not title:
            continue
        if title in seen:
            if title not in duplicates:
                duplicates.append(title)
            continue
        seen.add(title)
        if title not in COLUMNS_BY_HEADER:
            unknowns.append(title)
            continue
        indexed.append((idx, COLUMNS_BY_HEADER[title]))

    if duplicates:
        raise invalid_file_error(
            "duplicate_columns",
            f"Cột {', '.join(duplicates)} bị lặp. Mỗi cột chỉ ghi một lần.",
            columns=duplicates,
        )
    if unknowns:
        raise invalid_file_error(
            "unknown_columns",
            f"Không nhận ra cột {', '.join(unknowns)}. Tải file mẫu để lấy đúng tên cột.",
            columns=unknowns,
        )
    missing = [h for h in REQUIRED_HEADERS if h not in seen]
    if "Ngày áp dụng giá mới" in seen and "Giá mới" not in seen and "Giá mới" not in missing:
        missing.append("Giá mới")
    if missing:
        raise invalid_file_error(
            "missing_columns",
            f"Thiếu cột {', '.join(missing)}. Tải file mẫu để lấy đúng tên cột.",
            columns=missing,
        )
    return indexed


def _is_cell_empty(parsed: ParsedCell) -> bool:
    if parsed.is_formula:
        return False
    if parsed.value is None:
        return True
    if isinstance(parsed.value, str) and parsed.value.strip() == "":
        return True
    return False


def read_import_workbook(uploaded_file) -> ParsedWorkbook:
    """Đọc file `.xlsx` đã tải lên và trả `ParsedWorkbook` (chưa chạm DB)."""
    if not openpyxl.xml.DEFUSEDXML:
        raise RuntimeError("defusedxml phải được bật cho openpyxl.")
    if uploaded_file is None:
        raise invalid_file_error("not_xlsx", NOT_XLSX_MSG)

    filename = (getattr(uploaded_file, "name", "") or "").strip()
    lower_name = filename.lower()
    if lower_name and not lower_name.endswith(".xlsx"):
        raise invalid_file_error("not_xlsx", NOT_XLSX_MSG)

    max_bytes = settings.ITEM_IMPORT_MAX_BYTES
    declared_size = getattr(uploaded_file, "size", None)
    if declared_size is not None and declared_size == 0:
        raise invalid_file_error("unreadable", UNREADABLE_MSG)
    if declared_size is not None and declared_size > max_bytes:
        raise _file_too_large_error()

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    raw_bytes = uploaded_file.read(max_bytes + 1)
    if not raw_bytes:
        raise invalid_file_error("unreadable", UNREADABLE_MSG)
    if len(raw_bytes) > max_bytes:
        raise _file_too_large_error()
    if not raw_bytes.startswith(ZIP_MAGIC):
        raise invalid_file_error("not_xlsx", NOT_XLSX_MSG)

    _check_zip_container(raw_bytes)
    file_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    wb_val = None
    wb_raw = None
    try:
        try:
            wb_val = openpyxl.load_workbook(
                io.BytesIO(raw_bytes), read_only=True, data_only=True, keep_links=False, keep_vba=False
            )
            wb_raw = openpyxl.load_workbook(
                io.BytesIO(raw_bytes), read_only=True, data_only=False, keep_links=False, keep_vba=False
            )
        except Exception as exc:
            raise invalid_file_error("unreadable", UNREADABLE_MSG) from exc

        if not wb_val.sheetnames:
            raise invalid_file_error("unreadable", UNREADABLE_MSG)
        sheet_name = SHEET_ITEMS if SHEET_ITEMS in wb_val.sheetnames else wb_val.sheetnames[0]
        ws_val = wb_val[sheet_name]
        ws_raw = wb_raw[sheet_name]

        scan_max_col = len(ALL_COLUMNS) + SCAN_EXTRA_COLS
        val_iter = ws_val.iter_rows(values_only=False, max_col=scan_max_col)
        raw_iter = ws_raw.iter_rows(values_only=False, max_col=scan_max_col)
        first_val = next(val_iter, None)
        first_raw = next(raw_iter, None)
        if first_val is None or first_raw is None:
            missing = list(REQUIRED_HEADERS)
            raise invalid_file_error(
                "missing_columns",
                f"Thiếu cột {', '.join(missing)}. Tải file mẫu để lấy đúng tên cột.",
                columns=missing,
            )

        indexed_columns = _parse_headers(first_val)
        headers = tuple(col.header for _, col in indexed_columns)
        max_col = max(idx for idx, _ in indexed_columns) + 1
        max_rows = settings.ITEM_IMPORT_MAX_ROWS
        scan_ceiling = max_rows * SCAN_ROWS_FACTOR + SCAN_ROWS_SLACK

        parsed_rows = []
        for row_number, (v_row, r_row) in enumerate(zip(val_iter, raw_iter), start=2):
            if row_number - 1 > scan_ceiling:
                raise _too_many_rows_error(max_rows)
            cells = {}
            for col_idx, column in indexed_columns:
                v_cell = v_row[col_idx] if col_idx < len(v_row) and col_idx < max_col else None
                r_cell = r_row[col_idx] if col_idx < len(r_row) and col_idx < max_col else None
                r_type = getattr(r_cell, "data_type", None)
                r_val = getattr(r_cell, "value", None)
                v_val = getattr(v_cell, "value", None)
                is_formula = r_type == "f" or (
                    isinstance(r_val, str)
                    and r_val.startswith("=")
                    and not getattr(r_cell, "quotePrefix", False)
                    and r_type != "s"
                )
                cells[column.key] = ParsedCell(
                    value=v_val,
                    is_formula=is_formula,
                    has_cached_value=(v_val is not None) if is_formula else True,
                )
            if all(_is_cell_empty(c) for c in cells.values()):
                continue
            parsed_rows.append(ParsedRow(row_number=row_number, cells=cells))
            if len(parsed_rows) > max_rows:
                raise _too_many_rows_error(max_rows)
    finally:
        if wb_val is not None:
            wb_val.close()
        if wb_raw is not None:
            wb_raw.close()

    if not parsed_rows:
        raise invalid_file_error("empty", EMPTY_FILE_MSG)

    return ParsedWorkbook(file_sha256=file_sha256, headers=headers, rows=tuple(parsed_rows))
