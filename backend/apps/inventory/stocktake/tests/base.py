"""Dữ liệu nền cho test API kiểm kê (B1, R8). Mọi dữ liệu là giả."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.models import StaffProfile
from apps.catalog.models import Item, ItemGroup
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import StockReconciliation, Warehouse
from apps.purchasing.models import Supplier

URL = "/api/inventory/reconciliations/"
# Giá mua có giá trị riêng biệt: nếu rò vào JSON thì tìm thấy chuỗi này.
PURCHASE_RATE = Decimal("123457")
RATE_SENTINEL = "123457"


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


def line(batch, counted, reason=""):
    return {"batch": batch.pk, "counted_qty": str(counted), "reason": reason}


class StocktakeApiBase(TestCase):
    def setUp(self):
        group = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA01", name="Cá thu", item_group=group)
        self.item2 = Item.objects.create(code="CA02", name="Cá ngừ", item_group=group)
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.wh2 = Warehouse.objects.create(name="Kho lạnh")
        self.today = timezone.localdate()
        self.owner = make_user("u_owner", roles.OWNER)
        self.manager = make_user("u_manager", roles.MANAGER)
        self.manager2 = make_user("u_manager2", roles.MANAGER)
        self.warehouse_staff = make_user("u_warehouse", roles.WAREHOUSE_STAFF)
        self.warehouse_staff2 = make_user("u_warehouse2", roles.WAREHOUSE_STAFF)
        self.delivery_staff = make_user("u_delivery", roles.DELIVERY_STAFF)
        self.customer_service = make_user("u_cs", roles.CUSTOMER_SERVICE)
        StaffProfile.objects.create(user=self.warehouse_staff, phone="0900000901", display_name="Kho Thử")
        StaffProfile.objects.create(user=self.manager, phone="0900000902", display_name="Quản Lý Thử")
        self.batch = self.make_batch("50", item=self.item, warehouse=self.wh)
        self.batch2 = self.make_batch("30", item=self.item2, warehouse=self.wh2)

    def make_batch(self, qty, *, item=None, warehouse=None):
        return batch_services.create_batch(
            item=item or self.item, supplier=self.sup, warehouse=warehouse or self.wh,
            received_date=self.today, qty=Decimal(qty), purchase_rate=PURCHASE_RATE,
        )

    def api(self, user):
        return client_for(user)

    def create_via_api(self, user, lines=None, **extra):
        payload = {"count_date": str(self.today), "note": "Đếm đầu ca", **extra}
        if lines is not None:
            payload["lines"] = lines
        resp = self.api(user).post(URL, payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()

    def replace_via_api(self, user, rec_json, lines, **extra):
        payload = {"expected_updated_at": rec_json["updated_at"], "lines": lines, **extra}
        return self.api(user).post(f"{URL}{rec_json['id']}/lines/", payload, format="json")

    def make_draft(self, user=None, lines=None):
        """Tạo phiếu DRAFT qua API (có dòng), trả JSON chi tiết."""
        user = user or self.warehouse_staff
        return self.create_via_api(user, lines if lines is not None else [line(self.batch, "48.500")])

    def approve_via_api(self, user, rec):
        """Phiếu còn nháp thì owner gửi duyệt trước (#20), rồi `user` duyệt. Trả response của lần duyệt."""
        if self.recon(rec["id"]).status == StockReconciliation.Status.DRAFT:
            self.api(self.owner).post(f"{URL}{rec['id']}/submit/")
        return self.api(user).post(f"{URL}{rec['id']}/approve/")

    def force_submitted(self, rec):
        """Đặt thẳng SUBMITTED cho phiếu rỗng (service không cho gửi phiếu rỗng) để thử đường duyệt phiếu rỗng."""
        StockReconciliation.objects.filter(pk=rec["id"]).update(status=StockReconciliation.Status.SUBMITTED)

    def assertNoCostLeak(self, response):
        data = response.json()
        self.assertEqual(find_cost_keys(data), set())
        self.assertNotIn(RATE_SENTINEL, response.content.decode())

    def recon(self, pk):
        return StockReconciliation.objects.get(pk=pk)
