"""
Bảng cột DUY NHẤT của file Excel mặt hàng (FISH-66, 02b §4.1, BR-DM-27/28).

Đây là danh sách tường minh, KHÔNG lặp qua field của model (bất biến 1: không bao giờ có cột giá mua, giá vốn,
chi phí phụ, lãi lỗ, mã lô, nhà cung cấp, tồn, ảnh). Thứ tự khi ghi là thứ tự trong `ALL_COLUMNS`.
"""
from dataclasses import dataclass

# Quyền xem file: model perm `catalog.view_item`; ba cột giá chỉ khi có quyền xem giá bán.
VIEW_ITEMS_PERM = "catalog.view_item"
VIEW_PRICES_PERM = "catalog.view_itemprice"

# Quyền nhập (D4, dùng ở lô 3): đủ cả 4. Khai ở đây để FE và BE dùng cùng một nguồn.
IMPORT_PERMS = (
    "catalog.add_item",
    "catalog.change_item",
    "catalog.add_itemprice",
    "catalog.change_itemprice",
)

# Kiểu ô
TEXT = "text"        # chữ (có chặn công thức)
INT = "int"          # số nguyên
FLAG = "flag"        # "Có" / "Không"
MONEY = "money"      # số nguyên đồng, định dạng #,##0
DATE = "date"        # dd/mm/yyyy


@dataclass(frozen=True)
class Column:
    key: str
    header: str
    kind: str
    width: int
    read_only: bool = False      # cột chỉ để xem, tô xám
    needs_price_perm: bool = False


ALL_COLUMNS = (
    Column("code", "Mã hàng", TEXT, 16),
    Column("name", "Tên", TEXT, 32),
    Column("item_group", "Nhóm hàng", TEXT, 20),
    Column("item_type", "Loại", TEXT, 18, read_only=True),
    Column("stock_uom", "Đơn vị", TEXT, 10, read_only=True),
    Column("is_active", "Đang kinh doanh", FLAG, 16),
    Column("shelf_life_in_days", "Hạn dùng mặc định (ngày)", INT, 14),
    Column("has_batch_no", "Quản lý theo lô", FLAG, 14),
    Column("has_expiry_date", "Có hạn dùng", FLAG, 12),
    Column("short_note", "Ghi chú ngắn", TEXT, 24),
    Column("spec", "Quy cách", TEXT, 24),
    Column("storage", "Bảo quản", TEXT, 24),
    Column("origin", "Nguồn hàng", TEXT, 24),
    Column("description", "Mô tả", TEXT, 40),
    Column("current_price", "Giá bán hiện hành", MONEY, 16, read_only=True, needs_price_perm=True),
    Column("new_price", "Giá mới", MONEY, 14, needs_price_perm=True),
    Column("new_price_from", "Ngày áp dụng giá mới", DATE, 18, needs_price_perm=True),
)


def columns_for(*, with_prices):
    """Bộ cột theo quyền: 17 cột khi có quyền xem giá bán, 14 cột khi không (BR-DM-28)."""
    return tuple(c for c in ALL_COLUMNS if with_prices or not c.needs_price_perm)
