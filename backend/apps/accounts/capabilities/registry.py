"""
Registry "việc" cho ma trận phân quyền (B4, 02b §3 B4, đề xuất BR-PQ-32).

MỘT nguồn duy nhất: mỗi "việc" người dùng thấy trên màn Phân quyền = một tập permission Django.
Tập `perms` của các việc RỜI NHAU (test kiểm), nên bật/tắt một việc không đụng việc khác.

`owner_only` (T9): chỉ nhóm Chủ được bật. Gồm các ô ❌ ở spec §1.5, chính sách AI, và sửa giá bán/ưu đãi
(spec §1.4: chỉ Chủ có CRU ItemPrice, PricingRule). Đúng ranh "Quản lý được uỷ việc làm khách phải chờ; Chủ giữ
việc tiền rời túi hoặc đổi con số lời lỗ" (bất biến 2).

`requires`: các việc phải đang BẬT thì việc này mới dùng được (M1, techlead Lô 14). Chỉ khai khi code thật đòi: hiện chỉ
`pack_print` -> `deliver`, vì `DeliveryNoteViewSet.set_status` đòi `delivery.change_deliverynote` (việc `deliver`) cho mọi
chuyển trạng thái, kể cả READY (chỉ sau đó mới kiểm `pack_deliverynote`). Test quét mọi @action có `required_perms` để bắt
cặp mới. `view_orders` KHÔNG khai là việc gốc: không action nào đòi `sales.view_salesorder` (chỉ màn hình đọc đơn cần),
nên Chủ tắt được và FE cảnh báo (02b §3 B4).

Permission nằm ngoài registry (quyền xem hàng loạt, quyền Tầng 1 khác...) KHÔNG BAO GIỜ bị service này đụng tới.
"""
from dataclasses import dataclass

from apps.accounts import roles
from apps.common.ai_visibility import ai_features_enabled

SECTION_SALES = "Bán hàng"
SECTION_STOCK = "Hàng hoá & kho"
SECTION_ACCOUNTING = "Kế toán"
SECTION_WEBSITE = "Website"
SECTION_ADMIN = "Quản trị"


@dataclass(frozen=True)
class Capability:
    key: str
    label: str
    section: str
    perms: tuple
    owner_only: bool = False
    requires: tuple = ()


CAPABILITIES = (
    # Bán hàng
    Capability("view_orders", "Xem đơn", SECTION_SALES, ("sales.view_salesorder", "sales.view_salesorderline")),
    Capability(
        "view_sales_invoices", "Xem hoá đơn bán", SECTION_SALES,
        ("sales.view_salesinvoice", "sales.view_salesinvoiceline"),
    ),
    Capability("view_customers", "Xem khách hàng", SECTION_SALES, ("sales.view_customer_list",)),
    Capability(
        "view_order_customer_info", "Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền", SECTION_SALES,
        ("sales.view_order_customer_info",),
    ),
    Capability(
        "confirm_calls", "Gọi xác nhận đơn", SECTION_SALES,
        ("delivery.confirm_with_customer", "delivery.change_recipient"),
    ),
    Capability("confirm_payment", "Xác nhận đã nhận tiền", SECTION_SALES, ("sales.confirm_payment_manual",), True),
    Capability("cancel_paid", "Huỷ đơn đã thanh toán", SECTION_SALES, ("sales.cancel_paid_order",)),
    Capability("create_refund", "Lập phiếu hoàn tiền", SECTION_SALES, ("sales.create_refund",)),
    Capability("confirm_refund", "Xác nhận đã hoàn tiền", SECTION_SALES, ("sales.confirm_refund",), True),
    Capability(
        "pack_print", "Soạn hàng, in tem", SECTION_SALES,
        ("delivery.pack_deliverynote", "delivery.print_label"),
        requires=("deliver",),
    ),
    Capability("assign_delivery", "Chọn người giao", SECTION_SALES, ("delivery.assign_deliverynote",)),
    Capability("deliver", "Giao hàng, báo kết quả giao", SECTION_SALES, ("delivery.change_deliverynote",)),
    # Hàng hoá & kho
    Capability(
        "receive", "Nhập lô tại cảng", SECTION_STOCK,
        ("purchasing.add_purchasereceipt", "purchasing.change_purchasereceipt"),
    ),
    Capability("add_cost", "Thêm chi phí phụ vào lô", SECTION_STOCK, ("purchasing.add_purchasecost",), True),
    Capability("publish_batch", "Mở bán lô", SECTION_STOCK, ("inventory.publish_batch",)),
    Capability("close_batch", "Chốt lô", SECTION_STOCK, ("inventory.close_batch",), True),
    Capability(
        "count_stock", "Nhập số kiểm kê", SECTION_STOCK,
        ("inventory.add_stockreconciliation", "inventory.change_stockreconciliation"),
    ),
    Capability("approve_count", "Duyệt kiểm kê", SECTION_STOCK, ("inventory.approve_stockreconciliation",)),
    Capability("create_return", "Ghi hàng hoàn", SECTION_STOCK, ("inventory.add_returntostock",)),
    Capability("approve_return", "Duyệt hàng hoàn", SECTION_STOCK, ("inventory.approve_returntostock",)),
    Capability(
        "set_price", "Sửa giá bán", SECTION_STOCK,
        (
            "catalog.add_itemprice", "catalog.change_itemprice",
            "catalog.add_pricingrule", "catalog.change_pricingrule",
        ),
        True,
    ),
    # Kế toán
    Capability("view_cost", "Xem giá vốn", SECTION_ACCOUNTING, ("inventory.view_costprice",), True),
    Capability("view_profit", "Xem báo cáo lãi lỗ", SECTION_ACCOUNTING, ("reports.view_profitreport",), True),
    # Website
    Capability("write_content", "Viết bài", SECTION_WEBSITE, ("content.add_entry", "content.change_entry")),
    Capability("publish_content", "Đăng bài lên Shop", SECTION_WEBSITE, ("content.publish_entry",)),
    # Quản trị
    Capability("manage_staff", "Tạo tài khoản, đổi nhóm", SECTION_ADMIN, ("accounts.manage_staff",), True),
    Capability("view_audit", "Xem nhật ký hoạt động", SECTION_ADMIN, ("accounts.view_auditlog",)),
    Capability("ai_policy", "Cài đặt chính sách AI", SECTION_ADMIN, ("ai.manage_ai_policy",), True),
)

BY_KEY = {c.key: c for c in CAPABILITIES}

# Việc thuộc về AI: ẩn khỏi ma trận khi AI tắt (lô dọn chữ AI, W39). `CAPABILITIES`/`BY_KEY` giữ nguyên để test
# "perms rời nhau" và `_check_requires` không đổi; chỉ chỗ HIỂN THỊ/NHẬN INPUT dùng `visible_capabilities()`.
AI_CAPABILITY_KEYS = frozenset({"ai_policy"})


def visible_capabilities():
    """Các việc hiện trong ma trận: bỏ việc AI khi `AI_ENABLED` tắt."""
    if ai_features_enabled():
        return CAPABILITIES
    return tuple(c for c in CAPABILITIES if c.key not in AI_CAPABILITY_KEYS)


def visible_keys(keys):
    """Giữ khoá hiển thị được (dùng cho dòng nhật ký đổi quyền cũ)."""
    if ai_features_enabled():
        return list(keys)
    return [k for k in keys if k not in AI_CAPABILITY_KEYS]

# Nhóm Chủ luôn đủ quyền, không sửa qua ma trận (GROUP_LOCKED).
LOCKED_GROUP = roles.OWNER

# Trạng thái một việc đối với một nhóm.
STATE_ON = "on"
STATE_OFF = "off"
STATE_PARTIAL = "partial"

# Phạm vi dữ liệu (Tầng 3) KHÔNG còn ở đây: xem `apps/accounts/data_scopes/catalog.py` (PV-02, thay bảng phạm vi cố định cũ).
