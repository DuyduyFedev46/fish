"""Dựng dữ liệu dùng chung cho test lô L2 (S3, S4, S5)."""
import datetime
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesInvoice, SalesOrder


def make_user(username, *groups, perms=()):
    user = User.objects.create_user(username, password="x")
    for name in groups:
        user.groups.add(Group.objects.get(name=name))
    for perm in perms:
        app_label, codename = perm.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )
    return User.objects.get(pk=user.pk)  # bỏ cache quyền


def client_for(user):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def make_master():
    g = ItemGroup.objects.create(name="Cá")
    item = Item.objects.create(code="CA01", name="Cá thu", item_group=g)
    sup = Supplier.objects.create(name="Đầu mối A")
    wh = Warehouse.objects.create(name="Kho chính")
    return item, sup, wh


def make_batch(item, sup, wh, qty="50"):
    return batch_services.create_batch(
        item=item, supplier=sup, warehouse=wh,
        received_date=timezone.localdate(), qty=Decimal(qty), purchase_rate=Decimal("80000"),
    )


def make_order_with_note(code, phone, *, assigned_to=None):
    """Đơn PROCESSING + hoá đơn (signal tự tạo phiếu giao) → trả (order, customer, note)."""
    customer = Customer.objects.create(phone=phone, name=f"Khách {code}", default_address="1 Cảng")
    order = SalesOrder.objects.create(
        code=code, customer=customer, status=SalesOrder.Status.PROCESSING,
        delivery_address="1 Cảng", phone=phone, total_amount=Decimal("100000"),
    )
    invoice = SalesInvoice.objects.create(
        code=f"INV-{code}", sales_order=order, customer=customer,
        issued_at=datetime.datetime(2026, 9, 1, 8, 0, tzinfo=datetime.timezone.utc),
        amount=Decimal("100000"), status=SalesInvoice.Status.ISSUED,
    )
    note = invoice.delivery_notes.get()
    if assigned_to is not None:
        note.assigned_to = assigned_to
        note.save(update_fields=["assigned_to"])
    return order, customer, note
