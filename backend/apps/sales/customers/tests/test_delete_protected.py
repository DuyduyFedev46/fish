"""B9 (rà soát bảo mật 15/11, BR-PQ-10): xoá khách đã có đơn -> 409 câu tiếng Việt, không 500. Dữ liệu giả."""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesOrder


class CustomerDeleteTests(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Cá")
        item = Item.objects.create(code="CA01", name="Cá thu", item_group=g)
        pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(price_list=pl, item=item, rate=Decimal("100000"),
                                 valid_from=timezone.localdate() - datetime.timedelta(days=1))
        batch = batch_services.create_batch(
            item=item, supplier=Supplier.objects.create(name="A"), warehouse=Warehouse.objects.create(name="Kho"),
            received_date=timezone.localdate(), qty=Decimal("50"), purchase_rate=Decimal("80000"),
        )
        batch_services.publish_batch(batch=batch, actor=None)
        self.admin = APIClient()
        self.admin.force_authenticate(User.objects.create_superuser("root_del", password="x"))

    def test_delete_customer_with_order_is_409_vietnamese(self):
        APIClient().post("/api/shop/orders/", {
            "customer": {"phone": "0900000888", "name": "Khach Gia"}, "delivery_address": "Dia chi gia",
            "items": [{"item_code": "CA01", "qty": "1"}]}, format="json")
        customer = Customer.objects.get(phone="0900000888")
        self.assertTrue(SalesOrder.objects.filter(customer=customer).exists())
        r = self.admin.delete(f"/api/sales/customers/{customer.pk}/")
        self.assertEqual(r.status_code, 409, r.content)
        self.assertIn("đơn", r.json()["detail"])
        self.assertTrue(Customer.objects.filter(pk=customer.pk).exists())
        self.assertNotIn("0900000888", r.content.decode())

    def test_delete_customer_without_documents_still_works(self):
        customer = Customer.objects.create(phone="0900000889", name="Khach Khong Don")
        self.assertEqual(self.admin.delete(f"/api/sales/customers/{customer.pk}/").status_code, 204)
