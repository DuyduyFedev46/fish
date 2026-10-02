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
    Capability("view_customers", "Xem khách hàng", SECTION_SALES, ("sales.view_customer_list",)),
    Capability(
        "confirm_calls", "Gọi xác nhận đơn", SECTION_SALES,
        ("delivery.confirm_with_customer", "delivery.change_recipient"),
    ),
    Capability("confirm_payment", "Xác nhận đã nhận tiền", SECTION_SALES, ("sales.confirm_payment_manual",), True),
    Capability("cancel_paid", "Huỷ đơn đã thanh toán", SECTION_SALES, ("sales.cancel_paid_order",)),
    Capability("create_refund", "Lập phiếu hoàn", SECTION_SALES, ("sales.create_refund",)),
    Capability("confirm_refund", "Xác nhận đã hoàn tiền", SECTION_SALES, ("sales.confirm_refund",), True),
    Capability(
        "pack_print", "Soạn hàng, in tem", SECTION_SALES,
        ("delivery.pack_deliverynote", "delivery.print_label"),
        requires=("deliver",),
    ),
    Capability("assign_delivery", "Giao phiếu cho người giao", SECTION_SALES, ("delivery.assign_deliverynote",)),
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
    Capability("create_return", "Ghi hàng hoàn về kho", SECTION_STOCK, ("inventory.add_returntostock",)),
    Capability("approve_return", "Duyệt hàng hoàn về kho", SECTION_STOCK, ("inventory.approve_returntostock",)),
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

# Nhóm Chủ luôn đủ quyền, không sửa qua ma trận (GROUP_LOCKED).
LOCKED_GROUP = roles.OWNER

# Trạng thái một việc đối với một nhóm.
STATE_ON = "on"
STATE_OFF = "off"
STATE_PARTIAL = "partial"

# Phạm vi dữ liệu (Tầng 3, W3i) — CHỈ ĐỌC. `orders`, `deliveries`: bảng cố định theo `scope_orders_for`,
# `DeliveryNoteViewSet.get_queryset` (theo nhóm, không đổi khi bật/tắt việc); đổi code Tầng 3 thì sửa bảng này.
# `customers`: TÍNH ĐỘNG (M2, bất biến 9) — nhóm có `sales.view_customer_list` thì xem được MỌI khách ("Tất cả khách",
# `can_view_customer_directory` không có phạm vi dòng); nếu không, lấy giá trị bảng này: NV giao chỉ thấy khách của
# phiếu được gán, nhóm khác "Không xem".
CUSTOMER_DIRECTORY_PERM = "sales.view_customer_list"
SCOPE_ALL = "Tất cả"
SCOPE_ALL_CUSTOMERS = "Tất cả khách"
SCOPE_ASSIGNED = "Được gán"
SCOPE_CALL_RANGE = "Trong phạm vi gọi"
SCOPE_NONE = "Không xem"

GROUP_SCOPES = {
    roles.OWNER: {"orders": SCOPE_ALL, "deliveries": SCOPE_ALL, "customers": SCOPE_NONE},
    roles.MANAGER: {"orders": SCOPE_ALL, "deliveries": SCOPE_ALL, "customers": SCOPE_NONE},
    roles.WAREHOUSE_STAFF: {"orders": SCOPE_ALL, "deliveries": SCOPE_ALL, "customers": SCOPE_NONE},
    roles.DELIVERY_STAFF: {"orders": SCOPE_ASSIGNED, "deliveries": SCOPE_ASSIGNED, "customers": SCOPE_ASSIGNED},
    roles.CUSTOMER_SERVICE: {"orders": SCOPE_CALL_RANGE, "deliveries": SCOPE_CALL_RANGE, "customers": SCOPE_NONE},
}
