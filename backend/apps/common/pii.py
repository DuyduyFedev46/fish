"""
Tiện ích xử lý dữ liệu cá nhân (PII) — Cá Về.
Bảo vệ Bất biến 9: không rò rỉ SĐT, tên, địa chỉ hoặc số tài khoản khách hàng.
"""
import re


def normalize_phone(phone: str) -> str:
    """
    Chuẩn hoá số điện thoại:
    - Bỏ khoảng trắng, dấu chấm, dấu gạch ngang, ngoặc.
    - Chuyển đầu số +84 hoặc 84 thành 0.
    """
    if not phone:
        return ""
    digits = re.sub(r"[^\d+]", "", str(phone))
    if digits.startswith("+84"):
        digits = "0" + digits[3:]
    elif digits.startswith("84") and len(digits) >= 11:
        digits = "0" + digits[2:]
    return re.sub(r"\D", "", digits)


def mask_phone(phone: str) -> str:
    """
    Che số điện thoại hiển thị: giữ 2 số đầu + 3 số cuối -> dạng '09xx xxx 123'.
    Nếu số quá ngắn (< 5 chữ số), trả về chuỗi sao '***'.
    """
    norm = normalize_phone(phone)
    if len(norm) < 5:
        return "***"
    prefix = norm[:2]
    suffix = norm[-3:]
    return f"{prefix}xx xxx {suffix}"


def mask_phone_last4(phone: str) -> str:
    """
    Che SĐT trên tem in (TEM-01): chỉ giữ 4 số cuối -> 'xxxxxx4567'.
    Chuẩn hoá trước; rỗng hoặc dưới 4 chữ số -> '***'. Không thay `mask_phone` (AC4).
    """
    norm = normalize_phone(phone)
    if len(norm) < 4:
        return "***"
    return f"xxxxxx{norm[-4:]}"


def has_long_digit_run(text: str, min_len: int = 9) -> bool:
    """
    Kiểm tra xem chuỗi có chứa dãy chữ số dài (>= min_len chữ số) hay không,
    kể cả trường hợp các chữ số bị ngăn cách bởi khoảng trắng, dấu chấm, gạch ngang.
    Dùng để chặn rò rỉ số tài khoản hoặc SĐT khách trong ghi chú cuộc gọi (BR-GH-19).
    """
    if not text:
        return False
    # Tìm các đoạn liên tiếp gồm chữ số và ký tự ngăn cách phổ biến
    cleaned = re.sub(r"[\s.\-_/]", "", str(text))
    return bool(re.search(rf"\d{{{min_len},}}", cleaned))
