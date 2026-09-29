"""
Bảng danh sách chặn và phân loại an toàn tất định cho AI (02b §3, DW-07, DW-08).
Hằng số trong code — review qua PR, không chỉnh từ DB/Admin.
"""
from apps.common.cost_keys import COST_KEYS

# Tiền tố URL cấm hẳn không bao giờ vào chỉ mục (H11, H14, bất biến 9, go-live, cskh)
FORBIDDEN_PREFIXES = (
    "/api/shop/",
    "/api/internal/",
    "/api/auth/",
    "/api/ai/",
    "/api/staff/",
    "/api/audit-logs/",
    "/api/commands/",
    "/api/public/",
    "/api/cskh/",
    "/api/dashboard/attention/",
)

# Hậu tố URL cấm hẳn (tem có tên/SĐT/địa chỉ khách)
FORBIDDEN_SUFFIXES = (
    "/label/",
    "/label/print/",
    "/label/void/",
    "/label",
    "/label/print",
    "/label/void",
)

# Phương thức HTTP cấm hẳn (Bất biến 3, H4)
FORBIDDEN_METHODS = frozenset({"DELETE", "PUT"})

# Quyền Tầng 2 cấm hẳn trong chỉ mục AI (H11, BR-PQ)
FORBIDDEN_PERMS_T2 = frozenset({
    "accounts.manage_staff",
    "accounts.view_auditlog",
    "ai.manage_ai_policy",
})

# Resource cấm hoàn toàn (H2, bất biến 9)
FORBIDDEN_RESOURCES = frozenset({"sales.customer", "customer"})

# Model cấm ghi CRUD thông thường (H7, BR-PQ-11 — AI không tự tạo đơn / hoá đơn)
FORBIDDEN_WRITE_MODELS = frozenset({
    "sales.salesorder", "salesorder",
    "sales.salesinvoice", "salesinvoice",
})

# Vùng đỏ: chỉ C khi công tắc đóng; tối đa B trì hoãn ghi khi mở (BR-AI-07/18, §7)
RED_ZONE_PERMS = frozenset({
    "inventory.close_batch",
    "sales.confirm_refund",
    "sales.confirm_payment_manual",
})

# Trần C ép: không thể nâng lên B/A (BR-AI-18, H6, H9, Q-L1)
FORCE_C_PERMS = frozenset({
    "sales.cancel_paid_order",
    "sales.create_refund",
    "purchasing.add_purchasecost",
    "purchasing.change_purchasecost",
    "catalog.add_itemprice",
    "catalog.change_itemprice",
    "catalog.delete_itemprice",
    "catalog.add_pricingrule",
    "catalog.change_pricingrule",
    "catalog.delete_pricingrule",
    "catalog.add_pricelist",
    "catalog.change_pricelist",
    "catalog.delete_pricelist",
    "inventory.approve_stockreconciliation",
    "inventory.approve_returntostock",
    "inventory.publish_batch",
    "inventory.cancel_expired_batch",
})

# Lọc đầu ra: Khoá PII khách (H2, bất biến 9 — loại bỏ đệ quy kể cả với Chủ)
SCRUB_PII_KEYS = frozenset({
    "phone",
    "customer_phone",
    "customer_name",
    "delivery_address",
    "shipping_address",
    "recipient_name",
    "receiver_name",
    "address",
    "email",
    "raw_payload",
    "transfer_content",
    "content",
    "bank_account_name",
    "counter_account_name",
})

# Lọc đầu ra: Chữ tự do (H10 — tránh Prompt Injection)
SCRUB_FREE_TEXT_KEYS = frozenset({
    "note",
    "reason",
    "resolution_note",
    "failure_reason",
    "comment",
})

# Lọc đầu ra: Khoá giá vốn khi thiếu view_costprice (bất biến 1, H3)
SCRUB_COST_KEYS = COST_KEYS


def is_url_forbidden(path: str) -> bool:
    """Kiểm tra URL có nằm trong danh sách cấm tất định không."""
    import re
    # Bỏ regex và format suffix
    cleaned = re.sub(r'\\?\.<format>.*', '', path)
    cleaned = re.sub(r'[\^$]', '', cleaned)
    normalized = "/" + cleaned.strip("/") + "/" if cleaned.strip("/") else "/"
    for prefix in FORBIDDEN_PREFIXES:
        p_clean = prefix.rstrip("/")
        if normalized.startswith(prefix) or cleaned.startswith(p_clean) or normalized.startswith(p_clean + "/"):
            return True
    for suffix in FORBIDDEN_SUFFIXES:
        if normalized.rstrip("/").endswith(suffix.rstrip("/")):
            return True
    return False


def is_perm_forbidden(perm: str) -> bool:
    """Kiểm tra quyền có bị cấm hẳn không."""
    if perm.startswith("auth."):
        return True
    return perm in FORBIDDEN_PERMS_T2


def is_red_zone_action(required_perms: tuple | list | set) -> bool:
    """Kiểm tra action có thuộc vùng đỏ không (đúng bằng 3 quyền đỏ)."""
    return bool(set(required_perms) & RED_ZONE_PERMS)


# Quyền Tầng 2 được phép nâng lên B/A (chỉ nhap_lo ở Lô 4, còn lại trần C ép theo 02b §3)
WHITELISTED_ABOVE_C_PERMS = frozenset({
    "purchasing.add_purchasereceipt",
    "purchasing.change_purchasereceipt",
})


def is_force_c_action(required_perms: tuple | list | set) -> bool:
    """Kiểm tra action có bị ép trần C không (02b §3: mọi quyền T2 chưa trong whitelist đều ép C)."""
    perms_set = set(required_perms)
    if not perms_set:
        return False
    if is_red_zone_action(perms_set):
        return True
    if perms_set & FORCE_C_PERMS:
        return True
    if not perms_set.issubset(WHITELISTED_ABOVE_C_PERMS):
        return True
    return False
