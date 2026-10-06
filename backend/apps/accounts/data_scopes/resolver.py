"""
Hàm phân giải phạm vi dữ liệu của một người (BR-PQ-34, UC-6, S-5). 02b §1.3.

Luật:
1. Superuser hoặc thuộc nhóm `owner`: giá trị rộng nhất của mọi đối tượng (`via_group` = `owner`, hoặc None với superuser).
2. Với mỗi đối tượng chỉ xét **nhóm đủ điều kiện**: nhóm của người đó có ÍT NHẤT MỘT permission trong `gate_perms`
   (quyền của chính *nhóm*, không phải quyền gán trực tiếp). Lấy giá trị `rank` lớn nhất. Lý do: chặn rò chéo nhóm. Người
   K+G, Chủ tắt "Xem đơn" của K nhưng D1 của K vẫn lưu "Tất cả" (Q-7): nếu không lọc theo nhóm đủ điều kiện, người này thấy
   mọi đơn nhờ quyền xem đơn của G cộng phạm vi "Tất cả" của K.
3. Không nhóm đủ điều kiện (kể cả người không nhóm, quyền gán trực tiếp), hoặc nhóm thiếu dòng cấu hình, hoặc giá trị lưu
   không còn là lựa chọn hợp lệ: giá trị `rank = 0` (hẹp nhất).
4. D2 `invoices` lấy giá trị D1 `orders` CỦA CHÍNH nhóm có quyền xem hoá đơn. D8 `audit_log` là `all` khi có nhóm đủ điều kiện.
5. Nhớ trên đối tượng user (`_data_scope_cache`, cùng cách Django nhớ `_perm_cache`): mỗi request nạp user mới nên đổi cấu hình
   có hiệu lực từ request kế tiếp (BR-PQ-36). `overrides` (xem trước, Lô 5) thì KHÔNG nhớ.
6. Tối đa 3 truy vấn cho cả 8 đối tượng: nhóm của user, permission cổng của các nhóm đó, `GroupDataScope` của các nhóm đó.

Hàm này chỉ ĐỌC cấu hình; chưa có chỗ đọc phạm vi nào ở màn nghiệp vụ gọi nó (PV-03 → PV-07).
"""
from dataclasses import dataclass

from django.contrib.auth.models import Permission

from apps.accounts import roles
from apps.accounts.models import GroupDataScope

from . import catalog

CACHE_ATTR = "_data_scope_cache"


@dataclass(frozen=True)
class Resolved:
    value: str
    via_group: str | None


def _role_index(name):
    return roles.ALL_ROLES.index(name) if name in roles.ALL_ROLES else len(roles.ALL_ROLES)


def _gate_codenames():
    return {perm.split(".", 1)[1] for obj in catalog.OBJECTS for perm in obj.gate_perms}


def _narrowest():
    result = {obj.key: Resolved(catalog.narrowest_value(obj), None) for obj in catalog.OBJECTS}
    return result


def _widest(via_group):
    return {obj.key: Resolved(catalog.widest_value(obj), via_group) for obj in catalog.OBJECTS}


def _load(user, overrides):
    """(danh sách (group_id, name) theo thứ tự vai, {group_id: {perm đầy đủ}}, {group_id: {key: value}})."""
    groups = sorted(user.groups.values_list("pk", "name"), key=lambda row: (_role_index(row[1]), row[1]))
    ids = [pk for pk, _ in groups]
    held = {pk: set() for pk in ids}
    stored = {pk: {} for pk in ids}
    if ids:
        rows = Permission.objects.filter(group__in=ids, codename__in=_gate_codenames()).values_list(
            "group__pk", "content_type__app_label", "codename")
        for group_id, app_label, codename in rows:
            held[group_id].add(f"{app_label}.{codename}")
        for group_id, key, value in GroupDataScope.objects.filter(group_id__in=ids).values_list(
                "group_id", "object_key", "value"):
            stored[group_id][key] = value
    for group_id, changed in (overrides or {}).items():
        if group_id in stored:
            stored[group_id].update(changed)
    return groups, held, stored


def _resolve_object(obj, groups, held, stored):
    best = None  # (rank, Resolved)
    for group_id, name in groups:
        if not set(obj.gate_perms) & held[group_id]:
            continue  # nhóm không đủ điều kiện: giá trị đã lưu không được tính
        if obj.key == "audit_log":
            value = "all"
        elif obj.derived_from:
            source = catalog.BY_KEY[obj.derived_from]
            value = catalog.valid_or_narrowest(source, stored[group_id].get(source.key))
        else:
            value = catalog.valid_or_narrowest(obj, stored[group_id].get(obj.key))
        rank = catalog.rank_of(obj, value)
        if best is None or rank > best[0]:  # lớn hơn hẳn mới thay: hoà thì giữ nhóm đứng trước theo thứ tự vai
            best = (rank, Resolved(value, name))
    return best[1] if best else Resolved(catalog.narrowest_value(obj), None)


def resolve_data_scopes(user, *, overrides=None) -> dict:
    """{key đối tượng: Resolved(value, via_group)} cho cả 8 đối tượng.

    `overrides` = `{group_id: {key: value}}`: giá trị giả định để xem trước tác động (không ghi, không nhớ)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return _narrowest()
    if overrides is None:
        cached = getattr(user, CACHE_ATTR, None)
        if cached is not None:
            return cached
    if user.is_superuser:
        result = _widest(None)
    else:
        groups, held, stored = _load(user, overrides)
        if any(name == roles.OWNER for _, name in groups):
            result = _widest(roles.OWNER)
        else:
            result = {obj.key: _resolve_object(obj, groups, held, stored) for obj in catalog.OBJECTS}
    if overrides is None:
        setattr(user, CACHE_ATTR, result)
    return result


def resolve_data_scope(user, key) -> str:
    """Giá trị phạm vi của `user` cho đối tượng `key` (KeyError nếu `key` không có trong catalog)."""
    return resolve_data_scopes(user)[key].value
