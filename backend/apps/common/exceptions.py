"""Lỗi nghiệp vụ dùng chung — service layer raise cái này khi vi phạm business rule."""
import re

BR_CODE_RE = re.compile(r"BR-[A-Z]{2}-\d{2}")
DEFAULT_CODE = "BUSINESS_ERROR"


class BusinessError(Exception):
    """
    Vi phạm một business rule (BR-*). Tầng API bắt và trả HTTP 400
    `{"detail": <thông điệp>, "code": <mã>}` (quy ước contract, S3).

    `code`: truyền tường minh (vd `code="BR-PQ-14"`); bỏ trống thì lấy mã BR đầu
    tiên trong thông điệp; không có thì `"BUSINESS_ERROR"`.
    """

    http_status = 400  # lớp con cho vi phạm thẩm quyền có thể đặt 403 (vd BR-PQ-17)

    def __init__(self, message="", code=None):
        super().__init__(message)
        if code is None:
            found = BR_CODE_RE.search(str(message))
            code = found.group(0) if found else DEFAULT_CODE
        self.code = code
