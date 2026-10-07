"""
Mô tả phạm vi dữ liệu của nhóm cho màn Phân quyền (W3i/W3h), PV-02, 02b §2.1–§2.2.

Lô 2: ĐỌC (`data_scopes` 8 dòng, `data_scope_values` 6 đối tượng sửa được; chuỗi `scopes` cũ đã bỏ ở Lô 6).
Lô 5 (PV-08..PV-10): kiểm giá trị (`parse_scope_changes`), tầm với và mở rộng dữ liệu khách (`reach`, `widened_objects`, 02b §2.5),
xem trước (`preview_group_changes`, 02b §2.4), áp (`apply_scope_changes`). Việc đổi nhóm có khoá lạc quan, AuditLog và gọi các hàm này
nằm ở `capabilities/services.py`.
Mọi chữ trả ra là mã và nhãn cố định của dự án, không dữ liệu khách, không giá vốn (bất biến 1, 9).
"""
from django.contrib.auth.models import Group, User

from apps.accounts import roles
from apps.accounts.capabilities import registry
from apps.accounts.models import GroupAccessConfig, GroupDataScope
from apps.common.exceptions import BusinessError

from . import catalog
from .resolver import resolve_data_scopes

OWNER_NOTE = "Chủ luôn thấy tất cả"
INVOICES_NOTE = "Theo Đơn hàng"
DEFAULT_VERSION = 1


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


D7_CAPPED_NOTE = "Bật Xem khách hàng để thấy tất cả khách"


def _capped_note(obj, held, value):
    """L4 (review 06/10): D7 lưu rộng hơn `capped_value` mà nhóm thiếu `full_perm` thì giá trị hiệu lực bị chặn trần; nói rõ cho Chủ."""
    if obj.full_perm and obj.full_perm not in held and effective_rank(obj, value, held) < catalog.rank_of(obj, value):
        return D7_CAPPED_NOTE
    return None


def _row(group, obj, held, stored):
    owner = _is_owner(group)
    if obj.key == "invoices":
        value = catalog.FOLLOWS_ORDERS
    elif obj.key == "audit_log":
        value = "all" if owner or _eligible(obj, held) else "none"
    else:
        value = _stored_value(group, obj, stored)
    note = OWNER_NOTE if owner else (INVOICES_NOTE if obj.key == "invoices" else None)
    if note is None and not owner and obj.key == "customers" and _eligible(obj, held):
        note = _capped_note(obj, held, value)
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


# --- Lô 5: kiểm, mở rộng dữ liệu khách, xem trước, áp (PV-08, PV-09; 02b §2.3–§2.5) --------------------------------

SCOPE_OBJECT_UNKNOWN = "SCOPE_OBJECT_UNKNOWN"
SCOPE_READ_ONLY = "SCOPE_READ_ONLY"
SCOPE_VALUE_INVALID = "SCOPE_VALUE_INVALID"
INVALID_INPUT = "INVALID_INPUT"
V2_KEY = "view_order_customer_info"
PO_Q1_MESSAGE = "Bật Xem khách hàng thì chọn phạm vi Khách hàng khác Không xem."
UNCHANGED_NO_ONE = "Nhóm này chưa có ai đang làm nên chưa người nào thấy thêm."

# Câu "N người … sẽ thấy tên, SĐT, địa chỉ khách <cụm>" theo từng đối tượng (khớp mock F1).
WIDEN_PHRASE = {
    "orders": "của mọi đơn", "invoices": "trên hoá đơn bán", "deliveries": "của mọi phiếu giao",
    "confirmation": "của mọi phiếu chờ gọi", "returns": "của mọi phiếu hàng hoàn", "customers": "của mọi khách",
    V2_KEY: "trên đơn, hoá đơn và phiếu giao",
}
V2_LABEL = "Thông tin khách trên đơn"


def parse_scope_changes(scopes) -> dict:
    """Kiểm `scopes` của PUT/POST (02b §2.3 bước 5, 6): {mã đối tượng: mã giá trị}. Lỗi đầu tiên thắng."""
    if scopes is None:
        return {}
    if not isinstance(scopes, dict):
        raise BusinessError("Phạm vi phải gửi dạng danh sách khoá và giá trị.", code=INVALID_INPUT)
    for key, value in scopes.items():
        obj = catalog.BY_KEY.get(key)
        if obj is None:
            raise BusinessError("Có đối tượng phạm vi không có trong danh sách.", code=SCOPE_OBJECT_UNKNOWN)
        if obj.read_only:
            raise BusinessError(f"“{obj.label}” chỉ để xem, không đổi được ở đây.", code=SCOPE_READ_ONLY)
        if not isinstance(value, str) or catalog.rank_of(obj, value) is None:
            raise BusinessError(f"Giá trị phạm vi của “{obj.label}” không hợp lệ.", code=SCOPE_VALUE_INVALID)
    return dict(scopes)


def merged_values(group, stored, changes) -> dict:
    """Giá trị 6 phạm vi sau khi áp `changes` lên cấu hình đã lưu của `group`."""
    values = data_scope_values(group, stored)
    values.update(changes)
    return values


def check_po_q1(held_after, values_after):
    """PO-Q1 (02b §2.3 bước 10): việc "Xem khách hàng" bật thì D7 không được là `none`."""
    if catalog.CUSTOMERS.full_perm in held_after and values_after["customers"] == "none":
        raise BusinessError(PO_Q1_MESSAGE, code=SCOPE_VALUE_INVALID)


def effective_rank(obj, value, held) -> int:
    """Rank HIỆU LỰC (luật H1): đối tượng có `full_perm` mà nhóm thiếu thì bị chặn trần ở `capped_value` (D7)."""
    rank = catalog.rank_of(obj, value)
    if obj.full_perm and obj.full_perm not in held:
        rank = min(rank, catalog.rank_of(obj, obj.capped_value))
    return rank


def reach(obj, held, values) -> tuple:
    """Tầm với của nhóm với đối tượng: (cổng mở?, rank hiệu lực). D2 lấy rank theo D1 của chính nhóm (02b §1.3 luật 4)."""
    source = catalog.BY_KEY[obj.derived_from] if obj.derived_from else obj
    return _eligible(obj, held), effective_rank(source, values[source.key], held)


def is_widening(before, after) -> bool:
    """02b §2.5: sau thay đổi cổng mở và rank lớn hơn (cổng đang đóng coi như rank 0, nên vừa mở với rank 0 không tính)."""
    if not after[0]:
        return False
    return after[1] > (before[1] if before[0] else 0)


def widened_objects(held_before, held_after, values_before, values_after) -> list:
    """Danh sách `{key, from, to}` các đối tượng có dữ liệu khách được MỞ RỘNG, cộng V2 khi bật (02b §2.5).

    `from`/`to` là giá trị ĐÃ LƯU (L11): ca cổng vừa mở trên giá trị đang lưu cho `from == to`. D2 dùng giá trị D1."""
    out = []
    for obj in catalog.OBJECTS:
        if not obj.customer_data:
            continue
        source = obj.derived_from or obj.key
        before = reach(obj, held_before, values_before)
        after = reach(obj, held_after, values_after)
        if is_widening(before, after):
            out.append({"key": obj.key, "from": values_before[source], "to": values_after[source]})
    v2 = registry.BY_KEY[V2_KEY].perms[0]
    if v2 not in held_before and v2 in held_after:
        out.append({"key": V2_KEY, "from": "off", "to": "on"})
    return out


def _active_members(group):
    return list(User.objects.filter(groups=group, is_active=True).select_related("staff_profile").order_by("username"))


def _display(user):
    profile = getattr(user, "staff_profile", None)
    return (profile.display_name if profile else "") or user.get_full_name() or user.get_username()


def _open_rows(key, user, value) -> set:
    """Mã dòng CHƯA KẾT THÚC mà `user` thấy được ở đối tượng `key` với phạm vi `value` (02b §2.4). Khách không đếm."""
    if key == "orders":
        from apps.sales.models import SalesOrder
        from apps.sales.orders.scope import scope_orders_for

        qs = SalesOrder.objects.filter(status__in=(SalesOrder.Status.BOOKED, SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING))
        return set(scope_orders_for(user, qs, value=value).values_list("pk", flat=True))
    if key == "deliveries":
        from apps.delivery.models import DeliveryNote
        from apps.delivery.scope import scope_deliveries_for

        qs = DeliveryNote.objects.exclude(status__in=(DeliveryNote.Status.COMPLETED, DeliveryNote.Status.CANCELLED))
        return set(scope_deliveries_for(user, qs, value=value).values_list("pk", flat=True))
    if key == "returns":
        from apps.inventory.models import ReturnToStock
        from apps.inventory.returns.scope import scope_returns_for

        qs = ReturnToStock.objects.filter(status=ReturnToStock.Status.DRAFT)
        return set(scope_returns_for(user, qs, value=value).values_list("pk", flat=True))
    if key == "receipts":
        from apps.purchasing.models import PurchaseReceipt
        from apps.purchasing.receipts.scope import scope_receipts_for

        qs = PurchaseReceipt.objects.filter(status=PurchaseReceipt.Status.DRAFT)
        return set(scope_receipts_for(user, qs, value=value).values_list("pk", flat=True))
    if key == "confirmation":
        from apps.delivery.confirmation.scope import ALL_PENDING, OPEN_CALL_STATES, customer_service_note_q
        from apps.delivery.models import DeliveryNote

        qs = DeliveryNote.objects.filter(confirmation__state__in=OPEN_CALL_STATES)
        if value != ALL_PENDING:
            qs = qs.filter(customer_service_note_q(user))
        return set(qs.values_list("pk", flat=True))
    return set()


def _rows_losing(key, members, group, values_after) -> int:
    """Số dòng chưa kết thúc mà ÍT NHẤT MỘT thành viên đang thấy và sẽ mất khi nhóm đổi sang `values_after` (gộp không trùng)."""
    lost = set()
    for member in members:
        before = resolve_data_scopes(member, overrides={})[key].value
        after = resolve_data_scopes(member, overrides={group.pk: {key: values_after[key]}})[key].value
        if before == after:
            continue
        lost |= _open_rows(key, member, before) - _open_rows(key, member, after)
    return len(lost)


def preview_group_changes(group, *, held_before, held_after, values_before, values_after) -> dict:
    """Kết quả xem trước (02b §2.4), cũng là `impact` của lỗi 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED`. Không ghi gì.

    Chỉ có mã, nhãn và tên NHÂN VIÊN: không tên, SĐT, địa chỉ khách (bất biến 9)."""
    members = _active_members(group)
    widened = widened_objects(held_before, held_after, values_before, values_after)
    widens = bool(widened)
    count = len(members)
    if not widens:
        message = ""
    elif count == 0:
        message = UNCHANGED_NO_ONE
    elif len(widened) == 1:
        message = f"{count} người trong nhóm sẽ thấy tên, SĐT, địa chỉ khách {WIDEN_PHRASE[widened[0]['key']]}."
    else:
        labels = [V2_LABEL if w["key"] == V2_KEY else catalog.BY_KEY[w["key"]].label for w in widened]
        message = f"{count} người trong nhóm sẽ thấy tên, SĐT, địa chỉ khách ở: {', '.join(labels)}."

    narrowed, wider = [], []
    others = [(g, {f"{p.content_type.app_label}.{p.codename}" for p in g.permissions.select_related("content_type")},
               set(User.objects.filter(groups=g, is_active=True).values_list("pk", flat=True)))
              for g in Group.objects.filter(name__in=roles.ALL_ROLES).exclude(pk=group.pk)]
    other_stored = load_stored([g.pk for g, _, _ in others])
    for obj in catalog.stored_objects():
        key = obj.key
        if values_before[key] == values_after[key]:
            continue
        rank_before = reach(obj, held_before, values_before)[1]
        rank_after = reach(obj, held_after, values_after)[1]
        if rank_after < rank_before:
            narrowed.append({
                "key": key, "from": values_before[key], "to": values_after[key],
                "rows_losing_access": _rows_losing(key, members, group, values_after),
            })
        for member in members:
            for other, other_held, other_members in others:
                if member.pk not in other_members or not _eligible(obj, other_held):
                    continue
                other_value = _stored_value(other, obj, other_stored[other.pk])
                if effective_rank(obj, other_value, other_held) > effective_rank(obj, values_after[key], held_after):
                    entry = {"id": member.pk, "display_name": _display(member), "via_group": other.name, "key": key}
                    if entry not in wider:
                        wider.append(entry)
    return {
        "widens_customer_data": widens,
        "widened": widened,
        "affected_members": [{"id": m.pk, "display_name": _display(m)} for m in members] if widens else [],
        "affected_count": count if widens else 0,
        "message": message,
        "already_wider_elsewhere": wider,
        "narrowed": narrowed,
    }


def apply_scope_changes(group, changes, stored) -> dict:
    """Ghi các giá trị phạm vi thật sự đổi; trả `{key: {"from", "to"}}` cho AuditLog (rỗng nếu không có gì đổi)."""
    audit = {}
    for key, wanted in changes.items():
        obj = catalog.BY_KEY[key]
        before = catalog.valid_or_narrowest(obj, stored.get(key))
        if before == wanted:
            continue
        GroupDataScope.objects.update_or_create(group=group, object_key=key, defaults={"value": wanted})
        audit[key] = {"from": before, "to": wanted}
    return audit


def scope_event_label(key, change) -> str:
    """"Đổi phạm vi Phiếu nhập: Tất cả phiếu → Do tôi tạo trong ngày" từ mã (không dùng `changes` thô ở FE)."""
    obj = catalog.BY_KEY.get(key)
    if obj is None or obj.read_only:
        return "Đổi phạm vi dữ liệu"
    labels = {option.value: option.label for option in obj.options}
    return f"Đổi phạm vi {obj.label}: {labels.get((change or {}).get('from'), '?')} → {labels.get((change or {}).get('to'), '?')}"


def scope_object_keys(changes) -> list:
    """Khoá của `changes` AuditLog phạm vi là mã đối tượng sửa được (bỏ cờ `customer_data_widening_confirmed`)."""
    return [key for key in (changes or {}) if key in catalog.BY_KEY and not catalog.BY_KEY[key].read_only]
