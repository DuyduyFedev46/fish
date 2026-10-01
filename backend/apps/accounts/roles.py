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
