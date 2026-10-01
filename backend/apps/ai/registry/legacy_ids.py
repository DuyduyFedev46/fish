"""
Khoá AI cũ (trước P8b Lô 4) -> khoá tiếng Anh (R5).

`AiConfigVersion` và `AiPolicyVersion` là append-only nên các phiên bản đã ghim vẫn mang khoá tiếng Việt. Mọi chỗ ĐỌC các
phiên bản đó và mọi đường GHI nhận khoá cũ đều đi qua các hàm ở đây để tính ra đúng mức như khoá mới. Các hàm thuần:
không sửa đối tượng truyền vào, chịu được `None`. Khi cả khoá cũ lẫn khoá mới cùng có, khoá mới thắng.

File chỉ chứa dữ liệu và hàm thuần, không import model, để import ở đâu cũng không vòng. GIỮ VĨNH VIỄN (P8b Lô 5): phiên bản
cấu hình/chính sách AI đã ghim vẫn mang khoá cũ nên còn phải đọc được.
"""

# id lệnh AI cũ -> mới (chỉ lệnh nhập lô đổi id ở Lô 4; hàm view `nhap_lo` đổi thành `receive_batches`).
LEGACY_COMMAND_IDS = {
    "purchasing.purchasereceipt.nhap_lo": "purchasing.purchasereceipt.receive_batches",
}

# Khoá trần/ngưỡng dạng ngắn (đoạn cuối của id lệnh) cũ -> mới.
LEGACY_COMMAND_ALIASES = {
    "nhap_lo": "receive_batches",
}

# Nhóm lệnh AI cũ -> mới (khoá của `group_levels`, `AiAction`/`CommandSpec.group`).
LEGACY_GROUP_KEYS = {
    "thu_mua": "purchasing",
    "ban_hang": "sales",
    "cskh": "customer_service",
}

# Mức nhạy cảm cũ -> mới (CommandSpec.sensitivity).
LEGACY_SENSITIVITY = {
    "cao": "high",
    "trung_binh": "medium",
    "thap": "low",
}

# Tên Group (vai) cũ -> mới. Dùng cho `AiAction.assignee_group` cũ và cho `preview_group_rename` (xem trước migration
# accounts/0013 trên môi trường chưa chạy nó). Không dùng để nhận tên cũ ở đường ghi: đã gỡ ở P8b Lô 5.
# Tên Group đang dùng trong code vẫn chỉ ở `apps.accounts.roles`.
LEGACY_ASSIGNEE_GROUPS = {
    "chu": "owner",
    "quan_ly": "manager",
    "nv_kho": "warehouse_staff",
    "nv_giao": "delivery_staff",
    "cskh": "customer_service",
}


def normalize_command_id(command_id):
    return LEGACY_COMMAND_IDS.get(command_id, command_id)


def normalize_group_key(group_key):
    return LEGACY_GROUP_KEYS.get(group_key, group_key)


def normalize_sensitivity(value):
    return LEGACY_SENSITIVITY.get(value, value)


def _normalize_key(key):
    key = LEGACY_COMMAND_IDS.get(key, key)
    return LEGACY_COMMAND_ALIASES.get(key, key)


def _normalize_mapping(mapping, normalize_key):
    """Đổi khoá của dict theo `normalize_key`; khoá mới (đã có sẵn) thắng khoá cũ trùng đích."""
    if not isinstance(mapping, dict):
        return {}
    out = {}
    for key, value in mapping.items():
        new_key = normalize_key(key)
        if new_key != key and new_key in mapping:
            continue  # khoá mới đã có trong nguồn: giữ giá trị của khoá mới
        out[new_key] = value
    return out


def normalize_command_keys(mapping):
    """`overrides`, `limits`, `caps`: khoá là id lệnh đầy đủ hoặc đoạn cuối (`nhap_lo`)."""
    return _normalize_mapping(mapping, _normalize_key)


def normalize_group_levels(mapping):
    """`group_levels`: khoá là nhóm lệnh."""
    return _normalize_mapping(mapping, normalize_group_key)


def has_legacy_keys(group_levels=None, overrides=None, limits=None, caps=None):
    """Có khoá cũ nào trong các cấu hình này không (dùng cho migration để biết cần thêm phiên bản mới)."""
    if isinstance(group_levels, dict) and any(k in LEGACY_GROUP_KEYS for k in group_levels):
        return True
    for mapping in (overrides, limits, caps):
        if isinstance(mapping, dict) and any(_normalize_key(k) != k for k in mapping):
            return True
    return False
