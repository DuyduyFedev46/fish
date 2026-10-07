"""
Bộ dữ liệu giả cho ảnh chụp phạm vi dữ liệu (PV-01, UC-5 bước 3, rủi ro R3).

Mọi chuỗi là GIẢ (bất biến 9): tên "Khách Giả NN", SĐT "09000001NN", địa chỉ "Số NN Đường Giả". Mốc ghi theo NHÃN
(`order_assigned_courier`, ...), không theo pk hay mã sinh tự động, nên đổi thứ tự tạo không làm lệch tệp mốc.

Giờ cố định `NOW` (patch `django.utils.timezone.now` ở test): 06/10/2026 10:00 giờ VN. Cửa sổ dữ liệu khách 7 ngày:
`pii_cutoff` = 00:00 giờ VN ngày 29/09/2026, nên phiếu kết thúc 28/09 23:30 giờ VN (8 ngày) bị ẩn còn phiếu kết thúc
29/09 00:30 giờ VN (7 ngày) vẫn thấy.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import ReturnToStock, Warehouse
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier
from apps.sales.models import Customer, Refund, SalesInvoice, SalesOrder

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 10, 6, 3, 0, tzinfo=UTC)  # 10:00 giờ VN


def utc(year, month, day, hour=0, minute=0):
    return datetime.datetime(year, month, day, hour, minute, tzinfo=UTC)


# Nhãn tài khoản. Chủ, Quản lý, NV kho, NV giao, CSKH, người kiêm nhiệm kho+giao, người không nhóm, superuser.
USER_LABELS = (
    "owner", "manager", "warehouse_staff", "courier", "courier_other", "customer_service", "customer_service_other",
    "warehouse_courier", "direct_permissions", "superuser", "anonymous",
)

# Người không nhóm nhưng được gán quyền trực tiếp (UC-6, R9): đủ quyền xem để bắt mọi đường đọc.
DIRECT_PERMISSIONS = (
    "sales.view_salesorder", "sales.view_salesorderline", "sales.view_salesinvoice", "sales.view_salesinvoiceline",
    "sales.view_customer", "sales.view_customer_list", "sales.view_refund",
    "delivery.view_deliverynote", "delivery.confirm_with_customer",
    "inventory.view_returntostock", "purchasing.view_purchasereceipt",
    "reports.view_dashboard",
    # PV-07: V2 cấp cho 5 nhóm qua migration; người không nhóm phải được cấp tay mới thấy tên khách trên đơn (R9, D-3).
    "sales.view_order_customer_info",
)

# Một đơn = một khách riêng. `note`: trạng thái phiếu giao sau khi chỉnh; `task`: tình trạng gọi; `courier`: nhãn người giao;
# `completed`: mốc kết thúc phiếu; `call`: (nhãn người gọi, mốc gọi).
ORDER_SPECS = (
    {"label": "order_booked_unpaid", "status": "BOOKED", "invoice": False},
    {"label": "order_confirming_pending", "note": "CONFIRMING", "task": "PENDING"},
    {"label": "order_confirming_escalated", "note": "CONFIRMING", "task": "ESCALATED"},
    {"label": "order_assigned_courier", "note": "DELIVERING", "task": "DONE", "courier": "courier", "issued": NOW},
    {"label": "order_assigned_other", "note": "DELIVERING", "task": "DONE", "courier": "courier_other", "issued": NOW},
    {"label": "order_assigned_warehouse_courier", "note": "DELIVERING", "task": "DONE", "courier": "warehouse_courier"},
    {"label": "order_assigned_direct", "note": "DELIVERING", "task": "DONE", "courier": "direct_permissions"},
    {"label": "order_failed_courier", "note": "FAILED", "task": "DONE", "courier": "courier"},
    {"label": "order_ended_3_days", "note": "COMPLETED", "task": "DONE", "courier": "courier",
     "completed": utc(2026, 10, 3, 5, 0)},
    {"label": "order_ended_7_days_inside", "note": "COMPLETED", "task": "DONE", "courier": "courier",
     "completed": utc(2026, 9, 28, 17, 30)},  # 00:30 giờ VN 29/09
    {"label": "order_ended_8_days", "note": "COMPLETED", "task": "DONE", "courier": "courier",
     "completed": utc(2026, 9, 28, 16, 30)},  # 23:30 giờ VN 28/09
    {"label": "order_ended_other_courier", "note": "COMPLETED", "task": "DONE", "courier": "courier_other",
     "completed": utc(2026, 10, 5, 5, 0)},
    {"label": "order_called_recent_by_cs", "note": "PREPARING", "task": "DONE",
     "call": ("customer_service", utc(2026, 10, 4, 3, 0))},
    {"label": "order_called_old_by_cs", "note": "PREPARING", "task": "DONE",
     "call": ("customer_service", utc(2026, 9, 27, 3, 0))},
    {"label": "order_called_by_other_cs", "note": "PREPARING", "task": "DONE",
     "call": ("customer_service_other", utc(2026, 10, 5, 3, 0))},
    {"label": "order_cancelled_courier", "status": "CANCELLED", "note": "CANCELLED", "task": "DONE",
     "courier": "courier"},
)

# Phiếu nhập: (nhãn, người tạo, mốc tạo). Ba mốc quanh nửa đêm giờ VN để bắt "trong ngày" (PV-06-AC3/AC4).
RECEIPT_SPECS = (
    ("receipt_warehouse_today", "warehouse_staff", NOW),
    ("receipt_warehouse_after_midnight", "warehouse_staff", utc(2026, 10, 5, 17, 5)),  # 00:05 giờ VN 06/10
    ("receipt_warehouse_before_midnight", "warehouse_staff", utc(2026, 10, 5, 16, 50)),  # 23:50 giờ VN 05/10
    ("receipt_manager_today", "manager", NOW),
    ("receipt_owner_old", "owner", utc(2026, 9, 20, 3, 0)),
)

# Tên, SĐT, địa chỉ và ghi chú GIẢ: test PV-01-AC4 grep các chuỗi này trong tệp mốc.
FAKE_STRINGS = []


class Scene:
    """Kết quả dựng dữ liệu: người dùng, và bản đồ pk -> nhãn của từng loại chứng từ."""

    def __init__(self):
        self.users = {}
        self.orders = {}  # nhãn -> SalesOrder
        self.invoices = {}
        self.notes = {}
        self.customers = {}
        self.returns = {}
        self.batch = None
        self.receipts = {}
        self.refunds = {}
        self.codes = {}  # mã đơn -> nhãn

    def labels(self, kind):
        """{pk: nhãn} của một loại chứng từ."""
        return {obj.pk: label for label, obj in getattr(self, kind).items()}


def _make_user(username, *group_names, perms=(), superuser=False):
    if superuser:
        user = User.objects.create_superuser(username, password="x")
    else:
        user = User.objects.create_user(username, password="x")
    for name in group_names:
        user.groups.add(Group.objects.get(name=name))
    for perm in perms:
        app_label, codename = perm.split(".")
        user.user_permissions.add(Permission.objects.get(content_type__app_label=app_label, codename=codename))
    return User.objects.get(pk=user.pk)  # bỏ cache quyền


def build_users(scene):
    users = {
        "owner": _make_user("pv_owner", roles.OWNER),
        "manager": _make_user("pv_manager", roles.MANAGER),
        "warehouse_staff": _make_user("pv_warehouse", roles.WAREHOUSE_STAFF),
        "courier": _make_user("pv_courier", roles.DELIVERY_STAFF),
        "courier_other": _make_user("pv_courier_other", roles.DELIVERY_STAFF),
        "customer_service": _make_user("pv_cs", roles.CUSTOMER_SERVICE),
        "customer_service_other": _make_user("pv_cs_other", roles.CUSTOMER_SERVICE),
        "warehouse_courier": _make_user("pv_warehouse_courier", roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF),
        "direct_permissions": _make_user("pv_direct", perms=DIRECT_PERMISSIONS),
        "superuser": _make_user("pv_superuser", superuser=True),
        "anonymous": None,
    }
    scene.users = users
    return users


def build_orders(scene):
    for index, spec in enumerate(ORDER_SPECS, start=1):
        label = spec["label"]
        phone = f"09000001{index:02d}"
        name = f"Khách Giả {index:02d}"
        address = f"Số {index:02d} Đường Giả"
        note_text = f"Ghi chú giả {index:02d}"
        FAKE_STRINGS.extend([phone, name, address, note_text])
        customer = Customer.objects.create(phone=phone, name=name, default_address=address, note=note_text)
        order = SalesOrder.objects.create(
            code=f"SO-PV-{index:02d}", customer=customer, status=spec.get("status", "PROCESSING"),
            delivery_address=address, phone=phone, total_amount=Decimal("100000"),
        )
        scene.customers[f"customer_of_{label}"] = customer
        scene.orders[label] = order
        scene.codes[order.code] = label
        if spec.get("invoice", True):
            _build_invoice_and_note(scene, spec, label, order, customer, index)


def _build_invoice_and_note(scene, spec, label, order, customer, index):
    invoice = SalesInvoice.objects.create(
        code=f"INV-PV-{index:02d}", sales_order=order, customer=customer, issued_at=spec.get("issued", utc(2026, 10, 1, 1, 0)),
        amount=Decimal("100000"), status=SalesInvoice.Status.ISSUED,
    )  # signal tạo phiếu giao CONFIRMING + mục chờ gọi PENDING
    note = invoice.delivery_notes.get()
    changes = {"status": spec["note"]}
    courier = spec.get("courier")
    if courier:
        changes["assigned_to"] = scene.users[courier]
    if spec.get("completed"):
        changes["completed_at"] = spec["completed"]
    DeliveryNote.objects.filter(pk=note.pk).update(**changes)
    ConfirmationTask.objects.filter(note=note).update(state=spec["task"])
    if spec.get("call"):
        who, at = spec["call"]
        call = CustomerCall.objects.create(
            note=note, result=CustomerCall.Result.UNREACHABLE, note_text="Gọi thử", created_by=scene.users[who],
        )
        CustomerCall.objects.filter(pk=call.pk).update(created_at=at)
    if spec.get("status") == "CANCELLED":
        SalesInvoice.objects.filter(pk=invoice.pk).update(status=SalesInvoice.Status.CANCELLED)
    scene.invoices[f"invoice_of_{label}"] = invoice
    scene.notes[f"note_of_{label}"] = DeliveryNote.objects.get(pk=note.pk)


def build_extras(scene):
    """Khách chưa có đơn, phiếu hàng hoàn, phiếu nhập, phiếu hoàn tiền."""
    FAKE_STRINGS.extend(["0900000999", "Khách Giả 99", "Số 99 Đường Giả"])
    scene.customers["customer_idle"] = Customer.objects.create(
        phone="0900000999", name="Khách Giả 99", default_address="Số 99 Đường Giả", note="",
    )

    group = ItemGroup.objects.create(name="Cá giả")
    item = Item.objects.create(code="PV01", name="Cá giả", item_group=group)
    supplier = Supplier.objects.create(name="Đầu mối giả")
    warehouse = Warehouse.objects.create(name="Kho giả")
    batch = batch_services.create_batch(
        item=item, supplier=supplier, warehouse=warehouse, received_date=datetime.date(2026, 10, 5),
        qty=Decimal("50"), purchase_rate=Decimal("80000"), batch_id="PV01-261005-AAAAA",
    )

    scene.batch = batch
    owner, warehouse_user = scene.users["owner"], scene.users["warehouse_staff"]
    for label, note_label in (
        ("return_courier", "note_of_order_assigned_courier"),
        ("return_other", "note_of_order_assigned_other"),
        ("return_no_note", None),
    ):
        scene.returns[label] = ReturnToStock.objects.create(
            delivery_note=scene.notes[note_label] if note_label else None, batch=batch, qty=Decimal("1.000"),
            created_by=warehouse_user, note="",
        )

    for label, creator, created_at in RECEIPT_SPECS:
        receipt = PurchaseReceipt.objects.create(
            supplier=supplier, warehouse=warehouse, received_date=datetime.date(2026, 10, 6),
            created_by=scene.users[creator],
        )
        PurchaseReceipt.objects.filter(pk=receipt.pk).update(created_at=created_at)
        PurchaseReceiptLine.objects.create(receipt=receipt, item=item, qty=Decimal("10.000"), rate=Decimal("80000"))
        scene.receipts[label] = PurchaseReceipt.objects.get(pk=receipt.pk)

    for label, invoice_label, status in (
        ("refund_courier_order", "invoice_of_order_assigned_courier", Refund.Status.REFUNDED),
        ("refund_other_order", "invoice_of_order_assigned_other", Refund.Status.PENDING),
    ):
        scene.refunds[label] = Refund.objects.create(
            sales_invoice=scene.invoices[invoice_label], amount=Decimal("50000"), status=status, created_by=owner,
        )


def build_scene():
    """Dựng toàn bộ dữ liệu theo thứ tự cố định. Gọi trong `setUpTestData` khi `timezone.now` đã bị patch về NOW."""
    FAKE_STRINGS.clear()
    scene = Scene()
    build_users(scene)
    build_orders(scene)
    build_extras(scene)
    return scene
