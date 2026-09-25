import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.catalog.models import Item, ItemGroup
from apps.common.exceptions import BusinessError
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier
from apps.purchasing.receipts import services as receipt_services


class SubmitReceiptTests(TestCase):
    def setUp(self):
        self.g = ItemGroup.objects.create(name="Cá")
        self.tom = Item.objects.create(
            code="TOM01", name="Tôm sú", item_group=self.g, shelf_life_in_days=90
        )
        self.muc = Item.objects.create(
            code="MUC01", name="Mực", item_group=self.g, shelf_life_in_days=60
        )
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.user = User.objects.create(username="kho")
        self.today = datetime.date(2026, 9, 1)

    def _receipt(self):
        return PurchaseReceipt.objects.create(
            supplier=self.sup, warehouse=self.wh,
            received_date=self.today, created_by=self.user,
        )

    def test_each_line_makes_one_batch_with_qty_rate_expiry(self):
        r = self._receipt()
        PurchaseReceiptLine.objects.create(
            receipt=r, item=self.tom, qty=Decimal("100"), rate=Decimal("200000")
        )
        PurchaseReceiptLine.objects.create(
            receipt=r, item=self.muc, qty=Decimal("50"), rate=Decimal("150000"),
            shelf_life_days=30,  # sửa xuống thấp hơn mặc định 60 -> hợp lệ
        )

        batches = receipt_services.submit_receipt(receipt=r, actor=self.user)

        self.assertEqual(len(batches), 2)               # BR-MH-01: 1 lô / dòng
        r.refresh_from_db()
        self.assertEqual(r.status, PurchaseReceipt.Status.SUBMITTED)

        tom_batch = PurchaseReceiptLine.objects.get(receipt=r, item=self.tom).batch
        self.assertEqual(tom_batch.qty_received, Decimal("100"))
        self.assertEqual(tom_batch.qty_available, Decimal("100"))
        self.assertEqual(tom_batch.purchase_rate, Decimal("200000"))
        self.assertEqual(tom_batch.landed_unit_cost, Decimal("200000"))  # chưa có chi phí
        self.assertEqual(tom_batch.status, Batch.Status.DRAFT)
        self.assertEqual(tom_batch.expiry_date, self.today + datetime.timedelta(days=90))

        muc_batch = PurchaseReceiptLine.objects.get(receipt=r, item=self.muc).batch
        self.assertEqual(muc_batch.expiry_date, self.today + datetime.timedelta(days=30))

    def test_shelf_life_higher_than_default_is_rejected(self):
        r = self._receipt()
        PurchaseReceiptLine.objects.create(
            receipt=r, item=self.muc, qty=Decimal("10"), rate=Decimal("100000"),
            shelf_life_days=120,  # > mặc định 60 -> BR-MH-02 chặn
        )
        with self.assertRaises(BusinessError):
            receipt_services.submit_receipt(receipt=r, actor=self.user)
        # không lô nào được tạo, phiếu vẫn DRAFT (transaction rollback)
        self.assertEqual(Batch.objects.count(), 0)
        r.refresh_from_db()
        self.assertEqual(r.status, PurchaseReceipt.Status.DRAFT)

    def test_idempotent_second_call_creates_no_duplicate(self):
        r = self._receipt()
        PurchaseReceiptLine.objects.create(
            receipt=r, item=self.tom, qty=Decimal("100"), rate=Decimal("200000")
        )
        first = receipt_services.submit_receipt(receipt=r, actor=self.user)
        second = receipt_services.submit_receipt(receipt=r, actor=self.user)
        self.assertEqual(Batch.objects.count(), 1)
        self.assertEqual(first[0].pk, second[0].pk)
