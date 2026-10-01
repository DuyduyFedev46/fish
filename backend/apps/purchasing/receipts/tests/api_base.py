"""Dữ liệu nền cho test API đọc phiếu nhập (R10, 02b §3.8). Mọi dữ liệu là giả."""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.models import StaffProfile
from apps.catalog.models import Item, ItemGroup
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Warehouse
from apps.purchasing.costs import services as cost_services
from apps.purchasing.models import PurchaseInvoice, PurchaseReceipt, PurchaseReceiptLine, Supplier
from apps.purchasing.receipts import services

URL = "/api/purchasing/receipts/"

# Giá trị mốc riêng biệt: nếu rò ra JSON thì tìm thấy chuỗi này.
RATE = Decimal("123457")
RATE_SENTINEL = "123457"
COST_AMOUNT = Decimal("987654")
COST_SENTINEL = "987654"
INVOICE_AMOUNT = Decimal("555551")
INVOICE_SENTINEL = "555551"
# Phiếu chính: 10 kg x 123457 = 1234570 đ.
LINE_QTY = Decimal("10")


def find_cost_keys(data):
    """Quét đệ quy JSON, trả tập khoá giá vốn tìm thấy (COST_KEYS)."""
    found = set()
    if isinstance(data, dict):
        for key, value in data.items():
            if key in COST_KEYS:
                found.add(key)
            found |= find_cost_keys(value)
    elif isinstance(data, list):
        for value in data:
            found |= find_cost_keys(value)
    return found


class ReceiptsApiBase(TestCase):
    def setUp(self):
        group = ItemGroup.objects.create(name="Cá")
        self.item_a = Item.objects.create(code="CA01", name="Cá thu", item_group=group, shelf_life_in_days=90)
        self.item_b = Item.objects.create(code="TOM01", name="Tôm sú", item_group=group, shelf_life_in_days=60)
        self.supplier = Supplier.objects.create(name="Đầu mối A")
        self.other_supplier = Supplier.objects.create(name="Vựa B")
        self.warehouse = Warehouse.objects.create(name="Kho chính")
        self.owner = make_user("u_owner", roles.OWNER)
        self.manager = make_user("u_manager", roles.MANAGER)
        self.warehouse_staff = make_user("u_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("u_courier", roles.DELIVERY_STAFF)
        self.customer_service = make_user("u_cs", roles.CUSTOMER_SERVICE)
        self.no_group = User.objects.create_user("u_no_group", password="x")
        StaffProfile.objects.create(user=self.warehouse_staff, phone="0900000102", display_name="Tâm Thử")
        # Phiếu đã ghi nhận 2 dòng (2 mặt hàng, 2 lô), cho nhà cung cấp A.
        self.receipt, self.batches = self.submit(
            self.supplier, [(self.item_a, "10", RATE), (self.item_b, "5", Decimal("80000"))],
            datetime.date(2026, 9, 28),
        )

    def submit(self, supplier, specs, received_date, actor=None):
        lines = [{"item_code": item, "qty": Decimal(qty), "rate": rate} for item, qty, rate in specs]
        return services.create_and_submit_receipt(
            supplier=supplier, lines=lines, actor=actor or self.warehouse_staff,
            received_date=received_date, warehouse=self.warehouse,
        )

    def make_draft(self, supplier=None, received_date=datetime.date(2026, 10, 1)):
        receipt = PurchaseReceipt.objects.create(
            supplier=supplier or self.supplier, warehouse=self.warehouse, received_date=received_date,
            created_by=self.warehouse_staff,
        )
        PurchaseReceiptLine.objects.create(receipt=receipt, item=self.item_a, qty=Decimal("3"), rate=RATE)
        return receipt

    def add_invoice(self, receipt, amount=INVOICE_AMOUNT):
        return PurchaseInvoice.objects.create(
            supplier=receipt.supplier, receipt=receipt, amount=amount, invoice_date=receipt.received_date,
            created_by=self.owner,
        )

    def add_cost(self, batches, amount=COST_AMOUNT):
        return cost_services.record_purchase_cost(
            cost_type="ICE", amount=amount, allocation_method="BY_QTY",
            incurred_date=datetime.date(2026, 9, 28), allocations=list(batches), actor=self.owner,
        )

    def get(self, user, path=""):
        return client_for(user).get(f"{URL}{path}")

    def ids(self, user, query=""):
        resp = self.get(user, query)
        self.assertEqual(resp.status_code, 200, query)
        return {row["id"] for row in resp.json()["results"]}
