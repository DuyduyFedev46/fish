"""Dữ liệu nền cho test API hàng hoàn về kho (R9). Mọi dữ liệu là giả (SĐT, tên, địa chỉ)."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.models import StaffProfile
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_master, make_order_with_note, make_user
from apps.delivery import services as delivery_services
from apps.delivery.models import DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import ReturnToStock
from apps.sales.models import SalesInvoiceLine, SalesInvoiceLineBatch

URL = "/api/inventory/returns/"

# Giá mua có giá trị riêng biệt: nếu rò ra JSON thì tìm thấy chuỗi này.
PURCHASE_RATE = Decimal("123457")
RATE_SENTINEL = "123457"
# Ghi chú tự do có SĐT giả: không được lọt vào AuditLog, dòng thời gian, AI.
NOTE_WITH_PHONE = "Khách Nguyễn Thử hẹn lại, gọi 0900000777"
PHONE_SENTINEL = "0900000777"


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


class ReturnsApiBase(TestCase):
    """Hai người giao A, B; mỗi người một phiếu ĐANG GIAO có 10 kg của cùng một lô."""

    def setUp(self):
        self.item, self.sup, self.wh = make_master()
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            qty=Decimal("50"), purchase_rate=PURCHASE_RATE,
        )
        batch_services.publish_batch(batch=self.batch, actor=None)
        self.owner = make_user("u_owner", roles.OWNER)
        self.manager = make_user("u_manager", roles.MANAGER)
        self.warehouse_staff = make_user("u_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("u_courier_a", roles.DELIVERY_STAFF)
        self.other_courier = make_user("u_courier_b", roles.DELIVERY_STAFF)
        self.customer_service = make_user("u_cs", roles.CUSTOMER_SERVICE)
        self.no_group = User.objects.create_user("u_no_group", password="x")
        StaffProfile.objects.create(user=self.courier, phone="0900000101", display_name="Phúc Thử")
        self.order, _customer, self.note = self.make_delivering_note("SO-R9-A", "0900000201", self.courier)
        self.other_order, _c, self.other_note = self.make_delivering_note("SO-R9-B", "0900000202", self.other_courier)

    def make_delivering_note(self, code, phone, courier, *, qty="10", batch=None):
        """Đơn + hoá đơn + phiếu giao đã chạy qua READY → DELIVERING (có AuditLog giờ rời kho), 1 dòng phân bổ `batch`."""
        order, customer, note = make_order_with_note(code, phone, assigned_to=courier)
        self.add_allocation(note, batch or self.batch, qty)
        note.status = DeliveryNote.Status.READY
        note.save(update_fields=["status"])
        delivery_services.advance_status(note=note, to_status=DeliveryNote.Status.DELIVERING, actor=courier)
        note.refresh_from_db()
        return order, customer, note

    def add_allocation(self, note, batch, qty):
        line = SalesInvoiceLine.objects.create(
            invoice=note.sales_invoice, item=self.item, qty=Decimal(qty), rate=Decimal("100000"),
            amount=Decimal(qty) * Decimal("100000"),
        )
        SalesInvoiceLineBatch.objects.create(
            invoice_line=line, batch=batch, component_item=self.item, qty=Decimal(qty), unit_cost=PURCHASE_RATE,
        )

    def make_return(self, note=None, qty="2", created_by=None, free_note=""):
        return ReturnToStock.objects.create(
            delivery_note=note or self.note, batch=self.batch, qty=Decimal(qty), note=free_note,
            created_by=created_by or self.courier, returned_at=timezone.now(),
        )

    def post(self, user, payload, url=URL):
        return client_for(user).post(url, payload, format="json")

    def payload(self, delivery_note=None, qty="2", **extra):
        return {"delivery_note": (delivery_note or self.note).pk, "batch": self.batch.pk, "qty": qty, **extra}
