"""
Nhóm lệnh AI và mức nhạy cảm: nguồn duy nhất cho các giá trị chuỗi (P8b Lô 1).

File này chỉ chứa hằng, không import gì. Giá trị vẫn là tên cũ đang lưu trong cấu hình AI
(`AiConfigVersion.group_levels`) và snapshot chỉ mục lệnh; đổi sang tiếng Anh ở Lô 4.
"""

# Nhóm lệnh (CommandSpec.group, khoá của AiConfigVersion.group_levels)
PURCHASING = "thu_mua"
SALES = "ban_hang"
CUSTOMER_SERVICE = "cskh"

# Mức nhạy cảm của lệnh (CommandSpec.sensitivity)
SENSITIVITY_HIGH = "cao"
SENSITIVITY_MEDIUM = "trung_binh"
SENSITIVITY_LOW = "thap"
