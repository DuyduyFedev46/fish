"""
Nhóm lệnh AI và mức nhạy cảm: nguồn duy nhất cho các giá trị chuỗi (P8b Lô 1, đổi sang tiếng Anh ở Lô 4).

File này chỉ chứa hằng, không import gì. Giá trị là khoá lưu trong cấu hình AI (`AiConfigVersion.group_levels`)
và trong chỉ mục lệnh. Khoá cũ (`thu_mua`, `ban_hang`, `cskh`, `cao`, `trung_binh`, `thap`) còn nằm trong các phiên bản
đã ghim; `apps/ai/registry/legacy_ids.py` đổi chúng sang khoá mới khi đọc.
"""

# Nhóm lệnh (CommandSpec.group, khoá của AiConfigVersion.group_levels)
PURCHASING = "purchasing"
SALES = "sales"
CUSTOMER_SERVICE = "customer_service"

# Mức nhạy cảm của lệnh (CommandSpec.sensitivity)
SENSITIVITY_HIGH = "high"
SENSITIVITY_MEDIUM = "medium"
SENSITIVITY_LOW = "low"
