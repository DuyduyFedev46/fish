"""
Tên Group (vai) dùng trong code: nguồn duy nhất, không rải chuỗi ở nơi khác (P8b Lô 1, đổi sang tiếng Anh ở Lô 4).

File này chỉ chứa hằng, không import gì, để `apps/common` và mọi app import được mà không vòng.
Giá trị là tên Group đang lưu trong DB (`auth_group.name`); migration `accounts/0013_rename_groups_to_english`
đổi tên Group GIỮ NGUYÊN id nên quyền và thành viên đi theo.
"""

OWNER = "owner"
MANAGER = "manager"
WAREHOUSE_STAFF = "warehouse_staff"
DELIVERY_STAFF = "delivery_staff"
CUSTOMER_SERVICE = "customer_service"

# Thứ tự vai cố định (dùng cho sắp xếp danh sách Group trả ra API).
ALL_ROLES = (OWNER, MANAGER, WAREHOUSE_STAFF, DELIVERY_STAFF, CUSTOMER_SERVICE)

# Tên Group cũ (trước Lô 4) -> tên mới. Mọi đường GHI (gán nhóm cho nhân viên, tạo nhân viên) vẫn nhận tên cũ cho client
# cũ còn mở trong lúc triển khai, rồi chuẩn hoá sang tên mới TRƯỚC khi lưu (R5). Gỡ cùng route cũ ở Lô 5.
LEGACY_ROLE_NAMES = {
    "chu": OWNER,
    "quan_ly": MANAGER,
    "nv_kho": WAREHOUSE_STAFF,
    "nv_giao": DELIVERY_STAFF,
    "cskh": CUSTOMER_SERVICE,
}


def normalize_role_name(name):
    """Tên Group cũ -> tên mới; tên mới và tên lạ giữ nguyên (để nơi gọi tự báo lỗi tên không tồn tại)."""
    return LEGACY_ROLE_NAMES.get(name, name)
