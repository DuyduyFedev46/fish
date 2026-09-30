"""
Tên Group (vai) dùng trong code: nguồn duy nhất, không rải chuỗi ở nơi khác (P8b Lô 1).

File này chỉ chứa hằng, không import gì, để `apps/common` và mọi app import được mà không vòng.
Giá trị là tên Group đang lưu trong DB (`auth_group.name`); đổi sang tiếng Anh ở Lô 4 bằng
cách đổi giá trị tại đây cùng migration đổi tên Group.
"""

OWNER = "chu"
MANAGER = "quan_ly"
WAREHOUSE_STAFF = "nv_kho"
DELIVERY_STAFF = "nv_giao"
CUSTOMER_SERVICE = "cskh"

# Thứ tự vai cố định (dùng cho sắp xếp danh sách Group trả ra API).
ALL_ROLES = (OWNER, MANAGER, WAREHOUSE_STAFF, DELIVERY_STAFF, CUSTOMER_SERVICE)
