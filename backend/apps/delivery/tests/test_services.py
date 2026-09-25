import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.catalog.models import Item, ItemGroup
from apps.common.exceptions import BusinessError
from apps.delivery import services
from apps.delivery.models import DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import ReturnToStock, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesInvoice, SalesOrder


class DeliveryServiceTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(phone="0900000001", name="Khách A")
        self.order = SalesOrder.objects.create(
            code="SO-0001",
            customer=self.customer,
            status=SalesOrder.Status.PROCESSING,
            delivery_address="123 đường A",
            phone="0900000001",
            total_amount=Decimal("100000"),
        )
        self.invoice = SalesInvoice.objects.create(
            code="INV-0001",
            sales_order=self.order,
            customer=self.customer,
            issued_at=datetime.datetime(2026, 9, 1, 8, 0, tzinfo=datetime.timezone.utc),
            amount=Decimal("100000"),
            status=SalesInvoice.Status.ISSUED,
        )
        self.staff = User.objects.create_user("nv_giao1", password="x")

        # Lô hàng để test return_to_warehouse
        g = ItemGroup.objects.create(name="Cá")
        item = Item.objects.create(code="CA01", name="Cá thu", item_group=g)
        sup = Supplier.objects.create(name="Đầu mối A")
        wh = Warehouse.objects.create(name="Kho chính")
        self.batch = batch_services.create_batch(
            item=item, supplier=sup, warehouse=wh,
            received_date=datetime.date(2026, 9, 1), qty=Decimal("50"),
            purchase_rate=Decimal("80000"),
        )

    # --- create_delivery_note ------------------------------------------------

    def test_create_delivery_note_sets_preparing_and_unique_code(self):
        dn = services.create_delivery_note(invoice=self.invoice)
        self.assertEqual(dn.status, DeliveryNote.Status.PREPARING)
        self.assertEqual(dn.sales_invoice, self.invoice)
        self.assertTrue(dn.code)
        dn2 = services.create_delivery_note(invoice=self.invoice)
        self.assertNotEqual(dn.code, dn2.code)

    def test_create_delivery_note_requires_issued_invoice(self):
        self.invoice.status = SalesInvoice.Status.CANCELLED
        self.invoice.save(update_fields=["status"])
        with self.assertRaises(BusinessError):
            services.create_delivery_note(invoice=self.invoice)

    # --- advance_status -------------------------------------------------------

    def test_advance_status_happy_path_sets_completed_at(self):
        dn = services.create_delivery_note(invoice=self.invoice)
        services.advance_status(note=dn, to_status=DeliveryNote.Status.READY, actor=self.staff)
        dn.refresh_from_db()
        self.assertEqual(dn.status, DeliveryNote.Status.READY)

        services.advance_status(note=dn, to_status=DeliveryNote.Status.DELIVERING, actor=self.staff)
        dn.refresh_from_db()
        self.assertEqual(dn.status, DeliveryNote.Status.DELIVERING)
        self.assertIsNone(dn.completed_at)

        services.advance_status(note=dn, to_status=DeliveryNote.Status.COMPLETED, actor=self.staff)
        dn.refresh_from_db()
        self.assertEqual(dn.status, DeliveryNote.Status.COMPLETED)
        self.assertIsNotNone(dn.completed_at)

    def test_advance_status_rejects_skipping_steps(self):
        dn = services.create_delivery_note(invoice=self.invoice)
        with self.assertRaises(BusinessError):
            services.advance_status(
                note=dn, to_status=DeliveryNote.Status.DELIVERING, actor=self.staff
            )

    def test_completed_is_one_way(self):
        dn = services.create_delivery_note(invoice=self.invoice)
        dn.status = DeliveryNote.Status.COMPLETED
        dn.save(update_fields=["status"])
        with self.assertRaises(BusinessError):
            services.advance_status(
                note=dn, to_status=DeliveryNote.Status.DELIVERING, actor=self.staff
            )

    def test_failed_can_go_back_to_delivering(self):
        dn = services.create_delivery_note(invoice=self.invoice)
        dn.status = DeliveryNote.Status.DELIVERING
        dn.save(update_fields=["status"])
        note, _ = services.mark_failed(note=dn, actor=self.staff)
        services.advance_status(
            note=note, to_status=DeliveryNote.Status.DELIVERING, actor=self.staff
        )
        note.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.DELIVERING)

    # --- mark_failed ------------------------------------------------------------

    @override_settings(DELIVERY_MAX_FAILED_ATTEMPTS=2)
    def test_mark_failed_increments_and_flags_after_threshold(self):
        dn = services.create_delivery_note(invoice=self.invoice)
        dn.status = DeliveryNote.Status.DELIVERING
        dn.save(update_fields=["status"])

        note, needs_decision = services.mark_failed(note=dn, actor=self.staff)
        self.assertEqual(note.failed_attempts, 1)
        self.assertFalse(needs_decision)

        services.advance_status(
            note=note, to_status=DeliveryNote.Status.DELIVERING, actor=self.staff
        )
        note, needs_decision = services.mark_failed(note=note, actor=self.staff)
        self.assertEqual(note.failed_attempts, 2)
        self.assertTrue(needs_decision)  # >= ngưỡng DELIVERY_MAX_FAILED_ATTEMPTS (BR-GH-04)

    def test_mark_failed_requires_delivering_status(self):
        dn = services.create_delivery_note(invoice=self.invoice)
        with self.assertRaises(BusinessError):
            services.mark_failed(note=dn, actor=self.staff)

    # --- return_to_warehouse ------------------------------------------------------

    def test_return_to_warehouse_creates_pending_approval(self):
        dn = services.create_delivery_note(invoice=self.invoice)
        dn.status = DeliveryNote.Status.FAILED
        dn.save(update_fields=["status"])

        rt = services.return_to_warehouse(
            note=dn, batch=self.batch, qty=Decimal("5"), actor=self.staff
        )
        self.assertEqual(rt.status, ReturnToStock.Status.DRAFT)
        self.assertEqual(rt.decision, ReturnToStock.Decision.PENDING)
        self.assertEqual(rt.batch, self.batch)
        self.assertEqual(rt.qty, Decimal("5"))
        # Chưa tác động tồn kho — chỉ tạo phiếu chờ duyệt (BR-HV-02)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, Decimal("50"))

    def test_return_to_warehouse_requires_delivering_or_failed(self):
        dn = services.create_delivery_note(invoice=self.invoice)  # PREPARING
        with self.assertRaises(BusinessError):
            services.return_to_warehouse(
                note=dn, batch=self.batch, qty=Decimal("5"), actor=self.staff
            )
