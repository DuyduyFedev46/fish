"""
Kiểm và ghép địa chỉ giao có cấu trúc (STA-02, BR-BH-29/34). Thuần hàm, không log (bất biến 9).
"""
from dataclasses import dataclass

from . import catalog

STREET_MAX = 200


@dataclass(frozen=True)
class StructuredAddress:
    scheme: str
    province_code: str
    district_code: str  # "" ở kiểu mới
    ward_code: str
    street: str
    full_text: str


def compose_full_address(street, ward, district, province) -> str:
    """Số nhà, phường/xã, [quận/huyện], tỉnh. `district` là None ở kiểu mới."""
    parts = [street, ward.name]
    if district is not None:
        parts.append(district.name)
    parts.append(province.name)
    return ", ".join(parts)


def parse_address_parts(raw) -> tuple[StructuredAddress | None, dict[str, str]]:
    """Trả `(địa chỉ, {})` hoặc `(None, lỗi theo ô)`. Không ném. Khoá lỗi = khoá request."""
    if not isinstance(raw, dict):
        return None, {"delivery_address": "Chọn địa chỉ giao hàng."}

    scheme = raw.get("scheme")
    if scheme not in catalog.SCHEMES:
        return None, {"scheme": "Chọn kiểu địa chỉ."}

    errors: dict[str, str] = {}
    legacy = scheme == catalog.SCHEME_LEGACY

    province = catalog.get_province(scheme, raw.get("province_code"))
    if province is None:
        errors["province_code"] = "Chọn tỉnh/thành phố."

    district = None
    district_raw = raw.get("district_code")
    if legacy:
        if province is not None:
            district = catalog.get_district(scheme, district_raw)
            if district is not None and district.parent_code != province.code:
                district = None
        if district is None:
            errors["district_code"] = "Chọn quận/huyện."
    elif district_raw not in (None, ""):
        errors["district_code"] = "Địa chỉ mới không có quận/huyện."

    ward = None
    parent = district if legacy else province
    if parent is not None:
        ward = catalog.get_ward(scheme, raw.get("ward_code"))
        if ward is not None and ward.parent_code != parent.code:
            ward = None
    if ward is None:
        errors["ward_code"] = "Chọn phường/xã."

    street_raw = raw.get("street")
    street = " ".join(street_raw.split()) if isinstance(street_raw, str) else ""
    if not street or len(street) > STREET_MAX:
        errors["street"] = f"Nhập số nhà, tên đường (tối đa {STREET_MAX} ký tự)."

    if errors:
        return None, errors
    return (
        StructuredAddress(
            scheme=scheme,
            province_code=province.code,
            district_code=district.code if district else "",
            ward_code=ward.code,
            street=street,
            full_text=compose_full_address(street, ward, district, province),
        ),
        {},
    )
