"""
Ghi file xlsx (xuất danh sách, file mẫu) — hàm thuần, không đụng request hay DB (FISH-66, 02b §4.1, §6.4).

Chặn công thức độc (S3-AC10): mọi ô chữ luôn là ô chữ (`data_type = "s"`); chuỗi bắt đầu bằng `= + - @`, tab, CR, LF
thì đặt thêm `quotePrefix` để Excel giữ ô là chữ kể cả khi người dùng bấm vào sửa. Không thêm dấu `'` vào giá trị,
nên tải về rồi nhập lại không đổi chữ.
"""
import io

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .columns import DATE, FLAG, INT, MONEY, TEXT

SHEET_ITEMS = "Hàng bán"
SHEET_GUIDE = "Hướng dẫn"
CREATOR = "Cá Về"
DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")
MAX_CELL_CHARS = 32767  # giới hạn một ô của Excel
GREY_FILL = PatternFill("solid", fgColor="E7E6E6")
FLAG_YES, FLAG_NO = "Có", "Không"

GUIDE_LINES = (
    "Cách đọc file này",
    "Mỗi dòng là một mặt hàng. Đừng đổi tên các cột ở dòng đầu tiên.",
    "Cột tô xám (Loại, Đơn vị, Giá bán hiện hành) chỉ để xem. Sửa các cột này không đổi gì trong hệ thống.",
    "Ô chữ để trống nghĩa là giữ nguyên chữ hiện có. File này không xoá được chữ đã nhập.",
    "Muốn đổi giá bán, ghi vào cột Giá mới (số nguyên đồng) và Ngày áp dụng giá mới (dd/mm/yyyy). Để trống ngày thì áp dụng từ hôm nay.",
    "Cột Đang kinh doanh, Quản lý theo lô, Có hạn dùng ghi Có hoặc Không.",
    "File chỉ có thông tin mặt hàng và giá bán, không có thông tin mua hàng hay tồn kho.",
)


def write_text_cell(cell, value):
    """Ghi chữ vào ô, luôn là ô chữ, chặn công thức độc."""
    text = "" if value is None else str(value)
    text = ILLEGAL_CHARACTERS_RE.sub("", text)[:MAX_CELL_CHARS]
    if text == "":
        cell.value = None
        return
    cell.value = text
    cell.data_type = "s"  # openpyxl tự coi chuỗi bắt đầu bằng "=" là công thức; ép về chữ
    if text.startswith(DANGEROUS_PREFIXES):
        cell.quotePrefix = True


def _write_value(cell, column, value):
    if column.kind == TEXT:
        write_text_cell(cell, value)
        return
    if column.kind == MONEY:
        cell.number_format = "#,##0"
    elif column.kind == DATE:
        cell.number_format = "dd/mm/yyyy"
    if value is None:
        return
    if column.kind == FLAG:
        cell.value = FLAG_YES if value else FLAG_NO
    elif column.kind in (INT, MONEY):
        cell.value = int(value)
    elif column.kind == DATE:
        cell.value = value


def build_items_workbook(columns, rows):
    """`rows`: danh sách dict `{khoá cột: giá trị Python}`. Trả bytes xlsx. Cột thiếu trong dict = ô trống."""
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_ITEMS
    bold = Font(bold=True)
    for index, column in enumerate(columns, start=1):
        head = ws.cell(row=1, column=index, value=column.header)
        head.font = bold
        head.alignment = Alignment(wrap_text=True, vertical="center")
        if column.read_only:
            head.fill = GREY_FILL
        ws.column_dimensions[head.column_letter].width = column.width
    ws.freeze_panes = "A2"

    last_row = len(rows) + 1
    for r, row in enumerate(rows, start=2):
        for c, column in enumerate(columns, start=1):
            cell = ws.cell(row=r, column=c)
            _write_value(cell, column, row.get(column.key))
            if column.read_only:
                cell.fill = GREY_FILL
    # Cột cờ có danh sách chọn Có/Không (mẫu nhập, dòng thêm tay).
    flag_validation = DataValidation(type="list", formula1=f'"{FLAG_YES},{FLAG_NO}"', allow_blank=True)
    ws.add_data_validation(flag_validation)
    for c, column in enumerate(columns, start=1):
        letter = ws.cell(row=1, column=c).column_letter
        if column.kind == FLAG:
            flag_validation.add(f"{letter}2:{letter}{max(last_row, 1001)}")

    guide = wb.create_sheet(SHEET_GUIDE)
    for r, line in enumerate(GUIDE_LINES, start=1):
        cell = guide.cell(row=r, column=1)
        write_text_cell(cell, line)
        if r == 1:
            cell.font = bold
    guide.column_dimensions["A"].width = 110

    wb.properties.creator = CREATOR  # không ghi tên người tải vào thuộc tính file
    wb.properties.lastModifiedBy = CREATOR
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
