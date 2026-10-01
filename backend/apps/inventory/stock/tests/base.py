"""Dữ liệu nền cho test API kho (sổ nhập xuất, kho, phiếu điều chỉnh, lọc lô). Mọi dữ liệu là giả."""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.models import StaffProfile
from apps.catalog.models import Item, ItemGroup
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier
from apps.purchasing.receipts import services as receipt_services

# Giá mua có giá trị riêng biệt: nếu rò ra JSON thì tìm thấy chuỗi này.
PURCHASE_RATE = Decimal("123457")
RATE_SENTINEL = "123457"

ALL_GROUPS = (
    roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE,
)
READERS = (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF)
NON_READERS = (roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE)


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


class StockApiBase(TestCase):
    def setUp(self):
        self.group = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=self.group)
        self.item2 = Item.objects.create(code="CA02", name="Cá ngừ", item_group=self.group)
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.sup2 = Supplier.objects.create(name="Đầu mối B")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.wh2 = Warehouse.objects.create(name="Kho lạnh")
        self.today = timezone.localdate()
        self.users = {name: make_user(f"u_{name}", name) for name in ALL_GROUPS}
        self.no_group = User.objects.create_user("u_no_group", password="x")
        self.owner = self.users[roles.OWNER]
        self.manager = self.users[roles.MANAGER]
        self.warehouse_staff = self.users[roles.WAREHOUSE_STAFF]
        StaffProfile.objects.create(user=self.warehouse_staff, phone="0900000999", display_name="Kho Thử")

    def api(self, user):
        return client_for(user)

    def make_batch(self, *, item=None, supplier=None, warehouse=None, qty="100", actor=None, days=90):
        return batch_services.create_batch(
            item=item or self.item, supplier=supplier or self.sup, warehouse=warehouse or self.wh,
            received_date=self.today, qty=Decimal(qty), purchase_rate=PURCHASE_RATE,
            shelf_life_days=days, actor=actor,
        )

    def make_receipt_batch(self, *, item=None, supplier=None, warehouse=None, qty="50", actor=None):
        """Lô sinh từ phiếu nhập thật (qua `submit_receipt`) → `receipt` có dữ liệu."""
        supplier = supplier or self.sup
        receipt = PurchaseReceipt.objects.create(
            supplier=supplier, warehouse=warehouse or self.wh, received_date=self.today,
            created_by=actor or self.warehouse_staff,
        )
        PurchaseReceiptLine.objects.create(
            receipt=receipt, item=item or self.item, qty=Decimal(qty), rate=PURCHASE_RATE,
        )
        (batch,) = receipt_services.submit_receipt(receipt=receipt, actor=actor or self.warehouse_staff)
        return receipt, batch

    def assert_no_cost(self, response, *, who=""):
        self.assertEqual(response.status_code, 200, (who, response.content[:300]))
        self.assertEqual(find_cost_keys(response.json()), set(), who)
        self.assertNotIn(RATE_SENTINEL, response.content.decode(), who)
