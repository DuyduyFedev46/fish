"""
Danh mục phạm vi dữ liệu D1..D8 (Tầng 3, BR-PQ-33/34) — MỘT nguồn duy nhất, thay bảng phạm vi cố định cũ ở `capabilities/registry.py`.

Chỉ chứa dữ liệu thuần (không import model, không truy vấn). Lựa chọn do dự án định nghĩa, Chủ không gõ luật (S-8).
`rank` càng lớn càng rộng; mỗi đối tượng có đúng một lựa chọn `rank = 0` (hẹp nhất, dùng khi thiếu cấu hình, UC-6).

Đối tượng chỉ đọc: `invoices` (D2) theo `orders` của chính nhóm đó; `audit_log` (D8) suy từ việc `view_audit`.
Hai đối tượng này không lưu dòng nào ở `GroupDataScope`.

Mặc định (`defaults`) khớp migration `accounts/0015_seed_group_data_scopes` (test kiểm). Riêng `customers` mặc định của
Quản lý là `all` vì nhóm đang có quyền xem khách lúc migrate.
"""
from dataclasses import dataclass, field

from apps.accounts import roles

# Nhóm có dòng cấu hình mặc định. `owner` không lưu (luôn rộng nhất, S-5).
DEFAULT_GROUPS = (roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE)

FOLLOWS_ORDERS = "follows_orders"  # giá trị hiển thị của D2


@dataclass(frozen=True)
class ScopeOption:
    value: str
    label: str
    rank: int


@dataclass(frozen=True)
class ScopeObject:
    key: str
    label: str
    options: tuple
    customer_data: bool
    gate_perms: tuple  # nhóm đủ điều kiện khi có ÍT NHẤT MỘT permission này (quyền của chính nhóm)
    gate_capability: str | None  # mã việc ở registry mà tắt thì ô mờ; None khi gốc là quyền Tầng 1 ngoài registry
    gate_label: str  # chữ dùng trong "Nhóm không có quyền xem ..." khi không có việc gốc ở registry
    defaults: dict = field(default_factory=dict)
    read_only: bool = False
    derived_from: str | None = None
    # H1 (review 06/10): nhóm đủ điều kiện nhưng thiếu `full_perm` chỉ đóng góp tối đa `capped_value` (min theo rank).
    full_perm: str | None = None
    capped_value: str | None = None


def _defaults(manager, warehouse_staff, delivery_staff, customer_service):
    return {
        roles.MANAGER: manager,
        roles.WAREHOUSE_STAFF: warehouse_staff,
        roles.DELIVERY_STAFF: delivery_staff,
        roles.CUSTOMER_SERVICE: customer_service,
    }


ORDERS = ScopeObject(
    key="orders", label="Đơn hàng", customer_data=True,
    options=(
        ScopeOption("assigned_deliveries", "Đơn có phiếu giao gán cho tôi", 0),
        ScopeOption("assigned_or_confirmation", "Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận", 1),
        ScopeOption("all", "Tất cả đơn", 2),
    ),
    gate_perms=("sales.view_salesorder",), gate_capability="view_orders", gate_label="đơn hàng",
    defaults=_defaults("all", "all", "assigned_deliveries", "assigned_or_confirmation"),
)

INVOICES = ScopeObject(
    key="invoices", label="Hoá đơn bán", customer_data=True, options=(), read_only=True, derived_from="orders",
    gate_perms=("sales.view_salesinvoice",), gate_capability="view_sales_invoices", gate_label="hoá đơn bán",
)

DELIVERIES = ScopeObject(
    key="deliveries", label="Phiếu giao", customer_data=True,
    options=(
        ScopeOption("assigned", "Phiếu gán cho tôi", 0),
        ScopeOption("all", "Tất cả phiếu", 1),
    ),
    gate_perms=("delivery.view_deliverynote",), gate_capability=None, gate_label="phiếu giao",
    defaults=_defaults("all", "all", "assigned", "assigned"),
)

CONFIRMATION = ScopeObject(
    key="confirmation", label="Gọi xác nhận", customer_data=True,
    options=(
        ScopeOption("pending_or_called_recently", "Phiếu đang chờ gọi hoặc tôi đã gọi trong N ngày", 0),
        ScopeOption("all_pending", "Mọi phiếu chờ gọi", 1),
    ),
    gate_perms=("delivery.confirm_with_customer",), gate_capability="confirm_calls", gate_label="gọi xác nhận",
    defaults=_defaults("all_pending", "all_pending", "pending_or_called_recently", "pending_or_called_recently"),
)

RETURNS = ScopeObject(
    key="returns", label="Hàng hoàn", customer_data=True,
    options=(
        ScopeOption("assigned_deliveries", "Phiếu của phiếu giao gán cho tôi", 0),
        ScopeOption("all", "Tất cả phiếu", 1),
    ),
    gate_perms=("inventory.view_returntostock",), gate_capability=None, gate_label="hàng hoàn",
    defaults=_defaults("all", "all", "assigned_deliveries", "assigned_deliveries"),
)

RECEIPTS = ScopeObject(
    key="receipts", label="Phiếu nhập", customer_data=False,
    options=(
        ScopeOption("created_by_me_today", "Do tôi tạo trong ngày", 0),
        ScopeOption("created_by_me", "Do tôi tạo", 1),
        ScopeOption("all", "Tất cả phiếu", 2),
    ),
    gate_perms=("purchasing.view_purchasereceipt", "purchasing.add_purchasereceipt"),
    gate_capability="receive", gate_label="phiếu nhập",
    defaults=_defaults("all", "all", "all", "all"),
)

CUSTOMERS = ScopeObject(
    key="customers", label="Khách hàng", customer_data=True,
    options=(
        ScopeOption("none", "Không xem", 0),
        ScopeOption("assigned_deliveries", "Khách của phiếu giao gán cho tôi (trong cửa sổ)", 1),
        ScopeOption("all", "Tất cả khách", 2),
    ),
    gate_perms=("sales.view_customer_list", "sales.view_customer"),
    gate_capability="view_customers", gate_label="khách hàng",
    full_perm="sales.view_customer_list", capped_value="assigned_deliveries",
    # Quản lý đang có `view_customer_list` lúc migrate -> all; NV giao đi qua phiếu giao; còn lại không xem.
    defaults=_defaults("all", "none", "assigned_deliveries", "none"),
)

AUDIT_LOG = ScopeObject(
    key="audit_log", label="Nhật ký hoạt động", customer_data=False, read_only=True,
    options=(
        ScopeOption("none", "Không xem", 0),
        ScopeOption("all", "Tất cả", 1),
    ),
    gate_perms=("accounts.view_auditlog",), gate_capability="view_audit", gate_label="nhật ký hoạt động",
)

# Thứ tự D1..D8 (contract 02b §2.2).
OBJECTS = (ORDERS, INVOICES, DELIVERIES, CONFIRMATION, RETURNS, RECEIPTS, CUSTOMERS, AUDIT_LOG)
BY_KEY = {obj.key: obj for obj in OBJECTS}


def ranked_options(obj):
    """Các lựa chọn có rank của đối tượng; đối tượng suy ra (D2) dùng lựa chọn của đối tượng gốc."""
    if obj.options:
        return obj.options
    return BY_KEY[obj.derived_from].options


def stored_objects():
    """Sáu đối tượng Chủ sửa được và được lưu ở `GroupDataScope` (không gồm D2, D8)."""
    return tuple(obj for obj in OBJECTS if not obj.read_only)


def narrowest_value(obj):
    """Giá trị `rank = 0` của đối tượng (dùng khi thiếu cấu hình hoặc giá trị lưu không hợp lệ)."""
    return min(ranked_options(obj), key=lambda option: option.rank).value


def widest_value(obj):
    return max(ranked_options(obj), key=lambda option: option.rank).value


def rank_of(obj, value):
    """Rank của `value`, hoặc None nếu không thuộc lựa chọn của đối tượng."""
    for option in ranked_options(obj):
        if option.value == value:
            return option.rank
    return None


def valid_or_narrowest(obj, value):
    """`value` nếu là lựa chọn hợp lệ của đối tượng, không thì giá trị rank 0 (thiếu dòng cấu hình hoặc giá trị hỏng)."""
    return value if rank_of(obj, value) is not None else narrowest_value(obj)
