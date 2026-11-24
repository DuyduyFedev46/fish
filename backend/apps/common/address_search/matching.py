"""
So khớp tên tỉnh/[quận, huyện]/phường, xã từ VietMap với danh mục tĩnh Cá Về (SHOP-3-04, 02b §1.9b.4).

Thuần hàm, không truy vấn cơ sở dữ liệu, không ghi log. Chỉ trả gợi ý khi khớp ĐÚNG 1 đơn vị ở mỗi cấp.
"""
from typing import Any

from apps.common.administrative_units import catalog


def _normalize_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    collapsed = " ".join(value.split())
    return catalog.fold_text(collapsed) if collapsed else ""


def _match_single(units: list[catalog.Unit], raw_name: Any) -> catalog.Unit | None:
    target = _normalize_name(raw_name)
    if not target:
        return None
    matches = [unit for unit in units if _normalize_name(unit.name) == target]
    return matches[0] if len(matches) == 1 else None


def match_administrative_unit(
    *,
    scheme: str,
    city: str,
    district: str,
    ward: str,
) -> dict[str, str | None] | None:
    """
    Đối chiếu tên hành chính từ Place v4 sang mã danh mục Cá Về theo `scheme` (`current` | `legacy`).
    Không dùng `ward_id`/`city_id` của VietMap (chưa xác minh khớp GSO, 02b §1.9b.4).
    """
    if scheme not in catalog.SCHEMES:
        return None

    province = _match_single(catalog.provinces(scheme), city)
    if province is None:
        return None

    matched_district: catalog.Unit | None = None
    if scheme == catalog.SCHEME_LEGACY:
        matched_district = _match_single(catalog.districts(scheme, province.code), district)
        if matched_district is None:
            return None
        parent_code = matched_district.code
    else:
        parent_code = province.code

    matched_ward = _match_single(catalog.wards(scheme, parent_code), ward)
    if matched_ward is None:
        return None

    return {
        "scheme": scheme,
        "province_code": province.code,
        "district_code": matched_district.code if matched_district is not None else None,
        "ward_code": matched_ward.code,
        "ward_name": matched_ward.name,
    }
