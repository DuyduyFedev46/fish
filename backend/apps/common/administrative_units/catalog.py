"""
Danh mục đơn vị hành chính (STA-01). Đọc 2 file JSON tĩnh trong `data/` một lần mỗi tiến trình; không vào DB, không log.

Hai kiểu địa chỉ: `current` (tỉnh -> phường/xã, từ 01/07/2025) và `legacy` (tỉnh -> quận/huyện -> phường/xã).
Cùng một mã có thể là hai đơn vị khác nhau ở hai kiểu nên mọi hàm đều nhận `scheme`.
"""
import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SCHEME_CURRENT = "current"
SCHEME_LEGACY = "legacy"
SCHEMES = (SCHEME_CURRENT, SCHEME_LEGACY)

_DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class Unit:
    code: str
    name: str
    parent_code: str | None = None


def fold_text(value: str) -> str:
    """Chữ thường, bỏ dấu (đ -> d) để sắp xếp ổn định."""
    text = unicodedata.normalize("NFD", value.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn").lower()


@lru_cache(maxsize=None)
def _index(scheme: str) -> dict:
    with open(_DATA_DIR / f"{scheme}.json", encoding="utf-8") as handle:
        raw = json.load(handle)
    provinces = {p["code"]: Unit(p["code"], p["name"], None) for p in raw["provinces"]}
    districts = {d["code"]: Unit(d["code"], d["name"], d["province_code"]) for d in raw.get("districts", [])}
    ward_parent_key = "province_code" if scheme == SCHEME_CURRENT else "district_code"
    wards = {w["code"]: Unit(w["code"], w["name"], w[ward_parent_key]) for w in raw["wards"]}

    def group(units: dict) -> dict:
        grouped: dict = {}
        for unit in units.values():
            grouped.setdefault(unit.parent_code, []).append(unit)
        for members in grouped.values():
            members.sort(key=lambda u: (fold_text(u.name), u.code))
        return grouped

    return {
        "provinces": provinces,
        "districts": districts,
        "wards": wards,
        "districts_by_parent": group(districts),
        "wards_by_parent": group(wards),
    }


def _check_scheme(scheme: str) -> None:
    if scheme not in SCHEMES:
        raise ValueError("scheme không hợp lệ")


def provinces(scheme: str) -> list[Unit]:
    _check_scheme(scheme)
    return sorted(_index(scheme)["provinces"].values(), key=lambda u: u.code)


def districts(scheme: str, province_code: str) -> list[Unit]:
    """Chỉ có ở kiểu cũ; kiểu mới trả danh sách rỗng."""
    _check_scheme(scheme)
    return list(_index(scheme)["districts_by_parent"].get(province_code, []))


def wards(scheme: str, parent_code: str) -> list[Unit]:
    """Cha là tỉnh ở kiểu mới, là huyện ở kiểu cũ."""
    _check_scheme(scheme)
    return list(_index(scheme)["wards_by_parent"].get(parent_code, []))


def get_province(scheme: str, code) -> Unit | None:
    _check_scheme(scheme)
    return _index(scheme)["provinces"].get(code) if isinstance(code, str) else None


def get_district(scheme: str, code) -> Unit | None:
    _check_scheme(scheme)
    return _index(scheme)["districts"].get(code) if isinstance(code, str) else None


def get_ward(scheme: str, code) -> Unit | None:
    _check_scheme(scheme)
    return _index(scheme)["wards"].get(code) if isinstance(code, str) else None
