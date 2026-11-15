"""
L-1 (rà soát bảo mật 15/11, bất biến 5): IPN/webhook xác nhận tiền ghi AuditLog, không ghi dữ liệu cá nhân.
"""
import datetime
import json
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder

TOKEN = "t" * 40
FAKE_NAME = "Nguyen Van Gia"
FAKE_PHONE = "0900000777"
FAKE_ADDRESS = "Dia chi gia 12"


@override_settings(INTERNAL_SERVICE_TOKEN=TOKEN)
class IpnAuditLogTests(TestCase):
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
        self.api = APIClient()
        body = {"customer": {"phone": FAKE_PHONE, "name": FAKE_NAME}, "delivery_address": FAKE_ADDRESS,
                "items": [{"item_code": "CA01", "qty": "1"}]}
        self.code = self.api.post("/api/shop/orders/", body, format="json").json()["order_code"]
        self.order = SalesOrder.objects.get(code=self.code)

    def _ipn(self, txn="AUDIT1", amount=None, path="sepay-ipn"):
        return self.api.post(f"/api/internal/payments/{path}/", {
            "bank_txn_id": txn, "order_code": self.code,
            "amount": str(amount if amount is not None else self.order.total_amount),
            "received_at": timezone.now().isoformat(),
            "raw": {"payer": FAKE_NAME, "phone": FAKE_PHONE}}, format="json",
            HTTP_X_INTERNAL_TOKEN=TOKEN)

    def test_ipn_paid_writes_audit_log_by_system(self):
        before = AuditLog.objects.count()
        self.assertEqual(self._ipn().status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.PROCESSING)
        rows = AuditLog.objects.filter(action="confirm_payment_ipn")
        self.assertEqual(rows.count(), 1)
        row = rows.get()
        self.assertIsNone(row.actor)
        self.assertEqual(row.object_id, str(self.order.pk))
        self.assertGreater(AuditLog.objects.count(), before)

    def test_ipn_audit_log_has_no_personal_data(self):
        self._ipn()
        blob = json.dumps(list(AuditLog.objects.values("note", "changes", "object_repr")),
                          ensure_ascii=False, default=str)
        for needle in (FAKE_NAME, FAKE_PHONE, FAKE_ADDRESS):
            self.assertNotIn(needle, blob)

    def test_replayed_ipn_does_not_duplicate_audit_log(self):
        self._ipn()
        self._ipn()
        self.assertEqual(AuditLog.objects.filter(action="confirm_payment_ipn").count(), 1)

    def test_legacy_webhook_path_also_audited(self):
        self.assertEqual(self._ipn(txn="AUDIT2", path="sepay-webhook").status_code, 200)
        self.assertEqual(AuditLog.objects.filter(action="confirm_payment_ipn").count(), 1)
