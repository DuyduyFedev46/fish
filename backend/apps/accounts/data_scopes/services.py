"""
Mô tả phạm vi dữ liệu của nhóm cho màn Phân quyền (W3i/W3h), PV-02, 02b §2.1–§2.2.

Lô 2 chỉ ĐỌC: dựng `data_scopes` (8 dòng), `data_scope_values` (6 đối tượng sửa được) và chuỗi `scopes` cũ từ cấu hình đã lưu.
Hàm ghi (kiểm, xem trước, áp, AuditLog, khoá lạc quan) thuộc Lô 5 (PV-08..PV-10).
Mọi chữ trả ra là mã và nhãn cố định của dự án, không dữ liệu khách, không giá vốn (bất biến 1, 9).
"""
from apps.accounts import roles
from apps.accounts.capabilities import registry
from apps.accounts.models import GroupAccessConfig, GroupDataScope

from . import catalog

OWNER_NOTE = "Chủ luôn thấy tất cả"
INVOICES_NOTE = "Theo Đơn hàng"
DEFAULT_VERSION = 1

# Chuỗi `scopes` cũ (FE tới Lô 6): giữ nguyên nhãn đang dùng, dựng từ cấu hình thay vì bảng cố định.
LEGACY_ORDERS = {
    "all": "Tất cả",
    "assigned_deliveries": "Được gán",
    "assigned_or_confirmation": "Được gán hoặc trong phạm vi gọi xác nhận",
}
LEGACY_DELIVERIES = {"all": "Tất cả", "assigned": "Được gán"}
LEGACY_ALL_CUSTOMERS = "Tất cả khách"
LEGACY_ASSIGNED = "Được gán"
LEGACY_NONE = "Không xem"
CUSTOMER_LIST_PERM = "sales.view_customer_list"
CUSTOMER_PERM = "sales.view_customer"


def load_stored(group_ids) -> dict:
    """{group_id: {object_key: value}} — một truy vấn cho nhiều nhóm."""
    stored = {pk: {} for pk in group_ids}
    for group_id, key, value in GroupDataScope.objects.filter(group_id__in=list(group_ids)).values_list(
            "group_id", "object_key", "value"):
        stored[group_id][key] = value
    return stored


def load_versions(group_ids) -> dict:
    """{group_id: row_version} — nhóm chưa có dòng cấu hình coi như phiên bản 1."""
    versions = {pk: DEFAULT_VERSION for pk in group_ids}
    for group_id, version in GroupAccessConfig.objects.filter(group_id__in=list(group_ids)).values_list(
            "group_id", "row_version"):
        versions[group_id] = version
    return versions


def version_string(row_version) -> str:
    return str(row_version)


def _is_owner(group) -> bool:
    return group.name == roles.OWNER


def _eligible(obj, held) -> bool:
    return bool(set(obj.gate_perms) & held)


def _stored_value(group, obj, stored):
    """Giá trị phạm vi của nhóm với đối tượng sửa được: nhóm Chủ luôn rộng nhất, còn lại theo cấu hình đã lưu."""
    if _is_owner(group):
        return catalog.widest_value(obj)
    return catalog.valid_or_narrowest(obj, stored.get(obj.key))


def data_scope_values(group, stored) -> dict:
    """{key: value} cho 6 đối tượng sửa được (W3h cần để gửi kèm D7 khi bật "Xem khách hàng")."""
    return {obj.key: _stored_value(group, obj, stored) for obj in catalog.stored_objects()}


def _inactive_reason(obj, held, group):
    if _is_owner(group) or _eligible(obj, held):
        return None
    capability = registry.BY_KEY.get(obj.gate_capability)
    if capability is not None:
        return f'Không xem — bật việc "{capability.label}" trước'
    return f"Nhóm không có quyền xem {obj.gate_label}"


def _options(obj):
    if obj.read_only:
        return []
    return [
        {"value": option.value, "label": option.label, "rank": option.rank}
        for option in sorted(obj.options, key=lambda o: o.rank)
    ]


def _row(group, obj, held, stored):
    owner = _is_owner(group)
    if obj.key == "invoices":
        value = catalog.FOLLOWS_ORDERS
    elif obj.key == "audit_log":
        value = "all" if owner or _eligible(obj, held) else "none"
    else:
        value = _stored_value(group, obj, stored)
    note = OWNER_NOTE if owner else (INVOICES_NOTE if obj.key == "invoices" else None)
    return {
        "key": obj.key,
        "label": obj.label,
        "value": value,
        "editable": bool(not owner and not obj.read_only),
        "customer_data": obj.customer_data,
        # Chỉ trả mã việc có thật ở registry (V1 `view_sales_invoices` chưa có tới PV-07): FE không trỏ tới việc không tồn tại.
        "gate_capability": obj.gate_capability if obj.gate_capability in registry.BY_KEY else None,
        "inactive_reason": _inactive_reason(obj, held, group),
        "note": note,
        "options": _options(obj),
    }


def describe_data_scopes(group, held, stored) -> list:
    """8 dòng D1..D8 của nhóm (02b §2.2). `held` = tập permission `app.codename` của nhóm; `stored` = cấu hình đã lưu."""
    return [_row(group, obj, held, stored) for obj in catalog.OBJECTS]


def legacy_scopes(group, held, stored) -> dict:
    """Chuỗi `scopes` cũ ({orders, deliveries, customers}) dựng từ cấu hình đã lưu; bỏ ở Lô 6 cùng lúc FE đổi kiểu.

    `customers` vẫn theo quyền thực tế (M2, bất biến 9): nhóm có `sales.view_customer_list` -> "Tất cả khách"; không thì
    "Được gán" chỉ khi cấu hình là `assigned_deliveries` và nhóm có `sales.view_customer`, còn lại "Không xem"."""
    values = data_scope_values(group, stored)
    if CUSTOMER_LIST_PERM in held or _is_owner(group):
        customers = LEGACY_ALL_CUSTOMERS
    elif values["customers"] == "assigned_deliveries" and CUSTOMER_PERM in held:
        customers = LEGACY_ASSIGNED
    else:
        customers = LEGACY_NONE
    return {
        "orders": LEGACY_ORDERS[values["orders"]],
        "deliveries": LEGACY_DELIVERIES[values["deliveries"]],
        "customers": customers,
    }
